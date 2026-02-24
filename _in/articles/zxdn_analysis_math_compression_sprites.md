# ZXDN Article Analysis: Math, Compression, Sprites, Sorting, Demo Workflow

Source: ZXDN (ZX Demo News) article archive, `/coding/` section.
Analyzed: 8 articles from 6 different ZX Spectrum e-zines (1997-2007).

---

## 1. ig10rndg.txt — PRNG Generators (LFSR + Mitchell-Moore)

**Author:** Lord Vader (lvd^mHm)
**Source:** Info Guide #10, Ryazan, 05.2007

### Key techniques

**LFSR (Linear Feedback Shift Register):**
- Hardware-style PRNG identical to AY-3-8910 noise generator
- Explains XOR tap positions for maximum-length sequences (period = 2^N - 1)
- Provides complete tap tables for N=3..39 (single tap) and N=8,16,24,32 (triple tap)
- Z80 implementation of 15-bit LFSR: ~30 bytes, outputs 1 random BIT per call via carry flag
- Notes fundamental limitation: LFSR outputs single random bits, not bytes

**Mitchell-Moore generator (additive lagged Fibonacci):**
- Formula: X[n] = (X[n-24] + X[n-55]) mod m
- Period for bytes (m=256): ~2^62
- Z80 implementation uses 256-byte circular table
- Returns random byte in A, plus two more decorrelated values in B and C
- Requires initialization with non-zero table data

### Cycle counts
- LFSR15: not counted explicitly, but very fast (~40-50 T per bit)
- Mitchell-Moore: not counted, but short code path (~60-80 T estimated)

### What's NEW vs our Ch.4
- **Our book covers:** Patrik Rak CMWC, Ion Random, shift-and-add multiply
- **New here:** LFSR theory with tap tables (connects to AY noise generator -- good for Ch.10/11 sound chapters). Mitchell-Moore additive lagged Fibonacci is a distinct PRNG family not in our book.
- **Worth noting:** The LFSR tap table (N=3..39, plus N=8,16,24,32) is a useful reference. The connection to AY noise is pedagogically valuable.

### Notable algorithms worth reimplementing
- Mitchell-Moore generator with 256-byte table -- simple, good quality, period ~2^62. A practical alternative to CMWC for when you need fast random bytes with moderate state.

---

## 2. dv05math.txt — Fast Multiply, Square Root

**Author:** Card!nal/PGC/BD
**Source:** Deja Vu #05, Kemerovo, 01.07.1998

### Key techniques

**Square-table multiplication (a*b via difference of squares):**
- Uses (a+b)^2/2 - (a-b)^2/2 = a*b
- 512-byte lookup table of squares (0..255)
- Table generation code provided
- Handles unsigned 8x8->16 bit multiply
- Algorithm sourced from game BATTLE COMMAND 128 and Spectrum Expert #1

**Newton's method square root:**
- Modified Newton iteration for integer sqrt(HL) -> HL
- Uses 15-byte table of "average roots" for initial approximation
- Formula: (sqrt(2^n) + sqrt(2^(n+1))) / 2
- Only 1 division for values 2..16383, 2 divisions for 16384..65535
- Full division routine included (16-bit DIV with rounding)

### Cycle counts
- **Shift-and-add multiply (loop):** min 310, max 358 T-states
- **Shift-and-add multiply (unrolled):** min 206, max 254 T-states
- **Square-table multiply:** min 141, max 207 T-states (1.5-2.5x faster)
- **Square root:** ~1500-2500 T-states (vs ~5000-10000 for naive Newton)

### What's NEW vs our Ch.4
- **Our book covers:** shift-and-add multiply, fixed-point arithmetic
- **New here:** The square-table multiply implementation with full signed/unsigned handling and cycle counts. Newton sqrt with table-of-averages approximation.
- **Key insight:** The square-table multiply at 141-207 T is significantly faster than our shift-and-add (206-254 T unrolled). This is the classic demoscene fast multiply.

### Notable algorithms worth reimplementing
- **Square-table 8x8 multiply** -- the canonical fast multiply for ZX Spectrum, deserves a place in Ch.4. 512 bytes of tables, 141-207 T. Referenced by SE#1.
- **Newton sqrt with average-root table** -- compact and practical.

---

## 3. zf7fcalc.txt — Fast Calculations in Assembler

**Author:** GreenFort
**Source:** ZX Format #7, Saint Petersburg, 06.12.1997

### Key techniques

**8-bit division (C/B -> L remainder A):**
- Binary long division using SLI (undocumented) for bit shifting
- Counter embedded in result register (clever trick: L starts at #01, shifts out as counter)
- Can chain two calls for 8.8 fixed-point division result (H.L)
- Precision: +/-(1/256), i.e., ~2 decimal places

**24-bit division (A,H,L / B,D,E -> A,H,L):**
- Full 3-byte division using EXX for shadow register workspace
- Handles overflow detection
- Result usable directly in 3-byte add/subtract chains

**8-bit multiplication (B*C -> HL):**
- Standard shift-and-add, 8-iteration loop with DJNZ
- Can be unrolled for speed

**24-bit multiplication (A,H,L * B,D,E -> A,H,L):**
- 24-iteration shift-and-add using EXX
- Overflow flag in memory variable
- Result chains with 3-byte arithmetic

### Cycle counts
- Not explicitly counted, but all routines are compact loop-based implementations.

### What's NEW vs our Ch.4
- **Our book covers:** 8x8 multiply, fixed-point
- **New here:** 24-bit (3-byte) multiply and division routines. The chained 8.8 fixed-point division technique (two CALL DIVIS for integer.fraction result). The SLI-based bit counter trick.
- **Key insight:** The 3-byte arithmetic is essential for 3D calculations where 16-bit precision is insufficient. The article explicitly targets vector graphics use cases.

### Notable algorithms worth reimplementing
- **Chained 8.8 fixed-point division** -- elegant two-call pattern for fractional results. Good for Ch.4.
- **24-bit multiply/divide** -- useful reference for Ch.6 (3D math).

---

## 4. ig7hpack.txt — LZ Compression Practical Principles

**Author:** Alone Coder (A. Coder)
**Source:** Info Guide #7, Ryazan, 06.2005

### Key techniques

This is a comprehensive ~8K-word article on practical LZ packer implementation for ZX Spectrum. Major topics:

**Terminology and foundations:**
- LZ (Lempel-Ziv): find repeated substrings, encode as (displacement, length) references
- Huffman coding for encoding reference parameters
- Window/dictionary size determines maximum displacement
- Canonical Huffman tree construction and storage

**Hash-based string matching:**
- Key tables: 2-3 byte hashes mapping to last-seen address
- Hash chains: each window position stores pointer to previous position with same hash
- Memory formula: window*3 + keys (e.g., 32K window + 12-bit keys = 104K)
- 11-bit vs 13-bit keys: ~5% speed difference
- Discussion of 128K memory constraints limiting window to ~32-40K

**Huffman tree construction for packer:**
- Build frequency statistics during LZ pass
- Store entire LZ stream in uncompressed form (separate buffer)
- Construct optimal Huffman tree from statistics
- Truncate tree depth to max 15 levels (RAR/RIP compatible)
- Canonical code assignment from tree depths

**Packing strategies (3 levels):**
1. **Greedy (Fast):** Take best match found scanning backward. Used in most ZX packers.
2. **Lazy evaluation (Best):** After finding match, check if skipping one byte gives better match at next position. 1.5-2x slower, noticeable compression improvement. Used in Zlib, ZXRar.
3. **Optimal LZH:** Described in IG#6, not yet implemented on ZX.

**Practical ZX implementation details:**
- TR-DOS file handling for archives
- Sector-based I/O buffering
- Swap mechanism for decompression (source from ZXUnRar)
- Handling files >255 sectors (satellite files)

**Notable technical details:**
- Problem with hash search on long runs of repeated bytes (AAAAAA...) -- slower than CPIR/CPDR brute force
- Hrumer's optimization proposal for Laser Compact: special handling of AA... and ABAB... sequences
- Lazy evaluation boundary tuning: detailed table of displacement ranges and thresholds for when +1 length improvement is worthwhile

### What's NEW vs our Ch.14
- **Our book covers:** ZX0, Exomizer, LZ4, decision tree for choosing compressor (user perspective)
- **New here:** Complete packer-side implementation details. Hash table design, Huffman tree construction, strategy comparison (greedy vs lazy eval vs optimal). This is the *implementer's* perspective, not the *user's* perspective.
- **Key insight:** This article is the most detailed ZX-specific LZ packing tutorial available. It bridges the gap between "use ZX0" and "understand how compression works internally."

### Notable algorithms worth reimplementing
- The article is more of a design guide than code listings. The hash chain search structure and lazy evaluation strategy are the key takeaways. Potentially useful for a sidebar in Ch.14 on "how your compressor works internally."

---

## 5. dv06huff.txt — Huffman Compression

**Author:** Diver/CRG, Elena Gladkova/CRG
**Source:** Deja Vu #06, Kemerovo, 01.10.1998

### Key techniques

**Comprehensive Huffman coding tutorial:**
- Establishes key formula: COMPRESSION = MODELING + CODING
- Formal graph theory definitions (tree, binary tree, H-tree)
- History: Huffman's 1952 paper

**Classic Huffman algorithm:**
1. Create leaf nodes for all symbols with frequency weights
2. Repeatedly merge two lightest nodes into parent
3. Assign 0/1 to branches
4. Read codes from leaf to root (reversed)
- Worked example with 5-symbol alphabet (A=15, B=7, C=6, D=6, E=5)
- Produces codes: A=0, B=100, C=101, D=110, E=111

**Adaptive Huffman coding (main focus):**
- No need to transmit frequency table
- Single-pass encoding and decoding
- Ordered tree property: nodes numbered in weight order, siblings adjacent
- Tree update algorithm:
  1. Increment leaf weight
  2. If ordering violated, swap node with last node of same weight
  3. Propagate up to root
- ESCAPE code for new symbols (start with empty tree)
- EOF marker in initial tree

**Overflow and scaling:**
- Maximum code length related to Fibonacci sequence: Fib(18) = 4181 can cause overflow with 16-bit weights
- Weight scaling (divide by 2) when maximum reached
- Scaling actually IMPROVES compression (recent symbols weighted more)
- Rebuilt tree after scaling may differ from original

**ASCII art tree diagrams:** Extensive worked examples showing tree evolution through multiple symbol insertions and node swaps.

### What's NEW vs our Ch.14
- **Our book covers:** Compression from the user side (ZX0, Exomizer, etc.)
- **New here:** Complete adaptive Huffman implementation theory. The ordered-tree property and its maintenance algorithm. The observation that periodic scaling improves compression (recency weighting).
- **Key insight:** This pairs with ig7hpack.txt to give complete theoretical and practical coverage of ZX compression internals. The Fibonacci connection to max code length is elegant.

### Notable algorithms worth reimplementing
- Adaptive Huffman is rarely implemented standalone on ZX (it's usually part of LZ+Huffman). The article is educational rather than directly practical. Good reference material for a Ch.14 sidebar.

---

## 6. zg45spro.txt — Fast Sprite Output (Alone Coder)

**Author:** Alone Coder
**Source:** ZX-Guide #4.5, Ryazan, 08.2002

### Key techniques

**Context:** Sprite rendering for RTS (real-time strategy) games. Requirements: 20+ characters, 24+ sprites each, pixel-accurate movement, masked sprites on linear-addressed framebuffer.

**Three approaches to pixel-shifted sprite output:**
1. Runtime bit shifts (slow)
2. Pre-shifted byte lookup table (8*256 or 8*2*256 bytes -- memory heavy)
3. **Table of subroutines** (chosen approach) -- 8 small code fragments, one per pixel shift

**Implementation details:**
- SP-based sprite reading (POP for 4 bytes: 2 mask + 2 image per line)
- 8 separate shift routines (RL0..RL7) for each bit offset
- Uses AND mask / XOR image pattern for transparent overlay
- Parity flag (JP PE) trick to dispatch to correct shift routine
- Linear framebuffer addressing (assumes shadow screen with linear layout)
- Sprites stored upside-down (position by feet -- variable height characters)
- Vertical clipping by arithmetic on line count
- Deliberately avoids undocumented SLI instruction

**Interrupt-driven rendering architecture:**
- Key innovation: sprite output runs IN the interrupt handler
- Sprites split into groups that fit within one frame (220 lines budget, more for Turbo)
- Height-based budget checking after each sprite
- Remaining frame time used for AI and sprite list generation

**Parallel programming problem:**
- Three proposed solutions for render/logic synchronization:
  1. Double-buffered sprite lists (14 bytes/character, frame lag)
  2. Single list with generation-before-rendering (7 bytes/character, implemented)
  3. Ring buffer list (256 bytes total, not implemented)

**Full Z80 source code** for all 8 shift routines included, plus discussion of wider sprites (vertical strip slicing).

### What's NEW vs our Ch.16
- **Our book covers:** OR/AND sprites, compiled sprites, masking, pre-shifted sprites
- **New here:**
  - The **subroutine-table approach** (8 code variants instead of pre-shifted data) -- a memory-efficient middle ground between runtime shifting and full pre-shift
  - **SP-based sprite reading** for maximum throughput (POP BC / POP HL for 4 bytes at once)
  - **Interrupt-driven sprite rendering** architecture with frame-budget sprite batching
  - The **parallel rendering/AI** problem and three synchronization solutions
  - Parity flag dispatch trick for shift selection

### Notable algorithms worth reimplementing
- **The 8-variant shift+mask sprite routine** -- excellent practical code, complete and ready to adapt. The SP-based data reading pattern is a classic demoscene technique.
- **Frame-budget sprite batching** -- the interrupt-driven rendering with height-based budget checking is an elegant game engine architecture pattern worth discussing in Ch.16 or Ch.20.

---

## 7. sng2dngl.txt — DAINGY Demo Post-Mortem

**Author:** Cryss/RZL
**Source:** Scenergy #2, Novgorod, 2000

### Key techniques

**Demo:** DAINGY intro, 3rd place at CC'999 demoparty.

**Memory layout:**
- `line` (calculated) -- line rotation procedure, built at runtime
- `chunks` at #7600 -- 8x4 pixel textures
- `sin` at #7900 -- sinusoid table
- `#8000` -- image data (256x4096, 1 byte = 1 pixel)
- `tenbuf` at #FA00 -- frame buffer

**Runtime code generation:**
- Rotation procedure for one image line is ASSEMBLED AT RUNTIME by LDIR-copying a template 32 times + appending RET
- Saves code space, adapts to memory layout

**Compact sine approximation:**
- Self-described as "shortest method known to me"
- Approximates quarter-sine by accumulating variable with decreasing step constants
- Generates half-period with amplitude #01..#EF in minimal code
- The derivative of sin changes from max to min over 0..PI/2; approximated by repeated addition with decreasing constants

**Texture rotation (the main effect):**
- Rotates text inscription over texture
- BC and BC' hold X/Y increments (dx, dy from sin/cos)
- Per-line: apply rotation, write to tenbuf
- Perspective distortion by modifying one increment each line (DEC BC twice)

**Pseudo-3D lateral faces:**
- Column-scan of tenbuf: find first non-zero byte, fill subsequent bytes with decreasing values
- Creates illusion of 3D depth on rotated text
- Top-edge gradient to hide clipping artifacts

**Chunk-based rendering:**
- 4x4 pixel chunks stored in 32 bytes (4 bits per pixel, packed)
- Runtime unpacking via RLD instruction
- Brightness control by shifting chunk data (fade in/out)

**Optimizations and trade-offs:**
- HALT-synchronized output
- Double-buffered pages (#55/#57 screen switching)
- 256 frames total (register B counter)
- Code reuse: single LDIR fill routine for zeroing memory AND setting attributes (by careful address/size alignment)
- Data format: string characters stored as (letter-#20)*4 for compact lookup

### What's NEW vs our Ch.20
- **Our book covers:** Demo workflow from idea to compo release
- **New here:** Complete post-mortem of a real compo intro with full source walkthrough. The runtime code generation technique (LDIR-copying a rotation template). The compact sine approximation. The pseudo-3D column-fill technique.
- **Key insight:** This is exactly the kind of "how a real demo was built" material that Ch.20 needs. DAINGY placed 3rd at CC'999, making it a documented compo production with source.

### Notable algorithms worth reimplementing
- **Compact sine approximation** -- the accumulate-with-decreasing-step method is remarkably short. Worth a sidebar.
- **Column-scan pseudo-3D** -- simple technique for giving depth to rotated text, applicable to many effects.

---

## 8. dod2sort.txt — Sorting Algorithms on ZX Spectrum

**Author:** Kenotron
**Source:** Demo or Die #2, 1999

### Key techniques

**Four sorting algorithms compared:**

**1. Bubble Sort:**
- Standard adjacent-swap with early termination (no-swap flag)
- Written in STORM assembler (by X-Trade)
- Performance: **~3 interrupts** (~210,000 T) for 60 elements
- Verdict: "quite slow (maybe the slowest)"

**2. Selection Sort (Simple Exchange):**
- Find minimum in remaining array, place at front
- Performance: **~1 interrupt** (~85,000 T) for 60 elements
- "A bit (much) faster" than bubble sort

**3. Von Neumann Merge Sort:**
- Theoretical description only, no ZX implementation
- Author notes difficulty of pointer-based algorithms on Z80 (no pointer indirection)
- "If you struggle long enough, something will come out :)"

**4. Radix/Byte Sort (BYTESORT+):**
- Key insight: treat byte values as indices into 256 counters
- Phase 1 (sort+pack): scan array, increment counter[value] for each element
- Phase 2 (unpack): iterate 256 counters, emit value N times for counter[N]
- Uses 512 bytes for 16-bit counters (handles counts > 255)
- Unrolled unpack loop via computed jump (PUSH HL/RET trick)
- **Performance: ~30,000 T** (~1/2 interrupt) for 60 elements
  - Sort phase: only 14% of total time
  - Unpack phase: 86% (but grows slower than sort phase with array size)
  - Sort time is LINEAR in array size (O(n)), unpack is O(256) constant overhead

### Cycle counts (60-element array)
| Method | T-states | Interrupts |
|--------|----------|------------|
| Bubble sort | ~210,000 | ~3 |
| Selection sort | ~85,000 | ~1.2 |
| BYTESORT+ | ~30,000 | ~0.4 |

### What's NEW vs our book
- **Our book:** Does not have a dedicated sorting chapter. Sorting is tangentially relevant to Ch.6 (3D face ordering), Ch.16 (sprite priority).
- **New here:** Practical Z80 implementations of bubble, selection, and counting/radix sort with real benchmarks. The BYTESORT+ is essentially a counting sort -- the fastest possible for 8-bit keys and the natural choice for Z80 demoscene work (depth sorting, painter's algorithm).
- **Key insight:** BYTESORT+ (counting sort) at 30,000 T for 60 elements is fast enough for real-time face sorting in 3D engines. The 512-byte counter array fits easily in memory.

### Notable algorithms worth reimplementing
- **BYTESORT+ (counting sort)** -- extremely practical for depth sorting in 3D demos. O(n) sort + O(256) unpack. The unrolled unpack via computed jump is a nice optimization. Directly applicable to Ch.6 (painter's algorithm).

---

## Summary: Cross-reference with Book Chapters

### Ch.4 (Math) -- Gaps to fill:
1. **Square-table multiply** (dv05math): 141-207 T vs 206-254 T for shift-and-add. The canonical fast multiply. Our book should cover this as the primary fast multiply technique.
2. **LFSR generators** (ig10rndg): Connection to AY noise generator. Tap tables as reference.
3. **Mitchell-Moore PRNG** (ig10rndg): Alternative to CMWC for random byte generation.
4. **24-bit arithmetic** (zf7fcalc): Essential for 3D math when 16-bit is insufficient.
5. **Newton sqrt** (dv05math): Practical integer square root with table approximation.

### Ch.6 (3D) -- Supporting material:
1. **BYTESORT+ counting sort** (dod2sort): O(n) face sorting for painter's algorithm.
2. **24-bit multiply/divide** (zf7fcalc): For 3D coordinate transformations.

### Ch.14 (Compression) -- Gaps to fill:
1. **LZ packer internals** (ig7hpack): Hash tables, key tables, lazy evaluation strategy. Our chapter covers compressors as tools; this adds "how they work inside."
2. **Adaptive Huffman** (dv06huff): Complete theory with ordered-tree maintenance. Educational complement.

### Ch.16 (Sprites) -- Gaps to fill:
1. **Subroutine-table shifted sprites** (zg45spro): Memory-efficient alternative to pre-shifted data. 8 code variants instead of 8x data copies.
2. **SP-based sprite reading** (zg45spro): POP for bulk data loading during sprite output.
3. **Frame-budget interrupt-driven rendering** (zg45spro): Architectural pattern for game engines.

### Ch.20 (Demo Workflow) -- Supporting material:
1. **DAINGY post-mortem** (sng2dngl): Complete source walkthrough of CC'999 compo intro. Runtime code generation, compact sine, pseudo-3D column fill.

### Algorithms most worth reimplementing (priority order):
1. **Square-table 8x8 multiply** -- core technique missing from Ch.4
2. **BYTESORT+ counting sort** -- directly useful for 3D face sorting
3. **SP-based shifted sprite routine** -- Alone Coder's 8-variant approach
4. **Mitchell-Moore PRNG** -- alternative PRNG for Ch.4
5. **Newton sqrt with table** -- practical square root
6. **Compact sine approximation** -- from DAINGY, smallest known Z80 sine
