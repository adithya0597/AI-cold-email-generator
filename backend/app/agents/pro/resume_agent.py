"""
Resume Agent -- tailors resumes for specific jobs.

Given a user's master resume (structured profile data) and a target job,
produces a tailored resume optimized for the role.  Stores the result in
the ``documents`` table with type=RESUME and a job_id reference.

Architecture: Extends BaseAgent (ADR-1 custom orchestrator).
CRITICAL: NEVER fabricates qualifications not present in the master resume.
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


class TailoredSection(BaseModel):
    """A single resume section that has been tailored."""

    section_name: str
    original_content: str
    tailored_content: str
    changes_made: list[str]


class TailoredResume(BaseModel):
    """Full tailored resume output from the LLM."""

    sections: list[TailoredSection]
    keywords_incorporated: list[str]
    keywords_missing: list[str]
    ats_score: int
    tailoring_rationale: str


# ---------------------------------------------------------------------------
# System prompt — anti-hallucination mandate
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a professional resume tailoring assistant. Given a user's master \
resume data and a target job description, optimize the resume for this \
specific role.

RULES:
1. You must ONLY use experience, skills, and qualifications present in the \
user's master resume. NEVER invent, fabricate, or embellish qualifications.
2. Reorder and emphasize existing experience that is most relevant to the \
target role.
3. Rephrase bullet points to mirror the job description's language and \
keywords.
4. Add relevant skills from the user's skill set that match the job \
requirements.
5. Optimize the professional summary to align with the target role.
6. Return an ATS score (0-100) based on keyword match percentage.
7. List keywords you incorporated and keywords still missing.
"""


# ---------------------------------------------------------------------------
# ResumeAgent
# ---------------------------------------------------------------------------


class ResumeAgent(BaseAgent):
    """Resume tailoring agent.

    Class attribute ``agent_type`` matches ``AgentType.RESUME`` enum value.
    """

    agent_type = "resume"

    async def execute(self, user_id: str, task_data: dict) -> AgentOutput:
        """Execute the resume tailoring workflow.

        1. Load user context (profile with skills, experience, education)
        2. Load target job from database
        3. Analyze job requirements
        4. Tailor resume via LLM
        5. Calculate keyword gaps
        6. Store tailored document
        7. Return AgentOutput with rationale and stats

        Args:
            user_id: Clerk user ID.
            task_data: Must contain ``job_id`` (UUID string).

        Returns:
            AgentOutput with tailoring summary.
        """
        from app.agents.orchestrator import get_user_context

        job_id = task_data.get("job_id")
        if not job_id:
            return AgentOutput(
                action="resume_tailoring_failed",
                rationale="No job_id provided in task_data",
                confidence=1.0,
                data={"error": "missing_job_id"},
            )

        # 1. Load user context
        context = await get_user_context(user_id)
        profile = context.get("profile") or {}

        if not profile.get("skills") and not profile.get("experience"):
            return AgentOutput(
                action="resume_tailoring_failed",
                rationale="User has no profile data to tailor from",
                confidence=1.0,
                data={"error": "empty_profile"},
            )

        # 2. Load job details
        job = await self._load_job(job_id)
        if not job:
            return AgentOutput(
                action="resume_tailoring_failed",
                rationale=f"Job {job_id} not found",
                confidence=1.0,
                data={"error": "job_not_found"},
            )

        # 3. Analyze job requirements
        job_analysis = self._analyze_job(job)

        # 4. Tailor resume via LLM
        try:
            tailored = await self._tailor_resume(profile, job_analysis)
        except Exception as exc:
            logger.error("LLM tailoring failed for user=%s job=%s: %s", user_id, job_id, exc)
            return AgentOutput(
                action="resume_tailoring_failed",
                rationale=f"LLM tailoring error: {exc}",
                confidence=0.0,
                data={"error": "llm_failure"},
            )

        # 5. Calculate keyword gaps
        keyword_gaps = self._calculate_keyword_gaps(job_analysis, tailored)

        # 6. Store tailored document
        document_id = await self._store_document(user_id, job_id, tailored)

        # 7. Build output
        sections_modified = [s.section_name for s in tailored.sections if s.changes_made]

        return AgentOutput(
            action="resume_tailored",
            rationale=tailored.tailoring_rationale,
            confidence=min(tailored.ats_score / 100.0, 1.0),
            data={
                "document_id": str(document_id),
                "job_id": job_id,
                "ats_score": tailored.ats_score,
                "sections_modified": sections_modified,
                "keyword_gaps": keyword_gaps,
                "keywords_incorporated": tailored.keywords_incorporated,
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

    def _analyze_job(self, job: dict[str, Any]) -> dict[str, Any]:
        """Extract structured requirements from a job listing."""
        description = job.get("description") or ""
        title = job.get("title") or ""

        # Extract keywords from description (simple word frequency approach)
        words = description.lower().split()
        # Filter common words, keep meaningful terms
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "from", "is", "are", "was", "were",
            "be", "been", "being", "have", "has", "had", "do", "does", "did",
            "will", "would", "could", "should", "may", "might", "must",
            "shall", "can", "need", "we", "you", "they", "it", "he", "she",
            "this", "that", "these", "those", "our", "your", "their", "its",
            "not", "no", "as", "if", "so", "up", "out", "about", "into",
            "through", "during", "before", "after", "above", "below",
            "between", "under", "over", "all", "each", "every", "both",
            "few", "more", "most", "other", "some", "such", "than", "too",
            "very", "just", "also", "now", "here", "there", "when", "where",
            "how", "what", "which", "who", "whom", "why", "while",
        }
        keywords = [w.strip(".,;:!?()[]{}\"'") for w in words if len(w) > 2]
        keywords = [w for w in keywords if w and w not in stop_words]

        # Count frequency, take top keywords
        freq: dict[str, int] = {}
        for kw in keywords:
            freq[kw] = freq.get(kw, 0) + 1
        sorted_kw = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        top_keywords = [kw for kw, _ in sorted_kw[:30]]

        return {
            "title": title,
            "company": job.get("company") or "",
            "description": description,
            "location": job.get("location") or "",
            "keywords": top_keywords,
        }

    async def _tailor_resume(
        self, profile: dict[str, Any], job_analysis: dict[str, Any]
    ) -> TailoredResume:
        """Call the LLM to produce a tailored resume."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI()

        # Build user message with profile and job context
        user_message = self._build_tailoring_prompt(profile, job_analysis)

        completion = await client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_format=TailoredResume,
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
                    agent_type="resume",
                )
        except Exception as exc:
            logger.debug("Cost tracking failed: %s", exc)

        return parsed

    def _build_tailoring_prompt(
        self, profile: dict[str, Any], job_analysis: dict[str, Any]
    ) -> str:
        """Build the user-facing prompt for resume tailoring."""
        sections = []

        sections.append("## TARGET JOB")
        sections.append(f"Title: {job_analysis['title']}")
        sections.append(f"Company: {job_analysis['company']}")
        sections.append(f"Description:\n{job_analysis['description'][:3000]}")

        sections.append("\n## USER'S MASTER RESUME DATA")

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
            "\nPlease tailor the resume sections for this specific job. "
            "Return each section with original and tailored content."
        )

        return "\n".join(sections)

    def _calculate_keyword_gaps(
        self, job_analysis: dict[str, Any], tailored: TailoredResume
    ) -> dict[str, Any]:
        """Compare job keywords with tailored resume content."""
        job_keywords = set(job_analysis.get("keywords", []))

        # Gather all text from tailored sections
        tailored_text = " ".join(
            s.tailored_content.lower() for s in tailored.sections
        )

        matched = []
        missing = []
        for kw in job_keywords:
            if kw in tailored_text:
                matched.append(kw)
            else:
                missing.append(kw)

        return {
            "matched": matched,
            "missing": missing,
            "match_rate": len(matched) / max(len(job_keywords), 1),
        }

    async def _store_document(
        self, user_id: str, job_id: str, tailored: TailoredResume
    ) -> str:
        """Store the tailored resume as a Document record.

        Auto-increments version for the same user+job combo.
        Returns the new document ID as a string.
        """
        from uuid import uuid4

        from sqlalchemy import text

        from app.db.engine import AsyncSessionLocal

        content = json.dumps(
            {
                "sections": [s.model_dump() for s in tailored.sections],
                "ats_score": tailored.ats_score,
                "keywords_incorporated": tailored.keywords_incorporated,
                "keywords_missing": tailored.keywords_missing,
                "tailoring_rationale": tailored.tailoring_rationale,
            }
        )

        async with AsyncSessionLocal() as session:
            # Get next version number
            result = await session.execute(
                text(
                    "SELECT COALESCE(MAX(version), 0) + 1 "
                    "FROM documents "
                    "WHERE user_id = (SELECT id FROM users WHERE clerk_id = :uid) "
                    "AND job_id = :jid "
                    "AND type = 'resume'"
                ),
                {"uid": user_id, "jid": job_id},
            )
            next_version = result.scalar()

            doc_id = str(uuid4())

            await session.execute(
                text(
                    "INSERT INTO documents (id, user_id, type, version, content, job_id, schema_version) "
                    "VALUES (:id, (SELECT id FROM users WHERE clerk_id = :uid), "
                    "'resume', :ver, :content, :jid, 1)"
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
