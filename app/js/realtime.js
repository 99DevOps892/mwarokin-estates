/**
 * Mwarokin Estates — Realtime Module
 * Central manager for Supabase Realtime subscriptions. Only created on pages
 * that need live updates (dashboard, admin). Removes channels on page unload.
 */
(function () {
  const sb = window.supabaseClient;
  if (!sb) return;

  const channels = [];

  window.MWAROKIN_REALTIME = {
    subscribeToTable,
    removeAll,
    channels
  };

  /**
   * Subscribe to changes on a table.
   * @param {string} table
   * @param {Function} callback  (payload) => void
   * @param {Object} [options]   { filter, event }
   */
  function subscribeToTable(table, callback, options) {
    options = options || {};
    const channel = sb
      .channel('mw-' + table + '-' + Date.now())
      .on('postgres_changes', {
        event: options.event || '*',
        schema: 'public',
        table: table,
        ...(options.filter ? { filter: options.filter } : {})
      }, function (payload) {
        try { callback(payload); } catch (e) { console.error('realtime callback error:', e); }
      })
      .subscribe();

    channels.push(channel);
    return channel;
  }

  function removeAll() {
    channels.forEach(function (ch) {
      try { sb.removeChannel(ch); } catch (e) {}
    });
    channels.length = 0;
  }

  window.addEventListener('beforeunload', removeAll);
})();