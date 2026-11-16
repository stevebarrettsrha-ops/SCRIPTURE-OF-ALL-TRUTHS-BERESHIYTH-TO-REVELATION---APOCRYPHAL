#!/usr/bin/env python3
"""
unify_names.py

One name, one spelling. The canon was extracted from several editions, and
the same person or place arrives spelled two ways — "Ya'aqoḇ" beside
"Ya‛aqoḇ", "Laḇan" beside "Laban", "Aḇraham" beside "Aḇrahim", "Aliyahu"
beside "Ĕliyahu". This script finds every such pair and settles it.

Which form wins:

  1. EXPLICIT — forms the owner has ruled on. The ancient forms the canon
     itself prints win over later ones: Aliyahu, Aḇraham, Yahrushalayim,
     Yahtsḥaq, Yahshma'al, Yahshayahu, Yahrmeyahu.
  2. GUIDE — a name listed in CLAUDE.md takes the spelling given there
     (Ya'aqoḇ, Yoseph, Lewi, Re'uḇen, Shim'on, Kena'an, Yarden, Sheth …),
     and so do the words built on it (Lewites, Re'uḇenites, Kena'anites).
  3. Otherwise, of two forms that differ only in their Hebrew marks
     (ḇ ḏ ḥ ḵ ḡ ĕ and the ayin / aleph apostrophes), the one carrying the
     marks wins — "Laḇan" over "Laban", "Ḥeḇron" over "Hebron" — and a tie
     goes to the commoner form.

  4. There is no J in these names: J is Y, and Ja is Yah. A name that
     still arrived with a J (mostly in Ḥanoḵ, Yashar, Yoḇelim and 1 Ezra)
     takes the form the canon already prints for the same person or place
     where there is one (Jebusites -> Yahḇusites, Jethro -> Yahthro), and
     otherwise is respelled by the rule (Ijasusa'al -> Yahsusa'Al,
     Gida'ljal -> Gada'lYah'Al). Roman names (Julius, Justus, Julia,
     Junias) are left as they are.
  5. Ye- and Je- are Yah-, as the canon already has it in Yahrushalayim
     and Yahrmeyahu: Yĕshua -> Yahshua, Yĕhu -> Yahhu, Yehudith -> Yahudith.

Pairs that only look alike are left alone (DISTINCT): "Baruk" the word and
"Baruḵ" the man, "Haran" the man and "Ḥaran" the city, "Ramah" and
"Ra‛mah", and so on.

Usage:
    python3 scripts/unify_names.py            # report what differs (exit 1)
    python3 scripts/unify_names.py --fix      # rewrite assets/text/
    python3 scripts/unify_names.py --verbose  # list every pair and its winner
"""
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT_DIR = ROOT / "assets" / "text"

TAG = re.compile(r"(<[^>]+>)")
WORD = re.compile(r"[A-Za-zÀ-ɏḀ-ỿ]+(?:[‛’'][A-Za-zÀ-ɏḀ-ỿ]+)*")
MARKS = set("ḇḏḥḵḡĕḆḎḤḴḠĔ‛’'")

# 1. Ruled on by the owner: later form -> ancient form.
EXPLICIT = {
    "Aḇrahim": "Aḇraham",
    "Ĕliyahu": "Aliyahu",
    "Yashayahu": "Yahshayahu",
}

# 2. Spellings fixed by CLAUDE.md, and every rival of each. Words built on
#    the name (…ite, …ites) follow it.
GUIDE = {
    "Ya'aqoḇ": ["Ya‛aqoḇ", "Ya’aqoḇ"],
    "Yoseph": ["Yosĕph"],
    "Yahuḏah": ["Yahudah"],
    "Yahuḏi": ["Yahudi"],
    "Yahuḏim": ["Yahudim"],
    "Shim'on": ["Shim‛on", "Shim’on", "Shimon"],
    "Kena'an": ["Kena‛an", "Kena’an"],
    "Lewi": ["Lĕwi"],
    "Re'uḇen": ["Re’uḇĕn", "Re‛uḇĕn", "Re'uḇĕn", "Re’uḇen", "Reuben"],
    "Yarden": ["Yardĕn"],
    "Sheth": ["Shĕth"],
    "Sheol": ["She’ol"],
    "Dawiḏ": ["Dawid"],
    "Sha’ul": ["Shaul"],
    "Yo'Al": ["Yo’al", "Yo’Ãl", "Yo'al"],
    "Yahshma'al": ["Yahshma‛al", "Yahshma’al"],
    "Dan": ["Ḏan"],
    "Estĕr": ["Ester"],
    "Yokeḇeḏ": ["Yoḵeḇeḏ"],
}
# The letter of Yahudah (Jude) is named as the guide names it.
GUIDE_SKIP_BOOKS = {"Yahudah": {"yahudah"}}

# 4. No J: J is Y, Ja is Yah. Left side as it arrived, right side settled.
NO_J = {
    # --- the form the canon already prints for the same name
    "Jeshua": "Yĕshua", "Joppa": "Yapho", "Jamnia": "Yaḇneh",
    "Jozadak": "Yahhotsaḏaq", "Jebusites": "Yahḇusites",
    "Jebusite": "Yahḇusite", "Jabus": "Yahḇus", "Jephuneh": "Yahphunneh",
    "Joab": "Yo’aḇ", "Jozabad": "Yozaḇaḏ", "Jeremoth": "Yahrĕmoth",
    "Jamin": "Yamin", "Jachin": "Yaḵin", "Jesse": "Yahshai",
    "Jeshaiah": "Yahshayah", "Jarib": "Yariḇ", "Jehohanan": "Yahhoḥanan",
    "Malchijah": "Malkiyah", "Malchiyah": "Malkiyah", "Joarib": "Yoyariḇ",
    "Jazer": "Ya‛zĕr", "Jemual": "Yahmu’al", "Jeush": "Ye‛ush",
    "Jetzer": "Yĕtser", "Jezer": "Yĕtser", "Jaakon": "Ya‛aqan",
    "Jahaz": "Yahats", "James": "Ya'aqoḇ", "Jehoiachin": "Yahhoyaḵin",
    "Jorah": "Yorah", "Jedaiah": "Yahḏayah", "Jahazial": "Yaḥazi’al",
    "Josiphiah": "Yosiphyah", "Jahzeiah": "Yaḥzeyah", "Mijamin": "Miyamin",
    "Jeremai": "Yahrĕmai", "Ahijah": "Aḥiyah", "Kirjath": "Qiryath",
    "Jabbok": "Yabboq", "Jabbuk": "Yabboq", "Jasub": "Yashuḇ",
    "Jahleal": "Yaḥle’al", "Jachleal": "Yaḥle’al", "Yachleal": "Yaḥle’al",
    "Jahzial": "Yaḥtsi’al", "Jachzeal": "Yaḥtse’al", "Yachzeal": "Yaḥtse’al",
    "Jeroboam": "Yaroḇ‛am", "Jobal": "Yobal", "Jabal": "Yaḇal",
    "Jubal": "Yuḇal", "Jetheth": "Yahthĕth", "Ajah": "Ayah",
    "Jehoseph": "Yahhosĕph", "Jishvah": "Yahshwah", "Jishvi": "Yahshwi",
    "Jethro": "Yahthro", "Jered": "Yahreḏ", "Jarmuth": "Yarmuth",
    "Ajalon": "Ayalon", "Hallelujah": "HalleluYah", "Halleluyah": "HalleluYah",
    "Judith": "Yehudith", "Jehudith": "Yehudith",
    # --- by the rule alone
    "Jambri": "Yahmbri", "Jaalah": "Yahalah", "Jaddus": "Yahddus",
    "Joda": "Yoda", "Johanan": "Yoḥanan", "Jeual": "Yeual",
    "Jodan": "Yodan", "Jeremial": "Yahrĕmial", "Jathan": "Yahthan",
    "Javanim": "Yahwanim", "Jimnah": "Yimnah", "Jekuthial": "Yequthial",
    "Janiah": "Yahniah", "Jobat": "Yobat", "Jephal": "Yephal",
    "Jannes": "Yahnnes", "Jambres": "Yahmbres",
    # --- the names in Ḥanoḵ and Yoḇelim
    "Ijasusa'al": "Yahsusa'Al", "Gida'ljal": "Gada'lYah'Al",
    "Mel'ejal": "Mel'eYah'Al", "Melkejal": "MelkeYah'Al",
    "Baraqijal": "BaraqiYah'Al", "Rumjal": "RumYah'Al",
    "Danjal": "DanYah'Al", "Batarjal": "BatarYah'Al",
    "Busasejal": "BusaseYah'Al", "Rasujal": "RasuYah'Al",
    "Jomjaal": "YomYah'Al", "Semjaza": "SemYahza", "Samjaza": "SamYahza",
    "Kasdeja": "KasdeYah", "Asonja": "AsonYah", "Orjares": "OrYahres",
    "Hilujaseph": "HiluYahseph", "Abelsjail": "Abelsyail",
    "Jetral": "Yetral", "Jeqon": "Yeqon", "Aljo": "Alyo",
    "Ijaska": "Yahska", "Ijasaka": "Yahsaka", "Ijaka": "Yahka",
    "Ijona": "Iyona", "Ije": "Iyĕ",
}
# 5. Ye- and Je- are Yah-: the same rule the canon already follows in
#    Yahrushalayim, Yahriḥo and Yahrmeyahu, carried to the names it missed.
YE_YAH = {
    "Yĕhu": "Yahhu", "Yĕshua": "Yahshua", "Yehudith": "Yahudith",
    "Ye‛arim": "Yah‛arim", "Ye‛i’ĕl": "Yah‛i’ĕl", "Ye‛ush": "Yahush",
    "Yĕtser": "Yahtser", "Yĕtserites": "Yahtserites", "Yĕsher": "Yahsher",
    "Ye‛u’ĕl": "Yah‛u’ĕl", "Ye‛uts": "Yah‛uts", "Yeual": "Yahual",
    "Yequthial": "Yahquthial", "Yephal": "Yahphal", "Yetral": "Yahtral",
    "Yeqon": "Yahqon", "Miḵayehu": "Miḵayahu",
    "Alyeho‛ĕynai": "Alyahho‛ĕynai",
}
THE_NAME = '(<span class="dn">YAHUAH</span>) <span class="hwhy">HWHY</span>'

# Look-alikes that are different names, or a name beside a common word.
DISTINCT = {
    "baruk", "shelah", "haran", "er", "ramah", "ben", "heal", "hor", "abi",
    "bel", "en", "masters", "temah", "hoshea", "haggai", "nahum", "yahtsah",
    "ezer", "tob", "lud", "eri", "kesed", "madai", "amen",
}


def fold(w):
    s = unicodedata.normalize("NFD", w)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[‛’']", "", s).lower()


def marks(w):
    return sum(1 for c in w if c in MARKS)


def books():
    for path in sorted(TEXT_DIR.glob("*.json")):
        yield path, json.loads(path.read_text(encoding="utf-8"))


def count_words():
    cnt = Counter()
    for _, data in books():
        for ch in data["chapters"].values():
            for v in ch["verses"]:
                for w in WORD.findall(TAG.sub(" ", v["t"])):
                    if w[0].isupper() and not w.isupper():
                        cnt[re.sub(r"[’']s$", "", w)] += 1
    return cnt


def build_map(cnt):
    """variant -> winner, for whole words."""
    mapping = dict(EXPLICIT)
    mapping.update(NO_J)
    mapping.update(YE_YAH)
    guide_stems = []
    for win, rivals in GUIDE.items():
        for r in rivals:
            mapping[r] = win
            guide_stems.append((r, win))
    settled = {fold(w) for w in list(mapping) + list(mapping.values())}
    settled -= {fold(w) for w in NO_J.values()} - {fold(w) for w in NO_J}
    settled |= {fold(w) for w in YE_YAH} | {fold(w) for w in YE_YAH.values()}
    stems = sorted(((fold(win), win) for win in GUIDE), key=lambda p: -len(p[0]))

    def built_on_guide(w):
        """Lĕwites -> Lewites: a word built on a guide name follows it."""
        f = fold(w)
        for fs, win in stems:
            if f.startswith(fs) and f[len(fs):] in ("ite", "ites", "te", "tes", "im"):
                return win + f[len(fs):]
        return None

    groups = defaultdict(list)
    for w in cnt:
        groups[fold(w)].append(w)
    for key, forms in groups.items():
        if key in DISTINCT or key in settled:
            continue
        built = built_on_guide(forms[0])
        if built:
            for f in forms:
                mapping[f] = built
            continue
        if len({f.lower() for f in forms}) < 2:
            continue
        win = max(forms, key=lambda f: (marks(f), cnt[f]))
        for f in forms:
            if f != win and f.lower() != win.lower():
                mapping[f] = win
    # Follow a chain to its end: Jeush -> Ye‛ush -> Yahush.
    for k in list(mapping):
        seen = {k}
        while mapping[k] in mapping and mapping[mapping[k]] not in seen:
            seen.add(mapping[k])
            mapping[k] = mapping[mapping[k]]
    return {k: v for k, v in mapping.items() if k != v}


def apply(text, mapping, book):
    def one(m):
        w = m.group(0)
        tail = ""
        mm = re.search(r"[’']s$", w)
        if mm:
            w, tail = w[:mm.start()], mm.group(0)
        win = mapping.get(w)
        if win and book not in GUIDE_SKIP_BOOKS.get(w, ()):
            return win + tail
        return m.group(0)
    text = re.sub(r"\bJehovah\b", THE_NAME, text)
    # Joshua son of Nun is Yahusha, whatever form the edition gave him;
    # the other men named Yahshua (the kohen gadol, the Lewites) keep it.
    text = re.sub(r"\bY(?:ahshuah?|ĕshua|eshua|ahushua) (the )?son of Nun\b",
                  lambda m: "Yahusha " + (m.group(1) or "") + "son of Nun", text)
    parts = TAG.split(text)
    for i in range(0, len(parts), 2):          # even parts are outside tags
        parts[i] = WORD.sub(one, parts[i])
    return "".join(parts)


def main():
    fix = "--fix" in sys.argv
    verbose = "--verbose" in sys.argv
    cnt = count_words()
    mapping = build_map(cnt)
    changed = Counter()
    for path, data in books():
        dirty = False
        for ch in data["chapters"].values():
            for v in ch["verses"]:
                new = apply(v["t"], mapping, path.stem)
                if new != v["t"]:
                    old_words = WORD.findall(TAG.sub(" ", v["t"]))
                    new_words = WORD.findall(TAG.sub(" ", new))
                    for a, b in zip(old_words, new_words):
                        if a != b:
                            changed[(a, b)] += 1
                    v["t"] = new
                    dirty = True
        if dirty and fix:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n",
                            encoding="utf-8")
    total = sum(changed.values())
    if verbose or not fix:
        for (a, b), n in sorted(changed.items(), key=lambda kv: -kv[1]):
            print(f"  {a} -> {b}  ×{n}")
    print(f"{len(changed)} spellings, {total} places "
          f"{'unified' if fix else 'differ from the settled form'}.")
    if total and not fix:
        print("Run with --fix to unify them.")
        sys.exit(1)


if __name__ == "__main__":
    main()
