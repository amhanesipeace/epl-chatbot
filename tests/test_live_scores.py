"""Tests for live-score parsing in epl_data.get_live_scores.

The network call is stubbed so these run offline and deterministically.
"""
import io
import json

import epl_data


class _FakeResp:
    def __init__(self, payload):
        self._data = json.dumps(payload).encode("utf-8")
    def read(self):
        return self._data
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


def _patch_feed(monkeypatch, payload):
    monkeypatch.setattr(epl_data.urllib.request, "urlopen",
                        lambda *a, **k: _FakeResp(payload))


def test_filters_to_requested_league(monkeypatch):
    payload = {"livescore": [
        {"idLeague": "4328", "strHomeTeam": "Arsenal", "strAwayTeam": "Chelsea",
         "intHomeScore": "2", "intAwayScore": "1", "strStatus": "2H",
         "strProgress": "67", "updated": "2026-09-23 14:00:00"},
        {"idLeague": "9999", "strHomeTeam": "Other", "strAwayTeam": "Team",
         "intHomeScore": "0", "intAwayScore": "0", "strStatus": "1H"},
    ]}
    _patch_feed(monkeypatch, payload)
    games = epl_data.get_live_scores()          # default = EPL (4328)
    assert len(games) == 1
    g = games[0]
    assert g["home"] == "Arsenal" and g["away"] == "Chelsea"
    assert g["home_score"] == "2" and g["away_score"] == "1"
    assert g["status"] == "2H" and g["minute"] == "67"


def test_no_live_games_returns_empty(monkeypatch):
    _patch_feed(monkeypatch, {"livescore": []})
    assert epl_data.get_live_scores() == []


def test_missing_livescore_key_is_safe(monkeypatch):
    _patch_feed(monkeypatch, {})
    assert epl_data.get_live_scores() == []


def test_custom_league_id(monkeypatch):
    payload = {"livescore": [
        {"idLeague": "5944", "strHomeTeam": "Italy U20", "strAwayTeam": "Spain U20",
         "intHomeScore": "0", "intAwayScore": "2", "strStatus": "2H",
         "strProgress": "78"},
    ]}
    _patch_feed(monkeypatch, payload)
    assert epl_data.get_live_scores() == []          # EPL filter -> none
    games = epl_data.get_live_scores(league_id="5944")
    assert len(games) == 1 and games[0]["minute"] == "78"
