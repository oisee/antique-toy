# Chapter 2: The Screen as a Puzzle

> "Why do the rows go in that order?"
> -- Every ZX Spectrum programmer, at some point

Open any emulator, type `PEEK 16384` and you are reading the first byte of the Spectrum's screen. But which byte is it? Not the top-left of the screen in any simple sense. The pixel at coordinate (0,0) is there, yes -- but the pixel at (0,1), the very next row down, lives 256 bytes away. The pixel at (0,8), the top row of the second character cell, lives only 32 bytes from the start. And the pixel at (0,64) -- the first row of the screen's middle third -- lives exactly 2,048 bytes from the start, at `$4800`.

This is the Spectrum's most famous puzzle. The screen memory layout is not sequential, not intuitive, and not an accident. It is a consequence of hardware design choices made in 1982, and it shapes every piece of code that touches the display. Understanding this layout -- and learning the tricks that make it fast to navigate -- is fundamental to everything that follows in this book.

---

## The Memory Map: 6,912 Bytes of Screen

The Spectrum's display occupies a fixed region of memory:

```text
$4000 - $57FF    Pixel data      6,144 bytes   (256 x 192 pixels, 1 bit per pixel)
$5800 - $5AFF    Attributes        768 bytes   (32 x 24 colour cells)
```

The pixel area holds the bitmap: 256 pixels across, packed 8 per byte, giving 32 bytes per row. With 192 rows, that is 32 x 192 = 6,144 bytes. Each byte represents 8 horizontal pixels, with bit 7 as the leftmost pixel and bit 0 as the rightmost.

The attribute area holds the colour information: one byte per 8x8 character cell. There are 32 columns and 24 rows, giving 32 x 24 = 768 bytes.

Together: 6,144 + 768 = 6,912 bytes. That is the entire display.

<!-- figure: ch02_screen_layout -->
![ZX Spectrum screen memory layout with thirds, character cells, and attribute area](illustrations/output/ch02_screen_layout.png)

The pixel data and attribute data serve different purposes but are tightly coupled. Each pixel byte controls 8 dots on screen; the attribute byte for the corresponding 8x8 cell controls what colour those dots appear in. Change the pixel and you change the shape. Change the attribute and you change the colour. But you can only change colour for an entire 8x8 block -- not per pixel. This is the "attribute clash" that defines the Spectrum's visual character, and we will return to it shortly.

First, the puzzle: why are the pixel rows scrambled?

---

## The Interleave: Where the Rows Live

If the Spectrum stored its pixel rows sequentially, row 0 would be at `$4000`, row 1 at `$4020`, row 2 at `$4040`, and so on. Each row is 32 bytes, so row N would simply be at `$4000 + N * 32`. Simple, fast, sensible.

That is not what happens.

The screen is divided into three **thirds**, each 64 pixel rows tall. Within each third, the rows are interleaved by character cell row. Here is where the first 16 rows actually live:

```text
Row  0:  $4000     Third 0, char row 0, scan line 0
Row  1:  $4100     Third 0, char row 0, scan line 1
Row  2:  $4200     Third 0, char row 0, scan line 2
Row  3:  $4300     Third 0, char row 0, scan line 3
Row  4:  $4400     Third 0, char row 0, scan line 4
Row  5:  $4500     Third 0, char row 0, scan line 5
Row  6:  $4600     Third 0, char row 0, scan line 6
Row  7:  $4700     Third 0, char row 0, scan line 7
Row  8:  $4020     Third 0, char row 1, scan line 0
Row  9:  $4120     Third 0, char row 1, scan line 1
Row 10:  $4220     Third 0, char row 1, scan line 2
Row 11:  $4320     Third 0, char row 1, scan line 3
Row 12:  $4420     Third 0, char row 1, scan line 4
Row 13:  $4520     Third 0, char row 1, scan line 5
Row 14:  $4620     Third 0, char row 1, scan line 6
Row 15:  $4720     Third 0, char row 1, scan line 7
```

Look at the pattern. The first 8 rows are the 8 scanlines of character row 0 -- but they are 256 bytes apart, not 32. Within those 8 rows, the high byte of the address increments by 1 each time: `$40`, `$41`, `$42`, ... `$47`. Then row 8 jumps to `$4020` -- back to a high byte of `$40`, but with the low byte advanced by 32.

Here is the complete picture for the top third of the screen:

```text
Char row 0:   scan lines at $4000, $4100, $4200, $4300, $4400, $4500, $4600, $4700
Char row 1:   scan lines at $4020, $4120, $4220, $4320, $4420, $4520, $4620, $4720
Char row 2:   scan lines at $4040, $4140, $4240, $4340, $4440, $4540, $4640, $4740
Char row 3:   scan lines at $4060, $4160, $4260, $4360, $4460, $4560, $4660, $4760
Char row 4:   scan lines at $4080, $4180, $4280, $4380, $4480, $4580, $4680, $4780
Char row 5:   scan lines at $40A0, $41A0, $42A0, $43A0, $44A0, $45A0, $46A0, $47A0
Char row 6:   scan lines at $40C0, $41C0, $42C0, $43C0, $44C0, $45C0, $46C0, $47C0
Char row 7:   scan lines at $40E0, $41E0, $42E0, $43E0, $44E0, $45E0, $46E0, $47E0
```

The middle third starts at `$4800` and follows the same pattern. The bottom third starts at `$5000`.

### Why?

The reason is the ULA -- the Uncommitted Logic Array that generates the video signal. The ULA reads one byte of pixel data and one byte of attribute data for every 8-pixel character cell it draws. It needs both bytes at specific moments as it rasters across the screen.

The interleaved layout meant that the ULA's address counter logic could be built with fewer gates. As the ULA scans left to right across a character row, it increments the low 5 bits of the address (the column). When it reaches the right edge, it increments the high byte to move to the next scanline within the same character row. When it finishes all 8 scanlines, it wraps the high byte and advances the low-byte row bits.

This is elegant from a hardware perspective. The ULA's address generation is a simple combination of counters -- no multiplication, no complex address arithmetic. The PCB routing was simpler, the gate count was lower, and the chip was cheaper to manufacture.

The programmer pays the price.

---

## The Bit Layout: Decoding (x, y) into an Address

![ZX Spectrum screen memory layout — interleaved thirds with colour-coded address bit mapping](../../build/screenshots/proto_ch02_screen_layout.png)

To understand the interleave precisely, look at how the Y coordinate maps into the 16-bit screen address. Consider a pixel at column `x` (0--255) and row `y` (0--191). The byte containing that pixel is at:

```text
High byte:  0 1 0 T T S S S
Low byte:   L L L C C C C C
```

Where:
- `TT` = which third of the screen (0, 1, or 2). Bits 7--6 of y.
- `SSS` = scanline within the character cell (0--7). Bits 2--0 of y.
- `LLL` = character row within the third (0--7). Bits 5--3 of y.
- `CCCCC` = column in bytes (0--31). This is x / 8, or equivalently bits 7--3 of x.

The crucial thing: the bits of y are not in order. Bits 7-6 go to one place, bits 5-3 go to another, and bits 2-0 go to yet another. The y coordinate is sliced up and distributed across the address.

Let us visualise this with a concrete example. Pixel (80, 100):

```text
x = 80:     column byte = 80 / 8 = 10      CCCCC = 01010
y = 100:    binary = 01100100
            TT  = 01       (third 1, the middle third)
            LLL = 100      (char row 4 within the third)
            SSS = 100      (scan line 4 within the char cell)

High byte:  0  1  0  0  1  1  0  0  = $4C
Low byte:   1  0  0  0  1  0  1  0  = $8A

Address: $4C8A
```

The bit within that byte is determined by the low 3 bits of x. Bit 7 is the leftmost pixel, so pixel position (x AND 7) maps to bit 7 - (x AND 7).

### The address calculation in Z80

Converting (x, y) to a screen address is something you need to do fast and often. Here is a standard routine:

```z80 id:ch02_the_address_calculation_in
; Input:  B = y (0-191), C = x (0-255)
; Output: HL = screen address, A = bit mask
;
pixel_addr:
    ld   a, b          ; 4T   A = y
    and  $07           ; 7T   A = SSS (scan line within char)
    or   $40           ; 7T   A = 010 00 SSS (add screen base)
    ld   h, a          ; 4T   H = high byte (partial)

    ld   a, b          ; 4T   A = y again
    rra                ; 4T   \
    rra                ; 4T    | shift bits 5-3 of y
    rra                ; 4T   /  down to bits 2-0
    and  $E0           ; 7T   mask to get LLL 00000
    ld   l, a          ; 4T   L = LLL 00000 (partial)

    ld   a, b          ; 4T   A = y again
    and  $C0           ; 7T   A = TT 000000
    rra                ; 4T   \
    rra                ; 4T    | shift bits 7-6 of y
    rra                ; 4T   /  to bits 4-3
    or   h             ; 4T   combine with SSS
    ld   h, a          ; 4T   H = 010 TT SSS (complete)

    ld   a, c          ; 4T   A = x
    rra                ; 4T   \
    rra                ; 4T    | x / 8
    rra                ; 4T   /
    and  $1F           ; 7T   mask to CCCCC
    or   l             ; 4T   combine with LLL 00000
    ld   l, a          ; 4T   L = LLL CCCCC (complete)
                       ; --- Total: ~91 T-states
```

91 T-states is not cheap. In a tight inner loop processing thousands of pixels, you would not call this routine per pixel. Instead, you calculate the starting address once and then navigate the screen using fast pointer manipulation -- which brings us to the most important routine in Spectrum graphics programming.

![Pixel plotting demo — individual pixels placed on screen using the address calculation routine](../../build/screenshots/ch02_pixel_demo.png)

---

## DOWN_HL: Moving One Pixel Row Down

You have a pointer in HL to some byte on the screen. You want to move it one pixel row down -- to the byte at the same column, one scanline lower. How hard can this be?

On a linear framebuffer, you add 32 (the number of bytes per row). One `ADD HL, DE` with DE = 32: 11 T-states, done.

On the Spectrum, it is a puzzle within the puzzle. Moving one pixel row down means:

1. **Within a character cell** (scanlines 0--6 to 1--7): increment H. The scanline bits are in the low 3 bits of H, so `INC H` moves you one scanline down.

2. **Crossing a character cell boundary** (scanline 7 to scanline 0 of the next row): reset the scanline bits of H back to 0, and add 32 to L to move to the next character row.

3. **Crossing a third boundary** (bottom of char row 7 in one third to top of char row 0 in the next): reset L back, and add 8 to H to move to the next third. Equivalently, add `$0800` to the address.

The classic routine handles all three cases:

```z80 id:ch02_downhl_moving_one_pixel_row
; DOWN_HL: move HL one pixel row down on the Spectrum screen
; Input:  HL = current screen address
; Output: HL = screen address one row below
;
down_hl:
    inc  h             ; 4T   try moving one scan line down
    ld   a, h          ; 4T
    and  7             ; 7T   did we cross a character boundary?
    ret  nz            ; 11/5T  no: done

    ; Crossed a character cell boundary.
    ; Reset scan line to 0, advance character row.
    ld   a, l          ; 4T
    add  a, 32         ; 7T   next character row (L += 32)
    ld   l, a          ; 4T
    ret  c             ; 11/5T  if carry, we crossed into next third

    ; No carry from L, but we need to undo the H increment
    ; that moved us into the wrong third.
    ld   a, h          ; 4T
    sub  8             ; 7T   back up one third in H
    ld   h, a          ; 4T
    ret                ; 10T
```

This routine takes different amounts of time depending on which case it hits:

| Case | Frequency | T-states |
|------|-----------|----------|
| Within a character cell | 7 out of 8 rows | 4 + 4 + 7 + 11 = **26** |
| Character boundary, same third | 7 out of 64 rows | 4 + 4 + 7 + 5 + 4 + 7 + 4 + 5 + 4 + 7 + 4 + 10 = **65** |
| Third boundary | 2 out of 192 rows | 4 + 4 + 7 + 5 + 4 + 7 + 4 + 11 = **46** |

The common case -- staying within a character cell -- is fast: 26 T-states (a conditional RET that fires costs 11T, not 5T). The uncommon case (crossing a character row boundary within the same third) is 65 T-states. Averaged over all 192 rows, the cost works out to about **30.5 T-states per call**.

That average hides a problem. If you are iterating down the full screen and calling DOWN_HL on every row, those occasional 65-T-state calls spike your per-line timing unpredictably. For a demo effect that needs consistent timing per scanline, this jitter is unacceptable.

### Introspec's Optimisation

In December 2020, Introspec (spke) published a detailed analysis on Hype titled "Once more about DOWN_HL" (Eshchyo raz pro DOWN_HL). The article examined the problem of iterating down the full screen efficiently -- not just the cost of one call, but the total cost of moving HL through all 192 rows.

The naive approach -- calling the classic DOWN_HL routine 191 times -- costs **5,825 T-states** for a full screen traversal. Introspec's goal was to find the fastest way to iterate through all 192 rows, visiting every screen address in top-to-bottom order.

His key insight was to use **split counters**. Instead of testing the address bits after every increment to detect boundary crossings, he structured the loop to match the screen's three-level hierarchy directly:

```text id:ch02_introspec_s_optimisation
For each third (3 iterations):
    For each character row within the third (8 iterations):
        For each scan line within the character cell (8 iterations):
            process this row
            INC H                  ; next scan line
        undo 8 INC H's, ADD 32 to L   ; next character row
    undo 8 ADD 32's, advance to next third
```

The innermost operation is just `INC H` -- 4 T-states. No testing, no branching. The character-row and third transitions happen at fixed, predictable points in the loop, so there is no conditional logic in the inner loop at all.

The result: **2,343 T-states** for a full screen traversal. That is a 60% improvement over the classic approach, and the per-line cost is absolutely predictable -- no jitter.

There was also an elegant variation attributed to RST7, using a dual-counter approach where the outer loop maintains a pair of counters that naturally track the character-row and third boundaries. The inner loop body reduces to a single `INC H`, and the boundary handling is folded into the counter manipulation at the outer loop level.

The practical lesson: when you need to iterate through the Spectrum's screen in order, do not call a general-purpose DOWN_HL routine 191 times. Restructure your loop to match the screen's natural hierarchy, and the branching disappears.

Here is a simplified version of the split-counter approach:

```z80 id:ch02_introspec_s_optimisation_2
; Iterate all 192 screen rows using split counters
; HL = $4000 at entry (top-left of screen)
;
iterate_screen:
    ld   hl, $4000          ; 10T  start of screen
    ld   c, 3               ; 7T   3 thirds

.third_loop:
    ld   b, 8               ; 7T   8 character rows per third

.row_loop:
    push hl                 ; 11T  save start of this char row

    ; --- Process 8 scan lines within this character cell ---
    REPT 7
        ; ... your per-row code here, using HL ...
        inc  h              ; 4T   next scan line
    ENDR
    ; ... process the 8th (last) scan line ...

    pop  hl                 ; 10T  restore char row start
    ld   a, l               ; 4T
    add  a, 32              ; 7T   next character row
    ld   l, a               ; 4T

    djnz .row_loop          ; 13T/8T

    ; Advance to next third
    ld   a, h               ; 4T
    add  a, 8               ; 7T   next third ($0800 higher)
    ld   h, a               ; 4T

    dec  c                  ; 4T
    jr   nz, .third_loop    ; 12T/7T
```

The `REPT 7` directive (supported by sjasmplus) repeats the block 7 times at assembly time -- a partial unroll. Inside that block, moving down one scanline is a single `INC H`. No testing, no branching. The character-row advance and third-advance happen at the fixed outer loop boundaries.

---

## Attribute Memory: 768 Bytes That Changed Everything

Below the pixel data, at `$5800`--`$5AFF`, sits the attribute memory. It is 768 bytes -- one for each 8x8 character cell on the screen, arranged sequentially from left to right, top to bottom. Unlike the pixel area, the attribute layout is entirely linear: cell (col, row) is at `$5800 + row * 32 + col`.

Each attribute byte has this layout:

```text
  Bit:   7     6     5  4  3     2  1  0
       +-----+-----+--------+--------+
       |  F  |  B  | PAPER  |  INK   |
       +-----+-----+--------+--------+

  F       = Flash (0 = off, 1 = flashing at ~1.6 Hz)
  B       = Bright (0 = normal, 1 = bright)
  PAPER   = Background colour (0-7)
  INK     = Foreground colour (0-7)
```

The 3-bit colour codes map to:

```text
  0 = Black       4 = Green
  1 = Blue        5 = Cyan
  2 = Red         6 = Yellow
  3 = Magenta     7 = White
```

With the BRIGHT bit, each colour has a normal and bright variant. Black stays black whether bright or not, so the total palette is 15 distinct colours:

```text
Normal:  Black  Blue  Red  Magenta  Green  Cyan  Yellow  White
Bright:  Black  Blue  Red  Magenta  Green  Cyan  Yellow  White
                (brighter versions of each)
```

<!-- figure: ch02_attr_byte -->
![Attribute byte bit layout showing flash, bright, paper, and ink fields](illustrations/output/ch02_attr_byte.png)

An attribute byte of `$47` = `01000111`: flash off (bit 7 = 0), bright **on** (bit 6 = 1), paper = 000 (black), ink = 111 (white). Bright white text on a black background. The non-bright version is `$07` = `00000111` -- the Spectrum's default after `BORDER 0: PAPER 0: INK 7`.

This kind of bit-level detail matters when you are constructing attribute values at speed. A common pattern:

```z80 id:ch02_attribute_memory_768_bytes_4
; Build an attribute byte: bright white ink on blue paper
; Bright = 1, Paper = 001 (blue), Ink = 111 (white)
; = 01 001 111 = $4F
    ld   a, $4F
```

### The Attribute Clash

Here is the defining constraint of the ZX Spectrum: within each 8x8 pixel cell, you can only have **two colours** -- ink and paper. Every set pixel (1) displays in the ink colour. Every clear pixel (0) displays in the paper colour. You cannot have three colours, or gradients, or per-pixel colouring, within a single cell.

This means that if a red sprite overlaps with a green background, the 8x8 cell containing the overlap must choose: all set pixels in this cell are either red or green. You cannot have some red and some green set pixels in the same cell. The visual result is a jarring block of colour that "clashes" with its surroundings -- the infamous attribute clash.

```text
Without clash (hypothetical per-pixel colour):

  +---------+---------+
  |  Red    | Red on  |
  |  sprite | green   |
  |  pixels | back-   |
  |         | ground  |
  +---------+---------+

With attribute clash (Spectrum reality):

  +---------+---------+
  |  Red    | Either  |
  |  sprite | ALL red |
  |  pixels | or ALL  |
  |         | green   |
  +---------+---------+

  The overlapping cell cannot have both colours.
```

Many early Spectrum games simply avoided the problem: monochrome graphics, or characters carefully designed to align with the 8x8 grid. Games like Knight Lore and Head Over Heels used a single ink/paper pair for the entire play area, eliminating clash entirely at the cost of colour.

But the demoscene saw this differently. Attribute clash is not just a limitation -- it is a **creative constraint**. The 8x8 grid forces a particular aesthetic: bold blocks of colour, sharp geometric patterns, deliberate use of contrast. Demo effects that work entirely in attribute space -- tunnels, plasmas, scrollers -- can update 768 bytes per frame instead of 6,144, freeing enormous amounts of cycle budget for computation. When your entire display is attribute-driven, clash becomes irrelevant because you are not mixing sprites with backgrounds -- the attributes *are* the graphics.

Introspec's demo Eager (2015) built its visual language entirely around this insight. The tunnel effect, the chaos zoomer, and the colour cycling animation all operate on attributes, not pixels. The result is an effect that runs at full frame rate with room to spare for digital drums and a sophisticated scripting engine. Clash is not a problem because the constraint was embraced from the start.

---

## The Border: More Than Decoration

The 256x192 pixel display area sits in the centre of the screen, surrounded by a wide border. The border colour is set by writing to port `$FE`:

```z80 id:ch02_the_border_more_than
    ld   a, 1          ; 7T   blue = colour 1
    out  ($FE), a       ; 11T  set border colour
```

Only bits 0--2 of the byte written to `$FE` affect the border colour. There are 8 colours (0--7), with no bright variants -- the border palette is the non-bright set. Bits 3 and 4 of port `$FE` control the MIC and EAR outputs (tape interface and beeper sound), so you should mask or set those bits appropriately if you are not intending to make noise.

The border colour change takes effect immediately -- on the very next scanline being drawn. This is what makes the border so useful as a debugging tool. As we saw in Chapter 1, changing the border colour before and after a section of code creates a visible stripe whose height reveals the code's T-state cost. The border is your oscilloscope.

### Border Effects

Because border colour changes are visible on the next scanline, precisely timed `OUT` instructions can create multicolour stripes, raster bars, and even crude graphics in the border area.

The basic principle: the ULA draws one scanline every 224 T-states (on Pentagon). If you execute an `OUT ($FE), A` instruction at the right moment, you change the border colour at a specific horizontal position on the current scanline. By executing a rapid sequence of `OUT` instructions with different colour values, you can paint horizontal stripes of colour in the border.

```z80 id:ch02_border_effects
; Simple border stripes
; Assumes we are synced to the start of a border scanline

    ld   a, 2          ; 7T   red
    out  ($FE), a       ; 11T
    ; ... delay to fill this scanline ...
    ld   a, 5          ; 7T   cyan
    out  ($FE), a       ; 11T
    ; ... delay to fill next scanline ...
    ld   a, 6          ; 7T   yellow
    out  ($FE), a       ; 11T
```

More advanced border effects can create gradient bars, scrolling text, or even low-resolution images. The challenge is extreme: you have 224 T-states per scanline, and each colour change costs at minimum 18 T-states (7 for `LD A,n` + 11 for `OUT`). That gives you roughly 12 colour changes per scanline, which means at most 12 horizontal colour bands per line.

Demo coders have pushed this to remarkable extremes. By pre-loading multiple registers with colour values and using faster sequences like `OUT (C), A` followed by register swaps, they squeeze more colour changes per line. The border becomes a display unto itself -- a canvas outside the canvas.

For our purposes, the border's most important role is the one from Chapter 1: a free, always-available timing visualiser. When you are optimising the screen-fill routine later in this chapter, the border is how you will see your progress.

---

## Practical: The Checkerboard Fill

The example at `chapters/ch02-screen-as-puzzle/examples/fill_screen.a80` fills the pixel area with a checkerboard pattern and the attributes with bright white on blue. Let us walk through it section by section.

```z80 id:ch02_practical_the_checkerboard
    ORG $8000

SCREEN  EQU $4000       ; pixel area start
ATTRS   EQU $5800       ; attribute area start
SCRLEN  EQU 6144        ; pixel bytes (256*192/8)
ATTLEN  EQU 768         ; attribute bytes (32*24)
```

The code is placed at `$8000` -- safely in uncontended memory on all Spectrum models. The constants name the key addresses and sizes.

```z80 id:ch02_practical_the_checkerboard_2
start:
    ; --- Fill pixels with checkerboard pattern ---
    ld   hl, SCREEN
    ld   de, SCREEN + 1
    ld   bc, SCRLEN - 1
    ld   (hl), $55       ; checkerboard: 01010101
    ldir
```

This uses the classic LDIR self-copy trick. It writes `$55` (binary `01010101`) to the first byte at `$4000`, then copies from each byte to the next for 6,143 bytes. The result: every byte of the pixel area is `$55`, which produces alternating set/clear pixels -- a checkerboard. Because the pattern is the same in every byte, the interleaved row order does not matter -- every row gets the same pattern regardless.

Cost: `LDIR` copies 6,143 bytes. The last iteration costs 16T, all others 21T: (6,143 - 1) x 21 + 16 = 128,998 T-states. Nearly two full frames on a Pentagon. This is fine for a one-time setup, but you would never do this in a per-frame rendering loop.

```z80 id:ch02_practical_the_checkerboard_3
    ; --- Fill attributes: white ink on blue paper ---
    ; Attribute byte: flash=0, bright=1, paper=001 (blue), ink=111 (white)
    ; = 01 001 111 = $4F
    ld   hl, ATTRS
    ld   de, ATTRS + 1
    ld   bc, ATTLEN - 1
    ld   (hl), $4F
    ldir
```

Same technique for the attributes. The value `$4F` decodes as: flash off (0), bright on (1), paper blue (001), ink white (111). Every 8x8 cell gets bright white ink on blue paper. The checkerboard pixels are set/clear, so you see alternating white and blue dots -- a classic ZX Spectrum visual pattern.

Cost: `LDIR` copies 767 bytes -- (767 - 1) x 21 + 16 = 16,102 T-states.

```z80 id:ch02_practical_the_checkerboard_4
    ; --- Border: blue ---
    ld   a, 1
    out  ($FE), a

    ; Infinite loop
.wait:
    halt
    jr   .wait
```

Sets the border to blue (colour 1) to match the paper colour, creating a visually clean frame. Then loops forever, halting between frames. The `HALT` waits for the next maskable interrupt, which fires once per frame -- this is the idle heartbeat of every Spectrum program.

![Screen fill with alternating bytes — checkerboard pattern in bright white on blue](../../build/screenshots/ch02_fill_screen.png)

### What to try

Load `fill_screen.a80` in your assembler and emulator. Then experiment:

- Change `$55` to `$AA` for the inverse checkerboard, or to `$FF` for solid fill, or `$81` for vertical bars.
- Change `$4F` to `$07` to see the same pattern without BRIGHT, or to `$38` for white paper with black ink (the inverse of default).
- Try `$C7` -- that sets the flash bit. Watch the characters alternate between ink and paper colours at about 1.6 Hz.
- Replace the LDIR pixel fill with a DOWN_HL loop that writes different patterns to different rows. Now you will see the interleave in action: if you write `$FF` to rows 0-7 (the first character cell's scanlines), the filled area will appear as 8 horizontal stripes separated by gaps -- because those rows are 256 bytes apart, not 32.

---

## Navigating the Screen: A Practical Summary

Here are the essential pointer operations for the Spectrum screen, collected in one place. These are the building blocks of every graphics routine.

### Moving right one byte (8 pixels)

```z80 id:ch02_moving_right_one_byte_8
    inc  l             ; 4T
```

This works within a character row because the column is in the low 5 bits of L. If you need to cross byte boundaries at the right edge (column 31 to column 0 of the next row), you need the full DOWN_HL plus reset of L -- but typically you do not, because your loops are 32 bytes wide.

### Moving down one pixel row

```z80 id:ch02_moving_down_one_pixel_row
    inc  h             ; 4T    (within a character cell)
```

This works for 7 out of 8 rows. On the 8th row, you need the full boundary-crossing logic from the DOWN_HL routine above.

### Moving down one character row (8 pixels)

```z80 id:ch02_moving_down_one_character_row
    ld   a, l          ; 4T
    add  a, 32         ; 7T
    ld   l, a          ; 4T    total: 15T (if no third crossing)
```

This advances by one character row within a third. If L overflows (carry set), you have crossed into the next third and need to add 8 to H.

### Moving up one pixel row

```z80 id:ch02_moving_up_one_pixel_row
    dec  h             ; 4T    (within a character cell)
```

The inverse of `INC H`. Same boundary issues at character cell and third boundaries. Here is the full UP_HL routine, the mirror of DOWN_HL:

```z80 id:ch02_moving_up_one_pixel_row_2
; UP_HL: move HL one pixel row up on the Spectrum screen
; Input:  HL = current screen address
; Output: HL = screen address one row above
;
; Classic version:
up_hl:
    dec  h             ; 4T   try moving one scan line up
    ld   a, h          ; 4T
    and  7             ; 7T   did we cross a character boundary?
    cp   7             ; 7T
    ret  nz            ; 11/5T  no: done

    ; Crossed a character cell boundary upward.
    ld   a, l          ; 4T
    sub  32            ; 7T   previous character row (L -= 32)
    ld   l, a          ; 4T
    ret  c             ; 11/5T  if carry, crossed into prev third

    ld   a, h          ; 4T
    add  a, 8          ; 7T   compensate H
    ld   h, a          ; 4T
    ret                ; 10T
```

There is a subtle optimisation here, contributed by Art-top (Artem Topchiy): replacing `and 7 / cp 7` with `cpl / and 7`. After `DEC H`, if the low 3 bits of H wrapped from `000` to `111`, we crossed a character boundary. The classic test checks `AND 7` then compares with 7. The optimised version complements first: if the bits are `111`, CPL makes them `000`, and `AND 7` gives zero. This saves 1 byte and 3 T-states in the boundary-crossing path:

```z80 id:ch02_moving_up_one_pixel_row_3
; UP_HL optimised (Art-top)
; Saves 1 byte, 3 T-states on boundary crossing
;
up_hl_opt:
    dec  h             ; 4T
    ld   a, h          ; 4T
    cpl                ; 4T   complement: 111 -> 000
    and  7             ; 7T   zero if we crossed boundary
    ret  nz            ; 11/5T

    ld   a, l          ; 4T
    sub  32            ; 7T
    ld   l, a          ; 4T
    ret  c             ; 11/5T

    ld   a, h          ; 4T
    add  a, 8          ; 7T
    ld   h, a          ; 4T
    ret                ; 10T
```

The same `CPL / AND 7` trick works in DOWN_HL too, though the boundary condition there tests for `000` (which CPL turns into `111`, also non-zero after AND), so it does not help going downward. It is specifically the *upward* direction where the classic code needs the extra `CP 7` that the optimisation eliminates.

### Computing the attribute address from a pixel address

If HL points to a byte in the pixel area, the corresponding attribute address can be calculated. Recall the pixel address structure: H = `010TTSSS`, L = `LLLCCCCC`. The attribute address for the same character cell is `$5800 + TT * 256 + LLL * 32 + CCCCC`. Since L already encodes `LLL * 32 + CCCCC` (which ranges 0--255), the attribute address is simply `($58 + TT) : L`. All we need to do is extract the two TT bits from H, combine them with `$58`, and leave L unchanged:

```z80 id:ch02_computing_the_attribute
; Convert pixel address in HL to attribute address in HL
; Input:  HL = pixel address ($4000-$57FF)
; Output: HL = corresponding attribute address ($5800-$5AFF)
;
    ld   a, h          ; 4T
    rrca               ; 4T
    rrca               ; 4T
    rrca               ; 4T
    and  3             ; 7T
    or   $58           ; 7T
    ld   h, a          ; 4T
    ; L unchanged       --- Total: 34T
```

This works because L already contains `LLL CCCCC` -- the character row within the third (0--7) combined with the column (0--31) -- and that is exactly the low byte of the attribute address. The high byte just needs the third number added to `$58`. Elegant.

**Special case: when H has scanline bits = 111.** If you are iterating through a character cell top-to-bottom and have just processed the last scanline (scanline 7), the low 3 bits of H are `111`. In this case there is a faster 4-instruction conversion, contributed by Art-top:

```z80 id:ch02_computing_the_attribute_2
; Pixel-to-attribute when H low bits are %111
; (e.g., after processing the last scanline of a character cell)
; Input:  HL where H = 010TT111
; Output: HL = attribute address
;
    srl  h             ; 8T   010TT111 -> 0010TT11
    rrc  h             ; 8T   0010TT11 -> 10010TT1
    srl  h             ; 8T   10010TT1 -> 010010TT
    set  4, h          ; 8T   010010TT -> 010110TT = $58+TT
    ; L unchanged.     --- Total: 32T, 4 instructions
```

This is 2 T-states faster than the general method and avoids the `AND / OR` sequence. The trade-off is that it only works when the scanline bits are `111` -- but that is exactly the situation after a top-to-bottom character cell render loop, which is one of the most common use cases.

---

> **Agon Light 2 Sidebar**
>
> The Agon Light 2's display is managed by a VDP (Video Display Processor) -- an ESP32 microcontroller running the FabGL library. The eZ80 CPU communicates with the VDP over a serial link, sending commands to set graphics modes, draw pixels, define sprites, and manage palettes.
>
> There is no interleaved memory layout. There is no attribute clash. The VDP supports multiple bitmap modes at various resolutions (from 640x480 down to 320x240 and below), with 64 colours or full RGBA palettes depending on the mode. Hardware sprites (up to 256) and tile maps are supported natively.
>
> What changes for the programmer:
>
> - **No address puzzle.** Pixel coordinates map linearly to buffer positions. You do not need DOWN_HL or split-counter screen traversal.
> - **No attribute clash.** Each pixel can be any colour. The 8x8 grid constraint does not exist.
> - **No direct memory access to the framebuffer.** The CPU cannot write directly to video memory the way a Spectrum CPU writes to `$4000`. Instead, you send VDP commands over the serial link. Drawing a pixel means sending a command sequence, not storing a byte. This introduces latency -- the serial link runs at 1,152,000 baud -- but it also means the CPU is free during rendering.
> - **No cycle-level border tricks.** The VDP handles display timing independently. You cannot create raster effects by timing `OUT` instructions, because the display pipeline is decoupled from the CPU clock.
>
> For a Spectrum programmer, the Agon feels freeing and frustrating in equal measure. The constraints that forced creative solutions on the Spectrum simply do not exist -- but neither do the direct-hardware tricks that those constraints enabled. You trade the puzzle for an API.

---

## Putting It Together: What the Screen Layout Means for Code

Every technique in the rest of this book is shaped by the screen layout described in this chapter. Here is why each piece matters:

**Sprite drawing** requires computing a screen address for the sprite's position, then iterating down through the sprite's rows. Each row means `INC H` (7 out of 8 times) or the full character-boundary crossing. A 16-pixel-tall sprite spans exactly 2 character cells -- you will cross one boundary. A 24-pixel sprite spans 3 cells, crossing 2 boundaries. The boundary-crossing cost is a fixed tax on every sprite.

**Screen clearing** (Chapter 3) uses the PUSH trick -- setting SP to `$5800` and pushing data downward through the pixel area. The interleave does not matter for clearing because every byte gets the same value. But for *patterned* clears (striped backgrounds, gradient fills), the interleave means you must think carefully about which rows get which data.

**Scrolling** (Chapter 17) is where the layout hurts most. Scrolling the screen up by one pixel means moving each row's 32 bytes to the address of the row above it. On a linear framebuffer, this is one big block copy. On the Spectrum, the source and destination addresses for each row are related by the DOWN_HL logic -- not by a fixed offset. A scroll routine must navigate the interleave for every row it copies.

**Attribute effects** (Chapters 8--9) are where the layout helps. Because the attribute area is linear and small (768 bytes), updating colours is fast. A full-screen attribute update with LDIR costs about 16,000 T-states -- less than a quarter of a frame. This is why attribute-based effects (tunnels, plasmas, colour cycling) are a staple of Spectrum demoscene work.

---

## Summary

- The Spectrum's 6,912-byte display consists of **6,144 bytes of pixel data** at `$4000`--`$57FF` and **768 bytes of attributes** at `$5800`--`$5AFF`.
- Pixel rows are **interleaved** by character cell: the address encodes y as `010 TT SSS` (high byte) and `LLL CCCCC` (low byte), where the bits of y are shuffled across the address.
- Moving **one pixel row down** within a character cell is just `INC H` (4 T-states). Crossing character and third boundaries requires additional logic.
- The classic **DOWN_HL** routine handles all cases but costs up to 65 T-states at boundaries. For full-screen iteration, **split-counter loops** (Introspec's approach) reduce total cost by 60% and eliminate timing jitter.
- Each attribute byte encodes **Flash, Bright, Paper, and Ink** in the format `FBPPPIII`. Only **two colours per 8x8 cell** -- this is the attribute clash.
- Attribute clash is not just a limitation but a **creative constraint** that defined the Spectrum's visual aesthetic and led to efficient attribute-only demo effects.
- The **border** colour is set by `OUT ($FE), A` (bits 0--2) and changes are visible on the next scanline, making it a **timing debug tool** and a canvas for demoscene raster effects.
- The **Agon Light 2** has no interleaved layout, no attribute clash, and no direct framebuffer access -- it replaces the puzzle with a VDP command API.

---

## Try It Yourself

1. **Map the addresses.** Pick 10 random (x, y) coordinates and calculate the screen address by hand using the `010TTSSS LLLCCCCC` bit layout. Then write a small Z80 routine that plots a single pixel at each coordinate and verify your calculations match.

2. **Visualise the interleave.** Modify `fill_screen.a80` to write different values to the first 8 rows. Write `$FF` (solid) to row 0 and `$00` (empty) to rows 1--7. Because rows 0--7 are at `$4000`, `$4100`, ..., `$4700`, you will need to change H to reach each row. The result should be a single bright line at the very top, with a gap of 7 empty lines before the next solid line at row 8.

3. **Time DOWN_HL.** Use the border-colour timing harness from Chapter 1. Call the classic DOWN_HL routine 191 times (for a full screen traversal) and measure the stripe. Then implement the split-counter version and compare. The split-counter version should produce a visibly shorter stripe.

4. **Attribute painter.** Write a routine that fills the attribute area with a gradient: column 0 gets colour 0, column 1 gets colour 1, and so on (cycling through 0--7). Each row should have the same pattern. Then modify it so each row shifts the pattern by one position -- a diagonal rainbow. This is the seed of an attribute-based demo effect.

5. **Border stripes.** After a `HALT`, execute a tight loop that changes the border colour on every scanline for 64 lines. Use the 8 border colours in sequence (0, 1, 2, 3, 4, 5, 6, 7, repeat). You should see horizontal rainbow stripes in the top border. Adjust the timing delay between `OUT` instructions until the stripes are clean and stable.

---

> **Sources:** Introspec "Eshchyo raz pro DOWN_HL" (Hype, 2020); Introspec "GO WEST Part 1" (Hype, 2015) for contended memory effects at screen addresses; Introspec "Making of Eager" (Hype, 2015) for attribute-based effect design; the Spectrum's ULA documentation for memory layout rationale; Art-top (personal communication, 2026) for the optimised UP_HL and fast pixel-to-attribute conversion.

*Next: Chapter 3 -- The Demoscener's Toolbox. Unrolled loops, self-modifying code, the stack as a data pipe, and the techniques that let you do the impossible within the budget.*
