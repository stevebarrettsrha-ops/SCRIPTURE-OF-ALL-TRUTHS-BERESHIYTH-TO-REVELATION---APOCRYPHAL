"""Apply CLAUDE.md Hebrew-roots transliteration rules to every verse in
assets/text/*.json.

Rules:
1. Word boundaries only — replace whole words, not substrings.
2. Case-sensitive — preserve the source case (TITLE → Title, all-caps → all-caps).
3. Apply multi-word phrases first, then longest single words first.
4. Possessives ("God's" → "Aluahim's") and compounds ("Israelites" →
   "Yasharalites") follow the base word's mapping.
5. Divine names are wrapped in `<span class="dn">…</span>` so the renderer
   can style them; everything else is plain text.

The mapping table is derived directly from CLAUDE.md — keep them in sync.
"""
import json, os, re, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXT_DIR = os.path.join(ROOT, "assets", "text")


# ----------------------------------------------------------------------
# Mapping tables (CLAUDE.md)
# ----------------------------------------------------------------------

# Divine names (always wrap in <span class="dn">).
# Multi-word phrases must come BEFORE the single-word forms.
DIVINE = [
    ("Jesus Christ",      "Yahusha haMashiach"),
    ("LORD",              "Yahuah"),
    ("the Lord",          "Yahuah"),
    ("The Lord",          "Yahuah"),
    ("Lord God",          "Yahuah Aluahim"),
    ("Holy Spirit",       "Ruach haQodesh"),
    ("Holy Ghost",        "Ruach haQodesh"),
    ("Jesus",             "Yahusha"),
    ("Christ",            "Mashiach"),
    ("Messiah",           "Mashiach"),
    ("Elohim",            "Aluahim"),
    ("God",               "Aluahim"),
    ("Yisra’ĕl",          "Yasharal"),   # curly apostrophe (U+2019)
    ("Yisra'ĕl",          "Yasharal"),   # straight apostrophe (U+0027)
    ("Yisrael",           "Yasharal"),
    ("Israel",            "Yasharal"),
    ("Ĕl",                "Al"),
    ("El",                "Al"),
]

# Patriarchs & matriarchs
PEOPLE_PATRIARCHS = [
    ("Adam",       "Adawm"),
    ("Eve",        "Ḥawwah"),
    ("Cain",       "Qayin"),
    ("Abel",       "Heḇel"),
    ("Seth",       "Sheth"),
    ("Enoch",      "Ḥanoḵ"),
    ("Methuselah", "Methushelaḥ"),
    ("Lamech",     "Lemeḵ"),
    ("Noah",       "Noaḥ"),
    ("Ham",        "Ḥam"),
    ("Japheth",    "Yepheth"),
    ("Nimrod",     "Nimroḏ"),
    ("Abraham",    "Aḇraham"),
    ("Abram",      "Aḇram"),
    ("Hagar",      "Haḡar"),
    ("Ishmael",    "Yishma'al"),
    ("Isaac",      "Yitsḥaq"),
    ("Rebecca",    "Riḇqah"),
    ("Esau",       "Ĕsaw"),
    ("Jacob",      "Ya'aqoḇ"),
    ("Joseph",     "Yoseph"),
]

PEOPLE_LEADERS = [
    ("Moses",    "Mosheh"),
    ("Aaron",    "Aharon"),
    ("Joshua",   "Yahusha"),
    ("Samuel",   "Shemu'al"),
    ("David",    "Dawiḏ"),
    ("Solomon",  "Shelomoh"),
    ("Elijah",   "Ĕliyahu"),
    ("Isaiah",   "Yashayahu"),
    ("Jeremiah", "Yirmeyahu"),
    ("Daniel",   "Daniyal"),
    ("Jochebed", "Yokeḇeḏ"),
]

PEOPLE_TRIBES = [
    ("Judah",    "Yahuḏah"),
    ("Benjamin", "Binyamin"),
    ("Simeon",   "Shim'on"),
    ("Levi",     "Lewi"),
    ("Ephraim",  "Ephrayim"),
    ("Manasseh", "Menashsheh"),
    ("Reuben",   "Re'uḇen"),
]

PLACES = [
    ("Jerusalem",  "Yerushalayim"),
    ("Egyptians",  "Mitsrites"),
    ("Egyptian",   "Mitsrite"),
    ("Egypt",      "Mitsrayim"),
    ("Canaan",     "Kena'an"),
    ("Jordan",     "Yarden"),
    ("Midian",     "Miḏyan"),
    ("Zion",       "Tsiyon"),
]

# Theological / liturgical terms (case-sensitive — only lowercase forms unless
# specified otherwise — Sabbath / Torah etc. capitalized in source map to capitalized targets).
TERMS = [
    # plurals first (so "angels" matches before "angel")
    ("commandments", "mitsvot"),
    ("commandment",  "mitsvah"),
    ("testimonies",  "eduyot"),
    ("testimony",    "eduth"),
    ("blessings",    "berakoth"),
    ("blessing",     "berakah"),
    ("covenants",    "berithot"),
    ("covenant",     "berith"),
    ("judgments",    "mishpatim"),
    ("judgment",     "mishpat"),
    ("altars",       "mizbe'achot"),
    ("altar",        "mizbe'ach"),
    ("priests",      "kohanim"),
    ("priesthood",   "kehunnah"),
    ("priestly",     "kohenic"),
    ("high priest",  "kohen gadol"),
    ("priest",       "kohen"),
    ("angels",       "mal'akim"),
    ("angel",        "mal'ak"),
    ("messengers",   "mal'akim"),
    ("messenger",    "mal'ak"),
    ("assemblies",   "qahalim"),
    ("assembly",     "qahal"),
    ("congregations","qahalim"),
    ("congregation", "qahal"),
    ("prophets",     "neḇi'im"),
    ("prophecy",     "neḇuah"),
    ("prophet",      "naḇi"),
    ("souls",        "nepheshoth"),
    ("soul",         "nephesh"),
    ("spirits",      "ruchot"),
    ("heavens",      "shamayim"),
    ("heaven",       "shamayim"),
    ("blessed",      "baruk"),
    ("salvation",    "yasha"),
    ("temple",       "heykal"),
    ("Sabbath",      "Shabbath"),
    ("Passover",     "Pesach"),
    ("Tabernacles",  "Sukkot"),
    ("Praise Yah",   "HalleluYah"),
    ("Sheol",        "Sheol"),
    # Less specific singletons that could overlap with English fragments —
    # leave OFF by default to avoid over-aggressive replacement:
    # ("spirit", "ruach"),  # would match too aggressively in proverbs/wisdom
    # ("peace",  "shalom"),
    # ("grace",  "chen"),
    # ("favour", "chen"),
]


# ----------------------------------------------------------------------
# Replacement engine
# ----------------------------------------------------------------------

def case_match(replacement, source):
    """Return `replacement` cased to match `source`.

    - source ALL CAPS  → replacement ALL CAPS
    - source Title-cased → replacement Title-cased
    - source lowercase → replacement lowercase (use as-is)
    """
    if source.isupper():
        return replacement.upper()
    # Title case if first letter capital and rest lowercase
    if source[:1].isupper() and source[1:].islower():
        # Capitalize first letter of replacement, keep diacritics
        return replacement[:1].upper() + replacement[1:]
    if source.istitle():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def build_replacements(divine, *groups):
    """Produce a list of (pattern, replacement_callable) tuples,
    sorted by pattern length descending so longer phrases win.

    Special rule type "prefix" matches the source as a word PREFIX
    followed by another letter (used to fold compound names like
    Ĕliyahu / Eliab / Eldad → Aliyahu / Aliab / Aldad)."""
    rules = []
    # Divine names get wrapped in <span class="dn">
    for src, dst in divine:
        rules.append(('divine', src, dst))
    for group in groups:
        for src, dst in group:
            rules.append(('plain', src, dst))
    # Sort by source length descending so multi-word and longer names match first
    rules.sort(key=lambda r: -len(r[1]))
    # Prefix rules — applied LAST so longer named matches (Elohim, Ĕliyahu mappings
    # etc.) get first crack. Match Word-start "El"/"Ĕl" followed by another letter.
    PREFIX_RULES = [("Ĕl", "Al"), ("El", "Al")]
    for src, dst in PREFIX_RULES:
        rules.append(('prefix', src, dst))
    compiled = []
    for kind, src, dst in rules:
        if kind == 'prefix':
            # Word start followed by another letter (compound names only).
            pat = re.compile(rf"\b{re.escape(src)}(?=[A-Za-zÀ-ɏḀ-ỿ])", re.IGNORECASE)
        else:
            # Word-boundary regex; case-insensitive so we can match different cases
            # then fix the case in the replacer.
            pat = re.compile(rf"\b{re.escape(src)}(?='s\b|s\b|\b)", re.IGNORECASE)
        compiled.append((kind, pat, src, dst))
    return compiled


def transliterate(text, rules):
    """Apply all rules to `text`. Returns the transformed text."""
    # Track positions already replaced so longer matches "win" and we don't
    # re-replace inside a previous span (e.g., don't match "God" inside "Yahuah").
    out = []
    i = 0
    # Use placeholder approach: mark protected ranges
    # Strategy: iterate per rule, but apply non-overlapping. Simpler approach:
    # apply rules in order (longest first), each rule with a protected-region
    # check via sentinel char.
    SENTINEL = "\x00"
    for kind, pat, src, dst in rules:
        def repl(m):
            matched = m.group(0)
            replaced_word = case_match(dst, matched.replace("'s", "").rstrip("s") if matched.endswith("'s") else
                                            matched.rstrip("s") if matched.lower().endswith("s") and not src.endswith("s") and src.lower() + "s" == matched.lower() else
                                            matched)
            # Possessive
            if matched.endswith("'s"):
                final = case_match(dst, matched[:-2]) + "'s"
            elif (matched.lower() == src.lower() + "s"
                  and not src.lower().endswith("s")):
                # Plural added — for proper nouns we add 's' to the transliteration
                # (e.g. Israelites already in PLACES; otherwise simple "s")
                final = case_match(dst, matched[:-1]) + "s"
            else:
                final = case_match(dst, matched)
            # Wrap divine names with sentinel-protected span
            if kind == 'divine':
                return SENTINEL + '<span class="dn">' + final + '</span>' + SENTINEL
            elif kind == 'prefix':
                # Just substitute the prefix — preserve the rest of the word
                # (the regex is zero-width-lookahead for the next letter, so
                # the matched text is only the prefix itself).
                return SENTINEL + final + SENTINEL
            else:
                return SENTINEL + final + SENTINEL
        # Apply only outside SENTINEL regions
        parts = text.split(SENTINEL)
        # Even-indexed parts are unprotected; odd-indexed already replaced
        for idx in range(0, len(parts), 2):
            parts[idx] = pat.sub(repl, parts[idx])
        text = SENTINEL.join(parts)
    # Strip sentinels
    return text.replace(SENTINEL, '')


def main():
    rules = build_replacements(DIVINE, PEOPLE_PATRIARCHS, PEOPLE_LEADERS,
                               PEOPLE_TRIBES, PLACES, TERMS)
    files = sorted(glob.glob(os.path.join(TEXT_DIR, "*.json")))
    total_verses = 0
    for f in files:
        with open(f, encoding='utf-8') as fp:
            book = json.load(fp)
        changed = 0
        for ch_str, cdat in book.get('chapters', {}).items():
            for v in cdat.get('verses', []):
                new_t = transliterate(v['t'], rules)
                if new_t != v['t']:
                    v['t'] = new_t
                    changed += 1
        if changed:
            with open(f, 'w', encoding='utf-8') as fp:
                json.dump(book, fp, ensure_ascii=False, indent=1)
            total_verses += changed
        print(f'{book["id"]:<28} {changed:>5} verse(s) updated')
    print(f'\nTotal: {total_verses} verses transliterated.')


if __name__ == '__main__':
    main()
