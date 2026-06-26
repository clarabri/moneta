#!/bin/bash
set -e

echo "🏦 Moneta — Setup"
echo "================="

# SQLCipher (Datenbank-Verschlüsselung, NFR-2)
if ! command -v brew &>/dev/null; then
  echo "⚠️  Homebrew nicht gefunden — SQLCipher-Verschlüsselung wird übersprungen."
  echo "   Für Verschlüsselung: https://brew.sh installieren, dann ./setup.sh erneut ausführen."
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
  python3 -m venv .venv
fi

echo "→ Installiere Python-Abhängigkeiten …"
.venv/bin/pip install -q -r requirements.txt

# Download JS vendor files (einmalig)
VENDOR="static/vendor"
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
echo "   ./run.sh"
