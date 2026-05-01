"""Extract chapter -> PDF page index from each scripture PDF.

Outputs scripts/index.json with structure:
{
  "books": [
    {"id": "bereshith",
     "hebrew": "BEREISHITH",
     "english": "Genesis",
     "section": "Torah",
     "pdf": "TheBesorah-all.0001.pdf",
     "chapters": {"1": 43, "2": 44, ...}        # PDF page numbers (1-indexed)
    }, ...
  ]
}
"""
from pypdf import PdfReader
import re, json, os, unicodedata

PDF_DIR = os.path.join(os.path.dirname(__file__), "..", "SCRIPTURE")
OUT     = os.path.join(os.path.dirname(__file__), "index.json")

# Books in TheBesorah, in order, with (id, display Hebrew, english, section, expected start printed page)
BESORAH_BOOKS = [
    # Torah
    ("bereshith",      "BERĔSHITH",        "Genesis",        "Torah",  43, 50),
    ("shemoth",        "SHEMOTH",          "Exodus",         "Torah",  102, 40),
    ("wayyiqra",       "WAYYIQRA",         "Leviticus",      "Torah",  150, 27),
    ("bemidbar",       "BEMIḎBAR",         "Numbers",        "Torah",  185, 36),
    ("debarim",        "DEḆARIM",          "Deuteronomy",    "Torah",  235, 34),
    # Nebi'im
    ("yahusha",        "YAHUSHA",          "Joshua",         "Nebi'im", 277, 24),
    ("shophetim",      "SHOPHETIM",        "Judges",         "Nebi'im", 306, 21),
    ("1shemuel",       "1 SHEMU'ĔL",       "1 Samuel",       "Nebi'im", 335, 31),
    ("2shemuel",       "2 SHEMU'ĔL",       "2 Samuel",       "Nebi'im", 372, 24),
    ("1melakim",       "1 MELAḴIM",        "1 Kings",        "Nebi'im", 404, 22),
    ("2melakim",       "2 MELAḴIM",        "2 Kings",        "Nebi'im", 441, 25),
    ("yeshayahu",      "YESHAYAHU",        "Isaiah",         "Nebi'im", 476, 66),
    ("yirmeyahu",      "YIRMEYAHU",        "Jeremiah",       "Nebi'im", 531, 52),
    ("yehezqel",       "YEḤEZQ'ĔL",        "Ezekiel",        "Nebi'im", 595, 48),
    ("daniel",         "DANI'ĔL",          "Daniel",         "Nebi'im", 652, 12),
    ("hoshea",         "HOSHĔA",           "Hosea",          "Nebi'im", 670, 14),
    ("yoel",           "YO'ĔL",            "Joel",           "Nebi'im", 678, 3),
    ("amos",           "AMOS",             "Amos",           "Nebi'im", 682, 9),
    ("obadyah",        "OḆADYAH",          "Obadiah",        "Nebi'im", 689, 1),
    ("yonah",          "YONAH",            "Jonah",          "Nebi'im", 690, 4),
    ("mikah",          "MIḴAH",            "Micah",          "Nebi'im", 693, 7),
    ("nahum",          "NAḤUM",            "Nahum",          "Nebi'im", 698, 3),
    ("habaqquq",       "ḤAḆAQQUQ",         "Habakkuk",       "Nebi'im", 700, 3),
    ("tsephanyah",     "TSEPHANYAH",       "Zephaniah",      "Nebi'im", 703, 3),
    ("haggai",         "ḤAGGAI",           "Haggai",         "Nebi'im", 706, 2),
    ("zekaryah",       "ZEḴARYAH",         "Zechariah",      "Nebi'im", 708, 14),
    ("malaki",         "MAL'AḴI",          "Malachi",        "Nebi'im", 718, 4),
    # Kethubim
    ("tehillim",       "TEHILLIM",         "Psalms",         "Kethubim", 721, 150),
    ("mishle",         "MISHLĔ",           "Proverbs",       "Kethubim", 810, 31),
    ("iyob",           "IYOḆ",             "Job",            "Kethubim", 841, 42),
    ("shir-hashirim",  "SHIR HASHIRIM",    "Song of Songs",  "Kethubim", 870, 8),
    ("ruth",           "RUTH",             "Ruth",           "Kethubim", 876, 4),
    ("ekah",           "ĔḴAH",             "Lamentations",   "Kethubim", 880, 5),
    ("qoheleth",       "QOHELETH",         "Ecclesiastes",   "Kethubim", 888, 12),
    ("ester",          "ESTĔR",            "Esther",         "Kethubim", 897, 10),
    ("ezra",           "EZRA",             "Ezra",           "Kethubim", 906, 10),
    ("nehemyah",       "NEḤEMYAH",         "Nehemiah",       "Kethubim", 918, 13),
    ("1dibre-hayamim", "1 DIḆRĔ HAYAMIM",  "1 Chronicles",   "Kethubim", 935, 29),
    ("2dibre-hayamim", "2 DIḆRĔ HAYAMIM",  "2 Chronicles",   "Kethubim", 969, 36),
    # Messianic
    ("mattithyahu",    "MATTITHYAHU",      "Matthew",        "Messianic", 1021, 28),
    ("mark",           "MARK",             "Mark",           "Messianic", 1059, 16),
    ("luke",           "LUKE",             "Luke",           "Messianic", 1083, 24),
    ("yahuchanon",     "YAHUCHANON",       "John",           "Messianic", 1123, 21),
    ("acts",           "ACTS",             "Acts",           "Messianic", 1154, 28),
    ("romans",         "ROMANS",           "Romans",         "Messianic", 1193, 16),
    ("1corinthians",   "1 CORINTHIANS",    "1 Corinthians",  "Messianic", 1209, 16),
    ("2corinthians",   "2 CORINTHIANS",    "2 Corinthians",  "Messianic", 1224, 13),
    ("galatians",      "GALATIANS",        "Galatians",      "Messianic", 1234, 6),
    ("ephesians",      "EPHESIANS",        "Ephesians",      "Messianic", 1240, 6),
    ("philippians",    "PHILIPPIANS",      "Philippians",    "Messianic", 1246, 4),
    ("colossians",     "COLOSSIANS",       "Colossians",     "Messianic", 1250, 4),
    ("1thessalonians", "1 THESSALONIANS",  "1 Thessalonians","Messianic", 1254, 5),
    ("2thessalonians", "2 THESSALONIANS",  "2 Thessalonians","Messianic", 1258, 3),
    ("1timothy",       "1 TIMOTHY",        "1 Timothy",      "Messianic", 1260, 6),
    ("2timothy",       "2 TIMOTHY",        "2 Timothy",      "Messianic", 1264, 4),
    ("titus",          "TITUS",            "Titus",          "Messianic", 1267, 3),
    ("philemon",       "PHILĔMON",         "Philemon",       "Messianic", 1269, 1),
    ("ibrim",          "IḆRIM",            "Hebrews",        "Messianic", 1270, 13),
    ("yaaqob",         "YA'AQOḆ",          "James",          "Messianic", 1282, 5),
    ("1kepha",         "1 KĔPHA",          "1 Peter",        "Messianic", 1286, 5),
    ("2kepha",         "2 KĔPHA",          "2 Peter",        "Messianic", 1291, 3),
    ("1yahuchanon",    "1 YAHUCHANON",     "1 John",         "Messianic", 1294, 5),
    ("2yahuchanon",    "2 YAHUCHANON",     "2 John",         "Messianic", 1298, 1),
    ("3yahuchanon",    "3 YAHUCHANON",     "3 John",         "Messianic", 1299, 1),
    ("yahudah",        "YAHUDAH",          "Jude",           "Messianic", 1300, 1),
    ("hazon",          "ḤAZON",            "Revelation",     "Messianic", 1302, 22, "REVELATION"),
]

def normalize(s):
    """Strip accents, normalize curly quotes/dashes to ASCII, uppercase."""
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    # Normalize Unicode punctuation that varies between source and our table
    for src, dst in [('‘', "'"), ('’', "'"), ('“', '"'), ('”', '"'),
                     ('—', '-'), ('–', '-')]:
        s = s.replace(src, dst)
    return s.upper()

def printed_to_pdf(printed_page):
    """0001.pdf covers printed pages 1-700; 0002.pdf covers 701-1344."""
    if printed_page <= 700:
        return ("TheBesorah-all.0001.pdf", printed_page)
    return ("TheBesorah-all.0002.pdf", printed_page - 700)

def build_besorah_index():
    # Use column-aware extraction so 2-column psalms pages produce correct chapter detection.
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from extract_text import extract_page_text

    def get_text(printed):
        if printed <= 700:
            return extract_page_text("TheBesorah-all.0001.pdf", printed)
        return extract_page_text("TheBesorah-all.0002.pdf", printed - 700)

    books = []
    for idx, entry in enumerate(BESORAH_BOOKS):
        # Allow optional 7th element: text used to match chapter headers in PDF
        bid, heb, eng, section, start, ch_count = entry[:6]
        match_name = entry[6] if len(entry) > 6 else heb
        # End printed page = next book's start - 1, or 1320 for last (Revelation ends ~1320)
        if idx + 1 < len(BESORAH_BOOKS):
            end = BESORAH_BOOKS[idx + 1][4] - 1
        else:
            end = 1320
        # Build chapter -> printed page map
        ch_pages = {}
        ch_pages[1] = start

        heb_norm = normalize(match_name)
        heb_norm_nospace = heb_norm.replace(" ", "")

        # Walk pages in order, looking for actual chapter starts in the body
        # (digit alone on a line followed by a capital — the Besorah's drop-cap
        # convention). The running page header (e.g. "TEHILLIM 51") is NOT
        # reliable, because the Besorah's running head sometimes references a
        # psalm that begins on a later page.
        # We DO use the running header for the FIRST chapter of each book, since
        # the header on the first page reliably says "<book> 1".
        first_page_txt = get_text(start)
        first_head = normalize(first_page_txt[:200])
        for pat in (rf'{re.escape(heb_norm)}\s+(\d+)',
                    rf'{re.escape(heb_norm_nospace)}\s*(\d+)'):
            m = re.search(pat, first_head)
            if m:
                ch = int(m.group(1))
                if 1 <= ch <= ch_count and ch not in ch_pages:
                    ch_pages[ch] = start
                break

        for p in range(start, end + 1):
            txt = get_text(p)
            # Body chapter starts: a digit on its own line followed by a capital.
            # Exclude only the FIRST LINE (which is the running header like
            # "TEHILLIM 51" or "653 DANI'EL 2") so a chapter heading on row 2 is
            # still detected.
            first_nl = txt.find('\n')
            body = txt[first_nl + 1:] if first_nl != -1 else txt
            for m in re.finditer(r'(?:^|\n)\s*(\d+)\s*\n\s*(?=[A-ZÀ-￿"“‘\'])', body):
                ch = int(m.group(1))
                if 1 <= ch <= ch_count and ch not in ch_pages:
                    ch_pages[ch] = p

        # Fill missing chapters via interpolation between known anchors
        anchors = sorted(ch_pages.items())
        complete = {}
        for i, (ch, page) in enumerate(anchors):
            complete[ch] = page
        # Fill gaps
        for ch in range(1, ch_count + 1):
            if ch in complete:
                continue
            # find prev and next anchor
            prev_ch = max((c for c in complete if c < ch), default=None)
            next_ch = min((c for c in complete if c > ch), default=None)
            if prev_ch is not None and next_ch is not None:
                # linear interpolation
                p1, p2 = complete[prev_ch], complete[next_ch]
                interp = p1 + round((p2 - p1) * (ch - prev_ch) / (next_ch - prev_ch))
                complete[ch] = interp
            elif prev_ch is not None:
                complete[ch] = complete[prev_ch]
            elif next_ch is not None:
                complete[ch] = complete[next_ch]
            else:
                complete[ch] = start

        # Convert printed pages to (pdf, page)
        chapters = {}
        for ch in sorted(complete):
            pdf_file, pdf_pg = printed_to_pdf(complete[ch])
            chapters[str(ch)] = {"pdf": pdf_file, "page": pdf_pg, "printed": complete[ch]}

        books.append({
            "id": bid, "hebrew": heb, "english": eng, "section": section,
            "chapter_count": ch_count,
            "chapters": chapters,
        })
        print(f'{bid}: {len(complete)}/{ch_count} chapters mapped (start={start})')
    return books

# ============================================================
# OTHER PDFs - book of Enoch, Jasher, Testaments of 12 Patriarchs, Apocrypha
# ============================================================

def build_enoch():
    """The Complete Book of Enoch - 193 pages.
    Structure: Book of Enoch (1 Enoch) — 108 chapters.
    Headers use tab characters: 'Chapter\\t<N>'."""
    fname = 'The Complete Book of Enoch, Standard English Version - Jay Winter.pdf'
    r = PdfReader(os.path.join(PDF_DIR, fname))
    chapters = {}
    for i, page in enumerate(r.pages):
        txt = page.extract_text() or ''
        # Tab-separated: "Chapter\t1"
        for m in re.finditer(r'Chapter[\s\t]+(\d+)', txt):
            ch = int(m.group(1))
            if 1 <= ch <= 108 and str(ch) not in chapters:
                chapters[str(ch)] = {"pdf": fname, "page": i + 1, "printed": i + 1}
    # Linear interpolation for any missing chapters
    if chapters:
        anchors = sorted((int(k), v["page"]) for k, v in chapters.items())
        for ch in range(1, 109):
            if str(ch) in chapters: continue
            prev = max((c for c, _ in anchors if c < ch), default=None)
            nxt  = min((c for c, _ in anchors if c > ch), default=None)
            if prev is not None and nxt is not None:
                p1 = next(p for c, p in anchors if c == prev)
                p2 = next(p for c, p in anchors if c == nxt)
                interp = p1 + round((p2 - p1) * (ch - prev) / (nxt - prev))
                chapters[str(ch)] = {"pdf": fname, "page": interp, "printed": interp}
            elif prev is not None:
                p = next(pp for c, pp in anchors if c == prev)
                chapters[str(ch)] = {"pdf": fname, "page": p, "printed": p}
            elif nxt is not None:
                p = next(pp for c, pp in anchors if c == nxt)
                chapters[str(ch)] = {"pdf": fname, "page": p, "printed": p}
    print(f'enoch: {len(chapters)}/108 chapters mapped')
    return [{
        "id": "chanok",
        "hebrew": "ḤANOḴ",
        "english": "Enoch",
        "section": "Apocryphal",
        "chapter_count": 108,
        "chapters": chapters,
    }]

def build_jasher():
    """unknown_book-of-jasher.pdf - 297 pages, 91 chapters numbered as Roman numerals.
    Headers are Roman numerals on their own line: I, II, III, ..., XCI."""
    fname = 'unknown_book-of-jasher.pdf'
    r = PdfReader(os.path.join(PDF_DIR, fname))

    def roman_to_int(s):
        vals = {'I':1,'V':5,'X':10,'L':50,'C':100,'D':500,'M':1000}
        s = s.upper()
        total, prev = 0, 0
        for c in reversed(s):
            v = vals.get(c, 0)
            if v < prev: total -= v
            else: total += v; prev = v
        return total

    chapters = {}
    # Detect contents page(s) — many roman numerals listed in close succession with no verses.
    # Skip the first ~8 pages (Jasher's table of contents) when scanning for chapter starts.
    SKIP_PRE = 6
    for i, page in enumerate(r.pages):
        if i < SKIP_PRE:
            continue
        txt = page.extract_text() or ''
        # A real chapter heading is a Roman numeral on its own line followed by a verse-1 marker
        # within a short window.
        for m in re.finditer(r'(?:^|\n)\s*([IVXLC]+)\s*\n', txt):
            r_str = m.group(1)
            try:
                ch = roman_to_int(r_str)
            except Exception:
                continue
            if not (1 <= ch <= 91): continue
            if str(ch) in chapters: continue
            # Confirm a verse-1 marker follows within ~80 chars
            tail = txt[m.end(): m.end() + 200]
            if re.search(r'^\s*1\s+[A-Z“"\']', tail):
                chapters[str(ch)] = {"pdf": fname, "page": i + 1, "printed": i + 1}
    # Interpolate
    if chapters:
        anchors = sorted((int(k), v["page"]) for k, v in chapters.items())
        for ch in range(1, 92):
            if str(ch) in chapters: continue
            prev = max((c for c, _ in anchors if c < ch), default=None)
            nxt  = min((c for c, _ in anchors if c > ch), default=None)
            if prev and nxt:
                p1 = next(p for c, p in anchors if c == prev)
                p2 = next(p for c, p in anchors if c == nxt)
                interp = p1 + round((p2 - p1) * (ch - prev) / (nxt - prev))
                chapters[str(ch)] = {"pdf": fname, "page": interp, "printed": interp}
            elif prev:
                p = next(pp for c, pp in anchors if c == prev)
                chapters[str(ch)] = {"pdf": fname, "page": p, "printed": p}
            elif nxt:
                p = next(pp for c, pp in anchors if c == nxt)
                chapters[str(ch)] = {"pdf": fname, "page": p, "printed": p}
    print(f'jasher: {len(chapters)}/91 chapters mapped')
    return [{
        "id": "yashar",
        "hebrew": "YASHAR",
        "english": "Jasher",
        "section": "Apocryphal",
        "chapter_count": 91,
        "chapters": chapters,
    }]

def build_adam_eve():
    """First and Second Book of Adam and Eve.

    44.pdf — First Book, 79 chapters with `Chapter <Roman>` headings.
    78.pdf — Second Book, 22 chapters with `CHAP. <Roman>.` headings.
    """
    def roman_to_int(s):
        vals = {'I':1,'V':5,'X':10,'L':50,'C':100,'D':500,'M':1000}
        total, prev = 0, 0
        for c in reversed(s.upper()):
            v = vals.get(c, 0)
            if v < prev: total -= v
            else: total += v; prev = v
        return total

    def to_roman(n):
        vals = [(100,'C'),(90,'XC'),(50,'L'),(40,'XL'),(10,'X'),(9,'IX'),(5,'V'),(4,'IV'),(1,'I')]
        out = ''
        for v, s in vals:
            while n >= v:
                out += s; n -= v
        return out

    def map_book(fname, pattern, total):
        r = PdfReader(os.path.join(PDF_DIR, fname))
        chapters = {}
        # Skip TOC pages (first ~5)
        SKIP_PRE = 5
        for i, page in enumerate(r.pages):
            if i < SKIP_PRE:
                continue
            txt = page.extract_text() or ''
            for m in re.finditer(pattern, txt):
                rom = m.group(1)
                ch = roman_to_int(rom)
                if not (1 <= ch <= total): continue
                if str(ch) in chapters: continue
                # Confirm a verse-1 marker follows nearby
                tail = txt[m.end(): m.end() + 200]
                if re.search(r'(?:^|\n)\s*1\s+[A-Z“"\']', tail) or re.search(r'^\s*\w', tail):
                    chapters[str(ch)] = {"pdf": fname, "page": i + 1, "printed": i + 1}
        # Interpolate
        if chapters:
            anchors = sorted((int(k), v["page"]) for k, v in chapters.items())
            for ch in range(1, total + 1):
                if str(ch) in chapters: continue
                prev = max((c for c, _ in anchors if c < ch), default=None)
                nxt  = min((c for c, _ in anchors if c > ch), default=None)
                if prev and nxt:
                    p1 = next(p for c, p in anchors if c == prev)
                    p2 = next(p for c, p in anchors if c == nxt)
                    interp = p1 + round((p2 - p1) * (ch - prev) / (nxt - prev))
                elif prev:
                    interp = next(pp for c, pp in anchors if c == prev)
                else:
                    interp = next(pp for c, pp in anchors if c == nxt)
                chapters[str(ch)] = {"pdf": fname, "page": interp, "printed": interp}
        return chapters

    book1 = map_book('44.pdf', r'Chapter\s+([IVXLC]+)', 79)
    book2 = map_book('78.pdf', r'CHAP\.\s+([IVXLC]+)\.', 22)
    print(f'adam-eve-1: {len(book1)}/79 chapters mapped')
    print(f'adam-eve-2: {len(book2)}/22 chapters mapped')
    return [
        {"id": "adam-eve-1", "hebrew": "ADAM WAḤAWWAH 1", "english": "First Book of Adam and Eve",
         "section": "Apocryphal", "chapter_count": 79, "chapters": book1},
        {"id": "adam-eve-2", "hebrew": "ADAM WAḤAWWAH 2", "english": "Second Book of Adam and Eve",
         "section": "Apocryphal", "chapter_count": 22, "chapters": book2},
    ]


def build_testaments():
    """THE TESTAMENTS OF THE TWELVE PATRIARCHS - 46 pages.
    Each testament is a single book."""
    fname = 'THE TESTAMENTS OF THE TWELVE PATRIARCHS.pdf'
    r = PdfReader(os.path.join(PDF_DIR, fname))
    PATRIARCHS = [
        ("reuben",    "RE'UḆĔN",   "REUBEN"),
        ("shimeon",   "SHIM'ON",   "SIMEON"),
        ("levi",      "LĔWI",      "LEVI"),
        ("yahudah",   "YAHUDAH",   "JUDAH"),
        ("issakar",   "YISSAKAR",  "ISSACHAR"),
        ("zebulun",   "ZEḆULUN",   "ZEBULUN"),
        ("dan",       "DAN",       "DAN"),
        ("naphtali",  "NAPHTALI",  "NAPHTALI"),
        ("gad",       "GAD",       "GAD"),
        ("asher",     "ASHĔR",     "ASHER"),
        ("yoseph",    "YOSĔPH",    "JOSEPH"),
        ("benyamin",  "BENYAMIN",  "BENJAMIN"),
    ]
    # Testament starts use the pattern "1 1 The copy of the Testament/words of <Name>"
    # Patriarchs appear in canonical order across pages. We assign them by sequence.
    starts = []
    for i in range(len(r.pages)):
        txt = r.pages[i].extract_text() or ''
        if re.search(r'1\s+1[,\s]*\d*\s+The copy of', txt):
            starts.append(i + 1)
    pages = {}
    for idx, (pid, heb, eng_upper) in enumerate(PATRIARCHS):
        if idx < len(starts):
            pages[pid] = starts[idx]
    books = []
    for pid, heb, eng_upper in PATRIARCHS:
        chapters = {}
        if pid in pages:
            chapters["1"] = {"pdf": fname, "page": pages[pid], "printed": pages[pid]}
        books.append({
            "id": f"testament-{pid}",
            "hebrew": f"TESTAMENT OF {heb}",
            "english": f"Testament of {eng_upper.title()}",
            "section": "Patriarchs",
            "chapter_count": 1,
            "chapters": chapters,
        })
    print(f'testaments: {len(pages)}/12 patriarchs located')
    return books

def build_apocrypha():
    """ilide.info-the-apocrypha-...ethiopic-bible-... - 740 pages.
    Use TOC printed page numbers + offset (PDF page = printed + 2)."""
    fname = 'ilide.info-the-apocrypha-including-books-from-the-ethiopic-bible-pr_08c2e4c2f2223e5d640766290ee98f9b.pdf'
    OFFSET = 2  # PDF page = printed + 2
    # (id, hebrew, english, printed_start, chapter_count)
    APOC_BOOKS = [
        ("1esdras",     "1 EZRA",                "1 Esdras",              12,  9),
        ("2esdras",     "2 EZRA",                "2 Esdras",              34,  16),
        ("1maccabees",  "1 MAQQABIM",            "1 Maccabees",           80,  16),
        ("2maccabees",  "2 MAQQABIM",            "2 Maccabees",           129, 15),
        ("3maccabees",  "3 MAQQABIM",            "3 Maccabees",           164, 7),
        ("4maccabees",  "4 MAQQABIM",            "4 Maccabees",           180, 18),
        ("epistle-jeremiah","IGGERETH YIRMEYAHU","Letter of Jeremiah",    205, 1),
        ("azariah",     "TEPHILLAH AZARYAH",     "Prayer of Azariah",     209, 1),
        ("baruch",      "BARUḴ",                 "Baruch",                212, 6),
        ("manasseh",    "TEPHILLAH MENASHSHEH",  "Prayer of Manasseh",    220, 1),
        ("bel-dragon",  "BEL UNETSHAYIN",        "Bel and the Dragon",    221, 1),
        ("sirach",      "BEN SIRA",              "Wisdom of Sirach",      224, 51),
        ("wisdom",      "ḤOḴMATH SHELOMOH",      "Wisdom of Solomon",     295, 19),
        ("esther-add",  "TOSEPHOTH ESTĔR",       "Additions to Esther",   320, 6),
        ("tobit",       "TOḆIYAH",               "Tobit",                 327, 14),
        ("judith",      "YEHUDITH",              "Judith",                343, 16),
        ("susanna",     "SHOSHANNAH",            "Susanna",               367, 1),
        ("psalm151",    "TEHILLIM 151",          "Psalm 151",             371, 1),
        ("eth-enoch",   "ḤANOḴ HABASHIY",        "Enoch (Ethiopic)",      372, 108),
        ("jubilees",    "YOḆELIM",               "Jubilees",              478, 50),
        ("1clements",   "1 CLEMENTS",            "1 Clements",            582, 65),
        ("hermas",      "HOSHEPHARD",            "Shepherd of Hermas",    630, 95),
    ]
    r = PdfReader(os.path.join(PDF_DIR, fname))
    nP = len(r.pages)
    books = []
    for i, (bid, heb, eng, start_printed, ch_count) in enumerate(APOC_BOOKS):
        # PDF page range
        start = min(start_printed + OFFSET, nP)
        end_printed = APOC_BOOKS[i+1][3] - 1 if i+1 < len(APOC_BOOKS) else 720
        end = min(end_printed + OFFSET, nP)
        # Detect chapter starts within range
        chapters = {}
        if ch_count > 1:
            # Per-book heading pattern: 1Clements uses "1Clem N:M", Hermas uses
            # bare "N:M" (with verse 1 = "N:1"), the rest use "Chapter N".
            if bid == '1clements':
                ch_pat = re.compile(r'1Clem\s+(\d+)\s*:\s*1\b')
            elif bid == 'hermas':
                ch_pat = re.compile(r'(?:^|\n|\s)(\d+)\s*:\s*1\s+[A-Z]')
            else:
                ch_pat = re.compile(r'(?:Chapter|CHAPTER)\s+(\d+)')
            for p in range(start, end + 1):
                txt = r.pages[p - 1].extract_text() or ''
                for m in ch_pat.finditer(txt):
                    ch = int(m.group(1))
                    if 1 <= ch <= ch_count and str(ch) not in chapters:
                        chapters[str(ch)] = {"pdf": fname, "page": p, "printed": p - OFFSET}
            # Always anchor chapter 1 at start
            chapters.setdefault("1", {"pdf": fname, "page": start, "printed": start_printed})
            # Interpolate missing
            anchors = sorted((int(k), v["page"]) for k, v in chapters.items())
            for ch in range(1, ch_count + 1):
                if str(ch) in chapters: continue
                prev = max((c for c, _ in anchors if c < ch), default=None)
                nxt  = min((c for c, _ in anchors if c > ch), default=None)
                if prev is not None and nxt is not None:
                    p1 = next(p for c, p in anchors if c == prev)
                    p2 = next(p for c, p in anchors if c == nxt)
                    interp = p1 + round((p2 - p1) * (ch - prev) / (nxt - prev))
                elif prev is not None:
                    interp = next(pp for c, pp in anchors if c == prev)
                else:
                    interp = next(pp for c, pp in anchors if c == nxt) if nxt else start
                chapters[str(ch)] = {"pdf": fname, "page": interp, "printed": interp - OFFSET}
        else:
            chapters["1"] = {"pdf": fname, "page": start, "printed": start_printed}

        books.append({
            "id": f"apoc-{bid}",
            "hebrew": heb,
            "english": eng,
            "section": "Apocrypha",
            "chapter_count": ch_count,
            "chapters": chapters,
        })
    print(f'apocrypha: {len(books)} books mapped')
    return books

if __name__ == '__main__':
    all_books = []
    all_books.extend(build_besorah_index())
    all_books.extend(build_enoch())
    all_books.extend(build_jasher())
    all_books.extend(build_adam_eve())
    all_books.extend(build_testaments())
    all_books.extend(build_apocrypha())

    out = {"books": all_books}
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f'\nWrote {OUT}: {len(all_books)} books')
