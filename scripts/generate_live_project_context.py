#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys
if __package__ in {None, ''}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
from datetime import datetime, timezone
from pathlib import Path
import os
import subprocess
import sys

from scripts._context_common import REPO_ROOT, ALWAYS_INCLUDE, iter_repo_files, render_tree, run_git

DEFAULT_OUTPUT = REPO_ROOT / 'notes' / 'LIVE_PROJECT_CONTEXT.txt'


def _section(title: str, body: str) -> str:
    return f'===== {title} =====\n\n{body.strip()}\n'


def _test_status() -> str:
    if os.getenv('PYTEST_CURRENT_TEST') or os.getenv('LITMAP_CONTEXT_SKIP_TESTS') == '1':
        return 'Skipped automated checks during nested test execution or explicit skip mode.'
    try:
        result = subprocess.run([sys.executable, '-m', 'pytest', '-q'], cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return 'pytest not available in current environment.'
    summary = result.stdout.strip() or result.stderr.strip() or '(no output)'
    if len(summary) > 3000:
        summary = summary[:3000].rstrip() + '\n...[trimmed]'
    return f'Return code: {result.returncode}\n{summary}'


def build_live_project_context() -> str:
    files = iter_repo_files()
    timestamp = datetime.now(timezone.utc).isoformat()
    readme = (REPO_ROOT / 'README.md').read_text(encoding='utf-8') if (REPO_ROOT / 'README.md').exists() else ''
    intent = (REPO_ROOT / 'notes' / 'PROJECT_INTENT.md').read_text(encoding='utf-8') if (REPO_ROOT / 'notes' / 'PROJECT_INTENT.md').exists() else ''
    branch = run_git('branch', '--show-current') or '(not available)'
    commit = run_git('rev-parse', 'HEAD') or '(not available)'
    status = run_git('status', '--short') or '(clean or git unavailable)'
    manifest_lines = []
    for path in files:
        rel = path.relative_to(REPO_ROOT).as_posix()
        size = path.stat().st_size
        priority = ' [priority]' if rel in ALWAYS_INCLUDE else ''
        manifest_lines.append(f'- {rel} ({size} bytes){priority}')
    body = [f'LIVE PROJECT CONTEXT\nGenerated: {timestamp}\nRepository root: {REPO_ROOT}']
    body.append(_section('PROJECT INTENT', intent or 'No project intent note found.'))
    body.append(_section('README', readme or 'No README found.'))
    body.append(_section('GIT SNAPSHOT', f'Branch: {branch}\nCommit: {commit}\n\nStatus:\n{status}'))
    body.append(_section('AUTOMATED CHECKS', _test_status()))
    body.append(_section('REPOSITORY TREE', render_tree()))
    body.append(_section('TEXT FILE MANIFEST', '\n'.join(manifest_lines)))
    body.append(_section('HANDOFF NOTES', 'Attach this file plus notes/RAW_CODE_STATE.txt in a new chat.\nThe live context gives intent, git state, tests, tree, and manifest.\nThe raw code state gives verbatim source for manageable text files.'))
    return '\n'.join(body).rstrip() + '\n'


def main() -> None:
    parser = argparse.ArgumentParser(description='Generate a lightweight live project context file for LLM handoff.')
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_live_project_context(), encoding='utf-8')
    print(args.output)


if __name__ == '__main__':
    main()
