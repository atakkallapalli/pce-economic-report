"""Bronze layer: Extract raw NYC Taxi data from the TLC public dataset."""

from __future__ import annotations

import logging
import os
import urllib.request
from typing import Any

from pyspark.sql import DataFrame, SparkSession

logger = logging.getLogger(__name__)


def download_taxi_parquet(config: dict[str, Any]) -> list[str]:
    """Download NYC Yellow Taxi parquet files from the TLC public endpoint.

    Returns a list of local file paths for the downloaded parquets.
    """
    base_url = config["source"]["base_url"]
    dataset = config["source"]["dataset"]
    months = config["source"]["months"]
    download_dir = config["storage"]["raw_download_dir"]

    os.makedirs(download_dir, exist_ok=True)
    local_paths: list[str] = []

    for month in months:
        filename = f"{dataset}_{month}.parquet"
        url = f"{base_url}/{filename}"
        local_path = os.path.join(download_dir, filename)

        if os.path.exists(local_path):
            logger.info("Already downloaded: %s", local_path)
        else:
            logger.info("Downloading %s ...", url)
            urllib.request.urlretrieve(url, local_path)
            size_mb = os.path.getsize(local_path) / (1024 * 1024)
            logger.info("Downloaded %s (%.1f MB)", filename, size_mb)

        local_paths.append(local_path)

    return local_paths


def ingest_to_bronze(
    spark: SparkSession,
    config: dict[str, Any],
    local_paths: list[str],
) -> DataFrame:
    """Read raw parquet files and write them as a Delta table (Bronze layer).

    The bronze table preserves the raw schema with an added ingestion timestamp.
    """
    from pyspark.sql.functions import current_timestamp, input_file_name, lit

    bronze_path = config["storage"]["bronze_path"]
    hive_db = config["hive"]["database"]
    bronze_table = config["hive"]["tables"]["bronze"]

    df_raw = spark.read.parquet(*local_paths)

    df_bronze = (
        df_raw
        .withColumn("_ingestion_timestamp", current_timestamp())
        .withColumn("_source_file", input_file_name())
    )

    record_count = df_bronze.count()
    logger.info("Bronze layer: %d records from %d files", record_count, len(local_paths))

    df_bronze.write.format("delta").mode("overwrite").save(bronze_path)
    logger.info("Bronze Delta table written to %s", bronze_path)

    spark.sql(f"CREATE DATABASE IF NOT EXISTS {hive_db}")
    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {hive_db}.{bronze_table}
        USING DELTA
        LOCATION '{os.path.abspath(bronze_path)}'
    """)
    logger.info("Registered Hive table: %s.%s", hive_db, bronze_table)

    return df_bronze
