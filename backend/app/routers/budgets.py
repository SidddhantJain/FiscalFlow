from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta
from decimal import Decimal
from app.database import get_db
from app.models.budget import Budget
from app.models.transaction import Transaction
from app.models.category import Category
from app.schemas.budget import Budget as BudgetSchema, BudgetCreate, BudgetUpdate
from app.routers.accounts import get_default_user_id

router = APIRouter(prefix="/budgets", tags=["Budgets"])

MASTER_BUDGET_TEMPLATE = [
    {"name": "PG Rent & Covered Meals", "category": "PG Rent & Covered Meals", "amount": 14000.00, "notes": "Breakfast & dinner daily, Saturday full meals, Sunday breakfast."},
    {"name": "Daily Office Lunch (Mon–Sat)", "category": "Daily Office Lunch (Mon–Sat)", "amount": 3250.00, "notes": "26 working days @ ₹100–150/day in/near Sigma Soft Tech Park."},
    {"name": "BMTC Bus Commute", "category": "BMTC Bus Commute", "amount": 1000.00, "notes": "Daily bus fares between Varthur Kodi and Kundalahalli Gate."},
    {"name": "Lifestyle & Personal Essentials", "category": "Lifestyle & Personal Essentials", "amount": 3500.00, "notes": "Sunday meals, mobile recharge, toiletries, laundry supplies."},
    {"name": "Emergency Fund Allocation", "category": "Emergency Fund Allocation", "amount": 2750.00, "notes": "Built up monthly in your liquid bank savings."},
    {"name": "Monthly SIP Investment", "category": "Monthly SIP Investment", "amount": 5500.00, "notes": "Capped fixed wealth-building auto-investment."},
    {"name": "Unallocated Flex Buffer", "category": "Unallocated Flex Buffer", "amount": 1000.00, "notes": "Extra cash left untouched in your bank account."}
]

def recalculate_budget_spent(budget: Budget, db: Session):
    cat = db.query(Category).filter(Category.id == budget.category_id).first()
    cat_type = cat.type if cat else "EXPENSE"
    
    total_spent = db.query(func.sum(Transaction.amount)).filter(
        Transaction.category_id == budget.category_id,
        Transaction.date >= budget.start_date,
        Transaction.date <= budget.end_date,
        Transaction.type == cat_type
    ).scalar() or Decimal("0.00")
    
    budget.spent = total_spent

@router.post("/", response_model=BudgetSchema, status_code=status.HTTP_201_CREATED)
def create_budget(budget: BudgetCreate, db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    db_budget = Budget(
        user_id=user_id,
        category_id=budget.category_id,
        amount=budget.amount,
        spent=budget.spent or Decimal("0.00"),
        start_date=budget.start_date,
        end_date=budget.end_date,
        name=budget.name,
        notes=budget.notes
    )
    db.add(db_budget)
    db.commit()
    db.refresh(db_budget)
    recalculate_budget_spent(db_budget, db)
    db.commit()
    db.refresh(db_budget)
    return db_budget

@router.get("/", response_model=list[BudgetSchema])
def list_budgets(db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    budgets = db.query(Budget).filter(Budget.user_id == user_id).all()
    for budget in budgets:
        recalculate_budget_spent(budget, db)
    db.commit()
    return budgets

@router.post("/reset-master", status_code=status.HTTP_200_OK)
def reset_to_master_budget(db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    """
    Clears existing budgets for current month and seeds the exact Master Budget distribution.
    """
    today = date.today()
    start_date = today.replace(day=1)
    if today.month == 12:
        end_date = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end_date = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

    # Delete existing budgets for the user
    db.query(Budget).filter(Budget.user_id == user_id).delete()
    
    created_budgets = []
    for item in MASTER_BUDGET_TEMPLATE:
        cat = db.query(Category).filter(Category.name == item["category"]).first()
        if not cat:
            cat_type = "INVESTMENT" if "Investment" in item["category"] or "SIP" in item["category"] else "SAVINGS" if "Emergency" in item["category"] else "EXPENSE"
            cat = Category(name=item["category"], type=cat_type, user_id=None)
            db.add(cat)
            db.commit()
            db.refresh(cat)
            
        b = Budget(
            user_id=user_id,
            category_id=cat.id,
            amount=Decimal(str(item["amount"])),
            spent=Decimal("0.00"),
            start_date=start_date,
            end_date=end_date,
            name=item["name"],
            notes=item["notes"]
        )
        db.add(b)
        created_budgets.append(b)
        
    db.commit()
    for b in created_budgets:
        recalculate_budget_spent(b, db)
    db.commit()
    
    return {"message": f"Successfully initialized {len(created_budgets)} Master Budget allocations."}

@router.get("/summary", status_code=status.HTTP_200_OK)
def get_budget_summary(db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    """
    Calculates detailed planned vs actual distribution, overgrown alerts, and percentages.
    """
    budgets = db.query(Budget).filter(Budget.user_id == user_id).all()
    categories = db.query(Category).all()
    cat_name_map = {c.id: c.name for c in categories}
    cat_type_map = {c.id: c.type for c in categories}

    total_planned = Decimal("0.00")
    total_spent = Decimal("0.00")
    items = []
    overgrown_items = []

    for b in budgets:
        recalculate_budget_spent(b, db)
        c_name = cat_name_map.get(b.category_id, b.name or "Budget Item")
        c_type = cat_type_map.get(b.category_id, "EXPENSE")
        
        amt = Decimal(str(b.amount))
        sp = Decimal(str(b.spent))
        total_planned += amt
        total_spent += sp
        
        pct_used = float(round((sp / amt * 100), 1)) if amt > 0 else 0.0
        is_overgrown = sp > amt
        remaining = amt - sp
        
        item_data = {
            "id": b.id,
            "name": b.name or c_name,
            "category_name": c_name,
            "category_id": b.category_id,
            "category_type": c_type,
            "amount": float(amt),
            "spent": float(sp),
            "remaining": float(remaining),
            "percent_used": pct_used,
            "is_overgrown": is_overgrown,
            "notes": b.notes or "",
            "start_date": b.start_date.isoformat(),
            "end_date": b.end_date.isoformat()
        }
        items.append(item_data)
        if is_overgrown:
            overgrown_items.append(item_data)

    db.commit()

    # Master Income Reference
    planned_income = 31000.00
    stipend_income = 25000.00
    family_income = 6000.00

    return {
        "planned_income": planned_income,
        "income_breakdown": {
            "Internship Stipend": stipend_income,
            "Family Support": family_income
        },
        "total_planned_allocation": float(total_planned),
        "total_actual_spent": float(total_spent),
        "total_remaining": float(Decimal(str(planned_income)) - total_spent),
        "items": items,
        "overgrown_count": len(overgrown_items),
        "overgrown_items": overgrown_items
    }

@router.put("/{budget_id}", response_model=BudgetSchema)
def update_budget(budget_id: int, budget_update: BudgetUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    db_budget = db.query(Budget).filter(Budget.id == budget_id, Budget.user_id == user_id).first()
    if not db_budget:
        raise HTTPException(status_code=404, detail="Budget not found")
        
    update_data = budget_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_budget, key, value)
        
    recalculate_budget_spent(db_budget, db)
    db.commit()
    db.refresh(db_budget)
    return db_budget

@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(budget_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    db_budget = db.query(Budget).filter(Budget.id == budget_id, Budget.user_id == user_id).first()
    if not db_budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    db.delete(db_budget)
    db.commit()
    return None
