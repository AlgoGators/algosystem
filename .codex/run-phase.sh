#!/usr/bin/env bash
# Drive one restructure phase through codex.
#   ./.codex/run-phase.sh 1
# The phase prompt is fed on stdin; the agent's reply is forced to match
# report-schema.json and lands in .codex/reports/phase-<n>.json
set -euo pipefail

PHASE="${1:?usage: run-phase.sh <phase-number>}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROMPT="${ROOT}/.codex/phases/phase-${PHASE}.md"
REPORT="${ROOT}/.codex/reports/phase-${PHASE}.json"

[[ -f "$PROMPT" ]] || { echo "no such phase prompt: $PROMPT" >&2; exit 1; }
mkdir -p "${ROOT}/.codex/reports"

cd "$ROOT"
codex exec \
  --dangerously-bypass-approvals-and-sandbox \
  --cd "$ROOT" \
  --output-schema "${ROOT}/.codex/report-schema.json" \
  --output-last-message "$REPORT" \
  < "$PROMPT"

echo "--- report written to ${REPORT} ---"
