"""Tests for H1B service layer (Story 7-1).

Covers: company name normalization, source aggregation, upsert, pipeline.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.research.h1b_service import (
    SourceData,
    SponsorRecord,
    aggregate_sources,
    normalize_company_name,
    upsert_sponsor,
)


# ---------------------------------------------------------------------------
# normalize_company_name tests
# ---------------------------------------------------------------------------


class TestNormalizeCompanyName:
    def test_strips_inc(self):
        assert normalize_company_name("Acme, Inc.") == "acme"

    def test_strips_inc_no_period(self):
        assert normalize_company_name("Acme Inc") == "acme"

    def test_strips_llc(self):
        assert normalize_company_name("TechCo LLC") == "techco"

    def test_strips_corp(self):
        assert normalize_company_name("Evil Corp") == "evil"

    def test_strips_corporation(self):
        assert normalize_company_name("Global Corporation") == "global"

    def test_strips_ltd(self):
        assert normalize_company_name("British Ltd.") == "british"

    def test_strips_company(self):
        assert normalize_company_name("Ford Motor Company") == "ford motor"

    def test_strips_lp(self):
        assert normalize_company_name("Venture L.P.") == "venture"

    def test_collapses_whitespace(self):
        assert normalize_company_name("  Google  LLC ") == "google"

    def test_lowercases(self):
        assert normalize_company_name("MICROSOFT") == "microsoft"

    def test_multiple_suffixes(self):
        assert normalize_company_name("Acme Corp, Inc.") == "acme"

    def test_no_suffix(self):
        assert normalize_company_name("Amazon") == "amazon"

    def test_empty_string(self):
        assert normalize_company_name("") == ""

    def test_name_with_numbers(self):
        assert normalize_company_name("3M Company") == "3m"


# ---------------------------------------------------------------------------
# aggregate_sources tests
# ---------------------------------------------------------------------------


class TestAggregateSources:
    def test_merges_all_three_sources(self):
        h1b = SourceData(source="h1bgrader", company_name="Google Inc", total_petitions=150, approval_rate=0.92)
        mvj = SourceData(source="myvisajobs", company_name="Google", avg_wage=125000, wage_source="myvisajobs", domain="google.com")
        uscis = SourceData(source="uscis", company_name="Google LLC", total_petitions=200, approval_rate=0.88, avg_wage=130000, wage_source="uscis_lca")

        result = aggregate_sources(h1b, mvj, uscis)

        assert result.company_name == "Google Inc"
        assert result.company_name_normalized == "google"
        assert result.total_petitions == 200  # max of sources
        assert result.approval_rate == 0.88  # USCIS preferred
        assert result.avg_wage == 130000  # USCIS preferred
        assert result.wage_source == "uscis_lca"
        assert result.domain == "google.com"  # from MyVisaJobs

    def test_partial_sources_h1bgrader_only(self):
        h1b = SourceData(source="h1bgrader", company_name="Acme Corp", total_petitions=50, approval_rate=0.75)

        result = aggregate_sources(h1b, None, None)

        assert result.company_name == "Acme Corp"
        assert result.total_petitions == 50
        assert result.approval_rate == 0.75
        assert result.avg_wage is None
        assert result.domain is None

    def test_partial_sources_myvisajobs_only(self):
        mvj = SourceData(source="myvisajobs", company_name="Startup", avg_wage=95000, wage_source="myvisajobs")

        result = aggregate_sources(None, mvj, None)

        assert result.company_name == "Startup"
        assert result.total_petitions == 0
        assert result.avg_wage == 95000

    def test_all_none_sources(self):
        result = aggregate_sources(None, None, None)

        assert result.company_name == "Unknown"
        assert result.company_name_normalized == "unknown"
        assert result.total_petitions == 0

    def test_uscis_overrides_h1bgrader_approval_rate(self):
        h1b = SourceData(source="h1bgrader", company_name="X", approval_rate=0.95)
        uscis = SourceData(source="uscis", company_name="X", approval_rate=0.80)

        result = aggregate_sources(h1b, None, uscis)

        assert result.approval_rate == 0.80  # USCIS wins

    def test_h1bgrader_used_when_no_uscis(self):
        h1b = SourceData(source="h1bgrader", company_name="Y", approval_rate=0.90)

        result = aggregate_sources(h1b, None, None)

        assert result.approval_rate == 0.90


# ---------------------------------------------------------------------------
# upsert_sponsor tests
# ---------------------------------------------------------------------------


class TestUpsertSponsor:
    @pytest.mark.asyncio
    async def test_upsert_executes_sql(self):
        mock_sess = AsyncMock()
        sponsor = SponsorRecord(
            company_name="Test Corp",
            company_name_normalized="test",
            total_petitions=100,
            approval_rate=0.85,
        )

        await upsert_sponsor(mock_sess, sponsor)

        mock_sess.execute.assert_called_once()
        mock_sess.commit.assert_called_once()
        # Verify parameterized query
        call_args = mock_sess.execute.call_args
        params = call_args[0][1]
        assert params["company_name"] == "Test Corp"
        assert params["company_name_normalized"] == "test"
        assert params["total_petitions"] == 100
        assert params["approval_rate"] == 0.85
