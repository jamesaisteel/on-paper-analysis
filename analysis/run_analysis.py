#!/usr/bin/env python3
"""
Leverkusen 2023/24 event-data analysis — driver.

Answers, entirely from the cached StatsBomb event files:
  Verification  season totals (must reproduce W28 D6 L0, 89-24, 90 pts)
  Q1            expected points (xPts) vs actual, exact Poisson-binomial
  Q2            goal timings and late-goal result impact
  Q3            game state — minutes leading / level / trailing
  Q4            rolling five-match xG trends

Writes ../leverkusen-matches.csv (one row per match) and prints a full report
to stdout. Pure standard library; re-run with `python3 analysis/run_analysis.py`.
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import statsbomb_lib as L

REPO_ROOT = L.REPO_ROOT
LATE_MIN = 85          # primary "late goal" threshold (period-2 clock >= 85:00)


def build_records():
    matches = L.load_match_list()
    fid, fname = L.find_featured_team(matches)
    recs = []
    for m in matches:
        ev = L.load_events(m["match_id"])
        recs.append(L.extract_match(m, ev, fid))
    recs.sort(key=lambda r: r["match_week"])
    return recs, fid, fname


# --------------------------------------------------------------------------- #
def section(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def verification(recs):
    section("VERIFICATION — season totals from event data")
    W = sum(r["result"] == "W" for r in recs)
    D = sum(r["result"] == "D" for r in recs)
    Ls = sum(r["result"] == "L" for r in recs)
    GF = sum(r["goals_for"] for r in recs)
    GA = sum(r["goals_against"] for r in recs)
    PTS = sum(r["points"] for r in recs)
    print(f"  Matches parsed : {len(recs)}")
    print(f"  Record         : W{W} D{D} L{Ls}   (target W28 D6 L0)")
    print(f"  Goals for/ag   : {GF}-{GA}          (target 89-24)")
    print(f"  Points         : {PTS}             (target 90)")
    ok = (W, D, Ls, GF, GA, PTS) == (28, 6, 0, 89, 24, 90)
    print(f"  ==> {'PASS — reproduces the headline figures exactly' if ok else 'FAIL'}")
    # own-goal accounting
    og_for = sum(1 for r in recs for g in r["goals"] if g["kind"] == "own_goal" and g["for_featured"])
    og_ag = sum(1 for r in recs for g in r["goals"] if g["kind"] == "own_goal" and not g["for_featured"])
    shot_goals_for = sum(1 for r in recs for g in r["goals"] if g["kind"] != "own_goal" and g["for_featured"])
    shot_goals_ag = sum(1 for r in recs for g in r["goals"] if g["kind"] != "own_goal" and not g["for_featured"])
    print(f"  Goals for  = {shot_goals_for} shots + {og_for} own goals = {shot_goals_for+og_for}")
    print(f"  Goals ag.  = {shot_goals_ag} shots + {og_ag} own goals = {shot_goals_ag+og_ag}")
    return ok


# --------------------------------------------------------------------------- #
def q1_expected_points(recs):
    section("Q1 — Expected points (exact Poisson-binomial) vs actual")
    cum_actual = cum_xpts = cum_xpts_nopen = 0.0
    print(f"  {'wk':>2} {'opp':<20} {'v':<1} {'res':<3} {'pts':>3} "
          f"{'xPts':>5} {'xPtsNP':>6}  {'P(W)':>5} {'P(D)':>5} {'P(L)':>5}  "
          f"{'xGf':>4} {'xGa':>4}")
    for r in recs:
        xgf = [s["xg"] for s in r["shots_for"]]
        xga = [s["xg"] for s in r["shots_against"]]
        xgf_np = [s["xg"] for s in r["shots_for"] if not s["is_penalty"]]
        xga_np = [s["xg"] for s in r["shots_against"] if not s["is_penalty"]]

        xpts, (pw, pd, pl) = L.expected_points(xgf, xga)
        xpts_np, _ = L.expected_points(xgf_np, xga_np)

        r["xg_for"] = sum(xgf)
        r["xg_against"] = sum(xga)
        r["xpts"] = xpts
        r["xpts_nopen"] = xpts_np
        r["p_win"], r["p_draw"], r["p_loss"] = pw, pd, pl

        cum_actual += r["points"]
        cum_xpts += xpts
        cum_xpts_nopen += xpts_np
        print(f"  {r['match_week']:>2} {r['opponent'][:20]:<20} {r['venue']:<1} "
              f"{r['result']:<3} {r['points']:>3} {xpts:>5.2f} {xpts_np:>6.2f}  "
              f"{pw:>5.2f} {pd:>5.2f} {pl:>5.2f}  {sum(xgf):>4.1f} {sum(xga):>4.1f}")

    print("  " + "-" * 76)
    print(f"  SEASON  actual points   : {cum_actual:.0f}")
    print(f"          xPts (all shots): {cum_xpts:.2f}   (diff {cum_actual-cum_xpts:+.2f})")
    print(f"          xPts (no pens)  : {cum_xpts_nopen:.2f}   (diff {cum_actual-cum_xpts_nopen:+.2f})")
    print(f"          total xG for    : {sum(r['xg_for'] for r in recs):.2f}")
    print(f"          total xG against: {sum(r['xg_against'] for r in recs):.2f}")

    # Biggest over/under-performances vs xPts (all shots)
    ranked = sorted(recs, key=lambda r: r["points"] - r["xpts"])
    print("\n  Most 'unlucky' (actual << xPts):")
    for r in ranked[:5]:
        print(f"    wk{r['match_week']:>2} {r['opponent'][:18]:<18} {r['venue']} "
              f"{r['result']} got {r['points']} vs xPts {r['xpts']:.2f} "
              f"({r['points']-r['xpts']:+.2f})")
    print("  Most 'fortunate' (actual >> xPts):")
    for r in ranked[-5:][::-1]:
        print(f"    wk{r['match_week']:>2} {r['opponent'][:18]:<18} {r['venue']} "
              f"{r['result']} got {r['points']} vs xPts {r['xpts']:.2f} "
              f"({r['points']-r['xpts']:+.2f})")
    return cum_actual, cum_xpts, cum_xpts_nopen


# --------------------------------------------------------------------------- #
def _bucket(period, minute):
    if period == 1:
        if minute < 15:
            return "01-15"
        if minute < 30:
            return "16-30"
        if minute < 45:
            return "31-45"
        return "45+ (1H stpg)"
    else:
        if minute < 60:
            return "46-60"
        if minute < 75:
            return "61-75"
        if minute < 90:
            return "76-90"
        return "90+ (2H stpg)"


BUCKET_ORDER = ["01-15", "16-30", "31-45", "45+ (1H stpg)",
                "46-60", "61-75", "76-90", "90+ (2H stpg)"]


def q2_goal_timings(recs):
    section("Q2 — Goal timings and the late-goal reputation")
    for_b = {b: 0 for b in BUCKET_ORDER}
    ag_b = {b: 0 for b in BUCKET_ORDER}
    for r in recs:
        for g in r["goals"]:
            b = _bucket(g["period"], g["minute"])
            (for_b if g["for_featured"] else ag_b)[b] += 1
    print(f"  {'bucket':<15} {'for':>4} {'against':>8}")
    for b in BUCKET_ORDER:
        print(f"  {b:<15} {for_b[b]:>4} {ag_b[b]:>8}")
    print(f"  {'TOTAL':<15} {sum(for_b.values()):>4} {sum(ag_b.values()):>8}")

    # threshold counts
    print("\n  Late-goal counts (period-2 clock), for / against:")
    for thr in (85, 86, 90):
        gf = sum(1 for r in recs for g in r["goals"]
                 if g["for_featured"] and g["period"] == 2 and g["minute"] >= thr)
        ga = sum(1 for r in recs for g in r["goals"]
                 if not g["for_featured"] and g["period"] == 2 and g["minute"] >= thr)
        print(f"    >= {thr}' : {gf} for, {ga} against")

    # Enumerate each late goal (>= LATE_MIN) with result-change classification
    print(f"\n  Every goal from the {LATE_MIN}:00 mark onward "
          f"(period 2, minute >= {LATE_MIN}):")
    print(f"  {'wk':>2} {'opp':<18} {'v':<1} {'min':>5} {'side':<7} "
          f"{'before->after':<16} {'effect':<22} {'final':<5}")
    changing_for = changing_against = 0
    for r in recs:
        for g in r["goals"]:
            if g["period"] == 2 and g["minute"] >= LATE_MIN:
                before, after = L.running_state_before_after(r, g)
                changed = before != after
                side = "FOR" if g["for_featured"] else "against"
                mm = f"{g['minute']}:{g['second']:02d}"
                # human label
                names = {"lead": "lead", "level": "level", "trail": "trail"}
                if changed:
                    effect = f"{_wdl(before)}->{_wdl(after)} (CHANGED)"
                    if g["for_featured"]:
                        changing_for += 1
                    else:
                        changing_against += 1
                else:
                    effect = "padded (no change)"
                print(f"  {r['match_week']:>2} {r['opponent'][:18]:<18} {r['venue']:<1} "
                      f"{mm:>5} {side:<7} {names[before]+'->'+names[after]:<16} "
                      f"{effect:<22} {r['result']:<5}")
    print(f"\n  Late (>= {LATE_MIN}') goals that CHANGED the running result: "
          f"{changing_for} for, {changing_against} against")

    # Season-level "freeze at 85:00" points impact
    section("Q2b — Points swing from the late phase (freeze scoreline at 85:00)")
    pts_at_85 = 0
    pts_actual = 0
    swing_matches = []
    for r in recs:
        sf = sum(1 for g in r["goals"] if not (g["period"] == 2 and g["minute"] >= LATE_MIN) and g["for_featured"])
        sa = sum(1 for g in r["goals"] if not (g["period"] == 2 and g["minute"] >= LATE_MIN) and not g["for_featured"])
        res85 = "W" if sf > sa else ("D" if sf == sa else "L")
        p85 = {"W": 3, "D": 1, "L": 0}[res85]
        pts_at_85 += p85
        pts_actual += r["points"]
        if p85 != r["points"]:
            swing_matches.append((r, sf, sa, res85, p85))
    print(f"  Points if every match ended at 85:00 : {pts_at_85}")
    print(f"  Points actually taken                : {pts_actual}")
    print(f"  Net swing from goals >= {LATE_MIN}'          : {pts_actual - pts_at_85:+d}")
    print("  Matches where the late phase changed the points:")
    for r, sf, sa, res85, p85 in swing_matches:
        print(f"    wk{r['match_week']:>2} {r['opponent'][:18]:<18} {r['venue']}: "
              f"at 85' {sf}-{sa} ({res85},{p85}pt) -> final "
              f"{r['goals_for']}-{r['goals_against']} ({r['result']},{r['points']}pt)")
    return changing_for, changing_against, pts_at_85, pts_actual


def _wdl(state):
    return {"lead": "win", "level": "draw", "trail": "loss"}[state]


# --------------------------------------------------------------------------- #
def q3_game_state(recs):
    section("Q3 — Game state: minutes leading / level / trailing (Leverkusen POV)")
    tot_lead = tot_level = tot_trail = 0.0
    print(f"  {'wk':>2} {'opp':<20} {'v':<1} {'res':<3} "
          f"{'lead':>6} {'level':>6} {'trail':>6} {'match':>6}")
    for r in recs:
        gs = L.game_state_minutes(r)
        r["lead_sec"], r["level_sec"], r["trail_sec"] = gs["lead_sec"], gs["level_sec"], gs["trail_sec"]
        tot_lead += gs["lead_sec"]
        tot_level += gs["level_sec"]
        tot_trail += gs["trail_sec"]
        print(f"  {r['match_week']:>2} {r['opponent'][:20]:<20} {r['venue']:<1} "
              f"{r['result']:<3} {gs['lead_sec']/60:>6.1f} {gs['level_sec']/60:>6.1f} "
              f"{gs['trail_sec']/60:>6.1f} {gs['total_sec']/60:>6.1f}")
    total = tot_lead + tot_level + tot_trail
    print("  " + "-" * 70)
    print(f"  SEASON leading : {tot_lead/60:8.1f} min  ({100*tot_lead/total:5.1f}%)")
    print(f"         level   : {tot_level/60:8.1f} min  ({100*tot_level/total:5.1f}%)")
    print(f"         trailing: {tot_trail/60:8.1f} min  ({100*tot_trail/total:5.1f}%)")
    print(f"         total   : {total/60:8.1f} min")
    # how many matches did they ever trail?
    trailed = [r for r in recs if r["trail_sec"] > 0]
    print(f"  Matches in which Leverkusen ever trailed: {len(trailed)} of {len(recs)}")
    for r in trailed:
        print(f"    wk{r['match_week']:>2} {r['opponent'][:18]:<18} {r['venue']} "
              f"{r['result']}  trailed {r['trail_sec']/60:.1f} min")
    return tot_lead, tot_level, tot_trail


# --------------------------------------------------------------------------- #
def q4_trend(recs):
    section("Q4 — Rolling five-match xG trend (trailing window)")
    win = 5
    print("  Per-match then trailing-5 rolling (xGf=xG for, xGa=xG against, "
          "xG/sh=xG per shot for):")
    print(f"  {'wk':>2} {'opp':<18} {'xGf':>5} {'xGa':>5} {'sh':>3} {'xG/sh':>6} | "
          f"{'r.xGf':>6} {'r.xGa':>6} {'r.xG/sh':>7}")
    rows = []
    for i, r in enumerate(recs):
        n_for = len(r["shots_for"])
        xgps = r["xg_for"] / n_for if n_for else 0.0
        r["shots_for_n"] = n_for
        r["shots_against_n"] = len(r["shots_against"])
        r["xg_per_shot_for"] = xgps
        window = recs[max(0, i - win + 1): i + 1]
        r_xgf = sum(w["xg_for"] for w in window) / len(window)
        r_xga = sum(w["xg_against"] for w in window) / len(window)
        w_shots = sum(len(w["shots_for"]) for w in window)
        r_xgps = sum(w["xg_for"] for w in window) / w_shots if w_shots else 0.0
        full = len(window) == win
        r["roll_xg_for"] = r_xgf
        r["roll_xg_against"] = r_xga
        r["roll_xg_per_shot"] = r_xgps
        r["roll_full"] = full
        tag = "" if full else "  (partial window)"
        print(f"  {r['match_week']:>2} {r['opponent'][:18]:<18} {r['xg_for']:>5.2f} "
              f"{r['xg_against']:>5.2f} {n_for:>3} {xgps:>6.3f} | "
              f"{r_xgf:>6.2f} {r_xga:>6.2f} {r_xgps:>7.3f}{tag}")
        rows.append(r)

    # split-season comparison
    first, second = recs[:17], recs[17:]
    def agg(chunk):
        xgf = sum(r["xg_for"] for r in chunk)
        xga = sum(r["xg_against"] for r in chunk)
        sh = sum(len(r["shots_for"]) for r in chunk)
        return xgf, xga, xgf / len(chunk), xga / len(chunk), xgf / sh
    a1 = agg(first)
    a2 = agg(second)
    print("\n  First 17 vs last 17 weeks:")
    print(f"    xG for / match   : {a1[2]:.2f}  ->  {a2[2]:.2f}")
    print(f"    xG against / match: {a1[3]:.2f}  ->  {a2[3]:.2f}")
    print(f"    xG per shot (for): {a1[4]:.3f}  ->  {a2[4]:.3f}")


# --------------------------------------------------------------------------- #
def write_csv(recs, path):
    cols = [
        "match_week", "match_id", "date", "opponent", "venue",
        "goals_for", "goals_against", "result", "points",
        "shots_for", "shots_against", "xg_for", "xg_against", "xg_per_shot_for",
        "xg_for_nopen", "xg_against_nopen",
        "p_win", "p_draw", "p_loss", "xpts", "xpts_nopen",
        "min_leading", "min_level", "min_trailing", "min_total",
        "goals_for_ge85", "goals_against_ge85",
        "roll5_xg_for", "roll5_xg_against", "roll5_xg_per_shot", "roll5_full",
        "cum_points", "cum_xpts", "cum_xpts_nopen",
    ]
    cum_p = cum_x = cum_xn = 0.0
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in recs:
            cum_p += r["points"]
            cum_x += r["xpts"]
            cum_xn += r["xpts_nopen"]
            gf85 = sum(1 for g in r["goals"] if g["for_featured"] and g["period"] == 2 and g["minute"] >= LATE_MIN)
            ga85 = sum(1 for g in r["goals"] if not g["for_featured"] and g["period"] == 2 and g["minute"] >= LATE_MIN)
            xgf_np = sum(s["xg"] for s in r["shots_for"] if not s["is_penalty"])
            xga_np = sum(s["xg"] for s in r["shots_against"] if not s["is_penalty"])
            w.writerow([
                r["match_week"], r["match_id"], r["date"], r["opponent"], r["venue"],
                r["goals_for"], r["goals_against"], r["result"], r["points"],
                r["shots_for_n"], r["shots_against_n"],
                f"{r['xg_for']:.4f}", f"{r['xg_against']:.4f}", f"{r['xg_per_shot_for']:.4f}",
                f"{xgf_np:.4f}", f"{xga_np:.4f}",
                f"{r['p_win']:.4f}", f"{r['p_draw']:.4f}", f"{r['p_loss']:.4f}",
                f"{r['xpts']:.4f}", f"{r['xpts_nopen']:.4f}",
                f"{r['lead_sec']/60:.2f}", f"{r['level_sec']/60:.2f}",
                f"{r['trail_sec']/60:.2f}", f"{(r['lead_sec']+r['level_sec']+r['trail_sec'])/60:.2f}",
                gf85, ga85,
                f"{r['roll_xg_for']:.4f}", f"{r['roll_xg_against']:.4f}",
                f"{r['roll_xg_per_shot']:.4f}", int(r["roll_full"]),
                f"{cum_p:.0f}", f"{cum_x:.4f}", f"{cum_xn:.4f}",
            ])
    print(f"\nWrote {path}")


def write_goals_csv(recs, path):
    """One row per goal — scored and conceded — across all matches, carrying the
    running scoreline immediately after each goal. Reconciles against the
    per-match goals_for / goals_against and the season anchors (113 goals =
    89 for + 24 against, incl. 3 own goals all for) BEFORE writing; on any
    divergence it names the offending match and refuses to write the file.

    r['goals'] is already sorted (period, minute, second) by extract_match, so
    iterating it in order yields a correct running scoreline and its first
    element is the match's first goal (either side)."""
    cols = [
        "match_week", "match_id", "date", "opponent", "venue",
        "period", "minute", "second",
        "side", "goal_type", "is_penalty",
        "score_for_after", "score_against_after", "is_first_goal",
    ]
    rows = []
    per_match = []          # (record, for_count, against_count) for reconciliation
    total_own = own_for = 0
    for r in recs:
        sf = sa = 0
        for i, g in enumerate(r["goals"]):
            if g["for_featured"]:
                sf += 1
            else:
                sa += 1
            if g["kind"] == "own_goal":
                total_own += 1
                own_for += int(g["for_featured"])
            rows.append({
                "match_week": r["match_week"],
                "match_id": r["match_id"],
                "date": r["date"],
                "opponent": r["opponent"],
                "venue": r["venue"],
                "period": g["period"],
                "minute": g["minute"],
                "second": g["second"],
                "side": "for" if g["for_featured"] else "against",
                # a penalty is still a Shot in StatsBomb; own goals are the only
                # non-shot goal type here, and they carry no xG.
                "goal_type": "own_goal" if g["kind"] == "own_goal" else "shot",
                "is_penalty": "true" if g["kind"] == "penalty" else "false",
                "score_for_after": sf,
                "score_against_after": sa,
                "is_first_goal": "true" if i == 0 else "false",
            })
        mf = sum(1 for g in r["goals"] if g["for_featured"])
        ma = sum(1 for g in r["goals"] if not g["for_featured"])
        per_match.append((r, mf, ma))

    # ---- verify before writing; refuse to write on any divergence ---------- #
    problems = []
    for r, mf, ma in per_match:
        if (mf, ma) != (r["goals_for"], r["goals_against"]):
            problems.append(
                f"match_week {r['match_week']} ({r['opponent']}, {r['venue']}): "
                f"goals_detail {mf}-{ma} vs leverkusen-matches.csv "
                f"{r['goals_for']}-{r['goals_against']}")
    total_for = sum(mf for _, mf, _ in per_match)
    total_against = sum(ma for _, _, ma in per_match)
    if len(rows) != 113:
        problems.append(f"total rows {len(rows)} != 113")
    if total_for != 89:
        problems.append(f"'for' goals {total_for} != 89")
    if total_against != 24:
        problems.append(f"'against' goals {total_against} != 24")
    if (total_own, own_for) != (3, 3):
        problems.append(f"own goals {total_own} ({own_for} for) != 3 (all for)")
    if problems:
        raise SystemExit(
            "goals_detail.csv NOT written — verification failed:\n  "
            + "\n  ".join(problems))

    rows.sort(key=lambda x: (x["match_week"], x["period"], x["minute"], x["second"]))
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"\nWrote {path}  ({len(rows)} goals: {total_for} for, {total_against} "
          f"against, incl. {total_own} own goals all for)")


def main():
    recs, fid, fname = build_records()
    print(f"Featured team: {fname} (id {fid}) — {len(recs)} matches, "
          f"weeks {recs[0]['match_week']}-{recs[-1]['match_week']}")
    verification(recs)
    q1_expected_points(recs)      # sets xg_for/against, xpts, probs
    q2_goal_timings(recs)
    q3_game_state(recs)           # sets lead/level/trail sec
    q4_trend(recs)                # sets shots_for_n, rolling fields
    write_csv(recs, os.path.join(REPO_ROOT, "leverkusen-matches.csv"))
    write_goals_csv(recs, os.path.join(REPO_ROOT, "goals_detail.csv"))


if __name__ == "__main__":
    main()
