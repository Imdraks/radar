#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "${RADAR_CODESPACES_SANDBOX:-}" != "1" ]]; then
  echo "Cette installation est réservée au conteneur de test Radar." >&2
  exit 1
fi
python -m venv .devcontainer/.local/venv
.devcontainer/.local/venv/bin/python -m pip install -r backend/requirements.txt
npm --prefix frontend ci --no-audit --no-fund
.devcontainer/.local/venv/bin/python .devcontainer/radar.py init
echo "Installation terminée. Identifiants : python .devcontainer/radar.py credentials"
