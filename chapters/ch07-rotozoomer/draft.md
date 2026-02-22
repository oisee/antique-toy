# Chapter 7: Rotozoomer and Chunky Pixels

> *"The trick is that you don't rotate the screen. You rotate your walk through the texture."*
> -- paraphrasing the core insight behind every rotozoomer ever written

---

There is a moment in Illusion where the screen fills with a pattern -- a texture, monochrome, repeating -- and then it begins to turn. The rotation is smooth and continuous, the zoom breathes in and out, and the whole thing runs at a pace that makes you forget you are watching a Z80 push pixels at 3.5 MHz. It is not the most technically demanding effect in the demo. The sphere (Chapter 6) is harder mathematically. The dotfield scroller (Chapter 10) is tighter in its cycle budget. But the rotozoomer is the one that looks effortless, and on the Spectrum, making something look effortless is the hardest trick of all.

This chapter traces two threads. The first is Introspec's 2017 analysis of the rotozoomer from Illusion by X-Trade. The second is sq's 2022 article on Hype about chunky pixel optimisation, which pushes the approach to 4x4 pixels and catalogues a family of rendering strategies with precise cycle counts. Together, they map the design space: how chunky pixels work, how rotozoomers use them, and the performance trade-offs that determine whether your effect runs at 4 frames per screen or 12.

---

## What a Rotozoomer Actually Does

A rotozoomer displays a 2D texture rotated by some angle and scaled by some factor. The naive approach: for every screen pixel, compute its corresponding texture coordinate via a trigonometric rotation:

```
    tx = sx * cos(theta) * scale  +  sy * sin(theta) * scale  +  offset_x
    ty = -sx * sin(theta) * scale  +  sy * cos(theta) * scale  +  offset_y
```

At 256x192, that is 49,152 pixels each needing two multiplications. Even with a 54-T-state square-table multiply (Chapter 4), you exceed five million T-states -- roughly 70 frames' worth of CPU time. The effect is mathematically trivial and computationally impossible.

The key insight is that the transformation is *linear*. Moving one pixel right on screen always adds the same (dx, dy) to the texture coordinates. Moving one pixel down always adds the same (dx', dy'). The per-pixel cost collapses from two multiplications to two additions:

```
Step right:   dx = cos(theta) * scale,   dy = -sin(theta) * scale
Step down:    dx' = sin(theta) * scale,  dy' = cos(theta) * scale
```

Start each row at the correct texture coordinate and step by (dx, dy) for every pixel. The inner loop becomes: read the texel, advance by (dx, dy), repeat. Two additions per pixel, no multiplications. The per-frame setup is four multiplications to compute the step vectors from the current angle and scale. Everything else follows from linearity.

This is the fundamental optimisation behind every rotozoomer on every platform. On the Amiga, on the PC, on the Spectrum.

---

## Chunky Pixels: Trading Resolution for Speed

Even at two additions per pixel, writing 6,144 bytes to the Spectrum's interleaved video memory per frame is impractical -- not if you also want to update the angle and leave time for music. Chunky pixels solve this by reducing the effective resolution. Instead of one texel per screen pixel, you map one texel to a 2x2, 4x4, or 8x8 block.

Illusion uses 2x2 chunky pixels: effective resolution 128x96, a 4x reduction in work. The effect looks blocky up close, but at the speed the texture sweeps across the screen, motion hides the coarseness. The eye forgives low resolution when everything is moving.

The encoding is designed for the inner loop. Each chunky pixel is stored as `$03` (on) or `$00` (off). Why `$03`? Because `ADD A,A` twice shifts it left by 2 positions, and then `ADD A,(HL)` merges the next pixel's `$03` into the lower bits. Four chunky pixels combine into one output byte using nothing but shifts and additions -- no masking, no branching, no bit manipulation.

---

## The Inner Loop from Illusion

Introspec's disassembly reveals the core rendering sequence. HL walks through the texture; H tracks one axis and L the other:

```z80
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

The rendering cost for 128x96 at 2x2 chunky:

```
16 output bytes/row x 95 T-states = 1,520 T-states/row
1,520 x 96 rows = 145,920 T-states total
```

Roughly 2 frames on a Pentagon. Introspec's estimate of 4-6 frames per screen is more conservative, accounting for code generation, buffer transfer, and the overhead that accumulates beyond the bare inner loop.

---

## Buffer to Screen Transfer

The rotozoomer renders into an off-screen buffer, then transfers to video memory. The interleaved screen layout makes direct rendering painful, and buffering avoids tearing.

The transfer uses the stack:

```z80
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

```z80
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

### Historical Roots: Born Dead #05

sq notes these techniques build on work published in Born Dead #05, a Russian demoscene newspaper from approximately 2001. The foundational article described basic chunky rendering; sq's contribution was the systematic optimisation and the pre-generated procedure variant. This is how scene knowledge evolves: a technique surfaces in an obscure disk magazine, circulates within the community, and twenty-one years later someone revisits it with fresh measurements and new tricks.

---

## Practical: Building a Simple Rotozoomer

Here is the structure for a working rotozoomer with 2x2 chunky pixels and a checkerboard texture.

**Texture.** A 256-byte page-aligned table where each byte is `$03` or `$00`, generating 8-pixel-wide stripes. The H register provides the second dimension; XORing H into the lookup creates a full checkerboard:

```z80
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

```z80
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

## The Design Space

The chunky pixel size is the most consequential design decision in a rotozoomer:

| Parameter | 2x2 (Illusion) | 4x4 (sq) | 8x8 (attributes) |
|-----------|----------------|----------|-------------------|
| Resolution | 128x96 | 64x48 | 32x24 |
| Texels/frame | 12,288 | 3,072 | 768 |
| Inner loop cost | ~146,000 T | ~29,000 T | ~7,300 T |
| Frames/screen | ~2.3 | ~0.5 | ~0.1 |
| Visual quality | Good motion | Chunky but fast | Very blocky |
| Use case | Featured effects | Bumpmapping, overlays | Attribute-only FX |

The 4x4 version fits within a single frame with room for a music engine and other effects. The 2x2 version takes 2-3 frames but looks substantially better. The 8x8 case is the attribute tunnel from Chapter 9.

Once you have a fast chunky renderer, the rotozoomer is just one application. The same engine drives **bumpmapping** (read height differences instead of raw texels, derive shading), **interlaced effects** (render odd/even rows on alternating frames, doubling effective frame rate at the cost of flicker), and **texture distortion** (vary the walk direction per row for wavy or ripple effects). A 4x4 rotozoomer can share a frame with a scrolltext, a music engine, and a screen transfer. sq's work was motivated by exactly this versatility.

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
