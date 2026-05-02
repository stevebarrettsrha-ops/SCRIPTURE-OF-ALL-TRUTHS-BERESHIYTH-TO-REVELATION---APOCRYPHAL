// besorah-marks.js
// Bookmark + last-read tracking, stored in browser localStorage. No backend.
// Same API is used by chapter.html, index.html, and the bundled
// besorah-offline.html (which inlines this file at build time).
(function (global) {
  "use strict";

  var LAST_KEY = "besorah:lastRead";
  var MARKS_KEY = "besorah:bookmarks";
  var MAX_MARKS = 200;

  function safeGet(key) {
    try { return JSON.parse(localStorage.getItem(key) || "null"); }
    catch (e) { return null; }
  }
  function safeSet(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); }
    catch (e) { /* quota / private mode — silently ignore */ }
  }

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
      bookmarks: getBookmarks()
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

  function importFromFile(file, onDone) {
    var reader = new FileReader();
    reader.onload = function () {
      try {
        var parsed = JSON.parse(reader.result);
        if (parsed.bookmarks) safeSet(MARKS_KEY, parsed.bookmarks);
        if (parsed.lastRead) safeSet(LAST_KEY, parsed.lastRead);
        if (onDone) onDone(null);
      } catch (e) {
        if (onDone) onDone(e);
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
    wireBookmarkButton: wireBookmarkButton,
    wireVerseClicks: wireVerseClicks,
    scrollToVerse: scrollToVerse,
    chapterHref: chapterHref,
    exportToFile: exportToFile,
    importFromFile: importFromFile
  };
})(window);
