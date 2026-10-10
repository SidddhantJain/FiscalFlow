from datetime import timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.transaction import Transaction
from app.models.account import Account

def detect_and_link_transfers(db: Session, user_id: int, days_window: int = 2) -> int:
    """
    Scans transactions for the user and automatically detects transfers:
    If there is a debit transaction in Account A and a credit transaction in Account B 
    of the exact same amount within `days_window`, it merges them into a single TRANSFER transaction.
    If the destination account is of type 'SAVINGS', the transaction is designated as type 'SAVINGS' instead of 'TRANSFER'.
    Returns the number of transfers linked/deduplicated.
    """
    # Fetch all accounts for the user
    accounts = db.query(Account).filter(Account.user_id == user_id).all()
    account_ids = [a.id for a in accounts]
    if not account_ids:
        return 0

    # Fetch transactions that are not currently type 'TRANSFER' or 'SAVINGS' (with destination account)
    transactions = db.query(Transaction).filter(
        Transaction.account_id.in_(account_ids),
        Transaction.type != "TRANSFER",
        Transaction.destination_account_id.is_(None)
    ).order_by(Transaction.date.asc()).all()
    
    # Split into potential debits and credits
    debits = []
    credits = []
    
    for tx in transactions:
        # A transaction is a debit candidate if type is EXPENSE/INVESTMENT/SAVINGS/LOAN/TAX
        if tx.type in ["EXPENSE", "INVESTMENT", "SAVINGS", "LOAN", "TAX"]:
            debits.append(tx)
        # A transaction is a credit candidate if type is INCOME
        elif tx.type in ["INCOME"]:
            credits.append(tx)
            
    linked_count = 0
    matched_credits = set()
    
    for debit in debits:
        debit_amount = abs(debit.amount)
        for credit in credits:
            if credit.id in matched_credits:
                continue
            
            credit_amount = abs(credit.amount)
            # 1. Amounts must match exactly
            if debit_amount != credit_amount:
                continue
                
            # 2. Must be different accounts
            if debit.account_id == credit.account_id:
                continue
                
            # 3. Date window check
            date_diff = abs((debit.date - credit.date).days)
            if date_diff <= days_window:
                # Found a transfer match!
                dest_account = db.query(Account).filter(Account.id == credit.account_id).first()
                if dest_account and dest_account.account_type == "SAVINGS":
                    debit.type = "SAVINGS"
                else:
                    debit.type = "TRANSFER"
                    
                debit.destination_account_id = credit.account_id
                debit.amount = debit_amount
                
                # Merge descriptions
                debit.description = f"Transfer: {debit.description} -> {credit.description}"
                
                # Migrate any linked receipts from the credit side
                for receipt in credit.receipts:
                    receipt.transaction_id = debit.id
                
                # Delete the redundant credit side
                db.delete(credit)
                matched_credits.add(credit.id)
                linked_count += 1
                break
                
    if linked_count > 0:
        db.commit()
        
    return linked_count
