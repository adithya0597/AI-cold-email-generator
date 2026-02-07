"""
LinkedIn post templates — structural blueprints for different post formats.

Each template defines a repeatable structure with style suggestions,
target lengths, and example hooks.
"""

TEMPLATES = [
    # --- Existing 6 templates ---
    {
        "name": "Insight Share",
        "description": "Share a professional insight or lesson learned from experience.",
        "suggested_style": "Adam Grant",
        "structure_hint": "Hook (counterintuitive insight) → Context (why this matters) → Evidence (data or story) → Reframe (new way to think about it) → Question",
        "example_hook": "The best managers I know do something most companies forbid.",
        "target_length_chars": 1300,
    },
    {
        "name": "Career Milestone",
        "description": "Celebrate a professional achievement while providing value to the reader.",
        "suggested_style": "Brene Brown",
        "structure_hint": "Hook (the achievement) → Behind the scenes (struggle) → Lessons learned (3 max) → Gratitude → Forward-looking CTA",
        "example_hook": "Today I hit a milestone I almost gave up on 3 years ago.",
        "target_length_chars": 1200,
    },
    {
        "name": "Industry Trend",
        "description": "Analyze a trend in your industry and share a unique perspective.",
        "suggested_style": "Simon Sinek",
        "structure_hint": "Hook (trend statement) → Why it matters now → What most people miss → Your prediction → Question inviting debate",
        "example_hook": "Everyone is talking about AI replacing jobs. Nobody is talking about what comes after.",
        "target_length_chars": 1400,
    },
    {
        "name": "Quick Tips",
        "description": "Deliver 3-5 actionable tips the reader can apply immediately.",
        "suggested_style": "Neil Patel",
        "structure_hint": "Hook (promise of value) → Tip 1 with result → Tip 2 with result → Tip 3 with result → CTA to save/share",
        "example_hook": "5 changes to my morning routine that doubled my output.",
        "target_length_chars": 1300,
    },
    {
        "name": "Motivational",
        "description": "Inspire action through a strong, direct message.",
        "suggested_style": "Gary Vaynerchuk",
        "structure_hint": "Hook (bold statement) → Reality check → Reframe → Encouragement → Direct CTA",
        "example_hook": "You don't need another course. You need to start.",
        "target_length_chars": 1000,
    },
    {
        "name": "Wellness & Leadership",
        "description": "Connect well-being practices to professional performance.",
        "suggested_style": "Arianna Huffington",
        "structure_hint": "Hook (wellness insight) → The cost of ignoring it → Science/data → Micro-step to try today → Reflective question",
        "example_hook": "I used to wear exhaustion like a badge of honor. Then I collapsed.",
        "target_length_chars": 1200,
    },
    # --- 4 NEW templates ---
    {
        "name": "Controversial Take",
        "description": "Challenge a widely held belief in your industry. Drives 3-5x comments by triggering debate.",
        "suggested_style": "Adam Grant",
        "structure_hint": "Hook (Everyone thinks X) → Why the consensus is wrong → Your contrarian evidence → The nuance most miss → Specific question inviting pushback",
        "example_hook": "Everyone thinks networking events are valuable. Here's why they're wrong.",
        "target_length_chars": 1400,
    },
    {
        "name": "Personal Story",
        "description": "Vulnerability plus growth narrative. Top trend in 2025-2026 LinkedIn content. Highest trust-building format.",
        "suggested_style": "Brene Brown",
        "structure_hint": "Hook (moment of failure or doubt) → What happened (raw, specific details) → The turning point → What I learned → How this applies to you → Question about their experience",
        "example_hook": "Two years ago I got fired. It was the best thing that happened to my career.",
        "target_length_chars": 1500,
    },
    {
        "name": "How-To Guide",
        "description": "Step-by-step actionable framework. High save and share rate because readers bookmark for later use.",
        "suggested_style": "Neil Patel",
        "structure_hint": "Hook (result you'll help them get) → Step 1 with why it works → Step 2 with common mistake → Step 3 with pro tip → Step 4 with expected result → CTA to save for later",
        "example_hook": "How I got 50K impressions on LinkedIn in 30 days (step by step).",
        "target_length_chars": 1500,
    },
    {
        "name": "Listicle",
        "description": "'X Things I Learned' numbered format. Scannable, drives dwell time, and performs well in the algorithm.",
        "suggested_style": "Gary Vaynerchuk",
        "structure_hint": "Hook (X things I learned from Y) → Item 1 (short, punchy) → Item 2 → Item 3 → ... → Item X → Bonus insight → Which one resonates most?",
        "example_hook": "7 things I learned after sending 500 cold emails.",
        "target_length_chars": 1400,
    },
]
