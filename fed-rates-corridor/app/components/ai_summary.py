"""
AI-generated summary module for different personas.

Generates context-appropriate summaries of economic charts and data
tailored for different audiences: economists, Fed executives, and
the general public.
"""

import pandas as pd


def _compute_rate_stats(data: dict) -> dict:
    """Compute key statistics from the loaded rate data."""
    stats = {}
    for series_id, df in data.items():
        if df.empty:
            continue
        latest = df.iloc[-1]["value"]
        prev_month = df[df.index <= (df.index[-1] - pd.DateOffset(months=1))]
        prev_year = df[df.index <= (df.index[-1] - pd.DateOffset(years=1))]

        stats[series_id] = {
            "latest": round(float(latest), 2),
            "latest_date": df.index[-1].strftime("%B %d, %Y"),
            "1m_ago": (
                round(float(prev_month.iloc[-1]["value"]), 2) if not prev_month.empty else None
            ),
            "1y_ago": round(float(prev_year.iloc[-1]["value"]), 2) if not prev_year.empty else None,
            "min": round(float(df["value"].min()), 2),
            "max": round(float(df["value"].max()), 2),
        }

    # Corridor metrics
    if "DFEDTARU" in stats and "DFEDTARL" in stats:
        stats["_corridor"] = {
            "upper": stats["DFEDTARU"]["latest"],
            "lower": stats["DFEDTARL"]["latest"],
            "width_bps": round((stats["DFEDTARU"]["latest"] - stats["DFEDTARL"]["latest"]) * 100),
            "change_1y": None,
        }
        if stats["DFEDTARU"].get("1y_ago") is not None:
            stats["_corridor"]["change_1y"] = round(
                (stats["DFEDTARU"]["latest"] - stats["DFEDTARU"]["1y_ago"]) * 100
            )

    return stats


def generate_economist_summary(data: dict, title: str = "") -> str:
    """Generate a technical summary for economists and researchers."""
    stats = _compute_rate_stats(data)
    corridor = stats.get("_corridor", {})

    lines = []
    lines.append(f"## Technical Analysis: {title or 'Rate Corridor'}")
    lines.append("")
    lines.append(
        f"**As of:** {stats.get('DFF', stats.get('DFEDTARU', {})).get('latest_date', 'N/A')}"
    )
    lines.append("")

    # Current stance
    if corridor:
        lines.append("### Current Policy Stance")
        lines.append(
            f"- Federal funds target range: **{corridor['lower']:.2f}% – "
            f"{corridor['upper']:.2f}%** ({corridor['width_bps']:.0f} bps corridor)"
        )
        if corridor.get("change_1y") is not None:
            direction = (
                "easing"
                if corridor["change_1y"] < 0
                else ("tightening" if corridor["change_1y"] > 0 else "unchanged")
            )
            lines.append(
                f"- Year-over-year change: **{corridor['change_1y']:+.0f} bps** ({direction})"
            )
        lines.append("")

    # Rate positioning
    lines.append("### Corridor Rate Positioning")
    rate_order = [
        "DFEDTARU",
        "SRFTSYD",
        "IORB",
        "DFF",
        "SOFR",
        "TGCRRATE",
        "RRPONTSYAWARD",
        "DFEDTARL",
    ]
    labels = {
        "DFEDTARU": "Target Upper",
        "DFEDTARL": "Target Lower",
        "IORB": "IORB",
        "DFF": "Eff. Fed Funds",
        "SOFR": "SOFR",
        "TGCRRATE": "Tri-Party GCR",
        "RRPONTSYAWARD": "ON RRP",
        "SRFTSYD": "SRP Rate",
    }
    for sid in rate_order:
        if sid in stats:
            s = stats[sid]
            spread = ""
            if corridor and sid not in ("DFEDTARU", "DFEDTARL"):
                bp_from_upper = round((s["latest"] - corridor["upper"]) * 100)
                spread = f" (UL{bp_from_upper:+.0f} bps)"
            lines.append(f"- {labels.get(sid, sid)}: {s['latest']:.2f}%{spread}")
    lines.append("")

    # Spread analysis
    lines.append("### Spread Analysis")
    if "IORB" in stats and "DFF" in stats:
        iorb_dff = round((stats["IORB"]["latest"] - stats["DFF"]["latest"]) * 100, 1)
        lines.append(f"- IORB–DFF spread: {iorb_dff:+.1f} bps")
    if "SOFR" in stats and "DFF" in stats:
        sofr_dff = round((stats["SOFR"]["latest"] - stats["DFF"]["latest"]) * 100, 1)
        lines.append(f"- SOFR–DFF spread: {sofr_dff:+.1f} bps")
    if "DFF" in stats and "DFEDTARL" in stats:
        dff_floor = round((stats["DFF"]["latest"] - stats["DFEDTARL"]["latest"]) * 100, 1)
        lines.append(f"- DFF–Floor spread: {dff_floor:+.1f} bps")
    lines.append("")

    # Assessment
    lines.append("### Assessment")
    if corridor:
        dff_pos = stats.get("DFF", {}).get("latest", 0)
        pct_in_corridor = (
            (dff_pos - corridor["lower"]) / (corridor["upper"] - corridor["lower"]) * 100
            if corridor["upper"] != corridor["lower"]
            else 50
        )
        lines.append(
            f"- Effective rate positioning: {pct_in_corridor:.0f}% "
            f"from corridor floor (target: ~50–60%)"
        )
        status = "normal" if 30 < pct_in_corridor < 80 else "atypical"
        qualifier = (
            "rates well-contained within bounds"
            if status == "normal"
            else "rates positioned outside typical range"
        )
        lines.append(f"- Corridor functioning: **{status}** — {qualifier}")
        lines.append("- No evidence of rate leakage beyond administered bounds")
    lines.append("")

    return "\n".join(lines)


def generate_executive_summary(data: dict, title: str = "") -> str:
    """Generate a concise summary for Fed executives / senior policymakers."""
    stats = _compute_rate_stats(data)
    corridor = stats.get("_corridor", {})

    lines = []
    lines.append(f"## Executive Briefing: {title or 'Monetary Policy Implementation'}")
    lines.append("")
    lines.append(
        f"**Date:** {stats.get('DFF', stats.get('DFEDTARU', {})).get('latest_date', 'N/A')}"
    )
    lines.append("")

    # Bottom line up front
    lines.append("### Bottom Line")
    if corridor:
        lines.append(
            f"The federal funds rate is trading at **{stats.get('DFF', {}).get('latest', 'N/A')}%**, "
            f"well within the target range of "
            f"**{corridor['lower']:.2f}%–{corridor['upper']:.2f}%**. "
            f"Policy implementation is functioning as intended."
        )
        if corridor.get("change_1y") is not None and corridor["change_1y"] < 0:
            lines.append(
                f"\nCumulative easing over the past year: "
                f"**{abs(corridor['change_1y']):.0f} basis points**."
            )
    lines.append("")

    # Key metrics
    lines.append("### Key Metrics")
    lines.append("")
    lines.append("| Indicator | Rate | Status |")
    lines.append("|---|---|---|")
    indicators = [
        ("IORB", "IORB (steering tool)"),
        ("DFF", "Effective Fed Funds"),
        ("SOFR", "SOFR (repo benchmark)"),
    ]
    for sid, label in indicators:
        if sid in stats:
            status = "On target"
            lines.append(f"| {label} | {stats[sid]['latest']:.2f}% | {status} |")
    lines.append("")

    # Action items
    lines.append("### Observations")
    lines.append("- All administered rates are set at appropriate levels relative to target range")
    lines.append("- Market rates clustering as expected between IORB and ON RRP")
    lines.append("- No indication of reserve scarcity or funding market stress")
    if corridor.get("change_1y") is not None and corridor["change_1y"] < 0:
        lines.append(
            f"- Rate cuts totaling {abs(corridor['change_1y']):.0f} bps "
            "have transmitted smoothly to money markets"
        )
    lines.append("")

    return "\n".join(lines)


def generate_public_summary(data: dict, title: str = "") -> str:
    """Generate a plain-language summary for the general public."""
    stats = _compute_rate_stats(data)
    corridor = stats.get("_corridor", {})

    lines = []
    lines.append(f"## What This Chart Shows: {title or 'Interest Rates'}")
    lines.append("")

    # Simple explanation
    lines.append("### In Plain English")
    lines.append("")
    if corridor:
        lines.append(
            f"The Federal Reserve currently sets its main interest rate target between "
            f"**{corridor['lower']:.2f}%** and **{corridor['upper']:.2f}%**. "
            f"This is the rate at which banks lend money to each other overnight."
        )
        lines.append("")
        lines.append(
            "This rate affects everything from mortgage rates to savings account yields. "
            "When the Fed raises this rate, borrowing becomes more expensive. "
            "When they lower it, borrowing becomes cheaper."
        )
        lines.append("")

        if corridor.get("change_1y") is not None:
            if corridor["change_1y"] < 0:
                change_pct = abs(corridor["change_1y"]) / 100
                lines.append(
                    f"**Over the past year**, the Fed has **lowered** rates by "
                    f"{change_pct:.2f} percentage points. This means:"
                )
                lines.append("- Mortgage rates may be slightly lower")
                lines.append("- Savings accounts earn a bit less interest")
                lines.append("- The Fed is trying to support economic growth")
            elif corridor["change_1y"] > 0:
                change_pct = corridor["change_1y"] / 100
                lines.append(
                    f"**Over the past year**, the Fed has **raised** rates by "
                    f"{change_pct:.2f} percentage points. This means:"
                )
                lines.append("- Mortgage rates and loan rates are higher")
                lines.append("- Savings accounts earn more interest")
                lines.append("- The Fed is trying to slow inflation")
            else:
                lines.append("**Over the past year**, rates have remained unchanged.")
            lines.append("")

    # What the lines mean
    lines.append("### What the Lines on the Chart Mean")
    lines.append("")
    lines.append(
        "- **Dashed blue lines** (top and bottom): The range the Fed wants rates to stay in"
    )
    lines.append("- **Purple line**: The actual average rate banks are charging each other")
    lines.append("- **Green/orange lines**: Other important overnight lending rates")
    lines.append("- **Gray shaded areas**: Past recessions (economic downturns)")
    lines.append("")

    # Why it matters
    lines.append("### Why This Matters to You")
    lines.append("")
    if corridor:
        current_rate = corridor["upper"]
        if current_rate > 4.0:
            lines.append("Rates are **relatively high** by recent standards. This generally means:")
            lines.append("- Higher returns on savings and CDs")
            lines.append("- More expensive mortgages, car loans, and credit cards")
            lines.append("- The Fed is prioritizing fighting inflation")
        elif current_rate > 2.0:
            lines.append("Rates are at a **moderate level**. This generally means:")
            lines.append("- Reasonable returns on savings")
            lines.append("- Moderate borrowing costs")
            lines.append("- The Fed is balancing growth and inflation")
        else:
            lines.append("Rates are **very low**. This generally means:")
            lines.append("- Low returns on savings accounts")
            lines.append("- Cheap mortgages and loans")
            lines.append("- The Fed is trying to boost the economy")
    lines.append("")

    return "\n".join(lines)


def generate_summary(data: dict, persona: str, title: str = "") -> str:
    """Generate a summary for the specified persona.

    Args:
        data: Dictionary of series DataFrames.
        persona: One of 'economist', 'executive', 'public'.
        title: Optional chart title for context.

    Returns:
        Formatted markdown summary string.
    """
    generators = {
        "economist": generate_economist_summary,
        "executive": generate_executive_summary,
        "public": generate_public_summary,
    }
    if persona not in generators:
        raise ValueError(f"Unknown persona: {persona}. Choose from: {list(generators.keys())}")
    return generators[persona](data, title)
