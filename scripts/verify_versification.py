#!/usr/bin/env python3
"""
verify_versification.py

Proves the 66-book canon carries the standard versification, book by book:
the same chapter count as the KJV tradition, and the same final verse
number in every chapter. Together with audit_structure.py (which proves
every chapter's numbering is contiguous from 1), a clean run here means the
verse structure of all 66 books is exactly the standard one — nothing
missing, nothing extra, nothing misnumbered.

The reference data comes from the `pythonbible` package (pip install
pythonbible), which encodes the standard KJV versification.

Usage:
    python3 scripts/verify_versification.py     # exit 1 on any difference
"""
import json
import sys
from pathlib import Path

try:
    import pythonbible as pb
except ImportError:
    raise SystemExit("Need the `pythonbible` package: pip install pythonbible")

ROOT = Path(__file__).resolve().parent.parent
TEXT_DIR = ROOT / "assets" / "text"

B = pb.Book
BOOKS = {
 'bereshith': B.GENESIS, 'shamoth': B.EXODUS, 'wayyiqra': B.LEVITICUS,
 'bamidbar': B.NUMBERS, 'dabarim': B.DEUTERONOMY, 'yahusha': B.JOSHUA,
 'shophetim': B.JUDGES, 'ruth': B.RUTH, '1shamual': B.SAMUEL_1,
 '2shamual': B.SAMUEL_2, '1malakim': B.KINGS_1, '2malakim': B.KINGS_2,
 '1dibre-hayamim': B.CHRONICLES_1, '2dibre-hayamim': B.CHRONICLES_2,
 'ezra': B.EZRA, 'nehemyah': B.NEHEMIAH, 'ester': B.ESTHER, 'iyob': B.JOB,
 'tehillim': B.PSALMS, 'mishle': B.PROVERBS, 'qoheleth': B.ECCLESIASTES,
 'shir-hashirim': B.SONG_OF_SONGS, 'yashayahu': B.ISAIAH,
 'yirmayahu': B.JEREMIAH, 'ekah': B.LAMENTATIONS, 'yahazqal': B.EZEKIEL,
 'danial': B.DANIEL, 'hoshea': B.HOSEA, 'yoal': B.JOEL, 'amos': B.AMOS,
 'obadyahu': B.OBADIAH, 'yonah': B.JONAH, 'mikah': B.MICAH,
 'nahum': B.NAHUM, 'habaqquq': B.HABAKKUK, 'tsephanyahu': B.ZEPHANIAH,
 'haggai': B.HAGGAI, 'zakaryahu': B.ZECHARIAH, 'malaki': B.MALACHI,
 'mattithyahu': B.MATTHEW, 'mark': B.MARK, 'luke': B.LUKE,
 'yahuchanon': B.JOHN, 'acts': B.ACTS, 'romans': B.ROMANS,
 '1corinthians': B.CORINTHIANS_1, '2corinthians': B.CORINTHIANS_2,
 'galatians': B.GALATIANS, 'ephesians': B.EPHESIANS,
 'philippians': B.PHILIPPIANS, 'colossians': B.COLOSSIANS,
 '1thessalonians': B.THESSALONIANS_1, '2thessalonians': B.THESSALONIANS_2,
 '1timothy': B.TIMOTHY_1, '2timothy': B.TIMOTHY_2, 'titus': B.TITUS,
 'philemon': B.PHILEMON, 'ibrim': B.HEBREWS, 'yaaqob': B.JAMES,
 '1kepha': B.PETER_1, '2kepha': B.PETER_2, '1yahuchanon': B.JOHN_1,
 '2yahuchanon': B.JOHN_2, '3yahuchanon': B.JOHN_3, 'yahudah': B.JUDE,
 'hazon': B.REVELATION,
}


def main():
    diffs = []
    matched = 0
    for bid, kb in BOOKS.items():
        d = json.loads((TEXT_DIR / f"{bid}.json").read_text(encoding="utf-8"))
        chs = d["chapters"]
        want_c = pb.get_number_of_chapters(kb)
        if len(chs) != want_c:
            diffs.append(f"{bid}: {len(chs)} chapters, standard has {want_c}")
            continue
        clean = True
        for c in range(1, want_c + 1):
            want_last = pb.get_number_of_verses(kb, c)
            got_last = chs[str(c)]["verses"][-1]["n"]
            if got_last != want_last:
                diffs.append(f"{bid} {c}: last verse {got_last}, "
                             f"standard has {want_last}")
                clean = False
        if clean:
            matched += 1

    print(f"{matched}/{len(BOOKS)} books match the standard versification "
          f"chapter-for-chapter, verse-for-verse.")
    for x in diffs:
        print(f"  ! {x}")
    if diffs:
        sys.exit(1)


if __name__ == "__main__":
    main()
