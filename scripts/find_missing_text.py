#!/usr/bin/env python3
"""
find_missing_text.py

Finds scripture that is printed in a source PDF but never reached
assets/text/ — the "missing scriptures" a reader notices as a verse that
stops mid-sentence, or a number that skips.

How it works
------------
Every book in assets/index.json records, per chapter, which PDF it came
from and on which page. For each book this script re-reads that page range,
runs the raw PDF English through the same transliteration the reader sees
(scripts/transliterate.py) so the two sides speak the same vocabulary, and
then asks a simple question of every word on the page: does it sit inside
any run of `N` consecutive words that also appears in assets/text/?

The comparison is made against the whole corpus, not just the book being
scanned, because a page at the end of one book carries the opening of the
next, and that opening is not missing — it is simply in the neighbouring
file.

Words that fail that test are gathered into runs. A run longer than
`--min-run` words is real text the extractor dropped, and is reported with
the chapter it belongs beside. Short runs are the ordinary noise of two
different renderings of the same sentence (a repaired hyphenation, a
running header, a footnote) and are ignored.

Usage:
    python3 scripts/find_missing_text.py                 # every book
    python3 scripts/find_missing_text.py adam-eve-1      # one or more books
    python3 scripts/find_missing_text.py --min-run 12    # only longer gaps
    python3 scripts/find_missing_text.py --all           # keep the apparatus too

By default a run that is plainly page apparatus — a chapter heading, a
running header, a page number — is counted but not printed: it is text the
extractor was right to leave out.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import transliterate as T  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TEXT_DIR = ROOT / "assets" / "text"
INDEX_PATH = ROOT / "assets" / "index.json"
PDF_DIR = ROOT / "SCRIPTURE"

TAG = re.compile(r"<[^>]+>")
NGRAM = 5


def fold(word):
    """Reduce a word to what two renderings of it can be expected to share."""
    s = unicodedata.normalize("NFD", word.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", s)


# The Besorah volumes set a verse number hard against the first word —
# "2Re'uḇĕn", "23And" — so a number and a word have to come apart before
# either can be compared with the JSON, where the number lives in "n".
GLUED = re.compile(r"(?<=\d)(?=[A-Za-z])|(?<=[A-Za-z])(?=\d)")


def words_of(text):
    out = []
    for tok in TAG.sub(" ", text).split():
        for part in GLUED.split(tok):
            w = fold(part)
            if w and not w.isdigit():
                out.append(w)
    return out


def shingles(seq, n=NGRAM):
    return {tuple(seq[i:i + n]) for i in range(len(seq) - n + 1)}


_readers = {}


def pages_of(pdf_name):
    """Cache one PdfReader per PDF and return its per-page extracted text."""
    if pdf_name not in _readers:
        from pypdf import PdfReader
        r = PdfReader(str(PDF_DIR / pdf_name))
        _readers[pdf_name] = [(p.extract_text() or "") for p in r.pages]
    return _readers[pdf_name]


def transliterated(text, rules):
    """Put raw PDF English through the reader-facing transformations, so a
    comparison isn't defeated by the very substitutions we made on purpose."""
    s = T.transliterate(text, rules)
    s = T.repair_stranded_yisra(s)
    s = T.yi_ye_to_yah(s)
    s = T.el_suffix_to_al(s)
    return s


def book_pdf_span(info):
    """(pdf name, first page, last page) covered by a book, 1-based."""
    by_pdf = {}
    for ch in info["chapters"].values():
        by_pdf.setdefault(ch["pdf"], []).append(ch["page"])
    # A book can straddle two volumes; report the span of each.
    return [(name, min(pp), max(pp)) for name, pp in by_pdf.items()]


# Page apparatus: a heading, a running header/footer, a page number. These
# are printed on the page but are not part of the reading, so the extractor
# is right to drop them.
APPARATUS = re.compile(
    r"\bChapter\s+[IVXLC]+\b|\bCHAP[.,]\s*[IVXLC]+|\bPage\s*\||"
    r"\bBook of [A-Z\u1e00-\u1eff]|\bTHE [A-Z ]{6,}\b", re.U)


def is_apparatus(text):
    if APPARATUS.search(text):
        return True
    letters = re.findall(r"[A-Za-z\u00c0-\u024f\u1e00-\u1eff]+", text)
    # A run that is mostly bare numbers is a column of page/verse numbers.
    return len(letters) < len(text.split()) * 0.5


def runs_of_misses(pdf_words, covered, min_run):
    out, start = [], None
    for i, ok in enumerate(covered + [True]):
        if not ok and start is None:
            start = i
        elif ok and start is not None:
            if i - start >= min_run:
                out.append((start, i))
            start = None
    return out


def corpus_shingles():
    """Every N-gram the reader can actually reach, across all 104 books."""
    known = set()
    for path in sorted(TEXT_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for cn in sorted(data["chapters"], key=int):
            for v in data["chapters"][cn]["verses"]:
                known |= shingles(words_of(v["t"]))
    return known


def scan(bid, info, rules, min_run, context, known):
    if not (TEXT_DIR / f"{bid}.json").exists():
        return []
    findings = []
    for pdf_name, first, last in book_pdf_span(info):
        pages = pages_of(pdf_name)
        # A chapter's text can spill past the page its heading sits on.
        lo, hi = max(1, first), min(len(pages), last + 2)
        raw = "\n".join(pages[p - 1] for p in range(lo, hi + 1))
        pdf_tokens = []
        for tok in TAG.sub(" ", transliterated(raw, rules)).split():
            pdf_tokens += GLUED.split(tok)
        pw = [fold(t) for t in pdf_tokens]
        pw = ["" if w.isdigit() else w for w in pw]
        keep = [i for i, w in enumerate(pw) if w]
        seq = [pw[i] for i in keep]
        if len(seq) < NGRAM:
            continue
        covered = [False] * len(seq)
        for i in range(len(seq) - NGRAM + 1):
            if tuple(seq[i:i + NGRAM]) in known:
                for j in range(i, i + NGRAM):
                    covered[j] = True
        for a, b in runs_of_misses(pdf_words=seq, covered=covered, min_run=min_run):
            lead = " ".join(pdf_tokens[keep[a]:keep[b - 1] + 1])
            before = " ".join(pdf_tokens[max(0, keep[a] - context):keep[a]])
            findings.append((pdf_name, b - a, before, lead, is_apparatus(lead)))
    return findings


def main():
    argv = [a for a in sys.argv[1:]]
    min_run = 10
    context = 8
    if "--min-run" in argv:
        i = argv.index("--min-run")
        min_run = int(argv[i + 1]); del argv[i:i + 2]
    show_all = "--all" in argv
    if "--context" in argv:
        i = argv.index("--context")
        context = int(argv[i + 1]); del argv[i:i + 2]
    wanted = [a for a in argv if not a.startswith("--")]

    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    rules = T.build_replacements(T.DIVINE, T.PEOPLE_PATRIARCHS, T.PEOPLE_LEADERS,
                                 T.PEOPLE_J_NAMES, T.PEOPLE_TRIBES, T.PLACES,
                                 T.TERMS)
    known = corpus_shingles()
    total = 0
    quiet = 0
    for b in index["books"]:
        if wanted and b["id"] not in wanted:
            continue
        if not b.get("chapters"):
            continue
        found = scan(b["id"], b, rules, min_run, context, known)
        real = [f for f in found if show_all or not f[4]]
        skipped = len(found) - len(real)
        if not real:
            if skipped:
                quiet += skipped
            continue
        print(f"\n=== {b['id']} ({b['english']}) — {len(real)} run(s)"
              + (f", {skipped} apparatus run(s) hidden" if skipped else ""))
        for pdf_name, n, before, text, apparatus in real:
            total += n
            print(f"  [{n:3} words]{' apparatus' if apparatus else ''} …{before}")
            print(f"      >>> {text}")
    print(f"\n{total} word(s) of PDF text unaccounted for "
          f"(runs of {min_run}+ words); {quiet} apparatus run(s) hidden.")


if __name__ == "__main__":
    main()
