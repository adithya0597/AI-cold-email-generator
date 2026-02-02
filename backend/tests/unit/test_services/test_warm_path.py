"""Tests for Warm Path Finder Service (Story 9-2).

Covers: analyze(), path types, strength scoring, suggested actions,
graceful degradation, to_dict(), agent integration.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.network.warm_path import WarmPath, WarmPathService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def service():
    return WarmPathService()


@pytest.fixture
def mock_llm_response():
    """Standard LLM response for warm path analysis."""
    return {
        "paths": [
            {
                "contact_name": "Alice Smith",
                "path_type": "1st_degree",
                "strength": "strong",
                "relationship_context": "Worked together at TechCo for 3 years",
                "suggested_action": "Reach out directly to Alice",
                "mutual_connections": ["Bob Jones", "Carol Lee"],
            },
            {
                "contact_name": "Dave Wilson",
                "path_type": "alumni",
                "strength": "medium",
                "relationship_context": "Same university, graduated 2020",
                "suggested_action": "Mention shared alma mater",
                "mutual_connections": [],
            },
        ]
    }


@pytest.fixture
def connection_data():
    return {
        "contacts": [
            {"name": "Alice Smith", "company": "Acme Corp"},
            {"name": "Bob Jones", "company": "Other Co"},
        ]
    }


# ---------------------------------------------------------------------------
# AC1: Warm path analysis
# ---------------------------------------------------------------------------


class TestAnalyze:
    @pytest.mark.asyncio
    async def test_returns_warm_path_list(
        self, service, mock_llm_response, connection_data
    ):
        """analyze() returns list of WarmPath objects."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            result = await service.analyze(["Acme Corp"], connection_data)

        assert len(result) > 0
        assert all(isinstance(p, WarmPath) for p in result)

    @pytest.mark.asyncio
    async def test_empty_companies_returns_empty(self, service):
        """analyze() returns empty list for no target companies."""
        result = await service.analyze([], {})
        assert result == []

    @pytest.mark.asyncio
    async def test_multiple_companies_parallel(
        self, service, mock_llm_response, connection_data
    ):
        """analyze() handles multiple companies via asyncio.gather."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            result = await service.analyze(
                ["Acme Corp", "Globex Inc"], connection_data
            )

        # Should have paths for both companies
        assert len(result) >= 2
        companies = {p.company for p in result}
        assert "Acme Corp" in companies
        assert "Globex Inc" in companies


# ---------------------------------------------------------------------------
# AC1: Path types
# ---------------------------------------------------------------------------


class TestPathTypes:
    @pytest.mark.asyncio
    async def test_1st_degree_path(self, service, connection_data):
        """1st_degree path type is correctly set."""
        response = {
            "paths": [
                {
                    "contact_name": "Alice",
                    "path_type": "1st_degree",
                    "relationship_context": "Direct connection",
                    "mutual_connections": ["Bob"],
                }
            ]
        }
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=response)

            result = await service.analyze(["Acme"], connection_data)

        assert result[0].path_type == "1st_degree"

    @pytest.mark.asyncio
    async def test_2nd_degree_path(self, service, connection_data):
        """2nd_degree path type is correctly set."""
        response = {
            "paths": [
                {
                    "contact_name": "Charlie",
                    "path_type": "2nd_degree",
                    "relationship_context": "Friend of friend",
                    "mutual_connections": [],
                }
            ]
        }
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=response)

            result = await service.analyze(["Acme"], connection_data)

        assert result[0].path_type == "2nd_degree"

    @pytest.mark.asyncio
    async def test_alumni_path(self, service, connection_data):
        """alumni path type is correctly set."""
        response = {
            "paths": [
                {
                    "contact_name": "Eve",
                    "path_type": "alumni",
                    "relationship_context": "MIT alumni",
                    "mutual_connections": [],
                }
            ]
        }
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=response)

            result = await service.analyze(["Acme"], connection_data)

        assert result[0].path_type == "alumni"


# ---------------------------------------------------------------------------
# AC2: Strength scoring
# ---------------------------------------------------------------------------


class TestStrengthScoring:
    def test_strong_score(self, service):
        """1st degree with multiple mutuals and depth → strong."""
        path_data = {
            "path_type": "1st_degree",
            "mutual_connections": ["A", "B", "C"],
            "relationship_context": "Worked together closely",
        }
        assert service._score_path_strength(path_data) == "strong"

    def test_medium_score(self, service):
        """Alumni with one mutual → medium."""
        path_data = {
            "path_type": "alumni",
            "mutual_connections": ["A"],
            "relationship_context": "Same school",
        }
        assert service._score_path_strength(path_data) == "medium"

    def test_weak_score(self, service):
        """2nd degree with no mutuals → weak."""
        path_data = {
            "path_type": "2nd_degree",
            "mutual_connections": [],
            "relationship_context": "Distant connection",
        }
        assert service._score_path_strength(path_data) == "weak"


# ---------------------------------------------------------------------------
# AC3: Suggested actions
# ---------------------------------------------------------------------------


class TestSuggestedActions:
    def test_1st_degree_action(self, service):
        """1st degree paths get direct outreach suggestion."""
        path_data = {"contact_name": "Alice", "path_type": "1st_degree"}
        action = service._generate_suggested_action(path_data, "Acme")
        assert "directly" in action.lower() or "reach out" in action.lower()

    def test_alumni_action(self, service):
        """Alumni paths get school mention suggestion."""
        path_data = {"contact_name": "Eve", "path_type": "alumni"}
        action = service._generate_suggested_action(path_data, "Acme")
        assert "alma mater" in action.lower()

    def test_2nd_degree_action(self, service):
        """2nd degree paths get intro request suggestion."""
        path_data = {"contact_name": "Charlie", "path_type": "2nd_degree"}
        action = service._generate_suggested_action(path_data, "Acme")
        assert "intro" in action.lower() or "mutual" in action.lower()

    @pytest.mark.asyncio
    async def test_suggested_actions_populated(
        self, service, mock_llm_response, connection_data
    ):
        """Warm paths have suggested_action set."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value=mock_llm_response)

            result = await service.analyze(["Acme"], connection_data)

        for path in result:
            assert path.suggested_action != ""


# ---------------------------------------------------------------------------
# AC5: Graceful degradation
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    @pytest.mark.asyncio
    async def test_llm_failure_returns_partial(self, service, connection_data):
        """When LLM fails, returns partial results."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(
                side_effect=Exception("LLM down")
            )

            result = await service.analyze(["Acme"], connection_data)

        assert len(result) > 0
        assert result[0].data_quality == "partial"

    @pytest.mark.asyncio
    async def test_empty_llm_response(self, service, connection_data):
        """When LLM returns empty, returns partial results."""
        with patch("app.core.llm_clients.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_json = AsyncMock(return_value={})

            result = await service.analyze(["Acme"], connection_data)

        assert len(result) > 0
        assert result[0].data_quality == "partial"


# ---------------------------------------------------------------------------
# to_dict() serialization
# ---------------------------------------------------------------------------


class TestToDict:
    def test_to_dict_includes_all_fields(self):
        """to_dict() includes ALL dataclass fields."""
        path = WarmPath(
            contact_name="Alice",
            company="Acme",
            path_type="1st_degree",
            strength="strong",
            relationship_context="Colleagues",
            suggested_action="Reach out",
            mutual_connections=["Bob"],
            data_quality="complete",
        )
        d = path.to_dict()
        assert d["contact_name"] == "Alice"
        assert d["company"] == "Acme"
        assert d["path_type"] == "1st_degree"
        assert d["strength"] == "strong"
        assert d["relationship_context"] == "Colleagues"
        assert d["suggested_action"] == "Reach out"
        assert d["mutual_connections"] == ["Bob"]
        assert d["data_quality"] == "complete"
        # Ensure all 8 fields are present
        assert len(d) == 8


# ---------------------------------------------------------------------------
# AC4: Agent integration
# ---------------------------------------------------------------------------


class TestAgentIntegration:
    @pytest.mark.asyncio
    async def test_agent_calls_service(self):
        """NetworkAgent._analyze_warm_paths() delegates to WarmPathService."""
        from app.agents.core.network_agent import NetworkAgent

        agent = NetworkAgent()
        mock_paths = [
            WarmPath(
                contact_name="Alice",
                company="Acme",
                path_type="1st_degree",
                strength="strong",
                data_quality="complete",
            )
        ]

        with patch(
            "app.services.network.warm_path.WarmPathService"
        ) as MockService:
            instance = MockService.return_value
            instance.analyze = AsyncMock(return_value=mock_paths)

            result = await agent._analyze_warm_paths(
                ["Acme"], {"contacts": []}
            )

        assert len(result) == 1
        assert result[0]["contact_name"] == "Alice"
        instance.analyze.assert_called_once()
