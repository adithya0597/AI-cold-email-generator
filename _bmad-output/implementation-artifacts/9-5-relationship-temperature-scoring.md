# Story 9.5: Relationship Temperature Scoring

Status: done

## Story

As a **user**,
I want **to see relationship strength with target contacts**,
So that **I know when relationships are warm enough for asks**.

## Acceptance Criteria

1. **AC1: Temperature score display** — Given I have interacted with contacts, when I view my network dashboard, then each contact shows a temperature score: Cold (no interaction), Warming (some engagement), Warm (regular interaction), Hot (recent meaningful exchange).
2. **AC2: Temperature factors** — Given a temperature is computed, when factors are considered, then it accounts for: recency of interaction, frequency of engagement, depth of interaction.
3. **AC3: Outreach readiness indicator** — Given a contact's temperature is sufficient (Warm or Hot), when displayed, then a "Ready for outreach" indicator is shown.
4. **AC4: Integration with NetworkAgent** — Given the temperature service is implemented, when the agent produces output, then temperature scores are included in the network analysis.

## Tasks / Subtasks

- [x] Task 1: Create RelationshipTemperatureService (AC: #1, #2, #3)
  - [x] 1.1 Create `backend/app/services/network/temperature_scoring.py` with `RelationshipTemperatureService` class
  - [x] 1.2 Define `TemperatureScore` dataclass with fields: `contact_name`, `score` (cold/warming/warm/hot), `numeric_score` (0.0-1.0), `factors` (dict with recency, frequency, depth scores), `ready_for_outreach` (bool), `last_interaction`, `interaction_count`, `data_quality`
  - [x] 1.3 Implement `score_contacts(engagement_history: list[dict]) -> list[TemperatureScore]` that computes temperature from engagement records
  - [x] 1.4 Implement `_compute_recency_score(last_interaction: datetime) -> float` — decays over time (1.0 = today, 0.0 = 90+ days)
  - [x] 1.5 Implement `_compute_frequency_score(interaction_count: int, days_span: int) -> float`
  - [x] 1.6 Implement `_compute_depth_score(interaction_types: list[str]) -> float` — comments > likes, mutual conversations > one-way
  - [x] 1.7 Implement `_classify_temperature(numeric_score: float) -> str` — 0-0.25=cold, 0.25-0.5=warming, 0.5-0.75=warm, 0.75-1.0=hot
  - [x] 1.8 Add `to_dict()` method including ALL fields

- [x] Task 2: Integrate with NetworkAgent output (AC: #4)
  - [x] 2.1 In `_assemble_network_analysis()`, add temperature scores from EngagementTrackingService history
  - [x] 2.2 Include `ready_for_outreach` contacts in the analysis output

- [x] Task 3: Write tests (AC: #1-#4)
  - [x] 3.1 Create `backend/tests/unit/test_services/test_temperature_scoring.py`
  - [x] 3.2 Test score_contacts() returns correct TemperatureScore list
  - [x] 3.3 Test temperature classification boundaries (cold/warming/warm/hot)
  - [x] 3.4 Test recency decay scoring
  - [x] 3.5 Test frequency scoring
  - [x] 3.6 Test depth scoring (comment > like)
  - [x] 3.7 Test ready_for_outreach flag (true when warm/hot)
  - [x] 3.8 Test to_dict() includes ALL fields
  - [x] 3.9 Test with empty engagement history returns cold scores

## Dev Notes

### Architecture Compliance

- **Service location**: `backend/app/services/network/temperature_scoring.py`
- **Data structure**: `@dataclass` for `TemperatureScore`
- **Pure computation**: This service does NOT use LLM — it's a deterministic scoring algorithm based on engagement data. No LLMClient needed.
- **No new DB tables**: Temperature scores are computed on-the-fly from engagement history stored in agent_outputs.
- **Integration**: Called from NetworkAgent during `_assemble_network_analysis()` to enrich output with temperature data.

### Existing Utilities to Use

- No external dependencies needed — pure Python computation
- Uses `EngagementRecord` data from 9-4

### Project Structure Notes

- Service file: `backend/app/services/network/temperature_scoring.py`
- Test file: `backend/tests/unit/test_services/test_temperature_scoring.py`
- Modified file: `backend/app/agents/core/network_agent.py` (enrich _assemble_network_analysis)

### References

- [Source: backend/app/services/network/engagement_tracking.py — EngagementRecord data source]
- [Source: backend/app/agents/core/network_agent.py — _assemble_network_analysis to modify]

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5

### Debug Log References
N/A

### Completion Notes List
- 19 tests passing for temperature scoring service
- Pure computation, no LLM — deterministic scoring algorithm
- Temperature classification: cold(0-0.25), warming(0.25-0.5), warm(0.5-0.75), hot(0.75-1.0)
- Weighted factors: recency(40%), frequency(30%), depth(30%)
- ready_for_outreach flag set for warm/hot contacts
- Integrated into NetworkAgent._assemble_network_analysis()

### File List
- backend/app/services/network/temperature_scoring.py (created)
- backend/tests/unit/test_services/test_temperature_scoring.py (created)
- backend/app/agents/core/network_agent.py (modified)
