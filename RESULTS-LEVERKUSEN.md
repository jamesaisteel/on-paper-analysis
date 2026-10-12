# Results — Bayer Leverkusen, 2023/24 Bundesliga (event-data analysis)

**For:** the On Paper *Plotline* episode "Leverkusen's Unbeaten Season, Stopped at 85:00". Answers four research questions (Q1–Q4 below) from StatsBomb event data.
**Data:** StatsBomb Open Data, competition 9 / season 281 — the Leverkusen-only 2023/24 release, 34 matches, weeks 1–34, no gaps.
**Computed:** 2026-08-06. Every number below comes from the event files. Nothing is recalled.

> **Scope reminder.** This dataset contains only Leverkusen matches. There is **no league baseline** in it. Nowhere below is any figure called "high" or "low" *for a Bundesliga side* — such a claim needs a second source and is flagged where it would be tempting.

## How to reproduce

Pure standard-library Python, no dependencies. The event cache (~119 MB) is gitignored.

```bash
python3 analysis/download_data.py     # caches match list + 34 event files under ./data
python3 analysis/run_analysis.py      # prints the full report, writes leverkusen-matches.csv + goals_detail.csv
```

- `analysis/statsbomb_lib.py` — loading, per-match extraction, the Poisson-binomial/convolution match model, the game-state timeline.
- `analysis/run_analysis.py` — verification + Q1–Q4 + CSV.
- `leverkusen-matches.csv` — one row per match with every per-match figure used here (so charts can be built without re-running). **Generated locally and not included in this repository:** it is derived from StatsBomb data, which their licence does not allow to be redistributed.

To run a second season: point `download_data.py` at another competition/season and re-run. `find_featured_team()` auto-detects the one club present in every match, so the code is not hard-wired to Leverkusen.

---

## Verification — season totals reproduce exactly

| Metric | From event data | Target | |
|---|---|---|---|
| Matches parsed | 34 | 34 | ✅ |
| Record | **W28 D6 L0** | W28 D6 L0 | ✅ |
| Goals for–against | **89–24** | 89–24 | ✅ |
| Points | **90** | 90 | ✅ |

The parse also matches the official scoreline in **all 34 matches individually** (zero discrepancies against the `home_score`/`away_score` fields), and week-order equals date-order (no fixture was played out of sequence, so "across the 34 weeks" in Q4 is unambiguous).

**Own-goal handling.** StatsBomb records each own goal as a pair — `Own Goal For` (credited to the beneficiary) and `Own Goal Against` (its mirror). Counting `Own Goal For` per team once avoids double-counting. All three own goals in this release fell *for* Leverkusen; none were conceded.

- Goals **for** = 86 shot-goals + 3 own goals = **89**
- Goals **against** = 24 shot-goals + 0 own goals = **24**

The dataset reproduces the headline record. Proceeding.

---

## Q1 — Expected points vs actual points

**Method.** For each match, each team's goal total is modelled as a **Poisson-binomial** over its list of shot `statsbomb_xg` values (each shot an independent Bernoulli with p = xG). The two teams' goal distributions are treated as independent and **convolved exactly** to give win/draw/loss probabilities — no Monte Carlo. xPts = 3·P(win) + 1·P(draw). Own goals are excluded from the xG model (they are not shots) but remain in the actual-goal totals.

### Headline

| | Actual | xPts (all shots) | xPts (penalties excluded) |
|---|---|---|---|
| **Season points** | **90** | **74.88** | **72.16** |
| vs actual | — | **+15.12** | **+17.84** |

Season shot xG: **72.70 for, 27.81 against** (difference **+44.89**).

Leverkusen took **15.1 more points than their shot quality alone predicts** — and the gap *widens* to +17.8 when penalties are removed, so the overperformance is **not** an artefact of penalty xG. (They took 8 penalties, scored all 8, worth 6.27 xG; they conceded zero penalties all season. Removing these high-xG shots lowers the *model's* expectation while the real points stay at 90.)

### Where the +15 comes from — it is entirely in the wins

| Split | Actual pts | xPts | Difference |
|---|---|---|---|
| 28 wins | 84 | 64.09 | **+19.91** |
| 6 draws | 6 | 10.78 | **−4.78** |

The overperformance lives entirely in **converting even/marginal games into wins**. In the six draws they actually *under*performed xPts by ~5 — those were games they dominated on chances (Dortmund twice, Gladbach) but only drew.

**The mechanism** (finishing and goalkeeping above the xG baseline):

- Attack: **86 shot-goals from 72.70 xG → +13.3** above expected, plus 3 own goals = 89.
- Defence: **24 conceded from 27.81 xGA → 3.8 fewer** than the chances "deserved".

### The extremes

**Most fortunate** (took far more than xPts) — all narrow wins in coin-flip games:

| Wk | Opponent | V | Res | Pts | xPts | Δ |
|---|---|---|---|---|---|---|
| 10 | Hoffenheim | A | W | 3 | 1.15 | +1.85 |
| 1 | RB Leipzig | H | W | 3 | 1.21 | +1.79 |
| 23 | FSV Mainz 05 | H | W | 3 | 1.32 | +1.68 |
| 21 | Bayern Munich | H | W | 3 | 1.71 | +1.29 |
| 6 | FSV Mainz 05 | A | W | 3 | 1.73 | +1.27 |

**Most "unlucky"** (took far less than xPts) — every one is a draw against a top-half side:

| Wk | Opponent | V | Res | Pts | xPts | Δ |
|---|---|---|---|---|---|---|
| 19 | Gladbach | H | D | 1 | 2.81 | −1.81 |
| 13 | Dortmund | H | D | 1 | 2.40 | −1.40 |
| 30 | Dortmund | A | D | 1 | 2.12 | −1.12 |
| 4 | Bayern Munich | A | D | 1 | 1.40 | −0.40 |
| 31 | VfB Stuttgart | H | D | 1 | 1.25 | −0.25 |

### Per-match table

xPts = all shots; xPts⁻ᵖ = penalties excluded. xGf/xGa = shot xG for/against.

| Wk | Opponent | V | Score | Res | Pts | xPts | xPts⁻ᵖ | xGf | xGa |
|---:|---|:--:|:--:|:--:|--:|--:|--:|--:|--:|
| 1 | RB Leipzig | H | 3–2 | W | 3 | 1.21 | 1.21 | 1.5 | 1.7 |
| 2 | Gladbach | A | 3–0 | W | 3 | 2.53 | 2.53 | 2.7 | 0.8 |
| 3 | Darmstadt 98 | H | 5–1 | W | 3 | 2.82 | 2.82 | 3.3 | 0.6 |
| 4 | Bayern Munich | A | 2–2 | D | 1 | 1.40 | 0.87 | 2.2 | 2.2 |
| 5 | Heidenheim | H | 4–1 | W | 3 | 2.95 | 2.85 | 3.7 | 0.3 |
| 6 | FSV Mainz 05 | A | 3–0 | W | 3 | 1.73 | 1.73 | 0.8 | 0.4 |
| 7 | FC Köln | H | 3–0 | W | 3 | 2.44 | 2.44 | 2.9 | 1.2 |
| 8 | Wolfsburg | A | 2–1 | W | 3 | 1.94 | 1.94 | 2.0 | 1.2 |
| 9 | Freiburg | H | 2–1 | W | 3 | 1.88 | 1.88 | 1.4 | 0.8 |
| 10 | Hoffenheim | A | 3–2 | W | 3 | 1.15 | 1.15 | 1.3 | 1.5 |
| 11 | Union Berlin | H | 4–0 | W | 3 | 2.73 | 2.73 | 1.9 | 0.0 |
| 12 | Werder Bremen | A | 3–0 | W | 3 | 2.18 | 2.18 | 1.1 | 0.2 |
| 13 | Dortmund | H | 1–1 | D | 1 | 2.40 | 2.40 | 2.1 | 0.8 |
| 14 | VfB Stuttgart | A | 1–1 | D | 1 | 0.80 | 0.80 | 1.5 | 2.4 |
| 15 | Frankfurt | H | 3–0 | W | 3 | 2.92 | 2.92 | 2.8 | 0.2 |
| 16 | Bochum | H | 4–0 | W | 3 | 2.92 | 2.78 | 3.4 | 0.3 |
| 17 | Augsburg | A | 1–0 | W | 3 | 2.35 | 2.35 | 1.6 | 0.3 |
| 18 | RB Leipzig | A | 3–2 | W | 3 | 1.99 | 1.99 | 1.9 | 1.1 |
| 19 | Gladbach | H | 0–0 | D | 1 | 2.81 | 2.81 | 2.6 | 0.2 |
| 20 | Darmstadt 98 | A | 2–0 | W | 3 | 2.23 | 2.23 | 2.0 | 0.8 |
| 21 | Bayern Munich | H | 3–0 | W | 3 | 1.71 | 1.71 | 1.0 | 0.6 |
| 22 | Heidenheim | A | 2–1 | W | 3 | 2.43 | 2.43 | 1.8 | 0.5 |
| 23 | FSV Mainz 05 | H | 2–1 | W | 3 | 1.32 | 1.32 | 1.1 | 1.1 |
| 24 | FC Köln | A | 2–0 | W | 3 | 1.90 | 1.90 | 1.3 | 0.7 |
| 25 | Wolfsburg | H | 2–0 | W | 3 | 2.63 | 2.63 | 1.8 | 0.2 |
| 26 | Freiburg | A | 3–2 | W | 3 | 2.46 | 2.46 | 2.6 | 0.9 |
| 27 | Hoffenheim | H | 2–1 | W | 3 | 2.64 | 2.64 | 2.8 | 0.6 |
| 28 | Union Berlin | A | 1–0 | W | 3 | 2.68 | 2.29 | 2.6 | 0.5 |
| 29 | Werder Bremen | H | 5–0 | W | 3 | 2.75 | 2.43 | 3.0 | 0.7 |
| 30 | Dortmund | A | 1–1 | D | 1 | 2.12 | 2.12 | 1.4 | 0.6 |
| 31 | VfB Stuttgart | H | 2–2 | D | 1 | 1.25 | 1.25 | 1.7 | 1.8 |
| 32 | Frankfurt | A | 5–1 | W | 3 | 2.23 | 1.04 | 2.6 | 1.4 |
| 33 | Bochum | A | 5–0 | W | 3 | 2.98 | 2.94 | 4.3 | 0.3 |
| 34 | Augsburg | H | 2–1 | W | 3 | 2.38 | 2.38 | 2.2 | 0.8 |
| | **Season** | | | | **90** | **74.88** | **72.16** | **72.7** | **27.8** |

**Reading.** By expected points, Leverkusen were a **~75-point team who scored 90**. On its own, that +15 is the *variance* reading's strongest single piece of evidence: they beat their chances everywhere the games were tight. But note the caveat carried into the verdict — xPts assumes league-average finishing, and this side had elite finishers and a strong keeper, so part of the +15 is repeatable skill rather than luck. **This dataset cannot separate the two** (no player-level or multi-season baseline), so the +15 should be read as "outperformed the chance-quality baseline," not "got lucky by 15 points."

---

## Q2 — Goal timings and the late-goal reputation

**Choices stated up front.** StatsBomb's `minute` is a continuous match clock: second-half stoppage appears as 90, 91, 92… and is **not** extra time (there is none — every match has only periods 1 and 2). First-half stoppage (period 1, minute ≥ 45) is bucketed separately from the early second half so the two never blur. "Late" is shown at three thresholds because the word is ambiguous; the primary is **the 85:00 mark onward** (period-2 minute ≥ 85).

### Every goal, bucketed

| Bucket | For | Against |
|---|--:|--:|
| 01–15 | 9 | 5 |
| 16–30 | 11 | 1 |
| 31–45 | 11 | 5 |
| 45+ (1st-half stoppage) | 6 | 0 |
| 46–60 | 14 | 6 |
| 61–75 | 16 | 3 |
| 76–90 | 14 | 4 |
| 90+ (2nd-half stoppage) | **8** | **0** |
| **Total** | **89** | **24** |

Leverkusen scored in every phase; the single busiest window for goals *for* is 61–75. The reputation shows up at the very end: **8 goals in second-half stoppage time, and none conceded there.**

### Late-goal counts (period-2 clock)

| Threshold | For | Against |
|---|--:|--:|
| ≥ 85' | 13 | 2 |
| ≥ 86' | 11 | 0 |
| ≥ 90' | 8 | 0 |

### The decisive finding — freeze the scoreline at the 85:00 mark

If every match had ended at 85:00, Leverkusen's record would read **W25 D6 L3 — 81 points.** Champions, comfortably, but **not unbeaten.** The goals from 85:00 onward were worth a net **+9 points** (81 → 90) and turned three would-be defeats into unbeaten results.

Freezing instead at **90:00** gives the same **81 points (W25 D6 L3)** — six matches had their result altered by a goal in the 90th minute or later. **The invincibility, specifically, was manufactured in the final five minutes.**

### Every goal from 85:00 onward, and what it did

| Wk | Opponent | V | Min | Side | State change | Effect | Final |
|---|---|:--:|:--:|:--:|---|---|:--:|
| 4 | Bayern Munich | A | 85:21 | against | level→trail | **draw→loss** | D |
| 4 | Bayern Munich | A | 93:46 | FOR (pen) | trail→level | **loss→draw** | D |
| 17 | Augsburg | A | 93:49 | FOR | level→lead | **draw→win** | W |
| 18 | RB Leipzig | A | 90:40 | FOR | level→lead | **draw→win** | W |
| 21 | Bayern Munich | H | 94:38 | FOR | lead→lead | padded | W |
| 22 | Heidenheim | A | 85:59 | against | lead→lead | padded | W |
| 25 | Wolfsburg | H | 85:45 | FOR | lead→lead | padded | W |
| 27 | Hoffenheim | H | 87:24 | FOR | trail→level | **loss→draw** | W |
| 27 | Hoffenheim | H | 90:12 | FOR | level→lead | **draw→win** | W |
| 29 | Werder Bremen | H | 89:25 | FOR | lead→lead | padded | W |
| 30 | Dortmund | A | 96:52 | FOR | trail→level | **loss→draw** | D |
| 31 | VfB Stuttgart | H | 95:59 | FOR | trail→level | **loss→draw** | D |
| 32 | Frankfurt | A | 88:24 | FOR | lead→lead | padded | W |
| 33 | Bochum | A | 85:50 | FOR | lead→lead | padded | W |
| 33 | Bochum | A | 92:07 | FOR | lead→lead | padded | W |

Of the 15 goals from 85:00 on: **7 for Leverkusen changed the running result** (2 draw→win, 3 loss→draw, plus the loss→draw pair at Bayern), **1 against** (Bayern's 85:21). The other 7 padded existing leads.

### Four matches where the unbeaten record was actively being lost after the 85th minute — and saved

| Wk | Opponent | V | State late on | Saved to |
|---|---|:--:|---|:--:|
| 4 | Bayern Munich | A | trailed 1–2 from 85:21 | 2–2 D (94' penalty) |
| 27 | Hoffenheim | H | trailed 0–1 until 87:24 | 2–1 W (88' + 91') |
| 30 | Dortmund | A | trailed 0–1 from 80:25 | 1–1 D (97') |
| 31 | VfB Stuttgart | H | trailed 1–2 (from 0–2) | 2–2 D (96') |

(Two further late winners — Augsburg 94' in a 0–0, Leipzig 91' from 2–2 — turned *draws* into wins but were not rescues of the record.)

**Reading.** The late-goal reputation is real and, for the invincible record specifically, decisive. Strip the goals scored from 85:00 onward and Leverkusen have three defeats and 81 points. The *title* survives that surgery untouched (won by 17); the *unbeaten record* does not survive it at all.

---

## Q3 — Game state: minutes leading, level, trailing

Time is measured in **actual elapsed match minutes** (period 2 stitched onto the end of period 1 using StatsBomb's `Half End` markers, which sit within ~2 s of each period's last on-ball action). The running scoreline — including own goals — partitions each match; intervals are attributed to Leverkusen's state.

| State | Minutes | Share |
|---|--:|--:|
| **Leading** | 1,705.3 | **51.5%** |
| Level | 1,313.8 | 39.7% |
| **Trailing** | 290.9 | **8.8%** |
| Total | 3,310.1 | (avg 97.4 min/match) |

Supporting facts:

- **Leverkusen scored first in 26 of 34 matches.** One match was goalless (Gladbach 0–0). They conceded first in 7.
- **They ever trailed in only 7 of 34 matches** — and those 7 are exactly the 7 where they conceded first.
- **Once ahead, they were never behind.** In none of the 26 matches where they scored first did they subsequently trail. Every minute they spent trailing came from an early concession, not a surrendered lead.
- Conceding first cost them nothing in the loss column: those 7 matches went **2 W, 5 D, 0 L**.

The 291 trailing minutes are concentrated in a handful of games (Dortmund H 78.5, Hoffenheim H 57.8, Leipzig A 51.1, Stuttgart H 49.9, Bayern A 25.8, Dortmund A 16.4, Stuttgart A 11.4).

**Reading.** This is the *method* reading's strongest evidence. A team that led for more than half of all football played, trailed for under 9%, and never once coughed up a lead was steering games, not chasing them. The high "level" share is mostly early 0–0 phases before they scored (they scored first three times out of four) plus the six draws.

---

## Q4 — Shot-quality trend across the season (rolling five-match)

Trailing five-match windows. xGf = xG for per match, xGa = xG against per match, xG/sh = xG per shot (for). Full per-week series is in the CSV (`roll5_*` columns).

**First 17 weeks vs last 17 weeks:**

| | Weeks 1–17 | Weeks 18–34 |
|---|--:|--:|
| xG for / match | 2.13 | 2.14 |
| xG against / match | 0.88 | 0.76 |
| xG per shot (for) | 0.123 | 0.111 |

Across the 34-week rolling series, xG for oscillates between roughly 1.4 and 2.6 per match with no directional drift; xG against sits low throughout (mostly 0.4–1.3) and if anything edges *down* in the second half; xG per shot wanders in a narrow band with no trend.

**Reading.** Underlying performance **held roughly flat** — it neither visibly improved nor decayed as the unbeaten streak lengthened into a pressure of its own. The attack generated the same ~2.1 xG per game at the end as at the start; the defence stayed miserly from first week to last. There is no signal here of a team riding an improving wave, and none of one cracking under the weight of the record. (Whether flat generation like this is itself remarkable would require a league baseline this dataset does not contain.)

---

## Which thesis does the evidence support?

The research behind the episode posed two readings of the one-goal wins: **method** (controlled game states — led, managed, closed) versus **variance** (coin flips that landed — a season repeatedly rescued). **The event data does not pick one cleanly. It splits them by which achievement you are explaining** — and that split is exactly the separation the research suspected but could not prove.

**The championship was earned — the method reading.** By the underlying numbers Leverkusen were the better side in essentially every match: 72.7 xG for against 27.8, a +44.9 chance-quality difference. They led for 51.5% of all minutes and trailed for 8.8%; they scored first three times in four; and *once ahead they were never behind*. A 17-point title built on that is not luck.

**The unbeaten record was, in meaningful part, survived — the variance/rescue reading.** It rests on two things the method reading cannot absorb. First, a **+15-point overperformance of expected points** (90 vs 74.9; +17.8 with penalties removed), concentrated entirely in turning even games into wins. Second, and more concretely, **the record was manufactured after the 85th minute**: freeze every match at 85:00 and Leverkusen have three defeats and 81 points, and in four matches — Bayern (a), Hoffenheim (h), Dortmund (a), Stuttgart (h) — they were *actively losing* in the final minutes and escaped.

So: **neither thesis is cleanly correct, and the honest answer is that they describe two different trophies.** The 90-point, 17-clear title was steered. The *invincibility* was, on four separate afternoons, rescued — and without the goals of the last five minutes it would read W25 D6 L3. The video's spine is not "earned *or* survived" but **"the title was earned; the unbeaten record was earned *and* survived, and the difference between those two sentences is about nine points scored after the 85th minute."**

One caution before that becomes a script line: the +15 xPts gap is the load-bearing number for the "survived" half, and xPts assumes league-average finishing. A side with elite finishers and a strong goalkeeper will beat it as a matter of skill, not fortune, and **this dataset cannot say how much of the +15 is repeatable** — that needs a player-level or multi-season baseline it does not contain. The *timing* facts (81 points at 85:00; four late escapes) are not subject to that caveat: they are counts, not models.

---

## Method, choices, and what cannot be computed

- **xPts model.** Each shot is an independent Bernoulli(xG); a team's goals are the Poisson-binomial sum; the two teams are convolved exactly for W/D/L. Two independence assumptions are baked in — shots within a team, and the two teams' totals — both standard for xG-based match models and both approximations (rebounds and game state create real dependence). No simulation was used, so there is no seed to report.
- **Own goals** are excluded from the xG model (not shots) and included in actual goals (via `Own Goal For`, counted once). All three fell for Leverkusen.
- **Penalties** are shown both ways throughout Q1. Included: xPts 74.88. Excluded: 72.16. The overperformance survives — indeed grows — without them.
- **"Late" goals** are reported at ≥85', ≥86' and ≥90'; the 85:00 and 90:00 scoreline freezes both yield 81 points, so the headline is robust to the threshold.
- **Added time.** No match has extra time (periods 1–2 only). Second-half stoppage (minute 90+) is treated as normal second-half time. Game-state minutes use actual elapsed time from `Half End` markers, so match lengths vary (avg 97.4 min; one outlier, Union away, ran to ~105 real minutes with 10 injury stoppages).
- **What this dataset cannot answer:** anything needing a league or multi-season baseline — whether the one-goal-win rate, the flat xG trend, or the finishing overperformance is unusual *for a Bundesliga side*; and the skill-vs-luck decomposition of the +15 xPts. The 2022/23 finish (the "sixth to unbeaten" framing) and the final league table are also outside these files. Flag all of these for a second source before scripting.
