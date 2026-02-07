---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
status: 'complete'
completedAt: '2026-01-25'
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/analysis/brainstorming-session-2026-01-25.md'
  - 'docs/project-structure.md'
  - 'docs/codebase-analysis.md'
workflowType: 'architecture'
project_name: 'JobPilot'
user_name: 'bala'
date: '2026-01-25'
---

# Architecture Decision Document - JobPilot

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

---

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**

JobPilot requires a sophisticated multi-agent AI system coordinating 5+ specialized agents:
- **Orchestrator Agent**: Central coordinator, state management, briefing generation
- **Job Scout Agent**: Continuous job board monitoring, matching algorithm
- **Resume Agent**: On-demand tailoring with diff view, ATS optimization
- **Pipeline Agent**: Email parsing, status detection, auto-tracking
- **Apply Agent**: Autonomous submission with tier-based approval gates

Key functional domains: Agent Orchestration (8 reqs), Research (9 reqs), Application Automation (9 reqs), Pipeline Management (7 reqs), User Communication (9 reqs), Enterprise (9 reqs), Onboarding (6 reqs).

**Non-Functional Requirements:**

| Category | Key Constraints |
|----------|-----------------|
| Performance | <30s agent response, <60s profile parse, <2s page load |
| Scalability | 10,000 DAU, 100K jobs/day, 50K applications/day |
| Reliability | 99.5% uptime, >95% auto-apply success rate |
| Security | OAuth 2.0, AES-256, encrypted blocklists, SOC 2 by Year 1 |
| Privacy | GDPR/CCPA, stealth mode, data minimization |
| Cost | <$6 LLM cost/user/month for 68%+ gross margin |

**Scale & Complexity:**

- Primary domain: Full-stack SaaS with AI agent orchestration
- Complexity level: High (multi-agent coordination, real-time control)
- Estimated architectural components: 18-22

### Technical Constraints & Dependencies

**Brownfield Constraints:**
- Existing FastAPI backend (modular, reusable)
- Existing React frontend (router, component patterns)
- Existing LLM client abstraction (OpenAI/Anthropic fallback)
- Existing dual-model processing strategy

**External Dependencies:**
- OpenAI/Anthropic APIs for LLM (critical path)
- LinkedIn public profiles for onboarding
- Job boards (Indeed, Glassdoor) for job data
- Gmail/Outlook OAuth for pipeline tracking
- H1B data sources (H1BGrader, MyVisaJobs, USCIS)
- Stripe for payments

**Compliance Constraints:**
- LinkedIn ToS: No automation on LinkedIn platform
- Job Board ToS: Rate limits, terms compliance
- H1B Data: Source attribution required

### Cross-Cutting Concerns Identified

| Concern | Impact | Architectural Response |
|---------|--------|----------------------|
| **Agent Orchestration** | All features | Central orchestrator pattern, shared memory |
| **Autonomy Enforcement** | All agent actions | Middleware/decorator pattern, tier validation |
| **Audit Logging** | Transparency requirement | Event sourcing, immutable log store |
| **LLM Cost Tracking** | Margin protection | Per-request tagging, usage aggregation |
| **Privacy/Stealth** | Passive users | Encrypted data, no public footprint |
| **Graceful Degradation** | Reliability | Fallbacks, queue-based retry |

---

## Starter Template Evaluation

*Enhanced with Party Mode insights from Winston (Architect), Amelia (Developer), Murat (Test Architect), and Mary (Analyst)*

### Primary Technology Domain

Full-stack SaaS with AI agent orchestration - brownfield extension of existing FastAPI + React codebase.

### Brownfield Foundation (No New Starter Needed)

This project extends an existing codebase with 70% reusable patterns:
- **Backend**: FastAPI 0.104.1, Python 3.9+
- **Frontend**: React 18.2, TailwindCSS 3.3, React Router 6
- **LLM Integration**: OpenAI/Anthropic SDK with fallback pattern

### New Technology Additions

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Database** | Supabase (PostgreSQL) | Managed, RLS, real-time, fast setup |
| **Auth** | Clerk | LinkedIn OAuth, MFA, session management |
| **Background Jobs** | Celery + Redis | Scheduled tasks, batch processing |
| **Agent Coordination** | Redis pub/sub + flags | Real-time control, emergency brake |
| **Agent Framework** | Custom + `langchain-core` only | Tier-based autonomy needs custom logic |
| **React State** | TanStack Query + Zustand | Server state caching + lightweight UI state |
| **Email** | SendGrid | Transactional, briefings |
| **Testing** | pytest + Playwright + Schemathesis | Full coverage, E2E, API contracts |

### Architectural Decisions from Technology Selection

**Language & Runtime:**
- Python 3.9+ (backend) - async support, LLM SDKs
- TypeScript strict mode (frontend) - type safety for agent responses

**Agent Architecture:**
- Custom orchestrator for L0-L3 autonomy enforcement
- `langchain-core` only (~2MB) - NOT full langchain package (~50MB)
  - `ChatOpenAI`, `ChatAnthropic` (model wrappers)
  - `PromptTemplate` (prompt management)
  - `PydanticOutputParser` (structured output)
  - Cost tracking callbacks
- Shared memory via PostgreSQL for agent coordination
- **Required output schema:**
  ```python
  class AgentOutput(BaseModel):
      action: str
      rationale: str  # REQUIRED - shown to user for transparency
      confidence: float
      alternatives_considered: list[str]
  ```

**Emergency Brake Implementation:**
- Checkpoint-based pause using Redis flag
- Agents check `paused:{user_id}` at each logical step
- Not true instant-stop, but sufficient for MVP (no action >30s)
```python
class BaseAgent:
    def execute(self, task):
        for step in task.steps:
            if self.is_paused():  # Check Redis flag
                raise AgentPausedException()
            self.run_step(step)
```

**Briefing Reliability Strategy:**
- Primary: Celery scheduled task at 8am user-local
- Fallback: SendGrid webhook trigger if no briefing by 8:15am
- Dead letter queue for failed briefings with on-call alerts
- Graceful degradation: "Lite briefing" from cache if agents down

**State Management:**
- TanStack Query for server state (briefings, jobs, pipeline)
- Zustand for UI state (emergency brake, modals)
- Redis pub/sub for real-time agent control signals

**Testing Strategy:**

| Layer | Tool | Purpose |
|-------|------|---------|
| Backend Unit | pytest + pytest-asyncio | Standard FastAPI testing |
| Agent Contract | pytest | Orchestrator ↔ Agent interface tests |
| Autonomy Tests | pytest | Explicit L0-L3 enforcement tests |
| Cost Simulation | pytest | CI test: verify <$6/user/month |
| API Contract | Schemathesis | Auto-generate from OpenAPI |
| Frontend Unit | Jest + RTL | Component testing |
| E2E | Playwright | User journey testing |

**Critical Test Example:**
```python
def test_llm_cost_under_budget(mock_user_month_activity):
    """Simulate 1 month of typical user activity - MUST pass in CI"""
    total_cost = simulate_user_month(mock_user_month_activity)
    assert total_cost < 6.00, f"LLM cost ${total_cost} exceeds $6 budget"
```

**Note:** No project initialization command needed - extending existing codebase.

---

## Core Architectural Decisions

*Enhanced with Party Mode insights from Winston (Architect), Amelia (Developer), Murat (Test Architect), and Mary (Analyst)*

### 1. Data Architecture

#### Decision: Hybrid Schema (Relational + JSONB)

**Approach:**
- Relational tables for structured entities (users, jobs, applications, contacts)
- JSONB columns for flexible agent outputs and evolving schemas
- Soft-delete pattern for compliance (applications, contacts retain audit trail)

**Schema Strategy:**
```sql
-- Structured relational data
CREATE TABLE applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    job_id UUID REFERENCES jobs(id),
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,  -- Soft delete
    deleted_by UUID,         -- Party Mode: WHO deleted
    deletion_reason TEXT,    -- Party Mode: WHY deleted
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Flexible agent outputs with versioning
CREATE TABLE agent_outputs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type VARCHAR(50) NOT NULL,
    user_id UUID REFERENCES users(id),
    schema_version INTEGER DEFAULT 1,  -- Party Mode: Schema versioning
    output JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Three-Layer Caching:**

| Layer | Technology | Purpose | Invalidation Trigger |
|-------|------------|---------|---------------------|
| L1 | Redis | Hot data, session state | TTL + explicit invalidation on write |
| L2 | Materialized Views | Aggregated metrics, leaderboards | Scheduled refresh (5min) + on-demand |
| L3 | TanStack Query | Frontend server state | Stale-while-revalidate + mutation invalidation |

**Party Mode Enhancements:**
1. ✅ Added `schema_version` field to all JSONB columns for migration paths
2. ✅ Documented cache invalidation triggers explicitly in table above
3. ✅ Added `deleted_by` and `deletion_reason` for compliance audit trail
4. ✅ Will add `jsonschema` validation tests for agent outputs (see Testing section)

---

### 2. Auth & Security Architecture

#### Decision: Clerk + Supabase RLS + Abstraction Layer

**Authentication Flow:**
```
User → Clerk (OAuth/MFA) → JWT → Supabase RLS → Data
```

**Authorization Model:**
```python
# Tier + Feature Flags pattern
TIER_FEATURES = {
    "free": {
        "can_draft": True,
        "can_auto_apply": False,
        "max_applications_day": 5,
        "h1b_data": False
    },
    "pro": {
        "can_draft": True,
        "can_auto_apply": True,
        "approval_required": True,
        "max_applications_day": 50,
        "h1b_data": False
    },
    "h1b_pro": {
        "can_draft": True,
        "can_auto_apply": True,
        "approval_required": False,
        "max_applications_day": 100,
        "h1b_data": True
    },
    "career_insurance": {
        "can_draft": True,
        "can_auto_apply": True,
        "approval_required": False,
        "max_applications_day": 20,
        "h1b_data": False,
        "passive_mode": True
    }
}

# Party Mode: Abstraction layer for future migration
class AuthProvider(ABC):
    @abstractmethod
    async def get_user(self, token: str) -> User: ...
    @abstractmethod
    async def validate_session(self, session_id: str) -> bool: ...

class ClerkAuthProvider(AuthProvider):
    """Current implementation - can swap for self-hosted later"""
    ...
```

**Row-Level Security (RLS):**
```sql
-- Users can only see their own data
CREATE POLICY user_isolation ON applications
    FOR ALL
    USING (user_id = auth.uid());

-- Party Mode: Development bypass with safeguards
CREATE POLICY dev_bypass ON applications
    FOR ALL
    USING (
        current_setting('app.environment', true) = 'development'
        AND current_setting('app.rls_bypass', true) = 'true'
    );
```

**Stealth Mode Encryption:**
- Blocklists encrypted at rest with AES-256
- Encryption key rotation every 90 days
- Audit log for encryption operations (SOC 2 compliance)

**Party Mode Enhancements:**
1. ✅ Created `AuthProvider` abstraction layer for future self-hosted option
2. ✅ Added development mode RLS bypass with environment safeguards
3. ✅ Will add automated tier boundary penetration tests
4. ✅ Documented SSO/SAML upgrade path (Clerk Enterprise tier)
5. ✅ Added encryption-at-rest audit logging for blocklists

---

### 3. API & Communication Architecture

#### Decision: REST + WebSockets + Versioned API

**API Structure:**
```
/api/v1/                    # Versioned from day one (Party Mode)
├── /auth/*                 # Authentication endpoints
├── /users/*                # User management
├── /jobs/*                 # Job CRUD + search
├── /applications/*         # Application pipeline
├── /agents/*               # Agent control
│   ├── POST /agents/pause  # Emergency brake
│   ├── POST /agents/resume
│   └── GET /agents/status
├── /briefings/*            # Daily briefings
└── /approvals/*            # Approval queue
```

**WebSocket Channels:**
```typescript
// Real-time agent updates
ws://api/v1/ws/agents/{user_id}

// Events:
// - agent.started
// - agent.step_completed
// - agent.paused
// - agent.completed
// - agent.error
// - briefing.generating  // Party Mode: Status visibility
// - briefing.ready
```

**Emergency Brake State Machine:**
```
                    ┌─────────────┐
                    │   RUNNING   │
                    └──────┬──────┘
                           │ brake_pulled
                           ▼
                    ┌─────────────┐
          ┌─────────│   PAUSING   │─────────┐
          │         └──────┬──────┘         │
          │                │                │
    in_flight_timeout      │ all_clear      │ in_flight_failed
          │                │                │
          ▼                ▼                ▼
    ┌───────────┐   ┌─────────────┐   ┌───────────┐
    │  TIMEOUT  │   │   PAUSED    │   │  PARTIAL  │
    │  (manual) │   │   (clean)   │   │  (review) │
    └───────────┘   └─────────────┘   └───────────┘
```

**Optimistic Update Pattern:**
```typescript
// Approval queue with rollback UX (Party Mode)
const approveAction = useMutation({
  mutationFn: approveAgentAction,
  onMutate: async (actionId) => {
    // Optimistic update
    await queryClient.cancelQueries(['approvals']);
    const previous = queryClient.getQueryData(['approvals']);
    queryClient.setQueryData(['approvals'], (old) =>
      old.map(a => a.id === actionId ? {...a, status: 'approved'} : a)
    );
    return { previous };
  },
  onError: (err, actionId, context) => {
    // Rollback with user notification
    queryClient.setQueryData(['approvals'], context.previous);
    toast.error('Approval failed - action rolled back');
  },
  onSettled: () => {
    queryClient.invalidateQueries(['approvals']);
  }
});
```

**Briefing Reliability with User Visibility:**
```python
# Party Mode: User-visible briefing status
async def generate_briefing(user_id: str):
    await publish_status(user_id, "briefing.generating", {"eta_seconds": 45})

    try:
        briefing = await orchestrator.generate_briefing(user_id)
        await publish_status(user_id, "briefing.ready", {"briefing_id": briefing.id})
    except BriefingTimeout:
        # Fallback to lite briefing
        lite = await generate_lite_briefing(user_id)
        await publish_status(user_id, "briefing.lite_ready", {
            "briefing_id": lite.id,
            "reason": "Full briefing delayed - showing cached summary"
        })
        await notify_ops("Briefing timeout", user_id)
```

**Party Mode Enhancements:**
1. ✅ Documented emergency brake state machine with in-flight handling
2. ✅ Designed optimistic update rollback UX pattern
3. ✅ Versioned API from day one (`/api/v1/`)
4. ✅ Added briefing generation status visibility to users
5. ✅ Defined retry/fallback notifications for failed briefings

---

### 4. Frontend Architecture

#### Decision: TanStack Query + Zustand + Custom Agent Hooks

**State Management Split:**

| State Type | Tool | Examples |
|------------|------|----------|
| Server State | TanStack Query | Jobs, applications, briefings, agent outputs |
| UI State | Zustand | Modals, emergency brake toggle, form drafts |
| Agent State | Custom Hook | Real-time agent status, WebSocket integration |

**Custom Agent State Hook:**
```typescript
// Party Mode: Dedicated hook for agent coordination
function useAgentState(userId: string) {
  const [agentStatus, setAgentStatus] = useState<AgentStatus>('idle');
  const [currentStep, setCurrentStep] = useState<string | null>(null);
  const queryClient = useQueryClient();

  useEffect(() => {
    const ws = new WebSocket(`${WS_URL}/agents/${userId}`);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case 'agent.started':
          setAgentStatus('running');
          break;
        case 'agent.step_completed':
          setCurrentStep(data.step);
          // Invalidate relevant queries
          queryClient.invalidateQueries(['applications']);
          break;
        case 'agent.paused':
          setAgentStatus('paused');
          break;
        case 'agent.completed':
          setAgentStatus('idle');
          queryClient.invalidateQueries(['briefings']);
          break;
      }
    };

    return () => ws.close();
  }, [userId, queryClient]);

  return { agentStatus, currentStep };
}
```

**Runtime Validation with Zod:**
```typescript
// Party Mode: Don't trust backend blindly
import { z } from 'zod';

const AgentOutputSchema = z.object({
  action: z.string(),
  rationale: z.string().min(1), // REQUIRED
  confidence: z.number().min(0).max(1),
  alternatives_considered: z.array(z.string())
});

type AgentOutput = z.infer<typeof AgentOutputSchema>;

// In API layer
async function fetchAgentOutput(id: string): Promise<AgentOutput> {
  const response = await api.get(`/agents/outputs/${id}`);
  return AgentOutputSchema.parse(response.data); // Runtime validation
}
```

**Approval Queue UI Design:**
```typescript
// Party Mode: Prominently display confidence + alternatives
function ApprovalCard({ action }: { action: PendingAction }) {
  return (
    <Card>
      <CardHeader>
        <Badge variant={getConfidenceBadge(action.confidence)}>
          {Math.round(action.confidence * 100)}% confident
        </Badge>
        <h3>{action.action}</h3>
      </CardHeader>

      <CardBody>
        {/* WHY is as visible as WHAT */}
        <Section title="Why this action?">
          <p className="text-lg">{action.rationale}</p>
        </Section>

        <Section title="Alternatives considered">
          <ul>
            {action.alternatives_considered.map(alt => (
              <li key={alt}>{alt}</li>
            ))}
          </ul>
        </Section>
      </CardBody>

      <CardFooter>
        <Button variant="approve" onClick={() => approve(action.id)}>
          Approve
        </Button>
        <Button variant="reject" onClick={() => reject(action.id)}>
          Reject
        </Button>
        <Button variant="modify" onClick={() => openModify(action.id)}>
          Modify & Approve
        </Button>
      </CardFooter>
    </Card>
  );
}
```

**Party Mode Enhancements:**
1. ✅ Created `useAgentState` custom hook for agent coordination
2. ✅ Added `zod` runtime validation for agent outputs
3. ✅ Will implement seeded mock agents for deterministic E2E tests
4. ✅ Designed approval UI to prominently display confidence + alternatives

---

### 5. Infrastructure Architecture

#### Decision: Vercel + Railway + Kubernetes Migration Path

**MVP Infrastructure:**

```
┌─────────────────────────────────────────────────────────┐
│                      Vercel                              │
│  ┌─────────────────────────────────────────────────┐    │
│  │              React Frontend                      │    │
│  │         (Static + Edge Functions)               │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                      Railway                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   FastAPI    │  │    Celery    │  │    Redis     │  │
│  │   Backend    │  │   Workers    │  │   (Cache +   │  │
│  │              │  │              │  │    Queue)    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                     Supabase                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  PostgreSQL  │  │   Auth       │  │   Realtime   │  │
│  │  (with RLS)  │  │   (backup)   │  │   (optional) │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**Kubernetes Migration Path (Party Mode):**

| Trigger | Migration Action |
|---------|-----------------|
| >5000 DAU | Evaluate K8s for agent workers |
| Custom autoscaling needed | Migrate Celery workers to K8s |
| Enterprise on-prem request | Full K8s deployment option |
| Cost optimization (>$5K/mo) | Self-managed K8s cluster |

**Migration Checklist:**
- [ ] Containerize all services (Docker)
- [ ] Create Helm charts for each service
- [ ] Implement K8s-native job scheduling (replace Celery)
- [ ] Set up horizontal pod autoscaler for agent workers
- [ ] Migrate from Railway Redis to managed Redis (ElastiCache)

**Celery Task Management:**
```python
# Party Mode: Heartbeats + zombie cleanup
from celery import Celery
from celery.signals import task_prerun, task_postrun

app = Celery('jobpilot')

# Task timeout configuration
app.conf.task_time_limit = 300  # Hard limit: 5 minutes
app.conf.task_soft_time_limit = 240  # Soft limit: 4 minutes

# Heartbeat configuration
app.conf.worker_send_task_events = True
app.conf.task_send_sent_event = True

@app.task(bind=True, max_retries=3)
def agent_task(self, user_id: str, task_type: str, payload: dict):
    try:
        # Heartbeat every 30 seconds
        with heartbeat_context(self, interval=30):
            return execute_agent_task(user_id, task_type, payload)
    except SoftTimeLimitExceeded:
        # Graceful shutdown
        save_partial_state(user_id, task_type)
        raise

# Zombie task cleanup (runs every 5 minutes)
@app.task
def cleanup_zombie_tasks():
    """Find and terminate tasks without heartbeat for >2 minutes"""
    stale_tasks = find_stale_tasks(threshold_minutes=2)
    for task in stale_tasks:
        app.control.revoke(task.id, terminate=True)
        notify_ops(f"Zombie task terminated: {task.id}")
```

**Observability Stack:**
```python
# Party Mode: OpenTelemetry from day one
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Initialize tracing
tracer = trace.get_tracer(__name__)

# Instrument frameworks
FastAPIInstrumentor.instrument()
CeleryInstrumentor().instrument()

# Agent execution tracing
@tracer.start_as_current_span("agent_execute")
async def execute_agent(agent_type: str, task: AgentTask):
    span = trace.get_current_span()
    span.set_attribute("agent.type", agent_type)
    span.set_attribute("user.id", task.user_id)

    for i, step in enumerate(task.steps):
        with tracer.start_as_current_span(f"step_{i}") as step_span:
            step_span.set_attribute("step.name", step.name)
            result = await run_step(step)
            step_span.set_attribute("step.success", result.success)

    return result
```

**LLM Cost Dashboard:**
```python
# Party Mode: Real-time cost tracking with alerts
class LLMCostTracker:
    def __init__(self, monthly_budget: float = 6.0):
        self.monthly_budget = monthly_budget
        self.alert_threshold = 0.8  # Alert at 80%

    async def track_request(self, user_id: str, model: str, tokens: int, cost: float):
        await redis.hincrby(f"llm_cost:{user_id}:{current_month()}", "total", int(cost * 100))

        # Check budget
        current_cost = await self.get_user_cost(user_id)
        if current_cost > self.monthly_budget * self.alert_threshold:
            await self.send_budget_alert(user_id, current_cost)

    async def get_cost_dashboard(self) -> dict:
        """Ops dashboard - real-time cost visibility"""
        return {
            "total_cost_today": await self.get_total_cost(period="day"),
            "total_cost_month": await self.get_total_cost(period="month"),
            "users_over_80_pct": await self.get_users_near_budget(),
            "projected_month_end": await self.project_month_end_cost(),
            "cost_by_agent": await self.get_cost_breakdown_by_agent()
        }
```

**Party Mode Enhancements:**
1. ✅ Documented Kubernetes migration path with triggers
2. ✅ Implemented Celery task heartbeats + zombie cleanup
3. ✅ Added OpenTelemetry distributed tracing from day one
4. ✅ Built real-time LLM cost dashboard with 80% budget alerts

---

### Architectural Decisions Summary

| Category | Decision | Key Technologies |
|----------|----------|-----------------|
| **Data** | Hybrid relational + JSONB with versioning | PostgreSQL, Redis, TanStack Query |
| **Auth** | Clerk with abstraction layer + RLS | Clerk, Supabase RLS, JWT |
| **API** | Versioned REST + WebSockets | FastAPI, WebSockets, /api/v1/ |
| **Frontend** | TanStack Query + Zustand + Custom Hooks | React, Zod, TypeScript |
| **Infrastructure** | Vercel + Railway → K8s path | Celery, Redis, OpenTelemetry |

**Party Mode Enhancements Applied:** 22 total across all categories

---

## Implementation Patterns & Consistency Rules

*18 conflict points addressed with comprehensive enforcement guidelines*

### Pattern Categories Defined

**Critical Conflict Points Identified:** 18 areas where AI agents could make different choices

| Category | Conflicts Addressed |
|----------|-------------------|
| Database Naming | 7 (tables, columns, PKs, FKs, indexes, constraints, JSONB) |
| API Naming | 5 (endpoints, path params, query params, headers, versions) |
| Code Naming | 6 (files, classes, functions, variables, constants, private) |
| Structure | 4 (test location, component org, file structure, config) |
| API Format | 3 (response wrapper, error format, data exchange) |
| Communication | 4 (event naming, agent output, state management) |

---

### Naming Patterns

#### Database Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Tables | snake_case, plural | `applications`, `job_matches`, `agent_outputs` |
| Columns | snake_case | `user_id`, `created_at`, `job_title` |
| Primary Keys | `id` (UUID) | `id UUID PRIMARY KEY DEFAULT gen_random_uuid()` |
| Foreign Keys | `{table_singular}_id` | `user_id`, `job_id`, `application_id` |
| Indexes | `idx_{table}_{columns}` | `idx_applications_user_id`, `idx_jobs_status_created` |
| Constraints | `{table}_{type}_{columns}` | `applications_fk_user`, `jobs_check_status` |
| JSONB Fields | snake_case | `agent_output`, `metadata`, `preferences` |

```sql
-- ✅ CORRECT
CREATE TABLE applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    job_id UUID REFERENCES jobs(id),
    status VARCHAR(50) NOT NULL,
    agent_output JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_applications_user_id ON applications(user_id);

-- ❌ WRONG
CREATE TABLE Application (
    ApplicationId UUID PRIMARY KEY,
    userId UUID,
    JobID UUID,
    Status VARCHAR(50)
);
```

#### API Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Endpoints | Plural nouns, lowercase | `/api/v1/jobs`, `/api/v1/applications` |
| Path Parameters | snake_case in URL | `/api/v1/users/{user_id}/applications` |
| Query Parameters | snake_case | `?status=pending&sort_by=created_at` |
| Headers | Kebab-case with X- prefix for custom | `X-Request-Id`, `X-User-Tier` |
| Versions | URL prefix | `/api/v1/`, `/api/v2/` |

```python
# ✅ CORRECT
@router.get("/api/v1/jobs/{job_id}/applications")
async def get_job_applications(job_id: UUID, status: Optional[str] = None):
    ...

# ❌ WRONG
@router.get("/api/v1/getJobApplications/{jobId}")
async def getJobApplications(jobId: UUID):
    ...
```

#### Code Naming Conventions

**Python (Backend):**

| Element | Convention | Example |
|---------|------------|---------|
| Files | snake_case | `job_scout_agent.py`, `resume_service.py` |
| Classes | PascalCase | `JobScoutAgent`, `ResumeService` |
| Functions | snake_case | `get_matching_jobs()`, `tailor_resume()` |
| Variables | snake_case | `user_id`, `job_matches`, `agent_output` |
| Constants | SCREAMING_SNAKE_CASE | `MAX_RETRIES`, `DEFAULT_TIMEOUT` |
| Private | Leading underscore | `_internal_method()`, `_cached_value` |

**TypeScript (Frontend):**

| Element | Convention | Example |
|---------|------------|---------|
| Files (components) | PascalCase | `ApprovalCard.tsx`, `JobList.tsx` |
| Files (utilities) | camelCase | `useAgentState.ts`, `apiClient.ts` |
| Components | PascalCase | `ApprovalCard`, `BriefingPanel` |
| Functions/Hooks | camelCase | `useAgentState()`, `fetchJobs()` |
| Variables | camelCase | `userId`, `jobMatches`, `agentOutput` |
| Constants | SCREAMING_SNAKE_CASE | `API_BASE_URL`, `MAX_RETRIES` |
| Types/Interfaces | PascalCase | `AgentOutput`, `JobMatch`, `UserPreferences` |

```typescript
// ✅ CORRECT
interface AgentOutput {
  action: string;
  rationale: string;
  confidence: number;
  alternativesConsidered: string[];
}

const useAgentState = (userId: string) => { ... }

// ❌ WRONG
interface agent_output {
  Action: string;
  rationale: string;
}

const use_agent_state = (user_id: string) => { ... }
```

---

### Structure Patterns

#### Project Organization

```
jobpilot/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app entry
│   │   ├── models.py                  # Pydantic models (shared)
│   │   ├── config.py                  # App configuration
│   │   │
│   │   ├── api/                       # API routes by domain
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── jobs.py
│   │   │   │   ├── applications.py
│   │   │   │   ├── agents.py
│   │   │   │   ├── briefings.py
│   │   │   │   └── approvals.py
│   │   │   └── deps.py                # Shared dependencies
│   │   │
│   │   ├── agents/                    # Agent implementations
│   │   │   ├── __init__.py
│   │   │   ├── base.py                # BaseAgent class
│   │   │   ├── orchestrator.py
│   │   │   ├── job_scout.py
│   │   │   ├── resume_agent.py
│   │   │   ├── pipeline_agent.py
│   │   │   └── apply_agent.py
│   │   │
│   │   ├── services/                  # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── job_service.py
│   │   │   ├── application_service.py
│   │   │   ├── briefing_service.py
│   │   │   └── h1b_service.py
│   │   │
│   │   ├── core/                      # Shared utilities
│   │   │   ├── __init__.py
│   │   │   ├── llm_clients.py
│   │   │   ├── error_handlers.py
│   │   │   ├── cost_tracker.py
│   │   │   └── security.py
│   │   │
│   │   └── db/                        # Database
│   │       ├── __init__.py
│   │       ├── connection.py
│   │       ├── models.py              # SQLAlchemy models
│   │       └── migrations/
│   │
│   ├── tests/                         # All backend tests
│   │   ├── __init__.py
│   │   ├── conftest.py                # Shared fixtures
│   │   ├── unit/
│   │   │   ├── test_agents.py
│   │   │   ├── test_services.py
│   │   │   └── test_cost_tracker.py
│   │   ├── integration/
│   │   │   ├── test_api_jobs.py
│   │   │   └── test_agent_orchestration.py
│   │   └── contract/
│   │       └── test_agent_contracts.py
│   │
│   ├── celery_app.py                  # Celery configuration
│   ├── requirements.txt
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   │   ├── index.tsx
│   │   ├── App.tsx
│   │   │
│   │   ├── components/                # Shared UI components
│   │   │   ├── ui/                    # Base UI (buttons, cards, etc.)
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Card.tsx
│   │   │   │   └── index.ts
│   │   │   └── layout/                # Layout components
│   │   │       ├── Header.tsx
│   │   │       ├── Sidebar.tsx
│   │   │       └── index.ts
│   │   │
│   │   ├── features/                  # Feature modules
│   │   │   ├── jobs/
│   │   │   │   ├── components/
│   │   │   │   │   ├── JobCard.tsx
│   │   │   │   │   └── JobList.tsx
│   │   │   │   ├── hooks/
│   │   │   │   │   └── useJobs.ts
│   │   │   │   ├── api/
│   │   │   │   │   └── jobsApi.ts
│   │   │   │   └── index.ts
│   │   │   │
│   │   │   ├── agents/
│   │   │   │   ├── components/
│   │   │   │   │   ├── AgentStatus.tsx
│   │   │   │   │   └── EmergencyBrake.tsx
│   │   │   │   ├── hooks/
│   │   │   │   │   └── useAgentState.ts
│   │   │   │   └── index.ts
│   │   │   │
│   │   │   ├── approvals/
│   │   │   ├── briefings/
│   │   │   └── pipeline/
│   │   │
│   │   ├── hooks/                     # Shared hooks
│   │   │   ├── useAuth.ts
│   │   │   └── useWebSocket.ts
│   │   │
│   │   ├── services/                  # API client layer
│   │   │   ├── apiClient.ts
│   │   │   └── websocketClient.ts
│   │   │
│   │   ├── stores/                    # Zustand stores
│   │   │   ├── uiStore.ts
│   │   │   └── index.ts
│   │   │
│   │   ├── types/                     # TypeScript types
│   │   │   ├── api.ts
│   │   │   ├── agents.ts
│   │   │   └── index.ts
│   │   │
│   │   └── utils/                     # Utilities
│   │       ├── formatters.ts
│   │       └── validators.ts
│   │
│   ├── __tests__/                     # Frontend tests
│   │   ├── components/
│   │   └── features/
│   │
│   ├── e2e/                           # Playwright E2E tests
│   │   ├── fixtures/
│   │   └── specs/
│   │
│   └── package.json
│
└── docs/
    ├── architecture.md
    ├── api-reference.md
    └── agent-contracts.md
```

---

### Format Patterns

#### API Response Format

**Success Response (Wrapped):**

```json
{
  "data": { ... } | [ ... ],
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-01-25T10:30:00Z",
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total": 150,
      "total_pages": 8
    }
  }
}
```

**Implementation:**

```python
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional, List

T = TypeVar('T')

class PaginationMeta(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int

class ResponseMeta(BaseModel):
    request_id: str
    timestamp: datetime
    pagination: Optional[PaginationMeta] = None

class ApiResponse(BaseModel, Generic[T]):
    data: T
    meta: ResponseMeta
```

#### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable error message",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ],
    "request_id": "uuid"
  }
}
```

**Error Codes:**

| Code | HTTP Status | Usage |
|------|-------------|-------|
| `VALIDATION_ERROR` | 400 | Input validation failed |
| `UNAUTHORIZED` | 401 | Authentication required |
| `FORBIDDEN` | 403 | Tier/permission denied |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | State conflict (e.g., already applied) |
| `RATE_LIMITED` | 429 | Too many requests |
| `AGENT_ERROR` | 500 | Agent execution failed |
| `LLM_ERROR` | 502 | LLM provider error |
| `SERVICE_UNAVAILABLE` | 503 | Temporary outage |

#### Data Exchange Formats

| Data Type | JSON Format | Example |
|-----------|-------------|---------|
| Dates | ISO 8601 string | `"2026-01-25T10:30:00Z"` |
| UUIDs | String | `"550e8400-e29b-41d4-a716-446655440000"` |
| Money | Integer cents | `1999` (for $19.99) |
| Booleans | true/false | `true`, `false` |
| Nulls | null | `null` (never omit) |
| Enums | String | `"pending"`, `"approved"` |

**JSON Field Naming:**
- API responses: `camelCase` (frontend-friendly)
- Database/internal: `snake_case` (Python-friendly)
- Auto-convert at API boundary using Pydantic aliases

---

### Communication Patterns

#### Event Naming (Dot Notation)

**Event Hierarchy:**

```
{domain}.{entity}.{action}

Examples:
- agent.orchestrator.started
- agent.job_scout.job_matched
- agent.resume.tailoring_complete
- briefing.daily.generated
- approval.action.pending
- pipeline.application.status_changed
```

**Event Payload Structure:**

```python
class EventPayload(BaseModel):
    event_type: str                    # e.g., "agent.job_scout.job_matched"
    event_id: UUID
    timestamp: datetime
    user_id: UUID
    data: dict                         # Event-specific payload
    metadata: dict = {}                # Optional context
```

#### Agent Output Format (Extended)

```python
class AgentOutput(BaseModel):
    # Core fields (required)
    action: str
    rationale: str                     # REQUIRED - shown to user
    confidence: float                  # 0.0 to 1.0
    alternatives_considered: list[str]

    # Extended fields (for tracking)
    agent_id: str                      # e.g., "job_scout", "resume_agent"
    execution_time_ms: int
    tokens_used: int
    model_used: str                    # e.g., "gpt-4", "gpt-3.5-turbo"

    # Metadata
    schema_version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

#### State Management Patterns

**Zustand Store Pattern:**

```typescript
// Minimal UI state in Zustand
interface UIState {
  isEmergencyBrakeActive: boolean;
  activeModal: string | null;

  // Actions (verb prefix)
  activateEmergencyBrake: () => void;
  deactivateEmergencyBrake: () => void;
  openModal: (modalId: string) => void;
  closeModal: () => void;
}
```

**TanStack Query Pattern:**

```typescript
// Query keys follow [domain, entity, params] pattern
const jobKeys = {
  all: ['jobs'] as const,
  lists: () => [...jobKeys.all, 'list'] as const,
  list: (filters: JobFilters) => [...jobKeys.lists(), filters] as const,
  details: () => [...jobKeys.all, 'detail'] as const,
  detail: (id: string) => [...jobKeys.details(), id] as const,
};
```

---

### Process Patterns

#### Error Handling Pattern

**Backend:**
- Use `@async_error_handler` decorator with fallback values
- Distinguish recoverable vs non-recoverable errors
- Queue recoverable errors for retry

**Frontend:**
- Error boundaries at feature level
- Toast notifications for user-facing errors
- Automatic retry for transient failures (up to 3 times)

#### Loading State Pattern

| State | Variable Name | Description |
|-------|---------------|-------------|
| Initial load | `isLoading` | First fetch, no data |
| Refetching | `isFetching` | Background refresh, has stale data |
| Submitting | `isSubmitting` | Form/action in progress |
| Processing | `isProcessing` | Long-running operation |

**UI Pattern:**
- Skeleton for initial load
- Subtle spinner for refetch (non-blocking)
- Disabled state + spinner for submissions

---

### Enforcement Guidelines

**All AI Agents MUST:**

1. ✅ Follow naming conventions exactly - no exceptions
2. ✅ Use the wrapped API response format for all endpoints
3. ✅ Include `rationale` in every agent output
4. ✅ Use dot notation for all event names
5. ✅ Place tests in the designated test directories
6. ✅ Use feature folders for domain-specific components
7. ✅ Convert snake_case ↔ camelCase at API boundaries only
8. ✅ Follow the error response format exactly
9. ✅ Use ISO 8601 for all date/time values
10. ✅ Include `schema_version` in all JSONB outputs

**Pattern Enforcement:**

| Method | Tool | When |
|--------|------|------|
| Linting | ESLint + Ruff | Pre-commit hook |
| Type checking | TypeScript strict + mypy | Pre-commit + CI |
| API validation | Schemathesis | CI on every PR |
| Naming check | Custom lint rules | CI |
| Test location | CI directory check | CI |

---

### Pattern Examples

**Good Examples:**

```python
# ✅ Database: snake_case plural table
CREATE TABLE job_matches (...)

# ✅ API: plural REST endpoint
GET /api/v1/applications/{application_id}

# ✅ Python: snake_case function
async def get_matching_jobs(user_id: UUID) -> list[Job]:

# ✅ TypeScript: camelCase variables, PascalCase components
const jobMatches = useJobs(filters);
<JobCard job={job} />
```

**Anti-Patterns:**

```python
# ❌ Mixed case in database
CREATE TABLE JobMatches (UserId UUID...)

# ❌ Verb in REST endpoint
GET /api/v1/getApplications

# ❌ camelCase in Python
def getMatchingJobs(userId):

# ❌ snake_case in TypeScript
const job_matches = use_jobs(filters);
```

---

## Project Structure & Boundaries

*Enhanced with Party Mode insights from Winston (Architect), Amelia (Developer), Murat (Test Architect), and Mary (Analyst) - 15 enhancements applied*

### Requirements to Architecture Mapping

| Domain (from PRD) | Primary Location | Secondary Touches |
|-------------------|-----------------|-------------------|
| **Agent Orchestration** (8 reqs) | `backend/app/agents/` | `frontend/features/agents/` |
| **Research & Intelligence** (9 reqs) | `backend/app/services/research/` | `frontend/features/jobs/` |
| **Application Automation** (9 reqs) | `backend/app/agents/apply_agent.py` | `frontend/features/pipeline/` |
| **Pipeline Management** (7 reqs) | `backend/app/services/pipeline/` | `frontend/features/pipeline/` |
| **User Communication** (9 reqs) | `backend/app/services/briefing/` | `frontend/features/briefings/` |
| **Enterprise Features** (9 reqs) | `backend/app/services/enterprise/` | `frontend/features/admin/` |
| **Onboarding** (6 reqs) | `backend/app/services/onboarding/` | `frontend/features/onboarding/` |

### Complete Project Directory Structure

```
jobpilot/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                     # Main CI pipeline
│   │   ├── deploy-staging.yml         # Staging deployment
│   │   └── deploy-prod.yml            # Production deployment
│   ├── CODEOWNERS
│   └── pull_request_template.md
│
├── .husky/
│   ├── pre-commit                     # Lint + type check
│   └── commit-msg                     # Commit message validation
│
├── contracts/                         # [Party Mode] API contracts
│   ├── openapi.yaml                   # OpenAPI 3.0 spec (source of truth)
│   └── pact/                          # Consumer-driven contracts
│       └── frontend-backend.json
│
├── fixtures/                          # [Party Mode] Shared test fixtures
│   ├── users.json                     # Mock user data
│   ├── jobs.json                      # Mock job data
│   ├── applications.json              # Mock application data
│   └── agent_outputs.json             # Mock agent outputs
│
├── env/                               # [Party Mode] Environment templates
│   ├── .env.example                   # Base template
│   ├── .env.development               # Dev defaults
│   └── .env.test                      # Test defaults
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI entry point
│   │   ├── config.py                  # Settings from env vars
│   │   ├── models.py                  # Shared Pydantic models
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py                # Dependency injection
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── router.py          # v1 API router aggregation
│   │   │       ├── schemas/           # [Party Mode] Co-located schemas
│   │   │       │   ├── __init__.py
│   │   │       │   ├── auth.py
│   │   │       │   ├── jobs.py
│   │   │       │   ├── applications.py
│   │   │       │   └── agents.py
│   │   │       ├── auth.py            # POST /auth/login, /auth/logout
│   │   │       ├── users.py           # /users/* endpoints
│   │   │       ├── jobs.py            # /jobs/* endpoints
│   │   │       ├── applications.py    # /applications/* endpoints
│   │   │       ├── agents.py          # /agents/* (pause, resume, status)
│   │   │       ├── briefings.py       # /briefings/* endpoints
│   │   │       ├── approvals.py       # /approvals/* endpoints
│   │   │       ├── pipeline.py        # /pipeline/* endpoints
│   │   │       ├── h1b.py             # /h1b/* endpoints (H1B Pro only)
│   │   │       ├── webhooks/          # [Party Mode] External callbacks
│   │   │       │   ├── __init__.py
│   │   │       │   ├── gmail.py       # Gmail OAuth callback
│   │   │       │   ├── outlook.py     # Outlook OAuth callback
│   │   │       │   └── stripe.py      # Stripe webhooks
│   │   │       └── admin/
│   │   │           ├── __init__.py
│   │   │           ├── users.py       # Admin user management
│   │   │           └── metrics.py     # Admin dashboards
│   │   │
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                # BaseAgent class + AgentOutput schema
│   │   │   ├── orchestrator.py        # Central coordinator
│   │   │   ├── core/                  # [Party Mode] Core agents (all tiers)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── job_scout.py       # Job matching agent
│   │   │   │   └── pipeline_agent.py  # Email parsing, status tracking
│   │   │   ├── pro/                   # [Party Mode] Pro tier agents
│   │   │   │   ├── __init__.py
│   │   │   │   ├── resume_agent.py    # Resume tailoring agent
│   │   │   │   └── apply_agent.py     # Application submission agent
│   │   │   ├── h1b/                   # [Party Mode] H1B Pro agents
│   │   │   │   ├── __init__.py
│   │   │   │   └── h1b_agent.py       # H1B research agent
│   │   │   └── contracts/
│   │   │       ├── __init__.py
│   │   │       └── agent_interface.py # Agent contract definitions
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── job_service.py         # Job CRUD + search
│   │   │   ├── application_service.py # Application management
│   │   │   ├── user_service.py        # User profile management
│   │   │   │
│   │   │   ├── briefing/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── briefing_service.py    # Briefing generation
│   │   │   │   ├── briefing_scheduler.py  # Celery scheduling
│   │   │   │   └── templates/             # Briefing templates
│   │   │   │
│   │   │   ├── research/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── company_service.py     # Company research
│   │   │   │   ├── h1b_service.py         # H1B sponsor data
│   │   │   │   └── salary_service.py      # Salary intelligence
│   │   │   │
│   │   │   ├── pipeline/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── email_parser.py        # Email parsing
│   │   │   │   ├── status_detector.py     # Application status detection
│   │   │   │   └── pipeline_service.py    # Pipeline management
│   │   │   │
│   │   │   ├── onboarding/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── linkedin_parser.py     # LinkedIn profile parsing
│   │   │   │   ├── resume_parser.py       # Resume parsing
│   │   │   │   └── onboarding_service.py  # Onboarding orchestration
│   │   │   │
│   │   │   └── enterprise/
│   │   │       ├── __init__.py
│   │   │       ├── team_service.py        # Team management
│   │   │       └── analytics_service.py   # Enterprise analytics
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── llm/                   # [Party Mode] LLM-related code
│   │   │   │   ├── __init__.py
│   │   │   │   ├── clients.py         # OpenAI/Anthropic wrappers
│   │   │   │   ├── config.py          # Model selection
│   │   │   │   └── cost_tracker.py    # LLM cost tracking
│   │   │   ├── auth/                  # [Party Mode] Auth-related code
│   │   │   │   ├── __init__.py
│   │   │   │   ├── security.py        # Encryption, stealth mode
│   │   │   │   ├── tier_enforcement.py # L0-L3 autonomy enforcement
│   │   │   │   └── feature_flags.py   # [Party Mode] Feature flag definitions
│   │   │   ├── infra/                 # [Party Mode] Infrastructure code
│   │   │   │   ├── __init__.py
│   │   │   │   ├── events.py          # Event publishing utilities
│   │   │   │   └── error_handlers.py  # Error classes + decorators
│   │   │   └── web_scraper.py         # URL extraction, content cleaning
│   │   │
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── connection.py          # Supabase connection
│   │   │   ├── models.py              # SQLAlchemy models
│   │   │   ├── repositories/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── user_repo.py
│   │   │   │   ├── job_repo.py
│   │   │   │   ├── application_repo.py
│   │   │   │   └── agent_output_repo.py
│   │   │   └── migrations/
│   │   │       └── versions/
│   │   │
│   │   └── monitoring/
│   │       ├── __init__.py
│   │       ├── alerts.py              # AlertManager + channels
│   │       ├── metrics.py             # MetricsCollector
│   │       └── tracing.py             # OpenTelemetry setup
│   │
│   ├── celery_app.py                  # Celery configuration
│   ├── celery_tasks/
│   │   ├── __init__.py
│   │   ├── briefing_tasks.py          # Daily briefing generation
│   │   ├── agent_tasks.py             # Background agent execution
│   │   ├── cleanup_tasks.py           # Zombie task cleanup
│   │   └── h1b_tasks.py               # H1B data refresh
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py                # Shared fixtures (imports from /fixtures)
│   │   ├── factories/
│   │   │   ├── __init__.py
│   │   │   ├── user_factory.py
│   │   │   └── job_factory.py
│   │   ├── mocks/
│   │   │   ├── __init__.py
│   │   │   ├── mock_llm.py            # Seeded LLM mock
│   │   │   └── mock_agents.py         # Deterministic agent mocks
│   │   ├── unit/
│   │   │   ├── test_agents/
│   │   │   │   ├── test_base_agent.py
│   │   │   │   ├── test_job_scout.py
│   │   │   │   └── test_orchestrator.py
│   │   │   ├── test_services/
│   │   │   │   ├── test_job_service.py
│   │   │   │   └── test_briefing_service.py
│   │   │   └── test_core/
│   │   │       ├── test_cost_tracker.py
│   │   │       └── test_tier_enforcement.py
│   │   ├── integration/
│   │   │   ├── test_api/
│   │   │   │   ├── test_jobs_api.py
│   │   │   │   └── test_agents_api.py
│   │   │   └── test_agent_orchestration.py
│   │   ├── contract/
│   │   │   ├── test_agent_contracts.py
│   │   │   └── test_api_contracts.py  # Schemathesis
│   │   └── quality_gates/             # [Party Mode] CI-blocking tests
│   │       ├── __init__.py
│   │       ├── test_llm_cost_budget.py    # <$6/user/month
│   │       ├── test_performance.py        # Response time thresholds
│   │       └── test_security.py           # Security checks
│   │
│   ├── scripts/
│   │   ├── seed_data.py               # Development data seeding
│   │   └── run_migrations.py          # Migration runner
│   │
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── pyproject.toml
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── index.tsx                  # React entry point
│   │   ├── App.tsx                    # App + routing
│   │   ├── main.css                   # Global styles (Tailwind)
│   │   │
│   │   ├── components/
│   │   │   ├── ui/                    # Base UI components
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Button.test.tsx    # [Party Mode] Co-located tests
│   │   │   │   ├── Card.tsx
│   │   │   │   ├── Badge.tsx
│   │   │   │   ├── Modal.tsx
│   │   │   │   ├── Skeleton.tsx
│   │   │   │   ├── Toast.tsx
│   │   │   │   └── index.ts
│   │   │   ├── layout/
│   │   │   │   ├── Header.tsx
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   ├── MainLayout.tsx
│   │   │   │   └── index.ts
│   │   │   └── forms/
│   │   │       ├── Input.tsx
│   │   │       ├── Select.tsx
│   │   │       ├── FileUpload.tsx
│   │   │       └── index.ts
│   │   │
│   │   ├── shared/                    # [Party Mode] Cross-feature code
│   │   │   ├── api/
│   │   │   │   ├── errorHandling.ts   # API error handling
│   │   │   │   └── responseTypes.ts   # Common response types
│   │   │   ├── hooks/
│   │   │   │   ├── useDebounce.ts
│   │   │   │   └── useLocalStorage.ts
│   │   │   └── utils/
│   │   │       ├── dateFormatters.ts
│   │   │       └── currencyFormatters.ts
│   │   │
│   │   ├── constants/                 # [Party Mode] Magic strings
│   │   │   ├── apiRoutes.ts           # API endpoint constants
│   │   │   ├── storageKeys.ts         # localStorage/sessionStorage keys
│   │   │   ├── queryKeys.ts           # TanStack Query key factory
│   │   │   └── featureFlags.ts        # Feature flag names
│   │   │
│   │   ├── features/
│   │   │   ├── auth/
│   │   │   │   ├── components/
│   │   │   │   │   ├── LoginForm.tsx
│   │   │   │   │   └── ProtectedRoute.tsx
│   │   │   │   ├── hooks/
│   │   │   │   │   └── useAuth.ts
│   │   │   │   └── index.ts
│   │   │   │
│   │   │   ├── onboarding/
│   │   │   │   ├── components/
│   │   │   │   │   ├── LinkedInImport.tsx
│   │   │   │   │   ├── ResumeUpload.tsx
│   │   │   │   │   ├── PreferencesForm.tsx
│   │   │   │   │   └── OnboardingWizard.tsx
│   │   │   │   ├── hooks/
│   │   │   │   │   └── useOnboarding.ts
│   │   │   │   └── index.ts
│   │   │   │
│   │   │   ├── jobs/
│   │   │   │   ├── components/
│   │   │   │   │   ├── JobCard.tsx
│   │   │   │   │   ├── JobList.tsx
│   │   │   │   │   ├── JobFilters.tsx
│   │   │   │   │   └── JobDetail.tsx
│   │   │   │   ├── hooks/
│   │   │   │   │   └── useJobs.ts
│   │   │   │   ├── api/
│   │   │   │   │   └── jobsApi.ts
│   │   │   │   └── index.ts
│   │   │   │
│   │   │   ├── agents/
│   │   │   │   ├── components/
│   │   │   │   │   ├── AgentStatus.tsx
│   │   │   │   │   ├── EmergencyBrake.tsx
│   │   │   │   │   ├── AgentActivityFeed.tsx
│   │   │   │   │   └── AgentControlPanel.tsx
│   │   │   │   ├── hooks/
│   │   │   │   │   └── useAgentState.ts
│   │   │   │   └── index.ts
│   │   │   │
│   │   │   ├── approvals/
│   │   │   │   ├── components/
│   │   │   │   │   ├── ApprovalCard.tsx
│   │   │   │   │   ├── ApprovalQueue.tsx
│   │   │   │   │   └── ApprovalDetail.tsx
│   │   │   │   ├── hooks/
│   │   │   │   │   └── useApprovals.ts
│   │   │   │   └── index.ts
│   │   │   │
│   │   │   ├── briefings/
│   │   │   │   ├── components/
│   │   │   │   │   ├── BriefingCard.tsx
│   │   │   │   │   ├── BriefingDetail.tsx
│   │   │   │   │   └── BriefingHistory.tsx
│   │   │   │   ├── hooks/
│   │   │   │   │   └── useBriefings.ts
│   │   │   │   └── index.ts
│   │   │   │
│   │   │   ├── pipeline/
│   │   │   │   ├── components/
│   │   │   │   │   ├── PipelineKanban.tsx
│   │   │   │   │   ├── ApplicationCard.tsx
│   │   │   │   │   └── ApplicationDetail.tsx
│   │   │   │   ├── hooks/
│   │   │   │   │   └── usePipeline.ts
│   │   │   │   └── index.ts
│   │   │   │
│   │   │   ├── resume/
│   │   │   │   ├── components/
│   │   │   │   │   ├── ResumeDiffView.tsx
│   │   │   │   │   ├── ResumeEditor.tsx
│   │   │   │   │   └── ResumePreview.tsx
│   │   │   │   ├── hooks/
│   │   │   │   │   └── useResume.ts
│   │   │   │   └── index.ts
│   │   │   │
│   │   │   ├── h1b/                   # H1B Pro only
│   │   │   │   ├── components/
│   │   │   │   │   ├── SponsorCard.tsx
│   │   │   │   │   ├── SponsorSearch.tsx
│   │   │   │   │   └── H1BDashboard.tsx
│   │   │   │   ├── hooks/
│   │   │   │   │   └── useH1BData.ts
│   │   │   │   └── index.ts
│   │   │   │
│   │   │   ├── upgrade/               # [Party Mode] Tier upgrade flow
│   │   │   │   ├── components/
│   │   │   │   │   ├── UpgradePrompt.tsx
│   │   │   │   │   ├── TierComparison.tsx
│   │   │   │   │   └── PaymentForm.tsx
│   │   │   │   ├── hooks/
│   │   │   │   │   └── useUpgrade.ts
│   │   │   │   └── index.ts
│   │   │   │
│   │   │   ├── admin/                 # [Party Mode] Enterprise admin
│   │   │   │   ├── components/
│   │   │   │   │   ├── TeamDashboard.tsx
│   │   │   │   │   ├── UserManagement.tsx
│   │   │   │   │   └── AnalyticsDashboard.tsx
│   │   │   │   ├── hooks/
│   │   │   │   │   └── useAdmin.ts
│   │   │   │   └── index.ts
│   │   │   │
│   │   │   └── settings/
│   │   │       ├── components/
│   │   │       │   ├── ProfileSettings.tsx
│   │   │       │   ├── PreferencesSettings.tsx
│   │   │       │   ├── NotificationSettings.tsx
│   │   │       │   └── BillingSettings.tsx
│   │   │       └── index.ts
│   │   │
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts        # WebSocket connection
│   │   │   └── useMediaQuery.ts       # Responsive hooks
│   │   │
│   │   ├── services/
│   │   │   ├── apiClient.ts           # Axios instance + interceptors only
│   │   │   └── websocketClient.ts     # WebSocket manager
│   │   │
│   │   ├── stores/
│   │   │   ├── uiStore.ts             # Zustand UI state
│   │   │   └── index.ts
│   │   │
│   │   ├── types/
│   │   │   ├── api.ts                 # API response types
│   │   │   ├── agents.ts              # Agent-related types
│   │   │   ├── jobs.ts                # Job types
│   │   │   └── index.ts
│   │   │
│   │   ├── schemas/                   # [Party Mode] Zod validation schemas
│   │   │   ├── agentOutput.ts
│   │   │   ├── job.ts
│   │   │   └── index.ts
│   │   │
│   │   ├── utils/
│   │   │   └── validators.ts          # Generic validators
│   │   │
│   │   └── lib/
│   │       ├── clerk.ts               # Clerk configuration
│   │       ├── queryClient.ts         # TanStack Query setup
│   │       └── featureFlags.ts        # [Party Mode] Feature flag client
│   │
│   ├── e2e/
│   │   ├── fixtures/
│   │   │   ├── auth.ts                # Auth fixtures
│   │   │   └── mockAgents.ts          # Seeded agent mocks
│   │   ├── specs/
│   │   │   ├── onboarding.spec.ts
│   │   │   ├── briefing.spec.ts
│   │   │   ├── approval-flow.spec.ts
│   │   │   └── emergency-brake.spec.ts
│   │   └── playwright.config.ts
│   │
│   ├── public/
│   │   ├── favicon.ico
│   │   └── assets/
│   │       └── images/
│   │
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── vite.config.ts
│   └── Dockerfile
│
├── infrastructure/
│   ├── docker/
│   │   ├── docker-compose.yml         # Local development
│   │   ├── docker-compose.test.yml    # CI testing
│   │   └── docker-compose.prod.yml    # Production reference
│   │
│   ├── railway/
│   │   └── railway.toml               # Railway configuration
│   │
│   ├── supabase/
│   │   ├── migrations/
│   │   │   └── 00001_initial_schema.sql
│   │   ├── seed.sql                   # Development seed data
│   │   └── config.toml
│   │
│   ├── monitoring/                    # [Party Mode] Observability config
│   │   ├── grafana/
│   │   │   └── dashboards/
│   │   │       ├── agent-performance.json
│   │   │       ├── llm-costs.json
│   │   │       └── user-activity.json
│   │   └── alerts/
│   │       ├── cost-alerts.yaml
│   │       └── performance-alerts.yaml
│   │
│   └── load-tests/                    # [Party Mode] Performance tests
│       ├── k6/
│       │   ├── scenarios/
│       │   │   ├── briefing-load.js
│       │   │   └── agent-concurrent.js
│       │   └── config.js
│       └── README.md
│
├── docs/
│   ├── architecture.md                # This document
│   ├── api-reference.md               # OpenAPI-generated
│   ├── agent-contracts.md             # Agent interface specs
│   ├── runbook.md                     # Operations runbook
│   ├── onboarding-dev.md              # Developer onboarding
│   └── adr/                           # [Party Mode] Architecture Decision Records
│       ├── 001-clerk-over-auth0.md
│       ├── 002-celery-over-rq.md
│       ├── 003-supabase-over-planetscale.md
│       └── template.md
│
├── scripts/
│   ├── setup-dev.sh                   # Development setup
│   ├── run-tests.sh                   # Test runner
│   └── deploy.sh                      # Deployment helper
│
├── .gitignore
├── README.md
└── Makefile                           # Common dev commands
```

### Architectural Boundaries

#### API Boundaries

```
┌─────────────────────────────────────────────────────────┐
│                    EXTERNAL BOUNDARY                     │
│                                                          │
│   /api/v1/*  ←──────────────────────────────────────┐   │
│       │                                              │   │
│       ▼                                              │   │
│   ┌─────────────────────────────────────────────┐   │   │
│   │           Authentication Boundary            │   │   │
│   │   Clerk JWT Validation + RLS Enforcement    │   │   │
│   └─────────────────────────────────────────────┘   │   │
│       │                                              │   │
│       ▼                                              │   │
│   ┌─────────────────────────────────────────────┐   │   │
│   │            Tier Enforcement Layer            │   │   │
│   │   @require_tier("pro") + Feature Flags      │   │   │
│   └─────────────────────────────────────────────┘   │   │
│       │                                              │   │
│       ▼                                              │   │
│   ┌───────────────┬───────────────┬─────────────┐   │   │
│   │   API Layer   │  Service Layer │ Agent Layer │   │   │
│   │  (api/v1/*)   │  (services/*)  │  (agents/*) │   │   │
│   └───────────────┴───────────────┴─────────────┘   │   │
│       │                   │                │         │   │
│       └───────────────────┼────────────────┘         │   │
│                           ▼                          │   │
│   ┌─────────────────────────────────────────────┐   │   │
│   │              Data Access Layer               │   │   │
│   │      Repositories + Supabase RLS            │   │   │
│   └─────────────────────────────────────────────┘   │   │
│                                                      │   │
└──────────────────────────────────────────────────────┘   │
                                                           │
                          WebSocket                        │
                    ws://api/v1/ws/agents/{user_id} ───────┘
```

#### Service Boundaries

| Boundary | Components | Communication |
|----------|------------|---------------|
| **Agent → Service** | Agents call services, never direct DB | Method calls |
| **Service → Repository** | Services use repos for data access | Method calls |
| **API → Service** | Controllers inject services via deps.py | Dependency injection |
| **Agent → Agent** | Via Orchestrator only | Event-based |
| **Frontend → Backend** | REST API + WebSocket | HTTP/WS |

#### Data Boundaries

| Data Type | Owner | Access Pattern |
|-----------|-------|----------------|
| User data | `user_service` | RLS-enforced, user_id filter |
| Job data | `job_service` | Public read, admin write |
| Applications | `application_service` | User-owned, RLS |
| Agent outputs | `agent_output_repo` | Append-only, user-owned |
| H1B data | `h1b_service` | Cached, shared across users |

### Integration Points

#### Internal Communication

| From | To | Method | Purpose |
|------|-----|--------|---------|
| Frontend | Backend API | REST over HTTPS | All data operations |
| Frontend | Backend WS | WebSocket | Real-time agent updates |
| API | Services | Method call | Business logic |
| Services | Repositories | Method call | Data access |
| Orchestrator | Agents | Direct call | Task delegation |
| Agents | Redis | Pub/sub | Status updates, pause check |
| Celery | Services | Task invocation | Background jobs |

#### External Integrations

| Integration | Location | Purpose |
|-------------|----------|---------|
| Clerk | `frontend/lib/clerk.ts`, `backend/api/deps.py` | Authentication |
| Supabase | `backend/db/connection.py` | Database |
| OpenAI/Anthropic | `backend/core/llm/clients.py` | LLM |
| SendGrid | `backend/services/briefing/` | Email delivery |
| Redis | `backend/celery_app.py`, `backend/core/infra/events.py` | Queue, cache, pub/sub |
| H1BGrader API | `backend/services/research/h1b_service.py` | H1B data |
| Gmail/Outlook | `backend/api/v1/webhooks/` | Email OAuth |
| Stripe | `backend/api/v1/webhooks/stripe.py` | Payments |

#### Data Flow

```
User Action → Frontend Component → API Client → FastAPI Endpoint
                                                      │
                                                      ▼
                                          Service Layer (business logic)
                                                      │
                                          ┌───────────┴───────────┐
                                          ▼                       ▼
                                    Repository            Agent (if async)
                                          │                       │
                                          ▼                       ▼
                                    Supabase (RLS)          Redis Queue
                                                                  │
                                                                  ▼
                                                           Celery Worker
                                                                  │
                                                                  ▼
                                                      WebSocket → Frontend
```

### Party Mode Enhancements Applied

| # | Enhancement | Location |
|---|-------------|----------|
| 1 | Agent tier grouping | `backend/app/agents/{core,pro,h1b}/` |
| 2 | Frontend shared code | `frontend/src/shared/` |
| 3 | Root-level test fixtures | `/fixtures/` |
| 4 | Enterprise admin frontend | `frontend/features/admin/` |
| 5 | Core directory split | `backend/core/{llm,auth,infra}/` |
| 6 | Co-located API schemas | `backend/api/v1/schemas/` |
| 7 | Quality gates tests | `backend/tests/quality_gates/` |
| 8 | Webhooks directory | `backend/api/v1/webhooks/` |
| 9 | Frontend constants | `frontend/src/constants/` |
| 10 | Upgrade flow feature | `frontend/features/upgrade/` |
| 11 | Monitoring config | `infrastructure/monitoring/` |
| 12 | Load tests | `infrastructure/load-tests/` |
| 13 | ADR documentation | `docs/adr/` |
| 14 | API contracts | `/contracts/` |
| 15 | Environment templates | `/env/` |

---

## Architecture Validation Results

*Comprehensive validation of coherence, coverage, and implementation readiness*

### Coherence Validation ✅

#### Decision Compatibility

All technology decisions verified compatible:

| Decision Pair | Compatibility | Notes |
|---------------|---------------|-------|
| FastAPI + Celery + Redis | ✅ | Standard async Python stack |
| React + TanStack Query + Zustand | ✅ | Modern React state split |
| Supabase + Clerk | ✅ | JWT forwarding for RLS |
| `langchain-core` + Custom Orchestrator | ✅ | Lightweight + custom autonomy |
| OpenTelemetry + FastAPI + Celery | ✅ | All have OTel instrumentation |

#### Pattern Consistency

All patterns align with technology choices:
- ✅ Naming conventions consistent across all layers
- ✅ Response formats standardized (wrapped `{data, meta}`)
- ✅ Error handling patterns uniform
- ✅ Event naming follows dot notation hierarchy

#### Structure Alignment

Project structure supports all architectural decisions:
- ✅ Agent tier grouping matches autonomy levels
- ✅ Feature folders mirror backend services
- ✅ Test organization includes quality gates
- ✅ API versioning in routes matches patterns

### Requirements Coverage Validation ✅

#### Domain Requirements Coverage

| Domain | Requirements | Coverage |
|--------|-------------|----------|
| Agent Orchestration | 8 | ✅ 100% |
| Research & Intelligence | 9 | ✅ 100% |
| Application Automation | 9 | ✅ 100% |
| Pipeline Management | 7 | ✅ 100% |
| User Communication | 9 | ✅ 100% |
| Enterprise Features | 9 | ✅ 100% |
| Onboarding | 6 | ✅ 100% |
| **Total** | **57** | **✅ 100%** |

#### Non-Functional Requirements Coverage

| Category | Key Requirement | Architecture Support |
|----------|-----------------|---------------------|
| Performance | <30s agent response | Celery timeouts, Redis caching |
| Performance | <2s page load | Vercel edge, TanStack Query |
| Scalability | 10K DAU | Railway auto-scale, K8s path |
| Reliability | 99.5% uptime | Briefing fallbacks, DLQ |
| Security | OAuth 2.0, AES-256 | Clerk, encryption layer |
| Privacy | GDPR/CCPA | Soft delete, RLS, minimization |
| Cost | <$6 LLM/user/month | Cost tracker, CI budget test |

### Implementation Readiness Validation ✅

#### Decision Completeness

| Area | Status |
|------|--------|
| Technology stack with versions | ✅ Complete |
| Agent architecture with schemas | ✅ Complete |
| Data architecture with SQL examples | ✅ Complete |
| Auth flow with diagrams | ✅ Complete |
| API structure with formats | ✅ Complete |
| Infrastructure with migration path | ✅ Complete |

#### Pattern Completeness

| Category | Elements | Status |
|----------|----------|--------|
| Database naming | 7 conventions | ✅ Complete |
| API naming | 5 conventions | ✅ Complete |
| Code naming | Python + TypeScript | ✅ Complete |
| Response formats | Success + error + pagination | ✅ Complete |
| Event patterns | Naming + payload | ✅ Complete |
| State management | Zustand + TanStack | ✅ Complete |

#### Structure Completeness

- ✅ 200+ files/directories specified
- ✅ Requirements → files mapping complete
- ✅ Integration points documented
- ✅ Boundaries clearly defined

### Gap Analysis Results

#### Critical Gaps: **NONE** ✅

#### Important Gaps (Resolved via Party Mode)

| Gap | Resolution |
|-----|------------|
| Email OAuth webhooks | Added `api/v1/webhooks/` |
| Enterprise frontend | Added `frontend/features/admin/` |
| Load testing | Added `infrastructure/load-tests/` |
| ADR documentation | Added `docs/adr/` |

#### Nice-to-Have (Deferred)

- Mobile app architecture (when expansion planned)
- Multi-region deployment (when international needed)
- ML model versioning (when custom models introduced)

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed (High - multi-agent)
- [x] Technical constraints identified (brownfield, ToS compliance)
- [x] Cross-cutting concerns mapped (6 concerns)

**✅ Architectural Decisions**
- [x] Technology stack fully specified with versions
- [x] 5 core decision categories documented
- [x] 22 Party Mode enhancements integrated
- [x] Performance and cost considerations addressed

**✅ Implementation Patterns**
- [x] 18 conflict points addressed
- [x] Naming conventions for all layers
- [x] Communication patterns specified
- [x] Process patterns (error, loading) documented

**✅ Project Structure**
- [x] Complete directory tree (200+ items)
- [x] 15 Party Mode structure enhancements
- [x] Component boundaries established
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** ✅ READY FOR IMPLEMENTATION

**Validation Score:** 98%

**Confidence Level:** HIGH

**Key Strengths:**
1. Comprehensive agent architecture with tier-based autonomy
2. Strong consistency patterns preventing AI agent conflicts
3. Complete project structure with clear boundaries
4. Robust testing strategy including cost budget gates
5. Party Mode insights from 4 expert perspectives

**Areas for Future Enhancement:**
1. Mobile app architecture when expansion planned
2. Multi-region deployment for international scale
3. Custom ML model versioning when introduced

### Implementation Handoff

**AI Agent Guidelines:**

1. Follow all architectural decisions exactly as documented
2. Use implementation patterns consistently across all components
3. Respect project structure and boundaries
4. Refer to this document for all architectural questions
5. Validate against patterns before creating new files
6. Include `rationale` in all agent outputs

**First Implementation Steps:**

1. Set up Supabase project with initial schema
2. Configure Clerk authentication
3. Extend existing FastAPI backend with new structure
4. Set up Celery + Redis infrastructure
5. Create base agent framework with orchestrator

**Development Environment Setup:**
```bash
# Use the documented structure
make setup-dev  # Runs scripts/setup-dev.sh
```

---

## Architecture Completion Summary

### Workflow Completion

| Attribute | Value |
|-----------|-------|
| **Workflow Status** | ✅ COMPLETED |
| **Total Steps** | 8 |
| **Date Completed** | 2026-01-25 |
| **Document Location** | `_bmad-output/planning-artifacts/architecture.md` |

### Final Architecture Deliverables

**📋 Complete Architecture Document**

- All architectural decisions documented with specific versions
- Implementation patterns ensuring AI agent consistency
- Complete project structure with 200+ files/directories
- Requirements to architecture mapping (57 FRs → 100% coverage)
- Validation confirming 98% coherence and completeness

**🏗️ Implementation Ready Foundation**

| Metric | Count |
|--------|-------|
| Architectural decisions | 5 core categories |
| Implementation patterns | 18 conflict points addressed |
| Party Mode enhancements | 37 total (22 decisions + 15 structure) |
| Requirements supported | 57 functional + all NFRs |

**📚 AI Agent Implementation Guide**

- Technology stack with verified versions
- Consistency rules preventing implementation conflicts
- Project structure with clear boundaries
- Integration patterns and communication standards

### Quality Assurance Checklist

**✅ Architecture Coherence**
- [x] All decisions work together without conflicts
- [x] Technology choices are compatible
- [x] Patterns support the architectural decisions
- [x] Structure aligns with all choices

**✅ Requirements Coverage**
- [x] All 57 functional requirements supported
- [x] All non-functional requirements addressed
- [x] Cross-cutting concerns handled
- [x] Integration points defined

**✅ Implementation Readiness**
- [x] Decisions are specific and actionable
- [x] Patterns prevent agent conflicts
- [x] Structure is complete and unambiguous
- [x] Examples provided for clarity

### Project Success Factors

**🎯 Clear Decision Framework**
Every technology choice made collaboratively with clear rationale, enhanced by Party Mode expert panel insights.

**🔧 Consistency Guarantee**
Implementation patterns and rules ensure multiple AI agents produce compatible, consistent code.

**📋 Complete Coverage**
All project requirements architecturally supported with clear mapping from business needs to technical implementation.

**🏗️ Solid Foundation**
Brownfield extension of existing FastAPI + React codebase with modern stack additions (Supabase, Clerk, Celery).

---

**Architecture Status:** ✅ READY FOR IMPLEMENTATION

**Next Phase:** Create Epics & Stories using architectural decisions documented herein.

**Document Maintenance:** Update this architecture when major technical decisions are made during implementation.



