"""Enterprise billing service.

Manages seat-based billing, cost computation, and invoice history.
All billing data is stored in Organization.settings["billing"] JSONB.
No real payment processor integration -- V1 computes costs locally.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Organization, OrganizationMember
from app.services.enterprise.audit import log_audit_event


class BillingService:
    """Seat-based billing operations for enterprise organizations."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_billing_summary(
        self,
        session: AsyncSession,
        org_id: str,
    ) -> Dict[str, Any]:
        """Return billing summary for an organization.

        Returns dict with:
            seats_allocated, seats_used, seats_available,
            monthly_cost, cost_per_seat, billing_cycle_start,
            billing_cycle_end, volume_discount_percent
        """
        org = await self._get_org(session, org_id)
        billing = (org.settings or {}).get("billing", {})

        seats_allocated = billing.get("seats_allocated", 0)
        cost_per_seat = Decimal(str(billing.get("cost_per_seat", "0")))
        discount_pct = float(billing.get("volume_discount_percent", 0))

        # Count active members
        seats_used = await self._count_active_members(session, org_id)
        seats_available = max(seats_allocated - seats_used, 0)

        monthly_cost = self._compute_monthly_cost(
            seats_allocated, cost_per_seat, discount_pct
        )

        # Billing cycle defaults: current month
        today = date.today()
        cycle_start = billing.get(
            "billing_cycle_start",
            today.replace(day=1).isoformat(),
        )
        cycle_end = billing.get(
            "billing_cycle_end",
            (today.replace(day=28) + timedelta(days=4)).replace(day=1).isoformat(),
        )

        return {
            "seats_allocated": seats_allocated,
            "seats_used": seats_used,
            "seats_available": seats_available,
            "monthly_cost": float(monthly_cost),
            "cost_per_seat": float(cost_per_seat),
            "billing_cycle_start": cycle_start,
            "billing_cycle_end": cycle_end,
            "volume_discount_percent": discount_pct,
        }

    async def update_seats(
        self,
        session: AsyncSession,
        org_id: str,
        new_seat_count: int,
        admin_user_id: str,
    ) -> Dict[str, Any]:
        """Update seat allocation for an organization.

        Validates that new_seat_count >= active member count.
        Recalculates monthly cost and creates an AuditLog entry.

        Returns updated billing summary dict.

        Raises:
            ValueError: If new_seat_count < active members.
        """
        active_count = await self._count_active_members(session, org_id)
        if new_seat_count < active_count:
            raise ValueError(
                f"Cannot reduce seats below active member count ({active_count})."
            )

        org = await self._get_org(session, org_id)
        billing = dict((org.settings or {}).get("billing", {}))
        old_seat_count = billing.get("seats_allocated", 0)

        cost_per_seat = Decimal(str(billing.get("cost_per_seat", "0")))
        discount_pct = float(billing.get("volume_discount_percent", 0))

        billing["seats_allocated"] = new_seat_count
        new_cost = self._compute_monthly_cost(
            new_seat_count, cost_per_seat, discount_pct
        )

        # Append to history
        history: list = list(billing.get("history", []))
        history.append(
            self._generate_invoice_record(
                org_id=org_id,
                period=date.today(),
                seats=new_seat_count,
                cost_per_seat=float(cost_per_seat),
                discount_pct=discount_pct,
                monthly_cost=float(new_cost),
            )
        )
        billing["history"] = history

        # Persist updated settings
        settings = dict(org.settings or {})
        settings["billing"] = billing
        org.settings = settings

        # Audit trail
        await log_audit_event(
            session=session,
            org_id=org_id,
            actor_id=admin_user_id,
            action="seats_updated",
            resource_type="organization",
            resource_id=org_id,
            changes={
                "old_seat_count": old_seat_count,
                "new_seat_count": new_seat_count,
                "monthly_cost": float(new_cost),
            },
        )

        return await self.get_billing_summary(session, org_id)

    async def get_invoices(
        self,
        session: AsyncSession,
        org_id: str,
        page: int = 1,
        per_page: int = 10,
    ) -> Dict[str, Any]:
        """Return paginated invoice records from billing history.

        Returns:
            {
                "invoices": [...],
                "total": int,
                "page": int,
                "per_page": int,
                "total_pages": int,
            }
        """
        org = await self._get_org(session, org_id)
        billing = (org.settings or {}).get("billing", {})
        history: list = billing.get("history", [])

        # Sort by date descending (most recent first)
        history_sorted = sorted(
            history,
            key=lambda r: r.get("invoice_date", ""),
            reverse=True,
        )

        total = len(history_sorted)
        total_pages = max(math.ceil(total / per_page), 1)
        start = (page - 1) * per_page
        end = start + per_page
        page_items = history_sorted[start:end]

        return {
            "invoices": page_items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        }

    async def get_cost_trend(
        self,
        session: AsyncSession,
        org_id: str,
        months: int = 6,
    ) -> List[Dict[str, Any]]:
        """Return cost trend for the last N months.

        Extracts monthly totals from billing history.
        Returns list of {month: "YYYY-MM", cost: float}.
        """
        org = await self._get_org(session, org_id)
        billing = (org.settings or {}).get("billing", {})
        history: list = billing.get("history", [])

        # Aggregate by month
        monthly: Dict[str, float] = {}
        for record in history:
            inv_date = record.get("invoice_date", "")
            if len(inv_date) >= 7:
                month_key = inv_date[:7]  # "YYYY-MM"
                monthly[month_key] = record.get("amount", 0.0)

        # Get last N months
        today = date.today()
        result = []
        for i in range(months - 1, -1, -1):
            d = today - timedelta(days=i * 30)
            month_key = d.strftime("%Y-%m")
            result.append({
                "month": month_key,
                "cost": monthly.get(month_key, 0.0),
            })

        # Deduplicate by month key (keep first occurrence)
        seen = set()
        deduped = []
        for item in result:
            if item["month"] not in seen:
                seen.add(item["month"])
                deduped.append(item)

        return deduped

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_monthly_cost(
        seat_count: int,
        cost_per_seat: Decimal,
        discount_percent: float,
    ) -> Decimal:
        """Compute monthly cost with optional volume discount.

        Formula: seat_count * cost_per_seat * (1 - discount_percent / 100)
        """
        base = Decimal(seat_count) * cost_per_seat
        if discount_percent > 0:
            discount_factor = Decimal(str(1 - discount_percent / 100))
            base = base * discount_factor
        return base.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def _generate_invoice_record(
        org_id: str,
        period: date,
        seats: int,
        cost_per_seat: float,
        discount_pct: float,
        monthly_cost: float,
    ) -> Dict[str, Any]:
        """Generate a computed invoice record for a billing period."""
        ref_prefix = str(org_id)[:8] if org_id else "00000000"
        return {
            "invoice_date": period.isoformat(),
            "amount": monthly_cost,
            "seats": seats,
            "cost_per_seat": cost_per_seat,
            "discount_percent": discount_pct,
            "status": "paid",
            "reference_id": f"INV-{ref_prefix}-{period.strftime('%Y%m%d')}",
        }

    async def _get_org(
        self, session: AsyncSession, org_id: str
    ) -> Organization:
        """Fetch organization by ID."""
        result = await session.execute(
            select(Organization).where(
                Organization.id == UUID(org_id) if isinstance(org_id, str) else org_id
            )
        )
        org = result.scalar_one_or_none()
        if org is None:
            raise ValueError(f"Organization {org_id} not found.")
        return org

    async def _count_active_members(
        self, session: AsyncSession, org_id: str
    ) -> int:
        """Count active members in an organization."""
        result = await session.execute(
            select(func.count(OrganizationMember.id)).where(
                OrganizationMember.org_id
                == (UUID(org_id) if isinstance(org_id, str) else org_id)
            )
        )
        return result.scalar() or 0
