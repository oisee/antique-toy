# Ped7g Discord Review Feedback (2026-02-25)

Source: Czech/Slovak ZX Spectrum Discord
Language: Slovak

## upkr compression

See `upkr_compression.md` in this folder. Key point: sweet spot 512-2048 compressed bytes,
above that too slow for 3.5MHz. Not suitable for 32KB demos.

**Status**: Added to packbench.py packer profiles and mentioned in Ch.14/Appendix C.

## General readiness question

> судя по скорости релизов, мне кажется, что это пишет AI, а ты только «рулишь». Так что
> если ты собираешься некоторые главы ещё несколько раз основательно переделывать и проверять,
> то мне кажется бессмысленным сейчас стараться делать исправления и рисковать, что они снова
> пропадут при следующем редактировании.

> в целом выглядит интересно... но пока я бы обозначил это как WIP/draft, потому что словами
> Introspec'а — «Z80 they still don't know» — и это видно по результату.

**Response**: Very early stages, book is < 1 week old. Opus accelerates prototyping but
human review needed. After topic stabilization, human editors will be assigned per chapter.
Feedback won't be lost — goes into feedback/corrections folder as guardrails.

## Appendix A specific issues

### 1. Shadow registers warning — INCORRECT claim

> Warning: The Spectrum ROM interrupt handler (IM1) uses the shadow registers.
> If interrupts are enabled, EXX/EX AF,AF' data will be corrupted on every interrupt.

Ped7g says: only IY is important (must point to sysvars or safe memory),
shadow registers are preserved by ROM ISR.

**Status**: ✅ Fixed (2026-02-26). Warning now correctly says IY is the concern,
shadow registers are safe. Appendix A line ~447.

### 2. pixel_addr routine (p.464) — incomplete

> Missing setting of upper 3 bits in L to Y:5:3

**Status**: ✅ Fixed (2026-02-26). Added Y[5:3] → L[7:5] computation using
AND $38 + RLCA + RLCA, then OR with X/8 column bits. T-state cost updated to ~107T.

### 3. Quick Cost Comparisons — confusing

> "Copy 1 byte to mem" — the "slow way" writes to HL and is actually faster.
> The two approaches are too different to compare without explanation.
> Looks more like set/fill than copy.

**Status**: ✅ Fixed (2026-02-26). Row relabeled to "Copy 1 byte (HL)→(DE)" with
correct slow way: `LD A,(HL)`+`LD (DE),A`+`INC HL`+`INC DE` (26T, 4B) vs LDI (16T, 2B).

### 4. sjasmplus --syntax=abf

> Would be happier if --syntax=abf was more promoted. More reasonable default
> for people starting with sjasmplus.

**Status**: ✅ Added (2026-02-26). Listed in Appendix D Key Flags table with
description of what it enables.

### 5. VSCode problemMatcher regex

> Current regex doesn't catch id-warnings like `warning[out0]`.
> Suggested fix: `^(.*)\\((\\d+)\\):\\s+(error|warning)[^:]*:\\s+(.*)$`

**Status**: ✅ Fixed (2026-02-26). Applied Ped7g's suggested regex.

### 6. RLE routine in compression chapter

> RLE routine offered for 256B intros is unnecessarily long and has
> wrong T-states count.

**Status**: ✅ Fixed (2026-02-26). Code size corrected from "23 bytes" / "under 30 bytes"
to correct "12 bytes". T-state annotation clarified with per-pair overhead note.
Added transposition tip for improving RLE compression with 2D data.

### 7. Z80N instructions (Appendix F)

> T-state counts "fly up and down" — possible first draft quality.

**Status**: ✅ IMPLEMENTED (2026-02-27). Full audit of all Z80N T-state values against
wiki.specnext.dev. Nearly all values were halved; corrected PIXELDN/PIXELAD/SETAE (4→8T),
LDIX/LDDX (5→16T), LDIRX/LDDRX/LDPIRX (5→21/16T), MIRROR/SWAPNIB (4→8T), TEST (7→11T),
BSLA/BSRA/BSRL/BSRF/BRLC (4→8T), PUSH nn (11→23T), ADD HL/DE/BC,A (4→8T),
NEXTREG reg,val (12→20T), NEXTREG reg,A (8→17T), OUTINB (5→16T). MUL D,E (8T) was already correct.
Ped7g audit credit added to Sources section.

---

## RLE depacker for 256B intros — detailed follow-up (2026-02-27)

Ped7g clarifies his earlier RLE comment wasn't just "a feeling" that RLE is big for 256 bytes,
but that the code is genuinely long and complex. Provides a complete working example.

### Minimal self-modifying RLE depacker (9 bytes core)

```z80
target:
  ds <size needed + stack>
intro_data:
  dw target
  db value, rep
  ..
  db 0x18,0 ; must reach `ld (hl),c` and overwrite it to create opcode `18 23` -> `jr rle_loop_inner+0x25`
rle_start:
  ld sp,intro_data
  pop hl
rle_loop_outer:
  pop bc
rle_loop_inner:
  ld (hl),c
  inc hl
  djnz rle_loop_inner
  jr rle_loop_outer
; 0x1F bytes to fill with other helper code
  ds 0x1F
intro_start:
  assert $ == rle_loop_inner + 2 + 0x23 ; make sure we are at exiting `jr` target
  ...
```

### Byte count analysis

- Book's "minimal RLE decompressor": 13 bytes (but HL+DE pre-set, needs outer call)
- Ped7g's skeleton: `db 0x18,0` (jr in data) + `rle_loop_outer` code → 2+1+1+1+2+2 = **9 bytes** core
- SP+HL setup adds +6 → **15 bytes total** for self-contained RLE decoder
- Awkward 31-byte window that must be jumped over and filled with code; worst case +4 bytes (2x jr)

### Complete working example (120 bytes .bin)

```z80
    DEVICE ZXSPECTRUM48, $8000

target  EQU $4000
  ; start RLE with filling screen
    ORG $5B00       ; loading address of intro -> print buffer
intro_data:
    dw target
; bitmap stripes every other line
    .(4*3) db $AA, 0, $00, 0
    db $43, 32*2, $44, 32*4, $45, 32*3, $46, 32*2, $47, 32*2
    db $46, 32*2, $45, 32*3, $44, 32*4, $43, 32*2
    db 0x18,0 ; must reach `ld (hl),c` and overwrite it to create opcode `18 23` -> `jr rle_loop_inner+0x25`
rle_start:
  ei  ; simulate BASIC environment after LOAD including enabled interrupts during depack
  ld sp,intro_data
  pop hl
rle_loop_outer:
  pop bc
rle_loop_inner:
  ld (hl),c
  inc hl
  djnz rle_loop_inner
  jr rle_loop_outer
; 0x1F bytes to fill with other helper code
  ds 0x1F
intro_start:
  assert $ == rle_loop_inner + 2 + 0x23 ; make sure we are at exiting `jr` target
    inc a
    and 7
    out (254),a
    jr intro_start

    SAVESNA "temp.sna", rle_start
    SAVEBIN "temp.bin", intro_data, $-intro_data    ; real intro binary
```

Result: 120 bytes .bin (including 31 bytes padding that could contain code).
Screenshot: colored stripes filling screen via attribute values.

### Complexity notes for the book

Ped7g notes this is harder to describe in a book because:
1. Part of the data IS the mechanism (the `db 0x18,0` overwrites the depack loop to create a `jr` exit)
2. User must understand the buffer must end "in the code" to overwrite the depack loop
3. Advanced users will immediately ask "wait, he changes SP, what about interrupts?" —
   the interrupt does occasionally overwrite something, but only data already consumed,
   so the stack remains functional for the intro code itself

### Permission

**Permission GRANTED** (2026-02-27): "samozrejme, urob s nim co chces, je to sucast feedbacku"
(= "of course, do whatever you want with it, it's part of the feedback")

### Additional RLE exit variations (2026-02-27)

Ped7g suggests more exit strategies beyond the `jr` self-modify:
1. **Target area behind code** — RLE depacker at the end, overwrite `jr rle_loop_outer`
   offset so it jumps further to intro code without needing the 31-byte padding window
2. **`jp $C3C3` trick** — place `$C3` values in RLE data with exact repeat count so DJNZ
   terminates exactly when `jp $C3C3` opcode is assembled in memory; align the whole intro
   so address $C3C3 is the continuation of the intro. Eliminates both padding AND explicit
   exit code.
3. General principle: "takych veci sa da vymysliet... vzdy zalezi na konkretnej situacii"
   (you can invent many such things, always depends on the specific situation)

**Status**: ✅ IMPLEMENTED (2026-02-27). Added as sidebar in Ch.14 (compression) with
complete working mini-intro (120 bytes), byte count analysis, interrupt safety note,
advanced variants, and full credit/permission attribution.

---

## Signed arithmetic gap (2026-02-27)

> "nasobenie je vzdy len unsigned a neskor uz sa len vola napr. nejake rotate ale nikde
> sa nerozobera priamo ako riesit signed cisla"
>
> (multiplication is always only unsigned, and later it just calls e.g. some rotate
> but nowhere is there a direct discussion of how to handle signed numbers)

### Analysis

**Confirmed gap.** Ch04 covers unsigned multiply (shift-and-add, square table). Ch05 calls
`mul_signed` / `mul_signed_c` but **never shows the implementation**. No dedicated section on:
- Two's complement fundamentals (what it is, why $FF = -1)
- Sign extension (byte→16-bit: `bit 7,a / sbc a,a / ld d,a`)
- NEG instruction and when to use it vs XOR+INC
- Signed multiply algorithm (abs+multiply+sign-correct, or Booth's)
- Signed 8.8 fixed-point multiplication
- Signed division

Ch19 (collisions) uses SRA for signed right shift but doesn't teach it systematically.

### Action needed

Add a dedicated "Signed Arithmetic" section to Ch04, covering:
1. Two's complement primer (3-4 paragraphs)
2. Sign extension patterns with code
3. `mul_signed` implementation (the one Ch05 calls!)
4. Cost comparison table: signed vs unsigned operations
5. Worked example: signed coordinate rotation

**Status**: ✅ IMPLEMENTED (2026-02-27). Added dedicated "Signed Multiply" section to Ch04
with two's complement primer, sign extension idiom (rla/sbc a,a), mul_signed implementation
(matching Ch05 calling convention: B,C → HL), mul_signed_c wrapper (A,C → HL for backface
culling), cost comparison table, and Ped7g credit.

**Priority: HIGH** — this is a fundamental building block that multiple later chapters depend on.
