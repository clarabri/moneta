import pandas as pd
import re
import unicodedata
import hashlib

# Function to create a unique hash ID for each transaction based on its attributes
def create_transaction_id(row):
    key = (
        str(row["booking_date"]) +
        str(row["amount"]) +
        str(row["payee"]) +
        str(row["description"])
    )
    return hashlib.md5(key.encode()).hexdigest()

# Function to normalize text by removing accents, converting to lowercase, and replacing spaces with underscores
def normalize_text(text):
    if pd.isna(text):
        return ""

    text = str(text).lower().strip()

    # Remove accents (ä -> a, é -> e, ...)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))

    # Replace multiple whitespace with a single space
    text = re.sub(r"\s+", "_", text)

    # Remove punctuation
    text = re.sub(r"[^\w\s]", "", text)

    return text

# Function to load a DKB CSV export and return a normalized DataFrame
def load(file: str) -> pd.DataFrame:
    """Load a DKB CSV export and return a normalized DataFrame."""

    df = pd.read_csv(
        file,
        sep=";",
        encoding="utf-8",
        skiprows=4
    )
    account_df = pd.read_csv(
        file,
        sep=";",
        encoding="utf-8",
        nrows=1,
        header=None
    )

    # Rename columns to the internal format
    df = df.rename(columns={
        "Buchungsdatum": "booking_date",
        "Wertstellung": "value_date",
        "Zahlungsempfänger*in": "payee",
        "Verwendungszweck": "description",
        "Umsatztyp": "transaction_type",
        "Betrag (€)": "amount"
    })

    # Convert dates
    df["booking_date"] = pd.to_datetime(
        df["booking_date"],
        dayfirst=True,
        format="%d.%m.%y"
    )

    df["value_date"] = pd.to_datetime(
        df["value_date"],
        dayfirst=True,
        format="%d.%m.%y"
    )

    # Convert amount
    df["amount"] = (
        df["amount"]
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .astype(float)
    )

    # Normalize columns
    df["payee"] = df["payee"].apply(normalize_text)
    df["description"] = df["description"].apply(normalize_text)

    # Add metadata
    df["currency"] = "EUR"
    df["source"] = "DKB"
    df["category"] = None # this will be the ML defined tag
    df["account"] = account_df.iloc[0, 1].strip('"')
    df["transaction_id"] = df.apply(create_transaction_id, axis=1)

    # Return only normalized columns
    return df[
        [
            "transaction_id",
            "booking_date",
            "value_date",
            "amount",
            "currency",
            "payee",
            "description",
            "source",
            "transaction_type",
            "category",
            "account"
        ]
    ]