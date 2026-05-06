"""Unit tests for the Fed chart templates module."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.templates.fed_templates import (
    TEMPLATE_CATALOG,
    ChartTemplate,
    SeriesConfig,
    get_template,
    list_templates,
)


class TestTemplateCatalog:
    """Tests for template catalog."""

    def test_has_five_templates(self):
        assert len(TEMPLATE_CATALOG) == 5

    def test_required_templates_exist(self):
        expected = [
            "rate_corridor",
            "fed_funds_target",
            "overnight_rates",
            "iorb_framework",
            "repo_rates",
        ]
        for name in expected:
            assert name in TEMPLATE_CATALOG

    def test_all_templates_are_chart_template(self):
        for template in TEMPLATE_CATALOG.values():
            assert isinstance(template, ChartTemplate)

    def test_all_series_are_series_config(self):
        for template in TEMPLATE_CATALOG.values():
            for series in template.series:
                assert isinstance(series, SeriesConfig)


class TestGetTemplate:
    """Tests for get_template function."""

    def test_valid_template(self):
        template = get_template("rate_corridor")
        assert template.name == "rate_corridor"
        assert len(template.series) > 0

    def test_invalid_template_raises(self):
        with pytest.raises(ValueError, match="not found"):
            get_template("nonexistent_template")

    def test_rate_corridor_has_all_series(self):
        template = get_template("rate_corridor")
        series_ids = [s.series_id for s in template.series]
        assert "DFEDTARU" in series_ids
        assert "DFEDTARL" in series_ids
        assert "DFF" in series_ids


class TestListTemplates:
    """Tests for list_templates function."""

    def test_returns_list(self):
        templates = list_templates()
        assert isinstance(templates, list)
        assert len(templates) == 5

    def test_has_required_keys(self):
        templates = list_templates()
        for t in templates:
            assert "name" in t
            assert "title" in t


class TestSeriesConfig:
    """Tests for SeriesConfig dataclass."""

    def test_defaults(self):
        config = SeriesConfig(series_id="TEST", label="Test", color="#000")
        assert config.line_style == "solid"
        assert config.line_width == 1.6

    def test_custom_values(self):
        config = SeriesConfig(
            series_id="X", label="Y", color="#fff", line_style="dashed", line_width=2.5
        )
        assert config.line_style == "dashed"
        assert config.line_width == 2.5


class TestChartTemplate:
    """Tests for ChartTemplate dataclass."""

    def test_defaults(self):
        template = ChartTemplate(name="test", title="Test", subtitle="Sub", description="Desc")
        assert template.show_recession_shading is True
        assert template.show_corridor_fill is False
        assert template.y_axis_label == "Percent"
