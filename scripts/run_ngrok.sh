#!/usr/bin/env bash
# Expose the app (on port 4040) via ngrok using project config.
# Prereq: run once — ngrok config add-authtoken YOUR_TOKEN
# App should be running on 4040 before starting this.
set -e
cd "$(dirname "$0")/.."
CONFIG="tools/ngrok.yml"
if [ -f "$CONFIG" ]; then
  exec ngrok http 4040 --config "$CONFIG"
else
  exec ngrok http 4040
fi
