"""Verify Hebrew-roots transliteration accuracy across assets/text/*.json.

This is the *accuracy* counterpart to verify_text.py (which checks the
extracted English against the PDFs). Here we check that the CLAUDE.md /
transliterate.py rules have been applied faithfully and that no Hebrew
transliteration has silently "disappeared" — i.e. lost its divine-name
styling, been corrupted, or been left as the original anglicised word.

The mapping tables are imported directly from transliterate.py, so this
verifier always agrees with the single source of truth used to produce
the data (which itself mirrors CLAUDE.md).

Checks
------
1. Encoding / markup integrity (hard fail)
   - U+FFFD replacement chars (a diacritic that got corrupted)
   - NUL sentinel (\\x00) leaked from the replacement engine
   - <span> / </span> imbalance
   - any span class other than the whitelisted dn / hwhy / fn
   - a divine-name span glued to the middle of a word (stranded markup)

2. Untranslated source names (hard fail)
   - whole-word, case-aware occurrences of unambiguous anglicised names
     that CLAUDE.md says must always become Hebrew (Jesus, Israel, Moses…)

3. Unwrapped divine names (hard fail)
   - the *unambiguous* divine names — Yahuah, Aluahim, Mashiach, Yasharal —
     appearing as plain text outside a <span class="dn">. These are always
     the Most High / the Messiah / the set-apart nation, so an unwrapped
     occurrence is always a styling miss.

4. Ambiguous divine name "Yahusha" (informational only)
   - "Yahusha" doubles as Joshua (a man) and Yahusha the Messiah. We report
     unwrapped occurrences for the record but never auto-wrap them, because
     wrapping Joshua-the-man as a divine name would be wrong.

Usage
-----
    python3 scripts/verify_transliteration.py          # report, exit 1 on fail
    python3 scripts/verify_transliteration.py --fix     # wrap the safe misses
    python3 scripts/verify_transliteration.py <substr>  # limit to matching books
"""
import json
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import transliterate as T  # noqa: E402  (single source of truth for the rules)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXT_DIR = os.path.join(ROOT, "assets", "text")

# ---------------------------------------------------------------------------
# Divine names that are ALWAYS divine, so a bare (unwrapped) occurrence is
# unambiguously a styling miss and is safe to auto-wrap. Imported from
# transliterate.py (which mirrors the CLAUDE.md "Divine Names" table) so the
# verifier and the generator never drift apart. "Yahusha" is excluded there
# because it doubles as Joshua (a man). "YAHUAH" (the spoken form annotating
# the paleo HWHY) is already wrapped at annotation time, so the bare token
# never appears alone.
UNAMBIGUOUS_DIVINE = T.UNAMBIGUOUS_DIVINE

# Ambiguous — reported but never auto-wrapped (Joshua the man vs the Messiah).
AMBIGUOUS_DIVINE = ["Yahusha"]

# Unambiguous anglicised source names that must never survive a pass. These
# are the high-confidence proper nouns from the CLAUDE.md tables — short
# names that collide with English words (Ham, Job, Seth, Reu, Gad, Dan…) and
# the El/Ĕl prefix rule are deliberately excluded to avoid false positives.
SOURCE_NAMES_MUST_CONVERT = [
    "Jesus", "Christ", "Messiah", "Elohim",
    "Israel", "Israelite", "Israelites",
    "Egypt", "Egyptian", "Egyptians",
    "Jerusalem", "Moses", "Aaron",
    "Abraham", "Abram", "Isaac", "Jacob",
]

_DN_SPAN = re.compile(r'<span class="(?:dn|hwhy)">.*?</span>')
_SPAN_OPEN = re.compile(r'<span class="([^"]*)">')
_STRANDED = re.compile(r"[A-Za-zÀ-ɏḀ-ỿ][\'’]?"
                       r'<span class="dn">(?:Al|al|El|el)</span>')


def _strip_spans(text):
    """Return text with dn/hwhy span *contents* removed, so a search only
    sees transliterations that are NOT already wrapped."""
    return _DN_SPAN.sub("", text)


def _iter_verses(only=None):
    for tf in sorted(glob.glob(os.path.join(TEXT_DIR, "*.json"))):
        bid = os.path.basename(tf)[:-5]
        if only and only not in bid:
            continue
        book = json.load(open(tf, encoding="utf-8"))
        for ch in book.get("chapters", {}):
            for v in book["chapters"][ch]["verses"]:
                yield tf, book, bid, ch, v


def scan(only=None):
    """Return a findings dict (no mutation)."""
    f = {
        "fffd": [], "nul": [], "imbalance": [], "bad_class": [],
        "stranded": [], "leftover": {}, "unwrapped": {}, "ambiguous": {},
    }
    for _tf, _book, bid, ch, v in _iter_verses(only):
        t = v["t"]
        loc = f"{bid} {ch}:{v['n']}"
        if "�" in t:
            f["fffd"].append(loc)
        if "\x00" in t:
            f["nul"].append(loc)
        if t.count("<span") != t.count("</span>"):
            f["imbalance"].append(loc)
        for cls in _SPAN_OPEN.findall(t):
            # dn/hwhy mark divine names; fn carries a footnote from the
            # source edition (styled and skipped by speech, like sweep_text
            # and check_render both allow).
            if cls not in ("dn", "hwhy", "fn"):
                f["bad_class"].append((loc, cls))
        if _STRANDED.search(t):
            f["stranded"].append((loc, t[:90]))
        for name in SOURCE_NAMES_MUST_CONVERT:
            if re.search(r"\b" + re.escape(name) + r"\b", t):
                f["leftover"].setdefault(name, []).append(loc)
        bare = _strip_spans(t)
        for dn in UNAMBIGUOUS_DIVINE:
            if re.search(r"\b" + re.escape(dn) + r"\b", bare):
                f["unwrapped"].setdefault(dn, []).append(loc)
        for dn in AMBIGUOUS_DIVINE:
            if re.search(r"\b" + re.escape(dn) + r"\b", bare):
                f["ambiguous"].setdefault(dn, []).append(loc)
    return f


# Wrapping the safe misses reuses the exact pass the generator runs, so a
# --fix here is identical to a fresh transliterate.py run.
wrap_bare_divine = T.wrap_bare_divine


def apply_fix(only=None):
    """Wrap every bare unambiguous divine name in place. Returns (files, verses)."""
    files_changed = 0
    verses_changed = 0
    for tf in sorted(glob.glob(os.path.join(TEXT_DIR, "*.json"))):
        bid = os.path.basename(tf)[:-5]
        if only and only not in bid:
            continue
        book = json.load(open(tf, encoding="utf-8"))
        changed = 0
        for ch in book.get("chapters", {}):
            for v in book["chapters"][ch]["verses"]:
                new = wrap_bare_divine(v["t"])
                if new != v["t"]:
                    v["t"] = new
                    changed += 1
        if changed:
            with open(tf, "w", encoding="utf-8") as fp:
                json.dump(book, fp, ensure_ascii=False, indent=1)
            files_changed += 1
            verses_changed += changed
    return files_changed, verses_changed


def report(f):
    hard = 0

    def section(title, items):
        nonlocal hard
        n = len(items)
        if n:
            hard += n
        print(f"\n{title}: {n}")
        return n

    print("=" * 70)
    print("TRANSLITERATION ACCURACY VERIFICATION")
    print("=" * 70)

    section("U+FFFD corrupted characters", f["fffd"])
    for x in f["fffd"][:10]:
        print("   ", x)
    section("NUL sentinel leaks", f["nul"])
    for x in f["nul"][:10]:
        print("   ", x)
    section("Unbalanced <span> tags", f["imbalance"])
    for x in f["imbalance"][:10]:
        print("   ", x)
    section("Non-dn/hwhy span classes", f["bad_class"])
    for x in f["bad_class"][:10]:
        print("   ", x)
    section("Stranded divine-span mid-word", f["stranded"])
    for x in f["stranded"][:10]:
        print("   ", x)

    left_total = sum(len(v) for v in f["leftover"].values())
    print(f"\nUntranslated source names: {left_total}")
    hard += left_total
    for k in sorted(f["leftover"], key=lambda x: -len(f["leftover"][x])):
        print(f"   {k:14} {len(f['leftover'][k]):>5}   e.g. {f['leftover'][k][:3]}")

    unwrapped_total = sum(len(v) for v in f["unwrapped"].values())
    print(f"\nUnwrapped UNAMBIGUOUS divine names: {unwrapped_total}")
    hard += unwrapped_total
    for k in sorted(f["unwrapped"], key=lambda x: -len(f["unwrapped"][x])):
        print(f"   {k:14} {len(f['unwrapped'][k]):>5}   e.g. {f['unwrapped'][k][:3]}")

    amb_total = sum(len(v) for v in f["ambiguous"].values())
    print(f"\nUnwrapped ambiguous 'Yahusha' (informational, Joshua vs Messiah): "
          f"{amb_total}")
    for k in sorted(f["ambiguous"], key=lambda x: -len(f["ambiguous"][x])):
        print(f"   {k:14} {len(f['ambiguous'][k]):>5}   "
              f"(left as-is; verify context manually if needed)")

    print("\n" + "=" * 70)
    if hard == 0:
        print("RESULT: PASS — no transliteration accuracy issues.")
    else:
        print(f"RESULT: {hard} accuracy issue(s) found. "
              f"Run with --fix to wrap unambiguous divine names.")
    print("=" * 70)
    return hard


def main():
    args = [a for a in sys.argv[1:]]
    do_fix = "--fix" in args
    args = [a for a in args if a != "--fix"]
    only = args[0] if args else None

    if do_fix:
        files, verses = apply_fix(only)
        print(f"Fix: wrapped bare divine names in {verses} verse(s) "
              f"across {files} file(s).\n")

    findings = scan(only)
    hard = report(findings)
    sys.exit(1 if hard else 0)


if __name__ == "__main__":
    main()
