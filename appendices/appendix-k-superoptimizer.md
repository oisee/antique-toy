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

**247/247 divisors solved** (3--255). COMPLETE --- zero gaps. Every u8 division has a proven optimal sequence.

| Divisor | Insts | T-states | vs general loop (280T) |
|---------|-------|----------|------------------------|
| /3  | 14 | 130T | 2.2× |
| /5  | 14 | 127T | 2.2× |
| /7  | 14 | 123T | 2.3× |
| /9  | 11 | 97T | 2.9× |
| /10 | 14 | 124T | 2.3× |
| /15 | 12 | 102T | 2.7× |
| /19 | 10 | 86T | 3.3× |
| /25 | 10 | 83T | 3.4× |
| /50 | 10 | 80T | 3.5× |
| /57 | 6 | 49T | 5.7× |
| /100 | 9 | 105T | 2.7× |
| /114 | 6 | 46T | 6.1× |
| /171 | 4 | 27T | **10.4×** |
| /205 | 5 | 35T | 8.0× |
| /255 | 6 | 50T | 5.6× |

**Total: 247/247 divisors --- COMPLETE. Average 107T. Fastest: div171 = 4 instructions, 27T (10.4× vs loop).** `div10 = 124T` matches the famous Hacker's Delight hand-optimized sequence --- found automatically by GPU in 11 seconds. Last solved: div129 = 16 instructions, 160T.

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
```

---

## K.5 16-bit Idioms

| Idiom | Sequence | Insts | T-states |
|-------|----------|-------|----------|
| NEG HL (DE=0) | `EX DE,HL : OR A : SBC HL,DE` | 3 | 23T |
| NEG HL (universal) | `XOR A : SUB L : LD L,A : SBC A,A : SUB H : LD H,A` | 6 | 24T |
| Sign-extend A→HL | `ADC A,L : SBC A,A : LD H,A` | 3 | 12T |
| NOT HL | `DEC H : XOR H : LD L,A` | 3 | 12T |
| HL >> 1 | `SRL H : RR L` | 2 | 16T |
| HL × 3 | `LD C,A : ADD HL,BC : ADD HL,BC` | 3 | 26T |
| HL × 10 | (5 insts via shift-add) | 5 | 48T |
| HL × 256 | `LD H,L : LD L,0` | 2 | 11T |

**NEG HL** has 4 variants with different register prerequisites. Alf's universal method works without any prerequisites. The GPU found shorter versions requiring DE=0 or B=0.

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
- **Total: ~2KB packed blob covers ALL optimal arithmetic for Z80.** 254 multiplies + 247 divisions + rotation/shift sleds. For ZX Spectrum: just 4% of 48KB RAM.

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

**501 total provably optimal arithmetic sequences for Z80.**

**See also:** Appendix L (floating-point formats), Appendix M (BCD arithmetic), Appendix N (LUT generators), Appendix O (meta-analysis of all sequences).

---

*Generated by z80-optimizer v1.0.0*
