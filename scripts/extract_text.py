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
import pdfplumber
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


# ---- Column-aware extraction (for the Besorah PDFs which use 2-column psalms) ----
_plumber_cache = {}
def get_plumber(name):
    if name not in _plumber_cache:
        _plumber_cache[name] = pdfplumber.open(os.path.join(PDF_DIR, name))
    return _plumber_cache[name]


def _group_lines(words, line_tol=5):
    """Group words into lines, then sort each line left-to-right.

    Step 1: assign each word to a line whose representative `top` is within
    `line_tol` (5 px). This handles the palaeo-Hebrew Tetragrammaton (HWHY)
    sitting ~2 px above the regular baseline: it joins its actual line
    instead of being lifted to its own row.

    Step 2: sort each line's words by x0 so the visual reading order is
    preserved.

    Step 3: sort lines by the line's mean `top`."""
    if not words:
        return []
    # First pass: build lines by walking words sorted by top
    by_top = sorted(words, key=lambda w: w['top'])
    line_buckets = []   # list of {anchor_top, words[]}
    for w in by_top:
        placed = False
        for b in line_buckets:
            if abs(w['top'] - b['anchor_top']) <= line_tol:
                b['words'].append(w)
                # Update anchor to running mean for stability
                b['anchor_top'] = sum(x['top'] for x in b['words']) / len(b['words'])
                placed = True
                break
        if not placed:
            line_buckets.append({'anchor_top': w['top'], 'words': [w]})
    # Sort buckets top-to-bottom
    line_buckets.sort(key=lambda b: b['anchor_top'])
    # Within each line, sort by x0 and join
    return [' '.join(x['text'] for x in sorted(b['words'], key=lambda x: x['x0']))
            for b in line_buckets]


def extract_page_text(pdf_filename, page_num):
    """Column-aware text extraction. Auto-detects single vs two-column pages
    and returns text in proper reading order (col 1 then col 2 for two-column).

    Page-header words (book name banners that span both columns) are
    detected by being either (a) wide enough that they span the column
    gutter, or (b) high on the page above the first body row, and emitted
    once at the start instead of being shoved into one column."""
    pdf = get_plumber(pdf_filename)
    if not (1 <= page_num <= len(pdf.pages)):
        return ''
    page = pdf.pages[page_num - 1]
    words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
    if not words:
        return ''
    width = page.width
    mid = width / 2

    # Header detection: top region of the page that contains words spanning
    # the column gutter (book title banner). Find the lowest y of any
    # gutter-spanning word and treat everything at-or-above as header.
    header_y = 0
    for w in words:
        spans_gutter = w['x0'] < mid - 5 and w['x1'] > mid + 5
        if spans_gutter and w['top'] < page.height * 0.15:
            header_y = max(header_y, w['bottom'])

    header = [w for w in words if w['top'] < header_y - 0.5]
    body   = [w for w in words if w['top'] >= header_y - 0.5]

    left  = [w for w in body if w['x0'] + (w['x1'] - w['x0']) / 2 < mid]
    right = [w for w in body if w['x0'] + (w['x1'] - w['x0']) / 2 >= mid]

    # Single-column: if either side is very thin, treat as one column.
    if len(body) and (len(right) < 0.20 * len(body) or len(left) < 0.20 * len(body)):
        return '\n'.join(_group_lines(body))

    return '\n'.join(_group_lines(header) + _group_lines(left) + _group_lines(right))


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
        # Page-only number like "43" — must be > 200 (printed page numbers) so a
        # standalone verse-number drop cap like "1" or "2" isn't dropped here.
        m = re.match(r'^(\d+)\s*$', first)
        if m and int(m.group(1)) > 200:
            lines.pop(0); drops += 1; continue
        # Lower page numbers (1..200) are dropped only if they appear at the very top.
        if drops == 0 and m:
            lines.pop(0); drops += 1; continue
        # "44    BERĔSHITH 2", "278Yahusha 2", "3361 SHEMU'ĔL 1",
        # "989 2 DIḆRE haYAMIM 22" — running header with leading page number,
        # optional book-prefix digit ("1 ", "2 "), book name, optional chapter.
        if len(first) <= 35 and re.match(
            rf"^\d+\s+(?:\d\s+)?[{UPPER}][{LETTER}'\s\-]*?(?:\s+\d+){{0,2}}\s*$", first):
            lines.pop(0); drops += 1; continue
        # "BERĔSHITH", "BERĔSHITH 2", "BERĔSHITH 43 92", "2 DIḆRE haYAMIM 22 989"
        # — Hebrew name optionally preceded by a book-prefix digit and followed
        # by chapter and/or page numbers.
        if len(first) <= 35 and re.match(
            rf"^(?:\d\s+)?[{UPPER}][{LETTER}'\s\-]+(?:\s+\d+){{0,2}}\s*$", first):
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

    parts = []
    for pg in range(start_pg, end_pg + 1):
        # Use column-aware extraction so 2-column Tehillim pages don't interleave verses
        cleaned = strip_besorah_page(extract_page_text(pdf_file, pg))
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


# ---------------------------- ADAM & EVE FORMAT ----------------------------

def parse_adam_eve_chapter(book, chapter, start_pg, end_pg):
    """First / Second Book of Adam and Eve.
    First book uses `Chapter <Roman>`; second uses `CHAP. <Roman>.`."""
    fname = book['chapters'][str(chapter)]['pdf']
    r = get_pdf(fname)

    def to_roman(n):
        vals = [(100,'C'),(90,'XC'),(50,'L'),(40,'XL'),(10,'X'),(9,'IX'),(5,'V'),(4,'IV'),(1,'I')]
        out = ''
        for v, s in vals:
            while n >= v:
                out += s; n -= v
        return out

    parts = []
    for pg in range(start_pg, end_pg + 1):
        if 1 <= pg <= len(r.pages):
            parts.append(r.pages[pg - 1].extract_text() or '')
    full = '\n'.join(parts)

    rom_this = to_roman(chapter)
    rom_next = to_roman(chapter + 1)
    if fname == '78.pdf':
        # second book uses "CHAP. I."
        this_pat = rf'CHAP\.\s+{rom_this}\.'
        next_pat = rf'CHAP\.\s+{rom_next}\.'
    else:
        this_pat = rf'Chapter\s+{rom_this}\b'
        next_pat = rf'Chapter\s+{rom_next}\b'

    m = re.search(this_pat, full)
    if m:
        full = full[m.end():]
        # Skip leading whitespace/newlines, then a chapter subtitle line
        # (e.g. "The grief stricken family. Cain marries Luluwa and they move
        # away.") that follows the chapter heading and precedes verse 1.
        full = full.lstrip('\n\r ')
        first_break = full.find('\n')
        if 0 < first_break < 200:
            first_line = full[:first_break].strip()
            # Only skip if the line is a descriptive subtitle (no verse marker
            # and not the start of verse 1 text).
            if not re.match(r'^\s*1\s', first_line) and first_line.endswith('.'):
                full = full[first_break + 1:]

    n = re.search(next_pat, full)
    if n:
        full = full[:n.start()]

    # Clean header noise
    full = re.sub(r'http\S+', '', full)
    full = re.sub(r'(?i)blackmask', '', full)

    # Parse verses
    verse_pat = re.compile(r'(?:^|\n)\s*(\d+)\s+(?=[A-Za-z“"\'])')
    matches = list(verse_pat.finditer(full))
    verses = []
    expected = 1
    # If the first verse marker is "2" (no leading "1"), the chapter's first
    # paragraph is unnumbered verse 1. Capture it from the start of `full`.
    if matches and int(matches[0].group(1)) == 2:
        v1_text = re.sub(r'\s+', ' ', full[:matches[0].start()]).strip()
        if v1_text:
            verses.append({"n": 1, "t": v1_text})
            expected = 2
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
    # Strip the apocrypha PDF's inline chapter labels — `Wis.8`, `Jdt.9`,
    # `Sir.51`, `Tob.14`, `Bar.6`, `Bel.1`, `IMac.16`, etc. — that mark
    # the next chapter and otherwise bleed into the prior chapter's text.
    txt = re.sub(r'\b(?:Wis|Jdt|Sir|Tob|Bar|Bel|IMac|IIMac|IIIMac|IVMac|Esd|Mac)\.\s*\d+\b', '', txt)
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

    bid = book['id']

    # ---- 1 Clements: verse markers like "1Clem 1:5\n<text>"
    if bid == 'apoc-1clements':
        # Find this chapter's start (first occurrence of "1Clem <chapter>:")
        m = re.search(rf'1Clem\s+{chapter}\s*:\s*\d+', full)
        if m:
            full = full[m.start():]
        n = re.search(rf'1Clem\s+{chapter+1}\s*:\s*\d+', full)
        if n:
            full = full[:n.start()]
        verse_pat = re.compile(rf'1Clem\s+{chapter}\s*:\s*(\d+)\s*')
        matches = list(verse_pat.finditer(full))
        verses = []
        for i, mm in enumerate(matches):
            try: vn = int(mm.group(1))
            except: continue
            if vn < 1 or vn > 100: continue
            end = matches[i+1].start() if i+1 < len(matches) else len(full)
            text = re.sub(r'\s+', ' ', full[mm.end():end]).strip()
            if text:
                verses.append({"n": vn, "t": text})
        return verses or [{"n": 1, "t": re.sub(r'\s+', ' ', full).strip()}]

    # ---- Shepherd of Hermas: verse markers "1:5", "2:10", etc.
    if bid == 'apoc-hermas':
        # Trim to this chapter only by matching "<chapter>:<n>" markers
        # Find first marker for this chapter
        pat = re.compile(rf'(?:^|\n|\s){chapter}\s*:\s*(\d+)\s')
        # Limit to this chapter range
        m = pat.search(full)
        if m:
            full = full[m.start():]
        nxt = re.search(rf'(?:^|\n|\s){chapter+1}\s*:\s*1\s', full)
        if nxt:
            full = full[:nxt.start()]
        verse_pat = re.compile(rf'(?:^|\n|\s){chapter}\s*:\s*(\d+)\s')
        matches = list(verse_pat.finditer(full))
        verses = []
        for i, mm in enumerate(matches):
            try: vn = int(mm.group(1))
            except: continue
            if vn < 1 or vn > 100: continue
            end = matches[i+1].start() if i+1 < len(matches) else len(full)
            text = re.sub(r'\s+', ' ', full[mm.end():end]).strip()
            if text:
                verses.append({"n": vn, "t": text})
        return verses or [{"n": 1, "t": re.sub(r'\s+', ' ', full).strip()}]

    # ---- Standard apocrypha: "Chapter <N>" + bracketed verse markers
    m = re.search(rf'Chapter\s+{chapter}\b', full)
    if m:
        full = full[m.end():]
    n = re.search(rf'Chapter\s+{chapter+1}\b', full)
    if n:
        full = full[:n.start()]

    # Bracketed verse markers: [1], [2], …
    # Sirach uses ranges like [1-14], [15-26]; expand to start verse only.
    verse_pat = re.compile(r'\[(\d+)(?:\s*-\s*\d+)?\]\s*')
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
                elif bid in ("adam-eve-1", "adam-eve-2"):
                    verses = parse_adam_eve_chapter(book, ch, start_pg, end_pg)
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
