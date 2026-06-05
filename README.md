# Gaffer — EPL Chatbot ⚽

A friendly English Premier League chatbot that runs **fully locally** on
[Ollama](https://ollama.com) (Meta's **Llama 3.1 8B**) and answers with
**live, up-to-date data** — current standings, latest results, and upcoming
fixtures — fetched from [TheSportsDB](https://www.thesportsdb.com).

Created by Peace Amhanesi.

- 🧠 **Local LLM** — Llama 3.1 via Ollama, no cloud, no API bills.
- 📡 **Live data** — standings/results/fixtures injected into each answer (RAG-style).
- 💬 **Web chat UI** — clean streaming chat in your browser.
- 🖥️ **Terminal version** — a custom `epl-bot` model via the `Modelfile`.

## How it works

```
Browser chat  ──>  Flask (app.py)  ──>  Ollama  (llama3.1:8b)
                        │
                        └──>  epl_data.py  ──>  TheSportsDB (live standings/results/fixtures)
```

On every message, `app.py` fetches a fresh snapshot of the league (cached 5 min),
prepends it to the system prompt as a "LIVE DATA" block, then streams the model's
reply token-by-token to the page. Because the live table is the source of truth,
the bot answers current questions correctly even though the model's own training
data is older.

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

Then open **http://localhost:5050** and start chatting. Try:

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
