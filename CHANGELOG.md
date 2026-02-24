# What's New

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
