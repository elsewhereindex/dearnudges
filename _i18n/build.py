#!/usr/bin/env python3
"""
Render one static HTML file per page per locale.

WHY THIS EXISTS
---------------
The site used to serve every language from a single URL, swapping
`<span data-lang="xx">` blocks with JavaScript. Two problems:

1. Google indexes ONE version of a URL. The French and Spanish copy existed but
   earned no search traffic, because Googlebot only ever saw English.
   Google's guidance is explicit: give each language its own URL and link them
   with hreflang.
2. It does not scale. Every string is duplicated inline per language. At 3
   languages that is already 3 copies of every sentence across 8 files; at the
   31 the app supports it would be ~7,000 inline strings and 248 hand-edited
   files.

So: strings live in strings.json, pages are templates, and this renders static
output. Same shape as the apps' gen_android.py. No framework, no runtime
dependency, no build step for the visitor: the output is plain HTML.

LAYOUT
------
    /            English, and the hreflang x-default
    /fr/  /es/   one directory per additional locale

Run:  python3 _i18n/build.py
"""
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "_i18n", "strings.json")
BASE_URL = "https://dearnudges.com"

PAGES = ["index.html", "about.html", "press.html",
         "privacy.html", "research.html", "support.html"]

# Assets that live at the site root. A page rendered into /fr/ has to reach
# them with ../ , so every local reference is rewritten per locale.
ROOT_ASSETS = re.compile(
    r'((?:src|href)=")(?!https?://|//|#|mailto:|/)([^"]*\.(?:png|jpg|jpeg|svg|css|zip|ico|webp))"')

GROUP = re.compile(
    r'<span data-lang="en">(.*?)</span>\s*'
    r'<span data-lang="fr">(.*?)</span>\s*'
    r'<span data-lang="es">(.*?)</span>', re.S)

# The old client-side switcher: a fixed nav of buttons plus its <script>.
LANG_NAV = re.compile(r'<nav class="lang-nav">.*?</nav>', re.S)
LANG_SCRIPT = re.compile(r'<script>\s*function setLang.*?</script>', re.S)


def load():
    with open(DATA, encoding="utf-8") as f:
        return json.load(f)


def lang_url(locale, page):
    """Canonical URL for a page in a locale. English lives at the root."""
    tail = "" if page == "index.html" else page
    return f"{BASE_URL}/{tail}" if locale == "en" else f"{BASE_URL}/{locale}/{tail}"


def hreflang_block(ready, page):
    """Reciprocal hreflang set. Every version lists every version, including
    itself — an incomplete set is silently ignored by Google.

    ONLY locales that actually exist. An hreflang pointing at a URL that 404s
    invalidates the cluster, which is worse than having no annotation at all,
    so planned-but-unbuilt locales are deliberately absent here even though the
    switcher shows them."""
    out = [f'    <link rel="canonical" href="{lang_url("__SELF__", page)}">']
    for loc in ready:
        out.append(f'    <link rel="alternate" hreflang="{loc}" href="{lang_url(loc, page)}">')
    out.append(f'    <link rel="alternate" hreflang="x-default" href="{lang_url("en", page)}">')
    return "\n".join(out)


def switcher(locales, active, page, names, ready, doc):
    """Server-rendered switcher: real links, so it works without JavaScript and
    crawlers can follow it.

    Languages are labelled with ENDONYMS (Deutsch, 日本語), never flags. A flag
    is a country, not a language: Spanish is spoken in twenty-odd countries and
    Arabic in as many, so any flag chosen excludes most of its speakers. This is
    long-standing W3C guidance.

    The compact row carries the live locales as short codes. The "+" opens a
    panel listing everything else in a tidy two-column grid, rather than the
    ragged wrap that variable-width chips produce."""
    endo = doc.get("endonyms", {})
    ui = doc.get("ui", {})
    live, soon = [], []
    for loc in locales:
        if loc in ready:
            label = names.get(loc, loc.upper())
            cls = "lang-btn active" if loc == active else "lang-btn"
            extra = ' aria-current="true"' if loc == active else ""
            live.append(f'<a class="{cls}" hreflang="{loc}"{extra} '
                        f'href="{lang_url(loc, page)}">{label}</a>')
        else:
            soon.append(f'<span class="lang-soon-item">{endo.get(loc, loc)}</span>')
    heading = (ui.get("soon_heading") or {}).get(active, "Coming soon")
    note = (ui.get("app_note") or {}).get(active, "")
    return (
        '<nav class="lang-nav" aria-label="Language">\n'
        f'        {"".join(live)}\n'
        '        <button class="lang-btn lang-more" aria-expanded="false" '
        'aria-controls="lang-more-list" aria-label="More languages" '
        'onclick="this.setAttribute(\'aria-expanded\', '
        'this.getAttribute(\'aria-expanded\')===\'true\'?\'false\':\'true\')">+</button>\n'
        '        <div class="lang-more-list" id="lang-more-list">\n'
        f'            <p class="lang-soon-heading">{heading}</p>\n'
        f'            <div class="lang-soon-grid">{"".join(soon)}</div>\n'
        f'            <p class="lang-soon-note">{note}</p>\n'
        '        </div>\n'
        '    </nav>'
    )


def render(page, locale, doc):
    src = open(os.path.join(ROOT, "_i18n", "templates", page), encoding="utf-8").read()
    strings = doc["strings"]
    locales = doc["locales"]
    ready = set(doc.get("ready", locales))
    names = doc.get("names", {})

    # 1. Collapse each language group down to this locale's copy.
    by_en = {v["en"]: v for v in strings.values()}

    def pick(m):
        en = m.group(1).strip()
        entry = by_en.get(en)
        if not entry:
            return m.group(1)
        return entry.get(locale) or entry["en"]

    out = GROUP.sub(pick, src)

    # 2. Correct <html lang> for the locale actually being served.
    rtl = locale in doc.get("rtl", [])
    attrs = f'lang="{locale}"' + (' dir="rtl"' if rtl else "")
    out = re.sub(r'<html lang="[^"]*">', f'<html {attrs}>', out, count=1)

    # 3. Rewrite root-relative assets for pages served from a subdirectory.
    if locale != "en":
        out = ROOT_ASSETS.sub(lambda m: f'{m.group(1)}../{m.group(2)}"', out)

    # 4. hreflang + canonical.
    block = hreflang_block([l for l in locales if l in ready], page).replace("__SELF__", locale)
    out = out.replace("</head>", block + "\n</head>", 1)

    # 4b. Title and meta description, plus their Open Graph and Twitter twins.
    #     These are what a search engine and a shared link actually display, so
    #     leaving them English made a French URL present in English.
    meta = (doc.get("meta", {}) or {}).get(page, {})
    t = (meta.get("title") or {}).get(locale)
    dsc = (meta.get("desc") or {}).get(locale)
    if t:
        out = re.sub(r'<title>.*?</title>', lambda _m: f'<title>{t}</title>', out, count=1, flags=re.S)
        for prop in ('og:title', 'twitter:title'):
            out = re.sub(r'(<meta (?:property|name)="' + prop + r'" content=")[^"]*"',
                         lambda m: m.group(1) + t + '"', out)
    if dsc:
        out = re.sub(r'(<meta name="description" content=")[^"]*"',
                     lambda m: m.group(1) + dsc + '"', out, count=1)
        for prop in ('og:description', 'twitter:description'):
            out = re.sub(r'(<meta (?:property|name)="' + prop + r'" content=")[^"]*"',
                         lambda m: m.group(1) + dsc + '"', out)
    # og:url must point at this locale's canonical URL, not the English one.
    out = re.sub(r'(<meta property="og:url" content=")[^"]*"',
                 lambda m: m.group(1) + lang_url(locale, page) + '"', out)

    # 4c. Screenshot alt text and caption. Alt text is content, so it is
    #     translated like everything else; an English alt on a French page is
    #     the same defect as an English heading, just invisible to sighted users.
    shots = doc.get("shots", {})
    for token, key in (("SHOT_ALT1", "alt1"), ("SHOT_ALT2", "alt2"),
                       ("SHOT_ALT3", "alt3"), ("SHOT_CAPTION", "caption")):
        val = (shots.get(key) or {}).get(locale) or (shots.get(key) or {}).get("en", "")
        out = out.replace(token, val)

    # 5. Navigation chrome. These labels sit as bare text in the markup rather
    #    than in language spans, so they stayed English on every locale until
    #    now. Anchored on the surrounding tags to avoid touching body copy that
    #    happens to contain the same word.
    nav = doc.get("nav", {})
    NAVMAP = [("nav_home", "Home"), ("nav_about", "About"), ("nav_research", "Research"),
              ("nav_faq", "FAQ"), ("nav_privacy", "Privacy"), ("nav_press", "Press")]
    for key, en in NAVMAP:
        word = nav.get(key, {}).get(locale, en)
        if word == en:
            continue
        # Bottom/top nav items: the label is the last text node in the anchor.
        out = re.sub(r'(</svg>\s*)' + en + r'(\s*</a>)', r'\g<1>' + word + r'\g<2>', out)
        # Footer links: <a href="about.html">About</a>
        out = re.sub(r'(<a href="[a-z]+\.html">)' + en + r'(</a>)', r'\g<1>' + word + r'\g<2>', out)

    # 6. Replace the JS switcher with rendered links, and drop its script.
    out = LANG_NAV.sub(lambda _m: switcher(locales, locale, page, names, ready, doc), out, count=1)
    out = LANG_SCRIPT.sub("", out)
    return out


def sitemap(doc):
    """One <url> per page per locale, each listing every alternate."""
    locales, ready = doc["locales"], set(doc.get("ready", doc["locales"]))
    rows = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for page in PAGES:
        for loc in locales:
            if loc not in ready:
                continue
            rows.append(f"  <url>\n    <loc>{lang_url(loc, page)}</loc>")
            for alt in locales:
                if alt in ready:
                    rows.append(f'    <xhtml:link rel="alternate" hreflang="{alt}" '
                                f'href="{lang_url(alt, page)}"/>')
            rows.append(f'    <xhtml:link rel="alternate" hreflang="x-default" '
                        f'href="{lang_url("en", page)}"/>')
            rows.append("  </url>")
    rows.append("</urlset>")
    return "\n".join(rows) + "\n"


def preflight(doc):
    """Refuse to build a locale that would render in a fallback font.

    Quicksand, Inter and Encode Sans Expanded are Latin-only, and only the
    latin + latin-ext subsets are self-hosted. Shipping Japanese or Arabic
    would silently drop to a system font: translated, and visibly off-brand.
    Marking such a locale `ready` is therefore a mistake worth failing on
    rather than discovering on the live site."""
    bad = [l for l in doc.get("ready", []) if l in doc.get("needs_font", [])]
    if bad:
        raise SystemExit(
            f"REFUSING TO BUILD: {bad} need a script the self-hosted fonts do not "
            f"cover. Add a font with those glyphs and extend fonts.css first, or "
            f"remove them from `ready`.")


def main():
    doc = load()
    preflight(doc)
    ready = doc.get("ready", doc["locales"])
    written = 0
    for locale in doc["locales"]:
        if locale not in ready:
            continue
        outdir = ROOT if locale == "en" else os.path.join(ROOT, locale)
        if locale != "en":
            os.makedirs(outdir, exist_ok=True)
        for page in PAGES:
            html = render(page, locale, doc)
            dest = os.path.join(outdir, page)
            with open(dest, "w", encoding="utf-8") as f:
                f.write(html)
            written += 1
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(sitemap(doc))
    print(f"rendered {written} files across {len(ready)} locales")
    print(f"wrote sitemap.xml")


if __name__ == "__main__":
    sys.exit(main())
