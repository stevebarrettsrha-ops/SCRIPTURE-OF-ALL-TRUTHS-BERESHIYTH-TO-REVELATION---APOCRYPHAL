// besorah-home.js
// Everything the home page shows, in one place so the multi-page site
// (index.html) and the single-file offline edition (besorah-offline.html)
// render an identical home screen from the same code.
//
//   BesorahHome.render({
//     index,        // parsed assets/index.json
//     pool,         // parsed assets/daily-bread.json -> .pool
//     loadBook,     // (bookId) -> Promise<book text json>
//     chapterUrl,   // (bookId, chapter, verse, markId) -> href
//     bookUrl       // (bookId) -> href
//   })
//
// Panels: Daily Bread · Continue reading · Choose your reader ·
//         Tehillim · Mishle · Marked text · Bookmarks
(function (global) {
  "use strict";

  var ctx = null;
  var bookCache = {};

  // ---- helpers --------------------------------------------------------
  function el(id) { return document.getElementById(id); }

  function bookById(id) {
    for (var i = 0; i < ctx.index.books.length; i++) {
      if (ctx.index.books[i].id === id) return ctx.index.books[i];
    }
    return null;
  }

  function getBook(id) {
    if (bookCache[id]) return Promise.resolve(bookCache[id]);
    return Promise.resolve(ctx.loadBook(id)).then(function (t) {
      bookCache[id] = t;
      return t;
    });
  }

  // Verse text may carry <span class="dn"> (divine names) and
  // <span class="hwhy"> (the paleo-Hebrew tetragrammaton). Escape
  // everything, then let just those two back in — same rule the chapter
  // pages use.
  function renderVerseText(raw) {
    // Word forms are corrected on the way to the screen (assets/words.js).
    var fixed = global.BesorahWords ? global.BesorahWords.repair(raw) : raw;
    var esc = String(fixed)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
    // Un-escape only the whitelisted tags, opening and closing handled
    // separately so a footnote containing a divine name still renders.
    return esc
      .replace(/&lt;span class="(dn|hwhy|fn)"&gt;/g, '<span class="$1">')
      .replace(/&lt;\/span&gt;/g, "</span>");
  }

  function plain(raw) {
    var fixed = global.BesorahWords ? global.BesorahWords.repair(raw) : raw;
    return String(fixed).replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
  }

  function chapterLabel(book, chapter) {
    return book.chapter_count > 1 ? book.hebrew + " " + chapter : book.hebrew;
  }

  // Days since the epoch in the reader's own timezone, so the portion
  // turns over at local midnight.
  function dayNumber(d) {
    d = d || new Date();
    return Math.floor(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) / 86400000);
  }

  function dayOfYear(d) {
    d = d || new Date();
    var start = Date.UTC(d.getFullYear(), 0, 1);
    var today = Date.UTC(d.getFullYear(), d.getMonth(), d.getDate());
    return Math.floor((today - start) / 86400000) + 1;
  }

  function longDate(d) {
    try {
      return d.toLocaleDateString(undefined, {
        weekday: "long", day: "numeric", month: "long", year: "numeric"
      });
    } catch (e) {
      return d.toDateString();
    }
  }

  function empty(node, message) {
    var p = document.createElement("p");
    p.className = "note card-empty";
    p.textContent = message;
    node.appendChild(p);
  }

  function head(title, sub, extraClass) {
    var d = document.createElement("div");
    d.className = "card-head" + (extraClass ? " " + extraClass : "");
    d.innerHTML = '<h2>' + title + '</h2>';
    if (sub) {
      var s = document.createElement("span");
      s.className = "card-note";
      s.textContent = sub;
      d.appendChild(s);
    }
    return d;
  }

  // ==================================================================
  //  DAILY BREAD
  // ==================================================================
  function todaysPortion(now) {
    var pool = ctx.pool || [];
    if (!pool.length) return null;
    var n = dayNumber(now) % pool.length;
    if (n < 0) n += pool.length;
    return pool[n];
  }

  function renderDaily(now) {
    var root = el("daily-card");
    if (!root) return;
    var entry = todaysPortion(now);
    root.innerHTML = "";
    root.appendChild(head("Daily Bread", longDate(now)));
    if (!entry) { empty(root, "No portion is available today."); return; }

    var book = bookById(entry.book);
    if (!book) { empty(root, "No portion is available today."); return; }

    var body = document.createElement("div");
    body.className = "daily-body";
    var range = entry.from === entry.to
      ? String(entry.from) : entry.from + "–" + entry.to;
    body.innerHTML =
      '<div class="daily-theme">' + entry.theme + "</div>" +
      '<div class="daily-ref"><span class="heb">' +
        chapterLabel(book, entry.chapter) + ":" + range + "</span>" +
        '<span class="eng">' + book.english + " " + entry.chapter + ":" + range +
      "</span></div>" +
      '<div class="verses daily-verses" id="daily-verses"></div>' +
      '<p class="daily-reflection"></p>' +
      '<div class="daily-actions">' +
        '<div class="tts-bar" id="daily-tts"></div>' +
        '<a class="card-more" id="daily-open">Open the whole chapter &rarr;</a>' +
      "</div>";
    root.appendChild(body);
    body.querySelector(".daily-reflection").textContent = entry.reflection;
    var open = el("daily-open");
    open.href = ctx.chapterUrl(book.id, entry.chapter, entry.from);

    var out = el("daily-verses");
    out.innerHTML = '<p class="note">Fetching today\'s portion…</p>';

    getBook(book.id).then(function (text) {
      var ch = text.chapters[String(entry.chapter)];
      var verses = (ch && ch.verses) || [];
      out.innerHTML = "";
      var found = 0;
      for (var i = 0; i < verses.length; i++) {
        var v = verses[i];
        if (v.n < entry.from || v.n > entry.to) continue;
        var p = document.createElement("p");
        p.className = "verse";
        p.id = "v-" + v.n;
        p.dataset.v = v.n;
        p.innerHTML = '<sup class="verse-n">' + v.n + "</sup> " + renderVerseText(v.t);
        out.appendChild(p);
        found++;
      }
      if (!found) {
        out.innerHTML = '<p class="note">This portion could not be loaded.</p>';
        return;
      }
      // Read-aloud for the portion, using the reader chosen below.
      if (global.BesorahTTS) {
        global.BesorahTTS.init(el("daily-tts"), {
          compact: true,
          label: "Read to me",
          title: "Read today's portion aloud"
        });
        global.BesorahTTS.bind(out);
      }
    }).catch(function (err) {
      out.innerHTML = '<p class="note">This portion could not be loaded.</p>';
      if (global.console) console.error(err);
    });
  }

  // ==================================================================
  //  CONTINUE READING
  // ==================================================================
  function renderContinue() {
    var root = el("continue-card");
    if (!root) return;
    root.innerHTML = "";
    root.appendChild(head("Continue reading"));
    var last = global.BesorahMarks.getLastRead();
    if (!last) {
      empty(root, "Nothing started yet — open any book and this is where you " +
                  "will pick up again.");
      var start = document.createElement("a");
      start.className = "card-more";
      start.href = ctx.chapterUrl("bereshith", 1);
      start.textContent = "Begin at Bereshith 1 →";
      root.appendChild(start);
      return;
    }
    var card = document.createElement("a");
    card.className = "continue-card";
    card.href = ctx.chapterUrl(last.bookId, last.chapter);
    var chSuffix = last.chapterCount > 1 ? " " + last.chapter : "";
    card.innerHTML =
      '<span class="continue-label">Pick up where you left off</span>' +
      '<span class="continue-target"><span class="heb"></span>' +
      '<span class="eng"></span></span>';
    card.querySelector(".heb").textContent = last.hebrew + chSuffix;
    card.querySelector(".eng").textContent = last.english;
    root.appendChild(card);
  }

  // ==================================================================
  //  CHOOSE YOUR READER
  // ==================================================================
  function renderReader() {
    var root = el("reader-card");
    if (!root) return;
    root.innerHTML = "";
    root.appendChild(head("Choose your reader"));
    var panel = document.createElement("div");
    root.appendChild(panel);
    if (global.BesorahTTS) global.BesorahTTS.readerPicker(panel);
  }

  // ==================================================================
  //  TEHILLIM / MISHLE QUICK ACCESS
  // ==================================================================
  // Tehillim walks the 150 songs across the year; Mishle follows the
  // day of the month, the way the 31 chapters are traditionally read.
  function todaysChapter(book, now) {
    if (book.id === "mishle") {
      return Math.min((now || new Date()).getDate(), book.chapter_count);
    }
    return ((dayOfYear(now) - 1) % book.chapter_count) + 1;
  }

  function renderQuick(bookId, slotId, now) {
    var root = el(slotId);
    if (!root) return;
    var book = bookById(bookId);
    root.innerHTML = "";
    if (!book) { empty(root, "This book is not in the index."); return; }

    root.appendChild(head(
      book.hebrew + ' <span class="card-sub">' + book.english + "</span>",
      book.chapter_count + " chapters"
    ));

    var ch = todaysChapter(book, now);
    var today = document.createElement("a");
    today.className = "quick-today";
    today.href = ctx.chapterUrl(book.id, ch);
    today.innerHTML =
      '<span class="quick-today-label">Today\'s reading</span>' +
      '<span class="quick-today-ref">' + book.hebrew + " " + ch + "</span>" +
      '<span class="quick-today-line">…</span>';
    root.appendChild(today);

    var jump = document.createElement("form");
    jump.className = "quick-jump";
    jump.innerHTML =
      '<label>Go to chapter ' +
        '<input type="number" min="1" max="' + book.chapter_count + '" ' +
        'value="' + ch + '" aria-label="Chapter number"></label>' +
      '<button type="submit" class="tts-btn">Open</button>';
    jump.addEventListener("submit", function (e) {
      e.preventDefault();
      var n = parseInt(jump.querySelector("input").value, 10);
      if (!n || n < 1 || n > book.chapter_count) return;
      global.location.href = ctx.chapterUrl(book.id, n);
    });
    root.appendChild(jump);

    var grid = document.createElement("div");
    grid.className = "chapter-grid mini";
    for (var i = 1; i <= book.chapter_count; i++) {
      var a = document.createElement("a");
      a.className = "chapter-link" + (i === ch ? " is-today" : "");
      a.href = ctx.chapterUrl(book.id, i);
      a.textContent = i;
      grid.appendChild(a);
    }
    root.appendChild(grid);

    var more = document.createElement("a");
    more.className = "card-more";
    more.href = ctx.bookUrl(book.id);
    more.textContent = "All of " + book.hebrew + " →";
    root.appendChild(more);

    // A taste of today's chapter, fetched after the panel is on screen.
    getBook(book.id).then(function (text) {
      var chap = text.chapters[String(ch)];
      var first = chap && chap.verses && chap.verses[0];
      var line = today.querySelector(".quick-today-line");
      if (!first) { line.textContent = ""; return; }
      var s = plain(first.t);
      line.textContent = s.length > 120 ? s.slice(0, 118).trim() + "…" : s;
    }).catch(function () {
      var line = today.querySelector(".quick-today-line");
      if (line) line.textContent = "";
    });
  }

  // ==================================================================
  //  MARKED TEXT
  // ==================================================================
  function refLabel(m) {
    var ch = m.chapterCount > 1 ? " " + m.chapter : "";
    return m.verse != null ? m.hebrew + ch + ":" + m.verse : m.hebrew + ch;
  }

  function renderMarked() {
    var root = el("marked-card");
    if (!root) return;
    var marks = global.BesorahMarks.getTextMarks();
    root.innerHTML = "";
    var h = head("Marked text" + (marks.length ? ' <span class="count">(' +
                 marks.length + ")</span>" : ""));
    root.appendChild(h);

    if (!marks.length) {
      empty(root, "Nothing marked yet. While reading, select any words and " +
                  "choose “✎ Mark text” — everything you keep shows up here.");
      return;
    }

    var tools = document.createElement("div");
    tools.className = "bookmarks-tools card-tools";
    tools.innerHTML =
      '<button id="tm-clear" type="button">Clear all</button>';
    h.appendChild(tools);

    var list = document.createElement("ul");
    list.className = "mark-list";
    for (var i = 0; i < marks.length; i++) {
      var m = marks[i];
      var li = document.createElement("li");
      li.className = "mark-item";
      var a = document.createElement("a");
      a.className = "mark-link";
      a.href = ctx.chapterUrl(m.bookId, m.chapter, m.verse, m.id);
      var q = document.createElement("span");
      q.className = "mark-quote";
      q.textContent = m.text;
      var r = document.createElement("span");
      r.className = "mark-ref";
      r.textContent = refLabel(m) + " · " + m.english;
      a.appendChild(q);
      a.appendChild(r);
      li.appendChild(a);
      var del = document.createElement("button");
      del.type = "button";
      del.className = "bm-remove";
      del.title = "Remove this mark";
      del.textContent = "×";
      del.dataset.id = m.id;
      li.appendChild(del);
      list.appendChild(li);
    }
    root.appendChild(list);

    list.addEventListener("click", function (e) {
      var btn = e.target.closest ? e.target.closest(".bm-remove") : null;
      if (!btn) return;
      e.preventDefault();
      global.BesorahMarks.removeTextMark(btn.dataset.id);
      renderMarked();
    });
    el("tm-clear").addEventListener("click", function () {
      if (global.confirm("Remove every marked passage?")) {
        global.BesorahMarks.clearTextMarks();
        renderMarked();
      }
    });
  }

  // ==================================================================
  //  BOOKMARKS
  // ==================================================================
  function renderBookmarks() {
    var root = el("bookmarks-card");
    if (!root) return;
    var marks = global.BesorahMarks.getBookmarks();
    root.innerHTML = "";
    var h = head("Bookmarks" + (marks.length ? ' <span class="count">(' +
                 marks.length + ")</span>" : ""));
    root.appendChild(h);

    var tools = document.createElement("div");
    tools.className = "bookmarks-tools card-tools";
    tools.innerHTML =
      '<button id="bm-export" type="button" title="Save your bookmarks and ' +
      'marked passages to a file">Export</button>' +
      '<label class="bm-import-label" title="Restore from an exported file">Import' +
      '<input id="bm-import" type="file" accept="application/json" hidden></label>' +
      (marks.length ? '<button id="bm-clear" type="button">Clear</button>' : "");
    h.appendChild(tools);

    if (!marks.length) {
      empty(root, "No bookmarks yet. Tap ☆ in the chapter bar to keep a whole " +
                  "chapter, or a verse number to keep a single verse.");
    } else {
      var grid = document.createElement("div");
      grid.className = "book-grid";
      for (var i = 0; i < marks.length; i++) {
        var m = marks[i];
        var a = document.createElement("a");
        a.className = "book-link bookmark-item" + (m.verse != null ? " bm-verse" : "");
        a.href = ctx.chapterUrl(m.bookId, m.chapter, m.verse);
        var verseAttr = m.verse != null ? ' data-v="' + m.verse + '"' : "";
        a.innerHTML =
          '<span class="heb"></span><span class="eng"></span>' +
          '<button class="bm-remove" type="button" title="Remove" ' +
          'data-id="' + m.bookId + '" data-ch="' + m.chapter + '"' + verseAttr + ">×</button>";
        a.querySelector(".heb").textContent = refLabel(m);
        a.querySelector(".eng").textContent = m.english;
        grid.appendChild(a);
      }
      root.appendChild(grid);

      grid.addEventListener("click", function (e) {
        var btn = e.target.closest ? e.target.closest(".bm-remove") : null;
        if (!btn) return;
        e.preventDefault();
        e.stopPropagation();
        var v = btn.dataset.v ? parseInt(btn.dataset.v, 10) : undefined;
        global.BesorahMarks.removeBookmark(btn.dataset.id,
                                           parseInt(btn.dataset.ch, 10), v);
        renderBookmarks();
      });
      el("bm-clear").addEventListener("click", function () {
        if (global.confirm("Remove all bookmarks and reset Continue reading?")) {
          global.BesorahMarks.clearAll();
          renderBookmarks();
          renderContinue();
        }
      });
    }

    el("bm-export").addEventListener("click", function () {
      global.BesorahMarks.exportToFile();
    });
    el("bm-import").addEventListener("change", function (e) {
      var f = e.target.files[0];
      if (!f) return;
      global.BesorahMarks.importFromFile(f, function (err) {
        if (err) global.alert("Could not read that bookmark file.");
        else { renderBookmarks(); renderContinue(); renderMarked(); }
      });
    });
  }

  // ==================================================================
  function render(options) {
    ctx = options;
    var now = new Date();
    renderDaily(now);
    renderContinue();
    renderReader();
    renderQuick("tehillim", "tehillim-card", now);
    renderQuick("mishle", "mishle-card", now);
    renderMarked();
    renderBookmarks();
  }

  global.BesorahHome = {
    render: render,
    refresh: function () { renderMarked(); renderBookmarks(); renderContinue(); }
  };
})(window);
