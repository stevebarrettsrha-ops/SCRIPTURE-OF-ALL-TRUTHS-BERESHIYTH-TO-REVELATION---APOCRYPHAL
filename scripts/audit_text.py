"""Thorough audit of every chapter against its source PDF.

For each chapter:
  - extract raw PDF text from the recorded page range
  - sample 3 verses (first / middle / last)
  - confirm each verse's text appears (sliding-window match) in the
    raw PDF text
  - check verse numbering is sequential 1..N

Writes a per-book report to scripts/audit-report.md and a summary to stdout.
"""
from pypdf import PdfReader
import re, json, os, unicodedata, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "assets", "index.json")
TEXT_DIR = os.path.join(ROOT, "assets", "text")
PDF_DIR = os.path.join(ROOT, "SCRIPTURE")
REPORT = os.path.join(ROOT, "scripts", "audit-report.md")


def normalize(s):
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r'[^\w\s]', ' ', s.lower())
    return re.sub(r'\s+', ' ', s).strip()


_pdf_cache = {}
def get_pdf(name):
    if name not in _pdf_cache:
        _pdf_cache[name] = PdfReader(os.path.join(PDF_DIR, name))
    return _pdf_cache[name]


def page_text(pdf_filename, page):
    r = get_pdf(pdf_filename)
    if 1 <= page <= len(r.pages):
        return r.pages[page - 1].extract_text() or ''
    return ''


def text_in_pdf(needle_text, pdf_filename, start_page, end_page):
    raw = ''
    for p in range(start_page, end_page + 1):
        raw += '\n' + page_text(pdf_filename, p)
    raw_norm = normalize(raw)
    words = normalize(needle_text).split()
    if len(words) < 4:
        # Short verse — match whole thing
        n = ' '.join(words)
        return bool(n) and n in raw_norm
    # Sliding 8-word window
    for start in range(0, max(1, len(words) - 4), 4):
        win = ' '.join(words[start:start + 8])
        if win and win in raw_norm:
            return True
    return False


def audit_book(book, index):
    bid = book['id']
    text_path = os.path.join(TEXT_DIR, f'{bid}.json')
    if not os.path.exists(text_path):
        return {'id': bid, 'status': 'MISSING', 'issues': ['no JSON file']}
    text_book = json.load(open(text_path, encoding='utf-8'))
    idx_book = next(b for b in index['books'] if b['id'] == bid)

    issues = []
    chapters = text_book['chapters']
    verse_total = 0
    chapter_with_no_verses = []
    chapter_with_gaps = []
    chapter_with_missing_text = []

    for ch_str in sorted(chapters, key=int):
        ch = int(ch_str)
        cdat = chapters[ch_str]
        verses = cdat.get('verses', [])
        verse_total += len(verses)
        if not verses:
            chapter_with_no_verses.append(ch)
            continue
        # Check sequential numbering
        nums = [v['n'] for v in verses]
        if nums != list(range(1, len(nums) + 1)):
            # Find first gap
            for i, n in enumerate(nums):
                if n != i + 1:
                    chapter_with_gaps.append((ch, n, i + 1))
                    break

        # Determine PDF page range for this chapter
        idx_ch = idx_book['chapters'].get(ch_str)
        if not idx_ch:
            continue
        start_pg = idx_ch['page']
        idx_next = idx_book['chapters'].get(str(ch + 1))
        if idx_next and idx_next['pdf'] == idx_ch['pdf']:
            end_pg = max(start_pg, idx_next['page'])
        else:
            end_pg = start_pg + 5

        # Check first/mid/last verse text
        idxs = sorted(set([0, len(verses) // 2, len(verses) - 1]))
        for vi in idxs:
            v = verses[vi]
            if not text_in_pdf(v['t'], idx_ch['pdf'], start_pg, end_pg):
                chapter_with_missing_text.append({
                    'chapter': ch, 'verse': v['n'],
                    'text': v['t'][:100],
                    'pdf': idx_ch['pdf'], 'pages': f'{start_pg}-{end_pg}',
                })

    # Build issues summary
    if chapter_with_no_verses:
        issues.append(f'{len(chapter_with_no_verses)} chapter(s) with NO verses: {chapter_with_no_verses[:5]}')
    if chapter_with_gaps:
        issues.append(f'{len(chapter_with_gaps)} chapter(s) with verse-number gaps')
    if chapter_with_missing_text:
        issues.append(f'{len(chapter_with_missing_text)} sampled verse(s) NOT FOUND in PDF')

    return {
        'id': bid,
        'hebrew': text_book['hebrew'],
        'english': text_book['english'],
        'section': text_book['section'],
        'chapter_count': text_book['chapter_count'],
        'verse_total': verse_total,
        'no_verses': chapter_with_no_verses,
        'gaps': chapter_with_gaps,
        'missing_text': chapter_with_missing_text,
        'issues': issues,
        'status': 'OK' if not issues else 'ISSUES',
    }


def main():
    index = json.load(open(INDEX, encoding='utf-8'))
    rows = []
    for b in index['books']:
        try:
            rows.append(audit_book(b, index))
        except Exception as e:
            rows.append({'id': b['id'], 'status': 'ERROR', 'error': str(e)})

    # Print summary table
    fmt = '{:<28} {:>4} {:>7}  {:<7} {}'
    print(fmt.format('BOOK', 'CH', 'VERSES', 'STATUS', 'NOTES'))
    print('-' * 100)
    ok = issues = 0
    for r in rows:
        if r.get('status') in ('MISSING', 'ERROR'):
            print(f'{r["id"]:<28} {r.get("status"):<10} {r.get("error","")}')
            issues += 1
            continue
        notes = '; '.join(r['issues']) if r['issues'] else 'ok'
        print(fmt.format(r['id'], r['chapter_count'], r['verse_total'], r['status'], notes))
        if r['status'] == 'OK':
            ok += 1
        else:
            issues += 1
    print('-' * 100)
    print(f'{len(rows)} books — {ok} OK, {issues} with issues.')

    # Write detailed markdown report
    with open(REPORT, 'w', encoding='utf-8') as f:
        f.write('# Audit Report\n\n')
        f.write(f'{len(rows)} books — {ok} OK, {issues} with issues.\n\n')

        f.write('## Books with verse-text mismatches against PDF\n\n')
        any_mismatches = False
        for r in rows:
            if r.get('missing_text'):
                any_mismatches = True
                f.write(f'### {r["hebrew"]} ({r["english"]}) — {r["id"]}\n\n')
                for m in r['missing_text'][:10]:
                    f.write(f'- ch {m["chapter"]} v{m["verse"]} (PDF {m["pdf"]} pp {m["pages"]}):\n')
                    f.write(f'  - extracted: `{m["text"]!r}`\n')
                f.write('\n')
        if not any_mismatches:
            f.write('_None — all sampled verses appear in their PDF page range._\n\n')

        f.write('## Books with empty chapters\n\n')
        for r in rows:
            if r.get('no_verses'):
                f.write(f'- **{r["hebrew"]}**: chapters {r["no_verses"]}\n')

        f.write('\n## Books with verse-number gaps\n\n')
        for r in rows:
            if r.get('gaps'):
                f.write(f'- **{r["hebrew"]}** ({len(r["gaps"])} ch with gaps): ')
                f.write(', '.join(f'ch{ch} (got v{got} where v{exp} expected)'
                                  for ch, got, exp in r['gaps'][:5]))
                f.write('\n')

    print(f'\nDetailed report → {REPORT}')


if __name__ == '__main__':
    main()
