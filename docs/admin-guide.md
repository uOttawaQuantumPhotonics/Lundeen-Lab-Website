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

## Connecting photonicquantum.info

1. At the domain registrar, add DNS records for GitHub Pages:
   four `A` records for the bare domain pointing to 185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153,
   and a `CNAME` record for `www` pointing to `uottawaquantumphotonics.github.io`.
2. Settings → Pages → Custom domain: `photonicquantum.info`; once the check passes, tick **Enforce HTTPS**.
3. In `_config.yml`, set `url: "https://photonicquantum.info"` and `baseurl: ""`, and merge.

(Check GitHub's current instructions, "Managing a custom domain for your GitHub Pages site", before changing DNS.)

## When something goes wrong

- **The site didn't update after a merge:** Actions tab → "Build and publish the website" → the red run shows the error.
  Usually a typo in a YAML file; fix it in a new pull request. The live site keeps the last good version meanwhile.
- **The bot said "unexpected error" on an issue:** open the linked Actions run. Common causes: doi.org or ORCID was down
  (edit the issue later to retry), or a photo link that can't be downloaded.
- **A name list in a form is out of date:** Actions tab → "Update the forms' name lists" → Run workflow, then merge its pull request.
- **Undo a change:** open the merged pull request and click **Revert**; merge the revert pull request.
