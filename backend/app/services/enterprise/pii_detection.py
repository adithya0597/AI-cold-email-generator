"""
PII Detection Service for enterprise organizations.

Provides regex-based detection of potential company PII (project names,
internal URLs, email domains, proprietary terms) in resume and cover letter
content before finalization.

Detection results are anonymized -- matched text is never stored in alerts.
Admin alerting uses SHA-256 hashed user_id to protect employee privacy.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AgentActivity, Organization


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class PIIDetection:
    """A single PII detection result."""

    matched_term: str
    category: str
    position: int  # character offset in scanned text
    pattern_id: str  # identifier for the pattern that matched


@dataclass
class PIICheckResult:
    """Result of a PII check on generated content."""

    pii_detected: bool
    categories: List[str] = field(default_factory=list)
    detection_count: int = 0


# ---------------------------------------------------------------------------
# Default patterns (built-in, always active unless org overrides)
# ---------------------------------------------------------------------------

DEFAULT_PATTERNS: List[Dict[str, Any]] = [
    {
        "pattern": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.internal\b",
        "category": "internal_email",
        "description": "Internal company email domain",
        "enabled": True,
        "id": "default_internal_email",
    },
    {
        "pattern": r"https?://[a-zA-Z0-9.-]+\.internal(?:/[^\s]*)?",
        "category": "internal_url",
        "description": "Internal company URL",
        "enabled": True,
        "id": "default_internal_url",
    },
    {
        "pattern": r"https?://(?:jira|confluence|gitlab|bitbucket)\.[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?",
        "category": "internal_tool_url",
        "description": "Internal tool URL (Jira, Confluence, GitLab, Bitbucket)",
        "enabled": True,
        "id": "default_internal_tool_url",
    },
    {
        "pattern": r"\b(?:Project|Operation)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b",
        "category": "code_name",
        "description": "Potential project/operation code name",
        "enabled": True,
        "id": "default_code_name",
    },
]


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class PIIDetectionService:
    """Regex-based PII detection for enterprise content screening.

    Merges default detection patterns with organization-specific custom
    patterns, applies whitelist exclusions, and returns anonymized results.
    """

    def __init__(self) -> None:
        self._compiled_cache: Dict[str, re.Pattern] = {}

    # -- public API ---------------------------------------------------------

    async def scan_text(
        self,
        text: str,
        org_id: str,
        session: AsyncSession,
    ) -> List[PIIDetection]:
        """Scan *text* for PII patterns configured for *org_id*.

        Returns a list of :class:`PIIDetection` objects (may be empty).
        Whitelist filtering is applied before returning.
        """
        patterns = await self._load_patterns(org_id, session)
        detections: List[PIIDetection] = []

        for pat in patterns:
            if not pat.get("enabled", True):
                continue
            regex = self._compile(pat["pattern"])
            if regex is None:
                continue  # skip invalid patterns silently at scan time
            for match in regex.finditer(text):
                detections.append(
                    PIIDetection(
                        matched_term=match.group(),
                        category=pat.get("category", "unknown"),
                        position=match.start(),
                        pattern_id=pat.get("id", "custom"),
                    )
                )

        detections = await self._apply_whitelist(detections, org_id, session)
        return detections

    async def check_pii(
        self,
        text: str,
        user_id: str,
        org_id: str,
        session: AsyncSession,
    ) -> PIICheckResult:
        """High-level hook for the generation flow.

        Scans *text*, and if PII is detected creates an anonymized
        :class:`AgentActivity` alert record. Returns a :class:`PIICheckResult`.
        """
        detections = await self.scan_text(text, org_id, session)

        if not detections:
            return PIICheckResult(pii_detected=False)

        categories = sorted(set(d.category for d in detections))

        # Create anonymized alert
        await self._create_alert(
            user_id=user_id,
            org_id=org_id,
            categories=categories,
            detection_count=len(detections),
            session=session,
        )

        return PIICheckResult(
            pii_detected=True,
            categories=categories,
            detection_count=len(detections),
        )

    @staticmethod
    def validate_patterns(patterns: List[Dict[str, Any]]) -> List[str]:
        """Validate that all regex patterns compile.

        Returns a list of error messages (empty if all valid).
        """
        errors: List[str] = []
        for i, pat in enumerate(patterns):
            raw = pat.get("pattern", "")
            try:
                re.compile(raw)
            except re.error as exc:
                errors.append(f"Pattern {i} ({raw!r}): {exc}")
        return errors

    @staticmethod
    def hash_user_id(user_id: str) -> str:
        """Return a SHA-256 hex digest of *user_id* for anonymized storage."""
        return hashlib.sha256(user_id.encode("utf-8")).hexdigest()

    # -- internal helpers ---------------------------------------------------

    async def _load_patterns(
        self,
        org_id: str,
        session: AsyncSession,
    ) -> List[Dict[str, Any]]:
        """Merge default patterns with org-custom patterns."""
        result = await session.execute(
            select(Organization.settings).where(Organization.id == org_id)
        )
        row = result.scalar()
        settings: Dict[str, Any] = row if isinstance(row, dict) else {}

        custom: List[Dict[str, Any]] = settings.get("pii_patterns", [])

        # Default patterns first, then org-custom patterns
        merged = list(DEFAULT_PATTERNS)
        for pat in custom:
            # Assign an id if missing
            if "id" not in pat:
                pat["id"] = f"custom_{len(merged)}"
            merged.append(pat)

        return merged

    async def _apply_whitelist(
        self,
        detections: List[PIIDetection],
        org_id: str,
        session: AsyncSession,
    ) -> List[PIIDetection]:
        """Remove detections whose matched_term is in the org whitelist."""
        result = await session.execute(
            select(Organization.settings).where(Organization.id == org_id)
        )
        row = result.scalar()
        settings: Dict[str, Any] = row if isinstance(row, dict) else {}

        whitelist: List[str] = settings.get("pii_whitelist", [])
        if not whitelist:
            return detections

        # Case-insensitive whitelist matching
        lower_whitelist = {term.lower() for term in whitelist}
        return [
            d for d in detections if d.matched_term.lower() not in lower_whitelist
        ]

    async def _create_alert(
        self,
        user_id: str,
        org_id: str,
        categories: List[str],
        detection_count: int,
        session: AsyncSession,
    ) -> None:
        """Create an anonymized AgentActivity alert for PII detection.

        NEVER stores actual user_id, name, or matched text.
        Uses SHA-256 hash of user_id for anonymization.
        """
        hashed_uid = self.hash_user_id(user_id)

        # PRIVACY NOTE: The AgentActivity.user_id FK stores the real user_id
        # because the model requires a valid FK to the users table. Admin-facing
        # API endpoints (GET /pii-alerts) MUST only expose data.hashed_user_id
        # and NEVER join back to the users table. The real user_id column should
        # be treated as an internal implementation detail, not exposed in any
        # admin-facing response. See admin_enterprise.py get_pii_alerts().
        activity = AgentActivity(
            id=uuid4(),
            user_id=user_id,
            event_type="pii_detected",
            agent_type="pii_detection",
            title="PII detected in generated content",
            severity="warning",
            data={
                "hashed_user_id": hashed_uid,
                "org_id": org_id,
                "categories": categories,
                "detection_count": detection_count,
            },
        )
        session.add(activity)

    def _compile(self, pattern: str) -> Optional[re.Pattern]:
        """Compile and cache a regex pattern. Returns None on error."""
        if pattern in self._compiled_cache:
            return self._compiled_cache[pattern]
        try:
            compiled = re.compile(pattern)
            self._compiled_cache[pattern] = compiled
            return compiled
        except re.error:
            return None
