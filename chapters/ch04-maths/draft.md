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

```z80
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

For 16x16 producing a 32-bit result, Dark's MULU224 runs in 730 to 826 T-states. In practice, demoscene 3D engines avoid full 16x16 multiplies by keeping coordinates in 8.8 fixed-point and using 8x8 multiplies where possible.

### Method 2: Square Table Lookup

Dark's second method trades memory for speed, exploiting an algebraic identity that every demoscener eventually discovers:

```
A * B = ((A+B)^2 - (A-B)^2) / 4
```

Pre-compute a table of n^2/4 values, and multiplication becomes two lookups and a subtraction -- approximately 61 T-states, more than three times faster than shift-and-add.

You need a 512-byte table of (n^2/4) for n = 0 to 511, page-aligned for single-register indexing. The table must be 512 bytes because (A+B) can reach 510.

```z80
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

## Division on Z80

Division on the Z80 is even more painful than multiplication. No divide instruction, and the algorithm is inherently serial -- each quotient bit depends on the previous subtraction. Dark again presents two methods: accurate and fast.

### Method 1: Shift-and-Subtract (Restoring Division)

Binary long division. Start with a zeroed accumulator. The dividend shifts in from the right, one bit per iteration. Try subtracting the divisor; if it succeeds, set a quotient bit. If it fails, restore the accumulator -- hence "restoring division."

```z80
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

The 16-bit version (DIVU222) costs 938 to 1034 T-states. A thousand cycles for a single divide. With a frame budget of ~70,000 T-states, you can afford perhaps 70 divides per frame -- doing nothing else. This is why demoscene 3D engines go to extreme lengths to avoid division.

### Method 2: Logarithmic Division

Dark's faster alternative uses logarithm tables:

```
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

```z80
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

Drawing lines is fundamental to wireframe 3D. Every edge of a rotating object is a line from (x1,y1) to (x2,y2), and you need to draw it fast. Dark's treatment of line drawing in Spectrum Expert #01 is the longest section of his article, because he works through three progressively faster approaches before arriving at his final solution.

### The Classic Algorithm

Bresenham's line algorithm is well known. You step along the major axis (whichever of x or y covers more distance) one pixel at a time, maintaining an error accumulator that tells you when to step along the minor axis. The error term starts at zero, increases by dy (or dx) at each step, and when it exceeds the threshold, you step sideways and subtract dx (or dy) from the error.

On the ZX Spectrum, "set a pixel" is not a simple operation. The screen memory is interleaved -- row 0 is at $4000, row 1 at $4100, row 2 at $4200, and so on in a non-sequential pattern that makes vertical movement expensive. Setting a single pixel requires computing a byte address and a bit position within that byte. The standard Spectrum ROM routine for pixel plotting takes over 1000 T-states per pixel. Even a hand-optimised Bresenham loop costs around 80 T-states per pixel.

### The Xopha Modification

Dark mentions an optimisation he attributes to Xopha: instead of computing pixel addresses from scratch each time, you maintain a screen pointer (HL) and advance it incrementally. Moving one pixel right means rotating a bit mask; moving one pixel down means adjusting HL with the DOWN_HL macro (itself a multi-instruction sequence due to the interleaved screen layout). This helps, but the core problem remains.

### Dark's Matrix Method: 8x8 Pixel Grids

Then Dark makes his key observation: **"87.5% of checks are wasted."**

Here is what he means. In a Bresenham loop, at every pixel you ask: should I step sideways? For a nearly horizontal line, the answer is almost always no -- you just keep moving along the major axis. For a 45-degree line, you step sideways every time. But on average, across all possible line slopes, seven out of eight checks produce no side-step. You are burning cycles on a conditional branch that almost never fires.

Dark's solution: pre-compute the pixel pattern for each possible line slope within an 8x8 pixel grid, and unroll the drawing loop to output entire grid cells at once.

Think of it this way. A line segment within an 8x8 pixel area can be described by its entry point, its exit point, and the set of pixels it passes through. For each octant (there are eight, due to x/y symmetry and positive/negative slopes), you can enumerate all possible 8-pixel patterns. Each pattern is a sequence of `SET bit,(HL)` instructions with appropriate address increments between them.

```z80
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

No conditional branches. No error accumulator updates. Just a straight sequence of `SET` instructions with a couple of address adjustments. The `SET bit,(HL)` instruction takes 15 T-states. Eight of them plus a couple of `INC H` operations gives roughly 130 T-states per 8-pixel segment, or about 16 T-states per pixel. Even accounting for the overhead of looking up which segment routine to call and advancing to the next character cell, Dark achieves approximately **48 T-states per pixel** in the inner drawing loop -- nearly half the cost of the classical Bresenham approach.

The price is memory. You need a separate unrolled routine for each possible slope within each octant. Dark estimates about **3KB of memory** for the pre-unrolled octant loops. On a 128K Spectrum, that is a modest investment for a massive speed gain.

### How the Trap-Based Termination Works

An additional optimisation: instead of checking a loop counter at every pixel ("have I drawn the full line yet?"), Dark sets a trap. He calculates where the line ends and plants a sentinel value in the routine. When the drawing code hits the sentinel, it exits. This eliminates the `DEC counter / JR NZ` overhead from the inner loop entirely.

The complete line-drawing system -- setup, octant selection, segment lookup, and unrolled drawing -- is one of the most impressive pieces of code in Spectrum Expert #01. And it is exactly what powers the wireframe 3D engine in *Illusion*. When Introspec disassembled the demo in 2017, he found this matrix method at work, drawing the wireframe objects that filled the screen at full frame rate.

---

## Fixed-Point Arithmetic

Before we leave the world of Z80 maths, we need to formalise something that has been lurking behind every algorithm in this chapter: fixed-point numbers.

The Z80 has no floating-point unit. It has no concept of decimal points. Every register holds an integer. But demo effects need fractional values -- a rotation angle of 0.7 radians, a velocity of 1.5 pixels per frame, a perspective scale factor of 0.003. The solution is fixed-point: you pick a convention for where the "decimal point" lives within an integer, and then do all your arithmetic in integers while keeping track of the scaling mentally.

### Format 8.8

The most common fixed-point format on the Z80 is **8.8**: the high byte holds the integer part (signed or unsigned), and the low byte holds the fractional part. A 16-bit register pair like HL holds one fixed-point number:

```
H = integer part    (-128..+127 signed, or 0..255 unsigned)
L = fractional part (0..255, representing 0/256 to 255/256)
```

So `HL = $0180` represents 1.5 (H=1, L=128, and 128/256 = 0.5). `HL = $FF80` in signed interpretation represents -0.5 (H=$FF = -1 in two's complement, but L=$80 adds back 0.5, giving -1 + 0.5 = -0.5).

The beauty of this format is that **addition and subtraction are free**. They are just normal 16-bit operations:

```z80
; Fixed-point 8.8 addition: result = a + b
; HL = first operand, DE = second operand
    add  hl, de          ; that's it. 11 T-states.

; Fixed-point 8.8 subtraction: result = a - b
    or   a               ; clear carry
    sbc  hl, de          ; 15 T-states.
```

The processor does not know or care that you are treating these as fixed-point numbers. The binary addition works identically whether the bits represent 16-bit integers or 8.8 fixed-point values, because the positional arithmetic is the same.

### Fixed-Point Multiplication

Multiplication is where fixed-point gets interesting. If you multiply two 8.8 numbers, you get a result in **16.16 format** -- 32 bits total, with 16 bits of fraction. But you only want an 8.8 result. So you need to multiply, then shift right by 8 bits (discarding the lowest byte of the 32-bit product) to get back to 8.8 format.

In practice, if the integer parts of your operands are small (which they usually are in demo effects -- coordinates within the screen, rotation factors between -1 and +1), you can use a simplified approach: multiply just the key bytes and assemble the result:

```z80
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

The exact implementation depends on your precision needs. For a sine-table-driven rotation where the sine values are 8-bit signed (-128 to +127 representing -1.0 to +0.996), you multiply an 8-bit coordinate by an 8-bit sine value using the `mulu112` routine from earlier in this chapter, and the 16-bit result is already in 8.8 format -- the high byte is your rotated integer coordinate, the low byte is the fractional part you can either use or discard.

### Why Fixed-Point Matters

Fixed-point arithmetic is the bridge between the integer-only Z80 and the continuous mathematics of demo effects. Every 3D rotation, every scrolling trajectory, every smooth animation relies on it. The format 8.8 is the sweet spot for the Z80: it fits in a register pair, add/subtract are free, multiply costs roughly 200 T-states (using `mulu112`), and the precision is sufficient for screen-resolution effects.

Higher precision formats exist -- 4.12 gives more fractional bits at the expense of integer range, 12.4 gives more integer range at the expense of smoothness -- but 8.8 covers the vast majority of use cases. The game development chapters later in this book use 8.8 exclusively for entity positions, velocities, and physics calculations.

---

## Theory and Practice

The algorithms in this chapter are not isolated techniques. They form a system. The multiply routine feeds the rotation matrix. The rotation matrix outputs coordinates that need perspective division. The division uses log tables. The rotated, projected vertices connect with lines drawn by the matrix Bresenham method. And all of it runs on fixed-point arithmetic, with sine and cosine values pulled from the parabolic lookup table.

Dark understood this in 1997. He wrote these algorithms as separate sections of a magazine article, but he designed them as components of a single engine -- the engine that powered *Illusion*. When you see a wireframe cube spinning on a Spectrum at full frame rate, every routine in this chapter is executing, dozens of times per frame, in a carefully budgeted pipeline:

1. **Read the rotation angle** from the sine table (parabolic approximation, ~20 T-states per lookup)
2. **Multiply** vertex coordinates by rotation factors (shift-and-add for accuracy, or square-table for speed -- ~200 or ~60 T-states per multiply, 12 multiplies per vertex)
3. **Divide** by Z for perspective projection (log tables, ~60 T-states per division)
4. **Draw lines** between projected vertices (matrix Bresenham, ~48 T-states per pixel)

For a simple cube (8 vertices, 12 edges), the total per-frame cost is roughly:

- Rotation: 8 vertices x 12 multiplies x 200 T-states = 19,200 T-states
- Projection: 8 vertices x 1 divide x 60 T-states = 480 T-states
- Line drawing: 12 edges x ~40 pixels x 48 T-states = 23,040 T-states
- **Total: ~42,720 T-states** -- comfortably within the ~70,000 T-state frame budget

Switch to the fast square-table multiply and rotation drops to 5,760 T-states. The vertices will jitter slightly, but you now have headroom for more complex objects or additional effects. This is the trade-off Dark described: speed or accuracy. In a demo, you make that choice for every effect, every frame.

---

## What Dark Got Right

Looking back at Spectrum Expert #01 from nearly thirty years' distance, what strikes you is not just the quality of the algorithms -- which are solid, practical, and well-optimised -- but the quality of the thinking. Dark presents each algorithm, explains the trade-offs honestly, admits when his derivation has gaps ("something is not right here"), and trusts the reader to be intelligent enough to fill those gaps themselves.

He was writing for an audience of Spectrum coders in Russia in the late 1990s -- a community that was building some of the most impressive 8-bit demos in the world, on hardware that the rest of the world had abandoned a decade earlier. The algorithms in this chapter are the building blocks they used. When you write your first 3D engine for the Spectrum, these are the routines that will make it possible.

In the next chapter, we will see how Dark and STS extended this mathematical foundation to build a complete 3D system: the midpoint method for vertex interpolation, backface culling, and solid polygon rendering. The maths in this chapter is the foundation. Chapter 5 is the architecture built on top of it.

---

*All cycle counts in this chapter are for Pentagon timing (no wait states). On a standard 48K Spectrum or Scorpion with contended memory, expect higher counts for code executing in the lower 32K of RAM. See Appendix A for the complete timing reference.*
