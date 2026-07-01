#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_MESSAGE="Update context and push latest changes"
COMMIT_MESSAGE="${1:-$DEFAULT_MESSAGE}"

log() {
  printf '[update.sh] %s\n' "$*"
}

fail() {
  printf '[update.sh] ERROR: %s\n' "$*" >&2
  exit 1
}

cleanup() {
  rc=$?
  if [[ $rc -ne 0 ]]; then
    printf '[update.sh] Aborted with exit code %s\n' "$rc" >&2
  fi
}
trap cleanup EXIT

cd "$REPO_ROOT"

[[ -f pyproject.toml ]] || fail 'pyproject.toml not found; run this script from the LitMap repo root.'
[[ -f scripts/repo_tool.py ]] || fail 'scripts/repo_tool.py not found.'

PYTHON_BIN=""
if [[ -x .venv/bin/python ]]; then
  PYTHON_BIN=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python)"
else
  fail 'No usable Python interpreter found.'
fi

command -v git >/dev/null 2>&1 || fail 'git is required.'

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail 'This directory is not a git working tree.'
BRANCH="$(git branch --show-current)"
[[ -n "$BRANCH" ]] || fail 'Detached HEAD detected; check out a branch before running update.sh.'

log "Generating fresh context files..."
"$PYTHON_BIN" scripts/repo_tool.py context

log "Staging changes..."
git add -A

if git diff --cached --quiet; then
  log 'No changes to commit after refreshing context.'
  exit 0
fi

log "Committing on branch ${BRANCH}..."
git commit -m "$COMMIT_MESSAGE"

log "Pushing ${BRANCH} to origin..."
git push -u origin "$BRANCH"

log 'Done.'
