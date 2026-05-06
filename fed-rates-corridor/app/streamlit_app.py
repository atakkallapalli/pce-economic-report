"""
Federal Reserve Policy Rate Corridor - Interactive Analysis App.

A Streamlit application for customizing Fed rate corridor charts, building
new analyses from templates, uploading data, generating AI summaries, and
exporting reproducible R/Python code.

Usage:
    streamlit run fed-rates-corridor/app/streamlit_app.py
"""

import os
import sys

import pandas as pd
import streamlit as st

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.components.ai_summary import generate_summary  # noqa: E402
from app.components.chart_builder import build_plotly_chart  # noqa: E402
from app.components.code_export import (  # noqa: E402
    export_data_csv,
    export_python_code,
    export_r_code,
)
from app.templates.fed_templates import TEMPLATE_CATALOG, get_template  # noqa: E402

# ---------------------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Fed Rate Corridor Analysis",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS (Fed styling)
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .main-header {
        font-family: 'Helvetica Neue', Arial, sans-serif;
        color: #1f4e79;
        border-bottom: 3px solid #1f4e79;
        padding-bottom: 10px;
        margin-bottom: 20px;
    }
    .metric-card {
        background: #f8f9fa;
        border-left: 4px solid #1f4e79;
        padding: 12px 16px;
        margin: 8px 0;
        border-radius: 0 4px 4px 0;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background: #f0f2f6;
        border-radius: 4px 4px 0 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def load_series_data(series_id: str, data_dir: str) -> pd.DataFrame:
    """Load a FRED series from CSV."""
    path = os.path.join(data_dir, f"{series_id}.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path, na_values=".")
    date_col = df.columns[0]
    value_col = df.columns[1]
    df = df[[date_col, value_col]].copy()
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna().set_index("date")
    return df


def load_all_data(data_dir: str, series_ids: list) -> dict:
    """Load all specified series."""
    data = {}
    for sid in series_ids:
        df = load_series_data(sid, data_dir)
        if not df.empty:
            data[sid] = df
    return data


# ---------------------------------------------------------------------------
# Sidebar Navigation
# ---------------------------------------------------------------------------
st.sidebar.markdown("## 🏛️ Fed Rate Corridor")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    [
        "📊 Dashboard",
        "🎨 Customize Chart",
        "📋 Templates",
        "📤 Upload Data",
        "🤖 AI Summary",
        "💾 Export Code",
    ],
)

# Data directory
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")

# Check if data exists
if not os.path.exists(DATA_DIR):
    st.warning(
        "⚠️ Data directory not found. Please run `python fed-rates-corridor/download_rates.py` first."
    )
    st.stop()


# ---------------------------------------------------------------------------
# PAGE: Dashboard
# ---------------------------------------------------------------------------
if page == "📊 Dashboard":
    st.markdown(
        '<h1 class="main-header">Federal Reserve Policy Rate Corridor</h1>', unsafe_allow_html=True
    )

    # Load default template data
    template = get_template("rate_corridor")
    series_ids = [s.series_id for s in template.series]
    data = load_all_data(DATA_DIR, series_ids)

    if not data:
        st.error("No data available. Run download_rates.py first.")
        st.stop()

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    if "DFEDTARU" in data:
        col1.metric("Target Upper", f"{data['DFEDTARU'].iloc[-1]['value']:.2f}%")
    if "DFF" in data:
        col2.metric("Eff. Fed Funds", f"{data['DFF'].iloc[-1]['value']:.2f}%")
    if "SOFR" in data:
        col3.metric("SOFR", f"{data['SOFR'].iloc[-1]['value']:.2f}%")
    if "DFEDTARL" in data:
        col4.metric("Target Lower", f"{data['DFEDTARL'].iloc[-1]['value']:.2f}%")

    # Date range selector
    st.markdown("---")
    col_range1, col_range2 = st.columns(2)
    with col_range1:
        view_option = st.selectbox("Time Range", ["1 Year", "2 Years", "5 Years", "Max"])
    with col_range2:
        end_date = pd.Timestamp.now()
        if view_option == "1 Year":
            start_date = end_date - pd.DateOffset(years=1)
        elif view_option == "2 Years":
            start_date = end_date - pd.DateOffset(years=2)
        elif view_option == "5 Years":
            start_date = end_date - pd.DateOffset(years=5)
        else:
            start_date = pd.Timestamp("2000-01-01")
        st.write(f"Showing: {start_date.strftime('%b %Y')} – {end_date.strftime('%b %Y')}")

    # Build chart
    series_configs = [
        {
            "series_id": s.series_id,
            "label": s.label,
            "color": s.color,
            "line_style": s.line_style,
            "line_width": s.line_width,
        }
        for s in template.series
    ]
    fig = build_plotly_chart(
        data,
        title=template.title,
        subtitle=template.subtitle,
        series_configs=series_configs,
        show_recession=True,
        show_corridor=True,
        corridor_upper="DFEDTARU",
        corridor_lower="DFEDTARL",
        date_range=(start_date, end_date),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Summary table
    st.markdown("### Current Rates")
    rate_data = []
    for s in template.series:
        if s.series_id in data:
            df = data[s.series_id]
            rate_data.append(
                {
                    "Series": s.label,
                    "Latest Rate": f"{df.iloc[-1]['value']:.2f}%",
                    "Date": df.index[-1].strftime("%Y-%m-%d"),
                }
            )
    st.dataframe(pd.DataFrame(rate_data), use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# PAGE: Customize Chart
# ---------------------------------------------------------------------------
elif page == "🎨 Customize Chart":
    st.markdown('<h1 class="main-header">Customize Chart</h1>', unsafe_allow_html=True)
    st.markdown("Configure chart appearance, select series, and adjust styling.")

    # Series selection
    all_series = {
        "DFEDTARU": "Federal Funds Target Range - Upper Limit",
        "DFEDTARL": "Federal Funds Target Range - Lower Limit",
        "IORB": "Interest Rate on Reserve Balances",
        "SOFR": "Secured Overnight Financing Rate",
        "DFF": "Federal Funds Effective Rate",
        "TGCRRATE": "Tri-Party General Collateral Rate",
        "RRPONTSYAWARD": "Overnight Reverse Repurchase Agreements Award Rate",
        "SRFTSYD": "Standing Repo (SRP) Operations Rate",
    }

    # Include uploaded series if any
    if "uploaded_series" in st.session_state:
        for name in st.session_state.uploaded_series:
            all_series[name] = f"[Uploaded] {name}"

    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.markdown("#### Series Selection")
        selected_series = st.multiselect(
            "Choose series to display",
            options=list(all_series.keys()),
            default=["DFEDTARU", "DFEDTARL", "IORB", "DFF", "SOFR"],
            format_func=lambda x: all_series[x],
        )

        st.markdown("#### Date Range")
        date_start = st.date_input("Start Date", value=pd.Timestamp("2023-01-01"))
        date_end = st.date_input("End Date", value=pd.Timestamp.now())

        st.markdown("#### Chart Options")
        chart_title = st.text_input("Chart Title", "Federal Reserve Policy Rate Corridor")
        chart_subtitle = st.text_input("Subtitle", "Daily rates, Percent, Not Seasonally Adjusted")
        show_recession = st.checkbox("Show recession shading", value=True)
        show_corridor = st.checkbox("Show corridor fill", value=True)

        st.markdown("#### Style")
        chart_height = st.slider("Chart height (px)", 400, 800, 550)

    # Series customization
    st.markdown("#### Series Colors & Styles")
    default_colors = {
        "DFEDTARU": "#1f4e79",
        "DFEDTARL": "#1f4e79",
        "IORB": "#2e75b6",
        "SOFR": "#548235",
        "DFF": "#7030a0",
        "TGCRRATE": "#ed7d31",
        "RRPONTSYAWARD": "#70ad47",
        "SRFTSYD": "#c00000",
    }
    series_configs = []
    if not selected_series:
        st.info("Select at least one series to display.")
    cols = st.columns(min(len(selected_series), 4)) if selected_series else []
    for i, sid in enumerate(selected_series):
        with cols[i % len(cols)]:
            color = st.color_picker(
                f"{sid}", value=default_colors.get(sid, "#333333"), key=f"color_{sid}"
            )
            style = st.selectbox(
                "Style",
                ["solid", "dashed", "dotted", "dashdot"],
                key=f"style_{sid}",
                index=1 if sid in ("DFEDTARU", "DFEDTARL") else 0,
            )
            width = st.slider(
                "Width",
                0.5,
                4.0,
                1.6 if sid not in ("DFEDTARU", "DFEDTARL") else 2.2,
                key=f"width_{sid}",
            )
            series_configs.append(
                {
                    "series_id": sid,
                    "label": all_series[sid],
                    "color": color,
                    "line_style": style,
                    "line_width": width,
                }
            )

    # Load data and build chart
    data = load_all_data(DATA_DIR, selected_series)

    # Add uploaded data if present
    if "uploaded_data" in st.session_state:
        for name, df in st.session_state.uploaded_data.items():
            if name in selected_series:
                data[name] = df

    with col_right:
        if data:
            fig = build_plotly_chart(
                data,
                title=chart_title,
                subtitle=chart_subtitle,
                series_configs=series_configs,
                show_recession=show_recession,
                show_corridor=show_corridor,
                corridor_upper="DFEDTARU",
                corridor_lower="DFEDTARL",
                date_range=(pd.Timestamp(date_start), pd.Timestamp(date_end)),
                height=chart_height,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Select series and ensure data is available.")

    # Store configs in session for export
    st.session_state["current_configs"] = series_configs
    st.session_state["current_title"] = chart_title
    st.session_state["current_subtitle"] = chart_subtitle
    st.session_state["current_date_range"] = (pd.Timestamp(date_start), pd.Timestamp(date_end))
    st.session_state["current_show_recession"] = show_recession
    st.session_state["current_show_corridor"] = show_corridor


# ---------------------------------------------------------------------------
# PAGE: Templates
# ---------------------------------------------------------------------------
elif page == "📋 Templates":
    st.markdown('<h1 class="main-header">Prebuilt Fed Chart Templates</h1>', unsafe_allow_html=True)
    st.markdown("Select a template to instantly generate a styled chart, then customize further.")

    # Template selection
    template_names = list(TEMPLATE_CATALOG.keys())
    template_labels = {k: v.title for k, v in TEMPLATE_CATALOG.items()}

    selected_template = st.selectbox(
        "Choose a template",
        template_names,
        format_func=lambda x: template_labels[x],
    )

    template = get_template(selected_template)

    # Template info
    col_info, col_chart = st.columns([1, 2])

    with col_info:
        st.markdown(f"### {template.title}")
        st.markdown(f"*{template.description}*")
        st.markdown(f"**Category:** {template.category}")
        st.markdown(f"**Series count:** {len(template.series)}")
        st.markdown("---")
        st.markdown("**Included series:**")
        for s in template.series:
            st.markdown(f"- `{s.series_id}`: {s.label}")

    with col_chart:
        # Load template data
        series_ids = [s.series_id for s in template.series]
        data = load_all_data(DATA_DIR, series_ids)

        if data:
            series_configs = [
                {
                    "series_id": s.series_id,
                    "label": s.label,
                    "color": s.color,
                    "line_style": s.line_style,
                    "line_width": s.line_width,
                }
                for s in template.series
            ]
            end_date = pd.Timestamp.now()
            start_date = pd.Timestamp(template.default_start_date)

            fig = build_plotly_chart(
                data,
                title=template.title,
                subtitle=template.subtitle,
                series_configs=series_configs,
                show_recession=template.show_recession_shading,
                show_corridor=template.show_corridor_fill,
                corridor_upper=template.corridor_upper,
                corridor_lower=template.corridor_lower,
                date_range=(start_date, end_date),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Data not available for this template. Run download_rates.py.")


# ---------------------------------------------------------------------------
# PAGE: Upload Data
# ---------------------------------------------------------------------------
elif page == "📤 Upload Data":
    st.markdown('<h1 class="main-header">Upload Series Data</h1>', unsafe_allow_html=True)
    st.markdown(
        "Upload your own time series data (CSV or Excel) to overlay on Fed charts. "
        "The file must have a date column and one or more value columns."
    )

    uploaded_file = st.file_uploader("Choose a CSV or Excel file", type=["csv", "xlsx", "xls"])

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith((".xlsx", ".xls")):
                df_upload = pd.read_excel(uploaded_file)
            else:
                df_upload = pd.read_csv(uploaded_file)

            st.markdown("### Preview")
            st.dataframe(df_upload.head(10), use_container_width=True)

            # Column mapping
            st.markdown("### Column Mapping")
            col1, col2 = st.columns(2)
            with col1:
                date_col = st.selectbox("Date column", df_upload.columns.tolist())
            with col2:
                value_cols = st.multiselect(
                    "Value column(s)",
                    [c for c in df_upload.columns if c != date_col],
                )

            if value_cols and st.button("Add to Chart Data"):
                if "uploaded_data" not in st.session_state:
                    st.session_state.uploaded_data = {}
                    st.session_state.uploaded_series = []

                for col in value_cols:
                    series_df = df_upload[[date_col, col]].copy()
                    series_df.columns = ["date", "value"]
                    series_df["date"] = pd.to_datetime(series_df["date"])
                    series_df["value"] = pd.to_numeric(series_df["value"], errors="coerce")
                    series_df = series_df.dropna().set_index("date")

                    series_name = col.replace(" ", "_").upper()
                    st.session_state.uploaded_data[series_name] = series_df
                    if series_name not in st.session_state.uploaded_series:
                        st.session_state.uploaded_series.append(series_name)

                    st.success(
                        f"Added '{series_name}' ({len(series_df)} observations). "
                        f"Go to 'Customize Chart' to include it in your chart."
                    )

        except Exception as e:
            st.error(f"Error reading file: {e}")

    # Show currently uploaded series
    if "uploaded_series" in st.session_state and st.session_state.uploaded_series:
        st.markdown("### Currently Uploaded Series")
        for name in st.session_state.uploaded_series:
            df = st.session_state.uploaded_data[name]
            st.markdown(
                f"- **{name}**: {len(df)} observations "
                f"({df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')})"
            )


# ---------------------------------------------------------------------------
# PAGE: AI Summary
# ---------------------------------------------------------------------------
elif page == "🤖 AI Summary":
    st.markdown('<h1 class="main-header">AI-Generated Summaries</h1>', unsafe_allow_html=True)
    st.markdown(
        "Generate context-appropriate summaries of the rate corridor analysis "
        "tailored for different audiences."
    )

    # Load data
    template = get_template("rate_corridor")
    series_ids = [s.series_id for s in template.series]
    data = load_all_data(DATA_DIR, series_ids)

    if not data:
        st.error("No data available. Run download_rates.py first.")
        st.stop()

    # Persona selection
    st.markdown("### Select Audience")
    persona_tabs = st.tabs(["🎓 Economist", "👔 Fed Executive", "👤 General Public"])

    personas = [
        (
            "economist",
            "🎓 Economist",
            "Technical analysis with spreads, corridor mechanics, and policy implications",
        ),
        (
            "executive",
            "👔 Fed Executive",
            "Concise briefing with bottom line, key metrics, and action items",
        ),
        (
            "public",
            "👤 General Public",
            "Plain-language explanation of what interest rates mean for everyday life",
        ),
    ]

    for i, (persona_key, persona_label, persona_desc) in enumerate(personas):
        with persona_tabs[i]:
            st.markdown(f"*{persona_desc}*")
            st.markdown("---")

            summary = generate_summary(
                data, persona_key, title="Federal Reserve Policy Rate Corridor"
            )
            st.markdown(summary)

            # Download button
            st.download_button(
                f"Download {persona_label} Summary",
                summary,
                file_name=f"fed_rates_summary_{persona_key}.md",
                mime="text/markdown",
            )


# ---------------------------------------------------------------------------
# PAGE: Export Code
# ---------------------------------------------------------------------------
elif page == "💾 Export Code":
    st.markdown('<h1 class="main-header">Export as Code</h1>', unsafe_allow_html=True)
    st.markdown(
        "Export your customized chart as a standalone Python or R script with "
        "embedded data. The exported code can recreate the exact chart on any platform."
    )

    # Use current session configs or defaults
    if "current_configs" in st.session_state:
        configs = st.session_state.current_configs
        title = st.session_state.get("current_title", "Federal Reserve Policy Rate Corridor")
        subtitle = st.session_state.get("current_subtitle", "")
        date_range = st.session_state.get("current_date_range", None)
        show_recession = st.session_state.get("current_show_recession", True)
        show_corridor = st.session_state.get("current_show_corridor", True)
    else:
        template = get_template("rate_corridor")
        configs = [
            {
                "series_id": s.series_id,
                "label": s.label,
                "color": s.color,
                "line_style": s.line_style,
                "line_width": s.line_width,
            }
            for s in template.series
        ]
        title = template.title
        subtitle = template.subtitle
        date_range = (pd.Timestamp("2023-01-01"), pd.Timestamp.now())
        show_recession = True
        show_corridor = True

    # Load data for export
    series_ids = [c["series_id"] for c in configs]
    data = load_all_data(DATA_DIR, series_ids)

    if not data:
        st.error("No data available for export.")
        st.stop()

    st.markdown("### Export Options")

    export_tabs = st.tabs(["🐍 Python", "📊 R", "📁 Data (CSV)"])

    with export_tabs[0]:
        st.markdown("Standalone Python script with matplotlib and embedded data.")
        python_code = export_python_code(
            data,
            title=title,
            subtitle=subtitle,
            series_configs=configs,
            show_recession=show_recession,
            show_corridor=show_corridor,
            corridor_upper="DFEDTARU",
            corridor_lower="DFEDTARL",
            date_range=date_range,
        )
        st.code(python_code[:3000] + "\n\n# ... (truncated for display) ...", language="python")
        st.download_button(
            "⬇️ Download Python Script",
            python_code,
            file_name="fed_chart_export.py",
            mime="text/x-python",
        )

    with export_tabs[1]:
        st.markdown("Standalone R script with base graphics and embedded data.")
        r_code = export_r_code(
            data,
            title=title,
            subtitle=subtitle,
            series_configs=configs,
            show_recession=show_recession,
            show_corridor=show_corridor,
            corridor_upper="DFEDTARU",
            corridor_lower="DFEDTARL",
            date_range=date_range,
        )
        st.code(r_code[:3000] + "\n\n# ... (truncated for display) ...", language="r")
        st.download_button(
            "⬇️ Download R Script",
            r_code,
            file_name="fed_chart_export.R",
            mime="text/plain",
        )

    with export_tabs[2]:
        st.markdown("Export the underlying data as CSV for use in any tool.")
        csv_data = export_data_csv(data, configs, date_range)
        st.text_area(
            "CSV Preview (first 20 lines)", "\n".join(csv_data.split("\n")[:20]), height=300
        )
        st.download_button(
            "⬇️ Download CSV Data",
            csv_data,
            file_name="fed_rates_data.csv",
            mime="text/csv",
        )

    st.markdown("---")
    st.markdown(
        "**Note:** Exported scripts are fully self-contained — they include the data "
        "encoded within the script. No external files or API access needed to run them."
    )
