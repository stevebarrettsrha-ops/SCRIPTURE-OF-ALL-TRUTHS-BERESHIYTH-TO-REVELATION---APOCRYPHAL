#!/usr/bin/env python3
"""
fix_broken_words.py

Repairs PDF-extraction artifacts where a single word was split into
two pieces by a column-edge line break (e.g. "moun tains" -> "mountains").
Operates on the per-book JSON files in assets/text/.

Strategy:
  1. Hyphen-line-break:  "moun- tains" or "<word>-<lowercase>" -> drop hyphen, join.
  2. Soft-wrap:          For lower/Title-case "<a> <b>" pairs, join when
                         the *joined* form is a real English word AND at
                         least one of the parts is not.

The English check uses the `english-words` (web2) wordlist, with simple
suffix-stripping so that plurals/inflections (which web2 lacks) still
register as valid words.

Usage:
    pip install english-words
    python3 scripts/fix_broken_words.py
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT_DIR = ROOT / "assets" / "text"

try:
    from english_words import get_english_words_set
except ImportError:
    print("Need the `english-words` package. Run: pip install english-words", file=sys.stderr)
    sys.exit(1)

WORDS = get_english_words_set(["web2"], lower=True)
# Hand-augment with high-frequency inflections / common forms that web2 misses.
WORDS |= {
    "mountains", "shamayim", "yahuah", "yahusha", "aluahim",
    "theophilos",  # Greek dedicatee in Luke / Acts ("Theo philos" -> "Theophilos")
}

# Stoplist of short common words (prepositions, articles, auxiliaries,
# pronouns) that we must never strip out of a context like "Aram is …" or
# "to be paid" by gluing them onto a neighbour. If either fragment of a
# candidate pair appears here, the merge is refused — these words almost
# always stand alone, and gluing them produces nonsense even when the
# joined form happens to be in the dictionary (e.g. "tamarin" the monkey).
STOP_GLUE = {
    "a", "an", "the",
    "i", "we", "you", "he", "she", "it", "they", "me", "us", "him", "her", "them",
    "my", "your", "his", "its", "our", "their",
    "is", "am", "are", "was", "were", "be", "been", "being",
    "do", "did", "does", "done", "doing",
    "have", "has", "had",
    "will", "would", "shall", "should", "can", "could", "may", "might", "must",
    "of", "to", "in", "on", "at", "by", "for", "from", "with", "into", "onto",
    "as", "if", "or", "and", "but", "nor", "so", "yet", "than", "then",
    "out", "off", "up", "down", "over", "under", "above", "below",
    "no", "not", "yes", "all", "any", "each", "such", "same",
    "this", "that", "these", "those", "there", "here",
    "who", "whom", "whose", "what", "when", "where", "why", "how", "which",
    "law", "old", "new", "way", "one", "two",   # frequent in compound traps
}


def is_english(word: str) -> bool:
    """True if `word` (case-insensitive) plausibly exists as an English
    base form or a simple inflection of one."""
    w = word.lower()
    if not w.isalpha():
        return False
    if w in WORDS:
        return True
    # Strip common inflectional suffixes and recheck.
    for suf in ("ies", "ing", "ied", "ed", "es", "er", "ly", "s"):
        if w.endswith(suf) and len(w) > len(suf) + 1:
            stem = w[: -len(suf)]
            if stem in WORDS:
                return True
            # Special: -ies / -ied usually means stem+y (e.g. "cities" -> "city")
            if suf in ("ies", "ied") and (stem + "y") in WORDS:
                return True
            # Special: -ing / -ed on verbs ending in 'e' that was dropped
            # (e.g. "making" -> "mak"+"ing" -> "make"; "quaked" -> "quak"+"ed" -> "quake")
            if suf in ("ing", "ed") and (stem + "e") in WORDS:
                return True
            # Special: doubled consonant -ed / -ing (e.g. "running" -> "run")
            if suf in ("ing", "ed") and len(stem) >= 2 and stem[-1] == stem[-2]:
                if stem[:-1] in WORDS:
                    return True
    return False


# Regions of text wrapped in HTML tags should be left untouched.
TAG_PAT = re.compile(r"<[^>]+>")


def split_protected(text):
    """Yield (kind, segment) where kind is 'tag' or 'text'. Tag segments
    are returned untouched; text segments are eligible for fixes."""
    pos = 0
    for m in TAG_PAT.finditer(text):
        if m.start() > pos:
            yield ("text", text[pos:m.start()])
        yield ("tag", m.group(0))
        pos = m.end()
    if pos < len(text):
        yield ("text", text[pos:])


# Hyphen-line-break: "<letters>- <lowercase letters>" -> joined, hyphen dropped.
HYPHEN_BREAK_PAT = re.compile(r"\b([A-Za-z]{2,})-\s+([a-z][a-z]{1,15})\b")

# Token splitter: alphabetic word OR run of non-letters (kept verbatim).
# We rebuild the text from tokens, so word/separator structure is preserved.
TOKEN_PAT = re.compile(r"[A-Za-z]+|[^A-Za-z]+")


def _refuse(a, b):
    """Refuse to merge if either fragment is a stoplist word, since those
    almost always stand alone in real text. This blocks bogus joins like
    'Aram is' -> 'Aramis' (proper name in dict) or 'in law' -> 'inlaw'."""
    return a.lower() in STOP_GLUE or b.lower() in STOP_GLUE


def _proper_noun_trap(a, joined):
    """When `a` is Title Case (likely a proper noun), only allow the merge
    if the joined form is a *direct* English word (no suffix-stripping
    needed). This blocks bogus joins like 'Bera king' -> 'Beraking' where
    the dictionary only matches via the obscure root 'berak' + '-ing'."""
    if not a:
        return False
    if not (a[0].isupper() and (len(a) == 1 or a[1:].islower())):
        return False
    return joined.lower() not in WORDS


# Inline citation marker artifacts in 1 Clement: the chapter prefix "1Clem"
# was sometimes OCR'd as "lClem" (lowercase L instead of digit 1) and/or
# split across a column edge as "1C lem" / "lC lem". Normalise to "1Clem".
CITATION_PAT = re.compile(r'\b[1lI][Cc]\s*lem\s+(\d+\s*:\s*\d+)')


def fix_text_segment(seg, stats):
    # Pass 0: 1Clem citation-marker normalisation.
    def _cite(m):
        out = f"1Clem {m.group(1)}"
        if out != m.group(0):
            stats["citation"] = stats.get("citation", 0) + 1
        return out
    seg = CITATION_PAT.sub(_cite, seg)

    # Pass 1: hyphen-line-breaks. Safe-ish, but still gated by dictionary
    # AND corpus attestation so we don't fuse legitimate hyphenated
    # compounds (e.g. "in-law") or weird obscure web2 matches.
    def _drop_hyphen(m):
        a, b = m.group(1), m.group(2)
        if _refuse(a, b):
            return m.group(0)
        joined = a + b
        if not is_english(joined):
            return m.group(0)
        # Allow merge if the joined form is a direct dictionary entry
        # (common word) OR is well-attested elsewhere in the corpus.
        if joined.lower() in WORDS or CORPUS_FREQ.get(joined.lower(), 0) >= 2:
            stats["hyphen"] += 1
            return joined
        return m.group(0)
    seg = HYPHEN_BREAK_PAT.sub(_drop_hyphen, seg)

    # Pass 2: soft-wrap merges using dictionary check.
    # Walk all adjacent (word, single-space, word) triples manually so that
    # we can examine *every* consecutive pair without the regex engine
    # consuming words greedily. (Re.sub on a pair pattern would skip the
    # middle word in "the moun tains", missing "moun"+"tains".)
    tokens = TOKEN_PAT.findall(seg)
    if len(tokens) >= 3:
        i = 0
        while i + 2 < len(tokens):
            a, sep, b = tokens[i], tokens[i + 1], tokens[i + 2]
            if (a.isalpha() and b.isalpha() and sep == " "
                    and not _refuse(a, b)):
                # Refuse if `b` starts with uppercase: that almost always
                # means `b` is a proper noun (e.g. "saw Ali", "outran Kĕpha",
                # "woman Izeḇel"), and gluing it onto the prior word loses
                # the name. Legitimate broken-word fragments have `b`
                # lowercase ("moun tains", "Pervers ity").
                if b[0].isupper():
                    i += 1
                    continue
                joined = a + b
                if not _proper_noun_trap(a, joined):
                    a_ok = is_english(a)
                    b_ok = is_english(b)
                    j_ok = is_english(joined)
                    # Allow the merge when the joined form is plausibly
                    # English AND at least one fragment alone is not.
                    # Confidence tiers (any one sufficient):
                    #   * Direct dictionary hit on the joined form.
                    #   * Joined form well-attested elsewhere in the
                    #     corpus (>=2 standalone instances).
                    #   * Either fragment is a corpus-rare token
                    #     (frequency <= 2). Real words like "one",
                    #     "head", "art" appear hundreds+ of times in
                    #     the corpus, while broken fragments like
                    #     "messeng", "ndments", "ju" appear only at
                    #     their broken site — strong artefact signal.
                    direct = joined.lower() in WORDS
                    attested = CORPUS_FREQ.get(joined.lower(), 0) >= 2
                    rare_fragment = (CORPUS_FREQ.get(a.lower(), 0) <= 2
                                     or CORPUS_FREQ.get(b.lower(), 0) <= 2)
                    if (j_ok and (direct or attested or rare_fragment)
                            and not (a_ok and b_ok)):
                        stats["soft"] += 1
                        stats["examples"].setdefault(f"{a} {b}", joined)
                        # Replace three tokens with the joined word and continue
                        tokens[i:i + 3] = [joined]
                        # Don't advance — re-check this position with new neighbour
                        continue
            i += 1
        seg = "".join(tokens)

    return seg


def fix_text(text, stats):
    out = []
    for kind, seg in split_protected(text):
        if kind == "tag":
            out.append(seg)
        else:
            out.append(fix_text_segment(seg, stats))
    return "".join(out)


def build_corpus_freq(books_data):
    """Count how often each lowercase word appears as a single token in the
    corpus. Used as a sanity check: a candidate merge is only allowed if
    the joined form is well-attested elsewhere (count >= 2). This filters
    out matches against obscure dictionary entries (e.g. web2 has 'sawali',
    but 'mountains' shows up 500x where 'sawali' shows up at most once)."""
    from collections import Counter
    freq = Counter()
    for book in books_data:
        for ch in book.get("chapters", {}).values():
            for v in ch.get("verses", []):
                t = TAG_PAT.sub("", v["t"])
                for w in re.findall(r"[A-Za-z]+", t):
                    freq[w.lower()] += 1
    return freq


# Set by main() before fix passes are applied. Used inside _soft_wrap.
CORPUS_FREQ: dict = {}


def main():
    files = sorted(TEXT_DIR.glob("*.json"))
    books_data = []
    for fp in files:
        with fp.open(encoding="utf-8") as f:
            books_data.append(json.load(f))
    global CORPUS_FREQ
    CORPUS_FREQ = build_corpus_freq(books_data)

    stats = {"hyphen": 0, "soft": 0, "examples": {}}
    changed_files = 0
    for fp, book in zip(files, books_data):
        changed = False
        for ch in book.get("chapters", {}).values():
            for v in ch.get("verses", []):
                fixed = fix_text(v["t"], stats)
                if fixed != v["t"]:
                    v["t"] = fixed
                    changed = True
        if changed:
            with fp.open("w", encoding="utf-8") as f:
                json.dump(book, f, ensure_ascii=False, indent=1)
            changed_files += 1

    print(f"Files updated:        {changed_files} / {len(files)}")
    print(f"Hyphen breaks fixed:  {stats['hyphen']}")
    print(f"Soft-wraps merged:    {stats['soft']}")
    if stats.get("citation"):
        print(f"Citation markers:     {stats['citation']}")
    if stats["examples"]:
        print("Sample soft-wrap merges:")
        # Sort by joined-form length (longest first) for visibility
        items = sorted(stats["examples"].items(), key=lambda kv: -len(kv[1]))[:30]
        for orig, joined in items:
            print(f"  {orig!r:30} -> {joined!r}")


if __name__ == "__main__":
    main()
