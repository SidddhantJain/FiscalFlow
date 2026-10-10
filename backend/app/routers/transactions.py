from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from datetime import date
from decimal import Decimal
from app.database import get_db
from app.models.transaction import Transaction
from app.models.account import Account
from app.models.category import Category
from app.schemas.transaction import Transaction as TransactionSchema, TransactionCreate, TransactionUpdate
from app.routers.accounts import get_default_user_id
from app.services.statement_import import parse_statement, import_statement_transactions
from app.services.transfer_engine import detect_and_link_transfers
from app.services.ai_engine import auto_categorize_uncategorized_transactions

router = APIRouter(prefix="/transactions", tags=["Transactions"])

from app.services.ai_engine import auto_categorize_uncategorized_transactions, extract_transaction_tags

@router.post("/", response_model=TransactionSchema, status_code=status.HTTP_201_CREATED)
def create_transaction(tx: TransactionCreate, db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    # Verify account exists
    account = db.query(Account).filter(Account.id == tx.account_id, Account.user_id == user_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
        
    tags = tx.tags
    if not tags:
        cat_name = ""
        if tx.category_id:
            cat = db.query(Category).filter(Category.id == tx.category_id).first()
            if cat:
                cat_name = cat.name
        tags = extract_transaction_tags(tx.description, cat_name, tx.type)

    db_tx = Transaction(
        date=tx.date,
        description=tx.description,
        amount=tx.amount,
        type=tx.type,
        category_id=tx.category_id,
        account_id=tx.account_id,
        destination_account_id=tx.destination_account_id,
        reference_number=tx.reference_number,
        is_recurring=tx.is_recurring,
        notes=tx.notes,
        tags=tags
    )
    db.add(db_tx)
    
    # Update account balance
    # INCOME increase; EXPENSE / SAVINGS / INVESTMENT decrease from primary account.
    # If TRANSFER, decrease from primary account and increase destination account.
    if tx.type == "INCOME":
        account.current_balance += tx.amount
    elif tx.type in ["TRANSFER", "SAVINGS", "INVESTMENT"] and tx.destination_account_id:
        dest_account = db.query(Account).filter(Account.id == tx.destination_account_id, Account.user_id == user_id).first()
        if not dest_account:
            raise HTTPException(status_code=404, detail="Destination account not found")
        account.current_balance -= tx.amount
        dest_account.current_balance += tx.amount
    else:
        # EXPENSE, LOAN, TAX (and SAVINGS/INVESTMENT if no destination account)
        account.current_balance -= tx.amount
        
    db.commit()
    db.refresh(db_tx)
    return db_tx

@router.get("/", response_model=list[TransactionSchema])
def list_transactions(
    start_date: date | None = None,
    end_date: date | None = None,
    tx_type: str | None = None,
    category_id: int | None = None,
    account_id: int | None = None,
    tag: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_default_user_id)
):
    # Fetch accounts owned by user to filter
    user_accounts = db.query(Account).filter(Account.user_id == user_id).all()
    user_account_ids = [a.id for a in user_accounts]
    
    query = db.query(Transaction).filter(
        Transaction.account_id.in_(user_account_ids)
    )
    
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    if tx_type:
        query = query.filter(Transaction.type == tx_type)
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    if tag:
        query = query.filter(Transaction.tags.ilike(f"%{tag}%"))
    if search:
        query = query.filter(Transaction.description.ilike(f"%{search}%"))
        
    return query.order_by(Transaction.date.desc()).all()

@router.put("/{tx_id}", response_model=TransactionSchema)
def update_transaction(
    tx_id: int,
    tx_update: TransactionUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_default_user_id)
):
    user_accounts = db.query(Account).filter(Account.user_id == user_id).all()
    user_account_ids = [a.id for a in user_accounts]
    
    db_tx = db.query(Transaction).filter(Transaction.id == tx_id, Transaction.account_id.in_(user_account_ids)).first()
    if not db_tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
        
    update_data = tx_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_tx, key, value)
        
    db.commit()
    db.refresh(db_tx)
    return db_tx

@router.delete("/{tx_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(tx_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    # Fetch accounts owned by user
    user_accounts = db.query(Account).filter(Account.user_id == user_id).all()
    user_account_ids = [a.id for a in user_accounts]
    
    tx = db.query(Transaction).filter(Transaction.id == tx_id, Transaction.account_id.in_(user_account_ids)).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
        
    # Revert account balances before deletion
    account = db.query(Account).filter(Account.id == tx.account_id).first()
    if tx.type == "INCOME":
        account.current_balance -= tx.amount
    elif tx.type in ["TRANSFER", "SAVINGS", "INVESTMENT"] and tx.destination_account_id:
        dest_account = db.query(Account).filter(Account.id == tx.destination_account_id).first()
        if dest_account:
            dest_account.current_balance -= tx.amount
        account.current_balance += tx.amount
    else:
        account.current_balance += tx.amount
        
    db.delete(tx)
    db.commit()
    return None

@router.post("/import", status_code=status.HTTP_200_OK)
async def import_statement(
    account_id: int = Form(...),
    bank_type: str = Form("DEFAULT_CSV"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_default_user_id)
):
    # Verify account
    account = db.query(Account).filter(Account.id == account_id, Account.user_id == user_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
        
    file_bytes = await file.read()
    
    try:
        parsed_txs = parse_statement(file_bytes, file.filename, bank_type)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse statement: {str(e)}")
        
    if not parsed_txs:
        return {"message": "No valid transactions parsed from statement."}
        
    imported = import_statement_transactions(db, account_id, parsed_txs)
    
    # Auto-run engines post-import
    auto_categorize_uncategorized_transactions(db, user_id)
    detect_and_link_transfers(db, user_id)
    
    return {"message": f"Successfully parsed {len(parsed_txs)} transactions, imported {imported} new records."}

@router.post("/detect-transfers", status_code=status.HTTP_200_OK)
def trigger_transfer_detection(db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    count = detect_and_link_transfers(db, user_id)
    return {"message": f"Transfer intelligence engine linked {count} transactions."}
