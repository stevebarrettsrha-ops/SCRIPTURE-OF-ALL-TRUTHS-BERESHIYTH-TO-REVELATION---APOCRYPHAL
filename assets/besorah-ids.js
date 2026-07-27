// besorah-ids.js
// The book ids that have changed, and what they changed to.
//
// A book's id is its file name and its place in every link — and it is
// also what a saved bookmark, a marked passage and "continue reading"
// wrote into localStorage months ago. When a name is corrected the id
// follows it, so anything already saved would point at a book that no
// longer exists, and a link someone shared would open on "Book not
// found".
//
// So every old id is kept here for good. Nothing reads the table except
// resolve(), which the three pages call before they look a book up, and
// migrate(), which rewrites what is in storage once.
//
//   BesorahIds.resolve(id)  -> the current id for any id, old or new
//   BesorahIds.migrate(obj) -> the same object with its bookId brought
//                              forward (returns true if it changed)
(function (global) {
  "use strict";

  var RENAMED = {
    "yeshayahu": "yashayahu",
    "1shemuel": "1shamual",
    "2shemuel": "2shamual",
    "1melakim": "1malakim",
    "2melakim": "2malakim",
    "shemoth": "shamoth",
    "bemidbar": "bamidbar",
    "debarim": "dabarim",
    "yirmeyahu": "yirmayahu",
    "yehezqel": "yahazqal",
    "daniel": "danial",
    "yoel": "yoal",
    "obadyah": "obadyahu",
    "tsephanyah": "tsephanyahu",
    "zekaryah": "zakaryahu"
  };

  // A saved bookmark also kept a copy of the name it was showing, so the
  // old spelling would survive on the home page until the reader saved it
  // again. These bring that copy forward too.
  var RENAMED_HEBREW = {
    "YESHAYAHU": "YASHAYAHU",
    "1 SHEMU'ĔL": "1 SHAMU'AL",
    "2 SHEMU'ĔL": "2 SHAMU'AL",
    "1 MELAḴIM": "1 MALAḴIM",
    "2 MELAḴIM": "2 MALAḴIM",
    "SHEMOTH": "SHAMOTH",
    "BEMIḎBAR": "BAMIḎBAR",
    "DEḆARIM": "DAḆARIM",
    "YIRMEYAHU": "YIRMAYAHU",
    "YEḤEZQ'ĔL": "YAHAZQ'AL",
    "DANI'ĔL": "DANI'AL",
    "YO'ĔL": "YO'AL",
    "OḆADYAH": "OḆADYAHU",
    "TSEPHANYAH": "TSEPHANYAHU",
    "ZEḴARYAH": "ZAḴARYAHU"
  };

  function resolve(id) {
    if (!id) return id;
    return RENAMED.hasOwnProperty(id) ? RENAMED[id] : id;
  }

  // A stored entry — a bookmark, a text mark, the last-read pointer.
  // Returns true when something was brought forward.
  function migrate(entry) {
    if (!entry || !entry.bookId) return false;
    var now = resolve(entry.bookId);
    if (now === entry.bookId) return false;
    entry.bookId = now;
    if (entry.hebrew && RENAMED_HEBREW.hasOwnProperty(entry.hebrew)) {
      entry.hebrew = RENAMED_HEBREW[entry.hebrew];
    }
    return true;
  }

  global.BesorahIds = {
    RENAMED: RENAMED,
    RENAMED_HEBREW: RENAMED_HEBREW,
    resolve: resolve,
    migrate: migrate
  };
})(typeof window !== "undefined" ? window : this);
