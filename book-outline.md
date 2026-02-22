# Coding the Impossible
## Z80 Demoscene Techniques for Modern Makers

> *From inner loops to AI-assisted development — a practical guide to pushing 8-bit hardware to the limit*

---

## Concept

A book that bridges two worlds: the hard-won wisdom of ZX Spectrum demoscene coders and the modern toolchain (VS Code, AI assistants, eZ80 hardware like Agon Light 2). Not a nostalgia trip — a *living* technical book where every technique is explained, every example compiles, and readers can run everything on real or emulated hardware.

**Target audience:** Retro-computing enthusiasts who want to go deeper than BASIC. Modern embedded developers curious about extreme optimisation. Demosceners who want their knowledge documented before it's lost. Game developers targeting ZX Spectrum or Agon Light 2.

**Key differentiator:** Every chapter follows the pattern: *idea → constraint → trick → working code → "try it yourself"*. Source code for all examples on GitHub. Real demos, real code, real people explaining their real thought processes.

**Target platforms:**

| Platform | CPU | Clock | RAM | Graphics | Sound |
|----------|-----|-------|-----|----------|-------|
| ZX Spectrum 128K (+ clones) | Z80A | 3.5 MHz (7 MHz turbo on clones) | 128KB (banked) | ULA, 256×192, 8×8 attributes | AY-3-8910 (TurboSound: 2×AY, Next: 3×AY) |
| Agon Light 2 | eZ80 | 18.432 MHz | 512KB flat | VDP (ESP32 + FabGL) | ESP32 audio |

**Primary platform:** ZX Spectrum 128K — maximum depth, all demoscene chapters. Agon Light 2 — cross-platform practicals in game-dev chapters, dedicated porting chapter.

---

## Introduction

- **Manifesto**: two platforms, not twenty — depth over breadth
- The learning pair: Spectrum = hard constraints + bare metal; Agon = Z80 evolution without legacy shackles
- **The X-Trade Thread**: Dark from X-Trade wrote Spectrum Expert algorithm articles (1997–98) AND coded Illusion. Introspec reverse-engineered Illusion's inner loops on Hype in 2017. We have *both sides* — 20 years apart. This narrative thread runs through the whole book.
- How to read: demoscene path (Parts I–IV) vs game-dev path (Parts I, V–VI) vs follow everything
- **Introspec's maxim**: "coder effects are always about evolving a computation scheme"

---

## Part I: The Machine and the Mindset

### Chapter 1: Thinking in Cycles
- The Z80 programmer's worldview: everything is a budget
- T-states, machine cycles, and why they matter
- Pentagon vs. wait machines: why cycle counts differ
- The frame budget: 69,888 T-states (48K) vs 71,680 (Pentagon) — your canvas
- **Agon sidebar**: Agon frame budget (~368,000 T-states) — same Z80 instruction set, 5× the room
- **Practical:** Set up VS Code + Z80MacroAsm boilerplate (sq's Hype guide + zxboilerplate template)
- **Practical:** Write a "how fast is this?" timing harness with border colour
- **Historical note:** Dark/X-Trade from Spectrum Expert #01: "read a maths textbook — derivatives, integrals"

> **Sources:** sq "VS Code + Z80MacroAsm" (Hype 2019), aGGreSSor VS Code guide (Hype 2026)

### Chapter 2: The Screen as a Puzzle
- ZX Spectrum video memory layout: the weird interleave and why it exists
- Why rows go $4000, $4100, $4200… → $4020, $4120… — historical reason and practical consequences
- Attribute memory: 768 bytes that changed everything — INK, PAPER, BRIGHT, FLASH
- The border: not just decoration — a timing-visible debug tool (OUT $FE)
- DOWN_HL: moving the screen pointer one pixel row down — from 5,922 to 2,343 cycles (Introspec + RST7's elegant dual-counter solution)
- **Agon sidebar**: VDP modes (bitmap, sprites, tiles) — different paradigm, same CPU family
- **Practical:** Fill the screen, fill the attributes, make a border stripe — Spectrum + Agon

> **Sources:** Introspec "DOWN_HL" (Hype 2020), Introspec "GO WEST Part 1" contended memory (Hype 2015)

### Chapter 3: The Demoscener's Toolbox
- Unrolled loops and self-modifying code
- The stack as a data pipe: PUSH/POP tricks for fast screen output
- LDI chains and why `ldi` is everyone's best friend
- Code generation: when your program writes the program that draws the screen
- RET-chaining: set SP to render list, each procedure ends with RET popping next address (DenisGrachev's tile engines in Dice Legends)
- **Sidebar:** Introspec's "Code is Dead" — code only lives when people read it in debuggers

> **Sources:** DenisGrachev "Tiles and RET" (Hype 2025), Introspec "Code is Dead" (Hype 2015)

### Chapter 4: The Maths You Actually Need
> *Based on Dark/X-Trade's legendary Spectrum Expert #01 articles — the same Dark who coded Illusion*

**Multiplication on Z80** (from SE#01)
- Method 1: shift-and-add from LSB — `RR C : JR NC,$+3 : ADD A,B : RRA` loop
- 8×8→16 in 196–204 T-states, 16×16→32 in 730–826 T-states
- Method 2: square table lookup — `A*B = ((A+B)²-(A-B)²)/4`, 61 T-states with accuracy trade-off
- **Practical:** Build both multipliers, compare outputs, see the vertex jitter

**Division on Z80** (from SE#01)
- Shift-and-subtract: restoring division. 8/8 in 236–244 T-states, 16/16 in 938–1034 T-states
- Logarithmic division: `Log(A/B) = Log(A) - Log(B)` with 256-byte tables
- Dark's "method of guessing" the 0.4606 correction coefficient — honest maths

**Sine and Cosine** (from SE#01)
- The parabolic approximation: `Y ≈ X²` mimics a half-period of sine
- Generating a 256-byte signed cosine table in a tight loop
- **Sidebar:** Raider's "9 commandments" of sine tables (from the Hype comments on Illusion article)

**Bresenham's Line** (from SE#01)
- Classic algorithm → Xopha modification → why both are too slow
- Dark's matrix method: 8×8 pixel grids with SET x,(HL), ~48 cycles/pixel
- "87.5% of checks are wasted" — the insight that drives the optimisation
- **Practical:** Draw lines fast enough for wireframe 3D

**Fixed-point arithmetic** (needed for game-dev chapters too)
- Format 8.8: integer + fractional in one 16-bit word
- Add/sub: free (normal 16-bit ops). Multiply 8.8×8.8: ~200 cycles on Z80

> **Sources:** Dark/X-Trade Spectrum Expert #01 "Programming Algorithms" (1997)

### Chapter 5: 3D on 3.5 MHz
> *Based on Dark & STS's Spectrum Expert #02*

**The Midpoint Method** (from SE#02)
- The problem: 12 multiplications per vertex × N vertices = pain
- The trick: compute only a cube, derive all other vertices by averaging
- Virtual processor with 4 commands: Load, Store, Average, End
- Writing "programs" for vertex interpolation: `DB 4,128!5,64!8`

**Solid Polygons** (from SE#02)
- Backface culling via normal Z-component: `Vx*Wy - Vy*Wx`
- Convex polygon filling, Z-sorting for complex objects

**Historical context:** These articles are from 1997–1998. The same team (X-Trade) released Illusion around this time. The algorithms in the magazine are the building blocks of the demo.

- **Practical:** A spinning 3D solid object using midpoint vertex generation

> **Sources:** Dark & STS "Programming" (Spectrum Expert #02, 1998)

---

## Part II: Classic Effects Deconstructed

> *Each chapter takes a real demo, explains the effect, shows the inner loop, counts the cycles, and provides a buildable version.*

### Chapter 6: The Sphere — Texture Mapping on 3.5 MHz
- **Source demo:** Illusion by X-Trade (ENLiGHT'96, 1st place)
- Byte-per-pixel source → bit-packed sphere via dynamically generated unrolled loops
- The inner loop: `add a : add (hl)` with variable `inc l` skips
- Lookup tables at #6944 for pixel skip distances
- 101+32x T-states per byte — why it fits in one frame
- **Practical:** Build a 56×56 spinning sphere
- **Sidebar:** The Hype debate — kotsoft and Introspec arguing about inner loops vs maths

> **Sources:** Introspec "Technical Analysis of Illusion" (Hype 2017) — sphere section

### Chapter 7: Rotozoomer and Chunky Pixels
- **Source demo:** Illusion by X-Trade
- Walking through a texture at an angle: `ld a,(hl) : inc l : dec h : add a : add a : add (hl)`
- 2×2 chunky pixels: storing #03 or #00 in a byte
- Per-frame code generation: recalculating the walk direction
- 95 T-states per 4 chunks → 4–6 frames per screen
- **Deep dive: 4×4 chunky pixels** — sq's optimization from 101 to 76 cycles/pair via self-modifying 256-variant procedures (based on Born Dead #05)
- **Practical:** Build a simple rotozoomer with sine-table movement

> **Sources:** Introspec "Illusion analysis" (Hype 2017) — rotozoomer section; sq "Chunky effects on ZX Spectrum" (Hype 2022)

### Chapter 8: Multicolor — Breaking the Attribute Grid
- **Source:** DenisGrachev's Old Tower and GLUF game engines
- The LDPUSH technique: `ld de, 2-byte-data : push de` generates executable display code
- Data written backwards due to stack pointer mechanics, 51 bytes per scanline
- GLUF: 8×2 multicolor, 24×16 char area, double-buffered, ~70,000 cycles per frame
- Two-frame architecture: Frame 1 = attributes + tiles, Frame 2 = remaining tiles + sprites
- **Ringo Render 64×48**: "11110000b" pattern, screen switching every 4 scanlines, half-character scroll
- **Sidebar:** Black Crow #05 multicolor article with algorithm and example code (from ZXArt)
- **Practical:** A multicolor game screen with moving sprites

> **Sources:** DenisGrachev "Multicolor Will Be Conquered" (Hype 2019); DenisGrachev "Ringo Render 64×48" (Hype 2022); Black Crow #05 (ZXArt)

### Chapter 9: Attribute Tunnels and Chaos Zoomers
- **Source demo:** Eager by Introspec/Life on Mars (2015)
- Pseudo-chunky attributes: variable-size "pixels" hiding low centre resolution
- Plasma-based tunnel with 4-fold symmetry: `ld a,(hl) : ld (nn),a : ld (mm),a : ld (bc),a : ldi`
- Chaos zoomer via unrolled `ld hl,nn : ldi`
- Code generation in Processing → Z80 assembly
- **Sidebar:** "Zapilator" — the love-hate relationship with precalculation
- **Practical:** An attribute tunnel with reflection symmetry

> **Sources:** Introspec "Making of Eager" (Hype 2015); Eager file_id.diz (extracted)

### Chapter 10: The Dotfield Scroller and 4-Phase Colour
- **Source demo:** Illusion (scroller) + Eager (4-phase)
- Scroller inner loop: `ld a,(bc) : pop hl : rla : jr nc,$ : set ?,(hl)` — 36 T-states/pixel
- Stack-based address tables for bouncing motion
- 4-phase colour animation: 2 normal + 2 inverted frames → palette shift illusion
- **Practical:** A bouncing dot-matrix scroller + a 4-phase cycling demo

> **Sources:** Introspec "Illusion analysis" (Hype 2017) — scroller section; Introspec "Making of Eager" (Hype 2015) — 4-phase section

---

## Part III: Sound Meets Screen

### Chapter 11: Sound Architecture — AY, TurboSound, and Triple AY
- **AY-3-8910 deep dive:** All 14 registers, envelope shapes (10 unique forms with oscillograms), noise generator
- Ports $FFFD/$BFFD, frequency formula: freq = clock / (16 × period)
- Mixer register R7 — the most important register: 6 bits controlling tone on/off + noise on/off per channel. Table of all useful combinations
- **Chiptune techniques on 3 channels:** arpeggios, buzz-bass, drum synthesis via noise+envelope, ornaments, portamento
- **TurboSound (2×AY):** addressing two AY chips on clones (Pentagon, Scorpion, etc.). Port $FFFD bit scheme for chip select. 6 channels, true stereo. What it changes musically — bass+lead+drums without compromise
- **Triple AY on ZX Spectrum Next:** 3×AY = 9 channels. Next's enhanced AY with per-channel stereo panning. How compositions change with 9 voices — orchestral thinking on 8-bit
- **Music engine architecture:** IM2 interrupt handler → read pattern → update AY registers. Frame budget: how many cycles you can spend in interrupt before main loop starves
- **Formats and trackers:** Vortex Tracker II (.pt3), Pro Tracker 3 (.pt3), ASC Sound Master — which format when. Conversion pipeline: VT2 → .pt3 → embed in binary
- **Sound effects system:** Priority-based channel stealing — SFX temporarily hijacks a channel, returns to music after. Procedural SFX tables: explosion (noise+decay), laser (sweep down), jump (sweep up), pickup (arpeggio up)
- **Sidebar: Beeper — a brief history of impossibility.** Shiru's catalog of ~30 engines (2010–2015): from 1-bit to 16-channel polyphony (ZX-16 by Jan Deak). Octode XL in Rain demo — 9 channels on 48K beeper. An astonishing engineering feat, covered here as context, not as primary technique.
- **Agon sidebar:** VDP sound system — waveforms, ADSR envelopes, MIDI-like approach. Different paradigm, same musical goals
- **Practical:** AY sound tester with real-time register visualisation + 3-channel melody with noise drums

> **Sources:** Dark "GS Sound System" (SE#01, 1997); Dark "Music" (SE#02, 1998); Shiru "Beeper 20XX" (Hype 2016); Rain file_id.diz (extracted); Info Guide #14 ASC Sound Master docs (ZXArt 2024)

### Chapter 12: Digital Drums and Music Sync
- **Source demo:** Eager by Introspec
- Digital samples blended with AY: n1k-o's insight (digital attack + AY decay = convincing hybrid)
- Frame budgeting with drums: 2 frames per hit, async video generation
- Double-buffered attribute frames: prepare 2 pages, play drum, flip
- **Scripting engine:** Two-level: outer (effects) + inner (variations). kWORK command: generate N frames, show independently
- Async generation: falling behind during drums, catching up between hits
- **GABBA's innovation:** Luma Fusion (iOS video editor) for 50fps timeline editing, frame-level sync with n1k-o's track
- Robus's Z80 threading: IM2-based context switching, SwitchThread procedure, dedicated stacks per thread (used in WAYHACK demo)
- **Practical:** A minimal scripted demo engine with 3 effects, music sync, and a digital kick drum

> **Sources:** Introspec "Making of Eager" (Hype 2015); diver4d "Making of GABBA" (Hype 2019); Robus "Threads on Z80" (Hype 2015)

---

## Part IV: Size-Coding and Compression

### Chapter 13: The Craft of Size-Coding
- Anatomy of a 256-byte intro: NHBF by UriS — looped square wave power chords + random pentatonic notes, "playing puzzle-like games" with optimization
- Every byte counts: overlapping code and data, register values from screen clear matching text length
- 512-byte intro: structure, self-modifying tricks for extreme compression
- **LPRINT trick** (diver4d): redirect printer output to screen memory, data reorders through 8 states — from pirated cassette loaders to demo art
- **Practical:** Write a 256-byte intro step by step

> **Sources:** UriS "NHBF Making-of" (Hype 2025); diver4d "LPRINT Secrets" (Hype 2015)

### Chapter 14: Compression — More Data in Less Space
- Introspec's comprehensive benchmark of 10 compressors for Z80:
  - Exomizer: 48.31% ratio, ~250 cycles/byte
  - ApLib: 49.18%, ~105 cycles/byte, 199-byte decompressor
  - Pletter 5: 51.52%, ~75 cycles/byte
  - LZ4: 58.55%, ~34 cycles/byte (>2KB per frame!)
  - ZX7: decent ratio, 69-byte decompressor
- Key insight: "Compression acts as a method to increase effective memory bandwidth"
- ZX0 on Z80 (~70 bytes decompressor)
- RLE and delta-coding for tilemaps and sprite animations
- **Break Space**: 122 frames compressed into 10KB — compression in practice
- **Practical:** Build compression into your Makefile pipeline: PNG → converter → compress → embed → decompress at load

> **Sources:** Introspec "Data Compression for Modern Z80 Coding" (Hype 2017); Break Space file_id.diz (extracted)

---

## Part V: Game Development

> *Cross-platform: every chapter has ZX Spectrum (primary) and Agon Light 2 implementations.*

### Chapter 15: Anatomy of Two Machines
- **ZX Spectrum 128K:** Full memory map, banking ($7FFD), contended memory (practical note, not drama), ULA timing
- **Clone differences:** Pentagon (71,680 T-states, 7 MHz turbo), Scorpion (256KB, GMX 320×200×16), ZX Next (MMU, Layer 2, hardware sprites, Copper, DMA)
- **Agon Light 2:** 24-bit flat memory, MOS API, dual-processor (eZ80 ↔ ESP32), ADL-mode vs Z80 mode
- **Contended memory details:** Introspec's GO WEST — penalty ~0.92 cycles/byte random, ~1.3 for stack; zero during border. Floating bus sync, #7FFD reading bug, ULA snow.
- **Practical:** Memory inspector utility — Spectrum + Agon

> **Sources:** Introspec "GO WEST Parts 1–2" (Hype 2015)

### Chapter 16: Fast Sprites
**ZX Spectrum — six methods, simple to extreme:**
1. XOR sprites: 20 lines, for cursors and bullets
2. OR+AND masked sprites: industry standard, full cycle-counted code
3. Pre-shifted sprites: 4 or 8 shifted copies, memory vs speed trade-off
4. Stack sprites (PUSH method): DI → save SP → PUSH chain → restore SP → EI — fastest output
5. Compiled sprites: sprite = executable code, each pixel byte is `LD (HL),n`
6. Dirty rectangles: track changed areas, save/restore background

**Agon:** Hardware VDP sprites (VDU 23,27,...), limits per scanline

- **Practical:** 8 animated 16×16 sprites with background save/restore, target 25 fps — Spectrum + Agon

### Chapter 17: Scrolling
**ZX Spectrum:**
- Vertical pixel scrolling: full algorithm with interleaved memory, cost analysis
- Horizontal scrolling: RLC/RRC chains per byte — expensive, full budget calculation
- Attribute (character) scrolling: cheap 8-pixel jumps via LDIR
- Combined: character scroll + pixel offset within 8px window
- Shadow screen trick: draw next frame in bank 7, flip

**Agon:** Hardware scroll offsets, tilemap scrolling, ring-buffer column loading

- **Practical:** Horizontal side-scrolling level — combined method on Spectrum, hardware tiles on Agon

### Chapter 18: Game Loop and Entity System
- **Main loop:** HALT → Input → Update → Render → repeat
- Frame budget: Spectrum ~70K T-states, Agon ~368K
- **State machine:** table of handler pointers (Title → Menu → Game → Pause → GameOver)
- **Input:** Keyboard half-rows (IN A,($FE)), Kempston joystick, Agon PS/2 keyboard
- **Entity structure:** X (16-bit fixed), Y, type, state, anim_frame, dx, dy, health, flags
- **Entity array:** static allocation, iterate, activate/deactivate via flag
- **Object pool:** reuse slots for bullets, particles, effects
- **Practical:** Game skeleton with state machine, 16 entities (player, 8 enemies, 7 bullets) — Spectrum + Agon

### Chapter 19: Collisions, Physics, and Enemy AI
**Collisions:**
- AABB: 4 comparisons with early exit
- Tile collisions: entity coords → tile index → type check (passable/wall/hazard)
- Sliding collision response: push out on one axis, slide on other

**Physics:**
- Gravity: velocity_y += gravity (fixed-point, every frame)
- Jump: velocity_y = -jump_force
- Friction: velocity_x >>= 1 (shift right = divide by 2)

**Enemy AI:**
- FSM: Patrol → Chase → Attack → Retreat → Death
- Patterns: patrol between points, chase player (sign of dx), ambush, shoot, flee
- Optimisation: update AI every 2nd or 3rd frame

- **Practical:** Platformer physics + 4 enemy types — Spectrum + Agon

---

## Part VI: Putting It All Together

### Chapter 20: Demo Workflow — From Idea to Compo
- Introspec's design philosophy: "Design = complete aggregate of all demo components, both visible and concealed"
- **Lo-Fi Motion workflow** (restorer): scene table system, 14 effects, virtual 1-byte-per-pixel buffers, sjasmplus + BGE + Ruby scripts + hrust1opt, built in 2 weeks of evenings, source on GitHub
- **Making-of culture:** from Eager (detailed technical writeup in NFO) to GABBA (iOS video editor for sync) to NHBF (256 bytes, "puzzle-like games")
- **Tools:** sjasmplus, BGE, Photoshop, Ruby/Processing scripts, Makefile, CI
- **Compo culture:** Multimatograf, DiHalt, Chaos Constructions, CAFe, Revision
- How to enter your first compo
- The community: Hype, ZXArt, Pouet
- **Introspec's "MORE"**: "Two pixels suffice to tell a story" — transcend platform limitations

> **Sources:** restorer "Making of Lo-Fi Motion" (Hype 2020); Introspec "For Design" (Hype 2015); Introspec "MORE" (Hype 2015)

### Chapter 21: Full Game — ZX Spectrum 128K
- Genre: side-scrolling platformer (5 levels, 4 enemy types, boss)
- Integration: renderer + scrolling + sprites + physics + collisions + AI + music + SFX
- Bank usage: levels/graphics in banks 0–3, music/SFX in 4–6, shadow screen in 7
- Loading from tape or DivMMC (esxDOS: RST $08, F_OPEN, F_READ, F_CLOSE)
- Loading screen, menu, high scores
- Profiling in DeZog, finding bottlenecks, final polish
- Release format: .tap with loader

### Chapter 22: Porting — Agon Light 2
- Same game, different architecture — same Z80 ISA, completely different constraints
- Agon: hardware sprites + tilemap scrolling + SD loading, no memory pressure, 24-bit addressing
- ADL-mode vs Z80-compatible mode: when to use which, switching pitfalls
- eZ80 @ 18 MHz: what Spectrum tricks still matter (inner loop efficiency), what becomes irrelevant (memory conservation)
- **Comparison table:** code size, fps, resource size, dev complexity, visual result (screenshots side by side)
- What each platform forces you to do better

### Chapter 23: AI-Assisted Z80 Development
- Claude Code and the feedback loop: write → assemble → emulate → debug → iterate
- DeZog integration: automated debugging with breakpoints and memory inspection
- When AI helps (iteration, boilerplate, test generation) vs when it doesn't (novel optimisation)
- **Case study:** Building MinZ — a Z80 programming language with AI assistance
- **Honest take:** Introspec says "Z80 they still don't know" — where are the real limits?
- **Historical parallel:** HiSoft C on ZX Spectrum (SE#02): "10–15× faster than BASIC" but no floats. Higher-level languages on constrained hardware have always been a compromise.

> **Sources:** HiSoft C review (Spectrum Expert #02, 1998)

---

## Appendices

### A: Z80 Instruction Reference with Cycle Counts
- Sorted by use case (output, calculation, flow control)
- Pentagon vs 48K timing differences
- The border timing table: `out` at 11 vs 12 T-states (with the full Hype thread story)

### B: Sine Table Generation and Trigonometric Tables
- 256-byte sine table, fixed-point arithmetic on Z80
- Raider's method: H = table base, L = argument, rotate L freely
- Dark's parabolic approximation from SE#01
- Log/antilog tables for fast division (Dark's derivative-based generation)

### C: Data Compression Quick Reference
- Comparison table from Introspec's benchmark (10 compressors, ratio/speed/size)
- ZX0/ZX7 decompressor listings for Z80

### D: Development Environment Setup
- VS Code + Z80MacroAsm + SjASMPlus + DeZog
- Emulators: Fuse, Unreal Speccy, Spectaculator, ZXMAK2 — and why they all sound different
- Agon: ez80asm, MOS API, serial loading
- Makefile for two targets, CI via GitHub Actions

### E: eZ80 Quick Reference
- New instructions and addressing modes
- ADL mode, 24-bit addressing
- Agon MOS API basics, VDP command reference

### F: ZX Spectrum Clone Memory Maps
- Pentagon 128/512/1024, Scorpion ZS-256, Profi, ATM Turbo 2+, ZX Next
- Port tables, banking schemes, special capabilities (GMX, Copper, DMA)

### G: AY-3-8910 / TurboSound / 3×AY Register Reference
- All 14 registers with bit maps and oscillograms for all envelope shapes
- TurboSound: chip select addressing, stereo channel assignment
- ZX Next triple AY: per-channel stereo panning registers, extended addressing
- Frequency table: all notes × all octaves → register values

### H: DivIDE/DivMMC and esxDOS API Reference
- Automapping, RST $08 calls, file operations

---

## Source Materials & Status

| Material | Status | Source |
|----------|--------|--------|
| Illusion inner loops + cycle analysis | ✅ Fetched | Introspec, Hype 2017 |
| Eager making-of + design process | ✅ Fetched | Introspec, Hype 2015 |
| Dark/X-Trade: Algorithms (mult, div, sin, line) | ✅ Fetched | Spectrum Expert #01, ZXArt |
| Dark/X-Trade: 3D graphics + midpoint method | ✅ Fetched | Spectrum Expert #02, ZXArt |
| Dark/X-Trade: HiSoft C/Pascal review | ✅ Fetched | Spectrum Expert #02, ZXArt |
| Dark/X-Trade: GS Sound System | ✅ Fetched | Spectrum Expert #01, ZXArt |
| DenisGrachev: Multicolor / LDPUSH technique | ✅ Fetched | Hype 2019 |
| DenisGrachev: Ringo Render 64×48 | ✅ Fetched | Hype 2022 |
| DenisGrachev: Tiles and RET-chaining | ✅ Fetched | Hype 2025 |
| sq: Chunky pixel optimisation | ✅ Fetched | Hype 2022 |
| sq: VS Code + Z80MacroAsm setup | ✅ Fetched | Hype 2019 |
| Robus: Threads on Z80 | ✅ Fetched | Hype 2015 |
| Introspec: Data compression benchmark | ✅ Fetched | Hype 2017 |
| Introspec: DOWN_HL optimisation | ✅ Fetched | Hype 2020 |
| Introspec: GO WEST 1 & 2 (contended memory) | ✅ Fetched | Hype 2015 |
| Introspec: "Code is Dead" / "For Design" / "MORE" | ✅ Fetched | Hype 2015 |
| Shiru: Beeper engines 20XX | ✅ Fetched | Hype 2016 |
| diver4d: LPRINT secrets | ✅ Fetched | Hype 2015 |
| diver4d: Making of GABBA | ✅ Fetched | Hype 2019 |
| restorer: Making of Lo-Fi Motion | ✅ Fetched | Hype 2020 |
| UriS: NHBF making-of | ✅ Fetched | Hype 2025 |
| Rain file_id.diz (beeper engine details) | ✅ Extracted | scene.org ZIP |
| Eager file_id.diz (credits + notes) | ✅ Extracted | scene.org ZIP |
| Break Space file_id.diz | ✅ Extracted | scene.org ZIP (short, need full NFO) |
| Void, Manifesto, and 13 other NFO/DIZ | ✅ Extracted | scene.org ZIPs |
| Eager source code | 🟡 Promised | Introspec (need permission) |
| Introspec interview | 🟡 Partial | Telegram 2026-02-20 |
| Break Space full NFO | 🟡 Partial | Need bay6.retroscene.org or Pouet |
| DenisGrachev: Hara Mamba making-of | 🟡 To complete | Hype 2019 (partially fetched) |
| sq: full chunky effects code | 🟡 To complete | Hype 2022 (/demo/1084) |
| psndcj interview | ❌ Need | Contact via demoscene |
| Screamer interview | ❌ Need | Contact via demoscene |
| 512b/4K intro teardowns | ❌ Need | Select works, get permission |
| MinZ case study | 🟡 In progress | Alice's own project |
| Agon Light 2 porting guide | 🟡 In progress | Alice's own project |
| TurboSound / 3×AY documentation | ❌ Need | ZX Next docs, clone manuals |
| Black Crow #05 multicolor article | 🟡 On ZXArt | TRD image, needs emulator |
| Born Dead #05 chunky article | 🟡 On ZXArt | TRD image, needs emulator |
| Scenergy #01–03 (English!) | 🟡 On ZXArt | TRD images, worth scanning |
| ZX Format #02–08 technical articles | 🟡 On ZXArt | TRD images, systematic survey needed |
| Subliminal Extacy (English ZX zine) | 🟡 On ZXArt | Multi-format, worth checking |
| Spectrum Expert TRD images | 🟡 Available | ZXArt (SP_EXP1.ZIP, SP_EXP2.ZIP) |

---

## Side Project: "Not Eager" Demo

> A companion demo built with AI assistance — proof that Claude Code *can* help with real Z80 demoscene work. Response to Introspec's (valid) skepticism.

**Concept:** Reverse-engineer the key techniques from Eager (2015), combine with Dark's midpoint 3D engine (SE#02), create a new demo "inspired by Eager."

**Target effects:**
1. Attribute tunnel with 4-fold symmetry (Eager, Ch.9)
2. Chaos zoomer (Eager, Ch.9)
3. 4-phase colour animation (Eager, Ch.10)
4. **Midpoint 3D object** (Dark/SE#02, Ch.5) — the new ingredient
5. Digital drums on AY (Eager, Ch.12)

**Technical spec:** ZX Spectrum 128K, Pentagon timing, AY + digital drums, async frame generation, scripting engine.

**Strategic goal:** Get Introspec onboard as technical reviewer / collaborator for the book. "We didn't just write *about* demos, we *made* one — with AI."

**Book integration:** Case study for Chapter 23 (AI-Assisted Development), plus practical source material for Chapters 5, 9, 10, 12.

**Source:** `demo/` directory in this repo.

---

## Notes on Approach

1. **Every code example must compile and run.** No pseudocode, no "exercise for the reader" hand-waving. GitHub repo with CI that builds everything for both platforms.

2. **Respect the sources.** Introspec explicitly said his sources are closed but he'd share with Alice. Each use needs explicit permission. Don't paraphrase people's techniques without credit.

3. **The AI angle is honest, not hype.** Document where Claude Code actually helped and where it didn't. Introspec's scepticism is valid and worth including.

4. **Bilingual consideration.** The ZX Spectrum demoscene is heavily Russian-speaking. Hype articles are in Russian; interviews would likely be in Russian. Consider English primary text with Russian-language sidebars/quotes.

5. **The X-Trade narrative thread.** Dark wrote the algorithms (SE#01–02, 1997–98) AND coded Illusion. Introspec reverse-engineered it 20 years later. We have both sides. This thread runs Part I → Part II naturally.

6. **Two platforms, one book.** ZX Spectrum gets the most depth (demoscene + game dev). Agon Light 2 appears in game-dev chapters and the porting chapter. The Spectrum is the star; Agon shows what the same ISA can do with room to breathe. NEO6502/65C02 may be added later if there's interest.

7. **Making-of as primary source.** The richest material we have is making-of articles: Eager, Lo-Fi Motion, GABBA, NHBF, Hara Mamba, Rain. The book should feel like a collection of these stories, woven together with teaching.

---

## Changes from v1 (z80-book-outline.md)

### Added based on new sources:
- **Chapter 8 (Multicolor)** — NEW. DenisGrachev's LDPUSH technique, Ringo Render, Black Crow #05 multicolor — enough material for a standalone chapter
- **Chapter 3 additions** — RET-chaining from DenisGrachev's tile engines
- **Chapter 11 (Sound)** — Completely restructured: AY deep dive + TurboSound (2×AY) + Triple AY (Next) as primary focus. Chiptune techniques, music engine architecture, SFX system, tracker formats. Beeper as historical sidebar only
- **Chapter 13 (Size-coding)** — Now grounded in NHBF making-of and LPRINT trick
- **Chapter 14 (Compression)** — Standalone chapter based on Introspec's thorough benchmark
- **Chapter 20 (Demo Workflow)** — Lo-Fi Motion's toolchain as a real case study
- **Robus's Z80 threading** — Added to Chapter 12 (Music Sync)
- **Spectrum Expert articles text** — Now fetched from ZXArt, full summaries available

### Merged from book-plan.md (8-битный Ренессанс):
- **Two-platform structure** — Chapters 15–22 cover game development on Spectrum + Agon (NEO6502/65C02 dropped for now — may add later)
- **Full game implementation** — Chapters 21–22 build a complete platformer
- **Sprites deep dive** — Chapter 16 (six methods from simple to extreme)
- **Scrolling chapter** — Chapter 17
- **Entity system and AI** — Chapters 18–19
- **Clone memory maps** — Appendix F (Pentagon, Scorpion, Profi, ATM, Next)
- **AY/TurboSound/3×AY register reference** — Appendix G (expanded from just AY)

### Structure changes:
- Maths chapter renumbered to Ch.4 (was 3½) — it deserves a full chapter number
- 3D chapter renumbered to Ch.5 (was 3¾)
- Demoscene effects now Part II (Ch.6–10), not starting at Ch.4
- Sound chapter completely restructured: AY deep dive + TurboSound (2×AY) + Triple AY (Next) as main focus. Beeper is a historical sidebar, not a deep-dive. Music engine, SFX system, trackers/formats all in one chapter.
- Game development is Part V (Ch.15–19) — substantial, not an afterthought
- Full game is Part VI (Ch.20–22)
- AI chapter moved to end (Ch.23) — it's about workflow, reads better after the reader has built things
- Total: 23 chapters + 8 appendices (was 15 chapters + 6 appendices in v1; 25 chapters in book-plan.md)
