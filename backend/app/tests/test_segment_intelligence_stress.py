import time
import pytest
from datetime import date, timedelta
from decimal import Decimal
from app.services.transfer_engine import detect_and_link_transfers
from app.services.ai_engine import (
    extract_transaction_tags, 
    learn_user_tag_rule, 
    auto_categorize_uncategorized_transactions,
    CATEGORY_KEYWORDS
)
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.tag_rule import UserTagRule

def test_transfer_matching_window_and_account_rules(db):
    """Segment 3: Validate O(N) transfer matcher across 2-day windows, same-account exclusions, and SAVINGS destinations."""
    user_id = 1
    
    # Create 3 accounts: Current (Checking), Salary, and Liquid Savings
    acc_checking = Account(user_id=user_id, name="Checking Account", bank_name="HDFC", account_type="CURRENT", current_balance=50000.0)
    acc_salary = Account(user_id=user_id, name="Salary Account", bank_name="Axis", account_type="SALARY", current_balance=80000.0)
    acc_savings = Account(user_id=user_id, name="Emergency Savings", bank_name="SBI", account_type="SAVINGS", current_balance=10000.0)
    db.add_all([acc_checking, acc_salary, acc_savings])
    db.commit()

    base_date = date(2025, 9, 10)

    # 1. Valid transfer between checking and salary (1 day apart, same amount 5000)
    tx1_debit = Transaction(date=base_date, description="Transfer to Axis", amount=Decimal("5000.00"), type="EXPENSE", account_id=acc_checking.id)
    tx1_credit = Transaction(date=base_date + timedelta(days=1), description="NEFT from HDFC", amount=Decimal("5000.00"), type="INCOME", account_id=acc_salary.id)

    # 2. Valid transfer to SAVINGS account (same day, amount 10000) -> should become type 'SAVINGS'
    tx2_debit = Transaction(date=base_date, description="Sweep to Emergency Fund", amount=Decimal("10000.00"), type="EXPENSE", account_id=acc_salary.id)
    tx2_credit = Transaction(date=base_date, description="Sweep Inflow", amount=Decimal("10000.00"), type="INCOME", account_id=acc_savings.id)

    # 3. Invalid transfer: outside 2-day window (5 days apart) -> should NOT match
    tx3_debit = Transaction(date=base_date, description="Old transfer", amount=Decimal("2000.00"), type="EXPENSE", account_id=acc_checking.id)
    tx3_credit = Transaction(date=base_date + timedelta(days=6), description="Late credit", amount=Decimal("2000.00"), type="INCOME", account_id=acc_salary.id)

    # 4. Invalid transfer: debit and credit within SAME account -> should NOT match
    tx4_debit = Transaction(date=base_date, description="Internal adjustment debit", amount=Decimal("1500.00"), type="EXPENSE", account_id=acc_checking.id)
    tx4_credit = Transaction(date=base_date, description="Internal adjustment credit", amount=Decimal("1500.00"), type="INCOME", account_id=acc_checking.id)

    db.add_all([tx1_debit, tx1_credit, tx2_debit, tx2_credit, tx3_debit, tx3_credit, tx4_debit, tx4_credit])
    db.commit()

    # Run transfer heuristic matcher
    matched_count = detect_and_link_transfers(db, user_id=user_id, days_window=2)
    assert matched_count == 2, f"Expected exactly 2 matched transfers, got {matched_count}"

    # Verify tx1 became TRANSFER
    db.refresh(tx1_debit)
    assert tx1_debit.type == "TRANSFER"
    assert tx1_debit.destination_account_id == acc_salary.id

    # Verify tx2 became SAVINGS
    db.refresh(tx2_debit)
    assert tx2_debit.type == "SAVINGS"
    assert tx2_debit.destination_account_id == acc_savings.id

    # Verify tx3 and tx4 debits remained unchanged
    db.refresh(tx3_debit)
    assert tx3_debit.type == "EXPENSE"
    db.refresh(tx4_debit)
    assert tx4_debit.type == "EXPENSE"

def test_stress_transfer_matching_100_pairs(db):
    """Segment 3: Stress test transfer detection with 100 concurrent transfer pairs in < 500ms."""
    user_id = 1
    acc_a = Account(user_id=user_id, name="Batch Account A", bank_name="HDFC", account_type="CURRENT", current_balance=500000.0)
    acc_b = Account(user_id=user_id, name="Batch Account B", bank_name="ICICI", account_type="CURRENT", current_balance=500000.0)
    db.add_all([acc_a, acc_b])
    db.commit()

    txs = []
    base_date = date(2025, 1, 1)
    for i in range(1, 101):
        dt = base_date + timedelta(days=i % 60)
        amt = Decimal(f"{1000 + i}.00")
        tx_debit = Transaction(date=dt, description=f"Debit Transfer {i}", amount=amt, type="EXPENSE", account_id=acc_a.id)
        tx_credit = Transaction(date=dt, description=f"Credit Inflow {i}", amount=amt, type="INCOME", account_id=acc_b.id)
        txs.extend([tx_debit, tx_credit])

    db.add_all(txs)
    db.commit()

    start_time = time.time()
    matched = detect_and_link_transfers(db, user_id=user_id, days_window=2)
    elapsed = time.time() - start_time

    assert matched == 100, f"Expected 100 matched pairs, got {matched}"
    assert elapsed < 0.5, f"Transfer matching for 100 pairs took {elapsed:.3f}s (target <0.5s)"

def test_ai_rule_learning_and_repetitive_task_reducer(db):
    """Segment 3: Test user tag learning and automated propagation to 50 new merchant transactions."""
    user_id = 1
    acc = Account(user_id=user_id, name="Tag Test Account", bank_name="SBI", account_type="SAVINGS", current_balance=10000.0)
    db.add(acc)
    db.commit()

    # User manually tags a merchant
    sample_desc = "ChaiPoint"
    tags_to_learn = "Food, Chai, Office Canteen"
    rule = learn_user_tag_rule(db, user_id=user_id, description=sample_desc, tags=tags_to_learn)
    assert rule is not None
    assert rule.pattern == "chaipoint"

    # Now create 50 incoming transactions containing the keyword
    incoming_txs = []
    for i in range(50):
        t = Transaction(
            date=date(2025, 8, (i % 28) + 1),
            description=f"UPI/998877{i}/ChaiPoint TechPark/{i}",
            amount=Decimal("120.00"),
            type="EXPENSE",
            account_id=acc.id
        )
        incoming_txs.append(t)
    db.add_all(incoming_txs)
    db.commit()

    # Run auto-categorization and tag propagation
    start_time = time.time()
    updated_count = auto_categorize_uncategorized_transactions(db, user_id=user_id)
    elapsed = time.time() - start_time

    assert updated_count == 50
    assert elapsed < 0.5

    # Verify all 50 inherited the learned tags!
    for t in incoming_txs:
        db.refresh(t)
        assert t.tags is not None
        assert "Chai" in t.tags
        assert "Food" in t.tags
