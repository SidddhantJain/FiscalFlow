import os
import io
import csv
from datetime import datetime, date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.category import Category
from app.models.statement_file import StatementFile
from app.models.tag_rule import UserTagRule
from app.routers.accounts import get_default_user_id
from app.services.ai_engine import auto_categorize_uncategorized_transactions, learn_user_tag_rule

router = APIRouter(prefix="/statements", tags=["Statements"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "uploads", "statements")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("/", status_code=status.HTTP_200_OK)
def list_statement_files(db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    """
    Lists all raw bank statements uploaded by the user with metadata.
    """
    files = db.query(StatementFile).filter(StatementFile.user_id == user_id).order_by(StatementFile.upload_date.desc()).all()
    result = []
    for f in files:
        acc_name = f.account.name if f.account else "Unknown Account"
        result.append({
            "id": f.id,
            "filename": f.filename,
            "account_id": f.account_id,
            "account_name": acc_name,
            "bank_type": f.bank_type,
            "file_size": f.file_size,
            "file_size_kb": round(f.file_size / 1024, 1),
            "transaction_count": f.transaction_count,
            "upload_date": f.upload_date.isoformat()
        })
    return result

@router.get("/{statement_id}/download")
def download_statement_file(statement_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    """
    Downloads the original bank statement attachment file exactly as uploaded.
    """
    stmt = db.query(StatementFile).filter(StatementFile.id == statement_id, StatementFile.user_id == user_id).first()
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement file not found")
        
    file_path = os.path.join(UPLOAD_DIR, stmt.saved_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File is no longer available on disk")
        
    media_type = "text/csv" if stmt.filename.endswith(".csv") else "application/octet-stream"
    return FileResponse(
        path=file_path,
        filename=stmt.filename,
        media_type=media_type
    )

@router.get("/export/axis")
def export_axis_statement(
    account_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_default_user_id)
):
    """
    Exports transactions in the standard Axis Bank Statement format:
    Tran Date,CHQNO,PARTICULARS,DR,CR,BAL,SOL
    """
    user_accounts = db.query(Account).filter(Account.user_id == user_id).all()
    user_account_ids = [a.id for a in user_accounts]
    
    query = db.query(Transaction).filter(Transaction.account_id.in_(user_account_ids))
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)
        
    txs = query.order_by(Transaction.date.asc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Axis Bank Standard Header
    writer.writerow(["Tran Date", "CHQNO", "PARTICULARS", "DR", "CR", "BAL", "SOL"])
    
    running_balance = Decimal("0.00")
    for tx in txs:
        date_str = tx.date.strftime("%d-%m-%Y")
        chqno = tx.reference_number or "-"
        particulars = tx.description
        
        dr_str = ""
        cr_str = ""
        if tx.type in ["EXPENSE", "INVESTMENT", "SAVINGS", "TRANSFER", "TAX", "LOAN"]:
            dr_str = f"{tx.amount:.2f}"
            running_balance -= tx.amount
        else:
            cr_str = f"{tx.amount:.2f}"
            running_balance += tx.amount
            
        bal_str = f"{running_balance:.2f}"
        sol_str = "001"
        
        writer.writerow([date_str, chqno, particulars, dr_str, cr_str, bal_str, sol_str])
        
    output.seek(0)
    filename = f"Axis_Statement_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/export/full-csv")
def export_full_ledger_csv(
    account_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    tag: str | None = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_default_user_id)
):
    """
    Exports full transaction ledger including categories, tags, account names, and notes.
    """
    user_accounts = db.query(Account).filter(Account.user_id == user_id).all()
    user_account_ids = [a.id for a in user_accounts]
    
    query = db.query(Transaction).filter(Transaction.account_id.in_(user_account_ids))
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    if tag:
        query = query.filter(Transaction.tags.ilike(f"%{tag}%"))
        
    txs = query.order_by(Transaction.date.desc()).all()
    categories = {c.id: c.name for c in db.query(Category).all()}
    accounts = {a.id: a.name for a in user_accounts}
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(["Date", "Description", "Amount (INR)", "Type", "Category", "Tags", "Account", "Reference", "Notes"])
    for tx in txs:
        cat_name = categories.get(tx.category_id, "")
        acc_name = accounts.get(tx.account_id, "")
        writer.writerow([
            tx.date.isoformat(),
            tx.description,
            f"{tx.amount:.2f}",
            tx.type,
            cat_name,
            tx.tags or "",
            acc_name,
            tx.reference_number or "",
            tx.notes or ""
        ])
        
    output.seek(0)
    filename = f"FiscalFlow_Ledger_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/tag-rules", status_code=status.HTTP_200_OK)
def list_tag_rules(db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    """
    Returns all learned and custom repetitive transaction tag rules.
    """
    rules = db.query(UserTagRule).filter(UserTagRule.user_id == user_id).order_by(UserTagRule.match_count.desc()).all()
    categories = {c.id: c.name for c in db.query(Category).all()}
    return [
        {
            "id": r.id,
            "pattern": r.pattern,
            "tags": r.tags,
            "category_id": r.category_id,
            "category_name": categories.get(r.category_id, ""),
            "match_count": r.match_count,
            "updated_at": r.updated_at.isoformat()
        }
        for r in rules
    ]

@router.post("/tag-rules/apply-all", status_code=status.HTTP_200_OK)
def apply_all_tag_rules(db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    """
    Applies learned tag rules across all matching transactions in the ledger.
    """
    updated_count = auto_categorize_uncategorized_transactions(db, user_id)
    return {"message": f"Successfully evaluated and updated {updated_count} transactions with learned tag rules."}
