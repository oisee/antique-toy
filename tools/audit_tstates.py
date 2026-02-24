#!/usr/bin/env python3
"""T-state audit tool — compares inline annotations with computed values.

Reads Z80 assembly fragments (from listings/ or inline) and:
  1. Computes correct T-state cost for each instruction using tstate.py's database
  2. Parses existing inline T-state comments
  3. Reports: OK, WRONG (with correct value), MISSING, UNKNOWN

Also supports --asm-check mode: wraps fragments in ORG $8000 / END and assembles
with sjasmplus to check for invalid instructions.

Usage:
    python3 tools/audit_tstates.py listings/*.z80
    python3 tools/audit_tstates.py --asm-check listings/*.z80
    python3 tools/audit_tstates.py --scan-chapters     # scan inline code blocks in drafts
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# Add project root and spectools to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from spectools.cli.tstate import (
    lookup_tstates,
    _parse_operands,
    _normalise_operand,
    parse_line,
    _Z80_MNEMONICS,
    _DIRECTIVES,
)

# ---------------------------------------------------------------------------
# Inline T-state comment parser
# ---------------------------------------------------------------------------

# Patterns for inline T-state annotations:
#   ; 7T  or  ; 7 T
#   ; 11T (5T if taken)  or  ; 11T(5T taken)
#   ; 13/8T  or  ; 13/8 T
#   ; 12/7T (taken/not-taken)
#   ; 11 T-states
TSTATE_COMMENT_RE = re.compile(
    r';\s*'
    r'(?:'
    # Pattern A: X/Y T — taken/not-taken shorthand
    r'(\d+)\s*/\s*(\d+)\s*T(?:-states?)?'
    r'|'
    # Pattern B: XT (YT if taken/not-taken/condition)
    r'(\d+)\s*T(?:-states?)?\s*\((\d+)\s*T?\s*(?:if\s+)?(?:taken|not[- ]taken|[a-z]+)\)'
    r'|'
    # Pattern C: simple XT
    r'(\d+)\s*T(?:-states?)?'
    r')'
)

# Alternative patterns for more complex annotations
TSTATE_ALT_RE = re.compile(
    r';\s*(\d+)\s*T\s*/\s*(\d+)\s*T\s*\(taken/not-taken\)'
)


def parse_inline_tstates(comment):
    """Parse inline T-state annotation from a comment string.

    Returns:
        None — no annotation found
        int — fixed cost
        (int, int) — (taken, not-taken) or (first, second) pair
    """
    if not comment:
        return None

    # Try alternative pattern first (more specific)
    m = TSTATE_ALT_RE.search(comment)
    if m:
        return (int(m.group(1)), int(m.group(2)))

    m = TSTATE_COMMENT_RE.search(comment)
    if not m:
        return None

    # Pattern A: X/Y T
    if m.group(1) is not None:
        return (int(m.group(1)), int(m.group(2)))

    # Pattern B: XT (YT if condition)
    if m.group(3) is not None:
        primary = int(m.group(3))
        secondary = int(m.group(4))
        # Convention: primary is the "default" annotation, secondary is the alternative
        # We return (primary, secondary) — caller compares with computed (taken, not-taken)
        return (primary, secondary)

    # Pattern C: simple XT
    if m.group(5) is not None:
        return int(m.group(5))

    return None


def costs_match(inline, computed):
    """Check if inline annotation matches computed T-state cost.

    Handles various annotation conventions:
    - Simple: 7 matches 7
    - Tuple: (12, 7) matches (12, 7)
    - Simple matching first of tuple: 12 matches (12, 7) — OK if primary is taken
    - Swapped: (7, 12) vs (12, 7) — WRONG (swapped)
    """
    if inline is None or computed is None:
        return None  # can't compare

    if isinstance(computed, tuple):
        taken, not_taken = computed

        if isinstance(inline, tuple):
            # Both tuples — check exact match or swapped
            if inline == (taken, not_taken):
                return True
            return False

        # Inline is simple int — OK if it matches taken cost
        if inline == taken:
            return True
        # Also OK if it matches not-taken (common for "falls through" paths)
        # But flag as partial
        if inline == not_taken:
            return 'partial'
        return False

    # Computed is simple int
    if isinstance(inline, tuple):
        # Inline has extra info — check if primary matches
        if inline[0] == computed:
            return True
        return False

    return inline == computed


def format_computed(cost):
    """Format computed T-state cost for display."""
    if cost is None:
        return '?T'
    if isinstance(cost, tuple):
        return f'{cost[0]}/{cost[1]}T (taken/not-taken)'
    return f'{cost}T'


def format_inline(cost):
    """Format inline annotation for display."""
    if cost is None:
        return 'none'
    if isinstance(cost, tuple):
        return f'{cost[0]}/{cost[1]}T'
    return f'{cost}T'


# ---------------------------------------------------------------------------
# File auditor
# ---------------------------------------------------------------------------

def audit_file(filepath, verbose=False):
    """Audit a single .z80 file for T-state correctness.

    Returns list of findings: (line_num, status, instruction, detail)
    Status: OK, WRONG, MISSING, UNKNOWN, SKIP
    """
    lines = Path(filepath).read_text(encoding='utf-8').split('\n')
    findings = []

    for line_num, raw_line in enumerate(lines, 1):
        info = parse_line(raw_line)

        # Skip non-instruction lines
        if info.is_blank or info.is_comment_only or info.is_directive or info.is_equ:
            continue
        if info.mnemonic is None:
            # Label-only line
            continue

        mnemonic = info.mnemonic
        operands = info.operands
        computed = info.tstates

        # Parse inline annotation from original comment
        inline = parse_inline_tstates(info.comment)

        # Build instruction string for display
        if operands:
            instr_str = f'{mnemonic} {",".join(operands)}'
        else:
            instr_str = mnemonic

        if computed is None:
            findings.append((line_num, 'UNKNOWN', instr_str,
                             'instruction not in T-state database'))
            continue

        if inline is None:
            if verbose:
                findings.append((line_num, 'MISSING', instr_str,
                                 f'correct={format_computed(computed)}'))
            continue

        match = costs_match(inline, computed)
        if match is True:
            if verbose:
                findings.append((line_num, 'OK', instr_str,
                                 f'{format_computed(computed)}'))
        elif match == 'partial':
            findings.append((line_num, 'PARTIAL', instr_str,
                             f'inline={format_inline(inline)} correct={format_computed(computed)} '
                             f'(annotated not-taken cost only)'))
        else:
            findings.append((line_num, 'WRONG', instr_str,
                             f'inline={format_inline(inline)} correct={format_computed(computed)}'))

    return findings


# ---------------------------------------------------------------------------
# Chapter scanner — audit inline code blocks directly
# ---------------------------------------------------------------------------

def scan_chapters(verbose=False):
    """Scan all chapter drafts for T-state annotation errors in z80 code blocks."""
    chapter_dirs = sorted(ROOT.glob('chapters/*/draft.md'))
    all_findings = []

    for md_path in chapter_dirs:
        lines = md_path.read_text(encoding='utf-8').split('\n')
        rel = md_path.relative_to(ROOT)
        in_z80_block = False
        block_start = 0

        for i, line in enumerate(lines):
            if re.match(r'^```z80\b', line) or re.match(r'^```asm\b', line):
                in_z80_block = True
                block_start = i + 1
                continue
            if in_z80_block and re.match(r'^```\s*$', line):
                in_z80_block = False
                continue
            if not in_z80_block:
                continue

            # Parse this line as Z80 assembly
            info = parse_line(line)
            if info.is_blank or info.is_comment_only or info.is_directive or info.is_equ:
                continue
            if info.mnemonic is None:
                continue

            computed = info.tstates
            inline = parse_inline_tstates(info.comment)

            if info.operands:
                instr_str = f'{info.mnemonic} {",".join(info.operands)}'
            else:
                instr_str = info.mnemonic

            if computed is None:
                all_findings.append((str(rel), i + 1, 'UNKNOWN', instr_str,
                                     'instruction not in T-state database'))
                continue

            if inline is None:
                if verbose:
                    all_findings.append((str(rel), i + 1, 'MISSING', instr_str,
                                         f'correct={format_computed(computed)}'))
                continue

            match = costs_match(inline, computed)
            if match is True:
                pass  # OK
            elif match == 'partial':
                all_findings.append((str(rel), i + 1, 'PARTIAL', instr_str,
                                     f'inline={format_inline(inline)} correct={format_computed(computed)}'))
            else:
                all_findings.append((str(rel), i + 1, 'WRONG', instr_str,
                                     f'inline={format_inline(inline)} correct={format_computed(computed)}'))

    return all_findings


# ---------------------------------------------------------------------------
# sjasmplus assembly check
# ---------------------------------------------------------------------------

def asm_check_file(filepath):
    """Wrap a .z80 fragment in ORG/END and try to assemble with sjasmplus.

    Returns list of error strings (empty = OK).
    """
    content = Path(filepath).read_text(encoding='utf-8')

    # Check if already has ORG
    has_org = bool(re.search(r'^\s*org\b', content, re.IGNORECASE | re.MULTILINE))

    wrapped = ''
    if not has_org:
        wrapped += '    ORG $8000\n'
    wrapped += content
    if not content.rstrip().endswith('END'):
        wrapped += '\n'

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.a80', delete=False, encoding='utf-8') as f:
        f.write(wrapped)
        tmp_path = f.name

    try:
        result = subprocess.run(
            ['sjasmplus', '--nologo', '--raw=/dev/null', tmp_path],
            capture_output=True, text=True, timeout=10
        )
        errors = []
        for line in (result.stdout + result.stderr).split('\n'):
            line = line.strip()
            if not line:
                continue
            # Filter out "undefined symbol" errors (expected for fragments)
            if 'symbol' in line.lower() and ('not defined' in line.lower() or 'undefined' in line.lower()):
                continue
            # Filter out "label" errors
            if 'label' in line.lower() and 'not found' in line.lower():
                continue
            # Keep real errors
            if 'error' in line.lower() or 'unrecognized' in line.lower():
                errors.append(line)
        return errors
    except FileNotFoundError:
        return ['sjasmplus not found in PATH']
    except subprocess.TimeoutExpired:
        return ['assembly timed out']
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='T-state audit tool — compare inline annotations with computed values',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('files', nargs='*', help='Z80 assembly files to audit')
    parser.add_argument('--asm-check', action='store_true',
                        help='Also check with sjasmplus for invalid instructions')
    parser.add_argument('--scan-chapters', action='store_true',
                        help='Scan inline code blocks in chapter drafts')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Show OK and MISSING annotations too')
    parser.add_argument('--summary', action='store_true',
                        help='Only show summary counts')

    args = parser.parse_args()

    if args.scan_chapters:
        findings = scan_chapters(verbose=args.verbose)
        counts = {'WRONG': 0, 'UNKNOWN': 0, 'PARTIAL': 0, 'MISSING': 0}

        for f in findings:
            file_path, line_num, status, instr, detail = f
            counts[status] = counts.get(status, 0) + 1
            if not args.summary:
                print(f'{file_path}:{line_num}  {status:8s}  {instr:<30s}  {detail}')

        print(f'\n---')
        print(f'Chapter scan: {counts["WRONG"]} WRONG, {counts["UNKNOWN"]} UNKNOWN, '
              f'{counts.get("PARTIAL", 0)} PARTIAL, {counts.get("MISSING", 0)} MISSING')
        sys.exit(1 if counts['WRONG'] or counts['UNKNOWN'] else 0)

    if not args.files:
        parser.print_help()
        sys.exit(1)

    total_counts = {'OK': 0, 'WRONG': 0, 'UNKNOWN': 0, 'MISSING': 0, 'PARTIAL': 0}
    asm_errors = []

    for filepath in args.files:
        if not Path(filepath).exists():
            print(f'{filepath}: FILE NOT FOUND', file=sys.stderr)
            continue

        findings = audit_file(filepath, verbose=args.verbose)
        rel = Path(filepath).name

        for line_num, status, instr, detail in findings:
            total_counts[status] = total_counts.get(status, 0) + 1
            if not args.summary:
                print(f'{rel}:{line_num}  {status:8s}  {instr:<30s}  {detail}')

        if args.asm_check:
            errors = asm_check_file(filepath)
            if errors:
                for e in errors:
                    asm_errors.append(f'{rel}: {e}')
                    if not args.summary:
                        print(f'{rel}  ASM_ERR  {e}')

    print(f'\n---')
    print(f'Files: {len(args.files)}')
    print(f'T-states: {total_counts["WRONG"]} WRONG, {total_counts["UNKNOWN"]} UNKNOWN, '
          f'{total_counts.get("PARTIAL", 0)} PARTIAL')
    if args.verbose:
        print(f'  {total_counts["OK"]} OK, {total_counts["MISSING"]} MISSING')
    if args.asm_check:
        print(f'Assembly: {len(asm_errors)} errors')

    sys.exit(1 if total_counts['WRONG'] or total_counts['UNKNOWN'] or asm_errors else 0)


if __name__ == '__main__':
    main()
