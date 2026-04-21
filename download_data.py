"""
Download PCE (Personal Consumption Expenditures) data from FRED.

Downloads the following series as CSV files into the data/ directory:
  - PCE:      Personal Consumption Expenditures (Billions $, SAAR)
  - PCEPI:    PCE Price Index (2017=100)
  - PCEPILFE: Core PCE Price Index excl. Food & Energy (2017=100)
  - PCEC96:   Real PCE (Billions of Chained 2017 $, SAAR)
  - PCEDG:    PCE Durable Goods (Billions $, SAAR)
  - PCEND:    PCE Nondurable Goods (Billions $, SAAR)
  - PCES:     PCE Services (Billions $, SAAR)

No API key required -- uses FRED's public CSV download endpoint.

Usage:
    python download_data.py
"""

import os
import urllib.request
import sys


# FRED series to download
SERIES = [
    "PCE",       # Personal Consumption Expenditures
    "PCEPI",     # PCE Price Index
    "PCEPILFE",  # Core PCE Price Index (excl. food & energy)
    "PCEC96",    # Real PCE (chained 2017 dollars)
    "PCEDG",     # PCE: Durable Goods
    "PCEND",     # PCE: Nondurable Goods
    "PCES",      # PCE: Services
]

FRED_CSV_URL = (
    "https://fred.stlouisfed.org/graph/fredgraph.csv"
    "?id={series_id}&cosd=1959-01-01&coed=9999-12-31"
)


def download_series(series_id: str, output_dir: str) -> str:
    """Download a single FRED series as CSV.

    Args:
        series_id: FRED series identifier (e.g. 'PCE').
        output_dir: Directory to save the CSV file.

    Returns:
        Path to the downloaded file.

    Raises:
        RuntimeError: If the download fails.
    """
    url = FRED_CSV_URL.format(series_id=series_id)
    filepath = os.path.join(output_dir, f"{series_id}.csv")

    try:
        urllib.request.urlretrieve(url, filepath)
        size = os.path.getsize(filepath)
        print(f"  {series_id}: {size:,} bytes -> {filepath}")
        return filepath
    except Exception as exc:
        raise RuntimeError(f"Failed to download {series_id}: {exc}") from exc


def main() -> None:
    """Download all PCE-related FRED series."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "data")
    os.makedirs(output_dir, exist_ok=True)

    print(f"Downloading {len(SERIES)} FRED series to {output_dir}/\n")

    errors = []
    for series_id in SERIES:
        try:
            download_series(series_id, output_dir)
        except RuntimeError as exc:
            print(f"  ERROR: {exc}", file=sys.stderr)
            errors.append(series_id)

    print(f"\nDone. {len(SERIES) - len(errors)}/{len(SERIES)} series downloaded.")
    if errors:
        print(f"Failed: {', '.join(errors)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
