// Moneta — Alpine.js app logic

function app() {
  return {
    // ── State ──────────────────────────────────────────────────────────────
    view: 'dashboard',
    dash: null,
    accounts: [],
    transactions: [],
    categories: [],
    recurringRules: [],
    rules: [],
    budgets: [],
    goals: [],
    pots: [],
    potsAccount: '',
    catTab: 'expense',
    selectedParent: null,
    cycleDayInput: '',
    importStatus: '',
    txAutocat: false,
    budgetsWithSpent: [],
    catChart: null,
    csvState: null,
    csvText: '',
    csvHeaders: [],
    csvPreview: [],
    csvConfig: { delimiter: ';', decimal_sep: ',', date_format: '%d.%m.%Y', account_id: '', col_date: '', col_amount: '', col_payee: '', col_purpose: '', col_type: '', default_type: 'auto' },
    csvResult: '',

    txFilter: {
      start: new Date(new Date().setDate(1)).toISOString().slice(0,10),
      end: new Date().toISOString().slice(0,10),
      account_id: '',
      category_id: '',
    },

    modals: { tx: false, account: false, category: false, recurring: false, rule: false, budget: false, goal: false, pot: false },

    txForm: {},
    accForm: {},
    catForm: {},
    recurringForm: {},
    ruleForm: {},
    budgetForm: {},
    goalForm: {},
    potForm: {},

    // ── Init ───────────────────────────────────────────────────────────────
    async init() {
      await Promise.all([
        this.loadAccounts(),
        this.loadCategories(),
        this.loadRecurring(),
        this.loadRules(),
        this.loadBudgets(),
        this.loadGoals(),
        this.loadPots(),
      ]);
      await this.loadDashboard();
      await this.loadCycleSetting();
    },

    // ── Navigation ─────────────────────────────────────────────────────────
    async setView(v) {
      this.view = v;
      if (v === 'dashboard') await this.loadDashboard();
      if (v === 'transactions') await this.loadTransactions();
      if (v === 'budgets') {
        await this.loadBudgetSpent();
        this.$nextTick(() => this.renderCatChart());
      }
      if (v === 'pots') await this.loadPots();
    },

    viewTitle() {
      const titles = {
        dashboard: 'Dashboard',
        transactions: 'Transaktionen',
        accounts: 'Konten',
        categories: 'Kategorien',
        recurring: 'Wiederkehrende Einträge',
        rules: 'Auto-Kategorisierungsregeln',
        budgets: 'Budgets',
        goals: 'Sparziele',
        pots: 'Virtuelle Töpfe',
        export: 'Export & Import',
      };
      return titles[this.view] || '';
    },

    // ── API helpers ─────────────────────────────────────────────────────────
    async api(method, path, body) {
      const opts = { method, headers: { 'Content-Type': 'application/json' } };
      if (body !== undefined) opts.body = JSON.stringify(body);
      const res = await fetch('/api' + path, opts);
      if (!res.ok) {
        const err = await res.text();
        alert('Fehler: ' + err);
        return null;
      }
      return res.json();
    },

    // ── Format helpers ──────────────────────────────────────────────────────
    eur(v) {
      return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(v ?? 0);
    },

    fmtDate(d) {
      if (!d) return '';
      return new Date(d + 'T12:00:00').toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' });
    },

    accTypeLabel(t) {
      return { checking: 'Girokonto', savings: 'Sparkonto', cash: 'Bargeld', credit: 'Kreditkarte' }[t] || t;
    },

    intervalLabel(t) {
      return { monthly: 'Monatlich', quarterly: 'Vierteljährl.', biannual: 'Halbjährl.', annual: 'Jährlich' }[t] || t;
    },

    isOverdue(d) {
      return d && d <= new Date().toISOString().slice(0, 10);
    },

    accountName(id) {
      return this.accounts.find(a => a.id === id)?.name || '–';
    },

    // ── Dashboard ───────────────────────────────────────────────────────────
    async loadDashboard() {
      this.dash = await this.api('GET', '/dashboard');
    },

    // ── Accounts ────────────────────────────────────────────────────────────
    async loadAccounts() {
      this.accounts = await this.api('GET', '/accounts') || [];
    },

    openAccountModal(acc) {
      this.accForm = acc ? { ...acc } : { name: '', type: 'checking', initial_balance: 0, currency: 'EUR', balance_date: '' };
      this.modals.account = true;
    },

    editAccount(acc) { this.openAccountModal(acc); },

    async saveAccount() {
      const { id, ...data } = this.accForm;
      if (!data.name) return alert('Name erforderlich');
      if (id) await this.api('PUT', '/accounts/' + id, data);
      else await this.api('POST', '/accounts', data);
      this.modals.account = false;
      await this.loadAccounts();
      if (this.view === 'dashboard') await this.loadDashboard();
    },

    async deleteAccount(id) {
      if (!confirm('Konto löschen? Alle zugehörigen Transaktionen werden ebenfalls gelöscht.')) return;
      await this.api('DELETE', '/accounts/' + id);
      await this.loadAccounts();
      if (this.view === 'dashboard') await this.loadDashboard();
    },

    // ── Transactions ─────────────────────────────────────────────────────────
    async loadTransactions() {
      const p = new URLSearchParams();
      if (this.txFilter.start) p.set('start', this.txFilter.start);
      if (this.txFilter.end) p.set('end', this.txFilter.end);
      if (this.txFilter.account_id) p.set('account_id', this.txFilter.account_id);
      if (this.txFilter.category_id) p.set('category_id', this.txFilter.category_id);
      this.transactions = await this.api('GET', '/transactions?' + p) || [];
    },

    resetTxFilter() {
      const now = new Date();
      this.txFilter = {
        start: new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10),
        end: now.toISOString().slice(0, 10),
        account_id: '',
        category_id: '',
      };
      this.loadTransactions();
    },

    openTxModal() {
      this.txAutocat = false;
      this.txForm = {
        type: 'expense',
        date: new Date().toISOString().slice(0, 10),
        account_id: this.accounts[0]?.id || '',
        amount: '',
        payee: '',
        purpose: '',
        note: '',
        category_id: '',
        transfer_to_account_id: '',
      };
      this.modals.tx = true;
    },

    editTx(tx) {
      this.txAutocat = false;
      this.txForm = { ...tx };
      this.modals.tx = true;
    },

    async suggestCategory() {
      if (this.txForm.type === 'transfer') return;
      const res = await this.api('GET', `/transactions/suggest-category?payee=${encodeURIComponent(this.txForm.payee)}&purpose=${encodeURIComponent(this.txForm.purpose)}`);
      if (res?.category_id && !this.txForm.category_id) {
        this.txForm.category_id = res.category_id;
        this.txAutocat = true;
      }
    },

    async saveTx() {
      if (!this.txForm.account_id) return alert('Konto wählen');
      if (!this.txForm.amount || this.txForm.amount <= 0) return alert('Betrag erforderlich');
      const { id, ...data } = this.txForm;
      data.amount = parseFloat(data.amount);
      if (id) await this.api('PUT', '/transactions/' + id, data);
      else await this.api('POST', '/transactions', data);
      this.modals.tx = false;
      this.txAutocat = false;
      await this.loadTransactions();
      await this.loadAccounts();
      if (this.view === 'dashboard') await this.loadDashboard();
    },

    async deleteTx(id) {
      if (!confirm('Transaktion löschen?')) return;
      await this.api('DELETE', '/transactions/' + id);
      await this.loadTransactions();
      await this.loadAccounts();
    },

    // ── Categories ────────────────────────────────────────────────────────────
    async loadCategories() {
      this.categories = await this.api('GET', '/categories') || [];
    },

    openCategoryModal(parentId, type) {
      this.catForm = { name: '', parent_id: parentId || null, type: type || this.catTab, icon: '📁' };
      this.modals.category = true;
    },

    editCategory(cat) {
      this.catForm = { ...cat };
      this.modals.category = true;
    },

    async saveCategory() {
      if (!this.catForm.name) return alert('Name erforderlich');
      const { id, ...data } = this.catForm;
      if (id) await this.api('PUT', '/categories/' + id, data);
      else await this.api('POST', '/categories', data);
      this.modals.category = false;
      await this.loadCategories();
    },

    async deleteCategory(id) {
      if (!confirm('Kategorie löschen? Untergruppen werden zu Übergruppen.')) return;
      await this.api('DELETE', '/categories/' + id);
      if (this.selectedParent === id) this.selectedParent = null;
      await this.loadCategories();
    },

    // ── Recurring ──────────────────────────────────────────────────────────────
    async loadRecurring() {
      this.recurringRules = await this.api('GET', '/recurring') || [];
    },

    openRecurringModal() {
      this.recurringForm = {
        name: '', amount: '', type: 'expense', interval_type: 'monthly',
        day_of_month: 1, account_id: this.accounts[0]?.id || '',
        category_id: '', payee: '', purpose: '',
        next_due_date: new Date().toISOString().slice(0, 10),
        active: true,
      };
      this.modals.recurring = true;
    },

    editRecurring(r) {
      this.recurringForm = { ...r };
      this.modals.recurring = true;
    },

    async saveRecurring() {
      if (!this.recurringForm.name) return alert('Name erforderlich');
      if (!this.recurringForm.amount || this.recurringForm.amount <= 0) return alert('Betrag erforderlich');
      if (!this.recurringForm.account_id) return alert('Konto wählen');
      const { id, ...data } = this.recurringForm;
      data.amount = parseFloat(data.amount);
      if (id) await this.api('PUT', '/recurring/' + id, data);
      else await this.api('POST', '/recurring', data);
      this.modals.recurring = false;
      await this.loadRecurring();
    },

    async deleteRecurring(id) {
      if (!confirm('Eintrag löschen?')) return;
      await this.api('DELETE', '/recurring/' + id);
      await this.loadRecurring();
    },

    async bookRecurring(r) {
      if (!confirm(`"${r.name}" jetzt buchen (${this.eur(r.amount)})?`)) return;
      const res = await this.api('POST', '/recurring/' + r.id + '/book');
      if (res) {
        alert(`Gebucht ✓\nNächste Fälligkeit: ${this.fmtDate(res.next_due_date)}`);
        await this.loadRecurring();
        await this.loadAccounts();
        if (this.view === 'dashboard') await this.loadDashboard();
        if (this.view === 'transactions') await this.loadTransactions();
      }
    },

    async loadCycleSetting() {
      const res = await this.api('GET', '/settings/cycle_start_day');
      this.cycleDayInput = res?.value || '';
    },

    async saveCycleDay() {
      if (this.cycleDayInput) {
        await this.api('PUT', '/settings/cycle_start_day', { value: String(this.cycleDayInput) });
      }
      await this.loadDashboard();
    },

    // ── Rules ──────────────────────────────────────────────────────────────────
    async loadRules() {
      this.rules = await this.api('GET', '/rules') || [];
    },

    openRuleModal() {
      this.ruleForm = { pattern: '', field: 'payee', category_id: '', priority: 5 };
      this.modals.rule = true;
    },

    editRule(r) {
      this.ruleForm = { ...r };
      this.modals.rule = true;
    },

    async saveRule() {
      if (!this.ruleForm.pattern) return alert('Muster erforderlich');
      if (!this.ruleForm.category_id) return alert('Kategorie wählen');
      const { id, ...data } = this.ruleForm;
      if (id) await this.api('PUT', '/rules/' + id, data);
      else await this.api('POST', '/rules', data);
      this.modals.rule = false;
      await this.loadRules();
    },

    async deleteRule(id) {
      if (!confirm('Regel löschen?')) return;
      await this.api('DELETE', '/rules/' + id);
      await this.loadRules();
    },

    // ── Budgets ────────────────────────────────────────────────────────────────
    async loadBudgets() {
      this.budgets = await this.api('GET', '/budgets') || [];
    },

    async loadBudgetSpent() {
      await this.loadBudgets();
      // Get current month spending per category
      const now = new Date();
      const start = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10);
      const end = now.toISOString().slice(0, 10);
      const bycat = await this.api('GET', `/analysis/by-category?start=${start}&end=${end}`) || [];
      const spentMap = {};
      bycat.filter(r => r.type === 'expense').forEach(r => {
        spentMap[r.category_id] = r.total;
      });
      // Actually we need spent by category_id — but analysis returns category_name
      // Let's fetch transactions for each budget category (simpler approach)
      this.budgetsWithSpent = await Promise.all(this.budgets.map(async b => {
        const txs = await this.api('GET', `/transactions?category_id=${b.category_id}&start=${start}&end=${end}`);
        const spent = (txs || []).filter(t => t.type === 'expense').reduce((s, t) => s + t.amount, 0);
        return { ...b, spent: Math.round(spent * 100) / 100, pct: b.amount > 0 ? (spent / b.amount) * 100 : 0 };
      }));
    },

    openBudgetModal() {
      this.budgetForm = { category_id: '', amount: '' };
      this.modals.budget = true;
    },

    editBudget(b) {
      this.budgetForm = { ...b };
      this.modals.budget = true;
    },

    async saveBudget() {
      if (!this.budgetForm.category_id) return alert('Kategorie wählen');
      if (!this.budgetForm.amount || this.budgetForm.amount <= 0) return alert('Betrag erforderlich');
      const { id, ...data } = this.budgetForm;
      data.amount = parseFloat(data.amount);
      if (id) await this.api('PUT', '/budgets/' + id, data);
      else await this.api('POST', '/budgets', data);
      this.modals.budget = false;
      await this.loadBudgetSpent();
    },

    async deleteBudget(id) {
      if (!confirm('Budget löschen?')) return;
      await this.api('DELETE', '/budgets/' + id);
      await this.loadBudgetSpent();
    },

    async renderCatChart() {
      const canvas = document.getElementById('catChart');
      if (!canvas) return;
      const now = new Date();
      const start = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10);
      const end = now.toISOString().slice(0, 10);
      const data = await this.api('GET', `/analysis/by-category?start=${start}&end=${end}`) || [];
      const expenses = data.filter(r => r.type === 'expense').slice(0, 8);
      if (this.catChart) this.catChart.destroy();
      const colors = ['#6366f1','#ec4899','#f59e0b','#22c55e','#3b82f6','#14b8a6','#f97316','#a855f7'];
      this.catChart = new Chart(canvas, {
        type: 'doughnut',
        data: {
          labels: expenses.map(r => (r.icon || '') + ' ' + r.name),
          datasets: [{ data: expenses.map(r => r.total), backgroundColor: colors, borderWidth: 0 }],
        },
        options: {
          responsive: true,
          plugins: {
            legend: { position: 'bottom', labels: { color: '#8b8fa8', font: { size: 11 } } },
            tooltip: {
              callbacks: {
                label: ctx => new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(ctx.raw),
              },
            },
          },
        },
      });
    },

    // ── Goals ──────────────────────────────────────────────────────────────────
    async loadGoals() {
      this.goals = await this.api('GET', '/goals') || [];
    },

    openGoalModal() {
      this.goalForm = { name: '', target_amount: '', current_amount: 0, monthly_contribution: 0, target_date: '', color: '#6366f1' };
      this.modals.goal = true;
    },

    editGoal(g) {
      this.goalForm = { ...g };
      this.modals.goal = true;
    },

    async saveGoal() {
      if (!this.goalForm.name) return alert('Name erforderlich');
      if (!this.goalForm.target_amount || this.goalForm.target_amount <= 0) return alert('Zielbetrag erforderlich');
      const { id, ...data } = this.goalForm;
      data.target_amount = parseFloat(data.target_amount);
      data.current_amount = parseFloat(data.current_amount) || 0;
      data.monthly_contribution = parseFloat(data.monthly_contribution) || 0;
      if (!data.target_date) data.target_date = null;
      if (id) await this.api('PUT', '/goals/' + id, data);
      else await this.api('POST', '/goals', data);
      this.modals.goal = false;
      await this.loadGoals();
    },

    async deleteGoal(id) {
      if (!confirm('Sparziel löschen?')) return;
      await this.api('DELETE', '/goals/' + id);
      await this.loadGoals();
    },

    async updateGoalAmount(g) {
      if (!g._newAmount && g._newAmount !== 0) return;
      const data = {
        name: g.name,
        target_amount: g.target_amount,
        current_amount: parseFloat(g._newAmount),
        monthly_contribution: g.monthly_contribution,
        target_date: g.target_date || null,
        color: g.color,
      };
      await this.api('PUT', '/goals/' + g.id, data);
      g._newAmount = '';
      await this.loadGoals();
    },

    // ── Pots ──────────────────────────────────────────────────────────────────────
    async loadPots() {
      const url = this.potsAccount ? `/pots?account_id=${this.potsAccount}` : '/pots';
      this.pots = await this.api('GET', url) || [];
    },

    openPotModal() {
      this.potForm = { account_id: this.potsAccount || (this.accounts[0]?.id || ''), name: '', target_amount: '', color: '#6366f1' };
      this.modals.pot = true;
    },

    editPot(pot) {
      this.potForm = { ...pot };
      this.modals.pot = true;
    },

    async savePot() {
      if (!this.potForm.account_id) return alert('Konto wählen');
      if (!this.potForm.name) return alert('Name erforderlich');
      if (this.potForm.target_amount === '' || this.potForm.target_amount < 0) return alert('Betrag erforderlich');
      const { id, ...data } = this.potForm;
      data.target_amount = parseFloat(data.target_amount) || 0;
      if (id) await this.api('PUT', '/pots/' + id, data);
      else await this.api('POST', '/pots', data);
      this.modals.pot = false;
      await this.loadPots();
      await this.loadAccounts();
    },

    async deletePot(id) {
      if (!confirm('Topf löschen?')) return;
      await this.api('DELETE', '/pots/' + id);
      await this.loadPots();
      await this.loadAccounts();
    },

    // ── CSV Import ────────────────────────────────────────────────────────────────
    parseCSVRaw(text, delimiter) {
      const rows = [];
      for (const line of text.split('\n')) {
        if (!line.trim()) continue;
        // Simple split — handles quoted fields with delimiter inside
        const cells = [];
        let inQuote = false, cur = '';
        for (let i = 0; i < line.length; i++) {
          const ch = line[i];
          if (ch === '"') { inQuote = !inQuote; continue; }
          if (ch === delimiter && !inQuote) { cells.push(cur.trim()); cur = ''; }
          else cur += ch;
        }
        cells.push(cur.trim());
        rows.push(cells);
      }
      return rows;
    },

    loadCsvPreview(event) {
      const file = event.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (e) => {
        this.csvText = e.target.result;
        this.updateCsvPreview();
        this.csvState = 'mapping';
      };
      reader.readAsText(file, 'utf-8');
      event.target.value = '';
    },

    reparsePreview() {
      this.updateCsvPreview();
    },

    updateCsvPreview() {
      const rows = this.parseCSVRaw(this.csvText, this.csvConfig.delimiter);
      if (!rows.length) return;
      this.csvHeaders = rows[0];
      this.csvPreview = rows.slice(1, 6);
      // Auto-detect common column names
      const tryMatch = (candidates) => this.csvHeaders.find(h => candidates.some(c => h.toLowerCase().includes(c))) || '';
      if (!this.csvConfig.col_date)    this.csvConfig.col_date    = tryMatch(['datum', 'date', 'buchungstag', 'valuta']);
      if (!this.csvConfig.col_amount)  this.csvConfig.col_amount  = tryMatch(['betrag', 'amount', 'umsatz', 'wert']);
      if (!this.csvConfig.col_payee)   this.csvConfig.col_payee   = tryMatch(['empfänger', 'auftraggeber', 'name', 'payee', 'beguenstigter']);
      if (!this.csvConfig.col_purpose) this.csvConfig.col_purpose = tryMatch(['verwendungszweck', 'purpose', 'betreff', 'text', 'buchungstext']);
      if (!this.csvConfig.col_type)    this.csvConfig.col_type    = tryMatch(['buchungsart', 'umsatzart', 'art', 'typ', 'soll/haben', 'haben/soll']);
    },

    async importCsv() {
      if (!this.csvConfig.account_id) return alert('Konto wählen');
      if (!this.csvConfig.col_date)   return alert('Datum-Spalte zuordnen');
      if (!this.csvConfig.col_amount) return alert('Betrag-Spalte zuordnen');
      const payload = { csv_text: this.csvText, ...this.csvConfig };
      const res = await this.api('POST', '/import/csv', payload);
      if (res) {
        let msg = `✓ ${res.imported} Transaktionen importiert`;
        if (res.skipped > 0) msg += `, ${res.skipped} übersprungen (Duplikate)`;
        if (res.errors?.length) msg += `\n⚠️ Fehler: ${res.errors.join('; ')}`;
        this.csvResult = msg;
        this.csvState = 'done';
        await this.loadAccounts();
        if (this.view === 'transactions') await this.loadTransactions();
        if (this.view === 'dashboard') await this.loadDashboard();
      }
    },

    // ── Export / Import ─────────────────────────────────────────────────────────
    async exportData() {
      const res = await fetch('/api/export');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `moneta-export-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    },

    async importData(event) {
      const file = event.target.files[0];
      if (!file) return;
      if (!confirm('Alle vorhandenen Daten werden überschrieben. Fortfahren?')) {
        event.target.value = '';
        return;
      }
      const text = await file.text();
      let json;
      try { json = JSON.parse(text); }
      catch { this.importStatus = '❌ Ungültige JSON-Datei'; return; }
      const res = await this.api('POST', '/import', json);
      if (res) {
        this.importStatus = `✓ Import erfolgreich. ${res.imported?.transactions || 0} Transaktionen geladen.`;
        await this.init();
      }
      event.target.value = '';
    },
  };
}
