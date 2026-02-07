# Quality, Testing & DevOps Strategy

**Project:** JobPilot
**Domain:** AI Agent Platform - Quality Engineering
**Researched:** 2026-01-30
**Overall Confidence:** MEDIUM-HIGH

---

## Executive Summary

JobPilot presents a testing challenge that goes beyond typical web application quality assurance. The platform has an AI agent orchestration system with 5+ specialized agents producing non-deterministic outputs, tier-based autonomy levels that must be enforced as security boundaries, and high-stakes actions (auto-applying to jobs) where errors directly damage user trust and careers. The existing codebase already demonstrates solid test discipline -- Story 0-1 achieved 97.28% coverage with 120 tests using a well-structured pytest setup. The challenge ahead is extending this foundation to handle LLM output validation, agent behavioral testing, CI/CD for a multi-service architecture, and production observability.

The core tension: traditional deterministic testing cannot validate AI agent behavior, but sloppy probabilistic testing cannot protect tier-enforcement boundaries or deal-breaker violations. The strategy must combine strict deterministic testing for safety-critical paths (autonomy enforcement, deal-breaker compliance, emergency brake) with probabilistic/LLM-as-judge evaluation for agent output quality (resume tailoring, job matching, briefing generation).

---

## 1. Current Test Infrastructure Assessment

### What Exists (Story 0-1 Baseline)

| Aspect | Current State | Assessment |
|--------|--------------|------------|
| **Framework** | pytest 7.4.3 + pytest-asyncio 0.21.1 | Solid foundation |
| **Coverage Tool** | pytest-cov 4.1.0 | Standard, adequate |
| **Coverage Achieved** | 97.28% on Story 0-1 | Excellent baseline discipline |
| **Test Count** | ~120 tests | Well-decomposed by acceptance criteria |
| **Test Structure** | `backend/tests/unit/test_db/` | Organized by component |
| **Fixtures** | conftest.py with event_loop, mock_env_vars | Basic but functional |
| **Mocking** | pytest-mock 3.12.0, monkeypatch for env vars | Standard toolkit |
| **Test Data** | faker 20.0.3 | Available for synthetic data |
| **Timeouts** | pytest-timeout 2.2.0 | Good -- prevents hanging tests |

**Confidence: HIGH** -- directly verified from codebase files.

### Strengths of Current Approach

1. **Acceptance Criteria Mapping**: Tests are organized by AC (AC1-AC6), making traceability excellent. Each test class maps to a specific acceptance criterion.
2. **Parametrized Tests**: Good use of `@pytest.mark.parametrize` for testing all 8 models against common assertions (UUIDs, timestamps, soft-delete).
3. **Multi-Level Validation**: Tests validate at both the SQLAlchemy model level (metadata inspection) AND migration SQL file level (string parsing). This catches drift between models and migrations.
4. **Enum Completeness**: Every enum has a test asserting exact value sets, preventing silent additions/removals.

### Gaps to Address

| Gap | Impact | Priority |
|-----|--------|----------|
| **No integration tests with real DB** | SQLite in-memory only; PostgreSQL-specific features untested | HIGH |
| **No API endpoint tests** | FastAPI TestClient not used yet | HIGH |
| **No LLM/agent test infrastructure** | No mocks for LLM responses, no agent behavioral tests | HIGH |
| **No frontend tests** | No Jest/RTL/Playwright setup visible | MEDIUM |
| **No CI/CD pipeline** | No `.github/workflows/` directory exists | HIGH |
| **No security testing** | No Bandit, no SAST scanning | MEDIUM |
| **No performance benchmarks** | No baseline response time measurements | LOW (MVP) |

---

## 2. Testing Strategy for AI Agent Systems

### The Non-Determinism Problem

JobPilot's agents produce outputs that vary between runs even with identical inputs. A resume tailored for the same job posting will differ each time. A job match rationale will be worded differently. This breaks traditional `assert output == expected` testing.

**Confidence: HIGH** -- well-documented industry challenge, verified across multiple sources.

### Recommended Testing Pyramid for JobPilot

```
                    /\
                   /  \    E2E (Playwright)
                  /    \   - Critical user journeys
                 /------\  - Emergency brake flow
                /        \ - Onboarding happy path
               /  Agent   \
              /  Evals     \ LLM-as-Judge (DeepEval)
             /  (DeepEval)  \ - Resume quality scoring
            /                \ - Match rationale coherence
           /------------------\- Briefing completeness
          /                    \
         /   Integration Tests  \ FastAPI TestClient + real Supabase
        /   (Contract + API)     \ - API response formats
       /                          \ - RLS enforcement
      /----------------------------\- Agent contract interfaces
     /                              \
    /        Unit Tests (pytest)     \ Pure logic, deterministic
   /  Autonomy enforcement, cost      \
  /  tracking, deal-breaker logic,      \
 /  enum validation, schema validation    \
/------------------------------------------\
```

### Layer 1: Deterministic Unit Tests (pytest)

**What to test deterministically:**
- Tier enforcement logic (L0-L3 boundaries) -- MUST be hard pass/fail
- Deal-breaker filter logic -- MUST never allow violations
- Emergency brake state machine -- MUST stop within constraints
- LLM cost tracking calculations -- MUST stay under $6/user/month
- Data model validation (Pydantic schemas, enums)
- Encryption/decryption of blocklists

**Approach:** Standard pytest with mocked LLM responses. Use fixed seed data. Assert exact outcomes.

```python
# Example: Tier enforcement MUST be deterministic
def test_free_tier_cannot_auto_apply():
    """L0-L1 users must NEVER auto-apply. Hard failure."""
    user = create_user(tier="free")
    action = ApplyAction(job_id="123", user=user)
    with pytest.raises(TierViolationError):
        orchestrator.execute(action)

def test_deal_breaker_blocks_application():
    """Jobs violating deal-breakers get score=0. Hard failure."""
    user = create_user(deal_breakers={"min_salary": 80000})
    job = create_job(salary_max=60000)
    score = job_matcher.score(user, job)
    assert score == 0  # Not probabilistic -- must be exactly 0
```

### Layer 2: Agent Contract Tests (pytest)

**What to test:** Interface compliance between orchestrator and agents. Every agent MUST return `AgentOutput` with required fields.

```python
def test_agent_output_has_required_fields():
    """All agents must return rationale (transparency requirement)."""
    output = mock_agent.execute(task)
    assert output.rationale  # Non-empty string required
    assert 0 <= output.confidence <= 1
    assert isinstance(output.alternatives_considered, list)
```

### Layer 3: LLM Evaluation Tests (DeepEval)

**Recommendation: Use DeepEval** -- the leading pytest-native LLM evaluation framework.

**Confidence: MEDIUM-HIGH** -- verified via official docs and multiple 2026 sources. DeepEval has 50+ metrics, native pytest integration, and supports agent evaluation with tool-call validation.

**Installation:**
```bash
pip install deepeval
```

**Key metrics for JobPilot:**

| Agent | Metric | Threshold | Type |
|-------|--------|-----------|------|
| Resume Agent | G-Eval (resume quality) | 0.7 | Soft failure |
| Resume Agent | Faithfulness (no fabrication) | 0.9 | Hard failure |
| Job Scout | Answer Relevancy (match rationale) | 0.6 | Soft failure |
| Briefing Gen | Task Completion | 0.7 | Soft failure |
| Apply Agent | Tool Correctness (right tools called) | 0.9 | Hard failure |
| All Agents | Hallucination | 0.9 (inverse) | Hard failure |

**Soft Failure Strategy (from industry best practices):**

| Score Range | Action |
|-------------|--------|
| 0.0 - 0.5 | HARD FAIL -- blocks merge |
| 0.5 - 0.8 | SOFT FAIL -- merge allowed, but tracked. If >20% soft failures across suite, blocks merge |
| 0.8 - 1.0 | PASS |

```python
# Example: Resume Agent evaluation with DeepEval
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from deepeval.metrics import GEval, HallucinationMetric

def test_resume_tailoring_quality():
    test_case = LLMTestCase(
        input="Tailor resume for Senior Python Developer at Acme Corp",
        actual_output=resume_agent.tailor(user_profile, job_posting),
        expected_output="Resume emphasizing Python, FastAPI, leadership experience",
        context=["User has 5 years Python, 2 years FastAPI, led team of 4"]
    )
    # Quality is soft -- allow variation
    quality_metric = GEval(
        name="Resume Quality",
        criteria="Resume is tailored to job requirements, highlights relevant experience",
        threshold=0.7
    )
    # Fabrication is hard -- never invent experience
    hallucination_metric = HallucinationMetric(threshold=0.9)
    assert_test(test_case, [quality_metric, hallucination_metric])
```

### Layer 4: Integration Tests

**API contract testing with Schemathesis:**
```bash
pip install schemathesis
```
Auto-generates test cases from OpenAPI spec. Catches schema drift and unexpected error codes.

**Database integration tests:** Use a real Supabase test project (or local Supabase via Docker) rather than SQLite. PostgreSQL-specific features (JSONB, arrays, RLS policies) cannot be tested with SQLite.

### Layer 5: E2E Tests (Playwright)

**Critical flows to automate:**
1. Onboarding: LinkedIn URL paste -> profile extraction -> preference wizard
2. Emergency brake: Toggle pause -> verify all agents stop -> resume
3. Approval queue: Review pending actions -> approve/reject -> verify pipeline update
4. Briefing: Open daily briefing -> click through sections -> act on items

**Approach:** Use seeded/mocked agent backends for deterministic E2E tests. Real LLM calls in E2E are too slow and flaky.

---

## 3. CI/CD Pipeline Design

### Recommended: GitHub Actions

**Confidence: HIGH** -- standard for Python/FastAPI projects, well-documented, free for public repos, integrates with all target services.

No CI/CD exists yet (no `.github/workflows/` directory). This is a critical gap.

### Pipeline Architecture

```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  # Stage 1: Fast checks (< 2 min)
  lint-and-type:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install ruff mypy
      - run: ruff check backend/
      - run: mypy backend/app/ --ignore-missing-imports

  # Stage 2: Unit tests (< 5 min)
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r backend/requirements.txt
      - run: pytest backend/tests/unit/ -v --cov=backend/app --cov-report=xml
      - uses: codecov/codecov-action@v4

  # Stage 3: Quality gates (< 5 min)
  quality-gates:
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - run: pytest backend/tests/quality_gates/ -v
      # Includes: LLM cost budget, tier enforcement, security checks

  # Stage 4: Agent evals (< 10 min, requires OPENAI_API_KEY)
  agent-evals:
    runs-on: ubuntu-latest
    needs: unit-tests
    if: github.event_name == 'push'  # Skip on PR to save costs
    env:
      OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    steps:
      - run: deepeval test run backend/tests/evals/ --verbose

  # Stage 5: Integration tests (< 10 min)
  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    services:
      redis:
        image: redis:7
        ports: ['6379:6379']
    steps:
      - run: pytest backend/tests/integration/ -v

  # Stage 6: Security scan
  security:
    runs-on: ubuntu-latest
    steps:
      - run: pip install bandit safety
      - run: bandit -r backend/app/ -ll
      - run: safety check -r backend/requirements.txt
```

### Pipeline Stages Summary

| Stage | Duration | Trigger | Blocks Merge |
|-------|----------|---------|--------------|
| Lint + Type Check (ruff, mypy) | ~1 min | All PRs | Yes |
| Unit Tests + Coverage | ~3 min | All PRs | Yes (>90% threshold) |
| Quality Gates | ~3 min | All PRs | Yes |
| Agent Evals (DeepEval) | ~8 min | Push to main only | Soft (tracks score trends) |
| Integration Tests | ~5 min | All PRs | Yes |
| Security Scan (Bandit + Safety) | ~2 min | All PRs | Yes (high severity) |
| E2E Tests (Playwright) | ~10 min | Push to main only | Yes |

### Cost Consideration for Agent Evals in CI

Running DeepEval with LLM-as-judge costs money (OpenAI API calls). Mitigations:
- Run agent evals only on push to main, not every PR
- Use GPT-3.5-turbo as judge (cheaper than GPT-4)
- Cache eval results for unchanged agent code
- Set a monthly CI eval budget cap (~$50/month estimated)

### Recommended Tooling Swap

| Current | Recommended | Reason |
|---------|-------------|--------|
| flake8 + black | **ruff** | 10-100x faster, replaces both linter and formatter |
| No SAST | **bandit** | Python-specific security scanning |
| No dependency audit | **safety** or **pip-audit** | Catches known vulnerabilities |
| No commit hooks | **pre-commit** (already in deps) | Enforce locally before CI |

**Note:** `ruff` is the current standard Python linter/formatter as of 2026, replacing flake8+black+isort. It is written in Rust and dramatically faster.

**Confidence: HIGH** -- ruff is widely adopted, Bandit is OWASP-recommended for Python.

---

## 4. Monitoring & Observability Strategy

### Architecture Decision from PRD

The architecture document already specifies:
- OpenTelemetry from day one
- Sentry for error tracking
- PostHog for user analytics
- LLM cost tracking with per-user dashboards

### Recommended Stack

| Layer | Tool | Purpose | Confidence |
|-------|------|---------|------------|
| **Error Tracking** | Sentry (FastAPI integration) | Errors, performance, releases | HIGH |
| **Distributed Tracing** | OpenTelemetry -> Sentry OTLP | Agent execution traces, latency | HIGH |
| **Metrics** | Prometheus (already in deps) + Grafana Cloud | System metrics, custom dashboards | HIGH |
| **Celery Monitoring** | Flower (with auth proxy) | Worker health, task queues | HIGH |
| **User Analytics** | PostHog | Funnel analysis, feature adoption | MEDIUM |
| **LLM Cost Tracking** | Custom (Redis-backed, as designed) | Per-user, per-agent cost | HIGH |
| **Uptime Monitoring** | Better Uptime or UptimeRobot | 99.5% SLA verification | MEDIUM |
| **Log Aggregation** | Railway built-in + Sentry breadcrumbs | Centralized logs | MEDIUM |

### Sentry + FastAPI + OpenTelemetry Setup

As of 2026, Sentry recommends the newer OTLPIntegration for OpenTelemetry, which is simpler than the legacy SentrySpanProcessor approach.

```python
# backend/app/monitoring/tracing.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

sentry_sdk.init(
    dsn=os.environ["SENTRY_DSN"],
    integrations=[
        FastApiIntegration(),
        CeleryIntegration(),
    ],
    traces_sample_rate=0.2,  # 20% sampling for performance
    profiles_sample_rate=0.1,  # 10% profiling
    environment=os.environ.get("ENVIRONMENT", "development"),
)
```

**Confidence: HIGH** -- verified against Sentry official docs for FastAPI.

### Agent-Specific Observability

Critical metrics to track per agent:

| Metric | Alert Threshold | Why |
|--------|----------------|-----|
| Agent execution time | >30s (P95) | PRD NFR: <30s agent response |
| LLM tokens per request | >4000 tokens | Cost control |
| LLM cost per user/month | >$4.80 (80% of $6) | Margin protection |
| Agent error rate | >5% | Reliability |
| Emergency brake response time | >5s | Safety SLA |
| Auto-apply success rate | <95% | PRD NFR |
| Deal-breaker violation count | >0 | CRITICAL -- zero tolerance |

### Railway Monitoring Limitations

Railway provides basic logging but limited observability. As of 2026, teams with production reliability needs often find Railway's built-in monitoring insufficient.

**Recommendation:** Do NOT rely solely on Railway logging. Use Sentry + OpenTelemetry as primary observability. Railway logs are supplementary.

**Confidence: MEDIUM** -- based on WebSearch findings about Railway limitations.

---

## 5. Deployment Strategy

### Target Architecture

```
Frontend (Vercel) --> Backend API (Railway) --> Supabase (Hosted)
                          |
                     Celery Workers (Railway)
                          |
                     Redis (Railway)
```

### Deployment Pipeline

| Environment | Purpose | Deploy Trigger | URL Pattern |
|-------------|---------|---------------|-------------|
| **Local Dev** | Development | Manual | localhost:8000 / localhost:3000 |
| **Staging** | Pre-production testing | Push to `develop` | staging.jobpilot.app |
| **Production** | Live users | Push to `main` (after approval) | app.jobpilot.app |

### Railway Configuration

```toml
# railway.toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "backend/Dockerfile"

[deploy]
healthcheckPath = "/api/v1/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

### Deployment Checklist (Per Release)

1. All CI checks pass (lint, tests, security scan)
2. Agent evals show no score regression
3. Database migrations applied to staging first
4. Staging smoke tests pass
5. Production deploy with health check verification
6. Monitor error rate for 15 minutes post-deploy
7. Rollback plan confirmed (Railway supports instant rollback)

### Docker Strategy

No Dockerfile exists yet. Recommended:

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["gunicorn", "backend.app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

---

## 6. Security Testing Strategy

### Threat Model for JobPilot

| Asset | Threat | Impact | Mitigation |
|-------|--------|--------|------------|
| User credentials (Clerk) | Session hijacking | Account takeover | Clerk handles; verify JWT validation |
| API keys (OpenAI, etc.) | Exposure in logs/code | Financial loss, abuse | Env vars, Bandit SAST, .gitignore |
| Employer blocklist | Data breach | Career damage (stealth mode broken) | AES-256 encryption at rest |
| Resume/profile data | Unauthorized access | Privacy violation (GDPR) | Supabase RLS, row-level isolation |
| Email OAuth tokens | Token theft | Email access, pipeline manipulation | Encrypted storage, short-lived tokens |
| Agent actions | Tier escalation | Unauthorized auto-apply | Middleware enforcement, audit logging |
| H1B visa status | Unauthorized disclosure | Legal/career impact | Per-field access control, consent gates |

### Automated Security Testing

| Tool | Purpose | CI Integration | Priority |
|------|---------|---------------|----------|
| **Bandit** | Python SAST (hardcoded secrets, SQL injection, etc.) | Every PR | P0 |
| **Safety / pip-audit** | Known vulnerability scanning in dependencies | Every PR | P0 |
| **Schemathesis** | API fuzzing from OpenAPI spec | Weekly | P1 |
| **gitleaks** | Detect secrets committed to repo | Pre-commit hook | P0 |
| **OWASP ZAP** | Dynamic API security testing | Monthly (staging) | P2 |

### Security Tests to Write

```python
# backend/tests/quality_gates/test_security.py

def test_no_hardcoded_secrets():
    """Scan codebase for hardcoded API keys, passwords, tokens."""
    # Use bandit programmatically or regex patterns
    pass

def test_rls_enforces_user_isolation():
    """User A cannot access User B's applications."""
    # Requires real Supabase connection
    pass

def test_tier_escalation_blocked():
    """Free user cannot call Pro-only endpoints."""
    response = client.post("/api/v1/agents/apply", headers=free_user_headers)
    assert response.status_code == 403

def test_blocklist_encrypted_at_rest():
    """Employer blocklist is never stored in plaintext."""
    # Verify encryption in database
    pass

def test_agent_action_audit_logged():
    """Every agent action creates an immutable audit log entry."""
    pass

def test_emergency_brake_cannot_be_bypassed():
    """When brake is active, no agent action can execute."""
    pass
```

### OWASP API Security Top 10 Coverage

| Risk | JobPilot Exposure | Mitigation |
|------|-------------------|------------|
| **Broken Object Level Authorization** | HIGH (multi-tenant) | Supabase RLS + service-layer checks |
| **Broken Authentication** | MEDIUM (Clerk handles most) | Verify Clerk JWT validation, test MFA flows |
| **Broken Object Property Level Authorization** | HIGH (tier features) | `@require_tier` decorator on all endpoints |
| **Unrestricted Resource Consumption** | HIGH (LLM costs) | Rate limiting + per-user LLM budget caps |
| **Broken Function Level Authorization** | HIGH (admin endpoints) | Separate admin router with role checks |
| **Server Side Request Forgery** | MEDIUM (LinkedIn scraping) | URL allowlisting, no user-controlled URLs to internal services |
| **Security Misconfiguration** | MEDIUM | Automated config audits, no debug mode in prod |

**Confidence: HIGH** -- OWASP guidelines are authoritative and stable.

---

## 7. Test Infrastructure Recommendations

### Directory Structure (Aligned with Architecture)

```
backend/tests/
  conftest.py                    # Shared fixtures, factory imports
  factories/                     # Test data factories (factory_boy or custom)
    user_factory.py
    job_factory.py
    agent_output_factory.py
  mocks/
    mock_llm.py                  # Seeded LLM responses for deterministic tests
    mock_agents.py               # Deterministic agent mocks for E2E
  unit/
    test_db/                     # Schema, models (exists)
    test_agents/                 # Agent logic, tier enforcement
    test_services/               # Business logic
    test_core/                   # Cost tracker, encryption, etc.
  integration/
    test_api/                    # FastAPI TestClient tests
    test_agent_orchestration.py  # Multi-agent coordination
  contract/
    test_agent_contracts.py      # Agent interface compliance
    test_api_contracts.py        # Schemathesis API fuzzing
  evals/
    test_resume_quality.py       # DeepEval: resume tailoring
    test_match_relevancy.py      # DeepEval: job match scoring
    test_briefing_quality.py     # DeepEval: briefing generation
    test_hallucination.py        # DeepEval: anti-hallucination
  quality_gates/
    test_llm_cost_budget.py      # <$6/user/month simulation
    test_performance.py          # Response time thresholds
    test_security.py             # Security assertions
  e2e/                           # (or frontend/e2e/)
    specs/
      onboarding.spec.ts
      emergency_brake.spec.ts
      approval_flow.spec.ts
```

### Key Dependencies to Add

```txt
# Testing - LLM Evaluation
deepeval>=1.0.0

# Testing - API Contract
schemathesis>=3.0.0

# Testing - Factories
factory-boy>=3.3.0

# Security Testing
bandit>=1.7.0
safety>=3.0.0

# CI/CD Linting (replaces flake8+black)
ruff>=0.4.0

# Monitoring
sentry-sdk[fastapi,celery]>=2.0.0
opentelemetry-instrumentation-fastapi>=0.45b0
opentelemetry-instrumentation-celery>=0.45b0
```

### Coverage Targets

| Component | Target | Rationale |
|-----------|--------|-----------|
| Core safety logic (tiers, deal-breakers, brake) | 100% | Zero-defect required |
| Database models + migrations | 95%+ | Already at 97%, maintain |
| API endpoints | 90%+ | Contract compliance |
| Agent business logic | 85%+ | Complex but testable |
| Services layer | 85%+ | Business rules |
| Agent output quality (DeepEval) | Tracked, not gated at first | Build baseline before enforcing |

---

## 8. Roadmap Implications

### Phase Ordering for Quality Infrastructure

**Phase 1 (Foundation):** CI/CD pipeline + unit test expansion
- Set up GitHub Actions with lint, type check, unit tests
- Add Bandit security scanning
- Add gitleaks pre-commit hook
- Expand test factories and fixtures
- Rationale: Every subsequent phase benefits from CI/CD. Do this first.

**Phase 2 (Agent Framework):** Agent contract tests + mock infrastructure
- Create deterministic LLM mock layer
- Write tier enforcement tests (hard pass/fail)
- Write deal-breaker enforcement tests (zero tolerance)
- Set up agent contract interface tests
- Rationale: Agent logic must be testable before building agents.

**Phase 3 (Agent Implementation):** DeepEval integration + quality baselines
- Install and configure DeepEval
- Write initial eval tests for each agent
- Establish quality baselines (don't gate yet, just track)
- Rationale: Baseline must exist before enforcing quality gates.

**Phase 4 (Growth):** Integration tests + E2E + observability
- Sentry + OpenTelemetry instrumentation
- Playwright E2E for critical flows
- API contract testing with Schemathesis
- LLM cost budget CI gate activated
- Rationale: By this phase, enough functionality exists to test end-to-end.

**Phase 5 (Production):** Security hardening + monitoring dashboards
- OWASP ZAP dynamic testing against staging
- Grafana dashboards for agent performance
- LLM cost alerting (80% budget threshold)
- Deal-breaker violation monitoring (zero tolerance alerts)

### Research Flags for Phases

| Phase | Flag | Reason |
|-------|------|--------|
| Phase 2 | DEEPER RESEARCH NEEDED | How to mock LLM responses deterministically while preserving realistic agent behavior |
| Phase 3 | DEEPER RESEARCH NEEDED | DeepEval metric selection and threshold tuning requires experimentation |
| Phase 4 | Standard patterns | Playwright and Schemathesis are well-documented |
| Phase 5 | Standard patterns | Sentry/OTel setup is well-documented |

---

## 9. Confidence Assessment

| Area | Confidence | Reason |
|------|------------|--------|
| Current test infrastructure assessment | HIGH | Directly read from codebase |
| Pytest/unit test strategy | HIGH | Standard, well-established patterns |
| DeepEval recommendation | MEDIUM-HIGH | Verified via official docs + multiple 2026 sources, but not yet used in this codebase |
| CI/CD pipeline design | HIGH | Standard GitHub Actions patterns for FastAPI |
| Sentry + OTel setup | HIGH | Verified against official Sentry docs |
| Railway deployment | MEDIUM | WebSearch-based; Railway limitations noted by multiple sources |
| Security testing (OWASP) | HIGH | OWASP guidelines are authoritative |
| Soft failure thresholds | MEDIUM | Industry emerging practice, thresholds need tuning per project |

---

## 10. Open Questions

1. **DeepEval cost in CI**: What is the actual OpenAI API cost per eval run? Need to benchmark before committing to per-PR eval runs.
2. **Supabase local dev**: Should we use Supabase CLI local instance for integration tests, or a dedicated test project? Local is faster but may diverge from hosted behavior.
3. **Frontend test framework**: Architecture mentions Jest + RTL, but the frontend setup needs verification. Vitest may be a better choice if using Vite (as suggested by architecture).
4. **Agent mock fidelity**: How realistic do LLM mocks need to be for integration tests? Recorded responses (VCR-style) vs. templated responses vs. actual LLM calls with low temperature.
5. **Railway scaling limits**: At what user count does Railway's credit-based pricing become untenable? Need cost modeling before committing to Railway long-term.

---

## Sources

### Testing AI Agent Systems
- [How We Are Testing Our Agents in Dev](https://towardsdatascience.com/how-we-are-testing-our-agents-in-dev/) -- Towards Data Science
- [Evaluations for the Agentic World](https://medium.com/quantumblack/evaluations-for-the-agentic-world-c3c150f0dd5a) -- McKinsey/QuantumBlack
- [4 Frameworks to Test Non-Deterministic AI Agent Behavior](https://datagrid.com/blog/4-frameworks-test-non-deterministic-ai-agents) -- DataGrid
- [AI Agent Evaluation: 5 Lessons Learned The Hard Way](https://www.montecarlodata.com/blog-ai-agent-evaluation/) -- Monte Carlo Data
- [Beyond Traditional Testing: Non-Deterministic Software](https://dev.to/aws/beyond-traditional-testing-addressing-the-challenges-of-non-deterministic-software-583a) -- AWS/DEV
- [State of AI Agents](https://www.langchain.com/state-of-agent-engineering) -- LangChain

### LLM Evaluation Frameworks
- [DeepEval - The LLM Evaluation Framework](https://github.com/confident-ai/deepeval) -- GitHub
- [DeepEval Getting Started](https://deepeval.com/docs/getting-started) -- Official Docs
- [DeepEval Unit Testing in CI/CD](https://deepeval.com/docs/evaluation-unit-testing-in-ci-cd) -- Official Docs
- [LLM Testing in 2026: Top Methods and Strategies](https://www.confident-ai.com/blog/llm-testing-in-2024-top-methods-and-strategies) -- Confident AI
- [Testing for LLM Applications: A Practical Guide](https://langfuse.com/blog/2025-10-21-testing-llm-applications) -- Langfuse

### CI/CD & Deployment
- [FastAPI with GitHub Actions and GHCR](https://pyimagesearch.com/2024/11/11/fastapi-with-github-actions-and-ghcr-continuous-delivery-made-simple/) -- PyImageSearch
- [Deploy FastAPI on Railway](https://docs.railway.com/guides/fastapi) -- Railway Docs
- [Railway Hosting Explained: Limitations in 2026](https://kuberns.com/blogs/post/railway-hosting-explained/) -- Kuberns
- [Deploy FastAPI + Celery on Railway](https://railway.com/deploy/fastapi-celery-beat-worker-flower) -- Railway

### Monitoring & Observability
- [Sentry FastAPI Integration](https://docs.sentry.io/platforms/python/integrations/fastapi/) -- Sentry Official Docs
- [Sentry OTLP Integration](https://docs.sentry.io/platforms/python/integrations/otlp/) -- Sentry Official Docs
- [OpenTelemetry FastAPI Instrumentation](https://pypi.org/project/opentelemetry-instrumentation-fastapi/) -- PyPI

### Security
- [OWASP API Security Project](https://owasp.org/www-project-api-security/) -- OWASP
- [REST Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html) -- OWASP
- [Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html) -- OWASP
