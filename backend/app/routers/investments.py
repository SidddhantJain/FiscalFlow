import os
import shutil
from datetime import datetime, date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from app.database import get_db, utc_now
from app.models.investment import Investment
from app.models.account import Account
from app.models.statement_file import StatementFile
from app.models.sip import SipSchedule
from app.models.budget import Budget
from app.schemas.investment import Investment as InvestmentSchema, InvestmentCreate, InvestmentUpdate
from app.routers.accounts import get_default_user_id
from app.services.statement_import import import_demat_holdings
from app.services.tax_engine import compute_capital_gains_tax

router = APIRouter(prefix="/investments", tags=["Investments"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "statements")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/", response_model=InvestmentSchema, status_code=status.HTTP_201_CREATED)
def create_investment(inv: InvestmentCreate, db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    db_inv = Investment(
        user_id=user_id,
        name=inv.name,
        symbol=inv.symbol,
        asset_class=inv.asset_class,
        account_id=inv.account_id,
        broker=inv.broker,
        units=inv.units,
        purchase_price=inv.purchase_price,
        current_value=inv.current_value,
        buy_date=inv.buy_date or utc_now(),
        last_updated=utc_now()
    )
    db.add(db_inv)
    db.commit()
    db.refresh(db_inv)
    return db_inv

@router.get("/", response_model=list[InvestmentSchema])
def list_investments(db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    return db.query(Investment).filter(Investment.user_id == user_id).all()

@router.get("/analysis", response_model=dict)
def get_financial_analysis(db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    """
    Comprehensive financial analysis tool: portfolio valuation, stock holdings, P&L,
    broker-wise distribution (Groww, Angel One, Zerodha), and SIP schedule alignment.
    """
    investments = db.query(Investment).filter(Investment.user_id == user_id).all()
    sips = db.query(SipSchedule).filter(SipSchedule.user_id == user_id).all()
    accounts = db.query(Account).filter(Account.user_id == user_id).all()
    
    total_invested = Decimal("0.00")
    total_current_value = Decimal("0.00")
    holdings_list = []
    asset_breakdown = {}
    broker_breakdown = {}
    
    for inv in investments:
        units = Decimal(str(inv.units or 1.0))
        # Total cost
        cost = inv.purchase_price * units if inv.units else inv.purchase_price
        curr = inv.current_value
        pnl = curr - cost
        pnl_pct = float((pnl / cost * 100) if cost > 0 else 0)
        
        total_invested += cost
        total_current_value += curr
        
        # Asset class grouping
        ac = inv.asset_class or "STOCK"
        asset_breakdown[ac] = float(Decimal(str(asset_breakdown.get(ac, 0.0))) + curr)
        
        # Broker grouping
        brk = inv.broker or "Direct / Unassigned"
        broker_breakdown[brk] = float(Decimal(str(broker_breakdown.get(brk, 0.0))) + curr)
        
        holdings_list.append({
            "id": inv.id,
            "name": inv.name,
            "symbol": inv.symbol or inv.name[:6].upper(),
            "asset_class": inv.asset_class,
            "broker": inv.broker or "Groww",
            "units": float(inv.units) if inv.units else None,
            "purchase_price": float(inv.purchase_price),
            "current_value": float(inv.current_value),
            "total_invested": float(cost),
            "pnl": float(pnl),
            "pnl_pct": round(pnl_pct, 2),
            "buy_date": inv.buy_date.strftime("%Y-%m-%d") if inv.buy_date else None,
            "last_updated": inv.last_updated.strftime("%Y-%m-%d") if inv.last_updated else None
        })
        
    total_pnl = total_current_value - total_invested
    total_pnl_pct = float((total_pnl / total_invested * 100) if total_invested > 0 else 0)
    
    # Calculate % allocation per holding
    for h in holdings_list:
        h["allocation_pct"] = round((h["current_value"] / float(total_current_value) * 100) if total_current_value > 0 else 0, 1)
        
    # SIP Metrics & Master Budget Alignment
    total_monthly_sip = sum([Decimal(str(s.amount)) for s in sips if s.status == "ACTIVE"])
    master_sip_target = Decimal("5500.00")  # Final Master Budget allocation target
    sip_alignment_pct = round(float((total_monthly_sip / master_sip_target * 100) if master_sip_target > 0 else 0), 1)
    
    # Upcoming SIP timeline
    today = date.today()
    upcoming_sips = []
    for s in sips:
        days_left = (s.next_sip_date - today).days if s.next_sip_date else 0
        upcoming_sips.append({
            "id": s.id,
            "scheme_name": s.scheme_name,
            "amount": float(s.amount),
            "sip_day": s.sip_day_of_month,
            "next_date": s.next_sip_date.isoformat() if s.next_sip_date else None,
            "days_left": days_left,
            "broker": s.broker,
            "status": s.status
        })
    upcoming_sips.sort(key=lambda x: x["days_left"])
    
    # Liquid vs Investment ratio
    liquid_cash = sum([Decimal(str(a.current_balance)) for a in accounts if a.account_type in ["SAVINGS", "SALARY", "WALLET", "CASH"]])
    total_wealth = total_current_value + liquid_cash
    
    # Statutory Capital Gains Analysis (Finance Act 2024: STCG @ 20%, LTCG @ 12.5% with ₹1.25L exemption)
    capital_gains = compute_capital_gains_tax(holdings_list)

    return {
        "portfolio_summary": {
            "total_invested": float(total_invested),
            "current_value": float(total_current_value),
            "total_pnl": float(total_pnl),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "liquid_cash": float(liquid_cash),
            "total_net_wealth": float(total_wealth),
            "cagr_estimate_pct": 14.8,  # Indicative Indian equity long-term benchmark
            "holdings_count": len(holdings_list)
        },
        "capital_gains_tax": capital_gains,
        "sip_analytics": {
            "monthly_committed_sip": float(total_monthly_sip),
            "master_budget_target": float(master_sip_target),
            "sip_alignment_pct": sip_alignment_pct,
            "active_sips_count": len([s for s in sips if s.status == "ACTIVE"]),
            "upcoming_sips": upcoming_sips
        },
        "asset_allocation": asset_breakdown,
        "broker_breakdown": broker_breakdown,
        "holdings": holdings_list
    }

@router.post("/import-demat", response_model=dict)
async def import_demat_statement(
    file: UploadFile = File(...),
    account_id: int = Form(...),
    broker_type: str = Form("GROWW_DEMAT"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_default_user_id)
):
    """
    Imports Demat statements (Groww, Angel One, Zerodha, Generic) and persists statement file.
    """
    account = db.query(Account).filter(Account.id == account_id, Account.user_id == user_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Selected Demat/Investment account not found")
        
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty statement file provided")
        
    # Save file persistently to uploads/statements/
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_name = os.path.basename(file.filename)
    unique_filename = f"demat_{timestamp}_{clean_name}"
    saved_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    with open(saved_path, "wb") as f:
        f.write(contents)
        
    # Parse & import holdings and transactions
    result = import_demat_holdings(db, user_id, account_id, contents, file.filename, broker_type)
    
    # Record in StatementFile
    stmt_file = StatementFile(
        user_id=user_id,
        account_id=account_id,
        filename=file.filename,
        saved_filename=unique_filename,
        file_size=len(contents),
        bank_type=broker_type,
        transaction_count=result["imported_transactions"] + result["imported_holdings"],
        upload_date=utc_now()
    )
    db.add(stmt_file)
    db.commit()
    db.refresh(stmt_file)
    
    return {
        "message": f"Demat statement processed successfully: {result['imported_holdings']} holdings and {result['imported_transactions']} transactions updated!",
        "statement_file_id": stmt_file.id,
        "holdings_count": result["imported_holdings"],
        "transactions_count": result["imported_transactions"]
    }

@router.put("/{inv_id}", response_model=InvestmentSchema)
def update_investment(inv_id: int, inv_update: InvestmentUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    db_inv = db.query(Investment).filter(Investment.id == inv_id, Investment.user_id == user_id).first()
    if not db_inv:
        raise HTTPException(status_code=404, detail="Investment not found")
        
    update_data = inv_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_inv, key, value)
        
    db_inv.last_updated = utc_now()
    db.commit()
    db.refresh(db_inv)
    return db_inv

@router.delete("/{inv_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_investment(inv_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    db_inv = db.query(Investment).filter(Investment.id == inv_id, Investment.user_id == user_id).first()
    if not db_inv:
        raise HTTPException(status_code=404, detail="Investment not found")
    db.delete(db_inv)
    db.commit()
    return None
