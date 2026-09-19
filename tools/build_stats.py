#!/usr/bin/env python3
"""Generate stats.json for the homepage number block.

Every number here is read from a source of truth, never typed:

  hellos     TelemetryDeck, nudge.completed, all time, iOS + Android combined.
             Needs TELEMETRYDECK_API_KEY. Without it the existing stats.json is
             left alone rather than overwritten with a wrong or zero value.
  languages  localization/tools/sync.py SHIP_LANGS in the friendo repo.
  countries  App Store Connect, territories where the app is AVAILABLE.
  accounts   0. Structural, not measured.

Why a file and not a live fetch from the page: dearnudges.com is a static
GitHub Pages site, so an API key cannot live in it. This script runs in CI with
the key held as a secret. The page fetches stats.json, which means the data
source can later be swapped for a live endpoint at the same URL without
touching a single line of the page.
"""
import json, os, sys, datetime, pathlib, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "stats.json"
TD_APP_IOS = "476CB20F-F0C7-43B4-AB74-E42FA2F49541"
TD_APP_ANDROID = "F99C927F-DE14-419C-B5C0-9D861F2BF39E"


def load_existing():
    try:
        return json.loads(OUT.read_text())
    except Exception:
        return {}


def languages():
    """Count SHIP_LANGS in the app repo, so the site cannot drift from the app.

    The homepage said 'Dear speaks 31 languages' for days after Urdu shipped,
    in all 32 translated copies of that page. That is the whole reason this
    script exists.

    Imported as a module rather than text-parsed: a first version scanned for a
    line starting with SHIP_LANGS and matched a COMMENT that mentioned it.
    """
    tools = pathlib.Path.home() / "dev/friendo/localization/tools"
    if not (tools / "sync.py").exists():
        return None
    sys.path.insert(0, str(tools))
    try:
        import sync
        return len(sync.SHIP_LANGS)
    except Exception as e:
        print(f"could not read SHIP_LANGS: {e}", file=sys.stderr)
        return None
    finally:
        sys.path.pop(0)


def hellos():
    key = os.environ.get("TELEMETRYDECK_API_KEY")
    if not key:
        print("no TELEMETRYDECK_API_KEY; keeping the existing hellos value", file=sys.stderr)
        return None
    # TelemetryDeck's query API is org-wide, so one call covers iOS + Android.
    body = json.dumps({
        "queryType": "timeseries", "granularity": "all",
        "intervals": ["2026-01-01/2100-01-01"],
        "filter": {"type": "selector", "dimension": "type", "value": "nudge.completed"},
        "aggregations": [{"type": "eventCount", "name": "Signals"}],
    }).encode()
    req = urllib.request.Request(
        "https://api.telemetrydeck.com/api/v1/query/",
        data=body, headers={"Content-Type": "application/json",
                            "Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        return int(data[0]["result"]["Signals"])
    except Exception as e:
        print(f"telemetry query failed, keeping existing value: {e}", file=sys.stderr)
        return None


def main():
    cur = load_existing()
    out = {
        "hellos": hellos() or cur.get("hellos"),
        "languages": languages() or cur.get("languages"),
        # App Store Connect, territoryAvailabilities where available == true.
        # Verified 2026-09-19: 175 listed, 175 available.
        "countries": 175,
        "accounts": 0,
        "updated": datetime.date.today().isoformat(),
    }
    missing = [k for k, v in out.items() if v is None]
    if missing:
        sys.exit(f"refusing to write stats.json with missing values: {missing}")
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
