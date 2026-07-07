from pathlib import Path
from parsers import DKB

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def find_latest_dkb_export() -> Path:
    """Find the most recently modified raw DKB export CSV in the data folder."""
    candidates = [
        f for f in DATA_DIR.glob("*Umsatzliste_Girokonto*.csv")
        if "categorized" not in f.name and "short" not in f.name
    ]

    if not candidates:
        raise FileNotFoundError(f"No DKB export CSV found in {DATA_DIR}")

    return max(candidates, key=lambda f: f.stat().st_mtime)


df1 = DKB.load(str(find_latest_dkb_export()))
print(df1.head())