/* ═══════════════════════════════════════════════════════════
   Mwarokin Estates · Premium Webapp shared logic
   Umbrella: Syllogism Technology Africa (STA)
   Depends on: supabase-js CDN, js/config.js, js/supabase-client.js
   ═══════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  var sb = window.supabaseClient;

  var DASH = {
    admin: 'Dashboard Overview.html',
    landlord: 'Landlord Management Dashbord.html',
    caretaker: 'CareTakers Dashboard.html',
    tenant: 'Tenant Management Dashboard.html'
  };
  var DEFAULT_ROLE = 'tenant';

  window.MWAROKIN_APP = window.MWAROKIN_APP || {};

  function homeFor(role) {
    var page = DASH[role] || DASH[DEFAULT_ROLE];
    return window.appPath ? window.appPath(page) : page;
  }
  window.MWAROKIN_APP.homeFor = homeFor;

  // ─── Auth-aware header ───
  async function renderAuth() {
    var cta = document.getElementById('navCta');
    if (!cta || !sb) return;
    try {
      var s = await sb.auth.getSession();
      if (s.data && s.data.session) {
        var role = DEFAULT_ROLE;
        try {
          var u = await sb.auth.getUser();
          var p = await sb.from('profiles').select('role').eq('id', u.data.user.id).maybeSingle();
          if (p.data && p.data.role) role = p.data.role;
        } catch (e) {}
        var email = s.data.session.user.email || '';
        cta.innerHTML =
          '<a class="btn btn-ghost" href="' + homeFor(role) + '"><i class="fas fa-columns"></i> My Dashboard</a>' +
          '<button class="btn btn-gold" onclick="MWAROKIN_APP.logout()"><i class="fas fa-sign-out-alt"></i> Sign Out</button>' +
          '<span class="role-chip" style="margin-left:2px">' + (role.charAt(0).toUpperCase() + role.slice(1)) + '</span>';
        document.getElementById('mobileCta') && (document.getElementById('mobileCta').innerHTML =
          '<a class="btn btn-ghost" href="' + homeFor(role) + '"><i class="fas fa-columns"></i> My Dashboard</a>');
        return;
      }
    } catch (e) {}
    cta.innerHTML =
      '<a class="btn btn-ghost" href="Login.html"><i class="fas fa-sign-in-alt"></i> Sign In</a>' +
      '<a class="btn btn-gold" href="register.html"><i class="fas fa-user-plus"></i> Create Account</a>';
    var m = document.getElementById('mobileCta');
    if (m) m.innerHTML = '<a class="btn btn-gold" href="Login.html"><i class="fas fa-sign-in-alt"></i> Sign In</a>';
  }

  function logout() {
    if (!sb) { window.location.href = 'Login.html?reason=loggedout'; return; }
    sb.auth.signOut().then(function () {
      window.location.href = 'Login.html?reason=loggedout';
    });
  }
  window.MWAROKIN_APP.logout = logout;

  // ─── Mobile menu ───
  function setupMobile() {
    var burger = document.getElementById('hamburger');
    var menu = document.getElementById('mobileMenu');
    if (!burger || !menu) return;
    burger.addEventListener('click', function () {
      var open = menu.classList.toggle('open');
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    menu.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', function () { menu.classList.remove('open'); });
    });
  }

  // ─── PWA install prompt ───
  var deferredPrompt = null;
  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();
    deferredPrompt = e;
    var btn = document.getElementById('installBtn');
    if (btn) {
      btn.style.display = 'inline-flex';
      btn.addEventListener('click', function () {
        if (deferredPrompt) {
          deferredPrompt.prompt();
          deferredPrompt.userChoice.then(function (choice) {
            if (choice.outcome === 'accepted') toast('Mwarokin Estates app installed. Enjoy!', 'success');
            deferredPrompt = null;
          });
        }
      });
    }
  });
  window.addEventListener('appinstalled', function () {
    toast('Mwarokin Estates app installed.', 'success');
  });

  // ─── Year in footers ───
  function setYear() {
    document.querySelectorAll('[data-year]').forEach(function (el) {
      el.textContent = String(new Date().getFullYear());
    });
  }

  // ─── Active nav link ───
  function setActive() {
    var current = window.location.pathname.split('/').pop() || 'index.html';
    document.querySelectorAll('.nav-links a, .mobile-menu a').forEach(function (a) {
      var href = a.getAttribute('href');
      if (href && href.toLowerCase() === current.toLowerCase()) a.classList.add('active');
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    setYear();
    setActive();
    setupMobile();
    renderAuth();
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('sw.js').catch(function () {});
    }
  });
})();