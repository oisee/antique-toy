#!/usr/bin/env python3
"""Semi-automatic code block classifier and tagger.

Scans all chapters/*/draft.md for code fences and:
  1. Classifies bare ``` blocks (no language) as z80, mermaid, or text
  2. Generates id:chNN_description tags for z80/mermaid blocks

Usage:
    python3 tools/autotag.py --preview           # show proposed changes (default)
    python3 tools/autotag.py --apply              # write changes to files
    python3 tools/autotag.py --lang-only --apply  # only add language tags, skip id:
    python3 tools/autotag.py --stats              # count bare/tagged/total blocks
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Z80 detection heuristic
# ---------------------------------------------------------------------------
Z80_SIGNALS = {
    'ld', 'push', 'pop', 'call', 'ret', 'jp', 'jr', 'djnz',
    'add', 'sub', 'and', 'or', 'xor', 'cp', 'inc', 'dec',
    'nop', 'halt', 'di', 'ei', 'im', 'out', 'in', 'exx',
    'ldir', 'ldi', 'rst', 'bit', 'set', 'res', 'rl', 'rr',
    'sla', 'sra', 'srl', 'rlca', 'rrca', 'rla', 'rra',
    'org', 'equ', 'db', 'dw', 'ds', 'defb', 'defw',
}

MERMAID_SIGNALS = {
    'graph', 'flowchart', 'sequencediagram', 'classDiagram',
    'statediagram', 'gantt', 'pie', 'erdiagram',
    'journey', 'gitgraph', 'mindmap', 'timeline',
}

# Regex for code fence
FENCE_OPEN_RE = re.compile(r'^```(\w*)(.*?)\s*$')
FENCE_CLOSE_RE = re.compile(r'^```\s*$')

# Regex for headings
HEADING_RE = re.compile(r'^(#{2,3})\s+(.*)')

# Regex to extract chapter number from path
CH_NUM_RE = re.compile(r'ch(\d+)')

# Tag regex (already tagged with id:)
TAG_RE = re.compile(r'\b(id|src):\S+')


def classify_block(content_lines):
    """Classify a bare code block by its content.

    Returns: 'z80', 'mermaid', or 'text'
    """
    # Check first 5 non-empty lines
    checked = 0
    for line in content_lines:
        stripped = line.strip()
        if not stripped:
            continue
        if checked >= 5:
            break

        # Check mermaid (case-insensitive for first word)
        first_word = stripped.split()[0].rstrip(':;')
        if first_word.lower() in {s.lower() for s in MERMAID_SIGNALS}:
            return 'mermaid'

        # Check Z80 — first word before space/comma, strip label prefix
        # Handle lines like "label: ld a, 0" or ".loop ld a, 0"
        work = stripped
        # Strip global label (word followed by colon)
        m = re.match(r'^[A-Za-z_]\w*\s*:\s*', work)
        if m:
            work = work[m.end():]
        # Strip local label (.word optionally followed by colon)
        m = re.match(r'^\.\w+\s*:?\s*', work)
        if m:
            work = work[m.end():]

        if work:
            first_mnemonic = work.split()[0].split(',')[0].lower()
            if first_mnemonic in Z80_SIGNALS:
                return 'z80'

        # Also check comment-only lines starting with ; which are Z80 convention
        if stripped.startswith(';'):
            # Z80 comments — don't count as a classification signal alone
            pass

        checked += 1

    # Second pass: if >50% of non-empty lines start with ; it's likely Z80
    non_empty = [l.strip() for l in content_lines if l.strip()]
    if non_empty:
        comment_lines = sum(1 for l in non_empty if l.startswith(';'))
        # If all lines are comments, and any mention registers, it's Z80
        if comment_lines == len(non_empty):
            text = ' '.join(non_empty).lower()
            if any(r in text for r in ['register', ' hl', ' de', ' bc', ' sp', 't-state', 'byte']):
                return 'z80'

    return 'text'


def slugify(text):
    """Convert heading text to a slug suitable for an id tag."""
    # Remove markdown formatting
    text = re.sub(r'\*\*|__|\*|_|`', '', text)
    # Remove section numbers like "2.1" or "16.3"
    text = re.sub(r'^\d+\.\d+\.?\s*', '', text)
    # Take first meaningful words (up to ~30 chars)
    text = text.strip()
    # Convert to lowercase, replace non-alphanumeric with underscore
    slug = re.sub(r'[^a-z0-9]+', '_', text.lower())
    # Strip leading/trailing underscores
    slug = slug.strip('_')
    # Truncate
    parts = slug.split('_')
    result = []
    length = 0
    for p in parts:
        if length + len(p) + 1 > 30:
            break
        result.append(p)
        length += len(p) + 1
    return '_'.join(result) if result else 'block'


def scan_file(md_path):
    """Scan a markdown file and return info about all code blocks.

    Returns list of dicts:
        start_line: int (0-indexed line of opening fence)
        end_line: int (0-indexed line of closing fence)
        lang: str (current language tag, '' if bare)
        rest: str (rest of fence line after language)
        content: list[str] (lines between fences)
        heading: str (nearest H2/H3 above the block)
        has_id: bool (already has id: tag)
        has_src: bool (already has src: tag)
        classified_lang: str (our guess: z80/mermaid/text)
        proposed_id: str (generated id)
    """
    lines = md_path.read_text(encoding='utf-8').split('\n')
    blocks = []
    current_heading = ''

    # Extract chapter number
    ch_match = CH_NUM_RE.search(str(md_path))
    ch_num = int(ch_match.group(1)) if ch_match else 0
    ch_prefix = f'ch{ch_num:02d}'

    # ID counter for disambiguation
    id_counts = {}

    i = 0
    while i < len(lines):
        # Track headings
        hm = HEADING_RE.match(lines[i])
        if hm:
            current_heading = hm.group(2)
            i += 1
            continue

        # Check for code fence
        fm = FENCE_OPEN_RE.match(lines[i])
        if fm:
            lang = fm.group(1)
            rest = fm.group(2).strip()
            start_line = i

            # Collect content
            content = []
            j = i + 1
            while j < len(lines) and not FENCE_CLOSE_RE.match(lines[j]):
                content.append(lines[j])
                j += 1
            end_line = j

            # Classify
            has_id = bool(re.search(r'\bid:\S+', rest))
            has_src = bool(re.search(r'\bsrc:\S+', rest))

            if lang == '':
                classified = classify_block(content)
            else:
                classified = lang

            # Generate proposed ID
            slug = slugify(current_heading) if current_heading else 'block'
            proposed_id = f'{ch_prefix}_{slug}'

            # Disambiguate
            if proposed_id in id_counts:
                id_counts[proposed_id] += 1
                proposed_id = f'{proposed_id}_{id_counts[proposed_id]}'
            else:
                id_counts[proposed_id] = 1

            blocks.append({
                'start_line': start_line,
                'end_line': end_line,
                'lang': lang,
                'rest': rest,
                'content': content,
                'heading': current_heading,
                'has_id': has_id,
                'has_src': has_src,
                'classified_lang': classified,
                'proposed_id': proposed_id,
            })

            i = j + 1
            continue

        i += 1

    return blocks, lines


def apply_changes(md_path, blocks, lines, lang_only=False):
    """Apply tagging changes to a file, return list of changes made."""
    changes = []
    # Work on a copy of lines
    new_lines = list(lines)
    offset = 0  # line offset from insertions (not used — we modify in-place)

    for block in blocks:
        start = block['start_line']
        old_fence = new_lines[start]

        # Build new fence line
        lang = block['lang']
        rest = block['rest']
        classified = block['classified_lang']

        new_lang = lang if lang else classified
        new_rest = rest

        if not lang_only:
            # Add id: tag if missing and block is z80 or mermaid
            if not block['has_id'] and not block['has_src'] and new_lang in ('z80', 'mermaid'):
                new_rest = f'{rest} id:{block["proposed_id"]}'.strip() if rest else f'id:{block["proposed_id"]}'

        new_fence = f'```{new_lang}'
        if new_rest:
            new_fence += f' {new_rest}'

        if new_fence != old_fence.rstrip():
            changes.append({
                'line': start + 1,  # 1-indexed
                'old': old_fence.rstrip(),
                'new': new_fence,
                'type': 'lang' if not lang else 'id',
            })
            new_lines[start] = new_fence

    return new_lines, changes


def get_chapter_files():
    """Get all chapter draft.md files sorted by chapter number."""
    pattern = "chapters/*/draft.md"
    files = sorted(ROOT.glob(pattern))
    return files


def cmd_preview(args):
    """Preview proposed changes."""
    files = get_chapter_files()
    total_bare = 0
    total_tagged = 0
    total_changes = 0

    for md_path in files:
        blocks, lines = scan_file(md_path)
        _, changes = apply_changes(md_path, blocks, lines, lang_only=args.lang_only)

        rel = md_path.relative_to(ROOT)
        bare = sum(1 for b in blocks if not b['lang'])
        tagged = sum(1 for b in blocks if b['has_id'] or b['has_src'])

        if changes:
            print(f"\n{rel} ({len(blocks)} blocks, {bare} bare, {tagged} tagged)")
            for c in changes:
                print(f"  L{c['line']:4d}  {c['old']}")
                print(f"     →  {c['new']}")
            total_changes += len(changes)

        total_bare += bare
        total_tagged += tagged

    print(f"\n---")
    print(f"Total: {total_bare} bare blocks to classify, {total_changes} changes proposed")


def cmd_apply(args):
    """Apply changes to files."""
    files = get_chapter_files()
    total_changes = 0

    for md_path in files:
        blocks, lines = scan_file(md_path)
        new_lines, changes = apply_changes(md_path, blocks, lines, lang_only=args.lang_only)

        if changes:
            rel = md_path.relative_to(ROOT)
            md_path.write_text('\n'.join(new_lines), encoding='utf-8')
            print(f"  {rel}: {len(changes)} changes applied")
            for c in changes:
                print(f"    L{c['line']:4d}  {c['old']}  →  {c['new']}")
            total_changes += len(changes)

    print(f"\n---\n{total_changes} total changes applied")


def cmd_stats(args):
    """Show statistics about code blocks."""
    files = get_chapter_files()
    print(f"{'Chapter':<45s} {'Total':>5s} {'Bare':>5s} {'z80':>5s} {'mmd':>5s} {'text':>5s} {'id:':>5s} {'src:':>5s}")
    print('-' * 90)

    grand = {'total': 0, 'bare': 0, 'z80': 0, 'mermaid': 0, 'text': 0, 'id': 0, 'src': 0}

    for md_path in files:
        blocks, _ = scan_file(md_path)
        rel = md_path.relative_to(ROOT)

        total = len(blocks)
        bare = sum(1 for b in blocks if not b['lang'])
        z80 = sum(1 for b in blocks if (b['lang'] or b['classified_lang']) == 'z80')
        mermaid = sum(1 for b in blocks if (b['lang'] or b['classified_lang']) == 'mermaid')
        text = sum(1 for b in blocks if not b['lang'] and b['classified_lang'] == 'text')
        has_id = sum(1 for b in blocks if b['has_id'])
        has_src = sum(1 for b in blocks if b['has_src'])

        if total:
            print(f"{str(rel):<45s} {total:5d} {bare:5d} {z80:5d} {mermaid:5d} {text:5d} {has_id:5d} {has_src:5d}")

        grand['total'] += total
        grand['bare'] += bare
        grand['z80'] += z80
        grand['mermaid'] += mermaid
        grand['text'] += text
        grand['id'] += has_id
        grand['src'] += has_src

    print('-' * 90)
    g = grand
    print(f"{'TOTAL':<45s} {g['total']:5d} {g['bare']:5d} {g['z80']:5d} {g['mermaid']:5d} {g['text']:5d} {g['id']:5d} {g['src']:5d}")


def main():
    parser = argparse.ArgumentParser(
        description="Semi-automatic code block classifier and tagger",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--preview', action='store_true', default=True,
                       help='Show proposed changes without writing (default)')
    group.add_argument('--apply', action='store_true',
                       help='Write changes to files')
    group.add_argument('--stats', action='store_true',
                       help='Show block statistics only')

    parser.add_argument('--lang-only', action='store_true',
                        help='Only add language tags to bare blocks, skip id: tags')

    args = parser.parse_args()

    if args.stats:
        cmd_stats(args)
    elif args.apply:
        cmd_apply(args)
    else:
        cmd_preview(args)


if __name__ == '__main__':
    main()
