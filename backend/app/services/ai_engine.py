import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.transaction import Transaction
from app.models.account import Account
from app.models.category import Category
from app.models.subscription import Subscription
from app.models.asset_liability import AssetLiability
from app.models.goal import Goal

# 1. TRANSACTION CATEGORIZATION RULE-BASED ENGINE
CATEGORY_KEYWORDS = {
    "Salary": ["salary", "paycheck", "employer", "wages", "direct dep"],
    "Interest": ["interest", "int.", "fd payout", "savings interest"],
    "Dividend": ["dividend", "div.", "payout stock"],
    "Refund": ["refund", "cashback", "reimbursement", "returned"],
    "Food": ["swiggy", "zomato", "restaurant", "mcdonald", "starbucks", "food", "dine", "eat", "grocery", "groceries", "supermarket", "blinkit", "zepto", "instamart"],
    "Transport": ["uber", "ola", "metro", "fuel", "petrol", "shell", "cng", "toll", "fastag"],
    "Shopping": ["amazon", "flipkart", "myntra", "shopping", "retail", "zara", "hnm", "clothing", "electronics"],
    "Entertainment": ["netflix", "spotify", "prime video", "youtube premium", "hotstar", "cinema", "movie", "bookmyshow", "gaming", "steam"],
    "Utilities": ["electricity", "broadband", "bescom", "airtel", "jio", "water bill", "gas", "recharge", "googleone", "icloud"],
    "Medical": ["hospital", "pharmacy", "medical", "doctor", "health", "apollo", "medplus", "dental"],
    "Education": ["tuition", "school", "college", "course", "udemy", "coursera", "book", "stationery"],
    "Travel": ["flight", "hotel", "irctc", "railway", "makemytrip", "airbnb", "vacation"],
    "Insurance": ["lic", "hdfc ergo", "medical insurance", "car insurance", "term insurance"],
    "Mutual Funds": ["mutual fund", "sip", "groww", "zerodha", "coin", "kuvera"],
    "Stocks": ["stocks", "shares", "angelone", "upstox", "trading"],
    "Gold": ["sovereign gold", "sgb", "jeweller", "gold coin"],
    "FD": ["fixed deposit", "recurring deposit", "fd creation", "term deposit"],
    "PPF": ["ppf deposit", "public provident"],
    "NPS": ["nps deposit", "national pension"],
    "Savings Transfer": ["transfer to savings", "savings sweep", "emergency fund deposit"]
}

def categorize_transaction_desc(desc: str) -> str:
    """
    Categorizes a transaction based on simple regex pattern matching on the description.
    """
    desc_lower = desc.lower()
    for category_name, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', desc_lower) or kw in desc_lower:
                return category_name
    return "Other"

def auto_categorize_uncategorized_transactions(db: Session, user_id: int) -> int:
    """
    Finds all uncategorized transactions for the user, runs categorization rules,
    and updates their category_id based on matched Category models.
    """
    # Load all categories for mapping
    # We will map category names to DB IDs
    categories = db.query(Category).all()
    cat_map = {c.name: c.id for c in categories}
    
    # Check if we need to create missing standard categories
    # (Just in case standard ones aren't initialized yet)
    
    # Get user transactions with no category
    accounts = db.query(Account).filter(Account.user_id == user_id).all()
    account_ids = [a.id for a in accounts]
    
    uncategorized = db.query(Transaction).filter(
        Transaction.account_id.in_(account_ids),
        Transaction.category_id.is_(None)
    ).all()
    
    updated_count = 0
    for tx in uncategorized:
        guessed_name = categorize_transaction_desc(tx.description)
        if guessed_name != "Other" and guessed_name in cat_map:
            tx.category_id = cat_map[guessed_name]
            updated_count += 1
            
    if updated_count > 0:
        db.commit()
    return updated_count


# 2. EXPENSE LEAK DETECTOR
def detect_expense_leaks(db: Session, user_id: int) -> list[dict]:
    """
    Scans transactions to find potential leakage:
    1. Repeated food delivery orders (Swiggy/Zomato)
    2. Active subscriptions with no matching transactions (Unused Subscriptions)
    3. Weekend overspending (spending on weekends significantly higher than average weekdays)
    """
    leaks = []
    accounts = db.query(Account).filter(Account.user_id == user_id).all()
    account_ids = [a.id for a in accounts]
    if not account_ids:
        return leaks
        
    thirty_days_ago = date.today() - timedelta(days=30)
    
    # Fetch all transactions from the last 30 days
    recent_txs = db.query(Transaction).filter(
        Transaction.account_id.in_(account_ids),
        Transaction.date >= thirty_days_ago
    ).all()
    
    # Heuristic 1: Repeated food delivery orders
    food_orders = [tx for tx in recent_txs if tx.type == "EXPENSE" and tx.category and tx.category.name == "Food"]
    swiggy_zomato_orders = [tx for tx in food_orders if "swiggy" in tx.description.lower() or "zomato" in tx.description.lower()]
    
    if len(swiggy_zomato_orders) >= 10:
        total_spent = sum(tx.amount for tx in swiggy_zomato_orders)
        leaks.append({
            "type": "REPEATED_FOOD",
            "title": "Frequent Food Delivery",
            "content": f"You ordered from Swiggy/Zomato {len(swiggy_zomato_orders)} times in the last 30 days, spending a total of ₹{total_spent:,.2f}.",
            "potential_savings": float(total_spent) * 0.3, # Assume 30% savings if disciplined
            "severity": "WARNING" if len(swiggy_zomato_orders) > 15 else "INFO"
        })
        
    # Heuristic 2: Unused Subscriptions
    # Find active subscriptions that do not have a matching payment transaction in the last 35 days
    subscriptions = db.query(Subscription).filter(
        Subscription.user_id == user_id,
        Subscription.is_active == True
    ).all()
    
    for sub in subscriptions:
        has_payment = False
        sub_name_words = sub.name.lower().split()
        for tx in recent_txs:
            if tx.type == "EXPENSE":
                # Match name word overlaps (e.g. Netflix, Spotify)
                if any(word in tx.description.lower() for word in sub_name_words) and abs(tx.amount - sub.amount) < (sub.amount * Decimal("0.1")):
                    has_payment = True
                    break
        if not has_payment:
            leaks.append({
                "type": "UNUSED_SUBSCRIPTION",
                "title": f"Potential Unused Subscription: {sub.name}",
                "content": f"We didn't detect any transaction matching your {sub.name} subscription (₹{sub.amount:,.2f}/{sub.billing_cycle.lower()}) in the last 30 days. You might be paying for a service you're not using.",
                "potential_savings": float(sub.amount),
                "severity": "WARNING"
            })
            
    # Heuristic 3: Weekend Overspending
    weekend_spend = Decimal("0.00")
    weekday_spend = Decimal("0.00")
    weekend_days = 0
    weekday_days = 0
    
    # Classify by weekday
    for tx in recent_txs:
        if tx.type == "EXPENSE":
            # weekday() is 0-6 (Mon-Sun)
            if tx.date.weekday() in [5, 6]:  # Sat, Sun
                weekend_spend += tx.amount
            else:
                weekday_spend += tx.amount
                
    # Calculate days in the 30-day window
    for i in range(30):
        d = date.today() - timedelta(days=i)
        if d.weekday() in [5, 6]:
            weekend_days += 1
        else:
            weekday_days += 1
            
    avg_weekend_daily = weekend_spend / weekend_days if weekend_days else Decimal("0.00")
    avg_weekday_daily = weekday_spend / weekday_days if weekday_days else Decimal("0.00")
    
    if avg_weekend_daily > avg_weekday_daily * Decimal("1.8") and weekend_spend > 2000:
        leaks.append({
            "type": "WEEKEND_OVERSPENDING",
            "title": "Weekend Spending Spike",
            "content": f"Your weekend daily spending (₹{avg_weekend_daily:,.2f}) is significantly higher than your weekday spending (₹{avg_weekday_daily:,.2f}).",
            "potential_savings": float(weekend_spend - (avg_weekday_daily * weekend_days)),
            "severity": "INFO"
        })
        
    return leaks


# 3. CASHFLOW FORECASTING
def forecast_cashflow(db: Session, user_id: int) -> dict:
    """
    Predicts:
    1. Expected Month End Balance
    2. Expected Savings
    3. Expected Deficit
    Using average daily income and expense rates from the last 60 days.
    """
    accounts = db.query(Account).filter(Account.user_id == user_id).all()
    total_current_balance = sum(a.current_balance for a in accounts)
    
    # Fetch transactions from the last 60 days to build a baseline
    sixty_days_ago = date.today() - timedelta(days=60)
    txs = db.query(Transaction).filter(
        Transaction.account_id.in_([a.id for a in accounts]),
        Transaction.date >= sixty_days_ago
    ).all()
    
    total_income = sum(tx.amount for tx in txs if tx.type == "INCOME")
    total_expense = sum(tx.amount for tx in txs if tx.type in ["EXPENSE", "TAX"])
    
    daily_income = total_income / 60
    daily_expense = total_expense / 60
    
    # Days left in this month
    today = date.today()
    if today.month == 12:
        next_month = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month = today.replace(month=today.month + 1, day=1)
    days_left = (next_month - today).days
    
    projected_income_remaining = daily_income * days_left
    projected_expense_remaining = daily_expense * days_left
    
    expected_month_end_balance = total_current_balance + projected_income_remaining - projected_expense_remaining
    expected_savings = projected_income_remaining - projected_expense_remaining
    
    return {
        "current_total_balance": float(total_current_balance),
        "days_remaining_in_month": days_left,
        "projected_income_remaining": float(projected_income_remaining),
        "projected_expense_remaining": float(projected_expense_remaining),
        "expected_month_end_balance": float(expected_month_end_balance),
        "expected_savings": float(expected_savings) if expected_savings > 0 else 0.0,
        "expected_deficit": float(abs(expected_savings)) if expected_savings < 0 else 0.0
    }


# 4. FINANCIAL HEALTH SCORING
def calculate_financial_health_score(db: Session, user_id: int) -> dict:
    """
    Calculates health score (0-100) based on:
    1. Savings Rate (25%)
    2. Emergency Fund Coverage (20%)
    3. Debt Ratio (20%)
    4. Investment Rate (20%)
    5. Spending Discipline (15%)
    """
    accounts = db.query(Account).filter(Account.user_id == user_id).all()
    account_ids = [a.id for a in accounts]
    
    # 60 day history for income/expense rates
    sixty_days_ago = date.today() - timedelta(days=60)
    txs = db.query(Transaction).filter(
        Transaction.account_id.in_(account_ids),
        Transaction.date >= sixty_days_ago
    ).all()
    
    # Calculate monthly income & expense average
    monthly_income = sum(tx.amount for tx in txs if tx.type == "INCOME") / 2
    monthly_expense = sum(tx.amount for tx in txs if tx.type == "EXPENSE") / 2
    monthly_investments = sum(tx.amount for tx in txs if tx.type == "INVESTMENT") / 2
    monthly_savings_transfers = sum(tx.amount for tx in txs if tx.type == "SAVINGS") / 2
    
    if monthly_income <= 0:
        # Avoid divide by zero
        return {"score": 50, "risk_level": "UNKNOWN", "recommendations": ["No recent income recorded. Add transactions to get your health score."]}
        
    # Metric 1: Savings Rate (25% weight)
    # Savings Rate = (Income - Expense) / Income
    savings_rate = (monthly_income - monthly_expense) / monthly_income
    # Target: 30%+ is excellent
    m1_score = min(max(float(savings_rate) / 0.3 * 100, 0.0), 100.0)
    
    # Metric 2: Emergency Fund (20% weight)
    # Calculate emergency fund total
    # Check for Account of type SAVINGS, or Goals labeled "Emergency"
    savings_balance = sum(a.current_balance for a in accounts if a.account_type in ["SAVINGS", "WALLET"])
    emergency_goals = db.query(Goal).filter(
        Goal.user_id == user_id,
        Goal.name.ilike("%emergency%")
    ).all()
    emergency_goal_funds = sum(g.current_amount for g in emergency_goals)
    
    total_emergency_fund = savings_balance + emergency_goal_funds
    monthly_avg_expense = max(monthly_expense, Decimal("10000.00")) # floor at 10k to prevent divide by zero issues
    
    months_covered = total_emergency_fund / monthly_avg_expense
    # Target: 6 months coverage
    m2_score = min(max(float(months_covered) / 6.0 * 100, 0.0), 100.0)
    
    # Metric 3: Debt Ratio (20% weight)
    # Fetch liabilities (e.g. Loans, Credit Cards)
    liabilities = db.query(AssetLiability).filter(
        AssetLiability.user_id == user_id,
        AssetLiability.type == "LIABILITY"
    ).all()
    total_debt = sum(l.value for l in liabilities)
    
    # Monthly debt servicing (assumed as 3% of total outstanding debt for scoring purposes if no specific loan payment is tracked)
    monthly_debt_payment = total_debt * Decimal("0.03")
    debt_ratio = monthly_debt_payment / monthly_income
    # Target: Debt servicing <= 15% of income
    if debt_ratio <= 0.15:
        m3_score = 100.0
    else:
        m3_score = max(100.0 - (float(debt_ratio - Decimal("0.15")) / 0.35 * 100), 0.0)
        
    # Metric 4: Investment Rate (20% weight)
    # Target: 20%+ of income invested
    investment_rate = (monthly_investments + monthly_savings_transfers) / monthly_income
    m4_score = min(max(float(investment_rate) / 0.20 * 100, 0.0), 100.0)
    
    # Metric 5: Spending Discipline (15% weight)
    # Compare expenses vs income. Overspending relative to income penalizes this
    expense_to_income = monthly_expense / monthly_income
    if expense_to_income <= 0.5:
        m5_score = 100.0
    elif expense_to_income >= 1.0:
        m5_score = 0.0
    else:
        m5_score = (1.0 - float(expense_to_income)) / 0.5 * 100
        
    # Calculate final weighted score
    final_score = int(
        m1_score * 0.25 +
        m2_score * 0.20 +
        m3_score * 0.20 +
        m4_score * 0.20 +
        m5_score * 0.15
    )
    
    if final_score >= 80:
        risk = "LOW"
    elif final_score >= 50:
        risk = "MEDIUM"
    else:
        risk = "HIGH"
        
    recs = []
    if m1_score < 60:
        recs.append("Increase your monthly savings rate by cutting down on non-essential leakages.")
    if m2_score < 70:
        recs.append(f"Build up your Emergency Fund. You currently have ~{float(months_covered):.1f} months of expenses covered. Aim for 6 months.")
    if m3_score < 80:
        recs.append("Pay off high-interest debt (like credit cards) to lower your debt-to-income ratio.")
    if m4_score < 60:
        recs.append("Set up automated mutual fund SIPs to increase your investment rate to at least 20% of your income.")
        
    if not recs:
        recs.append("Great job! Keep doing what you're doing. Your financial health is solid.")
        
    return {
        "score": final_score,
        "risk_level": risk,
        "metrics": {
            "savings_rate_score": round(m1_score, 1),
            "emergency_fund_score": round(m2_score, 1),
            "debt_ratio_score": round(m3_score, 1),
            "investment_rate_score": round(m4_score, 1),
            "spending_discipline_score": round(m5_score, 1)
        },
        "recommendations": recs
    }
