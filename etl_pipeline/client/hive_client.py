"""Sample Hive client that connects to the Hive catalog and queries curated data.

Demonstrates querying Delta tables registered in the Hive metastore, running
analytical SQL queries, and exporting results to CSV/JSON for downstream use.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from typing import Any

import pandas as pd
from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

HIVE_DATABASE = "nyc_taxi_analytics"
OUTPUT_DIR = "etl_pipeline/output/client_exports"


def get_spark_session() -> SparkSession:
    """Create a SparkSession that connects to the existing Hive metastore."""
    builder = (
        SparkSession.builder
        .appName("NYC_Taxi_Hive_Client")
        .master("local[*]")
        .config("spark.sql.warehouse.dir", "./warehouse")
        .config(
            "spark.sql.extensions",
            "io.delta.sql.DeltaSparkSessionExtension",
        )
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
        .enableHiveSupport()
    )
    return configure_spark_with_delta_pip(builder).getOrCreate()


def list_tables(spark: SparkSession) -> list[str]:
    """List all tables in the analytics database."""
    spark.sql(f"USE {HIVE_DATABASE}")
    tables = spark.sql("SHOW TABLES").collect()
    table_names = [row.tableName for row in tables]
    logger.info("Available tables in %s: %s", HIVE_DATABASE, table_names)
    return table_names


def query_daily_summary(spark: SparkSession) -> pd.DataFrame:
    """Query daily trip summary with key metrics."""
    sql = f"""
        SELECT
            pickup_date,
            total_trips,
            ROUND(total_revenue, 2) AS total_revenue,
            ROUND(avg_fare, 2) AS avg_fare,
            ROUND(avg_trip_distance, 2) AS avg_distance_mi,
            ROUND(avg_trip_duration_min, 1) AS avg_duration_min,
            ROUND(avg_tip_pct, 1) AS avg_tip_pct,
            ROUND(avg_speed, 1) AS avg_speed_mph
        FROM {HIVE_DATABASE}.trip_summary_daily
        ORDER BY pickup_date
    """
    logger.info("Querying daily trip summary...")
    return spark.sql(sql).toPandas()


def query_top_routes(spark: SparkSession, top_n: int = 20) -> pd.DataFrame:
    """Query the most popular pickup-dropoff routes."""
    sql = f"""
        SELECT
            PULocationID AS pickup_zone,
            DOLocationID AS dropoff_zone,
            trip_count,
            ROUND(avg_fare, 2) AS avg_fare,
            ROUND(avg_distance, 2) AS avg_distance,
            ROUND(total_revenue, 2) AS total_revenue
        FROM {HIVE_DATABASE}.zone_performance
        ORDER BY trip_count DESC
        LIMIT {top_n}
    """
    logger.info("Querying top %d routes...", top_n)
    return spark.sql(sql).toPandas()


def query_hourly_demand(spark: SparkSession) -> pd.DataFrame:
    """Query hourly demand patterns."""
    sql = f"""
        SELECT
            pickup_hour,
            pickup_day_of_week,
            is_weekend,
            trip_count,
            ROUND(avg_fare, 2) AS avg_fare,
            ROUND(total_revenue, 2) AS total_revenue
        FROM {HIVE_DATABASE}.hourly_demand
        ORDER BY pickup_day_of_week, pickup_hour
    """
    logger.info("Querying hourly demand patterns...")
    return spark.sql(sql).toPandas()


def query_fare_breakdown(spark: SparkSession) -> pd.DataFrame:
    """Query fare analysis by distance and time of day."""
    sql = f"""
        SELECT
            distance_bucket,
            time_of_day,
            payment_type_desc,
            trip_count,
            ROUND(avg_fare, 2) AS avg_fare,
            ROUND(avg_tip, 2) AS avg_tip,
            ROUND(avg_fare_per_mile, 2) AS avg_fare_per_mile,
            ROUND(total_revenue, 2) AS total_revenue
        FROM {HIVE_DATABASE}.fare_analysis
        ORDER BY distance_bucket, time_of_day
    """
    logger.info("Querying fare breakdown...")
    return spark.sql(sql).toPandas()


def query_custom_sql(spark: SparkSession, sql: str) -> pd.DataFrame:
    """Run an arbitrary SQL query against the Hive catalog."""
    logger.info("Running custom SQL: %s", sql[:100])
    return spark.sql(sql).toPandas()


def export_results(
    results: dict[str, pd.DataFrame],
    output_dir: str = OUTPUT_DIR,
) -> None:
    """Export query results to CSV and JSON files."""
    os.makedirs(output_dir, exist_ok=True)

    for name, df in results.items():
        csv_path = os.path.join(output_dir, f"{name}.csv")
        json_path = os.path.join(output_dir, f"{name}.json")

        df.to_csv(csv_path, index=False)
        df.to_json(json_path, orient="records", indent=2, date_format="iso")
        logger.info("Exported %s: %d rows -> %s", name, len(df), csv_path)


def run_all_queries(spark: SparkSession) -> dict[str, pd.DataFrame]:
    """Execute all pre-built analytical queries."""
    return {
        "daily_summary": query_daily_summary(spark),
        "top_routes": query_top_routes(spark),
        "hourly_demand": query_hourly_demand(spark),
        "fare_breakdown": query_fare_breakdown(spark),
    }


def print_summary_stats(results: dict[str, pd.DataFrame]) -> None:
    """Print high-level summary statistics from query results."""
    daily = results["daily_summary"]
    routes = results["top_routes"]

    print("\n" + "=" * 60)
    print("NYC TAXI ANALYTICS - SUMMARY")
    print("=" * 60)

    if not daily.empty:
        print(f"\nDate range: {daily['pickup_date'].min()} to {daily['pickup_date'].max()}")
        print(f"Total trips: {daily['total_trips'].sum():,.0f}")
        print(f"Total revenue: ${daily['total_revenue'].sum():,.2f}")
        print(f"Avg fare: ${daily['avg_fare'].mean():.2f}")
        print(f"Avg trip distance: {daily['avg_distance_mi'].mean():.2f} miles")
        print(f"Avg trip duration: {daily['avg_duration_min'].mean():.1f} minutes")

    if not routes.empty:
        top_route = routes.iloc[0]
        print(f"\nBusiest route: Zone {top_route['pickup_zone']} -> Zone {top_route['dropoff_zone']}")
        print(f"  ({top_route['trip_count']:,.0f} trips, avg fare ${top_route['avg_fare']:.2f})")

    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="NYC Taxi Hive Client")
    parser.add_argument("--query", help="Custom SQL query to execute")
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export results to CSV/JSON",
    )
    args = parser.parse_args()

    spark = get_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    try:
        tables = list_tables(spark)
        if not tables:
            logger.error("No tables found. Run the ETL pipeline first.")
            return

        if args.query:
            result = query_custom_sql(spark, args.query)
            print(result.to_string())
            if args.export:
                export_results({"custom_query": result})
        else:
            results = run_all_queries(spark)
            print_summary_stats(results)
            if args.export:
                export_results(results)
                logger.info("Results exported to %s", OUTPUT_DIR)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
