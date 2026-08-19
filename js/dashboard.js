/**
 * Mwarokin Estates — Dashboard Module
 * Renders stats, properties, payments, maintenance and notifications for the
 * signed-in user. Requires dashboard.html.
 */
(function () {
  const sb = window.supabaseClient;
  if (!sb) return;

  document.addEventListener('DOMContentLoaded', async function () {
    const welcome = document.getElementById('welcome-user');
    if (!welcome) return; // not the dashboard page

    const auth = await window.MWAROKIN_AUTH.requireAuth();
    if (!auth) return;

    const profile = await window.MWAROKIN_AUTH.getProfile(auth.id);
    welcome.textContent = 'Welcome, ' + (profile?.full_name || auth.email) + ' — ' + (profile?.role || 'member');

    await Promise.all([
      loadStats(profile),
      loadPropertiesTab(profile),
      loadPaymentsTab(profile),
      loadMaintenanceTab(profile),
      loadNotificationsTab(profile)
    ]);

    setupTabs();
    setupMaintenanceModal();
    subscribe();
  });

  function setupTabs() {
    const tabs = document.querySelectorAll('#dash-tabs .tab');
    tabs.forEach(function (tab) {
      tab.addEventListener('click', function () {
        tabs.forEach(function (t) { t.classList.remove('active'); });
        document.querySelectorAll('.tab-panel').forEach(function (p) { p.classList.remove('active'); });
        tab.classList.add('active');
        document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
      });
    });
  }

  async function loadStats(profile) {
    const { data } = await sb.rpc('get_dashboard_stats');
    const map = {
      'stat-properties': data ? data.total_properties : '—',
      'stat-available': data ? data.available_properties : '—',
      'stat-leases': data ? data.active_leases : '—',
      'stat-revenue': data ? window.fmtMoney(data.monthly_revenue) : '—',
      'stat-fees': data ? window.fmtMoney(data.platform_fees) : '—',
      'stat-maintenance': data ? data.pending_maintenance : '—'
    };
    Object.keys(map).forEach(function (id) {
      const el = document.getElementById(id);
      if (el) el.textContent = map[id];
    });
  }

  async function loadPropertiesTab(profile) {
    const grid = document.getElementById('dash-properties');
    const empty = document.getElementById('dash-props-empty');
    if (!grid) return;
    const isStaff = profile && ['admin', 'agent'].includes(profile.role);
    const props = await window.MWAROKIN_PROPERTIES.getProperties(isStaff ? {} : { status: 'available' });
    grid.innerHTML = '';
    if (!props.length) { empty.classList.remove('hidden'); return; }
    props.forEach(function (p) { grid.appendChild(window.MWAROKIN_PROPERTIES.renderCard(p)); });
  }

  async function loadPaymentsTab(profile) {
    const list = document.getElementById('payment-list');
    const empty = document.getElementById('payments-empty');
    if (!list) return;
    const payments = await window.MWAROKIN_PAYMENTS.getMyPayments();
    list.innerHTML = '';
    if (!payments.length) { empty.classList.remove('hidden'); return; }
    payments.forEach(function (p) {
      const item = document.createElement('div');
      item.className = 'list-item';
      item.innerHTML = '' +
        '<div><h4>' + window.esc((p.properties && p.properties.title) || 'Rent payment') + '</h4>' +
        '<p>' + window.esc(p.payment_method) + ' · ' + window.esc(p.payment_date) + '</p></div>' +
        '<div style="text-align:right">' +
          '<div class="amount">' + window.fmtMoney(p.amount) + '</div>' +
          '<span class="badge status-' + (p.status === 'completed' ? 'available' : p.status === 'failed' ? 'sold' : 'rented') + '">' + window.esc(p.status) + '</span>' +
        '</div>';
      list.appendChild(item);
    });
  }

  async function loadMaintenanceTab(profile) {
    const list = document.getElementById('maintenance-list');
    if (!list) return;
    const { data } = await sb.from('maintenance_requests').select('*').order('created_at', { ascending: false }).limit(20);
    list.innerHTML = '';
    if (!data || !data.length) {
      list.innerHTML = '<p class="empty">No maintenance requests. Report an issue to get started.</p>';
      return;
    }
    data.forEach(function (m) {
      const item = document.createElement('div');
      item.className = 'list-item';
      item.innerHTML = '' +
        '<div><h4>[' + window.esc(m.request_type) + '] ' + window.esc(m.description.slice(0, 60)) + '</h4>' +
        '<p>' + window.esc(m.priority) + ' priority · ' + window.esc(m.created_at.slice(0, 10)) + '</p></div>' +
        '<span class="badge status-' + (m.status === 'completed' ? 'available' : m.status === 'cancelled' ? 'sold' : 'rented') + '">' + window.esc(m.status.replace('_', ' ')) + '</span>';
      list.appendChild(item);
    });
  }

  async function loadNotificationsTab(profile) {
    const list = document.getElementById('notification-list');
    const empty = document.getElementById('notifications-empty');
    if (!list) return;
    const user = await window.MWAROKIN_AUTH.getUser();
    const { data } = await sb.from('notifications').select('*').eq('user_id', user.id).order('created_at', { ascending: false }).limit(20);
    list.innerHTML = '';
    if (!data || !data.length) { empty.classList.remove('hidden'); return; }
    data.forEach(function (n) {
      const item = document.createElement('div');
      item.className = 'list-item';
      item.innerHTML = '' +
        '<div><h4>' + window.esc(n.title) + '</h4><p>' + window.esc(n.body) + '</p></div>' +
        '<span class="badge ' + (n.is_read ? 'status-available' : 'status-rented') + '">' + (n.is_read ? 'read' : 'new') + '</span>';
      list.appendChild(item);
      if (!n.is_read) {
        sb.from('notifications').update({ is_read: true, read_at: new Date().toISOString() }).eq('id', n.id);
      }
    });
  }

  function setupMaintenanceModal() {
    const openBtn = document.getElementById('btn-new-maintenance');
    const modal = document.getElementById('maintenance-modal');
    if (!openBtn || !modal) return;
    openBtn.addEventListener('click', function () { modal.classList.remove('hidden'); });
    const form = document.getElementById('maintenance-form');
    form.addEventListener('submit', async function (e) {
      e.preventDefault();
      const user = await window.MWAROKIN_AUTH.getUser();
      const { data: tenant } = await sb.from('tenants').select('id').eq('user_id', user.id).maybeSingle();
      const { error } = await sb.from('maintenance_requests').insert({
        tenant_id: tenant?.id || null,
        request_type: document.getElementById('m-type').value,
        priority: document.getElementById('m-priority').value,
        description: document.getElementById('m-description').value
      });
      if (error) { window.toast(error.message, 'error'); return; }
      window.toast('Maintenance request submitted.', 'success');
      modal.classList.add('hidden');
      form.reset();
      setTimeout(function () { window.location.reload(); }, 900);
    });
  }

  // Live-update stats & lists when payments/properties change
  function subscribe() {
    if (!window.MWAROKIN_REALTIME) return;
    window.MWAROKIN_REALTIME.subscribeToTable('payments', function () {
      loadStats();
      loadPaymentsTab();
    });
    window.MWAROKIN_REALTIME.subscribeToTable('maintenance_requests', function () {
      loadMaintenanceTab();
    });
    window.MWAROKIN_REALTIME.subscribeToTable('notifications', function (payload) {
      if (payload.eventType === 'INSERT') {
        loadNotificationsTab();
        window.toast(payload.new.title, 'info');
      }
    });
  }
})();