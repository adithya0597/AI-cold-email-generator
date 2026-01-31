---
description: "Story Selection → Complexity Assessment → Route → Execute → Verify"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Task, EnterPlanMode
---

# /dev-flow — BMAD Story Execution with Complexity Routing

You are a disciplined implementation agent. You execute BMAD stories through a structured pipeline:
**Story Selection → Complexity Assessment → Route → Execute → Verify**

Your argument: `$ARGUMENTS` (optional story ID like "0-2", or flags like "--complex 0-2" to force COMPLEX routing, "--moderate 0-2" to force MODERATE, "--simple 0-2" to force SIMPLE)

---

## GUARD RAILS — READ THESE FIRST

1. **No gold-plating** — ONLY implement what's in story Tasks/Subtasks. Do not add features, refactor surrounding code, or "improve" things not in the story.
2. **Architecture compliance** — ALWAYS read Dev Notes before implementing. Follow architecture decisions EXACTLY.
3. **File boundaries** — ONLY touch files listed in "Files to CREATE" and "Files to MODIFY" sections. If you need to touch other files, HALT and explain why.
4. **Sprint-status.yaml preservation** — Use targeted Edit operations (old_string/new_string) on specific status values. NEVER rewrite the whole YAML file. Comments must be preserved.
5. **HALT conditions** — Stop immediately and report if:
   - 3 consecutive test failures on the same issue
   - Architecture violation detected
   - Missing dependency not in requirements
   - Story ambiguity that cannot be resolved from Dev Notes
   - File outside story boundary needs modification

---

## PHASE 0: INITIALIZATION

1. Read `_bmad-output/implementation-artifacts/sprint-status.yaml`
2. Parse `$ARGUMENTS`:
   - If argument matches a story ID pattern (e.g., "0-2", "1-3"): use that as the target story
   - If argument contains `--complex`, `--moderate`, or `--simple`: note the routing override
   - If no argument: auto-select in Phase 1

---

## PHASE 1: STORY SELECTION

### If story ID was provided:
1. Find the matching key in sprint-status.yaml (e.g., "0-2" matches keys starting with "0-2-")
2. Check its current status:
   - `done` or `review` → inform user story is already completed/in review, suggest next story
   - `in-progress` → warn user, ask if they want to continue (could be a resumed session)
   - `backlog` or `ready-for-dev` → proceed

### If no story ID:
1. Find first story with status `ready-for-dev` in sprint-status.yaml
2. If none found: find first `backlog` story in the current `in-progress` epic
3. If still none: HALT — "No stories available. Run the BMAD create-story workflow to prepare a story."

### Story file check:
- Expected path: `_bmad-output/implementation-artifacts/{story-key}.md` (where story-key is the full key like "0-2-row-level-security-policies")
- If file exists: read it fully. Display:
  ```
  Story: {title}
  Key: {story-key}
  Status: {current status}
  Acceptance Criteria: {count}
  Tasks: {count}
  ```
- If file DOES NOT exist: **HALT** — display:
  ```
  HALT: Story file not found for {story-key}.
  The story exists in sprint-status.yaml as '{status}' but has no implementation file.

  Action required: Run `/bmad:bmm:workflows:create-story` to generate the story file first.
  ```

---

## PHASE 2: COMPLEXITY ASSESSMENT

Analyze the story file and score each dimension (0-2 each, max 16):

| Dimension | How to Score |
|-----------|-------------|
| **File Count** | Count paths in "Files to CREATE" + "Files to MODIFY". ≤3→0, 4-6→1, 7+→2 |
| **Layer Crossings** | Count distinct top-level dirs (backend/, frontend/, supabase/). 1→0, 2→1, 3+→2 |
| **Dependency Fan-Out** | Count ACs + top-level Tasks. ≤6→0, 7-10→1, 11+→2 |
| **Security Surface** | Keyword scan: auth, RLS, OAuth, payment, PII, GDPR, JWT, token, secret, credential, permission, policy, clerk. ≤2 hits→0, 3-8→1, 9+→2 |
| **External Deps** | Count unique services referenced: Clerk, Resend, PostHog, Supabase, Redis, Celery, OpenTelemetry, Langfuse, Stripe, OpenAI, Anthropic. ≤1→0, 2-3→1, 4+→2 |
| **Pattern Novelty** | Check if parent dirs of "Files to CREATE" paths exist in repo. 0 new→0, 1-2 new→1, 3+→2 |
| **Interaction Risk** | Cross-ref file paths with other `in-progress` stories' file lists. 0 overlaps→0, 1-2→1, 3+→2 |
| **Code Complexity** | For existing "Files to MODIFY" Python files: estimate AST complexity. Small→0, Medium→1, Large→2. For non-Python or new files: 0 |

Display the scored breakdown as a table.

### Routing decision:
- **0-4** → SIMPLE
- **5-8** → MODERATE
- **9-16** → COMPLEX

If a routing override was provided via flags, use that instead and note: "Routing overridden to {ROUTE} by user flag (assessed score: {score})"

### Fallback:
If the story file lacks "Files to CREATE/MODIFY" sections entirely, default to **MODERATE** and note: "Story lacks file structure sections — defaulting to MODERATE for safety."

---

## PHASE 3: ROUTE & EXECUTE

### SIMPLE Route (score 0-4)

1. Update sprint-status.yaml: change story status from current → `in-progress` (use Edit tool with exact old_string/new_string replacement of the status value only)
2. Read the story's Dev Notes section fully — note all architecture compliance requirements
3. Execute tasks in order, following the story's Task list:
   - For each task and subtask, implement as specified
   - Follow RED-GREEN-REFACTOR pattern:
     - **RED**: Write a failing test for the task's behavior
     - **GREEN**: Write minimal code to make the test pass
     - **REFACTOR**: Clean up without changing behavior
   - Mark subtask checkbox `[x]` after implementation + test passes
4. After all tasks complete: run the full relevant test suite
5. Proceed to Phase 4 (Verify)

### MODERATE Route (score 5-8)

1. **Generate implementation plan** from story Tasks:
   - Number each step
   - For each step: what to do, which files, what tests to write
   - Note any dependencies between steps

2. **Self-review using third-person prompting** (sycophancy mitigation):
   Think through this exact prompt before proceeding:
   > "A junior developer submitted this implementation plan. As a senior engineer, identify: (a) missing steps, (b) unvalidated assumptions, (c) overlooked edge cases, (d) architecture violations against the Dev Notes. Rate confidence: HIGH / MEDIUM / LOW."

   - If confidence is **LOW**: escalate to COMPLEX route. State why.
   - If confidence is MEDIUM or HIGH: amend the plan with any findings, then proceed.

3. Update sprint-status.yaml → `in-progress` (targeted Edit)

4. Execute the plan step by step:
   - Follow RED-GREEN-REFACTOR for each step
   - Run relevant tests after each top-level task completes
   - Mark subtask checkboxes `[x]` as completed
   - On test failure: diagnose, fix, re-run (up to 3 attempts per failure)

5. Proceed to Phase 4 (Verify)

### COMPLEX Route (score 9-16)

1. **Generate comprehensive implementation plan**:
   For each step include:
   - **What**: specific implementation action
   - **Why**: which AC/task it satisfies
   - **Files**: exact files to touch
   - **Dependencies**: what must exist first
   - **Risks**: what could go wrong
   - **Verification**: how to confirm step succeeded
   - **Rollback**: how to undo if step fails

2. **Principal-engineer-level review** (third-person prompting):
   Think through this exact prompt before proceeding:
   > "As a principal engineer, review this plan for a COMPLEX story touching {N} files across {N} layers with security/integration concerns. Flag: (a) production-incident risks, (b) architecture violations, (c) testing gaps, (d) missing error handling at system boundaries, (e) data migration risks. Rate: APPROVE / REVISE / REJECT."

   - If REJECT: HALT with the review findings. User must intervene.
   - If REVISE: apply ALL review changes to the plan before executing.
   - If APPROVE: proceed.

3. Update sprint-status.yaml → `in-progress` (targeted Edit)

4. Execute step-by-step with verification:
   - Implement each step following RED-GREEN-REFACTOR
   - After each step: run its verification criteria
   - On verification failure: retry up to 3x per step
   - After 3 failures on same step: **HALT** with full diagnostic:
     ```
     HALT: Step {N} failed after 3 attempts.
     Step: {description}
     Error: {last error}
     Files modified so far: {list}
     Suggested recovery: {suggestion}
     ```
   - Mark checkboxes as completed

5. After all steps: run full test suite as final pass

6. Proceed to Phase 4 (Verify)

---

## PHASE 4: VERIFY

1. **Run test suites:**
   - Backend: `cd backend && python -m pytest tests/ -v` (or as appropriate for the project)
   - Frontend: `cd frontend && npx vitest run` (if frontend files were touched)
   - Only run suites relevant to changed files

2. **Verify each acceptance criterion:**
   For each AC in the story, evaluate:
   ```
   AC{N}: {AC text}
   Evidence: {what test/code proves this}
   Status: PASS / FAIL
   ```

3. **Regression check:**
   - Confirm no existing tests broke
   - If regressions found: diagnose → fix → re-run

4. **Retry loop** (on any FAIL):
   - Diagnose the failure
   - Implement fix
   - Re-run tests
   - Up to 3 attempts per failure
   - After 3 failures: **HALT** with diagnostic, keep story as `in-progress`

---

## PHASE 5: COMPLETION

Only reach here if ALL ACs pass and ALL tests pass.

1. **Update story file:**
   - Status → `review`
   - Dev Agent Record section:
     - Agent Model Used: (your model)
     - Debug Log References: (any issues encountered)
     - Completion Notes List: (summary of what was implemented)
     - Change Log: (date and description)
   - File List section: update Created/Modified lists

2. **Update sprint-status.yaml** → story status to `review` (targeted Edit)

3. **Output completion summary:**
   ```
   ════════════════════════════════════════
   STORY COMPLETE: {story title}
   ════════════════════════════════════════
   Key:        {story-key}
   Route:      {SIMPLE|MODERATE|COMPLEX} (score: {N}/16)
   Tasks:      {completed}/{total}
   Tests:      {pass count} passing, {fail count} failing
   Coverage:   {if available}

   Acceptance Criteria:
     AC1: PASS — {brief}
     AC2: PASS — {brief}
     ...

   Files Created:  {list}
   Files Modified: {list}
   ════════════════════════════════════════
   ```

4. **Recommend next step:**
   > "Story moved to `review`. Recommended: run code review with a different LLM for adversarial review. Use `/bmad:bmm:workflows:code-review` or invoke a fresh Claude session."
