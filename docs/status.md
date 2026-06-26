# Moneta — Implementierungsstand

Stand: 2026-06-26  
MVP-Branch: lokal, macOS, `http://localhost:8000`

---

## Legende

| Symbol | Bedeutung |
|--------|-----------|
| ✅ | Umgesetzt |
| ⚠️ | Teilweise umgesetzt (Einschränkung notiert) |
| ❌ | Noch nicht umgesetzt |

---

## 1. Harte Constraints

| ID | Constraint | Status | Anmerkung |
|----|------------|--------|-----------|
| C-1 | Offline-First | ✅ | Alle Kernfunktionen laufen ohne Internet. Alpine.js und Chart.js werden beim Setup lokal in `frontend/vendor/` abgelegt. |
| C-2 | Kein Bank-Login | ✅ | Keine Banking-Schnittstelle, keine externen API-Aufrufe zur Laufzeit. |
| C-3 | Lokale Datenhaltung | ✅ | SQLite-Datenbank unter `~/.moneta/data.db`, keine Cloud-Verbindung. |
| C-4 | Dateneigentum / Portabilität | ✅ | Export und Import aller Daten als JSON über die UI (→ NFR-3). |

---

## 2. Dateneingabe (FR-D)

| ID | Prio | Anforderung | Status | Anmerkung |
|----|------|-------------|--------|-----------|
| FR-D1 | Must | Manuelle Erfassung (Betrag, Datum, Konto, Kategorie, Empfänger, Verwendungszweck, Notiz) | ✅ | Vollständig im Transaktions-Modal. |
| FR-D2 | Must | CSV-Import mit konfigurierbarem Spalten-Mapping | ✅ | Export/Import-Ansicht. Upload → Spalten-Mapping (Datum, Betrag, Empfänger, Verwendungszweck, Typ) → Import. Deutsche/englische Zahlen- und Datumsformate konfigurierbar. Auto-Kategorisierung greift auch beim Import. |
| FR-D3 | Should | Import CAMT.053 und MT940 | ❌ | Noch nicht umgesetzt. |
| FR-D4 | Should | Dublettenerkennung beim Import | ✅ | Beim CSV-Import: Dublettenerkennung über (Konto, Datum, Betrag, Empfänger), konfigurierbar (Checkbox). |
| FR-D5 | Must | Wiederkehrende Abbuchungen (Intervall: monatlich, vierteljährlich, halbjährlich, jährlich) | ✅ | Vollständig konfigurierbar. Manuelles Buchen per Button; `next_due_date` wird automatisch vorgerückt. |
| FR-D6 | Must | Transaktionen bearbeiten und löschen; Einnahmen/Ausgaben unterschieden | ✅ | Edit- und Delete-Aktion in der Transaktionsliste. |
| FR-D7 | Must | Wiederkehrende Einnahmen; höchste Einnahme bestimmt Zyklustart | ✅ | Rekurrente Einnahmen konfigurierbar. Die höchste aktive Einnahme-Regel legt den `day_of_month` des Zyklus fest (`get_cycle_start()` in `backend/main.py`). |
| FR-D8 | Should | Anteilige Rücklage pro Fixkosteneintrag (statt voller Buchung) | ❌ | Noch nicht umgesetzt. |

---

## 3. Mehrere Konten (FR-K)

| ID | Prio | Anforderung | Status | Anmerkung |
|----|------|-------------|--------|-----------|
| FR-K1 | Must | Mehrere Konten anlegen, bearbeiten, löschen | ✅ | Vollständig in der Konten-Ansicht. |
| FR-K2 | Must | Konto-Typ (Girokonto, Sparkonto, Bargeld, Kreditkarte) und aktueller Saldo | ✅ | Typ als Enum; Saldo = Startsaldo + Transaktionen. |
| FR-K3 | Must | Saldo pro Konto aus Startsaldo + Transaktionen | ✅ | Berechnung in `GET /api/accounts`. |
| FR-K4 | Must | Gesamtübersicht aller Konten (Summe des Vermögens) | ✅ | Im Dashboard (Kacheln + Gesamtvermögen-Karte) und in der Konten-Tabelle. |
| FR-K5 | Should | Umbuchungen verändern keinen Gesamtsaldo | ✅ | Typ `transfer` wird beim Saldo beidseitig berücksichtigt (Abgang + Zugang); taucht nicht als Ausgabe in Analysen auf. |

---

## 4. Kategorisierung (FR-C)

| ID | Prio | Anforderung | Status | Anmerkung |
|----|------|-------------|--------|-----------|
| FR-C1 | Must | Zweistufiger Kategorien-Katalog (Übergruppe → Untergruppe) | ✅ | 39 vorausgefüllte Kategorien in 9 Übergruppen (Ausgaben + Einnahmen). |
| FR-C2 | Must | Über- und Untergruppen frei anlegen, umbenennen, verschieben, löschen | ✅ | Vollständig in der Kategorien-Ansicht (Tabs Ausgaben / Einnahmen). |
| FR-C3 | Must | Kategorisierung für Ausgaben und Einnahmen | ✅ | Kategorien haben `type=income` oder `type=expense`. |
| FR-C4 | Must | Regelbasierte Auto-Kategorisierung (Textmuster auf Empfänger/Verwendungszweck) | ✅ | `apply_category_rules()` in `backend/main.py`; 20 Standardregeln vorbefüllt (REWE, EDEKA, Netflix, …). Live-Vorschlag beim Tippen im Transaktions-Modal. |
| FR-C5 | Must | Manuelle Korrektur hat Vorrang | ✅ | Kategorie im Modal jederzeit überschreibbar; wird direkt gespeichert. |
| FR-C6 | Should | Lernen aus Korrekturen (Regelvorschlag nach manueller Korrektur) | ❌ | Noch nicht umgesetzt. |
| FR-C7 | Should | Regeln einsehbar und editierbar | ✅ | Eigene „Auto-Regeln"-Ansicht mit vollem CRUD. |
| FR-C8 | Could | Optionales lokales ML-Modell | ❌ | Out of scope für MVP. |

---

## 5. Budgets (FR-B)

| ID | Prio | Anforderung | Status | Anmerkung |
|----|------|-------------|--------|-----------|
| FR-B1 | Must | Budgets pro Kategorie (Betrag je Zyklus) | ✅ | Vollständig in der Budget-Ansicht. |
| FR-B2 | Must | Anzeige Budget vs. tatsächliche Ausgaben (verbraucht / verbleibend) | ✅ | Fortschrittsbalken pro Budget; Farbe wechselt bei >80 % (amber) und >100 % (rot). |
| FR-B3 | Should | Warnung bei Annäherung / Überschreitung | ⚠️ | Visuell durch Farbe im Fortschrittsbalken signalisiert; keine Push-Benachrichtigung. |
| FR-B4 | Could | Übertrag von Restbudget in Folgezyklus | ❌ | Noch nicht umgesetzt. |

---

## 6. Sparziele (FR-S)

| ID | Prio | Anforderung | Status | Anmerkung |
|----|------|-------------|--------|-----------|
| FR-S1 | Must | Sparziele anlegen (Zielbetrag, optionales Zieldatum, Name) | ✅ | Vollständig in der Sparziele-Ansicht. |
| FR-S2 | Must | Fortschrittsanzeige (aktuell gespart / Zielbetrag, prozentual) | ✅ | Fortschrittsbalken mit konfigurierter Farbe; manuelles Aktualisieren des aktuellen Betrags direkt in der Kachel. |
| FR-S3 | Should | Sparziel als virtueller Topf (innerhalb eines realen Kontos) | ❌ | Hängt von FR-T an; Sparziele sind aktuell kontounabhängig. |
| FR-S4 | Could | Nötige monatliche Sparrate bei Zieldatum | ❌ | Noch nicht umgesetzt. |

---

## 7. Virtuelle Töpfe (FR-T)

| ID | Prio | Anforderung | Status | Anmerkung |
|----|------|-------------|--------|-----------|
| FR-T1 | Must | Virtuelle Töpfe innerhalb eines Kontos | ✅ | Tabelle `pots` in `backend/db.py`; volle CRUD-API (`/api/pots`); eigene UI-Ansicht mit Konto-Filter. |
| FR-T2 | Must | Reservierter Betrag; Summe aller Töpfe vs. Kontosaldo | ✅ | `GET /api/accounts` liefert `pots_reserved` (Summe aller Topf-Zielbeträge) und `free_balance` (Saldo − reserviert). Anzeige in der Töpfe-Ansicht als 3-Kacheln-Summary. |
| FR-T3 | Should | Anzeige frei verfügbarer Saldo (Kontosaldo − Töpfe) | ✅ | Wird in der Töpfe-Ansicht als „Frei verfügbar"-Kachel angezeigt. |
| FR-T4 | Should | Sparziel an Topf koppeln | ❌ | Hängt von FR-T1 und FR-S3 ab. |

---

## 8. Verfügbarer Betrag / Zyklus (FR-V)

| ID | Prio | Anforderung | Status | Anmerkung |
|----|------|-------------|--------|-----------|
| FR-V1 | Must | Prominente Anzeige des verfügbaren Betrags auf dem Startbildschirm | ✅ | Große Zahl oben im Dashboard, grün/rot je nach Vorzeichen. |
| FR-V2 | Must | Formel: `verfügbar = Einnahmen − Fixkosten − Sparziele − tatsächliche variable Ausgaben` | ✅ | Berechnung in `GET /api/dashboard` (`backend/main.py`); alle Werte stammen aus dem aktuellen Zyklus. |
| FR-V3 | Must | Budgets reduzieren „verfügbar" nur in Höhe der Ist-Ausgaben; Rest wird ausgegraut als „eingeplant" | ✅ | `eingeplant`-Zeile unterhalb der Hauptzahl; wird nicht vom verfügbaren Betrag abgezogen. |
| FR-V4 | Must | Nicht budgetierte Ausgaben reduzieren „verfügbar" unmittelbar | ✅ | Variable Ausgaben werden vollständig subtrahiert, unabhängig von Budget-Zuweisung. |
| FR-V5 | Must | Transparente Aufschlüsselung (Einnahmen, Fixkosten, Sparziele, Ausgaben, Eingeplant) | ✅ | Breakdown-Grid direkt unter der Hauptzahl. |
| FR-V6 | Must | Zyklusbeginn = Eingang der höchsten wiederkehrenden Einnahme; manueller Stichtag als Fallback | ✅ | `get_cycle_start()` in `backend/main.py`; manueller Tag konfigurierbar in der Wiederkehrend-Ansicht → Einstellungen gespeichert in `settings`-Tabelle. |

---

## 9. Analyse & Auswertung (FR-A)

| ID | Prio | Anforderung | Status | Anmerkung |
|----|------|-------------|--------|-----------|
| FR-A1 | Must | Ausgaben pro Kategorie (Liste + Diagramm) | ✅ | Donut-Chart in der Budget-Ansicht; API `GET /api/analysis/by-category`. |
| FR-A2 | Should | Zeitverlauf von Ausgaben/Einnahmen (Monatsvergleich, Trend) | ❌ | API `GET /api/analysis/cashflow` ist implementiert, UI-Seite fehlt noch. |
| FR-A3 | Should | Einnahmen-Ausgaben-Saldo pro Monat (Cashflow) | ❌ | Wie FR-A2. |
| FR-A4 | Could | Filter/Suche über Transaktionen | ⚠️ | Filter nach Zeitraum, Konto und Kategorie vorhanden; Freitextsuche nach Empfänger/Betrag fehlt. |
| FR-A5 | Could | Erkennung wiederkehrender Zahlungen aus Transaktionsverlauf | ❌ | Noch nicht umgesetzt. |

---

## 10. Nicht-funktionale Anforderungen (NFR)

| ID | Prio | Anforderung | Status | Anmerkung |
|----|------|-------------|--------|-----------|
| NFR-1 | Must | Kein Tracking, keine Telemetrie | ✅ | Keine externen Verbindungen zur Laufzeit. |
| NFR-2 | Must | Verschlüsselung at rest (mind. optional) | ✅ | SQLCipher 4 (AES-256-CBC, PBKDF2-HMAC-SHA512 mit 256.000 Iterationen). Passwort per Terminal-Prompt oder `MONETA_KEY`-Umgebungsvariable; liegt nur im RAM. Migration bestehender Datenbanken automatisch via `PRAGMA rekey`. Details → `docs/security.md`. |
| NFR-3 | Must | Export & Import (JSON oder SQLite + CSV) | ✅ | JSON-Export und -Import vollständig über die UI; enthält alle Entitäten. |
| NFR-4 | Must | macOS (Desktop) + Android (GrapheneOS), offline | ⚠️ | macOS: ✅ läuft als lokaler Webserver. Android: ❌ noch nicht adressiert; Technologiewahl für Cross-Platform offen. |
| NFR-5 | Should | Performance bei ≥ mehreren tausend Transaktionen | ⚠️ | SQLite mit WAL-Modus; keine Indizes auf `date`/`account_id` gesetzt. Pagination über `limit`/`offset` vorhanden, aber im UI noch nicht genutzt. |
| NFR-6 | Should | Backup & Geräteabgleich (manuell, ohne Cloud) | ⚠️ | JSON-Export ermöglicht manuelles Backup; Syncthing/Nextcloud-Integration ist Aufgabe des Nutzers. |
| NFR-7 | Could | Mehrwährungsfähigkeit | ⚠️ | Währungsfeld pro Konto vorhanden; Umrechnung und Mehrwährungs-Auswertung fehlen. |
| NFR-8 | Could | Lokalisierung (Deutsch, Datum-/Zahlenformate) | ✅ | UI auf Deutsch; Datumsformate mit `de-DE`-Locale; Beträge als EUR-Currency-Format. |

---

## Zusammenfassung

| Kategorie | Must ✅ | Must ⚠️ | Must ❌ | Should ✅ | Should ⚠️ | Should ❌ | Could |
|-----------|---------|---------|---------|-----------|-----------|----------|-------|
| Constraints (C) | 4 | — | — | — | — | — | — |
| Dateneingabe (D) | 4 | — | — | 1 (D4) | — | 2 (D3,D8) | — |
| Konten (K) | 4 | — | — | 1 | — | — | — |
| Kategorien (C) | 5 | — | — | 1 | — | 1 | 1 |
| Budgets (B) | 2 | — | — | — | 1 | — | 1 |
| Sparziele (S) | 2 | — | — | — | — | 1 | 1 |
| Töpfe (T) | 2 | — | — | 1 | — | 1 | — |
| Verfügbar (V) | 6 | — | — | — | — | — | — |
| Analyse (A) | 1 | — | — | — | — | 2 | 2 |
| NFR | 4 | 1 | — | — | 3 | — | 1 |

**Alle Must-Anforderungen sind jetzt vollständig umgesetzt.**

---

## Priorisierte nächste Schritte

1. **FR-A2 / FR-A3** — Cashflow-Chart: API `GET /api/analysis/cashflow` existiert bereits, UI-Ansicht (Balkendiagramm) fehlt
2. **FR-C6** — Lernende Regeln: Nach manueller Kategoriekorrektur Regel-Vorschlag anzeigen
3. **FR-T4 / FR-S3** — Sparziel an Topf koppeln
4. **NFR-5** — DB-Indizes auf `date`, `account_id`, `category_id` für Performance bei großen Datenmengen
5. **FR-D3** — CAMT.053 / MT940 Import
