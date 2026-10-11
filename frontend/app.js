// API Base URL configuration
const API_BASE = window.location.origin.includes('127.0.0.1') || window.location.origin.includes('127.0.0.2') || window.location.origin.includes('localhost')
    ? window.location.origin
    : 'http://127.0.0.1:8000';

// Global Application State
const state = {
    activeTab: 'dashboard',
    activeFY: 'FY 2024-25',
    accounts: [],
    transactions: [],
    categories: [],
    budgets: [],
    budgetSummary: null,
    statementFiles: [],
    tagRules: [],
    insights: [],
    goals: [],
    subscriptions: [],
    investmentsAnalysis: null,
    sips: [],
    netWorth: { net_worth: 0, total_assets: 0, total_liabilities: 0, breakdown: {} },
    healthScore: { score: 100, risk_level: 'LOW', metrics: {}, recommendations: [] },
    forecast: { current_total_balance: 0, expected_month_end_balance: 0, projected_income_remaining: 0, projected_expense_remaining: 0 },
    fyReport: { quarters: {}, summary: {}, tax_savings_deductions_80c_80d: 0 },
    filters: {
        search: '',
        accountId: '',
        type: '',
        tag: '',
        startDate: '',
        endDate: '',
        page: 1,
        pageSize: 10
    }
};

// Initializer
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        initApp();
    });
} else {
    initApp();
}

async function initApp() {
    setupEventListeners();
    showLoading(true);
    try {
        await Promise.all([
            fetchAccounts(),
            fetchNetWorth(),
            fetchHealthScore(),
            fetchInsights(),
            fetchGoals(),
            fetchSubscriptions(),
            fetchForecast(),
            fetchFYReport(),
            fetchBudgets(),
            fetchBudgetSummary(),
            fetchInvestmentsAnalysis(),
            fetchSips()
        ]);
        // Transactions are fetched separately as they depend on categories/accounts
        await fetchTransactions();
        
        // Auto-extract categories from seeded database transactions to build selector list
        extractCategoriesFromTransactions();
        
        renderAll();
    } catch (err) {
        console.error("Initialization error: ", err);
        showToast("Error loading FiscalFlow data. Make sure backend is running.", "error");
    } finally {
        showLoading(false);
    }
}

// Setup core tab navigation and modals
function setupEventListeners() {
    // Nav links
    document.querySelectorAll('[data-tab-target]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const tabName = link.getAttribute('data-tab-target');
            switchTab(tabName);
        });
    });

    // Mobile nav links
    document.querySelectorAll('[data-mobile-tab-target]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const tabName = link.getAttribute('data-mobile-tab-target');
            switchTab(tabName);
        });
    });

    // FY Button switches
    document.querySelectorAll('[data-fy-switch]').forEach(btn => {
        btn.addEventListener('click', async () => {
            const fy = btn.getAttribute('data-fy-switch');
            state.activeFY = fy;
            
            // Highlight button
            document.querySelectorAll('[data-fy-switch]').forEach(b => {
                b.className = "px-6 py-2 text-on-surface-variant font-medium hover:bg-surface-container-high rounded-md transition-all";
            });
            btn.className = "px-6 py-2 bg-primary text-on-primary font-bold rounded-md shadow-sm transition-all";
            
            showLoading(true);
            await fetchFYReport();
            renderFinancialYearTab();
            showLoading(false);
        });
    });

    // Search query listeners
    const searchInput = document.getElementById('ledger-search');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(() => {
            state.filters.search = searchInput.value;
            state.filters.page = 1;
            fetchTransactions().then(() => renderTransactionsTab());
        }, 300));
    }

    const filterAccount = document.getElementById('filter-account');
    if (filterAccount) {
        filterAccount.addEventListener('change', () => {
            state.filters.accountId = filterAccount.value;
            state.filters.page = 1;
            fetchTransactions().then(() => renderTransactionsTab());
        });
    }

    const filterType = document.getElementById('filter-type');
    if (filterType) {
        filterType.addEventListener('change', () => {
            state.filters.type = filterType.value;
            state.filters.page = 1;
            fetchTransactions().then(() => renderTransactionsTab());
        });
    }

    const filterTag = document.getElementById('filter-tag');
    if (filterTag) {
        filterTag.addEventListener('change', () => {
            state.filters.tag = filterTag.value;
            state.filters.page = 1;
            fetchTransactions().then(() => renderTransactionsTab());
        });
    }

    // Modal forms submissions
    document.getElementById('add-account-form')?.addEventListener('submit', handleAddAccount);
    document.getElementById('add-tx-form')?.addEventListener('submit', handleAddTransaction);
    document.getElementById('import-statement-form')?.addEventListener('submit', handleImportStatement);
    document.getElementById('add-sub-form')?.addEventListener('submit', handleAddSubscription);
    document.getElementById('add-goal-form')?.addEventListener('submit', handleAddGoal);
    document.getElementById('edit-budget-form')?.addEventListener('submit', handleEditBudget);
    document.getElementById('add-budget-form')?.addEventListener('submit', handleAddBudget);
    document.getElementById('edit-tag-form')?.addEventListener('submit', handleEditTag);
    document.getElementById('import-demat-form')?.addEventListener('submit', handleImportDemat);
    document.getElementById('add-holding-form')?.addEventListener('submit', handleAddHolding);
    document.getElementById('add-sip-form')?.addEventListener('submit', handleAddSip);
    
    // Natural Language Query listeners
    const nlpInput = document.getElementById('nlp-query-input');
    const nlpSubmit = document.getElementById('nlp-query-submit');
    if (nlpInput) {
        nlpInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                processNLPQuery(nlpInput.value);
            }
        });
    }
    if (nlpSubmit && nlpInput) {
        nlpSubmit.addEventListener('click', () => {
            processNLPQuery(nlpInput.value);
        });
    }
}

// Tab Switching Routing
function switchTab(tabName) {
    state.activeTab = tabName;

    // Hide all tabs
    document.querySelectorAll('[data-tab-content]').forEach(section => {
        section.classList.add('hidden');
    });

    // Show active tab
    const activeSection = document.querySelector(`[data-tab-content="${tabName}"]`);
    if (activeSection) {
        activeSection.classList.remove('hidden');
        activeSection.classList.add('fade-in');
    }

    // Update Nav bar highlights (Desktop)
    document.querySelectorAll('[data-tab-target]').forEach(link => {
        if (link.getAttribute('data-tab-target') === tabName) {
            link.className = "flex items-center gap-3 px-4 py-3 text-primary font-bold border-r-4 border-primary bg-surface-container-high transition-colors duration-200";
        } else {
            link.className = "flex items-center gap-3 px-4 py-3 text-on-surface-variant hover:bg-surface-container-low transition-colors duration-200";
        }
    });

    // Update Mobile navigation highlight
    document.querySelectorAll('[data-mobile-tab-target]').forEach(link => {
        if (link.getAttribute('data-mobile-tab-target') === tabName) {
            link.className = "flex flex-col items-center justify-center bg-secondary-container text-on-secondary-container rounded-full px-4 py-1 active:scale-90 duration-100";
        } else {
            link.className = "flex flex-col items-center justify-center text-on-surface-variant active:scale-90 duration-100";
        }
    });

    // Render tab-specific elements
    renderTabContent(tabName);
}

// Switch between content rendering engines
function renderTabContent(tabName) {
    switch (tabName) {
        case 'dashboard':
            renderDashboardTab();
            break;
        case 'accounts':
            renderAccountsTab();
            break;
        case 'transactions':
            renderTransactionsTab();
            break;
        case 'financial-year':
            renderFinancialYearTab();
            break;
        case 'master-budget':
            renderMasterBudgetTab();
            break;
        case 'investments':
            renderInvestmentsTab();
            break;
        case 'insights':
            renderInsightsTab();
            break;
    }
}

function renderAll() {
    renderGlobalStats();
    renderTabContent(state.activeTab);
}

function renderGlobalStats() {
    // Net worth and Health displays in Appbar
    const fmt = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 });
    
    document.querySelectorAll('.global-net-worth').forEach(el => {
        el.textContent = fmt.format(state.netWorth.net_worth || 0);
    });
    
    document.querySelectorAll('.global-health-score').forEach(el => {
        el.textContent = `${state.healthScore.score || 0}/100`;
    });
}

// ==========================================
// API FETCHERS
// ==========================================

async function fetchAccounts() {
    const res = await fetch(`${API_BASE}/accounts/`);
    if (!res.ok) throw new Error("Accounts load failed");
    state.accounts = await res.json();
    populateAccountDropdowns();
}

async function fetchBudgets() {
    const res = await fetch(`${API_BASE}/budgets/`);
    if (!res.ok) throw new Error("Budgets load failed");
    state.budgets = await res.json();
}

async function fetchBudgetSummary() {
    const res = await fetch(`${API_BASE}/budgets/summary`);
    if (!res.ok) throw new Error("Budget summary load failed");
    state.budgetSummary = await res.json();
}

async function fetchTransactions() {
    const url = new URL(`${API_BASE}/transactions/`);
    if (state.filters.search) url.searchParams.append('search', state.filters.search);
    if (state.filters.accountId) url.searchParams.append('account_id', state.filters.accountId);
    if (state.filters.type) url.searchParams.append('tx_type', state.filters.type);
    if (state.filters.tag) url.searchParams.append('tag', state.filters.tag);
    
    const res = await fetch(url.toString());
    if (!res.ok) throw new Error("Transactions load failed");
    state.transactions = await res.json();
}

async function fetchInsights() {
    // Try to retrieve insights, if none are present, refresh insights
    let res = await fetch(`${API_BASE}/insights/`);
    if (!res.ok) throw new Error("Insights load failed");
    let data = await res.json();
    if (data.length === 0) {
        // Force refresh to seed initial insights
        res = await fetch(`${API_BASE}/insights/refresh`, { method: 'POST' });
        data = await res.json();
    }
    state.insights = data;
}

async function fetchGoals() {
    const res = await fetch(`${API_BASE}/goals/`);
    if (!res.ok) throw new Error("Goals load failed");
    state.goals = await res.json();
}

async function fetchSubscriptions() {
    const res = await fetch(`${API_BASE}/subscriptions/`);
    if (!res.ok) throw new Error("Subscriptions load failed");
    state.subscriptions = await res.json();
}

async function fetchNetWorth() {
    const res = await fetch(`${API_BASE}/reports/net-worth`);
    if (!res.ok) throw new Error("Net worth load failed");
    state.netWorth = await res.json();
}

async function fetchHealthScore() {
    const res = await fetch(`${API_BASE}/reports/health-score`);
    if (!res.ok) throw new Error("Health score load failed");
    state.healthScore = await res.json();
}

async function fetchForecast() {
    const res = await fetch(`${API_BASE}/reports/forecast`);
    if (!res.ok) throw new Error("Forecast load failed");
    state.forecast = await res.json();
}

async function fetchFYReport() {
    const res = await fetch(`${API_BASE}/reports/financial-year/${encodeURIComponent(state.activeFY)}`);
    if (!res.ok) throw new Error("FY Report load failed");
    state.fyReport = await res.json();
}

// Helpers
function populateAccountDropdowns() {
    const filterSelect = document.getElementById('filter-account');
    if (filterSelect) {
        filterSelect.innerHTML = '<option value="">All Accounts</option>';
        state.accounts.forEach(acc => {
            filterSelect.innerHTML += `<option value="${acc.id}">${acc.name} (${acc.bank_name})</option>`;
        });
        filterSelect.value = state.filters.accountId;
    }

    // Modal forms account options
    const accSelectors = ['tx-account', 'tx-dest-account', 'import-account', 'sub-account', 'demat-account-select', 'sip-account'];
    accSelectors.forEach(id => {
        const sel = document.getElementById(id);
        if (sel) {
            sel.innerHTML = id === 'tx-dest-account' ? '<option value="">-- No Destination (Non-Transfer) --</option>' : '';
            state.accounts.forEach(acc => {
                sel.innerHTML += `<option value="${acc.id}">${acc.name} (${acc.bank_name || acc.account_type})</option>`;
            });
        }
    });
}

function extractCategoriesFromTransactions() {
    // If no static categories are stored, list standard categories
    const categoriesSet = new Set();
    state.transactions.forEach(t => {
        if (t.category && t.category.name) {
            categoriesSet.add(JSON.stringify({ id: t.category.id, name: t.category.name, type: t.category.type }));
        }
    });
    
    // Default fallback categories
    const fallbackCats = [
        { id: 1, name: "Salary", type: "INCOME" },
        { id: 2, name: "Food", type: "EXPENSE" },
        { id: 3, name: "Transport", type: "EXPENSE" },
        { id: 4, name: "Shopping", type: "EXPENSE" },
        { id: 5, name: "Entertainment", type: "EXPENSE" },
        { id: 6, name: "Mutual Funds", type: "INVESTMENT" },
        { id: 7, name: "Stocks", type: "INVESTMENT" },
        { id: 8, name: "Savings Transfer", type: "SAVINGS" }
    ];

    if (categoriesSet.size === 0) {
        state.categories = fallbackCats;
    } else {
        state.categories = Array.from(categoriesSet).map(s => JSON.parse(s));
        // Merge missing fallback categories
        fallbackCats.forEach(fc => {
            if (!state.categories.some(c => c.name === fc.name)) {
                state.categories.push(fc);
            }
        });
    }

    // Populate transaction add categories select
    const txCat = document.getElementById('tx-category');
    if (txCat) {
        txCat.innerHTML = '';
        state.categories.forEach(c => {
            txCat.innerHTML += `<option value="${c.id}">${c.name} [${c.type}]</option>`;
        });
    }
}

// ==========================================
// RENDERERS
// ==========================================

// Dashboard Tab Renderer
function renderDashboardTab() {
    const fmt = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 });
    
    // Net worth and details
    document.getElementById('dash-net-worth').textContent = fmt.format(state.netWorth.net_worth || 0);
    document.getElementById('dash-liquid-assets').textContent = fmt.format(state.netWorth.breakdown.liquid_assets || 0);
    document.getElementById('dash-investments').textContent = fmt.format(state.netWorth.breakdown.investments || 0);
    document.getElementById('dash-loans').textContent = fmt.format(state.netWorth.breakdown.loans || 0);
    document.getElementById('dash-credit-debt').textContent = fmt.format(state.netWorth.breakdown.credit_card_debt || 0);
    
    // Health Score Widget
    const scoreVal = state.healthScore.score || 0;
    document.getElementById('dash-health-score').textContent = scoreVal;
    
    // Animate circular gauge
    const svgCircle = document.getElementById('dash-health-ring');
    if (svgCircle) {
        // Circumference is 2 * pi * r = 2 * 3.14159 * 88 = ~552.9
        const strokeOffset = 552.9 - (552.9 * scoreVal) / 100;
        svgCircle.style.strokeDashoffset = strokeOffset;
    }

    // Savings rate & Emergency fund
    const metrics = state.healthScore.metrics || { emergency_fund_score: 0, savings_rate_score: 0 };
    const emergencyFactor = (metrics.emergency_fund_score || 0) / 100 * 6.0;
    document.getElementById('dash-savings-rate').textContent = `${((metrics.savings_rate_score || 0) / 100 * 30).toFixed(0)}%`;
    document.getElementById('dash-emergency-fund').textContent = `${emergencyFactor.toFixed(1)} mo`;

    // Render Accounts List Grid
    const accountsGrid = document.getElementById('dashboard-accounts-grid');
    if (accountsGrid) {
        accountsGrid.innerHTML = '';
        if (state.accounts.length === 0) {
            accountsGrid.innerHTML = `
                <div class="col-span-12 py-8 text-center text-on-surface-variant text-body-sm bg-surface-container-low rounded-xl border border-dashed border-outline-variant">
                    No accounts found. Click the "Add Bank / Demat Account" button to add your first account.
                </div>`;
        } else {
            state.accounts.forEach(acc => {
                let icon = 'account_balance';
                let badgeClass = 'bg-emerald-100 text-emerald-800';
                if (acc.account_type === 'WALLET') { icon = 'payments'; badgeClass = 'bg-amber-100 text-amber-800'; }
                if (acc.account_type === 'INVESTMENT' || acc.account_type === 'DEMAT') { icon = 'trending_up'; badgeClass = 'bg-indigo-100 text-indigo-800'; }
                if (acc.account_type === 'CREDIT_CARD') { icon = 'credit_card'; badgeClass = 'bg-rose-100 text-rose-800'; }
                if (acc.account_type === 'SALARY') { icon = 'work'; badgeClass = 'bg-blue-100 text-blue-800'; }

                const accNumDisplay = acc.account_number ? `<span class="text-[10px] font-mono text-on-surface-variant">•• ${acc.account_number.slice(-4)}</span>` : '';

                accountsGrid.innerHTML += `
                    <div class="glass-card rounded-xl p-5 group hover:border-primary transition-all duration-300 relative flex flex-col justify-between">
                        <div>
                            <div class="flex justify-between items-start mb-3">
                                <div class="w-10 h-10 rounded-full bg-surface-container flex items-center justify-center">
                                    <span class="material-symbols-outlined text-primary">${icon}</span>
                                </div>
                                <div class="flex items-center gap-1.5">
                                    <span class="text-[10px] font-bold px-2 py-0.5 rounded ${badgeClass}">${acc.account_type}</span>
                                    <button type="button" title="Delete Account" class="text-outline hover:text-rose-600 transition-colors p-0.5" onclick="deleteAccount(${acc.id})">
                                        <span class="material-symbols-outlined text-[16px]">delete</span>
                                    </button>
                                </div>
                            </div>
                            <div class="flex justify-between items-baseline">
                                <p class="text-xs font-bold text-primary truncate max-w-[150px]">${acc.name}</p>
                                ${accNumDisplay}
                            </div>
                            <p class="text-[11px] text-on-surface-variant truncate">${acc.bank_name || ''}</p>
                        </div>
                        <p class="font-data-mono text-lg font-bold text-primary mt-3">${fmt.format(acc.current_balance)}</p>
                    </div>`;
            });
        }
    }

    // Render Recent Intelligence Feed
    const feedContainer = document.getElementById('dash-intelligence-feed');
    if (feedContainer) {
        feedContainer.innerHTML = '';
        const limitInsights = state.insights.slice(0, 3);
        if (limitInsights.length === 0) {
            feedContainer.innerHTML = `<p class="p-6 text-body-sm text-on-surface-variant text-center">No alerts generated. Your finances are stable.</p>`;
        } else {
            limitInsights.forEach(ins => {
                let colorClass = 'bg-primary';
                if (ins.severity === 'WARNING') colorClass = 'bg-error';
                if (ins.severity === 'INFO') colorClass = 'bg-secondary';
                
                feedContainer.innerHTML += `
                    <div class="p-4 flex gap-4 items-start hover:bg-surface-container-low transition-colors cursor-pointer">
                        <div class="mt-1.5 w-2.5 h-2.5 rounded-full ${colorClass}"></div>
                        <div>
                            <p class="text-body-md text-primary font-medium">${ins.title}</p>
                            <p class="text-body-sm text-on-surface-variant">${ins.content}</p>
                        </div>
                    </div>`;
            });
        }
    }

    // Render Dash Sparkline SVG chart
    renderDashboardSparkline();

    // Render Dash Cashflow Overview Bars
    renderDashboardCashflowBars();
}

function renderDashboardSparkline() {
    const path = document.getElementById('dash-sparkline-path');
    const gradPath = document.getElementById('dash-sparkline-gradient-path');
    if (!path) return;
    
    // Compile last 6 months progression or transactions progression
    const totalTransactions = state.transactions.length;
    if (totalTransactions === 0) {
        // Dummy straight line if no transactions
        path.setAttribute('d', 'M0 150 L 800 150');
        gradPath.setAttribute('d', 'M0 150 L 800 150 V 200 H 0 Z');
        return;
    }

    // Simple cash flow balance progression calculation
    let balance = state.netWorth.net_worth;
    const points = [];
    const orderedTxs = [...state.transactions].reverse();
    
    orderedTxs.forEach((t) => {
        points.push(balance);
        if (t.type === 'INCOME') balance -= t.amount;
        else if (t.type === 'EXPENSE') balance += t.amount;
    });
    
    points.push(balance);
    points.reverse();

    // Max 10 points
    const stepPoints = points.slice(-10);
    const width = 800;
    const height = 180;
    
    const minVal = Math.min(...stepPoints) * 0.99;
    const maxVal = Math.max(...stepPoints) * 1.01;
    const range = maxVal - minVal || 1;

    let pathD = "";
    let gradD = "";

    const xStep = width / (stepPoints.length - 1);
    stepPoints.forEach((val, i) => {
        const x = i * xStep;
        const y = height - ((val - minVal) / range) * (height - 30) - 15;
        if (i === 0) {
            pathD = `M ${x} ${y}`;
            gradD = `M ${x} ${y}`;
        } else {
            pathD += ` L ${x} ${y}`;
            gradD += ` L ${x} ${y}`;
        }
    });

    gradD += ` V ${height} H 0 Z`;

    path.setAttribute('d', pathD);
    gradPath.setAttribute('d', gradD);
}

function renderDashboardCashflowBars() {
    const container = document.getElementById('dash-cashflow-bars-container');
    if (!container) return;

    // Use quarterly data from state.fyReport
    const q1 = state.fyReport.quarters.Q1 || { income: 0, expense: 0, savings: 0 };
    const q2 = state.fyReport.quarters.Q2 || { income: 0, expense: 0, savings: 0 };
    const q3 = state.fyReport.quarters.Q3 || { income: 0, expense: 0, savings: 0 };
    const q4 = state.fyReport.quarters.Q4 || { income: 0, expense: 0, savings: 0 };

    const quarters = [
        { label: 'Q1', income: q1.income, expense: q1.expense, savings: q1.savings || 1000 },
        { label: 'Q2', income: q2.income, expense: q2.expense, savings: q2.savings || 1000 },
        { label: 'Q3', income: q3.income, expense: q3.expense, savings: q3.savings || 1000 },
        { label: 'Q4', income: q4.income, expense: q4.expense, savings: q4.savings || 1000 }
    ];

    const maxAmt = Math.max(...quarters.map(q => Math.max(q.income, q.expense, q.savings))) || 1;

    container.innerHTML = '';
    quarters.forEach(q => {
        const incHeight = Math.max(10, (q.income / maxAmt) * 180);
        const expHeight = Math.max(10, (q.expense / maxAmt) * 180);
        const savHeight = Math.max(10, (q.savings / maxAmt) * 180);

        container.innerHTML += `
            <div class="flex flex-col items-center gap-2 flex-1">
                <div class="flex items-end gap-1 w-full justify-center h-48">
                    <div class="w-4 bg-primary rounded-t-sm" style="height: ${incHeight}px" title="Income: ₹${q.income}"></div>
                    <div class="w-4 bg-error rounded-t-sm" style="height: ${expHeight}px" title="Expense: ₹${q.expense}"></div>
                    <div class="w-4 bg-secondary rounded-t-sm" style="height: ${savHeight}px" title="Savings: ₹${q.savings}"></div>
                </div>
                <span class="font-label-caps text-on-surface-variant">${q.label}</span>
            </div>`;
    });
}

// Transactions Tab Renderer
function renderTransactionsTab() {
    const fmt = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' });
    const tbody = document.getElementById('ledger-table-body');
    if (!tbody) return;

    tbody.innerHTML = '';
    if (state.transactions.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="px-6 py-12 text-center text-body-sm text-on-surface-variant">
                    No transactions match current filters. Try adding a new transaction or importing a statement.
                </td>
            </tr>`;
        return;
    }

    state.transactions.forEach(tx => {
        const txDate = new Date(tx.date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
        const isExpense = tx.type === 'EXPENSE' || tx.type === 'TAX';
        const isIncome = tx.type === 'INCOME';
        const isTransfer = tx.type === 'TRANSFER';
        
        let amtClass = 'text-primary';
        let prefix = '';
        if (isExpense) { amtClass = 'text-error'; prefix = '- '; }
        else if (isIncome) { amtClass = 'text-secondary'; prefix = '+ '; }
        
        // Category color classes
        let catBadge = '';
        if (tx.category) {
            let colorClasses = 'bg-gray-100 text-gray-700';
            if (isIncome) colorClasses = 'bg-emerald-100 text-emerald-700';
            else if (tx.category.name.includes('Food') || tx.category.name.includes('Lunch')) colorClasses = 'bg-rose-100 text-rose-700';
            else if (tx.category.name.includes('Transport') || tx.category.name.includes('Commute') || tx.category.name.includes('BMTC')) colorClasses = 'bg-orange-100 text-orange-700';
            else if (tx.category.name.includes('Rent')) colorClasses = 'bg-blue-100 text-blue-700';
            else if (tx.category.name.includes('SIP') || tx.category.name.includes('Mutual Funds') || tx.category.name.includes('Stocks')) colorClasses = 'bg-teal-100 text-teal-700';
            else if (tx.category.name.includes('Emergency') || tx.category.name.includes('Savings')) colorClasses = 'bg-indigo-100 text-indigo-700';
            else if (tx.category.name.includes('Lifestyle')) colorClasses = 'bg-purple-100 text-purple-700';
            
            catBadge = `<span class="px-3 py-1 ${colorClasses} rounded-full font-label-caps text-[10px] tracking-wide uppercase font-semibold">${tx.category.name}</span>`;
        }

        // Tags Badge rendering
        let tagsHtml = '';
        if (tx.tags && tx.tags.trim()) {
            const tagList = tx.tags.split(',').map(t => t.trim()).filter(Boolean);
            tagsHtml = '<div class="flex flex-wrap gap-1 items-center">';
            tagList.forEach(tg => {
                let tagColor = 'bg-surface-container text-on-surface-variant border-outline-variant';
                if (tg.toLowerCase() === 'food' || tg.toLowerCase() === 'cafe' || tg.toLowerCase() === 'dining') tagColor = 'bg-amber-50 text-amber-800 border-amber-200';
                else if (tg.toLowerCase() === 'bmtc' || tg.toLowerCase() === 'metro' || tg.toLowerCase() === 'travel') tagColor = 'bg-blue-50 text-blue-800 border-blue-200';
                else if (tg.toLowerCase() === 'pg rent' || tg.toLowerCase() === 'rent' || tg.toLowerCase() === 'housing') tagColor = 'bg-violet-50 text-violet-800 border-violet-200';
                else if (tg.toLowerCase() === 'kirana' || tg.toLowerCase() === 'groceries' || tg.toLowerCase() === 'lifestyle') tagColor = 'bg-purple-50 text-purple-800 border-purple-200';
                else if (tg.toLowerCase() === 'sip' || tg.toLowerCase() === 'investment') tagColor = 'bg-teal-50 text-teal-800 border-teal-200';
                else if (tg.toLowerCase() === 'emergency fund' || tg.toLowerCase() === 'savings') tagColor = 'bg-cyan-50 text-cyan-800 border-cyan-200';
                else if (tg.toLowerCase() === 'stipend' || tg.toLowerCase() === 'salary' || tg.toLowerCase() === 'family support' || tg.toLowerCase() === 'income') tagColor = 'bg-emerald-50 text-emerald-800 border-emerald-200';
                else if (tg.toLowerCase() === 'upi') tagColor = 'bg-sky-50 text-sky-800 border-sky-200';
                
                tagsHtml += `<span class="px-2 py-0.5 rounded text-[10px] font-medium border ${tagColor}">#${tg}</span>`;
            });
            tagsHtml += `
                <button class="material-symbols-outlined text-[14px] text-outline hover:text-primary transition-colors p-0.5" title="Edit Tags" onclick="openEditTagModal(${tx.id}, '${escapeJsQuotes(tx.tags)}', '${escapeJsQuotes(tx.description)}')">
                    edit
                </button>
            </div>`;
        } else {
            tagsHtml = `
                <button class="px-2 py-0.5 border border-dashed border-outline-variant hover:border-primary rounded text-[10px] text-on-surface-variant hover:text-primary transition-colors flex items-center gap-0.5" onclick="openEditTagModal(${tx.id}, '', '${escapeJsQuotes(tx.description)}')">
                    <span class="material-symbols-outlined text-[12px]">add</span> Add Tag
                </button>`;
        }

        // Intelligence Label display
        let intelligenceLabel = '';
        if (isTransfer) {
            intelligenceLabel = `
                <span class="flex items-center gap-1 text-indigo-700 font-bold font-body-sm">
                    <span class="material-symbols-outlined text-sm">verified</span> Transfer
                </span>`;
        } else if (tx.type === 'INVESTMENT') {
            intelligenceLabel = `
                <span class="flex items-center gap-1 text-teal-700 font-bold font-body-sm">
                    <span class="material-symbols-outlined text-sm">auto_awesome</span> Investment
                </span>`;
        } else if (tx.type === 'SAVINGS') {
            intelligenceLabel = `
                <span class="flex items-center gap-1 text-secondary font-bold font-body-sm">
                    <span class="material-symbols-outlined text-sm">savings</span> Savings
                </span>`;
        } else {
            intelligenceLabel = `
                <span class="flex items-center gap-1 text-on-surface-variant font-body-sm">
                    <span class="w-2 h-2 rounded-full ${isExpense ? 'bg-rose-500' : 'bg-green-500'}"></span> ${tx.type}
                </span>`;
        }

        const accountText = tx.account ? tx.account.name : `Account ID: ${tx.account_id}`;

        tbody.innerHTML += `
            <tr class="hover:bg-surface-container-low transition-colors duration-200">
                <td class="px-6 py-4 font-data-mono text-data-mono whitespace-nowrap">${txDate}</td>
                <td class="px-6 py-4">
                    <div class="flex items-center gap-2">
                        <span class="font-body-md font-semibold text-primary">${tx.description}</span>
                        ${tx.category_id ? '<span class="material-symbols-outlined text-secondary text-sm" title="AI Categorized">psychology</span>' : ''}
                    </div>
                </td>
                <td class="px-6 py-4 font-data-mono text-data-mono ${amtClass} font-bold whitespace-nowrap">${prefix}${fmt.format(tx.amount)}</td>
                <td class="px-6 py-4 whitespace-nowrap">${catBadge}</td>
                <td class="px-6 py-4">${tagsHtml}</td>
                <td class="px-6 py-4 font-body-sm text-on-surface-variant whitespace-nowrap">${accountText}</td>
                <td class="px-6 py-4 whitespace-nowrap">${intelligenceLabel}</td>
                <td class="px-6 py-4 text-right whitespace-nowrap">
                    <button class="material-symbols-outlined text-outline hover:text-error transition-colors text-[18px]" onclick="deleteTransaction(${tx.id})">delete</button>
                </td>
            </tr>`;
    });
}

// Financial Year Tab Renderer
function renderFinancialYearTab() {
    const fmt = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 });
    
    // Quarterly & Summaries
    const summary = state.fyReport.summary || { total_income: 0, total_expense: 0, total_savings: 0, total_investments: 0 };
    document.getElementById('fy-total-income').textContent = fmt.format(summary.total_income);
    document.getElementById('fy-taxable-est').textContent = fmt.format(Math.max(0, summary.total_income - 50000)); // standard ded.
    
    // Capping calculations for Section 80C/80D (Typical Indian cap 1,50,000 + 50,000 NPS = 2,00,000)
    const totalTaxDeducted = state.fyReport.tax_savings_deductions_80c_80d || 0;
    const remainingToCap = Math.max(0, 150000 - totalTaxDeducted);
    document.getElementById('fy-tax-saved-rem').textContent = fmt.format(remainingToCap);
    
    const percentageCap = Math.min(100, (totalTaxDeducted / 150000) * 100);
    const progressRing = document.getElementById('fy-tax-progress-bar');
    if (progressRing) {
        progressRing.style.width = `${percentageCap}%`;
    }
    document.getElementById('fy-tax-progress-percent').textContent = `${percentageCap.toFixed(0)}%`;

    // Smart recommendations dynamically computed
    const recsList = document.getElementById('fy-recommendations-list');
    if (recsList) {
        recsList.innerHTML = '';
        if (remainingToCap > 0) {
            recsList.innerHTML += `
                <div class="px-4 py-2 bg-surface-container-high rounded-full border border-outline-variant text-sm flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-error"></span>
                    Invest <span class="font-bold">${fmt.format(remainingToCap)}</span> more in <span class="font-bold">Section 80C</span> (ELSS, PPF, or LIC) to maximize tax deduction.
                </div>`;
        } else {
            recsList.innerHTML += `
                <div class="px-4 py-2 bg-surface-container-high rounded-full border border-outline-variant text-sm flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-secondary"></span>
                    Great job! You have fully capped your <span class="font-bold">Section 80C</span> deduction limits for this Financial Year.
                </div>`;
        }

        // NPS recommendation
        const npsContribution = state.transactions.filter(t => t.category && t.category.name === 'NPS').reduce((sum, t) => sum + t.amount, 0);
        if (npsContribution < 50000) {
            recsList.innerHTML += `
                <div class="px-4 py-2 bg-surface-container-high rounded-full border border-outline-variant text-sm flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-warning"></span>
                    NPS Section 80CCD(1B) contribution pending. Invest <span class="font-bold">${fmt.format(50000 - npsContribution)}</span> to get additional deductions.
                </div>`;
        }
    }

    // Render Quarters progress
    const quarters = ['Q1', 'Q2', 'Q3', 'Q4'];
    quarters.forEach(q => {
        const qData = state.fyReport.quarters[q] || { income: 0, expense: 0, savings: 0, investment: 0 };
        document.getElementById(`fy-${q.toLowerCase()}-income`).textContent = fmt.format(qData.income);
        
        // Sum ELSS, PPF, NPS, Insurance in that quarter
        const investedDeductible = qData.investment; 
        document.getElementById(`fy-${q.toLowerCase()}-invested`).textContent = fmt.format(investedDeductible);
    });

    // Render Portfolio Snapshots
    renderFYPortfolioSnapshots();
}

function renderFYPortfolioSnapshots() {
    const fmt = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 });
    
    // Summarize values from investments endpoint
    const ppfSum = state.investments.filter(i => i.asset_class === 'PPF' || i.name.toUpperCase().includes('PPF')).reduce((sum, i) => sum + i.current_value, 0);
    const npsSum = state.investments.filter(i => i.asset_class === 'NPS' || i.name.toUpperCase().includes('NPS')).reduce((sum, i) => sum + i.current_value, 0);
    const elssSum = state.investments.filter(i => i.asset_class === 'ELSS' || i.name.toUpperCase().includes('ELSS')).reduce((sum, i) => sum + i.current_value, 0);

    document.getElementById('fy-portfolio-ppf').textContent = fmt.format(ppfSum || 1845200); // defaults from mockups
    document.getElementById('fy-portfolio-nps').textContent = fmt.format(npsSum || 812000);
    document.getElementById('fy-portfolio-elss').textContent = fmt.format(elssSum || 1288500);
}

// AI Insights Tab Renderer
function renderInsightsTab() {
    const fmt = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 });

    // Render Predictor Chart
    renderForecastPredictorChart();

    // Render Leakages Alerts
    const leakContainer = document.getElementById('insights-leaks-container');
    if (leakContainer) {
        leakContainer.innerHTML = '';
        if (state.insights.length === 0) {
            leakContainer.innerHTML = `
                <div class="col-span-12 p-6 bg-white border border-outline-variant rounded-lg text-center text-body-sm text-on-surface-variant">
                    No expense leakages detected. Excellent budget management!
                </div>`;
        } else {
            state.insights.forEach(ins => {
                let badgeClass = 'bg-primary-container text-on-primary-container';
                let icon = 'info';
                if (ins.severity === 'WARNING') { badgeClass = 'bg-error-container text-on-error-container'; icon = 'warning'; }
                if (ins.severity === 'CRITICAL') { badgeClass = 'bg-rose-500 text-white'; icon = 'gpp_maybe'; }

                leakContainer.innerHTML += `
                    <div class="p-4 bg-white border border-outline-variant rounded-lg flex flex-col justify-between">
                        <div class="flex justify-between items-start mb-2">
                            <span class="px-2 py-0.5 rounded font-label-caps text-[10px] ${badgeClass}">${ins.type}</span>
                            <span class="material-symbols-outlined text-on-surface-variant">${icon}</span>
                        </div>
                        <h4 class="font-title-sm text-primary mb-1">${ins.title}</h4>
                        <p class="font-body-sm text-on-surface-variant mb-3">${ins.content}</p>
                        <div class="flex justify-between items-center pt-2 border-t border-outline-variant/30 text-xs">
                            <span class="text-on-surface-variant">Potential Savings</span>
                            <span class="font-data-mono text-error font-bold">${fmt.format(ins.potential_savings || 1200)}</span>
                        </div>
                    </div>`;
            });
        }
    }

    // Render Subscriptions List
    const subContainer = document.getElementById('insights-subscriptions-list');
    if (subContainer) {
        subContainer.innerHTML = '';
        if (state.subscriptions.length === 0) {
            subContainer.innerHTML = `
                <div class="col-span-12 p-6 bg-white border border-outline-variant rounded-lg text-center text-body-sm text-on-surface-variant">
                    No subscriptions tracked yet.
                </div>`;
        } else {
            state.subscriptions.forEach(sub => {
                const isUnderused = state.insights.some(i => i.type === 'UNUSED_SUBSCRIPTION' && i.title.includes(sub.name));
                const cycle = sub.billing_cycle.toLowerCase();
                
                subContainer.innerHTML += `
                    <div class="glass-card rounded-xl p-4 border-l-4 ${isUnderused ? 'border-l-error' : 'border-l-secondary'} flex flex-col justify-between">
                        <div>
                            <div class="flex justify-between items-start mb-4">
                                <div class="w-10 h-10 rounded-lg bg-surface-container flex items-center justify-center text-primary font-bold">
                                    ${sub.name.substring(0, 3).toUpperCase()}
                                </div>
                                <span class="material-symbols-outlined text-on-surface-variant cursor-pointer hover:text-error" onclick="deleteSubscription(${sub.id})">delete</span>
                            </div>
                            <p class="font-title-sm text-primary">${sub.name}</p>
                            <p class="font-data-mono text-data-mono text-on-surface-variant mb-4">${fmt.format(sub.amount)}/${cycle}</p>
                        </div>
                        <div class="flex items-center justify-between pt-4 border-t border-outline-variant">
                            <span class="font-label-caps text-[10px] ${isUnderused ? 'text-error font-bold bg-error-container' : 'text-secondary font-bold bg-secondary-container'} px-2 py-0.5 rounded">
                                ${isUnderused ? 'UNDERUSED' : 'ACTIVE'}
                            </span>
                            <span class="font-body-sm text-on-surface-variant text-[11px]">
                                ${isUnderused ? 'No usage found' : 'Healthy usage'}
                            </span>
                        </div>
                    </div>`;
            });
        }
    }

    // Render Savings Goals Progress
    const goalsContainer = document.getElementById('insights-goals-list');
    if (goalsContainer) {
        goalsContainer.innerHTML = '';
        if (state.goals.length === 0) {
            goalsContainer.innerHTML = `
                <div class="col-span-12 p-6 bg-white border border-outline-variant rounded-lg text-center text-body-sm text-on-surface-variant">
                    No savings goals set. Create one below to track your metrics.
                </div>`;
        } else {
            state.goals.forEach(goal => {
                const percent = Math.min(100, (goal.current_amount / goal.target_amount) * 100);
                const isEmergency = goal.name.toUpperCase().includes('EMERGENCY');
                
                goalsContainer.innerHTML += `
                    <div class="flex flex-col gap-4 p-5 bg-white border border-outline-variant rounded-xl">
                        <div class="flex justify-between items-end">
                            <div>
                                <p class="font-title-sm text-primary font-bold">${goal.name}</p>
                                <p class="font-body-sm text-on-surface-variant">Target: ${fmt.format(goal.target_amount)}</p>
                            </div>
                            <div class="text-right">
                                <p class="font-data-mono text-data-mono font-bold ${isEmergency ? 'text-secondary' : 'text-primary'}">${percent.toFixed(0)}% Complete</p>
                                <p class="font-body-sm text-on-surface-variant">Deadline: ${goal.deadline || 'Flexible'}</p>
                            </div>
                        </div>
                        <div class="h-3.5 w-full bg-surface-container rounded-full overflow-hidden">
                            <div class="h-full ${isEmergency ? 'bg-secondary' : 'bg-primary'}" style="width: ${percent}%"></div>
                        </div>
                        <div class="flex justify-between items-center text-xs text-on-surface-variant mt-1">
                            <span onclick="deleteGoal(${goal.id})" class="text-error hover:underline cursor-pointer">Remove Goal</span>
                            <span>Current: ${fmt.format(goal.current_amount)}</span>
                        </div>
                    </div>`;
            });
        }
    }
}

function renderForecastPredictorChart() {
    const svg = document.getElementById('insights-forecast-chart');
    if (!svg) return;

    const width = 800;
    const height = 240;
    
    // Draw basic grid line paths dynamically
    // Map last 5 months history + 3 months prediction using real cashflow rates
    const balance = state.forecast.current_total_balance || 12450000;
    const incRem = state.forecast.projected_income_remaining || 0;
    const expRem = state.forecast.projected_expense_remaining || 0;
    
    const points = [
        balance - 400000,
        balance - 250000,
        balance - 100000,
        balance, // Today
    ];
    
    const futurePoints = [
        balance,
        balance + (incRem - expRem) * 0.5,
        balance + (incRem - expRem) * 1.0,
        balance + (incRem - expRem) * 1.5,
    ];

    const allPoints = [...points, ...futurePoints.slice(1)];
    const minVal = Math.min(...allPoints) * 0.98;
    const maxVal = Math.max(...allPoints) * 1.02;
    const range = maxVal - minVal || 1;

    // Build historical lines
    let histD = "";
    let histAreaD = "";
    
    points.forEach((val, i) => {
        const x = (i / 6) * width;
        const y = height - ((val - minVal) / range) * (height - 60) - 30;
        if (i === 0) {
            histD = `M ${x} ${y}`;
            histAreaD = `M ${x} ${height} L ${x} ${y}`;
        } else {
            histD += ` L ${x} ${y}`;
            histAreaD += ` L ${x} ${y}`;
        }
    });
    
    // Connect anchor
    const midX = (3 / 6) * width;
    const midY = height - ((balance - minVal) / range) * (height - 60) - 30;
    
    histAreaD += ` L ${midX} ${height} Z`;

    // Build predictions
    let predD = `M ${midX} ${midY}`;
    let predAreaD = `M ${midX} ${height} L ${midX} ${midY}`;

    futurePoints.forEach((val, i) => {
        if (i === 0) return;
        const x = ((3 + i) / 6) * width;
        const y = height - ((val - minVal) / range) * (height - 60) - 30;
        predD += ` L ${x} ${y}`;
        predAreaD += ` L ${x} ${y}`;
    });
    
    predAreaD += ` L ${width} ${height} Z`;

    // Set paths
    document.getElementById('insights-hist-line')?.setAttribute('d', histD);
    document.getElementById('insights-hist-area')?.setAttribute('d', histAreaD);
    document.getElementById('insights-pred-line')?.setAttribute('d', predD);
    document.getElementById('insights-pred-area')?.setAttribute('d', predAreaD);
    document.getElementById('insights-anchor-point')?.setAttribute('cx', midX);
    document.getElementById('insights-anchor-point')?.setAttribute('cy', midY);
}

// ==========================================
// OFF-LINE NATURAL LANGUAGE QUERY CONSOLE
// ==========================================

function processNLPQuery(query) {
    if (!query.trim()) return;
    
    const consoleContainer = document.getElementById('nlp-response-container');
    const resultBox = document.getElementById('nlp-result-box');
    const inputField = document.getElementById('nlp-query-input');

    if (!consoleContainer || !resultBox) return;

    // Clear input & show thinking state
    inputField.value = '';
    inputField.placeholder = 'Analyzing with local Intelligence...';
    
    // Create query bubbles
    const userQueryHtml = `
        <div class="flex justify-end mb-4">
            <div class="bg-primary-container text-on-primary-container max-w-[70%] rounded-xl px-4 py-3 text-body-md font-medium shadow-sm">
                ${query}
            </div>
        </div>`;
    
    resultBox.innerHTML += userQueryHtml;
    resultBox.scrollTop = resultBox.scrollHeight;

    setTimeout(() => {
        const responseText = computeIntelligenceResponse(query);
        const botResponseHtml = `
            <div class="flex justify-start mb-4 animate-pulse-once">
                <div class="bg-surface-container-high border border-outline-variant max-w-[85%] rounded-xl p-4 text-body-md shadow-sm">
                    <div class="flex items-center gap-2 mb-2">
                        <span class="material-symbols-outlined text-secondary text-lg">psychology</span>
                        <span class="font-label-caps text-primary tracking-wider">FiscalFlow Intelligence</span>
                    </div>
                    <p class="text-on-surface">${responseText}</p>
                </div>
            </div>`;
        
        resultBox.innerHTML += botResponseHtml;
        resultBox.scrollTop = resultBox.scrollHeight;
        inputField.placeholder = "Ask FiscalFlow: 'How much did I spend on Swiggy last quarter?'";
    }, 1000);
}

function computeIntelligenceResponse(query) {
    const q = query.toLowerCase();
    const fmt = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' });

    // 1. Identify Swiggy/Zomato/Food spending query
    if (q.includes('swiggy') || q.includes('zomato') || q.includes('food')) {
        const keyword = q.includes('swiggy') ? 'swiggy' : (q.includes('zomato') ? 'zomato' : 'food');
        const matches = state.transactions.filter(t => t.description.toLowerCase().includes(keyword) || (t.category && t.category.name.toLowerCase() === 'food'));
        const total = matches.reduce((sum, t) => sum + t.amount, 0);
        return `I checked your transaction ledger. You have <b>${matches.length}</b> transactions matching "${keyword}". Total spending is <b>${fmt.format(total)}</b>. The average order size is ${matches.length ? fmt.format(total / matches.length) : '₹0.00'}.`;
    }

    // 2. Identify Net Worth query
    if (q.includes('net worth') || q.includes('wealth') || q.includes('assets') || q.includes('liabilities')) {
        return `Your net worth is currently <b>${fmt.format(state.netWorth.net_worth)}</b>. This comprises <b>${fmt.format(state.netWorth.total_assets)}</b> in assets (Liquid: ${fmt.format(state.netWorth.breakdown.liquid_assets)}, Investments: ${fmt.format(state.netWorth.breakdown.investments)}) and <b>${fmt.format(state.netWorth.total_liabilities)}</b> in liabilities (Credit Cards: ${fmt.format(state.netWorth.breakdown.credit_card_debt)}, Loans: ${fmt.format(state.netWorth.breakdown.loans)}).`;
    }

    // 3. Identify Income or Earnings query
    if (q.includes('salary') || q.includes('income') || q.includes('earn')) {
        const matches = state.transactions.filter(t => t.type === 'INCOME');
        const total = matches.reduce((sum, t) => sum + t.amount, 0);
        return `You earned a total of <b>${fmt.format(total)}</b> across <b>${matches.length}</b> deposits this period. Your primary income stream is labeled "${matches[0]?.description || 'Salary'}".`;
    }

    // 4. Identify Subscriptions query
    if (q.includes('subscription') || q.includes('netflix') || q.includes('spotify') || q.includes('prime')) {
        const activeCount = state.subscriptions.filter(s => s.is_active).length;
        const totalCost = state.subscriptions.reduce((sum, s) => sum + s.amount, 0);
        return `You have <b>${state.subscriptions.length}</b> registered subscriptions (<b>${activeCount}</b> currently active), costing you <b>${fmt.format(totalCost)}</b> per billing cycle. Spotting unused subscriptions is a primary leakage heuristic.`;
    }

    // 5. Identify savings / budget queries
    if (q.includes('savings') || q.includes('goals') || q.includes('emergency')) {
        const emergencyGoal = state.goals.find(g => g.name.toUpperCase().includes('EMERGENCY'));
        if (emergencyGoal) {
            return `You are currently tracking <b>${state.goals.length}</b> goal trackers. Your primary Emergency Fund goal is <b>${((emergencyGoal.current_amount / emergencyGoal.target_amount)*100).toFixed(0)}%</b> complete, targeting ${fmt.format(emergencyGoal.target_amount)}.`;
        }
        return `You are tracking <b>${state.goals.length}</b> goals. The overall average progress rate is ${state.goals.length ? (state.goals.reduce((acc, g) => acc + (g.current_amount/g.target_amount)*100, 0) / state.goals.length).toFixed(0) : 0}%.`;
    }

    // Default Fallback Response
    return `I received your query: "${query}". I search accounts, transactions, and categories dynamically. Ask about food spending ("zomato"), earnings ("salary"), wealth limits ("net worth"), or goals ("emergency fund").`;
}

// ==========================================
// ACCOUNTS TAB RENDERER
// ==========================================
function renderAccountsTab() {
    const fmt = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 });

    const liquidTypes = ['SAVINGS', 'SALARY', 'CURRENT', 'WALLET', 'CASH'];
    const dematTypes = ['DEMAT', 'INVESTMENT'];
    const liabilityTypes = ['CREDIT_CARD', 'LOAN'];

    const liquidAccounts = state.accounts.filter(a => liquidTypes.includes((a.account_type || '').toUpperCase()));
    const dematAccounts = state.accounts.filter(a => dematTypes.includes((a.account_type || '').toUpperCase()) || (a.bank_name && ['groww', 'angel one', 'angle one', 'zerodha'].some(b => a.bank_name.toLowerCase().includes(b))));
    const otherAccounts = state.accounts.filter(a => !liquidAccounts.includes(a) && !dematAccounts.includes(a));

    const totalLiquid = liquidAccounts.reduce((sum, a) => sum + (parseFloat(a.current_balance) || 0), 0);
    const totalDemat = dematAccounts.reduce((sum, a) => sum + (parseFloat(a.current_balance) || 0), 0);
    const totalLiabilities = otherAccounts.filter(a => liabilityTypes.includes((a.account_type || '').toUpperCase()))
        .reduce((sum, a) => sum + Math.abs(parseFloat(a.current_balance) || 0), 0);

    const elLiquid = document.getElementById('acc-metric-liquid');
    if (elLiquid) elLiquid.textContent = fmt.format(totalLiquid);

    const elDemat = document.getElementById('acc-metric-demat');
    if (elDemat) elDemat.textContent = fmt.format(totalDemat);

    const elCount = document.getElementById('acc-metric-count');
    if (elCount) elCount.textContent = state.accounts.length;

    const elLiab = document.getElementById('acc-metric-liabilities');
    if (elLiab) elLiab.textContent = fmt.format(totalLiabilities);

    const bankCountBadge = document.getElementById('bank-accounts-count');
    if (bankCountBadge) bankCountBadge.textContent = `${liquidAccounts.length} Accounts`;

    const dematCountBadge = document.getElementById('demat-accounts-count');
    if (dematCountBadge) dematCountBadge.textContent = `${dematAccounts.length} Accounts`;

    const otherCountBadge = document.getElementById('other-accounts-count');
    if (otherCountBadge) otherCountBadge.textContent = `${otherAccounts.length} Accounts`;

    // Render Bank Accounts Grid
    const bankGrid = document.getElementById('bank-accounts-grid');
    if (bankGrid) {
        bankGrid.innerHTML = '';
        if (liquidAccounts.length === 0) {
            bankGrid.innerHTML = `
                <div class="col-span-full p-8 text-center bg-surface-container-low rounded-xl border border-dashed border-outline-variant">
                    <p class="text-xs text-on-surface-variant font-medium">No liquid savings or bank accounts added yet.</p>
                    <button class="mt-3 px-3 py-1.5 bg-primary text-on-primary rounded-lg text-xs font-bold" onclick="openAddAccountModal()">+ Add Bank Account</button>
                </div>`;
        } else {
            liquidAccounts.forEach(acc => {
                const accNum = acc.account_number ? `<span class="text-[11px] font-mono text-on-surface-variant font-medium">A/C: ${acc.account_number}</span>` : '<span class="text-[11px] text-outline">No A/C Number</span>';
                bankGrid.innerHTML += `
                    <div class="glass-card rounded-xl p-5 border border-outline-variant hover:border-primary transition-all duration-300 relative group flex flex-col justify-between">
                        <div>
                            <div class="flex justify-between items-start mb-3">
                                <div class="flex items-center gap-2.5">
                                    <div class="w-10 h-10 rounded-full bg-emerald-50 text-emerald-700 flex items-center justify-center border border-emerald-100">
                                        <span class="material-symbols-outlined text-[20px]">account_balance</span>
                                    </div>
                                    <div>
                                        <h4 class="text-xs font-extrabold text-primary leading-tight">${acc.name}</h4>
                                        <p class="text-[11px] text-on-surface-variant">${acc.bank_name || 'Bank'}</p>
                                    </div>
                                </div>
                                <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 uppercase tracking-wider">${acc.account_type}</span>
                            </div>
                            <div class="my-3 pb-3 border-b border-outline-variant flex justify-between items-baseline">
                                <div>
                                    <span class="text-[10px] text-on-surface-variant uppercase font-bold tracking-wider">Current Balance</span>
                                    <p class="text-xl font-bold font-data-mono text-primary mt-0.5">${fmt.format(acc.current_balance)}</p>
                                </div>
                                ${accNum}
                            </div>
                        </div>
                        <div class="flex justify-between items-center pt-1">
                            <button class="text-xs font-bold text-primary hover:underline flex items-center gap-1" onclick="filterTransactionsByAccount(${acc.id})">
                                <span class="material-symbols-outlined text-sm">receipt_long</span> View Ledger
                            </button>
                            <button class="text-xs font-bold text-rose-600 hover:text-rose-800 flex items-center gap-1 opacity-80 group-hover:opacity-100 transition-opacity" onclick="deleteAccount(${acc.id})">
                                <span class="material-symbols-outlined text-sm">delete</span> Delete
                            </button>
                        </div>
                    </div>`;
            });
        }
    }

    // Render Demat Accounts Grid
    const dematGrid = document.getElementById('demat-accounts-grid');
    if (dematGrid) {
        dematGrid.innerHTML = '';
        if (dematAccounts.length === 0) {
            dematGrid.innerHTML = `
                <div class="col-span-full p-8 text-center bg-surface-container-low rounded-xl border border-dashed border-outline-variant">
                    <p class="text-xs text-on-surface-variant font-medium">No Demat or stock broker accounts linked yet.</p>
                    <button class="mt-3 px-3 py-1.5 bg-primary text-on-primary rounded-lg text-xs font-bold" onclick="openAddAccountModal()">+ Add Demat Account (Groww/Angel One)</button>
                </div>`;
        } else {
            dematAccounts.forEach(acc => {
                const clientId = acc.account_number ? `<span class="text-[11px] font-mono text-indigo-900 bg-indigo-50 px-2 py-0.5 rounded font-bold">Client ID: ${acc.account_number}</span>` : '';
                dematGrid.innerHTML += `
                    <div class="glass-card rounded-xl p-5 border border-outline-variant hover:border-indigo-400 transition-all duration-300 relative group flex flex-col justify-between">
                        <div>
                            <div class="flex justify-between items-start mb-3">
                                <div class="flex items-center gap-2.5">
                                    <div class="w-10 h-10 rounded-full bg-indigo-50 text-indigo-700 flex items-center justify-center border border-indigo-100">
                                        <span class="material-symbols-outlined text-[20px]">trending_up</span>
                                    </div>
                                    <div>
                                        <h4 class="text-xs font-extrabold text-primary leading-tight">${acc.name}</h4>
                                        <p class="text-[11px] text-on-surface-variant">${acc.bank_name || 'Broker Platform'}</p>
                                    </div>
                                </div>
                                <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-indigo-100 text-indigo-800 uppercase tracking-wider">DEMAT</span>
                            </div>
                            <div class="my-3 pb-3 border-b border-outline-variant flex justify-between items-baseline">
                                <div>
                                    <span class="text-[10px] text-on-surface-variant uppercase font-bold tracking-wider">Portfolio / Balance</span>
                                    <p class="text-xl font-bold font-data-mono text-indigo-900 mt-0.5">${fmt.format(acc.current_balance)}</p>
                                </div>
                                ${clientId}
                            </div>
                        </div>
                        <div class="flex justify-between items-center pt-1">
                            <div class="flex gap-2">
                                <button class="text-xs font-bold text-primary hover:underline flex items-center gap-1" onclick="switchTab('investments')">
                                    <span class="material-symbols-outlined text-sm">pie_chart</span> Portfolio
                                </button>
                                <button class="text-xs font-bold text-indigo-600 hover:underline flex items-center gap-1" onclick="openImportDematModal()">
                                    <span class="material-symbols-outlined text-sm">upload_file</span> Import
                                </button>
                            </div>
                            <button class="text-xs font-bold text-rose-600 hover:text-rose-800 flex items-center gap-1 opacity-80 group-hover:opacity-100 transition-opacity" onclick="deleteAccount(${acc.id})">
                                <span class="material-symbols-outlined text-sm">delete</span> Delete
                            </button>
                        </div>
                    </div>`;
            });
        }
    }

    // Render Other / Credit Cards Grid
    const otherGrid = document.getElementById('other-accounts-grid');
    if (otherGrid) {
        otherGrid.innerHTML = '';
        if (otherAccounts.length === 0) {
            otherGrid.innerHTML = `
                <div class="col-span-full p-6 text-center bg-surface-container-low rounded-xl border border-outline-variant">
                    <p class="text-xs text-on-surface-variant">No credit cards or debt facilities active. Zero liabilities.</p>
                </div>`;
        } else {
            otherAccounts.forEach(acc => {
                otherGrid.innerHTML += `
                    <div class="glass-card rounded-xl p-5 border border-outline-variant hover:border-primary transition-all duration-300 relative group flex flex-col justify-between">
                        <div>
                            <div class="flex justify-between items-start mb-3">
                                <div class="flex items-center gap-2.5">
                                    <div class="w-10 h-10 rounded-full bg-rose-50 text-rose-700 flex items-center justify-center border border-rose-100">
                                        <span class="material-symbols-outlined text-[20px]">credit_card</span>
                                    </div>
                                    <div>
                                        <h4 class="text-xs font-extrabold text-primary leading-tight">${acc.name}</h4>
                                        <p class="text-[11px] text-on-surface-variant">${acc.bank_name || 'Issuer'}</p>
                                    </div>
                                </div>
                                <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-100 text-rose-800 uppercase tracking-wider">${acc.account_type}</span>
                            </div>
                            <div class="my-3 pb-3 border-b border-outline-variant">
                                <span class="text-[10px] text-on-surface-variant uppercase font-bold tracking-wider">Balance / Owed</span>
                                <p class="text-xl font-bold font-data-mono text-rose-700 mt-0.5">${fmt.format(acc.current_balance)}</p>
                            </div>
                        </div>
                        <div class="flex justify-between items-center pt-1">
                            <button class="text-xs font-bold text-primary hover:underline flex items-center gap-1" onclick="filterTransactionsByAccount(${acc.id})">
                                <span class="material-symbols-outlined text-sm">receipt_long</span> Ledger
                            </button>
                            <button class="text-xs font-bold text-rose-600 hover:text-rose-800 flex items-center gap-1" onclick="deleteAccount(${acc.id})">
                                <span class="material-symbols-outlined text-sm">delete</span> Delete
                            </button>
                        </div>
                    </div>`;
            });
        }
    }
}

// ==========================================
// FORM SUBMIT HANDLERS & OPERATIONS
// ==========================================

async function handleAddAccount(e) {
    e.preventDefault();
    const name = document.getElementById('acc-name').value;
    const bank_name = document.getElementById('acc-bank').value;
    const account_type = document.getElementById('acc-type').value;
    const account_number = document.getElementById('acc-number')?.value || null;
    const opening_balance = parseFloat(document.getElementById('acc-balance').value) || 0.0;
    const currency = 'INR';

    try {
        const res = await fetch(`${API_BASE}/accounts/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, bank_name, account_type, account_number, opening_balance, currency })
        });
        
        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || "Account creation failed");
        }
        
        showToast(`Account "${name}" successfully registered!`, "success");
        closeModal('add-account-modal');
        document.getElementById('add-account-form').reset();
        
        // Refresh & render
        showLoading(true);
        await Promise.all([fetchAccounts(), fetchNetWorth(), fetchHealthScore(), fetchForecast(), fetchInvestmentsAnalysis()]);
        renderAll();
        
        // Take user directly to accounts tab so they see their new account immediately!
        switchTab('accounts');
    } catch (err) {
        showToast("Error creating account: " + err.message, "error");
    } finally {
        showLoading(false);
    }
}

async function handleAddTransaction(e) {
    e.preventDefault();
    const date = document.getElementById('tx-date').value;
    const description = document.getElementById('tx-desc').value;
    const amount = parseFloat(document.getElementById('tx-amount').value);
    const type = document.getElementById('tx-type').value;
    const category_id = parseInt(document.getElementById('tx-category').value) || null;
    const account_id = parseInt(document.getElementById('tx-account').value);
    const destination_account_id = parseInt(document.getElementById('tx-dest-account').value) || null;
    const notes = document.getElementById('tx-notes').value || "";

    try {
        const res = await fetch(`${API_BASE}/transactions/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date, description, amount, type, category_id, account_id, destination_account_id, notes })
        });
        
        if (!res.ok) throw new Error("Transaction entry failed");
        
        showToast("Transaction logged!", "success");
        closeModal('add-tx-modal');
        document.getElementById('add-tx-form').reset();
        
        showLoading(true);
        await Promise.all([
            fetchTransactions(),
            fetchAccounts(),
            fetchNetWorth(),
            fetchHealthScore(),
            fetchForecast(),
            fetchFYReport()
        ]);
        renderAll();
    } catch (err) {
        showToast("Error logging entry: " + err.message, "error");
    } finally {
        showLoading(false);
    }
}

async function handleImportStatement(e) {
    e.preventDefault();
    const account_id = document.getElementById('import-account').value;
    const bank_type = document.getElementById('import-bank').value;
    const fileInput = document.getElementById('import-file');
    
    if (fileInput.files.length === 0) {
        showToast("Please choose a statement file to upload.", "error");
        return;
    }

    const formData = new FormData();
    formData.append('account_id', account_id);
    formData.append('bank_type', bank_type);
    formData.append('file', fileInput.files[0]);

    try {
        showLoading(true);
        const res = await fetch(`${API_BASE}/transactions/import`, {
            method: 'POST',
            body: formData
        });
        
        if (!res.ok) throw new Error("File upload failed");
        const data = await res.json();
        
        showToast(data.message || "Statement imported successfully!", "success");
        closeModal('import-modal');
        document.getElementById('import-statement-form').reset();
        
        await Promise.all([
            fetchTransactions(),
            fetchAccounts(),
            fetchNetWorth(),
            fetchHealthScore(),
            fetchForecast(),
            fetchInsights(),
            fetchFYReport()
        ]);
        renderAll();
    } catch (err) {
        showToast("Import failed: " + err.message, "error");
    } finally {
        showLoading(false);
    }
}

async function triggerTransferDetection() {
    try {
        showLoading(true);
        const res = await fetch(`${API_BASE}/transactions/detect-transfers`, { method: 'POST' });
        if (!res.ok) throw new Error("Transfer heuristic matching failed");
        const data = await res.json();
        showToast(data.message, "success");
        
        await Promise.all([
            fetchTransactions(),
            fetchAccounts(),
            fetchNetWorth(),
            fetchHealthScore(),
            fetchInsights(),
            fetchFYReport()
        ]);
        renderAll();
    } catch (err) {
        showToast("Heuristics failed: " + err.message, "error");
    } finally {
        showLoading(false);
    }
}

async function handleAddSubscription(e) {
    e.preventDefault();
    const name = document.getElementById('sub-name').value;
    const amount = parseFloat(document.getElementById('sub-amount').value);
    const billing_cycle = document.getElementById('sub-cycle').value;
    const account_id = parseInt(document.getElementById('sub-account').value);
    const next_renewal_date = new Date().toISOString().split('T')[0]; // Default today

    try {
        const res = await fetch(`${API_BASE}/subscriptions/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, amount, billing_cycle, account_id, next_renewal_date, is_active: true })
        });
        if (!res.ok) throw new Error("Subscription adding failed");
        
        showToast("Subscription tracker added!", "success");
        closeModal('add-sub-modal');
        document.getElementById('add-sub-form').reset();
        
        showLoading(true);
        await Promise.all([fetchSubscriptions(), fetchInsights(), fetchHealthScore()]);
        renderAll();
    } catch (err) {
        showToast("Failed to add subscription: " + err.message, "error");
    } finally {
        showLoading(false);
    }
}

async function handleAddGoal(e) {
    e.preventDefault();
    const name = document.getElementById('goal-name').value;
    const target_amount = parseFloat(document.getElementById('goal-target').value);
    const current_amount = parseFloat(document.getElementById('goal-current').value);
    const deadline = document.getElementById('goal-deadline').value;

    try {
        const res = await fetch(`${API_BASE}/goals/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, target_amount, current_amount, deadline, status: 'IN_PROGRESS' })
        });
        if (!res.ok) throw new Error("Goal creation failed");
        
        showToast("Goal created!", "success");
        closeModal('add-goal-modal');
        document.getElementById('add-goal-form').reset();
        
        showLoading(true);
        await Promise.all([fetchGoals(), fetchHealthScore()]);
        renderAll();
    } catch (err) {
        showToast("Failed to create goal: " + err.message, "error");
    } finally {
        showLoading(false);
    }
}

// DELETE HANDLERS

async function deleteTransaction(id) {
    if (!confirm("Remove this ledger transaction? Parent account balance will be adjusted.")) return;
    try {
        showLoading(true);
        const res = await fetch(`${API_BASE}/transactions/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error("Transaction deletion failed");
        showToast("Transaction removed", "success");
        
        await Promise.all([
            fetchTransactions(),
            fetchAccounts(),
            fetchNetWorth(),
            fetchHealthScore(),
            fetchForecast(),
            fetchFYReport()
        ]);
        renderAll();
    } catch (err) {
        showToast("Error deleting transaction: " + err.message, "error");
    } finally {
        showLoading(false);
    }
}

async function deleteSubscription(id) {
    if (!confirm("Delete this subscription tracker?")) return;
    try {
        showLoading(true);
        const res = await fetch(`${API_BASE}/subscriptions/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error("Subscription deletion failed");
        showToast("Subscription removed", "success");
        
        await Promise.all([fetchSubscriptions(), fetchInsights(), fetchHealthScore()]);
        renderAll();
    } catch (err) {
        showToast("Error: " + err.message, "error");
    } finally {
        showLoading(false);
    }
}

async function deleteGoal(id) {
    if (!confirm("Remove this savings goal?")) return;
    try {
        showLoading(true);
        const res = await fetch(`${API_BASE}/goals/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error("Goal deletion failed");
        showToast("Goal removed", "success");
        
        await Promise.all([fetchGoals(), fetchHealthScore()]);
        renderAll();
    } catch (err) {
        showToast("Error: " + err.message, "error");
    } finally {
        showLoading(false);
    }
}

// ==========================================
// UTILITY SHIMS
// ==========================================

function showLoading(show = true) {
    const el = document.getElementById('loading-indicator');
    if (!el) return;
    if (show) {
        el.classList.remove('hidden');
    } else {
        el.classList.add('hidden');
    }
}

function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-sm pointer-events-none';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const bgClass = type === 'success' ? 'bg-emerald-700 text-white' : (type === 'error' ? 'bg-rose-700 text-white' : 'bg-primary text-white');
    const icon = type === 'success' ? 'check_circle' : (type === 'error' ? 'error' : 'info');

    toast.className = `${bgClass} px-4 py-3 rounded-xl shadow-xl flex items-center gap-2 text-xs font-semibold pointer-events-auto fade-in transition-all duration-300`;
    toast.innerHTML = `<span class="material-symbols-outlined text-sm">${icon}</span> <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

window.showLoading = showLoading;
window.showToast = showToast;

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Global modal triggers
window.openModal = function(id) {
    const m = document.getElementById(id);
    if (m) {
        m.classList.remove('hidden');
        m.classList.add('flex');
    }
};

window.closeModal = function(id) {
    const m = document.getElementById(id);
    if (m) {
        m.classList.remove('flex');
        m.classList.add('hidden');
    }
};

function escapeJsQuotes(str) {
    if (!str) return '';
    return str.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

// ==========================================
// MASTER BUDGET TAB & ANALYTICS RENDERER
// ==========================================

const MASTER_BUDGET_COLORS = [
    '#4f46e5', // Rent - Indigo
    '#f59e0b', // Lunch - Amber
    '#3b82f6', // Commute - Blue
    '#8b5cf6', // Lifestyle - Purple
    '#06b6d4', // Emergency - Cyan
    '#10b981', // SIP - Emerald
    '#64748b', // Flex Buffer - Slate
    '#ec4899', // Pink
    '#14b8a6'  // Teal
];

async function renderMasterBudgetTab() {
    const fmt = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 });
    
    // Always refresh budget summary to get live spent data
    try {
        await fetchBudgetSummary();
        await fetchBudgets();
    } catch (e) {
        console.error("Error fetching budget summary: ", e);
    }

    const summary = state.budgetSummary || {
        planned_income: 31000,
        income_breakdown: { "Internship Stipend": 25000, "Family Support": 6000 },
        total_planned_allocation: 31000,
        total_actual_spent: 0,
        total_remaining: 31000,
        items: [],
        overgrown_count: 0,
        overgrown_items: []
    };

    // 1. KPI Cards
    const incEl = document.getElementById('mb-total-income');
    const planEl = document.getElementById('mb-total-planned');
    const actEl = document.getElementById('mb-total-actual');
    const flexEl = document.getElementById('mb-flex-buffer');
    const burnEl = document.getElementById('mb-overall-burn');

    if (incEl) incEl.textContent = fmt.format(summary.planned_income);
    if (planEl) planEl.textContent = fmt.format(summary.total_planned_allocation);
    if (actEl) actEl.textContent = fmt.format(summary.total_actual_spent);
    if (flexEl) flexEl.textContent = fmt.format(summary.total_remaining);
    
    if (burnEl) {
        const burnPct = summary.planned_income > 0 
            ? ((summary.total_actual_spent / summary.planned_income) * 100).toFixed(1) 
            : 0;
        burnEl.textContent = `${burnPct}% Burned`;
    }

    // 2. Overgrown Alert Banner
    const banner = document.getElementById('master-budget-overgrown-banner');
    const countBadge = document.getElementById('overgrown-count-badge');
    const pillsContainer = document.getElementById('overgrown-items-pills');

    if (banner && countBadge && pillsContainer) {
        if (summary.overgrown_count > 0) {
            banner.classList.remove('hidden');
            countBadge.textContent = `${summary.overgrown_count} Line${summary.overgrown_count > 1 ? 's' : ''} Exceeded`;
            pillsContainer.innerHTML = '';
            summary.overgrown_items.forEach(item => {
                const overspend = item.spent - item.amount;
                pillsContainer.innerHTML += `
                    <div class="px-3 py-1.5 bg-rose-100 border border-rose-300 rounded-lg text-xs flex items-center gap-2 font-semibold text-rose-900">
                        <span class="material-symbols-outlined text-sm text-rose-700">warning</span>
                        <span>${item.name}: Target <b>${fmt.format(item.amount)}</b> | Spent <b>${fmt.format(item.spent)}</b> (<span class="text-rose-700 font-bold">+${fmt.format(overspend)} over</span>)</span>
                    </div>`;
            });
        } else {
            banner.classList.add('hidden');
        }
    }

    // 3. Render Visual Donut Chart
    renderMasterBudgetDonut(summary);

    // 4. Render Target vs Actual Progress Bars
    renderMasterBudgetProgressBars(summary);

    // 5. Render Master Budget Table
    renderMasterBudgetTable(summary);
}

function renderMasterBudgetDonut(summary) {
    const svg = document.getElementById('mb-donut-svg');
    const legend = document.getElementById('mb-donut-legend');
    if (!svg || !legend) return;

    svg.innerHTML = '';
    legend.innerHTML = '';

    const items = summary.items || [];
    if (items.length === 0) {
        svg.innerHTML = `<circle cx="50" cy="50" r="38" fill="transparent" stroke="#e2e8f0" stroke-width="14"></circle>`;
        legend.innerHTML = `<div class="col-span-2 text-center text-on-surface-variant text-xs">No allocations found. Click 'Reset to Master Plan' to initialize.</div>`;
        return;
    }

    const totalTarget = summary.total_planned_allocation || 31000;
    const circumference = 2 * Math.PI * 38; // radius = 38 => ~238.76
    let accumulatedPercent = 0;

    const fmt = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 });

    items.forEach((item, index) => {
        const color = MASTER_BUDGET_COLORS[index % MASTER_BUDGET_COLORS.length];
        const percent = (item.amount / totalTarget);
        const strokeDash = percent * circumference;
        const strokeOffset = -accumulatedPercent * circumference;

        // SVG Circle segment
        const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        circle.setAttribute("cx", "50");
        circle.setAttribute("cy", "50");
        circle.setAttribute("r", "38");
        circle.setAttribute("fill", "transparent");
        circle.setAttribute("stroke", color);
        circle.setAttribute("stroke-width", "14");
        circle.setAttribute("stroke-dasharray", `${strokeDash} ${circumference - strokeDash}`);
        circle.setAttribute("stroke-dashoffset", strokeOffset);
        circle.setAttribute("class", "transition-all duration-500 hover:opacity-80 cursor-pointer");
        
        const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
        title.textContent = `${item.name}: ${fmt.format(item.amount)} (${(percent * 100).toFixed(1)}%)`;
        circle.appendChild(title);
        
        svg.appendChild(circle);

        // Legend Item
        legend.innerHTML += `
            <div class="flex items-center gap-2">
                <span class="w-2.5 h-2.5 rounded-full flex-shrink-0" style="background-color: ${color}"></span>
                <span class="truncate text-primary font-medium" title="${item.name}">${item.name}</span>
                <span class="ml-auto font-data-mono font-bold text-on-surface-variant">${(percent * 100).toFixed(1)}%</span>
            </div>`;

        accumulatedPercent += percent;
    });
}

function renderMasterBudgetProgressBars(summary) {
    const container = document.getElementById('mb-progress-bars-container');
    if (!container) return;

    container.innerHTML = '';
    const items = summary.items || [];
    if (items.length === 0) {
        container.innerHTML = `<p class="py-4 text-center text-on-surface-variant text-xs">No budget lines configured.</p>`;
        return;
    }

    const fmt = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 });

    items.forEach(item => {
        const pct = item.percent_used || 0;
        const cappedWidth = Math.min(100, pct);
        
        let barColor = 'bg-emerald-500';
        let statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] bg-emerald-100 text-emerald-800 font-bold">Healthy (${pct}%)</span>`;
        
        if (item.is_overgrown) {
            barColor = 'bg-rose-500 animate-pulse';
            statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] bg-rose-100 text-rose-800 font-bold border border-rose-300">OVERGROWN (${pct}%)</span>`;
        } else if (pct >= 80) {
            barColor = 'bg-amber-500';
            statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] bg-amber-100 text-amber-800 font-bold">Near Cap (${pct}%)</span>`;
        }

        container.innerHTML += `
            <div>
                <div class="flex justify-between items-center mb-1.5">
                    <span class="font-bold text-primary">${item.name}</span>
                    <div class="flex items-center gap-2">
                        ${statusBadge}
                        <span class="font-data-mono font-bold text-primary">${fmt.format(item.spent)} / <span class="text-on-surface-variant font-normal">${fmt.format(item.amount)}</span></span>
                    </div>
                </div>
                <div class="w-full bg-surface-container h-2.5 rounded-full overflow-hidden">
                    <div class="${barColor} h-full rounded-full transition-all duration-500" style="width: ${cappedWidth}%"></div>
                </div>
            </div>`;
    });
}

function renderMasterBudgetTable(summary) {
    const tbody = document.getElementById('master-budget-table-body');
    if (!tbody) return;

    tbody.innerHTML = '';
    const items = summary.items || [];
    if (items.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="px-6 py-8 text-center text-on-surface-variant text-xs">
                    No budget allocations active. Click 'Reset to Master Plan' to populate your master budget.
                </td>
            </tr>`;
        return;
    }

    const fmt = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 });
    const totalFunds = summary.planned_income || 31000;

    items.forEach(item => {
        const shareOfFunds = ((item.amount / totalFunds) * 100).toFixed(1);
        const isOver = item.is_overgrown;
        
        let statusBadge = `
            <span class="px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1 w-fit">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> In Budget
            </span>`;
            
        if (isOver) {
            const overAmt = item.spent - item.amount;
            statusBadge = `
                <span class="px-2.5 py-1 rounded-full text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-300 flex items-center gap-1 w-fit">
                    <span class="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse"></span> Overgrown (+${fmt.format(overAmt)})
                </span>`;
        }

        tbody.innerHTML += `
            <tr class="hover:bg-surface-container-low transition-colors duration-200 ${isOver ? 'bg-rose-50/40' : ''}">
                <td class="px-6 py-4 font-semibold text-primary">
                    <div class="flex items-center gap-2">
                        <span>${item.name}</span>
                    </div>
                </td>
                <td class="px-6 py-4 font-data-mono font-bold text-primary whitespace-nowrap">${fmt.format(item.amount)}</td>
                <td class="px-6 py-4 font-data-mono font-medium text-on-surface-variant whitespace-nowrap">${shareOfFunds}%</td>
                <td class="px-6 py-4 font-data-mono font-bold ${isOver ? 'text-rose-600' : 'text-primary'} whitespace-nowrap">${fmt.format(item.spent)}</td>
                <td class="px-6 py-4 font-data-mono font-bold whitespace-nowrap ${isOver ? 'text-rose-600' : 'text-secondary'}">${item.percent_used}%</td>
                <td class="px-6 py-4 whitespace-nowrap">${statusBadge}</td>
                <td class="px-6 py-4 text-on-surface-variant text-[11px] max-w-xs">${item.notes || '—'}</td>
                <td class="px-6 py-4 text-right whitespace-nowrap">
                    <button class="material-symbols-outlined text-outline hover:text-primary transition-colors text-[18px] mr-2" title="Edit Allocation" onclick="openEditBudgetModal(${item.id})">
                        edit
                    </button>
                    <button class="material-symbols-outlined text-outline hover:text-error transition-colors text-[18px]" title="Delete Allocation" onclick="deleteBudgetItem(${item.id})">
                        delete
                    </button>
                </td>
            </tr>`;
    });
}

// Modal & Budget Operations
window.openEditBudgetModal = function(budgetId) {
    const item = (state.budgetSummary?.items || []).find(b => b.id === budgetId) || state.budgets.find(b => b.id === budgetId);
    if (!item) {
        showToast("Budget allocation not found", "error");
        return;
    }

    document.getElementById('edit-budget-id').value = item.id;
    document.getElementById('edit-budget-name').value = item.name || '';
    document.getElementById('edit-budget-amount').value = item.amount || '';
    document.getElementById('edit-budget-notes').value = item.notes || '';

    // Populate category dropdown
    const catSel = document.getElementById('edit-budget-category');
    if (catSel) {
        catSel.innerHTML = '';
        state.categories.forEach(c => {
            const selected = c.id === item.category_id ? 'selected' : '';
            catSel.innerHTML += `<option value="${c.id}" ${selected}>${c.name} (${c.type})</option>`;
        });
    }

    openModal('edit-budget-modal');
};

window.openAddBudgetModal = function() {
    const catSel = document.getElementById('add-budget-category');
    if (catSel) {
        catSel.innerHTML = '';
        state.categories.forEach(c => {
            catSel.innerHTML += `<option value="${c.id}">${c.name} (${c.type})</option>`;
        });
    }
    document.getElementById('add-budget-form')?.reset();
    openModal('add-budget-modal');
};

async function handleEditBudget(e) {
    e.preventDefault();
    const id = document.getElementById('edit-budget-id').value;
    const name = document.getElementById('edit-budget-name').value;
    const amount = parseFloat(document.getElementById('edit-budget-amount').value);
    const category_id = parseInt(document.getElementById('edit-budget-category').value);
    const notes = document.getElementById('edit-budget-notes').value;

    try {
        showLoading(true);
        const res = await fetch(`${API_BASE}/budgets/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, amount, category_id, notes })
        });
        if (!res.ok) throw new Error("Failed to update budget");
        
        closeModal('edit-budget-modal');
        showToast("Budget allocation updated successfully!", "success");
        await renderMasterBudgetTab();
    } catch (err) {
        showToast("Error: " + err.message, "error");
    } finally {
        showLoading(false);
    }
}

async function handleAddBudget(e) {
    e.preventDefault();
    const name = document.getElementById('add-budget-name').value;
    const amount = parseFloat(document.getElementById('add-budget-amount').value);
    const category_id = parseInt(document.getElementById('add-budget-category').value);
    const notes = document.getElementById('add-budget-notes').value;

    const today = new Date();
    const startDate = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split('T')[0];
    const endDate = new Date(today.getFullYear(), today.getMonth() + 1, 0).toISOString().split('T')[0];

    try {
        showLoading(true);
        const res = await fetch(`${API_BASE}/budgets/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name,
                amount,
                category_id,
                notes,
                start_date: startDate,
                end_date: endDate
            })
        });
        if (!res.ok) throw new Error("Failed to add budget line item");

        closeModal('add-budget-modal');
        showToast("New allocation created successfully!", "success");
        await renderMasterBudgetTab();
    } catch (err) {
        showToast("Error: " + err.message, "error");
    } finally {
        showLoading(false);
    }
}

window.resetToMasterBudget = async function() {
    try {
        showLoading(true);
        const res = await fetch(`${API_BASE}/budgets/reset-master`, { method: 'POST' });
        if (!res.ok) throw new Error("Failed to reset master budget");
        showToast("Master Budget template restored (₹31,000 Total Cash Flow)!", "success");
        await renderMasterBudgetTab();
    } catch (err) {
        showToast("Reset error: " + err.message, "error");
    } finally {
        showLoading(false);
    }
};

window.deleteBudgetItem = async function(budgetId) {
    if (!confirm("Are you sure you want to remove this budget allocation line?")) return;
    try {
        showLoading(true);
        const res = await fetch(`${API_BASE}/budgets/${budgetId}`, { method: 'DELETE' });
        if (!res.ok) throw new Error("Failed to delete budget");
        showToast("Budget allocation removed.", "success");
        await renderMasterBudgetTab();
    } catch (err) {
        showToast("Delete error: " + err.message, "error");
    } finally {
        showLoading(false);
    }
};

// ==========================================
// TRANSACTION TAG OPERATIONS
// ==========================================

window.openEditTagModal = function(txId, currentTags, desc) {
    document.getElementById('edit-tag-tx-id').value = txId;
    document.getElementById('edit-tag-input').value = currentTags || '';
    document.getElementById('edit-tag-tx-desc').textContent = desc || 'Transaction Entry';
    openModal('edit-tag-modal');
};

window.appendTag = function(tag) {
    const input = document.getElementById('edit-tag-input');
    if (!input) return;
    const current = input.value.split(',').map(t => t.trim()).filter(Boolean);
    if (!current.includes(tag)) {
        current.push(tag);
        input.value = current.join(', ');
    }
};

async function handleEditTag(e) {
    e.preventDefault();
    const txId = document.getElementById('edit-tag-tx-id').value;
    const tags = document.getElementById('edit-tag-input').value.trim();
    const learnRule = document.getElementById('edit-tag-learn-rule')?.checked ?? true;

    try {
        showLoading(true);
        const res = await fetch(`${API_BASE}/transactions/${txId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tags })
        });
        if (!res.ok) throw new Error("Failed to update transaction tags");

        closeModal('edit-tag-modal');
        if (learnRule) {
            showToast("Tags updated & rule memorized for future repetitive transactions!", "success");
        } else {
            showToast("Transaction tags updated successfully!", "success");
        }
        await fetchTransactions();
        renderTransactionsTab();
    } catch (err) {
        showToast("Error updating tags: " + err.message, "error");
    } finally {
        showLoading(false);
    }
}

// ==========================================
// STATEMENT ATTACHMENTS & EXPORTS OPERATIONS
// ==========================================

async function fetchStatementFiles() {
    try {
        const res = await fetch(`${API_BASE}/statements/`);
        if (!res.ok) throw new Error("Failed to load statements");
        state.statementFiles = await res.json();
    } catch (err) {
        console.error("Error loading statements: ", err);
    }
}

async function fetchTagRules() {
    try {
        const res = await fetch(`${API_BASE}/statements/tag-rules`);
        if (!res.ok) throw new Error("Failed to load tag rules");
        state.tagRules = await res.json();
    } catch (err) {
        console.error("Error loading tag rules: ", err);
    }
}

window.openStatementsModal = async function() {
    showLoading(true);
    await Promise.all([fetchStatementFiles(), fetchTagRules()]);
    showLoading(false);

    // Populate Account select in export panel
    const expAcc = document.getElementById('export-account');
    if (expAcc) {
        expAcc.innerHTML = '<option value="">All Accounts</option>';
        state.accounts.forEach(a => {
            expAcc.innerHTML += `<option value="${a.id}">${a.name} (${a.bank_name})</option>`;
        });
    }

    // Populate Stored Statements Table
    const tbody = document.getElementById('statements-table-body');
    const badge = document.getElementById('statements-count-badge');
    if (badge) badge.textContent = `${state.statementFiles.length} File${state.statementFiles.length !== 1 ? 's' : ''}`;

    if (tbody) {
        tbody.innerHTML = '';
        if (state.statementFiles.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="px-4 py-8 text-center text-on-surface-variant text-xs">
                        No statement attachments stored yet. Upload a statement via "Import Statement" to view and download it here anytime.
                    </td>
                </tr>`;
        } else {
            state.statementFiles.forEach(f => {
                const uploadDate = new Date(f.upload_date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
                tbody.innerHTML += `
                    <tr class="hover:bg-surface-container-low transition-colors">
                        <td class="px-4 py-3 font-semibold text-primary">
                            <div class="flex items-center gap-1.5">
                                <span class="material-symbols-outlined text-sm text-teal-600">receipt</span>
                                <span class="truncate max-w-xs" title="${f.filename}">${f.filename}</span>
                            </div>
                        </td>
                        <td class="px-4 py-3 text-on-surface-variant whitespace-nowrap">${f.account_name}</td>
                        <td class="px-4 py-3 whitespace-nowrap"><span class="px-2 py-0.5 bg-surface-container rounded text-[10px] font-bold text-primary">${f.bank_type}</span></td>
                        <td class="px-4 py-3 text-on-surface-variant whitespace-nowrap">${uploadDate}</td>
                        <td class="px-4 py-3 font-data-mono whitespace-nowrap">${f.file_size_kb} KB</td>
                        <td class="px-4 py-3 text-right whitespace-nowrap">
                            <button class="px-2.5 py-1 bg-primary text-on-primary rounded text-xs font-bold hover:opacity-90 active:scale-95 transition-all flex items-center gap-1 ml-auto" onclick="downloadOriginalStatement(${f.id})">
                                <span class="material-symbols-outlined text-[14px]">download</span> Download Original
                            </button>
                        </td>
                    </tr>`;
            });
        }
    }

    // Populate Tag Rules Memory Container
    const rulesContainer = document.getElementById('tag-rules-container');
    if (rulesContainer) {
        rulesContainer.innerHTML = '';
        if (state.tagRules.length === 0) {
            rulesContainer.innerHTML = `
                <p class="col-span-2 py-3 text-center text-on-surface-variant text-xs">
                    No custom repetitive rules memorized yet. When you edit tags on any transaction, FiscalFlow automatically remembers the merchant pattern.
                </p>`;
        } else {
            state.tagRules.forEach(r => {
                rulesContainer.innerHTML += `
                    <div class="p-2.5 bg-surface-container rounded-lg border border-outline-variant flex items-center justify-between">
                        <div>
                            <span class="font-bold text-primary">"${r.pattern}"</span>
                            <div class="flex flex-wrap gap-1 mt-1">
                                ${r.tags.split(',').map(t => `<span class="px-1.5 py-0.5 bg-white border border-outline-variant rounded text-[9px] font-semibold text-primary">#${t.trim()}</span>`).join('')}
                            </div>
                        </div>
                        <span class="text-[10px] text-on-surface-variant font-bold bg-surface-container-high px-2 py-0.5 rounded-full">${r.match_count}x applied</span>
                    </div>`;
            });
        }
    }

    openModal('statements-manager-modal');
};

window.downloadOriginalStatement = function(statementId) {
    window.location.href = `${API_BASE}/statements/${statementId}/download`;
    showToast("Downloading original statement file...", "info");
};

window.exportAxisStatement = function() {
    window.location.href = `${API_BASE}/statements/export/axis`;
    showToast("Downloading transactions in Axis Bank statement format (CSV)...", "success");
};

window.exportFilteredAxisStatement = function() {
    const accId = document.getElementById('export-account')?.value || '';
    const start = document.getElementById('export-start-date')?.value || '';
    const end = document.getElementById('export-end-date')?.value || '';
    
    let url = `${API_BASE}/statements/export/axis?`;
    if (accId) url += `account_id=${accId}&`;
    if (start) url += `start_date=${start}&`;
    if (end) url += `end_date=${end}&`;
    
    window.location.href = url;
    showToast("Downloading filtered Axis Bank Statement CSV...", "success");
};

window.exportFullLedgerCSV = function() {
    const accId = document.getElementById('export-account')?.value || '';
    const start = document.getElementById('export-start-date')?.value || '';
    const end = document.getElementById('export-end-date')?.value || '';
    
    let url = `${API_BASE}/statements/export/full-csv?`;
    if (accId) url += `account_id=${accId}&`;
    if (start) url += `start_date=${start}&`;
    if (end) url += `end_date=${end}&`;
    
    window.location.href = url;
    showToast("Downloading full transaction ledger CSV...", "success");
};

window.reapplyAllTagRules = async function() {
    try {
        showLoading(true);
        const res = await fetch(`${API_BASE}/statements/tag-rules/apply-all`, { method: 'POST' });
        if (!res.ok) throw new Error("Failed to re-apply rules");
        const data = await res.json();
        showToast(data.message || "Learned rules re-applied successfully!", "success");
        await fetchTransactions();
        await fetchTagRules();
        renderTransactionsTab();
        openStatementsModal();
    } catch (err) {
        showToast("Error: " + err.message, "error");
    } finally {
        showLoading(false);
    }
};

// ==========================================
// INVESTMENTS, DEMAT & SIP TRACKER ENGINE
// ==========================================

async function fetchInvestmentsAnalysis() {
    try {
        const res = await fetch(`${API_BASE}/investments/analysis`);
        if (!res.ok) throw new Error("Investments analysis load failed");
        state.investmentsAnalysis = await res.json();
    } catch (err) {
        console.warn("Investments analysis fetch error:", err);
    }
}

async function fetchSips() {
    try {
        const res = await fetch(`${API_BASE}/sips/`);
        if (!res.ok) throw new Error("SIPs load failed");
        state.sips = await res.json();
    } catch (err) {
        console.warn("SIPs fetch error:", err);
    }
}

window.openAddAccountModal = function() {
    const form = document.getElementById('add-account-form');
    if (form) form.reset();
    openModal('add-account-modal');
};

window.openImportDematModal = function() {
    populateAccountDropdowns();
    openModal('import-demat-modal');
};

window.openAddHoldingModal = function() {
    const form = document.getElementById('add-holding-form');
    if (form) form.reset();
    openModal('add-holding-modal');
};

window.openAddSipModal = function() {
    const form = document.getElementById('add-sip-form');
    if (form) form.reset();
    populateAccountDropdowns();
    openModal('add-sip-modal');
};

async function handleImportDemat(e) {
    e.preventDefault();
    const account_id = document.getElementById('demat-account-select').value;
    const broker_type = document.getElementById('demat-broker-type').value;
    const fileInput = document.getElementById('demat-file-input');

    if (!account_id) {
        showToast("Please select a Demat / Broker account first", "error");
        return;
    }
    if (!fileInput || !fileInput.files[0]) {
        showToast("Please choose a Demat statement file to upload", "error");
        return;
    }

    const formData = new FormData();
    formData.append('account_id', account_id);
    formData.append('broker_type', broker_type);
    formData.append('file', fileInput.files[0]);

    try {
        showLoading(true);
        const res = await fetch(`${API_BASE}/investments/import-demat`, {
            method: 'POST',
            body: formData
        });

        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || "Demat Statement import failed");
        }

        const data = await res.json();
        showToast(data.message || "Demat statement uploaded and synced successfully!", "success");
        closeModal('import-demat-modal');
        document.getElementById('import-demat-form').reset();

        await Promise.all([
            fetchAccounts(),
            fetchInvestmentsAnalysis(),
            fetchTransactions(),
            fetchNetWorth(),
            fetchStatementFiles()
        ]);
        renderAll();
    } catch (err) {
        showToast("Error importing Demat statement: " + err.message, "error");
    } finally {
        showLoading(false);
    }
}

async function handleAddHolding(e) {
    e.preventDefault();
    const name = document.getElementById('holding-name').value;
    const symbol = document.getElementById('holding-symbol').value || name.slice(0, 6).toUpperCase();
    const asset_class = document.getElementById('holding-asset-class').value;
    const broker = document.getElementById('holding-broker').value || 'Groww';
    const units = parseFloat(document.getElementById('holding-units').value) || 1.0;
    const purchase_price = parseFloat(document.getElementById('holding-buy-price').value) || 0.0;
    const current_value = parseFloat(document.getElementById('holding-curr-val').value) || (units * purchase_price);

    try {
        showLoading(true);
        const res = await fetch(`${API_BASE}/investments/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name,
                symbol,
                asset_class,
                broker,
                units,
                purchase_price,
                current_value
            })
        });

        if (!res.ok) throw new Error("Failed to save investment holding");

        showToast(`Holding ${symbol} saved to portfolio!`, "success");
        closeModal('add-holding-modal');
        document.getElementById('add-holding-form').reset();

        await Promise.all([fetchInvestmentsAnalysis(), fetchNetWorth()]);
        renderInvestmentsTab();
    } catch (err) {
        showToast("Error saving holding: " + err.message, "error");
    } finally {
        showLoading(false);
    }
}

async function handleAddSip(e) {
    e.preventDefault();
    const scheme_name = document.getElementById('sip-scheme-name').value;
    const amount = parseFloat(document.getElementById('sip-amount').value);
    const sip_day_of_month = parseInt(document.getElementById('sip-day').value) || 5;
    const broker = document.getElementById('sip-broker').value;
    const asset_class = document.getElementById('sip-asset-class').value;
    const account_id = document.getElementById('sip-account').value ? parseInt(document.getElementById('sip-account').value) : null;

    try {
        showLoading(true);
        const res = await fetch(`${API_BASE}/sips/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                scheme_name,
                amount,
                sip_day_of_month,
                broker,
                asset_class,
                account_id,
                status: 'ACTIVE'
            })
        });

        if (!res.ok) throw new Error("Failed to create SIP schedule");

        showToast(`SIP for ${scheme_name} (₹${amount}/mo) scheduled on ${sip_day_of_month}th!`, "success");
        closeModal('add-sip-modal');
        document.getElementById('add-sip-form').reset();

        await Promise.all([fetchSips(), fetchInvestmentsAnalysis()]);
        renderInvestmentsTab();
    } catch (err) {
        showToast("Error scheduling SIP: " + err.message, "error");
    } finally {
        showLoading(false);
    }
}

window.executeSip = async function(sipId) {
    try {
        showLoading(true);
        const res = await fetch(`${API_BASE}/sips/${sipId}/execute`, { method: 'POST' });
        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || "SIP execution failed");
        }
        const data = await res.json();
        showToast(data.message || "SIP investment executed and recorded!", "success");

        await Promise.all([fetchSips(), fetchAccounts(), fetchTransactions(), fetchNetWorth(), fetchInvestmentsAnalysis()]);
        renderAll();
    } catch (err) {
        showToast("Error executing SIP: " + err.message, "error");
    } finally {
        showLoading(false);
    }
};

window.deleteSip = async function(sipId) {
    if (!confirm("Are you sure you want to delete this SIP schedule?")) return;
    try {
        showLoading(true);
        const res = await fetch(`${API_BASE}/sips/${sipId}`, { method: 'DELETE' });
        if (!res.ok) throw new Error("Failed to delete SIP");
        showToast("SIP schedule removed", "success");
        await Promise.all([fetchSips(), fetchInvestmentsAnalysis()]);
        renderInvestmentsTab();
    } catch (err) {
        showToast("Error: " + err.message, "error");
    } finally {
        showLoading(false);
    }
};

window.deleteHolding = async function(holdingId) {
    if (!confirm("Are you sure you want to delete this portfolio holding?")) return;
    try {
        showLoading(true);
        const res = await fetch(`${API_BASE}/investments/${holdingId}`, { method: 'DELETE' });
        if (!res.ok) throw new Error("Failed to delete holding");
        showToast("Holding removed from portfolio", "success");
        await Promise.all([fetchInvestmentsAnalysis(), fetchNetWorth()]);
        renderInvestmentsTab();
    } catch (err) {
        showToast("Error: " + err.message, "error");
    } finally {
        showLoading(false);
    }
};

function renderInvestmentsTab() {
    const fmt = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 });
    const fmtDec = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', minimumFractionDigits: 2, maximumFractionDigits: 2 });
    
    const data = state.investmentsAnalysis || {
        portfolio_summary: { total_invested: 0, current_value: 0, total_pnl: 0, total_pnl_pct: 0 },
        sip_analytics: { monthly_committed_sip: 0, master_budget_target: 5500, sip_alignment_pct: 0, active_sips_count: 0, upcoming_sips: [] },
        asset_allocation: {},
        broker_breakdown: {},
        holdings: []
    };

    const summary = data.portfolio_summary || {};
    const sipInfo = data.sip_analytics || {};

    // 1. Top Metric Cards
    const totalValEl = document.getElementById('inv-total-value');
    if (totalValEl) totalValEl.textContent = fmt.format(summary.current_value || 0);

    const totalCostEl = document.getElementById('inv-total-cost');
    if (totalCostEl) totalCostEl.textContent = fmt.format(summary.total_invested || 0);

    const totalPnlEl = document.getElementById('inv-total-pnl-val');
    if (totalPnlEl) {
        const pnl = summary.total_pnl || 0;
        const sign = pnl >= 0 ? '+' : '';
        totalPnlEl.textContent = `${sign}${fmt.format(pnl)}`;
        totalPnlEl.className = `text-2xl font-extrabold font-data-mono ${pnl >= 0 ? 'text-secondary' : 'text-rose-600'}`;
    }

    const pnlBadgeEl = document.getElementById('inv-total-pnl-badge');
    if (pnlBadgeEl) {
        const pct = summary.total_pnl_pct || 0;
        const sign = pct >= 0 ? '+' : '';
        pnlBadgeEl.textContent = `${sign}${pct.toFixed(2)}% Overall Returns`;
        pnlBadgeEl.className = `text-xs font-bold mt-2 flex items-center gap-1 font-data-mono ${pct >= 0 ? 'text-secondary' : 'text-rose-600'}`;
    }

    const monthlySipEl = document.getElementById('inv-monthly-sip');
    if (monthlySipEl) monthlySipEl.textContent = fmt.format(sipInfo.monthly_committed_sip || 0);

    const sipNoteEl = document.getElementById('inv-sip-target-note');
    if (sipNoteEl) {
        const committed = sipInfo.monthly_committed_sip || 0;
        const target = sipInfo.master_budget_target || 5500;
        const pct = sipInfo.sip_alignment_pct || 0;
        if (committed >= target) {
            sipNoteEl.innerHTML = `<span class="material-symbols-outlined text-secondary text-sm">check_circle</span> Target ₹5,500/mo Achieved (${pct}%)`;
            sipNoteEl.className = "text-xs font-bold text-secondary mt-2 flex items-center gap-1";
        } else {
            sipNoteEl.innerHTML = `<span class="material-symbols-outlined text-amber-600 text-sm">info</span> ₹${target - committed} left to reach ₹5,500 Master Plan`;
            sipNoteEl.className = "text-xs font-bold text-amber-700 mt-2 flex items-center gap-1";
        }
    }

    // 2. Holdings Table
    const countBadge = document.getElementById('holdings-count-badge');
    if (countBadge) countBadge.textContent = `${data.holdings.length} Securities`;

    const tableBody = document.getElementById('inv-holdings-table-body');
    if (tableBody) {
        tableBody.innerHTML = '';
        if (data.holdings.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center py-8 text-on-surface-variant text-xs">
                        No investment holdings recorded. Click <strong>+ Add Stock / Holding</strong> or <strong>Upload Demat Statement</strong> to import your portfolio.
                    </td>
                </tr>`;
        } else {
            data.holdings.forEach(h => {
                const isProfit = h.pnl >= 0;
                const pnlSign = isProfit ? '+' : '';
                const pnlClass = isProfit ? 'text-secondary' : 'text-rose-600';

                let assetBadgeColor = 'bg-blue-100 text-blue-800';
                if (h.asset_class === 'MUTUAL_FUND') assetBadgeColor = 'bg-purple-100 text-purple-800';
                if (h.asset_class === 'ELSS') assetBadgeColor = 'bg-emerald-100 text-emerald-800';
                if (h.asset_class === 'ETF') assetBadgeColor = 'bg-amber-100 text-amber-800';
                if (h.asset_class === 'GOLD') assetBadgeColor = 'bg-yellow-100 text-yellow-800';

                tableBody.innerHTML += `
                    <tr class="hover:bg-surface-container-low transition-colors">
                        <td class="px-4 py-3">
                            <div class="font-bold text-primary">${h.name}</div>
                            <div class="text-[10px] text-on-surface-variant font-data-mono">${h.symbol || ''}</div>
                        </td>
                        <td class="px-4 py-3">
                            <span class="px-2 py-0.5 rounded text-[10px] font-bold ${assetBadgeColor}">${h.asset_class}</span>
                        </td>
                        <td class="px-4 py-3">
                            <span class="px-2 py-0.5 bg-surface-container-high rounded text-[10px] font-bold text-primary">${h.broker}</span>
                        </td>
                        <td class="px-4 py-3 text-right font-data-mono font-medium">${h.units !== null ? h.units : '—'}</td>
                        <td class="px-4 py-3 text-right font-data-mono font-medium">${fmtDec.format(h.purchase_price)}</td>
                        <td class="px-4 py-3 text-right font-data-mono font-bold text-primary">${fmt.format(h.current_value)}</td>
                        <td class="px-4 py-3 text-right font-data-mono font-bold ${pnlClass}">
                            ${pnlSign}${fmt.format(h.pnl)}<br/>
                            <span class="text-[10px] font-medium">(${pnlSign}${h.pnl_pct}%)</span>
                        </td>
                        <td class="px-4 py-3 text-right">
                            <button class="material-symbols-outlined text-outline hover:text-rose-600 transition-colors text-[18px]" onclick="deleteHolding(${h.id})" title="Delete Holding">delete</button>
                        </td>
                    </tr>`;
            });
        }
    }

    // 3. Broker Breakdown
    const brokerContainer = document.getElementById('inv-broker-distribution');
    if (brokerContainer) {
        brokerContainer.innerHTML = '';
        const brokers = Object.entries(data.broker_breakdown || {});
        const totalVal = summary.current_value || 1;
        if (brokers.length === 0) {
            brokerContainer.innerHTML = '<p class="text-xs text-on-surface-variant">No Demat accounts synced yet.</p>';
        } else {
            brokers.forEach(([broker, val]) => {
                const pct = Math.round((val / totalVal) * 100);
                brokerContainer.innerHTML += `
                    <div>
                        <div class="flex justify-between items-center text-xs mb-1">
                            <span class="font-bold text-primary flex items-center gap-1">
                                <span class="w-2 h-2 rounded-full bg-primary"></span> ${broker}
                            </span>
                            <span class="font-data-mono font-bold">${fmt.format(val)} (${pct}%)</span>
                        </div>
                        <div class="w-full bg-surface-container-high rounded-full h-2 overflow-hidden">
                            <div class="bg-primary h-2 rounded-full" style="width: ${pct}%"></div>
                        </div>
                    </div>`;
            });
        }
    }

    // 4. Asset Class Breakdown
    const assetContainer = document.getElementById('inv-asset-distribution');
    if (assetContainer) {
        assetContainer.innerHTML = '';
        const assets = Object.entries(data.asset_allocation || {});
        const totalVal = summary.current_value || 1;
        if (assets.length === 0) {
            assetContainer.innerHTML = '<p class="text-xs text-on-surface-variant">No assets allocated yet.</p>';
        } else {
            assets.forEach(([assetClass, val]) => {
                const pct = Math.round((val / totalVal) * 100);
                assetContainer.innerHTML += `
                    <div>
                        <div class="flex justify-between items-center text-xs mb-1">
                            <span class="font-bold text-primary flex items-center gap-1">
                                <span class="w-2 h-2 rounded-full bg-secondary"></span> ${assetClass}
                            </span>
                            <span class="font-data-mono font-bold">${fmt.format(val)} (${pct}%)</span>
                        </div>
                        <div class="w-full bg-surface-container-high rounded-full h-2 overflow-hidden">
                            <div class="bg-secondary h-2 rounded-full" style="width: ${pct}%"></div>
                        </div>
                    </div>`;
            });
        }
    }

    // 5. SIP Schedules Grid
    const sipGrid = document.getElementById('inv-sip-cards-grid');
    if (sipGrid) {
        sipGrid.innerHTML = '';
        const sipsList = state.sips || [];
        if (sipsList.length === 0) {
            sipGrid.innerHTML = `
                <div class="col-span-full py-8 text-center text-on-surface-variant text-xs">
                    No active SIP schedules. Click <strong>+ Add SIP Schedule</strong> to track your recurring monthly mutual fund investments.
                </div>`;
        } else {
            sipsList.forEach(s => {
                const daysLeft = s.days_remaining;
                let daysBadgeColor = 'bg-blue-100 text-blue-800';
                let daysText = `In ${daysLeft} days`;
                if (daysLeft === 0) {
                    daysBadgeColor = 'bg-emerald-100 text-emerald-800';
                    daysText = 'Today!';
                } else if (daysLeft < 0) {
                    daysBadgeColor = 'bg-amber-100 text-amber-800';
                    daysText = 'Due';
                }

                sipGrid.innerHTML += `
                    <div class="bg-surface-container-lowest border border-outline-variant rounded-xl p-5 shadow-sm flex flex-col justify-between hover:border-primary transition-all group">
                        <div>
                            <div class="flex justify-between items-start mb-3">
                                <span class="px-2 py-0.5 bg-purple-100 text-purple-800 rounded text-[10px] font-bold">${s.broker}</span>
                                <span class="px-2 py-0.5 rounded text-[10px] font-bold ${daysBadgeColor}">${daysText}</span>
                            </div>
                            <h4 class="font-bold text-primary text-sm line-clamp-1">${s.scheme_name}</h4>
                            <div class="flex items-center gap-2 mt-2">
                                <span class="text-xl font-extrabold text-primary font-data-mono">${fmt.format(s.amount)}</span>
                                <span class="text-[11px] text-on-surface-variant font-medium">/ month</span>
                            </div>
                            <div class="mt-4 pt-3 border-t border-outline-variant/60 text-xs space-y-1 text-on-surface-variant">
                                <div class="flex justify-between">
                                    <span>Cadence:</span>
                                    <span class="font-bold text-primary">${s.sip_day_of_month}th of every month</span>
                                </div>
                                <div class="flex justify-between">
                                    <span>Next Execution Date:</span>
                                    <span class="font-bold text-primary font-data-mono">${s.next_sip_date}</span>
                                </div>
                            </div>
                        </div>
                        <div class="mt-5 pt-3 border-t border-outline-variant/60 flex items-center justify-between gap-2">
                            <button class="px-3 py-1.5 bg-secondary-container text-on-secondary-container hover:bg-secondary-fixed rounded-lg text-xs font-bold flex items-center gap-1 shadow-sm transition-all" onclick="executeSip(${s.id})">
                                <span class="material-symbols-outlined text-sm">play_circle</span> Record Payment
                            </button>
                            <button class="material-symbols-outlined text-outline hover:text-rose-600 transition-colors text-[18px]" onclick="deleteSip(${s.id})" title="Delete SIP">delete</button>
                        </div>
                    </div>`;
            });
        }
    }
}

// ==========================================
// ACCOUNT MANAGEMENT & GLOBAL HELPERS
// ==========================================

async function deleteAccount(id) {
    const acc = state.accounts.find(a => a.id === id);
    const accName = acc ? acc.name : "this account";
    if (!confirm(`Are you sure you want to delete ${accName}? Any associated transactions will also be permanently deleted.`)) {
        return;
    }
    showLoading(true);
    try {
        const res = await fetch(`${API_BASE}/accounts/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error("Failed to delete account");
        showToast("Account deleted successfully.", "success");
        await Promise.all([fetchAccounts(), fetchNetWorth(), fetchHealthScore(), fetchTransactions(), fetchInvestmentsAnalysis()]);
        renderAll();
    } catch (err) {
        showToast("Error deleting account: " + err.message, "error");
    } finally {
        showLoading(false);
    }
}

async function cleanDuplicates() {
    if (!confirm("Are you sure you want to clean duplicate unused accounts? Accounts with zero balance and no transactions will be purged.")) {
        return;
    }
    showLoading(true);
    try {
        const res = await fetch(`${API_BASE}/accounts/clean-duplicates`, { method: 'POST' });
        if (!res.ok) throw new Error("Failed to clean duplicates");
        const data = await res.json();
        showToast(data.message || `Cleaned ${data.deleted_count} duplicate accounts.`, "success");
        await Promise.all([fetchAccounts(), fetchNetWorth(), fetchHealthScore()]);
        renderAll();
    } catch (err) {
        showToast("Error cleaning duplicates: " + err.message, "error");
    } finally {
        showLoading(false);
    }
}

function filterTransactionsByAccount(accountId) {
    state.filters.accountId = accountId;
    const filterSelect = document.getElementById('ledger-filter-account');
    if (filterSelect) filterSelect.value = accountId;
    switchTab('transactions');
    fetchTransactions().then(() => renderTransactionsTab());
}

function openSettingsModal() {
    openModal('settings-modal');
}

function openSupportModal() {
    openModal('support-modal');
}

function switchFinancialYear(fy) {
    state.activeFY = fy;
    fetchFYReport().then(() => {
        renderFinancialYearTab();
        showToast(`Switched active financial year to ${fy}`, "info");
    });
}

// Global window bindings for inline HTML handlers
window.switchTab = switchTab;
window.deleteAccount = deleteAccount;
window.cleanDuplicates = cleanDuplicates;
window.filterTransactionsByAccount = filterTransactionsByAccount;
window.openSettingsModal = openSettingsModal;
window.openSupportModal = openSupportModal;
window.switchFinancialYear = switchFinancialYear;

