# Book Review Synthesis — v11

Date: 2026-02-24
Scope: All 23 English chapters, technical accuracy + AI smell

## Stats (programmatic)

- **107,401 words** across 23 chapters (prose only)
- **363 code blocks** (267 z80, 79 untagged, 8 mermaid, 9 other)
- **0 tagged blocks** (listings system not yet adopted)
- **0 TODOs** remaining
- **1 thin chapter**: Ch.03 at 2,900 words
- **2 code-heavy chapters**: Ch.18 (1,070 code lines), Ch.21 (1,074 code lines)

---

## HIGH Severity — Must Fix (12 issues)

| # | Ch | Issue | Root Cause |
|---|-----|-------|------------|
| 1 | 02 | RET cc T-state values swapped in 6 comments + timing table | 5/11 reversed: taken=11T, not-taken=5T |
| 2 | 04 | Patrik Rak and Raxoft treated as different people | Same person (Raxoft = handle) |
| 3 | 07 | `SET n,(DE)` / `RES n,(DE)` used in code | **Instructions don't exist on Z80** — only (HL)/(IX+d)/(IY+d) |
| 4 | 10 | Claims `LD (addr),SP` doesn't exist | **It does: ED 73, 20T** — code uses it while claiming it's impossible |
| 5 | 11 | Mixer value $28 wrong — enables noise B, not noise C | $28=0b00101000 → noise B on; correct for noise C = $18 |
| 6 | 15 | 48K contended memory table claims ALL RAM contended | Only $4000-$7FFF is contended; $8000+ is uncontended |
| 7 | 16 | XOR sprite inner loop claimed 98T/row, actual **134T** | JR NZ annotated as 7T (not-taken), but common case is taken = **12T** |
| 8 | 16 | Same JR NZ error in masked sprite code | Same root cause as #7 |
| 9 | 18 | `spawn_bullet`: `ADD IX,DE` with dirty D register | D contains loop counter (7,6,5...), corrupting IX. Real code bug. |
| 10 | 19 | AABB worst-case claims ~156T, actual **~270T** | 12 IX/IY-indexed instructions at 19T each = 228T alone |
| 11 | 19 | `tile_at` claims ~40T, actual **~182T** | Off by 4.5x — core frame budget routine |
| 12 | 23 | DOWN_HL claimed buggy but is **actually correct** | Chapter's key "AI gets Z80 wrong" argument uses a correct example |

---

## MEDIUM Severity — Should Fix (17 issues)

| # | Ch | Issue |
|---|-----|-------|
| 1 | 02 | LDIR cost calculation off by 21T (wrong formula) |
| 2 | 02 | Attribute LDIR cost: wrong byte count AND wrong arithmetic |
| 3 | 02 | UP_HL has same RET cc comment bug |
| 4 | 06 | Summary reverses Illusion (1996) / SE articles (1997) causation |
| 5 | 07 | 2x2 chunky cost uses 96 rows, should be 48 texel rows |
| 6 | 08 | PUSH operation order described backwards |
| 7 | 09 | LD HL,nn + LDI = 5 bytes, not 6 |
| 8 | 10 | PUSH-based 768-byte copy claims ~4,500T, actual ~8,064T |
| 9 | 11 | Natural tuning table: F2 mod 16 = 8, not 0 |
| 10 | 11 | Natural tuning table: A#2 mod 16 = 10, not 2 |
| 11 | 11 | TurboSound register blast: claims ~400T, actual ~800-1600T |
| 12 | 11 | sfx_pickup table has editing artifact (false-start data left in) |
| 13 | 15 | Agon frame rate: table says 50Hz but Agon runs at 60Hz |
| 14 | 16 | Masked sprite row advance: 27T not 22T |
| 15 | 16 | Agon baud rate: ch15 says 384K, ch16 says 1.152M |
| 16 | 18 | Stack at $FFFF is in banked memory region |
| 17 | 19 | AABB code silently wraps on X+width overflow |
| 18 | 21 | IM2 handler doesn't save/restore IY |
| 19 | 22 | `ld hl, a` is not a valid Z80/eZ80 instruction |

---

## AI Smell — Patterns Identified

### Structural patterns (cut or rewrite)
1. **"X is not Y. It is Z." reframing** — appears in ch07, ch09, ch10, ch12, ch23. Once is style, five times is a tic.
2. **Unattributed faux-profound epigraphs** — ch19, ch21, ch22 all open with AI-generated aphorisms
3. **Chain-of-thought leaking** — Ch.02 has "Wait -- that is wrong" and three failed derivation attempts LEFT IN PROSE
4. **Philosophical summary sections** — ch06, ch08, ch10, ch13, ch22, ch23 all have "what this means" sections that restate technical content as aphorisms
5. **Motivational pep talks** — ch20 "You will not win" paragraph, ch23 "If that makes you uncomfortable, good"
6. **Defensive AI balancing** — "This is not a criticism of either platform" (ch17)

### Word-level tics to search-and-destroy
- "remarkably" (ch05 x2, ch09)
- "deceptively simple" (ch11, ch12)
- "staggering" (ch05)
- "profound" (ch04)
- "liberating" (ch15)
- "paradigm shift" (ch15)
- "borders on magic" (ch13)
- "startlingly convincing" (ch12)

### MEDIUM AI smell (should cut/rewrite)
| Ch | Section/Line | Issue |
|----|-------------|-------|
| 02 | Lines 330-332 | "Wait -- that is wrong" chain-of-thought |
| 02 | Lines 579-670 | Three failed derivation attempts |
| 08 | Lines 390-402 | "What DenisGrachev's Work Means" editorial padding |
| 10 | Lines 280-291 | "Temporal Cheating" philosophy section |
| 13 | Lines 542-551 | "Size-Coding as Art" philosophical padding |
| 17 | Line 607 | "This is not a criticism" defensive balance |
| 20 | Line 388 | "You will not win" motivational speech |
| 22 | Lines 726-753 | "What Each Platform Forces You To Do Better" — 30 lines of truisms |
| 23 | Lines 399-411 | "The Broader Picture" generic AI observations |

---

## Recurring T-State Error Pattern

The single most common technical error across the book is **JR cc / RET cc timing confusion**:
- JR cc: taken=12T, not-taken=7T
- RET cc: taken=11T, not-taken=5T

Errors found in: Ch.02 (6 locations), Ch.07 (1), Ch.16 (2). The comments consistently annotate the NOT-TAKEN cost as the primary value, when the TAKEN cost should come first (matching the book's own convention).

**Recommendation:** Global search for all `; *[0-9]+T` annotations on JR and RET conditional instructions. Verify each one.

---

## LDIR Formula Error Pattern

Multiple chapters use the wrong LDIR cost formula:
- **Wrong:** N × 21 + 16 (double-counts last byte)
- **Correct:** (N-1) × 21 + 16

Found in: Ch.02 (lines 447, 462), Ch.17 (line 28). Ch.03 and Ch.17 line 376 get it right.

**Recommendation:** Search all LDIR cost calculations, standardize to (N-1)×21+16.

---

## Per-Chapter Readiness Assessment

| Ch | Title | Verdict | Key Issues |
|----|-------|---------|------------|
| 01 | Thinking in Cycles | **LOCK** | Minor (6912 = "pixel data" wording) |
| 02 | Screen as Puzzle | **EDIT** | RET cc swap, LDIR formulas, chain-of-thought leaks |
| 03 | Demoscene Toolbox | **EDIT** | Thin (2900 words), frame budget inconsistency |
| 04 | Maths | **EDIT** | Raxoft=Patrik Rak, "profound principle" |
| 05 | 3D | **LOCK** | Minor ("remarkably" x2, overflow caveat) |
| 06 | Sphere | **LOCK** | Minor (summary causation, padding section) |
| 07 | Rotozoomer | **EDIT** | SET/RES (DE) don't exist, row count confusion |
| 08 | Multicolor | **LOCK** | Minor (PUSH order, DenisGrachev section) |
| 09 | Tunnels | **LOCK** | Minor (5 not 6 bytes, BC side effect) |
| 10 | Scroller | **EDIT** | LD(nn),SP claim, PUSH cost 2x off, flicker threshold |
| 11 | Sound | **EDIT** | Mixer $28 wrong, tuning table errors, blast cost |
| 12 | Music Sync | **LOCK** | Minor (opening paragraph, "startlingly") |
| 13 | Sizecoding | **LOCK** | Minor (cut sec 13.10 padding) |
| 14 | Compression | **LOCK** | Minor (ZX0/ZX7 sizes, budget arithmetic) |
| 15 | Anatomy | **EDIT** | Contended memory table wrong, Agon 50/60Hz |
| 16 | Sprites | **EDIT** | XOR sprite 98T→134T, JR NZ errors throughout |
| 17 | Scrolling | **LOCK** | Minor (LDIR formula, defensive balance) |
| 18 | Game Loop | **EDIT** | spawn_bullet bug, stack in banked memory |
| 19 | Collisions | **EDIT** | AABB 156→270T, tile_at 40→182T, overflow bug |
| 20 | Demo Workflow | **LOCK** | Minor (cut motivational paragraph) |
| 21 | Full Game | **LOCK** | Minor (IY save, CLEAR value) |
| 22 | Porting Agon | **EDIT** | Invalid `ld hl,a`, baud rate conflict, padding |
| 23 | AI-Assisted | **EDIT** | DOWN_HL "bug" is correct, generic closing |

### Summary
- **LOCK (ready for illustrations/code/screenshots):** 12 chapters (1, 5, 6, 8, 9, 12, 13, 14, 17, 20, 21, 22→after minor fixes)
- **EDIT (needs text fixes before locking):** 11 chapters (2, 3, 4, 7, 10, 11, 15, 16, 18, 19, 23)

---

## Recommended Fix Order

1. **Global JR/RET timing audit** — systematic, catches the #1 recurring error
2. **Ch.02** — highest density of errors, most visible (early chapter)
3. **Ch.19** — T-state claims off by 2-4x, feeds frame budget decisions
4. **Ch.23** — DOWN_HL argument is wrong, needs new example or rewrite
5. **Ch.16** — sprite costs wrong, readers will reproduce these
6. **Ch.11** — mixer value, tuning table, blast cost
7. **Ch.15** — contended memory table
8. **Ch.07** — nonexistent instructions
9. **Ch.10** — LD(nn),SP claim
10. **Ch.04** — Raxoft identity
11. **Ch.18** — spawn_bullet bug
12. **Ch.22** — invalid instruction, baud rate
13. **AI smell cleanup pass** — search-and-destroy word list + cut padding sections
