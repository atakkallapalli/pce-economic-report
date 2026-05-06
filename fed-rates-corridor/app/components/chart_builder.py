"""
Chart builder component with Fed stylesheet.

Generates interactive Plotly charts with Federal Reserve styling.
"""

import io

import matplotlib
import pandas as pd
import plotly.graph_objects as go

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

# NBER recession periods
RECESSIONS = [
    ("2001-03-01", "2001-11-01"),
    ("2007-12-01", "2009-06-01"),
    ("2020-02-01", "2020-04-01"),
]

# Fed stylesheet colors
FED_STYLE = {
    "bg_color": "white",
    "grid_color": "#e0e0e0",
    "text_color": "#333333",
    "font_family": "Helvetica Neue, Helvetica, Arial, sans-serif",
    "title_size": 16,
    "axis_size": 12,
}


def build_plotly_chart(
    data: dict,
    title: str = "Federal Reserve Rate Chart",
    subtitle: str = "",
    series_configs: list = None,
    show_recession: bool = True,
    show_corridor: bool = False,
    corridor_upper: str = "",
    corridor_lower: str = "",
    date_range: tuple = None,
    height: int = 550,
) -> go.Figure:
    """Build an interactive Plotly chart with Fed styling."""
    fig = go.Figure()

    # Add recession shading
    if show_recession:
        for start, end in RECESSIONS:
            start_ts = pd.Timestamp(start)
            end_ts = pd.Timestamp(end)
            if date_range:
                if end_ts < date_range[0] or start_ts > date_range[1]:
                    continue
            fig.add_vrect(
                x0=start,
                x1=end,
                fillcolor="gray",
                opacity=0.08,
                layer="below",
                line_width=0,
            )

    # Add corridor fill
    if show_corridor and corridor_upper in data and corridor_lower in data:
        upper_df = data[corridor_upper]
        lower_df = data[corridor_lower]
        if date_range:
            upper_df = upper_df[
                (upper_df.index >= date_range[0]) & (upper_df.index <= date_range[1])
            ]
            lower_df = lower_df[
                (lower_df.index >= date_range[0]) & (lower_df.index <= date_range[1])
            ]
        fig.add_trace(
            go.Scatter(
                x=upper_df.index,
                y=upper_df["value"],
                mode="lines",
                line={"width": 0},
                showlegend=False,
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=lower_df.index,
                y=lower_df["value"],
                mode="lines",
                line={"width": 0},
                fill="tonexty",
                fillcolor="rgba(31, 78, 121, 0.06)",
                showlegend=False,
                hoverinfo="skip",
            )
        )

    # Plot each series
    if series_configs:
        for config in series_configs:
            sid = config["series_id"]
            if sid not in data:
                continue
            df = data[sid]
            if date_range:
                df = df[(df.index >= date_range[0]) & (df.index <= date_range[1])]
            if df.empty:
                continue

            dash_map = {
                "solid": "solid",
                "dashed": "dash",
                "dotted": "dot",
                "dashdot": "dashdot",
            }
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df["value"],
                    mode="lines",
                    name=config.get("label", sid),
                    line={
                        "color": config.get("color", "#333333"),
                        "width": config.get("line_width", 1.6),
                        "dash": dash_map.get(config.get("line_style", "solid"), "solid"),
                    },
                    hovertemplate="%{y:.2f}%<extra>%{fullData.name}</extra>",
                )
            )

    # Apply Fed styling
    fig.update_layout(
        title={
            "text": f"<b>{title}</b><br><span style='font-size:11px;color:#666'>{subtitle}</span>",
            "x": 0.01,
            "xanchor": "left",
            "font": {"size": FED_STYLE["title_size"], "family": FED_STYLE["font_family"]},
        },
        xaxis={
            "showgrid": True,
            "gridcolor": FED_STYLE["grid_color"],
            "gridwidth": 0.5,
            "linecolor": FED_STYLE["text_color"],
            "tickfont": {"size": 10, "family": FED_STYLE["font_family"]},
        },
        yaxis={
            "title": {"text": "Percent", "font": {"size": 12, "family": FED_STYLE["font_family"]}},
            "showgrid": True,
            "gridcolor": FED_STYLE["grid_color"],
            "gridwidth": 0.5,
            "linecolor": FED_STYLE["text_color"],
            "tickfont": {"size": 10, "family": FED_STYLE["font_family"]},
            "ticksuffix": "%",
        },
        plot_bgcolor=FED_STYLE["bg_color"],
        paper_bgcolor=FED_STYLE["bg_color"],
        font={"family": FED_STYLE["font_family"], "color": FED_STYLE["text_color"]},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": -0.25,
            "xanchor": "left",
            "x": 0,
            "font": {"size": 9},
        },
        margin={"l": 60, "r": 20, "t": 80, "b": 100},
        height=height,
        hovermode="x unified",
        annotations=[
            {
                "text": (
                    "Sources: Board of Governors of the Federal Reserve System (US); "
                    "Federal Reserve Bank of New York via FRED®"
                ),
                "showarrow": False,
                "xref": "paper",
                "yref": "paper",
                "x": 0,
                "y": -0.35,
                "font": {"size": 8, "color": "#888"},
            }
        ],
    )

    return fig


def build_matplotlib_chart(
    data: dict,
    title: str = "Federal Reserve Rate Chart",
    subtitle: str = "",
    series_configs: list = None,
    show_recession: bool = True,
    show_corridor: bool = False,
    corridor_upper: str = "",
    corridor_lower: str = "",
    date_range: tuple = None,
) -> bytes:
    """Build a static matplotlib chart (for export) with Fed styling."""
    plt.rcParams.update(
        {
            "figure.figsize": (14, 7),
            "figure.dpi": 150,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#333333",
            "axes.linewidth": 0.8,
            "axes.grid": True,
            "grid.color": "#e0e0e0",
            "grid.linewidth": 0.5,
            "lines.linewidth": 1.8,
            "font.family": "sans-serif",
            "font.size": 10,
        }
    )

    fig, ax = plt.subplots()

    # Recession shading
    if show_recession:
        for start, end in RECESSIONS:
            ax.axvspan(pd.Timestamp(start), pd.Timestamp(end), alpha=0.08, color="gray")

    # Plot series
    if series_configs:
        for config in series_configs:
            sid = config["series_id"]
            if sid not in data:
                continue
            df = data[sid]
            if date_range:
                df = df[(df.index >= date_range[0]) & (df.index <= date_range[1])]
            if df.empty:
                continue
            ls_map = {"solid": "-", "dashed": "--", "dotted": ":", "dashdot": "-."}
            ax.plot(
                df.index,
                df["value"],
                color=config.get("color", "#333333"),
                linestyle=ls_map.get(config.get("line_style", "solid"), "-"),
                linewidth=config.get("line_width", 1.6),
                label=config.get("label", sid),
            )

    # Corridor fill
    if show_corridor and corridor_upper in data and corridor_lower in data:
        upper = data[corridor_upper]
        lower = data[corridor_lower]
        if date_range:
            upper = upper[(upper.index >= date_range[0]) & (upper.index <= date_range[1])]
            lower = lower[(lower.index >= date_range[0]) & (lower.index <= date_range[1])]
        merged = upper.join(lower, lsuffix="_u", rsuffix="_l", how="inner")
        ax.fill_between(
            merged.index, merged["value_l"], merged["value_u"], alpha=0.06, color="#1f4e79"
        )

    ax.set_title(title, fontsize=14, fontweight="bold", loc="left", pad=12)
    ax.text(0.0, 1.02, subtitle, transform=ax.transAxes, fontsize=9, color="#666", va="bottom")
    ax.set_ylabel("Percent", fontsize=11, fontweight="bold")
    ax.legend(loc="upper right", ncol=2, fontsize=7.5, framealpha=0.95)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    if date_range:
        ax.set_xlim(date_range[0], date_range[1])

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.yaxis.set_major_locator(MultipleLocator(0.25))

    fig.text(
        0.01,
        -0.02,
        "Sources: Board of Governors of the Federal Reserve System (US); "
        "Federal Reserve Bank of New York via FRED®",
        fontsize=7.5,
        color="#666",
    )

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()
