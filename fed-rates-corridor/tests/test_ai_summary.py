"""Unit tests for the AI summary module."""

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.components.ai_summary import (
    _compute_rate_stats,
    generate_economist_summary,
    generate_executive_summary,
    generate_public_summary,
    generate_summary,
)


@pytest.fixture
def sample_data():
    """Create sample rate data for testing."""
    dates = pd.date_range("2024-01-01", periods=365, freq="D")
    data = {
        "DFEDTARU": pd.DataFrame({"value": [5.50] * 365}, index=dates),
        "DFEDTARL": pd.DataFrame({"value": [5.25] * 365}, index=dates),
        "DFF": pd.DataFrame({"value": [5.33] * 365}, index=dates),
        "IORB": pd.DataFrame({"value": [5.40] * 365}, index=dates),
        "SOFR": pd.DataFrame({"value": [5.31] * 365}, index=dates),
        "TGCRRATE": pd.DataFrame({"value": [5.30] * 365}, index=dates),
        "RRPONTSYAWARD": pd.DataFrame({"value": [5.30] * 365}, index=dates),
        "SRFTSYD": pd.DataFrame({"value": [5.50] * 365}, index=dates),
    }
    return data


@pytest.fixture
def empty_data():
    """Create empty data dict."""
    return {}


class TestComputeRateStats:
    """Tests for _compute_rate_stats."""

    def test_computes_stats_for_all_series(self, sample_data):
        stats = _compute_rate_stats(sample_data)
        assert "DFEDTARU" in stats
        assert "DFEDTARL" in stats
        assert "DFF" in stats
        assert "_corridor" in stats

    def test_corridor_metrics(self, sample_data):
        stats = _compute_rate_stats(sample_data)
        corridor = stats["_corridor"]
        assert corridor["upper"] == 5.50
        assert corridor["lower"] == 5.25
        assert corridor["width_bps"] == 25

    def test_latest_values(self, sample_data):
        stats = _compute_rate_stats(sample_data)
        assert stats["DFF"]["latest"] == 5.33
        assert stats["IORB"]["latest"] == 5.40

    def test_empty_data(self, empty_data):
        stats = _compute_rate_stats(empty_data)
        assert stats == {}

    def test_handles_empty_dataframe(self):
        data = {"DFF": pd.DataFrame({"value": []}, index=pd.DatetimeIndex([]))}
        stats = _compute_rate_stats(data)
        assert "DFF" not in stats


class TestGenerateEconomistSummary:
    """Tests for economist summary generation."""

    def test_generates_markdown(self, sample_data):
        summary = generate_economist_summary(sample_data, "Test")
        assert "## Technical Analysis" in summary
        assert "Test" in summary

    def test_includes_corridor_analysis(self, sample_data):
        summary = generate_economist_summary(sample_data)
        assert "Policy Stance" in summary
        assert "5.25" in summary
        assert "5.50" in summary

    def test_includes_spread_analysis(self, sample_data):
        summary = generate_economist_summary(sample_data)
        assert "Spread Analysis" in summary

    def test_includes_rate_positioning(self, sample_data):
        summary = generate_economist_summary(sample_data)
        assert "Corridor Rate Positioning" in summary


class TestGenerateExecutiveSummary:
    """Tests for executive summary generation."""

    def test_generates_markdown(self, sample_data):
        summary = generate_executive_summary(sample_data)
        assert "Executive" in summary or "Bottom Line" in summary

    def test_includes_metrics(self, sample_data):
        summary = generate_executive_summary(sample_data)
        assert "5.33" in summary or "DFF" in summary

    def test_concise_format(self, sample_data):
        summary = generate_executive_summary(sample_data)
        lines = summary.strip().split("\n")
        assert len(lines) < 50


class TestGeneratePublicSummary:
    """Tests for public-facing summary generation."""

    def test_generates_markdown(self, sample_data):
        summary = generate_public_summary(sample_data)
        assert "Plain" in summary or "What" in summary

    def test_no_jargon(self, sample_data):
        summary = generate_public_summary(sample_data)
        assert "mortgage" in summary.lower() or "savings" in summary.lower()


class TestGenerateSummary:
    """Tests for the dispatcher function."""

    def test_economist_persona(self, sample_data):
        summary = generate_summary(sample_data, "economist")
        assert "Technical Analysis" in summary

    def test_executive_persona(self, sample_data):
        summary = generate_summary(sample_data, "executive")
        assert len(summary) > 0

    def test_public_persona(self, sample_data):
        summary = generate_summary(sample_data, "public")
        assert len(summary) > 0

    def test_invalid_persona_raises(self, sample_data):
        with pytest.raises(ValueError):
            generate_summary(sample_data, "invalid_persona")


class TestEdgeCases:
    """Tests for edge cases."""

    def test_zero_change_labels_unchanged(self):
        """When rates haven't changed YoY, should say 'unchanged' not 'tightening'."""
        dates = pd.date_range("2023-01-01", periods=400, freq="D")
        data = {
            "DFEDTARU": pd.DataFrame({"value": [5.50] * 400}, index=dates),
            "DFEDTARL": pd.DataFrame({"value": [5.25] * 400}, index=dates),
            "DFF": pd.DataFrame({"value": [5.33] * 400}, index=dates),
        }
        summary = generate_economist_summary(data)
        assert "unchanged" in summary

    def test_atypical_corridor_status(self):
        """When DFF is outside typical range, status should say 'atypical'."""
        dates = pd.date_range("2024-01-01", periods=365, freq="D")
        data = {
            "DFEDTARU": pd.DataFrame({"value": [5.50] * 365}, index=dates),
            "DFEDTARL": pd.DataFrame({"value": [5.25] * 365}, index=dates),
            "DFF": pd.DataFrame({"value": [5.26] * 365}, index=dates),
        }
        summary = generate_economist_summary(data)
        assert "atypical" in summary
        assert "outside typical range" in summary
