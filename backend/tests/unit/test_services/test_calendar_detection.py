"""Tests for Calendar Interview Detection Service (Story 8-7).

Covers: pattern matching, flagging, confirmation/dismissal,
company name matching, duration filtering, external attendees.
"""

import pytest

from app.services.research.calendar_detection import (
    CalendarInterviewDetector,
    DetectedInterview,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def detector():
    return CalendarInterviewDetector()


@pytest.fixture
def interview_event():
    return {
        "id": "evt-1",
        "title": "Technical Interview with Acme Corp",
        "start": "2026-02-10T10:00:00Z",
        "end": "2026-02-10T11:00:00Z",
        "duration_minutes": 60,
        "attendees": ["user@gmail.com", "recruiter@acme.com"],
    }


@pytest.fixture
def non_interview_event():
    return {
        "id": "evt-2",
        "title": "Weekly Team Standup",
        "start": "2026-02-10T09:00:00Z",
        "end": "2026-02-10T09:15:00Z",
        "duration_minutes": 15,
        "attendees": ["user@gmail.com", "coworker@gmail.com"],
    }


@pytest.fixture
def recruiter_call_event():
    return {
        "id": "evt-3",
        "title": "Call with Recruiter - Sarah",
        "start": "2026-02-11T14:00:00Z",
        "end": "2026-02-11T14:30:00Z",
        "duration_minutes": 30,
        "attendees": ["user@gmail.com", "sarah@recruiting.io"],
    }


# ---------------------------------------------------------------------------
# AC1: Pattern matching
# ---------------------------------------------------------------------------


class TestPatternMatching:
    def test_detects_interview_in_title(self, detector, interview_event):
        """Events with 'interview' in title are detected."""
        results = detector.detect([interview_event], user_domain="gmail.com")
        assert len(results) == 1
        assert results[0].title == "Technical Interview with Acme Corp"

    def test_detects_recruiter_call(self, detector, recruiter_call_event):
        """Events with 'call with recruiter' detected."""
        results = detector.detect([recruiter_call_event], user_domain="gmail.com")
        assert len(results) == 1

    def test_detects_phone_screen(self, detector):
        """Events with 'phone screen' detected."""
        event = {
            "id": "evt-4",
            "title": "Phone Screen - Backend Role",
            "start": "2026-02-12T10:00:00Z",
            "end": "2026-02-12T10:45:00Z",
            "duration_minutes": 45,
            "attendees": [],
        }
        results = detector.detect([event])
        assert len(results) == 1

    def test_ignores_non_interview(self, detector, non_interview_event):
        """Non-interview events are not flagged."""
        results = detector.detect([non_interview_event], user_domain="gmail.com")
        assert len(results) == 0

    def test_detects_company_name_match(self, detector):
        """Events with known company name in title detected."""
        event = {
            "id": "evt-5",
            "title": "Meeting with TechCorp Team",
            "start": "2026-02-13T10:00:00Z",
            "end": "2026-02-13T11:00:00Z",
            "duration_minutes": 60,
            "attendees": ["user@gmail.com", "hr@techcorp.com"],
        }
        results = detector.detect(
            [event],
            user_domain="gmail.com",
            known_companies=["TechCorp"],
        )
        assert len(results) == 1
        assert results[0].company_hint == "TechCorp"

    def test_duration_filtering(self, detector):
        """Events too short are not detected (unless strong title match)."""
        event = {
            "id": "evt-6",
            "title": "Quick Chat",
            "start": "2026-02-13T10:00:00Z",
            "end": "2026-02-13T10:10:00Z",
            "duration_minutes": 10,
            "attendees": [],
        }
        results = detector.detect([event])
        assert len(results) == 0


# ---------------------------------------------------------------------------
# AC2: Flagging
# ---------------------------------------------------------------------------


class TestFlagging:
    def test_detected_events_have_pending_status(self, detector, interview_event):
        """Detected interviews have 'pending' status."""
        results = detector.detect([interview_event])
        assert results[0].status == "pending"

    def test_confidence_score_assigned(self, detector, interview_event):
        """Detected interviews have confidence > 0."""
        results = detector.detect([interview_event], user_domain="gmail.com")
        assert results[0].confidence > 0

    def test_matched_patterns_recorded(self, detector, interview_event):
        """Matched patterns are recorded for transparency."""
        results = detector.detect([interview_event], user_domain="gmail.com")
        assert len(results[0].matched_patterns) > 0


# ---------------------------------------------------------------------------
# AC3: Confirmation / dismissal
# ---------------------------------------------------------------------------


class TestConfirmation:
    def test_confirm_sets_status(self, detector, interview_event):
        """confirm() sets status to 'confirmed'."""
        results = detector.detect([interview_event])
        confirmed = detector.confirm(results[0])
        assert confirmed.status == "confirmed"

    def test_dismiss_sets_status(self, detector, interview_event):
        """dismiss() sets status to 'dismissed'."""
        results = detector.detect([interview_event])
        dismissed = detector.dismiss(results[0])
        assert dismissed.status == "dismissed"


# ---------------------------------------------------------------------------
# AC5: External attendees
# ---------------------------------------------------------------------------


class TestExternalAttendees:
    def test_identifies_external_attendees(self, detector, interview_event):
        """External attendees (different domain) identified."""
        results = detector.detect([interview_event], user_domain="gmail.com")
        assert "recruiter@acme.com" in results[0].external_attendees

    def test_no_external_without_domain(self, detector, interview_event):
        """No external attendees when user_domain not provided."""
        results = detector.detect([interview_event])
        assert results[0].external_attendees == []


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_to_dict(self, detector, interview_event):
        """to_dict() produces correct structure."""
        results = detector.detect([interview_event], user_domain="gmail.com")
        d = results[0].to_dict()
        assert "event_id" in d
        assert "title" in d
        assert "matched_patterns" in d
        assert "confidence" in d
        assert "status" in d
        assert "external_attendees" in d


# ---------------------------------------------------------------------------
# Multiple events
# ---------------------------------------------------------------------------


class TestMultipleEvents:
    def test_scans_multiple_events(
        self, detector, interview_event, non_interview_event, recruiter_call_event
    ):
        """Correctly filters interview events from mixed batch."""
        events = [interview_event, non_interview_event, recruiter_call_event]
        results = detector.detect(events, user_domain="gmail.com")
        assert len(results) == 2  # interview + recruiter call
