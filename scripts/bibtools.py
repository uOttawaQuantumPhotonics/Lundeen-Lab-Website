"""
scripts/bibtools.py: fetch BibTeX for new publications and add it to the library.

Used by process_submission.py (the "Add a publication" form) and orcid_sync.py
(the weekly ORCID check).

    bibtex_for_doi(doi)     BibTeX from doi.org (the publisher's own record)
    bibtex_for_arxiv(id)    BibTeX built from the arXiv listing
    arxiv_for_doi(doi)      the arXiv number of a published paper, via OpenAlex
    add_field(bibtex,k,v)   append one field to an entry
    add_entry(bibtex, ...)  add to _bibliography/lundeenlab.bib, or replace the
                            preprint entry it supersedes; refuses duplicates
"""
import re
import urllib.parse
import xml.etree.ElementTree as ET

from site_data import BIB, fetch, bib_ids, normalise_doi, normalise_arxiv


class BibError(Exception):
    """A problem the submitter can fix (bad DOI, duplicate, ...). The message is
    posted on their issue."""


def bibtex_for_doi(doi):
    url = 'https://doi.org/' + urllib.parse.quote(doi, safe='/:;()._-')
    try:
        text = fetch(url, accept='application/x-bibtex; charset=utf-8').strip()
    except Exception as e:
        raise BibError('Could not find DOI `%s` at doi.org (%s). Please check it.' % (doi, e))
    if not text.startswith('@'):
        raise BibError('doi.org did not return a citation for `%s`.' % doi)
    return text


def bibtex_for_arxiv(arxiv_id):
    try:
        xml = fetch('https://export.arxiv.org/api/query?id_list=' + arxiv_id)
    except Exception as e:
        raise BibError('Could not reach arXiv for `%s` (%s).' % (arxiv_id, e))
    ns = {'a': 'http://www.w3.org/2005/Atom'}
    entry = ET.fromstring(xml).find('a:entry', ns)
    if entry is None or entry.find('a:title', ns) is None:
        raise BibError('arXiv has no paper `%s`. Please check the number.' % arxiv_id)
    title = ' '.join(entry.find('a:title', ns).text.split())
    authors = ' and '.join(a.find('a:name', ns).text.strip() for a in entry.findall('a:author', ns))
    year = entry.find('a:published', ns).text[:4]
    first = authors.split(' and ')[0].split()[-1] if authors else 'arXiv'
    key = re.sub(r'\W', '', first) + year + arxiv_id.replace('.', '')
    return ('@misc{%s,\n  title = {%s},\n  author = {%s},\n  year = {%s},\n'
            '  journal = {arXiv:%s},\n  eprint = {%s},\n  archivePrefix = {arXiv},\n'
            '  url = {https://arxiv.org/abs/%s},\n}') % (key, title, authors, year, arxiv_id, arxiv_id, arxiv_id)


def arxiv_for_doi(doi):
    """Return the arXiv number OpenAlex knows for this DOI, or ''."""
    try:
        import json
        w = json.loads(fetch('https://api.openalex.org/works/doi:' + urllib.parse.quote(doi, safe='/')))
    except Exception:
        return ''
    for loc in w.get('locations', []):
        for field in ('landing_page_url', 'pdf_url'):
            a = normalise_arxiv(loc.get(field) or '') if 'arxiv' in (loc.get(field) or '') else ''
            if a:
                return a
    return ''


def add_field(bibtex, key, value):
    """Add `key = {value}` as the last field of one BibTeX entry."""
    body = re.sub(r'[\s,]*\}\s*$', '', bibtex.rstrip())
    return body + ',\n  %s = {%s}\n}' % (key, value)


def _with_eprint(bibtex, arxiv_id):
    """Add `eprint = {...}` so the site shows a direct arXiv button."""
    if not arxiv_id or re.search(r'\beprint\s*=', bibtex, re.I):
        return bibtex
    return add_field(add_field(bibtex, 'eprint', arxiv_id), 'archivePrefix', 'arXiv')


def _entries(text):
    """Yield (start, end, entry_text) for each @entry in the bib file."""
    for m in re.finditer(r'@\w+\s*\{', text):
        j, depth = m.end(), 1
        while depth and j < len(text):
            depth += {'{': 1, '}': -1}.get(text[j], 0)
            j += 1
        yield m.start(), j, text[m.start():j]


def add_entry(bibtex, doi='', arxiv_id=''):
    """Add one entry. Returns 'added' or 'replaced preprint'. Raises BibError for duplicates."""
    doi, arxiv_id = normalise_doi(doi).lower(), normalise_arxiv(arxiv_id)
    if not doi:
        m = re.search(r'\bdoi\s*=\s*\{([^}]+)\}', bibtex, re.I)
        doi = m.group(1).strip().lower() if m else ''
    bibtex = _with_eprint(bibtex.strip(), arxiv_id)
    text = BIB.read_text(encoding='utf-8', newline='')     # newline='': keep the file's line endings
    dois, arxs = bib_ids(text)
    if doi and doi in dois:
        raise BibError('This paper (DOI `%s`) is already on the Publications page.' % doi)

    # A published version of a preprint we already list: replace the preprint entry.
    if arxiv_id and arxiv_id in arxs:
        for s, e, entry in _entries(text):
            if arxiv_id in entry:
                if re.search(r'\bdoi\s*=', entry, re.I) or not doi:
                    raise BibError('This paper (arXiv `%s`) is already on the Publications page.' % arxiv_id)
                sep = '\r\n' if '\r\n' in text else '\n'
                BIB.write_bytes((text[:s] + bibtex.replace('\n', sep) + text[e:]).encode('utf-8'))
                return 'replaced preprint'

    # Make the citation key unique.
    m = re.match(r'@\w+\s*\{\s*([^,\s]+)', bibtex)
    if m and re.search(r'@\w+\s*\{\s*' + re.escape(m.group(1)) + r'\s*,', text):
        bibtex = bibtex.replace(m.group(1), m.group(1) + 'b', 1)
    sep = '\r\n' if '\r\n' in text else '\n'
    BIB.write_bytes((text.rstrip() + sep + sep + bibtex.replace('\n', sep) + sep).encode('utf-8'))
    return 'added'
