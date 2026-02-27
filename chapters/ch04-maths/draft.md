# Chapter 4: The Maths You Actually Need

> *"Read a maths textbook -- derivatives, integrals. You will need them."*
> -- Dark, Spectrum Expert #01 (1997)

In 1997, a teenager in St. Petersburg sat down to write a magazine article about multiplication. Not the kind you learn in school -- the kind that makes a wireframe cube spin on a ZX Spectrum at 50 frames per second. His name was Dark, he coded for the group X-Trade, and his demo *Illusion* had already won first place at ENLiGHT'96. Now he was writing *Spectrum Expert*, an electronic magazine distributed on floppy disk, and he was going to explain exactly how his algorithms worked.

What follows is drawn directly from Dark's "Programming Algorithms" article in Spectrum Expert #01. These are the routines that powered *Illusion* -- the same multiply that rotated vertices, the same sine table that drove the rotozoomer, the same line drawer that rendered wireframes at full frame rate. When Introspec reverse-engineered *Illusion* twenty years later on the Hype blog, he found these exact algorithms at work inside the binary.

---

## Multiplication on Z80

The Z80 has no multiply instruction. Every time you need A times B -- for rotation matrices, perspective projection, texture mapping -- you must synthesize it from shifts and adds. Dark presents two methods, and he is characteristically honest about the trade-off between them.

### Method 1: Shift-and-Add from LSB

The classic approach. Scan through the bits of the multiplier from LSB to MSB. For each set bit, add the multiplicand into an accumulator. After each bit, shift the accumulator right. After eight iterations, the accumulator holds the full product.

Here is Dark's 8x8 unsigned multiply. Input: B times C. Result in A (high byte) and C (low byte):

```z80 id:ch04_method_1_shift_and_add_from
; MULU112 -- 8x8 unsigned multiply
; Input:  B = multiplicand, C = multiplier
; Output: A:C = B * C (16-bit result, A=high, C=low)
; Cost:   196-204 T-states (Pentagon)
;
; From Dark / X-Trade, Spectrum Expert #01 (1997)

mulu112:
    ld   a, 0           ; clear accumulator (high byte of result)
    ld   d, 8           ; 8 bits to process

.loop:
    rr   c              ; shift LSB of multiplier into carry
    jr   nc, .noadd     ; if bit was 0, skip addition
    add  a, b           ; add multiplicand to accumulator
.noadd:
    rra                 ; shift accumulator right (carry into bit 7,
                        ;   bit 0 into carry -- this carry feeds
                        ;   back into C via the next RR C)
    dec  d
    jr   nz, .loop
    ret
```

Study this carefully. The `RRA` instruction shifts A right, but also pushes A's lowest bit into the carry flag. On the next iteration, `RR C` rotates that carry into the top of C. So the low bits of the product gradually assemble in C, while the high bits accumulate in A. After eight iterations, the full 16-bit result sits in A:C.

The cost is 196 to 204 T-states depending on how many multiplier bits are set -- each set bit costs one extra `ADD A,B` (4 T-states). The example at `chapters/ch04-maths/examples/multiply8.a80` shows a variant returning the result in HL.

<!-- Screenshot removed: result is border colour only, not capturable as static image -->

For 16x16 producing a 32-bit result, Dark's MULU224 runs in 730 to 826 T-states. In practice, demoscene 3D engines avoid full 16x16 multiplies by keeping coordinates in 8.8 fixed-point and using 8x8 multiplies where possible.

<!-- figure: ch04_multiply_walkthrough -->
![Shift-and-add 8x8 multiply walkthrough](illustrations/output/ch04_multiply_walkthrough.png)

### Method 2: Square Table Lookup

Dark's second method trades memory for speed, exploiting an algebraic identity that every demoscener eventually discovers:

```text
A * B = ((A+B)^2 - (A-B)^2) / 4
```

Pre-compute a table of n^2/4 values, and multiplication becomes two lookups and a subtraction -- approximately 61 T-states, more than three times faster than shift-and-add.

You need a 512-byte table of (n^2/4) for n = 0 to 511, page-aligned for single-register indexing. The table must be 512 bytes because (A+B) can reach 510.

```z80 id:ch04_method_2_square_table_lookup_2
; MULU_FAST -- Square table multiply
; Input:  B, C = unsigned 8-bit factors
; Output: HL = B * C (16-bit result)
; Cost:   ~61 T-states (Pentagon)
; Requires: sq_table = 512-byte table of n^2/4, page-aligned
;
; A*B = ((A+B)^2 - (A-B)^2) / 4

mulu_fast:
    ld   h, sq_table >> 8  ; high byte of table address
    ld   a, b
    add  a, c              ; A = B + C (may overflow into carry)
    ld   l, a
    ld   e, (hl)           ; look up (B+C)^2/4 low byte
    inc  h
    ld   d, (hl)           ; look up (B+C)^2/4 high byte

    ld   a, b
    sub  c                 ; A = B - C (may go negative)
    jr   nc, .pos
    neg                    ; take absolute value
.pos:
    ld   l, a
    dec  h
    ld   a, e
    sub  (hl)              ; subtract (B-C)^2/4 low byte
    ld   e, a
    inc  h
    ld   a, d
    sbc  a, (hl)           ; subtract (B-C)^2/4 high byte
    ld   d, a

    ex   de, hl            ; HL = result
    ret
```

The trade-off? Dark is characteristically honest: **"Choose: speed or accuracy."** The table stores integer values of n^2/4, so there is a rounding error of up to 0.25 per lookup. For large values this is negligible. For the small coordinate deltas in 3D rotation, the error produces visible vertex jitter. With shift-and-add, the rotation is perfectly smooth.

For texture mapping, plasma, scrollers -- use the fast multiply. For wireframe 3D where the eye tracks individual vertices -- stick with shift-and-add. Dark knew this because he had tried both in *Illusion*.

**Generating the square table** is a one-time startup cost. Dark suggests using the derivative method: since d(x^2)/dx = 2x, you can build the table incrementally by adding a linearly increasing delta at each step. In practice, most coders compute the table in a BASIC loader or initialisation routine and move on.

---

## Signed Multiply

A chapter that teaches unsigned multiplication and then uses it to rotate 3D coordinates has a gap: rotation matrices operate on signed values. X can be -40 or +40, sine values range from -128 to +127. Every `call mul_signed` in Chapter 5 depends on the routine you are about to see. As Ped7g put it during his review: "a chapter that teaches 3D rotation without showing signed multiply is like a cookbook that lists ingredients but forgets the oven."

### Two's Complement in Practice

The Z80 represents signed integers in two's complement. The rules are simple:

- Bit 7 is the sign bit: 0 = positive, 1 = negative
- Positive values are the same as unsigned: $00 = 0, $01 = 1, ..., $7F = 127
- Negative values count down from $FF: $FF = -1, $FE = -2, ..., $80 = -128
- `NEG` computes the absolute value of a negative number (negate A: A = 0 - A). Cost: 8T

The critical insight for arithmetic: **ADD and SUB do not care about signedness.** Adding $FF (-1) to $03 (+3) gives $02 (+2) --- correct in both signed and unsigned interpretation. The hardware addition is identical. Only multiplication requires explicit sign handling, because the shift-and-add loop treats the multiplier bits as unsigned positional values.

### Sign Extension: The `rla / sbc a,a` Idiom

When you multiply an 8-bit signed value by another 8-bit signed value, you need to know the signs. The cheapest way to extract the sign bit on the Z80:

```z80
; Sign extension: A → D (0 if positive, $FF if negative)
; Cost: 8T, 2 bytes. Branchless.
    rla                 ; 4T  rotate sign bit into carry
    sbc  a, a           ; 4T  A = 0 if carry clear, $FF if set
```

After `sbc a,a`, A is $00 for positive inputs or $FF for negative inputs. This is the standard sign-extension byte used across the Z80 demoscene.

### `mul_signed` --- Signed 8×8 Multiply

The algorithm: XOR the two inputs to determine the result sign, take absolute values, multiply unsigned, negate the result if the sign was negative. This is the routine that Chapter 5 calls six times per vertex rotation and twice per backface cull.

```z80 id:ch04_mul_signed
; mul_signed — 8x8 signed multiply
; Input:  B = signed multiplicand, C = signed multiplier
; Output: HL = signed 16-bit result
; Cost:   ~240-260 T-states (Pentagon)
;
; Algorithm: determine sign, abs both, unsigned multiply, negate if needed.

mul_signed:
    ld   a, b
    xor  c               ; 4T  bit 7 = result sign (1 = negative)
    push af              ; 11T save sign flag

    ; Absolute value of B
    ld   a, b
    or   a
    jp   p, .b_pos       ; 10T skip if positive
    neg                  ; 8T  A = |B|
.b_pos:
    ld   b, a

    ; Absolute value of C
    ld   a, c
    or   a
    jp   p, .c_pos
    neg
.c_pos:
    ld   c, a

    ; Unsigned 8x8 multiply: B * C -> A:C (high:low)
    ld   a, 0
    ld   d, 8
.mul_loop:
    rr   c
    jr   nc, .noadd
    add  a, b
.noadd:
    rra
    dec  d
    jr   nz, .mul_loop

    ; A:C = unsigned product. Move to HL.
    ld   h, a
    ld   l, c

    ; Negate result if sign was negative
    pop  af              ; 10T recover sign
    or   a
    jp   p, .done        ; 10T skip if positive
    ; Negate HL: HL = 0 - HL
    xor  a
    sub  l
    ld   l, a
    sbc  a, a
    sub  h
    ld   h, a
.done:
    ret
```

The core is the same shift-and-add loop from `mulu112`, wrapped with sign detection and conditional negation. The overhead is ~40-60 T-states beyond the unsigned multiply, depending on how many operands need negation.

### `mul_signed_c` --- Thin Wrapper for Backface Culling

Chapter 5's backface culling passes the first operand in A rather than B. A thin wrapper avoids restructuring the caller:

```z80 id:ch04_mul_signed_c
; mul_signed_c — signed multiply with A,C inputs
; Input:  A = signed multiplicand, C = signed multiplier
; Output: HL = signed 16-bit result
; Cost:   ~250-270 T-states (Pentagon)

mul_signed_c:
    ld   b, a            ; 4T
    jr   mul_signed      ; 12T  fall through to mul_signed
```

### Cost Comparison

| Routine | Input | Result | T-states | Notes |
|---------|-------|--------|----------|-------|
| `mulu112` (unsigned) | B, C | A:C (16-bit) | 196--204 | Chapter 4 shift-and-add |
| `mulu_fast` (square table) | B, C | HL (16-bit) | ~61 | Needs 512-byte table; rounding error |
| `mul_signed` | B, C (signed) | HL (signed 16-bit) | ~240--260 | Sign handling adds ~40--60T |
| `mul_signed_c` | A, C (signed) | HL (signed 16-bit) | ~250--270 | Wrapper for backface culling |

The signed multiply is roughly 25% more expensive than unsigned. For a wireframe cube with 8 vertices and 6 multiplies per axis rotation (12 total per full 3D rotation), the per-vertex cost is ~3,120 T-states --- still comfortably within the frame budget.

The rotation matrices in Chapter 5 call `mul_signed` six times per vertex for Z-axis and perspective, and `mul_signed_c` twice per face for backface culling. Now you know exactly what those calls do.

> **Credit:** The signed arithmetic gap was identified by Ped7g (Peter Helcmanovsky) during his review of the book.

---

## Division on Z80

Division on the Z80 is even more painful than multiplication. No divide instruction, and the algorithm is inherently serial -- each quotient bit depends on the previous subtraction. Dark again presents two methods: accurate and fast.

### Method 1: Shift-and-Subtract (Restoring Division)

Binary long division. Start with a zeroed accumulator. The dividend shifts in from the right, one bit per iteration. Try subtracting the divisor; if it succeeds, set a quotient bit. If it fails, restore the accumulator -- hence "restoring division."

```z80 id:ch04_method_1_shift_and_subtract
; DIVU111 -- 8-bit unsigned divide
; Input:  B = dividend, C = divisor
; Output: B = quotient, A = remainder
; Cost:   236-244 T-states (Pentagon)
;
; From Dark / X-Trade, Spectrum Expert #01 (1997)

divu111:
    xor  a               ; clear accumulator (remainder workspace)
    ld   d, 8            ; 8 bits to process

.loop:
    sla  b               ; shift dividend left -- MSB into carry
    rla                  ; shift carry into accumulator
    cp   c               ; try to subtract divisor
    jr   c, .too_small   ; if accumulator < divisor, skip
    sub  c               ; subtract divisor from accumulator
    inc  b               ; set bit 0 of quotient (B was just shifted,
                         ;   so bit 0 is free)
.too_small:
    dec  d
    jr   nz, .loop
    ret                  ; B = quotient, A = remainder
```

The `INC B` to set the quotient bit is a neat trick: B was just shifted left by `SLA B`, so bit 0 is guaranteed zero. `INC B` sets it without affecting other bits -- cheaper than `OR` or `SET`.

The 16-bit version (DIVU222) costs 938 to 1034 T-states. A thousand T-states for a single divide. With a frame budget of ~70,000 T-states, you can afford perhaps 70 divides per frame -- doing nothing else. This is why demoscene 3D engines go to extreme lengths to avoid division.

### Method 2: Logarithmic Division

Dark's faster alternative uses logarithm tables:

```text
Log(A / B) = Log(A) - Log(B)
A / B = AntiLog(Log(A) - Log(B))
```

With two 256-byte lookup tables -- Log and AntiLog -- division becomes two lookups, a subtraction, and a third lookup. Cost drops to roughly 50-70 T-states. For perspective division (dividing by Z to project 3D points onto screen), this is a game-changer.

**Generating the log table** is where things get interesting. Dark proposes building it using derivatives -- the same incremental technique as the square table. The derivative of log2(x) is 1/(x * ln(2)), so you accumulate fractional increments step by step, starting from log2(1) = 0 and working upward. The constant 1/ln(2) = 1.4427 needs to be scaled to fit the table's 8-bit range.

And here is where Dark's honesty shines through. After deriving the generation formula, he attempts to compute a correction coefficient for the table scaling and arrives at 0.4606. He then writes -- in a published magazine article -- *"Something is not right here, so it is recommended to write a similar one yourself."*

A seventeen-year-old in 1997, publishing in a disk magazine read by his peers across the Russian Spectrum scene, openly saying: I got this working, but my derivation has a hole in it, figure out the clean version yourself. That honesty is rare in technical writing at any level, and it is one of the things that makes Spectrum Expert such a remarkable document.

In practice, the log tables work. Rounding errors from compressing a continuous function into 256 bytes are acceptable for perspective projection. Dark's 3D engine in *Illusion* uses exactly this technique.

---

## Sine and Cosine

Rotation, scrolling, plasma -- every effect that curves needs trigonometry. On the Z80, you pre-compute a lookup table. Dark's approach is beautifully pragmatic: a parabola is close enough to a sine wave for demo work.

### The Parabolic Approximation

Half a period of cosine, from 0 to pi, curves from +1 down to -1. A parabola y = 1 - 2*(x/pi)^2 follows almost the same path. Maximum error is about 5.6% -- terrible for engineering, invisible in a demo at 256x192 resolution.

Dark generates a 256-byte signed cosine table (-128 to +127), indexed by angle: 0 = 0 degrees, 64 = 90 degrees, 128 = 180 degrees, 256 wraps to 0. The power-of-two period means the angle index wraps naturally with 8-bit overflow, and cosine becomes sine by adding 64.

```z80 id:ch04_the_parabolic_approximation
; Generate 256-byte signed cosine table (-128..+127)
; using parabolic approximation
;
; The table covers one full period: cos(n * 2*pi/256)
; scaled to signed 8-bit range.
;
; Approach: for the first half (0..127), compute
;   y = 127 - (x^2 * 255 / 128^2)
; approximated via incrementing differences.
; Mirror for second half.

gen_cos_table:
    ld   hl, cos_table
    ld   b, 0              ; x = 0
    ld   de, 0             ; running delta (fixed-point)

    ; First quarter: cos descends from +127 to 0
    ; Second quarter: continues to -128
    ; ...build via incremental squared differences

    ; In practice, the generation loop runs ~30 bytes
    ; and produces the table in a few hundred cycles.
```

The key insight: you do not need to compute x^2 for each entry. Since (x+1)^2 - x^2 = 2x + 1, you build the parabola incrementally -- start at the peak, subtract a linearly increasing delta. No multiplication, no division, no floating point.

The resulting table is a piecewise parabolic approximation. Plot it against true sine and you will struggle to see the difference. For wireframe 3D or a bouncing scroller, it is more than good enough.

> **Sidebar: Raider's 9 Commandments of Sine Tables**
>
> In the Hype comments on Introspec's analysis of *Illusion*, veteran coder Raider dropped a list of rules for sine table design that became informally known as the "9 commandments." The key principles:
>
> - Use a power-of-two table size (256 entries is canonical).
> - Align the table to a page boundary so `H` holds the base and `L` is the raw angle -- indexing is free.
> - Store signed values for direct use in coordinate arithmetic.
> - Let the angle wrap naturally via 8-bit overflow -- no bounds checking.
> - Cosine is just sine offset by a quarter period: load angle, add 64, look up.
> - If you need higher precision, use a 16-bit table (512 bytes) but you rarely do.
> - Generate the table at startup rather than storing it in the binary -- saves space, costs nothing.
> - For 3D rotation, pre-multiply by your scaling factor and store the scaled values.
> - Never compute trigonometry at runtime. If you think you need to, you are wrong.
>
> These commandments reflect decades of collective experience. Follow them and your sine tables will be fast, small, and correct.

---

## Bresenham's Line Drawing

Every edge of a wireframe object is a line from (x1,y1) to (x2,y2), and you need to draw it fast. Dark's treatment in Spectrum Expert #01 is the longest section of his article, working through three progressively faster approaches.

### The Classic Algorithm and Xopha Modification

Bresenham's algorithm steps along the major axis one pixel at a time, maintaining an error accumulator for minor-axis steps. On the Spectrum, "set a pixel" is expensive -- the interleaved screen memory means computing a byte address and bit position costs real T-states. The ROM routine takes over 1000 T-states per pixel. Even a hand-optimised Bresenham loop costs ~80 T-states per pixel.

Dark mentions Xopha's improvement: maintain a screen pointer (HL) and advance it incrementally rather than recomputing from scratch. Moving right means rotating a bit mask; moving down means the multi-instruction DOWN_HL adjustment. Better, but the core problem remains.

### Dark's Matrix Method: 8x8 Pixel Grids

Then Dark makes his key observation: **"87.5% of checks are wasted."**

In a Bresenham loop, at every pixel you ask: should I step sideways? For a nearly horizontal line, the answer is almost always no. On average, seven out of eight checks produce no side-step. You are burning T-states on a conditional branch that almost never fires.

Dark's solution: pre-compute the pixel pattern for each line slope within an 8x8 pixel grid, and unroll the drawing loop to output entire grid cells at once. A line segment within an 8x8 area is fully determined by its slope. For each of the eight octants, enumerate all possible 8-pixel patterns as straight sequences of `SET bit,(HL)` instructions with address increments between them.

```z80 id:ch04_dark_s_matrix_method_8x8
; Example: one unrolled 8-pixel segment of a nearly-horizontal line
; (octant 0: moving right, gently sloping down)
;
; The line enters at the left edge of an 8x8 character cell
; and exits at the right edge, dropping one pixel row partway through.

    set  7, (hl)        ; pixel 0 (leftmost bit in byte)
    set  6, (hl)        ; pixel 1
    set  5, (hl)        ; pixel 2
    set  4, (hl)        ; pixel 3
    set  3, (hl)        ; pixel 4
    ; --- step down one pixel row ---
    inc  h              ; next screen row (within character cell)
    set  2, (hl)        ; pixel 5
    set  1, (hl)        ; pixel 6
    set  0, (hl)        ; pixel 7 (rightmost bit in byte)
```

No conditional branches. No error accumulator. `SET bit,(HL)` takes 15 T-states; eight of them plus a couple of `INC H` operations gives ~130 T-states per 8-pixel segment, or about 16 T-states per pixel. With lookup and cell-advance overhead, Dark achieves approximately **48 T-states per pixel** -- nearly half the classical Bresenham cost.

The price is memory: a separate unrolled routine for each slope per octant, about **3KB total**. On a 128K Spectrum, a modest investment for a massive speed gain.

### Trap-Based Termination

Instead of checking a loop counter at every pixel, Dark plants a sentinel where the line ends. When the drawing code hits the sentinel, it exits -- eliminating the `DEC counter / JR NZ` overhead entirely.

The complete system -- octant selection, segment lookup, unrolled drawing, trap termination -- is one of the most impressive pieces of code in Spectrum Expert #01. When Introspec disassembled *Illusion* in 2017, he found this matrix method at work, drawing the wireframes at full frame rate.

---

## Fixed-Point Arithmetic

Every algorithm in this chapter assumes something we have not yet made explicit: fixed-point numbers.

The Z80 has no floating-point unit. Every register holds an integer. But demo effects need fractional values -- rotation angles, sub-pixel velocities, scale factors. The solution is fixed-point: pick a convention for where the "decimal point" lives within an integer, then do all arithmetic in integers while tracking the scaling mentally.

### Format 8.8

The most common format on the Z80 is **8.8**: high byte = integer part, low byte = fractional part. One 16-bit register pair holds one fixed-point number:

```text
H = integer part    (-128..+127 signed, or 0..255 unsigned)
L = fractional part (0..255, representing 0/256 to 255/256)
```

`HL = $0180` represents 1.5 (H=1, L=128, and 128/256 = 0.5). `HL = $FF80` signed is -0.5 (H=$FF = -1 in two's complement, L=$80 adds 0.5).

The beauty: **addition and subtraction are free** -- just normal 16-bit operations:

```z80 id:ch04_format_8_8_2
; Fixed-point 8.8 addition: result = a + b
; HL = first operand, DE = second operand
    add  hl, de          ; that's it. 11 T-states.

; Fixed-point 8.8 subtraction: result = a - b
    or   a               ; clear carry
    sbc  hl, de          ; 15 T-states.
```

The processor does not care that you are treating these as fixed-point. Binary addition is the same whether the bits represent integers or 8.8 values.

### Fixed-Point Multiplication

Multiplying two 8.8 numbers produces a 16.16 result -- 32 bits. You want 8.8 back, so you take bits 8..23 of the product (effectively shifting right by 8). In practice, with small integer parts (coordinates, rotation factors between -1 and +1), you can decompose the multiply into partial products:

```z80 id:ch04_fixed_point_multiplication
; Fixed-point 8.8 multiply (simplified)
; Input:  BC = first operand (B.C in 8.8)
;         DE = second operand (D.E in 8.8)
; Output: HL = result (H.L in 8.8)
;
; Full product = BC * DE (32 bits), we want bits 8..23
;
; Decomposition:
;   BC * DE = (B*256+C) * (D*256+E)
;           = B*D*65536 + (B*E + C*D)*256 + C*E
;
; In 8.8 result (bits 8..23):
;   H.L = B*D*256 + B*E + C*D + (C*E)/256
;
; For small B,D (say -1..+1), B*D*256 is the dominant term.
; C*E/256 is a rounding correction.
; Total cost: ~200 T-states using the shift-and-add multiplier.

fixmul88:
    ; Multiply B*E -> add to result high
    ld   a, b
    call mul8             ; A = B*E (assuming 8x8->8 truncated)
    ld   h, a

    ; Multiply C*D -> add to result
    ld   a, c
    ld   b, d
    call mul8             ; A = C*D
    add  a, h
    ld   h, a

    ; For higher precision, also compute B*D and C*E
    ; and combine. In practice, the two middle terms
    ; are often sufficient for demo work.

    ld   l, 0             ; fractional part (approximate)
    ret
```

For sine-table-driven rotation where sine values are 8-bit signed (-128 to +127, representing -1.0 to +0.996), multiplying an 8-bit coordinate by a sine value via `mulu112` gives a 16-bit result already in 8.8 format -- high byte is the rotated integer coordinate, low byte is the fraction.

### Why Fixed-Point Matters

Format 8.8 is the sweet spot for the Z80: fits in a register pair, add/subtract are free, multiply costs ~200 T-states, and precision is sufficient for screen-resolution effects. Other formats exist -- 4.12 for more fractional precision, 12.4 for more integer range -- but 8.8 covers the vast majority of use cases. The game development chapters later in this book use 8.8 exclusively.

---

## Theory and Practice

These algorithms are not isolated techniques. They form a system. Multiply feeds the rotation matrix. Rotation outputs coordinates needing perspective division. Division uses log tables. Projected vertices connect with lines drawn by the matrix method. All of it runs on fixed-point arithmetic, with sine values from the parabolic table.

Dark designed these as components of a single engine -- the engine that powered *Illusion*. A wireframe cube spinning at full frame rate exercises every routine in this chapter:

1. **Read the rotation angle** from the sine table (parabolic approximation, ~20 T-states per lookup)
2. **Multiply** vertex coordinates by rotation factors (shift-and-add for accuracy, or square-table for speed -- ~200 or ~60 T-states per multiply, 12 multiplies per vertex)
3. **Divide** by Z for perspective projection (log tables, ~60 T-states per division)
4. **Draw lines** between projected vertices (matrix Bresenham, ~48 T-states per pixel)

For a simple cube (8 vertices, 12 edges), the total per-frame cost is roughly:

- Rotation: 8 vertices x 12 multiplies x 200 T-states = 19,200 T-states
- Projection: 8 vertices x 1 divide x 60 T-states = 480 T-states
- Line drawing: 12 edges x ~40 pixels x 48 T-states = 23,040 T-states
- **Total: ~42,720 T-states** -- comfortably within the ~70,000 T-state frame budget

Switch to the fast square-table multiply and rotation drops to 5,760 T-states. The vertices jitter slightly, but you now have headroom for more complex objects. Speed or accuracy -- in a demo, you make that choice for every effect, every frame.

---

## What Dark Got Right

Looking back at Spectrum Expert #01 from nearly thirty years' distance, what strikes you is not just the quality of the algorithms but the quality of the thinking. Dark presents each one, explains the trade-offs honestly, admits when his derivation has gaps, and trusts the reader to fill those gaps.

He was writing for Spectrum coders in Russia in the late 1990s -- a community building some of the most impressive 8-bit demos in the world, on hardware the rest of the world had abandoned. These are the building blocks they used. When you write your first 3D engine for the Spectrum, these routines will make it possible.

In the next chapter, Dark and STS extend this mathematical foundation into a complete 3D system: the midpoint method for vertex interpolation, backface culling, and solid polygon rendering. The maths here is the foundation. Chapter 5 is the architecture built on top.

---

## Random Numbers: When Tables Won't Do

Everything so far in this chapter is deterministic. Given the same inputs, the same multiply, the same sine lookup, the same line draw -- you get the same output. That is exactly what you want for a spinning wireframe cube or a smooth plasma.

But sometimes you need chaos. Stars twinkling in a star field. Particles scattering from an explosion. Noise textures for terrain generation. A shuffled order for loading screens. In size-coding competitions (256 bytes or less), a good random number generator can produce surprisingly complex visual effects from almost no code.

The Z80 has no hardware random number generator. You must synthesize randomness from arithmetic, and the quality of that arithmetic matters more than you might think.

### The R Register Trick

The Z80 has a built-in source of entropy that many coders reach for first: the R register. It increments automatically with each instruction fetch (every M1 cycle), cycling through 0-127. You can read it in 9 T-states:

```z80 id:ch04_the_r_register_trick
    ld   a, r              ; 9 T -- read refresh counter
```

This is *not* a PRNG. The R register is fully deterministic -- it advances by one per instruction, and its value at any point depends entirely on the code path taken since reset. In a demo with a fixed main loop, R produces the same sequence every time. But it is useful as a seed source: read R once at startup (when timing depends on how long the user waited before pressing a key) and feed that unpredictable value into a proper PRNG.

Some coders mix R into their generator at every call, adding genuine instruction-timing entropy. The Ion generator below uses exactly this trick.

### Four Generators from the Community

In 2024, Gogin (of the Russian ZX scene) assembled a collection of Z80 PRNG routines and shared them for evaluation. Gogin tested them systematically, filling large bitmaps to reveal statistical patterns. The results are instructive -- not all "random" routines are equally random.

Here are four generators from that collection, ordered from best to worst quality.

#### Patrik Rak (Raxoft)'s CMWC Generator (Best Quality)

This is a **Complement Multiply-With-Carry** generator by Patrik Rak (Raxoft), using the multiplier 253 and an 8-byte circular buffer. The mathematics behind CMWC are well-studied: George Marsaglia proved that certain multiplier/buffer combinations produce sequences with enormous periods. With multiplier 253 and buffer size 8, the theoretical period is (253^8 - 1) / 254 -- approximately 2^66 values before repeating.

```z80 id:ch04_four_generators_from_the
; Patrik Rak's CMWC PRNG
; Quality: Excellent -- passes visual bitmap tests
; Size:    ~30 bytes code + 8 bytes table
; Output:  A = pseudo-random byte
; Period:  ~2^66

patrik_rak_cmwc_rnd:
    ld   hl, .table
.smc_idx:
    ld   bc, 0              ; 10 T -- i (self-modifying)
    add  hl, bc             ; 11 T
    ld   a, c               ; 4 T
    inc  a                  ; 4 T
    and  7                  ; 7 T -- wrap index to 0-7
    ld   (.smc_idx+1), a    ; 13 T -- store new index
    ld   c, (hl)            ; 7 T -- y = q[i]
    ex   de, hl             ; 4 T
    ld   h, c               ; 4 T -- t = 256 * y
    ld   l, b               ; 4 T
    sbc  hl, bc             ; 15 T -- t = 255 * y
    sbc  hl, bc             ; 15 T -- t = 254 * y
    sbc  hl, bc             ; 15 T -- t = 253 * y
.smc_car:
    ld   c, 0               ; 7 T -- carry (self-modifying)
    add  hl, bc             ; 11 T -- t = 253 * y + c
    ld   a, h               ; 4 T
    ld   (.smc_car+1), a    ; 13 T -- c = t / 256
    ld   a, l               ; 4 T -- x = t % 256
    cpl                     ; 4 T -- x = ~x (complement)
    ld   (de), a            ; 7 T -- q[i] = x
    ret                     ; 10 T

.table:
    DB   82, 97, 120, 111, 102, 116, 20, 12
```

The algorithm multiplies the current buffer entry by 253, adds a carry value, stores the new carry, and complements the result. The 8-byte circular buffer means the generator's state space is vast -- 8 bytes of buffer plus 1 byte of carry plus the index, giving far more internal state than any single-register generator can achieve.

Gogin's verdict: **best quality** in the collection. When filling a 256x192 bitmap, no visible patterns emerge even at large scales.

#### Ion Random (Second Best)

Originally from Ion Shell for the TI-83 calculator, adapted for Z80. This generator mixes the R register with a feedback loop, achieving surprisingly good randomness from just ~15 bytes:

```z80 id:ch04_four_generators_from_the_2
; Ion Random
; Quality: Good -- minor patterns visible only at extreme scale
; Size:    ~15 bytes
; Output:  A = pseudo-random byte
; Origin:  Ion Shell (TI-83), adapted for Z80

ion_rnd:
.smc_seed:
    ld   hl, 0              ; 10 T -- seed (self-modifying)
    ld   a, r               ; 9 T -- read refresh counter
    ld   d, a               ; 4 T
    ld   e, (hl)            ; 7 T
    add  hl, de             ; 11 T
    add  a, l               ; 4 T
    xor  h                  ; 4 T
    ld   (.smc_seed+1), hl  ; 16 T -- update seed
    ret                     ; 10 T
```

The R register injection means this generator produces different sequences depending on the calling context -- how many instructions execute between calls affects R, which feeds back into the state. For a demo main loop with fixed timing, R advances predictably, but the nonlinear mixing (ADD + XOR) still produces good output. In a game where player input varies the call pattern, the R contribution adds genuine unpredictability.

Gogin's verdict: **second best**. Very compact, good quality for its size.

#### XORshift 16-bit (Mediocre)

A 16-bit XORshift generator -- the Z80 adaptation of Marsaglia's well-known family:

```z80 id:ch04_four_generators_from_the_3
; 16-bit XORshift PRNG
; Quality: Mediocre -- visible diagonal patterns in bitmap tests
; Size:    ~25 bytes
; Output:  A = pseudo-random byte (H or L)
; Period:  65535

xorshift_rnd:
.smc_state:
    ld   hl, 1              ; 10 T -- state (self-modifying, must not be 0)
    ld   a, h               ; 4 T
    rra                     ; 4 T
    ld   a, l               ; 4 T
    rra                     ; 4 T
    xor  h                  ; 4 T
    ld   h, a               ; 4 T
    ld   a, l               ; 4 T
    rra                     ; 4 T
    ld   a, h               ; 4 T
    rra                     ; 4 T
    xor  l                  ; 4 T
    ld   l, a               ; 4 T
    xor  h                  ; 4 T
    ld   h, a               ; 4 T
    ld   (.smc_state+1), hl ; 16 T -- update state
    ret                     ; 10 T
```

XORshift generators are fast and simple, but with only 16 bits of state the period is at most 65,535. More problematically, the bit-rotation pattern creates visible diagonal streaks when the output is mapped to pixels. For a quick star field or particle effect this may be acceptable. For anything that fills large screen areas with "noise," the patterns become obvious.

#### Patrik Rak's CMWC Variant (Mediocre)

A second CMWC variant by Patrik Rak (Raxoft), similar in principle to his version above but with a different buffer arrangement. Gogin found it produced **visible patterns at scale** -- likely due to the way the carry propagation interacts with the buffer indexing. We include it in the compilable example (`examples/prng.a80`) for completeness, but for production use, his 8-byte-buffer version above is strictly superior.

### Elite's Tribonacci Approach

Worth a brief mention: the legendary *Elite* (1984) used a Tribonacci-like sequence for its procedurally generated galaxy. Three registers feed back into each other in a cycle, producing deterministic but well-distributed sequences. The key insight was reproducibility -- given the same seed, the same galaxy generates every time, which meant the entire universe could "fit" in a few bytes of generator state. David Braben and Ian Bell used this to generate 8 galaxies of 256 star systems each from a handful of seed bytes. The technique is closer to a hash function than a PRNG, but the principle -- small state, large apparent complexity -- is the same one that drives demoscene size-coding.

### Elite's Galaxy Generator: A Deeper Look

The Tribonacci approach deserves more detail because it illustrates a key principle: **a PRNG is not just a random number source -- it is a compression algorithm.**

David Braben and Ian Bell needed 8 galaxies of 256 star systems, each with a name, position, economy, government type, and tech level. Storing all of that explicitly would consume kilobytes. Instead, they stored only a 6-byte seed per galaxy and a deterministic generator that expanded each seed into the full star system data. The generator was a three-register feedback loop -- each step rotates and XORs three 16-bit values:

```z80 id:ch04_elite_s_galaxy_generator_a
; Elite's galaxy generator (conceptual, 6502 origin):
;   seed = [s0, s1, s2]  (three 16-bit words)
;   twist: s0' = s1, s1' = s2, s2' = s0 + s1 + s2  (mod 65536)
;   repeat twist for each byte of star system data
```

On the Z80, the same principle works with three register pairs. The "twist" operation produces deterministic but well-distributed values. The crucial property: given the same seed, the same galaxy generates every time. Navigation between stars is just re-seeding and re-generating.

This idea -- **small state, large apparent complexity** -- drives demoscene size-coding too. A 256-byte intro that fills the screen with intricate patterns is doing exactly what Elite did: expanding a tiny seed into a large, complex output through a deterministic process.

### Shaped Randomness

Sometimes you want numbers that are random but follow a specific distribution. A flat uniform PRNG gives every value equal probability, but real-world phenomena are rarely uniform: enemy spawn rates, particle speeds, terrain heights -- all tend to cluster around preferred values.

Common tricks on the Z80:

- **Triangular distribution** -- add two uniform random bytes and shift right. The sum clusters around the centre (128), producing "natural-looking" variation. Cost: two PRNG calls + ADD + SRL = ~20 extra T-states.

```z80 id:ch04_shaped_randomness
; Triangular random: result clusters around 128
    call patrik_rak_cmwc_rnd  ; A = uniform random
    ld   b, a
    call patrik_rak_cmwc_rnd  ; A = another uniform random
    add  a, b                 ; sum (wraps at 256)
    rra                       ; divide by 2 → triangular distribution
```

- **Rejection sampling** -- generate a random number, reject values outside your desired range. For power-of-two ranges this is free (just AND with a mask). For arbitrary ranges, loop until the value fits.

- **Weighted tables** -- store a 256-byte lookup table where each output value appears in proportion to its desired probability. Index with a uniform random byte. The table costs 256 bytes but the lookup is instant (7 T-states). Perfect when the distribution is complex and fixed.

- **PRNG as hash function** -- feed structured data (coordinates, frame numbers) through the PRNG to get deterministic noise. This is how size-coded plasma and noise textures work: `random(x XOR y XOR frame)` gives a different-looking value per pixel per frame, but it is entirely reproducible.

### Seeds and Reproducibility

In a demo, reproducibility is usually desirable: the effect should look the same every time it runs, because the coder choreographed the visuals to match the music. Seed the PRNG once with a fixed value and the sequence is deterministic.

In a game, unpredictability matters. Common seeding strategies:

- **FRAMES system variable ($5C78)** -- the Spectrum ROM maintains a 3-byte frame counter at address $5C78 that increments every 1/50th of a second from power-on. Reading it gives a time-dependent seed that varies with how long the machine has been running. Art-top (Artem Topchiy) recommends using it to initialise Patrik Rak's CMWC table:

```z80 id:ch04_seeds_and_reproducibility
; Seed Patrik Rak CMWC from FRAMES system variable
    ld   hl, $5C78            ; FRAMES (3 bytes, increments at 50 Hz)
    ld   a, (hl)              ; low byte -- most variable
    ld   de, patrik_rak_cmwc_rnd.table
    ld   b, 8
.seed_loop:
    xor  (hl)                 ; mix with FRAMES
    ld   (de), a              ; write to table
    inc  de
    rlca                      ; rotate for variety
    add  a, b                 ; add loop counter
    djnz .seed_loop
```

- **Read R at a user-input moment** -- the exact instruction count between reset and the player pressing a key varies each run. `LD A,R` at that moment captures timing entropy.
- **Frame counter accumulation** -- XOR the R register into an accumulator every frame during the title screen; use the accumulated value as seed when the game starts.
- **Combine multiple sources** -- XOR together R, the low byte of FRAMES, and a byte from the floating bus (on 48K Spectrums, reading certain ports returns whatever the ULA is currently fetching from RAM -- a source of positional entropy).

For demos, simply initialise the generator's state to a known value and leave it. The compilable example (`examples/prng.a80`) shows all four generators with fixed seeds.

### Comparison Table

| Algorithm | Size (bytes) | Speed (T-states) | Quality | Period | Notes |
|-----------|-------------|-------------------|---------|--------|-------|
| Patrik Rak CMWC | ~30 + 8 table | ~170 | Excellent | ~2^66 | Best overall; 8-byte buffer |
| Ion Random | ~15 | ~75 | Good | Depends on R | Compact; mixes R register |
| XORshift 16 | ~25 | ~90 | Mediocre | 65,535 | Visible diagonal patterns |
| Patrik Rak CMWC (alt) | ~35 + 10 table | ~180 | Mediocre | ~2^66 | Patterns visible at scale |
| LD A,R alone | 2 | 9 | Poor | 128 | NOT a PRNG; use as seed only |

For most demoscene work, **Patrik Rak's CMWC** is the clear winner: excellent quality, reasonable size, and a period so long it will never repeat during a demo. If code size is critical (size-coding, 256-byte intros), **Ion Random** packs remarkable quality into 15 bytes. XORshift is a fallback when you need something quick and do not care about visual quality.

> **Credits:** PRNG collection, quality assessment, and bitmap testing by **Gogin**. Patrik Rak's CMWC generator is based on George Marsaglia's Complementary Multiply-With-Carry theory. Ion Random originates from **Ion Shell** for the TI-83 calculator.

![PRNG output — random attribute colours fill the screen, revealing the generator's statistical quality](../../build/screenshots/ch04_prng.png)

---

*All cycle counts in this chapter are for Pentagon timing (no wait states). On a standard 48K Spectrum or Scorpion with contended memory, expect higher counts for code executing in the lower 32K of RAM. See Appendix A for the complete timing reference.*

> **Sources:** Dark / X-Trade, "Programming Algorithms" (Spectrum Expert #01, 1997); Gogin, PRNG collection and quality assessment; Patrik Rak (Raxoft), CMWC generator; Ped7g (Peter Helcmanovsky), signed arithmetic gap identification and review
