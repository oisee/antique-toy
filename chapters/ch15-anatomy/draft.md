# Chapter 15: Anatomy of Two Machines

> "Design characterizes realizational, stylistic, ideological integrity."
> -- Introspec (spke), "For Design" (Hype 2015)

Welcome to Part V. We are building a game.

Parts I through IV gave you the demoscener's toolkit: cycle counting, screen tricks, inner loop optimisation, sound architecture, compression. A game makes different demands. You need the full memory map, not just the screen region. You need to understand banking, because your levels, music, and sprite data will not fit in one contiguous block. You need to know how the Agon Light 2's two processors talk to each other, because your game loop straddles that boundary.

This chapter is the hardware reference for everything that follows. Where Chapter 1 gave you the frame budget and Chapter 2 gave you the screen layout, this chapter gives you everything else. Keep it bookmarked.

---

## 15.1 ZX Spectrum 128K: Memory Map

The original 48K Spectrum had a simple memory model: 16 KB ROM at `$0000`-`$3FFF`, 48 KB RAM at `$4000`-`$FFFF`. The 128K model keeps this layout visible to the CPU but hides a banking system underneath.

The 128K has eight 16 KB pages of RAM (pages 0-7, totalling 128 KB) and two 16 KB ROMs (ROM 0: 128K editor, ROM 1: 48K BASIC). At any moment, the Z80 sees a 64 KB address space divided into four 16 KB slots:

| Address Range | Contents | Notes |
|---------------|----------|-------|
| `$0000`-`$3FFF` | ROM (0 or 1) | Selected by bit 4 of `$7FFD` |
| `$4000`-`$7FFF` | RAM page 5 | **Always** page 5. Screen memory lives here. |
| `$8000`-`$BFFF` | RAM page 2 | **Always** page 2. |
| `$C000`-`$FFFF` | RAM page N | Switchable: any page 0-7 via `$7FFD` |

Pages 5 and 2 are hardwired into their slots. You cannot swap them out. This means the screen (`$4000`-`$57FF`) is always accessible, and your main code (typically ORG'd at `$8000`) sits in page 2 where it will not disappear when you switch banks.

The top 16 KB slot at `$C000`-`$FFFF` is the flexible one. Write to port `$7FFD` and the page mapped there changes.

### The $7FFD Port: Bank Switching

Port `$7FFD` controls memory configuration on the 128K. It is write-only -- you cannot read it back. This means you must shadow its value in a RAM variable if you need to know the current state.

```
Port $7FFD bit layout:
  Bit 0-2:  RAM page mapped at $C000 (0-7)
  Bit 3:    Screen select (0 = normal screen at page 5,
                           1 = shadow screen at page 7)
  Bit 4:    ROM select (0 = 128K ROM, 1 = 48K BASIC ROM)
  Bit 5:    Disable paging (set this and banking is locked
            until next reset -- used by 48K BASIC)
  Bits 6-7: Unused
```

A typical bank-switch routine:

```z80
; Switch RAM page at $C000 to page number in A (0-7)
; Preserves other $7FFD bits from shadow variable
bank_switch:
    ld   b, a                 ; 4T   save desired page
    ld   a, (bank_shadow)     ; 13T  load current $7FFD state
    and  %11111000            ; 7T   clear page bits (0-2)
    or   b                    ; 4T   insert new page number
    ld   (bank_shadow), a     ; 13T  update shadow
    ld   bc, $7FFD            ; 10T
    out  (c), a               ; 12T  do the switch
    ret                       ; 10T
                              ; --- 73T total
```

Those 73 T-states are not free, but they are negligible compared to a frame budget of 70,000+. The real cost of banking is architectural, not temporal: you must design your data layout so that you never need to access two different banked pages simultaneously. Music data in page 4, level data in page 3, sprite graphics in page 6 -- but your music player and your renderer cannot both be running from `$C000` at the same time.

**The shadow screen.** Bit 3 of `$7FFD` selects which RAM page the ULA reads for display: page 5 (normal) or page 7 (shadow). This gives you hardware double-buffering -- draw into the shadow screen while the ULA displays the normal one, then flip by toggling bit 3. We will use this heavily in Chapter 17 (Scrolling) and Chapter 21 (Full Game).

### A Practical Memory Map for a 128K Game

Here is how a real game might lay out its 128 KB across the eight pages:

| Page | Slot | Usage |
|------|------|-------|
| 0 | `$C000` (banked) | Level data (maps, tile definitions) |
| 1 | `$C000` (banked) | Sprite graphics set 1 |
| 2 | `$8000`-`$BFFF` (fixed) | Main game code, entity system, interrupt handler |
| 3 | `$C000` (banked) | Sprite graphics set 2, lookup tables |
| 4 | `$C000` (banked) | Music data (.pt3 patterns, instruments) |
| 5 | `$4000`-`$7FFF` (fixed) | Primary screen, attribute memory, system vars |
| 6 | `$C000` (banked) | Sound effects, additional level data |
| 7 | `$C000` (banked) | Shadow screen (double-buffer target) |

Notice: page 7 serves double duty. The ULA can display it as the shadow screen, but you can also bank it into `$C000` and use it as a 16 KB data page when you are not double-buffering. Many demos exploit this.

The critical constraint: **your interrupt handler and main loop must live in pages 2 or 5**, because those are the only pages guaranteed to be mapped at all times. If an interrupt fires while page 4 is banked in at `$C000`, and your interrupt handler lives at `$C000`, the CPU jumps into your music data instead of your code. The result is a crash, usually a spectacular one.

**Rule:** never put time-critical code in a banked page unless you are absolutely certain which page is active when that code runs.

---

## 15.2 Contended Memory: The Practical Truth

In Chapter 1, we established that Pentagon clones have no contended memory and that cycle counts are reliable everywhere. That is true, and the Pentagon remains the standard for cycle-counted demo work. But if you are writing a game for release, your players will include people running original Sinclair hardware, Amstrad +2A/+3 models, and modern FPGA clones that emulate the original timing. You need to know what contended memory does and how to avoid its worst effects.

Introspec covered this exhaustively in his "GO WEST" articles on Hype (2015). Here is the practical summary.

### What Gets Contended

On the original Sinclair machines, the ULA and the CPU share a memory bus. When the ULA is reading screen data to paint the display (during the 192 active scanlines), any CPU access to certain RAM pages gets delayed. The CPU is literally halted for extra T-states while the ULA finishes its read.

The contended pages differ between models:

| Model | Contended Pages | Always Fast |
|-------|----------------|-------------|
| 48K | All RAM (`$4000`-`$FFFF`) | None (but `$8000`+ is less contended in practice) |
| 128K / +2 | Pages 1, 3, 5, 7 | Pages 0, 2, 4, 6 |
| +2A / +2B / +3 | Pages 4, 5, 6, 7 | Pages 0, 1, 2, 3 |

The 48K is the worst case -- all RAM is contended. On the 128K, the pattern is every odd page. On the +2A/+3, it flips: the high pages are contended.

This has immediate practical consequences. On a 128K, your main code at `$8000` (page 2) is in uncontended memory -- fast. The screen at `$4000` (page 5) is contended -- writes to screen memory are slower during active display. And page 7 (the shadow screen) is also contended, which means double-buffer fills to the shadow screen are slower than you might expect on original hardware.

### How Much Slower?

Introspec measured the actual penalties:

- **Random byte access to contended memory:** approximately **0.92 extra T-states per byte** on average during active display
- **Stack operations (PUSH/POP) to contended memory:** approximately **1.3 extra T-states per byte** on average
- **During border time:** **zero penalty** -- contention only occurs while the ULA is actively painting scanlines

That 0.92 figure means a `LD A,(HL)` that should cost 7 T-states will cost, on average, about 7.92 T-states when HL points into contended memory during active display. A PUSH that writes two bytes to contended memory at 11 T-states will cost about 13.6 T-states instead.

These averages hide a messy reality: the actual penalty depends on where in the ULA's 8-T-state read cycle your CPU access lands. The pattern repeats every 8 T-states: penalties of 6, 5, 4, 3, 2, 1, 0, 0 extra states. You can land anywhere in this cycle, and the penalty compounds with each memory access within an instruction. This makes precise cycle counting on contended machines genuinely difficult.

### The Practical Response

For game development, not demo effects, the approach is straightforward:

1. **Put your code in uncontended memory.** On the 128K, ORG at `$8000` (page 2) -- always fast.
2. **Write to the screen during border time when possible.** The top and bottom borders give you contention-free access to screen memory. So does the left/right border of each scanline.
3. **Do not worry about precise contention modelling.** Budget a 15-20% slowdown for code that touches screen memory during active display, and design your frame budget with that margin. This is not cycle-counted demo work; this is game development.
4. **Test on real hardware or accurate emulators.** Fuse emulates contention correctly. Unreal Speccy (Pentagon mode) does not, by design. ZEsarUX can emulate multiple models.

Introspec's advice from GO WEST boils down to this: **contended memory is a portability issue, not a drama.** If your code runs on Pentagon, it will almost certainly run on original hardware too -- just a little slower during screen writes. The places where contention actually breaks things are cycle-exact raster effects (multicolour, floating bus sync), and those are demo techniques, not game techniques.

---

## 15.3 ULA Timing

The ULA generates the video signal and the CPU interrupt. Understanding its timing is essential for border effects, interrupt-driven music, and screen synchronisation.

### Frame Structure

A complete frame consists of scanlines. The scanline width and total scanline count differ between models:

| Machine | T-states/line | Scanlines | T-states/frame |
|---------|--------------|-----------|----------------|
| ZX Spectrum 48K | 224 | 312 | 69,888 |
| ZX Spectrum 128K | 228 | 311 | 70,908 |
| Pentagon 128 | 224 | 320 | 71,680 |

Note the 128K's wider scanline (228 vs 224 T-states). The extra 4 T-states per line are in the border/sync portion, not the active display.

### Tact-Maps: Frame Regions

The frame divides into three regions. The interrupt fires at the start of vertical blank, before the top border. Here is the timing map for each model:

**Pentagon 128 (71,680 T-states)**

```
Interrupt ──┐
            │
Top border  │  80 lines × 224T = 17,920T   No screen reads. No contention.
            │
Active      │ 192 lines × 224T = 43,008T   ULA reads screen memory.
display     │                                No contention on Pentagon.
            │
Bottom      │  48 lines × 224T = 10,752T   No screen reads. No contention.
border      │
────────────┘  Total: 71,680T
```

**ZX Spectrum 128K (70,908 T-states)**

```
Interrupt ──┐
            │
Top border  │  63 lines × 228T = 14,364T   No screen reads. No contention.
            │
Active      │ 192 lines × 228T = 43,776T   ULA reads screen memory.
display     │                                Contention on pages 1,3,5,7.
            │
Bottom      │  56 lines × 228T = 12,768T   No screen reads. No contention.
border      │
────────────┘  Total: 70,908T
```

**ZX Spectrum 48K (69,888 T-states)**

```
Interrupt ──┐
            │
Top border  │  64 lines × 224T = 14,336T   No screen reads. No contention.
            │
Active      │ 192 lines × 224T = 43,008T   ULA reads screen memory.
display     │                                Contention on all RAM.
            │
Bottom      │  56 lines × 224T = 12,544T   No screen reads. No contention.
border      │
────────────┘  Total: 69,888T
```

After a `HALT`, you have the entire top border period -- 17,920 T-states on Pentagon, 14,364 on 128K -- to do work before the beam enters the active display area and contention begins. This is why well-structured Spectrum code does screen writes at the top of the frame: you get contention-free access to screen memory during the border period.

### Scanline Timing

Each scanline breaks down into an active portion (where the ULA reads screen data) and border/sync portions:

**48K and Pentagon (224 T-states per line):**

```
128T  active pixel area (ULA reads screen data)
 24T  right border
 48T  horizontal sync + retrace
 24T  left border
```

**128K (228 T-states per line):**

```
128T  active pixel area (ULA reads screen data)
 24T  right border
 52T  horizontal sync + retrace
 24T  left border
```

During the 128 active T-states, memory access to contended pages gets delayed (on non-Pentagon machines). During the remaining 96 T-states (or 100 on 128K), no contention. Even during active display, roughly half of each scanline is contention-free.

### Total vs Practical Budget

The frame totals above are the time between interrupts. The *practical* budget -- T-states available for your code -- is less:

| Overhead | Cost |
|----------|------|
| HALT + interrupt acknowledge (IM1) | ~30 T-states |
| Minimal ISR (EI + RET) | ~14 T-states |
| Typical PT3 music player (in ISR) | ~3,000--5,000 T-states |
| Main loop housekeeping (frame counter, HALT jump) | ~20--50 T-states |

Practical budgets with a music player running:

| Machine | Total | After PT3 player | After player + contention margin |
|---------|-------|-------------------|----------------------------------|
| Pentagon | 71,680 | ~66,000--68,000 | ~66,000--68,000 (no contention) |
| 128K | 70,908 | ~65,000--67,000 | ~55,000--60,000 (screen writes during active display) |
| 48K | 69,888 | ~64,000--66,000 | ~50,000--55,000 (all RAM contended) |

When this book says "frame budget of ~70,000 T-states," it means the total. When planning your inner loops, budget for the practical figure -- typically 65,000--68,000 on Pentagon with music.

---

## 15.4 Floating Bus, ULA Snow, and the $7FFD Bug

These are three hardware quirks that appear on original Sinclair machines but not on most clones. You may never encounter them in game development, but they can cause mysterious bugs if you do not know they exist.

### Floating Bus

On original Spectrum hardware, reading from an unattached port returns whatever data the ULA happens to be putting on the data bus at that moment. During active display, the ULA is reading screen memory, so a read from port `$FF` returns the byte the ULA is currently reading.

Demo coders exploit this for beam synchronisation: read the floating bus in a tight loop until you see a known value from screen memory, and you know exactly where the beam is. This is the cheapest sync method -- no interrupt timing required.

Games rarely need this, but be aware: if your code reads from a port that does not exist on the hardware, the return value is unpredictable and varies between models. The floating bus is *not* emulated on Pentagon, Scorpion, or ZX Next.

### The $7FFD Read Bug

Port `$7FFD` is write-only. But on some Spectrum models, reading from port `$7FFD` (even unintentionally, through an instruction that happens to put `$7FFD` on the address bus) causes the floating bus value to be written into the port. This triggers a spurious page switch.

The practical danger: the Z80 instruction `LD A,(nn)` puts the address `nn` on the bus during execution. If `nn` happens to be `$7FFD` and you are reading data stored at address `$7FFD`, the memory read can trigger a port write on original hardware. This is an obscure bug but a real one. Avoid storing data at address `$7FFD`.

### ULA Snow

If the Z80's I register (used for IM2 interrupt vector table base) is set to a value in the range `$40`-`$7F`, the DRAM refresh cycle during every M1 opcode fetch puts an address in the `$4000`-`$7FFF` range onto the address bus. This conflicts with the ULA's screen reads and produces visual "snow" -- random noise on the display.

The fix is simple: **never set I to a value between `$40` and `$7F`.** The typical IM2 setup uses `I = $FE` with a 257-byte table of identical vectors at `$FE00`-`$FF00`. This keeps I well above the danger zone.

---

## 15.5 Clone Differences

The ZX Spectrum ecosystem includes dozens of clones, but three matter most for modern development: the Pentagon 128, the Scorpion ZS-256, and the ZX Spectrum Next.

### Pentagon 128

The Pentagon is the standard platform for the Russian demoscene and the primary target for this book's demoscene chapters.

| Parameter | Pentagon 128 | Original 128K |
|-----------|-------------|---------------|
| CPU clock | 3.5 MHz | 3.5 MHz |
| T-states per frame | **71,680** | 70,908 |
| Scanlines per frame | **320** | 311 |
| Contended memory | **None** | Pages 1, 3, 5, 7 |
| Border lines (top) | **80** | 63 |
| Border lines (bottom) | **48** | 56 |

The extra 772 T-states per frame (71,680 vs 70,908) come from the additional scanlines. The border is distributed differently: a taller top border and a shorter bottom border. This affects border effects -- demo code that produces a symmetrical border pattern on the 128K will be slightly asymmetric on the Pentagon.

The absence of contended memory is the Pentagon's defining feature for programmers. Every instruction costs exactly what the datasheet says. This is why we use Pentagon timing throughout this book.

**7 MHz Turbo mode.** Many Pentagon-compatible machines (Pentagon 512, Pentagon 1024, ATM Turbo 2+) offer a 7 MHz turbo mode. The CPU runs at double speed, but the ULA timing stays the same. This means the frame budget doubles to approximately 143,360 T-states in turbo mode. The catch: turbo mode is not standard across all machines, and code that relies on it will not run on a stock Pentagon 128 or any Sinclair hardware.

For games, turbo mode is a luxury that lets you run more complex logic or more sprites per frame. For demos targeting compo rules, it is usually forbidden -- competitions specify "Pentagon 128K, 3.5 MHz."

### Scorpion ZS-256

The Scorpion is a Ukrainian clone with 256 KB of RAM (16 pages of 16 KB) and several hardware extensions.

| Feature | Scorpion ZS-256 |
|---------|----------------|
| RAM | 256 KB (16 pages) |
| Banking | Extended `$1FFD` port for pages 8-15 |
| Graphics | GMX mode: 320x200, 16 colours from 256 |
| Contended memory | None |
| Frame timing | Pentagon-compatible (71,680 T-states) |

The doubled RAM is useful for games: you get 16 data pages instead of 8. The extra pages are accessed via port `$1FFD`, which uses a similar scheme to `$7FFD` but controls the additional RAM.

GMX (Graphics Mode Extended) is the Scorpion's party trick: a 320x200 display with 16 colours chosen from a 256-colour palette. This breaks completely with the Spectrum's attribute-based display, offering a linear framebuffer closer to what you might see on an Amiga or a PC VGA. The GMX framebuffer is large (32,000 bytes for 4-bit colour) and lives in the extended RAM pages.

Few games target GMX because it limits your audience to Scorpion owners. But it demonstrates what Z80 hardware can do when freed from the ULA's attribute grid.

### ZX Spectrum Next

The ZX Spectrum Next is the modern flagship of the platform: an FPGA-based machine that is backward-compatible with the original Spectrum but adds substantial new hardware.

| Feature | ZX Spectrum Next |
|---------|-----------------|
| CPU | Z80N (Z80 + new instructions) at 3.5 / 7 / 14 / 28 MHz |
| RAM | 1 MB (extendable to 2 MB), 8 KB MMU pages |
| MMU | 8 slots x 8 KB = fine-grained memory mapping |
| Layer 2 | 256x192 or 320x256, 8-bit colour (256 colours) |
| Tilemap | Hardware tilemap layer, 40x32 or 80x32 tiles |
| Sprites | 128 hardware sprites, 16x16, up to 12 per scanline |
| Copper | Co-processor for per-scanline register changes |
| DMA | zxnDMA for fast block transfers |
| AY sound | 3 x AY-3-8910 (9 channels) with per-channel stereo panning |

The Next's **MMU** is fundamentally different from the 128K's banking. Instead of one switchable 16 KB slot, the Next divides the entire 64 KB address space into eight 8 KB slots. Each slot can be independently mapped to any 8 KB page from the 1-2 MB RAM pool. This means you can have fine-grained control:

```z80
; Map 8KB page $0A into slot 3 ($6000-$7FFF)
    ld   a, $0A
    ld   bc, $243B          ; Next register select port
    ld   a, $53             ; Register $53 = MMU slot 3
    out  (c), a
    ld   bc, $253B          ; Next register data port
    ld   a, $0A             ; Page $0A
    out  (c), a
```

This is much more flexible than the 128K's single switchable slot. You can map sprite data into one 8 KB window, level data into another, and music data into a third -- all simultaneously visible.

**Layer 2** gives you a 256-colour bitmap display without attribute clash. This is the single biggest quality-of-life improvement for game developers: no more careful attribute planning, no more colour clash workarounds. Just a framebuffer where each byte is one pixel. The cost is memory: a 256x192 Layer 2 screen is 49,152 bytes.

**Hardware sprites** on the Next provide 128 sprite slots, each 16x16 pixels with 8-bit colour, up to 12 per scanline. Sprite attributes (position, pattern, rotation) are set through Next registers and port `$57`. No software rendering needed.

**The Copper** is a co-processor that executes a simple program synchronised to the beam position. It can write to any Next register at any scanline, enabling per-line palette changes, scroll offsets, and raster effects without consuming Z80 T-states -- a deliberate homage to the Amiga Copper.

**zxnDMA** provides hardware-accelerated block transfers at approximately 2 T-states per byte -- about 10 times faster than `LDIR`. For filling the Layer 2 framebuffer or transferring sprite data, DMA is transformative.

The Next is essentially a different machine that happens to be backward-compatible. The interesting constraints shift from "can I fit this in the frame budget" to "how do I best use multiple hardware layers."

---

## 15.6 Agon Light 2: A Different Beast

The Agon Light 2 is the second platform for our game development chapters. It runs a Zilog eZ80 -- a direct descendant of the Z80 -- at 18.432 MHz, with 512 KB of flat RAM and a separate ESP32 co-processor handling video and audio. The architecture is fundamentally different from the Spectrum: instead of a CPU that shares a bus with a fixed video output chip, the Agon uses two independent processors communicating over a serial link.

### Dual-Processor Architecture

The Agon's defining characteristic is the split between the **eZ80** (your CPU) and the **ESP32** (the VDP, Video Display Processor):

```
                        +-----------+
                        |   eZ80    |  18.432 MHz
                        |  512 KB   |  Your code runs here
                        |  MOS API  |  24-bit addressing
                        +-----+-----+
                              |
                          UART serial
                          (384 Kbaud)
                              |
                        +-----+-----+
                        |   ESP32   |  240 MHz dual-core
                        |  FabGL    |  Video: up to 640x480
                        |  VDP      |  Audio: waveforms, samples
                        +-----------+
```

This split has profound consequences:

1. **No shared video memory.** You cannot write directly to a framebuffer. Every pixel, every sprite, every tile operation is a *command* sent over the serial link from the eZ80 to the ESP32.
2. **Latency.** The serial link runs at 384,000 baud. A single command byte takes about 26 microseconds to transmit. Complex drawing operations (fill rectangle, draw bitmap) require multiple bytes and the VDP needs time to execute them.
3. **Asynchronous rendering.** The VDP processes commands from a buffer. Your eZ80 code sends commands and continues running. The VDP catches up independently. This means you do not have the Spectrum's tight coupling between CPU work and screen output -- but you also cannot precisely control when pixels appear.
4. **Independent frame rate.** The VDP renders at its own rate (typically 60 Hz). Your eZ80 game loop can run at whatever rate it wants; the VDP will display whatever it has most recently drawn.

For Spectrum programmers, this is a paradigm shift. You go from "I write bytes to video memory and they appear on the next scanline" to "I send drawing commands and trust the VDP to render them eventually." The upside is enormously reduced CPU overhead for graphics. The downside is less control.

### eZ80 Memory Model: 24-Bit Flat

The eZ80 has a 24-bit address bus, giving it a theoretical 16 MB address space. The Agon Light 2 maps 512 KB of RAM into the bottom of this space:

| Address Range | Size | Contents |
|---------------|------|----------|
| `$000000`-`$07FFFF` | 512 KB | RAM |
| `$080000`-`$0FFFFF` | 512 KB | RAM (mirror, on some boards) |
| `$A00000`-`$FFFFFF` | varies | I/O, on-chip peripherals |

No banking. No page switching. No contended memory. Your code, your data, your buffers, your lookup tables -- everything lives in one flat, linearly addressable space. After the Spectrum's 8-page juggling act, this is liberating.

The eZ80 supports two operating modes that determine how it uses this address space.

### ADL Mode vs Z80 Mode

This is the most important architectural distinction on the Agon, and it trips up newcomers constantly.

**Z80 mode** (also called Z80-compatible mode) makes the eZ80 behave like a classic Z80: 16-bit registers, 16-bit addresses, 64 KB address space. All standard Z80 code runs unmodified. The upper 8 bits of the address come from the MBASE register, creating a 64 KB "window" into the 24-bit address space. This is what you use when porting existing Z80 code.

**ADL mode** (Address Data Long) is the eZ80's native mode: 24-bit registers, 24-bit addresses, full 16 MB address space. HL, BC, DE, SP, and IX/IY are all 24 bits wide. `LD HL,$123456` loads a 3-byte value. `PUSH HL` pushes 3 bytes onto the stack (not 2). Every pointer is 3 bytes.

```z80
; ADL mode: 24-bit addressing, full 512KB accessible
    ld   hl, $040000       ; point to a buffer 256KB into RAM
    ld   (hl), $FF         ; write directly -- no banking needed
    ld   bc, 1024
    ld   de, $040001
    ldir                   ; fill 1KB in one shot
```

MOS (the Agon's operating system) boots the eZ80 in ADL mode, and most Agon software stays in ADL mode. The key differences from Z80 mode:

| Feature | Z80 Mode | ADL Mode |
|---------|----------|----------|
| Register width | 16 bits | 24 bits |
| Address space | 64 KB (via MBASE) | 16 MB (24-bit) |
| PUSH/POP size | 2 bytes | 3 bytes |
| JP/CALL addresses | 16-bit | 24-bit |
| Stack frame size | 2 bytes per entry | 3 bytes per entry |
| Instruction encoding | Z80-compatible | Extended (3-byte addresses) |

**The trap:** if you write code assuming 16-bit values and run it in ADL mode, things break in subtle ways. A `PUSH HL` pushes 3 bytes, not 2, so your stack-based data structures have a different size. A `JP (HL)` jumps to a 24-bit address, so lookup tables of 16-bit addresses will not work. The eZ80 provides `LD.S` and `LD.L` suffixed instructions to explicitly control the data width, and you can switch between modes with `JP.LIL` / `JP.SIS` prefixes, but this gets complicated fast.

**The practical rule for games:** stay in ADL mode. Use 24-bit addresses everywhere. Do not try to share code between a Spectrum build and an Agon build at the source level -- the addressing is too different. Instead, share *algorithms* and *data formats*, with platform-specific implementations for memory access, I/O, and graphics.

### MOS API: The Operating System

MOS (Machine Operating System) provides system services on the Agon: file I/O, keyboard input, timer access, and VDP communication. MOS calls are made through `RST $08` with a function number in the A register:

```z80
; MOS API: open a file
    ld   hl, filename       ; pointer to null-terminated filename
    ld   c, $01             ; mode: read
    rst  $08                ; MOS call
    db   $0A                ; function $0A: ffs_fopen
    ; Returns file handle in A
filename:
    db   "level1.dat", 0
```

Key MOS functions for game development:

| Function | Code | Description |
|----------|------|-------------|
| `mos_getkey` | `$00` | Read keyboard (non-blocking) |
| `mos_load` | `$01` | Load file from SD card |
| `mos_save` | `$02` | Save file to SD card |
| `mos_sysvars` | `$08` | Get pointer to system variables (vsync counter, etc.) |
| `ffs_fopen` | `$0A` | Open file |
| `ffs_fclose` | `$0B` | Close file |
| `ffs_fread` | `$0C` | Read from file |
| `mos_getrtc` | `$12` | Get real-time clock |

File I/O on the Agon is trivially easy compared to the Spectrum. No tape loading, no esxDOS wrappers, no TR-DOS: just open a file from the SD card and read it into memory. Level data, sprite sheets, music -- load them on demand, no banking gymnastics.

### VDP Commands: Talking to the Screen

All graphics go through VDU commands sent to the ESP32 VDP. The eZ80 sends bytes to a VDU output stream; the VDP interprets them as drawing instructions:

```z80
; VDP: draw a filled rectangle at (10, 10)
    rst  $10 : db 25        ; PLOT command
    rst  $10 : db 85        ; mode: filled rectangle
    rst  $10 : db 10        ; x low
    rst  $10 : db 0         ; x high
    rst  $10 : db 10        ; y low
    rst  $10 : db 0         ; y high
```

Verbose compared to `LD (HL),A`, but the VDP does the rendering on the ESP32. The VDP supports bitmap modes (up to 640x480), up to 256 hardware sprites (each up to 64x64), hardware tilemaps with scrolling, and audio (waveforms, ADSR, samples).

The bottleneck is the serial link, not the CPU. A complex scene with many sprite updates can saturate the UART, causing visual lag. Minimise VDP commands per frame: batch updates, use hardware scrolling instead of redrawing tiles, and let the sprite engine do the heavy lifting.

---

## 15.7 Comparing the Platforms

Let us lay out the two machines side by side, focusing on what matters for the game engine we will build in Chapters 16-19.

| Feature | ZX Spectrum 128K | Agon Light 2 |
|---------|-----------------|---------------|
| CPU | Z80A @ 3.5 MHz | eZ80 @ 18.432 MHz |
| T-states per frame (50 Hz) | ~70,908 (128K) / 71,680 (Pentagon) | ~368,640 |
| RAM | 128 KB (8 x 16 KB pages) | 512 KB (flat) |
| Address space | 64 KB (banked) | 16 MB (24-bit) |
| Screen memory | Shared bus, direct write | Separate VDP, command-based |
| Colours | 15 (8 base x bright, minus overlap) | Up to 64 in standard modes |
| Resolution | 256x192 (attribute colour per 8x8) | Configurable, up to 640x480 |
| Sprites | Software only | Up to 256 hardware sprites |
| Scrolling | Software only (manual shift/copy) | Hardware scroll offsets |
| Sound | AY-3-8910 (3 channels) | ESP32 audio (multi-channel, waveforms) |
| Storage | Tape / DivMMC (esxDOS) | SD card (FAT32) |
| Double buffering | Shadow screen (page 7) | VDP-managed |

The frame budget ratio is approximately 5:1 in the Agon's favour. But the Agon's graphics go through a serial bottleneck, so raw CPU speed does not translate directly to rendering speed. On the Spectrum, `PUSH HL` writes two bytes to the screen in 11 T-states. On the Agon, updating a sprite position requires 6+ bytes over a 384 Kbaud link, taking hundreds of microseconds regardless of CPU speed.

The Spectrum rewards byte-level optimisation. The Agon rewards architectural decisions. Both reward careful thinking about frame budgets.

---

## 15.8 Practical: Memory Inspector Utility

Let us build a simple memory inspector for both platforms. This utility displays a region of RAM as hex bytes on screen, and lets you navigate through memory with the keyboard. It is the kind of tool you will use constantly during development.

### Spectrum Version

The Spectrum version writes directly to screen memory. We display 16 rows of 16 bytes (256 bytes per page) with the start address shown at the left.

```z80
; Memory Inspector - ZX Spectrum 128K
; Displays 256 bytes of memory as hex, navigable with keys
; ORG $8000 (page 2, uncontended)

    ORG  $8000

SCREEN_ATTR EQU $5800
START_ADDR  EQU inspect_addr      ; address to inspect (self-mod)

start:
    call clear_screen

main_loop:
    halt                          ; sync to frame

    ; Read keyboard
    call read_keys                ; returns: A = action
    cp   1
    jr   z, .page_up             ; Q = previous page
    cp   2
    jr   z, .page_down           ; A = next page
    cp   3
    jr   z, .bank_up             ; P = next bank
    cp   4
    jr   z, .bank_down           ; O = previous bank
    jr   .draw

.page_up:
    ld   hl, (inspect_addr)
    ld   de, -256
    add  hl, de
    ld   (inspect_addr), hl
    jr   .draw
.page_down:
    ld   hl, (inspect_addr)
    ld   de, 256
    add  hl, de
    ld   (inspect_addr), hl
    jr   .draw
.bank_up:
    ld   a, (current_bank)
    inc  a
    and  7                        ; wrap 0-7
    ld   (current_bank), a
    call bank_switch
    jr   .draw
.bank_down:
    ld   a, (current_bank)
    dec  a
    and  7
    ld   (current_bank), a
    call bank_switch

.draw:
    ; Display current bank and address
    call draw_header

    ; Display 16 rows x 16 bytes
    ld   hl, (inspect_addr)
    ld   b, 16                    ; 16 rows
    ld   de, $4060                ; screen position (row 3, col 0)
.row_loop:
    push bc
    push hl

    ; Print address
    ld   a, h
    call print_hex                ; print high byte of address
    ld   a, l
    call print_hex                ; print low byte
    ld   a, ':'
    call print_char

    ; Print 16 hex bytes
    pop  hl
    push hl
    ld   b, 16
.byte_loop:
    ld   a, (hl)
    call print_hex                ; 7T load + print routine
    inc  hl
    ld   a, ' '
    call print_char
    djnz .byte_loop

    pop  hl
    ld   de, 16
    add  hl, de                   ; advance to next row
    pop  bc

    ; Move screen pointer down one character row
    call next_char_row

    djnz .row_loop

    jr   main_loop

; --- Data ---
inspect_addr:  dw $C000          ; start address to inspect
current_bank:  db 0              ; current bank at $C000
bank_shadow:   db 0              ; shadow of port $7FFD

; read_keys, print_hex, print_char, clear_screen,
; draw_header, next_char_row, bank_switch: implementations
; omitted for brevity -- see examples/mem_inspect.a80
; for the complete compilable source.
```

The key architectural point: we inspect `$C000` because that is the banked slot. By changing `current_bank`, we can page through all 8 RAM pages using the `bank_switch` routine from section 15.1. The inspector itself lives at `$8000` (page 2), safe from banking changes.

### Agon Version

The Agon version uses MOS system calls for keyboard input and VDP text output. No screen memory calculation, no attribute handling -- just send text to the VDP.

```z80
; Memory Inspector - Agon Light 2 (ADL mode)
    .ASSUME ADL=1
    ORG  $040000

main_loop:
    ; Wait for vsync via MOS sysvar
    rst  $08
    db   $08                      ; mos_sysvars
    ld   a, (ix+$00)              ; sysvar_time (low byte)
.wait_vsync:
    cp   (ix+$00)
    jr   z, .wait_vsync           ; spin until counter changes

    ; Check keyboard (Q = up, A = down)
    rst  $08
    db   $00                      ; mos_getkey
    ; ... navigation same as Spectrum version ...

.draw:
    rst  $10
    db   30                       ; VDU 30 = cursor home

    ld   hl, (inspect_addr)       ; 24-bit load!
    ld   b, 16
.row_loop:
    push bc
    push hl
    call print_hex24              ; print full 24-bit address
    ld   a, ':'
    rst  $10
    pop  hl
    push hl
    ld   b, 16
.byte_loop:
    ld   a, (hl)                  ; direct 24-bit access, no banking
    call print_hex8
    inc  hl
    djnz .byte_loop
    pop  hl
    ld   de, 16
    add  hl, de
    pop  bc
    djnz .row_loop
    jr   main_loop

inspect_addr: dl $000000          ; 24-bit address (dl, not dw)
; Full source: examples/mem_inspect_agon.a80
```

Notice the contrast:

- **No bank switching.** The Agon inspector can look at any address in 512 KB directly. `LD HL,$070000` and you are inspecting 448 KB into RAM. No ports, no shadow variables, no risk of banking in the wrong page.
- **No screen address calculation.** Text output goes through `RST $10`, and the VDP handles cursor positioning, character rendering, and scrolling.
- **24-bit data directives.** We use `dl` (define long) for 3-byte pointers instead of `dw` (define word).
- **VSync through system variables.** MOS provides a `sysvar_time` counter that increments each frame. We spin-wait on it for frame synchronisation -- cruder than the Spectrum's `HALT`, but functional.

Both inspectors do the same job. The Spectrum version is more code (you must handle everything yourself) but gives you total control. The Agon version is less code (the OS and VDP handle display) but gives you less control over exactly how the output looks.

This mirrors the broader development experience on both platforms. The Spectrum demands more effort for less visual richness. The Agon demands less effort for more visual richness. Both reward understanding the hardware.

---

## Summary

- The **ZX Spectrum 128K** has 128 KB of RAM in 8 pages of 16 KB. Pages 2 and 5 are fixed in the address space; the top 16 KB slot at `$C000` is switchable via port `$7FFD`. Keep your main code in page 2 and your interrupt handler away from banked memory.

- **Contended memory** slows CPU access to certain RAM pages during active display on original Sinclair hardware. Average penalty: ~0.92 extra T-states per byte. Pentagon clones have no contention. For game development, budget a 15-20% overhead on screen writes and keep time-critical code in uncontended pages.

- **ULA timing:** the interrupt fires at the top of the frame. You get ~14,000 T-states of contention-free time before the beam enters the active display area. Use this window for screen writes.

- The **$7FFD port** is write-only. Shadow its value in RAM. Bit 3 selects the shadow screen (page 7) for double buffering. Bit 5 disables paging permanently until reset.

- **Floating bus**, **ULA snow**, and the **$7FFD read bug** are quirks of original Sinclair hardware. Avoid I register values `$40`-`$7F`. Do not store data at address `$7FFD`. The floating bus is not present on clones.

- **Pentagon 128**: no contended memory, 71,680 T-states per frame, 320 scanlines. The demoscene standard. 7 MHz turbo mode doubles the frame budget on some variants.

- **Scorpion ZS-256**: 256 KB RAM (16 pages), GMX 320x200x16 colour mode.

- **ZX Spectrum Next**: 1-2 MB RAM with 8 KB MMU pages, Layer 2 (256-colour bitmap), 128 hardware sprites, Copper co-processor, zxnDMA, triple AY sound.

- The **Agon Light 2** uses a dual-processor architecture: eZ80 @ 18.432 MHz for logic, ESP32 for video/audio. 512 KB flat RAM, 24-bit addressing (ADL mode), MOS API for system services, VDP commands for all graphics.

- **ADL mode vs Z80 mode**: ADL mode uses 24-bit registers and addresses. Z80 mode emulates classic Z80 with 16-bit addresses via MBASE. Stay in ADL mode for new Agon code.

- The **serial link** between eZ80 and ESP32 is the Agon's bottleneck. Minimise VDP command traffic per frame. Use hardware sprites and tilemaps to reduce the number of drawing commands.

- Both platforms reward careful frame budget management. The Spectrum gives you ~70,000 T-states and demands byte-level optimisation. The Agon gives you ~368,000 T-states but throttles graphics through a serial link. Different constraints, same discipline.

---

> **Sources:** Introspec "GO WEST Parts 1--2" (Hype 2015); ZX Spectrum 128K Service Manual; Zilog eZ80 CPU User Manual; Agon Light 2 Documentation (Bernardo Kastrup); ZX Spectrum Next User Manual (2nd Edition)
