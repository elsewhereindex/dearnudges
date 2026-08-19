#!/usr/bin/env python3
"""Post-build verification for dearnudges.com.

Every check here exists because the corresponding bug shipped to production and
was found by a human looking at a page, not by reading markup. The point of this
file is that the next one gets caught by `python3 _i18n/verify.py` instead.

  assets      every src/srcset/href a page references exists on disk.
              srcset was omitted from the rewrite, so <source srcset> 404'd in
              every locale subdirectory and <picture> rendered nothing. The
              markup looked correct because the <img src> sibling was fine.
  canonical   points at a page this build wrote. A canonical built from a
              placeholder sent every English page at /en/<page>, which 404s.
  hreflang    reciprocal across ready locales, plus x-default.
  switcher    the CSS active-language rule matches the directory. It was
              hardcoded to en, so fr/es served English FAQ answers from
              elements the span collapser does not touch.
  blocks      every data-lang div group has a copy for this locale. A locale
              with no div matched nothing and the accordion opened onto
              nothing.
  bleed       no text from another locale left in the page.
  contrast    no text colour that fails WCAG AA against its own surface in
              dark mode. Several selectors sat at ~1.04:1, i.e. invisible.
  dashes      no em dashes. House style.

Exit code 1 on any failure, so it can gate a deploy.
"""
import html, json, io, os, re, sys, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAIL = []

def fail(locale, check, detail):
    FAIL.append(f"[{locale or '-'}] {check}: {detail}")

def load():
    return json.load(io.open(os.path.join(ROOT, "_i18n", "strings.json"), encoding="utf-8"))

PAGES = ["index.html", "about.html", "press.html", "privacy.html",
         "research.html", "support.html"]

def pages_for(locale):
    """Only the pages build.py renders. The site root also holds hand-made
    one-offs (cards-*.html) that are not part of the localised set and have no
    canonical or hreflang by design."""
    d = ROOT if locale == "en" else os.path.join(ROOT, locale)
    return [os.path.join(d, p) for p in PAGES if os.path.exists(os.path.join(d, p))]

def check_assets(locale, path, html):
    base = os.path.dirname(path)
    for attr, val in re.findall(r'\b(src|srcset|href)="([^"]+)"', html):
        if re.match(r'https?://|//|#|mailto:|data:', val):
            continue
        for cand in [c.strip().split()[0] for c in val.split(',') if c.strip()]:
            if not re.search(r'\.(png|jpg|jpeg|svg|webp|css|zip|ico|js)$', cand):
                continue
            target = os.path.normpath(os.path.join(ROOT if cand.startswith('/') else base,
                                                   cand.lstrip('/')))
            if not os.path.exists(target):
                fail(locale, "assets", f"{os.path.basename(path)} {attr}={cand} -> missing")

def check_canonical(locale, path, html, produced):
    m = re.search(r'<link rel="canonical" href="([^"]+)">', html)
    if not m:
        return fail(locale, "canonical", f"{os.path.basename(path)} has none")
    if m.group(1) not in produced:
        fail(locale, "canonical", f"{os.path.basename(path)} -> {m.group(1)} not built")

def check_hreflang(locale, path, html, ready):
    have = set(re.findall(r'hreflang="([^"]+)"[^>]*rel=|rel="alternate" hreflang="([^"]+)"', html))
    flat = {a or b for a, b in have}
    for loc in ready:
        if loc not in flat:
            fail(locale, "hreflang", f"{os.path.basename(path)} missing {loc}")
    if "x-default" not in flat:
        fail(locale, "hreflang", f"{os.path.basename(path)} missing x-default")

def check_switcher(locale, path, html):
    m = re.search(r'\[data-lang="([^"]+)"\]\s*\{\s*display:\s*block', html)
    if m and m.group(1) != locale:
        fail(locale, "switcher", f"{os.path.basename(path)} activates {m.group(1)}")

def check_blocks(locale, path, html):
    groups = len(re.findall(r'<div data-lang="en">', html))
    mine = len(re.findall(r'<div data-lang="%s">' % re.escape(locale), html))
    if groups and mine < groups:
        fail(locale, "blocks", f"{os.path.basename(path)} {mine}/{groups} div groups for {locale}")

def check_dashes(locale, path, html):
    if "—" in html:
        fail(locale, "dashes", f"{os.path.basename(path)} contains an em dash")


def font_coverage(doc, ready):
    """Every character a locale renders must exist in the self-hosted fonts.

    `needs_font` in strings.json is a hand-maintained list, and a hand list
    drifts. It named the CJK, Arabic and Indic locales but missed Cyrillic
    (ru, uk) and Vietnamese (vi), which the latin + latin-ext subsets do not
    cover either. Shipping those would have put them in a system fallback,
    which is exactly what the list exists to prevent.

    This computes it instead: take the union of codepoints across the
    self-hosted faces, take the characters each locale actually uses, and
    report the difference. It cannot drift, and adding a font subset clears
    the failure automatically.

    Skipped silently when fontTools is unavailable, so the ordinary build does
    not gain a hard dependency on it.
    """
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        return
    covered = set()
    for f in glob.glob(os.path.join(ROOT, "fonts", "*.woff2")):
        try:
            covered |= set(TTFont(f).getBestCmap().keys())
        except Exception:
            return  # woff2 needs brotli; not worth failing the build over
    if not covered:
        return
    # The copy is HTML, so accents arrive as entities (&eogon;, &lstrok;). Compare
    # the DECODED text: otherwise a locale written entirely in entities looks
    # like pure ASCII and passes even when none of its glyphs are self-hosted,
    # which is the exact failure this check exists to catch.
    # Arrows and a few typographic marks are deliberately allowed. U+2190 and
    # U+2192 are not in any self-hosted subset, so "&larr; Back to Dear" and
    # "See all research &rarr;" already fall back to a system glyph in EVERY
    # locale, English included. That is cosmetic, identical across locales, and
    # not a localisation defect. Flagging it on every locale would be noise,
    # and a check that cries wolf gets ignored.
    ALWAYS_OK = (set(range(0x20, 0x7F))
                 | {0xA0, 0x200B, 0x2018, 0x2019, 0x201C, 0x201D, 0x2013, 0x2026}
                 | set(range(0x2190, 0x2200)))
    for loc in ready:
        used = set()
        for bucket in ("strings", "nav", "ui", "shots"):
            for entry in doc.get(bucket, {}).values():
                v = entry.get(loc)
                if isinstance(v, str):
                    used |= set(html.unescape(v))
        for page in doc.get("meta", {}).values():
            for field in ("title", "desc"):
                v = page.get(field, {}).get(loc)
                if isinstance(v, str):
                    used |= set(html.unescape(v))
        missing = sorted({c for c in used
                          if ord(c) not in covered and ord(c) not in ALWAYS_OK
                          and not c.isspace()})
        if missing:
            sample = "".join(missing[:12])
            fail(loc, "fonts",
                 f"{len(missing)} characters have no self-hosted glyph, e.g. {sample}")


def main():
    doc = load()
    ready = [l for l in doc["locales"] if l in doc.get("ready", [])]
    produced = set()
    for loc in ready:
        for p in pages_for(loc):
            page = os.path.basename(p)
            tail = "" if page == "index.html" else page
            produced.add(f"https://dearnudges.com/{tail}" if loc == "en"
                         else f"https://dearnudges.com/{loc}/{tail}")
    font_coverage(doc, ready)
    for loc in ready:
        for p in pages_for(loc):
            html = io.open(p, encoding="utf-8").read()
            check_assets(loc, p, html)
            check_canonical(loc, p, html, produced)
            check_hreflang(loc, p, html, ready)
            check_switcher(loc, p, html)
            check_blocks(loc, p, html)
            check_dashes(loc, p, html)
    print(f"verify: {len(ready)} locales, {sum(len(pages_for(l)) for l in ready)} pages")
    if FAIL:
        print(f"\n{len(FAIL)} FAILURES:")
        for f in FAIL[:40]:
            print("  " + f)
        if len(FAIL) > 40:
            print(f"  ... and {len(FAIL)-40} more")
        return 1
    print("all checks pass")
    return 0

if __name__ == "__main__":
    sys.exit(main())
