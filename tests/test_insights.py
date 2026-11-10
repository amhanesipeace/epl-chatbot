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


# --- european_race ----------------------------------------------------------

def _top5(p4, p5):
    """A 5-team table where only the 4th/5th points matter for this insight."""
    return [team(1, "City", 30), team(2, "Arsenal", 28), team(3, "Liverpool", 26),
            team(4, "Villa", p4), team(5, "Spurs", p5)]


def test_european_race_tight():
    out = insights.european_race(_top5(24, 22))
    assert out["title"] == "Race for the top four"
    assert "Villa" in out["detail"] and "Spurs" in out["detail"]
    assert "2 points" in out["detail"]


def test_european_race_level():
    out = insights.european_race(_top5(23, 23))
    assert out["title"] == "Scrap for the top four"
    assert "level" in out["detail"]


def test_european_race_quiet_when_settled():
    assert insights.european_race(_top5(24, 18)) is None   # 6-point gap


def test_european_race_needs_five_teams():
    assert insights.european_race([team(i, f"T{i}", 20) for i in range(1, 5)]) is None


# --- relegation_battle ------------------------------------------------------

def _bottom(safe_pts, drop_pts):
    """A 6-team table where only the last-safe (n-3) / first-dropped points matter.

    With 6 teams the drop zone is the bottom three: index 3 (= standings[-4]) is
    the last safe place, index 4 (= standings[-3]) the first team relegated.
    """
    return [team(1, "Top", 40), team(2, "Second", 38),
            team(3, "Safe", safe_pts), team(4, "Drop", drop_pts),
            team(5, "Weak", 8), team(6, "Bottom", 5)]


def test_relegation_battle_tight():
    out = insights.relegation_battle(_bottom(20, 18))
    assert out["title"] == "Relegation battle"
    assert "Drop" in out["detail"] and "Safe" in out["detail"]
    assert "2 points" in out["detail"]


def test_relegation_battle_level():
    out = insights.relegation_battle(_bottom(19, 19))
    assert out["title"] == "Relegation dogfight"
    assert "level" in out["detail"]


def test_relegation_battle_singular_point():
    assert "1 point from" in insights.relegation_battle(_bottom(20, 19))["detail"]


def test_relegation_battle_quiet_when_settled():
    assert insights.relegation_battle(_bottom(24, 18)) is None   # 6-point cushion


def test_relegation_battle_needs_enough_teams():
    assert insights.relegation_battle([team(i, f"T{i}", 20) for i in range(1, 6)]) is None


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


# --- most_involvements ------------------------------------------------------

def test_most_involvements_clear_leader():
    # Haaland: 12+2=14; Saka: 8+4=12. Haaland leads involvements by 2.
    sc = [scorer("Haaland", 12, "City", assists=2),
          scorer("Saka", 8, "Arsenal", assists=4)]
    out = insights.most_involvements(sc)
    assert out["title"] == "Haaland most involved"
    assert "14" in out["detail"] and "12 goals + 2 assists" in out["detail"]
    assert "2 clear" in out["detail"]


def test_most_involvements_highlights_a_creator_over_the_top_scorer():
    # Top scorer is Haaland (14 goals), but Palmer has more involvements and is
    # assist-heavy -> the insight should surface the creator.
    sc = [scorer("Haaland", 14, "City", assists=1),
          scorer("Palmer", 7, "Chelsea", assists=10)]
    out = insights.most_involvements(sc)
    assert out["title"] == "Palmer pulling the strings"
    assert "17" in out["detail"] and "7 goals + 10 assists" in out["detail"]


def test_most_involvements_deadlock():
    sc = [scorer("A", 6, "X", assists=4), scorer("B", 5, "Y", assists=5)]
    out = insights.most_involvements(sc)        # both on 10
    assert out["title"] == "Involvements deadlock"
    assert "level" in out["detail"]


def test_most_involvements_singular_wording():
    sc = [scorer("A", 1, "X", assists=1), scorer("B", 1, "Y", assists=0)]
    detail = insights.most_involvements(sc)["detail"]
    assert "1 goal + 1 assist" in detail        # singular, no trailing 's'


def test_most_involvements_quiet_without_data():
    assert insights.most_involvements([]) is None
    assert insights.most_involvements([scorer("A", 0, assists=0)]) is None
    assert insights.most_involvements([scorer("A", 5, assists=2)]) is None   # only one


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
