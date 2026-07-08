#!/bin/bash
set -e

# Immer vom Projektstamm aus arbeiten, egal aus welchem Verzeichnis das Skript aufgerufen wird
cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "🏦 Moneta — Setup"
echo "================="

# SQLCipher (Datenbank-Verschlüsselung, NFR-2)
if ! command -v brew &>/dev/null; then
  echo "⚠️  Homebrew nicht gefunden — SQLCipher-Verschlüsselung wird übersprungen."
  echo "   Für Verschlüsselung: https://brew.sh installieren, dann ./scripts/setup.sh erneut ausführen."
else
  if ! brew list sqlcipher &>/dev/null; then
    echo "→ Installiere SQLCipher (Datenbank-Verschlüsselung) …"
    brew install sqlcipher
  else
    echo "→ SQLCipher bereits installiert."
  fi
fi

# Python virtualenv
if [ ! -d ".venv" ]; then
  echo "→ Erstelle virtuelle Python-Umgebung …"
  python -m venv .venv
fi

echo "→ Installiere Python-Abhängigkeiten …"
.venv/bin/pip install -q -r requirements.txt

# JS-Vendor-Dateien einmalig herunterladen (lokal gespeichert, kein CDN zur Laufzeit)
VENDOR="frontend/vendor"
mkdir -p "$VENDOR"

if [ ! -f "$VENDOR/alpine.min.js" ]; then
  echo "→ Lade Alpine.js …"
  curl -sL "https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js" -o "$VENDOR/alpine.min.js"
fi

if [ ! -f "$VENDOR/chart.min.js" ]; then
  echo "→ Lade Chart.js …"
  curl -sL "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js" -o "$VENDOR/chart.min.js"
fi

echo ""
echo "✅ Setup abgeschlossen! Starte die App mit:"
echo "   ./scripts/run.sh"
