/**
 * Service Worker for Auto Trading Analyzer PWA
 *
 * Strategy:
 *  - Static assets (HTML, CSS, JS, icons): cache-first with background update
 *  - API / data calls (RSS feeds, yfinance): network-first with cache fallback
 */

const CACHE_NAME = 'auto-trade-v2';
const STATIC_CACHE = 'auto-trade-static-v2';
const DATA_CACHE = 'auto-trade-data-v2';

// Static assets to pre-cache on install (relative paths for cross-browser compat)
const PRECACHE_ASSETS = [
  './',
  './index.html',
  './css/styles.css',
  './js/config.js',
  './js/sentiment.js',
  './js/companies.js',
  './js/themes.js',
  './js/technicals.js',
  './js/signals.js',
  './js/analyzer.js',
  './js/news.js',
  './js/portfolio.js',
  './js/app.js',
  './manifest.json',
  './icons/icon.svg',
  './icons/icon-192x192.png',
  './icons/icon-512x512.png',
  './icons/apple-touch-icon.png',
  './icons/favicon.ico',
];

// ---- Install: pre-cache static assets ----
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      return cache.addAll(PRECACHE_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

// ---- Activate: clean up old caches ----
self.addEventListener('activate', (event) => {
  const currentCaches = [STATIC_CACHE, DATA_CACHE];
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => !currentCaches.includes(name))
          .map((name) => caches.delete(name))
      );
    }).then(() => self.clients.claim())
  );
});

// ---- Fetch: route requests to the right strategy ----
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Skip non-GET requests
  if (event.request.method !== 'GET') return;

  // Skip cross-origin requests that aren't fonts/CDN
  if (url.origin !== self.location.origin &&
      !url.hostname.includes('googleapis.com') &&
      !url.hostname.includes('gstatic.com')) {
    return;
  }

  // Data/API requests — network-first
  if (isDataRequest(url)) {
    event.respondWith(networkFirst(event.request, DATA_CACHE));
    return;
  }

  // Static assets — cache-first with background update (stale-while-revalidate)
  event.respondWith(staleWhileRevalidate(event.request, STATIC_CACHE));
});

// ---- Helpers ----

function isDataRequest(url) {
  // RSS feeds, finance APIs, etc.
  return (
    url.pathname.includes('/rss') ||
    url.hostname.includes('finance.yahoo.com') ||
    url.hostname.includes('news.google.com') ||
    url.hostname.includes('feeds.') ||
    url.pathname.endsWith('.json') && !url.pathname.includes('manifest')
  );
}

async function networkFirst(request, cacheName) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (err) {
    const cached = await caches.match(request);
    if (cached) return cached;
    // Return a minimal offline response for data requests
    return new Response(
      JSON.stringify({ offline: true, error: 'No network connection' }),
      { headers: { 'Content-Type': 'application/json' } }
    );
  }
}

async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);

  // Kick off a background fetch to update the cache
  const fetchPromise = fetch(request).then((networkResponse) => {
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  }).catch(() => null);

  // Return cached version immediately, or wait for network
  return cached || fetchPromise || new Response('Offline', { status: 503 });
}
