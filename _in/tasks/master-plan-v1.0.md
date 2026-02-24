# Master Plan — Path to v1.0

## Date: 2026-02-24 | Current: v0.7 (EN ahead, translations at v0.6)

## Current State

| Category | Done | Total | % |
|----------|------|-------|---|
| Chapters | 23 | 23 | 100% |
| Chapter examples (.a80) | 28 | 28 | 100% |
| Appendices | 8 (A-H) | 8 (A-H) | 100% |
| Illustrations | 23 (14 PNG + 9 Mermaid/ASCII) | ~248 planned | 9% |
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
| ~~L1~~ | ~~**Appendices F, H** — Z80 variants, Storage APIs (TR-DOS & esxDOS)~~ | DONE — moved to Phase 2 | — |
| L2 | **Full illustration coverage** — Batch D screenshots + remaining diagrams | Professional look | 1-2 weeks |
| L3 | **Editing pass** — all 23 chapters, consistency, flow, fact-check | Publication quality | 1-2 weeks |
| L4 | **Demo release** — "Antique Toy" with 5+ effects, music, release at demoparty | Proof of concept | 2-4 weeks |
| ~~L5~~ | ~~**mze-based test suite** — run every example, validate screen output, regression CI~~ | DEFERRED — blocked by mze issues #11, #13 | — |

## Recommended Phases

### Phase 1: Foundation — DONE
- Q1: Appendix D (dev environment setup) — DONE
- Q2: Ch21-23 assembly examples — DONE (28/28 pass, 0 fail)
- ~~Q4: MinZ test integration~~ — DEFERRED (oisee/minz issues #11-13)

### Phase 2: Visual Polish + eZ80 + Appendices — DONE
- Q3: Batch A illustrations (9 Mermaid/ASCII diagrams) — DONE (23 total figures)
- Q5: Appendix E (eZ80 reference, 332 lines) — DONE
- L1: Appendix F (Z80 variants: Z80N, R800, Soviet clones, 236 lines) — DONE
- L1: Appendix H (Storage APIs: TR-DOS & esxDOS, 503 lines) — DONE
- Figure tagging (`<!-- figure: -->`) — DONE (14 existing PNG + 9 new diagrams tagged)

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

## Feedback-driven items

| Source | Request | Priority | Status |
|--------|---------|----------|--------|
| Eremus | Contended memory coverage (48K/128K ULA timing) | High | TODO — affects multiple chapters |
| Eremus | Reference Introspec's "Go West" articles | Medium | TODO |
| RCL | More direct links to source materials | Medium | TODO |
| RCL | Reference zxdn.narod.ru/coding.htm | Low | Noted |
| RCL | Platform-specific optimization (DOWN_HL, RST, stack) | Done | README now has per-chapter platform tags |

## Notes
- No TODO/FIXME markers in any chapter
- All 28 sjasmplus examples pass
- All figures tagged with `<!-- figure: chNN_name -->` for greppability
- Translation manifest system tracks staleness for future EN edits
- EN is primary; translations catch up periodically
- Build: `python3 build_book.py --lang {en,es,ru,uk} --all`
