#!/usr/bin/env python3
"""
scripts/sync_forms.py: keep the name lists in the update forms in step with the data.

GitHub issue forms can't read the site's data, so their drop-down lists are written into
the form files. This script rewrites the lines between

        # BEGIN generated: current members (scripts/sync_forms.py)
        # END generated

(and the same for "alumni") from _data/members.yml and _data/alumni.yml, in page order.

It runs automatically:
  - inside every submission pull request (process_submission.py calls it), and
  - after any change to those data files reaches main (.github/workflows/sync-forms.yml),
    which opens a pull request if the lists were out of date (e.g. after a hand edit).
You can also run it yourself:  python3 scripts/sync_forms.py
Prints the files it changed; exit code 0 either way.
"""
import re
import sys

from site_data import ROOT, load_yaml

FORMS = ROOT / '.github' / 'ISSUE_TEMPLATE'

# Fixed first option of each generated list.
FIRST = {('profile.yml', 'current members'): 'New member (not listed yet)',
         ('alumni-update.yml', 'current members'): 'Not listed',
         ('alumni-update.yml', 'alumni'): 'Not listed'}


def yaml_item(name):
    """One list line, quoted so names with ':' or '#' stay valid YAML."""
    return '- "%s"' % name.replace('\\', '\\\\').replace('"', '\\"')


def names(kind):
    _, rows = load_yaml('members' if kind == 'current members' else 'alumni')
    seen, out = set(), []
    for r in rows:
        if r['name'] not in seen:                 # a drop-down can't repeat an option
            seen.add(r['name'])
            out.append(r['name'])
    return out


def sync():
    changed = []
    for (form, kind), first in FIRST.items():
        path = FORMS / form
        text = path.read_text(encoding='utf-8')
        pattern = re.compile(r'(?P<indent>[ \t]*)# BEGIN generated: %s \(scripts/sync_forms\.py\)\n.*?(?P=indent)# END generated'
                             % re.escape(kind), re.S)
        m = pattern.search(text)
        if not m:
            sys.exit('%s: no "BEGIN generated: %s" block found' % (form, kind))
        ind = m.group('indent')
        block = '\n'.join([ind + '# BEGIN generated: %s (scripts/sync_forms.py)' % kind] +
                          [ind + yaml_item(n) for n in [first] + names(kind)] +
                          [ind + '# END generated'])
        new = text[:m.start()] + block + text[m.end():]
        if new != text:
            path.write_text(new, encoding='utf-8')
            changed.append(form)
    return sorted(set(changed))


if __name__ == '__main__':
    for f in sync():
        print('updated', f)
