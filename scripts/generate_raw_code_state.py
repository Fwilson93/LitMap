#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys
if __package__ in {None, ''}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
from pathlib import Path

from scripts._context_common import REPO_ROOT, ALWAYS_INCLUDE, iter_repo_files

DEFAULT_OUTPUT = REPO_ROOT / 'notes' / 'RAW_CODE_STATE.txt'
DEFAULT_MAX_FILE_BYTES = 80_000


def build_raw_code_state(max_file_bytes: int = DEFAULT_MAX_FILE_BYTES) -> str:
    files = iter_repo_files()
    lines: list[str] = [
        'RAW CODE STATE',
        f'Repository root: {REPO_ROOT}',
        f'Included text files: {len(files)}',
        f'Max file bytes: {max_file_bytes}',
        '',
        '===== FILE MANIFEST =====',
        '',
    ]
    for path in files:
        rel = path.relative_to(REPO_ROOT).as_posix()
        size = path.stat().st_size
        marker = ' [priority]' if rel in ALWAYS_INCLUDE else ''
        lines.append(f'{rel} | size={size} bytes{marker}')
    lines.extend(['', '===== FULL FILE CONTENTS (VERBATIM TEXT FILES) =====', ''])
    for path in files:
        rel = path.relative_to(REPO_ROOT).as_posix()
        size = path.stat().st_size
        lines.extend([f'===== FILE: {rel} =====', '', f'Path: {rel}', f'Size: {size} bytes'])
        if size > max_file_bytes:
            lines.extend([f'Skipped: file exceeds max size threshold of {max_file_bytes} bytes.', ''])
            continue
        try:
            content = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            lines.extend(['Skipped: file is not valid UTF-8 text.', ''])
            continue
        fence = '```'
        lines.extend([f'{fence}{path.suffix.lstrip(".") or "text"}', content.rstrip(), fence, ''])
    return '\n'.join(lines).rstrip() + '\n'


def main() -> None:
    parser = argparse.ArgumentParser(description='Generate a compact verbatim raw code snapshot for LLM handoff.')
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--max-file-bytes', type=int, default=DEFAULT_MAX_FILE_BYTES)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_raw_code_state(max_file_bytes=args.max_file_bytes), encoding='utf-8')
    print(args.output)


if __name__ == '__main__':
    main()
