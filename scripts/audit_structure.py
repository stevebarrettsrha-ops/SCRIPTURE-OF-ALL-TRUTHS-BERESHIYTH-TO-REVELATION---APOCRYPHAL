#!/usr/bin/env python3
"""
audit_structure.py

The structural companion to sweep_text.py: where the sweeper checks the
inside of each verse, this audits the shape of the whole canon — that every
book holds chapters 1..N, that the index agrees, that each book has the
number of chapters its edition prints, and that verse numbering inside
every chapter runs 1, 2, 3 … without a gap, a duplicate, or a hole.

A numbering gap is treated as an error unless it is listed in
KNOWN_SOURCE_GAPS: each entry there was checked against the printed page
and found to be the source's own — a verse the edition omits (the RSV
apocrypha omit many Sirach verses), groups into a range ("[15-26]"), or
prints out of order. Nothing goes into that list without the page having
been read.

Usage:
    python3 scripts/audit_structure.py          # exit 1 on any un-vouched fault
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT_DIR = ROOT / "assets" / "text"
INDEX_PATH = ROOT / "assets" / "index.json"

# Chapters per book, as the SOURCE EDITIONS print them. The 66-book canon is
# fixed; the companions follow their own editions (the Jay Winter Enoch is
# set as three Books whose 25 chapters are numbered here continuously; the
# Lumpkin Sirach counts its translator's prologue as a chapter, so 52).
CHAPTERS = {
 'bereshith': 50, 'shamoth': 40, 'wayyiqra': 27, 'bamidbar': 36,
 'dabarim': 34, 'yahusha': 24, 'shophetim': 21, 'ruth': 4, '1shamual': 31,
 '2shamual': 24, '1malakim': 22, '2malakim': 25, '1dibre-hayamim': 29,
 '2dibre-hayamim': 36, 'ezra': 10, 'nehemyah': 13, 'ester': 10, 'iyob': 42,
 'tehillim': 150, 'mishle': 31, 'qoheleth': 12, 'shir-hashirim': 8,
 'yashayahu': 66, 'yirmayahu': 52, 'ekah': 5, 'yahazqal': 48, 'danial': 12,
 'hoshea': 14, 'yoal': 3, 'amos': 9, 'obadyahu': 1, 'yonah': 4, 'mikah': 7,
 'nahum': 3, 'habaqquq': 3, 'tsephanyahu': 3, 'haggai': 2, 'zakaryahu': 14,
 'malaki': 4,
 'mattithyahu': 28, 'mark': 16, 'luke': 24, 'yahuchanon': 21, 'acts': 28,
 'romans': 16, '1corinthians': 16, '2corinthians': 13, 'galatians': 6,
 'ephesians': 6, 'philippians': 4, 'colossians': 4, '1thessalonians': 5,
 '2thessalonians': 3, '1timothy': 6, '2timothy': 4, 'titus': 3,
 'philemon': 1, 'ibrim': 13, 'yaaqob': 5, '1kepha': 5, '2kepha': 3,
 '1yahuchanon': 5, '2yahuchanon': 1, '3yahuchanon': 1, 'yahudah': 1,
 'hazon': 22,
 'yashar': 91, 'chanok': 25, 'apoc-eth-enoch': 108, 'apoc-jubilees': 50,
 'apoc-1esdras': 9, 'apoc-2esdras': 16, 'apoc-1maccabees': 16,
 'apoc-2maccabees': 15, 'apoc-3maccabees': 7, 'apoc-4maccabees': 18,
 'apoc-tobit': 14, 'apoc-judith': 16, 'apoc-wisdom': 19, 'apoc-baruch': 5,
 'apoc-1clements': 65, 'apoc-hermas': 114, 'apoc-sirach': 52,
 'apoc-esther-add': 7,
 'testament-reuben': 7, 'testament-shimeon': 9, 'testament-levi': 19,
 'testament-yahudah': 26, 'testament-issakar': 7, 'testament-zebulun': 10,
 'testament-dan': 7, 'testament-naphtali': 9, 'testament-gad': 8,
 'testament-asher': 8, 'testament-yoseph': 20, 'testament-benyamin': 12,
 'adam-eve-1': 79, 'adam-eve-2': 22,
 'apoc-azariah': 1, 'apoc-manasseh': 1, 'apoc-susanna': 1,
 'apoc-bel-dragon': 1, 'apoc-epistle-jeremiah': 1, 'apoc-psalm151': 1,
}

# (book, chapter, last verse before the gap, first verse after) — every one
# verified against the printed page. "start" means the chapter opens there.
KNOWN_SOURCE_GAPS = {
    # RSV prints "[4]" with no text (a manuscript omission it footnotes).
    ("apoc-4maccabees", "10", 3, 5),
    # The print carries no text for 11:7-8.
    ("apoc-4maccabees", "11", 6, 9),
    # The print sets Addition 11:1 — the Greek colophon — at the END of the
    # book, where it stands as 7:11; chapter 1 therefore opens at verse 2.
    ("apoc-esther-add", "1", "start", 2),
    # Lumpkin's Jubilees runs these verses into the one before them.
    ("apoc-jubilees", "19", 24, 27), ("apoc-jubilees", "32", 10, 12),
    ("apoc-jubilees", "41", 10, 12), ("apoc-jubilees", "48", 7, 9),
    # The RSV-lineage Sirach omits many verses and prints others as grouped
    # ranges ("[15-26]"); the numbering here mirrors that page for page.
    ("apoc-sirach", "1", 1, 15), ("apoc-sirach", "1", 15, 27),
    ("apoc-sirach", "2", 18, 22), ("apoc-sirach", "4", 18, 20),
    ("apoc-sirach", "4", 24, 26), ("apoc-sirach", "8", 2, 4),
    ("apoc-sirach", "11", 20, 22), ("apoc-sirach", "12", 14, 17),
    ("apoc-sirach", "14", 13, 15), ("apoc-sirach", "17", 14, 17),
    ("apoc-sirach", "18", 4, 6), ("apoc-sirach", "18", 8, 10),
    ("apoc-sirach", "18", 15, 17), ("apoc-sirach", "18", 17, 19),
    ("apoc-sirach", "18", 20, 22), ("apoc-sirach", "19", 2, 4),
    ("apoc-sirach", "20", 17, 20), ("apoc-sirach", "20", 20, 22),
    ("apoc-sirach", "21", 2, 4), ("apoc-sirach", "23", 8, 11),
    ("apoc-sirach", "25", 17, 19), ("apoc-sirach", "25", 23, 25),
    ("apoc-sirach", "26", 11, 13), ("apoc-sirach", "27", 18, 28),
    # The 1887 Jasher printing omits these two verses (the page shows the
    # numbering step over them).
    ("yashar", "23", 66, 68), ("yashar", "63", 23, 25),
}

TAG = re.compile(r"<[^>]+>")


def main():
    idx = {b["id"]: b for b in
           json.loads(INDEX_PATH.read_text(encoding="utf-8"))["books"]}
    problems, vouched = [], 0
    files = sorted(TEXT_DIR.glob("*.json"))
    tot_c = tot_v = 0
    for fp in files:
        d = json.loads(fp.read_text(encoding="utf-8"))
        bid = d["id"]
        chs = d["chapters"]
        meta = idx.get(bid)
        if not meta:
            problems.append(f"{bid}: not in index.json")
        else:
            if meta["chapter_count"] != len(chs):
                problems.append(f"{bid}: index says {meta['chapter_count']} "
                                f"chapters, text has {len(chs)}")
            if set(meta["chapters"]) != set(chs):
                problems.append(f"{bid}: index chapter keys differ from text")
        if d["chapter_count"] != len(chs):
            problems.append(f"{bid}: chapter_count field {d['chapter_count']}"
                            f" != {len(chs)}")
        keys = sorted(int(k) for k in chs)
        if keys != list(range(1, len(keys) + 1)):
            problems.append(f"{bid}: chapter keys not 1..N")
        want = CHAPTERS.get(bid)
        if want is None:
            problems.append(f"{bid}: no expected chapter count on record")
        elif len(chs) != want:
            problems.append(f"{bid}: {len(chs)} chapters, edition has {want}")
        tot_c += len(chs)
        for cn in sorted(chs, key=int):
            vs = chs[cn]["verses"]
            if not vs:
                problems.append(f"{bid} {cn}: no verses")
                continue
            ns = [v["n"] for v in vs]
            tot_v += len(ns)
            if ns[0] != 1:
                if (bid, cn, "start", ns[0]) in KNOWN_SOURCE_GAPS:
                    vouched += 1
                else:
                    problems.append(f"{bid} {cn}: opens at verse {ns[0]}")
            if len(set(ns)) != len(ns):
                problems.append(f"{bid} {cn}: duplicate verse numbers")
            if ns != sorted(ns):
                problems.append(f"{bid} {cn}: verse numbers out of order")
            for a, b in zip(ns, ns[1:]):
                if b != a + 1:
                    if (bid, cn, a, b) in KNOWN_SOURCE_GAPS:
                        vouched += 1
                    else:
                        problems.append(f"{bid} {cn}: numbering jumps "
                                        f"{a} -> {b}")
            for v in vs:
                if not TAG.sub("", v["t"]).strip():
                    problems.append(f"{bid} {cn}:{v['n']}: empty verse")

    print(f"Audited {len(files)} books · {tot_c} chapters · {tot_v} verses")
    print(f"  source-vouched numbering gaps  {vouched}")
    print(f"  structural faults              {len(problems)}")
    for p in problems:
        print(f"    ! {p}")
    if problems:
        sys.exit(1)
    print("Every chapter present, every verse accounted for.")


if __name__ == "__main__":
    main()
