# MinZ v0.23.0 — Highlights for Antique Toy Book

From the Birthday Marathon sprint (2026-03-26). Material for chapters on assembly, optimization, and demoscene techniques.

---

## 1. MZA INCBIN — Binary Data Embedding

```z80
; Include sprite data directly in assembly
sprite_data:
    INCBIN "player.spr"              ; entire file
font_8x8:
    INCBIN "font.bin", 0, 768        ; first 768 bytes (96 chars × 8 rows)
sin_table:
    INCBIN "sin256.bin"              ; precomputed sine LUT
mul_table:
    INCBIN "mulopt8.bin", 128, 256   ; skip header, take 256 bytes
```

**Syntax:** `INCBIN "filename" [, offset [, length]]`
- Resolves paths relative to source file directory
- Bounds checking on offset/length
- Perfect for: sprites, fonts, lookup tables, GPU-precomputed data

**Book usage:** Chapters on sprites, fonts, screen data. Replace hand-typed DB sequences.

---

## 2. RLCA Sled — Multi-Entry Barrel Shifter (9 bytes)

```z80
; 8 entry points, one shared function. Fall-through cascade.
__rotate_7:  RLCA        ; enter here for 7-bit rotation
__rotate_6:  RLCA
__rotate_5:  RLCA
__rotate_4:  RLCA        ; ← nibble swap entry
__rotate_3:  RLCA
__rotate_2:  RLCA
__rotate_1:  RLCA
__rotate_0:  RET         ; shared return — 9 bytes total
```

**Usage:**
```z80
; Nibble swap: CALL __rotate_4
LD A, 0xAB
CALL __rotate_4      ; A = 0xBA — 43T (17+16+10)

; High nibble extraction:
CALL __rotate_4
AND 0x0F             ; A = high nibble

; Rotate left by 3:
CALL __rotate_3      ; 39T (17+12+10)
```

**Cost analysis:**
| Method | Bytes | T-states |
|--------|-------|----------|
| 4× RLCA inline | 4 | 16T |
| CALL __rotate_4 | 3 (CALL) + 9 (shared) | 43T |
| Loop with counter | ~8 | ~60T |

Sled trades speed for code size: 9 shared bytes serve ALL rotation counts.
With multiple callers, total code size shrinks.

**TSMC variant:** First call patches `CALL __rotate_0` → `CALL __rotate_N`.
Subsequent calls execute patched dispatch — zero overhead decision.

**MinZ peephole:** Compiler automatically folds 3+ consecutive RLCA instructions → `CALL __rotate_N`. Sled auto-emitted when referenced.

**Book usage:** Chapter on optimization techniques, TSMC section, barrel shifter tricks.

---

## 3. DD Prefix Gotcha: LD IXH, H

**The bug:** Under DD prefix, `H` means `IXH`. So `LD IXH, H` = `LD IXH, IXH` = NOP!

```z80
; WRONG — this is a no-op!
LD IXH, H        ; DD 64 = LD IXH, IXH (not LD IXH, H)

; CORRECT — route through A
LD A, H           ; 4T
LD IXH, A         ; 8T — total 12T, 3 bytes
```

All 8 combinations affected:
- `LD IXH, H` / `LD IXH, L` / `LD IXL, H` / `LD IXL, L`
- `LD IYH, H` / `LD IYH, L` / `LD IYL, H` / `LD IYL, L`

MZA assembler handles this automatically via fake instruction expansion.

**Book usage:** Chapter on undocumented instructions, IX/IY half-registers section.

---

## 4. GPU-Optimal Arithmetic (from z80-optimizer v1.0.0)

### Constant Multiplication (164 sequences)
```z80
; GPU ×10: 20T (vs Dark's MULU112: 196T — 10× speedup!)
; A = A × 10
    ADD A, A        ; ×2
    LD B, A
    ADD A, A        ; ×4
    ADD A, A        ; ×8
    ADD A, B        ; ×8 + ×2 = ×10
```

### Constant Division (118/120 sequences)
```z80
; GPU div3: 130T (vs loop ~340T — 2.6× faster)
; GPU div10: 124T (matches Hacker's Delight!)
; GPU div100: 9 instructions
```

### Branchless ABS
```z80
; ABS(A) = 6 instructions, 24T — no branch!
; (found by GPU exhaustive search over 33-op pool)
```

### Branchless NOT (logical)
```z80
; NOT(A) = 3 instructions, 16T
NEG               ; 0→0, nonzero→nonzero, sets CY
SBC A, A          ; CY→0xFF, no CY→0x00
INC A             ; 0xFF→0x00, 0x00→0x01
```

**Book usage:** Chapter 4 (maths) appendix. Show GPU brute-force methodology + results table.

---

## 5. C99/C11/C23 on Z80

MinZ C frontend now supports:
- **C99:** `_Bool`, for-init-decl, designated init (struct + array), compound literals, mixed decls
- **C11:** `_Static_assert`, `_Generic`, anonymous structs/unions, `_Alignof`, `typeof`
- **C17:** Full conformance (`__STDC_VERSION__ = 201710L`)
- **C23:** `bool`/`true`/`false` as keywords (no include needed)
- **Headers:** stdbool.h, assert.h, ctype.h (17 inline funcs), stdalign.h, stdnoreturn.h
- **514/514** corpus asserts pass

**Book usage:** Chapter on modern C on retro hardware, if relevant.

---

## 6. @error — Z80-Native Error Propagation

```nanz
fun safe_div?(a: u8, b: u8) -> u8 {
    if b == 0 { @error(1) }    // SCF / LD A, 1 / RET — 2 bytes
    return a / b
}

fun compute(a: u8, b: u8) -> u8 {
    var x: u8 = safe_div?(a, b)
    @propagate                  // RET C — 1 byte! conditional return on carry
    return x + 1
}
```

CY flag = error signal. A register = error code. `RET C` = propagate.
**The Z80 was designed for this pattern** — `RET C` is 1 byte, 5T (11T when taken).

Parser enforces: `?` in function name = fallible → must have `@check`/`@propagate` after call.

**Book usage:** Chapter on error handling, Z80 flag tricks.

---

## Links

- **Release:** https://github.com/oisee/minz/releases/tag/v0.23.0
- **z80-optimizer:** https://github.com/oisee/z80-optimizer/releases/tag/v1.0.0
- **RLCA sled example:** examples/nanz/16_rotate_sled.nanz
- **C Standards Roadmap:** docs/C_Standards_Roadmap.md
- **@error design:** docs/Error_Propagation_Design.md
- **Session wisdom:** contexts/2026-03-26-session-wisdom.md

---

*From MinZ Birthday Marathon, 2026-03-26. Happy to answer questions! — ddll send ju6yy047:main*
