# Adding a language to dearnudges.com

Adding a locale is a **data change**, not a code change.

## Steps

1. **Translate.** Add the locale code to every entry in `strings.json`:
   `strings.*` (page copy), `nav.*` (menu labels), `meta.*` (title +
   description per page). Nothing may be left in English except the product
   name "Dear", persona names, journal titles, emails and URLs.
2. **Mark it live.** Add the code to `ready`.
3. **Build.** `python3 _i18n/build.py`
4. **Check it.** Serve locally and look at the page. Confirm the nav, the
   `<title>`, and the switcher.

## What the build does for you

- Renders `/<locale>/<page>.html` for every page.
- Sets `<html lang>`, and `dir="rtl"` for locales listed in `rtl`.
- Emits `hreflang` + `canonical`, restricted to locales in `ready`. **A
  `hreflang` pointing at a URL that 404s invalidates the whole cluster**, so
  planned locales are shown in the switcher but never annotated.
- Localizes `<title>`, `<meta description>`, and the Open Graph / Twitter
  cards, and points `og:url` at that locale's canonical URL.
- Regenerates `sitemap.xml` with `xhtml:link` alternates.
- Rewrites root-relative asset paths for pages served from a subdirectory.

## The font guard

`build.py` **refuses to build** any locale listed in `needs_font`. Quicksand,
Inter and Encode Sans Expanded are Latin-only, and only the latin + latin-ext
subsets are self-hosted, so Japanese, Arabic, Hindi, Thai, Hebrew and the
Indic scripts would silently fall back to a system font: translated, and
visibly not the brand.

To ship one of those 12 locales you must first add a font covering the script,
self-host it, extend `fonts.css`, and remove the locale from `needs_font`.

## Do not

- Hand-edit anything under `/fr/`, `/es/` etc. It is generated and will be
  overwritten. Edit the English page (the template) or `strings.json`.
- Add a locale to `ready` before its strings are translated. Untranslated keys
  fall back to English, which is worse than the language not being offered:
  it looks broken rather than incomplete.
- Point `hreflang` at anything that is not live.
