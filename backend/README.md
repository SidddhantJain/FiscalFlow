# FiscalFlow Backend Engine

This directory contains the FastAPI-powered local-first backend for FiscalFlow—a Personal Financial Management & Analysis Platform focused on the Indian financial ecosystem.

## Stack Overview
- **Core**: Python 3.10+ & FastAPI
- **Database**: SQLite (local, offline-first) with SQLAlchemy ORM (2.0 style)
- **Validation**: Pydantic v2
- **Data Import**: Pandas and OpenPyXL for statement reading (CSV/Excel)

---

## Getting Started

### 1. Requirements & Setup
Ensure you have Python 3.10+ installed. Navigate to this directory and create a virtual environment:
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows (CMD/PowerShell)
.venv\Scripts\activate
# On Linux/macOS
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

*(Alternatively, if you use the `uv` tool, simply run `uv pip install -r requirements.txt`)*

### 2. Configure Environment
Copy the `.env.example` file to `.env`:
```bash
cp .env.example .env
```

### 3. Run the Server
While you can run the server manually:
```bash
uvicorn app.main:app --reload
```
You are encouraged to run the automation scripts from the project root (`start.py` to start and `stop.py` to stop) using your editor's **Run** button or standard python command.

Once running, you can access the interactive API docs at:
- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## Testing

Run the automated test suite with `pytest`:
```bash
pytest app/tests
```

---

## Core Components

1. **Accounts & Transactions Ledger**: Core modules allowing local tracking of bank balances, wallets, assets, and liabilities. Handles automated parent account balance updates when transactions are logged.
2. **Transfer Intelligence Engine**: Heuristics to automatically detect self-transfers, investment allocations, or credit card payments (matching dual debit/credit entries in a short date window) and merging them into a single `TRANSFER` or `SAVINGS` transaction (if transferring to a designated savings account) to avoid double counting.
3. **Statement Import System**: Ingests standard, Axis Bank, HDFC Bank, and SBI Bank CSV/Excel statements, parses row data, deduplicates transactions, and updates balances. The Axis Bank parser targets: `SRL NO`, `Tran Date`, `CHQNO`, `PARTICULARS`, `DR`, `CR`, `BAL`, and `SOL`.
4. **Reports & FY Dashboard**: Summarizes net worth, cashflow forecast, and generates Indian Financial Year (April 1 to March 31) quarterly aggregates with tax-deductible investment insights.
5. **AI Engine / Insights**: Offline-capable rule-based heuristics that auto-categorize transactions (e.g. UPI transactions as general Expense/Spending, Groww/Angel One transactions as Investments/Savings), identify leakages (like frequent food ordering or unused subscriptions), and compute a weighted 0-100 Financial Health Score.
