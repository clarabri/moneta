#!/bin/bash
set -e

if [ ! -d ".venv" ]; then
  echo "Setup noch nicht ausgeführt. Starte ./setup.sh zuerst."
  exit 1
fi

echo "🏦 Moneta läuft auf http://localhost:8000"
echo "   Ctrl+C zum Beenden"
echo ""
.venv/bin/python main.py
