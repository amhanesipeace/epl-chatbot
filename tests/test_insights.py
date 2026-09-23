"""Tests for the insights engine (insights.py).

The engine is pure and network-free, so we feed it synthetic data and assert on
the narrative output. Each insight is tested for both when it SHOULD fire and
when it should stay quiet (so the dashboard doesn't surface weak stories).
"""
import insights


# --- builders for synthetic data --------------------------------------------

def team(rank, name, points, form="", gf=0, ga=0, played=5, w=0, d=0, l=0, gd=0):
    return {"rank": rank, "team": name, "points": points, "form": form,
            "gf": gf, "ga": ga, "played": played, "win": w, "draw": d,
            "loss": l, "gd": gd}


def scorer(name, goals, team_="X", assists=0):
    return {"name": name, "team": team_, "goals": goals, "assists": assists}


def result(home, away, hs, as_, date="2026-09-20"):
    return {"home": home, "away": away, "home_score": hs, "away_score": as_,
            "date": date}


# --- helpers ----------------------------------------------------------------

def test_form_points():
    assert insights._form_points("WWWWW") == 15
    assert insights._form_points("WDLWD") == 3 + 1 + 0 + 3 + 1
    assert insights._form_points("") == 0
    assert insights._form_points(None) == 0


def test_int_coerces_and_defaults():
    assert insights._int("7") == 7
    assert insights._int(None) == 0
    assert insights._int("x", 5) == 5


# --- title_race -------------------------------------------------------------

def test_title_race_runaway():
    s = [team(1, "City", 20), team(2, "Arsenal", 15)]
    out = insights.title_race(s)
    assert "City" in out["title"]
    assert "5 points" in out["detail"]


def test_title_race_tight():
    s = [team(1, "City", 16), team(2, "Arsenal", 15)]
    out = insights.title_race(s)
    assert out["title"] == "Tight at the top"
    assert "1 point" in out["detail"]


def test_title_race_level():
    s = [team(1, "City", 15), team(2, "Arsenal", 15)]
    out = insights.title_race(s)
    assert "level" in out["detail"]


def test_title_race_needs_two_teams():
    assert insights.title_race([team(1, "City", 10)]) is None
    assert insights.title_race([]) is None


# --- in_form_team / struggling_team -----------------------------------------

def test_in_form_team_fires_for_hot_streak():
    s = [team(1, "City", 15, form="WWWWW"), team(2, "Arsenal", 12, form="WLWLL")]
    out = insights.in_form_team(s)
    assert "City" in out["title"]


def test_in_form_team_quiet_when_nobody_hot():
    s = [team(1, "City", 8, form="DLDLD"), team(2, "Arsenal", 7, form="LLDLL")]
    assert insights.in_form_team(s) is None


def test_struggling_team_fires_for_bad_form():
    s = [team(1, "City", 15, form="WWWWW"), team(20, "Bottom", 1, form="LLLLL")]
    out = insights.struggling_team(s)
    assert "Bottom" in out["title"]


def test_struggling_team_quiet_when_everyone_ok():
    s = [team(1, "City", 15, form="WWWWW"), team(2, "Arsenal", 12, form="WWDWW")]
    assert insights.struggling_team(s) is None


# --- best_attack_defense ----------------------------------------------------

def test_best_attack_defense():
    s = [team(1, "City", 15, gf=20, ga=8), team(2, "Arsenal", 12, gf=10, ga=3)]
    out = insights.best_attack_defense(s)
    assert "City" in out["detail"]      # best attack (20 goals)
    assert "Arsenal" in out["detail"]   # best defence (3 conceded)


# --- scorer_race ------------------------------------------------------------

def test_scorer_race_clear_leader():
    sc = [scorer("Haaland", 10), scorer("Isak", 5)]
    out = insights.scorer_race(sc)
    assert "Haaland" in out["title"]
    assert "5 clear" in out["detail"]


def test_scorer_race_deadlock():
    sc = [scorer("Haaland", 7), scorer("Isak", 7)]
    out = insights.scorer_race(sc)
    assert out["title"] == "Golden Boot deadlock"


def test_scorer_race_quiet_when_no_goals():
    assert insights.scorer_race([scorer("A", 0), scorer("B", 0)]) is None
    assert insights.scorer_race([]) is None


# --- biggest_win / goals_glut -----------------------------------------------

def test_biggest_win_fires_on_big_margin():
    r = [result("City", "Luton", 5, 0), result("Arsenal", "Spurs", 2, 1)]
    out = insights.biggest_win(r)
    assert "City" in out["detail"] and "5-0" in out["detail"]


def test_biggest_win_quiet_on_close_games():
    r = [result("City", "Luton", 2, 1), result("Arsenal", "Spurs", 1, 1)]
    assert insights.biggest_win(r) is None


def test_biggest_win_credits_away_winner():
    r = [result("Luton", "City", 0, 4)]
    out = insights.biggest_win(r)
    assert out["detail"].startswith("City")   # away team won 4-0


def test_goals_glut_high_scoring():
    r = [result("A", "B", 3, 3), result("C", "D", 2, 2),
         result("E", "F", 4, 1), result("G", "H", 3, 0)]
    out = insights.goals_glut(r)
    assert out["title"] == "Goals are flowing"


def test_goals_glut_low_scoring():
    r = [result("A", "B", 0, 0), result("C", "D", 1, 0),
         result("E", "F", 0, 1), result("G", "H", 1, 0)]
    out = insights.goals_glut(r)
    assert out["title"] == "Cagey affairs"


def test_goals_glut_needs_enough_games():
    assert insights.goals_glut([result("A", "B", 3, 3)]) is None


# --- build_insights (integration) -------------------------------------------

def test_build_insights_filters_none_and_returns_list():
    standings = [team(1, "City", 20, form="WWWWW", gf=20, ga=5),
                 team(2, "Arsenal", 12, form="WWDWW", gf=12, ga=6)]
    scorers = [scorer("Haaland", 10), scorer("Isak", 4)]
    results = [result("City", "Luton", 5, 0), result("Arsenal", "Spurs", 3, 2),
               result("Chelsea", "Everton", 2, 2), result("Fulham", "Brentford", 1, 1)]
    out = insights.build_insights(standings, scorers, results)
    assert isinstance(out, list) and len(out) >= 3
    assert all("title" in i and "detail" in i for i in out)


def test_build_insights_empty_data_is_safe():
    assert insights.build_insights([], [], []) == []
