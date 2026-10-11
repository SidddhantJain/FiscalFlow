import time
import pytest
from decimal import Decimal
from datetime import date
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.category import Category
from app.models.investment import Investment
from app.models.asset_liability import AssetLiability
from app.services.ai_engine import calculate_financial_health_score, forecast_cashflow

def test_net_worth_engine_assets_and_liabilities(client, db):
    """Segment 6: Validate Net Worth aggregation across liquid banks, investments, and credit card debts."""
    user_id = 1
    
    # 1. Bank account with positive balance
    acc_bank = Account(user_id=user_id, name="Savings", bank_name="SBI", account_type="SAVINGS", current_balance=50000.0)
    # 2. Credit Card with debt (-15,000 balance)
    acc_cc = Account(user_id=user_id, name="Amazon Pay ICICI", bank_name="ICICI", account_type="CREDIT_CARD", current_balance=-15000.0)
    db.add_all([acc_bank, acc_cc])
    db.commit()

    # 3. Investment with current value 30,000
    inv = Investment(user_id=user_id, name="PPF Account", symbol="PPF", asset_class="FIXED_INCOME", units=Decimal("1"), purchase_price=Decimal("25000"), current_value=Decimal("30000"))
    db.add(inv)
    
    # 4. Asset Liability (Physical Asset: 20,000 Laptop, Loan Liability: 5,000 Personal Loan)
    laptop = AssetLiability(user_id=user_id, name="MacBook", type="ASSET", category="ELECTRONICS", value=Decimal("20000"), as_of_date=date.today())
    loan = AssetLiability(user_id=user_id, name="Student Loan", type="LIABILITY", category="PERSONAL_LOAN", value=Decimal("5000"), as_of_date=date.today())
    db.add_all([laptop, loan])
    db.commit()

    res = client.get("/reports/net-worth")
    assert res.status_code == 200
    data = res.json()

    # Total Assets = Liquid (50k) + Investments (30k) + Physical (20k) = 100k
    assert data["total_assets"] == 100000.0
    # Total Liabilities = CC Debt (15k) + Loan (5k) = 20k
    assert data["total_liabilities"] == 20000.0
    # Net Worth = 100k - 20k = 80k
    assert data["net_worth"] == 80000.0

def test_indian_financial_year_quarterly_report_and_80c_cap(client, db):
    """Segment 6: Validate FY 2024-25 quarterly partitioning (Q1..Q4) and Section 80C capping at ₹1,50,000."""
    user_id = 1
    acc = Account(user_id=user_id, name="Salary Bank", bank_name="Axis", account_type="SALARY", current_balance=100000.0)
    db.add(acc)
    db.commit()

    # Transactions in each FY 2024-25 quarter
    tx_q1 = Transaction(date=date(2024, 5, 10), description="Q1 Stipend", amount=Decimal("25000.00"), type="INCOME", account_id=acc.id)
    tx_q2 = Transaction(date=date(2024, 8, 15), description="Q2 Stipend", amount=Decimal("25000.00"), type="INCOME", account_id=acc.id)
    tx_q3 = Transaction(date=date(2024, 11, 20), description="Q3 Stipend", amount=Decimal("25000.00"), type="INCOME", account_id=acc.id)
    tx_q4 = Transaction(date=date(2025, 2, 25), description="Q4 Stipend", amount=Decimal("25000.00"), type="INCOME", account_id=acc.id)

    # Tax 80C Investment: ₹180,000 in ELSS Mutual Funds (exceeds ₹1.5L cap)
    elss_cat = db.query(Category).filter(Category.name.ilike("%Mutual Funds%")).first()
    tx_elss = Transaction(date=date(2025, 1, 5), description="ELSS Tax Saver Fund", amount=Decimal("180000.00"), type="INVESTMENT", category_id=elss_cat.id, account_id=acc.id)

    db.add_all([tx_q1, tx_q2, tx_q3, tx_q4, tx_elss])
    db.commit()

    res = client.get("/reports/financial-year/FY 2024-25")
    assert res.status_code == 200
    report = res.json()

    assert report["quarters"]["Q1"]["income"] == 25000.0
    assert report["quarters"]["Q2"]["income"] == 25000.0
    assert report["quarters"]["Q3"]["income"] == 25000.0
    assert report["quarters"]["Q4"]["income"] == 25000.0
    assert report["summary"]["total_income"] == 100000.0

    # Verify statutory 80C deductions capped at ₹150,000
    assert report["statutory_capped_80c_deduction"] == 150000.0

def test_financial_health_score_zero_income_resilience(db):
    """Segment 6: Validate financial health score algorithm resilience against edge case of zero income or negative balance."""
    user_id = 1
    # User with zero accounts and zero income
    health = calculate_financial_health_score(db, user_id=user_id)
    assert health is not None
    assert "score" in health
    assert 0 <= health["score"] <= 100
    assert health["risk_level"] in ["LOW", "MODERATE", "HIGH", "CRITICAL", "UNKNOWN"]

def test_stress_reports_and_insights_with_100_transactions(client, db):
    """Segment 6: Stress test report generation across 100 transactions in < 200ms."""
    user_id = 1
    acc = Account(user_id=user_id, name="Report Stress Acc", bank_name="HDFC", account_type="SAVINGS", current_balance=50000.0)
    db.add(acc)
    db.commit()

    txs = []
    for i in range(100):
        m = (i % 12) + 1
        y = 2024 if m >= 4 else 2025
        t = Transaction(
            date=date(y, m, (i % 28) + 1),
            description=f"Transaction {i}",
            amount=Decimal("500.00"),
            type="INCOME" if i % 2 == 0 else "EXPENSE",
            account_id=acc.id
        )
        txs.append(t)
    db.add_all(txs)
    db.commit()

    start_time = time.time()
    res = client.get("/reports/financial-year/FY 2024-25")
    elapsed = time.time() - start_time

    assert res.status_code == 200
    assert elapsed < 0.20, f"FY Report calculation took {elapsed:.3f}s (target <0.20s)"
