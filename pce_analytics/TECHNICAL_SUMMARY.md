# PCE Analytics — Technical Summary

## Overview

The PCE Analytics module is a self-contained data pipeline for ingesting, analyzing, and visualizing **Personal Consumption Expenditures (PCE)** macroeconomic data from the Federal Reserve Economic Data (FRED) service. It generates standardized inflation reports, multi-horizon analysis charts, and a machine-readable statistics summary used for economic analysis.

---

## Architecture

```
pce-economic-report/
├── pce_analytics/               # PCE analytics package
│   ├── __init__.py              # Package marker
│   ├── download_data.py         # FRED data acquisition (7 series)
│   ├── analyze_pce.py           # Computation engine + 8 chart generators
│   └── TECHNICAL_SUMMARY.md     # This document
├── data/                        # Raw FRED CSV cache (gitignored)
│   ├── PCE.csv
│   ├── PCEPI.csv
│   ├── PCEPILFE.csv
│   ├── PCEC96.csv
│   ├── PCEDG.csv
│   ├── PCEND.csv
│   └── PCES.csv
└── output/                      # Generated artifacts (gitignored)
    ├── charts/                  # 8 PNG visualizations (150 DPI)
    └── stats.json               # Machine-readable summary statistics
```

### Data Flow

```
FRED Public CSV API
       │
       ▼
download_data.py ──► data/*.csv  (7 FRED series)
                         │
                         ▼
  analyze_pce.py ──► output/charts/*.png  (8 charts)
                 └──► output/stats.json   (key statistics)
```

---

## Data Sources

All data is fetched from FRED's public CSV endpoint (`https://fred.stlouisfed.org/graph/fredgraph.csv`). No API key is required.

| FRED Series | Description | Units |
|-------------|-------------|-------|
| `PCE` | Personal Consumption Expenditures | Billions $, SAAR |
| `PCEPI` | PCE Price Index (Headline Inflation) | Index, 2017=100 |
| `PCEPILFE` | Core PCE Price Index (excl. Food & Energy) | Index, 2017=100 |
| `PCEC96` | Real PCE (inflation-adjusted) | Billions Chained 2017 $ |
| `PCEDG` | PCE: Durable Goods | Billions $, SAAR |
| `PCEND` | PCE: Nondurable Goods | Billions $, SAAR |
| `PCES` | PCE: Services | Billions $, SAAR |

---

## Computed Metrics

The analysis engine (`analyze_pce.py`) derives the following metrics from raw FRED series:

### Inflation Rates
- **Year-over-Year (YoY)**: 12-month percent change — `pct_change(12) * 100`
- **Month-over-Month Annualized**: Single-month growth projected to 12 months — `((1 + pct_change(1))^12 - 1) * 100`
- **3-Month Annualized**: Rolling 3-month growth annualized — `((level / level.shift(3))^(12/3) - 1) * 100`
- **6-Month Annualized**: Rolling 6-month growth annualized — `((level / level.shift(6))^(12/6) - 1) * 100`

### Composition
- **Component Shares**: Durable Goods, Nondurable Goods, and Services as percentage of total PCE
- **Real vs. Nominal**: Inflation-adjusted (chained 2017 dollars) spending levels and growth

---

## Key Statistics (Latest: March 2026)

| Metric | Value |
|--------|-------|
| **Nominal PCE** | $21,860.5B |
| **Nominal PCE YoY Growth** | 5.7% |
| **Real PCE** | $16,772.7B (chained 2017$) |
| **Real PCE YoY Growth** | 2.1% |
| **Headline PCE Inflation (YoY)** | 3.5% |
| **Headline MoM Annualized** | 8.3% |
| **Headline 3M Annualized** | 5.6% |
| **Headline 6M Annualized** | 4.3% |
| **Core PCE Inflation (YoY)** | 3.2% |
| **Core MoM Annualized** | 3.6% |
| **Core 3M Annualized** | 4.4% |
| **Core 6M Annualized** | 3.7% |
| **Services Share** | 69.0% |
| **Nondurable Goods Share** | 20.2% |
| **Durable Goods Share** | 10.8% |

---

## Generated Charts

The analysis pipeline produces 8 publication-quality PNG charts at 150 DPI.

### Chart 1: Headline vs. Core PCE Inflation (YoY)

Compares headline and core PCE inflation since 2015, with the Fed's 2% target line and COVID-19 recession shading.

![Headline vs Core PCE Inflation](https://app.devin.ai/attachments/5157e927-c663-4df7-ac5a-0ea7bd7bad2e/01_headline_vs_core_inflation.png)

---

### Chart 2: Multi-Horizon Inflation Dashboard

Side-by-side panels showing headline (left) and core (right) PCE inflation at 3-month, 6-month, and 12-month annualized horizons since 2020. Reveals momentum shifts before they appear in the 12-month rate.

![Multi-Horizon Inflation](https://app.devin.ai/attachments/b21ee4c5-c77a-422e-8aa7-724fb60a4031/02_multi_horizon_inflation.png)

---

### Chart 3: Nominal PCE — Level and Growth Rate

Dual-axis view of nominal spending (left axis, billions $) and YoY growth rate (right axis, %). Shows the relationship between absolute spending levels and growth dynamics.

![Nominal PCE Level and Growth](https://app.devin.ai/attachments/b35a956d-914a-457e-ae58-b11a10c41aec/03_nominal_pce_level_growth.png)

---

### Chart 4: Real PCE (Chained 2017 Dollars)

Inflation-adjusted consumer spending with dual-axis level and growth view. Isolates volume growth from price effects.

![Real PCE](https://app.devin.ai/attachments/a1b622c8-85e1-4350-9cdd-d9302cbc3ef9/04_real_pce.png)

---

### Chart 5: PCE Components — YoY Growth by Category

Tracks year-over-year growth for Durable Goods, Nondurable Goods, and Services since 2015. Highlights the divergent recovery patterns after COVID.

![PCE Components Growth](https://app.devin.ai/attachments/11c65153-6acf-42f7-83c0-27d99231664c/05_pce_components_growth.png)

---

### Chart 6: PCE Composition — Pie Chart and Historical Stacked Area

Left panel: current-month breakdown of spending by category. Right panel: evolution of category shares since 2000. Services dominate at ~69%.

![PCE Composition](https://app.devin.ai/attachments/51825a55-e14a-411a-a2fa-400e74afdc9b/06_pce_composition.png)

---

### Chart 7: Long-Run Inflation History (1960–Present)

Full historical view of headline and core PCE inflation with NBER recession shading. Provides context for the current cycle relative to the 1970s stagflation, Volcker disinflation, Great Moderation, and post-COVID surge.

![Long-Run Inflation History](https://app.devin.ai/attachments/8aec6b6e-2135-49fd-b5a7-788da8e82012/07_long_run_inflation_history.png)

---

### Chart 8: Monthly PCE Inflation (Annualized Bars)

Bar chart of the last 24 months of month-over-month annualized headline and core inflation. Highlights month-to-month volatility and recent trend direction relative to the 2% target.

![Monthly Inflation Bars](https://app.devin.ai/attachments/8de4495b-c67e-4150-b1c1-5062850b0bbf/08_monthly_inflation_bars.png)

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Data I/O | `urllib.request` | FRED CSV download (no external dependencies) |
| Data Processing | `pandas` | Time series loading, cleaning, metric computation |
| Visualization | `matplotlib` (Agg backend) | Non-interactive chart rendering for automation |
| Numerical | `numpy` | Array operations for bar chart positioning |

### Key Design Decisions

- **Agg Backend**: Matplotlib uses the non-interactive `Agg` backend, enabling headless execution in CI/CD, Docker containers, and remote servers.
- **Relative Pathing**: All paths derive from `SCRIPT_DIR` / `PROJECT_DIR`, so the pipeline works regardless of the working directory.
- **No API Key Required**: Data acquisition uses FRED's public CSV endpoint, removing authentication overhead.
- **Gitignored Artifacts**: Both `data/` and `output/` are gitignored — they are ephemeral and fully reproducible.

---

## Usage

```bash
# From the project root:

# 1. Download latest data from FRED
python pce_analytics/download_data.py

# 2. Run analysis and generate all charts + stats
python pce_analytics/analyze_pce.py

# Output:
#   output/charts/*.png   (8 charts)
#   output/stats.json     (key statistics)
```

### Dependencies

```
pandas
matplotlib
numpy
```

These are standard Python scientific computing libraries. Install via:

```bash
pip install pandas matplotlib numpy
```
