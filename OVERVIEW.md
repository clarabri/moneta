# Moneta — Projektübersicht & Aufbau

## Verzeichnisstruktur

```
moneta/
├── backend/             # Python-Backend: API-Server und Datenbankschicht
│   ├── main.py          # FastAPI-App: alle Routen, Geschäftslogik, Einstiegspunkt
│   └── db.py            # Datenbankschicht: Verbindung, Schema, Seed-Kategorien, Verschlüsselung
├── frontend/            # Browser-Frontend: statische Dateien, kein Build-Schritt nötig
│   ├── index.html       # Single-Page-App (Alpine.js, alle Ansichten als x-show-Blöcke)
│   ├── style.css        # Alle Stile
│   ├── app.js           # Alpine.js-Datenzustand, API-Aufrufe, Chart-Konfiguration
│   └── vendor/          # Lokal gespeicherte JS-Bibliotheken (kein CDN zur Laufzeit)
│       ├── alpine.min.js
│       └── chart.min.js
├── scripts/             # Shell-Skripte für Betrieb und Setup
│   ├── setup.sh         # Erstinstallation: SQLCipher, Python-venv, JS-Bibliotheken
│   └── run.sh           # App starten (wechselt automatisch in den Projektstamm)
├── docs/                # Projektdokumentation
│   ├── requirements.md  # Anforderungen (funktional + nicht-funktional)
│   ├── status.md        # Aktueller Implementierungsstand je Anforderung
│   └── security.md      # Sicherheitskonzept: SQLCipher-Verschlüsselung (NFR-2)
├── requirements.txt     # Python-Abhängigkeiten (FastAPI, uvicorn, sqlcipher3)
├── .gitignore
├── README.md            # Benutzerdokumentation: Installation, Start, Features
└── OVERVIEW.md          # Diese Datei: Entwicklerübersicht
```

## Wie die App funktioniert

Moneta ist eine lokale Web-App ohne Cloud-Verbindung. Der Ablauf beim Start:

1. `./scripts/run.sh` startet `backend/main.py` mit dem lokalen Python-Interpreter.
2. `backend/main.py` startet einen FastAPI/uvicorn-Server auf `127.0.0.1:8000` — ausschließlich lokal erreichbar.
3. Der Server öffnet automatisch den Browser unter `http://localhost:8000`.
4. Die Route `GET /` liefert `frontend/index.html` direkt als Datei (`FileResponse`).
5. Alle weiteren statischen Dateien (`style.css`, `app.js`, Vendor-Bibliotheken) werden über den Mount `/static → frontend/` ausgeliefert.
6. Die App im Browser kommuniziert ausschließlich mit `localhost`-API-Endpunkten (`/api/...`).

## Datenhaltung

| Was | Wo |
|-----|----|
| Datenbank | `~/.moneta/data.db` (SQLite, außerhalb des Projektordners) |
| Passwort (optional) | Nur im RAM, nie auf der Festplatte |
| Netzwerkverbindungen | Keine — nur `127.0.0.1:8000` zum eigenen Rechner |

Die Datenbank wird beim ersten Start automatisch angelegt und mit Standard-Kategorien befüllt (`backend/db.py: init_db()`). Optionale AES-256-Verschlüsselung via SQLCipher — Details in `docs/security.md`.

## Technologie-Stack

| Schicht | Technologie |
|---------|-------------|
| Backend | Python 3.11+, FastAPI, uvicorn |
| Datenbank | SQLite (plain) oder SQLCipher (AES-256, optional) |
| Frontend | Alpine.js (Reaktivität), Chart.js (Diagramme) |
| Kein Build-Schritt | Kein npm, kein Webpack, kein Transpiler |

## Wichtige Dateien auf einen Blick

| Datei | Inhalt |
|-------|--------|
| `backend/main.py` | Alle API-Routen: Konten, Transaktionen, Kategorien, Budgets, Sparziele, Töpfe, CSV-Import, JSON-Export/Import, Dashboard, Analyse |
| `backend/db.py` | DB-Verbindung, PRAGMA-Konfiguration, Schema (`CREATE TABLE`), Seed-Kategorien (39 Stück), Seed-Regeln (20 Stück), Verschlüsselungslogik |
| `frontend/app.js` | Alpine.js-Komponente mit allen Datenzuständen, API-Aufrufen und Chart-Konfigurationen |
| `frontend/index.html` | HTML-Struktur der SPA; jede Ansicht (Dashboard, Transaktionen, Budgets …) ist ein `x-show`-Block |
| `scripts/setup.sh` | Installiert SQLCipher (Homebrew), legt Python-venv an, lädt JS-Bibliotheken lokal |
| `scripts/run.sh` | Prüft venv, startet `backend/main.py` immer vom Projektstamm aus |
