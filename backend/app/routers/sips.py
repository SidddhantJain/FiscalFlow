from datetime import datetime, date, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.sip import SipSchedule
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.category import Category
from app.schemas.sip import SipSchedule as SipSchema, SipScheduleCreate, SipScheduleUpdate
from app.routers.accounts import get_default_user_id
import calendar

router = APIRouter(prefix="/sips", tags=["SIP Schedules"])

def calculate_next_sip_date(day_of_month: int, from_date: date | None = None) -> date:
    """Calculates the upcoming SIP execution date for a given day of month."""
    if not from_date:
        from_date = date.today()
    
    # Try current month on day_of_month
    year = from_date.year
    month = from_date.month
    
    # Bound day to max days in month
    max_days = calendar.monthrange(year, month)[1]
    target_day = min(day_of_month, max_days)
    
    candidate = date(year, month, target_day)
    if candidate >= from_date:
        return candidate
    
    # Otherwise next month
    if month == 12:
        year += 1
        month = 1
    else:
        month += 1
        
    max_days = calendar.monthrange(year, month)[1]
    target_day = min(day_of_month, max_days)
    return date(year, month, target_day)

@router.get("/", response_model=list[dict])
def list_sips(db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    sips = db.query(SipSchedule).filter(SipSchedule.user_id == user_id).order_by(SipSchedule.sip_day_of_month.asc()).all()
    today = date.today()
    
    result = []
    for sip in sips:
        # Update / ensure next_sip_date is up to date
        expected_next = calculate_next_sip_date(sip.sip_day_of_month, today)
        if sip.next_sip_date != expected_next:
            sip.next_sip_date = expected_next
            db.commit()
            
        days_remaining = (sip.next_sip_date - today).days
        acc_name = None
        if sip.account_id:
            acc = db.query(Account).filter(Account.id == sip.account_id).first()
            if acc:
                acc_name = acc.name
                
        result.append({
            "id": sip.id,
            "user_id": sip.user_id,
            "scheme_name": sip.scheme_name,
            "asset_class": sip.asset_class,
            "amount": float(sip.amount),
            "frequency": sip.frequency,
            "sip_day_of_month": sip.sip_day_of_month,
            "start_date": sip.start_date.isoformat(),
            "next_sip_date": sip.next_sip_date.isoformat(),
            "days_remaining": days_remaining,
            "broker": sip.broker,
            "folio_number": sip.folio_number,
            "status": sip.status,
            "account_id": sip.account_id,
            "account_name": acc_name,
            "notes": sip.notes
        })
    return result

@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_sip(sip_in: SipScheduleCreate, db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    next_date = sip_in.next_sip_date or calculate_next_sip_date(sip_in.sip_day_of_month)
    
    db_sip = SipSchedule(
        user_id=user_id,
        account_id=sip_in.account_id,
        scheme_name=sip_in.scheme_name,
        asset_class=sip_in.asset_class,
        amount=sip_in.amount,
        frequency=sip_in.frequency,
        sip_day_of_month=sip_in.sip_day_of_month,
        start_date=sip_in.start_date,
        next_sip_date=next_date,
        broker=sip_in.broker,
        folio_number=sip_in.folio_number,
        status=sip_in.status,
        notes=sip_in.notes
    )
    db.add(db_sip)
    db.commit()
    db.refresh(db_sip)
    
    return {
        "id": db_sip.id,
        "scheme_name": db_sip.scheme_name,
        "amount": float(db_sip.amount),
        "sip_day_of_month": db_sip.sip_day_of_month,
        "next_sip_date": db_sip.next_sip_date.isoformat(),
        "broker": db_sip.broker,
        "status": db_sip.status
    }

@router.put("/{sip_id}", response_model=dict)
def update_sip(sip_id: int, sip_update: SipScheduleUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    db_sip = db.query(SipSchedule).filter(SipSchedule.id == sip_id, SipSchedule.user_id == user_id).first()
    if not db_sip:
        raise HTTPException(status_code=404, detail="SIP Schedule not found")
        
    update_data = sip_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_sip, key, value)
        
    if "sip_day_of_month" in update_data:
        db_sip.next_sip_date = calculate_next_sip_date(db_sip.sip_day_of_month)
        
    db.commit()
    db.refresh(db_sip)
    return {
        "id": db_sip.id,
        "scheme_name": db_sip.scheme_name,
        "amount": float(db_sip.amount),
        "sip_day_of_month": db_sip.sip_day_of_month,
        "next_sip_date": db_sip.next_sip_date.isoformat(),
        "broker": db_sip.broker,
        "status": db_sip.status
    }

@router.get("/projection", response_model=dict)
def calculate_sip_projection(
    monthly_amount: float = 2500.0,
    expected_cagr_pct: float = 12.0,
    years: int = 10
):
    """
    Calculates future wealth projection for regular SIP investments using standard compounding formula.
    """
    p = float(monthly_amount)
    r = float(expected_cagr_pct)
    n = int(years) * 12
    i = (r / 100.0) / 12.0
    
    if i > 0:
        future_val = p * (((1.0 + i) ** n - 1.0) / i) * (1.0 + i)
    else:
        future_val = p * n
        
    total_invested = p * n
    wealth_gain = max(0.0, future_val - total_invested)
    
    # Statutory LTCG tax projection (Finance Act 2024: 12.5% on gains exceeding ₹1,25,000 + 4% cess)
    statutory_ltcg_exemption = 125000.0
    taxable_ltcg_gain = max(0.0, wealth_gain - statutory_ltcg_exemption)
    projected_ltcg_tax = (taxable_ltcg_gain * 0.125) * 1.04
    post_tax_future_value = future_val - projected_ltcg_tax

    return {
        "monthly_amount": p,
        "expected_cagr_pct": r,
        "years": years,
        "total_months": n,
        "total_invested": round(total_invested, 2),
        "future_value": round(future_val, 2),
        "wealth_gain": round(wealth_gain, 2),
        "statutory_capital_gains_projection": {
            "legal_basis": "Finance Act 2024 (Section 112A @ 12.5% + 4% Cess)",
            "statutory_exemption_limit": statutory_ltcg_exemption,
            "exempt_gain": round(min(wealth_gain, statutory_ltcg_exemption), 2),
            "taxable_gain": round(taxable_ltcg_gain, 2),
            "estimated_ltcg_tax": round(projected_ltcg_tax, 2),
            "post_tax_future_value": round(post_tax_future_value, 2)
        }
    }

@router.delete("/{sip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sip(sip_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    db_sip = db.query(SipSchedule).filter(SipSchedule.id == sip_id, SipSchedule.user_id == user_id).first()
    if not db_sip:
        raise HTTPException(status_code=404, detail="SIP Schedule not found")
    db.delete(db_sip)
    db.commit()
    return None

@router.post("/{sip_id}/execute", response_model=dict)
@router.post("/{sip_id}/log-payment", response_model=dict)
def record_sip_execution(sip_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    """Records an investment transaction corresponding to this SIP."""
    db_sip = db.query(SipSchedule).filter(SipSchedule.id == sip_id, SipSchedule.user_id == user_id).first()
    if not db_sip:
        raise HTTPException(status_code=404, detail="SIP Schedule not found")
        
    account_id = db_sip.account_id
    if not account_id:
        acc = db.query(Account).filter(Account.user_id == user_id).first()
        if acc:
            account_id = acc.id
            
    if not account_id:
        raise HTTPException(status_code=400, detail="No source account available to execute SIP")
        
    # Find or assign Category
    cat = db.query(Category).filter(Category.name.ilike("%Monthly SIP%") | Category.name.ilike("%Investment%")).first()
    cat_id = cat.id if cat else None
    
    today = date.today()
    tx = Transaction(
        date=today,
        description=f"SIP: {db_sip.scheme_name} ({db_sip.broker})",
        amount=db_sip.amount,
        type="INVESTMENT",
        category_id=cat_id,
        account_id=account_id,
        reference_number=f"SIP-{db_sip.id}-{today.strftime('%Y%m%d')}",
        is_recurring=True,
        tags=f"SIP, Investment, {db_sip.broker}, MutualFund",
        notes=f"Auto-recorded SIP execution for {db_sip.scheme_name}"
    )
    db.add(tx)
    
    # Update account balance
    acc = db.query(Account).filter(Account.id == account_id).first()
    if acc:
        acc.current_balance -= db_sip.amount
        
    # Advance next_sip_date
    db_sip.next_sip_date = calculate_next_sip_date(db_sip.sip_day_of_month, from_date=today + timedelta(days=1))
    db.commit()
    
    return {
        "message": f"SIP {db_sip.scheme_name} of ₹{db_sip.amount} executed successfully!",
        "transaction_id": tx.id,
        "next_sip_date": db_sip.next_sip_date.isoformat()
    }
