# Gaffer — EPL Insights Dashboard ⚽

[![CI](https://github.com/amhanesipeace/epl-chatbot/actions/workflows/ci.yml/badge.svg)](https://github.com/amhanesipeace/epl-chatbot/actions/workflows/ci.yml)

A live English Premier League **dashboard** that pulls standings, top scorers,
results and fixtures from public sport APIs and **automatically surfaces
insights** — turning raw data into story-ready headlines (title race, form,
Golden Boot, biggest wins). A local-LLM chat assistant ("Ask Gaffer") is built
in as a side panel.

Created by Peace Amhanesi.

- 📊 **Auto insights** — a rules engine (`insights.py`) reads the live data and
  writes narrative takes: title race, hottest/coldest form, best attack/defence,
  Golden Boot race, statement results, goals-per-game pace.
- 🔴 **Live in-play scores** — a "LIVE NOW" banner shows EPL matches as they
  happen (score + minute), auto-polling every 30s; hidden when nothing is on.
- 📈 **Live dashboard** — league table with colour-coded form, top scorers,
  recent results and upcoming fixtures, all from live APIs.
- 📡 **Data layer** — standings/results/fixtures from [TheSportsDB](https://www.thesportsdb.com);
  top scorers from the official Fantasy Premier League API; cached 5 min.
- 💬 **Ask Gaffer** — local LLM chat (Llama 3.1 via [Ollama](https://ollama.com))
  grounded in the same live data (RAG-style). Optional; the dashboard works without it.
- 🖥️ **Terminal version** — a custom `epl-bot` model via the `Modelfile`.

## How it works

```
                         ┌─>  insights.py  ──>  narrative insights ("stories")
Browser (dashboard.html) │
        │                └─>  epl_data.py  ──>  TheSportsDB + FPL API (live data)
        │  GET /api/dashboard  ──>  Flask (app.py)  ──┘
        │
        └─ POST /api/chat  ──>  Flask  ──>  Ollama (llama3.1:8b), grounded in the live data
```

- **Dashboard** (`/`): the page calls `GET /api/dashboard`, which fetches live
  standings, top scorers, results and fixtures (`epl_data.py`, cached 5 min),
  runs the raw numbers through `insights.py`, and returns structured JSON. The
  page renders the table, leaderboards, and the auto-insight cards.
- **Chat** (`/chat`, or the side panel): each message is answered by a local LLM
  with the same live data injected as a "LIVE DATA" block, so answers stay
  current even though the model's training data is older.

The insight layer is deliberately pure/O(n) and network-free (`insights.py`),
so it is fast and easy to unit-test.

## Testing

The insights engine is fully unit-tested (no network needed):

```bash
pip install -r requirements-dev.txt
pytest
```

26 tests cover every insight generator — both when it should fire and when it
should stay quiet — plus the helpers, the `build_insights` integration, and the
live-score parser (with the network call stubbed). CI runs them on every push
(see the badge above).

## Requirements

- macOS / Linux with [Ollama](https://ollama.com) installed and running
- The model pulled: `ollama pull llama3.1:8b`
- Python 3.9+ and Flask (`pip install -r requirements.txt`)

## Run the web app

```bash
cd ~/epl-chatbot
pip install -r requirements.txt      # first time only
./run.sh                             # or: python3 app.py
```

Then open **http://localhost:5050** for the dashboard (the chat panel is on the
same page; a full-screen chat lives at `/chat`). Try asking Gaffer:

- "Show me the current table"
- "Who's top of the league right now?"
- "What were the latest results?"
- "When does Arsenal play next?"

## Terminal version (optional)

A custom Ollama model with the same personality (no live data) is defined in
`Modelfile`:

```bash
ollama create epl-bot -f Modelfile
ollama run epl-bot
```

## Always-on deployment (macOS)

Run the app + a public Cloudflare tunnel automatically at login, kept alive
across crashes and reboots, using `launchd`:

```bash
cd ~/epl-chatbot
deploy/install.sh        # registers the two LaunchAgents
./show-url.sh            # prints the current public https URL
```

This launches:

- **`com.epl.chatbot`** — the Flask app on `localhost:5050`
- **`com.epl.tunnel`** — `cloudflared` exposing it to the internet

Both have `KeepAlive` set, so macOS restarts them if they crash and relaunches
them every time you log in. The app and model stay **on your Mac** — Cloudflare
only forwards traffic — so the public link is live whenever your Mac is awake.

Useful commands:

```bash
./show-url.sh                              # current public URL
launchctl list | grep epl                  # are the agents running?
tail -f logs/app.log logs/tunnel.log       # live logs
deploy/uninstall.sh                        # stop & remove auto-start
```

> **Note:** the free "quick tunnel" URL changes on each restart. For a
> permanent custom address, use a named Cloudflare tunnel (free Cloudflare
> account + a domain). The `.plist` files use absolute paths for this machine;
> adjust them if you move the project or run as a different user.
>
> Requires the **Ollama app** to be running (set it to "Open at Login" so the
> model is available after a reboot).

## Configuration

Environment variables (optional):

| Var          | Default                  | Purpose                       |
| ------------ | ------------------------ | ----------------------------- |
| `EPL_MODEL`  | `llama3.1:8b`            | Ollama model to use           |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server address         |

## Files

| File             | Purpose                                            |
| ---------------- | -------------------------------------------------- |
| `app.py`         | Flask server — chat API + serves the UI            |
| `epl_data.py`    | Fetches & formats live EPL data from TheSportsDB   |
| `index.html`     | Streaming chat web UI                              |
| `Modelfile`      | Terminal-only custom Ollama model (`epl-bot`)      |
| `run.sh`         | Convenience launcher                               |

## Notes

- Live data comes from TheSportsDB's free public API (no key required).
- The model runs locally, so the first reply after startup may take a moment
  while it loads into memory.
