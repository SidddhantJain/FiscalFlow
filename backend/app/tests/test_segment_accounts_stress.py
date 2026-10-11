import time
import pytest
from decimal import Decimal

def test_account_creation_all_types(client):
    """Segment 1: Validate creation of all supported account types with opening balances."""
    account_types = ["SAVINGS", "CURRENT", "SALARY", "DEMAT", "CREDIT_CARD", "WALLET", "CASH"]
    created_ids = []
    
    for idx, acc_type in enumerate(account_types):
        res = client.post("/accounts/", json={
            "name": f"Test {acc_type} Account {idx}",
            "bank_name": "Test Bank",
            "account_type": acc_type,
            "opening_balance": 15000.50
        })
        assert res.status_code == 201, f"Failed for {acc_type}: {res.text}"
        data = res.json()
        assert data["account_type"] == acc_type
        assert float(data["current_balance"]) == 15000.50
        created_ids.append(data["id"])
        
    # Verify all accounts listable
    list_res = client.get("/accounts/")
    assert list_res.status_code == 200
    listed_ids = [a["id"] for a in list_res.json()]
    for cid in created_ids:
        assert cid in listed_ids

def test_account_balance_integrity_under_rapid_activity(client):
    """Segment 1: Stress test balance calculations across dozens of rapid deposits and debits."""
    acc_res = client.post("/accounts/", json={
        "name": "Rapid Balance Account",
        "bank_name": "Axis Bank",
        "account_type": "SAVINGS",
        "opening_balance": 10000.00
    })
    acc_id = acc_res.json()["id"]
    
    expected_balance = Decimal("10000.00")
    
    # 20 credits and 20 debits
    for i in range(20):
        credit_amt = Decimal("500.00")
        client.post("/transactions/", json={
            "date": f"2026-06-{(i % 28) + 1:02d}",
            "description": f"Rapid Credit {i}",
            "amount": float(credit_amt),
            "type": "INCOME",
            "account_id": acc_id
        })
        expected_balance += credit_amt
        
        debit_amt = Decimal("200.00")
        client.post("/transactions/", json={
            "date": f"2026-06-{(i % 28) + 1:02d}",
            "description": f"Rapid Debit {i}",
            "amount": float(debit_amt),
            "type": "EXPENSE",
            "account_id": acc_id
        })
        expected_balance -= debit_amt
        
    acc_check = client.get(f"/accounts/{acc_id}")
    assert acc_check.status_code == 200
    actual_balance = Decimal(str(acc_check.json()["current_balance"]))
    assert actual_balance == expected_balance
    assert actual_balance == Decimal("16000.00")

def test_clean_duplicates_safeguards_active_accounts(client):
    """Segment 1: Validate duplicate purge cleans empty zero-balance accounts but preserves accounts with data."""
    # 1. Create original account with transactions
    orig = client.post("/accounts/", json={
        "name": "My Primary Account",
        "bank_name": "HDFC Bank",
        "account_type": "SAVINGS",
        "opening_balance": 5000.00
    }).json()
    
    client.post("/transactions/", json={
        "date": "2026-06-10",
        "description": "Important Transaction",
        "amount": 1000.00,
        "type": "INCOME",
        "account_id": orig["id"]
    })
    
    # 2. Create duplicate inactive accounts with 0 balance
    dup1 = client.post("/accounts/", json={
        "name": "My Primary Account",
        "bank_name": "HDFC Bank",
        "account_type": "SAVINGS",
        "opening_balance": 0.00
    }).json()
    
    dup2 = client.post("/accounts/", json={
        "name": "My Primary Account",
        "bank_name": "HDFC Bank",
        "account_type": "SAVINGS",
        "opening_balance": 0.00
    }).json()
    
    # 3. Run clean-duplicates
    purge_res = client.post("/accounts/clean-duplicates")
    assert purge_res.status_code == 200
    purge_data = purge_res.json()
    assert purge_data["deleted_count"] >= 2
    
    # Verify original account with transactions is still intact!
    check_orig = client.get(f"/accounts/{orig['id']}")
    assert check_orig.status_code == 200
    assert float(check_orig.json()["current_balance"]) == 6000.00

def test_accounts_stress_bulk_load(client):
    """Segment 1: Stress test creating 30 accounts in rapid succession and querying within 500ms."""
    start_time = time.time()
    for i in range(30):
        client.post("/accounts/", json={
            "name": f"Stress Account {i}",
            "bank_name": "SBI",
            "account_type": "SAVINGS",
            "opening_balance": float(i * 100)
        })
    creation_duration = time.time() - start_time
    assert creation_duration < 5.0, f"Account creation took too long: {creation_duration:.2f}s"
    
    query_start = time.time()
    res = client.get("/accounts/")
    query_duration = time.time() - query_start
    assert res.status_code == 200
    assert len(res.json()) >= 30
    assert query_duration < 0.5, f"Bulk account fetch query took too long: {query_duration:.3f}s"
