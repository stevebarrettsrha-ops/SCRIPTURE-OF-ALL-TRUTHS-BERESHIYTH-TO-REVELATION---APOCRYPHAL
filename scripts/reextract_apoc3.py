"""Focused re-extraction of three structurally-corrupted apocrypha books.

The generic apocrypha path in extract_text.py mis-handled these three books
because their source markers don't match its assumptions and the index.json
page maps were wrong:

  * apoc-1clements  — the source marks verses "1Clem C:V", but the OCR renders
                      ~7% of them as "lClem" (lowercase L). The old parser keyed
                      on "1Clem" only, so chapter-boundary detection failed and
                      chapters swallowed following text (the visible "lClem 10:1"
                      bleed + duplicated paragraphs). Fix: normalise [lI]Clem ->
                      1Clem, then split on every C:V marker. Pages 584-631, ch 1-65.

  * apoc-hermas     — the index gave Hermas only 3 pages (632-634); it actually
                      runs 632-726. Verses are marked "<sect-ch>[<continuous-ch>]:<v>"
                      (e.g. "2[6]:3"); Vision 1 omits the bracket because its
                      section chapters 1-4 already equal the continuous chapters.
                      We key on the continuous chapter number, giving chapters 1-114.

  * apoc-esther-add — chapters are headed "AddEsth.N" (N = 10-16, the traditional
                      Addition numbers), each with bracketed [v] verses. The index
                      pointed every chapter at the single page 322, so the standard
                      "Chapter N" parser produced duplicated blobs. Pages 322-328.

This writes ENGLISH JSON only. Run scripts/transliterate.py afterwards (limited
to these files) to apply the Hebrew-roots rules, exactly like the main pipeline.
"""
import json
import os
import re
from pypdf import PdfReader

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = os.path.join(
    ROOT, "SCRIPTURE",
    "ilide.info-the-apocrypha-including-books-from-the-ethiopic-bible-pr_"
    "08c2e4c2f2223e5d640766290ee98f9b.pdf",
)
OUT_DIR = os.path.join(ROOT, "assets", "text")

_READER = None


def reader():
    global _READER
    if _READER is None:
        _READER = PdfReader(PDF)
    return _READER


def raw_pages(start, end):
    """Concatenated raw text for 1-based page range [start, end], with the
    running header/footer noise removed. Also returns a page index — a list of
    (char_offset, pdf_page) pairs — so a marker's source page can be recovered
    for the per-chapter "PDF" cross-reference link."""
    r = reader()
    parts = []
    page_index = []
    offset = 0
    for p in range(start, end + 1):
        t = r.pages[p - 1].extract_text() or ""
        # The printed folio (pdf page − 2) often sits hard against a banner
        # and pypdf may split its digits ("601" comes through as "60 1");
        # remove that exact number where it touches a banner, and only that
        # number — a verse marker can open the line right after the banner.
        banners = [r"(?:Joseph|Yoseph)\s+[B8]\.\s+Lumpkin",
                   r"The Apocrypha:\s*Including Books from the\s*Eth[i;]op[i;]c Bible"]
        for b in banners:
            for pn in (p - 3, p - 2, p - 1):
                d = r"\s?".join(re.escape(c) for c in str(pn))
                t = re.sub(rf"(?:(?<=\s)|^){d}\s*(?={b})", " ", t)
                t = re.sub(rf"({b})\s*{d}(?=\s|$)", r"\1", t)
            t = re.sub(b, " ", t)
        # The folio can also end the page's text with no banner beside it
        # (the banner opens the NEXT page); eat it at the extreme edges too.
        for pn in (p - 3, p - 2, p - 1):
            d = r"\s?".join(re.escape(c) for c in str(pn))
            t = re.sub(rf"(?:(?<=\s)|^){d}\s*$", " ", t)
            t = re.sub(rf"^\s*{d}(?=\s)", " ", t)
        # Drop standalone page-number lines (the printed folio at page bottom).
        t = "\n".join(l for l in t.split("\n") if not re.match(r"^\s*\d{1,4}\s*$", l))
        page_index.append((offset, p))
        parts.append(t)
        offset += len(t) + 1                              # +1 for the join "\n"
    return "\n".join(parts), page_index


def page_at(page_index, pos):
    """Return the pdf page containing character offset `pos`."""
    page = page_index[0][1]
    for off, pg in page_index:
        if off > pos:
            break
        page = pg
    return page


# Specific OCR character confusions seen in this PDF's apocrypha section.
_OCR_WORD_FIXES = [
    ("HimseU", "Himself"), ("dwelL", "dwell"), ("tranquiL", "tranquil"),
    ("weIl", "well"), ("seaL", "seal"), ("seIf", "self"),
    ("Israet", "Israel"), ("faithfut", "faithful"),
]


def normalize_ocr(s):
    """Repair the recurrent OCR character confusions in this scan."""
    s = s.replace("­", "")                       # soft hyphen
    # The digit "0" is frequently substituted for the vocative "O"
    # ("0 Lord", "0 house of Israel"). Only swap a standalone, non-numeric 0.
    s = re.sub(r"(?<!\d)\b0\b(?!\d)", "O", s)
    for a, b in _OCR_WORD_FIXES:
        s = s.replace(a, b)
    return s


def clean_text(s):
    """Collapse whitespace and tidy a verse body."""
    s = re.sub(r"\s+", " ", s).strip()
    # Repair words split by the OCR across a hyphen-newline ("com- pleted").
    s = re.sub(r"(\w)-\s+(\w)", r"\1\2", s)
    s = normalize_ocr(s)
    return s


# --------------------------------------------------------------------------
# 1 Clement
# --------------------------------------------------------------------------
def extract_1clements():
    full, pidx = raw_pages(584, 631)
    # Normalise the verse-label OCR variants: the leading "1" is rendered as a
    # lowercase "l" or capital "I", and the label is sometimes split by a space
    # ("1 Clem 4:3", "1C lem 52:2"). Fold them all to a canonical "1Clem".
    full = re.sub(r"\b[1lI]\s*C\s*lem", "1Clem", full)
    # Verse number is occasionally dropped by the OCR ("1Clem 4:And jealousy..."),
    # so capture it optionally and fill in the next sequential number.
    marks = list(re.finditer(r"1Clem\s+(\d+)\s*:\s*(\d+)?", full))
    chapters, pages, last_v = {}, {}, {}
    for i, m in enumerate(marks):
        c = int(m.group(1))
        if not (1 <= c <= 65):
            continue
        v = int(m.group(2)) if m.group(2) else last_v.get(c, 0) + 1
        if not (1 <= v <= 100):
            continue
        last_v[c] = v
        end = marks[i + 1].start() if i + 1 < len(marks) else len(full)
        text = clean_text(full[m.end():end])
        if text:
            chapters.setdefault(c, []).append({"n": v, "t": text})
            pages.setdefault(c, page_at(pidx, m.start()))
    return chapters, pages


# --------------------------------------------------------------------------
# Shepherd of Hermas
# --------------------------------------------------------------------------
_HERMAS_SECTION = re.compile(
    r"\b(?:Vision|Mandate|Command|Parable|Similitude)\s+\d+\b")
# A verse marker is EITHER a bracketed continuous chapter "<sect>[<cont>]:<v>"
# (authoritative) OR a bare "<n>:<v>" (the section-relative prefix; used for
# Vision 1 and as a fallback where the OCR destroyed the bracket). The closing
# "]" is frequently OCR'd as "J"; an optional letter suffix handles "[104a]".
_HERMAS_MARK = re.compile(
    r"(?:"
    # bracketed: <sect>[<continuous>]:<v>. The OCR renders "[" as "[" or "{",
    # "]" as "]"/"J"/"}", and a sub-chapter letter suffix ("104a") may sit on
    # either side of the closing bracket.
    r"(\d+)\s*[\[\{]\s*(\d+)[a-z]?\s*[\]J\})][a-z]?"  # 1=sect 2=continuous
    r"|(?<![\d\]J\})])(\d+)"                           # 3=bare section number
    r")\s*:\s*(\d+)"                                   # 4=verse
)

# Three more shapes the scan gives a bracketed marker, normalised before
# matching: "8116]:9" ("[" set as the digit 1), "27[1 04]:6" (a space inside
# the bracketed number), and "10[76):2" (")" for "]", handled above).
def _normalize_hermas_marks(full):
    full = re.sub(r"(?<=\d)1(\d{2})\](?=\s*:)", r"[\1]", full)
    full = re.sub(r"\[\s*(\d)\s+(\d+)\s*([\]J\})])", r"[\1\2]", full)
    return full


def _emit(chapters, ch, v, text):
    if text:
        chapters.setdefault(ch, []).append({"n": v, "t": text})


def extract_hermas():
    full, pidx = raw_pages(632, 726)
    # The section banners ("Vision 1" ...) sit between markers; blanking them
    # keeps offsets stable so the page index stays valid.
    full = _HERMAS_SECTION.sub(lambda m: " " * len(m.group(0)), full)
    full = _normalize_hermas_marks(full)

    marks = list(_HERMAS_MARK.finditer(full))
    chapters, pages = {}, {}
    cur = 0          # current continuous chapter
    prev_v = 0       # previous verse number within cur
    recovered = 0
    for i, m in enumerate(marks):
        bracket = int(m.group(2)) if m.group(2) else None
        v = int(m.group(4))
        if v < 1 or v > 200:
            continue
        if bracket and cur < bracket <= 114:
            # A bracket strictly ahead of us is an authoritative forward jump.
            cur = bracket
        elif cur == 0:
            cur = 1                           # Vision 1 opening (unbracketed)
        elif v <= prev_v:
            # Verse number reset within the same/earlier chapter number means
            # the bracket digit was OCR-misread as a prior chapter (the source
            # has chapters 14/64/91/93/98/105-108 whose brackets are garbled):
            # a reset always marks the next continuous chapter.
            cur += 1
            recovered += 1
        prev_v = v
        end = marks[i + 1].start() if i + 1 < len(marks) else len(full)
        _emit(chapters, cur, v, clean_text(full[m.end():end]))
        pages.setdefault(cur, page_at(pidx, m.start()))
    if recovered:
        print(f"  hermas: recovered {recovered} chapter boundaries from "
              f"OCR-garbled markers")
    return chapters, pages


# --------------------------------------------------------------------------
# Additions to Esther
# --------------------------------------------------------------------------
def extract_esther_add():
    full, pidx = raw_pages(322, 328)
    heads = list(re.finditer(r"AddEsth\.?\s*(\d+)", full))
    chapters, pages = {}, {}
    # The source labels the additions AddEsth.11-16 then AddEsth.10 (the dream
    # interpretation, placed last). The reader UI numbers chapters consecutively
    # from 1, so re-number them 1..7 in the PDF's own reading order.
    seq = 0
    for i, h in enumerate(heads):
        c = int(h.group(1))
        if not (10 <= c <= 16):
            continue
        seq += 1
        page = page_at(pidx, h.start())
        end = heads[i + 1].start() if i + 1 < len(heads) else len(full)
        body = full[h.end():end]
        # Verse markers are "[n]"; the OCR sometimes renders a brace for either
        # bracket ("[2}", "{15]"), so accept [ or { open and ] or } close.
        vmarks = list(re.finditer(r"[\[\{](\d+)\s*[\]J\})]\s*", body))
        verses = []
        last_v = 0
        for j, vm in enumerate(vmarks):
            v = int(vm.group(1))
            # The Greek colophon ("In the fourth year of Ptolemy and Cleopatra
            # ... the Letter of Purim") trails AddEsth.10 under a fresh "[1]"
            # with no header of its own; fold it on as the next verse so the
            # numbering stays monotonic and the text is preserved.
            if v <= last_v:
                v = last_v + 1
            vend = vmarks[j + 1].start() if j + 1 < len(vmarks) else len(body)
            text = clean_text(body[vm.end():vend])
            # Drop any stray "AddEsth.NN" cross-reference tag that bled into the
            # body (the OCR writes the next addition's label, e.g. "AddEsth.ll").
            text = re.sub(r"\s*AddEsth\.?\s*\w*", "", text).strip()
            if text:
                verses.append({"n": v, "t": text})
                last_v = v
        if verses:
            chapters[seq] = verses
            pages[seq] = page
    return chapters, pages


# --------------------------------------------------------------------------
BOOK_META = {
    "apoc-1clements":  dict(hebrew="1 CLEMENTS", english="1 Clements",
                            page=584, fn=extract_1clements),
    "apoc-hermas":     dict(hebrew="SHEPHERD OF HERMAS",
                            english="Shepherd of Hermas",
                            page=632, fn=extract_hermas),
    "apoc-esther-add": dict(hebrew="ADDITIONS TO ESTHER",
                            english="Additions to Esther",
                            page=322, fn=extract_esther_add),
}


INDEX_PATH = os.path.join(ROOT, "assets", "index.json")
PDF_NAME = os.path.basename(PDF)


def main():
    index = json.load(open(INDEX_PATH, encoding="utf-8"))
    by_id = {b["id"]: b for b in index["books"]}

    for bid, meta in BOOK_META.items():
        chapters, pages = meta["fn"]()
        out_ch = {}
        for c in sorted(chapters):
            out_ch[str(c)] = {
                "verses": chapters[c],
                "page": pages.get(c, meta["page"]),
                "pdf": PDF_NAME,
            }
        out = {
            "id": bid,
            "hebrew": meta["hebrew"],
            "english": meta["english"],
            "section": "Apocrypha",
            "chapter_count": len(out_ch),
            "chapters": out_ch,
        }
        path = os.path.join(OUT_DIR, f"{bid}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        total_v = sum(len(c["verses"]) for c in out_ch.values())
        print(f"{bid}: {len(out_ch)} chapters, {total_v} verses -> {path}")

        # Keep index.json in sync: correct chapter_count and per-chapter page map
        # so the reader builds the right chapter list and PDF links.
        if bid in by_id:
            b = by_id[bid]
            b["chapter_count"] = len(out_ch)
            b["chapters"] = {
                str(c): {"pdf": PDF_NAME, "page": pages.get(c, meta["page"])}
                for c in sorted(chapters)
            }
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    print("index.json updated for the three books")


if __name__ == "__main__":
    main()
