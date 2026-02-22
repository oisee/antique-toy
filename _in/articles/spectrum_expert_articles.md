# Spectrum Expert — Fetched Article Summaries

> Fetched from zxart.ee, 2026-02-22. AI-extracted summaries.

---

## Spectrum Expert #01 (X-Trade, 1997)

**Download:** SP_EXP1.ZIP (TRD) or SP_EXP1O.zip (UDI) from ZXArt
**Platform:** Pentagon 128 | **Rating:** 4.08/5

### Full Article List

1. **Shell** — Interface navigation guide
2. **Introduction** — Creation challenges, call for contributions
3. **From the Editorial** — Critique of ZX magazine quality
4. **Enlight 1997** — Party report (chaotic, cancelled day 2, alcohol problems)
5. **Interview** — Hardware innovations, SKORPION computer
6. **Games Review** — 1990s ZX Spectrum games
7. **★★★ Programming (3D Graphics)** — Fast 3D implementation by Dark & STS
8. **★★★ Programming Algorithms** — Multiplication, division, sine, Bresenham by Dark
9. **SOFT: STORM Assembler** — Storm T.A. features and syntax
10. **SOFT: PRO-TRACKER 3.01** — Tracker improvements
11. **SOFT: RIFF TRACKER v2.9** — Music editor review
12. **★★ Programming Sound (GS)** — GS sound system for games by Mikhail Blum
13. **Hardware: GMX** — Graphic Memory eXpander details
14. **Hardware: Buffered Bus** — Enhancement techniques
15. **Humor** (2 articles) — Jokes and game reviews
16. **Advertisement** — Product listings

---

### Article: Programming Algorithms (Dark, SE#01)

**Six essential algorithms for Z80 assembly:**

**1. Multiplication**
- Method 1 (shift-and-add from LSB): MULU112 = 8×8→16, 196–204 T-states. MULU224 = 16×16→32, 730–826 T-states.
- Method 2 (square table lookup): A*B = ((A+B)²-(A-B)²)/4. ~61 T-states but with accuracy trade-off. "Choose: speed or accuracy."

**2. Division**
- Shift-and-subtract (restoring division): DIVU111 = 8/8, 236–244 T-states. DIVU222 = 16/16, 938–1034 T-states.
- Logarithmic division: Log(A/B) = Log(A) - Log(B) with 256-byte log/antilog tables.

**3. Trigonometric Approximations**
- Cosine table via parabolic approximation (Y=X² mimics sine half-period). Signed table -128 to 127.

**4. Logarithm and Exponential Tables**
- Y=Log₂(X) and Y=(2^X)-1 lookup tables. Generation via derivatives. Accuracy within 1/128 error.
- Dark's "method of guessing" the 0.4606 correction coefficient.

**5. Bresenham's Line Drawing**
- Classic → Xopha modification → Dark's matrix method (8×8 pixel grids with SET x,(HL)).
- Setup: ~250 cycles. Drawing: ~80 cycles/pixel → optimised to ~48 min.
- Key insight: "87.5% of checks are wasted" in conditional approaches.
- 3KB memory for pre-unrolled octant loops.

**Notes:** Storm T.A. assembler syntax. Cycle counts for Pentagon (different from wait-state machines like Scorpion).

---

### Article: Programming — Fast 3D Graphics (Dark & STS, SE#01)

- 3D object definition: vertices in object space (x,y,z), edge connections (vertex pairs)
- Example: pyramid with stored vertices and edges
- **Rotation**: sequential rotation around Z, Y, X axes
  - X' = x*cos(AZ) + y*sin(AZ), etc.
  - ROTATE procedure accepting angle parameters
- **Projection**:
  - Parallel projection (ignoring Z depth)
  - Perspective: Xr = ((X''+Xcnt)*Scale/(Z+Zcnt)) + Xoffset
- Real-time computation without massive lookup tables
- Z80 assembly examples in Storm T.A. syntax
- Uses multiplication and trig routines from companion "Programming Algorithms" article

---

### Article: GS Sound System (Mikhail Blum, SE#01)

Comprehensive guide to programming the GS (General Sound) system for ZX Spectrum games.

**Architecture:**
- Port 179 (GSDAT): data transmission
- Port 187 (GSCOM): command control
- Memory: 114,688 bytes for effects + MOD files on standard 112K systems

**Key commands:**
- #30 load module, #31 start, #32 stop
- #38 load sample, #39 play current sample
- #40 set note (36-71), #41 set softness (0-64), #45 set priority (0-255)
- #80-#83 play sample in channels 0-3
- #3A stop effect in channel

**Constraints:**
- Only ONE .MOD file + 255 effects, or just MOD, or just effects
- 4-channel only (8-channel truncated)
- No samples with loops shorter than 1KB
- Must disable interrupts during GS communication

**Example game:** TARGET RENEGADE with 24 distinct sound effects.

---

## Spectrum Expert #02 (X-Trade, 1998)

**Download:** SP_EXP2.ZIP (TRD) or SP_EXP2O.zip (UDI) from ZXArt
**Platform:** Pentagon 128 | **Rating:** 4.14/5

### Full Article List

1. Help — Safety instructions
2. From the Editors — Feedback on second issue
3. News — Community updates
4. **Hardware: ZX-Bus** — Creating ZX-Bus for modifications
5. **Hardware of the ZX Spectrum** — Soviet-compatible machines
6. **Opinion on Sprinter** — Critical review
7. **Music** — Computer-generated music limitations
8. Mail — Reader correspondence
9. Toys (2 sections) — Game reviews (Anarchy, Captain Planet, Little Computer People)
10. **★★★ Programming: 3D Graphics** — Midpoint method, polygon filling by Dark & STS
11. **★★ Software: Pascal Compiler** — HiSoft Pascal HP4D review
12. **★★ Software: C Compiler** — HiSoft C review
13. Fomin (2 sections) — Humor
14. Advertisements (4 sections)

---

### Article: 3D Graphics — Midpoint Method (Dark & STS, SE#02)

**The core problem:** Rotating 3D objects requires 12 multiplications per vertex × N vertices.

**The Midpoint Method:**
1. Calculate 4 cube vertices normally
2. Mirror remaining 4 vertices relative to cube center
3. Derive complex vertices via averaging: v8 = (v4+v5)/2, v9 = (v3+v7)/2, etc.

**Virtual Processor:**
- Single register, 64×24-bit word RAM
- Four instructions: Load, Store, Average, End
- 8-bit format: 2-bit opcode + 6-bit point number
- "Programs" for vertex interpolation: DB 4,128!5,64!8

**Additional optimisations:**
- Calculate only 3 points with arithmetic completion
- Polar coordinate rotation to reduce total multiplications

**Surface visibility:**
- Backface culling via Z-component of surface normal (cross product)
- Eliminates back-facing polygons before rendering

---

### Article: HiSoft Pascal HP4D (SE#02)

- Compiler occupies 12K, editor ~2K, ~21K for programs
- Types: boolean, char, integer, real, string, word, record
- Functions: ABS, SQR, SQRT, SIN, COS, INLINE (machine code), INCH (=INKEY$)
- 68 error codes
- "Suitable for data processing and computational mathematics"

---

### Article: HiSoft C (SE#02)

- **No floating-point support** — major limitation
- "10-15× faster than BASIC" — substantial speed improvement
- 33 reserved keywords including standard C + "inline" and "cast"
- stdio.lib provides graphics at BASIC capability levels
- gam128.h for extended memory access (128K banking)
- 64+ error codes
- Conclusion: useful for speed-critical work where float isn't needed
