#!/usr/bin/env python3
"""Manage external code listings across all language editions.

Tag format on code fences:

    ```z80 src:examples/timing_harness.a80 lines:9..39
    ; ... inline code ...
    ```

    ```z80 id:ch03_push_fill
    ; ... standalone snippet ...
    ```

    ```mermaid id:ch08_beam_race
    graph TD
        A --> B
    ```

Subcommands:

    extract [--lang en]     Extract id: tagged blocks → listings/
    inject  [--lang all]    Inject canonical code → .md files (all languages)
    verify  [--diff]        Verify inline code matches canonical source
    stats                   Count tagged/untagged blocks per chapter

Usage:
    python3 tools/manage_listings.py extract
    python3 tools/manage_listings.py inject --lang all
    python3 tools/manage_listings.py verify --diff
    python3 tools/manage_listings.py stats
"""

import argparse
import difflib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LISTINGS_DIR = ROOT / "listings"

# Languages and their chapter locations
LANG_CONFIG = {
    "en": {
        "chapter_glob": "chapters/*/draft.md",
        "appendix_glob": "appendices/appendix-*.md",
    },
    "es": {
        "chapter_glob": "translations/es/chapters/ch*.md",
        "appendix_glob": "translations/es/appendices/appendix-*.md",
    },
    "ru": {
        "chapter_glob": "translations/ru/chapters/ch*.md",
        "appendix_glob": "translations/ru/appendices/appendix-*.md",
    },
    "uk": {
        "chapter_glob": "translations/uk/chapters/ch*.md",
        "appendix_glob": "translations/uk/appendices/appendix-*.md",
    },
}

# Regex for tagged code fences:
#   ```lang key:value key:value ...
# Captures: lang, then we parse key:value pairs from the rest
TAGGED_FENCE_RE = re.compile(
    r'^```(\w+)'                # language
    r'((?:\s+\w+:[^\s]+)+)'    # one or more key:value pairs
    r'\s*$'
)

# Any code fence opening
ANY_FENCE_RE = re.compile(r'^```(\w+)')


def parse_tags(tag_string):
    """Parse 'src:path lines:1..10 id:name' into a dict."""
    tags = {}
    for m in re.finditer(r'(\w+):(\S+)', tag_string):
        key, value = m.group(1), m.group(2)
        tags[key] = value
    return tags


def parse_line_range(range_str):
    """Parse '9..39' into (9, 39) tuple."""
    if not range_str:
        return None, None
    parts = range_str.split('..')
    if len(parts) == 2:
        return int(parts[0]), int(parts[1])
    return None, None


def get_md_files(lang="en"):
    """Get all markdown files for a given language."""
    cfg = LANG_CONFIG.get(lang)
    if not cfg:
        print(f"Unknown language: {lang}", file=sys.stderr)
        return []
    files = sorted(ROOT.glob(cfg["chapter_glob"]))
    files += sorted(ROOT.glob(cfg["appendix_glob"]))
    return files


def scan_blocks(md_path):
    """Scan a markdown file for all code blocks, returning tagged and untagged.

    Returns list of dicts with keys:
        tagged: bool
        lang: str (z80, mermaid, etc.)
        tags: dict (src, lines, id)
        content: str (the code block content, without fences)
        start_line: int (1-indexed line number of the opening fence)
        end_line: int (1-indexed line number of the closing fence)
        md_file: Path
    """
    lines = md_path.read_text(encoding='utf-8').split('\n')
    blocks = []

    i = 0
    while i < len(lines):
        # Try tagged fence first
        m = TAGGED_FENCE_RE.match(lines[i])
        if m:
            lang = m.group(1)
            tags = parse_tags(m.group(2))
            start_line = i + 1  # 1-indexed

            # Collect content until closing ```
            code_lines = []
            j = i + 1
            while j < len(lines) and lines[j].rstrip() != '```':
                code_lines.append(lines[j])
                j += 1
            end_line = j + 1  # 1-indexed

            blocks.append({
                'tagged': True,
                'lang': lang,
                'tags': tags,
                'content': '\n'.join(code_lines),
                'start_line': start_line,
                'end_line': end_line,
                'md_file': md_path,
            })
            i = j + 1
            continue

        # Try any fence (untagged)
        m2 = ANY_FENCE_RE.match(lines[i])
        if m2:
            lang = m2.group(1)
            start_line = i + 1

            code_lines = []
            j = i + 1
            while j < len(lines) and lines[j].rstrip() != '```':
                code_lines.append(lines[j])
                j += 1
            end_line = j + 1

            blocks.append({
                'tagged': False,
                'lang': lang,
                'tags': {},
                'content': '\n'.join(code_lines),
                'start_line': start_line,
                'end_line': end_line,
                'md_file': md_path,
            })
            i = j + 1
            continue

        i += 1

    return blocks


def resolve_source(md_file, tags):
    """Resolve the canonical source content for a tagged block.

    For src: blocks — read from the .a80 file (optionally with line range).
    For id: blocks — read from listings/ directory.

    Returns (content, source_path) or (None, expected_path) if missing.
    """
    if 'src' in tags:
        src_path = tags['src']
        start, end = parse_line_range(tags.get('lines'))

        # Resolve relative to the chapter directory first, then repo root
        chapter_dir = md_file.parent
        # For EN chapters: chapters/ch01-xxx/draft.md → chapter_dir = chapters/ch01-xxx/
        # For translations: translations/es/chapters/ch01-xxx.md → chapter_dir = translations/es/chapters/
        full_path = chapter_dir / src_path
        if not full_path.exists():
            # For translations, also try the EN chapter directory
            # e.g. src:examples/foo.a80 → chapters/ch01-xxx/examples/foo.a80
            # We need to figure out the EN chapter from the translation filename
            en_path = _find_en_source(md_file, src_path)
            if en_path and en_path.exists():
                full_path = en_path
            else:
                # Try repo root
                full_path = ROOT / src_path

        if not full_path.exists():
            return None, full_path

        text = full_path.read_text(encoding='utf-8')
        file_lines = text.split('\n')

        if start is not None and end is not None:
            file_lines = file_lines[start - 1:end]

        return '\n'.join(file_lines), full_path

    elif 'id' in tags:
        block_id = tags['id']
        # Determine extension from the block's language
        # We check common extensions
        for ext in ['.z80', '.mmd', '.asm', '.a80']:
            listing_path = LISTINGS_DIR / f"{block_id}{ext}"
            if listing_path.exists():
                return listing_path.read_text(encoding='utf-8').rstrip('\n'), listing_path

        # Not found — guess extension
        listing_path = LISTINGS_DIR / f"{block_id}.z80"
        return None, listing_path

    return None, None


def _find_en_source(md_file, src_path):
    """For a translation .md, find the corresponding EN chapter directory."""
    md_str = str(md_file)
    # Pattern: translations/{lang}/chapters/ch01-xxx.md
    m = re.search(r'translations/\w+/chapters/(ch\d+)', md_str)
    if m:
        ch_prefix = m.group(1)
        # Find the EN chapter directory
        for d in ROOT.glob(f"chapters/{ch_prefix}-*/"):
            candidate = d / src_path
            if candidate.exists():
                return candidate
    # Also try appendices
    m = re.search(r'translations/\w+/appendices/(appendix-\w+)', md_str)
    if m:
        return ROOT / "appendices" / src_path
    return None


def normalize(s):
    """Normalize for comparison: strip trailing whitespace per line, strip trailing newlines."""
    return '\n'.join(line.rstrip() for line in s.rstrip('\n').split('\n'))


# --- Subcommands ---

def cmd_extract(args):
    """Extract id: tagged blocks from EN .md files into listings/ directory."""
    lang = args.lang or "en"
    md_files = get_md_files(lang)

    LISTINGS_DIR.mkdir(exist_ok=True)
    extracted = 0
    skipped = 0

    for md in md_files:
        blocks = scan_blocks(md)
        for block in blocks:
            if not block['tagged']:
                continue
            if 'id' not in block['tags']:
                continue

            block_id = block['tags']['id']
            lang_tag = block['lang']

            # Determine file extension
            if lang_tag == 'mermaid':
                ext = '.mmd'
            else:
                ext = '.z80'

            out_path = LISTINGS_DIR / f"{block_id}{ext}"
            content = block['content'].rstrip('\n') + '\n'
            out_path.write_text(content, encoding='utf-8')
            rel_md = md.relative_to(ROOT)
            print(f"  EXTRACT  {rel_md}:{block['start_line']}  →  listings/{block_id}{ext}")
            extracted += 1

    print(f"\n---\n{extracted} blocks extracted, {skipped} skipped")


def cmd_inject(args):
    """Inject canonical code into tagged blocks across language editions."""
    if args.lang == "all":
        langs = list(LANG_CONFIG.keys())
    else:
        langs = [args.lang]

    total_injected = 0
    total_skipped = 0
    total_missing = 0

    for lang in langs:
        md_files = get_md_files(lang)
        for md in md_files:
            result = _inject_file(md)
            total_injected += result['injected']
            total_skipped += result['skipped']
            total_missing += result['missing']

    print(f"\n---\n{total_injected} injected, {total_skipped} unchanged, {total_missing} missing source")


def _inject_file(md_path):
    """Inject canonical code into a single .md file. Returns counts."""
    lines = md_path.read_text(encoding='utf-8').split('\n')
    new_lines = []
    stats = {'injected': 0, 'skipped': 0, 'missing': 0}
    rel_md = md_path.relative_to(ROOT)

    i = 0
    while i < len(lines):
        m = TAGGED_FENCE_RE.match(lines[i])
        if m:
            tags = parse_tags(m.group(2))

            # Keep the fence opening line
            new_lines.append(lines[i])

            # Skip old content
            j = i + 1
            while j < len(lines) and lines[j].rstrip() != '```':
                j += 1

            # Resolve canonical source
            source_content, source_path = resolve_source(md_path, tags)

            if source_content is not None:
                # Inject canonical content
                new_lines.extend(source_content.rstrip('\n').split('\n'))
                tag_label = tags.get('src') or tags.get('id', '?')
                print(f"  INJECT   {rel_md}:{i+1}  ←  {tag_label}")
                stats['injected'] += 1
            else:
                # Source missing — keep original content
                k = i + 1
                orig_lines_text = lines[k:j]
                new_lines.extend(orig_lines_text)
                tag_label = tags.get('src') or tags.get('id', '?')
                print(f"  MISSING  {rel_md}:{i+1}  →  {source_path}")
                stats['missing'] += 1

            # Add closing fence
            if j < len(lines):
                new_lines.append(lines[j])
            i = j + 1
            continue

        new_lines.append(lines[i])
        i += 1

    # Write back
    new_text = '\n'.join(new_lines)
    old_text = md_path.read_text(encoding='utf-8')
    if new_text != old_text:
        md_path.write_text(new_text, encoding='utf-8')
    else:
        stats['skipped'] += stats['injected']
        stats['injected'] = 0

    return stats


def cmd_verify(args):
    """Verify inline code matches canonical sources."""
    show_diff = args.diff
    lang = args.lang or "en"

    if lang == "all":
        langs = list(LANG_CONFIG.keys())
    else:
        langs = [lang]

    total = 0
    ok = 0
    stale = 0
    missing = 0

    for lang in langs:
        md_files = get_md_files(lang)
        for md in md_files:
            blocks = scan_blocks(md)
            for block in blocks:
                if not block['tagged']:
                    continue

                total += 1
                source_content, source_path = resolve_source(md, block['tags'])
                rel_md = md.relative_to(ROOT)
                tag_label = block['tags'].get('src') or block['tags'].get('id', '?')
                line_range = ""
                if 'lines' in block['tags']:
                    line_range = f" lines:{block['tags']['lines']}"

                if source_content is None:
                    print(f"  MISSING  {rel_md}:{block['start_line']}  →  {tag_label}{line_range}")
                    missing += 1
                elif normalize(block['content']) == normalize(source_content):
                    print(f"  OK       {rel_md}:{block['start_line']}  →  {tag_label}{line_range}")
                    ok += 1
                else:
                    print(f"  STALE    {rel_md}:{block['start_line']}  →  {tag_label}{line_range}")
                    stale += 1
                    if show_diff:
                        diff = difflib.unified_diff(
                            block['content'].rstrip('\n').split('\n'),
                            source_content.rstrip('\n').split('\n'),
                            fromfile=f'{rel_md} (inline)',
                            tofile=str(source_path.relative_to(ROOT) if source_path.is_relative_to(ROOT) else source_path),
                            lineterm=''
                        )
                        for d in diff:
                            print(f"           {d}")

    print(f"\n---\n{total} tagged listings: {ok} ok, {stale} stale, {missing} missing")
    return 1 if (stale or missing) else 0


def cmd_stats(args):
    """Count tagged vs untagged code blocks per chapter."""
    lang = args.lang or "en"

    if lang == "all":
        langs = list(LANG_CONFIG.keys())
    else:
        langs = [lang]

    grand_tagged = 0
    grand_untagged = 0
    grand_src = 0
    grand_id = 0

    for lang in langs:
        if len(langs) > 1:
            print(f"\n=== {lang.upper()} ===")

        md_files = get_md_files(lang)
        lang_tagged = 0
        lang_untagged = 0

        for md in md_files:
            blocks = scan_blocks(md)
            tagged = [b for b in blocks if b['tagged']]
            untagged = [b for b in blocks if not b['tagged']]
            rel_md = md.relative_to(ROOT)

            src_count = sum(1 for b in tagged if 'src' in b['tags'])
            id_count = sum(1 for b in tagged if 'id' in b['tags'])

            if tagged or untagged:
                print(f"  {rel_md}: {len(tagged)} tagged (src:{src_count} id:{id_count}), {len(untagged)} untagged")

            lang_tagged += len(tagged)
            lang_untagged += len(untagged)
            grand_src += src_count
            grand_id += id_count

        grand_tagged += lang_tagged
        grand_untagged += lang_untagged

        if len(langs) > 1:
            total = lang_tagged + lang_untagged
            pct = (lang_tagged / total * 100) if total else 0
            print(f"  Subtotal: {lang_tagged}/{total} tagged ({pct:.0f}%)")

    total = grand_tagged + grand_untagged
    pct = (grand_tagged / total * 100) if total else 0
    print(f"\n---\nTotal: {grand_tagged} tagged (src:{grand_src} id:{grand_id}), {grand_untagged} untagged — {pct:.0f}% adoption")


def main():
    parser = argparse.ArgumentParser(
        description="Manage external code listings across all language editions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    sub = parser.add_subparsers(dest='command', required=True)

    # extract
    p_extract = sub.add_parser('extract', help='Extract id: tagged blocks → listings/')
    p_extract.add_argument('--lang', default='en', help='Language to extract from (default: en)')

    # inject
    p_inject = sub.add_parser('inject', help='Inject canonical code → .md files')
    p_inject.add_argument('--lang', default='all', help='Language(s) to inject into (default: all)')

    # verify
    p_verify = sub.add_parser('verify', help='Verify inline code matches source')
    p_verify.add_argument('--diff', action='store_true', help='Show diffs for stale listings')
    p_verify.add_argument('--lang', default='en', help='Language to verify (default: en, use "all" for all)')

    # stats
    p_stats = sub.add_parser('stats', help='Count tagged/untagged blocks per chapter')
    p_stats.add_argument('--lang', default='en', help='Language to count (default: en, use "all" for all)')

    args = parser.parse_args()

    if args.command == 'extract':
        cmd_extract(args)
    elif args.command == 'inject':
        cmd_inject(args)
    elif args.command == 'verify':
        rc = cmd_verify(args)
        sys.exit(rc)
    elif args.command == 'stats':
        cmd_stats(args)


if __name__ == '__main__':
    main()
