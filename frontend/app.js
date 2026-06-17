// API Base URL configuration
const API_BASE = window.location.origin.includes('127.0.0.1') || window.location.origin.includes('localhost')
    ? window.location.origin
    : 'http://127.0.0.1:8000';

// Global Application State
const state = {
    activeTab: 'dashboard',
    activeFY: 'FY 2024-25',
    accounts: [],
    transactions: [],
    categories: [],
    insights: [],
    goals: [],
    subscriptions: [],
    netWorth: { net_worth: 0, total_assets: 0, total_liabilities: 0, breakdown: {} },
    healthScore: { score: 100, risk_level: 'LOW', metrics: {}, recommendations: [] },
    forecast: { current_total_balance: 0, expected_month_end_balance: 0, projected_income_remaining: 0, projected_expense_remaining: 0 },
    fyReport: { quarters: {}, summary: {}, tax_savings_deductions_80c_80d: 0 },
    filters: {
        search: '',
        accountId: '',
        type: '',
        startDate: '',
        endDate: '',
        page: 1,
        pageSize: 10
    }
};

// Initializer
document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

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
            fetchFYReport()
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

    // Modal forms submissions
    document.getElementById('add-account-form')?.addEventListener('submit', handleAddAccount);
    document.getElementById('add-tx-form')?.addEventListener('submit', handleAddTransaction);
    document.getElementById('import-statement-form')?.addEventListener('submit', handleImportStatement);
    document.getElementById('add-sub-form')?.addEventListener('submit', handleAddSubscription);
    document.getElementById('add-goal-form')?.addEventListener('submit', handleAddGoal);
    
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
        case 'transactions':
            renderTransactionsTab();
            break;
        case 'financial-year':
            renderFinancialYearTab();
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

async function fetchTransactions() {
    const url = new URL(`${API_BASE}/transactions/`);
    if (state.filters.search) url.searchParams.append('search', state.filters.search);
    if (state.filters.accountId) url.searchParams.append('account_id', state.filters.accountId);
    if (state.filters.type) url.searchParams.append('tx_type', state.filters.type);
    
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
    const accSelectors = ['tx-account', 'tx-dest-account', 'import-account', 'sub-account'];
    accSelectors.forEach(id => {
        const sel = document.getElementById(id);
        if (sel) {
            sel.innerHTML = id === 'tx-dest-account' ? '<option value="">-- No Destination (Non-Transfer) --</option>' : '';
            state.accounts.forEach(acc => {
                sel.innerHTML += `<option value="${acc.id}">${acc.name}</option>`;
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
    const emergencyFactor = state.healthScore.metrics.emergency_fund_score / 100 * 6.0;
    document.getElementById('dash-savings-rate').textContent = `${(state.healthScore.metrics.savings_rate_score / 100 * 30).toFixed(0)}%`;
    document.getElementById('dash-emergency-fund').textContent = `${emergencyFactor.toFixed(1)} mo`;

    // Render Accounts List Grid
    const accountsGrid = document.getElementById('dashboard-accounts-grid');
    if (accountsGrid) {
        accountsGrid.innerHTML = '';
        if (state.accounts.length === 0) {
            accountsGrid.innerHTML = `
                <div class="col-span-12 py-8 text-center text-on-surface-variant text-body-sm">
                    No accounts found. Click the + button in the appbar to add your bank account.
                </div>`;
        } else {
            state.accounts.forEach(acc => {
                let icon = 'account_balance';
                if (acc.account_type === 'WALLET') icon = 'payments';
                if (acc.account_type === 'INVESTMENT') icon = 'show_chart';
                if (acc.account_type === 'CREDIT_CARD') icon = 'credit_card';

                accountsGrid.innerHTML += `
                    <div class="glass-card rounded-lg p-6 group hover:border-primary transition-all duration-300">
                        <div class="flex justify-between items-start mb-4">
                            <div class="w-10 h-10 rounded-full bg-surface-container flex items-center justify-center">
                                <span class="material-symbols-outlined text-primary">${icon}</span>
                            </div>
                            <span class="material-symbols-outlined text-outline group-hover:text-primary transition-colors cursor-pointer" onclick="deleteAccount(${acc.id})">delete</span>
                        </div>
                        <p class="text-body-sm text-on-surface-variant">${acc.name} (${acc.bank_name})</p>
                        <p class="font-title-sm text-primary font-bold mt-1">${fmt.format(acc.current_balance)}</p>
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
                <td colspan="7" class="px-6 py-12 text-center text-body-sm text-on-surface-variant">
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
            else if (tx.category.name === 'Food') colorClasses = 'bg-rose-100 text-rose-700';
            else if (tx.category.name === 'Transport') colorClasses = 'bg-orange-100 text-orange-700';
            else if (tx.category.name === 'Mutual Funds' || tx.category.name === 'Stocks') colorClasses = 'bg-teal-100 text-teal-700';
            
            catBadge = `<span class="px-3 py-1 ${colorClasses} rounded-full font-label-caps text-[10px] tracking-wide uppercase">${tx.category.name}</span>`;
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
                <td class="px-6 py-4 font-data-mono text-data-mono">${txDate}</td>
                <td class="px-6 py-4">
                    <div class="flex items-center gap-2">
                        <span class="font-body-md font-semibold text-primary">${tx.description}</span>
                        ${tx.category_id ? '<span class="material-symbols-outlined text-secondary text-sm" title="AI Categorized">psychology</span>' : ''}
                    </div>
                </td>
                <td class="px-6 py-4 font-data-mono text-data-mono ${amtClass} font-bold">${prefix}${fmt.format(tx.amount)}</td>
                <td class="px-6 py-4">${catBadge}</td>
                <td class="px-6 py-4 font-body-sm text-on-surface-variant">${accountText}</td>
                <td class="px-6 py-4">${intelligenceLabel}</td>
                <td class="px-6 py-4 text-right">
                    <button class="material-symbols-outlined text-outline hover:text-error transition-colors" onclick="deleteTransaction(${tx.id})">delete</button>
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
// FORM SUBMIT HANDLERS & OPERATIONS
// ==========================================

async function handleAddAccount(e) {
    e.preventDefault();
    const name = document.getElementById('acc-name').value;
    const bank_name = document.getElementById('acc-bank').value;
    const account_type = document.getElementById('acc-type').value;
    const opening_balance = parseFloat(document.getElementById('acc-balance').value);
    const currency = 'INR';

    try {
        const res = await fetch(`${API_BASE}/accounts/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, bank_name, account_type, opening_balance, currency })
        });
        
        if (!res.ok) throw new Error("Account creation failed");
        
        showToast("Account successfully registered!", "success");
        closeModal('add-account-modal');
        document.getElementById('add-account-form').reset();
        
        // Refresh & render
        showLoading(true);
        await Promise.all([fetchAccounts(), fetchNetWorth(), fetchHealthScore(), fetchForecast()]);
        renderAll();
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
async function deleteAccount(id) {
    if (!confirm("Are you sure you want to delete this account? All related transactions will be affected.")) return;
    try {
        showLoading(true);
        const res = await fetch(`${API_BASE}/accounts/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error("Account deletion failed");
        showToast("Account removed", "success");
        
        await Promise.all([
            fetchAccounts(),
            fetchTransactions(),
            fetchNetWorth(),
            fetchHealthScore(),
            fetchForecast(),
            fetchFYReport()
        ]);
        renderAll();
    } catch (err) {
        showToast("Error deleting: " + err.message, "error");
    } finally {
        showLoading(false);
    }
}

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

function showLoading(show) {
    const spinner = document.getElementById('loading-indicator');
    if (spinner) {
        if (show) spinner.classList.remove('hidden');
        else spinner.classList.add('hidden');
    }
}

function showToast(msg, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    let color = 'bg-primary text-white';
    if (type === 'success') color = 'bg-secondary text-white';
    if (type === 'error') color = 'bg-error text-white font-bold';
    
    toast.className = `px-6 py-3 rounded-lg shadow-lg ${color} transition-all duration-300 transform translate-y-2 opacity-0 flex items-center gap-2`;
    toast.innerHTML = `
        <span class="material-symbols-outlined text-md">info</span>
        <span class="text-body-sm font-medium">${msg}</span>`;
    
    container.appendChild(toast);
    
    // Animate in
    setTimeout(() => {
        toast.classList.remove('translate-y-2', 'opacity-0');
    }, 10);
    
    // Remove after 3.5s
    setTimeout(() => {
        toast.classList.add('translate-y-2', 'opacity-0');
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 3500);
}
// Trigger manual refresh for insights
window.refreshInsightsList = async function() {
    try {
        showLoading(true);
        const res = await fetch(`${API_BASE}/insights/refresh`, { method: 'POST' });
        if (!res.ok) throw new Error("Heuristic execution failed");
        state.insights = await res.json();
        showToast("Intelligence parameters scanned. Insights up to date.", "success");
        renderAll();
    } catch (err) {
        showToast("Refresh error: " + err.message, "error");
    } finally {
        showLoading(false);
    }
};
