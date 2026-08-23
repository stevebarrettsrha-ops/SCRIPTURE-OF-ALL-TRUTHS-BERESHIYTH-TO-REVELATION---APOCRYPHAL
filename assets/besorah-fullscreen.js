// besorah-fullscreen.js
//
// One button, every page: read the Besorah fullscreen.
//
// The button injects itself bottom-right on any page that loads this file
// (the four reader pages and the offline edition alike), carries its own
// styles so no stylesheet needs to know about it, and uses the Fullscreen
// API with the WebKit fallbacks so desktop browsers and Android phones all
// work. Press F to toggle from the keyboard; Esc leaves fullscreen as the
// browser always allows.
//
// iPhone Safari has no Fullscreen API for pages, so there the button stays
// hidden — the pages instead carry the "add to home screen" metas, and a
// reader who pins the Besorah to their home screen gets it fullscreen that
// way. When the app is already running standalone (pinned), the button
// also stays hidden: there is no chrome left to remove.
(function () {
  "use strict";

  var doc = document;
  var root = doc.documentElement;

  function fsElement() {
    return doc.fullscreenElement || doc.webkitFullscreenElement || null;
  }

  var supported = !!(root.requestFullscreen || root.webkitRequestFullscreen);
  var standalone =
    (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches) ||
    window.navigator.standalone === true;
  if (!supported || standalone) return;

  function enter() {
    var el = root;
    var p = el.requestFullscreen ? el.requestFullscreen()
          : el.webkitRequestFullscreen ? el.webkitRequestFullscreen()
          : null;
    // Some engines return a promise that rejects when the gesture is not
    // accepted; a silent decline is better than an uncaught rejection.
    if (p && p.catch) p.catch(function () {});
  }

  function exit() {
    var p = doc.exitFullscreen ? doc.exitFullscreen()
          : doc.webkitExitFullscreen ? doc.webkitExitFullscreen()
          : null;
    if (p && p.catch) p.catch(function () {});
  }

  function toggle() { fsElement() ? exit() : enter(); }

  // --- the button --------------------------------------------------------
  var EXPAND = "⛶";      // ⛶
  var COMPRESS = "×";    // × (shown while fullscreen: "close")

  var style = doc.createElement("style");
  style.textContent =
    ".fs-btn{position:fixed;right:14px;bottom:14px;z-index:60;" +
    "width:44px;height:44px;border-radius:50%;" +
    "border:1px solid var(--rule,#4a3a28);" +
    "background:var(--panel,#251c16);color:var(--gold,#d4af37);" +
    "font-size:20px;line-height:1;cursor:pointer;" +
    "display:flex;align-items:center;justify-content:center;" +
    "box-shadow:0 2px 10px rgba(0,0,0,.45);opacity:.82;" +
    "transition:opacity 120ms,color 120ms;}" +
    ".fs-btn:hover{opacity:1;color:var(--link-hover,#fff3b8);}" +
    ".fs-btn:focus-visible{outline:2px solid var(--gold,#d4af37);outline-offset:2px;}" +
    "@media print{.fs-btn{display:none;}}";
  doc.head.appendChild(style);

  var btn = doc.createElement("button");
  btn.type = "button";
  btn.className = "fs-btn";
  btn.setAttribute("aria-pressed", "false");
  doc.addEventListener("DOMContentLoaded", function () { doc.body.appendChild(btn); });
  if (doc.body) doc.body.appendChild(btn);

  function paint() {
    var on = !!fsElement();
    btn.textContent = on ? COMPRESS : EXPAND;
    btn.title = on ? "Exit fullscreen (Esc)" : "Fullscreen (F)";
    btn.setAttribute("aria-label", btn.title);
    btn.setAttribute("aria-pressed", on ? "true" : "false");
  }
  paint();

  btn.addEventListener("click", toggle);
  doc.addEventListener("fullscreenchange", paint);
  doc.addEventListener("webkitfullscreenchange", paint);

  // F toggles, but never while the reader is typing in a field.
  doc.addEventListener("keydown", function (e) {
    if (e.key !== "f" && e.key !== "F") return;
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    var t = e.target;
    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" ||
              t.tagName === "SELECT" || t.isContentEditable)) return;
    toggle();
  });
})(typeof window !== "undefined" ? window : this);
