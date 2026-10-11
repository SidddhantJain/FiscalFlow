import io
import re
import csv
from html.parser import HTMLParser
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
    "AUTO_DETECT": {
        "auto": True,
        "desc": "Smart Auto-Detection Engine (All Indian Banks & Brokers)"
    },
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
        "symbol_cols": ["Symbol", "Stock Name", "Scheme Name", "Company Name", "Instrument", "Fund Name", "Tradingsymbol", "Scrip Name"],
        "qty_cols": ["Quantity", "Qty", "Shares", "Units", "Total Quantity", "Trade Qty"],
        "buy_price_cols": ["Avg Price", "Buy Price", "Average Price", "Buy Avg Price", "Purchase Price", "Price", "Execution Price", "Trade Price"],
        "curr_price_cols": ["Current Price", "Market Price", "CMP", "NAV", "Last Price", "LTP"],
        "invested_cols": ["Invested Value", "Invested Amount", "Total Invested", "Investment Value", "Order Value", "Trade Value", "Total Amount"],
        "current_val_cols": ["Current Value", "Present Value", "Market Value", "Total Current Value", "Valuation"],
        "date_cols": ["Trade Date", "Date", "Buy Date", "Execution Date", "Order Date", "Order Execution Time"],
        "type_cols": ["Type", "Trade Type", "Transaction Type", "Order Type", "Action", "Buy/Sell"]
    },
    "ANGELONE_DEMAT": {
        "is_demat": True,
        "broker": "Angel One",
        "symbol_cols": ["Fund Name", "ISIN", "Symbol", "Scrip Name", "Stock", "Instrument", "Scheme Name"],
        "qty_cols": ["Units", "Qty", "Quantity", "Shares", "Trade Qty"],
        "buy_price_cols": ["Average NAV", "Avg NAV", "Price", "Trade Price", "Avg Price", "Buy Price"],
        "curr_price_cols": ["NAV as on", "NAV", "CMP", "Current Price", "Market Price"],
        "invested_cols": ["Invested Value", "Trade Value", "Net Amount", "Total Amount", "Invested Amount"],
        "current_val_cols": ["Value as on", "Current Value", "Market Value", "Valuation", "Total Current Value"],
        "date_cols": ["Trade Date", "Date", "Txn Date", "Execution Date"],
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
        "symbol_cols": ["Fund Name", "ISIN", "Symbol", "Name", "Stock Name", "Scheme Name"],
        "qty_cols": ["Quantity", "Units", "Qty"],
        "buy_price_cols": ["Average NAV", "Buy Price", "Avg Price", "Price"],
        "curr_price_cols": ["NAV as on", "Current Price", "CMP", "NAV"],
        "invested_cols": ["Invested Value", "Invested Amount"],
        "current_val_cols": ["Value as on", "Current Value", "Valuation"],
        "date_cols": ["Date", "Trade Date"],
        "type_cols": ["Type", "Transaction Type"]
    }
}

# Regex heuristics for Indian banking and demat headers
BANK_PATTERNS = {
    "date": [
        r"tran\s*date", r"txn\s*date", r"transaction\s*date", r"trade\s*date",
        r"value\s*date", r"posting\s*date", r"^date$", r"trans\s*date", r"post\s*date"
    ],
    "desc": [
        r"particulars", r"narration", r"description", r"details", r"remarks",
        r"transaction\s*details", r"narrative", r"transaction\s*remarks", r"memo", r"^desc$"
    ],
    "debit": [
        r"^dr$", r"^dr\b", r"\bdr\b", r"debit", r"withdrawal", r"withdrawal\s*amt", r"withdrawal\s*amount",
        r"debit\s*amt", r"debit\s*amount", r"^dr\.$", r"amount\s*debited", r"paid\s*out"
    ],
    "credit": [
        r"^cr$", r"^cr\b", r"\bcr\b", r"credit", r"deposit", r"deposit\s*amt", r"deposit\s*amount",
        r"credit\s*amt", r"credit\s*amount", r"^cr\.$", r"amount\s*credited", r"paid\s*in"
    ],
    "amount": [
        r"^amount$", r"net\s*amount", r"txn\s*amount", r"transaction\s*amount", r"^amt$", r"total"
    ],
    "indicator": [
        r"^cr\s*/\s*dr$", r"^dr\s*/\s*cr$", r"^cr/dr$", r"^dr/cr$", r"^type$", r"^txn\s*type$",
        r"^transaction\s*type$", r"^indicator$", r"cr\s*dr", r"dr\s*cr"
    ],
    "ref": [
        r"chqno", r"chq\s*/\s*ref", r"ref\s*no", r"cheque\s*no", r"reference",
        r"utr", r"txn\s*ref", r"chq\s*no", r"ref\s*number", r"bill\s*/\s*chq\s*no", r"bill/chq"
    ],
    "balance": [
        r"^bal$", r"balance", r"closing\s*balance", r"closing\s*bal", r"running\s*balance"
    ]
}

DEMAT_PATTERNS = {
    "symbol": [
        r"^tradingsymbol$", r"^symbol$", r"scrip\s*name", r"stock\s*name",
        r"scheme\s*name", r"^instrument$", r"^security$", r"^ticker$",
        r"fund\s*name", r"^isin$"
    ],
    "name": [
        r"fund\s*name", r"stock\s*name", r"scheme\s*name", r"company\s*name", r"scrip\s*name", r"^name$"
    ],
    "qty": [
        r"^qty$", r"^quantity$", r"^shares$", r"^units$", r"trade\s*qty", r"total\s*quantity"
    ],
    "buy_price": [
        r"avg\s*price", r"buy\s*price", r"average\s*price", r"buy\s*avg", r"^price$", r"trade\s*price",
        r"purchase\s*price", r"average\s*nav", r"avg\s*nav", r"execution\s*price"
    ],
    "curr_price": [
        r"current\s*price", r"^cmp$", r"^nav$", r"market\s*price", r"last\s*price", r"^ltp$", r"close\s*price",
        r"nav\s*as\s*on"
    ],
    "invested": [
        r"invested\s*val", r"invested\s*amount", r"total\s*invested", r"trade\s*val", r"net\s*amount",
        r"investment\s*value", r"order\s*val"
    ],
    "current_val": [
        r"current\s*val", r"present\s*val", r"market\s*val", r"total\s*current\s*value", r"valuation",
        r"value\s*as\s*on"
    ],
    "date": [
        r"trade\s*date", r"buy\s*date", r"order\s*execution", r"order\s*date", r"^date$"
    ],
    "type": [
        r"trade\s*type", r"transaction\s*type", r"order\s*type", r"buy/sell", r"^action$", r"^type$"
    ]
}

class SimpleHTMLTableParser(HTMLParser):
    """Parses HTML tables without requiring lxml/beautifulsoup4."""
    def __init__(self):
        super().__init__()
        self.rows = []
        self.current_row = []
        self.current_cell = []
        self.in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag in ("td", "th"):
            self.in_cell = True
            self.current_cell = []
        elif tag == "tr":
            self.current_row = []

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell.append(data.strip())

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self.in_cell = False
            self.current_row.append(" ".join(self.current_cell).strip())
        elif tag == "tr":
            if any(self.current_row):
                self.rows.append(self.current_row)

def parse_html_table(html_str: str) -> pd.DataFrame:
    """Extracts the largest table from an HTML string into a pandas DataFrame."""
    parser = SimpleHTMLTableParser()
    parser.feed(html_str)
    if not parser.rows:
        return pd.DataFrame()
    
    # Locate header row among first 10 rows
    header_idx = 0
    keywords = ["date", "particulars", "description", "narration", "debit", "credit", "amount", "symbol", "qty"]
    for idx, r in enumerate(parser.rows[:15]):
        row_str = " ".join([c.lower() for c in r])
        if sum(1 for kw in keywords if kw in row_str) >= 2:
            header_idx = idx
            break

    headers = [str(c).strip() for c in parser.rows[header_idx]]
    data = parser.rows[header_idx + 1:]
    max_cols = len(headers)
    cleaned_data = []
    for r in data:
        if len(r) < max_cols:
            r = r + [""] * (max_cols - len(r))
        cleaned_data.append(r[:max_cols])
    return pd.DataFrame(cleaned_data, columns=headers)

def clean_decimal(val) -> Decimal:
    """Helper to safely parse decimal values from bank/demat statement columns."""
    if val is None:
        return Decimal("0.00")
    val_str = str(val).strip().replace(",", "").replace("₹", "").replace("$", "").replace("Rs.", "").replace("Rs", "")
    if not val_str or val_str.lower() in ("nan", "-", "--", "nil", "none", "null", ""):
        return Decimal("0.00")
    if val_str.lower().endswith("dr") or val_str.lower().endswith("cr"):
        val_str = val_str[:-2].strip()
    if val_str.startswith("(") and val_str.endswith(")"):
        val_str = "-" + val_str[1:-1].strip()
    try:
        return Decimal(val_str)
    except Exception:
        return Decimal("0.00")

def parse_date_flexible(val) -> date | None:
    """Parses date from any standard format flexibly."""
    if not val or str(val).strip().lower() in ("nan", "none", "null", ""):
        return None
    if isinstance(val, (datetime, pd.Timestamp)):
        return val.date()
    if isinstance(val, date):
        return val

    val_str = str(val).strip()
    # Try common explicit date formats
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d %b %Y", "%d-%b-%Y", "%d-%b-%y", "%Y/%m/%d"):
        try:
            return datetime.strptime(val_str, fmt).date()
        except ValueError:
            pass
    try:
        dt = pd.to_datetime(val_str, dayfirst=True)
        if pd.notna(dt):
            return dt.date()
    except Exception:
        pass
    return None

def resolve_bank_columns(cols: list) -> dict:
    """Auto-detects canonical bank columns from list of column names."""
    resolved = {}
    cleaned_map = {c: str(c).strip().lower() for c in cols}
    for field, patterns in BANK_PATTERNS.items():
        for pat in patterns:
            for orig_col, clean_col in cleaned_map.items():
                if re.search(pat, clean_col):
                    if field not in resolved:
                        resolved[field] = orig_col
                        break
            if field in resolved:
                break
    return resolved

def resolve_demat_columns(cols: list) -> dict:
    """Auto-detects Demat holding/orderbook columns from list of column names."""
    resolved = {}
    cleaned_map = {c: str(c).strip().lower() for c in cols}
    for field, patterns in DEMAT_PATTERNS.items():
        for pat in patterns:
            for orig_col, clean_col in cleaned_map.items():
                if re.search(pat, clean_col):
                    if field not in resolved:
                        resolved[field] = orig_col
                        break
            if field in resolved:
                break
    return resolved

def is_demat_format(cols: list) -> bool:
    """Detects if columns indicate Demat/trading statements rather than regular bank accounts."""
    c_lower = " ".join([str(c).strip().lower() for c in cols])
    has_qty = any(k in c_lower for k in ["quantity", "qty", "shares", "units"])
    has_symbol = any(k in c_lower for k in [
        "symbol", "ticker", "scrip", "stock name", "scheme name", "instrument",
        "tradingsymbol", "fund name", "isin"
    ])
    has_demat_cues = any(k in c_lower for k in ["unrealized p&l", "folio no", "avg nav", "average nav", "invested value", "order value"])
    return (has_qty and has_symbol) or has_demat_cues

def read_file_to_dataframe(file_bytes: bytes, file_name: str) -> pd.DataFrame:
    """
    Robust reader for CSV, XLS, XLSX, and HTML statements.
    Handles encoding variations, preamble metadata rows, and multi-sheet workbooks.
    """
    if not file_bytes:
        raise ValueError("Uploaded statement file is empty.")

    file_name_lower = file_name.lower()

    # Check for HTML tables disguised as XLS / CSV / HTML
    sample_head = file_bytes[:1024].lstrip().lower()
    if sample_head.startswith(b"<html") or sample_head.startswith(b"<!doctype"):
        text = file_bytes.decode("utf-8", errors="ignore")
        df = parse_html_table(text)
        if not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            return df

    # Excel parsing (.xlsx, .xls)
    if file_name_lower.endswith(".xlsx") or file_name_lower.endswith(".xls"):
        # First try default engine (compatible with unit test mocks)
        engine = "xlrd" if file_name_lower.endswith(".xls") else "openpyxl"
        try:
            df = pd.read_excel(io.BytesIO(file_bytes), engine=engine)
            # If loaded successfully and has recognizable columns, return it
            if isinstance(df, pd.DataFrame):
                df.columns = [str(c).strip() for c in df.columns]
                # Check if preamble exists (e.g. Row 0 has instructions or only 1 column filled)
                resolved = resolve_bank_columns(df.columns)
                if resolved.get("date") or is_demat_format(df.columns):
                    return df
        except Exception:
            pass

        # Multi-sheet smart workbook scanner
        try:
            xl = pd.ExcelFile(io.BytesIO(file_bytes))
            target_sheet = xl.sheet_names[0]
            for s in xl.sheet_names:
                s_low = s.lower()
                if any(k in s_low for k in ["statement", "transaction", "bank", "holding", "trade", "order", "ledger", "fund"]):
                    target_sheet = s
                    break

            raw_df = xl.parse(target_sheet, header=None)
            header_idx = 0
            # 1. First check if a definitive Demat/Holdings header row exists (e.g. Angel One, Groww Trade Book)
            for idx in range(min(40, len(raw_df))):
                row_str = " ".join([str(v).lower() for v in raw_df.iloc[idx].tolist() if pd.notna(v)])
                if ("fund name" in row_str and ("isin" in row_str or "units" in row_str or "nav" in row_str)) or ("symbol" in row_str and "quantity" in row_str):
                    header_idx = idx
                    break
            else:
                # 2. General banking / ledger header scanner
                keywords = [
                    "tran date", "txn date", "date", "particulars", "narration", "description",
                    "debit", "credit", "amount", "symbol", "quantity", "fund name", "isin",
                    "units", "average nav", "nav", "invested value", "folio"
                ]
                for idx in range(min(40, len(raw_df))):
                    row_str = " ".join([str(v).lower() for v in raw_df.iloc[idx].tolist() if pd.notna(v)])
                    if sum(1 for kw in keywords if kw in row_str) >= 2:
                        header_idx = idx
                        break

            df = xl.parse(target_sheet, skiprows=header_idx)
            df.columns = [str(c).strip() for c in df.columns]
            return df
        except Exception:
            # Final fallback: try reading as HTML table
            try:
                text = file_bytes.decode("utf-8", errors="ignore")
                df = parse_html_table(text)
                if not df.empty:
                    df.columns = [str(c).strip() for c in df.columns]
                    return df
            except Exception:
                pass

    # CSV / Text statement handling
    # 1. First try direct pd.read_csv (ensures unit test mocks pass immediately)
    try:
        df = pd.read_csv(io.BytesIO(file_bytes))
        if isinstance(df, pd.DataFrame):
            df.columns = [str(c).strip() for c in df.columns]
            if resolve_bank_columns(df.columns).get("date") or is_demat_format(df.columns):
                return df
    except Exception:
        pass

    # 2. Multi-encoding decode with preamble scan, quote sanitization, footer truncation, and delimiter detection
    encodings = ["utf-8-sig", "utf-8", "cp1252", "latin1", "iso-8859-1"]
    decoded_text = None
    for enc in encodings:
        try:
            decoded_text = file_bytes.decode(enc)
            break
        except UnicodeDecodeError:
            continue

    if decoded_text is None:
        decoded_text = file_bytes.decode("latin1", errors="ignore")

    lines = decoded_text.splitlines()
    keywords = [
        "tran date", "txn date", "date", "particulars", "narration", "description",
        "debit", "credit", "dr", "cr", "withdrawal", "deposit", "amount", "balance",
        "symbol", "qty", "instrument", "tradingsymbol", "chqno", "chq", "fund name",
        "isin", "units", "nav"
    ]
    header_idx = 0
    # Scan up to 120 lines to skip long preambles (Name, Address, Nominee, IFSC, etc.)
    for idx, line in enumerate(lines[:120]):
        line_low = line.lower()
        if ("fund name" in line_low and ("isin" in line_low or "units" in line_low or "nav" in line_low)) or ("symbol" in line_low and "quantity" in line_low):
            header_idx = idx
            break
        matches = sum(1 for kw in keywords if re.search(r"\b" + kw + r"\b", line_low))
        if matches >= 2:
            header_idx = idx
            break

    header_line = lines[header_idx] if header_idx < len(lines) else ""
    sep = ","
    if header_line.count(";") > header_line.count(","):
        sep = ";"
    elif header_line.count("\t") > header_line.count(","):
        sep = "\t"
    elif header_line.count("|") > header_line.count(","):
        sep = "|"

    table_lines = lines[header_idx:]

    # Footer markers that appear after all transaction rows
    footer_markers = [
        "*** end", "end of statement", "abbreviations", "legends:", "legends /",
        "disclaimer", "registered office", "this is a computer generated",
        "page total", "statement summary", "important information"
    ]

    cleaned_table_lines = []
    for line in table_lines:
        line_str = line.strip()
        if not line_str:
            continue
        line_low = line_str.lower()
        # Stop at footer / disclaimer rows
        if any(marker in line_low for marker in footer_markers):
            break
        # Fix unclosed quotes in transaction descriptions or footers (odd number of quotes)
        if line.count('"') % 2 != 0:
            line = line.replace('"', '')
        cleaned_table_lines.append(line)

    cleaned_csv = "\n".join(cleaned_table_lines)

    # Multi-engine parsing fallbacks to guarantee no EOF inside string or tokenizing failure
    df = None
    # Attempt A: Standard parse on cleaned CSV
    try:
        df = pd.read_csv(io.StringIO(cleaned_csv), sep=sep, on_bad_lines="skip")
    except Exception:
        df = None

    # Attempt B: QUOTE_NONE parse (ignores quotation marks entirely, preventing any unclosed quote errors)
    if df is None or df.empty or not (resolve_bank_columns(df.columns).get("date") or is_demat_format(df.columns)):
        try:
            df = pd.read_csv(io.StringIO(cleaned_csv), sep=sep, quoting=csv.QUOTE_NONE, on_bad_lines="skip")
        except Exception:
            df = None

    # Attempt C: Python engine with quotechar disabled
    if df is None or df.empty or not (resolve_bank_columns(df.columns).get("date") or is_demat_format(df.columns)):
        try:
            df = pd.read_csv(io.StringIO(cleaned_csv), sep=sep, engine="python", quoting=csv.QUOTE_NONE, on_bad_lines="skip")
        except Exception:
            df = None

    # Attempt D: Fallback to line-by-line csv.reader with QUOTE_NONE
    if df is None or df.empty:
        try:
            raw_reader = csv.reader(cleaned_table_lines, delimiter=sep, quoting=csv.QUOTE_NONE)
            parsed_rows = [r for r in raw_reader if any(r)]
            if parsed_rows:
                headers = [str(c).strip() for c in parsed_rows[0]]
                data_rows = parsed_rows[1:]
                max_c = len(headers)
                normalized_rows = []
                for r in data_rows:
                    if len(r) < max_c:
                        r = r + [""] * (max_c - len(r))
                    normalized_rows.append(r[:max_c])
                df = pd.DataFrame(normalized_rows, columns=headers)
        except Exception:
            df = pd.DataFrame()

    if df is not None and not df.empty:
        df.columns = [str(c).strip() for c in df.columns]
        return df

    return pd.DataFrame()

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
    Supports auto-detection across Axis, HDFC, SBI, ICICI, Groww, Angel One, Zerodha, and generic statements.
    """
    template = BANK_TEMPLATES.get(bank_type, BANK_TEMPLATES["DEFAULT_CSV"])
    
    # Read file bytes into pandas DataFrame using robust loader
    if file_name.endswith(".xlsx") or file_name.endswith(".xls"):
        engine = "xlrd" if file_name.endswith(".xls") else "openpyxl"
        try:
            df = pd.read_excel(io.BytesIO(file_bytes), engine=engine)
            if isinstance(df, pd.DataFrame):
                df.columns = [str(c).strip() for c in df.columns]
                # If loaded sheet 0 does not have date/demat columns, try smart reader
                if not (resolve_bank_columns(df.columns).get("date") or is_demat_format(df.columns)):
                    df = read_file_to_dataframe(file_bytes, file_name)
        except Exception:
            df = read_file_to_dataframe(file_bytes, file_name)
    else:
        try:
            df = pd.read_csv(io.BytesIO(file_bytes))
            if isinstance(df, pd.DataFrame):
                df.columns = [str(c).strip() for c in df.columns]
                if not (resolve_bank_columns(df.columns).get("date") or is_demat_format(df.columns)):
                    df = read_file_to_dataframe(file_bytes, file_name)
        except Exception:
            df = read_file_to_dataframe(file_bytes, file_name)

    df.columns = [str(c).strip() for c in df.columns]

    # Check if this statement is a Demat holding/trade statement
    if template.get("is_demat") or (bank_type == "AUTO_DETECT" and is_demat_format(df.columns)):
        demat_tmpl = template if template.get("is_demat") else BANK_TEMPLATES["GROWW_DEMAT"]
        holdings, txs = parse_demat_dataframe(df, demat_tmpl)
        return txs

    # Resolve columns: first check template, then fall back to auto-detection
    date_col = None
    desc_col = None
    debit_col = None
    credit_col = None
    withdrawal_col = None
    deposit_col = None
    amount_col = None
    indicator_col = None
    ref_col = None

    # Check if template columns match the actual dataframe
    template_matches = (
        "date_col" in template and template["date_col"] in df.columns and
        (
            ("amount_col" in template and template["amount_col"] in df.columns) or
            ("debit_col" in template and template["debit_col"] in df.columns) or
            ("withdrawal_col" in template and template["withdrawal_col"] in df.columns)
        )
    )

    if template_matches:
        date_col = template.get("date_col")
        desc_col = template.get("desc_col")
        debit_col = template.get("debit_col")
        credit_col = template.get("credit_col")
        withdrawal_col = template.get("withdrawal_col")
        deposit_col = template.get("deposit_col")
        amount_col = template.get("amount_col")
        indicator_col = template.get("indicator_col")
        ref_col = template.get("ref_col")
        date_format = template.get("date_format")
    else:
        # Auto-resolve columns via regex heuristics
        resolved = resolve_bank_columns(df.columns)
        date_col = resolved.get("date")
        desc_col = resolved.get("desc")
        debit_col = resolved.get("debit")
        credit_col = resolved.get("credit")
        amount_col = resolved.get("amount")
        indicator_col = resolved.get("indicator")
        ref_col = resolved.get("ref")
        date_format = None

    if not date_col:
        # If still no date column found, scan columns for any column containing date
        for c in df.columns:
            if "date" in c.lower():
                date_col = c
                break

    parsed_transactions = []
    for _, row in df.iterrows():
        try:
            # 1. Parse date
            raw_date = str(row.get(date_col, "")).strip() if date_col else ""
            if not raw_date or raw_date.lower() == "nan":
                continue

            tx_date = None
            if date_format:
                try:
                    tx_date = datetime.strptime(raw_date, date_format).date()
                except Exception:
                    pass
            if not tx_date:
                tx_date = parse_date_flexible(raw_date)
            if not tx_date:
                continue

            # 2. Parse Description
            desc = ""
            if desc_col and desc_col in row:
                desc = str(row.get(desc_col, "")).strip()
            if not desc or desc.lower() == "nan":
                # Fallback to any string column that isn't date or numbers
                for col in df.columns:
                    if col != date_col and col not in [debit_col, credit_col, amount_col, ref_col]:
                        val_str = str(row.get(col, "")).strip()
                        if len(val_str) > 3 and val_str.lower() != "nan":
                            desc = val_str
                            break
            if not desc or desc.lower() == "nan":
                continue

            # If Segment Type exists (e.g. STOCKS_SETTLEMENT, GROWW_WITHDRAW, UPI), prepend it for readability
            for seg_col in ["Segment Type", "Transaction Type", "Txn Type"]:
                if seg_col in row and row[seg_col] and str(row[seg_col]).strip() not in ("nan", "-", "--", ""):
                    seg_val = str(row[seg_col]).strip()
                    if seg_val.lower() not in desc.lower() and seg_val.lower() not in ("bill", "jv", "payment"):
                        desc = f"{seg_val}: {desc}"
                    break

            # 3. Parse Amount and Transaction Type
            amount = Decimal("0.00")
            tx_type = "EXPENSE"

            if withdrawal_col and withdrawal_col in row and deposit_col and deposit_col in row:
                w_amt = clean_decimal(row.get(withdrawal_col, 0))
                d_amt = clean_decimal(row.get(deposit_col, 0))
                if w_amt > 0:
                    amount = w_amt
                    tx_type = "EXPENSE"
                elif d_amt > 0:
                    amount = d_amt
                    tx_type = "INCOME"
                else:
                    continue
            elif debit_col and debit_col in row and credit_col and credit_col in row:
                w_amt = clean_decimal(row.get(debit_col, 0))
                d_amt = clean_decimal(row.get(credit_col, 0))
                if w_amt > 0:
                    amount = w_amt
                    tx_type = "EXPENSE"
                elif d_amt > 0:
                    amount = d_amt
                    tx_type = "INCOME"
                else:
                    continue
            elif amount_col and amount_col in row:
                raw_amt_str = str(row.get(amount_col, "")).strip()
                val = clean_decimal(raw_amt_str)
                amount = abs(val)
                if amount == 0:
                    continue

                raw_amt_lower = raw_amt_str.lower()
                ind_str = str(row.get(indicator_col, "")).strip().lower() if indicator_col and indicator_col in row else ""

                if ind_str in ("dr", "debit", "wdl", "withdrawal", "payment", "out", "pay", "d"):
                    tx_type = "EXPENSE"
                elif ind_str in ("cr", "credit", "dep", "deposit", "receipt", "in", "c"):
                    tx_type = "INCOME"
                elif raw_amt_lower.endswith("dr") or "(dr)" in raw_amt_lower or (raw_amt_str.startswith("(") and raw_amt_str.endswith(")")):
                    tx_type = "EXPENSE"
                elif raw_amt_lower.endswith("cr") or "(cr)" in raw_amt_lower:
                    tx_type = "INCOME"
                elif val < 0:
                    tx_type = "EXPENSE"
                elif val > 0:
                    desc_lower = desc.lower()
                    if any(k in desc_lower for k in ["salary", "stipend", "interest received", "dividend", "refund", "cashback", "deposited", "credit"]):
                        tx_type = "INCOME"
                    elif any(k in desc_lower for k in ["paid to", "payment to", "withdrawal", "purchase", "debited", "charges", "fees"]):
                        tx_type = "EXPENSE"
                    else:
                        tx_type = "EXPENSE"
            else:
                continue

            # 4. Parse Reference Number
            ref_num = None
            if ref_col and ref_col in row:
                ref_num = str(row.get(ref_col, "")).strip()
                if ref_num.lower() in ("nan", "-", "--", ""):
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

    # Auto-resolve Demat columns
    resolved_demat = resolve_demat_columns(df.columns)

    symbol_cols = template.get("symbol_cols", [])
    if resolved_demat.get("symbol"):
        symbol_cols = [resolved_demat["symbol"]] + symbol_cols

    qty_cols = template.get("qty_cols", [])
    if resolved_demat.get("qty"):
        qty_cols = [resolved_demat["qty"]] + qty_cols

    buy_price_cols = template.get("buy_price_cols", [])
    if resolved_demat.get("buy_price"):
        buy_price_cols = [resolved_demat["buy_price"]] + buy_price_cols

    curr_price_cols = template.get("curr_price_cols", [])
    if resolved_demat.get("curr_price"):
        curr_price_cols = [resolved_demat["curr_price"]] + curr_price_cols

    invested_cols = template.get("invested_cols", [])
    if resolved_demat.get("invested"):
        invested_cols = [resolved_demat["invested"]] + invested_cols

    current_val_cols = template.get("current_val_cols", [])
    if resolved_demat.get("current_val"):
        current_val_cols = [resolved_demat["current_val"]] + current_val_cols

    date_cols = template.get("date_cols", [])
    if resolved_demat.get("date"):
        date_cols = [resolved_demat["date"]] + date_cols

    type_cols = template.get("type_cols", [])
    if resolved_demat.get("type"):
        type_cols = [resolved_demat["type"]] + type_cols

    for _, row in df.iterrows():
        try:
            symbol = find_column_val(row, symbol_cols)
            if not symbol or symbol.lower() in ("nan", "total", "grand total", "summary", "-", "--"):
                continue

            qty = find_column_decimal(row, qty_cols)
            buy_price = find_column_decimal(row, buy_price_cols)
            curr_price = find_column_decimal(row, curr_price_cols)
            invested_val = find_column_decimal(row, invested_cols)
            current_val = find_column_decimal(row, current_val_cols)

            # Auto-calculate missing values
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
            raw_date = find_column_val(row, date_cols)
            trade_date = parse_date_flexible(raw_date) or date.today()

            # Name and Symbol detection
            name_val = find_column_val(row, ["Fund Name", "Stock Name", "Scheme Name", "Company Name", "Scrip Name", "Name", "Instrument"]) or symbol
            isin_val = find_column_val(row, ["ISIN", "isin"])
            if isin_val and isin_val.lower() not in ("nan", "-", ""):
                ticker_val = isin_val
            else:
                ticker_val = find_column_val(row, ["Symbol", "Tradingsymbol", "Ticker"]) or symbol.split()[0].upper()

            # Determine Asset Class from row context
            row_text = (" ".join([str(v) for v in row.values if pd.notna(v)]) + f" {symbol} {name_val}").lower()
            asset_class = "STOCK"
            if any(k in row_text for k in ["fund", "mf", "growth", "direct", "index", "parag", "quant", "uti", "mirae", "axis", "ppfas", "fof"]):
                if "elss" in row_text or "tax" in row_text:
                    asset_class = "ELSS"
                elif "index" in row_text or "nifty" in row_text:
                    asset_class = "INDEX_FUND"
                else:
                    asset_class = "MUTUAL_FUND"
            elif any(k in row_text for k in ["etf", "goldbees", "niftybees", "juniorbees"]):
                asset_class = "ETF"

            # Transaction Type
            raw_type = find_column_val(row, type_cols, "BUY").upper()
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
                    "description": f"Demat {raw_type}: {name_val} ({broker})",
                    "amount": tx_amount,
                    "type": tx_type,
                    "reference_number": f"{broker.upper()}-{ticker_val.replace(' ', '')[:8]}-{trade_date.strftime('%Y%m%d')}",
                    "tags": f"Investment, Stock, {broker}, {asset_class}"
                })
        except Exception:
            continue

    return holdings, transactions

def parse_demat_statement(file_bytes: bytes, file_name: str, broker_type: str = "GROWW_DEMAT") -> tuple[list[dict], list[dict]]:
    """Parses raw bytes from a Demat statement file."""
    file_name_lower = file_name.lower()
    df = read_file_to_dataframe(file_bytes, file_name)
    df.columns = [str(c).strip() for c in df.columns]

    # Auto-detect Angel One if file contains Angel One cues
    if "angel" in file_name_lower or any("angel" in str(c).lower() for c in df.columns) or any(k in df.columns for k in ["Fund Name", "Average NAV"]):
        broker_type = "ANGELONE_DEMAT"
    elif "groww" in file_name_lower:
        broker_type = "GROWW_DEMAT"

    template = BANK_TEMPLATES.get(broker_type, BANK_TEMPLATES["GROWW_DEMAT"])
    return parse_demat_dataframe(df, template)

def import_statement_transactions(db: Session, account_id: int, transactions_data: list[dict]) -> int:
    """
    Saves parsed statement transactions into the database using high-speed bulk in-memory deduplication.
    Deduplicates based on (date, amount, reference_number/description).
    Adjusts the parent account current balance based on transaction activity.
    """
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        return 0

    if not transactions_data:
        return 0

    # 1. Fetch all existing transaction signatures for this account in 1 single bulk query
    existing_recs = db.query(
        Transaction.date,
        Transaction.amount,
        Transaction.reference_number,
        Transaction.description
    ).filter(Transaction.account_id == account_id).all()

    existing_set = set()
    for r_date, r_amount, r_ref, r_desc in existing_recs:
        amt_str = f"{Decimal(str(r_amount)):.2f}"
        date_str = str(r_date)
        if r_ref:
            existing_set.add((date_str, amt_str, str(r_ref).strip()))
        if r_desc:
            existing_set.add((date_str, amt_str, str(r_desc).strip()))

    new_tx_objects = []
    balance_delta = Decimal("0.00")

    for data in transactions_data:
        t_date_str = str(data["date"])
        t_amt_str = f"{Decimal(str(data['amount'])):.2f}"
        t_ref = str(data.get("reference_number", "")).strip() if data.get("reference_number") else ""
        t_desc = str(data.get("description", "")).strip()

        # Check deduplication
        if t_ref and (t_date_str, t_amt_str, t_ref) in existing_set:
            continue
        if (t_date_str, t_amt_str, t_desc) in existing_set:
            continue

        # Add to existing set to avoid duplicates within the same statement file
        if t_ref:
            existing_set.add((t_date_str, t_amt_str, t_ref))
        existing_set.add((t_date_str, t_amt_str, t_desc))

        tx = Transaction(
            date=data["date"],
            description=data["description"],
            amount=data["amount"],
            type=data["type"],
            account_id=account_id,
            reference_number=data.get("reference_number"),
            tags=data.get("tags")
        )
        new_tx_objects.append(tx)

        # Track account balance changes
        if data["type"] == "INCOME":
            balance_delta += data["amount"]
        elif data["type"] in ["EXPENSE", "INVESTMENT", "SAVINGS", "LOAN", "TAX"]:
            balance_delta -= data["amount"]

    if new_tx_objects:
        db.add_all(new_tx_objects)
        account.current_balance += balance_delta
        db.commit()

    return len(new_tx_objects)

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
            existing.last_updated = datetime.now()
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
                last_updated=datetime.now()
            )
            db.add(new_inv)
            imported_holdings_count += 1

    db.commit()

    imported_tx_count = import_statement_transactions(db, account_id, txs)

    return {
        "imported_holdings": imported_holdings_count,
        "imported_transactions": imported_tx_count
    }
