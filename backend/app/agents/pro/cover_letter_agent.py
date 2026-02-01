"""
Cover Letter Agent -- generates tailored cover letters for specific jobs.

Given a user's profile data and a target job, produces a personalized
cover letter optimized for the role.  Stores the result in the
``documents`` table with type=COVER_LETTER and a job_id reference.

Architecture: Extends BaseAgent (ADR-1 custom orchestrator).
CRITICAL: NEVER fabricates qualifications not present in the user's profile.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel

from app.agents.base import AgentOutput, BaseAgent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic models for LLM structured output
# ---------------------------------------------------------------------------


class CoverLetterContent(BaseModel):
    """Structured cover letter output from the LLM."""

    opening: str
    body_paragraphs: list[str]
    closing: str
    word_count: int
    personalization_sources: list[str]


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a professional cover letter writer. Given a user's profile data \
and a target job description, write a personalized cover letter for this \
specific role.

RULES:
1. You must ONLY reference experience, skills, and qualifications present \
in the user's profile. NEVER invent, fabricate, or embellish qualifications.
2. The cover letter MUST be 250-400 words total (opening + body + closing).
3. The opening paragraph must reference something specific about the \
company or role — their mission, recent news mentioned in the description, \
or specific aspects of the position.
4. Body paragraphs must connect the user's specific experience and skills \
to the job requirements. Use concrete examples from their profile.
5. The closing must include a professional call to action.
6. Tone: confident, professional, and authentic — not generic or robotic.
7. Return the word_count of the full letter (opening + body + closing).
8. List personalization_sources: what specific details you referenced \
(e.g., "company mission from description", "specific role requirement").
"""


# ---------------------------------------------------------------------------
# CoverLetterAgent
# ---------------------------------------------------------------------------


class CoverLetterAgent(BaseAgent):
    """Cover letter generation agent.

    Class attribute ``agent_type`` identifies this agent for routing & logging.
    """

    agent_type = "cover_letter"

    async def execute(self, user_id: str, task_data: dict) -> AgentOutput:
        """Execute the cover letter generation workflow.

        1. Load user context (profile)
        2. Load target job from database
        3. Generate cover letter via LLM
        4. Store as Document(type='cover_letter', job_id=...)
        5. Return AgentOutput

        Args:
            user_id: Clerk user ID.
            task_data: Must contain ``job_id`` (UUID string).

        Returns:
            AgentOutput with cover letter content and document_id.
        """
        from app.agents.orchestrator import get_user_context

        job_id = task_data.get("job_id")
        if not job_id:
            return AgentOutput(
                action="cover_letter_failed",
                rationale="No job_id provided in task_data",
                confidence=1.0,
                data={"error": "missing_job_id"},
            )

        # 1. Load user context
        context = await get_user_context(user_id)
        profile = context.get("profile") or {}

        if not profile.get("skills") and not profile.get("experience"):
            return AgentOutput(
                action="cover_letter_failed",
                rationale="User has no profile data to generate from",
                confidence=1.0,
                data={"error": "empty_profile"},
            )

        # 2. Load job details
        job = await self._load_job(job_id)
        if not job:
            return AgentOutput(
                action="cover_letter_failed",
                rationale=f"Job {job_id} not found",
                confidence=1.0,
                data={"error": "job_not_found"},
            )

        # 3. Generate cover letter via LLM
        try:
            cover_letter = await self._generate_cover_letter(profile, job)
        except Exception as exc:
            logger.error(
                "LLM cover letter generation failed for user=%s job=%s: %s",
                user_id, job_id, exc,
            )
            return AgentOutput(
                action="cover_letter_failed",
                rationale=f"LLM generation error: {exc}",
                confidence=0.0,
                data={"error": "llm_failure"},
            )

        # 4. Store document
        document_id = await self._store_document(user_id, job_id, cover_letter)

        # 5. Build output
        return AgentOutput(
            action="cover_letter_generated",
            rationale=(
                f"Generated {cover_letter.word_count}-word cover letter for "
                f"{job.get('title', 'unknown')} at {job.get('company', 'unknown')}"
            ),
            confidence=0.9,
            data={
                "document_id": document_id,
                "job_id": job_id,
                "word_count": cover_letter.word_count,
                "personalization_sources": cover_letter.personalization_sources,
            },
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _load_job(self, job_id: str) -> dict[str, Any] | None:
        """Load job details from the database."""
        from sqlalchemy import text

        from app.db.engine import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text(
                    "SELECT id, title, company, description, location, "
                    "salary_min, salary_max, employment_type, remote "
                    "FROM jobs WHERE id = :jid"
                ),
                {"jid": job_id},
            )
            row = result.mappings().first()
            return dict(row) if row else None

    async def _generate_cover_letter(
        self, profile: dict[str, Any], job: dict[str, Any]
    ) -> CoverLetterContent:
        """Call the LLM to produce a cover letter."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI()

        user_message = self._build_prompt(profile, job)

        completion = await client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_format=CoverLetterContent,
        )

        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise ValueError("LLM returned no parsed content")

        # Track cost
        try:
            from app.observability.cost_tracker import track_llm_cost

            usage = completion.usage
            if usage:
                await track_llm_cost(
                    user_id="system",
                    model="gpt-4o-mini",
                    input_tokens=usage.prompt_tokens,
                    output_tokens=usage.completion_tokens,
                    agent_type="cover_letter",
                )
        except Exception as exc:
            logger.debug("Cost tracking failed: %s", exc)

        return parsed

    def _build_prompt(
        self, profile: dict[str, Any], job: dict[str, Any]
    ) -> str:
        """Build the user-facing prompt for cover letter generation."""
        sections = []

        sections.append("## TARGET JOB")
        sections.append(f"Title: {job.get('title', '')}")
        sections.append(f"Company: {job.get('company', '')}")
        sections.append(f"Location: {job.get('location', '')}")
        sections.append(f"Description:\n{(job.get('description') or '')[:3000]}")

        sections.append("\n## USER'S PROFILE DATA")

        if profile.get("headline"):
            sections.append(f"Headline: {profile['headline']}")

        if profile.get("skills"):
            skills = profile["skills"]
            if isinstance(skills, list):
                sections.append(f"Skills: {', '.join(skills)}")
            else:
                sections.append(f"Skills: {skills}")

        if profile.get("experience"):
            sections.append("\nExperience:")
            exp = profile["experience"]
            if isinstance(exp, list):
                for item in exp:
                    if isinstance(item, dict):
                        sections.append(
                            f"- {item.get('title', '')} at {item.get('company', '')} "
                            f"({item.get('start_date', '')} - {item.get('end_date', 'Present')})"
                        )
                        if item.get("description"):
                            sections.append(f"  {item['description']}")
                    else:
                        sections.append(f"- {item}")

        if profile.get("education"):
            sections.append("\nEducation:")
            edu = profile["education"]
            if isinstance(edu, list):
                for item in edu:
                    if isinstance(item, dict):
                        sections.append(
                            f"- {item.get('degree', '')} in {item.get('field', '')} "
                            f"from {item.get('institution', '')} ({item.get('graduation_year', '')})"
                        )
                    else:
                        sections.append(f"- {item}")

        sections.append(
            "\nWrite a personalized cover letter for this specific job. "
            "The letter must be 250-400 words."
        )

        return "\n".join(sections)

    async def _store_document(
        self, user_id: str, job_id: str, cover_letter: CoverLetterContent
    ) -> str:
        """Store the cover letter as a Document record.

        Auto-increments version for the same user+job combo.
        Returns the new document ID as a string.
        """
        from uuid import uuid4

        from sqlalchemy import text

        from app.db.engine import AsyncSessionLocal

        content = json.dumps(cover_letter.model_dump())

        async with AsyncSessionLocal() as session:
            # Get next version number
            result = await session.execute(
                text(
                    "SELECT COALESCE(MAX(version), 0) + 1 "
                    "FROM documents "
                    "WHERE user_id = (SELECT id FROM users WHERE clerk_id = :uid) "
                    "AND job_id = :jid "
                    "AND type = 'cover_letter'"
                ),
                {"uid": user_id, "jid": job_id},
            )
            next_version = result.scalar()

            doc_id = str(uuid4())

            await session.execute(
                text(
                    "INSERT INTO documents (id, user_id, type, version, content, job_id, schema_version) "
                    "VALUES (:id, (SELECT id FROM users WHERE clerk_id = :uid), "
                    "'cover_letter', :ver, :content, :jid, 1)"
                ),
                {
                    "id": doc_id,
                    "uid": user_id,
                    "jid": job_id,
                    "ver": next_version,
                    "content": content,
                },
            )
            await session.commit()

        return doc_id
