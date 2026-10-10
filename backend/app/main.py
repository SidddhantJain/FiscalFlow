from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
from app.database import engine, Base, SessionLocal
from app.models.user import User
from app.models.category import Category
from app.routers import accounts, transactions, budgets, goals, subscriptions, investments, reports, insights

from datetime import date, datetime, timedelta
from sqlalchemy import text
from app.models.budget import Budget

# Initialize Database schemas
Base.metadata.create_all(bind=engine)

def run_sqlite_migrations():
    """Applies non-destructive schema migrations for SQLite."""
    with engine.connect() as conn:
        # 1. Check transactions table for 'tags' column
        result = conn.execute(text("PRAGMA table_info(transactions)")).fetchall()
        column_names = [row[1] for row in result]
        if "tags" not in column_names:
            conn.execute(text("ALTER TABLE transactions ADD COLUMN tags VARCHAR"))
            conn.commit()

        # 2. Check budgets table for 'name' and 'notes' columns
        b_result = conn.execute(text("PRAGMA table_info(budgets)")).fetchall()
        b_cols = [row[1] for row in b_result]
        if "name" not in b_cols:
            conn.execute(text("ALTER TABLE budgets ADD COLUMN name VARCHAR"))
            conn.commit()
        if "notes" not in b_cols:
            conn.execute(text("ALTER TABLE budgets ADD COLUMN notes VARCHAR"))
            conn.commit()

# Run migration check
run_sqlite_migrations()

# Seed database with default local user and Master Budget categories
def seed_database():
    db = SessionLocal()
    try:
        # Check and seed default user
        default_user = db.query(User).first()
        if not default_user:
            default_user = User(
                name="Local User",
                email="local@fiscalflow.internal",
                currency="INR"
            )
            db.add(default_user)
            db.commit()
            db.refresh(default_user)
            
        # Seed standard Indian & Master Budget categories
        standard_categories = [
            # Master Budget Income
            ("Internship Stipend", "INCOME"),
            ("Family Support", "INCOME"),
            ("Salary", "INCOME"),
            ("Interest", "INCOME"),
            ("Dividend", "INCOME"),
            ("Refund", "INCOME"),
            # Master Budget Expenses & Allocations
            ("PG Rent & Covered Meals", "EXPENSE"),
            ("Daily Office Lunch (Mon–Sat)", "EXPENSE"),
            ("BMTC Bus Commute", "EXPENSE"),
            ("Lifestyle & Personal Essentials", "EXPENSE"),
            ("Unallocated Flex Buffer", "EXPENSE"),
            # Standard Expenses
            ("Food", "EXPENSE"),
            ("Transport", "EXPENSE"),
            ("Shopping", "EXPENSE"),
            ("Entertainment", "EXPENSE"),
            ("Utilities", "EXPENSE"),
            ("Medical", "EXPENSE"),
            ("Education", "EXPENSE"),
            ("Travel", "EXPENSE"),
            ("Insurance", "EXPENSE"),
            # Master Budget Investments & Savings
            ("Monthly SIP Investment", "INVESTMENT"),
            ("Emergency Fund Allocation", "SAVINGS"),
            # Standard Investments & Savings
            ("Mutual Funds", "INVESTMENT"),
            ("Stocks", "INVESTMENT"),
            ("Gold", "INVESTMENT"),
            ("FD", "INVESTMENT"),
            ("PPF", "INVESTMENT"),
            ("NPS", "INVESTMENT"),
            ("Savings Transfer", "SAVINGS")
        ]
        
        for name, cat_type in standard_categories:
            exists = db.query(Category).filter(
                Category.name == name,
                Category.type == cat_type
            ).first()
            if not exists:
                new_cat = Category(name=name, type=cat_type, user_id=None)
                db.add(new_cat)
        db.commit()

        # Seed initial default Master Budget if no budgets exist for default user
        user_budgets = db.query(Budget).filter(Budget.user_id == default_user.id).count()
        if user_budgets == 0:
            today = date.today()
            start_date = today.replace(day=1)
            if today.month == 12:
                end_date = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_date = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

            master_budget_items = [
                ("PG Rent & Covered Meals", 14000.00, "Breakfast & dinner daily, Saturday full meals, Sunday breakfast."),
                ("Daily Office Lunch (Mon–Sat)", 3250.00, "26 working days @ ₹100–150/day in/near Sigma Soft Tech Park."),
                ("BMTC Bus Commute", 1000.00, "Daily bus fares between Varthur Kodi and Kundalahalli Gate."),
                ("Lifestyle & Personal Essentials", 3500.00, "Sunday meals, mobile recharge, toiletries, laundry supplies."),
                ("Emergency Fund Allocation", 2750.00, "Built up monthly in your liquid bank savings."),
                ("Monthly SIP Investment", 5500.00, "Capped fixed wealth-building auto-investment."),
                ("Unallocated Flex Buffer", 1000.00, "Extra cash left untouched in your bank account.")
            ]

            for cat_name, amt, notes in master_budget_items:
                cat = db.query(Category).filter(Category.name == cat_name).first()
                if cat:
                    b = Budget(
                        user_id=default_user.id,
                        category_id=cat.id,
                        amount=amt,
                        spent=0.00,
                        start_date=start_date,
                        end_date=end_date,
                        name=cat_name,
                        notes=notes
                    )
                    db.add(b)
            db.commit()
    finally:
        db.close()

# Run database seeder
seed_database()

app = FastAPI(
    title="FiscalFlow API",
    description="Personal Financial Management & Analysis Platform focused on the Indian financial ecosystem.",
    version="1.0.0"
)

# Enable CORS for React + Typescript frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(accounts.router)
app.include_router(transactions.router)
app.include_router(budgets.router)
app.include_router(goals.router)
app.include_router(subscriptions.router)
app.include_router(investments.router)
app.include_router(reports.router)
app.include_router(insights.router)

# Mount frontend static files directory
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/", response_class=HTMLResponse)
def read_root():
    index_file = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>FiscalFlow Frontend not found</h1><p>Ensure index.html is in the frontend folder.</p>")
