"""
Enhanced influencer style definitions for LinkedIn post generation.

Each style captures a distinct writing voice with specific patterns,
tone, and anti-patterns to avoid.
"""

INFLUENCER_STYLES = {
    "Gary Vaynerchuk": {
        "description": (
            "Confrontational, high-energy motivational voice. "
            "Speaks in absolute truths with zero filter. "
            "Treats every post like a wake-up call to the reader."
        ),
        "characteristics": [
            "ALL CAPS for emphasis on key words",
            "One-sentence paragraphs for rhythm",
            "Blunt, no-nonsense declarative statements",
            "References hustle, patience, and self-awareness",
            "Calls out excuses and entitlement directly",
            "Uses profanity-adjacent intensity without actual profanity",
        ],
        "tone": "confrontational",
        "example_hook": "Stop waiting for permission to start.",
        "avoid": [
            "Academic language or citations",
            "Hedging or qualifiers like 'maybe' or 'perhaps'",
            "Long multi-sentence paragraphs",
            "Polished corporate-speak",
        ],
    },
    "Simon Sinek": {
        "description": (
            "Philosophical and purpose-driven. Always starts with 'why' "
            "before getting to 'what' or 'how'. Builds arguments through "
            "rhetorical questions and optimistic reframing."
        ),
        "characteristics": [
            "Opens with rhetorical questions or 'Start with Why' framing",
            "Draws parallels between leadership and everyday life",
            "Uses analogy and metaphor over raw data",
            "Builds to an inspiring conclusion",
            "References trust, purpose, and infinite thinking",
            "Conversational yet elevated tone",
        ],
        "tone": "optimistic",
        "example_hook": "Great leaders don't set out to be leaders. They set out to make a difference.",
        "avoid": [
            "Cynicism or negativity",
            "Tactical how-to lists without purpose framing",
            "Aggressive or confrontational tone",
            "Data dumps without narrative context",
        ],
    },
    "Brene Brown": {
        "description": (
            "Vulnerability meets research rigor. Shares personal stories "
            "of failure and growth backed by academic findings. "
            "Makes courage and empathy feel actionable, not soft."
        ),
        "characteristics": [
            "Opens with a personal story or admission of struggle",
            "Cites specific research findings to support points",
            "Uses phrases like 'what I know for sure' and 'the data shows'",
            "Bridges personal vulnerability to universal truth",
            "Ends with a courage-oriented call to action",
            "Balances warmth with intellectual credibility",
        ],
        "tone": "vulnerable",
        "example_hook": "I used to think vulnerability was weakness. Then I looked at the data.",
        "avoid": [
            "Surface-level positivity without depth",
            "Purely tactical or transactional advice",
            "Aggressive self-promotion",
            "Dismissing emotions as irrelevant to business",
        ],
    },
    "Neil Patel": {
        "description": (
            "Data-obsessed marketing practitioner. Every post delivers "
            "numbered, actionable tips backed by specific metrics. "
            "Writes like a consultant giving away free advice."
        ),
        "characteristics": [
            "Leads with a surprising statistic or data point",
            "Numbered lists (3, 5, or 7 items) as core structure",
            "Each tip is immediately actionable",
            "References real tools, platforms, and case studies",
            "Ends with 'which one will you try first?' style CTA",
            "Concise sentences, no filler",
        ],
        "tone": "practical",
        "example_hook": "I analyzed 1M LinkedIn posts. Here are 5 patterns that get 10x engagement.",
        "avoid": [
            "Abstract philosophy without actionable takeaways",
            "Emotional storytelling without data support",
            "Long narrative paragraphs",
            "Vague advice like 'be authentic'",
        ],
    },
    "Arianna Huffington": {
        "description": (
            "Wellness-centered leadership voice. Redefines success beyond "
            "productivity metrics. Advocates for rest, boundaries, and "
            "mindful leadership as competitive advantages."
        ),
        "characteristics": [
            "Reframes burnout as a systemic failure, not personal weakness",
            "Quotes ancient wisdom alongside modern science",
            "Uses calm, measured language even on urgent topics",
            "Advocates for sleep, boundaries, and micro-steps",
            "Positions well-being as a business strategy",
            "References her own burnout-to-transformation story",
        ],
        "tone": "reflective",
        "example_hook": "We are drowning in data and starving for wisdom.",
        "avoid": [
            "Hustle culture glorification",
            "Aggressive or confrontational framing",
            "Dismissing rest as laziness",
            "Purely tactical growth-hacking advice",
        ],
    },
    "Adam Grant": {
        "description": (
            "Organizational psychologist who leads with counterintuitive "
            "research findings. Challenges conventional workplace wisdom "
            "with evidence, then offers a reframe."
        ),
        "characteristics": [
            "Opens with a counterintuitive claim that challenges assumptions",
            "Backs every assertion with named studies or experiments",
            "Uses 'but here's what the research actually shows' pivot",
            "Explores both sides before landing on a nuanced conclusion",
            "References givers, takers, and organizational culture",
            "Ends with a thought-provoking question, not a command",
        ],
        "tone": "curious",
        "example_hook": "The most productive people aren't the ones who work the longest hours.",
        "avoid": [
            "Unsupported opinions presented as facts",
            "Binary thinking without nuance",
            "Motivational platitudes without evidence",
            "Self-promotional content disguised as insight",
        ],
    },
}
