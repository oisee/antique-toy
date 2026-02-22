# MZA Bug Report — Binary Comparison with sjasmplus v1.21.1

Date: 2026-02-22
Test method: Same .a80 source files assembled by both sjasmplus (reference) and mza.
Binary output compared byte-for-byte.

## Results

| File | Size | Match? |
|------|------|--------|
| ch01 timing_harness.a80 | 18 B | MATCH |
| ch02 fill_screen.a80 | 33 B | MATCH |
| ch02 pixel_demo.a80 | 180 B | MATCH |
| ch03 push_fill.a80 | 50 B | MATCH |
| ch04 multiply8.a80 | 34 B | MATCH |
| ch05 wireframe_cube.a80 | 1383 B | **DIFFER** (8 bytes — Bug 3) |
| ch09 plasma.a80 | 1280 B | MATCH |
| ch11 ay_test.a80 | 132 B | MATCH |
| ch16 sprite_demo.a80 | 350 B | MATCH |
| ch18 game_skeleton.a80 | 829 B | **DIFFER** (13 bytes — Bug 1) |
| ch19 aabb_test.a80 | 321 B | MATCH |
| demo torus.a80 | 1929 B | **DIFFER** (8 bytes — Bug 3) |

**9/12 byte-identical. 3/12 differ due to bugs below.**

---

## Bug 1: BIT/SET/RES bit number ignored when using EQU constants

**Severity: HIGH — silent wrong code generation**

When the bit number operand of BIT, SET, or RES comes from an EQU constant,
mza always encodes bit=0 in the opcode byte, ignoring the actual value.
Literal bit numbers work correctly. No error is reported.

### Minimal reproduction

```z80
    ORG $8000
FLAG3 EQU 3
    bit  3, a           ; literal → CB 5F  ← both correct
    bit  FLAG3, a       ; EQU     → CB 5F  ← mza produces CB 47 (bit 0!)
    set  3, b           ; literal → CB D8  ← both correct
    set  FLAG3, b       ; EQU     → CB D8  ← mza produces CB C0 (set 0!)
    res  3, a           ; literal → CB 9F  ← both correct
    res  FLAG3, a       ; EQU     → CB 9F  ← mza produces CB 87 (res 0!)
    bit  3, (ix+5)      ; literal → DD CB 05 5E  ← both correct
    bit  FLAG3, (ix+5)  ; EQU     → DD CB 05 5E  ← mza produces DD CB 05 46 (bit 0!)
```

### Affected instructions in project (game_skeleton.a80, 13 byte diffs)

| Source instruction | sjasmplus | mza | Expected bit |
|--------------------|-----------|-----|-------------|
| `bit INPUT_FIRE, a` (×4) | CB 67 | CB 47 | 4 |
| `set INPUT_LEFT, d` | CB CA | CB C2 | 1 |
| `set INPUT_UP, d` | CB DA | CB C2 | 3 |
| `set INPUT_DOWN, d` | CB D2 | CB C2 | 2 |
| `set INPUT_FIRE, d` | CB E2 | CB C2 | 4 |
| `res FLAG_FACING_L, (ix+9)` | DD CB 09 9E | DD CB 09 86 | 3 |
| `bit INPUT_LEFT, a` | CB 4F | CB 47 | 1 |
| `set FLAG_FACING_L, (ix+9)` | DD CB 09 DE | DD CB 09 C6 | 3 |
| `bit FLAG_FACING_L, a` | CB 5F | CB 47 | 3 |
| `bit FLAG_VISIBLE, (ix+9)` | DD CB 09 4E | DD CB 09 46 | 1 |

### Analysis

The bit number field (bits 5-3 of the CB-prefixed opcode byte) is always
encoded as 000 when the operand is an EQU symbol. With literal numbers
the field is correct. This suggests the expression evaluator returns the
value but the encoder doesn't apply it to the bit field — likely it uses
the raw token (which defaults to 0) instead of the resolved value.

---

## Bug 2: BIT/SET/RES with (HL) operand not supported

**Severity: MEDIUM — assembly error (not silent)**

```z80
    bit  3, (hl)        ; valid Z80: CB 5E — mza: "invalid register"
    set  3, (hl)        ; valid Z80: CB DE — mza: "invalid register"
    res  3, (hl)        ; valid Z80: CB 9E — mza: "invalid register"
```

These are standard Z80 instructions. Register forms (`bit 3, a`) and
IX-indexed forms (`bit 3, (ix+d)`) work, but the (HL) form is rejected.

Not triggered by the current project files (none use bit/set/res with (HL)),
but it's a completeness gap.

---

## Bug 3: Local labels in expressions resolve to address 0

**Severity: HIGH — silent wrong code generation**

When a local label (`.name`) is referenced inside an arithmetic expression,
mza resolves the label to address 0 instead of its actual address.
Direct references to local labels work; only expressions fail.

### Minimal reproduction

```z80
    ORG $8000
target:
    nop
.local:
    nop
    ld   a, (.local)        ; sjasm: 3A 15 80  ← correct ($8015)
                             ; mza:   3A 00 00  ← WRONG (label=0)
    ld   (.local + 1), a    ; sjasm: 32 16 80  ← correct ($8016)
                             ; mza:   32 01 00  ← WRONG (0+1=1)
```

### Affected instructions in project

wireframe_cube.a80 and draw.a80 (via torus.a80) use self-modifying code
with local labels:

```z80
draw_line:
    ...
    ld   (.smc_hcmp + 1), a    ; sjasm: 32 7B 83 ← correct
                                ; mza:   32 01 00 ← WRONG
    ...
.smc_hcmp:
    cp   0                      ; self-modified target
```

All 4 labels affected: `.smc_hcmp`, `.smc_hsub`, `.smc_vcmp`, `.smc_vsub`
Each has 2 expression references → 8 byte differences per file.

### Workaround

Use global labels for self-modifying code targets (the original code before
the sjasmplus migration used global `smc_hcmp:` which worked in both).

---

## Summary for mza developers

| Bug | Type | Impact | Fix priority |
|-----|------|--------|-------------|
| BIT/SET/RES + EQU | Silent wrong code | Named bit flags broken | HIGH |
| BIT/SET/RES + (HL) | Assembly error | Missing instruction form | MEDIUM |
| Local labels in expressions | Silent wrong code | SMC patterns broken | HIGH |

The mza opcode test suite (715/715 PASS) likely tests with literal operands
only. Adding tests with EQU constants for bit numbers and local labels in
expressions would catch bugs 1 and 3.
