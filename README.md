# Coding the Impossible

**Z80 Demoscene Techniques for Modern Makers**

**TL;DR:** 23 chapters, ~128K words, 28 compilable examples, 4 languages. You know Z80 -- this book shows you *why* the tricks work, not *what* the registers are. [Download PDF](https://github.com/oisee/antique-toy/releases/download/v0.7/book-a4-v0.7.pdf)

A book about Z80 optimization for those who already know the processor and want to understand *why* certain techniques work the way they do. Not a beginner tutorial, not a platform manual -- a cookbook of hard-won tricks from the demoscene, with cycle counts and working code.

The book covers ZX Spectrum 128K as the primary platform, with eZ80/Agon Light 2 as a modern counterpoint. Agon is the most powerful and actually purchasable (~$50 on Olimex) descendant of Z80 -- architecturally closer to BBC Micro than to Spectrum, showing how the same instruction set can drive a completely different machine.

## How to read this book

Chapter 1 (T-state budgets) is the foundation -- read it first. Everything after that can be read in any order, like a recipe book. This is deliberate: linear "here are registers, here are instructions" exposition is the path to the "car manual from the glovebox" feeling. If you already know Z80, you don't need that.

## Download

**[Latest release](https://github.com/oisee/antique-toy/releases/latest)** -- PDF (A4, A5) and EPUB in four languages:

| Language | Version | PDF | Words |
|----------|---------|-----|-------|
| English | **v0.7** | [book-a4-v0.7.pdf](https://github.com/oisee/antique-toy/releases/download/v0.7/book-a4-v0.7.pdf) | ~128K |
| Spanish | v0.6 | [book-a4_ES-v0.6.pdf](https://github.com/oisee/antique-toy/releases/download/v0.6/book-a4_ES-v0.6.pdf) | ~165K |
| Russian | v0.6 | [book-a4_RU-v0.6.pdf](https://github.com/oisee/antique-toy/releases/download/v0.6/book-a4_RU-v0.6.pdf) | ~140K |
| Ukrainian | v0.6 | [book-a4_UK-v0.6.pdf](https://github.com/oisee/antique-toy/releases/download/v0.6/book-a4_UK-v0.6.pdf) | ~142K |

English is the primary edition and always ahead. Translations catch up periodically, every few releases.

## Contents

23 chapters, ~128K words (English), 28 compilable assembly examples.

| Part | Chapters | Topic |
|------|----------|-------|
| I: Foundations | 1-4 | T-state budgets, screen layout, demoscene toolbox, fast maths |
| II: Demoscene | 5-14 | Wireframe 3D, sphere, rotozoomer, multicolor, plasma tunnels, scrollers, AY sound, music sync, sizecoding, compression |
| III: Game Dev | 15-22 | 128K hardware, sprites, scrolling, game loop, collisions, demo workflow, full 128K game, porting to Agon Light 2 |
| IV: Meta | 23 | AI-assisted Z80 development |

### Appendices

| Appendix | Status | Content |
|----------|--------|---------|
| A: Z80 Instruction Reference | Done | Timing tables, fast instructions, undocumented ops, flag cheat sheet |
| B: Sine Table Generation | Done | 7 approaches compared (full table to Bhaskara I), decision tree |
| C: Compression Quick Reference | Done | 14 compressors compared, decision tree, decompressor code |
| D: Development Environment | Done | sjasmplus, VS Code, DeZog, ZEsarUX/Fuse setup |
| E: eZ80 Reference | Planned | ADL mode, new instructions, MOS API |
| F: Memory Maps | Planned | Spectrum 128K, Pentagon, clone variants |
| G: AY-3-8910 Register Reference | Done | Full register map, note table, TurboSound, envelope shapes |
| H: esxDOS/DivMMC API | Planned | File I/O for modern storage |

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
| 13 | `intro256.a80` | 256-byte intro skeleton |
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

## Companion demo

"Antique Toy" -- an AI-assisted multi-effect ZX Spectrum demo in `demo/src/`. Currently includes a wireframe torus with real-time rotation. More effects planned (plasma, backface culling).

## License

[CC BY-NC 4.0](LICENSE.md) -- free for non-commercial use, attribution required.

(c) 2025-2026 Alice Vinogradova
