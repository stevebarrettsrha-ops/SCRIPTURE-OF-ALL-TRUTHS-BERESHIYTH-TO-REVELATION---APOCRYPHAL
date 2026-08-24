// besorah-nav.js
//
// Soft navigation between the reader pages (index, books, book, chapter):
// a click on a link to one of them fetches the target page and swaps its
// title, styles and <body> into this same document instead of letting the
// browser navigate. Leaving the document is what drops the browser out of
// fullscreen, so a reader in fullscreen keeps it wherever they go — the
// same reason the offline edition routes with hashes. It also makes every
// page change quicker, since the stylesheets and scripts already loaded
// stay loaded.
//
// Native navigation is kept for everything else: modified clicks (new
// tab), target="_blank" links (the PDFs), downloads, in-page anchors,
// links to other directories (Extra Features, SCRIPTURE), other origins,
// and browsers without the needed APIs. If a soft load fails, the page
// falls back to a real navigation rather than stranding the reader.
//
// Contract with the pages: each page's inline script is wrapped in an
// IIFE (so re-running it never redeclares top-level bindings) and wires
// listeners only to elements inside <body> — the swap replaces those
// elements, so their listeners go with them. Window/document-level
// history handling lives here and only here. Script-injected body nodes
// that must survive a swap (the fullscreen button, the mark popup) are
// carried over by the KEEP list below.
(function (global) {
  "use strict";

  var doc = global.document;
  if (!global.fetch || !global.DOMParser || !global.URL ||
      !global.history || !history.pushState ||
      !Element.prototype.closest) return;

  var PAGES = ["index.html", "books.html", "book.html", "chapter.html"];
  var KEEP = ".fs-btn, .mark-pop";
  var dir = location.pathname.replace(/[^/]*$/, "");

  // Where we are, ignoring the hash — used to tell a hash-only history
  // move (handled natively) from a real page change.
  var current = location.pathname + location.search;

  // The page we hard-loaded owns whatever <style> sits in head now; mark
  // it so the first swap away replaces it like any later one.
  (function () {
    var styles = doc.querySelectorAll("head style");
    for (var i = 0; i < styles.length; i++) {
      styles[i].setAttribute("data-page-style", "");
    }
  })();

  // Resolves href to a URL this router should handle, or null.
  function softTarget(href) {
    if (!href) return null;
    var url;
    try { url = new URL(href, location.href); } catch (e) { return null; }
    if (url.origin !== location.origin) return null;
    if (url.pathname === dir) return url;             // bare directory -> index
    if (url.pathname.replace(/[^/]*$/, "") !== dir) return null;
    var name = url.pathname.slice(dir.length);
    return PAGES.indexOf(name) === -1 ? null : url;
  }

  // ---- the swap ---------------------------------------------------------

  // Scripts adopted from a DOMParser document never execute, so they are
  // pulled out of the parsed page and re-created: external ones loaded
  // once each (in order), inline ones re-run on every visit.
  function extractScripts(parsed) {
    var externals = [], inline = [];
    var scripts = parsed.querySelectorAll("script");
    for (var i = 0; i < scripts.length; i++) {
      var s = scripts[i];
      if (s.src) externals.push(s.src);
      else if (s.textContent) inline.push(s.textContent);
      s.parentNode.removeChild(s);
    }
    return { externals: externals, inline: inline };
  }

  function loadExternals(list, done) {
    var have = {};
    for (var i = 0; i < doc.scripts.length; i++) have[doc.scripts[i].src] = 1;
    (function next(i) {
      while (i < list.length && have[list[i]]) i++;
      if (i >= list.length) { done(); return; }
      have[list[i]] = 1;
      var s = doc.createElement("script");
      // A script that fails to fetch must not strand the page half-built;
      // the modules all degrade gracefully when a sibling is absent.
      s.onload = s.onerror = function () { next(i + 1); };
      s.src = list[i];
      doc.head.appendChild(s);
    })(0);
  }

  function swapStyles(parsed) {
    var i, live = doc.querySelectorAll("head style[data-page-style]");
    for (i = 0; i < live.length; i++) live[i].parentNode.removeChild(live[i]);
    var styles = parsed.querySelectorAll("head style");
    for (i = 0; i < styles.length; i++) {
      var st = doc.createElement("style");
      st.setAttribute("data-page-style", "");
      st.textContent = styles[i].textContent;
      doc.head.appendChild(st);
    }
    // A stylesheet the incoming page has and this document does not (the
    // home page's extra font, say) is added plainly — we are past first
    // paint, so the load-without-blocking trick is not needed.
    var have = {};
    var links = doc.querySelectorAll("head link[rel~='stylesheet']");
    for (i = 0; i < links.length; i++) have[links[i].href] = 1;
    var incoming = parsed.querySelectorAll("head link[rel~='stylesheet']");
    for (i = 0; i < incoming.length; i++) {
      if (have[incoming[i].href]) continue;
      have[incoming[i].href] = 1;
      var ln = doc.createElement("link");
      ln.rel = "stylesheet";
      ln.href = incoming[i].href;
      doc.head.appendChild(ln);
    }
  }

  function swapBody(parsed) {
    if (global.speechSynthesis) global.speechSynthesis.cancel();
    var keep = doc.querySelectorAll(KEEP);
    var body = doc.body;
    body.innerHTML = "";
    while (parsed.body.firstChild) body.appendChild(parsed.body.firstChild);
    for (var i = 0; i < keep.length; i++) body.appendChild(keep[i]);
    global.scrollTo(0, 0);
  }

  function runInline(inline) {
    for (var i = 0; i < inline.length; i++) {
      var s = doc.createElement("script");
      s.textContent = inline[i];
      doc.body.appendChild(s);
    }
  }

  // ---- navigation -------------------------------------------------------

  var seq = 0;   // stale-response guard for rapid navigation

  function load(href) {
    var my = ++seq;
    current = location.pathname + location.search;
    fetch(href)
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.text();
      })
      .then(function (html) {
        if (my !== seq) return;
        var parsed = new DOMParser().parseFromString(html, "text/html");
        var scripts = extractScripts(parsed);
        doc.title = parsed.title;
        swapStyles(parsed);
        swapBody(parsed);
        loadExternals(scripts.externals, function () {
          if (my !== seq) return;
          runInline(scripts.inline);
        });
      })
      .catch(function () {
        if (my === seq) location.reload();
      });
  }

  doc.addEventListener("click", function (e) {
    if (e.defaultPrevented) return;          // a page script handled it
    if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var a = e.target.closest ? e.target.closest("a[href]") : null;
    if (!a) return;
    if (a.target && a.target !== "_self") return;
    if (a.hasAttribute("download")) return;
    var url = softTarget(a.getAttribute("href"));
    if (!url) return;
    // In-page anchors scroll natively.
    if (url.pathname === location.pathname && url.search === location.search &&
        url.hash) return;
    e.preventDefault();
    history.pushState(null, "", url.href);
    load(url.href);
  });

  global.addEventListener("popstate", function () {
    // Hash-only moves (in-page anchors) are the browser's to restore.
    if (location.pathname + location.search === current) return;
    load(location.href);
  });

  global.BesorahNav = {
    // A page doing its own pushState (the chapter page turns in place)
    // reports it here so a later popstate is measured against the right
    // starting point.
    note: function () { current = location.pathname + location.search; }
  };
})(window);
