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
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = ROOT / "assets" / "index.json"
TEXT_DIR = ROOT / "assets" / "text"
STYLE_PATH = ROOT / "assets" / "style.css"
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

<!-- ============ INDEX VIEW ============ -->
<div id="view-index" class="view active">
  <div class="offline-banner">OFFLINE EDITION — all 102 books bundled in this single file</div>
  <header class="site-header">
    <h1>THE BESORAH</h1>
    <div class="sub">Bereshith &mdash; to &mdash; Ḥazon &mdash; with the Apocrypha</div>
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
    <nav><a href="#/">&larr; All Books</a></nav>
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
      <a href="#/" style="margin-right:0.6rem;">&larr;</a>
      <span class="heb" id="bar-heb">…</span>
      <span class="eng" id="bar-eng"></span>
      <span id="bar-ch" style="margin-left:0.6rem; color: var(--ink-dim);"></span>
    </div>
    <div class="controls">
      <a id="prev" href="#">&larr; Prev</a>
      <a id="book-toc" href="#">Chapters</a>
      <a id="pdf-link" href="#" target="_blank" title="Open original PDF page">PDF</a>
      <a id="next" href="#">Next &rarr;</a>
    </div>
  </div>
  <main class="chapter-main">
    <div class="chapter-page" id="chapter-page">
      <h1 class="chapter-page-title" id="page-heb"></h1>
      <h2 class="chapter-page-sub" id="page-eng"></h2>
      <div class="chapter-num" id="ch-num"></div>
      <div id="verses" class="verses"></div>
      <p class="note" id="loading" style="display:none;">Loading chapter…</p>
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

  // ---------- ROUTING ----------
  // hash forms:
  //   #/                   -> index
  //   #/book/<id>          -> book chapters
  //   #/book/<id>/<ch>     -> chapter view
  function show(viewId) {
    for (const v of document.querySelectorAll('.view')) v.classList.remove('active');
    document.getElementById(viewId).classList.add('active');
    window.scrollTo(0, 0);
  }

  function route() {
    const h = location.hash || '#/';
    const m = h.match(/^#\/book\/([^/]+)(?:\/(\d+))?\/?$/);
    if (!m) {
      renderIndex(document.getElementById('search').value);
      show('view-index');
      return;
    }
    const bookId = decodeURIComponent(m[1]);
    const ch = m[2] ? parseInt(m[2], 10) : null;
    if (ch) {
      renderChapter(bookId, ch);
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
        a.href = `#/book/${encodeURIComponent(b.id)}`;
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
    const esc = raw.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return esc.replace(
      /&lt;span class="dn"&gt;([\s\S]*?)&lt;\/span&gt;/g,
      '<span class="dn">$1</span>'
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

  function renderChapter(bookId, chapter) {
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

    const prevHref = chapter > 1 ? `#/book/${book.id}/${chapter - 1}` : '#';
    const nextHref = chapter < book.chapter_count ? `#/book/${book.id}/${chapter + 1}` : '#';
    setLink('prev',  prevHref, chapter <= 1);
    setLink('prev2', prevHref, chapter <= 1);
    setLink('next',  nextHref, chapter >= book.chapter_count);
    setLink('next2', nextHref, chapter >= book.chapter_count);
    document.getElementById('book-toc').href = `#/book/${book.id}`;

    verseBox.innerHTML = '';
    const verses = ch.verses || [];
    if (verses.length === 0) {
      verseBox.innerHTML =
        `<p class="note">No text extracted for this chapter. <a href="SCRIPTURE/${ch.pdf}#page=${ch.page}" target="_blank">Open the PDF page</a>.</p>`;
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
        p.innerHTML = `<sup class="verse-n">${v.n}</sup> ` + renderVerseText(v.t);
        verseBox.appendChild(p);
      }
    }
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

    index_json = json.dumps(index, ensure_ascii=False, separators=(",", ":"))
    text_json = json.dumps(text, ensure_ascii=False, separators=(",", ":"))

    # Embedded data lives in <script type="application/json"> tags, so the
    # only sequence that can break us is a literal "</script>" inside JSON.
    # Escape its closing slash to keep the parser happy.
    index_json = index_json.replace("</", "<\\/")
    text_json = text_json.replace("</", "<\\/")

    html = (
        HTML_TEMPLATE
        .replace("__STYLE__", style)
        .replace("__INDEX_JSON__", index_json)
        .replace("__TEXT_JSON__", text_json)
    )

    OUTPUT.write_text(html, encoding="utf-8")
    size_mb = OUTPUT.stat().st_size / (1024 * 1024)
    print(f"Wrote {OUTPUT.relative_to(ROOT)} ({size_mb:.1f} MB)")
    print(f"  Books indexed:  {len(index['books'])}")
    print(f"  Text bundles:   {len(text)}")


if __name__ == "__main__":
    main()
