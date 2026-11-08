# Updating the website

There are two ways to change the site.

- **The forms** (easiest; no coding). Anyone with a free GitHub account can use them.
- **Editing files directly** on GitHub, for page text and anything the forms don't cover.

Either way, nothing goes live until an admin approves it (see [admin-guide.md](admin-guide.md)).

> Everything on GitHub here is public, including form submissions before they are approved.
> Don't include anything you wouldn't want published.

## The four forms

Open them from the repository's **Issues → New issue** page, or from the links below.

| Form | Use it to | What changes |
|---|---|---|
| [News item](https://github.com/uOttawaQuantumPhotonics/Lundeen-Lab-Website/issues/new?template=news.yml) | announce a paper, award, event, new member… | a card on the News page; the three newest also show on Home |
| [Add a publication](https://github.com/uOttawaQuantumPhotonics/Lundeen-Lab-Website/issues/new?template=publication.yml) | add a paper, preprint, conference paper or patent | the Publications page |
| [My profile](https://github.com/uOttawaQuantumPhotonics/Lundeen-Lab-Website/issues/new?template=profile.yml) | join Current members, or update your card (role, project, bio, photo, links) | the People page |
| [Moving on / alumni update](https://github.com/uOttawaQuantumPhotonics/Lundeen-Lab-Website/issues/new?template=alumni-update.yml) | leave the group, or say where you are now | the Alumni table on the People page |

After you click **Submit**:

1. Within a minute or two the bot comments on your issue with a link to a pull request,
   or, if something needs fixing (a date in the wrong format, a photo it can't open), it says what.
   To fix it, **edit your issue** (••• → Edit); the bot tries again automatically.
2. An admin reviews and merges the pull request. The bot closes your issue.
3. About two minutes later the change is on the live site.

Tips

- **Photos:** drag the file into the Photo box. Headshots are cropped to a square (400 × 400);
  send one at least that size with your head near the top-centre. News photos are resized to 1200 px wide.
- **Profile updates:** only the fields you fill in change; leave the rest empty.
- **Links on your card:** only the links you give appear, as small icons.
- **Publications:** one of DOI, arXiv number or BibTeX is enough; the bot fetches the rest.
  If the paper is already listed as a preprint, its entry is replaced by the published version.
  Every week the bot also checks Jeff's ORCID record and proposes anything missing.
- **No GitHub account?** Email Jeff at jlundeen@uottawa.ca.

## Editing files directly

On GitHub, open a file, click the pencil icon, make your change, then choose
**"Create a new branch for this commit and start a pull request"**. An admin approves it like any submission.

### Editing page text

Each page is one HTML file in the top folder: `research.html`, `join.html`, `resources.html`,
`contact.html`, and the fixed parts of `index.html` (Home), `people.html` and `news.html`.
The text sits between tags, e.g.

```html
<p style="margin: 0; font-size: 16px; line-height: 1.7; color: #b5bfca">Change only this text.</p>
```

Change the words; leave the `<tags>` and `style="..."` alone so the design stays as approved.
Lines starting with `{%` or containing `{{ }}` are Jekyll instructions; don't change them unless you know Jekyll.

### Editing data files

These YAML files hold the content that changes often. Each starts with a comment explaining its fields.

| File | What it holds |
|---|---|
| `_data/members.yml` | Current members (the forms edit this) |
| `_data/alumni.yml` | Alumni table; anyone whose position mentions "Professor" also appears under Faculty positions |
| `_data/alumni_levels.yml` | the alumni groups and their order |
| `_data/news.yml` | news items, newest first |
| `_data/home.yml` | Home page photo carousel and "Selected papers" |
| `_data/nav.yml` | the main menu |

YAML rules of thumb: keep the indentation exactly as in the neighbouring entries (spaces, not tabs);
put text in `"double quotes"` if it contains a colon followed by a space (`: `); `""` means "empty".
If you break the format, the build fails and the live site simply stays as it was. GitHub emails the admins.

### Replacing the whole publication list

The Publications page is generated from `_bibliography/lundeenlab.bib`, a Zotero export.
To refresh it, export the Zotero library as BibTeX and upload it over that file.
Papers added by the form or the ORCID bot live only in that file, so add them to Zotero too,
or they will be dropped by the next export.

### Adding or changing a photo

Upload the image into the right folder under `assets/img/` (`people/`, `photos/`, `news/`, `logos/`, `maps/`),
then refer to it by file name in the page or data file. Keep photos under about 400 KB
(1600 px wide is plenty for a banner).
