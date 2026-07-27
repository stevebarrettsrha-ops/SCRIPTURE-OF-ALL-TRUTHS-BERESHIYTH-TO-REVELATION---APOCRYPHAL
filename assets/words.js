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
    "carefull": "carefully"
  };

  // --- 4. inline verse markers ----------------------------------------
  // "[19]", "[19J", "[19 J" — a verse number the typesetter printed inside
  // the running text. scripts/sweep_text.py turns these into real verses;
  // this pattern is what both sides agree on, and the render-time pass
  // removes any that survive.
  var VERSE_MARKER = /\[\s*(\d{1,3})\s*[J\]\)]\s*/g;

  // The double numbering some editions print for the Shepherd of Hermas —
  // "10[76]:2" — is a cross-reference, not part of the reading, so the
  // whole reference goes rather than just its bracket.
  var DUAL_REFERENCE = /\b\d{1,3}\s*\[\s*\d{1,3}\s*[J\]\)]\s*:\s*\d{1,3}\s*/g;

  // --------------------------------------------------------------------
  function applyCase(sample, replacement) {
    if (!sample) return replacement;
    if (sample[0] === sample[0].toUpperCase() &&
        sample[0] !== sample[0].toLowerCase()) {
      return replacement.charAt(0).toUpperCase() + replacement.slice(1);
    }
    return replacement;
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

  function lookup(table, key) {
    return table[key.toLowerCase().replace(/\s+/g, " ")];
  }

  // Repair a run of plain text (no markup inside).
  function repairPlain(text) {
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
    s = s.replace(DUAL_REFERENCE, " ").replace(VERSE_MARKER, " ");
    // Tidy the seams the repairs can leave behind. The space before a
    // punctuation mark is closed up only when the mark is not part of an
    // ellipsis — "Sha'ul was ... years old" must keep its spacing.
    s = s.replace(/[ \t]{2,}/g, " ")
         .replace(/(^|[^.…])[ \t]+([,;:!?]|\.(?![.…]))/g, "$1$2");
    return s;
  }

  // Repair text that may contain the whitelisted <span> markup: only the
  // text between tags is touched, so the markup can never be corrupted.
  function repair(text) {
    var s = String(text == null ? "" : text);
    if (s.indexOf("<") === -1) return repairPlain(s);
    var out = "", i = 0;
    var re = /<[^>]*>/g, m;
    while ((m = re.exec(s)) !== null) {
      out += repairPlain(s.slice(i, m.index)) + m[0];
      i = m.index + m[0].length;
    }
    return out + repairPlain(s.slice(i));
  }

  global.BesorahWords = {
    JOINS: JOINS,
    SPLITS: SPLITS,
    TYPOS: TYPOS,
    VERSE_MARKER: VERSE_MARKER,
    repair: repair,
    repairPlain: repairPlain
  };
})(typeof window !== "undefined" ? window : this);
