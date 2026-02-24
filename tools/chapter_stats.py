#!/usr/bin/env python3
"""Extract mechanical metadata from all English chapter drafts.

Outputs per-chapter: word count, code blocks, sections, TODOs, cross-refs.
No LLM needed — pure parsing.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHAPTERS = sorted(ROOT.glob("chapters/ch*/draft.md"))

TODO_RE = re.compile(r'\b(TODO|FIXME|TBD|XXX|\?\?\?)\b', re.IGNORECASE)
XREF_RE = re.compile(r'[Cc]hapter\s+(\d+)')
FENCE_RE = re.compile(r'^```(\w*)(.*)')
HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)')


def analyze(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Word count (prose only, skip code blocks)
    prose_words = 0
    code_blocks = []
    in_code = False
    code_lang = ""
    code_meta = ""
    code_lines = 0
    headings = []
    todos = []
    xrefs = set()
    figures = 0

    for i, line in enumerate(lines, 1):
        if in_code:
            if line.startswith("```"):
                code_blocks.append({"lang": code_lang, "meta": code_meta, "lines": code_lines})
                in_code = False
            else:
                code_lines += 1
            continue

        m = FENCE_RE.match(line)
        if m:
            in_code = True
            code_lang = m.group(1) or "unknown"
            code_meta = m.group(2).strip()
            code_lines = 0
            continue

        # Headings
        hm = HEADING_RE.match(line)
        if hm:
            headings.append({"level": len(hm.group(1)), "text": hm.group(2), "line": i})

        # Prose words
        prose_words += len(line.split())

        # TODOs
        for tm in TODO_RE.finditer(line):
            todos.append({"marker": tm.group(), "line": i, "context": line.strip()[:80]})

        # Cross-refs
        for xm in XREF_RE.finditer(line):
            xrefs.add(int(xm.group(1)))

        # Figures
        if re.search(r'!\[', line) or re.search(r'<figure', line, re.I):
            figures += 1

    # Code block summary
    lang_counts = {}
    tagged = 0
    untagged = 0
    for cb in code_blocks:
        lang_counts[cb["lang"]] = lang_counts.get(cb["lang"], 0) + 1
        if cb["meta"]:
            tagged += 1
        else:
            untagged += 1

    ch_num = int(path.parent.name[2:4])
    return {
        "chapter": ch_num,
        "dir": path.parent.name,
        "prose_words": prose_words,
        "code_blocks": len(code_blocks),
        "code_by_lang": lang_counts,
        "tagged": tagged,
        "untagged": untagged,
        "total_code_lines": sum(cb["lines"] for cb in code_blocks),
        "headings": headings,
        "h2_count": sum(1 for h in headings if h["level"] == 2),
        "h3_count": sum(1 for h in headings if h["level"] == 3),
        "todos": todos,
        "xrefs": sorted(xrefs),
        "figures": figures,
    }


def print_report(stats: list[dict]):
    total_words = 0
    total_code = 0
    total_code_lines = 0
    total_todos = 0

    print("=" * 90)
    print(f"{'Ch':>3}  {'Words':>6}  {'Code':>4}  {'Tag':>3}/{' Untag':<5}  "
          f"{'CLines':>6}  {'H2':>3}  {'H3':>3}  {'Fig':>3}  {'TODO':>4}  {'XRefs'}")
    print("-" * 90)

    for s in stats:
        total_words += s["prose_words"]
        total_code += s["code_blocks"]
        total_code_lines += s["total_code_lines"]
        total_todos += len(s["todos"])

        xref_str = ",".join(str(x) for x in s["xrefs"][:6])
        if len(s["xrefs"]) > 6:
            xref_str += "..."

        print(f"{s['chapter']:3d}  {s['prose_words']:6d}  {s['code_blocks']:4d}  "
              f"{s['tagged']:3d} / {s['untagged']:<5d}  "
              f"{s['total_code_lines']:6d}  {s['h2_count']:3d}  {s['h3_count']:3d}  "
              f"{s['figures']:3d}  {len(s['todos']):4d}  {xref_str}")

    print("-" * 90)
    print(f"TOT  {total_words:6d}  {total_code:4d}  "
          f"{'':>3}   {'':5}  {total_code_lines:6d}  "
          f"{'':>3}  {'':>3}  {'':>3}  {total_todos:4d}")
    print("=" * 90)

    # TODOs detail
    all_todos = [(s["chapter"], t) for s in stats for t in s["todos"]]
    if all_todos:
        print(f"\n--- TODOs ({len(all_todos)}) ---")
        for ch, t in all_todos:
            print(f"  Ch{ch:02d}:{t['line']}  [{t['marker']}]  {t['context']}")

    # Code language breakdown
    all_langs = {}
    for s in stats:
        for lang, cnt in s["code_by_lang"].items():
            all_langs[lang] = all_langs.get(lang, 0) + cnt
    print(f"\n--- Code blocks by language ---")
    for lang, cnt in sorted(all_langs.items(), key=lambda x: -x[1]):
        print(f"  {lang:12s}  {cnt:4d}")

    # Thin chapters (< 3000 words)
    thin = [s for s in stats if s["prose_words"] < 3000]
    if thin:
        print(f"\n--- Thin chapters (< 3000 words) ---")
        for s in thin:
            print(f"  Ch{s['chapter']:02d} ({s['dir']}): {s['prose_words']} words")

    # Code-heavy chapters (code lines > prose words * 0.5)
    heavy = [s for s in stats if s["total_code_lines"] > s["prose_words"] * 0.3]
    if heavy:
        print(f"\n--- Code-heavy chapters (code > 30% of prose) ---")
        for s in heavy:
            ratio = s["total_code_lines"] / max(s["prose_words"], 1) * 100
            print(f"  Ch{s['chapter']:02d}: {ratio:.0f}% code-to-prose ratio")


def main():
    if not CHAPTERS:
        print("No chapters found!", file=sys.stderr)
        sys.exit(1)

    stats = [analyze(ch) for ch in CHAPTERS]
    print_report(stats)


if __name__ == "__main__":
    main()
