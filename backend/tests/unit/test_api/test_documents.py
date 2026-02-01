"""Tests for the Documents API endpoints (Story 5-2).

Covers: master resume upload, archive previous, single active master,
structured data parsing, download with signed URL, list documents,
delete document, and upload validation.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_session_cm():
    """Create a mock async session context manager."""
    mock_sess = AsyncMock()
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_sess)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    return mock_cm, mock_sess


def _make_upload_file(filename="resume.pdf", content=b"fake pdf content", content_type="application/pdf"):
    """Create a mock UploadFile."""
    mock_file = AsyncMock()
    mock_file.filename = filename
    mock_file.content_type = content_type
    mock_file.read = AsyncMock(return_value=content)
    return mock_file


def _make_parsed_profile():
    """Create a mock ExtractedProfile."""
    profile = MagicMock()
    profile.model_dump.return_value = {
        "name": "Test User",
        "email": "test@example.com",
        "phone": "555-0100",
        "headline": "Senior Engineer",
        "skills": ["Python", "FastAPI"],
        "experience": [{"company": "Acme", "title": "Engineer", "start_date": "2020-01", "end_date": "Present", "description": "Built things"}],
        "education": [{"institution": "MIT", "degree": "BS", "field": "CS", "graduation_year": "2019"}],
    }
    profile.skills = ["Python", "FastAPI"]
    profile.experience = [MagicMock(model_dump=MagicMock(return_value={"company": "Acme", "title": "Engineer"}))]
    profile.education = [MagicMock(model_dump=MagicMock(return_value={"institution": "MIT", "degree": "BS"}))]
    profile.headline = "Senior Engineer"
    return profile


# ---------------------------------------------------------------------------
# Test: Upload master resume (AC1, AC4)
# ---------------------------------------------------------------------------


class TestUploadMasterResume:
    """Tests for POST /master-resume."""

    @pytest.mark.asyncio
    async def test_upload_creates_document_and_updates_profile(self):
        """Upload stores file, creates Document, parses resume, updates Profile."""
        mock_cm, mock_sess = _mock_session_cm()
        mock_sess.execute = AsyncMock(return_value=MagicMock())
        mock_sess.commit = AsyncMock()

        parsed = _make_parsed_profile()
        mock_file = _make_upload_file()

        with (
            patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm),
            patch("app.services.storage_service.upload_file", new_callable=AsyncMock, return_value="user123/resume.pdf"),
            patch("app.services.resume_parser.extract_profile_from_resume", new_callable=AsyncMock, return_value=parsed),
        ):
            from app.api.v1.documents import upload_master_resume

            result = await upload_master_resume(file=mock_file, user_id="user123")

        assert result["document_id"]  # Non-empty UUID
        assert result["storage_path"] == "user123/resume.pdf"
        assert result["parsed"] is not None
        assert result["parsed"]["name"] == "Test User"

        # Verify SQL calls: archive old + insert new + update path + update profile data
        assert mock_sess.execute.call_count >= 4
        assert mock_sess.commit.call_count == 1

    @pytest.mark.asyncio
    async def test_upload_with_parsing_failure_still_creates_document(self):
        """When resume_parser fails, document is still created (parsed=None)."""
        mock_cm, mock_sess = _mock_session_cm()
        mock_sess.execute = AsyncMock(return_value=MagicMock())
        mock_sess.commit = AsyncMock()

        mock_file = _make_upload_file()

        with (
            patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm),
            patch("app.services.storage_service.upload_file", new_callable=AsyncMock, return_value="user123/resume.pdf"),
            patch("app.services.resume_parser.extract_profile_from_resume", new_callable=AsyncMock, side_effect=Exception("Parser failed")),
        ):
            from app.api.v1.documents import upload_master_resume

            result = await upload_master_resume(file=mock_file, user_id="user123")

        assert result["document_id"]
        assert result["parsed"] is None
        # Only 3 SQL calls: archive old + insert new + update path (no profile data update)
        assert mock_sess.execute.call_count == 3


# ---------------------------------------------------------------------------
# Test: Archive previous master (AC2)
# ---------------------------------------------------------------------------


class TestArchivePreviousMaster:
    """Tests that uploading a new master resume soft-deletes the previous one."""

    @pytest.mark.asyncio
    async def test_archive_old_master_on_new_upload(self):
        """Previous master is soft-deleted when new one is uploaded."""
        mock_cm, mock_sess = _mock_session_cm()
        mock_sess.execute = AsyncMock(return_value=MagicMock())
        mock_sess.commit = AsyncMock()

        mock_file = _make_upload_file()

        with (
            patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm),
            patch("app.services.storage_service.upload_file", new_callable=AsyncMock, return_value="user123/resume.pdf"),
            patch("app.services.resume_parser.extract_profile_from_resume", new_callable=AsyncMock, side_effect=Exception("skip")),
        ):
            from app.api.v1.documents import upload_master_resume

            await upload_master_resume(file=mock_file, user_id="user123")

        # First SQL call should be the archive UPDATE
        first_call = mock_sess.execute.call_args_list[0]
        sql_text = str(first_call[0][0])
        assert "UPDATE documents" in sql_text
        assert "deleted_at" in sql_text
        assert "archived_by_new_upload" in sql_text


# ---------------------------------------------------------------------------
# Test: Single active master (AC3)
# ---------------------------------------------------------------------------


class TestSingleActiveMaster:
    """Tests that only one active master resume exists."""

    @pytest.mark.asyncio
    async def test_archive_query_targets_active_master_only(self):
        """Archive query only targets documents with job_id IS NULL AND deleted_at IS NULL."""
        mock_cm, mock_sess = _mock_session_cm()
        mock_sess.execute = AsyncMock(return_value=MagicMock())
        mock_sess.commit = AsyncMock()

        mock_file = _make_upload_file()

        with (
            patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm),
            patch("app.services.storage_service.upload_file", new_callable=AsyncMock, return_value="user123/resume.pdf"),
            patch("app.services.resume_parser.extract_profile_from_resume", new_callable=AsyncMock, side_effect=Exception("skip")),
        ):
            from app.api.v1.documents import upload_master_resume

            await upload_master_resume(file=mock_file, user_id="user123")

        # Archive SQL must filter on job_id IS NULL AND deleted_at IS NULL
        first_call = mock_sess.execute.call_args_list[0]
        sql_text = str(first_call[0][0])
        assert "job_id IS NULL" in sql_text
        assert "deleted_at IS NULL" in sql_text


# ---------------------------------------------------------------------------
# Test: Download master resume (AC5)
# ---------------------------------------------------------------------------


class TestDownloadMasterResume:
    """Tests for GET /master-resume."""

    @pytest.mark.asyncio
    async def test_download_returns_signed_url(self):
        """Returns document metadata with signed download URL."""
        mock_cm, mock_sess = _mock_session_cm()

        doc_id = uuid4()
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = {
            "id": doc_id,
            "version": 1,
            "content": '{"name": "Test User"}',
            "created_at": datetime(2026, 1, 15, tzinfo=timezone.utc),
            "resume_storage_path": "user123/resume.pdf",
        }
        mock_sess.execute = AsyncMock(return_value=mock_result)

        with (
            patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm),
            patch("app.services.storage_service.get_signed_url", new_callable=AsyncMock, return_value="https://storage.example.com/signed/resume.pdf"),
        ):
            from app.api.v1.documents import get_master_resume

            result = await get_master_resume(user_id="user123")

        assert result["document_id"] == str(doc_id)
        assert result["version"] == 1
        assert result["download_url"] == "https://storage.example.com/signed/resume.pdf"

    @pytest.mark.asyncio
    async def test_download_not_found_returns_404(self):
        """Returns 404 when no master resume exists."""
        mock_cm, mock_sess = _mock_session_cm()

        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = None
        mock_sess.execute = AsyncMock(return_value=mock_result)

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.api.v1.documents import get_master_resume

            with pytest.raises(Exception) as exc_info:
                await get_master_resume(user_id="user123")

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Test: List documents (AC6)
# ---------------------------------------------------------------------------


class TestListDocuments:
    """Tests for GET /documents."""

    @pytest.mark.asyncio
    async def test_list_returns_paginated_documents(self):
        """Returns paginated list of user documents."""
        mock_cm, mock_sess = _mock_session_cm()

        doc_id = uuid4()
        # First call: count, second call: page
        mock_count = MagicMock()
        mock_count.scalar.return_value = 2

        mock_rows = MagicMock()
        mock_rows.mappings.return_value.all.return_value = [
            {
                "id": doc_id,
                "type": "resume",
                "version": 1,
                "job_id": None,
                "created_at": datetime(2026, 1, 15, tzinfo=timezone.utc),
            },
            {
                "id": uuid4(),
                "type": "resume",
                "version": 1,
                "job_id": uuid4(),
                "created_at": datetime(2026, 1, 14, tzinfo=timezone.utc),
            },
        ]

        mock_sess.execute = AsyncMock(side_effect=[mock_count, mock_rows])

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.api.v1.documents import list_documents

            result = await list_documents(user_id="user123", doc_type=None, page=1, page_size=20)

        assert result["total"] == 2
        assert len(result["documents"]) == 2
        assert result["page"] == 1
        assert result["page_size"] == 20
        assert result["documents"][0]["id"] == str(doc_id)

    @pytest.mark.asyncio
    async def test_list_with_type_filter(self):
        """Type filter is applied when doc_type is provided."""
        mock_cm, mock_sess = _mock_session_cm()

        mock_count = MagicMock()
        mock_count.scalar.return_value = 0
        mock_rows = MagicMock()
        mock_rows.mappings.return_value.all.return_value = []

        mock_sess.execute = AsyncMock(side_effect=[mock_count, mock_rows])

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.api.v1.documents import list_documents

            result = await list_documents(user_id="user123", doc_type="resume", page=1, page_size=20)

        # Verify the type filter was included in the SQL
        count_call = mock_sess.execute.call_args_list[0]
        sql_text = str(count_call[0][0])
        assert "d.type = :dtype" in sql_text


# ---------------------------------------------------------------------------
# Test: Delete document (AC7)
# ---------------------------------------------------------------------------


class TestDeleteDocument:
    """Tests for DELETE /documents/{document_id}."""

    @pytest.mark.asyncio
    async def test_delete_soft_deletes_document(self):
        """Soft-deletes a document owned by the user."""
        mock_cm, mock_sess = _mock_session_cm()

        doc_id = str(uuid4())
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = doc_id
        mock_sess.execute = AsyncMock(return_value=mock_result)
        mock_sess.commit = AsyncMock()

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.api.v1.documents import delete_document

            result = await delete_document(document_id=doc_id, user_id="user123")

        assert result["message"] == "Document deleted"
        assert result["document_id"] == doc_id

        # Verify soft-delete SQL
        call_args = mock_sess.execute.call_args_list[0]
        sql_text = str(call_args[0][0])
        assert "deleted_at" in sql_text
        assert "user_deleted" in sql_text

    @pytest.mark.asyncio
    async def test_delete_not_found_returns_404(self):
        """Returns 404 when document doesn't exist or not owned by user."""
        mock_cm, mock_sess = _mock_session_cm()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_sess.execute = AsyncMock(return_value=mock_result)
        mock_sess.commit = AsyncMock()

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.api.v1.documents import delete_document

            with pytest.raises(Exception) as exc_info:
                await delete_document(document_id=str(uuid4()), user_id="user123")

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Test: Upload validation (AC8)
# ---------------------------------------------------------------------------


class TestUploadValidation:
    """Tests for file validation on upload."""

    @pytest.mark.asyncio
    async def test_rejects_non_pdf_docx_files(self):
        """Rejects files that are not PDF or DOCX."""
        mock_file = _make_upload_file(filename="resume.txt", content_type="text/plain")

        from app.api.v1.documents import upload_master_resume

        with pytest.raises(Exception) as exc_info:
            await upload_master_resume(file=mock_file, user_id="user123")

        assert exc_info.value.status_code == 400
        assert "Unsupported file type" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_rejects_empty_file(self):
        """Rejects empty files."""
        mock_file = _make_upload_file(content=b"")

        from app.api.v1.documents import upload_master_resume

        with pytest.raises(Exception) as exc_info:
            await upload_master_resume(file=mock_file, user_id="user123")

        assert exc_info.value.status_code == 400
        assert "empty" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_rejects_oversized_file(self):
        """Rejects files exceeding 10MB."""
        mock_file = _make_upload_file(content=b"x" * (11 * 1024 * 1024))

        from app.api.v1.documents import upload_master_resume

        with pytest.raises(Exception) as exc_info:
            await upload_master_resume(file=mock_file, user_id="user123")

        assert exc_info.value.status_code == 400
        assert "exceeds" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_accepts_docx_file(self):
        """Accepts DOCX files."""
        mock_cm, mock_sess = _mock_session_cm()
        mock_sess.execute = AsyncMock(return_value=MagicMock())
        mock_sess.commit = AsyncMock()

        mock_file = _make_upload_file(
            filename="resume.docx",
            content=b"fake docx content",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        with (
            patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm),
            patch("app.services.storage_service.upload_file", new_callable=AsyncMock, return_value="user123/resume.docx"),
            patch("app.services.resume_parser.extract_profile_from_resume", new_callable=AsyncMock, side_effect=Exception("skip")),
        ):
            from app.api.v1.documents import upload_master_resume

            result = await upload_master_resume(file=mock_file, user_id="user123")

        assert result["document_id"]
        assert result["storage_path"] == "user123/resume.docx"


# ---------------------------------------------------------------------------
# Diff endpoint helpers
# ---------------------------------------------------------------------------


def _make_tailored_content():
    """Return JSON content matching TailoredResume structure."""
    return json.dumps({
        "sections": [
            {
                "section_name": "summary",
                "original_content": "Senior Software Engineer with 5 years experience",
                "tailored_content": "Senior Backend Engineer with 5 years building scalable APIs",
                "changes_made": ["Reframed as backend-focused", "Added API emphasis"],
            },
            {
                "section_name": "skills",
                "original_content": "Python, FastAPI, PostgreSQL, React",
                "tailored_content": "Python, FastAPI, PostgreSQL, Distributed Systems",
                "changes_made": ["Reordered for relevance"],
            },
            {
                "section_name": "new_section",
                "original_content": "",
                "tailored_content": "Relevant certifications section",
                "changes_made": ["Added certifications section"],
            },
        ],
        "keywords_incorporated": ["python", "fastapi", "backend"],
        "keywords_missing": ["kubernetes"],
        "ats_score": 82,
        "tailoring_rationale": "Emphasized backend experience for Backend Engineer role",
    })


def _make_master_content():
    """Return JSON content matching master resume (ExtractedProfile)."""
    return json.dumps({
        "name": "Test User",
        "skills": ["Python", "FastAPI"],
        "experience": [],
        "education": [],
    })


# ---------------------------------------------------------------------------
# Test: Diff endpoint happy path (AC1, AC2, AC4, AC5)
# ---------------------------------------------------------------------------


class TestDiffEndpointHappyPath:
    """Tests for GET /{document_id}/diff."""

    @pytest.mark.asyncio
    async def test_diff_returns_structured_comparison(self):
        """Returns section-level diff with ATS metrics and job context."""
        mock_cm, mock_sess = _mock_session_cm()

        tailored_id = uuid4()
        master_id = uuid4()
        job_id = uuid4()

        # Query 1: tailored document
        mock_tailored = MagicMock()
        mock_tailored.mappings.return_value.first.return_value = {
            "id": tailored_id,
            "type": "resume",
            "content": _make_tailored_content(),
            "job_id": job_id,
            "version": 1,
            "created_at": datetime(2026, 1, 15, tzinfo=timezone.utc),
        }

        # Query 2: master document
        mock_master = MagicMock()
        mock_master.mappings.return_value.first.return_value = {
            "id": master_id,
            "content": _make_master_content(),
        }

        # Query 3: job context
        mock_job = MagicMock()
        mock_job.mappings.return_value.first.return_value = {
            "title": "Backend Engineer",
            "company": "BigTech Inc",
        }

        mock_sess.execute = AsyncMock(side_effect=[mock_tailored, mock_master, mock_job])

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.api.v1.documents import get_document_diff

            result = await get_document_diff(document_id=str(tailored_id), user_id="user123")

        assert result["document_id"] == str(tailored_id)
        assert result["master_document_id"] == str(master_id)
        assert result["version"] == 1
        assert result["ats_score"] == 82
        assert result["keywords_incorporated"] == ["python", "fastapi", "backend"]
        assert result["keywords_missing"] == ["kubernetes"]
        assert result["tailoring_rationale"] == "Emphasized backend experience for Backend Engineer role"
        assert result["job"]["title"] == "Backend Engineer"
        assert result["job"]["company"] == "BigTech Inc"
        assert len(result["sections"]) == 3


# ---------------------------------------------------------------------------
# Test: Change classification (AC3)
# ---------------------------------------------------------------------------


class TestDiffChangeClassification:
    """Tests for change type classification in diff sections."""

    @pytest.mark.asyncio
    async def test_sections_classified_correctly(self):
        """Sections are classified as modified, added based on content."""
        mock_cm, mock_sess = _mock_session_cm()

        tailored_id = uuid4()
        job_id = uuid4()

        mock_tailored = MagicMock()
        mock_tailored.mappings.return_value.first.return_value = {
            "id": tailored_id,
            "type": "resume",
            "content": _make_tailored_content(),
            "job_id": job_id,
            "version": 1,
            "created_at": datetime(2026, 1, 15, tzinfo=timezone.utc),
        }

        mock_master = MagicMock()
        mock_master.mappings.return_value.first.return_value = {
            "id": uuid4(),
            "content": _make_master_content(),
        }

        mock_job = MagicMock()
        mock_job.mappings.return_value.first.return_value = {"title": "Engineer", "company": "Co"}

        mock_sess.execute = AsyncMock(side_effect=[mock_tailored, mock_master, mock_job])

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.api.v1.documents import get_document_diff

            result = await get_document_diff(document_id=str(tailored_id), user_id="user123")

        sections = result["sections"]
        # summary: both exist and differ → modified
        assert sections[0]["change_type"] == "modified"
        # skills: both exist and differ → modified
        assert sections[1]["change_type"] == "modified"
        # new_section: original empty, tailored exists → added
        assert sections[2]["change_type"] == "added"


# ---------------------------------------------------------------------------
# Test: Authorization (AC6)
# ---------------------------------------------------------------------------


class TestDiffAuthorization:
    """Tests that diff endpoint returns 404 for unauthorized access."""

    @pytest.mark.asyncio
    async def test_wrong_user_gets_404(self):
        """Returns 404 when document not owned by user."""
        mock_cm, mock_sess = _mock_session_cm()

        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = None
        mock_sess.execute = AsyncMock(return_value=mock_result)

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.api.v1.documents import get_document_diff

            with pytest.raises(Exception) as exc_info:
                await get_document_diff(document_id=str(uuid4()), user_id="wrong_user")

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Test: Validation (AC7)
# ---------------------------------------------------------------------------


class TestDiffValidation:
    """Tests for validation — master resume and non-existent docs."""

    @pytest.mark.asyncio
    async def test_master_resume_returns_400(self):
        """Returns 400 when requesting diff for a master resume (no job_id)."""
        mock_cm, mock_sess = _mock_session_cm()

        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = {
            "id": uuid4(),
            "type": "resume",
            "content": "{}",
            "job_id": None,  # Master resume
            "version": 1,
            "created_at": datetime(2026, 1, 15, tzinfo=timezone.utc),
        }
        mock_sess.execute = AsyncMock(return_value=mock_result)

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.api.v1.documents import get_document_diff

            with pytest.raises(Exception) as exc_info:
                await get_document_diff(document_id=str(uuid4()), user_id="user123")

        assert exc_info.value.status_code == 400
        assert "tailored" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_nonexistent_document_returns_404(self):
        """Returns 404 when document doesn't exist."""
        mock_cm, mock_sess = _mock_session_cm()

        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = None
        mock_sess.execute = AsyncMock(return_value=mock_result)

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.api.v1.documents import get_document_diff

            with pytest.raises(Exception) as exc_info:
                await get_document_diff(document_id=str(uuid4()), user_id="user123")

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_no_master_resume_returns_404(self):
        """Returns 404 when no master resume exists for the user."""
        mock_cm, mock_sess = _mock_session_cm()

        # Tailored doc exists
        mock_tailored = MagicMock()
        mock_tailored.mappings.return_value.first.return_value = {
            "id": uuid4(),
            "type": "resume",
            "content": _make_tailored_content(),
            "job_id": uuid4(),
            "version": 1,
            "created_at": datetime(2026, 1, 15, tzinfo=timezone.utc),
        }

        # No master resume
        mock_master = MagicMock()
        mock_master.mappings.return_value.first.return_value = None

        mock_sess.execute = AsyncMock(side_effect=[mock_tailored, mock_master])

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.api.v1.documents import get_document_diff

            with pytest.raises(Exception) as exc_info:
                await get_document_diff(document_id=str(uuid4()), user_id="user123")

        assert exc_info.value.status_code == 404
        assert "master resume" in str(exc_info.value.detail).lower()


# ---------------------------------------------------------------------------
# Test: ATS metrics in response (AC4, AC8)
# ---------------------------------------------------------------------------


class TestDiffATSMetrics:
    """Tests that ATS metrics are included in diff response."""

    @pytest.mark.asyncio
    async def test_ats_metrics_present(self):
        """Response includes ats_score, keywords_incorporated, keywords_missing."""
        mock_cm, mock_sess = _mock_session_cm()

        mock_tailored = MagicMock()
        mock_tailored.mappings.return_value.first.return_value = {
            "id": uuid4(),
            "type": "resume",
            "content": _make_tailored_content(),
            "job_id": uuid4(),
            "version": 1,
            "created_at": datetime(2026, 1, 15, tzinfo=timezone.utc),
        }

        mock_master = MagicMock()
        mock_master.mappings.return_value.first.return_value = {
            "id": uuid4(),
            "content": _make_master_content(),
        }

        mock_job = MagicMock()
        mock_job.mappings.return_value.first.return_value = {"title": "Eng", "company": "Co"}

        mock_sess.execute = AsyncMock(side_effect=[mock_tailored, mock_master, mock_job])

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.api.v1.documents import get_document_diff

            result = await get_document_diff(document_id=str(uuid4()), user_id="user123")

        assert "ats_score" in result
        assert result["ats_score"] == 82
        assert "keywords_incorporated" in result
        assert len(result["keywords_incorporated"]) == 3
        assert "keywords_missing" in result
        assert result["keywords_missing"] == ["kubernetes"]
        assert "tailoring_rationale" in result
