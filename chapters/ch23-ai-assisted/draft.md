# Chapter 23: AI-Assisted Z80 Development

> "Z80 they still don't know."
> -- Introspec (spke), Life on Mars, 2024

This book was partially written with AI assistance. The chapter you are reading was drafted by Claude Code. The assembler used to build the examples -- MinZ's `mza` -- was built with AI assistance. The "Not Eager" companion demo that this book documents was coded in a feedback loop between a human and an AI agent. If that makes you uncomfortable, good. That discomfort is worth examining.

This is the most self-aware chapter in the book. We are going to look honestly at what AI assistance means for Z80 development in 2026 -- where it genuinely helps, where it confidently fails, and where the answer is a frustrating "it depends." We will do this with real examples, real code, and real failure cases, because the demoscene has never had patience for hype.

---

## 23.1 The Historical Parallel: HiSoft C on ZX Spectrum

Before we talk about AI, let us talk about another attempt to bring higher-level tools to the ZX Spectrum.

In 1998, *Spectrum Expert* #02 -- the same issue where Dark and STS published their midpoint 3D method (Chapter 5) -- reviewed the HiSoft C compiler for ZX Spectrum. The verdict was mixed. The compiler produced code that ran "10--15x faster than BASIC." It supported 33 reserved keywords, offered a stdio.lib that provided graphics at BASIC capability levels, and included `gam128.h` for 128K memory bank access.

But it had no floating-point support.

Think about that for a moment. A C compiler. On a machine where floating-point is already handled by the ROM's RST $28 calculator, sitting there in 16K of free code. And the compiler could not use it.

The conclusion from the *Spectrum Expert* reviewer was precise: "useful for speed-critical work where float isn't needed." A tool with clear strengths and hard limits, evaluated honestly.

HiSoft Pascal HP4D told a similar story. The compiler occupied 12K, leaving roughly 21K for programs. It supported real types and trig functions -- SIN, COS, SQRT -- and was "suitable for data processing and computational mathematics." But 21K for your program, on a machine where a single uncompressed screen takes 6,912 bytes, means you are writing small programs or nothing.

Higher-level languages on constrained hardware have always been a compromise. They accelerate certain tasks enormously. They make other tasks impossible. The question was never "is HiSoft C good or bad?" but "what is it good *for*, and what should you still write in assembly?"

AI-assisted Z80 development is the same kind of compromise. Different shape, same question.

---

## 23.2 The Claude Code Feedback Loop

Here is how AI-assisted Z80 development actually works in practice. It is not magic. It is a loop.

### The Loop

```
prompt --> code --> assemble --> error? --> fix --> assemble --> run --> wrong? --> fix --> run --> correct
  ^                                                                                                |
  +------------------------------------------------------------------------------------------------+
```

You describe what you want. The AI generates Z80 assembly. You assemble it. It fails -- wrong syntax, wrong label format, wrong assembler dialect. You paste the error back. The AI fixes it. You assemble again. This time it compiles. You run it in the emulator. The output is wrong -- the screen fills with garbage, the border is the wrong colour, nothing appears at all. You describe what you see. The AI adjusts. You run again.

This loop is not fundamentally different from how a human programmer works, except for one critical detail: the AI generates its first attempt much faster and gets some classes of errors much more predictably.

### A Concrete Example

Suppose you ask Claude Code to write a routine that fills the ZX Spectrum attribute area with a diagonal stripe pattern. Here is a plausible first attempt:

```z80
; Fill attributes with diagonal stripes
; Pattern: alternating INK colours along diagonals
    ORG $8000

fill_diagonal:
    ld   hl, $5800          ; attribute memory start
    ld   b, 24              ; 24 rows

.row_loop:
    ld   c, 32              ; 32 columns per row
    ld   a, 24
    sub  b                  ; A = row index (0-23)

.col_loop:
    push af
    add  a, c               ; A = row + column
    and  7                  ; clamp to 0-7 (INK colours)
    or   $40                ; set BRIGHT bit
    ld   (hl), a            ; write attribute
    inc  hl
    pop  af
    dec  c
    jr   nz, .col_loop

    djnz .row_loop
    ret
```

This is reasonable code. It assembles. It runs. But there are problems. The column counter `C` counts down from 32, not up from 0, so the diagonal goes the wrong direction. The `or $40` sets bit 6 (BRIGHT), which is correct, but the visual effect has diagonals running top-right to bottom-left instead of the more natural top-left to bottom-right. And the PUSH/POP AF in the inner loop costs 22 T-states per attribute byte -- unnecessary overhead if you restructure the calculation.

None of these are *wrong* in the sense that the code crashes. They are *wrong* in the sense that a Z80 programmer would not write the code this way. A human who has filled attributes hundreds of times would compute the diagonal index differently, avoid the PUSH/POP, and get the direction right on the first attempt because the pattern of row + column is second nature.

Here is the version you arrive at after two iterations:

```z80
fill_diagonal:
    ld   hl, $5800
    ld   d, 0               ; row index

.row_loop:
    ld   e, 0               ; column index
    ld   b, 32

.col_loop:
    ld   a, d
    add  a, e               ; diagonal = row + col
    and  7
    or   $40                ; BRIGHT + INK colour
    ld   (hl), a
    inc  hl
    inc  e
    djnz .col_loop

    inc  d
    ld   a, d
    cp   24
    jr   nz, .row_loop
    ret
```

Cleaner. No PUSH/POP. Diagonals run the right direction. The inner loop costs 4 + 4 + 7 + 4 + 7 + 7 + 6 + 4 + 13 = 56 T-states per byte -- not brilliant, but functional for a fill routine that runs once.

The point is not that the AI wrote bad code. The point is that the *loop* -- prompt, generate, assemble, test, fix, test again -- is the actual workflow. AI assistance does not eliminate the need to understand Z80. It shifts the bottleneck from writing code to evaluating code.

### What Makes the Loop Fast

The loop is faster with AI than without for specific categories of work:

**Boilerplate.** The ORG directive, the HALT loop, the border colour timing harness from Chapter 1, the attribute fill skeleton, the AY register write subroutine, the LDIR setup, the interrupt mode setup. Every Z80 project starts with the same 30-50 lines. The AI generates these correctly and instantly. A human types them from memory. The AI is faster.

**Iteration on a known pattern.** "Now make the diagonal go the other direction." "Add a frame counter so it animates." "Make the colours cycle through BRIGHT and non-BRIGHT." Each iteration is a small delta on existing code. The AI applies the delta faster than manual editing, and the changes are usually correct.

**Test harness generation.** "Write a test that fills memory at $C000 with values 0-255, calls the multiply routine at $8000, and checks the results against a table." The AI generates this kind of scaffolding code quickly and reliably. The structure of a test -- set up inputs, call routine, compare outputs -- is well within AI competence.

**Documentation and comments.** "Add cycle counts to every instruction in this inner loop." The AI knows the Z80 timing tables and applies them correctly in straightforward cases. This is tedious human work that machines handle well.

### What Makes the Loop Slow

**Novel algorithms.** When you ask for something the AI has not seen -- a new unrolling strategy, a trick that exploits Z80 flag behaviour in a specific way, a code generation scheme tailored to your exact data layout -- the AI generates plausible-looking code that is often subtly wrong. Worse, it is wrong in ways that compile and run but produce incorrect results. You spend more time debugging AI-generated code than you would have spent writing it yourself.

**Cycle counting under pressure.** The AI can count cycles for isolated instructions. But when you need to know the exact cost of a routine that spans contended and uncontended memory, involves conditional branches with different taken/not-taken costs, and must fit within a budget of 2,340 T-states (one scanline minus a few instructions), the AI's estimates are unreliable. It will tell you "approximately 2,200 T-states" when the actual cost depends on branch probabilities and memory alignment. This is where DeZog becomes essential.

**Creative effect design.** "Design a visual effect that looks good and fits in 8,000 T-states" is a question the AI cannot answer. It can implement an effect you describe. It cannot invent one. The creative core of demoscene work -- finding a computation scheme that produces compelling visuals within a tight budget -- remains entirely human.

---

## 23.3 DeZog Integration: The Other Half of the Loop

If the AI generates the code, DeZog tells you whether it works.

DeZog is a VS Code extension that provides a Z80 debugger interface. It connects to emulators (ZEsarUX, CSpect, MAME) or its own internal Z80 simulator and gives you breakpoints, memory inspection, register watches, call stacks, and disassembly views -- the standard debugging experience that modern developers expect, applied to Z80 code.

### The AI + DeZog Workflow

The most productive workflow for AI-assisted Z80 development combines Claude Code with DeZog in a tight loop:

1. **Claude Code generates a routine** -- say, an 8x8 multiply.
2. **You assemble it** with `mza` and load it into the DeZog-connected emulator.
3. **You set a breakpoint** at the entry point and step through.
4. **You watch the registers** at each step. Does A contain the right intermediate value after the first `ADD A,B`? Does the carry flag get set when it should?
5. **You spot a divergence** -- the high byte of the result is wrong. You take a screenshot of the register state or copy the values.
6. **You paste the divergence back to Claude Code** -- "After 6 iterations of the shift loop, A = $3C but should be $78. Here are the register values at the breakpoint."
7. **Claude Code identifies the bug** -- usually a missing shift, a wrong register choice, or an off-by-one in the loop count.
8. **You fix, reassemble, retest.**

This workflow is powerful because it gives the AI what it lacks: ground truth. The AI is good at reasoning about code structure but poor at mentally simulating Z80 execution over many iterations. DeZog provides the actual execution state. The AI reasons about the gap between expected and actual state. Together, they converge on correct code faster than either alone.

### Memory Inspection for Data-Heavy Code

For routines that manipulate memory -- screen fills, table generation, buffer operations -- DeZog's memory view is indispensable. You can set a breakpoint after your sine table generation routine and inspect the 256 bytes at the table address. Are they symmetric? Do they peak at the right value? Do they cross zero at the right position?

This is especially valuable for AI-generated lookup tables. Claude Code can generate a routine that computes a 256-byte sine table using the parabolic approximation from Chapter 4. The routine will usually *almost* work -- the shape is right, the range is right, but there might be an off-by-one in the index that shifts the entire table by one position, or a sign error that inverts one quadrant. DeZog lets you see the table directly and compare it to known-good values.

### What DeZog Cannot Do (Yet)

DeZog does not currently integrate with AI agents programmatically. You, the human, are the bridge. You read the register values, you copy them into the prompt, you interpret the AI's response and apply the fix. There is no API where Claude Code can set a breakpoint, read the result, and autonomously decide what to change.

This gap is the next frontier. An AI agent that could run code, observe the result, and iterate without human intervention would close the loop entirely for a class of well-defined problems -- "generate a routine that produces this exact output." But for creative and architectural work, the human remains in the loop.

---

## 23.4 When AI Helps, When It Does Not

Let us be specific. Not "AI is good at some things" -- specific categories with specific assessments.

### AI Helps: High Confidence

**Instruction encoding.** Which instructions are one byte, which are two, which are three? What is the opcode for `LD A,(HL)` versus `LD A,(DE)`? The AI has this memorised perfectly. For the standard Z80 instruction set, it is a reliable reference.

**Cycle counts for individual instructions.** `DJNZ` taken = 13T, not taken = 8T. `LDIR` per byte = 21T except last = 16T. `OUT (C),A` = 12T. The AI gets these right consistently. The one caveat: it sometimes confuses contended and uncontended timing, or Pentagon versus 48K timing. If you specify the machine, it is accurate.

**Boilerplate and scaffolding.** Interrupt mode setup, ORG directives, HALT loops, AY register writes, screen clear routines. These are patterns the AI has seen many times. It generates them correctly and saves typing.

**Translating between assembler dialects.** "Convert this sjasmplus code to mza syntax" or "rewrite this TASM code for z80asm." The AI handles syntax differences (hex prefixes, label formats, directive names) reliably.

**Explaining existing code.** Give the AI a block of Z80 assembly and ask "what does this do?" It will trace through the logic, explain the register usage, and identify common patterns (PUSH/POP save, LDIR block copy, self-modifying code). This is one of its strongest capabilities -- reading Z80 is easier than writing it, and the AI reads well.

### AI Helps: Medium Confidence

**Standard algorithms.** Shift-and-add multiply, restoring division, Bresenham line drawing, LDIR-based scrolling. The AI generates working implementations of these, but they are usually textbook versions -- correct but not optimised. A human would squeeze out 5-15% more speed through register allocation tricks, flag exploitation, and unrolling that the AI does not think to apply.

**Memory layout and addressing.** "Set up a 256-byte aligned table at $xx00" or "calculate the attribute address for screen position (row, col)." The AI understands the Spectrum's screen layout and generates correct address calculations, though it occasionally gets the third-boundary crossing wrong in the pixel memory interleave.

**Simple self-modifying code.** Patching an immediate operand, changing a jump target, swapping an instruction. The AI understands the concept and generates correct examples for simple cases. Complex self-modification -- where the modified code's behaviour depends on multiple patches interacting -- is unreliable.

### AI Does Not Help: Low Confidence

**Novel inner loop optimisation.** This is the big one. When you need to shave 3 T-states off an inner loop that runs 6,144 times per frame -- when 3 T-states is the difference between 50 fps and 48 fps -- the AI cannot reliably find the optimisation. It will suggest standard approaches (unrolling, table lookup, register substitution) but will not discover the *specific* trick that this *specific* data layout and register allocation permit.

Introspec's `ld a,(hl) : inc l : dec h : add a : add a : add (hl)` rotozoomer inner loop from his Illusion analysis (Chapter 7) is 95 T-states for 4 chunky pixel pairs. The genius is in the choice to use `inc l` instead of `inc hl` (saving 2 T-states, 6 for the pair) and to exploit the fact that `add a` (a doubling) is 4T while `sla a` (a shift, which does the same thing) is 8T. These are the kinds of micro-decisions that accumulate into the difference between a demo that runs and a demo that does not. AI does not make these decisions well, because they require understanding the *global* context of register pressure, memory alignment, and frame budget simultaneously.

**Contended memory timing.** On original 48K and 128K Spectrums, memory access in the $4000-$7FFF range incurs variable delays depending on the ULA's scan position. The delay pattern (6, 5, 4, 3, 2, 1, 0, 0 extra T-states per 8-T-state period) interacts with instruction timing in ways the AI cannot reliably predict. Introspec documented this exhaustively in "GO WEST" (Hype, 2015): approximately 2.625 extra T-states per byte access on average during screen rendering. The AI knows this fact but cannot apply it to calculate the actual runtime of a routine that mixes contended and uncontended access.

**Flag-based tricks.** The Z80's flag register is a goldmine for size-coders and optimisers. `SCF` then `RL A` gives a different result than `OR A` then `RL A`. `ADD A,A` sets the carry from bit 7 -- usable as a branch condition *and* a multiplication in one instruction. The AI knows these facts individually but does not spontaneously combine them into novel optimisations.

**Aesthetic judgement.** What looks good? Which colour combination works for a plasma? How should the tunnel distortion curve feel? Should the scroller bounce or sine-wave? These are creative decisions that the AI cannot make. It can implement your aesthetic vision. It cannot have one.

---

## 23.5 Case Study: Building MinZ

MinZ is a programming language for Z80 and eZ80 systems, built by Alice with substantial AI assistance over the course of 2024-2026. It compiles modern, readable code to efficient Z80 assembly. The project is real, open-source, and at version 0.18.0 as of this writing.

MinZ is relevant to this chapter for two reasons. First, it is a case study in AI-assisted development of Z80-targeting tools. Second, it is itself an example of the HiSoft C pattern -- a higher-level language on constrained hardware, with familiar strengths and limits.

### What MinZ Is

MinZ provides typed variables (`u8`, `u16`, `i8`, `i16`, `bool`), functions with multiple returns, control flow (`if/else`, `while`, `for i in 0..n`), structs, arrays, and a standard library covering maths, graphics, input, sound, and memory operations. It compiles to Z80 assembly via its own assembler (`mza`), runs on its own emulator (`mze`), and targets ZX Spectrum, CP/M, and Agon Light 2.

A MinZ program looks like this:

```minz
import stdlib.graphics.screen;
import stdlib.input.keyboard;
import stdlib.time.delay;

fun main() -> void {
    clear_screen();
    draw_circle(128, 96, 50);

    loop {
        wait_frame();
        let dx = get_key_dx();
        // Move sprite based on input...
    }
}
```

This compiles to Z80 assembly, assembles to a binary, and runs on real or emulated hardware. The self-contained toolchain -- compiler, assembler, emulator, REPL, remote runner -- means no external dependencies.

### Where AI Helped Build MinZ

**The compiler itself.** MinZ's compiler is written in Go (~90,000 lines). The bulk of the code generation -- translating MinZ's intermediate representation to Z80 assembly -- was written in an AI-assisted loop. The pattern: describe the semantics of a language feature, generate the code generator, test against the emulator, fix discrepancies. For standard features like arithmetic expressions, function calls, and control flow, this loop converged quickly. Claude Code generated correct code generators for `if/else` and `while` loops on the first or second attempt.

**The assembler.** `mza`, the MinZ Z80 assembler, was built with AI assistance. It supports the full Z80 instruction set, macros, multiple output formats, and two-pass assembly. The instruction encoding table -- which maps mnemonics to opcodes, handling all the Z80's irregular prefix byte patterns (CB, DD, ED, FD) -- was generated by the AI and verified against the Z80 data sheet. This is exactly the kind of systematic, table-driven code that AI handles well.

**The emulator.** `mze`, the built-in Z80 emulator, achieves 100% instruction coverage. Building it involved implementing every Z80 instruction, including the undocumented ones (SLL, the IX/IY half-register operations). The AI generated the initial implementation for each instruction from the Z80 manual, and the test suite (also AI-generated) caught the edge cases -- flag behaviour on overflow, the half-carry flag on DAA, the interrupt enable/disable timing.

**The standard library.** Ten modules covering maths, graphics, input, text, sound, timing, memory, and CP/M system calls. Each module is a MinZ source file that compiles to Z80 assembly. The AI generated initial implementations of standard library functions (memcpy via LDIR, screen clear, keyboard reading) and the human refined them for Z80 efficiency.

**Peephole optimiser.** MinZ includes 35+ peephole optimisation patterns that simplify generated assembly. Patterns like "replace `LD A,0` with `XOR A`" and "replace `LD A,B : OR A : JR NZ` with `LD A,B : OR B : JR NZ`" were proposed by the AI and verified by the human. This is another sweet spot: the AI knows the Z80 instruction set well enough to suggest valid simplifications, and the human verifies they are semantically correct.

### Where AI Did Not Help Build MinZ

**True Self-Modifying Code (TSMC).** MinZ's most distinctive feature is TSMC -- the compiler can emit code that rewrites its own instructions at runtime for performance. A single-byte opcode patch (7-20 T-states) replaces a conditional branch sequence (44+ T-states). The *concept* of TSMC was Alice's invention, not the AI's. The AI could not have proposed "what if the compiled code patched its own opcodes to change behaviour at runtime?" because the idea requires understanding both the compilation model and the Z80's instruction encoding at a level the AI does not reach unprompted.

**The parser.** MinZ originally used tree-sitter for parsing but hit out-of-memory issues on large files. The replacement -- a hand-written recursive descent parser in Go -- was designed by Alice, informed by AI consultation (GPT-4, o4-mini, and Claude were all asked for architectural advice). The AI colleagues agreed that a hand-written parser was the right approach and suggested keeping tree-sitter's test corpus. But the parser's actual grammar design -- how MinZ's syntax maps to AST nodes -- was human work. The AI could generate parser code for individual grammar rules but could not design the grammar itself.

**Register allocation for the code generator.** Deciding which variables live in which Z80 registers, when to spill to memory, and how to handle the Z80's irregular register file (only certain registers can be used with certain instructions) is a constraint satisfaction problem that the AI handles poorly. It generates code that works but wastes registers, uses unnecessary memory stores, and misses opportunities to keep hot values in registers across basic blocks.

### The MinZ Verdict

MinZ could not exist without AI assistance. The sheer volume of systematic code -- the instruction encoder, the emulator, the standard library, the peephole patterns -- would have taken one developer years to write manually. With AI assistance, MinZ went from concept to v0.18.0 in roughly 18 months.

But MinZ's *interesting* features -- TSMC, the zero-cost lambda-to-function transform, the UFCS method dispatch -- are human inventions. The AI implemented them, but did not conceive them.

This maps precisely to the HiSoft C pattern. The tool accelerates the routine work enormously. The creative work remains human. The compromise is real and worth making.

---

## 23.6 Honest Take: "Z80 They Still Don't Know"

Introspec's scepticism about AI's Z80 capabilities is not generic technophobia. It comes from decades of experience pushing the Z80 to its absolute limits. When he says "Z80 they still don't know," he means something specific.

Consider the rotozoomer inner loop from his Illusion analysis. The effect walks through a texture at an angle, producing rotated and zoomed 2x2 chunky pixels. The inner loop is:

```z80
    ld   a, (hl)    ; 7T   read texture byte
    inc  l          ; 4T   next column (no carry needed: 256-aligned!)
    dec  h          ; 4T   previous row
    add  a          ; 4T   double (same as SLA A but 4T not 8T)
    add  a          ; 4T   quadruple
    add  (hl)       ; 7T   combine with second texture sample
                    ; --- 30T per pixel pair
```

The key insight is `inc l` instead of `inc hl`. This saves 2 T-states but only works because the texture is aligned to a 256-byte boundary, so incrementing just L never needs to carry into H. The AI would use `inc hl` -- the safe, general choice -- and lose 2 T-states per iteration. Over 3,072 pixel pairs per frame, that is 6,144 T-states -- nearly 10% of the frame budget on a 48K Spectrum.

This is what "Z80 they still don't know" means. Not that the AI cannot write Z80 assembly -- it can. Not that it gets the instructions wrong -- it usually does not. But that it does not understand the *context* in which each instruction choice matters. It does not think in budgets. It does not see that `inc l` is safe here because of the alignment constraint three abstraction layers up. It does not know that 2 T-states per iteration, multiplied by thousands of iterations, is the difference between fitting in one frame and needing two.

### What the AI Gets Wrong, Specifically

We tested Claude Code on several Z80 tasks from the demoscene domain. Here are representative results.

**Task: Write a DOWN_HL routine.** DOWN_HL moves the screen pointer in HL one pixel row down in the Spectrum's interleaved video memory. It is the most commonly used graphics primitive on the platform. Introspec wrote a definitive article about it (Hype, 2020).

The AI's first attempt:

```z80
down_hl:
    inc  h              ; 4T   move down one pixel row
    ld   a, h           ; 4T
    and  7              ; 7T
    ret  nz             ; 11T/5T  still within the character row
    ld   a, l           ; 4T
    add  a, 32          ; 7T   next character row
    ld   l, a           ; 4T
    ret  c              ; 11T/5T  if carry, crossed into next third
    ld   a, h           ; 4T
    sub  8              ; 7T
    ld   h, a           ; 4T
    ret                 ; 10T
```

This is correct for the first two thirds of the screen but fails at the third-third boundary. The screen memory is divided into three 2,048-byte thirds, and the transition from the second to the third third requires adding $08 to H, not subtracting. The AI generated code that handles the common case correctly but gets the boundary case wrong.

Introspec's article presents a version by RST7 using a dual-counter approach that handles all boundaries correctly in 2,343 T-states for a full-screen traverse. The naive version -- the one most humans write on their first attempt, and the one the AI approximates -- costs 5,922 T-states. The gap between "works" and "works well" is a factor of 2.5x.

**Task: Generate an unrolled screen fill.** Asked to generate an unrolled PUSH-based screen fill (the technique from Chapter 3), the AI produced correct code -- PUSH pairs writing two bytes at a time, DI/EI to protect the stack pointer manipulation. But it did not think to arrange the data in reverse order (PUSH writes high byte first, to lower addresses), which means the fill pattern was backwards. A human who has written PUSH fills before accounts for this automatically.

**Task: Optimise a given inner loop.** Given a working inner loop and asked to make it faster, the AI suggested standard optimisations: unrolling, lookup tables, register substitution. These are valid. But it did not find the non-obvious optimisation -- the one where you rearrange memory layout to enable `inc l` instead of `inc hl`, or use the carry flag from an addition as a branch condition instead of a separate comparison. The non-obvious optimisation requires understanding the full context of the routine, and the AI's context window, while large, does not capture the *spatial* and *temporal* structure of a Z80 program the way a human expert's mental model does.

### Where Introspec Is Right

The deepest Z80 optimisations are not about knowing instructions. They are about understanding the interplay between memory layout, register allocation, instruction encoding, timing constraints, and visual output -- simultaneously. This interplay is what Introspec means by "evolving a computation scheme" (Chapter 1). A computation scheme is a holistic design where every decision affects every other decision. The AI operates on code locally. The expert operates on the scheme globally.

The AI does not know Z80 in the sense that Introspec knows Z80. It has memorised the instruction set but not internalised the machine.

### Where Introspec Is Not Quite Right

But "Z80 they still don't know" implies the AI is useless for Z80 work, and that is not true either.

The AI is not trying to replace Introspec. It is trying to help Alice -- a programmer who understands Z80 well enough to evaluate AI output but does not have decades of inner-loop optimisation experience. For Alice, the AI's output is a starting point that is better than a blank screen. She does not need the AI to find the `inc l` trick. She needs it to generate the first 80% of the routine so she can spend her time on the last 20%.

The demoscene has always been about the last 20%. The AI does not change that. It changes how fast you get through the first 80%.

---

## 23.7 The "Not Eager" Demo: AI in Practice

The companion demo for this book -- "Not Eager" -- is a deliberate experiment: build a ZX Spectrum demo with AI assistance and document what happens.

The name is a nod to Introspec's *Eager* (2015, 1st place at 3BM openair). We are attempting to implement effects inspired by Eager -- the attribute tunnel with 4-fold symmetry, the chaos zoomer, 4-phase colour animation -- plus Dark's midpoint 3D engine from *Spectrum Expert* #02. If it works, it proves AI can assist with real demoscene work. If it fails, the failure is itself instructive.

### What Has Worked

**Effect prototyping.** Claude Code generates working first drafts of effect routines fast enough to try ideas that would otherwise not be worth the typing time. "What if the tunnel used 8-fold symmetry instead of 4-fold?" is a question you can answer in 15 minutes with AI-generated code instead of 2 hours of manual coding. Most prototypes get discarded. But the ones that survive move quickly to refinement.

**Tooling.** The build system, the asset pipeline, the Makefile rules, the test harnesses -- all the infrastructure around the demo -- was AI-generated and works reliably. This is unsexy but important. A professional build pipeline means faster iteration, and faster iteration means more experiments per evening session.

**Code review.** Feeding the AI a routine and asking "what is wrong with this?" or "how can this be faster?" is surprisingly effective. The AI does not find the deep optimisations, but it catches obvious mistakes -- off-by-one errors, forgotten DI/EI around stack manipulation, wrong output port numbers. Having a tireless code reviewer that responds in seconds is genuinely useful.

### What Has Not Worked

**The 3D engine.** Dark's midpoint method (Chapter 5) involves a virtual processor with a custom instruction set for vertex interpolation. The AI understood the concept but generated a broken implementation. The vertex program encoding -- where 2-bit opcodes and 6-bit point numbers are packed into single bytes -- was incorrectly parsed. The averaging instruction computed `(A+B)/2` using `ADD A,B : SRA A`, which is correct for unsigned values but overflows for signed coordinates. This took three debugging sessions to identify and fix, longer than writing it from scratch would have taken.

**Music integration.** Synchronising AY music playback with frame-level effect changes requires an interrupt-driven architecture where the music player runs in the IM2 handler and the main loop communicates with it through shared state. The AI generated a music player that worked in isolation but conflicted with the effect code's use of the shadow registers (EXX, EX AF,AF'). The conflict was subtle -- both the music player and the effect routine used the shadow BC register for different purposes, and the EXX in the interrupt handler swapped in stale values. This is the kind of bug that requires understanding the full system architecture, not just individual routines.

### The Honest Assessment

"Not Eager" is not finished as of this writing. The effects work individually. Integration is ongoing. Whether the final demo is good enough to submit to a competition is an open question.

But the process has been instructive. AI assistance made the project *feasible* for a solo developer working evenings and weekends. Without AI, the prototyping phase alone would have consumed months. With AI, it consumed weeks. Whether the final product matches what a dedicated human team could produce in the same calendar time is a different question -- and probably the wrong one to ask. The right question is: does AI assistance let more people make demos? The answer, provisionally, is yes.

---

## 23.8 The Feedback Loop in Practice

Let us trace a complete iteration cycle on a real problem from the "Not Eager" project.

### The Problem

We need a routine that copies one quarter of the attribute screen to the other three quarters, implementing 4-fold symmetry for the tunnel effect. The source quadrant is the top-left 16x12 attributes. The destinations are top-right (mirrored horizontally), bottom-left (mirrored vertically), and bottom-right (mirrored both).

### Iteration 1: The Prompt

"Write a Z80 routine that copies the top-left 16x12 quadrant of the ZX Spectrum attribute area ($5800) to the other three quadrants with appropriate mirroring. Top-right should be horizontally mirrored. Bottom-left should be vertically mirrored. Bottom-right should be both."

### Iteration 1: The AI Output

Claude Code generates 47 lines of assembly. The horizontal mirror is implemented by reading the source left-to-right and writing the destination right-to-left. The vertical mirror reads rows top-to-bottom and writes bottom-to-top. The code uses HL for source, DE for destination, and BC for a loop counter.

### Iteration 1: Assembly

The code assembles with `mza` on the first attempt. No syntax errors.

### Iteration 1: Testing

Load into the emulator. Run. The top-left quadrant is correct (it was already there). The top-right quadrant is mirrored -- but offset by one column. The bottom-left quadrant is correct. The bottom-right has garbage.

### Iteration 2: Diagnosis

Set a breakpoint at the horizontal mirror loop. Step through. The destination pointer for the top-right quadrant starts at $5800 + 31 (column 31) instead of $5800 + 16 + 15 = $5800 + 31 -- wait, that is correct. Step further. The problem: after copying one row, the source pointer advances by 16 (correct) but the destination pointer subtracts 16 from a position that has already been decremented 16 times (the mirror loop). The destination pointer is off by the width of the quadrant after the first row.

Paste the register values into Claude Code: "After row 0, DE = $580F (correct destination end of row 0 top-right). After row 1, DE = $581F (should be $582F). The destination is off by 16 after each row."

### Iteration 2: The Fix

Claude Code identifies the issue: after the mirror loop decrements DE 16 times, it needs to advance DE by 32 + 16 = 48 bytes to reach the start of the next row's mirror position. The original code advanced by 32 (one row width) -- forgetting that the mirror loop had already moved DE backwards by 16.

### Iteration 3: Retesting

Fix applied. Reassemble. The top-right quadrant now mirrors correctly. The bottom-right is still wrong -- it turns out the combined horizontal+vertical mirror has a similar pointer arithmetic error. One more iteration fixes it.

### Total Time

Three iterations, approximately 25 minutes from first prompt to working code. Manual coding estimate: 40-60 minutes for an experienced Z80 programmer who has done attribute mirroring before. For someone doing it for the first time: 2-3 hours.

The AI saved time, but most of the time saved was on the initial generation. The debugging -- finding the pointer arithmetic error, understanding why it was wrong, communicating the fix -- took the same amount of time whether the code was AI-generated or human-written.

---

## 23.9 Building Your Own AI-Assisted Workflow

If you want to use AI assistance for Z80 development, here is a practical setup.

### The Toolchain

1. **Editor:** VS Code with Z80 Macro Assembler extension and Z80 Assembly Meter.
2. **AI assistant:** Claude Code (or any code-capable LLM with a chat interface that can see your project files).
3. **Assembler:** `mza` (from MinZ) or sjasmplus. The AI knows both dialects.
4. **Emulator + debugger:** DeZog connected to ZEsarUX or the internal simulator.
5. **Build system:** A Makefile that assembles, links, and optionally launches the emulator.

### The Workflow

**Start with the AI.** Describe what you want in plain English. Be specific about the target machine (Spectrum 128K, Pentagon timing), the memory addresses, the register conventions, and the assembler syntax. The more context you provide, the better the first attempt.

**Assemble immediately.** Do not read the AI's code carefully. Assemble it. If it fails, paste the error. Reading AI code is slower than testing it.

**Test with border colours.** Wrap the AI-generated routine in a border colour timing harness (Chapter 1). Run it. Does the border stripe appear? Is it the right width? If yes, the routine runs and terminates. If no, there is a crash or infinite loop.

**Debug with DeZog.** When the output is wrong, do not guess. Set a breakpoint. Step through. Find the first instruction where the register state diverges from what you expect. Report that divergence to the AI.

**Iterate until correct.** Usually 2-5 iterations for a routine of moderate complexity. If it takes more than 5, consider writing the routine yourself -- the AI is failing to understand the problem.

**Optimise yourself.** Once the routine is correct, profile it. Count cycles. Find the hot loop. Apply the optimisations from Chapters 1-14 -- the unrolling, the table lookups, the register tricks that the AI does not find. This is where your Z80 knowledge matters most.

### Prompt Engineering for Z80

Some prompts work better than others.

**Good prompt:** "Write a Z80 routine for ZX Spectrum 128K (Pentagon timing) that copies 16 bytes from the address in HL to screen memory at (DE), with the screen address following the Spectrum interleave pattern. After each byte, advance DE to the next pixel row using the standard down_hl method. Use mza syntax. Include cycle counts."

**Bad prompt:** "Write a sprite routine for the Spectrum."

The good prompt specifies the machine, the assembler, the memory addresses, the expected behaviour, and what the output should include. The bad prompt leaves everything ambiguous, and the AI will make assumptions -- usually wrong ones.

**Prompt for optimisation:** "Here is a working routine [paste code]. It currently takes approximately 3,200 T-states per call. I need it under 2,400. What can be improved? Do not change the interface (HL = source, DE = destination, B = height). Pentagon timing."

Giving the AI a concrete performance target and a constraint on the interface forces it to look for real optimisations instead of restructuring the code in ways that change the calling convention.

---

## 23.10 The Broader Picture

This chapter has been about a specific tool -- AI code generation -- applied to a specific domain -- Z80 assembly. But the pattern is general.

Every tool that raises the abstraction level on constrained hardware follows the same trajectory. BASIC was the first: accessible, slow, memory-hungry. HiSoft C was the next step: faster, more structured, but limited (no floats). Then came assembler-level tools -- macro assemblers, cross-development on PCs, build systems, debuggers -- that kept the abstraction level at machine code but removed friction from the development process.

AI-assisted development is the latest step. It does not change the abstraction level of the output -- you are still writing Z80 assembly, and the Z80 still executes the same instructions at the same speeds. What it changes is the speed of the input -- how fast you can go from idea to working (if unoptimised) code.

This is not a small change. The ZX Spectrum demoscene has been constrained not just by the machine's hardware but by the *human cost* of programming it. Writing Z80 assembly is slow. Debugging it is slower. Learning the tricks -- the memory layouts, the register conventions, the flag exploits -- takes years. AI assistance lowers the entry barrier without lowering the ceiling. The experts will still write better inner loops than any AI. But more people will get to the point where they can appreciate *why* those inner loops are better.

And that is good for the scene. The demoscene thrives on participation. More people writing Z80 code, even with AI assistance, means more people watching demos, attending compos, reading articles on Hype, and contributing to the community's collective knowledge. If this book helps that happen -- if the combination of documented techniques and AI-assisted tooling brings even a handful of new makers into the ZX Spectrum scene -- then the compromise is worth making.

Introspec is right that AI does not know Z80. Not the way he knows it. But AI does not need to know Z80 the way Introspec does. It needs to know it well enough to help a newcomer get started, make fewer mistakes, and reach the point where they can learn the deep tricks from Introspec's articles themselves.

That is the honest assessment. Neither magic nor useless. A tool. Like HiSoft C, but different.

---

## Summary

- **AI-assisted Z80 development follows a feedback loop:** prompt, generate, assemble, test, debug, iterate. The AI generates the first draft fast; the human evaluates and refines. The loop typically takes 2-5 iterations for a routine of moderate complexity.

- **AI is reliable for** instruction encoding, cycle counts, boilerplate, dialect translation, and code explanation. It is moderately reliable for standard algorithms and simple self-modifying code. It is unreliable for novel optimisation, contended memory timing, creative effect design, and deep flag-based tricks.

- **DeZog integration** closes the gap between AI output and correct code. The human reads register states from the debugger and feeds divergences back to the AI, which reasons about the mismatch. Programmatic AI-debugger integration does not yet exist but is the obvious next step.

- **The MinZ case study** shows the pattern clearly: AI assistance made it possible for one developer to build a complete language toolchain (compiler, assembler, emulator, standard library) in 18 months. The routine work -- instruction encoding, test generation, standard library functions -- was AI-generated. The creative work -- TSMC, zero-cost abstractions, grammar design -- was human.

- **Introspec's scepticism is valid:** AI does not understand Z80 the way an expert does. It does not think in budgets, does not see cross-cutting constraints, does not find non-obvious optimisations. The deepest demoscene work remains beyond AI's reach.

- **The historical parallel holds:** HiSoft C was "10-15x faster than BASIC" but had no floats. AI-assisted Z80 development is dramatically faster for scaffolding and iteration but cannot match human experts for inner loop optimisation. Higher-level tools on constrained hardware have always been a compromise. The question is not "good or bad?" but "good *for what*?"

- **The practical workflow** combines Claude Code for code generation, DeZog for debugging, `mza` or sjasmplus for assembly, and a Makefile for build automation. Start with AI, assemble immediately, test with border colours, debug with DeZog, optimise yourself.

- **The broader effect** is positive: AI assistance lowers the entry barrier to Z80 development without lowering the ceiling. More people can start; the experts are still needed for the deep work. This is good for the demoscene.

---

## Try It Yourself

1. **The boilerplate test.** Ask your AI assistant to generate a ZX Spectrum 128K boot template: ORG at $8000, disable interrupts, set up IM1, HALT loop with border colour timing harness. Assemble and run it. How many iterations did it take?

2. **The optimisation test.** Write (or AI-generate) a working attribute fill loop. Measure its cost with border colour timing. Then ask the AI to make it faster. Measure again. Now optimise it yourself using techniques from Chapters 1-3. Compare all three versions: original, AI-optimised, human-optimised.

3. **The DOWN_HL challenge.** Ask the AI to write a DOWN_HL routine. Test it on all 192 pixel rows. Does it handle the third-boundary transitions correctly? Compare to Introspec's analysis (Hype, 2020). This is a litmus test for AI Z80 competence.

4. **The MinZ experiment.** Install the MinZ toolchain (`mza`, `mze`). Write a simple program in MinZ -- a screen fill, a keyboard reader, a bouncing pixel. Compare the generated assembly to what you would write by hand. Where is the MinZ output good? Where is it wasteful?

5. **Build something.** Pick an effect from an earlier chapter. Use AI assistance to write the first draft. Iterate until it works. Profile it. Optimise the inner loop by hand. Document each step. You have just experienced the workflow this entire chapter describes.

---

*This is the final technical chapter. What follows are the appendices -- reference tables, setup guides, and the instruction reference you will reach for every time you write Z80 assembly.*

> **Sources:** HiSoft C review (Spectrum Expert #02, 1998); Introspec "Technical Analysis of Illusion" (Hype, 2017); Introspec "DOWN_HL" (Hype, 2020); Introspec "GO WEST Parts 1-2" (Hype, 2015)
