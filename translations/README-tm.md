# Translation Memory Tool

`translations/tm.py` -- paragraph-level Translation Memory for incremental retranslation.

## What it does

The tool segments every chapter into markdown blocks (paragraphs, headings, code fences, lists, etc.), aligns the v0.6 English source with the existing ES/RU/UK translations by position, and stores these aligned pairs in `translations/tm.json`. When the English source is later edited, it diffs the current EN against the v0.6 baseline at the block level, classifies each block as EQUAL, MODIFIED, or NEW, and exports only the changed blocks for LLM translation. After the LLM translates the delta, `apply` merges the new translations with the unchanged blocks from TM and writes the complete translated file.

## Why

All three translations (ES, RU, UK) were completed at v0.6. Since then, the English text has gone through many editing passes, but most changes are localized. Roughly 87% of blocks are identical to v0.6, so only ~13% need retranslation. For MODIFIED blocks, the tool provides both the old EN and old translation as context, so the LLM can adapt rather than translate from scratch. The estimated cost savings are ~89% compared to full retranslation.

## Commands

All commands are run from the repository root.

### `build` -- build TM from v0.6 alignment

```sh
python3 translations/tm.py build
```

Reads every chapter/appendix at the `v0.6` git tag, segments it, aligns each block with the on-disk translations, and writes `translations/tm.json`. Run this once before using any other command.

### `stats` -- reuse statistics

```sh
python3 translations/tm.py stats
```

Shows per-language, per-chapter breakdown: how many blocks are reusable (EQUAL), how many need updating (MODIFIED), how many are entirely new (NEW), and the estimated cost savings.

### `diff <lang> [filter]` -- segment-level change report

```sh
python3 translations/tm.py diff es          # all chapters, Spanish
python3 translations/tm.py diff ru ch04     # only chapter 4, Russian
python3 translations/tm.py diff uk app      # appendices matching "app", Ukrainian
```

Prints counts and percentages for EQUAL / MODIFIED / NEW blocks per chapter. The optional filter is a substring match against manifest keys (e.g. `ch04` matches `chapters/ch04-fast-multiply`).

### `export <lang> [filter]` -- export delta for LLM translation

```sh
python3 translations/tm.py export es ch04 > /tmp/tm_ru/ch04-delta.md
python3 translations/tm.py export ru > /tmp/tm_ru/all-delta.md
```

Writes a structured document to stdout containing only the blocks that need translation. Each block is labeled:

- **TRANSLATE** -- new block, no prior translation exists. Full EN text provided.
- **UPDATE** -- block was modified since v0.6. Current EN, previous EN, and previous translation are all provided for context.
- **VERBATIM** -- non-translatable block (code fence, horizontal rule). Keep as-is.

Blocks that are EQUAL to the TM are omitted entirely -- they will be filled in automatically during `apply`.

### `apply <lang> <key> <file>` -- merge LLM output back

```sh
python3 translations/tm.py apply es ch04 /tmp/tm_ru/ch04-translated.md
```

Reads the LLM output file, parses `## Block N` headers to extract translated blocks, merges them with EQUAL blocks from TM, and writes the complete translated chapter to `translations/<lang>/chapters/<name>.md`. Also updates `tm.json` with the new translations.

The key filter must match exactly one manifest entry. The LLM output can use either the structured `## Block N` format (preferred) or be a plain translated markdown file, which will be segmented and matched by position.

## Workflow

The full retranslation cycle for a language:

```sh
# 1. Build TM (once, or after rebasing translations)
python3 translations/tm.py build

# 2. Check what changed
python3 translations/tm.py diff es
python3 translations/tm.py stats

# 3. Export delta for one chapter
python3 translations/tm.py export es ch04 > /tmp/tm_ru/ch04-delta.md

# 4. Translate (feed the delta file to an LLM with glossary-lookup.md)

# 5. Merge result back
python3 translations/tm.py apply es ch04 /tmp/tm_ru/ch04-translated.md

# 6. Stamp the manifest so manifest.py knows this translation is current
python3 translations/manifest.py stamp es
```

Repeat steps 3-5 for each chapter, or export all at once with no filter.

## Block types

The segmenter splits markdown on blank lines (code fences are atomic and span blank lines). Each block is classified:

| Type | Translatable | Description |
|------|-------------|-------------|
| paragraph | yes | Regular prose text |
| heading | yes | `# ...` through `###### ...` |
| list | yes | Bullet or numbered lists |
| blockquote | yes | `> ...` quoted text |
| table | yes | Pipe-delimited tables |
| image | yes | `![alt](path)` (alt text is translated) |
| code | no | Fenced code blocks (` ``` ... ``` `) |
| hr | no | Horizontal rules (`---`) |
| comment | no | HTML comments (`<!-- ... -->`) |

Non-translatable blocks are carried through verbatim from the current EN source. Code blocks are compared by body only (fence markers stripped before hashing) so that changing the language tag on a fence does not trigger a false diff.

## Storage

`translations/tm.json` contains:

```json
{
  "meta": {
    "version": 1,
    "base_ref": "v0.6",
    "built": "2026-02-28T...",
    "segments_total": 4200
  },
  "segments": {
    "chapters/ch01-thinking-in-cycles": [
      {
        "type": "heading",
        "en": "# Chapter 1: Thinking in Cycles",
        "en_hash": "a1b2c3d4e5f6",
        "es": "# Capitulo 1: Pensando en Ciclos",
        "ru": "# Глава 1: Мыслить тактами",
        "uk": "# Розділ 1: Мислити тактами"
      }
    ]
  }
}
```

Each segment stores the v0.6 EN text, a truncated SHA-256 hash of the EN text, the block type, and the aligned translation for each language that had one. The `apply` command updates segments in place after merging.

## Integration with manifest.py

The TM tool and the manifest system are complementary:

- **manifest.py** tracks whether a translation file is stale (EN source changed since last stamp). It works at the file level.
- **tm.py** works at the block level within files. It knows which specific paragraphs changed and can reuse the rest.

After running `apply`, always run `manifest.py stamp` to record the current EN hash:

```sh
python3 translations/tm.py apply es ch04 /tmp/tm_ru/ch04-translated.md
python3 translations/manifest.py stamp es
```

Use `manifest.py check` to find which files need retranslation, then use `tm.py diff` and `tm.py export` to minimize the actual translation work.

## Dependencies

- Python 3.8+
- Git (for `git show` to read v0.6 baseline)
- Optional: `rapidfuzz` for faster similarity matching in diff/apply. Falls back to `difflib.SequenceMatcher` if not installed.
