/**
 * Mwarokin Estates — Property Detail Page Module
 * Renders a single property (property.html?id=...), counts the view, and lets
 * the visitor enquire via WhatsApp/contact channels.
 */
(function () {
  const sb = window.supabaseClient;
  if (!sb) return;

  document.addEventListener('DOMContentLoaded', async function () {
    const container = document.getElementById('property-detail');
    if (!container) return; // not property.html

    const params = new URLSearchParams(window.location.search);
    const id = params.get('id');
    if (!id) {
      container.innerHTML = '<p class="empty">No property selected.</p>';
      return;
    }

    const prop = await window.MWAROKIN_PROPERTIES.getProperty(id);
    if (!prop) {
      container.innerHTML = '<p class="empty">Property not found or was removed.</p>';
      return;
    }

    window.MWAROKIN_PROPERTIES.incrementViews(id);
    window.MWAROKIN_PROPERTIES.renderPropertyDetail(prop, container);
    document.title = prop.title + ' | Mwarokin Estates';

    // Re-render price on currency change
    if (window.MWAROKIN_CURRENCY) {
      window.MWAROKIN_CURRENCY.onChange(function () {
        window.MWAROKIN_PROPERTIES.renderPropertyDetail(prop, container);
      });
    }

    // Enquire / share buttons
    const enquire = document.getElementById('pdetail-enquire');
    if (enquire) {
      enquire.addEventListener('click', function () {
        const text = 'Hello! I am interested in "' + prop.title + '" at ' + prop.location + ' (' + prop.price + ' KES/month).';
        const wa = 'https://wa.me/?text=' + encodeURIComponent(text);
        window.open(wa, '_blank');
      });
    }
  });
})();