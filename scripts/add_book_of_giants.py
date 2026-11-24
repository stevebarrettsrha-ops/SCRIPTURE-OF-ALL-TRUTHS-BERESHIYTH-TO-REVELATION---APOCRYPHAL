#!/usr/bin/env python3
"""
add_book_of_giants.py

Builds assets/text/apoc-giants.json — the Book of Giants (Gibborim) — from

    SCRIPTURE/The-Book-of-Giants-Lumpkin.pdf
    (Joseph B. Lumpkin, "The Book of Giants: The Watchers, Nephilim, and
     the Book of Enoch")

and records it in assets/index.json in the Ethiopic & Eastern Apocrypha
section, straight after Ḥanoḵ (Ethiopic), whose story it carries on.

Only the Book of Giants is taken. The volume also prints the whole of
1 Enoch (with the Giants fragments interleaved), which the canon already
has, and Lumpkin's own introductions and commentary; none of that is
brought in. Two chapters:

  1. The Aramaic version — the Qumran fragments (1Q23, 2Q26, 4Q530-532,
     6Q8) in the order Lumpkin reconstructs them, PDF pages 20-23.
  2. The Manichean version — the Middle Persian (Kawan) fragments of the
     giants' story, PDF pages 31-32. The pages Lumpkin prints after them,
     "On the Five Elements" and "On the Hearers", are Manichaean teaching
     from the same manuscript, not the giants' story, and are left out.

Each fragment is one verse. Its manuscript number (4Q531 Frag. 3 …) is
kept as the verse's note (<span class="fn">), shown under the verse and
left out of copies, so the text reads on while the source can still be
traced. Lumpkin's few editorial asides become notes too.

The fragments' square brackets become the reader's own marks, as for the
Dead Sea Scrolls psalms: "[ . . . ]" (words lost) reads "…", and a word
the editors restored is set lighter and in italic (<span class="rs">).
A bracket the print leaves unclosed (the restoration runs on to a gap)
is dropped rather than guessed at.

Transliteration is the canon's own (scripts/transliterate.py). Run
`python3 scripts/sweep_text.py --fix` afterwards, as for every book, so
the house words are applied. Safe to re-run.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import transliterate as T  # noqa: E402

PDF_NAME = "The-Book-of-Giants-Lumpkin.pdf"
PDF = ROOT / "SCRIPTURE" / PDF_NAME
OUT = ROOT / "assets" / "text" / "apoc-giants.json"
INDEX = ROOT / "assets" / "index.json"
BOOK_ID = "apoc-giants"
AFTER = "apoc-eth-enoch"

ARAMAIC_PAGES = (20, 23)      # 1-based PDF pages
MANICHEAN_PAGES = (31, 32)

SIGLUM = re.compile(
    r"^((?:1Q23|2Q26|4Q53[0-2]|6Q8)(?:\s+Col\.\s*\d+)?"
    r"(?:\s+Frags?\.\s*\d+(?:\s*[+\-–]\s*\d+)*)?)(?=\s|\[)")

# Lumpkin's own lines inside the reconstructed text.
SUPPLEMENT_NOTE = ("So much of the Aramaic version is missing in this area of the "
                   "text that to reconstruct the flow we have used the Manichean "
                   "version to supplement.")

# The Manichean pages set long vowels apart from their word ("S ā m").
MACRON = re.compile(r"(?<=[A-Za-zšŠ]) ?([āīūōēĀĪŪŌ]) ?(?=[A-Za-zšŠ])")
MACRON_START = re.compile(r"\b([ĀĪŪŌ]) (?=[a-z])")

SPECIALS = [
    ("decend", "descend"),
    ("not affect", "not effect"),
    ("[There]upon", "Thereupon"),
    ("There upon", "Thereupon"),
    ("[and monsters! grew", "[and monsters] grew"),
    ("giant's which", "giants which"),
    # a man's lord, not the Name (CLAUDE.md rule 3)
    ("but the lord that is above him", "but the master that is above him"),
]


def pages(first, last):
    from pypdf import PdfReader
    r = PdfReader(str(PDF))
    return "\n".join((r.pages[p - 1].extract_text() or "") for p in range(first, last + 1))


def paragraphs(text):
    text = text.replace("\t", " ")
    out = []
    for block in re.split(r"\n\s*\xa0\s*\n|\n\s*\n", text):
        s = re.sub(r"[\xa0\s]+", " ", block).strip()
        if s:
            out.append(s)
    return out


def tidy(s):
    s = re.sub(r"(\w)- (\w)", r"\1\2", s)               # hyphen at line end
    s = re.sub(r"\.(?:\s*\.){2,}", "…", s)               # ". . ." / ". .."
    s = re.sub(r"\.\s+\.(?=\s|$|\])", "…", s)            # ". ." split over lines
    s = s.replace("...", "…")
    for a, b in SPECIALS:
        s = s.replace(a, b)
    s = MACRON.sub(r"\1", s)
    s = MACRON_START.sub(r"\1", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def brackets(s):
    """[ … ] -> …, [words] -> restored span; unmatched brackets dropped."""
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c == "[":
            j = i + 1
            while j < n and s[j] not in "[]":
                j += 1
            if j < n and s[j] == "]":
                inner = s[i + 1:j].strip()
                if re.search(r"[A-Za-zÀ-ɏḀ-ỿ]", inner):
                    # a gap inside the brackets stays outside the restoration
                    lead = inner.startswith("…")
                    trail = inner.endswith("…")
                    inner = inner.strip("… ").rstrip()
                    out.append((" … " if lead else "") + '<span class="rs">' + inner
                               + "</span>" + (" … " if trail else ""))
                else:
                    out.append(" … ")
                i = j + 1
                continue
            i += 1                                       # unclosed: drop it
            continue
        if c == "]":
            i += 1                                       # stray close: drop it
            continue
        out.append(c)
        i += 1
    s = "".join(out)
    # restoration completing the word before it: "w<rs>ho</rs>" stays whole
    s = re.sub(r"\s*…(?:\s*…)*\s*", " … ", s)
    s = re.sub(r'…\s*([.,;:])(?!\w)', "…", s)
    s = re.sub(r"\s+([,;:.?!])", r"\1", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"^…\s*", "… ", s)
    s = re.sub(r'… "(?=[\s.,]|$)', '…"', s)
    return s


def translit(s, rules):
    s = T.transliterate(s, rules)
    s = T.repair_stranded_yisra(s)
    s = T.yi_ye_to_yah(s)
    s = T.el_suffix_to_al(s)
    s = T.annotate_hwhy(s)
    s = T.wrap_bare_divine(s)
    return s


def note(s):
    return ' <span class="fn">' + s + "</span>"


def aramaic():
    text = pages(*ARAMAIC_PAGES)
    text = text.split("Book of Giants -- Reconstructed Texts", 1)[1]
    text = text.split("This ends the Aramaic Version.", 1)[0]
    paras = paragraphs(text)
    paras.pop(0)          # Lumpkin's heading ("The wicked angels decend, …")
    verses, pending_note = [], None
    insert = False
    for p in paras:
        if p.startswith("(So much of the Aramaic"):
            pending_note = ("The editor: " + SUPPLEMENT_NOTE)
            continue
        if p.startswith("One version adds"):
            insert = True
            p = p.split(":", 1)[1].strip()
            p = re.sub(r'^[.\s]*"[.\s]*', '… "', p)     # '. . " . . for'
        if p.startswith("(This ends the Manichean addition"):
            continue
        p = tidy(p)
        m = SIGLUM.match(p)
        if m and not insert:
            sig = re.sub(r"\s+", " ", m.group(1)).replace("Frag.", "frag.").replace(
                "Frags.", "frags.").replace("Col.", "col.")
            sig = re.sub(r"frag\.(\d)", r"frag. \1", sig)
            sig = re.sub(r"\s*-\s*", "–", sig)
            body = p[m.end():].strip()
            fn = "Qumran, " + sig + "."
        elif insert:
            body, fn = p.replace("(This ends the Manichean addition.)", "").strip(), (
                "One version adds this passage, from the Manichean version.")
            insert = False
        else:
            body, fn = p, None
        if pending_note:
            fn = (fn + " " if fn else "") + pending_note
            pending_note = None
        verses.append((body, fn))
    return verses


def manichean():
    text = pages(*MANICHEAN_PAGES)
    text = text.split("Manichean Version of the Book of Giants", 1)[1]
    text = text.split("[On the Five Elements]", 1)[0]
    paras = paragraphs(text)
    # Lumpkin's own heading and the editors' remarks before the fragments
    while paras and not paras[0].startswith("…") and not paras[0].startswith(". ."):
        paras.pop(0)
    return [(tidy(p), None) for p in paras]


# Names the transliteration tables do not carry, in the forms the canon's
# own Ḥanoḵ already prints them (Semjaza, Azazal, Baraqal, Raphaal).
NAMES = [
    (r"\bShemihaza\b", "Semjaza"), (r"\bAzaiel\b", "Azazel"),
    (r"\bBaraq[’']el\b", "Baraqel"), (r"\bBarakel\b", "Baraqel"),
]

# Chapters, as runs of fragments: the Aramaic version (Qumran) in four,
# the Manichean in two. Each chapter's title is not printed (no book in the
# canon has chapter titles); it is here for whoever reads the script.
ARAMAIC_CHAPTERS = [
    (0, 5),     # 1  the Watchers' sin; the giants born and their violence
    (5, 13),    # 2  the tablet in the water; the giants' fear and dreams
    (13, 17),   # 3  the dreams of the two brothers; Mahway flies to Ḥanoḵ
    (17, 19),   # 4  Ḥanoḵ's tablet to Semjaza; the judgment
]
MANICHEAN_CHAPTERS = [
    (0, 3),     # 5  the giants' strife, the signs, Ḥanoḵ's message
    (3, 6),     # 6  the giants' boasts and proverbs; the rule of the Watchers
]
MIN_WORDS, MAX_WORDS = 7, 45


def split_points(t):
    """Offsets in t where a verse may begin: after a sentence's end, or at a
    gap ("…"), never inside a span."""
    sentence, gap, depth, i = [], [], 0, 0
    while i < len(t):
        if t.startswith("<span", i):
            depth += 1
        elif t.startswith("</span>", i):
            depth -= 1
        elif depth == 0 and t[i] == " " and i > 0:
            before, after = t[:i].rstrip(), t[i + 1:]
            if re.search(r"[.?!][\"”’']?$", before) and not before.endswith("…") \
                    and re.match(r"[A-Z\"“…<]", after):
                sentence.append(i)
            elif before.endswith("…") and not after.startswith("<span class=\"fn"):
                gap.append(i)
        i += 1
    return sentence, gap


def words(t):
    return len(re.findall(r"[A-Za-zḀ-ỿ']+", re.sub(r"<[^>]+>", " ", t)))


def verses_of(t):
    """One fragment -> verses the length of the canon's: split at sentences,
    then at gaps where a piece is still long; short pieces join the one
    before (or after, at the start)."""
    sentence, gap = split_points(t)
    pieces, last = [], 0
    for i in sentence:
        pieces.append(t[last:i].strip()); last = i
    pieces.append(t[last:].strip())
    out = []
    for piece in pieces:
        while words(piece) > MAX_WORDS:
            _, g = split_points(piece)
            # the gap nearest the middle that leaves both halves long enough
            best = None
            for i in g:
                a, b = words(piece[:i]), words(piece[i:])
                if a >= MIN_WORDS * 2 and b >= MIN_WORDS:
                    if best is None or abs(a - b) < abs(words(piece[:best]) - words(piece[best:])):
                        best = i
            if best is None:
                break
            out.append(piece[:best].strip()); piece = piece[best:].strip()
        out.append(piece)
    merged = []
    for piece in out:
        if merged and (words(piece) < MIN_WORDS or words(merged[-1]) < MIN_WORDS):
            merged[-1] += " " + piece
        else:
            merged.append(piece)
    return [m for m in merged if words(m)]


def render(body, rules):
    for a, b in NAMES:
        body = re.sub(a, b, body)
    return brackets(translit(body, rules))


def page_of(fragment, first, last):
    from pypdf import PdfReader
    r = PdfReader(str(PDF))
    key = re.sub(r"\W+", "", fragment)[:40]
    for p in range(first, last + 1):
        page = re.sub(r"\W+", "", tidy(r.pages[p - 1].extract_text() or ""))
        if key[:25] in page:
            return p
    return first


def main():
    rules = T.build_replacements(T.DIVINE, T.PEOPLE_PATRIARCHS, T.PEOPLE_LEADERS,
                                 T.PEOPLE_J_NAMES, T.PEOPLE_TRIBES, T.PLACES, T.TERMS)
    aram = [b for b, _ in aramaic()]
    mani = [b for b, _ in manichean()]
    assert len(aram) == 19, len(aram)
    assert len(mani) == 6, [m[:40] for m in mani]
    chapters, refs = {}, {}
    plan = [(aram, a, b, ARAMAIC_PAGES) for a, b in ARAMAIC_CHAPTERS] + \
           [(mani, a, b, MANICHEAN_PAGES) for a, b in MANICHEAN_CHAPTERS]
    for n, (frags, a, b, pages_) in enumerate(plan, 1):
        vs = []
        for frag in frags[a:b]:
            vs += verses_of(render(frag, rules))
        page = page_of(frags[a], *pages_)
        chapters[str(n)] = {"verses": [{"n": i, "t": t} for i, t in enumerate(vs, 1)],
                            "pdf": PDF_NAME, "page": page}
        refs[str(n)] = {"pdf": PDF_NAME, "page": page}
    data = {"id": BOOK_ID, "hebrew": "GIBBORIM", "english": "Book of Giants",
            "section": "Apocrypha", "chapter_count": len(chapters),
            "chapters": chapters}
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    entry = {k: data[k] for k in ("id", "hebrew", "english", "section", "chapter_count")}
    entry["chapters"] = refs
    books = [b for b in idx["books"] if b["id"] != BOOK_ID]
    at = next(i for i, b in enumerate(books) if b["id"] == AFTER) + 1
    books.insert(at, entry)
    idx["books"] = books
    INDEX.write_text(json.dumps(idx, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(chapters)} chapters, "
          + ", ".join(f"{k}:{len(c['verses'])}" for k, c in chapters.items()) + " verses")


if __name__ == "__main__":
    main()
