"""Extract verse text per chapter from each PDF and write per-book JSON files
to assets/text/<book_id>.json.

Output format per book:
{
  "id": "bereshith",
  "hebrew": "BERĔSHITH",
  "english": "Genesis",
  "section": "Torah",
  "chapter_count": 50,
  "chapters": {
     "1": {"verses": [{"n": 1, "t": "In the beginning..."}, ...], "page": 43, "pdf": "..."},
     ...
  }
}
"""
from pypdf import PdfReader
import re, json, os

ROOT      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR   = os.path.join(ROOT, "SCRIPTURE")
INDEX_IN  = os.path.join(ROOT, "assets", "index.json")
OUT_DIR   = os.path.join(ROOT, "assets", "text")
os.makedirs(OUT_DIR, exist_ok=True)

# Cache PDFs once
_pdf_cache = {}
def get_pdf(name):
    if name not in _pdf_cache:
        _pdf_cache[name] = PdfReader(os.path.join(PDF_DIR, name))
    return _pdf_cache[name]


# Character class shortcuts:
# UPPER = ASCII uppercase + non-ASCII letters (covers Ḥ, Ĕ, Ḇ, Ḏ, etc.)
# LETTER = letters of either case + non-ASCII
UPPER  = "A-Z-￿"
LETTER = "A-Za-z-￿"


# ---------------------------- BESORAH FORMAT ----------------------------

# Footnote opener: a Capitalized word (or hyphenated phrase) followed by ":" or "—" then text
FOOTNOTE_PAT = re.compile(
    r'\n([A-Z][A-Za-z\-\'-￿]+(?:[\s/\-][A-Za-z\-\'-￿]+){0,4})\s*[:—]\s+[A-Za-z“‘"\']'
)


def strip_besorah_page(raw):
    """Strip page header lines and any trailing footnote block."""
    lines = raw.split('\n')
    drops = 0
    while lines and drops < 4:
        first = lines[0].strip()
        if not first:
            lines.pop(0)
            continue
        # Page-only number like "43"
        if re.match(r'^\d+\s*$', first):
            lines.pop(0); drops += 1; continue
        # "44    BERĔSHITH 2", "278Yahusha 2", "3361 SHEMU'ĔL 1"
        # Restrict to short lines (book names are at most ~25 chars) to avoid eating verse 1.
        if len(first) <= 25 and re.match(rf"^\d+\s*[{UPPER}][{LETTER}'\s\-]*?(?:\s+\d+)?\s*$", first):
            lines.pop(0); drops += 1; continue
        # "BERĔSHITH" or "BERĔSHITH 2" — Hebrew name (all uppercase) optionally with chapter number
        if re.match(rf"^[{UPPER}][{UPPER}'\s\-]+(?:\s+\d+)?\s*$", first):
            lines.pop(0); drops += 1; continue
        # "GENESIS — 1 MOSHEH" — English name + em-dash + ordinal + Hebrew name
        if re.match(r"^[A-Z][A-Z\s]+\s*[—–\-]\s*\d+\s*[A-Z][A-Za-z]*\s*$", first):
            lines.pop(0); drops += 1; continue
        break
    body = '\n'.join(lines)

    # Strip footnote tail: scan after the last verse marker
    verse_positions = [m.start() for m in re.finditer(rf'(?:^|\s|\n)(\d+)(?=[{UPPER}"“‘\'])', body)]
    scan_from = verse_positions[-1] if verse_positions else 0
    m = FOOTNOTE_PAT.search(body, scan_from)
    if m:
        body = body[:m.start()]
    return body


def parse_besorah_chapter(book, chapter, start_pg, end_pg):
    """Extract verses for one chapter of the Besorah."""
    pdf_file = book['chapters'][str(chapter)]['pdf']
    r1 = get_pdf("TheBesorah-all.0001.pdf")
    r2 = get_pdf("TheBesorah-all.0002.pdf")

    def get_text(pdf_filename, page):
        r = r1 if pdf_filename == "TheBesorah-all.0001.pdf" else r2
        if 1 <= page <= len(r.pages):
            return r.pages[page - 1].extract_text() or ""
        return ""

    parts = []
    for pg in range(start_pg, end_pg + 1):
        cleaned = strip_besorah_page(get_text(pdf_file, pg))
        parts.append(cleaned)
    full = "\n".join(parts)

    # Locate THIS chapter start: a chapter-number marker followed by space + capitalized text
    # (verse 1 is denoted by the chapter number itself in the Besorah typesetting).
    # Use \b to avoid matching mid-number like "31" containing "1".
    chap_start_pat = re.compile(rf'(?:^|\n|\s){chapter}\s+(?=[{UPPER}"“‘\'])')
    next_chap_pat  = re.compile(rf'(?:^|\n|\s){chapter+1}\s+(?=[{UPPER}"“‘\'])')

    m = chap_start_pat.search(full)
    if m:
        full = full[m.end():]
        full = "1 " + full   # synthesize verse 1 marker
    n = next_chap_pat.search(full)
    if n:
        full = full[:n.start()]

    # Verses: number followed (with optional space) by a letter or quote
    # Allow lowercase too (e.g. "15and let them be...") since some verses begin with lowercase.
    verse_pat = re.compile(rf'(?:^|(?<=\s))(\d+)\s*(?=[{LETTER}"“‘\'])')
    matches = list(verse_pat.finditer(full))

    verses = []
    seen = set()
    expected = 1
    for i, mm in enumerate(matches):
        try: n = int(mm.group(1))
        except: continue
        if n < 1 or n > 200: continue
        if n in seen: continue
        # Allow only forward progression (skip duplicates / out-of-order)
        if n < expected: continue
        if n > expected + 5: continue   # likely a stray number, not a verse marker
        end = matches[i+1].start() if i+1 < len(matches) else len(full)
        text = full[mm.end():end].strip()
        text = re.sub(r'\s+', ' ', text)
        if not text: continue
        verses.append({"n": n, "t": text})
        seen.add(n)
        expected = n + 1
    return verses


# ---------------------------- ENOCH FORMAT ----------------------------

def strip_enoch_page(raw):
    """Just normalize tabs to spaces. Do NOT strip standalone-digit lines —
    in this PDF the verse markers are typeset as digits on their own line."""
    return raw.replace('\t', ' ')


def parse_enoch_chapter(book, chapter, start_pg, end_pg):
    r = get_pdf('The Complete Book of Enoch, Standard English Version - Jay Winter.pdf')
    parts = []
    for pg in range(start_pg, end_pg + 1):
        if 1 <= pg <= len(r.pages):
            parts.append(strip_enoch_page(r.pages[pg - 1].extract_text() or ''))
    full = '\n'.join(parts)

    m = re.search(rf'Chapter\s+{chapter}\b', full)
    if m:
        # Skip past the chapter heading + a possible subtitle line
        after = full[m.end():]
        # Drop next line if it looks like a subtitle
        sub = re.match(r'\s*\n([A-Z][A-Za-z\s]+)\n', after)
        if sub:
            after = after[sub.end():]
        full = after
    nxt = re.search(rf'Chapter\s+{chapter+1}\b', full)
    if nxt:
        full = full[:nxt.start()]
    full = re.sub(r'\bBook\s+\d+:\s*[A-Za-z\s]+', '', full)

    verse_pat = re.compile(rf'(?:^|\n|(?<=\s))(\d+)\s+(?=[{LETTER}“"\'])')
    matches = list(verse_pat.finditer(full))
    verses = []
    expected = 1
    for i, mm in enumerate(matches):
        try: n = int(mm.group(1))
        except: continue
        if n < 1 or n > 200: continue
        if n < expected or n > expected + 5: continue
        end = matches[i+1].start() if i+1 < len(matches) else len(full)
        text = re.sub(r'\s+', ' ', full[mm.end():end]).strip()
        if text:
            verses.append({"n": n, "t": text})
            expected = n + 1

    if not verses:
        text = re.sub(r'\s+', ' ', full).strip()
        if text:
            verses = [{"n": 1, "t": text}]
    return verses


# ---------------------------- JASHER FORMAT ----------------------------

def to_roman(n):
    vals = [(100,'C'),(90,'XC'),(50,'L'),(40,'XL'),(10,'X'),(9,'IX'),(5,'V'),(4,'IV'),(1,'I')]
    out = ''
    for v, s in vals:
        while n >= v:
            out += s; n -= v
    return out


def parse_jasher_chapter(book, chapter, start_pg, end_pg):
    r = get_pdf('unknown_book-of-jasher.pdf')
    parts = []
    for pg in range(start_pg, end_pg + 1):
        if 1 <= pg <= len(r.pages):
            parts.append(r.pages[pg - 1].extract_text() or '')
    full = '\n'.join(parts)

    rom_this = to_roman(chapter)
    rom_next = to_roman(chapter + 1)
    m = re.search(rf'(?:^|\n)\s*{rom_this}\s*(?:\n|$)', full)
    if m:
        full = full[m.end():]
    n = re.search(rf'(?:^|\n)\s*{rom_next}\s*(?:\n|$)', full)
    if n:
        full = full[:n.start()]

    # Strip page-only number lines
    full = '\n'.join(l for l in full.split('\n') if not re.match(r'^\s*\d+\s*$', l.strip()))

    verse_pat = re.compile(rf'(?:^|\n)\s*(\d+)\s+(?=[{LETTER}“"\'])')
    matches = list(verse_pat.finditer(full))
    verses = []
    expected = 1
    for i, mm in enumerate(matches):
        try: vn = int(mm.group(1))
        except: continue
        if vn < 1 or vn > 200: continue
        if vn < expected or vn > expected + 5: continue
        end = matches[i+1].start() if i+1 < len(matches) else len(full)
        text = re.sub(r'\s+', ' ', full[mm.end():end]).strip()
        if text:
            verses.append({"n": vn, "t": text})
            expected = vn + 1

    if not verses:
        text = re.sub(r'\s+', ' ', full).strip()
        if text: verses = [{"n": 1, "t": text}]
    return verses


# ---------------------------- TESTAMENTS FORMAT ----------------------------

def parse_testament(book, start_pg, end_pg):
    fname = 'THE TESTAMENTS OF THE TWELVE PATRIARCHS.pdf'
    r = get_pdf(fname)
    parts = []
    for pg in range(start_pg, end_pg + 1):
        if 1 <= pg <= len(r.pages):
            raw = r.pages[pg - 1].extract_text() or ''
            cleaned = re.sub(r'Page\s*\|\s*\d+\s*', '', raw)
            cleaned = re.sub(r'www\.Scriptural-Truth\.com', '', cleaned)
            cleaned = re.sub(r'\[The Apocrypha and Pseudepigrapha[^\]]*\]', '', cleaned)
            parts.append(cleaned)
    full = '\n'.join(parts)
    full = re.sub(r'\s+', ' ', full).strip()
    return [{"n": 1, "t": full}] if full else []


# ---------------------------- APOCRYPHA FORMAT ----------------------------

def strip_apoc_page(raw):
    txt = raw
    txt = re.sub(r'The Apocrypha:\s*Including Books from the\s*Ethiopic Bible\s*', '', txt)
    txt = re.sub(r'Joseph B\. Lumpkin\s*', '', txt)
    txt = '\n'.join(l for l in txt.split('\n') if not re.match(r'^\s*\d+\s*$', l.strip()))
    return txt


def parse_apocrypha_chapter(book, chapter, start_pg, end_pg):
    fname = 'ilide.info-the-apocrypha-including-books-from-the-ethiopic-bible-pr_08c2e4c2f2223e5d640766290ee98f9b.pdf'
    r = get_pdf(fname)
    parts = []
    for pg in range(start_pg, end_pg + 1):
        if 1 <= pg <= len(r.pages):
            parts.append(strip_apoc_page(r.pages[pg - 1].extract_text() or ''))
    full = '\n'.join(parts)

    m = re.search(rf'Chapter\s+{chapter}\b', full)
    if m:
        full = full[m.end():]
    n = re.search(rf'Chapter\s+{chapter+1}\b', full)
    if n:
        full = full[:n.start()]

    # Bracketed verse markers: [1], [2], …
    verse_pat = re.compile(r'\[(\d+)\]\s+')
    matches = list(verse_pat.finditer(full))
    verses = []
    if matches:
        expected = 1
        for i, mm in enumerate(matches):
            try: vn = int(mm.group(1))
            except: continue
            if vn < 1 or vn > 200: continue
            if vn < expected or vn > expected + 5: continue
            end = matches[i+1].start() if i+1 < len(matches) else len(full)
            text = re.sub(r'\s+', ' ', full[mm.end():end]).strip()
            if text:
                verses.append({"n": vn, "t": text})
                expected = vn + 1

    if not verses:
        # Fallback to plain numeric markers
        verse_pat2 = re.compile(rf'(?:^|\n|(?<=\s))(\d+)\s+(?=[{LETTER}“"\'])')
        matches = list(verse_pat2.finditer(full))
        expected = 1
        for i, mm in enumerate(matches):
            try: vn = int(mm.group(1))
            except: continue
            if vn < 1 or vn > 200: continue
            if vn < expected or vn > expected + 5: continue
            end = matches[i+1].start() if i+1 < len(matches) else len(full)
            text = re.sub(r'\s+', ' ', full[mm.end():end]).strip()
            if text:
                verses.append({"n": vn, "t": text})
                expected = vn + 1

    if not verses:
        text = re.sub(r'\s+', ' ', full).strip()
        if text: verses = [{"n": 1, "t": text}]
    return verses


# ---------------------------- BUILD ----------------------------

def build():
    with open(INDEX_IN, encoding='utf-8') as f:
        index = json.load(f)

    # Build a lookup: for each (pdf, current chapter end) → next book's start page in same PDF.
    # Collect all (pdf, start_page) pairs across books to find "next anchor in PDF".
    all_anchors = {}   # pdf -> sorted list of start pages
    for b in index['books']:
        for ch_dat in b['chapters'].values():
            all_anchors.setdefault(ch_dat['pdf'], []).append(ch_dat['page'])
    for k in all_anchors:
        all_anchors[k] = sorted(set(all_anchors[k]))

    def next_anchor_after(pdf, page):
        """Return the next chapter/book start page in this PDF after `page`."""
        for p in all_anchors.get(pdf, []):
            if p > page:
                return p
        return None

    for book in index['books']:
        bid     = book['id']
        section = book['section']
        chapters = book['chapters']
        ch_count = book['chapter_count']
        out_chapters = {}

        for ch in range(1, ch_count + 1):
            cdat = chapters.get(str(ch))
            if not cdat: continue
            start_pg = cdat['page']
            next_ch = chapters.get(str(ch + 1))
            if next_ch and next_ch['pdf'] == cdat['pdf']:
                end_pg = max(start_pg, next_ch['page'])
            else:
                # Last chapter of this book: end at next book's start page in same PDF
                nxt = next_anchor_after(cdat['pdf'], start_pg)
                end_pg = (nxt - 1) if nxt else (start_pg + 6)
                # Safety cap: no more than 12 pages for a single chapter
                end_pg = min(end_pg, start_pg + 12)
            try:
                if section in ("Torah", "Nebi'im", "Kethubim", "Messianic"):
                    verses = parse_besorah_chapter(book, ch, start_pg, end_pg)
                elif bid == "chanok":
                    verses = parse_enoch_chapter(book, ch, start_pg, end_pg)
                elif bid == "yashar":
                    verses = parse_jasher_chapter(book, ch, start_pg, end_pg)
                elif section == "Patriarchs":
                    verses = parse_testament(book, start_pg, end_pg)
                elif section == "Apocrypha":
                    verses = parse_apocrypha_chapter(book, ch, start_pg, end_pg)
                else:
                    verses = []
            except Exception as e:
                print(f'  ERR {bid} ch {ch}: {e}')
                verses = []

            out_chapters[str(ch)] = {
                "verses": verses,
                "page": start_pg,
                "pdf": cdat['pdf'],
            }

        out_book = {
            "id": bid,
            "hebrew": book['hebrew'],
            "english": book['english'],
            "section": section,
            "chapter_count": ch_count,
            "chapters": out_chapters,
        }
        outpath = os.path.join(OUT_DIR, f'{bid}.json')
        with open(outpath, 'w', encoding='utf-8') as f:
            json.dump(out_book, f, ensure_ascii=False, indent=1)
        total_v = sum(len(c['verses']) for c in out_chapters.values())
        print(f'{bid}: {len(out_chapters)} chapters, {total_v} verses')


if __name__ == '__main__':
    build()
