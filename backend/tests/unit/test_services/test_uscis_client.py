"""Tests for USCIS public data client (Story 7-4).

Covers: employer data parsing, employer stats extraction, download caching,
fetch_uscis integration.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.research.uscis_client import (
    EmployerStats,
    USCISClient,
    get_employer_stats,
    parse_employer_data,
)


# ---------------------------------------------------------------------------
# parse_employer_data tests
# ---------------------------------------------------------------------------


class TestParseEmployerData:
    def test_valid_csv(self, tmp_path):
        """Parses a well-formed USCIS employer data CSV."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "Employer,Initial Approvals,Initial Denials,Continuing Approvals,Continuing Denials,Fiscal Year\n"
            "GOOGLE LLC,500,10,300,5,2024\n"
            "META PLATFORMS INC,200,20,150,10,2024\n"
        )

        rows = parse_employer_data(csv_file)

        assert len(rows) == 2
        assert rows[0]["Employer"] == "GOOGLE LLC"
        assert rows[0]["Initial Approvals"] == "500"

    def test_empty_file(self, tmp_path):
        """Empty CSV returns empty list."""
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text(
            "Employer,Initial Approvals,Initial Denials,Continuing Approvals,Continuing Denials,Fiscal Year\n"
        )

        rows = parse_employer_data(csv_file)

        assert rows == []


# ---------------------------------------------------------------------------
# get_employer_stats tests
# ---------------------------------------------------------------------------


class TestGetEmployerStats:
    def test_found_employer(self):
        """Extracts stats for a matching employer."""
        records = [
            {"Employer": "GOOGLE LLC", "Initial Approvals": "500", "Initial Denials": "10", "Continuing Approvals": "300", "Continuing Denials": "5", "Fiscal Year": "2024"},
        ]

        result = get_employer_stats(records, "Google")

        assert result is not None
        assert result.initial_approvals == 500
        assert result.initial_denials == 10
        assert result.continuing_approvals == 300
        assert result.continuing_denials == 5
        assert result.total_petitions == 815
        assert result.approval_rate == pytest.approx(800 / 815, abs=0.01)

    def test_not_found(self):
        """Returns None for unknown employer."""
        records = [
            {"Employer": "GOOGLE LLC", "Initial Approvals": "500", "Initial Denials": "10", "Continuing Approvals": "300", "Continuing Denials": "5", "Fiscal Year": "2024"},
        ]

        result = get_employer_stats(records, "NonexistentCorp")

        assert result is None

    def test_multiple_entries_aggregated(self):
        """Multiple entries for same employer are summed."""
        records = [
            {"Employer": "AMAZON.COM INC", "Initial Approvals": "200", "Initial Denials": "5", "Continuing Approvals": "100", "Continuing Denials": "2", "Fiscal Year": "2023"},
            {"Employer": "AMAZON.COM LLC", "Initial Approvals": "300", "Initial Denials": "10", "Continuing Approvals": "150", "Continuing Denials": "3", "Fiscal Year": "2024"},
        ]

        result = get_employer_stats(records, "Amazon.com")

        assert result is not None
        assert result.initial_approvals == 500
        assert result.initial_denials == 15
        assert result.total_petitions == 770


# ---------------------------------------------------------------------------
# USCISClient.download_employer_data tests
# ---------------------------------------------------------------------------


class TestDownloadEmployerData:
    @pytest.mark.asyncio
    async def test_cache_hit(self, tmp_path):
        """Cached file is reused without download."""
        client = USCISClient(cache_dir=tmp_path)
        cached = tmp_path / "uscis_h1b_employer_2024.csv"
        cached.write_text("Employer,Initial Approvals\nTest,100\n")

        path = await client.download_employer_data(2024)

        assert path == cached


# ---------------------------------------------------------------------------
# fetch_uscis integration tests
# ---------------------------------------------------------------------------


class TestFetchUscisIntegration:
    @pytest.mark.asyncio
    async def test_returns_populated_source_data(self):
        """Replaced fetch_uscis returns SourceData with attribution."""
        from app.services.research.h1b_service import SourceData, fetch_uscis

        mock_stats = EmployerStats(
            initial_approvals=500,
            initial_denials=10,
            continuing_approvals=300,
            continuing_denials=5,
        )

        with patch("app.services.research.uscis_client.USCISClient") as MockClient:
            instance = AsyncMock()
            instance.fetch_employer_stats = AsyncMock(return_value=mock_stats)
            MockClient.return_value = instance

            result = await fetch_uscis("Google")

        assert result is not None
        assert isinstance(result, SourceData)
        assert result.source == "uscis"
        assert result.total_petitions == 815
        assert result.approval_rate == pytest.approx(800 / 815, abs=0.01)
        assert "attribution" in result.raw_data

    @pytest.mark.asyncio
    async def test_returns_none_on_failure(self):
        """fetch_uscis returns None when data fetch fails."""
        from app.services.research.h1b_service import fetch_uscis

        with patch("app.services.research.uscis_client.USCISClient") as MockClient:
            instance = AsyncMock()
            instance.fetch_employer_stats = AsyncMock(side_effect=Exception("Network error"))
            MockClient.return_value = instance

            result = await fetch_uscis("FailCorp")

        assert result is None
