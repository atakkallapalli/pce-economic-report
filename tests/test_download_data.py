"""
Tests for download_data.py.

All network access is mocked so tests run offline.
"""

import os
from unittest import mock

import pytest

import download_data


class TestDownloadSeries:
    """Tests for download_series()."""

    def test_successful_download(self, tmp_path):
        """download_series writes a file and returns its path."""
        fake_csv = "observation_date,PCE\n2024-01-01,15000.0\n"

        def fake_urlretrieve(url, filepath):
            with open(filepath, "w") as f:
                f.write(fake_csv)

        with mock.patch("download_data.urllib.request.urlretrieve",
                        side_effect=fake_urlretrieve):
            path = download_data.download_series("PCE", str(tmp_path))

        assert os.path.exists(path)
        assert path == os.path.join(str(tmp_path), "PCE.csv")
        with open(path) as f:
            assert "observation_date" in f.read()

    def test_download_builds_correct_url(self, tmp_path):
        """The URL contains the series id."""
        captured_url = {}

        def spy_urlretrieve(url, filepath):
            captured_url["url"] = url
            with open(filepath, "w") as f:
                f.write("observation_date,TEST\n")

        with mock.patch("download_data.urllib.request.urlretrieve",
                        side_effect=spy_urlretrieve):
            download_data.download_series("PCEPI", str(tmp_path))

        assert "id=PCEPI" in captured_url["url"]

    def test_download_failure_raises_runtime_error(self, tmp_path):
        """A network error is wrapped in RuntimeError."""
        with mock.patch("download_data.urllib.request.urlretrieve",
                        side_effect=OSError("network down")):
            with pytest.raises(RuntimeError, match="Failed to download"):
                download_data.download_series("PCE", str(tmp_path))


class TestMain:
    """Tests for main()."""

    def test_creates_data_directory(self, tmp_path, monkeypatch):
        """main() creates the data/ directory if it doesn't exist."""
        monkeypatch.setattr(download_data, "SERIES", ["PCE"])

        # Point script_dir to tmp_path
        monkeypatch.setattr(os.path, "abspath",
                            lambda p: str(tmp_path / "download_data.py"))

        def fake_urlretrieve(url, filepath):
            with open(filepath, "w") as f:
                f.write("observation_date,PCE\n2024-01-01,100\n")

        with mock.patch("download_data.urllib.request.urlretrieve",
                        side_effect=fake_urlretrieve):
            download_data.main()

        assert os.path.isdir(tmp_path / "data")

    def test_main_continues_on_partial_failure(self, tmp_path, monkeypatch):
        """main() downloads remaining series even if one fails, then exits 1."""
        monkeypatch.setattr(download_data, "SERIES", ["GOOD", "BAD", "GOOD2"])

        monkeypatch.setattr(os.path, "abspath",
                            lambda p: str(tmp_path / "download_data.py"))

        call_count = {"n": 0}

        def selective_urlretrieve(url, filepath):
            call_count["n"] += 1
            if "id=BAD" in url:
                raise OSError("simulated failure")
            with open(filepath, "w") as f:
                f.write("observation_date,X\n2024-01-01,1\n")

        with mock.patch("download_data.urllib.request.urlretrieve",
                        side_effect=selective_urlretrieve):
            with pytest.raises(SystemExit) as exc_info:
                download_data.main()

        assert exc_info.value.code == 1
        # All 3 series were attempted
        assert call_count["n"] == 3

    def test_main_exits_cleanly_on_success(self, tmp_path, monkeypatch):
        """main() does not call sys.exit when all downloads succeed."""
        monkeypatch.setattr(download_data, "SERIES", ["PCE"])
        monkeypatch.setattr(os.path, "abspath",
                            lambda p: str(tmp_path / "download_data.py"))

        def fake_urlretrieve(url, filepath):
            with open(filepath, "w") as f:
                f.write("observation_date,PCE\n2024-01-01,100\n")

        with mock.patch("download_data.urllib.request.urlretrieve",
                        side_effect=fake_urlretrieve):
            # Should NOT raise SystemExit
            download_data.main()


class TestConstants:
    """Sanity checks on module-level constants."""

    def test_series_list_has_seven_entries(self):
        assert len(download_data.SERIES) == 7

    def test_url_template_contains_placeholder(self):
        assert "{series_id}" in download_data.FRED_CSV_URL

    def test_all_expected_series_present(self):
        expected = {"PCE", "PCEPI", "PCEPILFE", "PCEC96", "PCEDG", "PCEND", "PCES"}
        assert set(download_data.SERIES) == expected
