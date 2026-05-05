"""Streamlit analytics dashboard for NYC Taxi curated data.

Reads exported CSV/JSON data produced by the Hive client and presents
interactive visualizations covering trip volumes, revenue, demand patterns,
fare distributions, and route analytics.

Usage:
    streamlit run etl_pipeline/client/dashboard.py
"""

from __future__ import annotations

import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

DATA_DIR = "etl_pipeline/output/client_exports"

DAY_NAMES = {
    1: "Sunday",
    2: "Monday",
    3: "Tuesday",
    4: "Wednesday",
    5: "Thursday",
    6: "Friday",
    7: "Saturday",
}


@st.cache_data
def load_data() -> dict[str, pd.DataFrame]:
    """Load exported analytics data from CSV files."""
    datasets: dict[str, pd.DataFrame] = {}
    expected = ["daily_summary", "top_routes", "hourly_demand", "fare_breakdown"]

    for name in expected:
        csv_path = os.path.join(DATA_DIR, f"{name}.csv")
        json_path = os.path.join(DATA_DIR, f"{name}.json")

        if os.path.exists(csv_path):
            datasets[name] = pd.read_csv(csv_path)
        elif os.path.exists(json_path):
            datasets[name] = pd.read_json(json_path)
        else:
            st.warning(f"Missing data file: {name}. Run the Hive client first.")
            datasets[name] = pd.DataFrame()

    if "daily_summary" in datasets and not datasets["daily_summary"].empty:
        datasets["daily_summary"]["pickup_date"] = pd.to_datetime(
            datasets["daily_summary"]["pickup_date"]
        )

    return datasets


def render_kpi_cards(daily: pd.DataFrame) -> None:
    """Render top-level KPI metric cards."""
    if daily.empty:
        return

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_trips = daily["total_trips"].sum()
        st.metric("Total Trips", f"{total_trips:,.0f}")

    with col2:
        total_rev = daily["total_revenue"].sum()
        st.metric("Total Revenue", f"${total_rev:,.0f}")

    with col3:
        avg_fare = daily["avg_fare"].mean()
        st.metric("Avg Fare", f"${avg_fare:.2f}")

    with col4:
        avg_dist = daily["avg_distance_mi"].mean()
        st.metric("Avg Distance", f"{avg_dist:.1f} mi")


def render_daily_trends(daily: pd.DataFrame) -> None:
    """Render daily trip volume and revenue trends."""
    if daily.empty:
        return

    st.subheader("Daily Trip Volume & Revenue")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=daily["pickup_date"],
            y=daily["total_trips"],
            name="Trips",
            marker_color="#636EFA",
            opacity=0.7,
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=daily["pickup_date"],
            y=daily["total_revenue"],
            name="Revenue ($)",
            line={"color": "#EF553B", "width": 2},
        ),
        secondary_y=True,
    )

    fig.update_layout(
        height=400,
        legend={"orientation": "h", "y": 1.1},
        margin={"t": 30, "b": 40},
    )
    fig.update_yaxes(title_text="Number of Trips", secondary_y=False)
    fig.update_yaxes(title_text="Revenue ($)", secondary_y=True)

    st.plotly_chart(fig, use_container_width=True)


def render_speed_duration(daily: pd.DataFrame) -> None:
    """Render average speed and duration trends."""
    if daily.empty:
        return

    st.subheader("Trip Duration & Speed Trends")

    col1, col2 = st.columns(2)

    with col1:
        fig = px.line(
            daily,
            x="pickup_date",
            y="avg_duration_min",
            title="Average Trip Duration (minutes)",
            labels={"avg_duration_min": "Duration (min)", "pickup_date": "Date"},
        )
        fig.update_layout(height=300, margin={"t": 40, "b": 30})
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.line(
            daily,
            x="pickup_date",
            y="avg_speed_mph",
            title="Average Speed (mph)",
            labels={"avg_speed_mph": "Speed (mph)", "pickup_date": "Date"},
        )
        fig.update_layout(height=300, margin={"t": 40, "b": 30})
        st.plotly_chart(fig, use_container_width=True)


def render_hourly_heatmap(hourly: pd.DataFrame) -> None:
    """Render hourly demand heatmap by day of week."""
    if hourly.empty:
        return

    st.subheader("Demand Heatmap: Hour vs Day of Week")

    hourly_copy = hourly.copy()
    hourly_copy["day_name"] = hourly_copy["pickup_day_of_week"].map(DAY_NAMES)

    pivot = hourly_copy.pivot_table(
        index="day_name",
        columns="pickup_hour",
        values="trip_count",
        aggfunc="sum",
    )

    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    pivot = pivot.reindex([d for d in day_order if d in pivot.index])

    fig = px.imshow(
        pivot,
        labels={"x": "Hour of Day", "y": "Day of Week", "color": "Trip Count"},
        color_continuous_scale="YlOrRd",
        aspect="auto",
    )
    fig.update_layout(height=350, margin={"t": 20, "b": 30})
    st.plotly_chart(fig, use_container_width=True)


def render_fare_analysis(fare: pd.DataFrame) -> None:
    """Render fare distribution charts."""
    if fare.empty:
        return

    st.subheader("Fare Analysis")

    col1, col2 = st.columns(2)

    with col1:
        by_distance = (
            fare.groupby("distance_bucket")
            .agg({"trip_count": "sum", "avg_fare": "mean", "total_revenue": "sum"})
            .reset_index()
        )
        fig = px.bar(
            by_distance,
            x="distance_bucket",
            y="trip_count",
            color="avg_fare",
            title="Trips by Distance Bucket",
            labels={
                "distance_bucket": "Distance",
                "trip_count": "Trips",
                "avg_fare": "Avg Fare ($)",
            },
            color_continuous_scale="Viridis",
        )
        fig.update_layout(height=350, margin={"t": 40, "b": 30})
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        by_time = (
            fare.groupby("time_of_day")
            .agg({"trip_count": "sum", "avg_fare": "mean", "total_revenue": "sum"})
            .reset_index()
        )
        fig = px.pie(
            by_time,
            values="trip_count",
            names="time_of_day",
            title="Trip Distribution by Time of Day",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_layout(height=350, margin={"t": 40, "b": 30})
        st.plotly_chart(fig, use_container_width=True)


def render_payment_analysis(fare: pd.DataFrame) -> None:
    """Render payment type breakdown and tipping patterns."""
    if fare.empty:
        return

    st.subheader("Payment & Tipping Patterns")

    col1, col2 = st.columns(2)

    with col1:
        by_payment = (
            fare.groupby("payment_type_desc")
            .agg({"trip_count": "sum", "total_revenue": "sum"})
            .reset_index()
        )
        fig = px.bar(
            by_payment,
            x="payment_type_desc",
            y="total_revenue",
            color="trip_count",
            title="Revenue by Payment Type",
            labels={
                "payment_type_desc": "Payment Type",
                "total_revenue": "Revenue ($)",
                "trip_count": "Trip Count",
            },
        )
        fig.update_layout(height=350, margin={"t": 40, "b": 30})
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        tip_data = (
            fare.groupby("time_of_day")
            .agg({"avg_tip": "mean", "avg_fare": "mean"})
            .reset_index()
        )
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=tip_data["time_of_day"],
                y=tip_data["avg_fare"],
                name="Avg Fare",
                marker_color="#636EFA",
            )
        )
        fig.add_trace(
            go.Bar(
                x=tip_data["time_of_day"],
                y=tip_data["avg_tip"],
                name="Avg Tip",
                marker_color="#00CC96",
            )
        )
        fig.update_layout(
            title="Average Fare vs Tip by Time of Day",
            barmode="group",
            height=350,
            margin={"t": 40, "b": 30},
        )
        st.plotly_chart(fig, use_container_width=True)


def render_top_routes(routes: pd.DataFrame) -> None:
    """Render top routes analysis."""
    if routes.empty:
        return

    st.subheader("Top 20 Routes by Trip Volume")

    routes_display = routes.copy()
    routes_display["route"] = (
        "Zone " + routes_display["pickup_zone"].astype(str)
        + " -> Zone " + routes_display["dropoff_zone"].astype(str)
    )

    fig = px.bar(
        routes_display.head(20),
        x="route",
        y="trip_count",
        color="avg_fare",
        title="Most Popular Routes",
        labels={
            "route": "Route",
            "trip_count": "Trip Count",
            "avg_fare": "Avg Fare ($)",
        },
        color_continuous_scale="Plasma",
    )
    fig.update_layout(
        height=400,
        margin={"t": 40, "b": 80},
        xaxis_tickangle=-45,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_weekday_weekend(hourly: pd.DataFrame) -> None:
    """Compare weekday vs weekend demand patterns."""
    if hourly.empty:
        return

    st.subheader("Weekday vs Weekend Demand")

    grouped = (
        hourly.groupby(["pickup_hour", "is_weekend"])
        .agg({"trip_count": "sum", "avg_fare": "mean"})
        .reset_index()
    )
    grouped["category"] = grouped["is_weekend"].map({True: "Weekend", False: "Weekday"})

    fig = px.line(
        grouped,
        x="pickup_hour",
        y="trip_count",
        color="category",
        title="Hourly Trip Count: Weekday vs Weekend",
        labels={
            "pickup_hour": "Hour of Day",
            "trip_count": "Trip Count",
            "category": "Day Type",
        },
    )
    fig.update_layout(height=350, margin={"t": 40, "b": 30})
    st.plotly_chart(fig, use_container_width=True)


def main() -> None:
    st.set_page_config(
        page_title="NYC Taxi Analytics Dashboard",
        page_icon="\U0001f695",
        layout="wide",
    )

    st.title("NYC Yellow Taxi - Analytics Dashboard")
    st.caption(
        "Curated data product from the PySpark ETL pipeline "
        "(Delta Lake + Hive Catalog)"
    )

    data = load_data()

    daily = data.get("daily_summary", pd.DataFrame())
    hourly = data.get("hourly_demand", pd.DataFrame())
    routes = data.get("top_routes", pd.DataFrame())
    fare = data.get("fare_breakdown", pd.DataFrame())

    if all(df.empty for df in [daily, hourly, routes, fare]):
        st.error(
            "No data found. Please run the ETL pipeline and Hive client first:\n\n"
            "```bash\n"
            "python -m etl_pipeline.src.pipeline\n"
            "python -m etl_pipeline.client.hive_client --export\n"
            "```"
        )
        return

    render_kpi_cards(daily)
    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Trip Trends", "Demand Patterns", "Fare Analysis", "Route Analytics"]
    )

    with tab1:
        render_daily_trends(daily)
        render_speed_duration(daily)

    with tab2:
        render_hourly_heatmap(hourly)
        render_weekday_weekend(hourly)

    with tab3:
        render_fare_analysis(fare)
        render_payment_analysis(fare)

    with tab4:
        render_top_routes(routes)

    st.divider()
    with st.expander("Raw Data Explorer"):
        selected = st.selectbox(
            "Select dataset",
            list(data.keys()),
        )
        if selected and not data[selected].empty:
            st.dataframe(data[selected], use_container_width=True, height=400)


if __name__ == "__main__":
    main()
