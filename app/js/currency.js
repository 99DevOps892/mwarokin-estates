/**
 * Mwarokin Estates — Currency Manager
 * Multi-currency display using rates from the Supabase `exchange_rates` table.
 * KES is the system base currency.
 */
(function () {
  const cfg = window.MWAROKIN_CONFIG;
  let current = cfg.defaultCurrency || 'KES';
  let rates = { KES: 1 };
  let listeners = [];

  const symbols = { KES: 'KSh ', USD: '$', EUR: '€', GBP: '£' };

  function detectInitial() {
    try {
      const saved = localStorage.getItem('mw_currency');
      if (saved) return saved;
    } catch (e) {}
    return cfg.defaultCurrency || 'KES';
  }

  async function loadRates() {
    if (typeof window.supabaseClient === 'undefined') return;
    try {
      const { data } = await window.supabaseClient
        .from('exchange_rates')
        .select('target_currency, rate')
        .eq('base_currency', 'KES');
      if (data) {
        const next = { KES: 1 };
        data.forEach(function (r) { next[r.target_currency] = Number(r.rate) || 1; });
        rates = next;
      }
    } catch (e) {}
  }

  function populateSelectors() {
    (cfg.supportedCurrencies || []).forEach(function (code) {
      const sel = document.getElementById('currency-select');
      if (sel) {
        const opt = document.createElement('option');
        opt.value = code;
        opt.textContent = code;
        sel.appendChild(opt);
      }
    });
  }

  function emit() {
    listeners.forEach(function (fn) { try { fn(current); } catch (e) {} });
    document.dispatchEvent(new CustomEvent('mw:currencychange', { detail: { currency: current } }));
  }

  window.MWAROKIN_CURRENCY = {
    current: 'KES',
    get current() { return current; },
    rate: function (code) { return rates[code] || 1; },
    convert: function (amount, from, to) {
      if (!from || from === 'KES') from = 'KES';
      const toRate = rates[to] || 1;
      const fromRate = rates[from] || 1;
      return (Number(amount) || 0) * (toRate / fromRate);
    },
    format: function (amount, code) {
      const ccy = code || current;
      const sym = symbols[ccy] || ccy + ' ';
      const n = Number(amount) || 0;
      return sym + n.toLocaleString(undefined, { maximumFractionDigits: 2 });
    },
    async setCurrency(code) {
      if (code === current) return;
      current = code;
      try { localStorage.setItem('mw_currency', code); } catch (e) {}
      try {
        const { data: { user } } = await window.supabaseClient.auth.getUser();
        if (user) {
          await window.supabaseClient.from('profiles')
            .update({ preferred_currency: code }).eq('id', user.id);
        }
      } catch (e) {}
      emit();
    },
    onChange: function (fn) { listeners.push(fn); },
    async init() {
      populateSelectors();
      current = detectInitial();
      await loadRates();
      emit();

      const sel = document.getElementById('currency-select');
      if (sel) {
        sel.value = current;
        sel.addEventListener('change', function () {
          window.MWAROKIN_CURRENCY.setCurrency(sel.value);
        });
      }
    }
  };
})();