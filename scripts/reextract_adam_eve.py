"""Focused re-extraction of the First and Second Books of Adam and Eve.

The generic Adam & Eve parser in extract_text.py left two defects:

  * Chapter-heading / subtitle bleed: every page of both PDFs carries a
    running footer block — "First Book of Adam and Eve\\nChapter <Roman>
    <subtitle> <page>" (44.pdf) / "THE SECOND BOOK OF Adam and Eve\\nCHAP.
    <Roman> <page>" (78.pdf) — that pypdf emits at the END of each page's
    text. Concatenating pages without stripping it injected the running
    header (and a duplicate chapter heading + subtitle) into the middle of
    verses, 60+ times per book.

  * Second-book verse mis-alignment: 78.pdf leaves verse 1 of each chapter
    un-numbered and glues later verse numbers to their text ("2Then"). The
    old verse regex needed a space after the number, so it missed those and
    let chapters swallow the next chapter's opening verses (e.g. 3:1-3 were
    lost into 2:7).

  * Dropped text: a line that opens with a number the sequence cannot
    accept was treated as a mis-numbered verse and thrown away with its
    words — losing, among others, the second half of Adam & Eve 1 3:6
    ("...these were 5,000 and 500 years; and how One would then come and
    save him and his descendants"). A number that is not the next verse is
    now read as what it is: part of the sentence.

  * Mid-line verse numbers: where the PDF wrapped a number into the middle
    of a line ("...prayed to God to explain it to him. 6 Then God in his
    mercy...") the verse was never opened, so two verses ran together and
    the numbering skipped.

This re-extractor strips the footer block per page (everything from the
running-header marker to end-of-page), then splits on the real in-body
chapter headings and parses verses with the correct per-book rules.

Writes ENGLISH JSON only; run the transliteration pipeline afterwards.
"""
import json
import os
import re
from pypdf import PdfReader

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR = os.path.join(ROOT, "SCRIPTURE")
OUT_DIR = os.path.join(ROOT, "assets", "text")
INDEX_PATH = os.path.join(ROOT, "assets", "index.json")

ROMAN = r"(?=[IVXLC])(X{0,3})(IX|IV|V?I{0,3})"
_ROMAN_FULL = re.compile(r"^[IVXLC]+$")


def from_roman(s):
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
    total = prev = 0
    for ch in reversed(s):
        v = vals.get(ch, 0)
        total += -v if v < prev else v
        prev = v
    return total


def clean_text(s):
    s = re.sub(r"−−|--", " - ", s)        # "−−" / "--" -> spaced dash
    # 44.pdf sets its dashes as a control character ("four elements\x14fire,
    # earth, air, and water\x14was widely accepted"); left in, it welds the
    # words on either side together.
    s = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", " ", s)
    # The scan reads a vocative "O" as a zero — "0 Adam, from the time ye
    # have dwelt in this cave".
    s = re.sub(r"(?<![\d,.])\b0\b(?![\d,.])", "O", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"(\w)- (\w)", r"\1\2", s)            # de-hyphenate line breaks
    return s


def _page_texts(fname, start_page, footer_marker):
    """Yield (pdf_page, cleaned_page_text) for body pages, with the running
    footer block (footer_marker .. end-of-page) removed."""
    r = PdfReader(os.path.join(PDF_DIR, fname))
    for p in range(start_page, len(r.pages) + 1):
        t = r.pages[p - 1].extract_text() or ""
        i = t.find(footer_marker)
        if i >= 0:
            t = t[:i]
        # also drop any leading copy of the running header
        t = t.replace(footer_marker, " ")
        yield p, t


def _concat_with_pages(pages):
    """pages = list of (pdf_page, text). Return (full, page_index)."""
    parts, page_index, off = [], [], 0
    for pg, t in pages:
        page_index.append((off, pg))
        parts.append(t)
        off += len(t) + 1
    return "\n".join(parts), page_index


def page_at(page_index, pos):
    pg = page_index[0][1]
    for off, p in page_index:
        if off > pos:
            break
        pg = p
    return pg


# --------------------------------------------------------------------------
# First Book of Adam and Eve  (44.pdf)
#   heading: "Chapter <Roman>\x14<subtitle>\n1 <v1>\n2 <v2> ...", verses
#   numbered from 1 at line starts.
# --------------------------------------------------------------------------
def extract_book1():
    pages = list(_page_texts("44.pdf", 6, "First Book of Adam and Eve"))
    full, pidx = _concat_with_pages(pages)
    # Begin at the first real in-body chapter heading.
    m0 = re.search(r"Chapter\s+I\s*\x14", full)
    if m0:
        full = full[m0.start():]
        pidx = [(o - m0.start(), p) for o, p in pidx]
    heads = list(re.finditer(r"Chapter\s+([IVXLC]+)\s*\x14", full))
    chapters, pages_map = {}, {}
    cur = 0
    for i, h in enumerate(heads):
        n = from_roman(h.group(1))
        if not (cur < n <= cur + 3):          # keep strictly increasing
            continue
        end = heads[i + 1].start() if i + 1 < len(heads) else len(full)
        body = full[h.end():end]
        # subtitle = up to the first verse-1 marker; verses follow.
        vm = re.search(r"(?:^|\n)\s*1\s+", body)
        if vm:
            body = body[vm.start():]
        verses = _parse_numbered(body, first_expected=1)
        if verses:
            # The book's closing verse runs straight into the colophon
            # ("…defiled with blood. . . . End of First Book of Adam and
            # Eve"), whose tail the footer strip has already removed. Take
            # the orphaned "End of" with it so the verse ends where it does.
            verses[-1]["t"] = re.sub(r"\s*\.(?:\s*\.)+\s*End of\s*$", ".",
                                     verses[-1]["t"]).rstrip()
        if verses:                            # only advance on a real chapter
            cur = n
            chapters[n] = verses
            pages_map[n] = page_at(pidx, h.start())
    return chapters, pages_map


# --------------------------------------------------------------------------
# Second Book of Adam and Eve  (78.pdf)
#   heading: "CHAP. <Roman>.\n     <subtitle>\n     <v1 UNNUMBERED>\n     2 <v2>"
#   blocks are 2+ space indented; verse 1 carries no number.
# --------------------------------------------------------------------------
def extract_book2():
    pages = list(_page_texts("78.pdf", 6, "THE SECOND BOOK OF Adam and Eve"))
    full, pidx = _concat_with_pages(pages)
    m0 = re.search(r"CHAP[.,]\s+I[.,]", full)
    if m0:
        full = full[m0.start():]
        pidx = [(o - m0.start(), p) for o, p in pidx]
    heads = list(re.finditer(r"CHAP[.,]\s+([IVXLC]+)[.,]?", full))
    chapters, pages_map = {}, {}
    cur = 0
    for i, h in enumerate(heads):
        n = from_roman(h.group(1))
        if not (cur < n <= cur + 3):
            continue
        end = heads[i + 1].start() if i + 1 < len(heads) else len(full)
        body = full[h.end():end]
        # Split into indented blocks: subtitle, verse1 (unnumbered), 2, 3 ...
        blocks = re.split(r"\n {2,}", "\n" + body)
        blocks = [b for b in (b.strip() for b in blocks) if b]
        if len(blocks) < 2:
            continue
        verses = []
        # blocks[0] = subtitle (drop). blocks[1] = verse 1 (unnumbered).
        v1 = _fix_dropcap(blocks[1])
        verses.append({"n": 1, "t": clean_text(v1)})
        expected = 2
        for blk in blocks[2:]:
            mm = re.match(r"(\d{1,3})\s*(.*)$", blk, re.S)
            vn = int(mm.group(1)) if mm else None
            txt = clean_text(mm.group(2)) if mm else ""
            if vn is not None and expected <= vn <= expected + 3:
                if txt:
                    verses.append({"n": vn, "t": txt})
                    expected = vn + 1
                continue
            if vn is not None and vn > expected + 3 and len(txt.split()) >= 5:
                # The source mis-prints the number — 2 Adam & Eve 13:13 is
                # set as "18" — but the block is plainly the next verse.
                # Give it the number the chapter's sequence calls for
                # rather than dropping a verse of the reading.
                verses.append({"n": expected, "t": txt})
                expected += 1
                continue
            # A continuation line, a stray page number, a date: not a verse
            # of its own, so keep the words with the verse they follow.
            tail = clean_text(blk)
            if tail and verses:
                verses[-1]["t"] = (verses[-1]["t"] + " " + tail).strip()
        if verses:
            cur = n
            chapters[n] = verses
            pages_map[n] = page_at(pidx, h.start())
    return chapters, pages_map


def _fix_dropcap(s):
    """Repair the all-caps / letter-spaced drop-cap opening of an unnumbered
    verse 1: 'A S for' -> 'As for', 'AND Eve' -> 'And Eve', 'THEN God' ->
    'Then God'."""
    s = s.lstrip()
    # Join leading run of single capital letters separated by spaces.
    m = re.match(r"((?:[A-Z] ){1,3}[A-Z])(?=[a-z ]|$)", s)
    if m:
        joined = m.group(1).replace(" ", "")
        s = joined + s[m.end():]
    # Title-case a leading ALL-CAPS word.
    m = re.match(r"([A-Z]{2,})(\b)", s)
    if m:
        s = m.group(1).capitalize() + s[m.end(1):]
    return s


# A verse number opens a line, or — where the PDF wrapped the number into
# the middle of a line — follows the end of the previous sentence.
_MARK = re.compile(r"""(?:^|\n)\s*(\d{1,3})\s+(?=[A-Za-z"\u201c\u2018'(])"""
                   r"""|(?<=[.!?"'\u201d\u2019])\s+(\d{1,3})\s+"""
                   r"""(?=[A-Za-z"\u201c\u2018'(])""")


def _parse_numbered(body, first_expected=1):
    """Split a chapter body at its verse numbers.

    Only a number that continues the chapter's sequence opens a verse.
    Anything else — "500 years; and how One would then come" beginning a
    line, a date, a tally — is prose, so the text around it stays with the
    verse it belongs to instead of being dropped on the floor.
    """
    accepted = []
    expected = first_expected
    for mm in _MARK.finditer(body):
        n = int(mm.group(1) or mm.group(2))
        if n < expected or n > expected + 3:
            continue
        accepted.append((n, mm.start(), mm.end()))
        expected = n + 1
    verses = []
    for i, (n, _start, end) in enumerate(accepted):
        stop = accepted[i + 1][1] if i + 1 < len(accepted) else len(body)
        txt = clean_text(body[end:stop])
        if txt:
            verses.append({"n": n, "t": txt})
    return verses


BOOK_META = {
    "adam-eve-1": dict(hebrew="FIRST BOOK OF ADAM & EVE",
                       english="First Book of Adam and Eve",
                       pdf="44.pdf", fn=extract_book1),
    "adam-eve-2": dict(hebrew="SECOND BOOK OF ADAM & EVE",
                       english="Second Book of Adam and Eve",
                       pdf="78.pdf", fn=extract_book2),
}


def main():
    index = json.load(open(INDEX_PATH, encoding="utf-8"))
    by_id = {b["id"]: b for b in index["books"]}
    for bid, meta in BOOK_META.items():
        chapters, pages_map = meta["fn"]()
        # preserve existing hebrew/english/section if present
        old = by_id.get(bid, {})
        out_ch = {}
        for c in sorted(chapters):
            out_ch[str(c)] = {"verses": chapters[c],
                              "page": pages_map.get(c, 6),
                              "pdf": meta["pdf"]}
        out = {
            "id": bid,
            "hebrew": old.get("hebrew", meta["hebrew"]),
            "english": old.get("english", meta["english"]),
            "section": old.get("section", "Apocrypha"),
            "chapter_count": len(out_ch),
            "chapters": out_ch,
        }
        with open(os.path.join(OUT_DIR, f"{bid}.json"), "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        tv = sum(len(c["verses"]) for c in out_ch.values())
        print(f"{bid}: {len(out_ch)} chapters, {tv} verses")
        if bid in by_id:
            b = by_id[bid]
            b["chapter_count"] = len(out_ch)
            b["chapters"] = {str(c): {"pdf": meta["pdf"], "page": pages_map.get(c, 6)}
                             for c in sorted(chapters)}
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    print("index.json updated")


if __name__ == "__main__":
    main()
