/* Mwarokin Estates · Production Service Worker (PWA)
   Umbrella: Syllogism Technology Africa
   Strategy: network-first for navigation + API, stale-while-revalidate for static.
   Offline fallback for payment pages. Cache-first for images.
   Bump VERSION to force cache refresh across all clients. */
var VERSION = 'mwarokin-v2.0.0';
var STATIC_CACHE = VERSION + '-static';
var DYNAMIC_CACHE = VERSION + '-dynamic';
var IMAGE_CACHE = VERSION + '-images';

var SHELL = [
  './',
  './index.html',
  './login.html',
  './register.html',
  './dashboard.html',
  './css/style.css',
  './js/config.js',
  './js/supabase-client.js',
  './js/auth.js',
  './js/payments.js',
  './js/payment-poller.js',
  './js/i18n.js',
  './js/currency.js',
  './manifest.json'
];

var OFFLINE_FALLBACK = './index.html';

self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(STATIC_CACHE).then(function (cache) {
      return cache.addAll(SHELL);
    }).then(function () {
      return self.skipWaiting();
    })
  );
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(
        keys
          .filter(function (k) { return k.indexOf(VERSION) !== 0; })
          .map(function (k) { return caches.delete(k); })
      );
    }).then(function () {
      return self.clients.claim();
    })
  );
});

self.addEventListener('fetch', function (event) {
  var req = event.request;
  if (req.method !== 'GET') return;

  var url = new URL(req.url);

  // Skip Supabase API calls — always go to network
  if (url.hostname.indexOf('supabase') !== -1) return;

  // Skip external CDN resources — network only
  if (url.origin !== self.location.origin && !url.pathname.startsWith('/mwarokin-estates/')) return;

  // Navigation: network-first with offline fallback
  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req).then(function (res) {
        var copy = res.clone();
        caches.open(DYNAMIC_CACHE).then(function (c) { c.put(req, copy); });
        return res;
      }).catch(function () {
        return caches.match(req).then(function (hit) {
          return hit || caches.match(OFFLINE_FALLBACK);
        });
      })
    );
    return;
  }

  // Images: cache-first (offline-friendly)
  if (req.destination === 'image' || url.pathname.match(/\.(png|jpg|jpeg|gif|svg|webp|ico)$/i)) {
    event.respondWith(
      caches.open(IMAGE_CACHE).then(function (cache) {
        return cache.match(req).then(function (hit) {
          if (hit) return hit;
          return fetch(req).then(function (res) {
            if (res.ok) cache.put(req, res.clone());
            return res;
          }).catch(function () { return new Response('', { status: 404 }); });
        });
      })
    );
    return;
  }

  // Static assets (CSS, JS): stale-while-revalidate
  event.respondWith(
    caches.open(STATIC_CACHE).then(function (cache) {
      return cache.match(req).then(function (hit) {
        var fetched = fetch(req).then(function (res) {
          if (res.ok) {
            var copy = res.clone();
            cache.put(req, copy);
          }
          return res;
        }).catch(function () { return hit; });
        return hit || fetched;
      });
    })
  );
});

// Listen for messages from the page (e.g., skip waiting)
self.addEventListener('message', function (event) {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
