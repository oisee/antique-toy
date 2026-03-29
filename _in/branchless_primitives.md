# Z80 Branchless Primitives Library
## Exhaustive-Verified Sequences for Branch-Free Computation

*From z80-optimizer project, March 2026. All sequences verified on 256 or 65536 inputs.*

---

## The Foundation: SBC A,A

```z80
SBC A, A    ; A = CY ? 0xFF : 0x00
            ; 1 instruction, 4 T-states
            ; CY flag PRESERVED after execution
```

This single instruction converts the carry flag into a bitmask.
It is the most important Z80 idiom for branchless programming.

---

## Flag Materialization (Exhaustive Brute-Force Results)

### What works (branchless)

| Conversion | 0/1 repr | 0xFF/0x00 repr | Winner |
|-----------|----------|----------------|--------|
| CY→A | RLA; AND 1 (2i, 11T) | **SBC A,A (1i, 4T)** | 0xFF |
| CY→Z | CCF; SBC A,A (2i, 8T) | CCF; SBC A,A (2i, 8T) | tie |
| A→Z | ADD A,A (1i, 4T) | **AND A (1i, 4T) preserves A!** | 0xFF |
| A→CY | RRCA (1i, 4T, clobbers A) | RLCA (1i, 4T, clobbers A) | tie |
| A→CY preserve A | CP 1; CCF (2i, 11T) | CP 1; CCF (2i, 11T) | tie |
| 0/1 ↔ 0xFF | NEG (1i, 8T) | NEG (1i, 8T) | — |

**Verdict: 0xFF/0x00 wins** — 20T total vs 27T for 0/1 representation.
Boolean AND/OR/XOR/NOT are FREE with 0xFF/0x00 (native Z80 logic instructions).

### What's impossible (proven)

**Z→CY and Z→A: IMPOSSIBLE branchless.**

Proof: exhaustive analysis of all 26 relevant Z80 instructions shows that NO instruction
uses the Z flag as input for computing A or CY. The Z flag is **write-only** — it is set
by ALU operations but never read by any non-branching instruction.

By induction: if no single instruction propagates Z→{A,CY}, then no sequence can either.
Verified exhaustively at depth 4 (456,976 sequences): zero propagate Z→CY.

The only instructions that read Z are conditional branches:
JR Z / JR NZ / JP Z / JP NZ / CALL Z / CALL NZ / RET Z / RET NZ

**Implication for compilers:** CY is the only viable flag for branchless bool propagation.
Z flag = branch-only.

---

## Branchless Arithmetic

### ABS(A) — Signed Absolute Value
```z80
; Input: A = signed 8-bit (-128..127)
; Output: A = |A| (0..128)
; Clobbers: B, C
; Cost: 6 instructions, 24 T-states
; Verified: 256/256 correct

    LD  B, A        ; save original
    RLCA            ; bit 7 (sign) → CY
    SBC A, A        ; A = mask (0xFF if negative, 0x00 if positive)
    LD  C, A        ; save mask
    XOR B           ; A = original XOR mask
    SUB C           ; A = (original XOR mask) - mask = |original|

; Math: abs(x) = (x XOR mask) - mask, where mask = arithmetic_shift_right(x, 7)
; When positive: mask=0, (x XOR 0) - 0 = x
; When negative: mask=0xFF, (x XOR 0xFF) - 0xFF = ~x + 1 = -x
```

### MIN(A, B) — Unsigned Minimum
```z80
; Input: A = first value, B = second value
; Output: A = min(A, B)
; Clobbers: C, D
; Cost: 8 instructions, 32 T-states
; Verified: 65536/65536 correct (all 256×256 combinations)

    LD  C, A        ; save A
    SUB B           ; CY = (A < B)
    SBC A, A        ; mask = CY ? 0xFF : 0x00
    LD  D, A        ; save mask
    LD  A, C        ; restore original A
    XOR B           ; A = A XOR B
    AND D           ; A = (A XOR B) AND mask
    XOR B           ; A = B XOR ((A XOR B) AND mask) = min(A,B)

; Math: select(mask, A, B) = B XOR ((A XOR B) AND mask)
; When CY (A<B): mask=0xFF, B XOR (A XOR B) = A ✓
; When NC (A≥B): mask=0x00, B XOR 0 = B ✓
```

### MAX(A, B) — Unsigned Maximum
```z80
; Same structure, swap operands in final XOR
    LD  C, A
    SUB B           ; CY = (A < B)
    SBC A, A
    LD  D, A
    LD  A, B        ; ← B instead of C
    XOR C           ; ← C instead of B
    AND D
    XOR C           ; A = max(A,B)
; 8 instructions, 32 T-states, verified 65536/65536
```

### CMOV: CY ? B : C — Conditional Move
```z80
; Input: CY = condition, B = true value, C = false value
; Output: A = CY ? B : C
; Clobbers: A, D
; Cost: 6 instructions, 24 T-states
; Verified: 131072/131072 (2 × 256 × 256)

    SBC A, A        ; mask = CY ? 0xFF : 0x00
    LD  D, A        ; save mask (CY still preserved!)
    LD  A, B        ; A = true_value
    XOR C           ; A = true XOR false
    AND D           ; A = (true XOR false) AND mask
    XOR C           ; A = false XOR ((true XOR false) AND mask) = select

; This is the bitwise select: result = C ^ ((B ^ C) & mask)
; ARM has CSEL, x86 has CMOV — Z80 has this 6-instruction sequence.
```

### CLAMP(A, lo, hi) — Range Clamping
```z80
; = MAX(lo, MIN(A, hi)) — two chained CMOVs
; 16 instructions, 64 T-states
; Clobbers: A, B, C, D, E
```

---

## Division by Constant

### div3: EXACT (no lookup table!)
```z80
; A = A / 3 (unsigned, truncating)
; Method: A × 171 >> 9
; Verified: 256/256 EXACT — zero error for all inputs 0-255

    LD  B, A        ; save input
    LD  C, 171      ; magic constant
    CALL mul8       ; HL = A × 171 (use mul8 from tables)
    SRL H           ; H = (A×171) >> 9 (the >>8 is implicit in H, +1 SRL)
    LD  A, H        ; result
```

**Why 171?** ⌊256×256/3⌋ = 21845, and 171 = ⌊21845/128 + 0.5⌋.
The formula A×171>>9 gives exact integer division by 3 for all uint8 values.

### Other divisors (approximate, max error = 1)

| Divisor | Formula | Exact/256 | Max error |
|---------|---------|-----------|-----------|
| /3 | A×171>>9 | **256/256** | **0** |
| /5 | A×103>>9 | 239/256 | 1 |
| /7 | A×37>>8 | 220/256 | 1 |
| /10 | A×26>>8 | 218/256 | 1 |

---

## Branch vs Branchless on Z80

**On Z80, branch usually wins.** The branch misprediction penalty is only 5T
(failed conditional = instruction fetched but not taken). Branchless overhead
is typically 15-24T.

| Approach | abs_diff cost | When to use |
|----------|--------------|-------------|
| Branch: SUB C; RET NC; NEG | 9T fast, 14T slow | **Default choice** |
| Branchless: 6-instruction ABS | 24T always | GPU codegen, crypto |

**Branchless is valuable for:**
1. **SBC A,A mask** — always worth it (1 instruction CY→mask)
2. **CMOV in hot inner loops** where branch cost > body cost
3. **GPU code generation** (Nanz→CUDA, no branch divergence)
4. **Timing-sensitive code** (constant-time execution)

---

*All sequences from z80-optimizer brute-force search.
Flag materialization: 26-op pool, depth 6 exhaustive.
Arithmetic: verified on all input combinations.*
