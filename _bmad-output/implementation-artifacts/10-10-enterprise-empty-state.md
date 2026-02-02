# Story 10.10: Enterprise Empty State

Status: done

## Story

As an **enterprise admin visiting the admin dashboard for the first time**,
I want **to see a guided setup experience with clear steps and progress tracking**,
So that **I can quickly configure my organization's career transition program without confusion**.

## Acceptance Criteria

1. **AC1: Empty state heading** — Given the enterprise dashboard has no configuration completed, when the admin views the dashboard, then they see a heading: "Set up your organization's career transition program" with a supportive subheading.

2. **AC2: Step-by-step guide** — Given the empty state is displayed, when the admin views the setup steps, then they see an ordered list of steps: (1) Upload company logo, (2) Customize welcome message, (3) Set autonomy defaults, (4) Upload employee list. Each step has a title, brief description, and action button.

3. **AC3: Progress tracker** — Given some setup steps are completed, when the admin views the empty state, then a progress tracker shows completion percentage (e.g., "2 of 4 steps complete — 50%") with a visual progress bar.

4. **AC4: Step completion callbacks** — Given a step's action button is clicked, when the admin completes the step action, then the step is marked as complete (checkmark icon), the progress percentage updates, and the next incomplete step is highlighted.

5. **AC5: Help link** — Given the empty state is displayed, when the admin views the bottom section, then there is a "Need help getting started?" link/CTA that opens the help documentation (external URL placeholder).

6. **AC6: Dismissal on completion** — Given all setup steps are marked complete, when the admin views the dashboard, then the empty state is no longer shown and the full admin dashboard is displayed instead.

7. **AC7: Accessibility** — Given the empty state component renders, when screen readers navigate it, then all interactive elements have appropriate `aria-label` attributes, the progress bar has `aria-valuenow`/`aria-valuemin`/`aria-valuemax`, and step status is communicated via `aria-current`.

## Tasks / Subtasks

- [x] Task 1: Create EnterpriseEmptyState component (AC: #1, #2, #3, #4, #5, #6, #7)
  - [x] 1.1 Create `frontend/src/components/enterprise/EnterpriseEmptyState.tsx` with TypeScript + Tailwind
  - [x] 1.2 Implement heading section: "Set up your organization's career transition program" with subheading
  - [x] 1.3 Implement setup steps list with four steps, each containing: step number, title, description, action button, completion state (checkmark when done)
  - [x] 1.4 Implement progress tracker bar with percentage text (e.g., "2 of 4 steps complete — 50%") and visual progress bar using Tailwind width utilities
  - [x] 1.5 Implement step completion callbacks: props accept `completedSteps: Set<number>` and `onStepAction: (stepNumber: number) => void`
  - [x] 1.6 Implement help link CTA at bottom: "Need help getting started?" with `href` prop (default to placeholder URL)
  - [x] 1.7 Add accessibility attributes: `aria-label` on buttons, `aria-valuenow`/`aria-valuemin`/`aria-valuemax` on progress bar, `aria-current="step"` on active step
  - [x] 1.8 Implement conditional rendering: component returns `null` when all steps are complete (parent shows full dashboard)

- [x] Task 2: Write tests (AC: #1-#7)
  - [x] 2.1 Create `frontend/src/__tests__/EnterpriseEmptyState.test.tsx`
  - [x] 2.2 Test heading "Set up your organization's career transition program" renders
  - [x] 2.3 Test all four setup steps render with titles and descriptions
  - [x] 2.4 Test progress percentage shows "0 of 4 steps complete — 0%" when no steps done
  - [x] 2.5 Test progress percentage shows "2 of 4 steps complete — 50%" when two steps done
  - [x] 2.6 Test progress percentage shows "4 of 4 steps complete — 100%" when all steps done
  - [x] 2.7 Test completed step shows checkmark icon and completed styling
  - [x] 2.8 Test step action button calls `onStepAction` callback with correct step number
  - [x] 2.9 Test help link renders with correct text and href
  - [x] 2.10 Test component returns null when all steps complete
  - [x] 2.11 Test `aria-label` attributes present on action buttons
  - [x] 2.12 Test progress bar has `aria-valuenow`, `aria-valuemin`, `aria-valuemax` attributes

## Dev Notes

### Architecture Compliance

- **Frontend-only story**: No backend changes required. This is a presentational component with props-driven state.
- **Component location**: `frontend/src/components/enterprise/EnterpriseEmptyState.tsx` — enterprise components in `enterprise/` subdirectory
- **Pattern reference**: Follow `NetworkEmptyState.tsx` component pattern — heading, descriptive text, CTA, props for state
- **React + Tailwind only**: No additional UI libraries. Use Tailwind utility classes for styling, progress bar, and responsive layout.
- **Props interface**: Component accepts `completedSteps: Set<number>`, `onStepAction: (stepNumber: number) => void`, and optional `helpUrl: string`. Parent component manages step completion state.
- **Accessibility**: Use semantic HTML (`ol` for ordered steps, `progress` or `div[role="progressbar"]` for progress bar). All interactive elements must have `aria-label`.

### Existing Utilities to Use

- `NetworkEmptyState.tsx` — reference pattern for empty state component structure, heading, CTA layout
- Tailwind CSS — utility classes for layout, progress bar, responsive design
- React Testing Library — for component tests (following existing test patterns)

### Project Structure Notes

- Component file: `frontend/src/components/enterprise/EnterpriseEmptyState.tsx`
- Test file: `frontend/src/__tests__/EnterpriseEmptyState.test.tsx`

### References

- [Source: frontend/src/components/network/NetworkEmptyState.tsx — Empty state component pattern reference]
- [Source: frontend/src/components/network/NetworkDashboard.tsx — Dashboard component pattern reference]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Route Taken

Direct execution: Task 1 (component) -> Task 2 (tests) -> verify -> commit

### GSD Subagents Used

None (single-agent execution)

### Debug Log References

None (all 16 tests passed on first run)

### Completion Notes List

- All 7 ACs satisfied
- Component follows NetworkEmptyState.tsx pattern (heading, CTA, props-driven state)
- 16 tests covering all ACs including accessibility
- No deviations from plan

### Change Log

- a194163: feat(10-10): create EnterpriseEmptyState component
- 3e48f9b: test(10-10): add EnterpriseEmptyState tests (16 passing)

### File List

#### Files to CREATE
- `frontend/src/components/enterprise/EnterpriseEmptyState.tsx`
- `frontend/src/__tests__/EnterpriseEmptyState.test.tsx`

#### Files to MODIFY
- (none)
