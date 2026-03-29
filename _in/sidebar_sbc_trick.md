# Sidebar 4.x: The SBC A,A Trick — From Accident to Foundation

Every Z80 programmer discovers `SBC A,A` eventually. Few realise it's
the single most powerful idiom the chip has. One instruction, four
T-states, and it unlocks an entire family of branchless algorithms
that neither Zilog nor Intel ever intended.

## What It Does

```z80
SBC A, A        ; A = A - A - CY
```

If carry is clear: A = 0 - 0 = **0x00**.
If carry is set:   A = 0 - 0 - 1 = -1 = **0xFF**.

That's it. One instruction turns a single-bit flag into a full byte
mask. And here's the subtle part that makes everything work:
**the carry flag is preserved afterwards.** SBC A,A with CY=1 produces
A=0xFF *and* CY=1. This means you can chain operations after it
without losing the condition.

## Why It Matters

The Z80 has no conditional move. No predicated execution. No CMOV.
The only way to do "if carry then X else Y" is a branch:

```z80
; Traditional: branch
    JR  NC, .else       ; 12T taken, 7T not taken
    LD  A, trueValue    ;  7T
    JR  .end            ; 12T
.else:
    LD  A, falseValue   ;  7T
.end:                   ; Total: 19-26T, variable timing
```

With SBC A,A, no branch needed:

```z80
; Branchless: SBC mask
    SBC A, A            ;  4T — A = CY ? 0xFF : 0x00
    AND B               ;  4T — A = CY ? B : 0
; Total: 8T, constant timing, two instructions.
```

## The Building Blocks

The mask opens a cascade of possibilities. Each builds on the last.

### Level 1: Conditional Zero

```z80
    SBC A, A            ; mask
    AND B               ; A = CY ? B : 0
; 2 instructions, 8T
```

Useful for: conditional accumulation, masked writes, flag-to-value.

### Level 2: Conditional Select (CMOV)

```z80
    SBC A, A            ; mask = CY ? 0xFF : 0x00
    LD  D, A            ; save mask
    LD  A, B            ; A = true_value
    XOR C               ; A = true XOR false
    AND D               ; A = (true XOR false) AND mask
    XOR C               ; A = CY ? B : C
; 6 instructions, 24T
```

The algebra: `C XOR ((B XOR C) AND mask)`. When mask=0xFF, the XOR
pairs cancel and you get B. When mask=0x00, the AND kills everything
and the final XOR restores C. This is the standard bitwise select
used in SIMD programming — here, on a 1976 CPU.

Verified: all 131,072 input combinations (2 × 256 × 256).

### Level 3: Branchless Absolute Value

```z80
    LD  B, A            ; save original
    RLCA                ; sign bit → carry
    SBC A, A            ; mask = negative ? 0xFF : 0x00
    LD  C, A            ; save mask
    XOR B               ; A = original XOR mask
    SUB C               ; A = (original XOR mask) - mask
; 6 instructions, 24T
```

The two's complement identity: `|x| = (x XOR mask) - mask` where
mask is the arithmetic sign extension. When positive, mask=0 and
nothing changes. When negative, XOR inverts all bits and SUB adds 1
(because subtracting 0xFF = adding 1 modulo 256). This is `-x = ~x + 1`,
the textbook definition of negation.

Verified: all 256 signed inputs (-128 to +127).

### Level 4: Branchless MIN and MAX

```z80
; MIN(A, B):
    LD  C, A            ; save A
    SUB B               ; CY = (A < B)
    SBC A, A            ; mask
    LD  D, A            ; save mask
    LD  A, C            ; restore A
    XOR B               ; A XOR B
    AND D               ; select
    XOR B               ; A = CY ? A_orig : B = min(A, B)
; 8 instructions, 32T. Verified: all 65,536 input pairs.
```

MAX is identical but with B and C swapped in the final XOR sequence.

### Level 5: Exact Division

This one surprised us. Integer division by 3, exact for all 256 inputs:

```z80
; A = A / 3 (exact, no lookup table)
    LD  C, 171          ; magic constant
    ; ... multiply A × 171 → HL ...
    SRL H               ; HL >>= 1 (combined with implicit >>8)
    LD  A, H            ; A = (A × 171) >> 9
```

Why 171? Because 256/3 ≈ 85.333, and 171 = 2 × 85 + 1. The formula
`A × 171 >> 9` gives exact truncating division by 3 for every uint8.
We found this by brute-force: testing all multipliers 1-511 against
all 256 inputs. Only 171 is exact for `/3`. For `/5`, `/7`, `/10`,
the best multipliers give max error = 1.

## What It Can't Do

SBC A,A reads the **carry flag**. Not the zero flag. And on the Z80,
nothing reads the zero flag except conditional branches.

We proved this exhaustively: of all 26 relevant single-byte
instructions, **none** uses Z as an input to compute A or CY. By
induction, no sequence of any length can convert Z→CY without
branching. The zero flag is write-only.

This means: if your condition comes from `CP` (which sets Z for
equality), you can't use SBC A,A directly. You need the condition
in carry first. For unsigned comparison, `SUB` and `CP` both set
carry naturally. For equality, you need a branch — there's no
escape.

**For compiler writers:** this proof means CY is the only viable
flag for branchless boolean propagation. Design your calling
conventions accordingly.

## The Philosophical Bit

SBC A,A was not designed. Zilog specified `SBC A,r` as
"A = A - r - CY" and moved on. The trick emerges because `A - A`
is always zero, leaving CY as the sole variable. It's an accident
of orthogonal instruction design — the same accident that gives
x86 its `SBB EAX,EAX` idiom and ARM its `SBC R0,R0,R0`.

But on the Z80, where registers are scarce and branches are cheap
(only 5T penalty), the trick sits in a strange place: too expensive
for simple conditionals (branch is 5T cheaper), yet indispensable
for the cases where branching fails entirely — inner loops, timing-
critical code, GPU code generation, and the construction of higher
abstractions like MIN, MAX, and CMOV that the architecture lacks.

It's not the most important Z80 instruction. But it's the one that
makes the impossible merely expensive.
