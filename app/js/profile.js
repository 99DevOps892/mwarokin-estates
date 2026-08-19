/**
 * Mwarokin Estates — Profile Module
 * Handles profile.html: profile update, communication channels, preferences,
 * password change, danger zone. Pre-fills from the current user session.
 */
(function () {
  const sb = window.supabaseClient;
  if (!sb) return;

  document.addEventListener('DOMContentLoaded', async function () {
    if (!document.getElementById('profile-form')) return;

    const auth = await window.MWAROKIN_AUTH.requireAuth();
    if (!auth) return;

    const profile = await window.MWAROKIN_AUTH.getProfile(auth.id);

    // --- Identity ---
    const fullName = document.getElementById('pf-full-name');
    const phone = document.getElementById('pf-phone');
    if (profile) {
      if (fullName) fullName.value = profile.full_name || '';
      if (phone) phone.value = profile.phone || '';
      const sel = document.getElementById('pf-language');
      if (sel) sel.value = profile.preferred_language || window.MWAROKIN_I18N.current();
      const csel = document.getElementById('pf-currency');
      if (csel) csel.value = profile.preferred_currency || window.MWAROKIN_CURRENCY.current;
      const emailEl = document.getElementById('pf-email');
      if (emailEl) emailEl.textContent = auth.email || '';
    }

    document.getElementById('profile-form').addEventListener('submit', async function (e) {
      e.preventDefault();
      const result = await window.MWAROKIN_AUTH.updateProfile({
        full_name: fullName.value.trim(),
        phone: phone.value.trim(),
        preferred_language: document.getElementById('pf-language').value,
        preferred_currency: document.getElementById('pf-currency').value
      });
      window.toast(result.success ? 'Profile updated.' : result.error, result.success ? 'success' : 'error');
    });

    // --- Communication channels ---
    const comm = await window.MWAROKIN_AUTH.getCommunicationProfile(auth.id);
    if (comm) {
      const map = { 'comm-whatsapp': 'whatsapp', 'comm-telegram': 'telegram', 'comm-sms': 'sms', 'comm-email': 'email' };
      Object.keys(map).forEach(function (id) {
        const field = document.getElementById(id);
        if (field && comm[map[id]]) field.value = comm[map[id]];
      });
    }
    const commForm = document.getElementById('comm-form');
    if (commForm) {
      commForm.addEventListener('submit', async function (e) {
        e.preventDefault();
        const fields = {
          whatsapp: document.getElementById('comm-whatsapp').value.trim(),
          telegram: document.getElementById('comm-telegram').value.trim(),
          sms: document.getElementById('comm-sms').value.trim(),
          email: document.getElementById('comm-email').value.trim() || auth.email
        };
        const result = await window.MWAROKIN_AUTH.saveCommunicationProfile(fields);
        window.toast(result.success ? 'Communication channels saved.' : result.error, result.success ? 'success' : 'error');
      });
    }

    // --- Password ---
    const pwForm = document.getElementById('password-form');
    if (pwForm) {
      pwForm.addEventListener('submit', async function (e) {
        e.preventDefault();
        const p1 = document.getElementById('pw-new').value;
        const p2 = document.getElementById('pw-confirm').value;
        if (p1.length < 8) { window.toast('Password must be at least 8 characters.', 'warning'); return; }
        if (p1 !== p2) { window.toast('Passwords do not match.', 'warning'); return; }
        const result = await window.MWAROKIN_AUTH.updatePassword(p1);
        window.toast(result.success ? 'Password updated.' : result.error, result.success ? 'success' : 'error');
        if (result.success) pwForm.reset();
      });
    }

    // --- Danger zone ---
    const dangerForm = document.getElementById('danger-form');
    if (dangerForm) {
      dangerForm.addEventListener('submit', async function (e) {
        e.preventDefault();
        const email = document.getElementById('danger-email').value.trim();
        if (email !== auth.email) { window.toast('Enter your account email to confirm.', 'warning'); return; }
        if (!confirm('This permanently deletes your account. Continue?')) return;
        // Note: deletion via client SDK requires the delete user edge function / admin key.
        window.toast('Account deletion requires administrator approval. Our team will contact you.', 'info');
      });
    }
  });
})();