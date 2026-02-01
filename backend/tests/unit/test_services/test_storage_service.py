"""Tests for Supabase Storage service.

Covers upload, signed URL generation, deletion, file validation,
and graceful degradation when Supabase is not configured.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services.storage_service import (
    ACCEPTED_CONTENT_TYPES,
    ACCEPTED_EXTENSIONS,
    DEFAULT_BUCKET,
    MAX_FILE_SIZE_BYTES,
    delete_file,
    get_signed_url,
    upload_file,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_PDF = b"%PDF-1.4 sample content"
SAMPLE_USER_ID = "user_abc123"


@pytest.fixture
def mock_settings_configured():
    """Settings with Supabase configured."""
    with patch("app.services.storage_service.settings") as mock_s:
        mock_s.SUPABASE_URL = "https://test.supabase.co"
        mock_s.SUPABASE_KEY = "test-key"
        yield mock_s


@pytest.fixture
def mock_settings_unconfigured():
    """Settings with Supabase NOT configured."""
    with patch("app.services.storage_service.settings") as mock_s:
        mock_s.SUPABASE_URL = ""
        mock_s.SUPABASE_KEY = ""
        yield mock_s


@pytest.fixture
def mock_storage():
    """Mock the _get_storage() helper."""
    with patch("app.services.storage_service._get_storage") as mock_gs:
        mock_bucket = MagicMock()
        mock_gs.return_value.from_ = MagicMock(return_value=mock_bucket)
        yield mock_bucket


# ---------------------------------------------------------------------------
# upload_file tests
# ---------------------------------------------------------------------------


class TestUploadFile:
    """Tests for upload_file()."""

    @pytest.mark.asyncio
    async def test_upload_calls_supabase_with_correct_params(
        self, mock_settings_configured, mock_storage
    ):
        """upload_file calls Supabase SDK with correct bucket, path, and options."""
        result = await upload_file(
            user_id=SAMPLE_USER_ID,
            file_bytes=SAMPLE_PDF,
            filename="resume.pdf",
            content_type="application/pdf",
        )

        assert result == f"{SAMPLE_USER_ID}/resume.pdf"
        mock_storage.upload.assert_called_once_with(
            path=f"{SAMPLE_USER_ID}/resume.pdf",
            file=SAMPLE_PDF,
            file_options={"content-type": "application/pdf"},
        )

    @pytest.mark.asyncio
    async def test_upload_graceful_degradation_no_supabase(
        self, mock_settings_unconfigured
    ):
        """upload_file returns path without calling Supabase when not configured."""
        result = await upload_file(
            user_id=SAMPLE_USER_ID,
            file_bytes=SAMPLE_PDF,
            filename="resume.pdf",
        )

        assert result == f"{SAMPLE_USER_ID}/resume.pdf"

    @pytest.mark.asyncio
    async def test_upload_rejects_oversized_file(self, mock_settings_configured):
        """upload_file raises ValueError for files exceeding 10MB."""
        big_file = b"x" * (MAX_FILE_SIZE_BYTES + 1)

        with pytest.raises(ValueError, match="exceeds maximum"):
            await upload_file(
                user_id=SAMPLE_USER_ID,
                file_bytes=big_file,
                filename="big.pdf",
            )

    @pytest.mark.asyncio
    async def test_upload_rejects_unsupported_extension(
        self, mock_settings_configured
    ):
        """upload_file raises ValueError for unsupported file extensions."""
        with pytest.raises(ValueError, match="Unsupported file extension"):
            await upload_file(
                user_id=SAMPLE_USER_ID,
                file_bytes=SAMPLE_PDF,
                filename="resume.txt",
            )

    @pytest.mark.asyncio
    async def test_upload_rejects_exe_extension(self, mock_settings_configured):
        """upload_file raises ValueError for .exe files."""
        with pytest.raises(ValueError, match="Unsupported file extension"):
            await upload_file(
                user_id=SAMPLE_USER_ID,
                file_bytes=SAMPLE_PDF,
                filename="malware.exe",
            )

    @pytest.mark.asyncio
    async def test_upload_rejects_unsupported_content_type(
        self, mock_settings_configured
    ):
        """upload_file raises ValueError for unsupported content types."""
        with pytest.raises(ValueError, match="Unsupported content type"):
            await upload_file(
                user_id=SAMPLE_USER_ID,
                file_bytes=SAMPLE_PDF,
                filename="resume.pdf",
                content_type="text/plain",
            )

    @pytest.mark.asyncio
    async def test_upload_handles_409_duplicate_by_upserting(
        self, mock_settings_configured, mock_storage
    ):
        """upload_file handles 409 Duplicate by calling update instead."""
        mock_storage.upload.side_effect = Exception("409 Duplicate")
        mock_storage.update = MagicMock()

        result = await upload_file(
            user_id=SAMPLE_USER_ID,
            file_bytes=SAMPLE_PDF,
            filename="resume.pdf",
        )

        assert result == f"{SAMPLE_USER_ID}/resume.pdf"
        mock_storage.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_without_content_type(
        self, mock_settings_configured, mock_storage
    ):
        """upload_file works without content_type parameter."""
        result = await upload_file(
            user_id=SAMPLE_USER_ID,
            file_bytes=SAMPLE_PDF,
            filename="resume.pdf",
        )

        assert result == f"{SAMPLE_USER_ID}/resume.pdf"
        mock_storage.upload.assert_called_once_with(
            path=f"{SAMPLE_USER_ID}/resume.pdf",
            file=SAMPLE_PDF,
            file_options=None,
        )

    @pytest.mark.asyncio
    async def test_upload_docx_accepted(
        self, mock_settings_configured, mock_storage
    ):
        """upload_file accepts .docx files."""
        result = await upload_file(
            user_id=SAMPLE_USER_ID,
            file_bytes=SAMPLE_PDF,
            filename="resume.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        assert result == f"{SAMPLE_USER_ID}/resume.docx"


# ---------------------------------------------------------------------------
# get_signed_url tests
# ---------------------------------------------------------------------------


class TestGetSignedUrl:
    """Tests for get_signed_url()."""

    @pytest.mark.asyncio
    async def test_signed_url_returns_url_with_correct_expiry(
        self, mock_settings_configured, mock_storage
    ):
        """get_signed_url calls create_signed_url with correct params."""
        mock_storage.create_signed_url = MagicMock(
            return_value={"signedURL": "https://storage.supabase.co/signed/resume.pdf?token=abc"}
        )

        result = await get_signed_url("user_123/resume.pdf", expires_in=900)

        assert "signed" in result
        mock_storage.create_signed_url.assert_called_once_with(
            "user_123/resume.pdf", 900
        )

    @pytest.mark.asyncio
    async def test_signed_url_graceful_degradation(self, mock_settings_unconfigured):
        """get_signed_url returns placeholder URL when Supabase not configured."""
        result = await get_signed_url("user_123/resume.pdf")

        assert "placeholder.storage" in result
        assert "resumes" in result
        assert "user_123/resume.pdf" in result


# ---------------------------------------------------------------------------
# delete_file tests
# ---------------------------------------------------------------------------


class TestDeleteFile:
    """Tests for delete_file()."""

    @pytest.mark.asyncio
    async def test_delete_removes_file_returns_true(
        self, mock_settings_configured, mock_storage
    ):
        """delete_file removes file from bucket and returns True."""
        mock_storage.remove = MagicMock()

        result = await delete_file("user_123/resume.pdf")

        assert result is True
        mock_storage.remove.assert_called_once_with(["user_123/resume.pdf"])

    @pytest.mark.asyncio
    async def test_delete_graceful_degradation(self, mock_settings_unconfigured):
        """delete_file returns True when Supabase not configured."""
        result = await delete_file("user_123/resume.pdf")

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_returns_false_on_error(
        self, mock_settings_configured, mock_storage
    ):
        """delete_file returns False when Supabase raises an exception."""
        mock_storage.remove = MagicMock(side_effect=Exception("Storage error"))

        result = await delete_file("user_123/resume.pdf")

        assert result is False
