"""
Job Scout Agent -- monitors job boards and creates scored matches.

Queries JSearch (primary) and Adzuna (secondary) APIs based on user
preferences, deduplicates and stores jobs, scores them against preferences,
filters deal-breakers, and creates Match records for qualifying jobs.

Architecture: Extends BaseAgent (ADR-1 custom orchestrator).
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from app.agents.base import AgentOutput, BaseAgent

logger = logging.getLogger(__name__)


class JobScoutAgent(BaseAgent):
    """Job Scout agent that discovers and scores job listings.

    Class attribute ``agent_type`` is used by BaseAgent for recording
    outputs, activities, and publishing WebSocket events.
    """

    agent_type = "job_scout"

    async def execute(self, user_id: str, task_data: dict) -> AgentOutput:
        """Execute the job scout workflow.

        1. Load user context (preferences, profile)
        2. Build search queries from preferences
        3. Fetch jobs from all configured sources
        4. Deduplicate and store in jobs table
        5. Score each job against preferences
        6. Filter deal-breaker violations
        7. Create Match records for qualifying jobs
        8. Return AgentOutput with summary

        Args:
            user_id: The user to scout jobs for.
            task_data: Optional overrides (e.g. specific query, location).

        Returns:
            AgentOutput with action summary and match statistics.
        """
        from app.agents.orchestrator import get_user_context

        # 1. Load user context
        context = await get_user_context(user_id)
        preferences = context.get("preferences") or {}
        profile = context.get("profile") or {}

        # 2. Build search queries
        queries = self._build_search_queries(preferences, task_data)
        if not queries:
            logger.info("No search queries for user=%s (no preferences set)", user_id)
            return AgentOutput(
                action="job_scout_complete",
                rationale="No target titles or search criteria configured",
                confidence=1.0,
                data={"jobs_found": 0, "matches_created": 0},
            )

        # 3. Fetch jobs from all sources
        raw_jobs = await self._fetch_jobs(queries, preferences)

        if not raw_jobs:
            return AgentOutput(
                action="job_scout_complete",
                rationale="No jobs found from any source",
                confidence=1.0,
                data={"jobs_found": 0, "matches_created": 0},
            )

        # 4. Deduplicate and store
        from app.db.engine import AsyncSessionLocal
        from app.services.job_dedup import upsert_jobs

        async with AsyncSessionLocal() as session:
            stored_jobs = await upsert_jobs(raw_jobs, session)

            # 5 & 6. Score and filter (heuristic pass)
            from app.config import settings

            heuristic_threshold = settings.MATCH_SCORE_THRESHOLD * 0.5  # pre-filter

            scored_jobs = []
            for job in stored_jobs:
                if self._check_deal_breakers(job, preferences):
                    continue  # Deal-breaker violated, skip
                score, rationale = self._score_job(job, preferences, profile)
                if score >= heuristic_threshold:
                    scored_jobs.append((job, score, rationale))

            # 5b. LLM refinement for jobs passing pre-filter
            if settings.LLM_SCORING_ENABLED and scored_jobs:
                from app.services.job_scoring import score_job_with_llm

                refined: list[tuple[Any, int, str]] = []
                for job, h_score, h_rationale in scored_jobs:
                    try:
                        result = await score_job_with_llm(
                            job, preferences, profile,
                            user_id=user_id,
                            heuristic_score=h_score,
                        )
                        if result.used_llm:
                            refined.append((job, result.score, result.rationale))
                        else:
                            refined.append((job, h_score, h_rationale))
                    except Exception as exc:
                        logger.warning(
                            "LLM scoring failed for job=%s: %s",
                            getattr(job, "id", "?"),
                            exc,
                        )
                        refined.append((job, h_score, h_rationale))
                scored_jobs = refined

            # 6b. Apply final threshold filter
            scored_jobs = [
                (job, score, rationale)
                for job, score, rationale in scored_jobs
                if score >= settings.MATCH_SCORE_THRESHOLD
            ]

            # 7. Create matches
            matches_created = await self._create_matches(
                user_id, scored_jobs, session
            )

            await session.commit()

        # 8. Return summary
        avg_score = (
            sum(s for _, s, _ in scored_jobs) / len(scored_jobs)
            if scored_jobs
            else 0
        )

        return AgentOutput(
            action="job_scout_complete",
            rationale=(
                f"Found {len(raw_jobs)} jobs, stored {len(stored_jobs)}, "
                f"created {matches_created} matches (avg score: {avg_score:.0f}%)"
            ),
            confidence=0.9,
            data={
                "jobs_found": len(raw_jobs),
                "jobs_stored": len(stored_jobs),
                "matches_created": matches_created,
                "average_score": round(avg_score, 1),
            },
        )

    # ------------------------------------------------------------------
    # Search query building
    # ------------------------------------------------------------------

    def _build_search_queries(
        self, preferences: dict, task_data: dict
    ) -> list[dict[str, Any]]:
        """Build search queries from user preferences.

        Returns a list of query dicts with 'query' and optional 'location' keys.
        """
        # Allow task_data to override
        if task_data.get("query"):
            return [{"query": task_data["query"], "location": task_data.get("location")}]

        target_titles = preferences.get("target_titles") or []
        target_locations = preferences.get("target_locations") or []

        if not target_titles:
            return []

        queries: list[dict[str, Any]] = []
        # Combine titles into a single query string (OR-style)
        title_query = " OR ".join(target_titles[:5])  # Cap at 5 titles

        if target_locations:
            for loc in target_locations[:3]:  # Cap at 3 locations
                queries.append({"query": title_query, "location": loc})
        else:
            queries.append({"query": title_query, "location": None})

        return queries

    # ------------------------------------------------------------------
    # Job fetching
    # ------------------------------------------------------------------

    async def _fetch_jobs(
        self, queries: list[dict[str, Any]], preferences: dict
    ) -> list[Any]:
        """Fetch jobs from all sources for all queries."""
        from app.config import settings
        from app.services.job_sources.aggregator import JobAggregator
        from app.services.job_sources.adzuna import AdzunaSource
        from app.services.job_sources.indeed import IndeedSource
        from app.services.job_sources.jsearch import JSearchSource
        from app.services.job_sources.linkedin import LinkedInSource

        sources = [JSearchSource(), AdzunaSource()]
        if settings.INDEED_RAPIDAPI_HOST:
            sources.append(IndeedSource())
        if settings.LINKEDIN_RAPIDAPI_HOST:
            sources.append(LinkedInSource())
        aggregator = JobAggregator(sources=sources)

        all_jobs = []
        filters: dict[str, Any] = {}
        if preferences.get("salary_minimum"):
            filters["salary_min"] = preferences["salary_minimum"]

        for q in queries:
            jobs = await aggregator.search_all(
                query=q["query"],
                location=q.get("location"),
                filters=filters,
            )
            all_jobs.extend(jobs)

        return all_jobs

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _score_job(
        self, job: Any, preferences: dict, profile: dict | None = None
    ) -> tuple[int, str]:
        """Score a job against user preferences.

        Scoring breakdown (raw 0-110, normalized to 0-100):
            - Title match: 0-25 pts
            - Location match: 0-20 pts
            - Salary match: 0-20 pts
            - Skills overlap: 0-20 pts
            - Seniority match: 0-15 pts
            - Company size: 0-10 pts

        Returns:
            Tuple of (total_score, rationale_string).
        """
        profile = profile or {}
        breakdown: dict[str, tuple[int, int]] = {}  # category -> (score, max)

        # Title match (0-25)
        title_score = self._score_title(job, preferences)
        breakdown["title"] = (title_score, 25)

        # Location match (0-20)
        location_score = self._score_location(job, preferences)
        breakdown["location"] = (location_score, 20)

        # Salary match (0-20)
        salary_score = self._score_salary(job, preferences)
        breakdown["salary"] = (salary_score, 20)

        # Skills overlap (0-20)
        skills_score = self._score_skills(job, profile)
        breakdown["skills"] = (skills_score, 20)

        # Seniority match (0-15)
        seniority_score = self._score_seniority(job, preferences)
        breakdown["seniority"] = (seniority_score, 15)

        # Company size (0-10)
        company_size_score = self._score_company_size(job, preferences)
        breakdown["company_size"] = (company_size_score, 10)

        raw_total = sum(s for s, _ in breakdown.values())
        # Normalize from 0-110 range to 0-100
        total = int(raw_total / 1.1)
        rationale = self._build_rationale(breakdown, total)
        return total, rationale

    def _score_title(self, job: Any, preferences: dict) -> int:
        """Score title match against target_titles (0-25)."""
        target_titles = preferences.get("target_titles") or []
        if not target_titles:
            return 12  # Neutral score if no preference

        job_title = (getattr(job, "title", "") or "").lower()
        for target in target_titles:
            target_lower = target.lower()
            if target_lower in job_title or job_title in target_lower:
                return 25  # Exact/substring match
            # Check word overlap
            target_words = set(target_lower.split())
            title_words = set(job_title.split())
            overlap = target_words & title_words
            if len(overlap) >= len(target_words) * 0.5:
                return 20  # Partial match

        return 5  # Low match

    def _score_location(self, job: Any, preferences: dict) -> int:
        """Score location match (0-20)."""
        target_locations = preferences.get("target_locations") or []
        work_arrangement = preferences.get("work_arrangement")
        job_remote = getattr(job, "remote", False)
        job_location = (getattr(job, "location", "") or "").lower()

        # Remote job + user wants remote = perfect match
        if job_remote and work_arrangement == "remote":
            return 20

        if not target_locations:
            return 10  # Neutral

        for loc in target_locations:
            if loc.lower() in job_location:
                return 20  # Location match

        # Remote job is always a partial match
        if job_remote:
            return 15

        return 0  # No location match

    def _score_salary(self, job: Any, preferences: dict) -> int:
        """Score salary match (0-20)."""
        salary_min_pref = preferences.get("salary_minimum")
        salary_target = preferences.get("salary_target")

        job_salary_min = getattr(job, "salary_min", None)
        job_salary_max = getattr(job, "salary_max", None)

        if not salary_min_pref and not salary_target:
            return 10  # Neutral if no preference

        if not job_salary_min and not job_salary_max:
            return 10  # Unknown salary, neutral

        # Use the best available salary figure
        job_salary = job_salary_max or job_salary_min or 0

        if salary_target and job_salary >= salary_target:
            return 20  # Meets or exceeds target
        elif salary_min_pref and job_salary >= salary_min_pref:
            # Between min and target
            if salary_target and salary_min_pref:
                ratio = (job_salary - salary_min_pref) / max(
                    salary_target - salary_min_pref, 1
                )
                return min(20, max(10, int(10 + ratio * 10)))
            return 15
        elif salary_min_pref and job_salary < salary_min_pref:
            return 0  # Below minimum

        return 10  # Neutral

    def _score_skills(self, job: Any, profile: dict) -> int:
        """Score skills overlap (0-20)."""
        user_skills = profile.get("skills") or []
        if not user_skills:
            return 10  # Neutral

        description = (getattr(job, "description", "") or "").lower()
        title = (getattr(job, "title", "") or "").lower()
        text = f"{title} {description}"

        if not text.strip():
            return 10  # Neutral

        matches = sum(1 for skill in user_skills if skill.lower() in text)
        if not user_skills:
            return 10

        ratio = matches / len(user_skills)
        return min(20, max(0, int(ratio * 20)))

    def _score_seniority(self, job: Any, preferences: dict) -> int:
        """Score seniority match (0-15)."""
        target_seniority = preferences.get("seniority_levels") or []
        if not target_seniority:
            return 8  # Neutral

        title = (getattr(job, "title", "") or "").lower()
        description = (getattr(job, "description", "") or "").lower()
        text = f"{title} {description}"

        seniority_keywords = {
            "junior": ["junior", "entry level", "entry-level", "associate", "jr."],
            "mid": ["mid-level", "mid level", "intermediate"],
            "senior": ["senior", "sr.", "lead", "principal"],
            "staff": ["staff", "principal", "distinguished"],
            "manager": ["manager", "director", "head of", "vp"],
        }

        for level in target_seniority:
            level_lower = level.lower()
            # Direct match
            if level_lower in text:
                return 15
            # Keyword match
            keywords = seniority_keywords.get(level_lower, [])
            if any(kw in text for kw in keywords):
                return 15

        return 3  # No match

    def _score_company_size(self, job: Any, preferences: dict) -> int:
        """Score company size preference match (0-10)."""
        min_company_size = preferences.get("min_company_size")
        if min_company_size is None:
            return 5  # No preference, neutral

        # Extract company size from raw_data (various API key names)
        raw_data = getattr(job, "raw_data", None) or {}
        company_size = None
        for key in ("companySize", "company_size", "employerSize", "employer_size"):
            val = raw_data.get(key)
            if val is not None:
                try:
                    company_size = int(val)
                except (ValueError, TypeError):
                    continue
                break

        if company_size is None:
            return 5  # Unknown company size, neutral

        if company_size >= min_company_size:
            return 10
        return 0

    # ------------------------------------------------------------------
    # Deal-breaker checking
    # ------------------------------------------------------------------

    def _check_deal_breakers(self, job: Any, preferences: dict) -> bool:
        """Check if any deal-breaker is violated.

        Returns True if a deal-breaker IS violated (job should be excluded).
        """
        # Excluded companies
        excluded_companies = preferences.get("excluded_companies") or []
        job_company = (getattr(job, "company", "") or "").lower()
        for exc_company in excluded_companies:
            if exc_company.lower() in job_company:
                logger.debug(
                    "Deal-breaker: excluded company '%s' for job '%s'",
                    exc_company,
                    getattr(job, "title", ""),
                )
                return True

        # Excluded industries
        excluded_industries = preferences.get("excluded_industries") or []
        description = (getattr(job, "description", "") or "").lower()
        title = (getattr(job, "title", "") or "").lower()
        text = f"{title} {description}"
        for industry in excluded_industries:
            if industry.lower() in text:
                logger.debug(
                    "Deal-breaker: excluded industry '%s' for job '%s'",
                    industry,
                    getattr(job, "title", ""),
                )
                return True

        # Salary below minimum
        salary_min_pref = preferences.get("salary_minimum")
        if salary_min_pref:
            job_salary_max = getattr(job, "salary_max", None)
            job_salary_min = getattr(job, "salary_min", None)
            # Only reject if salary is known AND below minimum
            best_salary = job_salary_max or job_salary_min
            if best_salary and best_salary < salary_min_pref:
                logger.debug(
                    "Deal-breaker: salary %d below minimum %d for job '%s'",
                    best_salary,
                    salary_min_pref,
                    getattr(job, "title", ""),
                )
                return True

        return False

    # ------------------------------------------------------------------
    # Rationale building
    # ------------------------------------------------------------------

    def _build_rationale(
        self, breakdown: dict[str, tuple[int, int]], normalized_total: int | None = None
    ) -> str:
        """Build a human-readable rationale string from score breakdown.

        Example: "78% match: title (20/25), location (20/20), salary (18/20),
                  skills (10/20), seniority (10/15), company_size (5/10)"
        """
        if normalized_total is None:
            raw = sum(s for s, _ in breakdown.values())
            normalized_total = int(raw / 1.1)
        parts = [f"{cat} ({s}/{m})" for cat, (s, m) in breakdown.items()]
        return f"{normalized_total}% match: {', '.join(parts)}"

    # ------------------------------------------------------------------
    # Match creation
    # ------------------------------------------------------------------

    async def _create_matches(
        self,
        user_id: str,
        scored_jobs: list[tuple[Any, int, str]],
        session: Any,
    ) -> int:
        """Create Match records for scored jobs, skipping existing matches.

        Checks for existing (user_id, job_id) pairs before inserting to
        prevent duplicate matches on repeated agent runs.

        Args:
            user_id: User ID for the matches.
            scored_jobs: List of (job, score, rationale) tuples.
            session: AsyncSession for database operations.

        Returns:
            Number of new matches created.
        """
        from sqlalchemy import select

        from app.db.models import Match

        if not scored_jobs:
            return 0

        # Fetch existing matches for this user to avoid duplicates
        job_ids = [job.id for job, _, _ in scored_jobs]
        result = await session.execute(
            select(Match.job_id).where(
                Match.user_id == user_id,
                Match.job_id.in_(job_ids),
            )
        )
        existing_job_ids = {row[0] for row in result.all()}

        count = 0
        for job, score, rationale in scored_jobs:
            if job.id in existing_job_ids:
                logger.debug(
                    "Skipping existing match for user=%s job=%s", user_id, job.id
                )
                continue
            match = Match(
                id=uuid4(),
                user_id=user_id,
                job_id=job.id,
                score=score,
                rationale=rationale,
                status="new",
            )
            session.add(match)
            count += 1

        await session.flush()
        logger.info("Created %d new matches for user=%s (skipped %d existing)",
                     count, user_id, len(existing_job_ids))
        return count
