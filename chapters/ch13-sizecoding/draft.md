# Chapter 13: The Craft of Size-Coding

> "It was like playing puzzle-like games -- constant reshuffling of code to find shorter encodings."
> -- UriS, on writing NHBF (2025)

There is a category of demoscene competition where the constraint is not time but *space*. Your entire program -- the code that draws the screen, produces the sound, handles the frame loop, holds whatever data it needs -- must fit in 256 bytes. Or 512. Or 1K, or 4K, or 8K. Not a byte more. The file is measured, and if it is 257 bytes, it is disqualified.

These are **size-coding** competitions, and they produce some of the most remarkable work on the ZX Spectrum scene. A 256-byte intro that fills the screen with animated patterns and plays a recognisable melody is not just a technical exercise -- it is a form of compression so extreme it borders on magic. The audience sees an effect that should require kilobytes. The file is a quarter of a kilobyte. The gap between expectation and reality is the art.

This chapter is about the mindset, the techniques, and the specific tricks that make size-coding possible. We will dissect a real 256-byte intro (UriS's NHBF, 2025), explore a BASIC-era trick that packs complex screen output into a handful of bytes (diver4d's LPRINT technique), survey what becomes possible at 512 bytes, and then walk through the practical process of shrinking an effect from 400 bytes down to 256.

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

The limits are absolute. The file submitted to the competition organiser is measured in bytes, and there is no negotiation. On the ZX Spectrum, the file is typically a raw binary or a .tap loader whose payload matches the limit.

What makes size-coding fascinating is that it requires a completely different way of thinking about code. In normal programming -- even in the cycle-counted world of demoscene effects -- you optimise for *speed*. You unroll loops, duplicate data, generate code at runtime, all trading space for time. Size-coding inverts this. You trade everything for space. Speed does not matter. Readability does not matter. Convention does not matter. The only question is: can you make it one byte shorter?

UriS, who wrote the 256-byte intro NHBF (No Heart Beats Forever) for Chaos Constructions 2025, described the process as "playing puzzle-like games." That description is exact. Size-coding is a puzzle where the pieces are Z80 instructions, the board is 256 bytes of RAM, and the goal is to produce the most impressive result with the fewest pieces. Every instruction choice, every register allocation, every data layout is a move in this puzzle, and the best solutions involve moves that solve multiple problems simultaneously.

The mindset shift from normal coding:

- **Every byte is precious.** A 3-byte instruction where a 2-byte instruction would suffice is not "slightly wasteful" -- it is 0.4% of your entire program. At 256 bytes, saving one byte is like saving 250 bytes in a 64K program.

- **Code and data overlap.** The same bytes that execute as instructions can also serve as data -- lookup values, string characters, screen coordinates. The Z80 does not know the difference. Only the program counter's path through memory distinguishes code from data.

- **Instruction choice is driven by size, not speed.** `RST $10` costs 1 byte and calls the ROM character output routine. `CALL $0010` does the same thing but costs 3 bytes. In a normal demo you would never notice. In 256 bytes, those 2 bytes are the difference between having sound or not.

- **Initial state is free data.** After a standard Spectrum boot, registers have known values. Memory at certain addresses contains known data. A size-coder exploits every bit of this free state.

- **Self-modifying code is not a trick -- it is a necessity.** When you cannot afford a separate variable, you modify an instruction's operand in place. When you need a subroutine to do two slightly different things, you patch its opcode.

---

## 13.2 Anatomy of a 256-Byte Intro: NHBF

**NHBF** (No Heart Beats Forever) was created by UriS for Chaos Constructions 2025. It was inspired by RED REDUX, shown at Multimatograf 2025, which demonstrated that a 256-byte intro on the Spectrum could be more than a flickering pattern -- it could have character.

NHBF produces two things: a visual display (text with screen effects) and music (looped square-wave power chords with random pentatonic melody notes). All in 256 bytes. Let us examine how.

### The Music

At 256 bytes, you cannot include a tracker player. You cannot include note tables. You can barely include a melody. What you *can* do is drive the AY chip directly with minimal code.

NHBF's sound consists of two elements:

1. **Power chords** -- a looped sequence of square-wave tones that cycle through a short chord progression. The tone periods are hardcoded as immediate values in the AY register-write instructions themselves. The same bytes that form the `LD A, n` operand also *are* the musical note.

2. **Random pentatonic notes** -- the melody channel uses a simple pseudo-random generator to pick from a pentatonic scale. A pentatonic scale (five notes per octave) sounds pleasant regardless of which notes land next to each other -- there are no dissonant intervals. This means you get a melody that sounds intentional, even though it is random.

The pseudo-random generator is typically a single instruction sequence like `LD A,R` (read the refresh register, which cycles through values 0-127 continuously) followed by an AND to mask it into the desired range. Two bytes for a "random" number.

### The Visuals

The visual component displays text with screen effects. On the Spectrum, printing text to the screen can be done through ROM routines -- `RST $10` outputs the character in A to the current print position, and is the smallest way to get pixels on screen (1 byte per call, plus the character data is in the ROM, not in your code).

But even printing a text string takes bytes: each character costs at least 1 byte for the character code plus 1 byte for the `RST $10` call. For a 20-character string, that is 40 bytes -- 15% of your budget just for text output. Size-coders look for ways to compress this further.

### The Puzzle: Finding Overlaps

UriS describes the core of the process as constant reshuffling. You write a first version that works. It is 300 bytes. You stare at it. You notice that the loop counter for the visual effect ends up with the same value you need as the AY register number for the next sound update. So you remove the `LD A, 7` that sets the register number -- the loop already left A with the value 7. You save 2 bytes.

Then you notice that the screen-clearing routine uses LDIR, which decrements BC to zero. If you arrange the code so the next section needs BC = 0, you save the `LD BC, 0` that would otherwise initialise it. Another 3 bytes.

This is what UriS means by "puzzle-like games." Every instruction produces side effects -- register values, flag states, memory contents -- and the art is arranging instructions so that one routine's side effects are another routine's inputs.

### Art-Top's Discovery

During the development of NHBF, Art-Top (a fellow coder reviewing the work) noticed something remarkable: the register values left over from the screen-clearing routine happened to match the exact length needed for the text string. This was not planned. UriS had written the screen clear, then the text output, and the two happened to share a register state that eliminated a separate length counter.

This kind of serendipitous overlap is the heart of 256-byte coding. You cannot plan for it -- you can only create the conditions where it can happen, by constantly rearranging code and watching for accidental alignments. When you find one, it feels like discovering that two jigsaw pieces from different puzzles fit together perfectly.

### Key Techniques at 256 Bytes

From NHBF and other 256-byte intros, a set of standard techniques emerges:

**1. Use initial register and memory state.**

After a standard Spectrum reset (or tape load), many registers contain known values. On most loaders:

- A = 0 or the last byte loaded
- BC often contains the length of the last loaded block
- HL often points to the end of loaded data
- The system variables area ($5C00-$5CB5) contains known values
- Screen memory ($4000-$5AFF) is clear if you just did a CLS

Every known value you can use instead of loading explicitly saves 1-3 bytes.

**2. Overlap code and data.**

The same byte can be an opcode when executed and data when read. For example, the byte $3E is the opcode for `LD A, n` -- but it is also the value 62, which could be an ASCII character, a screen coordinate, or an AY register value. If your program executes this byte as an instruction and also reads it as data from a different path through the code, you have made one byte do two jobs.

A common pattern: the immediate operand of a `LD A, n` instruction doubles as a data byte that another part of the program reads with `LD A, (addr)`. The instruction takes 2 bytes ($3E, n). If you can arrange for another routine to reference address (instruction_address + 1), it reads n as data. Zero extra bytes for the data storage.

**3. Choose instructions for size, not speed.**

| Large encoding | Small encoding | Savings |
|---------------|----------------|---------|
| `CALL $0010` (3 bytes) | `RST $10` (1 byte) | 2 bytes |
| `JP label` (3 bytes) | `JR label` (2 bytes) | 1 byte |
| `LD A, 0` (2 bytes) | `XOR A` (1 byte) | 1 byte |
| `LD HL, nn : LD (HL), A` (4 bytes) | `LD (nn), A` (3 bytes) | 1 byte |
| `CP 0` (2 bytes) | `OR A` / `AND A` (1 byte) | 1 byte |
| `LD B, 0 : LD C, n` (4 bytes) | `LD BC, n` (3 bytes) | 1 byte |

The RST instructions deserve special attention. The Z80 has eight restart vectors at addresses $00, $08, $10, $18, $20, $28, $30, and $38. `RST n` is a one-byte CALL to address n. On the Spectrum, several of these point to useful ROM routines:

- `RST $10` -- print character in A (the BASIC RST 16 routine)
- `RST $18` -- collect a character
- `RST $28` -- calculator entry point

In a normal demo, you would never use `RST $10` for screen output -- it is slow, it goes through the ROM print engine, it is not cycle-efficient. But at 256 bytes, saving 2 bytes per CALL is everything.

**4. Self-modifying code to reuse sequences.**

If you need a subroutine to operate on two different addresses, hardcode the first address and patch it for the second call:

```z80
    ld   hl, addr1
    call routine
    ld   (routine + 1), hl     ; patch the LD inside routine
    ; now routine operates on addr2
    ; (assuming HL ends up pointing to addr2 after the first call)
```

This is cheaper than passing parameters on the stack or through additional registers, provided the flow allows it.

**5. Mathematical relationships between constants.**

If your music needs tone period 200 and your visual effect needs a loop count of 200, use the same value. Better still: if one value is twice another, use `ADD A, A` or `SLA A` (1 byte) instead of loading the second value (2 bytes). Size-coders hunt obsessively for mathematical relationships between the constants their program needs.

---

## 13.3 The LPRINT Trick

In 2015, diver4d published an article on Hype titled "Secrets of LPRINT" (Sekrety LPRINT), documenting a technique that turns a single BASIC statement into a complex screen effect. The trick is older than the demoscene itself -- it first appeared in pirated cassette software loaders in the 1980s -- but diver4d traced its history and explained the mechanics for modern coders.

### How It Works

The ZX Spectrum BASIC has an `LPRINT` statement that sends text to a printer. The system variable at address 23681 ($5C81) controls where the BASIC output routines direct their data. Normally, it points to the printer buffer. But if you modify this variable to point to screen memory, `LPRINT` writes its output directly to the screen.

Here is the smallest possible version:

```basic
10 POKE 23681,64: LPRINT "HELLO"
```

That POKE redirects the printer channel to screen memory starting at $4000. When LPRINT executes, it sends its character data to the screen instead of the printer.

### The Transposition Effect

What makes LPRINT visually interesting is not just the redirection -- it is the *way* data appears on screen. The Spectrum's screen memory is not laid out in simple linear order (as Chapter 2 explained). The address mapping interleaves character rows in a non-obvious pattern. When LPRINT writes data sequentially to "printer" addresses, the bytes land in screen memory according to the printer driver's sequential logic, but they *display* according to the screen's interleaved layout.

The result: data appears to fill the screen in a "transposed" manner, cycling through 8 states as it progresses through the screen thirds. Each character row within a character line gets filled before moving to the next character line. The visual effect is a rapid cascade of data that appears to build up the screen in horizontal bands, then shift and recombine.

With different character data -- graphical characters, UDGs (User Defined Graphics), or carefully chosen ASCII sequences -- this transposition effect produces striking visual patterns. The LPRINT statement itself handles all the complexity of screen addressing, character rendering, and cursor advancement. Your BASIC program provides only the data.

### Historical Origin

diver4d traced the LPRINT trick back to pirated cassette software loaders from the early 1980s Spectrum era. When pirates duplicated commercial software onto cassettes, they often added custom loading screens -- animated displays that entertained the user during the multi-minute tape loading process. These loaders were written in BASIC (or minimal machine code) and needed to produce visual effects in very few bytes. The LPRINT trick was ideal: a single BASIC statement could fill the screen with animated garbage that looked deliberately artistic.

The effect fell out of use as the scene moved to machine code. But in 2011, JtN and 4D (diver4d's group) released **BBB**, a demo that deliberately returned to the LPRINT trick as an artistic statement. BBB used BASIC's LPRINT to create visual patterns that were then manipulated with further POKE statements and loops. The demo proved that the old pirate-loader trick could be elevated to art when used with intention.

### Why It Matters for Size-Coding

The LPRINT trick is relevant to size-coding because it achieves complex screen output for almost zero bytes of your own code. The ROM's print engine does all the heavy lifting -- character lookup, pixel rendering, cursor advancement, screen addressing. Your code provides only:

1. The POKE to redirect output (a few bytes)
2. The data to print (as few or as many characters as you want)
3. The RST $10 or LPRINT call to trigger the output

In a BASIC size-coding entry, a single LPRINT loop can produce a full-screen animated pattern in under 50 bytes of BASIC tokens. In machine code, a loop around `RST $10` with a data pointer achieves the same. Either way, you leverage the Spectrum ROM as a "free" screen-output engine -- thousands of bytes of code that do not count against your size limit because they are already in the machine.

---

## 13.4 512-Byte Intros: Room to Breathe

Doubling the size limit from 256 to 512 bytes changes what is possible far more than you might expect. It is not twice as much -- it is qualitatively different.

At 256 bytes, you are fighting for every instruction. The effect is limited to whatever a single tight loop can produce, and sound (if present) is minimal. At 512 bytes, you can have a proper effect *and* proper sound, or two different effects with a transition.

### Common 512-Byte Patterns

**Plasma via sine table sums.** A plasma effect computes a colour for each screen cell by summing sine waves at different frequencies and phases. The sine table is the expensive part -- a full 256-byte table would consume half your budget. Solutions: use a 64-entry quarter-wave table and mirror it (saves 192 bytes), or generate the table at startup using the parabolic approximation from Chapter 4 (costs ~20 bytes of code instead of 256 bytes of data).

**Tunnel via angle/distance lookup.** An attribute tunnel (like the one in Eager, Chapter 9) normally uses large precalculated tables. At 512 bytes, you compute angle and distance on the fly using simple approximations. The visual quality is lower, but the tunnel is recognisably a tunnel.

**Fire via cellular automaton.** The classic fire effect: each pixel's value is the average of its neighbours below, minus a small decay. This requires only a few instructions per pixel and produces a convincing fire animation. At 512 bytes, you can implement the fire algorithm *and* set up a palette via attributes *and* add a simple beeper sound effect.

### Self-Modifying Tricks at 512 Bytes

With 512 bytes, self-modification becomes a structural tool rather than a last-resort optimisation.

**Change your own jump addresses.** A single rendering loop that cycles through multiple effects:

```z80
effect_jump:
    jr   effect_1           ; this JR offset gets patched
    ; ...
effect_1:
    ; render effect 1
    ; at end:
    ld   a, effect_2 - effect_jump - 2
    ld   (effect_jump + 1), a    ; patch the JR to go to effect 2
    jr   main_loop
```

The `jr` is 2 bytes. Patching its offset is 4 bytes. A full `JP` dispatch table with state variable would cost 8+ bytes. At 512 bytes, those 4-6 bytes buy you another few instructions of actual effect code.

**Patch your own operands.** Instead of maintaining a frame counter in a variable (3 bytes for `LD (counter), A`), store the counter *as the immediate operand* of an instruction that already needs a value:

```z80
frame_ld:
    ld   a, 0               ; this 0 is the frame counter
    inc  a
    ld   (frame_ld + 1), a  ; update the counter in place
```

The frame counter lives inside the instruction stream. No separate variable, no extra memory access.

### The ORG Trick

A subtle but powerful technique: choose your program's ORG address so that the address bytes themselves are useful data.

If your effect needs the value $40 as a constant (the high byte of screen memory), ORG your code at an address where $40 appears naturally as part of an address reference. For example, if a `CALL $4000` appears in your code, the bytes $CD $00 $40 contain the value $40 at offset +2. Another instruction can reference that byte as data.

More aggressively: place your code at address $4000 itself. Now every `JR` or `DJNZ` that references a label near the start of your code generates offset bytes that happen to be small numbers -- useful as loop counters, colour values, or AY register data.

This is the deepest level of the size-coding puzzle: choosing where to place your code so that the *encoding of the code itself* provides data you need elsewhere.

---

## 13.5 Practical: Writing a 256-Byte Intro Step by Step

Let us build a 256-byte intro from scratch. We will start with a working effect-plus-sound that comes in at roughly 400 bytes, then optimise it down to 256 through the techniques described in this chapter.

### Step 1: The Initial Version (~400 bytes)

Our effect: a simple attribute plasma. We fill the 768 bytes of attribute memory with values computed from sine sums, offset by a frame counter. For sound, we play a simple melody on AY channel A.

```z80
    ORG  $8000

    ; --- Sine table (64 bytes, quarter-wave) ---
sine_table:
    DB   0,  6, 12, 18, 25, 31, 37, 43
    DB  49, 54, 60, 65, 71, 76, 81, 85
    DB  90, 94, 98,102,106,109,112,115
    DB  117,120,122,124,125,126,127,127

    ; --- Note table (8 entries, 16 bytes) ---
notes:
    DW   424, 378, 337, 283    ; C4, D4, E4, G4 (pentatonic)
    DW   252, 212, 189, 169    ; A4, C5, D5, E5

start:
    halt                       ; wait for frame

    ; --- Sound: play next note ---
    ld   a, (frame_counter)
    and  7                     ; 8 notes in rotation
    add  a, a                  ; *2 for word index
    ld   e, a
    ld   d, 0
    ld   hl, notes
    add  hl, de
    ld   e, (hl)
    inc  hl
    ld   d, (hl)               ; DE = tone period

    ld   bc, $FFFD
    xor  a                     ; register 0: tone A low
    out  (c), a
    ld   b, $BF
    out  (c), e                ; write low byte
    ld   b, $FF
    ld   a, 1                  ; register 1: tone A high
    out  (c), a
    ld   b, $BF
    out  (c), d                ; write high byte
    ld   b, $FF
    ld   a, 8                  ; register 8: volume A
    out  (c), a
    ld   b, $BF
    ld   a, 15                 ; max volume
    out  (c), a

    ; --- Mixer: enable tone A ---
    ld   b, $FF
    ld   a, 7
    out  (c), a
    ld   b, $BF
    ld   a, %00111110          ; tone A on, rest off
    out  (c), a

    ; --- Visual: attribute plasma ---
    ld   hl, $5800             ; attribute memory
    ld   a, (frame_counter)
    ld   d, a                  ; D = frame offset

    ld   b, 24                 ; 24 rows
.row_loop:
    ld   c, 32                 ; 32 columns
.col_loop:
    ld   a, d                  ; frame offset
    add  a, b                  ; + row
    add  a, c                  ; + column
    and  $1F                   ; mask to table range
    push hl
    ld   hl, sine_table
    ld   e, a
    ld   d, 0
    add  hl, de
    ld   a, (hl)               ; sine value
    pop  hl
    srl  a                     ; scale to 0-63
    srl  a
    and  %00111111             ; 6-bit attribute
    ld   (hl), a
    inc  hl
    dec  c
    jr   nz, .col_loop
    djnz .row_loop

    ; --- Increment frame counter ---
    ld   hl, frame_counter
    inc  (hl)

    jr   start

frame_counter:
    DB   0
```

This is clear, readable, and about 200 instructions -- far too large. Let us count: the sine table is 32 bytes (we used a 32-entry quarter-wave), the note table is 16 bytes, and the code is roughly 150 bytes. Total: around 200 bytes of data + 200 bytes of code. We need to reach 256 total.

### Step 2: Replace CALL with RST Where Possible

Our first version does not use CALL, but the principle applies generally. Any call to a ROM address that matches an RST vector saves 2 bytes. If we were printing text with `CALL $0010`, switching to `RST $10` saves 2 bytes per invocation.

In our case, we can replace the AY register-writing sequence with a tight subroutine and use a single RST to call it -- but only if we are willing to place our code so that a subroutine lands on an RST vector. For a 256-byte intro loaded at the right address, this is sometimes possible.

More practically: we can write a small AY-write helper and CALL it, or we can inline the writes but share the port setup.

**Savings: replace the verbose AY setup with a loop.**

```z80
; Write multiple AY registers from a data block
; HL points to pairs: register, value, register, value, ...
; B = count
ay_batch:
    ld   c, $FD
.ay_loop:
    ld   b, $FF
    outi                       ; OUT (C), (HL); HL++; B--
    ld   b, $BF
    outi                       ; OUT (C), (HL); HL++; B--
    jr   nz, .ay_loop          ; B counts down
    ret
```

Wait -- `OUTI` decrements B and we need B for the port high byte. This will not work directly. Instead, the classic size-coding approach:

```z80
; Minimal AY write: register in A, value in E
ay_write:
    ld   bc, $FFFD
    out  (c), a
    ld   b, $BF
    out  (c), e
    ret
```

This is 8 bytes. Each call to it costs 3 bytes (CALL) + 2 bytes (loading A and E). The six AY writes in our original code become 6 x 5 = 30 bytes + 8 bytes for the routine = 38 bytes. The original inline version was about 60 bytes. Savings: ~22 bytes.

### Step 3: Overlap Initialised Data with Code

The 32-byte sine table sits at the start of our program. Can it do double duty?

Look at the sine values: 0, 6, 12, 18, 25, 31, 37, 43... These are just bytes. If they happen to decode as Z80 instructions, the CPU could *execute* them before reaching the real code -- producing some side effects that we might exploit.

- $00 = `NOP` -- harmless
- $06 = `LD B, n` -- loads the next byte into B
- $0C = `INC C`
- $12 = `LD (DE), A`
- $19 = `ADD HL, DE`
- $1F = `RRA`
- $25 = `DEC H`
- $2B = `DEC HL`

This is mostly harmless. If we ORG the sine table at the entry point, the CPU will execute these bytes as (mostly nonsensical) instructions, then fall through to our real code. The register values will be scrambled, but if we reload the registers we need before using them, no harm done.

The trick is: we got 32 bytes of sine data for free. They occupy the same space as "code" that the CPU harmlessly stumbles through on its first pass. After the first frame, the main loop jumps back to the real entry point, never executing the sine table again. But the data stays there for lookup.

**Savings:** We already had the 32 bytes, but now they are at the top of the binary, and we do not need a separate label or alignment -- the program starts at the sine table.

### Step 4: Exploit Register State from Initialisation

After the standard Spectrum LOAD, several registers have known values. On most tape loaders:

- HL points near the end of the loaded data
- BC = 0 or a small value
- A = the verify byte

But more usefully: after our *own* screen clear, we know exactly what registers contain. If we clear attributes with `LDIR`, then after the clear:

- BC = 0
- HL = $5B00 (one past end of attributes)
- DE = wherever DE pointed

If the next operation needs BC = 0 or HL near $5B00, we can skip the initialisation.

In our plasma loop, after writing all 768 attributes, HL = $5B00. If we then need to read from the system variables area ($5C00-$5CB5), HL is close. A single `LD H, $5C` (2 bytes) puts us in range, instead of a full `LD HL, $5Cnn` (3 bytes). One byte saved.

Art-Top's discovery in NHBF was exactly this kind of observation: the register values left over from the screen clearing routine happened to match the length needed for the text string. It was not planned. It was noticed. And noticing is the skill.

### Step 5: Choose Smaller Instruction Encodings

Go through the entire program and question every instruction:

- `LD A, 0` (2 bytes) becomes `XOR A` (1 byte). We already did this, but check everywhere.
- `LD HL, nn` followed by `LD A, (HL)` (4 bytes) becomes `LD A, (nn)` (3 bytes) if we do not need HL afterwards.
- `INC HL` (1 byte) is fine, but if L will not overflow, `INC L` (1 byte, same size but 2 T-states faster) is equivalent and may enable further optimisations if we later need H unchanged.
- `JP label` (3 bytes) becomes `JR label` (2 bytes) if the target is within -128..+127 bytes. At 256 bytes total, everything is in range. **Every JP in a 256-byte intro should be a JR.**
- `CALL sub : ... : RET` can sometimes be replaced by falling through to the subroutine directly, eliminating the CALL and the RET -- saving 4 bytes.

Each substitution saves 1-2 bytes. Across a 400-byte program, finding 15-20 such substitutions cuts 20-30 bytes. Combined with data/code overlap and register-state reuse, you approach 256.

### The Final Push

The last 10-20 bytes are the hardest. At this point, every obvious optimisation has been applied. What remains is structural rearrangement:

- **Reorder the code** so that fall-through eliminates a JR. Moving a subroutine to just before its caller can save 2 bytes (the JR to it disappears).
- **Merge loops.** If the sound update and the visual update both iterate over something, combine them into one loop.
- **Use the stack for temporaries.** `PUSH AF` (1 byte) saves A for later, where `LD (var), A` would cost 3 bytes.
- **Embed data in the instruction stream.** If you need the byte $07 as data and also need a `RLCA` instruction (opcode $07) somewhere, can you arrange for one to serve as the other?

This is where UriS's "puzzle-like games" description is most apt. You stare at the hex dump. You try moving the sound routine before the visual routine. You try storing the frame counter in the IY register instead of memory. You try replacing the sine table with a runtime generator. Each attempt reshuffles the bytes. Sometimes you find a configuration where everything lines up. Sometimes you do not, and you try another path.

The reward for this process is disproportionate to its apparent significance. A 256-byte intro is trivially small. But the satisfaction of fitting a coherent audiovisual experience into 256 bytes -- of solving the puzzle -- is real and specific and unlike any other feeling in programming.

---

## 13.6 Design Principles for Size-Coding

Having walked through the specifics, here are the general principles that guide experienced size-coders:

**1. Choose your effect for its byte efficiency, not its visual complexity.**

A plasma (sine sums) is byte-efficient because one formula drives the entire screen. A sprite animation is byte-expensive because you need per-frame data. Effects that compute everything from a formula and a frame counter are natural fits for size-coding. Effects that require stored assets are not.

**2. Write the first version without size concern. Then measure.**

Do not try to size-optimise while writing the initial version. Get it working. Then measure. You need to know which parts are large before you know where to cut.

**3. Keep a hex dump visible.**

Size-coders work with the assembled binary open alongside the source. Every change, reassemble and check the byte count. Many assemblers can emit a listing file that shows the assembled bytes next to each source line. This is essential.

**4. Try radical restructuring before micro-optimisation.**

Saving 1 byte by changing `LD A,0` to `XOR A` is good. Saving 30 bytes by eliminating the note table entirely and generating notes from a formula is better. Always look for structural savings first.

**5. Exploit the platform.**

The Spectrum ROM is 16K of free code. Every routine in it -- character printing, tape loading, calculator, BEEP -- is available at the cost of a 1-byte RST or 3-byte CALL. Size-coders on other platforms (PC, Amiga) do not have this luxury. On the Spectrum, the ROM is an asset.

The system variables area contains known values. The character set in ROM provides pixel data. The ULA's behaviour is predictable. Use all of it.

---

## 13.7 Size-Coding as Art

There is a moment in size-coding -- and UriS's making-of captures it perfectly -- when you stop thinking about the technique and start feeling the aesthetics. The program is 260 bytes. You need to cut 4. You could remove a visual feature. You could simplify the sound. Or you could find an encoding where the same bytes serve both purposes.

When you find that encoding, it is not just a technical solution. It is *elegant*. The code is more beautiful for being smaller. The bytes have more meaning because each one serves multiple purposes. The program is denser, more interconnected, more like a poem where every word carries weight.

This is why size-coding competitions persist, even though the practical utility of a 256-byte program is essentially zero. The craft is the point. The constraint is the canvas. And the results -- tiny binaries that produce music and motion from a space smaller than this paragraph -- are genuine art.

diver4d's LPRINT article makes a similar point from the opposite direction. The LPRINT trick is not efficient. It is not fast. It produces visual noise that barely qualifies as an "effect." But when JtN and 4D used it in BBB (2011), framing the technique with artistic intent, the result was a demo that people remembered. The constraint (BASIC, a printer redirect hack, no machine code) became the medium. The limitations became the style.

Size-coding teaches you things that improve all your coding. The discipline of questioning every byte sharpens your awareness of instruction encodings. The habit of looking for overlaps between code and data transfers to any optimisation work. The practice of exploiting initial state and side effects makes you a better systems programmer. And the experience of solving the puzzle -- finding the arrangement where everything fits -- is a skill that applies far beyond 256 bytes.

---

## Summary

- **Size-coding** competitions require complete programs in 256, 512, 1K, 4K, or 8K bytes -- strict limits that demand a fundamentally different approach to programming.
- **NHBF** (UriS, 2025) demonstrates the 256-byte mindset: every byte does double duty, register states from one routine feed into the next, and instruction choice is driven purely by encoding size.
- **The LPRINT trick** (diver4d, 2015) redirects BASIC's printer output to screen memory by modifying address 23681, producing complex visual patterns in a handful of bytes -- a technique that originated in pirated cassette loaders and was later elevated to demo art.
- **At 512 bytes**, self-modifying code becomes structural (patching jump targets, embedding counters in operands), and effects like plasma, tunnel, and fire become feasible alongside basic sound.
- **The optimisation process** moves from structural changes (eliminating tables, merging loops, choosing byte-efficient effects) to micro-level encoding choices (RST for CALL, JR for JP, XOR A for LD A,0) to serendipitous discoveries (register states aligning with data needs).
- **The ORG trick** -- choosing your program's load address so that address bytes double as useful data -- represents the deepest level of the size-coding puzzle.

---

## Try It Yourself

1. **Start large, shrink small.** Write an attribute plasma that fills the screen from a sine formula and a frame counter. Get it working at any size. Then set a target of 512 bytes and optimise until you reach it. Track every byte you save and how you saved it.

2. **Explore the LPRINT trick.** In BASIC, try `POKE 23681,64 : FOR i=1 TO 500 : LPRINT CHR$(RND*96+32); : NEXT i`. Watch the screen fill with transposed character data. Experiment with different character ranges and see how the visual pattern changes.

3. **Map your register state.** Write a small program and, at each point in the code, annotate what every register contains. Look for places where one routine's output is another routine's needed input. This is the fundamental skill of size-coding: seeing the register state as a shared resource.

4. **Study the RST vectors.** Disassemble the Spectrum ROM at addresses $0000, $0008, $0010, $0018, $0020, $0028, $0030, and $0038. For each one, determine what it does and what registers it expects. These are your "free" subroutines for size-coding.

5. **The 256-byte challenge.** Take the practical from this chapter and push it to 256 bytes. You will need to make hard choices about what to keep and what to cut. That is the point.

---

*Next: Chapter 14 -- Compression: More Data in Less Space. We move from programs that fit in 256 bytes to the problem of fitting kilobytes of data into kilobytes of storage, with Introspec's comprehensive benchmark of 10 compressors as our guide.*

> **Sources:** UriS "NHBF Making-of" (Hype, 2025); diver4d "LPRINT Secrets" (Hype, 2015)
