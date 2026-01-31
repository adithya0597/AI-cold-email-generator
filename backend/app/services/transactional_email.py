"""
Transactional email service using the Resend SDK.

This service handles system-generated emails (briefings, notifications,
account-related messages).  It is separate from the legacy
``email_service.py`` which handles LLM-generated cold-email content.

ADR-6 resolved: Resend was chosen over SendGrid for better DX,
generous free tier (3 000 emails/month), and simpler API surface.

Usage::

    from app.services.transactional_email import send_email, send_briefing

    await send_email(
        to="user@example.com",
        subject="Your daily briefing",
        html="<h1>Good morning</h1>...",
    )
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

TEMPLATES: Dict[str, str] = {
    "briefing": """
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
        <h1 style="color: #4F46E5;">Your Daily Job Briefing</h1>
        <p>Hi {user_name},</p>
        {content}
        <hr style="border: none; border-top: 1px solid #E5E7EB; margin: 24px 0;" />
        <p style="color: #6B7280; font-size: 12px;">
            You are receiving this because you have briefings enabled in JobPilot.
            <a href="{unsubscribe_url}">Unsubscribe</a>
        </p>
    </div>
    """,
    "welcome": """
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
        <h1 style="color: #4F46E5;">Welcome to JobPilot</h1>
        <p>Hi {user_name},</p>
        <p>Your AI career agent is ready to start working for you.</p>
        <p>Here is what happens next:</p>
        <ol>
            <li>Upload your resume so we can tailor applications</li>
            <li>Set your job preferences and target companies</li>
            <li>Let your agent start finding and applying to opportunities</li>
        </ol>
        <a href="{dashboard_url}" style="display: inline-block; padding: 12px 24px;
           background-color: #4F46E5; color: white; text-decoration: none;
           border-radius: 6px; margin-top: 16px;">
           Go to Dashboard
        </a>
    </div>
    """,
    "account_deletion": """
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
        <h1 style="color: #DC2626;">Account Deletion Scheduled</h1>
        <p>Hi {user_name},</p>
        <p>Your JobPilot account has been scheduled for deletion. All your data
        will be permanently removed in <strong>30 days</strong>.</p>
        <p>If this was a mistake, sign in to cancel the deletion before the
        grace period expires.</p>
    </div>
    """,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def send_email(
    to: str,
    subject: str,
    html: str,
    from_email: str = "JobPilot <noreply@jobpilot.ai>",
    reply_to: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send a transactional email via Resend.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        html: HTML body content.
        from_email: Sender address (must be verified in Resend dashboard).
        reply_to: Optional reply-to address.

    Returns:
        Resend API response dict with ``id`` on success.

    Raises:
        RuntimeError: If RESEND_API_KEY is not configured.
        Exception: On Resend API errors.
    """
    if not settings.RESEND_API_KEY:
        logger.warning(
            "RESEND_API_KEY not configured -- email to %s suppressed", to
        )
        return {"id": None, "suppressed": True}

    try:
        import resend

        resend.api_key = settings.RESEND_API_KEY

        params: Dict[str, Any] = {
            "from": from_email,
            "to": [to],
            "subject": subject,
            "html": html,
        }
        if reply_to:
            params["reply_to"] = reply_to

        response = resend.Emails.send(params)
        logger.info("Email sent to %s -- id=%s", to, response.get("id"))
        return response

    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to, exc)
        raise


async def send_briefing(
    to: str,
    user_name: str,
    content_html: str,
    unsubscribe_url: str = "#",
) -> Dict[str, Any]:
    """
    Send a daily job briefing email using the briefing template.

    Args:
        to: Recipient email address.
        user_name: User's display name for personalisation.
        content_html: The main briefing content (HTML).
        unsubscribe_url: Link to unsubscribe from briefings.

    Returns:
        Resend API response dict.
    """
    html = TEMPLATES["briefing"].format(
        user_name=user_name,
        content=content_html,
        unsubscribe_url=unsubscribe_url,
    )
    return await send_email(
        to=to,
        subject="Your Daily Job Briefing -- JobPilot",
        html=html,
    )


async def send_welcome(
    to: str,
    user_name: str,
    dashboard_url: str = "https://app.jobpilot.ai/dashboard",
) -> Dict[str, Any]:
    """Send a welcome email after account creation."""
    html = TEMPLATES["welcome"].format(
        user_name=user_name,
        dashboard_url=dashboard_url,
    )
    return await send_email(
        to=to,
        subject="Welcome to JobPilot",
        html=html,
    )


async def send_account_deletion_notice(
    to: str,
    user_name: str,
) -> Dict[str, Any]:
    """Send confirmation that account deletion has been scheduled."""
    html = TEMPLATES["account_deletion"].format(user_name=user_name)
    return await send_email(
        to=to,
        subject="Account Deletion Scheduled -- JobPilot",
        html=html,
    )
