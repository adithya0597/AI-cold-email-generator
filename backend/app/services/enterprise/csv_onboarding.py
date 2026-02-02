"""CSV-based bulk employee onboarding service.

Parses and validates CSV files containing employee email lists for
bulk organization onboarding. Handles email format validation,
duplicate detection, and existing account checks.
"""

from __future__ import annotations

import codecs
import csv
import io
import re
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OrganizationMember, User

# Simplified RFC 5322 email pattern
_EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9]"
    r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
)

MAX_BATCH_SIZE = 1000

REQUIRED_HEADERS = {"email"}
OPTIONAL_HEADERS = {"first_name", "last_name", "department"}
ALL_HEADERS = REQUIRED_HEADERS | OPTIONAL_HEADERS


@dataclass
class RowError:
    """A single validation error for a CSV row."""

    row_number: int
    email: str
    error_reason: str


@dataclass
class ValidationResult:
    """Result of validating parsed CSV rows."""

    valid_rows: list[dict] = field(default_factory=list)
    invalid_rows: list[RowError] = field(default_factory=list)


class CSVOnboardingService:
    """Service for parsing and validating employee CSV uploads."""

    def parse_csv(self, file_content: bytes) -> list[dict]:
        """Parse a CSV file and extract employee rows.

        Args:
            file_content: Raw bytes of the uploaded CSV file.

        Returns:
            List of dicts with keys matching CSV headers.

        Raises:
            ValueError: If CSV exceeds MAX_BATCH_SIZE or missing required headers.
        """
        # Handle UTF-8 BOM
        if file_content.startswith(codecs.BOM_UTF8):
            file_content = file_content[len(codecs.BOM_UTF8) :]

        text = file_content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))

        if reader.fieldnames is None:
            raise ValueError("CSV file is empty or has no headers")

        # Normalize header names
        headers = {h.strip().lower() for h in reader.fieldnames}
        if not REQUIRED_HEADERS.issubset(headers):
            missing = REQUIRED_HEADERS - headers
            raise ValueError(f"Missing required CSV headers: {', '.join(missing)}")

        rows = []
        for i, row in enumerate(reader, start=2):  # Row 1 is header
            if i - 1 > MAX_BATCH_SIZE:
                raise ValueError(
                    f"CSV exceeds maximum batch size of {MAX_BATCH_SIZE} rows"
                )
            # Normalize keys and strip values
            normalized = {
                k.strip().lower(): (v.strip() if v else "")
                for k, v in row.items()
                if k and k.strip().lower() in ALL_HEADERS
            }
            rows.append(normalized)

        return rows

    async def validate_rows(
        self,
        rows: list[dict],
        org_id: str,
        session: AsyncSession,
    ) -> ValidationResult:
        """Validate parsed CSV rows against business rules.

        Args:
            rows: Parsed CSV rows from parse_csv().
            org_id: The organization UUID string.
            session: Active async DB session.

        Returns:
            ValidationResult with valid and invalid rows.
        """
        result = ValidationResult()
        seen_emails: dict[str, int] = {}

        # Collect all emails for batch DB lookup
        all_emails = [r.get("email", "").lower() for r in rows]

        # Batch query: find existing users by email
        existing_users_result = await session.execute(
            select(User.id, User.email).where(User.email.in_(all_emails))
        )
        existing_users = {row.email.lower(): row.id for row in existing_users_result}

        # Batch query: find org members by user_id
        if existing_users:
            org_members_result = await session.execute(
                select(OrganizationMember.user_id).where(
                    OrganizationMember.org_id == UUID(org_id),
                    OrganizationMember.user_id.in_(list(existing_users.values())),
                )
            )
            org_member_ids = {row.user_id for row in org_members_result}
        else:
            org_member_ids = set()

        for i, row in enumerate(rows, start=2):  # Row 1 is header
            email = row.get("email", "").lower()

            # Email format validation
            if not email or not _EMAIL_PATTERN.match(email):
                result.invalid_rows.append(
                    RowError(row_number=i, email=email, error_reason="invalid_email_format")
                )
                continue

            # Duplicate detection within CSV
            if email in seen_emails:
                result.invalid_rows.append(
                    RowError(row_number=i, email=email, error_reason="duplicate_in_upload")
                )
                continue
            seen_emails[email] = i

            # Existing account detection
            if email in existing_users:
                user_id = existing_users[email]
                if user_id in org_member_ids:
                    result.invalid_rows.append(
                        RowError(
                            row_number=i,
                            email=email,
                            error_reason="already_in_org",
                        )
                    )
                else:
                    result.invalid_rows.append(
                        RowError(
                            row_number=i,
                            email=email,
                            error_reason="existing_account_different_org",
                        )
                    )
                continue

            result.valid_rows.append(row)

        return result
