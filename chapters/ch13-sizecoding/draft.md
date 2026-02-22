# Chapter 13: The Craft of Size-Coding

> "It was like playing puzzle-like games -- constant reshuffling of code to find shorter encodings."
> -- UriS, on writing NHBF (2025)

There is a category of demoscene competition where the constraint is not time but *space*. Your entire program -- the code that draws the screen, produces the sound, handles the frame loop, holds whatever data it needs -- must fit in 256 bytes. Or 512. Or 1K, or 4K, or 8K. Not a byte more. The file is measured, and if it is 257 bytes, it is disqualified.

These are **size-coding** competitions, and they produce some of the most remarkable work on the ZX Spectrum scene. A 256-byte intro that fills the screen with animated patterns and plays a recognisable melody is a form of compression so extreme it borders on magic. The gap between what the audience sees and the file size that produces it -- that gap is the art.

This chapter is about the mindset, the techniques, and the specific tricks that make size-coding possible.

---

## 13.1 What is Size-Coding?

Demo competitions typically offer several size-limited categories:

| Category | Size limit | What fits |
|----------|-----------|-----------|
| 256 bytes | 256 | One tight effect, maybe simple sound |
| 512 bytes | 512 | An effect with basic music or two simple effects |
| 1K intro | 1,024 | Multiple effects, proper music, transitions |
| 4K intro | 4,096 | A short demo with several parts |
| 8K intro | 8,192 | A polished mini-demo |

The limits are absolute. The file is measured in bytes, and there is no negotiation.

What makes size-coding fascinating is that it inverts the normal optimisation hierarchy. In the cycle-counted world of demoscene effects, you optimise for *speed* -- unrolling loops, duplicating data, generating code, all trading space for time. Size-coding inverts this. Speed does not matter. Readability does not matter. The only question is: can you make it one byte shorter?

UriS, who wrote the 256-byte intro NHBF for Chaos Constructions 2025, described the process as "playing puzzle-like games." The description is exact. Size-coding is a puzzle where the pieces are Z80 instructions, the board is 256 bytes of RAM, and the best solutions involve moves that solve multiple problems simultaneously.

The mindset shift:

- **Every byte is precious.** A 3-byte instruction where a 2-byte one suffices is 0.4% of your entire program. At 256 bytes, one byte saved is like saving 250 bytes in a 64K program.

- **Code and data overlap.** The same bytes that execute as instructions can serve as data. The Z80 does not know the difference -- only the program counter's path through memory distinguishes code from data.

- **Instruction choice is driven by size, not speed.** `RST $10` costs 1 byte. `CALL $0010` does the same thing in 3 bytes. In a normal demo you would never notice. In 256 bytes, those 2 bytes are the difference between having sound or not.

- **Initial state is free data.** After boot, registers have known values. Memory at certain addresses contains known data. A size-coder exploits every bit of this free state.

- **Self-modifying code is not a trick -- it is a necessity.** When you cannot afford a separate variable, you modify an instruction's operand in place.

---

## 13.2 Anatomy of a 256-Byte Intro: NHBF

**NHBF** (No Heart Beats Forever) was created by UriS for Chaos Constructions 2025, inspired by RED REDUX from Multimatograf 2025. It produces text with screen effects and music -- looped square-wave power chords with random pentatonic melody notes -- all in 256 bytes.

### The Music

At 256 bytes, you cannot include a tracker player or note tables. NHBF drives the AY chip directly. The power chords are hardcoded as immediate values in the AY register-write instructions -- the same bytes that form the `LD A, n` operand *are* the musical note. The melody channel uses a pseudo-random generator (typically `LD A, R` -- read the refresh register -- followed by AND to mask the range) to pick from a pentatonic scale. A pentatonic scale sounds pleasant regardless of which notes land next to each other, so the melody sounds intentional even though it is random. Two bytes for a "random" number; five notes that never clash.

### The Visual

Printing text through the ROM -- `RST $10` outputs a character for 1 byte per call -- is the cheapest way to get pixels on screen. But even a 20-character string costs 40 bytes (character codes + RST calls). Size-coders look for ways to compress further: overlapping the string data with other code, or computing characters from a formula.

### The Puzzle: Finding Overlaps

UriS describes the core process as constant reshuffling. You write a first version at 300 bytes, then stare at it. You notice the loop counter for the visual effect ends up holding the value you need as the AY register number. Remove the `LD A, 7` that would set it -- the loop already left A with 7. Two bytes saved. The screen-clearing routine uses LDIR, which decrements BC to zero. Arrange the code so the next section needs BC = 0, and save the `LD BC, 0` -- another 3 bytes.

Every instruction produces side effects -- register values, flag states, memory contents -- and the art is arranging instructions so that one routine's side effects are another routine's inputs.

### Art-Top's Discovery

During development, Art-Top noticed something remarkable: the register values left over from the screen-clearing routine happened to match the exact length needed for the text string. Not planned. UriS had written the screen clear, then the text output, and the two happened to share a register state that eliminated a separate length counter.

This kind of serendipitous overlap is the heart of 256-byte coding. You cannot plan for it. You can only create conditions where it can happen, by constantly rearranging code and watching for accidental alignments. When you find one, it feels like discovering that two jigsaw pieces from different puzzles fit together perfectly.

### Key Techniques at 256 Bytes

**1. Use initial register and memory state.** After a standard tape load, registers hold known values: A often holds the last byte loaded, BC the block length, HL points near the end of loaded data. The system variables area ($5C00-$5CB5) contains known values. Screen memory is clear after CLS. Every known value you exploit instead of loading explicitly saves 1-3 bytes.

**2. Overlap code and data.** The byte $3E is the opcode for `LD A, n` and also the value 62 -- an ASCII character, a screen coordinate, or an AY register value. If your program executes this byte as an instruction *and* reads it as data from a different code path, you have made one byte do two jobs. Common pattern: the immediate operand of `LD A, n` doubles as data that another routine reads with `LD A, (addr)` pointing at instruction_address + 1.

**3. Choose instructions for size.**

| Large encoding | Small encoding | Savings |
|---------------|----------------|---------|
| `CALL $0010` (3 bytes) | `RST $10` (1 byte) | 2 bytes |
| `JP label` (3 bytes) | `JR label` (2 bytes) | 1 byte |
| `LD A, 0` (2 bytes) | `XOR A` (1 byte) | 1 byte |
| `CP 0` (2 bytes) | `OR A` (1 byte) | 1 byte |

The RST instructions are critical. `RST n` is a 1-byte CALL to one of eight addresses ($00, $08, $10, $18, $20, $28, $30, $38). On the Spectrum, `RST $10` calls the ROM character output, `RST $28` enters the calculator. In a normal demo these ROM routines are too slow. At 256 bytes, saving 2 bytes per CALL is everything.

**Every JP in a 256-byte intro should be a JR** -- the whole program fits within the -128..+127 range.

**4. Self-modifying code to reuse sequences.** Need a subroutine to operate on two different addresses? Hardcode the first and patch the operand for the second call. Cheaper than parameter passing.

**5. Mathematical relationships between constants.** If your music needs tone period 200 and your effect needs loop count 200, use the same register. If one value is twice another, use `ADD A, A` (1 byte) instead of loading a second constant (2 bytes).

---

## 13.3 The LPRINT Trick

In 2015, diver4d published "Secrets of LPRINT" on Hype, documenting a technique older than the demoscene itself -- one that first appeared in pirated cassette software loaders in the 1980s.

### How It Works

The system variable at address 23681 ($5C81) controls where BASIC's output routines direct data. Normally it points to the printer buffer. Modify it to point to screen memory, and LPRINT writes directly to the screen:

```basic
10 POKE 23681,64: LPRINT "HELLO"
```

That single POKE redirects the printer channel to $4000 -- the start of screen memory.

### The Transposition Effect

The visual result is not just text on screen -- it is *transposed* text. The Spectrum's screen memory is interleaved (Chapter 2), but the printer driver writes sequentially. Data lands in screen memory according to the driver's linear logic but *displays* according to the interleaved layout. The result cycles through 8 visual states as it progresses through the screen thirds -- a cascade of data that builds in horizontal bands, shifting and recombining.

With different character data -- graphical characters, UDGs, or carefully chosen ASCII sequences -- the transposition produces striking visual patterns. The LPRINT statement handles all screen addressing, character rendering, and cursor advancement. Your program provides only the data.

### From Pirate Loaders to Demo Art

diver4d traced the trick to pirated cassette loaders. Pirates adding custom loading screens needed visual effects in very few BASIC bytes -- LPRINT was ideal. The technique fell out of use as the scene moved to machine code.

But in 2011, JtN and 4D released **BBB**, a demo that deliberately returned to LPRINT as an artistic statement. The old pirate-loader trick, framed with intention, became demo art. The constraint -- BASIC, a printer redirect hack, no machine code -- became the medium.

### Why It Matters for Size-Coding

LPRINT achieves complex screen output for almost zero bytes of your own code. The ROM does the heavy lifting. Your contribution: a POKE to redirect output, data to print, and `RST $10` (or LPRINT) to trigger it. You leverage the Spectrum's 16K ROM as a "free" screen-output engine -- code that does not count against your size limit.

---

## 13.4 512-Byte Intros: Room to Breathe

Doubling from 256 to 512 bytes is not twice as much -- it is qualitatively different. At 256, you fight for every instruction and sound is minimal. At 512, you can have a proper effect *and* proper sound, or two effects with a transition.

### Common 512-Byte Patterns

**Plasma via sine table sums.** The sine table is the expensive part. A full 256-byte table consumes half your budget. Solutions: a 64-entry quarter-wave table mirrored at runtime (saves 192 bytes), or generate the table at startup using the parabolic approximation from Chapter 4 (~20 bytes of code instead of 256 bytes of data).

**Tunnel via angle/distance lookup.** At 512 bytes, you compute angle and distance on the fly using rough approximations. Lower visual quality than the Eager tunnel (Chapter 9), but recognisably a tunnel.

**Fire via cellular automaton.** Each cell averages its neighbours below, minus decay. A few instructions per pixel, convincing animation, and at 512 bytes you can add attributes for colour *and* a beeper sound.

### Self-Modifying Tricks

Self-modification becomes structural at 512 bytes. Embed the frame counter *inside* an instruction:

```z80
frame_ld:
    ld   a, 0               ; this 0 is the frame counter
    inc  a
    ld   (frame_ld + 1), a  ; update the counter in place
```

No separate variable. The counter lives in the instruction stream.

Patch jump offsets to switch between effects:

```z80
effect_jump:
    jr   effect_1               ; this offset gets patched
    ; ...
effect_1:
    ; render effect 1, then:
    ld   a, effect_2 - effect_jump - 2
    ld   (effect_jump + 1), a   ; next frame jumps to effect 2
```

### The ORG Trick

Choose your program's ORG address so that address bytes themselves are useful data. Place code at $4000 and every JR/DJNZ targeting labels near the start generates small offset bytes -- usable as loop counters, colour values, or AY register numbers. If your effect needs $40 (the high byte of screen memory) as a constant, place code at an address where $40 appears naturally in an address operand. The *encoding of the code itself* provides data you need elsewhere.

This is the deepest level of the size-coding puzzle.

---

## 13.5 Practical: Writing a 256-Byte Intro Step by Step

Start with a working attribute plasma (~400 bytes) and optimise it to 256.

### Step 1: The Unoptimised Version

A simple attribute plasma: fill 768 bytes of attribute memory with values from sine sums, offset by a frame counter. Sound: a cycling melody on AY channel A. This version is clean, readable, and roughly 400 bytes -- the sine table (32 bytes), note table (16 bytes), inline AY writes, and the plasma loop with table lookups.

### Step 2: Replace CALL with RST

Any call to a ROM address matching an RST vector saves 2 bytes per invocation. For AY output, replace the six verbose inline register writes (~60 bytes) with a small subroutine:

```z80
ay_write:                      ; register in A, value in E
    ld   bc, $FFFD
    out  (c), a
    ld   b, $BF
    out  (c), e
    ret                        ; 8 bytes total
```

Six calls (5 bytes each: load A + load E + CALL) = 30 + 8 = 38 bytes. Savings: ~22 bytes.

### Step 3: Overlap Data with Code

The 32-byte sine table at the entry point decodes as mostly harmless Z80 instructions ($00=NOP, $06=LD B,n, $0C=INC C...). Place it at the program start. On first execution, the CPU stumbles through these "instructions," scrambling some registers. The main loop then jumps past the table and never executes it again -- but the data remains for lookups. The table bytes serve double duty.

### Step 4: Exploit Register State

After the plasma loop writes 768 attributes, HL = $5B00 and BC = 0 (from any LDIR used in initialisation). If the next operation needs these values, skip the explicit loads. Art-Top's discovery in NHBF was exactly this: register values from screen clearing matched the text string length. Not planned. Noticed.

After each optimisation pass, annotate what every register contains at every point. Register state is a shared resource -- the fundamental currency of size-coding.

### Step 5: Smaller Encodings Everywhere

- `LD A, 0` -> `XOR A` (save 1 byte)
- `LD HL, nn` + `LD A, (HL)` -> `LD A, (nn)` (save 1 byte if HL not needed)
- `JP` -> `JR` everywhere (save 1 byte each)
- `CALL sub : ... : RET` -> fall through directly (save 4 bytes)
- `PUSH AF` for temporary saves vs `LD (var), A` (save 2 bytes)

### The Final Push

The last 10-20 bytes are the hardest. Structural rearrangement: reorder code so fall-throughs eliminate JR instructions. Merge the sound and visual loops. Embed data bytes in the instruction stream -- if you need $07 as data and also need an `RLCA` (opcode $07), arrange for one to serve as both.

You stare at the hex dump. You try moving the sound routine before the visual routine. You try replacing the sine table with a runtime generator. Each attempt reshuffles the bytes. Sometimes everything lines up.

The satisfaction of fitting a coherent audiovisual experience into 256 bytes -- of solving the puzzle -- is real and specific and unlike any other feeling in programming.

---

## 13.6 Size-Coding as Art

There is a moment in size-coding -- and UriS's making-of captures it perfectly -- when the program is 260 bytes and you need to cut 4. You could remove a visual feature. You could simplify the sound. Or you could find an encoding where the same bytes serve both purposes. When you find that encoding, it is not just a technical solution. It is *elegant*. The code is more beautiful for being smaller.

This is why size-coding competitions persist. The practical utility of a 256-byte program is zero. The craft is the point. The constraint is the canvas. The results -- tiny binaries that produce music and motion from a space smaller than this paragraph -- are genuine art.

diver4d's LPRINT article makes a similar point from the opposite direction. The LPRINT trick is not efficient. It produces visual noise that barely qualifies as an "effect." But when JtN and 4D used it in BBB, framing the technique with artistic intent, the result was a demo people remembered. The constraint became the medium. The limitations became the style.

Size-coding teaches you things that improve all your coding. The discipline of questioning every byte sharpens instruction-encoding awareness. The habit of looking for overlaps transfers to any optimisation work. The practice of exploiting initial state and side effects makes you a better systems programmer. And the puzzle-solving experience -- finding the arrangement where everything fits -- applies far beyond 256 bytes.

---

## Summary

- **Size-coding** competitions require complete programs in 256, 512, 1K, 4K, or 8K bytes -- strict limits that demand a fundamentally different approach to programming.
- **NHBF** (UriS, CC 2025) demonstrates the 256-byte mindset: every byte does double duty, register states from one routine feed into the next, instruction choice is driven purely by encoding size.
- **The LPRINT trick** (diver4d, 2015) redirects BASIC's printer output to screen memory via address 23681, producing complex visual patterns in a handful of bytes -- from pirated cassette loaders to demo art.
- **At 512 bytes**, self-modifying code becomes structural (patching jump targets, embedding counters in operands), and effects like plasma, tunnel, and fire become feasible alongside sound.
- **The optimisation process** moves from structural changes (eliminating tables, merging loops) to encoding choices (RST for CALL, JR for JP, XOR A for LD A,0) to serendipitous discoveries (register states aligning with data needs).
- **The ORG trick** -- choosing your load address so that address bytes double as useful data -- represents the deepest level of the puzzle.

---

## Try It Yourself

1. **Start large, shrink small.** Write an attribute plasma with a frame counter. Get it working at any size. Then optimise to 512 bytes, tracking every byte saved and how.

2. **Explore LPRINT.** In BASIC, try `POKE 23681,64 : FOR i=1 TO 500 : LPRINT CHR$(RND*96+32); : NEXT i`. Watch the transposed data fill the screen. Experiment with different character ranges.

3. **Map your register state.** Write a small program and annotate what every register contains at every point. Look for places where one routine's output matches another's needed input.

4. **Study the RST vectors.** Disassemble the Spectrum ROM at $0000, $0008, $0010, $0018, $0020, $0028, $0030, $0038. These are your "free" subroutines.

5. **The 256-byte challenge.** Push the practical from this chapter to 256 bytes. You will need to make hard choices about what to keep and what to cut. That is the point.

---

*Next: Chapter 14 -- Compression: More Data in Less Space. We move from programs that fit in 256 bytes to the problem of fitting kilobytes of data into kilobytes of storage, with Introspec's comprehensive benchmark of 10 compressors as our guide.*

> **Sources:** UriS "NHBF Making-of" (Hype, 2025); diver4d "LPRINT Secrets" (Hype, 2015)
