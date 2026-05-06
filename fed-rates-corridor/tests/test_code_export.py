"""Unit tests for the code export module."""

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.components.code_export import (
    _dataframe_to_csv_string,
    export_data_csv,
    export_python_code,
    export_r_code,
)


@pytest.fixture
def sample_data():
    """Create sample rate data for testing."""
    dates = pd.date_range("2024-01-01", periods=30, freq="D")
    return {
        "DFF": pd.DataFrame({"value": [5.33] * 30}, index=dates),
        "SOFR": pd.DataFrame({"value": [5.31] * 30}, index=dates),
    }


@pytest.fixture
def sample_configs():
    """Create sample series configs."""
    return [
        {"series_id": "DFF", "label": "Fed Funds", "color": "#7030a0", "line_style": "solid"},
        {"series_id": "SOFR", "label": "SOFR", "color": "#548235", "line_style": "solid"},
    ]


class TestDataframeToCsv:
    """Tests for _dataframe_to_csv_string."""

    def test_basic_csv_generation(self, sample_data, sample_configs):
        csv = _dataframe_to_csv_string(sample_data, sample_configs)
        assert "date" in csv
        assert "DFF" in csv
        assert "SOFR" in csv

    def test_with_date_range(self, sample_data, sample_configs):
        date_range = (pd.Timestamp("2024-01-05"), pd.Timestamp("2024-01-15"))
        csv = _dataframe_to_csv_string(sample_data, sample_configs, date_range)
        lines = csv.strip().split("\n")
        assert len(lines) == 12  # header + 11 days

    def test_empty_data(self, sample_configs):
        csv = _dataframe_to_csv_string({}, sample_configs)
        assert csv == ""

    def test_missing_series(self, sample_data):
        configs = [{"series_id": "NONEXISTENT", "label": "X"}]
        csv = _dataframe_to_csv_string(sample_data, configs)
        assert csv == ""


class TestExportPythonCode:
    """Tests for Python code export."""

    def test_generates_valid_python(self, sample_data, sample_configs):
        code = export_python_code(sample_data, "Test", "Subtitle", sample_configs)
        assert "import matplotlib" in code
        assert "import pandas" in code
        assert "DATA_B64" in code

    def test_includes_embedded_data(self, sample_data, sample_configs):
        code = export_python_code(sample_data, "Test", "Sub", sample_configs)
        assert "base64" in code
        assert len(code) > 1000

    def test_escapes_special_characters(self, sample_data, sample_configs):
        code = export_python_code(sample_data, 'Rate "Corridor"', "Sub", sample_configs)
        assert 'Rate \\"Corridor\\"' in code

    def test_title_with_triple_quotes(self, sample_data, sample_configs):
        """Ensure triple quotes in title don't break the f-string."""
        code = export_python_code(sample_data, "Rate '''test'''", "Sub", sample_configs)
        assert code is not None
        assert len(code) > 100

    def test_with_date_range(self, sample_data, sample_configs):
        date_range = (pd.Timestamp("2024-01-05"), pd.Timestamp("2024-01-15"))
        code = export_python_code(sample_data, "Test", "Sub", sample_configs, date_range=date_range)
        assert "START_DATE" in code
        assert "2024-01-05" in code


class TestExportRCode:
    """Tests for R code export."""

    def test_generates_valid_r(self, sample_data, sample_configs):
        code = export_r_code(sample_data, "Test", "Subtitle", sample_configs)
        assert "csv_text" in code
        assert "read.csv" in code
        assert "png(" in code

    def test_includes_embedded_data(self, sample_data, sample_configs):
        code = export_r_code(sample_data, "Test", "Sub", sample_configs)
        assert "DFF" in code
        assert len(code) > 500

    def test_escapes_special_characters(self, sample_data, sample_configs):
        code = export_r_code(sample_data, 'Rate "Corridor"', "Sub", sample_configs)
        assert 'Rate \\"Corridor\\"' in code


class TestExportDataCsv:
    """Tests for CSV data export."""

    def test_basic_csv(self, sample_data, sample_configs):
        csv = export_data_csv(sample_data, sample_configs)
        assert "date" in csv
        assert "DFF" in csv
        assert "5.33" in csv

    def test_with_date_range(self, sample_data, sample_configs):
        date_range = (pd.Timestamp("2024-01-05"), pd.Timestamp("2024-01-15"))
        csv = export_data_csv(sample_data, sample_configs, date_range)
        lines = csv.strip().split("\n")
        assert len(lines) <= 12
