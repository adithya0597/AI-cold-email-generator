"""Tests for MyVisaJobs-equivalent data extractor (Story 7-3).

Covers: company details extraction, job title aggregation, location aggregation,
fetch_myvisajobs integration.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.research.myvisajobs_client import (
    CompanyDetails,
    MyVisaJobsClient,
    extract_company_details,
    get_top_job_titles,
    get_worksite_locations,
)


# ---------------------------------------------------------------------------
# extract_company_details tests
# ---------------------------------------------------------------------------


class TestExtractCompanyDetails:
    def test_extracts_wage_and_counts(self):
        """Extracts average wage and petition count for a company."""
        records = [
            {"EMPLOYER_NAME": "Google LLC", "CASE_STATUS": "Certified", "WAGE_RATE_OF_PAY_FROM": "150000", "WAGE_UNIT_OF_PAY": "Year", "SOC_TITLE": "Software Developer", "WORKSITE_STATE": "CA"},
            {"EMPLOYER_NAME": "Google Inc", "CASE_STATUS": "Certified", "WAGE_RATE_OF_PAY_FROM": "160000", "WAGE_UNIT_OF_PAY": "Year", "SOC_TITLE": "Data Scientist", "WORKSITE_STATE": "NY"},
        ]

        result = extract_company_details(records, "google")

        assert result.avg_wage == pytest.approx(155000, abs=1)
        assert result.total_records == 2

    def test_hourly_conversion(self):
        """Hourly wages are converted to annual."""
        records = [
            {"EMPLOYER_NAME": "PayCo LLC", "CASE_STATUS": "Certified", "WAGE_RATE_OF_PAY_FROM": "75", "WAGE_UNIT_OF_PAY": "Hour", "SOC_TITLE": "Engineer", "WORKSITE_STATE": "TX"},
        ]

        result = extract_company_details(records, "payco")

        assert result.avg_wage == pytest.approx(75 * 2080, abs=1)

    def test_empty_records(self):
        """Empty records return zeroed CompanyDetails."""
        result = extract_company_details([], "anything")

        assert result.total_records == 0
        assert result.avg_wage is None
        assert result.top_job_titles == []
        assert result.worksite_locations == {}


# ---------------------------------------------------------------------------
# get_top_job_titles tests
# ---------------------------------------------------------------------------


class TestGetTopJobTitles:
    def test_returns_top_5(self):
        """Returns top 5 job titles by count."""
        records = [
            {"SOC_TITLE": "Software Developer"} for _ in range(10)
        ] + [
            {"SOC_TITLE": "Data Scientist"} for _ in range(8)
        ] + [
            {"SOC_TITLE": "Product Manager"} for _ in range(6)
        ] + [
            {"SOC_TITLE": "Designer"} for _ in range(4)
        ] + [
            {"SOC_TITLE": "Analyst"} for _ in range(2)
        ] + [
            {"SOC_TITLE": "Intern"} for _ in range(1)
        ]

        result = get_top_job_titles(records, limit=5)

        assert len(result) == 5
        assert result[0] == ("Software Developer", 10)
        assert result[1] == ("Data Scientist", 8)
        assert result[4] == ("Analyst", 2)

    def test_empty_records(self):
        """Empty records return empty list."""
        result = get_top_job_titles([], limit=5)
        assert result == []

    def test_fewer_than_limit(self):
        """Returns all titles if fewer than limit."""
        records = [
            {"SOC_TITLE": "Engineer"},
            {"SOC_TITLE": "Manager"},
        ]

        result = get_top_job_titles(records, limit=5)

        assert len(result) == 2


# ---------------------------------------------------------------------------
# get_worksite_locations tests
# ---------------------------------------------------------------------------


class TestGetWorksiteLocations:
    def test_multiple_states(self):
        """Counts petitions per state."""
        records = [
            {"WORKSITE_STATE": "CA"},
            {"WORKSITE_STATE": "CA"},
            {"WORKSITE_STATE": "NY"},
            {"WORKSITE_STATE": "TX"},
        ]

        result = get_worksite_locations(records)

        assert result["CA"] == 2
        assert result["NY"] == 1
        assert result["TX"] == 1

    def test_single_state(self):
        """Single state returns single entry."""
        records = [{"WORKSITE_STATE": "WA"}, {"WORKSITE_STATE": "WA"}]

        result = get_worksite_locations(records)

        assert result == {"WA": 2}

    def test_empty_records(self):
        """Empty records return empty dict."""
        result = get_worksite_locations([])
        assert result == {}


# ---------------------------------------------------------------------------
# fetch_myvisajobs integration tests
# ---------------------------------------------------------------------------


class TestFetchMyvisajobsIntegration:
    @pytest.mark.asyncio
    async def test_returns_populated_source_data(self):
        """Replaced fetch_myvisajobs returns SourceData with attribution."""
        from app.services.research.h1b_service import SourceData, fetch_myvisajobs

        mock_details = CompanyDetails(
            avg_wage=145000.0,
            total_records=50,
            top_job_titles=[("Software Developer", 30), ("Data Scientist", 20)],
            worksite_locations={"CA": 35, "NY": 15},
        )

        with patch("app.services.research.myvisajobs_client.MyVisaJobsClient") as MockClient:
            instance = AsyncMock()
            instance.fetch_company_details = AsyncMock(return_value=mock_details)
            MockClient.return_value = instance

            result = await fetch_myvisajobs("Google")

        assert result is not None
        assert isinstance(result, SourceData)
        assert result.source == "myvisajobs"
        assert result.avg_wage == 145000.0
        assert result.wage_source == "dol_lca"
        assert "attribution" in result.raw_data
        assert "top_job_titles" in result.raw_data

    @pytest.mark.asyncio
    async def test_returns_none_on_failure(self):
        """fetch_myvisajobs returns None when data fetch fails."""
        from app.services.research.h1b_service import fetch_myvisajobs

        with patch("app.services.research.myvisajobs_client.MyVisaJobsClient") as MockClient:
            instance = AsyncMock()
            instance.fetch_company_details = AsyncMock(side_effect=Exception("Network error"))
            MockClient.return_value = instance

            result = await fetch_myvisajobs("FailCorp")

        assert result is None
