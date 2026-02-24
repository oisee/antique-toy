# ZXDN Article Analysis: Sound & Multicolor Techniques

Analysis of 7 articles from ZX Spectrum diskmags (ZXDN archive), focused on sound
(AY/TurboSound, digital samples, sync) and multicolor/border effects.

Source files: `_in/raw/zxdn/coding/` (CP1251 encoding, Russian language).

---

## 1. ig8tsprg.txt — TurboSound Programming

**Author:** Shiru Otaku
**Source:** Info Guide #8, Ryazan, December 2005

### Key Techniques

Comprehensive guide to programming the TurboSound (2xAY) card, covering all three
hardware variants and their chip-selection protocols:

1. **NedoPC TurboSound** (most common standard):
   - Chip selection via port `#FFFD` (same as AY register select port)
   - Write `#FF` to select chip 0 (default), `#FE` to select chip 1
   - Selection procedure: `LD BC,#FFFD / LD A,#FF / OUT (C),A` (chip 0)
   - Universal routine with parameter: `AND 1 / XOR B / OUT (C),A` where B=#FF

2. **QUADRA (Amazing Soft Making)**:
   - Incompatible variant using ports `#EEFD` and `#AFFD` for the second chip
   - Different register selection addresses per chip

3. **PoS TurboSound**:
   - Uses port `#1F` for chip switching
   - Value 0 = chip 0, value 1 = chip 1
   - Simpler selection: `LD A,0 / OUT (#1F),A` for chip 0

4. **Universal chip selection** supporting both NedoPC and PoS:
   - Auto-detection routine by Himik's ZxZ/PoS-WT
   - Writes different values to register 0 on each chip, reads back to identify variant
   - Detection sets a flag used by universal `selChip` routine

5. **6-channel music playback**:
   - Run two independent PT3 players, one per chip
   - Sequence: `CALL selChip1 / CALL player1 / CALL selChip0 / CALL player0`
   - **Critical**: Always select chip 0 after finishing TS operations (chip 0 is the
     one that produces sound on non-TS machines)

### Specific Ports, Registers, Timing

| Item | Value |
|------|-------|
| AY register select port | `#FFFD` |
| AY data write port | `#BFFD` |
| NedoPC chip 0 select | Write `#FF` to `#FFFD` |
| NedoPC chip 1 select | Write `#FE` to `#FFFD` |
| QUADRA chip 1 register port | `#EEFD` |
| QUADRA chip 1 data port | `#AFFD` |
| PoS chip select port | `#1F` |

### What's NEW vs Our Book

**Ch.11 (AY/TurboSound)** already covers TurboSound basics. What this article adds:

- **QUADRA variant** — entirely different port scheme (`#EEFD`/`#AFFD`), not mentioned in our book
- **PoS TurboSound** via port `#1F` — third hardware variant not covered
- **Auto-detection algorithm** — practical code to detect which TS variant is present at runtime
- **Universal chip selection** — single routine supporting all variants
- **"Always reset to chip 0"** rule — important production detail

### Notable Implementation Details Worth Reimplementing

- The auto-detection routine (write different values per chip, read back) is a practical
  pattern we should document in Ch.11 for real-world demo compatibility
- Universal `selChip` with XOR trick is elegant and compact

---

## 2. zg2mchow.txt — Multicolor: Complete Guide

**Author:** Alone Coder
**Source:** ZX-Guide #2, Ryazan, November 1999

### Key Techniques

Encyclopedic guide to multicolor modes on ZX Spectrum, covering everything from basic
per-line attribute changes to advanced dual-screen page-flipping techniques:

1. **Fundamental timing constants (Pentagon)**:
   - Frame = 71680 T-states
   - Scanline = 224 T-states
   - Total lines = 320 (304 visible: 64 top border + 192 screen + 48 bottom border)
   - T-states to top of screen area = 17920 (80 lines x 224 T)

2. **MC 1x8 (basic multicolor)**: one attribute change per 8-pixel row
   - POP-LD method: `POP HL / LD (nn),HL` pairs, 8 repetitions x 26T + 16T overhead = 224T per line
   - LDIR alternative: 13 x LDI = 208T + overhead (for 13 chars wide)

3. **MC 2x8**: two attribute changes per row (top and bottom halves of character cell)

4. **MC 4x8**: four attribute changes per row — practical limit for Pentagon

5. **MC24 (24-char wide multicolor)**:
   - Uses PUSH method + dual screen page switching
   - 144 bytes transferred in 1792 T-states = 12.4 T per byte
   - Screen page switching every 224 T via `OUT (C),D` / `OUT (C),E`
     with BC=`#7FFD`, D=31, E=23

6. **DeCrunch / Maker approach**: generates self-modifying code at runtime to produce
   exact timing for multicolor attribute updates — a form of JIT compilation for the Z80

7. **Enumeration of ~40 graphic modes**: MC, GREY, COL, OPT variants with different
   resolution/color tradeoffs

8. **Historical overview**: SuperCode (1983), Satisfaction (1994, CodeBusters),
   EYE ACHE (1996-97), and evolution of multicolor techniques

### Specific Ports, Registers, Timing

| Item | Value |
|------|-------|
| Pentagon frame length | 71680 T-states |
| Pentagon scanline | 224 T-states |
| Total lines | 320 (64 top border + 192 screen + 48 bottom + 16 vsync) |
| T to screen top | 17920 T (80 x 224) |
| POP HL | 10 T |
| LD (nn),HL | 16 T |
| LDI | 16 T |
| OUT (C),r | 12 T |
| Port #7FFD | Memory/screen page selection |
| Screen 0 value | 23 (bit 3 = 0) |
| Screen 1 value | 31 (bit 3 = 1) |
| MC24 throughput | 12.4 T per byte |

### What's NEW vs Our Book

**Ch.8 (multicolor)** covers beam racing, per-scanline attribute changes, IM2 setup.
What this article adds:

- **MC24 dual-page technique** — using `OUT (C),D` / `OUT (C),E` for page switching
  mid-scanline to achieve 24-char wide multicolor — NOT in our book
- **Maker/DeCrunch pattern** — runtime code generation for exact multicolor timing;
  this is a JIT-compilation technique our book doesn't cover
- **PUSH method** for attribute transfer — alternative to POP-LD, with different
  throughput characteristics
- **Comprehensive mode taxonomy** (~40 modes) — useful reference for classifying what
  different demos achieve
- **Exact T-state budget** per method (POP-LD, LDI, PUSH) with worked calculations

### Notable Implementation Details Worth Reimplementing

- MC24 page-flipping technique with OUT (C),D/E timing could be a standalone example
- The POP-LD multicolor loop is a clean, compilable example already close to what our
  Ch.8 examples do, but Alone Coder's cycle accounting is more rigorous
- The "Maker" concept (generate self-modifying code for per-frame attribute layout)
  is a powerful pattern applicable to demo engines (Ch.12)

---

## 3. sng1msnc.txt — Music Synchronization in Demos

**Author:** Flying/DR
**Source:** Scenergy #1, Novgorod, 1999

### Key Techniques

In-depth article on synchronizing visual effects with music in demos. Describes the
evolution from primitive methods to a full event-driven synchronization system:

1. **Method 1: Pattern-end sync** (simplest, most limited):
   - Extract "end of pattern" flag from music player
   - Change effect on pattern boundary
   - Limitations: linear only, code changes required to adjust timing

2. **Method 2: Interrupt counter** (frame counting):
   - Hang a counter on the interrupt handler, incrementing each frame
   - Match counter values to known note positions in music
   - Code example:
     ```
     LD DE,<target note index>
     LOOP: HALT
     LD HL,(NOTE_COUNTER)
     OR A
     SBC HL,DE
     JR NZ,LOOP
     ```
   - Limitations: linear sync only, code edits needed to adjust sync points,
     no parallel effect support

3. **Flying's event-driven sync system** (the article's main contribution):
   A complete "sync resident" architecture with three types of messages:

   **Sync table format**: each entry = `[word: counter_value] [byte: message_type]`

   **Message types**:
   - **M_SYNC** — synchronizing markers that accumulate (non-blocking). Effects call
     `WAIT_FOR_MARKER` (blocking) or `CHECK_FOR_MARKER` (non-blocking, returns CY flag).
     Markers are not lost if the effect hasn't polled yet.
   - **M_BEAT** — "beat" markers for screen flash/blink effects. Resident calls
     `_START_FLASH` handler on beat, then `_END_FLASH` after FLASH_SPEED interrupts.
     Border color auto-managed by resident.
   - **Custom** — arbitrary event markers with unique IDs. Calls user
     `ACTIONS_HANDLER` with message ID in register A. Multiple custom messages per
     interrupt supported (they accumulate within one frame).

4. **Resident architecture**:
   - Runs on every interrupt (IM2), performs these steps per frame:
     1. Increment interrupt counter
     2. Compare counter to current sync table entry
     3. If match: dispatch by message type (M_SYNC / M_BEAT / Custom)
     4. Process accumulated custom messages
     5. Check deferred function call table
     6. Play music
   - Must be called FIRST in the IM2 handler (before any screen effects) to avoid
     border color artifacts

5. **Deferred function calls** (`ADD_IM2_HANDLER`):
   - Schedule a procedure to be called N interrupts later
   - Input: HL = procedure address, A = number of interrupts to skip
   - Example: sprite drawing checks which screen page is visible, and if wrong page,
     defers itself by 1 interrupt:
     ```
     LD A,(PAGE)
     AND #08
     JR Z,...0
     LD HL,VIEW_SPRITE
     LD A,1
     CALL ADD_IM2_HANDLER
     RET
     ...0: ;draw sprite
     ```
   - Also used for timed sprite erasure (draw sprite, schedule erase N frames later)

6. **Demo system environment**:
   - Effect code is written with a "demo environment emulator" for standalone testing
   - Conditional compilation switches between standalone and integrated-demo modes
   - Portable effect architecture: effect + its sync pseudoprogram = complete module

7. **Interface variables**:
   - `IM2_HANDLER` — pointer to IM2 handler
   - `BEAT_START_FLASH` / `BEAT_END_FLASH` — flash start/end handlers
   - `FLASH_SPEED` — number of interrupts per flash
   - `BORDER` / `BEAT_BORDER` — default and flash border colors
   - `MARKERS_HANDLER` — custom message handler (receives ID in A)
   - `EXIT_SP` — saved SP for immediate effect exit via `LD SP,(EXIT_SP) / RET`

8. **Source code structure** (CC999 invitation dentro):
   - `RESIDENT.A` — resident code
   - `RES_EQUS.A` — equates for resident
   - Uses TASM v4.12 by RST7/CBS assembler (not directly portable to sjasmplus)

### Specific Ports, Registers, Timing

| Item | Value |
|------|-------|
| Port #7FFD bit 3 | Screen page select (0=page 5, 1=page 7) |
| IM2 handler | Called every frame (50 Hz on Pentagon) |
| Sync table entry | 3 bytes: word (counter) + byte (message code) |
| Frame counter | 16-bit, incremented each interrupt |

### What's NEW vs Our Book

**Ch.12 (demo engine, sync)** covers timeline sync and music players. What this
article adds:

- **Complete event-driven sync architecture** — our book describes basic timeline sync,
  but Flying's system is a full message-passing framework with typed events, marker
  accumulation, and deferred calls. This is significantly more sophisticated.
- **Three message types** (M_SYNC, M_BEAT, Custom) — our book doesn't differentiate
  sync event types
- **Non-blocking sync check** (`CHECK_FOR_MARKER` with CY flag) vs blocking wait
  (`WAIT_FOR_MARKER`) — useful API pattern not in our book
- **Marker accumulation** — markers are not lost if effect hasn't polled; prevents
  sync lockups on slower machines
- **Deferred function calls** — schedule-a-procedure-for-N-frames-later mechanism;
  powerful for dual-screen effects
- **Demo environment emulator** — standalone testing framework for effects; relevant
  to our Ch.12 demo engine architecture
- **EXIT via SP restore** — `LD (EXIT_SP),SP` pattern for immediate effect exit;
  elegant emergency-exit mechanism

### Notable Implementation Details Worth Reimplementing

- The complete sync resident (interrupt handler + sync table interpreter + deferred calls)
  is a production-grade demo engine core. Our "Antique Toy" demo could benefit from this
  architecture.
- `CHECK_FOR_MARKER` / `WAIT_FOR_MARKER` pair is a clean API for sync-aware effects
- Deferred call mechanism (`ADD_IM2_HANDLER`) solves the dual-screen-page problem
  elegantly and is reusable
- The sync table format (counter word + message byte) is compact and practical
- The "demo system environment" pattern (conditional compilation for standalone vs
  integrated mode) is excellent engineering practice

---

## 4. bd09gmcc.txt — AY Digital Sample Playback (MCC Method)

**Author:** UnBEL!EVER/Speed co. (first article) + MOn5+Er/Sage Group (second article)
**Source:** Born Dead #09, Samara, 1999 + Born Dead #0G, Samara, 2000

### Key Techniques

Two articles on the MCC (Mixed Channel Correction) method for playing digital audio
samples through the AY-3-8910 / YM2149F sound chip:

**Article 1 (UnBEL!EVER): Standard MCC player**

1. **MCC principle**: Use all 3 AY channels to synthesize DAC-like output levels.
   Two "edge" channels provide the main signal, center channel provides correction
   to achieve more amplitude levels than any single channel can produce.

2. **MCC lookup table**: 108 synthesized amplitude levels for YM2149F chip.
   - Center channel contributes ~52% of the mixed signal
   - Table indexed by sample byte value, produces 3 register values (one per channel)
   - Each table entry: 2 bytes (edge channel volumes packed) + implicit center value

3. **Standard playback loop** at 24305.556 Hz (24 KHz):
   - 144 T-states per sample byte
   - Main loop:
     ```
     MCC_PLY: LD E,(HL)       ; read sample byte
              LD A,(DE)       ; lookup table: edge channel
              EX AF,AF'
              DEC D
              LD A,(DE)       ; lookup table: center channel
              INC D
              EXX
              OUT (C),D       ; select AY register
              OUT (253),A     ; write center channel volume
              ...
     ```
   - Uses port 253 for fast single-byte AY data writes

4. **Playback rate constants** (delay between samples):
   - 24 KHz: 144 T per sample (standard, no extra delay)
   - 16 KHz: 80 T extra delay per sample
   - 11 KHz: 182 T extra delay
   - 8 KHz: 304 T extra delay

5. **Stereo layout matters**: ABC, ACB, or BAC mixer settings produce different center
   channel positioning. Wrong center channel identification ruins MCC quality.

**Article 2 (MOn5+Er): Super-fast MCC player**

6. **43.75 KHz playback** — 80 T per sample (nearly double the standard rate!):
   - Uses SP as sample data pointer: `POP HL` reads 2 bytes at once (10 T)
   - Processes 2 samples per loop iteration (160 T for 2 samples = 80 T each)
   - Loop control via `JP (IX)` (8 T, faster than `JP nn` at 10 T)
   - Key insight: POP reads 2 bytes in 10 T vs LD E,(HL)/INC HL at 11 T for 1 byte

7. **End-of-sample detection**:
   - Uses INT handler to check if playback finished
   - Sample pointer (SP) compared to end address
   - 896 bytes of silence padding required at end of sample (71680/80 = 896 frames per
     interrupt period)

8. **Limitations of super-fast variant**:
   - Cannot use stack during playback (SP is sample pointer)
   - Interrupts disabled during playback
   - Must pad sample with 896 bytes of silence

### Specific Ports, Registers, Timing

| Item | Value |
|------|-------|
| AY register select | Port `#FFFD` (BC=`#FFFD`) |
| AY data write | Port `#BFFD` (full) or port 253 (fast, low byte only) |
| OUT (C),r | 12 T |
| OUT (253),A | 11 T |
| Standard MCC rate | 24305 Hz (144 T/sample) |
| Super-fast MCC rate | 43750 Hz (80 T/sample) |
| MCC levels | 108 synthesized amplitudes |
| Center channel mix | ~52% of output |
| Silence padding | 896 bytes (for super-fast variant) |
| POP HL | 10 T (reads 2 bytes) |
| JP (IX) | 8 T |
| AY volume registers | R8 (ch A), R9 (ch B), R10 (ch C) |

### What's NEW vs Our Book

**Ch.12 (digital drums)** covers DAC-like AY tricks. What these articles add:

- **Complete MCC lookup table** with 108 levels — our book mentions the concept but
  this provides the actual production-ready table with exact volume values for YM2149F
- **Port 253 fast write** — using low byte of `#BFFD` for faster single-byte AY data
  output (11 T vs 12 T for OUT (C),r). Not mentioned in our book.
- **Super-fast 43.75 KHz technique** using SP as data pointer — pushes AY sample
  playback to near-CD quality by repurposing the stack pointer. This is a significant
  technique not in our book.
- **896-byte silence padding** requirement — practical detail for the SP-based player
- **Stereo layout dependency** — which physical channel is "center" depends on mixer
  wiring; must be identified correctly for MCC. Not discussed in our book.
- **Delay tables for multiple rates** (8/11/16/24 KHz) — practical reference for
  rate selection

### Notable Implementation Details Worth Reimplementing

- The standard 24 KHz MCC player loop is compact and could be a Ch.12 example
- The super-fast variant (SP as pointer, JP (IX) loop) is a masterclass in cycle
  optimization — excellent material for demonstrating extreme T-state squeezing
- The MCC lookup table (108 levels from 3 channels) should be referenced or included
  as a data appendix
- Port 253 fast-write trick is worth a sidebar in Ch.11 or Ch.12

---

## 5. zf6mlclr.txt — Making Multicolors

**Author:** MIK / VIRT GROUP
**Source:** ZX Format #6, St. Petersburg, 30.07.1997

### Key Techniques

Step-by-step tutorial on implementing basic multicolor on ZX Spectrum:

1. **Multicolor procedure structure**:
   - Wait for INT (HALT)
   - Delay to reach screen scan area
   - Wait for ULA to read attributes from specific position
   - Replace attributes with new values
   - Pad timing to exactly 224 T per scanline
   - Repeat for each line

2. **IM2 setup for beam racing**:
   - Fill 257-byte table with vector address high byte
   - Set I register to table page
   - Place RET instruction at vector target (`#BFBF`)
   - `LD A,#BE / LD I,A / IM 2`

3. **Attribute transfer via LDI**:
   - 6 x LDI for 6 characters wide = 96 T
   - Remaining time filled with NOPs and timing padding: `LD DE,0` (10T) + `DS 23,0`
     (23 x 4 = 92T) to reach 224T total

4. **Scorpion timing adjustment**: different T-state counts for Scorpion vs Pentagon,
   requiring timing tuning per machine

### Specific Ports, Registers, Timing

| Item | Value |
|------|-------|
| Scanline | 224 T (most machines) |
| LDI | 16 T |
| LD DE,0 | 10 T (timing pad) |
| NOP | 4 T |
| IM2 vector table | 257 bytes, e.g. at `#BE00`-`#BF00` |
| IM2 handler address | `#BFBF` (place RET there) |
| Attribute area start | `#5800` |

### What's NEW vs Our Book

**Ch.8 (multicolor)** covers beam racing and IM2 setup. This article is more basic
than our existing coverage but offers:

- **Step-by-step build-up** from first principles — useful for verifying our Ch.8
  pedagogy covers the same ground
- **Scorpion-specific timing** — our book focuses on Pentagon; Scorpion timing
  differences are not covered
- **Concrete LDI-based multicolor** with exact T-state budget — a clean alternative to
  the POP-LD method that could be a secondary example

### Notable Implementation Details Worth Reimplementing

- The LDI-based multicolor is simpler than POP-LD and could work as a "starter"
  example before the more complex approaches in Ch.8
- IM2 setup with `#BFBF` as RET address is a common pattern worth documenting as
  the standard approach

---

## 6. zf5bordr.txt — Border Effects

**Author:** MIK
**Source:** ZX Format #5, St. Petersburg, 12.12.1996

### Key Techniques

Tutorial on creating visual effects in the ZX Spectrum border area:

1. **ULA border rendering**:
   - ULA reads port `#FE` bits 0-2 for border color
   - Every 4 T-states: 8 pixels formed in the shift register
   - Pentagon: border pixels read individually from `#FE` (unlike screen area where
     data/attributes are interleaved)

2. **Horizontal stripes**:
   - `OUT (#FE),A` with different values for each scanline
   - Pad to 224 T per line using NOPs and DJNZ
   - Example: `OUT (#FE),A / NOP / NOP / ... / DJNZ`

3. **Vertical stripes** (the hard technique):
   - Alternating `OUT (C),D / OUT (C),E` = 12 T each
   - 16 OUT pairs = 192 T of stripe data per line
   - Overhead: 3 NOPs (12T) + DEC A (4T) + JR NZ (12T) = 28T
   - Total: 192 + 28 = 220T per line (close to 224T scanline)
   - BC = `#00FE` (port #FE), D and E hold two alternating colors

4. **Phase alignment after HALT**:
   - HALT returns at an unpredictable T-state within a 4T window
   - To align to non-4T boundaries, use instructions with non-4T durations:
     - `LD A,(nn)` = 13 T
     - `DEC DE` = 6 T
     - `ADC A,(HL)` = 7 T
   - Combining these gives exact phase control

5. **Pentagon vs other machines**:
   - Pentagon: 320 lines x 224 T = 71680 T per frame, 50 Hz
   - Scorpion and original 48K have different line counts (312) and timings (220 T)

### Specific Ports, Registers, Timing

| Item | Value |
|------|-------|
| Border color port | `#FE` (bits 0-2) |
| OUT (#FE),A | 11 T |
| OUT (C),r | 12 T |
| Pentagon frame | 71680 T (320 lines x 224 T) |
| Scorpion/48K frame | ~69888 T (312 lines x ~224 T) or 312 x 220 |
| NOP | 4 T |
| DEC A | 4 T |
| JR NZ,nn | 12 T (taken) / 7 T (not taken) |
| LD A,(nn) | 13 T (for phase alignment) |
| DEC DE | 6 T (for phase alignment) |
| ADC A,(HL) | 7 T (for phase alignment) |
| Vertical stripe pair | OUT (C),D + OUT (C),E = 24 T for 2 color columns |

### What's NEW vs Our Book

**Ch.8** doesn't explicitly cover border effects (it focuses on screen-area multicolor).
This article provides:

- **Border effects as a separate technique** — our book's beam racing is screen-focused;
  border-area effects use different timing constraints (no attribute interleaving)
- **Phase alignment tricks** — using non-4T instructions to align to exact T-state phase
  after HALT. This is a subtle timing technique not explicitly covered.
- **Vertical stripe timing** — alternating OUT (C),D / OUT (C),E at 12T each for
  maximum color resolution in the border
- **Pentagon vs Scorpion vs 48K timing differences** — comparative timing data

### Notable Implementation Details Worth Reimplementing

- The vertical stripe routine (OUT (C),D / OUT (C),E alternation) is a clean,
  self-contained example suitable for a sidebar in Ch.8
- Phase alignment after HALT (using 13T/6T/7T instructions) is a generally useful
  technique for any beam-racing code — worth adding as a tip
- The distinction between border rendering (individual pixel reads) and screen rendering
  (interleaved reads) clarifies ULA behavior

---

## 7. flt1ayfq.txt — AY Frequency Divider Table

**Author:** Amadeus Voxon / FLASH
**Source:** Flash Time #1, Novosibirsk, 1997

### Key Techniques

Reference article providing the mathematical basis for AY-3-8910 note frequency
calculations:

1. **AY frequency formula**:
   - `F(note) = F(tact) / 12 / Const`
   - Therefore: `Const = F(tact) / 12 / F(note)`
   - Where `F(tact)` = 1,750,000 Hz (AY clock frequency on ZX Spectrum)
   - The divider is 12 because 12 bits of the tone period register are used
     (actually /16, but the formula as given is for the TP register value)

2. **Complete note frequency table** for 8 octaves:
   - C1 = 32.70 Hz through B8 = 7901.4 Hz
   - All 12 chromatic notes per octave

3. **Key advice: ROUND, don't truncate**:
   - When computing the divider constant, rounding to nearest integer gives better
     pitch accuracy than truncating
   - The author criticizes Sound Tracker and ASM tracker editors for using inaccurate
     note tables due to truncation

4. **Implied register format**: AY tone period = 12-bit value in register pairs
   (R0/R1 for channel A, R2/R3 for B, R4/R5 for C), low byte first

### Specific Ports, Registers, Timing

| Item | Value |
|------|-------|
| AY clock (ZX Spectrum) | 1,750,000 Hz |
| Tone period registers | R0/R1 (ch A), R2/R3 (ch B), R4/R5 (ch C) |
| Tone period range | 0-4095 (12-bit) |
| C1 frequency | 32.70 Hz |
| A4 (concert pitch) | 440.0 Hz |
| C8 frequency | 4186.0 Hz |

### What's NEW vs Our Book

**Ch.11 (AY registers)** covers tone generation basics. This article adds:

- **Exact formula for computing divider constants** — if our book provides a note table,
  this article explains how to derive it from first principles
- **Rounding vs truncation** — practical advice for accurate note tables that our book
  should mention
- **Complete 8-octave reference table** — useful as a data reference or appendix
- **Critique of existing trackers** — historical context showing that even popular music
  editors had inaccurate tuning

### Notable Implementation Details Worth Reimplementing

- The note frequency table (or the formula to generate it) should be in our Ch.11 or
  in Appendix I (AY-beat)
- The rounding advice is a one-line tip worth including: "Always round the divider
  constant to the nearest integer"

---

## Summary: Priority Items for Book Integration

### High Priority (significant new content)

1. **Flying's sync system** (sng1msnc) — event-driven sync architecture with typed
   messages, marker accumulation, and deferred calls. Substantially enriches Ch.12's
   demo engine coverage.

2. **MCC digital sample playback** (bd09gmcc) — complete 108-level DAC emulation
   via 3 AY channels, plus the super-fast 43.75 KHz variant using SP as pointer.
   Critical addition to Ch.12's digital drums section.

3. **MC24 dual-page multicolor** (zg2mchow) — page-flipping mid-scanline for 24-char
   wide multicolor. Extends Ch.8 beyond basic beam racing.

4. **TurboSound variants** (ig8tsprg) — QUADRA and PoS hardware variants plus
   auto-detection. Completes Ch.11's TurboSound coverage.

### Medium Priority (useful additions)

5. **Border effects** (zf5bordr) — vertical stripes and phase alignment. Good sidebar
   material for Ch.8.

6. **AY frequency formula** (flt1ayfq) — derivation of note tables from first
   principles. Sidebar for Ch.11 or Appendix I.

7. **Maker/DeCrunch JIT code generation** (zg2mchow) — runtime code generation for
   multicolor. Advanced technique for Ch.8 or Ch.12.

### Low Priority (confirms existing coverage)

8. **Basic multicolor tutorial** (zf6mlclr) — step-by-step LDI-based multicolor.
   Validates our Ch.8 pedagogy, minor additions only (Scorpion timing).
