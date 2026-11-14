#!/usr/bin/env python3
"""
restore_source_defects.py

The printed sources themselves carry a handful of defects that no parser can
read around: a verse number the volume never printed (so two verses run
together), a verse printed out of place, and a few verses whose text the
printing omitted outright. This script holds each such repair, verse by
verse, and applies it idempotently after extraction and transliteration.

Three kinds of repair, in honesty order:

  SPLITS   — the verse's words are all present, only the printed number is
             missing or garbled; the text is cut where the number belongs.
  INSERTS  — the verse's words are printed in the source, but somewhere a
             parser cannot bind them (out of order, marker destroyed); the
             text is taken verbatim from the source page.
  SUPPLIES — the printing omits the verse altogether; the verse is supplied
             in the edition's own voice and marked with a footnote saying
             so, because a reader must be able to tell supplied text from
             the source's.

Run after transliterate.py; safe to run any number of times:

    python3 scripts/restore_source_defects.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reextract_testaments as _T  # noqa: E402  (verse snapping)

ROOT = Path(__file__).resolve().parent.parent
TEXT_DIR = ROOT / "assets" / "text"

FN = ' <span class="fn">Supplied — the printed source omits this verse.</span>'
FN_RESTORED = (' <span class="fn">Restored — the scan of the printed source '
               'garbled this verse.</span>')

# (book, chapter, verse-to-split, text of the NEW verse that begins where the
# split lands; the remainder stays with the original verse)
SPLITS = [
    # The Besorah prints Luke 21:1-2 as one verse — the "2" never made it to
    # the plate ("…into the treasury and He saw a certain poor widow…").
    ("luke", "21", 1, 2, "and He saw a certain poor widow putting in two mites."),
    # Yirmayahu 51:1-2, the same fault ("…My opponents. And I shall send
    # winnowers to Baḇal…").
    ("yirmayahu", "51", 1, 2,
     "And I shall send winnowers to Baḇal, who shall winnow her and empty "
     "her land. For they shall be against her all around, in the day of evil."),
    # Chanok 9:31's marker is set as "3l" — the scan's l for 1.
    ("chanok", "9", 30, 31,
     "For wisdom is poured out like water, and esteem faileth not before "
     "Him for evermore."),
]

# Splits where the missing verse's words are already inside the previous
# verse, behind a marker the scan garbled — "67" left inline, "n" for 11,
# "S" for 8. The verse is cut where the print's own marker sits; the marker
# itself is removed from the reading. `head_n` renumbers the head where the
# print gave one number to two verses' text (Yoḇelim 19:26-27).
SPLITS2 = [
    dict(book="yashar", ch="23", src=66, new=67, marker="67",
         probe="O Yahuah, thou art a merciful and compassionate King"),
    dict(book="yashar", ch="63", src=23, new=24, marker="24",
         probe="O Yahuah Aluahim of A\u1e07raham and Yahts\u1e25aq my ancestors"),
    dict(book="apoc-jubilees", ch="19", src=24, new=25,
         probe="And these shall serve to lay the foundations"),
    dict(book="apoc-jubilees", ch="19", src=27, new=27, head_n=26,
         probe="\"Ya'aqo\u1e07, my beloved son"),
    dict(book="apoc-jubilees", ch="32", src=10, new=11, marker="n",
         probe="In its year shall the seed be eaten"),
    dict(book="apoc-jubilees", ch="41", src=10, new=11, marker="n",
         probe="She said to him, \"Give me my pay"),
    dict(book="apoc-jubilees", ch="48", src=7, new=8, marker="S",
         probe="Prince Mastema stood against you"),
]

# The scan destroyed the middle of this verse (only "…a sevenfold crop"
# survives); the print carries it, and the wording is the RSV the volume is
# set from. The garbage bytes it left in the verse before are cleaned.
RESTORES = [
    ("apoc-sirach", "8", 3,
     "My son, do not sow the furrows of injustice, and you will not reap a "
     "sevenfold crop."),
]
CLEANUPS = [
    ("apoc-sirach", "8", 2,
     "Stay away from wrong, and it will turn away from you."),
]

# Verses that do not belong: the page window of a book's last chapter can
# swallow the tail of the book printed beside it. Each entry names a verse
# to delete, with the place its text actually belongs.
DELETES = [
    # Nahum 3 ends at 19; this "verse 20" is Mikah 7:20, which stands in
    # its own book.
    ("nahum", "3", 20),
]

# (book, chapter, verse number, verse text) — text verbatim from the PDF.
INSERTS = [
    # The Besorah prints Yahazqal 37:18 pages out of place (its words sit
    # between 37:6 and 37:7 in the page flow), so no parser can bind it.
    ("yahazqal", "37", 18,
     "“And when the children of your people speak to you, saying, ‘Won’t "
     "you show us what you mean by these?’"),
    # Mishle 12:13 is printed with its marker clipped to "3" at the column
    # edge; the words are on the page.
    ("mishle", "12", 13,
     "In the transgression of the lips is an evil snare, But the righteous "
     "gets out of distress."),
]

# Words the print carries in the middle or at the end of a verse, set in
# capitals on a line of their own, which the extractor once dropped as a
# page banner. (book, chapter, verse, anchor, words): the words go straight
# after the anchor, verbatim from the source page.
COMPLETES = [
    ("shamoth", "29", 41, "an offering made by fire to",
     ' (<span class="dn">YAHUAH</span>) <span class="hwhy">HWHY</span>–'),
    ("luke", "2", 23, "shall be called qadash (Set Apart) to",
     ' (<span class="dn">YAHUAH</span>) <span class="hwhy">HWHY</span>” –'),
    ("hazon", "17", 5, "BAḆAL THE GREAT,",
     " THE MOTHER OF THE WHORES AND OF THE ABOMINATIONS OF"),
    ("hazon", "19", 16, "a Name written: SOVEREIGN",
     " OF SOVEREIGNS AND MASTER OF"),
    # A line lost where a verse crosses a page or column: the first line of
    # the page after the running header, or one line of a two-column page
    # shuffled into the other column. Verbatim from the source page.
    ("bamidbar", "16", 5, "“Tomorrow morning",
     " (<span class=\"dn\">YAHUAH</span>) <span class=\"hwhy\">HWHY</span> shall make known who is His"),
    ("bereshith", "22", 9, "to the place which",
     " <span class=\"dn\">Aluahim</span> had commanded him and"),
    ("bereshith", "37", 2, "with his brothers.",
     " And the young man was with the sons"),
    ("wayyiqra", "13", 6, "pronounce him clean.",
     " It is a scab and he shall wash his"),
    ("dabarim", "12", 18, "within your gates.",
     " And you shall rejoice before (<span class=\"dn\">YAHUAH</span>) <span class=\"hwhy\">HWHY</span>"),
    ("yahusha", "2", 1, "and Yahriḥo.”",
     " And they went and came to the house"),
    ("yahusha", "10", 34, "to Eḡlon.",
     " And they encamped against it and"),
    ("yahusha", "21", 32, "slayer and",
     " Ḥammoth Dor with its open land and"),
    ("shophetim", "18", 23, "the children of Dan.",
     " So they turned around and said to"),
    ("1shamual", "15", 1, "said to Sha’ul,",
     " “(<span class=\"dn\">YAHUAH</span>) <span class=\"hwhy\">HWHY</span> sent me to anoint you"),
    ("1malakim", "4", 33, "out of the wall.",
     " And he spoke of beasts and of birds"),
    ("1malakim", "7", 40, "and the bowls.",
     " And Ḥiram completed doing all the"),
    ("1malakim", "10", 22, "fleet of Ḥiram.",
     " Once every three years the ships of"),
    ("2malakim", "15", 25, "fifty men of Gil‛aḏ.",
     " So he killed him and reigned in his"),
    ("yashayahu", "33", 6, "and knowledge.",
     " The fear of (<span class=\"dn\">YAHUAH</span>) <span class=\"hwhy\">HWHY</span> – that is His"),
    ("yashayahu", "40", 4, "hill made low.",
     " And the steep ground shall become"),
    ("yirmayahu", "7", 10, "stood before",
     " Me in this house which is called by"),
    ("yirmayahu", "15", 15, "<span class=\"hwhy\">HWHY</span>.",
     " Remember me and visit me and"),
    ("habaqquq", "2", 6, "and say,",
     " ‘Woe to him who increases what is"),
    ("tehillim", "3", 7, "O my <span class=\"dn\">Aluahim</span>!",
     " Because You have smitten all my"),
    ("tehillim", "8", 1, "in all the earth,",
     " You who set Your splendour above"),
    ("tehillim", "31", 11, "a dread to my friends;",
     " Those who see me outside flee from"),
    ("tehillim", "37", 35, "in great power,",
     " And spreading himself"),
    ("tehillim", "55", 4, "pained within me,",
     " And the frights of death"),
    ("tehillim", "69", 5, "my foolishness;",
     " And my guilt has not been hidden"),
    ("tehillim", "81", 14, "at once,",
     " And turn My hand against their"),
    ("tehillim", "86", 4, "the being of Your",
     " servant, For to You, O (<span class=\"dn\">YAHUAH</span>) <span class=\"hwhy\">HWHY</span>, I lift up my being."),
    ("tehillim", "99", 6, "upon His Name.",
     " They called upon (<span class=\"dn\">YAHUAH</span>) <span class=\"hwhy\">HWHY</span>"),
    ("tehillim", "107", 42, "see and rejoice,",
     " And all unrighteousness shuts its"),
    ("tehillim", "109", 15, "<span class=\"hwhy\">HWHY</span>,",
     " And let Him cut off their"),
    ("tehillim", "146", 9, "fatherless and widow,",
     " But the way of the wrong ones"),
    ("mishle", "25", 1, "proverbs of",
     " Shelomoh which the men of"),
    ("mishle", "25", 28, "over his ruach",
     " Is like a broken-down city"),
    ("mishle", "31", 3, "to women,",
     " Nor your ways to wiping"),
    ("ekah", "2", 2, "down to the ground.",
     " He has profaned the reign and its"),
    ("nehemyah", "3", 30, "repaired another section.",
     " After him Meshullam son of Bereḵyah"),
    ("2dibre-hayamim", "21", 2, "the sons of",
     " Yahhoshaphat: Azaryahu and Yahḥi’al and Zaḵaryahu and Azaryahu and Miḵa’al"),
    # Defects of the print itself, mended from the parallel the Besorah
    # prints elsewhere. 2 Dibre haYamim 18:33 breaks off at "And he"; its
    # end was set after 18:22, and 1 Malakim 22:34 reads it so.
    ("2dibre-hayamim", "18", 33, "between the joints of his armour. And he",
     " said to the driver of his chariot, “Turn around and take me out of the battle, for I am wounded.”"),
]


# (book, chapter, verse) — a run of verses the source prints with a double
# number, "36(106)", which the extractor did not take for markers, so the
# whole run sits inside one verse. Split at each marker, numbered by the
# number in brackets (2 Esdras 7 continues 106–140 after the restored
# fragment, as the NRSV prints it).
UNMERGES = [
    ("apoc-2esdras", "7", 105),
]
_DOUBLE_MARK = re.compile(r"\s*\b\d{1,3}\((\d{1,3})\)\s*")

# (book, chapter, verse holding the run, heading) — the extractor lost a
# chapter's opening: Enoch 89:1-8 came out as a second copy of 85:1-8, and
# 89:9 swallowed the rest of 85 with all of 86-88 (printed again in their
# own places) and then the true 89:1-9 behind a "Chapter 89" heading. The
# verses after the heading replace the chapter's opening, by their own
# printed numbers.
REBUILDS = [
    ("apoc-eth-enoch", "89", 9, "Chapter 89"),
]
_INLINE_MARK = re.compile(r"\s*\b(\d{1,2})\s+(?=[A-Z‘“'\"])")

# (book, chapter, verse, wrong, right) — a scan misread inside a verse: a
# page header run into the text ("Yoseph 8. Lumpkin"), or a letter read as
# a digit ("1" for I, "0" for O, "50" for So). Checked against the page.
PATCHES = [
    ("apoc-susanna", "1", 59, "your Yoseph 8. Lumpkin own head", "your own head"),
    ("apoc-hermas", "28", 3, "if 1 can be saved", "if I can be saved"),
    ("apoc-jubilees", "35", 20, "the day 1 die", "the day I die"),
    ("apoc-jubilees", "18", 13, "\" 50 that it is said", "\" so that it is said"),
    ("apoc-1esdras", "7", 4, ". 50 with the consent", ". So with the consent"),
    ("apoc-2maccabees", "4", 29, "while 50 stratus left", "while Sostratus left"),
    ("apoc-sirach", "19", 16, "? 50 a word", "? So a word"),
    ("hazon", "20", 4, "hands.And", "hands. And"),
    ("apoc-jubilees", "1", 19, "'0 <", "'O <"),
    ("apoc-jubilees", "1", 20, "mercy, 0 <", "mercy, O <"),
    ("apoc-jubilees", "12", 21, "heart, 0 my", "heart, O my"),
    ("apoc-jubilees", "25", 13, "him, 0 <", "him, O <"),
    ("apoc-eth-enoch", "84", 2, "you, 0 <", "you, O <"),
    ("apoc-eth-enoch", "84", 5, "now, 0 <", "now, O <"),
    ("apoc-eth-enoch", "84", 6, "servant, 0 <", "servant, O <"),
    ("2dibre-hayamim", "36", 23, "Yahuḏah. whoever is among you", "Yahuḏah. Whoever is among you"),
    ("yaaqob", "4", 8, "to you. cleanse hands, sinners.", "to you. Cleanse hands, you sinners."),
    ("yashayahu", "41", 8, "But you, Yahsra’al,", "But you, <span class=\"dn\">Yasharal</span>,"),
    ("bamidbar", "25", 1, "And Yasra’al dwelt", "And <span class=\"dn\">Yasharal</span> dwelt"),
    ("testament-levi", "9", 8, "w bile yet", "while yet"),
    ("testament-levi", "9", 8, "first -fruits", "first-fruits"),
    ("testament-levi", "9", 8, "sacrifice, wash Of twelve", "sacrifice, wash. Of twelve"),
    # The apocrypha volume is an OCR'd scan: S read as 5 in names, I as 1
    # or l, l as I or L, a closing quote as II or 11, O as a, and words split
    # by a space ("W rite"). Each checked against the page.
    ("apoc-1esdras", "2", 26, "\"1 have read", "\"I have read"),
    ("apoc-1esdras", "7", 1, "Then 5isinnes", "Then Sisinnes"),
    ("apoc-1esdras", "7", 1, "and 5athrabuzanes", "and Sathrabuzanes"),
    ("apoc-1esdras", "8", 1, "son of5hallum", "son of Shallum"),
    ("apoc-1esdras", "8", 54, "kohanim, 5herebiah", "kohanim, Sherebiah"),
    ("apoc-1esdras", "1", 30, "from the battIe,", "from the battle,"),
    ("apoc-1esdras", "1", 30, "line of battIe.", "line of battle."),
    ("apoc-tobit", "1", 18, "if 5ennacherib", "if Sennacherib"),
    ("apoc-tobit", "5", 13, "great 5hemaiah", "great Shemaiah"),
    ("apoc-tobit", "2", 4, "50 before I tasted", "So before I tasted"),
    ("apoc-tobit", "3", 7, "father's maidsJ", "father's maids,"),
    ("apoc-2maccabees", "4", 26, "50 Yason, who", "So Yason, who"),
    ("apoc-2maccabees", "4", 31, "50 the king went", "So the king went"),
    ("apoc-2maccabees", "6", 25, "my oid age", "my old age"),
    ("apoc-2maccabees", "6", 27, "my oid age", "my old age"),
    ("apoc-2maccabees", "7", 11, "back again.11", "back again.\""),
    ("apoc-2maccabees", "11", 30, "Xanthic us", "Xanthicus"),
    ("apoc-4maccabees", "5", 33, "my oid age", "my old age"),
    ("apoc-4maccabees", "5", 36, "my oid age", "my old age"),
    ("apoc-jubilees", "42", 11, "my oId age", "my old age"),
    ("apoc-sirach", "28", 2, "stones, 50 sin i5 wedged", "stones, so sin is wedged"),
    ("apoc-sirach", "25", 13, "grew taIl like", "grew tall like"),
    ("apoc-sirach", "25", 14, "grew taIl like", "grew tall like"),
    ("apoc-sirach", "25", 14, "I grew talL", "I grew tall."),
    ("apoc-sirach", "35", 26, "who wiIl listen", "who will listen"),
    ("apoc-1maccabees", "1", 18, "wounded and felL", "wounded and fell."),
    ("apoc-1maccabees", "1", 33, "their citadeL", "their citadel."),
    ("apoc-2esdras", "7", 132, "\"1 know,", "\"I know,"),
    ("apoc-2esdras", "8", 45, "own creation. II", "own creation.\""),
    ("apoc-2esdras", "8", 46, "said, IIThings", "said, \"Things"),
    ("apoc-2esdras", "8", 62, "like you.1I Then", "like you.\" Then"),
    ("apoc-2esdras", "8", 63, "IIBehold", "\"Behold"),
    ("apoc-2esdras", "11", 45, "littIe wings", "little wings"),
    ("apoc-3maccabees", "1", 9, "excelIence", "excellence"),
    ("apoc-3maccabees", "3", 24, "are iIl disposed", "are ill disposed"),
    ("apoc-wisdom", "2", 22, "blameless souIs", "blameless souls"),
    ("apoc-eth-enoch", "16", 4, "shalom.\"1", "shalom.\""),
    ("apoc-eth-enoch", "52", 2, "soft meta1,", "soft metal,"),
    ("apoc-eth-enoch", "52", 6, "soft meta1,", "soft metal,"),
    ("apoc-hermas", "10", 1, "say 1. \"Listen", "say I. \"Listen"),
    ("apoc-hermas", "30", 1, "and 1 apprehend", "and I apprehend"),
    ("apoc-hermas", "31", 1, "Sir,\" say 1, \"from", "Sir,\" say I, \"from"),
    ("apoc-hermas", "31", 7, "\"1 was quickened", "\"I was quickened"),
    ("apoc-hermas", "35", 1, "say 1. \"But now", "say I. \"But now"),
    ("apoc-hermas", "38", 5, "say 1. \"Aye", "say I. \"Aye"),
    ("apoc-hermas", "46", 1, "\"1 would fain", "\"I would fain"),
    ("apoc-hermas", "58", 1, "\"1 told you", "\"I told you"),
    ("apoc-hermas", "92", 1, "\"H ear,\"", "\"Hear,\""),
    ("apoc-jubilees", "1", 22, "\"1 know their", "\"I know their"),
    ("apoc-jubilees", "1", 27, "\"W rite for", "\"Write for"),
    ("apoc-jubilees", "12", 17, "he said, U All", "he said, \"All"),
    ("apoc-jubilees", "14", 7, "\"1 am <span", "\"I am <span"),
    ("apoc-jubilees", "35", 21, "\"1 will do all", "\"I will do all"),
    ("apoc-jubilees", "35", 26, "\"1 shall do your", "\"I shall do your"),
    ("apoc-jubilees", "43", 11, "\"a my master", "\"O my master"),
    # "Lord" (and once "lord's") said to a man, not to Yahuah, was carried
    # over as the Name: Terah to Nimroḏ, Sarai of Aḇram, Ya'aqoḇ to Ĕsaw,
    # Yahuḏah to Yoseph. Lowercase lord is master (CLAUDE.md rule 3).
    ("apoc-jubilees", "43", 11, "in my <span class=\"dn\">Yahuah</span>'s ear", "in my master's ear"),
    ("yashar", "8", 17, "My <span class=\"dn\">Yahuah</span> and king", "My master and king"),
    ("yashar", "12", 52, "my <span class=\"dn\">Yahuah</span> and king", "my master and king"),
    ("yashar", "15", 17, "my <span class=\"dn\">Yahuah</span> Aḇram", "my master Aḇram"),
    ("yashar", "18", 35, "Not so my <span class=\"dn\">Yahuah</span>,", "Not so my master,"),
    ("yashar", "26", 2, "my <span class=\"dn\">Yahuah</span> Aḇraham", "my master Aḇraham"),
    ("yashar", "26", 28, "That which my <span class=\"dn\">Yahuah</span> has", "That which my master has"),
    ("yashar", "32", 69, "my <span class=\"dn\">Yahuah</span>'s place", "my master's place"),
]

# (book, chapter, verse) — R. H. Charles prints the Testaments' verse numbers
# in the margin, against the LINE a verse begins on, and the scan set them
# inline ("till he was 5 sold to the Ishmaelites. And when Re'uḇen came").
# reextract_testaments.py snaps each number to the nearest sentence break;
# it took only the exact next number, so where the scan lost one (Zebulun
# 4:4) every number after it was refused and the chapter ran together.
# These verses are split with the same snapping, allowing one lost number.
# Where the scan lost a margin number the verses stay together; those gaps
# are listed in audit_structure.py.
MARGIN_SPLITS = [
    ("testament-zebulun", "4", 3), ("testament-dan", "3", 1),
    ("testament-levi", "3", 5), ("testament-levi", "9", 8),
    ("testament-yahudah", "7", 4), ("testament-yahudah", "10", 3),
    ("testament-yahudah", "13", 3), ("testament-issakar", "2", 3),
]
_MARGIN = re.compile(r"\s(\d{1,2})(?:,\s?(\d{1,2}))?(,?)(?=\s)")

# (book, chapter, verse, true ending) — the extractor read past a book's last
# verse into the pages printed after it (a study essay, the "Ten Words" back
# page) and ran them on as part of the verse. Everything after the true
# ending is cut.
TRUNCATES = [
    ("hazon", "22", 21, "qadashiyms (Set Apart Ones). Amĕn."),
    ("2dibre-hayamim", "36", 23, "let him go up!’ ”"),
    # A study note set inside the verse ("This has not been filled yet but
    # this prophesy …") — the editor's voice, not the prophet's.
    ("yashayahu", "11", 11, "from the islands of the sea."),
    # The PRINT sets the end of 18:33 here, after 18:22 (see COMPLETES).
    ("2dibre-hayamim", "18", 22, "has spoken evil concerning you.”"),
    # Page apparatus run on at a verse end: a running head ("IMacA",
    # "Mandate S", "Parables Which He spoke With Me"), a section title page
    # (Chanok's "Book 2: The Parables" ...), a stray margin "3" left by the
    # 9:31 split, and the closing "THE END".
    ("apoc-1maccabees", "3", 60, "so he will do.\""),
    ("apoc-hermas", "32", 4, "walk in this purity.\""),
    ("apoc-hermas", "49", 5, "shall live unto <span class=\"dn\">Aluahim</span>.\""),
    ("chanok", "7", 68, "bless Him for ever."),
    ("chanok", "9", 30, "Ruchot be baruk."),
    ("chanok", "10", 80, "committing sin.\""),
    ("chanok", "19", 152, "seen that vision."),
    ("chanok", "14", 27, "strong before <span class=\"dn\">Yahuah</span> of Ruchot."),
    ("yashar", "91", 17, "<span class=\"dn\">Yahuah</span> be of good courage."),
]

# (book, chapter, verse number, verse text) — the printing omits the verse;
# supplied in the edition's own voice, with the footnote appended.
SUPPLIES = [
    ("mikah", "7", 17,
     "They lick dust like a serpent, they crawl from their holes like "
     "snakes of the earth. They are afraid of "
     '(<span class="dn">YAHUAH</span>) <span class="hwhy">HWHY</span> our '
     '<span class="dn">Aluahim</span>, and they fear because of You.'),
    ("iyob", "24", 21,
     "He treats evil the barren who does not bear, and does no good for "
     "the widow."),
    ("apoc-azariah", "1", 1,
     "And they walked about in the midst of the flames, singing hymns to "
     '<span class="dn">Aluahim</span> and blessing '
     '<span class="dn">Yahuah</span>.'),
    ("apoc-manasseh", "1", 1,
     'O <span class="dn">Yahuah</span> Almighty, '
     '<span class="dn">Aluahim</span> of our fathers, of Aḇraham and '
     "Yahtsḥaq and Ya'aqoḇ and of their righteous posterity;"),
    ("apoc-psalm151", "1", 1,
     "I was small among my brothers, and youngest in my father's house; I "
     "tended my father's sheep."),
    ("apoc-susanna", "1", 1,
     "There was a man living in Baḇal (Baḇylon) whose name was Yoaqim."),
]


def _find_plain(text, probe):
    """Find `probe` in `text` ignoring markup: the divine names inside a
    verse are wrapped in spans, so a plain-words probe must see through the
    tags. Returns the index into the ORIGINAL text, or -1."""
    plain, back = [], []
    for m in re.finditer(r"<[^>]+>|.", text, re.S):
        if not m.group(0).startswith("<"):
            plain.append(m.group(0))
            back.append(m.start())
    j = "".join(plain).find(re.sub(r"<[^>]+>", "", probe))
    return back[j] if j >= 0 else -1


def load(bid):
    p = TEXT_DIR / f"{bid}.json"
    return p, json.loads(p.read_text(encoding="utf-8"))


def save(p, d):
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n",
                 encoding="utf-8")


def main():
    changed = 0
    for bid, cn, src_n, new_n, new_text in SPLITS:
        p, d = load(bid)
        vs = d["chapters"][cn]["verses"]
        if any(v["n"] == new_n for v in vs):
            continue                          # already split
        src = next(v for v in vs if v["n"] == src_n)
        # the tail of the merged verse must carry the new verse's words
        probe = new_text[:40].split("<")[0].strip()
        i = src["t"].find(probe)
        if i < 0:
            print(f"  !! {bid} {cn}:{src_n}: split anchor not found; skipped")
            continue
        head = src["t"][:i].rstrip()
        # drop a garbled marker ("3l") left dangling before the cut
        head = head.rstrip("l1 ").rstrip()
        src["t"] = head
        vs.insert(vs.index(src) + 1, {"n": new_n, "t": new_text})
        save(p, d)
        changed += 1
        print(f"  split {bid} {cn}:{src_n} -> {src_n},{new_n}")

    for e in SPLITS2:
        p, d = load(e["book"])
        vs = d["chapters"][e["ch"]]["verses"]
        head_n = e.get("head_n", e["src"])
        if any(v["n"] == e["new"] for v in vs) and (
                e["new"] != e["src"] or any(v["n"] == head_n for v in vs)):
            continue                          # already split
        src = next(v for v in vs if v["n"] == e["src"])
        i = _find_plain(src["t"], e["probe"])
        if i < 0:
            print(f"  !! {e['book']} {e['ch']}:{e['src']}: probe not found; skipped")
            continue
        head, tail = src["t"][:i].rstrip(), src["t"][i:].strip()
        m = e.get("marker")
        if m and head.endswith(m):
            head = head[:-len(m)].rstrip()
        src["t"] = head
        src["n"] = head_n
        vs.insert(vs.index(src) + 1, {"n": e["new"], "t": tail})
        save(p, d)
        changed += 1
        print(f"  split {e['book']} {e['ch']}:{e['src']} -> {head_n},{e['new']}")

    for bid, cn, n in DELETES:
        p, d = load(bid)
        vs = d["chapters"][cn]["verses"]
        if any(v["n"] == n for v in vs):
            d["chapters"][cn]["verses"] = [v for v in vs if v["n"] != n]
            save(p, d)
            changed += 1
            print(f"  delete {bid} {cn}:{n}")

    for bid, cn, n, text in CLEANUPS:
        p, d = load(bid)
        vs = d["chapters"][cn]["verses"]
        v = next(x for x in vs if x["n"] == n)
        if v["t"] != text:
            v["t"] = text
            save(p, d)
            changed += 1
            print(f"  cleanup {bid} {cn}:{n}")

    for bid, cn, n, text in RESTORES:
        p, d = load(bid)
        vs = d["chapters"][cn]["verses"]
        if not any(v["n"] == n for v in vs):
            at = next((i for i, v in enumerate(vs) if v["n"] > n), len(vs))
            vs.insert(at, {"n": n, "t": text + FN_RESTORED})
            save(p, d)
            changed += 1
            print(f"  restore {bid} {cn}:{n}")

    for bid, cn, n, anchor, words in COMPLETES:
        p, d = load(bid)
        v = next(x for x in d["chapters"][cn]["verses"] if x["n"] == n)
        plain = re.sub(r"<[^>]+>", "", v["t"])
        if re.sub(r"<[^>]+>", "", anchor + words).strip(" –”") in plain:
            continue                          # already whole
        i = v["t"].find(anchor)
        if i < 0:
            print(f"  !! {bid} {cn}:{n}: anchor not found; skipped")
            continue
        i += len(anchor)
        v["t"] = v["t"][:i] + words + v["t"][i:]
        save(p, d)
        changed += 1
        print(f"  complete {bid} {cn}:{n}")

    for bid, cn, n in UNMERGES:
        p, d = load(bid)
        vs = d["chapters"][cn]["verses"]
        v = next(x for x in vs if x["n"] == n)
        parts = _DOUBLE_MARK.split(v["t"])
        if len(parts) < 3:
            continue                          # already split
        v["t"] = parts[0].rstrip()
        at = vs.index(v) + 1
        for num, text in zip(parts[1::2], parts[2::2]):
            vs.insert(at, {"n": int(num), "t": text.strip()})
            at += 1
        save(p, d)
        changed += 1
        print(f"  unmerge {bid} {cn}:{n} -> {len(parts) // 2} verses")

    for bid, cn, n, heading in REBUILDS:
        p, d = load(bid)
        vs = d["chapters"][cn]["verses"]
        v = next(x for x in vs if x["n"] == n)
        i = v["t"].find(heading)
        if i < 0:
            continue                          # already rebuilt
        parts = _INLINE_MARK.split(v["t"][i + len(heading):])
        fresh = {int(k): t.strip() for k, t in zip(parts[1::2], parts[2::2])}
        if sorted(fresh) != list(range(1, n + 1)):
            print(f"  !! {bid} {cn}:{n}: markers {sorted(fresh)}; skipped")
            continue
        for x in vs:
            if x["n"] in fresh:
                x["t"] = fresh[x["n"]]
        save(p, d)
        changed += 1
        print(f"  rebuild {bid} {cn}:1-{n}")

    for bid, cn, n, wrong, right in PATCHES:
        p, d = load(bid)
        v = next(x for x in d["chapters"][cn]["verses"] if x["n"] == n)
        if wrong in v["t"]:
            v["t"] = v["t"].replace(wrong, right, 1)
            save(p, d)
            changed += 1
            print(f"  patch {bid} {cn}:{n}")

    for bid, cn, n in MARGIN_SPLITS:
        p, d = load(bid)
        vs = d["chapters"][cn]["verses"]
        v = next(x for x in vs if x["n"] == n)
        t, last, marks = v["t"], n, []
        for m in _MARGIN.finditer(t):
            nums = [int(m.group(1))] + ([int(m.group(2))] if m.group(2) else [])
            if not (last < nums[0] <= last + 2):
                continue
            marks.append((m.start(), m.end(), nums))
            last = nums[-1]
        if not marks:
            continue                          # already split
        clean, at, pos = "", 0, []
        for a, b, nums in marks:
            clean += t[at:a] + " "
            pos += [(k, len(clean)) for k in nums]
            at = b
        clean = re.sub(r"\s+", " ", clean + t[at:])
        # the same snapping the Testaments extractor uses for every other
        # verse: the nearest sentence boundary, before or after the number
        starts = _T._sentence_starts(clean)
        cuts, floor = [], 0
        for k, i in pos:
            cut = _T._snap(starts, i, floor)
            if cut <= floor:
                continue                      # shares a sentence; no split
            cuts.append((k, cut))
            floor = cut
        bounds = [(n, 0)] + cuts
        new = []
        for i, (k, cut) in enumerate(bounds):
            end = bounds[i + 1][1] if i + 1 < len(bounds) else len(clean)
            new.append({"n": k, "t": clean[cut:end].strip()})
        at = vs.index(v)
        vs[at:at + 1] = new
        save(p, d)
        changed += 1
        print(f"  margin-split {bid} {cn}:{n} -> {[k for k, _ in cuts]}")

    for bid, cn, n, ending in TRUNCATES:
        p, d = load(bid)
        v = next(x for x in d["chapters"][cn]["verses"] if x["n"] == n)
        i = v["t"].find(ending)
        if i < 0:
            print(f"  !! {bid} {cn}:{n}: ending not found; skipped")
            continue
        if v["t"][i + len(ending):].strip():
            v["t"] = v["t"][:i + len(ending)]
            save(p, d)
            changed += 1
            print(f"  truncate {bid} {cn}:{n}")

    for kind, table in (("insert", INSERTS), ("supply", SUPPLIES)):
        for bid, cn, n, text in table:
            p, d = load(bid)
            vs = d["chapters"][cn]["verses"]
            if any(v["n"] == n for v in vs):
                continue
            t = text + (FN if kind == "supply" else "")
            at = next((i for i, v in enumerate(vs) if v["n"] > n), len(vs))
            vs.insert(at, {"n": n, "t": t})
            save(p, d)
            changed += 1
            print(f"  {kind} {bid} {cn}:{n}")
    print(f"{changed} repair(s) applied.")


if __name__ == "__main__":
    main()
