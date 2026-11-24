// sw.js — the installable Besorah.
//
// Once the site has been opened over http(s), this worker keeps the pages,
// styles, scripts and fonts on the device, and every book that has been
// read (or searched, or saved from the "Aa" panel) — so the reader works
// with no connection, the same as the single-file offline edition.
//
//   pages, scripts, styles, the index, the books — served from the cache at
//     once and refreshed from the network behind the scenes, so a correction
//     to the text arrives on the next visit;
//   fonts and icons — cache first; they never change under the same name;
//   SCRIPTURE/*.pdf — always from the network; far too large to keep.
//
// Bump VERSION when the list below changes.
var VERSION = "besorah-v4";
var SHELL = [
  "./",
  "index.html",
  "books.html",
  "book.html",
  "chapter.html",
  "search.html",
  "manifest.webmanifest",
  "assets/style.css",
  "assets/index.json",
  "assets/DailyBread.js",
  "assets/besorah-fullscreen.js",
  "assets/besorah-home.js",
  "assets/besorah-ids.js",
  "assets/besorah-marks.js",
  "assets/besorah-nav.js",
  "assets/besorah-search.js",
  "assets/besorah-tts.js",
  "assets/besorah-ui.js",
  "assets/pronunciation.js",
  "assets/words.js",
  "assets/fonts/cardo-latin-400-italic.woff2",
  "assets/fonts/cardo-latin-400-normal.woff2",
  "assets/fonts/cardo-latin-700-normal.woff2",
  "assets/fonts/cardo-latin-ext-400-italic.woff2",
  "assets/fonts/cardo-latin-ext-400-normal.woff2",
  "assets/fonts/cardo-latin-ext-700-normal.woff2",
  "assets/icons/icon-180.png",
  "assets/icons/icon-192.png",
  "assets/icons/icon-512.png",
  "assets/icons/icon-maskable-512.png"
];

self.addEventListener("install", function (e) {
  e.waitUntil(caches.open(VERSION).then(function (c) { return c.addAll(SHELL); })
    .then(function () { return self.skipWaiting(); }));
});

self.addEventListener("activate", function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k !== VERSION; })
      .map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

self.addEventListener("fetch", function (e) {
  var req = e.request;
  if (req.method !== "GET") return;
  var url = new URL(req.url);
  if (url.origin !== location.origin) return;
  if (/\/SCRIPTURE\//.test(url.pathname) || /\.pdf$/i.test(url.pathname)) return;

  // A page is one page whatever its ?id=&ch= — chapter.html renders them all.
  var key = req.mode === "navigate" ? new Request(url.pathname) : req;

  if (/\/assets\/(fonts|icons)\//.test(url.pathname)) {
    e.respondWith(caches.match(key).then(function (hit) {
      return hit || fetch(req).then(function (res) {
        var copy = res.clone();
        caches.open(VERSION).then(function (c) { c.put(key, copy); });
        return res;
      });
    }));
    return;
  }

  e.respondWith(caches.open(VERSION).then(function (c) {
    return c.match(key, { ignoreSearch: req.mode === "navigate" }).then(function (hit) {
      var net = fetch(req).then(function (res) {
        if (res && res.ok) c.put(key, res.clone());
        return res;
      }).catch(function () { return hit; });
      if (hit) { e.waitUntil(net); return hit; }
      return net;
    });
  }));
});
