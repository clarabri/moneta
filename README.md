# Moneta

Persönliche Finanzverwaltung — lokal, offline, ohne Cloud.

> **In Progress** — Kernfunktionen sind lauffähig, einige Features fehlen noch (siehe unten).

---

## Was ist das?

Moneta ist eine lokale Web-App zur Verwaltung von Konten, Transaktionen, Budgets und Sparzielen. Sie läuft als kleiner Server auf dem eigenen Gerät und ist im Browser erreichbar. Es gibt keine Anmeldung, keine Cloud-Verbindung, keine Telemetrie — alle Daten bleiben auf dem eigenen Rechner.

## Features

- **Mehrere Konten** — Girokonto, Sparkonto, Bargeld, Kreditkarte
- **Transaktionen** — manuell erfassen, bearbeiten, löschen; Einnahmen / Ausgaben / Umbuchungen
- **CSV-Import** — Bankexporte importieren mit konfigurierbarem Spalten-Mapping
- **Kategorien** — zweistufiger Katalog (Übergruppe → Untergruppe), frei anpassbar
- **Auto-Kategorisierung** — Regeln ordnen Transaktionen automatisch zu (Empfänger/Verwendungszweck)
- **Wiederkehrende Einträge** — monatlich, vierteljährlich, halbjährlich, jährlich
- **Budgets** — pro Kategorie, mit Fortschrittsanzeige
- **Sparziele** — Zielbetrag, Zieldatum, monatliche Sparrate
- **Virtuelle Töpfe** — reservieren einen Teil des Kontosaldos für einen bestimmten Zweck
- **Dashboard** — verfügbarer Betrag im aktuellen Zyklus auf einen Blick
- **Export / Import** — alle Daten als JSON, für Backups und Gerätewechsel
- **Verschlüsselung** — Datenbank optional per Passwort verschlüsselt (SQLCipher / AES-256)

## Voraussetzungen

- macOS
- Python 3.11+
- [Homebrew](https://brew.sh)

## Installation

```bash
git clone <repo-url>
cd moneta
./scripts/setup.sh
```

Das Skript installiert SQLCipher (via Homebrew), legt eine virtuelle Python-Umgebung an und lädt alle Abhängigkeiten.

## Starten

```bash
./scripts/run.sh
```

Die App öffnet sich automatisch unter `http://localhost:8000`. Mit `Ctrl+C` beenden.

Beim ersten Start wird nach einem **Datenbankpasswort** gefragt. Ein leeres Passwort deaktiviert die Verschlüsselung. Wer das Passwort nicht jedes Mal eintippen möchte:

```bash
MONETA_KEY="meinPasswort" ./scripts/run.sh
```

## Daten

Die Datenbank liegt unter `~/.moneta/data.db`. Bei aktivierter Verschlüsselung ist sie mit AES-256 gesichert — Details in [`docs/security.md`](docs/security.md).

## Status

Das Projekt ist funktionsfähig, aber noch nicht fertig. Was noch fehlt:

| Feature | Beschreibung |
|---------|-------------|
| Cashflow-Chart | API ist vorhanden, UI-Ansicht fehlt noch |
| CAMT.053 / MT940 Import | Bankformat-Import (nur CSV ist bisher implementiert) |
| Lernende Kategorisierung | Regelvorschlag nach manueller Korrektur |
| Virtuelle Töpfe → Sparziele | Töpfe und Sparziele verknüpfen |
| Android | App läuft bisher nur auf macOS |

Vollständiger Stand: [`docs/status.md`](docs/status.md)

## Technologie

| Komponente | Technologie |
|------------|-------------|
| Backend | Python, FastAPI, SQLite / SQLCipher |
| Frontend | Alpine.js, Chart.js (beide lokal, kein CDN zur Laufzeit) |
| Datenbank | SQLite mit optionaler SQLCipher-Verschlüsselung |
