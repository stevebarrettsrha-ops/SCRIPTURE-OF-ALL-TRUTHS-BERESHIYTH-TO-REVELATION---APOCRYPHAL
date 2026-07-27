// words.js
// How a word must appear on the page.
//
// The canon is extracted from typeset PDFs, and the extraction leaves two
// kinds of scar. A word that straddled a column break arrives split in two
// ("command ments", "sover eign"); a word that sat tight against its
// neighbour arrives welded ("becausethey", "twentyseven"). A third scar is
// the verse marker the typesetter printed inline — "[19]", which the page
// scanner reads as "[19J" — sitting in the middle of a sentence.
//
// This file is the single place where those are named. It is used twice:
//
//   * at build time  — scripts/sweep_text.py reads these tables and repairs
//                      assets/text/*.json, so the data itself is clean;
//   * at render time — BesorahWords.repair() runs over every verse before
//                      it reaches the screen, so anything that slips in
//                      later (or any book re-extracted from a PDF) is still
//                      shown correctly.
//
//   BesorahWords.repair(text)      -> corrected text (HTML markup preserved)
//   BesorahWords.repairPlain(text) -> corrected text, no markup expected
//
// Entries are deliberately explicit rather than clever: an automatic
// dictionary pass cannot tell "showbread" (one word, correct) from
// "goodlooking" (two words, welded), so every correction here was read in
// context first. For the same reason a split whose halves are both ordinary
// English is never listed — joining "with in" would wreck "dealt with in
// precisely the same fashion".
(function (global) {
  "use strict";

  // --- 1. words the extraction split in two ---------------------------
  // Keys are lower-case; the replacement inherits the capitalisation of
  // the first fragment, so "Sover eign" comes out "Sovereign".
  var JOINS = {
    "them selves": "themselves",
    "your selves": "yourselves",
    "him self": "himself",
    "her self": "herself",
    "my self": "myself",
    "our selves": "ourselves",
    "it self": "itself",
    "false hood": "falsehood",
    "sover eign": "sovereign",
    "peopl es": "peoples",
    "gate keepers": "gatekeepers",
    "command ments": "commandments",
    "command ment": "commandment",
    "re joiced": "rejoiced",
    "re joice": "rejoice",
    "trans gression": "transgression",
    "trans gressions": "transgressions",
    "mad est": "madest",
    "right eousness": "righteousness",
    "wilder ness": "wilderness",
    "inherit ance": "inheritance",
    "under standing": "understanding",
    "ever lasting": "everlasting",
    "king dom": "kingdom",
    "to gether": "together",
    "gener ation": "generation",
    "gener ations": "generations",
    "congre gation": "congregation",
    "abomin ation": "abomination",
    "sanctu ary": "sanctuary",
    "offer ing": "offering",
    "offer ings": "offerings",
    "moun tains": "mountains",
    "moun tain": "mountain"
  };

  // --- 2. words the extraction welded together ------------------------
  // Only forms that are wrong in every context appear here; genuine
  // compounds (showbread, herdsmen, watchmen, firstfruits, overnight,
  // seedtime, wholesome …) are deliberately absent.
  var SPLITS = {
    "becausethey": "because they",
    "headshall": "head shall",
    "sharesin": "shares in",
    "richthrough": "rich through",
    "shouldgo": "should go",
    "goodlooking": "good-looking",
    "wellknown": "well-known",
    "likeminded": "like-minded",
    "bowlshaped": "bowl-shaped",
    "selfcontrol": "self-control",
    "fruitbearing": "fruit-bearing",
    "everflowing": "ever-flowing",
    "semiticlanguage": "Semitic-language",
    "twentytwo": "twenty-two",
    "twentyfive": "twenty-five",
    "twentyseven": "twenty-seven",
    "twentyeight": "twenty-eight",
    "twentynine": "twenty-nine",
    "twentysecond": "twenty-second",
    "thirtyfive": "thirty-five",
    "thirtysix": "thirty-six",
    "thirtysecond": "thirty-second",
    "fortyone": "forty-one",
    "fortytwo": "forty-two",
    "fortyfour": "forty-four",
    "fortyfive": "forty-five",
    "fortysix": "forty-six",
    "fiftytwo": "fifty-two",
    "fiftythree": "fifty-three",
    "fiftysix": "fifty-six",
    "sixtyfour": "sixty-four",
    "sixtysix": "sixty-six",
    "seventyfive": "seventy-five",
    "onethird": "one-third",
    "onefifth": "one-fifth",
    "onetenth": "one-tenth"
  };

  // --- 3. plain misreadings -------------------------------------------
  // A scanner reading two glyphs as one. Each was checked against the
  // printed page before being listed.
  var TYPOS = {
    "backfmy": "back my",
    "carefull": "carefully",
    // Digits the scanner read for letters — an S read as 5, an o as 0.
    // Each was checked against its verse.
    "50dom": "Sodom",
    "50stratus": "Sostratus",
    "5halmaneser": "Shalmaneser",
    "5eleucus": "Seleucus",
    "5alu": "Salu",
    // Two glyphs read as one.
    "b~ cause": "because",
    "1£ you": "If you",
    "sellin&": "selling,",
    "sprin&": "spring,"
  };

  // --- 4. house style -------------------------------------------------
  // The Besorah does not use the Latin- and Greek-rooted church words. The
  // Torah, the Prophets, the Writings and the Messianic writings contain
  // no "holy", no "sacred", no "saints", no "sanctify", no "glory", no
  // "cross", no "hell", no "ungodly" — not one occurrence between them.
  // They use set-apart, set-apart ones, esteem, stake, Sheol, wicked. The
  // apocryphal books were set from other editions and arrived carrying the
  // church words, so this table brings them into line, and every entry is
  // what the main books already say in the parallel place.
  //
  // Longer keys are matched first, so "holy of holies" and "holy ones"
  // resolve before the bare word. Capitalisation is inherited word by
  // word, so "Holy One" becomes "Set-apart One".
  var HOUSE = {
    // --- qodesh: the Latin-rooted words for what is set apart ----------
    // "holy" appears 0 times in the Torah, the Prophets, the Writings and
    // the Messianic writings, which use "set-apart" 747 times.
    "holy of holies": "Most Set-apart Place",
    // The church in Yerushalayim is a building with a name; it keeps it.
    "holy sepulcher": "Holy Sepulcher",
    "holy sepulchre": "Holy Sepulchre",
    "most holy": "most set-apart",
    "holy ones": "set-apart ones",
    "holy one": "set-apart one",
    "holy place": "set-apart place",
    "holiness": "set-apartness",
    "holy": "set-apart",
    // sanctify → set apart          (Shemoth 19:10, 1 Corinthians 6:11)
    "sanctification": "set-apartness",
    "sanctified": "set-apart",
    "sanctifies": "sets apart",
    "sanctifying": "setting apart",
    "sanctify": "set apart",
    // consecrate → set apart        (the same qadash)
    "consecration": "setting apart",
    "consecrated": "set-apart",
    "consecrates": "sets apart",
    "consecrate": "set apart",
    // hallowed → set-apart          (Mattithyahu 6:9, Luke 11:2)
    "hallowed": "set-apart",
    "hallows": "sets apart",
    "hallow": "set apart",
    // sacred → set-apart            (no "sacred" anywhere in the canon)
    "sacred": "set-apart",
    // saints → set-apart ones       (Romans 1:7, Ephesians 1:1, Ḥazon 13:7)
    "saints": "set-apart ones",
    "saintly": "set-apart",
    "sainted": "set-apart",
    "saint": "set-apart one",

    // --- eusebeia: reverence, not "godliness" --------------------------
    // The Messianic writings render it "reverence" nine times over
    // (1 Timothy 2:2, 4:7, 4:8, 6:6, 6:11; 2 Kepha 1:3, 1:6, 3:11;
    // Titus 1:1) and "reverently" in Titus 2:12.
    "godliness": "reverence",
    "godly": "set-apart",
    "piety": "reverence",
    "pious": "reverent",
    "piously": "reverently",
    "devoutly": "reverently",
    "devout": "reverent",

    // --- asebeia: wicked, not "ungodly" --------------------------------
    // Romans 5:6 and 4:5, 1 Kepha 4:18, 2 Kepha 2:5 and Yahudah 1:15 all
    // read "wicked"; Romans 1:18 and 11:26 and Titus 2:12 "wickedness".
    "ungodliness": "wickedness",
    "ungodly": "wicked",
    "godlessness": "wickedness",
    "godless": "wicked",
    "impieties": "wickedness",
    "impiety": "wickedness",
    "impiously": "wickedly",
    "impious": "wicked",
    "godlessly": "wickedly",

    // --- doxa: esteem, not "glory" -------------------------------------
    // "glory" appears 0 times in the main books, which use "esteem" 383
    // times (Romans 3:23, Yeshayahu 6:3, Tehillim 19:1, Yahuchanon 1:14)
    // and "esteem" as the verb (Yahuchanon 17:1 "Esteem Your Son").
    // "glory in" is boasting, not esteem — the main books say "boast"
    // (1 Corinthians 1:31, Yehezqel 35:13).
    "glories in": "boasts in",
    "glorying": "boasting",
    "gloried": "boasted",
    "glories": "splendours",
    "gloriously": "with esteem",
    "glorious": "esteemed",
    "glorified": "esteemed",
    "glorifies": "esteems",
    "glorifying": "esteeming",
    "glorify": "esteem",
    "glory": "esteem",

    // --- divine → Mighty-like ------------------------------------------
    // 2 Kepha 1:3-4 reads "His Mighty-like power" and "partakers of the
    // Mighty-like nature". The main books use "divine" only as the verb
    // for divination (Mikah 3:11, Yeḥezqel 13:9), so the adjective is
    // listed by its collocations and the verb is left untouched.
    "divine ruach": "Mighty-like ruach",
    "divine justice": "Mighty-like justice",
    "divine law": "Mighty-like law",
    "divine laws": "Mighty-like laws",
    "divine fire": "Mighty-like fire",
    "divine nature": "Mighty-like nature",
    "divine instructions": "Mighty-like instructions",
    "divine instruction": "Mighty-like instruction",
    "divine intervention": "Mighty-like intervention",
    "divine matters": "Mighty-like matters",
    "divine life": "Mighty-like life",
    "divine philosophy": "Mighty-like philosophy",
    "divine wrath": "Mighty-like wrath",
    "divine hymns": "Mighty-like hymns",
    "divine reason": "Mighty-like reason",
    "divine legislation": "Mighty-like legislation",
    "divine throne": "Mighty-like throne",
    "divine providence": "Mighty-like providence",
    "divine inheritance": "Mighty-like inheritance",
    "divine mitsvot": "Mighty-like mitsvot",
    "divine power": "Mighty-like power",
    "divine hand": "Mighty-like hand",
    "divine knowledge": "Mighty-like knowledge",
    "divine and": "Mighty-like and",
    // Standing alone at the end of a clause.
    "was divine": "was Mighty-like",
    "truly divine": "truly Mighty-like",
    "and divine": "and Mighty-like",
    "be divine": "be Mighty-like",
    "godlike": "Mighty-like",

    // --- the stake, not the cross --------------------------------------
    // Mattithyahu 16:24, 1 Corinthians 1:18, Philippians 2:8, Galatians
    // 6:14 — "stake" 37 times, "cross" never.
    "cross": "stake",

    // --- Sheol, not hell -----------------------------------------------
    // Four of these verses gloss it themselves — "hell (Sheol)" — and
    // CLAUDE.md gives grave/underworld as Sheol.
    "hell": "Sheol"
  };

  // --- 5. inline verse markers ----------------------------------------
  // "[19]", "[19J", "[19 J" — a verse number the typesetter printed inside
  // the running text. scripts/sweep_text.py turns these into real verses;
  // this pattern is what both sides agree on, and the render-time pass
  // removes any that survive.
  var VERSE_MARKER = /\[\s*(\d{1,3})\s*[J\])}]\s*/g;

  // The double numbering some editions print for the Shepherd of Hermas —
  // "10[76]:2" — is a cross-reference, not part of the reading, so the
  // whole reference goes rather than just its bracket.
  var DUAL_REFERENCE = /\b\d{1,3}\s*\[\s*\d{1,3}\s*[J\])}]\s*:\s*\d{1,3}\s*/g;

  // --- 6. glyphs that are not part of the reading ----------------------
  // The Torah, the Prophets, the Writings and the Messianic books contain
  // no brackets, no asterisks and no minus signs at all. The apocryphal
  // books, printed from scholarly editions, arrive carrying all three:
  //
  //   [ ]  { }   editorial brackets marking a translator's insertion, very
  //              often left unbalanced because the pair straddles a verse
  //              boundary. The words inside are part of the text; only the
  //              brackets are apparatus, so the brackets go and the words
  //              stay.
  //   −          a MINUS SIGN standing in for a hyphen ("hard−hearted") or,
  //              between words, for a dash.
  //   * ** ***   footnote marks. The mark itself is noise; a note that
  //              follows one at the end of a verse is real content, so it
  //              is kept and marked up as a footnote rather than deleted.
  //   / ' , I    a closing double-quote the scanner broke apart, which is
  //              how "Yea, lady/' I said" happens. A slash between two
  //              words with no spaces ("language/lip") is a real
  //              translator's alternative and is left alone.
  var MINUS = /−/g;
  // House typography is the en dash: the Torah, the Prophets, the Writings
  // and the Messianic books use it 1,358 times and the em dash once. The
  // apocryphal books arrive with "--" instead, 135 times.
  var DOUBLE_HYPHEN = /\s*--+\s*/g;
  var EM_DASH = /—/g;
  // A minus sign between two letters is a hyphen ("hard−hearted"), unless
  // what follows is a function word, in which case the printed line was a
  // dash: "his father Ḥanoḵ−for he had shown him" reads as an aside.
  var LETTER = "A-Za-zÀ-ɏḀ-ỿ0-9";
  var DASH_WORDS =
    "for|he|she|it|they|we|you|I|the|a|an|and|but|who|whom|that|which|so|as|" +
    "when|then|if|because|even|yet|to|in|of|on|with|there|this|these|those";
  var MINUS_DASH = new RegExp("([" + LETTER + "])−(?=(?:" + DASH_WORDS + ")\\b)", "g");
  var MINUS_HYPHEN = new RegExp("([" + LETTER + "])−(?=[" + LETTER + "])", "g");
  var FOOTNOTE = /\s\*{1,3}\s+(\S[\s\S]*)$/;
  var FOOTNOTE_BARE = /\s*\*{1,3}\s*$/;
  var STRAY_STAR = /\*+/g;
  // A stray middle dot the scanner dropped into a word gap.
  var MIDDLE_DOT = /·/g;
  // Some editions gloss the word they are translating — "hell (Sheol)",
  // "Sheol (the grave)". Once both halves say the same thing the gloss is
  // noise, so it is collapsed before the word tables run.
  var SELF_GLOSS = /\b(hell|Sheol)\s*\((?:Sheol|the grave|hell)\)/gi;
  var BRACKETS = /[[\]{}]/g;
  // A bracketed number whose digits the scanner mangled: [4S] is [45].
  var BRACKET_DIGITS = /\[\s*([0-9SlIOB]{1,3})\s*[J\]\)}]/g;
  var DIGIT_FOR_LETTER = { "S": "5", "l": "1", "I": "1", "O": "0", "B": "8" };

  function normalizeMarkerDigits(s) {
    return s.replace(BRACKET_DIGITS, function (m, body) {
      if (!/[SlIOB]/.test(body)) return m;
      var fixed = body.replace(/[SlIOB]/g, function (c) {
        return DIGIT_FOR_LETTER[c];
      });
      return /^\d{1,3}$/.test(fixed) ? "[" + fixed + "]" : m;
    });
  }

  function repairGlyphs(text) {
    var s = text;
    // Quote marks the scanner split into a slash and a stray letter.
    s = s.replace(/([A-Za-z,.])\s*\/\s*['’]/g, "$1”")
         .replace(/([A-Za-z.])\/I\b/g, "$1”")
         .replace(/([A-Za-z])\s*\/\s*,/g, "$1,”")
         .replace(/,\s1\/\s+/g, ", “")
         .replace(/([A-Za-z])\/ (?=[a-z])/g, "$1, ");
    // Minus sign: a dash before a function word, a hyphen inside a
    // compound, an em dash anywhere else.
    s = s.replace(MINUS_DASH, "$1 – ")
         .replace(MINUS_HYPHEN, "$1-")
         .replace(MINUS, " – ")
         .replace(DOUBLE_HYPHEN, " – ")
         .replace(EM_DASH, "–");
    // Footnotes: keep the note, mark it as one; drop every other star.
    if (s.indexOf("*") !== -1) {
      s = s.replace(FOOTNOTE_BARE, "");
      var note = s.match(FOOTNOTE);
      if (note) {
        s = s.slice(0, note.index) +
            ' <span class="fn">' + note[1].replace(STRAY_STAR, "").trim() +
            "</span>";
      }
      s = s.replace(STRAY_STAR, "");
    }
    s = s.replace(MIDDLE_DOT, "");
    s = s.replace(SELF_GLOSS, "$1");
    return s;
  }

  // --------------------------------------------------------------------
  function isUpper(ch) {
    return ch === ch.toUpperCase() && ch !== ch.toLowerCase();
  }

  // The replacement wears the capitalisation of what it replaced, word by
  // word where the two line up — so "Holy One" becomes "Set-apart One" and
  // not "Set-apart one".
  function applyCase(sample, replacement) {
    if (!sample) return replacement;
    var from = sample.split(/\s+/), to = replacement.split(/\s+/);
    if (from.length === to.length) {
      var out = [];
      for (var i = 0; i < to.length; i++) {
        out.push(from[i] && isUpper(from[i].charAt(0))
          ? to[i].charAt(0).toUpperCase() + to[i].slice(1)
          : to[i]);
      }
      return out.join(" ");
    }
    return isUpper(sample.charAt(0))
      ? replacement.charAt(0).toUpperCase() + replacement.slice(1)
      : replacement;
  }

  // Build one alternation per table so a verse is walked a fixed number of
  // times however long the tables grow.
  function escapeRe(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }

  function keysToRe(obj, wrap) {
    var keys = [];
    for (var k in obj) if (obj.hasOwnProperty(k)) keys.push(escapeRe(k));
    if (!keys.length) return null;
    keys.sort(function (a, b) { return b.length - a.length; });
    return new RegExp(wrap.replace("%s", "(" + keys.join("|") + ")"), "gi");
  }

  var JOIN_RE = keysToRe(JOINS, "\\b%s\\b");
  var SPLIT_RE = keysToRe(SPLITS, "\\b%s\\b");
  var TYPO_RE = keysToRe(TYPOS, "\\b%s\\b");
  var HOUSE_RE = keysToRe(HOUSE, "\\b%s\\b");

  function lookup(table, key) {
    return table[key.toLowerCase().replace(/\s+/g, " ")];
  }

  // The word tables, over one run of plain text (never any markup inside).
  function repairWords(text) {
    var s = String(text == null ? "" : text);
    if (JOIN_RE) {
      s = s.replace(JOIN_RE, function (m) {
        var r = lookup(JOINS, m);
        return r ? applyCase(m, r) : m;
      });
    }
    if (SPLIT_RE) {
      s = s.replace(SPLIT_RE, function (m) {
        var r = lookup(SPLITS, m);
        return r ? applyCase(m, r) : m;
      });
    }
    if (TYPO_RE) {
      s = s.replace(TYPO_RE, function (m) {
        var r = lookup(TYPOS, m);
        return r ? applyCase(m, r) : m;
      });
    }
    if (HOUSE_RE) {
      s = s.replace(HOUSE_RE, function (m) {
        var r = lookup(HOUSE, m);
        return r ? applyCase(m, r) : m;
      });
    }
    s = s.replace(DUAL_REFERENCE, " ").replace(VERSE_MARKER, " ");
    // Tidy the seams the repairs can leave behind. The space before a
    // punctuation mark is closed up only when the mark is not part of an
    // ellipsis — "Sha'ul was ... years old" must keep its spacing.
    s = s.replace(/[ \t]{2,}/g, " ")
         .replace(/(^|[^.…])[ \t]+([,;:!?]|\.(?![.…]))/g, "$1$2");
    return s;
  }

  // Repair a verse, markup and all. The order matters:
  //
  //   1. bracketed numbers are un-mangled, so "[4S]" can be recognised as
  //      the verse marker "[45]" in step 3;
  //   2. glyph repair runs over the whole verse — a footnote has to be
  //      found against the real end of the verse, not the end of some run
  //      between two <span>s;
  //   3. the word tables and the marker strip run only on the text between
  //      tags, so markup can never be corrupted;
  //   4. whatever brackets remain are apparatus, and go — their contents
  //      are words and stay.
  function repair(text) {
    var s = String(text == null ? "" : text);
    s = normalizeMarkerDigits(s);
    s = repairGlyphs(s);

    var out = "", i = 0;
    var re = /<[^>]*>/g, m;
    while ((m = re.exec(s)) !== null) {
      out += repairWords(s.slice(i, m.index)) + m[0];
      i = m.index + m[0].length;
    }
    out += repairWords(s.slice(i));

    out = out.replace(BRACKETS, "");
    // Closing up a bracket can leave a doubled space or a stranded one
    // before punctuation.
    return out.replace(/[ \t]{2,}/g, " ")
              .replace(/(^|[^.…])[ \t]+([,;:!?]|\.(?![.…]))/g, "$1$2")
              .trim();
  }

  global.BesorahWords = {
    JOINS: JOINS,
    SPLITS: SPLITS,
    TYPOS: TYPOS,
    HOUSE: HOUSE,
    VERSE_MARKER: VERSE_MARKER,
    repair: repair,
    repairPlain: repair,
    repairGlyphs: repairGlyphs
  };
})(typeof window !== "undefined" ? window : this);
