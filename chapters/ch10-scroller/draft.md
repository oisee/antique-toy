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

Picture a message -- "ILLUSION BY X-TRADE" -- rendered not in solid block characters but as a field of individual dots, each dot a single pixel. The text drifts horizontally across the screen in a smooth scroll. But the dots are not sitting on flat scan lines. They bounce. The entire dot field undulates in a sine wave, each column offset vertically from its neighbours, creating the impression of text rippling on the surface of water.

### The Font as Texture

The font is stored as a bitmap texture in memory -- one bit per dot. If the bit is 1, a dot appears on screen. If the bit is 0, nothing happens. The critical word is *transparent*. In a normal renderer, you write every pixel position. In the dotfield scroller, transparent pixels are nearly free. You check the bit, and if it is zero, you skip. Only the set pixels require a write to video memory.

This means rendering cost is proportional to the number of visible dots, not the total area. A typical 8x8 character might have 20 set pixels out of 64. For a large scrolling message, this economy matters enormously. BC points to the font data; RLA shifts each bit into the carry flag to determine on or off.

### Stack-Based Address Tables

In a conventional scroller, each pixel's screen position is calculated from (x, y) coordinates using the Spectrum's interleaved address formula. That calculation involves shifts, masks, and lookups. Doing it for thousands of pixels per frame would consume the entire budget.

Dark's solution: pre-calculate every screen address and store them as a table that the stack pointer walks through. POP reads 2 bytes and auto-increments SP, all in 10 T-states. Point SP at the table instead of the real stack, and POP becomes the fastest possible address retrieval -- no index registers, no pointer arithmetic, no overhead.

The bouncing motion is encoded entirely in the address table. Each entry is a screen address that already includes the vertical sine offset. The "bounce" does not happen at render time. It happened when the table was built. All three dimensions of the animation -- scroll position, bounce wave, character shape -- collapse into a single linear sequence of 16-bit addresses, consumed at full speed by POP.

### The Inner Loop

Introspec's 2017 analysis of Illusion reveals the inner loop. One byte of font data contains 8 bits -- 8 pixels. `LD A,(BC)` reads the byte once, then RLA shifts one bit at a time through 8 unrolled iterations:

```z80
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

The `LD A,(BC)` and `INC BC` cost 13 T-states amortised over 8 pixels -- about 1.6 T per pixel. Introspec's "36 T-states per pixel" is the worst-case cost within the unrolled byte, excluding that overhead.

The SET bit position changes for each pixel (7, 6, 5 ... 0), which is why the loop is unrolled 8 times rather than repeated. You cannot parameterise the bit position in SET without IX/IY indexing (far too slow) or self-modifying code (overhead). Unrolling is the clean solution.

### The Budget Arithmetic

The Pentagon frame budget is 71,680 T-states. Assuming 60-70% is available for the scroller (the rest going to music, screen clearing, table setup), that is roughly 45,000 T-states.

Consider 4,096 dots (8 characters of 8x8 text). A typical font is about 30% filled: 1,200 opaque dots at 36 T each, 2,900 transparent at 26 T each. Total: 43,200 + 75,400 + 6,656 (byte-fetch overhead) = approximately 125,000 T-states. That is about 1.75 frames -- the scroller updates at roughly 28 fps, comfortably smooth.

The numbers work because two optimisations compound. Stack-based addressing eliminates all coordinate calculation. Texture-driven transparency eliminates all writes for empty pixels.

### How the Bounce Is Encoded

The address table is where the art lives. To create the bouncing motion, a sine table offsets each column's vertical position:

```
y_offset = sin_table[(column * 8 + scroll_pos * 2) & 255]
```

The multiplication by 8 controls spatial frequency; the factor of 2 on scroll position controls phase speed. Given each dot's (x, y + y_offset), the Spectrum screen address is calculated and stored in the table. The table-building code runs once per frame, outside the inner loop. The inner loop sees only a stream of pre-computed addresses.

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

On the Spectrum, inversion is cheap -- swap the ink and paper bits in the attribute byte, or pre-compute both normal and inverted buffers and cycle between them.

### Practical Cost

Four pre-built attribute buffers, cycled once per frame. The per-frame cost is a block copy of 768 bytes into attribute RAM: about 16,000 T-states via LDIR, or about 4,500 T-states via PUSH tricks. Less than a quarter of the frame budget either way.

Memory: 4 x 768 = 3,072 bytes for the buffers. The pixel patterns (A and B) are written once at initialisation and never touched again.

### Text Overlay

In Eager, scrolling text overlays the colour animation. The simplest approach reserves certain cells for text, excluding them from the colour cycle -- fixed white-on-black attributes with actual font glyphs. A more sophisticated approach integrates text into the phase animation: the glyph shapes override specific bits in patterns A and B, ensuring text is visible in every frame while surrounding pixels still cycle. This produces text that appears to float on the animated background, with colour bleeding up to the edges of each letterform.

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
