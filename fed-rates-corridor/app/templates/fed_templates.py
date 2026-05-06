"""
Prebuilt Federal Reserve chart templates.

Provides ready-to-use chart configurations matching official Fed/FRED styling
for common monetary policy visualizations.
"""

from dataclasses import dataclass, field


@dataclass
class SeriesConfig:
    """Configuration for a single FRED series in a template."""

    series_id: str
    label: str
    color: str
    line_style: str = "solid"
    line_width: float = 1.6
    source: str = ""


@dataclass
class ChartTemplate:
    """A prebuilt chart template with Fed styling."""

    name: str
    title: str
    subtitle: str
    description: str
    series: list = field(default_factory=list)
    y_axis_label: str = "Percent"
    show_recession_shading: bool = True
    show_corridor_fill: bool = False
    corridor_upper: str = ""
    corridor_lower: str = ""
    default_start_date: str = "2020-01-01"
    category: str = "Monetary Policy"


# ---------------------------------------------------------------------------
# Template Catalog
# ---------------------------------------------------------------------------

TEMPLATE_CATALOG = {
    "rate_corridor": ChartTemplate(
        name="rate_corridor",
        title="Federal Reserve Policy Rate Corridor",
        subtitle="Daily rates, Percent, Not Seasonally Adjusted",
        description=(
            "The complete Federal Reserve rate corridor showing all administered "
            "and market-determined rates between the target range bounds. "
            "Replicates FRED Graph ?g=1Ng5J."
        ),
        series=[
            SeriesConfig(
                "DFEDTARU",
                "Federal Funds Target Range - Upper Limit",
                "#1f4e79",
                "dashed",
                2.2,
                "Board of Governors",
            ),
            SeriesConfig(
                "SRFTSYD",
                "Standing Repo (SRP) Operations Rate",
                "#c00000",
                "solid",
                1.6,
                "NY Fed",
            ),
            SeriesConfig(
                "IORB",
                "Interest Rate on Reserve Balances (IORB Rate)",
                "#2e75b6",
                "solid",
                1.6,
                "Board of Governors",
            ),
            SeriesConfig(
                "SOFR",
                "Secured Overnight Financing Rate",
                "#548235",
                "solid",
                1.6,
                "NY Fed",
            ),
            SeriesConfig(
                "DFF",
                "Federal Funds Effective Rate",
                "#7030a0",
                "solid",
                1.6,
                "Board of Governors",
            ),
            SeriesConfig(
                "TGCRRATE",
                "Tri-Party General Collateral Rate",
                "#ed7d31",
                "solid",
                1.6,
                "NY Fed",
            ),
            SeriesConfig(
                "RRPONTSYAWARD",
                "Overnight Reverse Repurchase Agreements Award Rate",
                "#70ad47",
                "solid",
                1.6,
                "NY Fed",
            ),
            SeriesConfig(
                "DFEDTARL",
                "Federal Funds Target Range - Lower Limit",
                "#1f4e79",
                "dashed",
                2.2,
                "Board of Governors",
            ),
        ],
        show_corridor_fill=True,
        corridor_upper="DFEDTARU",
        corridor_lower="DFEDTARL",
        default_start_date="2020-01-01",
        category="Monetary Policy",
    ),
    "fed_funds_target": ChartTemplate(
        name="fed_funds_target",
        title="Federal Funds Target Range",
        subtitle="Daily, Percent, Not Seasonally Adjusted",
        description=(
            "Upper and lower bounds of the FOMC federal funds target range "
            "with the effective federal funds rate."
        ),
        series=[
            SeriesConfig(
                "DFEDTARU",
                "Target Range - Upper Limit",
                "#1f4e79",
                "dashed",
                2.0,
                "Board of Governors",
            ),
            SeriesConfig(
                "DFF",
                "Federal Funds Effective Rate",
                "#7030a0",
                "solid",
                2.0,
                "Board of Governors",
            ),
            SeriesConfig(
                "DFEDTARL",
                "Target Range - Lower Limit",
                "#1f4e79",
                "dashed",
                2.0,
                "Board of Governors",
            ),
        ],
        show_corridor_fill=True,
        corridor_upper="DFEDTARU",
        corridor_lower="DFEDTARL",
        default_start_date="2015-01-01",
        category="Monetary Policy",
    ),
    "overnight_rates": ChartTemplate(
        name="overnight_rates",
        title="Overnight Money Market Rates",
        subtitle="Daily, Percent, Not Seasonally Adjusted",
        description=(
            "Key overnight secured and unsecured lending rates — SOFR, "
            "Fed Funds Effective, and Tri-Party GC Rate."
        ),
        series=[
            SeriesConfig(
                "SOFR",
                "Secured Overnight Financing Rate",
                "#548235",
                "solid",
                2.0,
                "NY Fed",
            ),
            SeriesConfig(
                "DFF",
                "Federal Funds Effective Rate",
                "#7030a0",
                "solid",
                2.0,
                "Board of Governors",
            ),
            SeriesConfig(
                "TGCRRATE",
                "Tri-Party General Collateral Rate",
                "#ed7d31",
                "solid",
                2.0,
                "NY Fed",
            ),
        ],
        default_start_date="2018-04-01",
        category="Money Markets",
    ),
    "iorb_framework": ChartTemplate(
        name="iorb_framework",
        title="IORB Rate Implementation Framework",
        subtitle="Daily, Percent, Not Seasonally Adjusted",
        description=(
            "The Interest on Reserve Balances rate relative to the target range "
            "and overnight market rates. Shows how IORB steers rates."
        ),
        series=[
            SeriesConfig(
                "DFEDTARU",
                "Target Range - Upper",
                "#1f4e79",
                "dashed",
                1.8,
                "Board of Governors",
            ),
            SeriesConfig(
                "IORB",
                "Interest Rate on Reserve Balances",
                "#2e75b6",
                "solid",
                2.5,
                "Board of Governors",
            ),
            SeriesConfig(
                "DFF",
                "Federal Funds Effective Rate",
                "#7030a0",
                "solid",
                1.6,
                "Board of Governors",
            ),
            SeriesConfig(
                "RRPONTSYAWARD",
                "ON RRP Award Rate",
                "#70ad47",
                "solid",
                1.8,
                "NY Fed",
            ),
            SeriesConfig(
                "DFEDTARL",
                "Target Range - Lower",
                "#1f4e79",
                "dashed",
                1.8,
                "Board of Governors",
            ),
        ],
        show_corridor_fill=True,
        corridor_upper="DFEDTARU",
        corridor_lower="DFEDTARL",
        default_start_date="2021-07-01",
        category="Monetary Policy",
    ),
    "repo_rates": ChartTemplate(
        name="repo_rates",
        title="Repurchase Agreement Rates",
        subtitle="Daily, Percent, Not Seasonally Adjusted",
        description=(
            "Standing Repo Facility rate, SOFR, and Tri-Party GC Rate — "
            "the key secured lending rates in the overnight market."
        ),
        series=[
            SeriesConfig(
                "SRFTSYD",
                "Standing Repo (SRP) Rate",
                "#c00000",
                "solid",
                2.0,
                "NY Fed",
            ),
            SeriesConfig(
                "SOFR",
                "Secured Overnight Financing Rate",
                "#548235",
                "solid",
                2.0,
                "NY Fed",
            ),
            SeriesConfig(
                "TGCRRATE",
                "Tri-Party General Collateral Rate",
                "#ed7d31",
                "solid",
                2.0,
                "NY Fed",
            ),
        ],
        default_start_date="2021-07-01",
        category="Money Markets",
    ),
}


def get_template(name: str) -> ChartTemplate:
    """Get a chart template by name."""
    if name not in TEMPLATE_CATALOG:
        raise ValueError(f"Template '{name}' not found. Available: {list(TEMPLATE_CATALOG.keys())}")
    return TEMPLATE_CATALOG[name]


def list_templates() -> list:
    """List all available templates with metadata."""
    return [
        {
            "name": t.name,
            "title": t.title,
            "description": t.description,
            "category": t.category,
            "series_count": len(t.series),
        }
        for t in TEMPLATE_CATALOG.values()
    ]
