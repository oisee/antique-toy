# Appendix B: Sine Table Generation and Trigonometric Tables

> *"Cosine is just sine offset by a quarter period."*
> -- Raider's Commandments

---

Every demo effect that curves -- rotation, plasma, scrolling, tunnels -- needs a sine table. On the Z80, you pre-compute the values into a lookup table and index by angle. The question is how to store and access that table as efficiently as possible.

This appendix compares eight approaches to sine table storage, ranging from the obvious (256-byte table) to the exotic (2-bit second-order delta encoding). The data comes from `verify/sine_compare.py`, which you can run to reproduce every number here.

## The Standard Format

A demoscene sine table has **256 entries**, indexed by angle:

| Index | Angle |
|-------|-------|
| 0 | 0° |
| 64 | 90° |
| 128 | 180° |
| 192 | 270° |
| 256 (wraps to 0) | 360° |

Each entry is a **signed byte** (-128 to +127), representing -1.0 to approximately +1.0. The power-of-two period means the angle index wraps naturally with 8-bit overflow, and cosine becomes sine by adding 64:

```z80
; sin(angle) -- direct table lookup
    ld   h, high(sin_table)  ; 7T   table must be 256-byte aligned
    ld   l, a                ; 4T   A = angle (0-255)
    ld   a, (hl)             ; 7T   A = sin(angle)
                             ; --- 18 T-states total

; cos(angle) -- offset by quarter period
    add  a, 64               ; 7T   cos = sin + 90°
    ld   l, a                ; 4T
    ld   a, (hl)             ; 7T
```

This is Raider's key rule: store H once with the table's high byte, then L is the angle and wraps freely.

---

## Comparison of Approaches

| # | Approach | Data | Code | Total | RAM | Max Error | RMS |
|---|----------|------|------|-------|-----|-----------|-----|
| 1 | Full table (256 bytes) | 256 | 0 | **256** | 0 | 0 | 0.00 |
| 2 | Quarter-wave table | 65 | 21 | **86** | 0 | 0 | 0.00 |
| 3 | Parabolic approximation | 0 | 38 | **38** | 0 | 8 | 4.51 |
| 4 | Quarter-wave + 2nd-order deltas | 18 | 45 | **63** | 64 | 0 | 0.00 |
| 5 | Bhaskara I approximation | 0 | ~60 | **~60** | 0 | 1 | 0.49 |
| 5b | Bhaskara I + correction bitmap | 1 | ~80 | **~81** | 0 | 0 | 0.00 |
| 6 | Quarter-wave + packed 4-bit deltas | 33 | 43 | **76** | 64 | 0 | 0.00 |
| 7 | Full 2nd-order deltas, 2-bit packed | 66 | 30 | **96** | 256 | 0 | 0.00 |

The approaches fall into three categories:

- **Lookup-based** (no RAM needed): full table, quarter-wave table
- **Generation-based** (needs RAM buffer at startup): delta and second-order delta approaches
- **Approximate** (no table at all): parabolic, Bhaskara I
- **Approximate + exact correction**: Bhaskara I with correction bitmap

---

## Approach 1: Full 256-Byte Table

The simplest and fastest. Pre-compute all 256 values and embed them as data.

```z80
; Lookup: 18 T-states, zero error
    ld   h, high(sin_table)
    ld   l, a
    ld   a, (hl)
```

**Cost:** 256 bytes of ROM.
**Speed:** 18 T-states per lookup.
**When to use:** Always, unless you are size-coding. On a 48K Spectrum with ~40K free, 256 bytes is nothing. This is the default choice.

---

## Approach 2: Quarter-Wave Table

A sine wave has four-fold symmetry. The first quadrant (0° to 90°, indices 0 to 64) contains all the information:

- **Second quadrant** (65-128): mirror of first quadrant. `sin(128 - i) = sin(i)`.
- **Third quadrant** (129-192): negative of first quadrant. `sin(128 + i) = -sin(i)`.
- **Fourth quadrant** (193-255): negative mirror. `sin(256 - i) = -sin(i)`.

Store only 65 bytes (indices 0 through 64 inclusive), then reconstruct:

```z80
; Quarter-wave sine lookup
; Input:  A = angle (0-255)
; Output: A = sin(angle), signed byte
; Uses:   HL, BC
; Table:  sin_quarter (65 bytes, 256-byte aligned)
;
qsin:
    ld   c, a               ; 4T   save original angle
    and  $7F                 ; 7T   fold to 0-127 (first half)
    cp   65                  ; 7T   past the peak?
    jr   c, .no_mirror       ; 12/7T
    ; Mirror: index = 128 - index
    neg                      ; 8T
    add  a, 128              ; 7T
.no_mirror:
    ld   h, high(sin_quarter) ; 7T
    ld   l, a                ; 4T
    ld   a, (hl)             ; 7T   A = |sin(angle)|
    bit  7, c                ; 8T   was original angle >= 128?
    ret  z                   ; 11/5T  no: positive half, done
    neg                      ; 8T   yes: negate for third/fourth quadrant
    ret                      ; 10T
```

**Cost:** 65 bytes data + ~21 bytes code = **86 bytes total**.
**Speed:** ~50-70 T-states per lookup (varies by quadrant).
**Error:** Zero.
**When to use:** Size-limited demos (256-byte, 512-byte intros) where you need exact values but cannot spare 256 bytes.

---

## Approach 3: Parabolic Approximation (Dark's Method)

From Dark / X-Trade, *Spectrum Expert* #01 (1997). The idea: half a period of cosine looks like a parabola. The approximation `y ≈ 1 - 2(x/π)²` matches closely. In integer terms, each half-period is generated as a piecewise quadratic.

**Pure code, zero data.** The generation loop needs an 8×8 multiply and some accumulator logic -- approximately 38 bytes.

The error is bounded: **maximum absolute error = 8** (out of a 256-step range), or about **6.3%** of full scale. The RMS error is 4.51.

Here is where the parabola diverges from true sine (first quadrant):

```
Index  True  Para  Diff
    0     0     0    +0
    4    12    15    -3
    8    25    30    -5
   12    37    43    -6
   16    49    56    -7
   20    60    67    -7
   24    71    77    -6
   28    81    87    -6
   32    88    93    -5
```

The parabola is consistently "ahead" -- it rises faster near zero and is flatter near the peak. Maximum divergence: **8 units at index 17** (about 24°).

**When to use:** Extreme size-coding (64-byte intros, tight loaders). Plasmas, simple scrollers, and wobble effects where the eye does not distinguish exact curvature from approximate. Not suitable for smooth rotation or precise wireframe 3D.

---

## Approach 4: Second-Order Delta Encoding (The Deep Trick)

This is the most mathematically interesting approach, and by far the most compact exact representation.

### The Key Insight

The second derivative of sin(x) is -sin(x). At 8-bit integer precision, quantising to signed bytes, the second finite difference of the sine table has a remarkable property: **every value is exactly -1, 0, or +1**.

```
True sine:      [0,  3,  6,  9, 12, 16, 19, 22, 25, ...]
First diff:     [3,  3,  3,  3,  4,  3,  3,  3,  3, ...]
Second diff:    [0,  0,  0,  1, -1,  0,  0,  0,  0, ...]
```

Three values. Two bits per entry. This is not an approximation -- it is exact. The mathematical reason: `d²(sin)/dx²` is a smooth function with small magnitude, and at 256 entries per period with 8-bit amplitude, the discrete second derivative never exceeds ±1.

### Full Table via 2-Bit Second-Order Deltas

Store: initial value (1 byte), initial delta (1 byte), then 254 second-order deltas packed at 2 bits each (64 bytes). **Total: 66 bytes data + ~30 bytes decode code = 96 bytes.** Needs 256 bytes of RAM to decode into.

### Quarter-Wave via 2-Bit Second-Order Deltas

Combine with quarter-wave symmetry: store only the first 64 second-order deltas. **Total: 18 bytes data + ~45 bytes decode code = 63 bytes.** Needs 64 bytes of RAM.

This is the **smallest exact representation**: 63 bytes total for a perfect 256-entry sine table.

```z80
; Decode quarter-wave from 2-bit second-order deltas
; sin_d2_data: 16 bytes of packed 2-bit deltas (64 entries)
; sin_buffer:  64 bytes RAM for decoded quarter-wave
;
decode_quarter_d2:
    ld   hl, sin_buffer      ; destination
    ld   de, sin_d2_data     ; source (packed d2 values)
    xor  a
    ld   (hl), a             ; sin[0] = 0
    inc  hl
    ld   b, a                ; b = current delta (starts at 0)
    ld   c, 63               ; 63 more entries to decode

.loop:
    ; Unpack 2-bit d2 value
    ; 00 = 0, 01 = +1, 11 = -1 (10 unused)
    rr   (de)                ; shift out 2 bits
    rr   (de)
    ; ... (bit extraction logic)

    ; Apply: delta += d2, value += delta
    add  a, b               ; new delta
    ld   b, a
    ld   a, (hl-1)          ; previous value (pseudocode)
    add  a, b
    ld   (hl), a
    inc  hl
    dec  c
    jr   nz, .loop

    ; Now use qsin() lookup on sin_buffer
```

The decode runs once at startup. After that, use the quarter-wave lookup routine from Approach 2 on the decoded buffer.

**When to use:** Size-coded demos (128-byte, 256-byte intros) where you need exact values, can afford 64 bytes of RAM, and have a brief startup phase. The decode loop runs in under 2,000 T-states -- invisible.

> **Sidebar: Why Not 1 Bit Per Delta?**
>
> An intuitive objection: the quarter-wave sine (0° to 90°) is monotonically increasing. First differences d1 are always non-negative. In continuous maths, the second derivative of sine in the first quadrant is always negative (the curve is concave). So d2 should be ≤ 0, meaning we only need {-1, 0} -- a single bit per entry.
>
> The intuition is right for continuous sine, but wrong for quantised integer sine. At 8-bit precision, rounding creates occasional upward bumps in d1:
>
> ```
> d1:  3, 3, 3, 3, 4, 3, 3, ...  (that 4 is a rounding correction)
> d2:  0, 0, 0, +1, -1, 0, ...   (the +1 is load-bearing)
> ```
>
> There are 12 such +1 entries out of 63. If you suppress them (cap d1 to be monotonically non-increasing), the errors *accumulate*: by index 64 the peak reaches only 108 instead of 127 -- a max error of 19, worse than the parabolic approximation. Those +1 corrections carry precisely the information needed to hit the right integer values. You cannot drop them.
>
> A variable-length prefix code (0 → 1 bit, ±1 → 2 bits) saves 4 bytes of data over fixed 2-bit encoding but costs ~15 extra bytes of Z80 decode logic. Net loss. The 2-bit fixed encoding is the practical optimum.

> **Sidebar: Why Parabolic + Correction Doesn't Help**
>
> Another intuitive idea: generate a parabolic approximation (38 bytes of code, max error 8), then store a small correction table to fix it to exact values. The corrections range from -8 to +8, so they should compress well.
>
> The corrections *do* compress well -- their first differences are exactly {-1, 0, +1}, packing into 2 bits per entry. But this is no coincidence. A parabola is a quadratic with constant second derivative. So:
>
> - `d2(sin)` ∈ {-1, 0, +1} -- the sine's second derivative at integer precision
> - `d2(para)` ∈ {-1, 0, +1} -- the parabola's second derivative (nearly constant)
> - `d1(correction)` = `d1(sin) - d1(para)` ∈ {-1, 0, +1} -- **same entropy**
>
> The correction deltas have *exactly the same structure* as the direct sine d2. But the parabolic route adds 38 bytes of generation code, plus ~20 bytes to apply corrections. Total: ~96 bytes vs 63 bytes for direct d2 encoding.
>
> The parabola removes the smooth (low-frequency) component of sine -- but the 2-bit d2 encoding already handles smooth data perfectly. There is nothing left for the parabola to contribute that d2 doesn't already capture. The generation code is pure overhead.

---

## Approach 5: Bhaskara I Approximation (7th Century)

The most surprising entry in our comparison comes from 7th-century Indian mathematician Bhaskara I. His rational approximation to sine, published around 629 CE, achieves **max error of only 1 unit** at 8-bit precision -- dramatically better than the parabolic approximation (max error 8) and nearly exact.

### The Formula

For angle x in radians (0 to π):

```
sin(x) ≈ 16x(π - x) / (5π² - 4x(π - x))
```

In our integer domain (angle 0-64 for the first quadrant, amplitude 0-127):

```
sin(i) ≈ 127 × 16i(64 - i) / (5 × 64² - 4 × i(64 - i))
       = 127 × 16i(64 - i) / (20480 - 4i(64 - i))
```

The formula is a ratio of two quadratics. On the Z80 this needs an 8×8 multiply and a 16-bit division -- routines that many demos already include for 3D projection or texture mapping.

### Accuracy

Across the 65 entries of the first quadrant, Bhaskara I matches the exact integer sine everywhere except **8 positions** (out of 65), where it is off by exactly ±1:

```
Index  True  Bhaskara  Diff
    4    12        13    -1
   17    51        52    -1
   28    81        80    +1
   31    88        87    +1
   40   106       105    +1
   43   111       110    +1
   50   120       119    +1
   52   122       121    +1
```

Only 8 positions differ, all by exactly ±1. The errors are split: 2 entries where Bhaskara overshoots (near the start), 6 where it undershoots (near the peak). Eight corrections total, which encode as a single byte bitmap.

### Z80 Implementation

The implementation requires:
- An 8×8→16 multiply routine (~20 bytes, likely already available)
- A 16÷16→16 divide routine (~30 bytes, likely already available)
- The Bhaskara wrapper itself (~25 bytes)
- Quarter-wave folding logic (~15 bytes, shared with Approach 2)

If your demo already has multiply and divide routines, the marginal cost is roughly **25 bytes** for a sine function with max error 1.

If you need the routines from scratch, total is approximately **60 bytes** of code with zero data bytes. This is competitive with the d2 delta approach (63 bytes) but requires no RAM buffer and no startup decode phase. The tradeoff: 1 unit of error vs perfect accuracy.

### Bhaskara I + Correction Bitmap (Exact)

To eliminate that last unit of error, store the 8 correction positions as a bitmap. Since the corrections are symmetric (first 4 need +1, last 4 need -1), one byte suffices:

```z80
; After computing Bhaskara approximation in A, index in C:
    push af
    ld   a, c
    ; Look up correction from bitmap (8 specific indices)
    ; ... (~20 bytes of correction logic)
    pop  af
    add  a, correction      ; ±1 or 0
```

Total: ~80 bytes code + 1 byte data = **~81 bytes**, zero RAM, zero startup, exact values. More expensive than d2 deltas (63B) but avoids the RAM buffer and startup decode.

### When to Use Bhaskara I

- **You already have multiply/divide routines:** ~25 bytes extra, max error 1. Hard to beat.
- **No RAM available for decode buffer:** Unlike d2 deltas, Bhaskara computes on the fly.
- **Real-time generation needed:** Each value is computed independently -- no sequential dependency, so you can compute sin(any angle) without decoding a table first.
- **±1 error is acceptable:** For scrollers, plasmas, and most visual effects, the difference between max error 1 and max error 0 is literally invisible.

> **Historical Note:** Bhaskara I's formula predates European trigonometric tables by nearly a millennium. That a 7th-century rational approximation achieves max error 1 on a 1980s 8-bit processor is a beautiful collision of mathematical elegance and engineering constraints. The formula was published in *Mahabhaskariya* (629 CE), a commentary on Aryabhata's astronomical methods.

---

## Practical Recommendations

Every generation-based approach produces a lookup table at startup. After that, the runtime cost is identical: `LD H, high(table) / LD L, A / LD A, (HL)` = **18 T-states** for a 256-byte table, or the quarter-wave folding routine at **50-70 T-states** for a 64-byte buffer. The "ROM cost" column below is what matters for size-coding -- it is the total bytes your approach occupies in the binary.

| Use Case | Approach | ROM Cost | RAM | Init | Lookup | Error |
|----------|----------|----------|-----|------|--------|-------|
| **Normal demo / game** | Full 256-byte table | 256B | 0 | none | 18 T | exact |
| **512-byte intro** | Quarter-wave table | 86B | 0 | none | 50-70 T | exact |
| **256-byte intro** | Quarter + d2 deltas | 63B | 64B | ~2K T | 50-70 T | exact |
| **Has multiply/divide** | Bhaskara I (generate to LUT) | ~25B extra | 256B | ~80K T | 18 T | ±1 max |
| **128-byte intro** | Parabolic (generate to LUT) | 38B | 256B | ~10K T | 18 T | ±8 max |

### The Decision Tree

1. **Do you have 256 bytes to spare?** Use the full table. Do not overthink it. `LD L,A / LD A,(HL)` at 18 T-states cannot be beaten.

2. **Size-limited but need accuracy?** Quarter-wave table at 86 bytes. No RAM needed, no startup phase. Lookup is 50-70 T-states (the folding logic).

3. **Extreme size limit, exact values needed?** Quarter-wave + second-order delta decoding at 63 bytes. Decode once at startup into a 64-byte quarter buffer, then use the same folding lookup.

4. **Already have multiply/divide?** Bhaskara I at ~25 bytes extra. Generate a full 256-byte LUT at startup, then enjoy 18 T-state lookups with max error 1.

5. **Extreme size limit, approximate OK?** Parabolic at 38 bytes, zero data. Generate to a 256-byte LUT at startup. Max error 8, good for plasmas and wobbles.

### What Does Not Work

- **Parabolic + correction table** (123 bytes exact): worse than just using a quarter-wave table (86 bytes). The overhead of computing the parabola *and* looking up a correction defeats the purpose.

- **Delta + RLE** (100-219 bytes): sine deltas vary smoothly rather than repeating in runs. RLE is designed for data with long constant runs -- sine is the wrong shape for it.

- **Full delta-encoded table** (152-271 bytes): uses *more* total bytes than the raw 256-byte table. Delta encoding only helps when deltas are significantly smaller than the original values; sine deltas are already bounded to ±4, but you still need 256 of them.

---

## Raider's Commandments

In the Hype comments on Introspec's analysis of *Illusion*, veteran coder Raider distilled decades of collective wisdom into informal "commandments" for sine table design:

1. **256 entries per full period.** The angle index wraps with 8-bit overflow. No modular arithmetic needed.
2. **Signed bytes: -128 to +127.** Matches Z80 signed arithmetic.
3. **Page-align the table.** Place it at a 256-byte boundary so H is constant. `LD H,high(table)` once, then `LD L,angle / LD A,(HL)` forever.
4. **Cosine is sine + 64.** One `ADD A,64` instruction.
5. **Sine of (angle + 128) = -sine(angle).** `NEG` flips the sign. Use this for phase shifts.
6. **Do not compute sine at runtime** unless you are size-coding. A table lookup is always faster.
7. **Keep the amplitude as a power of two** (64, 127, 128) so multiplication is a shift.
8. **Quarter-wave symmetry** saves 75% storage when every byte matters.
9. **Test at the boundaries.** Index 0 should be exactly 0. Index 64 should be the maximum positive value (+127). Index 128 should be exactly 0. Index 192 should be the maximum negative value (-128 or -127, depending on your convention).

These rules reflect decades of experience. Follow them and your sine tables will be fast, small, and correct.

---

## Reference: The Full 256-Byte Table

For convenience, here is the standard sine table (256 entries, signed, period = 256, amplitude ±127):

```z80
; 256-byte sine table, page-aligned
; sin(0) = 0, sin(64) = +127, sin(128) = 0, sin(192) = -128
;
    ALIGN 256
sin_table:
    DB    0,   3,   6,   9,  12,  16,  19,  22
    DB   25,  28,  31,  34,  37,  40,  43,  46
    DB   49,  51,  54,  57,  60,  63,  65,  68
    DB   71,  73,  76,  78,  81,  83,  85,  88
    DB   90,  92,  94,  96,  98, 100, 102, 104
    DB  106, 108, 109, 111, 112, 114, 115, 117
    DB  118, 119, 120, 121, 122, 123, 124, 124
    DB  125, 126, 126, 127, 127, 127, 127, 127
    DB  127, 127, 127, 127, 127, 127, 126, 126
    DB  125, 124, 124, 123, 122, 121, 120, 119
    DB  118, 117, 115, 114, 112, 111, 109, 108
    DB  106, 104, 102, 100,  98,  96,  94,  92
    DB   90,  88,  85,  83,  81,  78,  76,  73
    DB   71,  68,  65,  63,  60,  57,  54,  51
    DB   49,  46,  43,  40,  37,  34,  31,  28
    DB   25,  22,  19,  16,  12,   9,   6,   3
    DB    0,  -3,  -6,  -9, -12, -16, -19, -22
    DB  -25, -28, -31, -34, -37, -40, -43, -46
    DB  -49, -51, -54, -57, -60, -63, -65, -68
    DB  -71, -73, -76, -78, -81, -83, -85, -88
    DB  -90, -92, -94, -96, -98,-100,-102,-104
    DB -106,-108,-109,-111,-112,-114,-115,-117
    DB -118,-119,-120,-121,-122,-123,-124,-124
    DB -125,-126,-126,-127,-127,-127,-127,-127
    DB -128,-127,-127,-127,-127,-127,-126,-126
    DB -125,-124,-124,-123,-122,-121,-120,-119
    DB -118,-117,-115,-114,-112,-111,-109,-108
    DB -106,-104,-102,-100, -98, -96, -94, -92
    DB  -90, -88, -85, -83, -81, -78, -76, -73
    DB  -71, -68, -65, -63, -60, -57, -54, -51
    DB  -49, -46, -43, -40, -37, -34, -31, -28
    DB  -25, -22, -19, -16, -12,  -9,  -6,  -3
```

Copy, paste, assemble, use.

---

> **Sources:** Dark / X-Trade "Programming Algorithms" (Spectrum Expert #01, 1997) for the parabolic approximation; Bhaskara I, *Mahabhaskariya* (629 CE) for the rational approximation; Raider (Hype comments, 2017) for sine table design principles; `verify/sine_compare.py` for comparative analysis
