"""
scripts/site_data.py: shared helpers for the bot scripts.

    load_yaml / save_yaml   read and write the files in _data/ while keeping the
                            explanatory comment block at the top of each file
    parse_issue_form        turn a GitHub issue-form body into {label: answer}
    fetch                   download a URL (used for BibTeX, ORCID, OpenAlex, photos)
    bib_ids                 the DOIs and arXiv numbers already in the BibTeX file
    slugify                 "Kyle Jordan" -> "kyle-jordan"

Needs PyYAML and Pillow (installed by the workflows: pip install pyyaml pillow).
"""
import re
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / '_data'
BIB = ROOT / '_bibliography' / 'lundeenlab.bib'
USER_AGENT = 'lundeen-lab-website-bot (+https://github.com/uOttawaQuantumPhotonics/Lundeen-Lab-Website)'


# ---- YAML files in _data/ ---------------------------------------------------

class _Dumper(yaml.SafeDumper):
    """Writes YAML in the same style as the hand-written files: block lists,
    unicode kept as is, and empty strings as "" so they are easy to spot."""


def _str(dumper, value):
    style = '"' if value == '' else ('|' if '\n' in value else None)
    return dumper.represent_scalar('tag:yaml.org,2002:str', value, style=style)


_Dumper.add_representer(str, _str)


def load_yaml(name):
    """Return (header_comment_text, data) for _data/<name>.yml."""
    text = (DATA / (name + '.yml')).read_text(encoding='utf-8')
    header = []
    for line in text.splitlines(keepends=True):
        if line.startswith('#') or not line.strip():
            header.append(line)
        else:
            break
    return ''.join(header), yaml.safe_load(text) or []


def save_yaml(name, header, data):
    body = yaml.dump(data, Dumper=_Dumper, allow_unicode=True, sort_keys=False, width=1000)
    (DATA / (name + '.yml')).write_text(header.rstrip('\n') + '\n\n' + body, encoding='utf-8')


# ---- Issue forms ------------------------------------------------------------

def parse_issue_form(body):
    """GitHub renders a submitted issue form as markdown:

        ### Headline

        Kyle Jordan starts a postdoc

        ### Link

        _No response_

    Return {'Headline': 'Kyle Jordan starts a postdoc', 'Link': '', ...}."""
    answers = {}
    for block in re.split(r'^### ', body or '', flags=re.M)[1:]:
        label, _, value = block.partition('\n')
        value = value.strip()
        if value == '_No response_':
            value = ''
        if value.startswith('```') and value.endswith('```'):      # "render:" code fences
            value = re.sub(r'^```\w*\n?|\n?```$', '', value).strip()
        answers[label.strip()] = value
    return answers


def image_urls(text):
    """Image links in a form answer (drag-and-drop uploads become markdown or <img> tags)."""
    urls = re.findall(r'!\[[^\]]*\]\((https?://[^)\s]+)\)', text or '')
    urls += re.findall(r'<img[^>]+src="(https?://[^"]+)"', text or '')
    if not urls:
        urls = re.findall(r'(https://github\.com/user-attachments/assets/[\w-]+)', text or '')
    return urls


# ---- Network ----------------------------------------------------------------

class _DropAuthOnRedirect(urllib.request.HTTPRedirectHandler):
    """Follow redirects, but never send our GitHub token to another host.

    Photos uploaded in a form live at github.com/user-attachments/...; GitHub answers with
    a redirect to a pre-signed storage URL. Python would forward the Authorization header
    there too, and the storage service rejects a request with two kinds of credentials
    (HTTP 400 Bad Request). So the header is dropped whenever the host changes."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None and urllib.parse.urlsplit(newurl).netloc != urllib.parse.urlsplit(req.full_url).netloc:
            new.remove_header('Authorization')
        return new


_opener = urllib.request.build_opener(_DropAuthOnRedirect)


def fetch(url, accept=None, token=None, binary=False, timeout=30):
    headers = {'User-Agent': USER_AGENT}
    if accept:
        headers['Accept'] = accept
    if token and urllib.parse.urlsplit(url).netloc.endswith('github.com'):   # the token is only for GitHub
        headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request(url, headers=headers)
    with _opener.open(req, timeout=timeout) as r:
        data = r.read()
    return data if binary else data.decode('utf-8', 'replace')


# ---- BibTeX -----------------------------------------------------------------

ARXIV_RE = re.compile(r'(?:arXiv[:.]|arxiv\.org/abs/|eprint\s*=\s*\{)\s*(\d{4}\.\d{4,5})', re.I)


def bib_ids(text=None):
    """Return (set of lower-case DOIs, set of arXiv numbers) already in the bib file."""
    text = BIB.read_text(encoding='utf-8') if text is None else text
    dois = {d.strip().lower() for d in re.findall(r'\bdoi\s*=\s*\{([^}]+)\}', text, re.I)}
    arx = set(ARXIV_RE.findall(text))
    return dois, arx


def normalise_doi(s):
    s = (s or '').strip()
    s = re.sub(r'^(https?://)?(dx\.)?doi\.org/', '', s, flags=re.I)
    return re.sub(r'^doi:\s*', '', s, flags=re.I)


def normalise_arxiv(s):
    m = re.search(r'(\d{4}\.\d{4,5})', s or '')
    return m.group(1) if m else ''


# ---- Misc -------------------------------------------------------------------

def slugify(s, limit=60):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    s = re.sub(r'[^a-zA-Z0-9]+', '-', s).strip('-').lower()
    return s[:limit].rstrip('-')
