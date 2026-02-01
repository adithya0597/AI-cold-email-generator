"""Tests for transactional email service and Resend webhook handling."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from unittest.mock import MagicMock, patch

import pytest

from app.services.transactional_email import (
    TEMPLATES,
    send_account_deletion_notice,
    send_briefing,
    send_email,
    send_welcome,
)


# ---------------------------------------------------------------------------
# send_email tests
# ---------------------------------------------------------------------------


class TestSendEmail:
    """Test core email sending function."""

    @pytest.mark.asyncio
    @patch("app.services.transactional_email.settings")
    async def test_suppressed_when_api_key_not_set(self, mock_settings):
        """Returns suppressed response when RESEND_API_KEY is empty."""
        mock_settings.RESEND_API_KEY = ""

        result = await send_email(
            to="user@example.com",
            subject="Test",
            html="<p>Hello</p>",
        )

        assert result["suppressed"] is True
        assert result["id"] is None

    @pytest.mark.asyncio
    @patch("app.services.transactional_email.resend", create=True)
    @patch("app.services.transactional_email.settings")
    async def test_calls_resend_sdk_with_correct_params(self, mock_settings, mock_resend):
        """Calls resend.Emails.send with correct parameters."""
        mock_settings.RESEND_API_KEY = "re_test_key"

        # Mock the lazy import by patching at module level
        mock_resend.Emails.send.return_value = {"id": "email_123"}

        # We need to patch the import inside send_email
        with patch("app.services.transactional_email.settings") as ms:
            ms.RESEND_API_KEY = "re_test_key"
            # Patch the import statement
            import app.services.transactional_email as te_mod

            original_send = te_mod.send_email

            # Directly test with mocked resend
            with patch.dict("sys.modules", {"resend": mock_resend}):
                result = await original_send(
                    to="user@example.com",
                    subject="Test Subject",
                    html="<p>Content</p>",
                )

        mock_resend.Emails.send.assert_called_once()
        call_args = mock_resend.Emails.send.call_args[0][0]
        assert call_args["to"] == ["user@example.com"]
        assert call_args["subject"] == "Test Subject"
        assert call_args["html"] == "<p>Content</p>"

    @pytest.mark.asyncio
    @patch("app.services.transactional_email.settings")
    async def test_includes_reply_to_when_provided(self, mock_settings):
        """Reply-to is included in params when provided."""
        mock_settings.RESEND_API_KEY = "re_test"
        mock_resend = MagicMock()
        mock_resend.Emails.send.return_value = {"id": "email_456"}

        with patch.dict("sys.modules", {"resend": mock_resend}):
            await send_email(
                to="user@example.com",
                subject="Test",
                html="<p>Hi</p>",
                reply_to="reply@example.com",
            )

        call_args = mock_resend.Emails.send.call_args[0][0]
        assert call_args["reply_to"] == "reply@example.com"


# ---------------------------------------------------------------------------
# Template helper tests
# ---------------------------------------------------------------------------


class TestSendBriefing:
    """Test briefing email with template."""

    @pytest.mark.asyncio
    @patch("app.services.transactional_email.send_email")
    async def test_uses_briefing_template(self, mock_send):
        """Briefing email uses correct template with personalization."""
        mock_send.return_value = {"id": "brief_1"}

        await send_briefing(
            to="user@example.com",
            user_name="Alice",
            content_html="<p>3 new matches</p>",
            unsubscribe_url="https://app.jobpilot.ai/unsubscribe/abc",
        )

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]
        assert "Alice" in call_kwargs["html"]
        assert "3 new matches" in call_kwargs["html"]
        assert "https://app.jobpilot.ai/unsubscribe/abc" in call_kwargs["html"]
        assert call_kwargs["subject"] == "Your Daily Job Briefing -- JobPilot"


class TestSendWelcome:
    """Test welcome email with template."""

    @pytest.mark.asyncio
    @patch("app.services.transactional_email.send_email")
    async def test_uses_welcome_template(self, mock_send):
        """Welcome email uses correct template."""
        mock_send.return_value = {"id": "welcome_1"}

        await send_welcome(to="user@example.com", user_name="Bob")

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]
        assert "Bob" in call_kwargs["html"]
        assert "Welcome to JobPilot" in call_kwargs["subject"]


class TestSendAccountDeletion:
    """Test account deletion notice."""

    @pytest.mark.asyncio
    @patch("app.services.transactional_email.send_email")
    async def test_uses_deletion_template(self, mock_send):
        """Deletion notice uses correct template."""
        mock_send.return_value = {"id": "del_1"}

        await send_account_deletion_notice(to="user@example.com", user_name="Carol")

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]
        assert "Carol" in call_kwargs["html"]
        assert "Account Deletion" in call_kwargs["subject"]


# ---------------------------------------------------------------------------
# CAN-SPAM compliance tests
# ---------------------------------------------------------------------------


class TestCanSpamCompliance:
    """Verify templates include required elements."""

    def test_briefing_template_has_unsubscribe(self):
        """Briefing template includes unsubscribe link."""
        assert "unsubscribe" in TEMPLATES["briefing"].lower()
        assert "{unsubscribe_url}" in TEMPLATES["briefing"]

    def test_briefing_template_has_sender_info(self):
        """Briefing template identifies sender."""
        assert "JobPilot" in TEMPLATES["briefing"]


# ---------------------------------------------------------------------------
# Webhook signature verification tests
# ---------------------------------------------------------------------------


class TestVerifyWebhookSignature:
    """Test Resend webhook signature verification."""

    def _sign(self, payload: bytes, msg_id: str, timestamp: str, secret: str) -> str:
        """Helper to create a valid svix signature."""
        secret_bytes = base64.b64decode(secret.split("_", 1)[-1])
        to_sign = f"{msg_id}.{timestamp}.{payload.decode()}"
        sig = base64.b64encode(
            hmac.new(secret_bytes, to_sign.encode(), hashlib.sha256).digest()
        ).decode()
        return f"v1,{sig}"

    def test_valid_signature_accepted(self):
        """Valid signature returns True."""
        from app.api.v1.webhooks import verify_webhook_signature

        # Create a secret key (base64-encoded)
        raw_key = b"test-secret-key-1234567890123456"
        secret = "whsec_" + base64.b64encode(raw_key).decode()
        payload = b'{"type":"email.delivered","data":{}}'
        msg_id = "msg_abc123"
        timestamp = str(int(time.time()))
        signature = self._sign(payload, msg_id, timestamp, secret)

        assert verify_webhook_signature(
            payload=payload,
            svix_id=msg_id,
            svix_timestamp=timestamp,
            svix_signature=signature,
            secret=secret,
        )

    def test_invalid_signature_rejected(self):
        """Invalid signature returns False."""
        from app.api.v1.webhooks import verify_webhook_signature

        assert not verify_webhook_signature(
            payload=b'{"type":"email.delivered"}',
            svix_id="msg_123",
            svix_timestamp=str(int(time.time())),
            svix_signature="v1,invalid_signature",
            secret="whsec_" + base64.b64encode(b"secret").decode(),
        )

    def test_expired_timestamp_rejected(self):
        """Stale timestamp (>5min) returns False."""
        from app.api.v1.webhooks import verify_webhook_signature

        old_timestamp = str(int(time.time()) - 600)  # 10 minutes ago

        assert not verify_webhook_signature(
            payload=b'{"type":"email.delivered"}',
            svix_id="msg_123",
            svix_timestamp=old_timestamp,
            svix_signature="v1,some_sig",
            secret="whsec_" + base64.b64encode(b"secret").decode(),
        )

    def test_invalid_timestamp_rejected(self):
        """Non-numeric timestamp returns False."""
        from app.api.v1.webhooks import verify_webhook_signature

        assert not verify_webhook_signature(
            payload=b"{}",
            svix_id="msg_123",
            svix_timestamp="not-a-number",
            svix_signature="v1,sig",
            secret="whsec_" + base64.b64encode(b"secret").decode(),
        )


# ---------------------------------------------------------------------------
# Webhook endpoint tests
# ---------------------------------------------------------------------------


class TestResendWebhookEndpoint:
    """Test the webhook endpoint behavior."""

    @pytest.mark.asyncio
    async def test_processes_delivery_event(self):
        """Delivery event is processed successfully."""
        from fastapi.testclient import TestClient

        from app.api.v1.webhooks import router

        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        with patch("app.api.v1.webhooks.settings") as mock_settings:
            mock_settings.RESEND_WEBHOOK_SECRET = ""  # Skip signature check

            client = TestClient(app)
            response = client.post(
                "/webhooks/resend",
                json={
                    "type": "email.delivered",
                    "data": {"email_id": "em_123", "to": ["user@test.com"]},
                },
            )

        assert response.status_code == 200
        assert response.json()["status"] == "processed"
        assert response.json()["event_type"] == "email.delivered"

    @pytest.mark.asyncio
    async def test_processes_bounce_event(self):
        """Bounce event is processed with warning."""
        from fastapi.testclient import TestClient

        from app.api.v1.webhooks import router

        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        with patch("app.api.v1.webhooks.settings") as mock_settings:
            mock_settings.RESEND_WEBHOOK_SECRET = ""

            client = TestClient(app)
            response = client.post(
                "/webhooks/resend",
                json={
                    "type": "email.bounced",
                    "data": {"email_id": "em_456", "to": ["bounce@test.com"]},
                },
            )

        assert response.status_code == 200
        assert response.json()["status"] == "processed"

    @pytest.mark.asyncio
    async def test_ignores_unknown_event(self):
        """Unknown event type returns ignored status."""
        from fastapi.testclient import TestClient

        from app.api.v1.webhooks import router

        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        with patch("app.api.v1.webhooks.settings") as mock_settings:
            mock_settings.RESEND_WEBHOOK_SECRET = ""

            client = TestClient(app)
            response = client.post(
                "/webhooks/resend",
                json={"type": "email.unknown_type", "data": {}},
            )

        assert response.status_code == 200
        assert response.json()["status"] == "ignored"

    @pytest.mark.asyncio
    async def test_rejects_invalid_signature(self):
        """Invalid signature returns 401."""
        from fastapi.testclient import TestClient

        from app.api.v1.webhooks import router

        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        with patch("app.api.v1.webhooks.settings") as mock_settings:
            mock_settings.RESEND_WEBHOOK_SECRET = (
                "whsec_" + base64.b64encode(b"test-secret").decode()
            )

            client = TestClient(app)
            response = client.post(
                "/webhooks/resend",
                json={"type": "email.delivered", "data": {}},
                headers={
                    "svix-id": "msg_test",
                    "svix-timestamp": str(int(time.time())),
                    "svix-signature": "v1,invalid",
                },
            )

        assert response.status_code == 401
