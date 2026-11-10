# Admin guide

For the `web-admins` team (currently JLOttawa and mffg1993), who approve changes and look after the settings.

## Reviewing a submission

You get a GitHub email for each new pull request. Open it and check:

- **Files changed** tab: the text is right and appropriate to publish.
- **Photos:** the pull request shows the cropped headshot or news photo.
- **"Submitted on behalf of someone else"** warning: make sure the person agreed.

Then **Review changes → Approve**, and **Merge pull request**. Approving alone doesn't publish anything. If Merge is blocked with "Review required" (your own approval doesn't count when you pushed to the pull request), tick "Merge without waiting for requirements to be met (bypass rules)". Then delete the branch (or turn on Settings → General → Automatically delete head branches). The site is live about two minutes later
(progress: the **Actions** tab, workflow "Build and publish the website").

To make a small fix before merging, edit the file in the pull request yourself (Files changed → ••• → Edit file).

To **decline**: write a one-line reason as a comment, then **Close pull request**.
The bot posts your reason on the submitter's issue and closes it.

The weekly ORCID check opens a pull request titled "Publications: N new from ORCID" when it finds something.
Delete any entries you don't want (edit `_bibliography/lundeenlab.bib` in the pull request), then merge.

## One-time setup (do these once, in this order)

1. **Publish with Actions.** Settings → Pages → Build and deployment → Source: **GitHub Actions**.
2. **Let the bot open pull requests.** Settings → Actions → General → Workflow permissions:
   keep **Read repository contents and packages permissions** (each workflow asks for the extra access it needs)
   and tick **Allow GitHub Actions to create and approve pull requests**.
   If the box is greyed out, tick the same option in the organization's settings
   (Organization → Settings → Actions → General) first.
3. **Create the four labels** the forms use: Issues → Labels → New label:
   `news`, `publication`, `profile`, `alumni`.
4. **Create the approvers team.** Organization → Teams → New team `web-admins`, add JLOttawa and mffg1993,
   then in this repository Settings → Collaborators and teams, give `web-admins` the **Maintain** role.
5. **Protect main.** Settings → Branches → Add branch ruleset (or classic rule) for `main`:
   - Require a pull request before merging, with **1 approval**
   - **Require review from Code Owners** (the owners are set in `.github/CODEOWNERS`)
   - Optionally allow the admins to bypass, so you can merge your own small fixes without a second person.

## Changing who approves

Add or remove people in the `web-admins` team. Nothing in the code needs to change.

## The domain: photonicquantum.info

Connected on 10 Nov 2026. How it is set up, in case it needs fixing:

- **Registrar and DNS:** Squarespace (Domains → photonicquantum.info). The nameservers are Squarespace's own
  (`nsd1`–`nsd4.squarespacedns.com`). Until Nov 2026 they pointed to Amazon (AWS Route 53, from the old Uniweb site),
  and records added in Squarespace were ignored. If Squarespace shows "You're using custom nameservers", that has been undone.
- **DNS records** (Squarespace → DNS → Custom records):

  | Type | Name | Data |
  | --- | --- | --- |
  | A | `@` | 185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153 (four records) |
  | CNAME | `www` | `uottawaquantumphotonics.github.io` |
  | TXT | `_github-pages-challenge-uottawaquantumphotonics` | the code from Organization → Settings → Pages (domain verification) |

  Leave the `_domainconnect` record and the two `googlehosted.com` records alone.
- **GitHub:** Repository → Settings → Pages → Custom domain `photonicquantum.info`, **Enforce HTTPS** ticked.
  Organization → Settings → Pages: domain verification (still pending on 10 Nov, waiting for DNS caches).
- **After any change of address**, run Actions → "Build and publish the website" → Run workflow; otherwise
  images and styles point at the old address.
- **Check DNS from anywhere:** https://dnschecker.org (types A, CNAME, NS, TXT).
- **Waiting:** a nameserver change, or a "record not found" answer seen before a change, can take up to 24 hours to clear.

## When something goes wrong

- **The site didn't update after a merge:** Actions tab → "Build and publish the website" → the red run shows the error.
  Usually a typo in a YAML file; fix it in a new pull request. The live site keeps the last good version meanwhile.
- **The bot said "unexpected error" on an issue:** open the linked Actions run. Common causes: doi.org or ORCID was down
  (edit the issue later to retry), or a photo link that can't be downloaded.
- **A name list in a form is out of date:** Actions tab → "Update the forms' name lists" → Run workflow, then merge its pull request.
- **Undo a change:** open the merged pull request and click **Revert**; merge the revert pull request.
