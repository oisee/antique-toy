# Chapter 3: The Demoscener's Toolbox

Every craft has its bag of tricks --- patterns that practitioners reach for so instinctively they stop thinking of them as tricks at all. A Z80 demoscener reaches for the techniques in this chapter.

These patterns --- unrolled loops, self-modifying code, the stack as a data pipe, LDI chains, code generation, and RET-chaining --- appear in almost every effect we will build in Part II. They are what separates a demo that fits in one frame from one that takes three. Learn them here, and you will recognise them everywhere.

---

## Unrolled Loops and Self-Modifying Code

### The cost of looping

Consider the simplest possible inner loop: clearing 256 bytes of memory.

```z80
; Looped version: clear 256 bytes at (HL)
    ld   b, 0            ; 7 T   (B=0 means 256 iterations)
    xor  a               ; 4 T
.loop:
    ld   (hl), a         ; 7 T
    inc  hl              ; 6 T
    djnz .loop           ; 13 T  (8 on last iteration)
```

Each iteration costs 7 + 6 + 13 = 26 T-states to store a single byte. Of those 26 T-states, only 7 actually do the work --- `ld (hl), a` writes the byte. The other 19 T-states are overhead: incrementing the pointer and looping back. That is 73% overhead. For 256 bytes, the total is 256 x 26 - 5 = 6,651 T-states.

On a machine where you have 69,888 T-states per frame (or 71,680 on a Pentagon), those wasted cycles hurt.

### Unrolling: trade ROM for speed

The solution is brutal and effective: write out the loop body N times and delete the loop.

```z80
; Unrolled version: clear 256 bytes at (HL)
    xor  a               ; 4 T
    ld   (hl), a         ; 7 T
    inc  hl              ; 6 T
    ld   (hl), a         ; 7 T
    inc  hl              ; 6 T
    ld   (hl), a         ; 7 T
    inc  hl              ; 6 T
    ; ... repeated 256 times total
```

Each byte now costs 7 + 6 = 13 T-states. No DJNZ. No loop counter. Total: 256 x 13 = 3,328 T-states --- half the looped version.

The cost is code size. Those 256 repetitions of `ld (hl), a : inc hl` occupy 512 bytes. The looped version was 7 bytes. You are paying 505 bytes of ROM for a 50% speed gain. In a 48K demo, that is a real trade-off. In a 128K production with banked memory, it is usually worth it.

**When to unroll:** Inner loops that execute thousands of times per frame --- screen clearing, sprite drawing, data copying. These are the loops where the DJNZ overhead dominates your frame budget.

**When NOT to unroll:** Outer loops that run once or twice per frame. If your setup loop runs 24 times (once per character row), the 5 T-states you save per iteration buy you 120 T-states total --- less than the time it takes to execute three NOPs. Not worth the code bloat.

A practical middle ground is *partial unrolling*. Unroll 8 or 16 iterations inside the loop, then use DJNZ for the outer count. The `push_fill.a80` example in this chapter's `examples/` directory does exactly this: 16 PUSHes per iteration, 192 iterations. You get most of the speed benefit at a fraction of the code cost.

### Self-modifying code: the Z80's secret weapon

The Z80 has no instruction cache. No prefetch buffer. No pipeline. When the CPU fetches an instruction byte from RAM, it reads whatever is there *right now*. If you changed that byte one cycle ago, the CPU sees the new value. This is not a hack or an exploit --- it is a guaranteed property of the architecture.

Self-modifying code (SMC) means writing to instruction bytes at runtime, changing what the program does as it runs. The classic pattern is patching an immediate operand:

```z80
; Self-modifying code: fill with a runtime-determined value
    ld   a, (fill_value)       ; load the fill byte from somewhere
    ld   (patch + 1), a        ; overwrite the operand of the LD below
patch:
    ld   (hl), $00             ; this $00 gets replaced at runtime
    inc  hl
    ; ...
```

The `ld (patch + 1), a` instruction writes into the second byte of the `ld (hl), $00` instruction --- the immediate operand. After the patch, `ld (hl), $00` becomes `ld (hl), $AA` or whatever value you loaded. The CPU has no idea anything happened. It just executes whatever bytes it finds.

This is enormously powerful. Some common SMC patterns:

**Patching opcodes.** You can even replace the instruction itself. Need a loop that sometimes increments HL and sometimes decrements it? Before the loop, write the opcode for INC HL ($23) or DEC HL ($2B) into the instruction byte. Inside the inner loop, there is no branch at all --- the right instruction is already in place. Compare this to a branch-per-iteration approach that would cost 12 T-states (JR NZ) on every single pixel.

**Saving and restoring the stack pointer.** This pattern appears constantly when using PUSH tricks (below):

```z80
    ld   (restore_sp + 1), sp     ; save SP into the operand below
    ; ... do stack tricks ...
restore_sp:
    ld   sp, $0000                ; self-modified: the $0000 was overwritten
```

The `ld (nn), sp` instruction saves the current SP value directly into the two bytes that form the operand of the later `ld sp, nn`. No temporary variable, no extra memory access. This is idiomatic Z80 demoscene code --- you will see it in virtually every production that touches the stack pointer.

**A word of caution.** Self-modifying code is safe and instant on the Z80, the eZ80, and every Spectrum clone. It is *not* safe on modern cached CPUs (x86, ARM) without explicit cache flush instructions. If you are porting to a different architecture, this is the first thing that breaks.

---

## The Stack as a Data Pipe

### Why PUSH is the fastest write on the Z80

The PUSH instruction writes 2 bytes to memory and decrements SP, all in 11 T-states. Let us compare the alternatives for writing data to a screen address:

| Method | Bytes written | T-states | T-states per byte |
|--------|--------------|----------|-------------------|
| `ld (hl), a` + `inc hl` | 1 | 13 | 13.0 |
| `ld (hl), a` + `inc l` | 1 | 11 | 11.0 |
| `ldi` | 1 | 16 | 16.0 |
| `ldir` (per byte) | 1 | 21 | 21.0 |
| `push hl` | 2 | 11 | **5.5** |

PUSH writes two bytes in 11 T-states --- 5.5 T-states per byte. That is roughly 2.4x faster than the fastest single-byte alternative (`ld (hl), a` + `inc l`) and nearly 4x faster than LDIR.

The catch is that PUSH writes to where SP points, and SP is normally your stack. To use PUSH as a data pipe, you must hijack the stack pointer.

### The technique

The pattern is always the same:

1. Disable interrupts (DI). If an interrupt fires while SP points to the screen, the CPU will push the return address into your pixel data. Chaos follows.
2. Save SP. Use self-modifying code to stash it.
3. Set SP to the *end* of your target area. The stack grows downward --- PUSH decrements SP before writing. So if you want to fill from $4000 to $57FF, you set SP to $5800.
4. Load your data into register pairs and PUSH repeatedly.
5. Restore SP and re-enable interrupts (EI).

Here is the core of the `push_fill.a80` example from this chapter's `examples/` directory:

```z80
stack_fill:
    di                          ; critical: no interrupts while SP is moved
    ld   (restore_sp + 1), sp   ; self-modifying: save SP

    ld   sp, SCREEN_END         ; SP points to end of screen ($5800)
    ld   hl, $AAAA              ; pattern to fill

    ld   b, 192                 ; 192 iterations x 16 PUSHes x 2 bytes = 6144
.loop:
    push hl                     ; 11 T  \
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |  16 PUSHes = 32 bytes
    push hl                     ; 11 T   |  = 176 T-states
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |
    push hl                     ; 11 T  /
    djnz .loop                  ; 13 T (8 on last)

restore_sp:
    ld   sp, $0000              ; self-modified: restores original SP
    ei
    ret
```

The 16-PUSH inner body writes 32 bytes in 176 T-states. With the DJNZ overhead, the total for 6,144 bytes (the entire pixel area) comes to roughly 36,000 T-states. Compare that to LDIR for the same job: 6,144 x 21 - 5 = 129,019 T-states. The PUSH method is about 3.6x faster.

For a full-screen clear, that difference is the difference between fitting comfortably in one frame and bleeding into the next.

### Where PUSH tricks are used

- **Screen clearing.** The most common use. Every demo needs to clear the screen between effects.
- **Compiled sprites.** The sprite is compiled into a sequence of PUSH instructions with pre-loaded register pairs. The fastest possible sprite output on the Z80.
- **Fast data output.** Any time you need to blast a block of data to a contiguous address range: attribute fills, buffer copies, display list construction.

The price you pay: interrupts are off. If your music player runs from an IM2 interrupt, it will miss a beat during a long PUSH sequence. Demo coders plan around this --- schedule PUSH fills during border time, or split them across multiple frames.

---

## LDI Chains

### LDI vs LDIR

The Z80 has two flavours of block copy: LDI (copy one byte) and LDIR (repeat until BC = 0). Both copy a byte from (HL) to (DE), increment HL and DE, and decrement BC. The difference is timing:

| Instruction | T-states | Notes |
|-------------|----------|-------|
| LDI | 16 | Copies 1 byte, always 16 T |
| LDIR (per byte) | 21 | Copies 1 byte, loops back. Last byte: 16 T |

LDIR costs 5 extra T-states per byte because, after each copy, it checks whether BC has reached zero and, if not, decrements PC by 2 to re-execute itself. Those 5 T-states add up fast.

For 256 bytes:
- LDIR: 255 x 21 + 16 = 5,371 T-states
- 256 x LDI: 256 x 16 = 4,096 T-states
- Savings: 1,275 T-states (24%)

A chain of individual LDI instructions is just 256 repetitions of the two-byte opcode `$ED $A0`. That is 512 bytes of code to save 24% --- the same ROM-for-speed trade-off as loop unrolling.

### When LDI chains shine

The sweet spot for LDI chains is copying blocks where you know the size at assembly time and the size is not too large. Copying a 32-byte sprite row? A chain of 32 LDIs costs 64 bytes of code and saves 160 T-states over LDIR. For 24 character rows of sprite data, that is 3,840 T-states saved per frame. Worthwhile.

The real power of LDI chains emerges when you combine them with *entry point arithmetic*. If you have a chain of 256 LDIs and you want to copy only 100 bytes, you can jump into the chain at position 156. No loop counter, no setup --- just calculate the entry point and JP to it. This technique is used in Introspec's chaos zoomer in the demo Eager (2015):

```z80
; Chaos zoomer inner loop (simplified from Eager)
; Each line copies a different number of bytes from a source buffer.
; Entry point into the LDI chain is calculated per line.
    ld   hl, source_data
    ld   de, dest_screen
    ; ... calculate entry point based on zoom factor ...
    jp   (ix)             ; jump into the LDI chain at the right point

ldi_chain:
    ldi                   ; byte 255
    ldi                   ; byte 254
    ldi                   ; byte 253
    ; ... 256 LDIs total ...
    ldi                   ; byte 0
    ; falls through to next line setup
```

This variable-length copy with zero per-byte loop overhead is a technique you simply cannot achieve with LDIR. It is one reason LDI is everyone's best friend in demoscene code.

---

## Code Generation

### The most powerful technique

Everything above --- unrolling, self-modification, PUSH tricks, LDI chains --- is a fixed optimisation. You write the code once, and it runs the same way every frame. Code generation goes further: your program writes the program that draws the screen.

This is the technique that separates good demos from impossible ones.

There are two variants: offline code generation (before assembly) and runtime code generation (during execution).

### Offline: generating assembly from a higher-level language

Introspec used Processing (a Java-based creative coding environment) to generate Z80 assembly code for the chaos zoomer in his demo Eager (2015). The idea: a chaos zoomer changes its magnification and position every frame. Each frame, different pixels from the source image map to different screen locations. Rather than computing these mappings at runtime --- which would require division, multiplication, and branching deep in the inner loop --- the Processing script pre-calculated every mapping and output .a80 source files containing nothing but optimised LDI chains and LD instructions.

The workflow: a Processing script calculates, for each frame, which source byte maps to which screen byte. It outputs Z80 assembly source --- sequences of `ld hl, source_addr` and `ldi` instructions --- which the assembler (SjASMPlus) builds alongside the hand-written engine code. At runtime, the engine simply calls into the pre-generated code for the current frame.

This is not "cheating." It is the fundamental insight that division of labour between compile time and runtime can eliminate branches, lookups, and arithmetic from the inner loop entirely. The Processing script does the hard maths once, slowly, on a modern machine. The Z80 does the easy part --- copying bytes --- as fast as physically possible.

### Runtime: the program writes machine code during execution

Sometimes the parameters change every frame, so offline generation is not enough. In these cases, the program generates machine code into a RAM buffer at runtime, then executes it.

The sphere-mapping routine in X-Trade's legendary Illusion (ENLiGHT'96) uses this approach. The sphere geometry changes as it rotates: different pixels need different skip distances, different source addresses. Before each frame, the engine writes Z80 machine code bytes --- actual opcode bytes --- into a buffer. The code might look something like this:

```z80
; Runtime code generation (conceptual, simplified from Illusion)
; Generate an unrolled rendering loop for this frame's sphere slice

    ld   hl, code_buffer
    ld   de, sphere_table       ; per-frame skip distances

    ld   b, SPHERE_WIDTH
.gen_loop:
    ld   a, (de)                ; load skip distance for this pixel
    inc  de

    ; Emit: ld a, (hl) -- opcode $7E
    ld   (hl), $7E
    inc  hl

    ; Emit: add a, N   -- opcodes $C6, N
    ld   (hl), $C6
    inc  hl
    ld   (hl), a                ; the skip distance, as immediate operand
    inc  hl

    djnz .gen_loop

    ; Emit: ret -- opcode $C9
    ld   (hl), $C9

    ; Now execute the generated code
    call code_buffer
```

The generated code is a straight-line sequence with no branches, no lookups, no loop overhead. It runs as fast as hand-written unrolled code, but it is *different code every frame*.

When your inner loop changes shape every frame --- because a rotozoomer changes direction, or a sphere rotates, or a tunnel shifts --- runtime code generation avoids branches entirely. Instead of "if pixel_skip == 3 then..." at 12 T-states per branch, you emit the exact instructions needed and execute them branch-free.

**When to generate code:** If the same operations happen every frame with only data changes, self-modifying code (patching operands) suffices. If the *structure* changes --- different numbers of iterations, different instruction sequences --- generate the code. If you can precompute the variations on a modern machine, prefer offline generation: it is debuggable, verifiable, and imposes zero runtime cost. Runtime generation pays off when the generated code executes far more often than it costs to generate.

---

## RET-Chaining

### Turning the stack into a dispatch table

In 2025, DenisGrachev published a technique on Hype that he developed for his game Dice Legends. The problem: rendering a tile-based playfield requires drawing dozens of tiles per frame, each at a different screen position. The naive approach calls each tile-drawing routine with CALL:

```z80
; Naive approach: call each tile renderer
    call draw_tile_0
    call draw_tile_1
    call draw_tile_2
    ; ...
```

Each CALL costs 17 T-states. For a 30 x 18 playfield (540 tiles), that is 9,180 T-states spent just on CALL instructions --- not counting the tile drawing itself.

DenisGrachev's insight: set SP to a *render list* --- a table of addresses in memory --- and end each tile-drawing procedure with RET. RET pops 2 bytes from (SP) into PC and increments SP. If SP points to your render list, RET does not return to the caller --- it jumps to the next tile-drawing routine in the list.

```z80
; RET-chaining: zero call overhead
    di
    ld   (restore_sp + 1), sp   ; save SP
    ld   sp, render_list        ; SP points to our dispatch table

    ; "Call" the first tile routine by falling into it or using RET:
    ret                         ; pops first address from render_list

; Each tile routine ends with:
draw_tile_N:
    ; ... draw the tile ...
    ret                         ; pops NEXT address from render_list

; The render list is a sequence of addresses:
render_list:
    dw   draw_tile_42           ; first tile to draw
    dw   draw_tile_7            ; second tile
    dw   draw_tile_42           ; third tile (same tile type, different position)
    ; ... one entry per tile on screen ...
    dw   render_done            ; sentinel: address of cleanup code

render_done:
restore_sp:
    ld   sp, $0000              ; self-modified: restore SP
    ei
```

Each "call" now costs just 10 T-states (the cost of RET) instead of 17 (CALL). For 540 tiles, that saves 540 x 7 = 3,780 T-states. But the real gain is deeper: because each tile routine can be a different procedure --- wide tile, narrow tile, blank tile, animated tile --- you get free dispatch. No jump table lookup, no indirect call, no switch statement. The render list *is* the program.

### Three strategies for the render list

DenisGrachev explored three approaches to constructing the render list:

1. **Map as render list.** The tilemap itself is the render list: each cell contains the address of the drawing routine for that tile type. Simple but inflexible --- changing a tile means rewriting 2 bytes in the map.

2. **Address-based segments.** The screen is divided into segments. Each segment's render list is a block of addresses copied from a master table. Changing tiles means copying a new address block.

3. **Byte-based with 256-byte lookup tables.** Each tile type is a single byte (the tile index). A 256-byte lookup table maps tile indices to routine addresses. The render list is built by iterating through the tilemap bytes and looking up each address. This is the approach DenisGrachev chose for Dice Legends.

Using the byte-based approach, he expanded the playfield from 26 x 15 tiles (the limit of his previous engine) to 30 x 18 tiles while maintaining the target frame rate. The savings from eliminating CALL overhead, combined with the zero-cost dispatch, freed enough cycles to render 40% more tiles.

### The trade-offs

RET-chaining shares the same fundamental constraint as all stack tricks: interrupts must be disabled while SP is hijacked. If your music engine runs from IM2, you need to schedule the rendering carefully --- either finish all RET-chaining before the interrupt fires, or run the music engine from the main loop instead.

The technique also requires that each tile routine be a self-contained procedure that ends with RET and does not itself use CALL (since the stack is not available for nested calls). In practice, tile routines are short and simple enough that this is not a limitation.

---

## Sidebar: "Code is Dead" (Introspec, 2015)

In January 2015, Introspec published a short, provocative essay on Hype titled "Code is Dead" (Kod myortv). The argument draws a parallel to Roland Barthes' "Death of the Author": just as Barthes argued that a text's meaning belongs to the reader, not the writer, Introspec argues that demo code only truly lives when someone reads it --- in a debugger, in a disassembly listing, in source code shared on a forum.

The uncomfortable truth: modern demos are consumed as visual media. People watch them on YouTube. They vote on Pouet based on video captures. Nobody sees the inner loops. A brilliant optimisation that saves 3 T-states per pixel is invisible to 99% of the audience. "Writing code purely for its own sake," Introspec wrote, "has lost relevance."

And yet.

You are reading this book. We are opening the debugger. We are counting T-states. We are looking inside. The techniques in this chapter are not museum exhibits. They are living tools, and the fact that most people will never see them does not diminish their craft.

Introspec's essay is a challenge, not a surrender. He went on to publish some of the most detailed technical analyses the ZX scene has ever produced --- including the Illusion teardown and the compression benchmarks referenced throughout this book. Code may be dead to the YouTube viewer. But to the reader with a disassembler and a curious mind, it is very much alive.

---

## Putting It All Together

The techniques in this chapter are not independent. In practice, they compose:

- **Screen clearing** combines *unrolled loops* with *PUSH tricks*: a partially unrolled loop of 16 PUSHes per iteration, with SP hijacked via *self-modifying code*.
- **Compiled sprites** combine *code generation* (each sprite compiles to executable code), *PUSH output* (the fastest way to write pixel data), and *self-modification* (patching screen addresses per frame).
- **Tile engines** combine *RET-chaining* for dispatch with *LDI chains* inside each tile routine for fast data copy.
- **Chaos zoomers** combine *offline code generation* (Processing scripts emitting assembly) with *LDI chains* (the generated code is mostly LDI sequences) and *self-modification* (patching source addresses per frame).

The common thread: every technique eliminates something from the inner loop. Unrolling eliminates the loop counter. Self-modification eliminates branches. PUSH eliminates per-byte overhead. LDI chains eliminate the LDIR repeat penalty. Code generation eliminates the entire distinction between code and data. RET-chaining eliminates CALL overhead.

The Z80 runs at 3.5 MHz. You have 69,888 T-states per frame. Every T-state you save in the inner loop is a T-state you can spend on more pixels, more colours, more motion. The toolbox in this chapter is how you get there.

In the chapters that follow, you will see each of these techniques at work in real demos --- the textured sphere of Illusion, the attribute tunnel of Eager, the multicolor engine of Old Tower. The goal of this chapter was to give you the vocabulary. Now let us see what the masters built with it.

---

## Try It Yourself

1. **Measure the difference.** Take the timing harness from Chapter 1 and measure three versions of a 256-byte fill: (a) the `ld (hl), a : inc hl : djnz` loop, (b) a fully unrolled `ld (hl), a : inc hl` x 256, and (c) the PUSH-based fill from `examples/push_fill.a80`. Compare the border stripe widths. The PUSH version's stripe should be visibly shorter.

2. **Build a self-modifying clear.** Write a screen-clear routine that takes the fill pattern as a parameter and patches it into a PUSH-based fill loop using self-modifying code. Call it twice with different patterns and watch the screen alternate.

3. **Time an LDI chain.** Write a 32-byte copy using LDIR and another using 32 x LDI. Measure both with the border-colour technique. The LDI chain should save 160 T-states --- visible if you run the copy in a tight loop.

4. **Experiment with entry points.** Build a 128-entry LDI chain and a small routine that calculates an entry point based on a value in register A (0--128). Jump into the chain at different points. This is a simplified version of the variable-length copy used in real chaos zoomers.

> **Sources:** DenisGrachev "Tiles and RET" (Hype, 2025); Introspec "Making of Eager" (Hype, 2015); Introspec "Technical Analysis of Illusion" (Hype, 2017); Introspec "Code is Dead" (Hype, 2015)
