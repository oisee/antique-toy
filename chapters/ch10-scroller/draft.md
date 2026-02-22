# Chapter 10: The Dotfield Scroller and 4-Phase Colour

> *"Two normal frames and two inverted frames. The eye sees the average."*
> -- Introspec, Making of Eager (2015)

---

The ZX Spectrum displays two colours per 8x8 cell. Text scrolls across a screen at whatever rate the CPU can manage. These are fixed constraints -- the hardware does what it does, and no amount of cleverness will change the silicon.

But cleverness can change what the viewer *perceives*.

This chapter brings together two techniques from two different demos, separated by nearly twenty years but connected by a shared principle. The dotfield scroller from X-Trade's *Illusion* (ENLiGHT'96) renders text as a bouncing cloud of individual dots, each one placed with pixel-perfect precision at a cost of just 36 T-states. The 4-phase colour animation from Introspec's *Eager* (3BM Open Air 2015) alternates four carefully constructed frames at 50Hz to trick the eye into seeing colours the hardware cannot produce. One exploits spatial resolution -- placing dots wherever you want, unconstrained by character cells. The other exploits temporal resolution -- cycling frames faster than the eye can follow. Together they demonstrate the two main axes of cheating on constrained hardware: space and time.

---

## Part 1: The Dotfield Scroller

### What the Viewer Sees

Picture a message -- "ILLUSION BY X-TRADE" -- rendered not in solid block characters but as a field of individual dots, each dot a single pixel. The text drifts horizontally across the screen in a smooth scroll. But the dots are not sitting on flat scan lines. They bounce. The entire dot field undulates in a sine wave, each column of dots offset vertically from its neighbours, creating the impression that the text is rippling on the surface of water. The motion is continuous and fluid. It looks expensive. It is not.

### The Font as Texture

The text in a dotfield scroller is not drawn using the ROM character set or standard bitmap rendering. Instead, the font is stored as a texture -- a bitmap in memory where each bit represents one dot. If the bit is 1, a dot appears on screen. If the bit is 0, nothing happens -- the dot is transparent.

The critical word is *transparent*. In a normal character renderer, you write both set and unset pixels to screen memory: black ink on white paper, or whatever your colours are. Every pixel position costs you a write. In the dotfield scroller, transparent pixels cost almost nothing. You check the bit, and if it is zero, you skip. Only the set pixels -- the actual dots of the text -- require a write to video memory.

This means the cost of rendering is proportional to the number of visible dots, not to the total area of the text. A typical 8x8 character might have 20 set pixels out of 64. You are paying for 20 operations instead of 64. For a large scrolling message, this matters enormously.

BC points to the font data in memory. As the inner loop runs, BC advances through the texture byte by byte, and RLA shifts each bit into the carry flag to determine whether that dot is on or off.

### Stack-Based Address Tables

Here is where the design gets interesting. In a conventional scroller, each pixel's screen position is calculated from its (x, y) coordinates using the Spectrum's interleaved screen address formula. That calculation is not cheap -- it involves shifts, masks, and lookups. Doing it for thousands of pixels per frame would consume the entire budget.

Dark's solution: pre-calculate every screen address in advance and store them in a table. But not just any table. The addresses are pushed onto the stack.

The Z80's POP instruction reads 2 bytes from the address in SP and increments SP, all in 10 T-states. If SP points not to the actual program stack but to a pre-built table of screen addresses, then POP becomes the fastest possible way to retrieve the next destination address. No index registers. No pointer arithmetic. No memory-mapped lookup tables. Just POP -- 10 T-states, and you have the screen address for the next dot.

The bouncing motion is encoded entirely in the address table. Each entry in the table is a screen address that already includes the vertical offset for that dot's position in the sine wave. The "bounce" does not happen at render time. It happened when the table was built. At render time, the CPU simply reads addresses in order and plots dots at those positions. The path of every dot through the bounce pattern is pre-calculated and frozen into the address sequence.

For each frame of animation, you build a new address table (or select from a set of pre-built tables corresponding to different scroll positions and bounce phases). The table encodes: which column of the text is visible, what the horizontal scroll offset is, and what the vertical bounce offset is at each position. All three dimensions of the animation -- scroll, bounce, and character shape -- collapse into a single linear sequence of 16-bit addresses.

### The Inner Loop

Introspec's 2017 analysis of Illusion's scroller reveals the inner loop. It is five instructions:

```z80
; Dotfield scroller inner loop
; BC  = pointer to font/texture data
; SP  = pointer to pre-built screen address table
; The bit position for SET is fixed per pass (self-modified or unrolled)

    ld   a,(bc)      ;  7 T  read texture byte
    pop  hl          ; 10 T  get next screen address from the stack
    rla              ;  4 T  shift texture bit into carry
    jr   nc,$+4      ;  7 T  skip SET if bit is 0 (transparent)
    set  ?,(hl)      ; 15 T  set the pixel on screen
                     ;       (? = bit position, 0-7)
```

Let us count the cost per pixel.

**When the dot is transparent (bit = 0):**

| Instruction | T-states |
|-------------|----------|
| `ld a,(bc)` | 7 |
| `pop hl` | 10 |
| `rla` | 4 |
| `jr nc,$+4` | 12 (taken) |
| **Total** | **33** |

Wait -- the `JR NC` costs 12 T-states when the branch is taken (the common case for transparent pixels) and 7 when it falls through. Let us reconsider. Actually, the `JR` instruction costs 12 T-states when the jump is taken and 7 when it is not taken. For a transparent pixel, carry is clear, so NC is true, the jump is taken, and we skip the SET. That is 12 T. For an opaque pixel, carry is set, NC is false, the jump is not taken (7 T), and we fall through to `SET ?,(HL)` at 15 T.

But Introspec quotes 36 T-states as the cost per pixel. Let us look at this more carefully. The 36 T-states figure accounts for the *worst case* path -- the opaque pixel:

| Instruction | T-states |
|-------------|----------|
| `ld a,(bc)` | 7 |
| `pop hl` | 10 |
| `rla` | 4 |
| `jr nc,$+4` | 7 (not taken -- pixel is opaque) |
| `set ?,(hl)` | 15 |
| **Total** | **43** |

Hmm -- that gives 43, not 36. There is a subtlety I have glossed over. The inner loop as Introspec documented it does not re-read the texture byte for every pixel. One byte of font data contains 8 bits -- 8 pixels. The `LD A,(BC)` reads the byte once, and then RLA shifts one bit at a time through 8 iterations. BC advances only after all 8 bits of the current byte are consumed.

The amortised loop, then, looks more like this:

```z80
; Full texture byte processing (8 pixels from one font byte)
    ld   a,(bc)      ;  7 T  read one font byte (once per 8 pixels)
    inc  bc          ;  6 T  advance to next font byte

    ; Pixel 7 (MSB)
    pop  hl          ; 10 T
    rla              ;  4 T
    jr   nc,.skip7   ; 12/7 T
    set  7,(hl)      ; 15 T
.skip7:

    ; Pixel 6
    pop  hl          ; 10 T
    rla              ;  4 T
    jr   nc,.skip6   ; 12/7 T
    set  6,(hl)      ; 15 T
.skip6:

    ; ... pixels 5 through 0 follow the same pattern ...
```

Now the per-pixel cost for an opaque pixel is:

| Instruction | T-states |
|-------------|----------|
| `pop hl` | 10 |
| `rla` | 4 |
| `jr nc` | 7 (not taken) |
| `set ?,(hl)` | 15 |
| **Total** | **36** |

And for a transparent pixel: 10 + 4 + 12 = **26** T-states (the JR is taken, skipping the SET).

The `LD A,(BC)` and `INC BC` together cost 13 T-states, amortised over 8 pixels -- about 1.6 T-states per pixel. Introspec's "36 T-states per pixel" figure refers to the worst-case per-pixel cost *within* the unrolled byte loop, excluding the one-time byte fetch overhead.

Thirty-six T-states. To place a single dot at an arbitrary screen location, following a pre-calculated bounce path, with automatic transparency handling.

### The Budget Arithmetic

What can you do with 36 T-states per pixel?

The Pentagon frame budget is 71,680 T-states. If the scroller consumed the entire frame -- no music, no other effects, no overhead -- you could plot 71,680 / 36 = 1,991 opaque dots per frame. In practice, you need time for music, screen clearing, and the address table setup, so perhaps 60-70% of the frame is available for rendering. Call it 45,000 T-states for the scroller proper. That gives you about 1,250 opaque dots.

But remember: transparent dots are cheaper -- 26 T-states each. A typical font glyph is perhaps 30% filled. So in a field of 4,096 dots (say, 8 characters of 8x8 text at various scroll positions), roughly 1,200 are opaque (36 T each) and 2,900 are transparent (26 T each). Total: 1,200 x 36 + 2,900 x 26 = 43,200 + 75,400 = 118,600 T-states. Add the byte-fetch overhead: 4,096 / 8 x 13 = 6,656 T-states. Grand total: about 125,000 T-states.

That is roughly 1.75 frames. At 50Hz, the scroller updates at about 28 fps -- comfortably smooth for a scrolling text effect, with headroom for music and the address table rebuild.

The numbers work because of the two optimisations working in concert. The stack-based addressing eliminates all coordinate calculation. The texture-driven transparency eliminates all writes for empty pixels. Together, they reduce the per-pixel cost to a point where thousands of dots per frame become feasible on a 3.5 MHz processor.

### Why the Stack?

You might wonder: why use the stack for the address table? Why not a regular pointer with `LD HL,(IX+d)` or similar indexed addressing?

The answer is speed. Compare the alternatives for fetching a 16-bit address:

| Method | T-states | Notes |
|--------|----------|-------|
| `pop hl` | 10 | Auto-increments SP |
| `ld l,(hl) : ld h,(hl)` | ~18 | Two reads, needs pointer management |
| `ld hl,(nn)` | 16 | Fixed address, no auto-increment |
| `ld l,(ix+d) : ld h,(ix+d)` | 38 | IX-indexed, painfully slow |

POP is nearly twice as fast as the next practical option and four times faster than IX-indexed addressing. The auto-increment is free -- SP advances automatically, ready for the next POP. No pointer housekeeping. No INC instructions. The address table *streams* through the CPU at maximum speed.

The price is the usual one for stack tricks: interrupts must be disabled while SP is hijacked, and the real stack is unavailable. The address table must be built before the rendering pass begins, and SP must be saved and restored (via self-modifying code, as we saw in Chapter 3) around the rendering loop. These are standard costs in demoscene programming.

### How the Bounce Is Encoded

The address table is where the art lives. Each entry is a 16-bit screen address that specifies *exactly* where a dot will appear -- both its horizontal position (encoded in the byte offset and bit position) and its vertical position (encoded in the screen address's line component, following the Spectrum's interleaved layout).

To create the bouncing motion, you pre-calculate a sine table (Chapter 4) and use it to offset the vertical position of each column of dots. For scroll position *s* and column *c*, the vertical offset might be:

```
y_offset = sin_table[(c * 8 + s * 2) & 255]
```

The multiplication by 8 controls the spatial frequency of the wave (how many undulations are visible across the screen). The multiplication by 2 on the scroll position controls the phase speed (how fast the wave appears to move). Both are trivially adjustable.

Given the base y-position and the y_offset, you calculate the Spectrum screen address using the standard algorithm (or a lookup table), and store it in the address table. The horizontal position is encoded in which byte of the screen line and which bit position the SET instruction will use.

For animation, each frame you rebuild the address table with a new scroll position (shifting which characters are visible and where) and a new phase offset for the bounce. The table-building code runs once per frame, outside the inner loop, and its cost is amortised. The inner loop sees only a stream of pre-computed addresses.

---

## Part 2: 4-Phase Colour Animation

### The Colour Problem

The ZX Spectrum's colour system is brutally simple. Each 8x8 pixel cell has one attribute byte specifying an ink colour (0-7) and a paper colour (0-7), plus a brightness bit shared between them. Within any single cell, you get exactly two colours. There is no way around this in a single frame.

But the Spectrum runs at 50 frames per second. And the human eye does not see individual frames at that rate. It sees the *average*.

### The Trick

Introspec's 4-phase colour technique, used in Eager (2015), exploits persistence of vision to create the illusion of more than two colours per cell. The method cycles through four frames in sequence:

**Frame 1 (Normal A):** Ink = colour1, Paper = colour2. Pixel data = pattern A.

**Frame 2 (Normal B):** Ink = colour3, Paper = colour4. Pixel data = pattern B.

**Frame 3 (Inverted A):** Ink = colour2, Paper = colour1. Pixel data = pattern A (same pixels as Frame 1, but ink and paper are swapped).

**Frame 4 (Inverted B):** Ink = colour4, Paper = colour3. Pixel data = pattern B (same pixels as Frame 2, but ink and paper are swapped).

Then the cycle repeats: 1, 2, 3, 4, 1, 2, 3, 4, ...

At 50Hz, each frame displays for 20 milliseconds. The four-frame cycle completes in 80 milliseconds -- 12.5 cycles per second, well above the flicker-fusion threshold for most viewers (especially on CRT displays, where phosphor persistence helps smooth the transitions).

What does the eye see? Consider a single pixel position. Across the four frames, that position is "on" (ink colour) in some frames and "off" (paper colour) in others. The perceived colour is a weighted average of the colours displayed at that position across the cycle.

Here is the key: because Frames 1 and 3 use the same pixel pattern but with swapped ink and paper, a pixel that is "on" (ink) in Frame 1 becomes "off" (paper) in Frame 3 -- but with the ink and paper colours reversed. The same swap happens between Frames 2 and 4. This means every pixel position sees all four colours -- colour1, colour2, colour3, colour4 -- during the cycle, just in different proportions depending on whether it is "on" or "off" in each pattern.

### The Maths of Perception

Let us trace what happens at a single pixel position. Suppose it is "on" in pattern A and "off" in pattern B.

| Frame | Attribute | Pixel state | Displayed colour |
|-------|-----------|-------------|-----------------|
| 1 (Normal A) | ink=C1, paper=C2 | on (ink) | C1 |
| 2 (Normal B) | ink=C3, paper=C4 | off (paper) | C4 |
| 3 (Inverted A) | ink=C2, paper=C1 | on (ink) | C2 |
| 4 (Inverted B) | ink=C4, paper=C3 | off (paper) | C3 |

The eye perceives the average: (C1 + C4 + C2 + C3) / 4. All four colours contribute equally.

Now suppose the pixel is "on" in *both* patterns:

| Frame | Attribute | Pixel state | Displayed colour |
|-------|-----------|-------------|-----------------|
| 1 (Normal A) | ink=C1, paper=C2 | on (ink) | C1 |
| 2 (Normal B) | ink=C3, paper=C4 | on (ink) | C3 |
| 3 (Inverted A) | ink=C2, paper=C1 | on (ink) | C2 |
| 4 (Inverted B) | ink=C4, paper=C3 | on (ink) | C4 |

Same result: (C1 + C3 + C2 + C4) / 4. Again, equal contribution from all four colours.

The same holds if the pixel is "off" in both patterns, or "off" in A and "on" in B. In all four cases, the perceived colour is the same average. This means the pixel data does not matter for the average colour -- only the choice of C1, C2, C3, C4 determines the perceived hue.

But wait -- if the average is always the same regardless of pixel state, what is the point of having two different patterns? The answer: the *intermediate* colours matter. Between the averaged states, the pixel flickers through different colour combinations. The pixel patterns control the *texture* of the flicker. A pixel that alternates between bright red and bright green flickers noticeably at 12.5Hz. A pixel that alternates between two similar shades of yellow barely flickers at all. The choice of patterns -- which pixels are "on" in A versus B -- determines how smooth or coarse the perceived colour appears.

This is where anti-clashing pixel selection enters. Introspec carefully chose patterns A and B so that the transitions between frames produced minimal visible flicker. Dithering patterns -- checkerboards, halftone grids, and ordered dithering matrices -- ensure that no individual pixel toggles too aggressively between very different colours. The result is a perceived palette that feels richer than the Spectrum's native 15 colours, with smooth gradients emerging from the temporal averaging.

### Why Inversion?

The inversion step -- swapping ink and paper between Frames 1/3 and 2/4 -- is essential. Without it, "on" pixels would always show the ink colour and "off" pixels would always show the paper colour. You would get exactly two visible colours, just flickering between two different pairs. The inversion ensures that both ink and paper contribute to both "on" and "off" pixels across the cycle, mixing all four colours into the perceived output.

On the ZX Spectrum, inverting the display is cheap. You do not need to rewrite pixel memory. You just swap the ink and paper values in the attribute byte. If the normal attribute is `ink=2, paper=5` (binary: `00101010`), the inverted attribute is `ink=5, paper=2` (binary: `01010010`). Swapping ink and paper is a bit manipulation on the attribute byte -- or, more practically, you pre-compute both the normal and inverted attribute buffers and switch between them.

### Practical Cost

How expensive is 4-phase colour? You need to update the attribute area every frame. That is 768 bytes per frame -- but you are not *calculating* new attributes each frame. You have four pre-built attribute buffers (or two, if you derive the inverted versions on the fly by swapping ink/paper bits), and you cycle through them. The per-frame cost is a block copy of 768 bytes into attribute RAM.

Using LDI chains (Chapter 3), 768 bytes costs 768 x 16 = 12,288 T-states. Using PUSH tricks with the stack pointed at attribute RAM, you can do it even faster: 768 / 2 x 11 = 4,224 T-states for the raw pushes, plus setup and teardown. Either way, the attribute update fits comfortably within the frame budget, leaving ample room for other effects.

The real cost is memory. Four attribute buffers x 768 bytes = 3,072 bytes. On a 128K Spectrum that is trivial. On a 48K machine, it is a meaningful chunk of your 41K of available RAM, but still manageable.

The pixel patterns (A and B) only need to be written once -- they sit in bitmap memory and do not change frame to frame. You pre-fill the bitmap with the chosen dithering patterns at initialisation time and never touch it again during the animation.

### Text Overlay

Introspec used 4-phase colour in Eager as a background animation with scrolling text overlaid on top. The text overlay introduces a complication: the text must remain readable across all four phases.

The solution is to reserve certain cells for text and exclude them from the colour cycling. In text cells, the attribute is fixed (say, white ink on black paper) and the pixel data is the actual font glyphs. These cells do not participate in the 4-phase cycle, so the text remains solid and legible while the colour animation ripples behind it.

Alternatively, you can integrate the text into the phase animation by carefully choosing which pattern pixels to modify in the text area. The text glyphs override certain bits in patterns A and B, ensuring that the text character's shape is visible in every frame. The surrounding non-text pixels in the same cells still participate in the colour cycling. This produces text that appears to float on the animated background, with the animation bleeding right up to the edges of each letterform.

This second approach is harder to implement correctly -- you must ensure the text is legible against every colour combination that appears during the cycle -- but when it works, the visual effect is striking.

---

## The Shared Principle: Temporal Cheating

Step back from the implementation details and look at what these two techniques have in common.

The dotfield scroller uses 50 frames per second of *spatial* addressing to create the impression of smooth, fluid motion. Each frame, the dots are in slightly different positions. The motion is not calculated in real time -- it is pre-baked into address tables. The CPU's job is not to *think* about where dots go. Its job is to *place* them, as fast as possible, reading pre-computed coordinates from the stack.

The 4-phase colour animation uses 50 frames per second of *temporal* alternation to create the impression of colours that do not exist in any single frame. Each frame displays a different pair of colours with a different pixel pattern. No single frame contains the perceived result. The result exists only in the viewer's retina, as the persistence of vision averages four distinct images into one.

Both techniques exploit the same physical reality: the CRT display refreshes at 50Hz, and the human visual system cannot resolve individual frames at that rate. The Spectrum's *temporal* resolution -- 50 distinct images per second -- is far richer than its *spatial* resolution (256x192 pixels) or its *colour* resolution (2 colours per cell). Demoscene coders discovered, empirically and independently across many platforms, that temporal resolution is the cheapest axis to exploit.

This is not unique to the Spectrum. Amiga coders used copper-list tricks to display more colours than the hardware palette allowed, flickering between two screens. PC coders in the early 1990s used page-flipping and palette rotation to simulate smooth motion and colour depth. But the Spectrum, with its extreme constraints, makes the principle unusually visible. You can *see* the trade-off: 2 colours per cell, 50 times per second, producing the illusion of a richer display.

The dotfield scroller and the 4-phase colour animation sit at opposite ends of this spectrum of tricks. The scroller uses the stack -- the fastest data channel on the Z80 -- to address space. The colour animation uses frame alternation to address colour. Both reduce their inner loops to the absolute minimum: the scroller to 36 T-states per dot, the colour animation to a pre-built buffer swap. Both move the complexity out of the inner loop and into pre-computation. And both produce results that look, to the casual viewer, like the hardware should not be capable of them.

---

## Practical 1: A Bouncing Dot-Matrix Text Scroller

This project builds a simplified dotfield scroller. We will render a short text message as a bouncing dot-matrix field, with each character's pixels plotted individually using the POP-based addressing technique.

### Data Structures

**Font data.** We need an 8x8 bitmap font stored one byte per character row, 8 bytes per character. The Spectrum ROM contains a suitable font at address `$3D00` (characters 32-127), but for clarity we will use our own:

```z80
    ALIGN 256
font_data:
    ; Character 'A' (8 bytes, top to bottom)
    db %00111100
    db %01000010
    db %01000010
    db %01111110
    db %01000010
    db %01000010
    db %01000010
    db %00000000

    ; Character 'B', 'C', etc. follow...
    ; (Or INCBIN a complete font file)
```

**Sine table.** A 256-byte table for the bounce offset, page-aligned:

```z80
    ALIGN 256
bounce_table:
    LUA ALLPASS
    for i = 0, 255 do
        -- Amplitude of 16 pixels, offset to positive range
        sj.add_byte(math.floor(math.sin(i * math.pi / 128) * 16 + 16))
    end
    ENDLUA
```

**Address table.** This is the stack-based table of pre-calculated screen addresses. It sits in RAM and is rebuilt every frame:

```z80
addr_table:
    ds  4096 * 2          ; space for up to 4096 16-bit addresses
addr_table_end:
```

### Building the Address Table

Before each frame, we build the address table. For each dot in the visible portion of the text, we calculate its screen address based on the scroll position and bounce offset:

```z80
; Build the address table for the current frame
; Input:  scroll_pos = horizontal scroll offset (0-255)
;         bounce_phase = phase offset for sine wave
; Output: addr_table filled, addr_table_ptr set to start

build_addr_table:
    ld   ix,addr_table
    ld   hl,message          ; pointer to message text

    ld   b,0                 ; column counter
.char_loop:
    ld   a,(hl)              ; read character code
    or   a
    ret  z                   ; null terminator = done

    ; Calculate font data address for this character
    ; font_addr = font_data + (char - 32) * 8
    sub  32
    ld   e,a
    ld   d,0
    sla  e : rl d            ; DE = (char-32) * 2
    sla  e : rl d            ; DE = (char-32) * 4
    sla  e : rl d            ; DE = (char-32) * 8
    push hl                  ; save message pointer
    ld   hl,font_data
    add  hl,de               ; HL = font data for this character

    ; For each row (0-7) of this character:
    ld   c,8                 ; 8 rows per character
    push bc                  ; save column counter
    ld   b,0                 ; row counter within character
.row_loop:
    ; For each column bit (0-7):
    ld   a,(hl)              ; read font row byte
    push hl                  ; save font pointer

    ld   d,8                 ; 8 bits per byte
.bit_loop:
    ; Calculate screen position:
    ;   x = char_column * 8 + bit - scroll_pos
    ;   y = row + bounce_table[(char_column * 8 + bit + bounce_phase) & 255]

    ; Calculate the bounce offset
    push af                  ; save font byte
    ; ... (calculate y from bounce_table) ...
    ; ... (calculate screen address from x, y) ...

    ; Store screen address in the table
    ld   (ix+0),e            ; low byte of screen address
    ld   (ix+1),d            ; high byte of screen address
    inc  ix
    inc  ix

    pop  af                  ; restore font byte
    rla                      ; next bit
    dec  d
    jr   nz,.bit_loop

    pop  hl                  ; restore font pointer
    inc  hl                  ; next font row
    inc  b                   ; next row
    dec  c
    jr   nz,.row_loop

    pop  bc                  ; restore column counter
    inc  b                   ; next character column
    pop  hl                  ; restore message pointer
    inc  hl                  ; next character
    jr   .char_loop
```

This is the slow part -- table construction. It runs once per frame, outside the inner loop. The goal is not to make this fast (though it should be reasonable) but to make the rendering loop that follows as fast as possible.

### The Rendering Loop

Once the table is built, rendering is the fast part:

```z80
; Render the dotfield from the address table
; The font data and address table are interleaved:
; for each font byte, 8 consecutive address entries follow.

render_dotfield:
    di
    ld   (restore_sp+1),sp   ; save SP (self-modifying)
    ld   sp,addr_table        ; SP now points to our address table

    ld   hl,message
    ld   bc,font_data         ; BC will track font data position

    ; For each font byte:
.byte_loop:
    ld   a,(bc)               ;  7 T  read font byte
    inc  bc                   ;  6 T  advance font pointer

    ; Pixel 7 (MSB)
    pop  hl                   ; 10 T
    rla                       ;  4 T
    jr   nc,.s7               ; 12 T (taken) / 7 T (not taken)
    set  7,(hl)               ; 15 T
.s7:
    ; Pixel 6
    pop  hl                   ; 10 T
    rla                       ;  4 T
    jr   nc,.s6               ; 12/7 T
    set  6,(hl)               ; 15 T
.s6:
    ; Pixel 5
    pop  hl                   ; 10 T
    rla                       ;  4 T
    jr   nc,.s5               ; 12/7 T
    set  5,(hl)               ; 15 T
.s5:
    ; Pixel 4
    pop  hl                   ; 10 T
    rla                       ;  4 T
    jr   nc,.s4               ; 12/7 T
    set  4,(hl)               ; 15 T
.s4:
    ; Pixel 3
    pop  hl                   ; 10 T
    rla                       ;  4 T
    jr   nc,.s3               ; 12/7 T
    set  3,(hl)               ; 15 T
.s3:
    ; Pixel 2
    pop  hl                   ; 10 T
    rla                       ;  4 T
    jr   nc,.s2               ; 12/7 T
    set  2,(hl)               ; 15 T
.s2:
    ; Pixel 1
    pop  hl                   ; 10 T
    rla                       ;  4 T
    jr   nc,.s1               ; 12/7 T
    set  1,(hl)               ; 15 T
.s1:
    ; Pixel 0 (LSB)
    pop  hl                   ; 10 T
    rla                       ;  4 T
    jr   nc,.s0               ; 12/7 T
    set  0,(hl)               ; 15 T
.s0:
    ; Check if more font bytes to process
    ; (counter management here)
    djnz .byte_loop           ; 13/8 T

restore_sp:
    ld   sp,$0000             ; self-modified: restores real SP
    ei
    ret
```

The core of each pixel -- `pop hl : rla : jr nc,skip : set ?,(hl)` -- is exactly the sequence Introspec documented from Illusion. The SET bit position changes for each of the 8 pixels within a byte, which is why the loop is unrolled rather than repeated. You cannot parameterise the bit position in SET without IX/IY indexing (which would be far too slow) or self-modifying code (which would add overhead). Unrolling 8 times is the clean solution.

### Main Loop

```z80
main:
    ; Clear screen
    call clear_screen

    ; Main animation loop
.frame:
    halt                      ; sync to 50Hz

    call clear_screen         ; erase previous frame's dots
    call build_addr_table     ; pre-calculate all dot positions
    call render_dotfield      ; plot the dots

    ; Advance animation
    ld   hl,scroll_pos
    inc  (hl)                 ; advance scroll
    ld   hl,bounce_phase
    inc  (hl)
    inc  (hl)                 ; advance bounce at 2x scroll speed

    jr   .frame
```

The `clear_screen` call is necessary because SET only turns pixels on -- it does not clear previously set pixels. Each frame must start with a clean screen. A PUSH-based clear (Chapter 3) is fast enough that the overhead is acceptable.

### Extensions

The simplified version above captures the core technique. A production implementation would add:

- **Partial screen clearing.** Instead of clearing the entire screen, track the bounding box of the dotfield and clear only that region. This can halve the clear cost.
- **Double buffering.** Render dots into an off-screen buffer, then copy to the display. Eliminates the visible clear-then-draw flicker. On a 128K machine, use the shadow screen (bank 7).
- **Multiple bounce harmonics.** Add a second or third sine term to the bounce offset for more complex wave shapes.
- **Variable dot density.** Skip every other column or row to reduce dot count, creating a more sparse, ethereal appearance.

---

## Practical 2: A 4-Phase Colour Cycling Animation

This project builds a simple 4-phase colour animation that produces smooth colour gradients impossible in a single Spectrum frame. The goal is a full-screen wash of colour that appears to have more than two colours per cell.

### Setup: The Pixel Patterns

We need two pixel patterns in bitmap memory. Pattern A and Pattern B should be complementary dithering patterns:

```z80
; Fill bitmap with two interleaved dither patterns
; Even character rows get Pattern A (checkerboard)
; Odd character rows get Pattern B (inverse checkerboard)

setup_patterns:
    ; Pattern A: $55 = 01010101 (even lines)
    ; Pattern B: $AA = 10101010 (odd lines)
    ;
    ; Within each 8-pixel-tall cell, we alternate:
    ;   Lines 0,2,4,6 = $55 (pattern A)
    ;   Lines 1,3,5,7 = $AA (pattern B)

    ld   hl,$4000
    ld   b,192               ; 192 pixel lines
.fill:
    ld   a,b
    and  1                   ; check odd/even scan line
    jr   z,.even_line
    ld   a,$AA               ; odd lines: pattern B
    jr   .store
.even_line:
    ld   a,$55               ; even lines: pattern A
.store:
    ld   d,a
    ld   c,32                ; 32 bytes per line
.line:
    ld   (hl),d
    inc  hl
    dec  c
    jr   nz,.line
    djnz .fill
    ret
```

In practice, you would use a more sophisticated dithering pattern -- an ordered 4x4 Bayer matrix, for example -- to minimise visible flicker. The checkerboard above is the simplest case.

### The Four Attribute Buffers

Pre-calculate four attribute buffers, each 768 bytes. The colours should be chosen to produce a smooth gradient when averaged:

```z80
; Generate four attribute buffers for a diagonal colour wash
; Buffer 0: ink=blue(1),   paper=red(2)     (Normal A)
; Buffer 1: ink=green(4),  paper=cyan(5)    (Normal B)
; Buffer 2: ink=red(2),    paper=blue(1)    (Inverted A)
; Buffer 3: ink=cyan(5),   paper=green(4)   (Inverted B)

; For a gradient effect, vary the colours across the screen.

generate_attr_buffers:
    ; Buffer 0 (Normal A)
    ld   hl,attr_buf_0
    ld   b,24                ; 24 rows
.row0:
    ld   c,32                ; 32 columns
.col0:
    ; Choose ink/paper based on position for gradient
    ld   a,b
    add  a,c                 ; diagonal index
    and  %00000111           ; 8 colour steps
    ld   d,a                 ; ink colour
    ld   a,7
    sub  d                   ; paper = 7 - ink (complementary)
    sla  d : sla  d : sla d  ; ink into bits 0-2
    or   d                   ; combine: paper in 3-5, ink in 0-2
    ld   (hl),a
    inc  hl
    dec  c
    jr   nz,.col0
    djnz .row0

    ; Buffer 2 (Inverted A) = Buffer 0 with ink/paper swapped
    ld   hl,attr_buf_0
    ld   de,attr_buf_2
    ld   b,0                 ; 256 iterations (we will do 3 passes)
    ld   c,3                 ; 3 x 256 = 768
.swap_loop:
    ld   a,(hl)
    ; Swap ink (bits 0-2) and paper (bits 3-5)
    ld   d,a
    rrca : rrca : rrca       ; rotate ink to paper position
    and  %00111000           ; mask paper bits
    ld   e,a
    ld   a,d
    rlca : rlca : rlca       ; rotate paper to ink position
    and  %00000111           ; mask ink bits
    or   e                   ; combine
    ; Preserve bright and flash bits (6-7) from original
    ld   e,a
    ld   a,d
    and  %11000000
    or   e
    ld   (de),a
    inc  hl
    inc  de
    djnz .swap_loop
    dec  c
    jr   nz,.swap_loop

    ; Repeat for Buffers 1 and 3 with a different colour scheme
    ; ... (similar code with different colour mapping) ...
    ret

attr_buf_0:  ds 768
attr_buf_1:  ds 768
attr_buf_2:  ds 768
attr_buf_3:  ds 768
```

### The Main Loop

The animation loop is almost absurdly simple. Each frame, copy the next buffer into attribute RAM and advance the phase counter:

```z80
phase:  db 0

main_loop:
    halt                     ; sync to 50Hz

    ; Select buffer based on phase (0-3)
    ld   a,(phase)
    and  3                   ; mask to 0-3
    ld   l,a
    ld   h,0
    add  hl,hl              ; x2 for word index
    ld   de,buffer_table
    add  hl,de
    ld   e,(hl)
    inc  hl
    ld   d,(hl)              ; DE = source buffer address

    ; Copy 768 bytes to attribute RAM
    ld   hl,$5800            ; destination: attribute memory
    ex   de,hl               ; HL = source, DE = destination
    ld   bc,768
    ldir                     ; 768 x 21 = ~16,000 T-states

    ; Advance phase
    ld   hl,phase
    inc  (hl)

    jr   main_loop

buffer_table:
    dw   attr_buf_0          ; phase 0: Normal A
    dw   attr_buf_1          ; phase 1: Normal B
    dw   attr_buf_2          ; phase 2: Inverted A
    dw   attr_buf_3          ; phase 3: Inverted B
```

That is the entire runtime animation engine: one LDIR per frame. About 16,000 T-states. Less than a quarter of the frame budget.

### Adding Motion

A static colour wash is not very interesting. To animate the gradient, offset the colour calculation by a frame counter when generating the buffers. But regenerating all four buffers every frame would be expensive.

The efficient approach: use a circular buffer strategy. Each frame, you need only one *new* buffer -- the other three were computed in previous frames. Generate buffer N, display buffer N-3, and you maintain a 4-frame pipeline with only one buffer generation per frame. The colour offset advances by 1 each frame, so each newly generated buffer shows the next step of the animation.

Alternatively, if you pre-compute a set of buffers covering the full animation cycle and store them across 128K memory banks, the runtime cost drops to zero -- just a bank switch and an LDIR.

### What the Viewer Sees

With a well-chosen colour scheme and dithering pattern, the 4-phase animation produces a display that appears to have smooth colour gradients -- something flatly impossible on the Spectrum in a single frame. The "extra" colours exist only in the viewer's temporal averaging, but they are convincingly real. On a CRT, the phosphor glow further smooths the transitions. On modern LCD displays or in emulators running at exactly 50Hz, the effect can show visible flicker; the technique was designed for CRT and works best there.

---

## Putting It Together

This chapter has covered two specific techniques, but the deeper lesson is general. The ZX Spectrum's frame rate -- 50 interrupts per second, each one an opportunity to change everything on screen -- is an exploitable resource. Demoscene coders learned to think of the frame rate not as a *constraint* (how fast must my code run?) but as a *capability* (how many distinct images can I show per second?).

The dotfield scroller uses this capability for motion. Each frame is a snapshot of the dot positions at one instant. The viewer's brain interpolates between snapshots to perceive smooth movement. The faster the frame rate, the smoother the interpolation -- which is why the 36 T-states per pixel figure matters so much. Faster pixels mean more dots per frame, which means denser text, which means a richer visual.

The 4-phase colour animation uses this capability for colour. Each frame is one of four colour states. The viewer's retina averages the states to perceive a blended result. The technique would not work at 12.5Hz (one complete cycle every 320ms) -- the flicker would be visible and distracting. But at 50Hz, each phase displays for only 20ms, and the cycle completes in 80ms. The brain sees a steady colour.

Both techniques demonstrate the same core insight: on constrained hardware, time is your most abundant resource. You have limited pixels, limited colours, limited memory, limited CPU cycles per frame. But you have 50 frames per second. That is 50 chances to change the picture. Every frame you waste showing the same static image is a frame you could have used to show a slightly different one, building up an illusion that no single frame could achieve.

This is what makes the demoscene a temporal art form. A screenshot of a dotfield scroller shows a scatter of pixels. A screenshot of a 4-phase colour animation shows two colours per cell, exactly as the hardware specifies. You have to see them *move* to see them work. The beauty is in the sequence, not the frame.

---

## Summary

- The **dotfield scroller** renders text as individual dots at arbitrary screen positions. The inner loop -- `pop hl : rla : jr nc,skip : set ?,(hl)` -- costs 36 T-states per opaque pixel and 26 T-states per transparent pixel.
- **Stack-based addressing** encodes the entire bounce trajectory as a pre-built table of screen addresses. POP retrieves addresses at 10 T-states each -- the fastest possible random-access read on the Z80.
- **4-phase colour animation** cycles through 4 attribute frames (2 normal + 2 inverted) at 50Hz. Persistence of vision averages the colours, creating the illusion of more than 2 colours per cell.
- The **inversion step** (swapping ink and paper) ensures all four colours contribute to every pixel position, regardless of the pixel pattern.
- Both techniques exploit **temporal resolution** -- the Spectrum's 50fps refresh rate -- to create effects impossible in any single frame.
- The **scroller** uses the stack for spatial flexibility; the **colour animation** uses frame alternation for colour flexibility. Together they illustrate the two main axes of demoscene "cheating": clever addressing (space) and persistence of vision (time).

---

## Try It Yourself

1. Build the dotfield scroller from Practical 1. Start with a single character, no bounce -- just a static dot-matrix "A" plotted via the POP-based inner loop. Verify that the timing harness (Chapter 1) shows the expected cost. Then add the bounce table and watch the character undulate.

2. Experiment with bounce parameters. Change the amplitude (the multiplier in the sine table generator), the spatial frequency (the multiplier on the column index), and the phase speed. Small changes produce dramatically different visual textures -- from gentle ripples to violent whiplash.

3. Build the 4-phase colour animation from Practical 2. Start with a uniform colour across the screen (all cells the same ink/paper pair in each phase). Verify that you see a solid, non-flickering colour that is neither the ink nor the paper of any single frame. Then add the diagonal gradient and watch smooth colour bands emerge.

4. Try different dithering patterns for the pixel data. Replace the checkerboard with a 2x2 block pattern, or a Bayer matrix, or random noise. Each pattern produces a different visual texture in the averaged result. Which patterns minimise visible flicker? Which produce the smoothest perceived gradients?

5. Combine the two techniques. Use 4-phase colour to render a colourful background, then overlay a monochrome dotfield scroller on top. You will need to be careful about which attribute cells the scroller touches -- it must not interfere with the colour cycling in non-text areas.

---

> **Sources:** Introspec, "Technical Analysis of Illusion by X-Trade" (Hype, 2017); Introspec, "Making of Eager" (Hype, 2015); Dark, "Programming Algorithms" (Spectrum Expert #01, 1997). The inner loop disassembly and cycle counts follow Introspec's 2017 analysis. The 4-phase colour technique is described in the Eager making-of article and the party version's file_id.diz.
