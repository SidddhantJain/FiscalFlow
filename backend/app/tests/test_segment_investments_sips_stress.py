import time
import pytest
from decimal import Decimal
from datetime import date
from app.routers.sips import calculate_next_sip_date
from app.models.account import Account
from app.models.investment import Investment

def test_sip_next_date_calendar_bounding():
    """Segment 5: Validate SIP schedule day-of-month bounding across month ends (Feb 28/29, Apr 30, etc.)."""
    # 31st of month requested from Feb 1st
    next_date_feb = calculate_next_sip_date(day_of_month=31, from_date=date(2025, 2, 1))
    assert next_date_feb == date(2025, 2, 28)

    # 31st of month requested from April 1st
    next_date_apr = calculate_next_sip_date(day_of_month=31, from_date=date(2025, 4, 1))
    assert next_date_apr == date(2025, 4, 30)

    # 15th of month requested on 16th of current month -> should jump to next month
    next_date_jump = calculate_next_sip_date(day_of_month=15, from_date=date(2025, 5, 16))
    assert next_date_jump == date(2025, 6, 15)

def test_multi_broker_investments_and_analysis_engine(client, db):
    """Segment 5: Test Groww, Angel One, and Zerodha holdings aggregation and P&L calculations."""
    demat_acc = client.post("/accounts/", json={
        "name": "Groww & Angel Demat",
        "bank_name": "Groww",
        "account_type": "DEMAT",
        "opening_balance": 0.00
    }).json()

    # Add stocks and mutual funds across brokers
    holdings = [
        {"name": "Tata Consultancy Services", "symbol": "TCS", "asset_class": "EQUITY", "broker": "Groww", "units": 10.0, "purchase_price": 3500.0, "current_value": 39000.0, "account_id": demat_acc["id"]},
        {"name": "HDFC Bank Ltd", "symbol": "HDFCBANK", "asset_class": "EQUITY", "broker": "Groww", "units": 20.0, "purchase_price": 1600.0, "current_value": 34000.0, "account_id": demat_acc["id"]},
        {"name": "Nifty 50 Index Fund", "symbol": "NIFTY50", "asset_class": "MUTUAL_FUND", "broker": "Angel One", "units": 500.0, "purchase_price": 100.0, "current_value": 56000.0, "account_id": demat_acc["id"]},
        {"name": "Gold ETF", "symbol": "GOLDBEES", "asset_class": "GOLD", "broker": "Zerodha", "units": 100.0, "purchase_price": 50.0, "current_value": 5800.0, "account_id": demat_acc["id"]},
    ]
    for h in holdings:
        res = client.post("/investments/", json=h)
        assert res.status_code == 201

    analysis_res = client.get("/investments/analysis")
    assert analysis_res.status_code == 200
    data = analysis_res.json()

    total_invested = (10*3500) + (20*1600) + (500*100) + (100*50) # 35k + 32k + 50k + 5k = 122,000
    total_current = 39000 + 34000 + 56000 + 5800 # 134,800
    expected_pnl = total_current - total_invested # +12,800

    assert data["portfolio_summary"]["total_invested"] == total_invested
    assert data["portfolio_summary"]["current_value"] == total_current
    assert data["portfolio_summary"]["total_pnl"] == expected_pnl
    assert data["portfolio_summary"]["total_pnl_pct"] > 0

    # Verify broker breakdown
    assert "Groww" in data["broker_breakdown"]
    assert "Angel One" in data["broker_breakdown"]
    assert "Zerodha" in data["broker_breakdown"]

def test_sip_schedule_lifecycle_and_payment_logging(client):
    """Segment 5: Create active SIP, query projection, and log monthly payment into ledger."""
    # Create source bank account
    bank = client.post("/accounts/", json={
        "name": "SIP Mandate Bank",
        "bank_name": "HDFC",
        "account_type": "SAVINGS",
        "opening_balance": 25000.00
    }).json()

    # 1. Create monthly SIP
    sip_res = client.post("/sips/", json={
        "scheme_name": "Parag Parikh Flexi Cap Fund",
        "amount": 2500.00,
        "frequency": "MONTHLY",
        "sip_day_of_month": 10,
        "broker": "Groww",
        "target_category": "Monthly SIP Investment",
        "account_id": bank["id"]
    })
    assert sip_res.status_code == 201
    sip = sip_res.json()
    assert sip["amount"] == 2500.00

    # 2. Log SIP payment
    pay_res = client.post(f"/sips/{sip['id']}/log-payment")
    assert pay_res.status_code == 200

    # Check bank balance reduced by ₹2,500
    acc_check = client.get(f"/accounts/{bank['id']}").json()
    assert float(acc_check["current_balance"]) == 22500.00

    # 3. Check SIP wealth projections
    proj_res = client.get(f"/sips/projection?monthly_amount=2500&expected_cagr_pct=12&years=10")
    assert proj_res.status_code == 200
    proj_data = proj_res.json()
    assert proj_data["future_value"] > proj_data["total_invested"]
    assert proj_data["wealth_gain"] > 0

def test_stress_investments_analysis_50_holdings(client, db):
    """Segment 5: Stress test financial analysis calculation across 50 portfolio assets in < 250ms."""
    user_id = 1
    acc = client.post("/accounts/", json={"name": "Demat Stress", "account_type": "DEMAT", "opening_balance": 0.0}).json()

    inv_objects = []
    for i in range(50):
        inv = Investment(
            user_id=user_id,
            name=f"Stock Asset {i}",
            symbol=f"SYM{i}",
            asset_class="EQUITY" if i % 2 == 0 else "MUTUAL_FUND",
            account_id=acc["id"],
            broker="Groww" if i % 3 == 0 else "Angel One",
            units=Decimal(f"{10 + i}.0"),
            purchase_price=Decimal("200.00"),
            current_value=Decimal(f"{(10 + i) * 250}.00")
        )
        inv_objects.append(inv)
    db.add_all(inv_objects)
    db.commit()

    start_time = time.time()
    res = client.get("/investments/analysis")
    elapsed = time.time() - start_time

    assert res.status_code == 200
    assert elapsed < 0.25, f"Investment analysis took {elapsed:.3f}s (target <0.25s)"
    data = res.json()
    assert data["portfolio_summary"]["holdings_count"] >= 50
