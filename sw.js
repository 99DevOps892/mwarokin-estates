/* Mwarokin Estates · Service Worker (PWA)
   Umbrella: Syllogism Technology Africa
   Strategy: network-first for navigation, stale-while-revalidate for assets.
   Bump VERSION to force cache refresh. */
var VERSION = 'mwarokin-v1.0.0';
var SHELL = [
  './',
  './index.html',
  './Login.html',
  './register.html',
  './legacy-index.html',
  './css/app.css',
  './js/app.js',
  './js/config.js',
  './js/supabase-client.js',
  './manifest.json',
  './img/pwa-192.png',
  './img/pwa-512.png'
];

self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(VERSION).then(function (cache) {
      return cache.addAll(SHELL).catch(function () {});
    }).then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) { return k !== VERSION; }).map(function (k) { return caches.delete(k); }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function (event) {
  var req = event.request;
  if (req.method !== 'GET') return;

  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req).then(function (res) {
        var copy = res.clone();
        caches.open(VERSION).then(function (c) { c.put(req, copy); });
        return res;
      }).catch(function () {
        return caches.match(req).then(function (hit) { return hit || caches.match('./index.html'); });
      })
    );
    return;
  }

  event.respondWith(
    caches.match(req).then(function (hit) {
      var fetched = fetch(req).then(function (res) {
        var copy = res.clone();
        caches.open(VERSION).then(function (c) { c.put(req, copy); });
        return res;
      }).catch(function () { return hit; });
      return hit || fetched;
    })
  );
});