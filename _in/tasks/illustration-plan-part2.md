# Illustration Plan -- Chapters 13-18

This document identifies illustrations needed for chapters 13-18 of "Coding the Impossible: Z80 Demoscene Techniques for Modern Makers." Each table lists proposed illustrations, their category, priority (P1 = essential, P2 = strongly recommended, P3 = nice to have), and a description of what the diagram should show.

**Categories:**
- **TD** = Technical diagram (matplotlib / vector graphics) -- memory layouts, waveforms, geometry, charts
- **FD** = Flow diagram (Mermaid / flowchart) -- loops, state machines, pipelines, timing
- **PX** = Pixel art / screenshot -- screen layout, rendering steps, colour examples
- **CS** = Code structure -- register maps, SMC flow, memory maps

---

## Chapter 13: The Craft of Size-Coding

| # | Illustration title | Category | Priority | Description |
|---|-------------------|----------|----------|-------------|
| 13.1 | Size category comparison | TD | P1 | Nested rectangles (or stacked bars) showing 256, 512, 1K, 4K, 8K byte limits with annotated examples of what fits in each. Visual sense of scale: 256 bytes smaller than this paragraph. |
| 13.2 | Byte-level anatomy of NHBF | CS | P1 | Hex dump or memory map of a 256-byte intro showing colour-coded regions: music AY writes, visual output code, sine/tone data embedded in instruction stream, loop structure. Label overlapping code/data bytes. |
| 13.3 | Code/data overlap diagram | CS | P1 | Instruction bytes in memory (e.g., $3E = LD A,n opcode) shown from two perspectives: (a) as the CPU executes it (instruction), (b) as another routine reads the operand address as data. Two arrows converging on the same byte. |
| 13.4 | Instruction size comparison table | TD | P2 | Visual bar chart: CALL $0010 (3 bytes) vs RST $10 (1 byte), JP label (3) vs JR label (2), LD A,0 (2) vs XOR A (1), CP 0 (2) vs OR A (1). Savings shown as hatched "freed" segments. |
| 13.5 | Register state flow between routines | FD | P2 | Flow diagram showing two routines connected by register state. Routine A exits with A=7, HL=$5800, BC=0. Routine B needs exactly those values. Arrow showing "free data transfer via side effects." |
| 13.6 | LPRINT trick: transposition effect | PX | P1 | Two panels: (a) how printer driver writes sequential bytes to interleaved screen memory, producing scrambled horizontal bands, (b) the resulting visual pattern on screen. Show POKE 23681,64 redirecting output path. |
| 13.7 | The ORG trick: address bytes as data | CS | P2 | Memory region at ORG $4000 with a JR instruction whose offset byte happens to equal $40 -- the same value needed as the high byte of screen memory. Arrow showing the dual use. |
| 13.8 | 256-byte optimisation pipeline | FD | P2 | Step-by-step cascade: 400 bytes (working) -> replace CALL with RST (save 22B) -> overlap data with code (save 32B) -> exploit register state (save 8B) -> smaller encodings (save 12B) -> structural rearrangement (save 70B) -> 256 bytes. Show byte count at each stage. |
| 13.9 | Attribute plasma at 256 bytes | PX | P3 | Screenshot (or generated image) showing a colourful attribute plasma pattern filling the screen -- the target visual output of the practical exercise. |

---

## Chapter 14: Compression -- More Data in Less Space

| # | Illustration title | Category | Priority | Description |
|---|-------------------|----------|----------|-------------|
| 14.1 | Compression tradeoff triangle | TD | P1 | Triangle diagram with three vertices: compression ratio, decompression speed, decompressor code size. Place Exomizer (ratio corner), LZ4 (speed corner), ZX7/ZX0 (code size corner), ApLib/Pletter (middle region) as labelled dots. The Pareto frontier as a curve. |
| 14.2 | Compressor benchmark scatter plot | TD | P1 | Scatter plot with axes: compressed size (horizontal, lower=better) vs decompression speed in T/byte (vertical, lower=faster). One dot per compressor, labelled. Show the Pareto frontier line connecting non-dominated tools. |
| 14.3 | LZ compression: match/literal encoding | TD | P1 | Byte stream visualisation: original data with a repeated substring highlighted. Below: compressed stream showing a literal run, then a back-reference arrow (offset + length) pointing to the earlier occurrence. Decode arrows showing reconstruction. |
| 14.4 | Break Space: 122 frames in 10KB | TD | P2 | Visual scale comparison: 122 full screens (843,264 bytes) represented as a tall stack, compressed to a tiny 10,512-byte block. Show the 1.25% ratio graphically. |
| 14.5 | ZX0 decompressor code size in context | TD | P2 | A 256-byte grid (16x16 cells) where 70 cells are coloured (the ZX0 decompressor) and 186 cells are open (remaining budget for a 256-byte intro). Visual sense of how small 70 bytes is. |
| 14.6 | Delta coding: inter-frame difference | PX | P1 | Two near-identical ZX Spectrum screens side by side with changed pixels highlighted in red. Below: the delta stream showing only (offset, value) pairs for changed bytes. Show dramatic size reduction. |
| 14.7 | Asset pipeline: PNG to .tap | FD | P1 | Pipeline diagram: source PNG -> png2scr converter -> .scr file -> zx0 compressor -> .zx0 file -> INCBIN in .asm -> sjasmplus -> .tap. Show the Makefile integration points. |
| 14.8 | Compressor decision flowchart | FD | P2 | Decision tree: "Size-coded intro?" -> yes -> ZX0/ZX7. No -> "Real-time streaming?" -> yes -> LZ4. No -> "One-time load?" -> yes -> Exomizer. No -> "Need balance?" -> ApLib/Pletter. Also: "Identical runs?" -> RLE. "Animation frames?" -> Delta+LZ. |
| 14.9 | MegaLZ revival: format vs implementation | TD | P3 | Split diagram: left side shows the LZ format (bit-level encoding) unchanged since 2005; right side shows old decompressor (slow, bloated) crossed out and new decompressor (92 bytes, 98T/byte) replacing it. Lesson: format and implementation are separable. |
| 14.10 | Compression as bandwidth amplifier | TD | P3 | Pipe diagram: narrow pipe (compressed, 800 bytes) flowing into decompressor block, expanding to wide pipe (2KB output). Label: 34 T/byte = one frame. Show effective bandwidth exceeding raw bus throughput. |

---

## Chapter 15: Anatomy of Two Machines

| # | Illustration title | Category | Priority | Description |
|---|-------------------|----------|----------|-------------|
| 15.1 | ZX Spectrum 128K memory map | CS | P1 | Full 64KB address space divided into 4 slots: ROM ($0000-$3FFF), page 5 fixed ($4000-$7FFF), page 2 fixed ($8000-$BFFF), switchable page 0-7 ($C000-$FFFF). Colour-coded pages with arrows showing $7FFD port bank selection. |
| 15.2 | $7FFD port bit layout | CS | P1 | Bit field diagram for the 8-bit port value: bits 0-2 (RAM page), bit 3 (screen select), bit 4 (ROM select), bit 5 (disable paging), bits 6-7 (unused). Annotate each field with its function. |
| 15.3 | Practical 128K game memory layout | CS | P1 | Eight RAM pages (0-7) shown as blocks, each labelled with its typical game usage: page 0 (level data), page 1 (sprite set 1), page 2 (main code, fixed), page 4 (music), page 5 (screen, fixed), page 7 (shadow screen). Colour-coded by function. |
| 15.4 | Contended memory: model comparison | TD | P1 | Table or heatmap showing which pages are contended on each Spectrum model: 48K (all), 128K/+2 (odd pages 1,3,5,7), +2A/+3 (high pages 4,5,6,7). Green=fast, red=contended. |
| 15.5 | Frame timing tact-maps | TD | P1 | Three vertical strip diagrams (Pentagon, 128K, 48K) showing the frame divided into top border, active display, and bottom border. Label T-states for each region, mark the interrupt point, and highlight contention zones. |
| 15.6 | Scanline breakdown | TD | P2 | Single scanline dissected: 128T active pixel area, 24T right border, 48T/52T sync+retrace, 24T left border. Mark the contention window vs free window within each scanline. |
| 15.7 | Practical frame budget waterfall | TD | P2 | Waterfall chart: total frame (71,680T) -> subtract interrupt overhead (30T) -> subtract ISR (14T) -> subtract PT3 player (4,000T) -> subtract housekeeping (40T) -> remaining practical budget (~67,000T). Versions for Pentagon, 128K, 48K. |
| 15.8 | Shadow screen double-buffering | FD | P1 | Two-frame sequence: Frame N shows page 5 on screen while CPU draws to page 7; Frame N+1 flips (bit 3 toggle), page 7 now displayed, CPU draws to page 5. Arrows show flip via $7FFD. |
| 15.9 | ULA snow and I register danger zone | TD | P2 | Number line from $00 to $FF showing the I register value. Highlight $40-$7F as the danger zone (ULA snow). Mark common safe values: $FE (standard IM2 setup), $00 (default). |
| 15.10 | Agon Light 2 dual-processor architecture | CS | P1 | Block diagram showing eZ80 (18.432 MHz, 512KB RAM, MOS) connected to ESP32 (240 MHz, FabGL VDP, audio) via UART serial link (384 Kbaud). Label command flow direction and latency. |
| 15.11 | eZ80 memory map (flat 24-bit) | CS | P2 | Linear memory bar from $000000 to $0FFFFF: 512KB RAM ($000000-$07FFFF), optional mirror, I/O peripherals ($A00000+). Contrast with the Spectrum's banked view above. |
| 15.12 | ADL mode vs Z80 mode comparison | TD | P2 | Side-by-side register diagram: Z80 mode (16-bit HL, BC, DE, SP) vs ADL mode (24-bit HL, BC, DE, SP). Show PUSH pushing 2 vs 3 bytes. Show address space: 64KB window vs full 16MB. |
| 15.13 | Platform comparison: Spectrum vs Agon | TD | P1 | Side-by-side infographic comparing the two platforms across key dimensions: CPU speed (3.5 vs 18.4 MHz), RAM (128KB banked vs 512KB flat), frame budget (71K vs 369K T), sprites (software vs hardware), scrolling (software vs hardware), sound (AY vs ESP32 audio). |
| 15.14 | VDP command flow diagram | FD | P2 | Sequence diagram: eZ80 sends VDU bytes via RST $10 -> UART serial -> ESP32 VDP receives, interprets, renders -> display output. Show latency at each stage. |

---

## Chapter 16: Fast Sprites

| # | Illustration title | Category | Priority | Description |
|---|-------------------|----------|----------|-------------|
| 16.1 | Six sprite methods comparison chart | TD | P1 | Bar chart comparing the six methods: XOR (1,700T), OR+AND masked (2,300T), pre-shifted masked (2,300T), stack/PUSH (810T), compiled no-mask (570T), compiled masked (1,088T). Group by masking support. This is the chapter's key reference figure. |
| 16.2 | XOR sprite: draw and erase cycle | PX | P1 | Three panels: (a) background before sprite, (b) after XOR draw (sprite visible, some pixels inverted over background detail), (c) after second XOR (background perfectly restored). Show the A XOR B XOR B = A property visually. |
| 16.3 | OR+AND masking sequence | PX | P1 | Single byte-level walkthrough: original screen byte, AND with mask (clears sprite-shaped hole), OR with graphic (stamps sprite). Show the 8 bits at each step with colour: background bits in blue, cleared bits in grey, sprite bits in red. |
| 16.4 | Mask + graphic data format | CS | P2 | Memory layout for one sprite row: mask_L, gfx_L, mask_R, gfx_R (4 bytes). Show a sample 16-pixel row with mask 1s (transparent) and 0s (opaque), and the corresponding graphic bits. |
| 16.5 | Pre-shifted sprite memory tradeoff | TD | P1 | Stacked bar chart showing memory cost: 1 copy (64B), 4 copies (256B), 8 copies at 3-byte width (768B). Then multiplied by 4 animation frames and 8 sprites: 2KB, 8KB, 24KB. Show as fraction of 128KB total RAM. |
| 16.6 | Byte alignment and the shift problem | PX | P2 | 8-pixel-wide byte grid showing a sprite at x=53 (byte column 6, pixel 5 within byte). The sprite straddles two bytes with 5 bits of shift. Show the overflow into a third byte column. Contrast with byte-aligned position. |
| 16.7 | Stack sprite: SP and screen addresses | CS | P1 | Diagram showing SP set to the bottom-right of the sprite's screen area, with PUSH writing upward through the interleaved screen. Show the problem: SP decrements linearly but screen rows are non-contiguous. Show per-row explicit SP loads as the solution. |
| 16.8 | Compiled sprite: instruction anatomy | CS | P2 | Memory dump of a compiled sprite routine: LD (HL),$3C (2 bytes), INC L (1 byte), LD (HL),$0F (2 bytes), DEC L, INC H. Show how code bytes ARE the sprite data. Contrast with data-driven approach (mask+gfx table + interpreter loop). |
| 16.9 | Compiled sprite with masking | CS | P2 | Four-instruction sequence per byte: LD A,(HL) / AND $C3 / OR $3C / LD (HL),A. Show the mask and graphic values baked into instruction operands. Compare cost: 28T per byte vs 52T in generic loop. |
| 16.10 | Dirty rectangle: save/restore/draw cycle | FD | P1 | Three-phase diagram per frame: (1) Restore old backgrounds (reverse order, arrows from save buffers to old screen positions), (2) Save new backgrounds (arrows from new screen positions to save buffers), (3) Draw sprites at new positions. Emphasise reverse-order restoration for overlap correctness. |
| 16.11 | Overlap ordering problem | PX | P2 | Two overlapping sprites A and B. Panel 1: A drawn on top of B (A's save buffer contains B's pixels). Panel 2: correct restoration (A first, then B reveals clean background). Panel 3: incorrect forward restoration (B first leaves A's ghost). |
| 16.12 | Full frame budget for 8 sprites | TD | P1 | Stacked bar showing per-frame cost breakdown: restore 8 backgrounds (11,200T), save 8 new backgrounds (11,200T), draw 8 sprites masked (18,400T), total 40,800T out of 71,680T. Show remaining 30,880T as "available for game logic." |
| 16.13 | Agon VDP sprite vs Spectrum software sprite | TD | P3 | Side-by-side comparison: Spectrum (6 methods, 570-2,300T per sprite draw, complex code) vs Agon (VDU command, ~1,660T per move for serial overhead, VDP handles rendering). Different bottlenecks visualised. |

---

## Chapter 17: Scrolling

| # | Illustration title | Category | Priority | Description |
|---|-------------------|----------|----------|-------------|
| 17.1 | Scrolling method cost comparison | TD | P1 | Bar chart comparing all methods from the summary table: full pixel horizontal (135,000T), full pixel vertical (107,000T), attribute only (17,000T), combined average (10,000T), combined peak (70,000T), shadow+tile redraw (59,000T), character scroll (52,000-66,000T). Horizontal line at 71,680T marking the frame budget. |
| 17.2 | Horizontal RL bit-shift chain | CS | P1 | Row of 32 bytes processed right-to-left. Show carry flag propagating from byte 31 to byte 0: bit 7 of each byte exits into carry, carry enters bit 0 of the next byte left. Arrows showing the pixel flow direction. Label: 21T per byte. |
| 17.3 | Interleaved screen and vertical scroll | PX | P1 | Diagram showing two adjacent pixel rows in the interleaved layout (row N at address $4x00, row N+1 at $4x00+$100 within a character cell, but different at char boundaries). Arrows showing the copy direction for scrolling up. Highlight the boundary crossing problem. |
| 17.4 | Combined scroll method: 8-frame cycle | FD | P1 | Timeline of 8 consecutive frames: frames 1-7 show only edge-column pixel shift (~6,700T each), frame 8 shows character scroll + new column draw + attribute update (~70,000T). Annotate average and peak costs. |
| 17.5 | Edge-column pixel shift | PX | P2 | Play area grid (20x20 chars) with only the 2 rightmost columns highlighted. Show the RL (HL) shift on those 2 bytes per row, with carry propagation between them. The rest of the screen is untouched. |
| 17.6 | Attribute LDIR scroll | CS | P2 | Linear attribute memory ($5800-$5AFF) with an arrow showing LDIR copying bytes 1-767 to positions 0-766. The rightmost column (every 32nd byte) receives new data. Simple, fast, 17,000T. |
| 17.7 | Shadow screen double-buffer scroll strategy | FD | P1 | Two-frame alternation: Frame N displays page 5 while tile renderer draws the scrolled scene into page 7. Frame N+1 flips to page 7 (tear-free), renderer works on page 5. Show the "redraw from tilemap" approach vs "shift existing data." |
| 17.8 | Tile-based rendering pipeline | FD | P2 | Pipeline for one tile: tilemap lookup (get tile index) -> tile data address (base + index*8) -> copy 8 bytes to screen (navigating interleave, 8 LDI ops). Show per-tile cost: ~180T. Total for 400 tiles: ~72,000T. |
| 17.9 | Ring-buffer column loading (Agon) | CS | P2 | Circular tilemap buffer (40 columns wide, screen shows 32). Write pointer updates the column that just scrolled off-screen with new level data. Read viewport wraps around. Hardware scroll offset advances smoothly. |
| 17.10 | Bidirectional scroll: RL vs RR | TD | P3 | Side-by-side: leftward scroll uses RL (HL) right-to-left, rightward scroll uses RR (HL) left-to-right. Both at 21T per byte. Show the SMC approach: patch RL/RR opcode and INC/DEC direction at runtime. |
| 17.11 | Spectrum vs Agon scrolling cost comparison | TD | P2 | Two-column comparison: Spectrum (10,000-135,000T per frame, software-driven, tearing risk) vs Agon (500-3,000T, hardware register + ring-buffer column load, no tearing). Show the ~20x CPU cost difference. |

---

## Chapter 18: Game Loop and Entity System

| # | Illustration title | Category | Priority | Description |
|---|-------------------|----------|----------|-------------|
| 18.1 | The game loop | FD | P1 | Circular flow diagram: HALT (sync) -> Read Input -> Update State -> Render -> back to HALT. Label the 50Hz heartbeat. Show the "miss a frame" case as a dashed bypass. |
| 18.2 | Frame budget breakdown for a game | TD | P1 | Pie chart or stacked bar: input (500T, 0.8%), entity update (8,000T, 12.5%), collision (4,000T, 6.3%), music (5,000T, 7.8%), sprite rendering (24,000T, 37.5%), scroll (12,000T, 18.8%), misc (3,000T, 4.7%), headroom (7,500T, 11.7%). On a 64,000T practical budget. |
| 18.3 | State machine dispatch | FD | P1 | Diagram showing game_state variable indexing into a jump table (DW state_title, DW state_menu, DW state_game, DW state_pause, DW state_gameover). Arrow from JP (HL) to the selected handler. Show O(1) dispatch cost (73T). |
| 18.4 | State transition graph | FD | P1 | Directed graph: TITLE -> MENU -> GAME -> PAUSE (bidirectional with GAME), GAME -> GAMEOVER -> TITLE. Label each transition with the trigger (FIRE key, P key, health=0). |
| 18.5 | Keyboard matrix: half-row layout | CS | P1 | Visual keyboard diagram showing the 8 half-rows with port addresses ($FE, $FD, $FB, $F7, $EF, $DF, $BF, $7F). Highlight the game control keys (Q, A, O, P, SPACE) and their bit positions within their respective half-rows. |
| 18.6 | Edge detection: press vs hold | TD | P2 | Timeline across 5 frames showing a key held for 3 frames. Row 1: raw input_flags (0,1,1,1,0). Row 2: input_prev (0,0,1,1,1). Row 3: input_pressed = current AND NOT prev (0,1,0,0,0). Show that input_pressed fires only on the first frame of the press. |
| 18.7 | Entity structure layout (10 bytes) | CS | P1 | Memory block with 10 labelled fields: X lo (offset 0), X hi (+1), Y (+2), type (+3), state (+4), anim_frame (+5), dx (+6), dy (+7), health (+8), flags (+9). Colour-code position fields, type/state, motion, and flags. |
| 18.8 | Entity array: slot assignments | CS | P1 | Array of 16 slots (0-15) shown as a strip. Slot 0 coloured as "Player", slots 1-8 as "Enemies", slots 9-15 as "Projectiles/Effects". Show the fixed partitioning. |
| 18.9 | 8.8 fixed-point X position | TD | P2 | Register pair diagram: H = integer pixel (0-255), L = fractional subpixel (0-255). Example: $0180 = pixel 1, fraction 128 = 1.5 pixels. Show ADD HL,DE adding velocity, with carry propagating from L to H. |
| 18.10 | Multiply-by-10 decomposition | TD | P3 | Arithmetic diagram: index * 10 = (index * 8) + (index * 2). Show the three ADD HL,HL shifts (x2, x4, x8) and the saved x2 term being added back. 94T total. |
| 18.11 | Object pool lifecycle | FD | P2 | Cycle diagram: spawn (find inactive slot, fill fields, set ACTIVE) -> update (per-type handler runs each frame) -> deactivate (clear flags, slot becomes available). Show a bullet traversing all three stages. |
| 18.12 | Type dispatch jump table | FD | P2 | Diagram: type byte (0-4) doubled as index into type_handlers table. Table entries: DW update_inactive, DW update_player, DW update_enemy, DW update_bullet, DW update_explosion. Arrow from JP (HL) to selected handler. Compare to chain-of-CP approach (O(n) vs O(1)). |
| 18.13 | IX vs HL access cost comparison | TD | P3 | Bar chart: LD A,(IX+n) at 19T vs LD A,(HL) at 7T. Show the "copy to registers" strategy: 4 IX loads (76T up front) then 10 register accesses (40T) vs 10 IX accesses (190T). Net saving: 74T per entity. |
| 18.14 | Complete game skeleton architecture | FD | P1 | Block diagram tying all pieces together: main_loop with HALT -> state dispatch (jump table) -> state_game handler calling: read_input_with_edges, update_entities (entity array iteration with type dispatch), render_entities, music. Show data flow: input_flags -> player update -> spawn_bullet -> projectile pool. |

---

## Summary Statistics

| Chapter | Illustrations | P1 | P2 | P3 |
|---------|-------------|----|----|-----|
| Ch13 | 9 | 3 | 4 | 2 |
| Ch14 | 10 | 4 | 3 | 3 |
| Ch15 | 14 | 6 | 6 | 2 |
| Ch16 | 13 | 5 | 5 | 3 |
| Ch17 | 11 | 4 | 5 | 2 |
| Ch18 | 14 | 6 | 5 | 3 |
| **Total** | **71** | **28** | **28** | **15** |

### Category Distribution

| Category | Count | Description |
|----------|-------|-------------|
| TD (Technical diagram) | 27 | Charts, cost comparisons, scatter plots, tradeoff visualisations |
| FD (Flow diagram) | 20 | Pipelines, state machines, lifecycles, frame sequences |
| PX (Pixel art / screenshot) | 9 | Screen rendering examples, visual walkthroughs, before/after |
| CS (Code structure) | 15 | Memory layouts, register maps, data formats, bit fields |

### Production Notes

1. **matplotlib** is the recommended tool for all TD-category diagrams. Use the same consistent style as Part 1: dark background (#1a1a2e), bright accent colours matching ZX Spectrum palette (blue #0000D7, red #D70000, green #00D700, yellow #D7D700, cyan #00D7D7, magenta #D700D7, white #D7D7D7).

2. **Mermaid** is recommended for all FD-category diagrams. Use flowchart LR or TD orientation depending on the flow direction.

3. **PX-category** illustrations can be generated programmatically (Python/PIL or the existing verify/ JS prototypes) or captured from emulator screenshots with annotation overlays.

4. **CS-category** diagrams work well as hand-drawn-style technical illustrations (similar to Patterson & Hennessy textbook diagrams) or as clean SVG boxes-and-arrows.

5. **Priority P1 illustrations** (28 total) should be created first -- these explain concepts that are genuinely hard to convey in text alone.

6. **Chapters 15 and 18 are illustration-heavy** (14 each) because they introduce many new architectural concepts (memory maps, platform comparisons, entity systems, state machines) that benefit strongly from visual reference material.

7. **Chapter 16's six-method comparison chart** (16.1) is arguably the single most important illustration in this batch -- it is the key reference figure that readers will return to repeatedly when choosing a sprite method.
