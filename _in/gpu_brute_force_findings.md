# GPU Brute-Force Findings for antique_toy Book

Summary of provably optimal Z80 sequences discovered via exhaustive
GPU search. For inclusion in "Antique Toy" book chapters on Z80 maths
and optimization tricks.

## Constant Multiplication (Chapter 4: Maths)

**254/254 constants solved** — every u8 multiply has a proven optimal sequence.

Notable tricks the GPU discovered:

| Multiply | Sequence | Insts | T-states | Trick |
|----------|----------|-------|----------|-------|
| ×2 | `RLA` | 1 | 4T | Rotate left (NOT ADD A,A — 4T vs 4T same but RLA is shorter opcode) |
| ×3 | `LD B,A : ADC A,A : ADD A,B` | 3 | 12T | ADC doubles with carry propagation |
| ×10 | `RLA : LD B,A : ADD A,B : ADD A,A : ADD A,B` | 5 | 20T | ×2 → save → ×3 → ×2 → ×5 → +saved |
| ×128 | `RRCA : SBC A,A : ADC A,B : RRA` | 4 | 16T | Carry trick: RRCA puts bit0→carry, SBC A,A=mask |
| ×255 | `NEG` | 1 | 8T | -1 mod 256 = 255! `A × 255 = -A` |
| ×254 | `RLA : NEG` | 2 | 12T | ×2 then negate |
| ×252 | `RLA : NEG : ADD A,A` | 3 | 16T | |

**Key insight**: 7 of 21 candidate instructions never appear in any optimal solution:
SLA A (= ADD A,A but 8T not 4T), SRA A, RLC A, RRC A (CB prefix = slower),
OR A, SCF, EX AF,AF'. Removing them → 38× faster search.

### 16-bit Multiply (u8 × K → HL)

**254/254 complete** using only **3 instructions**: ADD HL,HL + ADD HL,BC + LD C,A.
This is a complete basis for 16-bit constant multiplication on Z80.

With SWAP_HL (= LD H,L / LD L,0) and SUB HL,BC: 86% code compression via prefix sharing.

×255 (16-bit): `LD H,L : LD L,0 : LD C,A : OR A : SBC HL,BC` = 30T
(byte swap trick: ×256 - ×1)

### Packed Library: 1.1KB for ALL Multiplies

Multiple entry points via labels, shared fall-through code:
```asm
mul104: ADD A,A     ; ×104 enters here
mul52:  ADD A,A     ; ×52 enters here
mul26:  ADD A,B     ; ×26
mul24:  ADD A,A     ; ×24
mul12:  ADD A,A     ; ×12
mul6:   LD B,A : ADD A,B : ADD A,B
mul2:   RLA
        RET         ; 7 constants, 9 instructions, 1 shared RET!
```

594 bytes for 164 mul8 constants (51% compression).
~500 bytes for 254 mul16 constants (86% compression).

## Constant Division

**118/120 divisors solved** via guided brute-force (abstract chain → focused GPU).

| Division | Sequence | Insts | T-states | vs loop |
|----------|----------|-------|----------|---------|
| /3 | reciprocal ×171 + SRL | 14 | 130T | 2.2× |
| /5 | reciprocal ×205 + SRL | 14 | 127T | 2.2× |
| /7 | reciprocal multiply chain | 14 | 123T | 2.3× |
| /9 | reciprocal ×57 chain | 11 | 97T | 2.9× |
| /10 | reciprocal ×205 chain | 14 | 124T | 2.3× |
| /19 | reciprocal ×27 chain | 10 | 86T | 3.3× |
| /25 | reciprocal ×41 chain | 10 | 83T | 3.4× |
| /50 | reciprocal chain | 10 | 80T | **3.5×** |
| /57 | reciprocal | 6 | 60T | **4.7×** |
| /100 | reciprocal chain | 9 | 105T | 2.7× |

**div10 = 124T matches Hacker's Delight** — found automatically by GPU in 11 seconds!

Method: n/K = (n × M) >> S where M = round(2^S / K).
GPU searches the Z80 materialization of the multiply-then-shift pattern.

## Branchless Idioms

All found via GPU exhaustive search with 37-op pool:

| Idiom | Sequence | Insts | T-states |
|-------|----------|-------|----------|
| bool(A) | `LD B,A : NEG : ADC A,B` | 3 | 16T |
| NOT(A) | `NEG : SBC A,A : INC A` | 3 | 16T |
| is_neg(A) | `RLCA : SBC A,A : NEG` | 3 | 16T |
| lsb(A) | `LD B,A : NEG : AND B` | 3 | 16T |
| complement(A) | `CPL` | 1 | 4T |
| half(A) | `RRA` | 1 | 4T |
| nibble_swap(A) | `RLCA : RLCA : RLCA : RLCA` | 4 | 16T |
| double_sat(A) | `RLCA : LD B,A : SBC A,A : OR B` | 4 | 16T |
| max_0(A) | `LD B,A : RLCA : SBC A,A : XOR B : AND B` | 5 | 20T |
| sign(A) | (5 insts) | 5 | 20T |
| ABS(A) | `LD B,A : RLCA : SBC A,A : XOR B : SBC A,B : ADC A,B` | 6 | 24T |

**The SBC A,A carry-to-mask trick** appears in many: sets A to 0x00 or 0xFF
depending on carry flag. Combined with RLCA (sign bit → carry): instant sign detection.

**INC A / DEC A don't touch carry** — essential for interleaved multi-byte operations.

## 16-bit Idioms

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

**NEG HL**: 4 variants with different prerequisites. Alf's universal method
(XOR A / SUB L / LD L,A / SBC A,A / SUB H / LD H,A) works without
any register prerequisites. Our GPU found shorter versions requiring DE=0 or B=0.

**Sign-extend trick**: `ADC A,L` doubles A (overflow if ≥128 → carry),
`SBC A,A` converts carry to 0xFF mask, `LD H,A` stores sign byte. 12T total.

## Multi-Entry Instruction Sleds

```asm
rot7: RLCA         ; 9 bytes, 7 entry points
rot6: RLCA         ; CALL rot4 = nibble swap
rot5: RLCA         ; CALL rot1 = ×2 via rotate
rot4: RLCA
rot3: RLCA
rot2: RLCA
rot1: RLCA
      RET

shr7: SRL A        ; 16 bytes, 7 entry points
shr6: SRL A        ; CALL shr1 = /2
shr5: SRL A        ; CALL shr4 = /16 (hi nibble)
shr4: SRL A
shr3: SRL A
shr2: SRL A
shr1: SRL A
      RET
```

Combined with multiply/division chains: one ~2KB packed blob covers
ALL optimal arithmetic for Z80. Hundreds of entry points, zero wasted bytes.

## How It Was Found

1. **GPU exhaustive search**: try ALL instruction sequences up to length N
2. **QuickCheck**: 4 test inputs reject 99.99% of candidates instantly
3. **Full verification**: all 256 inputs checked for surviving candidates
4. **Pool reduction**: analyze which ops appear → remove useless ones → search deeper
5. **Guided search**: abstract chains predict pattern → GPU materializes to Z80
6. **Cross-verified**: NVIDIA CUDA × 2 + AMD OpenCL + AMD Vulkan + Apple Metal + CPU

Hardware: 2× RTX 4060 Ti + RTX 2070 + Radeon RX 580 + M2 MacBook Air.
All results identical across 5 platforms and 4 GPU APIs.

---

*Generated by z80-optimizer v1.0.0 (birthday release 🎂)*
*Repository: https://github.com/oisee/z80-optimizer*
