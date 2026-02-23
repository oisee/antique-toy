# Appendix A: Z80 Instruction Quick Reference

> *"An instruction that should take 7 T-states might take 13 if it lands on the worst phase of the contention cycle."*
> -- Chapter 1

This is not a complete Z80 manual. It is a reference card for demoscene and game programmers on ZX Spectrum and Agon Light 2 -- the instructions you actually use, the timings you need to know by heart, and the patterns that save T-states in inner loops.

All T-state counts assume **Pentagon timing** (no contention). Byte counts are the instruction encoding length. Flag columns show: **S** (sign), **Z** (zero), **H** (half-carry), **P/V** (parity/overflow), **N** (subtract), **C** (carry). A dash means unchanged; a dot means undefined.

---

## 8-Bit Load Instructions

| Instruction | Bytes | T-states | Flags | Notes |
|-------------|-------|----------|-------|-------|
| `LD r,r'` | 1 | 4 | ------ | Fastest instruction. r,r' = A,B,C,D,E,H,L |
| `LD r,n` | 2 | 7 | ------ | Immediate load |
| `LD r,(HL)` | 1 | 7 | ------ | Memory read via HL |
| `LD (HL),r` | 1 | 7 | ------ | Memory write via HL |
| `LD (HL),n` | 2 | 10 | ------ | Immediate to memory |
| `LD A,(BC)` | 1 | 7 | ------ | |
| `LD A,(DE)` | 1 | 7 | ------ | |
| `LD (BC),A` | 1 | 7 | ------ | |
| `LD (DE),A` | 1 | 7 | ------ | |
| `LD A,(nn)` | 3 | 13 | ------ | Absolute address |
| `LD (nn),A` | 3 | 13 | ------ | Absolute address |
| `LD r,(IX+d)` | 3 | 19 | ------ | Indexed. Expensive -- avoid in inner loops |
| `LD (IX+d),r` | 3 | 19 | ------ | Indexed |
| `LD (IX+d),n` | 4 | 23 | ------ | Indexed immediate |
| `LD A,I` | 2 | 9 | SZ0P0- | P/V = IFF2 |
| `LD A,R` | 2 | 9 | SZ0P0- | P/V = IFF2; R = refresh counter |

---

## 16-Bit Load Instructions

| Instruction | Bytes | T-states | Flags | Notes |
|-------------|-------|----------|-------|-------|
| `LD rr,nn` | 3 | 10 | ------ | rr = BC, DE, HL, SP |
| `LD HL,(nn)` | 3 | 16 | ------ | |
| `LD (nn),HL` | 3 | 16 | ------ | |
| `LD rr,(nn)` | 4 | 20 | ------ | rr = BC, DE, SP (ED prefix) |
| `LD (nn),rr` | 4 | 20 | ------ | rr = BC, DE, SP (ED prefix) |
| `LD SP,HL` | 1 | 6 | ------ | Set up stack pointer |
| `LD SP,IX` | 2 | 10 | ------ | |
| `PUSH rr` | 1 | 11 | ------ | rr = AF, BC, DE, HL. **5.5T per byte** |
| `POP rr` | 1 | 10 | ------ | **5T per byte** -- fastest 2-byte read |
| `PUSH IX` | 2 | 15 | ------ | |
| `POP IX` | 2 | 14 | ------ | |

---

## 8-Bit Arithmetic and Logic

| Instruction | Bytes | T-states | Flags | Notes |
|-------------|-------|----------|-------|-------|
| `ADD A,r` | 1 | 4 | SZ.V0C | |
| `ADD A,n` | 2 | 7 | SZ.V0C | |
| `ADD A,(HL)` | 1 | 7 | SZ.V0C | |
| `ADC A,r` | 1 | 4 | SZ.V0C | Add with carry |
| `ADC A,n` | 2 | 7 | SZ.V0C | |
| `SUB r` | 1 | 4 | SZ.V1C | |
| `SUB n` | 2 | 7 | SZ.V1C | |
| `SUB (HL)` | 1 | 7 | SZ.V1C | |
| `SBC A,r` | 1 | 4 | SZ.V1C | Subtract with carry |
| `CP r` | 1 | 4 | SZ.V1C | Compare (SUB without storing result) |
| `CP n` | 2 | 7 | SZ.V1C | |
| `CP (HL)` | 1 | 7 | SZ.V1C | |
| `AND r` | 1 | 4 | SZ1P00 | H always set, C always cleared |
| `AND n` | 2 | 7 | SZ1P00 | |
| `OR r` | 1 | 4 | SZ0P00 | Clears H and C |
| `OR n` | 2 | 7 | SZ0P00 | |
| `XOR r` | 1 | 4 | SZ0P00 | `XOR A` = zero A in 4T/1B (vs `LD A,0` = 7T/2B) |
| `XOR n` | 2 | 7 | SZ0P00 | |
| `INC r` | 1 | 4 | SZ.V0- | Does **not** affect carry |
| `DEC r` | 1 | 4 | SZ.V1- | Does **not** affect carry |
| `INC (HL)` | 1 | 11 | SZ.V0- | Read-modify-write |
| `DEC (HL)` | 1 | 11 | SZ.V1- | Read-modify-write |
| `NEG` | 2 | 8 | SZ.V1C | A = 0 - A (two's complement negate) |
| `DAA` | 1 | 4 | SZ.P-C | BCD adjust -- rarely used in demos |
| `CPL` | 1 | 4 | --1-1- | A = NOT A (one's complement) |
| `SCF` | 1 | 4 | --0-00 | Set carry flag. N,H cleared. New behaviour on CMOS |
| `CCF` | 1 | 4 | --.-0. | Complement carry. H = old C |

---

## 16-Bit Arithmetic

| Instruction | Bytes | T-states | Flags | Notes |
|-------------|-------|----------|-------|-------|
| `ADD HL,rr` | 1 | 11 | --.?0C | rr = BC, DE, HL, SP. Only affects H, N, C |
| `ADC HL,rr` | 2 | 15 | SZ.V0C | Full flag set |
| `SBC HL,rr` | 2 | 15 | SZ.V1C | Full flag set |
| `INC rr` | 1 | 6 | ------ | No flags affected |
| `DEC rr` | 1 | 6 | ------ | No flags affected |
| `ADD IX,rr` | 2 | 15 | --.?0C | rr = BC, DE, IX, SP |

**Key point:** `INC rr` and `DEC rr` do **not** set the zero flag. You cannot use `DEC BC / JR NZ` as a 16-bit loop counter. Use `DEC B / JR NZ` for 8-bit loops with `DJNZ`, or test BC explicitly.

---

## Rotate and Shift

| Instruction | Bytes | T-states | Flags | Notes |
|-------------|-------|----------|-------|-------|
| `RLCA` | 1 | 4 | --0-0C | Rotate A left, bit 7 to carry and bit 0 |
| `RRCA` | 1 | 4 | --0-0C | Rotate A right, bit 0 to carry and bit 7 |
| `RLA` | 1 | 4 | --0-0C | Rotate A left through carry |
| `RRA` | 1 | 4 | --0-0C | Rotate A right through carry. **Key for multiply loops** |
| `RLC r` | 2 | 8 | SZ0P0C | CB-prefix. Full flag set |
| `RRC r` | 2 | 8 | SZ0P0C | |
| `RL r` | 2 | 8 | SZ0P0C | Rotate left through carry |
| `RR r` | 2 | 8 | SZ0P0C | Rotate right through carry |
| `SLA r` | 2 | 8 | SZ0P0C | Shift left arithmetic. Bit 0 = 0 |
| `SRA r` | 2 | 8 | SZ0P0C | Shift right arithmetic. Bit 7 preserved (sign extend) |
| `SRL r` | 2 | 8 | SZ0P0C | Shift right logical. Bit 7 = 0 |
| `RLC (HL)` | 2 | 15 | SZ0P0C | Read-modify-write |
| `RL (HL)` | 2 | 15 | SZ0P0C | Scroll pixel data left |
| `RR (HL)` | 2 | 15 | SZ0P0C | Scroll pixel data right |
| `SLA (HL)` | 2 | 15 | SZ0P0C | |
| `SRL (HL)` | 2 | 15 | SZ0P0C | |
| `RLD` | 2 | 18 | SZ0P0- | Rotate (HL) nibbles left through A. Useful for nybble graphics |
| `RRD` | 2 | 18 | SZ0P0- | Rotate (HL) nibbles right through A |

**Demoscene note:** `RLA`/`RRA` (4T, 1 byte) only affect carry and bits 3,5 of F. The CB-prefix versions `RL r`/`RR r` (8T, 2 bytes) set all flags. In multiply loops, the accumulator versions save half the cost.

---

## Bit Manipulation

| Instruction | Bytes | T-states | Flags | Notes |
|-------------|-------|----------|-------|-------|
| `BIT b,r` | 2 | 8 | .Z1.0- | Test bit b of register |
| `BIT b,(HL)` | 2 | 12 | .Z1.0- | Test bit b of memory |
| `SET b,r` | 2 | 8 | ------ | Set bit b of register |
| `SET b,(HL)` | 2 | 15 | ------ | Set bit b of memory. **Used in line drawing** |
| `RES b,r` | 2 | 8 | ------ | Reset bit b of register |
| `RES b,(HL)` | 2 | 15 | ------ | Reset bit b of memory |

---

## Jump, Call, Return

| Instruction | Bytes | T-states | Flags | Notes |
|-------------|-------|----------|-------|-------|
| `JP nn` | 3 | 10 | ------ | Absolute jump |
| `JP cc,nn` | 3 | 10 | ------ | Conditional: NZ, Z, NC, C, PO, PE, P, M. **Same speed taken or not** |
| `JR e` | 2 | 12 | ------ | Relative jump (-128 to +127) |
| `JR cc,e` | 2 | 12/7 | ------ | cc = NZ, Z, NC, C only. **7T if not taken** |
| `JP (HL)` | 1 | 4 | ------ | Jump to address in HL. Fastest indirect jump |
| `JP (IX)` | 2 | 8 | ------ | Jump to address in IX |
| `DJNZ e` | 2 | 13/8 | ------ | Dec B, jump if NZ. **13T taken, 8T not taken** |
| `CALL nn` | 3 | 17 | ------ | Push PC, jump to nn |
| `CALL cc,nn` | 3 | 17/10 | ------ | 10T if not taken |
| `RET` | 1 | 10 | ------ | Pop PC. **Used for RET-chaining dispatch** |
| `RET cc` | 1 | 11/5 | ------ | 5T if not taken |
| `RST p` | 1 | 11 | ------ | Call to $00,$08,$10,$18,$20,$28,$30,$38 |

**Key comparisons for dispatch:**

| Method | T-states | Bytes |
|--------|----------|-------|
| `CALL nn` | 17 | 3 |
| `RET` (as dispatch in RET-chain) | 10 | 1 |
| `JP (HL)` | 4 | 1 |
| `JP nn` | 10 | 3 |

---

## I/O Instructions

| Instruction | Bytes | T-states | Flags | Notes |
|-------------|-------|----------|-------|-------|
| `OUT (n),A` | 2 | 11 | ------ | Port address = `(A << 8) | n`. Border: `OUT ($FE),A` |
| `IN A,(n)` | 2 | 11 | ------ | Port address = `(A << 8) | n`. Keyboard: `IN A,($FE)` |
| `OUT (C),r` | 2 | 12 | ------ | Port address = BC. **AY register write** |
| `IN r,(C)` | 2 | 12 | SZ0P0- | Port address = BC. Sets flags |
| `OUTI` | 2 | 16 | .Z..1. | Out (HL) to port (C), inc HL, dec B |
| `OTIR` | 2 | 21/16 | 01..1. | Repeat OUTI until B=0. 16T on last |
| `OUTD` | 2 | 16 | .Z..1. | Out (HL) to port (C), inc HL, dec B |

**AY-3-8910 port addresses on ZX Spectrum 128K:**

| Port | Address | Purpose |
|------|---------|---------|
| Register select | `$FFFD` | `LD BC,$FFFD : OUT (C),A` |
| Data write | `$BFFD` | `LD B,$BF : OUT (C),r` |
| Data read | `$FFFD` | `IN A,(C)` |

Typical AY register write sequence (24T + overhead):

```z80
    ld   bc, $FFFD      ; 10T  AY register select port
    out  (c), a          ; 12T  select register number (in A)
    ld   b, $BF          ;  7T  switch to data port $BFFD
    out  (c), e          ; 12T  write value (in E)
                         ; --- 41T total
```

---

## Block Instructions

| Instruction | Bytes | T-states | Flags | Notes |
|-------------|-------|----------|-------|-------|
| `LDI` | 2 | 16 | --0.0- | (DE) = (HL), inc HL, inc DE, dec BC. P/V = (BC != 0) |
| `LDIR` | 2 | 21/16 | --000- | Repeat LDI. 21T per byte, 16T last byte |
| `LDD` | 2 | 16 | --0.0- | (DE) = (HL), dec HL, dec DE, dec BC |
| `LDDR` | 2 | 21/16 | --000- | Repeat LDD. 21T per byte, 16T last byte |
| `CPI` | 2 | 16 | SZ.?1- | Compare A with (HL), inc HL, dec BC |
| `CPIR` | 2 | 21/16 | SZ.?1- | Repeat CPI. Stops when match or BC=0 |
| `CPD` | 2 | 16 | SZ.?1- | Compare A with (HL), dec HL, dec BC |
| `CPDR` | 2 | 21/16 | SZ.?1- | Repeat CPD |

**LDI vs LDIR per-byte cost:**

| Method | Per byte | 256 bytes | 32 bytes | Savings |
|--------|----------|-----------|----------|---------|
| LDIR | 21T (16T last) | 5,371T | 672T | -- |
| LDI chain | 16T | 4,096T | 512T | 24% faster |

An unrolled LDI chain costs 2 bytes per LDI (`$ED $A0`), but saves 5T per byte -- 24% faster than LDIR. See Chapter 3 for entry-point arithmetic with LDI chains.

---

## Exchange and Misc

| Instruction | Bytes | T-states | Flags | Notes |
|-------------|-------|----------|-------|-------|
| `EX DE,HL` | 1 | 4 | ------ | Swap DE and HL. **Free pointer swap** |
| `EX AF,AF'` | 1 | 4 | ------ | Swap AF with shadow AF' |
| `EXX` | 1 | 4 | ------ | Swap BC,DE,HL with BC',DE',HL'. **6 registers in 4T** |
| `EX (SP),HL` | 1 | 19 | ------ | Swap HL with top of stack. Useful for parameter passing |
| `EX (SP),IX` | 2 | 23 | ------ | Swap IX with top of stack |
| `DI` | 1 | 4 | ------ | Disable interrupts. **Required before stack tricks** |
| `EI` | 1 | 4 | ------ | Enable interrupts. Delayed one instruction |
| `HALT` | 1 | 4+ | ------ | Wait for interrupt. The frame sync instruction |
| `NOP` | 1 | 4 | ------ | Padding, timing |
| `IM 1` | 2 | 8 | ------ | Interrupt mode 1 (RST $38). Standard Spectrum mode |
| `IM 2` | 2 | 8 | ------ | Interrupt mode 2. Uses I register as vector table high byte |

---

## The Demoscene "Fast" Instructions

These are the cheapest instructions per category -- the building blocks of every optimised inner loop.

### Fastest Register-to-Register Move

`LD r,r'` -- **4T, 1 byte**. The minimum cost of any Z80 instruction. Includes `LD A,A` (effectively a NOP that does not affect flags).

### Fastest Way to Zero a Register

`XOR A` -- **4T, 1 byte**. Sets A to zero, sets Z flag, clears carry. Compare with `LD A,0` at 7T/2 bytes. Always use `XOR A` unless you need flags preserved.

### Fastest Memory Read

`LD A,(HL)` -- **7T, 1 byte**. The minimum cost for any memory read. Other register sources (`LD A,(BC)`, `LD A,(DE)`) are also 7T/1 byte, but HL is the only pointer that supports `LD r,(HL)` for all registers.

### Fastest Memory Write

`LD (HL),r` -- **7T, 1 byte**. Tied with read. Writing to a BC or DE pointer (`LD (BC),A`, `LD (DE),A`) is also 7T/1B but only works with A.

### Fastest 2-Byte Write

`PUSH rr` -- **11T, 1 byte** for 2 bytes = **5.5T per byte**. The fastest way to write data to memory, but only to where SP points (downward). Requires DI and hijacking the stack pointer. See Chapter 3.

### Fastest 2-Byte Read

`POP rr` -- **10T, 1 byte** for 2 bytes = **5T per byte**. Even faster than PUSH for reading. Use with SP pointing at a data table for ultra-fast lookups.

### Fastest Block Copy

| Method | Per byte | Notes |
|--------|----------|-------|
| `PUSH/POP` pair | 5.25T | Write: 5.5T, Read: 5T. But needs SP hijack |
| `LDI` (unrolled chain) | 16T | No setup per byte. 24% faster than LDIR |
| `LDIR` | 21T | Single instruction, but slow per byte |
| `LD (HL),r` + `INC HL` | 13T | Manual loop body (no loop counter) |
| `LD (HL),r` + `INC L` | 11T | Only works within 256-byte page |

### Fastest I/O

`OUT (n),A` -- **11T, 2 bytes**. For fixed port addresses (border, etc.). For variable ports (AY), `OUT (C),r` at 12T/2 bytes is the only option.

### Fastest Pointer Swap

`EX DE,HL` -- **4T, 1 byte**. Exchange DE and HL contents instantly. No other register swap is this cheap. `EXX` also 4T/1 byte but swaps all three pairs at once.

### Fastest Conditional Loop

`DJNZ e` -- **13T taken, 8T not taken, 2 bytes**. Decrements B and jumps. Compare with `DEC B / JR NZ,e` at 4+12 = 16T/3 bytes. DJNZ saves 3T and 1 byte per iteration.

### Fastest Indirect Jump

`JP (HL)` -- **4T, 1 byte**. Jumps to the address in HL. Despite the misleading mnemonic, this does NOT read from memory at (HL) -- it loads PC with the value of HL. Indispensable for jump tables and computed gotos.

---

## Undocumented Instructions

These instructions are not in the official Zilog documentation but work reliably on all Z80 silicon (NMOS and CMOS), all ZX Spectrum clones, and the eZ80. They are widely used in demoscene code and supported by sjasmplus.

### IXH, IXL, IYH, IYL (Half-Index Registers)

The IX and IY registers can be split into 8-bit halves, accessed by prefixing normal H/L instructions with DD/FD:

| Instruction | Bytes | T-states | Notes |
|-------------|-------|----------|-------|
| `LD A,IXH` | 2 | 8 | Read high byte of IX |
| `LD A,IXL` | 2 | 8 | Read low byte of IX |
| `LD IXH,A` | 2 | 8 | Write high byte of IX |
| `LD IXL,n` | 3 | 11 | Immediate into IX low |
| `ADD A,IXL` | 2 | 8 | Arithmetic with IX halves |
| `INC IXH` | 2 | 8 | Increment IX high byte |
| `DEC IXL` | 2 | 8 | Decrement IX low byte |

**Demoscene use:** Two extra 8-bit registers for counters, accumulators, or small values without touching the main register file. Particularly useful when BC/DE/HL are all occupied as pointers. Cost: 4T more than the equivalent main-register operation.

sjasmplus syntax: `IXH`, `IXL`, `IYH`, `IYL` (also accepts `HX`, `LX`, `HY`, `LY`).

### SLL r (Shift Left Logical)

| Instruction | Bytes | T-states | Notes |
|-------------|-------|----------|-------|
| `SLL r` | 2 | 8 | Shift left, bit 0 set to 1 (not 0) |
| `SLL (HL)` | 2 | 15 | Same for memory |

`SLL` shifts left and sets bit 0 to 1 (unlike `SLA` which sets bit 0 to 0). Opcode: CB 30+r. Occasionally useful for constructing bit patterns.

sjasmplus syntax: `SLL` or `SLI` or `SL1`.

### OUT (C),0

| Instruction | Bytes | T-states | Notes |
|-------------|-------|----------|-------|
| `OUT (C),0` | 2 | 12 | Output zero to port BC |

Opcode `ED 71`. Outputs zero to the port addressed by BC. On CMOS Z80s (including eZ80), this outputs $FF instead. **Not portable to Agon Light 2.** On NMOS Z80s (all real Spectrums), it outputs $00 reliably.

sjasmplus syntax: `OUT (C),0`.

### CB-Prefix Undocumented Bit Operations on (IX+d)

Instructions like `SET b,(IX+d),r` simultaneously perform a bit operation on memory at (IX+d) and copy the result into register r. These are 4-byte instructions (DD CB dd op) taking 23T. Occasionally useful but rarely critical.

---

## Flag Effects Cheat Sheet

Knowing which instructions set which flags lets you avoid redundant `CP` or `AND A` instructions -- a common source of wasted T-states.

### Instructions That Set All Arithmetic Flags (S, Z, H, P/V, N, C)

- `ADD A,r/n/(HL)` -- P/V = overflow
- `ADC A,r/n/(HL)` -- P/V = overflow
- `SUB r/n/(HL)` -- P/V = overflow
- `SBC A,r/n/(HL)` -- P/V = overflow
- `CP r/n/(HL)` -- Same flags as SUB but A unchanged
- `NEG` -- P/V = overflow
- `ADC HL,rr` -- P/V = overflow
- `SBC HL,rr` -- P/V = overflow

### Instructions That Set Z and S (but NOT Carry)

- `INC r` / `DEC r` -- C unchanged. **Cannot test carry after INC/DEC.**
- `INC (HL)` / `DEC (HL)` -- Same
- `AND r/n/(HL)` -- C always 0, H always 1
- `OR r/n/(HL)` -- C always 0, H always 0
- `XOR r/n/(HL)` -- C always 0, H always 0
- `IN r,(C)` -- C unchanged
- `BIT b,r/(HL)` -- Z = complement of tested bit, C unchanged
- All CB-prefix rotates/shifts -- Full flag set including C

### Instructions That Set ONLY Carry-Related Flags

- `ADD HL,rr` -- H and C only (S, Z, P/V unchanged)
- `RLCA` / `RRCA` / `RLA` / `RRA` -- C, H=0, N=0 only (S, Z, P/V unchanged)
- `SCF` -- C=1, H=0, N=0
- `CCF` -- C inverted, H = old C, N=0

### Instructions That Set NO Flags

- `LD` (all variants)
- `INC rr` / `DEC rr` (16-bit inc/dec)
- `PUSH` / `POP` (except POP AF restores flags)
- `EX` / `EXX`
- `DI` / `EI` / `HALT` / `NOP`
- `JP` / `JR` / `DJNZ` / `CALL` / `RET` / `RST`
- `OUT (n),A` / `IN A,(n)` (the non-CB versions)

### Practical Tricks

**Test A for zero without CP 0:**
```z80
    or   a              ; 4T  sets Z if A=0, clears C
    and  a              ; 4T  same effect, but also sets H
```

**Test carry after 16-bit INC/DEC:** You cannot. `INC rr`/`DEC rr` set no flags. To test if a 16-bit register reached zero:
```z80
    ld   a, b           ; 4T
    or   c              ; 4T  Z set if BC = 0
```

**Skip CP after SUB:** If you already performed `SUB r`, the flags are set -- do not follow it with `CP` or `OR A`.

**INC/DEC preserve carry:** Use `INC r`/`DEC r` between multi-precision arithmetic without destroying the carry chain.

---

## Register Architecture

### Main Register Set

```
  A   F          Accumulator + Flags
  B   C          Counter (B for DJNZ) + general
  D   E          General purpose pair
  H   L          Primary memory pointer (HL is the "accumulator pair")
```

### Special Registers

```
  SP             Stack pointer (16-bit)
  PC             Program counter (16-bit)
  IX             Index register (16-bit, DD prefix, +4T penalty)
  IY             Index register (16-bit, FD prefix, +4T penalty)
                 NOTE: IY is used by the Spectrum ROM interrupt handler.
                 Do not use IY unless you have DI or IM2 set up.
  I              Interrupt vector page (used in IM2)
  R              Refresh counter (7-bit, increments every M1 cycle)
```

### Shadow Registers

```
  A'  F'         Swapped with EX AF,AF'
  B'  C'         \
  D'  E'          | Swapped all three with EXX
  H'  L'         /
```

`EXX` swaps BC/DE/HL with BC'/DE'/HL' in **4T**. This gives you six extra 8-bit registers (or three extra 16-bit pairs) at virtually zero cost. Common use: keep pointers in the shadow set and swap in/out as needed.

**Warning:** The Spectrum ROM interrupt handler (IM1) uses the shadow registers. If interrupts are enabled, `EXX`/`EX AF,AF'` data will be corrupted on every interrupt. Always `DI` before using shadow registers, or switch to IM2 with your own handler.

### Register Pairing for Instructions

| Pair | Used by | Notes |
|------|---------|-------|
| BC | `DJNZ` (B only), `OUT (C),r`, `IN r,(C)`, block instructions (counter) | B = loop counter, C = port low byte |
| DE | `EX DE,HL`, `LDI`/`LDIR` (destination), `LD (DE),A` | Destination pointer for block ops |
| HL | Nearly everything: `LD r,(HL)`, `ADD HL,rr`, `JP (HL)`, `PUSH/POP`, `LDI` (source) | The universal pointer |
| AF | `PUSH AF`/`POP AF`, `EX AF,AF'` | A = accumulator, F = flags |
| SP | `PUSH`/`POP`, `LD SP,HL`, `EX (SP),HL` | Hijack for data tricks |

---

## Common Instruction Sequences

### Pixel Address Calculation (Screen Address from Y,X)

Convert screen coordinates to ZX Spectrum video memory address. Input: B = Y (0-191), C = X (0-255). Output: HL = screen byte address, A = bit mask.

```z80
; pixel_addr: calculate screen address from coordinates
; Input:  B = Y (0-191), C = X (0-255)
; Output: HL = byte address, A = pixel bit position
; Cost:   ~55 T-states
;
pixel_addr:
    ld   a, b           ; 4T   A = Y
    and  $07             ; 7T   scanline within char cell (SSS)
    or   $40             ; 7T   add screen base ($4000 high byte)
    ld   h, a           ; 4T   H = 010 00 SSS (partial)
    ld   a, b           ; 4T   A = Y again
    rra                 ; 4T   \
    rra                 ; 4T    | shift character row (TTRR RRR)
    rra                 ; 4T   /  to bits 4-3
    and  $18             ; 7T   mask TT (third bits)
    or   h              ; 4T   H = 010 TT SSS
    ld   h, a           ; 4T
    ld   a, c           ; 4T   A = X
    rra                 ; 4T   \
    rra                 ; 4T    | X / 8
    rra                 ; 4T   /
    and  $1F             ; 7T   mask to 5-bit column
    ld   l, a           ; 4T   L = 000 CCCCC
```

### DOWN_HL: Move One Pixel Row Down

The most-used graphics primitive on the Spectrum. Common case (within character cell) costs only 20T.

```z80
; down_hl: advance HL one pixel row down
; Input:  HL = screen address
; Output: HL = address one row below
; Cost:   20T (common), 46T (third boundary), 77T (char boundary)
;
down_hl:
    inc  h              ; 4T   try next scanline
    ld   a, h           ; 4T
    and  7              ; 7T   crossed character boundary?
    ret  nz             ; 5T   no: done (20T total)

    ld   a, l           ; 4T   yes: advance character row
    add  a, 32          ; 7T   L += 32
    ld   l, a           ; 4T
    ret  c              ; 5T   carry = crossed third (46T total)

    ld   a, h           ; 4T   same third: undo extra H increment
    sub  8              ; 7T
    ld   h, a           ; 4T
    ret                 ; 10T  (77T total)
```

### 8x8 Unsigned Multiply (Shift-and-Add)

From Dark / X-Trade, Spectrum Expert #01 (1997). Used in rotation matrices and coordinate transforms.

```z80
; mulu112: 8x8 unsigned multiply
; Input:  B = multiplicand, C = multiplier
; Output: A:C = 16-bit result (A = high, C = low)
; Cost:   196-204 T-states
;
mulu112:
    ld   a, 0           ; 7T   clear accumulator
    ld   d, 8           ; 7T   8 bits

.loop:
    rr   c              ; 8T   shift multiplier bit into carry
    jr   nc, .noadd     ; 7/12T
    add  a, b           ; 4T   add multiplicand
.noadd:
    rra                 ; 4T   shift result right
    dec  d              ; 4T
    jr   nz, .loop      ; 12T
    ret                 ; 10T
```

### AY Register Write

Standard sequence for writing to the AY-3-8910 sound chip on ZX Spectrum 128K.

```z80
; ay_write: write value to AY register
; Input:  A = register number (0-15), E = value
; Cost:   41 T-states (plus CALL/RET overhead)
;
ay_write:
    ld   bc, $FFFD      ; 10T  register select port
    out  (c), a          ; 12T  select register
    ld   b, $BF          ;  7T  data port ($BFFD)
    out  (c), e          ; 12T  write value
    ret                  ; 10T
```

### 16-Bit Compare (HL vs DE)

The Z80 has no direct 16-bit compare. Use `SBC` and restore.

```z80
; Compare HL with DE (sets flags as if HL - DE)
; Destroys: A (if using the OR method for equality)
;
; For equality only:
    or   a              ; 4T   clear carry
    sbc  hl, de         ; 15T  HL = HL - DE, flags set
    add  hl, de         ; 11T  restore HL
                        ; --- 30T total, Z flag valid
```

### Stack-Based Screen Fill

The fastest way to fill the screen with a pattern. See Chapter 3.

```z80
; fill_screen: fill 6144 bytes using PUSH
; Input:  HL = 16-bit fill pattern
; Cost:   ~36,000 T-states (vs ~129,000 with LDIR)
;
fill_screen:
    di                          ; 4T
    ld   (restore_sp + 1), sp   ; 20T  save SP (self-modifying)
    ld   sp, $5800              ; 10T  end of pixel area

    ld   b, 192                 ; 7T   192 iterations x 16 pushes x 2 bytes = 6144
.loop:
    REPT 16
        push hl                 ; 11T  x 16 = 176T
    ENDR
    djnz .loop                  ; 13T/8T

restore_sp:
    ld   sp, $0000              ; 10T  self-modified
    ei                          ; 4T
    ret                         ; 10T
```

### Fast Pixel-Row Iteration (Split Counters)

From Introspec's DOWN_HL analysis (Hype, 2020). Eliminates all conditional branching from the inner loop. Total cost for 192 rows: 2,343T vs 5,922T for naive DOWN_HL calls.

```z80
; iterate all 192 rows with minimal overhead
; HL starts at $4000
;
iterate_screen:
    ld   hl, $4000          ; 10T
    ld   c, 3               ; 7T   three thirds

.third:
    ld   b, 8               ; 7T   eight character rows per third

.char_row:
    push hl                 ; 11T  save char row start

    REPT 7
        ; ... process row using HL ...
        inc  h              ; 4T   next scanline (NO branching)
    ENDR
    ; ... process 8th row ...

    pop  hl                 ; 10T  restore char row start
    ld   a, l              ; 4T
    add  a, 32             ; 7T   next character row
    ld   l, a              ; 4T
    djnz .char_row         ; 13T/8T

    ld   a, h              ; 4T
    add  a, 8              ; 7T   next third
    ld   h, a              ; 4T
    dec  c                 ; 4T
    jr   nz, .third        ; 12T/7T
```

---

## Quick Cost Comparisons

For inner loop decisions, these comparisons matter most:

| Operation | Slow way | Fast way | Savings |
|-----------|----------|----------|---------|
| Zero A | `LD A,0` (7T, 2B) | `XOR A` (4T, 1B) | 3T, 1B |
| Test A=0 | `CP 0` (7T, 2B) | `OR A` (4T, 1B) | 3T, 1B |
| Copy 1 byte to mem | `LD (HL),A`+`INC HL` (13T) | `LDI` (16T) | LDI is slower but auto-increments DE too |
| Copy N bytes | `LDIR` (21T/byte) | N x `LDI` (16T/byte) | 24% faster, costs 2N bytes of code |
| Fill 2 bytes | `LD (HL),A`+`INC HL` x2 (26T) | `PUSH rr` (11T) | 58% faster, needs SP hijack |
| 8-bit loop | `DEC B`+`JR NZ` (16T, 3B) | `DJNZ` (13T, 2B) | 3T, 1B per iteration |
| Indirect call | `CALL nn` (17T, 3B) | `RET` via render list (10T, 1B) | 7T, 2B per dispatch |
| Register swap | `LD A,H`+`LD H,D`+`LD D,A` (12T, 3B) | `EX DE,HL` (4T, 1B) | 8T, 2B |
| Save 6 registers | 3 x `PUSH` (33T, 3B) | `EXX` (4T, 1B) | 29T, 2B |

---

## Instruction Encoding Size Reference

For size-coding and estimating code density:

| Prefix | Instructions | Extra bytes | Extra T-states |
|--------|-------------|-------------|----------------|
| None | Most 8-bit ops, LD, ADD, INC, PUSH, POP, JP, JR | 0 | 0 |
| CB | Bit ops, shifts, rotates on registers | +1 | +4 typically |
| ED | Block ops, 16-bit ADC/SBC, IN/OUT (C), LD rr,(nn) | +1 | varies |
| DD | IX-indexed operations | +1 | +4 to +8 |
| FD | IY-indexed operations | +1 | +4 to +8 |
| DD CB | Bit/shift/rotate on (IX+d) | +2 | +8 to +12 |

**Size-coding tip:** Avoid IX/IY-indexed instructions when possible. `LD A,(IX+5)` is 3 bytes/19T. `LD L,5 / LD A,(HL)` is 3 bytes/11T if H already holds the page. The index registers are convenient but expensive.

---

> **Sources:** Zilog Z80 CPU User Manual (UM0080); Sean Young, "The Undocumented Z80 Documented" (2005); Dark / X-Trade, "Programming Algorithms" (Spectrum Expert #01, 1997); Introspec, "Once more about DOWN_HL" (Hype, 2020); Chapter 1 (timing harness); Chapter 3 (toolbox patterns); Chapter 4 (multiply, division)
