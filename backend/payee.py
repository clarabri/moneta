"""Payee-Bereinigung für die Kategorisierung.

clean_payee   -> Ort + Zahlen aus dem (bereits normalisierten) payee entfernen,
                 damit Embeddings nach HÄNDLER clustern statt nach STADT.
merchant_key  -> zusätzlich Rechtsformen/Zusätze am Ende weg -> kurze, stabile Händler-Kennung.

Erwartet payees im Format von DKB.normalize_text (klein, ohne Akzente, Wörter mit "_" verklebt).

Drei Stolperfallen beim Ort, die hier abgefangen werden:
  1) Stadt klebt direkt am Namensende:      "rossmann2098kiel"  -> rossmann + kiel
  2) Stadt steht teils doppelt:             "cupcinokielkiel"   -> cupcino + kiel + kiel
  3) Zusammengesetzte Städte sind gekappt:  "...frankfurtam"    (von "Frankfurt am Main")
Deshalb wird die Stadt nur AM ENDE ($) entfernt, sonst würde z. B. "kieler_forde..." zerstückelt.
"""
import re
import unicodedata
import geonamescache

# Von Städten hier NEHMEN wir auch die Alternativnamen, weil geonamescache sie unter dem englischen
# Hauptnamen führt (Vienna, Munich, Cologne), die payees aber die deutsche Form (wien, munchen, koln).
GERMAN_SPEAKING = {"DE", "AT", "CH", "LI", "LU"}
# Verbindungswörter zusammengesetzter Ortsnamen (Frankfurt AM Main, Halle AN DER Saale, ...)
CONNECTORS = {"am", "an", "im", "ob", "bei", "vor", "unter", "ober", "nieder", "auf", "in", "der", "den"}
# Rechtsformen + generische Zusätze, die am Ende einer Händler-Kennung wegkönnen
LEGAL = sorted({
    "gmbh", "mbh", "ag", "kgaa", "kg", "ohg", "ug", "gbr",
    "sarl", "cie", "sca", "sa", "bv", "nv", "ltd", "inc",
    "zwnln", "zweigniederlassung", "filiale", "fil", "markt",
}, key=len, reverse=True)


def _norm(s: str) -> str:
    """Wie DKB.normalize_text: klein, Akzente weg (ä->a, ü->u), ohne Leer-/Bindestriche."""
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.replace(" ", "").replace("-", "")


def _build_city_pattern() -> "re.Pattern":
    gc = geonamescache.GeonamesCache()
    names = set()
    for c in gc.get_cities().values():
        if c["population"] < 5000:
            continue
        de = c["countrycode"] in GERMAN_SPEAKING
        # Hauptname weltweit; Alternativnamen nur deutschsprachiger Raum
        # (sonst fremdsprachige Transliterations-Fehltreffer wie "deka"=Dhaka, "cino"=Chino).
        for form in [c["name"]] + ((c.get("alternatenames") or []) if de else []):
            n = _norm(form)
            if len(n) >= 4 and n.isascii() and n.isalpha():  # filtert Kürzel/nicht-lateinische Namen
                names.add(n)
        # Zusammengesetzte deutsche Städte: abgeschnittene Präfixe als konkrete Literale ergänzen,
        # damit gekappte Felder wie "frankfurtam" (von "frankfurtammain") am Ende matchen.
        # Literale (keine gierige Regel) können nicht überkorrigieren wie z. B. "im"+"mobilien".
        if de:
            toks = c["name"].lower().split()
            if len(toks) >= 2 and any(t in CONNECTORS for t in toks[1:]):
                full, base = _norm(c["name"]), _norm(toks[0])
                for length in range(len(base) + 2, len(full)):
                    if length >= 4:
                        names.add(full[:length])
    # längste zuerst -> "frankfurt" wird vor "furt" entfernt;  (\1)* entfernt dieselbe Stadt mehrfach
    names = sorted(names, key=len, reverse=True)
    return re.compile("(" + "|".join(re.escape(n) for n in names) + r")(\1)*$")


_CITY_PATTERN = _build_city_pattern()
_LEGAL_PATTERN = re.compile("(" + "|".join(re.escape(w) for w in LEGAL) + r")+$")


def clean_payee(payee: str) -> str:
    """Ort + Zahlen am Ende entfernen. Erwartet einen bereits normalisierten payee."""
    t = str(payee).replace("_", "")   # Unterstriche entfernen -> alles verkleben
    t = re.sub(r"\d+", "", t)         # Zahlen (Filial-/Terminal-IDs) raus
    t = _CITY_PATTERN.sub("", t)      # Stadt am Ende entfernen (auch wenn mehrfach dieselbe)
    return t.strip()


def merchant_key(payee_clean: str) -> str:
    """Kurze, stabile Händler-Kennung: Rechtsformen/Zusätze am Ende weg.

    Hinweis: große Zahlungsdienstleister (PayPal, Amazon) bleiben teils zersplittert
    (viel Rechtstext/Adresse) -> das fängt der kNN-Fallback auf.
    """
    k = _LEGAL_PATTERN.sub("", str(payee_clean)).strip()
    return k or str(payee_clean)      # nie leer zurückgeben


def normalize(text: str) -> str:
    """Rohen payee vereinheitlichen: klein, Akzente weg, nur noch a-z/0-9
    (Satzzeichen und Leerzeichen entfernt). clean_payee/merchant_key erwarten diese Form.
    (Ersetzt die früher in DKB.normalize_text erledigte Aufbereitung.)"""
    s = unicodedata.normalize("NFKD", str(text).lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s)


def to_merchant_key(raw_payee: str) -> str:
    """Kompletter Weg vom ROHEN payee zur stabilen Kennung:
    normalize -> clean_payee (Ort/Zahlen weg) -> merchant_key (Rechtsformen weg)."""
    return merchant_key(clean_payee(normalize(raw_payee)))


# Zahlungsdienstleister: der payee ist immer gleich (z. B. "PayPal") und bestimmt die
# Kategorie NICHT. Der echte Händler steht im Verwendungszweck -> von dort holen.
_PAYPAL_MERCHANT = re.compile(r"ihr einkauf bei\s+(.+?)\s*$", re.IGNORECASE)


def effective_key(payee: str, description: str = "") -> str:
    """Stabiler Händler-Key. Bei Zahlungsdienstleistern (PayPal) den ECHTEN Händler aus
    dem Verwendungszweck extrahieren, sonst den bereinigten payee verwenden."""
    if "paypal" in normalize(payee):
        m = _PAYPAL_MERCHANT.search(str(description))
        if m:
            return to_merchant_key(m.group(1))
    return to_merchant_key(payee)