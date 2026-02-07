# AI Content Generation Suite: Web Application - Product Requirements Plan (PRP)

## Purpose
Build a production-ready, public-facing web application with two core AI-powered features: a Cold Email Generator and a LinkedIn Post Generator. The application must focus on deep personalization through data parsing and provide tangible ROI to users via integrated performance tracking.

## Core Principles
- **Context is King**: The AI must leverage all provided user and external data to generate highly relevant content.
- **Validation Loops**: The final output must be measurable through real-world performance metrics (open rates, post engagement).
- **Information Dense**: The UI should be intuitive, guiding the user to provide the necessary inputs for high-quality generation.
- **Progressive Success**: Launch with core features, validate with users, then enhance with more tools and analytics.

## Goal
Create a scalable, monetizable SaaS platform that empowers sales and marketing professionals to create and optimize their outreach and social media content, saving them time and improving their results.

## Why
- **Business value**: Taps into the growing need for efficient, AI-powered marketing and sales tools. Provides a clear value proposition (better results, less time) that supports a subscription model.
- **Integration**: Demonstrates a sophisticated product that combines LLM prompting, web scraping, external API integration (LinkedIn), and performance analytics.
- **Problems solved**: Addresses the widespread issue of generic, low-performing content and the difficulty of measuring content ROI.

## What
A web application where users can:
- Generate cold emails personalized with their resume and the target company's data.
- Receive AI-generated suggestions for the email's key value proposition.
- Track the open rates of sent emails.
- Generate LinkedIn posts in various expert styles.
- Tailor the post's call-to-action based on a specific goal.
- Track the engagement metrics of their posts directly within the application.

## Success Criteria
✅ Cold Email Generator successfully parses resumes (PDF/DOCX) and company websites.
✅ Value Proposition Synthesis model generates relevant and compelling suggestions.
✅ Email tracking pixel correctly reports open rates.
✅ LinkedIn Post Generator accurately emulates both pre-selected and custom author styles.
✅ LinkedIn API integration correctly fetches post engagement metrics (Views, Likes, Comments).
✅ The application is deployed, stable, and provides a seamless user experience.

## All Needed Context

### Documentation & References
- **React**: https://react.dev/ - Frontend framework for building the user interface.
- **FastAPI**: https://fastapi.tiangolo.com/ - Backend framework for building the API and serving the AI models.
- **BeautifulSoup**: https://beautiful-soup-4.readthedocs.io/en/latest/ - Standard library for web scraping company website data.
- **OpenAI Prompt Engineering**: https://platform.openai.com/docs/guides/prompt-engineering - Core principles for designing prompts.
- **LinkedIn Posts API**: https://learn.microsoft.com/en-us/linkedin/marketing/integrations/community-management/shares/posts-api - LinkedIn API documentation.

## Desired Codebase Structure
```
.
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ColdEmailGenerator.js
│   │   │   └── LinkedInPostGenerator.js
│   │   └── App.js
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app definition
│   │   ├── models.py            # Pydantic models for API requests/responses
│   │   ├── services/
│   │   │   ├── email_service.py     # Logic for email generation & tracking
│   │   │   └── post_service.py      # Logic for post generation & tracking
│   │   └── core/
│   │       ├── llm_clients.py     # LLM integration logic
│   │       └── web_scraper.py     # Web scraping logic
│   ├── tests/
│   │   ├── test_email_service.py
│   │   └── test_post_service.py
├── .env.example                 # Environment variables template
├── requirements.txt             # Python dependencies
└── README.md                    # Comprehensive documentation
```

## Known Gotchas & Library Quirks
- **CRITICAL**: Web scraping must be robust against different website structures and handle failures gracefully.
- **CRITICAL**: LinkedIn post generation relies on author style emulation; ensure high-quality examples in the uploaded database.
- **CRITICAL**: Few-shot prompting for custom author styles is dependent on the quality of real-time search results; implement fallbacks.
- **CRITICAL**: Email tracking pixels can be blocked; educate users that open rates are an estimate.
- **CRITICAL**: Ensure all data handling is compliant with privacy regulations (GDPR, CCPA).
- **CRITICAL**: Store sensitive API keys and user credentials securely in .env and use a proper database.

## Implementation Blueprint

### Data Models and Structure

```python
# backend/app/models.py - Core Pydantic models
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional

class ColdEmailRequest(BaseModel):
    user_resume_text: str
    recipient_name: str
    recipient_role: str
    company_website_url: HttpUrl
    company_tone: str
    email_goal: str
    pain_point: Optional[str] = None

class LinkedInPostRequest(BaseModel):
    topic: str
    industry: str
    target_audience: str
    post_goal: str = Field(..., description="Options: Drive Engagement, Generate Leads, Build Thought Leadership")
    influencer_style: str
    custom_author_name: Optional[str] = None
```

## List of Tasks

### Task 1: Setup Backend with FastAPI
- Define API endpoints for /generate-email and /generate-post.
- Implement Pydantic models for request validation.

### Task 2: Implement Web Scraping and Parsing Service
- Use BeautifulSoup and httpx to scrape text from company URLs.
- Implement resume text extraction for PDF/DOCX.

### Task 3: Implement Cold Email Service
- Develop the multi-step LLM prompt chain for tone analysis and value proposition synthesis.
- Implement logic to embed a tracking pixel.

### Task 4: Implement LinkedIn Post Service
- Implement logic to select between curated prompts and dynamic few-shot prompts.
- Integrate with LinkedIn API for performance tracking.

### Task 5: Implement Frontend with React
- Build UI components for both generators with all specified input fields.
- Handle file uploads and API communication with the backend.

### Task 6: Add Comprehensive Tests
- Write unit tests for all services, mocking LLM calls and external APIs.
- Ensure 80%+ test coverage.

### Task 7: Create Documentation
- Include setup, installation, and usage instructions.
- Detail the API key configuration steps for all services.

## Per Task Pseudocode

### Task 3: Value Proposition Synthesis
```python
async def synthesize_value_propositions(resume_text: str, company_text: str, pain_point: str) -> List[str]:
    # PATTERN: Use a structured prompt with clear instructions
    prompt = f"""
    Act as a career coach. Based on the following resume text and company description,
    generate 3 unique value propositions connecting the candidate's skills to the company's needs.
    If a pain point is provided, make one proposition directly address it.

    Resume: {resume_text}
    Company: {company_text}
    Pain Point: {pain_point}

    Return a JSON list of strings.
    """
    response = await llm_client.generate(prompt)
    return parse_json_response(response)
```

### Task 4: Dynamic Style Prompting
```python
async def generate_custom_style_post(request: LinkedInPostRequest) -> str:
    # PATTERN: Real-time search to build a few-shot prompt
    author_samples = await real_time_search(request.custom_author_name)
    
    prompt = f"""
    You are an expert LinkedIn post generator. Emulate the writing style of {request.custom_author_name}
    based on the following examples:
    
    Example 1: {author_samples[0]}
    Example 2: {author_samples[1]}

    Now, write a post on the topic: "{request.topic}" for an audience of {request.target_audience}.
    The goal is to {request.post_goal}. Structure it with a Hook, Body, and Call to Action.
    """
    response = await llm_client.generate(prompt)
    return response
```

## Validation Loop

### Level 1: Unit & Integration Tests
```bash
# Run backend tests
pytest backend/tests/ -v --cov=backend/app

# Run frontend tests
npm test -- --coverage
```

### Level 2: End-to-End Test
1. Navigate to the Cold Email Generator.
2. Upload a sample resume and enter a company URL.
3. Verify that relevant value propositions are generated.
4. Generate the email and check that the tracking pixel is present.
5. Navigate to the LinkedIn Post Generator.
6. Select a pre-selected style and generate a post. Verify the tone.
7. Select "Custom," enter a public figure's name, and generate. Verify the tone.
8. Verify that the post is structured correctly with a hook, body, and CTA.

## Final Validation Checklist
✅ All unit tests pass with >80% coverage.
✅ E2E tests for both features are successful.
✅ Author style database uploads work correctly.
✅ Web scraping handles common website layouts and errors.
✅ The application is deployed and accessible via a public URL.
✅ README is complete with setup and usage instructions.
✅ All sensitive keys are managed via environment variables.

## Anti-Patterns to Avoid
❌ Don't build a web scraper that is too brittle; it will break often.
❌ Don't underestimate the importance of quality author samples for style emulation.
❌ Don't rely on a single LLM provider; build an abstraction layer to switch easily.
❌ Don't neglect the user experience for file uploads and loading states.
❌ Don't hardcode prompt templates; make them configurable.

## Confidence Score: 8/10
High confidence in the core value proposition. The main technical challenges will be the robustness of the web scraper and the reliability of the dynamic few-shot prompting for custom author styles. The performance tracking features are complex but will provide a significant competitive advantage.