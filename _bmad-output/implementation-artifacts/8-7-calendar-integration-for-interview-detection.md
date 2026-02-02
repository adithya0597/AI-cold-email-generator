# Story 8.7: Calendar Integration for Interview Detection

Status: done

## Story

As a **user**,
I want **interviews automatically detected from my calendar**,
so that **prep briefings are generated without manual input**.

## Acceptance Criteria

1. **AC1 - Pattern Matching:** Events matching interview patterns detected (title contains "interview"/"call with recruiter"/company name, external attendees, 30-60min duration).
2. **AC2 - Flagging:** Detected events flagged as potential interviews.
3. **AC3 - Confirmation:** User confirms/dismisses flagged events.
4. **AC4 - Trigger:** Confirmed triggers prep briefing generation.
5. **AC5 - Calendar Support:** Supports Google/Outlook calendar event format.

## Tasks / Subtasks

- [x] Task 1: Create CalendarInterviewDetector in backend/app/services/research/calendar_detection.py (AC: #1-#5)
- [x] Task 2: Write tests (AC: #1-#5)

## Dev Notes

- Files to CREATE: backend/app/services/research/calendar_detection.py, backend/tests/unit/test_services/test_calendar_detection.py
- Pattern matching is the core logic; actual Google/Outlook API integration deferred
- Service accepts calendar event dicts and returns detection results

## Dev Agent Record

- Tests: 15 new tests, all passing (88 total with existing 8-1 through 8-6)
- Files created: calendar_detection.py, test_calendar_detection.py
- No files modified (standalone service)
- No regressions in existing tests
