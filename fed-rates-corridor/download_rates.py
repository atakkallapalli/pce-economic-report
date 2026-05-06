"""
Download Federal Reserve policy rate corridor data from FRED.

Downloads the following daily interest rate series as CSV files:
  - DFEDTARU:      Federal Funds Target Range - Upper Limit
  - DFEDTARL:      Federal Funds Target Range - Lower Limit
  - IORB:          Interest Rate on Reserve Balances (IORB Rate)
  - SOFR:          Secured Overnight Financing Rate
  - DFF:           Federal Funds Effective Rate
  - TGCRRATE:      Tri-Party General Collateral Rate
  - RRPONTSYAWARD: Overnight Reverse Repurchase Agreements Award Rate
  - SRFTSYD:       Standing Repo (SRP) Operations Rate

Data sources:
  - Board of Governors of the Federal Reserve System (US)
  - Federal Reserve Bank of New York

Integrates with:
  - fredapi (https://github.com/FRB-demo/fredapi) - Python FRED client library
  - fred-mcp-server (https://github.com/FRB-demo/fred-mcp-server) - MCP server
    for LLM access to FRED data

Usage:
    python fed-rates-corridor/download_rates.py

    # With FRED API key (optional, enables fredapi library):
    FRED_API_KEY=your_key python fed-rates-corridor/download_rates.py
"""

import os
import sys
import urllib.request

import pandas as pd

# FRED series comprising the policy rate corridor
SERIES = {
    "DFEDTARU": "Federal Funds Target Range - Upper Limit",
    "DFEDTARL": "Federal Funds Target Range - Lower Limit",
    "IORB": "Interest Rate on Reserve Balances (IORB Rate)",
    "SOFR": "Secured Overnight Financing Rate",
    "DFF": "Federal Funds Effective Rate",
    "TGCRRATE": "Tri-Party General Collateral Rate",
    "RRPONTSYAWARD": "Overnight Reverse Repurchase Agreements Award Rate",
    "SRFTSYD": "Standing Repo (SRP) Operations Rate",
}

FRED_CSV_URL = (
    "https://fred.stlouisfed.org/graph/fredgraph.csv"
    "?id={series_id}&cosd={start_date}&coed=9999-12-31"
)

# Start date aligned with the FRED graph (covers full history for context)
START_DATE = "2000-01-01"


def download_with_fredapi(series_id: str, start_date: str) -> pd.Series:
    """Download a series using the fredapi library (requires FRED_API_KEY)."""
    from fredapi import Fred

    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        raise EnvironmentError("FRED_API_KEY not set")

    fred = Fred(api_key=api_key)
    data = fred.get_series(series_id, observation_start=start_date)
    return data


def download_with_csv(series_id: str, start_date: str, output_dir: str) -> str:
    """Download a series via FRED's public CSV endpoint (no API key required)."""
    url = FRED_CSV_URL.format(series_id=series_id, start_date=start_date)
    filepath = os.path.join(output_dir, f"{series_id}.csv")

    try:
        urllib.request.urlretrieve(url, filepath)
        size = os.path.getsize(filepath)
        print(f"  {series_id}: {size:,} bytes -> {filepath}")
        return filepath
    except Exception as exc:
        raise RuntimeError(f"Failed to download {series_id}: {exc}") from exc


def main() -> None:
    """Download all policy rate corridor series from FRED."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "data")
    os.makedirs(output_dir, exist_ok=True)

    use_fredapi = bool(os.environ.get("FRED_API_KEY"))
    method = "fredapi" if use_fredapi else "public CSV endpoint"
    print(f"Downloading {len(SERIES)} FRED series via {method}\n")
    print(f"Output directory: {output_dir}/\n")

    errors = []
    for series_id, description in SERIES.items():
        try:
            if use_fredapi:
                data = download_with_fredapi(series_id, START_DATE)
                filepath = os.path.join(output_dir, f"{series_id}.csv")
                df = data.reset_index()
                df.columns = ["observation_date", series_id]
                df.to_csv(filepath, index=False)
                size = os.path.getsize(filepath)
                print(f"  {series_id}: {size:,} bytes -> {filepath}")
            else:
                download_with_csv(series_id, START_DATE, output_dir)
        except Exception as exc:
            print(f"  ERROR ({series_id}): {exc}", file=sys.stderr)
            errors.append(series_id)

    print(f"\nDone. {len(SERIES) - len(errors)}/{len(SERIES)} series downloaded.")
    if errors:
        print(f"Failed: {', '.join(errors)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
