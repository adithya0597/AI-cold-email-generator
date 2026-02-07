"""
Integration service wrapping DSPy modules for use by the FastAPI app.

Handles LM configuration, request mapping, and response formatting.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import dspy

from app.config import settings

from .modules import LinkedInPostModule
from .styles import INFLUENCER_STYLES
from .templates import TEMPLATES

logger = logging.getLogger(__name__)


class LinkedInDSPyService:
    """High-level service that bridges FastAPI requests to the DSPy pipeline."""

    def __init__(self) -> None:
        self.module = LinkedInPostModule()
        self._configure_lm()

    def _configure_lm(self) -> None:
        lm = dspy.LM(
            model="openai/gpt-4o-mini",
            api_key=settings.OPENAI_API_KEY,
            temperature=0.7,
            max_tokens=2000,
        )
        dspy.configure(lm=lm)

    async def generate_post(self, request: Any) -> dict:
        """Generate a LinkedIn post using the DSPy pipeline.

        Args:
            request: A LinkedInPostRequest instance (or any object with
                     topic, industry, target_audience, post_goal,
                     influencer_style attributes).

        Returns:
            Dictionary matching LinkedInPostResponse fields.
        """
        style = request.influencer_style or "Adam Grant"
        goal = (
            request.post_goal.value
            if hasattr(request.post_goal, "value")
            else str(request.post_goal)
        )

        reference_context = ""
        if hasattr(request, "reference_urls") and request.reference_urls:
            reference_context = (
                "Reference URLs provided: "
                + ", ".join(str(u) for u in request.reference_urls)
            )

        prediction = self.module.forward(
            topic=request.topic,
            industry=request.industry,
            audience=request.target_audience,
            goal=goal,
            style=style,
            reference_context=reference_context,
        )

        hashtags_raw = prediction.hashtags
        if isinstance(hashtags_raw, str):
            hashtags = [
                t.strip() for t in hashtags_raw.split() if t.strip()
            ]
        else:
            hashtags = list(hashtags_raw)

        full_content = (
            f"{prediction.hook}\n\n"
            f"{prediction.body}\n\n"
            f"{prediction.cta}\n\n"
            f"{' '.join(hashtags)}"
        )

        word_count = len(full_content.split())
        reading_time = max(10, (word_count * 60) // 200)

        engagement_score = prediction.engagement_score
        if isinstance(engagement_score, str):
            try:
                engagement_score = float(engagement_score)
            except (ValueError, TypeError):
                engagement_score = 0.0

        return {
            "post_id": str(uuid.uuid4()),
            "content": full_content,
            "hook": prediction.hook,
            "body": prediction.body,
            "call_to_action": prediction.cta,
            "hashtags": hashtags,
            "estimated_reading_time": reading_time,
            "style_analysis": INFLUENCER_STYLES.get(style, {}).get(
                "description", f"Custom style: {style}"
            ),
            "engagement_score": engagement_score,
            "engagement_feedback": prediction.engagement_feedback,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_templates(self) -> list:
        """Return all available post templates."""
        return TEMPLATES

    def get_styles(self) -> list:
        """Return all available influencer style names."""
        return list(INFLUENCER_STYLES.keys())
