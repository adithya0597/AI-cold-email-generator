"""Tests for the Email Status Detection service (Story 6-1, Task 2).

Covers: rejection, interview, offer, applied, screening detection,
ambiguous emails, empty input, and confidence thresholds.
"""

from app.services.email_parser import CONFIDENCE_THRESHOLD, EmailStatusDetector


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _detector():
    return EmailStatusDetector()


# ---------------------------------------------------------------------------
# Test: Rejection detection
# ---------------------------------------------------------------------------


class TestRejectionDetection:
    """Tests for rejection email pattern matching."""

    def test_standard_rejection(self):
        """Detects 'decided to move forward with other candidates'."""
        d = _detector()
        result = d.detect(
            subject="Update on your application",
            body="After careful review, we have decided to move forward with other candidates.",
        )
        assert result.detected_status == "rejected"
        assert result.confidence >= CONFIDENCE_THRESHOLD
        assert not result.is_ambiguous

    def test_not_moving_forward(self):
        """Detects 'not moving forward with your application'."""
        d = _detector()
        result = d.detect(
            subject="Application Status",
            body="We are not moving forward with your application at this time.",
        )
        assert result.detected_status == "rejected"
        assert result.confidence >= 0.9

    def test_regret_to_inform(self):
        """Detects 'regret to inform'."""
        d = _detector()
        result = d.detect(
            subject="RE: Backend Engineer Position",
            body="We regret to inform you that the position has been filled.",
        )
        assert result.detected_status == "rejected"
        assert result.confidence >= 0.85


# ---------------------------------------------------------------------------
# Test: Interview detection
# ---------------------------------------------------------------------------


class TestInterviewDetection:
    """Tests for interview invitation pattern matching."""

    def test_schedule_interview(self):
        """Detects 'like to schedule an interview'."""
        d = _detector()
        result = d.detect(
            subject="Interview Request - Backend Engineer",
            body="We would like to schedule an interview with you for the Backend Engineer role.",
        )
        assert result.detected_status == "interview"
        assert result.confidence >= 0.90

    def test_invite_for_interview(self):
        """Detects 'invite you for an interview'."""
        d = _detector()
        result = d.detect(
            subject="Next Steps",
            body="We'd like to invite you for an interview with our engineering team.",
        )
        assert result.detected_status == "interview"
        assert result.confidence >= 0.90

    def test_phone_screen(self):
        """Detects 'schedule a phone screen'."""
        d = _detector()
        result = d.detect(
            subject="Phone Screen",
            body="I'd like to schedule a phone screen with you to discuss the role.",
        )
        assert result.detected_status == "interview"
        assert result.confidence >= 0.85


# ---------------------------------------------------------------------------
# Test: Offer detection
# ---------------------------------------------------------------------------


class TestOfferDetection:
    """Tests for offer pattern matching."""

    def test_pleased_to_offer(self):
        """Detects 'pleased to offer you the position'."""
        d = _detector()
        result = d.detect(
            subject="Offer Letter - Senior Engineer",
            body="We are pleased to offer you the position of Senior Engineer at BigTech Inc.",
        )
        assert result.detected_status == "offer"
        assert result.confidence >= 0.90

    def test_congratulations_offer(self):
        """Detects 'congratulations, you have been selected'."""
        d = _detector()
        result = d.detect(
            subject="Congratulations!",
            body="Congratulations! You have been selected for the role.",
        )
        assert result.detected_status == "offer"
        assert result.confidence >= 0.85


# ---------------------------------------------------------------------------
# Test: Applied confirmation detection
# ---------------------------------------------------------------------------


class TestAppliedDetection:
    """Tests for application confirmation pattern matching."""

    def test_thank_you_for_applying(self):
        """Detects 'thank you for applying'."""
        d = _detector()
        result = d.detect(
            subject="Application Received",
            body="Thank you for applying to the Backend Engineer position at BigTech.",
        )
        assert result.detected_status == "applied"
        assert result.confidence >= 0.75

    def test_application_received(self):
        """Detects 'we have received your application'."""
        d = _detector()
        result = d.detect(
            subject="Application Confirmation",
            body="We have received your application and will review it shortly.",
        )
        assert result.detected_status == "applied"
        assert result.confidence >= 0.80


# ---------------------------------------------------------------------------
# Test: Ambiguous / no match
# ---------------------------------------------------------------------------


class TestAmbiguousDetection:
    """Tests for ambiguous and unrecognized emails."""

    def test_generic_email_returns_no_status(self):
        """Generic email with no status signals returns None."""
        d = _detector()
        result = d.detect(
            subject="Company Newsletter",
            body="Check out our latest blog post about engineering best practices.",
        )
        assert result.detected_status is None
        assert result.confidence == 0.0
        assert result.is_ambiguous

    def test_empty_input(self):
        """Empty subject and body returns None with is_ambiguous."""
        d = _detector()
        result = d.detect(subject="", body="")
        assert result.detected_status is None
        assert result.confidence == 0.0
        assert result.is_ambiguous

    def test_subject_boost(self):
        """Pattern match in subject boosts confidence."""
        d = _detector()
        result_body_only = d.detect(
            subject="Update",
            body="We would like to schedule an interview with you.",
        )
        result_with_subject = d.detect(
            subject="Interview Request - schedule an interview",
            body="We would like to schedule an interview with you.",
        )
        assert result_with_subject.confidence >= result_body_only.confidence

    def test_screening_detection(self):
        """Detects screening / under review status."""
        d = _detector()
        result = d.detect(
            subject="Application Update",
            body="Your application is currently being reviewed by our hiring team.",
        )
        assert result.detected_status == "screening"
        assert result.confidence >= 0.70
