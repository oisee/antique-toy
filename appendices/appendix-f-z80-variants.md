# Appendix F: Z80 Variants --- Extended Instruction Sets

> *"The same instruction set, a completely different machine."*
> -- Chapter 22

The Zilog Z80 did not stay frozen in 1976. Over five decades, the original design has been cloned, extended, reimagined, and --- in the case of the ZX Spectrum Next --- rebuilt by the very community that spent thirty years cursing its limitations. This appendix surveys the major Z80 variants and their instruction set extensions, with a focus on what matters to demoscene and game programmers. The standard Z80 instruction set is covered in Appendix A; the eZ80 gets a deep dive in Appendix E. This appendix is the big picture --- how the variants relate, what each one adds, and why.

---

## 1. The Z80 Family Tree

The Z80 was designed by Federico Faggin and Masatoshi Shima at Zilog in 1976 as a software-compatible successor to the Intel 8080. It became the most widely used 8-bit CPU in history, powering everything from CP/M business machines to arcade cabinets to an entire generation of home computers. The instruction set was frozen at launch and never officially extended by Zilog --- until the eZ80, two decades later.

But others did extend it. Here is the family at a glance:

| Variant | Year | Notable Machine | Key Addition |
|---------|------|----------------|--------------|
| Z80 (Zilog) | 1976 | ZX Spectrum, MSX, Amstrad CPC | The original. 158 documented instructions. |
| KR1858VM1 (Soviet) | ~1986 | Pentagon, Scorpion | Exact clone. No instruction changes. |
| NSC800 (National Semi) | 1980 | Various embedded | CMOS Z80 with 8085-style bus. No new instructions. |
| R800 (ASCII Corp) | 1990 | MSX turboR | Z80-compatible, radically different pipeline. MULUB, MULUW. |
| eZ80 (Zilog) | 2001 | Agon Light 2 | 24-bit addressing, MLT, LEA, PEA, ADL mode. |
| Z80N (Next team) | 2017 | ZX Spectrum Next | Demoscene wish list: MUL, MIRROR, LDIRX, PIXELDN, barrel shifts. |

The Z80 and its clones share an identical instruction set. The R800, eZ80, and Z80N each added instructions to solve specific problems --- but very different problems, reflecting very different design goals.

---

## 2. Z80N --- The Demoscener's Wish List

The Z80N is the CPU in the ZX Spectrum Next. It was designed by Victor Trucco, Fabio Belavenuto, and the Next team --- people who had spent decades writing Z80 code and knew exactly where it hurt. Every new instruction addresses a specific, documented pain point from thirty years of Spectrum programming. The Z80N runs at 28 MHz (8x the original Spectrum clock) and adds roughly 40 new instructions, all encoded in previously-unused `$ED xx` opcode space.

The best way to understand the Z80N extensions is by the problem each instruction solves.

### Screen Navigation (the DOWN_HL problem)

On a standard Spectrum, calculating a screen address from pixel coordinates takes 50-60 T-states and a page of code (see `pixel_addr` in Appendix A). Moving one pixel row down requires the infamous `DOWN_HL` routine --- a conditional maze of INC, AND, ADD, and SUB that handles character boundaries and third boundaries. The Z80N replaces all of this with single instructions.

| Instruction | Bytes | T | What it replaces |
|-------------|-------|---|------------------|
| `PIXELDN` | 2 | 4 | The 10+ instruction `DOWN_HL` sequence (check third boundary, handle wrap, adjust H and L). Moves HL one pixel row down in screen memory. |
| `PIXELAD` | 2 | 4 | Full screen address calculation from (D,E) coordinates. Replaces the `pixel_addr` routine (~55T, 15+ instructions). |
| `SETAE` | 2 | 4 | Sets the appropriate pixel bit in A based on the low 3 bits of E (the x-coordinate). Replaces a lookup table or shift sequence. |

With these three instructions, the entire pixel-plotting sequence that consumed 70+ T-states and 20+ bytes on the original Z80 becomes:

```z80
; Z80N: plot pixel at (D=y, E=x) — 12T total
    pixelad             ; 4T  HL = screen address from (D,E)
    setae               ; 4T  A = pixel bit mask from E
    or   (hl)           ; 4T  set pixel (non-destructive)
    ; ... ld (hl), a to write
```

### Sprite Rendering (the masked blit problem)

The single most CPU-intensive operation in any Spectrum game or demo is the masked sprite blit: copying a rectangular block of sprite data to screen memory while skipping transparent pixels. On the standard Z80, this requires an inner loop of LD/AND/OR/LD per byte, typically 30-40 T-states per pixel byte. The Z80N adds block-copy instructions with built-in transparency.

| Instruction | Bytes | T | What it replaces |
|-------------|-------|---|------------------|
| `LDIX` | 2 | 5 | `LDI` but skips the copy if `(HL) == A`. One-instruction transparent copy: load A with the transparent colour, point HL at source, DE at destination, and each byte is copied only if it is not the transparent value. |
| `LDDX` | 2 | 5 | Same as LDIX but decrementing (like `LDD`). |
| `LDIRX` | 2 | 5/byte | Repeating LDIX. Hardware masked sprite blit in a single instruction. Copies BC bytes from (HL) to (DE), skipping any byte equal to A. |
| `LDDRX` | 2 | 5/byte | Repeating LDDX. |
| `LDPIRX` | 2 | 5/byte | Pattern fill with transparency from an 8-byte aligned source. Reads from `(HL & $FFF8) + (E & 7)`, copies to (DE) if not equal to A, increments DE, decrements BC. Hardware tiled background renderer. |

`LDIRX` alone replaces the most heavily optimised inner loop in decades of Spectrum game code. `LDPIRX` is even more exotic --- it treats the source as a repeating 8-byte pattern, effectively giving you a hardware tile renderer with transparency. Combined with the Next's Layer 2 and tilemap hardware, these instructions make the Spectrum Next a qualitatively different platform for sprite-heavy games.

### Arithmetic (the multiply problem)

The Z80 has no multiply instruction. Every multiply in Spectrum code is a shift-and-add loop costing 150-250 T-states (see `mulu112` in Appendix A). The Z80N fixes this with a single instruction.

| Instruction | Bytes | T | What it replaces |
|-------------|-------|---|------------------|
| `MUL D,E` | 2 | 8 | 8x8 unsigned multiply, result in DE. Replaces the ~200T shift-and-add loop. |

Eight T-states. At 28 MHz, that is 286 nanoseconds. The same operation on a standard 3.5 MHz Spectrum takes roughly 57 microseconds --- a 200:1 improvement when you factor in both the faster clock and the faster instruction. Rotation matrices, coordinate transforms, texture mapping, perspective projection --- everything that needs multiply is fundamentally cheaper on the Z80N.

### Bit Manipulation

| Instruction | Bytes | T | What it replaces |
|-------------|-------|---|------------------|
| `MIRROR` | 2 | 4 | Reverses all 8 bits of A. Horizontal sprite flip without a 256-byte lookup table. On the standard Z80, bit-reversing A requires either an unrolled 18-instruction sequence (`LD B,A : XOR A` then 8× `RR B : RLA`, ~104T) or a 256-byte lookup table (11T but costs 256 bytes of RAM). |
| `SWAPNIB` | 2 | 4 | Swaps the high and low nibbles of A. Replaces `RLCA : RLCA : RLCA : RLCA` (16T, 4 bytes). |
| `TEST nn` | 3 | 7 | `AND A, nn` without storing the result --- sets flags but preserves A. Like a CP for bitwise AND. Similar to the eZ80's TST instruction. |

`MIRROR` is particularly valuable for games. Without it, every horizontally flipped sprite either needs a pre-flipped copy in memory (doubling sprite data) or a 256-byte bit-reversal lookup table plus per-byte table lookups. With it, you can flip sprites on the fly at 4T per byte.

### Barrel Shifts (the multi-bit shift problem)

On the standard Z80, shifting a 16-bit value by more than one bit requires a loop: `SLA E : RL D` per bit, costing 16T per bit position. Shifting DE left by 5 bits costs 80T. The Z80N adds barrel shift instructions that shift DE by an arbitrary number of positions (specified in B) in constant time.

| Instruction | Bytes | T | What it replaces |
|-------------|-------|---|------------------|
| `BSLA DE,B` | 2 | 4 | Shift DE left by B bits. Replaces `B * (SLA E : RL D)`. |
| `BSRA DE,B` | 2 | 4 | Arithmetic shift DE right by B bits (sign-extending). |
| `BSRL DE,B` | 2 | 4 | Logical shift DE right by B bits (zero-filling). |
| `BSRF DE,B` | 2 | 4 | Shift DE right by B bits, filling with bit 15. |
| `BRLC DE,B` | 2 | 4 | Rotate DE left by B bits (circular). |

These are enormously useful in fixed-point arithmetic, pixel sub-positioning, and any code that converts between integer scales. A common operation like "multiply by 5 and shift right 3" that would take ~50T on a standard Z80 becomes trivial.

### Convenience Instructions

| Instruction | Bytes | T | What it replaces |
|-------------|-------|---|------------------|
| `PUSH nn` | 4 | 11 | Push a 16-bit immediate value onto the stack. No register needed. Saves the `LD rr, nn : PUSH rr` pattern (21T, 4 bytes on the original Z80 --- same byte count, but 10T faster and does not clobber a register pair). |
| `ADD HL,A` | 2 | 4 | Add A to HL. Replaces the 5-instruction, 23T sequence: `ADD A,L : LD L,A : ADC A,H : SUB L : LD H,A` (or the equivalent using a spare register). |
| `ADD DE,A` | 2 | 4 | Same as ADD HL,A but for DE. |
| `ADD BC,A` | 2 | 4 | Same for BC. |
| `NEXTREG reg,val` | 4 | 12 | Direct write to a Next hardware register. No I/O port setup needed. Replaces `LD BC,$243B : OUT (C),reg : LD BC,$253B : OUT (C),val` --- four instructions, 8 bytes, ~48T. |
| `NEXTREG reg,A` | 3 | 8 | Write A to a Next hardware register. |
| `OUTINB` | 2 | 5 | `OUT (C),(HL) : INC HL` combined. Useful for streaming data to I/O ports. |

### The Big Picture

The Z80N is, in a real sense, thirty years of demoscene frustration cast in silicon. Each instruction is a scar from a specific, well-documented pain:

- `PIXELDN` exists because every Spectrum programmer has written `DOWN_HL` at least once, debugged the third-boundary case at least twice, and wished they never had to again.
- `MIRROR` exists because every game programmer has wasted 256 bytes on a bit-reversal table for horizontal sprite flips.
- `LDIRX` exists because the masked blit inner loop is where most Spectrum games spend most of their CPU time.
- `MUL D,E` exists because the shift-and-add multiply loop is the single most re-implemented subroutine in Z80 history.

Unlike the eZ80 (designed by Zilog for embedded markets) or the R800 (designed by ASCII Corporation for the MSX platform), the Z80N was designed by the community, for the community. The instruction set reads like a demoscene wish list because it *is* a demoscene wish list --- the Next team solicited input from active Spectrum coders and prioritised the instructions that would remove the most pain from the most common operations.

---

## 3. eZ80 --- The Enterprise Extension

The eZ80 is Zilog's official successor to the Z80, designed for embedded systems that need more than 64 KB of address space. It is a strict superset of the Z80 --- every Z80 opcode is valid and behaves identically. The extensions are architectural rather than computational:

- **24-bit addressing and ADL mode.** Registers can be 16-bit or 24-bit depending on the operating mode. ADL mode (Address Data Long) gives you 24-bit registers and a flat 16 MB address space. Z80-compatible mode behaves exactly like a standard Z80 with MBASE providing the missing upper 8 address bits.

- **MLT rr --- 8x8 unsigned multiply.** `MLT BC` multiplies B by C and stores the 16-bit result in BC. Similarly for `MLT DE` (D * E -> DE) and `MLT HL` (H * L -> HL). This is more flexible than the Z80N's `MUL D,E`, which only operates on DE. The eZ80 gives you three independent multiply units. At 6 T-states on the eZ80 (running at 18.432 MHz on the Agon), this is blazing fast.

- **LEA and PEA.** Load Effective Address and Push Effective Address --- indexed address computation instructions. `LEA rr, IX+d` loads the computed address into a register pair without accessing memory. `PEA IX+d` pushes the computed address onto the stack. Useful for parameter passing and pointer arithmetic.

- **TST (test) and TSTIO.** Non-destructive AND test, similar to the Z80N's `TEST nn`. `TSTIO` tests an I/O port value against a mask.

- **IN0/OUT0.** I/O access to the internal peripheral space (addresses $00--$FF).

The eZ80 was designed for industrial control, networking equipment, and printers --- not retrocomputing. But it landed in the Agon Light 2, and suddenly a CPU designed for embedded markets became a retro gaming platform. The full eZ80 reference is in Appendix E; the porting story is in Chapter 22.

---

## 4. R800 --- The MSX turboR Speedster

The R800 is the oddest member of the family. Developed by ASCII Corporation for the MSX turboR (1990, Panasonic FS-A1GT/FS-A1ST), it is Z80-compatible in the sense that it executes the full Z80 instruction set --- but its internal architecture is radically different.

**Pipeline, not microcode.** The original Z80 is microcoded: each instruction is broken into machine cycles (M-cycles) of 3-6 clock ticks each, and complex instructions take many M-cycles. The R800 uses a pipelined design where most instructions complete in 1-2 clock cycles. At 7.16 MHz, this gives it an effective throughput roughly 5-8x faster than a 3.5 MHz Z80 for typical code.

**Hardware multiply.** The R800 adds two multiply instructions:

| Instruction | Operands | Result | Cycles | Notes |
|-------------|----------|--------|--------|-------|
| `MULUB A,r` | A * r (8-bit unsigned) | HL = 16-bit product | 14 | r = B, C, D, E |
| `MULUW HL,rr` | HL * rr (16-bit unsigned) | DE:HL = 32-bit product | 36 | rr = BC, SP |

A 16x16 multiply with a 32-bit result in 36 cycles is remarkable for an 8-bit-era CPU. On a standard Z80, a 16x16 multiply takes 600-1000 T-states depending on implementation. The R800 makes 3D transformations, DSP-style filtering, and other multiply-heavy algorithms genuinely practical.

**The pipeline trap.** Code optimised for Z80 timing can behave unexpectedly on the R800. The Z80 optimisation trick of unrolling `LDIR` into individual `LDI` instructions (saving 5T per byte) actually runs *slower* on the R800, because the R800's pipeline handles the `LDIR` repeat prefix efficiently. Similarly, self-modifying code --- a staple of Z80 demoscene technique --- can stall the R800's pipeline when a write hits a prefetched instruction. Code that is fast on the Z80 is not necessarily fast on the R800, and vice versa.

**Demoscene presence.** The MSX turboR has a tiny but dedicated demoscene. The hardware multiply makes real-time 3D feasible, and the raw speed allows effects that would be impossible at Z80 clock rates. But the platform's rarity (only sold in Japan, small production run) means the R800 remains a footnote in the broader Z80 story.

---

## 5. Soviet Clones --- Behind the Iron Curtain

The Soviet Union produced several Z80 clones to circumvent Western export restrictions. These chips enabled an entire ecosystem of ZX Spectrum-compatible computers that flourished from the late 1980s through the 1990s --- and whose demoscene community remains active today.

**KR1858VM1** (КР1858ВМ1). The primary Soviet Z80 clone. Pin-compatible, instruction-compatible, bug-compatible. Manufactured at the Angstrem factory in Zelenograd using reverse-engineered masks. The KR1858VM1 powered the Pentagon 128 and Scorpion ZS-256 --- the two most important Soviet Spectrum clones, and the platforms where much of the modern Russian/CIS ZX demoscene still targets its work.

**T34VM1** (Т34ВМ1). A later CMOS version of the same design, with lower power consumption and slightly different electrical characteristics. Functionally identical to the KR1858VM1.

Neither chip adds any new instructions. They are exact functional replicas of the Zilog Z80. The differences are electrical: different fabrication processes, different timing margins on setup and hold, slightly different behaviour on undocumented opcodes and flag bits. For software purposes, code that runs on a Zilog Z80 runs identically on a KR1858VM1.

The historical significance is immense. Without these clones, the ZX Spectrum ecosystem would not have spread across the Soviet Union and its successor states. The Pentagon 128, built around the KR1858VM1, became the *de facto* standard Spectrum platform in Russia, and its uncontended timing (no ULA contention delays) is the reference timing used throughout this book.

---

## 6. Comparison Table

| Feature | Z80 | Z80N | eZ80 | R800 |
|---------|-----|------|------|------|
| Clock (typical) | 3.5 MHz | 28 MHz | 18.4 MHz | 7.16 MHz |
| Address space | 64 KB | 64 KB + Next regs | 16 MB | 64 KB |
| Hardware multiply | No | `MUL D,E` (8T) | `MLT rr` (6T) | `MULUB` (14T), `MULUW` (36T) |
| 16x16 multiply | No | No | No | `MULUW` (36T, 32-bit result) |
| Barrel shift | No | `BSLA/BSRA/BSRL/BSRF/BRLC DE,B` (4T) | No | No |
| Block copy with mask | No | `LDIRX`, `LDPIRX` | No | No |
| Screen address helpers | No | `PIXELDN`, `PIXELAD`, `SETAE` | No | No |
| Bit reverse | No | `MIRROR` (4T) | No | No |
| Nibble swap | No | `SWAPNIB` (4T) | No | No |
| 24-bit mode | No | No | ADL mode | No |
| Push immediate | No | `PUSH nn` (11T) | No | No |
| Add 8-bit to 16-bit | No | `ADD HL/DE/BC, A` (4T) | No | No |
| Test (non-destructive AND) | No | `TEST nn` (7T) | `TST` (7T) | No |
| Hardware register I/O | No | `NEXTREG` (8-12T) | `IN0`/`OUT0` | No |
| Designed for | General computing | ZX Spectrum Next | Embedded systems | MSX turboR |

### Effective Multiply Performance

Since all four variants run at different clock speeds, the raw T-state counts do not tell the full story. Here is the wall-clock time for an 8x8 unsigned multiply on each platform:

| Variant | Clock | Instruction | Cycles | Wall-clock time |
|---------|-------|-------------|--------|-----------------|
| Z80 | 3.5 MHz | Shift-and-add loop | ~200 | ~57 us |
| Z80N | 28 MHz | `MUL D,E` | 8 | ~0.29 us |
| eZ80 | 18.4 MHz | `MLT DE` | 6 | ~0.33 us |
| R800 | 7.16 MHz | `MULUB A,r` | 14 | ~1.96 us |

The Z80N and eZ80 are effectively tied for multiply performance. The R800 is 30x faster than a standard Z80 but 6-7x slower than the Z80N/eZ80. All three are fast enough to make real-time 3D practical.

---

## 7. What This Means for the Book

All assembly code in this book targets the **standard Z80 instruction set**. Every example in every chapter will assemble and run on a stock ZX Spectrum 48K, a Pentagon 128, a Scorpion, an MSX, or any other machine with a Zilog Z80 or compatible clone. No extensions required.

This is a deliberate choice. The optimisation principles --- T-state budgets, register allocation, loop structure, self-modifying code, unrolled loops, stack tricks --- are universal. Code that is fast on a 3.5 MHz Z80 is fast on a 28 MHz Z80N. Code that fits in 48 KB fits in 16 MB. The constraints of the original Z80 teach you to think in a way that transfers to every variant in the family.

That said, if you have a ZX Spectrum Next, the Z80N extensions are too good to ignore. Chapter 22 covers porting strategies including Z80N-specific optimisations. If you have an Agon Light 2, Appendix E is your eZ80 reference and Chapter 22 walks through a complete Spectrum-to-Agon port. The barrel shifts, hardware multiply, and masked blit instructions do not change *how* you think about optimisation --- they change *where the bottleneck moves* once the classic pain points are eliminated.

The fundamentals do not change. The instructions get better.

---

## See Also

- **Appendix A: Z80 Instruction Quick Reference** --- complete standard Z80 instruction table with T-states, byte counts, and flag effects. The baseline that all variants share.
- **Appendix E: eZ80 Quick Reference** --- full eZ80 reference including mode system, MLT, LEA/PEA, and Agon Light 2 specifics.
- **Chapter 22: Porting --- Agon Light 2** --- practical porting walkthrough covering both eZ80 and Z80N extensions in context.

---

> **Sources:** Zilog Z80 CPU User Manual (UM0080); Zilog eZ80 CPU User Manual (UM0077); ZX Spectrum Next User Manual, Issue 2; ZX Spectrum Next Extended Instruction Set Documentation (wiki.specnext.dev); Victor Trucco, Fabio Belavenuto et al., Z80N instruction set design notes; ASCII Corporation R800 Technical Reference (1990); Sean Young, "The Undocumented Z80 Documented" (2005); Introspec, "Once more about DOWN_HL" (Hype, 2020); Dark / X-Trade, "Programming Algorithms" (Spectrum Expert #01, 1997)
