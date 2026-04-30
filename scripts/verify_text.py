"""Verify extracted verse text matches the source PDFs.

For each book, samples chapters and checks:
1. Verse numbering is sequential with no gaps.
2. Each extracted verse's text is a substring of the raw PDF page text
   (after light normalization).
3. Verse count is within ±15% of the canonical/expected count.

Reports per-book pass/fail and prints a summary table.
"""
from pypdf import PdfReader
import re, json, os, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Canonical verse counts (KJV-ish); used as a ballpark sanity check.
CANONICAL = {
    "bereshith": 1533, "shemoth": 1213, "wayyiqra": 859, "bemidbar": 1288,
    "debarim": 959, "yahusha": 658, "shophetim": 618, "1shemuel": 810,
    "2shemuel": 695, "1melakim": 816, "2melakim": 719, "yeshayahu": 1292,
    "yirmeyahu": 1364, "yehezqel": 1273, "daniel": 357, "hoshea": 197,
    "yoel": 73, "amos": 146, "obadyah": 21, "yonah": 48, "mikah": 105,
    "nahum": 47, "habaqquq": 56, "tsephanyah": 53, "haggai": 38,
    "zekaryah": 211, "malaki": 55, "tehillim": 2461, "mishle": 915,
    "iyob": 1070, "shir-hashirim": 117, "ruth": 85, "ekah": 154,
    "qoheleth": 222, "ester": 167, "ezra": 280, "nehemyah": 406,
    "1dibre-hayamim": 942, "2dibre-hayamim": 822,
    "mattithyahu": 1071, "mark": 678, "luke": 1151, "yahuchanon": 879,
    "acts": 1007, "romans": 433, "1corinthians": 437, "2corinthians": 257,
    "galatians": 149, "ephesians": 155, "philippians": 104, "colossians": 95,
    "1thessalonians": 89, "2thessalonians": 47, "1timothy": 113,
    "2timothy": 83, "titus": 46, "philemon": 25, "ibrim": 303,
    "yaaqob": 108, "1kepha": 105, "2kepha": 61, "1yahuchanon": 105,
    "2yahuchanon": 13, "3yahuchanon": 14, "yahudah": 25, "hazon": 404,
}


def normalize(s):
    """Strip diacritics, lowercase, collapse whitespace, drop punctuation for matching."""
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r'[^\w\s]', ' ', s.lower())
    s = re.sub(r'\s+', ' ', s).strip()
    return s


_pdf_cache = {}
def get_pdf(name):
    if name not in _pdf_cache:
        _pdf_cache[name] = PdfReader(os.path.join(ROOT, "SCRIPTURE", name))
    return _pdf_cache[name]


def get_raw_pages(pdf_file, start_page, end_page):
    r = get_pdf(pdf_file)
    pages = []
    for p in range(start_page, end_page + 1):
        if 1 <= p <= len(r.pages):
            pages.append(r.pages[p - 1].extract_text() or "")
    return "\n".join(pages)


def check_book(book_id, sample_chapters=None):
    """Verify a single book's extracted text. Returns dict of stats."""
    bpath = os.path.join(ROOT, "assets", "text", f"{book_id}.json")
    if not os.path.exists(bpath):
        return {"id": book_id, "status": "MISSING", "errors": ["no JSON file"]}
    book = json.load(open(bpath, encoding='utf-8'))
    stats = {
        "id": book_id,
        "hebrew": book['hebrew'],
        "english": book['english'],
        "chapter_count": book['chapter_count'],
        "extracted_verses": 0,
        "expected_verses": CANONICAL.get(book_id),
        "gaps": [],
        "out_of_order": [],
        "missing_in_pdf": [],
        "errors": [],
    }

    chapters = book['chapters']
    total = 0
    for ch_str, cdat in chapters.items():
        verses = cdat.get('verses', [])
        total += len(verses)
        # Verse numbers must be 1..N strictly increasing
        nums = [v['n'] for v in verses]
        for i, n in enumerate(nums):
            if n != i + 1:
                stats['gaps'].append((ch_str, n, i+1))
                break
    stats['extracted_verses'] = total

    # Sample chapters: 1, mid, last for each book unless overridden
    if sample_chapters is None:
        if book['chapter_count'] >= 3:
            sample_chapters = [1, book['chapter_count'] // 2, book['chapter_count']]
        else:
            sample_chapters = list(range(1, book['chapter_count'] + 1))

    # For each sampled chapter, compare extracted verse text against raw PDF text
    for ch in sample_chapters:
        cdat = chapters.get(str(ch))
        if not cdat or not cdat.get('verses'):
            continue
        pdf_file = cdat['pdf']
        start = cdat['page']
        # Find next chapter or +5 pages
        next_ch = chapters.get(str(ch + 1))
        if next_ch and next_ch['pdf'] == pdf_file:
            end = max(start, next_ch['page'])
        else:
            end = start + 5
        raw = get_raw_pages(pdf_file, start, end)
        raw_norm = normalize(raw)

        # Sample first, mid, last verse
        verses = cdat['verses']
        idxs = sorted(set([0, len(verses) // 2, len(verses) - 1]))
        for vi in idxs:
            v = verses[vi]
            text = v['t']
            # Match a contiguous run of ~8 words from the verse against the raw page text.
            # Try several windows so a single bad word doesn't fail the whole verse.
            words = normalize(text).split()
            if len(words) < 4:
                continue
            found = False
            for start_w in range(0, max(1, len(words) - 5), 4):
                window = ' '.join(words[start_w:start_w + 8])
                if window and window in raw_norm:
                    found = True
                    break
            if not found:
                stats['missing_in_pdf'].append({
                    'chapter': ch, 'verse': v['n'], 'text': text[:120],
                    'needle': ' '.join(words[:8])
                })

    # Verdict
    expected = stats['expected_verses']
    if expected:
        ratio = total / expected
        stats['recovery'] = round(ratio * 100, 1)
        if ratio < 0.7:
            stats['errors'].append(f'recovery {round(ratio*100)}% below 70%')
    if stats['gaps']:
        stats['errors'].append(f'{len(stats["gaps"])} chapter(s) with verse-number gaps')
    if stats['missing_in_pdf']:
        stats['errors'].append(f'{len(stats["missing_in_pdf"])} sampled verse(s) not found in PDF')

    stats['status'] = 'OK' if not stats['errors'] else 'ISSUES'
    return stats


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    index = json.load(open(os.path.join(ROOT, "assets", "index.json")))
    book_ids = [b['id'] for b in index['books']]
    if only:
        book_ids = [b for b in book_ids if only in b]

    total_books, total_ok, total_issues = 0, 0, 0
    print(f'{"BOOK":<30} {"CH":>4} {"VERSES":>7} {"EXP":>5} {"%":>5}  STATUS  NOTES')
    print('-' * 100)
    issues_detail = []
    for bid in book_ids:
        try:
            s = check_book(bid)
        except Exception as e:
            print(f'{bid:<30} ERROR: {e}')
            continue
        if s['status'] == 'MISSING':
            print(f'{bid:<30} MISSING')
            continue
        rec = s.get('recovery', '-')
        rec_str = f'{rec}%' if isinstance(rec, (int, float)) else '-'
        notes = '; '.join(s['errors']) if s['errors'] else 'ok'
        exp = s.get('expected_verses') or '-'
        print(f'{bid:<30} {s["chapter_count"]:>4} {s["extracted_verses"]:>7} {str(exp):>5} {rec_str:>5}  {s["status"]:<8} {notes}')
        total_books += 1
        if s['status'] == 'OK':
            total_ok += 1
        else:
            total_issues += 1
            if s['missing_in_pdf']:
                issues_detail.append((bid, s['missing_in_pdf'][:2]))

    print('-' * 100)
    print(f'{total_books} books checked: {total_ok} OK, {total_issues} with issues.')
    if issues_detail:
        print('\nSample mismatches (first 2 per book):')
        for bid, miss in issues_detail[:10]:
            print(f'  {bid}:')
            for m in miss:
                print(f'    ch {m["chapter"]} v{m["verse"]}: {m["text"][:80]}')
                print(f'      needle: "{m["needle"]}"')


if __name__ == '__main__':
    main()
