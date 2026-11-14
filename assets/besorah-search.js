// besorah-search.js
//
// Find a verse or a phrase anywhere in the 104 books.
//
//   BesorahSearch.mount(container, env)
//     env.getIndex()            -> Promise of assets/index.json
//     env.getBook(id)           -> Promise of assets/text/<id>.json
//     env.chapterUrl(id, ch, v) -> link to a verse
//     env.query / env.onQuery   -> the starting query, and a hook that is
//                                  told each new one (to keep it in the URL)
//
// Matching ignores case, the diacritics of the transliteration (ḇ, ḥ, ĕ …)
// and the kind of apostrophe, so "yaaqob", "Ya'aqoḇ" and "Ya‛aqoḇ" all find
// the same name. Words are matched as given, in order; "quotes" are not
// needed for a phrase. Text is searched as the page shows it — after the
// word-form repairs of words.js — with the HTML stripped.
//
// A query that names a place — "Bereshith 1:1", "John 3:16", "Tehillim 23"
// — is offered as a "Go to" link above the results.
(function (global) {
  "use strict";

  var doc = global.document;
  var SECTIONS = [
    ["", "All books"], ["Torah", "Torah"], ["Nabi'im", "Nabi'im — Prophets"],
    ["Kethubim", "Kethubim — Writings"], ["Messianic", "Messianic Writings"],
    ["Apocryphal", "Apocryphal Books"], ["Patriarchs", "Testaments of the Patriarchs"],
    ["Apocrypha", "Ethiopic & Eastern Apocrypha"]
  ];
  var PAGE = 100;

  // Fold one string, keeping a map from each folded character back to its
  // position in the original, so a hit can be highlighted in place.
  function fold(s) {
    var out = "", map = [];
    for (var i = 0; i < s.length; i++) {
      var c = s.charAt(i);
      var f = c.normalize ? c.normalize("NFD").replace(/[̀-ͯ]/g, "") : c;
      f = f.toLowerCase().replace(/[’‘‛ʼ´`'"“”]/g, "");
      if (/\s/.test(f)) f = " ";
      for (var j = 0; j < f.length; j++) {
        if (f === " " && out.charAt(out.length - 1) === " ") continue;
        out += f.charAt(j);
        map.push(i);
      }
    }
    return { s: out, map: map };
  }
  // The same folding without the position map, for scanning every verse.
  var MARKS = /[\u0300-\u036f]/g, APOS = /[’‘‛ʼ´`'"“”]/g;
  function fastFold(s) {
    return (s.normalize ? s.normalize("NFD") : s).replace(MARKS, "").toLowerCase()
      .replace(APOS, "").replace(/\s+/g, " ");
  }
  function foldQ(q) {
    return fold(q).s.replace(/[^a-z0-9 \-]/g, " ").replace(/\s+/g, " ").trim();
  }
  function plain(raw) {
    var t = global.BesorahWords ? global.BesorahWords.repair(raw) : raw;
    return t.replace(/<span class="fn">[\s\S]*?<\/span>/g, "")
      .replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
  }
  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function Engine(env) {
    this.env = env;
    this.books = null;      // [{book, verses:[{c, n, t, f}]}] once loaded
    this.loading = null;
  }
  Engine.prototype.load = function (progress) {
    var self = this;
    if (this.loading) return this.loading;
    this.loading = this.env.getIndex().then(function (idx) {
      self.index = idx;
      var done = 0, list = idx.books;
      // A few at a time: quick on a good connection, kind to a slow one.
      var out = new Array(list.length), next = 0;
      return new Promise(function (resolve) {
        function pump() {
          if (next >= list.length) return;
          var k = next++;
          Promise.resolve(self.env.getBook(list[k].id)).then(function (data) {
            var vs = [];
            var chs = data && data.chapters ? Object.keys(data.chapters) : [];
            chs.sort(function (a, b) { return a - b; });
            chs.forEach(function (c) {
              data.chapters[c].verses.forEach(function (v) {
                var t = plain(v.t);
                vs.push({ c: +c, n: v.n, t: t, f: null });
              });
            });
            out[k] = { book: list[k], verses: vs };
          }, function () { out[k] = { book: list[k], verses: [] }; }).then(function () {
            done++;
            if (progress) progress(done, list.length);
            if (done === list.length) resolve(out);
            else pump();
          });
        }
        for (var i = 0; i < 6; i++) pump();
      });
    }).then(function (books) { self.books = books; return books; });
    return this.loading;
  };
  // Every match, in canonical order.
  Engine.prototype.find = function (q, section) {
    var words = foldQ(q);
    if (!words) return [];
    var hits = [];
    for (var b = 0; b < this.books.length; b++) {
      var B = this.books[b];
      if (section && B.book.section !== section) continue;
      for (var i = 0; i < B.verses.length; i++) {
        var v = B.verses[i];
        if (v.f == null) v.f = fastFold(v.t);
        var at = v.f.indexOf(words);
        if (at !== -1) hits.push({ book: B.book, v: v, at: at, len: words.length });
      }
    }
    return hits;
  };

  // "Bereshith 1:1", "1 Shamu'Al 3", "John 3:16-18" -> a place to go.
  function parseRef(q, idx) {
    var m = /^\s*(.+?)\s+(\d+)(?:\s*[:.]\s*(\d+))?(?:\s*-\s*\d+)?\s*$/.exec(q);
    var name = m ? m[1] : q, ch = m ? +m[2] : 1, v = m && m[3] ? +m[3] : null;
    var key = foldQ(name).replace(/[\s\-]/g, "");
    if (!key || !idx) return null;
    var best = null;
    idx.books.forEach(function (b) {
      var names = [b.hebrew, b.english, b.id];
      for (var i = 0; i < names.length; i++) {
        var k = foldQ(names[i]).replace(/[\s\-]/g, "");
        if (k === key) { best = b; return; }
      }
    });
    if (!best) return null;
    if (!m) return { book: best, ch: 1, v: null };
    if (ch < 1 || ch > best.chapter_count) return null;
    return { book: best, ch: ch, v: v };
  }

  function snippet(hit) {
    var t = hit.v.t, map = fold(t).map;
    var s = map[hit.at], e = map[Math.min(hit.at + hit.len - 1, map.length - 1)] + 1;
    var from = 0, to = t.length;
    if (t.length > 260) {
      from = Math.max(0, s - 110);
      to = Math.min(t.length, e + 130);
      if (from > 0) from = t.indexOf(" ", from) + 1;
    }
    return (from > 0 ? "… " : "") + esc(t.slice(from, s)) + "<mark>" + esc(t.slice(s, e)) + "</mark>" +
      esc(t.slice(e, to)) + (to < t.length ? " …" : "");
  }

  function mount(box, env) {
    var engine = new Engine(env);
    var ui = global.BesorahUI;
    var name = function (b) { return ui ? ui.titleCase(b.hebrew) : b.hebrew; };
    box.innerHTML =
      '<form class="srch-form" role="search">' +
      '<label class="srch-l" for="srch-q">Find a verse or phrase</label>' +
      '<div class="srch-row"><input id="srch-q" type="search" autocomplete="off" ' +
      'placeholder="e.g. shalom, “the Word was”, Bereshith 1:1" aria-describedby="srch-status">' +
      '<button type="submit">Search</button></div>' +
      '<div class="srch-row srch-opts"><label>In <select id="srch-sec"></select></label></div>' +
      "</form>" +
      '<p class="srch-status note" id="srch-status" role="status" aria-live="polite"></p>' +
      '<div class="srch-go"></div><ol class="srch-results"></ol>' +
      '<p class="srch-more-wrap"><button type="button" class="srch-more" hidden>Show more</button></p>';
    var input = box.querySelector("#srch-q"), sec = box.querySelector("#srch-sec");
    var status = box.querySelector(".srch-status"), list = box.querySelector(".srch-results");
    var more = box.querySelector(".srch-more"), go = box.querySelector(".srch-go");
    SECTIONS.forEach(function (s) {
      var o = doc.createElement("option");
      o.value = s[0]; o.textContent = s[1];
      sec.appendChild(o);
    });
    var hits = [], shown = 0, seq = 0;

    function render(n) {
      var frag = doc.createDocumentFragment();
      for (var i = shown; i < Math.min(hits.length, shown + n); i++) {
        var h = hits[i], li = doc.createElement("li");
        var ref = name(h.book) + " " + h.v.c + ":" + h.v.n;
        li.innerHTML = '<a href="' + esc(env.chapterUrl(h.book.id, h.v.c, h.v.n)) + '">' +
          '<span class="srch-ref">' + esc(ref) + '</span> <span class="srch-eng">(' + esc(h.book.english) + ")</span></a>" +
          '<div class="srch-t">' + snippet(h) + "</div>";
        frag.appendChild(li);
      }
      shown = Math.min(hits.length, shown + n);
      list.appendChild(frag);
      more.hidden = shown >= hits.length;
    }

    function run() {
      var q = input.value.trim(), my = ++seq;
      if (env.onQuery) env.onQuery(q);
      list.innerHTML = ""; go.innerHTML = ""; hits = []; shown = 0; more.hidden = true;
      if (!q) { status.textContent = ""; return; }
      env.getIndex().then(function (idx) {
        var r = parseRef(q, idx);
        if (r && my === seq) {
          go.innerHTML = '<a class="srch-goto" href="' + esc(env.chapterUrl(r.book.id, r.ch, r.v)) + '">Go to ' +
            esc(name(r.book) + (r.book.chapter_count > 1 || r.v ? " " + r.ch + (r.v ? ":" + r.v : "") : "")) + " →</a>";
        }
      });
      if (foldQ(q).length < 2) { status.textContent = "Type at least two letters."; return; }
      status.textContent = engine.books ? "Searching…" : "Opening the books…";
      engine.load(function (d, n) {
        if (my === seq && d < n) status.textContent = "Opening the books… " + d + " of " + n;
      }).then(function () {
        if (my !== seq) return;
        hits = engine.find(q, sec.value);
        var books = {};
        hits.forEach(function (h) { books[h.book.id] = 1; });
        status.textContent = hits.length
          ? hits.length.toLocaleString() + " verse" + (hits.length === 1 ? "" : "s") + " in " +
            Object.keys(books).length + " book" + (Object.keys(books).length === 1 ? "" : "s")
          : "No verses found. Try fewer words, or the Hebrew form (shamayim, not heaven).";
        render(PAGE);
      });
    }

    box.querySelector("form").addEventListener("submit", function (e) { e.preventDefault(); run(); });
    sec.addEventListener("change", run);
    more.addEventListener("click", function () { render(PAGE); });
    var t = null;
    input.addEventListener("input", function () { clearTimeout(t); t = setTimeout(run, 350); });
    if (env.query) { input.value = env.query; run(); }
    return { focus: function () { input.focus(); }, set: function (q) { input.value = q || ""; run(); } };
  }

  global.BesorahSearch = { mount: mount, fold: fold, parseRef: parseRef };
})(typeof window !== "undefined" ? window : this);
