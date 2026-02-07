"""
DSPy Module classes for LinkedIn post generation.

Modules compose Signatures into multi-step pipelines with
hook optimization, anti-pattern filtering, and engagement scoring.
"""

import logging

import dspy

from .config import ANTI_PATTERNS, FORMATTING_RULES, HOOK_MAX_CHARS
from .signatures import (
    GenerateHashtags,
    GenerateLinkedInPost,
    OptimizeHook,
    ScoreEngagement,
)
from .styles import INFLUENCER_STYLES

logger = logging.getLogger(__name__)


class LinkedInPostModule(dspy.Module):
    """End-to-end LinkedIn post generation with quality checks."""

    def __init__(self):
        super().__init__()
        self.generate = dspy.ChainOfThought(GenerateLinkedInPost)
        self.optimize_hook = dspy.ChainOfThought(OptimizeHook)
        self.generate_hashtags = dspy.Predict(GenerateHashtags)
        self.score_engagement = dspy.ChainOfThought(ScoreEngagement)

    def forward(
        self,
        topic: str,
        industry: str,
        audience: str,
        goal: str,
        style: str,
        reference_context: str = "",
    ) -> dspy.Prediction:
        style_info = INFLUENCER_STYLES.get(
            style, INFLUENCER_STYLES.get("Adam Grant")
        )
        style_instructions = self._build_style_prompt(style_info)

        result = self.generate(
            topic=topic,
            industry=industry,
            audience=audience,
            goal=goal,
            style_instructions=style_instructions,
            reference_context=reference_context,
        )

        hook = result.hook
        if len(hook) > HOOK_MAX_CHARS:
            hook_result = self.optimize_hook(draft_hook=hook, topic=topic)
            hook = hook_result.optimized_hook

        full_post = f"{hook}\n\n{result.body}\n\n{result.cta}"

        if self._contains_anti_pattern(full_post):
            logger.info("Anti-pattern detected, regenerating post")
            anti_pattern_note = (
                f"\n\nCRITICAL: Do NOT use any of these phrases: "
                f"{', '.join(ANTI_PATTERNS)}"
            )
            result = self.generate(
                topic=topic,
                industry=industry,
                audience=audience,
                goal=goal,
                style_instructions=style_instructions + anti_pattern_note,
                reference_context=reference_context,
            )
            hook = result.hook
            if len(hook) > HOOK_MAX_CHARS:
                hook_result = self.optimize_hook(draft_hook=hook, topic=topic)
                hook = hook_result.optimized_hook
            full_post = f"{hook}\n\n{result.body}\n\n{result.cta}"

        score_result = self.score_engagement(post_content=full_post)

        return dspy.Prediction(
            hook=hook,
            body=result.body,
            cta=result.cta,
            hashtags=result.hashtags,
            engagement_score=score_result.score,
            engagement_strengths=score_result.strengths,
            engagement_feedback=score_result.improvements,
        )

    def _build_style_prompt(self, style_info: dict) -> str:
        characteristics = "\n".join(
            f"  → {c}" for c in style_info["characteristics"]
        )
        avoid_items = "\n".join(
            f"  ✗ {a}" for a in style_info.get("avoid", [])
        )

        return (
            f"VOICE: {style_info['description']}\n"
            f"TONE: {style_info['tone']}\n\n"
            f"WRITING PATTERNS:\n{characteristics}\n\n"
            f"EXAMPLE HOOK: {style_info.get('example_hook', '')}\n\n"
            f"AVOID:\n{avoid_items}\n\n"
            f"FORMATTING:\n{FORMATTING_RULES}"
        )

    def _contains_anti_pattern(self, text: str) -> bool:
        text_lower = text.lower()
        return any(
            pattern.lower() in text_lower for pattern in ANTI_PATTERNS
        )


class StyleAdapter(dspy.Module):
    """Adapts existing content to match a specific influencer's writing style."""

    def __init__(self):
        super().__init__()
        self.generate = dspy.ChainOfThought(GenerateLinkedInPost)

    def forward(
        self,
        content: str,
        target_style: str,
        industry: str = "General",
        audience: str = "Professionals",
    ) -> dspy.Prediction:
        style_info = INFLUENCER_STYLES.get(
            target_style, INFLUENCER_STYLES.get("Adam Grant")
        )

        characteristics = "\n".join(
            f"  → {c}" for c in style_info["characteristics"]
        )
        avoid_items = "\n".join(
            f"  ✗ {a}" for a in style_info.get("avoid", [])
        )

        style_instructions = (
            f"Rewrite the following content in the voice of {target_style}.\n"
            f"VOICE: {style_info['description']}\n"
            f"TONE: {style_info['tone']}\n"
            f"PATTERNS:\n{characteristics}\n"
            f"AVOID:\n{avoid_items}\n"
            f"FORMATTING:\n{FORMATTING_RULES}"
        )

        result = self.generate(
            topic=content[:200],
            industry=industry,
            audience=audience,
            goal="Build Thought Leadership",
            style_instructions=style_instructions,
            reference_context=content,
        )

        return dspy.Prediction(
            hook=result.hook,
            body=result.body,
            cta=result.cta,
            hashtags=result.hashtags,
        )
