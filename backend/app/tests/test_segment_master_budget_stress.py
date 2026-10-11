import time
import pytest
from decimal import Decimal
from datetime import date
from app.models.category import Category
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.budget import Budget

def test_master_budget_initialization_and_100_percent_distribution(client):
    """Segment 4: Verify Master Budget initializes exactly ₹31,000 allocation matching user's financial plan."""
    res = client.post("/budgets/reset-master")
    assert res.status_code == 200

    summary_res = client.get("/budgets/summary")
    assert summary_res.status_code == 200
    data = summary_res.json()

    assert data["planned_income"] == 31000.00
    assert data["income_breakdown"]["Internship Stipend"] == 25000.00
    assert data["income_breakdown"]["Family Support"] == 6000.00
    assert data["total_planned_allocation"] == 31000.00

    # Ensure all 7 key line items are present
    item_names = [item["name"] for item in data["items"]]
    assert "PG Rent & Covered Meals" in item_names
    assert "Daily Office Lunch (Mon–Sat)" in item_names
    assert "BMTC Bus Commute" in item_names
    assert "Lifestyle & Personal Essentials" in item_names
    assert "Emergency Fund Allocation" in item_names
    assert "Monthly SIP Investment" in item_names
    assert "Unallocated Flex Buffer" in item_names

def test_overgrowth_detection_and_flex_buffer_calculations(client, db):
    """Segment 4: Validate that expenses exceeding line item amounts trigger is_overgrown flag."""
    client.post("/budgets/reset-master")

    # Create account and find categories
    acc = client.post("/accounts/", json={
        "name": "Budget Spend Account",
        "bank_name": "Axis Bank",
        "account_type": "SAVINGS",
        "opening_balance": 50000.00
    }).json()

    pg_cat = db.query(Category).filter(Category.name.ilike("%PG Rent%")).first()
    lunch_cat = db.query(Category).filter(Category.name.ilike("%Office Lunch%")).first()
    assert pg_cat is not None
    assert lunch_cat is not None

    today_str = date.today().isoformat()

    # 1. Spend ₹15,500 on PG Rent (budget is ₹14,000 -> OVERGROWN by ₹1,500)
    client.post("/transactions/", json={
        "date": today_str,
        "description": "PG Rent Monthly + AC Extra Charge",
        "amount": 15500.00,
        "type": "EXPENSE",
        "category_id": pg_cat.id,
        "account_id": acc["id"]
    })

    # 2. Spend ₹2,000 on Lunch (budget is ₹3,250 -> HEALTHY)
    client.post("/transactions/", json={
        "date": today_str,
        "description": "Office Meals TechPark",
        "amount": 2000.00,
        "type": "EXPENSE",
        "category_id": lunch_cat.id,
        "account_id": acc["id"]
    })

    summary = client.get("/budgets/summary").json()
    assert summary["overgrown_count"] >= 1

    pg_item = next(item for item in summary["items"] if "PG Rent" in item["name"])
    assert pg_item["is_overgrown"] is True
    assert pg_item["spent"] == 15500.00
    assert pg_item["percent_used"] > 100.0

    lunch_item = next(item for item in summary["items"] if "Office Lunch" in item["name"])
    assert lunch_item["is_overgrown"] is False
    assert lunch_item["spent"] == 2000.00
    assert lunch_item["percent_used"] < 100.0

def test_stress_budget_summary_with_200_transactions(client, db):
    """Segment 4: Stress test budget summary computation across 200 categorized transactions."""
    client.post("/budgets/reset-master")
    acc = client.post("/accounts/", json={
        "name": "Stress Budget Account",
        "bank_name": "SBI",
        "account_type": "SAVINGS",
        "opening_balance": 100000.00
    }).json()

    cats = db.query(Category).all()
    today = date.today()

    # Batch create 200 transactions
    tx_objects = []
    for i in range(200):
        c = cats[i % len(cats)]
        t = Transaction(
            date=today,
            description=f"Expense item {i}",
            amount=Decimal("150.00"),
            type=c.type,
            category_id=c.id,
            account_id=acc["id"]
        )
        tx_objects.append(t)
    db.add_all(tx_objects)
    db.commit()

    start_time = time.time()
    res = client.get("/budgets/summary")
    elapsed = time.time() - start_time

    assert res.status_code == 200
    assert elapsed < 0.25, f"Budget summary calculation took {elapsed:.3f}s (target <0.25s)"
    data = res.json()
    assert data["total_actual_spent"] > 0
