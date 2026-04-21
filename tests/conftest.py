"""
Shared pytest fixtures for PCE economic report tests.

Provides synthetic FRED-like CSV data so tests run without network access.
"""

import os
import tempfile

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helpers to generate synthetic monthly series
# ---------------------------------------------------------------------------

def _monthly_dates(start="2020-01-01", periods=36):
    """Return a DatetimeIndex of monthly start-of-month dates."""
    return pd.date_range(start=start, periods=periods, freq="MS")


def _write_fred_csv(path, series_id, dates, values):
    """Write a CSV in FRED's public-endpoint format."""
    df = pd.DataFrame({"observation_date": dates, series_id: values})
    df.to_csv(path, index=False)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def data_dir(tmp_path):
    """Create a temp directory with synthetic CSVs for all 7 FRED series.

    The price-index series (PCEPI, PCEPILFE) grow at a steady ~0.2 % per
    month so that annualized inflation numbers are deterministic and easy
    to verify.  Level series (PCE, PCEC96, PCEDG, PCEND, PCES) are simple
    round numbers that make share arithmetic trivial.
    """
    dates = _monthly_dates("2020-01-01", periods=36)

    # Price indices: start at 100, grow 0.2 % each month
    pcepi_vals = [100.0 * (1.002 ** i) for i in range(36)]
    pcepilfe_vals = [100.0 * (1.0015 ** i) for i in range(36)]

    # Level series (billions $, SAAR)
    pce_vals = [15000.0 + i * 50 for i in range(36)]
    pcec96_vals = [13000.0 + i * 30 for i in range(36)]
    # Components that sum to roughly PCE
    pcedg_vals = [1500.0 + i * 5 for i in range(36)]
    pcend_vals = [3500.0 + i * 10 for i in range(36)]
    pces_vals = [10000.0 + i * 35 for i in range(36)]

    series_map = {
        "PCE": pce_vals,
        "PCEPI": pcepi_vals,
        "PCEPILFE": pcepilfe_vals,
        "PCEC96": pcec96_vals,
        "PCEDG": pcedg_vals,
        "PCEND": pcend_vals,
        "PCES": pces_vals,
    }

    for sid, vals in series_map.items():
        _write_fred_csv(
            os.path.join(tmp_path, f"{sid}.csv"),
            sid,
            dates,
            vals,
        )

    return tmp_path


@pytest.fixture()
def output_dir(tmp_path):
    """Return a temp directory for chart / stats output."""
    charts = tmp_path / "charts"
    charts.mkdir()
    return tmp_path
