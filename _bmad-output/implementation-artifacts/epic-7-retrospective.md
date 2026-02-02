# Epic 7 Retrospective: H1B Specialist Experience

Status: done

## Summary

Epic 7 delivered a complete H1B specialist experience across 10 stories, covering data aggregation from public DOL/USCIS disclosure data, sponsor scorecard UI, approval rate visualization, verified sponsor badges, H1B job filters, data freshness infrastructure, and empty states. All stories were assessed as SIMPLE complexity and completed successfully with 107 tests passing and all HIGH/MEDIUM code review issues resolved, including a SQL injection vulnerability in ILIKE search and missing auth guards.

## Metrics

- Stories: 10 completed (7-1 through 7-10)
- Tests: 107 passing (76 backend + 31 frontend)
- Code Review Issues: 22 found (7 HIGH, 9 MEDIUM, 6 LOW), all HIGH and MEDIUM fixed
- Complexity: All 10 stories scored SIMPLE (0-4) in assessment

## What Went Well

- All stories scored SIMPLE in complexity assessment, reflecting good story decomposition in the epic plan
- Consistent patterns across all 3 data source clients (DOL LCA, USCIS public data) made implementation predictable after the first client was built
- Strong test coverage from the start (107 tests) caught regressions early and made code review fixes safe
- Code review caught real security issues (SQL injection via ILIKE metacharacters, auth bypass on endpoints) that pure TDD missed -- validating the review step in the workflow
- Frontend used Tailwind-only bar charts for approval rate visualization, avoiding a charting library dependency and keeping the bundle lean
- Tier gating was applied consistently to all H1B endpoints (h1b_pro, career_insurance, enterprise)

## What Could Improve

- **Story File Lists left empty in Dev Agent Record**: Several stories did not populate the File List section, making it harder to trace what changed per story
- **Priority refresh is still a stub**: AC#3 of story 7-9 (Sponsor Data Freshness Infrastructure) has priority-based refresh as a stub rather than a full implementation -- this should be tracked as tech debt
- **No integration tests for full pipeline end-to-end**: The Celery pipeline (fetch -> normalize -> aggregate -> upsert -> API query) is only tested in isolated units; a full integration test would increase confidence
- **Frontend `useSponsorSearch` hook lacks dedicated test coverage**: The hook was created in story 7-5 but only tested indirectly through component tests, not with dedicated hook-level tests
- **LOW code review issues left unfixed**: 6 LOW-severity issues were not addressed; while acceptable per policy, they accumulate as minor tech debt

## Key Decisions & Rationale

- **Used DOL/USCIS public disclosure CSV data instead of scraping H1BGrader/MyVisaJobs**: Both H1BGrader and MyVisaJobs prohibit scraping via robots.txt and Terms of Service. The underlying data (DOL LCA disclosures, USCIS approval statistics) is publicly available, so we built clients against the authoritative government sources directly. This is both legally safer and more reliable.
- **Added LRU caching for parsed CSV data**: DOL disclosure CSVs are large files. Without caching, each sponsor query would trigger an O(N) re-parse. An LRU cache keyed by file hash avoids repeated parsing and keeps lookup fast.
- **Frontend uses Tailwind-only bar charts (no charting library)**: The approval rate visualization only needs simple horizontal bars. Using Tailwind utility classes avoids adding a charting library (e.g., Chart.js, Recharts) to the bundle for a single use case.
- **Tier gating on all H1B endpoints**: H1B data is a premium feature. Gating was applied at the API layer to h1b_pro, career_insurance, and enterprise tiers, with free and pro tiers receiving 403.

## Lessons Learned

- **ILIKE queries need metacharacter escaping even with parameterized queries**: Parameterized queries prevent SQL injection for values, but ILIKE pattern characters (%, _, \) in user input still alter query semantics. Explicit escaping of these metacharacters is required.
- **Session scope matters -- do not access row proxies after session close**: SQLAlchemy row proxy objects become detached after the session closes. Accessing attributes on detached proxies raises errors. Convert rows to dicts/models within the session context.
- **Lazy imports in Celery tasks work but mock patch paths must target source module**: When Celery tasks use lazy imports inside the function body, `unittest.mock.patch` must target the module where the import resolves, not the call site in the task function. This is a subtle but recurring gotcha.
- **Async mock streaming (httpx `aiter_bytes`) needs proper async generator factories**: Mocking httpx streaming responses requires returning async generators from factory functions, not bare async generators (which are exhausted after first use).
- **Frontend components need SSR guards for browser APIs**: Components that access `localStorage` or `window` must include SSR guards (`typeof window !== 'undefined'`) to avoid build-time and server-render failures.
- **Code review catches security issues that TDD misses**: TDD validates behavior against expected inputs. Code review with a security lens catches issues like SQL injection patterns and missing auth guards that tests do not exercise by default.

## Recommendations for Next Epic

- **Establish an integration test pattern**: Before Epic 8 (Interview Preparation), create a reusable pattern for end-to-end pipeline tests (Celery task -> service -> DB -> API) so each epic has at least one integration test
- **Enforce File List population in Dev Agent Record**: Add a checklist item or validation step to ensure story files are tracked, improving traceability
- **Address the priority refresh stub**: Schedule a small follow-up task to complete AC#3 of story 7-9 before it becomes a production gap
- **Add dedicated hook tests for shared frontend hooks**: Hooks like `useSponsorSearch` that are reused across multiple components should have standalone test coverage using `renderHook`
- **Continue the "public data first" pattern for external integrations**: The DOL/USCIS approach worked well and should be the default strategy for Epic 8's company research synthesis (story 8-2) -- prefer official APIs and public datasets over scraping
