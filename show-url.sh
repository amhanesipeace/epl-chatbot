#!/usr/bin/env bash
# Print the current public Cloudflare tunnel URL for the EPL chatbot.
LOG="$(dirname "$0")/logs/tunnel.log"
URL=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" "$LOG" 2>/dev/null | tail -1)
if [ -n "$URL" ]; then
  echo "Gaffer is live at: $URL"
else
  echo "No public URL yet — is the tunnel running? Check: launchctl list | grep epl"
fi
