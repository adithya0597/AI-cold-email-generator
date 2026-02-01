"""Email scanning service for JobPilot (Story 6-4).

Orchestrates fetching emails from connected providers (Gmail/Outlook)
and running status detection via the Pipeline Agent for each matched email.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Summary of an email scan run."""

    emails_processed: int = 0
    statuses_detected: int = 0
    flagged_for_review: int = 0
    errors: int = 0
    details: list[dict[str, Any]] = field(default_factory=list)


async def _get_user_connections(user_id: str) -> list[dict[str, Any]]:
    """Fetch active email connections for a user."""
    from sqlalchemy import text

    from app.db.engine import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                "SELECT id, provider, email_address, access_token_encrypted "
                "FROM email_connections "
                "WHERE user_id = (SELECT id FROM users WHERE clerk_id = :uid) "
                "AND status = 'active' "
                "AND deleted_at IS NULL"
            ),
            {"uid": user_id},
        )
        rows = result.mappings().all()

    return [
        {
            "id": str(row["id"]),
            "provider": row["provider"],
            "email_address": row["email_address"],
            "access_token": row["access_token_encrypted"],
        }
        for row in rows
    ]


async def _fetch_emails_for_connection(
    connection: dict[str, Any],
) -> list[dict[str, str]]:
    """Fetch job-related emails from a connected provider."""
    provider = connection["provider"]
    access_token = connection["access_token"]

    if provider == "gmail":
        from app.services.gmail_service import fetch_job_emails

        return await fetch_job_emails(access_token)
    elif provider == "outlook":
        from app.services.outlook_service import fetch_job_emails

        return await fetch_job_emails(access_token)
    else:
        logger.warning("Unknown email provider: %s", provider)
        return []


async def scan_user_emails(user_id: str) -> ScanResult:
    """Scan all connected email accounts for application status updates.

    Fetches emails from Gmail/Outlook, runs status detection on each,
    and returns a summary of results.
    """
    from app.services.email_parser import EmailStatusDetector

    connections = await _get_user_connections(user_id)

    if not connections:
        return ScanResult()

    detector = EmailStatusDetector()
    scan = ScanResult()

    for connection in connections:
        try:
            emails = await _fetch_emails_for_connection(connection)
        except Exception as exc:
            logger.error(
                "Failed to fetch emails from %s: %s", connection["provider"], exc
            )
            scan.errors += 1
            continue

        for email in emails:
            scan.emails_processed += 1
            subject = email.get("subject", "")
            snippet = email.get("snippet", "")

            try:
                result = await detector.detect_enhanced(subject, snippet)
            except Exception as exc:
                logger.error("Detection failed for email %s: %s", email.get("id"), exc)
                scan.errors += 1
                continue

            detail = {
                "email_id": email.get("id", ""),
                "subject": subject,
                "detected_status": result.detected_status,
                "confidence": result.confidence,
                "detection_method": result.detection_method,
                "is_ambiguous": result.is_ambiguous,
            }
            scan.details.append(detail)

            if result.detected_status is not None:
                if result.is_ambiguous:
                    scan.flagged_for_review += 1
                else:
                    scan.statuses_detected += 1

    return scan
