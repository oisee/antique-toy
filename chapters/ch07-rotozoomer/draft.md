# Chapter 7: Rotozoomer and Chunky Pixels

> *"The trick is that you don't rotate the screen. You rotate your walk through the texture."*
> -- paraphrasing the core insight behind every rotozoomer ever written

---

There is a moment in Illusion where the screen fills with a pattern -- a texture, monochrome, repeating -- and then it begins to turn. The rotation is smooth and continuous, the zoom breathes in and out, and the whole thing runs at a pace that makes you forget you are watching a Z80 push pixels at 3.5 MHz. It is not the most technically demanding effect in the demo. The sphere (Chapter 6) is harder mathematically. The dotfield scroller (Chapter 10) is tighter in its cycle budget. But the rotozoomer is the one that looks effortless, and on the Spectrum, making something look effortless is the hardest trick of all.

This chapter traces two threads. The first is Introspec's 2017 analysis of the rotozoomer from Illusion by X-Trade. The second is sq's 2022 article on Hype about chunky pixel optimisation, which pushes the approach to 4x4 pixels and catalogues a family of rendering strategies with precise cycle counts. Together, they map the design space: how chunky pixels work, how rotozoomers use them, and the performance trade-offs that determine whether your effect runs at 4 frames per screen or 12.

---

## What a Rotozoomer Actually Does

A rotozoomer displays a 2D texture rotated by some angle and scaled by some factor. The naive approach: for every screen pixel, compute its corresponding texture coordinate via a trigonometric rotation:

```text
    tx = sx * cos(theta) * scale  +  sy * sin(theta) * scale  +  offset_x
    ty = -sx * sin(theta) * scale  +  sy * cos(theta) * scale  +  offset_y
```

At 256x192, that is 49,152 pixels each needing two multiplications. Even with a 54-T-state square-table multiply (Chapter 4), you exceed five million T-states -- roughly 70 frames' worth of CPU time. The effect is mathematically trivial and computationally impossible.

The key insight is that the transformation is *linear*. Moving one pixel right on screen always adds the same (dx, dy) to the texture coordinates. Moving one pixel down always adds the same (dx', dy'). The per-pixel cost collapses from two multiplications to two additions:

```text
Step right:   dx = cos(theta) * scale,   dy = -sin(theta) * scale
Step down:    dx' = sin(theta) * scale,  dy' = cos(theta) * scale
```

Start each row at the correct texture coordinate and step by (dx, dy) for every pixel. The inner loop becomes: read the texel, advance by (dx, dy), repeat. Two additions per pixel, no multiplications. The per-frame setup is four multiplications to compute the step vectors from the current angle and scale. Everything else follows from linearity.

This is the fundamental optimisation behind every rotozoomer on every platform. On the Amiga, on the PC, on the Spectrum.

### Fixed-Point Stepping on the Z80

On a 16-bit or 32-bit platform, dx and dy would be fixed-point values: the integer part selects the texel, and the fractional part accumulates sub-pixel precision. On the Z80, we lack the registers and the bandwidth for true fixed-point inner loops. The classic Spectrum solution is to collapse the step to integer increments -- always exactly +1, -1, or 0 per axis -- and control the *ratio* of steps between axes to approximate the angle.

Consider a rotation of 30 degrees. The exact step vector would be (cos 30, -sin 30) = (0.866, -0.5). On a machine with fixed-point arithmetic, you would add 0.866 to the column coordinate and subtract 0.5 from the row coordinate per pixel. On the Z80, the inner loop instead alternates between two integer steps: some pixels step (+1 column, 0 rows) and others step (+1 column, -1 row). If you distribute these in a roughly 2:1 ratio -- two column-only steps for every diagonal step -- the average direction approximates the 0.866:0.5 ratio of a 30-degree walk. This is Bresenham's line algorithm applied to texture traversal.

The zoom factor determines how many texels you skip per screen pixel. At scale 1.0, every texel maps to one screen pixel. At scale 2.0, you skip every other texel, effectively zooming in. On the Spectrum, this is controlled by doubling the walk instructions: instead of one `INC L` per pixel, you execute two, stepping by 2 texels and producing a 2x zoom. Intermediate zoom levels again use Bresenham-like distribution: some pixels step by 1, others by 2, with the ratio controlled by an error accumulator.

The per-frame cost of computing these parameters is negligible: four lookups into a sine table, a few multiplications (or table lookups, see Chapter 4), and a Bresenham setup pass. All the heavy work is in the inner loop, which has been reduced to nothing but register increments and memory reads.

---

## Chunky Pixels: Trading Resolution for Speed

Even at two additions per pixel, writing 6,144 bytes to the Spectrum's interleaved video memory per frame is impractical -- not if you also want to update the angle and leave time for music. Chunky pixels solve this by reducing the effective resolution. Instead of one texel per screen pixel, you map one texel to a 2x2, 4x4, or 8x8 block.

Illusion uses 2x2 chunky pixels: effective resolution 128x96, a 4x reduction in work. The effect looks blocky up close, but at the speed the texture sweeps across the screen, motion hides the coarseness. The eye forgives low resolution when everything is moving.

### Why 2x2 Is the Sweet Spot

The choice of chunk size involves a three-way tradeoff: visual quality, rendering speed, and memory. At 2x2, you get 128x96 effective pixels -- enough to read text and recognise patterns in the texture. At 4x4, the 64x48 grid is noticeably coarser; fine details in the texture become unreadable, but the effect still "reads" as a coherent rotating surface. At 8x8, you are down to 32x24 blocks, which is the attribute grid resolution -- any texture detail is lost, and the effect looks like coloured rectangles. The last case can be useful for colour-only effects (attribute tunnels, Chapter 9), but for a pixel-rendered rotozoomer, 2x2 or 4x4 is the practical range.

The memory cost matters too. Each chunky pixel stores one byte, so a 2x2 rotozoomer at 128x96 needs 12,288 texels per frame. With a 256-byte texture row (the natural width for 8-bit wrapping), the texture itself occupies 256 bytes per row times however many rows you need. A 4x4 version only processes 3,072 texels, which means the inner loop runs one-quarter as many iterations -- but the visual cost is significant.

In practice, Spectrum demos land on 2x2 for featured rotozoomer effects and reserve 4x4 for situations where the rotozoomer shares the screen with other effects (bumpmapping overlays, split-screen compositions).

### The $03 Encoding Trick

The encoding is designed for the inner loop. Each chunky pixel is stored as `$03` (on) or `$00` (off). This value is not arbitrary -- it encodes exactly the two low bits set: `%00000011`. Watch what happens as four pixels accumulate in the A register:

```text
After pixel 1:  A = %00000011                  ($03)
After 2x shift: A = %00001100                  ($0C)
After pixel 2:  A = %00001100 + %00000011      ($0F)
After 2x shift: A = %00111100                  ($3C)
After pixel 3:  A = %00111100 + %00000011      ($3F)
After 2x shift: A = %11111100                  ($FC)
After pixel 4:  A = %11111100 + %00000011      ($FF)
```

If all four pixels are "on", the result is `$FF` -- all bits set. If all four are "off" (`$00`), the shifts and additions produce `$00`. Mixed patterns produce the correct 2-bit-per-pixel stripe: for example, on-off-on-off gives `%11001100` = `$CC`. Each pair of bits in the output byte corresponds to one chunky pixel. Since each chunky pixel is 2 screen pixels wide (2x2), the 8-bit output byte covers exactly 8 screen pixels: four chunky columns times two pixels each.

The critical property: because we only ever add `$03` or `$00`, there is no carry between pixel fields. The two-bit groups never overflow into each other. This is what makes the encoding branchless -- no masking needed, no OR operations, just `ADD A,A` and `ADD A,(HL)`.

---

## The Inner Loop from Illusion

Introspec's disassembly reveals the core rendering sequence. HL walks through the texture; H tracks one axis and L the other:

```z80 id:ch07_the_inner_loop_from_illusion
; Inner loop: combine 4 chunky pixels into one output byte
    ld   a,(hl)        ;  7T  -- read first chunky pixel ($03 or $00)
    inc  l             ;  4T  -- step right in texture
    dec  h             ;  4T  -- step up in texture
    add  a,a           ;  4T  -- shift left
    add  a,a           ;  4T  -- shift left (now shifted by 2)
    add  a,(hl)        ;  7T  -- add second chunky pixel
```

The sequence repeats for the third and fourth pixels. The `inc l` and `dec h` together trace a diagonal path through the texture -- and diagonal means rotated. The specific combination of increment and decrement instructions determines the rotation angle.

| Step | Instructions | T-states |
|------|-------------|----------|
| Read pixel 1 | `ld a,(hl)` | 7 |
| Walk | `inc l : dec h` | 8 |
| Shift + Read pixel 2 | `add a,a : add a,a : add a,(hl)` | 15 |
| Walk | `inc l : dec h` | 8 |
| Shift + Read pixel 3 | `add a,a : add a,a : add a,(hl)` | 15 |
| Walk | `inc l : dec h` | 8 |
| Shift + Read pixel 4 | `add a,a : add a,a : add a,(hl)` | 15 |
| Walk | `inc l : dec h` | 8 |
| Output + advance | `ld (de),a : inc e` | ~11 |
| **Total per byte** | | **~95** |

Introspec measured approximately 95 T-states per 4 chunks.

The critical observation: the walk direction is hardcoded into the instruction stream. A different rotation angle requires different instructions. Eight primary directions are possible using combinations of `inc l`, `dec l`, `inc h`, `dec h`, and `nop`. This means the rendering code changes every frame.

### Self-Modifying Code at the Byte Level

"Per-frame code generation" sounds exotic, but the mechanism is mundane. Each walk instruction is a single byte in memory. `INC L` is opcode `$2C`. `DEC L` is `$2D`. `INC H` is `$24`. `DEC H` is `$25`. `NOP` is `$00`. To change the walk direction from "right and up" (`INC L` + `DEC H`) to "pure right" (`INC L` + `NOP`), you write `$00` to the byte where `$25` currently sits. That is the entire code generation step: `LD A,$00 : LD (walk_target),A`. A few stores into the instruction stream, and the inner loop now walks in a different direction.

The targets are known at assembly time. Each SMC site is labelled (e.g., `.smc_walk_h_0:`) and the patching code uses those labels as literal addresses. There is no dynamic memory allocation, no instruction parsing, no runtime disassembly. You are writing known opcodes to known addresses. The Z80 has no instruction cache to invalidate, no pipeline to flush. The write takes effect immediately on the next fetch from that address.

In a fully unrolled inner loop (which Illusion uses for its 16-byte rows), there would be 64 walk-instruction sites to patch: 4 walk pairs per output byte times 16 bytes per row. Patching 64 bytes costs about 64 x 13 = 832 T-states (each `LD (nn),A` is 13 T-states), which is negligible compared to the 100,000+ T-states the rendering pass takes. The code generator is cheap. The generated code is what matters.

---

## Per-Frame Code Generation

The rendering code is generated fresh each frame, with walk-direction instructions patched for the current angle:

| Angle range | H step | L step | Direction |
|-------------|--------|--------|-----------|
| ~0 degrees | `nop` | `inc l` | Pure right |
| ~45 degrees | `dec h` | `inc l` | Right and up |
| ~90 degrees | `dec h` | `nop` | Pure up |
| ~135 degrees | `dec h` | `dec l` | Left and up |
| ~180 degrees | `nop` | `dec l` | Pure left |
| ~225 degrees | `inc h` | `dec l` | Left and down |
| ~270 degrees | `inc h` | `nop` | Pure down |
| ~315 degrees | `inc h` | `inc l` | Right and down |

For intermediate angles, the generator distributes steps unevenly using Bresenham-like error accumulation. A 30-degree rotation alternates between `inc l : nop` and `inc l : dec h` at roughly a 2:1 ratio, approximating the 1.73:1 tangent of 30 degrees. The resulting code is an unrolled loop where each iteration has its own specific walk pair, tuned to the current angle.

The rendering cost for 128x96 at 2x2 chunky. The 128x96 area is 96 pixel rows, but each 2x2 texel covers two pixel rows, giving 48 texel rows. Each texel row produces 16 output bytes (128 pixels / 8 bits per byte, with 4 chunky pixels packed per byte):

```text
16 output bytes/row x 95 T-states = 1,520 T-states/row
1,520 x 48 texel rows = 72,960 T-states total
```

Roughly 1 frame on a Pentagon (71,680 T-states per frame). But this is the bare inner loop only. A complete accounting adds:

```text
Code generation:        ~  1,000 T  (patching walk instructions)
Row setup (per row):    ~    800 T  (48 rows x ~17 T each)
Buffer-to-screen copy:  ~ 20,000 T  (stack trick, 1,536 bytes)
Sine table lookups:     ~    200 T
Frame overhead:         ~    500 T  (HALT, border, angle update)
                        ----------
Inner loop:               72,960 T
Total per frame:        ~ 95,460 T  (= 1.33 Pentagon frames)
```

On a standard 48K/128K Spectrum at 69,888 T-states per frame, the rendering takes roughly 1.4 frames. Introspec's estimate of 4-6 frames per screen accounts for the more complex code path in Illusion (which handles the full 256x192 screen, not just a 128x96 strip) and the cost of the music engine running in the interrupt. On a Pentagon with its slightly longer frame (71,680 T-states) and no contention, the inner loop runs about 3% faster.

Memory contention on the 48K/128K Spectrum adds another hidden cost. During the top 192 scanlines, the ULA steals cycles from the CPU when accessing the lower 16KB of RAM ($4000-$7FFF). The inner loop reads from the texture (which should be above $8000, out of contended memory) and writes to a buffer (also above $8000), so it avoids contention entirely. The buffer-to-screen transfer, however, writes directly to video RAM and will be slowed by contention if it overlaps with the display period. This is why demos synchronise the screen transfer to the border period or to the bottom of the display.

---

## Buffer to Screen Transfer

The rotozoomer renders into an off-screen buffer, then transfers to video memory. The interleaved screen layout makes direct rendering painful, and buffering avoids tearing.

The transfer uses the stack:

```z80 id:ch07_buffer_to_screen_transfer
    pop  hl                   ; 10T -- read 2 bytes from buffer
    ld   (screen_addr),hl     ; 16T -- write 2 bytes to screen
```

Screen addresses are embedded as literal operands, pre-calculated for the Spectrum's interleaving -- another instance of code generation. At 26 T-states per two bytes, a full 1,536-byte transfer costs under 20,000 T-states. The rendering pass is the bottleneck, not the transfer.

---

## Deep Dive: 4x4 Chunky Pixels (sq, Hype 2022)

sq's article pushes chunky pixels to 4x4 -- effective resolution 64x48. The visual result is coarser, but the performance gain opens up effects like bumpmapping and interlaced rendering. The article is a study in optimisation methodology: start straightforward, iteratively improve, measure at each step.

**Approach 1: Basic LD/INC (101 T-states per pair).** Load chunky value, write to buffer, advance pointers. The bottleneck is pointer management: `INC HL` at 6 T-states adds up over thousands of iterations.

**Approach 2: LDI variant (104 T-states -- slower!).** `LDI` copies a byte and auto-increments both pointers in one instruction. But it also decrements BC, consuming a register pair. The save/restore overhead makes it *slower* than the naive approach. A cautionary tale: on the Z80, the "clever" instruction is not always the fast one.

**Approach 3: LDD dual-byte (80 T-states per pair).** By arranging source and destination in reverse order, `LDD`'s auto-decrement works in your favour. A combined two-byte sequence exploits this for a 21% improvement over baseline.

**Approach 4: Self-modifying code (76-78 T-states per pair).** Pre-generate 256 rendering procedures, one per possible byte value, each with the pixel value baked in as an immediate operand:

```z80 id:ch07_deep_dive_4x4_chunky_pixels
; One of 256 pre-generated procedures
proc_A5:
    ld   (hl),$A5        ; 10T  -- value baked into instruction
    inc  l               ;  4T
    ld   (hl),$A5        ; 10T  -- 4x4 block spans 2 bytes horizontally
    ; ... handle vertical repetition ...
    ret                  ; 10T
```

The 256 procedures occupy approximately 3KB. Per-pixel rendering drops to 76-78 T-states -- 23% faster than baseline, 27% faster than LDI.

### Performance Comparison

| Approach | Cycles/pair | Relative | Memory |
|----------|------------|----------|--------|
| Basic LD/INC | 101 | 1.00x | Minimal |
| LDI variant | 104 | 0.97x | Minimal |
| LDD dual-byte | 80 | 1.26x | Minimal |
| Self-modifying (256 procs) | 76-78 | 1.30x | ~3KB |

The self-modifying approach wins, but the margin over LDD is narrow. In a 128K demo, 3KB is easily available. In a 48K production, the LDD approach might be the better engineering decision.

### Historical Roots: Born Dead #05 and the Scene Lineage

sq notes these techniques build on work published in Born Dead #05, a Russian demoscene newspaper from approximately 2001. Born Dead was one of several Russian-language disk magazines that served as technical journals for the ZX Spectrum demoscene. Unlike Western PC demoscene publications that could assume 486-class hardware, the Spectrum magazines operated under the constraints of a community that was still actively developing new techniques for a machine from 1982. The foundational article described basic chunky rendering -- the idea that you could treat the Spectrum's bit-mapped display as a lower-resolution chunky-pixel buffer and gain speed at the expense of resolution.

sq's contribution, twenty-one years later, was the systematic optimisation and the pre-generated procedure variant. But between Born Dead #05 and sq's 2022 article, the chunky rotozoomer appeared in numerous Spectrum demos. X-Trade's Illusion (ENLiGHT'96) was among the earliest full implementations. Other notable examples include Exploder^XTM's GOA4K and Refresh, 4D's productions, and later work from the Russian and Polish scenes. The technique spread partly through disassembly -- Introspec's 2017 analysis of Illusion is itself an example of the scene's tradition of learning by reverse engineering -- and partly through the informal knowledge network of disk magazines, BBS postings, and direct communication between coders.

This is how scene knowledge evolves: a technique surfaces in an obscure disk magazine, circulates within the community, and twenty-one years later someone revisits it with fresh measurements and new tricks. The chain from Born Dead to sq to this chapter is unbroken.

---

## Practical: Building a Simple Rotozoomer

Here is the structure for a working rotozoomer with 2x2 chunky pixels and a checkerboard texture.

**Texture.** A 256-byte page-aligned table where each byte is `$03` or `$00`, generating 8-pixel-wide stripes. The H register provides the second dimension; XORing H into the lookup creates a full checkerboard:

```lua id:ch07_practical_building_a_simple
    ALIGN 256
texture:
    LUA ALLPASS
    for i = 0, 255 do
        if math.floor(i / 8) % 2 == 0 then
            sj.add_byte(0x03)
        else
            sj.add_byte(0x00)
        end
    end
    ENDLUA
```

**Sine table and per-frame setup.** A 256-entry page-aligned sine table drives the rotation. Each frame reads `sin(frame_counter)` and `cos(frame_counter)` (cosine via a 64-index offset) to compute the step vectors, then patches the inner loop's walk instructions with the correct opcodes.

**The rendering loop.** The outer loop sets the starting texture coordinate for each row (stepping perpendicular to the walk direction). The inner loop walks through the texture:

```z80 id:ch07_practical_building_a_simple_2
.byte_loop:
    ld   a,(hl)              ; read texel 1
    inc  l                   ; walk (patched per-frame)
    add  a,a : add  a,a     ; shift
    add  a,(hl)              ; read texel 2
    inc  l                   ; walk
    add  a,a : add  a,a     ; shift
    add  a,(hl)              ; read texel 3
    inc  l                   ; walk
    add  a,a : add  a,a     ; shift
    add  a,(hl)              ; read texel 4
    inc  l                   ; walk
    ld   (de),a              ; write output byte
    inc  de
    djnz .byte_loop
```

The `inc l` instructions are the targets of the code generator. Before each frame, they are patched to the appropriate combination of `inc l`/`dec l`/`inc h`/`dec h`/`nop` based on the current angle. For non-cardinal angles, a Bresenham error accumulator distributes the minor-axis steps across the row, so each walk instruction in the unrolled loop may be different from its neighbours.

**Main loop.** `HALT` for vsync, compute step vectors, generate walk code, render to buffer, stack-copy buffer to screen, increment frame counter, repeat.

---

## Texture Design and Boundary Handling

The texture is the most constrained data structure in the rotozoomer. Every design decision in the inner loop -- the page alignment, the wrapping behaviour, the power-of-two sizing -- traces back to how the texture is laid out in memory.

### Why Page-Aligned, Why 256 Columns

The texture is page-aligned so that H selects the row and L selects the column. This is not merely convenient; it makes the inner loop possible. `INC L` and `DEC L` wrap at the 256-byte page boundary automatically -- when L overflows from `$FF` to `$00`, H is unchanged. The texture wraps horizontally for free, with zero branch overhead. If the texture were not page-aligned, L increments would carry into H, corrupting the row address. You would need explicit masking (`AND $3F` after every step), which would add 4-8 T-states per pixel and destroy the tight inner loop.

The vertical axis (H) also wraps, but over the full range of rows allocated to the texture. If you allocate 64 rows (pages), H ranges from the texture base page to base+63. `INC H` and `DEC H` will happily walk past the end of the texture into whatever memory follows. Illusion handles this by masking H to the texture height at the start of each row (not per pixel -- per-pixel masking would be too expensive). This works because within a single 16-byte row, the H coordinate changes by at most 16 steps, and if the texture is tall enough relative to the row width, an overflow within a row cannot reach memory that produces visual garbage. A 64-row texture with 16 H-steps per row has a comfortable margin.

### Choosing Texture Size

The texture must be a power-of-two in width (always 256, since L is 8 bits) and ideally a power-of-two in height for easy masking. Common choices:

- **256x256** (64KB): fills all of upper RAM on a 128K Spectrum. Maximum resolution, but leaves no room for code or buffers.
- **256x64** (16KB): the practical choice. Fits in one 16KB bank on 128K hardware. The 6-bit height mask (`AND $3F`) is fast and tiles seamlessly.
- **256x32** (8KB): fits on a 48K Spectrum with room for everything else. The texture repeats more visibly, but for a checkerboard or stripe pattern, repetition *is* the design.
- **256x16** (4KB): minimal. Works for very simple patterns like single-axis stripes.

For non-repeating textures (images, logos), the height should be at least as large as the effective screen height divided by the scale factor. A 2x2 rotozoomer with 96 effective rows needs at least 96 texture rows to avoid visible tiling when the zoom is at 1:1. At higher zoom levels, fewer rows are needed because the camera is "closer" to the texture surface.

### What About Screen Boundaries?

The Spectrum's 256x192 screen is 32 bytes wide by 192 lines. If your rotozoomer fills a 128x96 strip in the centre, you never approach the edge of video memory. But a full-screen rotozoomer at 256x192 (or even 128x192 with 2x2 chunky) must handle the case where the output address reaches the attribute area at `$5800`. The simplest approach: render into a buffer and only copy the portion that fits. A more aggressive approach: clip the row count to the visible area during code generation, which avoids wasted computation but adds complexity to the row loop.

In practice, most Spectrum rotozoomers render a strip smaller than the full screen. The visual framing -- a border, a title bar, a music credit -- hides the cropping and buys back T-states for other effects.

---

## The Design Space

The chunky pixel size is the most consequential design decision in a rotozoomer:

| Parameter | 2x2 (Illusion) | 4x4 (sq) | 8x8 (attributes) |
|-----------|----------------|----------|-------------------|
| Resolution | 128x96 | 64x48 | 32x24 |
| Texels/frame | 12,288 | 3,072 | 768 |
| Inner loop cost | ~73,000 T | ~29,000 T | ~7,300 T |
| Frames/screen | ~1.3 | ~0.5 | ~0.1 |
| Visual quality | Good motion | Chunky but fast | Very blocky |
| Use case | Featured effects | Bumpmapping, overlays | Attribute-only FX |

The 4x4 version fits within a single frame with room for a music engine and other effects. The 2x2 version takes roughly 1.3-1.5 frames (including overhead) but looks substantially better. The 8x8 case is the attribute tunnel from Chapter 9.

Once you have a fast chunky renderer, the rotozoomer is just one application. The same engine drives **bumpmapping** (read height differences instead of raw texels, derive shading), **interlaced effects** (render odd/even rows on alternating frames, doubling effective frame rate at the cost of flicker), and **texture distortion** (vary the walk direction per row for wavy or ripple effects). A 4x4 rotozoomer can share a frame with a scrolltext, a music engine, and a screen transfer. sq's work was motivated by exactly this versatility.

---

## Three Approaches to Texture Rotation

Everything above treats the rotozoomer as one technique with a tuneable chunk size. But "rotozoomer" on the Spectrum is really a family of three distinct approaches, each with different inner loops, different visual character, and different performance profiles. They share the same mathematical foundation -- the linear step vectors, the Bresenham-style angle distribution -- but diverge completely at the rendering level.

### Variant 1: Monochrome Bitmap (Full Pixel Resolution)

The purest form: every screen pixel maps to one texel. The texture is monochrome -- one bit per pixel -- so reading a texel means testing a single bit, and writing to the screen means setting or clearing a single bit. No chunky encoding, no block grouping. The result is a rotated texture at the full 256x192 resolution of the Spectrum display.

The inner loop skeleton looks something like this:

```z80 id:ch07_variant_1_monochrome_bitmap
; For each screen pixel:
; DE = texture pointer, HL = screen pointer
    ld   a,(de)           ;  7T  -- read texture byte
    and  n                ;  7T  -- test texture bit at current coords
    jr   z,.pixel_off     ; 12/7T
    set  m,(hl)           ; 15T  -- set screen bit
    jr   .pixel_done      ; 12T
.pixel_off:
    res  m,(hl)           ; 15T  -- clear screen bit
.pixel_done:
    ; advance texture coords (inc e / dec d / etc.)
    ; advance screen bit position
    ; ... next pixel
```

Note that SET and RES only work with (HL), (IX+d), or (IY+d) -- not (DE) or (BC). This forces HL to serve as the screen pointer, while DE handles the texture coordinates.

The per-pixel cost is brutal: 35-45 T-states minimum, with branching on every pixel. Across 49,152 pixels, that is 1.5 to 2 million T-states for the rendering pass alone -- roughly 21-28 frames on a standard Spectrum. A full-screen monochrome rotozoomer at 50fps is not happening.

But nobody said you need to fill the whole screen. The technique shines when applied to a smaller region -- a 128x64 strip, a circular viewport, a masked area -- or when you accept a lower frame rate in exchange for the visual impact of full-resolution rotation. It also works beautifully for distortion effects where the "rotation" is not uniform: varying the step vectors per scanline produces wave distortions, barrel effects, and the "sonic ripple" look seen in parts of Illusion by Dark/X-Trade. The coordinate mapping is no longer a simple rotation but a per-line warp through the texture. The maths is the same -- fixed-point stepping along a direction -- but the direction itself changes every row.

The visual payoff is striking. Where a 2x2 chunky rotozoomer looks like a rotating mosaic, the monochrome bitmap version looks like a rotating *image*. On a machine where every effect fights the same 69,888 T-state budget, dedicating multiple frames to full-resolution rendering is a deliberate aesthetic choice.

### Variant 2: Chunky Rotozoomer (2x2 or 4x4 Blocks)

This is the technique covered in the bulk of this chapter. Each screen block (2x2 or 4x4 pixels) maps to one texel. The `$03`/`$00` encoding, the `add a,a : add a,(hl)` accumulation, the walk-instruction patching -- all of it targets this approach.

At 2x2 (128x96 effective resolution), the inner loop runs at approximately 95 T-states per output byte, producing the smooth, recognisable rotozoomer seen in Illusion. At 4x4 (64x48), sq's pre-generated procedure variant eliminates the loop overhead entirely, bringing the cost down to 76-78 T-states per output pair and leaving room for multi-effect compositions within a single frame.

The chunky rotozoomer occupies the middle ground: fast enough for real-time, detailed enough to carry a featured effect. It is the workhorse of the Spectrum rotozoomer repertoire.

### Variant 3: Attribute Rotozoomer (8x8 Block "Pixels")

The Spectrum's attribute area at `$5800`-`$5AFF` stores colour information for each 8x8 pixel character cell: 32 columns by 24 rows, 768 bytes total. Each byte encodes INK, PAPER, BRIGHT, and FLASH for a single 8x8 block. The attribute rotozoomer ignores the bitmap entirely and treats these 768 attribute cells as the display surface. Each cell becomes one "pixel" in a 32x24 image.

The inner loop is structurally identical to the chunky version -- step through texture coordinates, read a value, write it to the output -- but the output is the attribute area, and the "texel" value is a colour attribute byte rather than a bit pattern. The effective resolution is just 32x24, which means the entire rendering pass is 768 iterations of the stepping loop.

The maths:

```text
32 columns x 24 rows = 768 attribute cells
~10 T-states per cell (read texel + write attribute + step)
768 x 10 = ~7,680 T-states total
```

That is roughly 11% of a single frame. You could run the attribute rotozoomer nine times over and still have room for a music engine. The cost is so low that the effect is essentially free.

But the visual payoff is different from the bitmap variants. You are not rotating pixels -- you are rotating coloured blocks. At 32x24, fine detail is invisible. What you get instead is a sweeping field of colour, a vivid mosaic that turns and breathes. The attribute rotozoomer in Illusion uses exactly this: a boldly coloured texture (not a monochrome bitmap) mapped through the attribute grid, producing the characteristic "stained glass" look of rotating colour fields that Illusion is known for. The PAPER and INK fields in each attribute byte give you two colours per cell, so a carefully designed texture can pack more visual information than the raw resolution suggests.

The attribute rotozoomer is perfect for backgrounds, transitions, or as a base layer with pixel-level effects composited on top. Because it only writes to the attribute area, the bitmap can be used simultaneously for a different effect -- a scroller, a logo, a particle field -- running at its own pace. This layered approach is a hallmark of multi-effect demo screens on the Spectrum.

### Comparison

| Variant | Effective resolution | Bytes written/frame | ~T-states (render) | Colour | Typical use |
|---------|---------------------|--------------------|--------------------|--------|-------------|
| Monochrome bitmap | 256x192 (or subregion) | 6,144 (full screen) | 1,500,000-2,000,000 | 1-bit | Hero effect, distortion, warp |
| Chunky 2x2 | 128x96 | 1,536 | ~73,000 | 1-bit | Featured rotozoomer |
| Chunky 4x4 | 64x48 | 384 | ~29,000 | 1-bit | Multi-effect, overlay |
| Attribute | 32x24 | 768 | ~7,700 | INK+PAPER (2 colours/cell) | Background, colour wash, transition |

The progression from top to bottom is a smooth trade: resolution for speed, detail for headroom. The monochrome bitmap gives you everything the Spectrum's display can show, at a cost that demands dedication. The attribute version gives you almost nothing in resolution, but it runs so fast that the rotozoomer becomes just another instrument in a multi-effect composition rather than the main event.

All four rows in this table share the same core algorithm. The step vectors are computed the same way. The Bresenham distribution works the same way. The difference is only where you write and how many iterations you run. Once you have built one rotozoomer, you have built all of them.

---

## The Rotozoomer in Context

The rotozoomer is not a rotation algorithm. It is a *memory traversal pattern*. You walk through a buffer in a straight line, and the walk direction determines what you see. Rotation is one choice of direction. Zoom is a choice of step size. The Z80 does not know trigonometry. It knows `INC L` and `DEC H`. Everything else is the programmer's interpretation.

In Illusion, the rotozoomer sits alongside the sphere and the dotfield scroller. All three share the same architecture: precomputed parameters, generated inner loops, sequential memory access. The sphere uses skip tables and variable `INC L` counts. The rotozoomer uses direction-patched walk instructions. The dotfield uses stack-based address tables. Three effects, one engine philosophy.

Dark built all of them. Introspec traced all of them. The pattern that connects them is the lesson of Part II: compute what you need before the inner loop starts, generate code that does nothing but read-shift-write, and keep the memory access sequential.

---

## Summary

- A rotozoomer displays a rotated and zoomed texture by walking through it at an angle. Linearity reduces per-pixel cost from two multiplications to two additions.
- Chunky pixels (2x2, 4x4) reduce effective resolution and rendering cost proportionally. Illusion uses 2x2 at 128x96; sq's system uses 4x4 at 64x48.
- Illusion's inner loop: `ld a,(hl) : add a,a : add a,a : add a,(hl)` with walk instructions between reads. Cost: ~95 T-states per byte for 4 chunky pixels.
- Walk direction changes per frame, requiring code generation -- the rendering loop is patched before each frame.
- sq's 4x4 optimisation journey: basic LD/INC (101 T-states) to LDI (104 T-states, slower) to LDD (80 T-states) to self-modifying code with 256 pre-generated procedures (76-78 T-states, ~3KB). Based on earlier work in Born Dead #05 (~2001).
- Buffer-to-screen transfer via `pop hl : ld (nn),hl` at ~26 T-states per two bytes.
- The rotozoomer shares its architecture with the sphere (Chapter 6) and dotfield (Chapter 10): precomputed parameters, generated inner loops, sequential memory access.

---

> **Sources:** Introspec, "Technical Analysis of Illusion by X-Trade" (Hype, 2017); sq, "Chunky Effects on ZX Spectrum" (Hype, 2022); Born Dead #05 (~2001, original chunky pixel techniques).
