"""
Calendar Interview Detection Service — detects interviews from calendar events.

Analyzes calendar events (Google Calendar / Outlook format) using pattern
matching to identify potential interviews. Detected interviews are flagged
for user confirmation before triggering prep briefing generation.

Architecture: Follows the service pattern. Actual calendar API integration
is deferred; this service processes event dicts from any calendar source.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Interview detection patterns
# ---------------------------------------------------------------------------

_INTERVIEW_TITLE_PATTERNS: list[re.Pattern] = [
    re.compile(r"\binterview\b", re.IGNORECASE),
    re.compile(r"\bcall with recruiter\b", re.IGNORECASE),
    re.compile(r"\brecruiter call\b", re.IGNORECASE),
    re.compile(r"\bphone screen\b", re.IGNORECASE),
    re.compile(r"\btechnical screen\b", re.IGNORECASE),
    re.compile(r"\bonsite\b", re.IGNORECASE),
    re.compile(r"\bhiring\s+manager\b", re.IGNORECASE),
    re.compile(r"\bpanel\s+interview\b", re.IGNORECASE),
    re.compile(r"\bcoding\s+challenge\b", re.IGNORECASE),
    re.compile(r"\btake[\s-]?home\b", re.IGNORECASE),
]

# Duration range typical for interviews (in minutes)
_MIN_DURATION_MINUTES = 25
_MAX_DURATION_MINUTES = 120


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class DetectedInterview:
    """A calendar event flagged as a potential interview."""

    event_id: str = ""
    title: str = ""
    start_time: str = ""
    end_time: str = ""
    duration_minutes: int = 0
    attendees: list[str] = field(default_factory=list)
    external_attendees: list[str] = field(default_factory=list)
    matched_patterns: list[str] = field(default_factory=list)
    confidence: float = 0.0
    status: str = "pending"  # pending, confirmed, dismissed
    company_hint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "title": self.title,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_minutes": self.duration_minutes,
            "attendees": self.attendees,
            "external_attendees": self.external_attendees,
            "matched_patterns": self.matched_patterns,
            "confidence": self.confidence,
            "status": self.status,
            "company_hint": self.company_hint,
        }


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class CalendarInterviewDetector:
    """Detects potential interviews from calendar events.

    Accepts events in a normalized dict format (compatible with both
    Google Calendar and Outlook event structures).
    """

    def detect(
        self,
        events: list[dict[str, Any]],
        user_domain: str = "",
        known_companies: list[str] | None = None,
    ) -> list[DetectedInterview]:
        """Scan calendar events and flag potential interviews.

        Args:
            events: List of calendar event dicts with keys:
                id, title/summary, start, end, attendees, duration_minutes.
            user_domain: User's email domain (to identify external attendees).
            known_companies: List of company names the user has applied to.

        Returns:
            List of DetectedInterview for events that match patterns.
        """
        if known_companies is None:
            known_companies = []

        detected: list[DetectedInterview] = []

        for event in events:
            result = self._analyze_event(event, user_domain, known_companies)
            if result is not None:
                detected.append(result)

        logger.info(
            "Calendar scan: %d events analyzed, %d potential interviews",
            len(events), len(detected),
        )
        return detected

    def _analyze_event(
        self,
        event: dict[str, Any],
        user_domain: str,
        known_companies: list[str],
    ) -> DetectedInterview | None:
        """Analyze a single calendar event for interview signals."""
        title = event.get("title") or event.get("summary") or ""
        event_id = str(event.get("id", ""))
        start = str(event.get("start", ""))
        end = str(event.get("end", ""))
        duration = event.get("duration_minutes", 0)
        attendees = event.get("attendees") or []

        signals: list[str] = []
        confidence = 0.0

        # Signal 1: Title pattern matching
        for pattern in _INTERVIEW_TITLE_PATTERNS:
            if pattern.search(title):
                signals.append(f"title_match:{pattern.pattern}")
                confidence += 0.4
                break  # One title match is enough

        # Signal 2: Company name in title
        company_hint = ""
        for company in known_companies:
            if company.lower() in title.lower():
                signals.append(f"company_match:{company}")
                company_hint = company
                confidence += 0.3
                break

        # Signal 3: Duration in interview range
        if _MIN_DURATION_MINUTES <= duration <= _MAX_DURATION_MINUTES:
            signals.append("duration_in_range")
            confidence += 0.15

        # Signal 4: External attendees
        external = self._find_external_attendees(attendees, user_domain)
        if external:
            signals.append(f"external_attendees:{len(external)}")
            confidence += 0.15

        # Only flag if we have at least one strong signal
        if confidence < 0.3:
            return None

        confidence = min(confidence, 1.0)

        return DetectedInterview(
            event_id=event_id,
            title=title,
            start_time=start,
            end_time=end,
            duration_minutes=duration,
            attendees=attendees,
            external_attendees=external,
            matched_patterns=signals,
            confidence=round(confidence, 2),
            status="pending",
            company_hint=company_hint,
        )

    def _find_external_attendees(
        self, attendees: list[str], user_domain: str
    ) -> list[str]:
        """Identify attendees with different email domains."""
        if not user_domain:
            return []

        external: list[str] = []
        for attendee in attendees:
            email = attendee if "@" in attendee else ""
            if email and not email.endswith(f"@{user_domain}"):
                external.append(email)

        return external

    def confirm(self, detection: DetectedInterview) -> DetectedInterview:
        """User confirms a detected interview."""
        detection.status = "confirmed"
        return detection

    def dismiss(self, detection: DetectedInterview) -> DetectedInterview:
        """User dismisses a false positive."""
        detection.status = "dismissed"
        return detection
