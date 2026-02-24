# ZXDN Graphics & 3D Articles — Analysis

Analyzed from the ZXDN article archive at `_in/raw/zxdn/coding/`.
All articles are from the late-1990s ZX Spectrum demoscene press (Russian).

---

## 1. zpw3gf3d.txt — Fast 3D Graphics for Speccy

**Author:** Ruff/Avalon/Rush/ASM (1997), with commentary by Viator/Avalon (1998) and errata by Pelepejchenko Aleksandr (ZX Power #4, 1999)
**Source:** ZX Power #3, Kharkov, 1998 (+ ZX Power #4, 1999)

### Key Techniques

**"Axis table" method for fast 3D point rotation:**

Instead of rotating each 3D point individually via matrix multiplication (6 multiplies per point), Ruff proposes pre-calculating the entire coordinate space of each axis as a 64-entry lookup table. The core insight: *rotate the axes, not the points*.

The procedure `K64` linearly interpolates 64 intermediate values between the center (0,0) and the rotated endpoint of each axis. This is done via Bresenham-style fixed-point addition in an unrolled DUP 64 loop:

```z80
DUP 64
LD A,H
ADD HL,DE     ; fixed-point step
LD (BC),A     ; store integer part
INC C
EDUP
```

To find a 3D point's screen position, you simply sum three table lookups (one per axis) plus the center offset:

```
Screen_Y = AxisY_table[pointY] + AxisX_table[pointX] + AxisZ_table[pointZ] + Center_Y
Screen_X = similar for X
```

The PRINT routine does this with 5 `ADD A,(HL)` instructions and `INC H` for axis table page switching, achieving ~200 T-states per point.

**Point plotting + delete buffer:** Each plotted point's screen address is pushed onto a "delete buffer" for fast erasure next frame (POP HL: LD (HL),0 chain).

### Innovations vs Standard Methods

- **No multiply needed at render time** — just 3 table lookups + adds per coordinate. Traditional rotation needs 4-6 multiplies per point.
- **175 vectors in one frame** vs 28 in Echology (Slovak demo). Claimed 6x faster.
- **Deformation for free** — stretching/squashing the object is just changing axis endpoints.
- Similar to "midpoint method" from Spectrum Expert #2, but independently developed.

### Errata (ZX Power #4)

Pelepejchenko found multiple bugs:
- Swapped PUSH order in the AX routine (coordinate stack misalignment)
- `SBC HL,DE` / `LD A,H` order was inverted in LOOP3 (off-by-one in table)
- Unnecessary `SUB 32` centering code in AX entry
- Published a corrected version from working sources
- Proposed optimization: eliminate EXX by using BC instead of HL', saving 3072 T-states (8*64*2*3) per axis recalculation

### What's NEW vs Our Book

**Our Ch.5 covers:** rotation matrices, sine tables, perspective projection, wireframe cube.

**New material:**
- The "axis table" method is a fundamentally different approach to 3D rotation — it's NOT matrix multiplication at all. Our Ch.5 uses the standard approach; this technique could be an advanced sidebar or section.
- Delete buffer pattern for fast screen erasure is a practical technique we don't describe.
- The DUP 64 unrolled Bresenham interpolation pattern is worth showing as an alternative to our sine-table approach.
- The comparison with Echology (28 vectors vs 175) gives concrete performance data for the book.

### Notable Code Patterns

- `LD (SAV+1),SP` / `LD SP,0` + `RET` — SMC to save/restore stack pointer
- Delete buffer: push addresses during render, pop+zero during erase
- `DUP 64 / EDUP` unrolled loops for table generation
- IX split into HX/LX for storing center coordinates (undocumented Z80 ops)

---

## 2. sng1bump.htm — Phong Bump Mapping on Speccy

**Author:** Flying/DR (written autumn 1997, published 1999)
**Source:** Scenergy #1, Novgorod, 1999

### Key Techniques

**Full derivation of bump mapping from mathematical model to optimized Z80 inner loop.**

The algorithm:
1. An image stores "height" per pixel (not color) — the bump map
2. For each pixel, compute pseudo-normal by differencing adjacent heights: `nx = Image(x+1,y) - Image(x-1,y)`, `ny = Image(x,y+1) - Image(x,y-1)`
3. Compute light vector: `vlx = x - lx`, `vly = y - ly`
4. Combine: `col = 15 - sqrt(difx^2 + dify^2)` where `difx = abs(vlx - nx)`
5. Key optimization: the sqrt+sqr function maps to a 16x16=256-byte lookup table

**Critical optimizations:**
- Pre-convert the image to (nx, ny) pairs — fetch via `POP HL` (10 T-states for both values)
- Store vlx in C, vly in B; then `ADD HL,BC` computes both difx and dify simultaneously in one instruction (11 T-states!)
- Light spot table is placed at page-aligned addresses so H=vly+ny directly indexes the correct row
- Inner loop: `POP HL` / `ADD HL,BC` / `LD A,(HL)` / `LD (DE),A` / `INC E` / `INC C` = **43 T-states/byte**
- Further optimization using `LDD` instead of explicit INC: `POP HL` / `ADD HL,BC` / `LDD` = **37 T-states/byte** (auto-corrects DE and BC)

**Variable-shape light spots:** The author also describes creating non-circular light patterns using a sector table + gradient table, allowing star-shaped or rayed light spots instead of the ubiquitous circle.

### Innovations

- The `ADD HL,BC` trick to compute two independent additions simultaneously is elegant and not widely documented
- Using `LDD` for auto-decrement of both buffer pointer and vlx counter is creative (requires mirroring the bump image in X)
- Pre-converting bump image to normals trades memory for speed
- References Binary Love demo (ENLiGHT'97) as implementation example

### What's NEW vs Our Book

**Our Ch.6 covers:** sphere rendering, texture mapping via skip tables.

**New material:**
- Bump mapping algorithm is entirely absent from our book. This is a major demoscene technique.
- The `ADD HL,BC` dual-addition trick is a general optimization pattern worth documenting.
- `LDD` inner loop at 37 T/byte is faster than most chunky output methods.
- Light spot shape variations (sector table approach) — creative extension we don't cover.
- 16x16 sqrt lookup table for approximating circular distance.

### Notable Code Patterns

```z80
; 43 T-states/byte bump mapping inner loop
POP HL      ; 10T: fetch nx,ny pair
ADD HL,BC   ; 11T: H=vly+ny, L=vlx+nx simultaneously
LD A,(HL)   ;  7T: lookup brightness from light table
LD (DE),A   ;  7T: write to screen buffer
INC E       ;  4T: next screen byte
INC C       ;  4T: advance vlx
```

---

## 3. sng2txmp.htm — Texture Mapping

**Author:** SaiR00S/EI (Eternity Industry), 1999
**Source:** Scenergy #2, Novgorod, 2000

### Key Techniques

**Standard linear texture mapping on triangles with complete Z80 implementation.**

Algorithm:
1. Sort triangle vertices by Y coordinate (bubble sort with EXX for texture coords)
2. Determine bend point (left or right) using `W = interpolated_X - vert2.x`
3. Build edge tables: TableLeftX[], TableRightX[], TableU[], TableV[] via linear interpolation
4. Compute constant texture steps: `DeltaU`, `DeltaV` (fixed-point 8.8 with sign)
5. Rasterize scanlines left-to-right, interpolating U,V

**Inner loop:**
```z80
LD A,H       ; V-coordinate in texture
ADD HL,DE    ; next V (fixed-point 8.8)
EXX
LD B,A
LD C,H       ; U-coordinate in texture
ADD HL,DE    ; next U (fixed-point 8.8)
LD A,(BC)    ; fetch texel
EXX
LD (BC),A    ; write to buffer
INC C        ; next X
```

**Vertex sorting with EXX:** Sorts three vertices + their texture coordinates simultaneously by swapping both register sets. Uses `LD A,L,L,C,C,A` notation (STORM assembler multi-assignment syntax for three-way swap).

### Innovations

- Bresenham interpolation mentioned as faster alternative to division-based delta computation
- Fixed-point 8.8 throughout for both screen and texture coordinates
- Texture step (DeltaU, DeltaV) is constant for the entire polygon, computed once per triangle

### What's NEW vs Our Book

**Our Ch.6 covers:** sphere rendering, texture mapping via skip tables.

**New material:**
- This is a proper triangle-rasterizing texture mapper, vs our sphere-specific skip-table approach. Completely different algorithm.
- Edge table construction (left/right boundary arrays) is a standard technique we should reference.
- The vertex sorting code with EXX is a nice pattern for parallel data manipulation.
- Fixed-point 8.8 inner loop for texture interpolation is more general than our skip-table method.

### Notable Code Patterns

- Three-way vertex sort with texture coordinates using EXX shadow registers
- `ADD HL,DE` for fixed-point 8.8 stepping (H = integer, L = fraction)
- `LD A,(BC)` for texel fetch where B = V, C = U (256-byte aligned texture)

---

## 4. sng2txph.txt — Texture Mapping + Phong Shading

**Author:** Senat/Eternity Industry, 1999 (18.09.999)
**Source:** Scenergy #2, Novgorod, 2000

### Key Techniques

**Combined texture mapping + Phong specular highlight on a 3D polygon.**

This describes the effect seen in Eternity Industry's "Napalm" demo — a rotating hemisphere with an eye texture and a moving specular highlight.

**Core inner loop (stack-driven):**
```z80
POP  HL      ; texture offset delta (from stack)
ADD  HL,BC   ; add to current scanline texture position
LD   A,(HL)  ; fetch texture color (0-15)
EXX
POP  HL      ; light spot texture offset delta
ADD  HL,BC   ; add to current scanline light position
ADD  A,(HL)  ; combine texture + light intensity
LD   E,A     ; lookup clamped result
LD   A,(DE)  ; fetch from saturation table (clamps >15 to 15)
EXX
LD   (DE),A  ; write to output buffer
INC  E       ; next pixel
```

**Key details:**
- Two textures needed: object texture (64x64) + light spot texture (64x64), both in a single 128K page
- Memory layout: 4 textures fit in one page, each 64 bytes wide, interleaved at #100-byte row stride
- Output buffer: 38 x 256 bytes (256 wide to avoid X-clipping). Fits 2-frame C2P at standard speed.
- Saturation table: handles overflow when texture + light > 15 (no Z80 saturating add)
- **Must run with interrupts disabled** (stack used for data)
- Precalculations are 2x those of plain texture mapping (edge interpolation for both texture and light coordinates)

### Innovations

- Stack-driven scanline rendering: texture deltas are pre-pushed onto the stack, then POPped during rasterization. This avoids index register overhead.
- Saturation table for color clamping (`ADD A,(HL)` can overflow; table maps 0-31 to 0-15)
- Dual-texture rendering in a single inner loop — one for the surface texture, one for the environment/light map
- Author lists further possible techniques: 3D camera, environment mapping, morphing stretch-tables, Z-buffer, S-buffer, alpha-channel, mirroring rotation, fast scaling, particles, spheres, tunnels, lens flare

### What's NEW vs Our Book

**Our Ch.6 covers:** sphere rendering, texture mapping via skip tables.

**New material:**
- Combined texture + environment/Phong shading is a major technique absent from our book. This is the kind of effect that made demos like Napalm stand out.
- Stack-driven rendering (POP for texture deltas) is a technique we mention in Ch.7 (rotozoomer) but don't apply to 3D polygon rendering.
- Saturation table for color clamping is a useful general-purpose trick.
- Memory layout for multiple 64x64 textures in one 128K page.
- The 38-line output buffer sized for 2-frame C2P is a practical design decision.

### Notable Code Patterns

- `POP HL` / `ADD HL,BC` / `LD A,(HL)` — stack-driven texture fetch
- `ADD A,(HL)` — combining two texture values
- `LD E,A` / `LD A,(DE)` — saturation lookup (D = page of clamp table)
- Dual `EXX` to switch between texture and light coordinate spaces

---

## 5. bd05fc2p.txt — Fast C2P Procedure

**Author:** Monster/Sage Group
**Source:** Born Dead #05, Samara, 07.01.1999

### Key Techniques

**Ultra-fast chunky-to-planar conversion using self-decoding jump table.**

The approach encodes each chunk's brightness directly into a jump address:
- Buffer byte format: `11xxxx00` where `xxxx` = brightness (0-15), `11` = 2 high bits for jump table page
- A 16K jump table at #C0C0 contains `JP ADR_#XX` entries
- Each `ADR_#XX` handler writes 6 lines of a chunk pair (immediate value in the code itself):

```z80
ADR_#XX: LD   H,D         ; set screen high byte
         LD   (HL),#xx    ; line 0 (immediate = dither pattern)
         INC  H
         LD   (HL),#xx    ; line 1
         INC  H
         LD   (HL),#xx    ; lines 2-5...
         INC  H
         LD   (HL),#xx
         INC  H
         LD   (HL),#xx
         INC L
         RET NZ           ; return to dispatcher
         ; segment boundary handling:
         LD  A,D
         ADD A,E
         LD  D,A
         RET
```

**Driver routine:**
```z80
C2P_DRW  LD  (C2P_RET+1),SP
         LD  SP,C2P_BUF       ; point stack at chunky buffer
         LD  HL,#4000          ; screen start
         LD  D,H
         LD  E,8
         RET                   ; "calls" first handler via RET
C2P_RET  LD  SP,0              ; restore stack
         RET
```

**Performance:** 109 T-states per chunk pair, **83,712 T-states for the entire screen** (~1.17 frames on Pentagon).

### Innovations

- Self-decoding via encoded buffer bytes: the buffer byte IS the jump address (high bits = page, low bits = chunk pair index)
- `RET` used as indirect jump (SP = buffer, POP gets next handler address)
- Chunk pairs processed together — one byte drives 6x2 pixel output
- Screen segment boundary crossing handled inline
- Referenced: >25 fps full-screen bump mapping in Born Dead #05 intro

### What's NEW vs Our Book

**Our Ch.7 covers:** rotozoomer, chunky pixel output, SMC inner loop.

**New material:**
- This is a completely different C2P architecture from what we describe. Our approach uses a linear conversion; this uses encoded jump tables.
- 83,712 T-states for full screen C2P is extremely fast — worth benchmarking against our approach.
- The "buffer byte encodes jump address" trick is a novel form of self-modifying code.
- Uses 16K of RAM for the jump table — classic speed/memory tradeoff.
- The `RET` as indirect call dispatcher pattern is something we should mention in Ch.7.

### Notable Code Patterns

- `LD SP,buffer` / `RET` — stack as data stream dispatcher
- Buffer byte format `11xxxx00` encoding brightness + jump page
- 6-line chunk rendering with `INC H` for screen line advance
- `RET NZ` for fast column advance, falling through to segment boundary code

---

## 6. dod2chnk.txt — Chunks Output

**Author:** Devil/eTc/Scene'99
**Source:** Demo or Die #2, 1999

### Key Techniques

**Complete chunk (4x4 pixel) output system with dither table generation.**

Two modes described:

**Mode 1: Packed format (2 chunks per byte, e.g., animation/plasma):**
```z80
PUTLIN:
  LD C,(HL)      ; get packed chunk code (hi nibble + lo nibble)
  INC HL
  LD A,(BC)      ; fetch dither line 0 from table
  LD (DE),A      ; write to screen
  INC D          ; next screen line
  INC B          ; next table line
  LD A,(BC):LD (DE),A:INC D,B  ; lines 1,2,3...
  LD A,(BC):LD (DE),A:INC D,B
  LD A,(BC):LD (DE),A:INC E    ; next column after 4th line
  ; second chunk: go back UP
  LD C,(HL):INC HL
  LD A,(BC):LD (DE),A:DEC D,B  ; descend
  ...
```

**Mode 2: Unpacked format (1 chunk per byte, general effects):**
```z80
PUT_LIN:
  LD C,(HL)      ; chunk 1 code
  LD A,(BC)      ; shift right 4 bits via table
  INC L
  LD C,(HL)      ; chunk 2 code
  OR C           ; combine into packed byte
  INC L
  EXX
  LD E,A         ; use as dither table index
  LD A,(DE):LD (HL),A:INC H:INC D  ; 4 lines
  LD A,(DE):LD (HL),A:INC H:INC D
  LD A,(DE):LD (HL),A:INC H:INC D
  LD A,(DE):LD (HL),A:INC L
  EXX
```

**Dither table generation (INIT_CH):** Builds all 256 combinations of chunk pairs (16x16) from 16 base dither patterns. The patterns use ordered dithering:
```
Level 0:  0000/0000/0000/0000
Level 8:  AA55/AA55 (checkerboard)
Level 15: FFFF/FFFF/FFFF/FFFF
```

Table: 1024 bytes at #F000 (4 lines x 256 combinations).

**Self-replicating code:** INITCH multiplies the PUTLIN block LEN times via LDIR to create a full scanline renderer, then appends RET. This is code generation at init time.

**Screen address table:** Pre-calculates 48 row addresses (every 4 lines) for fast Y-to-address mapping, including the ZX Spectrum's non-linear screen layout crossing.

### Innovations

- Two chunks packed into one byte index the dither table directly — one lookup per chunk pair
- Zigzag rendering (down for odd chunks, up for even) avoids screen address recalculation
- Self-replicating PUTLIN code eliminates loop overhead entirely
- DOW_DE4 routine handles the ZX screen's 3-segment layout for 4-line jumps

### What's NEW vs Our Book

**Our Ch.7 covers:** rotozoomer, chunky pixel output, SMC inner loop.

**New material:**
- The dither pattern table with all 256 pair combinations is a complete, ready-to-use system. Our Ch.7 discusses chunky pixels but doesn't provide a full dither table.
- Zigzag rendering pattern (down-up alternation) to minimize address calculations.
- Self-replicating code via LDIR for unrolled scanline output is a useful pattern.
- The packed 2-chunks-per-byte format and the shift-table workaround for unpacked data are practical implementation details.
- References to Refresh, Forever, 5th Element, Goa demos as chunky pixel users.

### Notable Code Patterns

- Dither data: 16 ordered-dithering patterns for 4x4 chunks (complete set provided)
- `LD C,(HL)` / `LD A,(BC)` — combined table index where B = table page, C = chunk code
- Zigzag: `INC D` x3 down, then `DEC D` x3 up for alternating columns
- LDIR-based code self-replication for unrolled loop generation

---

## 7. dod1hdfc.txt — Hidden Surface Algorithms

**Author:** Wolf/Etc group/Scene
**Source:** Demo Or Die #1, 1999

### Key Techniques

Three methods for hidden surface removal:

**Method 1: Back-face culling (convex objects only)**

Uses the 2D cross-product (determinant) of the first three projected vertices of each face:

```
D = (x3-x1)*(y2-y1) - (x2-x1)*(y3-y1)
```

If D < 0, the face is visible. Requires consistent vertex winding order (clockwise or counter-clockwise).

Data structure: `face[]` array of vertex indices, `points[]` array of 3D coordinates. Winding order must ensure the face is always "to the left" when traversing edges.

**Method 2: Painter's algorithm (Z-sorting)**

Sort faces by average Z: `Zavg = (Z1+Z2+Z3)/3`. Draw back-to-front. Simple but incorrect for intersecting or overlapping faces. Must draw ALL faces (no culling).

**Method 3: Z-buffer**

Per-pixel depth testing. Most correct but slowest. Requires interpolating Z coordinate along with texture/color. Two buffers: Z-buffer + color buffer.

### What's NEW vs Our Book

**Our Ch.5 covers:** rotation matrices, sine tables, perspective projection, wireframe cube.

**New material:**
- Back-face culling via cross-product is not explicitly derived in our Ch.5 (wireframe only — no faces). This should be added if we extend to solid objects.
- The data structure format (face[] + points[] arrays) is standard but not described in our book.
- Vertex winding order convention is important practical knowledge.
- Painter's algorithm and Z-buffer are mentioned as context for the tradeoff spectrum (speed vs correctness).
- The article is introductory but provides the correct formula and winding-order rules.

### Notable Code Patterns

- Cross-product determinant for back-face test: `D = (x3-x1)*(y2-y1) - (x2-x1)*(y3-y1)`
- Data structures: indexed face list + coordinate array (standard 3D object format)

---

## 8. zg1scfrm.txt — Screen Output Within One Interrupt

**Author:** Alone Coder
**Source:** ZX-Guide #1, Ryazan, 28.11.1998

### Key Techniques

**LD-PUSH method for full-screen output in one frame (71,680 T-states on Pentagon).**

The article debunks the claim from ZX-Power #1 that outputting 6144 bytes of screen data in one interrupt is impossible. The key insight: the previously-analyzed POP-PUSH method requires frequent SP modifications, but LD-PUSH only modifies SP once per line (not per byte pair).

**Basic LD-PUSH pattern:**
```z80
LD SP,...         ; set SP to end of screen line
LD DE,xx          ; load 2 bytes of data
PUSH DE           ; write 2 bytes
LD DE,yy          ; next 2 bytes
PUSH DE           ; write them
; repeat 16 times per line, 192 lines
JP PROG           ; loop
```

**The DOWN_SP optimization:**

Initial version (35 T): table lookup for next screen line address:
```z80
SET 7,H
LD E,(HL)
INC L
LD D,(HL)
EX DE,HL
LD SP,HL
```

Improved version (30 T): use POP to read from the same table:
```z80
SET 7,H
LD SP,HL
POP HL
LD SP,HL
```

Final version (28+3/8 T average): exploit that screen segment boundaries occur only 1 in 8 lines:
```z80
INC H
RRCA
JR NC,$+6      ; skip segment crossing (7 of 8 times)
SET 7,H
LD SP,HL
POP HL
LD SP,HL        ; always executed
```

With JP instead of JR: exactly **28 T-states** per line transition.

**Self-modifying breakpoint technique:**

The output program is an infinite loop. To enter/exit:
1. Write `JP USE` at the current line position (breakpoint)
2. Jump into the output loop
3. When execution hits the breakpoint, it jumps to USE which restores the original code and returns

For HALT synchronization: a second counter (HL') tracks 96 lines ahead, inserting `JP (IX)` where IX points to a HALT handler:
```z80
IMER: LD SP,0
      EXX
      HALT
      LD (HL),code_rrca
      DEC L
      LD (HL),code_inc_h
      PUSH HL
      EXX
      RET
```

**Scrolling application:** The output program can scroll by modifying which LD DE,nn values are used — writing new data into the freed line at each frame.

### Innovations

- LD-PUSH is faster than POP-PUSH because SP modification happens every 16 bytes (once per line) vs every 2 bytes
- The breakpoint technique for entering/exiting an infinite output loop is creative
- RRCA-based 1-in-8 test for segment boundary avoidance
- Mentioned that Adrenalize (FUNTOP'98) actually achieved full-screen output in one interrupt (though the exact method is unknown)
- Total budget: 192 lines * (16 * (10+11) + 28) = 192 * (336+28) = 192 * 364 = **69,888 T-states** — fits in Pentagon's 71,680 T-states per frame

### What's NEW vs Our Book

**Our book (general):** does not have a dedicated discussion of LD-PUSH full-screen output.

**New material:**
- LD-PUSH as a faster alternative to POP-PUSH for full-screen updates is not covered in our book
- The breakpoint injection technique for self-modifying output loops is novel
- The 28 T/line DOWN_SP optimization sequence is elegant
- Concrete timing analysis proving 6144 bytes CAN be output in one frame
- Scrolling via live code modification is a powerful technique for text displays
- The comparison of POP-PUSH vs LD-PUSH is valuable pedagogical content

### Notable Code Patterns

- `LD SP,addr` / `LD DE,data` / `PUSH DE` — the LD-PUSH pattern
- `INC H` / `RRCA` / `JR NC` — screen line advance with 1-in-8 segment check
- `SET 7,H` / `LD SP,HL` / `POP HL` / `LD SP,HL` — 30T next-line lookup
- Breakpoint injection: writing `JP handler` into the output code stream
- `JP (IX)` as a HALT injection point

---

## Summary: Gap Analysis vs Book Content

### Already Covered (partially) in Our Book
| Article Topic | Our Coverage | Gap |
|---|---|---|
| 3D rotation | Ch.5: standard matrix rotation | Axis-table method is a distinct alternative |
| Texture mapping | Ch.6: sphere skip tables | Triangle rasterizer is more general |
| Chunky pixels | Ch.7: rotozoomer C2P | Multiple C2P architectures exist |

### Major Gaps — Should Add to Book

1. **Bump mapping** (sng1bump) — Complete technique absent from book. Major demoscene effect. The `ADD HL,BC` dual-addition trick alone is worth a sidebar.

2. **Fast C2P via jump tables** (bd05fc2p) — 83K T-states full screen. Our Ch.7 should benchmark against this.

3. **Axis-table 3D rotation** (zpw3gf3d) — Fundamentally different from matrix rotation. Could be a "Fast Track" sidebar in Ch.5. The 200 T-states/point claim is remarkable.

4. **LD-PUSH full-screen output** (zg1scfrm) — Alone Coder's technique deserves mention in screen output discussions. The breakpoint injection pattern is unique.

5. **Combined texture + Phong shading** (sng2txph) — Stack-driven dual-texture inner loop. Relevant to Ch.6 as an advanced technique.

6. **Dither table system** (dod2chnk) — Complete 4x4 ordered-dithering set with all 256 combinations. Practical resource for Ch.7.

7. **Back-face culling** (dod1hdfc) — Cross-product test. Essential if Ch.5 extends to solid objects.

### Code Patterns Worth Reimplementing

| Pattern | Source | T-states | Notes |
|---|---|---|---|
| Bump mapping inner loop | sng1bump | 37-43 T/byte | POP+ADD HL,BC+LDD |
| C2P via jump table | bd05fc2p | 109 T/pair | Self-decoding buffer bytes |
| Axis table generation | zpw3gf3d | ~200 T/point | DUP 64 interpolation |
| Texture map inner loop | sng2txmp | ~50 T/texel | ADD HL,DE fixed-point 8.8 |
| Texture+Phong scanline | sng2txph | ~60 T/pixel | Dual POP+ADD, stack-driven |
| LD-PUSH screen output | zg1scfrm | 28 T/line xfer | Full screen in one frame |
| Chunk output zigzag | dod2chnk | ~30 T/chunk | Packed pair, dither table |
