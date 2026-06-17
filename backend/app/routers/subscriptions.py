from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.subscription import Subscription
from app.schemas.subscription import Subscription as SubscriptionSchema, SubscriptionCreate, SubscriptionUpdate
from app.routers.accounts import get_default_user_id

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])

@router.post("/", response_model=SubscriptionSchema, status_code=status.HTTP_201_CREATED)
def create_subscription(sub: SubscriptionCreate, db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    db_sub = Subscription(
        user_id=user_id,
        account_id=sub.account_id,
        name=sub.name,
        amount=sub.amount,
        billing_cycle=sub.billing_cycle,
        next_renewal_date=sub.next_renewal_date,
        is_active=sub.is_active
    )
    db.add(db_sub)
    db.commit()
    db.refresh(db_sub)
    return db_sub

@router.get("/", response_model=list[SubscriptionSchema])
def list_subscriptions(db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    return db.query(Subscription).filter(Subscription.user_id == user_id).all()

@router.put("/{sub_id}", response_model=SubscriptionSchema)
def update_subscription(sub_id: int, sub_update: SubscriptionUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    db_sub = db.query(Subscription).filter(Subscription.id == sub_id, Subscription.user_id == user_id).first()
    if not db_sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
        
    update_data = sub_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_sub, key, value)
        
    db.commit()
    db.refresh(db_sub)
    return db_sub

@router.delete("/{sub_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(sub_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    db_sub = db.query(Subscription).filter(Subscription.id == sub_id, Subscription.user_id == user_id).first()
    if not db_sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    db.delete(db_sub)
    db.commit()
    return None
