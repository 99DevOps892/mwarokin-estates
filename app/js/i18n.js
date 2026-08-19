/**
 * Mwarokin Estates — i18n Manager
 * Multi-language UI. Reads translations from the Supabase `translations` table,
 * falls back to a small built-in dictionary, persists per-user preference.
 */
(function () {
  const cfg = window.MWAROKIN_CONFIG;
  const fallback = {
    en: {
      'common.login': 'Login', 'common.register': 'Register', 'common.logout': 'Logout',
      'common.dashboard': 'Dashboard', 'common.profile': 'Profile', 'common.admin': 'Admin Panel',
      'common.browse_properties': 'Browse Properties', 'common.contact_us': 'Contact Us',
      'common.pay_rent': 'Pay Rent', 'common.report_issue': 'Report an Issue',
      'common.welcome_back': 'Welcome back', 'common.tagline': 'Premier Property Management & Real Estate'
    },
    sw: {
      'common.login': 'Ingia', 'common.register': 'Jisajili', 'common.logout': 'Toka',
      'common.dashboard': 'Dashibodi', 'common.profile': 'Wasifu', 'common.admin': 'Jopo la Usimamizi',
      'common.browse_properties': 'Tazama Majengo', 'common.contact_us': 'Wasiliana Nasi',
      'common.pay_rent': 'Lipa Kodi', 'common.report_issue': 'Ripoti Tatizo',
      'common.welcome_back': 'Karibu tena', 'common.tagline': 'Usimamizi Bora wa Mali Isiyohamishika'
    }
  };

  let current = 'en';
  let dict = {};

  function detectInitial() {
    try {
      const saved = localStorage.getItem('mw_lang');
      if (saved) return saved;
      const nav = (navigator.language || 'en').slice(0, 2);
      if ((cfg.supportedLanguages || []).some(function (l) { return l.code === nav; })) return nav;
    } catch (e) {}
    return cfg.defaultLanguage || 'en';
  }

  async function loadDictionary(lang) {
    dict = {};
    if (typeof window.supabaseClient === 'undefined') { return; }
    try {
      const { data } = await window.supabaseClient
        .from('translations')
        .select('key, value, namespace')
        .eq('language_code', lang)
        .eq('is_active', true);
      if (data) {
        data.forEach(function (t) { dict[t.namespace + '.' + t.key] = t.value; });
      }
    } catch (e) { /* offline / table missing — use fallback */ }
  }

  function applyLanguage(lang) {
    current = lang;
    try { localStorage.setItem('mw_lang', lang); } catch (e) {}
    document.documentElement.lang = lang;
    const langDef = (cfg.supportedLanguages || []).find(function (l) { return l.code === lang; });
    document.documentElement.dir = (langDef && langDef.rtl) ? 'rtl' : 'ltr';

    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      const key = el.getAttribute('data-i18n');
      const value = dict[key] || (fallback[lang] && fallback[lang][key]) || el.getAttribute('data-i18n');
      el.textContent = value;
    });

    // Update language selector if present
    const sel = document.getElementById('lang-select') || document.getElementById('pf-language');
    if (sel) sel.value = lang;

    document.dispatchEvent(new CustomEvent('mw:langchange', { detail: { lang: lang } }));
  }

  function populateSelectors() {
    (cfg.supportedLanguages || []).forEach(function (l) {
      const sel = document.getElementById('lang-select');
      if (sel) {
        const opt = document.createElement('option');
        opt.value = l.code;
        opt.textContent = l.flag + ' ' + l.native;
        sel.appendChild(opt);
      }
      const pf = document.getElementById('pf-language');
      if (pf) {
        const opt = document.createElement('option');
        opt.value = l.code;
        opt.textContent = l.name + ' — ' + l.native;
        pf.appendChild(opt);
      }
    });
  }

  window.MWAROKIN_I18N = {
    current: function () { return current; },
    t: function (key) { return dict[key] || (fallback[current] && fallback[current][key]) || key; },
    async setLanguage(lang) {
      await loadDictionary(lang);
      applyLanguage(lang);
      // persist to user profile if signed in
      try {
        const { data: { user } } = await window.supabaseClient.auth.getUser();
        if (user) {
          await window.supabaseClient.from('profiles')
            .update({ preferred_language: lang }).eq('id', user.id);
        }
      } catch (e) {}
    },
    async init() {
      populateSelectors();
      const lang = detectInitial();
      await loadDictionary(lang);
      applyLanguage(lang);

      const sel = document.getElementById('lang-select');
      if (sel) {
        sel.addEventListener('change', function () {
          window.MWAROKIN_I18N.setLanguage(sel.value);
        });
      }
    }
  };
})();