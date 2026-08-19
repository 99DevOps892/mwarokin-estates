/**
 * Mwarokin Estates — Properties Module
 * Fetch, render, create, update, delete properties. Realtime subscription hooks.
 */
(function () {
  const sb = window.supabaseClient;
  if (!sb) return;

  // ---------- Public API ----------
  window.MWAROKIN_PROPERTIES = {
    getProperties,
    getProperty,
    getFeaturedCount,
    addProperty,
    updateProperty,
    deleteProperty,
    incrementViews,
    renderCard,
    renderPropertyDetail
  };

  async function getProperties(filters) {
    filters = filters || {};
    let q = sb.from('properties').select('*');
    if (filters.status) q = q.eq('status', filters.status);
    if (filters.type && filters.type !== 'all') q = q.eq('property_type', filters.type);
    if (filters.search) {
      q = q.or('title.ilike.%' + filters.search + '%,location.ilike.%' + filters.search + '%,city.ilike.%' + filters.search + '%');
    }
    if (filters.limit) q = q.limit(filters.limit);
    q = q.order('is_featured', { ascending: false }).order('created_at', { ascending: false });
    const { data, error } = await q;
    if (error) { console.error('getProperties:', error.message); return []; }
    return data || [];
  }

  async function getProperty(id) {
    const { data, error } = await sb.from('properties').select('*').eq('id', id).maybeSingle();
    if (error || !data) return null;
    return data;
  }

  async function getFeaturedCount() {
    const { count, error } = await sb.from('properties').select('id', { count: 'exact', head: true }).eq('is_featured', true);
    if (error) return 0;
    return count || 0;
  }

  async function addProperty(payload) {
    const { data, error } = await sb.from('properties').insert([payload]).select().single();
    if (error) return { success: false, error: error.message };
    return { success: true, data };
  }

  async function updateProperty(id, payload) {
    const { data, error } = await sb.from('properties').update(payload).eq('id', id).select().single();
    if (error) return { success: false, error: error.message };
    return { success: true, data };
  }

  async function deleteProperty(id) {
    const { error } = await sb.from('properties').delete().eq('id', id);
    if (error) return { success: false, error: error.message };
    return { success: true };
  }

  async function incrementViews(id) {
    try { await sb.rpc('increment_property_views', { p_property_id: id }); } catch (e) {}
  }

  /** Build a property card element. */
  function renderCard(prop, ccy) {
    ccy = ccy || (window.MWAROKIN_CURRENCY ? window.MWAROKIN_CURRENCY.current : 'KES');
    const images = prop.images && prop.images.length ? prop.images : [];
    const img = images[0] || 'https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=800';
    const price = window.MWAROKIN_CURRENCY
      ? window.MWAROKIN_CURRENCY.format(window.MWAROKIN_CURRENCY.convert(prop.price, 'KES', ccy), ccy)
      : window.fmtMoney(prop.price, ccy);

    const card = document.createElement('article');
    card.className = 'property-card';
    card.innerHTML = '' +
      '<div class="pcard-media">' +
        '<img src="' + window.esc(img) + '" alt="' + window.esc(prop.title) + '" loading="lazy">' +
        '<span class="pcard-status status-' + window.esc(prop.status) + '">' + window.esc(prop.status.replace('_', ' ')) + '</span>' +
        '<button class="pcard-fav" data-id="' + prop.id + '" aria-label="Save">♥</button>' +
      '</div>' +
      '<div class="pcard-body">' +
        '<h3 class="pcard-title">' + window.esc(prop.title) + '</h3>' +
        '<p class="pcard-loc">📍 ' + window.esc(prop.location) + (prop.city ? ', ' + window.esc(prop.city) : '') + '</p>' +
        '<div class="pcard-price">' + price + '<small> / month</small></div>' +
        '<div class="pcard-meta">' +
          '<span>🛏 ' + (prop.bedrooms || 0) + '</span>' +
          '<span>🛁 ' + (prop.bathrooms || 0) + '</span>' +
          '<span>📐 ' + (prop.area_sqft || '—') + ' sqft</span>' +
        '</div>' +
        '<a class="btn btn-primary pcard-btn" href="' + window.appPath('property.html') + '?id=' + prop.id + '">View Details</a>' +
      '</div>';

    const fav = card.querySelector('.pcard-fav');
    fav.addEventListener('click', function (e) {
      e.preventDefault();
      fav.textContent = fav.textContent === '♥' ? '❤' : '♥';
    });
    return card;
  }

  /** Render the full property detail page. */
  function renderPropertyDetail(prop, container) {
    if (!container) return;
    const ccy = window.MWAROKIN_CURRENCY ? window.MWAROKIN_CURRENCY.current : 'KES';
    const price = window.MWAROKIN_CURRENCY
      ? window.MWAROKIN_CURRENCY.format(window.MWAROKIN_CURRENCY.convert(prop.price, 'KES', ccy), ccy)
      : window.fmtMoney(prop.price, ccy);
    const images = prop.images && prop.images.length ? prop.images : ['https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=800'];
    const amenities = prop.amenities || [];

    container.innerHTML = '' +
      '<div class="pdetail-hero">' +
        '<img src="' + window.esc(images[0]) + '" alt="' + window.esc(prop.title) + '">' +
        '<span class="pcard-status status-' + window.esc(prop.status) + '">' + window.esc(prop.status.replace('_', ' ')) + '</span>' +
      '</div>' +
      '<div class="pdetail-grid">' +
        '<div class="panel">' +
          '<h2>' + window.esc(prop.title) + '</h2>' +
          '<p class="pcard-loc">📍 ' + window.esc(prop.location) + ', ' + window.esc(prop.city || '') + ', ' + window.esc(prop.county || '') + '</p>' +
          '<div class="pdetail-meta">' +
            '<span>🛏 ' + (prop.bedrooms || 0) + ' beds</span>' +
            '<span>🛁 ' + (prop.bathrooms || 0) + ' baths</span>' +
            '<span>📐 ' + (prop.area_sqft || '—') + ' sqft</span>' +
            '<span>👁 ' + (prop.views_count || 0) + ' views</span>' +
          '</div>' +
          '<p class="pdetail-description">' + window.esc(prop.description || 'No description provided.') + '</p>' +
          (amenities.length ? '<div class="amenity-tags">' + amenities.map(function (a) { return '<span class="tag">' + window.esc(a) + '</span>'; }).join('') + '</div>' : '') +
        '</div>' +
        '<div class="side-card">' +
          '<p class="pdetail-price">' + price + '<small> / month</small></p>' +
          (prop.deposit ? '<p class="pcard-loc">Deposit: ' + window.fmtMoney(prop.deposit, ccy) + '</p>' : '') +
          '<div class="split-summary" style="margin-top:1rem">' +
            '<div class="split-row muted"><span>Landlord receives (95%)</span><span>' + (price.split(' ')[0] + ' ' + ((prop.price * 0.95).toLocaleString())) + '</span></div>' +
            '<div class="split-row muted"><span>Platform fee (5%)</span><span>' + (price.split(' ')[0] + ' ' + ((prop.price * 0.05).toLocaleString())) + '</span></div>' +
          '</div>' +
          '<a href="' + window.appPath('dashboard.html') + '" class="btn btn-primary btn-block btn-lg" style="margin-top:1rem">Enquire / Pay Rent</a>' +
        '</div>' +
      '</div>';
  }
})();