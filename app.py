"""EPL Chatbot web app.

A small Flask server that serves a chat UI and answers Premier League questions
using a local Ollama model (Meta's Llama 3.1), grounded with LIVE standings,
results, and fixtures fetched from TheSportsDB.
"""

import json
import os
import urllib.request

from flask import Flask, Response, request, send_from_directory

import epl_data
import insights

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = os.environ.get("EPL_MODEL", "llama3.1:8b")
HERE = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)

PERSONA = """You are "Gaffer", a friendly, knowledgeable English Premier League (EPL) assistant created by Peace Amhanesi.

You answer questions about the Premier League: clubs, players, managers, stadiums, history, rules, tactics, standings, results, and fixtures. Use a warm, enthusiastic football-fan tone, be accurate and concise, and add a quick interesting fact when it fits.

You are given a LIVE DATA snapshot below with the current season's league table (leading clubs), top scorers, recent results, upcoming fixtures, and — when two clubs are mentioned — their recent head-to-head meetings. Treat this snapshot as the source of truth for anything current (table positions, points, top scorers, latest scores, who plays next, head-to-head). Quote it when relevant.

Note: the live table may only list the leading clubs, not all 20. If asked about a club not shown in the table, give what you can from the other live sections (top scorers, results, head-to-head) and your own knowledge, and say if you're unsure. If something is genuinely not available, say so honestly rather than guessing. Politely steer off-topic questions back to football."""


def build_system_prompt(user_text=""):
    """Persona + a fresh live-data block, plus head-to-head if two clubs are named."""
    try:
        live = epl_data.build_context_block()
    except Exception as ex:
        live = f"(Live data temporarily unavailable: {ex})"

    # If the user mentions two clubs, fetch their recent meetings for this turn.
    try:
        teams = epl_data.find_teams_in_text(user_text)
        if len(teams) >= 2:
            a, b = teams[0], teams[1]
            h2h = epl_data.get_head_to_head(a, b)
            if h2h:
                live += f"\n\nHEAD-TO-HEAD ({a} vs {b}, most recent first):\n" + "\n".join(h2h)
    except Exception:
        pass

    return f"{PERSONA}\n\n----- LIVE DATA -----\n{live}\n----- END LIVE DATA -----"


@app.route("/")
def index():
    return send_from_directory(HERE, "dashboard.html")


@app.route("/chat")
def chat_page():
    return send_from_directory(HERE, "index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    body = request.get_json(force=True) or {}
    history = body.get("messages", [])

    last_user = ""
    for m in reversed(history):
        if m.get("role") == "user":
            last_user = m.get("content", "")
            break

    messages = [{"role": "system", "content": build_system_prompt(last_user)}]
    messages.extend(history)

    payload = json.dumps({
        "model": MODEL,
        "messages": messages,
        "stream": True,
        "options": {"temperature": 0.6, "top_p": 0.9, "num_ctx": 8192},
    }).encode("utf-8")

    def generate():
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                for line in resp:
                    line = line.strip()
                    if not line:
                        continue
                    chunk = json.loads(line)
                    token = (chunk.get("message") or {}).get("content", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        break
        except Exception as ex:
            yield f"\n\n[Error talking to the model: {ex}]"

    return Response(generate(), mimetype="text/plain; charset=utf-8")


@app.route("/api/dashboard")
def dashboard_data():
    """Structured live data + auto-computed insights for the dashboard UI."""
    from datetime import datetime, timezone

    def safe(fn, default):
        try:
            return fn()
        except Exception:
            return default

    standings = safe(lambda: epl_data.get_standings(), [])
    scorers = safe(lambda: epl_data.get_top_scorers(), [])
    results = safe(lambda: epl_data.get_recent_results_structured(), [])
    fixtures = safe(lambda: epl_data.get_upcoming_fixtures_structured(), [])

    return {
        "season": epl_data.current_season(),
        "fetched": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "standings": standings,
        "scorers": scorers,
        "results": results,
        "fixtures": fixtures,
        "insights": insights.build_insights(standings, scorers, results),
    }


@app.route("/api/refresh", methods=["POST"])
def refresh():
    """Drop cached API data so the next answer uses freshly fetched stats."""
    epl_data.clear_cache()
    from datetime import datetime, timezone
    return {
        "ok": True,
        "refreshed": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
    }


@app.route("/api/health")
def health():
    return {"ok": True, "model": MODEL, "season": epl_data.current_season()}


if __name__ == "__main__":
    print(f"  EPL Chatbot running at http://localhost:5050  (model: {MODEL})")
    app.run(host="127.0.0.1", port=5050, threaded=True)
