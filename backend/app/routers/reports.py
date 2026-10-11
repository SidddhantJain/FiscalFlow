from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime
from decimal import Decimal
from app.database import get_db
from app.models.account import Account
from app.models.investment import Investment
from app.models.asset_liability import AssetLiability
from app.models.transaction import Transaction
from app.routers.accounts import get_default_user_id
from app.services.ai_engine import forecast_cashflow, calculate_financial_health_score
from app.services.tax_engine import compare_tax_regimes, compute_new_regime_tax

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("/net-worth")
def get_net_worth(db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    """
    Calculates Net Worth = Assets - Liabilities.
    Assets = Bank accounts (Savings, Salary, Cash, Wallet) + Investments current value + Physical Assets.
    Liabilities = Credit Card debt + Loans (Home, Personal, Vehicle, etc.).
    """
    # 1. Accounts
    accounts = db.query(Account).filter(Account.user_id == user_id).all()
    liquid_assets = Decimal("0.00")
    credit_card_debt = Decimal("0.00")
    
    for acc in accounts:
        if acc.account_type == "CREDIT_CARD":
            if acc.current_balance < 0:
                credit_card_debt += abs(acc.current_balance)
        else:
            if acc.current_balance > 0:
                liquid_assets += acc.current_balance
            else:
                credit_card_debt += abs(acc.current_balance)
                
    # 2. Investments
    investments = db.query(Investment).filter(Investment.user_id == user_id).all()
    investment_assets = sum(inv.current_value for inv in investments)
    
    # 3. Physical Assets and Loans
    assets_liabilities = db.query(AssetLiability).filter(AssetLiability.user_id == user_id).all()
    physical_assets = sum(item.value for item in assets_liabilities if item.type == "ASSET")
    loan_liabilities = sum(item.value for item in assets_liabilities if item.type == "LIABILITY")
    
    total_assets = liquid_assets + investment_assets + physical_assets
    total_liabilities = credit_card_debt + loan_liabilities
    net_worth = total_assets - total_liabilities
    
    return {
        "net_worth": float(net_worth),
        "total_assets": float(total_assets),
        "total_liabilities": float(total_liabilities),
        "breakdown": {
            "liquid_assets": float(liquid_assets),
            "investments": float(investment_assets),
            "physical_assets": float(physical_assets),
            "credit_card_debt": float(credit_card_debt),
            "loans": float(loan_liabilities)
        }
    }

@router.get("/financial-year/{fy_label}")
def get_financial_year_report(fy_label: str, db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    """
    Generates report for an Indian Financial Year (e.g., 'FY 2024-25').
    Indian FY 2024-25 is April 1, 2024 to March 31, 2025.
    Summarizes quarterly income, expenses, and potential tax savings (80C/80D investments).
    """
    try:
        parts = fy_label.replace("FY", "").strip().split("-")
        start_year = int(parts[0].strip())
        if len(parts[1]) == 2:
            end_year = (start_year // 100) * 100 + int(parts[1].strip())
        else:
            end_year = int(parts[1].strip())
    except Exception:
        today = date.today()
        start_year = today.year - 1 if today.month < 4 else today.year
        end_year = start_year + 1
        fy_label = f"FY {start_year}-{str(end_year)[-2:]}"
        
    start_date = date(start_year, 4, 1)
    end_date = date(end_year, 3, 31)
    
    accounts = db.query(Account).filter(Account.user_id == user_id).all()
    account_ids = [a.id for a in accounts]
    
    txs = db.query(Transaction).filter(
        Transaction.account_id.in_(account_ids),
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).all()
    
    quarters = {
        "Q1": {"income": Decimal("0.00"), "expense": Decimal("0.00"), "savings": Decimal("0.00"), "investment": Decimal("0.00")},
        "Q2": {"income": Decimal("0.00"), "expense": Decimal("0.00"), "savings": Decimal("0.00"), "investment": Decimal("0.00")},
        "Q3": {"income": Decimal("0.00"), "expense": Decimal("0.00"), "savings": Decimal("0.00"), "investment": Decimal("0.00")},
        "Q4": {"income": Decimal("0.00"), "expense": Decimal("0.00"), "savings": Decimal("0.00"), "investment": Decimal("0.00")}
    }
    
    investments_80c = Decimal("0.00")
    investments_nps_80ccd1b = Decimal("0.00")
    investments_80d = Decimal("0.00")
    
    for tx in txs:
        m = tx.date.month
        if m in [4, 5, 6]:
            q = "Q1"
        elif m in [7, 8, 9]:
            q = "Q2"
        elif m in [10, 11, 12]:
            q = "Q3"
        else:
            q = "Q4"
            
        t = tx.type.upper()
        if t == "INCOME":
            quarters[q]["income"] += tx.amount
        elif t == "EXPENSE":
            quarters[q]["expense"] += tx.amount
        elif t == "SAVINGS":
            quarters[q]["savings"] += tx.amount
        elif t == "INVESTMENT":
            quarters[q]["investment"] += tx.amount
            cname = (tx.category.name if tx.category else "").upper()
            if any(k in cname for k in ["PPF", "ELSS", "LIFE INSURANCE", "MUTUAL FUNDS", "PF"]):
                investments_80c += tx.amount
            elif "NPS" in cname:
                investments_nps_80ccd1b += tx.amount
            elif any(k in cname for k in ["HEALTH", "MEDICAL"]):
                investments_80d += tx.amount
                
    q_out = {}
    for q, vals in quarters.items():
        q_out[q] = {k: float(v) for k, v in vals.items()}
        
    total_income = float(sum(quarters[q]["income"] for q in quarters))
    total_expense = float(sum(quarters[q]["expense"] for q in quarters))
    total_savings = float(sum(quarters[q]["savings"] for q in quarters))
    total_investments = float(sum(quarters[q]["investment"] for q in quarters))

    # Statutory Indian Tax Calculations
    tax_comparison = compare_tax_regimes(
        gross_income=total_income,
        deductions_80c=float(investments_80c),
        deductions_80d=float(investments_80d),
        deductions_nps_80ccd1b=float(investments_nps_80ccd1b),
        is_salaried=True
    )
        
    return {
        "financial_year": fy_label,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "quarters": q_out,
        "summary": {
            "total_income": total_income,
            "total_expense": total_expense,
            "total_savings": total_savings,
            "total_investments": total_investments
        },
        "tax_savings_deductions_80c_80d": float(investments_80c + investments_80d + investments_nps_80ccd1b),
        "statutory_capped_80c_deduction": min(float(investments_80c), 150000.0),
        "statutory_tax_computation": tax_comparison
    }

@router.get("/forecast")
def get_cashflow_forecast(db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    return forecast_cashflow(db, user_id)

@router.get("/health-score")
def get_health_score(db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    return calculate_financial_health_score(db, user_id)
