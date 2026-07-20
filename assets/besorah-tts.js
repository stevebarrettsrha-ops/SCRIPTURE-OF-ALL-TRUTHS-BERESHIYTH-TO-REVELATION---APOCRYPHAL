// besorah-tts.js
// Read-aloud (text-to-speech) player built on the browser's built-in
// Web Speech API (window.speechSynthesis). No backend, no network, no API
// keys — it uses whatever voices the reader's device provides, so it keeps
// working fully offline. The same API is used by chapter.html and the
// bundled besorah-offline.html (which inlines this file at build time).
//
//   BesorahTTS.init(toolbarEl)   -> build the player controls once
//   BesorahTTS.bind(versesEl)    -> point the player at a freshly rendered
//                                   chapter (call after every render)
//
// Playback speaks one verse (or prose block) at a time, highlighting and
// scrolling to each as it is spoken. Long blocks are split into short
// sentence-sized utterances to dodge the ~15s cut-off some browsers impose
// on a single utterance. Clicking a verse starts reading from that verse.
(function (global) {
  "use strict";

  var RATE_KEY  = "besorah:tts:rate";
  var VOICE_KEY = "besorah:tts:voice";
  var MAX_CHUNK = 200;  // characters per utterance (sentence-packed)

  var supported = typeof global.speechSynthesis !== "undefined" &&
                  typeof global.SpeechSynthesisUtterance !== "undefined";

  // ---- shared state ---------------------------------------------------
  var synth      = supported ? global.speechSynthesis : null;
  var toolbar    = null;      // the .tts-bar element (controls live here)
  var built      = false;     // controls constructed?
  var voices     = [];        // available SpeechSynthesisVoice list
  var rate       = 1.0;       // playback speed multiplier
  var voiceURI   = null;      // preferred voice (voiceURI) or null = default
  var autoVoice  = true;      // no saved voice yet -> auto-pick the best one

  var segments   = [];        // [{ el, chunks:[str,...] }, ...]
  var segIdx     = 0;         // current segment
  var chunkIdx   = 0;         // current chunk within segment
  var mode       = "stopped"; // "stopped" | "playing" | "paused"
  var gen        = 0;         // generation token; stale utterance callbacks ignore themselves

  // control element handles (filled by buildControls)
  var playBtn, stopBtn, rateInput, rateVal, voiceSel;

  // ---- persistence ----------------------------------------------------
  function loadPrefs() {
    try {
      var r = parseFloat(localStorage.getItem(RATE_KEY));
      if (isFinite(r) && r >= 0.5 && r <= 2) rate = r;
      var v = localStorage.getItem(VOICE_KEY);
      if (v === null) { autoVoice = true; voiceURI = null; }   // never chosen
      else { autoVoice = false; voiceURI = v || null; }        // "" = system default
    } catch (e) { /* private mode — use defaults */ }
  }
  function savePref(key, value) {
    try { localStorage.setItem(key, value); } catch (e) {}
  }

  // ---- text helpers ---------------------------------------------------
  // Verse text without its leading verse number, and with the divine-name
  // spans flattened to their transliterated text (which is exactly what we
  // want spoken: "Yahusha", "Aluahim", …).
  function elText(el) {
    var clone = el.cloneNode(true);
    var n = clone.querySelector(".verse-n");
    if (n) n.parentNode.removeChild(n);
    return (clone.textContent || "").replace(/\s+/g, " ").trim();
  }

  // Split a block of text into utterance-sized chunks at sentence
  // boundaries, packing sentences up to MAX_CHUNK characters each.
  function chunkText(text) {
    text = (text || "").replace(/\s+/g, " ").trim();
    if (!text) return [];
    var parts = text.match(/[^.!?;:]+[.!?;:]+["')\]]*|\S[^.!?;:]*$/g) || [text];
    var chunks = [], cur = "";
    for (var i = 0; i < parts.length; i++) {
      var p = parts[i].trim();
      if (!p) continue;
      if (cur && (cur.length + 1 + p.length) > MAX_CHUNK) {
        chunks.push(cur);
        cur = p;
      } else {
        cur = cur ? cur + " " + p : p;
      }
      // A single oversized part still needs to be spoken; keep it whole.
    }
    if (cur) chunks.push(cur);
    return chunks;
  }

  // ---- pronunciation --------------------------------------------------
  // Generic device voices mangle the Hebrew-roots transliterations and the
  // diacritics. We DON'T touch what's on screen — only the string handed to
  // the speech engine is respelled phonetically. Two layers:
  //   1) PRON: a curated respelling lexicon (keyed by a diacritic- and
  //      apostrophe-stripped, lower-cased form of the word) drawn from the
  //      pronunciation guides in CLAUDE.md. This is the authority.
  //   2) respellHebrew(): a fallback that phonetically flattens any word
  //      carrying Hebrew diacritics (ḇ→v, ḥ/ḵ→kh, ĕ→e, ayin dropped, q→k).
  // Casing is irrelevant to speech, so keys/values are lower-case.
  var PRON = {
    // Divine names & core sacred terms
    "yahuah": "yahoowah", "yah": "yah", "yahu": "yahoo",
    "yahusha": "yahooshua", "yahushua": "yahooshua",
    "mashiach": "masheeakh", "hamashiach": "ha masheeakh",
    "aluahim": "alooaheem", "aluah": "alooah",
    "yasharal": "yahsharal", "yasharalite": "yahsharalite",
    "yasharalites": "yahsharalites",
    "ruach": "rooakh", "ruchot": "rookhoat",
    "qodesh": "koadesh", "haqodesh": "ha koadesh",
    "halleluyah": "halelooyah",
    // People (patriarchs, prophets, kings)
    "abraham": "avraham", "abram": "avram", "hagar": "hagar",
    "yaaqob": "yaakov", "yitshaq": "yeetskhak", "noah": "noakh",
    "hanok": "khanok", "methushelah": "methooshelakh", "lemek": "lemek",
    "yoseph": "yosef", "yishmael": "yishmahel", "esaw": "aysaw",
    "mosheh": "mosheh", "aharon": "aharone", "dawid": "daweed",
    "shelomoh": "shelomo", "shemuel": "shemooel", "eliyahu": "eleeyahoo",
    "yashayahu": "yeshayahoo", "yirmeyahu": "yeermeyahoo",
    "yahuchanon": "yahookhanon", "yahudah": "yahoodah",
    "mattithyahu": "mateethyahoo", "ibrim": "eevreem",
    "binyamin": "binyameen", "shimon": "sheemone", "lewi": "lehvee",
    "ephrayim": "efrayeem", "menashsheh": "menahsheh", "reuben": "reuven",
    "shaul": "shahool",
    // Places
    "yerushalayim": "yerooshalayeem", "mitsrayim": "meetsrayeem",
    "mitsrites": "meetsrites", "mitsrite": "meetsrite",
    "kenaan": "kenahan", "yarden": "yarden", "midyan": "meedyan",
    "tsiyon": "tseeyone", "sinai": "sinai",
    // Theological & liturgical terms
    "shamayim": "shamayeem", "nephesh": "nefesh", "nepheshoth": "nefeshoat",
    "malak": "malak", "malakim": "malakeem",
    "kohen": "kohen", "kohanim": "kohaneem", "kehunnah": "kehoonah",
    "kohenic": "kohenik", "gadol": "gadole",
    "berith": "bereeth", "berithot": "bereetoat",
    "shalom": "shalome", "mizbeach": "meezbeakh", "mizbeachot": "meezbeakhoat",
    "mishpat": "meeshpat", "mishpatim": "meeshpateem",
    "qahal": "kahal", "qahalim": "kahaleem",
    "mitsvah": "meetsvah", "mitsvot": "meetsvoat",
    "eduth": "edooth", "eduyot": "edooyoat",
    "berakah": "berakah", "berakoth": "berakoat",
    "baruk": "barook", "barak": "barak",
    "chesed": "khesed", "kippur": "keepoor", "chen": "khen",
    "yeshua": "yeshooah", "heykal": "haykal", "sheol": "sheole",
    "qadash": "kadash", "qadashiyms": "kadasheems", "chaneph": "khanef",
    "shabbath": "shabbat", "torah": "torah", "pesach": "pesakh",
    "sukkot": "sookoat", "nabi": "navee", "nebiim": "neveeeem",
    "nebuah": "nevooah", "naba": "nava", "iyob": "eeyobe",
    "qoheleth": "koheleth", "qayin": "kah-yin", "hebel": "hevel",
    "mishle": "meeshlay", "tehillim": "teheeleem", "ekah": "aykah"
  };

  // Ayin / glottal-stop marks vary across the source PDFs: straight and
  // curly apostrophes, the reversed-9 mark (’ vs ‛), modifier letters, and
  // the Hebrew geresh. Treat them all as one droppable "ayin". Separate
  // global (replace) and non-global (test) copies — a shared /g regex is
  // stateful across .test() calls.
  var AYIN_G = /[‘’‚‛ʻʼʹ׳'`´]/g;
  var AYIN_T = /[‘’‚‛ʻʼʹ׳'`´]/;
  var COMBINING_G = /[̀-ͯ]/g;

  function nfd(w) { return w.normalize ? w.normalize("NFD") : w; }
  function hasDiacritic(w) { return /[̀-ͯ]/.test(nfd(w)); }

  // Lookup key: strip combining diacritics + every ayin variant, lower-case.
  function pronKey(w) {
    return nfd(w).replace(COMBINING_G, "")
                 .replace(AYIN_G, "")
                 .toLowerCase();
  }

  // Phonetic fallback for any diacritic-bearing word not in PRON.
  function respellHebrew(w) {
    return (w.normalize ? w.normalize("NFC") : w)
      .replace(/ḇ/g, "v").replace(/Ḇ/g, "V")
      .replace(/ḥ/g, "kh").replace(/Ḥ/g, "Kh")
      .replace(/ḵ/g, "kh").replace(/Ḵ/g, "Kh")
      .replace(/ḏ/g, "d").replace(/Ḏ/g, "D")
      .replace(/ḡ/g, "g").replace(/Ḡ/g, "G")
      .replace(/ṭ/g, "t").replace(/Ṭ/g, "T")
      .replace(/ĕ/g, "e").replace(/Ĕ/g, "E")
      .replace(AYIN_G, "")
      .replace(/q/g, "k").replace(/Q/g, "K");
  }

  // Word run = letters (incl. accented / Hebrew-Latin) plus ayin marks.
  var WORD_RE = /[A-Za-zÀ-ɏḀ-ỿ‘’‚‛ʻʼʹ׳'`´]+/g;

  function transformWord(w) {
    var key = pronKey(w);
    if (PRON.hasOwnProperty(key)) return PRON[key];
    // Possessive: "Aluahim's" -> lexicon("aluahim") + "s"
    if (key.charAt(key.length - 1) === "s" &&
        PRON.hasOwnProperty(key.slice(0, -1))) {
      return PRON[key.slice(0, -1)] + "s";
    }
    if (hasDiacritic(w)) return respellHebrew(w);
    if (AYIN_T.test(w)) return w.replace(AYIN_G, "");   // ayin / contraction
    return w;
  }

  // Turn on-screen text into a phonetic string for the speech engine.
  function speakable(text) {
    return String(text || "").replace(WORD_RE, transformWord);
  }

  // ---- voices ---------------------------------------------------------
  function loadVoices() {
    if (!synth) return;
    voices = synth.getVoices() || [];
    populateVoiceSelect();
  }

  // Rank the device's voices so the best English one is the default. Neural /
  // "natural" / "enhanced" voices sound best; Google's web voice next; remote
  // voices usually beat the robotic built-ins. Only used until the reader
  // makes an explicit choice.
  function pickBestVoice() {
    if (!voices.length) return null;
    var en = voices.filter(function (v) { return /^en/i.test(v.lang || ""); });
    var pool = (en.length ? en : voices).slice();
    function score(v) {
      var n = (v.name || "").toLowerCase();
      if (/natural|neural|enhanced|premium/.test(n)) return 0;
      if (/google/.test(n)) return 1;
      if (v.localService === false) return 2;
      return 3;
    }
    pool.sort(function (a, b) { return score(a) - score(b); });
    return pool[0] || null;
  }

  function populateVoiceSelect() {
    if (!voiceSel) return;
    // Sort: English voices first (this canon is English text), then by name.
    var sorted = voices.slice().sort(function (a, b) {
      var ae = /^en/i.test(a.lang) ? 0 : 1;
      var be = /^en/i.test(b.lang) ? 0 : 1;
      if (ae !== be) return ae - be;
      return a.name.localeCompare(b.name);
    });
    voiceSel.innerHTML = "";
    var def = document.createElement("option");
    def.value = "";
    def.textContent = "Default voice";
    voiceSel.appendChild(def);
    for (var i = 0; i < sorted.length; i++) {
      var v = sorted[i];
      var o = document.createElement("option");
      o.value = v.voiceURI;
      o.textContent = v.name + " (" + v.lang + ")";
      voiceSel.appendChild(o);
    }
    // With no saved choice, default to the best-sounding available voice.
    if (autoVoice && !voiceURI) {
      var best = pickBestVoice();
      if (best) voiceURI = best.voiceURI;
    }
    // Restore saved / auto-picked selection if that voice is present.
    if (voiceURI && voices.some(function (v) { return v.voiceURI === voiceURI; })) {
      voiceSel.value = voiceURI;
    } else {
      voiceSel.value = "";
    }
  }

  function currentVoice() {
    if (!voiceURI) return null;
    for (var i = 0; i < voices.length; i++) {
      if (voices[i].voiceURI === voiceURI) return voices[i];
    }
    return null;
  }

  // ---- controls -------------------------------------------------------
  function buildControls() {
    if (built || !toolbar) return;
    toolbar.classList.add("tts-bar");
    toolbar.innerHTML =
      '<button type="button" class="tts-btn tts-play" title="Read this chapter aloud">' +
        '<span class="tts-ico">▶</span><span class="tts-label">Read</span></button>' +
      '<button type="button" class="tts-btn tts-stop" title="Stop reading" disabled>■</button>' +
      '<label class="tts-rate" title="Reading speed">' +
        '<span class="tts-rate-ico">½×</span>' +
        '<input type="range" class="tts-rate-input" min="0.5" max="1.6" step="0.1">' +
        '<span class="tts-rate-val"></span></label>' +
      '<select class="tts-voice" title="Voice"></select>';

    playBtn   = toolbar.querySelector(".tts-play");
    stopBtn   = toolbar.querySelector(".tts-stop");
    rateInput = toolbar.querySelector(".tts-rate-input");
    rateVal   = toolbar.querySelector(".tts-rate-val");
    voiceSel  = toolbar.querySelector(".tts-voice");

    rateInput.value = String(rate);
    rateVal.textContent = rate.toFixed(1) + "×";

    playBtn.addEventListener("click", onPlayPause);
    stopBtn.addEventListener("click", stop);
    rateInput.addEventListener("input", function () {
      rate = parseFloat(rateInput.value) || 1.0;
      rateVal.textContent = rate.toFixed(1) + "×";
      savePref(RATE_KEY, String(rate));
      // Rate changes take effect on the next utterance; re-speak the current
      // chunk so the change is heard immediately while playing.
      if (mode === "playing") { chunkIdx--; nextGen(); speakCurrent(); }
    });
    voiceSel.addEventListener("change", function () {
      autoVoice = false;
      voiceURI = voiceSel.value || null;
      savePref(VOICE_KEY, voiceURI || "");
      if (mode === "playing") { chunkIdx--; nextGen(); speakCurrent(); }
    });

    built = true;
  }

  function setPlayButton(state) {
    if (!playBtn) return;
    var ico = playBtn.querySelector(".tts-ico");
    var lab = playBtn.querySelector(".tts-label");
    if (state === "playing") {
      ico.textContent = "⏸"; lab.textContent = "Pause";
      playBtn.title = "Pause reading";
    } else if (state === "paused") {
      ico.textContent = "▶"; lab.textContent = "Resume";
      playBtn.title = "Resume reading";
    } else {
      ico.textContent = "▶"; lab.textContent = "Read";
      playBtn.title = "Read this chapter aloud";
    }
    stopBtn.disabled = (state === "stopped");
  }

  // ---- playback engine ------------------------------------------------
  function nextGen() { gen++; if (synth) synth.cancel(); }

  function clearHighlight() {
    for (var i = 0; i < segments.length; i++) {
      segments[i].el.classList.remove("tts-speaking");
    }
  }

  function highlight(i) {
    clearHighlight();
    var el = segments[i] && segments[i].el;
    if (!el) return;
    el.classList.add("tts-speaking");
    var r = el.getBoundingClientRect();
    var vh = global.innerHeight || document.documentElement.clientHeight;
    if (r.top < 60 || r.bottom > vh - 40) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }

  function speakCurrent() {
    if (!synth) return;
    if (segIdx >= segments.length) { finish(); return; }
    var seg = segments[segIdx];
    if (chunkIdx < 0) chunkIdx = 0;
    if (chunkIdx >= seg.chunks.length) { segIdx++; chunkIdx = 0; speakCurrent(); return; }

    highlight(segIdx);
    mode = "playing";
    setPlayButton("playing");

    var myGen = gen;
    var u = new global.SpeechSynthesisUtterance(seg.chunks[chunkIdx]);
    u.rate = rate;
    var v = currentVoice();
    if (v) { u.voice = v; u.lang = v.lang; }
    u.onend = function () {
      if (myGen !== gen) return;         // superseded by cancel/restart
      chunkIdx++;
      if (chunkIdx >= seg.chunks.length) { segIdx++; chunkIdx = 0; }
      if (segIdx >= segments.length) { finish(); return; }
      speakCurrent();
    };
    u.onerror = function (e) {
      if (myGen !== gen) return;
      // "interrupted"/"canceled" are expected when we cancel deliberately.
      if (e && (e.error === "interrupted" || e.error === "canceled")) return;
      chunkIdx++;
      if (chunkIdx >= seg.chunks.length) { segIdx++; chunkIdx = 0; }
      if (segIdx >= segments.length) { finish(); return; }
      speakCurrent();
    };
    synth.speak(u);
  }

  function playFrom(i) {
    if (!segments.length) return;
    nextGen();
    segIdx = Math.max(0, Math.min(i, segments.length - 1));
    chunkIdx = 0;
    speakCurrent();
  }

  function onPlayPause() {
    if (mode === "playing") {
      synth.pause();
      mode = "paused";
      setPlayButton("paused");
    } else if (mode === "paused") {
      synth.resume();
      mode = "playing";
      setPlayButton("playing");
    } else {
      playFrom(0);
    }
  }

  function stop() {
    nextGen();
    mode = "stopped";
    segIdx = 0; chunkIdx = 0;
    clearHighlight();
    setPlayButton("stopped");
  }

  function finish() {
    gen++;
    mode = "stopped";
    segIdx = 0; chunkIdx = 0;
    clearHighlight();
    setPlayButton("stopped");
  }

  // ---- binding a chapter ---------------------------------------------
  function collectSegments(versesEl) {
    var segs = [];
    if (!versesEl) return segs;
    var prose = versesEl.querySelector(".prose");
    if (prose) {
      var chunks = chunkText(speakable(prose.textContent));
      if (chunks.length) segs.push({ el: prose, chunks: chunks });
      return segs;
    }
    var verses = versesEl.querySelectorAll("p.verse");
    for (var i = 0; i < verses.length; i++) {
      var chunks2 = chunkText(speakable(elText(verses[i])));
      if (chunks2.length) segs.push({ el: verses[i], chunks: chunks2 });
    }
    return segs;
  }

  // Click a verse (not its number — that toggles a bookmark) to start
  // reading from there. Ignore clicks made while selecting text.
  function wireClickToRead(versesEl) {
    if (!versesEl) return;
    versesEl.addEventListener("click", function (e) {
      var target = e.target;
      if (target.closest && target.closest(".verse-n")) return;
      var sel = global.getSelection && global.getSelection();
      if (sel && String(sel).length > 0) return;
      var el = target.closest ? target.closest("p.verse, p.prose") : null;
      if (!el) return;
      for (var i = 0; i < segments.length; i++) {
        if (segments[i].el === el) { playFrom(i); return; }
      }
    });
  }

  // ---- public API -----------------------------------------------------
  function init(toolbarEl) {
    if (!supported) {
      if (toolbarEl) toolbarEl.style.display = "none";
      return;
    }
    toolbar = toolbarEl;
    loadPrefs();
    buildControls();
    loadVoices();
    if (synth && typeof synth.addEventListener === "function") {
      synth.addEventListener("voiceschanged", loadVoices);
    } else if (synth) {
      synth.onvoiceschanged = loadVoices;
    }
    // Stop any speech if the reader leaves or hides the page.
    global.addEventListener("pagehide", stop);
    global.addEventListener("beforeunload", function () { if (synth) synth.cancel(); });
  }

  function bind(versesEl) {
    if (!supported) return;
    stop();                       // cancel anything from the previous chapter
    segments = collectSegments(versesEl);
    wireClickToRead(versesEl);
    if (versesEl) versesEl.classList.add("tts-readable");
    setPlayButton("stopped");
    // Hide the whole bar when a chapter has no speakable text.
    if (toolbar) toolbar.style.display = segments.length ? "" : "none";
  }

  global.BesorahTTS = {
    supported: supported,
    init: init,
    bind: bind,
    stop: stop
  };
})(window);
