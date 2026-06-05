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

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = os.environ.get("EPL_MODEL", "llama3.1:8b")
HERE = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)

PERSONA = """You are "Gaffer", a friendly, knowledgeable English Premier League (EPL) assistant created by Peace Amhanesi.

You answer questions about the Premier League: clubs, players, managers, stadiums, history, rules, tactics, standings, results, and fixtures. Use a warm, enthusiastic football-fan tone, be accurate and concise, and add a quick interesting fact when it fits.

You are given a LIVE DATA snapshot below with the current season's standings, recent results, and upcoming fixtures. Treat this snapshot as the source of truth for anything current (table positions, points, latest scores, who plays next). Quote it when relevant. If a question asks for something not in the snapshot and outside your training knowledge, say so honestly rather than guessing. Politely steer off-topic questions back to football."""


def build_system_prompt():
    """Persona + a fresh live-data block."""
    try:
        live = epl_data.build_context_block()
    except Exception as ex:
        live = f"(Live data temporarily unavailable: {ex})"
    return f"{PERSONA}\n\n----- LIVE DATA -----\n{live}\n----- END LIVE DATA -----"


@app.route("/")
def index():
    return send_from_directory(HERE, "index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    body = request.get_json(force=True) or {}
    history = body.get("messages", [])

    messages = [{"role": "system", "content": build_system_prompt()}]
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


@app.route("/api/health")
def health():
    return {"ok": True, "model": MODEL, "season": epl_data.current_season()}


if __name__ == "__main__":
    print(f"  EPL Chatbot running at http://localhost:5050  (model: {MODEL})")
    app.run(host="127.0.0.1", port=5050, threaded=True)
