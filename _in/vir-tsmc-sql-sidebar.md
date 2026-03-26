# Material from MinZ VIR Backend for Z80 Demoscene Book

**From:** minz-vir session (2026-03-26 birthday marathon)
**For:** antique-toy chapters on self-modifying code, AI-assisted optimization

---

## 1. TSMC Tunnels — Self-Modifying Register Preservation

### The Pattern
```z80
; Save A across a CALL without touching SP
; (SP free for screen blitting: LD SP,screen_addr / POP)

LD (.tunnel_a+1), A    ; 13T, 3 bytes — patch the immediate byte
CALL some_routine       ; clobbers A, B, C, D, E, H, L
.tunnel_a:
LD A, 0                 ; 7T, 2 bytes — CPU reads patched byte, not 0!
                        ; Total: 20T (vs PUSH AF/POP AF = 21T)
```

### Why It Matters for Demos
- **SP is free** — use SP as data pointer for fast screen output (POP trick)
- **1T cheaper** than PUSH/POP — matters in tight loops
- **Works for ANY 8-bit register** — not just pairs like PUSH/POP
- **Multiple tunnels** — unlimited save slots (vs 4 IX half-register slots)

### Cost Comparison
| Method | Save | Restore | Total | SP touched? |
|--------|------|---------|-------|-------------|
| IXH/IXL | 8T | 8T | 16T | No |
| TSMC tunnel | 13T | 7T | 20T | No |
| PUSH/POP | 11T | 10T | 21T | **Yes** |
| Memory spill | 13T | 13T | 26T | No |

### The Demoscene Connection
Classic ZX demo trick: `LD SP, screen_addr` then rapid `POP` for 2-byte-at-a-time screen filling. But if you need to CALL a routine mid-frame, PUSH/POP would corrupt SP. TSMC tunnels solve this — save registers without SP, keep SP pointed at screen memory.

### @error Propagation
TSMC tunnels also enable clean error propagation:
```z80
LD (.tunnel+1), A       ; save value
CALL risky_function?    ; may set carry flag (error)
RET C                   ; if error: return immediately (SP clean!)
.tunnel: LD A, 0        ; restore value (carry was clear = success)
```
RET C works because SP was never modified. With PUSH/POP, RET C would return to the wrong address.

---

## 2. SQL on ZX Spectrum — AI-Optimized Z80 Code

### What It Does
A complete SQL client (ZSQL) running on Z80 CP/M and ZX Spectrum:
```sql
CREATE TABLE mara (matnr TEXT, mtart TEXT, meins TEXT, maktx TEXT);
INSERT INTO mara VALUES ('100-100', 'FERT', 'ST', 'Pump Assembly');
SELECT * FROM mara WHERE mtart = 'FERT';
→ 100-100|FERT|ST|Pump Assembly
```

### How It's Compiled
- 31 functions, ALL via Z3 SMT solver (zero heuristic fallback)
- Z3-PFCCO optimizes calling conventions across ALL call sites simultaneously
- swap() compiles to 0 instructions (pure calling convention trick)
- puts() compiles to 1 instruction (RET — value already in place)

### Example: puts()
```z80
; Z3 saw: puts(str) just passes str to the output routine.
; PFCCO arranged: str arrives in HL (the output register).
; Result: nothing to do — just return.
puts:
    RET
```

The Z3 solver + PFCCO eliminated the entire function body by choosing calling conventions that make the function a no-op.

---

## 3. GPU-Optimal Arithmetic (372 Sequences)

### Constant Multiplication (254 entries)
Every u8 multiply-by-constant, proven optimal by CUDA exhaustive search:
```z80
; ×3 = 12T (vs 80T general multiply loop = 6.7× faster)
LD B, A
ADC A, A
ADD A, B

; ×10 = 20T
RLA
LD B, A
ADD A, B
ADD A, A
```

### Constant Division (118 entries)
```z80
; div57 = 6 instructions (shortest division ever!)
; div114 = 46T (fastest)
; div100 = 105T (vs 180T loop = 1.7× faster)
```

### For Demos
Pixel coordinate scaling, color cycling, sprite animation timing — all use constant multiply/divide. With GPU-proven optimal sequences, every arithmetic operation in the demo is as fast as physically possible.

---

## 4. The 83.6M Regalloc Table

**83.6 million** register allocation shapes solved exhaustively on GPU. For functions with ≤6 virtual registers (63% of real code), the compiler looks up the answer in O(1). No search, no heuristic — just a hash lookup.

**Feasibility cliff:** 95.9% of 2-vreg shapes are feasible, dropping to 0.9% at 6 vregs. The Z80's irregular register file eliminates the vast majority of theoretical configurations.

**For the book:** This is the "endgame tablebase" analogy — like chess engines that play perfectly with ≤7 pieces, the compiler allocates perfectly with ≤6 registers.
