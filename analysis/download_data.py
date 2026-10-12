#!/usr/bin/env python3
"""
Download and cache the StatsBomb Open Data files needed for the Leverkusen
2023/24 analysis.

Source: public GitHub repo statsbomb/open-data (raw.githubusercontent.com).
Competition 9 (1. Bundesliga), season 281 (2023/24) — a Leverkusen-only
release of 34 matches.

Files fetched:
  - match list:   data/matches/9/281.json
  - events:       data/events/{match_id}.json   (one per match)
  - 360 frames:   data/three-sixty/{match_id}.json  (optional; --with-360)

Everything is cached under ./data (gitignored). Re-running skips files that
are already present, so it is cheap to re-run for a second season: change
COMPETITION_ID / SEASON_ID below (or pass --competition / --season) and go.
"""
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error

RAW_BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")

COMPETITION_ID = 9
SEASON_ID = 281


def fetch(url, dest, retries=3):
    """Download url -> dest unless dest already exists. Returns bytes written."""
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return 0
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    last_err = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                data = resp.read()
            # Validate it parses as JSON before committing to disk.
            json.loads(data)
            tmp = dest + ".tmp"
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, dest)
            return len(data)
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as e:
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url}: {last_err}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--competition", type=int, default=COMPETITION_ID)
    ap.add_argument("--season", type=int, default=SEASON_ID)
    ap.add_argument("--with-360", action="store_true",
                    help="also download the 360 freeze-frame files (large)")
    args = ap.parse_args()

    comp, season = args.competition, args.season

    # 1. Match list.
    matches_path = os.path.join(DATA_DIR, "matches", str(comp), f"{season}.json")
    url = f"{RAW_BASE}/matches/{comp}/{season}.json"
    n = fetch(url, matches_path)
    print(f"match list: {matches_path} ({'downloaded' if n else 'cached'})")

    with open(matches_path) as f:
        matches = json.load(f)
    match_ids = sorted(m["match_id"] for m in matches)
    print(f"{len(match_ids)} matches in {comp}/{season}")

    # 2. Events per match.
    total_bytes = 0
    for i, mid in enumerate(match_ids, 1):
        dest = os.path.join(DATA_DIR, "events", f"{mid}.json")
        url = f"{RAW_BASE}/events/{mid}.json"
        n = fetch(url, dest)
        total_bytes += n
        status = "downloaded" if n else "cached"
        print(f"  [{i:>2}/{len(match_ids)}] events {mid}: {status} "
              f"({os.path.getsize(dest)/1e6:.1f} MB)")

    # 3. Optional 360 frames.
    if args.with_360:
        for i, mid in enumerate(match_ids, 1):
            dest = os.path.join(DATA_DIR, "three-sixty", f"{mid}.json")
            url = f"{RAW_BASE}/three-sixty/{mid}.json"
            try:
                n = fetch(url, dest)
                status = "downloaded" if n else "cached"
                print(f"  [{i:>2}/{len(match_ids)}] 360 {mid}: {status}")
            except RuntimeError as e:
                print(f"  [{i:>2}/{len(match_ids)}] 360 {mid}: MISSING ({e})",
                      file=sys.stderr)

    print(f"done. {total_bytes/1e6:.1f} MB of new event data fetched this run.")


if __name__ == "__main__":
    main()
