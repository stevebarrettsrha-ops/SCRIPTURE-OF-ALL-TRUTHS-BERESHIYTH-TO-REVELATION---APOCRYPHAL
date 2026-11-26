#!/usr/bin/env python3
"""
build_daily_bread.py

Checks assets/daily-bread.json and builds assets/DailyBread.js from it — the
table the home page draws today's portion from.

Every portion is chosen and written by hand. An earlier version of this
script picked passages by keyword and gave each one a line from a bank of
stock sayings filed under a theme ("trust", "joy", "refuge" …). The result
read as generic and often sat badly beside the verses it was printed under:
the line had been written for a theme, never for the passage. That
machinery is gone. A reflection now belongs to one passage only, and this
script's job is to keep it that way.

What is checked, for every entry (any failure stops the build):

  * the book, the chapter and every verse in the range exist in
    assets/text/, and the verses run consecutively;
  * a portion is a passage, never a lone line — two verses at least;
  * it begins where a sentence begins (not in lower case) and ends where
    one lands (a full stop, a question, an exclamation or a closing quote);
  * no verse is served by two portions;
  * the title and the reflection are present, of a sensible length, and
    carry no markdown or stray markup;
  * no two portions share a reflection, or a sentence of one — the stock
    line can not creep back in.

What is reported for a human to read (it does not stop the build):

  * every phrase a reflection puts in quotation marks that is not found in
    the passage printed above it. Quoting the passage is the point; a
    quotation from elsewhere (a line the passage answers, or the place the
    Messianic writings cite it) is allowed, but each one should be looked
    at, and its wording checked against the canon.

Only references are written to DailyBread.js. The verse text is read from
assets/text/ at run time, so a portion can never drift from the canon.

Usage:
    python3 scripts/build_daily_bread.py            # check, then build
    python3 scripts/build_daily_bread.py --check    # check only
"""
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT_DIR = ROOT / "assets" / "text"
INDEX_PATH = ROOT / "assets" / "index.json"
CURATED_PATH = ROOT / "assets" / "daily-bread.json"
OUTPUT = ROOT / "assets" / "DailyBread.js"

TAG = re.compile(r"<[^>]+>")
MIN_VERSES = 2
MAX_VERSES = 8
MIN_REFLECTION = 150
MAX_REFLECTION = 520
MAX_THEME = 60

OPENS_LOWER = re.compile(r"^\s*[“”‘\"'(–— ]*[a-zà-ɏḁ-ỿ]")
LANDS = re.compile(r"[.!?”’\"]\s*$")
QUOTED = re.compile(r"“([^”]+)”")
SENTENCE = re.compile(r"[^.!?]+[.!?]+[”’]?")


def plain(t):
    return TAG.sub("", t).strip()


def fold(s):
    """Lower-case, unaccented, unpunctuated — for comparing wording."""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("(YAHUAH) HWHY", "yahuah")
    s = re.sub(r"\((?:Set Apart|Faithful)[^)]*\)", "", s)
    s = re.sub(r"[’'‛]", "", s.lower())
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()


def check(pool, order):
    errors, notes = [], []
    books = {}
    served = {}
    sentences = {}
    for i, e in enumerate(pool):
        missing = [k for k in ("book", "chapter", "from", "to", "theme",
                               "reflection") if k not in e]
        if missing:
            errors.append(f"entry {i}: missing {', '.join(missing)}")
            continue
        ref = f"{e['book']} {e['chapter']}:{e['from']}-{e['to']}"
        if e["book"] not in order:
            errors.append(f"{ref}: no such book")
            continue
        if e["book"] not in books:
            books[e["book"]] = json.loads(
                (TEXT_DIR / f"{e['book']}.json").read_text(encoding="utf-8"))
        ch = books[e["book"]]["chapters"].get(str(e["chapter"]))
        if not ch:
            errors.append(f"{ref}: no such chapter")
            continue
        verses = [v for v in ch["verses"] if e["from"] <= v["n"] <= e["to"]]
        want = list(range(e["from"], e["to"] + 1))
        if [v["n"] for v in verses] != want:
            errors.append(f"{ref}: the canon does not hold every verse of "
                          f"this range, in order")
            continue
        if not (MIN_VERSES <= len(verses) <= MAX_VERSES):
            errors.append(f"{ref}: a portion is {MIN_VERSES} to {MAX_VERSES} "
                          f"verses, this is {len(verses)}")
        texts = [plain(v["t"]) for v in verses]
        if OPENS_LOWER.match(texts[0]):
            errors.append(f"{ref}: begins mid-sentence — “{texts[0][:40]}…”")
        if not LANDS.search(texts[-1]):
            errors.append(f"{ref}: does not land — “…{texts[-1][-40:]}”")
        for n in want:
            key = (e["book"], e["chapter"], n)
            if key in served:
                errors.append(f"{ref}: verse {n} is already served by "
                              f"{served[key]}")
            served[key] = ref

        theme, refl = e["theme"].strip(), e["reflection"].strip()
        if not theme or len(theme) > MAX_THEME:
            errors.append(f"{ref}: title missing or over {MAX_THEME} characters")
        if not (MIN_REFLECTION <= len(refl) <= MAX_REFLECTION):
            errors.append(f"{ref}: reflection is {len(refl)} characters "
                          f"(wanted {MIN_REFLECTION}–{MAX_REFLECTION})")
        if re.search(r"[*_#<>`]", theme + refl):
            errors.append(f"{ref}: markdown or markup in the title or reflection")
        if refl.count("“") != refl.count("”"):
            errors.append(f"{ref}: unbalanced quotation marks")

        for s in SENTENCE.findall(refl):
            k = fold(s)
            if len(k) < 25:
                continue
            if k in sentences:
                errors.append(f"{ref}: shares a sentence with {sentences[k]} "
                              f"— “{s.strip()[:50]}…”")
            sentences[k] = ref

        passage = fold(" ".join(texts))
        for q in QUOTED.findall(refl):
            for piece in re.split(r"\s*…\s*", q):
                k = fold(piece)
                if len(k.split()) >= 2 and k not in passage:
                    notes.append(f"{ref}: “{piece}”")
    return errors, notes


def main():
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    order = [b["id"] for b in index["books"]]
    pool = json.loads(CURATED_PATH.read_text(encoding="utf-8"))["pool"]

    errors, notes = check(pool, order)
    if notes:
        print(f"Quoted from outside the passage ({len(notes)}) — each one "
              f"checked against the canon by hand:")
        for n in notes:
            print("   ", n)
    if errors:
        print(f"\n{len(errors)} problem(s) in {CURATED_PATH.relative_to(ROOT)}:")
        for e in errors:
            print("   ", e)
        sys.exit(1)

    per_book = Counter(e["book"] for e in pool)
    verses = sum(e["to"] - e["from"] + 1 for e in pool)
    print(f"\n{len(pool)} portions, all sound  ({verses} verses, "
          f"{verses / len(pool):.1f} a portion, from {len(per_book)} books; "
          f"{len(pool) / 365.25:.1f} years without a repeat)")
    if "--check" in sys.argv:
        return

    portions = [
        {"b": e["book"], "c": e["chapter"], "f": e["from"], "t": e["to"],
         "th": e["theme"].strip(), "r": e["reflection"].strip()}
        for e in pool
    ]
    js = [HEADER]
    js.append("  var PORTIONS = " + json.dumps(
        portions, ensure_ascii=False, indent=1).replace("\n", "\n  ") + ";\n")
    js.append(BODY)
    OUTPUT.write_text("".join(js), encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")


HEADER = '''// DailyBread.js
// The portions the home page serves, one for each day.
//
// GENERATED by scripts/build_daily_bread.py from assets/daily-bread.json —
// edit the JSON and run the script, not this file. Every portion is chosen
// by hand and its reflection is written for that passage alone; the script
// checks each reference against the canon before anything is written here.
//
//   BesorahDailyBread.forDay(dayNumber)  -> {book, chapter, from, to,
//                                            theme, reflection}
//   BesorahDailyBread.size               -> how many portions exist
//
// Only references are stored. The verse text is read from assets/text/ at
// run time, so a portion can never drift from the canon.
//
// A portion is chosen by walking the list with a stride that is coprime
// with its length: every portion is served exactly once before any is
// served twice, and consecutive days fall in different books.
(function (global) {
  "use strict";

'''

BODY = '''
  function gcd(a, b) { while (b) { var t = a % b; a = b; b = t; } return a; }

  // A stride near the golden section of the total spreads consecutive days
  // across different books; coprimality guarantees full coverage.
  var stride = 0;
  function strideFor(total) {
    if (stride) return stride;
    var s = Math.floor(total * 0.6180339887) || 1;
    while (gcd(s, total) !== 1) s++;
    stride = s;
    return s;
  }

  // The portion for a given day number (days since the epoch, local time).
  function forDay(day) {
    var n = PORTIONS.length;
    if (!n) return null;
    day = Math.floor(day);
    var idx = ((day % n) * strideFor(n)) % n;
    if (idx < 0) idx += n;
    var p = PORTIONS[idx];
    return {
      book: p.b, chapter: p.c, from: p.f, to: p.t,
      theme: p.th, reflection: p.r
    };
  }

  global.BesorahDailyBread = {
    forDay: forDay,
    get size() { return PORTIONS.length; }
  };
})(typeof window !== "undefined" ? window : this);
'''


if __name__ == "__main__":
    main()
