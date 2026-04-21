"""
Analyze PCE data and generate charts for the economic report.

Reads CSV data from data/ directory (downloaded by download_data.py),
computes inflation metrics at multiple horizons, and produces 8 charts
in the output/charts/ directory along with a JSON summary of key statistics.

Usage:
    python download_data.py   # first, fetch data from FRED
    python analyze_pce.py     # then, run this script
"""

import os
import json

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np


# ---------------------------------------------------------------------------
# Paths (relative to this script's directory)
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output", "charts")
STATS_PATH = os.path.join(SCRIPT_DIR, "output", "stats.json")

# ---------------------------------------------------------------------------
# Matplotlib defaults
# ---------------------------------------------------------------------------
plt.rcParams.update({
    "figure.figsize": (12, 6),
    "font.size": 12,
    "axes.titlesize": 14,
    "axes.labelsize": 12,
    "lines.linewidth": 2,
    "figure.dpi": 150,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.3,
})

# NBER recession date ranges for chart shading
RECESSIONS = [
    ("1960-04-01", "1961-02-01"),
    ("1969-12-01", "1970-11-01"),
    ("1973-11-01", "1975-03-01"),
    ("1980-01-01", "1980-07-01"),
    ("1981-07-01", "1982-11-01"),
    ("1990-07-01", "1991-03-01"),
    ("2001-03-01", "2001-11-01"),
    ("2007-12-01", "2009-06-01"),
    ("2020-02-01", "2020-04-01"),
]


# ===================================================================
# Helper functions
# ===================================================================

def load_series(name: str) -> pd.DataFrame:
    """Load a FRED CSV from the data directory."""
    path = os.path.join(DATA_DIR, f"{name}.csv")
    df = pd.read_csv(path, parse_dates=["observation_date"], na_values=".")
    df = df.rename(columns={"observation_date": "date"}).dropna().set_index("date")
    return df


def add_recession_shading(ax):
    """Add gray NBER recession bars to an axes."""
    for start, end in RECESSIONS:
        ax.axvspan(pd.Timestamp(start), pd.Timestamp(end), alpha=0.1, color="gray")


# ===================================================================
# Data loading & computation
# ===================================================================

def load_all_data():
    """Load all PCE series and compute derived metrics."""
    pce = load_series("PCE")
    pcepi = load_series("PCEPI")
    pcepilfe = load_series("PCEPILFE")
    pcedg = load_series("PCEDG")
    pcend = load_series("PCEND")
    pces = load_series("PCES")
    pcec96 = load_series("PCEC96")

    # Year-over-year % change
    pcepi["pct_yoy"] = pcepi["PCEPI"].pct_change(12) * 100
    pcepilfe["pct_yoy"] = pcepilfe["PCEPILFE"].pct_change(12) * 100
    pce["pct_yoy"] = pce["PCE"].pct_change(12) * 100
    pcec96["pct_yoy"] = pcec96["PCEC96"].pct_change(12) * 100
    pcedg["pct_yoy"] = pcedg["PCEDG"].pct_change(12) * 100
    pcend["pct_yoy"] = pcend["PCEND"].pct_change(12) * 100
    pces["pct_yoy"] = pces["PCES"].pct_change(12) * 100

    # Month-over-month annualized
    pcepi["pct_mom_ann"] = ((1 + pcepi["PCEPI"].pct_change(1)) ** 12 - 1) * 100
    pcepilfe["pct_mom_ann"] = ((1 + pcepilfe["PCEPILFE"].pct_change(1)) ** 12 - 1) * 100

    # 3-month annualized
    pcepi["pct_3m_ann"] = ((pcepi["PCEPI"] / pcepi["PCEPI"].shift(3)) ** (12 / 3) - 1) * 100
    pcepilfe["pct_3m_ann"] = ((pcepilfe["PCEPILFE"] / pcepilfe["PCEPILFE"].shift(3)) ** (12 / 3) - 1) * 100

    # 6-month annualized
    pcepi["pct_6m_ann"] = ((pcepi["PCEPI"] / pcepi["PCEPI"].shift(6)) ** (12 / 6) - 1) * 100
    pcepilfe["pct_6m_ann"] = ((pcepilfe["PCEPILFE"] / pcepilfe["PCEPILFE"].shift(6)) ** (12 / 6) - 1) * 100

    return {
        "pce": pce,
        "pcepi": pcepi,
        "pcepilfe": pcepilfe,
        "pcedg": pcedg,
        "pcend": pcend,
        "pces": pces,
        "pcec96": pcec96,
    }


def compute_stats(data: dict) -> dict:
    """Compute key summary statistics for the report."""
    pce = data["pce"]
    pcepi = data["pcepi"]
    pcepilfe = data["pcepilfe"]
    pcec96 = data["pcec96"]
    pcedg = data["pcedg"]
    pcend = data["pcend"]
    pces = data["pces"]

    total = pce["PCE"].iloc[-1]

    return {
        "latest_date": pce.index[-1].strftime("%B %Y"),
        "pce_level": f"{pce['PCE'].iloc[-1]:,.1f}",
        "pce_yoy": f"{pce['pct_yoy'].iloc[-1]:.1f}",
        "real_pce_level": f"{pcec96['PCEC96'].iloc[-1]:,.1f}",
        "real_pce_yoy": f"{pcec96['pct_yoy'].iloc[-1]:.1f}",
        "pcepi_level": f"{pcepi['PCEPI'].iloc[-1]:.3f}",
        "headline_yoy": f"{pcepi['pct_yoy'].iloc[-1]:.1f}",
        "headline_mom_ann": f"{pcepi['pct_mom_ann'].iloc[-1]:.1f}",
        "headline_3m_ann": f"{pcepi['pct_3m_ann'].iloc[-1]:.1f}",
        "headline_6m_ann": f"{pcepi['pct_6m_ann'].iloc[-1]:.1f}",
        "core_level": f"{pcepilfe['PCEPILFE'].iloc[-1]:.3f}",
        "core_yoy": f"{pcepilfe['pct_yoy'].iloc[-1]:.1f}",
        "core_mom_ann": f"{pcepilfe['pct_mom_ann'].iloc[-1]:.1f}",
        "core_3m_ann": f"{pcepilfe['pct_3m_ann'].iloc[-1]:.1f}",
        "core_6m_ann": f"{pcepilfe['pct_6m_ann'].iloc[-1]:.1f}",
        "dg_share": f"{pcedg['PCEDG'].iloc[-1] / total * 100:.1f}",
        "nd_share": f"{pcend['PCEND'].iloc[-1] / total * 100:.1f}",
        "sv_share": f"{pces['PCES'].iloc[-1] / total * 100:.1f}",
        "dg_yoy": f"{pcedg['pct_yoy'].iloc[-1]:.1f}",
        "nd_yoy": f"{pcend['pct_yoy'].iloc[-1]:.1f}",
        "sv_yoy": f"{pces['pct_yoy'].iloc[-1]:.1f}",
        "prev_headline_yoy": f"{pcepi['pct_yoy'].iloc[-2]:.1f}",
        "prev_core_yoy": f"{pcepilfe['pct_yoy'].iloc[-2]:.1f}",
        "prev_date": pce.index[-2].strftime("%B %Y"),
    }


# ===================================================================
# Chart functions
# ===================================================================

def chart_headline_vs_core(data: dict) -> None:
    """Chart 1: Headline vs Core PCE Inflation (YoY), 2015-present."""
    pcepi = data["pcepi"]
    pcepilfe = data["pcepilfe"]

    fig, ax = plt.subplots(figsize=(14, 7))
    start = "2015-01-01"
    mask_h = pcepi.index >= start
    mask_c = pcepilfe.index >= start

    ax.plot(pcepi.index[mask_h], pcepi["pct_yoy"][mask_h],
            color="#1f77b4", label="Headline PCE Inflation (YoY)", linewidth=2.5)
    ax.plot(pcepilfe.index[mask_c], pcepilfe["pct_yoy"][mask_c],
            color="#d62728", label="Core PCE Inflation (YoY)", linewidth=2.5)
    ax.axhline(y=2.0, color="green", linestyle="--", linewidth=1.5, alpha=0.7,
               label="Fed 2% Target")
    ax.fill_between(pcepi.index[mask_h], 0, pcepi["pct_yoy"][mask_h],
                    alpha=0.05, color="#1f77b4")
    ax.axvspan(pd.Timestamp("2020-02-01"), pd.Timestamp("2020-04-01"),
               alpha=0.15, color="gray", label="Recession")

    ax.set_title("PCE Inflation: Headline vs. Core (Year-over-Year %)",
                 fontsize=16, fontweight="bold")
    ax.set_ylabel("Percent Change (YoY)", fontsize=13)
    ax.legend(loc="upper left", fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    plt.xticks(rotation=45)

    fig.savefig(os.path.join(OUTPUT_DIR, "01_headline_vs_core_inflation.png"))
    plt.close()
    print("  Chart 1: Headline vs Core Inflation")


def chart_multi_horizon(data: dict) -> None:
    """Chart 2: Multi-horizon inflation dashboard (headline & core)."""
    pcepi = data["pcepi"]
    pcepilfe = data["pcepilfe"]

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    recent = "2020-01-01"

    # Headline panel
    ax = axes[0]
    mask = pcepi.index >= recent
    ax.plot(pcepi.index[mask], pcepi["pct_yoy"][mask],
            label="12-month", linewidth=2.5, color="#1f77b4")
    ax.plot(pcepi.index[mask], pcepi["pct_6m_ann"][mask],
            label="6-month annualized", linewidth=2, color="#ff7f0e", alpha=0.8)
    ax.plot(pcepi.index[mask], pcepi["pct_3m_ann"][mask],
            label="3-month annualized", linewidth=1.5, color="#2ca02c", alpha=0.7)
    ax.axhline(y=2.0, color="red", linestyle="--", linewidth=1.5, alpha=0.6)
    ax.set_title("Headline PCE Inflation\n(Multiple Horizons)",
                 fontsize=14, fontweight="bold")
    ax.set_ylabel("Percent (Annualized)")
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    # Core panel
    ax = axes[1]
    mask = pcepilfe.index >= recent
    ax.plot(pcepilfe.index[mask], pcepilfe["pct_yoy"][mask],
            label="12-month", linewidth=2.5, color="#d62728")
    ax.plot(pcepilfe.index[mask], pcepilfe["pct_6m_ann"][mask],
            label="6-month annualized", linewidth=2, color="#9467bd", alpha=0.8)
    ax.plot(pcepilfe.index[mask], pcepilfe["pct_3m_ann"][mask],
            label="3-month annualized", linewidth=1.5, color="#8c564b", alpha=0.7)
    ax.axhline(y=2.0, color="red", linestyle="--", linewidth=1.5, alpha=0.6)
    ax.set_title("Core PCE Inflation\n(Multiple Horizons)",
                 fontsize=14, fontweight="bold")
    ax.set_ylabel("Percent (Annualized)")
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "02_multi_horizon_inflation.png"))
    plt.close()
    print("  Chart 2: Multi-Horizon Inflation")


def chart_nominal_pce(data: dict) -> None:
    """Chart 3: Nominal PCE level and YoY growth."""
    pce = data["pce"]

    fig, ax1 = plt.subplots(figsize=(14, 7))
    mask = pce.index >= "2015-01-01"
    color1 = "#1f77b4"

    ax1.fill_between(pce.index[mask], 0, pce["PCE"][mask], alpha=0.2, color=color1)
    ax1.plot(pce.index[mask], pce["PCE"][mask], color=color1, linewidth=2.5,
             label="Nominal PCE (left)")
    ax1.set_ylabel("Billions of Dollars", color=color1, fontsize=13)
    ax1.tick_params(axis="y", labelcolor=color1)

    ax2 = ax1.twinx()
    color2 = "#d62728"
    ax2.plot(pce.index[mask], pce["pct_yoy"][mask], color=color2, linewidth=2,
             alpha=0.8, label="YoY Growth % (right)")
    ax2.set_ylabel("Year-over-Year % Change", color=color2, fontsize=13)
    ax2.tick_params(axis="y", labelcolor=color2)
    ax2.axhline(y=0, color="gray", linestyle="-", linewidth=0.5)

    ax1.set_title("Personal Consumption Expenditures: Level and Growth Rate",
                  fontsize=16, fontweight="bold")
    ax1.grid(True, alpha=0.3)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=11)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    fig.savefig(os.path.join(OUTPUT_DIR, "03_nominal_pce_level_growth.png"))
    plt.close()
    print("  Chart 3: Nominal PCE Level & Growth")


def chart_real_pce(data: dict) -> None:
    """Chart 4: Real PCE (chained 2017 dollars) level and growth."""
    pcec96 = data["pcec96"]

    fig, ax1 = plt.subplots(figsize=(14, 7))
    mask = pcec96.index >= "2015-01-01"

    ax1.fill_between(pcec96.index[mask], 0, pcec96["PCEC96"][mask],
                     alpha=0.15, color="#2ca02c")
    ax1.plot(pcec96.index[mask], pcec96["PCEC96"][mask], color="#2ca02c",
             linewidth=2.5, label="Real PCE (left)")
    ax1.set_ylabel("Billions of Chained 2017 Dollars", color="#2ca02c", fontsize=13)
    ax1.tick_params(axis="y", labelcolor="#2ca02c")

    ax2 = ax1.twinx()
    ax2.plot(pcec96.index[mask], pcec96["pct_yoy"][mask], color="#d62728",
             linewidth=2, alpha=0.8, label="YoY Growth % (right)")
    ax2.set_ylabel("Year-over-Year % Change", color="#d62728", fontsize=13)
    ax2.tick_params(axis="y", labelcolor="#d62728")
    ax2.axhline(y=0, color="gray", linestyle="-", linewidth=0.5)

    ax1.set_title("Real Personal Consumption Expenditures (Chained 2017 Dollars)",
                  fontsize=16, fontweight="bold")
    ax1.grid(True, alpha=0.3)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=11)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    fig.savefig(os.path.join(OUTPUT_DIR, "04_real_pce.png"))
    plt.close()
    print("  Chart 4: Real PCE")


def chart_components_growth(data: dict) -> None:
    """Chart 5: PCE component YoY growth (durables, nondurables, services)."""
    pcedg = data["pcedg"]
    pcend = data["pcend"]
    pces = data["pces"]

    fig, ax = plt.subplots(figsize=(14, 7))
    start = "2015-01-01"

    ax.plot(pcedg.index[pcedg.index >= start],
            pcedg["pct_yoy"][pcedg.index >= start],
            label="Durable Goods (YoY)", linewidth=2, color="#1f77b4")
    ax.plot(pcend.index[pcend.index >= start],
            pcend["pct_yoy"][pcend.index >= start],
            label="Nondurable Goods (YoY)", linewidth=2, color="#ff7f0e")
    ax.plot(pces.index[pces.index >= start],
            pces["pct_yoy"][pces.index >= start],
            label="Services (YoY)", linewidth=2, color="#2ca02c")

    ax.axhline(y=0, color="gray", linestyle="-", linewidth=0.5)
    ax.axvspan(pd.Timestamp("2020-02-01"), pd.Timestamp("2020-04-01"),
               alpha=0.15, color="gray")

    ax.set_title("PCE Components: Year-over-Year Growth by Category",
                 fontsize=16, fontweight="bold")
    ax.set_ylabel("Percent Change (YoY)", fontsize=13)
    ax.legend(loc="upper left", fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    plt.xticks(rotation=45)

    fig.savefig(os.path.join(OUTPUT_DIR, "05_pce_components_growth.png"))
    plt.close()
    print("  Chart 5: Component Growth")


def chart_composition(data: dict) -> None:
    """Chart 6: PCE composition pie chart and historical stacked area."""
    pcedg = data["pcedg"]
    pcend = data["pcend"]
    pces = data["pces"]
    latest_date = data["pce"].index[-1].strftime("%B %Y")

    dg = pcedg["PCEDG"].iloc[-1]
    nd = pcend["PCEND"].iloc[-1]
    sv = pces["PCES"].iloc[-1]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    labels = ["Durable\nGoods", "Nondurable\nGoods", "Services"]
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]

    wedges, texts, autotexts = ax1.pie(
        [dg, nd, sv], explode=(0.02, 0.02, 0.05), labels=labels,
        colors=colors, autopct="%1.1f%%", shadow=False, startangle=90,
        textprops={"fontsize": 12},
    )
    for at in autotexts:
        at.set_fontsize(11)
        at.set_fontweight("bold")
    ax1.set_title(f"PCE Composition ({latest_date})", fontsize=14, fontweight="bold")

    merged = pd.DataFrame({
        "Durable Goods": pcedg["PCEDG"],
        "Nondurable Goods": pcend["PCEND"],
        "Services": pces["PCES"],
    }).dropna()
    merged = merged[merged.index >= "2000-01-01"]
    total = merged.sum(axis=1)
    shares = merged.div(total, axis=0) * 100

    ax2.stackplot(
        shares.index,
        shares["Durable Goods"], shares["Nondurable Goods"], shares["Services"],
        labels=["Durable Goods", "Nondurable Goods", "Services"],
        colors=colors, alpha=0.8,
    )
    ax2.set_title("PCE Composition Over Time (%)", fontsize=14, fontweight="bold")
    ax2.set_ylabel("Share of Total PCE (%)")
    ax2.legend(loc="center right", fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax2.set_ylim(0, 100)

    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "06_pce_composition.png"))
    plt.close()
    print("  Chart 6: PCE Composition")


def chart_long_run_history(data: dict) -> None:
    """Chart 7: Long-run PCE inflation history (1960-present) with recessions."""
    pcepi = data["pcepi"]
    pcepilfe = data["pcepilfe"]

    fig, ax = plt.subplots(figsize=(14, 7))
    h = pcepi["pct_yoy"].dropna()
    c = pcepilfe["pct_yoy"].dropna()

    ax.plot(h.index, h, color="#1f77b4", linewidth=1.5, alpha=0.8, label="Headline PCE")
    ax.plot(c.index, c, color="#d62728", linewidth=1.5, alpha=0.8, label="Core PCE")
    ax.axhline(y=2.0, color="green", linestyle="--", linewidth=1.5, alpha=0.7,
               label="Fed 2% Target")
    add_recession_shading(ax)

    ax.set_title("PCE Inflation: Long-Run Historical Perspective (1960-Present)",
                 fontsize=16, fontweight="bold")
    ax.set_ylabel("Percent Change (YoY)", fontsize=13)
    ax.legend(loc="upper right", fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator(5))

    fig.savefig(os.path.join(OUTPUT_DIR, "07_long_run_inflation_history.png"))
    plt.close()
    print("  Chart 7: Long-Run History")


def chart_monthly_bars(data: dict) -> None:
    """Chart 8: Last 24 months of MoM annualized inflation (bar chart)."""
    pcepi = data["pcepi"]
    pcepilfe = data["pcepilfe"]

    fig, ax = plt.subplots(figsize=(14, 7))
    recent_h = pcepi["pct_mom_ann"].iloc[-24:]
    recent_c = pcepilfe["pct_mom_ann"].iloc[-24:]

    x = np.arange(len(recent_h))
    width = 0.35
    ax.bar(x - width / 2, recent_h, width, label="Headline (MoM Ann.)",
           color="#1f77b4", alpha=0.8)
    ax.bar(x + width / 2, recent_c, width, label="Core (MoM Ann.)",
           color="#d62728", alpha=0.8)
    ax.axhline(y=2.0, color="green", linestyle="--", linewidth=1.5, alpha=0.7)
    ax.axhline(y=0, color="gray", linestyle="-", linewidth=0.5)

    ax.set_title("Monthly PCE Inflation (Annualized)", fontsize=16, fontweight="bold")
    ax.set_ylabel("Percent (Annualized)", fontsize=13)
    ax.set_xticks(x[::2])
    ax.set_xticklabels([d.strftime("%b\n%Y") for d in recent_h.index[::2]], fontsize=9)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, axis="y")

    fig.savefig(os.path.join(OUTPUT_DIR, "08_monthly_inflation_bars.png"))
    plt.close()
    print("  Chart 8: Monthly Inflation Bars")


# ===================================================================
# Main
# ===================================================================

def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Loading data...")
    data = load_all_data()

    print("\nComputing statistics...")
    stats = compute_stats(data)
    for k, v in stats.items():
        print(f"  {k}: {v}")

    os.makedirs(os.path.dirname(STATS_PATH), exist_ok=True)
    with open(STATS_PATH, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"\nStatistics saved to {STATS_PATH}")

    print("\nGenerating charts...")
    chart_headline_vs_core(data)
    chart_multi_horizon(data)
    chart_nominal_pce(data)
    chart_real_pce(data)
    chart_components_growth(data)
    chart_composition(data)
    chart_long_run_history(data)
    chart_monthly_bars(data)

    print(f"\nAll 8 charts saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
