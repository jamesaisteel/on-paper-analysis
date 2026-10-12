# On Paper — analysis

The working behind the numbers in [On Paper](https://www.youtube.com/@OnPaperSport) videos. Every figure on screen should trace to code you can run yourself, and this repository is where that code lives.

## Episode 1 — Leverkusen's Unbeaten Season, Stopped at 85:00

▶ [Watch on YouTube](https://www.youtube.com/watch?v=b9s1rmmIENw)

Bayer Leverkusen went through the 2023/24 Bundesliga unbeaten: 34 matches, W28 D6 L0, 90 points. Stop every match at the 85th minute instead, and they finish W25 D6 L3 on 81 points. The full analysis, including expected points, goal timings, game state and the rolling shot-quality trend, is in [`RESULTS-LEVERKUSEN.md`](RESULTS-LEVERKUSEN.md).

## Reproduce it

Pure standard-library Python 3 (tested on 3.9). No dependencies, no API key.

```bash
python3 analysis/download_data.py   # fetches the 34 match event files (~119 MB) into ./data
python3 analysis/run_analysis.py    # prints the full report and writes two CSVs locally
```

The run checks itself before reporting anything. It must reproduce the season exactly — **W28 D6 L0, 89 goals for, 24 against, 90 points** — and prints `PASS`, or it stops.

| File | What it does |
|---|---|
| `analysis/download_data.py` | Downloads and caches the StatsBomb files for one competition-season. Re-running skips what is already cached. |
| `analysis/statsbomb_lib.py` | Loading, per-match extraction, the expected-points match model, the game-state timeline. |
| `analysis/run_analysis.py` | Verification against the season totals, then questions 1–4, then the CSVs. |
| `RESULTS-LEVERKUSEN.md` | The written results, with every method choice stated. |

**Not included, on purpose:** the event data and the two CSVs the analysis writes (`leverkusen-matches.csv`, `goals_detail.csv`). StatsBomb's licence does not allow their data, or data derived from it, to be redistributed, so you generate both locally from StatsBomb's own repository. On 2026-10-12 a fresh run from an empty folder reproduced both CSVs byte for byte.

## Method, briefly

- **Expected points.** Each shot is an independent Bernoulli trial with p = StatsBomb xG. A team's goals are the Poisson-binomial sum, and the two teams are convolved exactly for win/draw/loss — no simulation, so no random seed.
- **Own goals** count as goals but are not shots, so they carry no xG.
- **The 85:00 freeze** uses StatsBomb's match clock, where second-half stoppage time continues as 90, 91, 92…
- **Limits.** This release contains only Leverkusen matches, so there is no league baseline. Nothing here claims a figure is high or low *for a Bundesliga side*, and the skill-versus-luck split of the expected-points gap cannot be computed from it.

## Data

<img src="img/statsbomb-logo.png" alt="StatsBomb" height="40">

Data: **StatsBomb Open Data** — [github.com/hudl/open-data](https://github.com/hudl/open-data), Bundesliga 2023/24 (competition 9, season 281). Used under the StatsBomb Open Data licence, which asks that published analysis credit StatsBomb with their logo. The logo above is StatsBomb's own lockup, taken from that repository.
