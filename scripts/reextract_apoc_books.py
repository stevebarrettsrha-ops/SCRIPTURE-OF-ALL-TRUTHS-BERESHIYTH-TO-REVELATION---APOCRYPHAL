"""Re-extract the apocrypha books whose chapters were destroyed by the
generic parser.

Root cause: index.json mapped every chapter of these books to a single
start page, so parse_apocrypha_chapter only ever read a 1-2 page window and
clipped on a "Chapter N" heading that doesn't exist (the source marks
chapters with inline labels like "2Mac.3"/"Tob.5", which strip_apoc_page
deleted). The result was that EVERY chapter of each book held the same
duplicated blob.

Here we read each book's true page span (from the apocrypha TOC; PDF page =
printed page + 2) and split on the real chapter markers:

  * label books  - "<Prefix>.<N>" (e.g. "1Mac.3", "Sir.0", "4Ezra.1"),
                   tolerating the OCR's "l"->1 / "O"->0 / brace slips;
  * 1 Esdras     - no inline label; each chapter restarts its verse run at
                   "[1]", so we split on the [1] markers.

Verses are bracketed "[N]" (ranges "[1-14]" keep the start number); the
scan also reads the OCR's "[19J" for "[19]", without which the Prayer of
Azariah lost every verse of the Song of the Three Young Men — the whole of
the book after verse 28 runs on in one paragraph whose markers are mostly
"[45 J"-shaped. Chapters
are renumbered 1..N in source order so the reader (which numbers chapters
from 1) shows every chapter. Writes ENGLISH JSON; run transliterate after.
"""
import json
import os
import re
from pypdf import PdfReader

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = os.path.join(
    ROOT, "SCRIPTURE",
    "ilide.info-the-apocrypha-including-books-from-the-ethiopic-bible-pr_"
    "08c2e4c2f2223e5d640766290ee98f9b.pdf")
OUT_DIR = os.path.join(ROOT, "assets", "text")
INDEX_PATH = os.path.join(ROOT, "assets", "index.json")

# id -> (start_page, end_page, label_regex or None for [1]-reset, canonical_cc)
# The label is the inline chapter marker; some books use OCR-variant prefixes
# (1 Maccabees "1Mac"/"IMac", Sirach "Sir"/"5ir"). 2 Esdras has no inline
# label so it falls back to the [1]-reset splitter like 1 Esdras.
BOOKS = {
    "apoc-1esdras":    (14, 35, None, 9),
    "apoc-2esdras":    (36, 81, None, 16),
    "apoc-1maccabees": (82, 130, r"(?:1\s*Mac|IMac)", 16),
    "apoc-2maccabees": (131, 165, r"2\s*Mac", 15),
    "apoc-3maccabees": (166, 181, r"3\s*Mac", 7),
    "apoc-4maccabees": (182, 206, r"4\s*Mac", 18),
    # No inline label and no "[1]" to reset on: one chapter, pages 211-213.
    "apoc-azariah":    (211, 213, None, 1),
    "apoc-baruch":     (214, 221, r"Bar", 5),
    "apoc-sirach":     (226, 296, r"(?:Sir|5ir)", 51),
    "apoc-wisdom":     (297, 321, r"Wis", 19),
    "apoc-tobit":      (329, 344, r"Tob", 14),
    "apoc-judith":     (345, 368, r"Jdt", 16),
}

# A bracketed verse number. The source is scanned, not typeset, so a closing
# "]" often comes through as "J" ("[19J", "[45 J") — read both.
MARKER = re.compile(r"[\[\{]\s*(\d+)\s*(?:-\s*\d+)?\s*[\]\}J]")

_PDF = None


def reader():
    global _PDF
    if _PDF is None:
        _PDF = PdfReader(PDF)
    return _PDF


# The running banner on every page carries the printed page number beside
# it, and pypdf often splits that number ("144" comes through as "14 4").
# Left in, those digits land inside the verse the page break interrupted —
# "his companions secretly 14 4 entered the villages". Only that page's own
# printed number (pdf page − 2 in this volume) is removed, and only where
# it sits against a banner: a verse marker often opens the line right after
# the top banner and must survive.
_BANNERS = [r"(?:Joseph|Yoseph)\s+[B8]\.\s+Lumpkin",
            r"The Apocrypha:\s*Including Books from the\s*Eth[i;]op[i;]c Bible"]


def _spaced_digits(n):
    return r"\s?".join(re.escape(d) for d in str(n))


def strip_banner(t, printed=None):
    for b in _BANNERS:
        if printed is not None:
            for pn in (printed, printed - 1, printed + 1):
                d = _spaced_digits(pn)
                t = re.sub(rf"(?:(?<=\s)|^){d}\s*(?={b})", " ", t)
                t = re.sub(rf"({b})\s*{d}(?=\s|$)", r"\1", t)
        t = re.sub(b, " ", t)
    if printed is not None:
        for pn in (printed - 1, printed, printed + 1):
            d = _spaced_digits(pn)
            t = re.sub(rf"(?:(?<=\s)|^){d}\s*$", " ", t)
            t = re.sub(rf"^\s*{d}(?=\s)", " ", t)
    return t


def raw_span(start, end):
    r = reader()
    parts = []
    for p in range(start, end + 1):
        t = strip_banner(r.pages[p - 1].extract_text() or "", printed=p - 2)
        parts.append(t)
    return "\n".join(parts)


def clean_text(s):
    s = re.sub(r"­", "", s)                       # soft hyphen
    s = re.sub(r"<\s*br\s*/?\s*>", " ", s)       # stray HTML remnant in the scan
    s = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", " ", s)
    s = re.sub(r"(?<!\d)\b0\b(?!\d)", "O", s)     # vocative 0 -> O
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"(\w)- (\w)", r"\1\2", s)
    return s


# The scan garbles a bracketed number three ways, and each cost verses until
# it was read back: digits set as letters ("[S2]" for [52], "[lS]" for [18]),
# a closing bracket set as the digit 1 ("[551" for [55], "[881" for [88]),
# and an opening bracket set as the digit 1 ("136]" for [36], "116]" for
# [16]). A repaired reading is only trusted when it lands on exactly the
# verse the chapter is waiting for — the sequence is the proof.
_M_NORMAL = r"[\[\{]\s*([0-9SlIOBZgqb]{1,3})\s*(?:-\s*(\d+))?\s*[\]\}J]"
_M_CLOSE1 = r"[\[\{]\s*(\d{1,3})1(?=\s)"      # "]" printed as "1"
_M_OPEN1 = r"(?<=\s)1(\d{1,3})\s*[\]\}J]"     # "[" printed as "1"
_M_ANY = re.compile(f"(?:{_M_NORMAL})|(?:{_M_CLOSE1})|(?:{_M_OPEN1})")

_DIGIT_FOR = {"S": "58", "l": "1", "I": "1", "O": "0", "B": "8",
              "Z": "2", "g": "9", "q": "9", "b": "6"}


def _candidates(token):
    """All numbers a letter-garbled token could stand for, and whether the
    reading needed repair at all."""
    outs = [""]
    repaired = False
    for c in token:
        if c.isdigit():
            outs = [o + c for o in outs]
        else:
            repaired = True
            outs = [o + d for o in outs for d in _DIGIT_FOR.get(c, "")]
    nums = {int(o) for o in outs if o}
    return nums, repaired


def _verses(body):
    """Bracketed [N] verses (ranges keep the start number)."""
    accepted = []                       # (n, match) that continue the chapter
    expected = None
    for m in _M_ANY.finditer(body):
        if m.group(1) is not None:      # normal bracket pair
            nums, repaired = _candidates(m.group(1))
        elif m.group(3) is not None:    # closing bracket read as 1
            nums, repaired = {int(m.group(3))}, True
        else:                           # opening bracket read as 1
            nums, repaired = {int(m.group(4))}, True
        want = 1 if expected is None else expected
        if repaired:
            # a guessed reading must land exactly on the next verse
            if want not in nums:
                continue
            n = want
        else:
            n = next(iter(nums))
            if expected is not None and (n < expected or n > expected + 5):
                continue
        accepted.append((n, m))
        # A range marker "[15-26]" groups verses; the next verse the chapter
        # is waiting for follows the END of the range, not its start.
        if m.group(2) is not None and int(m.group(2)) >= n:
            expected = int(m.group(2)) + 1
        else:
            expected = n + 1
    out = []
    for i, (n, m) in enumerate(accepted):
        end = accepted[i + 1][1].start() if i + 1 < len(accepted) else len(body)
        txt = clean_text(body[m.end():end])
        # a "verse" that is nothing but stray page digits is not a verse
        if re.fullmatch(r"[\d\s.,-]*", txt):
            txt = ""
        if txt:
            out.append({"n": n, "t": txt})
    return out


def _strip_pagenums(full):
    return "\n".join(l for l in full.split("\n")
                     if not re.match(r"^\s*\d{1,4}\s*$", l))


def extract_book(span, label_re):
    """A chapter boundary is an inline chapter LABEL ("2Mac.3") OR a verse
    run RESET (the bracketed verse numbering returning to [1]). Either signal
    alone is defeated by the OCR (garbled labels / garbled "[1]"), so we take
    the union of both, de-duplicate near-coincident boundaries, then split."""
    full = _strip_pagenums(raw_span(*span))
    bounds = set()
    if label_re:
        for m in re.finditer(label_re + r"\s*[.,]\s*[0-9lIOo]+", full):
            bounds.add(m.start())
    vmarks = list(re.finditer(MARKER, full))
    prev = 0
    for m in vmarks:
        n = int(m.group(1))
        if n == 1 and prev >= 2:              # genuine verse reset
            bounds.add(m.start())
        prev = n
    bounds.add(0)
    ordered = sorted(bounds)
    # Merge a label and its following "[1]" (within ~60 chars) into one boundary.
    merged = []
    for b in ordered:
        if merged and b - merged[-1] < 60:
            continue
        merged.append(b)
    chapters = []
    for i, b in enumerate(merged):
        end = merged[i + 1] if i + 1 < len(merged) else len(full)
        verses = _verses(full[b:end])
        if verses:
            chapters.append(verses)
    return [(i + 1, ch) for i, ch in enumerate(chapters)]


def main():
    """Re-extract every listed book, or only the ids given on the command
    line. Naming ids matters: this writes ENGLISH text, so a book that is
    already transliterated must not be regenerated unless it is going back
    through transliterate.py afterwards."""
    import sys
    wanted = {a for a in sys.argv[1:] if not a.startswith("-")}
    unknown = wanted - set(BOOKS)
    if unknown:
        raise SystemExit("not re-extractable here: " + ", ".join(sorted(unknown)))
    index = json.load(open(INDEX_PATH, encoding="utf-8"))
    by_id = {b["id"]: b for b in index["books"]}
    pdf_name = os.path.basename(PDF)
    for bid, (sp, ep, label_re, canon) in BOOKS.items():
        if wanted and bid not in wanted:
            continue
        chs = extract_book((sp, ep), label_re)
        # renumber 1..N in source order (reader numbers chapters from 1)
        out_ch = {}
        for i, (_orig_n, verses) in enumerate(chs, start=1):
            out_ch[str(i)] = {"verses": verses, "page": sp, "pdf": pdf_name}
        out = {
            "id": bid,
            "hebrew": by_id[bid].get("hebrew", bid),
            "english": by_id[bid].get("english", bid),
            "section": "Apocrypha",
            "chapter_count": len(out_ch),
            "chapters": out_ch,
        }
        with open(os.path.join(OUT_DIR, f"{bid}.json"), "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
            f.write("\n")
        tv = sum(len(c["verses"]) for c in out_ch.values())
        flag = "" if len(out_ch) == canon else f"  (canonical {canon})"
        print(f"{bid:22} {len(out_ch):3} chapters, {tv:4} verses{flag}")
        b = by_id[bid]
        b["chapter_count"] = len(out_ch)
        # Keep whatever the index already recorded for a chapter (the
        # "printed" page a reader would look up); only the pdf/page mapping
        # is ours to restate.
        old_ch = b.get("chapters", {})
        b["chapters"] = {}
        for i in range(1, len(out_ch) + 1):
            entry = dict(old_ch.get(str(i), {}))
            entry["pdf"] = pdf_name
            entry["page"] = sp
            b["chapters"][str(i)] = entry
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("index.json updated")


if __name__ == "__main__":
    main()
