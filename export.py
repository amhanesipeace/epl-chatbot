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
        writer.writerow([
            "" if row.get(key) is None else row.get(key)
            for _, key in _STANDINGS_COLUMNS
        ])
    return buf.getvalue()
