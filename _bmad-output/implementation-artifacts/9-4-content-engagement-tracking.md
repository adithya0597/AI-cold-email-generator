# Story 9.4: Content Engagement Tracking

Status: done

## Story

As a **Network Agent**,
I want **to track engagement with target contacts' content**,
So that **users build familiarity before direct outreach**.

## Acceptance Criteria

1. **AC1: Engagement opportunity surfacing** — Given target contacts are identified, when they post public content, then the agent surfaces engagement opportunities like "John posted about [topic] - good chance to comment".
2. **AC2: Comment draft suggestions** — Given an engagement opportunity exists, when the user views it, then a suggested thoughtful comment draft is provided.
3. **AC3: Engagement history tracking** — Given the user engages with content, when tracked, then engagement history is recorded with timestamp, type, and contact.
4. **AC4: Temperature impact** — Given engagement occurs, when tracked, then "Relationship temperature" increases with engagement frequency and depth.
5. **AC5: User control** — Given this feature exists, when configured, then it is optional and user-controlled (can be enabled/disabled).
6. **AC6: Integration with NetworkAgent** — Given the engagement service exists, when `NetworkAgent._identify_opportunities()` is called, then it delegates to EngagementTrackingService.

## Tasks / Subtasks

- [x] Task 1: Create EngagementTrackingService (AC: #1, #2, #3, #5)
  - [x] 1.1 Create `backend/app/services/network/engagement_tracking.py` with `EngagementTrackingService` class
  - [x] 1.2 Define `EngagementOpportunity` dataclass with fields: `contact_name`, `content_topic`, `content_type` (post/article/comment), `suggested_comment`, `opportunity_reason`, `relevance_score`, `data_quality`
  - [x] 1.3 Define `EngagementRecord` dataclass with fields: `contact_name`, `engagement_type`, `content_reference`, `timestamp`, `temperature_impact`
  - [x] 1.4 Implement `async find_opportunities(contacts: list[dict], user_profile: dict) -> list[EngagementOpportunity]` using LLM to generate plausible engagement suggestions based on contact profiles
  - [x] 1.5 Implement `_generate_comment_draft(opportunity: EngagementOpportunity, user_profile: dict) -> str` via LLM
  - [x] 1.6 Implement `record_engagement(user_id: str, record: EngagementRecord) -> None` that stores engagement in agent_outputs
  - [x] 1.7 Implement `get_engagement_history(user_id: str, contact_name: str) -> list[EngagementRecord]`
  - [x] 1.8 Add `to_dict()` on both dataclasses including ALL fields
  - [x] 1.9 Use `asyncio.gather()` for parallel opportunity analysis

- [x] Task 2: Replace stub in NetworkAgent._identify_opportunities() (AC: #6)
  - [x] 2.1 Import and call EngagementTrackingService.find_opportunities()
  - [x] 2.2 Return list[dict] via .to_dict()

- [x] Task 3: Write tests (AC: #1-#6)
  - [x] 3.1 Create `backend/tests/unit/test_services/test_engagement_tracking.py`
  - [x] 3.2 Test find_opportunities() returns correct structure
  - [x] 3.3 Test comment draft generation
  - [x] 3.4 Test engagement recording
  - [x] 3.5 Test engagement history retrieval
  - [x] 3.6 Test graceful degradation on LLM failure
  - [x] 3.7 Test to_dict() includes ALL fields on both dataclasses
  - [x] 3.8 Test agent integration calls service

## Dev Notes

### Architecture Compliance

- **Service location**: `backend/app/services/network/engagement_tracking.py`
- **Data structures**: `@dataclass` for `EngagementOpportunity` and `EngagementRecord`
- **Content tracking is simulated**: Real LinkedIn content feed integration is deferred. This service uses LLM to generate plausible engagement suggestions based on contact profile data.
- **Engagement persistence**: Store engagement records as JSON in `agent_outputs` table via BaseAgent pattern. No new DB tables.
- **User control**: The service respects an `engagement_tracking_enabled` flag in user preferences. Check via `get_user_context()`.
- **Use asyncio.gather()** for parallel opportunity analysis across contacts

### Existing Utilities to Use

- `LLMClient` from `app.core.llm_clients`
- `get_user_context(user_id)` for preference flags
- Follow `CompanyResearchService` pattern

### Project Structure Notes

- Service file: `backend/app/services/network/engagement_tracking.py`
- Test file: `backend/tests/unit/test_services/test_engagement_tracking.py`
- Modified file: `backend/app/agents/core/network_agent.py` (replace stub)

### References

- [Source: backend/app/services/research/company_research.py — Reference service pattern]
- [Source: backend/app/agents/core/network_agent.py — stub to replace]

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5

### Debug Log References
N/A

### Completion Notes List
- 10 tests passing for engagement tracking service
- EngagementTrackingService with asyncio.gather for parallel contact analysis
- EngagementOpportunity and EngagementRecord dataclasses with to_dict()
- record_engagement() stores to agent_outputs table
- get_engagement_history() queries by user_id and contact_name
- NetworkAgent._identify_opportunities() delegates to service

### File List
- backend/app/services/network/engagement_tracking.py (created)
- backend/tests/unit/test_services/test_engagement_tracking.py (created)
- backend/app/agents/core/network_agent.py (modified)
