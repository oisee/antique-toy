# Appendix E: eZ80 Quick Reference

> *"The same instruction set, a completely different machine."*
> -- Chapter 22

This appendix is a reference card for Z80 programmers approaching the eZ80 for the first time. It covers the architectural differences, the mode system, the new instructions, and the Agon Light 2 specifics you need for porting. It is not an exhaustive eZ80 manual --- it is the subset that matters for the work in Chapter 22.

If you already know the Z80 (and if you have read this far, you do), the eZ80 will feel familiar. The registers have the same names, the instructions have the same mnemonics, the flags work the same way. But three things are different: addresses are 24 bits wide, registers can be 24 bits wide, and there is a mode system that controls which width is active. Everything else follows from that.

---

## 1. Architecture Overview

The eZ80 is Zilog's extended Z80, designed for embedded systems that need more than 64 KB of address space. It is a strict superset of the Z80 --- every Z80 opcode is valid on the eZ80, with identical behaviour. The extensions add 24-bit addressing, 24-bit register width, and a handful of new instructions.

| Feature | Z80 | eZ80 |
|---------|-----|------|
| Address width | 16-bit (64 KB) | 24-bit (16 MB) |
| Register width | 16-bit (HL, BC, DE, SP, IX, IY) | 16-bit or 24-bit (mode-dependent) |
| Stack frame per PUSH/CALL | 2 bytes | 2 bytes (Z80 mode) or 3 bytes (ADL mode) |
| Hardware multiply | None | MLT rr (8x8 unsigned) |
| Instruction prefixes | CB, DD, ED, FD | Same, plus mode suffix prefixes |
| MBASE register | N/A | Provides upper 8 bits of addresses in Z80 mode |
| New instructions | N/A | LEA, PEA, MLT, TST, TSTIO, SLP, IN0/OUT0, STMIX/RSMIX |

The key mental model: in **ADL mode** (Address Data Long), the eZ80 behaves like a Z80 with 24-bit registers and 24-bit addresses. In **Z80-compatible mode**, it behaves like a standard Z80, with 16-bit registers and the MBASE register providing the missing upper 8 address bits.

---

## 2. Mode System

The eZ80 has two operating modes that control register width and address generation. Understanding these modes is the single most important concept for any Z80 programmer approaching the eZ80.

### The Two Modes

**Z80-compatible mode.** Registers are 16 bits wide. Addresses are 16 bits, with MBASE providing the upper 8 bits. `LD HL,$4000` loads a 16-bit value. `PUSH HL` pushes 2 bytes. Code behaves exactly like a standard Z80.

**ADL mode (Address Data Long).** Registers are 24 bits wide. Addresses are 24 bits. `LD HL,$040000` loads a 24-bit value. `PUSH HL` pushes 3 bytes. This is the native mode of the eZ80 and the default on the Agon Light 2.

### Mode Suffixes

Individual instructions can override the current mode using suffix prefixes:

| Suffix | Meaning | Register width | Address width |
|--------|---------|----------------|---------------|
| `.SIS` | Short Immediate, Short | 16-bit | 16-bit |
| `.LIS` | Long Immediate, Short | 24-bit | 16-bit |
| `.SIL` | Short Immediate, Long | 16-bit | 24-bit |
| `.LIL` | Long Immediate, Long | 24-bit | 24-bit |

The first letter (S/L) controls register width for that instruction. The third letter (S/L) controls address width. In ADL mode, `.SIS` forces an instruction to behave as standard Z80. In Z80 mode, `.LIL` forces an instruction to behave as full 24-bit.

### Mode-Switching Calls and Jumps

Calls and jumps can switch the processor mode at the target:

| Instruction | Current mode | Target mode | Return address size |
|-------------|-------------|-------------|---------------------|
| `CALL.IS nn` | ADL | Z80 | 3 bytes (ADL convention) |
| `CALL.IL nn` | Z80 | ADL | 3 bytes (long) |
| `JP.SIS nn` | any | Z80 | N/A (no return address) |
| `JP.LIL nn` | any | ADL | N/A (no return address) |
| `RST.LIL $08` | Z80 | ADL | 3 bytes (long) |

The `.IS` suffix means "Instruction Short" --- the target runs in Z80 mode. `.IL` means "Instruction Long" --- the target runs in ADL mode.

### The Practical Rule

**Stay in ADL mode.** MOS boots the Agon in ADL mode. MOS API calls expect ADL mode. VDP commands are sent through MOS routines that assume 24-bit stack frames. If you switch to Z80 mode and call MOS, the stack frame width mismatch will corrupt the stack and crash.

If you need tight 16-bit loops (e.g., porting a Z80 inner loop without rewriting it), use the `.SIS` suffix on individual instructions rather than switching the entire processor mode.

### The MBASE Trap

In Z80-compatible mode, the MBASE register provides the upper 8 bits of every memory address --- including instruction fetches. If you change MBASE while executing in Z80 mode, the next instruction fetch uses the new MBASE value. Unless your code exists at the corresponding physical address, execution jumps into garbage.

Rule: if you must use Z80 mode, set MBASE once at startup and leave it alone. Better yet, stay in ADL mode.

---

## 3. New Instructions

These instructions exist on the eZ80 but not on the standard Z80. They are the reason the eZ80 is more than just a Z80 with wider registers.

### Arithmetic and Test

| Instruction | Bytes | Cycles | Description |
|-------------|-------|--------|-------------|
| `MLT BC` | 2 | 6 | 8x8 unsigned multiply: B * C -> BC |
| `MLT DE` | 2 | 6 | 8x8 unsigned multiply: D * E -> DE |
| `MLT HL` | 2 | 6 | 8x8 unsigned multiply: H * L -> HL |
| `MLT SP` | 2 | 6 | 8x8 unsigned multiply: SPH * SPL -> SP (rarely useful) |
| `TST A, n` | 3 | 7 | Test: A AND n, set flags, A unchanged |
| `TST A, r` | 2 | 4 | Test: A AND r, set flags, A unchanged |
| `TSTIO n` | 3 | 12 | Test I/O: (C) AND n, set flags |

### Address Computation

| Instruction | Bytes | Cycles | Description |
|-------------|-------|--------|-------------|
| `LEA BC, IX+d` | 3 | 4 | BC = IX + signed displacement d |
| `LEA DE, IX+d` | 3 | 4 | DE = IX + d |
| `LEA HL, IX+d` | 3 | 4 | HL = IX + d |
| `LEA IX, IX+d` | 3 | 4 | IX = IX + d (add displacement to IX) |
| `LEA BC, IY+d` | 3 | 4 | BC = IY + d |
| `LEA DE, IY+d` | 3 | 4 | DE = IY + d |
| `LEA HL, IY+d` | 3 | 4 | HL = IY + d |
| `LEA IY, IY+d` | 3 | 4 | IY = IY + d (add displacement to IY) |
| `PEA IX+d` | 3 | 7 | Push (IX + d) onto stack |
| `PEA IY+d` | 3 | 7 | Push (IY + d) onto stack |

LEA computes an effective address without performing a memory access --- it is pure register arithmetic. On the standard Z80, computing `HL = IX + 5` requires a multi-instruction sequence (`PUSH IX / POP HL / LD DE,5 / ADD HL,DE`). LEA does it in a single instruction at 4 cycles.

### I/O and System

| Instruction | Bytes | Cycles | Description |
|-------------|-------|--------|-------------|
| `IN0 r, (n)` | 3 | 7 | Read from internal I/O port (8-bit address) |
| `OUT0 (n), r` | 3 | 7 | Write to internal I/O port (8-bit address) |
| `SLP` | 2 | -- | Sleep: halt CPU until interrupt (lower power than HALT) |
| `STMIX` | 2 | 4 | Set mixed-mode flag (enable ADL/Z80 interleaving) |
| `RSMIX` | 2 | 4 | Reset mixed-mode flag |

IN0/OUT0 use an 8-bit port address (unlike the standard IN/OUT which can use 16-bit port addresses via BC). They are designed for the eZ80's internal peripherals and are rarely used in Agon game code.

---

## 4. MLT --- The Game Changer

Of all the eZ80's new instructions, MLT is the most impactful for game and demo code. It performs an 8x8 unsigned multiply in a single instruction.

On the standard Z80, 8x8 multiplication requires a shift-and-add loop:

```z80
; Z80: 8x8 unsigned multiply (B * C -> A:C)
; Cost: 196-204 T-states, 14 bytes
mulu_z80:
    ld   a, 0           ; 7T   clear accumulator
    ld   d, 8           ; 7T   8 bits

.loop:
    rr   c              ; 8T   shift multiplier bit into carry
    jr   nc, .noadd     ; 7/12T
    add  a, b           ; 4T   add multiplicand
.noadd:
    rra                 ; 4T   shift result right
    dec  d              ; 4T
    jr   nz, .loop      ; 12T
    ret                 ; 10T  ~200 T-states total
```

On the eZ80:

```z80
; eZ80: 8x8 unsigned multiply (B * C -> BC)
; Cost: 6 cycles, 2 bytes
    mlt  bc             ; BC = B * C. Done.
```

Six cycles. Two bytes. No loop, no carry management, no temporary registers. The result lands in the full 16-bit register pair: the high byte of the product is in B, the low byte in C.

### What MLT Enables

**Sine table indexing.** Computing `base + angle * stride` for variable-stride sine lookups reduces from a subroutine call to two instructions (`MLT` + `ADD`).

**Sprite offset calculation.** Finding the address of sprite frame N in a sprite sheet: `base + frame * frame_size`. With MLT, this is trivial when frame_size fits in 8 bits.

**Fixed-point arithmetic.** Multiplying two 8-bit fixed-point values (e.g., velocity * friction) becomes a single instruction instead of a 200-T-state loop.

**Tile map addressing.** Computing `tile_base + (row * width + col)` where width fits in 8 bits: one MLT for the row offset, one ADD for the column.

### MLT Limitations

- **Unsigned only.** For signed multiplication, adjust the sign manually after the MLT.
- **8x8 only.** For 16x16 multiply, you still need a multi-step algorithm (though you can build it from MLT components).
- **Result overwrites both operands.** `MLT BC` destroys both B and C, replacing them with the 16-bit product. Save the inputs first if you need them.

---

## 5. Key Differences Summary

| Feature | Z80 (ZX Spectrum 128K) | eZ80 (Agon Light 2) |
|---------|----------------------|----------------------|
| Clock | 3.5 MHz | 18.432 MHz |
| Address width | 16-bit (64 KB visible) | 24-bit (16 MB, 512 KB populated) |
| Register width | 16-bit | 16-bit (Z80 mode) or 24-bit (ADL mode) |
| Stack per PUSH/CALL | 2 bytes | 2 bytes (Z80 mode) or 3 bytes (ADL mode) |
| Multiply instruction | None (shift-and-add loop, ~200T) | MLT rr (6 cycles) |
| RAM | 128 KB banked (8 x 16 KB pages) | 512 KB flat |
| RAM access model | Bank switching via port $7FFD | Flat 24-bit addressing |
| Video | ULA: direct memory-mapped at $4000 | VDP (ESP32): command-based via UART |
| Sound | AY-3-8910 via I/O ports | VDP audio via serial commands |
| Interrupts | IM1 (RST $38) or IM2 (vector table) | IM2 with MOS-managed vectors |
| Frame budget (50 Hz) | ~71,680 T-states (Pentagon) | ~368,640 T-states |
| Contended memory | Yes (ULA steals cycles from $4000-$7FFF) | No contention |
| OS | None (bare metal) | MOS (Machine Operating System) |
| Storage | Tape / DivMMC | SD card (FAT32, MOS file API) |

---

## 6. Agon Light 2 Specifics

### Hardware

- **CPU:** Zilog eZ80F92, 18.432 MHz
- **RAM:** 512 KB external SRAM, flat address space
- **VDP:** ESP32-PICO-D4 running FabGL, communicates with eZ80 via UART at 1,152,000 baud
- **Video modes:** Multiple, up to 640x480x64 colours. Most games use 320x240 or 320x200.
- **Hardware sprites:** Up to 256, managed entirely by VDP
- **Hardware tilemaps:** Scrollable tile layers, managed by VDP
- **Audio:** VDP synthesis --- sine, square, triangle, sawtooth, noise. Per-channel ADSR envelopes.
- **Storage:** MicroSD card, FAT32, accessed through MOS file API

### Frame Budget

At 18.432 MHz and 50 Hz refresh:

```
18,432,000 cycles/sec / 50 frames/sec = 368,640 cycles/frame
```

Compare with Pentagon (3.5 MHz, 50 Hz): 71,680 T-states/frame. The Agon has roughly **5.1x** the per-frame budget. But since many eZ80 instructions also execute in fewer cycles than their Z80 equivalents, effective throughput for typical code is 5x--20x greater.

### MOS API

MOS (Machine Operating System) provides the system interface. The standard entry point is `RST $08`:

```z80
; MOS API call pattern (in ADL mode)
    ld   a, mos_function     ; function number in A
    rst  $08                 ; call MOS
    ; return value in A (and sometimes HL)
```

Key MOS API functions:

| Function | Number | Description |
|----------|--------|-------------|
| `mos_getkey` | $00 | Wait for keypress, return ASCII code |
| `mos_load` | $01 | Load file from SD card to memory |
| `mos_save` | $02 | Save memory region to file on SD card |
| `mos_cd` | $03 | Change current directory |
| `mos_dir` | $04 | List directory contents |
| `mos_del` | $05 | Delete a file |
| `mos_ren` | $06 | Rename a file |
| `mos_sysvars` | $08 | Get pointer to system variables (keyboard map, VDP state, clock) |
| `mos_fopen` | $0A | Open file, return handle |
| `mos_fclose` | $0B | Close file handle |
| `mos_fread` | $0C | Read bytes from file |
| `mos_fwrite` | $0D | Write bytes to file |
| `mos_fseek` | $0E | Seek within file |

### VDP Command Protocol

VDP commands are sent as byte streams using `RST $10` (MOS: output byte to VDP). Most commands begin with VDU 23, followed by command-specific parameters:

```z80
; Send one byte to VDP
    ld   a, byte_value
    rst  $10                 ; MOS: send byte to VDP

; Example: set screen mode
    ld   a, 22               ; VDU 22 = set mode
    rst  $10
    ld   a, mode_number      ; 0-3 for standard modes
    rst  $10

; Example: move hardware sprite
; VDU 23, 27, 4, spriteNum          -- select sprite
; VDU 23, 27, 13, x.lo, x.hi, y.lo, y.hi  -- set position
```

The VDP processes commands asynchronously. There is a serial transfer delay between sending a command and the VDP acting on it. For smooth animation, send all updates early in the frame.

---

## 7. Porting Checklist

When porting Z80 code from the Spectrum to eZ80 ADL mode on the Agon, walk through this checklist:

**Addresses and pointers:**
- All addresses become 24-bit (3 bytes instead of 2)
- Change `DW` (define word) to `DL` (define long) for address tables
- Pointer table indexing changes from `* 2` to `* 3`
- Ensure upper byte of 24-bit addresses is correct (typically $00 or $04)

**Stack frames:**
- Every PUSH is 3 bytes, every CALL pushes a 3-byte return address
- Verify PUSH/POP pairs are balanced --- a mismatched pair corrupts 3 bytes, not 2
- Stack-relative offsets (e.g., accessing parameters pushed by the caller) change

**Block operations:**
- `LDIR` / `LDDR` use 24-bit BC in ADL mode --- ensure the upper byte of BC is zero if your count fits in 16 bits
- `PUSH`/`POP`-based block copy tricks push 3 bytes per PUSH, not 2

**Multiply:**
- Replace shift-and-add multiply loops with `MLT` where applicable
- `MLT BC` = B * C -> BC, `MLT DE` = D * E -> DE, `MLT HL` = H * L -> HL

**I/O and peripherals:**
- Replace port I/O (`OUT (C), A`, `IN A, ($FE)`) with MOS/VDP API calls
- Replace direct framebuffer writes ($4000--$5AFF) with VDP commands
- Replace AY register writes ($FFFD/$BFFD) with VDP sound commands

**Memory architecture:**
- Remove all bank switching logic (port $7FFD writes) --- flat address space
- Remove contended memory workarounds --- no contention on the Agon
- Remove shadow screen tricks --- VDP handles double buffering

**Code patterns that become unnecessary:**
- Self-modifying code for speed (still works, rarely worth the complexity)
- Stack pointer tricks for fast screen fills (no framebuffer to fill)
- Pre-shifted sprite copies (hardware sprites handle sub-pixel positioning)
- Interleaved screen address calculations (DOWN_HL, pixel_addr --- delete them)

**Code patterns that transfer directly:**
- Entity system loops (just widen pointers)
- AABB collision detection (8-bit comparisons, unchanged)
- Fixed-point 8.8 arithmetic (byte-level, unchanged)
- State machines and jump tables (widen table entries to 24-bit)
- DJNZ loops, CPIR searches, flag-based branching (all identical)

---

## See Also

- **Appendix A: Z80 Instruction Quick Reference** --- complete Z80 instruction table with T-states, byte counts, and flag effects. Everything in Appendix A also applies to the eZ80 in Z80-compatible mode.
- **Chapter 22: Porting --- Agon Light 2** --- the full porting walkthrough, with before/after code examples for rendering, sound, input, and game logic.

---

> **Sources:** Zilog eZ80 CPU User Manual (UM0077); Zilog eZ80F92 Product Specification (PS0153); Agon Light 2 Official Documentation, The Byte Attic; Dean Belfield, "Agon Light --- Programming Guide" (breakintoprogram.co.uk); Agon MOS API Documentation (github.com/AgonConsole8/agon-docs); Chapter 22 of this book
