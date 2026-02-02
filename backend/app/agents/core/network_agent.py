"""
Network Agent — helps users build professional relationships strategically.

Analyzes target companies, finds warm paths through existing connections,
identifies engagement opportunities, and generates introduction request
drafts. All outputs are suggestions/drafts for manual user execution —
the agent NEVER automates LinkedIn actions or direct messaging (legal risk).

All direct outreach requires human approval regardless of autonomy level.

Architecture: Extends BaseAgent (ADR-1 custom orchestrator).
"""

from __future__ import annotations

import logging
from typing import Any

from app.agents.base import AgentOutput, BaseAgent

logger = logging.getLogger(__name__)


class NetworkAgent(BaseAgent):
    """Network agent that helps users build professional relationships.

    Class attribute ``agent_type`` is used by BaseAgent for recording
    outputs, activities, and publishing WebSocket events.
    """

    agent_type = "network"

    async def execute(self, user_id: str, task_data: dict) -> AgentOutput:
        """Execute the network analysis workflow.

        Expected task_data keys:
            - target_companies (list[str], required): Companies to analyze.
            - connection_data (dict, optional): User's network info (imported connections).
            - user_profile (dict, optional): User profile for personalization.

        Returns:
            AgentOutput with network analysis in data.
        """
        target_companies = task_data.get("target_companies") or []
        connection_data = task_data.get("connection_data") or {}
        user_profile = task_data.get("user_profile") or {}

        if not target_companies:
            return AgentOutput(
                action="network_analysis_complete",
                rationale="No target companies provided — returning guidance",
                confidence=0.5,
                data={
                    "guidance": (
                        "Save jobs or add target companies to start "
                        "building warm paths to your network."
                    ),
                    "warm_paths": [],
                    "opportunities": [],
                    "intro_drafts": [],
                },
            )

        # Step 1: Warm path analysis
        warm_paths = await self._analyze_warm_paths(
            target_companies, connection_data
        )

        # Step 2: Relationship opportunity identification
        contacts = []
        for wp in warm_paths:
            if isinstance(wp, dict):
                contacts.append({
                    "name": wp.get("contact_name", ""),
                    "company": wp.get("company", ""),
                })
        opportunities = await self._identify_opportunities(
            contacts, user_profile
        )

        # Step 3: Introduction request draft generation
        intro_drafts = await self._generate_intro_drafts(
            warm_paths, user_profile
        )

        # Step 4: Queue drafts for approval (9-6)
        await self._queue_drafts_for_approval(user_id, intro_drafts, warm_paths)

        # Assemble network analysis with temperature scores (9-5)
        analysis = self._assemble_network_analysis(
            warm_paths=warm_paths,
            opportunities=opportunities,
            intro_drafts=intro_drafts,
            target_companies=target_companies,
        )

        # Compute confidence based on data completeness
        confidence = self._compute_confidence(
            warm_paths, opportunities, intro_drafts
        )

        # Any intro drafts require human approval
        has_drafts = len(intro_drafts) > 0

        return AgentOutput(
            action="network_analysis_complete",
            rationale=(
                f"Network analysis for {len(target_companies)} target "
                f"companies — {len(warm_paths)} warm paths found, "
                f"{len(intro_drafts)} intro drafts generated"
            ),
            confidence=confidence,
            data=analysis,
            requires_approval=has_drafts,
        )

    # ------------------------------------------------------------------
    # Analysis sub-steps (real implementations via services)
    # ------------------------------------------------------------------

    async def _analyze_warm_paths(
        self,
        target_companies: list[str],
        connection_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Analyze warm paths to target companies via user connections.

        Delegates to WarmPathService (story 9-2).
        """
        from app.services.network.warm_path import WarmPathService

        logger.info(
            "Analyzing warm paths for %d companies", len(target_companies)
        )
        service = WarmPathService()
        paths = await service.analyze(target_companies, connection_data)
        return [p.to_dict() for p in paths]

    async def _identify_opportunities(
        self,
        contacts: list[dict[str, Any]],
        user_profile: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Identify engagement opportunities with target contacts.

        Delegates to EngagementTrackingService (story 9-4).
        """
        from app.services.network.engagement_tracking import (
            EngagementTrackingService,
        )

        logger.info(
            "Identifying opportunities for %d contacts",
            len(contacts),
        )
        service = EngagementTrackingService()
        opportunities = await service.find_opportunities(contacts, user_profile)
        return [o.to_dict() for o in opportunities]

    async def _generate_intro_drafts(
        self,
        warm_paths: list[dict[str, Any]],
        user_profile: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Generate introduction request message drafts for warm paths.

        Delegates to IntroDraftService (story 9-3).
        """
        from app.services.network.intro_drafts import IntroDraftService

        logger.info(
            "Generating intro drafts for %d warm paths", len(warm_paths)
        )
        service = IntroDraftService()
        drafts = await service.generate(warm_paths, user_profile)
        return [d.to_dict() for d in drafts]

    async def _queue_drafts_for_approval(
        self,
        user_id: str,
        intro_drafts: list[dict[str, Any]],
        warm_paths: list[dict[str, Any]],
    ) -> int:
        """Queue each intro draft for human approval (story 9-6).

        Hard constraint: NEVER send messages without approval.

        Returns:
            Number of drafts successfully queued.
        """
        if not intro_drafts:
            return 0

        from app.services.network.approval import NetworkApprovalService

        service = NetworkApprovalService()
        # Build a lookup for context from warm paths
        path_lookup: dict[str, dict[str, Any]] = {}
        for wp in warm_paths:
            name = wp.get("contact_name", "")
            if name:
                path_lookup[name] = wp

        queued = 0
        for draft in intro_drafts:
            try:
                recipient = draft.get("recipient_name", "")
                context = path_lookup.get(recipient, {})
                await service.queue_outreach(user_id, draft, context)
                queued += 1
            except Exception as exc:
                logger.warning(
                    "Failed to queue draft for approval: %s", exc
                )
        return queued

    # ------------------------------------------------------------------
    # Analysis assembly (enriched with temperature scores — 9-5)
    # ------------------------------------------------------------------

    def _assemble_network_analysis(
        self,
        warm_paths: list[dict[str, Any]],
        opportunities: list[dict[str, Any]],
        intro_drafts: list[dict[str, Any]],
        target_companies: list[str],
    ) -> dict[str, Any]:
        """Merge all analysis sub-step outputs into a single dict."""
        from app.services.network.temperature_scoring import (
            RelationshipTemperatureService,
        )

        # Compute temperature scores from warm path data (9-5)
        temp_service = RelationshipTemperatureService()
        engagement_records = []
        for wp in warm_paths:
            # Use warm path data as proxy engagement records
            engagement_records.append({
                "contact_name": wp.get("contact_name", ""),
                "engagement_type": "connection",
                "timestamp": "",
                "temperature_impact": 0.0,
            })
        temperature_scores = [
            ts.to_dict() for ts in temp_service.score_contacts(engagement_records)
        ]

        # Identify contacts ready for outreach
        ready_contacts = [
            ts for ts in temperature_scores if ts.get("ready_for_outreach")
        ]

        return {
            "target_companies": target_companies,
            "warm_paths": warm_paths,
            "opportunities": opportunities,
            "intro_drafts": intro_drafts,
            "temperature_scores": temperature_scores,
            "ready_for_outreach": ready_contacts,
            "summary": {
                "companies_analyzed": len(target_companies),
                "total_warm_paths": len(warm_paths),
                "total_opportunities": len(opportunities),
                "total_intro_drafts": len(intro_drafts),
                "contacts_ready_for_outreach": len(ready_contacts),
            },
        }

    # ------------------------------------------------------------------
    # Confidence computation
    # ------------------------------------------------------------------

    def _compute_confidence(
        self,
        warm_paths: list[dict[str, Any]],
        opportunities: list[dict[str, Any]],
        intro_drafts: list[dict[str, Any]],
    ) -> float:
        """Compute confidence score based on data completeness (0.0 to 1.0)."""
        score = 0.0
        total = 3.0

        # Warm paths found
        if warm_paths:
            score += 1.0

        # Opportunities identified
        if opportunities:
            score += 1.0

        # Intro drafts generated
        if intro_drafts:
            score += 1.0

        return round(score / total, 2) if total > 0 else 0.5
