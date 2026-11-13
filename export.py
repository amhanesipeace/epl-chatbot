"""Turn fetched structured data into downloadable files — the 'take it with you'
layer.

Kept pure and network-free (like insights.py) so the serialisers are trivial to
test: they take already-fetched rows and return a string. The Flask routes in
app.py wrap these in a download Response.
"""
from __future__ import annotations

import csv
import io

# (output header, source key) for each standings column, in table order.
_STANDINGS_COLUMNS = [
    ("Rank", "rank"), ("Team", "team"), ("Played", "played"),
    ("Won", "win"), ("Drawn", "draw"), ("Lost", "loss"),
    ("GF", "gf"), ("GA", "ga"), ("GD", "gd"), ("Points", "points"),
    ("Form", "form"),
]


# (output header, source key) for each scorer column — the leading Rank column
# is the 1-based list position, not a source field.
_SCORERS_COLUMNS = [
    ("Player", "name"), ("Team", "team"), ("Goals", "goals"),
    ("Assists", "assists"),
]


def _blank(value):
    """Render None as an empty cell rather than the string "None"."""
    return "" if value is None else value


def standings_csv(standings: list[dict]) -> str:
    """Serialise the league table to CSV text (always includes the header row).

    Missing fields render as empty cells rather than the string "None", so a
    partial feed (TheSportsDB's free tier truncates the table) still exports
    cleanly.
    """
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([header for header, _ in _STANDINGS_COLUMNS])
    for row in standings:
        writer.writerow([_blank(row.get(key)) for _, key in _STANDINGS_COLUMNS])
    return buf.getvalue()


def scorers_csv(scorers: list[dict]) -> str:
    """Serialise the top-scorers table to CSV text (always includes the header).

    Prepends a 1-based Rank from the list order (the feed is already sorted by
    goals); missing fields render as empty cells, not "None".
    """
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Rank"] + [header for header, _ in _SCORERS_COLUMNS])
    for i, row in enumerate(scorers, start=1):
        writer.writerow([i] + [_blank(row.get(key)) for _, key in _SCORERS_COLUMNS])
    return buf.getvalue()
