# Appendix M: BCD Arithmetic on Z80 — GPU-Proven Optimal Sequences

> *`ADD A,A : DAA` --- BCD double in two instructions. The GPU proved there is nothing shorter.*

---

## M.1 Why BCD on Z80?

Binary-Coded Decimal stores each decimal digit in a nibble: the byte `$42` represents the number 42. Score counters, timers, and HUD displays in games all benefit from BCD --- no binary-to-decimal conversion needed for display. The Z80's `DAA` (Decimal Adjust Accumulator) instruction makes BCD arithmetic practical.

---

## M.2 GPU-Proven BCD Operations

The superoptimizer searched for optimal BCD sequences with a correct half-carry (H flag) model. An early search had a bug (missing H flag in the DAA model) --- fixing it unlocked all results.

| Operation | Z80 Code | Insts | T-states | Notes |
|-----------|----------|-------|----------|-------|
| BCD × 2 | `ADD A,A : DAA` | 2 | 8T | Double in BCD |
| BCD + 1 | `INC A : DAA` | 2 | 8T | Increment in BCD |
| BCD − 1 | `DEC A : DAA` | 2 | 8T | Decrement in BCD |
| BCD + BCD | `ADD A,B : DAA` | 2 | 8T | Add two BCD values |
| 100's complement | `NEG : DAA` | 2 | 12T | BCD negate (99 − n + 1) |
| BCD × 10 | `ADD A,A : DAA` (×2) then shift | 6 | ~28T | Via ×2, ×4, ×8+×2 |

Every sequence is provably optimal --- the GPU verified that no shorter sequence exists for any of these operations.

---

## M.3 The DAA Half-Carry Gotcha

`DAA` inspects two flags that most Z80 programmers ignore:

- **H flag** (half-carry): set when a carry occurs from bit 3 to bit 4 within a nibble
- **N flag**: set after subtraction (`SUB`, `DEC`, `NEG`), clear after addition (`ADD`, `INC`)

If the H flag model is wrong, `DAA` adjustments are incorrect for ~15% of inputs. The GPU's first search pass missed this, producing sequences that looked correct on spot checks but failed on edge cases like `$09 + $01` (should give `$10`, not `$0A`).

**Lesson:** when superoptimizing with `DAA`, the emulator must track H and N flags precisely. The Z80 manual's DAA truth table has 6 cases, not 2.

---

## M.4 Practical Use: Score Counter

```z80
; Increment 3-byte BCD score (6 digits) by value in A
; Score stored as BCD at (score), (score+1), (score+2)
add_score:
    ADD  A, (HL)      ; add to low byte
    DAA               ; BCD adjust
    LD   (HL), A
    INC  HL
    LD   A, 0         ; carry only (don't clear carry flag!)
    ADC  A, (HL)      ; propagate carry to middle byte
    DAA
    LD   (HL), A
    INC  HL
    LD   A, 0
    ADC  A, (HL)      ; propagate carry to high byte
    DAA
    LD   (HL), A
    RET               ; 6-digit BCD score updated
```

No binary-to-decimal conversion needed for display --- each nibble maps directly to a font character.

---

*Sequences verified by z80-optimizer v1.0.0 with full H/N flag DAA model.*
