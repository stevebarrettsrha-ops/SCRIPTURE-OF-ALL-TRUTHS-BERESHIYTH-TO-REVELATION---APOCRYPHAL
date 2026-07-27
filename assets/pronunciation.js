// pronunciation.js
// Teaches the browser's speech engine how to say the Hebrew-roots
// vocabulary of this canon. Nothing on screen is ever changed — only the
// string handed to the speech engine is respelled.
//
//   BesorahPron.speakable(text)   -> phonetic respelling of a passage
//   BesorahPron.wordFor(word)     -> respelling of a single word
//   BesorahPron.LEXICON           -> the respelling table (see below)
//
// Generic English voices have no idea what to do with "Ya'aqoḇ",
// "Yahrushalayim" or "mizbe'ach": they either spell-read the diacritics or
// stress the wrong syllable. Three layers fix that, applied in order:
//
//   1. LEXICON  — a curated respelling for the vocabulary that actually
//                 occurs in these 104 books, keyed by a diacritic- and
//                 ayin-stripped lower-case form. Pronunciations follow the
//                 guides in CLAUDE.md; the rest were written from the
//                 standard Hebrew reading of each name.
//   2. AFFIXES  — possessives, plurals and the "ha-" article, so a form
//                 like "Aluahim's", "mizbe'achot" or "haMashiach" resolves
//                 through its stem instead of needing its own entry.
//   3. RULES    — an orthographic fallback for the long tail: soft bet to
//                 "v", chet/kaf to "kh", qoph to "k", ayin dropped, and the
//                 characteristic endings (-yahu, -im, -oth, -ĕl) spelled the
//                 way an English voice reads them correctly.
//
// Syllables are hyphenated ("yah-oo-wah"): every major engine treats a
// hyphen as a syllable boundary inside a word, which is what stops
// "Yahuah" from coming out as "yahooah" or "Ya-HOO-a".
(function (global) {
  "use strict";

  // ---- 1. the curated lexicon ---------------------------------------
  // Keys: lower-case, diacritics and ayin/apostrophe marks removed.
  // Values: hyphen-separated syllables for the speech engine.
  var LEXICON = {
    "yahuah": "yah-oo-wah",
    "yah": "yah",
    "yahu": "yah-hoo",
    "yahusha": "yah-hoo-shoo-ah",
    "yahushua": "yah-hoo-shoo-ah",
    "mashiach": "mah-shee-akh",
    "hamashiach": "hah mah-shee-akh",
    "aluahim": "al-oo-ah-heem",
    "aluah": "al-oo-ah",
    "aloah": "al-oh-ah",
    "aluahims": "al-oo-ah-heems",
    "al": "ahl",
    "yasharal": "yah-shah-rahl",
    "yasharalite": "yah-shah-rahl-ite",
    "yasharalites": "yah-shah-rahl-ites",
    "ruach": "roo-akh",
    "ruchot": "roo-khoht",
    "qodesh": "koh-desh",
    "haqodesh": "hah koh-desh",
    "haqodashim": "hah koh-dah-sheem",
    "qodashim": "koh-dah-sheem",
    "qadosh": "kah-dohsh",
    "chasid": "khah-seed",
    "chasidim": "khah-see-deem",
    "halleluyah": "hah-leh-loo-yah",
    "besorah": "beh-soh-rah",
    "amen": "ah-mayn",
    "selah": "seh-lah",
    "shalom": "shah-lohm",
    "torah": "toh-rah",
    "shabbath": "shah-baht",
    "shabbathoth": "shah-bah-thoht",
    "pesach": "peh-sakh",
    "sukkot": "soo-koht",
    "matstsoth": "mahts-tsoht",
    "shaḇuoth": "shah-voo-oht",
    "shabuoth": "shah-voo-oht",

    // --- people: patriarchs, matriarchs, the first families ---
    "adam": "ah-dahm",
    "adawm": "ah-dahm",
    "adawms": "ah-dahms",
    "hawwah": "khah-wah",
    "qayin": "kah-yeen",
    "hebel": "heh-vel",
    "sheth": "sheth",
    "enosh": "eh-nohsh",
    "hanok": "khah-nohk",
    "methushelah": "meh-thoo-sheh-lakh",
    "lemek": "leh-mek",
    "noah": "noh-akh",
    "noach": "noh-akh",
    "shem": "shem",
    "ham": "khahm",
    "yepheth": "yeh-feth",
    "yahpheth": "yah-feth",
    "nimrod": "neem-rohd",
    "terah": "teh-rakh",
    "abraham": "ahv-rah-hahm",
    "abrahim": "ahv-rah-heem",
    "abram": "ahv-rahm",
    "sarah": "sah-rah",
    "sarai": "sah-rye",
    "hagar": "hah-gar",
    "yishmael": "yeesh-mah-ahl",
    "yahshmaal": "yahsh-mah-ahl",
    "yitshaq": "yeets-khahk",
    "yahtshaq": "yahts-khahk",
    "ribqah": "reev-kah",
    "esaw": "ay-sahv",
    "yaaqob": "yah-ah-kohv",
    "leah": "lay-ah",
    "rachal": "rah-khel",
    "bilhah": "beel-hah",
    "zilpah": "zeel-pah",
    "yoseph": "yoh-sef",
    "binyamin": "bin-yah-meen",
    "reuben": "reh-oo-ven",
    "shimon": "sheem-ohn",
    "lewi": "lay-vee",
    "yahudah": "yah-hoo-dah",
    "yahudim": "yah-hoo-deem",
    "yahudi": "yah-hoo-dee",
    "yahudite": "yah-hoo-dite",
    "yissaskar": "yee-sahs-kar",
    "yahssaskar": "yahs-sahs-kar",
    "issachar": "ee-sah-kar",
    "zebulun": "zeh-voo-loon",
    "dan": "dahn",
    "naphtali": "naf-tah-lee",
    "gad": "gahd",
    "asher": "ah-sher",
    "ephrayim": "ef-rah-yeem",
    "menashsheh": "meh-nahsh-sheh",
    "tamar": "tah-mar",
    "perets": "peh-rets",
    "zerah": "zeh-rakh",
    "yobal": "yoh-vahl",
    "hedad": "heh-dahd",

    // --- leaders, prophets, kings, priests ---
    "mosheh": "moh-sheh",
    "aharon": "ah-hah-rone",
    "miryam": "meer-yahm",
    "yokebed": "yoh-keh-ved",
    "amram": "ahm-rahm",
    "qehath": "keh-hahth",
    "qehathites": "keh-hah-thites",
    "gereshon": "gay-reh-shohn",
    "gereshom": "gay-reh-shohm",
    "merari": "meh-rah-ree",
    "ithamar": "eeth-ah-mar",
    "alazar": "el-ah-zar",
    "aleazar": "el-ee-ay-zar",
    "aliezer": "el-ee-ay-zer",
    "pinehas": "pee-neh-khahs",
    "kaleb": "kah-lev",
    "shophetim": "shoh-feh-teem",
    "gidon": "gid-ohn",
    "baraq": "bah-rahk",
    "yahphtah": "yahf-takh",
    "shimshon": "sheem-shohn",
    "manowah": "mah-noh-akh",
    "shemual": "sheh-moo-ahl",
    "shaul": "shah-ool",
    "dawid": "dah-veed",
    "yahhonathan": "yah-hoh-nah-thahn",
    "yonathan": "yoh-nah-thahn",
    "yahshai": "yee-shye",
    "yoab": "yoh-ahv",
    "abishai": "ah-vee-shye",
    "abshalom": "ahv-shah-lohm",
    "amnon": "ahm-nohn",
    "tseruyah": "tseh-roo-yah",
    "shelomoh": "sheh-loh-moh",
    "rehabam": "reh-khahv-ahm",
    "yarobam": "yah-rohv-ahm",
    "ahab": "ah-khahv",
    "izebal": "ee-zeh-vel",
    "aliyahu": "ay-lee-yah-hoo",
    "aliyah": "ay-lee-yah",
    "alisha": "el-ee-shah",
    "yehu": "yay-hoo",
    "hizqiyahu": "khiz-kee-yah-hoo",
    "hizqiyah": "khiz-kee-yah",
    "yoshiyahu": "yoh-shee-yah-hoo",
    "yahshayahu": "yah-shah-yah-hoo",
    "yeshayahu": "yeh-shah-yah-hoo",
    "yahrmeyahu": "yah-rem-yah-hoo",
    "yirmeyahu": "yeer-meh-yah-hoo",
    "yahrmeyah": "yah-rem-yah",
    "yehezqal": "yeh-khez-kel",
    "daniyal": "dahn-ee-ahl",
    "danial": "dahn-ee-ahl",
    "hoshea": "hoh-shay-ah",
    "yoal": "yoh-ahl",
    "amos": "ah-mohs",
    "obadyah": "oh-vahd-yah",
    "yonah": "yoh-nah",
    "mikah": "mee-kah",
    "nahum": "nah-khoom",
    "habaqquq": "khah-vah-kook",
    "tsephanyah": "tseh-fahn-yah",
    "haggai": "khah-gye",
    "zekaryah": "zeh-kar-yah",
    "zekaryahu": "zeh-kar-yah-hoo",
    "malaki": "mahl-ah-kee",
    "ezra": "ez-rah",
    "nehemyah": "neh-khem-yah",
    "mordekai": "mor-deh-kye",
    "ester": "es-ter",
    "iyob": "ee-yohv",
    "hannah": "khah-nah",
    "ruth": "rooth",
    "boaz": "boh-ahz",
    "yahhoshaphat": "yah-hoh-shah-faht",
    "yahhoyada": "yah-hoh-yah-dah",
    "yahhoyaqim": "yah-hoh-yah-keem",
    "yahhoram": "yah-hoh-rahm",
    "yahhoash": "yah-hoh-ahsh",
    "yahhoahaz": "yah-hoh-ah-khahz",
    "amatsyahu": "ah-mahts-yah-hoo",
    "uzziyahu": "oo-zee-yah-hoo",
    "yotham": "yoh-thahm",
    "ahaz": "ah-khahz",
    "tsidqiyahu": "tsid-kee-yah-hoo",
    "ahazyahu": "ah-khahz-yah-hoo",
    "azaryah": "ah-zar-yah",
    "azaryahu": "ah-zar-yah-hoo",
    "azariah": "ah-zar-yah",
    "hananyah": "khah-nahn-yah",
    "gedalyahu": "geh-dahl-yah-hoo",
    "shemayah": "sheh-mah-yah",
    "tsadoq": "tsah-dohk",
    "abiyathar": "ev-yah-thar",
    "ebyathar": "ev-yah-thar",
    "hilqiyahu": "khil-kee-yah-hoo",
    "hilqiyah": "khil-kee-yah",
    "benayahu": "beh-nah-yah-hoo",
    "alqanah": "el-kah-nah",
    "yahdayah": "yah-dah-yah",
    "yeshua": "yeh-shoo-ah",
    "zerubbabal": "zeh-roo-bah-vel",
    "shealtial": "sheh-ahl-tee-ahl",
    "koresh": "koh-resh",
    "dareyawesh": "dar-yah-vesh",
    "artahshashta": "ar-takh-shahsh-tah",
    "ahashwerosh": "ah-khahsh-veh-rohsh",
    "haman": "hah-mahn",
    "nebukadnetstsar": "neh-voo-kahd-net-sar",
    "nebukadretstsar": "neh-voo-kahd-ret-sar",
    "nebuzaradan": "neh-voo-zar-ah-dahn",
    "sanherib": "sahn-khay-reev",
    "rabshaqeh": "rahv-shah-keh",
    "shadrak": "shahd-rahk",
    "meyshak": "may-shahk",
    "abed": "ah-ved",
    "beliar": "bel-ee-ar",
    "beliyaal": "beh-lee-yah-ahl",
    "azazal": "ah-zah-zel",
    "mastema": "mahs-teh-mah",

    // --- Messianic writings ---
    "yahuchanon": "yah-hoo-khah-nohn",
    "mattithyahu": "mah-teeth-yah-hoo",
    "kepha": "kay-fah",
    "barnabah": "bar-nah-vah",
    "sila": "see-lahs",
    "immerser": "im-mer-ser",
    "natsareth": "nahts-ah-reth",
    "natsarene": "nahts-ah-reen",
    "ibrim": "eev-reem",
    "ibri": "eev-ree",
    "galil": "gah-leel",
    "gabrial": "gahv-ree-ahl",
    "mikaal": "mee-khah-ahl",
    "michaal": "mee-khah-ahl",
    "raphaal": "rah-fah-ahl",
    "urial": "oo-ree-ahl",
    "kerub": "keh-roov",
    "kerubim": "keh-roo-veem",
    "seraphim": "seh-rah-feem",

    // --- places ---
    "yahrushalayim": "yah-roo-shah-lah-yeem",
    "yerushalayim": "yeh-roo-shah-lah-yeem",
    "mitsrayim": "meets-rah-yeem",
    "mitsrite": "meets-rite",
    "mitsrites": "meets-rites",
    "kenaan": "keh-nah-ahn",
    "kenaanite": "keh-nah-ahn-ite",
    "kenaanites": "keh-nah-ahn-ites",
    "yarden": "yar-dayn",
    "midyan": "meed-yahn",
    "tsiyon": "tsee-yohn",
    "sinai": "sye-nye",
    "horeb": "khoh-rev",
    "babal": "bah-vel",
    "ashshur": "ahsh-shoor",
    "ninaweh": "nee-neh-veh",
    "nineweh": "nee-neh-veh",
    "shomeron": "shoh-meh-rohn",
    "shekem": "sheh-khem",
    "hebron": "kheh-vrohn",
    "beyth": "bayth",
    "lehem": "leh-khem",
    "bethlehem": "beth-leh-hem",
    "beersheba": "beh-er-sheh-vah",
    "yahriho": "yeh-ree-khoh",
    "gilgal": "gil-gahl",
    "gilead": "gil-ee-ahd",
    "bashan": "bah-shahn",
    "moab": "moh-ahv",
    "edom": "eh-dohm",
    "seir": "say-eer",
    "ammon": "ah-mohn",
    "amaleq": "ah-mah-lek",
    "amaleqites": "ah-mah-lek-ites",
    "philistines": "fil-is-teens",
    "pelishtites": "peh-leesh-tites",
    "aram": "ah-rahm",
    "arameans": "ah-rah-mee-ans",
    "damascus": "dah-mahs-kus",
    "lebanon": "leh-vah-nohn",
    "karmal": "kar-mel",
    "hermon": "kher-mohn",
    "megiddo": "meh-gid-oh",
    "shushan": "shoo-shahn",
    "shinar": "shee-nar",
    "sedom": "seh-dohm",
    "amorah": "ah-moh-rah",
    "gerar": "geh-rar",
    "haran": "khah-rahn",
    "mamre": "mahm-reh",
    "peniyal": "peh-nee-ahl",
    "sukkoth": "soo-kohth",
    "ashdod": "ahsh-dohd",
    "azzah": "ah-zah",
    "eqron": "ek-rohn",
    "gath": "gahth",
    "tsor": "tsohr",
    "tsidon": "tsee-dohn",
    "tsidonians": "tsee-doh-nee-ans",
    "yapho": "yah-foh",
    "tarshish": "tar-sheesh",
    "ophir": "oh-feer",
    "sheba": "sheh-vah",
    "kush": "koosh",
    "kushite": "koo-shite",
    "yawan": "yah-vahn",
    "chittim": "kit-eem",
    "euphrates": "yoo-fray-tees",
    "gihon": "gee-khohn",
    "hinnom": "hee-nohm",
    "anathoth": "ah-nah-thohth",
    "ramah": "rah-mah",
    "mitspah": "mits-pah",
    "gibon": "giv-ohn",
    "gibah": "giv-ah",
    "yabesh": "yah-vaysh",
    "qadesh": "kah-daysh",
    "paran": "pah-rahn",
    "heshbon": "khesh-bohn",
    "arnon": "ar-nohn",
    "yahbusites": "yeh-voo-sites",
    "yahbusite": "yeh-voo-site",
    "hiwwites": "khiv-ites",
    "perizzites": "peh-riz-ites",
    "horite": "khoh-rite",
    "amorites": "ah-moh-rites",
    "gilad": "gil-ahd",
    "hamath": "khah-mahth",
    "lakish": "lah-keesh",
    "eden": "ay-den",
    "en": "ayn",
    "gaash": "gah-ahsh",
    "eylam": "ay-lahm",
    "bethual": "beth-oo-ahl",
    "maakah": "mah-ah-kah",
    "yahzreal": "yiz-reh-ahl",
    "yizreal": "yiz-reh-ahl",

    // --- further names the books lean on ---
    "hebal": "heh-vel",
    "hebrew": "heh-broo",
    "hebrews": "heh-broos",
    "hadad": "hah-dahd",
    "sihon": "see-khohn",
    "abimelek": "ah-vee-meh-lek",
    "abner": "ahv-nayr",
    "bilam": "bil-ahm",
    "hamor": "khah-mohr",
    "nahor": "nah-khohr",
    "yoash": "yoh-ahsh",
    "tubal": "too-vahl",
    "shimi": "sheem-ee",
    "yashub": "yah-shoov",
    "eber": "ay-ver",
    "hittite": "khit-ite",
    "hittites": "khit-ites",
    "og": "ohg",
    "beor": "beh-ohr",
    "obed": "oh-ved",
    "heth": "khayth",
    "shelah": "sheh-lah",
    "qorah": "koh-rakh",
    "baasha": "bah-ah-shah",
    "abiyah": "ah-vee-yah",
    "nebat": "neh-vaht",
    "nadab": "nah-dahv",
    "hanan": "khah-nahn",
    "makir": "mah-keer",
    "hazaal": "khah-zah-ahl",
    "er": "ayr",

    // --- worship, law and the set-apart vocabulary ---
    "shamayim": "shah-mah-yeem",
    "nephesh": "neh-fesh",
    "nepheshoth": "neh-feh-shohth",
    "malak": "mahl-ahk",
    "malakim": "mahl-ah-keem",
    "kohen": "koh-hayn",
    "kohanim": "koh-hah-neem",
    "kohenic": "koh-hay-nik",
    "kehunnah": "keh-hoo-nah",
    "gadol": "gah-dohl",
    "lewite": "lay-vite",
    "lewites": "lay-vites",
    "berith": "beh-reeth",
    "berithot": "beh-ree-toht",
    "mizbeach": "meez-beh-akh",
    "mizbeachot": "meez-beh-ah-khoht",
    "mishpat": "meesh-paht",
    "mishpatim": "meesh-pah-teem",
    "qahal": "kah-hahl",
    "qahalim": "kah-hah-leem",
    "mitsvah": "meets-vah",
    "mitsvot": "meets-voht",
    "eduth": "ay-dooth",
    "eduyot": "ay-doo-yoht",
    "berakah": "beh-rah-kah",
    "berakoth": "beh-rah-kohth",
    "baruk": "bah-rook",
    "barak": "bah-rahk",
    "chesed": "kheh-sed",
    "kippur": "kee-poor",
    "chen": "khayn",
    "yasha": "yeh-shoo-ah",
    "heykal": "hay-kahl",
    "hekal": "hay-kahl",
    "heykals": "hay-kahls",
    "sheol": "sheh-ohl",
    "qadash": "kah-dahsh",
    "qadashiyms": "kah-dah-sheems",
    "chaneph": "khah-nef",
    "nabi": "nah-vee",
    "nebiim": "neh-vee-eem",
    "nebuah": "neh-voo-ah",
    "naba": "nah-vah",
    "tehillim": "teh-hee-leem",
    "mishle": "meesh-lay",
    "bereshith": "beh-ray-sheeth",
    "shemoth": "sheh-mohth",
    "wayyiqra": "vah-yeek-rah",
    "bemidbar": "beh-meed-bar",
    "debarim": "deh-vah-reem",
    "kethubim": "keh-thoo-veem",
    "ekah": "ay-kah",
    "qoheleth": "koh-heh-leth",
    "shir": "sheer",
    "hashirim": "hah shee-reem",
    "hayamim": "hah yah-meem",
    "dibre": "div-ray",
    "melakim": "meh-lah-keem",
    "hazon": "khah-zohn",
    "yashar": "yah-shar",
    "yobelim": "yoh-veh-leem",
    "sheqel": "sheh-kel",
    "sheqels": "sheh-kels",
    "homer": "khoh-mer",
    "ephah": "ay-fah",
    "hin": "heen",
    "shoham": "shoh-hahm",
    "asherim": "ah-shay-reem",
    "asherah": "ah-shay-rah",
    "dagon": "dah-gohn",
    "baal": "bah-ahl",
    "aluahs": "al-oo-ahs"
  };

  // Words that must never be respelled even though they carry a mark or
  // look Hebrew — ordinary English that the engine already says correctly.
  var LEAVE_ALONE = {
    "the": 1, "and": 1, "all": 1, "call": 1, "hall": 1, "shall": 1, "small": 1,
    "tall": 1, "wall": 1, "fall": 1, "ball": 1
  };

  // ---- 2. mark handling ---------------------------------------------
  // Ayin / glottal-stop marks vary across the source PDFs: straight and
  // curly apostrophes, the reversed-9 mark, modifier letters and the
  // Hebrew geresh. Treat them all as one droppable "ayin". Separate
  // global (replace) and non-global (test) copies — a shared /g regex is
  // stateful across .test() calls.
  var AYIN_G = /[‘’‚‛ʻʼʹ׳'`´]/g;
  var AYIN_T = /[‘’‚‛ʻʼʹ׳'`´]/;
  var COMBINING_G = /[̀-ͯ]/g;

  function nfd(w) { return w.normalize ? w.normalize("NFD") : w; }
  function hasDiacritic(w) { return /[̀-ͯ]/.test(nfd(w)); }

  // Lookup key: strip combining diacritics + every ayin variant, lower-case.
  function pronKey(w) {
    return nfd(w).replace(COMBINING_G, "").replace(AYIN_G, "").toLowerCase();
  }

  // ---- 3. orthographic fallback -------------------------------------
  // For any word not in the lexicon: flatten the Hebrew orthography to
  // something an English voice reads sensibly.
  function respell(w) {
    var s = (w.normalize ? w.normalize("NFC") : w);
    s = s
      .replace(/ḇ/g, "v").replace(/Ḇ/g, "V")
      .replace(/ḥ/g, "kh").replace(/Ḥ/g, "Kh")
      .replace(/ḵ/g, "kh").replace(/Ḵ/g, "Kh")
      .replace(/ḏ/g, "d").replace(/Ḏ/g, "D")
      .replace(/ḡ/g, "g").replace(/Ḡ/g, "G")
      .replace(/ṭ/g, "t").replace(/Ṭ/g, "T")
      .replace(/ṣ/g, "ts").replace(/Ṣ/g, "Ts")
      .replace(/ĕ/g, "e").replace(/Ĕ/g, "E")
      .replace(/[āăâ]/g, "ah").replace(/[ĀĂÂ]/g, "Ah")
      .replace(/[īĭî]/g, "ee").replace(/[ĪĬÎ]/g, "Ee")
      .replace(/[ōŏô]/g, "oh").replace(/[ŌŎÔ]/g, "Oh")
      .replace(/[ūŭû]/g, "oo").replace(/[ŪŬÛ]/g, "Oo")
      .replace(AYIN_G, "")
      .replace(/q/g, "k").replace(/Q/g, "K");
    // Characteristic endings, longest first.
    s = s
      .replace(/iyahu$/i, "ee-yah-hoo")
      .replace(/yahu$/i, "yah-hoo")
      .replace(/yah$/i, "yah")
      .replace(/oth$/i, "ohth")
      .replace(/ith$/i, "eeth")
      .replace(/im$/i, "eem")
      .replace(/([bcdfghjklmnpqrstvwxz])al$/i, "$1ahl");
    return s;
  }

  // ---- 4. one word --------------------------------------------------
  var PLURALS = [
    ["im", "eem"], ["oth", "ohth"], ["ot", "oht"], ["s", "s"]
  ];

  function wordFor(w) {
    if (!w) return w;
    var key = pronKey(w);
    if (LEAVE_ALONE[key] === 1) return w;
    if (LEXICON.hasOwnProperty(key)) return LEXICON[key];

    // Possessive: "Aluahim's" -> lexicon("aluahim") + "s"
    if (/s$/.test(key) && LEXICON.hasOwnProperty(key.slice(0, -1))) {
      return LEXICON[key.slice(0, -1)] + "s";
    }
    // The "ha-" article welded to a name: haMashiach, haQodesh, haShirim.
    if (key.length > 4 && key.slice(0, 2) === "ha" &&
        LEXICON.hasOwnProperty(key.slice(2))) {
      return "hah " + LEXICON[key.slice(2)];
    }
    // Hebrew plural of a known stem: mizbe'achot, mal'akim, berithot.
    for (var i = 0; i < PLURALS.length; i++) {
      var suf = PLURALS[i][0];
      if (key.length > suf.length + 2 && key.slice(-suf.length) === suf) {
        var stem = key.slice(0, -suf.length);
        if (LEXICON.hasOwnProperty(stem)) {
          return LEXICON[stem] + "-" + PLURALS[i][1];
        }
      }
    }
    // English word wearing an English suffix on a Hebrew stem
    // ("Yasharalites", "Mitsrites") is covered by the lexicon; anything
    // left that carries a Hebrew mark goes through the fallback.
    if (hasDiacritic(w) || AYIN_T.test(w)) return respell(w);
    return w;
  }

  // ---- 5. a whole passage -------------------------------------------
  // Word run = letters (incl. accented / Hebrew-Latin) plus ayin marks.
  var WORD_RE =
    /[A-Za-zÀ-ɏḀ-ỿ‘’‚‛ʻʼʹ׳'`´]+/g;

  // ---- 6. punctuation ------------------------------------------------
  // Voices differ wildly in what they read out: some announce "slash",
  // "dash", "asterisk", "quote", even "comma" and "full stop". None of it
  // belongs in a reading, so every mark is taken out of the string handed
  // to the engine.
  //
  // The pauses survive, because they do not come from the marks. The
  // player has already cut the passage into sentence-sized utterances
  // (see chunkText in besorah-tts.js), and the gap between two utterances
  // is what a listener hears as the end of a sentence.
  //
  // A hyphen becomes a space rather than vanishing: it is what separates
  // the syllables of a respelling ("yah-oo-wah"), and a space keeps that
  // separation without any voice announcing "dash".
  var HYPHENS = /[-‐‑‒–—―−]/g;
  var DROP_MARKS = /["'`´“”‘’«»‹›„‚(){}\[\]<>|\\\/_~^*%#@$&+=§¶†‡•·…,.;:!?¡¿]/g;

  function stripMarks(text) {
    return String(text || "")
      .replace(HYPHENS, " ")
      .replace(DROP_MARKS, " ")
      .replace(/\s{2,}/g, " ")
      .trim();
  }

  // The bracketed gloss is for the eye, not the ear. words.js writes the
  // Hebrew with its English alongside — "qadash (Set Apart)" — so a reader
  // meeting the word for the first time is never lost. Spoken aloud that
  // would be "qadash Set Apart" a thousand times over, so the gloss is
  // silenced here. Only these exact brackets go; every other parenthesis
  // in the canon is part of the reading and is left alone.
  var GLOSS = /\s*\((?:Most Set Apart Place|Set Apart Ones|Set Apart One|Set Apart Place|Set Apart|Faithful|Sheol)\)/g;

  function speakable(text) {
    var s = String(text || "").replace(GLOSS, "");
    return stripMarks(s.replace(WORD_RE, wordFor));
  }

  global.BesorahPron = {
    LEXICON: LEXICON,
    speakable: speakable,
    wordFor: wordFor,
    respell: respell,
    pronKey: pronKey
  };
})(typeof window !== "undefined" ? window : this);
