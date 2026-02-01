"""Tests for email scan service (Story 6-4, Task 2).

Covers: Gmail scan, Outlook scan, no connections, batch processing.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.email_parser import StatusDetection


def _mock_session_cm():
    mock_sess = AsyncMock()
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_sess)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    return mock_cm, mock_sess


class TestScanUserEmails:
    @pytest.mark.asyncio
    async def test_no_connections_returns_empty(self):
        """No connected accounts returns empty scan result."""
        mock_cm, mock_sess = _mock_session_cm()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []
        mock_sess.execute = AsyncMock(return_value=mock_result)

        with patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm):
            from app.services.email_scan_service import scan_user_emails

            result = await scan_user_emails("user123")

        assert result.emails_processed == 0
        assert result.statuses_detected == 0

    @pytest.mark.asyncio
    async def test_gmail_scan_processes_emails(self):
        """Gmail connection fetches and processes emails."""
        mock_cm, mock_sess = _mock_session_cm()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [
            {
                "id": "conn-1",
                "provider": "gmail",
                "email_address": "test@gmail.com",
                "access_token_encrypted": "token123",
            }
        ]
        mock_sess.execute = AsyncMock(return_value=mock_result)

        mock_emails = [
            {"id": "e1", "subject": "Interview Request", "snippet": "We'd like to schedule an interview."},
        ]

        detection = StatusDetection(
            detected_status="interview",
            confidence=0.95,
            evidence_snippet="schedule an interview",
            is_ambiguous=False,
            detection_method="regex",
        )

        with (
            patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm),
            patch("app.services.gmail_service.fetch_job_emails", new_callable=AsyncMock, return_value=mock_emails),
            patch("app.services.email_parser.EmailStatusDetector.detect_enhanced", new_callable=AsyncMock, return_value=detection),
        ):
            from app.services.email_scan_service import scan_user_emails

            result = await scan_user_emails("user123")

        assert result.emails_processed == 1
        assert result.statuses_detected == 1
        assert result.flagged_for_review == 0

    @pytest.mark.asyncio
    async def test_outlook_scan_processes_emails(self):
        """Outlook connection fetches and processes emails."""
        mock_cm, mock_sess = _mock_session_cm()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [
            {
                "id": "conn-2",
                "provider": "outlook",
                "email_address": "test@outlook.com",
                "access_token_encrypted": "ms-token",
            }
        ]
        mock_sess.execute = AsyncMock(return_value=mock_result)

        mock_emails = [
            {"id": "e1", "subject": "Application Update", "snippet": "We regret to inform you."},
        ]

        detection = StatusDetection(
            detected_status="rejected",
            confidence=0.90,
            evidence_snippet="regret to inform",
            is_ambiguous=False,
            detection_method="regex",
        )

        with (
            patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm),
            patch("app.services.outlook_service.fetch_job_emails", new_callable=AsyncMock, return_value=mock_emails),
            patch("app.services.email_parser.EmailStatusDetector.detect_enhanced", new_callable=AsyncMock, return_value=detection),
        ):
            from app.services.email_scan_service import scan_user_emails

            result = await scan_user_emails("user123")

        assert result.emails_processed == 1
        assert result.statuses_detected == 1

    @pytest.mark.asyncio
    async def test_ambiguous_email_flagged_for_review(self):
        """Ambiguous detection is counted as flagged_for_review."""
        mock_cm, mock_sess = _mock_session_cm()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [
            {
                "id": "conn-1",
                "provider": "gmail",
                "email_address": "test@gmail.com",
                "access_token_encrypted": "token",
            }
        ]
        mock_sess.execute = AsyncMock(return_value=mock_result)

        mock_emails = [
            {"id": "e1", "subject": "Update", "snippet": "Ambiguous content."},
        ]

        detection = StatusDetection(
            detected_status="screening",
            confidence=0.55,
            evidence_snippet="ambiguous",
            is_ambiguous=True,
            detection_method="regex",
        )

        with (
            patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm),
            patch("app.services.gmail_service.fetch_job_emails", new_callable=AsyncMock, return_value=mock_emails),
            patch("app.services.email_parser.EmailStatusDetector.detect_enhanced", new_callable=AsyncMock, return_value=detection),
        ):
            from app.services.email_scan_service import scan_user_emails

            result = await scan_user_emails("user123")

        assert result.emails_processed == 1
        assert result.statuses_detected == 0
        assert result.flagged_for_review == 1

    @pytest.mark.asyncio
    async def test_batch_processing_multiple_emails(self):
        """Multiple emails are processed independently."""
        mock_cm, mock_sess = _mock_session_cm()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [
            {
                "id": "conn-1",
                "provider": "gmail",
                "email_address": "test@gmail.com",
                "access_token_encrypted": "token",
            }
        ]
        mock_sess.execute = AsyncMock(return_value=mock_result)

        mock_emails = [
            {"id": "e1", "subject": "Interview", "snippet": "Schedule interview."},
            {"id": "e2", "subject": "Rejection", "snippet": "Move forward with others."},
            {"id": "e3", "subject": "Newsletter", "snippet": "Blog post."},
        ]

        detections = [
            StatusDetection("interview", 0.95, "schedule", False, "regex"),
            StatusDetection("rejected", 0.90, "move forward", False, "regex"),
            StatusDetection(None, 0.0, "", True, "regex"),
        ]

        with (
            patch("app.db.engine.AsyncSessionLocal", return_value=mock_cm),
            patch("app.services.gmail_service.fetch_job_emails", new_callable=AsyncMock, return_value=mock_emails),
            patch("app.services.email_parser.EmailStatusDetector.detect_enhanced", new_callable=AsyncMock, side_effect=detections),
        ):
            from app.services.email_scan_service import scan_user_emails

            result = await scan_user_emails("user123")

        assert result.emails_processed == 3
        assert result.statuses_detected == 2
        assert result.flagged_for_review == 0
        assert len(result.details) == 3
