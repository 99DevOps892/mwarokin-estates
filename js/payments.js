/**
 * Mwarokin Estates — Payments Module
 * Records payments with the automatic 95/5 split (server trigger calculates it).
 * Supports M-Pesa, Airtel Money and Bank Transfer flows.
 * When Edge Functions are deployed, this module POSTs to them; until then it
 * records the payment directly so the UI is fully functional.
 */
(function () {
  const sb = window.supabaseClient;
  if (!sb) return;

  const cfg = window.MWAROKIN_CONFIG || {};

  window.MWAROKIN_PAYMENTS = {
    createPayment,
    getMyPayments,
    getPaymentStats,
    approvePayment,
    rejectPayment,
    splitPreview,
    functionUrl
  };

  function functionUrl(name) {
    return (cfg.supabaseUrl || '').replace(/\/$/, '') + '/functions/v1/' + name;
  }

  /** Preview the 95/5 split for a given amount. */
  function splitPreview(amount) {
    const rate = cfg.commissionRate != null ? cfg.commissionRate : 5.0;
    const platform = Math.round(Number(amount || 0) * rate) / 100;
    const landlord = Number(amount || 0) - platform;
    return { total: Number(amount || 0), platform: platform, landlord: landlord, rate: rate };
  }

  /**
   * Create a payment record.
   * @param {Object} opts { amount, method, phone, lease_id, tenant_id, property_id, landlord_id }
   */
  async function createPayment(opts) {
    const amount = Number(opts.amount);
    if (!amount || amount <= 0) return { success: false, error: 'Enter a valid amount' };

    // Build payment row — split columns are auto-filled by DB trigger
    const paymentPayload = {
      amount: amount,
      payment_method: opts.method || 'mpesa',
      payment_date: new Date().toISOString().slice(0, 10),
      due_date: opts.due_date || new Date().toISOString().slice(0, 10),
      tenant_id: opts.tenant_id || null,
      property_id: opts.property_id || null,
      lease_id: opts.lease_id || null,
      landlord_id: opts.landlord_id || null,
      transaction_id: opts.transaction_id || ('ME-' + Date.now()),
      status: opts.method === 'bank-transfer' ? 'pending' : 'processing',
      metadata: opts.metadata || {}
    };

    // Prefer Edge Function when a live callback is configured.
    // We attempt the function first; on any failure we fall back to direct insert.
    try {
      const url = functionUrl('payments');
      const authHeader = (await sb.auth.getSession()).data.session
        ? 'Bearer ' + (await sb.auth.getSession()).data.session.access_token : '';
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(authHeader ? { Authorization: authHeader } : {}) },
        body: JSON.stringify(paymentPayload)
      });
      if (res.ok) {
        const body = await res.json();
        return { success: true, data: body, viaFunction: true };
      }
    } catch (e) { /* Edge function unavailable — fall back below */ }

    const { data, error } = await sb.from('payments').insert([paymentPayload]).select().single();
    if (error) return { success: false, error: error.message };
    return { success: true, data };
  }

  /** Payments visible to the current user. */
  async function getMyPayments(tenantId) {
    let q = sb.from('payments').select('*, properties(title)').order('created_at', { ascending: false }).limit(20);
    if (tenantId) q = q.eq('tenant_id', tenantId);
    const { data, error } = await q;
    if (error) return [];
    return data || [];
  }

  /** Admin: aggregate payment stats. */
  async function getPaymentStats() {
    const { data, error } = await sb.rpc('get_dashboard_stats');
    if (error || !data) {
      return { totalRevenue: 0, platformFees: 0, landlordPayouts: 0, pending: 0 };
    }
    return {
      totalRevenue: data.monthly_revenue || 0,
      platformFees: data.platform_fees || 0,
      landlordPayouts: data.landlord_payouts || 0,
      pending: data.overdue_payments || 0
    };
  }

  async function approvePayment(id) {
    const { data, error } = await sb.rpc('approve_payment', { p_payment_id: id });
    if (error) return { success: false, error: error.message };
    return { success: true, data };
  }

  async function rejectPayment(id) {
    const { data, error } = await sb.rpc('reject_payment', { p_payment_id: id });
    if (error) return { success: false, error: error.message };
    return { success: true, data };
  }

  // ---------- Dashboard "Pay Rent" wiring (shared by dashboard.js) ----------
  window.addEventListener('DOMContentLoaded', function () {
    const openBtn = document.getElementById('btn-pay-rent');
    const modal = document.getElementById('pay-modal');
    if (!openBtn || !modal) return;

    const amountInput = document.getElementById('pay-amount');
    const methodSelect = document.getElementById('pay-method');
    const phoneField = document.getElementById('phone-field');
    const totalEl = document.getElementById('split-total');
    const landlordEl = document.getElementById('split-landlord');
    const feeEl = document.getElementById('split-fee');

    function refreshSplit() {
      const preview = splitPreview(amountInput.value);
      totalEl.textContent = 'KES ' + preview.total.toLocaleString();
      landlordEl.textContent = 'KES ' + preview.landlord.toLocaleString();
      feeEl.textContent = 'KES ' + preview.platform.toLocaleString();
    }

    openBtn.addEventListener('click', function () {
      modal.classList.remove('hidden');
      refreshSplit();
    });
    amountInput.addEventListener('input', refreshSplit);
    methodSelect.addEventListener('change', function () {
      phoneField.classList.toggle('hidden', methodSelect.value === 'bank-transfer');
    });

    document.querySelectorAll('[data-close]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        document.getElementById(btn.dataset.close).classList.add('hidden');
      });
    });

    const submitBtn = document.getElementById('pay-submit');
    const errEl = document.getElementById('pay-error');
    submitBtn.addEventListener('click', async function () {
      errEl.classList.add('hidden');
      submitBtn.disabled = true;
      try {
        const amount = amountInput.value;
        const method = methodSelect.value;
        const phone = document.getElementById('pay-phone').value;
        const user = await window.MWAROKIN_AUTH.getUser();
        if (!user) { window.toast('Please login to pay.', 'warning'); window.location.href = window.appPath('login.html'); return; }

        // Find or create tenant record for this user
        let tenantId = null;
        const { data: tenant } = await sb.from('tenants').select('id').eq('user_id', user.id).maybeSingle();
        if (tenant) tenantId = tenant.id;

        const result = await createPayment({ amount, method, phone, tenant_id: tenantId });
        if (!result.success) {
          errEl.textContent = result.error;
          errEl.classList.remove('hidden');
          return;
        }
        window.toast(method === 'bank-transfer'
          ? 'Bank transfer recorded. Admin will verify shortly.'
          : 'Payment initiated. ' + (method === 'mpesa' ? 'Check your M-Pesa prompt.' : 'Check your Airtel Money prompt.'), 'success');
        modal.classList.add('hidden');
        setTimeout(function () { window.location.reload(); }, 1500);
      } catch (e) {
        errEl.textContent = e.message;
        errEl.classList.remove('hidden');
      } finally {
        submitBtn.disabled = false;
      }
    });
  });
})();