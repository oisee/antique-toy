# ZX Spectrum demoscene optimization: a deep technical reference

**The ZX Spectrum's Z80 processor, running at 3.5 MHz with no multiply instruction, no hardware sprites, and a deliberately scrambled screen layout, forced demoscene coders to invent some of the most creative low-level optimization techniques in computing history.** This reference covers the concrete assembly routines, exact cycle budgets, and algorithmic tricks that powered award-winning demos and games on hardware with just **69,888 T-states per frame**. Each technique below includes working Z80 assembly with T-state counts, drawn from production code, open-source demo repositories, and documented scener knowledge from both the English and Russian communities.

---

## Z80 multiplication without a MUL instruction

The Z80 has no multiply instruction, yet 3D rotations, plasma effects, and tunnel renderers all demand hundreds of multiplications per frame. Demoscene coders solved this with the algebraic identity **a×b = ((a+b)² − (a−b)²) / 4**, implemented via a 512-byte lookup table of pre-computed squares.

### Square-table multiplication (6×6 signed, ~54 T-states)

For operands where (a+b) cannot overflow a signed byte — always true for 6-bit values, which covers sine/cosine values scaled to ±63 — the fastest known Z80 multiply runs in approximately **54 T-states**, versus ~200 for shift-and-add:

```z80
; 6×6 signed multiply: B × C → BC (result)
; Requires 512-byte SqrTab aligned to 256-byte boundary
; Table contains x²/4 for x = -128..+127
Mul6x6:
    ld  h,SqrTab/256   ; 7T  — high byte of table base
    ld  d,h             ; 4T
    ld  a,b             ; 4T
    add a,c             ; 4T  — A = a+b
    ld  l,a             ; 4T
    ld  a,b             ; 4T
    sub c               ; 4T  — A = a-b
    ld  e,a             ; 4T
    ld  a,(de)          ; 7T  — low byte of (a-b)²/4
    sub (hl)            ; 7T  — subtract low byte of (a+b)²/4
    ld  c,a             ; 4T
    inc h               ; 4T
    inc d               ; 4T
    ld  a,(de)          ; 7T  — high byte of (a-b)²/4
    sbc a,(hl)          ; 7T  — subtract with borrow
    ld  b,a             ; 4T
    ; BC = (a-b)²/4 - (a+b)²/4 = -(a×b)
    ; Negate if needed, or pre-negate the table
; Total: ~54 T-states
```

The table is generated iteratively, exploiting the fact that consecutive squares differ by odd numbers (1, 3, 5, 7...):

```z80
    ld  hl,SqrTab       ; must be 256-byte aligned
    ld  b,l : ld c,l    ; BC = 0 (odd number accumulator)
    ld  d,l : ld e,l    ; DE = 0 (running square)
SqrGen:
    ld  (hl),e
    inc h
    ld  (hl),d           ; store x²/4 as 16-bit LE
    ld  a,l : neg : ld l,a
    ld  (hl),d : dec h : ld (hl),e  ; mirror for negative index
    ex  de,hl
    inc c : add hl,bc : inc c       ; add next odd number
    ex  de,hl
    cpl : ld l,a : rla
    jr  c,SqrGen
```

For the **full 8×8 signed range** (−128 to +127), overflow checking is required because (a+b) can exceed 127. The routine by Milos "baze" Bazelides uses `JP PE` to detect overflow and switches between two algebraic forms, completing in **70–90 T-states**.

### Fixed-point 8.8 arithmetic

The **8.8 format** stores numbers in a 16-bit register pair where the high byte is the integer part and the low byte is the fractional part. HL = $0341 represents 3 + 65/256 ≈ 3.254.

| Operation | Implementation | T-states |
|-----------|---------------|----------|
| Addition | `ADD HL,DE` | **11T** |
| Subtraction | `OR A / SBC HL,DE` | **19T** |
| Multiplication | 16×16→32 routine, take middle 2 bytes | **~544T avg** |
| Negate | `XOR A / SUB L / LD L,A / SBC A,A / SUB H / LD H,A` | **24T** |

For 3D rotation matrices, demo coders typically represent sine/cosine as signed bytes (−127 to +127, effectively 1.7 fixed-point). The square-table multiply naturally produces a result where the high byte contains the integer portion of the product, eliminating explicit division. A full 3D rotation of one point requires **9 multiplications and 6 additions** — at 54T per multiply via lookup table, that's ~486T for multiplies alone, achievable at roughly 140 points per frame if multiplication is the only bottleneck.

### Sine/cosine tables with quarter-wave reconstruction

The standard approach stores **64 entries** covering 0°–90° (indices 0–63), then reconstructs the full 256-entry wave via symmetry:

```z80
; Input: A = angle (0-255, where 256 = full circle)
; Output: A = sin(angle), signed byte (-127..+127)
GetSine:
    ld  c,a              ; 4T  — save original angle
    and $3F              ; 7T  — index within quadrant (0-63)
    bit 6,c              ; 8T  — Q2 or Q4? (mirror)
    jr  z,.no_mirror     ; 7/12T
    neg                  ; 8T  — mirror: 63 - index
    add a,63             ; 7T
.no_mirror:
    ld  h,SinTable/256   ; 7T  — table must be 256-aligned
    ld  l,a              ; 4T
    ld  a,(hl)           ; 7T  — lookup
    bit 7,c              ; 8T  — Q3 or Q4? (negate)
    ret z                ; 5/11T
    neg                  ; 8T
    ret                  ; 10T
; Best case: ~51T. Worst case: ~69T
```

Cosine is simply `sin(angle + 64)` — add 64 to the angle before lookup. For **sizecoding**, Neon/Darklite's parabolic sine generator creates a usable 256-entry table in just **19 bytes** of code using a second-order difference equation (sin″(x) ≈ −sin(x)), later optimized to **16 bytes** by baze/3SC.

### ROM calculator exploitation (RST $28)

The ZX Spectrum 48K ROM contains a complete **stack-based floating-point calculator** invoked via `RST $28`. Each subsequent byte is a calculator opcode until `$38` (end-calc) terminates and returns to Z80 execution. Key opcodes: **$1F** = sine, **$20** = cosine, **$28** = square root, **$04** = multiply, **$05** = divide.

```z80
; Compute sin(angle) — costs only ~8 bytes of code!
    ld   a,(angle)
    call $2D28        ; STACK-A: push A onto FP stack
    rst  $28          ; enter calculator
    defb $1F          ; sin
    defb $38          ; end-calc
    call $2DD5        ; FP-TO-A: result in A
```

Each trigonometric function costs **1 byte** as an opcode versus 64+ bytes for a lookup table. The tradeoff is speed: the ROM calculator consumes **~10,000+ T-states** per operation. This makes it impractical for real-time effects but invaluable for 256-byte intros where code size is the binding constraint.

### LFSR pseudo-random generators

The **16-bit XorShift** by John Metcalf is the gold standard for Z80 demos — **20 bytes, 86 T-states, period 65,535**:

```z80
xrnd:
    ld  hl,1          ; 10T — seed (must not be 0; self-modified)
    ld  a,h           ;  4T
    rra               ;  4T
    ld  a,l           ;  4T
    rra               ;  4T
    xor h             ;  4T
    ld  h,a           ;  4T
    ld  a,l           ;  4T
    rra               ;  4T
    ld  a,h           ;  4T
    rra               ;  4T
    xor l             ;  4T
    ld  l,a           ;  4T
    xor h             ;  4T
    ld  h,a           ;  4T
    ld  (xrnd+1),hl   ; 16T — self-modifying: updates seed
    ret               ; 10T
; Total: 96T including RET. Shift triplet 7,9,8.
```

For absolute minimal code (plasma/fire effects where quality doesn't matter), a **5-byte** 8-bit LFSR suffices:

```z80
    ld  a,N           ; self-modified seed
    rrca              ; rotate right
    xor $B4           ; tap polynomial
    ld  (seed),a      ; store back
```

---

## The scrambled screen: address calculation and navigation

The ZX Spectrum's screen memory layout at **$4000** encodes pixel addresses as `010TTSSS LLLCCCCC`, where T = third of screen (Y bits 7,6), S = scanline within character cell (Y bits 2,1,0), L = character row within third (Y bits 5,4,3), and C = column (X/8). The crucial insight is that **Y's least significant bits are in the high byte** while its middle bits are in the low byte — a deliberate hardware design that made DRAM access efficient for the ULA but nightmarish for programmers.

### Fastest (x,y) to screen address conversion

The standard calculated routine costs **~107 T-states** and 26 bytes:

```z80
; B = Y (0-191), C = X (0-255) → HL = screen address
Get_Pixel_Address:
    ld  a,b           ; 4T  — Y coordinate
    and %00000111     ; 7T  — extract scanline bits (Y2,Y1,Y0)
    or  %01000000     ; 7T  — set base $40xx
    ld  h,a           ; 4T
    ld  a,b           ; 4T  — Y again
    rra               ; 4T  — shift Y7,Y6 into position
    rra               ; 4T
    rra               ; 4T
    and %00011000     ; 7T  — mask third bits
    or  h             ; 4T  — combine: H = 010TT SSS
    ld  h,a           ; 4T
    ld  a,b           ; 4T  — Y again
    rla               ; 4T  — shift Y5,Y4,Y3 into position
    rla               ; 4T
    and %11100000     ; 7T  — mask character row bits
    ld  l,a           ; 4T
    ld  a,c           ; 4T  — X coordinate
    rra               ; 4T  — divide by 8
    rra               ; 4T
    rra               ; 4T
    and %00011111     ; 7T  — 5-bit column
    or  l             ; 4T  — combine: L = LLL CCCCC
    ld  l,a           ; 4T
    ret               ; 10T  — Total: ~107T
```

A **lookup table approach** trades 384 bytes of RAM for a ~6% speed gain (~99T), using a pre-computed table of 192 screen row base addresses. The calculation approach dominates in practice because 384 bytes is expensive on a 48K machine.

### The INC H trick and moving down one pixel

Within a single 8-pixel character cell, the scanline bits (SSS) occupy bits 0–2 of the high byte H. This means **`INC H` moves exactly one pixel down** in just **4 T-states** — the single most important screen navigation trick on the Spectrum. When the scanline wraps from 7→0 (crossing a character cell boundary), the full "down one pixel" routine handles it:

```z80
Pixel_Address_Down:
    inc h               ; 4T  — move down 1 scanline
    ld  a,h             ; 4T
    and %00000111       ; 7T  — did scanline wrap to 0?
    ret nz              ; 5T  — no: still in same char cell, done!
    ; Crossed character boundary
    ld  a,l             ; 4T
    add a,32            ; 7T  — advance one character row
    ld  l,a             ; 4T
    ret c               ; 5T  — carry means crossed third boundary (correct)
    ; Undo unwanted third increment
    ld  a,h             ; 4T
    sub 8               ; 7T
    ld  h,a             ; 4T
    ret                 ; 10T
; Best case (within cell): 20T. Worst case (crossing third): ~50T.
```

**Converting a pixel address to its attribute address** takes just 4 instructions — a common operation for games that need to color-check or set attributes:

```z80
    ld  a,h           ; HL = pixel address
    srl a : srl a : srl a
    add $58            ; ($50 + $08 offset adjustment)
    ld  h,a            ; HL now points to attribute byte
```

---

## Stack pointer as video output: the PUSH sprite technique

The `PUSH` instruction writes 2 bytes to memory and decrements SP, all in **11 T-states** — that's **5.5 T-states per byte**, making it the fastest bulk-write mechanism on the Z80. This is 27% faster than `LD (HL),r` at 7T/byte and 45% faster than `LD (HL),n` at 10T/byte.

### The canonical pattern

```z80
    di                          ; 4T  — MANDATORY: disable interrupts
    ld  (saved_sp+1),sp         ; 20T — save SP via self-modifying code
    ld  sp,screen_line_end      ; 10T — SP → past right edge of screen line
    ld  hl,$AABB                ; 10T — pixel data (pre-loaded)
    ld  de,$CCDD                ; 10T
    ld  bc,$EEFF                ; 10T
    push bc                     ; 11T — writes 2 bytes, SP -= 2
    push de                     ; 11T — writes 2 more bytes
    push hl                     ; 11T — writes 2 more bytes (6 bytes total)
saved_sp:
    ld  sp,0                    ; 10T — restored by SMC (the 0 was patched)
    ei                          ; 4T  — re-enable interrupts
```

**Critical details:** PUSH writes **right-to-left** (decrementing address), so SP must initially point past the rightmost byte. The `DI` is absolutely mandatory — if an interrupt fires while SP points at screen memory, the Z80 pushes the return address onto the "stack" (now screen RAM), corrupting the display and causing a crash when the ISR returns to a garbage address in video memory.

### Production example: Ghost 'n Goblins (1986)

Keith Burkhill's Ghost 'n Goblins used PUSH to clear 12 screen columns per scanline in its 8-way scrolling engine. The disassembly by VilleKrum reveals the inner loop:

```z80
; Clear 12 columns × 2 scanlines. DE=0, HL=screen addr, B=line count/2
nextline:
    ld  sp,hl          ; 6T  — SP → end of line
    push de            ; 11T — clear 2 bytes (×6 = 12 bytes)
    push de : push de : push de : push de : push de
    inc h              ; 4T  — next scanline (INC H trick!)
    ld  sp,hl          ; 6T
    push de : push de : push de : push de : push de : push de
    inc h              ; 4T
    djnz nextline      ; 13T
; 165T per 2 lines = 6.875T per byte — blazingly fast screen clearing
```

The game contained **15 specialized clear routines**, one for each width from 2 to 30 columns in 2-column steps. Steve Wetherill's **Crosswize** (1988) combined PUSH sprites with self-modifying code to achieve **50fps smooth scrolling** — the JP instruction within a PUSH buffer was patched at runtime to jump to the correct offset depending on which combination of 1-byte and 2-byte PUSH opcodes were needed.

### Compiled sprites

The ultimate evolution: each sprite is compiled into executable Z80 code. Instead of data interpreted by a renderer, the sprite *is* the renderer:

```z80
sprite_draw:
    ld  sp,$4810        ; 10T — end of screen line 0 + sprite width
    ld  bc,$F0E1        ; 10T — pixel data for this line
    push bc             ; 11T — write to screen
    ld  sp,$4910        ; 10T — next scanline (H+1)
    ld  bc,$A5C3        ; 10T — different pixel data
    push bc             ; 11T
    ; ... repeat for each scanline of the sprite ...
    ret                 ; 10T
```

The LD SP addresses are **patched via SMC** when the sprite moves, making each sprite position a simple set of byte writes to modify the compiled code.

---

## Self-modifying code: rewriting instructions at runtime

The Z80 has **no instruction cache, no prefetch buffer, and no pipeline**. Instructions are fetched byte-by-byte from RAM as they execute. Modifying a byte in memory and immediately executing it is guaranteed to use the new value. This makes self-modifying code (SMC) a first-class optimization technique with zero risk of stale data — unlike modern CPUs where SMC causes pipeline flushes and cache invalidation.

### Pattern 1: patching immediate operands

The most common pattern — modify the data byte of a `LD`, `CP`, `ADD`, or `AND` instruction:

```z80
; Setup (once per frame):
    ld  a,(scroll_offset)
    ld  (patch_point+1),a    ; +1 skips the opcode byte to reach the operand
; Hot loop (runs thousands of times):
patch_point:
    cp  0                     ; 7T — the "0" has been replaced with scroll_offset
```

The `+1` skips past the opcode byte (e.g., `$FE` for `CP n`) to reach the immediate operand. For 16-bit values, `+1` addresses the 2-byte operand of instructions like `LD HL,nnnn` (opcode `$21`). In SjASMPlus, the pattern `equ $-2` labels the operand location:

```z80
routine:
    ld  hl,0              ; 10T — "0" is actually a variable
xPos equ $-2              ; label points 2 bytes back to the operand
; Later: LD (xPos),DE patches the LD HL instruction
```

### Pattern 2: patching opcodes to eliminate branches

Instead of testing a direction flag on every iteration, patch the opcode once before the loop:

```z80
; Setup:
    ld  a,$2C             ; opcode for INC L (move right)
    ; or: ld a,$2D        ; opcode for DEC L (move left)
    ld  (direction),a     ; patch the instruction
; Inner loop — no branch, no test:
direction:
    inc l                 ; 4T — this opcode is patched to INC L or DEC L
    djnz loop
; Saves ~20T PER ITERATION vs BIT/JR/JR branching
```

Dean Belfield's Bresenham line drawer in **breakintoprogram/lib-spectrum** patches `RLC D` / `RRC D` opcodes at setup time, then the inner loop runs branch-free for all four quadrants. The saving is roughly **20 T-states per pixel** in the line-drawing inner loop.

### Pattern 3: unrolled loops with per-iteration constants

```z80
; Setup: patch 8 column offsets into unrolled loop
    ld  a,(scroll_col)
    ld  (iter0+1),a : inc a
    ld  (iter1+1),a : inc a
    ld  (iter2+1),a
    ; ...
; Unrolled hot path:
iter0: ld a,0 : call draw_column    ; 7T+17T — "0" patched
iter1: ld a,0 : call draw_column    ; no index calculation needed
iter2: ld a,0 : call draw_column    ; no loop overhead
```

Each iteration saves the `LD A,(IX+n)` or `LD A,(table+offset)` that would otherwise be needed to fetch per-iteration values.

---

## Procedural generation in 256-byte intros

Fitting a visually compelling demo effect into 256 bytes demands techniques that generate maximum visual complexity from minimum code. The attribute-only strategy is the foundation: the ZX Spectrum's color RAM is just **768 bytes** with a linear layout at `$5800`, versus 6,144 bytes of pixel data in the scrambled bitmap. Writing to attribute RAM requires no complex address calculation — just `LD DE,$5800` and increment.

### The 45-degree coordinate tilt

The single most impactful sizecoding trick for visual effects is computing **U = X+Y** and **V = X−Y** instead of using raw coordinates. This rotates the coordinate system 45°, transforming mundane horizontal/vertical banding into diagonal interference patterns. The code difference is one instruction:

```z80
; Basic pattern (horizontal/vertical banding):
    ld a,c : and b : and 7 : ld (de),a    ; boring grid

; 45° tilt (diagonal interference):
    ld a,c : add b : and 7 : ld (de),a    ; dramatic diagonal pattern
```

Replacing `AND` with `ADD`, `XOR`, or `SUB` produces entirely different visual textures. Adding a frame counter creates animation. **Fluxus** by superogue (1st place, Flash Party 2020) used this technique combined with 4 cycling color ramps and the ROM calculator for sine-based wobble, all in 256 bytes including AY music.

### BB by Introspec: iterative image compression in 125 bytes of data

**BB** (1st place, Multimatograf 2014) renders a recognizable portrait from pseudo-random noise using an extraordinary technique: 64 iterations, each plotting `4×N` pseudo-random 2×2 pixel blocks using XOR. The PRNG seed for each iteration is the "compressed data" — **125 bytes** encoding a 128×96 image at a 12.3× lossy compression ratio. Seeds were found by brute-force search over ~5×256×64×65,536 values, taking 1.5 days on 7 CPU cores.

### Attribute-only animation

For sizecoding, attribute RAM's linear layout and small size make it ideal:

```z80
; Minimal attribute plasma — fits well under 256 bytes
    ld  de,$5800      ; attribute RAM
    ld  b,24          ; 24 rows
yloop:
    ld  c,32          ; 32 columns
xloop:
    ld  a,c
    add a,b           ; 45° tilt: U = X+Y
    add a,(ix+0)      ; add frame counter for animation
    and 7             ; clamp to color range
    ld  (de),a        ; write attribute
    inc de
    dec c
    jr  nz,xloop
    djnz yloop
```

This core loop produces smoothly animated diagonal color waves across the entire screen. The pixel RAM can be pre-filled with a fixed checkerboard pattern (e.g., `$55` = alternating pixels) at startup, giving the color changes visible texture.

### Known startup register values

On entry from BASIC's `RANDOMIZE USR` command, certain registers hold known values that sizecoding intros exploit to save initialization bytes: **HL' = $2758**, **IY = $5C3A** (system variables), **BC = start address**. Using IXH/IXL and IYH/IYL as extra 8-bit variables saves register pressure (2 bytes for `LD IXH,n` vs allocating a memory variable).

---

## Beam racing and multicolor: per-scanline attribute changes

The ULA **re-reads attribute bytes for every pixel row**, not just once per 8-pixel character cell. If code modifies an attribute byte between scanlines, the ULA uses the new value for the next line. This exploit enables "multicolor" — giving each 8×1 pixel strip its own color, breaking the Spectrum's notorious 8×8 color clash.

### The scanline timing budget

On the **48K Spectrum** (3.5 MHz clock), each scanline takes exactly **224 T-states**:

| Phase | Duration | Pixels |
|-------|----------|--------|
| Active display | 128T | 256 pixels |
| Right border | 24T | 48 pixels |
| Horizontal retrace | 48T | — |
| Left border | 24T | 48 pixels |

A complete frame consists of **312 scanlines** (192 display + 56 top border + 56 bottom border + 8 vsync), totaling **69,888 T-states** at exactly **50.08 Hz**. The maskable interrupt fires once per frame; the first display pixel begins **14,336 T-states** after the interrupt on the 48K model.

The **128K Spectrum** differs subtly: 228T per scanline, 311 scanlines, 70,908T per frame at 3.5469 MHz. The **Pentagon 128** uses 224T × 320 scanlines = 71,680T per frame at 3.5 MHz, giving **~48.83 Hz** with significantly more border time for computation.

### Contended memory: the 6,5,4,3,2,1,0,0 pattern

During active display on the 48K, CPU access to addresses **$4000–$7FFF** is delayed by the ULA, which has bus priority for screen fetches. The delay follows a repeating 8-T-state pattern: **6, 5, 4, 3, 2, 1, 0, 0** T-states of additional wait, cycling every 8T across the 128T display portion of each scanline. This means an instruction that would normally take 7T might take up to 13T if it hits peak contention.

Demo coders compensate by placing time-critical code in **uncontended RAM** ($8000–$FFFF on 48K), carefully tracking T-state counts with contention factored in, or deliberately exploiting contention for self-synchronization. The Pentagon 128 has **no memory contention at all** — all RAM runs at full speed regardless of ULA activity — which is why Russian demos overwhelmingly target Pentagon and exhibit timing failures on Sinclair hardware.

### NIRVANA and BIFROST multicolor engines

Einar Saukas created four progressively capable engines, all using interrupt-driven attribute rewriting synchronized to the raster beam:

| Engine | Color resolution | Screen coverage | Tiles | Key tradeoff |
|--------|-----------------|----------------|-------|---------------|
| **BIFROST*** | 8×1 (per scanline) | 18×18 chars | 16×16 ctiles | Finest color, narrowest view |
| **BIFROST*2** | 8×1 | 20×22 chars | 16×16 ctiles | Wider, more CPU-hungry |
| **NIRVANA** | 8×2 (bicolor) | 30×22 chars | 16×16 tiles | Near-full width, 8 sprites@50fps |
| **NIRVANA+** | 8×2 | 32×23 chars | Full width | True full-screen multicolor |

The fundamental constraint is bandwidth: at 3.5 MHz, the CPU can write roughly **20 bytes** during the ~96T non-display gap per scanline. A full attribute row is 32 bytes. Therefore 8×1 multicolor is physically limited to ~18–20 character columns, while 8×2 bicolor (rewriting every other scanline) allows 30–32 columns by using two scanlines' worth of border time.

All engines auto-detect the Spectrum model (48K vs 128K vs +2A/+3) and adjust their timing loops accordingly. The game logic budget while running multicolor is equivalent to roughly **a 1 MHz Z80** — the majority of CPU time is consumed by attribute rewriting.

### The floating bus trick

Reading from an unattached I/O port ($FF) during active display returns whatever byte the ULA is currently fetching from video RAM. During border/retrace, it returns $FF. Joffa Smith discovered this around 1986 and used it in **Cobra** and **Terra Cresta** to detect beam position without timing loops:

```z80
fl_bus:
    in  a,($FF)        ; 11T — read floating bus
    cp  target_attr     ; 7T  — known attribute value at target position?
    jr  nz,fl_bus       ; 12/7T — loop until match
    ; Beam is now at the known screen position
```

Using port address **$40FF** (high byte in contended range) causes the IN instruction itself to be contended, which self-synchronizes the loop to the ULA's 8-T-state fetch cycle. This works on 48K and 128K models but **not on Pentagon** (which returns nothing useful) or +2A/+3 models (which require a different latched-bus technique, first documented by Ast A. Moore in 2017).

---

## Assembler macros: compile-time code generation

Modern ZX Spectrum development overwhelmingly uses **SjASMPlus**, which supports DUP/EDUP repeat blocks, parameterized macros, and embedded Lua scripting.

### DUP/EDUP for loop unrolling

```z80
; Unrolled 8× sprite copy — zero loop overhead at runtime
DUP 8
    ld  a,(hl)        ; 7T  — read sprite byte
    ld  (de),a        ; 7T  — write to screen
    inc hl             ; 6T  — next source
    inc d              ; 4T  — next scanline (INC H trick on DE)
EDUP
; Generates 8 copies: 24T × 8 = 192T total, vs ~296T with DJNZ loop
```

### Lua scripting for lookup tables

```z80
; Generate 256-entry sine table at assembly time
ALIGN 256
sine_table:
LUA ALLPASS
    for i = 0, 255 do
        sj.add_byte(math.floor(math.sin(i * math.pi / 128) * 127 + 128))
    end
ENDLUA
```

This eliminates runtime table generation entirely — the sine table is embedded directly in the binary. The `ALIGN 256` ensures the table is 256-byte aligned, enabling single-byte indexing via `LD L,angle / LD H,sine_table/256 / LD A,(HL)`.

### Pre-shifted sprite generation

For smooth horizontal scrolling, sprites need 8 versions shifted 0–7 pixels. A macro generates all shifts at assembly time:

```z80
GENERATE_SHIFTED_SPRITE: MACRO base_data, shift
    DUP sprite_height
        ; Shift each row right by 'shift' pixels
        ; Using assembler expressions to compute shifted bytes
    EDUP
ENDM
; Generate all 8 shifts:
DUP 8
    GENERATE_SHIFTED_SPRITE sprite_data, _DUP_CNT
EDUP
```

---

## The Russian scene: technical writings and open source code

The Russian ZX Spectrum community, centered on the Pentagon 128 clone, produced an enormous body of technical literature that remains largely unknown to English-speaking sceners.

### Alone Coder (Dmitry Bystrov) — the most prolific documenter

Alone Coder's website at **alonecoder.nedopc.com/zx/** hosts what may be the largest single collection of open-source ZX Spectrum demo code in existence. Key published sources include full Z80 assembly for **NedoDemo 2** (3.5MB of sources), **The Board 2** (6MB of sources), **New Wave 48K** (6MB of sources), plus standalone engines: a complete **3D engine** (4MB), a **Mode 7 rotation engine** (100KB), and the **EvoSDK** game development kit.

His technical articles, collected in the **ZX-Guide** series and **ACNews** magazine (76+ issues through 2023), cover optimization at a level rarely matched in English:

- **"Z80 Optimization Fundamentals"** (Info Guide #7): speed, size, and compressed-size optimization strategies
- **"On Displaying Screen in One Interrupt"** (ZX-Guide #1): the LD-PUSH method for full-screen transfer within one frame
- **"Optimal DOWN HL"** (ZX-Guide #1): fastest screen line advance routine
- **"Speed Optimization for Rotation/ZoomRotation/BumpMapping"** (ZX-Guide #4): concrete effect optimization
- **"Gray Code and Program Optimization"** (Info Guide #10): using Gray codes to reduce instruction counts in iterative code
- **"ADPCM Sound Compression"** (Born Dead #0G): 4:1 audio compression for beeper playback

### Mednonogov / Copper Feet (Vyacheslav Mednonogov)

Pioneer of complex game genres on the ZX Spectrum (real-time strategy, turn-based tactics), Mednonogov released **full source code** for his major games: НЛО (UFO: Enemy Unknown, 1995), НЛО-2 (1996), Чёрный Ворон (Black Raven, 1997), and its sequel. These sources have been independently compiled and verified by the community, enabling enthusiasts to produce colorized versions for enhanced Spectrum clones. His **Asm80 cross-assembler** (published within the Black Raven source package) was itself a community reference.

### The ZXDN coding index

The single most valuable catalog of Russian ZX technical literature is the **ZXDN (ZX Documentation Network)** at alexanderk.ru/zxdn/coding.html — a comprehensive categorized index of every known programming article across all Russian electronic magazines. Categories include code optimization, digital sound, graphics effects, multicolor techniques, data compression, and demo development, spanning dozens of publications: Adventurer (15 issues, Rybinsk), ZX Format (Saint Petersburg), ACNews, Spectrofon (23 issues, the first Russian disk magazine), Born Dead, Deja Vu, and many more.

### SpeccyWiki multicolor reference

The Russian-language SpeccyWiki article on multicolor (speccy.info/Мультиколор) is the most technically detailed reference found on the subject. It documents that stack-based multicolor can cover up to **24 character cells wide** on Pentagon and **22 on dual-field machines**, with full-screen (32 cells) multicolor achievable at reduced color depth using the Con18 converter.

### Open-source demo code on GitHub

Notable repositories with full Z80 source: **3sc-demos/ganzfeld** (ZX Spectrum 128 demo, extensively commented, released at Forever 2023), **breakintoprogram/lib-spectrum** (complete game development library with vector graphics, sprites, screen buffering), **tslanina's 256-byte intros** (BrainWaves, WakaWaka, RGB — competition-winning productions with full Pasmo source), and **z88dk/z88dk** which integrates the NIRVANA and BIFROST engines with C-callable wrappers and complete example code.

---

## Conclusion: engineering within absolute constraints

The ZX Spectrum demoscene's optimization techniques are not historical curiosities — they represent **optimal solutions to constrained computation** that remain instructive today. The square-table multiplication identity eliminates hardware multiply at the cost of 512 bytes of RAM, a tradeoff that generalizes to any system where memory is cheaper than ALU cycles. Self-modifying code achieves what branch prediction does on modern CPUs — eliminating conditional overhead in inner loops — but with perfect reliability on a machine with no speculative execution. The PUSH sprite technique of repurposing the stack pointer as a DMA controller exploits the Z80's internal microarchitecture (PUSH's tight 11T timing results from its dedicated bus cycle sequence) in a way that is impossible to replicate with any other instruction combination.

The Russian community's contributions deserve particular emphasis. Alone Coder's archive of source code (totaling tens of megabytes of Z80 assembly) and technical articles, Mednonogov's published commercial game sources, and the ZXDN index collectively form a parallel technical literature that is richer in some areas — particularly multicolor techniques and Pentagon-specific optimization — than anything available in English. The Pentagon's lack of memory contention created a cleaner optimization target that paradoxically produced more sophisticated timing code, because coders could reason about T-states without accounting for the unpredictable ULA contention delays that plague Sinclair hardware.

For the book developer seeking to go deeper, the primary sources to study are: baze's **Z80 Bits** for mathematical routines, the **breakintoprogram/lib-spectrum** GitHub repo for production-quality game library code, Alone Coder's **ZX-Guide** series for optimization theory, Einar Saukas's engine source code in **z88dk** for multicolor internals, and the competition-winning 256-byte intros by superogue, Introspec, and tslanina for masterclasses in extreme code density.