"""Re-extract the Testaments of the Twelve Patriarchs.

The source is R. H. Charles's edition, and it numbers verses the way a
printed page does: the small number sits in the MARGIN, beside the line on
which the verse begins — not against the first word of the verse. Flattened
into a stream of text by the PDF, that number lands wherever the line
happened to break:

    8 1 And when Simeon had made an end of commanding his sons, he slept
    with his fathers, being an 2 hundred and twenty years old. And they
    laid him in a wooden coffin, to take up his bones to 3 Hebron.

Splitting at the digit — what the previous extractor did — produced verses
that opened mid-sentence ("hundred and twenty years old") and closed on a
dangling preposition ("to take up his bones to"). A quarter of the verses
in some testaments read that way.

So a marker here is not a cut, it is a *hint*: the verse begins at a
sentence boundary somewhere on that line. This extractor moves each split
to the sentence boundary nearest the marker — forwards or backwards,
whichever is closer — subject to it landing after the previous verse's
start. On the passage above that recovers Charles exactly:

    1 And when Simeon had made an end of commanding his sons, he slept with
      his fathers, being an hundred and twenty years old.
    2 And they laid him in a wooden coffin, to take up his bones to Hebron.
    3 And they took them up secretly during a war of the Egyptians.

Two further defects are repaired here:

  * Dropped chapter openings. A testament's slice began at "The copy of the
    words of Judah", leaving its "1 1, 2" marker behind in the previous
    testament; the parser then took the first marker it could see (the "3"
    twelve words in) as the chapter's first verse and threw away everything
    before it. Judah, Levi, Zebulun and others each lost their opening
    sentences. The slice now starts at the marker.

  * Combined markers. "1, 2" or "1, 2, 3" printed together means several
    verses begin on that one line; each one after the first now takes the
    next sentence, instead of being dropped.

Writes ENGLISH JSON; run the transliteration pipeline afterwards:

    python3 scripts/reextract_testaments.py
    python3 scripts/transliterate.py testament-reuben testament-shimeon …
    python3 scripts/sweep_text.py --fix
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
PDF_NAME = "THE TESTAMENTS OF THE TWELVE PATRIARCHS.pdf"

# "<chapter> <verse>[, <verse>…] <Text>" opens a chapter. The OCR renders a
# verse-1 marker as "1", "l" or "I", and a chapter can open on a bracket.
# Several verses can share one printed line, and the source writes that
# either "1, 2" or "1 2".
_RUN = r"(?:\s*,\s*\d+|\s+\d+)*"
CH_PAT = re.compile(r"\b(\d+)\s+([1lI]" + _RUN + r")\s*(?=[A-Z\"“‘'\[]|--)")
# A bare number inside the body: one or more verse numbers on one line.
V_PAT = re.compile(r"(?<=\s)(\d+" + _RUN + r")\s+(?=[A-Za-z\"“‘'\[]|--)")
# The end of a sentence: terminal punctuation, any closing quote, a space.
SENT_END = re.compile(r"[.!?][\"”’')\]]*\s")


def _numbers(token):
    return [int(x) for x in re.findall(r"\d+", token)]


def _sentence_starts(text):
    """Every offset in `text` at which a new sentence begins."""
    return [m.end() for m in SENT_END.finditer(text)]


def _snap(starts, marker_pos, floor):
    """Move a marker to the sentence boundary the printed line points at.

    `marker_pos` is where the number sat in the flattened text — the start
    of a printed line, so the verse begins somewhere on that line, either
    just before the number or just after it. Take whichever sentence
    boundary is nearer, provided it lies beyond `floor` (the previous
    verse's start); if neither does, keep the marker where it is.
    """
    before = [s for s in starts if floor < s <= marker_pos]
    after = [s for s in starts if s > marker_pos and s > floor]
    cand = []
    if before:
        cand.append((marker_pos - before[-1], before[-1]))
    if after:
        cand.append((after[0] - marker_pos, after[0]))
    if not cand:
        return max(marker_pos, floor)
    return min(cand)[1]


def _strip_markers(chunk, opening):
    """Take the verse numbers out of the prose and say where they stood.

    Returns (clean text, [(verse number, offset into clean text), …]). A
    number that does not continue the sequence is left where it is: it is
    part of the reading ("a hundred and thirty-seven years"), not a marker.
    """
    expected = (opening[-1] if opening else 1) + 1
    accepted = []                       # (numbers on this line, span to cut)
    for m in V_PAT.finditer(chunk):
        run = m.group(1)
        take, cut_to = [], None
        for d in re.finditer(r"\d+", run):
            n = int(d.group(0))
            if n != expected:
                # Only the numbers before this one were markers; the rest
                # of the run is prose and must stay where it is.
                cut_to = m.start(1) + d.start()
                break
            take.append(n)
            expected = n + 1
        if take:
            accepted.append((take, (m.start(), cut_to if cut_to is not None
                                    else m.end())))

    out, marks, cut = [], [], 0
    for nums, (a, b) in accepted:
        out.append(chunk[cut:a])
        pos = sum(len(x) for x in out)
        for n in nums:
            marks.append((n, pos))
        cut = b
    out.append(chunk[cut:])
    return "".join(out), marks


def _parse_chapter(chunk, opening):
    """Split one chapter's text into verses.

    `opening` is the list of verse numbers printed with the chapter heading
    ("1", or "1, 2"); `chunk` is the text that follows it.
    """
    clean, marks = _strip_markers(chunk, opening)
    # Verses that share the heading's line ("1, 2") begin at the top of the
    # chapter, so they resolve against the same position as verse 1.
    marks = [(n, 0) for n in (opening[1:] if opening else [])] + marks
    starts = _sentence_starts(clean)

    cuts, floor = [], 0
    for n, pos in marks:
        at = _snap(starts, pos, floor)
        if at <= floor:                 # nothing left to give this verse
            continue
        cuts.append((n, at))
        floor = at

    verses = []
    bounds = [(opening[0] if opening else 1, 0)] + cuts
    for i, (n, at) in enumerate(bounds):
        end = bounds[i + 1][1] if i + 1 < len(bounds) else len(clean)
        text = re.sub(r"\s+", " ", clean[at:end]).strip()
        if text:
            verses.append({"n": n, "t": text})
    return verses


def _slices():
    """{'reuben': '<text>', …} — one contiguous run of text per testament.

    Same page cleaning as extract_text, but the cut is made BEFORE the
    chapter/verse marker that precedes the opening words ("1 1, 2 The copy
    of the words of Judah…"), not after it. Cutting after it is what left
    Judah, Levi and their brothers without the first sentences of chapter 1.
    """
    rdr = E.get_pdf(PDF_NAME)
    full = ""
    for pg in range(1, len(rdr.pages) + 1):
        text = rdr.pages[pg - 1].extract_text() or ""
        text = re.sub(r"Page\s*\|\s*\d+\s*", "", text)
        text = re.sub(r"www\.Scriptural-Truth\.com", "", text)
        text = re.sub(r"\[The Apocrypha and Pseudepigrapha[^\]]*\]", "", text)
        full += text + "\n"
    full = re.sub(r"\s+", " ", full)

    bounds = []
    for m in E._TESTAMENT_OPENER.finditer(full):
        start = m.start()
        back = re.search(r"\d+\s+[1lI](?:\s*,\s*\d+)*\s+$", full[:start])
        bounds.append((m.group(1).lower(), back.start() if back else start))
    out = {}
    for i, (name, start) in enumerate(bounds):
        end = bounds[i + 1][1] if i + 1 < len(bounds) else len(full)
        piece = full[start:end]
        # The last testament runs straight into the volume's closing matter
        # ("**** END. From Wikipedia, the free encyclopedia …"), which is
        # not part of Benjamin's twelfth chapter.
        cut = re.search(r"\*{2,}\s*END\b|\bFrom Wikipedia, the free", piece)
        if cut:
            piece = piece[:cut.start()]
        out[name] = piece.strip()
    return out


_slice_cache = None


def extract_testament(name):
    global _slice_cache
    if _slice_cache is None:
        _slice_cache = _slices()
    slc = _slice_cache.get(name)
    if not slc:
        return {}

    heads, last = [], 0
    for m in CH_PAT.finditer(slc):
        ch = int(m.group(1))
        if last < ch <= last + 5:
            heads.append((m, ch)); last = ch
        elif ch == last and heads:      # the source labels two chapters alike
            heads.append((m, ch)); last = ch + 1

    chapters, seq = {}, 0
    for i, (m, _ch) in enumerate(heads):
        end = heads[i + 1][0].start() if i + 1 < len(heads) else len(slc)
        verses = _parse_chapter(slc[m.end():end], _numbers(m.group(2)))
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
        old = meta.get("chapters") or {}
        first = next(iter(old.values()), {})
        page = first.get("page", 1)
        pdf = first.get("pdf", PDF_NAME)
        out_ch = {str(c): {"verses": chapters[c], "page": page, "pdf": pdf}
                  for c in sorted(chapters)}
        out = {
            "id": bid, "hebrew": meta["hebrew"], "english": meta["english"],
            "section": meta["section"], "chapter_count": len(out_ch),
            "chapters": out_ch,
        }
        with open(os.path.join(OUT_DIR, f"{bid}.json"), "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
            f.write("\n")
        tv = sum(len(c["verses"]) for c in out_ch.values())
        print(f"{bid:22} {len(out_ch):3} chapters, {tv:4} verses")
        meta["chapter_count"] = len(out_ch)
        meta["chapters"] = {}
        for c in sorted(chapters):
            entry = dict(old.get(str(c), {}))
            entry["pdf"] = pdf
            entry["page"] = page
            meta["chapters"][str(c)] = entry
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("index.json updated")


if __name__ == "__main__":
    main()
