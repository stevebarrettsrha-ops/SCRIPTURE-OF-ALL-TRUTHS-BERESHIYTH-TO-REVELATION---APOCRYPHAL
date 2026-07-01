# Text Spacing & Transliteration Audit — Findings and Action Plan

Date: 2026-07-01
Scope: all 104 book JSON files in `assets/text/`, `assets/index.json`,
source PDFs in `SCRIPTURE/`, and the CLAUDE.md transliteration guide.
Branch: `claude/text-spacing-transliteration-audit-5qjch0`

This document lays out **what was found** (read-only diagnostics, no text
was modified) and **the exact steps to take, in order,** to fix it. Each
step has a verification gate so a mistake in one phase cannot silently
flow into the next.

---

## Part 1 — Findings

### A. Spacing between letters and words

The corpus of 47,838 verses was scanned for every class of spacing defect.

| # | Defect class | Count | Where |
|---|---|---|---|
| A1 | Words split by a stray space ("moun tains", "Hol y", "upo n", "child ren") | **79** | mostly Apocrypha: Jubilees 31, Eth. Enoch 8, Hermas 5, Sirach 4; scattered 1–3 per book elsewhere |
| A2 | Space before punctuation ("spoken , saying") | **147** | spread across ~30 books |
| A3 | Truly stranded single letters ("like s moke", "pressure s and", "it is s transferred") | **3** | tehillim 102:3, ibrim 10:33, chanok 16:96 |
| A4 | Leading/trailing whitespace in a verse | **1** | apoc-2esdras 13:6 |
| A5 | Split transliterated name ("Yahru shalayim") | **2** | 2dibre-hayamim 26:9 (+1 more) |
| A6 | Double spaces, tabs, control chars, non-breaking/zero-width spaces, letter-spread ("t h e") | **0** | clean — the earlier U+0014 strip and `fix_broken_words.py` passes held |

Full location list for A1 saved during diagnosis; regenerate any time with
the frequency-based scan described in Step 2 below (joined form attested
≥ 5× in corpus AND at least one fragment attested ≤ 2×).

Notes:
- The 1,352 curly-quote possessives ("father’s house") match naive
  stranded-letter patterns but are **correct** — any fix pass must treat
  `’` (U+2019) and `'` (U+0027) as word characters.
- `(YAHUAH) HWHY` pairs are **intentional** — the paleo-Hebrew
  tetragrammaton annotation rendered by `.hwhy` styling in chapter.html.
  7,126 occurrences, all consistent. Do not "fix".

### B. Transliteration accuracy (vs CLAUDE.md)

The 66-book canon (Torah / Nebi'im / Kethubim / Messianic) is essentially
fully transliterated. Residue is concentrated in the Apocrypha,
Patriarchs, and Apocryphal (companion) sections:

| # | Term left anglicized | Count | Books | CLAUDE.md target |
|---|---|---|---|---|
| B1 | Canaan | 55 | yashar 37, testament-yahudah 6, jubilees 5, judith 2, others | Kena'an |
| B2 | Cain | 32 | adam-eve-2 16, yashar 14, enoch 2 | Qayin |
| B3 | Christ | 7 | testament-benyamin 5, apoc-eth-enoch 2 | Mashiach |
| B4 | Abel | 2 | apoc-eth-enoch 1, chanok 1 | Heḇel |
| B5 | Hebrews / Hebrew (person) | 95 | yashar 72, 4maccabees 8, jubilees 5, others | Iḇri / Iḇrim |
| B6 | holy / Holy | 470 | apocrypha + patriarchs only | canon convention is **"set-apart"** (747× in canon), not CLAUDE.md's "qadash" — see D1 |
| B7 | mercy | 231 | apocrypha + patriarchs only | canon convention is **"kindness"/"compassion"**, not CLAUDE.md's "chesed" — see D1 |

Fully clean (0 residue): Jesus, LORD, the Lord, God, Israel, Jerusalem,
Egypt, Moses, Aaron, David, Solomon, Isaac, Jacob, Abraham, Joseph,
Judah, Elijah, Isaiah, Jeremiah, Noah, Adam, Eve, Enoch, Jordan, Messiah,
Holy Spirit, Passover, Sabbath, heaven, angel, priest, covenant, spirit,
soul, altar, temple, prophet, salvation, judgment, commandment,
Egyptian(s), Israelite(s).

### C. Divine-name styling (`<span class="dn">`)

| Name | Wrapped | Unwrapped | Verdict |
|---|---|---|---|
| Yahuah / YAHUAH | 10,068 | 0 | ✓ complete |
| Aluahim | 6,026 | 0 | ✓ complete |
| Mashiach | 606 | 0 | ✓ complete |
| Yahusha | 1,005 | 326 | ✓ correct — all 326 verified to be the **human** Joshua (book of Yahusha 168, Yashar 97, Torah/history references, Luke 3:29 genealogy, Acts 7:45, Ibrim 4:8, Sirach 47:1, 1 Clem 12:2 "son of Nun") |
| HWHY | 0 (uses `.hwhy`) | 7,126 | ✓ intentional paleo-Hebrew annotation |

### D. CLAUDE.md guide vs corpus discrepancies (decide, don't auto-fix)

The corpus is internally consistent but diverges from CLAUDE.md in a few
places. These need a **policy decision** (update CLAUDE.md, or migrate the
corpus) before any bulk replacement is run:

| # | CLAUDE.md says | Corpus uses (consistently) |
|---|---|---|
| D1 | holy → qadash; mercy → chesed | canon uses "set-apart" (747×) and "kindness/compassion"; qadash/chesed appear 0× |
| D2 | Jerusalem → Yerushalayim | **Yahrushalayim** 1,032×; Yerushalayim 0× |
| D3 | Isaiah → Yashayahu | index/book uses **YESHAYAHU** |
| D4 | Daniel → Danial / Daniyal | index uses **DANI'ĔL** |
| D5 | Revelation → "Revelation" | index uses **ḤAZON** |
| D6 | Jubilees → "Jubilees" | index uses **YOḆELIM** |
| D7 | salvation → "yasha" (pron. "yeh-shoo-ah") | guide is internally inconsistent (yasha vs yeshuah); corpus has 0 anglicized "salvation" |

Recommendation: the corpus convention wins (it matches the printed
Besorah PDFs); update CLAUDE.md accordingly. D2's spelling
"Yahrushalayim" is 1,032:0 — changing it would be a mass edit against
the source PDFs.

### E. Book completeness vs PDFs

All 104 books present in `assets/index.json` + `assets/text/` with correct
section assignments and chapter counts (spot-checked: Bereshith 50,
Tehillim 150, Eth. Enoch 108, Hermas 114, Yashar 91). The repo already has
`scripts/audit_text.py` which samples 3 verses per chapter against the
source PDF page ranges — it should be re-run as the final gate (Step 7).

---

## Part 2 — Action plan (steps, in order)

**Step 0 — Freeze a baseline.**
Work only on branch `claude/text-spacing-transliteration-audit-5qjch0`.
Record `git rev-parse HEAD` and total verse/word counts per book so every
later step can prove it changed only what it claimed.
*Gate: baseline counts file committed.*

**Step 1 — Fix the 6 hand-verifiable one-offs first (A3 + A4 + A5).**
Three stranded letters, one trailing-space verse, two "Yahru shalayim"
splits. These are individually reviewed edits, not bulk regex — do them
by hand against the PDF text and commit separately.
*Gate: re-run the stranded-letter and name-split scans → 0 hits.*

**Step 2 — Fix the 79 split words (A1).**
Extend `scripts/fix_broken_words.py`'s corpus-attestation pass (joined
form ≥ 5×, fragment ≤ 2×) or apply the generated list directly. Every
merge must be reviewed against the list before writing — the stoplist and
proper-noun traps in the existing script exist because naive joins
corrupt text ("Aram is" → "Aramis").
*Gate: re-run the split-word census → 0 candidates; total word count per
book decreases by exactly the number of merges in that book; no verse
text changed outside listed locations (diff review).*

**Step 3 — Fix the 147 space-before-punctuation cases (A2).**
Single safe regex on text segments outside HTML tags:
`\s+([,.;:!?])(?=\s|$|”|’)` → `\1`. Curly quotes must be handled as
closers, and ellipses / em-dash spacing left alone.
*Gate: re-scan → 0; word counts unchanged.*

**Step 4 — Decide the D-table policy (owner decision).**
Confirm: corpus conventions (set-apart, kindness, Yahrushalayim,
Yeshayahu, Dani'ĕl, Ḥazon, Yoḇelim) are canonical → update CLAUDE.md
tables to match, so future extraction/transliteration passes don't
"correct" the corpus in the wrong direction. If instead CLAUDE.md is
canonical, Step 5's mapping changes accordingly (and D2 alone touches
1,032 verses).

**Step 5 — Transliterate the apocrypha residue (B1–B7).**
Run `scripts/transliterate.py`'s mapping over ONLY the affected books
with whole-word, case-aware replacements:
Canaan→Kena'an, Cain→Qayin, Abel→Heḇel, Christ→Mashiach (wrap in
`<span class="dn">`), Hebrew(s)→Iḇri/Iḇrim, holy→set-apart,
mercy→kindness (or per Step 4 decision).
Caveats: "Cain" must not touch words like "Cainan" (word boundaries);
"Christ" in testament-benyamin refers to the Messiah (verify each of the
7); "holy" replacements must preserve case ("Holy"→"Set-apart").
*Gate: `scripts/verify_transliteration.py` passes; anglicized-residue
scan → 0 for the agreed mapping.*

**Step 6 — Rebuild derived artifacts.**
`assets/text/*.json` is the source of truth; `besorah-offline.html` (9 MB)
inlines it. Re-run `scripts/build_offline.py` so the offline bundle picks
up every fix.
*Gate: offline build byte-diff shows only the expected verse changes.*

**Step 7 — Full verification sweep (the exit gate).**
1. `scripts/verify_text.py` — extracted text still matches PDFs.
2. `scripts/audit_text.py` — 3-verses-per-chapter PDF sampling → all OK.
3. `scripts/verify_transliteration.py` — markup integrity, no
   untransliterated names, dn-span coverage.
4. Re-run the whitespace scan from Part 1A → all six defect classes at 0.
*Gate: all four green before merge.*

**Step 8 — Commit discipline.**
One commit per step (1, 2, 3, 5, 6), each naming the defect class, count
fixed, and books touched, so any regression bisects to a single pass.

---

## Appendix — diagnostic queries used

All scans strip HTML tags first, treat `’`/`'` as word characters, and
run per-verse over `assets/text/*.json`:

- Split words: adjacent pair (a, b) where corpus-freq(a+b) ≥ 5 and
  min(freq(a), freq(b)) ≤ 2.
- Stranded letters: `\w (s) [a-z]{3,}` and single non-a/I letters
  bounded by spaces, excluding apostrophe contexts.
- Whitespace: `  +`, `^\s|\s$`, `[\x00-\x1f\x7f-\x9f]`, Unicode
  space/format classes, `(?:[A-Za-z] ){3,}[A-Za-z]` letter-spread.
- Punctuation: `\s+[,.;:!?](?=\s|$)`.
- Residue: whole-word case-aware search for every English term in the
  CLAUDE.md tables.
- dn coverage: name occurrences inside vs outside `<span class="dn">`.
