#!/usr/bin/env bash
# Launch the EPL Chatbot web app.
# Requires: Ollama running with the llama3.1:8b model pulled.
set -e
cd "$(dirname "$0")"
echo "Starting Gaffer — EPL Chatbot…"
echo "Open http://localhost:5050 in your browser."
exec python3 app.py
