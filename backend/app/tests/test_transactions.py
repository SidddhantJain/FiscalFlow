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


def test_import_statement_with_preamble_and_auto_detect(client):
    """Verifies that bank statements with preamble/metadata header rows are parsed seamlessly."""
    acc_res = client.post("/accounts/", json={
        "name": "SBI Savings",
        "bank_name": "State Bank of India",
        "account_type": "SAVINGS",
        "opening_balance": 5000.00
    })
    account_id = acc_res.json()["id"]

    csv_content = (
        "State Bank of India\n"
        "Account Statement for Period 01-10-2024 to 31-10-2024\n"
        "Account Number: 9876543210\n"
        "Branch: Bangalore Main\n"
        "Txn Date,Description,Ref No./Cheque No.,Debit,Credit,Balance\n"
        "01-10-2024,Stipend Sigma Park,REF101,-,25000.00,30000.00\n"
        "02-10-2024,PG Rent Stanza Living,REF102,14000.00,-,16000.00\n"
    ).encode("utf-8")

    res = client.post(
        "/transactions/import",
        data={"account_id": account_id, "bank_type": "AUTO_DETECT"},
        files={"file": ("sbi_statement.csv", csv_content, "text/csv")}
    )
    assert res.status_code == 200
    data = res.json()
    assert "Successfully parsed 2 transactions" in data["message"]
    assert data["transaction_count"] == 2


def test_import_statement_with_iso_8859_encoding(client):
    """Verifies that statements with Latin1 / ISO-8859 non-UTF8 bytes do not raise UnicodeDecodeError."""
    acc_res = client.post("/accounts/", json={
        "name": "HDFC Test",
        "bank_name": "HDFC",
        "account_type": "CURRENT",
        "opening_balance": 10000.00
    })
    account_id = acc_res.json()["id"]

    # Contains byte \xa3 (British Pound) or \x80 (Euro) in Latin1
    latin1_csv = (
        "Date,Description,Amount,Reference\n"
        "2024-10-01,Office Lunch Cafe \xa3,150.00,REF_LUNCH\n"
        "2024-10-02,Consulting Bonus,2000.00,REF_BONUS\n"
    ).encode("iso-8859-1")

    res = client.post(
        "/transactions/import",
        data={"account_id": account_id, "bank_type": "DEFAULT_CSV"},
        files={"file": ("export_latin1.csv", latin1_csv, "text/csv")}
    )
    assert res.status_code == 200
    assert res.json()["transaction_count"] == 2


def test_import_statement_html_as_xls(client):
    """Verifies that Netbanking HTML tables exported with .xls extension parse properly."""
    acc_res = client.post("/accounts/", json={
        "name": "Axis Netbanking",
        "bank_name": "Axis Bank",
        "account_type": "SAVINGS",
        "opening_balance": 2000.00
    })
    account_id = acc_res.json()["id"]

    html_xls = (
        "<html><body>"
        "<table border='1'>"
        "<tr><th>Tran Date</th><th>CHQNO</th><th>PARTICULARS</th><th>DR</th><th>CR</th><th>BAL</th></tr>"
        "<tr><td>01-10-2024</td><td>-</td><td>Sigma Soft Tech Park Stipend</td><td></td><td>25000.00</td><td>27000.00</td></tr>"
        "<tr><td>05-10-2024</td><td>CHQ01</td><td>Daily Office Lunch</td><td>150.00</td><td></td><td>26850.00</td></tr>"
        "</table>"
        "</body></html>"
    ).encode("utf-8")

    res = client.post(
        "/transactions/import",
        data={"account_id": account_id, "bank_type": "AXIS_CSV"},
        files={"file": ("axis_download.xls", html_xls, "application/vnd.ms-excel")}
    )
    assert res.status_code == 200
    assert res.json()["transaction_count"] == 2


def test_import_statement_empty_file_rejected(client):
    """Verifies that empty file uploads return a clear, user-friendly 400 Bad Request."""
    acc_res = client.post("/accounts/", json={
        "name": "Check Acc",
        "bank_name": "Bank",
        "account_type": "SAVINGS",
        "opening_balance": 100.00
    })
    account_id = acc_res.json()["id"]

    res = client.post(
        "/transactions/import",
        data={"account_id": account_id, "bank_type": "AUTO_DETECT"},
        files={"file": ("empty.csv", b"", "text/csv")}
    )
    assert res.status_code == 400
    assert "Uploaded statement file is empty" in res.json()["detail"]


def test_import_statement_with_unclosed_quote_at_row_649_and_preamble(client):
    """Verifies that statements with extensive preambles and unclosed quotes at row 649 (EOF inside string) parse successfully."""
    acc_res = client.post("/accounts/", json={
        "name": "Axis Salary Account",
        "bank_name": "Axis Bank",
        "account_type": "SALARY",
        "opening_balance": 15000.00
    })
    account_id = acc_res.json()["id"]

    preamble = [
        "Name :- SIDDHANT SHREYANS MISHRIKOTKAR",
        "Joint Holder :- -",
        "C/O SHREYANS NARENDRA 1501 N",
        "WING 57 MIDTOWN PHOENIX M WAKAD",
        "PUNE-411057",
        "MAHARASHTRA-INDIA",
        "Currency :- INR",
        "Customer ID :- 907471763",
        "IFSC Code :- UTIB0000135",
        "MICR Code :- 413211101",
        "Nominee Registered :- Y",
        "Nominee Name :- SHREYANS MISHRIKOTKAR",
        "Registered Mobile No :- XXXXXX2306",
        "Registered Email ID :- MIXXXXNT@GMAIL.COM",
        "PAN :- FYDPM2178F",
        "CKYC NUMBER :- XXXXXXXXXX2479",
        "",
        "Tran Date,CHQNO,PARTICULARS,DR,CR,BAL,SOL"
    ]

    tx_rows = []
    # Generate 630 transactions up to row 648
    for i in range(1, 631):
        tx_rows.append(f"01-10-2024,-,UPI TRANSACTION {i},,100.00,50000.00,001")

    # Row 649: unclosed quote in footer disclaimer
    footer = [
        '*** "END OF STATEMENT - SYSTEM GENERATED STATEMENT',
        "Disclaimer: In case of discrepancy please report within 14 days",
        "Abbreviations: CR-Credit DR-Debit"
    ]

    full_csv = "\n".join(preamble + tx_rows + footer).encode("utf-8")

    res = client.post(
        "/transactions/import",
        data={"account_id": account_id, "bank_type": "AUTO_DETECT"},
        files={"file": ("axis_649_unclosed.csv", full_csv, "text/csv")}
    )

    assert res.status_code == 200
    data = res.json()
    assert data["transaction_count"] == 630
    assert "Successfully parsed 630 transactions" in data["message"]


