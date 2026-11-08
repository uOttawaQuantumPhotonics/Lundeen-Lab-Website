#!/usr/bin/env python3
"""
scripts/build_publications.py: turn the BibTeX library into data for the Publications page.

    Input:   _bibliography/lundeenlab.bib   (a Zotero export; replace it to update the list)
    Output:  _data/publications.json        (read by publications.html; not stored in git)

GitHub Actions runs this before every Jekyll build (.github/workflows/deploy.yml).
To preview locally:  python3 scripts/build_publications.py && bundle exec jekyll serve

Uses only the Python standard library, so there is nothing to install.

For each entry the script works out:
  year, title, authors ("A. B. Smith, C. Jones, ..."; long lists shortened to six + "et al."),
  kind     Journal, Preprint, Conference or Patent (or Book/Thesis), from the entry type;
           a `sitekind = {...}` field, added by the publication form, overrides it
  citation e.g. "Physical Review Letters 117, 120401 (2016)" or "arXiv:2505.04607 (2025)"
  url      where the title links (the DOI if there is one)
  doi      DOI link, or "" (the DOI button is hidden when empty)
  arxiv    arXiv abstract page if the bib knows the arXiv id; otherwise an arXiv title search
  bibtex   the entry's own BibTeX (minus abstract/file/keyword fields) for "Copy BibTeX"
Entries are sorted newest year first; within a year the bib file's order is kept.
"""
import json
import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIB = ROOT / '_bibliography' / 'lundeenlab.bib'
OUT = ROOT / '_data' / 'publications.json'

# Article numbers missing from the bib, checked by hand against the publishers' pages.
# Key: DOI in lower case. Value: the page or article number to show.
PAGE_FIX = {
    '10.1088/1367-2630/ada05d': '121201',
    '10.1117/12.2670448': '127230X',
}

# Journal names to tidy up when Zotero exports them oddly.
VENUE_FIX = {'Nature communications': 'Nature Communications'}

# Fields left out of the "Copy BibTeX" text (long, private or noisy).
DROP_FIELDS = re.compile(r'\s*(abstract|file|keywords|urldate|langid|sitekind)\s*=', re.I)

ACCENTS = {'e': 'é', 'a': 'á', 'o': 'ó', 'i': 'í', 'u': 'ú', 'n': 'ñ'}


def parse_bib(text):
    """Return a list of (entry_type, {field: value}, raw_entry_text).
    A small brace-matching parser: enough for Zotero exports, not a full BibTeX parser."""
    entries = []
    pos = 0
    start_re = re.compile(r'@(\w+)\s*\{')
    while True:
        m = start_re.search(text, pos)
        if not m:
            break
        kind = m.group(1).lower()
        j, depth = m.end(), 1
        while depth and j < len(text):          # find the matching closing brace
            depth += {'{': 1, '}': -1}.get(text[j], 0)
            j += 1
        body = text[m.end():j - 1]
        pos = j
        if kind == 'comment':
            continue
        fields = {}
        for fm in re.finditer(r'(\w+)\s*=\s*\{', body):      # field = {value with {nested} braces}
            key, s, d = fm.group(1).lower(), fm.end(), 1
            e = s
            while d and e < len(body):
                d += {'{': 1, '}': -1}.get(body[e], 0)
                e += 1
            fields.setdefault(key, body[s:e - 1])
        for fm in re.finditer(r'(\w+)\s*=\s*(\d{4})\s*,', body):  # year = 2016, (no braces)
            fields.setdefault(fm.group(1).lower(), fm.group(2))
        entries.append((kind, fields, text[m.start():j]))
    return entries


def clean(s):
    """Strip LaTeX markup: accents, braces, \\&, ``quotes'', -- dashes."""
    s = re.sub(r'\\[`\'^"~]\{?(\w)\}?', r'\1', s)
    s = s.replace("{\\'e}", 'é').replace('\\&', '&').replace('``', '“').replace("''", '”').replace('--', '–')
    s = re.sub(r'[{}]', '', s).replace('\\', '')
    return re.sub(r'\s+', ' ', s).strip()


def format_authors(field):
    """'Lundeen, Jeff S. and Resch, K. J.' -> 'J. S. Lundeen, K. J. Resch'."""
    out = []
    for name in [x.strip() for x in field.split(' and ') if x.strip()]:
        if name == 'others':
            out.append('et al.')
            continue
        name = re.sub(r"\{\\'(\w)\}|\\'\{?(\w)\}?",
                      lambda m: ACCENTS.get(m.group(1) or m.group(2), m.group(1) or m.group(2)), name)
        name = clean(name)
        if ',' in name:
            last, first = [x.strip() for x in name.split(',', 1)]
        else:
            parts = name.split()
            last, first = parts[-1], ' '.join(parts[:-1])
        initials = ' '.join(x[0] + '.' for x in re.split(r'[\s\-]+', first) if x)
        out.append((initials + ' ' + last).strip())
    if len(out) > 8:
        out = out[:6] + ['et al.']
    return ', '.join(out)


def to_record(kind, f, raw):
    """Convert one parsed bib entry into the dictionary the page uses (None to skip it)."""
    title = clean(f.get('title', ''))
    if not title:
        return None
    venue = clean(f.get('journal', f.get('booktitle', '')))
    year = f.get('year', '')
    if not year:
        m = re.search(r'(20\d\d|19\d\d)', f.get('date', '') + f.get('urldate', ''))
        year = m.group(1) if m else ''
    doi = f.get('doi', '').strip()
    url = ('https://doi.org/' + doi) if doi else f.get('url', '').strip()

    # Which tab the entry belongs to.
    if kind == 'patent':
        k = 'Patent'
        venue = venue or 'Patent'
    elif 'arxiv' in venue.lower() or kind == 'misc':
        k = 'Preprint'
        venue = 'arXiv' if ('arxiv' in venue.lower() or not venue) else venue
    elif kind in ('conference', 'inproceedings') or 'Proceedings' in venue:
        k = 'Conference'
    else:
        k = 'Journal'
    # Entries added through the website form carry the type the submitter chose.
    k = clean(f.get('sitekind', '')) or k
    venue = VENUE_FIX.get(venue, venue)

    # The arXiv id, if the bib mentions one anywhere.
    m = re.search(r'(?:arXiv[:.]|arxiv\.org/abs/)(\d{4}\.\d{4,5})',
                  ' '.join(f.get(x, '') for x in ('journal', 'url', 'doi', 'eprint')), re.I)
    arx = m.group(1) if m else ''
    m = re.fullmatch(r'\s*(?:arXiv:)?(\d{4}\.\d{4,5})(v\d+)?\s*', f.get('eprint', ''), re.I)
    if m and not arx:                       # eprint = {2401.01234}, as the website form writes it
        arx = m.group(1)
    if not url and arx:
        url = 'https://arxiv.org/abs/' + arx

    # The short citation line.
    vol = clean(f.get('volume', ''))
    pages = clean(f.get('pages', '') or f.get('eid', '')).replace('-', '–').replace('––', '–')
    yr = ' (%s)' % year if year else ''
    if k == 'Preprint':
        m = re.search(r'(\d{4}\.\d{4,5})', f.get('journal', '') + ' ' + url + ' ' + f.get('doi', ''))
        citation = ('arXiv:' + m.group(1) if m else 'arXiv') + yr
    elif k == 'Patent':
        citation = ('Patent ' + clean(f.get('number', ''))).strip() + yr
    else:
        pages = re.sub(r'\s*–\s*', '–', PAGE_FIX.get(doi.lower(), pages))
        if venue.startswith('Proceedings of SPIE'):
            venue = 'Proc. SPIE'
        citation = venue + (' ' + vol if vol else '') + (', ' + pages if pages else '') + yr

    if doi and 'arxiv' in doi.lower():      # arXiv DOIs get the arXiv button instead
        doi = ''
    bibtex = '\n'.join(line.rstrip() for line in raw.strip().splitlines() if not DROP_FIELDS.match(line))
    return {
        'year': year, 'title': title, 'authors': format_authors(f.get('author', '')),
        'venue': venue, 'citation': citation, 'url': url or '#', 'kind': k,
        'doi': ('https://doi.org/' + doi) if doi else '',
        'arxiv': ('https://arxiv.org/abs/' + arx) if arx
                 else 'https://arxiv.org/search/?searchtype=title&query=' + urllib.parse.quote(title),
        'bibtex': bibtex,
    }


def main():
    text = BIB.read_text(encoding='utf-8').replace('\r\n', '\n')
    records = [r for r in (to_record(*e) for e in parse_bib(text)) if r]
    records.sort(key=lambda r: r['year'] or '0', reverse=True)   # stable: keeps bib order within a year
    OUT.write_text(json.dumps(records, ensure_ascii=False, indent=1), encoding='utf-8')
    print('Wrote %d publications to %s' % (len(records), OUT.relative_to(ROOT)))
    if not records:
        sys.exit('No publications found: is %s empty?' % BIB.relative_to(ROOT))


if __name__ == '__main__':
    main()
