#!/usr/bin/env python3
"""Refresh the facts inside dear-press-kit.zip.

The kit is what a journalist actually downloads, and it is the easiest thing on
the site to forget: it is a binary, so it never shows up in a diff and no build
step touches it. Assembled by hand on 18 August 2026, it was still claiming 31
languages and "The website is currently in English, French and Spanish" a month
after the site shipped in 31 locales and the app shipped its 32nd language.

This rewrites START-HERE.html inside the ZIP from stats.json and the locale
list in _i18n/strings.json, then repacks. Screenshots and the icon are carried
through untouched, so the kit keeps its contents and only its facts change.

Run:  python3 tools/build_press_kit.py
"""
import json, pathlib, re, shutil, tempfile, zipfile, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
ZIP = ROOT / "dear-press-kit.zip"
SHEET = "dear-press-kit/START-HERE.html"

# The app ships more languages than the site: a language is released in the app
# first and reaches dearnudges.com once its strings are translated. Urdu is the
# current gap. Two different numbers, both correct, so the kit has to say which
# is which rather than print one figure twice.
APP_LANGS = json.loads((ROOT / "stats.json").read_text())["languages"]
SITE_LOCALES = len(json.loads((ROOT / "_i18n" / "strings.json").read_text())["ready"])

# Endonyms, in the order the kit already lists them, plus any the app has
# gained since. Kept here rather than derived, because the kit lists the app's
# languages and strings.json only knows the site's.
EXTRA_ENDONYMS = ["اردو"]


def refresh(html):
    today = datetime.date.today().strftime("%-d %B %Y")
    html = re.sub(r"(Press kit &middot; updated )[^&]*( &middot;)",
                  lambda m: f"{m.group(1)}{today}{m.group(2)}", html, count=1)

    html = html.replace("<dt>Languages</dt><dd>31</dd>",
                        f"<dt>Languages</dt><dd>{APP_LANGS}</dd>", 1)
    html = html.replace("<h2>Languages &mdash; 31</h2>",
                        f"<h2>Languages &mdash; {APP_LANGS}</h2>", 1)
    html = html.replace("Dear ships fully translated in 31 languages",
                        f"Dear ships fully translated in {APP_LANGS} languages", 1)

    # The list ended at Kiswahili and never gained the languages added since.
    last = "<span>Kiswahili</span>"
    assert html.count(last) == 1
    for name in EXTRA_ENDONYMS:
        if f"<span>{name}</span>" not in html:
            html = html.replace(last, last + f"<span>{name}</span>", 1)
            last = f"<span>{name}</span>"

    html = html.replace(
        "The website is currently in English, French and Spanish.",
        f"dearnudges.com is available in {SITE_LOCALES} of these languages.", 1)
    return html


def main():
    with zipfile.ZipFile(ZIP) as z:
        names = z.namelist()
        assert SHEET in names, f"{SHEET} not in the kit"
        blobs = {n: z.read(n) for n in names}
        infos = {i.filename: i for i in z.infolist()}

    before = blobs[SHEET].decode("utf-8")
    after = refresh(before)
    if after == before:
        print("press kit already current; nothing written")
        return
    blobs[SHEET] = after.encode("utf-8")

    tmp = pathlib.Path(tempfile.mkstemp(suffix=".zip")[1])
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for n in names:
            z.writestr(infos[n], blobs[n])
    shutil.move(str(tmp), ZIP)
    print(f"press kit refreshed: app {APP_LANGS} languages, "
          f"site {SITE_LOCALES} locales, {len(names)} entries, "
          f"{ZIP.stat().st_size // 1024} kB")


if __name__ == "__main__":
    main()
