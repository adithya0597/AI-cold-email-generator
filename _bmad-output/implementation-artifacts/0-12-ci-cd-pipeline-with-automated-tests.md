# Story 0.12: CI/CD Pipeline with Automated Tests

Status: review

## Story

As a **developer**,
I want **automated testing and deployment on merge**,
so that **code quality is enforced and deployments are safe**.

## Acceptance Criteria

1. **AC1 - Backend Coverage Thresholds:** Given CI runs, when pytest completes, then >80% line coverage is required and >70% branch coverage is required.

2. **AC2 - Frontend Tests:** Given CI runs, when the frontend job completes, then Vitest tests pass and the build succeeds.

3. **AC3 - API Contract Validation:** Given CI runs, when Schemathesis validates, then API contracts match the OpenAPI spec.

4. **AC4 - Staging Auto-Deploy:** Given tests pass on main, when CI completes, then successful builds auto-deploy to staging.

5. **AC5 - Production Manual Approval:** Given staging is deployed, when production deploy is requested, then manual approval is required via GitHub environment protection.

6. **AC6 - Failed Tests Block Merge:** Given a PR has failing tests, when the PR is reviewed, then merge is blocked until tests pass.

## Tasks / Subtasks

- [x] Task 1: Enhance CI pipeline with coverage thresholds and contract testing (AC: #1, #2, #3)
  - [x] 1.1: Update pytest command in ci.yml to enforce `--cov-fail-under=80` and `--cov-branch`
  - [x] 1.2: Add Schemathesis job to ci.yml that validates API against OpenAPI spec
  - [x] 1.3: Add coverage artifact upload step for backend
  - [x] 1.4: Update pytest.ini coverage threshold from 70 to 80

- [x] Task 2: Add staging and production deploy jobs (AC: #4, #5)
  - [x] 2.1: Add `deploy-staging` job that runs after tests pass (needs: [backend-test, frontend-test])
  - [x] 2.2: Add `deploy-production` job with `environment: production` for manual approval gate
  - [x] 2.3: Both deploy jobs use placeholder scripts (actual infra TBD — Railway/Vercel)

- [x] Task 3: Document branch protection for merge blocking (AC: #6)
  - [x] 3.1: Add comment in ci.yml documenting required GitHub branch protection settings
  - [x] 3.2: Ensure all test jobs report proper status for branch protection rules

- [x] Task 4: Add schemathesis to requirements and configure (AC: #3)
  - [x] 4.1: Add `schemathesis` to backend requirements.txt
  - [x] 4.2: Create `backend/tests/contract/test_api_contract.py` placeholder for local contract testing

## Dev Notes

### Architecture Compliance

**CRITICAL — CI pipeline ALREADY EXISTS:**

1. **GitHub Actions workflow EXISTS:** `.github/workflows/ci.yml` with:
   - Triggers: push to main + PRs to main
   - Concurrency with cancel-in-progress
   - Backend job: Python 3.11, Redis 7, PostgreSQL 15, ruff lint, pytest with coverage
   - Frontend job: Node 20, vitest, npm build
   [Source: .github/workflows/ci.yml]

2. **pytest.ini EXISTS:** With 70% coverage threshold, asyncio auto mode, test markers
   [Source: backend/pytest.ini]

3. **Frontend tests configured:** Vitest 3.0.0 in package.json
   [Source: frontend/package.json]

**WHAT'S MISSING:**
- Coverage threshold is 70% (AC wants 80% line, 70% branch)
- No `--cov-branch` flag in CI
- No Schemathesis API contract validation
- No staging/production deploy jobs
- No coverage artifact upload
- No branch protection documentation

### Previous Story Intelligence (0-11)

- 16 email service tests passing
- All 434 unit tests passing (plus 2 pre-existing failures, 2 pre-existing errors)
- pytest.ini has `--cov-fail-under=70` — needs update to 80

### Technical Requirements

**Coverage thresholds:** Update pytest.ini and ci.yml to enforce 80% line + 70% branch.
Note: Current actual coverage is ~53% for unit tests only. The 80% threshold should apply
to tested modules only, not the entire codebase. Configure `--cov-fail-under=80` but may
need to adjust based on actual coverage after all stories complete.

**Schemathesis:** Runs against OpenAPI spec to validate API contract compliance:
```yaml
- name: Contract tests (Schemathesis)
  run: |
    cd backend
    schemathesis run http://localhost:8000/openapi.json --dry-run
```
For CI, use `--dry-run` or schema-only mode since we can't run a full API server easily.

**Deploy jobs:** Placeholder with `echo` commands since actual infrastructure (Railway/Vercel)
hasn't been chosen yet.

### Library/Framework Requirements

**New backend dependency:**
```
schemathesis>=3.30.0
```

### File Structure Requirements

**Files to CREATE:**
```
backend/tests/contract/__init__.py
backend/tests/contract/test_api_contract.py
```

**Files to MODIFY:**
```
.github/workflows/ci.yml                  # Add coverage thresholds, deploy jobs, contract testing
backend/pytest.ini                         # Update coverage threshold
backend/requirements.txt                   # Add schemathesis
```

**Files to NOT TOUCH:**
```
frontend/package.json                      # Frontend test config already correct
backend/app/main.py                        # Application code unchanged
```

### Testing Requirements

This story is primarily infrastructure configuration. The "tests" are:
- CI pipeline YAML validation (syntax)
- Coverage threshold enforcement
- Branch protection documentation
- Contract test placeholder

### References

- [Source: .github/workflows/ci.yml] — Existing CI pipeline
- [Source: backend/pytest.ini] — Test configuration
- [Source: frontend/package.json] — Frontend test scripts

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5

### Route Taken
SIMPLE (score: 4/16) — direct execution, no GSD subagents

### Debug Log References
None — clean implementation

### Completion Notes List
- Updated ci.yml with --cov-branch and --cov-fail-under=80 for backend tests
- Added coverage artifact upload step (14-day retention)
- Added contract-test job with Schemathesis --dry-run against generated OpenAPI schema
- Added deploy-staging job (placeholder, needs: backend-test + frontend-test)
- Added deploy-production job with `environment: production` for manual approval gate
- Added branch protection documentation comments at top of ci.yml
- Updated pytest.ini coverage threshold from 70 to 80 with --cov-branch
- Added schemathesis>=3.30.0 to requirements.txt
- Created contract test placeholder with 3 local schema validation tests

### Change Log
- 2026-02-01: Implemented all CI/CD enhancements

### File List
**Created:**
- `backend/tests/contract/__init__.py`
- `backend/tests/contract/test_api_contract.py`

**Modified:**
- `.github/workflows/ci.yml` — coverage thresholds, contract-test job, deploy jobs, branch protection docs
- `backend/pytest.ini` — coverage threshold 70→80, added --cov-branch
- `backend/requirements.txt` — added schemathesis>=3.30.0
