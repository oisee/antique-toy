# Appendix L: Z80-Optimal Floating Point — Why Byte-Aligned Exponents Beat IEEE

> *`INC H` = multiply by 2. Four T-states. IEEE 754 needs forty.*

---

## L.1 The Design Insight

IEEE 754 packs the exponent into a bit field that straddles byte boundaries. On an 8-bit CPU with no barrel shifter, extracting, incrementing, and repacking the exponent costs 30--40 T-states just to double a number.

The Z80-FP format family takes a different approach: **the exponent occupies an entire byte.** This means `INC reg` doubles the value and `DEC reg` halves it --- each in 4 T-states, 1 byte of code. The trade-off is reduced mantissa precision (7 bits instead of IEEE half's 10), but for demoscene and game applications, speed matters more than precision.

---

## L.2 The Type Hierarchy

Five formats share the same byte-aligned exponent convention, differing only in size and precision:

| Type | Size | Z80 Location | Layout | Precision | Key Operation |
|------|------|-------------|--------|-----------|---------------|
| `fp8` | 1 byte | A | `[EEEE.MMMM]` (E4M3) | ~3 digits | Ultra-compact |
| `fp16` | 2 bytes | HL | H=`[exp8]` L=`[S.mant7]` | ~2 digits | **Primary float** |
| `fp24` | 3 bytes | A+HL | A=`[exp8]` HL=`[S.mant15]` | ~4.5 digits | Extended precision |
| `fp32` | 4 bytes | HL+H'L' | Via EXX shadow bank | ~7 digits | Scientific |
| `fp40` | 5 bytes | A+HL+H'L' | Via EXX | ~9 digits | Maximum precision |

All formats use bias-127 exponent, so conversion between them is just mantissa truncation or expansion --- no bit-field repacking required.

---

## L.3 fp16: The Primary Float for Z80

### Memory Layout

```
Byte 0 (H): EEEEEEEE  — 8-bit exponent, bias 127
Byte 1 (L): SMMMMMMM  — S = sign, M = 7-bit mantissa (implicit leading 1)
```

Loads and stores via `LD HL,(addr)` / `LD (addr),HL`. Passes in HL, returns in HL.

### Operations

| Operation | Z80 Code | T-states | Notes |
|-----------|----------|----------|-------|
| ×2 | `INC H` | **4T** | Increment exponent |
| ÷2 | `DEC H` | **4T** | Decrement exponent |
| abs | `RES 7,L` | **8T** | Clear sign bit |
| negate | `LD A,L : XOR $80 : LD L,A` | 15T | Flip sign bit |
| is\_zero | `LD A,L : AND $7F : OR H` | 15T | Z flag set if zero |
| compare | Exponent first, then mantissa | ~45T | |
| add/sub | Align + add + normalize | 80--120T | Loop-based normalize |
| mul (const K) | Add exponents + mul8 table | **20--30T** | Uses Appendix K table! |
| mul (general) | Add exponents + 7×7 shift-add | 120--160T | |
| to\_uint8 | Shift mantissa by (134−exp) | 40--60T | Loop-based |
| from\_uint8 | Find leading 1, set exponent | 40--60T | Loop-based |

### Constant Multiply --- The Killer Feature

For `fp16 × 3.14159`:

1. Precompute the constant as fp16 at compile time: exp=128, mant=\$49, sign=0
2. Exponent addition: `LD A,H : ADD A,1 : LD H,A`
3. Mantissa multiply: use the mul8 table from Appendix K (mant = \$49|\$80 = \$C9)
4. **Total: ~20--30T** vs ~120T for general multiply

The 254-entry mul8 table covers constants 128--255, which is **100% of the fp16 mantissa range** (mantissas are normalized to \[1.0, 2.0), stored as 7-bit values plus implicit leading 1). Appendix K's multiplication table is literally the fp16 constant-multiply engine.

---

## L.4 fp24: When You Need More Precision

```
Byte 0 (A): EEEEEEEE  — 8-bit exponent, bias 127
Byte 1 (H): SMMMMMMM  — sign + mantissa bits 14:8
Byte 2 (L): MMMMMMMM  — mantissa bits 7:0
```

Uses A for the exponent --- **A is not free during fp24 operations.** Mantissa lives in HL, enabling `ADD HL,HL` for shift and `ADD HL,BC` for addition. Multiply by constant K uses the mul16 table from Appendix K.

| Operation | Z80 Code | T-states |
|-----------|----------|----------|
| ×2 | `INC A` | 4T |
| ÷2 | `DEC A` | 4T |
| abs | `RES 7,H` | 8T |
| negate | `LD B,A : LD A,H : XOR $80 : LD H,A : LD A,B` | 23T |
| normalize | `ADD HL,HL : DEC A` loop | max 14 iterations |

---

## L.5 Cross-Format Conversion

All Z80-FP formats share the same exponent bias (127) and byte alignment, so conversion is just register shuffling and mantissa width adjustment:

| Conversion | Method | Cost |
|-----------|--------|------|
| fp16 → fp24 | Expand mantissa, move exponent to A | ~20T |
| fp24 → fp16 | Truncate mantissa, move exponent to H | ~20T |
| uint8 → fp16 | Find leading 1, normalize | ~50T |
| fp16 → uint8 | Denormalize, extract integer | ~50T |
| f8.8 → fp16 | Find leading bit, set exponent | ~50T |
| fp16 → IEEE half | Repack exponent bits | ~30T |

---

## L.6 Design Rationale: Two fp24 Variants

Two layouts were considered for fp24:

1. **Sign-in-mantissa** (chosen): `A=[exp] H=[S.mant_hi] L=[mant_lo]` --- `INC A` = ×2, sign bit stays in H
2. **Sign-in-exponent**: `A=[S.exp7] HL=[mant16]` --- clean 16-bit mantissa for arithmetic, but ×2 requires sign-aware increment

The sign-in-mantissa layout won because fast ×2/÷2 is the most common floating-point operation in demoscene code (scaling, fading, interpolation), and it must be branchless.

---

*Data source: z80-optimizer v1.0.0, `pkg/fp16/`. Design: `docs/adr/adr-fp-format.md`*
