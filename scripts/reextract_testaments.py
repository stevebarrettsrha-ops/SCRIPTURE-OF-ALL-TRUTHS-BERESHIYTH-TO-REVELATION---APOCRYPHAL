"""Re-extract the Testaments of the Twelve Patriarchs with repaired chapter
detection.

The shared parser in extract_text.py dropped chapters whose marker the OCR
garbled: it required the verse-1 token to be "1"/"l" (the source also prints
a capital "I": "4 I Beware...") and required the chapter to open with a
letter/quote (some open with "[": "7 1 [Now I will declare..."). It also
dropped a chapter when the source mis-printed two consecutive chapters with
the same number (Judah labels both 25 and 26 as "26").

This re-extractor patches the two patterns, accepts a repeated chapter number
as the next chapter, and renumbers each testament's chapters 1..N in source
order (the reader numbers chapters from 1). Writes ENGLISH JSON; run the
transliteration pipeline afterwards.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extract_text as E  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "assets", "text")
INDEX_PATH = os.path.join(ROOT, "assets", "index.json")

# Patched patterns: allow "I" as the OCR'd verse-1 marker and "[" as a valid
# chapter/verse opening character.
E._TESTAMENT_CH_PAT = re.compile(
    r'\b(\d+)\s+[1lI](?:[,\s]+\d+)*\s*(?=[A-Z"“‘\'\[]|--)')
E._TESTAMENT_V_PAT = re.compile(
    r'(?:^|\s)(\d+)(?:[,\s]+\d+)*\s*(?=[A-Za-z"“‘\'\[]|--)')


def extract_testament(name):
    slc = E._testament_slices().get(name)
    if not slc:
        return {}
    # Collect chapter-marker positions. Accept a normal forward step (<=+5) or
    # a repeat of the current number (the source's duplicate-label glitch).
    positions, last = [], 0
    for m in E._TESTAMENT_CH_PAT.finditer(slc):
        ch = int(m.group(1))
        if last < ch <= last + 5:
            positions.append(m.start()); last = ch
        elif ch == last and positions:
            positions.append(m.start()); last = ch + 1

    chapters, seq = {}, 0
    first = positions[0] if positions else len(slc)
    pre = slc[:first].strip()
    if pre:                                   # unmarked opening = chapter 1
        verses = E._parse_testament_verses(pre, ch_num=0) or [{"n": 1, "t": pre}]
        seq += 1
        chapters[seq] = verses
    for i, pos in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(slc)
        chunk = slc[pos:end]
        mnum = re.match(r"\s*(\d+)", chunk)
        printed = int(mnum.group(1)) if mnum else 0
        verses = E._parse_testament_verses(chunk, ch_num=printed)
        if verses:
            seq += 1
            chapters[seq] = verses
    return chapters


def main():
    index = json.load(open(INDEX_PATH, encoding="utf-8"))
    by_id = {b["id"]: b for b in index["books"]}
    for bid, tname in E.TESTAMENT_NAMES.items():
        chapters = extract_testament(tname)
        if not chapters:
            print(f"{bid}: NO CHAPTERS"); continue
        meta = by_id[bid]
        page = next(iter(meta["chapters"].values())).get("page", 1) \
            if meta.get("chapters") else 1
        pdf = next(iter(meta["chapters"].values())).get("pdf",
              "THE TESTAMENTS OF THE TWELVE PATRIARCHS.pdf") \
            if meta.get("chapters") else "THE TESTAMENTS OF THE TWELVE PATRIARCHS.pdf"
        out_ch = {str(c): {"verses": chapters[c], "page": page, "pdf": pdf}
                  for c in sorted(chapters)}
        out = {
            "id": bid, "hebrew": meta["hebrew"], "english": meta["english"],
            "section": meta["section"], "chapter_count": len(out_ch),
            "chapters": out_ch,
        }
        with open(os.path.join(OUT_DIR, f"{bid}.json"), "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        tv = sum(len(c["verses"]) for c in out_ch.values())
        print(f"{bid:22} {len(out_ch):3} chapters, {tv:4} verses")
        meta["chapter_count"] = len(out_ch)
        meta["chapters"] = {str(c): {"pdf": pdf, "page": page}
                            for c in sorted(chapters)}
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    print("index.json updated")


if __name__ == "__main__":
    main()
