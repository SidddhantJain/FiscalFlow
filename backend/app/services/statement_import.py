import io
import pandas as pd
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.transaction import Transaction
from app.models.account import Account
from app.models.investment import Investment
from app.models.category import Category

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
    },
    "AXIS_CSV": {
        "date_col": "Tran Date",
        "desc_col": "PARTICULARS",
        "debit_col": "DR",
        "credit_col": "CR",
        "ref_col": "CHQNO",
        "date_format": "%d-%m-%Y"
    },
    "GROWW_DEMAT": {
        "is_demat": True,
        "broker": "Groww",
        "symbol_cols": ["Symbol", "Stock Name", "Scheme Name", "Company Name", "Instrument"],
        "qty_cols": ["Quantity", "Qty", "Shares", "Units", "Total Quantity"],
        "buy_price_cols": ["Avg Price", "Buy Price", "Average Price", "Buy Avg Price", "Purchase Price"],
        "curr_price_cols": ["Current Price", "Market Price", "CMP", "NAV", "Last Price"],
        "invested_cols": ["Invested Value", "Invested Amount", "Total Invested", "Investment Value"],
        "current_val_cols": ["Current Value", "Present Value", "Market Value", "Total Current Value"],
        "date_cols": ["Trade Date", "Date", "Buy Date", "Execution Date"],
        "type_cols": ["Type", "Trade Type", "Transaction Type", "Order Type"]
    },
    "ANGELONE_DEMAT": {
        "is_demat": True,
        "broker": "Angel One",
        "symbol_cols": ["Symbol", "Scrip Name", "Stock", "Instrument"],
        "qty_cols": ["Qty", "Quantity", "Shares", "Trade Qty"],
        "buy_price_cols": ["Price", "Trade Price", "Avg Price", "Buy Price"],
        "curr_price_cols": ["CMP", "Current Price", "Market Price", "NAV"],
        "invested_cols": ["Trade Value", "Net Amount", "Invested Value", "Total Amount"],
        "current_val_cols": ["Current Value", "Market Value", "Valuation"],
        "date_cols": ["Trade Date", "Date", "Txn Date"],
        "type_cols": ["Buy/Sell", "Type", "Trade Type"]
    },
    "ZERODHA_DEMAT": {
        "is_demat": True,
        "broker": "Zerodha",
        "symbol_cols": ["Symbol", "Instrument", "Tradingsymbol"],
        "qty_cols": ["Quantity", "Qty"],
        "buy_price_cols": ["Price", "Buy Price", "Average Price"],
        "curr_price_cols": ["Last Price", "CMP", "Market Price"],
        "invested_cols": ["Trade Value", "Invested Value"],
        "current_val_cols": ["Current Value", "Market Value"],
        "date_cols": ["Trade Date", "Order Execution Time", "Date"],
        "type_cols": ["Trade Type", "Type"]
    },
    "GENERIC_DEMAT": {
        "is_demat": True,
        "broker": "Demat",
        "symbol_cols": ["Symbol", "Name", "Stock Name", "Scheme Name"],
        "qty_cols": ["Quantity", "Units", "Qty"],
        "buy_price_cols": ["Buy Price", "Avg Price", "Price"],
        "curr_price_cols": ["Current Price", "CMP", "NAV"],
        "invested_cols": ["Invested Value", "Invested Amount"],
        "current_val_cols": ["Current Value", "Valuation"],
        "date_cols": ["Date", "Trade Date"],
        "type_cols": ["Type", "Transaction Type"]
    }
}

def clean_decimal(val) -> Decimal:
    """Helper to safely parse decimal values from bank/demat statement columns."""
    if val is None:
        return Decimal("0.00")
    val_str = str(val).strip().replace(",", "").replace("₹", "").replace("$", "")
    if not val_str or val_str.lower() in ("nan", "-", "--", "nil", "none", "null"):
        return Decimal("0.00")
    try:
        return Decimal(val_str)
    except Exception:
        return Decimal("0.00")

def find_column_val(row: pd.Series, candidate_cols: list[str], default="") -> str:
    """Finds the first available column matching candidate list in row."""
    for col in candidate_cols:
        for actual_col in row.index:
            if actual_col.strip().lower() == col.strip().lower():
                val = str(row[actual_col]).strip()
                if val and val.lower() != "nan":
                    return val
    return default

def find_column_decimal(row: pd.Series, candidate_cols: list[str]) -> Decimal:
    """Finds the first available decimal value matching candidate list in row."""
    for col in candidate_cols:
        for actual_col in row.index:
            if actual_col.strip().lower() == col.strip().lower():
                return clean_decimal(row[actual_col])
    return Decimal("0.00")

def parse_statement(file_bytes: bytes, file_name: str, bank_type: str = "DEFAULT_CSV") -> list[dict]:
    """
    Parses a bank or demat statement file (CSV or XLSX) into a list of normalized transaction dictionaries.
    """
    template = BANK_TEMPLATES.get(bank_type, BANK_TEMPLATES["DEFAULT_CSV"])
    
    # Read file bytes into pandas DataFrame
    if file_name.endswith(".xlsx") or file_name.endswith(".xls"):
        engine = "xlrd" if file_name.endswith(".xls") else "openpyxl"
        df = pd.read_excel(io.BytesIO(file_bytes), engine=engine)
    else:
        df = pd.read_csv(io.BytesIO(file_bytes))
        
    # Clean column names (strip whitespace)
    df.columns = [str(c).strip() for c in df.columns]
    
    if template.get("is_demat"):
        holdings, txs = parse_demat_dataframe(df, template)
        return txs
        
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
            
            if "withdrawal_col" in template and template["withdrawal_col"] in row:
                w_amt = clean_decimal(row.get(template["withdrawal_col"], 0))
                d_amt = clean_decimal(row.get(template["deposit_col"], 0))
                
                if w_amt > 0:
                    amount = w_amt
                    tx_type = "EXPENSE"
                elif d_amt > 0:
                    amount = d_amt
                    tx_type = "INCOME"
                else:
                    continue
            elif "debit_col" in template and template["debit_col"] in row:
                w_amt = clean_decimal(row.get(template["debit_col"], 0))
                d_amt = clean_decimal(row.get(template["credit_col"], 0))
                
                if w_amt > 0:
                    amount = w_amt
                    tx_type = "EXPENSE"
                elif d_amt > 0:
                    amount = d_amt
                    tx_type = "INCOME"
                else:
                    continue
            else:
                val = clean_decimal(row.get(template["amount_col"], 0))
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
            continue
            
    return parsed_transactions

def parse_demat_dataframe(df: pd.DataFrame, template: dict) -> tuple[list[dict], list[dict]]:
    """
    Extracts structured stock/MF holdings and investment transactions from Demat statements.
    """
    broker = template.get("broker", "Groww")
    holdings = []
    transactions = []
    
    for _, row in df.iterrows():
        try:
            symbol = find_column_val(row, template["symbol_cols"])
            if not symbol:
                continue
                
            qty = find_column_decimal(row, template["qty_cols"])
            buy_price = find_column_decimal(row, template["buy_price_cols"])
            curr_price = find_column_decimal(row, template["curr_price_cols"])
            invested_val = find_column_decimal(row, template["invested_cols"])
            current_val = find_column_decimal(row, template["current_val_cols"])
            
            # Calculate missing metrics
            if invested_val <= 0 and qty > 0 and buy_price > 0:
                invested_val = qty * buy_price
            if current_val <= 0 and qty > 0:
                if curr_price > 0:
                    current_val = qty * curr_price
                else:
                    current_val = invested_val
            if curr_price <= 0 and qty > 0 and current_val > 0:
                curr_price = current_val / qty
            if buy_price <= 0 and qty > 0 and invested_val > 0:
                buy_price = invested_val / qty
                
            # Date detection
            raw_date = find_column_val(row, template["date_cols"])
            trade_date = date.today()
            if raw_date:
                try:
                    trade_date = pd.to_datetime(raw_date).date()
                except Exception:
                    trade_date = date.today()
                    
            # Name and Symbol detection
            name_val = find_column_val(row, ["Stock Name", "Scheme Name", "Company Name", "Scrip Name", "Name", "Instrument"]) or symbol
            ticker_val = find_column_val(row, ["Symbol", "Tradingsymbol", "Ticker"]) or symbol.split()[0].upper()
            
            # Determine Asset Class from row context
            row_text = (" ".join([str(v) for v in row.values if pd.notna(v)]) + f" {symbol} {name_val}").lower()
            asset_class = "STOCK"
            if any(k in row_text for k in ["fund", "mf", "growth", "direct", "index", "parag", "quant", "uti", "mirae", "axis", "ppfas"]):
                if "elss" in row_text or "tax" in row_text:
                    asset_class = "ELSS"
                elif "index" in row_text or "nifty" in row_text:
                    asset_class = "INDEX_FUND"
                else:
                    asset_class = "MUTUAL_FUND"
            elif any(k in row_text for k in ["etf", "goldbees", "niftybees", "juniorbees"]):
                asset_class = "ETF"
                
            # Transaction Type
            raw_type = find_column_val(row, template["type_cols"], "BUY").upper()
            tx_type = "INVESTMENT"
            if "SELL" in raw_type:
                tx_type = "INCOME"
            elif "SIP" in raw_type:
                tx_type = "INVESTMENT"
                
            holdings.append({
                "name": name_val,
                "symbol": ticker_val,
                "asset_class": asset_class,
                "broker": broker,
                "units": qty,
                "purchase_price": buy_price,
                "current_value": current_val,
                "buy_date": datetime.combine(trade_date, datetime.min.time())
            })
            
            tx_amount = invested_val if tx_type == "INVESTMENT" else current_val
            if tx_amount > 0:
                transactions.append({
                    "date": trade_date,
                    "description": f"Demat {raw_type}: {symbol} ({broker})",
                    "amount": tx_amount,
                    "type": tx_type,
                    "reference_number": f"{broker.upper()}-{symbol.replace(' ', '')[:8]}-{trade_date.strftime('%Y%m%d')}",
                    "tags": f"Investment, Stock, {broker}, {asset_class}"
                })
        except Exception:
            continue
            
    return holdings, transactions

def parse_demat_statement(file_bytes: bytes, file_name: str, broker_type: str = "GROWW_DEMAT") -> tuple[list[dict], list[dict]]:
    """Parses raw bytes from a Demat statement file."""
    template = BANK_TEMPLATES.get(broker_type, BANK_TEMPLATES["GROWW_DEMAT"])
    if file_name.endswith(".xlsx") or file_name.endswith(".xls"):
        engine = "xlrd" if file_name.endswith(".xls") else "openpyxl"
        df = pd.read_excel(io.BytesIO(file_bytes), engine=engine)
    else:
        df = pd.read_csv(io.BytesIO(file_bytes))
        
    df.columns = [str(c).strip() for c in df.columns]
    return parse_demat_dataframe(df, template)

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
        duplicate_query = db.query(Transaction).filter(
            Transaction.account_id == account_id,
            Transaction.date == data["date"],
            Transaction.amount == data["amount"]
        )
        if data.get("reference_number"):
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
            reference_number=data.get("reference_number"),
            tags=data.get("tags")
        )
        db.add(tx)
        
        # Adjust account balance
        if data["type"] == "INCOME":
            account.current_balance += data["amount"]
        elif data["type"] in ["EXPENSE", "INVESTMENT", "SAVINGS"]:
            account.current_balance -= data["amount"]
            
        imported_count += 1
        
    if imported_count > 0:
        db.commit()
        
    return imported_count

def import_demat_holdings(db: Session, user_id: int, account_id: int, file_bytes: bytes, file_name: str, broker_type: str = "GROWW_DEMAT") -> dict:
    """
    Parses and syncs Demat stock/mutual fund holdings into the user's Investment portfolio and ledger.
    """
    holdings, txs = parse_demat_statement(file_bytes, file_name, broker_type)
    
    imported_holdings_count = 0
    for h in holdings:
        existing = db.query(Investment).filter(
            Investment.user_id == user_id,
            Investment.name == h["name"]
        ).first()
        
        if existing:
            existing.units = h["units"]
            existing.purchase_price = h["purchase_price"]
            existing.current_value = h["current_value"]
            existing.broker = h["broker"]
            existing.account_id = account_id
            existing.last_updated = datetime.utcnow()
            imported_holdings_count += 1
        else:
            new_inv = Investment(
                user_id=user_id,
                name=h["name"],
                symbol=h.get("symbol"),
                asset_class=h["asset_class"],
                account_id=account_id,
                broker=h["broker"],
                units=h["units"],
                purchase_price=h["purchase_price"],
                current_value=h["current_value"],
                buy_date=h.get("buy_date"),
                last_updated=datetime.utcnow()
            )
            db.add(new_inv)
            imported_holdings_count += 1
            
    db.commit()
    
    imported_tx_count = import_statement_transactions(db, account_id, txs)
    
    return {
        "imported_holdings": imported_holdings_count,
        "imported_transactions": imported_tx_count
    }
