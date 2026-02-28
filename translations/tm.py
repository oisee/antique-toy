#!/usr/bin/env python3
"""Translation Memory tool for paragraph-level reuse.

Builds a TM by aligning v0.6 EN paragraphs with their ES/RU/UK translations,
diffs current EN against v0.6 EN at segment level, exports only the delta
for LLM translation, and applies LLM output back.

Usage:
    python3 translations/tm.py build              # Build TM from v0.6 alignment
    python3 translations/tm.py diff es [ch04]     # Segment-level change report
    python3 translations/tm.py export es [ch04]   # Delta for LLM (stdout)
    python3 translations/tm.py apply es ch04 FILE # Merge LLM output → translated .md
    python3 translations/tm.py stats              # Reuse statistics
"""

import difflib
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
TRANSLATIONS_DIR = ROOT / "translations"
TM_FILE = TRANSLATIONS_DIR / "tm.json"
MANIFEST_FILE = TRANSLATIONS_DIR / "manifest.json"
LANGUAGES = ["es", "ru", "uk"]
BASE_REF = "v0.6"

try:
    from rapidfuzz.fuzz import ratio as _rf_ratio
    def similarity(a, b):
        return _rf_ratio(a, b) / 100.0
except ImportError:
    def similarity(a, b):
        return difflib.SequenceMatcher(None, a, b).ratio()


# ---------------------------------------------------------------------------
# Segmentation
# ---------------------------------------------------------------------------

def segment_markdown(text):
    """Split markdown into blocks. Code fences are atomic (span blank lines).

    Returns list of dicts: {"type": str, "text": str}
    """
    lines = text.split("\n")
    blocks = []
    current_lines = []
    in_fence = False

    def flush():
        nonlocal current_lines
        if not current_lines:
            return
        raw = "\n".join(current_lines)
        # Don't emit pure-whitespace blocks
        if raw.strip():
            blocks.append(raw)
        current_lines = []

    for line in lines:
        if not in_fence and line.startswith("```"):
            flush()
            in_fence = True
            current_lines.append(line)
        elif in_fence and line.startswith("```"):
            current_lines.append(line)
            in_fence = False
            flush()
        elif in_fence:
            current_lines.append(line)
        elif line.strip() == "":
            flush()
        else:
            current_lines.append(line)

    flush()
    return [{"type": classify_block(b), "text": b} for b in blocks]


def classify_block(text):
    """Classify a markdown block by type."""
    first = text.lstrip()
    if first.startswith("```"):
        return "code"
    if re.match(r"^#{1,6}\s", first):
        return "heading"
    if first.startswith("<!--") or first.startswith("<!-- "):
        return "comment"
    if first.startswith("---") and len(first.strip()) <= 5:
        return "hr"
    if first.startswith("!["):
        return "image"
    if first.startswith("|"):
        return "table"
    if first.startswith(">"):
        return "blockquote"
    if re.match(r"^[\-\*]\s|^\d+\.\s", first):
        return "list"
    return "paragraph"


def is_translatable(block_type):
    return block_type not in ("code", "hr", "comment")


# Block-type markers that may leak from LLM output
_TYPE_MARKER_RE = re.compile(
    r"^\((?:paragraph|heading|table|list|blockquote|image|code|hr|comment)\)\s*$"
)


def sanitize_block(text):
    """Strip block-type marker lines that leaked from export format."""
    lines = text.split("\n")
    cleaned = [l for l in lines if not _TYPE_MARKER_RE.match(l.strip())]
    # Remove leading/trailing blank lines introduced by removal
    result = "\n".join(cleaned).strip()
    return result if result else text


def block_hash(block):
    """Hash a block for comparison. Code blocks hash by body only (strip fence lines)."""
    text = block["text"]
    if block["type"] == "code":
        lines = text.split("\n")
        # Strip first and last lines (fence markers)
        body = "\n".join(lines[1:-1]) if len(lines) > 2 else ""
        return hashlib.sha256(body.encode()).hexdigest()[:12]
    return hashlib.sha256(text.encode()).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def git_show(ref, path):
    """Get file content from a git ref. Returns None if not found."""
    try:
        result = subprocess.run(
            ["git", "show", f"{ref}:{path}"],
            capture_output=True, text=True, cwd=ROOT,
        )
        if result.returncode == 0:
            return result.stdout
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Manifest / path helpers
# ---------------------------------------------------------------------------

def load_manifest():
    if MANIFEST_FILE.exists():
        return json.loads(MANIFEST_FILE.read_text())
    return {}


def en_source_path(key):
    """Relative path to EN source for a manifest key."""
    if key.startswith("chapters/"):
        name = key.split("/")[1]
        return f"chapters/{name}/draft.md"
    elif key.startswith("appendices/"):
        name = key.split("/")[1]
        return f"appendices/{name}.md"
    elif key == "glossary":
        return "glossary.md"
    return None


def translation_path(lang, key):
    """Absolute path to translation file."""
    if key.startswith("chapters/"):
        name = key.split("/")[1]
        return TRANSLATIONS_DIR / lang / "chapters" / f"{name}.md"
    elif key.startswith("appendices/"):
        name = key.split("/")[1]
        return TRANSLATIONS_DIR / lang / "appendices" / f"{name}.md"
    elif key == "glossary":
        return TRANSLATIONS_DIR / lang / "glossary.md"
    return None


def resolve_key_filter(filter_str):
    """Resolve a CLI filter like 'ch04' to matching manifest keys."""
    if not filter_str:
        return None  # no filter = all
    manifest = load_manifest()
    # Collect all keys from all languages
    all_keys = set()
    for lang_data in manifest.values():
        all_keys.update(lang_data.keys())
    matches = [k for k in sorted(all_keys) if filter_str in k]
    return matches if matches else None


# ---------------------------------------------------------------------------
# TM storage
# ---------------------------------------------------------------------------

def load_tm():
    if TM_FILE.exists():
        return json.loads(TM_FILE.read_text())
    return {"meta": {}, "segments": {}}


def save_tm(tm):
    TM_FILE.write_text(json.dumps(tm, indent=2, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# build command
# ---------------------------------------------------------------------------

def cmd_build():
    """Build TM from v0.6 alignment."""
    manifest = load_manifest()
    # Collect all keys that have at least one language translated
    all_keys = set()
    for lang in LANGUAGES:
        if lang in manifest:
            all_keys.update(manifest[lang].keys())

    tm = {
        "meta": {
            "version": 1,
            "base_ref": BASE_REF,
            "built": datetime.now(timezone.utc).isoformat(),
            "segments_total": 0,
        },
        "segments": {},
    }

    total_segments = 0
    warnings = []

    for key in sorted(all_keys):
        src_path = en_source_path(key)
        if not src_path:
            continue

        # Get v0.6 EN source
        en_text = git_show(BASE_REF, src_path)
        if en_text is None:
            warnings.append(f"  SKIP {key}: not found at {BASE_REF}")
            continue

        en_blocks = segment_markdown(en_text)
        segments = []

        # Load translations for each language
        lang_blocks = {}
        for lang in LANGUAGES:
            tr_path = translation_path(lang, key)
            if tr_path and tr_path.exists():
                # Use current on-disk translation (corresponds to v0.6 EN)
                tr_text = tr_path.read_text()
                lang_blocks[lang] = segment_markdown(tr_text)

        for lang, tr_blks in lang_blocks.items():
            diff = abs(len(en_blocks) - len(tr_blks))
            if diff > 3:
                warnings.append(
                    f"  WARN {key}/{lang}: block count mismatch "
                    f"(EN={len(en_blocks)}, {lang.upper()}={len(tr_blks)}, diff={diff})"
                )

        for i, en_blk in enumerate(en_blocks):
            seg = {
                "type": en_blk["type"],
                "en": en_blk["text"],
                "en_hash": block_hash(en_blk),
            }
            if is_translatable(en_blk["type"]):
                for lang in LANGUAGES:
                    tr_blks = lang_blocks.get(lang)
                    if tr_blks and i < len(tr_blks):
                        seg[lang] = tr_blks[i]["text"]
            segments.append(seg)

        tm["segments"][key] = segments
        total_segments += len(segments)

    tm["meta"]["segments_total"] = total_segments
    save_tm(tm)

    print(f"Built TM: {len(tm['segments'])} items, {total_segments} segments")
    print(f"Saved to {TM_FILE}")
    if warnings:
        print()
        for w in warnings:
            print(w)


# ---------------------------------------------------------------------------
# diff command
# ---------------------------------------------------------------------------

def diff_chapter(tm, key, lang):
    """Compute segment-level diff for a chapter. Returns (equal, modified, new, deleted) counts
    and a list of (status, current_idx, tm_idx) tuples."""
    tm_segs = tm["segments"].get(key)
    if not tm_segs:
        return None

    src_path = en_source_path(key)
    if not src_path:
        return None

    en_file = ROOT / src_path
    if not en_file.exists():
        return None

    current_blocks = segment_markdown(en_file.read_text())
    tm_hashes = [s["en_hash"] for s in tm_segs]
    cur_hashes = [block_hash(b) for b in current_blocks]

    sm = difflib.SequenceMatcher(None, tm_hashes, cur_hashes)
    opcodes = sm.get_opcodes()

    equal = 0
    modified = 0
    new = 0
    deleted = 0
    details = []

    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            for k in range(i2 - i1):
                equal += 1
                details.append(("EQUAL", j1 + k, i1 + k))
        elif tag == "replace":
            tm_range = list(range(i1, i2))
            cur_range = list(range(j1, j2))
            # Pair by similarity
            paired_tm = set()
            for ci in cur_range:
                best_sim = 0
                best_ti = None
                for ti in tm_range:
                    if ti in paired_tm:
                        continue
                    sim = similarity(current_blocks[ci]["text"], tm_segs[ti]["en"])
                    if sim > best_sim:
                        best_sim = sim
                        best_ti = ti
                if best_ti is not None and best_sim >= 0.5:
                    modified += 1
                    details.append(("MODIFIED", ci, best_ti))
                    paired_tm.add(best_ti)
                else:
                    new += 1
                    details.append(("NEW", ci, None))
            # Remaining unpaired TM segments are deleted
            for ti in tm_range:
                if ti not in paired_tm:
                    deleted += 1
        elif tag == "insert":
            for k in range(j2 - j1):
                new += 1
                details.append(("NEW", j1 + k, None))
        elif tag == "delete":
            deleted += (i2 - i1)

    # Check if translation exists for this lang
    has_translation = any(lang in s for s in tm_segs if is_translatable(s["type"]))

    return {
        "equal": equal,
        "modified": modified,
        "new": new,
        "deleted": deleted,
        "details": details,
        "current_blocks": current_blocks,
        "tm_segs": tm_segs,
        "has_translation": has_translation,
    }


def cmd_diff(lang, filter_keys=None):
    """Show segment-level change report."""
    tm = load_tm()
    if not tm["segments"]:
        print("TM is empty. Run 'build' first.")
        sys.exit(1)

    keys = filter_keys or sorted(tm["segments"].keys())
    grand = {"equal": 0, "modified": 0, "new": 0, "deleted": 0}

    for key in keys:
        result = diff_chapter(tm, key, lang)
        if result is None:
            # Could be a new item not in TM
            src_path = en_source_path(key)
            if src_path and (ROOT / src_path).exists():
                blocks = segment_markdown((ROOT / src_path).read_text())
                print(f"  {key}: ENTIRELY NEW ({len(blocks)} blocks)")
                grand["new"] += len(blocks)
            continue

        total = result["equal"] + result["modified"] + result["new"]
        if total == 0:
            continue

        eq_pct = 100 * result["equal"] / total if total else 0
        mod_pct = 100 * result["modified"] / total if total else 0
        new_pct = 100 * result["new"] / total if total else 0

        status = ""
        if not result["has_translation"]:
            status = " [no {lang} translation]"

        print(
            f"  {key}: "
            f"EQUAL: {result['equal']} ({eq_pct:.0f}%) | "
            f"MODIFIED: {result['modified']} ({mod_pct:.0f}%) | "
            f"NEW: {result['new']} ({new_pct:.0f}%)"
            f"{status}"
        )

        grand["equal"] += result["equal"]
        grand["modified"] += result["modified"]
        grand["new"] += result["new"]
        grand["deleted"] += result["deleted"]

    gtotal = grand["equal"] + grand["modified"] + grand["new"]
    if gtotal:
        print(f"\n  TOTAL: EQUAL: {grand['equal']} ({100*grand['equal']/gtotal:.0f}%) | "
              f"MODIFIED: {grand['modified']} ({100*grand['modified']/gtotal:.0f}%) | "
              f"NEW: {grand['new']} ({100*grand['new']/gtotal:.0f}%)")


# ---------------------------------------------------------------------------
# export command
# ---------------------------------------------------------------------------

def cmd_export(lang, filter_keys=None):
    """Export translation delta for LLM."""
    tm = load_tm()
    if not tm["segments"]:
        print("TM is empty. Run 'build' first.", file=sys.stderr)
        sys.exit(1)

    keys = filter_keys or sorted(tm["segments"].keys())

    # Header
    print("# Translation Job")
    print()
    print(f"**Target language:** {lang.upper()}")
    print(f"**Base reference:** {BASE_REF}")
    print()
    print("**Instructions:**")
    print("- Translate ONLY blocks marked TRANSLATE or UPDATE")
    print("- Blocks marked VERBATIM must be kept exactly as shown")
    print("- Blocks marked CONTEXT are for reference only, do not include in output")
    print("- Preserve all markdown formatting (headers, bold, links, etc.)")
    print("- Consult `translations/glossary-lookup.md` for canonical term translations")
    print("- Output each translated block under its `## Block N` header")
    print("- Do NOT echo type annotations like (paragraph), (heading), etc. in output")
    print("- For heading blocks: output the full translated heading with its # prefix")
    print()
    print("---")
    print()

    for key in keys:
        result = diff_chapter(tm, key, lang)
        if result is None:
            # Entirely new chapter
            src_path = en_source_path(key)
            if not src_path:
                continue
            en_file = ROOT / src_path
            if not en_file.exists():
                continue
            blocks = segment_markdown(en_file.read_text())
            print(f"# {key} (NEW)")
            print()
            for i, blk in enumerate(blocks):
                if is_translatable(blk["type"]):
                    print(f"## Block {i} — TRANSLATE")
                else:
                    print(f"## Block {i} — VERBATIM")
                print(f"<!-- type: {blk['type']} -->")
                print()
                print(blk["text"])
                print()
            continue

        # Has TM data — export only delta
        has_any_delta = any(
            s != "EQUAL" for s, _, _ in result["details"]
        )
        if not has_any_delta:
            continue

        print(f"# {key}")
        print()

        for status, cur_idx, tm_idx in result["details"]:
            blk = result["current_blocks"][cur_idx]
            btype = blk["type"]

            if status == "EQUAL":
                # Skip — will be reused from TM
                continue

            if not is_translatable(btype):
                print(f"## Block {cur_idx} — VERBATIM")
                print(f"<!-- type: {btype} -->")
                print()
                print(blk["text"])
                print()
                continue

            if status == "MODIFIED" and tm_idx is not None:
                tm_seg = result["tm_segs"][tm_idx]
                print(f"## Block {cur_idx} — UPDATE")
                print(f"<!-- type: {btype} -->")
                print()
                print("### Current EN:")
                print()
                print(blk["text"])
                print()
                if lang in tm_seg:
                    print(f"### Previous {lang.upper()} (reference):")
                    print()
                    print(tm_seg[lang])
                    print()
                print("### Previous EN (reference):")
                print()
                print(tm_seg["en"])
                print()
            elif status == "NEW":
                print(f"## Block {cur_idx} — TRANSLATE")
                print(f"<!-- type: {btype} -->")
                print()
                print(blk["text"])
                print()

        print("---")
        print()


# ---------------------------------------------------------------------------
# apply command
# ---------------------------------------------------------------------------

def cmd_apply(lang, key, input_file):
    """Merge LLM output back with TM to produce complete translated file."""
    tm = load_tm()
    if not tm["segments"]:
        print("TM is empty. Run 'build' first.", file=sys.stderr)
        sys.exit(1)

    input_path = Path(input_file)
    if not input_path.exists():
        print(f"Input file not found: {input_file}", file=sys.stderr)
        sys.exit(1)

    llm_text = input_path.read_text()
    result = diff_chapter(tm, key, lang)

    # Parse LLM output — look for ## Block N headers
    llm_blocks = parse_llm_output(llm_text)

    if not llm_blocks and result is not None:
        # Try full-chapter mode: LLM produced a complete translated .md
        llm_segments = segment_markdown(llm_text)
        llm_blocks = {i: seg["text"] for i, seg in enumerate(llm_segments)}

    # Build the final output
    src_path = en_source_path(key)
    if not src_path:
        print(f"Unknown key: {key}", file=sys.stderr)
        sys.exit(1)

    en_file = ROOT / src_path
    if not en_file.exists():
        print(f"EN source not found: {en_file}", file=sys.stderr)
        sys.exit(1)

    current_blocks = segment_markdown(en_file.read_text())
    output_parts = []

    if result is None:
        # Entirely new chapter — all from LLM
        for i, blk in enumerate(current_blocks):
            if not is_translatable(blk["type"]):
                output_parts.append(blk["text"])
            elif i in llm_blocks:
                output_parts.append(llm_blocks[i])
            else:
                # Fallback to EN if LLM didn't provide
                output_parts.append(blk["text"])
    else:
        # Merge TM + LLM
        for status, cur_idx, tm_idx in result["details"]:
            blk = current_blocks[cur_idx]

            if not is_translatable(blk["type"]):
                # Non-translatable: use current EN verbatim
                output_parts.append(blk["text"])
            elif status == "EQUAL" and tm_idx is not None:
                # Reuse TM translation
                tm_seg = result["tm_segs"][tm_idx]
                if lang in tm_seg:
                    output_parts.append(tm_seg[lang])
                else:
                    output_parts.append(blk["text"])
            elif cur_idx in llm_blocks:
                # Use LLM output
                output_parts.append(llm_blocks[cur_idx])
            else:
                # Fallback to EN
                print(f"  WARNING: Block {cur_idx} missing from LLM output, using EN",
                      file=sys.stderr)
                output_parts.append(blk["text"])

    # Sanitize: strip any leaked type-marker lines
    output_parts = [sanitize_block(p) for p in output_parts]

    # Write output
    out_path = translation_path(lang, key)
    if out_path is None:
        print(f"Cannot determine output path for {key}", file=sys.stderr)
        sys.exit(1)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n\n".join(output_parts) + "\n")
    print(f"Written: {out_path}")

    # Update TM with new entries
    update_tm_after_apply(tm, key, lang, current_blocks, output_parts)
    save_tm(tm)
    print(f"TM updated for {key}/{lang}")


def parse_llm_output(text):
    """Parse LLM structured output with ## Block N headers."""
    blocks = {}
    # Match both old format (with type annotation) and new format (without)
    pattern = re.compile(
        r"^## Block (\d+)\s*[—–-]\s*(?:TRANSLATE|UPDATE|VERBATIM)(?:\s*\([\w]+\))?",
        re.MULTILINE,
    )
    matches = list(pattern.finditer(text))

    for i, m in enumerate(matches):
        block_num = int(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        # Strip HTML comment type annotations (<!-- type: paragraph -->)
        content = re.sub(r"^<!--\s*type:\s*\w+\s*-->\s*\n?", "", content)
        # Strip any sub-headers (### Current EN:, ### Previous, etc.)
        # Keep only the first non-header content block
        lines = content.split("\n")
        result_lines = []
        skip = False
        for line in lines:
            if line.startswith("### "):
                skip = True
                continue
            if skip and line.strip() == "":
                continue
            if skip and not line.startswith("### "):
                # This is content after a sub-header — only take it if it's
                # the first (translated) section before any reference sections
                pass
            skip = False
            result_lines.append(line)

        content = "\n".join(result_lines).strip()
        # Remove trailing --- separators
        content = re.sub(r"\n---\s*$", "", content)
        # Strip leaked type-marker lines
        content = sanitize_block(content)
        if content:
            blocks[block_num] = content

    return blocks


def update_tm_after_apply(tm, key, lang, current_blocks, translated_parts):
    """Update TM segments for a chapter after apply."""
    new_segs = []
    for i, blk in enumerate(current_blocks):
        seg = {
            "type": blk["type"],
            "en": blk["text"],
            "en_hash": block_hash(blk),
        }
        # Carry over existing translations from old TM
        old_segs = tm["segments"].get(key, [])
        # Find matching old segment by hash
        for old in old_segs:
            if old["en_hash"] == seg["en_hash"]:
                for l in LANGUAGES:
                    if l in old and l != lang:
                        seg[l] = old[l]
                break

        if is_translatable(blk["type"]) and i < len(translated_parts):
            seg[lang] = translated_parts[i]

        new_segs.append(seg)

    tm["segments"][key] = new_segs
    # Update total
    tm["meta"]["segments_total"] = sum(len(s) for s in tm["segments"].values())


# ---------------------------------------------------------------------------
# stats command
# ---------------------------------------------------------------------------

def cmd_stats():
    """Show reuse statistics."""
    tm = load_tm()
    if not tm["segments"]:
        print("TM is empty. Run 'build' first.")
        sys.exit(1)

    print(f"TM: {tm['meta'].get('base_ref', '?')} | "
          f"{len(tm['segments'])} items | "
          f"{tm['meta'].get('segments_total', '?')} segments | "
          f"built {tm['meta'].get('built', '?')}")
    print()

    for lang in LANGUAGES:
        print(f"=== {lang.upper()} ===")
        grand = {"equal": 0, "modified": 0, "new": 0}

        for key in sorted(tm["segments"].keys()):
            result = diff_chapter(tm, key, lang)
            if result is None:
                # New item not in TM
                src_path = en_source_path(key)
                if src_path and (ROOT / src_path).exists():
                    blocks = segment_markdown((ROOT / src_path).read_text())
                    n = len(blocks)
                    grand["new"] += n
                    print(f"  {key}: NEW ({n} blocks)")
                continue

            total = result["equal"] + result["modified"] + result["new"]
            if total == 0:
                continue

            eq_pct = 100 * result["equal"] / total
            grand["equal"] += result["equal"]
            grand["modified"] += result["modified"]
            grand["new"] += result["new"]

            if result["equal"] == total:
                print(f"  {key}: 100% reuse ({total} blocks)")
            else:
                print(
                    f"  {key}: "
                    f"EQUAL={result['equal']} "
                    f"MOD={result['modified']} "
                    f"NEW={result['new']} "
                    f"({eq_pct:.0f}% reuse)"
                )

        gtotal = grand["equal"] + grand["modified"] + grand["new"]
        if gtotal:
            reuse_pct = 100 * grand["equal"] / gtotal
            savings = 100 * (grand["equal"] + 0.5 * grand["modified"]) / gtotal
            print(f"\n  TOTAL: {grand['equal']}/{gtotal} blocks reusable ({reuse_pct:.0f}%)")
            print(f"  Estimated translation cost savings: {savings:.0f}%")
        print()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "build":
        cmd_build()
    elif cmd == "diff":
        if len(sys.argv) < 3:
            print("Usage: tm.py diff <lang> [filter]")
            sys.exit(1)
        lang = sys.argv[2]
        if lang not in LANGUAGES:
            print(f"Unknown language: {lang}. Use: {LANGUAGES}")
            sys.exit(1)
        filt = sys.argv[3] if len(sys.argv) > 3 else None
        filter_keys = resolve_key_filter(filt)
        cmd_diff(lang, filter_keys)
    elif cmd == "export":
        if len(sys.argv) < 3:
            print("Usage: tm.py export <lang> [filter]")
            sys.exit(1)
        lang = sys.argv[2]
        if lang not in LANGUAGES:
            print(f"Unknown language: {lang}. Use: {LANGUAGES}")
            sys.exit(1)
        filt = sys.argv[3] if len(sys.argv) > 3 else None
        filter_keys = resolve_key_filter(filt)
        cmd_export(lang, filter_keys)
    elif cmd == "apply":
        if len(sys.argv) < 5:
            print("Usage: tm.py apply <lang> <key> <file>")
            sys.exit(1)
        lang = sys.argv[2]
        if lang not in LANGUAGES:
            print(f"Unknown language: {lang}. Use: {LANGUAGES}")
            sys.exit(1)
        key_filter = sys.argv[3]
        keys = resolve_key_filter(key_filter)
        if not keys or len(keys) != 1:
            print(f"Key filter '{key_filter}' must match exactly one item, got: {keys}")
            sys.exit(1)
        cmd_apply(lang, keys[0], sys.argv[4])
    elif cmd == "stats":
        cmd_stats()
    else:
        print(f"Unknown command: {cmd}. Use: build, diff, export, apply, stats")
        sys.exit(1)


if __name__ == "__main__":
    main()
