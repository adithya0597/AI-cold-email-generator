"""Tests for the Cover Letter Agent (Story 5-5).

Covers: LLM generation, content structure, word count,
document storage with versioning, error handling, and AgentOutput structure.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _mock_session_cm():
    """Create a mock async session context manager."""
    mock_sess = AsyncMock()
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_sess)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    return mock_cm, mock_sess


def _sample_profile():
    return {
        "headline": "Senior Software Engineer",
        "skills": ["Python", "FastAPI", "PostgreSQL", "React", "Docker"],
        "experience": [
            {
                "title": "Senior Software Engineer",
                "company": "TechCorp",
                "start_date": "2021-01",
                "end_date": "Present",
                "description": "Built microservices with Python and FastAPI",
            },
        ],
        "education": [
            {
                "institution": "MIT",
                "degree": "BS",
                "field": "Computer Science",
                "graduation_year": "2018",
            }
        ],
    }


def _sample_job_row():
    return {
        "id": "job-uuid-123",
        "title": "Backend Engineer",
        "company": "BigTech Inc",
        "description": (
            "We are looking for a backend engineer with experience in Python, "
            "FastAPI, PostgreSQL, and distributed systems."
        ),
        "location": "San Francisco, CA",
        "salary_min": 150000,
        "salary_max": 200000,
        "employment_type": "full-time",
        "remote": True,
    }


def _sample_cover_letter():
    from app.agents.pro.cover_letter_agent import CoverLetterContent

    return CoverLetterContent(
        opening=(
            "Dear Hiring Manager, I am excited to apply for the Backend Engineer "
            "position at BigTech Inc. Your focus on distributed systems and scalable "
            "APIs aligns perfectly with my background."
        ),
        body_paragraphs=[
            (
                "In my current role as Senior Software Engineer at TechCorp, I have "
                "spent the last three years building microservices with Python and "
                "FastAPI. I have designed APIs serving thousands of requests per second "
                "and worked extensively with PostgreSQL databases."
            ),
            (
                "My experience with Docker and distributed architectures makes me "
                "well-suited for this role. I am passionate about writing clean, "
                "well-tested code and have mentored junior developers on best practices."
            ),
        ],
        closing=(
            "I would welcome the opportunity to discuss how my experience can "
            "contribute to BigTech Inc's engineering team. I look forward to "
            "hearing from you."
        ),
        word_count=300,
        personalization_sources=[
            "company focus on distributed systems",
            "specific role requirement for Python and FastAPI",
        ],
    )


# ---------------------------------------------------------------------------
# Test: Happy path (AC1, AC2, AC5)
# ---------------------------------------------------------------------------


class TestCoverLetterAgentHappyPath:
    """Tests for agent happy path."""

    @pytest.mark.asyncio
    async def test_execute_generates_cover_letter_and_stores_document(self):
        """Agent produces CoverLetterContent, stores as Document, returns AgentOutput."""
        mock_cm, mock_sess = _mock_session_cm()

        # Version query returns scalar 1
        mock_version = MagicMock()
        mock_version.scalar.return_value = 1
        # Insert returns nothing
        mock_insert = MagicMock()
        mock_sess.execute = AsyncMock(side_effect=[mock_version, mock_insert])
        mock_sess.commit = AsyncMock()

        sample_cl = _sample_cover_letter()

        # Mock LLM completion
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(parsed=sample_cl))]
        mock_completion.usage = MagicMock(prompt_tokens=500, completion_tokens=300)

        mock_client = AsyncMock()
        mock_client.beta.chat.completions.parse = AsyncMock(return_value=mock_completion)

        # Mock job query (in _load_job)
        mock_job_cm, mock_job_sess = _mock_session_cm()
        mock_job_result = MagicMock()
        mock_job_result.mappings.return_value.first.return_value = _sample_job_row()
        mock_job_sess.execute = AsyncMock(return_value=mock_job_result)

        # The agent creates two sessions: _load_job and _store_document
        session_calls = [mock_job_cm, mock_cm]

        with (
            patch("app.agents.orchestrator.get_user_context", new_callable=AsyncMock, return_value={"profile": _sample_profile()}),
            patch("app.db.engine.AsyncSessionLocal", side_effect=session_calls),
            patch("openai.AsyncOpenAI", return_value=mock_client),
            patch("app.observability.cost_tracker.track_llm_cost", new_callable=AsyncMock),
        ):
            from app.agents.pro.cover_letter_agent import CoverLetterAgent

            agent = CoverLetterAgent()
            result = await agent.execute("user123", {"job_id": "job-uuid-123"})

        assert result.action == "cover_letter_generated"
        assert result.data["document_id"]
        assert result.data["job_id"] == "job-uuid-123"
        assert result.data["word_count"] == 300
        assert len(result.data["personalization_sources"]) == 2
        assert result.confidence == 0.9


# ---------------------------------------------------------------------------
# Test: Content structure (AC2)
# ---------------------------------------------------------------------------


class TestCoverLetterContentStructure:
    """Tests for cover letter content structure."""

    def test_cover_letter_content_has_required_fields(self):
        """CoverLetterContent has opening, body_paragraphs, closing, word_count."""
        cl = _sample_cover_letter()
        assert cl.opening
        assert len(cl.body_paragraphs) >= 1
        assert cl.closing
        assert cl.word_count > 0
        assert len(cl.personalization_sources) > 0

    def test_cover_letter_content_serializes_to_json(self):
        """Content can be serialized to JSON for Document.content storage."""
        cl = _sample_cover_letter()
        dumped = json.dumps(cl.model_dump())
        loaded = json.loads(dumped)
        assert loaded["opening"] == cl.opening
        assert loaded["word_count"] == cl.word_count


# ---------------------------------------------------------------------------
# Test: Word count (AC3)
# ---------------------------------------------------------------------------


class TestCoverLetterWordCount:
    """Tests for word count enforcement."""

    def test_sample_cover_letter_word_count_in_range(self):
        """Sample cover letter has word_count between 250-400."""
        cl = _sample_cover_letter()
        assert 250 <= cl.word_count <= 400


# ---------------------------------------------------------------------------
# Test: Versioning (AC6)
# ---------------------------------------------------------------------------


class TestCoverLetterVersioning:
    """Tests for auto-incrementing version on same user+job."""

    @pytest.mark.asyncio
    async def test_version_query_uses_cover_letter_type(self):
        """Version query filters by type='cover_letter'."""
        mock_cm, mock_sess = _mock_session_cm()

        mock_version = MagicMock()
        mock_version.scalar.return_value = 2  # Second version
        mock_insert = MagicMock()
        mock_sess.execute = AsyncMock(side_effect=[mock_version, mock_insert])
        mock_sess.commit = AsyncMock()

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.agents.pro.cover_letter_agent import CoverLetterAgent, CoverLetterContent

            agent = CoverLetterAgent()
            cl = CoverLetterContent(
                opening="Dear Hiring Manager",
                body_paragraphs=["I am writing to apply."],
                closing="Thank you.",
                word_count=250,
                personalization_sources=["role description"],
            )
            doc_id = await agent._store_document("user123", "job-uuid-123", cl)

        assert doc_id  # Returns a UUID string

        # Verify version query SQL includes 'cover_letter'
        version_call = mock_sess.execute.call_args_list[0]
        sql_text = str(version_call[0][0])
        assert "cover_letter" in sql_text

        # Verify insert SQL includes 'cover_letter'
        insert_call = mock_sess.execute.call_args_list[1]
        insert_sql = str(insert_call[0][0])
        assert "cover_letter" in insert_sql


# ---------------------------------------------------------------------------
# Test: Error handling — missing job_id
# ---------------------------------------------------------------------------


class TestCoverLetterErrorHandling:
    """Tests for agent error handling."""

    @pytest.mark.asyncio
    async def test_missing_job_id_returns_failure(self):
        """Agent returns failure output when no job_id provided."""
        from app.agents.pro.cover_letter_agent import CoverLetterAgent

        agent = CoverLetterAgent()
        result = await agent.execute("user123", {})

        assert result.action == "cover_letter_failed"
        assert result.data["error"] == "missing_job_id"

    @pytest.mark.asyncio
    async def test_empty_profile_returns_failure(self):
        """Agent returns failure when user has no profile data."""
        with patch(
            "app.agents.orchestrator.get_user_context",
            new_callable=AsyncMock,
            return_value={"profile": {}},
        ):
            from app.agents.pro.cover_letter_agent import CoverLetterAgent

            agent = CoverLetterAgent()
            result = await agent.execute("user123", {"job_id": "job-uuid-123"})

        assert result.action == "cover_letter_failed"
        assert result.data["error"] == "empty_profile"

    @pytest.mark.asyncio
    async def test_job_not_found_returns_failure(self):
        """Agent returns failure when job doesn't exist."""
        mock_cm, mock_sess = _mock_session_cm()
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = None
        mock_sess.execute = AsyncMock(return_value=mock_result)

        with (
            patch("app.agents.orchestrator.get_user_context", new_callable=AsyncMock, return_value={"profile": _sample_profile()}),
            patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm),
        ):
            from app.agents.pro.cover_letter_agent import CoverLetterAgent

            agent = CoverLetterAgent()
            result = await agent.execute("user123", {"job_id": "nonexistent"})

        assert result.action == "cover_letter_failed"
        assert result.data["error"] == "job_not_found"

    @pytest.mark.asyncio
    async def test_llm_failure_returns_failure(self):
        """Agent returns failure when LLM call throws."""
        mock_cm, mock_sess = _mock_session_cm()
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = _sample_job_row()
        mock_sess.execute = AsyncMock(return_value=mock_result)

        mock_client = AsyncMock()
        mock_client.beta.chat.completions.parse = AsyncMock(side_effect=Exception("API error"))

        with (
            patch("app.agents.orchestrator.get_user_context", new_callable=AsyncMock, return_value={"profile": _sample_profile()}),
            patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm),
            patch("openai.AsyncOpenAI", return_value=mock_client),
        ):
            from app.agents.pro.cover_letter_agent import CoverLetterAgent

            agent = CoverLetterAgent()
            result = await agent.execute("user123", {"job_id": "job-uuid-123"})

        assert result.action == "cover_letter_failed"
        assert result.data["error"] == "llm_failure"


# ---------------------------------------------------------------------------
# Test: API endpoint (AC7)
# ---------------------------------------------------------------------------


class TestCoverLetterAPIEndpoint:
    """Tests for POST /cover-letter endpoint."""

    @pytest.mark.asyncio
    async def test_endpoint_returns_document_id(self):
        """POST /cover-letter returns document_id and content."""
        mock_cm, mock_sess = _mock_session_cm()

        # First session: job validation query
        mock_job_result = MagicMock()
        mock_job_result.scalar_one_or_none.return_value = "job-uuid-123"
        mock_sess.execute = AsyncMock(return_value=mock_job_result)

        # Agent output mock
        from app.agents.base import AgentOutput

        mock_output = AgentOutput(
            action="cover_letter_generated",
            rationale="Generated 300-word cover letter",
            confidence=0.9,
            data={
                "document_id": "doc-uuid-456",
                "job_id": "job-uuid-123",
                "word_count": 300,
                "personalization_sources": ["company mission"],
            },
        )

        # Second session: load document content
        mock_cm2, mock_sess2 = _mock_session_cm()
        mock_doc_result = MagicMock()
        mock_doc_result.scalar_one_or_none.return_value = json.dumps({
            "opening": "Dear Hiring Manager",
            "body_paragraphs": ["I am writing..."],
            "closing": "Thank you.",
            "word_count": 300,
            "personalization_sources": ["company mission"],
        })
        mock_sess2.execute = AsyncMock(return_value=mock_doc_result)

        session_calls = [mock_cm, mock_cm2]

        with (
            patch("app.db.engine.AsyncSessionLocal", side_effect=session_calls),
            patch("app.agents.pro.cover_letter_agent.CoverLetterAgent.execute", new_callable=AsyncMock, return_value=mock_output),
        ):
            from app.api.v1.documents import CoverLetterRequest, generate_cover_letter

            result = await generate_cover_letter(
                body=CoverLetterRequest(job_id="job-uuid-123"),
                user_id="user123",
            )

        assert result["document_id"] == "doc-uuid-456"
        assert result["job_id"] == "job-uuid-123"
        assert result["word_count"] == 300
        assert result["content"]["opening"] == "Dear Hiring Manager"

    @pytest.mark.asyncio
    async def test_endpoint_missing_job_id_returns_422(self):
        """POST /cover-letter without job_id returns 422 (Pydantic validation)."""
        from app.api.v1.documents import CoverLetterRequest

        with pytest.raises(Exception):
            CoverLetterRequest()  # type: ignore[call-arg]

    @pytest.mark.asyncio
    async def test_endpoint_nonexistent_job_returns_404(self):
        """POST /cover-letter with unknown job_id returns 404."""
        mock_cm, mock_sess = _mock_session_cm()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_sess.execute = AsyncMock(return_value=mock_result)

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.api.v1.documents import CoverLetterRequest, generate_cover_letter

            with pytest.raises(Exception) as exc_info:
                await generate_cover_letter(
                    body=CoverLetterRequest(job_id="nonexistent"),
                    user_id="user123",
                )

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Test: Personalization (5-6 AC1, AC2, AC3)
# ---------------------------------------------------------------------------


class TestCoverLetterPersonalization:
    """Tests for company-specific personalization in cover letters."""

    def test_prompt_includes_company_context_section(self):
        """Prompt includes COMPANY CONTEXT section when job has rich description."""
        from app.agents.pro.cover_letter_agent import CoverLetterAgent

        agent = CoverLetterAgent()
        job = {
            "title": "Backend Engineer",
            "company": "BigTech Inc",
            "location": "SF",
            "description": (
                "At BigTech Inc, our mission is to democratize AI. "
                "We are building a platform that serves millions of users. "
                "Our team is passionate about scalable systems."
            ),
        }
        prompt = agent._build_prompt(_sample_profile(), job)

        assert "## COMPANY CONTEXT" in prompt
        assert "None available" not in prompt

    def test_company_context_extraction_with_mission(self):
        """Extracts company context when description mentions mission/values."""
        from app.agents.pro.cover_letter_agent import CoverLetterAgent

        agent = CoverLetterAgent()
        job = {
            "company": "ValueCo",
            "description": "Our mission is to make healthcare accessible to everyone.",
        }
        context = agent._extract_company_context(job)
        assert "mission" in context.lower()
        assert "ValueCo" in context

    def test_company_context_extraction_with_product(self):
        """Extracts product/team context from description."""
        from app.agents.pro.cover_letter_agent import CoverLetterAgent

        agent = CoverLetterAgent()
        job = {
            "company": "BuildCo",
            "description": "We build the next generation of developer tools.",
        }
        context = agent._extract_company_context(job)
        assert "product/team" in context.lower()

    def test_graceful_fallback_minimal_description(self):
        """Falls back gracefully when job description is minimal."""
        from app.agents.pro.cover_letter_agent import CoverLetterAgent

        agent = CoverLetterAgent()
        job = {
            "company": "",
            "description": "Python developer needed.",
        }
        context = agent._extract_company_context(job)
        assert "None available" in context

    def test_prompt_includes_fallback_context_for_minimal_job(self):
        """Prompt shows 'None available' for minimal job descriptions."""
        from app.agents.pro.cover_letter_agent import CoverLetterAgent

        agent = CoverLetterAgent()
        job = {
            "title": "Developer",
            "company": "",
            "location": "",
            "description": "Need a developer.",
        }
        prompt = agent._build_prompt(_sample_profile(), job)

        assert "## COMPANY CONTEXT" in prompt
        assert "None available" in prompt
