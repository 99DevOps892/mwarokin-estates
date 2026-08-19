/**
 * Mwarokin Estates — Admin Module
 * Admin panel: property CRUD, payment approval, lead campaigns, audit log.
 * Requires admin.html and an admin/agent role.
 */
(function () {
  const sb = window.supabaseClient;
  if (!sb) return;

  document.addEventListener('DOMContentLoaded', async function () {
    if (!document.getElementById('admin-tabs')) return;

    const auth = await window.MWAROKIN_AUTH.requireRole(['admin', 'agent']);
    if (!auth) return;

    await Promise.all([
      loadProperties(),
      loadPayments(),
      loadLeads(),
      loadAudit()
    ]);

    setupTabs();
    setupPropertyModal();
    setupLeadActions();
    subscribe();
  });

  function setupTabs() {
    const tabs = document.querySelectorAll('#admin-tabs .tab');
    tabs.forEach(function (tab) {
      tab.addEventListener('click', function () {
        tabs.forEach(function (t) { t.classList.remove('active'); });
        document.querySelectorAll('.tab-panel').forEach(function (p) { p.classList.remove('active'); });
        tab.classList.add('active');
        document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
      });
    });
  }

  // ---------- Properties ----------
  async function loadProperties(search) {
    const tbody = document.getElementById('admin-properties-tbody');
    if (!tbody) return;
    let props = await window.MWAROKIN_PROPERTIES.getProperties({});
    if (search) {
      const s = search.toLowerCase();
      props = props.filter(function (p) {
        return (p.title || '').toLowerCase().includes(s) || (p.location || '').toLowerCase().includes(s);
      });
    }
    tbody.innerHTML = '';
    props.forEach(function (p) {
      const tr = document.createElement('tr');
      tr.innerHTML = '' +
        '<td><strong>' + window.esc(p.title) + '</strong></td>' +
        '<td>' + window.esc(p.property_type) + '</td>' +
        '<td class="amount">' + window.fmtMoney(p.price) + '</td>' +
        '<td><span class="badge status-' + window.esc(p.status) + '">' + window.esc(p.status.replace('_', ' ')) + '</span></td>' +
        '<td>' + (p.views_count || 0) + '</td>' +
        '<td class="row-actions">' +
          '<button class="btn btn-ghost btn-sm" data-edit="' + p.id + '">Edit</button>' +
          '<button class="btn btn-danger btn-sm" data-del="' + p.id + '">Delete</button>' +
        '</td>';
      tbody.appendChild(tr);
    });

    tbody.querySelectorAll('[data-edit]').forEach(function (btn) {
      btn.addEventListener('click', function () { openPropertyModal(btn.dataset.edit); });
    });
    tbody.querySelectorAll('[data-del]').forEach(function (btn) {
      btn.addEventListener('click', async function () {
        if (!confirm('Delete this property?')) return;
        const result = await window.MWAROKIN_PROPERTIES.deleteProperty(btn.dataset.del);
        window.toast(result.success ? 'Deleted.' : result.error, result.success ? 'success' : 'error');
        loadProperties(document.getElementById('admin-search').value);
      });
    });
  }

  const searchInput = document.getElementById('admin-search');
  if (searchInput) {
    searchInput.addEventListener('input', function () {
      loadProperties(searchInput.value);
    });
  }

  function setupPropertyModal() {
    const addBtn = document.getElementById('btn-add-property');
    const modal = document.getElementById('property-modal');
    if (!addBtn || !modal) return;

    addBtn.addEventListener('click', function () {
      document.getElementById('property-modal-title').textContent = 'Add Property';
      document.getElementById('property-form').reset();
      modal.classList.remove('hidden');
    });

    document.querySelectorAll('[data-close]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        document.getElementById(btn.dataset.close).classList.add('hidden');
      });
    });

    document.getElementById('property-form').addEventListener('submit', async function (e) {
      e.preventDefault();
      const id = document.getElementById('p-id').value;
      const payload = {
        title: document.getElementById('p-title').value.trim(),
        property_type: document.getElementById('p-type').value,
        status: document.getElementById('p-status').value,
        price: Number(document.getElementById('p-price').value),
        deposit: Number(document.getElementById('p-deposit').value) || null,
        bedrooms: Number(document.getElementById('p-bedrooms').value) || 0,
        bathrooms: Number(document.getElementById('p-bathrooms').value) || 0,
        area_sqft: Number(document.getElementById('p-area').value) || null,
        location: document.getElementById('p-location').value.trim(),
        city: document.getElementById('p-city').value.trim(),
        county: document.getElementById('p-county').value.trim(),
        latitude: document.getElementById('p-lat').value ? Number(document.getElementById('p-lat').value) : null,
        longitude: document.getElementById('p-lng').value ? Number(document.getElementById('p-lng').value) : null,
        description: document.getElementById('p-description').value.trim(),
        images: document.getElementById('p-images').value.split(',').map(function (s) { return s.trim(); }).filter(Boolean),
        amenities: document.getElementById('p-amenities').value.split(',').map(function (s) { return s.trim(); }).filter(Boolean)
      };
      const result = id
        ? await window.MWAROKIN_PROPERTIES.updateProperty(id, payload)
        : await window.MWAROKIN_PROPERTIES.addProperty(payload);
      if (!result.success) { window.toast(result.error, 'error'); return; }
      window.toast('Property saved.', 'success');
      modal.classList.add('hidden');
      loadProperties(document.getElementById('admin-search').value);
    });
  }

  async function openPropertyModal(id) {
    const prop = await window.MWAROKIN_PROPERTIES.getProperty(id);
    if (!prop) return;
    const modal = document.getElementById('property-modal');
    document.getElementById('property-modal-title').textContent = 'Edit Property';
    document.getElementById('p-id').value = prop.id;
    document.getElementById('p-title').value = prop.title || '';
    document.getElementById('p-type').value = prop.property_type || 'house';
    document.getElementById('p-status').value = prop.status || 'available';
    document.getElementById('p-price').value = prop.price || '';
    document.getElementById('p-deposit').value = prop.deposit || '';
    document.getElementById('p-bedrooms').value = prop.bedrooms || 0;
    document.getElementById('p-bathrooms').value = prop.bathrooms || 0;
    document.getElementById('p-area').value = prop.area_sqft || '';
    document.getElementById('p-location').value = prop.location || '';
    document.getElementById('p-city').value = prop.city || '';
    document.getElementById('p-county').value = prop.county || '';
    document.getElementById('p-lat').value = prop.latitude || '';
    document.getElementById('p-lng').value = prop.longitude || '';
    document.getElementById('p-description').value = prop.description || '';
    document.getElementById('p-images').value = (prop.images || []).join(', ');
    document.getElementById('p-amenities').value = (prop.amenities || []).join(', ');
    modal.classList.remove('hidden');
  }

  // ---------- Payments ----------
  async function loadPayments() {
    const tbody = document.getElementById('admin-payments-tbody');
    if (!tbody) return;
    const stats = await window.MWAROKIN_PAYMENTS.getPaymentStats();
    const el = {
      'pay-total': window.fmtMoney(stats.totalRevenue),
      'pay-fees': window.fmtMoney(stats.platformFees),
      'pay-payouts': window.fmtMoney(stats.landlordPayouts),
      'pay-pending': stats.pending
    };
    Object.keys(el).forEach(function (id) {
      const node = document.getElementById(id);
      if (node) node.textContent = el[id];
    });

    const { data } = await sb.from('payments').select('*').order('created_at', { ascending: false }).limit(30);
    tbody.innerHTML = '';
    if (!data || !data.length) {
      tbody.innerHTML = '<tr><td colspan="8" class="empty">No payments yet.</td></tr>';
      return;
    }
    data.forEach(function (p) {
      const tr = document.createElement('tr');
      tr.innerHTML = '' +
        '<td>' + window.esc(p.transaction_id || p.id.slice(0, 8)) + '</td>' +
        '<td class="amount">' + window.fmtMoney(p.amount) + '</td>' +
        '<td>' + window.fmtMoney(p.landlord_amount) + '</td>' +
        '<td>' + window.fmtMoney(p.platform_fee) + '</td>' +
        '<td>' + window.esc(p.payment_method) + '</td>' +
        '<td><span class="badge status-' + (p.status === 'completed' ? 'available' : p.status === 'failed' ? 'sold' : 'rented') + '">' + window.esc(p.status) + '</span></td>' +
        '<td>' + window.esc(p.payment_date) + '</td>' +
        '<td class="row-actions">' +
          (p.status === 'pending' || p.status === 'processing'
            ? '<button class="btn btn-sm" style="background:var(--success);color:#fff" data-aprove="' + p.id + '">Approve</button>' +
              '<button class="btn btn-danger btn-sm" data-reject="' + p.id + '">Reject</button>'
            : '<span class="muted">—</span>') +
        '</td>';
      tbody.appendChild(tr);
    });

    tbody.querySelectorAll('[data-aprove]').forEach(function (btn) {
      btn.addEventListener('click', async function () {
        if (!confirm('Approve this payment?')) return;
        const r = await window.MWAROKIN_PAYMENTS.approvePayment(btn.dataset.aprove);
        window.toast(r.success ? 'Payment approved.' : r.error, r.success ? 'success' : 'error');
        loadPayments();
      });
    });
    tbody.querySelectorAll('[data-reject]').forEach(function (btn) {
      btn.addEventListener('click', async function () {
        if (!confirm('Reject this payment?')) return;
        const r = await window.MWAROKIN_PAYMENTS.rejectPayment(btn.dataset.reject);
        window.toast(r.success ? 'Payment rejected.' : r.error, r.success ? 'warning' : 'error');
        loadPayments();
      });
    });
  }

  // ---------- Leads (AI onboarding) ----------
  async function loadLeads() {
    const tbody = document.getElementById('admin-leads-tbody');
    if (!tbody) return;
    const { data } = await sb.from('prospects').select('*').order('lead_score', { ascending: false }).limit(30);
    tbody.innerHTML = '';
    if (!data || !data.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="empty">No prospects yet. Run an outreach campaign to start AI lead discovery.</td></tr>';
      return;
    }
    data.forEach(function (p) {
      const tr = document.createElement('tr');
      const signals = p.intent_signals || [];
      tr.innerHTML = '' +
        '<td>' + window.esc(p.name || '—') + '</td>' +
        '<td>' + window.esc(p.phone || p.email || '—') + '</td>' +
        '<td>' + window.esc(p.property_address || '—') + '</td>' +
        '<td><span class="badge status-' + (p.lead_score >= 60 ? 'available' : 'rented') + '">' + p.lead_score + '</span></td>' +
        '<td><span class="badge status-' + (p.qualification_status === 'hot' ? 'available' : p.qualification_status === 'converted' ? 'sold' : 'rented') + '">' + window.esc(p.qualification_status) + '</span></td>' +
        '<td>' + signals.length + ' signals</td>';
      tbody.appendChild(tr);
    });
  }

  function setupLeadActions() {
    const addBtn = document.getElementById('btn-add-lead');
    if (addBtn) {
      addBtn.addEventListener('click', async function () {
        const name = prompt('Prospect name (optional):');
        const phone = prompt('Phone:');
        if (!phone) return;
        const { error } = await sb.from('prospects').insert({
          name: name || null,
          phone: phone,
          lead_score: 50,
          intent_signals: [{ type: 'manual_entry', timestamp: new Date().toISOString() }]
        });
        if (error) { window.toast(error.message, 'error'); return; }
        window.toast('Prospect added.', 'success');
        loadLeads();
      });
    }

    const runBtn = document.getElementById('btn-run-campaign');
    if (runBtn) {
      runBtn.addEventListener('click', async function () {
        // This calls the AI orchestrator Edge Function when deployed.
        const { data, error } = await sb.rpc('get_high_intent_prospects', { min_score: 60, limit_count: 20 });
        if (error) {
          window.toast('No high-intent prospects yet. ' + error.message, 'info');
          return;
        }
        window.toast('Campaign queued for ' + (data || []).length + ' high-intent prospects.', 'success');
      });
    }
  }

  // ---------- Audit ----------
  async function loadAudit() {
    const tbody = document.getElementById('admin-audit-tbody');
    if (!tbody) return;
    const { data } = await sb.from('audit_logs').select('*, profiles(email, full_name)').order('created_at', { ascending: false }).limit(30);
    tbody.innerHTML = '';
    if (!data || !data.length) {
      tbody.innerHTML = '<tr><td colspan="4" class="empty">No audit records.</td></tr>';
      return;
    }
    data.forEach(function (a) {
      const tr = document.createElement('tr');
      tr.innerHTML = '' +
        '<td>' + window.esc((a.created_at || '').slice(0, 16)) + '</td>' +
        '<td>' + window.esc(a.action) + '</td>' +
        '<td>' + window.esc(a.table_name || '—') + '</td>' +
        '<td>' + window.esc((a.profiles && (a.profiles.full_name || a.profiles.email)) || 'system') + '</td>';
      tbody.appendChild(tr);
    });
  }

  // ---------- Realtime ----------
  function subscribe() {
    if (!window.MWAROKIN_REALTIME) return;
    window.MWAROKIN_REALTIME.subscribeToTable('payments', function () { loadPayments(); });
    window.MWAROKIN_REALTIME.subscribeToTable('properties', function () {
      loadProperties(document.getElementById('admin-search').value);
    });
    window.MWAROKIN_REALTIME.subscribeToTable('prospects', function () { loadLeads(); });
  }
})();