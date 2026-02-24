# Master Plan — Path to v1.0

## Date: 2026-02-24 | Current: v0.8 (EN ahead, translations at v0.6)

## Current State

| Category | Done | Total | % |
|----------|------|-------|---|
| Chapters | 23 | 23 | 100% |
| Chapter examples (.a80) | 29 | 29 | 100% |
| Appendices | 9 (A-I) | 9 (A-I) | 100% |
| Illustrations | 23 (14 PNG + 9 Mermaid/ASCII) | ~248 planned | 9% |
| Translations | 4 langs (at v0.6) | 4 langs | 100% (stale) |
| Spectools | 5 | 6 | 83% |
| Glossary | 95 terms | 95 terms | 100% |
| Words (EN) | ~180K | — | — |

## Completed

### Phase 1: Foundation — DONE (v0.7)
- Q1: Appendix D (dev environment setup) — DONE
- Q2: Ch21-23 assembly examples — DONE (28 pass)
- ~~Q4: MinZ test integration~~ — DEFERRED (oisee/minz issues #11-13)

### Phase 2: Visual Polish + eZ80 + Appendices — DONE (v0.7)
- Q3: Batch A illustrations (9 Mermaid/ASCII diagrams) — DONE
- Q5: Appendix E (eZ80 reference, 332 lines) — DONE
- Appendix F (Z80 variants: Z80N, R800, Soviet clones, 236 lines) — DONE
- Appendix H (Storage APIs: TR-DOS & esxDOS, 503 lines) — DONE
- Figure tagging (`<!-- figure: -->`) — DONE (23 total figures)

### Phase 3: Depth & Quality — DONE (v0.8)
- M1: Expand thin chapters — DONE
  - ch07 (rotozoomer): 2657 → 5745 words. Variants (monochrome/chunky/attribute), SMC detail, texture design
  - ch10 (scroller): 2712 → 4902 words. POP deep dive, Lissajous, 4-phase colour, demoscene lineage
  - ch13 (sizecoding): 3260 → 8552 words. Toolkit, 4K intros (GOA4K/inal/Megademica), AY bytebeat, procedural GFX
- Appendix I (Bytebeat & AY-Beat, 1107 lines) — DONE
  - Formula cookbook, E+T drone, music theory (scales, arpeggios, ornaments, progressions)
  - L-system grammars, tribonacci, melody-as-motion, PRNG with curated seeds
- `aybeat.a80` example (320 bytes, 3-channel generative music) — DONE
- CHANGELOG.md (human-language, appended to book PDF) — DONE
- Credits fixed: GOA4K + Refresh → Exploder^XTM, SerzhSoft added

## Remaining — Phase 4: Polish & Release

### M-Wins (still open)

| # | Task | Impact | Effort |
|---|------|--------|--------|
| M2 | **Batch B+C illustrations** — 12 diagrams (compression, sprites, state machines) | Visual completeness | 6-8h |
| M3 | **z80-opcodes.json** + z80dasm.py (spectools disassembler) | Educational tool | 4-6h |
| M4 | **Demo expansion** — plasma, backface culling for "Antique Toy" | Stronger ch23 case study | 1-2 days |

### L-Wins (still open)

| # | Task | Impact | Effort |
|---|------|--------|--------|
| L2 | **Full illustration coverage** — Batch D screenshots + remaining diagrams | Professional look | 1-2 weeks |
| L3 | **Editing pass** — all 23 chapters + 9 appendices, consistency, flow, fact-check | Publication quality | 1-2 weeks |
| L4 | **Demo release** — "Antique Toy" with 5+ effects, music, demoparty release | Proof of concept | 2-4 weeks |

### New items

| # | Task | Impact | Effort |
|---|------|--------|--------|
| N1 | **Listing inclusion** — embed .a80 source into chapter .md via include mechanism | Single source of truth for code | 2-4h |
| N2 | **Contended memory** — expand coverage across chapters (Eremus feedback) | Western European audience | 1-2 days |
| N3 | **Source references** — add zxdn.narod.ru, more direct links (RCL feedback) | Academic rigour | 2-3h |
| N4 | **Translation sync** — retranslate stale ES/RU/UK chapters to v0.8 level | Multi-language completeness | 3-5 days |

### Tag v1.0 after L3 (editing pass)

## MinZ Toolchain — DEFERRED

Tools at `~/dev/minz-ts` (v0.18.0-dev, Go, zero deps) are excluded from the book until reliability issues are resolved:

- **mze** `--cycles` reports 0 T-states → [oisee/minz#11](https://github.com/oisee/minz/issues/11)
- **mzd** lacks `--show-cycles` flag → [oisee/minz#12](https://github.com/oisee/minz/issues/12)
- **mze** needs exit code / assertion support → [oisee/minz#13](https://github.com/oisee/minz/issues/13)

Once issues are resolved, re-evaluate Q4 (test-run), M5 (MinZ appendix), and L5 (test suite).

## Feedback-driven items

| Source | Request | Priority | Status |
|--------|---------|----------|--------|
| Eremus | Contended memory coverage (48K/128K ULA timing) | High | TODO → N2 |
| Eremus | Reference Introspec's "Go West" articles | Medium | TODO → N2 |
| RCL | More direct links to source materials | Medium | TODO → N3 |
| RCL | Reference zxdn.narod.ru/coding.htm | Low | TODO → N3 |
| RCL | Platform-specific optimization (DOWN_HL, RST, stack) | Done | README per-chapter platform tags |

## Notes
- No TODO/FIXME markers in any chapter
- All 29 sjasmplus examples pass (29/29)
- All figures tagged with `<!-- figure: chNN_name -->` for greppability
- Translation manifest system tracks staleness for future EN edits
- EN is primary; translations catch up periodically
- Build: `python3 build_book.py --lang {en,es,ru,uk} --all`
- CHANGELOG.md auto-appended to EN book builds
