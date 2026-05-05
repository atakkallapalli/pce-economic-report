"""Unit tests for the ETL pipeline components."""

from __future__ import annotations

import os
import tempfile

import pytest
from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

from etl_pipeline.src.quality import QualityReport, check_silver_quality
from etl_pipeline.src.spark_session import load_config
from etl_pipeline.src.transform import clean_and_enrich


@pytest.fixture(scope="session")
def spark():
    """Create a test SparkSession with Delta support."""
    builder = (
        SparkSession.builder
        .appName("ETL_Pipeline_Tests")
        .master("local[2]")
        .config("spark.sql.warehouse.dir", tempfile.mkdtemp())
        .config(
            "spark.sql.extensions",
            "io.delta.sql.DeltaSparkSessionExtension",
        )
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
        .config("spark.driver.memory", "2g")
    )
    session = configure_spark_with_delta_pip(builder).getOrCreate()
    session.sparkContext.setLogLevel("ERROR")
    yield session
    session.stop()


@pytest.fixture
def sample_taxi_df(spark):
    """Create a sample DataFrame mimicking NYC Taxi raw data."""
    from datetime import datetime

    schema = StructType([
        StructField("VendorID", IntegerType(), True),
        StructField("tpep_pickup_datetime", TimestampType(), True),
        StructField("tpep_dropoff_datetime", TimestampType(), True),
        StructField("passenger_count", IntegerType(), True),
        StructField("trip_distance", DoubleType(), True),
        StructField("PULocationID", IntegerType(), True),
        StructField("DOLocationID", IntegerType(), True),
        StructField("payment_type", IntegerType(), True),
        StructField("fare_amount", DoubleType(), True),
        StructField("tip_amount", DoubleType(), True),
        StructField("total_amount", DoubleType(), True),
    ])

    data = [
        # Valid trips
        (1, datetime(2024, 1, 15, 8, 30), datetime(2024, 1, 15, 8, 50), 2, 3.5, 161, 237, 1, 15.0, 3.0, 20.3),
        (2, datetime(2024, 1, 15, 9, 0), datetime(2024, 1, 15, 9, 15), 1, 1.2, 43, 239, 1, 8.5, 2.0, 12.8),
        (1, datetime(2024, 1, 15, 14, 0), datetime(2024, 1, 15, 14, 45), 3, 8.0, 132, 48, 2, 32.0, 0.0, 35.5),
        (2, datetime(2024, 1, 15, 22, 0), datetime(2024, 1, 15, 22, 10), 1, 2.0, 236, 141, 1, 10.0, 2.5, 15.3),
        (1, datetime(2024, 2, 1, 7, 0), datetime(2024, 2, 1, 7, 20), 1, 4.5, 161, 100, 1, 18.0, 4.0, 24.8),
        # Invalid: negative fare
        (1, datetime(2024, 1, 15, 10, 0), datetime(2024, 1, 15, 10, 15), 1, 2.0, 100, 200, 1, -5.0, 0.0, -5.0),
        # Invalid: excessive distance
        (1, datetime(2024, 1, 15, 11, 0), datetime(2024, 1, 15, 11, 15), 1, 999.0, 100, 200, 1, 10.0, 0.0, 10.0),
        # Invalid: null pickup
        (1, None, datetime(2024, 1, 15, 12, 0), 1, 2.0, 100, 200, 1, 10.0, 0.0, 10.0),
        # Invalid: too many passengers
        (1, datetime(2024, 1, 15, 13, 0), datetime(2024, 1, 15, 13, 15), 20, 2.0, 100, 200, 1, 10.0, 0.0, 10.0),
    ]

    return spark.createDataFrame(data, schema)


@pytest.fixture
def config():
    """Load the test config."""
    config_path = "etl_pipeline/config/pipeline_config.yaml"
    if os.path.exists(config_path):
        return load_config(config_path)
    return {
        "quality": {
            "max_null_pct": 0.10,
            "min_fare_amount": 0.0,
            "max_fare_amount": 1000.0,
            "min_trip_distance": 0.0,
            "max_trip_distance": 200.0,
            "min_passenger_count": 0,
            "max_passenger_count": 9,
            "max_trip_duration_hours": 24.0,
        }
    }


class TestDataCleaning:
    """Tests for the Silver-layer transformation logic."""

    def test_removes_null_timestamps(self, spark, sample_taxi_df, config):
        result = clean_and_enrich(spark, sample_taxi_df, config)
        null_pickups = result.filter(F.col("tpep_pickup_datetime").isNull()).count()
        assert null_pickups == 0

    def test_removes_negative_fares(self, spark, sample_taxi_df, config):
        result = clean_and_enrich(spark, sample_taxi_df, config)
        neg_fares = result.filter(F.col("fare_amount") < 0).count()
        assert neg_fares == 0

    def test_removes_excessive_distance(self, spark, sample_taxi_df, config):
        result = clean_and_enrich(spark, sample_taxi_df, config)
        bad_dist = result.filter(F.col("trip_distance") > 200).count()
        assert bad_dist == 0

    def test_removes_excessive_passengers(self, spark, sample_taxi_df, config):
        result = clean_and_enrich(spark, sample_taxi_df, config)
        bad_pax = result.filter(F.col("passenger_count") > 9).count()
        assert bad_pax == 0

    def test_adds_derived_columns(self, spark, sample_taxi_df, config):
        result = clean_and_enrich(spark, sample_taxi_df, config)
        expected_cols = [
            "trip_duration_minutes",
            "avg_speed_mph",
            "fare_per_mile",
            "pickup_hour",
            "pickup_day_of_week",
            "pickup_month",
            "pickup_date",
            "is_weekend",
            "distance_bucket",
            "time_of_day",
            "payment_type_desc",
        ]
        for col in expected_cols:
            assert col in result.columns, f"Missing column: {col}"

    def test_trip_duration_positive(self, spark, sample_taxi_df, config):
        result = clean_and_enrich(spark, sample_taxi_df, config)
        neg_duration = result.filter(F.col("trip_duration_minutes") <= 0).count()
        assert neg_duration == 0

    def test_valid_record_count(self, spark, sample_taxi_df, config):
        result = clean_and_enrich(spark, sample_taxi_df, config)
        assert result.count() == 5


class TestQualityReport:
    """Tests for the quality check framework."""

    def test_quality_report_passed(self):
        report = QualityReport(layer="test")
        report.add_check("check1", True, "ok")
        assert report.passed is True

    def test_quality_report_failed(self):
        report = QualityReport(layer="test")
        report.add_check("check1", False, "bad data")
        assert report.passed is False

    def test_quality_report_summary(self):
        report = QualityReport(layer="test", total_records=100)
        report.add_check("check1", True, "ok")
        summary = report.summary()
        assert "PASSED" in summary
        assert "100 records" in summary

    def test_silver_quality_check(self, spark, sample_taxi_df, config):
        result = clean_and_enrich(spark, sample_taxi_df, config)
        report = check_silver_quality(result, config)
        assert report.passed is True
