# Story 8.6: Prep Briefing Delivery

Status: done

## Story

As a **user**,
I want **my interview prep briefing delivered proactively**,
so that **I have time to review before the interview**.

## Acceptance Criteria

1. **AC1 - 24h Delivery:** Given interview scheduled, when 24h before, then briefing delivered.
2. **AC2 - Channels:** Briefing delivered via push notification, email with summary, in-app notification.
3. **AC3 - Pipeline Card:** Briefing accessible from Pipeline card.
4. **AC4 - Reminder:** Reminder 2h before if unopened.
5. **AC5 - Delivery Service:** PrepBriefingDeliveryService handles multi-channel delivery.

## Tasks / Subtasks

- [x] Task 1: Create PrepBriefingDeliveryService in backend/app/services/research/prep_delivery.py (AC: #1-#4)
- [x] Task 2: Write tests (AC: #1-#5)

## Dev Notes

- Files to CREATE: backend/app/services/research/prep_delivery.py, backend/tests/unit/test_services/test_prep_delivery.py
- Delivery uses existing Celery infrastructure for scheduling
- This service is called by InterviewIntelAgent._schedule_delivery() already wired in 8-1

## Dev Agent Record

- Tests: 8 new tests, all passing (73 total with existing 8-1 through 8-5)
- Files created: prep_delivery.py, test_prep_delivery.py
- No files modified (standalone service)
- No regressions in existing tests
- 2026-02-02: Code review fixes — replaced per-call Redis connection with shared pool via get_redis_client() (H1), moved json/uuid to module-level imports (M5)
