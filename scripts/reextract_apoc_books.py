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

Verses are bracketed "[N]" (ranges "[1-14]" keep the start number). Chapters
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
    "apoc-baruch":     (214, 221, r"Bar", 5),
    "apoc-sirach":     (226, 296, r"(?:Sir|5ir)", 51),
    "apoc-wisdom":     (297, 321, r"Wis", 19),
    "apoc-tobit":      (329, 344, r"Tob", 14),
    "apoc-judith":     (345, 368, r"Jdt", 16),
}

_PDF = None


def reader():
    global _PDF
    if _PDF is None:
        _PDF = PdfReader(PDF)
    return _PDF


def raw_span(start, end):
    r = reader()
    parts = []
    for p in range(start, end + 1):
        t = r.pages[p - 1].extract_text() or ""
        t = t.replace("Joseph B. Lumpkin", " ").replace("Joseph 8. Lumpkin", " ")
        t = re.sub(r"The Apocrypha:\s*Including Books from the\s*Ethiopic Bible",
                   " ", t)
        parts.append(t)
    return "\n".join(parts)


def clean_text(s):
    s = re.sub(r"­", "", s)                       # soft hyphen
    s = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", " ", s)
    s = re.sub(r"(?<!\d)\b0\b(?!\d)", "O", s)     # vocative 0 -> O
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"(\w)- (\w)", r"\1\2", s)
    return s


def _verses(body):
    """Bracketed [N] verses (ranges keep the start number)."""
    marks = list(re.finditer(r"[\[\{]\s*(\d+)\s*(?:-\s*\d+)?\s*[\]\}]", body))
    out, expected = [], None
    for i, m in enumerate(marks):
        n = int(m.group(1))
        end = marks[i + 1].start() if i + 1 < len(marks) else len(body)
        txt = clean_text(body[m.end():end])
        # keep monotonic-ish verse numbers; tolerate small jumps
        if expected is not None and (n < expected - 0 or n > expected + 5):
            if n < expected:
                continue
        out.append({"n": n, "t": txt})
        expected = n + 1
    # drop empties but keep numbering
    return [v for v in out if v["t"]]


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
    vmarks = list(re.finditer(r"[\[\{]\s*(\d+)\s*(?:-\s*\d+)?\s*[\]\}]", full))
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
    index = json.load(open(INDEX_PATH, encoding="utf-8"))
    by_id = {b["id"]: b for b in index["books"]}
    pdf_name = os.path.basename(PDF)
    for bid, (sp, ep, label_re, canon) in BOOKS.items():
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
        tv = sum(len(c["verses"]) for c in out_ch.values())
        flag = "" if len(out_ch) == canon else f"  (canonical {canon})"
        print(f"{bid:22} {len(out_ch):3} chapters, {tv:4} verses{flag}")
        b = by_id[bid]
        b["chapter_count"] = len(out_ch)
        b["chapters"] = {str(i): {"pdf": pdf_name, "page": sp}
                         for i in range(1, len(out_ch) + 1)}
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    print("index.json updated")


if __name__ == "__main__":
    main()
