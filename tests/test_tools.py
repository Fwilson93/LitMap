from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.generate_live_project_context import build_live_project_context
from scripts.generate_raw_code_state import build_raw_code_state


def test_raw_code_state_contains_verbatim_files(monkeypatch) -> None:
    monkeypatch.setenv('LITMAP_CONTEXT_SKIP_TESTS', '1')
    text = build_raw_code_state(max_file_bytes=200_000)
    assert 'RAW CODE STATE' in text
    assert '===== FILE: app/main.py =====' in text
    assert '===== FILE: scripts/repo_tool.py =====' in text


def test_live_project_context_contains_intent_tree_and_checks(monkeypatch) -> None:
    monkeypatch.setenv('LITMAP_CONTEXT_SKIP_TESTS', '1')
    text = build_live_project_context()
    assert 'LIVE PROJECT CONTEXT' in text
    assert '===== PROJECT INTENT =====' in text
    assert '===== REPOSITORY TREE =====' in text
    assert '===== AUTOMATED CHECKS =====' in text


def test_repo_tool_context_command_writes_files(monkeypatch) -> None:
    monkeypatch.setenv('LITMAP_CONTEXT_SKIP_TESTS', '1')
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(['python', 'scripts/repo_tool.py', 'context'], cwd=repo_root, capture_output=True, text=True, check=False)
    assert result.returncode == 0
    assert (repo_root / 'notes' / 'LIVE_PROJECT_CONTEXT.txt').exists()
    assert (repo_root / 'notes' / 'RAW_CODE_STATE.txt').exists()


def test_context_manifest_excludes_generated_context_files(monkeypatch) -> None:
    monkeypatch.setenv('LITMAP_CONTEXT_SKIP_TESTS', '1')
    raw = build_raw_code_state(max_file_bytes=200_000)
    manifest = raw.split('===== FULL FILE CONTENTS (VERBATIM TEXT FILES) =====', 1)[0]
    assert 'notes/RAW_CODE_STATE.txt |' not in manifest
    assert 'notes/LIVE_PROJECT_CONTEXT.txt |' not in manifest
