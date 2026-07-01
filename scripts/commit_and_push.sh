#!/usr/bin/env bash
set -euo pipefail
if [ $# -lt 1 ]; then
  echo 'Usage: ./scripts/commit_and_push.sh "commit message"'
  exit 1
fi
python scripts/repo_tool.py context
python scripts/repo_tool.py commit -m "$1" --push
