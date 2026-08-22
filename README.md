# Scripture of All Truths — Bereshith to Revelation, with the Apocrypha

A static web reader for the canon, built directly from the source PDFs in `SCRIPTURE/`.
Each chapter has its own dedicated page that **renders the verse text extracted from
the original PDF in PDF order**, so verse numbering and chapter arrangement match the
source. A "PDF" link on each chapter page lets you cross-reference the original
typesetting. Hebrew transliterations (BERĔSHITH, SHEMOTH, YAHUSHA, …) are used in all
navigation.

## Structure

```
index.html            # HOME — Daily Bread, continue reading, reader, marks
books.html            # Book table of contents (104 books grouped by section)
book.html             # Chapter index for a single book (?id=<bookid>)
chapter.html          # Renders verses for a chapter (?id=<bookid>&ch=<n>)
besorah-offline.html  # Standalone single-file reader (open with file://)
start.bat             # One-click launcher (Windows)
start.command         # One-click launcher (macOS)
start.sh              # One-click launcher (Linux)
assets/
  style.css           # Site theme
  besorah-ids.js      # Book ids that have changed, and what they changed to
  besorah-marks.js    # Bookmarks, marked text + last-read (localStorage)
  besorah-tts.js      # Read-aloud player (browser Web Speech API; offline)
  besorah-home.js     # The home page panels (shared with the offline edition)
  DailyBread.js       # 205 daily portions, each a whole passage (generated)
  pronunciation.js    # How the Hebrew-roots vocabulary is spoken
  words.js            # How a word must appear on the page
  daily-bread.json    # The 98 hand-written portions DailyBread.js starts from
  index.json          # Book → chapter → PDF page mapping
  text/<bookid>.json  # Extracted verses per book (generated)
SCRIPTURE/
  *.pdf               # Original source PDFs (do not edit)
scripts/
  sweep_text.py       # Audits/repairs every book (markers, word forms, markup)
  build_daily_bread.py # Builds assets/DailyBread.js from the whole canon
  extract_index.py    # Builds assets/index.json by scanning the PDFs
  extract_text.py     # Builds assets/text/*.json by extracting verse text
  transliterate.py    # Applies CLAUDE.md Hebrew-roots transliteration rules
  fix_broken_words.py # Repairs words split by PDF line breaks (e.g. "moun tains" -> "mountains")
  build_offline.py    # Bundles everything into besorah-offline.html
```

## Sections covered

- **Torah** (5 books) — Bereshith, Shamoth, Wayyiqra, Bamidbar, Dabarim
- **Nabi'im** (22 books) — Yahusha through Mal'aki
- **Kethubim** (12 books) — Tehillim, Mishle, Iyob, … 2 Dibre haYamim
- **Messianic Writings** (27 books) — Mattithyahu through Ḥazon (Revelation)
- **Apocryphal Books** (4) — Ḥanok (Enoch), Yashar (Jasher), First & Second
  Book of Adam and Eve
- **Testaments of the Twelve Patriarchs** (12)
- **Ethiopic & Eastern Apocrypha** (22) — 1–4 Maccabees, Tobit, Judith, Sirach,
  Wisdom, Baruch, Jubilees, 1 Enoch, 1 Clements, Shepherd of Hermas, …

Total: **104 books**.

## The home page

Opening the reader lands on the home page (`index.html`, or `#/` in the
offline edition), which gathers everything you need to start reading:

| Panel | What it does |
|---|---|
| **Daily Bread** | A portion of scripture with a short reflection, chosen for the day — see below. Press **Read to me** to have it spoken, or open the whole chapter. |
| **Continue reading** | Picks up at the last chapter you had open. |
| **Choose your reader** | Who reads to you: the voices installed on your device, with a speed slider and a **Hear this reader** sample so you can compare them. Your choice is remembered and used on every chapter. |
| **Tehillim** | Today's psalm (the 150 songs walk through the year), a taste of it, a "go to chapter" box, and every chapter one tap away. |
| **Mishle** | The same, following the day of the month — the traditional way to read the 31 proverbs. |
| **Marked text** | Every passage you have marked while reading, quoted with its reference. Click one to jump straight back to it in the chapter. |
| **Bookmarks** | Whole chapters and single verses saved with ☆, plus Export/Import of everything you have kept. |

The full table of contents now lives on **All Books** (`books.html`).

The taste on the Tehillim and Mishle panels is not simply the chapter's first
line. A book can open with its own title ("The proverbs of Shelomoh son of
Dawiḏ, sovereign of Yasharal:"), and one line of a psalm usually stops well
before the thought does, so the taste passes over a heading, runs on verse by
verse until it has a whole sentence to show, and ends at the end of a sentence
or a clause rather than in the middle of a word.

### Daily Bread

`assets/DailyBread.js` holds the pool the portion is drawn from: **205
portions**, so a reader receives a different one every day for over half a
year before any comes round again — and the cycle only restarts once every
one of them has been served. The card itself says nothing about this; it just
shows the day's portion.

**A portion is a passage, never a lone line.** A single verse lifted out of
its paragraph is often a fragment ("and your ears hear a word behind you …")
or a saying with nothing around it to say what it means. So a verse that
qualifies is only a seed: every two-to-four-verse window around it is
considered, the one that reads best as a whole is served, and a seed with no
clean paragraph around it is dropped rather than served bare. That is why the
pool is a few hundred passages rather than a few hundred more bare lines.

It is generated by `scripts/build_daily_bread.py`, which reads every verse of
the canon and keeps the ones that stand on their own as encouragement. The
whole canon is 48,007 verses; most of them are narrative, law, genealogy or
judgement that need their chapter around them, so the script keeps only what
a reader can be handed cold:

- drawn from the books that speak to the reader — Tehillim, Mishle, Iyoḇ,
  Qoheleth, Dabarim, all the Prophets (Yashayahu, Yirmayahu …), all the
  Messianic writings (Mattithyahu, Mark, Luke, Yahuchanon …) and the wisdom
  books of the apocrypha;
- a complete thought: long enough to stand alone, short enough to take in,
  landing on a full stop;
- a paragraph, judged as a whole and not merely as the verse at its heart:
  it begins where a sentence begins, ends where the thought lands, and every
  verse in it is as clean as the seed;
- carrying a real note of encouragement, and none of the hard matter that
  needs its chapter — with the exception of a verse that overturns it
  ("I fear no evil", "shall not perish"), which is exactly what a portion is
  for;
- no scenes: a verse naming several people and moving them about is a story,
  not a portion.

Each is tagged with one of sixteen themes (refuge, comfort, strength, hope,
mercy, shalom …). The 98 hand-written portions keep their own reflections;
the rest are given the reflection whose turn it is that day from their
theme's bank, so the same verse read years apart is not framed the same way
twice. Only references are stored — the verse text is read from
`assets/text/` at run time, so a portion can never drift from the canon.

Regenerate after any change to the rules or the text:

```bash
python3 scripts/build_daily_bread.py
```

## Marking text

**Touch any verse** and a small menu opens where you touched, with two
options: **✎ Mark Text** and **▶ Start Reader**. Nothing happens until you
choose — touching a verse never starts the reader on its own.

- **Mark Text** keeps the whole verse. To keep just a phrase, select the
  words first and the same menu appears for the selection.
- **Start Reader** begins reading aloud from that verse.
- Touching an existing highlight offers **✕ Remove Mark** and **Start
  Reader**.

Marked passages are highlighted in gold and gathered in the Marked text panel
on the home page. Marks work in verses and in the long-form prose books, may
span divine names, and merge when they overlap.

Marks are stored in your browser's `localStorage`, exactly like bookmarks —
nothing is sent anywhere. They are included in the home page's **Export** file,
so they move with your bookmarks between devices or browsers.

## Reading features

Each chapter page includes a **🔊 Read aloud** player. It uses the browser's
built-in speech engine (the Web Speech API) and the voices already installed on
your device, so it needs **no internet, no account, and no external service** —
it works the same offline as online, including inside `besorah-offline.html`.

- **Read / Pause / Stop** the current chapter.
- Each verse is **highlighted and scrolled to** as it is spoken.
- **Touch any verse** for a menu offering **Start Reader** (read from there)
  or **Mark Text** — the reader never starts on its own from a touch.
  Touching the verse *number* still toggles a bookmark, as before.
- A **speed slider** and **voice picker** let you tune the narration; your
  choices are remembered on your device (`localStorage`) and never leave it.
  The same settings are on the home page under **Choose your reader**.
- The player defaults to the **best-sounding voice** your device offers
  (preferring "natural"/"neural"/enhanced voices) until you pick another.

**Pronunciation** lives in `assets/pronunciation.js`. Generic device voices have
no idea what to do with "Ya'aqoḇ" or "Yahrushalayim", so the player feeds the
speech engine a **phonetic respelling** — the text on screen is never changed,
only what is spoken. Three layers, in order:

1. a **lexicon** of 430+ respellings covering the vocabulary that actually
   occurs in these books, written as hyphenated syllables ("yah-oo-wah",
   "meez-beh-akh") because every engine treats a hyphen as a syllable break;
2. **affix rules** so possessives, Hebrew plurals and the welded "ha-" article
   resolve through their stem (`mizbe'achot`, `Aluahim's`, `haMashiach`);
3. **orthographic rules** for the long tail — ḇ→v, ḥ/ḵ→kh, ĕ→e, q→k, the ayin
   mark dropped, and the characteristic endings (-yahu, -im, -oth) spelled the
   way an English voice reads them.

Together they cover **93% of every set-apart word spoken across the canon**;
`python3 scripts/sweep_text.py` reports that figure and names the most common
words still falling through to the rules, so the lexicon can be extended where
it matters. To refine one pronunciation, edit its line in
`assets/pronunciation.js` and rerun `build_offline.py`.

**Punctuation is never spoken.** Voices differ wildly in what they read out —
some announce "slash", "dash", "asterisk", even "comma" — so every mark is
taken out of the string handed to the engine. The pauses survive, because
they do not come from the marks: the player has already cut the passage into
sentence-sized utterances, and the gap between two utterances is what a
listener hears as the end of a sentence. A hyphen becomes a space rather than
vanishing, since it is what separates the syllables of a respelling.

Voice quality still depends on the voices your operating system provides. If a
chapter has no extractable text, the player hides itself for that chapter.

## Keeping the text clean

The canon is extracted from typeset PDFs, and extraction leaves scars: a word
split across a column break ("command ments"), a word welded to its neighbour
("becausethey"), or a verse number the typesetter printed inline — `[19]`, which
the scanner reads as `[19J` — sitting in the middle of a sentence.

`assets/words.js` is the single place where the correct form of a word is
recorded (`JOINS`, `SPLITS`, `TYPOS`), and `scripts/sweep_text.py` reads those
same tables so the data and the site can never disagree:

```bash
python3 scripts/sweep_text.py            # audit all 104 books (exit 1 on issues)
python3 scripts/sweep_text.py --fix      # repair, then report every change
python3 scripts/sweep_text.py --verbose  # list each issue individually
node scripts/check_render.js             # render all 48,007 verses, fail on anything visible
python3 scripts/check_words_parity.py    # prove words.js and the sweeper agree
```

`check_render.js` is the exhaustive check: it runs every verse through the
same repair and escaping the chapter page uses, then fails on a stray
bracket, asterisk, minus sign, verse marker, unescaped tag, scanner quote
scar, doubled space or empty render. `check_words_parity.py` runs both
implementations of the rules — the browser's and the sweeper's — over every
verse and fails if they ever differ, which is what keeps the page and the
data in step.

### Nothing may go missing

A scar a reader can see is one thing; a verse that never arrived is
another. Two checks answer for the second, and they answer differently, so
both are needed.

```bash
python3 scripts/find_missing_text.py              # every book against its PDF
python3 scripts/find_missing_text.py adam-eve-1   # one or more books
python3 scripts/find_missing_text.py --all        # keep the page apparatus too
```

`find_missing_text.py` re-reads each book's own pages out of the source PDF,
runs that raw English through the same transliteration the reader sees so
the two sides speak one vocabulary, and then asks of every word on the page:
does it sit inside any run of five consecutive words that also appears
anywhere in `assets/text/`? Words that fail are gathered into runs, and a run
of ten or more is text the extractor dropped. The comparison is made against
the whole canon rather than the one book, because the page a book ends on
carries the opening of the next — that opening is not missing, it is in the
neighbouring file. Chapter headings, running headers and page numbers are
counted but not printed: they are on the page, and the extractor is right to
leave them off it.

The check has one blind spot, and it is instructive. Luke 10:27 went missing
for a while without this script noticing, because the words of the Great
Commandment also stand in Mattithyahu and Mark — the five-gram matched
there. What caught it was the second check, on structure rather than
wording: a chapter whose verse numbers skip, or a verse that ends on a
dangling "and", is a verse that has been swallowed. `sweep_text.py` reports
inline markers; the numbering itself is worth reading whenever a book is
re-extracted.

Between them the two found, and the extractors now recover:

| Where | What had gone |
|---|---|
| Prayer of Azariah 29-68 | the whole Song of the Three Young Men — the book stopped at "praised and esteemed and baruk Aluahim in the furnace, saying:" and said no more |
| The Testaments of the Twelve Patriarchs | every testament's opening sentences, and a versification that cut verses off mid-sentence |
| Luke 10:26-27 | the Great Commandment, lost to a verse number the volume itself misprints |
| Ḥanoḵ (Ethiopic) 49:1, 52:1, 102:1 | chapter openings whose marker the scanner read as a letter |
| Yoḇelim 10:21, 18:13, 25:13, 35:20, 46:1 | lines dropped at a number the sequence could not take |
| Adam & Ḥawwah 1 3:6 | "…these were 5,000 and 500 years; and how One would then come and save him and his descendants" |
| Adam & Ḥawwah 2 13:13 | Lemeḵ and the young shepherd, dropped over a misprinted verse number |

The apocryphal books add a fourth kind of scar, because they were set from
scholarly editions rather than from the Besorah plates. The Torah, the
Prophets, the Writings and the Messianic books contain **no** brackets, no
asterisks and no minus signs at all; those books arrived with 417 brackets,
131 minus signs and 48 asterisks between them. `words.js` names each one:

| Glyph | What it was | What is done |
|---|---|---|
| `[ ]` `{ }` | a translator's insertion, often left unbalanced because the pair straddles a verse | the words stay, the brackets go |
| `−` | a minus sign standing in for a hyphen (`hard−hearted`) or a dash (`Ḥanoḵ−for he had shown`) | hyphen inside a compound, em dash before a function word |
| `*` `**` | a footnote mark | the mark goes; a note behind it is kept and shown as a footnote |
| `/'` `/,` `./I` | a closing quote the scanner broke apart (`"Yea, lady/' I said"`) | the quote is restored — a slash between two words, `language/lip`, is a real alternative and is left alone |
| `[4S]` `[SO]` | a verse number whose digits were read as letters | un-mangled, then promoted into a real verse |
| `6` | a verse number with no brackets at all, left mid-sentence where the PDF wrapped it into the middle of a line | promoted into a real verse when it continues the chapter's numbering — never stripped, because a bare number is more often part of the reading (`5,000 and 500 years`) |
| `--` `—` | a dash typed as two hyphens, 135 times | the en dash the rest of the canon uses (1,358 times against a single em dash) |

### Names

The books were extracted from editions that did not agree with each
other, so the same name arrived spelled more than one way — Zeḵaryah
beside Zeḵaryahu, Shemu'al beside Shemu’al with a different apostrophe.
The `NAMES` table in `words.js` settles each one, and it is applied to
the book names in `assets/index.json` at the same time.

Two patterns run through it. **The first vowel is an a, not an e:**

| Was | Now |
|---|---|
| Yeshayahu | Yashayahu |
| Yirmeyahu | Yirmayahu |
| Melaḵim | Malaḵim |
| Shemoth | Shamoth |
| Bemiḏbar | Bamiḏbar |
| Deḇarim | Daḇarim |
| neḇi'im, Nebi'im | naḇi'im, Nabi'im |
| Ruach haQodesh | Ruach HaQadash |

**Qodash for the place, Qadash for the verb.** The two senses of the one
root are kept apart, so a reader can tell at a glance whether a verse is
naming a place or doing something:

| Sense | Reads | Count |
|---|---|---:|
| the place | **Qodash (Set Apart Place)** | 271 |
| the place, innermost | **Qodash haQodashim (Most Set Apart Place)** | 21 |
| the verb, and the adjective from it | **qadash (Set Apart)** | 965 |
| the ones set apart | **qadashiyms (Set Apart Ones)** | 145 |
| the One | **qadash (Set Apart One)** | 79 |
| the Ruach | **Ruach HaQadash** | 134 |

**And the theophoric ending is Al** (אֵל), the singular root behind
Aluahim, capitalised because it is the Name inside the name:

| Was | Now |
|---|---|
| Shemu'ĕl | Shamu'Al |
| Yeḥezq'ĕl | Yahazq'Al |
| Dani'ĕl | Dani'Al |
| Yo'ĕl | Yo'Al |

Three more take the long form of the theophoric *-yahu*: **Oḇadyahu**,
**Tsephanyahu**, **Zaḵaryahu**.

A book's id is its file name and its place in every link, so the ids
followed the names — `yeshayahu` became `yashayahu`. Anything a reader
had already saved (a bookmark, a marked passage, "continue reading")
still holds the old id, and so does any link they shared. **`assets/besorah-ids.js`**
keeps every old id for good: the three pages resolve through it before
they look a book up, and `besorah-marks.js` runs the saved state through
it once on load. A link to `?id=zekaryah` still opens ZAḴARYAHU.

### House style

The Torah, the Prophets, the Writings and the Messianic writings contain no
"holy", no "glory", no "sacred", no "saints", no "sanctify", no "ungodly",
no "cross", no "hell" — not one occurrence between them. The apocryphal
books were set from other editions and arrived carrying the church words,
so the `HOUSE` table in `words.js` brings all 104 books into one style.

The canon's own word for what is set apart is **qadash**, its plural
**qadashiyms**, and both now stand everywhere with the English alongside in
brackets so no reading is lost:

| Was | Now | Count |
|---|---|---:|
| holy, sacred, hallowed, sanctified, consecrated, set-apart | qadash (Set Apart) | 965 |
| holy place | Qodash (Set Apart Place) | 271 |
| holy ones, saints | qadashiyms (Set Apart Ones) | 145 |
| Holy One, saint | qadash (Set Apart One) | 79 |
| holy of holies | Qodash haQodashim (Most Set Apart Place) | 21 |
| Holy Spirit, Set-apart Ruach | Ruach HaQadash | 134 |

Yashayahu 6:3 reads *"Qadash (Set Apart), qadash (Set Apart), qadash (Set
Apart) is (YAHUAH) HWHY of hosts"*. The bracket is for the eye: the reader
strips exactly these glosses before speaking, so it says **kah-dahsh**, not
"qadash Set Apart", while every other parenthesis in the canon still speaks.

The rest, each one what the main books already say in the parallel place:

| Was | Now | Where the main books say it |
|---|---|---|
| glory, glorify, glorious | esteem, esteemed | Romans 3:23, Yahuchanon 17:1 |
| glory in, glorying | boast in, boasting | 1 Corinthians 1:31 |
| ungodly, godless, impious | wicked | Romans 5:6, Yahudah 1:15 |
| unholy | profane | the canon's own opposite of qadash |
| godly | chasid (Faithful) | chasid (חָסִיד), faithful, devoted |
| godliness, piety, devout | reverence, reverent | 1 Timothy 2:2, Titus 2:12 |
| majesty | Greatness | Ibrim 8:1, "the throne of the Greatness" |
| majestic | splendid | Yashayahu 4:2, "splendid and esteemed" |
| honour (verb) | respect | Shamoth 20:12, 1 Kepha 2:17 |
| honour (noun), honourable | esteem, esteemed | Ibrim 5:4, Mishle 3:9 |
| dishonour | disrespect | Romans 1:24, 2:23 |
| divinity, deity, godhead | Aluahim | אֱלֹהִים, with Al and Aluah its roots |
| divine (adjective), Godlike | Mighty-like | 2 Kepha 1:3 |
| cross | stake | Mattithyahu 16:24, Philippians 2:8 |
| crucified, crucify | impaled, impale | "impaled" 48 times, "crucified" never |
| hell | Sheol | the verses gloss it themselves — "hell (Sheol)" |

Capitalisation is inherited word by word, so "Holy One" becomes "Qadash
(Set Apart One)" rather than losing its capital; names that carry their own
capitalisation are listed in `LOCKED_CASE` so "Set-apart Ruach" resolves to
"Ruach HaQadash" and not "Ruach HAQADASH".

Four things are deliberately left alone: the **Church of the Holy
Sepulcher**, a building with a name; the **verb** "divine" (Mikah 3:11,
"her naḇi'im divine for a price"), which is why the adjective is listed by
its collocations; **"set-apartness"**, which has no single Hebrew noun in
this canon; and the **verb** "set … apart" (Shamoth 19:10), which stays
English because only the adjective and noun take the Hebrew.

**[docs/house-style-report.md](docs/house-style-report.md)** has the full
account: every rendering with its verse evidence, the counts, what survives
a search of all 48,007 verses and why each survivor is correct.

The sweep checks every verse of every book for inline verse markers, word
forms, stray glyphs, markup that isn't the whitelisted `<span class="dn">` /
`<span class="hwhy">` / `<span class="fn">`, chapter counts against
`index.json`, verse numbering, empty text and stray whitespace. Inline markers are promoted into **real verses**
when the numbering allows it (this is how Azaryah 1:18–28 and Sirach 15:13–26
were recovered), and `words.js` runs again at render time, so a book
re-extracted from its PDF is still shown correctly.

Entries are added by hand on purpose: no dictionary pass can tell "showbread"
(one word, correct) from "goodlooking" (two words, welded), and joining a pair
whose halves are both ordinary English would wreck a sentence like "dealt with
in precisely the same fashion".

## Running locally

You have three ways to read the canon offline. Pick whichever is easiest.

### Option 1 — Just double-click `besorah-offline.html` (zero setup)

A single self-contained HTML file at the repo root bundles every book
and every chapter inline — including the home page, the Daily Bread pool
and marked text. No web server, no Python, no internet required.
Download the repo, open `besorah-offline.html` in any modern browser,
and read.

The only feature that needs the full repo (rather than just the one
file) is the **PDF** cross-reference link on each chapter — that opens
the matching page from `SCRIPTURE/`, so keep the file alongside the
`SCRIPTURE/` folder if you want PDF lookups.

### Option 2 — One-click launcher (full site, with sticky URLs)

Double-click the launcher matching your OS:

| OS      | File             | Notes                                                |
|---------|------------------|------------------------------------------------------|
| Windows | `start.bat`      | Just double-click.                                   |
| macOS   | `start.command`  | First time: run `chmod +x start.command` once.       |
| Linux   | `start.sh`       | First time: run `chmod +x start.sh` once.            |

Each script starts a local Python HTTP server on port 8000 and opens
the reader in your default browser. Close the terminal window (or
press Ctrl+C) to stop the server. Requires Python 3 to be installed —
the script will tell you where to download it if it's missing.

### Option 3 — Manual server

```bash
python3 -m http.server 8000
# then open http://localhost:8000/
```

## Re-generating from the PDFs

If a source PDF is replaced or updated:

```bash
pip install pypdf pdfplumber english-words
python3 scripts/extract_index.py       # writes scripts/index.json
cp scripts/index.json assets/index.json
python3 scripts/extract_text.py        # writes assets/text/*.json (one file per book)
python3 scripts/reextract_apoc_books.py    # 1/2 Esdras, Maccabees, Baruch, Sirach,
                                       #   Wisdom, Tobit, Judith, Prayer of Azariah
python3 scripts/reextract_apoc3.py     # re-extracts 1 Clements, Shepherd of Hermas
                                       #   and Additions to Esther (marker-based;
                                       #   also syncs their index.json chapter maps)
python3 scripts/reextract_adam_eve.py  # both books of Adam and Ḥawwah
python3 scripts/reextract_testaments.py    # the Twelve Patriarchs
python3 scripts/transliterate.py       # applies CLAUDE.md Hebrew-roots transliterations
python3 scripts/fix_broken_words.py    # repairs words split across PDF line breaks
python3 scripts/verify_transliteration.py  # checks divine names are wrapped & no Hebrew "disappeared"
python3 scripts/sweep_text.py --fix    # verse markers, word forms, markup, whitespace
python3 scripts/find_missing_text.py   # nothing printed in the PDFs was left behind
python3 scripts/build_offline.py       # rebuilds besorah-offline.html
```

### Re-extracting one book

`extract_text.py`, `transliterate.py` and `reextract_apoc_books.py` each take
book ids, so a single book can go round the loop without disturbing the other
103:

```bash
python3 scripts/extract_text.py luke        # ENGLISH text for one book
python3 scripts/transliterate.py luke       # then the Hebrew-roots pass
python3 scripts/fix_broken_words.py         # (reads the whole corpus, writes what changed)
python3 scripts/sweep_text.py --fix
```

Name the ids rather than rebuilding everything. The transliteration passes are
**not** idempotent — run over a book that has already been through them, the
`Ĕl → Al` prefix rule takes a second bite — so a finished book must only be
transliterated again if it has just been re-extracted in English.

To change what the Daily Bread serves, edit `assets/daily-bread.json` — each
entry is a book id, chapter, verse range, theme and reflection; the verse text
itself is always read from `assets/text/`, so a portion can never drift from
the canon. Rerun `build_offline.py` afterwards to refresh the offline edition.

`verify_transliteration.py` cross-checks the rendered text against the
CLAUDE.md mapping tables (imported from `transliterate.py`): it fails if a
divine name is left unwrapped, an anglicised source name survives, or markup
is corrupted. Run it after any text change; `--fix` wraps the safe misses.

```bash
python3 scripts/verify_transliteration.py        # report (exit 1 on any issue)
python3 scripts/verify_transliteration.py --fix  # wrap unambiguous divine names
```
