/**
 * Mwarokin Estates — Home Page Module
 * Renders properties + search/filter on index.html.
 * Wired to the live index.html DOM ids:
 *   grid: properties-grid · stat: stat-properties
 *   filters: search-input / filter-type / filter-status · button: search-btn
 */
(function () {
  const sb = window.supabaseClient;
  if (!sb) return;

  document.addEventListener('DOMContentLoaded', async function () {
    const grid = document.getElementById('properties-grid');
    if (!grid) return; // not index.html

    // Hero stats
    const featured = await window.MWAROKIN_PROPERTIES.getFeaturedCount();
    const statProps = document.getElementById('stat-properties');
    const statFeatured = document.getElementById('stat-featured');
    if (statProps) statProps.textContent = '0';
    if (statFeatured) statFeatured.textContent = featured;
    try {
      const { count: total } = await sb.from('properties').select('id', { count: 'exact', head: true });
      if (statProps) statProps.textContent = total || 0;
    } catch (e) { /* ignore */ }

    await loadAndRender(grid);
  });

  function collectFilters() {
    const search = document.getElementById('search-input')?.value;
    const type = document.getElementById('filter-type')?.value;
    const status = document.getElementById('filter-status')?.value;
    const filters = {};
    if (search) filters.search = search;
    if (type && type !== 'all') filters.type = type;
    if (status) filters.status = status;
    return filters;
  }

  async function loadAndRender(grid) {
    const filters = collectFilters();
    grid.innerHTML = '<div class="loading">Loading properties…</div>';
    const props = await window.MWAROKIN_PROPERTIES.getProperties(filters);

    const countEl = document.getElementById('result-count');
    const noResults = document.getElementById('no-results');

    grid.innerHTML = '';
    if (!props.length) {
      if (noResults) noResults.classList.remove('hidden');
      if (countEl) countEl.textContent = '0 properties';
      return;
    }
    if (noResults) noResults.classList.add('hidden');
    if (countEl) countEl.textContent = props.length + ' propert' + (props.length === 1 ? 'y' : 'ies');
    props.forEach(function (p) { grid.appendChild(window.MWAROKIN_PROPERTIES.renderCard(p)); });

    // Re-render in the selected currency
    if (window.MWAROKIN_CURRENCY) {
      window.MWAROKIN_CURRENCY.onChange(function () {
        const ccy = window.MWAROKIN_CURRENCY.current;
        props.forEach(function (p, i) {
          const card = grid.children[i];
          if (!card) return;
          const priceEl = card.querySelector('.pcard-price');
          if (priceEl) {
            priceEl.innerHTML = window.MWAROKIN_CURRENCY.format(
              window.MWAROKIN_CURRENCY.convert(p.price, 'KES', ccy), ccy) + '<small> / month</small>';
          }
        });
      });
    }
  }

  // Wire search + filter controls
  function bindSearch() {
    const grid = document.getElementById('properties-grid');
    if (!grid) return;
    const run = function () { loadAndRender(grid); };

    const btn = document.getElementById('search-btn');
    if (btn) btn.addEventListener('click', function (e) { e.preventDefault(); run(); });
    ['filter-type', 'filter-status'].forEach(function (id) {
      const el = document.getElementById(id);
      if (el) el.addEventListener('change', run);
    });
    const input = document.getElementById('search-input');
    if (input) input.addEventListener('keydown', function (e) { if (e.key === 'Enter') run(); });
  }
  document.addEventListener('DOMContentLoaded', bindSearch);
})();