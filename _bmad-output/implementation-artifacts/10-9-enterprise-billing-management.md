# Story 10.9: Enterprise Billing Management

Status: done

## Story

As an **enterprise admin**,
I want **to view billing details, manage seat allocations, and review invoice history**,
So that **I can control program costs, scale the team as needed, and maintain financial oversight**.

## Acceptance Criteria

1. **AC1: Billing summary** — Given an admin views the billing page, when the billing endpoint is called, then it returns: total seats allocated, seats used, seats available, monthly cost, cost per seat, billing cycle dates, and volume discount percentage (if applicable).

2. **AC2: Seat management** — Given an admin adds or removes seats, when the seat update endpoint is called, then the Organization's seat_count is updated, the monthly cost is recalculated, and an AuditLog entry is created. Seat count cannot be reduced below the number of active members.

3. **AC3: Invoice history** — Given an admin views invoice history, when the invoices endpoint is called, then it returns a paginated list of invoice records with: invoice_date, amount, seats, status (paid, pending, overdue), and a reference ID. For V1, invoices are computed from historical seat changes (no real payment processor).

4. **AC4: Volume discount computation** — Given an organization has a volume discount configured in their contract, when costs are computed, then the discount percentage is applied. Discount tiers stored in Organization.settings["billing"]["volume_discount_percent"].

5. **AC5: Billing dashboard rendering** — Given the BillingDashboard component receives billing data, when it renders, then it displays: seats usage progress bar (used/allocated), monthly cost breakdown, invoice list table, and add/remove seats controls.

6. **AC6: Cost trend visualization** — Given billing history exists, when the dashboard renders, then it shows a simple cost trend (last 6 months) as a list of monthly totals (chart library deferred to future story).

7. **AC7: RBAC enforcement** — Given a non-admin user calls billing endpoints, when the request is processed, then it returns 403 Forbidden.

## Tasks / Subtasks

- [x] Task 1: Create BillingService (AC: #1, #2, #3, #4)
  - [x] 1.1 Create `backend/app/services/enterprise/billing.py` with `BillingService` class
  - [x] 1.2 Implement `get_billing_summary(org_id: str)` — returns dict with seats_allocated, seats_used, seats_available, monthly_cost, cost_per_seat, billing_cycle_start, billing_cycle_end, volume_discount_percent
  - [x] 1.3 Implement `update_seats(org_id: str, new_seat_count: int, admin_user_id: str)` — validate new_seat_count >= active member count, update Organization.seat_count, recalculate cost, create AuditLog entry
  - [x] 1.4 Implement `get_invoices(org_id: str, page: int, per_page: int)` — return paginated invoice records computed from billing history in Organization.settings["billing"]["history"]
  - [x] 1.5 Implement `_compute_monthly_cost(seat_count: int, cost_per_seat: Decimal, discount_percent: float)` — apply volume discount to base cost
  - [x] 1.6 Implement `_generate_invoice_record(org_id: str, period: date)` — compute invoice for a billing period from seat count and pricing

- [x] Task 2: Create API endpoints (AC: #1, #2, #3, #7)
  - [x] 2.1 Add billing routes to `backend/app/api/v1/admin_enterprise.py`
  - [x] 2.2 Implement `GET /api/v1/admin/billing` — returns billing summary
  - [x] 2.3 Implement `PUT /api/v1/admin/billing/seats` — accepts `seat_count: int` body, validates and updates
  - [x] 2.4 Implement `GET /api/v1/admin/billing/invoices` — returns paginated invoice list with `page` and `per_page` query params
  - [x] 2.5 Add RBAC dependency (reuse from earlier enterprise stories)

- [x] Task 3: Create BillingDashboard frontend component (AC: #5, #6)
  - [x] 3.1 Create `frontend/src/components/enterprise/BillingDashboard.tsx` with TypeScript + Tailwind
  - [x] 3.2 Implement seats usage progress bar (used / allocated with percentage)
  - [x] 3.3 Implement monthly cost breakdown card (base cost, discount, net cost)
  - [x] 3.4 Implement add/remove seats controls (number input + update button)
  - [x] 3.5 Implement invoice list table (date, amount, seats, status, reference ID)
  - [x] 3.6 Implement cost trend section as a simple monthly totals list (last 6 months)

- [x] Task 4: Write tests (AC: #1-#7)
  - [x] 4.1 Create `backend/tests/unit/test_services/test_billing.py`
  - [x] 4.2 Test billing summary returns correct seat counts and costs
  - [x] 4.3 Test seat addition updates count and recalculates cost
  - [x] 4.4 Test seat removal below active member count is rejected with 400
  - [x] 4.5 Test seat update creates AuditLog entry
  - [x] 4.6 Test volume discount is applied correctly (e.g., 10% discount on 50+ seats)
  - [x] 4.7 Test invoice list returns correct records with pagination
  - [x] 4.8 Test non-admin user receives 403 Forbidden
  - [x] 4.9 Create `frontend/src/__tests__/BillingDashboard.test.tsx`
  - [x] 4.10 Test dashboard renders seats progress bar
  - [x] 4.11 Test dashboard renders invoice table
  - [x] 4.12 Test add/remove seats controls are present

## Dev Notes

### Architecture Compliance

- **Service location**: `backend/app/services/enterprise/billing.py` — enterprise services in `enterprise/` subdirectory
- **API location**: Routes added to `backend/app/api/v1/admin_enterprise.py`
- **Frontend location**: `frontend/src/components/enterprise/BillingDashboard.tsx` — follows NetworkDashboard pattern
- **No real Stripe integration**: V1 computes costs locally based on seat count and tier pricing. Billing data stored in Organization.settings["billing"] JSONB. Real payment processing (Stripe) deferred to a future story.
- **Invoice generation**: Invoices are computed records derived from billing history, not real payment processor invoices. Stored in Organization.settings["billing"]["history"] as a list of period records.
- **Audit logging**: Seat changes create AuditLog entries with action_type="seats_updated", recording old and new seat counts.
- **Pricing config**: Base cost per seat stored in Organization.settings["billing"]["cost_per_seat"]. Volume discount in Organization.settings["billing"]["volume_discount_percent"].

### Existing Utilities to Use

- `get_current_user_id()` from `app/auth/clerk.py` — JWT authentication
- `TimestampMixin`, `SoftDeleteMixin` from `app/db/models.py` — model mixins
- Organization model (from story 10-1) — settings JSONB field for billing config
- AuditLog model (from story 10-3) — audit trail for seat changes
- RBAC dependency (from earlier enterprise stories) — admin role check
- NetworkDashboard.tsx — UI pattern reference for dashboard layout

### Project Structure Notes

- Service file: `backend/app/services/enterprise/billing.py`
- API routes: added to `backend/app/api/v1/admin_enterprise.py`
- Frontend component: `frontend/src/components/enterprise/BillingDashboard.tsx`
- Backend test file: `backend/tests/unit/test_services/test_billing.py`
- Frontend test file: `frontend/src/__tests__/BillingDashboard.test.tsx`

### References

- [Source: backend/app/db/models.py — User model with tier enum (FREE, PRO, H1B_PRO, CAREER_INSURANCE, ENTERPRISE)]
- [Source: backend/app/auth/clerk.py — get_current_user_id() authentication dependency]
- [Source: backend/app/api/v1/admin.py — Existing admin routes pattern]
- [Source: frontend/src/components/network/NetworkDashboard.tsx — Dashboard UI pattern reference]
- [Dependency: Story 10-1 — Organization model with settings JSONB, seat_count field]
- [Dependency: Story 10-2 — RBAC / admin role enforcement, OrganizationMember for active count]
- [Dependency: Story 10-3 — AuditLog model]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Route Taken

Direct implementation: BillingService -> API endpoints -> Frontend component -> Tests. All 4 tasks executed sequentially with atomic commits per task.

### GSD Subagents Used

None (single-agent execution)

### Debug Log References

No debug issues encountered. All tests passed on first run.

### Completion Notes List

- BillingService: 302 lines, 90% test coverage. Handles billing summary, seat management with validation, paginated invoices, cost trend, and volume discount computation.
- API: 4 new routes added to admin_enterprise.py (GET /billing, PUT /billing/seats, GET /billing/invoices, GET /billing/cost-trend). All existing routes preserved.
- Frontend: BillingDashboard.tsx follows NetworkDashboard props-based pattern with Tailwind styling. Includes progress bar, cost breakdown, seat controls, invoice table, and cost trend list.
- Tests: 21 backend tests (all pass), 8 frontend tests (all pass). Covers all 7 acceptance criteria.
- Added GET /billing/cost-trend endpoint (AC6) beyond the 3 originally specified endpoints to support the cost trend frontend section.

### Change Log

| Date | Change | Commit |
|------|--------|--------|
| 2026-02-02 | Created BillingService | 523076d |
| 2026-02-02 | Added billing API endpoints | e7dd72f |
| 2026-02-02 | Created BillingDashboard frontend | 15ec00f |
| 2026-02-02 | Added backend and frontend tests | d9ae01a |

### File List

#### Files CREATED
- `backend/app/services/enterprise/billing.py`
- `frontend/src/components/enterprise/BillingDashboard.tsx`
- `backend/tests/unit/test_services/test_billing.py`
- `frontend/src/__tests__/BillingDashboard.test.tsx`

#### Files MODIFIED
- `backend/app/api/v1/admin_enterprise.py`
