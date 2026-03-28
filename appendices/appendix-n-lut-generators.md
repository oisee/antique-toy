# Appendix N: LUT Generators — Compressing Tables into Programs

> *256 bytes of sqrt in ROM, or 12 bytes of code that computes it. The GPU found the code.*

---

## N.1 The Idea

A 256-byte lookup table stores one output for each possible input byte. A LUT generator is a short instruction sequence that *computes* the same mapping, generating the table at startup instead of storing it in ROM. The GPU superoptimizer searches for the shortest sequence whose output matches the target table to within acceptable error.

**Compression ratio: 20:1.** A 12-byte program replaces a 256-byte table. The "decompressor" is the CPU itself.

---

## N.2 Depth-11 Results

Each "compound operation" maps to 1--3 Z80 instructions (2--6 bytes). Searches at depth-11 (11 compound operations, ~22 bytes Z80 code):

### Exact Matches (zero errors)

| Function | Compound Ops | Description |
|----------|-------------|-------------|
| gray\_encode | 3 | `SAVE SHR XOR_B` --- Gray code: n XOR (n>>1) |
| gray\_decode | 13 | Exact inverse Gray code --- found via focused search on Vulkan RX 580 in <1 second |
| is\_pow2 | 7 | Via carry trick: `NEG SAVE NEG XOR_B SUB_B SBC_MASK NEG` |

### Good Approximations (>90% accuracy)

| Function | Max Error | Accuracy | Compound Ops | Key Trick |
|----------|-----------|----------|-------------|-----------|
| sqrt (f3.5) | ±10 | 92.2% | 5 | `SHR RLCA XOR_B RRCA MUL7` |
| bin→bcd | ±17 | 93.3% | 5 | `MUL3 MUL5 SBC_MASK` |
| sqrt (f4.4) | ±21 | 91.8% | 5 | `MUL5 RLCA XOR_B` |
| log2 (f4.4) | ±23 | 91.0% | 5 | `SUB_B MUL3 SUB_B` |
| cbrt (f2.6) | ±24 | 90.6% | 5 | `NEG AND_F0 NEG MUL3` |

### Medium Accuracy (>85%)

| Function | Max Error | Accuracy | Compound Ops |
|----------|-----------|----------|-------------|
| recip (256/x) | ±31 | 87.8% | 6 |
| log2 (f3.5) | ±36 | 85.9% | 5 |

### The Focused Search Breakthrough

The key insight from extended searches: **smaller operation pools enable deeper searches that find better results**. Instead of depth-12 with the full 33-op pool, focused searches with minimal pools (6--8 ops) reach depth-16+ and find exact solutions:

| Function | Strategy | Depth | Pool Size | Result |
|----------|----------|-------|-----------|--------|
| gray\_decode | Focused | 13 | 8 ops | **EXACT** (was ±3) |
| sqr\_hi (x²>>8) | Focused | 16 | 6 ops | ±29 |
| cbrt (f2.6) | Focused | 13 | 8 ops | ±16 (was ±24) |
| sin\_q1 | Focused | 15 | 6 ops | ±68 |

The gray\_decode result is striking: depth-11 with 33 ops gave ±3 error; depth-13 with 8 ops gave **zero error**. Fewer ops → deeper search → exact solution. The operation pool is the primary knob for trading breadth against depth.

---

## N.3 How It Works

Each compound operation is a macro that expands to 1--3 Z80 instructions:

| Compound Op | Z80 Expansion | T-states |
|-------------|--------------|----------|
| `SHR` | `SRL A` | 8T |
| `RLCA` | `RLCA` | 4T |
| `RRCA` | `RRCA` | 4T |
| `XOR_B` | `XOR B` | 4T |
| `ADD_B` | `ADD A,B` | 4T |
| `SUB_B` | `SUB B` | 4T |
| `MUL3` | `LD B,A : ADD A,A : ADD A,B` | 12T |
| `MUL5` | `LD B,A : ADD A,A : ADD A,A : ADD A,B` | 16T |
| `MUL7` | `LD B,A : ADD A,A : ADD A,B : ADD A,A : ADD A,B` | 20T |
| `SAVE` | `LD B,A` | 4T |
| `NEG` | `NEG` | 8T |
| `SBC_MASK` | `SBC A,A` | 4T |
| `AND_F0` | `AND $F0` | 7T |

The search enumerates all sequences of compound ops up to depth N, executes each on all 256 inputs, and compares against the target table. QuickCheck (4 inputs) rejects 99.99% instantly; survivors get full 256-input verification.

---

## N.4 The Rotation Dominance

`RRCA` (rotate right circular) appears at **276% frequency** across approximation sequences --- the average sequence uses it 2.76 times. Why?

Rotations are the mechanism by which linear arithmetic "sees" individual bits. After `RRCA`, the MSB contains what was previously the LSB. A subsequent `ADD A,A` produces a value that mixes low and high bit-fields --- something no sequence of pure additions can achieve. This mixing is exactly what nonlinear functions (sqrt, log2) require.

The rotation-addition pair is the minimal nonlinear basis for bit-level computation on the Z80 --- the equivalent of the butterfly operation in an FFT.

---

## N.5 Practical Use: Runtime Table Generation

```z80
; Generate 256-byte sqrt table (f4.4 format) at startup
; Approximation: sqrt(f4.4) via MUL5 RLCA XOR_B — ±21, 91.8%
; Table at sqrt_lut (256 bytes)
generate_sqrt:
    LD   HL, sqrt_lut
    XOR  A               ; start with input = 0
.loop:
    PUSH AF
    ; --- approximation sequence ---
    LD   B, A
    ADD  A, A             ; ×2
    ADD  A, A             ; ×4
    ADD  A, B             ; ×5
    RLCA                  ; rotate left
    XOR  B                ; mix bits
    ; --- end sequence ---
    LD   (HL), A          ; store result
    INC  HL
    POP  AF
    INC  A
    JR   NZ, .loop
    RET                   ; 256 iterations, ~20 bytes code
                          ; replaces 256 bytes ROM table
```

**Trade-off:** ~6,000 T-states startup cost (256 iterations × ~24T each) to save 256 bytes of ROM. For a demo that runs millions of frames, this is negligible.

---

## N.6 The Error-Depth Tradeoff

Each additional compound operation reduces maximum error by approximately **30%:**

| Depth | sqrt Max Error | Accuracy |
|-------|---------------|----------|
| 3 | ±45 | 82% |
| 5 | ±21 | 91.8% |
| 7 | ~±14 | ~94% |
| 9 | ~±10 | ~96% |
| 11 | ~±7 | ~97% |

The curve suggests diminishing returns past depth 9--10 for most functions when using the full operation pool. However, focused searches with minimal pools can push far deeper --- gray\_decode went from ±3 at depth-11/33-ops to EXACT at depth-13/8-ops.

**The practical ceiling is pool-dependent, not depth-dependent.** This is the key design insight for future LUT generator searches.

---

*Results from z80-optimizer v1.0.0 (3× GPU: RTX 4060 Ti × 2 + RTX 2070 + Vulkan RX 580). Depth-11 broad + focused searches to depth-16.*
