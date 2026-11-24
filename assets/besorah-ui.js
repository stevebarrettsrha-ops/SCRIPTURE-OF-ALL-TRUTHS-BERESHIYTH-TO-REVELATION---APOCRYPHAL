// besorah-ui.js
//
// The reader's comforts, on every page and in the offline edition alike:
//
//   * Appearance — Dark, Light or Sepia, or follow the device; text size;
//     and a compact reading mode. Kept on this device (localStorage), and
//     applied before first paint by the one-line snippet in each <head>.
//   * Turning chapters — ← / → keys and a horizontal swipe on the text.
//   * Go to — a book-and-chapter picker opened from the chapter bar.
//   * Glossary — tap a Hebrew word (shamayim, berith, naḇi …) for what it
//     means and how to say it; the respelling comes from pronunciation.js.
//   * decorate(html) — called by the chapter renderers. It wraps the
//     "(YAHUAH) HWHY" pair, the bracketed English glosses and the Hebrew
//     vocabulary in spans so they can be styled, hidden in compact mode and
//     tapped. It never adds or removes a character of text, so marks (which
//     count characters), read-aloud and copying see exactly what they did.
//   * Installable app — registers sw.js when served over http(s).
//
// Each edition may describe itself through window.BesorahEnv before this
// file runs (the offline edition does); the defaults fit the web pages.
(function (global) {
  "use strict";

  var doc = global.document;
  var root = doc.documentElement;
  var KEY = "besorah-prefs";

  // ---- the edition ---------------------------------------------------------
  var env = global.BesorahEnv || {};
  var cache = {};
  function getIndex() {
    if (env.getIndex) return env.getIndex();
    if (!cache.index) cache.index = fetch("assets/index.json").then(function (r) { return r.json(); });
    return cache.index;
  }
  function chapterUrl(id, ch, v) {
    if (env.chapterUrl) return env.chapterUrl(id, ch, v);
    return "chapter.html?id=" + encodeURIComponent(id) + "&ch=" + ch + (v ? "&v=" + v : "");
  }
  function searchUrl(q) {
    if (env.searchUrl) return env.searchUrl(q);
    return "search.html" + (q ? "?q=" + encodeURIComponent(q) : "");
  }

  // ---- preferences ---------------------------------------------------------
  var THEMES = ["auto", "dark", "light", "sepia"];
  var THEME_COLOR = { dark: "#1a1410", light: "#fbf7ee", sepia: "#f1e4c8" };
  var SIZES = [0.85, 0.92, 1, 1.1, 1.2, 1.35, 1.5, 1.7];

  function load() {
    var p = {};
    try { p = JSON.parse(global.localStorage.getItem(KEY) || "{}") || {}; } catch (e) { p = {}; }
    if (THEMES.indexOf(p.theme) === -1) p.theme = "auto";
    p.size = +p.size || 1;
    p.compact = !!p.compact;
    return p;
  }
  var prefs = load();

  function save() {
    try { global.localStorage.setItem(KEY, JSON.stringify(prefs)); } catch (e) { /* private mode */ }
  }

  function resolvedTheme() {
    if (prefs.theme !== "auto") return prefs.theme;
    var light = global.matchMedia && global.matchMedia("(prefers-color-scheme: light)").matches;
    return light ? "light" : "dark";
  }

  function apply() {
    root.setAttribute("data-theme", prefs.theme);
    root.style.setProperty("--fs", String(prefs.size));
    root.classList.toggle("compact-reading", prefs.compact);
    var meta = doc.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", THEME_COLOR[resolvedTheme()]);
    paintPanel();
  }
  if (global.matchMedia) {
    var mq = global.matchMedia("(prefers-color-scheme: light)");
    if (mq.addEventListener) mq.addEventListener("change", apply);
    else if (mq.addListener) mq.addListener(apply);
  }

  // ---- decorate: names, glosses and Hebrew words, text untouched -------------
  // The glossary: the CLAUDE.md vocabulary, with what each word means.
  // Keys are lower case with a plain apostrophe.
  var GLOSSARY = {
    "shamayim": "heaven, the heavens",
    "ruach": "spirit, wind, breath",
    "ruchot": "spirits, winds",
    "nephesh": "soul, being, life",
    "nepheshoth": "souls, beings",
    "mal'ak": "messenger, angel",
    "mal'akim": "messengers, angels",
    "kohen": "priest",
    "kohanim": "priests",
    "kohen gadol": "high priest",
    "kohanim gedolim": "high priests",
    "kehunnah": "priesthood",
    "kohenic": "priestly",
    "berith": "covenant",
    "berithot": "covenants",
    "shalom": "peace, completeness, well-being",
    "mizbe'ach": "altar",
    "mizbe'achot": "altars",
    "mishpat": "judgment, right-ruling",
    "mishpatim": "judgments, right-rulings",
    "qahal": "assembly, congregation",
    "qahalim": "assemblies",
    "mitsvah": "command, commandment",
    "mitsvot": "commands, commandments",
    "eduth": "testimony, witness",
    "eduyot": "testimonies",
    "berakah": "blessing",
    "berakoth": "blessings",
    "baruk": "blessed",
    "chesed": "lovingkindness, mercy",
    "kippur": "atonement, covering",
    "yom kippur": "the Day of Atonement",
    "chen": "favour, grace",
    "yasha": "salvation, deliverance",
    "heykal": "temple, palace",
    "hĕḵal": "temple, palace",
    "sheol": "the grave, the underworld",
    "qadash": "set apart, holy",
    "qodash": "the set-apart place",
    "qodash haqodashim": "the most set-apart place (Holy of Holies)",
    "qadashiyms": "set-apart ones (saints)",
    "chaneph": "hypocrite, profane one",
    "chanephim": "hypocrites",
    "chasid": "faithful, devoted",
    "shabbath": "the Sabbath, the day of rest",
    "torah": "teaching, instruction, the Law",
    "pesach": "Passover",
    "sukkot": "Tabernacles, the Feast of Booths",
    "halleluyah": "Praise Yah!",
    "iḇri": "a Hebrew",
    "iḇrim": "Hebrews",
    "naḇi": "prophet",
    "naḇi'im": "prophets",
    "neḇuah": "prophecy",
    "naḇa": "to prophesy",
    "aluah": "a god, a mighty one",
    "besorah": "good news, the gospel",
    "amĕn": "so be it, truly",
    "selah": "pause, lift up (a musical direction)",
    "yahuah": "the Name — יהוה, YHWH",
    "hwhy": "the Name written in paleo-Hebrew letters (read right to left: YHWH)"
  };
  // Bracketed English the text carries after a Hebrew word: "qadash (Set
  // Apart)". These are the house-style glosses; any other bracket is part
  // of the reading and is left as it is.
  var GLOSSES = "Assemblies|Assembly|Most Set Apart Place|Set Apart Ones|Set Apart One|Set Apart Place|Set Apart|Faithful|Baḇylonians|Baḇylonian|Baḇylon";
  var GLOSS_RE = new RegExp("((?:Qodash haQodashim)|[A-Za-zÀ-ɏḀ-ỿ'’]+) \\((" + GLOSSES + ")\\)", "g");
  var TERM_KEYS = Object.keys(GLOSSARY).filter(function (k) { return k !== "yahuah" && k !== "hwhy"; })
    .sort(function (a, b) { return b.length - a.length; });
  var L = "A-Za-zÀ-ɏḀ-ỿ";
  var TERM_RE = new RegExp("(^|[^" + L + "'’])(" + TERM_KEYS.map(function (k) {
    return k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/'/g, "['’]");
  }).join("|") + ")(?![" + L + "'’])", "gi");
  var PAIR = '(<span class="dn">YAHUAH</span>) <span class="hwhy">HWHY</span>';
  var PAIR_OUT = '<span class="nm" data-k="hwhy"><span class="nm-x">(</span>' +
    '<span class="dn">YAHUAH</span><span class="nm-x">) </span>' +
    '<span class="hwhy">HWHY</span></span>';

  function keyOf(word) {
    return word.toLowerCase().replace(/’/g, "'");
  }
  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
  }

  // Only text outside the name spans is touched: the html is cut at its
  // tags, and a running depth says whether a piece sits inside a span.
  function decorateText(t) {
    // Glossed words first; the plain-word pass then runs only on the text
    // between them, so no word is wrapped twice.
    var pieces = [], last = 0, m;
    GLOSS_RE.lastIndex = 0;
    while ((m = GLOSS_RE.exec(t))) {
      pieces.push(terms(t.slice(last, m.index)));
      pieces.push('<span class="term" data-k="' + esc(keyOf(m[1])) + '" data-g="' + esc(m[2]) + '">' +
        m[1] + '</span><span class="gloss"> (' + m[2] + ")</span>");
      last = GLOSS_RE.lastIndex;
    }
    pieces.push(terms(t.slice(last)));
    return pieces.join("");
  }
  function terms(s) {
    return s.replace(TERM_RE, function (m, pre, word) {
      return pre + '<span class="term" data-k="' + esc(keyOf(word)) + '">' + word + "</span>";
    });
  }

  function decorate(html) {
    if (!html) return html;
    html = html.split(PAIR).join(PAIR_OUT);
    var parts = html.split(/(<[^>]+>)/), depth = 0;
    for (var i = 0; i < parts.length; i++) {
      var p = parts[i];
      if (!p) continue;
      if (p.charAt(0) === "<") {
        if (/^<span class="(?:dn|hwhy|fn|rs|term|gloss)"/.test(p)) depth++;
        else if (p === "</span>" && depth > 0) depth--;
        continue;
      }
      if (depth === 0) parts[i] = decorateText(p);
    }
    return parts.join("");
  }

  // ---- floating controls ---------------------------------------------------
  function el(tag, cls, html) {
    var e = doc.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }

  var btn = el("button", "ui-btn", "Aa");
  btn.type = "button";
  btn.setAttribute("aria-label", "Reading settings: theme, text size, search");
  btn.setAttribute("aria-haspopup", "dialog");
  btn.setAttribute("aria-expanded", "false");
  btn.title = "Reading settings";

  var panel = el("div", "ui-panel");
  panel.setAttribute("role", "dialog");
  panel.setAttribute("aria-label", "Reading settings");
  panel.hidden = true;
  panel.innerHTML =
    '<div class="ui-row"><span class="ui-label" id="ui-theme-l">Theme</span>' +
    '<div class="ui-seg" role="radiogroup" aria-labelledby="ui-theme-l">' +
    '<button type="button" role="radio" data-theme="auto">Device</button>' +
    '<button type="button" role="radio" data-theme="dark">Dark</button>' +
    '<button type="button" role="radio" data-theme="light">Light</button>' +
    '<button type="button" role="radio" data-theme="sepia">Sepia</button></div></div>' +
    '<div class="ui-row"><span class="ui-label">Text size</span>' +
    '<div class="ui-size"><button type="button" data-size="-1" aria-label="Smaller text">A−</button>' +
    '<output class="ui-size-v" aria-live="polite">100%</output>' +
    '<button type="button" data-size="1" aria-label="Larger text">A+</button></div></div>' +
    '<div class="ui-row"><label class="ui-check"><input type="checkbox" data-compact> ' +
    'Compact reading <small>— show YAHUAH without “HWHY”, hide the bracketed English; tap a Hebrew word for its meaning</small></label></div>' +
    '<div class="ui-row ui-save-row" hidden><button type="button" class="ui-save">⬇ Keep all 106 books on this device</button></div>' +
    '<div class="ui-row ui-links"><a data-ui-search href="#">🔍 Search the scriptures</a>' +
    '<button type="button" class="ui-close">Close</button></div>';

  var KEEP_SEL = ".ui-btn, .ui-panel, .ui-pop, .ui-toast, .qp-panel";

  function mount() {
    if (!doc.body) return;
    if (!btn.isConnected) doc.body.appendChild(btn);
    if (!panel.isConnected) doc.body.appendChild(panel);
    btn.classList.toggle("ui-btn-solo", !doc.querySelector(".fs-btn"));
  }

  function paintPanel() {
    var i, b = panel.querySelectorAll("[data-theme]");
    for (i = 0; i < b.length; i++) {
      var on = b[i].getAttribute("data-theme") === prefs.theme;
      b[i].setAttribute("aria-checked", on ? "true" : "false");
      b[i].classList.toggle("on", on);
    }
    panel.querySelector(".ui-size-v").textContent = Math.round(prefs.size * 100) + "%";
    panel.querySelector("[data-compact]").checked = prefs.compact;
    panel.querySelector("[data-ui-search]").setAttribute("href", searchUrl(""));
    // Offered once the app is installed (a service worker controls the page).
    panel.querySelector(".ui-save-row").hidden =
      !(global.navigator.serviceWorker && global.navigator.serviceWorker.controller);
  }

  // Fetching every book through the service worker leaves it in the cache.
  function saveAll(button) {
    button.disabled = true;
    getIndex().then(function (idx) {
      var ids = idx.books.map(function (b) { return b.id; }), done = 0, next = 0;
      return new Promise(function (resolve) {
        function pump() {
          if (next >= ids.length) return;
          var id = ids[next++];
          fetch("assets/text/" + id + ".json").catch(function () {}).then(function () {
            done++;
            button.textContent = "Saving… " + done + " of " + ids.length;
            if (done === ids.length) resolve(); else pump();
          });
        }
        for (var i = 0; i < 4; i++) pump();
      });
    }).then(function () {
      button.textContent = "✓ All 106 books are on this device";
      say2("All 106 books saved for offline reading");
    }, function () { button.disabled = false; button.textContent = "⬇ Try again"; });
  }

  function openPanel(open) {
    mount();
    panel.hidden = !open;
    btn.setAttribute("aria-expanded", open ? "true" : "false");
    if (open) {
      paintPanel();
      var first = panel.querySelector(".on") || panel.querySelector("button");
      if (first) first.focus();
    }
  }

  btn.addEventListener("click", function () { openPanel(panel.hidden); });
  panel.addEventListener("click", function (e) {
    var t = e.target.closest ? e.target.closest("button, a") : null;
    if (!t) return;
    if (t.hasAttribute("data-theme")) { prefs.theme = t.getAttribute("data-theme"); save(); apply(); }
    else if (t.hasAttribute("data-size")) {
      var i = SIZES.indexOf(prefs.size);
      if (i === -1) i = 2;
      i = Math.max(0, Math.min(SIZES.length - 1, i + (+t.getAttribute("data-size"))));
      prefs.size = SIZES[i]; save(); apply();
    } else if (t.classList.contains("ui-close")) { openPanel(false); btn.focus(); }
    else if (t.hasAttribute("data-ui-search")) openPanel(false);
    else if (t.classList.contains("ui-save")) saveAll(t);
  });
  panel.addEventListener("change", function (e) {
    if (e.target.hasAttribute("data-compact")) { prefs.compact = e.target.checked; save(); apply(); }
  });

  // ---- glossary pop-over -----------------------------------------------------
  var pop = el("div", "ui-pop");
  pop.setAttribute("role", "dialog");
  pop.hidden = true;

  function say(text) {
    if (!global.speechSynthesis || !global.SpeechSynthesisUtterance) return;
    global.speechSynthesis.cancel();
    var u = new global.SpeechSynthesisUtterance(text);
    u.rate = 0.85;
    global.speechSynthesis.speak(u);
  }

  function showPop(target) {
    var key = target.getAttribute("data-k");
    var shown = key === "hwhy" ? "YAHUAH · HWHY" : target.textContent;
    var meaning = GLOSSARY[key] || GLOSSARY[key.replace(/['’]/g, "")] || "";
    var gloss = target.getAttribute("data-g");
    var word = key === "hwhy" ? "Yahuah" : target.textContent;
    var spoken = global.BesorahPron && BesorahPron.wordFor
      ? word.split(/\s+/).map(BesorahPron.wordFor).join(" ") : word;
    pop.innerHTML =
      '<div class="ui-pop-w">' + esc(shown) + "</div>" +
      (meaning ? '<div class="ui-pop-m">' + esc(meaning) + "</div>" : "") +
      (gloss && (!meaning || meaning.toLowerCase().indexOf(gloss.toLowerCase()) === -1)
        ? '<div class="ui-pop-m">“' + esc(gloss) + "”</div>" : "") +
      '<div class="ui-pop-s">Say it: <b>' + esc(spoken) + "</b> " +
      (global.speechSynthesis ? '<button type="button" class="ui-say" aria-label="Hear it">🔊</button>' : "") +
      "</div>";
    pop.setAttribute("aria-label", shown + ": " + meaning);
    if (!pop.isConnected) doc.body.appendChild(pop);
    pop.hidden = false;
    var r = target.getBoundingClientRect();
    var sx = global.pageXOffset || 0, sy = global.pageYOffset || 0;
    var w = pop.offsetWidth, vw = root.clientWidth;
    var left = Math.max(8, Math.min(r.left + sx + r.width / 2 - w / 2, sx + vw - w - 8));
    var top = r.bottom + sy + 8;
    if (r.bottom + pop.offsetHeight + 16 > global.innerHeight) top = r.top + sy - pop.offsetHeight - 8;
    pop.style.left = left + "px";
    pop.style.top = top + "px";
    pop.querySelector(".ui-say") && pop.querySelector(".ui-say").addEventListener("click", function () { say(spoken); });
  }
  function hidePop() { pop.hidden = true; }

  // Capture phase, so a tap on a Hebrew word shows its meaning instead of
  // opening the verse's Mark / Start Reader menu.
  doc.addEventListener("click", function (e) {
    var t = e.target.closest ? e.target.closest(".term, .nm") : null;
    if (t && !(global.getSelection && String(global.getSelection()).length)) {
      e.preventDefault();
      e.stopPropagation();
      showPop(t);
      return;
    }
    if (!pop.hidden && !pop.contains(e.target)) hidePop();
    if (!panel.hidden && !panel.contains(e.target) && e.target !== btn) openPanel(false);
    var qp = doc.querySelector(".qp-panel");
    if (qp && !qp.hidden && !qp.contains(e.target) &&
        !(e.target.closest && e.target.closest("[data-ui-picker]"))) qp.hidden = true;
  }, true);

  // ---- toast -----------------------------------------------------------------
  var toast = el("div", "ui-toast");
  toast.setAttribute("role", "status");
  toast.setAttribute("aria-live", "polite");
  var toastT = null;
  function say2(msg) {
    if (!toast.isConnected) doc.body.appendChild(toast);
    toast.textContent = msg;
    toast.classList.add("on");
    clearTimeout(toastT);
    toastT = setTimeout(function () { toast.classList.remove("on"); }, 2200);
  }

  // ---- the quick book & chapter picker -------------------------------------
  var SECTIONS = [
    ["Torah", "Torah"], ["Nabi'im", "Nabi'im — Prophets"], ["Kethubim", "Kethubim — Writings"],
    ["Messianic", "Messianic Writings"], ["Apocryphal", "Apocryphal Books"],
    ["Patriarchs", "Testaments of the Patriarchs"], ["Apocrypha", "Ethiopic & Eastern Apocrypha"],
    ["Dead Sea Scrolls", "Dead Sea Scrolls — Additions"]
  ];
  var here = { bookId: null, chapter: null };

  function openPicker(anchor) {
    var qp = doc.querySelector(".qp-panel");
    if (!qp) {
      qp = el("div", "qp-panel");
      qp.setAttribute("role", "dialog");
      qp.setAttribute("aria-label", "Go to a book and chapter");
      qp.hidden = true;
      qp.innerHTML = '<label class="qp-l">Book <select class="qp-book"></select></label>' +
        '<div class="qp-grid" role="list"></div>';
      doc.body.appendChild(qp);
      qp.querySelector(".qp-book").addEventListener("change", function () { fill(qp, this.value); });
      qp.addEventListener("keydown", function (e) { if (e.key === "Escape") { qp.hidden = true; anchor.focus(); } });
      qp.addEventListener("click", function (e) {
        if (e.target.closest && e.target.closest("a")) qp.hidden = true;
      });
    }
    if (!qp.hidden) { qp.hidden = true; return; }
    getIndex().then(function (idx) {
      var sel = qp.querySelector(".qp-book");
      if (!sel.options.length) {
        SECTIONS.forEach(function (s) {
          var g = doc.createElement("optgroup");
          g.label = s[1];
          idx.books.forEach(function (b) {
            if (b.section !== s[0]) return;
            var o = doc.createElement("option");
            o.value = b.id;
            o.textContent = b.hebrew + " (" + b.english + ")";
            g.appendChild(o);
          });
          if (g.children.length) sel.appendChild(g);
        });
        sel._idx = idx;
      }
      sel.value = here.bookId || sel.value;
      fill(qp, sel.value);
      qp.hidden = false;
      var r = anchor.getBoundingClientRect();
      qp.style.top = (r.bottom + (global.pageYOffset || 0) + 6) + "px";
      qp.style.left = Math.max(8, Math.min(r.left + (global.pageXOffset || 0),
        (global.pageXOffset || 0) + root.clientWidth - qp.offsetWidth - 8)) + "px";
      sel.focus();
    });
  }

  function fill(qp, id) {
    var sel = qp.querySelector(".qp-book");
    var book = sel._idx.books.filter(function (b) { return b.id === id; })[0];
    var grid = qp.querySelector(".qp-grid");
    grid.innerHTML = "";
    if (!book) return;
    var first = book.first_chapter || 1;
    for (var i = first; i < first + book.chapter_count; i++) {
      var a = doc.createElement("a");
      a.href = chapterUrl(book.id, i);
      a.textContent = i;
      a.setAttribute("role", "listitem");
      a.setAttribute("aria-label", book.hebrew + " chapter " + i);
      if (book.id === here.bookId && i === here.chapter) { a.className = "on"; a.setAttribute("aria-current", "page"); }
      grid.appendChild(a);
    }
  }

  doc.addEventListener("click", function (e) {
    var t = e.target.closest ? e.target.closest("[data-ui-picker]") : null;
    if (!t) return;
    e.preventDefault();
    openPicker(t);
  });

  // ---- turning chapters: keys and swipe -------------------------------------
  function visible(e) { return e && e.offsetParent !== null; }
  function turn(dir) {
    var a = doc.getElementById(dir < 0 ? "prev" : "next");
    if (!visible(a) || a.classList.contains("disabled") || !a.getAttribute("href")) return false;
    a.click();
    return true;
  }
  function typing(t) {
    return t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable);
  }
  doc.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      if (!pop.hidden) hidePop();
      if (!panel.hidden) { openPanel(false); btn.focus(); }
      return;
    }
    if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey || typing(e.target)) return;
    if (e.key === "ArrowLeft") { if (turn(-1)) e.preventDefault(); }
    else if (e.key === "ArrowRight") { if (turn(1)) e.preventDefault(); }
  });
  var sx0 = 0, sy0 = 0, st0 = 0, swiping = false;
  doc.addEventListener("touchstart", function (e) {
    var t = e.touches[0];
    swiping = e.touches.length === 1 && !!(e.target.closest && e.target.closest(".chapter-main"));
    sx0 = t.clientX; sy0 = t.clientY; st0 = Date.now();
  }, { passive: true });
  doc.addEventListener("touchend", function (e) {
    if (!swiping) return;
    swiping = false;
    var t = e.changedTouches[0];
    var dx = t.clientX - sx0, dy = t.clientY - sy0;
    if (Date.now() - st0 > 700 || Math.abs(dx) < 80 || Math.abs(dy) > Math.abs(dx) * 0.5) return;
    if (global.getSelection && String(global.getSelection()).length) return;
    turn(dx > 0 ? -1 : 1);
  }, { passive: true });

  // ---- copy / share a verse (called from the verse menu) -------------------
  function titleCase(heb) {
    return String(heb).split(" ").map(function (w) {
      if (/^\d+$/.test(w)) return w;
      var m = /^(ha)(.+)$/.exec(w);
      if (m && m[2] === m[2].toUpperCase()) return "ha" + m[2].charAt(0) + m[2].slice(1).toLowerCase();
      return w.charAt(0) + w.slice(1).toLowerCase();
    }).join(" ");
  }
  // A book numbered on from another is cited by the shared name: Psalm 155
  // of the Dead Sea Scrolls is "Tehillim 155:3", not "Tehillim 151–174 155:3".
  function citeName(book) {
    var name = titleCase(book.hebrew);
    return book.first_chapter > 1 ? name.replace(/\s+\d+[–-]\d+$/, "") : name;
  }
  function reference(book, chapter, verse) {
    var name = citeName(book);
    if (book.chapter_count <= 1 && !verse) return name;
    return name + " " + chapter + (verse ? ":" + verse : "");
  }
  function verseLink(book, chapter, verse) {
    var rel = chapterUrl(book.id, chapter, verse);
    try { return new URL(rel, location.href).href; } catch (e) { return rel; }
  }
  // What the reader sees: no verse number or footnote, and in compact mode
  // no "(…) HWHY" around the Name and no bracketed English.
  function visibleText(host) {
    var c = host.cloneNode(true);
    var drop = ".verse-n, .fn" + (prefs.compact ? ", .nm-x, .nm .hwhy, .gloss" : "");
    var d = c.querySelectorAll(drop);
    for (var i = 0; i < d.length; i++) d[i].parentNode.removeChild(d[i]);
    return (c.textContent || "").replace(/\s+/g, " ").trim();
  }
  function copyText(text) {
    if (global.navigator.clipboard && global.isSecureContext) {
      return global.navigator.clipboard.writeText(text);
    }
    return new Promise(function (ok, fail) {
      var ta = doc.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      doc.body.appendChild(ta);
      ta.select();
      var done = false;
      try { done = doc.execCommand("copy"); } catch (e) { done = false; }
      doc.body.removeChild(ta);
      done ? ok() : fail();
    });
  }
  function shareVerse(how, info) {
    var ref = reference(info.book, info.chapter, info.verse);
    var text = info.text || (info.el ? visibleText(info.el) : "");
    if (info.text && prefs.compact) {
      text = text.replace(/\(YAHUAH\) HWHY/g, "YAHUAH")
        .replace(new RegExp(" \\((?:" + GLOSSES + ")\\)", "g"), "");
    }
    var url = verseLink(info.book, info.chapter, info.verse);
    var body = "“" + text + "” — " + ref + " (The Besorah)";
    if (how === "share" && global.navigator.share) {
      global.navigator.share({ title: ref, text: body, url: url }).catch(function () {});
      return;
    }
    copyText(how === "share" ? body + "\n" + url : body).then(
      function () { say2(how === "share" ? "Copied with a link" : "Copied " + ref); },
      function () { say2("Could not copy"); });
  }

  // ---- install: the service worker -----------------------------------------
  if (!env.offline && "serviceWorker" in global.navigator && /^https?:$/.test(location.protocol)) {
    global.addEventListener("load", function () {
      global.navigator.serviceWorker.register("sw.js").catch(function () {});
    });
  }

  // ---- start ---------------------------------------------------------------
  apply();
  mount();
  doc.addEventListener("DOMContentLoaded", mount);

  global.BesorahUI = {
    decorate: decorate,
    prefs: function () { return prefs; },
    setTheme: function (t) { if (THEMES.indexOf(t) !== -1) { prefs.theme = t; save(); apply(); } },
    // The renderers report the chapter on screen, for the picker.
    chapterRendered: function (book, chapter) { here.bookId = book.id; here.chapter = chapter; mount(); },
    shareVerse: shareVerse,
    reference: reference,
    citeName: citeName,
    titleCase: titleCase,
    toast: say2,
    KEEP: KEEP_SEL,
    GLOSSARY: GLOSSARY
  };
})(typeof window !== "undefined" ? window : this);
