from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base, SessionLocal
from app.models.user import User
from app.models.category import Category
from app.routers import accounts, transactions, budgets, goals, subscriptions, investments, reports, insights

# Initialize Database schemas
Base.metadata.create_all(bind=engine)

# Seed database with default local user and standard Indian finance categories
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
            
        # Seed standard Indian/common categories
        standard_categories = [
            # Income
            ("Salary", "INCOME"),
            ("Interest", "INCOME"),
            ("Dividend", "INCOME"),
            ("Refund", "INCOME"),
            # Expense
            ("Food", "EXPENSE"),
            ("Transport", "EXPENSE"),
            ("Shopping", "EXPENSE"),
            ("Entertainment", "EXPENSE"),
            ("Utilities", "EXPENSE"),
            ("Medical", "EXPENSE"),
            ("Education", "EXPENSE"),
            ("Travel", "EXPENSE"),
            ("Insurance", "EXPENSE"),
            # Investments
            ("Mutual Funds", "INVESTMENT"),
            ("Stocks", "INVESTMENT"),
            ("Gold", "INVESTMENT"),
            ("FD", "INVESTMENT"),
            ("PPF", "INVESTMENT"),
            ("NPS", "INVESTMENT"),
            # Savings
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

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Welcome to FiscalFlow API Engine",
        "currency": "INR",
        "local_time": "2026-06-17T14:09:07+05:30"
    }
