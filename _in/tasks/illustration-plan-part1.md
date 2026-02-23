# Illustration Plan -- Chapters 1-12

This document identifies illustrations needed for the first 12 chapters of "Coding the Impossible: Z80 Demoscene Techniques for Modern Makers." Each table lists proposed illustrations, their category, priority (P1 = essential, P2 = strongly recommended, P3 = nice to have), and a description of what the diagram should show.

**Categories:**
- **TD** = Technical diagram (matplotlib / vector graphics) -- memory layouts, waveforms, geometry, charts
- **FD** = Flow diagram (Mermaid / flowchart) -- loops, state machines, pipelines, timing
- **PX** = Pixel art / screenshot -- screen layout, rendering steps, colour examples
- **CS** = Code structure -- register maps, SMC flow, memory maps

---

## Chapter 1: Thinking in Cycles

| # | Illustration title | Category | Priority | Description |
|---|-------------------|----------|----------|-------------|
| 1.1 | T-state cost comparison bar chart | TD | P1 | Horizontal bar chart comparing T-state costs of common instructions (NOP=4, LD A,B=4, LD A,(HL)=7, PUSH HL=11, LDIR=21, OUT=11). Visually conveys the cost range at a glance. |
| 1.2 | Machine cycle breakdown | TD | P2 | Timing diagram showing M-cycles within an instruction (e.g. LD A,(HL)): M1 opcode fetch (4T), M2 memory read (3T). Show bus activity: address bus, data bus, timing ticks. |
| 1.3 | Frame budget comparison | TD | P1 | Stacked bar or pie chart showing 71,680 T-states on Pentagon divided into: music player (~4,000T), main effect (~40,000T), screen clear (~20,000T), idle. Versions for 48K, 128K, Pentagon side by side. |
| 1.4 | Border stripe timing harness | PX | P1 | Annotated screenshot of emulator output showing the red border stripe produced by the timing harness code. Labels: "HALT (sync)", "red = code under test", "black = idle", with scanline count annotation. |
| 1.5 | Multi-colour border profiler | PX | P2 | Screenshot showing red/blue/green/black border bands for the multi-phase profiler variant. Labels for each phase (sprites, music, game logic, idle). |
| 1.6 | "What fits in a frame" budget arithmetic | TD | P2 | Infographic-style diagram: frame budget (71,680T) as a measuring container, with labelled blocks showing how many sprites (8-12), LDIR bytes (3,413), or multiply ops (1,327) fit. |
| 1.7 | Agon vs Pentagon frame budget | TD | P3 | Side-by-side comparison of Pentagon (71,680T) vs Agon (~368,000T) frame budgets, showing the 5x ratio visually as scaled rectangles. |

---

## Chapter 2: The Screen as a Puzzle

| # | Illustration title | Category | Priority | Description |
|---|-------------------|----------|----------|-------------|
| 2.1 | Spectrum memory map overview | CS | P1 | Full 64KB memory map showing ROM ($0000-$3FFF), screen pixel area ($4000-$57FF), attributes ($5800-$5AFF), user RAM ($5B00-$FFFF). Colour-coded with sizes labelled. |
| 2.2 | Screen address bit layout | TD | P1 | Diagram showing how the Y coordinate bits (TT, LLL, SSS) and X coordinate bits (CCCCC) map into the 16-bit screen address. Show the bit fields in H and L registers with colour-coded groupings: `010 TT SSS | LLL CCCCC`. |
| 2.3 | Interleaved row order visualisation | PX | P1 | Visual grid showing the first 16 pixel rows with their addresses. Highlight how rows 0-7 (within char row 0) are at $4000, $4100, ..., $4700 -- not sequential. Show the jump pattern with arrows. |
| 2.4 | Three-thirds screen structure | PX | P2 | Full screen divided into thirds (top $4000, middle $4800, bottom $5000), each subdivided into 8 character rows, each into 8 scanlines. Hierarchical nesting diagram. |
| 2.5 | DOWN_HL decision tree | FD | P1 | Flowchart showing the three cases of DOWN_HL: (1) within char cell (INC H, 20T), (2) char boundary same third (77T), (3) third boundary (46T). Show frequency of each case. |
| 2.6 | Split-counter iteration diagram | FD | P2 | Nested loop diagram showing thirds (3) > char rows (8) > scanlines (8) with INC H in the inner loop, and the boundary handling at each level. Compare to naive DOWN_HL approach. |
| 2.7 | Attribute byte bit layout | CS | P1 | Bit field diagram for the attribute byte: F(1), B(1), PAPER(3), INK(3). Show the 8 colour swatches for both normal and BRIGHT variants. |
| 2.8 | Attribute clash illustration | PX | P1 | Side-by-side: (a) hypothetical per-pixel colour showing a red sprite on green background, (b) actual Spectrum rendering showing the 8x8 cell forced to choose one pair. Exaggerated example with grid overlay. |
| 2.9 | Pixel-to-attribute address conversion | TD | P2 | Diagram showing the bit manipulation from pixel address (010TTSSS, LLLCCCCC) to attribute address (010110TT, LLLCCCCC). Show bits being extracted, rotated, and recombined. |
| 2.10 | Linear vs interleaved fill comparison | PX | P3 | Two screenshots: (a) sequential byte fill showing how the interleave creates stripes, (b) correct fill filling all rows uniformly. Demonstrates why the interleave matters for patterned fills. |

---

## Chapter 3: The Demoscener's Toolbox

| # | Illustration title | Category | Priority | Description |
|---|-------------------|----------|----------|-------------|
| 3.1 | Loop overhead visualisation | TD | P1 | Pie chart or stacked bar for one loop iteration (LD (HL),A + INC HL + DJNZ = 26T) showing 7T useful work vs 19T overhead (73% waste). Adjacent bar for unrolled version (13T, 0% overhead). |
| 3.2 | PUSH vs LDIR speed comparison | TD | P1 | Bar chart comparing bytes-per-T-state for: LD (HL),A+INC HL (13T/byte), LDI (16T), LDIR (21T), PUSH (5.5T/byte). The PUSH bar should visually dominate. |
| 3.3 | Stack-as-data-pipe memory diagram | CS | P1 | Memory map showing SP pointed at $5800 (end of screen), PUSH writing downward through pixel data. Show DI/EI guards, SP save/restore via SMC. Annotate the direction of the "data pipe." |
| 3.4 | Self-modifying code: operand patching | CS | P2 | Instruction bytes in memory (opcode, operand1, operand2) with an arrow showing LD (patch+1),A writing into the operand byte. Show before/after state of the patched instruction. |
| 3.5 | LDI chain with variable entry point | CS | P2 | Diagram of a chain of 256 LDI instructions in memory, with a calculated jump arrow entering at position 156 to copy only 100 bytes. Show the entry point arithmetic. |
| 3.6 | RET-chaining dispatch diagram | FD | P1 | Show SP pointing to a render list (table of addresses). RET pops the first address, jumps to draw_tile_42, which ends with RET, popping the next address (draw_tile_7), and so on. Show the stack unwinding through the dispatch table. |
| 3.7 | Technique composition matrix | TD | P2 | Table/matrix showing which techniques combine in practice: screen clearing = unrolled + PUSH + SMC, compiled sprites = codegen + PUSH + SMC, tile engines = RET-chain + LDI, chaos zoomers = offline codegen + LDI + SMC. |

---

## Chapter 4: The Maths You Actually Need

| # | Illustration title | Category | Priority | Description |
|---|-------------------|----------|----------|-------------|
| 4.1 | Shift-and-add multiply walkthrough | TD | P1 | Step-by-step diagram of 8x8 multiply (e.g., 13 x 11): show 8 iterations with the multiplier bits, carry, accumulator shifts, and partial products building up. Highlight which iterations trigger ADD. |
| 4.2 | Square table multiply: algebraic identity | TD | P2 | Visual proof of A*B = ((A+B)^2 - (A-B)^2)/4. Show the two table lookups as arrows into a parabola plot, with the subtraction yielding the product. |
| 4.3 | Speed vs accuracy trade-off chart | TD | P1 | Scatter plot with axes: T-states (horizontal) vs precision error (vertical). Points for shift-and-add (200T, exact), square-table (61T, +/-0.25), showing the speed-accuracy frontier. |
| 4.4 | Parabolic sine approximation | TD | P1 | Overlay plot: true sine wave vs parabolic approximation, over one full period (0-255 index). Mark the maximum error (~5.6%). Show the 256-byte table concept with discrete samples. |
| 4.5 | Sine table memory layout | CS | P2 | Page-aligned 256-byte table in memory. Show how H holds the table base and L is the raw angle index. Demonstrate cosine access by adding 64 to L. |
| 4.6 | Bresenham matrix method: 8x8 grid | TD | P1 | An 8x8 pixel grid showing a line segment at ~30 degrees. Highlight the SET bit positions and INC H step. Compare to classical Bresenham with per-pixel branch overhead. |
| 4.7 | Fixed-point 8.8 format | CS | P2 | Register pair HL with H = integer part, L = fractional part. Show examples: $0180 = 1.5, $FF80 = -0.5 (signed). Bit boundaries clearly marked. |
| 4.8 | 3D pipeline cost breakdown | TD | P2 | Waterfall/cascade chart showing per-frame cost of a spinning cube: rotation (19,200T) + projection (480T) + line drawing (23,040T) = ~42,720T out of 71,680T budget. |

---

## Chapter 5: 3D on 3.5 MHz

| # | Illustration title | Category | Priority | Description |
|---|-------------------|----------|----------|-------------|
| 5.1 | Midpoint method: vertex derivation | TD | P1 | 3D wireframe showing 4 basis vertices (large dots), 4 mirrored vertices (medium dots), and derived midpoint vertices (small dots) connected by averaging arrows. Show the cost: 2,400T vs 36T labels. |
| 5.2 | Virtual processor architecture | CS | P1 | Diagram of the virtual processor: one working register (3 bytes: x,y,z), 64 cells of point RAM, and 4 instruction opcodes (Load, Store, Average, End) with their bit encodings (00nnnnnn, 01nnnnnn, 10nnnnnn, 11------). |
| 5.3 | Virtual processor program execution trace | FD | P2 | Step-by-step trace of a short midpoint program (e.g., 6 instructions). Show the working register and cell contents at each step, with averaging operations highlighted. |
| 5.4 | Sequential rotation (Z, Y, X axes) | TD | P2 | Three coordinate system diagrams showing rotation around each axis in sequence: Z (affects X,Y), Y (affects X,Z), X (affects Y,Z). Show the 4 multiplies per axis. |
| 5.5 | Perspective projection geometry | TD | P1 | Side-view diagram showing camera, projection plane (screen), and a 3D point. Show how X_screen = (X * Scale) / (Z + Z_distance). Label the projection parameters. |
| 5.6 | Backface culling: normal vector test | TD | P2 | Polygon face with edge vectors V and W, showing the cross product normal pointing toward or away from the viewer. Label the sign test (positive = visible, negative = cull). |
| 5.7 | Complete 3D frame pipeline | FD | P1 | Flow diagram: Update angles -> Rotate basis -> Negate mirrors -> Run midpoint program -> Project all -> Backface cull -> Z-sort -> Fill polygons -> HALT. With T-state costs at each stage. |
| 5.8 | Midpoint derivation chain depth | TD | P3 | Tree diagram showing how v8 = avg(v0,v1), v9 = avg(v2,v3), v11 = avg(v8,v9) -- multi-level derivation. Show cumulative rounding error per level. |

---

## Chapter 6: The Sphere -- Texture Mapping on 3.5 MHz

| # | Illustration title | Category | Priority | Description |
|---|-------------------|----------|----------|-------------|
| 6.1 | Sphere projection: skip distances | TD | P1 | Cross-section of sphere showing how screen pixels map to texture pixels. At equator: uniform spacing (skip=1). Near poles: compressed (skip=3-4). Draw the sphere outline with horizontal scanlines and arrows showing sampling intervals. |
| 6.2 | Inner loop: bit accumulation | CS | P1 | Diagram showing 8 source pixels (0/1) being accumulated into one screen byte via ADD A,A + ADD A,(HL). Show the accumulator state after each step, with INC L advances between samples. |
| 6.3 | Runtime code generation pipeline | FD | P1 | Pipeline: Skip tables -> Code generator -> Code buffer (opcodes) -> Execute -> Screen. Show the flow from precomputed geometry to generated Z80 instructions to rendered output. |
| 6.4 | Cost formula visualisation | TD | P2 | Graph of "101 + 32x" T-states per byte, with x-axis showing position on sphere (equator to pole) and y-axis showing cost. Overlay the sphere width (bytes per line) to show total workload balancing. |
| 6.5 | Source texture memory layout | CS | P2 | Page-aligned 256-byte rows of 1-byte-per-pixel texture data. Show how INC L wraps within a page, and how H selects the row. Highlight the constraint: each scanline must fit in 256 bytes. |
| 6.6 | Precompute/generate/execute pattern | FD | P2 | Three-box pattern used throughout the book: (1) Precomputation (tables), (2) Code generation (emit opcodes), (3) Sequential execution (read-shift-write). Show how this pattern applies to sphere, rotozoomer, and dotfield. |

---

## Chapter 7: Rotozoomer and Chunky Pixels

| # | Illustration title | Category | Priority | Description |
|---|-------------------|----------|----------|-------------|
| 7.1 | Rotozoomer texture walk | TD | P1 | 2D texture grid with a diagonal walk path overlaid. Show step vectors (dx, dy) from the rotation angle. Highlight how "walking at an angle" through the texture = rotation on screen. |
| 7.2 | Chunky pixel comparison: 2x2, 4x4, 8x8 | PX | P1 | Same rotozoomer pattern rendered at three resolutions (128x96, 64x48, 32x24). Side-by-side comparison showing quality vs performance trade-off. Can be generated from the verify/ JS prototypes. |
| 7.3 | 8-direction walk instructions | CS | P2 | Octagonal compass rose showing the 8 primary walk directions and their Z80 instruction pairs (e.g., 0deg = NOP+INC L, 45deg = DEC H+INC L, 90deg = DEC H+NOP, etc.). |
| 7.4 | Chunky pixel encoding: $03/$00 | CS | P2 | Show how ADD A,A twice shifts $03 into position, then ADD A,(HL) merges the next pixel. Trace 4 chunky pixels combining into one output byte with bit-level detail. |
| 7.5 | Chunky rendering optimisation chart | TD | P2 | Bar chart comparing the 4 approaches from sq's article: Basic LD/INC (101T), LDI (104T), LDD (80T), SMC/256 procs (76-78T). Annotate with memory cost. |
| 7.6 | Buffer-to-screen transfer | CS | P3 | Diagram showing POP HL reading from linear buffer, LD (screen_addr),HL writing to interleaved screen memory. Show the pre-calculated screen addresses embedded as operands. |
| 7.7 | Bresenham-like step distribution | TD | P3 | For a 30-degree rotation, show the distribution of INC L+NOP vs INC L+DEC H pairs across a scanline. Error accumulator diagram similar to Bresenham line drawing. |

---

## Chapter 8: Multicolor -- Breaking the Attribute Grid

| # | Illustration title | Category | Priority | Description |
|---|-------------------|----------|----------|-------------|
| 8.1 | ULA scanline timing diagram | FD | P1 | Timeline showing one character row (8 scanlines x 224T). Mark when the ULA reads attribute bytes for each scanline. Show the window between reads where the CPU can change attributes. |
| 8.2 | 8x2 multicolor resolution | PX | P1 | Single 8x8 character cell split into 4 horizontal bands (2 scanlines each), each with independent ink/paper. Show the visual improvement: 8 colours per cell vs the standard 2. |
| 8.3 | LDPUSH instruction anatomy | CS | P1 | Memory diagram showing LD DE,$AABB (3 bytes: opcode + operand_lo + operand_hi) followed by PUSH DE (1 byte). Show SP decrementing, data flowing from the operand bytes to screen memory. Highlight that operand bytes ARE the display data. |
| 8.4 | GLUF two-frame architecture | FD | P1 | Dual-frame timeline: Frame 1 (attribute changes + partial tile rendering) and Frame 2 (finish tiles + sprite overlay). Show the alternation and what happens in each phase. |
| 8.5 | Double-buffered display code | CS | P2 | Two blocks of LDPUSH code in memory. While Buffer A executes (writes to screen), Buffer B is being patched with new tile/sprite data. Arrows show the flip between frames. |
| 8.6 | Tile patching into LDPUSH buffer | CS | P2 | Zoomed view of display code bytes: opcode-operand-operand-opcode-operand-operand. Show a tile renderer writing pixel data into the operand byte positions, skipping over opcode bytes. |
| 8.7 | Ringo dual-screen technique | TD | P1 | Diagram showing the $F0 pixel pattern splitting each cell into left (ink) and right (paper) halves. Two screens with different attributes, switching every 4 scanlines. Show the resulting 64x48 grid with independent colours. |
| 8.8 | Multicolor technique comparison table | TD | P2 | Visual comparison: traditional (80-90% CPU), GLUF/LDPUSH (70,000T, game-ready), Ringo (minimal CPU, 64x48). Show resolution, CPU cost, and use case for each. |

---

## Chapter 9: Attribute Tunnels and Chaos Zoomers

| # | Illustration title | Category | Priority | Description |
|---|-------------------|----------|----------|-------------|
| 9.1 | Attribute grid as framebuffer | PX | P1 | Full Spectrum screen showing a checkerboard pixel pattern in the bitmap, with the attribute grid overlaid. Demonstrate how changing attribute bytes alone creates the visual effect. Show 32x24 "pixel" resolution. |
| 9.2 | Plasma sum-of-sines visualisation | TD | P1 | Three individual sine waves (different frequencies, phases) plotted separately, then their sum, then the sum mapped to a colour palette. Show how the interference creates concentric ring patterns resembling a tunnel. |
| 9.3 | Four-fold symmetry copy pattern | TD | P1 | 32x24 grid divided into quadrants. Show the top-left quadrant being calculated, then arrows for horizontal mirror (top-right), vertical mirror (bottom-left), and both (bottom-right). Label the copy cost: ~2,880T for full screen. |
| 9.4 | Chaos zoomer: source-to-destination mapping | TD | P2 | Two grids (source and output). Arrows from source cells to output cells, showing magnification at center (many arrows from nearby cells) and compression at edges (arrows from distant cells). |
| 9.5 | Code generation pipeline (Processing to Z80) | FD | P2 | Pipeline diagram: Processing script -> calculates zoom mappings -> outputs .a80 source -> sjasmplus compiles -> Z80 executes pre-generated LDI chains. Show the offline/runtime split. |
| 9.6 | Eager async architecture overview | FD | P2 | High-level block diagram of Eager: scripting engine (outer + inner scripts) feeding the frame generator, ring buffer of attribute frames, display system reading at 50Hz, digital drums consuming CPU bursts. Preview of Ch12 architecture. |

---

## Chapter 10: The Dotfield Scroller and 4-Phase Colour

| # | Illustration title | Category | Priority | Description |
|---|-------------------|----------|----------|-------------|
| 10.1 | Dotfield scroller: bouncing text | PX | P1 | Screenshot-style rendering of "ILLUSION" as individual dots undulating in a sine wave. Show the dot positions displaced vertically per column. Annotate: each dot = 1 pixel, font bits determine which dots exist. |
| 10.2 | Stack-based address table | CS | P1 | Memory diagram: SP points to a table of 16-bit screen addresses. Each POP reads one address (10T), which includes the pre-baked sine-wave bounce offset. Show how the "bounce" is encoded in the address data, not computed at runtime. |
| 10.3 | Inner loop per-pixel cost breakdown | TD | P2 | Timeline showing one font byte (8 pixels). For each pixel: POP HL (10T), RLA (4T), JR NC (7T or 12T), SET N,(HL) (15T for opaque). Colour-code opaque vs transparent paths. Show amortised byte-fetch overhead. |
| 10.4 | 4-phase colour: frame cycle diagram | TD | P1 | Four frames in sequence: Normal A (ink=C1, paper=C2), Normal B (ink=C3, paper=C4), Inverted A (ink=C2, paper=C1), Inverted B (ink=C4, paper=C3). Show a single pixel's colour across all 4 frames, and the perceived average. |
| 10.5 | Perceived colour averaging | TD | P2 | Colour mixing diagram: for a pixel "on" in pattern A and "off" in B, show it cycling through C1, C4, C2, C3. Visual averaging (like overlapping coloured filters) demonstrating how 4 distinct colours merge into a perceived intermediate colour. |
| 10.6 | Temporal vs spatial cheating axes | TD | P2 | 2D diagram with axes: spatial resolution (horizontal) and temporal resolution (vertical). Place the dotfield scroller (high spatial, uses motion) and 4-phase colour (high temporal, uses frame alternation) at their respective positions. |
| 10.7 | Dithering pattern comparison | PX | P3 | Grid showing different dithering patterns (checkerboard, 2x2 blocks, Bayer 4x4, random) and how they affect flicker visibility in the 4-phase technique. |

---

## Chapter 11: Sound Architecture -- AY, TurboSound, and Triple AY

| # | Illustration title | Category | Priority | Description |
|---|-------------------|----------|----------|-------------|
| 11.1 | AY-3-8910 register map | CS | P1 | Complete register map as a visual block diagram: R0-R5 (tone periods for A/B/C), R6 (noise), R7 (mixer), R8-R10 (volume/envelope mode), R11-R12 (envelope period), R13 (envelope shape). Colour-coded by function group. |
| 11.2 | R7 mixer bit layout | CS | P1 | Bit field diagram for register R7 showing all 8 bits. Highlight the active-low logic (0 = ON). Include a truth table for common combinations (all tones, tone+noise, silence). |
| 11.3 | Envelope waveform shapes | TD | P1 | All 10 unique envelope shapes plotted as volume-over-time graphs. Group by behaviour: single decay ($00), single attack ($04), repeating sawtooth down ($08), repeating sawtooth up ($0C), triangles ($0A, $0E), hold-at-max ($0B, $0D). |
| 11.4 | Tone period to frequency chart | TD | P2 | Plot of frequency vs period value (12-bit range). Mark the musical note positions (C4, A4, etc.). Show the logarithmic relationship. |
| 11.5 | Arpeggio timing diagram | TD | P2 | Timeline across 6 frames at 50Hz showing channel A cycling through C4, E4, G4, C4, E4, G4. Show the frequency of each frame. Indicate "perceived chord" bracket above. |
| 11.6 | Buzz-bass: envelope abuse | TD | P2 | Waveform diagram showing repeating sawtooth envelope at a period matching the desired bass note. Compare to a plain square wave at the same frequency. Show how the envelope repetition creates the characteristic "buzz" timbre. |
| 11.7 | TurboSound: dual AY block diagram | CS | P1 | Two AY chip blocks with chip select logic. Show port $FFFD write $FF/$FE selecting chip 0/1. Show 6 total channels with stereo panning possibilities. |
| 11.8 | Triple AY (Next): 9-channel arrangement | CS | P2 | Three AY chip blocks with per-channel panning controls. Show a typical orchestral assignment (bass, lead, drums, harmony, etc.) across all 9 channels. |
| 11.9 | Music engine frame budget | TD | P2 | Bar chart showing typical T-state costs: simple player (1,500-2,500T), PT3 player (3,000-5,000T), VT2 with effects (4,000-7,000T), TurboSound (6,000-10,000T). Show these as fractions of the 71,680T frame. |
| 11.10 | IM2 interrupt handler flow | FD | P2 | Flowchart: interrupt fires -> push registers -> call music_play -> decrement speed counter -> if zero: process channels, apply ornaments, calculate periods -> write 14 AY registers -> pop registers -> RETI. |
| 11.11 | SFX channel stealing diagram | FD | P3 | Timeline showing channel C playing music, then SFX triggers (overrides channel C for N frames), then music resumes on channel C. Show the priority-based preemption. |

---

## Chapter 12: Digital Drums and Music Sync

| # | Illustration title | Category | Priority | Description |
|---|-------------------|----------|----------|-------------|
| 12.1 | Hybrid drum: digital attack + AY decay | TD | P1 | Waveform diagram with two phases: (1) digital PCM samples driving the volume register (jagged, high-frequency), (2) AY envelope taking over for the smooth decay tail. Mark the handoff point. Label CPU cost per phase. |
| 12.2 | CPU consumption during drum hit | TD | P1 | Frame timeline (50Hz ticks) showing normal operation, then 2 frames consumed by drum playback (hatched/red), then normal operation resumes. Show that the display continues but no new frames are generated. |
| 12.3 | Asynchronous frame buffer dynamics | TD | P1 | Producer-consumer diagram: generator fills ring buffer (variable rate), display drains it at 50Hz. Show buffer level over time: gradual fill between drums, sharp drain during drum hits, recovery after. |
| 12.4 | Ring buffer architecture | CS | P1 | Circular buffer of 8 attribute frames (768 bytes each). Write pointer (generator), read pointer (display ISR). Show the wrap-around and the count variable. Include the 128K memory bank hosting the buffer. |
| 12.5 | Two-level scripting system | FD | P1 | Hierarchical diagram: Outer script (effect sequence + durations) containing Inner scripts (per-effect parameter changes keyed to frame numbers). Show kWORK command generating a batch of frames. |
| 12.6 | kWORK: decouple generation from display | FD | P2 | Timeline: generator produces 8 frames in a burst (kWORK 8), then yields. Display shows them one-per-frame at 50Hz over 160ms. During playback, generator is free for drum handling or next batch. |
| 12.7 | GABBA video editor workflow | FD | P2 | Pipeline: compose music (frame markers) -> record effects in emulator -> arrange in video editor (Luma Fusion) -> extract sync frame numbers -> write into Z80 script data. Show the creative iteration loop. |
| 12.8 | Z80 threading: context switch | FD | P2 | Two-thread alternation diagram: Frame 1 (Thread 1 runs), IM2 interrupt -> SwitchThread -> Frame 2 (Thread 2 runs), IM2 -> SwitchThread -> Frame 3 (Thread 1), etc. Show SP and memory page switching at each context switch. |
| 12.9 | Demo engine architecture overview | FD | P1 | Complete block diagram tying together: IM2 ISR (music player + display consumer), main loop (drum check, frame generator, script advance), ring buffer, timeline script. Show data flow and control signals (drum_pending flag as mailbox). |
| 12.10 | Sync technique comparison | TD | P3 | Table/matrix comparing Introspec's approach (code-based, asynchronous buffer), diver4d's approach (video editor timeline), and Robus's approach (Z80 threading). Columns: iteration speed, flexibility, CPU model, best use case. |

---

## Summary Statistics

| Chapter | Illustrations | P1 | P2 | P3 |
|---------|-------------|----|----|-----|
| Ch01 | 7 | 3 | 3 | 1 |
| Ch02 | 10 | 5 | 3 | 2 |
| Ch03 | 7 | 3 | 3 | 1 |
| Ch04 | 8 | 4 | 3 | 1 |  -- note: was 4+4+0, adjusted
| Ch05 | 8 | 3 | 4 | 1 |
| Ch06 | 6 | 3 | 3 | 0 |
| Ch07 | 7 | 2 | 3 | 2 |
| Ch08 | 8 | 4 | 3 | 1 |  -- note: was 3+4+1, adjusted
| Ch09 | 6 | 3 | 3 | 0 |
| Ch10 | 7 | 2 | 3 | 2 |
| Ch11 | 11 | 4 | 5 | 2 |  -- note: was 3+6+2, adjusted
| Ch12 | 10 | 5 | 4 | 1 |
| **Total** | **95** | **41** | **39** | **15** |

### Category Distribution

| Category | Count | Description |
|----------|-------|-------------|
| TD (Technical diagram) | 40 | Charts, waveforms, geometry, comparisons |
| FD (Flow diagram) | 24 | Pipelines, state machines, timing, architectures |
| PX (Pixel art / screenshot) | 13 | Screen renders, visual comparisons, emulator output |
| CS (Code structure) | 18 | Register maps, memory layouts, instruction anatomy |

### Production Notes

1. **matplotlib** is the recommended tool for all TD-category diagrams. Use a consistent style: dark background (#1a1a2e), bright accent colours matching ZX Spectrum palette (blue #0000D7, red #D70000, green #00D700, yellow #D7D700, cyan #00D7D7, magenta #D700D7, white #D7D7D7).

2. **Mermaid** is recommended for all FD-category diagrams. Use flowchart LR or TD orientation depending on the flow direction.

3. **PX-category** illustrations can be generated programmatically (Python/PIL or the existing verify/ JS prototypes) or captured from emulator screenshots with annotation overlays.

4. **CS-category** diagrams work well as hand-drawn-style technical illustrations (similar to Patterson & Hennessy textbook diagrams) or as clean SVG boxes-and-arrows.

5. **Priority P1 illustrations** (41 total) should be created first -- these explain concepts that are genuinely hard to convey in text alone.
