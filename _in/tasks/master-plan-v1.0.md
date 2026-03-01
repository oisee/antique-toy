# Master Plan — Path to v1.0

## Date: 2026-03-01 | Current: v20 (EN + RU synced, ES/UK at v0.6)

## Current State

| Category | Done | Total | % |
|----------|------|-------|---|
| Chapters | 23 | 23 | 100% |
| Chapter examples (.a80) | 31 | 31 | 100% |
| Appendices | 10 (A-J) | 10 (A-J) | 100% |
| Illustrations | 28 (22 screenshots + 9 Mermaid/ASCII) | ~248 planned | 11% |
| Translation RU | 34/34 at v20 | 34 items | 100% (current) |
| Translation ES | 28/34 at v0.6 | 34 items | stale |
| Translation UK | 28/34 at v0.6 | 34 items | stale |
| Spectools | 5 | 6 | 83% |
| Glossary | 161 terms | 161 terms | 100% |
| Words (EN) | ~200K | — | — |
| Screenshot pipeline | 22 auto / 7 skip | 29 configured | 76% |
| Translation Memory | tm.py + tm.json | 3,977 segments | operational |

## Completed Phases

### Phase 1: Foundation — DONE (v0.7)
- All 23 chapters drafted, all examples compile
- Appendix D (dev setup) through Appendix I (bytebeat)

### Phase 2: Visual Polish + eZ80 — DONE (v0.7–v0.8)
- Batch A illustrations, figure tagging, eZ80 reference
- Appendices E, F, H (eZ80, Z80 variants, storage APIs)

### Phase 3: Depth & Quality — DONE (v0.8–v10)
- ch07 (rotozoomer), ch10 (scroller), ch13 (sizecoding) expanded 2-3x
- Appendix I (Bytebeat), aybeat.a80 engine
- CHANGELOG, credits fixes, first numbered release

### Phase 4: Technical Depth — DONE (v11–v18)
- Ped7g feedback: signed multiply (Ch.4), RLE sidebar (Ch.14), Z80N T-states
- Screenshot pipeline (mzx headless, 22 automated screenshots)
- 12 assembly units compile, 5 JS/HTML prototypes
- Appendix J (modern tools: z80-optimizer, GNU Rocket, Furnace, TiXL, Blender)

### Phase 5: Translation + Community Feedback — DONE (v19–v20)
- Translation Memory tool (translations/tm.py) — 87% block reuse
- Russian: all 34 items updated to v20 (23 chapters + 10 appendices + glossary)
- 6 new appendices (D-J) translated from scratch
- Community feedback: AY history, PSG terminology, pixel row fix, RLE screenshot
- Acknowledgements section added (Ped7g, Introspec, Rombor, Aki, mborik)

## Remaining — Phase 6: Polish & Release

### High Priority (v1.0 blockers)

| # | Task | Impact | Effort |
|---|------|--------|--------|
| L3 | **Editing pass** — all 23 chapters + 10 appendices, consistency, flow, fact-check | Publication quality | 1-2 weeks |
| N4a | **ES/UK translation sync** — use TM tool to update ES/UK from v0.6 → current | Multi-language completeness | 2-3 days |
| IMP-1 | **Ch12 "frame-level markers"** — clarify n1k-o's GABBA sync workflow | Technical accuracy | Needs n1k-o input |

### Medium Priority (nice for v1.0)

| # | Task | Impact | Effort |
|---|------|--------|--------|
| M2 | **Batch B+C illustrations** — 12 diagrams (compression, sprites, state machines) | Visual completeness | 6-8h |
| N2 | **Contended memory** — expand coverage across chapters (Eremus feedback) | Western European audience | 1-2 days |
| N3 | **Source references** — add zxdn.narod.ru, more direct links (RCL feedback) | Academic rigour | 2-3h |
| M3 | **z80-opcodes.json** + z80dasm.py (spectools disassembler) | Educational tool | 4-6h |

### Low Priority (post-v1.0)

| # | Task | Impact | Effort |
|---|------|--------|--------|
| L2 | **Full illustration coverage** — remaining ~220 diagrams | Professional look | 2-4 weeks |
| L4 | **Demo release** — "Antique Toy" with 5+ effects, music, demoparty | Proof of concept | 2-4 weeks |
| N1 | **Listing inclusion** — embed .a80 source into chapter .md | Single source of truth | 2-4h |
| NEW-2 | **Constant-T VGM player** — mborik collaboration | New content | Depends on mborik |

### Human Actions (non-code)

| # | Action | Owner |
|---|--------|-------|
| COM-1 | Join SinDiKat Slack | Alice |
| COM-2 | Ask n1k-o about GABBA sync workflow | Alice |
| COM-3 | Follow up with mborik on VGM player | Alice |

### Tag v1.0 after L3 (editing pass)

## MinZ Toolchain — DEFERRED

Tools at `~/dev/minz-ts` are excluded until reliability issues are resolved:
- **mze** `--cycles` reports 0 T-states → [oisee/minz#11](https://github.com/oisee/minz/issues/11)
- **mzd** lacks `--show-cycles` flag → [oisee/minz#12](https://github.com/oisee/minz/issues/12)
- **mze** needs exit code / assertion support → [oisee/minz#13](https://github.com/oisee/minz/issues/13)

## Build & Release

- EN: `python3 build_book.py --all --lang en`
- RU: `python3 build_book.py --all --lang ru`
- Test: `make test` (31 pass), `make screenshots` (22 OK, 7 skip)
- TM workflow: `build → diff → export → translate → apply → stamp`
- Translation manifest: `python3 translations/manifest.py check all`

## Notes
- All 31 sjasmplus examples pass
- All figures tagged with `<!-- figure: chNN_name -->` for greppability
- RU translation fully synced to EN at v20
- ES/UK translations at v0.6 — TM ready, just need to run the pipeline
- Feedback log: `_in/tasks/feedback-2026-02-28.md` (all code items closed)
