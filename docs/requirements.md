# Requirements: Offline-Finanz-Tracker

**Arbeitstitel:** Moneta
**Vorbild:** Finanzguru — aber ohne Cloud, ohne Banking-Schnittstelle
**Stand:** Entwurf

---

## 1. Vision

Eine App zum **Tracken und Analysieren der eigenen Ausgaben**, die vollständig offline läuft und zu keinem Zeitpunkt Bankzugangsdaten oder eine Kontoanbindung benötigt. Alle Daten liegen lokal beim Nutzer; die App ersetzt die Aggregations-/Auswertungsfunktion von Finanzguru, nicht dessen automatischen Kontoabruf.

---

## 2. Rahmenbedingungen (harte Constraints)

Diese gelten für **alle** Anforderungen und sind nicht verhandelbar.

| ID | Constraint |
|----|------------|
| C-1 | **Offline-First.** Sämtliche Kernfunktionen müssen ohne Internetverbindung vollständig nutzbar sein. |
| C-2 | **Kein Bank-Login.** Die App fragt zu keinem Zeitpunkt Online-Banking-Zugangsdaten ab und verbindet sich nicht mit Bank-APIs oder Aggregations-Diensten (kein FinTS/HBCI, kein PSD2/Open-Banking). |
| C-3 | **Lokale Datenhaltung.** Alle Nutzerdaten werden ausschließlich lokal gespeichert. Kein verpflichtender Cloud-Account, keine Telemetrie ohne Opt-in. |
| C-4 | **Dateneigentum.** Der Nutzer kann seine Daten jederzeit vollständig exportieren und importieren (Portabilität, Backup). |

---

## 3. Datenmodell — wie kommen Transaktionen rein?

Da C-2 jeden automatischen Abruf ausschließt, braucht es definierte Eingabewege. Das ist die Grundlage, ohne die der Rest nicht funktioniert.

| ID | Prio | Anforderung |
|----|------|-------------|
| FR-D1 | **Must** | Nutzer können Transaktionen **manuell erfassen** (Betrag, Datum, Konto, Kategorie, Empfänger/Verwendungszweck, optional Notiz). |
| FR-D2 | **Must** | Nutzer können Transaktionen per **Datei-Import** einlesen, ohne Bank-Login — als Datei-Export, die der Nutzer selbst aus seinem Banking exportiert hat. Format-Basis: **CSV** mit konfigurierbarem Spalten-Mapping. |
| FR-D3 | **Should** | Import zusätzlich für die deutschen Standardformate **CAMT.053** und **MT940** (vermeidet das fehleranfällige CSV-Mapping bei vielen Banken). |
| FR-D4 | **Should** | **Dublettenerkennung** beim Import (gleicher Betrag + Datum + Empfänger wird nicht doppelt angelegt). |
| FR-D5 | **Must** | **Wiederkehrende Abbuchungen** (Fixkosten, Abos) konfigurierbar mit Betrag, Empfänger, Kategorie und **Intervall** (monatlich, vierteljährlich, halbjährlich, jährlich). **Standard:** volle Buchung zum Fälligkeitstermin. |
| FR-D6 | **Must** | Transaktionen lassen sich **bearbeiten und löschen**; Einnahmen und Ausgaben werden unterschieden. |
| FR-D7 | **Must** | **Wiederkehrende Einbuchungen** (Einnahmen) konfigurierbar mit Betrag und Intervall (z. B. Gehalt, Stipendium). Die **höchste** wiederkehrende Einnahme gilt als Haupteinnahme und gibt den Zyklustakt vor (FR-V4); alle weiteren Einnahmen erhöhen nur das Einkommen des Zyklus. |
| FR-D8 | **Should** | Pro wiederkehrender Abbuchung **umschaltbar** zwischen *voller Buchung zum Fälligkeitstermin* (Default) und *anteiliger Rücklage* (Betrag wird gleichmäßig über die Zyklen bis zur Fälligkeit in einen Topf reserviert, FR-T1, um „verfügbar" zu glätten). |

---

## 4. Funktionale Anforderungen — deine fünf Kernpunkte

### 4.1 Mehrere Konten

| ID | Prio | Anforderung |
|----|------|-------------|
| FR-K1 | **Must** | Nutzer können **mehrere Konten** anlegen, bearbeiten und löschen. |
| FR-K2 | **Must** | Jedes Konto hat einen **Typ** (z. B. Girokonto, Sparkonto, Bargeld, Kreditkarte) und einen aktuellen Saldo. |
| FR-K3 | **Must** | Der **Saldo pro Konto** ergibt sich aus Startsaldo + zugeordneten Transaktionen und wird angezeigt. |
| FR-K4 | **Must** | Es gibt eine **Gesamtübersicht** über alle Konten (Summe des Vermögens). |
| FR-K5 | **Should** | **Umbuchungen zwischen Konten** verändern keinen Gesamtsaldo und tauchen nicht als Ausgabe in der Analyse auf. |

### 4.2 Kategorisierung (Über- und Untergruppen)

Kategorien gelten für **Ausgaben und Einnahmen** und sind **zweistufig**: Übergruppe → Untergruppe. Ohne Bankanbindung erfolgt die automatische Zuordnung **regelbasiert** auf Basis von Empfänger/Verwendungszweck — kein Cloud-ML nötig.

| ID | Prio | Anforderung |
|----|------|-------------|
| FR-C1 | **Must** | **Zweistufiger Kategorien-Katalog**: Übergruppen (z. B. Fixkosten, Abos, Lifestyle) mit zugehörigen Untergruppen (z. B. Fixkosten → Miete, Strom, Rundfunkbeitrag, Versicherungen; Abos → Zeitung, Streaming, Self-Hosting, VPN; Lifestyle → Abendessen, Theater, Kino). |
| FR-C2 | **Must** | Über- und Untergruppen lassen sich **frei anlegen, umbenennen, verschieben und löschen**. Vorbefüllung mit sinnvollen Defaults, die der Nutzer überschreiben kann. |
| FR-C3 | **Must** | Kategorisierung gilt für **Ausgaben und Einnahmen** gleichermaßen. |
| FR-C4 | **Must** | **Regelbasierte Auto-Kategorisierung**: Textmuster im Empfänger/Verwendungszweck (z. B. „REWE" → Lebensmittel) ordnen eine Unterkategorie zu. |
| FR-C5 | **Must** | **Manuelle Korrektur** jeder Zuordnung ist jederzeit möglich und hat Vorrang. |
| FR-C6 | **Should** | **Lernen aus Korrekturen**: Nach einer Korrektur schlägt die App vor, daraus eine Regel zu erstellen / die passende Regel anzupassen. |
| FR-C7 | **Should** | Regeln sind vom Nutzer **einsehbar und editierbar** (transparente Logik, keine Blackbox). |
| FR-C8 | **Could** | Optional lokales ML-Modell als Ausbaustufe (rein on-device), falls Regeln nicht ausreichen. |

### 4.3 Budgets

| ID | Prio | Anforderung |
|----|------|-------------|
| FR-B1 | **Must** | Nutzer können **Budgets pro Kategorie** festlegen (Betrag je Zyklus, vgl. FR-V4). |
| FR-B2 | **Must** | Anzeige **Budget vs. tatsächliche Ausgaben** je Kategorie für den laufenden Zyklus (verbraucht / verbleibend). |
| FR-B3 | **Should** | **Warnung/Markierung** bei Annäherung an bzw. Überschreitung eines Budgets. |
| FR-B4 | **Could** | **Übertrag** von Restbudget in den Folgezyklus (konfigurierbar pro Budget). |

### 4.4 Sparziele

| ID | Prio | Anforderung |
|----|------|-------------|
| FR-S1 | **Must** | Nutzer können **Sparziele** anlegen (Zielbetrag, optional Zieldatum, Name). |
| FR-S2 | **Must** | **Fortschrittsanzeige** je Ziel (aktuell gespart / Zielbetrag, prozentual). |
| FR-S3 | **Should** | Ein Sparziel ist als **Topf** umsetzbar (siehe FR-T4): reservierter Betrag innerhalb eines realen Kontos statt eigenes Konto. |
| FR-S4 | **Could** | Bei Zieldatum: Anzeige der **nötigen monatlichen Sparrate**, um das Ziel rechtzeitig zu erreichen. |

### 4.6 Virtuelle Töpfe

Töpfe sind virtuelle Unterteilungen eines realen Kontos — das Geld bleibt physisch auf dem Giro- oder Sparkonto, wird aber gedanklich „reserviert".

| ID | Prio | Anforderung |
|----|------|-------------|
| FR-T1 | **Must** | Nutzer können **virtuelle Töpfe innerhalb eines Kontos** anlegen (z. B. „Reisegeld", „Rücklagen") — sowohl im Giro- als auch im Sparkonto. |
| FR-T2 | **Must** | Ein Topf hält einen **reservierten Betrag**; die Summe aller Töpfe eines Kontos wird gegen dessen Saldo geprüft (Überschreitung wird markiert). |
| FR-T3 | **Should** | Anzeige des **frei verfügbaren (nicht reservierten) Saldos** je Konto = Kontosaldo − Summe der Töpfe. |
| FR-T4 | **Should** | Ein **Sparziel kann an einen Topf gekoppelt** werden (Topf = Sparziel mit Zielbetrag/optionalem Zieldatum). |

### 4.5 „So viel Geld habe ich noch zur Verfügung"

Kernkennzahl der App. **Zyklus = Eingang der Haupteinnahme** (höchste wiederkehrende Einnahme, FR-D7); weitere Einnahmen erhöhen das Einkommen des Zyklus, geben aber nicht den Takt vor.

Die Kennzahl basiert auf **tatsächlichen Ausgaben**, nicht auf voller Budget-Allokation: Ein angefangenes Budget reduziert „verfügbar" nur in Höhe des bereits Ausgegebenen; der noch nicht genutzte Budgetrest wird **ausgegraut** als „eingeplant" dargestellt.

| ID | Prio | Anforderung |
|----|------|-------------|
| FR-V1 | **Must** | Anzeige des **verfügbaren Betrags** für den laufenden Zyklus, prominent auf dem Startbildschirm. |
| FR-V2 | **Must** | **Formel:** `verfügbar = Einnahmen − Fixkosten − Sparziele − tatsächliche variable Ausgaben`, alles nur für den aktuellen Zyklus. „Einnahmen" = Summe aller Einnahmen des Zyklus; „variable Ausgaben" = alle getätigten Ausgaben, **budgetiert wie unbudgetiert**. |
| FR-V3 | **Must** | **Budgets reduzieren „verfügbar" nur in Höhe der Ist-Ausgaben.** Der noch nicht genutzte Budgetrest wird separat als **ausgegraut/„eingeplant"** angezeigt (Hinweis auf bereits verplantes Geld), aber nicht vom verfügbaren Betrag abgezogen. |
| FR-V4 | **Must** | **Nicht budgetierte Ausgaben reduzieren „verfügbar" unmittelbar** — die Übersicht erfasst jede Ausgabe, nicht nur geplante (vgl. FR-V2). |
| FR-V5 | **Must** | Die Berechnung ist **transparent aufschlüsselbar**: Einnahmen, Fixkosten, Sparziele, getätigte Ausgaben und eingeplanter (ausgegrauter) Budgetrest werden einzeln dargestellt. |
| FR-V6 | **Must** | Der **Zyklusbeginn** wird durch den Eingang der höchsten wiederkehrenden Einnahme bestimmt; ein manuell gesetzter Stichtag ist als Fallback möglich. |

---

## 5. Analyse & Auswertung

Du willst nicht nur tracken, sondern **analysieren** — daher explizit:

| ID | Prio | Anforderung |
|----|------|-------------|
| FR-A1 | **Must** | **Ausgaben pro Kategorie** für einen Zeitraum (Liste + Diagramm). |
| FR-A2 | **Should** | **Zeitverlauf** von Ausgaben/Einnahmen (Monatsvergleich, Trend). |
| FR-A3 | **Should** | **Einnahmen-Ausgaben-Saldo** pro Monat (Cashflow). |
| FR-A4 | **Could** | Filter/Suche über Transaktionen (Zeitraum, Konto, Kategorie, Empfänger, Betrag). |
| FR-A5 | **Could** | Erkennung **wiederkehrender Zahlungen** (Abo-Übersicht) aus dem Transaktionsverlauf. |

---

## 6. Nicht-funktionale Anforderungen

| ID | Prio | Anforderung |
|----|------|-------------|
| NFR-1 | **Must** | **Datenschutz by Design**: keine Telemetrie ohne ausdrückliches Opt-in; keine Drittanbieter-Tracker. |
| NFR-2 | **Must** | **Verschlüsselung at rest** der lokalen Datenbank (mind. optional, idealerweise per App-Passwort/Schlüssel). |
| NFR-3 | **Must** | **Export & Import** des kompletten Datenbestands in einem offenen, dokumentierten Format (z. B. JSON oder SQLite + CSV). Ergänzt C-4. |
| NFR-4 | **Must** | **Plattform**: Die App läuft auf **macOS** (Desktop) und **Android** (GrapheneOS) und funktioniert auf beiden offline. Beide Geräte teilen sich denselben Datenbestand (siehe NFR-6). *Mit welcher Technik das umgesetzt wird, ist eine spätere Entscheidung und gehört nicht in die Anforderungen.* |
| NFR-5 | **Should** | **Performance**: flüssige Bedienung bei ≥ mehreren tausend Transaktionen. |
| NFR-6 | **Should** | **Backup & Geräteabgleich**: einfache, manuell auslösbare Sicherung der Datendatei (kompatibel mit eigenem Backup-Tooling). Der Abgleich zwischen Mac und Handy läuft ohne Cloud — z. B. über die eigene Nextcloud/Syncthing oder per Export/Import. |
| NFR-7 | **Could** | **Mehrwährungsfähigkeit** (sonst: feste Default-Währung EUR). |
| NFR-8 | **Could** | **Lokalisierung**: Deutsch als Standard, Datums-/Zahlenformate nach Locale. |

---

## 7. Bewusst ausgeschlossen (Out of Scope)

- Automatischer Kontoabruf / Banking-Schnittstellen jeder Art (Folge aus C-2).
- Cloud-Konto, serverseitige Verarbeitung, geteilte Multi-User-Haushalte (zumindest im MVP).
- Anlageberatung, Wertpapier-/Depot-Tracking mit Kursdaten (offline kaum sinnvoll).

---

## 8. MVP-Vorschlag

Kleinster sinnvoller Funktionsumfang aus den **Must**-Anforderungen:
FR-D1, FR-D2, FR-D5–D7 (Erfassung, CSV-Import, wiederkehrende Buchungen) · FR-K1–K4 (Konten + Gesamtsumme) · FR-C1–C5 (Über-/Untergruppen + Regeln) · FR-B1–B2 (Budgets) · FR-S1–S2 (Sparziele) · FR-T1–T2 (Töpfe) · FR-V1–V6 (verfügbarer Betrag + Zyklus) · FR-A1 (Ausgaben pro Kategorie) · NFR-1–3.
*(FR-D8 anteilige Rücklage ist „Should" und kann nach dem MVP folgen.)*

---

## 9. Offene Fragen / zu treffende Entscheidungen

## 9. Offene Fragen / zu treffende Entscheidungen

**Alle Anforderungsfragen sind geklärt** — das Dokument ist vollständig:
Zyklus = Eingang der höchsten wiederkehrenden Einnahme (OQ-7) · Budgets zählen nach **Ist-Ausgaben**, Rest wird ausgegraut (OQ-5) · nicht budgetierte Ausgaben reduzieren „verfügbar" direkt (OQ-6) · Zyklus = Gehaltseingang (OQ-4) · Sparziele als virtuelle Töpfe (OQ-3) · seltene Fixkosten: volle Buchung als Default, anteilige Rücklage pro Eintrag umschaltbar (OQ-8, → FR-D8) · Plattform: macOS + Android, offline (OQ-2, → NFR-4).

Die Wahl der konkreten Technik (Programmiersprache, Framework) ist bewusst **keine** Anforderung, sondern eine spätere Umsetzungsentscheidung.
