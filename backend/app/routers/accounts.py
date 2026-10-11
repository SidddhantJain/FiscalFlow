from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.account import Account
from app.models.user import User
from app.schemas.account import Account as AccountSchema, AccountCreate, AccountUpdate

router = APIRouter(prefix="/accounts", tags=["Accounts"])

def get_default_user_id(db: Session = Depends(get_db)) -> int:
    """Helper dependency to retrieve the local user ID."""
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=500, detail="Default user not initialized")
    return user.id

@router.post("/", response_model=AccountSchema, status_code=status.HTTP_201_CREATED)
def create_account(account: AccountCreate, db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    db_account = Account(
        user_id=user_id,
        name=account.name,
        bank_name=account.bank_name,
        account_type=account.account_type,
        account_number=account.account_number,
        opening_balance=account.opening_balance,
        current_balance=account.opening_balance, # Initial current balance equals opening balance
        currency=account.currency
    )
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account

@router.get("/", response_model=list[AccountSchema])
def list_accounts(db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    return db.query(Account).filter(Account.user_id == user_id).all()

@router.get("/{account_id}", response_model=AccountSchema)
def get_account(account_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    account = db.query(Account).filter(Account.id == account_id, Account.user_id == user_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account

@router.put("/{account_id}", response_model=AccountSchema)
def update_account(account_id: int, account_update: AccountUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    db_account = db.query(Account).filter(Account.id == account_id, Account.user_id == user_id).first()
    if not db_account:
        raise HTTPException(status_code=404, detail="Account not found")
        
    update_data = account_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_account, key, value)
        
    db.commit()
    db.refresh(db_account)
    return db_account

@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    db_account = db.query(Account).filter(Account.id == account_id, Account.user_id == user_id).first()
    if not db_account:
        raise HTTPException(status_code=404, detail="Account not found")
    db.delete(db_account)
    db.commit()
    return None

@router.post("/clean-duplicates")
def clean_duplicate_accounts(db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    """Removes duplicate accounts with identical name and bank that have 0 balance or no transactions."""
    accounts = db.query(Account).filter(Account.user_id == user_id).order_by(Account.id.asc()).all()
    seen = {}
    deleted_count = 0
    for acc in accounts:
        key = (acc.name.strip().lower(), acc.bank_name.strip().lower() if acc.bank_name else "")
        if key in seen:
            has_tx = len(acc.transactions) > 0 if hasattr(acc, 'transactions') else False
            if not has_tx or acc.current_balance == 0:
                db.delete(acc)
                deleted_count += 1
                continue
        seen[key] = acc
    db.commit()
    return {"message": f"Cleaned {deleted_count} duplicate accounts.", "deleted_count": deleted_count}
