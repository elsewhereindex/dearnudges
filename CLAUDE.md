# CLAUDE.md — dearnudges.com

## 🔴 RULE #1: THIS REPOSITORY IS PUBLIC

Everything committed here is world-readable, permanently, including via commit
history after deletion. Removing a file later does not unpublish it.

**Never commit to this repo:**

- Internal specs, audits, reviews or planning documents
- Security findings, vulnerability notes, or commit SHAs of removed content
- Pricing strategy, revenue figures, or business plans
- Personal data of any third party: names, photos, contact details, contracts,
  compensation, or anything identifying an individual
- Credentials, API keys, tokens, certificates, or signing material
- Anything about an individual person without their explicit, documented consent

**Where internal documents belong:** the private `elsewhereindex/friendo` repo,
under `docs/superpowers/specs/`. That applies even when the document is *about*
this website.

**Before adding any file, ask:** would I be comfortable with a journalist, a
competitor, or the person named in it reading this? If not, it does not go here.

Check visibility if unsure:

```bash
gh repo view elsewhereindex/dearnudges --json visibility -q .visibility
```

## What this repo is

The static site for dearnudges.com. Plain HTML and CSS, no build step, no
framework, no dependencies. Deployed from `main` via GitHub Pages, proxied
through Cloudflare (which supplies the security headers, including CSP).

Trilingual EN/FR/ES via a `data-lang` show/hide switcher. The app itself ships
31 languages; the site does not.

## Conventions

- **No em dashes** in any user-facing copy. Ever.
- **No guilt language**: no "missed", "overdue", "streak", "behind".
- **Avoid "no tracking"** phrasing. Use on-device, no accounts, no ads.
- **Facts must match the app.** The free tier is **15** people
  (`Constants.freeNudgeLimit`). Check any number against the source before
  publishing it; the free-tier figure has been wrong in public four separate times.
- **Citations must survive being clicked.** If a statistic carries a DOI, the
  wording has to match what that paper actually reports.
