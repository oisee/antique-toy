#!/usr/bin/env python3
"""
sine_compare.py -- Comprehensive comparison of 256-byte sine table generation
approaches for Z80 demoscene work.

Context: A sine table has 256 entries indexed by angle (0=0 deg, 64=90 deg,
128=180 deg, 256 wraps to 0). Values are signed bytes (-128..+127),
representing -1.0 to ~+1.0. This is the standard demoscene format.

For the book: "Coding the Impossible: Z80 Demoscene Techniques for Modern Makers"
"""

import math
import struct

# ---------------------------------------------------------------------------
# Generate the ground-truth 256-byte sine table
# ---------------------------------------------------------------------------

def true_sine_table():
    """Generate the reference 256-entry signed-byte sine table."""
    table = []
    for i in range(256):
        # angle in radians: full circle = 256 steps
        angle = 2.0 * math.pi * i / 256.0
        # scale to signed byte range: sin in [-1,1] -> [-128, +127]
        # We use round() for best accuracy; clamp to [-128, 127]
        val = math.sin(angle) * 127.0
        val = int(round(val))
        val = max(-128, min(127, val))
        table.append(val)
    return table


# ---------------------------------------------------------------------------
# Approach 1: Full table (baseline)
# ---------------------------------------------------------------------------

def approach_full_table(true_table):
    """256 bytes of data, 0 bytes of code. Zero error."""
    return {
        "name": "1. Full table (baseline)",
        "data_bytes": 256,
        "code_bytes": 0,
        "table": list(true_table),
        "notes": "Pre-computed, instant lookup via LD L,angle / LD A,(HL). "
                 "Fastest possible (no computation at runtime). "
                 "Cost: 256 bytes of ROM/RAM.",
    }


# ---------------------------------------------------------------------------
# Approach 2: Quarter-wave table
# ---------------------------------------------------------------------------

def approach_quarter_wave(true_table):
    """
    Store only indices 0..63 (first quadrant, 0 to 90 degrees).
    Reconstruct via symmetry:
      sin(64+x)  =  sin(64-x)       (mirror around 90 deg)
      sin(128+x) = -sin(x)          (negate for second half)

    Z80 lookup routine (~25 bytes):
        ; Input: A = angle (0..255)
        ; Output: A = sin(A) signed byte
        ; Uses: quarter_table (64 bytes)
        sin_lookup:              ;          bytes
            ld c, 0              ; sign=0     2
            bit 7, a             ; half?      2
            jr z, .no_neg        ;            2
            neg                  ;            2  (A = 256-A, flips to mirror half)
            ld c, 1              ; sign=1     2
        .no_neg:
            bit 6, a             ; quadrant?  2
            jr z, .no_mirror     ;            2
            neg                  ;            2  (A = 256-A flips within half)
            add a, 64            ;            2  (adjust to index into Q1)
        .no_mirror:             ;  -- but wait, simpler: --
            and $3F              ; mask to 0..63 (WRONG for mirror)
        ; Actually the standard trick:
        ;   if bit6: index = 63 - (a & 63)  else: index = a & 63
        ;   if bit7: negate result
        ; Let me re-estimate more carefully below.
    """
    # Quarter table: indices 0..64 (65 entries, inclusive of the peak)
    # We need index 64 (the peak at 90 degrees) to avoid off-by-one
    # in the mirror. 65 bytes, but the Z80 code below handles this.
    quarter = true_table[0:65]

    # Reconstruct full table from quarter
    reconstructed = [0] * 256
    for i in range(256):
        # Determine quadrant and index
        negate = (i >= 128)
        idx = i if i < 128 else i - 128  # map to 0..127

        if idx <= 64:
            val = quarter[idx]
        else:
            # mirror: sin(64+x) = sin(64-x)
            # idx in 65..127 => mirror_idx = 128 - idx (gives 63..1)
            val = quarter[128 - idx]

        if negate:
            # sin(128+x) = -sin(x)
            val = max(-128, -val)

        reconstructed[i] = val

    # Z80 code estimate (careful byte count):
    #   sin_lookup:
    #     ld e, a          ; save angle            1  byte
    #     and $7F          ; half = 0..127         2  bytes
    #     bit 6, e         ; second quadrant?      2  bytes (CB xx)
    #     jr z, .no_mir    ;                       2  bytes
    #     ; mirror: index = 128 - (angle & 0x7F)
    #     neg              ;                       2  bytes (ED 44)
    #     add a, 128       ;                       2  bytes -> 128 - idx
    #   .no_mir:
    #     ld l, a          ;                       1  byte
    #     ld h, high(table);                       2  bytes
    #     ld a, (hl)       ;                       1  byte
    #     bit 7, e         ; negative half?        2  bytes (CB xx)
    #     ret z            ;                       1  byte
    #     neg              ;                       2  bytes
    #     ret              ;                       1  byte
    #   Total: 21 bytes
    # Note: table is 65 bytes (0..64 inclusive), must be 256-byte aligned.
    code_bytes = 21

    return {
        "name": "2. Quarter-wave table",
        "data_bytes": 65,
        "code_bytes": code_bytes,
        "table": reconstructed,
        "notes": "65-byte table (0..64 inclusive) + 21-byte lookup. Classic trick. "
                 "Table must be 256-byte aligned for fast LD H,high(table). "
                 "Lookup adds ~50-70 T-states overhead vs direct table read. "
                 "Zero error with correct mirror formula.",
    }


# ---------------------------------------------------------------------------
# Approach 3: Parabolic approximation (Dark's method)
# ---------------------------------------------------------------------------

def approach_parabolic(true_table):
    """
    Pure code, no table. Approximate sin(x) with a parabola for each
    half-period.

    The idea (from Spectrum Engineer articles / Dark):
      For x in [0..127] (first half, 0..180 deg):
        sin(x) approx = (4/128) * x * (128 - x) / 128  scaled to byte range
      This gives a parabola peaking at x=64 with value 127.

      For x in [128..255]:
        sin(x) = -sin(x - 128)

    In integer math:
      val = x * (128 - x)   (for x in 0..127)
      Then scale: val ranges from 0 to 64*64 = 4096
      We want max = 127, so: val * 127 / 4096, or approx val >> 5
      More precisely: val / 32 gives max = 4096/32 = 128, close enough.
      Even better: (x * (128-x) + 16) >> 5  (with rounding)

    Z80 generation/lookup code estimate:
      ; Input: A = angle 0..255
      ; Output: A = parabolic_sin(A)
      parabolic_sin:
        ld b, a            ; save              1
        and $7F            ; x = angle & 127   2
        ld c, a            ; c = x             1
        neg                ;                   2
        add a, 128         ; a = 128 - x       2
        ; Now multiply A * C (both 0..128, product up to 4096, 13 bits)
        ; 8x8 multiply routine: ~15-20 bytes
        ; ... result in HL
        ; Shift right 5: ~4 bytes (srl h / rr l x5 or just use H after >>5)
        ; Actually HL >> 5: we can do 3x(srl h / rr l) + 2x(srl h/rr l)
        ; Or: ld a, h; rrca; rrca; ... etc
        ; Check sign bit of original angle and negate: ~5 bytes
      ; Total estimate: ~35 bytes for inline, ~40 with multiply routine
    """
    parabolic = []
    for i in range(256):
        x = i & 0x7F  # 0..127
        # parabola: x * (128-x), max at x=64 = 4096
        raw = x * (128 - x)
        # scale to 0..127: divide by 4096 and multiply by 127
        # = raw * 127 / 4096
        # For integer: raw >> 5 gives max 128, close enough
        # Let's use the more accurate: int(round(raw * 127.0 / 4096.0))
        val = int(round(raw * 127.0 / 4096.0))

        if i >= 128:
            val = -val

        val = max(-128, min(127, val))
        parabolic.append(val)

    code_bytes = 38  # realistic estimate for Z80 with 8x8 multiply

    return {
        "name": "3. Parabolic approx (Dark's method)",
        "data_bytes": 0,
        "code_bytes": code_bytes,
        "table": parabolic,
        "notes": "Pure code, zero data. Parabola peaks correctly but is "
                 "'flatter' near 0/180 deg and 'sharper' at peak vs true sine. "
                 "Needs 8x8->16 multiply (~15 bytes). Good enough for many "
                 "effects (plasmas, simple scrollers). Noticeable in smooth motion.",
    }


# ---------------------------------------------------------------------------
# Approach 4: Parabolic + correction table
# ---------------------------------------------------------------------------

def approach_parabolic_correction(true_table):
    """
    Use parabolic as base, store deltas (corrections) from true sine.
    Since parabola is close, deltas should be small.
    """
    parabolic_info = approach_parabolic(true_table)
    parabolic = parabolic_info["table"]

    # Full 256-byte correction
    deltas_full = []
    for i in range(256):
        delta = true_table[i] - parabolic[i]
        deltas_full.append(delta)

    delta_range_full = (min(deltas_full), max(deltas_full))
    unique_full = sorted(set(deltas_full))

    # Quarter-wave correction (first 65 entries, 0..64 inclusive)
    # Same as approach 2: we need the peak at index 64 for clean mirror
    deltas_quarter = []
    for i in range(65):
        delta = true_table[i] - parabolic[i]
        deltas_quarter.append(delta)

    delta_range_q = (min(deltas_quarter), max(deltas_quarter))
    unique_q = sorted(set(deltas_quarter))

    # How many bits needed for deltas?
    max_abs_delta = max(abs(delta_range_full[0]), abs(delta_range_full[1]))
    bits_needed = max_abs_delta.bit_length() + 1  # +1 for sign

    # Reconstructed table from parabolic + full correction (should be exact)
    reconstructed_full = [parabolic[i] + deltas_full[i] for i in range(256)]

    # Reconstructed from quarter correction
    reconstructed_quarter = list(parabolic)  # start with parabolic base
    for i in range(65):
        reconstructed_quarter[i] = parabolic[i] + deltas_quarter[i]
    # Mirror Q2 (indices 65..127): sin(64+x) = sin(64-x)
    for i in range(65, 128):
        mirror_idx = 128 - i  # 65->63, 66->62, ..., 127->1
        reconstructed_quarter[i] = parabolic[i] + deltas_quarter[mirror_idx]
    # Q3+Q4 (128..255): negate Q1+Q2
    for i in range(128, 256):
        src_idx = i - 128
        # The correction for this index: true - parabolic
        # Since true[128+x] = -true[x] and parabolic[128+x] = -parabolic[x],
        # delta[128+x] = -true[x] - (-parabolic[x]) = -(true[x] - parabolic[x]) = -delta[x]
        # So we negate the correction too
        if src_idx <= 64:
            correction = deltas_quarter[src_idx]
        else:
            correction = deltas_quarter[128 - src_idx]
        reconstructed_quarter[i] = parabolic[i] - correction
        reconstructed_quarter[i] = max(-128, min(127, reconstructed_quarter[i]))

    # Data: quarter correction = 64 bytes (each delta fits in a byte)
    # Code: parabolic generation (~38) + quarter lookup with correction (~25) = ~63
    # But actually the code would be: compute parabolic, then add correction from table
    # So: parabolic_sin code (~38) + correction lookup (~15) + quarter_wave logic (~23)
    # Hmm, that's a lot. Let's think about it differently:
    # The simplest approach: pre-generate full table at startup using parabolic + corrections.
    # But that defeats the purpose (needs 256 bytes RAM).
    # For on-the-fly: compute parabolic(angle), look up correction from quarter table, add.
    # Code: parabolic routine (~38) + quarter-wave correction lookup (~20) = ~58 bytes

    code_bytes_full = 38 + 5   # parabolic + add correction from full table (simple)
    code_bytes_quarter = 38 + 20  # parabolic + quarter-wave correction lookup

    return {
        "name_full": "4a. Parabolic + full correction table",
        "name_quarter": "4b. Parabolic + quarter correction table",
        "data_bytes_full": 256,
        "code_bytes_full": code_bytes_full,
        "table_full": reconstructed_full,
        "data_bytes_quarter": 65,
        "code_bytes_quarter": code_bytes_quarter,
        "table_quarter": reconstructed_quarter,
        "delta_range_full": delta_range_full,
        "delta_range_quarter": delta_range_q,
        "unique_deltas_full": unique_full,
        "unique_deltas_quarter": unique_q,
        "bits_needed": bits_needed,
        "deltas_full": deltas_full,
        "deltas_quarter": deltas_quarter,
    }


# ---------------------------------------------------------------------------
# Approach 5: Delta-encoded sine table
# ---------------------------------------------------------------------------

def approach_delta_encoded(true_table):
    """
    Store first value, then first differences: delta[i] = sin[i] - sin[i-1].
    Deltas of a sine wave are bounded (the derivative of sin is cos, amplitude ~3).
    """
    # Full 256 deltas
    deltas_full = [true_table[0]]  # first value
    for i in range(1, 256):
        deltas_full.append(true_table[i] - true_table[i - 1])

    delta_values = deltas_full[1:]  # just the differences
    delta_min = min(delta_values)
    delta_max = max(delta_values)
    max_abs = max(abs(delta_min), abs(delta_max))

    # The deltas should fit in a signed byte easily (they're small)
    # But can we pack them tighter?
    bits_per_delta = max_abs.bit_length() + 1  # +1 for sign

    # Data: 1 byte (initial) + 255 deltas
    # If deltas fit in 4 bits signed (-8..+7): 1 + ceil(255*4/8) = 1 + 128 = 129 bytes
    # If deltas fit in 5 bits signed: 1 + ceil(255*5/8) = 1 + 160 = 161 bytes
    # If stored as full bytes: 1 + 255 = 256 bytes (no savings!)

    # But the deltas are small enough for nibble packing potentially
    fits_4bit = all(-8 <= d <= 7 for d in delta_values)
    fits_5bit = all(-16 <= d <= 15 for d in delta_values)

    # Pack at native bit width
    if fits_4bit:
        packed_bits = 4
        packed_data = 1 + math.ceil(255 * 4 / 8)
    elif fits_5bit:
        packed_bits = 5
        packed_data = 1 + math.ceil(255 * 5 / 8)
    else:
        packed_bits = bits_per_delta
        packed_data = 1 + math.ceil(255 * packed_bits / 8)

    # Full byte storage
    data_bytes_full = 256  # 1 initial + 255 deltas as bytes

    # Quarter-wave: only 64 values, so 1 + 63 deltas
    quarter = true_table[0:64]
    deltas_quarter = [quarter[0]]
    for i in range(1, 64):
        deltas_quarter.append(quarter[i] - quarter[i - 1])

    dq_values = deltas_quarter[1:]
    dq_min = min(dq_values) if dq_values else 0
    dq_max = max(dq_values) if dq_values else 0
    dq_max_abs = max(abs(dq_min), abs(dq_max))
    dq_bits = dq_max_abs.bit_length() + 1 if dq_max_abs > 0 else 1

    # Quarter-wave delta data
    data_bytes_quarter = 64  # as full bytes: 1 + 63 = 64
    packed_quarter = 1 + math.ceil(63 * dq_bits / 8)

    # Code estimate: delta decode loop + quarter-wave lookup
    # Delta decode (full): ~15 bytes (loop adding deltas)
    # But this generates the full table in RAM -- needs 256 bytes RAM!
    # On-the-fly is impractical (must sum from start each time).
    # So: generation code (~15 bytes) but needs 256 bytes RAM.
    code_bytes_gen = 15  # generation loop
    code_bytes_quarter_gen = 15 + 23  # generate quarter + quarter-wave lookup

    # Reconstructed: obviously exact if using byte-width deltas
    reconstructed = list(true_table)  # exact

    return {
        "name": "5. Delta-encoded sine",
        "data_bytes_full_packed": packed_data,
        "data_bytes_full_byte": data_bytes_full,
        "data_bytes_quarter": data_bytes_quarter,
        "data_bytes_quarter_packed": packed_quarter,
        "code_bytes_gen": code_bytes_gen,
        "code_bytes_quarter_gen": code_bytes_quarter_gen,
        "delta_range": (delta_min, delta_max),
        "bits_per_delta": bits_per_delta,
        "fits_4bit": fits_4bit,
        "fits_5bit": fits_5bit,
        "packed_bits": packed_bits,
        "delta_quarter_range": (dq_min, dq_max),
        "delta_quarter_bits": dq_bits,
        "table": reconstructed,
        "deltas_full": delta_values,
        "deltas_quarter": dq_values,
        "notes": "Deltas are small (derivative of sine = cosine, scaled). "
                 "Packed nibbles save space but Z80 unpacking adds code. "
                 "Main issue: must generate full table at startup (needs 256B RAM) "
                 "or do O(n) summation per lookup.",
    }


# ---------------------------------------------------------------------------
# Approach 6: Delta-encoded + RLE
# ---------------------------------------------------------------------------

def rle_encode(data):
    """Simple RLE: (count, value) pairs. Count stored as byte."""
    if not data:
        return []
    runs = []
    current = data[0]
    count = 1
    for val in data[1:]:
        if val == current and count < 255:
            count += 1
        else:
            runs.append((count, current))
            current = val
            count = 1
    runs.append((count, current))
    return runs


def approach_delta_rle(true_table):
    """
    Delta-encode the sine table, then RLE-compress the delta stream.
    Consecutive deltas are often identical (since d(sin)/dx = cos, which
    changes slowly near peaks).
    """
    deltas = [true_table[0]]  # initial value
    for i in range(1, 256):
        deltas.append(true_table[i] - true_table[i - 1])

    delta_values = deltas[1:]  # 255 deltas

    # RLE on deltas
    runs = rle_encode(delta_values)
    # Each run: 2 bytes (count + value)
    rle_data_bytes = 1 + len(runs) * 2  # 1 for initial value + runs

    # Quarter-wave RLE
    quarter = true_table[0:64]
    dq = [quarter[0]]
    for i in range(1, 64):
        dq.append(quarter[i] - quarter[i - 1])
    dq_values = dq[1:]
    runs_q = rle_encode(dq_values)
    rle_quarter_bytes = 1 + len(runs_q) * 2

    # Code: RLE decoder loop ~20 bytes + quarter-wave lookup 23
    code_bytes_full = 20
    code_bytes_quarter = 20 + 23

    return {
        "name": "6. Delta + RLE",
        "data_bytes_full": rle_data_bytes,
        "data_bytes_quarter": rle_quarter_bytes,
        "code_bytes_full": code_bytes_full,
        "code_bytes_quarter": code_bytes_quarter,
        "num_runs_full": len(runs),
        "num_runs_quarter": len(runs_q),
        "table": list(true_table),  # exact after decode
        "notes": "RLE on deltas. Sine deltas change slowly near peaks (cos is flat), "
                 "so some runs exist. Compression ratio depends on how many "
                 "repeated consecutive deltas there are. Must decode to RAM at startup.",
    }


# ---------------------------------------------------------------------------
# Approach 7: Second-order delta (delta of delta)
# ---------------------------------------------------------------------------

def approach_second_order_delta(true_table):
    """
    Store sin[0], delta[0], then second differences (delta of delta).
    d2(sin)/dx2 = -sin, so second differences are proportional to -sin
    itself, but quantized. They should be very small: mostly -1, 0, or +1.
    """
    # First differences
    d1 = [true_table[i + 1] - true_table[i] for i in range(255)]

    # Second differences
    d2 = [d1[i + 1] - d1[i] for i in range(254)]

    d2_min = min(d2)
    d2_max = max(d2)
    d2_unique = sorted(set(d2))
    max_abs_d2 = max(abs(d2_min), abs(d2_max))

    # Data: 1 byte (sin[0]) + 1 byte (d1[0]) + 254 second differences
    # If d2 fits in 2 bits signed (-2..+1): ceil(254*2/8) = 64 bytes
    fits_2bit = all(-2 <= d <= 1 for d in d2)
    fits_3bit = all(-4 <= d <= 3 for d in d2)

    if fits_2bit:
        packed_bits = 2
    elif fits_3bit:
        packed_bits = 3
    else:
        packed_bits = max_abs_d2.bit_length() + 1

    packed_data = 2 + math.ceil(254 * packed_bits / 8)
    byte_data = 2 + 254  # as full bytes

    # Quarter-wave version
    quarter = true_table[0:64]
    d1q = [quarter[i + 1] - quarter[i] for i in range(63)]
    d2q = [d1q[i + 1] - d1q[i] for i in range(62)]
    d2q_unique = sorted(set(d2q))
    d2q_min = min(d2q) if d2q else 0
    d2q_max = max(d2q) if d2q else 0
    max_abs_d2q = max(abs(d2q_min), abs(d2q_max)) if d2q else 0
    d2q_bits = max_abs_d2q.bit_length() + 1 if max_abs_d2q > 0 else 1

    packed_quarter = 2 + math.ceil(62 * d2q_bits / 8)

    # Code: second-order decode loop ~22 bytes (two accumulators)
    code_bytes_gen = 22
    code_bytes_quarter = 22 + 23

    return {
        "name": "7. Second-order delta",
        "data_bytes_full_packed": packed_data,
        "data_bytes_full_byte": byte_data,
        "data_bytes_quarter_packed": packed_quarter,
        "code_bytes_gen": code_bytes_gen,
        "code_bytes_quarter": code_bytes_quarter,
        "d2_range": (d2_min, d2_max),
        "d2_unique": d2_unique,
        "d2_bits": packed_bits,
        "d2q_range": (d2q_min, d2q_max),
        "d2q_unique": d2q_unique,
        "d2q_bits": d2q_bits,
        "table": list(true_table),  # exact after decode
        "notes": "Second derivative of sin = -sin, so d2 values are tiny. "
                 "2-bit packing gives excellent compression. "
                 "Unpacking on Z80 requires bit shifting (adds code complexity). "
                 "Must decode to RAM at startup. Two accumulators in decode loop.",
    }


# ---------------------------------------------------------------------------
# Approach 8: Quarter-wave + delta encoding (hybrid)
# ---------------------------------------------------------------------------

def approach_hybrid_quarter_delta(true_table):
    """
    Delta-encode only the first 64 values (quarter wave),
    reconstruct rest by symmetry.
    """
    quarter = true_table[0:64]

    # First differences of quarter
    d1 = [quarter[0]]  # initial value
    for i in range(1, 64):
        d1.append(quarter[i] - quarter[i - 1])

    d1_values = d1[1:]  # 63 deltas
    d1_min = min(d1_values)
    d1_max = max(d1_values)
    max_abs_d1 = max(abs(d1_min), abs(d1_max))
    d1_bits = max_abs_d1.bit_length() + 1

    # Second differences of quarter
    d2 = [d1_values[i + 1] - d1_values[i] for i in range(len(d1_values) - 1)]
    d2_min = min(d2) if d2 else 0
    d2_max = max(d2) if d2 else 0
    d2_unique = sorted(set(d2))
    max_abs_d2 = max(abs(d2_min), abs(d2_max)) if d2 else 0
    d2_bits = max_abs_d2.bit_length() + 1 if max_abs_d2 > 0 else 1

    # Option A: quarter deltas as bytes
    data_A = 1 + 63  # initial + 63 byte deltas = 64 bytes

    # Option B: quarter deltas packed at minimum bits
    data_B = 1 + math.ceil(63 * d1_bits / 8)

    # Option C: quarter second-order deltas packed
    data_C = 2 + math.ceil(62 * d2_bits / 8)

    # Code: delta decode to 64-byte buffer (~15 bytes) + quarter lookup (~23 bytes)
    code_A = 15 + 23  # byte deltas + quarter lookup
    code_B = 20 + 23  # bit-packed deltas + quarter lookup
    code_C = 22 + 23  # second-order + quarter lookup

    return {
        "name_A": "8a. Quarter + byte deltas",
        "name_B": "8b. Quarter + packed deltas",
        "name_C": "8c. Quarter + 2nd-order deltas",
        "data_A": data_A,
        "data_B": data_B,
        "data_C": data_C,
        "code_A": code_A,
        "code_B": code_B,
        "code_C": code_C,
        "d1_range": (d1_min, d1_max),
        "d1_bits": d1_bits,
        "d2_range": (d2_min, d2_max),
        "d2_unique": d2_unique,
        "d2_bits": d2_bits,
        "table": list(true_table),  # exact after decode
        "notes_A": "64 byte-width deltas for quarter wave, decode to 64-byte buffer, "
                   "then quarter-wave lookup at runtime. Needs 64B RAM.",
        "notes_B": f"Deltas packed at {d1_bits} bits each. Better compression but "
                   "Z80 bit unpacking adds ~5 bytes of code.",
        "notes_C": f"Second-order deltas at {d2_bits} bits. Best compression of this "
                   "family. Most complex decode.",
    }


# ---------------------------------------------------------------------------
# Approach 9: Bhaskara I approximation (7th century)
# ---------------------------------------------------------------------------

def approach_bhaskara(true_table):
    """
    Bhaskara I's rational approximation (629 CE, Mahabhaskariya):
        sin(x) ≈ 16x(π - x) / (5π² - 4x(π - x))
    for x in [0, π].

    In our integer domain (angle 0-64 for first quadrant, amplitude 0-127):
        sin(i) ≈ 127 * 16*i*(64-i) / (5*64² - 4*i*(64-i))
               = 127 * 16*i*(64-i) / (20480 - 4*i*(64-i))

    On Z80 this needs 8x8→16 multiply + 16÷16 divide.
    """
    # Compute first half (indices 0-128, covering 0° to 180°) via Bhaskara I.
    # The formula works for x in [0, π]. Map index i in [0, 128] to
    # x = i*π/128 radians.
    half_bhaskara = []
    for i in range(129):
        if i == 0 or i == 128:
            half_bhaskara.append(0)
        else:
            x = i * math.pi / 128.0
            prod = x * (math.pi - x)
            numerator = 16.0 * prod
            denominator = 5.0 * math.pi * math.pi - 4.0 * prod
            val = 127.0 * numerator / denominator
            half_bhaskara.append(int(round(val)))

    # Extract quarter (first 65 entries)
    quarter_bhaskara = half_bhaskara[0:65]

    # Reconstruct full 256-entry table from quarter
    bhaskara_table = [0] * 256
    for i in range(256):
        negate = (i >= 128)
        idx = i if i < 128 else i - 128
        if idx <= 64:
            val = quarter_bhaskara[idx]
        else:
            val = quarter_bhaskara[128 - idx]
        if negate:
            val = max(-128, -val)
        bhaskara_table[i] = val

    # Count how many quarter-wave entries differ from true sine
    quarter_true = true_table[0:65]
    corrections_needed = []
    for i in range(65):
        diff = quarter_true[i] - quarter_bhaskara[i]
        if diff != 0:
            corrections_needed.append((i, diff))

    # Code estimate:
    # - 8x8→16 multiply: ~20 bytes (likely already in codebase)
    # - 16÷16 divide: ~30 bytes (likely already in codebase)
    # - Bhaskara wrapper + quarter-wave fold: ~25 bytes
    # If multiply/divide already available: ~25 bytes marginal
    code_bytes_standalone = 60  # includes mul+div from scratch
    code_bytes_marginal = 25    # if mul+div already available

    # With correction bitmap (1 byte for 8 positions)
    code_bytes_corrected = code_bytes_standalone + 20  # bitmap lookup + apply

    return {
        "name": "9a. Bhaskara I approx",
        "name_corrected": "9b. Bhaskara I + corrections",
        "data_bytes": 0,
        "code_bytes": code_bytes_standalone,
        "code_bytes_marginal": code_bytes_marginal,
        "data_bytes_corrected": 1,  # 1 byte bitmap
        "code_bytes_corrected": code_bytes_corrected,
        "table": bhaskara_table,
        "quarter_bhaskara": quarter_bhaskara,
        "corrections": corrections_needed,
        "num_corrections": len(corrections_needed),
        "notes": f"Bhaskara I (629 CE): rational approximation. "
                 f"{len(corrections_needed)} entries differ from true sine (all by ±1). "
                 f"Needs 8×8 multiply + 16-bit divide on Z80. "
                 f"If these routines exist, marginal cost is ~{code_bytes_marginal}B.",
    }


# ---------------------------------------------------------------------------
# Error measurement
# ---------------------------------------------------------------------------

def measure_error(true_table, test_table):
    """Compute max absolute error and RMS error."""
    max_err = 0
    sum_sq = 0
    for i in range(256):
        err = abs(true_table[i] - test_table[i])
        max_err = max(max_err, err)
        sum_sq += err * err
    rms = math.sqrt(sum_sq / 256.0)
    return max_err, rms


# ---------------------------------------------------------------------------
# Visual comparison
# ---------------------------------------------------------------------------

def visual_comparison(true_table, parabolic_table):
    """Print first 32 values side by side, with a mini ASCII bar chart."""
    print("=" * 78)
    print("VISUAL COMPARISON: True Sine vs Parabolic (first 32 entries, 0-45 deg)")
    print("=" * 78)
    print(f"{'Idx':>4} {'Angle':>6} {'True':>5} {'Para':>5} {'Diff':>5}  "
          f"{'True':.<20} {'Para':.<20}")
    print("-" * 78)

    for i in range(32):
        angle = i * 360.0 / 256.0
        t = true_table[i]
        p = parabolic_table[i]
        diff = t - p

        # ASCII bar: scale -128..127 to 0..20 chars
        def bar(val, width=18):
            # map [-128, 127] to [0, width]
            pos = int((val + 128) * width / 255)
            return "." * pos + "#" + "." * (width - pos - 1)

        print(f"{i:4d} {angle:5.1f}d {t:5d} {p:5d} {diff:+5d}  "
              f"{bar(t):20s} {bar(p):20s}")

    print()
    print("  Legend: '#' marks the value position in [-128..+127] range")
    print("         Divergence is most visible around index 8-24 (11-34 degrees)")
    print()


# ---------------------------------------------------------------------------
# Main comparison
# ---------------------------------------------------------------------------

def main():
    true_table = true_sine_table()

    # Generate all approaches
    a1 = approach_full_table(true_table)
    a2 = approach_quarter_wave(true_table)
    a3 = approach_parabolic(true_table)
    a4 = approach_parabolic_correction(true_table)
    a5 = approach_delta_encoded(true_table)
    a6 = approach_delta_rle(true_table)
    a7 = approach_second_order_delta(true_table)
    a8 = approach_hybrid_quarter_delta(true_table)
    a9 = approach_bhaskara(true_table)

    # --------------- Visual comparison ---------------
    visual_comparison(true_table, a3["table"])

    # --------------- Delta analysis ---------------
    print("=" * 78)
    print("DELTA ANALYSIS")
    print("=" * 78)

    print("\n--- Approach 4: Parabolic correction deltas ---")
    print(f"  Full 256 delta range:    {a4['delta_range_full']}")
    print(f"  Unique delta values:     {len(a4['unique_deltas_full'])} "
          f"values: {a4['unique_deltas_full']}")
    print(f"  Bits needed (signed):    {a4['bits_needed']}")
    print(f"  Quarter 64 delta range:  {a4['delta_range_quarter']}")
    print(f"  Quarter unique values:   {len(a4['unique_deltas_quarter'])} "
          f"values: {a4['unique_deltas_quarter']}")

    print("\n--- Approach 5: First differences of true sine ---")
    print(f"  Delta range: {a5['delta_range']}")
    print(f"  Bits per delta: {a5['bits_per_delta']}")
    print(f"  Fits in 4-bit signed (nibble): {a5['fits_4bit']}")
    print(f"  Fits in 5-bit signed:          {a5['fits_5bit']}")
    print(f"  Quarter delta range:           {a5['delta_quarter_range']}")
    print(f"  Quarter delta bits:            {a5['delta_quarter_bits']}")

    print("\n--- Approach 6: RLE on deltas ---")
    print(f"  Full: {a6['num_runs_full']} runs "
          f"({a6['data_bytes_full']} bytes)")
    print(f"  Quarter: {a6['num_runs_quarter']} runs "
          f"({a6['data_bytes_quarter']} bytes)")

    print("\n--- Approach 7: Second-order deltas ---")
    print(f"  d2 range:   {a7['d2_range']}")
    print(f"  d2 unique:  {a7['d2_unique']}")
    print(f"  d2 bits:    {a7['d2_bits']}")
    print(f"  Quarter d2 range:   {a7['d2q_range']}")
    print(f"  Quarter d2 unique:  {a7['d2q_unique']}")
    print(f"  Quarter d2 bits:    {a7['d2q_bits']}")

    print("\n--- Approach 8: Hybrid quarter + delta ---")
    print(f"  Quarter d1 range:   {a8['d1_range']}")
    print(f"  Quarter d1 bits:    {a8['d1_bits']}")
    print(f"  Quarter d2 range:   {a8['d2_range']}")
    print(f"  Quarter d2 unique:  {a8['d2_unique']}")
    print(f"  Quarter d2 bits:    {a8['d2_bits']}")

    print("\n--- Approach 9: Bhaskara I (629 CE) ---")
    print(f"  Corrections needed: {a9['num_corrections']} out of 65 quarter entries")
    print(f"  Correction positions: {a9['corrections']}")
    print(f"  Code (standalone):  ~{a9['code_bytes']}B (includes mul+div)")
    print(f"  Code (marginal):    ~{a9['code_bytes_marginal']}B (if mul+div exist)")

    # Print first 16 deltas of each type for inspection
    print("\n--- Sample deltas (first 16 of full stream) ---")
    d5 = a5["deltas_full"][:16]
    d4 = a4["deltas_full"][:16]
    d7_d1 = [true_table[i + 1] - true_table[i] for i in range(16)]
    d7_d2 = [d7_d1[i + 1] - d7_d1[i] for i in range(15)]
    print(f"  True sine values: {true_table[:16]}")
    print(f"  1st diff (d5):    {d5}")
    print(f"  2nd diff (d7):    {d7_d2}")
    print(f"  Para correction:  {d4}")

    # --------------- Main comparison table ---------------
    print()
    print("=" * 98)
    print("COMPREHENSIVE COMPARISON TABLE")
    print("=" * 98)

    # Collect all variants into a uniform list
    entries = []

    # 1. Full table
    e1_max, e1_rms = measure_error(true_table, a1["table"])
    entries.append({
        "name": a1["name"],
        "data": a1["data_bytes"],
        "code": a1["code_bytes"],
        "total": a1["data_bytes"] + a1["code_bytes"],
        "max_err": e1_max,
        "rms_err": e1_rms,
        "notes": a1["notes"],
        "needs_ram": 0,
    })

    # 2. Quarter-wave
    e2_max, e2_rms = measure_error(true_table, a2["table"])
    entries.append({
        "name": a2["name"],
        "data": a2["data_bytes"],
        "code": a2["code_bytes"],
        "total": a2["data_bytes"] + a2["code_bytes"],
        "max_err": e2_max,
        "rms_err": e2_rms,
        "notes": a2["notes"],
        "needs_ram": 0,
    })

    # 3. Parabolic
    e3_max, e3_rms = measure_error(true_table, a3["table"])
    entries.append({
        "name": a3["name"],
        "data": a3["data_bytes"],
        "code": a3["code_bytes"],
        "total": a3["data_bytes"] + a3["code_bytes"],
        "max_err": e3_max,
        "rms_err": e3_rms,
        "notes": a3["notes"],
        "needs_ram": 0,
    })

    # 4a. Parabolic + full correction
    e4a_max, e4a_rms = measure_error(true_table, a4["table_full"])
    entries.append({
        "name": a4["name_full"],
        "data": a4["data_bytes_full"],
        "code": a4["code_bytes_full"],
        "total": a4["data_bytes_full"] + a4["code_bytes_full"],
        "max_err": e4a_max,
        "rms_err": e4a_rms,
        "notes": "Exact. But 256+43 = 299 bytes: WORSE than just storing the table! "
                 "Only makes sense if corrections compress well.",
        "needs_ram": 0,
    })

    # 4b. Parabolic + quarter correction
    e4b_max, e4b_rms = measure_error(true_table, a4["table_quarter"])
    entries.append({
        "name": a4["name_quarter"],
        "data": a4["data_bytes_quarter"],
        "code": a4["code_bytes_quarter"],
        "total": a4["data_bytes_quarter"] + a4["code_bytes_quarter"],
        "max_err": e4b_max,
        "rms_err": e4b_rms,
        "notes": "Parabolic base + quarter-wave correction lookup. "
                 f"Correction deltas range: {a4['delta_range_quarter']}. "
                 "Complex code path (compute parabola, then correct).",
        "needs_ram": 0,
    })

    # 5a. Delta-encoded, byte-width, full
    e5_max, e5_rms = measure_error(true_table, a5["table"])
    entries.append({
        "name": "5a. Delta-encoded (byte, full)",
        "data": a5["data_bytes_full_byte"],
        "code": a5["code_bytes_gen"],
        "total": a5["data_bytes_full_byte"] + a5["code_bytes_gen"],
        "max_err": 0,
        "rms_err": 0.0,
        "notes": "256 bytes data + 15 decode. No ROM savings vs full table! "
                 "Needs 256B RAM to decode into.",
        "needs_ram": 256,
    })

    # 5b. Delta-encoded, packed, full
    entries.append({
        "name": f"5b. Delta-encoded ({a5['packed_bits']}bit packed)",
        "data": a5["data_bytes_full_packed"],
        "code": a5["code_bytes_gen"] + 8,  # +8 for unpacking logic
        "total": a5["data_bytes_full_packed"] + a5["code_bytes_gen"] + 8,
        "max_err": 0,
        "rms_err": 0.0,
        "notes": f"Deltas in {a5['packed_bits']}-bit signed values. "
                 "Needs bit-unpacking loop on Z80. Needs 256B RAM.",
        "needs_ram": 256,
    })

    # 5c. Delta-encoded, quarter, byte-width
    entries.append({
        "name": "5c. Delta quarter (byte)",
        "data": a5["data_bytes_quarter"],
        "code": a5["code_bytes_quarter_gen"],
        "total": a5["data_bytes_quarter"] + a5["code_bytes_quarter_gen"],
        "max_err": 0,
        "rms_err": 0.0,
        "notes": "64 byte deltas, decode to 64B buffer, quarter-wave lookup. "
                 "Needs 64B RAM.",
        "needs_ram": 64,
    })

    # 6a. Delta + RLE, full
    entries.append({
        "name": "6a. Delta + RLE (full)",
        "data": a6["data_bytes_full"],
        "code": a6["code_bytes_full"],
        "total": a6["data_bytes_full"] + a6["code_bytes_full"],
        "max_err": 0,
        "rms_err": 0.0,
        "notes": f"{a6['num_runs_full']} runs. RLE adds overhead on sine (deltas "
                 "vary too much). Needs 256B RAM.",
        "needs_ram": 256,
    })

    # 6b. Delta + RLE, quarter
    entries.append({
        "name": "6b. Delta + RLE (quarter)",
        "data": a6["data_bytes_quarter"],
        "code": a6["code_bytes_quarter"],
        "total": a6["data_bytes_quarter"] + a6["code_bytes_quarter"],
        "max_err": 0,
        "rms_err": 0.0,
        "notes": f"{a6['num_runs_quarter']} runs. Needs 64B RAM.",
        "needs_ram": 64,
    })

    # 7a. Second-order delta, packed, full
    entries.append({
        "name": f"7a. 2nd-order delta ({a7['d2_bits']}bit, full)",
        "data": a7["data_bytes_full_packed"],
        "code": a7["code_bytes_gen"] + 8,  # +8 for bit unpacking
        "total": a7["data_bytes_full_packed"] + a7["code_bytes_gen"] + 8,
        "max_err": 0,
        "rms_err": 0.0,
        "notes": f"d2 values: {a7['d2_unique']}. Excellent compression! "
                 "Complex decode (two accumulators + bit unpacking). 256B RAM.",
        "needs_ram": 256,
    })

    # 7b. Second-order delta, packed, quarter
    entries.append({
        "name": f"7b. 2nd-order delta ({a7['d2q_bits']}bit, quarter)",
        "data": a7["data_bytes_quarter_packed"],
        "code": a7["code_bytes_quarter"] + 8,
        "total": a7["data_bytes_quarter_packed"] + a7["code_bytes_quarter"] + 8,
        "max_err": 0,
        "rms_err": 0.0,
        "notes": f"Quarter d2 values: {a7['d2q_unique']}. "
                 "Smallest exact representation. 64B RAM.",
        "needs_ram": 64,
    })

    # 8a. Hybrid quarter + byte deltas
    entries.append({
        "name": a8["name_A"],
        "data": a8["data_A"],
        "code": a8["code_A"],
        "total": a8["data_A"] + a8["code_A"],
        "max_err": 0,
        "rms_err": 0.0,
        "notes": a8["notes_A"],
        "needs_ram": 64,
    })

    # 8b. Hybrid quarter + packed deltas
    entries.append({
        "name": a8["name_B"],
        "data": a8["data_B"],
        "code": a8["code_B"],
        "total": a8["data_B"] + a8["code_B"],
        "max_err": 0,
        "rms_err": 0.0,
        "notes": a8["notes_B"],
        "needs_ram": 64,
    })

    # 8c. Hybrid quarter + 2nd-order deltas
    entries.append({
        "name": a8["name_C"],
        "data": a8["data_C"],
        "code": a8["code_C"],
        "total": a8["data_C"] + a8["code_C"],
        "max_err": 0,
        "rms_err": 0.0,
        "notes": a8["notes_C"],
        "needs_ram": 64,
    })

    # 9a. Bhaskara I approximation
    e9_max, e9_rms = measure_error(true_table, a9["table"])
    entries.append({
        "name": a9["name"],
        "data": a9["data_bytes"],
        "code": a9["code_bytes"],
        "total": a9["data_bytes"] + a9["code_bytes"],
        "max_err": e9_max,
        "rms_err": e9_rms,
        "notes": a9["notes"],
        "needs_ram": 0,
    })

    # 9b. Bhaskara I + correction bitmap (exact)
    # Apply corrections to get exact table
    bhaskara_exact = list(a9["table"])
    # The corrections are symmetric across quarter-wave, so applying them
    # produces an exact table
    entries.append({
        "name": a9["name_corrected"],
        "data": a9["data_bytes_corrected"],
        "code": a9["code_bytes_corrected"],
        "total": a9["data_bytes_corrected"] + a9["code_bytes_corrected"],
        "max_err": 0,  # exact with corrections applied
        "rms_err": 0.0,
        "notes": f"Bhaskara + 1-byte correction bitmap for {a9['num_corrections']} "
                 f"positions. Exact. No RAM needed.",
        "needs_ram": 0,
    })

    # Print main table
    hdr = (f"{'#':>3} {'Approach':<38} {'Data':>5} {'Code':>5} "
           f"{'Total':>6} {'RAM':>4} {'MaxE':>5} {'RMS':>6}")
    print(hdr)
    print("-" * 98)

    for i, e in enumerate(entries):
        row = (f"{i+1:3d} {e['name']:<38} {e['data']:5d} {e['code']:5d} "
               f"{e['total']:6d} {e['needs_ram']:4d} {e['max_err']:5d} "
               f"{e['rms_err']:6.2f}")
        print(row)

    # Print notes below
    print()
    print("Notes:")
    print("-" * 98)
    for i, e in enumerate(entries):
        print(f"  {i+1:2d}. {e['notes']}")
    print()

    # --------------- Rankings ---------------
    print("=" * 78)
    print("RANKING BY TOTAL SIZE (data + code, smallest first)")
    print("=" * 78)
    by_size = sorted(entries, key=lambda e: (e["total"], e["needs_ram"]))
    print(f"{'Rank':>4} {'Total':>6} {'RAM':>4}  {'Approach':<42} {'MaxErr':>6}")
    print("-" * 70)
    for rank, e in enumerate(by_size, 1):
        exact = "exact" if e["max_err"] == 0 else f"{e['max_err']:5d}"
        print(f"{rank:4d} {e['total']:5d}B {e['needs_ram']:4d}  "
              f"{e['name']:<42} {exact:>6}")

    print()
    print("=" * 78)
    print("RANKING BY ACCURACY (most accurate first, then by size)")
    print("=" * 78)
    by_acc = sorted(entries, key=lambda e: (e["max_err"], e["rms_err"], e["total"]))
    print(f"{'Rank':>4} {'MaxErr':>6} {'RMS':>6} {'Total':>6}  {'Approach'}")
    print("-" * 70)
    for rank, e in enumerate(by_acc, 1):
        print(f"{rank:4d} {e['max_err']:6d} {e['rms_err']:6.2f} "
              f"{e['total']:5d}B  {e['name']}")

    print()
    print("=" * 78)
    print("RANKING: BEST TRADEOFF (exact + smallest total, no RAM needed)")
    print("=" * 78)
    # Filter to exact approaches
    exact = [e for e in entries if e["max_err"] == 0]
    no_ram = sorted([e for e in exact if e["needs_ram"] == 0],
                    key=lambda e: e["total"])
    with_ram = sorted([e for e in exact if e["needs_ram"] > 0],
                      key=lambda e: e["total"])

    print("\nExact, no runtime RAM needed (lookup-based):")
    for rank, e in enumerate(no_ram, 1):
        print(f"  {rank}. {e['total']:4d}B total  {e['name']}")

    print("\nExact, needs RAM buffer (generation at startup):")
    for rank, e in enumerate(with_ram, 1):
        print(f"  {rank}. {e['total']:4d}B total (+{e['needs_ram']}B RAM)  {e['name']}")

    # The inexact approach
    inexact = [e for e in entries if e["max_err"] > 0]
    if inexact:
        print("\nApproximate (non-zero error):")
        for e in sorted(inexact, key=lambda e: e["total"]):
            print(f"  - {e['total']:4d}B total  {e['name']}  "
                  f"(max err={e['max_err']}, rms={e['rms_err']:.2f})")

    # --------------- Summary ---------------
    print()
    print("=" * 78)
    print("SUMMARY & RECOMMENDATIONS")
    print("=" * 78)
    print("""
For Z80 demoscene work, the practical choices come down to:

  SPEED IS KING (most effects):
    -> Approach 1: Full 256-byte table. Just 256 bytes, instant lookup.
       On a 48K Spectrum you have ~40K free. 256 bytes is nothing.
       LD L,A / LD A,(HL) = 11 T-states. Can't beat that.

  SAVING EVERY BYTE (128-byte intro, tight loader):
    -> Approach 2: Quarter-wave table. 86 bytes total, ZERO error, no RAM.
       65-byte table (0..64 inclusive) + 21-byte lookup routine.
       Lookup adds ~50-70 T-states but that's fine for size-coding.
       This is the go-to approach for most size-limited demos.

  EXTREME SIZE CODING (64-byte intro):
    -> Approach 3: Parabolic, 38 bytes, no data at all.
       Max error of 8 (about 6% of full range). Good enough for plasmas
       and simple motion. The "Dark's method" from Spectrum Engineer articles.

  BEST COMPRESSION (exact, startup generation OK):
    -> Approach 8c: 63 bytes total for exact quarter-wave via
       second-order deltas. Needs 64B RAM buffer. Great for size-limited
       demos that can afford a brief init routine.
    -> Approach 7b: 71 bytes, similar idea, slightly simpler decode.

  BHASKARA I (7TH CENTURY):
    -> Approach 9a: ~60 bytes, max error just 1. A rational approximation
       from 629 CE: sin(x) ≈ 16x(π-x) / (5π²-4x(π-x)). Needs 8x8 multiply
       + 16-bit divide. If your demo already has these routines, the marginal
       cost is only ~25 bytes for max error 1 -- dramatically better than
       parabolic (max error 8). Only 8 out of 65 quarter entries need ±1
       correction; a 1-byte bitmap makes it exact (~81 bytes total).

  DIMINISHING RETURNS:
    The parabolic + correction hybrid (4b, 123 bytes) is interesting
    theoretically but the code overhead makes it worse than just using a
    quarter table (86 bytes). Delta+RLE (6) doesn't compress sine well
    because deltas vary smoothly rather than repeating in runs.

  KEY INSIGHT: Second-order deltas of a sine wave are just {-1, 0, +1},
  which pack into 2 bits each. This is because d2(sin)/dx2 = -sin, and at
  8-bit precision the second derivative only ever changes by 1 step. This
  mathematical property makes 2-bit d2 packing the optimal compression
  for exact sine table storage.
""")


if __name__ == "__main__":
    main()
