# Project Structure

## Overview

| Aspect | Details |
|--------|---------|
| **Repository Type** | Multi-part |
| **Project Name** | AI Content Generation Suite |
| **Purpose** | Comprehensive AI-powered job search and professional networking platform for both domestic and international job seekers - enabling network building, personalized outreach, compelling content creation, H1B/visa sponsor research, interview preparation, and full job search pipeline management |

## Platform Scope

Complete toolkit for job seekers covering:

| Category | Activities |
|----------|-----------|
| **Cold Outreach** | Cold emails to recruiters/hiring managers, LinkedIn connection requests, InMail messages, referral requests |
| **Content & Personal Branding** | LinkedIn posts, Twitter/X content, thought leadership articles, portfolio showcases |
| **Network Building** | Target company/contact identification, alumni outreach, industry event follow-ups, warm introductions |
| **Application Materials** | Resume tailoring per job, cover letters, personal pitch scripts, portfolio descriptions |
| **Research & Intelligence** | Company research (culture, news, challenges), hiring manager background, industry trends, salary data, H1B visa sponsorship data (sponsor history, approval rates, LCA wages from USVisa, H1BGrader, MyVisaJobs, etc.), green card/PERM sponsorship history |
| **Communication Templates** | Application follow-ups, interview thank-yous, informational interview requests, negotiation messages |
| **Interview Preparation** | Company-specific prep, behavioral responses (STAR), technical prep, questions for interviewers |
| **Tracking & Organization** | Application pipeline, networking CRM, follow-up reminders, contact management |
| **Profile Optimization** | LinkedIn profile enhancement, resume analysis, skills gap identification |

## Project Parts

### Backend (backend/)

| Attribute | Value |
|-----------|-------|
| **Project Type** | Backend API |
| **Language** | Python 3.9+ |
| **Framework** | FastAPI 0.104.1 |
| **Key Technologies** | Pydantic 2.5, OpenAI SDK, Anthropic SDK, BeautifulSoup4, PyPDF2, python-docx |
| **Architecture** | REST API with service layer pattern |
| **Entry Point** | `app/main.py` |

### Frontend (frontend/)

| Attribute | Value |
|-----------|-------|
| **Project Type** | Web Application |
| **Language** | JavaScript (React) |
| **Framework** | React 18.2 with Create React App |
| **Key Technologies** | TailwindCSS 3.3, React Router 6, Axios, HeadlessUI, Recharts |
| **Architecture** | Component-based SPA with routing |
| **Entry Point** | `src/index.js` |

## Integration Architecture

- **Communication**: REST API calls over HTTP
- **Proxy**: Frontend proxies API requests to `http://localhost:8000`
- **Ports**: Frontend on `:3000`, Backend on `:8000`
