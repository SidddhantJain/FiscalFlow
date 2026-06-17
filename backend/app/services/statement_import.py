import io
import pandas as pd
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.transaction import Transaction
from app.models.account import Account

# Templates defining column mappings for standard bank statement exports
BANK_TEMPLATES = {
    "DEFAULT_CSV": {
        "date_col": "Date",
        "desc_col": "Description",
        "amount_col": "Amount",  # positive for credit, negative for debit
        "ref_col": "Reference",
        "date_format": "%Y-%m-%d"
    },
    "HDFC_CSV": {
        "date_col": "Date",
        "desc_col": "Description",
        "withdrawal_col": "Withdrawal",  # debits
        "deposit_col": "Deposit",        # credits
        "ref_col": "Chq/Ref No",
        "date_format": "%d/%m/%y"
    },
    "SBI_CSV": {
        "date_col": "Txn Date",
        "desc_col": "Description",
        "debit_col": "Debit",
        "credit_col": "Credit",
        "ref_col": "Ref No./Cheque No.",
        "date_format": "%d %b %Y"
    }
}

def parse_statement(file_bytes: bytes, file_name: str, bank_type: str = "DEFAULT_CSV") -> list[dict]:
    """
    Parses a bank statement file (CSV or XLSX) into a list of normalized transaction dictionaries.
    """
    template = BANK_TEMPLATES.get(bank_type, BANK_TEMPLATES["DEFAULT_CSV"])
    
    # Read file bytes into pandas DataFrame
    if file_name.endswith(".xlsx") or file_name.endswith(".xls"):
        df = pd.read_excel(io.BytesIO(file_bytes))
    else:
        df = pd.read_csv(io.BytesIO(file_bytes))
        
    # Clean column names (strip whitespace)
    df.columns = [str(c).strip() for c in df.columns]
    
    parsed_transactions = []
    
    for _, row in df.iterrows():
        try:
            # 1. Parse date
            raw_date = str(row.get(template["date_col"], "")).strip()
            if not raw_date or raw_date.lower() == "nan":
                continue
            
            try:
                tx_date = datetime.strptime(raw_date, template["date_format"]).date()
            except Exception:
                tx_date = pd.to_datetime(raw_date).date()
                
            # 2. Parse Description
            desc = str(row.get(template["desc_col"], "")).strip()
            if not desc or desc.lower() == "nan":
                continue
            
            # 3. Parse Amount and Transaction Type
            amount = Decimal("0.00")
            tx_type = "EXPENSE"
            
            # Check for double-column layouts (Withdrawal vs Deposit or Debit vs Credit)
            if "withdrawal_col" in template and template["withdrawal_col"] in row:
                w_val = str(row.get(template["withdrawal_col"], "0")).strip().replace(",", "")
                d_val = str(row.get(template["deposit_col"], "0")).strip().replace(",", "")
                
                w_amt = Decimal(w_val) if w_val and w_val.lower() != "nan" else Decimal("0.00")
                d_amt = Decimal(d_val) if d_val and d_val.lower() != "nan" else Decimal("0.00")
                
                if w_amt > 0:
                    amount = w_amt
                    tx_type = "EXPENSE"
                elif d_amt > 0:
                    amount = d_amt
                    tx_type = "INCOME"
                else:
                    continue  # Skip rows with no values
            elif "debit_col" in template and template["debit_col"] in row:
                w_val = str(row.get(template["debit_col"], "0")).strip().replace(",", "")
                d_val = str(row.get(template["credit_col"], "0")).strip().replace(",", "")
                
                w_amt = Decimal(w_val) if w_val and w_val.lower() != "nan" else Decimal("0.00")
                d_amt = Decimal(d_val) if d_val and d_val.lower() != "nan" else Decimal("0.00")
                
                if w_amt > 0:
                    amount = w_amt
                    tx_type = "EXPENSE"
                elif d_amt > 0:
                    amount = d_amt
                    tx_type = "INCOME"
                else:
                    continue
            else:
                # Single column amount layout
                raw_amount = str(row.get(template["amount_col"], "0")).strip().replace(",", "")
                val = Decimal(raw_amount)
                if val < 0:
                    amount = abs(val)
                    tx_type = "EXPENSE"
                elif val > 0:
                    amount = val
                    tx_type = "INCOME"
                else:
                    continue
            
            # 4. Parse Reference Number
            ref_num = None
            if "ref_col" in template and template["ref_col"] in row:
                ref_num = str(row.get(template["ref_col"], "")).strip()
                if ref_num.lower() == "nan" or not ref_num:
                    ref_num = None
            
            parsed_transactions.append({
                "date": tx_date,
                "description": desc,
                "amount": amount,
                "type": tx_type,
                "reference_number": ref_num
            })
        except Exception:
            # Skip unparseable rows
            continue
            
    return parsed_transactions

def import_statement_transactions(db: Session, account_id: int, transactions_data: list[dict]) -> int:
    """
    Saves parsed statement transactions into the database. Deduplicates based on date, description, and amount.
    Adjusts the parent account current balance based on transaction activity.
    """
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        return 0
        
    imported_count = 0
    for data in transactions_data:
        # Check for duplicates
        duplicate_query = db.query(Transaction).filter(
            Transaction.account_id == account_id,
            Transaction.date == data["date"],
            Transaction.amount == data["amount"]
        )
        if data["reference_number"]:
            duplicate = duplicate_query.filter(Transaction.reference_number == data["reference_number"]).first()
        else:
            duplicate = duplicate_query.filter(Transaction.description == data["description"]).first()
            
        if duplicate:
            continue
            
        tx = Transaction(
            date=data["date"],
            description=data["description"],
            amount=data["amount"],
            type=data["type"],
            account_id=account_id,
            reference_number=data["reference_number"]
        )
        db.add(tx)
        
        # Adjust account current balance
        if data["type"] == "INCOME":
            account.current_balance += data["amount"]
        else:
            account.current_balance -= data["amount"]
            
        imported_count += 1
        
    if imported_count > 0:
        db.commit()
        
    return imported_count
