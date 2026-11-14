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

# Words the print carries in the middle or at the end of a verse, set in
# capitals on a line of their own, which the extractor once dropped as a
# page banner. (book, chapter, verse, anchor, words): the words go straight
# after the anchor, verbatim from the source page.
COMPLETES = [
    ("shamoth", "29", 41, "an offering made by fire to",
     ' (<span class="dn">YAHUAH</span>) <span class="hwhy">HWHY</span>–'),
    ("luke", "2", 23, "shall be called qadash (Set Apart) to",
     ' (<span class="dn">YAHUAH</span>) <span class="hwhy">HWHY</span>” –'),
    ("hazon", "17", 5, "BAḆAL THE GREAT,",
     " THE MOTHER OF THE WHORES AND OF THE ABOMINATIONS OF"),
    ("hazon", "19", 16, "a Name written: SOVEREIGN",
     " OF SOVEREIGNS AND MASTER OF"),
    # A line lost where a verse crosses a page or column: the first line of
    # the page after the running header, or one line of a two-column page
    # shuffled into the other column. Verbatim from the source page.
    ("bamidbar", "16", 5, "“Tomorrow morning",
     " (<span class=\"dn\">YAHUAH</span>) <span class=\"hwhy\">HWHY</span> shall make known who is His"),
    ("bereshith", "22", 9, "to the place which",
     " <span class=\"dn\">Aluahim</span> had commanded him and"),
    ("bereshith", "37", 2, "with his brothers.",
     " And the young man was with the sons"),
    ("wayyiqra", "13", 6, "pronounce him clean.",
     " It is a scab and he shall wash his"),
    ("dabarim", "12", 18, "within your gates.",
     " And you shall rejoice before (<span class=\"dn\">YAHUAH</span>) <span class=\"hwhy\">HWHY</span>"),
    ("yahusha", "2", 1, "and Yahriḥo.”",
     " And they went and came to the house"),
    ("yahusha", "10", 34, "to Eḡlon.",
     " And they encamped against it and"),
    ("yahusha", "21", 32, "slayer and",
     " Ḥammoth Dor with its open land and"),
    ("shophetim", "18", 23, "the children of Dan.",
     " So they turned around and said to"),
    ("1shamual", "15", 1, "said to Sha’ul,",
     " “(<span class=\"dn\">YAHUAH</span>) <span class=\"hwhy\">HWHY</span> sent me to anoint you"),
    ("1malakim", "4", 33, "out of the wall.",
     " And he spoke of beasts and of birds"),
    ("1malakim", "7", 40, "and the bowls.",
     " And Ḥiram completed doing all the"),
    ("1malakim", "10", 22, "fleet of Ḥiram.",
     " Once every three years the ships of"),
    ("2malakim", "15", 25, "fifty men of Gil‛aḏ.",
     " So he killed him and reigned in his"),
    ("yashayahu", "33", 6, "and knowledge.",
     " The fear of (<span class=\"dn\">YAHUAH</span>) <span class=\"hwhy\">HWHY</span> – that is His"),
    ("yashayahu", "40", 4, "hill made low.",
     " And the steep ground shall become"),
    ("yirmayahu", "7", 10, "stood before",
     " Me in this house which is called by"),
    ("yirmayahu", "15", 15, "<span class=\"hwhy\">HWHY</span>.",
     " Remember me and visit me and"),
    ("habaqquq", "2", 6, "and say,",
     " ‘Woe to him who increases what is"),
    ("tehillim", "3", 7, "O my <span class=\"dn\">Aluahim</span>!",
     " Because You have smitten all my"),
    ("tehillim", "8", 1, "in all the earth,",
     " You who set Your splendour above"),
    ("tehillim", "31", 11, "a dread to my friends;",
     " Those who see me outside flee from"),
    ("tehillim", "37", 35, "in great power,",
     " And spreading himself"),
    ("tehillim", "55", 4, "pained within me,",
     " And the frights of death"),
    ("tehillim", "69", 5, "my foolishness;",
     " And my guilt has not been hidden"),
    ("tehillim", "81", 14, "at once,",
     " And turn My hand against their"),
    ("tehillim", "86", 4, "the being of Your",
     " servant, For to You, O (<span class=\"dn\">YAHUAH</span>) <span class=\"hwhy\">HWHY</span>, I lift up my being."),
    ("tehillim", "99", 6, "upon His Name.",
     " They called upon (<span class=\"dn\">YAHUAH</span>) <span class=\"hwhy\">HWHY</span>"),
    ("tehillim", "107", 42, "see and rejoice,",
     " And all unrighteousness shuts its"),
    ("tehillim", "109", 15, "<span class=\"hwhy\">HWHY</span>,",
     " And let Him cut off their"),
    ("tehillim", "146", 9, "fatherless and widow,",
     " But the way of the wrong ones"),
    ("mishle", "25", 1, "proverbs of",
     " Shelomoh which the men of"),
    ("mishle", "25", 28, "over his ruach",
     " Is like a broken-down city"),
    ("mishle", "31", 3, "to women,",
     " Nor your ways to wiping"),
    ("ekah", "2", 2, "down to the ground.",
     " He has profaned the reign and its"),
    ("nehemyah", "3", 30, "repaired another section.",
     " After him Meshullam son of Bereḵyah"),
    ("2dibre-hayamim", "21", 2, "the sons of",
     " Yahhoshaphat: Azaryahu and Yahḥi’al and Zaḵaryahu and Azaryahu and Miḵa’al"),
]


# (book, chapter, verse) — a run of verses the source prints with a double
# number, "36(106)", which the extractor did not take for markers, so the
# whole run sits inside one verse. Split at each marker, numbered by the
# number in brackets (2 Esdras 7 continues 106–140 after the restored
# fragment, as the NRSV prints it).
UNMERGES = [
    ("apoc-2esdras", "7", 105),
]
_DOUBLE_MARK = re.compile(r"\s*\b\d{1,3}\((\d{1,3})\)\s*")

# (book, chapter, verse holding the run, heading) — the extractor lost a
# chapter's opening: Enoch 89:1-8 came out as a second copy of 85:1-8, and
# 89:9 swallowed the rest of 85 with all of 86-88 (printed again in their
# own places) and then the true 89:1-9 behind a "Chapter 89" heading. The
# verses after the heading replace the chapter's opening, by their own
# printed numbers.
REBUILDS = [
    ("apoc-eth-enoch", "89", 9, "Chapter 89"),
]
_INLINE_MARK = re.compile(r"\s*\b(\d{1,2})\s+(?=[A-Z‘“'\"])")

# (book, chapter, verse, wrong, right) — a scan misread inside a verse: a
# page header run into the text ("Yoseph 8. Lumpkin"), or a letter read as
# a digit ("1" for I, "0" for O, "50" for So). Checked against the page.
PATCHES = [
    ("apoc-susanna", "1", 59, "your Yoseph 8. Lumpkin own head", "your own head"),
    ("apoc-hermas", "28", 3, "if 1 can be saved", "if I can be saved"),
    ("apoc-jubilees", "35", 20, "the day 1 die", "the day I die"),
    ("apoc-jubilees", "18", 13, "\" 50 that it is said", "\" so that it is said"),
    ("apoc-1esdras", "7", 4, ". 50 with the consent", ". So with the consent"),
    ("apoc-2maccabees", "4", 29, "while 50 stratus left", "while Sostratus left"),
    ("apoc-sirach", "19", 16, "? 50 a word", "? So a word"),
    ("hazon", "20", 4, "hands.And", "hands. And"),
    ("apoc-jubilees", "1", 19, "'0 <", "'O <"),
    ("apoc-jubilees", "1", 20, "mercy, 0 <", "mercy, O <"),
    ("apoc-jubilees", "12", 21, "heart, 0 my", "heart, O my"),
    ("apoc-jubilees", "25", 13, "him, 0 <", "him, O <"),
    ("apoc-eth-enoch", "84", 2, "you, 0 <", "you, O <"),
    ("apoc-eth-enoch", "84", 5, "now, 0 <", "now, O <"),
    ("apoc-eth-enoch", "84", 6, "servant, 0 <", "servant, O <"),
]

# (book, chapter, verse, true ending) — the extractor read past a book's last
# verse into the pages printed after it (a study essay, the "Ten Words" back
# page) and ran them on as part of the verse. Everything after the true
# ending is cut.
TRUNCATES = [
    ("hazon", "22", 21, "qadashiyms (Set Apart Ones). Amĕn."),
    ("2dibre-hayamim", "36", 23, "let him go up!’ ”"),
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
     "There was a man living in Baḇal (Baḇylon) whose name was Yoaqim."),
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

    for bid, cn, n, anchor, words in COMPLETES:
        p, d = load(bid)
        v = next(x for x in d["chapters"][cn]["verses"] if x["n"] == n)
        plain = re.sub(r"<[^>]+>", "", v["t"])
        if re.sub(r"<[^>]+>", "", anchor + words).strip(" –”") in plain:
            continue                          # already whole
        i = v["t"].find(anchor)
        if i < 0:
            print(f"  !! {bid} {cn}:{n}: anchor not found; skipped")
            continue
        i += len(anchor)
        v["t"] = v["t"][:i] + words + v["t"][i:]
        save(p, d)
        changed += 1
        print(f"  complete {bid} {cn}:{n}")

    for bid, cn, n in UNMERGES:
        p, d = load(bid)
        vs = d["chapters"][cn]["verses"]
        v = next(x for x in vs if x["n"] == n)
        parts = _DOUBLE_MARK.split(v["t"])
        if len(parts) < 3:
            continue                          # already split
        v["t"] = parts[0].rstrip()
        at = vs.index(v) + 1
        for num, text in zip(parts[1::2], parts[2::2]):
            vs.insert(at, {"n": int(num), "t": text.strip()})
            at += 1
        save(p, d)
        changed += 1
        print(f"  unmerge {bid} {cn}:{n} -> {len(parts) // 2} verses")

    for bid, cn, n, heading in REBUILDS:
        p, d = load(bid)
        vs = d["chapters"][cn]["verses"]
        v = next(x for x in vs if x["n"] == n)
        i = v["t"].find(heading)
        if i < 0:
            continue                          # already rebuilt
        parts = _INLINE_MARK.split(v["t"][i + len(heading):])
        fresh = {int(k): t.strip() for k, t in zip(parts[1::2], parts[2::2])}
        if sorted(fresh) != list(range(1, n + 1)):
            print(f"  !! {bid} {cn}:{n}: markers {sorted(fresh)}; skipped")
            continue
        for x in vs:
            if x["n"] in fresh:
                x["t"] = fresh[x["n"]]
        save(p, d)
        changed += 1
        print(f"  rebuild {bid} {cn}:1-{n}")

    for bid, cn, n, wrong, right in PATCHES:
        p, d = load(bid)
        v = next(x for x in d["chapters"][cn]["verses"] if x["n"] == n)
        if wrong in v["t"]:
            v["t"] = v["t"].replace(wrong, right, 1)
            save(p, d)
            changed += 1
            print(f"  patch {bid} {cn}:{n}")

    for bid, cn, n, ending in TRUNCATES:
        p, d = load(bid)
        v = next(x for x in d["chapters"][cn]["verses"] if x["n"] == n)
        i = v["t"].find(ending)
        if i < 0:
            print(f"  !! {bid} {cn}:{n}: ending not found; skipped")
            continue
        if v["t"][i + len(ending):].strip():
            v["t"] = v["t"][:i + len(ending)]
            save(p, d)
            changed += 1
            print(f"  truncate {bid} {cn}:{n}")

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
