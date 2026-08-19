/**
 * Mwarokin Estates ΓÇö Global Configuration
 * ======================================
 * Single source of truth for app settings.
 *
 * SECURITY: SUPABASE_ANON_KEY is a PUBLIC publishable key. It is safe to ship
 * in client-side code. NEVER put the service_role key here or in any frontend file.
 *
 * Deployed via GitHub Pages (99DevOps892). Credentials live in GitHub Actions
 * secrets (SUPABASE_URL, SUPABASE_ANON_KEY) and are injected at build time.
 */
window.MWAROKIN_CONFIG = (function () {
  const SUPABASE_URL = 'https://spnerrqumefbuuscumhw.supabase.co';
  const SUPABASE_ANON_KEY = 'YOUR_SUPABASE_ANON_PUBLIC_KEY_HERE';

  return {
    appName: 'Mwarokin Estates',
    tagline: 'Premier Property Management & Real Estate',
    supabaseUrl: SUPABASE_URL,
    supabaseAnonKey: SUPABASE_ANON_KEY,

    // GitHub Pages base path. If your repo is 99DevOps892/mwarokin-estates,
    // deployed to https://99devops892.github.io/mwarokin-estates/ use '/mwarokin-estates/'.
    // If deploying to a custom root domain, use '/'.
    basePath: '/mwarokin-estates/',

    // Platform commission model (must match platform_settings table in Supabase)
    commissionRate: 5.0, // % to Mwarokin Estates; balance goes to landlord

    // Supported languages & currencies for the i18n/currency managers
    defaultLanguage: 'en',
    defaultCurrency: 'KES',
    supportedLanguages: [
      { code: 'en', name: 'English', native: 'English', flag: 'GB', rtl: false },
      { code: 'sw', name: 'Swahili', native: 'Kiswahili', flag: 'KE', rtl: false },
      { code: 'fr', name: 'French', native: 'Fran├ºais', flag: 'FR', rtl: false },
      { code: 'de', name: 'German', native: 'Deutsch', flag: 'DE', rtl: false },
      { code: 'ar', name: 'Arabic', native: '╪º┘ä╪╣╪▒╪¿┘è╪⌐', flag: 'AE', rtl: true }
    ],
    supportedCurrencies: ['KES', 'USD', 'EUR', 'GBP'],

    // Feature flags ΓÇö flip as integrations are provisioned
    features: {
      realtime: true,          // Supabase Realtime subscriptions
      payments: true,          // M-Pesa / Airtel / Bank UI
      i18n: true,              // multi-language
      currency: true,          // multi-currency
      messaging: true,         // in-app + channel preferences
      aiLeads: false           // AI lead-generation agents (requires keys)
    },

    // Auth pages
    pages: {
      login: 'login.html',
      register: 'register.html',
      dashboard: 'dashboard.html',
      admin: 'admin.html',
      profile: 'profile.html',
      home: 'index.html'
    }
  };
})();
