"""Pseudonymisierung/Redaktion VOR der Verarbeitung.

Zweck: echte personenbezogene Daten (IBAN, Verwendungszweck-Freitext, Namen bei
Privat-Überweisungen) nicht im Klartext in Logs/Chat/Cloud landen lassen.

Wichtig zur Einordnung:
- Die eigentliche Kategorisierung (sentence-transformers, kNN) läuft LOKAL -> in
  Produktion verlassen die Daten den Rechner ohnehin nicht.
- Ein GEHOSTETES LLM zum Kategorisieren würde dagegen jeden payee in die Cloud schicken
  -> für echte Finanzdaten besser ein lokales Modell.
- Händlernamen (REWE, Decathlon) bleiben erhalten: sie sind das Kategorisierungssignal
  und keine personenbezogenen Daten des Kontoinhabers.
"""
import hashlib
import re

# Hinweise auf ein Unternehmen (dann KEINE Person -> nicht pseudonymisieren)
_ORG_HINT = re.compile(
    r"(gmbh|mbh|\bag\b|\bkg\b|ohg|\bug\b|\bse\b|\be\.?v\b|\bco\b|sarl|\bltd\b|\binc\b|"
    r"markt|apotheke|bank|versicherung|energie|telekom|verlag|gruppe)",
    re.IGNORECASE,
)


def _pseudo(value: str, salt: str, prefix: str = "Person") -> str:
    """Stabiler, gesalzener Hash -> gleicher Name ergibt immer dasselbe Pseudonym."""
    h = hashlib.sha256((salt + str(value)).encode()).hexdigest()[:8]
    return f"{prefix}_{h}"


def suspected_person_payees(df, payee_col: str = "payee"):
    """payees, die nach PRIVATperson aussehen (2-3 großgeschriebene Wörter, keine Ziffern,
    kein Firmen-Hinweis). Nur zum REVIEW gedacht -> daraus die known_persons-Liste bauen.
    Heuristik ist bewusst grob und kann Firmen ohne Rechtsform falsch treffen.
    """
    def looks_like_person(p: str) -> bool:
        s = str(p)
        if any(ch.isdigit() for ch in s) or _ORG_HINT.search(s):
            return False
        words = re.findall(r"[A-Za-zÄÖÜäöüß]+", s)
        return 2 <= len(words) <= 3 and all(w[:1].isupper() for w in words)

    return sorted({p for p in df[payee_col].astype(str) if looks_like_person(p)})


def pseudonymize_df(df, salt: str, known_persons=(), redact_columns=("account",),
                    payee_col: str = "payee"):
    """Gibt eine ANONYMISIERTE Kopie zurück.

    - redact_columns: Spalten komplett schwärzen (Default: account/IBAN;
      z. B. auch "description" ergänzen, wenn der Verwendungszweck Freitext-PII enthält).
    - known_persons: exakte payee-Werte (oder Teilstrings), die als Privatperson gelten
      -> werden durch ein stabiles Pseudonym ersetzt. Zuverlässiger als jede Heuristik.
    """
    out = df.copy()
    persons = [p.lower() for p in known_persons]

    for col in redact_columns:
        if col in out.columns:
            out[col] = "[redacted]"

    def fix(p: str) -> str:
        low = str(p).lower()
        if any(name in low for name in persons):
            return _pseudo(p, salt)
        return p

    if payee_col in out.columns:
        out[payee_col] = out[payee_col].map(fix)

    return out
