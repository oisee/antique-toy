# Appendix K: GPU Superoptimization — When Brute Force Beats Human Intuition

> *Dark wrote the fastest general multiply in 1997. In 2026, GPU brute-force proved 
> what's optimal for each specific constant — and it's 10× faster.*

## Overview

A superoptimizer tries every possible instruction sequence to find the provably 
shortest/fastest one. On GPU, this becomes practical: testing billions of 
candidates per second on commodity hardware.

## Method 3: GPU Brute-Force Constant Multiply

Dark's Method 1 (shift-and-add loop): **196-204T** for any 8-bit multiply.
GPU-optimal for specific constants:

| Constant | GPU-Optimal Sequence | T-states | vs Dark's loop |
|----------|---------------------|----------|----------------|
| ×2  | `RLA` | 4T | **50×** faster |
| ×3  | `LD B,A : ADC A,A : ADD A,B` | 12T | **16×** |
| ×10 | `RLA : LD B,A : ADD A,B : ADD A,A : ADD A,B` | 20T | **10×** |
| ×42 | `RLA : LD B,A : ... (8 insts)` | 32T | **6×** |
| ×128| `RRCA : SBC A,A : ADC A,B : RRA` | 16T | **12×** |
| ×255| `NEG` | 8T | **25×** |

**Average: 8× faster than the general loop for constant K.**

254/254 constants have GPU-proven optimal sequences. The surprising finding:
only 7 of 14 instruction types actually appear in any optimal solution.
The others (SLA A, RLC A, etc.) are strictly dominated by faster alternatives.

## The Division Breakthrough

Division by constant K on Z80 has no hardware support. The GPU found that
the reciprocal multiplication trick produces optimal sequences automatically:

`n / K = (n × M) >> S` where M ≈ 2^S / K

| Divisor | Sequence | T-states | vs general loop (280T) |
|---------|----------|----------|------------------------|
| /3  | 14 insts (reciprocal ×171 chain) | 130T | 2.2× |
| /10 | 14 insts (reciprocal ×205 chain) | 124T | 2.3× |
| /50 | 10 insts | 80T | 3.5× |
| /100| 9 insts | 105T | 2.7× |

244/247 divisors (3-255) (3-127) solved. div10 = 124T matches the famous
Hacker's Delight hand-optimized sequence — found automatically by GPU.

## Branchless Idioms

The GPU also discovered branchless implementations of common operations:

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

The key trick: `SBC A,A` converts the carry flag into a full byte mask
(0x00 or 0xFF). Combined with `RLCA` (sign bit → carry), this enables
instant sign detection without any conditional jumps.

## The Packed Arithmetic Cassette

All optimal sequences share instruction prefixes. A packed library with
multiple entry points via labels eliminates all redundancy:

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

Similarly, rotation/shift sleds cover all amounts with one fall-through chain:

```z80
rot7:   RLCA       ; 7 rotations
rot6:   RLCA       ; 6
rot5:   RLCA       ; 5
rot4:   RLCA       ; nibble swap! (4 rotations)
rot3:   RLCA       ; 3
rot2:   RLCA       ; 2
rot1:   RLCA       ; 1
        RET        ; 9 bytes, 7 entry points
```

**Total: ~2KB packed blob covers ALL optimal arithmetic for Z80.**
254 multiplies + 118 divisions + rotation/shift sleds.
For ZX Spectrum: just 4% of 48KB RAM.

## How It Works

1. Define the target: for each input A (0-255), what should the output be?
2. Generate all instruction sequences up to length N
3. QuickCheck: test 4 carefully chosen inputs — rejects 99.99% instantly
4. Full verify: test all 256 inputs for survivors
5. Pool reduction: analyze which ops appear in solutions, remove the rest
6. Guided search: abstract chains predict structure, GPU searches focused space

The search runs on commodity GPUs:
- NVIDIA RTX 4060 Ti: ~1 billion candidates/second
- AMD Radeon RX 580: ~400 million/second (via OpenCL)
- Apple M2: ~200 million/second (via Metal)

Cross-verified across 5 platforms (CUDA + OpenCL + Vulkan + Metal + CPU).

## Source & Tables

All sequences: https://github.com/oisee/z80-optimizer
- `data/mulopt8_clobber.json` — 164 multiply sequences with register annotations
- `data/div8_optimal.json` — 118 division sequences
- `data/mul8_library.asm` — packed Z80 assembly with entry points
- Full details: `docs/findings_for_antique_toy.md`

## Updated Division Table (244/247 divisors)

| Divisor | Insts | T-states | vs loop (280T) |
|---------|-------|----------|----------------|
| /3 | 14 | 130T | 2.2× |
| /5 | 14 | 127T | 2.2× |
| /6 | 13 | 131T | 2.1× |
| /7 | 14 | 123T | 2.3× |
| /9 | 11 | 97T | 2.9× |
| /10 | 14 | 124T | 2.3× |
| /12 | 12 | 120T | 2.3× |
| /13 | 14 | 120T | 2.3× |
| /15 | 12 | 102T | 2.7× |
| /19 | 10 | 86T | 3.3× |
| /20 | 13 | 133T | 2.1× |
| /24 | 12 | 102T | 2.7× |
| /25 | 10 | 83T | 3.4× |
| /30 | 11 | 98T | 2.9× |
| /40 | 12 | 114T | 2.5× |
| /50 | 10 | 80T | 3.5× |
| /57 | 6 | 49T | 5.7× |
| /60 | 11 | 95T | 2.9× |
| /100 | 9 | 105T | 2.7× |
| /114 | 6 | 46T | 6.1× |
| /171 | 4 | 27T | 10.4× |
| /205 | 5 | 35T | 8.0× |
| /255 | 6 | 50T | 5.6× |

**Total: 244 divisors, avg 107T**
**Fastest: div171 = 4 insts, 27T (10.4× vs loop)**
**Missing: div11, div43, div129 (need sequence length > 15)**
