import pytest
import io
from datetime import date
from decimal import Decimal
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.budget import Budget
from app.services.ai_engine import extract_transaction_tags, auto_categorize_uncategorized_transactions
from app.services.statement_import import parse_statement, import_statement_transactions

def test_extract_transaction_tags():
    # Food / Cafe
    tags = extract_transaction_tags("Third Wave Coffee Roasters Koramangala", "Daily Office Lunch (Mon–Sat)", "EXPENSE")
    assert "Food" in tags
    assert "Cafe" in tags
    
    # BMTC Commute
    tags = extract_transaction_tags("BMTC Bus Pass Varthur to Kundalahalli", "BMTC Bus Commute", "EXPENSE")
    assert "BMTC" in tags
    assert "Commute" in tags or "Travel" in tags

    # Kirana / Lifestyle
    tags = extract_transaction_tags("Blinkit Quick Commerce Groceries", "Lifestyle & Personal Essentials", "EXPENSE")
    assert "Kirana" in tags or "Groceries" in tags or "Lifestyle" in tags

    # PG Rent
    tags = extract_transaction_tags("Stanza Living PG Rent Monthly", "PG Rent & Covered Meals", "EXPENSE")
    assert "PG Rent" in tags or "Housing" in tags

    # Investment / SIP
    tags = extract_transaction_tags("Groww Mutual Fund Auto SIP", "Monthly SIP Investment", "INVESTMENT")
    assert "SIP" in tags or "Investment" in tags

    # UPI
    tags = extract_transaction_tags("UPI/42890123/Chai Point/siddhant@okaxis", "", "EXPENSE")
    assert "UPI" in tags

def test_axis_bank_statement_parsing_and_import(client, db):
    # 1. Create a test account
    acc = Account(user_id=1, name="Axis Salary Account", bank_name="Axis Bank", account_type="SALARY", current_balance=Decimal("0.00"))
    db.add(acc)
    db.commit()
    db.refresh(acc)

    # 2. Parse Axis CSV statement
    axis_csv = """Tran Date,CHQNO,PARTICULARS,DR,CR,BAL,SOL
01-10-2024,-,SIGMA SOFT TECH PARK STIPEND OCT,,25000.00,25000.00,001
02-10-2024,-,PG RENT STANZA LIVING OCT 2024,14000.00,,11000.00,001
03-10-2024,-,UPI/GROWW MUTUAL FUND SIP/groww@okaxis,5500.00,,5500.00,001
04-10-2024,-,BMTC BUS CHALO CARD RECHARGE,1000.00,,4500.00,001
05-10-2024,-,SIGMA CANTEEN OFFICE LUNCH,150.00,,4350.00,001
"""
    parsed_txs = parse_statement(axis_csv.encode('utf-8'), "axis.csv", "AXIS_CSV")
    assert len(parsed_txs) == 5
    assert parsed_txs[0]["amount"] == Decimal("25000.00")
    assert parsed_txs[0]["type"] == "INCOME"

    # 3. Import and run auto-categorization
    count = import_statement_transactions(db, acc.id, parsed_txs)
    assert count == 5
    
    auto_categorize_uncategorized_transactions(db, 1)
    
    txs = db.query(Transaction).filter(Transaction.account_id == acc.id).all()
    # Groww transaction should be categorized under Monthly SIP Investment / Mutual Funds and tagged SIP/Investment
    groww_tx = next(t for t in txs if "GROWW" in t.description)
    assert groww_tx.type == "INVESTMENT"
    assert "SIP" in groww_tx.tags or "Investment" in groww_tx.tags

def test_master_budget_summary_and_reset(client, db):
    # 1. Trigger Master Budget reset
    res = client.post("/budgets/reset-master")
    assert res.status_code == 200
    
    # 2. Query summary
    res = client.get("/budgets/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["planned_income"] == 31000.00
    assert data["total_planned_allocation"] == 31000.00
    assert len(data["items"]) == 7

def test_overgrown_budget_detection_and_tag_filtering(client, db):
    # 1. Reset master budget
    client.post("/budgets/reset-master")
    
    # 2. Create account
    acc = Account(user_id=1, name="Primary Bank", bank_name="Axis Bank", account_type="SAVINGS", current_balance=Decimal("10000.00"))
    db.add(acc)
    db.commit()
    db.refresh(acc)
    
    # 3. Find Office Lunch Category
    lunch_cat = db.query(Category).filter(Category.name.like("%Lunch%")).first()
    assert lunch_cat is not None
    
    # 4. Insert an over-budget expense (Lunch budget is ₹3,250, we spend ₹4,000)
    tx_data = {
        "date": date.today().isoformat(),
        "description": "Starbucks & Sigma Tech Park Multi Canteen Dining",
        "amount": 4000.00,
        "type": "EXPENSE",
        "category_id": lunch_cat.id,
        "account_id": acc.id,
        "tags": "Food, Cafe, Dining"
    }
    create_res = client.post("/transactions/", json=tx_data)
    assert create_res.status_code == 201
    
    # 5. Check budget summary for overgrown alert
    summary = client.get("/budgets/summary").json()
    assert summary["overgrown_count"] >= 1
    overgrown = summary["overgrown_items"][0]
    assert "Lunch" in overgrown["name"]
    assert overgrown["is_overgrown"] is True
    assert overgrown["spent"] == 4000.00
    
    # 6. Test Tag Filter in transactions endpoint
    res_tag = client.get("/transactions/?tag=Cafe")
    assert res_tag.status_code == 200
    txs = res_tag.json()
    assert len(txs) >= 1
    assert "Cafe" in txs[0]["tags"]

def test_manual_transaction_tag_update(client, db):
    acc = Account(user_id=1, name="Primary Bank", bank_name="Axis Bank", account_type="SAVINGS", current_balance=Decimal("10000.00"))
    db.add(acc)
    db.commit()
    db.refresh(acc)
    
    tx_data = {
        "date": date.today().isoformat(),
        "description": "Apollo Pharmacy Varthur",
        "amount": 450.00,
        "type": "EXPENSE",
        "account_id": acc.id
    }
    create_res = client.post("/transactions/", json=tx_data)
    assert create_res.status_code == 201
    tx = create_res.json()
    assert "Medical" in tx["tags"] or "Healthcare" in tx["tags"]
    
    # Manually change tags
    update_res = client.put(f"/transactions/{tx['id']}", json={"tags": "Medical, Essentials, CustomTag"})
    assert update_res.status_code == 200
    updated_tx = update_res.json()
    assert updated_tx["tags"] == "Medical, Essentials, CustomTag"

def test_repetitive_transaction_tag_learning(client, db):
    acc = Account(user_id=1, name="Axis Bank", bank_name="Axis Bank", account_type="SALARY", current_balance=Decimal("5000.00"))
    db.add(acc)
    db.commit()
    db.refresh(acc)
    
    # 1. Insert a transaction with a unique repetitive pattern
    tx1_data = {
        "date": date.today().isoformat(),
        "description": "Chai Point Whitefield Tech Lounge",
        "amount": 120.00,
        "type": "EXPENSE",
        "account_id": acc.id
    }
    r1 = client.post("/transactions/", json=tx1_data).json()
    
    # 2. User manually custom tags this transaction
    client.put(f"/transactions/{r1['id']}", json={"tags": "Office Snacks, Chai, Sigma Lunch"})
    
    # 3. Verify rule is remembered in tag rules list
    rules_res = client.get("/statements/tag-rules")
    assert rules_res.status_code == 200
    rules = rules_res.json()
    assert any("chai point" in r["pattern"] for r in rules)
    
    # 4. When a new identical or repetitive transaction arrives, it automatically inherits the learned tags!
    tx2_data = {
        "date": date.today().isoformat(),
        "description": "UPI/998811/Chai Point Whitefield Tech Lounge/chaipoint@okaxis",
        "amount": 140.00,
        "type": "EXPENSE",
        "account_id": acc.id
    }
    r2 = client.post("/transactions/", json=tx2_data).json()
    assert "Office Snacks" in r2["tags"]
    assert "Chai" in r2["tags"]

def test_statement_file_persistence_download_and_axis_export(client, db):
    acc = Account(user_id=1, name="Axis Savings", bank_name="Axis Bank", account_type="SAVINGS", current_balance=Decimal("20000.00"))
    db.add(acc)
    db.commit()
    db.refresh(acc)
    
    # 1. Upload an Axis statement file
    sample_csv = "Tran Date,CHQNO,PARTICULARS,DR,CR,BAL,SOL\n01-10-2024,-,SIGMA SOFT TECH PARK STIPEND OCT,,25000.00,25000.00,001\n"
    files = {"file": ("oct_axis_statement.csv", io.BytesIO(sample_csv.encode("utf-8")), "text/csv")}
    data = {"account_id": acc.id, "bank_type": "AXIS_CSV"}
    
    import_res = client.post("/transactions/import", data=data, files=files)
    assert import_res.status_code == 200
    res_data = import_res.json()
    assert "statement_id" in res_data
    statement_id = res_data["statement_id"]
    
    # 2. List statements
    stmts_res = client.get("/statements/")
    assert stmts_res.status_code == 200
    stmts = stmts_res.json()
    assert len(stmts) >= 1
    assert any(s["id"] == statement_id for s in stmts)
    
    # 3. Download the original statement file
    dl_res = client.get(f"/statements/{statement_id}/download")
    assert dl_res.status_code == 200
    assert dl_res.content.decode("utf-8") == sample_csv
    
    # 4. Export ledger in Axis Statement format
    export_res = client.get("/statements/export/axis")
    assert export_res.status_code == 200
    export_content = export_res.content.decode("utf-8")
    assert "Tran Date,CHQNO,PARTICULARS,DR,CR,BAL,SOL" in export_content
    assert "SIGMA SOFT TECH PARK STIPEND OCT" in export_content

