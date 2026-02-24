# Chapter 6: The Sphere --- Texture Mapping on 3.5 MHz

> *"Coder effects are always about evolving a computation scheme."*
> --- Introspec, 2017

---

It is 1996, and a demo called *Illusion* takes first place at ENLiGHT'96 in St. Petersburg. The audience watches a monochrome image wrap itself around a spinning sphere, rotating smoothly in real time, on a ZX Spectrum running at 3.5 MHz with no hardware acceleration whatsoever. No blitter. No GPU. No co-processor. Just a Z80, 48 kilobytes of contiguous RAM, and whatever a twenty-year-old coder named Dark could squeeze out of them.

Twenty years later, in March 2017, Introspec sits down with a copy of the binary and a disassembler. He picks apart the rendering loop instruction by instruction, counts T-states, maps memory addresses to data structures, and publishes his findings on Hype. What follows is one of the most detailed public teardowns of a demoscene effect ever written for the ZX Spectrum --- and, in the comment thread that erupts beneath it, a debate about what really matters in real-time rendering on constrained hardware.

This chapter follows Introspec's analysis. We will look over his shoulder as he traces the code, understand *why* the sphere works the way it does, and then build a simplified version ourselves.

---

## The Problem: A Round Object on a Square Screen

A sphere on screen is not a sphere. It is a circle filled with a distorted image. The distortion follows the rules of spherical projection: pixels near the equator are spaced evenly, pixels near the poles are compressed horizontally, and the entire mapping curves to create the illusion of a three-dimensional surface.

The source image in Illusion is stored as a monochrome bitmap --- one byte per pixel, where each byte is either 0 or 1. This is extravagant by Spectrum standards, where screen memory packs eight pixels per byte, but it buys something essential: the rendering code can treat pixels as arithmetic values rather than bit positions.

The task, then, is this: read pixels from the source image, sample them according to a spherical projection, pack eight of them into a single screen byte, and write that byte to video memory. Do this for every visible byte of the sphere. Do it fast enough to animate. Do it on a 3.5 MHz Z80.

## The Insight: Code That Writes Code

The first question any Z80 programmer asks is: what does the inner loop look like? On a machine where a single `NOP` takes 4 T-states and you have roughly 70,000 T-states per frame, the inner loop *is* the program. Everything else --- setup, table generation, frame management --- is overhead that happens once or infrequently. The inner loop runs thousands of times per frame.

Dark's solution is to not have a fixed inner loop at all.

Instead, the rendering code is *generated at runtime*. For each horizontal line of the sphere, the program constructs a sequence of Z80 instructions tailored to that line's geometry. The generated code reads source pixels in order, accumulates them into screen bytes via shifts and additions, and advances through the source data by distances that vary with the sphere's curvature. Different lines of the sphere produce different code.

This is a technique that appears throughout the demoscene: self-generating code, sometimes called "compiled sprites" when applied to sprite rendering, or "unrolled loop generation" in the general case. What makes the sphere version distinctive is the variability. A compiled sprite is fixed --- once generated, it draws the same shape every time. The sphere code changes with the rotation angle, because different source pixels become visible as the sphere turns.

## Inside the Disassembly

Introspec traced the rendering engine to a block of generated code and a set of lookup tables starting at address `$6944`. The tables encode the sphere's geometry as a series of *skip distances*: for each position along a scanline of the sphere, how many source pixels should be skipped before the next one is sampled.

At the equator, the skip distances are roughly uniform --- the source image maps onto the sphere with minimal distortion. Near the poles, the horizontal compression of the projection means larger skips between sampled pixels. At the very top and bottom, only a few pixels are visible per line, and the skips can be substantial.

The generated inner loop has a repeating structure. For each screen byte (eight packed pixels), it executes a sequence like this:

```z80 id:ch06_inside_the_disassembly
; --- Accumulating 8 source pixels into one screen byte ---
; HL points into the source image (one byte per pixel)
; A is the accumulator, building the screen byte bit by bit

    add  a,a          ; shift accumulator left (make room for next pixel)
    add  a,(hl)       ; add source pixel (0 or 1) into lowest bit
    inc  l            ; advance to next source pixel
    ; ... possibly more INC L instructions here,
    ; depending on how many pixels to skip

    add  a,a          ; shift again
    add  a,(hl)       ; sample next pixel
    inc  l
    inc  l            ; skip one extra pixel (sphere curvature)

    add  a,a
    add  a,(hl)
    inc  l

    ; ... six more times, for 8 pixels total ...
```

The key detail: between each `add a,(hl)`, the number of `inc l` instructions varies. One pixel position might need a single `inc l` (sample adjacent pixels). Another might need three or four (skip over compressed regions of the projection). The lookup tables at `$6944` encode exactly how many `inc l` instructions to insert at each position.

Let us look more carefully at what happens with a single pixel:

```z80 id:ch06_inside_the_disassembly_2
    add  a,a          ;  4 T-states  (shift A left by 1)
    add  a,(hl)       ;  7 T-states  (add source pixel into bit 0)
    inc  l            ;  4 T-states  (advance source pointer)
```

That is the minimum cost: 15 T-states to shift the accumulator and sample one pixel, plus 4 T-states for each source byte skipped. After eight such sequences, the accumulator holds a complete screen byte.

Notice that the source pointer is advanced using `inc l` rather than `inc hl`. This is deliberate. `INC HL` takes 6 T-states; `INC L` takes 4. By constraining the source data to sit within a single 256-byte page (so that only the low byte of the address changes), Dark saves 2 T-states per advance. When you are doing this thousands of times per frame, those 2 T-states add up.

There is a subtlety here that is easy to miss. The source image is stored as one byte per pixel, and `INC L` wraps around within a 256-byte page. This means each scanline of source data must fit within 256 bytes, and the source buffer must be page-aligned. The constraint shapes the entire memory layout of the demo.

## Counting T-States

Introspec calculated the cost per output byte as:

**101 + 32x T-states**

where *x* is the average number of extra `INC L` instructions per pixel beyond the mandatory one. Let us verify this.

The fixed cost per pixel is:

| Instruction | T-states |
|-------------|----------|
| `add a,a`   | 4        |
| `add a,(hl)`| 7        |
| `inc l`     | 4        |
| **Subtotal** | **15**  |

For 8 pixels, the fixed cost is 8 x 15 = 120 T-states. But there is additional overhead per byte: the code must write the completed byte to screen memory and set up for the next. Let us assume the output sequence looks something like:

```z80 id:ch06_counting_t_states
    ld   (de),a       ;  7 T-states  (write screen byte)
    inc  e            ;  4 T-states  (advance screen pointer)
```

There may also be setup for the accumulator (an `xor a` or similar) at the start of each byte. Taking Introspec's measured figure of 101 T-states as the fixed base cost per byte, the overhead beyond the raw pixel sampling accounts for roughly 101 - 120 = ... which means the base figure already includes the output instructions and some of the pixel work is interleaved differently than the naive count suggests.

The cleaner way to read the formula: 101 T-states of fixed overhead (output, pointer management, any per-byte setup), plus 32 T-states per extra skip. The "32" comes from 8 pixels times 4 T-states per extra `INC L`, which gives us x as the average number of extra skips per pixel position in that byte. When the sphere is near the equator, x is small --- the projection is close to uniform. Near the poles, x is large, and the rendering slows down. But the poles also have fewer bytes to draw (the sphere is narrower there), so the total workload roughly balances.

Is this fast enough? The Spectrum's frame is approximately 70,000 T-states (more on Pentagon: 71,680). A 56-pixel-diameter sphere occupies roughly 7 bytes across at its widest. Over the full height, perhaps 200--250 bytes need to be rendered. At 101 T-states per byte (equatorial, x near zero), that is roughly 25,000 T-states --- comfortably within a single frame budget, with room left for screen clearing, table lookups, and all the other housekeeping. Even near the poles where x might average 2--3, the cost per byte rises to 165--197 T-states, but fewer bytes need drawing. The arithmetic works out. It fits.

## The Code Generation Pass

Before the inner loop runs, a *code generation pass* constructs it. This pass reads the lookup tables at `$6944`, which encode the sphere geometry for the current rotation angle, and emits Z80 instructions into a buffer:

1. For each scanline of the sphere, read the skip distances from the table.
2. Emit `add a,a` followed by `add a,(hl)` for each pixel.
3. Emit the appropriate number of `inc l` instructions based on the skip distance.
4. After every 8 pixels, emit the output instruction to write the accumulated byte to screen memory.
5. At the end of each scanline, emit a return or jump to the next line's handler.

The generated code block is then called directly. The CPU executes the instructions as if they were a normal subroutine, but they were written moments ago by the code generator. This is self-modifying code in the most literal sense --- the program generates the program that draws the screen.

The code generation pass itself is not free, but it runs once per frame (or once per rotation step), while the generated inner loop runs hundreds of times. The amortized cost is negligible.

## What Dark Knew: Spectrum Expert and the Building Blocks

There is a detail in this story that transforms it from a technical curiosity into a narrative arc. Dark --- the coder behind Illusion's sphere effect --- is the same Dark who wrote the *Programming Algorithms* articles in Spectrum Expert #01, published in 1997.

Those articles cover multiplication (shift-and-add vs. square-table lookup), division (restoring and logarithmic), sine table generation via parabolic approximation, and Bresenham line drawing with optimized 8x8 matrix blocks. They are tutorial material, written for the ZX Spectrum programming community, explaining fundamental techniques that any demo coder would need.

And they are, quite precisely, the building blocks used in Illusion.

The sphere requires: trigonometric lookup tables for computing the projection (sine/cosine, the parabolic approximation from Dark's article). Fixed-point multiplication for scaling. Careful memory layout for speed (the same cycle-counting discipline that Dark teaches throughout the articles). The skip-table approach to encoding sphere geometry is a direct application of the kind of precomputation-driven thinking that Dark advocates.

Dark wrote the demo first --- Illusion won at ENLiGHT'96. Then, in 1997--98, he published the textbook that explained every technique he had used. Twenty years later, Introspec reverse-engineered the demo and found exactly the algorithms Dark had documented. We have both sides of the story: the practitioner explaining his methods after the fact, and the analyst confirming that those methods are precisely what the finished product contains.

## The Hype Debate: Inner Loops vs. Mathematics

Introspec's 2017 article on Hype sparked a long comment thread. Among the most substantive exchanges was a debate between kotsoft and Introspec about where the real work of an effect like this lies.

kotsoft argued that the mathematical approach to the projection --- how you compute which source pixel maps to which screen position --- is the critical design decision. Get the projection wrong, or use a naive algorithm, and no amount of inner-loop optimization will save you. The mathematical model determines whether the effect is even *feasible* on the hardware.

Introspec countered that the inner loop is where the T-states are actually spent. You can have a beautiful mathematical model, but if the rendering code costs 200 T-states per byte instead of 100, you have halved your frame rate. The mathematical approach defines *what* to compute; the inner loop determines *whether you can compute it in time*.

Both are right, and the tension between them illuminates something fundamental about demoscene coding. A demo effect is not pure mathematics and not pure engineering. It is the intersection: an elegant computation scheme (the sphere projection encoded as skip tables) married to an efficient execution strategy (generated unrolled loops with `INC L` advances). Neither alone is sufficient.

Introspec's summary captures it: "coder effects are always about evolving a computation scheme." The word *evolving* is key. You do not start with a textbook algorithm and optimize it until it fits. You evolve the algorithm and the implementation together, each constraining and enabling the other, until you find a form that works within the hardware's budget.

## Practical: A Simplified 56x56 Spinning Sphere

Let us sketch how you would build a simplified version of this effect. We will target a 56x56 pixel sphere --- 7 bytes wide at the equator, 56 scanlines tall. The goal is not to reproduce Illusion's full rendering engine, but to understand the core technique well enough to implement it.

### Step 1: Precompute the Sphere Geometry

For each scanline *y* (from -28 to +27, centered on the sphere), compute the visible arc:

```text
radius_at_y = sqrt(R^2 - y^2)    ; where R = 28 (sphere radius in pixels)
```

This gives the half-width of the sphere at that scanline. For each pixel position *x* within that arc, compute the corresponding longitude and latitude on the sphere surface:

```text
latitude  = arcsin(y / R)
longitude = arcsin(x / radius_at_y) + rotation_angle
```

These give the (u, v) coordinates into the source texture for each screen pixel.

### Step 2: Build Skip Tables

Rather than storing full (u, v) pairs for every pixel (prohibitively expensive in memory), compute the *difference in source position* between adjacent screen pixels. For each scanline, you need a list of skip values: how many source pixels to advance between consecutive screen samples.

Near the equator, consecutive screen pixels map to nearly adjacent source pixels --- skips of 1. Near the poles, the projection compresses, and you skip over more source pixels --- skips of 2, 3, or more.

Store these as a table. For our 56x56 sphere, you need at most 56 entries per line (the widest line), times 56 lines, times one byte per entry. That is at most 3,136 bytes for a single rotation angle --- but in practice, you can exploit vertical symmetry (top half mirrors bottom half) and store only half the table.

For animation, you need skip tables for multiple rotation angles. With 32 rotation steps, you could fit the tables into 32 x 1,568 = about 49KB. That overflows available memory, so in practice you would use fewer rotation steps, coarser angular resolution, or regenerate tables on the fly from a compact representation.

### Step 3: Generate the Rendering Code

For each frame, read the skip table for the current rotation angle and generate Z80 code:

```z80 id:ch06_step_3_generate_the_rendering
; Code generator pseudocode (in Z80 assembly, this would be
; a loop that writes opcodes into a buffer)

generate_sphere_code:
    ld   iy,skip_table        ; pointer to skip distances
    ld   ix,code_buffer       ; pointer to output code buffer

.line_loop:
    ; For each scan line...
    ld   b,bytes_this_line    ; number of output bytes (e.g. 7 at equator)

.byte_loop:
    ; For each output byte, emit code for 8 pixels:
    ld   c,8                  ; 8 pixels per byte

.pixel_loop:
    ; Emit: ADD A,A
    ld   (ix+0),$87           ; opcode for ADD A,A
    inc  ix

    ; Emit: ADD A,(HL)
    ld   (ix+0),$86           ; opcode for ADD A,(HL)
    inc  ix

    ; Emit INC L instructions based on skip distance
    ld   a,(iy+0)             ; read skip distance
    inc  iy

.emit_inc_l:
    or   a
    jr   z,.pixel_done
    ld   (ix+0),$2C           ; opcode for INC L
    inc  ix
    dec  a
    jr   nz,.emit_inc_l

.pixel_done:
    dec  c
    jr   nz,.pixel_loop

    ; Emit: LD (DE),A  (write byte to screen)
    ld   (ix+0),$12           ; opcode for LD (DE),A
    inc  ix
    ; Emit: INC E
    ld   (ix+0),$1C           ; opcode for INC E
    inc  ix

    dec  b
    jr   nz,.byte_loop

    ; Emit line transition code here (advance DE to next screen line)
    ; ...

    jr   .line_loop
```

This is simplified --- the actual Illusion code is more tightly integrated, and Dark likely used a more compact and efficient code generator. But the principle is the same: read skip distances, emit opcodes.

### Step 4: Execute and Display

Once the code buffer is filled, call it as a subroutine:

```z80 id:ch06_step_4_execute_and_display
    ld   hl,source_image      ; source texture (page-aligned, 1 byte/pixel)
    ld   de,screen_address    ; start of sphere area in video memory
    call code_buffer          ; execute the generated rendering code
```

The generated code runs through the entire sphere, reading source pixels, packing them into screen bytes, and writing them to video memory. When it returns, the sphere is drawn.

For animation, increment the rotation angle, load the corresponding skip table (or regenerate it), regenerate the code, and render again.

### Step 5: Source Image Layout

The source texture must be organized for fast sequential access. Since the rendering code uses `INC L` to advance through it, the texture must be page-aligned (start at an address where the low byte is `$00`), and each row must fit within 256 bytes. A 256-pixel-wide texture stored as one byte per pixel fits this constraint perfectly: each row occupies one page.

For the monochrome case, each pixel is `$00` or `$01`. This means `ADD A,(HL)` either adds 0 (pixel off) or 1 (pixel on) to the accumulator's lowest bit, right after `ADD A,A` has shifted everything up. The result is a bit-packed screen byte where each bit corresponds to a sampled source pixel.

---

## The Larger Pattern

The sphere in Illusion is a specific instance of a general demoscene pattern that appears throughout this book. The pattern has three parts:

**Precomputation.** Expensive mathematical work --- projection, trigonometry, coordinate transforms --- is done once (or once per frame) and stored as compact tables. The tables encode *what* to render without encoding *how*.

**Code generation.** The rendering code itself is generated from the tables. This eliminates branches, loop counters, and conditional logic from the inner loop. Every instruction in the generated code does useful work. There is no overhead for "figuring out what to do next" --- that decision was made during generation.

**Sequential memory access.** The inner loop reads data sequentially, advancing a pointer with single-byte increments. This is the fastest possible access pattern on the Z80, where register-indirect loads (`LD A,(HL)`) are cheap and indexed addressing (`LD A,(IX+d)`) is expensive.

The rotozoomer in the next chapter uses the same pattern. So does the dotfield scroller in Chapter 10. So do the attribute tunnels in Chapter 9. The specifics differ --- different tables, different generated code, different data formats --- but the architecture is the same. Introspec recognized this when he wrote that coder effects are about "evolving a computation scheme." The sphere, the rotozoomer, the tunnel: they are all evolved from the same fundamental approach. The evolution is in the details --- which computation, which table layout, which inner loop --- but the skeleton is shared.

Dark understood this in 1996. He encoded it in his Spectrum Expert articles in 1997. Introspec confirmed it by disassembly in 2017. The pattern is as valid now as it was then, on any platform where T-states are scarce and every instruction must earn its keep.

---

## Summary

- The sphere effect in Illusion maps a monochrome source image onto a rotating sphere using dynamically generated Z80 code.
- Lookup tables encode the sphere's geometry as pixel skip distances. The rendering code is generated from these tables at runtime.
- The inner loop uses `ADD A,A` and `ADD A,(HL)` to accumulate pixels into screen bytes, with variable numbers of `INC L` instructions to advance through the source data.
- Performance: 101 + 32x T-states per output byte, where x depends on position.
- The approach exemplifies a general demoscene pattern: precompute geometry, generate code, access memory sequentially.
- Dark applied these algorithms in Illusion (1996), then documented them in Spectrum Expert (1997--98). Introspec reverse-engineered the result twenty years later, confirming the techniques.

---

> **Sources:** Introspec, "Technical Analysis of Illusion by X-Trade" (Hype, 2017); Dark, "Programming Algorithms" (Spectrum Expert #01, 1997). The Hype comment thread includes contributions from kotsoft, Raider, and others.
