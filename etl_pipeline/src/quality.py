"""Data quality checks for each pipeline layer."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from typing import Any

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

logger = logging.getLogger(__name__)


@dataclass
class QualityReport:
    """Container for data quality check results."""

    layer: str
    total_records: int = 0
    checks: list[dict[str, Any]] = field(default_factory=list)
    passed: bool = True

    def add_check(self, name: str, passed: bool, details: str = "") -> None:
        self.checks.append({"name": name, "passed": passed, "details": details})
        if not passed:
            self.passed = False

    def summary(self) -> str:
        status = "PASSED" if self.passed else "FAILED"
        lines = [f"Quality Report [{self.layer}] - {status} ({self.total_records} records)"]
        for check in self.checks:
            mark = "OK" if check["passed"] else "FAIL"
            lines.append(f"  [{mark}] {check['name']}: {check['details']}")
        return "\n".join(lines)


def check_bronze_quality(df: DataFrame, config: dict[str, Any]) -> QualityReport:
    """Validate the raw bronze data."""
    report = QualityReport(layer="bronze")
    report.total_records = df.count()

    # Check: non-empty
    report.add_check(
        "non_empty",
        report.total_records > 0,
        f"{report.total_records} records",
    )

    # Check: critical columns exist
    required_cols = [
        "tpep_pickup_datetime",
        "tpep_dropoff_datetime",
        "fare_amount",
        "trip_distance",
    ]
    missing = [c for c in required_cols if c not in df.columns]
    report.add_check(
        "required_columns",
        len(missing) == 0,
        f"missing: {missing}" if missing else "all present",
    )

    # Check: null rates for critical columns
    max_null_pct = config["quality"]["max_null_pct"]
    for col_name in required_cols:
        if col_name in df.columns:
            null_count = df.filter(F.col(col_name).isNull()).count()
            null_pct = null_count / report.total_records if report.total_records > 0 else 0
            report.add_check(
                f"null_rate_{col_name}",
                null_pct <= max_null_pct,
                f"{null_pct:.2%} null ({null_count} records)",
            )

    logger.info(report.summary())
    return report


def check_silver_quality(df: DataFrame, config: dict[str, Any]) -> QualityReport:
    """Validate the cleaned silver data."""
    report = QualityReport(layer="silver")
    report.total_records = df.count()

    report.add_check(
        "non_empty",
        report.total_records > 0,
        f"{report.total_records} records",
    )

    # Check: no nulls in critical columns after cleaning
    critical_cols = ["tpep_pickup_datetime", "tpep_dropoff_datetime", "fare_amount"]
    for col_name in critical_cols:
        null_count = df.filter(F.col(col_name).isNull()).count()
        report.add_check(
            f"no_nulls_{col_name}",
            null_count == 0,
            f"{null_count} nulls remaining",
        )

    # Check: derived columns exist
    derived = ["trip_duration_minutes", "avg_speed_mph", "fare_per_mile", "pickup_hour"]
    missing_derived = [c for c in derived if c not in df.columns]
    report.add_check(
        "derived_columns",
        len(missing_derived) == 0,
        f"missing: {missing_derived}" if missing_derived else "all present",
    )

    # Check: no negative fares
    neg_fares = df.filter(F.col("fare_amount") < 0).count()
    report.add_check("no_negative_fares", neg_fares == 0, f"{neg_fares} negative fares")

    # Check: reasonable trip durations
    bad_durations = df.filter(
        (F.col("trip_duration_minutes") <= 0)
        | (F.col("trip_duration_minutes") > config["quality"]["max_trip_duration_hours"] * 60)
    ).count()
    report.add_check(
        "valid_durations",
        bad_durations == 0,
        f"{bad_durations} invalid durations",
    )

    logger.info(report.summary())
    return report


def check_gold_quality(tables: dict[str, DataFrame]) -> QualityReport:
    """Validate the gold aggregation tables."""
    report = QualityReport(layer="gold")

    total = 0
    for table_name, df in tables.items():
        count = df.count()
        total += count
        report.add_check(
            f"{table_name}_non_empty",
            count > 0,
            f"{count} rows",
        )

    report.total_records = total
    logger.info(report.summary())
    return report


def save_quality_reports(
    reports: list[QualityReport],
    output_path: str = "etl_pipeline/output/quality_report.json",
) -> None:
    """Persist quality reports as JSON."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    data = [asdict(r) for r in reports]
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    logger.info("Quality reports saved to %s", output_path)
