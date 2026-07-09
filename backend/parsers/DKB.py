import pandas as pd
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

# Function to find the header row, since the preamble length varies between exports
def find_header_row(file: str) -> int:
    """Return the 0-based line index of the column header in a DKB CSV export."""

    with open(file, encoding="utf-8-sig") as fh:
        for i, line in enumerate(fh):
            if line.lstrip('"').startswith("Buchungsdatum"):
                return i

    raise ValueError(f"No 'Buchungsdatum' header row found in {file}")

# Function to load a DKB CSV export and return a normalized DataFrame
def load(file: str) -> pd.DataFrame:
    """Load a DKB CSV export and return a normalized DataFrame."""

    df = pd.read_csv(
        file,
        sep=";",
        encoding="utf-8",
        skiprows=find_header_row(file)
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
        "Betrag (€)": "amount",
        "Kategorie": "category",
        "Unterkategorie": "subcateory"
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

    # Add metadata
    df["currency"] = "EUR"
    df["source"] = "DKB"
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
            "account",
            "category",
            "subcateory"
        ]
    ]