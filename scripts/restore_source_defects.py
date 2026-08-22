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
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT_DIR = ROOT / "assets" / "text"

FN = ' <span class="fn">Supplied — the printed source omits this verse.</span>'

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
