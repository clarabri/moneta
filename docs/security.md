# NFR-2 — Verschlüsselung at rest: technische Dokumentation

Stand: 2026-06-26

---

## Was genau passiert

Die Datenbankdatei `~/.moneta/data.db` wird mit **SQLCipher 4** verschlüsselt gespeichert.
SQLCipher ist eine Open-Source-Erweiterung für SQLite, die jede Seite der Datenbankdatei einzeln
mit AES-256-CBC verschlüsselt. Ohne das richtige Passwort sieht die Datei wie zufällige Binärdaten aus.

---

## Kryptographische Parameter (SQLCipher 4 Defaults)

| Parameter | Wert | Bedeutung |
|-----------|------|-----------|
| Verschlüsselung | AES-256-CBC | Symmetrische Blockverschlüsselung, 256-Bit-Schlüssel |
| Schlüsselableitung | PBKDF2-HMAC-SHA512 | Wandelt das Passwort in einen 256-Bit-Schlüssel um |
| PBKDF2-Iterationen | 256.000 | Erschwert Brute-Force-Angriffe erheblich |
| Seitengröße | 4096 Byte | Jede DB-Seite wird separat verschlüsselt |
| HMAC | SHA512 | Integritätsprüfung pro Seite (Schutz vor Manipulation) |
| Salt | 16 Byte, zufällig, im Dateiheader | Einzigartig pro Datenbankdatei |

**Was das bedeutet:** Wer nur die Datei `data.db` hat — z. B. nach Diebstahl des Geräts — kann
ohne das Passwort keine Daten lesen. Die 256.000 PBKDF2-Iterationen machen automatische
Passwortrateangriffe sehr langsam (je nach Hardware ~Millisekunden pro Versuch, nicht Mikrosekunden).

---

## Wo das Passwort gespeichert ist

**Nirgendwo auf der Festplatte.** Das Passwort existiert nur im Arbeitsspeicher (RAM), für die
Dauer der laufenden Anwendung. Konkret:

- Die Variable `DB_KEY` in `backend/db.py` hält das Passwort als Python-String im RAM.
- Beim Beenden der App wird der Prozess beendet und der RAM freigegeben.
- Es gibt keine Passwort-Datei, keinen Keychain-Eintrag, keine `.env`-Datei.

Das Passwort wird bei jedem Start neu eingegeben (oder per `MONETA_KEY`-Umgebungsvariable gesetzt).

---

## Startup-Ablauf

```
./scripts/run.sh
  └─► python backend/main.py
        ├─► sqlcipher3 importierbar? → ENCRYPTION_AVAILABLE = True
        ├─► MONETA_KEY-Umgebungsvariable gesetzt?
        │     JA  → Passwort aus Umgebungsvariable
        │     NEIN → getpass.getpass() → Passwort vom Terminal (kein Echo)
        ├─► Passwort leer?
        │     JA  → Warnung, App startet OHNE Verschlüsselung
        │     NEIN → set_db_key(passwort)
        ├─► migrate_encrypt_if_needed(): DB bereits vorhanden und unverschlüsselt?
        │     JA  → PRAGMA rekey → DB wird in-place verschlüsselt
        │     NEIN → nichts zu tun
        ├─► verify_key(): Passwort korrekt?
        │     NEIN → Fehlermeldung + sys.exit(1)
        └─► init_db(), Server startet
```

---

## Wie eine Datenbankverbindung geöffnet wird (`backend/db.py`)

```python
conn = _db_module.connect(str(DB_PATH))        # Datei öffnen
conn.execute(f"PRAGMA key='{escaped_key}'")    # Schlüssel setzen → entschlüsselt
conn.row_factory = _db_module.Row
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA foreign_keys=ON")
```

`PRAGMA key` muss die **erste** Operation nach dem Verbindungsaufbau sein.
SQLCipher entschlüsselt dann die Datenbankseiten transparent beim Lesen und verschlüsselt
sie beim Schreiben. Der Rest des Code (alle SQL-Abfragen) ist unverändert.

### SQL-Injection in PRAGMA key

`PRAGMA key` unterstützt keine parametrisierten Abfragen (Prepared Statements). Deshalb wird
das Passwort manuell escaped: einzelne Anführungszeichen werden verdoppelt (`'` → `''`).

```python
escaped = DB_KEY.replace("'", "''")
conn.execute(f"PRAGMA key='{escaped}'")
```

Das schützt davor, dass ein Passwort wie `'; DROP TABLE accounts; --` den PRAGMA-Aufruf bricht.

---

## Migration: unverschlüsselte → verschlüsselte Datenbank

Wer Moneta schon vor NFR-2 genutzt hat, hat eine unverschlüsselte `data.db`.
Die Migration läuft automatisch beim ersten Start mit Passwort:

```
migrate_encrypt_if_needed(key):
  1. Versuche, data.db mit plain sqlite3 zu öffnen und SELECT 1 auszuführen.
     → Gelingt es: Datei ist unverschlüsselt.
     → Schlägt es fehl: Datei ist bereits verschlüsselt (oder beschädigt) → abbrechen.
  2. Öffne data.db mit sqlcipher3 OHNE PRAGMA key (= SQLite-Kompatibilitätsmodus).
  3. Führe PRAGMA rekey='passwort' aus.
     → SQLCipher verschlüsselt die gesamte Datei in-place mit dem neuen Schlüssel.
  4. Fertig. Alle nachfolgenden Öffnungen benötigen das Passwort.
```

**Sicherheitshinweis:** Während der Migration existiert kurzzeitig ein unverschlüsselter
Datenbankzustand auf der Festplatte (der Originalzustand, der überschrieben wird).
Da die Migration in-place erfolgt, liegt kein zweites Klartext-Exemplar der Datenbank an.

---

## Was dieser Schutz NICHT leistet

| Szenario | Geschützt? | Begründung |
|----------|-----------|------------|
| Jemand stiehlt die `data.db`-Datei | ✅ Ja | AES-256, ohne Passwort nicht lesbar |
| Jemand hat Zugriff auf das laufende System (gleicher User) | ❌ Nein | Passwort liegt im RAM, kann ggf. ausgelesen werden |
| Jemand hat Root-Zugriff auf das Gerät | ❌ Nein | Root kann RAM und Prozesse auslesen |
| Brute-Force-Angriff auf das Passwort | ⚠️ Teilweise | PBKDF2 mit 256.000 Iterationen verlangsamt stark; ein schwaches Passwort bleibt angreifbar |
| Backup-Dateien der unverschlüsselten DB (Time Machine) | ❌ Nein | Alte Backups vor der Migration sind unverschlüsselt |

---

## Umgebungsvariable MONETA_KEY

Für automatisierte Setups (z. B. Skripte, Startartikel bei Login) kann das Passwort per
Umgebungsvariable übergeben werden:

```bash
MONETA_KEY="meinPasswort" ./scripts/run.sh
```

**Sicherheitshinweis:** Umgebungsvariablen sind auf macOS nicht für andere Benutzer sichtbar
(kein `/proc/<pid>/environ`-Äquivalent), aber sie können in Shell-Historien oder Logs auftauchen.
Die interaktive Eingabe via `getpass` ist sicherer, da das Passwort nie in der Shell-Historie landet.
