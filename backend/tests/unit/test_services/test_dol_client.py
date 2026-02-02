"""Tests for DOL disclosure data client (Story 7-2).

Covers: CSV parsing, company aggregation, trend calculation, download with caching.
"""

import csv
import io
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.research.dol_client import (
    DOLDisclosureClient,
    aggregate_by_company,
    calculate_trend,
    parse_disclosure_csv,
)


async def _async_iter_bytes(data: bytes):
    """Helper to create an async iterator of byte chunks."""
    yield data


# ---------------------------------------------------------------------------
# parse_disclosure_csv tests
# ---------------------------------------------------------------------------


class TestParseDisclosureCsv:
    def test_valid_csv(self, tmp_path):
        """Parses a well-formed DOL CSV file."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "EMPLOYER_NAME,CASE_STATUS,WAGE_RATE_OF_PAY_FROM,WAGE_UNIT_OF_PAY,SOC_TITLE,WORKSITE_STATE\n"
            "Google LLC,Certified,150000,Year,Software Developer,CA\n"
            "Meta Inc,Denied,75.50,Hour,Data Scientist,NY\n"
        )

        rows = parse_disclosure_csv(csv_file)

        assert len(rows) == 2
        assert rows[0]["EMPLOYER_NAME"] == "Google LLC"
        assert rows[0]["CASE_STATUS"] == "Certified"
        assert rows[0]["WAGE_RATE_OF_PAY_FROM"] == "150000"
        assert rows[1]["EMPLOYER_NAME"] == "Meta Inc"
        assert rows[1]["WAGE_UNIT_OF_PAY"] == "Hour"

    def test_malformed_rows_skipped(self, tmp_path):
        """Rows missing required columns are skipped."""
        csv_file = tmp_path / "bad.csv"
        csv_file.write_text(
            "EMPLOYER_NAME,CASE_STATUS,WAGE_RATE_OF_PAY_FROM,WAGE_UNIT_OF_PAY,SOC_TITLE,WORKSITE_STATE\n"
            "Good Corp,Certified,100000,Year,Engineer,TX\n"
            ",Certified,100000,Year,Engineer,TX\n"
        )

        rows = parse_disclosure_csv(csv_file)

        assert len(rows) == 1
        assert rows[0]["EMPLOYER_NAME"] == "Good Corp"

    def test_empty_file(self, tmp_path):
        """Empty CSV returns empty list."""
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text(
            "EMPLOYER_NAME,CASE_STATUS,WAGE_RATE_OF_PAY_FROM,WAGE_UNIT_OF_PAY,SOC_TITLE,WORKSITE_STATE\n"
        )

        rows = parse_disclosure_csv(csv_file)

        assert rows == []


# ---------------------------------------------------------------------------
# aggregate_by_company tests
# ---------------------------------------------------------------------------


class TestAggregateByCompany:
    def test_multiple_companies(self):
        """Groups records by normalized company name."""
        records = [
            {"EMPLOYER_NAME": "Google LLC", "CASE_STATUS": "Certified", "WAGE_RATE_OF_PAY_FROM": "150000", "WAGE_UNIT_OF_PAY": "Year"},
            {"EMPLOYER_NAME": "Google Inc", "CASE_STATUS": "Certified", "WAGE_RATE_OF_PAY_FROM": "160000", "WAGE_UNIT_OF_PAY": "Year"},
            {"EMPLOYER_NAME": "Meta Inc", "CASE_STATUS": "Denied", "WAGE_RATE_OF_PAY_FROM": "75", "WAGE_UNIT_OF_PAY": "Hour"},
        ]

        result = aggregate_by_company(records)

        assert "google" in result
        assert "meta" in result
        assert result["google"].total_petitions == 2
        assert result["google"].approved_count == 2
        assert result["meta"].total_petitions == 1
        assert result["meta"].denied_count == 1

    def test_single_company(self):
        """Single company aggregation."""
        records = [
            {"EMPLOYER_NAME": "Acme Corp", "CASE_STATUS": "Certified", "WAGE_RATE_OF_PAY_FROM": "120000", "WAGE_UNIT_OF_PAY": "Year"},
            {"EMPLOYER_NAME": "Acme Corp", "CASE_STATUS": "Denied", "WAGE_RATE_OF_PAY_FROM": "110000", "WAGE_UNIT_OF_PAY": "Year"},
            {"EMPLOYER_NAME": "Acme Corp", "CASE_STATUS": "Withdrawn", "WAGE_RATE_OF_PAY_FROM": "100000", "WAGE_UNIT_OF_PAY": "Year"},
        ]

        result = aggregate_by_company(records)

        assert "acme" in result
        stats = result["acme"]
        assert stats.total_petitions == 3
        assert stats.approved_count == 1
        assert stats.denied_count == 1
        assert stats.withdrawn_count == 1
        assert stats.approval_rate == pytest.approx(1 / 3, abs=0.01)

    def test_normalization_dedup(self):
        """Different legal suffixes merge into one entry."""
        records = [
            {"EMPLOYER_NAME": "Amazon.com Inc.", "CASE_STATUS": "Certified", "WAGE_RATE_OF_PAY_FROM": "180000", "WAGE_UNIT_OF_PAY": "Year"},
            {"EMPLOYER_NAME": "Amazon.com LLC", "CASE_STATUS": "Certified", "WAGE_RATE_OF_PAY_FROM": "190000", "WAGE_UNIT_OF_PAY": "Year"},
        ]

        result = aggregate_by_company(records)

        assert "amazon.com" in result
        assert result["amazon.com"].total_petitions == 2

    def test_hourly_to_annual_conversion(self):
        """Hourly wages are converted to annual (×2080)."""
        records = [
            {"EMPLOYER_NAME": "PayCo", "CASE_STATUS": "Certified", "WAGE_RATE_OF_PAY_FROM": "50", "WAGE_UNIT_OF_PAY": "Hour"},
        ]

        result = aggregate_by_company(records)

        assert result["payco"].avg_wage == pytest.approx(50 * 2080, abs=1)

    def test_comma_formatted_wages(self):
        """Handles wages with comma formatting like '150,000'."""
        records = [
            {"EMPLOYER_NAME": "RichCo", "CASE_STATUS": "Certified", "WAGE_RATE_OF_PAY_FROM": "150,000", "WAGE_UNIT_OF_PAY": "Year"},
        ]

        result = aggregate_by_company(records)

        assert result["richco"].avg_wage == pytest.approx(150000, abs=1)


# ---------------------------------------------------------------------------
# calculate_trend tests
# ---------------------------------------------------------------------------


class TestCalculateTrend:
    def test_increasing(self):
        """More than 10% increase → 'increasing'."""
        assert calculate_trend(current=120, previous=100) == "increasing"

    def test_decreasing(self):
        """More than 10% decrease → 'decreasing'."""
        assert calculate_trend(current=80, previous=100) == "decreasing"

    def test_stable(self):
        """Within ±10% → 'stable'."""
        assert calculate_trend(current=105, previous=100) == "stable"
        assert calculate_trend(current=95, previous=100) == "stable"

    def test_zero_previous(self):
        """Zero previous with current > 0 → 'increasing'."""
        assert calculate_trend(current=10, previous=0) == "increasing"

    def test_both_zero(self):
        """Both zero → 'stable'."""
        assert calculate_trend(current=0, previous=0) == "stable"


# ---------------------------------------------------------------------------
# DOLDisclosureClient.download_disclosure_file tests
# ---------------------------------------------------------------------------


def _make_stream_response(status_code: int, data: bytes = b""):
    """Create a mock response for httpx streaming."""
    resp = AsyncMock()
    resp.status_code = status_code
    resp.request = MagicMock()

    async def _aiter():
        yield data

    resp.aiter_bytes = _aiter
    return resp


def _make_httpx_client(stream_side_effects):
    """Create a mock httpx.AsyncClient with stream responses."""
    call_idx = {"i": 0}

    mock_client_instance = AsyncMock()

    def _stream(*args, **kwargs):
        idx = call_idx["i"]
        call_idx["i"] += 1
        resp = stream_side_effects[idx]
        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=resp)
        cm.__aexit__ = AsyncMock(return_value=False)
        return cm

    mock_client_instance.stream = _stream

    mock_client_cls = MagicMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_client_instance)
    cm.__aexit__ = AsyncMock(return_value=False)
    mock_client_cls.return_value = cm
    return mock_client_cls


class TestDownloadDisclosureFile:
    @pytest.mark.asyncio
    async def test_successful_download(self, tmp_path):
        """Downloads and caches CSV file."""
        client = DOLDisclosureClient(cache_dir=tmp_path)
        csv_data = b"EMPLOYER_NAME,CASE_STATUS\nTest,Certified\n"

        mock_cls = _make_httpx_client([_make_stream_response(200, csv_data)])

        with patch("app.services.research.dol_client.httpx.AsyncClient", mock_cls):
            path = await client.download_disclosure_file(2024)

        assert path.exists()
        assert "2024" in path.name
        assert path.read_bytes() == csv_data

    @pytest.mark.asyncio
    async def test_cache_hit_skips_download(self, tmp_path):
        """Cached file < 24h old is reused without download."""
        client = DOLDisclosureClient(cache_dir=tmp_path)

        # Pre-create a cached file
        cached = tmp_path / "h1b_disclosure_2024.csv"
        cached.write_text("EMPLOYER_NAME,CASE_STATUS\nCached,Certified\n")

        path = await client.download_disclosure_file(2024)

        assert path == cached  # Returned cached path, no download

    @pytest.mark.asyncio
    async def test_retry_on_failure(self, tmp_path):
        """Retries on transient failure with backoff."""
        client = DOLDisclosureClient(cache_dir=tmp_path)
        csv_data = b"EMPLOYER_NAME,CASE_STATUS\nTest,Certified\n"

        mock_cls = _make_httpx_client([
            _make_stream_response(500),
            _make_stream_response(200, csv_data),
        ])

        with patch("app.services.research.dol_client.httpx.AsyncClient", mock_cls), \
             patch("asyncio.sleep", new_callable=AsyncMock):
            path = await client.download_disclosure_file(2024)

        assert path.exists()


# ---------------------------------------------------------------------------
# fetch_h1bgrader integration test
# ---------------------------------------------------------------------------


class TestFetchH1bgraderIntegration:
    @pytest.mark.asyncio
    async def test_returns_populated_source_data(self):
        """Replaced fetch_h1bgrader returns SourceData with attribution."""
        from app.services.research.h1b_service import SourceData, fetch_h1bgrader

        mock_stats = MagicMock()
        mock_stats.total_petitions = 100
        mock_stats.approval_rate = 0.85
        mock_stats.avg_wage = 140000.0
        mock_stats.trend = "increasing"

        with patch("app.services.research.dol_client.DOLDisclosureClient") as MockClient:
            instance = AsyncMock()
            instance.fetch_company_stats = AsyncMock(return_value=mock_stats)
            MockClient.return_value = instance

            result = await fetch_h1bgrader("Google")

        assert result is not None
        assert isinstance(result, SourceData)
        assert result.source == "h1bgrader"
        assert result.total_petitions == 100
        assert result.approval_rate == 0.85
        assert result.avg_wage == 140000.0
        assert "attribution" in result.raw_data

    @pytest.mark.asyncio
    async def test_returns_none_on_failure(self):
        """fetch_h1bgrader returns None when DOL fetch fails."""
        from app.services.research.h1b_service import fetch_h1bgrader

        with patch("app.services.research.dol_client.DOLDisclosureClient") as MockClient:
            instance = AsyncMock()
            instance.fetch_company_stats = AsyncMock(side_effect=Exception("Network error"))
            MockClient.return_value = instance

            result = await fetch_h1bgrader("FailCorp")

        assert result is None
