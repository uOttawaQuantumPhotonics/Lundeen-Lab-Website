#!/usr/bin/env python3
"""
scripts/orcid_sync.py: the weekly ORCID check.

Reads Jeff's public ORCID record, finds works whose DOI or arXiv number is not yet in
_bibliography/lundeenlab.bib, fetches their BibTeX and adds them. Run once a week by
.github/workflows/orcid-sync.yml, which opens (or refreshes) one pull request if
anything was added.

    python3 scripts/orcid_sync.py <pr-body.md>

Works are skipped when they are already in the bib (same DOI, arXiv number or title),
or listed in _bibliography/orcid-skip.txt (one DOI or title per line; for works you
deliberately leave off the site, such as conference abstracts).

Exit codes: 0 = entries were added (pull-request text in <pr-body.md>),
            1 = nothing new, so no pull request is needed.
"""
import json
import re
import sys

from site_data import BIB, fetch, bib_ids, normalise_doi, normalise_arxiv
import bibtools

SKIP_FILE = BIB.parent / 'orcid-skip.txt'


def norm_title(t):
    """Lower-case letters and digits only, so small differences in case, braces or punctuation match."""
    return re.sub(r'[^a-z0-9]', '', re.sub(r'<[^>]+>', '', t).lower())


def bib_titles():
    text = BIB.read_text(encoding='utf-8')
    return {norm_title(t) for t in re.findall(r'\btitle\s*=\s*\{((?:[^{}]|\{[^{}]*\})*)\}', text, re.I)}


def skip_list():
    if not SKIP_FILE.exists():
        return set()
    lines = [l.split('#')[0].strip() for l in SKIP_FILE.read_text(encoding='utf-8').splitlines()]
    return {normalise_doi(l).lower() if l.startswith('10.') else norm_title(l) for l in lines if l}

ORCID_ID = '0000-0002-0978-2913'


def orcid_works():
    """Yield (title, doi, arxiv) for each work on the ORCID record (one per group)."""
    data = json.loads(fetch('https://pub.orcid.org/v3.0/%s/works' % ORCID_ID, accept='application/json'))
    for group in data.get('group', []):
        doi = arx = ''
        for ext in (group.get('external-ids') or {}).get('external-id', []):
            kind, value = ext.get('external-id-type'), ext.get('external-id-value', '')
            if kind == 'doi' and not doi:
                doi = normalise_doi(value)
            elif kind == 'arxiv' and not arx:
                arx = normalise_arxiv(value)
        summary = (group.get('work-summary') or [{}])[0]
        title = (((summary.get('title') or {}).get('title') or {}).get('value')) or '(untitled)'
        yield title, doi, arx


def main():
    out = sys.argv[1]
    added, skipped = [], []
    skip = skip_list()
    for title, doi, arx in orcid_works():
        title = re.sub(r'<[^>]+>', '', title).strip()   # ORCID titles sometimes carry HTML tags
        if (doi and doi.lower() in skip) or norm_title(title) in skip:
            continue                                  # deliberately left off the site
        dois, arxs = bib_ids()                        # re-read: earlier additions count
        if norm_title(title) in bib_titles() and not (doi and arx and arx in arxs and doi.lower() not in dois):
            continue                                  # same title already listed
        if (doi and doi.lower() in dois) or (arx and arx in arxs):
            if not (doi and arx and arx in arxs and doi.lower() not in dois):
                continue                              # already listed
        if doi and doi.lower().startswith('10.48550/arxiv.'):   # arXiv's own DOIs
            arx, doi = arx or normalise_arxiv(doi), ''
        if not doi and not arx:
            skipped.append(title)
            continue
        try:
            if doi:
                entry = bibtools.bibtex_for_doi(doi)
                arx = arx or bibtools.arxiv_for_doi(doi)
            else:
                entry = bibtools.bibtex_for_arxiv(arx)
            result = bibtools.add_entry(entry, doi=doi, arxiv_id=arx)
            added.append('- %s (%s)%s' % (title, 'https://doi.org/' + doi if doi else 'arXiv:' + arx,
                                          ' — replaces the preprint entry' if result != 'added' else ''))
        except bibtools.BibError as e:
            skipped.append('%s: %s' % (title, e))
    if not added:
        print('ORCID check: nothing new.')
        return 1
    body = ['The weekly ORCID check (%s) found %d work(s) not yet on the Publications page '
            'and added them to `_bibliography/lundeenlab.bib`:' % (ORCID_ID, len(added)), ''] + added
    if skipped:
        body += ['', 'Not added (no DOI or arXiv number, or an error); add by hand if needed:', '']
        body += ['- ' + s for s in skipped]
    body += ['', 'Remove any entry you do not want listed, then merge. '
             'If you also keep the library in Zotero, add these there too so the next export keeps them.']
    open(out, 'w').write('Publications: %d new from ORCID\n' % len(added) + '\n'.join(body) + '\n')
    print('\n'.join(added))
    return 0


if __name__ == '__main__':
    sys.exit(main())
