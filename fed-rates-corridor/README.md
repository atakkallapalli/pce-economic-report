# Federal Reserve Policy Rate Corridor Analysis

Replicates the FRED analysis published at:
**[https://fred.stlouisfed.org/graph/?g=1Ng5J](https://fred.stlouisfed.org/graph/?g=1Ng5J)**

This analysis visualizes the Federal Reserve's policy rate corridor — the range of key
money market interest rates bounded by the upper and lower limits of the federal funds
target range.

## Series Included

| Series ID | Description | Source |
|---|---|---|
| DFEDTARU | Federal Funds Target Range - Upper Limit | Board of Governors |
| DFEDTARL | Federal Funds Target Range - Lower Limit | Board of Governors |
| IORB | Interest Rate on Reserve Balances | Board of Governors |
| SOFR | Secured Overnight Financing Rate | NY Fed |
| DFF | Federal Funds Effective Rate | Board of Governors |
| TGCRRATE | Tri-Party General Collateral Rate | NY Fed |
| RRPONTSYAWARD | Overnight Reverse Repurchase Agreements Award Rate | NY Fed |
| SRFTSYD | Standing Repo (SRP) Operations Rate | NY Fed |

## Chart Styling

Charts use the **Federal Reserve official stylesheet** matching FRED's published
visualizations:
- Fed navy/blue color palette for target range bounds
- Distinct colors for each rate within the corridor
- Recession shading (NBER dates)
- Source attribution footer
- Grid lines and axis formatting consistent with fred.stlouisfed.org

## Usage

```bash
# 1. Download data from FRED
python fed-rates-corridor/download_rates.py

# 2. Generate analysis charts
python fed-rates-corridor/analyze_rates.py
```

### Optional: Use fredapi with API key

```bash
# Set your FRED API key (free at https://fred.stlouisfed.org/docs/api/api_key.html)
export FRED_API_KEY=your_api_key_here
python fed-rates-corridor/download_rates.py
```

## Output

- `output/fed_rates_corridor.png` — Full historical rate corridor chart
- `output/fed_rates_corridor_1yr.png` — 1-year view (matches default FRED graph)
- `output/rates_summary.json` — Summary statistics (latest values, ranges)

## Integration with FRED Tools

### fredapi (Python)
This analysis uses [FRB-demo/fredapi](https://github.com/FRB-demo/fredapi) — a Python
client library for the FRED API. When `FRED_API_KEY` is set, data is fetched through
the `fredapi.Fred` class. Without a key, the public FRED CSV endpoint is used.

### fred-mcp-server (MCP)
The series in this analysis can also be accessed via
[FRB-demo/fred-mcp-server](https://github.com/FRB-demo/fred-mcp-server) — an MCP
server that provides LLM access to FRED data. Relevant MCP tools:

- `fred_get_series` — Retrieve observations for any series ID
- `fred_search` — Discover related series by keyword
- `fred_browse` — Navigate FRED's category hierarchy

## Understanding the Rate Corridor

The Federal Reserve's policy rate corridor is the framework through which monetary
policy is implemented:

- **Upper Limit (DFEDTARU)**: The ceiling of the target range
- **Standing Repo Rate (SRFTSYD)**: Backstop lending facility rate (at or above upper limit)
- **IORB**: The rate paid on bank reserves — the primary tool steering rates
- **SOFR / DFF / TGCRRATE**: Market rates that trade within the corridor
- **ON RRP Award Rate (RRPONTSYAWARD)**: Floor rate for overnight lending
- **Lower Limit (DFEDTARL)**: The floor of the target range

## Directory Structure

```
fed-rates-corridor/
├── README.md              # This file
├── requirements.txt       # Python dependencies
├── download_rates.py      # Data download script
├── analyze_rates.py       # Analysis and chart generation
├── data/                  # Downloaded CSV files (gitignored)
└── output/                # Generated charts and statistics
```
