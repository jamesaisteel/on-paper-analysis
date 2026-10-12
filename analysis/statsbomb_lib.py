#!/usr/bin/env python3
"""
Reusable primitives for the Leverkusen (and any single-team StatsBomb release)
event-data analysis.

Contains, deliberately dependency-free (standard library only):
  - data loading and per-match extraction
  - Poisson-binomial goal distributions and exact match win/draw/loss
    probabilities by convolution
  - a running-scoreline / game-state timeline builder

Nothing in here prints or writes files; run_analysis.py drives it.

Design note: everything keys off a single "featured team" — the one club that
appears in every match of the release. For competition 9 / season 281 that is
Bayer Leverkusen (id 904). Point find_featured_team() at another single-team
release and the same code runs unchanged.
"""
import json
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")

# Event-type names that are administrative, not on-ball play. Used when we need
# the last genuine action of a period as a fallback for its end time.
NON_PLAY_TYPES = {
    "Half End", "Half Start", "Starting XI", "Tactical Shift",
    "Substitution", "Injury Stoppage", "Player Off", "Player On",
    "Referee Ball-Drop", "Bad Behaviour",
}


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def load_match_list(competition=9, season=281):
    path = os.path.join(DATA_DIR, "matches", str(competition), f"{season}.json")
    with open(path) as f:
        return json.load(f)


def load_events(match_id):
    path = os.path.join(DATA_DIR, "events", f"{match_id}.json")
    with open(path) as f:
        return json.load(f)


def find_featured_team(matches):
    """The team present in every match of a single-team release."""
    from collections import Counter
    appear = Counter()
    for m in matches:
        appear[(m["home_team"]["home_team_id"], m["home_team"]["home_team_name"])] += 1
        appear[(m["away_team"]["away_team_id"], m["away_team"]["away_team_name"])] += 1
    n = len(matches)
    featured = [k for k, c in appear.items() if c == n]
    if len(featured) != 1:
        raise ValueError(f"expected exactly one team in all {n} matches, got {featured}")
    return featured[0]  # (team_id, team_name)


# --------------------------------------------------------------------------- #
# Per-match extraction
# --------------------------------------------------------------------------- #
def _period_boundaries(events):
    """Return {period: (start_sec, end_sec)} using Half Start / Half End
    markers, in that period's own minute:second clock. Falls back to the first
    / last on-ball event if a marker is missing."""
    bounds = {}
    for p in (1, 2):
        pe = [e for e in events if e["period"] == p]
        if not pe:
            continue
        starts = [e for e in pe if e["type"]["name"] == "Half Start"]
        ends = [e for e in pe if e["type"]["name"] == "Half End"]
        if starts:
            s = min(_ev_sec(e) for e in starts)
        else:
            play = [e for e in pe if e["type"]["name"] not in NON_PLAY_TYPES]
            s = min(_ev_sec(e) for e in play)
        if ends:
            en = max(_ev_sec(e) for e in ends)
        else:
            play = [e for e in pe if e["type"]["name"] not in NON_PLAY_TYPES]
            en = max(_ev_sec(e) for e in play)
        bounds[p] = (s, en)
    return bounds


def _ev_sec(e):
    """This event's time within its own period clock, in seconds."""
    return e["minute"] * 60 + e["second"]


def abs_time_factory(bounds):
    """Return a function mapping (period, minute, second) -> absolute, monotonic
    match seconds from kickoff, stitching period 2 onto the end of period 1."""
    p1_start, p1_end = bounds.get(1, (0, 0))
    p1_dur = p1_end - p1_start
    p2_start = bounds.get(2, (2700, 2700))[0]

    def abs_time(period, minute, second):
        t = minute * 60 + second
        if period == 1:
            return t - p1_start
        # period 2 (and, defensively, anything later) stitched after period 1
        return p1_dur + (t - p2_start)
    return abs_time


def extract_match(match, events, featured_id):
    """Build a compact, analysis-ready record for one match, oriented so that
    'for' == the featured team and 'against' == its opponent."""
    home = match["home_team"]
    away = match["away_team"]
    featured_home = (home["home_team_id"] == featured_id)
    opp = away if featured_home else home
    opponent_name = opp["away_team_name"] if featured_home else opp["home_team_name"]
    opponent_id = opp["away_team_id"] if featured_home else opp["home_team_id"]

    bounds = _period_boundaries(events)
    abs_time = abs_time_factory(bounds)
    match_end_sec = abs_time(2, *_minsec(bounds[2][1]))

    shots_for, shots_against = [], []
    goals = []  # unified goal timeline: dicts with time + scoring side

    for e in events:
        tn = e["type"]["name"]
        if tn == "Shot":
            sh = e["shot"]
            xg = sh.get("statsbomb_xg", 0.0) or 0.0
            is_pen = sh.get("type", {}).get("name") == "Penalty"
            is_goal = sh.get("outcome", {}).get("name") == "Goal"
            rec = {
                "xg": xg,
                "is_penalty": is_pen,
                "is_goal": is_goal,
                "period": e["period"],
                "minute": e["minute"],
                "second": e["second"],
            }
            if e["team"]["id"] == featured_id:
                shots_for.append(rec)
            else:
                shots_against.append(rec)
            if is_goal:
                goals.append({
                    "for_featured": e["team"]["id"] == featured_id,
                    "kind": "penalty" if is_pen else "shot",
                    "period": e["period"], "minute": e["minute"], "second": e["second"],
                    "xg": xg,
                    "player": e.get("player", {}).get("name"),
                    "abs_sec": abs_time(e["period"], e["minute"], e["second"]),
                })
        elif tn == "Own Goal For":
            # Credited to the beneficiary team; counts as a goal FOR them.
            goals.append({
                "for_featured": e["team"]["id"] == featured_id,
                "kind": "own_goal",
                "period": e["period"], "minute": e["minute"], "second": e["second"],
                "xg": None,
                "player": e.get("player", {}).get("name"),
                "abs_sec": abs_time(e["period"], e["minute"], e["second"]),
            })
        # "Own Goal Against" is the mirror of "Own Goal For" — same physical
        # goal — so we deliberately ignore it to avoid double counting.

    goals.sort(key=lambda g: (g["period"], g["minute"], g["second"]))

    goals_for = sum(1 for g in goals if g["for_featured"])
    goals_against = sum(1 for g in goals if not g["for_featured"])

    if goals_for > goals_against:
        result = "W"
    elif goals_for == goals_against:
        result = "D"
    else:
        result = "L"
    points = {"W": 3, "D": 1, "L": 0}[result]

    return {
        "match_id": match["match_id"],
        "match_week": match["match_week"],
        "date": match["match_date"],
        "opponent": opponent_name,
        "opponent_id": opponent_id,
        "venue": "H" if featured_home else "A",
        "goals_for": goals_for,
        "goals_against": goals_against,
        # scores as recorded in the match file, for cross-checking our parse
        "file_score_for": match["home_score"] if featured_home else match["away_score"],
        "file_score_against": match["away_score"] if featured_home else match["home_score"],
        "result": result,
        "points": points,
        "shots_for": shots_for,
        "shots_against": shots_against,
        "goals": goals,
        "match_end_sec": match_end_sec,
        "bounds": bounds,
        "abs_time": abs_time,
    }


def _minsec(sec):
    return (sec // 60, sec % 60)


# --------------------------------------------------------------------------- #
# Poisson-binomial goal model and exact match probabilities
# --------------------------------------------------------------------------- #
def poisson_binomial_pmf(probs):
    """PMF over the number of successes for independent Bernoulli(p_i).
    Returns list where index k = P(exactly k successes). Exact, by convolution."""
    dist = [1.0]
    for p in probs:
        p = min(max(float(p), 0.0), 1.0)
        nxt = [0.0] * (len(dist) + 1)
        for k, dk in enumerate(dist):
            nxt[k] += dk * (1.0 - p)
            nxt[k + 1] += dk * p
        dist = nxt
    return dist


def match_outcome_probs(xg_for, xg_against):
    """Exact P(win), P(draw), P(loss) for the featured team, modelling each
    team's goals as a Poisson-binomial over its shot xG list and treating the
    two teams as independent. No simulation."""
    fdist = poisson_binomial_pmf(xg_for)
    adist = poisson_binomial_pmf(xg_against)
    p_win = p_draw = p_loss = 0.0
    for kf, pf in enumerate(fdist):
        for ka, pa in enumerate(adist):
            joint = pf * pa
            if kf > ka:
                p_win += joint
            elif kf == ka:
                p_draw += joint
            else:
                p_loss += joint
    return p_win, p_draw, p_loss


def expected_points(xg_for, xg_against):
    """Expected league points for the featured team from a single match."""
    p_win, p_draw, p_loss = match_outcome_probs(xg_for, xg_against)
    return 3.0 * p_win + 1.0 * p_draw, (p_win, p_draw, p_loss)


# --------------------------------------------------------------------------- #
# Game-state timeline (minutes leading / level / trailing, featured POV)
# --------------------------------------------------------------------------- #
def game_state_minutes(match):
    """Seconds the featured team spent leading, level and trailing, from the
    running scoreline. Intervals run from kickoff to each goal to full time."""
    lead = level = trail = 0.0
    sf = sa = 0  # score for / against
    t_prev = 0.0
    end = match["match_end_sec"]

    def bucket(a, b, sf, sa):
        nonlocal lead, level, trail
        dur = max(0.0, b - a)
        if sf > sa:
            lead += dur
        elif sf == sa:
            level += dur
        else:
            trail += dur

    for g in match["goals"]:
        t = g["abs_sec"]
        bucket(t_prev, t, sf, sa)
        if g["for_featured"]:
            sf += 1
        else:
            sa += 1
        t_prev = t
    bucket(t_prev, end, sf, sa)

    return {"lead_sec": lead, "level_sec": level, "trail_sec": trail,
            "total_sec": lead + level + trail}


def running_state_before_after(match, goal):
    """For a given goal in match['goals'], the featured-team result category
    ('lead'/'level'/'trail') immediately before and after it is scored."""
    sf = sa = 0
    before = None
    for g in match["goals"]:
        state = "lead" if sf > sa else ("level" if sf == sa else "trail")
        if g is goal:
            before = state
            if g["for_featured"]:
                sf += 1
            else:
                sa += 1
            after = "lead" if sf > sa else ("level" if sf == sa else "trail")
            return before, after
        if g["for_featured"]:
            sf += 1
        else:
            sa += 1
    raise ValueError("goal not found in match timeline")
