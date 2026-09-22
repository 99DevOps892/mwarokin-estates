/**
 * Mwarokin Estates — Bot Protection (Cloudflare Turnstile + honeypot)
 * ===================================================================
 * Drop-in client module. Usage:
 *   window.STA_BOT_PROTECT.inject(form);      // add honeypot + Turnstile widget
 *   const r = await window.STA_BOT_PROTECT.guard(form);  // { ok, message }
 *   if (!r.ok) { block submission; return; }
 *
 * The site key is PUBLIC by design (Turnstile tokens are verified server-side
 * in netlify/functions/bot-gate.mjs using TURNSTILE_SECRET_KEY).
 * When no site key is provisioned (local/dev), the guard skips token checks
 * so development is not blocked; production builds supply the key via
 * netlify.toml build env vars.
 */
(function () {
  'use strict';

  if (window.STA_BOT_PROTECT) return;
  const PLACEHOLDER_KEY = '0x4AAAAAAACONFIG_MISSING';
  const VERIFY_ENDPOINT = '/.netlify/functions/bot-gate';
  const WIDGET_ID = 'sta-turnstile-widget';

  function siteKey() {
    if (window.STA_TURNSTILE_SITE_KEY) return window.STA_TURNSTILE_SITE_KEY;
    if (window.MWAROKIN_CONFIG && window.MWAROKIN_CONFIG.turnstileSiteKey) {
      return window.MWAROKIN_CONFIG.turnstileSiteKey;
    }
    return PLACEHOLDER_KEY;
  }

  function configured() { return siteKey() !== PLACEHOLDER_KEY; }

  function inject(form) {
    if (!form) return;
    if (form.querySelector('[data-bot-honeypot]')) return;
    const hp = document.createElement('input');
    hp.type = 'text';
    hp.name = 'website';
    hp.setAttribute('tabindex', '-1');
    hp.setAttribute('autocomplete', 'off');
    hp.setAttribute('aria-hidden', 'true');
    hp.style.cssText = 'position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden;';
    hp.setAttribute('data-bot-honeypot', '');
    form.appendChild(hp);

    const widget = document.createElement('div');
    widget.id = WIDGET_ID;
    widget.className = 'cf-turnstile';
    widget.dataset.sitekey = siteKey();
    widget.dataset.theme = 'dark';
    widget.dataset.callback = 'STA_BOT_PROTECT.onToken';
    form.appendChild(widget);

    const script = document.createElement('script');
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit&onload=STA_BOT_PROTECT.onLoaded';
    script.async = true;
    script.defer = true;
    document.head.appendChild(script);
  }

  async function verify(token) {
    if (!token) return { ok: false, message: 'Bot check incomplete. Please try again.' };
    try {
      const res = await fetch(VERIFY_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: token, action: 'auth' })
      });
      const body = await res.json();
      return { ok: !!body.ok, message: body.message || (body.ok ? 'ok' : 'Bot check failed.') };
    } catch (e) {
      return { ok: false, message: 'Bot verification service unavailable.' };
    }
  }

  async function guard(form) {
    const hp = form.querySelector('[data-bot-honeypot]');
    if (hp && hp.value.trim().length > 0) {
      return { ok: false, message: 'Submission rejected.' };
    }
    if (!configured()) {
      return { ok: true, message: 'dev-skip' }; // bot protection not provisioned yet
    }
    const tokenEl = form.querySelector('input[name="cf-turnstile-response"]');
    const token = tokenEl ? tokenEl.value : '';
    return verify(token);
  }

  window.STA_BOT_PROTECT = {
    configure: function (key) { window.STA_TURNSTILE_SITE_KEY = key; },
    inject: inject,
    guard: guard,
    onToken: function (token) {
      const form = document.getElementById(WIDGET_ID) && document.getElementById(WIDGET_ID).form;
      if (form) {
        let inp = form.querySelector('input[name="cf-turnstile-response"]');
        if (!inp) {
          inp = document.createElement('input');
          inp.type = 'hidden';
          inp.name = 'cf-turnstile-response';
          form.appendChild(inp);
        }
        inp.value = token;
      }
    },
    onLoaded: function () { /* widget(s) may render explicitly */ }
  };
})();