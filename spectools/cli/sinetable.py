#!/usr/bin/env python3
"""
Sine Table Generator for Z80 Assembly Development.

Generates sine lookup tables using 7 different approaches,
from exact precomputed LUTs to compact approximation methods.
Part of spectools for the "Coding the Impossible" book project.

Usage:
    python sinetable.py --approach 1 --size 256 --amplitude 127
    python sinetable.py --approach 2 --size 256 --amplitude 127 --format c
    python sinetable.py --compare --size 256 --amplitude 127
"""

import argparse
import json
import math
import sys
from typing import NamedTuple


# ---------------------------------------------------------------------------
# Core sine generation — ideal reference
# ---------------------------------------------------------------------------

def ideal_sine(size: int, amplitude: int, unsigned: bool) -> list[float]:
    """Generate ideal sine values as floats for a full period."""
    values = []
    for i in range(size):
        angle = i * 2.0 * math.pi / size
        v = math.sin(angle) * amplitude
        if unsigned:
            v = v + amplitude
        values.append(v)
    return values


def quantize(values: list[float]) -> list[int]:
    """Round floats to nearest integer."""
    return [int(round(v)) for v in values]


# ---------------------------------------------------------------------------
# Approach 1 — Full 256-byte LUT
# ---------------------------------------------------------------------------

def approach1_full_lut(size: int, amplitude: int, unsigned: bool) -> list[int]:
    """Full precomputed sine table."""
    return quantize(ideal_sine(size, amplitude, unsigned))


# ---------------------------------------------------------------------------
# Approach 2 — Quarter-wave symmetry
# ---------------------------------------------------------------------------

def approach2_quarter_wave(size: int, amplitude: int, unsigned: bool) -> list[int]:
    """Quarter-wave table. Returns first quarter plus one entry (size/4 + 1
    entries, indices 0..size/4 inclusive) so reconstruction is exact.
    E.g. for size=256, returns 65 entries covering 0..pi/2."""
    quarter = size // 4
    values = []
    for i in range(quarter + 1):
        angle = i * 2.0 * math.pi / size
        v = math.sin(angle) * amplitude
        values.append(int(round(v)))
    return values


def approach2_reconstruct(quarter_table: list[int], size: int,
                          amplitude: int, unsigned: bool) -> list[int]:
    """Reconstruct full table from quarter-wave data (q+1 entries)."""
    q = size // 4
    full = [0] * size
    for i in range(size):
        if i <= q:           # 0..q
            v = quarter_table[i]
        elif i < 2 * q:     # q+1..2q-1
            v = quarter_table[2 * q - i]
        elif i <= 3 * q:    # 2q..3q
            v = -quarter_table[i - 2 * q]
        else:                # 3q+1..4q-1
            v = -quarter_table[4 * q - i]
        if unsigned:
            v = v + amplitude
        full[i] = v
    return full


# ---------------------------------------------------------------------------
# Approach 3 — Second-order delta encoding
# ---------------------------------------------------------------------------

def approach3_delta_encoding(size: int, amplitude: int, unsigned: bool
                             ) -> tuple[list[int], list[int], list[int],
                                        int, bool]:
    """Quarter-wave delta encoding, nibble-packed when possible.

    Stores the initial value (0) plus quarter-wave deltas. When all deltas
    fit in 0..15 (typical for size >= ~32 with reasonable amplitude), packs
    two deltas per byte (high nibble first). Otherwise falls back to byte
    storage.

    Combined with quarter-wave symmetry for reconstruction, this gives
    ~size/8 bytes (nibble-packed) or ~size/4 bytes (byte-packed).

    Returns (full_reconstructed, quarter_values, packed_bytes, nbytes,
             nibble_packed).
    """
    q = size // 4

    # Compute quarter-wave values (0..q inclusive, q+1 entries)
    quarter = []
    for i in range(q + 1):
        angle = i * 2.0 * math.pi / size
        quarter.append(int(round(math.sin(angle) * amplitude)))

    # Compute deltas within the quarter
    deltas = [quarter[i + 1] - quarter[i] for i in range(q)]

    # Check if nibble packing is possible (all deltas 0..15)
    nibble_ok = all(0 <= d <= 15 for d in deltas)

    if nibble_ok:
        # Pack deltas into nibbles (2 per byte, high nibble first)
        packed = []
        for i in range(0, q, 2):
            hi = deltas[i] & 0x0F
            lo = deltas[i + 1] & 0x0F if i + 1 < q else 0
            packed.append((hi << 4) | lo)

        # Reconstruct quarter from packed nibbles
        recon_quarter = [quarter[0]]
        for i in range(q):
            byte_idx = i // 2
            if i % 2 == 0:
                d = (packed[byte_idx] >> 4) & 0x0F
            else:
                d = packed[byte_idx] & 0x0F
            recon_quarter.append(recon_quarter[-1] + d)
    else:
        # Fall back to byte-per-delta storage
        packed = list(deltas)
        recon_quarter = [quarter[0]]
        for d in deltas:
            recon_quarter.append(recon_quarter[-1] + d)

    # Reconstruct full table from quarter using symmetry
    full = [0] * size
    for i in range(size):
        if i <= q:
            v = recon_quarter[i]
        elif i < 2 * q:
            v = recon_quarter[2 * q - i]
        elif i <= 3 * q:
            v = -recon_quarter[i - 2 * q]
        else:
            v = -recon_quarter[4 * q - i]
        if unsigned:
            v = v + amplitude
        full[i] = v

    # Storage: 1 byte initial + packed data
    nbytes = 1 + len(packed)

    return full, quarter, packed, nbytes, nibble_ok


# ---------------------------------------------------------------------------
# Approach 4 — Parabolic approximation
# ---------------------------------------------------------------------------

def approach4_parabolic(size: int, amplitude: int, unsigned: bool) -> list[int]:
    """Parabolic approximation: sin(x) ≈ 4x(π-x)/π² for 0..π,
    mirrored for π..2π."""
    values = []
    for i in range(size):
        x = i * 2.0 * math.pi / size
        # Normalize to 0..2π
        x = x % (2.0 * math.pi)
        if x < math.pi:
            # 0..π: positive half
            v = 4.0 * x * (math.pi - x) / (math.pi * math.pi)
        else:
            # π..2π: negative half (mirror)
            x2 = x - math.pi
            v = -4.0 * x2 * (math.pi - x2) / (math.pi * math.pi)
        v *= amplitude
        if unsigned:
            v += amplitude
        values.append(int(round(v)))
    return values


# ---------------------------------------------------------------------------
# Approach 5 — Bhaskara I approximation
# ---------------------------------------------------------------------------

def approach5_bhaskara(size: int, amplitude: int, unsigned: bool) -> list[int]:
    """Bhaskara I approximation: sin(x) ≈ 16x(π-x) / (5π²-4x(π-x))
    for 0..π, mirrored for π..2π."""
    values = []
    for i in range(size):
        x = i * 2.0 * math.pi / size
        x = x % (2.0 * math.pi)
        if x < math.pi:
            num = 16.0 * x * (math.pi - x)
            den = 5.0 * math.pi * math.pi - 4.0 * x * (math.pi - x)
            v = num / den if den != 0 else 0.0
        else:
            x2 = x - math.pi
            num = 16.0 * x2 * (math.pi - x2)
            den = 5.0 * math.pi * math.pi - 4.0 * x2 * (math.pi - x2)
            v = -(num / den) if den != 0 else 0.0
        v *= amplitude
        if unsigned:
            v += amplitude
        values.append(int(round(v)))
    return values


# ---------------------------------------------------------------------------
# Approach 6 — Recursive difference equation
# ---------------------------------------------------------------------------

def approach6_recursive(size: int, amplitude: int, unsigned: bool) -> list[int]:
    """Recursive difference equation:
    sin(n+1) = 2*cos(theta)*sin(n) - sin(n-1)
    where theta = 2*pi/size.

    Uses 16-bit (2.14) fixed-point for the coefficient and 16-bit (8.8)
    fixed-point for value accumulators. On a Z80 this requires a 16x16->32
    multiply followed by >>14 shift, feasible in ~120 T-states.

    Total data: 4 bytes (2*cos as 16-bit + sin(1) as 16-bit).
    Typical max error: ~4-5% for size=256, amplitude=127."""
    theta = 2.0 * math.pi / size
    cos_theta = math.cos(theta)

    # 2.14 fixed-point for coefficient (16-bit, max ~2.0)
    COEFF_FRAC = 14
    COEFF_SCALE = 1 << COEFF_FRAC

    # 8.8 fixed-point for value accumulators (16-bit, fits in register pair)
    VAL_FRAC = 8
    VAL_SCALE = 1 << VAL_FRAC

    # 2*cos(theta) in 2.14
    two_cos_fp = int(round(2.0 * cos_theta * COEFF_SCALE))

    # Initial conditions in 8.8
    sin_prev = 0  # sin(0) = 0
    sin_curr = int(round(math.sin(theta) * amplitude * VAL_SCALE))

    values = []
    for i in range(size):
        val = int(round(sin_prev / VAL_SCALE))
        if unsigned:
            val += amplitude
        values.append(val)
        # sin(n+1) = 2cos(theta)*sin(n) - sin(n-1)
        # Multiply 2.14 * 8.8, get 32-bit result, >>14 to get 8.8
        product = (two_cos_fp * sin_curr + (1 << (COEFF_FRAC - 1))) >> COEFF_FRAC
        sin_next = product - sin_prev
        sin_prev = sin_curr
        sin_curr = sin_next

    return values


# ---------------------------------------------------------------------------
# Approach 7 — CORDIC-style iterative
# ---------------------------------------------------------------------------

def approach7_cordic(size: int, amplitude: int, unsigned: bool) -> list[int]:
    """CORDIC-style iterative sine computation.

    Uses a table of arctangent values for iterative rotation.
    For each desired angle, rotates a unit vector using the CORDIC algorithm.

    Simulates Z80 implementation using 16-bit fixed-point (8.8) for
    coordinates and 16-bit angles. The atan table stores 16-bit angle values.

    CORDIC convergence range is ~[-99.7deg, +99.7deg]. For angles outside
    this range, we pre-rotate by +/-90 degrees (swap x,y and negate).

    On Z80: ~14 iterations, each needs 2 shifts + 2 adds + 1 comparison.
    Total data: ~30 bytes (14 x 16-bit atan values) + initial x value."""
    ITERATIONS = 14

    # Atan table as fractions of full circle (0..65536 = 0..2π)
    ANGLE_SCALE = 65536.0 / (2.0 * math.pi)
    atan_table_rad = [math.atan(2.0 ** (-i)) for i in range(ITERATIONS)]
    atan_table_fp = [int(round(a * ANGLE_SCALE)) for a in atan_table_rad]

    # CORDIC gain
    K = 1.0
    for i in range(ITERATIONS):
        K *= math.cos(atan_table_rad[i])

    # Fixed-point coordinate scale (8.8)
    COORD_FRAC = 8
    COORD_SCALE = 1 << COORD_FRAC

    # Initial x = K * amplitude (pre-scaled)
    init_x = int(round(K * amplitude * COORD_SCALE))

    # 90 degrees in our angle system
    QUARTER = 16384  # 65536 / 4

    def asr(val: int, shift: int) -> int:
        """Arithmetic shift right (preserves sign)."""
        if val >= 0:
            return val >> shift
        else:
            return -((-val) >> shift)

    values = []
    for idx in range(size):
        # Target angle as 16-bit value (0..65535 = 0..2π)
        target_fp = int(round(idx * 65536.0 / size)) & 0xFFFF

        # Normalize to signed range (-32768..32767 = -π..π)
        if target_fp >= 32768:
            target_signed = target_fp - 65536
        else:
            target_signed = target_fp

        # Pre-rotation for angles outside CORDIC convergence zone (~±99.7°)
        # If |angle| > 90°, pre-rotate by ±90° to bring into range
        x = init_x
        y = 0
        angle = 0

        if target_signed > QUARTER:
            # Pre-rotate +90°: (x,y) -> (-y, x)
            x, y = 0, init_x
            angle = QUARTER
        elif target_signed < -QUARTER:
            # Pre-rotate -90°: (x,y) -> (y, -x)
            x, y = 0, -init_x
            angle = -QUARTER

        # CORDIC iterations
        for i in range(ITERATIONS):
            if angle < target_signed:
                d = 1
            else:
                d = -1
            shift_x = asr(x, i)
            shift_y = asr(y, i)
            new_x = x - d * shift_y
            new_y = y + d * shift_x
            angle += d * atan_table_fp[i]
            x = new_x
            y = new_y

        # y / COORD_SCALE is the sine value
        v = int(round(y / COORD_SCALE))
        # Clamp to valid range
        v = max(-amplitude, min(amplitude, v))
        if unsigned:
            v += amplitude
        values.append(v)

    return values


# ---------------------------------------------------------------------------
# Error computation
# ---------------------------------------------------------------------------

class ErrorStats(NamedTuple):
    max_err: float      # maximum absolute error vs ideal (in amplitude units)
    rms_err: float      # RMS error vs ideal
    max_pct: float      # max error as percentage of amplitude
    rms_pct: float      # RMS error as percentage of amplitude


def compute_errors(approx: list[int], size: int, amplitude: int,
                   unsigned: bool) -> ErrorStats:
    """Compute error statistics of an approximation vs ideal sine."""
    ref = quantize(ideal_sine(size, amplitude, unsigned))

    if len(approx) != len(ref):
        # For quarter-wave, reconstruct full table first
        # This shouldn't happen if called correctly
        pass

    max_err = 0.0
    sum_sq = 0.0
    for i in range(len(ref)):
        err = abs(approx[i] - ref[i])
        max_err = max(max_err, err)
        sum_sq += err * err
    rms_err = math.sqrt(sum_sq / len(ref)) if ref else 0.0

    amp = amplitude if amplitude > 0 else 1
    return ErrorStats(
        max_err=max_err,
        rms_err=rms_err,
        max_pct=max_err / amp * 100.0,
        rms_pct=rms_err / amp * 100.0,
    )


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

APPROACH_NAMES = {
    1: "full LUT",
    2: "quarter-wave",
    3: "delta encoding",
    4: "parabolic approximation",
    5: "Bhaskara I approximation",
    6: "recursive difference equation",
    7: "CORDIC iterative",
}

APPROACH_NAMES_LONG = {
    1: "Full LUT",
    2: "Quarter-wave",
    3: "Delta encoding",
    4: "Parabolic",
    5: "Bhaskara I",
    6: "Recursive diff. eq.",
    7: "CORDIC",
}


def format_db_line(values: list[int], start_idx: int, signed: bool) -> str:
    """Format a single DB line with 8 values."""
    end_idx = start_idx + len(values) - 1
    if signed:
        parts = [f"{v:4d}" for v in values]
    else:
        parts = [f"{v:4d}" for v in values]
    return f"    DB  {', '.join(parts)}  ; {start_idx}-{end_idx}"


def format_asm_table(label: str, values: list[int], signed: bool,
                     per_line: int = 8) -> str:
    """Format values as assembly DB lines."""
    lines = []
    lines.append(f"{label}:")
    for i in range(0, len(values), per_line):
        chunk = values[i:i + per_line]
        lines.append(format_db_line(chunk, i, signed))
    return "\n".join(lines)


def format_asm_header(approach: int, size: int, amplitude: int,
                      unsigned: bool, errors: ErrorStats,
                      extra_lines: list[str] | None = None) -> str:
    """Format the assembly file header comment."""
    mode = "unsigned" if unsigned else "signed"
    lines = [
        f"; Sine table — approach {approach} ({APPROACH_NAMES[approach]}), "
        f"{size} entries, amplitude {amplitude} ({mode})",
        f"; Generated by sinetable.py (spectools)",
    ]
    if errors.max_err == 0:
        lines.append(f"; Max error: 0.000 (exact precomputed)")
    else:
        lines.append(
            f"; Max error: {errors.max_err:.3f} ({errors.max_pct:.3f}%), "
            f"RMS error: {errors.rms_err:.3f} ({errors.rms_pct:.3f}%)"
        )
    if extra_lines:
        for line in extra_lines:
            lines.append(f"; {line}")
    lines.append("")
    return "\n".join(lines)


def generate_approach1_asm(size: int, amplitude: int, unsigned: bool) -> str:
    """Generate full LUT assembly output."""
    values = approach1_full_lut(size, amplitude, unsigned)
    errors = compute_errors(values, size, amplitude, unsigned)
    header = format_asm_header(1, size, amplitude, unsigned, errors)
    table = format_asm_table("sine_table", values, not unsigned)
    return header + table


def generate_approach2_asm(size: int, amplitude: int, unsigned: bool) -> str:
    """Generate quarter-wave assembly output."""
    quarter = approach2_quarter_wave(size, amplitude, unsigned)
    full = approach2_reconstruct(quarter, size, amplitude, unsigned)
    errors = compute_errors(full, size, amplitude, unsigned)

    q = size // 4
    entries = q + 1
    extra = [
        f"Full table size: {size}. Reconstruct via symmetry.",
        f"Stores {entries} entries (indices 0..{q} inclusive).",
        f"Usage: for 0..{q} use table[i], "
        f"{q+1}..{2*q-1} use table[{2*q}-i],",
        f"       {2*q}..{3*q} negate table[i-{2*q}], "
        f"{3*q+1}..{size-1} negate table[{4*q}-i]",
    ]
    header = format_asm_header(2, entries, amplitude, unsigned, errors, extra)

    # Override the first header line for quarter-wave
    lines = header.split("\n")
    lines[0] = (
        f"; Sine table — approach 2 (quarter-wave), "
        f"{entries} entries (quarter+1), amplitude {amplitude}"
    )
    header = "\n".join(lines)

    table = format_asm_table("sine_quarter", quarter, True)
    return header + table


def generate_approach3_asm(size: int, amplitude: int, unsigned: bool) -> str:
    """Generate delta encoding assembly output."""
    reconstructed, quarter, packed, nbytes, nibble_packed = \
        approach3_delta_encoding(size, amplitude, unsigned)
    errors = compute_errors(reconstructed, size, amplitude, unsigned)

    q = size // 4
    deltas = [quarter[i + 1] - quarter[i] for i in range(q)]

    if nibble_packed:
        packing = "nibble-packed"
        pack_desc = f"{len(packed)} packed nibble bytes (2 deltas/byte)"
    else:
        packing = "byte-packed"
        pack_desc = f"{len(packed)} delta bytes"

    extra = [
        f"Quarter-wave {packing} delta encoding",
        f"Storage: {nbytes} bytes (1 initial + {pack_desc})",
        f"Quarter size: {q} deltas",
        f"Delta range: {min(deltas)}..{max(deltas)}"
        + (" (fits in 4-bit nibble)" if nibble_packed
           else " (byte per delta)"),
        f"Reconstruct quarter from deltas, then full table via symmetry.",
    ]

    if nibble_packed:
        extra += [
            f"",
            f"Z80 reconstruction code (unpacks to sine_buffer):",
            f"  ; Unpack nibble-packed deltas into quarter-wave table,",
            f"  ; then reconstruct full table via symmetry.",
            f"  ld hl, sine_packed    ; packed nibble data",
            f"  ld de, sine_buffer    ; destination quarter table",
            f"  xor a                 ; initial value = 0",
            f"  ld b, {len(packed)}              ; packed byte count",
            f".unpack:",
            f"  ld (de), a            ; store current value",
            f"  inc de",
            f"  ld c, (hl)            ; get packed byte",
            f"  push af               ; save accumulator",
            f"  ld a, c",
            f"  rrca",
            f"  rrca",
            f"  rrca",
            f"  rrca",
            f"  and $0F               ; high nibble = first delta",
            f"  ld c, a",
            f"  pop af",
            f"  add a, c              ; accumulate first delta",
            f"  ld (de), a            ; store value",
            f"  inc de",
            f"  push af",
            f"  ld a, (hl)            ; re-read packed byte",
            f"  and $0F               ; low nibble = second delta",
            f"  ld c, a",
            f"  pop af",
            f"  add a, c              ; accumulate second delta",
            f"  inc hl                ; next packed byte",
            f"  djnz .unpack",
        ]
    else:
        extra += [
            f"",
            f"Z80 reconstruction code (unpacks to sine_buffer):",
            f"  ; Add byte deltas to reconstruct quarter-wave table.",
            f"  ld hl, sine_deltas    ; delta byte data",
            f"  ld de, sine_buffer    ; destination quarter table",
            f"  xor a                 ; initial value = 0",
            f"  ld b, {len(packed)}              ; delta count",
            f".unpack:",
            f"  ld (de), a            ; store current value",
            f"  inc de",
            f"  add a, (hl)           ; add delta",
            f"  inc hl",
            f"  djnz .unpack",
            f"  ld (de), a            ; store final value",
        ]

    header = format_asm_header(3, size, amplitude, unsigned, errors, extra)

    lines = [header]

    # Emit the packed data
    label = "sine_packed" if nibble_packed else "sine_deltas"
    lines.append(f"{label}:")
    if nibble_packed:
        for i in range(0, len(packed), 8):
            chunk = packed[i:i + 8]
            end_idx = i + len(chunk) - 1
            parts = [f"${b:02X}" for b in chunk]
            lines.append(
                f"    DB  {', '.join(parts)}  ; bytes {i}-{end_idx}")
    else:
        for i in range(0, len(packed), 8):
            chunk = packed[i:i + 8]
            end_idx = i + len(chunk) - 1
            parts = [f"{d:4d}" for d in chunk]
            lines.append(
                f"    DB  {', '.join(parts)}  ; deltas {i}-{end_idx}")

    lines.append("")
    lines.append("; Unpacked quarter-wave for reference:")
    table = format_asm_table("; sine_quarter", quarter, True)
    table_lines = table.split("\n")
    commented = []
    for tl in table_lines:
        if tl.startswith("; sine_quarter:"):
            commented.append(tl)
        elif tl.strip():
            commented.append("; " + tl)
    lines.append("\n".join(commented))

    return "\n".join(lines)


def generate_approach4_asm(size: int, amplitude: int, unsigned: bool) -> str:
    """Generate parabolic approximation assembly output."""
    values = approach4_parabolic(size, amplitude, unsigned)
    errors = compute_errors(values, size, amplitude, unsigned)

    extra = [
        f"Parabolic approximation: sin(x) ≈ 4x(π-x)/π²",
        f"Max theoretical error vs true sine: ~5.6%",
        f"",
        f"Z80 implementation (for 0..255 input range, 0..π mapped to 0..128):",
        f"  ; Input: A = angle (0..255), Output: A = sin(angle)",
        f"  ; Uses parabolic formula in fixed-point",
        f"  ; For x in 0..128 (0..π):",
        f"  ;   sin(x) ≈ 4*x*(128-x)/128  (scaled)",
        f"  ; For x in 128..255 (π..2π):",
        f"  ;   sin(x) = -sin(x-128)",
        f"  ;",
        f"  ; This requires one multiply but no lookup table.",
        f"  para_sin:",
        f"  ;   ld b, a          ; save original",
        f"  ;   bit 7, a",
        f"  ;   jr z, .positive",
        f"  ;   neg              ; A = 256-A for second half",
        f"  ; .positive:",
        f"  ;   ld c, a          ; C = x (0..128)",
        f"  ;   ld a, 128",
        f"  ;   sub c            ; A = 128-x",
        f"  ;   ; multiply C * A, result in HL",
        f"  ;   call mul_8x8     ; HL = x*(128-x)",
        f"  ;   ; scale: HL * 4 / 128 = HL >> 5",
        f"  ;   ... (shift and negate if needed)",
    ]
    header = format_asm_header(4, size, amplitude, unsigned, errors, extra)

    # Include the precomputed values for reference
    lines = [header]
    lines.append("; Precomputed values for reference/verification:")
    table = format_asm_table("sine_parabolic", values, not unsigned)
    lines.append(table)
    return "\n".join(lines)


def generate_approach5_asm(size: int, amplitude: int, unsigned: bool) -> str:
    """Generate Bhaskara I approximation assembly output."""
    values = approach5_bhaskara(size, amplitude, unsigned)
    errors = compute_errors(values, size, amplitude, unsigned)

    extra = [
        f"Bhaskara I approximation: sin(x) ≈ 16x(π-x) / (5π²-4x(π-x))",
        f"Max theoretical error vs true sine: ~0.15%",
        f"",
        f"Z80 implementation sketch (fixed-point, 0..128 = 0..π):",
        f"  ; Input: A = angle (0..255), Output: A = sin(angle)",
        f"  ; For x in 0..128:",
        f"  ;   p = x*(128-x)       ; 8-bit multiply",
        f"  ;   num = 16*p           ; = p << 4",
        f"  ;   den = 5*128*128 - 4*p  ; = 81920 - 4*p",
        f"  ;   sin ≈ num / den      ; 16-bit division",
        f"  ; For x in 128..255: negate result of (x-128)",
        f"  ;",
        f"  ; Requires 8x8 multiply and 16-bit divide.",
        f"  ; More accurate than parabolic but heavier on CPU.",
    ]
    header = format_asm_header(5, size, amplitude, unsigned, errors, extra)

    lines = [header]
    lines.append("; Precomputed values for reference/verification:")
    table = format_asm_table("sine_bhaskara", values, not unsigned)
    lines.append(table)
    return "\n".join(lines)


def generate_approach6_asm(size: int, amplitude: int, unsigned: bool) -> str:
    """Generate recursive difference equation assembly output."""
    values = approach6_recursive(size, amplitude, unsigned)
    errors = compute_errors(values, size, amplitude, unsigned)

    theta = 2.0 * math.pi / size
    cos_theta = math.cos(theta)

    COEFF_FRAC = 14
    COEFF_SCALE = 1 << COEFF_FRAC
    VAL_FRAC = 8
    VAL_SCALE = 1 << VAL_FRAC

    two_cos_fp = int(round(2.0 * cos_theta * COEFF_SCALE))
    sin1_fp = int(round(math.sin(theta) * amplitude * VAL_SCALE))

    extra = [
        f"Recursive difference equation:",
        f"  sin(n+1) = 2*cos(theta)*sin(n) - sin(n-1)",
        f"  theta = 2*pi/{size}, 2*cos(theta) = {2.0*cos_theta:.6f}",
        f"  Coefficient (2.14 fixed-point): 2*cos(theta) = {two_cos_fp} "
        f"(${two_cos_fp & 0xFFFF:04X})",
        f"  Values in 8.8 fixed-point",
        f"  sin(0) = 0, sin(1) = {sin1_fp} (${sin1_fp & 0xFFFF:04X}) (8.8)",
        f"",
        f"Z80 reconstruction code:",
        f"  ; BC = sin(n-1) (8.8), DE = sin(n) (8.8)",
        f"  ; Constant: 2cos(theta) = ${two_cos_fp & 0xFFFF:04X} (2.14)",
        f"  ld bc, $0000           ; sin(0) = 0",
        f"  ld de, ${sin1_fp & 0xFFFF:04X}           ; sin(1) in 8.8",
        f".loop:",
        f"  ld a, d                ; high byte = integer sine value",
        f"  ; ... use A as sine value ...",
        f"  ; Compute sin(n+1) = 2cos(theta)*sin(n) - sin(n-1)",
        f"  push bc                ; save sin(n-1)",
        f"  ; multiply DE (8.8) by 2cos (2.14) -> 32-bit, shift >>14",
        f"  call mul_16x16_shr14   ; HL = (2cos * sin(n)) >> 14",
        f"  pop bc                 ; BC = sin(n-1)",
        f"  or a",
        f"  sbc hl, bc             ; HL = result - sin(n-1)",
        f"  ld b, d",
        f"  ld c, e                ; BC = old sin(n)",
        f"  ex de, hl              ; DE = new sin(n+1)",
        f"  djnz .loop",
        f"",
        f"Bytes needed: 4 (two 16-bit values: sin(1), 2*cos(theta))",
    ]
    header = format_asm_header(6, size, amplitude, unsigned, errors, extra)

    lines = [header]
    lines.append("sine_recursive_data:")
    lines.append(f"    DW  ${sin1_fp & 0xFFFF:04X}            "
                 f"; sin(1) in 8.8 fixed-point")
    lines.append(f"    DW  ${two_cos_fp & 0xFFFF:04X}            "
                 f"; 2*cos(2*pi/{size}) in 2.14 fixed-point")
    lines.append("")
    lines.append("; Reconstructed table for verification:")
    table = format_asm_table("sine_recursive", values, not unsigned)
    lines.append(table)
    return "\n".join(lines)


def generate_approach7_asm(size: int, amplitude: int, unsigned: bool) -> str:
    """Generate CORDIC assembly output."""
    values = approach7_cordic(size, amplitude, unsigned)
    errors = compute_errors(values, size, amplitude, unsigned)

    ITERATIONS = 14

    # Atan table as 16-bit angle values (0..65536 = 0..2π)
    ANGLE_SCALE = 65536.0 / (2.0 * math.pi)
    atan_table_rad = [math.atan(2.0 ** (-i)) for i in range(ITERATIONS)]
    atan_table_fp = [int(round(a * ANGLE_SCALE)) for a in atan_table_rad]

    # CORDIC gain
    K = 1.0
    for i in range(ITERATIONS):
        K *= math.cos(atan_table_rad[i])

    # 8.8 fixed-point initial x
    COORD_SCALE = 256
    init_x_fp = int(round(K * amplitude * COORD_SCALE))

    extra = [
        f"CORDIC iterative rotation ({ITERATIONS} iterations)",
        f"CORDIC gain K = {K:.6f}",
        f"Initial vector (8.8): x = ${init_x_fp & 0xFFFF:04X} "
        f"(= K*{amplitude} = {K*amplitude:.1f}), y = 0",
        f"Angles: 16-bit (0..65535 = 0..2*pi)",
        f"Coordinates: 8.8 fixed-point (16-bit signed)",
        f"",
        f"Arctan table (16-bit angle values):",
    ]
    for i, val in enumerate(atan_table_fp):
        deg = math.degrees(atan_table_rad[i])
        extra.append(
            f"  atan(2^-{i:2d}) = ${val:04X} ({val:5d})  ({deg:6.2f} deg)")

    extra += [
        f"",
        f"Z80 reconstruction code:",
        f"  ; For each target angle, pre-rotate if |angle| > 90 deg,",
        f"  ; then run {ITERATIONS} CORDIC iterations.",
        f"  ; Pre-rotation: if target > $4000, start with (0, init_x)",
        f"  ;               if target < $C000, start with (0, -init_x)",
        f"  ; Each iteration: compare angle vs target,",
        f"  ;   d = +1 if angle < target, else -1",
        f"  ;   x' = x - d*(y >> i)  (arithmetic shift)",
        f"  ;   y' = y + d*(x >> i)",
        f"  ;   angle += d * atan_table[i]",
        f"  ; Result: y >> 8 = sin(target_angle) * amplitude",
        f"",
        f"Data: {ITERATIONS * 2 + 2} bytes "
        f"({ITERATIONS} x 16-bit atan + 16-bit init_x)",
    ]
    header = format_asm_header(7, size, amplitude, unsigned, errors, extra)

    lines = [header]
    lines.append("cordic_atan_table:")
    for i in range(0, ITERATIONS, 4):
        chunk = atan_table_fp[i:i + 4]
        end = min(i + 3, ITERATIONS - 1)
        parts = [f"${v & 0xFFFF:04X}" for v in chunk]
        lines.append(
            f"    DW  {', '.join(parts)}  "
            f"; atan(2^-{i})..atan(2^-{end})")

    lines.append("")
    lines.append(f"cordic_init_x  DW  ${init_x_fp & 0xFFFF:04X}  "
                 f"; K * amplitude in 8.8 fixed-point")
    lines.append("")
    lines.append("; Reconstructed table for verification:")
    table = format_asm_table("sine_cordic", values, not unsigned)
    lines.append(table)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# C format output
# ---------------------------------------------------------------------------

def format_c_output(approach: int, values: list[int], size: int,
                    amplitude: int, unsigned: bool,
                    errors: ErrorStats) -> str:
    """Format output as C array."""
    mode = "unsigned" if unsigned else "signed"
    dtype = "uint8_t" if unsigned else "int8_t"
    lines = [
        f"/* Sine table — approach {approach} ({APPROACH_NAMES[approach]}), "
        f"{len(values)} entries, amplitude {amplitude} ({mode})",
        f" * Generated by sinetable.py (spectools)",
    ]
    if errors.max_err == 0:
        lines.append(f" * Max error: 0.000 (exact precomputed)")
    else:
        lines.append(
            f" * Max error: {errors.max_err:.3f} ({errors.max_pct:.3f}%), "
            f"RMS error: {errors.rms_err:.3f} ({errors.rms_pct:.3f}%)"
        )
    lines.append(f" */")
    lines.append(f"const {dtype} sine_table[{len(values)}] = {{")

    for i in range(0, len(values), 8):
        chunk = values[i:i + 8]
        parts = [f"{v:4d}" for v in chunk]
        comma = "," if i + 8 < len(values) else ""
        sep = ", ".join(parts)
        if i + 8 < len(values):
            lines.append(f"    {sep},  /* {i}-{i+len(chunk)-1} */")
        else:
            lines.append(f"    {sep}   /* {i}-{i+len(chunk)-1} */")
    lines.append(f"}};")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# JSON format output
# ---------------------------------------------------------------------------

def format_json_output(approach: int, values: list[int], size: int,
                       amplitude: int, unsigned: bool,
                       errors: ErrorStats) -> str:
    """Format output as JSON."""
    data = {
        "approach": approach,
        "approach_name": APPROACH_NAMES[approach],
        "size": len(values),
        "full_size": size,
        "amplitude": amplitude,
        "unsigned": unsigned,
        "max_error": round(errors.max_err, 4),
        "rms_error": round(errors.rms_err, 4),
        "max_error_pct": round(errors.max_pct, 4),
        "rms_error_pct": round(errors.rms_pct, 4),
        "values": values,
    }
    return json.dumps(data, indent=2)


# ---------------------------------------------------------------------------
# Top-level generation for each approach
# ---------------------------------------------------------------------------

def generate_values(approach: int, size: int, amplitude: int,
                    unsigned: bool) -> list[int]:
    """Generate the full-size value table for any approach (for comparison)."""
    if approach == 1:
        return approach1_full_lut(size, amplitude, unsigned)
    elif approach == 2:
        quarter = approach2_quarter_wave(size, amplitude, unsigned)
        return approach2_reconstruct(quarter, size, amplitude, unsigned)
    elif approach == 3:
        reconstructed, _, _, _, _ = approach3_delta_encoding(
            size, amplitude, unsigned)
        return reconstructed
    elif approach == 4:
        return approach4_parabolic(size, amplitude, unsigned)
    elif approach == 5:
        return approach5_bhaskara(size, amplitude, unsigned)
    elif approach == 6:
        return approach6_recursive(size, amplitude, unsigned)
    elif approach == 7:
        return approach7_cordic(size, amplitude, unsigned)
    else:
        raise ValueError(f"Unknown approach: {approach}")


def generate_output(approach: int, size: int, amplitude: int,
                    unsigned: bool, fmt: str) -> str:
    """Generate the formatted output for a given approach."""
    if fmt == "asm":
        if approach == 1:
            return generate_approach1_asm(size, amplitude, unsigned)
        elif approach == 2:
            return generate_approach2_asm(size, amplitude, unsigned)
        elif approach == 3:
            return generate_approach3_asm(size, amplitude, unsigned)
        elif approach == 4:
            return generate_approach4_asm(size, amplitude, unsigned)
        elif approach == 5:
            return generate_approach5_asm(size, amplitude, unsigned)
        elif approach == 6:
            return generate_approach6_asm(size, amplitude, unsigned)
        elif approach == 7:
            return generate_approach7_asm(size, amplitude, unsigned)
        else:
            raise ValueError(f"Unknown approach: {approach}")
    else:
        # For c and json, generate values and format
        values = generate_values(approach, size, amplitude, unsigned)
        errors = compute_errors(values, size, amplitude, unsigned)
        if fmt == "c":
            return format_c_output(approach, values, size, amplitude,
                                   unsigned, errors)
        elif fmt == "json":
            return format_json_output(approach, values, size, amplitude,
                                      unsigned, errors)
        else:
            raise ValueError(f"Unknown format: {fmt}")


# ---------------------------------------------------------------------------
# --compare mode
# ---------------------------------------------------------------------------

def estimate_bytes(approach: int, size: int) -> str:
    """Estimate storage bytes for each approach."""
    if approach == 1:
        return str(size)
    elif approach == 2:
        return str(size // 4 + 1)
    elif approach == 3:
        # 1 initial + size/4/2 packed nibble bytes
        return str(1 + size // 8)
    elif approach == 4:
        return "0"
    elif approach == 5:
        return "0"
    elif approach == 6:
        return "4"
    elif approach == 7:
        # 14 x 16-bit atan values + 16-bit init_x = 30 bytes
        return "30"
    return "?"


def approach_notes(approach: int) -> str:
    """Short notes for comparison table."""
    notes = {
        1: "Exact",
        2: "Exact (via symmetry)",
        3: "Nibble-packed, needs unpacker",
        4: "Formula only",
        5: "Formula only",
        6: "2 multiplies/step",
        7: "Iterative",
    }
    return notes.get(approach, "")


def run_compare(size: int, amplitude: int, unsigned: bool) -> str:
    """Run comparison of all approaches."""
    mode = "unsigned" if unsigned else "signed"
    lines = [
        f"Sine Table Approach Comparison (size={size}, "
        f"amplitude={amplitude}, {mode})",
        f"=" * 72,
        f"{'Approach':<10}{'Name':<25}{'Bytes':>6}  "
        f"{'Max Error':>10}  {'RMS Error':>10}  {'Notes'}",
        f"{'-'*10}{'-'*25}{'-'*6}  {'-'*10}  {'-'*10}  {'-'*20}",
    ]

    for approach in range(1, 8):
        values = generate_values(approach, size, amplitude, unsigned)
        errors = compute_errors(values, size, amplitude, unsigned)
        name = APPROACH_NAMES_LONG[approach]
        bytes_str = estimate_bytes(approach, size)
        notes = approach_notes(approach)

        if errors.max_err == 0:
            max_str = "0.000"
            rms_str = "0.000"
        else:
            max_str = f"{errors.max_pct:.3f}%"
            rms_str = f"{errors.rms_pct:.3f}%"

        lines.append(
            f"{approach:<10}{name:<25}{bytes_str:>6}  "
            f"{max_str:>10}  {rms_str:>10}  {notes}"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="sinetable",
        description="Sine Table Generator for Z80 Assembly Development. "
                    "Generates sine lookup tables using 7 different approaches, "
                    "from exact precomputed LUTs to compact approximation methods.",
        epilog="Examples:\n"
               "  %(prog)s --approach 1 --size 256 --amplitude 127\n"
               "  %(prog)s --approach 2 --size 256 --amplitude 127 --format c\n"
               "  %(prog)s --approach 5 --unsigned --amplitude 100\n"
               "  %(prog)s --compare\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--approach", "-a",
        type=int, choices=range(1, 8), default=1, metavar="N",
        help="Which approach to use (1-7). "
             "1=Full LUT, 2=Quarter-wave, 3=Delta encoding, "
             "4=Parabolic, 5=Bhaskara I, 6=Recursive, 7=CORDIC. "
             "Default: 1"
    )
    parser.add_argument(
        "--size", "-s",
        type=int, default=256, metavar="N",
        help="Table size in entries (default: 256). "
             "For approach 2, must be divisible by 4."
    )
    parser.add_argument(
        "--amplitude", "-A",
        type=int, default=127, metavar="N",
        help="Maximum amplitude value (default: 127, "
             "for signed byte range -127..127)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["asm", "c", "json"], default="asm",
        help="Output format (default: asm)"
    )
    parser.add_argument(
        "--unsigned", "-u",
        action="store_true",
        help="Output unsigned values (0..amplitude) "
             "instead of signed (-amplitude..+amplitude)"
    )
    parser.add_argument(
        "--compare", "-c",
        action="store_true",
        help="Compare all 7 approaches side by side. "
             "Ignores --approach flag."
    )

    args = parser.parse_args(argv)

    # Validation
    if args.size < 4:
        parser.error("--size must be at least 4")
    if args.approach == 2 and args.size % 4 != 0:
        parser.error("--size must be divisible by 4 for approach 2 "
                     "(quarter-wave)")
    if args.amplitude < 1:
        parser.error("--amplitude must be at least 1")
    if not args.unsigned and args.amplitude > 127:
        parser.error("--amplitude exceeds signed byte range (max 127). "
                     "Use --unsigned for larger values.")

    return args


def main(argv: list[str] | None = None) -> None:
    """Main entry point."""
    args = parse_args(argv)

    if args.compare:
        print(run_compare(args.size, args.amplitude, args.unsigned))
    else:
        output = generate_output(
            args.approach, args.size, args.amplitude,
            args.unsigned, args.format
        )
        print(output)


if __name__ == "__main__":
    main()
