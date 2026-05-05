# PCE Analytics

Data pipeline for Personal Consumption Expenditures (PCE) analysis using FRED macroeconomic data.

## Quick Start

```bash
# From the project root
python pce_analytics/download_data.py   # Fetch data from FRED
python pce_analytics/analyze_pce.py     # Generate charts + stats
```

## Contents

| File | Description |
|------|-------------|
| `download_data.py` | Downloads 7 FRED series (PCE, PCEPI, PCEPILFE, PCEC96, PCEDG, PCEND, PCES) |
| `analyze_pce.py` | Computes inflation metrics and generates 8 publication-quality charts |
| `TECHNICAL_SUMMARY.md` | Detailed technical documentation with analysis screenshots |

## Output

- `output/charts/` — 8 PNG charts (150 DPI)
- `output/stats.json` — Machine-readable key statistics

See [TECHNICAL_SUMMARY.md](TECHNICAL_SUMMARY.md) for full documentation.
