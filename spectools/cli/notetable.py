#!/usr/bin/env python3
"""AY-3-8910 Note Table Generator for ZX Spectrum.

Generates period tables for the AY-3-8910 / YM2149 sound chip across
multiple tuning systems. Output as Z80 assembly (DW), C array, or JSON.

Tuning systems supported:
  12-TET (equal temperament) -- default
  Just intonation (C-major, Roshin "Table #5" ratios)
  Pythagorean tuning
  Custom ratios from file

Usage:
  python notetable.py                           # 12-TET, ZX 128K defaults
  python notetable.py --just --clock 1520640    # Just intonation, Table #5 clock
  python notetable.py --pythagorean --format c  # Pythagorean, C output
  python notetable.py --custom ratios.txt       # Custom ratio file
  python notetable.py --check-envelope          # Show envelope alignment info
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from fractions import Fraction
from pathlib import Path
from typing import TextIO

# ── Constants ──────────────────────────────────────────────────────────

AY_PERIOD_MIN = 1
AY_PERIOD_MAX = 4095  # 12-bit range

# Standard AY clock frequencies
CLOCK_ZX128K = 1773400   # ZX Spectrum 128K / +2 / +3
CLOCK_ZX48K = 1750000    # ZX Spectrum 48K (some references)
CLOCK_TABLE5 = 1520640   # Ivan Roshin "Table #5" natural tuning

DEFAULT_CLOCK = CLOCK_ZX128K
DEFAULT_BASE_FREQ = 440.0
DEFAULT_OCTAVES = 8

# Note names: 12 semitones, using flats for minor intervals
NOTE_NAMES = ["C-", "C#", "D-", "Eb", "E-", "F-", "F#", "G-", "Ab", "A-", "Bb", "B-"]

# ── Tuning ratio tables ───────────────────────────────────────────────

# Just intonation (C-major, 5-limit) -- Roshin "Table #5"
JUST_RATIOS = [
    Fraction(1, 1),      # C
    Fraction(16, 15),    # C#
    Fraction(9, 8),      # D
    Fraction(6, 5),      # Eb
    Fraction(5, 4),      # E
    Fraction(4, 3),      # F
    Fraction(45, 32),    # F#
    Fraction(3, 2),      # G
    Fraction(8, 5),      # Ab
    Fraction(5, 3),      # A
    Fraction(9, 5),      # Bb
    Fraction(15, 8),     # B
]

# Pythagorean tuning (3-limit)
PYTHAGOREAN_RATIOS = [
    Fraction(1, 1),       # C
    Fraction(256, 243),   # C#
    Fraction(9, 8),       # D
    Fraction(32, 27),     # Eb
    Fraction(81, 64),     # E
    Fraction(4, 3),       # F
    Fraction(729, 512),   # F#
    Fraction(3, 2),       # G
    Fraction(128, 81),    # Ab
    Fraction(27, 16),     # A
    Fraction(16, 9),      # Bb
    Fraction(243, 128),   # B
]


# ── Note data ─────────────────────────────────────────────────────────

class Note:
    """A single note in the table."""

    __slots__ = ("name", "octave", "semitone", "freq_hz", "period", "midi")

    def __init__(self, name: str, octave: int, semitone: int,
                 freq_hz: float, period: int, midi: int) -> None:
        self.name = name
        self.octave = octave
        self.semitone = semitone
        self.freq_hz = freq_hz
        self.period = period
        self.midi = midi


# ── Frequency / period calculation ────────────────────────────────────

def freq_12tet(midi_note: int, base_freq: float) -> float:
    """Equal temperament frequency for a MIDI note number.
    midi_note 69 = A4 = base_freq."""
    return base_freq * (2.0 ** ((midi_note - 69) / 12.0))


def freq_ratio_based(semitone: int, octave: int, ratios: list[Fraction],
                     base_freq: float) -> float:
    """Frequency for ratio-based tuning systems.

    We anchor A4 (semitone=9, octave=4) to base_freq. The ratio table
    is relative to C in each octave. So:
      freq(C, oct) = base_freq * (ratio[0] / ratio[9]) * 2^(oct - 4)
      freq(note, oct) = freq(C, oct) * ratio[semitone]
    """
    # ratio[9] is A (the 10th note), anchored to base_freq at octave 4
    ratio_a = float(ratios[9])
    ratio_note = float(ratios[semitone])
    # C in octave 4 = base_freq / ratio_a (since A4 = C4 * ratio[9])
    c4_freq = base_freq / ratio_a
    # Scale to target octave
    c_oct_freq = c4_freq * (2.0 ** (octave - 4))
    return c_oct_freq * ratio_note


def ay_period(freq_hz: float, clock: int) -> int:
    """AY-3-8910 tone period from frequency.
    period = clock / (16 * freq), clamped to 12-bit range [1..4095]."""
    if freq_hz <= 0:
        return AY_PERIOD_MAX
    raw = clock / (16.0 * freq_hz)
    clamped = max(AY_PERIOD_MIN, min(AY_PERIOD_MAX, round(raw)))
    return int(clamped)


# ── Table generation ──────────────────────────────────────────────────

def parse_custom_ratios(path: str) -> list[Fraction]:
    """Read 12 ratio values from a file (one per line).
    Each line is either a fraction like 3/2 or a decimal like 1.5."""
    ratios: list[Fraction] = []
    filepath = Path(path)
    if not filepath.exists():
        print(f"Error: custom ratio file not found: {path}", file=sys.stderr)
        sys.exit(1)
    with filepath.open() as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                if "/" in line:
                    ratios.append(Fraction(line))
                else:
                    ratios.append(Fraction(line).limit_denominator(10000))
            except (ValueError, ZeroDivisionError) as e:
                print(f"Error: line {lineno} in {path}: {e}", file=sys.stderr)
                sys.exit(1)
    if len(ratios) != 12:
        print(f"Error: expected 12 ratios in {path}, got {len(ratios)}",
              file=sys.stderr)
        sys.exit(1)
    return ratios


def generate_table(tuning: str, clock: int, base_freq: float,
                   octaves: int,
                   ratios: list[Fraction] | None = None) -> list[Note]:
    """Generate the full note table."""
    notes: list[Note] = []
    for octave in range(octaves):
        for semitone in range(12):
            # MIDI note number: C-0 = 12 (C in octave 0)
            midi = 12 + octave * 12 + semitone
            name = f"{NOTE_NAMES[semitone]}{octave}"

            if tuning == "12tet":
                freq = freq_12tet(midi, base_freq)
            elif tuning in ("just", "pythagorean", "custom"):
                assert ratios is not None
                freq = freq_ratio_based(semitone, octave, ratios, base_freq)
            else:
                raise ValueError(f"Unknown tuning: {tuning}")

            period = ay_period(freq, clock)
            notes.append(Note(
                name=name,
                octave=octave,
                semitone=semitone,
                freq_hz=freq,
                period=period,
                midi=midi,
            ))
    return notes


# ── Output formatters ─────────────────────────────────────────────────

def tuning_label(tuning: str) -> str:
    labels = {
        "12tet": "12-TET",
        "just": "Just Intonation",
        "pythagorean": "Pythagorean",
        "custom": "Custom",
    }
    return labels.get(tuning, tuning)


def header_comment(tuning: str, clock: int, base_freq: float,
                   prefix: str = "; ") -> str:
    return (
        f"{prefix}AY-3-8910 Note Table — {tuning_label(tuning)}, "
        f"clock={clock} Hz, A4={base_freq:g} Hz\n"
        f"{prefix}Generated by notetable.py (spectools)"
    )


def format_asm(notes: list[Note], tuning: str, clock: int,
               base_freq: float, out: TextIO) -> None:
    """Output Z80 assembly DW table."""
    out.write(header_comment(tuning, clock, base_freq, "; "))
    out.write("\n\n")
    out.write("note_table:\n")

    current_octave = -1
    for note in notes:
        if note.octave != current_octave:
            current_octave = note.octave
            out.write(f"    ; Octave {current_octave}\n")
        hex_str = f"${note.period:04X}"
        out.write(f"    DW  {hex_str}  ; {note.name}  {note.period:5d}\n")


def format_c(notes: list[Note], tuning: str, clock: int,
             base_freq: float, out: TextIO) -> None:
    """Output C uint16_t array."""
    out.write(header_comment(tuning, clock, base_freq, "// "))
    out.write("\n\n")
    count = len(notes)
    out.write(f"const uint16_t note_table[{count}] = {{\n")
    for i, note in enumerate(notes):
        comma = "," if i < count - 1 else ""
        hex_str = f"0x{note.period:04X}"
        out.write(f"    {hex_str}{comma} /* {note.name}  {note.period:5d} */\n")
    out.write("};\n")


def format_json(notes: list[Note], tuning: str, clock: int,
                base_freq: float, out: TextIO) -> None:
    """Output JSON object."""
    data = {
        "tuning": tuning,
        "clock": clock,
        "base_freq": base_freq,
        "notes": [
            {
                "name": note.name,
                "octave": note.octave,
                "semitone": note.semitone,
                "period": note.period,
                "freq_hz": round(note.freq_hz, 2),
                "div16": (note.period % 16 == 0),
            }
            for note in notes
        ],
    }
    json.dump(data, out, indent=2)
    out.write("\n")


def format_envelope_check(notes: list[Note], out: TextIO) -> None:
    """Append envelope alignment report."""
    out.write("\n; Envelope alignment check (period divisible by 16):\n")
    for note in notes:
        quotient = note.period / 16.0
        if note.period % 16 == 0:
            mark = "Y"
            out.write(f"; {note.name}: {note.period} / 16 = {quotient:.0f}    {mark}\n")
        else:
            mark = "N"
            out.write(f"; {note.name}: {note.period} / 16 = {quotient:.1f}  {mark}\n")


# ── CLI ───────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="notetable",
        description=(
            "AY-3-8910 Note Table Generator.\n"
            "Generates period lookup tables for the AY/YM sound chip\n"
            "in various tuning systems and output formats."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  %(prog)s                               12-TET, ZX 128K defaults\n"
            "  %(prog)s --just --clock 1520640         Just intonation, Table #5\n"
            "  %(prog)s --pythagorean --format c       Pythagorean, C array\n"
            "  %(prog)s --12tet --check-envelope       12-TET with envelope check\n"
            "  %(prog)s --custom ratios.txt            Custom tuning ratios\n"
        ),
    )

    tuning_group = parser.add_mutually_exclusive_group()
    tuning_group.add_argument(
        "--12tet", dest="tuning", action="store_const", const="12tet",
        help="12-tone equal temperament (default)",
    )
    tuning_group.add_argument(
        "--just", dest="tuning", action="store_const", const="just",
        help="Just intonation (C-major, Roshin Table #5 ratios)",
    )
    tuning_group.add_argument(
        "--pythagorean", dest="tuning", action="store_const", const="pythagorean",
        help="Pythagorean tuning (3-limit)",
    )
    tuning_group.add_argument(
        "--custom", dest="custom_file", metavar="FILE",
        help="Custom ratio file (12 lines, fraction or decimal per line)",
    )

    parser.add_argument(
        "--clock", type=int, default=DEFAULT_CLOCK,
        help=f"AY clock in Hz (default {DEFAULT_CLOCK}; 48K: {CLOCK_ZX48K}; "
             f"Table#5: {CLOCK_TABLE5})",
    )
    parser.add_argument(
        "--base-freq", type=float, default=DEFAULT_BASE_FREQ,
        help=f"A4 reference frequency in Hz (default {DEFAULT_BASE_FREQ})",
    )
    parser.add_argument(
        "--format", choices=["asm", "c", "json"], default="asm",
        dest="output_format",
        help="Output format (default: asm)",
    )
    parser.add_argument(
        "--check-envelope", action="store_true",
        help="Report which periods are divisible by 16 (T+E buzz-bass)",
    )
    parser.add_argument(
        "--octaves", type=int, default=DEFAULT_OCTAVES,
        help=f"Number of octaves starting from octave 0 (default {DEFAULT_OCTAVES})",
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Determine tuning system and ratios
    ratios: list[Fraction] | None = None

    if args.custom_file:
        tuning = "custom"
        ratios = parse_custom_ratios(args.custom_file)
    elif args.tuning == "just":
        tuning = "just"
        ratios = JUST_RATIOS
    elif args.tuning == "pythagorean":
        tuning = "pythagorean"
        ratios = PYTHAGOREAN_RATIOS
    else:
        # Default to 12-TET
        tuning = "12tet"

    # Validate octaves
    if args.octaves < 1 or args.octaves > 10:
        print("Error: --octaves must be between 1 and 10", file=sys.stderr)
        sys.exit(1)

    # Generate table
    notes = generate_table(
        tuning=tuning,
        clock=args.clock,
        base_freq=args.base_freq,
        octaves=args.octaves,
        ratios=ratios,
    )

    # Output
    out = sys.stdout

    if args.output_format == "asm":
        format_asm(notes, tuning, args.clock, args.base_freq, out)
    elif args.output_format == "c":
        format_c(notes, tuning, args.clock, args.base_freq, out)
    elif args.output_format == "json":
        format_json(notes, tuning, args.clock, args.base_freq, out)

    # Envelope check (appended after main output, for asm and c formats)
    if args.check_envelope:
        format_envelope_check(notes, out)


if __name__ == "__main__":
    main()
