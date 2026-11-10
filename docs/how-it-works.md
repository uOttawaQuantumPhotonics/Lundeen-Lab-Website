# How the site works

For whoever maintains the code. Every file also starts with a comment saying what it does.

## The pieces

```
 forms (.github/ISSUE_TEMPLATE)          weekly ORCID check
            │                                    │
            ▼                                    ▼
 scripts/process_submission.py          scripts/orcid_sync.py
            │  edit _data/*.yml or the .bib       │
            └──────────────► pull request ◄───────┘
                                  │  approved by web-admins, merged to main
                                  ▼
             .github/workflows/deploy.yml
               1. scripts/build_publications.py   .bib → _data/publications.json
               2. jekyll build                    pages + layout + data → _site/
               3. publish to GitHub Pages
```

## Jekyll in one paragraph

Jekyll is a static-site generator: it runs once per change and produces plain HTML files, so the live site
has no server code and nothing to hack or update. Each page file (`research.html` …) starts with a few lines
of *front matter* (`layout`, `title`, `nav`) and contains that page's HTML. Jekyll wraps it in
`_layouts/default.html`, which adds the header and footer from `_includes/`. Inside pages,
[Liquid](https://shopify.github.io/liquid/) tags read the data files: `{{ site.data.members }}` is
`_data/members.yml`, and `{% for m in site.data.members %} … {% endfor %}` repeats a card for each member.
`{{ '/assets/…' | relative_url }}` adds the site's base address so links work both on
photonicquantum.info and, if the domain is ever removed, `…github.io/Lundeen-Lab-Website/`.

## Design

The pages were ported from the approved design mockups with their inline `style="…"` attributes kept,
so they look the same. `assets/css/site.css` holds the shared classes and the phone layout
(screens under 860 px), which overrides some inline styles through hook classes such as `.m1`, `.fs34`
and `.hero-sec`; the comment at the top of that file lists them.

## Where each page's content comes from

| Page | Written in the page file | From data |
|---|---|---|
| Home (`index.html`) | research cards, recruiting banner | carousel + selected papers: `_data/home.yml`; latest news: first 3 of `_data/news.yml` |
| Research | everything | — |
| People | PI section, outcome cards | members: `members.yml` (icons: `link_icons.yml`); alumni: `alumni.yml` grouped by `alumni_levels.yml`; alumni count, professor count and Faculty positions computed from `alumni.yml` |
| Publications | banner | `_data/publications.json`, built from `_bibliography/lundeenlab.bib` |
| News | banner | `_data/news.yml` via `_includes/news-card.html` |
| Join us, Resources, Contact | everything | — |

## JavaScript

`assets/js/site.js` (no libraries) does three things: the Home carousel (9 s per slide, paused for
visitors who prefer reduced motion), the alumni filter buttons, and the Publications search, type filter
and Copy BibTeX buttons. All content is in the HTML already, so the site still works without JavaScript.

## The bots

| Workflow | Trigger | Script | Result |
|---|---|---|---|
| `process-submission.yml` | an issue with label `news`, `publication`, `profile` or `alumni` is opened or edited | `process_submission.py` | branch `submission/issue-N` and a pull request, or a comment asking for a fix |
| `rejected-submission.yml` | such a pull request is closed without merging | — | the admin's last comment is posted on the issue, which is closed |
| `orcid-sync.yml` | Mondays, or by hand | `orcid_sync.py` | branch `bot/orcid-sync` and one pull request, if anything is new (works listed in `_bibliography/orcid-skip.txt` are never proposed) |
| `sync-forms.yml` | `members.yml` or `alumni.yml` changes on `main` | `sync_forms.py` | a pull request updating the forms' name lists, if they are out of date |
| `deploy.yml` | push to `main`, or by hand | `build_publications.py` | the live site |

`process_submission.py` reads the form answers by their **labels**, so if you rename a field in a form,
rename it in the script too. The Profile and Moving on forms identify people by drop-down lists of the
current members and alumni. Issue forms can't read data, so `sync_forms.py` writes those lists into the form
files, between `# BEGIN generated` and `# END generated` lines; every submission pull request updates them.
A name typed as "new" that resembles someone already listed (same words ignoring case and accents, or one
name extending the other, e.g. "Manuel Ferrer" and "Manuel Ferrer-García") stops the submission with a
comment; renames and removals are flagged with a warning in the pull request. Shared helpers are in `site_data.py` (YAML, issue parsing, downloads) and
`bibtools.py` (doi.org, arXiv and OpenAlex lookups; adding entries without duplicates).
Python needs only `pyyaml` and `pillow`; `build_publications.py` needs nothing beyond the standard library.

The submission workflow test-builds the site before opening a pull request, so a submission that would
break the build is caught before an admin sees it. Pull requests opened by the bot do not trigger other
workflows (a GitHub rule for its built-in token), which is why that check runs inside the same workflow.

## Previewing locally

```sh
bundle install
python3 scripts/build_publications.py
bundle exec jekyll serve      # http://localhost:4000/
```
