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

  function makeEntry(book, chapter) {
    return {
      bookId: book.id,
      hebrew: book.hebrew,
      english: book.english,
      chapter: chapter,
      chapterCount: book.chapter_count,
      ts: Date.now()
    };
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

  function isBookmarked(bookId, chapter) {
    return getBookmarks().some(function (m) {
      return m.bookId === bookId && m.chapter === chapter;
    });
  }

  function addBookmark(book, chapter) {
    var arr = getBookmarks().filter(function (m) {
      return !(m.bookId === book.id && m.chapter === chapter);
    });
    arr.unshift(makeEntry(book, chapter));
    if (arr.length > MAX_MARKS) arr.length = MAX_MARKS;
    safeSet(MARKS_KEY, arr);
  }

  function removeBookmark(bookId, chapter) {
    var arr = getBookmarks().filter(function (m) {
      return !(m.bookId === bookId && m.chapter === chapter);
    });
    safeSet(MARKS_KEY, arr);
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
    clearAll: clearAll,
    wireBookmarkButton: wireBookmarkButton,
    chapterHref: chapterHref,
    exportToFile: exportToFile,
    importFromFile: importFromFile
  };
})(window);
