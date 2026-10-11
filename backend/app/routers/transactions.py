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
        tags = extract_transaction_tags(tx.description, cat_name, tx.type, db, user_id)

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

from sqlalchemy import func
from datetime import date, timedelta

@router.get("/", response_model=list[TransactionSchema])
def list_transactions(
    start_date: date | None = None,
    end_date: date | None = None,
    tx_type: str | None = None,
    category_id: int | None = None,
    account_id: int | None = None,
    tag: str | None = None,
    search: str | None = None,
    days: int | None = None,
    limit: int | None = None,
    offset: int | None = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_default_user_id)
):
    # Fetch accounts owned by user to filter
    user_accounts = db.query(Account).filter(Account.user_id == user_id).all()
    user_account_ids = [a.id for a in user_accounts]
    
    query = db.query(Transaction).filter(
        Transaction.account_id.in_(user_account_ids)
    )
    
    if days:
        latest_date = db.query(func.max(Transaction.date)).filter(Transaction.account_id.in_(user_account_ids)).scalar()
        ref_date = latest_date or date.today()
        cutoff = ref_date - timedelta(days=days)
        query = query.filter(Transaction.date >= cutoff)
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
        
    query = query.order_by(Transaction.date.desc())
    if offset:
        query = query.offset(offset)
    if limit:
        query = query.limit(limit)
        
    return query.all()

import os
import time
from app.models.statement_file import StatementFile
from app.services.ai_engine import auto_categorize_uncategorized_transactions, extract_transaction_tags, learn_user_tag_rule

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "uploads", "statements")
os.makedirs(UPLOAD_DIR, exist_ok=True)

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
    
    # Automatically learn tag rule for repetitive transactions if tags were set
    if db_tx.tags:
        learn_user_tag_rule(db, user_id, db_tx.description, db_tx.tags, db_tx.category_id)
        # Apply learned rule to any existing uncategorized/untagged transactions with the same description
        auto_categorize_uncategorized_transactions(db, user_id)
        
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
    bank_type: str = Form("AUTO_DETECT"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_default_user_id)
):
    # Verify account
    account = db.query(Account).filter(Account.id == account_id, Account.user_id == user_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Selected account was not found.")
        
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded statement file is empty.")
        
    # Check if this is a Demat holding/trading statement or Demat bank_type
    is_demat_req = bank_type in ("GROWW_DEMAT", "ANGELONE_DEMAT", "ZERODHA_DEMAT", "GENERIC_DEMAT")
    
    try:
        if is_demat_req:
            from app.services.statement_import import import_demat_holdings
            demat_res = import_demat_holdings(db, user_id, account_id, file_bytes, file.filename, broker_type=bank_type)
            imported_count = demat_res.get("imported_transactions", 0)
            holdings_count = demat_res.get("imported_holdings", 0)
            
            # Persist the raw statement file locally
            saved_filename = f"{int(time.time())}_{file.filename.replace(' ', '_')}"
            saved_filepath = os.path.join(UPLOAD_DIR, saved_filename)
            with open(saved_filepath, "wb") as f_out:
                f_out.write(file_bytes)
                
            stmt_record = StatementFile(
                user_id=user_id,
                account_id=account_id,
                filename=file.filename,
                saved_filename=saved_filename,
                file_size=len(file_bytes),
                bank_type=bank_type,
                transaction_count=imported_count + holdings_count
            )
            db.add(stmt_record)
            db.commit()
            
            return {
                "message": f"Successfully parsed {holdings_count} portfolio holdings and {imported_count} transactions.",
                "statement_id": stmt_record.id,
                "filename": file.filename,
                "holdings_count": holdings_count,
                "transaction_count": imported_count,
                "imported_count": imported_count
            }
            
        parsed_txs = parse_statement(file_bytes, file.filename, bank_type)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse statement: {str(e)}")
        
    if not parsed_txs:
        raise HTTPException(
            status_code=400, 
            detail="No valid transactions could be parsed from this file. Please ensure the file contains valid dates, descriptions, and amounts."
        )
        
    # Persist the raw bank statement file locally
    saved_filename = f"{int(time.time())}_{file.filename.replace(' ', '_')}"
    saved_filepath = os.path.join(UPLOAD_DIR, saved_filename)
    with open(saved_filepath, "wb") as f_out:
        f_out.write(file_bytes)
        
    # Record StatementFile metadata in database
    stmt_record = StatementFile(
        user_id=user_id,
        account_id=account_id,
        filename=file.filename,
        saved_filename=saved_filename,
        file_size=len(file_bytes),
        bank_type=bank_type,
        transaction_count=len(parsed_txs)
    )
    db.add(stmt_record)
    db.commit()
    
    imported = import_statement_transactions(db, account_id, parsed_txs)
    
    # Auto-run engines post-import: applying learned tag rules, regex tags, and transfers
    auto_categorize_uncategorized_transactions(db, user_id)
    detect_and_link_transfers(db, user_id)
    
    return {
        "message": f"Successfully parsed {len(parsed_txs)} transactions and imported {imported} new records.",
        "statement_id": stmt_record.id,
        "filename": file.filename,
        "transaction_count": len(parsed_txs),
        "imported_count": imported
    }

@router.post("/detect-transfers", status_code=status.HTTP_200_OK)
def trigger_transfer_detection(db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    count = detect_and_link_transfers(db, user_id)
    return {"message": f"Transfer intelligence engine linked {count} transactions."}
