#!/usr/bin/env python3
"""Build per-locale font subsets for the scripts Quicksand and Inter do not cover.

Twelve locales (CJK, Arabic, Indic, Thai, Hebrew) need a face the site does not
have. The full Noto source for any one of them is 5 to 16 MB, which is not
shippable, and Google's own hosted slicing produces ~120 files per family.

So: take the characters each locale ACTUALLY uses across its six pages, subset
one Noto face down to exactly those, and declare it with a unicode-range listing
exactly those codepoints. A Japanese page ends up loading one file of a few tens
of kB instead of a 16 MB font or a hundred slices.

The face is declared under the family names the templates already use
('Quicksand' and 'Inter'), so no selector anywhere needs to change: unicode-range
is scoped per glyph, so Latin still comes from the real Quicksand and only the
locale's own script resolves to Noto.

Run this after adding or editing a locale's strings, then run build.py.
Requires fontTools and brotli:  pip install fonttools brotli

    python3 subset_fonts.py            # every locale in `needs_font` that is ready
    python3 subset_fonts.py ja ko      # just these
"""
import json, os, re, subprocess, sys, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(ROOT)
FONTS = os.path.join(SITE, "fonts")
CACHE = os.path.join(ROOT, ".fontcache")          # source TTFs, not committed
OUT_CSS = os.path.join(SITE, "fonts-i18n.css")

GF = "https://raw.githubusercontent.com/google/fonts/main/ofl/"

# locale -> (source font path under ofl/, output slug). Locales sharing a script
# share a slug prefix but still get their own subset, because their character
# sets differ and a shared subset would be the union.
SOURCES = {
    "ja":      ("notosansjp/NotoSansJP[wght].ttf",                 "NotoSansJP"),
    "ko":      ("notosanskr/NotoSansKR[wght].ttf",                 "NotoSansKR"),
    "zh-Hans": ("notosanssc/NotoSansSC[wght].ttf",                 "NotoSansSC"),
    "zh-Hant": ("notosanstc/NotoSansTC[wght].ttf",                 "NotoSansTC"),
    "hi":      ("notosansdevanagari/NotoSansDevanagari[wdth,wght].ttf", "NotoSansDevanagari"),
    "mr":      ("notosansdevanagari/NotoSansDevanagari[wdth,wght].ttf", "NotoSansDevanagari"),
    "ar":      ("notosansarabic/NotoSansArabic[wdth,wght].ttf",    "NotoSansArabic"),
    "th":      ("notosansthai/NotoSansThai[wdth,wght].ttf",        "NotoSansThai"),
    "he":      ("notosanshebrew/NotoSansHebrew[wdth,wght].ttf",    "NotoSansHebrew"),
    "bn":      ("notosansbengali/NotoSansBengali[wdth,wght].ttf",  "NotoSansBengali"),
    "ta":      ("notosanstamil/NotoSansTamil[wdth,wght].ttf",      "NotoSansTamil"),
    "te":      ("notosanstelugu/NotoSansTelugu[wdth,wght].ttf",    "NotoSansTelugu"),
}

# Already covered by the self-hosted Latin/Cyrillic/Vietnamese faces. Excluding
# them keeps each subset to the script that actually needs it and stops the
# Noto face from overriding Quicksand for ordinary Latin text.
def already_covered():
    from fontTools.ttLib import TTFont
    import glob
    have = set()
    for f in glob.glob(os.path.join(FONTS, "*.woff2")):
        if os.path.basename(f).startswith("Noto"):
            continue
        have |= set(TTFont(f).getBestCmap().keys())
    return have


def chars_for(locale, doc, template_html):
    """Every character this locale renders, from the catalogue and from its own
    FAQ answer divs in the support template."""
    used = set()
    def eat(s):
        import html as H
        used.update(H.unescape(s))
    for bucket in ("strings", "nav", "ui", "shots"):
        for entry in doc.get(bucket, {}).values():
            if locale in entry:
                eat(entry[locale])
    for page in doc.get("meta", {}).values():
        for field in page.values():
            if locale in field:
                eat(field[locale])
    for m in re.finditer(r'<div data-lang="%s">(.*?)</div>' % re.escape(locale),
                         template_html, re.S):
        eat(m.group(1))
    return used


def fetch(rel):
    os.makedirs(CACHE, exist_ok=True)
    dest = os.path.join(CACHE, os.path.basename(rel).replace("[", "_").replace("]", "_"))
    if not os.path.exists(dest):
        url = GF + urllib.parse.quote(rel)
        print(f"  downloading {os.path.basename(rel)} ...")
        urllib.request.urlretrieve(url, dest)
    return dest


def pinned(src):
    """Clamp the weight axis to the 400-700 the site actually sets.

    These are variable fonts with a 100-900 axis. Nothing on the site asks for
    a weight outside 400-700, and carrying the rest costs real bytes in a CJK
    subset. Cached next to the source so it is done once per family.
    """
    from fontTools import varLib
    out = src.replace(".ttf", "-w400-700.ttf")
    if not os.path.exists(out):
        subprocess.run([sys.executable, "-m", "fontTools.varLib.instancer",
                        src, "wght=400:700", "-o", out],
                       check=True, stdout=subprocess.DEVNULL)
    return out


def main():
    doc = json.load(open(os.path.join(ROOT, "strings.json")))
    tpl = open(os.path.join(ROOT, "templates", "support.html")).read()
    ready = set(doc["ready"])
    want = sys.argv[1:] or [l for l in doc.get("needs_font", []) if l in ready]
    if not want:
        print("subset_fonts: nothing to do (no needs_font locale is ready yet)")
        return

    covered = already_covered()
    faces, done = [], set()
    for loc in want:
        if loc not in SOURCES:
            print(f"  !! no source font mapped for {loc}"); continue
        rel, slug = SOURCES[loc]
        chars = {c for c in chars_for(loc, doc, tpl) if ord(c) not in covered}
        chars = {c for c in chars if c.isprintable() and not c.isspace()}
        if not chars:
            print(f"  {loc}: nothing outside the Latin faces, no subset needed"); continue
        cps = sorted(ord(c) for c in chars)
        src = pinned(fetch(rel))
        out = os.path.join(FONTS, f"{slug}-{loc}.woff2")
        # Deliberately NOT --layout-features=*. pyftsubset's default set already
        # contains every feature these scripts need to shape correctly (init /
        # medi / fina / isol for Arabic, akhn / half / blwf / pstf / rphf for
        # Indic, ccmp / mark / mkmk everywhere); "*" only adds the ones nothing
        # here uses, and cost 20% of the file to carry. Verified against
        # fontTools.subset.Options().layout_features.
        subprocess.run([sys.executable, "-m", "fontTools.subset", src,
                        "--unicodes=" + ",".join(f"U+{c:04X}" for c in cps),
                        "--flavor=woff2",
                        "--output-file=" + out], check=True)
        size = os.path.getsize(out)
        print(f"  {loc}: {len(cps)} glyphs -> {os.path.basename(out)} ({size/1024:.1f} kB)")
        done.add(loc)
        rng = ", ".join(f"U+{c:04X}" for c in cps)
        for family in ("Quicksand", "Inter"):
            for style in ("normal", "italic"):
                faces.append(f"""@font-face {{
  font-family: '{family}';
  font-style: {style};
  font-weight: 400 700;
  font-display: swap;
  src: url(fonts/{slug}-{loc}.woff2) format('woff2');
  unicode-range: {rng};
}}""")

    # `needs_font` is the fallback guard build.py uses when it cannot read the
    # fonts (no brotli). Subsetting a locale is exactly the moment that list
    # goes stale, so clear it here rather than leaving it to be noticed later.
    still = [l for l in doc.get("needs_font", []) if l not in done]
    if still != doc.get("needs_font"):
        doc["needs_font"] = still
        json.dump(doc, open(os.path.join(ROOT, "strings.json"), "w"),
                  ensure_ascii=False, indent=2)
        print(f"  needs_font: cleared {sorted(done)}, {len(still)} left")

    header = """/* GENERATED by _i18n/subset_fonts.py. Do not edit by hand.

   One face per locale, subset to exactly the characters that locale renders,
   declared under the family names the templates already use. unicode-range is
   per glyph, so Latin keeps coming from Quicksand and only this locale's script
   resolves to Noto. Regenerate after changing any of these locales' strings.

   Italic is mapped to the same upright file on purpose: none of these scripts
   has a real italic, and letting the browser synthesise a slant would be worse
   than simply not sloping them. */

"""
    open(OUT_CSS, "w").write(header + "\n".join(faces) + "\n")
    print(f"wrote {os.path.relpath(OUT_CSS, SITE)} ({len(faces)} faces)")


if __name__ == "__main__":
    main()
