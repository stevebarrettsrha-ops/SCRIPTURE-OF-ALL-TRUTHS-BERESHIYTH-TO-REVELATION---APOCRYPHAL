// besorah-marks.js
// Bookmark, marked-text (highlight) and last-read tracking, stored in browser
// localStorage. No backend. The same API is used by index.html (home),
// books.html, chapter.html, and the bundled besorah-offline.html (which
// inlines this file at build time).
//
// Three kinds of reader state live here:
//   * last-read   — one entry, powers the "Continue reading" card
//   * bookmarks   — whole chapters or single verses, saved from the ☆ button
//   * text marks  — an arbitrary run of text the reader selected and marked;
//                   painted back into the chapter as <mark class="tmark">
(function (global) {
  "use strict";

  var LAST_KEY = "besorah:lastRead";
  var MARKS_KEY = "besorah:bookmarks";
  var TEXT_KEY = "besorah:textmarks";
  var MAX_MARKS = 200;
  var MAX_TEXT_MARKS = 500;

  function safeGet(key) {
    try { return JSON.parse(localStorage.getItem(key) || "null"); }
    catch (e) { return null; }
  }
  function safeSet(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); }
    catch (e) { /* quota / private mode — silently ignore */ }
  }

  // A book renamed since this reader last opened the page left its old id
  // in everything already saved. besorah-ids.js knows what became what;
  // this runs the three stores through it once, on load, so a bookmark
  // made a year ago still opens and still shows the corrected name.
  function migrateStoredIds() {
    var ids = global.BesorahIds;
    if (!ids || !ids.migrate) return;
    var last = safeGet(LAST_KEY);
    if (last && ids.migrate(last)) safeSet(LAST_KEY, last);
    [MARKS_KEY, TEXT_KEY].forEach(function (key) {
      var arr = safeGet(key);
      if (!Array.isArray(arr)) return;
      var moved = false;
      arr.forEach(function (m) { if (ids.migrate(m)) moved = true; });
      if (moved) safeSet(key, arr);
    });
  }
  migrateStoredIds();

  function makeEntry(book, chapter, verse) {
    var entry = {
      bookId: book.id,
      hebrew: book.hebrew,
      english: book.english,
      chapter: chapter,
      chapterCount: book.chapter_count,
      ts: Date.now()
    };
    if (verse != null) entry.verse = verse;
    return entry;
  }

  function recordLastRead(book, chapter) {
    safeSet(LAST_KEY, makeEntry(book, chapter));
  }

  function getLastRead() {
    return safeGet(LAST_KEY);
  }

  function getBookmarks() {
    var arr = safeGet(MARKS_KEY);
    return Array.isArray(arr) ? arr : [];
  }

  // Equality on (bookId, chapter, verse). `verse` may be undefined for
  // chapter-level bookmarks, which are distinct from any verse-level
  // bookmark in the same chapter.
  function sameMark(m, bookId, chapter, verse) {
    return m.bookId === bookId
        && m.chapter === chapter
        && (m.verse == null ? verse == null : m.verse === verse);
  }

  function isBookmarked(bookId, chapter, verse) {
    return getBookmarks().some(function (m) {
      return sameMark(m, bookId, chapter, verse);
    });
  }

  function addBookmark(book, chapter, verse) {
    var arr = getBookmarks().filter(function (m) {
      return !sameMark(m, book.id, chapter, verse);
    });
    arr.unshift(makeEntry(book, chapter, verse));
    if (arr.length > MAX_MARKS) arr.length = MAX_MARKS;
    safeSet(MARKS_KEY, arr);
  }

  function removeBookmark(bookId, chapter, verse) {
    var arr = getBookmarks().filter(function (m) {
      return !sameMark(m, bookId, chapter, verse);
    });
    safeSet(MARKS_KEY, arr);
  }

  function bookmarkedVersesIn(bookId, chapter) {
    var out = {};
    getBookmarks().forEach(function (m) {
      if (m.bookId === bookId && m.chapter === chapter && m.verse != null) {
        out[m.verse] = true;
      }
    });
    return out;
  }

  function clearAll() {
    safeSet(MARKS_KEY, []);
    try { localStorage.removeItem(LAST_KEY); } catch (e) {}
  }

  // ==================================================================
  //  MARKED TEXT
  //  A text mark is a run of characters inside one verse (or one prose
  //  block) that the reader selected and marked. It is stored as a
  //  character range measured against the *plain text* of that element,
  //  ignoring the verse number, together with a copy of the marked text
  //  so the mark can still be found if the extraction is ever re-run and
  //  the offsets shift slightly.
  // ==================================================================

  function newId() {
    return "tm" + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
  }

  function getTextMarks() {
    var arr = safeGet(TEXT_KEY);
    return Array.isArray(arr) ? arr : [];
  }

  function textMarksIn(bookId, chapter) {
    return getTextMarks().filter(function (m) {
      return m.bookId === bookId && m.chapter === chapter;
    });
  }

  function textMarkCount() { return getTextMarks().length; }

  // Same verse (or the same prose block, where verse is null).
  function sameHost(m, bookId, chapter, verse) {
    return m.bookId === bookId
        && m.chapter === chapter
        && (m.verse == null ? verse == null : m.verse === verse);
  }

  // Add a mark over [start, end) of `fullText`. Any existing mark in the
  // same verse that touches or overlaps the new range is absorbed into it,
  // so marks never overlap and re-marking across a highlight simply widens
  // it. Returns the stored entry.
  function addTextMark(book, chapter, verse, start, end, fullText) {
    if (!(end > start)) return null;
    var all = getTextMarks();
    var kept = [];
    for (var i = 0; i < all.length; i++) {
      var m = all[i];
      if (sameHost(m, book.id, chapter, verse) && m.start <= end && m.end >= start) {
        start = Math.min(start, m.start);
        end = Math.max(end, m.end);
      } else {
        kept.push(m);
      }
    }
    var entry = {
      id: newId(),
      bookId: book.id,
      hebrew: book.hebrew,
      english: book.english,
      chapter: chapter,
      chapterCount: book.chapter_count,
      start: start,
      end: end,
      text: String(fullText).slice(start, end),
      ts: Date.now()
    };
    if (verse != null) entry.verse = verse;
    kept.unshift(entry);
    if (kept.length > MAX_TEXT_MARKS) kept.length = MAX_TEXT_MARKS;
    safeSet(TEXT_KEY, kept);
    return entry;
  }

  function removeTextMark(id) {
    safeSet(TEXT_KEY, getTextMarks().filter(function (m) { return m.id !== id; }));
  }

  function clearTextMarks() { safeSet(TEXT_KEY, []); }

  // ---- painting marks into rendered text ----------------------------
  // The text nodes that make up a verse, skipping the verse number.
  function textNodesOf(el) {
    var out = [];
    if (!el) return out;
    var walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null, false);
    var n;
    while ((n = walker.nextNode())) {
      var p = n.parentElement;
      if (p && p.closest && p.closest(".verse-n")) continue;
      out.push(n);
    }
    return out;
  }

  function plainTextOf(el) {
    var nodes = textNodesOf(el), s = "";
    for (var i = 0; i < nodes.length; i++) s += nodes[i].data;
    return s;
  }

  // Character offset of a selection boundary within `el`, or -1 when the
  // boundary is not inside the element's markable text.
  function boundaryOffset(el, node, offset) {
    if (!node) return -1;
    var target = node, before = 0;
    if (node.nodeType === 1) {
      // Element boundary (e.g. a triple-click): count the text of the
      // children that precede `offset`.
      var kids = node.childNodes;
      var probe = document.createRange();
      probe.setStart(node, 0);
      probe.setEnd(node, Math.min(offset, kids.length));
      var frag = probe.cloneContents();
      var holder = document.createElement("div");
      holder.appendChild(frag);
      before = plainTextOf(holder).length;
      target = null;
    }
    var nodes = textNodesOf(el), pos = 0;
    if (!target) {
      // Element boundary: `before` already counts from the start of `node`.
      // Find where `node` itself begins inside `el`.
      var startOfNode = 0, found = node === el;
      if (!found) {
        for (var j = 0; j < nodes.length; j++) {
          if (node.contains(nodes[j])) { found = true; break; }
          startOfNode += nodes[j].data.length;
        }
      }
      return found ? startOfNode + before : -1;
    }
    for (var i = 0; i < nodes.length; i++) {
      if (nodes[i] === target) return pos + offset;
      pos += nodes[i].data.length;
    }
    return -1;
  }

  // Wrap [start, end) of the element's plain text in <mark class="tmark">.
  function wrapRange(el, start, end, id) {
    var nodes = textNodesOf(el), pos = 0, pieces = [];
    for (var i = 0; i < nodes.length && pos < end; i++) {
      var node = nodes[i], len = node.data.length;
      var s = Math.max(start, pos), e = Math.min(end, pos + len);
      if (e > s) pieces.push({ node: node, s: s - pos, e: e - pos });
      pos += len;
    }
    // Split from the last piece backwards so the offsets computed above
    // stay valid while the DOM is being rewritten.
    for (var k = pieces.length - 1; k >= 0; k--) {
      var p = pieces[k], t = p.node;
      if (p.e < t.data.length) t.splitText(p.e);
      if (p.s > 0) t = t.splitText(p.s);
      var mk = document.createElement("mark");
      mk.className = "tmark";
      mk.setAttribute("data-mid", id);
      t.parentNode.insertBefore(mk, t);
      mk.appendChild(t);
    }
    return pieces.length > 0;
  }

  // Locate a stored mark in the element as it is rendered today. Offsets
  // win; if the text at those offsets no longer matches what was marked,
  // fall back to searching for the marked text itself.
  function resolveRange(el, m) {
    var full = plainTextOf(el);
    if (!m.text) {
      return m.end <= full.length ? { start: m.start, end: m.end } : null;
    }
    if (full.substr(m.start, m.text.length) === m.text) {
      return { start: m.start, end: m.start + m.text.length };
    }
    var i = full.indexOf(m.text);
    return i < 0 ? null : { start: i, end: i + m.text.length };
  }

  function hostElement(container, m) {
    if (!container) return null;
    if (m.verse != null) {
      return container.querySelector('p.verse[data-v="' + m.verse + '"]');
    }
    return container.querySelector("p.prose");
  }

  // Remove every painted highlight from an element, leaving the text intact.
  function unpaint(el) {
    if (!el) return;
    var marks = el.querySelectorAll("mark.tmark");
    for (var i = 0; i < marks.length; i++) {
      var mk = marks[i];
      while (mk.firstChild) mk.parentNode.insertBefore(mk.firstChild, mk);
      mk.parentNode.removeChild(mk);
    }
    el.normalize();
  }

  // Paint every stored mark for this chapter into the rendered verses.
  function applyTextMarks(container, bookId, chapter) {
    if (!container) return;
    var marks = textMarksIn(bookId, chapter);
    for (var i = 0; i < marks.length; i++) {
      var m = marks[i];
      var el = hostElement(container, m);
      if (!el) continue;
      var r = resolveRange(el, m);
      if (!r) continue;
      wrapRange(el, r.start, r.end, m.id);
    }
  }

  function repaintHost(container, el, bookId, chapter, verse) {
    unpaint(el);
    var marks = textMarksIn(bookId, chapter).filter(function (m) {
      return sameHost(m, bookId, chapter, verse);
    });
    for (var i = 0; i < marks.length; i++) {
      var r = resolveRange(el, marks[i]);
      if (r) wrapRange(el, r.start, r.end, marks[i].id);
    }
  }

  // ---- the little floating "Mark text" bubble ------------------------
  var popup = null;

  function ensurePopup() {
    if (popup) return popup;
    popup = document.createElement("div");
    popup.className = "mark-pop";
    popup.setAttribute("hidden", "");
    popup.innerHTML =
      '<button type="button" class="mark-pop-btn" data-act="mark">✎ Mark Text</button>' +
      '<button type="button" class="mark-pop-btn danger" data-act="unmark">✕ Remove Mark</button>' +
      '<button type="button" class="mark-pop-btn" data-act="read">▶ Start Reader</button>';
    document.body.appendChild(popup);
    return popup;
  }

  function hidePopup() {
    if (popup) popup.setAttribute("hidden", "");
    pendingId = null;
    pendingEl = null;
  }

  // `acts` is the list of buttons to offer, in order — e.g. ["mark", "read"].
  function showPopup(rect, acts) {
    var pop = ensurePopup();
    var all = ["mark", "unmark", "read"];
    for (var i = 0; i < all.length; i++) {
      pop.querySelector('[data-act="' + all[i] + '"]').style.display =
        acts.indexOf(all[i]) === -1 ? "none" : "";
    }
    pop.removeAttribute("hidden");
    var top = rect.top + (global.pageYOffset || 0) - pop.offsetHeight - 8;
    var left = rect.left + (global.pageXOffset || 0) +
               (rect.width / 2) - (pop.offsetWidth / 2);
    var maxLeft = (document.documentElement.clientWidth || 0) - pop.offsetWidth - 8;
    if (left < 8) left = 8;
    if (maxLeft > 8 && left > maxLeft) left = maxLeft;
    if (top < (global.pageYOffset || 0) + 4) {
      top = rect.bottom + (global.pageYOffset || 0) + 8;   // flip below
    }
    pop.style.top = top + "px";
    pop.style.left = left + "px";
  }

  // Wire selection-to-mark on a rendered chapter. Safe to call after every
  // render: the listeners are attached to a given container only once (the
  // offline single-file edition re-renders into the same element), while the
  // book/chapter they act on is refreshed each time. Call it before
  // BesorahTTS.bind() so a click on an existing highlight opens the remove
  // bubble instead of starting playback there.
  var wired = [];        // containers already carrying the listeners
  var ctx = null;        // {container, book, chapter, onChange} — current chapter
  var pending = null;    // {el, verse, start, end, fullText} — live selection
  var pendingId = null;  // id of the highlight the bubble offers to remove
  var pendingEl = null;  // the verse the menu was opened on

  function markChanged() {
    hidePopup();
    if (ctx && typeof ctx.onChange === "function") ctx.onChange();
    try {
      document.dispatchEvent(new CustomEvent("besorah:textmarks"));
    } catch (e) { /* very old browsers — the callback already ran */ }
  }

  // Anchor the menu where the reader touched, so it opens under the thumb
  // rather than at the top of a long verse.
  function rectOfClick(e, host) {
    var x = e.clientX, y = e.clientY;
    if (!x && !y) return host.getBoundingClientRect();
    return { top: y - 6, bottom: y + 6, left: x - 40, right: x + 40, width: 80,
             height: 12 };
  }

  function hostOf(node) {
    var el = node && (node.nodeType === 1 ? node : node.parentElement);
    return el && el.closest ? el.closest("p.verse, p.prose") : null;
  }

  function evaluateSelection() {
    if (!ctx) return;
    var container = ctx.container;
    var sel = global.getSelection && global.getSelection();
    if (!sel || sel.isCollapsed || sel.rangeCount === 0) {
      // A tap on a verse also produces a mouseup with an empty selection;
      // it has already opened the verse menu, which must stay up. With no
      // menu open, an empty selection simply closes the bubble.
      if (pendingId || pendingEl) return;
      return hidePopup();
    }
    var range = sel.getRangeAt(0);
    var host = hostOf(range.startContainer);
    if (!host || !container.contains(host) || host !== hostOf(range.endContainer)) {
      return hidePopup();
    }
    var start = boundaryOffset(host, range.startContainer, range.startOffset);
    var end = boundaryOffset(host, range.endContainer, range.endOffset);
    if (start < 0 || end < 0) return hidePopup();
    if (end < start) { var t = start; start = end; end = t; }
    var full = plainTextOf(host);
    // Trim whitespace the drag picked up at either end.
    while (start < end && /\s/.test(full.charAt(start))) start++;
    while (end > start && /\s/.test(full.charAt(end - 1))) end--;
    if (end - start < 2) return hidePopup();
    var v = host.dataset && host.dataset.v ? parseInt(host.dataset.v, 10) : null;
    pending = { el: host, verse: v, start: start, end: end, fullText: full };
    pendingId = null;
    pendingEl = host;
    showPopup(range.getBoundingClientRect(), ["mark", "read"]);
  }

  function wirePopupOnce() {
    var pop = ensurePopup();
    if (pop.dataset.wired) return;
    pop.dataset.wired = "1";
    // Keep the browser from dropping the selection before the click lands.
    pop.addEventListener("mousedown", function (e) { e.preventDefault(); });
    pop.addEventListener("click", function (e) {
      var btn = e.target.closest ? e.target.closest(".mark-pop-btn") : null;
      if (!btn || !ctx) return;
      if (btn.dataset.act === "mark" && pending) {
        addTextMark(ctx.book, ctx.chapter, pending.verse, pending.start,
                    pending.end, pending.fullText);
        repaintHost(ctx.container, pending.el, ctx.book.id, ctx.chapter, pending.verse);
        var sel = global.getSelection && global.getSelection();
        if (sel && sel.removeAllRanges) sel.removeAllRanges();
        pending = null;
        markChanged();
      } else if (btn.dataset.act === "read") {
        var el = pendingEl;
        hidePopup();
        var sel2 = global.getSelection && global.getSelection();
        if (sel2 && sel2.removeAllRanges) sel2.removeAllRanges();
        if (el && ctx && typeof ctx.onRead === "function") ctx.onRead(el);
      } else if (btn.dataset.act === "unmark" && pendingId) {
        var gone = getTextMarks().filter(function (m) { return m.id === pendingId; })[0];
        removeTextMark(pendingId);
        if (gone) {
          var el = hostElement(ctx.container, gone);
          if (el) repaintHost(ctx.container, el, ctx.book.id, ctx.chapter, gone.verse);
        }
        pendingId = null;
        markChanged();
      }
    });
    // The bubble is positioned in page coordinates, so it travels with the
    // text it points at; only a click elsewhere dismisses it.
    document.addEventListener("mousedown", function (e) {
      if (popup && !popup.contains(e.target)) hidePopup();
    });
  }

  // opts: { onChange, onRead } — onRead(verseElement) is what the menu's
  // "Start Reader" calls, so this module never has to know about the
  // read-aloud player.
  function wireTextMarks(container, book, chapter, opts) {
    if (!container) return;
    if (typeof opts === "function") opts = { onChange: opts };
    opts = opts || {};
    ctx = {
      container: container,
      book: book,
      chapter: chapter,
      onChange: opts.onChange,
      onRead: opts.onRead
    };
    pending = null;
    pendingId = null;
    hidePopup();
    applyTextMarks(container, book.id, chapter);
    container.classList.add("markable");
    wirePopupOnce();
    if (wired.indexOf(container) !== -1) return;
    wired.push(container);

    function later() { setTimeout(evaluateSelection, 0); }
    container.addEventListener("mouseup", later);
    container.addEventListener("touchend", later);
    container.addEventListener("keyup", function (e) {
      if (e.shiftKey || e.key === "Shift") later();
    });

    // Touching a verse opens a small menu rather than doing anything at
    // once: the reader chooses to mark it or to start the reader there.
    // On an existing highlight the first option becomes "Remove Mark".
    container.addEventListener("click", function (e) {
      var sel = global.getSelection && global.getSelection();
      if (sel && String(sel).length > 0) return;   // mid-selection, not a tap
      if (e.target.closest && e.target.closest(".verse-n")) return;  // bookmark
      var host = hostOf(e.target);
      if (!host || !container.contains(host)) return;
      e.preventDefault();
      e.stopImmediatePropagation();

      var mk = e.target.closest ? e.target.closest("mark.tmark") : null;
      pending = null;
      pendingEl = host;
      if (mk) {
        pendingId = mk.getAttribute("data-mid");
        showPopup(mk.getBoundingClientRect(), ["unmark", "read"]);
      } else {
        pendingId = null;
        // No selection: "Mark Text" keeps the whole verse.
        var full = plainTextOf(host);
        var s0 = 0, e0 = full.length;
        while (s0 < e0 && /\s/.test(full.charAt(s0))) s0++;
        while (e0 > s0 && /\s/.test(full.charAt(e0 - 1))) e0--;
        var v = host.dataset && host.dataset.v
          ? parseInt(host.dataset.v, 10) : null;
        pending = { el: host, verse: v, start: s0, end: e0, fullText: full,
                    whole: true };
        showPopup(rectOfClick(e, host), ["mark", "read"]);
      }
    });
  }

  // Scroll to a marked passage arrived at from the home page and flash it.
  function scrollToTextMark(id) {
    if (!id) return;
    var el = document.querySelector('mark.tmark[data-mid="' + id + '"]');
    if (!el) return;
    requestAnimationFrame(function () {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.classList.add("flash");
      setTimeout(function () { el.classList.remove("flash"); }, 1800);
    });
  }

  function paintButton(btn, on) {
    btn.textContent = on ? "★" : "☆";
    btn.setAttribute("aria-pressed", on ? "true" : "false");
    btn.title = on ? "Remove bookmark" : "Bookmark this chapter";
    btn.classList.toggle("on", on);
  }

  function wireBookmarkButton(btn, book, chapter) {
    if (!btn) return;
    var on = isBookmarked(book.id, chapter);
    paintButton(btn, on);
    btn.addEventListener("click", function () {
      if (isBookmarked(book.id, chapter)) {
        removeBookmark(book.id, chapter);
        paintButton(btn, false);
      } else {
        addBookmark(book, chapter);
        paintButton(btn, true);
      }
    });
  }

  // Wire all <p class="verse" id="v-N"> elements rendered for a chapter:
  // clicking the verse number toggles a verse-level bookmark and applies
  // the .bookmarked class for visual feedback.
  function wireVerseClicks(versesContainer, book, chapter) {
    if (!versesContainer) return;
    var marked = bookmarkedVersesIn(book.id, chapter);
    versesContainer.querySelectorAll("p.verse[data-v]").forEach(function (p) {
      var n = parseInt(p.getAttribute("data-v"), 10);
      if (marked[n]) p.classList.add("bookmarked");
      var num = p.querySelector(".verse-n");
      if (!num) return;
      num.style.cursor = "pointer";
      num.title = "Bookmark verse " + n;
      num.addEventListener("click", function (e) {
        e.preventDefault();
        if (isBookmarked(book.id, chapter, n)) {
          removeBookmark(book.id, chapter, n);
          p.classList.remove("bookmarked");
        } else {
          addBookmark(book, chapter, n);
          p.classList.add("bookmarked");
        }
      });
    });
  }

  // Scroll to a specific verse element after render and briefly flash it.
  function scrollToVerse(verse) {
    if (verse == null) return;
    var el = document.getElementById("v-" + verse);
    if (!el) return;
    // Defer to next frame so layout has settled.
    requestAnimationFrame(function () {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.classList.add("flash");
      setTimeout(function () { el.classList.remove("flash"); }, 1800);
    });
  }

  // Builds an <a> element pointing at a chapter. The URL builder is
  // injected so the same code works for both the multi-page site
  // (chapter.html?id=…&ch=…) and the offline single-file (#/book/…/…).
  function chapterHref(entry, urlBuilder) {
    return urlBuilder(entry.bookId, entry.chapter);
  }

  function exportToFile() {
    var data = {
      exportedAt: new Date().toISOString(),
      lastRead: getLastRead(),
      bookmarks: getBookmarks(),
      textMarks: getTextMarks()
    };
    var blob = new Blob([JSON.stringify(data, null, 2)],
                        { type: "application/json" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = "besorah-bookmarks.json";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }

  function isNonEmptyString(s) {
    return typeof s === "string" && s.length > 0;
  }
  function isPosInt(n) {
    return typeof n === "number" && isFinite(n) && n > 0 && Math.floor(n) === n;
  }

  // Validate and normalize a single bookmark / last-read entry coming
  // from an imported file. Returns a trustworthy entry, or null if the
  // entry is missing the fields the UI depends on. Unknown fields are
  // dropped; missing-but-recoverable fields are back-filled so a partial
  // export still renders rather than showing "undefined".
  function normalizeEntry(e) {
    if (!e || typeof e !== "object") return null;
    if (!isNonEmptyString(e.bookId)) return null;
    if (!isPosInt(e.chapter)) return null;
    var out = {
      bookId: e.bookId,
      hebrew: isNonEmptyString(e.hebrew) ? e.hebrew : e.bookId,
      english: isNonEmptyString(e.english) ? e.english : "",
      chapter: e.chapter,
      chapterCount: isPosInt(e.chapterCount) ? e.chapterCount : 1,
      ts: isPosInt(e.ts) ? e.ts : Date.now()
    };
    if (e.verse != null) {
      if (!isPosInt(e.verse)) return null;  // a malformed verse ref is unsafe to trust
      out.verse = e.verse;
    }
    return out;
  }

  // Same treatment for a marked passage: it additionally needs a sane
  // character range and the text that was marked, since those are what
  // let the highlight be found again in the rendered chapter.
  function normalizeTextMark(e) {
    var base = normalizeEntry(e);
    if (!base) return null;
    if (typeof e.start !== "number" || typeof e.end !== "number") return null;
    if (!isFinite(e.start) || !isFinite(e.end)) return null;
    if (e.start < 0 || e.end <= e.start) return null;
    if (!isNonEmptyString(e.text)) return null;
    base.id = isNonEmptyString(e.id) ? e.id : newId();
    base.start = Math.floor(e.start);
    base.end = Math.floor(e.end);
    base.text = e.text;
    return base;
  }

  // Import bookmarks/last-read from a previously exported file. Every
  // record is validated and normalized before it touches storage:
  // malformed entries are dropped, duplicates collapsed, and the list is
  // capped at MAX_MARKS. onDone(err) reports a non-null error when the
  // file is not JSON, not an object, or contains nothing usable.
  function importFromFile(file, onDone) {
    var reader = new FileReader();
    reader.onerror = function () {
      if (onDone) onDone(reader.error || new Error("Could not read file."));
    };
    reader.onload = function () {
      var parsed;
      try {
        parsed = JSON.parse(reader.result);
      } catch (e) {
        if (onDone) onDone(e);
        return;
      }
      if (!parsed || typeof parsed !== "object") {
        if (onDone) onDone(new Error("Unrecognized bookmark file."));
        return;
      }

      var sawData = false;
      if (Array.isArray(parsed.bookmarks)) {
        var clean = [];
        var seen = {};
        parsed.bookmarks.forEach(function (m) {
          var n = normalizeEntry(m);
          if (!n) return;
          var key = n.bookId + "|" + n.chapter + "|" + (n.verse == null ? "" : n.verse);
          if (seen[key]) return;        // collapse duplicates
          seen[key] = true;
          clean.push(n);
        });
        if (clean.length > MAX_MARKS) clean.length = MAX_MARKS;
        safeSet(MARKS_KEY, clean);
        sawData = true;
      }
      if (Array.isArray(parsed.textMarks)) {
        var cleanText = [];
        var seenText = {};
        parsed.textMarks.forEach(function (m) {
          var n = normalizeTextMark(m);
          if (!n) return;
          var k = n.bookId + "|" + n.chapter + "|" + (n.verse == null ? "" : n.verse) +
                  "|" + n.start + "|" + n.end;
          if (seenText[k]) return;
          seenText[k] = true;
          cleanText.push(n);
        });
        if (cleanText.length > MAX_TEXT_MARKS) cleanText.length = MAX_TEXT_MARKS;
        safeSet(TEXT_KEY, cleanText);
        sawData = true;
      }
      if (parsed.lastRead != null) {
        var last = normalizeEntry(parsed.lastRead);
        if (last) {
          safeSet(LAST_KEY, last);
          sawData = true;
        }
      }

      if (onDone) {
        onDone(sawData ? null : new Error("No valid bookmarks found in file."));
      }
    };
    reader.readAsText(file);
  }

  global.BesorahMarks = {
    recordLastRead: recordLastRead,
    getLastRead: getLastRead,
    getBookmarks: getBookmarks,
    isBookmarked: isBookmarked,
    addBookmark: addBookmark,
    removeBookmark: removeBookmark,
    bookmarkedVersesIn: bookmarkedVersesIn,
    clearAll: clearAll,
    getTextMarks: getTextMarks,
    textMarksIn: textMarksIn,
    textMarkCount: textMarkCount,
    addTextMark: addTextMark,
    removeTextMark: removeTextMark,
    clearTextMarks: clearTextMarks,
    applyTextMarks: applyTextMarks,
    wireTextMarks: wireTextMarks,
    scrollToTextMark: scrollToTextMark,
    wireBookmarkButton: wireBookmarkButton,
    wireVerseClicks: wireVerseClicks,
    scrollToVerse: scrollToVerse,
    chapterHref: chapterHref,
    exportToFile: exportToFile,
    importFromFile: importFromFile
  };
})(window);
