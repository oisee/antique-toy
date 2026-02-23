# Project Status — 2026-02-23

## The Big Numbers

| Asset | Done | Planned | % |
|-------|------|---------|---|
| Chapters | **23/23** | 23 | 100% |
| Words | **128K** | ~150K target | ~85% |
| Appendices | **4/8** | A,B,C,D,E,F,G,H | 50% |
| Assembly examples (.a80) | **25** pass | ~40 target | 63% |
| Illustrations | **14/248** | 248 | 6% |
| JS/HTML prototypes | **5** | ~10 | 50% |
| Spectools CLI | **5/6** | 6 | 83% |
| Demo ("Antique Toy") | **4 files** | expandable | MVP done |
| Book builds | **PDF A4/A5 + EPUB** | working | 100% |
| Releases | **v0.5** | v1.0 | — |

## Current Build

- English: v0.1-b7 (20260223)
- A4 PDF: 3.9 MB
- A5 PDF: 4.0 MB
- EPUB: 3.0 MB

## Chapters by Word Count

| Chapter | Words | Notes |
|---------|-------|-------|
| ch01-thinking-in-cycles | 4,088 | |
| ch02-screen-as-puzzle | 7,314 | |
| ch03-demoscene-toolbox | 3,549 | thin |
| ch04-maths | 5,997 | |
| ch05-3d | 5,017 | |
| ch06-sphere | 3,478 | thin |
| ch07-rotozoomer | 2,657 | thin — needs expansion |
| ch08-multicolor | 5,327 | |
| ch09-tunnels | 3,596 | |
| ch10-scroller | 2,712 | thin — needs expansion |
| ch11-sound | 6,565 | |
| ch12-music-sync | 5,878 | |
| ch13-sizecoding | 3,260 | thin — needs expansion |
| ch14-compression | 3,396 | thin |
| ch15-anatomy | 6,560 | |
| ch16-sprites | 7,021 | |
| ch17-scrolling | 7,018 | |
| ch18-gameloop | 9,219 | |
| ch19-collisions | 6,954 | |
| ch20-demo-workflow | 6,145 | |
| ch21-full-game | 9,735 | longest |
| ch22-porting-agon | 6,610 | |
| ch23-ai-assisted | 6,199 | |
| **TOTAL** | **128,295** | |

## Appendices

| Appendix | Status | Words |
|----------|--------|-------|
| A — Z80 Reference | done | 5,354 |
| B — Sine Tables | done | 3,504 |
| C — Compression | done | 2,678 |
| D — Dev Environment | **not started** | — |
| E — Agon Quick-Ref | **not started** | — |
| F — ZX Memory Map | **not started** | — |
| G — AY Registers | done | 7,434 |
| H — Resources | **not started** | — |

## Illustrations

14/248 done (6%). All 14 embedded in chapters.

| Chapter | Illustrations | Count |
|---------|--------------|-------|
| ch01 | tstate_costs, frame_budget | 2 |
| ch02 | screen_layout, attr_byte | 2 |
| ch04 | multiply_walkthrough | 1 |
| ch05 | 3d_pipeline | 1 |
| ch11 | ay_registers, envelope_shapes, just_intonation, te_alignment | 4 |
| ch15 | memory_map | 1 |
| ch16 | sprite_methods | 1 |
| ch17 | scroll_costs | 1 |
| ch18 | game_loop | 1 |

Next batch: see `_in/tasks/illustration-status.md` (9 Batch A charts, 12 Batch B+C diagrams, 5 Batch D screenshots).

## Spectools CLI

| Tool | Lines | Status |
|------|-------|--------|
| notetable.py | 400 | done |
| sinetable.py | 1,126 | done |
| tstate.py | 1,097 | done |
| scrview.py | 741 | done |
| autodiver.py | 481 | done |
| z80dasm.py | — | not started (needs z80-opcodes.json) |

## Translations

| Language | Status |
|----------|--------|
| English (source) | active, b7 |
| Spanish (es) | not started |
| Russian (ru) | not started |
| Ukrainian (uk) | not started |

Strategy: translate at milestone builds (every ~10 versions or major releases).

---

## Win Categories

### Q-wins (Quick — 1-2 hours each, high impact)

| # | Win | Impact | Effort |
|---|-----|--------|--------|
| Q1 | Batch A illustrations (9 charts) | wall-of-text → visual | low, parallel |
| Q2 | Appendices D,E,F,H | book feels complete | low, factual |
| Q3 | z80dasm.py (last CLI tool) | completes toolkit | medium |
| Q4 | Expand thin chapters (ch07, ch10, ch13) | even reading experience | low per chapter |
| Q5 | CHANGELOG.md | release tracking | trivial |

### M-wins (Medium — 1 day each, structural)

| # | Win | Impact | Effort |
|---|-----|--------|--------|
| M1 | Batch B+C illustrations (12 diagrams) | major visual upgrade | medium, parallel |
| M2 | Editing pass (23 chapters) | quality jump | medium-high |
| M3 | z80-opcodes.json | foundation for tools + emulator | medium |
| M4 | Translation vocabulary (ES/RU/UK) | unblocks translations | medium |
| M5 | More .a80 examples (+15) | compilable code coverage | medium, parallel |
| M6 | Index / cross-reference pass | navigation | medium |

### L-wins (Long — multi-day, strategic)

| # | Win | Impact | Effort |
|---|-----|--------|--------|
| L1 | Batch D illustrations (screenshots) | visual proof | needs emulator |
| L2 | Spectre emulator (Pillar 2) | killer differentiator | weeks |
| L3 | Web tools (Pillar 3) | reader engagement | week+ |
| L4 | Full translations (ES/RU/UK) | 3x audience | months |
| L5 | Demo expansion | proves thesis | week |
| L6 | Print preparation | physical book | week+ |
