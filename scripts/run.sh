#!/bin/bash
set -e

# Immer vom Projektstamm aus arbeiten, egal aus welchem Verzeichnis das Skript aufgerufen wird
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ ! -d ".venv" ]; then
  echo "Setup noch nicht ausgeführt. Starte ./scripts/setup.sh zuerst."
  exit 1
fi

echo "🏦 Moneta läuft auf http://localhost:8000"
echo "   Ctrl+C zum Beenden"
echo ""
.venv/bin/python backend/main.py
