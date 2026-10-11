# FiscalFlow Canonical Context & Architecture Reference

> **CRITICAL INSTRUCTION**: This `context.md` file is the definitive, single source of truth for the FiscalFlow codebase. Read this document before performing any feature additions, bug fixes, database operations, or responding to user queries to ensure absolute consistency across schemas, banking formats, broker integrations, master budgets, and UI state.

---

## 1. Project Overview & Architectural Foundation

**FiscalFlow** is an institutional-grade, full-stack personal wealth intelligence, statement ingestion, and budget tracking application engineered specifically for Indian personal finance workflows.

- **Backend**: Python 3.10+ / FastAPI / SQLAlchemy ORM / SQLite database (`backend/fiscalflow.db`).
- **Database Path Isolation**: The SQLite connection string in [`backend/app/database.py`](file:///d:/Siddhant/projects/FiscalFlow/backend/app/database.py) uses a canonical absolute path to `backend/fiscalflow.db`. This guarantees that executing scripts or commands from the workspace root or the `backend/` folder always connects to the identical database file without creating split or stray databases.
- **Frontend**: HTML5, Vanilla JavaScript (ES6+ modular state architecture), Tailwind CSS design tokens, Glassmorphism aesthetics, dynamic SVG sparklines and circular gauge meters, Google Material Symbols.
- **Server Orchestration**:
  - **Launch Server**: `python start.py` (Kills any orphan process on port 8000, opens `http://127.0.0.1:8000` in the browser, and starts the FastAPI/Uvicorn server with hot reload).
  - **Stop Server**: `python stop.py` (Safely terminates all background processes listening on port 8000).
  - **Test Suite**: `backend\.venv\Scripts\python.exe -m pytest backend/app/tests/ -v` (18 comprehensive automated tests).

---

## 2. Bank & Demat Account Architecture

Accounts represent liquid repositories, broker holdings, and credit liabilities.

### Supported Account Types (`account_type`):
- `SAVINGS`: Liquid savings bank accounts (e.g. HDFC Bank, Axis Bank, SBI).
- `SALARY`: Designated payroll accounts.
- `DEMAT`: Stock broker and mutual fund accounts (e.g. Groww, Angel One, Zerodha Kite).
- `INVESTMENT`: Direct AMC mutual fund or wealth accounts.
- `CURRENT`: Commercial / current bank accounts.
- `CREDIT_CARD`: Revolving credit facilities.
- `WALLET` / `CASH`: Digital wallets (Paytm, PhonePe) or physical currency.

### Account Fields & Model Schema:
- `id`: Primary Key (Integer).
- `user_id`: Foreign Key (`users.id`, ondelete="CASCADE").
- `name`: Display label (e.g. `Axis Salary`, `Groww Demat`, `Angel One Portfolio`).
- `bank_name`: Institution name (e.g. `Axis Bank`, `Groww`, `Angel One`, `HDFC Bank`).
- `account_type`: Enum string representing account class.
- `account_number`: Bank account number or Demat Client ID / DP ID (e.g. `1208160012345678`).
- `opening_balance`: Initial seed capital (Numeric 12, 2).
- `current_balance`: Live running balance adjusted automatically with transactions (Numeric 12, 2).
- `currency`: ISO currency code (default: `INR`).

### Account Endpoints (`backend/app/routers/accounts.py`):
- `GET /accounts/`: Retrieves all registered accounts.
- `POST /accounts/`: Creates an account with `name`, `bank_name`, `account_type`, `account_number`, `opening_balance`, `currency`. Returns HTTP 201 Created.
- `GET /accounts/{id}`: Retrieves details for a single account.
- `PUT /accounts/{id}`: Updates account metadata or balances.
- `DELETE /accounts/{id}`: Deletes an account and cascades to associated transactions.
- `POST /accounts/clean-duplicates`: Intelligently purges redundant test accounts that share identical names and have zero balance or no recorded transactions.

---

## 3. Statement Ingestion & Raw Attachment Storage

FiscalFlow stores both the parsed transaction ledger and the exact original uploaded statement files on the local filesystem.

### Persistent File Storage:
- Stored directory: `backend/uploads/statements/`
- Every uploaded statement is cataloged in the `statement_files` database table with its original filename, server-saved filename, bank/parser type, file size, and upload timestamp.
- Download endpoint: `GET /statements/{file_id}/download` allows downloading the exact original raw uploaded statement at any time.

### Supported Statement Parsers (`backend/app/services/statement_import.py`):
1. **Axis Bank CSV Parser (`AXIS_CSV`)**:
   - Matches official Axis Bank column specification:
     ```
     SRL NO | Tran Date | CHQNO | PARTICULARS | DR | CR | BAL | SOL
     ```
   - Dates parsed in `DD-MM-YYYY` format (e.g., `01-10-2024`).
   - Debit amounts (`DR`) become `EXPENSE` (or `INVESTMENT`/`SAVINGS` if heuristics match).
   - Credit amounts (`CR`) become `INCOME`.
2. **HDFC Bank Statement Parser (`HDFC_CSV`)**: Handles standard HDFC transaction narrations and decimal balances.
3. **SBI Bank Statement Parser (`SBI_CSV`)**: Parses State Bank of India transaction histories.
4. **Groww Demat Statement Parser (`GROWW_DEMAT`)**: Ingests Groww holding and trade reports (CSV/Excel), auto-creating stock and mutual fund entries with quantity, purchase price, and current market value.
5. **Angel One Demat Parser (`ANGELONE_DEMAT`)**: Ingests Angel One holding summaries, symbol mappings, and portfolio valuations.
6. **Zerodha Kite Parser (`ZERODHA_DEMAT`)**: Ingests Zerodha tradebooks and Console holding CSVs.
7. **Generic Demat Parser (`GENERIC_DEMAT`)**: Parses open CSV statements containing symbols, units, and values.
8. **Excel Statement Parser (`DEFAULT_XLS`)**: Reads `.xls` and `.xlsx` multi-column banking sheets via `openpyxl`.

### Export Formats:
- `GET /statements/export/axis`: Dynamically generates and downloads current ledger transactions formatted identically to Axis Bank statement structure (`SRL NO`, `Tran Date`, `CHQNO`, `PARTICULARS`, `DR`, `CR`, `BAL`, `SOL`).
- `GET /statements/export/full-csv`: Full ledger export containing tags, categories, accounts, and reference IDs.

---

## 4. Final Master Budget (Income Sources & Allocations)

The user's monthly financial baseline is structured around a **₹31,000 Total Monthly Cash Flow**:

### Income Sources:
| Income Source | Monthly Amount (₹) | % Share | Notes & Strategy |
| :--- | :--- | :--- | :--- |
| **Internship Stipend** | ₹25,000 | 80.6% | Primary monthly earning from Sigma Soft Tech Park internship. |
| **Family Support** | ₹6,000 | 19.4% | Supplementary monthly family contribution. |
| **Total Monthly Cash Flow** | **₹31,000** | **100.0%** | Combined available monthly funds. |

### Allocations & Spending Targets:
| Category / Line Item | Monthly Amount (₹) | % of Funds | Notes & Strategy | Type |
| :--- | :--- | :--- | :--- | :--- |
| **PG Rent & Covered Meals** | ₹14,000 | 45.2% | Breakfast & dinner daily, Saturday full meals, Sunday breakfast. | `EXPENSE` |
| **Daily Office Lunch (Mon–Sat)** | ₹3,250 | 10.5% | 26 working days @ ₹100–150/day in/near Sigma Soft Tech Park. | `EXPENSE` |
| **BMTC Bus Commute** | ₹1,000 | 3.2% | Daily bus fares between Varthur Kodi and Kundalahalli Gate. | `EXPENSE` |
| **Lifestyle & Personal Essentials** | ₹3,500 | 11.3% | Sunday meals, mobile recharge, toiletries, laundry supplies. | `EXPENSE` |
| **Emergency Fund Allocation** | ₹2,750 | 8.9% | Built up monthly in liquid bank savings. | `SAVINGS` |
| **Monthly SIP Investment** | ₹5,500 | 17.7% | Capped fixed wealth-building auto-investment. | `INVESTMENT` |
| **Unallocated Flex Buffer** | ₹1,000 | 3.2% | Extra cash left untouched in your bank account. | `EXPENSE` |

### Overgrown Alert Engine (`GET /budgets/summary`):
- When actual spending in any category exceeds its planned monthly target (`spent > amount`), the system triggers an **"Overgrown Budget Warning"** badge displaying exact overspend variance (`+₹X over limit`).
- Reset baseline: `POST /budgets/reset-master` restores and seeds this exact budget allocation table.

---

## 5. Intelligent Heuristics & Repetitive Task Reducer

FiscalFlow incorporates a multi-tier heuristics engine in [`backend/app/services/ai_engine.py`](file:///d:/Siddhant/projects/FiscalFlow/backend/app/services/ai_engine.py):

### Rule 1: UPI Spending Directive
- Any transaction identified with UPI patterns (`@okaxis`, `@okhdfcbank`, `UPI/`, `GPAY`, `PAYTM`, `CRED`, `QR`, `SCAN`) automatically defaults to **EXPENSE** / Spending.

### Rule 2: Investment Broker Directive
- Any transaction mentioning **Groww**, **Angel One**, **Angle One**, **Zerodha**, **Kite**, **Coin**, **Kuvera**, or mutual fund AMCs automatically defaults to **INVESTMENT** (`Monthly SIP Investment` / `Mutual Funds` / `Stocks`).

### Rule 3: Savings Transfer Directive
- Transfers targeting designated savings accounts or reserve funds default to **SAVINGS** (`Emergency Fund Allocation` / `Savings Transfer`).

### Rule 4: Repetitive Tag Memory (Task Reducer)
- Whenever a user manually updates the tags or category of a transaction, the pattern is memorized in the `user_tag_rules` table.
- Future statement uploads or transaction entries matching that pattern automatically inherit the learned tags and category.
- Management endpoints: `GET /statements/tag-rules` and `POST /statements/tag-rules/apply-all`.

---

## 6. Demat Investments & Recurring SIP Engine

### Portfolio Holdings (`backend/app/routers/investments.py`):
- Models individual stocks, mutual fund units, and gold holdings.
- Fields: `name`, `symbol` (e.g. `TCS`, `INFY`, `PPFAS`), `asset_class`, `broker` (Groww, Angel One, Zerodha), `account_id` (linked Demat Account), `units`, `purchase_price`, `current_value`, `buy_date`.
- Comprehensive financial analysis endpoint (`GET /investments/analysis`): Returns total invested cost, current portfolio value, net unrealized P&L (₹ and %), CAGR benchmark (~14.8%), broker distribution, and asset allocation breakdown.

### Recurring SIP Schedules (`backend/app/routers/sips.py`):
- Models auto-debit mutual fund investments aligned with the ₹5,500/month master plan.
- Fields: `scheme_name`, `amount`, `sip_day_of_month`, `next_sip_date`, `broker`, `account_id`, `status`.
- Automatically calculates next execution date and countdown (`days_remaining`).
- Single-click payment recording (`POST /sips/{id}/execute`): Immediately logs an investment transaction in the ledger, adjusts account balances, and advances the schedule to the next month.

---

## 7. Frontend User Interface & Tab Structure

The application UI is divided into dedicated functional domains:

1. **Dashboard (`dashboard`)**: Financial command center showing live Net Worth, SVG sparkline history, Health Score circular gauge, account cards, heuristic intelligence feed, cashflow bars, and asset breakdown.
2. **Bank & Demat Accounts (`accounts`)**: Dedicated management center displaying:
   - Summary metric cards (Liquid Savings, Demat Holdings, Total Accounts, Liabilities).
   - Liquid Bank Accounts grid (Savings, Salary, Current, Cash) with full account numbers and quick actions (View Ledger, Delete).
   - Demat & Broker Accounts grid (Groww, Angel One, Zerodha) with Client IDs, portfolio values, and import shortcuts.
   - Credit Cards & debt facilities grid.
   - Clean Duplicate Accounts button (`POST /accounts/clean-duplicates`).
3. **Transaction Ledger (`transactions`)**: Searchable, filterable ledger with inline tag editing, statement import, Axis format export, full CSV export, and transfer detection.
4. **Financial Year (`financial-year`)**: Tax analytics, FY 2024-25 vs FY 2023-24 selector, Section 80C/80D summaries, and quarterly audit checklist.
5. **Master Budget (`master-budget`)**: Visual ₹31,000 cash flow distribution with real-time spending progress bars, overgrown budget alerts, and reset utility.
6. **Investments & Demat (`investments`)**: Demat portfolio manager, holdings table, SIP calendar countdown cards, P&L analytics, and Demat statement ingestion.
7. **AI Insights (`insights`)**: Real-time heuristics feed, spending anomaly detection, emergency fund tracking, and NLP conversational assistant.

### Modal Dialogs:
- `add-account-modal`: Registers bank or Demat accounts. Automatically navigates to the Accounts tab upon creation.
- `add-tx-modal`: Manual transaction logger.
- `import-modal`: Universal statement importer supporting Axis Bank, HDFC, SBI, Groww, Angel One, and Zerodha.
- `import-demat-modal`: Dedicated Demat holding and trade statement importer.
- `add-holding-modal`: Add stock or mutual fund holding.
- `add-sip-modal`: Add recurring monthly SIP schedule.
- `statements-manager-modal`: Catalog of uploaded raw statement files, original file downloads, Axis export, and repetitive tag rules memory.
- `settings-modal`: Preferences, database maintenance (clean duplicate accounts, re-evaluate AI heuristics, reset master plan), version info.
- `support-modal`: User guide for Axis Bank statement format, Demat statements, Master Budget allocations, and heuristics.

---

## 8. Development & Verification Guide

### Quick Start:
```bash
# Start backend server and launch UI
python start.py

# Terminate server
python stop.py

# Run complete test suite
backend\.venv\Scripts\python.exe -m pytest backend/app/tests/ -v
```

### Database Verification:
```bash
# Inspect registered accounts
backend\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'backend'); from app.database import SessionLocal; from app.models.account import Account; db = SessionLocal(); print([(a.id, a.name, a.bank_name, a.account_type, a.current_balance, a.account_number) for a in db.query(Account).all()]); db.close()"
```

---

## 8. Statement Ingestion & Parsing Engine (`backend/app/services/statement_import.py`)

### Supported Statement Formats:
1. **Auto-Detect Engine (`AUTO_DETECT`)**:
   - Uses regex pattern heuristics (`BANK_PATTERNS` & `DEMAT_PATTERNS`) to resolve date, description, debit, credit, amount, and reference columns across all major Indian banks (Axis, HDFC, SBI, ICICI, Kotak, PNB) and Demat brokers.
2. **Bank CSV Statements**:
   - Multi-encoding support: `utf-8-sig`, `utf-8`, `cp1252`, `latin1`, `iso-8859-1`.
   - Deep preamble scan: Scans up to 120 lines to locate genuine table headers past extended bank customer information (Name, IFSC, MICR, Address, Nominee, PAN, CKYC).
   - Quote sanitization & EOF error prevention: Automatically balances and sanitizes unclosed quotes (`line.count('"') % 2 != 0`) and employs `quoting=csv.QUOTE_NONE` fallback to permanently prevent `EOF inside string starting at row X` errors.
   - Footer & disclaimer truncation: Automatically detects and trims trailing footer blocks (`*** END OF STATEMENT ***`, `Abbreviations:`, `Legends:`, `Disclaimer:`, `Page total:`) preventing footer text from corrupting transaction rows.
   - Flexible date parsing: Supports `%d-%m-%Y`, `%d/%m/%Y`, `%d/%m/%y`, `%Y-%m-%d`, `%d %b %Y`.
   - Currency & number parsing: Strips `₹`, `$`, `Rs.`, commas, trailing `Cr`/`Dr`, and parenthesized negative amounts `(1,500.00)`.
3. **Excel Workbooks (`.xlsx`, `.xls`)**:
   - Multi-sheet scanner: Prioritizes sheets containing `Bank Statements`, `Transactions`, `Holdings`, `Orders`, etc.
   - Netbanking HTML-as-XLS: Standard library `SimpleHTMLTableParser` parses HTML tables exported by netbanking portals with `.xls` extension.
4. **Demat & Stock Statements (`GROWW_DEMAT`, `ANGELONE_DEMAT`, `ZERODHA_DEMAT`, `GENERIC_DEMAT`)**:
   - Seamlessly synchronizes stock holdings into `investments` and trade activities into `transactions`.
   - Auto-categorizes asset classes: Stocks, Mutual Funds, Index Funds, ETFs, ELSS.## 9. Statutory Indian Tax & Capital Gains Engine (`backend/app/services/tax_engine.py`)

### Legal Compliance: Finance Act 2024 / FY 2024-25 & FY 2025-26
1. **New Tax Regime (Section 115BAC - Default)**:
   - **Salaried Standard Deduction**: ₹75,000 (increased from ₹50,000 under Finance (No. 2) Act, 2024).
   - **Tax Slabs**:
     - ₹0 – ₹3,00,000: Nil (0%)
     - ₹3,00,001 – ₹7,00,000: 5%
     - ₹7,00,001 – ₹10,00,000: 10%
     - ₹10,00,001 – ₹12,00,000: 15%
     - ₹12,00,001 – ₹15,00,000: 20%
     - Above ₹15,00,000: 30%
   - **Section 87A Rebate**: Full 100% tax rebate if Net Taxable Income $\le$ ₹7,00,000 (Rebate up to ₹25,000). Total tax = ₹0 for gross salary up to ₹7,75,000.
   - **Marginal Relief**: Automatically caps tax when income slightly exceeds ₹7,00,000 so tax payable never exceeds the income above ₹7,00,000.
   - **Health & Education Cess**: 4% on net tax.

2. **Old Tax Regime**:
   - **Standard Deduction**: ₹50,000.
   - **Chapter VI-A Statutory Caps**:
     - **Section 80C**: Strictly capped at ₹1,50,000 (ELSS, PPF, EPF, LIC, tuition, home loan principal).
     - **Section 80D**: Health Insurance capped at ₹25,000.
     - **Section 80CCD(1B)**: Additional NPS deduction capped at ₹50,000.
   - **Slabs**: 0–2.5L: Nil | 2.5L–5L: 5% | 5L–10L: 20% | >10L: 30%.
   - **Section 87A Rebate**: Up to ₹12,500 for taxable income $\le$ ₹5,00,000.
   - **Health & Education Cess**: 4% on net tax.

3. **Statutory Capital Gains Tax (Finance Act 2024)**:
   - **Holding Period Threshold**: 365 days (12 months) for listed equity and mutual funds.
   - **STCG (Section 111A)**: Taxed at flat **20%** (+4% cess = 20.8%).
   - **LTCG (Section 112A)**: Taxed at flat **12.5%** (+4% cess = 13.0%) on gains exceeding the **₹1,25,000 statutory annual exemption** (increased from ₹1,00,000).

4. **Automated Deep Penetration Testing**:
   - 64 tests across 12 test suites verifying every tax slab, cliff, deduction cap, stress condition, and edge case with 100% pass rate (`pytest`).
   - Production database (`fiscalflow.db`) is strictly purged of temp/benchmark accounts; benchmark scripts run solely against isolated, temporary databases.
