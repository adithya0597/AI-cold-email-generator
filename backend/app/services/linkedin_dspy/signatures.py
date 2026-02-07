"""
DSPy Signature classes for LinkedIn post generation.

Signatures define the input/output contract for each step in the pipeline.
DSPy uses these to construct optimized prompts automatically.
"""

import dspy


class GenerateLinkedInPost(dspy.Signature):
    """Generate a high-performing LinkedIn post optimized for engagement."""

    topic: str = dspy.InputField(desc="Main topic or idea for the post")
    industry: str = dspy.InputField(desc="Target industry")
    audience: str = dspy.InputField(desc="Target audience")
    goal: str = dspy.InputField(
        desc="Post goal: Drive Engagement, Generate Leads, or Build Thought Leadership"
    )
    style_instructions: str = dspy.InputField(
        desc="Writing style/voice instructions"
    )
    reference_context: str = dspy.InputField(
        desc="Context from reference URLs, empty if none", default=""
    )

    hook: str = dspy.OutputField(
        desc="Compelling first line under 140 characters that makes readers click 'see more'"
    )
    body: str = dspy.OutputField(
        desc=(
            "Main post content. Short paragraphs, 1-2 sentences each, "
            "separated by blank lines. Total post 1200-1500 characters."
        )
    )
    cta: str = dspy.OutputField(
        desc="Specific, answerable closing question that drives comments"
    )
    hashtags: str = dspy.OutputField(
        desc="3-5 relevant hashtags in #PascalCase format, space-separated"
    )


class OptimizeHook(dspy.Signature):
    """Optimize a LinkedIn post hook to be under 140 characters while maximizing click-through."""

    draft_hook: str = dspy.InputField(
        desc="The draft hook that may be too long"
    )
    topic: str = dspy.InputField(desc="Post topic for context")

    optimized_hook: str = dspy.OutputField(
        desc="Compelling hook under 140 characters"
    )


class ScoreEngagement(dspy.Signature):
    """Predict LinkedIn post engagement and provide improvement suggestions."""

    post_content: str = dspy.InputField(desc="The full LinkedIn post text")

    score: float = dspy.OutputField(
        desc="Predicted engagement score 0-100"
    )
    strengths: str = dspy.OutputField(
        desc="What works well in this post"
    )
    improvements: str = dspy.OutputField(
        desc="Specific improvements to increase engagement"
    )


class GenerateHashtags(dspy.Signature):
    """Generate optimal LinkedIn hashtags for a post."""

    content: str = dspy.InputField(desc="The post content")
    industry: str = dspy.InputField(desc="Target industry")

    hashtags: str = dspy.OutputField(
        desc="3-5 hashtags in #PascalCase, mix of broad and niche, space-separated"
    )
