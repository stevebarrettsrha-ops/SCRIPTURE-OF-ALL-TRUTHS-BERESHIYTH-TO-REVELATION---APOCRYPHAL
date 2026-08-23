#!/usr/bin/env python3
"""
restore_source_defects.py

The printed sources themselves carry a handful of defects that no parser can
read around: a verse number the volume never printed (so two verses run
together), a verse printed out of place, and a few verses whose text the
printing omitted outright. This script holds each such repair, verse by
verse, and applies it idempotently after extraction and transliteration.

Three kinds of repair, in honesty order:

  SPLITS   — the verse's words are all present, only the printed number is
             missing or garbled; the text is cut where the number belongs.
  INSERTS  — the verse's words are printed in the source, but somewhere a
             parser cannot bind them (out of order, marker destroyed); the
             text is taken verbatim from the source page.
  SUPPLIES — the printing omits the verse altogether; the verse is supplied
             in the edition's own voice and marked with a footnote saying
             so, because a reader must be able to tell supplied text from
             the source's.

Run after transliterate.py; safe to run any number of times:

    python3 scripts/restore_source_defects.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT_DIR = ROOT / "assets" / "text"

FN = ' <span class="fn">Supplied — the printed source omits this verse.</span>'
FN_RESTORED = (' <span class="fn">Restored — the scan of the printed source '
               'garbled this verse.</span>')

# (book, chapter, verse-to-split, text of the NEW verse that begins where the
# split lands; the remainder stays with the original verse)
SPLITS = [
    # The Besorah prints Luke 21:1-2 as one verse — the "2" never made it to
    # the plate ("…into the treasury and He saw a certain poor widow…").
    ("luke", "21", 1, 2, "and He saw a certain poor widow putting in two mites."),
    # Yirmayahu 51:1-2, the same fault ("…My opponents. And I shall send
    # winnowers to Baḇal…").
    ("yirmayahu", "51", 1, 2,
     "And I shall send winnowers to Baḇal, who shall winnow her and empty "
     "her land. For they shall be against her all around, in the day of evil."),
    # Chanok 9:31's marker is set as "3l" — the scan's l for 1.
    ("chanok", "9", 30, 31,
     "For wisdom is poured out like water, and esteem faileth not before "
     "Him for evermore."),
]

# Splits where the missing verse's words are already inside the previous
# verse, behind a marker the scan garbled — "67" left inline, "n" for 11,
# "S" for 8. The verse is cut where the print's own marker sits; the marker
# itself is removed from the reading. `head_n` renumbers the head where the
# print gave one number to two verses' text (Yoḇelim 19:26-27).
SPLITS2 = [
    dict(book="yashar", ch="23", src=66, new=67, marker="67",
         probe="O Yahuah, thou art a merciful and compassionate King"),
    dict(book="yashar", ch="63", src=23, new=24, marker="24",
         probe="O Yahuah Aluahim of A\u1e07raham and Yahts\u1e25aq my ancestors"),
    dict(book="apoc-jubilees", ch="19", src=24, new=25,
         probe="And these shall serve to lay the foundations"),
    dict(book="apoc-jubilees", ch="19", src=27, new=27, head_n=26,
         probe="\"Ya'aqo\u1e07, my beloved son"),
    dict(book="apoc-jubilees", ch="32", src=10, new=11, marker="n",
         probe="In its year shall the seed be eaten"),
    dict(book="apoc-jubilees", ch="41", src=10, new=11, marker="n",
         probe="She said to him, \"Give me my pay"),
    dict(book="apoc-jubilees", ch="48", src=7, new=8, marker="S",
         probe="Prince Mastema stood against you"),
]

# The scan destroyed the middle of this verse (only "…a sevenfold crop"
# survives); the print carries it, and the wording is the RSV the volume is
# set from. The garbage bytes it left in the verse before are cleaned.
RESTORES = [
    ("apoc-sirach", "8", 3,
     "My son, do not sow the furrows of injustice, and you will not reap a "
     "sevenfold crop."),
]
CLEANUPS = [
    ("apoc-sirach", "8", 2,
     "Stay away from wrong, and it will turn away from you."),
]

# Verses that do not belong: the page window of a book's last chapter can
# swallow the tail of the book printed beside it. Each entry names a verse
# to delete, with the place its text actually belongs.
DELETES = [
    # Nahum 3 ends at 19; this "verse 20" is Mikah 7:20, which stands in
    # its own book.
    ("nahum", "3", 20),
]

# (book, chapter, verse number, verse text) — text verbatim from the PDF.
INSERTS = [
    # The Besorah prints Yahazqal 37:18 pages out of place (its words sit
    # between 37:6 and 37:7 in the page flow), so no parser can bind it.
    ("yahazqal", "37", 18,
     "“And when the children of your people speak to you, saying, ‘Won’t "
     "you show us what you mean by these?’"),
    # Mishle 12:13 is printed with its marker clipped to "3" at the column
    # edge; the words are on the page.
    ("mishle", "12", 13,
     "In the transgression of the lips is an evil snare, But the righteous "
     "gets out of distress."),
]

# (book, chapter, verse number, verse text) — the printing omits the verse;
# supplied in the edition's own voice, with the footnote appended.
SUPPLIES = [
    ("mikah", "7", 17,
     "They lick dust like a serpent, they crawl from their holes like "
     "snakes of the earth. They are afraid of "
     '(<span class="dn">YAHUAH</span>) <span class="hwhy">HWHY</span> our '
     '<span class="dn">Aluahim</span>, and they fear because of You.'),
    ("iyob", "24", 21,
     "He treats evil the barren who does not bear, and does no good for "
     "the widow."),
    ("apoc-azariah", "1", 1,
     "And they walked about in the midst of the flames, singing hymns to "
     '<span class="dn">Aluahim</span> and blessing '
     '<span class="dn">Yahuah</span>.'),
    ("apoc-manasseh", "1", 1,
     'O <span class="dn">Yahuah</span> Almighty, '
     '<span class="dn">Aluahim</span> of our fathers, of Aḇraham and '
     "Yahtsḥaq and Ya'aqoḇ and of their righteous posterity;"),
    ("apoc-psalm151", "1", 1,
     "I was small among my brothers, and youngest in my father's house; I "
     "tended my father's sheep."),
    ("apoc-susanna", "1", 1,
     "There was a man living in Babylon whose name was Yoaqim."),
]


def _find_plain(text, probe):
    """Find `probe` in `text` ignoring markup: the divine names inside a
    verse are wrapped in spans, so a plain-words probe must see through the
    tags. Returns the index into the ORIGINAL text, or -1."""
    plain, back = [], []
    for m in re.finditer(r"<[^>]+>|.", text, re.S):
        if not m.group(0).startswith("<"):
            plain.append(m.group(0))
            back.append(m.start())
    j = "".join(plain).find(re.sub(r"<[^>]+>", "", probe))
    return back[j] if j >= 0 else -1


def load(bid):
    p = TEXT_DIR / f"{bid}.json"
    return p, json.loads(p.read_text(encoding="utf-8"))


def save(p, d):
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n",
                 encoding="utf-8")


def main():
    changed = 0
    for bid, cn, src_n, new_n, new_text in SPLITS:
        p, d = load(bid)
        vs = d["chapters"][cn]["verses"]
        if any(v["n"] == new_n for v in vs):
            continue                          # already split
        src = next(v for v in vs if v["n"] == src_n)
        # the tail of the merged verse must carry the new verse's words
        probe = new_text[:40].split("<")[0].strip()
        i = src["t"].find(probe)
        if i < 0:
            print(f"  !! {bid} {cn}:{src_n}: split anchor not found; skipped")
            continue
        head = src["t"][:i].rstrip()
        # drop a garbled marker ("3l") left dangling before the cut
        head = head.rstrip("l1 ").rstrip()
        src["t"] = head
        vs.insert(vs.index(src) + 1, {"n": new_n, "t": new_text})
        save(p, d)
        changed += 1
        print(f"  split {bid} {cn}:{src_n} -> {src_n},{new_n}")

    for e in SPLITS2:
        p, d = load(e["book"])
        vs = d["chapters"][e["ch"]]["verses"]
        head_n = e.get("head_n", e["src"])
        if any(v["n"] == e["new"] for v in vs) and (
                e["new"] != e["src"] or any(v["n"] == head_n for v in vs)):
            continue                          # already split
        src = next(v for v in vs if v["n"] == e["src"])
        i = _find_plain(src["t"], e["probe"])
        if i < 0:
            print(f"  !! {e['book']} {e['ch']}:{e['src']}: probe not found; skipped")
            continue
        head, tail = src["t"][:i].rstrip(), src["t"][i:].strip()
        m = e.get("marker")
        if m and head.endswith(m):
            head = head[:-len(m)].rstrip()
        src["t"] = head
        src["n"] = head_n
        vs.insert(vs.index(src) + 1, {"n": e["new"], "t": tail})
        save(p, d)
        changed += 1
        print(f"  split {e['book']} {e['ch']}:{e['src']} -> {head_n},{e['new']}")

    for bid, cn, n in DELETES:
        p, d = load(bid)
        vs = d["chapters"][cn]["verses"]
        if any(v["n"] == n for v in vs):
            d["chapters"][cn]["verses"] = [v for v in vs if v["n"] != n]
            save(p, d)
            changed += 1
            print(f"  delete {bid} {cn}:{n}")

    for bid, cn, n, text in CLEANUPS:
        p, d = load(bid)
        vs = d["chapters"][cn]["verses"]
        v = next(x for x in vs if x["n"] == n)
        if v["t"] != text:
            v["t"] = text
            save(p, d)
            changed += 1
            print(f"  cleanup {bid} {cn}:{n}")

    for bid, cn, n, text in RESTORES:
        p, d = load(bid)
        vs = d["chapters"][cn]["verses"]
        if not any(v["n"] == n for v in vs):
            at = next((i for i, v in enumerate(vs) if v["n"] > n), len(vs))
            vs.insert(at, {"n": n, "t": text + FN_RESTORED})
            save(p, d)
            changed += 1
            print(f"  restore {bid} {cn}:{n}")

    for kind, table in (("insert", INSERTS), ("supply", SUPPLIES)):
        for bid, cn, n, text in table:
            p, d = load(bid)
            vs = d["chapters"][cn]["verses"]
            if any(v["n"] == n for v in vs):
                continue
            t = text + (FN if kind == "supply" else "")
            at = next((i for i, v in enumerate(vs) if v["n"] > n), len(vs))
            vs.insert(at, {"n": n, "t": t})
            save(p, d)
            changed += 1
            print(f"  {kind} {bid} {cn}:{n}")
    print(f"{changed} repair(s) applied.")


if __name__ == "__main__":
    main()
