# Master Plan — Path to v1.0

## Date: 2026-02-24 | Current: v0.6 (all translations done)

## Current State

| Category | Done | Total | % |
|----------|------|-------|---|
| Chapters | 23 | 23 | 100% |
| Chapter examples (.a80) | 23 | 23 | 100% |
| Appendices | 5 (A,B,C,D,G) | 8 (A-H) | 63% |
| Illustrations | 14 | ~248 planned | 6% |
| Translations | 4 langs | 4 langs | 100% |
| Spectools | 5 | 6 | 83% |
| Glossary | 95 terms | 95 terms | 100% |

## Q-Wins (Quick, < 1 day each)

| # | Task | Impact | Effort |
|---|------|--------|--------|
| Q1 | **Appendix D** — Dev Environment Setup (VS Code, sjasmplus, DeZog, emulators) | Unblocks newcomers | 1-2h |
| Q2 | **Ch21-23 examples** — skeleton .a80 for game, Agon port, AI-assisted | Makes integration chapters practical | 2-4h |
| Q3 | **Batch A illustrations** — 9 charts (cost comparisons, memory layouts, pipelines) | Breaks wall-of-text | 4-6h |
| ~~Q4~~ | ~~**MinZ integration** — `make test-run` via `mze`, validate T-states via `mzd --show-cycles`~~ | DEFERRED — mze/mzd not ready (issues #11-13) | — |
| Q5 | **Appendix E** — eZ80 Quick Reference (ADL mode, LEA/MLT/TST, MOS API) | Supports ch22 | 2-3h |

## M-Wins (Medium, 1-3 days)

| # | Task | Impact | Effort |
|---|------|--------|--------|
| M1 | **Expand thin chapters** (ch07, ch10, ch13) +1-2K words each | Better depth consistency | 3-4h |
| M2 | **Batch B+C illustrations** — 12 diagrams (compression, sprites, state machines) | Visual completeness for key chapters | 6-8h |
| M3 | **z80-opcodes.json** + z80dasm.py (spectools disassembler) | Educational tool, could replace mzd for simple cases | 4-6h |
| M4 | **Demo expansion** — add plasma effect, backface culling to "Antique Toy" | Stronger ch23 case study | 1-2 days |
| ~~M5~~ | ~~**MinZ appendix/chapter** — "MinZ: A Modern Language for Z80" showcasing mz compiler~~ | DEFERRED — tools not mature enough | — |

## L-Wins (Longer, 1+ week)

| # | Task | Impact | Effort |
|---|------|--------|--------|
| L1 | **Appendices F, H** — Clone memory maps, esxDOS API reference | Completeness for power users | 2-3h each |
| L2 | **Full illustration coverage** — Batch D screenshots + remaining diagrams | Professional look | 1-2 weeks |
| L3 | **Editing pass** — all 23 chapters, consistency, flow, fact-check | Publication quality | 1-2 weeks |
| L4 | **Demo release** — "Antique Toy" with 5+ effects, music, release at demoparty | Proof of concept | 2-4 weeks |
| ~~L5~~ | ~~**mze-based test suite** — run every example, validate screen output, regression CI~~ | DEFERRED — blocked by mze issues #11, #13 | — |

## Recommended Phases

### Phase 1: Foundation — DONE
- Q1: Appendix D (dev environment setup) — DONE
- Q2: Ch21-23 assembly examples — DONE (28/28 pass, 0 fail)
- ~~Q4: MinZ test integration~~ — DEFERRED (oisee/minz issues #11-13)

### Phase 2: Visual Polish
- Q3: Batch A illustrations (9 charts)
- Q5: Appendix E (eZ80 reference)

### Phase 3: Depth & Quality
- M1: Expand thin chapters (ch07, ch10, ch13)
- M2: Batch B+C illustrations (12 diagrams)

### Tag v1.0 after Phase 2 or 3

## MinZ Toolchain — DEFERRED

Tools at `~/dev/minz-ts` (v0.18.0-dev, Go, zero deps) are excluded from the book until reliability issues are resolved:

- **mze** `--cycles` reports 0 T-states → [oisee/minz#11](https://github.com/oisee/minz/issues/11)
- **mzd** lacks `--show-cycles` flag → [oisee/minz#12](https://github.com/oisee/minz/issues/12)
- **mze** needs exit code / assertion support → [oisee/minz#13](https://github.com/oisee/minz/issues/13)

Once issues are resolved, re-evaluate Q4 (test-run), M5 (MinZ appendix), and L5 (test suite).

## Notes
- No TODO/FIXME markers in any chapter
- All 25 sjasmplus examples pass (14/25 mza — expected)
- All 14 illustration image links valid
- Translation manifest system tracks staleness for future EN edits
- Build: `python3 build_book.py --lang {en,es,ru,uk} --all`
