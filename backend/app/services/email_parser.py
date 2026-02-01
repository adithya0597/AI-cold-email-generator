"""
Email status detection service for the Pipeline Agent.

Analyzes email subject and body text to detect application status changes
using keyword/pattern matching. Returns structured results with confidence
scores and evidence snippets.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class StatusDetection:
    """Result of analyzing an email for application status signals."""

    detected_status: Optional[str]  # application_status enum value or None
    confidence: float  # 0.0 - 1.0
    evidence_snippet: str  # The text that triggered the detection
    is_ambiguous: bool  # True if confidence < 0.7
    detection_method: str = "regex"  # 'regex' or 'llm'


# ---------------------------------------------------------------------------
# Pattern definitions
# ---------------------------------------------------------------------------

# Each pattern: (compiled regex, application_status, base confidence)
_REJECTION_PATTERNS = [
    (re.compile(r"decided\s+to\s+(move|proceed)\s+forward\s+with\s+other", re.I), "rejected", 0.95),
    (re.compile(r"not\s+(be\s+)?moving\s+forward\s+with\s+your", re.I), "rejected", 0.95),
    (re.compile(r"unfortunately.{0,40}(not\s+selected|will\s+not\s+be\s+proceeding)", re.I), "rejected", 0.90),
    (re.compile(r"after\s+careful\s+consideration.{0,40}(other\s+candidates|different\s+direction)", re.I), "rejected", 0.90),
    (re.compile(r"position\s+has\s+been\s+filled", re.I), "rejected", 0.90),
    (re.compile(r"regret\s+to\s+inform", re.I), "rejected", 0.85),
    (re.compile(r"we\s+will\s+not\s+be\s+able\s+to\s+offer", re.I), "rejected", 0.90),
]

_INTERVIEW_PATTERNS = [
    (re.compile(r"(like|love)\s+to\s+schedule\s+(an?\s+)?interview", re.I), "interview", 0.95),
    (re.compile(r"invite\s+you\s+(to|for)\s+(an?\s+)?interview", re.I), "interview", 0.95),
    (re.compile(r"would\s+you\s+be\s+available\s+(for|to).{0,30}(interview|call|chat)", re.I), "interview", 0.90),
    (re.compile(r"schedule\s+(a\s+)?(phone|video|technical|onsite)\s+(screen|interview|call)", re.I), "interview", 0.90),
    (re.compile(r"(next\s+step|move\s+forward).{0,30}(interview|conversation|discussion)", re.I), "interview", 0.85),
    (re.compile(r"pleased\s+to\s+advance\s+you", re.I), "interview", 0.85),
]

_OFFER_PATTERNS = [
    (re.compile(r"pleased\s+to\s+(offer|extend)", re.I), "offer", 0.95),
    (re.compile(r"(offer\s+letter|formal\s+offer)\s+(attached|enclosed|for\s+your)", re.I), "offer", 0.95),
    (re.compile(r"congratulations.{0,30}(offer|selected|chosen)", re.I), "offer", 0.90),
    (re.compile(r"we('d|\s+would)\s+like\s+to\s+offer\s+you", re.I), "offer", 0.95),
]

_APPLIED_PATTERNS = [
    (re.compile(r"(thank\s+you|thanks)\s+for\s+(applying|your\s+application)", re.I), "applied", 0.80),
    (re.compile(r"(received|confirm).{0,20}(your\s+application|your\s+submission)", re.I), "applied", 0.85),
    (re.compile(r"application.{0,20}(received|submitted\s+successfully)", re.I), "applied", 0.85),
]

_SCREENING_PATTERNS = [
    (re.compile(r"(reviewing|review)\s+your\s+(application|resume|profile)", re.I), "screening", 0.75),
    (re.compile(r"your\s+application\s+is\s+(\w+\s+)?(being\s+)?reviewed", re.I), "screening", 0.75),
    (re.compile(r"(shortlisted|under\s+consideration)", re.I), "screening", 0.80),
]

# Ordered from highest-signal to lowest to avoid ambiguity
_ALL_PATTERNS = (
    _OFFER_PATTERNS
    + _INTERVIEW_PATTERNS
    + _REJECTION_PATTERNS
    + _SCREENING_PATTERNS
    + _APPLIED_PATTERNS
)

CONFIDENCE_THRESHOLD = 0.7


class EmailStatusDetector:
    """Detects application status changes from email content."""

    def detect(self, subject: str, body: str) -> StatusDetection:
        """Analyze email subject and body for application status signals.

        Args:
            subject: Email subject line.
            body: Email body text (plain text preferred).

        Returns:
            StatusDetection with detected_status, confidence, and evidence.
        """
        text = f"{subject}\n{body}"

        if not text.strip():
            return StatusDetection(
                detected_status=None,
                confidence=0.0,
                evidence_snippet="",
                is_ambiguous=True,
            )

        best_match: StatusDetection | None = None

        for pattern, status, base_confidence in _ALL_PATTERNS:
            match = pattern.search(text)
            if match:
                snippet = self._extract_snippet(text, match)
                # Boost confidence if pattern matches in subject
                confidence = base_confidence
                if pattern.search(subject):
                    confidence = min(confidence + 0.05, 1.0)

                if best_match is None or confidence > best_match.confidence:
                    best_match = StatusDetection(
                        detected_status=status,
                        confidence=confidence,
                        evidence_snippet=snippet,
                        is_ambiguous=confidence < CONFIDENCE_THRESHOLD,
                    )

        if best_match is not None:
            return best_match

        # No patterns matched
        return StatusDetection(
            detected_status=None,
            confidence=0.0,
            evidence_snippet="",
            is_ambiguous=True,
        )

    async def detect_with_llm(self, subject: str, body: str) -> StatusDetection:
        """Use LLM to classify an email's application status.

        Called as fallback when regex detection is ambiguous.
        """
        import json

        text = f"Subject: {subject}\n\nBody: {body[:500]}"

        prompt = (
            "Classify this email into one of these application statuses: "
            "rejected, interview, offer, applied, screening. "
            "If the email is not about a job application status, respond with 'none'. "
            "Respond with JSON only: {\"status\": \"...\", \"confidence\": 0.0-1.0, \"evidence\": \"brief quote\"}\n\n"
            f"{text}"
        )

        try:
            from openai import AsyncOpenAI

            from app.config import settings

            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=100,
            )
            content = response.choices[0].message.content or ""
            data = json.loads(content)

            status = data.get("status", "none")
            if status == "none" or status not in (
                "rejected", "interview", "offer", "applied", "screening"
            ):
                return StatusDetection(
                    detected_status=None,
                    confidence=0.0,
                    evidence_snippet="",
                    is_ambiguous=True,
                    detection_method="llm",
                )

            confidence = float(data.get("confidence", 0.5))
            evidence = data.get("evidence", "")[:200]

            return StatusDetection(
                detected_status=status,
                confidence=confidence,
                evidence_snippet=evidence,
                is_ambiguous=confidence < CONFIDENCE_THRESHOLD,
                detection_method="llm",
            )
        except Exception as exc:
            logger.warning("LLM classification failed: %s", exc)
            return StatusDetection(
                detected_status=None,
                confidence=0.0,
                evidence_snippet="",
                is_ambiguous=True,
                detection_method="llm",
            )

    async def detect_enhanced(self, subject: str, body: str) -> StatusDetection:
        """Try regex detection first, fall back to LLM if ambiguous."""
        result = self.detect(subject, body)

        # If regex is confident, use it
        if not result.is_ambiguous and result.detected_status is not None:
            return result

        # If regex found nothing or was ambiguous, try LLM
        llm_result = await self.detect_with_llm(subject, body)

        # If LLM gives a confident result, prefer it
        if not llm_result.is_ambiguous and llm_result.detected_status is not None:
            return llm_result

        # If LLM also ambiguous but found something, prefer LLM if higher confidence
        if llm_result.detected_status is not None and (
            result.detected_status is None or llm_result.confidence > result.confidence
        ):
            return llm_result

        # Fall back to regex result (even if ambiguous)
        return result

    @staticmethod
    def _extract_snippet(text: str, match: re.Match) -> str:
        """Extract a ~100-char snippet centered on the match."""
        start = max(0, match.start() - 30)
        end = min(len(text), match.end() + 70)
        snippet = text[start:end].strip()
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        return snippet
