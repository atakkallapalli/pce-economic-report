"""End-to-end pipeline orchestrator for the NYC Taxi ETL job."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from typing import Any

from etl_pipeline.src.extract import download_taxi_parquet, ingest_to_bronze
from etl_pipeline.src.load import build_all_gold_tables
from etl_pipeline.src.quality import (
    QualityReport,
    check_bronze_quality,
    check_gold_quality,
    check_silver_quality,
    save_quality_reports,
)
from etl_pipeline.src.spark_session import create_spark_session, load_config
from etl_pipeline.src.transform import clean_and_enrich, write_silver

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_pipeline(config_path: str = "etl_pipeline/config/pipeline_config.yaml") -> None:
    """Execute the full Bronze -> Silver -> Gold ETL pipeline."""
    start = time.time()
    config = load_config(config_path)

    logger.info("=" * 60)
    logger.info("NYC Taxi ETL Pipeline - Starting")
    logger.info("=" * 60)

    quality_reports: list[QualityReport] = []

    # --- Step 1: Create Spark session ---
    logger.info("Step 1/6: Creating Spark session with Delta Lake + Hive support")
    spark = create_spark_session(config)

    try:
        # --- Step 2: Extract (download raw data) ---
        logger.info("Step 2/6: Downloading NYC Taxi data")
        local_paths = download_taxi_parquet(config)

        # --- Step 3: Bronze layer (raw ingest) ---
        logger.info("Step 3/6: Ingesting to Bronze layer (Delta)")
        df_bronze = ingest_to_bronze(spark, config, local_paths)
        bronze_report = check_bronze_quality(df_bronze, config)
        quality_reports.append(bronze_report)

        # --- Step 4: Silver layer (clean + enrich) ---
        logger.info("Step 4/6: Transforming to Silver layer")
        df_silver = clean_and_enrich(spark, df_bronze, config)
        write_silver(spark, df_silver, config)
        silver_report = check_silver_quality(df_silver, config)
        quality_reports.append(silver_report)

        # --- Step 5: Gold layer (aggregations) ---
        logger.info("Step 5/6: Building Gold layer aggregation tables")
        gold_tables = build_all_gold_tables(spark, df_silver, config)
        gold_report = check_gold_quality(gold_tables)
        quality_reports.append(gold_report)

        # --- Step 6: Quality reports ---
        logger.info("Step 6/6: Saving quality reports")
        save_quality_reports(quality_reports)

        # --- Summary ---
        elapsed = time.time() - start
        logger.info("=" * 60)
        logger.info("Pipeline completed in %.1f seconds", elapsed)
        logger.info("=" * 60)

        hive_db = config["hive"]["database"]
        logger.info("Hive catalog tables:")
        spark.sql(f"SHOW TABLES IN {hive_db}").show(truncate=False)

        all_passed = all(r.passed for r in quality_reports)
        if not all_passed:
            logger.warning("Some quality checks FAILED - review the quality report")
            sys.exit(1)

        logger.info("All quality checks PASSED")

    finally:
        spark.stop()
        logger.info("Spark session stopped")


def main() -> None:
    parser = argparse.ArgumentParser(description="NYC Taxi ETL Pipeline")
    parser.add_argument(
        "--config",
        default="etl_pipeline/config/pipeline_config.yaml",
        help="Path to pipeline configuration YAML",
    )
    args = parser.parse_args()
    run_pipeline(args.config)


if __name__ == "__main__":
    main()
