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

# Optional English wordlist used by the post-passes (-el → -al and Yi/Ye → Yah)
# to skip genuine English words (Yet/Yes/Year/Wheel/Steel etc.). If the
# wordlist isn't installed, the post-passes simply rely on a smaller
# hand-curated stoplist below.
try:
    from english_words import get_english_words_set
    ENGLISH_WORDS = get_english_words_set(["web2"], lower=True)
except ImportError:
    ENGLISH_WORDS = set()


# English words beginning with "El"/"el" (or "Ĕl") that the prefix rule
# (Ĕl→Al / El→Al) must NOT convert. The prefix rule fires on "Eliyahu",
# "Elohim", "Elam" etc., but should leave English words like "Elect",
# "Elder", "Else", "Element" intact.
EL_PREFIX_EXCEPTIONS = {
    "elect", "elects", "elected", "electing", "election", "elections",
    "elective", "electoral", "elector", "electors",
    "electric", "electrical", "electricity",
    "electron", "electronic", "electronics",
    "elder", "elders", "elderly", "eldest",
    "else", "elsewhere",
    "elephant", "elephants",
    "element", "elements", "elemental", "elementary",
    "eleven", "eleventh",
    "eligible", "eligibility",
    "eliminate", "eliminated", "eliminating", "elimination",
    "eloquence", "eloquent", "eloquently",
    "elaborate", "elaborated", "elaborately",
    "elated", "elastic", "elapsed",
    "elder's", "elders'",
}

# Common English words ending in "-el"/"-EL" that the suffix post-pass must
# NOT touch (so "Wheel" doesn't become "Wheal", "Rebel" stays "Rebel").
# This is the exclusive list — note we deliberately don't consult the
# generic English wordlist because it contains many proper-noun names
# (Michael, Rachel, Uriel, Gabriel, Raphael, …) that the user DOES want
# transliterated. Add new English words here if any slip through.
EL_SUFFIX_EXCEPTIONS = {
    # Verbs
    "feel", "feels", "feeling", "feels", "feelings", "felt",
    "compel", "compels", "compelled", "compelling",
    "expel", "expels", "expelled", "expelling",
    "dispel", "dispels", "dispelled", "dispelling",
    "impel", "impels", "impelled", "impelling",
    "propel", "propels", "propelled", "propelling", "propeller",
    "repel", "repels", "repelled", "repelling", "repellent",
    "excel", "excels", "excelled", "excelling", "excellent", "excellence", "excellently",
    "rebel", "rebels", "rebelled", "rebelling", "rebellion", "rebellious",
    "cancel", "cancels", "canceled", "cancelled", "canceling", "cancellation",
    "level", "levels", "leveled", "leveling",
    "model", "models", "modeled", "modeling",
    "panel", "panels", "paneled", "paneling",
    "travel", "travels", "traveled", "traveling", "traveler", "travellers",
    "marvel", "marvels", "marvelled", "marvelling", "marveled", "marveling", "marvellous", "marvelous",
    "label", "labels", "labeled", "labelling", "labeling",
    "yodel", "yodels", "yodeled",
    "shrivel", "shrivels", "shriveled", "shriveling",
    "snivel", "snivels",
    "swivel", "swivels", "swiveled",
    "shovel", "shovels", "shoveled", "shoveling",
    "drivel",
    # Nouns — common English
    "counsel", "counsels", "counseled", "counseling",
    "counsellor", "counsellors", "counselor", "counselors",
    "wheel", "wheels", "wheeled",
    "steel", "steels",
    "angel", "angels", "angelic",
    "chapel", "chapels",
    "cruel", "cruelly", "cruelty",
    "fuel", "fuels", "fueled", "fueling",
    "duel", "duels", "dueled",
    "gospel", "gospels",
    "mussel", "mussels",
    "parallel", "parallels", "paralleled",
    "navel", "navels",
    "jewel", "jewels", "jeweled", "jewelled", "jewelry", "jewellery",
    "vowel", "vowels",
    "tunnel", "tunnels", "tunneled", "tunneling",
    "channel", "channels", "channeled", "channeling",
    "kennel", "kennels",
    "barrel", "barrels", "barreled",
    "novel", "novels", "novelist",
    "bowel", "bowels",
    "towel", "towels", "toweled",
    "dowel", "dowels",
    "vessel", "vessels",
    "chisel", "chisels", "chiseled",
    "easel", "easels",
    "hostel", "hostels",
    "libel", "libels", "libelous",
    "pretzel", "pretzels",
    "camel", "camels",
    "scalpel", "scalpels",
    "shekel", "shekels",                 # currency — appears as common noun
    "tassel", "tassels",
    "satchel", "satchels",
    "kestrel", "kestrels",
    "mongrel", "mongrels",
    "scoundrel", "scoundrels",
    "squirrel", "squirrels",
    "sequel", "sequels",
    "nickel", "nickels",
    "gravel", "gravels", "graveled",
    "gavel", "gavels",
    "petrel", "petrels",
    "morel", "morels",
    "hovel", "hovels",
    "parcel", "parcels", "parceled",
    "snorkel", "snorkels", "snorkeled",
    "tinsel",
    "trowel", "trowels", "troweled",
    "cudgel", "cudgels",
    "schnitzel",
    "personnel",
    "spaniel", "spaniels",
    "carousel", "carousels",
    "pixel", "pixels",
    "betel",                             # betel nut
    "bushel", "bushels",                 # biblical measure but English noun
    "bagel", "bagels",
    "mantel", "mantels",                 # fireplace mantel (different from "mantle")
    "rondel", "rondels",
    "decimal",                           # ends in -al, included for safety
}

# Common English words starting with "Yi" or "Ye" — these stay unchanged.
# "Yet", "Yes", "Yea", "Year(s)", "Yellow", etc. show up frequently in
# the corpus as ordinary prose, not as Hebrew names. (Drop the generic
# English wordlist check that previously protected these — web2 also
# contains obscure entries like "yether" which IS a biblical name and
# should transliterate; the user's directive applies broadly.)
YI_YE_EXCEPTIONS = {
    "yet", "yes", "yea", "year", "years", "yearly", "yearling", "yearlings",
    "yearn", "yearns", "yearned", "yearning",
    "yellow", "yellows", "yellowed", "yellowing", "yellowish",
    "yeast", "yeasts", "yeasty",
    "yell", "yells", "yelled", "yelling",
    "yesterday", "yet's",
    "yew", "yews",
    "yelp", "yelps", "yelped", "yelping",
    "yeoman", "yeomen",
    "yield", "yields", "yielded", "yielding",
    "yip", "yips", "yipe",
    "yen", "yens",                      # currency
    "yes-no", "yes's",
    "yeah", "yeahs",
    "yiddish", "yenta", "yentas",
    "yeti", "yetis",
}


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
    # Paleo-Hebrew render of יהושע — letters O-S-w-h-y in the Besorah PDF
    # are paleo glyphs for ע-ש-ו-ה-י (read right-to-left = Yahusha).
    ("OSwhy",             "Yahusha"),
    ("Christ",            "Mashiach"),
    ("Messiah",           "Mashiach"),
    ("Elohim",            "Aluahim"),
    ("God",               "Aluahim"),
    ("Yisra’ĕl",          "Yasharal"),   # curly apostrophe (U+2019)
    ("Yisra'ĕl",          "Yasharal"),   # straight apostrophe (U+0027)
    ("Yisraĕl",           "Yasharal"),   # no apostrophe
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
    # John the apostle / baptist — the source PDF uses "Yoḥanan", which
    # CLAUDE.md prescribes be normalised to "Yahuchanon" (the spelling
    # used for the four Yahuchanon books in the index).
    ("Yoḥanan",  "Yahuchanon"),
    ("Yochanan", "Yahuchanon"),
    ("Yohanan",  "Yahuchanon"),
    ("John",     "Yahuchanon"),
]

# Biblical proper nouns that begin with "J" — collapse to the Hebrew "Y"
# form per the user's directive ("any name with J should be Y"). English
# words that happen to begin with J (Just, Joy, Judge, Jealousy, Jubilant,
# Joke, Journal, ...) are deliberately NOT in this list and stay as-is.
PEOPLE_J_NAMES = [
    ("Jared",       "Yared"),
    ("Josiah",      "Yoshiyahu"),
    ("Jashub",      "Yashub"),
    ("Jeconiah",    "Yekanyah"),
    ("Jericho",     "Yeriḥo"),
    ("Jubilees",    "Yobelim"),
    ("Jubilee",     "Yobel"),
    ("Jason",       "Yason"),
    ("Judas",       "Yahudah"),
    ("Jews",        "Yahuḏim"),
    ("Jewish",      "Yahuḏite"),
    ("Jew",         "Yahuḏi"),
    ("Jehiel",      "Yeḥiel"),
    ("Joram",       "Yoram"),
    ("Jonah",       "Yonah"),
    ("Joel",        "Yoal"),
    ("Job",         "Iyob"),
    ("Jobab",       "Yobab"),
    ("Janus",       "Yanus"),
    ("Jania",       "Yania"),
    ("Janeas",      "Yaneas"),
    ("Javan",       "Yawan"),
    ("Jair",        "Yair"),
    ("Jaazer",      "Yaazer"),
    ("Jokshan",     "Yokshan"),
    ("Joakim",      "Yoaqim"),
    ("Jabin",       "Yabin"),
    ("Jephunneh",   "Yephunneh"),
    ("Japhia",      "Yaphia"),
    ("Jezebel",     "Izeḇel"),
    ("Jephtha",     "Yiphtaḥ"),
    ("Jephthah",    "Yiphtaḥ"),
    ("Joash",       "Yo'ash"),
    ("Jehoiakim",   "Yehoyaqim"),
    ("Jehoshaphat", "Yehoshaphat"),
    ("Jehu",        "Yehu"),
    ("Jonadab",     "Yonadab"),
    ("Jonathan",    "Yehonathan"),
    ("Judea",       "Yahuḏah"),
    ("Jabuk",       "Yabuk"),
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
    # Israel-as-people (non-divine): Israelite/Israelites and the various
    # half-transliterated variants the prefix-rule "El→Al" leaves behind
    # when the Yisra'el rule misses ("Yisra'el" + "ites" -> "Yisra'Alites").
    # Listed before bare "Israel" wins, since the engine sorts by length.
    ("Israelite",       "Yasharalite"),
    ("Yisra’Alite",     "Yasharalite"),
    ("Yisra'Alite",     "Yasharalite"),
    ("Yisraĕlite",      "Yasharalite"),
    ("Yisraelite",      "Yasharalite"),
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
    ("spirit",       "ruach"),
    # Hebrew "ruach" is the same word for "wind" — Bereshith 1:2's
    # "Ruach of Aluahim hovered" and 8:1's "wind to pass over the earth"
    # share the same root, so the English split into spirit/wind collapses
    # back into ruach / ruchot in a Hebrew-roots edition.
    ("winds",        "ruchot"),
    ("wind",         "ruach"),
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
    # Hebrew "shalom" covers wholeness/well-being/completeness, broader
    # than English "peace"; collapse them.
    ("peace",        "shalom"),
    # Hebrew "chen" covers grace/favour. Both English spellings map here.
    ("grace",        "chen"),
    ("favour",       "chen"),
    ("favor",        "chen"),
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
            # Capture the FULL word so the replacer can check it against the
            # English-words exception list (Elect, Elder, Else, Element, …).
            pat = re.compile(rf"\b{re.escape(src)}([A-Za-zÀ-ɏḀ-ỿ]+)", re.IGNORECASE)
        else:
            # The bare "Ĕl"/"El" divine rule must NOT match when it appears as
            # the suffix of a compound name like "Shemu'ĕl" or "Yisra'ĕl" —
            # otherwise the engine wraps that suffix as "<span class=dn>Al</span>"
            # and we end up with "Shemu'<span class=dn>Al</span>" stranded
            # markup. Specifically anchor to a negative lookbehind for any
            # kind of apostrophe.
            apos_guard = r"(?<!['’])" if src in ("Ĕl", "El") else ""
            pat = re.compile(
                rf"{apos_guard}\b{re.escape(src)}(?='s\b|s\b|\b)",
                re.IGNORECASE,
            )
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
        def repl(m, kind=kind, src=src, dst=dst):
            matched = m.group(0)

            # Prefix rule: the regex captures the FULL word (prefix + rest).
            # Check against the English-word exception list before converting,
            # so "Elect", "Elder", "Else", "Element" stay unchanged while
            # "Eliyahu", "Elohim", "Elam" still flip to "Aliyahu" / "Aluahim"
            # / "Alam".
            if kind == 'prefix':
                if matched.lower() in EL_PREFIX_EXCEPTIONS:
                    return matched
                prefix_part = matched[:len(src)]
                rest = matched[len(src):]
                new_prefix = case_match(dst, prefix_part)
                return SENTINEL + new_prefix + rest + SENTINEL

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


# Repair pass for corpora where an earlier transliteration run wrapped
# the "Ĕl" inside "Yisra'Ĕl" before the longer "Yisra'Ĕl→Yasharal" rule
# could fire, leaving stranded fragments like:
#     Yisra’<span class="dn">Al</span>
# The pattern can't be undone by the normal rule engine (the matched
# text is now split across markup), so we patch it post-hoc.
_STRANDED_YISRA = re.compile(
    r'Yisra[\'’]?<span class="dn">Al</span>(?:ite(s?))?'
)
def repair_stranded_yisra(text):
    def _r(m):
        suffix = m.group(1)  # None | '' | 's'
        if m.group(0).endswith('ites'):
            return 'Yasharalites'
        if m.group(0).endswith('ite'):
            return 'Yasharalite'
        return '<span class="dn">Yasharal</span>'
    return _STRANDED_YISRA.sub(_r, text)


# Annotate every paleo-Hebrew tetragrammaton "HWHY" with the spoken form
# "(YAHUAH)" placed in front, so readers see both the source render and
# the transliteration. The inner "HWHY" gets wrapped in a class="hwhy"
# span purely as an idempotency marker — re-runs see the marker and skip
# already-annotated occurrences.
_HWHY_PAT = re.compile(r'(?<!"hwhy">)\bHWHY\b')
def annotate_hwhy(text):
    return _HWHY_PAT.sub(
        '(<span class="dn">YAHUAH</span>) <span class="hwhy">HWHY</span>',
        text,
    )


# Post-pass: convert "-el" suffix to "-al" on Hebrew proper nouns. The user's
# directive is general ("Names that end in el should be al"), so this fires
# on any Title Case word ending in -el / -EL that isn't a known English word.
# The regex skips contents of <span> tags by anchoring to word characters
# only — markup can't accidentally end in "el" since "</span>" doesn't
# satisfy \w endings.
# The character class includes plain "e/E" plus the diacritic forms "ĕ/Ĕ"
# (U+0115 / U+0114) so that "Shemu’ĕl", "Yehezq’ĕl" etc. match alongside
# "Uriel", "Michael". Any letter case ("EL", "El", "eL", "el", "ĕl", "Ĕl",
# "ĚL", "ĕL") is supported, with the new suffix ("AL"/"Al"/"aL"/"al")
# derived per-character from the source case.
_EL_SUFFIX_PAT = re.compile(
    r"\b[A-ZĀ-ɏḀ-ỿ][A-Za-zÀ-ɏḀ-ỿ'’]+[EeĔĕ][Ll]\b"
)
def el_suffix_to_al(text):
    def _r(m):
        word = m.group(0)
        wl = word.lower()
        if wl in EL_SUFFIX_EXCEPTIONS:
            return word
        e_char = word[-2]
        l_char = word[-1]
        new_a = "A" if e_char.isupper() else "a"
        new_l = "L" if l_char.isupper() else "l"
        return word[:-2] + new_a + new_l
    # Iterate to a fixed point — compound names like "Yehallel'ĕl" contain
    # multiple "-el" segments separated by apostrophes; each pass strips the
    # outermost match, so we keep going until no further change.
    prev = None
    while text != prev:
        prev = text
        text = _EL_SUFFIX_PAT.sub(_r, text)
    return text


# Post-pass: convert "Yi"/"Ye" prefix on proper nouns to "Yah" (or "YAH"
# if the source is all-caps). Skips English words (Yet/Yes/Year/Yellow/…).
# Example: Yerushalayim → Yahrushalayim, Yitsḥaq → Yahtsḥaq.
_YI_YE_PAT = re.compile(
    r"\bY[eEiI][a-zA-ZÀ-ɏḀ-ỿ'’]+\b"
)
def yi_ye_to_yah(text):
    def _r(m):
        word = m.group(0)
        wl = word.lower()
        # Only consult the curated stoplist — the generic English wordlist
        # contains obscure entries like "yether" that the user wants
        # transliterated as the biblical name (Yahther).
        if wl in YI_YE_EXCEPTIONS:
            return word
        first  = word[0]   # Y or y
        second = word[1]   # e/E/i/I
        rest   = word[2:]
        ah = "AH" if second.isupper() else "ah"
        return first + ah + rest
    return _YI_YE_PAT.sub(_r, text)


def main():
    rules = build_replacements(DIVINE, PEOPLE_PATRIARCHS, PEOPLE_LEADERS,
                               PEOPLE_J_NAMES, PEOPLE_TRIBES, PLACES, TERMS)
    files = sorted(glob.glob(os.path.join(TEXT_DIR, "*.json")))
    total_verses = 0
    for f in files:
        with open(f, encoding='utf-8') as fp:
            book = json.load(fp)
        changed = 0
        for ch_str, cdat in book.get('chapters', {}).items():
            for v in cdat.get('verses', []):
                new_t = transliterate(v['t'], rules)
                new_t = repair_stranded_yisra(new_t)
                # Apply user-directed normalisations BEFORE HWHY annotation
                # so the Yi/Ye → Yah pass doesn't see the "(YAHUAH)" prefix
                # text it would also accidentally transform.
                new_t = yi_ye_to_yah(new_t)
                new_t = el_suffix_to_al(new_t)
                new_t = annotate_hwhy(new_t)
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
