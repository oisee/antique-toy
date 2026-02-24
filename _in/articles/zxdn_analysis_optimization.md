# ZXDN Optimization Articles: Analysis

Source files: `/Users/alice/dev/antique-toy/_in/raw/zxdn/coding/`
Analyzed: 2026-02-24

---

## 1. zg4optim.txt — Alone Coder: Speed Optimization for Rotation and BumpMapping

**Author:** Alone Coder (Дима Быстров / Dima Bystrov)
**Source:** ZX-Guide #4, Ryazan, 25.11.2001

### Summary

A focused tutorial on optimizing two specific demoscene effects: Rotation (including ZoomRotation) and BumpMapping. Alone Coder walks through progressively faster implementations, showing how to reduce the inner-loop cost from 70 t/c (T-states per chunk) down to as low as 16.5 t/c for rotation and 23.5 t/c for bump mapping. The article references Power Up (Exploder) as a positive example and Refresh as a negative one.

### Key Techniques (with cycle counts)

#### Rotation / ZoomRotation

| Approach | T-states/chunk | Notes |
|----------|---------------|-------|
| Naive (ADD IX,BC + EXX + LDI) | 70 t/c | Too many LD transfers |
| Register-only with JR NC (ADD A,B/C, INC H/L) + PUSH output | 47.5 t/c | Outputs via stack (backwards), 4 variants needed for inc/dec signs |
| Pre-generated table via POP (POP BC; ADD HL,BC; LDI) | 37 t/c | Table generated per frame, one per scanline |
| Table + PUSH output (LD BC,...; ADD HL,BC; LD E/D,(HL); PUSH DE) | 33.5 t/c | Stack output, paired reads |
| Generated INC H/INC L procedure + PUSH output | **16.5 t/c** | Self-modifying/generated code; ~5000 T-states generation overhead per frame |
| 4-pixel batch with chunk output | 33 t/4c = 8.25 t/c | References Illusion (Sonic rotation scene) |
| Combined chunk render + coordinate correction | 28.5 t/c per chunk, 26.5 t/c with DEC B elimination | Inline chunk output, flip-flop INC/DEC B trick |

**Key insight**: Batch multiple pixels per coordinate correction. Instead of correcting coordinates per pixel, correct every 2, 4, or even 32 pixels. The final example achieves 33 T-states per 4 chunks for a full-screen rotation:

> "Советую умножить 33(t)*16(x)*96(y)=50688 t! И это весь экран!"
> [Multiply 33(T)*16(x)*96(y)=50,688 T! And that's the whole screen!]

#### BumpMapping

| Approach | T-states/chunk | Notes |
|----------|---------------|-------|
| Stack-based (POP HL; ADD HL,BC; LDI) | 37 t/c | Uses all 3 "multimedia" Z80 instructions |
| Generated LD HL + ADD HL,BC + PUSH output | 33.5 t/c | Pre-built procedure |
| Reduced range ADD A,imm + LD L,A + PUSH output | **23.5 t/c** | Exploits that displacements fit in -128..+127 |
| Chunk variant with multicolor | 29 t/c | Inline chunk output |

**Key insight for bump**: relief displacements across a scanline usually fit in a signed byte (-128..+127), so you can replace 16-bit HL operations with 8-bit A operations, saving significant time per pixel.

### Code Patterns Worth Noting

1. **Stack output (writing backwards via PUSH DE)**: Paired reads into D and E from texture, then PUSH DE writes 2 bytes to screen. Requires DI and SP pointing at screen bottom. The article alternates between two halves of the inner loop (one loads E, one loads D, then PUSH).

2. **Generated procedure with INC H/INC L**: At frame start, a generator routine writes `INC H` / `INC L` / `LD E,(HL)` sequences into a buffer based on the current rotation angle. The generated code is then called once per scanline. Generation costs ~5000 T-states but eliminates all coordinate arithmetic from the inner loop.

3. **Chunk output via JP table (by Monster/Sage)**: A table of small procedures + JP instructions, addressed by chunk colour pairs (`%11aaaa00 11bbbb00`). Each procedure writes 4 scanlines of a chunk. SP points to the ChunkMap, so RET chains to the next chunk. This is effectively RET-chaining for chunk rendering.

4. **DEC B elimination trick**: When INC B / DEC B alternate between chunks, one vertical line is removed from the chunk pattern (7 colours instead of 8), making the alternation invisible. Saves 2 t/c.

5. **4-pixel batched rotation with PUSH**:
```z80
    [inc h]
    [inc l]
    LD E,(HL) ;%0aa00bb0
    ----------
    [inc h]
    [inc l]
    LD D,(HL) ;%0cc00dd0
    PUSH DE   ;SP=screen!
```
33 T-states for 4 chunks. The encoding packs two 2-colour chunks into each byte.

### Direct Quotes

> "При проектировании эффекта следует в первую очередь думать о скорости внутреннего цикла (inner loop) - цикла, тело которого выполняется максимальное количество раз."
> [When designing an effect, you should first think about the speed of the inner loop -- the loop whose body executes the maximum number of times.]

> "Скорость программы во многом определяется количеством команд LD. Действительно, к чему переливать из пустого в порожнее?"
> [A program's speed is largely determined by the number of LD instructions. Indeed, why pour from empty into void?]

> "Все использованные фрагменты программ сочинены мной, в чужой код глядеть не имею привычки. Любые совпадения случайны."
> [All code fragments used were composed by me; I do not have the habit of looking at other people's code. Any similarities are coincidental.]

### NEW vs. Our Book

**Already covered in Ch.1/Ch.3:**
- Inner-loop focus and T-state budgeting (Ch.1)
- PUSH-based output (stack as data pipe, Ch.3)
- Self-modifying code concept (Ch.3)
- Code generation concept (Ch.3)

**NEW / worth adding:**
- **Concrete rotation inner loop optimization progression** (70 -> 47.5 -> 37 -> 33.5 -> 16.5 t/c) -- excellent teaching sequence for a rotation chapter (Ch.6 or Ch.7)
- **Batching pixels per coordinate correction** -- a critical real-world optimization not covered in our toolbox chapter; the idea that you correct coordinates every N pixels rather than every pixel
- **Monster/Sage chunk output technique** with JP/RET dispatch table for chunk rendering -- a different application of RET-chaining than DenisGrachev's tile approach (Ch.3 covers RET-chaining but not this variant)
- **Bump mapping as "light source projection"** -- practical implementation insight for Ch.8 (if we cover bump)
- **DEC B elimination trick** via alternating INC/DEC and removing one colour line
- **The -128..+127 range optimization** for bump mapping -- shrinking 16-bit operations to 8-bit when displacement range permits
- **Claim of 50,688 T-states for full-screen rotation** -- a concrete benchmark we could reference/verify

---

## 2. ig7optim.txt — Alone Coder: Fundamentals of Z80 Optimization

**Author:** Alone Coder (A. Coder)
**Source:** Info Guide #7, Ryazan, 06.2005 (with corrections from Errata IG#8)

### Summary

A comprehensive optimization guide covering three domains: size optimization, packed-size optimization (for disk/ROM), and speed optimization. Also includes a useful catalogue of ZX Spectrum 48K ROM routines usable from user programs. This is the most "textbook-like" of the three articles -- a systematic reference rather than a demo-specific tutorial.

### Key Techniques

#### Size Optimization

1. **CALL addr : RET -> JP addr** (or JR addr). Classic tail-call elimination.

2. **CALL addr : JP addr2 -> LD BC,addr2 : PUSH BC** then place code near addr. Push return address and fall through.

3. **Multiple entry points**: Merge similar procedures by making them share code with different entry points:
```z80
OUT0    LD A,16
        JR $+4
OUT7    LD A,23
OUTME   LD (pg),A
OUTNO   PUSH BC
        LD BC,32765
        OUT (C),A
        POP BC
        RET
```

4. **"Forbidden constructions"** (suboptimal patterns to always replace):
   - `SLA A` -> `ADD A,A`
   - `SLA L : RL H` -> `ADD HL,HL`
   - `RL L : RL H` -> `ADC HL,HL`
   - `PUSH HL : SBC HL,DE : POP HL` -> `SBC HL,DE : ADD HL,DE` (when CY=0; preserves flags)
   - `DEC B : JR NZ,loop` -> `DJNZ loop`
   - `LD A,reg : OR A` -> `INC reg : DEC reg` (not for index regs)
   - Full alternative `JR C,cy : LD reg,num : JR ok : cy: LD reg,num2 : ok` -> `SBC A,A : AND num^num2 : XOR num` (for accumulator)

5. **Self-modifying variables** (`var1=$+1 : LD DE,0`): embed variables directly in instruction operands. Most efficient when the variable is used in subtraction or similar operations.

6. **IY+disp for variables**: Use BASIC system variables area via IY register for exotic variable access patterns.

7. **Loop exit by address overflow**: `INC L : JR NZ,loop` -- exit when low byte wraps, eliminating separate counter.

8. **ROM fragment reuse**: Use ROM routines as callable procedures. Notable addresses:
   - `$1661` (#1661): `LDDR : RET`
   - `$33C3` (#33C3): `LDIR : RET`
   - Useful for conditional calls and jumps to save code bytes.

#### Packed-Size Optimization

- Place similar code blocks adjacent for better LZ compression
- Unrolling (`DUP...EDUP`) sometimes compresses better than loops
- `JP addr` series compresses better than `JR rel` series (fixed addresses vs. relative offsets)
- Fill unused variable areas with zeros or adjacent opcodes
- Exclude buffer regions from the compressed block

#### Speed Optimization

1. **Profile before optimizing**: Use a pass-counter pattern (self-modifying multi-byte counter) to count loop iterations at runtime:
```z80
    PUSH AF
    LD A,0
    ADD A,1
    LD ($-3),A    ; self-modifying 24-bit counter
    LD A,0
    ADC A,0
    LD ($-3),A
    LD A,0
    ADC A,0
    LD ($-3),A
    POP AF
```

2. **Register allocation**: Keep data in registers, minimize memory access. Use alternate register set (EXX/EX AF,AF'). IX/IY are better as accumulators/counters than for indexed addressing (indexed access is slow: LD r,(IX+d) = 19 T-states).

3. **Aligned data**: Place data at "round addresses" (`$xx00`) so address calculation simplifies (e.g., `INC L` instead of `INC HL`).

4. **Square-of-half-sum multiplication**: "умножение через квадрат полусуммы минус квадрат полуразности" -- table-based multiplication using the identity `a*b = ((a+b)/2)^2 - ((a-b)/2)^2`. Requires pre-generated squares table.

5. **Stack as computation aid**: Use `LD SP,HL`, auto-increment, procedure tables, call chains in stack. Use `EX (SP),HL` for additional 16-bit operand.

6. **Bypass procedures in special cases**: Skip computation entirely when result is known (e.g., zero-area sprites).

7. **Exploit post-loop register state**: After a loop completes, registers often contain useful values (zeros, boundary addresses). Use them directly instead of reinitializing.

### Useful ROM Procedures Listed

The article provides a catalogue of ZX Spectrum 48K ROM routines:
- `#E88`: Screen address -> attribute address conversion
- `#E9B`/`#E9E`: Character row number -> screen address
- `#1660`: `EX DE,HL : LDDR : RET`
- `#2F8B`: `HL = A*10 + C` (BCD helper)
- `#3406`: `A = BC = A*5 : ADD HL,BC : RET`
- Various short `LD`/`INC`/`RET` sequences useful as stack-pushed "Forth-style" primitives

### Direct Quotes

> "Существует 4 направления оптимизации: по размеру, по скорости, по сжатому размеру и по объёму исходника."
> [There are 4 directions of optimization: by size, by speed, by compressed size, and by source volume.]

> "В конце концов запретите прерывания и задействуйте стек - либо как хранилище потока данных на ввод или вывод, либо как дополнительное 16-разрядное слагаемое при вычислениях."
> [Ultimately, disable interrupts and employ the stack -- either as a data stream store for input or output, or as an additional 16-bit operand for computations.]

> "ЛЮБЫЕ дикие идеи, какие только придут в вашу голову. Далеко не все варианты испробованы, велик шанс найти что-то новое, ни с кем не советуясь!"
> [ANY wild ideas that come into your head. Not all variants have been tried -- there is a great chance of finding something new without consulting anyone!]

> "в ассемблере, в отличие от ЯВУ, возможно сколько угодно точек входа в процедуру!"
> [In assembler, unlike high-level languages, you can have as many entry points into a procedure as you want!]

### NEW vs. Our Book

**Already covered in Ch.1/Ch.3:**
- T-state budgeting and inner-loop focus (Ch.1)
- Stack hijacking for data output (Ch.3)
- Self-modifying code (Ch.3)
- Unrolled loops (Ch.3)
- LDI vs LDIR comparison (Ch.3)

**NEW / worth adding:**
- **"Forbidden constructions" list** -- practical peephole optimization patterns (SLA A -> ADD A,A, etc.). These are universally useful and not currently in our book. Good candidate for a sidebar or appendix.
- **Multiple entry points in procedures** -- the "tree" pattern (OUT0/OUT7/OUTME/OUTNO) for size optimization. Not covered anywhere.
- **Self-modifying variables** ($+1 pattern) -- we cover SMC for stack save/restore but not the general pattern of embedding variables in instruction operands.
- **ROM routine catalogue** -- useful reference; could go in an appendix about the ZX Spectrum environment.
- **Pass-counter profiling pattern** -- a runtime profiling technique using SMC. Our Ch.1 covers border-colour timing but not iteration counting.
- **Packed-size optimization** -- an entire optimization domain we do not cover. Relevant to demo releases where disk space matters.
- **Square-of-half-sum multiplication** -- table-based fast multiply. Referenced as a technique but not implemented. Worth covering in Ch.4 (if we have a math chapter) or as an example.
- **Post-loop register state exploitation** -- a general principle not explicitly taught.
- **INC L : JR NZ,loop** -- counter-free loop termination via address byte overflow. Elegant pattern not in our book.

---

## 3. bd0abopt.txt — ALK/XTM: How to Code Optimally (Parts I & II)

**Author:** ALK/XTM
**Source:** Born Dead #0A, Samara, 03.07.1999 (Part I) + Born Dead #0B, Samara, 01.08.1999 (Part II, correction)

### Summary

A hands-on article from the 512-byte intro competition scene. ALK describes optimization techniques developed while writing ABSENT, a 512-byte intro for Chaos Construction '99. The article covers sine table generation in 75 bytes, attribute sprite output, screen clearing, and general optimization philosophy through concrete before/after examples. The tone is irreverent and practical.

### Key Techniques

#### Sine Table Generation (75 bytes = 44 code + 31 data)

A delta-RLE packed sine table that unpacks into 256 bytes at runtime. The RLE data encodes 1/4 period; the second quarter is a mirror copy, the second half is a direct copy. Each RLE byte packs:
- Bits 3-6: packet length (number of values)
- Bits 0-2: delta increment (+0..+7)

This saves 256 - 75 = 181 bytes vs. storing the raw table -- critical for 512-byte intros.

**Code pattern:**
```z80
SINTAB  EQU     #C000
        XOR     A
        LD      E,A
        LD      D,SINTAB/256
        LD      HL,RLESIN
        EX      AF,AF'
LRP1    LD      A,(HL)
        RRA : RRA : RRA
        AND     #F        ; packet length
        LD      B,A
        LD      A,(HL)
        AND     7         ; delta
        LD      C,A
        EX      AF,AF'
PVT     LD      (DE),A
        INC     E
        ADD     A,C       ; accumulate
        DJNZ    PVT
        EX      AF,AF'
        INC     HL
        BIT     6,E       ; quarter done?
        JR      Z,LRP1
        ; Mirror 2nd quarter
        ; LDIR 2nd half
```

#### Attribute Sprite Output (minimal code)

A bit-unpacker that reads a 1-bit-per-pixel sprite and outputs full attributes:
```z80
        RLC     (HL)      ; rotate sprite bit into carry
        SBC     A,A       ; A = 0 or #FF based on carry
        LD      (DE),A    ; write attribute
```

The `SBC A,A` trick: with carry set, `SBC A,A` produces #FF; with carry clear, produces 0. Variants:
- `AND #COLOR` after `SBC A,A` for monochrome-on-black
- `ADD A,#COLOR2` for two-colour sprites
- `AND E` for pseudo-colour using screen address as colour source
- Additional `AND C` with `SLI C` for fade-in effect (C cycles through 0, 1, 3, 7, #F, #1F, #3F, #7F, #FF)

**Note on `SLI C`**: The article uses the undocumented `SLI` (Shift Left and Insert 1) instruction, which shifts left and sets bit 0 to 1. Used to create a progressive mask: 0 -> 1 -> 3 -> 7 -> #F -> #1F -> #3F -> #7F -> #FF.

#### Screen Clearing Comparison

Four approaches compared by size (in bytes):

| Method | Size | Notes |
|--------|------|-------|
| LD/INC/DEC/OR/JP loop | 15 bytes | "Lamerstvo" (lameness) |
| LDDR fill | 12 bytes | "Normal" |
| BIT 6,H termination | 10 bytes | "Correct" |
| PUSH-based (3456x PUSH DE) | 3468 bytes | "Fast" -- 3456 PUSHes via `EI:HALT:LD SP,#5B00:.3456 PUSH DE:LD SP,HL` |

**Part II correction**: The 10-byte version was further improved to 9 bytes:
```z80
; Was:                      ; Corrected:
XOR   A                     XOR   A
LD    HL,#5B00              LD    HL,#5B00
DEC   HL                    DEC   HL
LD    (HL),A                LD    (HL),A
BIT   6,H                   OR    (HL)
JR    NZ,$-4                JR    Z,$-3
```
`OR (HL)` is 1 byte shorter than `BIT 6,H` (2 bytes) and works because the loop fills with zeros, so `OR (HL)` keeps A=0 and Z flag set until we exit the `$4000-$5AFF` range.

#### General Optimization Patterns

1. **Eliminate unnecessary subroutine wrapping**: If a procedure is called once, inline it.

2. **`CALL addr : RET` -> `JP addr`**: Classic tail call. ALK says: "тем, кто использует конструкции типа CALL SUBR1 : RET следует публично высказывать фи" [those who use CALL SUBR1 : RET constructions should be publicly shamed].

3. **Nested CALL for repeated subroutine calls**: Instead of 8x `CALL SUBR2` (24 bytes), use nested calls:
```z80
; "Correct" (12 bytes):
CALL SUBR_X     ; 3
....
CALL SUBR_X     ; 3
....
SUBR_X CALL SUBR_Y  ; 3
SUBR_Y CALL SUBR2   ; 3
SUBR2  ....
       RET
```
Each CALL doubles the execution count. 2 CALLs at top level + 2 levels of nesting = 4 executions each time.

4. **Exploit post-subroutine register state**: If a subroutine leaves D=#FF and B=#BF, use those values directly instead of reloading.

5. **`EX (SP),HL : JP (HL)`** instead of `RET` + `PUSH HL`: When a subroutine needs to return a value and transfer control, swap the return address with the result on the stack, then jump. Saves PUSH instructions:
```z80
; Instead of:           ; Use:
SUBRA  ....             SUBRA  ....
       LD L,H                  LD L,H
       SBC A,A                 SBC A,A
       LD H,A                  LD H,A
       RET              ;1     EX (SP),HL ;1
                                JP (HL)    ;1
; Caller:               ; Caller:
       CALL SUBRA              CALL SUBRA
       PUSH HL          ;1     ....  (result already on stack)
```

6. **Combining operations**: `CP #5B : ... : XOR A : OUT (C),A` -> `SUB #5B : ... : OUT (C),A` -- the SUB leaves A=0 after the comparison succeeds, eliminating the separate `XOR A`.

7. **OUTI trick**: Replace `EX AF,AF' : LD A,(HL) : OUT (C),A : INC HL : EX AF,AF'` (6 bytes) with `OUTI` (2 bytes) when outputting sequential bytes to a port.

#### Dithered Screen Pattern (for attribute halftonesn)

```z80
        LD      C,#AA
        LD      HL,#4000
LP1     LD      (HL),C
        INC     L
        JR      NZ,LP1
        RRC     C       ; alternate #AA / #55
        INC     H
        LD      A,H
        SUB     #58
        JR      NZ,LP1
```
Fills the screen with alternating `#AA` / `#55` (checkerboard pattern), rotating between lines. Used to create halftone effects in attribute-only demos.

### Direct Quotes

> "Любую программу можно соптимизировать до двух байт без потери её функциональности."
> [Any program can be optimized down to two bytes without losing its functionality.]
> -- Attributed to M.M.A (probably a joke/aphorism from the scene)

> "тем, кто использует конструкции типа CALL SUBR1 : RET следует 'публично высказывать фи'."
> [Those who use constructions like CALL SUBR1 : RET should be 'publicly shamed'.]

> "Чтобы вам сделать такого, чтобы вы от меня как бы отстали?"
> [What do I have to do to make you leave me alone?]
> -- Opening of Part II, characteristic demoscene irreverence.

> "говорят, недокументированная команда.. :)"
> [They say it's an undocumented instruction.. :)]
> -- On `SLI C`, the undocumented shift-left-insert-1 opcode.

### NEW vs. Our Book

**Already covered in Ch.1/Ch.3:**
- PUSH-based screen clearing (Ch.3)
- Tail-call optimization (`CALL+RET` -> `JP`) is implicitly assumed
- Self-modifying code concept (Ch.3)
- T-state awareness (Ch.1)

**NEW / worth adding:**
- **Delta-RLE sine table generation** (75 bytes) -- excellent for a size-coding or intro-coding chapter. Not covered anywhere in our book. Compact sine generation is fundamental to many effects (plasma, Lissajous, rotation, 3D).
- **`SBC A,A` as conditional mask** -- after a carry-producing instruction, `SBC A,A` gives #FF (carry set) or #00 (carry clear). Not explicitly taught, but widely used. Should be in Ch.3 toolbox or a "bit tricks" sidebar.
- **`SLI` (undocumented opcode)** -- shift left, insert 1 into bit 0. Used for progressive mask generation. Worth a sidebar on undocumented Z80 instructions.
- **`EX (SP),HL : JP (HL)` return trick** -- replaces CALL+PUSH for returning values via the stack. An advanced stack trick not in Ch.3.
- **Nested CALL doubling** -- recursive procedure structure for compact repeated execution. Not covered.
- **OUTI for sequential port output** -- replaces manual LD+OUT+INC sequences. Not mentioned in our book.
- **Dithered checkerboard fill** for attribute halftones -- a concrete technique for attribute-only effects.
- **`OR (HL)` termination** for downward screen clear -- saves 1 byte over `BIT 6,H` test. Extreme size optimization.
- **Attribute sprite unpacker** -- compact 1-bit to attribute expansion using `RLC (HL) : SBC A,A`. A pattern worth teaching for intro coding.
- **Post-subroutine register exploitation** as explicit principle -- reuse registers left by the previous operation.

---

## Cross-Article Summary: What to Add to the Book

### High-Priority Additions (techniques used in many demos)

1. **"Forbidden constructions" reference list** (from ig7optim): `SLA A` -> `ADD A,A`, `SLA L:RL H` -> `ADD HL,HL`, etc. These are universally useful peephole patterns. **Candidate: Ch.3 sidebar or Appendix.**

2. **`SBC A,A` conditional mask** (from bd0abopt): Fundamental bit trick used everywhere. **Candidate: Ch.3 toolbox.**

3. **Self-modifying variables** (`$+1` pattern, from ig7optim): General pattern for embedding variables in instruction operands. We cover SMC for SP save/restore but not the general variable case. **Candidate: Ch.3, expand SMC section.**

4. **Pixel batching for rotation** (from zg4optim): Correct coordinates every N pixels instead of every pixel. Core optimization for any coordinate-mapped effect. **Candidate: rotation/zoom chapters.**

5. **Inner-loop optimization progression** (from zg4optim): The 70 -> 47.5 -> 37 -> 33.5 -> 16.5 t/c walkthrough for rotation is a model teaching sequence. **Candidate: rotation chapter.**

### Medium-Priority Additions

6. **Delta-RLE sine table** (from bd0abopt): Compact sine generation, essential for size-limited demos. **Candidate: Appendix on sizecoding, or Ch.19 (intro coding).**

7. **ROM routine catalogue** (from ig7optim): Usable ROM fragments for size optimization. **Candidate: Appendix.**

8. **Pass counter profiling** (from ig7optim): Runtime iteration counting via SMC. Complementary to our border-colour timing. **Candidate: Ch.1 sidebar.**

9. **`EX (SP),HL : JP (HL)` return trick** (from bd0abopt): Advanced stack manipulation. **Candidate: Ch.3, expand stack tricks.**

10. **Packed-size optimization domain** (from ig7optim): Optimizing for compression ratio. **Candidate: Ch.13 (compression) or sidebar.**

### Low-Priority / Niche

11. **`SLI` undocumented opcode** (from bd0abopt): Useful but niche. **Candidate: sidebar on undocumented Z80.**
12. **OUTI for sequential port output** (from bd0abopt): Useful for AY/port work. **Candidate: Ch.10-11 (sound).**
13. **Nested CALL doubling** (from bd0abopt): Mainly for extreme size coding. **Candidate: sizecoding appendix.**
14. **Monster/Sage chunk dispatch via JP table** (from zg4optim): A specialized RET-chain variant. **Candidate: Ch.3 sidebar or rotation chapter.**
15. **INC L : JR NZ loop termination** (from ig7optim): Address-overflow loop exit. **Candidate: Ch.3 sidebar.**

### Attribution Notes

- Alone Coder (Dima Bystrov) is one of the most prolific ZX Spectrum scene writers. ZX-Guide and Info Guide were Ryazan-based diskmags.
- ALK/XTM wrote from Samara. Born Dead was a notable scene gazette, with BD#0A being the "jubilee" (10th) issue timed for CC'99.
- M.M.A is referenced as a co-author/collaborator in the Born Dead articles.
- Monster/Sage is credited by Alone Coder for the chunk output technique.
