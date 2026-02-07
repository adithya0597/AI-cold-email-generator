# Architecture & Patterns Research: JobPilot

**Domain:** AI-powered multi-agent job search platform
**Researched:** 2026-01-30
**Focus:** Architecture patterns, agent orchestration, database foundation, scalability
**Overall Confidence:** MEDIUM-HIGH

---

## Executive Summary

JobPilot's architecture is ambitious: a multi-agent orchestration system with tiered autonomy (L0-L3), real-time user control (emergency brake), and a hybrid Supabase + SQLAlchemy persistence layer. The BMAD architecture document is thorough and well-reasoned, but several areas need careful attention during implementation to avoid common pitfalls in agent-based systems.

The core architectural tension is between **agent autonomy** and **user control**. The L0-L3 tier system is a genuinely differentiating pattern, but it introduces cross-cutting enforcement complexity that touches every agent, every API endpoint, and every background task. Getting this wrong is the single biggest architectural risk.

The existing codebase (cold email generator) provides a solid FastAPI foundation but requires significant restructuring. The database schema (Story 0-1) has been implemented and is well-designed, though it has a notable gap: the dual-persistence approach (Supabase Python SDK client + SQLAlchemy ORM) introduces a split that needs resolution.

---

## 1. Multi-Agent Orchestration Architecture

### 1.1 Pattern Assessment

**Confidence: HIGH** (verified across multiple current sources)

The BMAD architecture specifies a **Coordinator-Worker (Supervisor) pattern** where a central Orchestrator Agent routes tasks to specialized agents (Job Scout, Resume, Apply, Pipeline, Follow-up). This is the correct pattern for JobPilot's use case.

**Why Coordinator-Worker is right here:**
- Clear task delegation semantics (Orchestrator decides what runs)
- Centralized state management (shared memory via PostgreSQL)
- Natural enforcement point for autonomy levels (Orchestrator checks tier before delegation)
- Supports the emergency brake pattern (single control point)

**Why NOT other patterns:**
- **Handoff pattern** (agents passing control to each other): Would make autonomy enforcement distributed and harder to audit. Each agent would need to know about tiers.
- **Peer-to-peer**: No central control point for emergency brake.
- **Sequential pipeline**: Too rigid -- agents need to run independently (Job Scout runs on schedule, Resume runs on-demand).

### 1.2 Custom Orchestrator vs. Framework

**Recommendation: Custom orchestrator using `langchain-core` primitives only.**

**Confidence: MEDIUM-HIGH**

The BMAD architecture correctly specifies `langchain-core` only (not full LangChain). This is validated by current ecosystem trends:

- **LangChain 1.0** (late 2025) slimmed down the core package, but even the slimmed version includes the agent loop, chains, and retrieval logic that JobPilot does not need.
- `langchain-core` provides model wrappers (`ChatOpenAI`, `ChatAnthropic`), `PromptTemplate`, and `PydanticOutputParser` -- exactly what the BMAD doc specifies.
- One fintech team reported **40% latency reduction** after moving from full LangChain to a custom orchestrator (source: Ampcome AI Agents Guide 2025).

**What to use from `langchain-core`:**
| Component | Purpose | Alternative |
|-----------|---------|-------------|
| `ChatOpenAI` / `ChatAnthropic` | Model wrappers | Raw SDK clients (already exist in codebase) |
| `PromptTemplate` | Prompt management | f-strings or Jinja2 |
| `PydanticOutputParser` | Structured output | Pydantic + manual JSON parsing |
| Cost tracking callbacks | LLM spend tracking | Custom middleware |

**Honest assessment:** The existing codebase already has an `LLMClient` abstraction in `backend/app/core/llm_clients.py` that wraps OpenAI and Anthropic directly. Adding `langchain-core` on top introduces a second abstraction layer. The team should decide: either use `langchain-core` model wrappers exclusively (replacing the existing abstraction) or skip `langchain-core` entirely and extend the existing abstraction. Do NOT maintain both.

**Recommendation:** Skip `langchain-core`. The existing `LLMClient` abstraction is sufficient. Extend it with:
- Structured output via Pydantic (already using Pydantic 2.5)
- Cost tracking via a decorator/middleware pattern
- Prompt management via a simple template registry

This eliminates a dependency, avoids dual-abstraction confusion, and keeps the stack lighter.

### 1.3 Agent Framework Alternatives Considered

| Framework | Why NOT for JobPilot |
|-----------|---------------------|
| **LangGraph** | Overkill -- graph-based workflows add complexity for what is fundamentally a coordinator-worker pattern. |
| **CrewAI** | Role-based delegation is close, but JobPilot needs custom autonomy tier enforcement that CrewAI does not natively support. |
| **OpenAI Agents SDK** | Handoff-based, tied to OpenAI. JobPilot needs provider fallback (Anthropic). |
| **AutoGen** | Research-focused, chatroom-style agent communication. Not a fit for the approval-gate workflow. |

### 1.4 Code vs. LLM Orchestration

**Recommendation: Code-based orchestration with LLM decision support.**

The Orchestrator should NOT use an LLM to decide which agent to invoke. Routing should be deterministic code based on:
- Task type (briefing generation, job matching, resume tailoring)
- User tier (L0-L3 determines what agents can run)
- Schedule (Job Scout runs on cron, not on LLM decision)

LLMs should only be used within individual agents for their specialized tasks (matching, tailoring, parsing). This keeps orchestration fast, predictable, and cheap.

---

## 2. Autonomy Tier Enforcement (L0-L3)

### 2.1 Pattern Design

**Confidence: HIGH** (this is a custom pattern, but grounded in research on autonomy frameworks)

The L0-L3 autonomy model is JobPilot's key differentiator. Current research from the Knight First Amendment Institute defines five levels of agent autonomy characterized by user roles: operator, collaborator, consultant, approver, observer. JobPilot's four tiers map well:

| JobPilot Tier | Knight Level | User Role | Agent Behavior |
|---------------|-------------|-----------|----------------|
| L0 (Free) | Operator | User does everything | Agent suggests only |
| L1 (Free) | Collaborator | User executes, agent drafts | Agent prepares, user acts |
| L2 (Pro) | Approver | User reviews daily digest | Agent acts, user approves batch |
| L3 (H1B Pro) | Observer | User monitors | Agent acts within rules autonomously |

### 2.2 Enforcement Architecture

**Recommendation: Decorator-based enforcement at the agent layer, NOT at the API layer.**

```python
# Pattern: Enforcement decorator on agent methods
class AutonomyGate:
    """Checks tier before allowing agent action."""

    def __init__(self, required_tier: UserTier, action_type: str):
        self.required_tier = required_tier
        self.action_type = action_type

    def __call__(self, func):
        @wraps(func)
        async def wrapper(agent_self, user_id: UUID, *args, **kwargs):
            user = await get_user(user_id)
            if not tier_allows(user.tier, self.required_tier):
                return AgentOutput(
                    action="blocked",
                    rationale=f"Action requires {self.required_tier} tier",
                    confidence=1.0,
                    alternatives_considered=["upgrade_tier"]
                )

            # For L2: queue for approval instead of executing
            if user.tier == UserTier.PRO and self.action_type == "write":
                return await queue_for_approval(user_id, func, args, kwargs)

            return await func(agent_self, user_id, *args, **kwargs)
        return wrapper
```

**Why decorator, not middleware:**
- Middleware runs on HTTP requests; agents run in Celery workers (no HTTP context).
- Decorators are co-located with agent logic, making enforcement visible and testable.
- Each agent method can declare its own tier requirement.

### 2.3 Approval Queue Architecture

The approval queue is the bridge between L2 (human-approves) and L3 (autonomous). This is architecturally critical.

**Pattern: Pending action table + WebSocket notification.**

```
Agent generates action -> Stored in `pending_approvals` table ->
  WebSocket pushes to frontend -> User approves/rejects ->
  Approved: Execute action -> Log to `agent_actions`
  Rejected: Log rejection reason -> Agent learns
```

**Missing from current schema:** The `agent_actions` table exists but there is no `pending_approvals` or `approval_queue` table. This needs to be added in a future migration. The table should include: action payload (JSONB), expiry time, user_id, agent_type, status (pending/approved/rejected/expired), and the original function context needed to resume execution.

---

## 3. Database Architecture Assessment

### 3.1 Schema Foundation (Story 0-1)

**Confidence: HIGH** (directly verified from code)

The initial schema is well-designed:

**Strengths:**
- UUID primary keys throughout (correct for distributed systems)
- Soft delete pattern with `deleted_at`, `deleted_by`, `deletion_reason` (good for compliance)
- `schema_version` on JSONB columns (supports schema evolution)
- Proper ENUM types for status fields
- Indexes on foreign keys and status columns
- `updated_at` trigger functions (database-level, not application-level)
- Separate `agent_actions` (audit log) and `agent_outputs` (JSONB results)

**Gaps identified:**

| Gap | Impact | Priority |
|-----|--------|----------|
| No `user_preferences` table | Deal-breakers, employer blocklist, notification settings have no home | HIGH - needed for MVP |
| No `pending_approvals` table | L2 approval queue has no persistence | HIGH - needed for Pro tier |
| No `h1b_sponsors` table | H1B data has no schema yet | MEDIUM - needed for H1B tier |
| No `briefings` table | Daily briefings have no storage | HIGH - needed for MVP |
| No `contacts` table (referenced in BMAD architecture) | No entity for tracking hiring managers, recruiters | LOW - post-MVP |
| `jobs` table missing: `location`, `salary_min`, `salary_max`, `remote_type`, `company_size` | Cannot implement job matching filters | HIGH - needed for Job Scout |
| `agent_actions.status` is TEXT not ENUM | Inconsistent with other status fields | LOW - tech debt |
| No compound index on `(user_id, status)` for applications | Slow filtered queries per user | MEDIUM |
| No `preferences` JSONB on `users` table | User preferences have nowhere to live | HIGH |

### 3.2 Dual Persistence Concern

**Confidence: HIGH** (verified from code)

The codebase currently has TWO database access patterns:

1. **Supabase Python SDK** (`backend/app/db/connection.py`): Uses `supabase.create_client()` for direct Supabase API calls.
2. **SQLAlchemy ORM** (`backend/app/db/models.py`): Full ORM model definitions with relationships.

These are NOT connected. The SQLAlchemy models exist but there is no SQLAlchemy engine, session factory, or async session configuration. The connection.py only creates a Supabase REST client.

**This is a critical architectural decision that must be resolved early:**

| Approach | Pros | Cons |
|----------|------|------|
| **Supabase SDK only** | Simpler, leverages RLS natively, real-time subscriptions built-in | No ORM relationships, no migration tooling (Alembic), limited query complexity |
| **SQLAlchemy only** (via direct PostgreSQL connection) | Full ORM, Alembic migrations, complex queries, async support | Must manually implement RLS bypass, no Supabase real-time, more connection management |
| **Hybrid** (SQLAlchemy for writes/complex queries, Supabase SDK for auth/realtime) | Best of both worlds | Two connection pools, consistency risk, more cognitive overhead |

**Recommendation: SQLAlchemy as primary, Supabase SDK only for auth/storage/realtime.**

Rationale:
- Agent orchestration requires complex queries (joins, aggregations, batch operations) that the Supabase REST API handles poorly.
- Alembic migrations are essential for a schema this complex.
- The existing `models.py` ORM definitions are already well-structured -- they just need an engine.
- Supabase SDK is still needed for: Clerk JWT validation against Supabase Auth, file storage (resumes), and potentially real-time subscriptions.

### 3.3 Supabase + SQLAlchemy Async: Known Issues

**Confidence: HIGH** (verified from current Supabase GitHub issues and community reports)

The `asyncpg` + Supabase PgBouncer combination has a **known `DuplicatePreparedStatementError`** under burst load. This is the most significant pain point in 2025 for this stack combination.

**Mitigation strategy:**
1. Use **direct connections** (port 5432) during development and early production. At JobPilot's initial scale (50-500 users), direct connections are fine.
2. Configure unique prepared statement names as a safety measure:
   ```python
   connect_args={
       "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
       "server_settings": {"jit": "off"},
   }
   ```
3. When scaling requires connection pooling (5000+ DAU), switch to transaction-mode pooler with `NullPool` in SQLAlchemy.
4. Monitor connection usage -- Supabase recommends keeping pooled connections to 40% of available.

### 3.4 Event Sourcing vs. Simple Audit Log

**Recommendation: Simple audit log pattern, NOT full event sourcing.**

The BMAD architecture mentions "event sourcing, immutable log store" for audit logging. Full event sourcing is overkill for JobPilot:

- Event sourcing requires rebuilding state from events (expensive for agent outputs).
- Agent actions are already stored in `agent_actions` with rationale and status.
- `agent_outputs` stores the JSONB results with schema versioning.

Instead, use the existing `agent_actions` table as an append-only audit log:
- Make it INSERT-only (no UPDATE/DELETE at application level)
- Add a `sequence_num BIGSERIAL` for ordering
- Add a `metadata JSONB` column for contextual data (tokens used, model, execution time)
- Consider a PostgreSQL trigger to prevent UPDATE/DELETE on this table

This provides full auditability without the complexity overhead of event sourcing.

---

## 4. Celery + Redis Task Architecture

### 4.1 Task Queue Design

**Confidence: HIGH** (well-established pattern, verified for 2025)

Celery + Redis is the correct choice for JobPilot's background processing needs. The pattern is mature and well-supported with FastAPI.

**Recommended queue topology:**

| Queue | Workers | Tasks | Priority |
|-------|---------|-------|----------|
| `default` | 2 | General tasks, cleanup | Normal |
| `agents` | 4 | Agent execution (Job Scout, Resume, Apply, Pipeline) | High |
| `briefings` | 2 | Daily briefing generation | High (time-sensitive) |
| `scraping` | 2 | Job board scraping, company research | Low |

**Why separate queues:**
- Agent tasks should not be blocked by slow scraping tasks.
- Briefing generation is time-critical (8am delivery) and should not compete with general tasks.
- Different concurrency limits per queue (scraping needs rate limiting).

### 4.2 Agent Task Lifecycle

```
1. Trigger (schedule or API request)
   |
2. Orchestrator evaluates task
   |-- Check user tier (autonomy gate)
   |-- Check emergency brake (Redis flag: paused:{user_id})
   |-- Route to appropriate agent
   |
3. Agent task enqueued to Celery
   |
4. Worker picks up task
   |-- Heartbeat every 30s (Redis key: heartbeat:{task_id})
   |-- Check emergency brake at each logical step
   |-- Execute agent logic (LLM calls, data processing)
   |
5. Result handling
   |-- L0-L1: Store result, notify user
   |-- L2: Store in pending_approvals, WebSocket notify
   |-- L3: Execute action, store in agent_actions, notify user
   |
6. Cleanup
   |-- Remove heartbeat key
   |-- Update task status
```

### 4.3 Emergency Brake Implementation

The BMAD architecture's Redis flag pattern is correct and practical:

```python
# Check pattern (called at each logical step within an agent)
async def check_brake(user_id: str) -> bool:
    return await redis.exists(f"paused:{user_id}")
```

**Important refinement:** The emergency brake state machine in the BMAD doc (RUNNING -> PAUSING -> PAUSED/TIMEOUT/PARTIAL) is well-designed. The key implementation detail is handling in-flight operations:

- **In-flight LLM calls**: Cannot be cancelled mid-request. The agent should check brake BEFORE each LLM call, not during.
- **In-flight applications**: If Apply Agent has submitted to a job board, it cannot be un-submitted. The brake prevents the NEXT action, not the current one.
- **State on brake**: All pending_approvals should be marked as "paused" so the user knows nothing will execute while brake is active.

---

## 5. Real-Time Communication Architecture

### 5.1 WebSocket + Redis Pub/Sub

**Confidence: MEDIUM-HIGH**

The BMAD architecture specifies WebSocket channels per user (`ws://api/v1/ws/agents/{user_id}`) with Redis pub/sub for agent status updates. This is a well-established pattern.

**Recommended approach:**

Use the `broadcaster` library with Redis backend for cross-instance message delivery. This handles:
- Multiple Uvicorn workers (each with its own WebSocket connections)
- Redis pub/sub fan-out across instances
- Clean connection lifecycle management

**Alternative considered:** Redis Streams instead of Pub/Sub. Redis Streams provide message persistence (messages are not lost if client disconnects). However, for agent status updates, missed messages are not critical -- the client can always fetch current state via REST API. Pub/Sub is simpler and sufficient.

### 5.2 Event Schema

The BMAD event naming convention (`{domain}.{entity}.{action}`) is good. Standardize the payload:

```python
class AgentEvent(BaseModel):
    event_type: str        # "agent.job_scout.job_matched"
    event_id: UUID
    timestamp: datetime
    user_id: UUID
    agent_type: AgentType
    data: dict             # Event-specific payload

    # For frontend rendering
    title: str             # Human-readable: "New job match found"
    severity: str          # "info", "action_required", "error"
```

---

## 6. Scalability Patterns

### 6.1 Current Scale Target

The BMAD NFRs specify: 10,000 DAU, 100K jobs/day, 50K applications/day. This is significant but achievable with the proposed stack.

### 6.2 Scaling Bottlenecks (In Order of Likelihood)

| Bottleneck | When | Mitigation |
|------------|------|------------|
| **LLM API rate limits** | 500+ concurrent users | Request queuing, batch processing, caching |
| **Database connections** | 2000+ DAU with Supabase free tier | Connection pooling, read replicas, query optimization |
| **Celery worker throughput** | 100+ concurrent agent tasks | Horizontal scaling (add workers), queue prioritization |
| **WebSocket connections** | 5000+ concurrent WS connections | Sticky sessions, Redis pub/sub fan-out |
| **Redis memory** | 10K+ cached items | TTL policies, eviction strategies, Redis cluster |

### 6.3 LLM Cost Architecture

The BMAD doc specifies `<$6/user/month` target. The cost tracking architecture is well-designed:

```
LLM Call -> Cost Tracker Middleware -> Redis Counter (per user, per month)
                                    -> Alert at 80% threshold
                                    -> Block at 100% (graceful degradation)
```

**Critical implementation detail:** Cost tracking MUST happen in the LLM client abstraction layer, not in individual agents. Every LLM call, regardless of which agent makes it, must be tracked. The existing `LLMClient` abstraction is the right place for this.

### 6.4 Three-Layer Caching

The BMAD architecture's three-layer caching (Redis -> Materialized Views -> TanStack Query) is sound:

| Layer | What to Cache | TTL | Invalidation |
|-------|--------------|-----|-------------|
| **Redis (L1)** | User preferences, emergency brake state, agent heartbeats | 5min-24hr | Explicit on write |
| **Materialized Views (L2)** | Job match scores, H1B sponsor aggregations | 5min refresh | Scheduled + on-demand |
| **TanStack Query (L3)** | Briefings, job lists, pipeline state | stale-while-revalidate | Mutation invalidation + WebSocket signals |

---

## 7. Anti-Patterns to Avoid

### 7.1 God Orchestrator

**Risk:** The Orchestrator Agent becomes a monolithic class handling routing, state management, briefing generation, conflict resolution, and tier enforcement.

**Prevention:** Split Orchestrator responsibilities:
- `TaskRouter`: Deterministic routing logic (code, not LLM)
- `StateManager`: User state, agent state, brake state
- `BriefingGenerator`: Briefing synthesis (uses LLM)
- `TierEnforcer`: Autonomy validation (decorator pattern)

### 7.2 Shared Mutable State Between Agents

**Risk:** Agents directly read/write shared database records, causing race conditions.

**Prevention:** Each agent should:
- Read its own input data (snapshot at task start)
- Write to its own output table (`agent_outputs`)
- Never directly modify another agent's data
- Communicate only through the Orchestrator or event system

### 7.3 Synchronous Agent Calls

**Risk:** API endpoint waits for agent to complete before responding.

**Prevention:** All agent operations should be async via Celery:
1. API receives request
2. Enqueues Celery task
3. Returns task_id immediately
4. Client polls or receives WebSocket update

Exception: Simple lookups (fetching cached results) can be synchronous.

### 7.4 Over-Engineering the Agent Memory

**Risk:** Building a sophisticated shared memory system (vector store, graph database) before validating the core product.

**Prevention:** Start with PostgreSQL JSONB for agent outputs. Schema versioning (`schema_version` column) allows evolution. Add pgvector for semantic job matching ONLY when basic keyword matching proves insufficient.

### 7.5 Dual Database Abstraction Drift

**Risk:** Some code uses Supabase SDK, other code uses SQLAlchemy, data gets out of sync.

**Prevention:** Establish clear boundaries immediately:
- SQLAlchemy: ALL data reads and writes for application logic
- Supabase SDK: Auth token validation, file storage, real-time subscriptions ONLY
- Never use both to access the same table

---

## 8. Migration Path from Existing Codebase

### 8.1 Current State

The existing codebase is a cold email generator with:
- FastAPI backend (reusable patterns)
- React frontend (reusable component patterns)
- LLM client abstraction (reusable, needs extension)
- No auth, no persistent storage (in-memory dicts), no background jobs

### 8.2 Incremental Migration Strategy

**Phase 1: Foundation** (corresponds to Epic 0)
- Add SQLAlchemy async engine configuration (the models already exist)
- Wire up Alembic for migrations
- Add Clerk auth middleware to FastAPI
- Set up Redis + Celery
- Keep existing email generator functional during migration

**Phase 2: Agent Framework** (corresponds to Epic 1-2)
- Create `BaseAgent` class with brake check, tier enforcement
- Implement Orchestrator as task router
- Build first agent (Job Scout) as proof of concept
- Validate the full lifecycle: trigger -> orchestrate -> execute -> store -> notify

**Phase 3: Feature Build** (corresponds to Epics 3-8)
- Each agent builds on BaseAgent pattern
- Each feature adds its own Celery tasks, API endpoints, frontend components
- Schema evolves via Alembic migrations per epic

### 8.3 What to Preserve from Existing Codebase

| Component | Preserve? | Why |
|-----------|-----------|-----|
| `LLMClient` abstraction | YES, extend | Good provider abstraction, add cost tracking |
| `WebScraper` | YES, extend | Working scraping logic, add caching layer |
| Error handling patterns | YES | `async_error_handler` decorator is solid |
| Monitoring/alerts skeleton | YES, extend | Base pattern exists, wire into production |
| Email service | NO | Replace with agent-based architecture |
| Post service | NO | Not relevant to JobPilot |
| Author styles service | NO | Not relevant to JobPilot |
| Frontend components | PARTIAL | Reuse layout/routing patterns, replace feature components |

---

## 9. Confidence Assessment

| Area | Confidence | Reasoning |
|------|------------|-----------|
| Coordinator-Worker pattern | HIGH | Well-established, validated by multiple sources, correct for use case |
| Custom orchestrator over framework | MEDIUM-HIGH | Strong evidence against full frameworks, but custom builds carry implementation risk |
| Skip `langchain-core` | MEDIUM | Existing abstraction is good, but `langchain-core` has ecosystem benefits (callbacks, tracing) |
| SQLAlchemy as primary DB layer | HIGH | Complex query needs, Alembic requirement, existing ORM models |
| Supabase asyncpg issues | HIGH | Well-documented in GitHub issues, multiple community reports |
| Celery + Redis for task queue | HIGH | Mature stack, extensive FastAPI integration guides |
| L0-L3 enforcement via decorators | MEDIUM | Custom pattern, not validated in production elsewhere |
| Event sourcing NOT needed | HIGH | Simpler audit log pattern achieves same goals with less complexity |
| WebSocket + Redis pub/sub | HIGH | Well-established pattern with multiple libraries |

---

## 10. Roadmap Implications

Based on this architecture research, the recommended phase structure:

### Phase 1: Database + Auth Foundation
- Resolve dual-persistence (SQLAlchemy primary, Supabase SDK for auth/storage)
- Add missing schema tables (preferences, approvals, briefings)
- Wire Alembic migrations
- Add Clerk auth middleware
- **Rationale:** Everything else depends on the data layer being solid

### Phase 2: Agent Framework Core
- BaseAgent with brake check + tier enforcement
- Orchestrator as deterministic task router
- Celery + Redis infrastructure
- WebSocket event system
- **Rationale:** Must validate agent lifecycle before building individual agents

### Phase 3: First Agent (Job Scout)
- Proves end-to-end: scrape -> match -> store -> briefing -> notify
- Validates cost tracking, caching, and scheduling patterns
- **Rationale:** Simplest agent (read-only, no approval queue needed for L0-L1)

### Phase 4+: Remaining Agents (Resume, Pipeline, Apply)
- Each builds on proven patterns from Phase 2-3
- Apply Agent introduces approval queue (L2) -- highest architectural complexity
- **Rationale:** Ordered by increasing complexity and dependency

### Research Flags for Later Phases
- **Job board scraping**: Needs dedicated research on rate limits, ToS compliance, and anti-detection
- **Email OAuth integration**: Gmail/Outlook OAuth has specific token refresh and scope requirements
- **H1B data sources**: Data freshness, accuracy, and legal attribution need investigation
- **Apply Agent form filling**: Automating job applications across different platforms is technically complex

---

## Sources

### Multi-Agent Orchestration
- [n8n Blog: AI Agent Orchestration Frameworks](https://blog.n8n.io/ai-agent-orchestration-frameworks/)
- [Google Developers: Multi-Agent Patterns in ADK](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/)
- [OpenAI Agents SDK: Orchestrating Multiple Agents](https://openai.github.io/openai-agents-python/multi_agent/)
- [AIMultiple: Top Agentic Orchestration Frameworks 2026](https://research.aimultiple.com/agentic-orchestration/)
- [LangChain Docs: Multi-Agent](https://docs.langchain.com/oss/python/langchain/multi-agent)

### LangChain Core vs. Full
- [Ampcome: LangChain vs Custom Workflows 2025](https://www.ampcome.com/post/langchain-vs-custom-workflows-ai-agents-2025)
- [LangChain Blog: LangChain and LangGraph 1.0](https://www.blog.langchain.com/langchain-langgraph-1dot0/)
- [Akka: 25 LangChain Alternatives](https://akka.io/blog/langchain-alternatives)

### Supabase + SQLAlchemy
- [Supabase Docs: Using SQLAlchemy with Supabase](https://supabase.com/docs/guides/troubleshooting/using-sqlalchemy-with-supabase-FUqebT)
- [Medium: Supabase Pooling and asyncpg Don't Mix](https://medium.com/@patrickduch93/supabase-pooling-and-asyncpg-dont-mix-here-s-the-real-fix-44f700b05249)
- [GitHub Issue: asyncpg PreparedStatementError](https://github.com/supabase/supabase/issues/35684)

### Celery + FastAPI
- [TestDriven.io: Asynchronous Tasks with FastAPI and Celery](https://testdriven.io/blog/fastapi-and-celery/)
- [Greeden Blog: Practical Background Processing with FastAPI](https://blog.greeden.me/en/2025/12/02/practical-background-processing-with-fastapi-a-job-queue-design-guide-with-backgroundtasks-and-celery/)
- [Medium: Celery in 2025 Bullet-Proof Background Jobs](https://medium.com/@theNewGenCoder/celery-in-2025-bullet-proof-background-jobs-with-fastapi-redis-retries-scheduling-91b8bb5f7257)

### Agent Autonomy Patterns
- [Google Cloud: Choose a Design Pattern for Agentic AI](https://docs.google.com/architecture/choose-design-pattern-agentic-ai-system)
- [Knight First Amendment Institute: Levels of Autonomy for AI Agents](https://knightcolumbia.org/content/levels-of-autonomy-for-ai-agents-1)
- [Databricks: Agent System Design Patterns](https://docs.databricks.com/aws/en/generative-ai/guide/agent-system-design-patterns)

### Event Sourcing / Audit Logs
- [Medium: Production-Ready Audit Logs in PostgreSQL](https://medium.com/@sehban.alam/lets-build-production-ready-audit-logs-in-postgresql-7125481713d8)
- [DEV: Event Storage in Postgres](https://dev.to/kspeakman/event-storage-in-postgres-4dk2)

### Real-Time WebSocket Patterns
- [ITNEXT: Scalable Real-Time Apps with Python and Redis](https://itnext.io/scalable-real-time-apps-with-python-and-redis-exploring-asyncio-fastapi-and-pub-sub-79b56a9d2b94)
- [DEV: Real-Time Notification Service with FastAPI, Redis Streams, and WebSockets](https://dev.to/geetnsh2k1/building-a-real-time-notification-service-with-fastapi-redis-streams-and-websockets-52ib)
- [fastapi-websocket-pubsub on PyPI](https://pypi.org/project/fastapi-websocket-pubsub/)
