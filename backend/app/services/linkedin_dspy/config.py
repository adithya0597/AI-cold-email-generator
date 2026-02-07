"""
LinkedIn-specific constants and configuration for DSPy post generation.
"""

# Mobile "see more" cutoff — hooks must fit before the fold
HOOK_MAX_CHARS = 140

# Engagement sweet spot for post length (characters)
OPTIMAL_POST_CHARS = (1200, 1500)

# Hashtag limits
MAX_HASHTAGS = 5
MIN_HASHTAGS = 3

# Phrases that signal generic, low-engagement LinkedIn content
ANTI_PATTERNS = [
    "I'm excited to announce",
    "I'm thrilled to share",
    "Thoughts?",
    "What do you think?",
    "Agree?",
    "I'm humbled",
    "I'm proud to announce",
    "Let that sink in",
    "Read that again",
    "Full stop.",
]

FORMATTING_RULES = """
- No **bold** markdown (LinkedIn doesn't render it). Use CAPS or unicode for emphasis.
- Max 2-3 emojis, placed at line beginnings only, never mid-sentence.
- Short paragraphs: 1-2 sentences max, separated by blank lines.
- End with ONE specific, answerable question (not generic "thoughts?").
- Use unicode markers: → ● ✓ ✗ for visual structure.
"""
