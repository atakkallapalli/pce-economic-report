"""
Code export module.

Generates reproducible Python and R scripts with embedded data
so the analysis can be recreated on a different platform.
"""

import base64
import io
import json
from datetime import datetime


def _dataframe_to_csv_string(data: dict, series_configs: list, date_range: tuple = None) -> str:
    """Convert selected series to a merged CSV string."""
    frames = []
    for config in series_configs:
        sid = config["series_id"]
        if sid not in data:
            continue
        df = data[sid].copy()
        if date_range:
            df = df[(df.index >= date_range[0]) & (df.index <= date_range[1])]
        df = df.rename(columns={"value": sid})
        frames.append(df)

    if not frames:
        return ""

    merged = frames[0]
    for f in frames[1:]:
        merged = merged.join(f, how="outer")

    buf = io.StringIO()
    merged.to_csv(buf, index_label="date")
    return buf.getvalue()


def export_python_code(
    data: dict,
    title: str,
    subtitle: str,
    series_configs: list,
    show_recession: bool = True,
    show_corridor: bool = False,
    corridor_upper: str = "",
    corridor_lower: str = "",
    date_range: tuple = None,
) -> str:
    """Generate a standalone Python script with embedded data."""
    csv_data = _dataframe_to_csv_string(data, series_configs, date_range)
    csv_b64 = base64.b64encode(csv_data.encode()).decode()

    configs_json = json.dumps(series_configs, indent=4)

    # Escape user input to prevent breaking generated script syntax
    safe_title = title.replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'")
    safe_subtitle = subtitle.replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'")

    date_range_str = ""
    if date_range:
        date_range_str = (
            f'START_DATE = "{date_range[0].strftime("%Y-%m-%d")}"\n'
            f'END_DATE = "{date_range[1].strftime("%Y-%m-%d")}"\n'
        )

    script = f'''"""
Federal Reserve Chart - Generated Export
Title: {title}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

This script is self-contained with embedded data.
Run it to recreate the chart on any platform with Python + matplotlib.

Requirements: pip install pandas matplotlib numpy
"""

import base64
import io
from io import StringIO

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MultipleLocator
import pandas as pd


# ============================================================================
# EMBEDDED DATA (base64-encoded CSV)
# ============================================================================
DATA_B64 = """{csv_b64}"""

# ============================================================================
# CHART CONFIGURATION
# ============================================================================
TITLE = "{safe_title}"
SUBTITLE = "{safe_subtitle}"
{date_range_str}
SERIES_CONFIGS = {configs_json}

SHOW_RECESSION = {show_recession}
SHOW_CORRIDOR = {show_corridor}
CORRIDOR_UPPER = "{corridor_upper}"
CORRIDOR_LOWER = "{corridor_lower}"

RECESSIONS = [
    ("2001-03-01", "2001-11-01"),
    ("2007-12-01", "2009-06-01"),
    ("2020-02-01", "2020-04-01"),
]


# ============================================================================
# CHART GENERATION
# ============================================================================
def load_data():
    """Decode embedded CSV data."""
    csv_str = base64.b64decode(DATA_B64).decode()
    df = pd.read_csv(StringIO(csv_str), index_col="date", parse_dates=True)
    return df


def plot_chart(df):
    """Generate the Fed-styled chart."""
    plt.rcParams.update({{
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
    }})

    fig, ax = plt.subplots()

    # Recession shading
    if SHOW_RECESSION:
        for start, end in RECESSIONS:
            ax.axvspan(pd.Timestamp(start), pd.Timestamp(end), alpha=0.08, color="gray")

    # Corridor fill
    if SHOW_CORRIDOR and CORRIDOR_UPPER in df.columns and CORRIDOR_LOWER in df.columns:
        ax.fill_between(
            df.index,
            df[CORRIDOR_LOWER],
            df[CORRIDOR_UPPER],
            alpha=0.06,
            color="#1f4e79",
        )

    # Plot each series
    ls_map = {{"solid": "-", "dashed": "--", "dotted": ":", "dashdot": "-."}}
    for config in SERIES_CONFIGS:
        sid = config["series_id"]
        if sid not in df.columns:
            continue
        series = df[sid].dropna()
        ax.plot(
            series.index,
            series.values,
            color=config.get("color", "#333333"),
            linestyle=ls_map.get(config.get("line_style", "solid"), "-"),
            linewidth=config.get("line_width", 1.6),
            label=config.get("label", sid),
        )

    ax.set_title(TITLE, fontsize=14, fontweight="bold", loc="left", pad=12)
    ax.text(0.0, 1.02, SUBTITLE, transform=ax.transAxes, fontsize=9, color="#666", va="bottom")
    ax.set_ylabel("Percent", fontsize=11, fontweight="bold")
    ax.legend(loc="upper right", ncol=2, fontsize=7.5, framealpha=0.95)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

    fig.text(
        0.01, -0.02,
        "Sources: Board of Governors of the Federal Reserve System (US); "
        "Federal Reserve Bank of New York via FRED\\u00ae",
        fontsize=7.5, color="#666",
    )

    output_path = "fed_chart_export.png"
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Chart saved to: {{output_path}}")
    return output_path


if __name__ == "__main__":
    print("Loading embedded data...")
    df = load_data()
    print(f"  {{len(df)}} observations, {{len(df.columns)}} series")
    print(f"  Date range: {{df.index[0].date()}} to {{df.index[-1].date()}}")
    print()
    print("Generating chart...")
    path = plot_chart(df)
    print("Done!")
'''
    return script


def export_r_code(
    data: dict,
    title: str,
    subtitle: str,
    series_configs: list,
    show_recession: bool = True,
    show_corridor: bool = False,
    corridor_upper: str = "",
    corridor_lower: str = "",
    date_range: tuple = None,
) -> str:
    """Generate a standalone R script with embedded data."""
    csv_data = _dataframe_to_csv_string(data, series_configs, date_range)
    # Escape for R heredoc
    csv_escaped = csv_data.replace("\\", "\\\\").replace('"', '\\"')

    # Escape user input to prevent breaking generated script syntax
    safe_title = title.replace("\\", "\\\\").replace('"', '\\"')
    safe_subtitle = subtitle.replace("\\", "\\\\").replace('"', '\\"')

    series_r_list = []
    for config in series_configs:
        series_r_list.append(
            f'  list(id="{config["series_id"]}", '
            f'label="{config.get("label", config["series_id"])}", '
            f'color="{config.get("color", "#333333")}", '
            f'lty={"2" if config.get("line_style") == "dashed" else "1"}, '
            f'lwd={config.get("line_width", 1.6)})'
        )
    series_r = ",\n".join(series_r_list)

    date_filter = ""
    if date_range:
        date_filter = (
            f"\n# Filter to date range\n"
            f'df <- df[df$date >= as.Date("{date_range[0].strftime("%Y-%m-%d")}") & '
            f'df$date <= as.Date("{date_range[1].strftime("%Y-%m-%d")}"), ]\n'
        )

    script = f"""# ==========================================================================
# Federal Reserve Chart - Generated R Export
# Title: {title}
# Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
#
# This script is self-contained with embedded data.
# Run it to recreate the chart on any platform with R.
#
# Requirements: No external packages needed (base R graphics)
# ==========================================================================

# ============================================================================
# EMBEDDED DATA
# ============================================================================
csv_text <- "{csv_escaped}"

df <- read.csv(text = csv_text, stringsAsFactors = FALSE)
df$date <- as.Date(df$date)
{date_filter}
# ============================================================================
# CHART CONFIGURATION
# ============================================================================
chart_title <- "{safe_title}"
chart_subtitle <- "{safe_subtitle}"

series_configs <- list(
{series_r}
)

show_recession <- {"TRUE" if show_recession else "FALSE"}
show_corridor <- {"TRUE" if show_corridor else "FALSE"}
corridor_upper <- "{corridor_upper}"
corridor_lower <- "{corridor_lower}"

recessions <- data.frame(
  start = as.Date(c("2001-03-01", "2007-12-01", "2020-02-01")),
  end = as.Date(c("2001-11-01", "2009-06-01", "2020-04-01"))
)


# ============================================================================
# CHART GENERATION
# ============================================================================
generate_chart <- function(output_file = "fed_chart_export.png") {{
  png(output_file, width = 14, height = 7, units = "in", res = 150)

  # Set margins
  par(mar = c(5, 4, 4, 2) + 0.1, family = "sans")

  # Determine y-axis range
  y_vals <- unlist(df[, -1], use.names = FALSE)
  y_range <- range(y_vals, na.rm = TRUE)
  y_range <- c(floor(y_range[1] * 4) / 4, ceiling(y_range[2] * 4) / 4)

  # Empty plot
  plot(df$date, rep(NA, nrow(df)),
       type = "n", ylim = y_range,
       xlab = "", ylab = "Percent",
       main = chart_title,
       axes = TRUE, frame.plot = FALSE)
  mtext(chart_subtitle, side = 3, line = 0, adj = 0, cex = 0.8, col = "#666666")

  # Grid
  abline(h = seq(y_range[1], y_range[2], by = 0.25), col = "#e0e0e0", lwd = 0.5)

  # Recession shading
  if (show_recession) {{
    for (i in 1:nrow(recessions)) {{
      rect(recessions$start[i], y_range[1], recessions$end[i], y_range[2],
           col = rgb(0.5, 0.5, 0.5, 0.08), border = NA)
    }}
  }}

  # Corridor fill
  if (show_corridor && corridor_upper %in% names(df) && corridor_lower %in% names(df)) {{
    polygon(
      c(df$date, rev(df$date)),
      c(df[[corridor_upper]], rev(df[[corridor_lower]])),
      col = rgb(31/255, 78/255, 121/255, 0.06), border = NA
    )
  }}

  # Plot each series
  legend_labels <- c()
  legend_colors <- c()
  legend_lty <- c()
  legend_lwd <- c()

  for (config in series_configs) {{
    if (config$id %in% names(df)) {{
      lines(df$date, df[[config$id]],
            col = config$color, lty = config$lty, lwd = config$lwd)
      legend_labels <- c(legend_labels, config$label)
      legend_colors <- c(legend_colors, config$color)
      legend_lty <- c(legend_lty, config$lty)
      legend_lwd <- c(legend_lwd, config$lwd)
    }}
  }}

  # Legend
  legend("topright", legend = legend_labels,
         col = legend_colors, lty = legend_lty, lwd = legend_lwd,
         cex = 0.7, bg = rgb(1, 1, 1, 0.95), ncol = 2)

  # Source attribution
  mtext("Sources: Board of Governors (US); NY Fed via FRED",
        side = 1, line = 4, adj = 0, cex = 0.65, col = "#888888")

  dev.off()
  cat(paste("Chart saved to:", output_file, "\\n"))
}}

# Run
cat("Generating chart...\\n")
cat(paste("  ", nrow(df), "observations,", ncol(df) - 1, "series\\n"))
cat(paste("  Date range:", min(df$date), "to", max(df$date), "\\n\\n"))
generate_chart()
cat("Done!\\n")
"""
    return script


def export_data_csv(data: dict, series_configs: list, date_range: tuple = None) -> str:
    """Export just the data as CSV."""
    return _dataframe_to_csv_string(data, series_configs, date_range)
