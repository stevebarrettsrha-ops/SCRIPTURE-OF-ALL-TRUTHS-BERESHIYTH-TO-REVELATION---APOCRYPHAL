#!/usr/bin/env python3
"""
sweep_text.py

Sweeps every book in assets/text/ and reports — or repairs — the scars the
PDF extraction leaves behind, so what reaches the reader is clean.

Checks (all 104 books, every chapter, every verse):

  1. inline verse markers   "[19]" / "[19J" printed inside a sentence.
     With --fix these become real verses wherever the numbering allows it
     (the marker's number must continue the chapter's sequence and not
     collide with an existing verse); otherwise the marker is removed.
  2. word forms             the JOINS / SPLITS / TYPOS tables in
     assets/words.js — the one place a word's correct form is recorded.
     The tables are read straight out of the JavaScript so the site and
     this script can never disagree.
  3. markup                 only <span class="dn"> and <span class="hwhy">
     are allowed, they must be balanced, and no stray angle bracket may
     survive.
  4. structure              chapter counts match assets/index.json, verse
     numbers are unique and ascending, nothing is empty.
  5. whitespace             doubled spaces, space before punctuation,
     leading/trailing space.
  6. speech coverage        how much of the Hebrew-roots vocabulary the
     lexicon in assets/pronunciation.js actually covers.

Usage:
    python3 scripts/sweep_text.py            # report only (exit 1 if issues)
    python3 scripts/sweep_text.py --fix      # repair, then report
    python3 scripts/sweep_text.py --verbose  # show every change / issue
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT_DIR = ROOT / "assets" / "text"
INDEX_PATH = ROOT / "assets" / "index.json"
WORDS_JS = ROOT / "assets" / "words.js"
PRON_JS = ROOT / "assets" / "pronunciation.js"

TAG = re.compile(r"<[^>]+>")
ALLOWED_TAG = re.compile(r'<span class="(?:dn|hwhy)">|</span>')
VERSE_MARKER = re.compile(r"\[\s*(\d{1,3})\s*[J\]\)]\s*")
# The double numbering some editions print for the Shepherd of Hermas —
# "10[76]:2" — is a cross-reference, not part of the reading.
DUAL_REFERENCE = re.compile(r"\b\d{1,3}\s*\[\s*\d{1,3}\s*[J\]\)]\s*:\s*\d{1,3}\s*")
WORD = re.compile(r"[A-Za-zÀ-ɏḀ-ỿ'’‛ʻʼ]+")


# ----------------------------------------------------------------- tables
def js_table(path, name):
    """Read a `var NAME = { … };` object literal out of a JS file.

    The tables in words.js / pronunciation.js are written as plain JSON so
    both JavaScript and Python can use them without a second copy.
    """
    src = path.read_text(encoding="utf-8")
    m = re.search(r"var\s+" + name + r"\s*=\s*(\{.*?\n\s*\});", src, re.S)
    if not m:
        raise SystemExit(f"could not find `var {name}` in {path.name}")
    body = m.group(1)
    body = re.sub(r"^\s*//.*$", "", body, flags=re.M)   # strip comments
    body = re.sub(r",(\s*\})", r"\1", body)             # trailing commas
    return json.loads(body)


JOINS = js_table(WORDS_JS, "JOINS")
SPLITS = js_table(WORDS_JS, "SPLITS")
TYPOS = js_table(WORDS_JS, "TYPOS")
LEXICON = js_table(PRON_JS, "LEXICON")


def _alt(keys):
    if not keys:
        return None
    ordered = sorted(keys, key=len, reverse=True)
    return re.compile(r"\b(" + "|".join(re.escape(k) for k in ordered) + r")\b",
                      re.I)


JOIN_RE = _alt(list(JOINS))
SPLIT_RE = _alt(list(SPLITS))
TYPO_RE = _alt(list(TYPOS))


def apply_case(sample, replacement):
    if sample[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def repair_plain(text, log=None, where=""):
    """Apply the word tables to a run of plain text (mirrors words.js)."""
    def sub(table):
        def go(m):
            key = re.sub(r"\s+", " ", m.group(0).lower())
            rep = table.get(key)
            if rep is None:
                return m.group(0)
            out = apply_case(m.group(0), rep)
            if log is not None and out != m.group(0):
                log.append((where, m.group(0), out))
            return out
        return go

    s = text
    if JOIN_RE:
        s = JOIN_RE.sub(sub(JOINS), s)
    if SPLIT_RE:
        s = SPLIT_RE.sub(sub(SPLITS), s)
    if TYPO_RE:
        s = TYPO_RE.sub(sub(TYPOS), s)
    s = DUAL_REFERENCE.sub(" ", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    # Close up a space before punctuation, but never inside an ellipsis.
    s = re.sub(r"(^|[^.…])[ \t]+([,;:!?]|\.(?![.…]))", r"\1\2", s)
    return s


def repair(text, log=None, where=""):
    """Apply the word tables outside of markup, never inside a tag."""
    if "<" not in text:
        return repair_plain(text, log, where)
    out, i = [], 0
    for m in TAG.finditer(text):
        out.append(repair_plain(text[i:m.start()], log, where))
        out.append(m.group(0))
        i = m.end()
    out.append(repair_plain(text[i:], log, where))
    return "".join(out)


def balanced(text):
    return len(re.findall(r"<span\b", text)) == len(re.findall(r"</span>", text))


# ------------------------------------------------------- verse marker fix
def split_markers(verses, log=None, where=""):
    """Turn inline "[19J" markers into real verses.

    A marker is promoted when its number is greater than the verse it sits
    in, ascending within that verse, and does not collide with a verse that
    already exists in the chapter. Anything else is simply removed, since a
    number printed mid-sentence is never part of the reading.
    """
    existing = {v["n"] for v in verses}
    out = []
    for idx, v in enumerate(verses):
        text = v["t"]
        marks = list(VERSE_MARKER.finditer(text))
        if not marks:
            out.append(v)
            continue

        following = [w["n"] for w in verses[idx + 1:]]
        ceiling = following[0] if following else 10 ** 6
        pieces, numbers, last_end, prev = [], [], 0, v["n"]
        ok = True
        for m in marks:
            n = int(m.group(1))
            if not (prev < n < ceiling) or n in existing:
                ok = False
                break
            pieces.append(text[last_end:m.start()])
            numbers.append(n)
            last_end = m.end()
            prev = n
        if ok and pieces:
            pieces.append(text[last_end:])
            if all(balanced(p) for p in pieces) and all(p.strip() for p in pieces):
                out.append({"n": v["n"], "t": pieces[0].strip()})
                for n, body in zip(numbers, pieces[1:]):
                    existing.add(n)
                    out.append({"n": n, "t": body.strip()})
                if log is not None:
                    log.append((where, f"verse {v['n']}",
                                "split into " + ", ".join(str(n) for n in [v["n"]] + numbers)))
                continue
        # Could not promote them — drop the markers so the prose reads cleanly.
        cleaned = VERSE_MARKER.sub(" ", text)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip()
        if log is not None:
            log.append((where, f"verse {v['n']}", "stripped inline marker(s)"))
        out.append({"n": v["n"], "t": cleaned})
    return out


# ------------------------------------------------------------ speech check
AYIN = re.compile(r"[‘’‚‛ʻʼʹ׳'`´]")


# An English possessive or contraction ("man’s", "isn’t") is not a Hebrew
# ayin, so it must not count a word as set-apart vocabulary.
ENGLISH_APOSTROPHE = re.compile(r"[‘’'`´](?:s|t|d|ll|ve|re|m)?$", re.I)


def is_hebrewish(w):
    if any(unicodedata.category(c) == "Mn"
           for c in unicodedata.normalize("NFD", w)):
        return True
    stripped = ENGLISH_APOSTROPHE.sub("", w)
    return bool(AYIN.search(stripped))


def in_lexicon(key):
    """Mirror of BesorahPron.wordFor's lookup: entry, possessive, the
    "ha-" article, or a Hebrew plural of a known stem."""
    if key in LEXICON:
        return True
    if key.endswith("s") and key[:-1] in LEXICON:
        return True
    if len(key) > 4 and key.startswith("ha") and key[2:] in LEXICON:
        return True
    for suf in ("im", "oth", "ot"):
        if len(key) > len(suf) + 2 and key.endswith(suf) and key[:-len(suf)] in LEXICON:
            return True
    return False


def pron_key(w):
    s = unicodedata.normalize("NFD", w)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return AYIN.sub("", s).lower()


def main():
    fix = "--fix" in sys.argv
    verbose = "--verbose" in sys.argv

    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    meta = {b["id"]: b for b in index["books"]}

    issues = {"markers": [], "markup": [], "structure": [], "whitespace": []}
    changes = []
    marker_count = 0
    verse_total = 0
    files = sorted(TEXT_DIR.glob("*.json"))

    for path in files:
        bid = path.stem
        data = json.loads(path.read_text(encoding="utf-8"))
        touched = False

        info = meta.get(bid)
        if not info:
            issues["structure"].append(f"{bid}: not listed in index.json")
        elif info["chapter_count"] != len(data["chapters"]):
            issues["structure"].append(
                f"{bid}: index says {info['chapter_count']} chapters, "
                f"text has {len(data['chapters'])}")

        for cn in sorted(data["chapters"], key=lambda x: int(x)):
            ch = data["chapters"][cn]
            verses = ch.get("verses", [])
            where = f"{bid} {cn}"
            if not verses:
                issues["structure"].append(f"{where}: chapter has no verses")
                continue

            marks_here = sum(len(VERSE_MARKER.findall(v["t"])) for v in verses)
            if marks_here:
                marker_count += marks_here
                issues["markers"].append(f"{where}: {marks_here} inline verse marker(s)")
                if fix:
                    verses = split_markers(verses, changes, where)
                    touched = True

            new_verses = []
            for v in verses:
                verse_total += 1
                t = v["t"]
                spot = f"{where}:{v['n']}"

                for tag in TAG.findall(t):
                    if not ALLOWED_TAG.fullmatch(tag):
                        issues["markup"].append(f"{spot}: unexpected tag {tag!r}")
                if not balanced(t):
                    issues["markup"].append(f"{spot}: unbalanced <span>")
                bare = TAG.sub("", t)
                if "<" in bare or ">" in bare:
                    issues["markup"].append(f"{spot}: stray angle bracket")

                repaired = repair(t, changes, spot)
                if re.search(r"  +", TAG.sub("", repaired)):
                    issues["whitespace"].append(f"{spot}: doubled space")
                if re.search(r"[^.…]\s([,;:!?]|\.(?![.…]))(?=\s|$)",
                             TAG.sub("", repaired)):
                    issues["whitespace"].append(f"{spot}: space before punctuation")
                if repaired != repaired.strip():
                    issues["whitespace"].append(f"{spot}: leading/trailing space")
                    repaired = repaired.strip()
                if not repaired.strip():
                    issues["structure"].append(f"{spot}: empty verse")
                if repaired != t:
                    touched = True
                new_verses.append({"n": v["n"], "t": repaired}
                                  if fix else {"n": v["n"], "t": t})

            ns = [v["n"] for v in new_verses]
            if len(set(ns)) != len(ns):
                issues["structure"].append(f"{where}: duplicate verse numbers")
            if ns != sorted(ns):
                issues["structure"].append(f"{where}: verse numbers out of order")

            if fix:
                ch["verses"] = new_verses

        if fix and touched:
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=1) + "\n",
                encoding="utf-8")

    # ---- speech coverage ------------------------------------------------
    from collections import Counter
    freq = Counter()
    hebrew_forms = {}      # key -> True when the printed form carries a
    for path in files:     #        Hebrew mark (diacritic or ayin)
        data = json.loads(path.read_text(encoding="utf-8"))
        for ch in data["chapters"].values():
            for v in ch.get("verses", []):
                for w in WORD.findall(TAG.sub("", v["t"])):
                    k = pron_key(w)
                    if not k:
                        continue
                    freq[k] += 1
                    if k not in hebrew_forms:
                        hebrew_forms[k] = is_hebrewish(w)
    hebrewish = sum(n for k, n in freq.items()
                    if hebrew_forms.get(k) or in_lexicon(k))
    covered = sum(n for k, n in freq.items() if in_lexicon(k))
    top_missing = [(k, n) for k, n in freq.most_common(1500)
                   if hebrew_forms.get(k) and not in_lexicon(k)][:15]

    # ---- report ---------------------------------------------------------
    print(f"Swept {len(files)} books · {verse_total} verses\n")
    labels = {
        "markers": "inline verse markers",
        "markup": "markup problems",
        "structure": "structural problems",
        "whitespace": "whitespace problems",
    }
    total = 0
    for key, label in labels.items():
        rows = issues[key]
        total += len(rows)
        print(f"  {label:24s} {len(rows)}")
        if rows and (verbose or len(rows) <= 12):
            for r in rows[:40]:
                print(f"      {r}")
    pct = (100.0 * covered / hebrewish) if hebrewish else 0.0
    print(f"\n  lexicon entries          {len(LEXICON)}")
    print(f"  set-apart vocabulary     {hebrewish} spoken words, "
          f"{covered} from the lexicon ({pct:.1f}%)")
    if top_missing:
        print("  most common words still using the fallback rules:")
        for k, n in top_missing:
            print(f"      {k} ({n}×)")

    if fix:
        print(f"\nRepairs applied: {len(changes)}")
        seen = {}
        for where, before, after in changes:
            seen.setdefault((before, after), []).append(where)
        for (before, after), spots in sorted(seen.items(), key=lambda x: -len(x[1])):
            head = ", ".join(spots[:3]) + ("…" if len(spots) > 3 else "")
            print(f"  {before!r} -> {after!r}  ×{len(spots)}  ({head})")
    elif total:
        print("\nRun with --fix to repair what can be repaired automatically.")

    return 1 if (total and not fix) else 0


if __name__ == "__main__":
    sys.exit(main())
