#!/usr/bin/env python3
"""
build_offline.py

Bundles index.json, every assets/text/<book>.json, and the stylesheet
into a single self-contained HTML file (besorah-offline.html) at the
repo root. The file works when opened directly with file:// (no web
server required), since all data is embedded inline.

Usage:
    python3 scripts/build_offline.py
"""
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = ROOT / "assets" / "index.json"
TEXT_DIR = ROOT / "assets" / "text"
STYLE_PATH = ROOT / "assets" / "style.css"
MARKS_JS_PATH = ROOT / "assets" / "besorah-marks.js"
TTS_JS_PATH = ROOT / "assets" / "besorah-tts.js"
HOME_JS_PATH = ROOT / "assets" / "besorah-home.js"
WORDS_JS_PATH = ROOT / "assets" / "words.js"
PRON_JS_PATH = ROOT / "assets" / "pronunciation.js"
DAILY_PATH = ROOT / "assets" / "daily-bread.json"
OUTPUT = ROOT / "besorah-offline.html"


def load_index():
    with INDEX_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def load_all_text():
    bundle = {}
    for jf in sorted(TEXT_DIR.glob("*.json")):
        with jf.open(encoding="utf-8") as f:
            bundle[jf.stem] = json.load(f)
    return bundle


def load_style():
    return STYLE_PATH.read_text(encoding="utf-8")


def escape_script_close(js):
    """Make JavaScript safe to inline inside a <script> block.

    Only "</script" can end the block early, so that is the one sequence
    escaped — blanket-escaping every "</" would silently break regular
    expressions such as /</g.
    """
    return re.sub(r"</(?=script)", "<\\\\/", js, flags=re.IGNORECASE)


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The Besorah — Offline</title>
<style>
__STYLE__
/* Offline-only tweaks */
body { display: flex; flex-direction: column; min-height: 100vh; margin: 0; }
.view { display: none; }
.view.active { display: block; }
#view-chapter { flex: 1 1 auto; display: none; flex-direction: column; }
#view-chapter.active { display: flex; }
#view-chapter > main { flex: 1 1 auto; }
.offline-banner {
  background: #2c211a;
  color: var(--ink-dim);
  text-align: center;
  font-size: 0.78rem;
  padding: 0.3rem;
  letter-spacing: 0.04em;
}
</style>
</head>
<body>

<!-- ============ HOME VIEW ============ -->
<div id="view-home" class="view active">
  <div class="offline-banner">OFFLINE EDITION — all 104 books bundled in this single file</div>
  <header class="site-header">
    <h1>THE BESORAH</h1>
    <div class="sub">Bereshith &mdash; to &mdash; Ḥazon &mdash; with the Apocrypha</div>
    <nav><a href="#/books">All 104 Books &rarr;</a></nav>
  </header>
  <main class="home">
    <section class="card daily-card" id="daily-card"></section>
    <div class="home-row">
      <section class="card" id="continue-card"></section>
      <section class="card" id="reader-card"></section>
    </div>
    <div class="home-row">
      <section class="card quick-card" id="tehillim-card"></section>
      <section class="card quick-card" id="mishle-card"></section>
    </div>
    <section class="card" id="marked-card"></section>
    <section class="card" id="bookmarks-card"></section>
  </main>
</div>

<!-- ============ INDEX (ALL BOOKS) VIEW ============ -->
<div id="view-index" class="view">
  <header class="site-header">
    <h1>THE BESORAH</h1>
    <div class="sub">Bereshith &mdash; to &mdash; Ḥazon &mdash; with the Apocrypha</div>
    <nav><a href="#/">&larr; Home</a></nav>
  </header>
  <main>
    <input type="search" id="search" placeholder="Search for a book (Hebrew or English name)…" autocomplete="off">
    <div id="content"></div>
  </main>
</div>

<!-- ============ BOOK VIEW ============ -->
<div id="view-book" class="view">
  <header class="site-header">
    <h1 id="book-page-title">THE BESORAH</h1>
    <div class="sub" id="book-page-section"></div>
    <nav><a href="#/">⌂ Home</a><a href="#/books">&larr; All Books</a></nav>
  </header>
  <main>
    <div class="book-title">
      <div class="heb" id="book-heb"></div>
      <div class="eng" id="book-eng"></div>
    </div>
    <div id="chapter-list"></div>
  </main>
</div>

<!-- ============ CHAPTER VIEW ============ -->
<div id="view-chapter" class="view">
  <div class="chapter-bar">
    <div class="title">
      <a href="#/" title="Home" style="margin-right:0.4rem;">⌂</a>
      <a href="#/books" title="All books" style="margin-right:0.6rem;">&larr;</a>
      <span class="heb" id="bar-heb">…</span>
      <span class="eng" id="bar-eng"></span>
      <span id="bar-ch" style="margin-left:0.6rem; color: var(--ink-dim);"></span>
    </div>
    <div class="controls">
      <a id="prev" href="#">&larr; Prev</a>
      <a id="book-toc" href="#">Chapters</a>
      <a id="pdf-link" href="#" target="_blank" title="Open original PDF page">PDF</a>
      <button id="bookmark-btn" class="btn" type="button" title="Bookmark this chapter" aria-pressed="false">☆</button>
      <a id="next" href="#">Next &rarr;</a>
    </div>
    <div class="tts-bar" id="tts-bar"></div>
  </div>
  <main class="chapter-main">
    <div class="chapter-page" id="chapter-page">
      <h1 class="chapter-page-title" id="page-heb"></h1>
      <h2 class="chapter-page-sub" id="page-eng"></h2>
      <div class="chapter-num" id="ch-num"></div>
      <div id="verses" class="verses"></div>
      <p class="note" id="loading" style="display:none;">Loading chapter…</p>
      <p class="note mark-hint">Select any words to mark them — everything you
        mark is gathered on the <a href="#/">home page</a>.</p>
    </div>
  </main>
  <footer class="chapter-footer">
    <div class="controls">
      <a id="prev2" href="#">&larr; Previous chapter</a>
      <a id="next2" href="#">Next chapter &rarr;</a>
    </div>
  </footer>
</div>

<!-- ============ EMBEDDED DATA ============ -->
<script id="index-data" type="application/json">__INDEX_JSON__</script>
<script id="text-data" type="application/json">__TEXT_JSON__</script>
<script id="daily-data" type="application/json">__DAILY_JSON__</script>

<!-- ============ WORD FORMS + PRONUNCIATION ============ -->
<script>
__WORDS_JS__
</script>
<script>
__PRON_JS__
</script>

<!-- ============ MARKS LIBRARY ============ -->
<script>
__MARKS_JS__
</script>

<!-- ============ READ-ALOUD (TTS) LIBRARY ============ -->
<script>
__TTS_JS__
</script>

<!-- ============ HOME PAGE ============ -->
<script>
__HOME_JS__
</script>

<script>
(function () {
  const SECTIONS = [
    { key: "Torah",       label: "Torah — Teaching" },
    { key: "Nebi'im",     label: "Nebi'im — Prophets" },
    { key: "Kethubim",    label: "Kethubim — Writings" },
    { key: "Messianic",   label: "Messianic Writings" },
    { key: "Apocryphal",  label: "Apocryphal Books" },
    { key: "Patriarchs",  label: "Testaments of the Twelve Patriarchs" },
    { key: "Apocrypha",   label: "Ethiopic & Eastern Apocrypha" }
  ];

  const INDEX = JSON.parse(document.getElementById('index-data').textContent);
  const TEXT  = JSON.parse(document.getElementById('text-data').textContent);
  const DAILY = JSON.parse(document.getElementById('daily-data').textContent);

  // Hash-router URL builders for the offline single-file edition.
  function chapterUrl(bookId, ch, verse, markId) {
    var url = `#/book/${encodeURIComponent(bookId)}/${ch}`;
    if (verse != null) url += `/v/${verse}`;
    if (markId) url += `/m/${encodeURIComponent(markId)}`;
    return url;
  }
  function bookUrl(bookId) {
    return `#/book/${encodeURIComponent(bookId)}`;
  }

  // ---------- HOME ----------
  function renderHome() {
    BesorahHome.render({
      index: INDEX,
      pool: DAILY.pool,
      loadBook: id => TEXT[id],
      chapterUrl: chapterUrl,
      bookUrl: bookUrl
    });
  }

  // ---------- ROUTING ----------
  function show(viewId) {
    for (const v of document.querySelectorAll('.view')) v.classList.remove('active');
    document.getElementById(viewId).classList.add('active');
    window.scrollTo(0, 0);
  }

  function route() {
    const h = location.hash || '#/';
    // Forms:
    //   #/                              -> home (Daily Bread & co.)
    //   #/books                         -> all 104 books
    //   #/book/<id>                     -> book chapters
    //   #/book/<id>/<ch>                -> chapter view
    //   #/book/<id>/<ch>/v/<n>          -> chapter view, scrolled to verse n
    //   #/book/<id>/<ch>/m/<markId>     -> chapter view, scrolled to a mark
    if (/^#\/books\/?$/.test(h)) {
      renderIndex(document.getElementById('search').value);
      show('view-index');
      return;
    }
    const m = h.match(
      /^#\/book\/([^/]+)(?:\/(\d+)(?:\/v\/(\d+))?(?:\/m\/([^/]+))?)?\/?$/);
    if (!m) {
      renderHome();
      show('view-home');
      return;
    }
    const bookId = decodeURIComponent(m[1]);
    const ch = m[2] ? parseInt(m[2], 10) : null;
    const verse = m[3] ? parseInt(m[3], 10) : null;
    const markId = m[4] ? decodeURIComponent(m[4]) : null;
    if (ch) {
      renderChapter(bookId, ch, verse, markId);
      show('view-chapter');
    } else {
      renderBook(bookId);
      show('view-book');
    }
  }

  // ---------- INDEX ----------
  function renderIndex(filter) {
    const root = document.getElementById('content');
    root.innerHTML = '';
    const f = (filter || '').trim().toLowerCase();

    for (const s of SECTIONS) {
      const books = INDEX.books.filter(b =>
        b.section === s.key &&
        (!f || b.hebrew.toLowerCase().includes(f) || b.english.toLowerCase().includes(f))
      );
      if (books.length === 0) continue;

      const section = document.createElement('section');
      section.className = 'section';
      const h2 = document.createElement('h2');
      h2.textContent = s.label;
      section.appendChild(h2);

      const grid = document.createElement('div');
      grid.className = 'book-grid';
      for (const b of books) {
        const a = document.createElement('a');
        a.className = 'book-link';
        a.href = bookUrl(b.id);
        a.innerHTML = `<span class="heb">${b.hebrew}</span><span class="eng">${b.english}</span>`;
        grid.appendChild(a);
      }
      section.appendChild(grid);
      root.appendChild(section);
    }

    if (root.children.length === 0) {
      const p = document.createElement('p');
      p.className = 'note';
      p.textContent = 'No books match your search.';
      root.appendChild(p);
    }
  }

  // ---------- BOOK ----------
  function renderBook(bookId) {
    const book = INDEX.books.find(b => b.id === bookId);
    const list = document.getElementById('chapter-list');
    if (!book) {
      list.innerHTML = '<p class="note">Book not found.</p>';
      return;
    }
    document.title = `${book.hebrew} (${book.english}) — The Besorah`;
    document.getElementById('book-page-title').textContent = book.hebrew;
    document.getElementById('book-page-section').textContent = book.section.toUpperCase();
    document.getElementById('book-heb').textContent = book.hebrew;
    document.getElementById('book-eng').textContent = book.english;

    list.innerHTML = '';
    if (book.chapter_count === 1) {
      const a = document.createElement('a');
      a.className = 'chapter-link';
      a.href = `#/book/${encodeURIComponent(book.id)}/1`;
      a.style.maxWidth = '300px';
      a.style.margin = '2rem auto';
      a.style.fontSize = '1.1rem';
      a.style.padding = '1rem';
      a.textContent = `Read ${book.hebrew} →`;
      list.appendChild(a);
    } else {
      const heading = document.createElement('p');
      heading.style.textAlign = 'center';
      heading.style.color = 'var(--ink-dim)';
      heading.style.marginTop = '1rem';
      heading.textContent = `${book.chapter_count} chapters`;
      list.appendChild(heading);

      const grid = document.createElement('div');
      grid.className = 'chapter-grid';
      for (let i = 1; i <= book.chapter_count; i++) {
        const a = document.createElement('a');
        a.className = 'chapter-link';
        a.href = `#/book/${encodeURIComponent(book.id)}/${i}`;
        a.textContent = i;
        grid.appendChild(a);
      }
      list.appendChild(grid);
    }
  }

  // ---------- CHAPTER ----------
  function renderVerseText(raw) {
    // Word forms are corrected on the way to the screen (assets/words.js).
    const fixed = window.BesorahWords ? BesorahWords.repair(raw) : raw;
    const esc = fixed.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return esc.replace(
      /&lt;span class="(dn|hwhy)"&gt;([\s\S]*?)&lt;\/span&gt;/g,
      '<span class="$1">$2</span>'
    );
  }

  function setLink(elId, href, disabled) {
    const el = document.getElementById(elId);
    if (!el) return;
    if (disabled) {
      el.classList.add('disabled');
      el.removeAttribute('href');
    } else {
      el.classList.remove('disabled');
      el.href = href;
    }
  }

  function renderChapter(bookId, chapter, verseAnchor, markAnchor) {
    const book = INDEX.books.find(b => b.id === bookId);
    const text = TEXT[bookId];
    const verseBox = document.getElementById('verses');
    if (!book || !text) {
      verseBox.innerHTML = '<p class="note">Chapter not found.</p>';
      return;
    }
    const ch = text.chapters[String(chapter)];
    if (!ch) {
      verseBox.innerHTML = '<p class="note">Chapter not found.</p>';
      return;
    }

    document.title = `${book.hebrew}${book.chapter_count > 1 ? ' ' + chapter : ''} — The Besorah`;
    document.getElementById('bar-heb').textContent = book.hebrew;
    document.getElementById('bar-eng').textContent = `(${book.english})`;
    document.getElementById('bar-ch').textContent =
      book.chapter_count > 1 ? `Chapter ${chapter}` : '';
    document.getElementById('page-heb').textContent = book.hebrew;
    document.getElementById('page-eng').textContent = book.english;
    document.getElementById('ch-num').textContent =
      book.chapter_count > 1 ? chapter : '';

    document.getElementById('pdf-link').href = `SCRIPTURE/${ch.pdf}#page=${ch.page}`;

    const prevHref = chapterUrl(book.id, chapter - 1);
    const nextHref = chapterUrl(book.id, chapter + 1);
    setLink('prev',  prevHref, chapter <= 1);
    setLink('prev2', prevHref, chapter <= 1);
    setLink('next',  nextHref, chapter >= book.chapter_count);
    setLink('next2', nextHref, chapter >= book.chapter_count);
    document.getElementById('book-toc').href = bookUrl(book.id);

    // Bookmark + last-read tracking (localStorage; nothing leaves the device)
    BesorahMarks.recordLastRead(book, chapter);
    BesorahMarks.wireBookmarkButton(
      document.getElementById('bookmark-btn'), book, chapter
    );
    // Read-aloud player (built once; re-pointed at this chapter's verses).
    BesorahTTS.init(document.getElementById('tts-bar'));

    verseBox.innerHTML = '';
    const verses = ch.verses || [];
    if (verses.length === 0) {
      verseBox.innerHTML =
        `<p class="note">No text extracted for this chapter. <a href="SCRIPTURE/${ch.pdf}#page=${ch.page}" target="_blank">Open the PDF page</a>.</p>`;
      BesorahTTS.bind(verseBox);
      return;
    }
    const isProse = verses.length === 1 && verses[0].t.length > 600;
    if (isProse) {
      const p = document.createElement('p');
      p.className = 'prose';
      p.innerHTML = renderVerseText(verses[0].t);
      verseBox.appendChild(p);
    } else {
      for (const v of verses) {
        const p = document.createElement('p');
        p.className = 'verse';
        p.id = `v-${v.n}`;
        p.dataset.v = v.n;
        p.innerHTML = `<sup class="verse-n">${v.n}</sup> ` + renderVerseText(v.t);
        verseBox.appendChild(p);
      }
      BesorahMarks.wireVerseClicks(verseBox, book, chapter);
    }
    // Marked text: paint saved highlights and let a fresh selection be
    // marked. Wired before the read-aloud player so tapping a highlight
    // offers to remove it instead of starting playback there.
    BesorahMarks.wireTextMarks(verseBox, book, chapter);
    BesorahTTS.bind(verseBox);
    if (markAnchor) BesorahMarks.scrollToTextMark(markAnchor);
    else BesorahMarks.scrollToVerse(verseAnchor);
  }

  // ---------- INIT ----------
  document.getElementById('search').addEventListener('input', e => {
    renderIndex(e.target.value);
  });
  window.addEventListener('hashchange', route);
  route();
})();
</script>
</body>
</html>
"""


def main():
    index = load_index()
    text = load_all_text()
    style = load_style()
    with DAILY_PATH.open(encoding="utf-8") as f:
        daily = json.load(f)
    marks_js = MARKS_JS_PATH.read_text(encoding="utf-8")
    tts_js = TTS_JS_PATH.read_text(encoding="utf-8")
    home_js = HOME_JS_PATH.read_text(encoding="utf-8")
    words_js = WORDS_JS_PATH.read_text(encoding="utf-8")
    pron_js = PRON_JS_PATH.read_text(encoding="utf-8")

    index_json = json.dumps(index, ensure_ascii=False, separators=(",", ":"))
    text_json = json.dumps(text, ensure_ascii=False, separators=(",", ":"))
    daily_json = json.dumps(daily, ensure_ascii=False, separators=(",", ":"))

    # Embedded data lives in <script type="application/json"> tags, so the
    # only sequence that can break us is a literal "</script>" inside JSON.
    # Escape its closing slash to keep the parser happy.
    index_json = index_json.replace("</", "<\\/")
    text_json = text_json.replace("</", "<\\/")
    daily_json = daily_json.replace("</", "<\\/")
    # Same protection for the inlined libraries (regular <script>), but only
    # the sequence that can actually close the block. Escaping every "</"
    # would corrupt regex literals such as /</g.
    marks_js_safe = escape_script_close(marks_js)
    tts_js_safe = escape_script_close(tts_js)
    home_js_safe = escape_script_close(home_js)
    words_js_safe = escape_script_close(words_js)
    pron_js_safe = escape_script_close(pron_js)

    html = (
        HTML_TEMPLATE
        .replace("__STYLE__", style)
        .replace("__INDEX_JSON__", index_json)
        .replace("__TEXT_JSON__", text_json)
        .replace("__DAILY_JSON__", daily_json)
        .replace("__MARKS_JS__", marks_js_safe)
        .replace("__TTS_JS__", tts_js_safe)
        .replace("__HOME_JS__", home_js_safe)
        .replace("__WORDS_JS__", words_js_safe)
        .replace("__PRON_JS__", pron_js_safe)
    )

    OUTPUT.write_text(html, encoding="utf-8")
    size_mb = OUTPUT.stat().st_size / (1024 * 1024)
    print(f"Wrote {OUTPUT.relative_to(ROOT)} ({size_mb:.1f} MB)")
    print(f"  Books indexed:  {len(index['books'])}")
    print(f"  Text bundles:   {len(text)}")
    print(f"  Daily portions: {len(daily.get('pool', []))}")


if __name__ == "__main__":
    main()
