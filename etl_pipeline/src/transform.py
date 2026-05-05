"""Silver layer: Clean, validate, and enrich NYC Taxi trip data."""

from __future__ import annotations

import logging
import os
from typing import Any

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, IntegerType

logger = logging.getLogger(__name__)


def clean_and_enrich(
    spark: SparkSession,
    df_bronze: DataFrame,
    config: dict[str, Any],
) -> DataFrame:
    """Apply data quality filters and add derived columns.

    Transformations:
    - Drop records with null pickup/dropoff timestamps
    - Filter invalid fare amounts and trip distances
    - Compute trip duration in minutes
    - Compute average speed (mph)
    - Compute fare per mile
    - Extract time-based features (hour, day of week, month)
    - Classify trip distance buckets
    - Classify time-of-day periods
    """
    quality = config["quality"]

    df = df_bronze

    initial_count = df.count()
    logger.info("Silver: starting with %d records", initial_count)

    # --- Data cleaning ---
    df = df.dropna(subset=["tpep_pickup_datetime", "tpep_dropoff_datetime"])

    df = df.filter(
        (F.col("fare_amount") >= quality["min_fare_amount"])
        & (F.col("fare_amount") <= quality["max_fare_amount"])
    )
    df = df.filter(
        (F.col("trip_distance") >= quality["min_trip_distance"])
        & (F.col("trip_distance") <= quality["max_trip_distance"])
    )
    df = df.filter(
        (F.col("passenger_count") >= quality["min_passenger_count"])
        & (F.col("passenger_count") <= quality["max_passenger_count"])
    )

    # --- Derived columns ---
    df = df.withColumn(
        "trip_duration_minutes",
        (
            F.unix_timestamp("tpep_dropoff_datetime")
            - F.unix_timestamp("tpep_pickup_datetime")
        )
        / 60.0,
    )

    # Filter unreasonable durations
    max_duration_min = quality["max_trip_duration_hours"] * 60
    df = df.filter(
        (F.col("trip_duration_minutes") > 0)
        & (F.col("trip_duration_minutes") <= max_duration_min)
    )

    df = df.withColumn(
        "avg_speed_mph",
        F.when(
            F.col("trip_duration_minutes") > 0,
            (F.col("trip_distance") / (F.col("trip_duration_minutes") / 60.0)),
        ).otherwise(F.lit(0.0)),
    )
    # Cap unreasonable speeds
    df = df.filter(F.col("avg_speed_mph") <= 100.0)

    df = df.withColumn(
        "fare_per_mile",
        F.when(
            F.col("trip_distance") > 0,
            F.col("fare_amount") / F.col("trip_distance"),
        ).otherwise(F.lit(0.0)),
    )

    # --- Time features ---
    df = (
        df.withColumn("pickup_hour", F.hour("tpep_pickup_datetime"))
        .withColumn("pickup_day_of_week", F.dayofweek("tpep_pickup_datetime"))
        .withColumn("pickup_month", F.month("tpep_pickup_datetime"))
        .withColumn("pickup_date", F.to_date("tpep_pickup_datetime"))
        .withColumn(
            "is_weekend",
            F.when(
                F.dayofweek("tpep_pickup_datetime").isin(1, 7), F.lit(True)
            ).otherwise(F.lit(False)),
        )
    )

    # --- Categorical features ---
    df = df.withColumn(
        "distance_bucket",
        F.when(F.col("trip_distance") < 1, "short (<1mi)")
        .when(F.col("trip_distance") < 5, "medium (1-5mi)")
        .when(F.col("trip_distance") < 15, "long (5-15mi)")
        .otherwise("very_long (>15mi)"),
    )

    df = df.withColumn(
        "time_of_day",
        F.when(F.col("pickup_hour").between(6, 11), "morning")
        .when(F.col("pickup_hour").between(12, 17), "afternoon")
        .when(F.col("pickup_hour").between(18, 22), "evening")
        .otherwise("night"),
    )

    df = df.withColumn(
        "payment_type_desc",
        F.when(F.col("payment_type") == 1, "Credit Card")
        .when(F.col("payment_type") == 2, "Cash")
        .when(F.col("payment_type") == 3, "No Charge")
        .when(F.col("payment_type") == 4, "Dispute")
        .otherwise("Unknown"),
    )

    final_count = df.count()
    dropped = initial_count - final_count
    logger.info(
        "Silver: %d records after cleaning (dropped %d, %.1f%%)",
        final_count,
        dropped,
        (dropped / initial_count * 100) if initial_count > 0 else 0,
    )

    return df


def write_silver(
    spark: SparkSession,
    df_silver: DataFrame,
    config: dict[str, Any],
) -> None:
    """Persist the cleaned dataset as a partitioned Delta table (Silver layer)."""
    silver_path = config["storage"]["silver_path"]
    hive_db = config["hive"]["database"]
    silver_table = config["hive"]["tables"]["silver"]

    (
        df_silver.write.format("delta")
        .mode("overwrite")
        .partitionBy("pickup_month")
        .save(silver_path)
    )
    logger.info("Silver Delta table written to %s", silver_path)

    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {hive_db}.{silver_table}
        USING DELTA
        LOCATION '{os.path.abspath(silver_path)}'
    """)
    logger.info("Registered Hive table: %s.%s", hive_db, silver_table)
