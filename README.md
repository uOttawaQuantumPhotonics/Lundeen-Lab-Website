# Lundeen Lab for Quantum Photonics: website

The website of the [Lundeen Lab](https://uottawaquantumphotonics.github.io/Lundeen-Lab-Website/) at the University of Ottawa.
It is built with [Jekyll](https://jekyllrb.com/) and hosted free on GitHub Pages.

## I want to…

| …do this | …go here |
|---|---|
| Add news, a paper, my profile, or my alumni update | [Open the forms](https://github.com/uOttawaQuantumPhotonics/Lundeen-Lab-Website/issues/new/choose), or read [docs/updating-content.md](docs/updating-content.md) |
| Edit page text (Research, Join us, Contact…) | [docs/updating-content.md](docs/updating-content.md#editing-page-text) |
| Approve submissions, change admins, connect the domain | [docs/admin-guide.md](docs/admin-guide.md) |
| Understand how the site is put together | [docs/how-it-works.md](docs/how-it-works.md) |

## How an update goes live

1. Someone fills in one of the four forms (an issue on this repository).
2. A bot prepares the change and opens a pull request.
3. An admin (the `web-admins` team) reviews it and merges.
4. The site rebuilds and is live about two minutes later.

Submissions are public on GitHub as soon as they are sent.

## Where things are

```
index.html, research.html, people.html, publications.html,
news.html, join.html, resources.html, contact.html      the eight pages
_data/            content kept as data: members, alumni, news, Home slides, menu
_bibliography/    lundeenlab.bib, the source of the Publications page
assets/           css/site.css, js/site.js, img/ (photos, logos, headshots, maps)
_layouts/, _includes/   the frame shared by every page (header, footer, news card)
scripts/          Python used by the bots and the build
.github/          the update forms (ISSUE_TEMPLATE) and automation (workflows)
docs/             these guides
```

## Preview on your own computer (optional)

You need Ruby and Python 3.

```sh
bundle install                          # once
python3 scripts/build_publications.py   # whenever the .bib file changes
bundle exec jekyll serve                # then open http://localhost:4000/Lundeen-Lab-Website/
```

Copyright © Jeff Lundeen. This website does not constitute official University of Ottawa content.
