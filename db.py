import uuid
from datetime import datetime
from pathlib import Path
import sqlite3 as _plain_sqlite3

# ---------------------------------------------------------------------------
# Encryption layer (SQLCipher, optional)
#
# If sqlcipher3 is installed, all database files are opened via SQLCipher.
# If not, we fall back to plain sqlite3 (unencrypted).
# ---------------------------------------------------------------------------

try:
    from sqlcipher3 import dbapi2 as _db_module
    ENCRYPTION_AVAILABLE = True
except ImportError:
    import sqlite3 as _db_module  # type: ignore
    ENCRYPTION_AVAILABLE = False

DB_PATH = Path.home() / ".moneta" / "data.db"
DB_KEY: str | None = None


def set_db_key(key: str) -> None:
    """Store the passphrase in memory. Never written to disk."""
    global DB_KEY
    DB_KEY = key


def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = _db_module.connect(str(DB_PATH))
    if ENCRYPTION_AVAILABLE and DB_KEY:
        # Single-quote escaping to prevent SQL injection in PRAGMA key.
        escaped = DB_KEY.replace("'", "''")
        conn.execute(f"PRAGMA key='{escaped}'")
    conn.row_factory = _db_module.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def migrate_encrypt_if_needed(key: str) -> bool:
    """
    If the database file already exists as a plain (unencrypted) SQLite file,
    encrypt it in-place using PRAGMA rekey.

    Detection: plain sqlite3 can read the file → it is unencrypted.
    Migration: open with sqlcipher3 in compatibility mode (no PRAGMA key =
    plain-SQLite passthrough), then PRAGMA rekey to add encryption.

    Returns True if migration was performed.
    """
    if not ENCRYPTION_AVAILABLE or not DB_PATH.exists():
        return False

    # Try opening as plain SQLite to detect whether the file is unencrypted.
    try:
        test = _plain_sqlite3.connect(str(DB_PATH))
        test.execute("SELECT 1 FROM sqlite_master")
        test.close()
    except _plain_sqlite3.DatabaseError:
        return False  # already encrypted, or corrupt — skip

    # File is plaintext. Open via sqlcipher3 without setting a key
    # (= SQLite compatibility mode), then re-key to encrypt.
    conn = _db_module.connect(str(DB_PATH))
    escaped = key.replace("'", "''")
    conn.execute(f"PRAGMA rekey='{escaped}'")
    conn.close()
    return True


def verify_key() -> bool:
    """
    Return True if DB_KEY can successfully open the database.
    Used to detect a wrong password before starting the server.
    """
    if not DB_PATH.exists():
        return True
    try:
        conn = get_db()
        conn.execute("SELECT 1 FROM sqlite_master")
        conn.close()
        return True
    except Exception:
        return False


def uid() -> str:
    return str(uuid.uuid4())


def now_iso() -> str:
    return datetime.now().isoformat()


SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    initial_balance REAL NOT NULL DEFAULT 0.0,
    currency TEXT NOT NULL DEFAULT 'EUR',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    parent_id TEXT REFERENCES categories(id) ON DELETE SET NULL,
    type TEXT NOT NULL,
    icon TEXT DEFAULT '📁',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    amount REAL NOT NULL,
    date TEXT NOT NULL,
    payee TEXT DEFAULT '',
    purpose TEXT DEFAULT '',
    note TEXT DEFAULT '',
    category_id TEXT REFERENCES categories(id) ON DELETE SET NULL,
    type TEXT NOT NULL,
    transfer_to_account_id TEXT REFERENCES accounts(id),
    recurring_rule_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recurring_rules (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    amount REAL NOT NULL,
    type TEXT NOT NULL,
    category_id TEXT REFERENCES categories(id) ON DELETE SET NULL,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    payee TEXT DEFAULT '',
    purpose TEXT DEFAULT '',
    interval_type TEXT NOT NULL,
    day_of_month INTEGER DEFAULT 1,
    next_due_date TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS category_rules (
    id TEXT PRIMARY KEY,
    pattern TEXT NOT NULL,
    field TEXT NOT NULL,
    category_id TEXT NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    priority INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS budgets (
    id TEXT PRIMARY KEY,
    category_id TEXT NOT NULL UNIQUE REFERENCES categories(id) ON DELETE CASCADE,
    amount REAL NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS savings_goals (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    target_amount REAL NOT NULL,
    current_amount REAL NOT NULL DEFAULT 0.0,
    monthly_contribution REAL NOT NULL DEFAULT 0.0,
    target_date TEXT,
    color TEXT DEFAULT '#6366f1',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pots (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    target_amount REAL NOT NULL DEFAULT 0.0,
    color TEXT DEFAULT '#6366f1',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

DEFAULT_CATEGORIES = [
    # (slug_key, name, parent_slug, type, icon)
    # Parents – expense
    ("fixkosten",        "Fixkosten",               None,           "expense", "🏠"),
    ("abos",             "Abos & Mitgliedschaften",  None,           "expense", "🔄"),
    ("lebensmittel",     "Lebensmittel",             None,           "expense", "🛒"),
    ("lifestyle",        "Lifestyle & Freizeit",     None,           "expense", "🎉"),
    ("transport",        "Transport",                None,           "expense", "🚗"),
    ("gesundheit",       "Gesundheit",               None,           "expense", "💊"),
    ("sonstiges_a",      "Sonstiges",                None,           "expense", "📦"),
    # Parents – income
    ("gehalt_cat",       "Gehalt & Lohn",            None,           "income",  "💰"),
    ("einnahmen_s",      "Sonstige Einnahmen",       None,           "income",  "💵"),
    # Children – expense
    ("miete",            "Miete / Hypothek",         "fixkosten",    "expense", "🏠"),
    ("strom",            "Strom",                    "fixkosten",    "expense", "⚡"),
    ("gas",              "Gas / Heizung",            "fixkosten",    "expense", "🔥"),
    ("internet",         "Internet",                 "fixkosten",    "expense", "🌐"),
    ("telefon",          "Telefon",                  "fixkosten",    "expense", "📱"),
    ("rundfunk",         "Rundfunkbeitrag",          "fixkosten",    "expense", "📺"),
    ("versicherung",     "Versicherungen",           "fixkosten",    "expense", "🛡️"),
    ("streaming",        "Streaming",                "abos",         "expense", "🎬"),
    ("zeitungen",        "Zeitungen / Magazine",     "abos",         "expense", "📰"),
    ("software",         "Software / Cloud",         "abos",         "expense", "💻"),
    ("fitness",          "Fitnessstudio",            "abos",         "expense", "🏋️"),
    ("musik",            "Musik-Abo",                "abos",         "expense", "🎵"),
    ("supermarkt",       "Supermarkt",               "lebensmittel", "expense", "🛒"),
    ("baeckerei",        "Bäckerei / Markt",         "lebensmittel", "expense", "🥐"),
    ("restaurant",       "Restaurant & Café",        "lifestyle",    "expense", "🍽️"),
    ("bar",              "Bar & Ausgehen",           "lifestyle",    "expense", "🍻"),
    ("kino",             "Kino & Theater",           "lifestyle",    "expense", "🎭"),
    ("shopping",         "Shopping & Kleidung",      "lifestyle",    "expense", "👗"),
    ("hobby",            "Hobby",                    "lifestyle",    "expense", "🎨"),
    ("reisen",           "Urlaub & Reisen",          "lifestyle",    "expense", "✈️"),
    ("opnv",             "ÖPNV / Bahn",              "transport",    "expense", "🚌"),
    ("tanken",           "Tanken",                   "transport",    "expense", "⛽"),
    ("taxi",             "Taxi / Ridesharing",       "transport",    "expense", "🚕"),
    ("arzt",             "Arzt & Apotheke",          "gesundheit",   "expense", "👨‍⚕️"),
    # Children – income
    ("gehalt",           "Gehalt",                   "gehalt_cat",   "income",  "💼"),
    ("freelance",        "Freelance",                "gehalt_cat",   "income",  "💡"),
    ("stipendium",       "Stipendium",               "gehalt_cat",   "income",  "🎓"),
    ("zinsen",           "Zinsen & Dividenden",      "einnahmen_s",  "income",  "📈"),
    ("steuer",           "Steuerrückerstattung",     "einnahmen_s",  "income",  "🏛️"),
    ("geschenke",        "Geschenke erhalten",       "einnahmen_s",  "income",  "🎁"),
]

DEFAULT_RULES = [
    # (pattern, field, category_slug, priority)
    ("REWE",            "payee", "supermarkt",    10),
    ("EDEKA",           "payee", "supermarkt",    10),
    ("LIDL",            "payee", "supermarkt",    10),
    ("ALDI",            "payee", "supermarkt",    10),
    ("PENNY",           "payee", "supermarkt",    10),
    ("NETTO",           "payee", "supermarkt",    10),
    ("KAUFLAND",        "payee", "supermarkt",    10),
    ("NETFLIX",         "payee", "streaming",     10),
    ("SPOTIFY",         "payee", "musik",         10),
    ("AMAZON PRIME",    "payee", "streaming",     10),
    ("DISNEY",          "payee", "streaming",     10),
    ("ARD ZDF",         "payee", "rundfunk",      10),
    ("RUNDFUNK",        "payee", "rundfunk",      10),
    ("TANKSTELLE",      "payee", "tanken",        10),
    ("ARAL",            "payee", "tanken",        10),
    ("SHELL",           "payee", "tanken",        10),
    ("DB BAHN",         "payee", "opnv",          10),
    ("MVGO",            "payee", "opnv",          10),
    ("UBER",            "payee", "taxi",          10),
    ("PAYPAL",          "payee", "sonstiges_a",    1),
]


def init_db():
    conn = get_db()
    conn.executescript(SCHEMA)
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    if count == 0:
        _seed(conn)

    conn.close()


def _seed(conn):
    ts = now_iso()
    slug_to_id: dict[str, str] = {}

    parents = [(s, n, p, t, i) for s, n, p, t, i in DEFAULT_CATEGORIES if p is None]
    children = [(s, n, p, t, i) for s, n, p, t, i in DEFAULT_CATEGORIES if p is not None]

    for slug, name, _, cat_type, icon in parents:
        cat_id = uid()
        slug_to_id[slug] = cat_id
        conn.execute(
            "INSERT INTO categories (id, name, parent_id, type, icon, created_at) VALUES (?,?,?,?,?,?)",
            (cat_id, name, None, cat_type, icon, ts),
        )

    for slug, name, parent_slug, cat_type, icon in children:
        cat_id = uid()
        slug_to_id[slug] = cat_id
        conn.execute(
            "INSERT INTO categories (id, name, parent_id, type, icon, created_at) VALUES (?,?,?,?,?,?)",
            (cat_id, name, slug_to_id.get(parent_slug), cat_type, icon, ts),
        )

    for pattern, field, cat_slug, priority in DEFAULT_RULES:
        if cat_slug in slug_to_id:
            conn.execute(
                "INSERT INTO category_rules (id, pattern, field, category_id, priority, created_at) VALUES (?,?,?,?,?,?)",
                (uid(), pattern, field, slug_to_id[cat_slug], priority, ts),
            )

    conn.commit()
