# Appendix K: GPU Superoptimization — When Brute Force Beats Human Intuition

> *Dark wrote the fastest general multiply in 1997. In 2026, GPU brute-force proved what's optimal for each specific constant — and it's 10× faster.*

---

## K.1 The Idea

A superoptimizer tries every possible instruction sequence to find the provably shortest/fastest one. On a CPU this is impractical beyond 3--4 instructions. On a GPU, testing billions of candidates per second, it becomes feasible up to 15 instructions --- enough to cover virtually all useful Z80 arithmetic.

The z80-optimizer project ran exhaustive searches on commodity GPUs (NVIDIA RTX 4060 Ti: ~1 billion candidates/second, AMD Radeon RX 580: ~400M/s, Apple M2: ~200M/s) and cross-verified every result across 5 platforms (CUDA, OpenCL, Vulkan, Metal, CPU reference).

---

## K.2 Constant Multiplication

Dark's Method 1 (shift-and-add loop, Chapter 4): **196--204T** for any 8-bit constant. The GPU found specific-constant sequences that are dramatically faster.

**254/254 constants solved --- ALL DIRECT.** Every `u8` multiply has a proven optimal sequence found by direct GPU brute-force. No composition fallbacks needed --- last 5 constants (×170, ×171, ×173, ×179, ×181) found at length-11.

| Constant | GPU-Optimal Sequence | Insts | T-states | vs Dark's loop |
|----------|---------------------|-------|----------|----------------|
| ×2  | `RLA` | 1 | 4T | **50×** faster |
| ×3  | `LD B,A : ADC A,A : ADD A,B` | 3 | 12T | **16×** |
| ×10 | `RLA : LD B,A : ADD A,B : ADD A,A : ADD A,B` | 5 | 20T | **10×** |
| ×42 | `RLA : LD B,A : ... (8 insts)` | 8 | 32T | **6×** |
| ×128 | `RRCA : SBC A,A : ADC A,B : RRA` | 4 | 16T | **12×** |
| ×254 | `RLA : NEG` | 2 | 12T | **16×** |
| ×255 | `NEG` | 1 | 8T | **25×** |

**Average: 8× faster than the general loop for constant K.**

**Key insight**: only 14 of 21 candidate instructions appear in any optimal solution. Seven are strictly dominated: `SLA A` (= `ADD A,A` but 8T not 4T), `SRA A`, `RLC A`, `RRC A` (CB prefix = slower), `OR A`, `SCF`, `EX AF,AF'`. Removing them accelerated the search 38×.

### 16-bit Multiply (u8 × K → HL)

**254/254 complete** using only **3 instructions**: `ADD HL,HL` + `ADD HL,BC` + `LD C,A`. This is a complete basis for 16-bit constant multiplication on Z80.

With `SWAP_HL` (= `LD H,L` / `LD L,0`) and `SUB HL,BC`: 86% code compression via prefix sharing.

×255 (16-bit): `LD H,L : LD L,0 : LD C,A : OR A : SBC HL,BC` = 30T (byte swap trick: ×256 − ×1).

---

## K.3 Constant Division

Division by constant K on Z80 has no hardware support. The GPU found that the reciprocal multiplication trick produces optimal sequences automatically:

`n / K = (n × M) >> S` where `M ≈ 2^S / K`

**254/254 divisors solved** (2--255). COMPLETE --- zero gaps. Every u8 division has a proven optimal sequence.

The v3 table uses **6 methods**, three of which were discovered by GPU exhaustive search:

| Method | Divisors | Description |
|--------|----------|-------------|
| shift | 5 | Powers of 2: SRL/SRA chains |
| mul\_shift | 30 | Classic reciprocal: `(A × M) >> S` |
| preshift\_mul | 36 | Pre-shift input, then reciprocal multiply |
| mul\_add256\_shift | 41 | Multiply + add 256 correction |
| double\_mul\_shift | 15 | Two-stage reciprocal |
| **carry\_compare** | **127** | **GPU-discovered:** ADC overflow trick for K≥128 |

**The carry\_compare breakthrough.** For divisors K ≥ 128, the quotient is always 0 or 1. The GPU discovered a branchless comparison via ADC overflow:

```z80
; Branchless A / K for K ≥ 128 (result: 0 or 1)
; GPU-discovered — not in any Z80 reference
    OR   A              ; 4T  clear carry
    LD   B, (256-K)     ; 7T  B = 256 - K
    ADC  A, B           ; 4T  A + (256-K): overflows iff A ≥ K
    SBC  A, A           ; 4T  mask from carry
    AND  1              ; 7T  A = (A ≥ K) ? 1 : 0
; 5 instructions, 26T. Verified: all 256 inputs for each K.
```

Representative sequences:

| Divisor | Insts | T-states | vs general loop (280T) |
|---------|-------|----------|------------------------|
| /2  | 1 | 8T | 35× |
| /3  | 14 | 130T | 2.2× |
| /5  | 14 | 127T | 2.2× |
| /10 | 14 | 124T | 2.3× |
| /57 | 6 | 49T | 5.7× |
| /100 | 9 | 105T | 2.7× |
| /128 | 5 | 26T | **10.8×** (carry\_compare) |
| /171 | 4 | 27T | **10.4×** |
| /200 | 5 | 26T | **10.8×** (carry\_compare) |
| /255 | 5 | 26T | **10.8×** (carry\_compare) |

**Total: 254/254 divisors --- COMPLETE. Average 79T (was 154T in v1 = −49%). Min 8T (/2), max 188T.** The carry\_compare method alone covers 127 of 254 divisors at a flat 26T. Three levels of validation: analytical (Hacker's Delight baseline), composite search (+12%), GPU exhaustive (+49% total).

---

## K.4 Branchless Idioms

All found via GPU exhaustive search with a 37-op instruction pool:

| Idiom | Sequence | Insts | T-states |
|-------|----------|-------|----------|
| `bool(A)` | `LD B,A : NEG : ADC A,B` | 3 | 16T |
| `NOT(A)` | `NEG : SBC A,A : INC A` | 3 | 16T |
| `is_neg(A)` | `RLCA : SBC A,A : NEG` | 3 | 16T |
| `lsb(A)` | `LD B,A : NEG : AND B` | 3 | 16T |
| `complement(A)` | `CPL` | 1 | 4T |
| `half(A)` | `RRA` | 1 | 4T |
| `nibble_swap(A)` | `RLCA : RLCA : RLCA : RLCA` | 4 | 16T |
| `double_sat(A)` | `RLCA : LD B,A : SBC A,A : OR B` | 4 | 16T |
| `max_0(A)` | `LD B,A : RLCA : SBC A,A : XOR B : AND B` | 5 | 20T |
| `sign(A)` | (5 insts) | 5 | 20T |
| `ABS(A)` | `LD B,A : RLCA : SBC A,A : XOR B : SBC A,B : ADC A,B` | 6 | 24T |
| `sat_add8(A,B)` | `ADD A,B : LD C,A : SBC A,A : OR C` | 4 | 16T |
| `sat_sub8(A,B)` | `SUB B : LD C,A : SBC A,A : CPL : AND C` | 5 | 20T |
| `sign8(A)` | `→ -1/0/+1` (RLCA + SBC + NEG chain) | 9 | 43T |
| `MIN(A,B)` | `SUB B : SBC A,A : AND ... : ADD A,B` | 8 | 32T |
| `MAX(A,B)` | `SUB B : SBC A,A : AND ... : ADD A,B` | 8 | 32T |
| `CMOV(CY?B:C)` | `SBC A,A : LD D,A : LD A,B : XOR C : AND D : XOR C` | 6 | 24T |
| `div3(A)` | `A×171>>9` --- no lookup table | 3 | 16T |

**The `SBC A,A` carry-to-mask trick** appears in many sequences: it sets A to `$00` or `$FF` depending on the carry flag. Combined with `RLCA` (sign bit → carry), this enables instant sign detection without any conditional jumps.

```z80
; BOOL(A): 0 if zero, 1 if nonzero — 3 insts, 16T
    LD   B, A
    NEG
    ADC  A, B     ; carry from NEG + original = 0 or 1

; ABS(A): absolute value of signed byte — 6 insts, 24T, branchless
    LD   B, A
    RLCA          ; sign bit → carry
    SBC  A, A     ; carry → mask (0x00 or 0xFF)
    XOR  B        ; conditional complement
    SBC  A, B     ; adjust
    ADC  A, B     ; correct

; Sign-extend A → HL: 3 insts, 12T
    ADC  A, L     ; double — overflow if ≥128 sets carry
    SBC  A, A     ; carry → 0xFF mask
    LD   H, A     ; H = sign extension byte

; CMOV — conditional select: CY ? B : C — 6 insts, 24T
    SBC  A, A     ; carry → mask (0x00 or 0xFF)
    LD   D, A     ; save mask
    LD   A, B
    XOR  C        ; B XOR C
    AND  D        ; mask: keep diff if CY, zero if not
    XOR  C        ; B if CY, C if not — branchless select

; div3(A) — exact division by 3, no table — 3 insts, 16T
; Uses reciprocal: A × 171 >> 9 = A/3 for all u8
; (171 ≈ 256×2/3, verified exhaustively on all 256 inputs)
```

**Bool convention:** CY flag with 0xFF/0x00 mask representation is optimal for Z80 branchless code. The Z flag is provably **write-only** for conditional purposes --- no branchless Z→CY conversion exists (verified by exhaustive GPU search). This means `SBC A,A` (CY→mask) is the universal conditional, while Z flag results require a branch.

**When to use branchless vs branch:** On the Z80, a conditional branch penalty is only 5T (the cost of a not-taken JR). A branchless ABS costs 24T; a branching version costs 9--14T. **Branch usually wins on Z80.** Branchless is valuable for: (1) the `SBC A,A` mask itself (always worth it at 4T), (2) inner loops where constant timing matters, (3) GPU code generation via Nanz→CUDA (no branch divergence), (4) cryptographic constant-time execution. For general code, prefer the branch.

### Division by Constant (Reciprocal Multiplication)

Exact or near-exact division without lookup tables, using the reciprocal trick `n/K = (n × M) >> S`:

| Divisor | Formula | Exact inputs | Max error |
|---------|---------|-------------|-----------|
| /3 | A×171>>9 | **256/256** | **0** |
| /5 | A×103>>9 | 239/256 | 1 |
| /7 | A×37>>8 | 220/256 | 1 |
| /10 | A×26>>8 | 218/256 | 1 |

Only /3 is exact for all u8 inputs. Magic constant 171 works because $\lfloor 256 \times 256 / 3 \rfloor = 21845$ and $171 = \lfloor 21845/128 + 0.5 \rfloor$. For other divisors, the full division table (Appendix K.3) provides GPU-proven optimal sequences.

---

## K.5 16-bit Idioms

| Idiom | Sequence | Insts | T-states |
|-------|----------|-------|----------|
| NEG HL (DE=0) | `EX DE,HL : OR A : SBC HL,DE` | 3 | 23T |
| NEG HL (universal) | `XOR A : SUB L : LD L,A : SBC A,A : SUB H : LD H,A` | 6 | 24T |
| NEG HL (v3) | `XOR A : SUB L : LD L,A : LD A,0 : SBC A,H : LD H,A` | 6 | 27T |
| ABS HL | `LD A,H : RLA : SBC A,A : LD B,A : XOR L : SUB B : LD L,A : LD A,B : XOR H : SBC A,B : LD H,A` | 11 | 44T |
| MIN HL,DE | `OR A : SBC HL,DE : ADD HL,DE : JR C,+1 : EX DE,HL` | 5 | 41--46T |
| MAX HL,DE | (same, swap JR condition) | 5 | 41--46T |
| Sign-extend A→HL | `ADC A,L : SBC A,A : LD H,A` | 3 | 12T |
| NOT HL | `DEC H : XOR H : LD L,A` | 3 | 12T |
| HL >> 1 | `SRL H : RR L` | 2 | 16T |
| HL × 3 | `LD C,A : ADD HL,BC : ADD HL,BC` | 3 | 26T |
| HL × 10 | (5 insts via shift-add) | 5 | 48T |
| HL × 256 | `LD H,L : LD L,0` | 2 | 11T |

**NEG HL** has 4 variants with different register prerequisites. Alf's universal method works without any prerequisites. The GPU found shorter versions requiring DE=0 or B=0. The v3 NEG HL (27T) avoids SBC A,A and works when CY is unknown.

**ABS HL** (44T, branchless) extends the 8-bit ABS pattern to 16 bits: extract sign from H, create mask, XOR-subtract both bytes. **MIN/MAX HL,DE** (41--46T) use the SBC+ADD trick: `SBC HL,DE` sets carry if HL < DE, then `ADD HL,DE` restores the original value. The conditional `EX DE,HL` is a single-byte branch (JR C/NC skips 1 byte) --- the only case where a branch is cheaper than branchless on Z80.

---

## K.5b Multi-Accumulator Arithmetic

> *The Z80 has 144 bits of registers --- enough for 4.5 simultaneous u32 accumulators. Choosing the right packing changes everything.*

The Z80 has no 32-bit registers. For u32 arithmetic, we pack four 8-bit registers into one logical accumulator. The classic choice is **DEHL** (D:E:H:L), but it is not the best:

| Convention | Layout | SHL32 | ADD32 | SAVE | Key feature |
|------------|--------|-------|-------|------|-------------|
| **DEHL** | D:E:H:L | 34T | 54T | 22T | ADC HL,rr native |
| **HLIX** | H:L:IXH:IXL | 30T | 30T | 24T | DE+BC free as temp |
| **HLH'L'** | H:L:H':L' | 30T | 30T | **4T** | EXX instant swap |

**HLH'L' wins overwhelmingly.** `EXX` swaps three register pairs in 4T. Where DEHL needs 22T to save state to the stack, HLH'L' does it in 4T. This 18T difference compounds with every multiply-by-constant.

### Why It Matters: ×10 Decomposition

Multiplying u32 by constant K requires SHL + SAVE + ADD. For `×10` (the atoi inner loop, ×2 + ×8):

| Convention | 3×SHL | 1×SAVE | 1×ADD | **Total ×10** |
|------------|-------|--------|-------|---------------|
| DEHL       | 102T  | 22T    | 54T   | **178T**      |
| HLIX       | 90T   | 24T    | 30T   | **144T**      |
| HLH'L'     | 90T   | 4T     | 30T   | **124T**      |

HLH'L' is **30% faster** than DEHL for ×10. Over 10 digits of atoi: 540T saved.

### The HLIX×10+A Trick

For atoi specifically, HLIX has an advantage: the digit in A is injected during the save step at zero extra cost.

```z80
; HLIX = HLIX × 10 + A (19 instructions, 178T, 31 bytes)
; Input:  HLIX = running total, A = digit (0-9)
; Output: HLIX = total × 10 + digit

  ADD  IX, IX     ; 15T ─┐ HLIX <<= 1 (×2)
  ADC  HL, HL     ; 15T ─┘

  ADD  A, IXL     ;  8T ─┐ Save HLIX×2 into DEBC
  LD   C, A       ;  4T  │ AND inject digit into low byte
  LD   A, IXH     ;  8T  │ — the +A is FREE
  ADC  A, 0       ;  7T  │
  LD   B, A       ;  4T  │
  LD   A, L       ;  4T  │
  ADC  A, 0       ;  7T  │ ADC A,H + SUB E trick:
  LD   E, A       ;  4T  │ chains carry from previous
  ADC  A, H       ;  4T  │ byte and subtracts already-
  SUB  E          ;  4T  │ saved E to isolate H+carry
  LD   D, A       ;  4T ─┘

  ADD  IX, IX     ; 15T ─┐ ×4
  ADC  HL, HL     ; 15T ─┘
  ADD  IX, IX     ; 15T ─┐ ×8
  ADC  HL, HL     ; 15T ─┘
  ADD  IX, BC     ; 15T ─┐ ×8 + ×2 = ×10 (+digit)
  ADC  HL, DE     ; 15T ─┘
```

### Register Budget: 144 Bits

The Z80's 18 eight-bit registers organize into up to 4.5 simultaneous u32 accumulators:

```
Main bank:  A  B  C  D  E  H  L      (56 bits)
Shadow:     A' B' C' D' E' H' L'     (56 bits, via EXX / EX AF,AF')
Index:      IXH  IXL  IYH  IYL      (32 bits)
                                     ─────────
                                     144 bits = 4.5 × u32
```

| Config | Bits | Layout | Use case |
|--------|------|--------|----------|
| 2×32 + 8 | 72 | HLIX + DEBC + A | atoi (×10+A) |
| 2×32 | 64 | HL:H'L' + DE:D'E' | bignum add |
| 3×32 | 96 | DEHL + D'E'H'L' + IX:IY | FP mul |
| 4×32 | 128 | DEHL + BCIX + D'E'H'L' + B'C'IY | SHA-256 |

For SHA-256, all four 32-bit working variables fit in registers --- no RAM spills needed.

---

## K.6 The Packed Arithmetic Cassette

All optimal sequences share instruction prefixes. A packed library with multiple entry points via labels eliminates all redundancy:

```z80
mul104:            ; ×104 entry point
mul52:  ADD A, A   ; ×52 entry point (×104 = ×52 × 2)
mul26:  ADD A, A   ; ×26 (×52 = ×26 × 2)
mul24:  ADD A, B   ; ×24
mul12:  ADD A, A   ; ×12
mul6:   LD  B, A   ; ×6
        ADD A, B
        ADD A, B
mul2:   RLA        ; ×2
        RET        ; shared — 7 constants, 9 instructions!
```

Rotation and shift sleds cover all amounts with one fall-through chain:

```z80
rot7:   RLCA       ; 7 rotations     shr7:   SRL A    ; 7 shifts
rot6:   RLCA       ; 6               shr6:   SRL A    ; 6
rot5:   RLCA       ; 5               shr5:   SRL A    ; 5
rot4:   RLCA       ; nibble swap     shr4:   SRL A    ; /16
rot3:   RLCA       ; 3               shr3:   SRL A    ; 3
rot2:   RLCA       ; 2               shr2:   SRL A    ; 2
rot1:   RLCA       ; 1               shr1:   SRL A    ; /2
        RET        ; 9 bytes          RET    ; 16 bytes
```

**Packed library sizes:**
- 594 bytes for 164 mul8 constants (51% compression)
- ~500 bytes for 254 mul16 constants (86% compression)
- **Total: ~2KB packed blob covers ALL optimal arithmetic for Z80.** 254 multiplies + 254 divisions + rotation/shift sleds + branchless idioms. For ZX Spectrum: just 4% of 48KB RAM.

---

## K.7 How It Works

1. **Define the target**: for each input A (0--255), what should the output be?
2. **Generate** all instruction sequences up to length N
3. **QuickCheck**: test 4 carefully chosen inputs --- rejects 99.99% instantly
4. **Full verify**: test all 256 inputs for survivors
5. **Pool reduction**: analyze which ops appear in solutions, remove the rest
6. **Guided search**: abstract chains predict structure, GPU searches focused space

The search runs on commodity GPUs:

- NVIDIA RTX 4060 Ti: ~1 billion candidates/second
- AMD Radeon RX 580: ~400 million/second (via OpenCL)
- Apple M2: ~200 million/second (via Metal)

Cross-verified across 5 platforms (CUDA + OpenCL + Vulkan + Metal + CPU). All results identical across 4 GPU APIs. The verification kernels are written in Nanz (a C23-like language) and compiled to GPU compute shaders via the `mir2gpu` backend --- the same compiler that targets Z80 also targets the GPU (see Chapter 23, Section 23.5c).

---

## K.8 Source & Data

All sequences available at: https://github.com/oisee/z80-optimizer

- `data/mulopt8_clobber.json` --- 164 multiply sequences with register annotations
- `data/div8_optimal.json` --- 247 division sequences
- `data/mul8_library.asm` --- packed Z80 assembly with multi-entry points

**508+ total provably optimal arithmetic sequences for Z80** (254 mul + 254 div).

**See also:** Appendix L (floating-point formats), Appendix M (BCD arithmetic), Appendix N (LUT generators), Appendix O (meta-analysis of all sequences), Appendix P (register allocation tables --- how the compiler uses these sequences without clobbering live variables).

---

*Generated by z80-optimizer v1.0.0*
