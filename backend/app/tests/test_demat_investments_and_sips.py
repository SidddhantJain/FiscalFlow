import io
from decimal import Decimal
from datetime import date, datetime
from app.models.account import Account
from app.models.investment import Investment
from app.models.sip import SipSchedule
from app.models.statement_file import StatementFile
from app.services.statement_import import parse_demat_statement, import_demat_holdings

def test_create_demat_and_bank_accounts(client, db):
    """Verifies creating bank and Demat accounts with account numbers and broker info."""
    # 1. Bank Account
    res_bank = client.post("/accounts/", json={
        "name": "HDFC Salary Account",
        "bank_name": "HDFC Bank",
        "account_type": "SALARY",
        "account_number": "501004928192",
        "opening_balance": 31000.00,
        "currency": "INR"
    })
    assert res_bank.status_code == 201
    bank_data = res_bank.json()
    assert bank_data["name"] == "HDFC Salary Account"
    assert bank_data["account_number"] == "501004928192"

    # 2. Demat Account
    res_demat = client.post("/accounts/", json={
        "name": "Groww Demat Account",
        "bank_name": "Groww",
        "account_type": "DEMAT",
        "account_number": "1208160098765432",
        "opening_balance": 50000.00,
        "currency": "INR"
    })
    assert res_demat.status_code == 201
    demat_data = res_demat.json()
    assert demat_data["account_type"] == "DEMAT"
    assert demat_data["bank_name"] == "Groww"

def test_groww_demat_statement_parsing_and_import(client, db):
    """Verifies parsing and importing a Groww Demat holding statement."""
    # Create Demat account
    acc = Account(
        user_id=1,
        name="Groww Investment Portfolio",
        bank_name="Groww",
        account_type="DEMAT",
        account_number="1208160012345678",
        opening_balance=Decimal("0.00"),
        current_balance=Decimal("0.00"),
        currency="INR"
    )
    db.add(acc)
    db.commit()
    db.refresh(acc)

    groww_csv = (
        "Stock Name,Symbol,Quantity,Avg Price,Current Price,Invested Value,Current Value,Trade Date,Type\n"
        "Tata Consultancy Services,TCS,10,3200.00,3800.00,32000.00,38000.00,2024-10-01,BUY\n"
        "Infosys Ltd,INFY,25,1400.00,1650.00,35000.00,41250.00,2024-10-05,BUY\n"
        "Parag Parikh Flexi Cap Fund - Direct Growth,PPFAS,150,60.00,75.00,9000.00,11250.00,2024-10-10,SIP\n"
    )

    file_bytes = groww_csv.encode("utf-8")
    holdings, txs = parse_demat_statement(file_bytes, "groww_holdings_oct2024.csv", "GROWW_DEMAT")

    assert len(holdings) == 3
    assert holdings[0]["symbol"] == "TCS"
    assert holdings[0]["units"] == Decimal("10")
    assert holdings[0]["purchase_price"] == Decimal("3200.00")
    assert holdings[0]["current_value"] == Decimal("38000.00")
    assert holdings[2]["asset_class"] == "MUTUAL_FUND"

    # Test API endpoint
    response = client.post(
        "/investments/import-demat",
        data={"account_id": acc.id, "broker_type": "GROWW_DEMAT"},
        files={"file": ("groww_holdings_oct2024.csv", io.BytesIO(file_bytes), "text/csv")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["holdings_count"] == 3

    # Check that statement file was recorded
    stmt_file = db.query(StatementFile).filter(StatementFile.bank_type == "GROWW_DEMAT").first()
    assert stmt_file is not None
    assert stmt_file.filename == "groww_holdings_oct2024.csv"

def test_angelone_demat_statement_parsing(client, db):
    """Verifies parsing Angel One Demat trade/holdings CSV."""
    angel_csv = (
        "Symbol,Scrip Name,Trade Date,Buy/Sell,Qty,Price,Trade Value,CMP,Current Value\n"
        "RELIANCE,Reliance Industries Ltd,2024-09-15,BUY,15,2400.00,36000.00,2700.00,40500.00\n"
        "HDFCBANK,HDFC Bank Ltd,2024-09-20,BUY,20,1500.00,30000.00,1650.00,33000.00\n"
    )
    file_bytes = angel_csv.encode("utf-8")
    holdings, txs = parse_demat_statement(file_bytes, "angel_portfolio.csv", "ANGELONE_DEMAT")
    assert len(holdings) == 2
    assert holdings[0]["symbol"] == "RELIANCE"
    assert holdings[0]["broker"] == "Angel One"
    assert holdings[0]["units"] == Decimal("15")

def test_sip_schedule_lifecycle_and_execution(client, db):
    """Verifies creating SIPs, computing upcoming execution dates, and recording executions."""
    # 1. Create source bank account
    acc = Account(
        user_id=1,
        name="Primary Salary Account",
        bank_name="HDFC Bank",
        account_type="SALARY",
        opening_balance=Decimal("50000.00"),
        current_balance=Decimal("50000.00"),
        currency="INR"
    )
    db.add(acc)
    db.commit()
    db.refresh(acc)

    # 2. Create SIP Schedule
    res_sip = client.post("/sips/", json={
        "scheme_name": "Quant Small Cap Fund - Direct Growth",
        "asset_class": "MUTUAL_FUND",
        "amount": 2500.00,
        "frequency": "MONTHLY",
        "sip_day_of_month": 15,
        "broker": "Groww",
        "account_id": acc.id,
        "status": "ACTIVE"
    })
    assert res_sip.status_code == 201
    sip_data = res_sip.json()
    assert sip_data["scheme_name"] == "Quant Small Cap Fund - Direct Growth"
    assert sip_data["amount"] == 2500.00
    assert sip_data["sip_day_of_month"] == 15
    assert sip_data["next_sip_date"] is not None

    # Add second SIP to reach ₹5,500 budget target (₹2,500 + ₹3,000)
    client.post("/sips/", json={
        "scheme_name": "Parag Parikh Flexi Cap Fund",
        "asset_class": "MUTUAL_FUND",
        "amount": 3000.00,
        "frequency": "MONTHLY",
        "sip_day_of_month": 5,
        "broker": "Groww",
        "account_id": acc.id,
        "status": "ACTIVE"
    })

    # 3. List SIPs and check countdown
    res_list = client.get("/sips/")
    assert res_list.status_code == 200
    sips = res_list.json()
    assert len(sips) == 2
    assert "days_remaining" in sips[0]

    # 4. Execute SIP and verify balance deduction and transaction generation
    sip_id = sip_data["id"]
    res_exec = client.post(f"/sips/{sip_id}/execute")
    assert res_exec.status_code == 200
    exec_data = res_exec.json()
    assert "executed successfully" in exec_data["message"]

    # Verify Account balance updated
    db.refresh(acc)
    assert acc.current_balance == Decimal("47500.00")  # 50000 - 2500

def test_financial_analysis_tool(client, db):
    """Verifies portfolio analysis endpoint returning valuations, P&L, and broker splits."""
    # Seed investments
    inv1 = Investment(
        user_id=1,
        name="Tata Consultancy Services",
        symbol="TCS",
        asset_class="STOCK",
        broker="Groww",
        units=Decimal("10"),
        purchase_price=Decimal("3000.00"),
        current_value=Decimal("35000.00")
    )
    inv2 = Investment(
        user_id=1,
        name="Parag Parikh Flexi Cap Fund",
        symbol="PPFAS",
        asset_class="MUTUAL_FUND",
        broker="Groww",
        units=Decimal("100"),
        purchase_price=Decimal("50.00"),
        current_value=Decimal("7000.00")
    )
    db.add_all([inv1, inv2])

    # Seed SIP
    sip = SipSchedule(
        user_id=1,
        scheme_name="Parag Parikh Flexi Cap Fund",
        amount=Decimal("5500.00"),
        sip_day_of_month=10,
        next_sip_date=date.today(),
        broker="Groww",
        status="ACTIVE"
    )
    db.add(sip)
    db.commit()

    # Call Analysis API
    res = client.get("/investments/analysis")
    assert res.status_code == 200
    analysis = res.json()

    summary = analysis["portfolio_summary"]
    assert summary["total_invested"] == 35000.00  # (10*3000) + (100*50) = 30000 + 5000 = 35000
    assert summary["current_value"] == 42000.00   # 35000 + 7000 = 42000
    assert summary["total_pnl"] == 7000.00
    assert summary["total_pnl_pct"] == 20.0

    sip_analytics = analysis["sip_analytics"]
    assert sip_analytics["monthly_committed_sip"] == 5500.00
    assert sip_analytics["master_budget_target"] == 5500.00
    assert sip_analytics["sip_alignment_pct"] == 100.0

def test_angel_one_mutual_fund_holdings_format_parsing():
    """Validates parsing Angel One Excel structure with header preamble and Fund Name / ISIN / NAV columns."""
    from app.services.statement_import import parse_demat_statement
    angel_csv = (
        "Client ID,S61221363\n"
        "Name,SIDDHANT SHREYANS MISHRIKOTKAR\n"
        "PAN NO,XXXXXX178F\n"
        "\n"
        "Summary of your holdings\n"
        "Invested Value,Value as on,Unrealized P&L,Unrealized P&L %\n"
        "25649.36,26501.76,852.40,3.32\n"
        "\n"
        "Holdings as on 08/10/2026\n"
        "Fund Name,ISIN,Category,Sub Category,Folio No,Source,Units,Invested Value,Value as on,Average NAV,NAV as on,Unrealized P&L,Unrealized P&L %\n"
        "HDFC Small Cap Fund,INF179KA1RW5,Equity,Small Cap Fund,32890510/71,Angel One,76.373,11749.87,11740.74,153.848,153.729,-9.13,-0.08\n"
        "Nippon India Silver ETF FoF,INF204KC1378,Other,FoFs Domestic,488444974147,Angel One,59.897,1999.96,1964.37,33.39,32.796,-35.59,-1.78\n"
        "Total,25649.36,26501.76\n"
    )
    holdings, txs = parse_demat_statement(angel_csv.encode("utf-8"), "Statement_2026.csv", "ANGELONE_DEMAT")
    assert len(holdings) == 2
    assert holdings[0]["name"] == "HDFC Small Cap Fund"
    assert holdings[0]["symbol"] == "INF179KA1RW5"
    assert holdings[0]["units"] == Decimal("76.373")
    assert holdings[0]["purchase_price"] == Decimal("153.848")
    assert holdings[0]["current_value"] == Decimal("11740.74")
    assert holdings[0]["asset_class"] == "MUTUAL_FUND"

    assert holdings[1]["name"] == "Nippon India Silver ETF FoF"
    assert holdings[1]["units"] == Decimal("59.897")

def test_groww_balance_statement_ledger_parsing():
    """Validates parsing Groww Balance Statement funds ledger with Debit (Rs.) and Credit (Rs.)."""
    from app.services.statement_import import parse_statement
    groww_csv = (
        "Client Name,Siddhant Shreyans Mishrikotkar\n"
        "Unique Client Code,5664699170\n"
        "PAN,FYDPM2178F\n"
        "\n"
        "Transaction Date,Settlement Date,Clearing Member,Segment Type,Settlement No.,Bill/Chq No.,Transaction Type,Particulars / Narration,Voucher No.,Debit (Rs.),Credit (Rs.),Balance (Rs.)\n"
        "28-09-2026,29-09-2026,CM,STOCKS_SETTLEMENT,5664699170_2026183M,5664699170_2026183M,bill,SET26280920697589853542567,0,0,544.48,544.48\n"
        "28-09-2026,28-09-2026,UPI,GROWW_WITHDRAW,PAYMENT|123,Payment,WTD26281842,GROWW WITHDRAWAL,0,22199.13,0,0\n"
        "10-08-2026,10-08-2026,UPI,UPI,JV,DEP20260810,JV,UPI DEPOSIT,0,0,1000.00,1000.00\n"
    )
    txs = parse_statement(groww_csv.encode("utf-8"), "Groww_Balance_Statement.csv", "AUTO_DETECT")
    assert len(txs) == 3
    # Credit is income
    assert txs[0]["type"] == "INCOME"
    assert txs[0]["amount"] == Decimal("544.48")
    # Debit is expense
    assert txs[1]["type"] == "EXPENSE"
    assert txs[1]["amount"] == Decimal("22199.13")
    # Credit deposit is income
    assert txs[2]["type"] == "INCOME"
    assert txs[2]["amount"] == Decimal("1000.00")

def test_credit_debit_preservation_with_indicator_and_ai_engine(db):
    """Guarantees that Credit/Debit indicator mapping and auto-categorization never invert transaction direction."""
    from app.services.statement_import import parse_statement, import_statement_transactions
    from app.services.ai_engine import auto_categorize_uncategorized_transactions
    from app.models.transaction import Transaction

    acc = Account(
        user_id=1,
        name="Indicator Test Account",
        bank_name="Test Bank",
        account_type="SAVINGS",
        opening_balance=Decimal("10000.00"),
        current_balance=Decimal("10000.00"),
        currency="INR"
    )
    db.add(acc)
    db.commit()

    # Statement with unified Amount column and Indicator column
    csv_data = (
        "Date,Particulars,Amount,Type\n"
        "2024-10-10,UPI from Vivek,500.00,CR\n"
        "2024-10-11,Sigma cafe Lunch,80.00,DR\n"
        "2024-10-12,Refund from Amazon,250.00,CR\n"
    )
    txs = parse_statement(csv_data.encode("utf-8"), "test.csv", "AUTO_DETECT")
    assert len(txs) == 3
    assert txs[0]["type"] == "INCOME"
    assert txs[1]["type"] == "EXPENSE"
    assert txs[2]["type"] == "INCOME"

    # Import into DB
    import_statement_transactions(db, acc.id, txs)
    # Run auto-categorization
    auto_categorize_uncategorized_transactions(db, 1)

    db_txs = db.query(Transaction).filter(Transaction.account_id == acc.id).order_by(Transaction.date).all()
    # Ensure income transactions remained INCOME even after categorizer ran!
    assert db_txs[0].type == "INCOME"
    assert db_txs[1].type == "EXPENSE"
    assert db_txs[2].type == "INCOME"

