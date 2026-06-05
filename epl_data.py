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

# simple in-memory cache so we don't hammer the API on every message
_CACHE = {}
_TTL = 300  # seconds (5 minutes)


def _get(url):
    """GET a URL with a short timeout and a tiny cache."""
    now = time.time()
    hit = _CACHE.get(url)
    if hit and now - hit[0] < _TTL:
        return hit[1]
    req = urllib.request.Request(url, headers={"User-Agent": "epl-chatbot/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    _CACHE[url] = (now, data)
    return data


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
        lines.append("STANDINGS (Pos. Team — Pld W-D-L GD Pts | Form):")
        for s in standings:
            lines.append(
                f"{s['rank']}. {s['team']} — "
                f"{s['played']} {s['win']}-{s['draw']}-{s['loss']} "
                f"GD {s['gd']} {s['points']}pts | {s['form'] or '-'}"
            )
        lines.append("")

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
