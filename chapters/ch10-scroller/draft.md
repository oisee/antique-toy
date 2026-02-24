# Chapter 10: The Dotfield Scroller and 4-Phase Colour

> *"Two normal frames and two inverted frames. The eye sees the average."*
> -- Introspec, Making of Eager (2015)

---

The ZX Spectrum displays two colours per 8x8 cell. Text scrolls across a screen at whatever rate the CPU can manage. These are fixed constraints -- the hardware does what it does, and no amount of cleverness will change the silicon.

But cleverness can change what the viewer *perceives*.

This chapter brings together two techniques from two different demos, separated by nearly twenty years but connected by a shared principle. The dotfield scroller from X-Trade's *Illusion* (ENLiGHT'96) renders text as a bouncing cloud of individual dots, each placed at a cost of just 36 T-states. The 4-phase colour animation from Introspec's *Eager* (3BM Open Air 2015) alternates four carefully constructed frames at 50Hz to trick the eye into seeing colours the hardware cannot produce. One exploits spatial resolution -- placing dots wherever you want, unconstrained by character cells. The other exploits temporal resolution -- cycling frames faster than the eye can follow. Together they demonstrate the two main axes of cheating on constrained hardware: space and time.

---

## Part 1: The Dotfield Scroller

### What the Viewer Sees

Picture a message -- "ILLUSION BY X-TRADE" -- rendered not in solid block characters but as a field of individual dots, each dot a single pixel. The text drifts horizontally across the screen in a smooth scroll. But the dots are not sitting on flat scanlines. They bounce. The entire dot field undulates in a sine wave, each column offset vertically from its neighbours, creating the impression of text rippling on the surface of water.

### The Font as Texture

The font is stored as a bitmap texture in memory -- one bit per dot. If the bit is 1, a dot appears on screen. If the bit is 0, nothing happens. The critical word is *transparent*. In a normal renderer, you write every pixel position. In the dotfield scroller, transparent pixels are nearly free. You check the bit, and if it is zero, you skip. Only the set pixels require a write to video memory.

This means rendering cost is proportional to the number of visible dots, not the total area. A typical 8x8 character might have 20 set pixels out of 64. For a large scrolling message, this economy matters enormously. BC points to the font data; RLA shifts each bit into the carry flag to determine on or off.

### Stack-Based Address Tables

In a conventional scroller, each pixel's screen position is calculated from (x, y) coordinates using the Spectrum's interleaved address formula. That calculation involves shifts, masks, and lookups. Doing it for thousands of pixels per frame would consume the entire budget.

Dark's solution: pre-calculate every screen address and store them as a table that the stack pointer walks through. POP reads 2 bytes and auto-increments SP, all in 10 T-states. Point SP at the table instead of the real stack, and POP becomes the fastest possible address retrieval -- no index registers, no pointer arithmetic, no overhead.

Compare POP to the alternatives. `LD A,(HL) : INC HL` fetches one byte in 11 T-states -- you would need two such pairs (22 T) to fetch an address, plus `LD L,A / LD H,A` bookkeeping. An indexed load like `LD L,(IX+0) : LD H,(IX+1)` costs 38 T-states for the pair. POP fetches both bytes, increments the pointer, and loads a register pair -- 10 T-states, no contest. The price is that you surrender the stack pointer to the renderer. Nothing else can use SP while the inner loop runs.

This means interrupts are fatal. If an interrupt fires while SP points into the address table, the Z80 pushes the return address onto the "stack" -- which is actually your data table. Two bytes of carefully computed screen addresses get overwritten with a return address, and the interrupt service routine proceeds to execute whatever garbage sits at the corrupted location. The result is anything from a garbled frame to a hard crash. The solution is simple and non-negotiable: `DI` before hijacking SP, `EI` after restoring it. Every POP-trick routine in every Spectrum demo follows this pattern:

```z80 id:ch10_stack_based_address_tables
    di
    ld   (.smc_sp+1), sp  ; save SP via self-modifying code
    ld   sp, table_addr    ; point SP at pre-computed data
    ; ... inner loop using POP ...
.smc_sp:
    ld   sp, $0000          ; self-modified: restores original SP
    ei
```

The save/restore uses self-modifying code because it is the fastest way to both save and restore SP in one step. `EX (SP),HL` requires a valid stack. `LD (addr),SP` exists (opcode ED 73, 20 T-states), but it saves SP to a fixed address -- you would then need a separate `LD SP,(addr)` to restore it later (also 20 T-states), and the restore is no faster than the self-modifying approach. The SMC technique writes SP's value directly into the operand field of a later `LD SP,nnnn` instruction: `LD (.smc+1),SP` costs 20 T-states for the save, and the restore (`LD SP,nnnn` with the patched operand) costs just 10 T-states. The combined save+restore is 30 T-states versus 40 T-states for the LD (addr),SP / LD SP,(addr) pair -- a small saving that also avoids reserving a separate memory location.

One subtle consequence: the DI/EI window blocks the frame interrupt. If the inner loop runs long, HALT at the top of the main loop will still catch the next interrupt -- but if the rendering overshoots an entire frame, you lose sync. This is why the budget arithmetic matters. You must know your worst-case timing before committing to the POP trick.

The bouncing motion is encoded entirely in the address table. Each entry is a screen address that already includes the vertical sine offset. The "bounce" does not happen at render time. It happened when the table was built. All three dimensions of the animation -- scroll position, bounce wave, character shape -- collapse into a single linear sequence of 16-bit addresses, consumed at full speed by POP.

### The Inner Loop

Introspec's 2017 analysis of Illusion reveals the inner loop. One byte of font data contains 8 bits -- 8 pixels. `LD A,(BC)` reads the byte once, then RLA shifts one bit at a time through 8 unrolled iterations:

```z80 id:ch10_the_inner_loop
; Dotfield scroller inner loop (unrolled for one font byte)
; BC = pointer to font/texture data, SP = pre-built address table

    ld   a,(bc)      ;  7 T  read font byte (once per 8 pixels)
    inc  bc          ;  6 T  advance to next font byte

    ; Pixel 7 (MSB)
    pop  hl          ; 10 T  get screen address from stack
    rla              ;  4 T  shift texture bit into carry
    jr   nc,.skip7   ; 12/7 T  skip if transparent
    set  7,(hl)      ; 15 T  plot the dot
.skip7:
    ; Pixel 6
    pop  hl          ; 10 T
    rla              ;  4 T
    jr   nc,.skip6   ; 12/7 T
    set  6,(hl)      ; 15 T
.skip6:
    ; ... pixels 5 through 0 follow the same pattern,
    ; with SET 5 through SET 0 ...
```

The per-pixel cost, excluding the amortised byte-fetch:

| Path | Instructions | T-states |
|------|-------------|----------|
| Opaque pixel | `pop hl` + `rla` + `jr nc` (not taken) + `set ?,(hl)` | **36** |
| Transparent pixel | `pop hl` + `rla` + `jr nc` (taken) | **26** |

![Bouncing dotfield text scroller in action -- text rendered as individual pixels undulating on a sine wave](../../build/screenshots/ch10_dotscroll.png)

The `LD A,(BC)` and `INC BC` cost 13 T-states amortised over 8 pixels -- about 1.6 T per pixel. Introspec's "36 T-states per pixel" is the worst-case cost within the unrolled byte, excluding that overhead.

The SET bit position changes for each pixel (7, 6, 5 ... 0), which is why the loop is unrolled 8 times rather than repeated. You cannot parameterise the bit position in SET without IX/IY indexing (far too slow) or self-modifying code (overhead). Unrolling is the clean solution.

### The Budget Arithmetic

Let us work the numbers properly. The standard Spectrum 48K frame is 69,888 T-states (the Pentagon clone runs slightly longer at 71,680). Of that, the ULA steals T-states during the active display for memory contention, but the scroller writes to screen memory during the entire frame, not just during the border, so contention is a real factor. In practice, assume about 60,000 usable T-states on a 48K and 65,000 on a Pentagon. Subtract music playback (a typical AY player costs 3,000-5,000 T per frame), screen clearing, and table construction. That leaves roughly 40,000-50,000 T-states for the actual dot rendering.

Consider a display of 8 characters of 8x8 font = 512 font bits per frame (8 chars x 8 bytes x 8 bits). With a typical font fill rate of about 30%, roughly 154 bits are set (opaque) and 358 are clear (transparent). The inner loop cost:

- 154 opaque pixels at 36 T each = 5,544 T
- 358 transparent pixels at 26 T each = 9,308 T
- 64 byte-fetches (`LD A,(BC) : INC BC`) at 13 T each = 832 T
- Total: approximately 15,684 T-states

That is well within a single frame. You could render 20+ characters before hitting the budget ceiling. The bottleneck is not the inner loop -- it is the table construction. Building 512 address entries with sine lookups and screen address calculation costs roughly 100-150 T-states per entry (depending on implementation), adding 50,000-75,000 T to the frame. Illusion solves this by pre-computing the entire table set into memory and cycling through offsets, or by building incrementally: when the scroll advances by one pixel, most table entries shift by one position and only the new column needs full recalculation.

The numbers work because two optimisations compound. Stack-based addressing eliminates all coordinate calculation from the inner loop. Texture-driven transparency eliminates all writes for empty pixels. The table build is expensive, but it runs outside the time-critical DI window and can be spread across the frame.

### How the Bounce Is Encoded

The address table is where the art lives. To create the bouncing motion, a sine table offsets each column's vertical position:

```text
y_offset = sin_table[(column * phase_freq + scroll_pos * speed_freq) & 255]
```

The two frequency parameters control the visual character of the wave. `phase_freq` determines the spatial frequency -- how many wave cycles fit across the visible dot columns. A value of 4 means each dot column advances 4 positions into the sine table, so 256/4 = 64 columns span one full wave cycle. A value of 8 doubles the frequency, creating a tighter ripple. `speed_freq` controls how fast the wave propagates over time: higher values make the bounce scroll faster independently of the text scroll.

The sine table itself is a 256-byte array of signed offsets, page-aligned for fast lookup. Page alignment means the high byte of the table address is fixed; only the low byte changes, so the lookup reduces to:

```z80 id:ch10_how_the_bounce_is_encoded_2
    ld   hl, sin_table    ; H = page, L = don't care
    ld   l, a             ; A = (column * freq + phase) & $FF
    ld   a, (hl)          ; 7 T — one memory read, no arithmetic
```

The values in the table are signed: positive offsets push the dot down, negative offsets push it up. The amplitude is baked into the table at generation time. A table with range -24 to +24 gives a bounce of 48 scanlines peak-to-peak. Generating the table is a one-time cost, typically done offline or during initialisation using a lookup or a simple approximation. On the Z80, computing true sine values at runtime is expensive, so demoscene coders either pre-compute tables externally or use quadrant symmetry: calculate one quarter-wave (64 entries), then mirror and negate to fill the remaining three quarters.

Given each dot's (x, y + y_offset), the Spectrum screen address is calculated and stored in the table. The table-building code runs once per frame, outside the inner loop. The inner loop sees only a stream of pre-computed addresses.

### Beyond Simple Sine: Lissajous, Helix, and Multi-Wave Patterns

The beauty of the pre-computed table approach is that the inner loop does not care what shape the motion follows. It consumes addresses at a fixed cost regardless of the trajectory that generated them. This makes it trivial to experiment with different movement patterns -- all the complexity lives in the table-building code.

A **Lissajous pattern** adds a horizontal sine offset as well as the vertical one. Instead of each column mapping to a fixed x byte on screen, the x position also oscillates:

```text
x_offset = sin_table[(column * x_freq + phase_x) & 255]
y_offset = sin_table[(column * y_freq + phase_y) & 255]
```

When `x_freq` and `y_freq` are coprime (say 3 and 2), the dot field traces a Lissajous figure -- the classic oscilloscope pattern. The text becomes a ribbon weaving through space. Different frequency ratios produce dramatically different shapes: 1:1 gives a circle or ellipse, 1:2 gives a figure-eight, 2:3 gives the trefoil pattern familiar from old analogue test equipment.

A **helix** or spiral effect uses a single phase that advances per column, but varies the amplitude:

```text
amplitude = base_amp + sin_table[(column * 2 + time) & 255] * depth_scale
y_offset = sin_table[(column * freq + phase) & 255] * amplitude / max_amp
```

This creates the illusion of dots receding into depth -- the wave flattens at the "far" point of the spiral and expands at the "near" point.

**Multi-wave superposition** is the simplest technique with the most dramatic payoff. Add two sine terms with different frequencies:

```text
y_offset = sin_table[(col * 4 + phase1) & 255] + sin_table[(col * 7 + phase2) & 255]
```

The result is a complex, organic-looking undulation that never quite repeats. Advancing `phase1` and `phase2` at different speeds produces continuously evolving motion from just two table lookups per column. Three or more harmonics create waves that look almost fluid-dynamic. This is the cheapest possible way to generate complex motion -- each additional harmonic costs one table lookup and one addition per column in the table builder, and the inner loop cost remains unchanged.

---

## Part 2: 4-Phase Colour Animation

### The Colour Problem

Each 8x8 cell has one ink colour (0-7) and one paper colour (0-7). Within a single frame, you get exactly two colours per cell. But the Spectrum runs at 50 frames per second, and the human eye does not see individual frames at that rate. It sees the average.

### The Trick

Introspec's 4-phase technique cycles through four frames:

1. **Normal A:** ink = C1, paper = C2. Pixel data = pattern A.
2. **Normal B:** ink = C3, paper = C4. Pixel data = pattern B.
3. **Inverted A:** ink = C2, paper = C1. Pixel data = pattern A (same pixels, swapped colours).
4. **Inverted B:** ink = C4, paper = C3. Pixel data = pattern B (same pixels, swapped colours).

At 50Hz, each frame displays for 20 milliseconds. The four-frame cycle completes in 80ms -- 12.5 cycles per second, above the flicker-fusion threshold on CRT displays.

### The Maths of Perception

Trace a single pixel that is "on" in pattern A and "off" in pattern B:

| Frame | Pixel state | Displayed colour |
|-------|-------------|-----------------|
| Normal A | on (ink) | C1 |
| Normal B | off (paper) | C4 |
| Inverted A | on (ink) | C2 |
| Inverted B | off (paper) | C3 |

The eye perceives the average: (C1 + C2 + C3 + C4) / 4.

Now check: a pixel "on" in both patterns sees C1, C3, C2, C4. A pixel "off" in both sees C2, C4, C1, C3. All cases produce the same average. The pixel pattern does not affect the perceived hue -- only the choice of C1 through C4 does.

Then why have two patterns? Because the *intermediate* transitions matter. A pixel that alternates between bright red and bright green flickers noticeably at 12.5Hz. A pixel alternating between similar shades barely flickers at all. The dithering patterns -- checkerboards, halftone grids, ordered matrices -- control the *texture* of the flicker. Introspec chose patterns so that transitions between frames produced minimal visible oscillation. This is anti-clashing pixel selection: the careful arrangement of "on" and "off" bits to ensure that no pixel toggles between dramatically different colours in consecutive frames.

### Why Inversion Is Essential

Without the inversion step, "on" pixels would always show ink and "off" pixels would always show paper. You would get exactly two visible colours per cell, flickering between two different pairs. The inversion ensures both ink and paper contribute to both pixel states across the cycle, mixing all four colours into the perceived output.

On the Spectrum, inversion is cheap. The attribute byte layout is `FBPPPIII` -- Flash, Bright, 3 bits of paper colour, 3 bits of ink colour. Swapping ink and paper means rotating the lower 6 bits: paper moves to ink position, ink moves to paper position, while Flash and Bright stay put. In code:

```z80 id:ch10_why_inversion_is_essential
; Swap ink and paper in attribute byte (A)
; Input:  A = F B P2 P1 P0 I2 I1 I0
; Output: A = F B I2 I1 I0 P2 P1 P0
    ld   b, a
    and  $C0           ; isolate Flash + Bright bits
    ld   c, a          ; save FB------
    ld   a, b
    and  $38           ; isolate paper (--PPP---)
    rrca
    rrca
    rrca               ; paper now in ink position (-----PPP)
    ld   d, a          ; save ink-from-paper
    ld   a, b
    and  $07           ; isolate ink (-----III)
    rlca
    rlca
    rlca               ; ink now in paper position (--III---)
    or   d             ; combine: --IIIPPP
    or   c             ; combine: FBIIIPPP = swapped attribute
```

The alternative is to pre-compute both normal and inverted attribute buffers at initialisation and simply cycle buffer pointers at runtime. This trades 3,072 bytes of memory for zero per-frame computation -- a worthwhile trade on 128K machines with memory to spare.

### Practical Cost

Four pre-built attribute buffers, cycled once per frame. The per-frame cost is a block copy of 768 bytes into attribute RAM ($5800-$5AFF). Using LDIR, this costs 21 T-states per byte: 768 x 21 = 16,128 T-states. Using the stack trick (POP from the source buffer, switch SP, PUSH to attribute RAM, batching through register pairs and shadow registers), a realistic cost is around 11,000-13,000 T-states depending on batch size and loop overhead -- a modest 1.2-1.5x speedup over LDIR. The gain is smaller than you might expect because each batch requires two SP switches (save source position, load destination, then swap back), and that overhead largely offsets the raw speed advantage of POP+PUSH over LDIR. For a *fill* (writing the same value to every byte), the PUSH trick is far more effective -- load register pairs once, then PUSH repeatedly -- but a copy from varying source data cannot avoid the read cost.

The cycle logic itself is trivial. A single variable holds the phase (0-3). Each frame, increment it and AND with 3 to wrap. Index into a 4-entry table of buffer base addresses:

```z80 id:ch10_practical_cost
    ld   a, (phase)
    inc  a
    and  3
    ld   (phase), a
    add  a, a           ; phase * 2 (pointer table is 16-bit entries)
    ld   hl, buf_ptrs
    ld   e, a
    ld   d, 0
    add  hl, de
    ld   a, (hl)
    inc  hl
    ld   h, (hl)
    ld   l, a           ; HL = source buffer address
    ld   de, $5800      ; DE = attribute RAM
    ld   bc, 768
    ldir                ; copy attributes for this phase
```

Memory: 4 x 768 = 3,072 bytes for the buffers. On a 48K machine that is a significant chunk; on 128K you can place buffers in paged banks. The pixel patterns (A and B) are written once at initialisation and never touched again -- only the attribute RAM changes each frame.

### Text Overlay

In Eager, scrolling text overlays the colour animation. There are several approaches, each with different trade-offs.

The simplest is **cell exclusion**: reserve certain character cells for text, skip them during the colour cycle, and write fixed white-on-black attributes with actual font glyphs. This is easy to implement -- just mask those cells out of the LDIR copy -- but creates a hard visual boundary between the animated background and the static text region. The text looks pasted on.

A more sophisticated approach is **pattern integration**: the glyph shapes override specific bits in both pixel patterns A and B. Where the font has a set bit, both patterns get that bit set (or cleared, depending on the desired text colour). This ensures the text pixel shows the same colour in all four phases -- it does not flicker because it never transitions between different colour states. The surrounding pixels continue to cycle normally. The result is text that appears to float on the animated background, with colour bleeding up to the edges of each letterform. The cost is that you must regenerate (or patch) the pixel patterns whenever the text scrolls, which adds a few thousand T-states per frame depending on how many cells contain text.

A third option for 128K machines is **layer compositing**: maintain the 4-phase background in one set of memory pages and the text scroller in another, then combine them during the attribute copy. This keeps the two systems independent -- the scroller does not need to know about the colour animation and vice versa -- at the cost of a slightly more complex copy loop that masks text cells.

---

## Demoscene Lineage

The dotfield scroller did not appear from nowhere. The technique sits in a lineage of ZX Spectrum effects that stretches from the mid-1980s to the present.

The earliest Spectrum scrollers were simple character-cell affairs: LDIR-based horizontal scrolls that shifted an entire line of character cells, one byte at a time. Pixel-smooth scrolling was harder -- the Spectrum has no hardware scroll register, so every pixel shift requires rewriting the bitmap data. By the early 1990s, demo coders had developed several approaches: RL/RR-based pixel scrolling (shifting every byte in a screen line), look-up table scrollers (pre-shifted copies of each character), and the double-buffer technique (draw into a back buffer, copy to screen). All of these were limited by the fundamental cost of moving bytes in and out of video RAM.

The dotfield approach breaks from this tradition entirely. Instead of scrolling a contiguous block of pixels, it decomposes the text into individual dots and places each one independently. This was Dark's insight in the mid-1990s: if you give up the idea of a solid font and accept a pointillist rendering, you can use the POP trick to place each dot with minimal overhead. The visual result -- text dissolving into a cloud of particles, bouncing on a sine wave -- became one of the signature effects of the Russian demoscene.

X-Trade's *Illusion* (ENLiGHT'96) was the demo that made the technique famous in the Spectrum world. The dotfield scroller was its centrepiece effect, running smoothly alongside music and other visual elements. Dark published the algorithmic principles in *Spectrum Expert* issues #01 and #02 (1997-98), where he described the general approach to POP-based rendering and sine-table animation. Two decades later, Introspec's detailed reverse-engineering of the Illusion binary (published in *Hype* magazine, 2017) confirmed Dark's claims and provided the exact cycle counts that the community had long speculated about.

The 4-phase colour technique has a different pedigree. Colour-cycling on the Spectrum has been explored since the 1980s -- simple two-frame alternation (flash-like effects) was common in games and demos. But the systematic four-phase approach, with its careful inversion step to ensure all four colours contribute equally, was refined by Introspec for *Eager* (3BM Open Air 2015). The party version's file_id.diz explicitly mentions the technique, and Introspec's "Making of Eager" article in *Hype* (2015) describes the design process: choosing colours so that adjacent phases minimise visible flicker, and using dithering patterns that distribute the transitions evenly across the cell.

The broader principle -- temporal multiplexing of colour -- appears on other platforms too. The Atari 2600 famously alternates frames to create flickering pseudo-sprites. The Game Boy uses a similar trick for pseudo-transparency. On the Spectrum, the technique is particularly effective because the CRT phosphor persistence smooths the transitions more than an LCD would. This is worth noting for modern viewers: 4-phase colour looks substantially better on a real CRT or a good CRT emulator (with phosphor simulation) than on a raw pixel-perfect display.

---

## The Shared Principle: Temporal Cheating

The dotfield scroller uses 50 frames per second for *spatial* flexibility. Each frame is a snapshot of dot positions at one instant; the viewer's brain interpolates between snapshots to perceive smooth motion. The CPU's job is to *place* dots as fast as possible, reading pre-computed addresses from the stack.

The 4-phase colour animation uses 50 frames per second for *colour* flexibility. Each frame displays one of four colour states; the viewer's retina averages them. No single frame contains the perceived result -- it exists only in persistence of vision.

Both exploit the same physical reality: the CRT refreshes at 50Hz, and the human visual system cannot resolve individual frames at that rate. The Spectrum's *temporal* resolution is far richer than its spatial or colour resolution. Demoscene coders discovered that temporal resolution is the cheapest axis to exploit.

Both reduce their inner loops to the absolute minimum. The scroller to 36 T-states per dot. The colour animation to a single buffer copy per frame. Both move complexity out of the inner loop into pre-computation. And both produce results that look, to the casual viewer, like the hardware should not be capable of them.

This is what makes the demoscene a temporal art form. A screenshot of a dotfield scroller shows a scatter of pixels. A screenshot of a 4-phase colour animation shows two colours per cell, exactly as the hardware specifies. You have to see them *move* to see them work. The beauty is in the sequence, not the frame.

---

## Practical 1: A Bouncing Dot-Matrix Text Scroller

Build a simplified dotfield scroller: a short text message rendered as a bouncing dot-matrix field using POP-based addressing.

**Data structures.** A page-aligned 8x8 bitmap font (the ROM font at `$3D00` works). A 256-byte sine table for the bounce offset. A RAM buffer for the address table (up to 4,096 x 2 bytes).

**Table construction.** Before each frame, iterate through the visible characters. For each bit in each font byte, calculate the screen address incorporating the sine-wave bounce offset, and store it in the address table. This runs once per frame outside the inner loop.

**Rendering.** Disable interrupts. Save SP via self-modifying code. Point SP at the address table. Execute the unrolled inner loop: `ld a,(bc) : inc bc`, then 8 repetitions of `pop hl : rla : jr nc,skip : set N,(hl)` with N from 7 down to 0. Restore SP. Enable interrupts.

**Main loop.** `halt` (sync to 50Hz), clear the screen (PUSH-based clear from Chapter 3), build the address table, render the dotfield, advance scroll position and bounce phase.

**Extensions.** Partial screen clearing (track the bounding box). Double buffering via shadow screen on 128K. Multiple bounce harmonics. Variable dot density for a sparser, more ethereal look.

---

## Practical 2: A 4-Phase Colour Cycling Animation

Build a 4-phase colour animation producing smooth gradients.

**Pixel patterns.** Fill bitmap memory with two complementary dither patterns. The simplest: even pixel lines get `$55` (01010101), odd lines get `$AA` (10101010). For production quality, use an ordered 4x4 Bayer matrix.

**Attribute buffers.** Pre-calculate four 768-byte buffers. Buffers 0 and 1 hold normal attributes with two different colour schemes (varying ink/paper across the screen for a diagonal gradient). Buffers 2 and 3 are the inverted versions -- ink and paper bits swapped. The swap is a bit rotation: three RRCAs to move ink bits to paper position, three RLCAs the other way, mask and combine.

**Main loop.** Each frame: `halt`, index into a 4-entry table of buffer pointers using a phase counter (AND 3), LDIR 768 bytes to `$5800`, increment the phase counter. That is the entire runtime engine -- about 16,000 T-states per frame.

**Animation.** For a moving gradient, regenerate one buffer per frame (the one about to become the oldest in the 4-frame cycle) with an advancing colour offset. This maintains a pipeline: display frame N while generating frame N+4. Alternatively, pre-compute all buffers across 128K banks for zero runtime cost.

---

## Summary

- The **dotfield scroller** renders text as individual dots. The inner loop -- `pop hl : rla : jr nc,skip : set ?,(hl)` -- costs 36 T-states per opaque pixel, 26 per transparent pixel.
- **Stack-based addressing** encodes the bounce trajectory as pre-built screen addresses. POP retrieves them at 10 T-states each -- the fastest random-access read on the Z80.
- **4-phase colour** cycles 4 attribute frames (2 normal + 2 inverted) at 50Hz. Persistence of vision averages the colours, creating the illusion of more than 2 colours per cell.
- The **inversion step** ensures all four colours contribute to every pixel position.
- Both techniques exploit **temporal resolution** to create effects impossible in any single frame.
- The scroller uses the stack for spatial flexibility; the colour animation uses frame alternation for colour flexibility -- the two main axes of demoscene cheating.

---

## Try It Yourself

1. Build the dotfield scroller. Start with a single static character plotted via the POP-based inner loop. Verify the expected timing with the border harness from Chapter 1. Then add the bounce table and watch it undulate.

2. Experiment with bounce parameters. Change the sine amplitude, spatial frequency, and phase speed. Small changes produce dramatic visual differences.

3. Build the 4-phase colour animation. Start with uniform colour (all cells the same in each phase). Verify you see a steady colour that is neither the ink nor the paper of any single frame. Then add the diagonal gradient.

4. Try different dithering patterns. Checkerboard, 2x2 blocks, Bayer matrix, random noise. Which minimise visible flicker? Which produce the smoothest perceived gradients?

5. Combine both techniques: 4-phase colour background with a monochrome dotfield scroller on top.

---

> **Sources:** Introspec, "Technical Analysis of Illusion by X-Trade" (Hype, 2017); Introspec, "Making of Eager" (Hype, 2015); Dark, "Programming Algorithms" (Spectrum Expert #01, 1997). The inner loop disassembly and cycle counts follow Introspec's 2017 analysis. The 4-phase colour technique is described in the Eager making-of article and the party version's file_id.diz.
