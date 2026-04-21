"""
Tests for analyze_pce.py.

Uses synthetic CSV data from conftest.py fixtures — no network access needed.
"""

import json
import os
from unittest import mock

import numpy as np
import pandas as pd
import pytest

import analyze_pce


# ===================================================================
# Helper: load data with DATA_DIR pointed at the fixture directory
# ===================================================================

def _load_data_from(data_dir):
    """Call load_all_data() with DATA_DIR redirected to *data_dir*."""
    with mock.patch.object(analyze_pce, "DATA_DIR", str(data_dir)):
        return analyze_pce.load_all_data()


# ===================================================================
# load_series
# ===================================================================

class TestLoadSeries:
    """Tests for load_series()."""

    def test_returns_dataframe_with_date_index(self, data_dir):
        with mock.patch.object(analyze_pce, "DATA_DIR", str(data_dir)):
            df = analyze_pce.load_series("PCE")
        assert isinstance(df.index, pd.DatetimeIndex)
        assert df.index.name == "date"

    def test_column_matches_series_name(self, data_dir):
        with mock.patch.object(analyze_pce, "DATA_DIR", str(data_dir)):
            df = analyze_pce.load_series("PCEPI")
        assert "PCEPI" in df.columns

    def test_na_values_are_dropped(self, data_dir):
        """Rows with '.' (FRED's NA marker) should be dropped."""
        # Write a CSV with a '.' value
        csv_path = os.path.join(str(data_dir), "TESTNA.csv")
        with open(csv_path, "w") as f:
            f.write("observation_date,TESTNA\n")
            f.write("2024-01-01,100.0\n")
            f.write("2024-02-01,.\n")
            f.write("2024-03-01,102.0\n")

        with mock.patch.object(analyze_pce, "DATA_DIR", str(data_dir)):
            df = analyze_pce.load_series("TESTNA")

        assert len(df) == 2
        assert pd.Timestamp("2024-02-01") not in df.index

    def test_missing_file_raises(self, tmp_path):
        with mock.patch.object(analyze_pce, "DATA_DIR", str(tmp_path)):
            with pytest.raises(FileNotFoundError):
                analyze_pce.load_series("NONEXISTENT")


# ===================================================================
# load_all_data — derived metrics
# ===================================================================

class TestLoadAllData:
    """Tests for load_all_data() and its derived columns."""

    def test_returns_all_seven_keys(self, data_dir):
        data = _load_data_from(data_dir)
        expected_keys = {"pce", "pcepi", "pcepilfe", "pcedg", "pcend",
                         "pces", "pcec96"}
        assert set(data.keys()) == expected_keys

    def test_yoy_columns_exist(self, data_dir):
        data = _load_data_from(data_dir)
        for key in data:
            assert "pct_yoy" in data[key].columns, f"pct_yoy missing in {key}"

    def test_price_index_has_all_horizons(self, data_dir):
        data = _load_data_from(data_dir)
        for key in ("pcepi", "pcepilfe"):
            for col in ("pct_yoy", "pct_mom_ann", "pct_3m_ann", "pct_6m_ann"):
                assert col in data[key].columns, f"{col} missing in {key}"

    def test_yoy_first_12_are_nan(self, data_dir):
        """YoY requires 12 prior observations; first 12 should be NaN."""
        data = _load_data_from(data_dir)
        assert data["pcepi"]["pct_yoy"].iloc[:12].isna().all()

    def test_yoy_after_12_are_finite(self, data_dir):
        data = _load_data_from(data_dir)
        assert data["pcepi"]["pct_yoy"].iloc[12:].notna().all()

    def test_mom_annualized_formula(self, data_dir):
        """Verify MoM annualized matches the expected formula on synthetic data."""
        data = _load_data_from(data_dir)
        pcepi = data["pcepi"]
        # Manual calculation for the last row
        last = pcepi["PCEPI"].iloc[-1]
        prev = pcepi["PCEPI"].iloc[-2]
        expected = ((1 + (last / prev - 1)) ** 12 - 1) * 100
        actual = pcepi["pct_mom_ann"].iloc[-1]
        assert abs(actual - expected) < 1e-8

    def test_3m_annualized_formula(self, data_dir):
        """Verify 3-month annualized matches the expected formula."""
        data = _load_data_from(data_dir)
        pcepi = data["pcepi"]
        last = pcepi["PCEPI"].iloc[-1]
        three_ago = pcepi["PCEPI"].iloc[-4]
        expected = ((last / three_ago) ** 4 - 1) * 100
        actual = pcepi["pct_3m_ann"].iloc[-1]
        assert abs(actual - expected) < 1e-8

    def test_6m_annualized_formula(self, data_dir):
        """Verify 6-month annualized matches the expected formula."""
        data = _load_data_from(data_dir)
        pcepi = data["pcepi"]
        last = pcepi["PCEPI"].iloc[-1]
        six_ago = pcepi["PCEPI"].iloc[-7]
        expected = ((last / six_ago) ** 2 - 1) * 100
        actual = pcepi["pct_6m_ann"].iloc[-1]
        assert abs(actual - expected) < 1e-8

    def test_steady_growth_yoy_is_consistent(self, data_dir):
        """With 0.2% monthly growth, 12-month YoY should be ~2.43%."""
        data = _load_data_from(data_dir)
        yoy = data["pcepi"]["pct_yoy"].iloc[-1]
        expected_yoy = ((1.002 ** 12) - 1) * 100  # ~2.43 %
        assert abs(yoy - expected_yoy) < 0.01


# ===================================================================
# compute_stats
# ===================================================================

class TestComputeStats:
    """Tests for compute_stats()."""

    def test_returns_all_expected_keys(self, data_dir):
        data = _load_data_from(data_dir)
        stats = analyze_pce.compute_stats(data)
        expected_keys = {
            "latest_date", "pce_level", "pce_yoy",
            "real_pce_level", "real_pce_yoy",
            "pcepi_level", "headline_yoy", "headline_mom_ann",
            "headline_3m_ann", "headline_6m_ann",
            "core_level", "core_yoy", "core_mom_ann",
            "core_3m_ann", "core_6m_ann",
            "dg_share", "nd_share", "sv_share",
            "dg_yoy", "nd_yoy", "sv_yoy",
            "prev_headline_yoy", "prev_core_yoy", "prev_date",
        }
        assert set(stats.keys()) == expected_keys

    def test_shares_sum_to_roughly_100(self, data_dir):
        """Component shares (dg + nd + sv) should sum close to 100%."""
        data = _load_data_from(data_dir)
        stats = analyze_pce.compute_stats(data)
        total_share = (float(stats["dg_share"])
                       + float(stats["nd_share"])
                       + float(stats["sv_share"]))
        assert abs(total_share - 100.0) < 1.0

    def test_latest_date_is_formatted(self, data_dir):
        data = _load_data_from(data_dir)
        stats = analyze_pce.compute_stats(data)
        # Should be "Month YYYY" format, e.g. "December 2022"
        assert " " in stats["latest_date"]
        parts = stats["latest_date"].split()
        assert len(parts) == 2
        assert parts[1].isdigit()

    def test_stats_values_are_strings(self, data_dir):
        """All stat values should be formatted strings (for JSON output)."""
        data = _load_data_from(data_dir)
        stats = analyze_pce.compute_stats(data)
        for key, val in stats.items():
            assert isinstance(val, str), f"{key} is {type(val)}, expected str"

    def test_prev_date_differs_from_latest(self, data_dir):
        data = _load_data_from(data_dir)
        stats = analyze_pce.compute_stats(data)
        assert stats["prev_date"] != stats["latest_date"]


# ===================================================================
# Chart generation
# ===================================================================

class TestChartGeneration:
    """Tests that each chart function creates a PNG file without errors."""

    @pytest.fixture(autouse=True)
    def _setup_output(self, data_dir, output_dir):
        """Redirect DATA_DIR and OUTPUT_DIR for all chart tests."""
        self._data = _load_data_from(data_dir)
        self._output_dir = output_dir / "charts"
        self._patcher = mock.patch.object(
            analyze_pce, "OUTPUT_DIR", str(self._output_dir))
        self._patcher.start()
        yield
        self._patcher.stop()

    def _chart_exists(self, filename):
        path = os.path.join(str(self._output_dir), filename)
        return os.path.isfile(path) and os.path.getsize(path) > 0

    def test_chart_headline_vs_core(self):
        analyze_pce.chart_headline_vs_core(self._data)
        assert self._chart_exists("01_headline_vs_core_inflation.png")

    def test_chart_multi_horizon(self):
        analyze_pce.chart_multi_horizon(self._data)
        assert self._chart_exists("02_multi_horizon_inflation.png")

    def test_chart_nominal_pce(self):
        analyze_pce.chart_nominal_pce(self._data)
        assert self._chart_exists("03_nominal_pce_level_growth.png")

    def test_chart_real_pce(self):
        analyze_pce.chart_real_pce(self._data)
        assert self._chart_exists("04_real_pce.png")

    def test_chart_components_growth(self):
        analyze_pce.chart_components_growth(self._data)
        assert self._chart_exists("05_pce_components_growth.png")

    def test_chart_composition(self):
        analyze_pce.chart_composition(self._data)
        assert self._chart_exists("06_pce_composition.png")

    def test_chart_long_run_history(self):
        analyze_pce.chart_long_run_history(self._data)
        assert self._chart_exists("07_long_run_inflation_history.png")

    def test_chart_monthly_bars(self):
        analyze_pce.chart_monthly_bars(self._data)
        assert self._chart_exists("08_monthly_inflation_bars.png")


# ===================================================================
# main() integration
# ===================================================================

class TestMainIntegration:
    """Lightweight integration test for main()."""

    def test_main_produces_stats_and_charts(self, data_dir, output_dir):
        charts_dir = output_dir / "charts"
        stats_path = output_dir / "stats.json"

        with mock.patch.object(analyze_pce, "DATA_DIR", str(data_dir)), \
             mock.patch.object(analyze_pce, "OUTPUT_DIR", str(charts_dir)), \
             mock.patch.object(analyze_pce, "STATS_PATH", str(stats_path)):
            analyze_pce.main()

        # stats.json should exist and be valid JSON
        assert stats_path.exists()
        with open(stats_path) as f:
            stats = json.load(f)
        assert "headline_yoy" in stats

        # All 8 chart PNGs should exist
        chart_files = list(charts_dir.glob("*.png"))
        assert len(chart_files) == 8


# ===================================================================
# add_recession_shading helper
# ===================================================================

class TestRecessionShading:
    """Tests for the add_recession_shading helper."""

    def test_adds_patches_to_axes(self):
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        initial_patches = len(ax.patches)
        analyze_pce.add_recession_shading(ax)
        assert len(ax.patches) == initial_patches + len(analyze_pce.RECESSIONS)
        plt.close(fig)

    def test_recessions_list_is_not_empty(self):
        assert len(analyze_pce.RECESSIONS) > 0

    def test_recession_dates_are_valid(self):
        for start, end in analyze_pce.RECESSIONS:
            s = pd.Timestamp(start)
            e = pd.Timestamp(end)
            assert e > s, f"Recession end {end} is not after start {start}"
