# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Working repository for **"Coding the Impossible: Z80 Demoscene Techniques for Modern Makers"** — a book about Z80/eZ80 assembly on ZX Spectrum and Agon Light 2, with deep focus on demoscene techniques. Companion demo project ("Not Eager") included.

**Merged outline:** `book-outline.md` (23 chapters + 8 appendices, 2 platforms: ZX Spectrum 128K + Agon Light 2). NEO6502/65C02 dropped for now.

## Repository Structure

```
book-outline.md          # THE master plan (v2, merged from both earlier outlines)
Makefile                 # Builds all chapter examples with mza
chapters/
  ch01-thinking-in-cycles/
    draft.md             # Chapter prose
    examples/*.a80       # Compilable Z80 assembly
  ch02-screen-as-puzzle/
  ...ch23-ai-assisted/
demo/                    # "Not Eager" companion demo project
  README.md
  src/                   # Demo Z80 source (WIP)
_in/                     # Input materials, research, raw sources
  raw/                   # ZIP archives of ZX Spectrum demos
  tasks/                 # Task lists, earlier outlines, dialogues
  articles/              # Fetched articles and extracted NFO/DIZ
    extracted/           # Per-demo NFO/DIZ from ZIP archives
    hype_article_catalog.md
    hype_article_summaries.md
    zxart_press_catalog.md
    spectrum_expert_articles.md
build/                   # Compiled output (gitignored)
```

## Build System

```sh
make              # compile all examples with mza
make test         # assemble all, report pass/fail
make ch01         # compile just chapter 1 examples
make clean        # remove build artifacts
```

**Primary assembler:** `mza` (MinZ Z80 Assembler) — we develop it at `../minz-ts/`. Aliased as `mza` in shell. Supports `--target zxspectrum`, `--target agon`.

**Secondary:** `sjasmplus` at `~/dev/bin/sjasmplus` (v1.07 RC8, old — needs upgrade for full compatibility). Examples should compile on both where possible.

## Key Context

- Two target platforms: **ZX Spectrum 128K** (primary, all demoscene + game dev) and **Agon Light 2** (eZ80, game dev chapters + porting)
- Sound focus: **AY-3-8910 → TurboSound (2×AY) → Triple AY (Next)**. Beeper is sidebar only.
- Core narrative: Dark/X-Trade wrote algorithms (SE#01-02, 1997-98) AND coded Illusion. Introspec reverse-engineered Illusion on Hype in 2017. Both sides available.
- "Not Eager" demo: AI-assisted demo project to prove Claude Code can help with real Z80 demoscene work. Response to Introspec's skepticism.
- Source materials include closed/private code (Eager source from Introspec) — respect permissions.
- The author (Alice) is active in the ZX Spectrum demoscene community with direct contacts (Introspec, psndcj/sq, 4D, Screamer).

## Assembly Code Conventions

- Use `.a80` extension for Z80 assembly files
- ORG $8000 for ZX Spectrum examples (above screen memory)
- Use mza syntax: `$FF` for hex, `%10101010` for binary, `.label` for local labels
- Comments explain cycle counts where relevant: `; 11 T` or `; 196-204 T-states`
- Examples must compile with `mza --target zxspectrum`

## Languages

Project is bilingual. Planning documents and conversations primarily in Russian. Chapter drafts in English. Preserve original language of source quotes.
