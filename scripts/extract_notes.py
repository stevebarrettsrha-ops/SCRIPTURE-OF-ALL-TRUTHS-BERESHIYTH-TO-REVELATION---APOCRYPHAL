"""Extract Besorah footnotes (8-pt text at the bottom of each page) into
assets/notes.json so they can be displayed on a dedicated commentary page.

Each footnote starts with a Capitalized term followed by `:` or `—`, then
an explanation. Examples:
  Elohim: The ending "im" is really "YM" (yod-mem) and makes the word plural...
  Sabbath: Shin-beth-tau in Hebrew means "cease" or rest...
"""
import pdfplumber, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR = os.path.join(ROOT, "SCRIPTURE")
OUT = os.path.join(ROOT, "assets", "notes.json")


def extract_footnotes_from_page(pdf_path, page_num, body_size=10):
    """Return the joined footnote text on a page, or '' if there is none.

    Footnotes are typeset in a smaller font (≈ 8pt vs 10pt body).
    We collect chars with size < body_size that fall below the last body line,
    group them into reading-order lines, and join."""
    with pdfplumber.open(pdf_path) as pdf:
        if page_num < 1 or page_num > len(pdf.pages):
            return ''
        page = pdf.pages[page_num - 1]
        chars = page.chars
        if not chars:
            return ''
        # Find the bottom of body text
        body_chars = [c for c in chars if abs(c['size'] - body_size) <= 0.5]
        if not body_chars:
            return ''
        last_body_y = max(c['bottom'] for c in body_chars)
        # Footnote chars: smaller font, below the last body line
        foot_chars = [c for c in chars
                      if c['size'] < body_size - 0.5 and c['top'] >= last_body_y - 1]
        if not foot_chars:
            return ''
        # Cluster into words then lines
        # Sort by y first
        foot_chars.sort(key=lambda c: (round(c['top']), c['x0']))
        # Build lines using the same approach as the main extractor — group by
        # near-equal `top`, sort each line by x0, join.
        lines = []
        current = []
        anchor_top = None
        for c in foot_chars:
            if anchor_top is None or abs(c['top'] - anchor_top) <= 2:
                current.append(c)
                if anchor_top is None:
                    anchor_top = c['top']
                else:
                    # running mean
                    anchor_top = (anchor_top + c['top']) / 2
            else:
                lines.append(sorted(current, key=lambda x: x['x0']))
                current = [c]
                anchor_top = c['top']
        if current:
            lines.append(sorted(current, key=lambda x: x['x0']))

        # Join each line's chars into text (insert space when chars have a gap > char-width)
        line_strs = []
        for line in lines:
            buf = []
            prev_x1 = None
            for c in line:
                if prev_x1 is not None and c['x0'] - prev_x1 > c['width'] * 0.5:
                    buf.append(' ')
                buf.append(c['text'])
                prev_x1 = c['x1']
            line_strs.append(''.join(buf).strip())
        return '\n'.join(line_strs).strip()


# Headings to detect: a line starting with "Word:" or "Word Word:" followed by a
# space + lowercase word.
NOTE_PAT = re.compile(
    r'(?P<term>(?:[A-Z][A-Za-zĀ-ӿḂ-ỿ\'-]+(?:\s[a-zA-Z][A-Za-zĀ-ӿḂ-ỿ\'-]+){0,3}))\s*[:—]\s+(?P<body>[A-Za-z“”\'\"].*?)(?=\n[A-Z][A-Za-zĀ-ӿḂ-ỿ\'-]+\s*[:—]\s+[A-Za-z]|\Z)',
    re.DOTALL,
)


def split_notes(footnote_text):
    """A page may have several footnotes concatenated; split them by their
    leading 'Term:' headings. Returns list of {term, body}."""
    notes = []
    for m in NOTE_PAT.finditer(footnote_text):
        term = m.group('term').strip()
        body = re.sub(r'\s+', ' ', m.group('body')).strip()
        # Skip noise — terms must be substantial
        if len(term) < 3 or term in {'And', 'For', 'But', 'See', 'Now', 'When', 'Then'}:
            continue
        if len(body) < 30:
            continue
        notes.append({'term': term, 'body': body})
    return notes


def book_for_page(printed_page, index):
    """Return (book_id, hebrew_name, chapter) most likely covering this page."""
    best = None
    for b in index['books']:
        if not b.get('chapters'):
            continue
        for ch_str, c in b['chapters'].items():
            if c.get('pdf', '').startswith('TheBesorah') and c['printed'] <= printed_page:
                if not best or c['printed'] > best[2]:
                    best = (b['id'], b['hebrew'], c['printed'], int(ch_str))
    return best


def main():
    index = json.load(open(os.path.join(ROOT, 'assets', 'index.json'), encoding='utf-8'))
    out_notes = []
    for fname in ('TheBesorah-all.0001.pdf', 'TheBesorah-all.0002.pdf'):
        path = os.path.join(PDF_DIR, fname)
        with pdfplumber.open(path) as pdf:
            n = len(pdf.pages)
        for p in range(1, n + 1):
            ftext = extract_footnotes_from_page(path, p)
            if not ftext or len(ftext) < 50:
                continue
            notes = split_notes(ftext)
            if not notes:
                continue
            printed_page = p if fname.endswith('0001.pdf') else p + 700
            anchor = book_for_page(printed_page, index)
            for n_obj in notes:
                n_obj['page'] = printed_page
                n_obj['pdf'] = fname
                if anchor:
                    n_obj['book_id'] = anchor[0]
                    n_obj['book'] = anchor[1]
                    n_obj['chapter'] = anchor[3]
                out_notes.append(n_obj)
        print(f'{fname}: scanned {n} pages')
    # Dedupe by term keeping first occurrence (paginate canonically)
    seen = set()
    unique = []
    for n in out_notes:
        key = (n['term'].lower(), n['body'][:80])
        if key in seen:
            continue
        seen.add(key)
        unique.append(n)

    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump({'notes': unique}, f, ensure_ascii=False, indent=1)
    print(f'\nExtracted {len(unique)} unique notes (out of {len(out_notes)} occurrences).')


if __name__ == '__main__':
    main()
