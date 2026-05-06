"""
Federal Reserve Policy Rate Corridor Analysis.

Replicates the FRED graph published at:
    https://fred.stlouisfed.org/graph/?g=1Ng5J

Produces a chart showing the Fed's rate corridor with all key money market
rates positioned between the upper and lower bounds of the federal funds
target range. Uses the Federal Reserve's official chart stylesheet.

Series plotted:
  - DFEDTARU: Federal Funds Target Range - Upper Limit (corridor ceiling)
  - SRFTSYD:  Standing Repo (SRP) Operations Rate
  - IORB:     Interest Rate on Reserve Balances
  - SOFR:     Secured Overnight Financing Rate
  - DFF:      Federal Funds Effective Rate
  - TGCRRATE: Tri-Party General Collateral Rate
  - RRPONTSYAWARD: Overnight Reverse Repurchase Agreements Award Rate
  - DFEDTARL: Federal Funds Target Range - Lower Limit (corridor floor)

Integrates with:
  - fredapi (https://github.com/FRB-demo/fredapi)
  - fred-mcp-server (https://github.com/FRB-demo/fred-mcp-server)

Usage:
    python fed-rates-corridor/download_rates.py   # fetch data first
    python fed-rates-corridor/analyze_rates.py    # generate chart
"""

import json
import os
import sys

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
CHART_PATH = os.path.join(OUTPUT_DIR, "fed_rates_corridor.png")
STATS_PATH = os.path.join(OUTPUT_DIR, "rates_summary.json")

# ---------------------------------------------------------------------------
# Federal Reserve Chart Stylesheet
# Matches the official FRED/Fed visual identity
# ---------------------------------------------------------------------------
FED_COLORS = {
    "DFEDTARU": "#1f4e79",  # Dark navy blue - upper bound
    "DFEDTARL": "#1f4e79",  # Dark navy blue - lower bound (same as upper)
    "SRFTSYD": "#c00000",  # Fed red - Standing Repo Rate
    "IORB": "#2e75b6",  # Medium blue - IORB
    "SOFR": "#548235",  # Forest green - SOFR
    "DFF": "#7030a0",  # Purple - Effective Fed Funds
    "TGCRRATE": "#ed7d31",  # Orange - Tri-Party GC Rate
    "RRPONTSYAWARD": "#70ad47",  # Light green - ON RRP Award Rate
}

FED_LABELS = {
    "DFEDTARU": "Federal Funds Target Range - Upper Limit",
    "DFEDTARL": "Federal Funds Target Range - Lower Limit",
    "SRFTSYD": "Standing Repo (SRP) Operations Rate",
    "IORB": "Interest Rate on Reserve Balances (IORB Rate)",
    "SOFR": "Secured Overnight Financing Rate",
    "DFF": "Federal Funds Effective Rate",
    "TGCRRATE": "Tri-Party General Collateral Rate",
    "RRPONTSYAWARD": "Overnight Reverse Repurchase Agreements Award Rate",
}

# Plot order (top to bottom within the corridor)
PLOT_ORDER = [
    "DFEDTARU",
    "SRFTSYD",
    "IORB",
    "SOFR",
    "DFF",
    "TGCRRATE",
    "RRPONTSYAWARD",
    "DFEDTARL",
]

# NBER recession periods for shading
RECESSIONS = [
    ("2001-03-01", "2001-11-01"),
    ("2007-12-01", "2009-06-01"),
    ("2020-02-01", "2020-04-01"),
]


# ---------------------------------------------------------------------------
# Fed Stylesheet - Matplotlib RC params
# ---------------------------------------------------------------------------
def apply_fed_stylesheet():
    """Apply Federal Reserve chart styling to matplotlib."""
    plt.rcParams.update(
        {
            "figure.figsize": (14, 7),
            "figure.dpi": 150,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#333333",
            "axes.linewidth": 0.8,
            "axes.titlesize": 14,
            "axes.titleweight": "bold",
            "axes.labelsize": 11,
            "axes.labelcolor": "#333333",
            "axes.grid": True,
            "grid.color": "#e0e0e0",
            "grid.linewidth": 0.5,
            "grid.linestyle": "-",
            "lines.linewidth": 1.8,
            "lines.antialiased": True,
            "font.family": "sans-serif",
            "font.sans-serif": [
                "Helvetica Neue",
                "Helvetica",
                "Arial",
                "DejaVu Sans",
            ],
            "font.size": 10,
            "xtick.color": "#333333",
            "ytick.color": "#333333",
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 8,
            "legend.framealpha": 0.95,
            "legend.edgecolor": "#cccccc",
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.3,
        }
    )


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------
def load_series(series_id: str) -> pd.DataFrame:
    """Load a FRED CSV from the data directory."""
    path = os.path.join(DATA_DIR, f"{series_id}.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Data file not found: {path}. Run download_rates.py first.")

    df = pd.read_csv(path, na_values=".")

    # Handle different column naming conventions from FRED CSV downloads
    date_col = None
    for candidate in ["observation_date", "DATE", "date"]:
        if candidate in df.columns:
            date_col = candidate
            break

    if date_col is None:
        # Assume first column is date
        date_col = df.columns[0]

    value_col = None
    for candidate in [series_id, series_id.upper(), series_id.lower()]:
        if candidate in df.columns:
            value_col = candidate
            break

    if value_col is None:
        # Assume second column is value
        value_col = df.columns[1]

    df = df[[date_col, value_col]].copy()
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna().set_index("date")
    return df


def load_all_series() -> dict:
    """Load all rate corridor series."""
    data = {}
    for series_id in PLOT_ORDER:
        try:
            data[series_id] = load_series(series_id)
        except FileNotFoundError as exc:
            print(f"  WARNING: {exc}")
    return data


# ---------------------------------------------------------------------------
# Chart Generation
# ---------------------------------------------------------------------------
def plot_rate_corridor(data: dict, output_path: str) -> None:
    """Generate the Fed rate corridor chart matching FRED's published graph."""
    apply_fed_stylesheet()

    fig, ax = plt.subplots()

    # Add recession shading
    for start, end in RECESSIONS:
        ax.axvspan(
            pd.Timestamp(start),
            pd.Timestamp(end),
            alpha=0.08,
            color="gray",
            zorder=0,
        )

    # Plot each series
    for series_id in PLOT_ORDER:
        if series_id not in data:
            continue
        df = data[series_id]
        line_style = "--" if series_id in ("DFEDTARU", "DFEDTARL") else "-"
        line_width = 2.2 if series_id in ("DFEDTARU", "DFEDTARL") else 1.6
        ax.plot(
            df.index,
            df["value"],
            color=FED_COLORS[series_id],
            linestyle=line_style,
            linewidth=line_width,
            label=FED_LABELS[series_id],
            zorder=2,
        )

    # Fill the target range corridor
    if "DFEDTARU" in data and "DFEDTARL" in data:
        upper = data["DFEDTARU"]
        lower = data["DFEDTARL"]
        merged = upper.join(lower, lsuffix="_upper", rsuffix="_lower", how="inner")
        ax.fill_between(
            merged.index,
            merged["value_lower"],
            merged["value_upper"],
            alpha=0.06,
            color="#1f4e79",
            zorder=1,
        )

    # Axis formatting
    ax.set_ylabel("Percent", fontsize=11, fontweight="bold")
    ax.set_xlabel("")
    ax.yaxis.set_major_locator(MultipleLocator(0.5))
    ax.yaxis.set_minor_locator(MultipleLocator(0.25))

    # Date axis formatting
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator(2))

    # Title and subtitle
    ax.set_title(
        "Federal Reserve Policy Rate Corridor",
        fontsize=14,
        fontweight="bold",
        loc="left",
        pad=12,
    )
    ax.text(
        0.0,
        1.02,
        "Daily rates, Percent, Not Seasonally Adjusted",
        transform=ax.transAxes,
        fontsize=9,
        color="#666666",
        va="bottom",
    )

    # Legend
    legend = ax.legend(
        loc="upper right",
        ncol=2,
        fontsize=7.5,
        framealpha=0.95,
        edgecolor="#cccccc",
        borderpad=0.8,
        columnspacing=1.5,
    )
    legend.get_frame().set_linewidth(0.5)

    # Source attribution (Fed style)
    fig.text(
        0.01,
        -0.02,
        "Sources: Board of Governors of the Federal Reserve System (US); "
        "Federal Reserve Bank of New York via FRED®",
        fontsize=7.5,
        color="#666666",
        ha="left",
    )
    fig.text(
        0.99,
        -0.02,
        "fred.stlouisfed.org",
        fontsize=7.5,
        color="#666666",
        ha="right",
    )

    # Recession footnote
    fig.text(
        0.01,
        -0.05,
        "Shaded areas indicate U.S. recessions.",
        fontsize=7,
        color="#888888",
        style="italic",
        ha="left",
    )

    # Clean up
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="both", which="both", length=4)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, dpi=150, facecolor="white")
    plt.close(fig)
    print(f"\nChart saved: {output_path}")


def plot_recent_corridor(data: dict, output_path: str) -> None:
    """Generate a 1-year view matching the default FRED graph display."""
    apply_fed_stylesheet()

    # Filter to last 1 year
    end_date = pd.Timestamp.now()
    start_date = end_date - pd.DateOffset(years=1)

    recent_data = {}
    for series_id, df in data.items():
        mask = df.index >= start_date
        if mask.any():
            recent_data[series_id] = df[mask]

    fig, ax = plt.subplots()

    # Plot each series
    for series_id in PLOT_ORDER:
        if series_id not in recent_data:
            continue
        df = recent_data[series_id]
        line_style = "--" if series_id in ("DFEDTARU", "DFEDTARL") else "-"
        line_width = 2.2 if series_id in ("DFEDTARU", "DFEDTARL") else 1.6
        ax.plot(
            df.index,
            df["value"],
            color=FED_COLORS[series_id],
            linestyle=line_style,
            linewidth=line_width,
            label=FED_LABELS[series_id],
            zorder=2,
        )

    # Fill corridor
    if "DFEDTARU" in recent_data and "DFEDTARL" in recent_data:
        upper = recent_data["DFEDTARU"]
        lower = recent_data["DFEDTARL"]
        merged = upper.join(lower, lsuffix="_upper", rsuffix="_lower", how="inner")
        ax.fill_between(
            merged.index,
            merged["value_lower"],
            merged["value_upper"],
            alpha=0.06,
            color="#1f4e79",
            zorder=1,
        )

    ax.set_ylabel("Percent", fontsize=11, fontweight="bold")
    ax.set_xlabel("")
    ax.yaxis.set_major_locator(MultipleLocator(0.25))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))

    ax.set_title(
        "Federal Reserve Policy Rate Corridor (1-Year View)",
        fontsize=14,
        fontweight="bold",
        loc="left",
        pad=12,
    )
    ax.text(
        0.0,
        1.02,
        "Daily rates, Percent, Not Seasonally Adjusted",
        transform=ax.transAxes,
        fontsize=9,
        color="#666666",
        va="bottom",
    )

    legend = ax.legend(
        loc="lower left",
        ncol=2,
        fontsize=7.5,
        framealpha=0.95,
        edgecolor="#cccccc",
        borderpad=0.8,
        columnspacing=1.5,
    )
    legend.get_frame().set_linewidth(0.5)

    fig.text(
        0.01,
        -0.02,
        "Sources: Board of Governors of the Federal Reserve System (US); "
        "Federal Reserve Bank of New York via FRED®",
        fontsize=7.5,
        color="#666666",
        ha="left",
    )
    fig.text(
        0.99,
        -0.02,
        "fred.stlouisfed.org",
        fontsize=7.5,
        color="#666666",
        ha="right",
    )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="both", which="both", length=4)

    recent_path = output_path.replace(".png", "_1yr.png")
    os.makedirs(os.path.dirname(recent_path), exist_ok=True)
    fig.savefig(recent_path, dpi=150, facecolor="white")
    plt.close(fig)
    print(f"Chart saved: {recent_path}")


# ---------------------------------------------------------------------------
# Summary Statistics
# ---------------------------------------------------------------------------
def compute_summary(data: dict) -> dict:
    """Compute summary statistics for the rate corridor."""
    stats = {}

    for series_id, df in data.items():
        if df.empty:
            continue
        latest = df.iloc[-1]["value"]
        stats[series_id] = {
            "label": FED_LABELS[series_id],
            "latest_value": round(float(latest), 2),
            "latest_date": df.index[-1].strftime("%Y-%m-%d"),
            "min_value": round(float(df["value"].min()), 2),
            "max_value": round(float(df["value"].max()), 2),
            "mean_value": round(float(df["value"].mean()), 4),
        }

    # Corridor width
    if "DFEDTARU" in data and "DFEDTARL" in data:
        upper_latest = data["DFEDTARU"].iloc[-1]["value"]
        lower_latest = data["DFEDTARL"].iloc[-1]["value"]
        stats["corridor_width_bps"] = round((upper_latest - lower_latest) * 100, 0)
        stats["current_target_range"] = f"{lower_latest:.2f}% - {upper_latest:.2f}%"

    return stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    """Run the full analysis pipeline."""
    print("=" * 60)
    print("Federal Reserve Policy Rate Corridor Analysis")
    print("Replicating: https://fred.stlouisfed.org/graph/?g=1Ng5J")
    print("=" * 60)
    print()

    # Load data
    print("Loading data...")
    data = load_all_series()

    if not data:
        print("ERROR: No data loaded. Run download_rates.py first.", file=sys.stderr)
        sys.exit(1)

    print(f"  Loaded {len(data)} series\n")

    # Generate charts
    print("Generating charts...")
    plot_rate_corridor(data, CHART_PATH)
    plot_recent_corridor(data, CHART_PATH)

    # Compute and save summary
    print("\nComputing summary statistics...")
    stats = compute_summary(data)
    os.makedirs(os.path.dirname(STATS_PATH), exist_ok=True)
    with open(STATS_PATH, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"Summary saved: {STATS_PATH}")

    # Print current rates
    print("\n" + "=" * 60)
    print("Current Federal Reserve Policy Rate Corridor")
    print("=" * 60)
    if "current_target_range" in stats:
        print(f"  Target Range: {stats['current_target_range']}")
        print(f"  Corridor Width: {stats['corridor_width_bps']:.0f} bps")
    print()
    for series_id in PLOT_ORDER:
        if series_id in stats:
            s = stats[series_id]
            print(f"  {s['label']}: {s['latest_value']:.2f}% ({s['latest_date']})")
    print()


if __name__ == "__main__":
    main()
