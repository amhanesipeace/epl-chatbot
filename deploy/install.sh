#!/usr/bin/env bash
# Install the EPL chatbot auto-start LaunchAgents (macOS).
# Starts the Flask app + Cloudflare tunnel at login and keeps them alive.
set -e
AGENTS="$HOME/Library/LaunchAgents"
HERE="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$AGENTS"
cp "$HERE/com.epl.chatbot.plist" "$HERE/com.epl.tunnel.plist" "$AGENTS/"

for label in com.epl.chatbot com.epl.tunnel; do
  launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$AGENTS/$label.plist"
done

echo "Installed. The app + tunnel will now start automatically at login."
echo "Find your public URL with:  ./show-url.sh"
