/**
 * SpendPulse Personal Finance Analyzer - Frontend Application Logic
 * Currency: INR (₹) | Locale: en-IN
 */

let state = {
  transactions: [],
  analytics: null,
  columns: [],
  currentFile: null,
  currentFileContent: null, // Store raw file content for re-upload
  filtered: [],
  currentPage: 1,
  pageSize: 15,
  monthlyChart: null,
  categoryChart: null
};

const ALL_CATEGORIES = [
  "Income", "Housing & Rent", "Groceries", "Dining & Cafes",
  "Utilities & Bills", "Transportation", "Entertainment & Subscriptions",
  "Shopping & Retail", "Healthcare & Fitness", "Investments & Finance",
  "Bank Fees & Charges", "Uncategorized"
];

// ─── Currency Formatter ──────────────────────────────────────
function fmt(num) {
  return '₹' + Math.abs(num).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// ─── Initialization ──────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();
  setupDropZone();
  loadSampleDataset('checking_csv');
});

// ─── Drag & Drop Setup ──────────────────────────────────────
function setupDropZone() {
  const dropZone = document.getElementById('dropZone');
  if (!dropZone) return;

  ['dragenter', 'dragover'].forEach(name => {
    dropZone.addEventListener(name, (e) => {
      e.preventDefault();
      dropZone.classList.add('border-indigo-500', 'bg-indigo-950/20');
    });
  });

  ['dragleave', 'drop'].forEach(name => {
    dropZone.addEventListener(name, (e) => {
      e.preventDefault();
      dropZone.classList.remove('border-indigo-500', 'bg-indigo-950/20');
    });
  });

  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    const files = e.dataTransfer ? e.dataTransfer.files : null;
    if (files && files.length > 0) {
      readAndUploadFile(files[0]);
    }
  });
}

// ─── File Picker ─────────────────────────────────────────────
function triggerFilePicker() {
  const fi = document.getElementById('fileInput') || document.getElementById('dropFileInput');
  if (fi) {
    fi.value = '';
    fi.click();
  }
}

function handleFileSelect(event) {
  const file = event.target.files && event.target.files[0];
  if (file) {
    readAndUploadFile(file);
  }
  // reset input so the same file can be re-selected if desired
  event.target.value = '';
}

// ─── Core: Read file as text, then inspect → upload ─────────
function readAndUploadFile(file) {
  if (!file) return;
  state.currentFile = file;

  const dt = document.getElementById('dropTitle');
  const ds = document.getElementById('dropSubtitle');
  if (dt) dt.textContent = '📄 ' + file.name;
  if (ds) ds.textContent = 'Analyzing ' + Math.round(file.size / 1024) + ' KB statement...';

  showLoading(true, 'Reading statement: ' + file.name);

  const reader = new FileReader();
  reader.onload = function(e) {
    state.currentFileContent = e.target.result;
    inspectAndUpload(file.name, state.currentFileContent);
  };
  reader.onerror = function() {
    showLoading(false);
    alert('Could not read the selected file. Please verify file permissions.');
  };
  reader.readAsText(file);
}

async function inspectAndUpload(filename, content) {
  const ext = filename.toLowerCase().split('.').pop();
  const mimeType = ext === 'json' ? 'application/json' : 'text/csv';

  try {
    const inspectBlob = new Blob([content], { type: mimeType });
    const inspectForm = new FormData();
    inspectForm.append('file', inspectBlob, filename);

    const inspectRes = await fetch('/api/inspect', { method: 'POST', body: inspectForm });
    if (!inspectRes.ok) {
      const err = await inspectRes.json().catch(() => ({}));
      console.warn('Server inspect error, falling back to client-side parser:', err);
      parseAndAnalyzeLocally(filename, content);
      return;
    }

    const inspectData = await inspectRes.json();
    state.columns = inspectData.columns;

    const mapping = inspectData.suggested_mapping;
    const hasDate = !!mapping.date_col;
    const hasAmount = !!mapping.amount_col || (!!mapping.debit_col && !!mapping.credit_col);

    if (hasDate && hasAmount) {
      await doUpload(filename, content, mimeType, null);
    } else {
      showLoading(false);
      populateMapperModal(inspectData);
      openMapperModal();
    }
  } catch (error) {
    console.warn('Backend unavailable, using instant client-side analysis:', error);
    parseAndAnalyzeLocally(filename, content);
  }
}

async function doUpload(filename, content, mimeType, mapping) {
  showLoading(true, 'Running financial analysis...');
  const blob = new Blob([content], { type: mimeType });
  const formData = new FormData();
  formData.append('file', blob, filename);
  if (mapping) {
    formData.append('column_mapping', JSON.stringify(mapping));
  }
  formData.append('account_name', filename.replace(/\.[^/.]+$/, ""));

  try {
    const res = await fetch('/api/upload', { method: 'POST', body: formData });
    showLoading(false);
    if (!res.ok) {
      console.warn('Server upload failed, falling back to local analysis');
      parseAndAnalyzeLocally(filename, content);
      return;
    }
    const data = await res.json();
    applyAnalysisResult(data);
  } catch (err) {
    console.warn('Network issue during upload, falling back to local analysis:', err);
    parseAndAnalyzeLocally(filename, content);
  }
}

// ─── Client-Side Analysis Engine Fallback ────────────────────
function parseAndAnalyzeLocally(filename, content) {
  showLoading(false);
  try {
    let txs = [];
    if (filename.toLowerCase().endsWith('.json')) {
      const raw = JSON.parse(content);
      const list = Array.isArray(raw) ? raw : (raw.transactions || raw.data || raw.items || []);
      txs = list.map((item, i) => {
        const amt = parseFloat(item.amount || item.val || 0);
        return {
          id: 'tx_c_' + i,
          date: item.date || item.trans_date || new Date().toISOString().slice(0, 10),
          description: item.description || item.narration || item.merchant || 'Transaction',
          amount: amt,
          type: amt >= 0 ? 'income' : 'expense',
          category: item.category || categorizeMerchant(item.description || item.narration || ''),
          account: 'Imported Statement'
        };
      });
    } else {
      // Smart CSV parser
      const lines = content.replace(/\r/g, '').split('\n').filter(l => l.trim().length > 0);
      let headerIdx = 0;
      let delim = ',';
      
      // Look for candidate header line
      for (let i = 0; i < Math.min(25, lines.length); i++) {
        const line = lines[i].toLowerCase();
        if (line.includes('date') || line.includes('narration') || line.includes('amount') || line.includes('debit') || line.includes('withdrawal')) {
          headerIdx = i;
          if (line.includes('\t')) delim = '\t';
          else if (line.includes(';')) delim = ';';
          break;
        }
      }

      const rawHeaders = lines[headerIdx].split(delim).map(h => h.trim().replace(/^"|"$/g, ''));
      const hLower = rawHeaders.map(h => h.toLowerCase());

      const dateCol = hLower.findIndex(h => h.includes('date') && !h.includes('value'));
      const descCol = hLower.findIndex(h => h.includes('desc') || h.includes('narrat') || h.includes('particular') || h.includes('merchant') || h.includes('detail'));
      const debitCol = hLower.findIndex(h => h.includes('debit') || h.includes('withdraw') || h.includes('dr'));
      const creditCol = hLower.findIndex(h => h.includes('credit') || h.includes('deposit') || h.includes('cr'));
      const amtCol = hLower.findIndex(h => h.includes('amount') || h.includes('amt'));

      for (let i = headerIdx + 1; i < lines.length; i++) {
        const parts = lines[i].split(delim).map(p => p.trim().replace(/^"|"$/g, ''));
        if (parts.length < 2) continue;

        const rawDate = dateCol >= 0 ? parts[dateCol] : parts[0];
        const rawDesc = descCol >= 0 ? parts[descCol] : parts[1] || 'Transaction';

        let num = 0;
        let isIncome = false;

        if (debitCol >= 0 || creditCol >= 0) {
          const deb = debitCol >= 0 ? parseFloat(parts[debitCol].replace(/[^\d.-]/g, '')) : NaN;
          const cred = creditCol >= 0 ? parseFloat(parts[creditCol].replace(/[^\d.-]/g, '')) : NaN;
          if (!isNaN(deb) && deb > 0) {
            num = deb;
            isIncome = false;
          } else if (!isNaN(cred) && cred > 0) {
            num = cred;
            isIncome = true;
          }
        } else if (amtCol >= 0) {
          const parsedAmt = parseFloat(parts[amtCol].replace(/[^\d.-]/g, ''));
          if (!isNaN(parsedAmt)) {
            num = Math.abs(parsedAmt);
            isIncome = parsedAmt > 0;
          }
        }

        if (num > 0) {
          txs.push({
            id: 'tx_c_' + i,
            date: rawDate || new Date().toISOString().slice(0, 10),
            description: rawDesc,
            amount: isIncome ? num : -num,
            type: isIncome ? 'income' : 'expense',
            category: categorizeMerchant(rawDesc),
            account: 'Imported Statement'
          });
        }
      }
    }

    if (txs.length === 0) {
      alert('No valid transactions found in ' + filename + '. Please check the file format.');
      return;
    }

    // Compute Analytics
    let totalIncome = 0;
    let totalExpenses = 0;
    const catMap = {};
    const monthMap = {};

    txs.forEach(t => {
      if (t.type === 'income') {
        totalIncome += t.amount;
      } else {
        totalExpenses += Math.abs(t.amount);
        catMap[t.category] = (catMap[t.category] || 0) + Math.abs(t.amount);
      }

      const m = (t.date || '').slice(0, 7) || 'Current';
      if (!monthMap[m]) monthMap[m] = { month: m, income: 0, expenses: 0, net: 0 };
      if (t.type === 'income') monthMap[m].income += t.amount;
      else monthMap[m].expenses += Math.abs(t.amount);
      monthMap[m].net = monthMap[m].income - monthMap[m].expenses;
    });

    const netFlow = totalIncome - totalExpenses;
    const savingsRate = totalIncome > 0 ? ((netFlow / totalIncome) * 100) : 0;

    const categoryBreakdown = Object.keys(catMap).map(k => ({
      category: k,
      total_amount: catMap[k],
      percentage: totalExpenses > 0 ? (catMap[k] / totalExpenses) * 100 : 0,
      transaction_count: 1
    }));

    const monthlyTrends = Object.values(monthMap).sort((a,b) => a.month.localeCompare(b.month));

    const result = {
      filename: filename,
      transactions: txs,
      analytics: {
        summary: {
          total_income: totalIncome,
          total_expense: totalExpenses,
          total_expenses: totalExpenses,
          net_cash_flow: netFlow,
          savings_rate: savingsRate,
          savings_rate_pct: savingsRate,
          total_transactions: txs.length,
          transaction_count: txs.length,
          date_range: { start: txs[0].date, end: txs[txs.length - 1].date }
        },
        category_breakdown: categoryBreakdown,
        monthly_trends: monthlyTrends,
        recurring_subscriptions: [],
        budgets: []
      }
    };

    applyAnalysisResult(result);
  } catch (err) {
    console.error('Local analysis error:', err);
    alert('Failed to parse statement: ' + err.message);
  }
}

function categorizeMerchant(desc) {
  const d = (desc || '').toLowerCase();
  if (d.includes('swiggy') || d.includes('zomato') || d.includes('restaurant') || d.includes('cafe') || d.includes('mcdonald') || d.includes('starbucks')) return 'Dining & Cafes';
  if (d.includes('blinkit') || d.includes('zepto') || d.includes('instamart') || d.includes('bigbasket') || d.includes('supermarket') || d.includes('grocery')) return 'Groceries';
  if (d.includes('uber') || d.includes('ola') || d.includes('rapido') || d.includes('metro') || d.includes('fuel') || d.includes('petrol')) return 'Transportation';
  if (d.includes('amazon') || d.includes('flipkart') || d.includes('myntra') || d.includes('retail') || d.includes('shopping')) return 'Shopping & Retail';
  if (d.includes('netflix') || d.includes('prime') || d.includes('spotify') || d.includes('hotstar') || d.includes('youtube')) return 'Entertainment & Subscriptions';
  if (d.includes('electricity') || d.includes('bescom') || d.includes('water') || d.includes('airtel') || d.includes('jio') || d.includes('broadband')) return 'Utilities & Bills';
  if (d.includes('rent') || d.includes('housing') || d.includes('maintenance')) return 'Housing & Rent';
  if (d.includes('salary') || d.includes('dividend') || d.includes('interest') || d.includes('credit')) return 'Income';
  if (d.includes('zerodha') || d.includes('groww') || d.includes('sip') || d.includes('mutual fund')) return 'Investments & Finance';
  return 'Uncategorized';
}

// ─── Loading Spinner ─────────────────────────────────────────
function showLoading(visible, message) {
  const overlay = document.getElementById('loadingOverlay');
  const txt = document.getElementById('loadingText');
  if (txt && message) {
    txt.textContent = message;
  }
  if (overlay) {
    overlay.classList.toggle('hidden', !visible);
  }
}

// ─── Load Sample Datasets ────────────────────────────────────
async function loadSampleDataset(sampleType) {
  showLoading(true);
  try {
    const res = await fetch('/api/sample/' + sampleType);
    showLoading(false);
    if (!res.ok) {
      alert('Failed to load sample dataset.');
      return;
    }
    const data = await res.json();
    state.currentFile = { name: data.filename };
    state.currentFileContent = null;
    applyAnalysisResult(data);
  } catch (err) {
    showLoading(false);
    console.error(err);
    alert('Could not fetch sample dataset.');
  }
}

// ─── Apply Analysis Result to UI ─────────────────────────────
function applyAnalysisResult(data) {
  state.transactions = data.transactions;
  state.analytics = data.analytics;
  state.columns = data.columns || [];

  // Status Bar
  document.getElementById('statusBar').classList.remove('hidden');
  document.getElementById('loadedFileName').textContent = data.filename || 'Statement';
  document.getElementById('statusRowCount').textContent = state.transactions.length.toLocaleString('en-IN');

  const dr = state.analytics.summary.date_range;
  if (dr && dr.start && dr.end) {
    document.getElementById('statusDateRange').textContent = 'Period: ' + dr.start + ' to ' + dr.end;
  }

  renderKPIs(state.analytics.summary, state.analytics.recurring_subscriptions);
  renderMonthlyChart(state.analytics.monthly_trends);
  renderCategoryChart(state.analytics.category_breakdown);
  renderRecurringSubscriptions(state.analytics.recurring_subscriptions);
  renderBudgetHealth(state.analytics.budgets);
  populateCategoryFilter();
  applyTableFilters();
  lucide.createIcons();
}

// ─── KPI Cards ───────────────────────────────────────────────
function renderKPIs(summary, subscriptions) {
  document.getElementById('kpiIncome').textContent = fmt(summary.total_income);
  document.getElementById('kpiExpense').textContent = fmt(summary.total_expense);

  const netEl = document.getElementById('kpiNet');
  netEl.textContent = (summary.net_cash_flow < 0 ? '-' : '+') + fmt(summary.net_cash_flow);
  netEl.className = summary.net_cash_flow >= 0
    ? 'text-xl sm:text-2xl font-bold text-emerald-400'
    : 'text-xl sm:text-2xl font-bold text-rose-400';

  const savingsEl = document.getElementById('kpiSavings');
  savingsEl.textContent = summary.savings_rate.toFixed(1) + '%';
  savingsEl.className = summary.savings_rate >= 20
    ? 'text-xl sm:text-2xl font-bold text-emerald-400'
    : 'text-xl sm:text-2xl font-bold text-violet-400';

  document.getElementById('kpiRecurring').textContent = subscriptions.length;
  const totalSubAnnual = subscriptions.reduce((acc, s) => acc + s.estimated_annual_cost, 0);
  document.getElementById('kpiRecurringSubtitle').textContent = '₹' + Math.round(totalSubAnnual / 12).toLocaleString('en-IN') + '/mo estimated';
}

// ─── Monthly Cash Flow Chart ─────────────────────────────────
function renderMonthlyChart(trends) {
  const ctx = document.getElementById('monthlyChart').getContext('2d');
  if (state.monthlyChart) state.monthlyChart.destroy();

  state.monthlyChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: trends.map(t => t.month),
      datasets: [
        {
          label: 'Income',
          data: trends.map(t => t.income),
          backgroundColor: 'rgba(52, 211, 153, 0.75)',
          borderColor: '#10b981', borderWidth: 1, borderRadius: 4
        },
        {
          label: 'Expenses',
          data: trends.map(t => t.expense),
          backgroundColor: 'rgba(244, 63, 94, 0.75)',
          borderColor: '#f43f5e', borderWidth: 1, borderRadius: 4
        },
        {
          type: 'line', label: 'Net Cash Flow',
          data: trends.map(t => t.net),
          borderColor: '#818cf8', backgroundColor: 'rgba(129, 140, 248, 0.1)',
          borderWidth: 2, pointBackgroundColor: '#6366f1', pointRadius: 4, tension: 0.3
        }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#94a3b8', font: { size: 11 } } },
        tooltip: { callbacks: { label: (item) => ' ' + item.dataset.label + ': ₹' + item.raw.toLocaleString('en-IN') } }
      },
      scales: {
        x: { grid: { color: 'rgba(51,65,85,0.3)' }, ticks: { color: '#94a3b8', font: { size: 11 } } },
        y: { grid: { color: 'rgba(51,65,85,0.3)' }, ticks: { color: '#94a3b8', font: { size: 11 }, callback: (v) => '₹' + v.toLocaleString('en-IN') } }
      }
    }
  });
}

// ─── Category Doughnut Chart ─────────────────────────────────
function renderCategoryChart(categories) {
  const ctx = document.getElementById('categoryChart').getContext('2d');
  if (state.categoryChart) state.categoryChart.destroy();

  const topCats = categories.slice(0, 7);
  const colors = ['#6366f1','#ec4899','#10b981','#f59e0b','#06b6d4','#8b5cf6','#64748b','#f43f5e'];

  state.categoryChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: topCats.map(c => c.category),
      datasets: [{ data: topCats.map(c => c.total), backgroundColor: colors, borderColor: '#0f172a', borderWidth: 2 }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { position: 'right', labels: { color: '#cbd5e1', font: { size: 10 }, boxWidth: 12 } },
        tooltip: { callbacks: { label: (item) => ' ' + item.label + ': ₹' + item.raw.toLocaleString('en-IN') } }
      },
      cutout: '65%'
    }
  });
}

// ─── Recurring Subscriptions ─────────────────────────────────
function renderRecurringSubscriptions(subscriptions) {
  const container = document.getElementById('recurringList');
  if (!subscriptions || subscriptions.length === 0) {
    container.innerHTML = '<div class="text-center py-6 text-xs text-slate-500">No recurring subscriptions detected.</div>';
    return;
  }
  container.innerHTML = subscriptions.map(sub => `
    <div class="flex items-center justify-between p-2.5 rounded-lg bg-slate-800/50 border border-slate-700/60 hover:bg-slate-800 transition">
      <div class="flex items-center gap-2.5">
        <div class="w-8 h-8 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center font-bold text-xs">${sub.merchant.charAt(0).toUpperCase()}</div>
        <div>
          <h4 class="text-xs font-semibold text-white">${sub.merchant}</h4>
          <span class="text-[10px] text-slate-400">${sub.category} &bull; ${sub.frequency}</span>
        </div>
      </div>
      <div class="text-right">
        <div class="text-xs font-bold text-amber-400">₹${sub.average_amount.toLocaleString('en-IN', {minimumFractionDigits:2, maximumFractionDigits:2})}</div>
        <div class="text-[10px] text-slate-500">₹${Math.round(sub.estimated_annual_cost).toLocaleString('en-IN')}/yr</div>
      </div>
    </div>
  `).join('');
}

// ─── Budget Health ───────────────────────────────────────────
function renderBudgetHealth(budgets) {
  const container = document.getElementById('budgetList');
  if (!budgets || budgets.length === 0) {
    container.innerHTML = '<div class="text-center py-6 text-xs text-slate-500">No budget metrics available.</div>';
    return;
  }
  container.innerHTML = budgets.map(b => {
    let barColor = 'bg-indigo-500', badgeClass = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20', badgeText = 'Safe';
    if (b.status === 'exceeded') { barColor = 'bg-rose-500'; badgeClass = 'bg-rose-500/10 text-rose-400 border-rose-500/20'; badgeText = 'Exceeded'; }
    else if (b.status === 'warning') { barColor = 'bg-amber-500'; badgeClass = 'bg-amber-500/10 text-amber-400 border-amber-500/20'; badgeText = 'Pacing High'; }
    return `
      <div class="space-y-1">
        <div class="flex items-center justify-between text-xs">
          <span class="font-medium text-slate-200">${b.category}</span>
          <div class="flex items-center gap-2">
            <span class="text-slate-400">₹${b.spent.toLocaleString('en-IN')} / ₹${b.budget.toLocaleString('en-IN')}</span>
            <span class="text-[10px] px-1.5 py-0.5 rounded border ${badgeClass} font-semibold">${badgeText}</span>
          </div>
        </div>
        <div class="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
          <div class="${barColor} h-1.5 rounded-full transition-all duration-300" style="width: ${Math.min(100, b.percentage)}%"></div>
        </div>
      </div>
    `;
  }).join('');
}

// ─── Category Filter Dropdown ────────────────────────────────
function populateCategoryFilter() {
  const select = document.getElementById('txCategoryFilter');
  const cats = Array.from(new Set(state.transactions.map(t => t.category))).sort();
  select.innerHTML = '<option value="ALL">All Categories</option>' + cats.map(c => '<option value="' + c + '">' + c + '</option>').join('');
}

// ─── Table Filters & Pagination ──────────────────────────────
function applyTableFilters() {
  const query = document.getElementById('txSearchInput').value.toLowerCase().trim();
  const catFilter = document.getElementById('txCategoryFilter').value;
  const typeFilter = document.getElementById('txTypeFilter').value;

  state.filtered = state.transactions.filter(tx => {
    const matchQ = !query || tx.description.toLowerCase().includes(query) || (tx.merchant && tx.merchant.toLowerCase().includes(query));
    const matchC = catFilter === 'ALL' || tx.category === catFilter;
    const matchT = typeFilter === 'ALL' || tx.type === typeFilter;
    return matchQ && matchC && matchT;
  });
  state.currentPage = 1;
  renderTable();
}

function renderTable() {
  const tbody = document.getElementById('transactionsTableBody');
  const total = state.filtered.length;
  if (total === 0) {
    tbody.innerHTML = '<tr><td colspan="5" class="py-8 text-center text-slate-500 font-sans">No matching transactions found.</td></tr>';
    document.getElementById('paginationInfo').textContent = 'Showing 0 of 0 transactions';
    document.getElementById('prevPageBtn').disabled = true;
    document.getElementById('nextPageBtn').disabled = true;
    return;
  }
  const start = (state.currentPage - 1) * state.pageSize;
  const end = Math.min(start + state.pageSize, total);
  const items = state.filtered.slice(start, end);

  tbody.innerHTML = items.map(tx => {
    const isInc = tx.amount > 0;
    const cls = isInc ? 'text-emerald-400' : 'text-slate-200';
    const sign = isInc ? '+' : '';
    return `
      <tr class="hover:bg-slate-800/40 transition">
        <td class="py-2 px-4 whitespace-nowrap text-slate-400">${tx.date}</td>
        <td class="py-2 px-4 font-sans font-medium text-white">${tx.merchant || tx.description}</td>
        <td class="py-2 px-4 text-slate-500 hidden md:table-cell truncate max-w-xs font-sans">${tx.description}</td>
        <td class="py-2 px-4 font-sans">
          <select onchange="updateTransactionCategory('${tx.id}', this.value)"
            class="text-[11px] py-0.5 px-2 rounded-md bg-slate-800 border border-slate-700 text-slate-300 focus:outline-none focus:border-indigo-500 cursor-pointer">
            ${ALL_CATEGORIES.map(cat => '<option value="' + cat + '"' + (cat === tx.category ? ' selected' : '') + '>' + cat + '</option>').join('')}
          </select>
        </td>
        <td class="py-2 px-4 text-right font-semibold ${cls}">${sign}₹${Math.abs(tx.amount).toLocaleString('en-IN', {minimumFractionDigits:2, maximumFractionDigits:2})}</td>
      </tr>
    `;
  }).join('');

  document.getElementById('paginationInfo').textContent = 'Showing ' + (start+1) + ' to ' + end + ' of ' + total + ' transactions';
  document.getElementById('currentPageNum').textContent = 'Page ' + state.currentPage + ' of ' + Math.ceil(total / state.pageSize);
  document.getElementById('prevPageBtn').disabled = state.currentPage === 1;
  document.getElementById('nextPageBtn').disabled = end >= total;
}

function changePage(delta) { state.currentPage += delta; renderTable(); }

// ─── Update Category Live ────────────────────────────────────
async function updateTransactionCategory(txId, newCategory) {
  try {
    const res = await fetch('/api/update-transaction-category', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ transactions: state.transactions, transaction_id: txId, new_category: newCategory })
    });
    if (res.ok) {
      const data = await res.json();
      state.transactions = data.transactions;
      state.analytics = data.analytics;
      renderKPIs(state.analytics.summary, state.analytics.recurring_subscriptions);
      renderCategoryChart(state.analytics.category_breakdown);
      renderBudgetHealth(state.analytics.budgets);
      populateCategoryFilter();
      applyTableFilters();
    }
  } catch (err) { console.error('Failed to update category', err); }
}

// ─── Export CSV ──────────────────────────────────────────────
async function exportCleanCSV() {
  if (!state.transactions || state.transactions.length === 0) { alert('No transactions to export.'); return; }
  try {
    const res = await fetch('/api/export/csv', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ transactions: state.transactions })
    });
    if (!res.ok) throw new Error('Export failed');
    const blob = await res.blob();
    const a = document.createElement('a');
    a.href = window.URL.createObjectURL(blob);
    a.download = 'spendpulse_cleaned_' + new Date().toISOString().slice(0, 10) + '.csv';
    document.body.appendChild(a);
    a.click();
    a.remove();
  } catch (err) { alert('Failed to generate export file.'); }
}

// ─── Column Mapping Modal ────────────────────────────────────
function openMapperModal() { document.getElementById('mapperModal').classList.remove('hidden'); }
function closeMapperModal() { document.getElementById('mapperModal').classList.add('hidden'); }

function populateMapperModal(inspectData) {
  document.getElementById('modalFileName').textContent = inspectData.filename;
  const cols = inspectData.columns;
  const sug = inspectData.suggested_mapping || {};
  const makeOpts = (sel) => '<option value="">-- None --</option>' + cols.map(c => '<option value="' + c + '"' + (c === sel ? ' selected' : '') + '>' + c + '</option>').join('');
  document.getElementById('mapDateCol').innerHTML = makeOpts(sug.date_col);
  document.getElementById('mapDescCol').innerHTML = makeOpts(sug.desc_col);
  document.getElementById('mapAmountCol').innerHTML = makeOpts(sug.amount_col);
  document.getElementById('mapCategoryCol').innerHTML = makeOpts(sug.category_col);
  document.getElementById('mapDebitCol').innerHTML = makeOpts(sug.debit_col);
  document.getElementById('mapCreditCol').innerHTML = makeOpts(sug.credit_col);
}

function applyCustomMappingAndAnalyze() {
  const m = {
    date_col: document.getElementById('mapDateCol').value || null,
    desc_col: document.getElementById('mapDescCol').value || null,
    amount_col: document.getElementById('mapAmountCol').value || null,
    category_col: document.getElementById('mapCategoryCol').value || null,
    debit_col: document.getElementById('mapDebitCol').value || null,
    credit_col: document.getElementById('mapCreditCol').value || null,
    invert_amount: document.getElementById('mapInvertAmount').checked
  };
  if (!m.date_col) { alert('Please select a Date column.'); return; }
  if (!m.desc_col) { alert('Please select a Description column.'); return; }
  if (!m.amount_col && !m.debit_col && !m.credit_col) { alert('Please select an Amount column or Debit/Credit columns.'); return; }
  closeMapperModal();
  if (state.currentFile && state.currentFileContent) {
    const ext = state.currentFile.name.toLowerCase().split('.').pop();
    const mimeType = ext === 'json' ? 'application/json' : 'text/csv';
    doUpload(state.currentFile.name, state.currentFileContent, mimeType, m);
  }
}
