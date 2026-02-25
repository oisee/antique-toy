# Chapter 1: Thinking in Cycles

> "Coder effects are always about evolving a computation scheme."
> -- Introspec (spke), Life on Mars

You have 71,680 clock ticks. That is your canvas, your budget, your entire world. Every instruction you write costs some of those ticks. Every frame, the counter resets and you get another 71,680 -- no more, no less. Miss the deadline and the screen tears, the music stutters, the illusion breaks.

This chapter is about learning to see your code the way a Z80 demoscener does: not as text, not as algorithms, but as a *budget*.

---

## T-States: The Currency of the Z80

The Z80 CPU does not execute instructions in uniform chunks. Every instruction takes a specific number of **T-states** (time states) -- the fundamental clock cycles of the processor. At 3.5 MHz, one T-state lasts approximately 286 nanoseconds. That number is not important. What is important is that instructions have wildly different costs, and you need to know those costs by heart.

Here is a handful of instructions you will use constantly:

| Instruction | What it does | T-states |
|-------------|-------------|----------|
| `NOP` | Nothing | 4 |
| `LD A,B` | Copy B into A | 4 |
| `LD A,(HL)` | Load byte from memory address in HL | 7 |
| `LD (HL),A` | Store A to memory address in HL | 7 |
| `LD A,n` | Load an immediate byte into A | 7 |
| `INC HL` | Increment HL | 6 |
| `ADD A,B` | Add B to A | 4 |
| `PUSH HL` | Push HL onto the stack | 11 |
| `DJNZ label` | Decrement B, jump if not zero | 13 (taken) / 8 (falls through) |
| `LDIR` | Block copy, per byte | 21 (repeating) / 16 (last byte) |
| `OUT (n),A` | Write A to I/O port | 11 |

Look at the range. A register-to-register `LD A,B` costs 4 T-states -- the minimum for any instruction. A memory read `LD A,(HL)` costs 7, because the CPU needs extra machine cycles to put the address on the bus and wait for the RAM to respond. `LDIR`, the block copy instruction that every Spectrum coder reaches for instinctively, costs 21 T-states per byte it copies (except the last byte, which costs 16). That is over five times the cost of a NOP.

<!-- figure: ch01_tstate_costs -->
![T-state costs for common Z80 instructions](illustrations/output/ch01_tstate_costs.png)

Why does this matter? Because when you are filling a screen, or updating sprite data, or computing the next frame of a plasma effect, every instruction is eating into your budget. The difference between a 4-T-state instruction and a 7-T-state instruction, multiplied across ten thousand iterations in an inner loop, is the difference between an effect that runs at 50 frames per second and one that does not.

### Machine Cycles and Memory Access

Each T-state is one tick of the CPU clock, but the Z80 does not talk to memory on every tick. Instructions are broken into **machine cycles** (M-cycles), each of which takes 3-6 T-states. The first machine cycle of every instruction is the **opcode fetch** (M1), which always takes 4 T-states: the CPU puts the program counter on the address bus, reads the opcode byte, and simultaneously refreshes DRAM. Further machine cycles read additional bytes (operands, memory data) or write results.

This is why `LD A,B` takes exactly 4 T-states -- it is a single-byte instruction that completes entirely within the opcode fetch. But `LD A,(HL)` takes 7 T-states: 4 for the opcode fetch, then 3 more for the memory read cycle where the CPU puts HL on the address bus and reads the byte at that address.

You do not need to memorize the internal machine cycle breakdown of every instruction. But understanding the pattern -- opcode fetch + operand reads + memory accesses = total cost -- helps you develop intuition for *why* instructions cost what they cost. A `PUSH HL` at 11 T-states makes sense when you realise the CPU must do an opcode fetch (5T for this one, since it also decrements SP), then two separate memory write cycles (3T each) to store the high and low bytes of HL onto the stack.

---

## The Frame: Your Canvas

The ZX Spectrum generates a PAL video signal at approximately 50 frames per second. Every frame, the ULA chip reads video memory and paints the screen, line by line. At the end of each frame, the ULA fires a maskable interrupt. The CPU executes a `HALT` instruction to wait for that interrupt, does its work, and then `HALT`s again to wait for the next frame. This is the heartbeat of every Spectrum program.

The number of T-states between one interrupt and the next -- the **frame budget** -- depends on the machine:

| Machine | T-states per frame | Scanlines | Hz |
|---------|-------------------|-----------|-----|
| ZX Spectrum 48K | 69,888 | 312 | 50.08 |
| ZX Spectrum 128K | 70,908 | 311 | 50.02 |
| Pentagon 128 | 71,680 | 320 | 48.83 |

Those are *total* T-states between interrupts. The practical budget is less -- subtract the interrupt handler cost (a PT3 music player typically consumes 3,000--5,000 T-states per frame), HALT overhead, and on non-Pentagon machines, contention penalties. On a Pentagon with a music player, expect roughly 66,000--68,000 T-states for your main loop. Chapter 15 has the detailed tact-maps.

<!-- figure: ch01_frame_budget -->
![Frame budget breakdown across ZX Spectrum models](illustrations/output/ch01_frame_budget.png)

If your main loop -- input handling, game logic, sound update, screen rendering -- takes more T-states than one frame, you drop frames. Things slow down. The border stripe trick we will build later in this chapter will make that painfully visible.

To put these numbers in perspective: a single `LDIR` copying 6,912 bytes (one full screen of pixel data) costs approximately 6,912 x 21 = 145,152 T-states. That is more than two entire frames on a 48K Spectrum. You cannot even copy the screen once per frame with the simplest possible method. This is the kind of constraint that forces creativity.

---

## Pentagon vs. Wait Machines

You will notice that the frame budgets above differ between machines. The difference is not just in the numbers -- it reflects a fundamental architectural split that shaped the ZX Spectrum demoscene.

### The Original Sinclair Machines

On the original 48K and 128K Spectrums, the screen memory lives at addresses `$4000`-`$5AFF` (pixel data) and `$5800`-`$5B00` (colour attributes). This memory region -- the entire `$4000`-`$7FFF` range, in fact -- is **contended memory**. The ULA (Uncommitted Logic Array), which generates the video signal, needs to read this memory to paint the screen. The CPU and the ULA share the same memory bus, and when both want to read at the same time, the ULA wins. The CPU is forced to wait.

During the 192 active display lines, every CPU access to the `$4000`-`$7FFF` range is potentially delayed. The delay follows a repeating 8-T-state pattern: 6, 5, 4, 3, 2, 1, 0, 0 extra wait states, cycling across each scanline. An instruction that should take 7 T-states might take 13 if it lands on the worst phase of the contention cycle.

This makes cycle-counting on original Spectrums a nightmare. Your carefully calculated inner loop runs at a different speed depending on where in the frame it executes, and whether the code or data it touches happens to be in the contended range. Introspec documented this in his "GO WEST" articles on Hype (2015): during screen rendering, each byte access to contended memory costs an average of 2.625 extra T-states. For stack operations writing to screen memory, expect roughly 1.3 extra T-states per byte.

### The Pentagon: Clean Timing

The Pentagon 128, the most popular Soviet ZX Spectrum clone, took a different approach. Its designers gave the ULA its own memory access window that does not conflict with the CPU. **There is no contended memory on the Pentagon.** Every instruction takes exactly the number of T-states listed in the datasheet, regardless of where the code lives or what memory it accesses.

This is why the Pentagon has a different frame length -- 71,680 T-states, 320 scanlines. The ULA timing is slightly different because there is no need to interleave CPU and ULA access. But the payoff is enormous: you can count cycles with absolute confidence. When your inner loop says it costs 36 T-states per iteration, it costs 36 T-states per iteration, every single time, everywhere in the frame.

This clean timing is why the Pentagon became the standard platform for the ZX Spectrum demoscene, particularly in the Former Soviet Union where these clones were ubiquitous. When you watch demos from groups like X-Trade, 4th Dimension, or Life on Mars, they are overwhelmingly targeting Pentagon timing. When Introspec wrote his legendary technical teardown of Illusion by X-Trade, the cycle counts he quoted assumed Pentagon.

For learning, the Pentagon model is ideal: you can focus on understanding what instructions cost without worrying about contention effects. All the T-state tables in this book assume Pentagon timing unless stated otherwise. When we need to discuss the differences (and we will, in Chapter 15), we will be explicit.

**The practical rule:** place your time-critical code in uncontended memory (`$8000`-`$FFFF` on a 48K), and your cycle counts will be correct on both Pentagons and original Spectrums.

---

## Thinking in Budgets

Now that you know the frame size, you can start doing the arithmetic that defines Z80 demoscene thinking.

Say you want to fill the entire screen with a calculated colour every frame -- a simple plasma effect, updating only the 768 bytes of attribute memory at `$5800`. At 50 fps, you need to compute and write 768 colour values every 71,680 T-states.

If your inner loop per attribute byte looks like this:

```z80 id:ch01_thinking_in_budgets
    ld   a,c        ; 4T   column index
    add  a,b        ; 4T   add row index (diagonal pattern)
    add  a,d        ; 4T   add frame counter (animation)
    and  7          ; 7T   clamp to 0-7
    ld   (hl),a     ; 7T   write attribute
    inc  hl         ; 6T   next attribute address
                    ; --- 32T per byte
```

That is 32 T-states per byte. For 768 bytes: 32 x 768 = 24,576 T-states. Add loop overhead (maintaining counters for rows and columns, the `DJNZ` for the inner loop), and you might land around 28,000-30,000 T-states. That leaves over 40,000 T-states for everything else -- music playback, input handling, whatever you need.

But what if you wanted to update every *pixel* byte, all 6,144 of them? At 32 T-states per byte, that is 196,608 T-states -- nearly three frames. Suddenly you are looking at a 17 fps update rate instead of 50 fps. You either need a faster inner loop, a smaller update region, or a different approach entirely.

This is how Z80 programmers think. Every design decision starts with arithmetic: how many bytes, how many T-states per byte, how many T-states in the frame budget, does it fit? When it does not fit, you do not reach for a faster machine -- you reach for a cleverer algorithm.

---

> **Agon Light 2 Sidebar**
>
> The Agon Light 2 runs a Zilog eZ80 at 18.432 MHz. The eZ80 executes the same Z80 instruction set (it is a direct architectural descendant), but most instructions run in fewer clock cycles -- many single-byte instructions complete in just 1 cycle instead of 4. At 18.432 MHz with a 50 Hz frame rate, you get approximately **368,640 T-states per frame**.
>
> That is just over 5 times the Pentagon's budget. The same Z80 assembly language, the same registers, the same instruction mnemonics -- but with five times the room to breathe. An inner loop that consumes 70% of a Pentagon frame might use only 14% of an Agon frame.
>
> This does not make the Agon "easy." It has its own constraints: no ULA-style video memory (the display is managed by an ESP32 coprocessor running the VDP), flat 24-bit addressing instead of banked memory, and a completely different I/O model. But if you have ever wished you could just have a *little more room* in your frame budget to try something ambitious, the Agon is where the same Z80 thinking scales up.
>
> Throughout this book, we will note where the Agon's larger budget changes the calculus. For now, just remember the number: **~368,000 T-states**. Same ISA, five times the canvas.

---

## Practical: Setting Up Your Development Environment

Before we write our first timing harness, you need a working toolchain. The setup described here follows sq's guide from Hype (2019), which has become the community standard.

### What You Need

1. **VS Code** -- your editor and integrated environment.
2. **Z80 Macro Assembler extension** by mborik (`mborik.z80-macroasm`) -- syntax highlighting, code completion, symbol resolution for Z80 assembly. Install from the VS Code marketplace.
3. **Z80 Assembly Meter** by Nestor Sancho -- displays the byte count and cycle count of the currently selected instruction(s) in the status bar. This is invaluable. Select a block of code and see its total T-state cost instantly.
4. **sjasmplus** -- the assembler itself. Cross-platform, open source, supports macros, Lua scripting, multiple output formats. Download from https://github.com/z00m128/sjasmplus and place the binary somewhere in your PATH.
5. **Unreal Speccy** (Windows) or **Fuse** (cross-platform) -- the emulator. Unreal Speccy is preferred for demo development because it emulates Pentagon timing accurately and has a built-in debugger.

### Project Structure

Create a directory for your Chapter 1 experiments. A minimal project looks like this:

```text
ch01/
  main.a80          -- your source file
  build.bat         -- (Windows) sjasmplus main.a80
  Makefile           -- (macOS/Linux) make target
```

### Build Configuration

In VS Code, set up a build task (`.vscode/tasks.json`) so you can compile with Ctrl+Shift+B:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Assemble Z80",
      "type": "shell",
      "command": "sjasmplus",
      "args": [
        "--fullpath",
        "--nologo",
        "--msg=war",
        "${file}"
      ],
      "group": {
        "kind": "build",
        "isDefault": true
      },
      "problemMatcher": {
        "owner": "z80",
        "fileLocation": "absolute",
        "pattern": {
          "regexp": "^(.*)\\((\\d+)\\):\\s+(error|warning):\\s+(.*)$",
          "file": 1,
          "line": 2,
          "severity": 3,
          "message": 4
        }
      }
    }
  ]
}
```

Press Ctrl+Shift+B. If sjasmplus is in your PATH and there are no errors, you will get a `.sna` or `.tap` file (depending on your source directives) that you can open directly in your emulator.

For integration with Unreal Speccy, Alex_Rider's 2024 extension adds an F5-to-launch binding -- the emulator opens your compiled snapshot automatically. If you are on macOS or Linux and using Fuse, a simple Makefile rule does the same:

```makefile
run: main.sna
	fuse --machine pentagon main.sna
```

---

## Practical: The Timing Harness

This is the most important debugging tool you will build in this entire book. It is dead simple, it requires no special hardware, and you will use it constantly.

The idea: change the border colour to red immediately before the code you want to measure, and change it back to black immediately after. The Spectrum's border is drawn by the ULA in real time, synchronised with the electron beam. A wider red stripe means more T-states spent in your code.

Here is the complete harness:

```z80 id:ch01_practical_the_timing_harness
    ORG $8000

start:
    ; Wait for the frame interrupt
    halt

    ; --- Border RED: code under test begins ---
    ld   a, 2          ; 7T  red = colour 2
    out  ($FE), a      ; 11T write to border port

    ; ===== CODE UNDER TEST =====
    ; Replace this block with whatever you want to measure.
    ; Example: 256 iterations of a NOP loop.

    ld   b, 0          ; 7T  B=0 wraps to 256 iterations
.loop:
    nop                ; 4T
    nop                ; 4T
    nop                ; 4T
    nop                ; 4T  -- 16T per iteration body
    djnz .loop         ; 13T taken, 8T on final iteration
    ; Total: 256 * (16+13) - 5 = 7,419 T-states

    ; ===== END CODE UNDER TEST =====

    ; --- Border BLACK: idle ---
    xor  a             ; 4T  A=0 (black), shorter than LD A,0
    out  ($FE), a      ; 11T

    ; Loop forever
    jr   start
```

Load this into your emulator. You will see a red stripe across the border. The height of that stripe is directly proportional to the number of T-states your test code consumed.

<!-- Screenshot removed: border-colour beam racing not capturable as static image -->

### Reading the Stripe

Each scanline takes 224 T-states (on Pentagon). So if your red stripe is N scanlines tall, your code took approximately N x 224 T-states. The example above uses about 7,419 T-states, which is roughly 33 scanlines -- you should see a red band about one-sixth of the way down the border.

Now try replacing the NOP loop with something heavier. Replace the four NOPs with:

```z80 id:ch01_reading_the_stripe
.loop:
    ld   a,(hl)        ; 7T
    add  a,(hl)        ; 7T
    ld   (de),a        ; 7T
    inc  hl            ; 6T   -- 27T per iteration body
    djnz .loop         ; 13T taken
    ; Total: 256 * (27+13) - 5 = 10,235 T-states
```

The red stripe grows noticeably. That visual difference -- you can see it without a debugger, without a profiler, without any tooling at all -- is 2,816 T-states. About 12 scanlines.

This is how Spectrum demo coders have profiled their effects since the 1980s. The border is your oscilloscope.

### Variations

You can use different colours to mark different phases of your code:

```z80 id:ch01_variations
    ld   a, 2          ; red
    out  ($FE), a
    call render_sprites
    ld   a, 1          ; blue
    out  ($FE), a
    call update_music
    ld   a, 4          ; green
    out  ($FE), a
    call game_logic
    xor  a             ; black
    out  ($FE), a
```

Now the border shows a red band (sprite rendering), then blue (music), then green (game logic), then black (idle time). You can see at a glance which subsystem is eating your frame budget.

A note on `xor a` versus `ld a, 0`: both set A to zero. `XOR A` takes 4 T-states and 1 byte. `LD A, 0` takes 7 T-states and 2 bytes. In a timing harness the difference is negligible, but it is worth noticing -- this kind of micro-awareness is what Z80 coding is made of.

---

## What Fits in a Frame?

Let us use our budget arithmetic to answer some practical questions.

**How many sprites can you draw per frame?** A 16x16 masked sprite using the OR+AND method takes roughly 16 scanlines x (read mask + read sprite + read screen + combine + write screen) per byte. A reasonable estimate is about 1,200 T-states per sprite. On a Pentagon, that is 71,680 / 1,200 = ~59 sprites, if sprite rendering were the *only* thing you did. In practice, with music, game logic, and everything else, 8-12 full sprites per frame is typical.

**How many bytes can LDIR copy per frame?** At 21 T-states per byte: 71,680 / 21 = 3,413 bytes. Not even half the screen.

**How many multiply operations?** A fast square-table 8x8 multiply takes about 54 T-states. 71,680 / 54 = 1,327 multiplications per frame. A single-point 3D rotation needs 9 multiplies. So you could rotate about 147 points per frame *if you did nothing else*. Practical limit with a full demo engine: 30-50 points.

Every design question reduces to this arithmetic. Can I do it? How many can I do? What do I have to give up to make room?

---

## Historical Note: Dark's Advice

In 1997, a programmer named Dark from the group X-Trade published a series of articles in *Spectrum Expert* #01, a Russian electronic magazine for ZX Spectrum developers. These articles covered multiplication, division, sine/cosine generation, and line-drawing algorithms in Z80 assembly -- the fundamental building blocks that power every demo effect.

Dark opened with this advice:

> "Read a maths textbook -- derivatives, integrals. Knowing them, you can create a table of practically any function in assembly."

This was not empty theory. Dark was not just a writer -- he was a coder. X-Trade's demo *Illusion*, released at ENLiGHT'96, featured a textured spinning sphere, a rotozoomer, a 3D engine, and a bouncing dot scroller, all running on a 3.5 MHz Z80. The algorithms Dark described in his magazine articles were the same algorithms powering his demo's effects.

Twenty years later, Introspec (spke) published a detailed technical teardown of Illusion on Hype, analysing the inner loops instruction by instruction, counting every T-state. The magazine articles from 1997 and the reverse engineering from 2017 tell the same story from both sides: the author explaining his building blocks, and a peer measuring the finished machine. We will follow this thread throughout the book.

Dark's point stands: the maths is not optional. You do not need a degree in mathematics, but you need to understand how to turn a mathematical function into a table, how to approximate expensive operations with cheap ones, and how to think about error versus speed. Chapter 4 will walk through Dark's algorithms in detail. For now, remember his advice. It is the starting point of everything.

---

## The Computation Scheme

Introspec, writing about what makes a good demo effect, distilled the philosophy into a single sentence:

> "Coder effects are always about evolving a computation scheme."

This is the deepest insight in this chapter. A demo effect is not a picture; it is a *process*. Each frame, the computation scheme produces the next state from the previous one. The art is in choosing a scheme that produces visually compelling evolution while fitting within the frame budget.

A plasma is a computation scheme: sum sine waves at each grid position, offset by time. A tunnel is a computation scheme: look up angle and distance from pre-computed tables, offset by time. A spinning 3D object is a computation scheme: multiply vertex coordinates by a rotation matrix that changes each frame. The particular scheme determines the visual result, the T-state cost, and the memory requirements -- all at once, all interlocked.

When you sit down to write an effect, you are not asking "how do I draw this picture." You are asking "what computation, evolved frame by frame, produces this visual?" That shift in thinking -- from image to process, from output to scheme -- is the Z80 programmer's worldview.

And the first constraint on any scheme is the budget. 71,680 T-states. Can you evolve your computation within that budget? If not, can you find a cheaper scheme that produces a similar visual? Can you precompute part of the scheme into tables? Can you spread the computation across multiple frames? Can you exploit symmetry to compute half the screen and mirror the other half?

These are the questions that drive every chapter in this book. They start here, with counting T-states.

---

## Summary

- Every Z80 instruction has a specific T-state cost. Learn the common ones by heart: `NOP` = 4, `LD A,B` = 4, `LD A,(HL)` = 7, `PUSH HL` = 11, `LDIR` = 21/16, `OUT (n),A` = 11.
- The **frame budget** is your hard constraint: 69,888 T-states (48K), 70,908 (128K), or 71,680 (Pentagon). At 50 fps, everything must fit.
- **Pentagon has no contended memory**, making cycle counts reliable and predictable. This is why it became the demoscene standard.
- The **Agon Light 2** (eZ80 @ 18.432 MHz) gives ~368,000 T-states per frame -- same instruction set, five times the room.
- The **border colour timing harness** is your oscilloscope: red before, black after, read the stripe width.
- Z80 programming is **budget arithmetic**: bytes x T-states per byte vs. frame budget. Every design decision starts here.
- Effects are **computation schemes evolved over time**. The art is finding a scheme that fits the budget and looks good.

---

## Try It Yourself

1. Build the timing harness from this chapter. Replace the NOP loop with a `LDIR` that copies 256 bytes and compare the stripe width to the NOP version. Calculate the expected T-state difference and verify it visually.

2. Write a loop that fills all 768 bytes of attribute memory (`$5800`-`$5AFF`) with a single colour value. Measure it with the harness. Now try filling it using `LDIR` instead of a byte-by-byte loop. Which is faster? By how many scanlines?

3. Open the Z80 Assembly Meter in VS Code. Select different code blocks and watch the T-state counter in the status bar. Get used to checking costs as you write.

4. Set up the multi-colour border profiler (red / blue / green / black) with three dummy loops of different lengths. Adjust the loop counts until you can visually distinguish all three bands. This is your calibration exercise for reading border timing.

---

*Next: Chapter 2 -- The Screen as a Puzzle. We will dive into the Spectrum's notoriously scrambled video memory layout and learn why `INC H` moves you one pixel down.*
