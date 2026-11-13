"""Tests for the CSV export layer (export.py) and the /api/standings.csv route.

The serialiser is pure, so it's tested directly on synthetic rows; the route is
tested with the live fetch monkeypatched so it runs offline.
"""
import csv
import io

import app as app_module
import epl_data
import export


def _row(rank, team, **kw):
    base = {"rank": rank, "team": team, "played": 10, "win": 6, "draw": 2,
            "loss": 2, "gf": 20, "ga": 10, "gd": 10, "points": 20, "form": "WWDLW"}
    base.update(kw)
    return base


def _parse(text):
    return list(csv.reader(io.StringIO(text)))


def test_header_row_always_present_even_when_empty():
    rows = _parse(export.standings_csv([]))
    assert len(rows) == 1
    assert rows[0] == ["Rank", "Team", "Played", "Won", "Drawn", "Lost",
                       "GF", "GA", "GD", "Points", "Form"]


def test_serialises_rows_in_order():
    text = export.standings_csv([_row(1, "Arsenal", points=27),
                                 _row(2, "City", points=25)])
    rows = _parse(text)
    assert len(rows) == 3                       # header + 2 teams
    assert rows[1][1] == "Arsenal" and rows[1][9] == "27"
    assert rows[2][1] == "City"


def test_missing_fields_render_as_empty_not_none():
    # A partial feed with some columns absent should not leak the text "None".
    text = export.standings_csv([{"rank": 1, "team": "Spurs", "points": 20}])
    assert "None" not in text
    row = _parse(text)[1]
    assert row[0] == "1" and row[1] == "Spurs"
    assert row[2] == "" and row[9] == "20"      # played empty, points filled
    assert row[10] == ""                        # form absent -> empty


def test_team_with_comma_is_quoted():
    text = export.standings_csv([_row(1, "Brighton, Hove")])
    assert '"Brighton, Hove"' in text
    assert _parse(text)[1][1] == "Brighton, Hove"


def test_route_returns_csv_attachment(monkeypatch):
    monkeypatch.setattr(epl_data, "get_standings",
                        lambda *a, **k: [_row(1, "Arsenal", points=30)])
    client = app_module.app.test_client()
    resp = client.get("/api/standings.csv")
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    assert "attachment" in resp.headers["Content-Disposition"]
    assert ".csv" in resp.headers["Content-Disposition"]
    assert b"Arsenal" in resp.data and b"Rank,Team" in resp.data


def test_route_survives_fetch_failure(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("feed down")
    monkeypatch.setattr(epl_data, "get_standings", _boom)
    client = app_module.app.test_client()
    resp = client.get("/api/standings.csv")
    assert resp.status_code == 200                      # header-only CSV, no 500
    assert resp.data.strip() == b"Rank,Team,Played,Won,Drawn,Lost,GF,GA,GD,Points,Form"


# --- scorers_csv ------------------------------------------------------------

def _scorer(name, goals, team="X", assists=0):
    return {"name": name, "team": team, "goals": goals, "assists": assists}


def test_scorers_header_present_when_empty():
    rows = _parse(export.scorers_csv([]))
    assert len(rows) == 1
    assert rows[0] == ["Rank", "Player", "Team", "Goals", "Assists"]


def test_scorers_rank_is_list_position():
    text = export.scorers_csv([_scorer("Haaland", 12, "City", 3),
                               _scorer("Salah", 10, "Liverpool", 5)])
    rows = _parse(text)
    assert rows[1] == ["1", "Haaland", "City", "12", "3"]
    assert rows[2][0] == "2" and rows[2][1] == "Salah"


def test_scorers_missing_fields_empty_not_none():
    text = export.scorers_csv([{"name": "X", "goals": 5}])   # no team/assists
    assert "None" not in text
    row = _parse(text)[1]
    assert row == ["1", "X", "", "5", ""]


def test_scorers_route_returns_csv_attachment(monkeypatch):
    monkeypatch.setattr(epl_data, "get_top_scorers",
                        lambda *a, **k: [_scorer("Haaland", 14, "City", 2)])
    client = app_module.app.test_client()
    resp = client.get("/api/scorers.csv")
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    assert "attachment" in resp.headers["Content-Disposition"]
    assert b"Haaland" in resp.data and b"Rank,Player,Team,Goals,Assists" in resp.data


def test_scorers_route_survives_fetch_failure(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("feed down")
    monkeypatch.setattr(epl_data, "get_top_scorers", _boom)
    client = app_module.app.test_client()
    resp = client.get("/api/scorers.csv")
    assert resp.status_code == 200
    assert resp.data.strip() == b"Rank,Player,Team,Goals,Assists"
