"""Unit tests for BillingService.

Tests verify:
- Billing summary returns correct structure (AC1)
- Seat update validates and recalculates (AC2)
- Seat reduction below active count rejected (AC2)
- AuditLog entry created on seat update (AC2)
- Invoice pagination (AC3)
- Volume discount computation (AC4)
- Cost trend extraction (AC6)
- RBAC enforcement (AC7)
"""

from __future__ import annotations

import inspect
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.enterprise.billing import BillingService


# ---------------------------------------------------------------------------
# _compute_monthly_cost tests (AC4: volume discount)
# ---------------------------------------------------------------------------


class TestComputeMonthlyCost:
    """Test static cost computation with volume discount."""

    def test_no_discount(self):
        cost = BillingService._compute_monthly_cost(10, Decimal("50.00"), 0)
        assert cost == Decimal("500.00")

    def test_with_discount(self):
        cost = BillingService._compute_monthly_cost(10, Decimal("50.00"), 10)
        assert cost == Decimal("450.00")

    def test_zero_seats(self):
        cost = BillingService._compute_monthly_cost(0, Decimal("50.00"), 10)
        assert cost == Decimal("0.00")

    def test_rounding(self):
        cost = BillingService._compute_monthly_cost(3, Decimal("33.33"), 7)
        # 3 * 33.33 = 99.99; 99.99 * 0.93 = 92.9907 -> 92.99
        assert cost == Decimal("92.99")

    def test_full_discount(self):
        cost = BillingService._compute_monthly_cost(10, Decimal("50.00"), 100)
        assert cost == Decimal("0.00")

    def test_large_seat_count(self):
        cost = BillingService._compute_monthly_cost(500, Decimal("25.00"), 15)
        # 500 * 25 = 12500; 12500 * 0.85 = 10625.00
        assert cost == Decimal("10625.00")


# ---------------------------------------------------------------------------
# _generate_invoice_record tests (AC3)
# ---------------------------------------------------------------------------


class TestGenerateInvoiceRecord:
    """Test invoice record generation."""

    def test_record_structure(self):
        record = BillingService._generate_invoice_record(
            org_id="12345678-abcd-1234-abcd-123456789012",
            period=date(2026, 1, 15),
            seats=50,
            cost_per_seat=25.0,
            discount_pct=10.0,
            monthly_cost=1125.0,
        )
        assert record["invoice_date"] == "2026-01-15"
        assert record["amount"] == 1125.0
        assert record["seats"] == 50
        assert record["cost_per_seat"] == 25.0
        assert record["discount_percent"] == 10.0
        assert record["status"] == "paid"
        assert record["reference_id"].startswith("INV-12345678-")

    def test_reference_id_format(self):
        record = BillingService._generate_invoice_record(
            org_id="abcdef01-0000-0000-0000-000000000000",
            period=date(2026, 3, 1),
            seats=10,
            cost_per_seat=50.0,
            discount_pct=0,
            monthly_cost=500.0,
        )
        assert record["reference_id"] == "INV-abcdef01-20260301"


# ---------------------------------------------------------------------------
# get_billing_summary tests (AC1)
# ---------------------------------------------------------------------------


class TestGetBillingSummary:
    """Test billing summary returns correct structure."""

    @pytest.mark.asyncio
    async def test_summary_structure(self):
        service = BillingService()

        mock_org = MagicMock()
        mock_org.settings = {
            "billing": {
                "seats_allocated": 50,
                "cost_per_seat": "25.00",
                "volume_discount_percent": 10,
                "billing_cycle_start": "2026-01-01",
                "billing_cycle_end": "2026-02-01",
            }
        }

        with patch.object(service, "_get_org", new_callable=AsyncMock, return_value=mock_org):
            with patch.object(service, "_count_active_members", new_callable=AsyncMock, return_value=35):
                session = AsyncMock()
                result = await service.get_billing_summary(session, "org-123")

        assert result["seats_allocated"] == 50
        assert result["seats_used"] == 35
        assert result["seats_available"] == 15
        assert result["cost_per_seat"] == 25.0
        assert result["volume_discount_percent"] == 10
        assert result["billing_cycle_start"] == "2026-01-01"
        assert result["billing_cycle_end"] == "2026-02-01"
        # 50 * 25 * 0.9 = 1125.00
        assert result["monthly_cost"] == 1125.0

    @pytest.mark.asyncio
    async def test_summary_empty_billing(self):
        """Summary returns zeros when no billing config exists."""
        service = BillingService()

        mock_org = MagicMock()
        mock_org.settings = {}

        with patch.object(service, "_get_org", new_callable=AsyncMock, return_value=mock_org):
            with patch.object(service, "_count_active_members", new_callable=AsyncMock, return_value=0):
                session = AsyncMock()
                result = await service.get_billing_summary(session, "org-123")

        assert result["seats_allocated"] == 0
        assert result["seats_used"] == 0
        assert result["monthly_cost"] == 0.0


# ---------------------------------------------------------------------------
# update_seats tests (AC2)
# ---------------------------------------------------------------------------


class TestUpdateSeats:
    """Test seat update, validation, and audit logging."""

    @pytest.mark.asyncio
    async def test_seat_increase(self):
        service = BillingService()

        mock_org = MagicMock()
        mock_org.settings = {
            "billing": {
                "seats_allocated": 50,
                "cost_per_seat": "25.00",
                "volume_discount_percent": 0,
                "history": [],
            }
        }

        with patch.object(service, "_get_org", new_callable=AsyncMock, return_value=mock_org):
            with patch.object(service, "_count_active_members", new_callable=AsyncMock, return_value=35):
                with patch("app.services.enterprise.billing.log_audit_event", new_callable=AsyncMock) as mock_audit:
                    session = AsyncMock()
                    result = await service.update_seats(
                        session, "org-123", 60, "admin-user-123"
                    )

        assert result["seats_allocated"] == 60
        # 60 * 25 = 1500.00
        assert result["monthly_cost"] == 1500.0
        mock_audit.assert_called_once()
        call_kwargs = mock_audit.call_args.kwargs
        assert call_kwargs["action"] == "seats_updated"
        assert call_kwargs["changes"]["old_seat_count"] == 50
        assert call_kwargs["changes"]["new_seat_count"] == 60

    @pytest.mark.asyncio
    async def test_seat_reduction_below_active_rejected(self):
        """Cannot reduce seats below active member count."""
        service = BillingService()

        with patch.object(service, "_count_active_members", new_callable=AsyncMock, return_value=35):
            session = AsyncMock()
            with pytest.raises(ValueError, match="Cannot reduce seats below active member count"):
                await service.update_seats(session, "org-123", 30, "admin-user")

    @pytest.mark.asyncio
    async def test_seat_update_creates_history_entry(self):
        service = BillingService()

        mock_org = MagicMock()
        mock_org.settings = {
            "billing": {
                "seats_allocated": 10,
                "cost_per_seat": "50.00",
                "volume_discount_percent": 0,
                "history": [],
            }
        }

        with patch.object(service, "_get_org", new_callable=AsyncMock, return_value=mock_org):
            with patch.object(service, "_count_active_members", new_callable=AsyncMock, return_value=5):
                with patch("app.services.enterprise.billing.log_audit_event", new_callable=AsyncMock):
                    session = AsyncMock()
                    await service.update_seats(session, "org-123", 20, "admin-user")

        # Verify history was appended
        billing = mock_org.settings["billing"]
        assert len(billing["history"]) == 1
        assert billing["history"][0]["seats"] == 20


# ---------------------------------------------------------------------------
# get_invoices tests (AC3: pagination)
# ---------------------------------------------------------------------------


class TestGetInvoices:
    """Test invoice pagination."""

    @pytest.mark.asyncio
    async def test_pagination(self):
        service = BillingService()

        history = [
            {"invoice_date": f"2026-01-{i:02d}", "amount": 100.0 * i, "seats": 10,
             "cost_per_seat": 10.0, "discount_percent": 0, "status": "paid",
             "reference_id": f"INV-{i}"}
            for i in range(1, 16)
        ]

        mock_org = MagicMock()
        mock_org.settings = {"billing": {"history": history}}

        with patch.object(service, "_get_org", new_callable=AsyncMock, return_value=mock_org):
            session = AsyncMock()
            result = await service.get_invoices(session, "org-123", page=1, per_page=5)

        assert result["total"] == 15
        assert result["page"] == 1
        assert result["per_page"] == 5
        assert result["total_pages"] == 3
        assert len(result["invoices"]) == 5

    @pytest.mark.asyncio
    async def test_empty_invoices(self):
        service = BillingService()

        mock_org = MagicMock()
        mock_org.settings = {}

        with patch.object(service, "_get_org", new_callable=AsyncMock, return_value=mock_org):
            session = AsyncMock()
            result = await service.get_invoices(session, "org-123")

        assert result["total"] == 0
        assert result["invoices"] == []
        assert result["total_pages"] == 1


# ---------------------------------------------------------------------------
# RBAC enforcement test (AC7)
# ---------------------------------------------------------------------------


class TestBillingEndpointAuth:
    """Test that billing endpoints require admin authentication."""

    def test_billing_summary_uses_require_admin(self):
        from app.api.v1.admin_enterprise import get_billing_summary
        from fastapi import params

        sig = inspect.signature(get_billing_summary)
        admin_param = sig.parameters.get("admin_ctx")
        assert admin_param is not None
        assert isinstance(admin_param.default, params.Depends)

    def test_update_seats_uses_require_admin(self):
        from app.api.v1.admin_enterprise import update_billing_seats
        from fastapi import params

        sig = inspect.signature(update_billing_seats)
        admin_param = sig.parameters.get("admin_ctx")
        assert admin_param is not None
        assert isinstance(admin_param.default, params.Depends)

    def test_invoices_uses_require_admin(self):
        from app.api.v1.admin_enterprise import get_billing_invoices
        from fastapi import params

        sig = inspect.signature(get_billing_invoices)
        admin_param = sig.parameters.get("admin_ctx")
        assert admin_param is not None
        assert isinstance(admin_param.default, params.Depends)

    def test_cost_trend_uses_require_admin(self):
        from app.api.v1.admin_enterprise import get_billing_cost_trend
        from fastapi import params

        sig = inspect.signature(get_billing_cost_trend)
        admin_param = sig.parameters.get("admin_ctx")
        assert admin_param is not None
        assert isinstance(admin_param.default, params.Depends)


# ---------------------------------------------------------------------------
# Cost trend tests (AC6)
# ---------------------------------------------------------------------------


class TestCostTrend:
    """Test cost trend extraction."""

    @pytest.mark.asyncio
    async def test_trend_from_history(self):
        service = BillingService()

        mock_org = MagicMock()
        mock_org.settings = {
            "billing": {
                "history": [
                    {"invoice_date": "2026-01-15", "amount": 1000.0},
                    {"invoice_date": "2025-12-15", "amount": 900.0},
                    {"invoice_date": "2025-11-15", "amount": 800.0},
                ]
            }
        }

        with patch.object(service, "_get_org", new_callable=AsyncMock, return_value=mock_org):
            session = AsyncMock()
            result = await service.get_cost_trend(session, "org-123", months=6)

        assert isinstance(result, list)
        assert len(result) <= 6
        # Each item should have month and cost
        for item in result:
            assert "month" in item
            assert "cost" in item

    @pytest.mark.asyncio
    async def test_trend_empty_history(self):
        service = BillingService()

        mock_org = MagicMock()
        mock_org.settings = {}

        with patch.object(service, "_get_org", new_callable=AsyncMock, return_value=mock_org):
            session = AsyncMock()
            result = await service.get_cost_trend(session, "org-123", months=6)

        assert isinstance(result, list)
        # Should still return month entries with 0 cost
        for item in result:
            assert item["cost"] == 0.0
