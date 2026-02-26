# Coding the Impossible

**Z80 Demoscene Techniques for Modern Makers**

> **!!! UNDER CONSTRUCTION !!!**
>
> This book is a work in progress. Content is incomplete, may contain errors,
> and is subject to change without notice.
>
> **How this book is written:**
> 1. With assistance from LLM (Claude Opus 4.6) based on open publications and data
> 2. By Alice directly — where personal expertise is "good enough" or no available sources or in new areas
> 3. Corrections and contributions on topic are welcome — PRs open

**TL;DR:** 23 chapters + 9 appendices, ~184K words, 29 compilable examples, 4 languages. You know Z80 -- this book shows you *why* the tricks work, not *what* the registers are. [Download PDF](https://github.com/oisee/antique-toy/releases/download/v0.8/book-a4-v0.8.pdf)

This book lives on the **ZX Spectrum**. Most techniques -- DOWN_HL, attribute tricks, ULA timing, 128K bank juggling -- only make sense on this machine. That's where the demoscene is, and that's where the hard problems are.

The foundation (T-state budgets, fixed-point maths, compression, algorithms) is pure Z80 and works on any platform. One chapter takes the whole game to **eZ80/Agon Light 2** (~$50 on Olimex) to show how the same instruction set drives a completely different machine.

Not a beginner tutorial, not a reference manual. A cookbook for those who already know Z80 and want to understand *why* the tricks work.

## How to read this book

Chapter 1 (T-state budgets) is the foundation -- read it first. Everything after that can be read in any order, like a recipe book. Linear "here are registers, here are instructions" exposition is the "car manual from the glovebox" experience. If you already know Z80, you don't need that.

## Download

**[Latest release](https://github.com/oisee/antique-toy/releases/latest)** -- PDF (A4, A5) and EPUB in four languages:

| Language | Version | PDF | Words |
|----------|---------|-----|-------|
| English | **v0.8** | [book-a4-v0.8.pdf](https://github.com/oisee/antique-toy/releases/download/v0.8/book-a4-v0.8.pdf) | ~180K |
| Spanish | v0.6 | [book-a4_ES-v0.6.pdf](https://github.com/oisee/antique-toy/releases/download/v0.6/book-a4_ES-v0.6.pdf) | ~165K |
| Russian | v0.6 | [book-a4_RU-v0.6.pdf](https://github.com/oisee/antique-toy/releases/download/v0.6/book-a4_RU-v0.6.pdf) | ~140K |
| Ukrainian | v0.6 | [book-a4_UK-v0.6.pdf](https://github.com/oisee/antique-toy/releases/download/v0.6/book-a4_UK-v0.6.pdf) | ~142K |

English is the primary edition and always ahead. Translations catch up periodically, every few releases.

## Contents

23 chapters + 9 appendices, ~184K words (English), 29 compilable assembly examples.

Platform tags: **Z80** = pure Z80, any platform. **ZX** = ZX Spectrum specific. **eZ80** = Agon Light 2.

| # | Chapter | Platform |
|---|---------|----------|
| 1 | Thinking in Cycles (T-state budgets) | **Z80** |
| 2 | The Screen as a Puzzle (ULA layout, attributes) | ZX |
| 3 | Demoscene Toolbox (PUSH fill, LDI chains, SMC) | **Z80** / ZX |
| 4 | The Maths You Actually Need (multiply, PRNG, fixed-point) | **Z80** |
| 5 | 3D on 3.5 MHz (wireframe, rotation matrices) | **Z80** |
| 6 | The Sphere (texture mapping, skip tables) | **Z80** / ZX |
| 7 | Rotozoomer (chunky pixels, SMC inner loop) | ZX |
| 8 | Multicolor (beam racing, per-scanline colour) | ZX |
| 9 | Attribute Tunnels and Chaos Zoomers | ZX |
| 10 | Dotfield Scroller and 4-Phase Colour | ZX |
| 11 | Sound Architecture (AY, TurboSound, Triple AY) | ZX |
| 12 | Digital Drums and Music Sync | ZX |
| 13 | The Craft of Size-Coding | **Z80** / ZX |
| 14 | Compression (ZX0, Exomizer, LZ4, pre-compression transforms, decision tree) | **Z80** |
| 15 | Anatomy of Two Machines (128K banking, ports) | ZX |
| 16 | Fast Sprites (OR/AND, compiled, masking) | ZX |
| 17 | Scrolling (pixel, tile, hardware tricks) | ZX |
| 18 | Game Loop and Entity System | **Z80** / ZX |
| 19 | Collisions, Physics, and Enemy AI | **Z80** |
| 20 | Demo Workflow (idea to compo release) | ZX |
| 21 | Full Game -- ZX Spectrum 128K | ZX |
| 22 | Porting to Agon Light 2 (ADL mode, VDP, MOS) | **eZ80** |
| 23 | AI-Assisted Z80 Development | **Z80** |

### Appendices

| Appendix | Status | Content |
|----------|--------|---------|
| A: Z80 Instruction Reference | Done | Timing tables, fast instructions, undocumented ops, flag cheat sheet |
| B: Sine Table Generation | Done | 7 approaches compared (full table to Bhaskara I), decision tree |
| C: Compression Quick Reference | Done | 14 compressors compared, decision tree, decompressor code |
| D: Development Environment | Done | sjasmplus, VS Code, DeZog, ZEsarUX/Fuse setup |
| E: eZ80 Reference | Done | ADL mode, MLT/LEA/PEA/TST, Agon Light 2 specifics, porting checklist |
| F: Z80 Variants | Done | Z80N (Next), R800 (MSX turboR), eZ80 summary, Soviet clones, comparison table |
| G: AY-3-8910 Register Reference | Done | Full register map, note table, TurboSound, envelope shapes |
| H: Storage APIs | Done | TR-DOS (Beta Disk 128) and esxDOS (DivMMC) — ports, ROM API, code examples |
| I: Bytebeat & AY-Beat | Done | Classic bytebeat, AY-beat engine, formula cookbook, music theory (scales, arpeggios, L-grammars), procedural sound |

## Building the book

Requires [Pandoc](https://pandoc.org/) and LuaLaTeX (TeX Live).

```sh
python3 build_book.py --pdf            # A4 PDF (English)
python3 build_book.py --all            # PDF A4 + A5 + EPUB
python3 build_book.py --lang es --all  # Spanish edition
python3 build_book.py --lang ru --all  # Russian edition
python3 build_book.py --lang uk --all  # Ukrainian edition
```

Or via Makefile shortcuts:

```sh
make book       # English, all formats
make book-a4    # English A4 PDF only
```

## Building the code examples

Requires [sjasmplus](https://github.com/z00m128/sjasmplus) (pinned as submodule in `tools/sjasmplus/`).

```sh
git clone --recursive https://github.com/oisee/antique-toy.git
cd antique-toy
make            # compile all 28 examples
make test       # assemble all, report pass/fail
make demo       # build the "Antique Toy" demo
```

### Examples by chapter

| Ch | Example | Technique |
|----|---------|-----------|
| 01 | `timing_harness.a80` | Border-colour cycle counting |
| 02 | `fill_screen.a80`, `pixel_demo.a80` | Screen memory, pixel plotting |
| 03 | `push_fill.a80` | PUSH-based fast screen fill |
| 04 | `multiply8.a80`, `prng.a80` | Shift-and-add multiply, PRNG |
| 05 | `wireframe_cube.a80` | 3D wireframe with rotation |
| 06 | `sphere.a80` | Sphere rendering with skip tables |
| 07 | `rotozoomer.a80` | Texture rotation with SMC patching |
| 08 | `multicolor.a80`, `multicolor_dualscreen.a80` | Beam-racing per-scanline colour |
| 09 | `plasma.a80` | Attribute-based plasma effect |
| 10 | `dotscroll.a80` | POP-trick bouncing dotfield |
| 11 | `ay_test.a80` | AY-3-8910 tone generation |
| 12 | `music_sync.a80` | Timeline sync + digital drums |
| 13 | `intro256.a80`, `aybeat.a80` | 256-byte intro skeleton, AY-beat generative music |
| 14 | `decompress.a80` | LZ77 decompressor |
| 15 | `bank_inspect.a80` | 128K memory bank inspector |
| 16 | `sprite_demo.a80` | Sprite rendering methods |
| 17 | `hscroll.a80` | Horizontal pixel scroller |
| 18 | `game_skeleton.a80` | Game loop + entity system |
| 19 | `aabb_test.a80` | AABB collision detection |
| 20 | `demo_framework.a80` | Scene table demo engine |
| 21 | `game_skeleton.a80` | 128K game: state machine, bank switching, entity loop |
| 22 | `agon_entity.a80` | Agon Light 2 porting patterns |
| 23 | `diagonal_fill.a80` | AI-assisted: naive vs optimised fill |

## Contributing

The book is about Z80 as a processor, not just ZX Spectrum as a platform. If you have materials on other Z80 machines -- Amstrad CPC, MSX, ZX Next, Robotron KC85, or anything else with a Z80 inside -- PRs are welcome. Clone the repo, add your chapter or appendix, rebuild the book.

Translations are managed via `translations/manifest.py` (SHA256-based staleness tracking). See `translations/PROGRESS.md` for details.

## Companion projects

### Antique Toy (demo)

An AI-assisted multi-effect ZX Spectrum demo in `demo/src/`. Currently includes a wireframe torus with real-time rotation. More effects planned (plasma, backface culling).

### Clockwork (demo toolchain)

[Clockwork](https://github.com/oisee/clockwork) is the companion toolchain for ZX Spectrum demo production. It connects the book's theory to practical demo-making workflow: timeline editing, music sync, memory budgeting, and asset pipeline management. The `--json` output from `tools/packbench.py` feeds directly into Clockwork's memory planner.

### Tools

The `tools/` directory contains Python utilities developed alongside the book:

| Tool | Purpose |
|------|---------|
| `packbench.py` | Packer benchmark, memory budget, streaming decompression estimator, pre-compression data analysis |
| `screenshots.py` | Automated screenshot generation for book illustrations (28 examples, headless emulator) |
| `manage_listings.py` | Code listing extraction, injection, and verification across chapters |
| `audit_tstates.py` | T-state annotation auditor — compares inline comments with computed cycle counts |
| `autotag.py` | Semi-automatic code block classifier and tagger |

## License

[CC BY-NC 4.0](LICENSE.md) -- free for non-commercial use, attribution required.

(c) 2025-2026 Alice Vinogradova
