"""Live English Premier League data from TheSportsDB (free API, key '3').

Fetches the current standings, recent results, and upcoming fixtures, and
formats them into a compact text block that gets injected into the chatbot's
prompt so it can answer with up-to-date information.
"""

import json
import time
import urllib.request
from datetime import datetime, timezone

API = "https://www.thesportsdb.com/api/v1/json/3"
EPL_LEAGUE_ID = "4328"   # English Premier League on TheSportsDB
# Official Fantasy Premier League API (public, no key) — used for top scorers.
FPL_API = "https://fantasy.premierleague.com/api/bootstrap-static/"

# simple in-memory cache so we don't hammer the APIs on every message
_CACHE = {}
_TTL = 300  # seconds (5 minutes)


def _get(url):
    """GET a URL with a short timeout and a tiny cache."""
    now = time.time()
    hit = _CACHE.get(url)
    if hit and now - hit[0] < _TTL:
        return hit[1]
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (epl-chatbot/1.0)"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    _CACHE[url] = (now, data)
    return data


def clear_cache():
    """Forget all cached API responses so the next call fetches fresh data."""
    _CACHE.clear()


def current_season():
    """EPL season string like '2025-2026'. Season starts in August."""
    now = datetime.now()
    start_year = now.year if now.month >= 8 else now.year - 1
    return f"{start_year}-{start_year + 1}"


def get_standings(season=None):
    season = season or current_season()
    data = _get(f"{API}/lookuptable.php?l={EPL_LEAGUE_ID}&s={season}")
    rows = (data or {}).get("table") or []
    out = []
    for r in rows:
        out.append({
            "rank": r.get("intRank"),
            "team": r.get("strTeam"),
            "played": r.get("intPlayed"),
            "win": r.get("intWin"),
            "draw": r.get("intDraw"),
            "loss": r.get("intLoss"),
            "gf": r.get("intGoalsFor"),
            "ga": r.get("intGoalsAgainst"),
            "gd": r.get("intGoalDifference"),
            "points": r.get("intPoints"),
            "form": r.get("strForm"),
        })
    return out


def _fmt_event_result(e):
    hs, as_ = e.get("intHomeScore"), e.get("intAwayScore")
    date = e.get("dateEvent") or (e.get("strTimestamp") or "")[:10]
    if hs is not None and as_ is not None:
        return f"{date}: {e.get('strHomeTeam')} {hs}-{as_} {e.get('strAwayTeam')}"
    return f"{date}: {e.get('strEvent')}"


def _fmt_event_fixture(e):
    ts = e.get("strTimestamp") or e.get("dateEvent") or ""
    return f"{ts[:16].replace('T', ' ')}: {e.get('strEvent')}"


def get_top_scorers(limit=10):
    """Top scorers this season from the official FPL API."""
    data = _get(FPL_API)
    teams = {t["id"]: t["name"] for t in data.get("teams", [])}
    players = data.get("elements", [])
    ranked = sorted(players, key=lambda p: p.get("goals_scored", 0), reverse=True)
    out = []
    for p in ranked[:limit]:
        if not p.get("goals_scored"):
            break
        name = f"{p.get('first_name','')} {p.get('second_name','')}".strip()
        out.append({
            "name": name or p.get("web_name"),
            "team": teams.get(p.get("team"), "?"),
            "goals": p.get("goals_scored", 0),
            "assists": p.get("assists", 0),
        })
    return out


def _events_named(name):
    data = _get(f"{API}/searchevents.php?e={name.replace(' ', '_')}")
    return (data or {}).get("event") or []


def get_head_to_head(team_a, team_b, limit=8):
    """Recent meetings between two clubs (both home/away orientations)."""
    events = _events_named(f"{team_a} vs {team_b}") + _events_named(f"{team_b} vs {team_a}")
    seen, rows = set(), []
    for e in events:
        eid = e.get("idEvent")
        if eid in seen:
            continue
        seen.add(eid)
        rows.append(e)
    rows.sort(key=lambda e: e.get("dateEvent") or "", reverse=True)
    return [_fmt_event_result(e) for e in rows[:limit]]


# Canonical TheSportsDB club names -> common aliases users might type.
# (The free data API truncates club-list endpoints, so we keep a fixed map.)
CLUBS = {
    "Arsenal": ["arsenal", "gunners"],
    "Aston Villa": ["aston villa", "villa"],
    "Bournemouth": ["bournemouth", "afc bournemouth", "cherries"],
    "Brentford": ["brentford", "bees"],
    "Brighton and Hove Albion": ["brighton", "brighton and hove", "seagulls"],
    "Burnley": ["burnley", "clarets"],
    "Chelsea": ["chelsea", "blues"],
    "Crystal Palace": ["crystal palace", "palace", "eagles"],
    "Everton": ["everton", "toffees"],
    "Fulham": ["fulham", "cottagers"],
    "Leeds United": ["leeds united", "leeds"],
    "Liverpool": ["liverpool", "reds"],
    "Manchester City": ["manchester city", "man city", "mancity", "city", "mcfc"],
    "Manchester United": ["manchester united", "man united", "man utd", "united", "mufc"],
    "Newcastle United": ["newcastle united", "newcastle", "magpies", "toon"],
    "Nottingham Forest": ["nottingham forest", "nott'm forest", "notts forest", "forest"],
    "Sunderland": ["sunderland", "black cats"],
    "Tottenham Hotspur": ["tottenham hotspur", "tottenham", "spurs", "thfc"],
    "West Ham United": ["west ham united", "west ham", "hammers"],
    "Wolverhampton Wanderers": ["wolverhampton wanderers", "wolverhampton", "wolves"],
}


def team_names():
    """Canonical names of the current EPL clubs."""
    return list(CLUBS)


def find_teams_in_text(text):
    """Return canonical EPL club names mentioned in text (longest alias first)."""
    text_l = " " + (text or "").lower() + " "
    # match longer aliases first so "man united" beats "united"
    aliases = []
    for canonical, names in CLUBS.items():
        for a in names:
            aliases.append((a, canonical))
    aliases.sort(key=lambda x: len(x[0]), reverse=True)

    found = []
    consumed = text_l
    for alias, canonical in aliases:
        if f" {alias} " in consumed or f" {alias}." in consumed or f" {alias}?" in consumed:
            if canonical not in found:
                found.append(canonical)
            consumed = consumed.replace(alias, "")  # avoid double-matching substrings
    return found


def get_recent_results(limit=12):
    data = _get(f"{API}/eventspastleague.php?id={EPL_LEAGUE_ID}")
    events = (data or {}).get("events") or []
    return [_fmt_event_result(e) for e in events[:limit]]


def get_upcoming_fixtures(limit=12):
    data = _get(f"{API}/eventsnextleague.php?id={EPL_LEAGUE_ID}")
    events = (data or {}).get("events") or []
    return [_fmt_event_fixture(e) for e in events[:limit]]


def build_context_block():
    """Assemble a compact, model-friendly snapshot of live EPL data."""
    season = current_season()
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"LIVE PREMIER LEAGUE DATA (season {season}, fetched {stamp}):", ""]

    try:
        standings = get_standings(season)
    except Exception as ex:
        standings = []
        lines.append(f"(standings unavailable: {ex})")

    if standings:
        lines.append(f"LEAGUE TABLE — leading clubs (top {len(standings)}; "
                     "Pos. Team — Pld W-D-L GD Pts | Form):")
        for s in standings:
            lines.append(
                f"{s['rank']}. {s['team']} — "
                f"{s['played']} {s['win']}-{s['draw']}-{s['loss']} "
                f"GD {s['gd']} {s['points']}pts | {s['form'] or '-'}"
            )
        lines.append("")

    try:
        scorers = get_top_scorers()
        if scorers:
            lines.append("TOP SCORERS:")
            for i, s in enumerate(scorers, 1):
                lines.append(f"{i}. {s['name']} ({s['team']}) — {s['goals']} goals, {s['assists']} assists")
            lines.append("")
    except Exception:
        pass

    try:
        results = get_recent_results()
        if results:
            lines.append("RECENT RESULTS:")
            lines.extend(results)
            lines.append("")
    except Exception:
        pass

    try:
        fixtures = get_upcoming_fixtures()
        if fixtures:
            lines.append("UPCOMING FIXTURES:")
            lines.extend(fixtures)
            lines.append("")
    except Exception:
        pass

    return "\n".join(lines).strip()


if __name__ == "__main__":
    # quick manual test
    print(build_context_block())
