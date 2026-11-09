#!/usr/bin/env python3
"""
scripts/process_submission.py: turn one submitted update form (a GitHub issue)
into changes to the site's data files.

Run by .github/workflows/process-submission.yml whenever an issue with one of the
form labels is opened or edited. The workflow then commits the changes to a branch
and opens a pull request for an admin to approve.

    python3 scripts/process_submission.py <github-event.json> <pr-body.md>

What each form does (the label on the issue picks the form):
    news         adds an item to the top of _data/news.yml (+ photo, 1200 px wide)
    publication  fetches BibTeX and adds it to _bibliography/lundeenlab.bib
    profile      adds or updates a card in _data/members.yml (+ photo, 400 x 400)
    alumni       "leaving": moves the person from members.yml to alumni.yml
                 "update":  edits (or adds) their row in alumni.yml

Exit codes
    0  success: files changed, <pr-body.md> holds the pull-request text
    2  the submission has a problem the submitter can fix: <pr-body.md> holds a
       message that the workflow posts on the issue (no pull request is opened)
"""
import datetime
import io
import json
import os
import re
import sys

from site_data import ROOT, load_yaml, save_yaml, parse_issue_form, image_urls, fetch, slugify, \
    normalise_doi, normalise_arxiv
import bibtools


class Problem(Exception):
    """Something the submitter should fix; the message is posted on the issue."""


TOKEN = os.environ.get('GITHUB_TOKEN')


# ---- Photos -----------------------------------------------------------------

def download_image(field_text, what):
    urls = image_urls(field_text)
    if not urls:
        if field_text.strip():
            raise Problem('I could not find an image in the %s box. Please drag a JPG or PNG file into it.' % what)
        return None
    from PIL import Image, ImageOps
    try:
        data = fetch(urls[0], token=TOKEN, binary=True, timeout=60)
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert('RGB')
    except Exception as e:
        raise Problem('I could not open the %s (%s). Please upload a JPG or PNG.' % (what, e))
    return img


def save_headshot(img, slug):
    """Crop to a square, keeping the upper part of a portrait photo, and save 400 x 400."""
    w, h = img.size
    if min(w, h) < 200:
        raise Problem('The photo is only %d × %d pixels; please send one at least 400 × 400.' % (w, h))
    side = min(w, h)
    left = (w - side) // 2
    top = int((h - side) * 0.25)          # a little above centre: keeps heads in frame
    img = img.crop((left, top, left + side, top + side)).resize((400, 400))
    rel = 'assets/img/people/%s.jpg' % slug
    img.save(ROOT / rel, quality=88, optimize=True)
    return rel


def save_news_photo(img, slug):
    w, h = img.size
    if w > 1200:
        img = img.resize((1200, round(h * 1200 / w)))
    (ROOT / 'assets/img/news').mkdir(parents=True, exist_ok=True)
    rel = 'assets/img/news/%s.jpg' % slug
    img.save(ROOT / rel, quality=85, optimize=True)
    return rel


def raw_url(branch, rel):
    """Link that shows a file from the pull-request branch (for the photo preview)."""
    repo = os.environ.get('GITHUB_REPOSITORY', 'uOttawaQuantumPhotonics/Lundeen-Lab-Website')
    return 'https://github.com/%s/blob/%s/%s?raw=true' % (repo, branch, rel)


def need_url(value, field):
    if value and not re.match(r'https?://\S+$', value):
        raise Problem('The %s should be a full web address starting with https:// (got "%s").' % (field, value))
    return value


# ---- Form handlers ----------------------------------------------------------
# Each returns (pull-request title, list of markdown lines describing the change).

NEWS_TAGS = ['Paper', 'People', 'Award', 'Event', 'Outreach', 'Other']


def do_news(a, branch):
    title, date_s, tag, text = a.get('Headline', ''), a.get('Date', ''), a.get('Tag', ''), a.get('Text', '')
    if len(title) > 80:
        raise Problem('The headline is %d characters; please keep it under 80.' % len(title))
    if len(text) > 400:
        raise Problem('The text is %d characters; please keep it under 400.' % len(text))
    try:
        date = datetime.date.fromisoformat(date_s)
    except ValueError:
        raise Problem('The date "%s" should look like 2026-11-08 (year-month-day).' % date_s)
    if tag not in NEWS_TAGS:
        raise Problem('Please choose a tag from the list.')
    link = need_url(a.get('Link', ''), 'link')
    slug = '%s-%s' % (date.isoformat(), slugify(title, 40))
    img = download_image(a.get('Photo', ''), 'photo')
    photo = save_news_photo(img, slug) if img else ''

    header, items = load_yaml('news')
    item = {'date': date.isoformat(), 'date_text': date.strftime('%b %Y'), 'tag': tag, 'title': title,
            'text': ' '.join(text.split()), 'link': link, 'image': photo.split('/')[-1] if photo else '',
            'image_credit': a.get('Photo credit', '') if photo else ''}
    items.append(item)
    items.sort(key=lambda x: str(x['date']), reverse=True)      # newest first
    save_yaml('news', header, items)
    lines = ['Adds a news item to `_data/news.yml`:', '', '> **%s** · %s · %s' % (title, tag, item['date_text']),
             '> ', '> ' + item['text']]
    if link:
        lines += ['> ', '> Read more: ' + link]
    if photo:
        lines += ['', 'Photo (resized to at most 1200 px wide):', '', '![photo](%s)' % raw_url(branch, photo)]
    return 'News: ' + title, lines


KIND = {'Journal article': 'Journal', 'Conference paper': 'Conference', 'Preprint': 'Preprint',
        'Book or chapter': 'Book', 'Patent': 'Patent', 'Thesis': 'Thesis'}


def do_publication(a, branch):
    doi = normalise_doi(a.get('DOI', ''))
    arx = normalise_arxiv(a.get('arXiv number', ''))
    bib = a.get('BibTeX', '').strip()
    if a.get('arXiv number') and not arx:
        raise Problem('"%s" does not look like an arXiv number (e.g. 2401.01234).' % a['arXiv number'])
    try:
        if doi:
            entry = bibtools.bibtex_for_doi(doi)
            arx = arx or bibtools.arxiv_for_doi(doi)
        elif bib.startswith('@'):
            entry = bib
        elif arx:
            entry = bibtools.bibtex_for_arxiv(arx)
        else:
            raise Problem('Please give a DOI, an arXiv number, or a BibTeX entry.')
        kind = KIND.get(a.get('Type', ''), '')
        if kind:
            entry = bibtools.add_field(entry, 'sitekind', kind)   # which tab it appears under
        result = bibtools.add_entry(entry, doi=doi, arxiv_id=arx)
    except bibtools.BibError as e:
        raise Problem(str(e))
    m = re.search(r'\btitle\s*=\s*[{"](.+?)[}"],?\s*\n', entry, re.I | re.S)
    t = re.sub(r'[{}]', '', m.group(1)) if m else (doi or arx)
    lines = ['%s `_bibliography/lundeenlab.bib`%s:' % ('Adds to' if result == 'added' else 'Updates',
             ' (replaces the preprint entry with the published version)' if result != 'added' else ''),
             '', '```bibtex', entry, '```']
    for label in ('Lab members who are authors', 'Note for the approver'):
        if a.get(label):
            lines += ['', '**%s:** %s' % (label, a[label])]
    return 'Publication: ' + t[:90], lines


LINK_FORMS = {   # form field -> (members.yml key, how to turn the answer into a URL)
    'Personal website': ('website', lambda v: need_url(v, 'website')),
    'Google Scholar': ('scholar', lambda v: need_url(v, 'Google Scholar link')),
    'ORCID': ('orcid', lambda v: 'https://orcid.org/' + re.sub(r'^https?://orcid\.org/', '', v)),
    'GitHub': ('github', lambda v: 'https://github.com/' + re.sub(r'^(https?://github\.com/|@)', '', v).strip('/')),
    'LinkedIn': ('linkedin', lambda v: need_url(v, 'LinkedIn link')),
    'X': ('x', lambda v: 'https://x.com/' + re.sub(r'^(https?://(x|twitter)\.com/|@)', '', v).strip('/')),
    'Bluesky': ('bluesky', lambda v: 'https://bsky.app/profile/' + re.sub(r'^(https?://bsky\.app/profile/|@)', '', v).strip('/')),
}


def find(items, name):
    """The entry with exactly this name (as picked from a form's drop-down list), or None."""
    return next((x for x in items if x['name'] == name), None)


def similar(a, b):
    """True when two names look like the same person: equal ignoring case and accents, or
    one is the other plus extra words ("Manuel Ferrer" / "Manuel Ferrer-García").
    Used only to STOP a submission that would create a duplicate, never to pick a card."""
    wa, wb = slugify(a).split('-'), slugify(b).split('-')
    n = min(len(wa), len(wb))
    return n >= 2 and wa[:n] == wb[:n]


def already_listed(typed, twin, where, list_name):
    """The message for a "new" name that matches someone already listed."""
    if slugify(typed) == slugify(twin):
        return '**%s** is already %s. Please pick your name in the %s list instead.' % (twin, where, list_name)
    return ('"%s" looks like it may already be %s as **%s**. If that is you, pick "%s" in the %s list '
            '(and put "%s" in Full name if you want the name changed).' % (typed, where, twin, twin, list_name, typed))


def picked(a, label, none_option):
    """The name chosen in a drop-down, or '' for no choice / the "not listed" option."""
    v = a.get(label, '').strip()
    return '' if v in ('', none_option) else v


NEW_MEMBER = 'New member (not listed yet)'
NOT_LISTED = 'Not listed'


def do_profile(a, branch):
    who = picked(a, 'Profile', NEW_MEMBER)
    action = a.get('What to do', 'Add or update')
    typed = ' '.join(a.get('Full name', '').split())
    header, members = load_yaml('members')
    warnings = []

    if action == 'Remove this card':
        if not who:
            raise Problem('To remove a card, pick it in the Profile list. "New member" has no card to remove.')
        m = find(members, who)
        if not m:
            raise Problem('"%s" is no longer on the People page, so there is nothing to remove.' % who)
        members.remove(m)
        save_yaml('members', header, members)
        warnings.append('This **removes** the card of **%s** from Current members, without adding an alumni entry. '
                        'Removal is meant for duplicates and mistakes; check that this person is not simply leaving '
                        '(that is the Moving on form).' % who)
        return 'Remove: ' + who, warnings, ['Removes **%s** from `_data/members.yml`. The photo file stays in the repository.' % who]

    if who:
        m = find(members, who)
        if not m:
            raise Problem('"%s" is no longer on the People page. Pick "New member" if you want to be added again.' % who)
        new = False
    else:
        if not typed:
            raise Problem('Please give your full name (you picked "New member").')
        twin = next((x['name'] for x in members if similar(x['name'], typed)), None)
        if twin:
            raise Problem(already_listed(typed, twin, 'on the People page', 'Profile'))
        for field in ('Role', 'Start (year and term)'):
            if not a.get(field):
                raise Problem('Please fill in "%s" (it is required for a new member).' % field)
        m = {'name': typed, 'role': '', 'project': '', 'bio': '', 'photo': '',
             'links': {k: '' for k, _ in LINK_FORMS.values()}}
        members.append(m)
        new = True

    project, bio = a.get('Project title', ''), ' '.join(a.get('Bio', '').split())
    if len(project) > 80:
        raise Problem('The project title is %d characters; please keep it under 80.' % len(project))
    if len(bio.split()) > 80:
        raise Problem('The bio is %d words; please keep it under 80.' % len(bio.split()))

    title = ('Profile: add ' if new else 'Profile: update ') + m['name']
    if not new and typed and typed != m['name']:
        warnings.append('This **renames** the card "%s" to "%s". Check that this is intended and not a typo.' % (m['name'], typed))
        title = 'Rename: %s → %s' % (m['name'], typed)
        m['name'] = typed
    # Only fields that were filled in change.
    for field, key in (('Role', 'role'), ('Start (year and term)', 'start'), ('Project title', 'project'), ('Bio', 'bio')):
        if a.get(field):
            m[key] = bio if key == 'bio' else a[field]
    m.setdefault('links', {})
    for field, (key, to_url) in LINK_FORMS.items():
        if a.get(field):
            m['links'][key] = to_url(a[field].strip())
    img = download_image(a.get('Photo', ''), 'photo')
    photo = save_headshot(img, slugify(m['name'])) if img else ''
    if photo:
        m['photo'] = photo.split('/')[-1]
    save_yaml('members', header, members)
    lines = ['%s **%s** in `_data/members.yml` (Current members on the People page).' % ('Adds' if new else 'Updates', m['name']),
             '', '```yaml', yaml_snippet(m), '```']
    if photo:
        lines += ['', 'Photo, cropped to 400 × 400:', '', '<img src="%s" width="160">' % raw_url(branch, photo)]
    return title, warnings, lines


LEVELS = {'Postdoctoral fellow': 'Postdoctoral fellows', 'PhD': 'PhD', 'MSc': 'MSc',
          'Undergraduate': 'Undergraduate and visiting researchers',
          'Visiting researcher': 'Undergraduate and visiting researchers'}


def do_alumni(a, branch):
    leaving = a.get("What's changing", '').startswith("I'm leaving")
    member = picked(a, 'If you are leaving, your current card', NOT_LISTED)
    alum = picked(a, 'If you are updating, your alumni entry', NOT_LISTED)
    typed = ' '.join(a.get('Full name', '').split())
    level = LEVELS.get(a.get('Level in the lab', ''), '')
    years = a.get('Years in the lab', '').replace('-', '–')
    position = a.get('Current position', '')
    link = need_url(a.get('Link', ''), 'link')
    header, alumni = load_yaml('alumni')
    lines, warnings = [], []

    if leaving:
        name = member or typed
        if not name:
            raise Problem('Please pick your name in "If you are leaving, your current card".')
        missing = [f for f, v in (('Level in the lab', level), ('Years in the lab', years), ('Current position', position)) if not v]
        if missing:
            raise Problem('When leaving the group, please also fill in: %s.' % ', '.join(missing))
        if member:
            mh, members = load_yaml('members')
            m = find(members, member)
            if not m:
                raise Problem('"%s" is no longer on the People page.' % member)
            members.remove(m)
            save_yaml('members', mh, members)
            lines.append('Removes **%s** from Current members (`_data/members.yml`). Their photo file stays in the repository.' % member)
        row = find(alumni, typed or member) or find(alumni, member)
    else:
        if alum:
            row = find(alumni, alum)
            if not row:
                raise Problem('"%s" is no longer in the alumni table.' % alum)
        else:
            if not typed:
                raise Problem('Please pick your name in "If you are updating, your alumni entry", or give your full name if you are not listed.')
            twin = next((x['name'] for x in alumni if similar(x['name'], typed)), None)
            if twin:
                raise Problem(already_listed(typed, twin, 'in the alumni table', 'alumni'))
            missing = [f for f, v in (('Level in the lab', level), ('Years in the lab', years), ('Current position', position)) if not v]
            if missing:
                raise Problem('You are not in the alumni table yet, so please also fill in: %s.' % ', '.join(missing))
            row = None
        name = alum or typed

    if row:
        if typed and typed != row['name']:
            warnings.append('This **renames** the alumni entry "%s" to "%s". Check that this is intended.' % (row['name'], typed))
        old_level = row['level']
        for k, v in (('name', typed), ('level', level), ('years', years), ('position', position), ('url', link)):
            if v:
                row[k] = v
        if row['level'] != old_level:              # a changed level moves the row to the top of its new group
            alumni.remove(row)
            i = next((k for k, x in enumerate(alumni) if x['level'] == row['level']), len(alumni))
            alumni.insert(i, row)
        lines.append('Updates their row in the alumni table (`_data/alumni.yml`).')
    else:
        row = {'name': typed or name, 'level': level, 'years': years, 'position': position, 'url': link}
        # New alumni go first within their level (the table lists the most recent first).
        i = next((k for k, x in enumerate(alumni) if x['level'] == level), len(alumni))
        alumni.insert(i, row)
        lines.append('Adds them to the alumni table under **%s** (`_data/alumni.yml`).' % level)
    save_yaml('alumni', header, alumni)
    lines += ['', '```yaml', yaml_snippet(row), '```']
    if 'Professor' in row['position']:
        lines += ['', 'Their position mentions "Professor", so they will also appear under Faculty positions. '
                  'Adding them to Collaborators on the Resources page is a manual step.']
    title = ('Rename: %s → %s' % (alum or member, typed)) if warnings else 'Alumni: ' + row['name']
    return title, warnings, lines


def yaml_snippet(d):
    import yaml
    from site_data import _Dumper
    return yaml.dump(d, Dumper=_Dumper, allow_unicode=True, sort_keys=False, width=1000).strip()


HANDLERS = {'news': do_news, 'publication': do_publication, 'profile': do_profile, 'alumni': do_alumni}


def main():
    event = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    issue = event['issue']
    labels = [l['name'] for l in issue.get('labels', [])]
    form = next((l for l in labels if l in HANDLERS), None)
    if not form:
        print('Not an update-form issue; nothing to do.')
        return 0
    answers = parse_issue_form(issue.get('body', ''))
    branch = 'submission/issue-%d' % issue['number']
    try:
        result = HANDLERS[form](answers, branch)
        title, warnings, lines = result if len(result) == 3 else (result[0], [], result[1])
        import sync_forms
        synced = sync_forms.sync()        # keep the forms' name lists in step with the data
    except Problem as e:
        open(out, 'w').write('Thanks for the submission! I could not prepare the website change:\n\n'
                             '> %s\n\nPlease **edit this issue** to fix it (••• menu → Edit); '
                             'I will try again automatically.' % e)
        return 2
    flag = ''
    if answers.get('Submitting for') == 'Someone else':
        warnings.append('Submitted **on behalf of someone else** by @%s. Please check that it is genuine before merging.'
                        % issue['user']['login'])
    for w in warnings:
        flag += '> [!WARNING]\n> %s\n\n' % w
    if synced:
        lines += ['', 'Also updates the name lists in the forms (%s).' % ', '.join('`%s`' % f for f in synced)]
    body = (flag + '\n'.join(lines) +
            '\n\n---\nFrom #%d, submitted by @%s. Merging publishes it; the site rebuilds in about two minutes.'
            '\nTo reject: comment with a one-line reason, then close this pull request.\n\nCloses #%d\n'
            % (issue['number'], issue['user']['login'], issue['number']))
    open(out, 'w').write(title + '\n' + body)
    print(title)
    return 0


if __name__ == '__main__':
    sys.exit(main())
