/**
 * Mwarokin Estates — Auth Module
 * Sign-up, sign-in, sign-out, session guard, nav state.
 */
(function () {
  const sb = window.supabaseClient;
  if (!sb) return;

  const cfg = window.MWAROKIN_CONFIG || {};

  // ---------- Public API ----------
  window.MWAROKIN_AUTH = {
    signUp,
    signIn,
    signOut,
    getUser,
    getProfile,
    requireAuth,
    requireRole,
    resetPassword,
    updatePassword,
    updateProfile,
    saveCommunicationProfile,
    getCommunicationProfile
  };

  // ---------- Auth operations ----------
  async function signUp({ email, password, full_name, phone, role }) {
    const { data, error } = await sb.auth.signUp({
      email,
      password,
      options: {
        data: { full_name, phone, role },
        emailRedirectTo: window.location.origin + cfg.basePath + 'dashboard.html'
      }
    });
    if (error) return { success: false, error: error.message };

    // Ensure a profile row exists (trigger also handles this)
    if (data.user) {
      await sb.from('profiles').upsert({
        id: data.user.id,
        full_name: full_name || '',
        phone: phone || '',
        role: role || 'tenant'
      }, { onConflict: 'id' });
    }
    return { success: true, data };
  }

  async function signIn(email, password) {
    const { data, error } = await sb.auth.signInWithPassword({ email, password });
    if (error) return { success: false, error: error.message };
    return { success: true, data };
  }

  async function signOut() {
    await sb.auth.signOut();
    const home = cfg.basePath || '/';
    window.location.href = home;
  }

  async function getUser() {
    const { data, error } = await sb.auth.getUser();
    if (error || !data.user) return null;
    return data.user;
  }

  async function getProfile(userId) {
    const id = userId || (await getUser())?.id;
    if (!id) return null;
    const { data, error } = await sb.from('profiles').select('*').eq('id', id).maybeSingle();
    if (error || !data) return null;
    return data;
  }

  /** Redirect to login if not signed in. Returns user or null. */
  async function requireAuth() {
    const user = await getUser();
    if (!user) {
      window.location.href = cfg.basePath + 'login.html';
      return null;
    }
    return user;
  }

  /** Redirect based on allowed roles. Returns { user, profile } or null. */
  async function requireRole(allowedRoles) {
    const user = await requireAuth();
    if (!user) return null;
    const profile = await getProfile(user.id);
    const role = profile?.role;
    if (!allowedRoles.includes(role)) {
      window.toast('Access denied. You do not have permission for this page.', 'error');
      window.location.href = cfg.basePath + 'dashboard.html';
      return null;
    }
    return { user, profile };
  }

  async function resetPassword(email) {
    const { error } = await sb.auth.resetPasswordForEmail(email, {
      redirectTo: window.location.origin + cfg.basePath + 'profile.html'
    });
    if (error) return { success: false, error: error.message };
    return { success: true };
  }

  async function updatePassword(newPassword) {
    const { error } = await sb.auth.updateUser({ password: newPassword });
    if (error) return { success: false, error: error.message };
    return { success: true };
  }

  async function updateProfile(patch) {
    const user = await getUser();
    if (!user) return { success: false, error: 'Not authenticated' };
    const { data, error } = await sb.from('profiles').update(patch).eq('id', user.id).select().single();
    if (error) return { success: false, error: error.message };
    return { success: true, data };
  }

  async function getCommunicationProfile(userId) {
    const id = userId || (await getUser())?.id;
    if (!id) return null;
    const { data, error } = await sb.from('communication_profiles').select('*').eq('user_id', id).maybeSingle();
    if (error || !data) return null;
    return data;
  }

  async function saveCommunicationProfile(fields) {
    const user = await getUser();
    if (!user) return { success: false, error: 'Not authenticated' };
    const { data, error } = await sb.from('communication_profiles')
      .upsert({ user_id: user.id, ...fields }, { onConflict: 'user_id' })
      .select()
      .single();
    if (error) return { success: false, error: error.message };
    return { success: true, data };
  }

  // ---------- Page behaviours ----------

  /** Update navbar for logged-in state. */
  async function setupNav() {
    const authEl = document.getElementById('nav-auth');
    const userEl = document.getElementById('nav-user');
    const logoutBtn = document.getElementById('nav-logout');
    const user = await getUser();

    if (authEl) authEl.classList.toggle('hidden', !!user);
    if (userEl) userEl.classList.toggle('hidden', !user);

    if (logoutBtn) {
      logoutBtn.addEventListener('click', function (e) {
        e.preventDefault();
        signOut();
      });
    }

    // Show admin link only for staff
    const adminLink = document.getElementById('admin-link');
    if (adminLink && user) {
      const profile = await getProfile(user.id);
      if (profile && ['admin', 'agent'].includes(profile.role)) {
        adminLink.classList.remove('hidden');
      }
    }
  }

  /** Handle <a href="logout"> pattern on any page. */
  function bindLogoutLinks() {
    document.querySelectorAll('a[href="logout"]').forEach(function (a) {
      a.addEventListener('click', function (e) { e.preventDefault(); signOut(); });
    });
  }

  /** Wire mobile burger menu. */
  function setupBurger() {
    const burger = document.getElementById('nav-burger');
    const links = document.getElementById('nav-links');
    if (burger && links) {
      burger.addEventListener('click', function () { links.classList.toggle('open'); });
    }
  }

  // ---------- Bootstraps ----------
  window.MWAROKIN = window.MWAROKIN || {};

  document.addEventListener('DOMContentLoaded', function () {
    bindLogoutLinks();
    setupBurger();
    if (typeof window.MWAROKIN_I18N !== 'undefined') {
      window.MWAROKIN_I18N.init();
    }
    if (typeof window.MWAROKIN_CURRENCY !== 'undefined') {
      window.MWAROKIN_CURRENCY.init();
    }
    setupNav();
  });

  // ---------- Login / register page handlers ----------
  document.addEventListener('DOMContentLoaded', function () {
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
      loginForm.addEventListener('submit', async function (e) {
        e.preventDefault();
        const btn = document.getElementById('login-btn');
        const err = document.getElementById('form-error');
        btn.disabled = true;
        err.classList.add('hidden');
        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;
        const result = await signIn(email, password);
        if (!result.success) {
          err.textContent = result.error;
          err.classList.remove('hidden');
          btn.disabled = false;
          return;
        }
        const profile = await getProfile(result.data.user.id);
        const next = (profile && ['admin', 'agent'].includes(profile.role)) ? 'admin.html' : 'dashboard.html';
        window.location.href = cfg.basePath + next;
      });
    }

    const resetLink = document.getElementById('reset-link');
    if (resetLink) {
      resetLink.addEventListener('click', async function (e) {
        e.preventDefault();
        const email = document.getElementById('email')?.value;
        if (!email) { window.toast('Enter your email address first.', 'warning'); return; }
        const result = await resetPassword(email);
        if (result.success) {
          window.toast('Password reset link sent. Check your email.', 'success');
        } else {
          window.toast(result.error, 'error');
        }
      });
    }

    const registerForm = document.getElementById('register-form');
    if (registerForm) {
      registerForm.addEventListener('submit', async function (e) {
        e.preventDefault();
        const btn = document.getElementById('register-btn');
        const err = document.getElementById('form-error');
        btn.disabled = true;
        err.classList.add('hidden');
        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;
        if (password.length < 8) {
          err.textContent = 'Password must be at least 8 characters.';
          err.classList.remove('hidden');
          btn.disabled = false;
          return;
        }
        const result = await signUp({
          email, password,
          full_name: document.getElementById('full_name').value.trim(),
          phone: document.getElementById('phone').value.trim(),
          role: document.getElementById('role').value
        });
        if (!result.success) {
          err.textContent = result.error;
          err.classList.remove('hidden');
          btn.disabled = false;
          return;
        }
        window.toast('Account created. Check your email to confirm, then sign in.', 'success');
        setTimeout(function () { window.location.href = cfg.basePath + 'login.html'; }, 1800);
      });
    }
  });
})();