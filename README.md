# Coding the Impossible

**Z80 Demoscene Techniques for Modern Makers**

A book about Z80/eZ80 assembly on ZX Spectrum and Agon Light 2, with deep focus on demoscene techniques. 23 chapters covering everything from T-state budgets and attribute plasma tunnels to wireframe 3D, digital drums, and full game development.

Companion demo project "Antique Toy" included -- an AI-assisted multi-effect ZX Spectrum demo.

## Current status

- **23/23 chapters drafted** (~124K words)
- **21 compilable .a80 examples** across chapters (23 total with demo)
- **4/8 appendices drafted** (A: Z80 reference, B: Sine tables, C: Compression, G: AY registers)
- **5 JS/HTML prototypes** in `verify/`
- **"Antique Toy" demo** -- wireframe torus working

### Chapter list

| Part | Chapters | Topic |
|------|----------|-------|
| I: Foundations | 1-4 | Cycles, screen layout, toolbox, maths |
| II: Demoscene | 5-14 | 3D, sphere, rotozoomer, multicolor, tunnels, scrollers, sound, music sync, sizecoding, compression |
| III: Game Dev | 15-22 | Hardware anatomy, sprites, scrolling, game loop, collisions, demo workflow, full game, porting |
| IV: Meta | 23 | AI-assisted development |

### Appendices

| Appendix | Status | Content |
|----------|--------|---------|
| A: Z80 Instruction Reference | Done | Timing tables, fast instructions, undocumented ops, flag cheat sheet |
| B: Sine Table Generation | Done | 7 approaches compared (full table → Bhaskara I), decision tree |
| C: Compression Quick Reference | Done | 14 compressors compared, decision tree, decompressor code |
| D: Development Environment | Planned | |
| E: eZ80 Reference | Planned | |
| F: Memory Maps | Planned | |
| G: AY-3-8910 Register Reference | Done | Full register map, note table, TurboSound, envelope shapes |
| H: DivMMC API | Planned | |

## Building the book

Requires [Pandoc](https://pandoc.org/) and LuaLaTeX (TeX Live).

```sh
make book-a4    # PDF, A4 format
make book-a5    # PDF, A5 format
make book-epub  # EPUB
make book       # all three
```

## Building the code examples

Requires [sjasmplus](https://github.com/z00m128/sjasmplus) (pinned as submodule in `tools/sjasmplus/`).

```sh
make            # compile all chapter examples
make test       # assemble all, report pass/fail (23 passing)
make demo       # build the "Antique Toy" demo
```

### Examples by chapter

| Chapter | Example | Technique |
|---------|---------|-----------|
| ch01 | `timing_harness.a80` | Border-colour cycle counting |
| ch02 | `fill_screen.a80`, `pixel_demo.a80` | Screen memory, pixel plotting |
| ch03 | `push_fill.a80` | PUSH-based fast screen fill |
| ch04 | `multiply8.a80` | Shift-and-add 8x8 multiply |
| ch05 | `wireframe_cube.a80` | 3D wireframe with rotation |
| ch06 | `sphere.a80` | Sphere rendering with skip tables |
| ch07 | `rotozoomer.a80` | Texture rotation with SMC patching |
| ch08 | `multicolor.a80` | Beam-racing per-scanline colour |
| ch09 | `plasma.a80` | Attribute-based plasma effect |
| ch10 | `dotscroll.a80` | POP-trick bouncing dotfield |
| ch11 | `ay_test.a80` | AY-3-8910 tone generation |
| ch12 | `music_sync.a80` | Timeline sync + digital drums |
| ch13 | `intro256.a80` | 256-byte intro skeleton |
| ch14 | `decompress.a80` | LZ77 decompressor |
| ch15 | `bank_inspect.a80` | 128K memory bank inspector |
| ch16 | `sprite_demo.a80` | Sprite rendering methods |
| ch17 | `hscroll.a80` | Horizontal pixel scroller |
| ch18 | `game_skeleton.a80` | Game loop + entity system |
| ch19 | `aabb_test.a80` | AABB collision detection |
| ch20 | `demo_framework.a80` | Scene table demo engine |

## Repository structure

```
book-outline.md              # Master plan (23 chapters + 8 appendices)
chapters/chNN-name/
  draft.md                   # Chapter prose
  examples/*.a80             # Compilable Z80 assembly
appendices/appendix-X-*.md   # Reference appendices
demo/src/                    # "Antique Toy" demo source
verify/                      # JS/HTML prototypes and analysis tools
_in/                         # Research materials and feedback
build/                       # Build output (gitignored)
```

## License

[CC BY-NC 4.0](LICENSE.md) -- free for non-commercial use, attribution required.

(c) 2025-2026 Alice Vinogradova. All rights reserved.
