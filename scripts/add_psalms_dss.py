#!/usr/bin/env python3
"""
add_psalms_dss.py

Builds assets/text/tehillim-dss.json — Psalms 151–174, the psalms the Dead
Sea Scrolls carry beyond the 150 — from

    SCRIPTURE/Psalms-151-174-Dead-Sea-Scrolls.pdf
    ("Psalms 151-174 From the Dead Sea Scrolls", Bethabara Scriptures;
     the translations are in the public domain)

and records the book in assets/index.json, in its own section ("Dead Sea
Scrolls"), numbered as the edition numbers it: chapters 151 to 174, so a
reference reads "Tehillim 155:3" as the 150 psalms do. The index carries
"first_chapter": 151 for the pages that list and turn chapters.

What the script does to the page, in order:

  1. Reads pages 3-12, drops the running head ("Psalms") and the stray
     "Psalmsscroll the" the PDF leaves at the foot of page 3.
  2. Mends the PDF's letter-spaced words ("H e", "a n d", "s t orehouses",
     "@lock" for the fl ligature) against the vocabulary of the rest of the
     canon, so only splits that make a known word are joined.
  3. Drops the Hebrew acrostic letters set beside Psalms 157 and 161 (the
     Besorah does not print them for Tehillim 119 either).
  4. Splits each psalm into its superscription (kept as the chapter's
     unnumbered "intro", like the opening of Jubilees) and its numbered
     verses; a verse begins only where the next number in sequence opens
     a line, so numbers inside the text are never taken for verses.
  5. Transliterates exactly as every other book is transliterated
     (scripts/transliterate.py), after mapping the names the rules do not
     carry to the forms the canon already uses (Jesse -> Yahshai, Hezekiah
     -> Ḥizqiyahu, Cyrus -> Koresh, Belial -> Beliya‛al, Assyria -> Ashshur,
     Adam -> Aḏam).
  6. Turns the scrolls' square brackets into the reader's own marks: a
     restored word becomes <span class="rs">…</span> (set lighter and in
     italic on the page), and an empty bracket — words lost and not
     restored — becomes "…". The reader allows no bare brackets, which
     elsewhere are scan debris.

Run `python3 scripts/sweep_text.py --fix` afterwards, as for every book, so
the house words (qadash, esteem, chesed …) are applied. Safe to re-run.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import transliterate as T  # noqa: E402

PDF_NAME = "Psalms-151-174-Dead-Sea-Scrolls.pdf"
PDF = ROOT / "SCRIPTURE" / PDF_NAME
OUT = ROOT / "assets" / "text" / "tehillim-dss.json"
INDEX = ROOT / "assets" / "index.json"
BOOK_ID = "tehillim-dss"
FIRST, LAST = 151, 174

# Spacing and spelling slips of this PDF, checked against the page and
# against the 151-160 edition of the same psalms.
SPECIALS = [
    ("a f flicted", "afflicted"), ("ful filled", "fulfilled"),
    ("s t orehouses", "storehouses"), ("st orehouses", "storehouses"),
    ("s t ars", "stars"), ("st ars", "stars"), ("Takea vision", "Take a vision"),
    ("thereforeI", "therefore I"), ("Mast ema", "Mastema"),
    ("Gre at", "Great"), ("L i fe", "Life"), ("Li fe", "Life"),
    ("w [ ho ]", "w[ho]"), ("commit ed", "committed"), ("commited", "committed"),
    # The 151-160 edition reads these "there is no Belial" and "raised mist".
    ("for their is no Belial", "for there is no Belial"),
    ("raised a midst", "raised a mist"),
    # letter-spaced runs that took in the word beside them
    ("OZion", "O Zion"), ("father'sdrove", "father's drove"),
    ("father’sdrove", "father’s drove"), ("whod[", "who d["), ("thef[", "the f["),
]
# Names the transliteration tables do not carry, in the canon's own forms.
NAMES = [
    (r"\bJesse\b", "Yahshai"), (r"\bHezekiah\b", "Ḥizqiyahu"),
    (r"\bCyrus\b", "Koresh"), (r"\bBelial\b", "Beliya‛al"),
    (r"\bBe\[lial", "Be[liya‛al"), (r"\bAssyria\b", "Ashshur"),
    (r"\bAdam\b", "Aḏam"), (r"\bjudgements\b", "judgments"),
    (r"\bjudgement\b", "judgment"), (r"\bJudgement\b", "Judgment"),
    (r"\bhalleluyah\b", "HalleluYah"), (r"\bYAHUAH\b", "Yahuah"),
    (r"\bYA\[HUAH", "Ya[huah"), (r"\bYAH\b", "Yah"),
    # "glories" here is the noun (the house renders it splendours); left
    # alone, "glories in" would be read as the verb, boasts in.
    (r"\byour glories in\b", "your splendours in"),
    (r"\bthe Day of Atonement\b", "Yom Kippur"),
    (r"\bGod of Gods\b", "God of gods"), (r"\bIs\]rael\b", "Israel]"),
]
HEBREW = re.compile(r"[֐-׿]")
SHORT = set("a i o ah am an as at be by do go he if in is it me my no of oh "
            "on or so to up us we ye".split())


def vocabulary():
    words = set()
    for p in (ROOT / "assets" / "text").glob("*.json"):
        if p.stem == BOOK_ID:
            continue
        for ch in json.loads(p.read_text(encoding="utf-8"))["chapters"].values():
            for v in ch["verses"]:
                words.update(w.lower() for w in re.findall(r"[A-Za-z]+",
                             re.sub(r"<[^>]+>", " ", v["t"])))
    return words


def page_lines():
    from pypdf import PdfReader
    pages = PdfReader(str(PDF)).pages
    out = []
    for i in range(2, len(pages)):
        t = (pages[i].extract_text() or "").replace("\t", " ")
        t = t.replace("@l", "fl").replace("@i", "fi").replace("@f", "ff")
        t = re.sub(r"Psalmsscroll\s*\nthe\s*$", "", t)
        lines = t.split("\n")
        if lines and lines[0].strip() == "Psalms":
            lines = lines[1:]
        out += [(i + 1, l) for l in lines]
    return out


def segment(w, vocab):
    """Split a run of letters into known words, fewest words first: the
    PDF letter-spaces a word and the one beside it alike ("t h e e a r t h"
    is "the earth", "a f a i t h f u l" is "a faithful")."""
    low, best = w.lower(), {0: []}
    for i in range(len(low)):
        if i not in best:
            continue
        for j in range(len(low), i, -1):
            if low[i:j] in vocab and (j not in best or len(best[j]) > len(best[i]) + 1):
                best[j] = best[i] + [w[i:j]]
    return " ".join(best[len(low)]) if len(low) in best else w


def mend(s, vocab):
    s = re.sub(r"\s+", " ", s)
    # letter-spaced runs: "a n d", "Y o u" — joined, then split into known
    # words where the run took in its neighbour too.
    def run(m):
        w = m.group(0).replace(" ", "")
        return w if w.lower() in vocab else segment(w, vocab)
    s = re.sub(r"\b(?:[A-Za-z] ){2,}[A-Za-z]\b", run, s)
    for a, b in SPECIALS:
        s = s.replace(a, b)
    # one stray letter split from the rest of its word: "H e", "o r", "I s"
    def join(m):
        a, b = m.group(1), m.group(2)
        w = (a + b).lower()
        lone = len(b) == 1 or b.lower() not in vocab
        if w in vocab and (lone or a not in "aAIO"):
            return a + b
        return m.group(0)
    s = re.sub(r"\b([A-Za-z]) ([a-z]+)\b", join, s)
    # a word the PDF kerned apart ("so ul", "Zi on"): rejoined when only
    # the whole is a word
    def pair(m):
        a, b = m.group(1), m.group(2)
        if (a + b).lower() in vocab and (a.lower() not in vocab or b.lower() not in vocab):
            return a + b
        return m.group(0)
    s = re.sub(r"\b([A-Za-z]{1,3}) ([a-z]{1,4})\b", pair, s)
    s = re.sub(r"\s+([,;:.?!])", r"\1", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse(vocab):
    psalms, cur = {}, None
    want_ch, last_v, buf, page_of = FIRST, 0, [], {}
    def flush():
        if cur is None or not buf:
            return
        text = " ".join(buf)
        text = re.sub(r"(\w)- (\w)", r"\1\2", text)          # under- standing
        if last_v == 0:
            psalms[cur]["intro"].append(text)
        else:
            psalms[cur]["verses"].append([last_v, text])
    for page, raw in page_lines():
        line = HEBREW.sub("", raw).rstrip()
        bare = line.strip()
        if bare == str(want_ch):
            flush(); buf = []
            cur, last_v = want_ch, 0
            psalms[cur] = {"intro": [], "verses": []}
            page_of[cur] = page
            want_ch += 1
            continue
        if cur is None or not bare:
            continue
        m = re.match(r"^(\d{1,2})\s+(.*)$", bare)
        if m and int(m.group(1)) == last_v + 1 and not raw.startswith(" "):
            flush(); buf = [m.group(2)]
            last_v += 1
            continue
        buf.append(bare)
    flush()
    assert sorted(psalms) == list(range(FIRST, LAST + 1)), sorted(psalms)
    return psalms, page_of


def brackets(s, vocab):
    """Square brackets -> restored spans and gaps, balanced per verse: a
    restoration can run across a verse number, so a "]" with no "[" before
    it closes one opened in the verse before, and a "[" left open runs on."""
    depth = opens = 0
    for c in s:
        if c == "[":
            depth += 1
        elif c == "]":
            if depth:
                depth -= 1
            else:
                opens += 1
    s = "[" * opens + s + "]" * depth
    # "Whi [ch", "w [ho": a restoration completing the word before it
    s = re.sub(r"\b([A-Za-z]+) \[ ?([a-z])",
               lambda m: m.group(0) if m.group(1).lower() in vocab
               else m.group(1) + "[" + m.group(2), s)
    def rep(m):
        inner = m.group(1).strip()
        if not re.search(r"[A-Za-zḀ-ỿ]", inner):
            return " … "
        return '<span class="rs">' + inner + "</span>"
    s = re.sub(r"\[([^\[\]]*)\]", rep, s)
    s = re.sub(r"\s*…\s*(?:…\s*)*", " … ", s)
    s = re.sub(r"…\s*[.,;:]+", "…", s)
    s = re.sub(r"\s+([,;:.?!])", r"\1", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"^…\s*", "… ", s)
    return s


def translit(s, rules):
    for a, b in NAMES:
        s = re.sub(a, b, s)
    s = T.transliterate(s, rules)
    s = T.repair_stranded_yisra(s)
    s = T.yi_ye_to_yah(s)
    s = T.el_suffix_to_al(s)
    s = T.annotate_hwhy(s)
    s = T.wrap_bare_divine(s)
    return s


def main():
    vocab = vocabulary()
    # ...and every word this PDF prints whole (three letters or more), for
    # the English the canon has since rendered in Hebrew (glory, mercy …).
    for _, line in page_lines():
        vocab.update(w.lower() for w in re.findall(r"(?<![A-Za-z] )\b[A-Za-z]{3,}\b(?! [A-Za-z]\b)", line))
    # Short words only from English itself: the canon's own text carries
    # scan fragments ("ul", "r") that would otherwise pass for words.
    vocab = {w for w in vocab if len(w) > 2} | SHORT
    rules = T.build_replacements(T.DIVINE, T.PEOPLE_PATRIARCHS, T.PEOPLE_LEADERS,
                                 T.PEOPLE_J_NAMES, T.PEOPLE_TRIBES, T.PLACES, T.TERMS)
    psalms, page_of = parse(vocab)
    chapters = {}
    for n in range(FIRST, LAST + 1):
        p = psalms[n]
        ch = {"verses": []}
        if p["intro"]:
            ch["intro"] = brackets(translit(mend(" ".join(p["intro"]), vocab), rules), vocab)
        for vn, text in p["verses"]:
            t = brackets(translit(mend(text, vocab), rules), vocab)
            ch["verses"].append({"n": vn, "t": t})
        chapters[str(n)] = ch
    data = {"id": BOOK_ID, "hebrew": "TEHILLIM 151–174",
            "english": "Psalms 151–174, Dead Sea Scrolls",
            "section": "Dead Sea Scrolls", "chapter_count": len(chapters),
            "first_chapter": FIRST, "chapters": chapters}
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    entry = {k: data[k] for k in ("id", "hebrew", "english", "section",
                                  "chapter_count", "first_chapter")}
    entry["chapters"] = {str(n): {"pdf": PDF_NAME, "page": page_of[n], "printed": page_of[n]}
                         for n in range(FIRST, LAST + 1)}
    idx["books"] = [b for b in idx["books"] if b["id"] != BOOK_ID] + [entry]
    INDEX.write_text(json.dumps(idx, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    nv = sum(len(c["verses"]) for c in chapters.values())
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(chapters)} psalms, {nv} verses, "
          f"{sum(1 for c in chapters.values() if 'intro' in c)} superscriptions")


if __name__ == "__main__":
    main()
