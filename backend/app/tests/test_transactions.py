from datetime import date
from unittest.mock import patch
import pandas as pd
from app.services.statement_import import parse_statement

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
    
    # Verify they were merged into a single SAVINGS transaction (since destination is SAVINGS)
    txs_after = client.get("/transactions/")
    assert len(txs_after.json()) == 1
    
    tx = txs_after.json()[0]
    assert tx["type"] == "SAVINGS"
    assert tx["account_id"] == src_id
    assert tx["destination_account_id"] == dst_id
    assert float(tx["amount"]) == 5000.00
    assert "ICICI" in tx["description"]


def test_xls_statement_import_parsing():
    mock_df = pd.DataFrame([
        {"Date": "2026-06-15", "Description": "Salary", "Amount": 50000.00, "Reference": "REF123"},
        {"Date": "2026-06-16", "Description": "Groceries", "Amount": -1500.00, "Reference": "REF124"}
    ])
    
    with patch("pandas.read_excel") as mock_read_excel:
        mock_read_excel.return_value = mock_df
        
        parsed = parse_statement(b"dummy bytes", "statement.xls", "DEFAULT_CSV")
        
        # Verify read_excel was called with engine="xlrd"
        mock_read_excel.assert_called_once()
        _, kwargs = mock_read_excel.call_args
        assert kwargs.get("engine") == "xlrd"
        
        # Verify transaction parsing
        assert len(parsed) == 2
        assert parsed[0]["description"] == "Salary"
        assert parsed[0]["amount"] == 50000.00
        assert parsed[0]["type"] == "INCOME"
        
        assert parsed[1]["description"] == "Groceries"
        assert parsed[1]["amount"] == 1500.00
        assert parsed[1]["type"] == "EXPENSE"


def test_xls_statement_import_endpoint(client):
    # 1. Create a bank account
    acc_res = client.post("/accounts/", json={
        "name": "HDFC Savings",
        "bank_name": "HDFC",
        "account_type": "SAVINGS",
        "opening_balance": 1000.00
    })
    account_id = acc_res.json()["id"]
    
    mock_df = pd.DataFrame([
        {"Date": "2026-06-18", "Description": "Salary Credit", "Amount": 10000.00, "Reference": "TXN001"},
        {"Date": "2026-06-19", "Description": "Rent Payment", "Amount": -3000.00, "Reference": "TXN002"}
    ])
    
    with patch("pandas.read_excel") as mock_read_excel:
        mock_read_excel.return_value = mock_df
        
        # Send post request to import endpoint
        response = client.post(
            "/transactions/import",
            data={"account_id": account_id, "bank_type": "DEFAULT_CSV"},
            files={"file": ("statement.xls", b"dummy bytes", "application/vnd.ms-excel")}
        )
        
        assert response.status_code == 200
        assert "Successfully parsed 2 transactions" in response.json()["message"]
        
        # Check account current balance updated
        acc_check = client.get(f"/accounts/{account_id}")
        assert float(acc_check.json()["current_balance"]) == 8000.00 # 1000 + 10000 - 3000


def test_axis_csv_statement_import_parsing():
    # Axis bank CSV uses: SRL NO, Tran Date, CHQNO, PARTICULARS, DR, CR, BAL, SOL
    mock_df = pd.DataFrame([
        {
            "SRL NO": 1,
            "Tran Date": "18-06-2026",
            "CHQNO": "CHQ100",
            "PARTICULARS": "Salary Credit Axis",
            "DR": "-",
            "CR": "55000.00",
            "BAL": "55000.00",
            "SOL": "1234"
        },
        {
            "SRL NO": 2,
            "Tran Date": "19-06-2026",
            "CHQNO": "",
            "PARTICULARS": "ATM Withdrawal Axis",
            "DR": "10000.00",
            "CR": "nan",
            "BAL": "45000.00",
            "SOL": "1234"
        }
    ])
    
    with patch("pandas.read_csv") as mock_read_csv:
        mock_read_csv.return_value = mock_df
        
        parsed = parse_statement(b"dummy bytes", "statement.csv", "AXIS_CSV")
        
        assert len(parsed) == 2
        assert parsed[0]["description"] == "Salary Credit Axis"
        assert parsed[0]["amount"] == 55000.00
        assert parsed[0]["type"] == "INCOME"
        assert parsed[0]["reference_number"] == "CHQ100"
        
        assert parsed[1]["description"] == "ATM Withdrawal Axis"
        assert parsed[1]["amount"] == 10000.00
        assert parsed[1]["type"] == "EXPENSE"
        assert parsed[1]["reference_number"] is None
