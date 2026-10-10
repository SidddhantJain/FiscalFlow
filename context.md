# FiscalFlow Project Context & Architecture Reference

> **Important Instruction**: Read this `context.md` file before performing any tasks or answering prompts on the FiscalFlow codebase to ensure strict adherence to established schemas, bank statement formats, master budgets, and categorization rules.

---

## 1. Project Overview & Tech Stack
**FiscalFlow** is a modern, full-stack personal wealth intelligence and budget tracking system tailored for Indian personal finance workflows.

- **Backend**: Python 3.10+ / FastAPI / SQLAlchemy / SQLite database (`backend/fiscalflow.db`).
- **Frontend**: HTML5, Vanilla JavaScript (ES6+), Modern Tailwind CSS, SVG Infographics & Charts, Material Symbols.
- **Server Orchestration**: 
  - Startup script: [`start.py`](file:///d:/Siddhant/projects/FiscalFlow/start.py) (kills zombie port 8000 processes and launches Uvicorn server).
  - Shutdown script: [`stop.py`](file:///d:/Siddhant/projects/FiscalFlow/stop.py) (safely terminates port 8000 server).
  - Standalone tracker exporter: [`generate_tracker.py`](file:///d:/Siddhant/projects/FiscalFlow/generate_tracker.py).

---

## 2. Bank Statement Specifications & Axis Bank Parsing
Bank statements are imported via `POST /transactions/import`.

### Standard Axis Bank Statement Columns:
```
SRL NO | Tran Date | CHQNO | PARTICULARS | DR | CR | BAL | SOL
```
- **Tran Date**: Formatted as `%d-%m-%Y` (e.g., `01-10-2024` or `15/10/2024`).
- **PARTICULARS**: Contains merchant details, UPI IDs, beneficiary names, transfer references.
- **DR / CR**: Debit (Expense/Outflow) and Credit (Income/Inflow) amounts.
- **BAL**: Running account balance.
- **SOL**: Branch / Service Outlet ID.

### Special Transaction Type Directives:
- Transactions made via **UPI** (e.g. `@okaxis`, `@okhdfcbank`, `UPI/`, `GPAY`, `PAYTM`, `CRED`) default to **EXPENSE** / Spending.
- Transactions to investment platforms like **Groww**, **Angel One**, **Zerodha**, **Kite**, **Coin**, **Kuvera** default to **INVESTMENT** (`Monthly SIP Investment` / `Mutual Funds` / `Stocks`).
- Transfers to designated savings accounts default to **SAVINGS** (`Emergency Fund Allocation` / `Savings Transfer`).

---

## 3. Final Master Budget (Income Sources & Allocations)

The user's monthly financial baseline is structured around a **₹31,000 Total Monthly Cash Flow**:

### Income Sources:
| Income Source | Monthly Amount (₹) | % Share | Notes & Strategy |
| :--- | :--- | :--- | :--- |
| **Internship Stipend** | ₹25,000 | 80.6% | Primary monthly earning from Sigma Soft Tech Park internship. |
| **Family Support** | ₹6,000 | 19.4% | Supplementary monthly family contribution. |
| **Total Monthly Cash Flow** | **₹31,000** | **100.0%** | Combined available monthly funds. |

### Allocations & Spending Caps:
| Category / Line Item | Monthly Amount (₹) | % of Funds | Notes & Strategy | Type |
| :--- | :--- | :--- | :--- | :--- |
| **PG Rent & Covered Meals** | ₹14,000 | 45.2% | Breakfast & dinner daily, Saturday full meals, Sunday breakfast. | `EXPENSE` |
| **Daily Office Lunch (Mon–Sat)** | ₹3,250 | 10.5% | 26 working days @ ₹100–150/day in/near Sigma Soft Tech Park. | `EXPENSE` |
| **BMTC Bus Commute** | ₹1,000 | 3.2% | Daily bus fares between Varthur Kodi and Kundalahalli Gate. | `EXPENSE` |
| **Lifestyle & Personal Essentials** | ₹3,500 | 11.3% | Sunday meals, mobile recharge, toiletries, laundry supplies. | `EXPENSE` |
| **Emergency Fund Allocation** | ₹2,750 | 8.9% | Built up monthly in liquid bank savings. | `SAVINGS` |
| **Monthly SIP Investment** | ₹5,500 | 17.7% | Capped fixed wealth-building auto-investment. | `INVESTMENT` |
| **Unallocated Flex Buffer** | ₹1,000 | 3.2% | Extra cash left untouched in your bank account. | `EXPENSE` |

### Overgrown Alert Engine:
- If spending in any category exceeds its planned monthly target (`spent > amount`), the system triggers an **"Overgrown Budget Warning"** badge with exact overspend variance (`+₹X over limit`) and strategy notes.

---

## 4. Intelligent Auto-Tagging & Categorization Engine
Transactions are automatically tagged and categorized on import or manual entry using regex heuristics in [`backend/app/services/ai_engine.py`](file:///d:/Siddhant/projects/FiscalFlow/backend/app/services/ai_engine.py):

| Tag Pattern | Keywords / Regex Match | Default Tags Added | Category Assigned |
| :--- | :--- | :--- | :--- |
| **Food & Dining** | `swiggy`, `zomato`, `restaurant`, `dhaba`, `thali`, `mess`, `canteen`, `bhojanalaya`, `pizza`, `burger`, `biryani` | `#Food`, `#Dining` | `Food` or `Daily Office Lunch (Mon–Sat)` |
| **Cafe / Coffee** | `cafe`, `coffee`, `tea`, `ccd`, `starbucks`, `chai point`, `blue tokai`, `third wave` | `#Food`, `#Cafe` | `Daily Office Lunch (Mon–Sat)` |
| **Groceries & Kirana** | `kirana`, `provision`, `supermarket`, `mart`, `blinkit`, `zepto`, `instamart`, `dmart`, `bigbasket`, `milk` | `#Groceries`, `#Kirana`, `#Lifestyle` | `Lifestyle & Personal Essentials` |
| **BMTC / Bus Commute** | `bmtc`, `bus`, `chalo`, `ksrtc`, `varthur`, `kundalahalli` | `#Travel`, `#BMTC`, `#Commute` | `BMTC Bus Commute` |
| **Metro Transit** | `metro`, `namma metro`, `bmrc`, `smart card` | `#Travel`, `#Metro`, `#Commute` | `Transport` |
| **PG & Rent** | `pg rent`, `rent`, `hostel`, `colive`, `stanza`, `zolo`, `landlord`, `room rent`, `flat` | `#Housing`, `#PG Rent` | `PG Rent & Covered Meals` |
| **Medical & Pharmacy** | `medical`, `pharmacy`, `pharma`, `apollo`, `medplus`, `1mg`, `netmeds`, `pharmeasy`, `hospital`, `clinic`, `doctor` | `#Medical`, `#Healthcare` | `Lifestyle & Personal Essentials` |
| **Lifestyle & Mobile** | `recharge`, `airtel`, `jio`, `vi`, `bsnl`, `laundry`, `salon`, `haircut`, `toiletries`, `amazon`, `flipkart`, `myntra`, `zudio` | `#Lifestyle`, `#Shopping` | `Lifestyle & Personal Essentials` |
| **SIP & Investments** | `groww`, `angelone`, `angle one`, `zerodha`, `kite`, `coin`, `kuvera`, `sip`, `mutual fund`, `uti`, `quant`, `nippon` | `#Investment`, `#SIP` | `Monthly SIP Investment` |
| **Savings Sweep** | `emergency fund`, `reserve`, `fd`, `fixed deposit`, `sweep`, `rd` | `#Savings`, `#Emergency Fund` | `Emergency Fund Allocation` |
| **Income Sources** | `stipend`, `sigma soft`, `sigma tech`, `internship`, `family`, `father`, `mother`, `papa`, `mummy`, `allowance` | `#Income`, `#Stipend` or `#Family Support` | `Internship Stipend` / `Family Support` |
| **UPI Payments** | `upi`, `gpay`, `phonepe`, `paytm`, `cred`, `qr`, `scan`, `@okaxis`, `@okhdfcbank` | `#UPI` | — |

- **Manual Tag Management**: Users can add, change, or remove tags directly on any transaction from the Ledger tab or via `PUT /transactions/{tx_id}`.

---

## 5. Core Database Schema (`backend/app/models/`)

### 1. `Transaction` (`app.models.transaction`)
- `id`: Integer (PK)
- `date`: Date
- `description`: String
- `amount`: Numeric(12, 2)
- `type`: String (`INCOME`, `EXPENSE`, `INVESTMENT`, `SAVINGS`, `TRANSFER`, `TAX`)
- `category_id`: Integer (FK -> `Category.id`, nullable)
- `account_id`: Integer (FK -> `Account.id`)
- `destination_account_id`: Integer (FK -> `Account.id`, nullable)
- `reference_number`: String (nullable)
- `is_recurring`: Boolean (default False)
- `notes`: String (nullable)
- `tags`: String (nullable, comma-separated e.g. `Food, Cafe, UPI`)

### 2. `Budget` (`app.models.budget`)
- `id`: Integer (PK)
- `user_id`: Integer (FK -> `User.id`)
- `category_id`: Integer (FK -> `Category.id`)
- `name`: String (nullable, e.g. `PG Rent & Covered Meals`)
- `amount`: Numeric(12, 2)
- `spent`: Numeric(12, 2) (dynamically re-calculated on read)
- `start_date`: Date
- `end_date`: Date
- `notes`: String (nullable, strategy and limit notes)

### 3. `StatementFile` (`app.models.statement_file`)
- `id`: Integer (PK)
- `user_id`: Integer (FK -> `User.id`)
- `filename`: Original uploaded filename (e.g. `Axis_Statement_Oct2024.csv`)
- `saved_filename`: Local persistent path in `backend/uploads/statements/`
- `file_size`: Size in bytes
- `bank_type`: Parser type (e.g. `AXIS`, `HDFC`, `SBI`, `GENERIC`)
- `transaction_count`: Number of imported transactions
- `upload_date`: Timestamp of upload

### 4. `UserTagRule` (`app.models.tag_rule`)
- `id`: Integer (PK)
- `user_id`: Integer (FK -> `User.id`)
- `pattern`: Merchant substring / normalized pattern (e.g. `swiggy`, `bmtc`, `groww`)
- `tags`: Comma-separated tags to automatically apply (e.g. `Food, Dining, Lunch`)
- `category_id`: Associated category ID (optional)
- `match_count`: How many times this rule has been matched

---

## 6. Repetitive Transaction Auto-Tagging Memory
To eliminate repetitive manual tagging:
- When a user adds/edits tags on a transaction, `learn_user_tag_rule()` creates or updates a persistent `UserTagRule`.
- Future imports and manual transaction entries query `UserTagRule` via `apply_learned_tag_rules()` and auto-apply the user's custom tags.
- The user can view, manage, and re-apply learned rules across all historical transactions with one click via `POST /statements/tag-rules/apply-all`.

---

## 7. Key API Endpoints

- `GET /transactions/?tag=Food&search=...`: Lists transactions filtered by date, type, account, and tag.
- `POST /transactions/`: Creates a transaction with automatic tag extraction and learned rule matching.
- `PUT /transactions/{tx_id}`: Updates transaction fields, tags, category, and updates learned tag memory.
- `DELETE /transactions/{tx_id}`: Reverts account balance and deletes record.
- `POST /transactions/import`: Parses and persistently stores bank statement files, extracts transactions, auto-categorizes, and applies learned tags.
- `GET /statements/`: Lists all uploaded and stored statement files.
- `GET /statements/{file_id}/download`: Downloads the exact original raw statement file uploaded by the user.
- `GET /statements/export/axis`: Downloads current transactions formatted identically to Axis Bank statements (`SRL NO`, `Tran Date`, `CHQNO`, `PARTICULARS`, `DR`, `CR`, `BAL`, `SOL`).
- `GET /statements/export/full-csv`: Downloads full transaction ledger with tags, categories, accounts, and reference numbers.
- `GET /statements/tag-rules`: Lists all learned repetitive tag rules.
- `POST /statements/tag-rules/apply-all`: Scans all past transactions and re-applies learned tag rules.
- `GET /budgets/`: Lists all user budgets with live-computed spending.
- `GET /budgets/summary`: Returns master planned income, actual spent, flex buffer, distribution percentages, and overgrown alerts.
- `POST /budgets/reset-master`: Resets and seeds the exact Master Budget (₹31,000 cash flow).
- `PUT /budgets/{budget_id}`: Modifies budget target amount, name, or strategy notes.
- `POST /budgets/`: Creates a custom budget line item.
- `DELETE /budgets/{budget_id}`: Deletes a budget line item.

---

## 8. How to Run & Verify

1. **Start Server**:
   ```bash
   python start.py
   ```
   Opens `http://127.0.0.1:8000` with live dashboard, transactions ledger, master budget tracker, statements manager, and AI insights.

2. **Stop Server**:
   ```bash
   python stop.py
   ```

3. **Run Automated Test Suite**:
   ```bash
   backend\.venv\Scripts\python.exe -m pytest backend/app/tests/ -v
   ```
