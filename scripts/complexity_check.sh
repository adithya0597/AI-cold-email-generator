#!/usr/bin/env bash
# complexity_check.sh — Zero-token BMAD story complexity scorer
# Usage: bash scripts/complexity_check.sh <story-file.md> [sprint-status.yaml]
#
# Outputs a complexity score (0-16) with routing recommendation.
# No LLM tokens consumed — pure text analysis.

set -euo pipefail

STORY_FILE="${1:-}"
SPRINT_STATUS="${2:-_bmad-output/implementation-artifacts/sprint-status.yaml}"

if [[ -z "$STORY_FILE" ]]; then
  echo "Usage: complexity_check.sh <story-file.md> [sprint-status.yaml]"
  echo ""
  echo "Example: bash scripts/complexity_check.sh _bmad-output/implementation-artifacts/0-2-row-level-security-policies.md"
  exit 1
fi

if [[ ! -f "$STORY_FILE" ]]; then
  echo "ERROR: Story file not found: $STORY_FILE"
  exit 1
fi

STORY_CONTENT="$(cat "$STORY_FILE")"

# Track total score
TOTAL=0

# Helper: clamp value to 0-2 range
clamp() {
  local val="$1"
  if (( val < 0 )); then echo 0
  elif (( val > 2 )); then echo 2
  else echo "$val"
  fi
}

# ─────────────────────────────────────────────
# Dimension 1: File Count (0-2)
# Count files in "Files to CREATE" and "Files to MODIFY" sections
# ─────────────────────────────────────────────
FILE_PATHS=()
IN_FILE_SECTION=0

while IFS= read -r line; do
  # Detect "Files to CREATE" or "Files to MODIFY" markers
  if echo "$line" | grep -qiE '^\*\*Files to (CREATE|MODIFY)'; then
    IN_FILE_SECTION=1
    continue
  fi
  # Detect end of file section (next ** header or blank line after content)
  if [[ $IN_FILE_SECTION -eq 1 ]]; then
    if echo "$line" | grep -qE '^\*\*'; then
      IN_FILE_SECTION=0
      continue
    fi
    # Extract file paths from code blocks or plain lines
    path=$(echo "$line" | sed -E 's/^```$//' | sed -E 's/#.*$//' | xargs)
    if [[ -n "$path" && "$path" != '```' ]]; then
      FILE_PATHS+=("$path")
    fi
  fi
done <<< "$STORY_CONTENT"

FILE_COUNT=${#FILE_PATHS[@]}
if (( FILE_COUNT <= 3 )); then
  FILE_SCORE=0
elif (( FILE_COUNT <= 6 )); then
  FILE_SCORE=1
else
  FILE_SCORE=2
fi
TOTAL=$((TOTAL + FILE_SCORE))

# ─────────────────────────────────────────────
# Dimension 2: Layer Crossings (0-2)
# Check how many distinct layers (backend/, frontend/, supabase/, etc.)
# ─────────────────────────────────────────────
LAYERS=()
for fp in "${FILE_PATHS[@]}"; do
  layer=$(echo "$fp" | cut -d'/' -f1)
  if [[ -n "$layer" && ! " ${LAYERS[*]:-} " =~ " $layer " ]]; then
    LAYERS+=("$layer")
  fi
done

LAYER_COUNT=${#LAYERS[@]}
if (( LAYER_COUNT <= 1 )); then
  LAYER_SCORE=0
elif (( LAYER_COUNT == 2 )); then
  LAYER_SCORE=1
else
  LAYER_SCORE=2
fi
TOTAL=$((TOTAL + LAYER_SCORE))

# ─────────────────────────────────────────────
# Dimension 3: Dependency Fan-Out (0-2)
# Count acceptance criteria + top-level tasks
# ─────────────────────────────────────────────
AC_COUNT=$(echo "$STORY_CONTENT" | grep -cE '^\d+\.\s+\*\*AC' || true)
TASK_COUNT=$(echo "$STORY_CONTENT" | grep -cE '^- \[[ x]\] Task' || true)
FANOUT=$((AC_COUNT + TASK_COUNT))

if (( FANOUT <= 6 )); then
  FANOUT_SCORE=0
elif (( FANOUT <= 10 )); then
  FANOUT_SCORE=1
else
  FANOUT_SCORE=2
fi
TOTAL=$((TOTAL + FANOUT_SCORE))

# ─────────────────────────────────────────────
# Dimension 4: Security Surface (0-2)
# Keyword scan for security-related concepts
# ─────────────────────────────────────────────
SECURITY_KEYWORDS="auth|RLS|row.level.security|OAuth|payment|PII|GDPR|CCPA|encryption|JWT|token|secret|credential|permission|role|policy|clerk"
SEC_HITS=$(echo "$STORY_CONTENT" | grep -ciE "$SECURITY_KEYWORDS" || true)

if (( SEC_HITS <= 2 )); then
  SEC_SCORE=0
elif (( SEC_HITS <= 8 )); then
  SEC_SCORE=1
else
  SEC_SCORE=2
fi
TOTAL=$((TOTAL + SEC_SCORE))

# ─────────────────────────────────────────────
# Dimension 5: External Dependencies (0-2)
# Count unique external service mentions
# ─────────────────────────────────────────────
EXT_SERVICES="Clerk|Resend|PostHog|Supabase|Redis|Celery|OpenTelemetry|Langfuse|Stripe|SendGrid|Twilio|AWS|GCP|Azure|OpenAI|Anthropic|Pinecone|Weaviate"
EXT_HITS=0
for svc in $(echo "$EXT_SERVICES" | tr '|' '\n'); do
  if echo "$STORY_CONTENT" | grep -qi "$svc"; then
    EXT_HITS=$((EXT_HITS + 1))
  fi
done

if (( EXT_HITS <= 1 )); then
  EXT_SCORE=0
elif (( EXT_HITS <= 3 )); then
  EXT_SCORE=1
else
  EXT_SCORE=2
fi
TOTAL=$((TOTAL + EXT_SCORE))

# ─────────────────────────────────────────────
# Dimension 6: Pattern Novelty (0-2)
# Check if parent directories of "Files to CREATE" exist
# ─────────────────────────────────────────────
NOVEL_COUNT=0
CREATE_SECTION=0
CREATE_FILES=()

while IFS= read -r line; do
  if echo "$line" | grep -qiE '^\*\*Files to CREATE'; then
    CREATE_SECTION=1
    continue
  fi
  if [[ $CREATE_SECTION -eq 1 ]]; then
    if echo "$line" | grep -qE '^\*\*'; then
      CREATE_SECTION=0
      continue
    fi
    path=$(echo "$line" | sed -E 's/#.*$//' | xargs)
    if [[ -n "$path" && "$path" != '```' ]]; then
      CREATE_FILES+=("$path")
    fi
  fi
done <<< "$STORY_CONTENT"

for fp in "${CREATE_FILES[@]}"; do
  parent_dir=$(dirname "$fp")
  if [[ ! -d "$parent_dir" ]]; then
    NOVEL_COUNT=$((NOVEL_COUNT + 1))
  fi
done

if (( NOVEL_COUNT == 0 )); then
  NOVEL_SCORE=0
elif (( NOVEL_COUNT <= 2 )); then
  NOVEL_SCORE=1
else
  NOVEL_SCORE=2
fi
TOTAL=$((TOTAL + NOVEL_SCORE))

# ─────────────────────────────────────────────
# Dimension 7: Interaction Risk (0-2)
# Cross-reference file paths with other in-progress stories
# ─────────────────────────────────────────────
INTERACTION_SCORE=0
if [[ -f "$SPRINT_STATUS" ]]; then
  # Find in-progress stories (not this one)
  STORY_KEY=$(basename "$STORY_FILE" .md)
  IN_PROGRESS_STORIES=$(grep -E ': in-progress' "$SPRINT_STATUS" | grep -v "^  epic" | sed 's/:.*//' | xargs || true)

  OVERLAP_COUNT=0
  for ip_story in $IN_PROGRESS_STORIES; do
    ip_story=$(echo "$ip_story" | xargs)
    [[ "$ip_story" == "$STORY_KEY" ]] && continue
    IP_FILE="_bmad-output/implementation-artifacts/${ip_story}.md"
    if [[ -f "$IP_FILE" ]]; then
      for fp in "${FILE_PATHS[@]}"; do
        clean_fp=$(echo "$fp" | sed 's/ *#.*//')
        if grep -qF "$clean_fp" "$IP_FILE" 2>/dev/null; then
          OVERLAP_COUNT=$((OVERLAP_COUNT + 1))
        fi
      done
    fi
  done

  if (( OVERLAP_COUNT == 0 )); then
    INTERACTION_SCORE=0
  elif (( OVERLAP_COUNT <= 2 )); then
    INTERACTION_SCORE=1
  else
    INTERACTION_SCORE=2
  fi
fi
TOTAL=$((TOTAL + INTERACTION_SCORE))

# ─────────────────────────────────────────────
# Dimension 8: Code Complexity (0-2)
# Python AST node count for existing "Files to MODIFY"
# ─────────────────────────────────────────────
MODIFY_SECTION=0
MODIFY_FILES=()

while IFS= read -r line; do
  if echo "$line" | grep -qiE '^\*\*Files to MODIFY'; then
    MODIFY_SECTION=1
    continue
  fi
  if [[ $MODIFY_SECTION -eq 1 ]]; then
    if echo "$line" | grep -qE '^\*\*'; then
      MODIFY_SECTION=0
      continue
    fi
    path=$(echo "$line" | sed -E 's/#.*$//' | xargs)
    if [[ -n "$path" && "$path" != '```' ]]; then
      MODIFY_FILES+=("$path")
    fi
  fi
done <<< "$STORY_CONTENT"

MAX_AST=0
for fp in "${MODIFY_FILES[@]}"; do
  clean_fp=$(echo "$fp" | sed 's/ *#.*//')
  if [[ -f "$clean_fp" && "$clean_fp" == *.py ]]; then
    ast_count=$(python3 -c "
import ast, sys
try:
    with open('$clean_fp') as f:
        tree = ast.parse(f.read())
    print(sum(1 for _ in ast.walk(tree)))
except:
    print(0)
" 2>/dev/null || echo 0)
    if (( ast_count > MAX_AST )); then
      MAX_AST=$ast_count
    fi
  fi
done

if (( MAX_AST <= 100 )); then
  COMPLEXITY_SCORE=0
elif (( MAX_AST <= 300 )); then
  COMPLEXITY_SCORE=1
else
  COMPLEXITY_SCORE=2
fi
TOTAL=$((TOTAL + COMPLEXITY_SCORE))

# ─────────────────────────────────────────────
# Routing Decision
# ─────────────────────────────────────────────
if (( TOTAL <= 4 )); then
  ROUTE="SIMPLE"
elif (( TOTAL <= 8 )); then
  ROUTE="MODERATE"
else
  ROUTE="COMPLEX"
fi

# ─────────────────────────────────────────────
# Output
# ─────────────────────────────────────────────
echo "╔══════════════════════════════════════════════╗"
echo "║       COMPLEXITY ASSESSMENT REPORT           ║"
echo "╠══════════════════════════════════════════════╣"
echo "║ Story: $(basename "$STORY_FILE" .md)"
echo "╠══════════════════════════════════════════════╣"
printf "║ %-32s %s/2 ║\n" "File Count ($FILE_COUNT files)" "$FILE_SCORE"
printf "║ %-32s %s/2 ║\n" "Layer Crossings ($LAYER_COUNT layers)" "$LAYER_SCORE"
printf "║ %-32s %s/2 ║\n" "Dependency Fan-Out ($FANOUT items)" "$FANOUT_SCORE"
printf "║ %-32s %s/2 ║\n" "Security Surface ($SEC_HITS hits)" "$SEC_SCORE"
printf "║ %-32s %s/2 ║\n" "External Deps ($EXT_HITS services)" "$EXT_SCORE"
printf "║ %-32s %s/2 ║\n" "Pattern Novelty ($NOVEL_COUNT new dirs)" "$NOVEL_SCORE"
printf "║ %-32s %s/2 ║\n" "Interaction Risk ($OVERLAP_COUNT overlaps)" "$INTERACTION_SCORE"
printf "║ %-32s %s/2 ║\n" "Code Complexity (max $MAX_AST AST)" "$COMPLEXITY_SCORE"
echo "╠══════════════════════════════════════════════╣"
printf "║ TOTAL SCORE: %-6s ROUTE: %-17s║\n" "$TOTAL/16" "$ROUTE"
echo "╚══════════════════════════════════════════════╝"
