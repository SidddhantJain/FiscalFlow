import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.database import get_db
from app.main import app

# Explicitly import all models to register them in Base.metadata
from app.models import (
    Base, User, Account, Category, Transaction, Budget, 
    Goal, Subscription, Investment, AssetLiability, Receipt, 
    FinancialYear, Insight
)

# File-based SQLite for reliable multi-threaded test access
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    # Clean up any residual test database
    if os.path.exists("./test.db"):
        try:
            os.remove("./test.db")
        except OSError:
            pass
            
    # Create all tables registered in Base.metadata
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    
    # Seed default test user
    user = User(
        name="Test User",
        email="test@fiscalflow.internal",
        currency="INR"
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    # Seed master categories
    standard_categories = [
        ("Internship Stipend", "INCOME"),
        ("Family Support", "INCOME"),
        ("Salary", "INCOME"),
        ("PG Rent & Covered Meals", "EXPENSE"),
        ("Daily Office Lunch (Mon–Sat)", "EXPENSE"),
        ("BMTC Bus Commute", "EXPENSE"),
        ("Lifestyle & Personal Essentials", "EXPENSE"),
        ("Unallocated Flex Buffer", "EXPENSE"),
        ("Food", "EXPENSE"),
        ("Transport", "EXPENSE"),
        ("Shopping", "EXPENSE"),
        ("Entertainment", "EXPENSE"),
        ("Utilities", "EXPENSE"),
        ("Medical", "EXPENSE"),
        ("Education", "EXPENSE"),
        ("Travel", "EXPENSE"),
        ("Insurance", "EXPENSE"),
        ("Monthly SIP Investment", "INVESTMENT"),
        ("Emergency Fund Allocation", "SAVINGS"),
        ("Mutual Funds", "INVESTMENT"),
        ("Stocks", "INVESTMENT"),
        ("Savings Transfer", "SAVINGS")
    ]
    for name, cat_type in standard_categories:
        cat = Category(name=name, type=cat_type, user_id=None)
        session.add(cat)
    session.commit()
    
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        
        # Clean up database file after run
        if os.path.exists("./test.db"):
            try:
                os.remove("./test.db")
            except OSError:
                pass

@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
