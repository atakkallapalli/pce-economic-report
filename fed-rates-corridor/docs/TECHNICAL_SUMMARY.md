# Technical Summary: Federal Reserve Policy Rate Corridor Analysis

## Overview

This module implements a complete data pipeline for fetching, analyzing, and visualizing the Federal Reserve's policy rate corridor — the framework of administered and market-determined interest rates through which the FOMC implements monetary policy.

The analysis replicates the FRED graph published at:
[https://fred.stlouisfed.org/graph/?g=1Ng5J](https://fred.stlouisfed.org/graph/?g=1Ng5J)

---

## System Architecture

### Components

| Component | File | Purpose |
|---|---|---|
| Data Ingestion | `download_rates.py` | Fetches 8 daily interest rate series from FRED |
| Analysis Engine | `analyze_rates.py` | Computes statistics and generates visualizations |
| Configuration | `requirements.txt` | Python dependency specifications |
| Output Artifacts | `output/` | Generated charts (PNG) and statistics (JSON) |

### Technology Stack

| Layer | Technology | Version |
|---|---|---|
| Language | Python | 3.10+ |
| Data Processing | pandas | ≥2.0 |
| Visualization | matplotlib | ≥3.7 |
| Numerical Computing | numpy | ≥1.24 |
| FRED API Client | fredapi | ≥0.5.0 |
| Data Source | FRED REST API / CSV Endpoint | v1 |

---

## Data Pipeline Architecture

### Ingestion Layer

The data ingestion module (`download_rates.py`) implements a dual-path data acquisition strategy:

1. **Primary Path (No Authentication):** Uses FRED's public CSV download endpoint
   - URL pattern: `https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}&cosd={start}&coed=9999-12-31`
   - No API key required
   - Returns observation-date-indexed CSV with series values

2. **Secondary Path (Authenticated):** Uses the `fredapi` Python library
   - Requires `FRED_API_KEY` environment variable
   - Provides access to additional metadata, revisions, and vintage data
   - Integrates with the FRB-demo/fredapi library

### Processing Layer

The analysis engine (`analyze_rates.py`) performs:

1. **Data Loading & Normalization**
   - Parses heterogeneous CSV column naming conventions
   - Handles missing values (FRED's `.` convention)
   - Constructs datetime-indexed pandas DataFrames

2. **Statistical Computation**
   - Latest values for each series
   - Min/max/mean over full history
   - Corridor width calculation (upper - lower bound in basis points)

3. **Visualization Generation**
   - Full historical view (2000–present)
   - 1-year rolling view (matches FRED's default display)
   - Federal Reserve official chart stylesheet

### Output Layer

| Artifact | Format | Description |
|---|---|---|
| `fed_rates_corridor.png` | PNG (150 DPI) | Full historical rate corridor chart |
| `fed_rates_corridor_1yr.png` | PNG (150 DPI) | 1-year view of the rate corridor |
| `rates_summary.json` | JSON | Key statistics and latest values |

---

## FRED Series Catalog

### Rate Corridor Components

| Series ID | Name | Source | Frequency | Role |
|---|---|---|---|---|
| DFEDTARU | Federal Funds Target Range - Upper Limit | Board of Governors | Daily, 7-Day | Corridor ceiling |
| DFEDTARL | Federal Funds Target Range - Lower Limit | Board of Governors | Daily, 7-Day | Corridor floor |
| IORB | Interest Rate on Reserve Balances | Board of Governors | Daily, 7-Day | Primary policy tool |
| SOFR | Secured Overnight Financing Rate | NY Fed | Daily | Treasury repo benchmark |
| DFF | Federal Funds Effective Rate | Board of Governors | Daily, 7-Day | Interbank lending rate |
| TGCRRATE | Tri-Party General Collateral Rate | NY Fed | Daily | Tri-party repo rate |
| RRPONTSYAWARD | Overnight Reverse Repurchase Agreements Award Rate | NY Fed | Daily | ON RRP floor rate |
| SRFTSYD | Standing Repo (SRP) Operations Rate | NY Fed | Daily | SRP ceiling rate |

### Data Availability

| Series | Start Date | End Date | Observations |
|---|---|---|---|
| DFF | 2000-01-03 | Present | ~6,800+ |
| DFEDTARU | 2008-12-16 | Present | ~6,200+ |
| DFEDTARL | 2008-12-16 | Present | ~6,200+ |
| IORB | 2021-07-29 | Present | ~1,700+ |
| SOFR | 2018-04-03 | Present | ~2,000+ |
| TGCRRATE | 2018-05-03 | Present | ~1,900+ |
| RRPONTSYAWARD | 2013-09-23 | Present | ~3,200+ |
| SRFTSYD | 2021-07-29 | Present | ~1,200+ |

---

## Visualization Specifications

### Federal Reserve Chart Stylesheet

The chart styling replicates the official FRED/Federal Reserve visual identity:

| Property | Value | Rationale |
|---|---|---|
| Figure Size | 14×7 inches | Widescreen aspect ratio for rate corridor |
| DPI | 150 | Publication quality |
| Font Family | Helvetica Neue / Arial / DejaVu Sans | Fed standard sans-serif |
| Background | White (#FFFFFF) | Clean, professional |
| Grid | Light gray (#E0E0E0), 0.5px | Subtle reference lines |
| Axis Color | Dark gray (#333333) | High contrast without pure black |
| Target Range | Navy blue (#1F4E79), dashed | Distinguishes administered bounds |
| Market Rates | Distinct colors, solid lines | Visual separation within corridor |

### Color Palette

```
DFEDTARU/DFEDTARL: #1F4E79 (Navy Blue)     — Target range bounds
SRFTSYD:           #C00000 (Fed Red)        — Standing Repo Rate
IORB:              #2E75B6 (Medium Blue)    — Interest on Reserves
SOFR:              #548235 (Forest Green)   — Secured Overnight Rate
DFF:               #7030A0 (Purple)         — Effective Fed Funds
TGCRRATE:          #ED7D31 (Orange)         — Tri-Party GC Rate
RRPONTSYAWARD:     #70AD47 (Light Green)    — ON RRP Award Rate
```

### Chart Features

- **Recession Shading:** Gray vertical bands for NBER-dated U.S. recessions (2001, 2007–2009, 2020)
- **Corridor Fill:** Semi-transparent fill between upper and lower target range bounds
- **Source Attribution:** Footer citing Board of Governors and NY Fed via FRED®
- **Axis Formatting:** Y-axis in 25 bps increments; X-axis with date labels

---

## Integration Points

### fredapi (Python Library)

```python
from fredapi import Fred

fred = Fred(api_key=os.environ["FRED_API_KEY"])
data = fred.get_series("SOFR", observation_start="2024-01-01")
```

- Repository: [FRB-demo/fredapi](https://github.com/FRB-demo/fredapi)
- Provides: `get_series()`, `get_series_info()`, `search()`, `get_series_as_of_date()`
- Authentication: Requires free FRED API key

### fred-mcp-server (MCP Protocol)

- Repository: [FRB-demo/fred-mcp-server](https://github.com/FRB-demo/fred-mcp-server)
- Protocol: Model Context Protocol (stdio/HTTP transport)
- Tools: `fred_browse`, `fred_search`, `fred_get_series`
- Use Case: LLM-powered economic data queries and analysis

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Network failure during download | RuntimeError raised, series added to error list |
| Missing CSV file at analysis time | FileNotFoundError with guidance to run download first |
| Invalid/missing values in CSV | Coerced to NaN, dropped from analysis |
| Missing FRED_API_KEY | Graceful fallback to public CSV endpoint |

---

## Performance Characteristics

| Metric | Value |
|---|---|
| Download time (8 series) | ~3–5 seconds |
| Chart generation time | ~2–3 seconds |
| Total pipeline runtime | ~5–8 seconds |
| Output chart file size | ~180–220 KB each |
| Memory footprint | ~50 MB peak |

---

## Security & Compliance

- No API keys are stored in source code or committed to version control
- FRED API key (when used) is read from environment variable only
- All data sourced from official Federal Reserve endpoints
- No PII or sensitive data processed
- Public data freely available per FRED's terms of use
