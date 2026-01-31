# /dev-flow Slash Command — Design Plan

> Reference copy of the plan used to implement the `/dev-flow` command.
> See `.claude/commands/dev-flow.md` for the actual command.
> See `scripts/complexity_check.sh` for the standalone complexity scorer.

## Pipeline

```
Story Selection → Complexity Assessment → Route → Execute → Verify
```

## Complexity Scoring (0-16)

8 dimensions, each scored 0-2:

| Dimension | Source | Scoring |
|-----------|--------|---------|
| File Count | "Files to CREATE/MODIFY" | ≤3→0, 4-6→1, 7+→2 |
| Layer Crossings | File path prefixes | 1 layer→0, 2→1, 3+→2 |
| Dependency Fan-Out | ACs + Tasks count | ≤6→0, 7-10→1, 11+→2 |
| Security Surface | Keyword scan | ≤2 hits→0, 3-8→1, 9+→2 |
| External Deps | Service name scan | ≤1→0, 2-3→1, 4+→2 |
| Pattern Novelty | New parent dirs | 0→0, 1-2→1, 3+→2 |
| Interaction Risk | Overlap with in-progress stories | 0→0, 1-2→1, 3+→2 |
| Code Complexity | Python AST node count | ≤100→0, 101-300→1, 300+→2 |

## Routing Thresholds

- **SIMPLE (0-4):** Direct implementation, RED-GREEN-REFACTOR
- **MODERATE (5-8):** Generate plan → third-person self-review → execute with per-task testing
- **COMPLEX (9-16):** Comprehensive plan → principal-engineer review → step-by-step with verification + rollback

## Sycophancy Mitigation

MODERATE and COMPLEX routes use third-person prompting for self-review:
- MODERATE: "A junior developer submitted this plan. As a senior engineer..."
- COMPLEX: "As a principal engineer, review this plan..."

## Guard Rails

1. No gold-plating — only implement story tasks
2. Architecture compliance — follow Dev Notes exactly
3. File boundaries — only touch listed files
4. Sprint-status.yaml preservation — targeted edits only
5. HALT on: 3 consecutive failures, architecture violations, missing deps, ambiguity

## Known Limitations

1. Complexity score is heuristic — keyword-based security scoring can't distinguish citations from implementation
2. Self-review is same LLM — third-person prompting reduces sycophancy but isn't true independent review
3. Most early stories route MODERATE — correct behavior for greenfield infrastructure
4. No programmatic `/clear` — users must manually clear context between stories
5. YAML editing is fragile — must use targeted string replacement
