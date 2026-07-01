#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys
if __package__ in {None, ''}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import subprocess
from typing import Optional

from scripts._context_common import REPO_ROOT, run_git
from scripts.generate_live_project_context import build_live_project_context
from scripts.generate_raw_code_state import build_raw_code_state

LIVE_PATH = REPO_ROOT / 'notes' / 'LIVE_PROJECT_CONTEXT.txt'
RAW_PATH = REPO_ROOT / 'notes' / 'RAW_CODE_STATE.txt'


def write_context(max_file_bytes: int = 80_000) -> None:
    LIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    LIVE_PATH.write_text(build_live_project_context(), encoding='utf-8')
    RAW_PATH.write_text(build_raw_code_state(max_file_bytes=max_file_bytes), encoding='utf-8')
    print(f'Wrote {LIVE_PATH}')
    print(f'Wrote {RAW_PATH}')


def run_tests() -> int:
    return subprocess.run([sys.executable, '-m', 'pytest', '-q'], cwd=REPO_ROOT, check=False).returncode


def commit_changes(message: str, push: bool = False) -> int:
    subprocess.run(['git', 'add', '-A'], cwd=REPO_ROOT, check=False)
    status = run_git('status', '--short')
    if not status:
        print('No staged or unstaged changes to commit.')
        return 0
    commit_result = subprocess.run(['git', 'commit', '-m', message], cwd=REPO_ROOT, check=False)
    if commit_result.returncode != 0:
        return int(commit_result.returncode)
    if push:
        branch = run_git('branch', '--show-current') or 'main'
        return subprocess.run(['git', 'push', 'origin', branch], cwd=REPO_ROOT, check=False).returncode
    return 0


def show_status() -> None:
    branch = run_git('branch', '--show-current') or '(not available)'
    commit = run_git('rev-parse', 'HEAD') or '(not available)'
    status = run_git('status', '--short') or '(clean or git unavailable)'
    print(f'Branch: {branch}')
    print(f'Commit: {commit}')
    print('Status:')
    print(status)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description='Lightweight repo maintenance helper for LitMap Slim.')
    subparsers = parser.add_subparsers(dest='command', required=True)

    subparsers.add_parser('status', help='Show git status summary.')
    context_parser = subparsers.add_parser('context', help='Generate both context files.')
    context_parser.add_argument('--max-file-bytes', type=int, default=80_000)
    update_parser = subparsers.add_parser('update', help='Generate context files and optionally run tests.')
    update_parser.add_argument('--run-tests', action='store_true')
    update_parser.add_argument('--max-file-bytes', type=int, default=80_000)
    commit_parser = subparsers.add_parser('commit', help='Stage, commit, and optionally push changes.')
    commit_parser.add_argument('-m', '--message', required=True)
    commit_parser.add_argument('--push', action='store_true')

    args = parser.parse_args(argv)
    if args.command == 'status':
        show_status()
        return 0
    if args.command == 'context':
        write_context(max_file_bytes=args.max_file_bytes)
        return 0
    if args.command == 'update':
        write_context(max_file_bytes=args.max_file_bytes)
        return run_tests() if args.run_tests else 0
    if args.command == 'commit':
        return commit_changes(message=args.message, push=args.push)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
