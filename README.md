# Scripture of All Truths — Bereshith to Revelation, with the Apocrypha

A static web reader for the canon, built directly from the source PDFs in `SCRIPTURE/`.
Each chapter has its own dedicated page that **renders the verse text extracted from
the original PDF in PDF order**, so verse numbering and chapter arrangement match the
source. A "PDF" link on each chapter page lets you cross-reference the original
typesetting. Hebrew transliterations (BERĔSHITH, SHEMOTH, YAHUSHA, …) are used in all
navigation.

## Structure

```
index.html            # Book table of contents (102 books grouped by section)
book.html             # Chapter index for a single book (?id=<bookid>)
chapter.html          # Renders verses for a chapter (?id=<bookid>&ch=<n>)
assets/
  style.css           # Site theme
  index.json          # Book → chapter → PDF page mapping
  text/<bookid>.json  # Extracted verses per book (generated)
SCRIPTURE/
  *.pdf               # Original source PDFs (do not edit)
scripts/
  extract_index.py    # Builds assets/index.json by scanning the PDFs
  extract_text.py     # Builds assets/text/*.json by extracting verse text
```

## Sections covered

- **Torah** (5 books) — Bereshith, Shemoth, Wayyiqra, Bemidbar, Debarim
- **Nebi'im** (22 books) — Yahusha through Mal'aki
- **Kethubim** (12 books) — Tehillim, Mishle, Iyob, … 2 Dibre haYamim
- **Messianic Writings** (27 books) — Mattithyahu through Ḥazon (Revelation)
- **Apocryphal Books** (2) — Ḥanok (Enoch), Yashar (Jasher)
- **Testaments of the Twelve Patriarchs** (12)
- **Ethiopic & Eastern Apocrypha** (22) — 1–4 Maccabees, Tobit, Judith, Sirach,
  Wisdom, Baruch, Jubilees, 1 Enoch, 1 Clements, Shepherd of Hermas, …

Total: **102 books**.

## Running locally

PDFs cannot be embedded from `file://` URLs in most browsers. Serve with:

```bash
python3 -m http.server 8000
# then open http://localhost:8000/
```

## Re-generating from the PDFs

If a source PDF is replaced or updated:

```bash
pip install pypdf
python3 scripts/extract_index.py    # writes scripts/index.json
cp scripts/index.json assets/index.json
python3 scripts/extract_text.py     # writes assets/text/*.json (one file per book)
```
