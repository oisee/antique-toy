# Illustration Plan -- Chapters 19-23 and Appendices A, B, C, G

This document identifies illustrations needed for chapters 19-23 and four appendices of "Coding the Impossible: Z80 Demoscene Techniques for Modern Makers." Each table lists proposed illustrations, their category, priority (P1 = essential, P2 = strongly recommended, P3 = nice to have), and a description of what the diagram should show.

**Categories:**
- **TD** = Technical diagram (matplotlib / vector graphics) -- memory layouts, waveforms, geometry, charts
- **FD** = Flow diagram (Mermaid / flowchart) -- loops, state machines, pipelines, timing
- **PX** = Pixel art / screenshot -- screen layout, rendering steps, colour examples
- **CS** = Code structure -- register maps, SMC flow, memory maps

---

## Chapter 19: Collisions, Physics, and Enemy AI

| # | Title | Cat | Priority | Description |
|---|-------|-----|----------|-------------|
| 19.1 | AABB overlap: four conditions | TD | P1 | Two rectangles A and B on a 2D grid with labelled edges (A.left, A.right, B.left, B.right, etc). Show the four inequality conditions as annotation arrows. Colour green for overlap zone, red for rejection. |
| 19.2 | AABB early-exit branching | FD | P1 | Flowchart of the check_aabb routine: Test 1 (horizontal left) -> fail -> return NC; pass -> Test 2 (horizontal right) -> fail -> return NC; pass -> Test 3 (vertical top) -> fail -> return NC; pass -> Test 4 (vertical bottom) -> fail -> return NC; pass -> return Carry set. Show T-state costs at each exit point (82T, ~100T, ~130T, ~156T). |
| 19.3 | Tile collision: pixel-to-tile lookup | TD | P1 | A 32x24 tilemap grid with one entity positioned across tile boundaries. Show the pixel coordinate (B,C) being right-shifted to produce a tile index. Draw arrows from the entity's corners and midpoints to the tile cells they sample. Highlight solid vs empty tiles in different colours. |
| 19.4 | Six-point entity sampling | TD | P2 | A player bounding box with 6 labelled sample points: bottom-left, bottom-right (feet), left-mid, right-mid (walls), top-left, top-right (head). Arrows to the tilemap cells each point queries. |
| 19.5 | Sliding collision response: axis-independent | FD | P2 | Two-step diagram: Step 1 -- apply X velocity, test X tile collisions, push-out if blocked. Step 2 -- apply Y velocity, test Y tile collisions, push-out if blocked. Show a diagonal movement vector decomposed into X then Y components, with the wall slide resulting from one axis being blocked. |
| 19.6 | Jump parabola: gravity + impulse | TD | P1 | Time vs Y-position graph showing the jump arc. Mark jump impulse (-3.5 pixels/frame), gravity accumulation (+0.25/frame^2), apex at frame 14, landing at frame 28. Annotate variable-height jump cut-off point. |
| 19.7 | Friction decay curve | TD | P2 | X-velocity vs frame plot showing exponential decay via right-shift: heavy friction (>>1 every frame), medium friction (>>1 every 2 frames), ice friction (>>1 every 4 frames). Three curves on the same axes, starting from the same initial velocity. |
| 19.8 | Physics update order | FD | P1 | Vertical pipeline: apply_gravity -> apply_friction -> move_entity -> check_player_tiles -> return. Show the data flow: velocity modified first, then position, then collision response. |
| 19.9 | Enemy FSM state transition diagram | FD | P1 | State machine with 5 nodes: PATROL, CHASE, ATTACK, RETREAT, DEATH. Labelled transition edges: "player within 48px", "within 16px", "cooldown expires", "health < threshold", "distance > 64px", "health = 0". Use different colours for each state. |
| 19.10 | JP table dispatch mechanism | CS | P2 | Memory layout showing the ai_state_table as 5 two-byte entries (DW addresses), with state byte (ix+5) indexing into it via ADD A,A + ADD HL,DE. Show the final JP (HL) jumping to the selected handler. |
| 19.11 | Four enemy type behaviour cards | TD | P2 | Four side-by-side mini-panels, one per enemy type (Walker, Shooter, Swooper, Ambusher). Each panel shows: sprite silhouette, state table (simplified), movement pattern (arrows on a platform), and detection range (circle/rectangle overlay). |
| 19.12 | Tuning parameter sensitivity chart | TD | P3 | Spider chart or parallel coordinate plot with axes for gravity, jump force, friction, patrol speed, chase speed, detect range. Three overlaid profiles: "Floaty/Moon", "Standard", "Heavy/Castlevania". |
| 19.13 | Frame budget breakdown: 16-entity game | TD | P2 | Stacked bar chart showing physics (~8,000T), collisions (~2,500T), AI (~4,000T), rendering placeholder (~20,000T), music (~3,000T), and slack (~34,000T) out of 71,680T total. Separate bar for worst case with reduced slack. |

---

## Chapter 20: Demo Workflow -- From Idea to Compo

| # | Title | Cat | Priority | Description |
|---|-------|-----|----------|-------------|
| 20.1 | Scene table architecture | CS | P1 | Memory layout showing a sequence of scene table entries (bank_number, entry_address, frame_duration, params). Arrows from each entry to an effect routine in a different memory bank. Show the linear read-and-dispatch flow. |
| 20.2 | Virtual buffer rendering pipeline | FD | P1 | Three-stage pipeline: Effect (renders into 32x24/32x48 virtual buffer) -> Output routine (converts buffer to attribute RAM format) -> Screen (attribute memory at $5800). Show the 1-byte-per-pixel buffer as an intermediate stage. |
| 20.3 | Lo-Fi Motion build pipeline | FD | P1 | Directed graph from source assets (PNG, raw data) through Ruby conversion scripts to binary includes (.bin, .hru), through sjasmplus assembly to output binary (.trd/.sna), into emulator (zemu). Each arrow is a Makefile rule. |
| 20.4 | Demo production timeline | TD | P2 | Gantt chart or horizontal timeline showing 14 days divided into phases: Engine (days 1-2), Effects (days 3-7), Content (days 8-10), Integration (days 11-12), Polish (days 13-14). Colour-coded bars, with the engine investment highlighted as the foundation. |
| 20.5 | Standard ZX demo project layout | CS | P2 | Directory tree diagram showing src/ (main.asm, engine.asm, effects/*, sound/*), data/ (music, screens, sinetable), tools/ (gen_sinetable.rb, convert_gfx.rb), and Makefile. File icons by type. |
| 20.6 | Compo submission checklist | FD | P3 | Flowchart: Choose party -> Read rules -> Test on target -> Submit early -> Write NFO -> Watch compo. Decision diamonds: "Remote entry accepted?" "File format correct?" "Cold-boot tested?" |
| 20.7 | Scene table: content vs engine separation | TD | P2 | Split diagram: left side = "Engine code" (immutable), right side = "Scene table data" (editable). Arrows show how reordering table entries or changing durations restructures the demo without touching engine code. |

---

## Chapter 21: Full Game -- ZX Spectrum 128K

| # | Title | Cat | Priority | Description |
|---|-------|-----|----------|-------------|
| 21.1 | 128K bank allocation map | CS | P1 | Visual memory map showing all 8 banks (0-7) as 16KB blocks. Bank 2 at $8000 (fixed: main code), Bank 5 at $4000 (fixed: screen), Bank 7 at $4000 (shadow screen). Switchable banks 0,1,3,4,6 at $C000 with colour-coded contents: level data, sprites, music. Show the port $7FFD bit layout. |
| 21.2 | Gameplay frame budget waterfall | TD | P1 | Waterfall chart showing each subsystem's T-state cost stacking up: input (200T) + player physics (800T) + player state (400T) + enemy AI (4,000T) + collisions (2,000T) + projectiles (500T) + scroll (12,000T) + tile render (12,000T) + bg restore (3,000T) + sprites (8,000T) + HUD (1,500T) + music IM2 (3,000T) = ~50,000T. Show 71,680T ceiling with slack labelled. |
| 21.3 | Gameplay frame budget: worst case | TD | P1 | Same waterfall as 21.2 but with worst-case numbers (6 enemies + scroll + projectiles): total ~65,000T, slack only ~6,500T (9%). Red warning zone near the ceiling. Use this alongside 21.2 for comparison. |
| 21.4 | Game state machine | FD | P1 | State diagram with nodes: LOADER, TITLE, MENU, GAMEPLAY, PAUSE, GAMEOVER, HISCORE, LEVELWIN. Transition edges labelled with triggers: "any key", "select Start", "pause key", "lives=0", "score qualifies", "next level loaded". |
| 21.5 | Ironclaw project directory layout | CS | P2 | Directory tree: src/ (14 .a80 files listed), data/ (levels/, tiles/, sprites/, music/, sfx/, screens/), tools/ (4 Python scripts), build/, Makefile. File count annotations. |
| 21.6 | Data pipeline: asset to binary | FD | P1 | Multi-track pipeline diagram: tileset.png -> png2tiles.py -> tileset.bin -> pletter -> tileset.bin.plt; level.tmx -> map2bin.py -> level_map.bin -> zx0 -> level.bin.zx0; player.png -> png2sprites.py -> player.bin; level.pt3 -> (direct INCBIN). All converge into sjasmplus -> ironclaw.tap. |
| 21.7 | Double-buffer scroll: shadow screen | TD | P2 | Diagram showing two screen buffers (Bank 5 and Bank 7). Frame N: draw into Bank 7 while displaying Bank 5. Frame N+1: flip via bit 3 of $7FFD. Show the column copy being spread across two frames. |
| 21.8 | Dirty rectangle sprite cycle | FD | P2 | Circular flow: (1) Save background beneath sprite -> (2) Draw sprite at new position -> (3) Next frame: restore saved background -> (4) Save new background -> repeat. Show the bg_save_buffer as an intermediate store. |
| 21.9 | Entity structure layout (16 bytes) | CS | P2 | Byte-level diagram of the 16-byte entity struct: offsets 0-1 (X position, 8.8), 2-3 (Y position), 4-5 (VX), 6-7 (VY), 8 (type), 9 (state), 10 (anim), 11 (health), 12 (flags with bit meanings), 13 (timer), 14-15 (aux). Colour-coded fields. |
| 21.10 | IM2 interrupt handler: bank switching | FD | P2 | Sequence diagram: IM2 fires -> save registers -> save current bank -> page in music bank -> call pt3_play -> call sfx_update -> restore bank -> restore registers -> EI + RETI. Show the critical bank save/restore pair. |
| 21.11 | .tap file structure | CS | P3 | Block diagram showing the .tap file as a sequence of blocks: Block 0 (BASIC loader), Block 1 (loading screen, 6912 bytes), Block 2 (main code), Blocks 3-7 (bank data). Show the BASIC loader text and LOAD "" CODE commands. |
| 21.12 | Priority-based SFX channel stealing | FD | P3 | Diagram showing AY channels A, B, C with music playing. SFX trigger on channel C: the SFX data temporarily overrides channel C's music registers. When SFX ends, channel C returns to music control. Show priority comparison logic. |
| 21.13 | DeZog profiling workflow | FD | P2 | Loop diagram: border stripe shows "over budget" -> DeZog breakpoint at frame start -> step through, measure each subsystem -> build profiling table -> identify bottleneck -> optimise -> measure again. |
| 21.14 | Physics-collision interleave | FD | P2 | Pipeline: (1) Apply gravity -> (2) Apply input -> (3) Horizontal move + X collision check + pushback -> (4) Vertical move + Y collision check + pushback -> (5) Jump check. Emphasise the separate X and Y axis handling. |

---

## Chapter 22: Porting -- Agon Light 2

| # | Title | Cat | Priority | Description |
|---|-------|-----|----------|-------------|
| 22.1 | Platform comparison table (visual) | TD | P1 | Side-by-side visual comparison: ZX Spectrum vs Agon Light 2. Two columns with icons/bars for: CPU speed (3.5 vs 18.4 MHz), RAM (128KB banked vs 512KB flat), video (ULA direct vs VDP coprocessor), frame budget (71K vs 368K T-states), sprites (software vs hardware). |
| 22.2 | ADL mode vs Z80-compatible mode | CS | P1 | Register file diagram showing the same registers in two modes: Z80 mode (16-bit HL, DE, BC, 16-bit PC, 2-byte PUSH) vs ADL mode (24-bit HL, DE, BC, 24-bit PC, 3-byte PUSH). Highlight the width difference with colour coding. |
| 22.3 | VDP command pipeline | FD | P1 | Flow diagram: eZ80 CPU sends VDU byte sequence via RST $10 -> serial link -> ESP32 VDP -> processes command -> updates display. Show the asynchronous nature: CPU continues while VDP processes. Annotate latency. |
| 22.4 | Spectrum vs Agon rendering model | TD | P1 | Two-panel diagram. Left: Spectrum -- CPU writes bytes directly to $4000 framebuffer -> ULA reads and displays. Right: Agon -- CPU sends VDP commands via serial -> VDP (ESP32) manages framebuffer internally -> display. Show the "no shared memory" boundary. |
| 22.5 | Memory architecture: banked vs flat | CS | P2 | Left: Spectrum 64KB address space with $C000 switchable window, 8 banks behind it, port $7FFD switching. Right: Agon 512KB flat space, all addresses visible simultaneously. Show a data access that requires bank switching on Spectrum but is direct on Agon. |
| 22.6 | What transfers / rewrites / rethinks | TD | P2 | Three-column categorisation chart. Column 1 "Transfers directly": entity system, AABB collisions, fixed-point physics, FSM AI. Column 2 "Needs rewriting": rendering, sound, input, loading. Column 3 "Needs rethinking": memory architecture, no banking, no SMC motivation. Use green/yellow/red colour coding. |
| 22.7 | Jump table: DW vs DL pointer width | CS | P2 | Side-by-side memory layout of a 5-entry state dispatch table. Left: Spectrum with DW (2 bytes per entry, multiply by 2). Right: Agon with DL (3 bytes per entry, multiply by 3). Show the index arithmetic difference. |
| 22.8 | Sprite cost comparison | TD | P2 | Bar chart comparing per-sprite rendering cost: Spectrum software masked sprite (~1,200T including bg save/restore) vs Agon VDP position command (~390T, no bg management needed). Show the 3x speedup plus elimination of dirty rectangles. |
| 22.9 | Porting step-by-step roadmap | FD | P2 | Sequential flow: (1) Set up Agon project -> (2) Replace rendering layer -> (3) Translate game logic (DW->DL, 16->24 bit) -> (4) Rewrite sound -> (5) Rewrite input -> (6) Rewrite loading -> (7) Test and tune. Numbered blocks connected by arrows. |
| 22.10 | eZ80 new instructions: LEA, MLT, TST | CS | P3 | Three mini-diagrams showing each new instruction. LEA: "IX = IY + offset" in one instruction vs 4 on Z80. MLT: "BC = B * C" (hardware multiply) vs shift-add loop. TST: "test bits without destroying A" vs AND + restore. Show T-state savings. |
| 22.11 | "What each platform teaches" Venn diagram | TD | P3 | Two overlapping circles. Spectrum circle: cycle-level efficiency, creative constraint solving, memory conservation, SMC tricks. Agon circle: system architecture, coprocessor communication, data pipeline management, asset tools. Overlap: tight inner loops, register-efficient code, lookup tables, data-oriented design. |

---

## Chapter 23: AI-Assisted Z80 Development

| # | Title | Cat | Priority | Description |
|---|-------|-----|----------|-------------|
| 23.1 | The AI feedback loop | FD | P1 | Circular flow diagram: Prompt -> Generate code -> Assemble -> Error? (branch: yes -> paste error, loop back to Generate; no -> Run in emulator) -> Wrong output? (branch: yes -> describe bug + DeZog register state, loop back to Generate; no -> Done). Show typical iteration count (2-5 rounds). |
| 23.2 | AI confidence spectrum | TD | P1 | Horizontal stacked bar or gradient chart with three zones: High confidence (green): instruction encoding, boilerplate, cycle counts, dialect translation. Medium confidence (yellow): standard algorithms, memory layout, simple SMC. Low confidence (red): novel inner loop optimisation, contended timing, creative effect design, flag tricks. |
| 23.3 | DeZog + Claude Code integration workflow | FD | P2 | Sequence diagram with three actors: Claude Code, Human, DeZog. Claude generates code -> Human assembles + loads -> Human sets breakpoint in DeZog -> DeZog shows register divergence -> Human copies state to Claude -> Claude diagnoses bug -> Human applies fix -> repeat. |
| 23.4 | HiSoft C parallel: tools through the ages | TD | P2 | Horizontal timeline / progression chart: BASIC (1982, slow, accessible) -> HiSoft C (1998, 10-15x faster, no floats) -> Macro assemblers (full control, high friction) -> AI-assisted assembly (2024+, fast scaffolding, no novel optimisation). Each entry with a brief strengths/limits annotation. |
| 23.5 | inc l vs inc hl: the 2T difference at scale | TD | P2 | Multiplication chart: 2 T-states saved x 3,072 iterations per frame = 6,144 T-states = 8.6% of 48K frame budget. Show this as a mini stacked bar: the 6,144T "savings" block highlighted within a 71,680T frame. Annotate that this is the kind of optimisation AI misses. |
| 23.6 | MinZ toolchain architecture | CS | P2 | Block diagram: MinZ source code -> Compiler (Go, ~90K lines) -> Z80 assembly -> mza assembler -> binary -> mze emulator or real hardware. Side branch: REPL, remote runner, DZRP debugger protocol. Label which parts were AI-generated vs human-designed. |
| 23.7 | DOWN_HL: AI attempt vs correct version | TD | P3 | Two side-by-side flowcharts. Left: AI's first attempt (handles 2/3 thirds correctly, fails at third boundary). Right: correct version with all three cases handled. Highlight the third-boundary bug in red. |

---

## Appendix A: Z80 Instruction Quick Reference

| # | Title | Cat | Priority | Description |
|---|-------|-----|----------|-------------|
| A.1 | T-state cost comparison chart (key instructions) | TD | P1 | Horizontal bar chart of common instructions grouped by category: Load (LD r,r=4T, LD r,(HL)=7T, LD (IX+d),r=19T), Arithmetic (ADD=4T, CP=4T, NEG=8T), Block (LDI=16T, LDIR=21T), Jump (JP=10T, JR=12/7T, DJNZ=13/8T, JP(HL)=4T). Colour-coded by category. |
| A.2 | Register architecture diagram | CS | P1 | Visual register file showing main registers (A,F,B,C,D,E,H,L), shadow set (A',F',B',C',D',E',H',L'), index registers (IX,IY), special registers (SP,PC,I,R). Show EXX/EX AF,AF' swap arrows between main and shadow sets. |
| A.3 | Flag register bit layout | CS | P1 | The F register as 8 bits: S(7), Z(6), -(5), H(4), -(3), P/V(2), N(1), C(0). Mark bits 5 and 3 as "undocumented (copy of result bits 5,3)". |
| A.4 | Screen address bit field diagram | TD | P2 | The pixel address format: H = `010 TT SSS`, L = `LLL CCCCC`. Colour-code each field (T=third, S=scanline, L=character row line, C=column). Show the derivation from Y coordinate bits. Same concept as 2.2 but formatted as a tear-out reference. |
| A.5 | PUSH/POP: fastest read/write comparison | TD | P2 | Comparison chart: PUSH at 5.5T/byte vs LD (HL),r at 7T/byte vs LDIR at 21T/byte vs LDI at 16T/byte. Show as bytes-per-T-state efficiency (inverse). |
| A.6 | Instruction encoding prefix tree | CS | P2 | Tree diagram showing: unprefixed (1 byte), CB prefix (bit ops, shifts), ED prefix (block ops, 16-bit arith), DD prefix (IX ops), FD prefix (IY ops), DD CB (IX bit ops). Show byte count and T-state penalty for each prefix level. |
| A.7 | IXH/IXL undocumented registers | CS | P3 | IX register split into two halves (IXH, IXL) with DD prefix annotation. Show that these provide 2 extra 8-bit registers at +4T cost per operation. |

---

## Appendix B: Sine Table Generation and Trigonometric Tables

| # | Title | Cat | Priority | Description |
|---|-------|-----|----------|-------------|
| B.1 | Sine table overview: 256 entries, page-aligned | TD | P1 | A sine wave plotted at 256 discrete samples, with index 0=0, 64=peak(+127), 128=0, 192=trough(-128). Mark the cosine offset (+64 index). Show the page-aligned table in memory with H=constant, L=angle index. |
| B.2 | Approach comparison: size vs accuracy | TD | P1 | Scatter plot with axes: ROM cost in bytes (x-axis) vs max error (y-axis, log scale or linear 0-8). Points for each approach: Full table (256B, 0 error), Quarter-wave (86B, 0), Parabolic (38B, error 8), Quarter+d2 deltas (63B, 0), Bhaskara I (60B, error 1), Bhaskara+correction (81B, 0). Pareto frontier line. |
| B.3 | Parabolic vs true sine: deviation plot | TD | P1 | Two overlaid waveforms for one quadrant (indices 0-64): true integer sine and parabolic approximation. Below: a difference plot showing the error, peaking at ~8 near index 17. |
| B.4 | Second-order delta encoding concept | TD | P2 | Three stacked plots: (1) sine values, (2) first differences (d1), (3) second differences (d2) showing values in {-1, 0, +1} only. Annotate that 2 bits per d2 entry suffice. |
| B.5 | Quarter-wave symmetry | TD | P2 | A full sine period with the four quadrants shaded differently. Arrows showing: Q2 = mirror of Q1, Q3 = negate Q1, Q4 = negate mirror of Q1. Show that only 65 values (Q1) need storage. |
| B.6 | Decision tree: which sine approach | FD | P2 | Flowchart: "256 bytes to spare?" -> Yes: full table. No -> "Need exact values?" -> Yes: "Have 86 bytes?" -> Yes: quarter-wave. No: quarter+d2 (63B). No (approximate OK) -> "Have multiply/divide?" -> Yes: Bhaskara I (25B extra). No: parabolic (38B). |

---

## Appendix C: Compression Quick Reference

| # | Title | Cat | Priority | Description |
|---|-------|-----|----------|-------------|
| C.1 | Compressor comparison: ratio vs speed scatter | TD | P1 | Scatter plot with axes: compression ratio (x-axis, 48%-60%) vs decompression speed in T/byte (y-axis, 30-250). Points for each compressor: Exomizer (48.3%, 250T), ApLib (49.2%, 105T), Hrust 1 (49.7%, 120T), Pletter (51.5%, 69T), MegaLZ fast (51.6%, 63T), ZX0 (~52%, 100T), ZX7 (53%, 107T), LZ4 (58.6%, 34T). Annotate the Pareto frontier. Label the "speed vs ratio" trade-off. |
| C.2 | Decision tree: which compressor | FD | P1 | Flowchart matching the decision tree in the appendix text: 256/512B intro? -> ZX0. 1K/4K intro? -> ZX0. Real-time streaming? -> LZ4. Fast between-scene? -> MegaLZ fast/Pletter. One-time load? -> Exomizer. Good balance? -> ApLib. Runs of bytes? -> Custom RLE. First project? -> ZX0/Bitbuster. |
| C.3 | Decompressor size vs ratio | TD | P2 | Bar chart (or bubble chart) with compressors on x-axis, dual y-axes for decompressor Z80 code size (bytes, bars) and compression ratio (%, line). Show the trade-off: ZX7 at 69 bytes is tiny but ratio is 53%; Exomizer at 170 bytes has best ratio at 48.3%. |
| C.4 | Build pipeline: asset to binary | FD | P2 | Pipeline diagram matching the appendix text: PNG -> png2scr -> scr -> zx0 -> .zx0 -> sjasmplus (INCBIN) -> .tap. Parallel track: WAV -> pt3tools -> .pt3 -> zx0. TMX -> tmx2bin -> .bin -> exomizer. Show Makefile as the orchestrator. |
| C.5 | Bytes-per-frame at 50fps | TD | P2 | Bar chart showing bytes decompressible per frame for each compressor: LZ4 (2,055), MegaLZ fast (1,109), Pletter (1,012), ZX0 (698), ApLib (665), Hrust 1 (582), Exomizer (279). Red line at common thresholds: 768 bytes (one attribute frame), 6,144 bytes (one pixel frame). |
| C.6 | In-place backwards decompression | CS | P3 | Memory diagram showing compressed data at the end of a buffer, decompressor reading backwards, output growing backwards. Show how the output overtakes the compressed data only after it has been consumed. Label "ZX0 backwards variant" support. |

---

## Appendix G: AY-3-8910 / TurboSound / Triple AY Register Reference

| # | Title | Cat | Priority | Description |
|---|-------|-----|----------|-------------|
| G.1 | AY-3-8910 block diagram | TD | P1 | Functional block diagram of the AY chip: three tone generators (12-bit period each), one noise generator (5-bit LFSR), mixer (6 enable bits), three volume controls (4-bit + envelope mode), one envelope generator (16-bit period + shape), two I/O ports. Show signal flow from oscillators through mixer and volume to output. |
| G.2 | Mixer register R7 bit layout | CS | P1 | The 8-bit R7 register with each bit labelled: [IOB][IOA][NC][NB][NA][TC][TB][TA]. Show "0 = ON" active-low convention prominently. Annotate common values: $38 (all tones, no noise), $3F (silence), $00 (everything on). |
| G.3 | Envelope shape waveforms | TD | P1 | Visual waveforms for all 10 unique envelope shapes ($00, $04, $08, $09, $0A, $0B, $0C, $0D, $0E, $0F), drawn as amplitude vs time plots. Group by behaviour: single-shot ($00 decay, $04 attack), repeating ($08 saw-down, $0C saw-up, $0A triangle, $0E triangle-inv), hold ($0B decay+hold-max, $0D attack+hold-max). Use the ASCII art waveforms from the appendix as guide but render as clean vector plots. |
| G.4 | Volume register: fixed vs envelope mode | CS | P2 | R8/R9/R10 bit layout: bit 4 = mode (0=fixed, 1=envelope), bits 3-0 = fixed volume. Diagram showing the branch: if bit 4 clear, bits 3-0 directly set volume; if bit 4 set, volume comes from the shared envelope generator. |
| G.5 | AY volume curve: logarithmic vs linear | TD | P2 | Plot with 16 steps (0-15) on x-axis and relative output amplitude on y-axis. Two curves: AY-3-8910 (logarithmic, approx 1.5 dB/step) and YM2149 (linear). Show the perceptual difference at low volume levels. |
| G.6 | TurboSound chip selection diagram | CS | P2 | Two AY chips sharing I/O ports $FFFD/$BFFD. A selector byte ($FF = chip 0, $FE = chip 1) written to $FFFD routes all subsequent register operations. Show the stereo output: chip 0 -> left speaker, chip 1 -> right speaker. |
| G.7 | Triple AY (Next) chip selection | CS | P3 | Extension of G.6 with three chips ($FF, $FE, $FD). Show per-channel stereo panning via R14 bit layout on the Next. |
| G.8 | Note frequency table: piano roll visualisation | TD | P2 | Piano-style chart with octaves 1-7 on the y-axis, notes C through B on the x-axis. Each cell shows the AY period value. Colour gradient from low periods (high pitch, top-right) to high periods (low pitch, bottom-left). Annotate octave 8 cells with "limited accuracy" markers. |
| G.9 | Two-step AY register write timing | CS | P2 | Timing sequence: (1) LD BC,$FFFD -> OUT (C),A (select register, 12T) -> (2) LD B,$BF -> OUT (C),E (write data, 12T). Show the "only B changes" optimisation (C stays at $FD throughout). Total: 41T including LD instructions. |
| G.10 | PT3 data flow: row to AY registers | FD | P3 | Pipeline: PT3 row data (note, instrument, effect) -> ornament table lookup (per-frame pitch offset) -> amplitude envelope lookup -> final period + volume calculation -> R0-R13 register writes. Show this for one channel, with the per-frame update loop. |
| G.11 | Buzz-bass: envelope as pitch | TD | P2 | Two signal diagrams. Top: normal tone (R0-R1 sets pitch, R8 sets fixed volume). Bottom: buzz-bass (R0-R1 disabled or very high, R11-R12 sets envelope period = pitch, R8 = envelope mode, R13 = repeating saw). Show the envelope's repeating sawtooth at audio frequency producing a bass tone. |

---

## Summary Statistics

| Section | P1 | P2 | P3 | Total |
|---------|----|----|----|----|
| Ch19: Collisions, Physics, AI | 5 | 6 | 2 | 13 |
| Ch20: Demo Workflow | 3 | 3 | 1 | 7 |
| Ch21: Full Game | 5 | 7 | 2 | 14 |
| Ch22: Porting -- Agon | 4 | 5 | 2 | 11 |
| Ch23: AI-Assisted | 2 | 4 | 1 | 7 |
| Appendix A: Z80 Reference | 3 | 3 | 1 | 7 |
| Appendix B: Sine Tables | 3 | 3 | 0 | 6 |
| Appendix C: Compression | 2 | 3 | 1 | 6 |
| Appendix G: AY Registers | 3 | 6 | 2 | 11 |
| **Total** | **30** | **40** | **12** | **82** |

---

## Tooling Recommendations

### Category-to-Tool Mapping

| Category | Tool | Rationale |
|----------|------|-----------|
| **TD** (Technical diagram) | **matplotlib** (Python) | Best for charts, waveforms, scatter plots, bar charts, overlaid curves. Script-based = reproducible. Export SVG natively. |
| **FD** (Flow diagram) | **Mermaid** (Markdown-based) or **draw.io** | Mermaid for simple state machines and flowcharts (embeddable, text-based). draw.io for more complex multi-actor sequence diagrams and pipeline diagrams. Export SVG from both. |
| **PX** (Pixel art / screenshot) | **Aseprite** or **Multipaint** for original pixel art; **emulator screenshots** for actual output | Aseprite exports PNG at exact pixel dimensions. For Spectrum-specific pixel art (attribute clash demos, screen layout), Multipaint enforces attribute constraints. |
| **CS** (Code structure) | **draw.io** or **matplotlib** | Memory maps and register layouts work well as hand-drawn-style vector diagrams in draw.io. Bit-field layouts are cleanest in matplotlib with table/cell rendering. |

### Output Formats

| Format | Use | Notes |
|--------|-----|-------|
| **SVG** | PDF output (A4 and A5 builds) | Vector, scales to any resolution, small file size, pandoc handles SVG-to-PDF via Inkscape or rsvg-convert. |
| **PNG (2x)** | EPUB output | Raster at 2x display resolution (e.g., 1200px wide for a 600px display column). EPUB readers do not reliably render SVG. |
| **Both** | Generated from the same source | matplotlib scripts should export both `savefig('fig.svg')` and `savefig('fig.png', dpi=200)`. Mermaid CLI exports both. |

### Directory Structure

```
illustrations/
  ch19/
    19-01-aabb-overlap.svg
    19-01-aabb-overlap.png
    19-02-aabb-early-exit.svg
    19-02-aabb-early-exit.png
    ...
  ch20/
    20-01-scene-table.svg
    ...
  ch21/
  ch22/
  ch23/
  appendix-a/
    a-01-tstate-chart.svg
    ...
  appendix-b/
  appendix-c/
  appendix-g/
  scripts/
    gen_ch19_figs.py       # matplotlib scripts per chapter
    gen_ch21_figs.py
    gen_appendix_a_figs.py
    gen_appendix_b_figs.py
    gen_appendix_c_figs.py
    gen_appendix_g_figs.py
    mermaid/
      ch19-fsm.mmd         # Mermaid source files
      ch20-pipeline.mmd
      ch21-state-machine.mmd
      ...
  Makefile                 # `make illustrations` regenerates all
```

### Naming Convention

`{chapter}-{number}-{short-name}.{ext}`

Examples: `19-01-aabb-overlap.svg`, `21-04-state-machine.svg`, `a-02-register-arch.svg`, `g-03-envelope-shapes.svg`

### Build Integration

Add a `make illustrations` target to the project Makefile that runs all generation scripts and converts Mermaid sources. The book build pipeline (pandoc) should reference SVG for PDF output and PNG for EPUB output, selectable via a pandoc filter or conditional include.

### Colour Palette

Use a consistent 8-colour palette across all technical diagrams for visual coherence:
- Primary: Spectrum blue (#0000D7), Spectrum red (#D70000), Spectrum green (#00D700)
- Secondary: Spectrum cyan (#00D7D7), Spectrum yellow (#D7D700), Spectrum magenta (#D700D7)
- Neutral: dark grey (#333333) for text/outlines, light grey (#CCCCCC) for backgrounds/grids

This palette references the ZX Spectrum's native BRIGHT colours, tying the illustrations to the book's subject matter.
