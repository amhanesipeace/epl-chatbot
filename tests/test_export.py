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
