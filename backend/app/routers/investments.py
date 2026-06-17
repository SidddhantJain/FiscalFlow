from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.models.investment import Investment
from app.schemas.investment import Investment as InvestmentSchema, InvestmentCreate, InvestmentUpdate
from app.routers.accounts import get_default_user_id

router = APIRouter(prefix="/investments", tags=["Investments"])

@router.post("/", response_model=InvestmentSchema, status_code=status.HTTP_201_CREATED)
def create_investment(inv: InvestmentCreate, db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    db_inv = Investment(
        user_id=user_id,
        name=inv.name,
        asset_class=inv.asset_class,
        units=inv.units,
        purchase_price=inv.purchase_price,
        current_value=inv.current_value,
        last_updated=datetime.utcnow()
    )
    db.add(db_inv)
    db.commit()
    db.refresh(db_inv)
    return db_inv

@router.get("/", response_model=list[InvestmentSchema])
def list_investments(db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    return db.query(Investment).filter(Investment.user_id == user_id).all()

@router.put("/{inv_id}", response_model=InvestmentSchema)
def update_investment(inv_id: int, inv_update: InvestmentUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    db_inv = db.query(Investment).filter(Investment.id == inv_id, Investment.user_id == user_id).first()
    if not db_inv:
        raise HTTPException(status_code=404, detail="Investment not found")
        
    update_data = inv_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_inv, key, value)
        
    db_inv.last_updated = datetime.utcnow()
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
