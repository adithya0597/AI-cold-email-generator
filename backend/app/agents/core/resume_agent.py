"""
Resume generation agent.

TODO: Full implementation in Story 5-1. This stub provides the PII hook
integration point for Story 10-8.

PII Hook Integration
--------------------
When generating resume or cover letter content, call the PII detection
hook before returning output to the user::

    from app.services.enterprise.pii_detection import PIIDetectionService

    service = PIIDetectionService()
    result = await service.check_pii(
        text=generated_text,
        user_id=user_id,
        org_id=org_id,
        session=session,
    )
    if result.pii_detected:
        # Add pii_warning=True to output, include result.categories
        output_data["pii_warning"] = True
        output_data["pii_categories"] = result.categories

The hook is synchronous in the output path -- if PII is detected, the
agent returns a modified output with ``pii_warning=True`` so the frontend
can display a warning before showing the content to the employee.
"""

from __future__ import annotations

# Placeholder: wire PII hook into generate_resume() when this agent is implemented.
# See PIIDetectionService.check_pii() in app/services/enterprise/pii_detection.py
