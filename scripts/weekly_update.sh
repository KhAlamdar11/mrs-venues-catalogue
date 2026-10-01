#!/usr/bin/env bash
# Run the weekly catalogue refresh headlessly with Claude Code.
#
#   ./scripts/weekly_update.sh                 # full refresh
#   ./scripts/weekly_update.sh "focus on swarm venues"  # extra instructions appended to the prompt
#
# Cron example (Mondays 08:00):
#   0 8 * * 1  cd /path/to/conferences_catalogue && ./scripts/weekly_update.sh >> logs/cron.log 2>&1
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p logs

PROMPT_FILE=.claude/commands/update-catalogue.md
# Strip YAML front matter and substitute $ARGUMENTS (as the /update-catalogue command would).
PROMPT="$(awk 'BEGIN{fm=0} NR==1 && /^---$/ {fm=1; next} fm && /^---$/ {fm=0; next} !fm' "$PROMPT_FILE")"
PROMPT="${PROMPT//\$ARGUMENTS/${1:-}}"

LOG="logs/update-$(date +%F).log"
echo "[$(date -Is)] starting weekly update -> $LOG"

claude -p "$PROMPT" \
  --permission-mode acceptEdits \
  --allowedTools "Read Edit Write Glob Grep WebSearch WebFetch \
Bash(python3 scripts/build.py:*) Bash(date:*) Bash(curl:*) Bash(tar:*) Bash(grep:*) \
Bash(ls:*) Bash(pdftotext:*) Bash(git status:*) Bash(git add:*) Bash(git commit:*) Bash(git diff:*)" \
  2>&1 | tee "$LOG"

echo "[$(date -Is)] done"
