# Sidebar K.5b: Multi-Accumulator Arithmetic

> *The Z80 has 144 bits of registers — enough for 4.5 simultaneous u32 accumulators. Choosing the right packing changes everything.*

## The Convention Problem

The Z80 has no 32-bit registers. For u32 arithmetic, we pack four 8-bit registers into one logical accumulator. The classic choice is **DEHL** (D:E:H:L), but it's not the only option — and not the best.

Three viable u32 conventions exist, each with dramatically different performance characteristics:

| Convention | Layout | SHL32 | ADD32 | SAVE | Key feature |
|------------|--------|-------|-------|------|-------------|
| **DEHL** | D:E:H:L | 34T | 54T | 22T | ADC HL,rr native |
| **HLIX** | H:L:IXH:IXL | 30T | 30T | 24T | DE+BC free as temp |
| **HLH'L'** | H:L:H':L' | 30T | 30T | **4T** | EXX instant swap |

**HLH'L' wins overwhelmingly** — EXX swaps three register pairs (BC↔B'C', DE↔D'E', HL↔H'L') in a single 4T instruction. Where DEHL needs 22T to save its state to the stack, HLH'L' does it in 4T. This 18T difference compounds with every multiply-by-constant operation.

## Why It Matters: ×K Decomposition

Multiplying a u32 by a constant K requires repeated doubling (SHL) with intermediate saves and additions. For `×10` (the atoi inner loop):

```
×10 = ×2 + ×8
    = (val<<1) + (val<<3)
    = SHL → SAVE → SHL → SHL → ADD
```

The cost breakdown:

| Convention | 3×SHL | 1×SAVE | 1×ADD | **Total ×10** |
|------------|-------|--------|-------|---------------|
| DEHL       | 102T  | 22T    | 54T   | **178T**      |
| HLIX       | 90T   | 24T    | 30T   | **144T**      |
| HLH'L'     | 90T   | 4T     | 30T   | **124T**      |

HLH'L' is **30% faster** than DEHL for ×10 alone. Over 10 digits of atoi, that's 540T saved.

## The HLIX×10+A Masterpiece

For the specific case of `atoi` (ASCII-to-integer), HLIX has an advantage: the digit in A can be **injected during the save step at zero extra cost**.

The hand-optimized sequence (from the Z80 community):

```z80
; HLIX = HLIX × 10 + A
; Input:  HLIX = running total, A = new digit (0-9)
; Output: HLIX = total × 10 + digit

  ADD  IX,IX      ; 15T  ┐ HLIX <<= 1
  ADC  HL,HL      ; 15T  ┘ (HLIX × 2)

  ADD  A,IXL      ;  8T  ┐
  LD   C,A        ;  4T  │ Save HLIX×2 into DEBC
  LD   A,IXH      ;  8T  │ AND inject digit A into
  ADC  A,0        ;  7T  │ low byte simultaneously!
  LD   B,A        ;  4T  │ (the +A is FREE)
  LD   A,L        ;  4T  │
  ADC  A,0        ;  7T  │
  LD   E,A        ;  4T  │
  ADC  A,H        ;  4T  │ Trick: reuse carry chain
  SUB  E          ;  4T  │ to avoid LD A,H
  LD   D,A        ;  4T  ┘

  ADD  IX,IX      ; 15T  ┐ HLIX×2 <<= 1 = HLIX×4
  ADC  HL,HL      ; 15T  ┘
  ADD  IX,IX      ; 15T  ┐ HLIX×4 <<= 1 = HLIX×8
  ADC  HL,HL      ; 15T  ┘
  ADD  IX,BC      ; 15T  ┐ HLIX×8 + HLIX×2 = HLIX×10
  ADC  HL,DE      ; 15T  ┘ (DEBC has saved ×2 + digit)
```

**19 instructions, 178T, 31 bytes.** The digit injection (`ADD A,IXL` at the start of the save phase) costs nothing because the carry propagation was happening anyway.

The `ADC A,H; SUB E` trick at lines 11-12 saves one instruction: instead of the obvious `LD A,H; ADC A,0; LD D,A`, it chains `ADC A,H` from the previous carry and subtracts the already-saved E to isolate just H+carry.

## Benchmark: 19 Constants

We benchmarked all three conventions on 19 representative multiply constants:

```
     K    DEHL    HLIX   HLH'L'  Winner
     3    116T     84T     64T   HLH'L'
     5    150T    114T     94T   HLH'L'
    10    184T    144T    124T   HLH'L'
    25    300T    228T    188T   HLH'L'
   100    368T    288T    248T   HLH'L'
  1000    542T    432T    372T   HLH'L'
 10000    726T    576T    496T   HLH'L'
```

**HLH'L' wins 14/19 cases. HLIX wins 5 (all power-of-2). DEHL wins zero.**

Average savings: **74T per multiply** vs DEHL.

## Division by Constant

For u32÷K, the multiply-and-shift trick works with 32-bit magic constants:

| ÷K | Magic M | Formula | Est. cost |
|----|---------|---------|-----------|
| ÷2 | shift | SHR32 | 28T |
| ÷10 | 0x1999999A | ×M >> 32 | ~426T |
| ÷100 | 0x028F5C29 | ×M >> 32 | ~426T |
| ÷1000 | 0x00418938 | ×M >> 32 | ~426T |

**But for itoa** (integer-to-ASCII), repeated subtraction of powers of 10 is faster:
subtract 10^9 up to 9 times (→ first digit), then 10^8, etc. Cost: SUB32 (34T) × 9 max = **306T per digit** — 28% faster than ÷10 via multiply.

## Register Budget: The Full Picture

The Z80's 18 eight-bit registers can be organized into up to 6 simultaneous accumulators:

```
Main bank:  A  B  C  D  E  H  L     (56 bits)
Shadow:     A' B' C' D' E' H' L'    (56 bits, via EXX / EX AF,AF')
Index:      IXH  IXL  IYH  IYL     (32 bits)
                                    ─────────
                                    144 bits = 4.5 × u32
```

Practical multi-accumulator configurations:

| Config | Bits | Layout | Use case |
|--------|------|--------|----------|
| 2×32 + 8 | 72 | HLIX + DEBC + A | atoi (×10+A) |
| 2×32 | 64 | HL:H'L' + DE:D'E' | bignum add |
| 3×32 | 96 | DEHL + D'E'H'L' + IX:IY | FP mul |
| 4×32 | 128 | DEHL + BCIX + D'E'H'L' + B'C'IY | SHA-256 |

For SHA-256, all four 32-bit working variables fit in registers — no RAM spills needed. This is the key to the estimated **58ms/block at 3.5MHz**.

## Recommendation for Compilers

A Z80 compiler should support all three conventions and select per-function:

1. **HLH'L'** — default for u32 arithmetic (×K, ADD, SUB)
2. **HLIX** — when A must be free (atoi, BCD) or IX/IY halves needed as 8-bit temps
3. **DEHL** — fallback for ISR code, or when IX and shadow bank are both occupied

The convention choice is a function-level decision, not a per-instruction one. Within a single function, all u32 operations should use the same packing.

---

*Data: analytical cost model from instruction timings. Individual operations (SHL32, ADD32) verified exhaustive. ×10+A sequence from Z80 community, timing confirmed. Benchmark model in `scripts/u32_mulk_search.py`. Full convention data in `data/u32_conventions.json`.*
