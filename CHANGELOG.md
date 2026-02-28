# What's New

## v20 (2026-02-28)

**Russian translation updated to v20 + community feedback fixes.**

### Community feedback (Aki, Rombor via SinDiKat Slack)

**Ch11 (Sound Architecture):** AY history corrected -- Investronica first integrated the AY into the Spanish Spectrum 128K, Sinclair adopted it, Amstrad inherited it for +2/+3. Chip variant clarified: the Spectrum 128K uses the AY-3-8912 (fewer I/O ports), not the 8910. "Without a dedicated sound CPU" reworded to "without dedicating the CPU to sound generation."

**Ch12 (Music & Sync):** "synthesiser" corrected to "PSG (Programmable Sound Generator)" for consistency with Ch11.

**Ch02 illustration:** Pixel row 109 → 107 in `ch02_screen_layout.png` (reported by Rombor). Address bits were correct, only the final row number was wrong: 64 + 5×8 + 3 = 107.

Full feedback log: `_in/tasks/feedback-2026-02-28.md`

### Translation Memory tool + Russian edition

Built `translations/tm.py` -- a paragraph-level Translation Memory system that aligns v0.6 EN with existing translations, diffs current EN at block level, and exports only the delta for LLM translation. The tool found that **87% of blocks were unchanged** since v0.6, so only 13% needed retranslation (~89% cost savings).

**How it worked:**
1. `tm.py build` segmented all 28 items at git tag v0.6, aligned EN blocks with RU/ES/UK translations positionally, stored in `tm.json` (3,976 segments)
2. `tm.py diff ru` classified each block as EQUAL (87%), MODIFIED (4%), or NEW (9%)
3. `tm.py export ru <chapter>` generated structured translation jobs containing only delta blocks, with previous RU as reference for MODIFIED blocks
4. Parallel Claude agents translated all delta blocks (~482 across 26 stale chapters + glossary + appendices)
5. `tm.py apply ru <chapter> <file>` reassembled complete RU chapters from TM (unchanged blocks) + agent output (new/modified blocks)
6. 6 new appendices (D-J) translated from scratch in parallel

**Result:** All 28 existing RU items updated from v0.6 to v20. 6 new appendices added. 34/34 OK, 0 stale, 0 missing.

**New files:**
- `translations/tm.py` -- Translation Memory tool (build/diff/export/apply/stats)
- `translations/tm.json` -- TM database (~3.5 MB, 3,976 segments)
- `translations/README-tm.md` -- TM tool documentation

## v19 (2026-02-28)

**z80-optimizer coverage + mermaid rendering fix.**

**Chapter 23 (AI-Assisted): Superoptimiser sidebar** — new section 23.5b covering z80-optimizer (oisee, 2025):
- Brute-force Z80 superoptimisation: 602,008 provably correct rules from exhaustive length-2 enumeration
- Explains methodology (full state equivalence, 406 opcodes × 406 opcodes, 34.7B comparisons)
- Bridges peephole optimisation (MinZ, 23.5) with the "Z80 they still don't know" discussion (23.6)
- Positions exhaustive search as "the other AI" alongside neural-network-based code generation

**Appendix J (Modern Tools): z80-optimizer entry** in J.5 (PC Demoscene Toolchain):
- Tool listing with usage context, example rules, and cross-reference to Ch.23

**Build fix:** Mermaid fenced code blocks now render correctly in PDF/EPUB. `build_book.py` converts `` ```mermaid id:xxx `` to `` ```{.mermaid} `` for pandoc compatibility.

## v18 (2026-02-27)

**Ped7g feedback patches + scene identity fixes.**

**Chapter 4 (Maths): Signed multiply section** — fills a gap identified by Ped7g where Ch05 calls `mul_signed` 8 times but it was never implemented:
- Two's complement primer (bit 7 = sign, $FF = -1, NEG for abs)
- Sign extension idiom: `rla / sbc a,a` (2 bytes, 8T, branchless)
- `mul_signed` (B,C signed → HL, ~240-260T) and `mul_signed_c` wrapper (A,C → HL) matching Ch05 calling conventions
- Cost comparison table: unsigned vs signed vs square-table

**Chapter 14 (Compression): Ped7g's self-modifying RLE sidebar** — complete 120-byte working mini-intro contributed with permission:
- 9-byte core depacker using SP as data pointer and `db $18,0` → `jr` self-modifying exit trick
- Byte count analysis, interrupt safety note, advanced variants (`jp $C3C3` trick)

**Appendix F: Z80N T-state audit** — nearly all values were wrong (halved). Corrected against wiki.specnext.dev:
- PIXELDN/PIXELAD/SETAE: 4→8T; LDIX/LDDX: 5→16T; LDIRX/LDDRX/LDPIRX: 5→21/16T
- MIRROR/SWAPNIB: 4→8T; TEST: 7→11T; barrel shifts: 4→8T
- PUSH nn: 11→23T; ADD HL/DE/BC,A: 4→8T; NEXTREG: 12→20T / 8→17T; OUTINB: 5→16T
- MUL D,E (8T) was the only correct one

**Scene identity corrections** across glossary, 5 chapters, and all 3 translations:
- sq ≠ psndcj: sq = Screamer (Skrju), psndcj = cyberjack (TBK/Triebkraft + 4D)
- "4th Dimension" → "4D+TBK (Triebkraft)" throughout
- Added Ped7g and Screamer (sq) to glossary Key People tables

## v17 (2026-02-27)

**Appendix J (modern tools), Ch.20 refactor, Ped7g feedback fixes.**

- New Appendix J: Modern Development Tools
- Ch.20 refactored with Unity/Unreal as data generators, Farbrausch sidebar
- Ped7g feedback: shadow register warning fix, pixel_addr fix, Quick Cost table fix, --syntax=abf, VSCode regex, RLE byte count correction

## v16 (2026-02-26)

**Pre-compression data preparation + packer benchmark tool.**

**Chapter 14 (Compression) expanded** with new section "Pre-Compression Data Preparation":
- Shannon entropy as theoretical floor for compression — with Python code to compute it
- Second derivative encoding: sine vs quadratic decay insight (visually identical curves, but quadratic has constant 2nd derivative → compresses to near-zero)
- Transposition for tabular data: column-major reordering of interleaved XYZ vertex tables, AY register dumps, animation keyframes — with concrete entropy measurements (7.52 → 2.58 bits/byte)
- Mask/pixel plane separation for sprites (10–20% ratio improvement)
- Practical transforms table for 8 common demo data types
- Key insight: transpose + delta + fast packer often beats raw + slow packer (better ratio AND faster decompression)
- Two new exercises: transpose-and-measure, quadratic substitution

**New tool: `tools/packbench.py`** — packer benchmark and streaming decompression estimator:
- `bench` mode: run real packer binaries on data files, measure compressed sizes (falls back to Introspec's benchmark ratios when binaries unavailable)
- `budget` mode: 128K memory map from TOML config — reserved areas, per-effect compressed storage, bank utilization
- `timeline` mode: streaming decompression scheduler — models overlap/pause/streaming phases for seamless demo effect transitions; `--what-if` compares all 9 packers per effect
- `analyze` mode: pre-compression data analysis — entropy comparison across transforms (raw/delta/delta²/XOR), stride-based transposition testing, curve fitting (linear/quadratic R²), periodicity detection, actionable suggestions
- All modes support `--json` for Clockwork integration
- 9 packer profiles from Introspec's benchmark + Ped7g's upkr feedback
- 4 platform presets (spectrum48, spectrum128, pentagon128, next)

**New config: `demo/packbench.toml`** — Antique Toy demo memory budget and timeline preset (5 effects: torus, plasma, dotscroll, rotozoomer, credits).

**New Makefile targets:** `packbench`, `packbench-budget`, `packbench-timeline`, `packbench-analyze`.

## v12 (2026-02-24)

**Comprehensive review pass.** Full technical audit of all 23 chapters with systematic fixes:

**12 HIGH severity fixes:**
- Ch.02: RET cc T-state values corrected (5/11T → 11/5T taken/not-taken) across 6 comments + timing table
- Ch.04: Patrik Rak and Raxoft identified as same person throughout
- Ch.07: `SET n,(DE)` / `RES n,(DE)` rewritten — instructions don't exist on Z80, replaced with (HL) approach
- Ch.10: False claim that `LD (addr),SP` doesn't exist removed (ED 73, 20T)
- Ch.11: AY mixer value corrected ($28 → $18 for noise C)
- Ch.15: Contended memory table corrected — only $4000-$7FFF contended on 48K, not all RAM
- Ch.16: XOR sprite inner loop timing corrected (98T → 134T), JR NZ annotations fixed throughout
- Ch.18: `spawn_bullet` bug fixed — D register zeroed before `ADD IX,DE`
- Ch.19: AABB worst-case recounted (156T → ~270T), `tile_at` recounted (40T → ~182T)
- Ch.23: DOWN_HL argument rewritten — was claiming correct code was buggy

**19 MEDIUM severity fixes:** LDIR formula standardised to (N-1)×21+16, PUSH operation order corrected, byte counts fixed, Agon 60Hz corrected, IM2 IY save added, invalid `ld hl,a` replaced, and more.

**AI smell cleanup:** Removed chain-of-thought leaks ("Wait -- that is wrong"), cut philosophical padding sections, eliminated word-level tics (remarkably, deceptively simple, paradigm shift, borders on magic, etc.), trimmed defensive balancing and motivational pep talks across 9 chapters.

**Two new tools:**
- `tools/autotag.py` — semi-automatic code block classifier and tagger (--preview, --apply, --stats)
- `tools/audit_tstates.py` — T-state audit comparing inline annotations with computed values (--scan-chapters, --asm-check)

**Code block pipeline:**
- 79 bare code blocks classified and tagged with language (z80/mermaid/text)
- 279 code blocks tagged with `id:chNN_slug` identifiers
- 271 .z80 + 8 .mmd canonical listings extracted to `listings/`
- Final audit: 0 WRONG, 0 PARTIAL T-state annotations
- All 29 assembly units compile with sjasmplus

## v11 (2026-02-24)

- Art-top/Gogin attribution fix across affected chapters.
- MCC sidebar content added.
- ZXDN research integrated.

## v10 (2026-02-24)

- External listings system (`tools/manage_listings.py`): extract, inject, verify, stats commands.
- Unified versioning via `version.json` + `build_book.py`.
- UNDER CONSTRUCTION banner for work-in-progress chapters.

## v0.8 (2026-02-24)

**Chapters expanded.** Three thin chapters significantly deepened:

- **Chapter 7 (Rotozoomer):** Three rotozoomer variants compared -- monochrome bitmap (full pixel), chunky (2x2/4x4), and attribute-based (32x24 colour grid). New sections on fixed-point stepping mechanics, self-modifying code at the byte level, texture design, and boundary handling. Credits corrected: GOA4K and Refresh are by Exploder^XTM.
- **Chapter 10 (Dotfield Scroller):** POP-trick deep dive with interrupt risks and SP-save patterns. Lissajous, helix, and multi-wave trajectory formulas. 4-phase colour cycling code with attribute byte manipulation. Demoscene lineage from Born Dead to Introspec's Eager.
- **Chapter 13 (Size-Coding):** Now covers the full range from 256 bytes to 4K intros. New size-coder's toolkit (register assumptions, DJNZ tricks, RST as 1-byte CALL, overlapping instructions). 4K intro section with GOA4K (Exploder^XTM), inal and Megademica (SerzhSoft). AY bytebeat and procedural graphics compo sections added.

**Five new appendices** (all 9 now complete, A--I):

- **E: eZ80 Quick Reference** -- ADL mode, MLT/LEA/PEA/TST, Agon Light 2 specifics.
- **F: Z80 Variants** -- Z80N (Next) instructions organised by the pain they solve, R800 (MSX turboR) pipeline and MULUB/MULUW, Soviet clones, comparison table.
- **H: Storage APIs** -- TR-DOS (Beta Disk 128) and esxDOS (DivMMC) with complete port maps, ROM API, and working code examples.
- **I: Bytebeat & AY-Beat** -- Classic PCM bytebeat adapted for the AY-3-8910. Formula cookbook (12 tone + 4 volume formulas), envelope drone, music theory for algorithms (scale tables, arpeggios, ornaments, chord progressions, L-system grammars, PRNG with curated seeds).

**New assembly example:** `aybeat.a80` -- 320-byte AY-beat engine demonstrating pentatonic scales, I-IV-V-I chord progression, arpeggio, step ornaments, envelope drone, and noise percussion. 19 bytes of musical data, three channels of generative sound.

**9 new diagrams** added across chapters 3, 8, 9, 14, 19, 20, 21, 22, 23. All 23 figures tagged with `<!-- figure: chNN_name -->` for greppability and translation tracking.

29 compilable examples, all passing. ~180K words (English).

## v0.7 (2026-02-24)

- Appendix D: Development environment setup (sjasmplus, VS Code, DeZog, emulators).
- Three new chapter examples: ch21 game skeleton (128K, 438 lines), ch22 Agon entity system (240 lines), ch23 AI-assisted diagonal fill (149 lines).
- README rewritten with honest platform positioning ("this book lives on the ZX Spectrum"), per-chapter platform tags, TL;DR with direct download link.
- 28 compilable examples, all passing.

## v0.6 (2026-02-23)

- All 23 chapters drafted. All 4 language editions (EN, ES, RU, UK) built and released.
- Translation manifest system for staleness tracking.
- ~128K words (English), ~575K words total across all languages.
