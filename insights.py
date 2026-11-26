"""Turn raw EPL data into narrative insights — the 'stories' layer.

Each helper takes already-fetched structured data (standings, scorers, results)
and returns a small dict: {title, detail}. The dashboard surfaces these so a
reader gets the STORY, not just a table. This is deliberately pure/O(n) and
has no network calls, so it is fast and easy to test.
"""
from __future__ import annotations

# A Premier League season is 38 games — the basis for pace projections.
SEASON_GAMES = 38


def _int(v, default=0):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _form_points(form: str) -> int:
    """Points from a form string like 'WWDLW' (W=3, D=1, L=0)."""
    return sum({"W": 3, "D": 1}.get(c, 0) for c in (form or "").upper())


def title_race(standings: list[dict]) -> dict | None:
    """The gap at the top — is it a runaway or a genuine race?"""
    if len(standings) < 2:
        return None
    first, second = standings[0], standings[1]
    gap = _int(first["points"]) - _int(second["points"])
    if gap == 0:
        detail = (f"{first['team']} and {second['team']} are level on "
                  f"{_int(first['points'])} pts — separated only by goal difference.")
        title = "Dead heat at the top"
    elif gap <= 2:
        detail = (f"{first['team']} lead {second['team']} by just {gap} "
                  f"point{'s' if gap != 1 else ''} — a real title race.")
        title = "Tight at the top"
    else:
        detail = (f"{first['team']} lead by {gap} points over {second['team']}, "
                  "opening a commanding gap.")
        title = f"{first['team']} pulling clear"
    return {"title": title, "detail": detail}


def projected_pace(standings: list[dict]) -> dict | None:
    """Where the leader's current pace lands them over a full 38-game season.

    Every other table insight reads the standings as they are *now*; this one
    looks forward, extrapolating the leader's points-per-game across the whole
    campaign. It needs enough games for the rate to mean something and stays
    quiet once the season is effectively complete (nothing left to project).
    """
    if not standings:
        return None
    leader = standings[0]
    played = _int(leader.get("played"))
    points = _int(leader.get("points"))
    if played < 5 or played >= SEASON_GAMES:
        return None  # too early to extrapolate, or no games left to project
    ppg = points / played
    projected = round(ppg * SEASON_GAMES)
    # Historic EPL context: ~90+ usually wins the title, 100 is exceptional.
    if projected >= 100:
        note = " — a historic, record-chasing pace."
    elif projected >= 90:
        note = " — title-winning pace on recent history."
    else:
        note = "."
    return {
        "title": f"{leader['team']} on course for {projected} points",
        "detail": (f"{leader['team']} are averaging {ppg:.2f} points a game from "
                   f"{played} played — on track for about {projected} across the "
                   f"{SEASON_GAMES}-game season{note}"),
    }


def european_race(standings: list[dict]) -> dict | None:
    """The scrap for the final Champions League place (4th vs 5th).

    Stays quiet when the top four looks settled, so the dashboard only tells the
    story when it is a genuine race.
    """
    if len(standings) < 5:
        return None
    fourth, fifth = standings[3], standings[4]
    gap = _int(fourth["points"]) - _int(fifth["points"])
    if gap > 3:
        return None  # top four looks settled — no story worth surfacing
    if gap == 0:
        return {
            "title": "Scrap for the top four",
            "detail": (f"{fourth['team']} and {fifth['team']} are level on "
                       f"{_int(fourth['points'])} pts for the last Champions "
                       "League place — split only by goal difference."),
        }
    return {
        "title": "Race for the top four",
        "detail": (f"{fourth['team']} cling to the final Champions League spot, "
                   f"just {gap} point{'s' if gap != 1 else ''} ahead of "
                   f"{fifth['team']}."),
    }


def in_form_team(standings: list[dict]) -> dict | None:
    """Best recent form (last ~5) — momentum, not season-long position."""
    ranked = [s for s in standings if s.get("form")]
    if not ranked:
        return None
    best = max(ranked, key=lambda s: (_form_points(s["form"]), s["form"].count("W")))
    fp = _form_points(best["form"])
    if fp < 7:  # nobody is really hot
        return None
    return {
        "title": f"{best['team']} are flying",
        "detail": (f"Best current form in the league: {best['form']} "
                   f"({fp}/15 pts from their last {len(best['form'])})."),
    }


def unbeaten_run(standings: list[dict]) -> dict | None:
    """A side still unbeaten this season — a season-long resilience story.

    Complements :func:`in_form_team` (which reads the last ~5 only): staying
    unbeaten across the whole campaign is a different, rarer narrative. Requires
    a meaningful number of games played so a one- or two-game start does not
    count, and stays quiet once everyone has lost.
    """
    unbeaten = [s for s in standings
                if _int(s.get("loss"), -1) == 0 and _int(s.get("played")) >= 5]
    if not unbeaten:
        return None
    # The longest, most substantial run: most games, then points, then GD.
    best = max(unbeaten, key=lambda s: (_int(s.get("played")),
                                        _int(s.get("points")), _int(s.get("gd"))))
    played = _int(best.get("played"))
    won, drawn = _int(best.get("win")), _int(best.get("draw"))
    record = f"{played} played, {won} won, {drawn} drawn"
    top = bool(standings) and standings[0]["team"] == best["team"]
    lead_in = "Leading the way and still" if top else "Still"
    detail = f"{lead_in} to be beaten this season — {record}."
    if len(unbeaten) == 1:
        detail += " The only side yet to taste defeat."
    return {"title": f"{best['team']} still unbeaten", "detail": detail}


def struggling_team(standings: list[dict]) -> dict | None:
    """Worst recent form among the bottom half — a relegation story."""
    ranked = [s for s in standings if s.get("form")]
    if not ranked:
        return None
    worst = min(ranked, key=lambda s: (_form_points(s["form"]), -s["form"].count("L")))
    fp = _form_points(worst["form"])
    if fp > 4:
        return None
    return {
        "title": f"Alarm bells for {worst['team']}",
        "detail": (f"Poorest form in the division: {worst['form']} "
                   f"({fp}/15 pts) — pressure building."),
    }


def winless_run(standings: list[dict]) -> dict | None:
    """A side still without a win this season — the mirror of :func:`unbeaten_run`.

    Season-long, unlike :func:`struggling_team` (which reads the last ~5 games):
    going a whole campaign without a win is its own, rarer story. Requires a
    meaningful number of games played so a slow start does not count, and stays
    quiet once every side has won at least once.
    """
    winless = [s for s in standings
               if _int(s.get("win"), -1) == 0 and _int(s.get("played")) >= 5]
    if not winless:
        return None
    # The longest, most troubling run: most games, then fewest points, then worst GD.
    worst = max(winless, key=lambda s: (_int(s.get("played")),
                                        -_int(s.get("points")), -_int(s.get("gd"))))
    played = _int(worst.get("played"))
    drawn, lost = _int(worst.get("draw")), _int(worst.get("loss"))
    record = f"{played} played, {drawn} drawn, {lost} lost"
    bottom = bool(standings) and standings[-1]["team"] == worst["team"]
    lead_in = "Rock bottom and still" if bottom else "Still"
    detail = f"{lead_in} without a win this season — {record}."
    if len(winless) == 1:
        detail += " The last side yet to win a game."
    return {"title": f"{worst['team']} still winless", "detail": detail}


def relegation_battle(standings: list[dict]) -> dict | None:
    """The scrap just above the drop — last safe place (n-3) vs first relegated.

    The mirror of :func:`european_race` at the bottom of the table: bottom three
    go down, so the story is the points gap between the last safe side and the
    team sitting just inside the relegation zone. Stays quiet when safety looks
    settled, so the dashboard only surfaces a genuine fight.
    """
    if len(standings) < 6:
        return None
    safe, drop = standings[-4], standings[-3]
    gap = _int(safe["points"]) - _int(drop["points"])
    if gap > 3:
        return None  # safety looks settled — no story worth surfacing
    if gap == 0:
        return {
            "title": "Relegation dogfight",
            "detail": (f"{drop['team']} and {safe['team']} are level on "
                       f"{_int(drop['points'])} pts either side of the drop — "
                       "separated only by goal difference."),
        }
    return {
        "title": "Relegation battle",
        "detail": (f"{drop['team']} sit in the relegation zone, just "
                   f"{gap} point{'s' if gap != 1 else ''} from safety and "
                   f"{safe['team']}."),
    }


def best_attack_defense(standings: list[dict]) -> dict | None:
    """Who scores most and who concedes least."""
    if not standings:
        return None
    top_attack = max(standings, key=lambda s: _int(s.get("gf")))
    best_def = min(standings, key=lambda s: _int(s.get("ga")))
    return {
        "title": "Attack vs defence",
        "detail": (f"{top_attack['team']} have the league's best attack "
                   f"({_int(top_attack['gf'])} goals); {best_def['team']} the "
                   f"meanest defence ({_int(best_def['ga'])} conceded)."),
    }


def biggest_win(results: list[dict]) -> dict | None:
    """The biggest-margin result in the recent set — a headline scoreline."""
    if not results:
        return None
    def margin(r):
        return abs(r["home_score"] - r["away_score"])
    top = max(results, key=margin)
    if margin(top) < 3:
        return None
    if top["home_score"] > top["away_score"]:
        winner, loser, score = top["home"], top["away"], f"{top['home_score']}-{top['away_score']}"
    else:
        winner, loser, score = top["away"], top["home"], f"{top['away_score']}-{top['home_score']}"
    return {
        "title": "Statement result",
        "detail": f"{winner} thumped {loser} {score} ({top['date']}).",
    }


def goals_glut(results: list[dict]) -> dict | None:
    """Are recent games high-scoring? A simple pace-of-play story."""
    if len(results) < 4:
        return None
    total = sum(r["home_score"] + r["away_score"] for r in results)
    avg = total / len(results)
    return {
        "title": "Goals are flowing" if avg >= 2.7 else "Cagey affairs",
        "detail": (f"{avg:.1f} goals per game across the last {len(results)} "
                   f"matches ({total} goals total)."),
    }


def scorer_race(scorers: list[dict]) -> dict | None:
    """The Golden Boot picture — leader and margin."""
    if not scorers:
        return None
    leader = scorers[0]
    if len(scorers) == 1 or leader["goals"] == 0:
        return None
    lead = leader["goals"] - scorers[1]["goals"]
    if lead >= 3:
        detail = (f"{leader['name']} ({leader['team']}) leads the scoring charts "
                  f"with {leader['goals']} — {lead} clear of the field.")
        title = f"{leader['name']} out in front"
    elif lead == 0:
        detail = (f"{leader['name']} and {scorers[1]['name']} share top spot on "
                  f"{leader['goals']} goals.")
        title = "Golden Boot deadlock"
    else:
        detail = (f"{leader['name']} ({leader['team']}) tops the charts with "
                  f"{leader['goals']}, just {lead} ahead of {scorers[1]['name']}.")
        title = "Golden Boot race on"
    return {"title": title, "detail": detail}


def most_involvements(scorers: list[dict]) -> dict | None:
    """Most goal involvements (goals + assists) — the player shaping the most
    goals, which the goals-only Golden Boot race can miss.

    Ranks by involvements, then goals as a tiebreak. Points out when the leader
    is a creator the scoring charts overlook (i.e. not the top scorer).
    """
    ranked = [s for s in scorers if (_int(s.get("goals")) + _int(s.get("assists")))]
    if len(ranked) < 2:
        return None
    ranked.sort(key=lambda s: (_int(s.get("goals")) + _int(s.get("assists")),
                               _int(s.get("goals"))), reverse=True)
    leader = ranked[0]
    g, a = _int(leader.get("goals")), _int(leader.get("assists"))
    total = g + a
    lead = total - (_int(ranked[1].get("goals")) + _int(ranked[1].get("assists")))
    breakdown = f"{g} goal{'s' if g != 1 else ''} + {a} assist{'s' if a != 1 else ''}"

    # Is the involvements leader a different player from the top scorer?
    top_scorer = max(scorers, key=lambda s: _int(s.get("goals")))
    if leader["name"] != top_scorer["name"] and a >= g:
        return {
            "title": f"{leader['name']} pulling the strings",
            "detail": (f"{leader['team']}'s {leader['name']} has a hand in the most "
                       f"goals — {total} involvements ({breakdown}), more than any "
                       "out-and-out striker."),
        }
    if lead == 0:
        return {
            "title": "Involvements deadlock",
            "detail": (f"{leader['name']} ({leader['team']}) tops goal involvements "
                       f"on {total} ({breakdown}), level with the chasing pack."),
        }
    return {
        "title": f"{leader['name']} most involved",
        "detail": (f"{leader['name']} ({leader['team']}) leads for goal "
                   f"involvements with {total} ({breakdown}), {lead} clear."),
    }


def build_insights(standings, scorers, results) -> list[dict]:
    """Run every insight generator and return the ones that fired."""
    candidates = [
        title_race(standings),
        projected_pace(standings),
        european_race(standings),
        in_form_team(standings),
        unbeaten_run(standings),
        struggling_team(standings),
        winless_run(standings),
        relegation_battle(standings),
        best_attack_defense(standings),
        scorer_race(scorers),
        most_involvements(scorers),
        biggest_win(results),
        goals_glut(results),
    ]
    return [c for c in candidates if c]
