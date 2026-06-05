#!/usr/bin/env bash
# Stop and remove the EPL chatbot auto-start LaunchAgents (macOS).
AGENTS="$HOME/Library/LaunchAgents"

for label in com.epl.chatbot com.epl.tunnel; do
  launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
  rm -f "$AGENTS/$label.plist"
done

echo "Removed. The app + tunnel will no longer start automatically."
echo "(Any currently running copies were stopped.)"
