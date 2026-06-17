from datetime import date

def test_transaction_creation_and_balance_adjustment(client):
    # 1. Create a bank account
    acc_res = client.post("/accounts/", json={
        "name": "SBI Savings",
        "bank_name": "SBI",
        "account_type": "SAVINGS",
        "opening_balance": 10000.00
    })
    account_id = acc_res.json()["id"]
    
    # 2. Add an Income transaction
    inc_res = client.post("/transactions/", json={
        "date": "2026-06-17",
        "description": "Salary Credit",
        "amount": 25000.00,
        "type": "INCOME",
        "account_id": account_id
    })
    assert inc_res.status_code == 201
    
    # Check account current balance increased
    acc_check = client.get(f"/accounts/{account_id}")
    assert float(acc_check.json()["current_balance"]) == 35000.00 # 10000 + 25000
    
    # 3. Add an Expense transaction
    exp_res = client.post("/transactions/", json={
        "date": "2026-06-17",
        "description": "Dinner at restaurant",
        "amount": 1500.00,
        "type": "EXPENSE",
        "account_id": account_id
    })
    assert exp_res.status_code == 201
    
    # Check account current balance decreased
    acc_check = client.get(f"/accounts/{account_id}")
    assert float(acc_check.json()["current_balance"]) == 33500.00 # 35000 - 1500
    
    # 4. Delete expense transaction and verify balance reverted
    tx_id = exp_res.json()["id"]
    client.delete(f"/transactions/{tx_id}")
    acc_check = client.get(f"/accounts/{account_id}")
    assert float(acc_check.json()["current_balance"]) == 35000.00 # Reverted to 35000.00


def test_transfer_intelligence_matching(client):
    # Create source account
    src_res = client.post("/accounts/", json={
        "name": "HDFC Salary",
        "account_type": "SALARY",
        "opening_balance": 50000.00
    })
    src_id = src_res.json()["id"]
    
    # Create destination account
    dst_res = client.post("/accounts/", json={
        "name": "ICICI Savings",
        "account_type": "SAVINGS",
        "opening_balance": 10000.00
    })
    dst_id = dst_res.json()["id"]
    
    # Create debit transaction on source (EXPENSE candidate)
    client.post("/transactions/", json={
        "date": "2026-06-15",
        "description": "Transfer to ICICI",
        "amount": 5000.00,
        "type": "EXPENSE",
        "account_id": src_id
    })
    
    # Create credit transaction on destination (INCOME candidate)
    client.post("/transactions/", json={
        "date": "2026-06-15",
        "description": "Funds from HDFC",
        "amount": 5000.00,
        "type": "INCOME",
        "account_id": dst_id
    })
    
    # Verify we have two separate transactions initially
    txs_init = client.get("/transactions/")
    assert len(txs_init.json()) == 2
    
    # Trigger Transfer Engine
    detect_res = client.post("/transactions/detect-transfers")
    assert detect_res.status_code == 200
    assert "linked 1" in detect_res.json()["message"]
    
    # Verify they were merged into a single TRANSFER transaction
    txs_after = client.get("/transactions/")
    assert len(txs_after.json()) == 1
    
    tx = txs_after.json()[0]
    assert tx["type"] == "TRANSFER"
    assert tx["account_id"] == src_id
    assert tx["destination_account_id"] == dst_id
    assert float(tx["amount"]) == 5000.00
    assert "ICICI" in tx["description"]
