from __future__ import annotations

from pathlib import Path
import subprocess

REPO_ROOT = Path(__file__).resolve().parents[1]
TEXT_EXTENSIONS = {'.py', '.md', '.toml', '.txt', '.css', '.js', '.html', '.yml', '.yaml', '.json', '.sh', '.gitignore'}
EXCLUDE_DIR_NAMES = {'.git', '.venv', 'venv', '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', 'node_modules', 'dist', 'build', '.idea', '.vscode'}
EXCLUDE_TOP_LEVEL = {'data'}
EXCLUDE_RELATIVE_PATHS = {'notes/LIVE_PROJECT_CONTEXT.txt', 'notes/RAW_CODE_STATE.txt'}
ALWAYS_INCLUDE = {'README.md', 'pyproject.toml', 'notes/PROJECT_INTENT.md', 'app/main.py', 'app/models.py', 'app/store.py', 'app/search.py', 'app/graph.py', 'scripts/repo_tool.py'}


def is_text_candidate(path: Path) -> bool:
    if path.name in {'package-lock.json'}:
        return False
    return path.suffix.lower() in TEXT_EXTENSIONS or path.name in {'Dockerfile', '.gitignore'}


def should_skip(path: Path) -> bool:
    rel = path.relative_to(REPO_ROOT).as_posix()
    if rel in EXCLUDE_RELATIVE_PATHS:
        return True
    parts = Path(rel).parts
    if any(part in EXCLUDE_DIR_NAMES for part in parts):
        return True
    return bool(parts and parts[0] in EXCLUDE_TOP_LEVEL)


def iter_repo_files() -> list[Path]:
    files: list[Path] = []
    for path in sorted(REPO_ROOT.rglob('*')):
        if path.is_dir():
            continue
        if should_skip(path):
            continue
        if is_text_candidate(path):
            files.append(path)
    return files


def render_tree() -> str:
    lines: list[str] = []
    for path in sorted(REPO_ROOT.rglob('*')):
        if should_skip(path):
            continue
        rel = path.relative_to(REPO_ROOT)
        depth = len(rel.parts) - 1
        prefix = '  ' * depth + '- '
        suffix = '/' if path.is_dir() else ''
        lines.append(f'{prefix}{rel.name}{suffix}')
    return '\n'.join(lines)


def run_git(*args: str) -> str:
    try:
        result = subprocess.run(['git', *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ''
    return result.stdout.strip()
