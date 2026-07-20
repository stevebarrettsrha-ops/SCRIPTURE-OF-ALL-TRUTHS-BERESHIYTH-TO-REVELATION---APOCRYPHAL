# Scripture of All Truths — Bereshith to Revelation, with the Apocrypha

A static web reader for the canon, built directly from the source PDFs in `SCRIPTURE/`.
Each chapter has its own dedicated page that **renders the verse text extracted from
the original PDF in PDF order**, so verse numbering and chapter arrangement match the
source. A "PDF" link on each chapter page lets you cross-reference the original
typesetting. Hebrew transliterations (BERĔSHITH, SHEMOTH, YAHUSHA, …) are used in all
navigation.

## Structure

```
index.html            # Book table of contents (104 books grouped by section)
book.html             # Chapter index for a single book (?id=<bookid>)
chapter.html          # Renders verses for a chapter (?id=<bookid>&ch=<n>)
besorah-offline.html  # Standalone single-file reader (open with file://)
start.bat             # One-click launcher (Windows)
start.command         # One-click launcher (macOS)
start.sh              # One-click launcher (Linux)
assets/
  style.css           # Site theme
  besorah-marks.js    # Bookmark + last-read tracking (localStorage)
  besorah-tts.js      # Read-aloud player (browser Web Speech API; offline)
  index.json          # Book → chapter → PDF page mapping
  text/<bookid>.json  # Extracted verses per book (generated)
SCRIPTURE/
  *.pdf               # Original source PDFs (do not edit)
scripts/
  extract_index.py    # Builds assets/index.json by scanning the PDFs
  extract_text.py     # Builds assets/text/*.json by extracting verse text
  transliterate.py    # Applies CLAUDE.md Hebrew-roots transliteration rules
  fix_broken_words.py # Repairs words split by PDF line breaks (e.g. "moun tains" -> "mountains")
  build_offline.py    # Bundles everything into besorah-offline.html
```

## Sections covered

- **Torah** (5 books) — Bereshith, Shemoth, Wayyiqra, Bemidbar, Debarim
- **Nebi'im** (22 books) — Yahusha through Mal'aki
- **Kethubim** (12 books) — Tehillim, Mishle, Iyob, … 2 Dibre haYamim
- **Messianic Writings** (27 books) — Mattithyahu through Ḥazon (Revelation)
- **Apocryphal Books** (4) — Ḥanok (Enoch), Yashar (Jasher), First & Second
  Book of Adam and Eve
- **Testaments of the Twelve Patriarchs** (12)
- **Ethiopic & Eastern Apocrypha** (22) — 1–4 Maccabees, Tobit, Judith, Sirach,
  Wisdom, Baruch, Jubilees, 1 Enoch, 1 Clements, Shepherd of Hermas, …

Total: **104 books**.

## Reading features

Each chapter page includes a **🔊 Read aloud** player. It uses the browser's
built-in speech engine (the Web Speech API) and the voices already installed on
your device, so it needs **no internet, no account, and no external service** —
it works the same offline as online, including inside `besorah-offline.html`.

- **Read / Pause / Stop** the current chapter.
- Each verse is **highlighted and scrolled to** as it is spoken.
- **Click any verse to start reading from there** (clicking the verse *number*
  still toggles a bookmark, as before).
- A **speed slider** and **voice picker** let you tune the narration; your
  choices are remembered on your device (`localStorage`) and never leave it.

Voice quality depends on the voices your operating system provides. If a chapter
has no extractable text, the player hides itself for that chapter.

## Running locally

You have three ways to read the canon offline. Pick whichever is easiest.

### Option 1 — Just double-click `besorah-offline.html` (zero setup)

A single self-contained HTML file at the repo root bundles every book
and every chapter inline. No web server, no Python, no internet
required. Download the repo, open `besorah-offline.html` in any modern
browser, and read.

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
python3 scripts/reextract_apoc3.py     # re-extracts 1 Clements, Shepherd of Hermas
                                       #   and Additions to Esther (marker-based;
                                       #   also syncs their index.json chapter maps)
python3 scripts/transliterate.py       # applies CLAUDE.md Hebrew-roots transliterations
python3 scripts/fix_broken_words.py    # repairs words split across PDF line breaks
python3 scripts/verify_transliteration.py  # checks divine names are wrapped & no Hebrew "disappeared"
python3 scripts/build_offline.py       # rebuilds besorah-offline.html
```

`verify_transliteration.py` cross-checks the rendered text against the
CLAUDE.md mapping tables (imported from `transliterate.py`): it fails if a
divine name is left unwrapped, an anglicised source name survives, or markup
is corrupted. Run it after any text change; `--fix` wraps the safe misses.

```bash
python3 scripts/verify_transliteration.py        # report (exit 1 on any issue)
python3 scripts/verify_transliteration.py --fix  # wrap unambiguous divine names
```
