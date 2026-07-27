// check_render.js
// Renders every verse of every book exactly as the page does — the word
// repair from assets/words.js, then the escape-and-whitelist step the
// chapter view uses — and fails on anything a reader should never see.
//
//   node scripts/check_render.js
//
// This is the exhaustive counterpart to the browser sweep: the browser
// proves the page works, this proves all 47,000+ verses come out clean.
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
global.window = global;
eval(fs.readFileSync(path.join(ROOT, 'assets/words.js'), 'utf8'));
eval(fs.readFileSync(path.join(ROOT, 'assets/pronunciation.js'), 'utf8'));

// The renderer, copied from chapter.html / besorah-home.js.
function renderVerseText(raw) {
  const fixed = BesorahWords.repair(raw);
  const esc = fixed
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  return esc
    .replace(/&lt;span class="(dn|hwhy|fn)"&gt;/g, '<span class="$1">')
    .replace(/&lt;\/span&gt;/g, '</span>');
}

const CHECKS = [
  ['stray bracket',        /[[\]{}]/],
  ['stray asterisk',       /\*/],
  ['minus sign',           /−/],
  ['inline verse marker',  /\[\s*\d{1,3}\s*[J\])}]/],
  ['unescaped markup',     /&lt;|&gt;/],
  ['scanner quote scar',   /[A-Za-z]\/['’,]|\/I\b/],
  ['doubled space',        /\s{2,}/],
  ['space before comma',   /[^.…]\s[,;]/],
];

const index = JSON.parse(fs.readFileSync(path.join(ROOT, 'assets/index.json'), 'utf8'));
const failures = [];
let verses = 0, chapters = 0;

for (const book of index.books) {
  const file = path.join(ROOT, 'assets/text', book.id + '.json');
  if (!fs.existsSync(file)) { failures.push([book.id, '-', 'no text file']); continue; }
  const data = JSON.parse(fs.readFileSync(file, 'utf8'));
  if (Object.keys(data.chapters).length !== book.chapter_count) {
    failures.push([book.id, '-', `has ${Object.keys(data.chapters).length} chapters, index says ${book.chapter_count}`]);
  }
  for (const [cn, ch] of Object.entries(data.chapters)) {
    chapters++;
    if (!ch.verses || !ch.verses.length) { failures.push([book.id, cn, 'no verses']); continue; }
    for (const v of ch.verses) {
      verses++;
      const html = renderVerseText(v.t);
      // What the reader actually sees, once the markup is drawn.
      const shown = html.replace(/<[^>]+>/g, '');
      for (const [label, re] of CHECKS) {
        if (re.test(shown)) {
          failures.push([book.id, `${cn}:${v.n}`, `${label} — ${shown.slice(Math.max(0, shown.search(re) - 40), shown.search(re) + 40)}`]);
        }
      }
      const opens = (html.match(/<span/g) || []).length;
      const closes = (html.match(/<\/span>/g) || []).length;
      if (opens !== closes) failures.push([book.id, `${cn}:${v.n}`, 'unbalanced span after render']);
      if (!shown.trim()) failures.push([book.id, `${cn}:${v.n}`, 'renders empty']);
      // Everything spoken must survive the pronunciation pass.
      if (typeof BesorahPron.speakable(shown) !== 'string') {
        failures.push([book.id, `${cn}:${v.n}`, 'pronunciation pass failed']);
      }
    }
  }
}

console.log(`Rendered ${verses} verses across ${chapters} chapters of ${index.books.length} books.`);
if (!failures.length) {
  console.log('Nothing a reader should not see.');
  process.exit(0);
}
const byKind = {};
for (const [b, c, msg] of failures) {
  const kind = msg.split(' — ')[0];
  (byKind[kind] = byKind[kind] || []).push(`${b} ${c}: ${msg}`);
}
console.log(`${failures.length} problems:`);
for (const [kind, rows] of Object.entries(byKind).sort((a, b) => b[1].length - a[1].length)) {
  console.log(`  ${kind}: ${rows.length}`);
  rows.slice(0, 8).forEach(r => console.log('      ' + r));
}
process.exit(1);
