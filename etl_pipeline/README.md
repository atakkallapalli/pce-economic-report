# NYC Taxi ETL Pipeline

End-to-end PySpark ETL pipeline implementing a **medallion architecture** (Bronze → Silver → Gold) with **Delta Lake** storage and **Hive metastore** cataloging. Includes a sample Hive client and a Streamlit analytics dashboard.

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  NYC TLC     │    │   Bronze    │    │   Silver    │    │    Gold     │
│  Public Data │───>│  Raw Delta  │───>│  Cleaned &  │───>│ Aggregated  │
│  (Parquet)   │    │  + Hive     │    │  Enriched   │    │  Analytics  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                               │
                                                               v
                                                    ┌─────────────────────┐
                                                    │  Hive Client        │
                                                    │  (SQL Queries)      │
                                                    │         │           │
                                                    │         v           │
                                                    │  Streamlit          │
                                                    │  Dashboard          │
                                                    └─────────────────────┘
```

## Dataset

**NYC Yellow Taxi Trip Records** from the [TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page) — one of the most widely-used public datasets for big data demonstrations.

- Format: Parquet
- Volume: ~3M+ records per month (~40-60 MB each)
- Default config processes 3 months (Jan-Mar 2024): ~9M+ records

## Data Layers

### Bronze (Raw)
- Raw parquet ingested as-is into Delta format
- Adds `_ingestion_timestamp` and `_source_file` metadata
- Registered as `nyc_taxi_analytics.yellow_taxi_raw` in Hive

### Silver (Cleaned & Enriched)
- Null/invalid record filtering
- Data quality enforcement (fare ranges, distance limits, passenger count)
- Derived columns:
  - `trip_duration_minutes`, `avg_speed_mph`, `fare_per_mile`
  - `pickup_hour`, `pickup_day_of_week`, `pickup_month`, `is_weekend`
  - `distance_bucket`, `time_of_day`, `payment_type_desc`
- Partitioned by `pickup_month`
- Registered as `nyc_taxi_analytics.yellow_taxi_cleaned` in Hive

### Gold (Analytics-Ready)
Four curated aggregation tables:

| Hive Table | Description |
|---|---|
| `trip_summary_daily` | Daily trip counts, revenue, avg fare/distance/duration |
| `zone_performance` | Metrics by pickup/dropoff location zone pair |
| `hourly_demand` | Hourly demand patterns by day of week |
| `fare_analysis` | Fare breakdown by distance bucket, time of day, payment type |

## Quick Start

### Prerequisites
- Python 3.10+
- Java 11 or 17 (for Spark)

### Install Dependencies

```bash
pip install -r etl_pipeline/requirements.txt
```

### Run the ETL Pipeline

```bash
# From the repository root
python -m etl_pipeline.src.pipeline
```

This will:
1. Download NYC Taxi parquet files from the TLC public endpoint
2. Ingest raw data into Bronze Delta table
3. Clean and enrich into Silver Delta table
4. Build four Gold aggregation Delta tables
5. Register all tables in the Hive metastore
6. Run data quality checks and save reports

### Run the Hive Client

```bash
# List tables and run all pre-built queries
python -m etl_pipeline.client.hive_client

# Export results to CSV/JSON for the dashboard
python -m etl_pipeline.client.hive_client --export

# Run a custom SQL query
python -m etl_pipeline.client.hive_client --query "SELECT * FROM nyc_taxi_analytics.trip_summary_daily LIMIT 10"
```

### Launch the Dashboard

```bash
streamlit run etl_pipeline/client/dashboard.py
```

The dashboard provides interactive visualizations:
- **KPI Cards**: Total trips, revenue, avg fare, avg distance
- **Trip Trends**: Daily volume + revenue time series
- **Demand Heatmap**: Hour × day-of-week trip intensity
- **Weekday vs Weekend**: Hourly demand comparison
- **Fare Analysis**: By distance bucket and time of day
- **Payment & Tipping**: Revenue by payment type, fare vs tip
- **Top Routes**: Most popular pickup-dropoff zone pairs

### Run Tests

```bash
pytest etl_pipeline/tests/ -v
```

## Project Structure

```
etl_pipeline/
├── config/
│   └── pipeline_config.yaml    # All pipeline settings
├── src/
│   ├── __init__.py
│   ├── spark_session.py        # Spark + Delta + Hive session factory
│   ├── extract.py              # Bronze: download & ingest raw data
│   ├── transform.py            # Silver: clean, validate, enrich
│   ├── load.py                 # Gold: aggregate curated tables
│   ├── quality.py              # Data quality framework
│   └── pipeline.py             # End-to-end orchestrator
├── client/
│   ├── __init__.py
│   ├── hive_client.py          # Sample Hive catalog client
│   └── dashboard.py            # Streamlit analytics dashboard
├── tests/
│   ├── __init__.py
│   └── test_pipeline.py        # Unit tests
├── requirements.txt
└── README.md
```

## Configuration

All pipeline settings are in `etl_pipeline/config/pipeline_config.yaml`:

- **source**: Dataset URL, months to ingest
- **spark**: App name, memory settings, Delta/Hive extensions
- **storage**: Lakehouse paths (bronze/silver/gold)
- **hive**: Database name, table names
- **quality**: Data quality thresholds (null %, fare/distance ranges)
