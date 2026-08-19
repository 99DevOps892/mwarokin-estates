/**
 * Mwarokin Estates ΓÇö Supabase Client (SHARED)
 * ===========================================
 * Initialized exactly ONCE. Every page includes this file first,
 * so all other modules share a single client instance.
 *
 * Include order in every HTML page:
 *   <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
 *   <script src="js/config.js"></script>
 *   <script src="js/supabase-client.js"></script>
 */
(function () {
  if (typeof window.supabase === 'undefined') {
    console.error('[supabase-client] supabase-js SDK not loaded. Add the CDN script before this file.');
    return;
  }

  const cfg = window.MWAROKIN_CONFIG || {};
  if (!cfg.supabaseUrl || !cfg.supabaseAnonKey || cfg.supabaseAnonKey.indexOf('YOUR_') === 0) {
    console.warn('[supabase-client] Supabase credentials are placeholders. Open js/config.js and set your anon public key.');
  }

  let client = null;
  try {
    client = window.supabase.createClient(cfg.supabaseUrl, cfg.supabaseAnonKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true
      },
      realtime: {
        params: { eventsPerSecond: 2 }
      }
    });
  } catch (err) {
    console.error('[supabase-client] Failed to create client:', err);
  }

  // Expose globally for all page modules
  window.supabaseClient = client;
  window.supabase = client;
  window.MWAROKIN = window.MWAROKIN || {};
  window.MWAROKIN.supabase = client;

  // ---------- Shared helpers (used across modules) ----------

  /** Escape HTML to prevent XSS when injecting user/data into the DOM. */
  window.esc = function (value) {
    if (value === null || value === undefined) return '';
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  };

  /** Format currency numbers (KES default). */
  window.fmtMoney = function (amount, currency) {
    const ccy = currency || (window.MWAROKIN_CURRENCY ? window.MWAROKIN_CURRENCY.current : 'KES');
    const symbols = { KES: 'KSh ', USD: '$', EUR: 'Γé¼', GBP: '┬ú' };
    const sym = symbols[ccy] || ccy + ' ';
    const n = Number(amount) || 0;
    return sym + n.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 });
  };

  /** Convert local base path to absolute-safe path for GitHub Pages. */
  window.appPath = function (file) {
    const base = (window.MWAROKIN_CONFIG || {}).basePath || '/';
    return base.replace(/\/$/, '') + '/' + file;
  };

  /** Simple toast notification. */
  window.toast = function (message, type) {
    type = type || 'info';
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }
    const el = document.createElement('div');
    el.className = 'toast toast-' + type;
    el.textContent = message;
    container.appendChild(el);
    setTimeout(function () { el.classList.add('toast-hide'); setTimeout(function () { el.remove(); }, 400); }, 4000);
  };
})();
