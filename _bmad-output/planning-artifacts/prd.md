---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-03-success', 'step-04-journeys', 'step-05-domains', 'step-06-features', 'step-07-nfrs', 'step-08-ux', 'step-09-tech', 'step-10-deps', 'step-11-review']
prdStatus: 'complete'
validationScore: 97
inputDocuments:
  - '_bmad-output/analysis/brainstorming-session-2026-01-25.md'
  - 'docs/project-structure.md'
  - 'docs/codebase-analysis.md'
workflowType: 'prd'
documentCounts:
  briefs: 0
  research: 0
  brainstorming: 1
  projectDocs: 2
projectType: 'brownfield'
classification:
  projectType: 'saas_b2b'
  domain: 'hr_tech_career'
  complexity: 'medium-high'
  projectContext: 'brownfield'
  innovationSignals:
    - 'AI Agents'
    - 'Workflow automation'
    - 'Tier-based autonomy model'
gtmStrategy:
  primaryMarket: 'All job seekers (active + passive)'
  h1bRole: 'Premium feature, not primary niche'
  coreValueProp: 'AI agents do your job search 24/7'
---

# Product Requirements Document - JobPilot

**Author:** bala
**Date:** 2026-01-25

## Executive Summary

**JobPilot** is an agent-first job search platform that transforms how people find jobs. Instead of users actively searching, applying, and tracking - AI agents work 24/7 on their behalf. Users set goals, review daily briefings, approve high-stakes actions, and show up to interviews.

**Core Value Proposition:** "Your AI Career Agent that works 24/7"

**Target Market:** All job seekers - both active (currently searching) and passive (employed but open) - who are tired of the manual grind of job searching.

**Differentiator:** Tier-based autonomy model inspired by Tesla's autopilot levels:
- **Free (L0-L1):** Agent drafts, human executes everything
- **Pro $19/mo (L2):** Agent acts, human reviews daily digest
- **H1B Pro $49/mo (L3):** Agent acts autonomously within rules + H1B sponsor intelligence
- **Career Insurance $29/mo (L2-3):** Passive background mode for employed professionals

**Brownfield Context:** Built on existing AI Content Generation Suite codebase (70% reusable) - FastAPI backend, React frontend, LLM client abstraction, dual-model processing strategy.

---

## Success Criteria

### User Success

| Metric | Target | Rationale |
|--------|--------|-----------|
| **Time to first value** | <5 minutes | Zero-setup onboarding (paste LinkedIn URL → full profile) |
| **Daily active time required** | <10 minutes | User reviews briefing and approves actions, not doing grunt work |
| **Quality job matches per week** | 10+ | Agent actively finding relevant opportunities |
| **Application completion rate** | 80%+ of approved jobs | Agent handles tedious application process reliably |
| **Net Promoter Score** | 50+ | Users feel "agent is working for me" |

**The "Aha!" Moment:** User wakes up to "Applied to 5 jobs overnight. 2 need your input." - they realize they're not doing job search anymore, the agent is.

### Business Success

| Timeframe | Metric | Target |
|-----------|--------|--------|
| **Week 4** | Beta users | 50 job seekers (mix of active/passive) |
| **Week 8** | Paying customers | 30 Pro ($19) + 5 H1B Pro ($49) = ~$815 MRR |
| **Week 12** | Growth validation | 80 Pro + 20 H1B Pro = ~$2,500 MRR |
| **Month 6** | Product-market fit | 400 Pro + 100 H1B Pro = ~$12,500 MRR |
| **Year 1** | Scale | 2,000+ paid users, $50k+ MRR |

**Key Business Metrics:**
- Pro → H1B Pro upgrade rate: 15-20% of eligible users
- 30-day retention: 65%+
- CAC payback period: <3 months
- Gross margin: 68%+ (Pro), 81%+ (H1B Pro), 86%+ (Career Insurance)

### Technical Success

| Metric | Target | Rationale |
|--------|--------|-----------|
| **LLM cost per user** | <$6/month | Maintain 68%+ gross margin on Pro tier |
| **Agent response time** | <30 seconds | Users shouldn't wait for briefings/actions |
| **Platform uptime** | 99.5% | Job search is time-sensitive |
| **Auto-apply success rate** | >95% | Agent actions must be reliable |
| **H1B data freshness** | <24 hours | Sponsor data must be current |

### Measurable Outcomes

**User Outcomes:**
- Users get more interviews with less effort
- Users never miss follow-ups or lose track of applications
- Users feel confident with AI-generated materials (resumes, cover letters)

**Business Outcomes:**
- Sustainable unit economics with LLM cost optimization
- Clear upgrade path from Free → Pro → H1B Pro
- H1B feature drives premium tier adoption without being the primary market

---

## Product Scope

### MVP - Minimum Viable Product (Weeks 1-4)

**Goal:** Prove core value prop - "Agent works for you"

| Feature | Agent | Priority |
|---------|-------|----------|
| Zero-setup onboarding (LinkedIn URL → profile) | Core | P0 |
| Daily briefing system | Orchestrator | P0 |
| Job Scout Agent (matching + alerts) | Research | P0 |
| Resume Agent (auto-tailoring) | Action | P0 |
| Pipeline Agent (auto-tracking from email) | Tracking | P0 |

**MVP Outcome:** Users can sign up in <5 min, get matched jobs, see auto-tailored resumes, and have their pipeline managed automatically.

### Growth Features (Weeks 5-8)

**Goal:** Differentiate and monetize

| Feature | Agent | Tier |
|---------|-------|------|
| H1B Sponsor Database + Alerts | Research | H1B Pro |
| Apply Agent (with human approval) | Action | Pro |
| Follow-up Agent | Tracking | Pro |
| Cover Letter Generator | Action | Pro |

**Growth Outcome:** Clear value differentiation between tiers; H1B users see unique value in premium tier.

### Vision (Weeks 9-12+)

**Goal:** Full autonomous job search

| Feature | Agent | Tier |
|---------|-------|------|
| Full autonomy mode (L3) | All | H1B Pro |
| Network Agent (relationship warming) | Action | H1B Pro |
| Content Agent (thought leadership) | Action | Pro |
| Interview Intel Agent (auto-prep) | Research | Pro |
| Career Insurance passive mode | All | Career Insurance |
| Enterprise outplacement (B2B) | All | Enterprise |

---

## User Journeys

### Journey 1: Maya - The Exhausted Active Job Seeker

**Profile:**
- 28-year-old marketing manager, laid off 6 weeks ago
- Applied to 150+ jobs manually, gotten 3 interviews
- Spends 4+ hours daily on job boards, feels like a full-time job
- Frustrated by repetitive applications, losing track of follow-ups

**Current Pain:**
> "I spend more time reformatting my resume than actually preparing for interviews. I applied somewhere last week and can't even remember which company."

**JobPilot Journey:**

| Stage | Experience | Autonomy Level |
|-------|------------|----------------|
| **Onboarding** | Pastes LinkedIn URL → full profile in 30 seconds | - |
| **Day 1** | Wakes up to: "Found 12 matches. Here are the top 5." | L1 (Free) |
| **Day 3** | Upgrades to Pro after seeing tailored resume previews | L2 |
| **Week 1** | Morning briefing: "Applied to 5 jobs overnight. 2 need your input." | L2 |
| **Week 2** | "Interview scheduled at Acme Corp. Prep briefing ready." | L2 |

**Critical Design Requirements (from What-If Analysis):**
- **Deal-breaker filters**: Maya sets "no startups under 50 people, no <$80k, no relocation" - agent NEVER violates these
- **Resume validation gate**: System validates resume before first auto-apply to prevent error propagation
- **Calendar conflict detection**: When 3 interviews land same day, agent suggests rescheduling + generates prep for each
- **Quick win celebration**: If Maya lands job in Week 2, celebrate + offer Career Insurance for next transition

**Success Metric:** Maya's daily job search time drops from 4 hours to 10 minutes.

---

### Journey 2: David - The Passive Professional

**Profile:**
- 35-year-old senior engineer at Fortune 500, employed but open
- Last job search was 3 years ago, dreads starting again
- Wants to know his market value without risking current job
- Would move for 30%+ raise or director title

**Current Pain:**
> "I don't have time to job search, but I also don't want to miss the perfect opportunity. I just want something running in the background."

**JobPilot Journey:**

| Stage | Experience | Autonomy Level |
|-------|------------|----------------|
| **Onboarding** | "Career Insurance" pitch resonates immediately | - |
| **Setup** | Sets stealth mode + employer blocklist + 30% raise threshold | L2-3 |
| **Month 1** | Weekly digest: "3 roles matched your criteria. None hit your bar." | L2 (passive) |
| **Month 3** | Alert: "Director role at Series C startup. 95% match. Rare." | Escalation |
| **Action** | Reviews, approves outreach. Agent handles intro + scheduling. | L3 |

**Critical Design Requirements (from What-If Analysis):**
- **Stealth Mode (P0)**: No public footprint, encrypted employer blocklist, no activity visible to current employer
- **Vacation handling**: Configurable response when opportunity arises during PTO (auto-hold, auto-decline, or escalate to personal email)
- **Engagement pulse**: Monthly "Still happy? Here's what I'd find if you weren't" to prevent paying-but-forgotten churn
- **Skill decay alerts**: "40% of Director roles now require X - want upskilling resources?"

**Success Metric:** David stays subscribed 12+ months, always "market ready" without lifting a finger.

---

### Journey 3: Priya - The H1B Job Seeker

**Profile:**
- 29-year-old data scientist on H1B, current visa expires in 8 months
- Needs employer who will sponsor AND start green card process
- Wasted 2 months interviewing at a company that said "we sponsor" but didn't
- Anxious about timeline, needs certainty

**Current Pain:**
> "I can't afford to waste time on companies that won't sponsor. Every week I spend interviewing at the wrong place is a week closer to my deadline."

**JobPilot Journey:**

| Stage | Experience | Autonomy Level |
|-------|------------|----------------|
| **Onboarding** | Sees H1B Pro tier, immediately understands value | - |
| **Setup** | Inputs visa expiry date, current employer, target companies | L3 |
| **Day 1** | "Found 8 verified H1B sponsors hiring data scientists in your area" | L3 |
| **Week 2** | "Company X has 94% H1B approval rate, started 12 green cards last year" | L3 |
| **Month 2** | Visa at 6 months: System enters "Urgent Mode" - expanded criteria, higher velocity | Adaptive |

**Critical Design Requirements (from What-If Analysis):**
- **Data freshness badges**: Show when H1B data was last verified, multiple source confirmation
- **Sponsor reliability scores**: Crowdsourced ratings - flag companies with mixed "we sponsor" signals
- **Current employer exclusion**: Auto-exclude current employer + configurable competitor blocklist
- **Urgent Mode trigger**: When visa < 90 days, UX shifts - expand criteria, increase apply velocity, surface backup plans (OPT extension, Canada PR pathways)
- **Multi-source verification**: Never rely on single data source for sponsor status

**Success Metric:** Priya finds verified sponsor in <60 days, zero time wasted on non-sponsors.

---

### Journey 4: Jennifer - The Enterprise HR Admin

**Profile:**
- 42-year-old HR Director at mid-size tech company doing layoffs
- Needs to provide outplacement support for 200 employees
- Budget-conscious, needs to show ROI to leadership
- Cares about employee experience and company reputation

**Current Pain:**
> "Traditional outplacement is expensive and employees hate it. I need something that actually helps them land jobs, not just checks a box."

**JobPilot Journey:**

| Stage | Experience | Autonomy Level |
|-------|------------|----------------|
| **Discovery** | Sales demo shows agent capabilities + enterprise dashboard | - |
| **Pilot** | 20 employees onboarded, Jennifer monitors aggregate metrics | Admin view |
| **Week 4** | Dashboard: "15 employees active, 47 interviews scheduled, 3 offers" | Reporting |
| **Month 2** | Expands to full 200, negotiates volume pricing | Enterprise |
| **Month 3** | Presents to leadership: "68% placement rate vs 40% industry average" | ROI proof |

**Critical Design Requirements (from What-If Analysis):**
- **Human QA layer option**: "White-glove" tier with dedicated support to prevent AI quality complaints
- **PII/confidential scanner**: Automatic detection before any external action - legal liability protection
- **Company-level rate limiting**: Prevent 500 employees all applying to same hot company (spam triggers, reputation damage)
- **Real-time dashboard**: Leading indicators (interviews scheduled, not just placements) so Jennifer can report progress early
- **Diversity of targets**: Intelligent distribution across companies to avoid flooding any single employer

**Success Metric:** 60%+ placement rate within 90 days, positive employee NPS, Jennifer renews contract.

---

### Cross-Journey Design Principles

*Derived from What-If Analysis across all personas:*

| Principle | Rationale | Implementation |
|-----------|-----------|----------------|
| **Trust Guardrails are P0** | Every persona has a scenario where agent overreach destroys trust | Deal-breaker filters, approval gates, undo capabilities |
| **Never Fabricate** | LLM hallucination = broken trust | Ground all actions in verified job board data |
| **Feedback Loops Everywhere** | Users must correct the agent constantly | Thumbs up/down on every match, explicit "this is wrong" flows |
| **Rejection Awareness** | Following up after "no" burns bridges | Parse rejection signals, "no means no" rules |
| **Privacy by Default** | Especially for passive users | Stealth mode, encrypted blocklists, no public footprint |
| **Adaptive Urgency** | H1B users need different behavior based on timeline | Visa deadline triggers UX mode shifts |

---

### Focus Group Insights

*From User Persona Focus Group with Maya, David, Priya, and Jennifer:*

#### Key Persona Reactions

| Feature | Maya (Active) | David (Passive) | Priya (H1B) | Jennifer (Enterprise) |
|---------|---------------|-----------------|-------------|----------------------|
| **Daily Briefing** | "Show me WHICH jobs and WHY" | "Weekly is fine - daily feels like pressure" | "H1B status must be front and center" | "Need aggregate view for reporting" |
| **Auto-Tailoring** | "Show me the diff before sending" | "Never touch my master resume" | "Handle visa disclosure nuance" | "Can it coach bad resumes, not just tailor?" |
| **Autonomy Tiers** | "Let me earn L3 over time" | "Need EMERGENCY BRAKE always" | "L2.5? Auto-apply to verified sponsors only" | "Per-employee autonomy settings needed" |

#### Dealbreakers by Persona

| Persona | Instant Uninstall Trigger |
|---------|---------------------------|
| **Maya** | Agent applies to job she explicitly rejected; recruiter calls about unknown application |
| **David** | ANY signal reaches current employer - even indirect "similar profile" notifications |
| **Priya** | Single application to non-sponsor; visa status disclosed without consent |
| **Jennifer** | Employees call it "creepy" or "Big Brother"; AI writes something embarrassing |

#### Wishlist Features (Future Consideration)

| Persona | Wish | Category |
|---------|------|----------|
| **Maya** | "Why am I not hearing back?" intelligence | Feedback Loop |
| **David** | Market value benchmark without effort | Passive Intelligence |
| **Priya** | Connect with H1B holders at target companies | Community |
| **Jennifer** | Predictive analytics for at-risk employees | Enterprise Analytics |

#### Surfaced Requirements

| Requirement | Description | Priority |
|-------------|-------------|----------|
| **Transparency Mode** | Show WHAT agent did and WHY - never black box | P0 |
| **Stealth Proof** | Provable invisibility for passive users, not just promises | P0 |
| **Source Attribution** | H1B data sources visible with freshness timestamps | P0 |
| **Emergency Brake** | Universal instant-pause across all tiers and personas | P0 |
| **Resume Diff View** | Side-by-side comparison before any application sent | P1 |
| **Empathy Layer** | Emotional support messaging for layoff situations | P1 |
| **Earned Autonomy** | Users can unlock higher tiers through trust-building, not just payment | P1 |
| **Per-User Config** | Enterprise admins set individual autonomy levels | P1 |
| **Briefing Frequency** | Configurable: daily (active), weekly (passive), real-time (urgent) | P1 |
| **Rejection Intelligence** | "Why no callbacks?" analysis and recommendations | P2 |
| **Market Benchmarking** | "What's my value?" for passive users | P2 |
| **H1B Community** | Connect users with successful H1B hires at target companies | P2 |
| **Churn Prediction** | Enterprise early warning for disengaged employees | P2 |

---

## Domain Requirements

### Domain 1: Agent Orchestration

*The brain that coordinates all specialized agents*

| Requirement | Description | Tier | Priority |
|-------------|-------------|------|----------|
| **Orchestrator Agent** | Central coordinator that routes tasks to specialized agents, manages state, resolves conflicts | All | P0 |
| **Autonomy Level Enforcement** | Enforce L0-L3 boundaries - agent cannot exceed user's tier permissions | All | P0 |
| **Emergency Brake** | Instant global pause - stops all agent activity within 5 seconds | All | P0 |
| **Action Audit Log** | Complete history of every agent action with timestamp, rationale, outcome | All | P0 |
| **Daily Briefing Generator** | Synthesize all agent activity into digestible summary with action items | All | P0 |
| **User Preference Memory** | Learn and remember user corrections, deal-breakers, preferences | All | P1 |
| **Earned Autonomy Progression** | Track trust signals to unlock higher autonomy over time | Pro+ | P1 |
| **Conflict Resolution** | When agents disagree (e.g., apply vs. wait), escalate to user or use rules | Pro+ | P1 |

### Domain 2: Research & Intelligence

*Finding opportunities and gathering intel*

| Requirement | Description | Tier | Priority |
|-------------|-------------|------|----------|
| **Job Scout Agent** | Continuous monitoring of job boards for matching opportunities | All | P0 |
| **Job Matching Algorithm** | Score jobs against user profile, preferences, deal-breakers | All | P0 |
| **Company Research** | Auto-gather company info: culture, news, funding, growth signals | Pro+ | P1 |
| **H1B Sponsor Database** | Aggregated sponsor data with approval rates, LCA wages, freshness dates | H1B Pro | P0 |
| **H1B Source Attribution** | Show data sources (H1BGrader, MyVisaJobs, USCIS) with last-updated timestamps | H1B Pro | P0 |
| **Sponsor Reliability Score** | Crowdsourced rating of "do they actually sponsor?" | H1B Pro | P1 |
| **Hiring Manager Profiler** | Research interviewer backgrounds for conversation hooks | Pro+ | P2 |
| **Market Benchmarking** | "What's my market value?" passive intelligence for employed users | Career Ins. | P2 |
| **Predictive Hiring Signals** | Detect companies likely to hire before jobs posted (funding, growth) | H1B Pro | P2 |

### Domain 3: Application Automation

*Preparing and submitting applications*

| Requirement | Description | Tier | Priority |
|-------------|-------------|------|----------|
| **Resume Agent** | Auto-tailor resume per job, optimized for ATS | Pro+ | P0 |
| **Resume Diff View** | Side-by-side comparison before any application sent | Pro+ | P0 |
| **Master Resume Protection** | Never modify original - always work on copies | All | P0 |
| **Cover Letter Generator** | Personalized cover letters with company-specific references | Pro+ | P1 |
| **Apply Agent** | Submit applications with human approval (L2) or autonomously (L3) | Pro+ | P1 |
| **Application Queue** | Batch applications for overnight submission with morning review | Pro+ | P1 |
| **Deal-Breaker Enforcement** | Agent NEVER applies to jobs violating user's explicit filters | All | P0 |
| **Visa Disclosure Control** | User controls when/how visa status is disclosed per application | H1B Pro | P1 |
| **Resume Coaching** | Feedback on weak resumes, not just tailoring (for Enterprise) | Enterprise | P2 |

### Domain 4: Pipeline Management

*Tracking applications and follow-ups*

| Requirement | Description | Tier | Priority |
|-------------|-------------|------|----------|
| **Pipeline Agent** | Auto-track application status from email parsing | Pro+ | P0 |
| **Status Detection** | Detect application events: received, reviewed, interview, rejection | Pro+ | P0 |
| **Follow-up Agent** | Draft and send follow-ups at optimal intervals | Pro+ | P1 |
| **Rejection Signal Parsing** | Detect "no" signals and mark as closed (no further follow-up) | Pro+ | P1 |
| **Interview Scheduling** | Detect interview requests, surface to user, suggest times | Pro+ | P1 |
| **Calendar Integration** | Sync interviews to calendar with auto-generated prep blocks | Pro+ | P2 |
| **Rejection Intelligence** | Analyze patterns: "Why am I not hearing back?" | Pro+ | P2 |

### Domain 5: User Communication & Control

*How users interact with and control the agent*

| Requirement | Description | Tier | Priority |
|-------------|-------------|------|----------|
| **Daily Briefing** | Morning summary: what happened, what needs attention | All | P0 |
| **Briefing Frequency Config** | Daily (active), weekly (passive), real-time (urgent) options | All | P1 |
| **Transparency Mode** | Every action shows WHAT and WHY - never black box | All | P0 |
| **Approval Queue** | Actions awaiting user approval with context and recommendations | Pro+ | P0 |
| **Feedback Loops** | Thumbs up/down on every match, explicit correction flows | All | P0 |
| **Notification Preferences** | Control channels: email, push, SMS, in-app only | All | P1 |
| **Stealth Mode** | Zero public footprint for passive users | Career Ins. | P0 |
| **Stealth Verification** | Provable invisibility - show what data is/isn't exposed | Career Ins. | P1 |
| **Employer Blocklist** | Encrypted list of companies agent must never contact | All | P0 |

### Domain 6: Enterprise & B2B

*Features for HR admins managing outplacement*

| Requirement | Description | Tier | Priority |
|-------------|-------------|------|----------|
| **Admin Dashboard** | Aggregate metrics: active users, interviews, placements | Enterprise | P0 |
| **Per-Employee Autonomy** | Admin sets individual autonomy levels per employee | Enterprise | P1 |
| **Bulk Onboarding** | CSV upload to provision 100+ employees at once | Enterprise | P1 |
| **PII Scanner** | Auto-detect confidential info before external actions | Enterprise | P0 |
| **Company Rate Limiting** | Prevent flooding single employer with applications | Enterprise | P1 |
| **White-Glove Mode** | Human QA layer for sensitive situations | Enterprise | P2 |
| **Empathy Messaging** | Warm, supportive tone for layoff situations | Enterprise | P1 |
| **At-Risk Alerts** | Predictive analytics for disengaged employees | Enterprise | P2 |
| **ROI Reporting** | Placement rates, time-to-hire, comparison to industry benchmarks | Enterprise | P1 |

### Domain 7: Onboarding & Profile

*Getting users started quickly*

| Requirement | Description | Tier | Priority |
|-------------|-------------|------|----------|
| **Zero-Setup Onboarding** | Paste LinkedIn URL → full profile in <60 seconds | All | P0 |
| **LinkedIn Profile Parser** | Extract experience, skills, education, preferences | All | P0 |
| **Resume Upload** | Alternative: upload existing resume for parsing | All | P0 |
| **Preference Wizard** | Quick setup: job types, locations, salary, deal-breakers | All | P0 |
| **H1B Profile Extension** | Visa type, expiry date, sponsor requirements | H1B Pro | P0 |
| **Profile Completeness Score** | Guide users to add missing info that improves matching | All | P1 |

### Domain Priority Matrix

| Domain | P0 Count | P1 Count | P2 Count | MVP Critical |
|--------|----------|----------|----------|--------------|
| Agent Orchestration | 5 | 3 | 0 | ✅ Yes |
| Research & Intelligence | 3 | 2 | 4 | ✅ Yes (partial) |
| Application Automation | 4 | 4 | 1 | ✅ Yes (partial) |
| Pipeline Management | 2 | 3 | 2 | ✅ Yes (partial) |
| User Communication | 5 | 3 | 0 | ✅ Yes |
| Enterprise & B2B | 2 | 5 | 2 | ❌ Post-MVP |
| Onboarding & Profile | 5 | 1 | 0 | ✅ Yes |

---

## Feature Requirements

### MVP Features (Weeks 1-4)

**Goal:** Prove core value prop - "Agent works for you"

#### F1: Zero-Setup Onboarding
| Attribute | Value |
|-----------|-------|
| **ID** | F1-ONBOARD |
| **Priority** | P0 |
| **Tier** | All |
| **Agent** | Core |

**Description:** User pastes LinkedIn URL and gets a complete profile in under 60 seconds.

**Acceptance Criteria:**
- [ ] User can paste LinkedIn public profile URL
- [ ] System extracts: name, headline, experience (last 5 roles), skills, education
- [ ] Profile populated within 60 seconds
- [ ] User can edit/correct any extracted field
- [ ] Alternative: Upload PDF resume for parsing
- [ ] Preference wizard launches after profile creation

#### F2: Preference Wizard
| Attribute | Value |
|-----------|-------|
| **ID** | F2-PREFS |
| **Priority** | P0 |
| **Tier** | All |
| **Agent** | Core |

**Description:** Quick setup flow to capture job preferences and deal-breakers.

**Acceptance Criteria:**
- [ ] Capture: target roles, locations, salary range, remote preference
- [ ] Capture deal-breakers: company size, industries to avoid, relocation limits
- [ ] For H1B users: visa type, expiry date, sponsor requirement toggle
- [ ] Employer blocklist (companies to never contact)
- [ ] Complete in <3 minutes
- [ ] Can modify preferences anytime from settings

#### F3: Daily Briefing System
| Attribute | Value |
|-----------|-------|
| **ID** | F3-BRIEFING |
| **Priority** | P0 |
| **Tier** | All |
| **Agent** | Orchestrator |

**Description:** Morning summary of all agent activity with clear action items.

**Acceptance Criteria:**
- [ ] Generated daily at user-configured time (default 8am local)
- [ ] Sections: New Matches, Actions Taken, Actions Pending Approval, Status Updates
- [ ] Each item shows WHAT and WHY (transparency mode)
- [ ] Delivered via email + in-app notification
- [ ] One-click actions from email (approve, reject, view details)
- [ ] Configurable frequency: daily, weekly, real-time

#### F4: Job Scout Agent
| Attribute | Value |
|-----------|-------|
| **ID** | F4-SCOUT |
| **Priority** | P0 |
| **Tier** | All |
| **Agent** | Research |

**Description:** Continuous monitoring of job boards for matching opportunities.

**Acceptance Criteria:**
- [ ] Monitors: LinkedIn, Indeed, Glassdoor, company career pages
- [ ] Match score (0-100) based on profile + preferences
- [ ] Respects deal-breakers (score = 0 if violated)
- [ ] Surfaces 10+ quality matches per week for active users
- [ ] De-duplicates across sources
- [ ] Shows match rationale ("85% match: skills align, salary in range, remote OK")

#### F5: Resume Agent
| Attribute | Value |
|-----------|-------|
| **ID** | F5-RESUME |
| **Priority** | P0 |
| **Tier** | Pro+ |
| **Agent** | Action |

**Description:** Auto-tailor resume for each job, optimized for ATS.

**Acceptance Criteria:**
- [ ] Creates tailored copy (never modifies master)
- [ ] Diff view: side-by-side comparison with changes highlighted
- [ ] Optimizes keywords for ATS parsing
- [ ] Maintains user's voice and style
- [ ] User can accept, reject, or edit tailored version
- [ ] Stores all versions with job association

#### F6: Pipeline Agent
| Attribute | Value |
|-----------|-------|
| **ID** | F6-PIPELINE |
| **Priority** | P0 |
| **Tier** | Pro+ |
| **Agent** | Tracking |

**Description:** Auto-track application status from email parsing.

**Acceptance Criteria:**
- [ ] Connects to user's email (Gmail OAuth, Outlook)
- [ ] Detects: application confirmations, interview requests, rejections
- [ ] Auto-creates pipeline entries for detected applications
- [ ] Status stages: Applied → Screening → Interview → Offer → Closed
- [ ] Manual override for any status
- [ ] Privacy: only parses job-related emails (keyword filtering)

#### F7: Emergency Brake
| Attribute | Value |
|-----------|-------|
| **ID** | F7-BRAKE |
| **Priority** | P0 |
| **Tier** | All |
| **Agent** | Core |

**Description:** Instant global pause for all agent activity.

**Acceptance Criteria:**
- [ ] One-click pause from any screen
- [ ] Stops all agent activity within 5 seconds
- [ ] Confirmation: "All agents paused. No actions will be taken."
- [ ] Resume requires explicit user action
- [ ] Audit log entry for pause/resume events

### Growth Features (Weeks 5-8)

**Goal:** Differentiate and monetize

#### F8: H1B Sponsor Database
| Attribute | Value |
|-----------|-------|
| **ID** | F8-H1B |
| **Priority** | P0 |
| **Tier** | H1B Pro |
| **Agent** | Research |

**Description:** Aggregated H1B sponsor intelligence with verification.

**Acceptance Criteria:**
- [ ] Data sources: H1BGrader, MyVisaJobs, USCIS public data
- [ ] Per company: approval rate, denial rate, LCA wage data, green card history
- [ ] Source attribution visible with freshness timestamp
- [ ] Sponsor reliability score (crowdsourced)
- [ ] Filter jobs by "verified sponsor only"
- [ ] Alert when new sponsor matches user's criteria

#### F9: Apply Agent
| Attribute | Value |
|-----------|-------|
| **ID** | F9-APPLY |
| **Priority** | P1 |
| **Tier** | Pro+ |
| **Agent** | Action |

**Description:** Submit applications with configurable autonomy.

**Acceptance Criteria:**
- [ ] L2 (Pro): Queues applications, user approves batch in morning briefing
- [ ] L3 (H1B Pro): Auto-applies within rules, user reviews after
- [ ] Never violates deal-breakers regardless of tier
- [ ] Attaches tailored resume + cover letter
- [ ] Tracks submission confirmation
- [ ] Rate limiting: max 10/day to prevent spam patterns

#### F10: Cover Letter Generator
| Attribute | Value |
|-----------|-------|
| **ID** | F10-COVER |
| **Priority** | P1 |
| **Tier** | Pro+ |
| **Agent** | Action |

**Description:** Personalized cover letters with company-specific references.

**Acceptance Criteria:**
- [ ] References specific job requirements
- [ ] Includes company-specific details (recent news, values)
- [ ] Maintains user's voice from writing samples
- [ ] Preview and edit before submission
- [ ] Multiple tone options: formal, conversational, enthusiastic

#### F11: Follow-up Agent
| Attribute | Value |
|-----------|-------|
| **ID** | F11-FOLLOWUP |
| **Priority** | P1 |
| **Tier** | Pro+ |
| **Agent** | Tracking |

**Description:** Draft and send follow-ups at optimal intervals.

**Acceptance Criteria:**
- [ ] Suggests follow-up at 5 days, 10 days post-application
- [ ] Detects rejection signals (no follow-up after "no")
- [ ] Draft for user approval (L2) or auto-send (L3)
- [ ] Personalized based on application context
- [ ] Stops after 2 follow-ups (configurable)

#### F12: Stealth Mode
| Attribute | Value |
|-----------|-------|
| **ID** | F12-STEALTH |
| **Priority** | P0 |
| **Tier** | Career Insurance |
| **Agent** | Core |

**Description:** Zero public footprint for passive job seekers.

**Acceptance Criteria:**
- [ ] No profile visible on any public surface
- [ ] Employer blocklist encrypted and enforced
- [ ] No "active on JobPilot" signals anywhere
- [ ] Stealth verification dashboard: shows what IS and ISN'T exposed
- [ ] Weekly digest instead of daily (less engagement = less risk)

### Vision Features (Weeks 9-12+)

**Goal:** Full autonomous job search

#### F13: Interview Intel Agent
| Attribute | Value |
|-----------|-------|
| **ID** | F13-INTEL |
| **Priority** | P2 |
| **Tier** | Pro+ |
| **Agent** | Research |

**Description:** Auto-generated interview prep briefings.

**Acceptance Criteria:**
- [ ] Company research: culture, recent news, challenges, competitors
- [ ] Interviewer research: LinkedIn, publications, speaking topics
- [ ] Common questions for role type
- [ ] STAR response suggestions based on user's experience
- [ ] Delivered 24 hours before scheduled interview

#### F14: Network Agent
| Attribute | Value |
|-----------|-------|
| **ID** | F14-NETWORK |
| **Priority** | P2 |
| **Tier** | H1B Pro |
| **Agent** | Action |

**Description:** Autonomous relationship warming and introduction requests.

**Acceptance Criteria:**
- [ ] Identifies warm paths to target companies (2nd degree connections)
- [ ] Drafts introduction request messages
- [ ] Engages with target contacts' content (likes, thoughtful comments)
- [ ] Tracks relationship temperature over time
- [ ] Human approval required for direct outreach

#### F15: Enterprise Admin Dashboard
| Attribute | Value |
|-----------|-------|
| **ID** | F15-ADMIN |
| **Priority** | P1 |
| **Tier** | Enterprise |
| **Agent** | - |

**Description:** Aggregate metrics and controls for HR admins.

**Acceptance Criteria:**
- [ ] Metrics: active users, applications sent, interviews scheduled, placements
- [ ] Per-employee autonomy level configuration
- [ ] Bulk onboarding via CSV upload
- [ ] At-risk employee alerts (low engagement)
- [ ] ROI reporting vs industry benchmarks
- [ ] PII detection alerts before any employee data leaves system

### Feature-to-Domain Mapping

| Feature | Primary Domain | Secondary Domains |
|---------|---------------|-------------------|
| F1 Zero-Setup Onboarding | Onboarding | - |
| F2 Preference Wizard | Onboarding | User Communication |
| F3 Daily Briefing | User Communication | Agent Orchestration |
| F4 Job Scout Agent | Research | Agent Orchestration |
| F5 Resume Agent | Application Automation | - |
| F6 Pipeline Agent | Pipeline Management | User Communication |
| F7 Emergency Brake | Agent Orchestration | User Communication |
| F8 H1B Sponsor Database | Research | - |
| F9 Apply Agent | Application Automation | Agent Orchestration |
| F10 Cover Letter Generator | Application Automation | - |
| F11 Follow-up Agent | Pipeline Management | Application Automation |
| F12 Stealth Mode | User Communication | - |
| F13 Interview Intel Agent | Research | - |
| F14 Network Agent | Research | Application Automation |
| F15 Enterprise Dashboard | Enterprise | All |

---

## Non-Functional Requirements

### NFR1: Performance

| Requirement | Target | Rationale |
|-------------|--------|-----------|
| **Page Load Time** | <2 seconds | Users expect snappy modern web apps |
| **Agent Response Time** | <30 seconds | Briefings and actions shouldn't feel slow |
| **LinkedIn Profile Parse** | <60 seconds | Zero-setup onboarding promise |
| **Resume Tailoring** | <45 seconds | Users waiting to review diff |
| **Job Match Scoring** | <5 seconds per job | Batch processing overnight acceptable |
| **Search/Filter** | <500ms | Pipeline and job list interactions |
| **Email Parsing** | <10 seconds per email | Background processing acceptable |

### NFR2: Scalability

| Requirement | Target | Rationale |
|-------------|--------|-----------|
| **Concurrent Users** | 10,000 DAU by Year 1 | Scale from 50 beta to 2,000+ paid |
| **Job Processing** | 100,000 jobs/day | Monitoring multiple boards at scale |
| **Application Queue** | 50,000 applications/day | Peak during Monday morning briefings |
| **H1B Data Volume** | 500,000+ company records | Comprehensive sponsor database |
| **Horizontal Scaling** | Auto-scale on demand | Handle traffic spikes (job market news) |

### NFR3: Availability & Reliability

| Requirement | Target | Rationale |
|-------------|--------|-----------|
| **Platform Uptime** | 99.5% | Job search is time-sensitive |
| **Scheduled Maintenance** | <4 hours/month | Weekend windows only |
| **Auto-Apply Success Rate** | >95% | Agent actions must be reliable |
| **Email Parsing Accuracy** | >90% | Status detection must be trustworthy |
| **Data Backup** | Daily with 30-day retention | User data is irreplaceable |
| **Disaster Recovery** | RTO <4 hours, RPO <1 hour | Business continuity |

### NFR4: Security

| Requirement | Target | Rationale |
|-------------|--------|-----------|
| **Authentication** | OAuth 2.0 + MFA option | Industry standard, user choice |
| **Data Encryption** | AES-256 at rest, TLS 1.3 in transit | Protect sensitive career data |
| **Employer Blocklist** | Encrypted, never plaintext | David's stealth mode requirement |
| **PII Handling** | GDPR/CCPA compliant | Legal requirement, trust building |
| **API Security** | Rate limiting, API keys, JWT tokens | Prevent abuse |
| **Audit Logging** | All agent actions logged immutably | Transparency mode requirement |
| **Penetration Testing** | Annual third-party audit | Enterprise requirement |
| **SOC 2 Type II** | By Year 1 | Enterprise sales requirement |

### NFR5: Privacy

| Requirement | Target | Rationale |
|-------------|--------|-----------|
| **Data Minimization** | Collect only what's needed | Privacy by design |
| **Email Access Scope** | Job-related emails only | User trust - no snooping |
| **Third-Party Sharing** | Never sell user data | Core value, not negotiable |
| **Data Portability** | Export all data on request | GDPR requirement |
| **Data Deletion** | Complete deletion within 30 days | Right to be forgotten |
| **Data Retention** | Applications: 2 years, Audit logs: 7 years, Inactive accounts: 1 year | Compliance + legal |
| **Stealth Verification** | Provable privacy for passive users | David's dealbreaker |

### NFR6: LLM & AI Constraints

| Requirement | Target | Rationale |
|-------------|--------|-----------|
| **LLM Cost per User** | <$6/month | Maintain 68%+ gross margin on Pro |
| **Model Selection** | GPT-3.5 for parsing, GPT-4 for quality | Cost optimization strategy |
| **Hallucination Prevention** | Ground in verified data only | Never fabricate jobs/companies |
| **Response Quality** | Human review for first 1000 users | Calibrate before full autonomy |
| **Fallback Handling** | Graceful degradation if LLM unavailable | Don't break user workflow |
| **Token Optimization** | Batch similar requests | Reduce API calls |

### NFR7: Compliance

| Requirement | Target | Rationale |
|-------------|--------|-----------|
| **GDPR** | Full compliance | EU users |
| **CCPA** | Full compliance | California users |
| **LinkedIn ToS** | No automation that violates ToS | Risk mitigation |
| **Job Board ToS** | Respect rate limits and terms | Sustainable scraping |
| **H1B Data Accuracy** | Source attribution required | Legal liability |
| **Accessibility** | WCAG 2.1 AA + quarterly audits | Inclusive design |

### NFR8: Observability

| Requirement | Target | Rationale |
|-------------|--------|-----------|
| **Application Monitoring** | Real-time dashboards | Ops visibility |
| **Error Tracking** | <1% error rate, alerts on spikes | Quality control |
| **Agent Activity Metrics** | Actions/hour, success rates | Agent performance tuning |
| **User Behavior Analytics** | Funnel analysis, feature adoption | Product iteration |
| **LLM Cost Tracking** | Per-user, per-feature breakdown | Margin protection |
| **Alerting** | PagerDuty integration | Incident response |

### NFR9: Internationalization (Future)

| Requirement | Target | Rationale |
|-------------|--------|-----------|
| **Language Support** | English first, Spanish/Mandarin Year 2 | Market expansion |
| **Currency** | USD first, multi-currency Year 2 | International pricing |
| **Time Zones** | User-local briefing times | Global user base |
| **Job Board Coverage** | US first, UK/Canada/India Year 2 | Market expansion |

### NFR Priority Matrix

| Category | MVP Critical | Growth | Vision |
|----------|--------------|--------|--------|
| Performance | ✅ Core targets | Optimize further | Sub-second |
| Scalability | 1,000 users | 10,000 users | 100,000 users |
| Availability | 99% | 99.5% | 99.9% |
| Security | Basic auth, encryption | MFA, SOC 2 prep | SOC 2 certified |
| Privacy | GDPR/CCPA basics | Stealth verification | Full audit trail |
| LLM Constraints | Cost tracking | Optimization | Custom models |
| Compliance | ToS compliance | Accessibility | Full audit |
| Observability | Basic monitoring | Full dashboards | Predictive |

---

## UX Requirements

### UX1: Core Design Principles

| Principle | Description | Application |
|-----------|-------------|-------------|
| **Agent-First, Not Tool-First** | Users supervise an agent, not operate a tool | Dashboard shows "what agent did" not "what you need to do" |
| **Transparency Over Magic** | Show reasoning, never black box | Every action shows WHAT and WHY |
| **Trust Through Control** | Users must feel in control at all times | Emergency brake, approval queues, deal-breakers |
| **Progressive Disclosure** | Show complexity only when needed | Simple by default, details on demand |
| **Calm Technology** | Respect user attention | Digest-based, not notification-heavy |

### UX2: Information Architecture

```
JobPilot
├── Home (Daily Briefing)
│   ├── Summary Cards
│   ├── Actions Pending Approval
│   ├── New Matches (preview)
│   └── Recent Activity Feed
├── Jobs
│   ├── Matched Jobs (scored list)
│   ├── Saved Jobs
│   ├── Job Detail + Agent Recommendation
│   └── Filters (location, salary, H1B, etc.)
├── Pipeline
│   ├── Kanban View (Applied → Interview → Offer)
│   ├── List View with filters
│   ├── Application Detail
│   └── Follow-up Queue
├── Documents
│   ├── Master Resume
│   ├── Tailored Versions (by job)
│   ├── Cover Letters
│   └── Diff Viewer
├── Settings
│   ├── Preferences & Deal-breakers
│   ├── Employer Blocklist
│   ├── Notification Settings
│   ├── Autonomy Level
│   ├── Stealth Mode (Career Insurance)
│   └── Account & Billing
└── [Enterprise Only] Admin Dashboard
    ├── Employee Overview
    ├── Aggregate Metrics
    ├── Per-Employee Config
    └── ROI Reports
```

### UX3: Key Interaction Patterns

#### Pattern: Daily Briefing

| Element | Behavior |
|---------|----------|
| **Delivery** | Email + in-app at user-configured time |
| **Structure** | Summary → Approvals Needed → New Matches → Activity |
| **Actions** | One-tap approve/reject from email |
| **Depth** | "View Details" expands inline, no page navigation |
| **Tone** | Conversational, agent speaking to user ("I found 3 great matches") |

#### Pattern: Approval Queue

| Element | Behavior |
|---------|----------|
| **Display** | Card-based, swipeable on mobile |
| **Context** | Shows job, tailored resume preview, agent rationale |
| **Actions** | Approve / Reject / Edit & Approve |
| **Batch** | "Approve All" for trusted users, with confirmation |
| **Undo** | 30-second undo window after approval |

#### Pattern: Job Match Card

| Element | Behavior |
|---------|----------|
| **Score** | Prominent 0-100 match score with color coding |
| **Rationale** | Expandable "Why this match?" section |
| **Deal-breakers** | Red flags if any filter nearly violated |
| **Actions** | Save / Dismiss / Apply Now / View Details |
| **H1B Badge** | "Verified Sponsor" badge with data freshness |

#### Pattern: Resume Diff View

| Element | Behavior |
|---------|----------|
| **Layout** | Side-by-side: Original | Tailored |
| **Highlighting** | Green = added, Red = removed, Yellow = modified |
| **Rationale** | Tooltip on each change explaining why |
| **Actions** | Accept All / Reject All / Edit Specific Section |
| **Revert** | One-click restore to master |

#### Pattern: Emergency Brake

| Element | Behavior |
|---------|----------|
| **Visibility** | Always visible in header/nav |
| **Activation** | Single tap, no confirmation (speed critical) |
| **Feedback** | Full-screen confirmation "All agents paused" |
| **Resume** | Requires explicit "Resume Agents" action |
| **Scope** | Pauses ALL agent activity immediately |

### UX4: Mobile-First Considerations

| Aspect | Requirement |
|--------|-------------|
| **Primary Use Case** | Review briefing during commute |
| **Touch Targets** | Minimum 44x44px |
| **Swipe Gestures** | Approve (right), Reject (left) on cards |
| **Offline** | Cache briefing for offline reading |
| **Push Notifications** | Interview scheduled, urgent approval needed |
| **Quick Actions** | iOS/Android notification actions |

### UX5: Tone & Voice

| Context | Tone | Example |
|---------|------|---------|
| **Briefing** | Friendly assistant | "Good morning! I found 5 new matches while you slept." |
| **Success** | Celebratory | "Interview scheduled! I've prepared a briefing for you." |
| **Approval Request** | Clear, respectful | "This role looks great. Ready to apply?" |
| **Error** | Honest, helpful | "I couldn't reach Indeed today. I'll try again tonight." |
| **Stealth Mode** | Reassuring | "You're invisible. Here's proof of what's protected." |
| **Enterprise** | Professional, warm | "We're here to support your transition." |

### UX6: Accessibility Requirements

| Requirement | Target |
|-------------|--------|
| **WCAG Level** | 2.1 AA compliance |
| **Screen Readers** | Full VoiceOver/TalkBack support |
| **Keyboard Navigation** | All actions keyboard-accessible |
| **Color Contrast** | 4.5:1 minimum ratio |
| **Motion** | Respect prefers-reduced-motion |
| **Focus Indicators** | Visible focus states |

### UX7: Visual Design Direction

| Element | Guideline |
|---------|-----------|
| **Style** | Clean, professional, trustworthy (not "startup playful") |
| **Colors** | Calm blues/greens, avoid aggressive reds except for errors |
| **Typography** | Highly readable, system fonts for performance |
| **Density** | Comfortable spacing, not cramped |
| **Icons** | Consistent icon family, meaningful not decorative |
| **Inspiration** | Linear (clarity), Superhuman (speed), Notion (flexibility) |

### UX8: Onboarding Flow

| Step | Screen | Goal |
|------|--------|------|
| 1 | Welcome | Value prop: "Your AI agent works 24/7" |
| 2 | LinkedIn Import | Paste URL or upload resume |
| 3 | Profile Review | Verify extracted data, make corrections |
| 4 | Preferences | Job types, locations, salary, deal-breakers |
| 5 | H1B (if applicable) | Visa type, expiry, sponsor requirement |
| 6 | Autonomy Level | Explain tiers, select starting level |
| 7 | First Briefing Preview | "Here's what tomorrow's briefing will look like" |
| 8 | Get Started | CTA to explore or wait for first briefing |

**Target:** Complete onboarding in <5 minutes

### UX9: Error & Empty States

| State | Design |
|-------|--------|
| **No matches yet** | Encouraging: "Your agent is searching. Check back tomorrow." |
| **Empty pipeline** | Actionable: "No applications yet. Review your matches?" |
| **Agent paused** | Clear status: "Agents paused. Resume to continue." |
| **API error** | Honest: "We hit a snag. Retrying automatically." |
| **No H1B data** | Helpful: "No sponsor data for this company yet. Know something? Tell us." |

---

## Technical Considerations

### Tech1: Existing Codebase Assets (Brownfield)

*From codebase analysis - 70% reusable*

| Component | Reuse Status | Notes |
|-----------|--------------|-------|
| **FastAPI Backend** | ✅ High | Modular endpoint design, CORS, health checks |
| **React Frontend** | ✅ High | Router, component patterns, form state |
| **LLM Client Abstraction** | ✅ High | OpenAI/Anthropic with fallback |
| **Dual-Model Strategy** | ✅ High | GPT-3.5 research → GPT-4 synthesis |
| **Web Scraper** | ✅ Medium | URL extraction, retry logic |
| **Error Handlers** | ✅ High | Async retry decorator, validation |
| **Session Cache** | ✅ High | Form persistence utility |
| **Monitoring/Alerts** | ✅ High | MetricsCollector, AlertManager |

### Tech2: New Infrastructure Required

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Database** | Supabase (PostgreSQL) | Managed, real-time, Row Level Security, fast setup |
| **Authentication** | Clerk | LinkedIn OAuth, MFA support, session management |
| **Background Jobs** | Celery + Redis | Agent task scheduling, retry logic |
| **Email Service** | SendGrid | Transactional emails, briefings |
| **File Storage** | Supabase Storage | Resume PDFs, documents |
| **Search** | PostgreSQL Full-Text + pgvector | Job matching, semantic search |
| **Hosting** | Vercel (FE) + Railway/Render (BE) | Fast deploys, auto-scaling |
| **Monitoring** | Sentry + PostHog | Error tracking + analytics |

### Tech3: Agent Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                        │
│  - Routes tasks to specialized agents                        │
│  - Manages state and context                                 │
│  - Enforces autonomy levels                                  │
│  - Generates daily briefings                                 │
└─────────────────────────────────────────────────────────────┘
         │           │           │           │           │
         ▼           ▼           ▼           ▼           ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ JOB SCOUT   │ │ RESUME      │ │ APPLY       │ │ PIPELINE    │ │ FOLLOW-UP   │
│ AGENT       │ │ AGENT       │ │ AGENT       │ │ AGENT       │ │ AGENT       │
│ (Research)  │ │ (Action)    │ │ (Action)    │ │ (Tracking)  │ │ (Tracking)  │
│             │ │             │ │             │ │             │ │             │
│ GPT-3.5     │ │ GPT-4       │ │ GPT-4       │ │ GPT-3.5     │ │ GPT-3.5     │
│ ~$0.30/user │ │ ~$1.50/user │ │ ~$1.00/user │ │ ~$0.50/user │ │ ~$0.20/user │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
         │           │           │           │           │
         ▼           ▼           ▼           ▼           ▼
┌─────────────────────────────────────────────────────────────┐
│                    SHARED MEMORY LAYER                       │
│  - User profile & preferences                                │
│  - Job history & interactions                                │
│  - Application pipeline state                                │
│  - Agent action audit log                                    │
└─────────────────────────────────────────────────────────────┘
```

### Tech4: Data Schema (Key Entities)

| Entity | Key Fields | Relationships |
|--------|------------|---------------|
| **User** | id, email, tier, autonomy_level, preferences_json | has_many: Applications, Documents, Matches |
| **Profile** | user_id, linkedin_data, skills[], experience[], education[] | belongs_to: User |
| **Job** | id, source, url, title, company, description, h1b_sponsor_status | has_many: Matches, Applications |
| **Match** | user_id, job_id, score, rationale, status (new/saved/dismissed) | belongs_to: User, Job |
| **Application** | user_id, job_id, status, applied_at, resume_version_id | belongs_to: User, Job |
| **Document** | user_id, type (resume/cover_letter), version, content, job_id | belongs_to: User |
| **AgentAction** | user_id, agent_type, action, rationale, status, timestamp | belongs_to: User |
| **H1BSponsor** | company_name, approval_rate, denial_rate, lca_data, sources[], updated_at | standalone |

### Tech5: API Design Principles

| Principle | Implementation |
|-----------|----------------|
| **RESTful** | Standard CRUD patterns for resources |
| **Versioned** | `/api/v1/` prefix for all endpoints |
| **Authenticated** | JWT tokens via Clerk |
| **Rate Limited** | Tier-based limits (Free: 100/hr, Pro: 1000/hr) |
| **Paginated** | Cursor-based pagination for lists |
| **Webhook-Ready** | Webhook endpoints for email provider callbacks |

### Tech6: LLM Cost Optimization Strategy

| Task | Model | Est. Cost/User/Month | Optimization |
|------|-------|---------------------|--------------|
| Profile parsing | GPT-3.5 | $0.10 | One-time per user |
| Job matching | GPT-3.5 + embeddings | $0.30 | Batch nightly |
| Resume tailoring | GPT-4 | $1.50 | On-demand, cached |
| Cover letters | GPT-4 → 3.5 hybrid | $0.80 | Template + customization |
| Email parsing | GPT-3.5 | $0.50 | Keyword pre-filter |
| Follow-ups | GPT-3.5 | $0.20 | Template-based |
| Briefing generation | GPT-3.5 | $0.30 | Structured summary |
| Orchestration | GPT-3.5 | $0.30 | Decision routing |
| **TOTAL** | Mixed | **~$5.00** | Target: <$6 |

### Tech7: Third-Party Integrations

| Integration | Purpose | Priority | Complexity |
|-------------|---------|----------|------------|
| **LinkedIn** | Profile import, job data | P0 | Medium (public scraping) |
| **Indeed** | Job listings | P0 | Medium (API or scraping) |
| **Glassdoor** | Job listings, company data | P1 | Medium |
| **Gmail/Outlook** | Email parsing for pipeline | P0 | High (OAuth) |
| **Google Calendar** | Interview sync | P2 | Medium |
| **H1BGrader** | Sponsor data | P0 (H1B tier) | Low (scraping) |
| **MyVisaJobs** | Sponsor data | P0 (H1B tier) | Low (scraping) |
| **USCIS** | Official H1B data | P1 | Medium (public data) |
| **Stripe** | Payments | P0 | Low |
| **SendGrid** | Transactional email | P0 | Low |

### Tech8: Security Implementation

| Layer | Implementation |
|-------|----------------|
| **Auth** | Clerk (OAuth 2.0, MFA, session management) |
| **API** | JWT validation, rate limiting, CORS |
| **Data** | Supabase RLS, encrypted blocklists |
| **Transport** | TLS 1.3 everywhere |
| **Secrets** | Environment variables, secret manager |
| **Audit** | Immutable action logs in database |
| **PII** | Redaction in logs, encrypted at rest |

### Tech9: Deployment Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Vercel     │     │  Railway/    │     │   Supabase   │
│  (Frontend)  │────▶│   Render     │────▶│  (Database)  │
│   React SPA  │     │  (Backend)   │     │  PostgreSQL  │
└──────────────┘     │   FastAPI    │     │   + Storage  │
                     └──────────────┘     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐     ┌──────────────┐
                     │    Redis     │     │   Celery     │
                     │   (Queue)    │◀───▶│  (Workers)   │
                     └──────────────┘     │  Agents run  │
                                          └──────────────┘
```

### Tech10: Migration Path from Existing Codebase

| Phase | Actions |
|-------|---------|
| **Week 1** | Add Supabase + Clerk, migrate auth |
| **Week 2** | Database schema, migrate from sessionStorage |
| **Week 3** | Agent framework scaffolding, orchestrator |
| **Week 4** | Job Scout + Resume agents, basic briefing |
| **Week 5-6** | Pipeline agent, email integration |
| **Week 7-8** | H1B data integration, Apply agent |

---

## Dependencies, Risks & Constraints

### Dep1: External Service Dependencies

| Dependency | Risk Level | Mitigation |
|------------|------------|------------|
| **OpenAI API** | Medium | Anthropic fallback implemented; cost monitoring |
| **LinkedIn Public Profiles** | High | ToS compliance; fallback to resume upload |
| **Indeed/Glassdoor** | Medium | Multiple job board sources; graceful degradation |
| **Gmail/Outlook OAuth** | Medium | Support both; manual pipeline update fallback |
| **Stripe** | Low | Industry standard; well-documented |
| **Supabase** | Low | Managed service; export capability |
| **Clerk** | Low | Managed auth; migration path exists |
| **H1B Data Sources** | Medium | Multiple sources; crowdsourced backup |

### Dep2: Feature Dependencies (Build Order)

```
Week 1-2: Foundation
├── Auth (Clerk) ─────────────────────────────┐
├── Database (Supabase) ──────────────────────┤
└── Profile Parser ───────────────────────────┘
                    │
                    ▼
Week 3-4: Core Agents
├── Orchestrator Agent ◄── requires: Auth, DB
├── Job Scout Agent ◄── requires: Orchestrator, Profile
├── Resume Agent ◄── requires: Orchestrator, Profile
└── Daily Briefing ◄── requires: Orchestrator, Email
                    │
                    ▼
Week 5-6: Pipeline
├── Email Integration ◄── requires: Auth (OAuth)
├── Pipeline Agent ◄── requires: Email, Orchestrator
└── Emergency Brake ◄── requires: Orchestrator
                    │
                    ▼
Week 7-8: Growth
├── H1B Database ◄── requires: DB, Scraping
├── Apply Agent ◄── requires: Resume Agent, Pipeline
├── Follow-up Agent ◄── requires: Pipeline, Email
└── Stealth Mode ◄── requires: Auth, Preferences
```

### Dep3: Assumptions

| Category | Assumption | Validation Plan |
|----------|------------|-----------------|
| **Market** | Job seekers want agent autonomy, not just tools | Beta user interviews, NPS surveys |
| **Technical** | LinkedIn public profiles remain scrapeable | Monitor ToS; build resume-upload fallback |
| **Technical** | LLM costs continue to decrease | Track costs monthly; adjust model mix |
| **Business** | $19-49 price points sustainable | A/B test pricing; monitor conversion |
| **User** | Users will trust AI to apply on their behalf | Start with L1-L2; earn L3 trust over time |
| **H1B** | H1B users will pay premium for sponsor data | Validate with H1B-focused beta cohort |

### Dep4: Constraints

| Constraint | Impact | Workaround |
|------------|--------|------------|
| **LinkedIn ToS** | Cannot automate actions on LinkedIn | Focus on job boards; manual LinkedIn actions |
| **Job Board Rate Limits** | Limited scraping frequency | Batch overnight; cache aggressively |
| **LLM Cost Budget** | <$6/user/month to maintain margins | Model optimization; caching; batching |
| **Small Team** | Limited engineering bandwidth | Prioritize ruthlessly; use managed services |
| **Brownfield Codebase** | Some refactoring required | Incremental migration; preserve working code |
| **GDPR/CCPA** | Data handling restrictions | Privacy by design; minimal data collection |

### Dep5: Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **LinkedIn blocks scraping** | Medium | High | Resume upload fallback; focus on job boards |
| **LLM costs exceed budget** | Medium | High | Aggressive model optimization; usage caps |
| **Users don't trust auto-apply** | Medium | High | Start conservative (L1-L2); earn trust gradually |
| **H1B data inaccurate** | Medium | High | Multi-source verification; user corrections |
| **Job board ToS violations** | Low | High | Respect rate limits; legal review |
| **Security breach** | Low | Critical | SOC 2 prep; penetration testing; encryption |
| **Competitor launches similar** | Medium | Medium | Speed to market; H1B data moat; UX quality |
| **Enterprise sales cycle too long** | Medium | Medium | Focus on B2C first; enterprise as expansion |

### Dep6: Open Questions

| Question | Owner | Decision Deadline |
|----------|-------|-------------------|
| Which job boards to prioritize after LinkedIn/Indeed? | Product | Week 2 |
| Self-hosted vs. managed Celery/Redis? | Engineering | Week 1 |
| H1B data: scrape vs. API vs. partnership? | Product | Week 3 |
| Enterprise pricing model (per-seat vs. flat)? | Business | Week 6 |
| Mobile app or responsive web only for MVP? | Product | Week 1 |
| Which LLM provider for fallback (Anthropic vs. others)? | Engineering | Week 1 |

### Dep7: Success Dependencies

| Milestone | Depends On | Risk if Delayed |
|-----------|------------|-----------------|
| **Beta Launch (Week 4)** | Auth, DB, Profile, Job Scout, Briefing | Delays all downstream |
| **First Paid Users (Week 8)** | Stripe, Resume Agent, Apply Agent | Revenue delay |
| **H1B Launch (Week 8)** | H1B data pipeline, verified accuracy | Premium tier delay |
| **Enterprise Pilot (Week 12)** | Admin dashboard, bulk onboarding, ROI reporting | B2B revenue delay |
