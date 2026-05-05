"""Gold layer: Aggregate curated data products for analytics."""

from __future__ import annotations

import logging
import os
from typing import Any

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

logger = logging.getLogger(__name__)


def build_daily_trip_summary(
    spark: SparkSession,
    df_silver: DataFrame,
    config: dict[str, Any],
) -> DataFrame:
    """Gold table: Daily trip summary with key operational metrics."""
    df = (
        df_silver.groupBy("pickup_date")
        .agg(
            F.count("*").alias("total_trips"),
            F.sum("fare_amount").alias("total_fare_revenue"),
            F.sum("tip_amount").alias("total_tips"),
            F.sum("total_amount").alias("total_revenue"),
            F.avg("trip_distance").alias("avg_trip_distance"),
            F.avg("trip_duration_minutes").alias("avg_trip_duration_min"),
            F.avg("fare_amount").alias("avg_fare"),
            F.avg("tip_amount").alias("avg_tip"),
            F.avg("avg_speed_mph").alias("avg_speed"),
            F.sum("passenger_count").alias("total_passengers"),
            F.avg("passenger_count").alias("avg_passengers"),
            F.stddev("fare_amount").alias("fare_stddev"),
            F.percentile_approx("fare_amount", 0.5).alias("median_fare"),
        )
        .withColumn("avg_revenue_per_trip", F.col("total_revenue") / F.col("total_trips"))
        .withColumn("avg_tip_pct", F.when(F.col("total_fare_revenue") > 0, F.col("total_tips") / F.col("total_fare_revenue") * 100).otherwise(F.lit(0.0)))
        .orderBy("pickup_date")
    )

    gold_path = os.path.join(config["storage"]["gold_path"], "trip_summary_daily")
    hive_db = config["hive"]["database"]
    table_name = config["hive"]["tables"]["gold_trip_summary"]

    df.write.format("delta").mode("overwrite").save(gold_path)
    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {hive_db}.{table_name}
        USING DELTA LOCATION '{os.path.abspath(gold_path)}'
    """)
    logger.info("Gold table created: %s.%s (%d rows)", hive_db, table_name, df.count())
    return df


def build_zone_performance(
    spark: SparkSession,
    df_silver: DataFrame,
    config: dict[str, Any],
) -> DataFrame:
    """Gold table: Performance metrics by pickup/dropoff location zones."""
    df = (
        df_silver.groupBy("PULocationID", "DOLocationID")
        .agg(
            F.count("*").alias("trip_count"),
            F.avg("fare_amount").alias("avg_fare"),
            F.avg("tip_amount").alias("avg_tip"),
            F.avg("trip_distance").alias("avg_distance"),
            F.avg("trip_duration_minutes").alias("avg_duration_min"),
            F.sum("total_amount").alias("total_revenue"),
            F.avg("avg_speed_mph").alias("avg_speed"),
        )
        .withColumn("avg_fare_per_mile", F.when(F.col("avg_distance") > 0, F.col("avg_fare") / F.col("avg_distance")).otherwise(F.lit(0.0)))
        .filter(F.col("trip_count") >= 10)
        .orderBy(F.desc("trip_count"))
    )

    gold_path = os.path.join(config["storage"]["gold_path"], "zone_performance")
    hive_db = config["hive"]["database"]
    table_name = config["hive"]["tables"]["gold_zone_metrics"]

    df.write.format("delta").mode("overwrite").save(gold_path)
    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {hive_db}.{table_name}
        USING DELTA LOCATION '{os.path.abspath(gold_path)}'
    """)
    logger.info("Gold table created: %s.%s (%d rows)", hive_db, table_name, df.count())
    return df


def build_hourly_demand(
    spark: SparkSession,
    df_silver: DataFrame,
    config: dict[str, Any],
) -> DataFrame:
    """Gold table: Hourly demand patterns by day of week."""
    df = (
        df_silver.groupBy("pickup_hour", "pickup_day_of_week", "is_weekend")
        .agg(
            F.count("*").alias("trip_count"),
            F.avg("fare_amount").alias("avg_fare"),
            F.avg("trip_distance").alias("avg_distance"),
            F.avg("trip_duration_minutes").alias("avg_duration_min"),
            F.sum("total_amount").alias("total_revenue"),
        )
        .orderBy("pickup_day_of_week", "pickup_hour")
    )

    gold_path = os.path.join(config["storage"]["gold_path"], "hourly_demand")
    hive_db = config["hive"]["database"]
    table_name = config["hive"]["tables"]["gold_hourly_demand"]

    df.write.format("delta").mode("overwrite").save(gold_path)
    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {hive_db}.{table_name}
        USING DELTA LOCATION '{os.path.abspath(gold_path)}'
    """)
    logger.info("Gold table created: %s.%s (%d rows)", hive_db, table_name, df.count())
    return df


def build_fare_analysis(
    spark: SparkSession,
    df_silver: DataFrame,
    config: dict[str, Any],
) -> DataFrame:
    """Gold table: Fare analysis by distance bucket, time of day, and payment type."""
    df = (
        df_silver.groupBy("distance_bucket", "time_of_day", "payment_type_desc")
        .agg(
            F.count("*").alias("trip_count"),
            F.avg("fare_amount").alias("avg_fare"),
            F.avg("tip_amount").alias("avg_tip"),
            F.avg("fare_per_mile").alias("avg_fare_per_mile"),
            F.sum("total_amount").alias("total_revenue"),
            F.percentile_approx("fare_amount", 0.5).alias("median_fare"),
            F.percentile_approx("tip_amount", 0.5).alias("median_tip"),
        )
        .orderBy("distance_bucket", "time_of_day")
    )

    gold_path = os.path.join(config["storage"]["gold_path"], "fare_analysis")
    hive_db = config["hive"]["database"]
    table_name = config["hive"]["tables"]["gold_fare_analysis"]

    df.write.format("delta").mode("overwrite").save(gold_path)
    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {hive_db}.{table_name}
        USING DELTA LOCATION '{os.path.abspath(gold_path)}'
    """)
    logger.info("Gold table created: %s.%s (%d rows)", hive_db, table_name, df.count())
    return df


def build_all_gold_tables(
    spark: SparkSession,
    df_silver: DataFrame,
    config: dict[str, Any],
) -> dict[str, DataFrame]:
    """Build all gold-layer aggregation tables."""
    logger.info("Building Gold layer tables...")
    return {
        "trip_summary_daily": build_daily_trip_summary(spark, df_silver, config),
        "zone_performance": build_zone_performance(spark, df_silver, config),
        "hourly_demand": build_hourly_demand(spark, df_silver, config),
        "fare_analysis": build_fare_analysis(spark, df_silver, config),
    }
