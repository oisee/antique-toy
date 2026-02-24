#!/usr/bin/env python3
"""Verify that inline code listings in chapter .md files match their source files.

Scans for code fences with source references:

    ```z80 examples/aybeat.a80
    ; ... full file quoted inline ...
    ```

    ```z80 examples/aybeat.a80 lines:45..80
    ; ... lines 45-80 quoted inline ...
    ```

Compares the inline code with the actual source file content.
Reports mismatches (stale quotes) and missing source files.

Usage:
    python3 tools/verify_listings.py                    # check all chapters
    python3 tools/verify_listings.py chapters/ch13-*/   # check specific chapter
    python3 tools/verify_listings.py --diff             # show diffs for stale listings
"""

import sys
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Pattern: ```z80 path/to/file.a80 [lines:10..50]
# Captures: language, file path, optional line range
FENCE_RE = re.compile(
    r'^```(\w+)\s+'
    r'(?P<path>[^\s]+\.(?:a80|asm|z80|inc))'   # file path (must have asm-like extension)
    r'(?:\s+lines:(?P<start>\d+)\.\.(?P<end>\d+))?'  # optional lines:N..M
    r'\s*$'
)


def extract_listings(md_path):
    """Extract all tagged code blocks from a .md file."""
    lines = md_path.read_text(encoding='utf-8').split('\n')
    listings = []

    i = 0
    while i < len(lines):
        m = FENCE_RE.match(lines[i])
        if m:
            fence_line = i + 1  # 1-indexed for display
            src_path = m.group('path')
            start = int(m.group('start')) if m.group('start') else None
            end = int(m.group('end')) if m.group('end') else None

            # Collect code block content until closing ```
            code_lines = []
            j = i + 1
            while j < len(lines) and not lines[j].rstrip() == '```':
                code_lines.append(lines[j])
                j += 1

            listings.append({
                'md_file': md_path,
                'fence_line': fence_line,
                'src_path': src_path,
                'start': start,
                'end': end,
                'inline_code': '\n'.join(code_lines),
            })
            i = j + 1
            continue

        i += 1

    return listings


def get_source_content(md_file, src_path, start, end):
    """Read the referenced source file, optionally slicing by line range."""
    # Resolve relative to the chapter/appendix directory
    chapter_dir = md_file.parent
    full_path = chapter_dir / src_path

    if not full_path.exists():
        # Try relative to repo root
        full_path = ROOT / src_path

    if not full_path.exists():
        return None, full_path

    text = full_path.read_text(encoding='utf-8')
    file_lines = text.split('\n')

    if start is not None and end is not None:
        # Line range is 1-indexed, inclusive
        file_lines = file_lines[start - 1:end]

    return '\n'.join(file_lines), full_path


def normalize(s):
    """Normalize for comparison: strip trailing whitespace per line, strip trailing newlines."""
    return '\n'.join(line.rstrip() for line in s.rstrip('\n').split('\n'))


def main():
    show_diff = '--diff' in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith('--')]

    if args:
        md_files = []
        for a in args:
            p = Path(a)
            if p.is_dir():
                md_files.extend(sorted(p.glob('**/draft.md')))
            elif p.is_file():
                md_files.append(p)
    else:
        md_files = sorted(ROOT.glob('chapters/*/draft.md'))
        md_files += sorted(ROOT.glob('appendices/appendix-*.md'))

    total = 0
    ok = 0
    stale = 0
    missing = 0

    for md in md_files:
        listings = extract_listings(md)
        for lst in listings:
            total += 1
            src_content, full_path = get_source_content(
                lst['md_file'], lst['src_path'], lst['start'], lst['end']
            )
            rel_md = lst['md_file'].relative_to(ROOT)
            line_range = f" lines:{lst['start']}..{lst['end']}" if lst['start'] else ""

            if src_content is None:
                print(f"  MISSING  {rel_md}:{lst['fence_line']}  →  {lst['src_path']}")
                missing += 1
            elif normalize(lst['inline_code']) == normalize(src_content):
                print(f"  OK       {rel_md}:{lst['fence_line']}  →  {lst['src_path']}{line_range}")
                ok += 1
            else:
                print(f"  STALE    {rel_md}:{lst['fence_line']}  →  {lst['src_path']}{line_range}")
                stale += 1
                if show_diff:
                    import difflib
                    diff = difflib.unified_diff(
                        lst['inline_code'].rstrip('\n').split('\n'),
                        src_content.rstrip('\n').split('\n'),
                        fromfile=f'{rel_md} (inline)',
                        tofile=str(full_path.relative_to(ROOT)),
                        lineterm=''
                    )
                    for d in diff:
                        print(f"           {d}")

    print(f"\n---\n{total} listings: {ok} ok, {stale} stale, {missing} missing")
    return 1 if (stale or missing) else 0


if __name__ == '__main__':
    sys.exit(main())
