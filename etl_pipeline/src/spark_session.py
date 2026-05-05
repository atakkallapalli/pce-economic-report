"""Spark session factory with Delta Lake and Hive support."""

from __future__ import annotations

import logging
from typing import Any

import yaml
from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession

logger = logging.getLogger(__name__)


def load_config(config_path: str = "etl_pipeline/config/pipeline_config.yaml") -> dict[str, Any]:
    """Load pipeline configuration from YAML."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def create_spark_session(config: dict[str, Any] | None = None) -> SparkSession:
    """Create a SparkSession configured for Delta Lake and Hive metastore.

    Enables:
    - Delta Lake read/write
    - Hive metastore for table cataloging
    - Local warehouse directory for managed tables
    """
    if config is None:
        config = load_config()

    spark_cfg = config["spark"]
    storage_cfg = config["storage"]

    builder = (
        SparkSession.builder
        .appName(spark_cfg["app_name"])
        .master(spark_cfg["master"])
        .config("spark.sql.warehouse.dir", spark_cfg["config"]["spark.sql.warehouse.dir"])
        .config("spark.driver.memory", spark_cfg["config"]["spark.driver.memory"])
        .config("spark.executor.memory", spark_cfg["config"]["spark.executor.memory"])
        .config(
            "spark.sql.extensions",
            spark_cfg["config"]["spark.sql.extensions"],
        )
        .config(
            "spark.sql.catalog.spark_catalog",
            spark_cfg["config"]["spark.sql.catalog.spark_catalog"],
        )
        .enableHiveSupport()
    )

    spark = configure_spark_with_delta_pip(builder).getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    logger.info("SparkSession created: %s", spark_cfg["app_name"])
    return spark
