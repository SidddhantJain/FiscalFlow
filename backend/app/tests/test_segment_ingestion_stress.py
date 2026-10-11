import io
import time
import pytest
from decimal import Decimal
from app.services.statement_import import parse_statement, import_statement_transactions
from app.models.account import Account

def test_axis_bank_deep_preamble_and_unclosed_quotes(db):
    """Segment 2: Ingest Axis Bank statement with 80 preamble lines, unicode ₹, and row 649 unclosed quote."""
    # Build preamble
    preamble_lines = [f"Account Statement Info Header Line {i}" for i in range(80)]
    preamble_lines.append("TRAN DATE,CHQ NO,PARTICULARS,DR,CR,BAL,SOL")
    
    # 50 valid transaction lines
    data_lines = []
    for i in range(1, 51):
        if i % 2 == 0:
            data_lines.append(f"01-08-2025,-,UPI/52134{i}/Swiggy/Bangalore,₹ 350.00,,₹ 45000.00,0012")
        else:
            data_lines.append(f"02-08-2025,-,SALARY/SigmaTech/Stipend,,₹ 25000.00,₹ 70000.00,0012")
            
    # Broken footer with unclosed quotes like real bank PDFs/CSVs
    footer_lines = [
        '*** "END OF STATEMENT - Axis Bank Customer Care 1860-419-5555',
        'Registered Office: "Trishul", 3rd Floor, Ahmedabad - 380 006',
        'Legends: CR - Credit, DR - Debit'
    ]
    
    full_csv = "\n".join(preamble_lines + data_lines + footer_lines)
    file_bytes = full_csv.encode("utf-8")
    
    start_time = time.time()
    txs = parse_statement(file_bytes, "axis_statement_sample.csv", "AXIS_CSV")
    parse_time = time.time() - start_time
    
    assert len(txs) == 50, f"Expected 50 parsed transactions, got {len(txs)}"
    assert parse_time < 1.0, f"Parsing took too long: {parse_time:.3f}s"
    
    # Check amounts parsed cleanly despite ₹ symbols
    assert txs[0]["amount"] == Decimal("25000.00")
    assert txs[0]["type"] == "INCOME"
    assert txs[1]["amount"] == Decimal("350.00")
    assert txs[1]["type"] == "EXPENSE"

def test_hdfc_and_sbi_statement_formats(db):
    """Segment 2: Validate HDFC and SBI statement header recognition and field extraction."""
    # HDFC format
    hdfc_csv = """Date,Narration,Chq/Ref No,Value Dt,Withdrawal Amt,Deposit Amt,Closing Balance
05/09/2025,POS 45678 STARBUCKS,REF1001,05/09/2025,450.00,,12000.00
06/09/2025,NEFT CR-SIGMA STIPEND,REF1002,06/09/2025,,25000.00,37000.00
"""
    txs_hdfc = parse_statement(hdfc_csv.encode("utf-8"), "hdfc_stmt.csv", "HDFC_CSV")
    assert len(txs_hdfc) == 2
    assert txs_hdfc[0]["type"] == "EXPENSE"
    assert txs_hdfc[1]["type"] == "INCOME"

    # SBI format
    sbi_csv = """Txn Date,Value Date,Description,Ref No./Cheque No.,Debit,Credit,Balance
10-Oct-2025,10-Oct-2025,TRANSFER TO GROWW MF,CHQ9988,5000.00,,45000.00
11-Oct-2025,11-Oct-2025,INTEREST CREDIT,INT0011,,120.00,45120.00
"""
    txs_sbi = parse_statement(sbi_csv.encode("utf-8"), "sbi_stmt.csv", "SBI_CSV")
    assert len(txs_sbi) == 2
    assert txs_sbi[0]["type"] in ["INVESTMENT", "EXPENSE"]
    assert txs_sbi[1]["type"] == "INCOME"

def test_stress_ingestion_1000_transactions(client, db):
    """Segment 2: Stress test ingestion of 1,000 transactions and verify deduplication benchmark."""
    # 1. Create account
    acc = client.post("/accounts/", json={
        "name": "Stress Test Bank",
        "bank_name": "Axis Bank",
        "account_type": "SAVINGS",
        "opening_balance": 100000.00
    }).json()
    acc_id = acc["id"]

    # 2. Generate 1,000 CSV transaction rows
    csv_rows = ["TRAN DATE,CHQ NO,PARTICULARS,DR,CR,BAL,SOL"]
    for i in range(1, 1001):
        day = (i % 28) + 1
        month = ((i // 28) % 12) + 1
        date_str = f"{day:02d}-{month:02d}-2025"
        ref_no = f"TXREF{i:06d}"
        if i % 3 == 0:
            csv_rows.append(f"{date_str},-,UPI/MERCHANT{i}/Dinner,250.00,,50000.00,1001")
        else:
            csv_rows.append(f"{date_str},-,UPI/PAYMENT{i}/BMTC Transit,50.00,,50000.00,1001")
            
    csv_content = "\n".join(csv_rows)
    file_bytes = csv_content.encode("utf-8")

    # Benchmark parsing 1,000 rows
    parse_start = time.time()
    parsed_txs = parse_statement(file_bytes, "bulk_1000.csv", "AXIS_CSV")
    parse_duration = time.time() - parse_start
    assert len(parsed_txs) == 1000
    assert parse_duration < 2.0, f"1,000 row parsing took {parse_duration:.2f}s (target <2.0s)"

    # Benchmark ingestion & SQL insert
    ingest_start = time.time()
    inserted_count = import_statement_transactions(db, acc_id, parsed_txs)
    ingest_duration = time.time() - ingest_start
    assert inserted_count == 1000
    assert ingest_duration < 3.0, f"1,000 row DB ingestion took {ingest_duration:.2f}s (target <3.0s)"

    # 3. Deduplication stress test: Re-ingest the exact same 1,000 transactions
    dedup_start = time.time()
    re_inserted_count = import_statement_transactions(db, acc_id, parsed_txs)
    dedup_duration = time.time() - dedup_start
    assert re_inserted_count == 0, "Deduplication failed: duplicates were inserted!"
    assert dedup_duration < 1.0, f"Deduplication took {dedup_duration:.2f}s (target <1.0s)"

    # 4. Stress query performance on 1,000 transactions with days=30 filter
    query_start = time.time()
    res = client.get("/transactions/?days=30")
    query_duration = time.time() - query_start
    assert res.status_code == 200
    assert query_duration < 0.25, f"Filtered query took {query_duration:.3f}s (target <0.25s)"
    data = res.json()
    assert len(data) > 0 and len(data) < 1000, f"Should return 30-day window, got {len(data)}"
