from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.budget import Budget
from app.models.transaction import Transaction
from app.schemas.budget import Budget as BudgetSchema, BudgetCreate, BudgetUpdate
from app.routers.accounts import get_default_user_id

router = APIRouter(prefix="/budgets", tags=["Budgets"])

@router.post("/", response_model=BudgetSchema, status_code=status.HTTP_201_CREATED)
def create_budget(budget: BudgetCreate, db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    db_budget = Budget(
        user_id=user_id,
        category_id=budget.category_id,
        amount=budget.amount,
        spent=budget.spent,
        start_date=budget.start_date,
        end_date=budget.end_date
    )
    db.add(db_budget)
    db.commit()
    db.refresh(db_budget)
    return db_budget

@router.get("/", response_model=list[BudgetSchema])
def list_budgets(db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    # Automatically refresh budgets spent amounts when querying
    budgets = db.query(Budget).filter(Budget.user_id == user_id).all()
    for budget in budgets:
        # Sum expense transactions under this category within budget dates
        total_spent = db.query(func.sum(Transaction.amount)).filter(
            Transaction.category_id == budget.category_id,
            Transaction.date >= budget.start_date,
            Transaction.date <= budget.end_date,
            Transaction.type == "EXPENSE"
        ).scalar() or 0.00
        budget.spent = total_spent
    db.commit()
    return budgets

@router.put("/{budget_id}", response_model=BudgetSchema)
def update_budget(budget_id: int, budget_update: BudgetUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    db_budget = db.query(Budget).filter(Budget.id == budget_id, Budget.user_id == user_id).first()
    if not db_budget:
        raise HTTPException(status_code=404, detail="Budget not found")
        
    update_data = budget_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_budget, key, value)
        
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
