/**
 * Mwarokin Estates — Home Page Module
 * Renders featured properties + search/filter on index.html.
 */
(function () {
  const sb = window.supabaseClient;
  if (!sb) return;

  document.addEventListener('DOMContentLoaded', async function () {
    const grid = document.getElementById('featured-grid');
    if (!grid) return; // not index.html

    const stats = await window.MWAROKIN_PROPERTIES.getFeaturedCount();
    const stat = document.getElementById('stat-count');
    if (stat) stat.textContent = stats;

    const filters = collectFilters();
    const props = await window.MWAROKIN_PROPERTIES.getProperties(filters);
    grid.innerHTML = '';
    if (!props.length) {
      grid.innerHTML = '<p class="empty" style="grid-column:1/-1;text-align:center">No properties match your search. Try widening filters.</p>';
      return;
    }
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
  });

  function collectFilters() {
    const search = document.getElementById('home-search')?.value;
    const type = document.getElementById('home-type')?.value;
    const status = document.getElementById('home-status')?.value;
    const filters = {};
    if (search) filters.search = search;
    if (type) filters.type = type;
    if (status) filters.status = status;
    return filters;
  }

  // Re-run search on filter change
  function bindSearch() {
    ['home-search', 'home-type', 'home-status'].forEach(function (id) {
      const el = document.getElementById(id);
      if (el) {
        el.addEventListener('change', function () {
          const grid = document.getElementById('featured-grid');
          grid.innerHTML = '<div class="loading">Loading properties…</div>';
          document.dispatchEvent(new CustomEvent('mw:home-reload'));
          // Reuse the full bootstrapped handler by reloading page data without nav flash
          window.MWAROKIN_PROPERTIES.getProperties(collectFilters()).then(function (props) {
            grid.innerHTML = '';
            if (!props.length) {
              grid.innerHTML = '<p class="empty" style="grid-column:1/-1;text-align:center">No properties match your search.</p>';
              return;
            }
            props.forEach(function (p) { grid.appendChild(window.MWAROKIN_PROPERTIES.renderCard(p)); });
          });
        });
      }
    });
  }
  document.addEventListener('DOMContentLoaded', bindSearch);
})();