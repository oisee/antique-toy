#!/usr/bin/env python3
"""Packer benchmark & streaming decompression estimator.

Benchmarks Z80 compression tools on real data, estimates memory budgets
for 128K bank allocation, and models streaming decompression schedules
for seamless demo effect transitions.

Four modes:
  bench     — Run packers on files, measure compressed size and ratios
  budget    — Memory budget estimation from TOML config (128K bank map)
  timeline  — Streaming decompression schedule (overlap/pause/stream)
  analyze   — Pre-compression data analysis: entropy, delta, transposition

Usage:
    python3 tools/packbench.py bench demo/data/*.bin --packers zx0,lz4
    python3 tools/packbench.py bench --list-packers
    python3 tools/packbench.py budget --config demo/packbench.toml
    python3 tools/packbench.py timeline --config demo/packbench.toml
    python3 tools/packbench.py timeline --config demo/packbench.toml --what-if
    python3 tools/packbench.py timeline --config demo/packbench.toml --json
    python3 tools/packbench.py analyze data.bin
    python3 tools/packbench.py analyze data.bin --stride 256 --columns 3
"""

import argparse
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    # Python < 3.11
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:
        tomllib = None  # type: ignore[assignment]

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Packer profiles — from Introspec's benchmark (Ch.14) + Ped7g feedback
# ---------------------------------------------------------------------------
# tstates_per_byte: decompression speed on Z80 @ 3.5MHz
# decomp_size: decompressor routine size in bytes
# est_ratio: average compression ratio from 1.2MB benchmark corpus
# binary: expected command-line tool name
# compress_args: arguments template ({input} and {output} are substituted)

PACKER_PROFILES = {
    "lz4": {
        "tstates_per_byte": 34,
        "decomp_size": 100,
        "est_ratio": 0.586,
        "binary": "lz4",
        "compress_args": ["-12", "-f", "{input}", "{output}"],
        "description": "Fastest decompression, largest output",
    },
    "megalz": {
        "tstates_per_byte": 63,
        "decomp_size": 234,
        "est_ratio": 0.516,
        "binary": "megalz",
        "compress_args": ["{input}", "{output}"],
        "description": "MegaLZ fast variant — good speed/ratio balance",
    },
    "pletter": {
        "tstates_per_byte": 69,
        "decomp_size": 120,
        "est_ratio": 0.515,
        "binary": "pletter",
        "compress_args": ["{input}", "{output}"],
        "description": "Pletter 5 — fast with decent ratio",
    },
    "zx0": {
        "tstates_per_byte": 100,
        "decomp_size": 70,
        "est_ratio": 0.52,
        "binary": "zx0",
        "compress_args": ["{input}", "{output}"],
        "description": "Modern default — tiny decompressor, good ratio",
    },
    "aplib": {
        "tstates_per_byte": 105,
        "decomp_size": 199,
        "est_ratio": 0.492,
        "binary": "apultra",
        "compress_args": ["{input}", "{output}"],
        "description": "Good balance of ratio and speed",
    },
    "zx7": {
        "tstates_per_byte": 107,
        "decomp_size": 69,
        "est_ratio": 0.53,
        "binary": "zx7",
        "compress_args": ["{input}", "{output}"],
        "description": "Classic — smallest decompressor (69 bytes)",
    },
    "hrust1": {
        "tstates_per_byte": 120,
        "decomp_size": 150,
        "est_ratio": 0.497,
        "binary": "hrust",
        "compress_args": ["{input}", "{output}"],
        "description": "Hrust 1 — relocatable, good ratio",
    },
    "exomizer": {
        "tstates_per_byte": 250,
        "decomp_size": 170,
        "est_ratio": 0.483,
        "binary": "exomizer",
        "compress_args": ["raw", "-c", "-q", "{input}", "-o", "{output}"],
        "description": "Best ratio, slow decompression",
    },
    "upkr": {
        "tstates_per_byte": 500,
        "decomp_size": 60,
        "est_ratio": 0.50,
        "binary": "upkr",
        "compress_args": ["pack", "{input}", "{output}"],
        "description": "Tiny decompressor, very slow — best for 256b-2K intros",
    },
}

# Sorted by decompression speed (fastest first)
PACKER_ORDER = [
    "lz4", "megalz", "pletter", "zx0", "aplib",
    "zx7", "hrust1", "exomizer", "upkr",
]


# ---------------------------------------------------------------------------
# Platform T-state budgets per frame
# ---------------------------------------------------------------------------

PLATFORMS = {
    "spectrum48":   {"tstates_per_frame": 69888,  "label": "ZX Spectrum 48K"},
    "spectrum128":  {"tstates_per_frame": 69888,  "label": "ZX Spectrum 128K"},
    "pentagon128":  {"tstates_per_frame": 71680,  "label": "Pentagon 128"},
    "next":         {"tstates_per_frame": 560000, "label": "ZX Spectrum Next"},
}

DEFAULT_PLATFORM = "spectrum128"


# ---------------------------------------------------------------------------
# 128K memory map — 8 banks × 16K
# ---------------------------------------------------------------------------
# Bank 5 = screen ($4000-$7FFF), Bank 2 = contended, Bank 0 = ROM-paged
# Banks 1,3,4,6,7 = freely usable; Bank 0 accessible via paging

BANK_SIZE = 16384  # 16K per bank
NUM_BANKS = 8


# ---------------------------------------------------------------------------
# PackerRunner — detect and run packer binaries
# ---------------------------------------------------------------------------

class PackerRunner:
    """Detects installed packer binaries and runs them on input files."""

    def __init__(self, custom_paths=None):
        self.custom_paths = custom_paths or {}
        self._detected = {}
        self._detect_all()

    def _detect_all(self):
        for name, profile in PACKER_PROFILES.items():
            custom = self.custom_paths.get(name)
            if custom:
                path = Path(custom)
                self._detected[name] = str(path) if path.exists() else None
            else:
                self._detected[name] = shutil.which(profile["binary"])

    def is_available(self, packer_name):
        return self._detected.get(packer_name) is not None

    def available_packers(self):
        return [n for n in PACKER_ORDER if self.is_available(n)]

    def compress(self, packer_name, input_path):
        """Compress a file, return compressed size in bytes or None on failure."""
        if not self.is_available(packer_name):
            return None

        binary = self._detected[packer_name]
        profile = PACKER_PROFILES[packer_name]

        with tempfile.NamedTemporaryFile(suffix=".packed", delete=False) as tmp:
            output_path = tmp.name

        try:
            args = []
            for a in profile["compress_args"]:
                args.append(
                    a.replace("{input}", str(input_path))
                     .replace("{output}", output_path)
                )
            cmd = [binary] + args
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60
            )
            if result.returncode != 0:
                return None
            return Path(output_path).stat().st_size
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return None
        finally:
            try:
                Path(output_path).unlink(missing_ok=True)
            except OSError:
                pass

    def estimate_size(self, packer_name, raw_size):
        """Estimate compressed size using profile ratio when binary unavailable."""
        profile = PACKER_PROFILES[packer_name]
        return int(raw_size * profile["est_ratio"])


# ---------------------------------------------------------------------------
# TOML config loader
# ---------------------------------------------------------------------------

def load_config(config_path):
    """Load and validate a packbench TOML config."""
    if tomllib is None:
        print("Error: Python 3.11+ or 'tomli' package required for TOML support",
              file=sys.stderr)
        sys.exit(1)

    path = Path(config_path)
    if not path.exists():
        print(f"Error: config file not found: {path}", file=sys.stderr)
        sys.exit(1)

    with open(path, "rb") as f:
        config = tomllib.load(f)

    # Resolve paths relative to config file location
    config_dir = path.parent

    # Validate required sections
    if "target" not in config:
        print("Error: [target] section required in config", file=sys.stderr)
        sys.exit(1)

    platform = config["target"].get("platform", DEFAULT_PLATFORM)
    if platform not in PLATFORMS:
        print(f"Error: unknown platform '{platform}'. "
              f"Known: {', '.join(PLATFORMS)}", file=sys.stderr)
        sys.exit(1)

    # Resolve data file paths in effects
    for effect in config.get("effects", []):
        if "data" in effect:
            resolved = []
            for d in effect["data"]:
                p = Path(d)
                if not p.is_absolute():
                    # Try relative to config dir, then relative to ROOT
                    candidate = config_dir / p
                    if not candidate.exists():
                        candidate = ROOT / p
                    p = candidate
                resolved.append(p)
            effect["_resolved_data"] = resolved

    return config


# ---------------------------------------------------------------------------
# Mode: bench
# ---------------------------------------------------------------------------

def cmd_bench(args):
    """Run packers on input files and report compression results."""
    runner = PackerRunner()

    if args.list_packers:
        print(f"{'Packer':<12s} {'T/byte':>7s} {'Decomp':>7s} {'Ratio':>7s} "
              f"{'Binary':>12s} {'Status':>10s}  Description")
        print("─" * 95)
        for name in PACKER_ORDER:
            p = PACKER_PROFILES[name]
            status = "installed" if runner.is_available(name) else "estimate"
            binary = runner._detected.get(name) or p["binary"]
            # Show just the basename for installed paths
            if runner.is_available(name):
                binary = Path(binary).name
            print(f"{name:<12s} {p['tstates_per_byte']:>7d} "
                  f"{p['decomp_size']:>6d}B {p['est_ratio']:>6.1%} "
                  f"{binary:>12s} {status:>10s}  {p['description']}")

        platform = args.platform or DEFAULT_PLATFORM
        tpf = PLATFORMS[platform]["tstates_per_frame"]
        print(f"\nPlatform: {PLATFORMS[platform]['label']} "
              f"({tpf:,} T-states/frame)")
        print(f"\n{'Packer':<12s} {'Bytes/frame':>12s}  "
              f"(decompression throughput at 50fps)")
        print("─" * 40)
        for name in PACKER_ORDER:
            p = PACKER_PROFILES[name]
            bpf = tpf / p["tstates_per_byte"]
            print(f"{name:<12s} {bpf:>11,.0f}B")
        return

    if not args.files:
        print("Error: no input files specified. Use --list-packers or provide files.",
              file=sys.stderr)
        sys.exit(1)

    # Determine which packers to run
    if args.packers:
        selected = [p.strip() for p in args.packers.split(",")]
        for p in selected:
            if p not in PACKER_PROFILES:
                print(f"Error: unknown packer '{p}'", file=sys.stderr)
                sys.exit(1)
    else:
        selected = list(PACKER_ORDER)

    platform = args.platform or DEFAULT_PLATFORM
    tpf = PLATFORMS[platform]["tstates_per_frame"]

    # Collect results
    results = []
    for filepath in args.files:
        path = Path(filepath)
        if not path.exists():
            print(f"Warning: {path} not found, skipping", file=sys.stderr)
            continue
        raw_size = path.stat().st_size
        if raw_size == 0:
            print(f"Warning: {path} is empty, skipping", file=sys.stderr)
            continue

        row = {"file": path.name, "raw_size": raw_size, "packers": {}}
        for packer in selected:
            compressed = runner.compress(packer, path)
            if compressed is not None:
                ratio = compressed / raw_size
                source = "real"
            else:
                compressed = runner.estimate_size(packer, raw_size)
                ratio = compressed / raw_size
                source = "est"
            row["packers"][packer] = {
                "compressed": compressed,
                "ratio": ratio,
                "source": source,
                "decomp_frames": math.ceil(
                    compressed * PACKER_PROFILES[packer]["tstates_per_byte"] / tpf
                ),
            }
        results.append(row)

    if args.json:
        json.dump({"platform": platform, "results": results},
                  sys.stdout, indent=2)
        print()
        return

    # Tabular output
    packer_cols = selected
    hdr = f"{'File':<30s} {'Raw':>8s}"
    for p in packer_cols:
        hdr += f"  {p:>12s}"
    print(hdr)
    print("─" * len(hdr))

    for row in results:
        line = f"{row['file']:<30s} {row['raw_size']:>7,d}B"
        for p in packer_cols:
            info = row["packers"][p]
            marker = "" if info["source"] == "real" else "~"
            line += f"  {marker}{info['compressed']:>6,d}B {info['ratio']:>4.0%}"
        print(line)

    if len(results) > 1:
        print("─" * len(hdr))
        total_raw = sum(r["raw_size"] for r in results)
        line = f"{'TOTAL':<30s} {total_raw:>7,d}B"
        for p in packer_cols:
            total_c = sum(r["packers"][p]["compressed"] for r in results)
            ratio = total_c / total_raw if total_raw else 0
            line += f"  {total_c:>7,d}B {ratio:>4.0%}"
        print(line)

    print(f"\n  ~ = estimated (binary not found, using profile ratio)")
    print(f"  Platform: {PLATFORMS[platform]['label']} "
          f"({tpf:,} T-states/frame)")


# ---------------------------------------------------------------------------
# Mode: budget
# ---------------------------------------------------------------------------

def cmd_budget(args):
    """Estimate memory budget from TOML config."""
    config = load_config(args.config)
    platform = config["target"].get("platform", DEFAULT_PLATFORM)
    tpf = PLATFORMS[platform]["tstates_per_frame"]
    runner = PackerRunner(config.get("packers", {}))

    reserved = config.get("memory", {}).get("reserved", {})
    effects = config.get("effects", [])

    # Calculate reserved memory
    reserved_items = []
    total_reserved = 0
    for name, spec in reserved.items():
        size = spec.get("size", 0)
        reserved_items.append((name, size, spec))
        total_reserved += size

    # Calculate per-effect storage needs
    effect_rows = []
    for eff in effects:
        name = eff.get("name", "unnamed")
        code_size = eff.get("code_size", 0)
        packer = eff.get("packer", "zx0")
        data_files = eff.get("_resolved_data", [])

        total_raw = 0
        total_compressed = 0
        for df in data_files:
            if df.exists():
                raw = df.stat().st_size
                total_raw += raw
                comp = runner.compress(packer, df)
                if comp is None:
                    comp = runner.estimate_size(packer, raw)
                total_compressed += comp
            else:
                est_raw = eff.get("data_size_estimate", 0)
                total_raw += est_raw
                total_compressed += runner.estimate_size(packer, est_raw)

        # Fallback: use data_size_estimate when no data files specified
        if not data_files and total_raw == 0:
            est_raw = eff.get("data_size_estimate", 0)
            total_raw = est_raw
            total_compressed = runner.estimate_size(packer, est_raw)

        total_footprint = code_size + total_compressed
        decomp_size = PACKER_PROFILES.get(packer, {}).get("decomp_size", 0)

        effect_rows.append({
            "name": name,
            "code_size": code_size,
            "data_raw": total_raw,
            "data_compressed": total_compressed,
            "packer": packer,
            "footprint": total_footprint,
            "decomp_size": decomp_size,
        })

    if args.json:
        json.dump({
            "platform": platform,
            "reserved": {n: s for n, s, _ in reserved_items},
            "effects": effect_rows,
            "total_reserved": total_reserved,
            "total_effects": sum(e["footprint"] for e in effect_rows),
        }, sys.stdout, indent=2)
        print()
        return

    # Display
    print(f"Memory Budget — {PLATFORMS[platform]['label']}")
    print(f"{'=' * 60}")

    print(f"\n  Reserved memory:")
    print(f"  {'Item':<25s} {'Size':>8s}  Notes")
    print(f"  {'─' * 55}")
    for name, size, spec in reserved_items:
        notes = ""
        if "bank" in spec:
            notes += f"bank {spec['bank']}"
        if "address" in spec:
            addr = spec["address"]
            if isinstance(addr, str):
                addr = int(addr, 0)
            notes += f"${addr:04X}"
        print(f"  {name:<25s} {size:>7,d}B  {notes}")
    print(f"  {'─' * 55}")
    print(f"  {'TOTAL reserved':<25s} {total_reserved:>7,d}B")

    print(f"\n  Effect storage (compressed):")
    print(f"  {'Effect':<16s} {'Packer':<10s} {'Code':>7s} {'Data':>10s} "
          f"{'Packed':>8s} {'Total':>8s}")
    print(f"  {'─' * 65}")
    grand_total = 0
    for e in effect_rows:
        data_str = f"{e['data_raw']:,d}" if e['data_raw'] > 0 else "—"
        comp_str = f"{e['data_compressed']:,d}" if e['data_compressed'] > 0 else "—"
        print(f"  {e['name']:<16s} {e['packer']:<10s} {e['code_size']:>6,d}B "
              f"{data_str:>9s}B {comp_str:>7s}B {e['footprint']:>7,d}B")
        grand_total += e["footprint"]
    print(f"  {'─' * 65}")
    print(f"  {'TOTAL effects':<28s} {' ' * 27} {grand_total:>7,d}B")

    # Shared resources (decompressor only counted once — largest needed)
    decomp_sizes = set(e["decomp_size"] for e in effect_rows)
    max_decomp = max(decomp_sizes) if decomp_sizes else 0

    # Bank allocation view
    usable_bytes = NUM_BANKS * BANK_SIZE
    total_used = total_reserved + grand_total + max_decomp
    free = usable_bytes - total_used

    print(f"\n  128K overview:")
    print(f"  {'─' * 40}")
    print(f"  {'Total RAM':<25s} {usable_bytes:>7,d}B  ({NUM_BANKS}×{BANK_SIZE // 1024}K)")
    print(f"  {'Reserved':<25s} {total_reserved:>7,d}B")
    print(f"  {'Decompressor':<25s} {max_decomp:>7,d}B  (largest needed)")
    print(f"  {'Effects (packed)':<25s} {grand_total:>7,d}B")
    print(f"  {'─' * 40}")
    pct = total_used / usable_bytes * 100
    print(f"  {'USED':<25s} {total_used:>7,d}B  ({pct:.1f}%)")
    print(f"  {'FREE':<25s} {free:>7,d}B  ({100 - pct:.1f}%)")

    if free < 0:
        print(f"\n  *** OVER BUDGET by {-free:,d} bytes! ***")


# ---------------------------------------------------------------------------
# Mode: timeline
# ---------------------------------------------------------------------------

def cmd_timeline(args):
    """Model streaming decompression schedule for demo effect transitions."""
    config = load_config(args.config)
    platform = config["target"].get("platform", DEFAULT_PLATFORM)
    tpf = PLATFORMS[platform]["tstates_per_frame"]
    runner = PackerRunner(config.get("packers", {}))

    effects = config.get("effects", [])
    if not effects:
        print("No effects defined in config.", file=sys.stderr)
        sys.exit(1)

    # Build effect list with computed compressed sizes
    effect_list = []
    for eff in effects:
        name = eff.get("name", "unnamed")
        packer = eff.get("packer", "zx0")
        code_size = eff.get("code_size", 0)
        duration = eff.get("duration_frames", 0)
        render_t = eff.get("render_tstates", 0)
        music_t = eff.get("music_tstates", 0)
        streaming = eff.get("streaming", False)
        data_files = eff.get("_resolved_data", [])

        total_compressed = 0
        total_raw = 0
        for df in data_files:
            if df.exists():
                raw = df.stat().st_size
                total_raw += raw
                comp = runner.compress(packer, df)
                if comp is None:
                    comp = runner.estimate_size(packer, raw)
                total_compressed += comp
            else:
                est_raw = eff.get("data_size_estimate", 0)
                total_raw += est_raw
                total_compressed += runner.estimate_size(packer, est_raw)

        # Fallback: use data_size_estimate when no data files specified
        if not data_files and total_raw == 0:
            est_raw = eff.get("data_size_estimate", 0)
            total_raw = est_raw
            total_compressed = runner.estimate_size(packer, est_raw)

        tpb = PACKER_PROFILES[packer]["tstates_per_byte"]
        spare_t = max(0, tpf - render_t - music_t)

        effect_list.append({
            "name": name,
            "packer": packer,
            "code_size": code_size,
            "compressed": total_compressed,
            "raw": total_raw,
            "duration": duration,
            "render_t": render_t,
            "music_t": music_t,
            "spare_t": spare_t,
            "streaming": streaming,
            "tpb": tpb,
        })

    # Compute transitions
    transitions = []
    current_frame = 0

    for i, eff in enumerate(effect_list):
        entry = {
            "effect": eff["name"],
            "packer": eff["packer"],
            "start_frame": current_frame,
            "compressed_bytes": eff["compressed"],
            "overlap_bytes": 0,
            "pause_frames": 0,
            "stream_during": 0,
            "notes": [],
        }

        # How many bytes were pre-decompressed during previous effect?
        overlap = 0
        if i > 0:
            prev = effect_list[i - 1]
            # Spare T-states during previous effect can decompress this effect
            if prev["spare_t"] > 0:
                bytes_per_frame = prev["spare_t"] / eff["tpb"]
                overlap = bytes_per_frame * prev["duration"]
                overlap = min(overlap, eff["compressed"])
            entry["overlap_bytes"] = overlap
            if overlap >= eff["compressed"]:
                entry["notes"].append(
                    f"fully pre-decompressed during {prev['name']}")

        remaining = eff["compressed"] - overlap

        if remaining > 0:
            if eff["streaming"]:
                # Streaming: only need code_size decompressed to start
                min_needed = max(0, eff["code_size"] - overlap)
                if min_needed > 0:
                    pause_t = min_needed * eff["tpb"]
                    entry["pause_frames"] = math.ceil(pause_t / tpf)
                # Rest decompressed during playback
                still_left = remaining - min_needed
                if still_left > 0 and eff["spare_t"] > 0:
                    stream_bpf = eff["spare_t"] / eff["tpb"]
                    stream_frames = math.ceil(still_left / stream_bpf)
                    entry["stream_during"] = stream_frames
                    if stream_frames > eff["duration"]:
                        entry["notes"].append(
                            f"WARNING: streaming needs {stream_frames}f "
                            f"but effect lasts {eff['duration']}f!")
                entry["notes"].append("streaming enabled")
            else:
                # Full decompression required before start
                pause_t = remaining * eff["tpb"]
                entry["pause_frames"] = math.ceil(pause_t / tpf)

        current_frame += entry["pause_frames"]
        entry["play_start"] = current_frame
        entry["play_end"] = current_frame + eff["duration"]
        current_frame = entry["play_end"]

        transitions.append(entry)

    total_frames = current_frame
    total_pause = sum(t["pause_frames"] for t in transitions)

    if args.json:
        json.dump({
            "platform": platform,
            "tstates_per_frame": tpf,
            "transitions": transitions,
            "total_frames": total_frames,
            "total_pause_frames": total_pause,
            "total_seconds": total_frames / 50.0,
        }, sys.stdout, indent=2)
        print()
        return

    # Visual timeline
    print(f"Streaming Decompression Timeline — {PLATFORMS[platform]['label']}")
    print(f"{'=' * 72}")
    print(f"  {tpf:,} T-states/frame, 50fps\n")

    for t in transitions:
        eff = next(e for e in effect_list if e["name"] == t["effect"])
        print(f"  [{t['effect']}]  packer={t['packer']}  "
              f"compressed={t['compressed_bytes']:,d}B  "
              f"code={eff['code_size']:,d}B")

        if t["overlap_bytes"] > 0:
            print(f"    overlap: {t['overlap_bytes']:,.0f}B pre-decompressed "
                  f"during previous effect")

        if t["pause_frames"] > 0:
            print(f"    PAUSE: {t['pause_frames']} frames "
                  f"({t['pause_frames'] / 50:.2f}s) for decompression")
        else:
            print(f"    pause: 0 frames (no wait needed)")

        print(f"    play: frame {t['play_start']}–{t['play_end']} "
              f"({eff['duration']} frames, {eff['duration'] / 50:.1f}s)")

        if t["stream_during"] > 0:
            print(f"    streaming: {t['stream_during']} frames of background "
                  f"decompression during playback")

        spare_bpf = eff["spare_t"] / eff["tpb"] if eff["tpb"] > 0 else 0
        print(f"    spare: {eff['spare_t']:,d} T/frame → "
              f"{spare_bpf:,.0f} bytes/frame for next effect")

        for note in t["notes"]:
            print(f"    * {note}")
        print()

    # Summary
    print(f"  {'─' * 60}")
    play_frames = sum(e["duration"] for e in effect_list)
    print(f"  Total: {total_frames} frames ({total_frames / 50:.1f}s)")
    print(f"  Playback: {play_frames} frames ({play_frames / 50:.1f}s)")
    print(f"  Pauses: {total_pause} frames ({total_pause / 50:.1f}s)")
    if play_frames > 0:
        efficiency = play_frames / total_frames * 100
        print(f"  Efficiency: {efficiency:.1f}% "
              f"(time spent playing vs total)")

    # What-if mode: compare all packers for each effect
    if args.what_if:
        print(f"\n\n{'=' * 72}")
        print(f"What-If Analysis — comparing all packers per effect")
        print(f"{'=' * 72}\n")

        for i, eff in enumerate(effect_list):
            print(f"  [{eff['name']}]  raw={eff['raw']:,d}B  "
                  f"code={eff['code_size']:,d}B  "
                  f"render={eff['render_t']:,d}T  music={eff['music_t']:,d}T")
            print(f"  {'Packer':<12s} {'Packed':>8s} {'Pause':>6s} "
                  f"{'Spare B/f':>10s} {'Decomp':>7s}  Notes")
            print(f"  {'─' * 60}")

            for pname in PACKER_ORDER:
                pp = PACKER_PROFILES[pname]
                # Estimate compressed size for this packer
                if eff["raw"] > 0:
                    comp = runner.compress(pname, None)  # Can't run without file
                    comp = int(eff["raw"] * pp["est_ratio"])
                else:
                    comp = int(eff["compressed"] / PACKER_PROFILES[eff["packer"]]["est_ratio"]
                               * pp["est_ratio"])

                tpb = pp["tstates_per_byte"]
                spare = max(0, tpf - eff["render_t"] - eff["music_t"])
                spare_bpf = spare / tpb if tpb > 0 else 0

                # Calculate pause needed (overlap from previous)
                overlap_bytes = 0
                if i > 0:
                    prev = effect_list[i - 1]
                    prev_spare = max(0, tpf - prev["render_t"] - prev["music_t"])
                    if prev_spare > 0:
                        overlap_bytes = min(
                            comp, prev_spare / tpb * prev["duration"])

                remaining = comp - overlap_bytes
                if eff["streaming"] and remaining > 0:
                    pause_need = max(0, eff["code_size"] - overlap_bytes)
                else:
                    pause_need = max(0, remaining)

                pause_frames = math.ceil(
                    pause_need * tpb / tpf) if pause_need > 0 else 0

                marker = " ◀ current" if pname == eff["packer"] else ""
                print(f"  {pname:<12s} {comp:>7,d}B {pause_frames:>5d}f "
                      f"{spare_bpf:>9,.0f}B {pp['decomp_size']:>6d}B{marker}")
            print()


# ---------------------------------------------------------------------------
# Mode: analyze — pre-compression data analysis
# ---------------------------------------------------------------------------

def entropy(data):
    """Shannon entropy in bits/byte (order-0). Max = 8.0 for random data."""
    if not data:
        return 0.0
    counts = [0] * 256
    for b in data:
        counts[b] += 1
    n = len(data)
    h = 0.0
    for c in counts:
        if c > 0:
            p = c / n
            h -= p * math.log2(p)
    return h


def delta_encode(data):
    """First derivative: d[i] = (data[i] - data[i-1]) & 0xFF."""
    if len(data) < 2:
        return data
    return bytes([(data[i] - data[i - 1]) & 0xFF for i in range(1, len(data))])


def delta2_encode(data):
    """Second derivative (delta of delta)."""
    return delta_encode(delta_encode(data))


def xor_encode(data):
    """XOR delta: d[i] = data[i] ^ data[i-1]."""
    if len(data) < 2:
        return data
    return bytes([data[i] ^ data[i - 1] for i in range(1, len(data))])


def transpose(data, stride):
    """Column-major transposition: read column-by-column from row-major data.

    Given data as rows of `stride` bytes, return data read column-first.
    Like reading a matrix by columns instead of rows.
    """
    if stride < 2 or len(data) < stride:
        return data
    rows = len(data) // stride
    tail = len(data) % stride
    result = bytearray()
    for col in range(stride):
        for row in range(rows):
            result.append(data[row * stride + col])
    # Append leftover bytes
    if tail:
        result.extend(data[rows * stride:])
    return bytes(result)


def count_runs(data):
    """Count runs of identical bytes. Returns (num_runs, longest_run, avg_run)."""
    if not data:
        return 0, 0, 0.0
    runs = 1
    current = 1
    longest = 1
    for i in range(1, len(data)):
        if data[i] == data[i - 1]:
            current += 1
            if current > longest:
                longest = current
        else:
            runs += 1
            current = 1
    return runs, longest, len(data) / runs


def count_zeros(data):
    """Count zero bytes (highly compressible by LZ)."""
    return sum(1 for b in data if b == 0)


def fit_linear(values):
    """Fit y = a*x + b to values. Returns (a, b, r_squared)."""
    n = len(values)
    if n < 3:
        return 0, 0, 0.0
    sx = n * (n - 1) / 2
    sx2 = n * (n - 1) * (2 * n - 1) / 6
    sy = sum(values)
    sxy = sum(i * v for i, v in enumerate(values))
    denom = n * sx2 - sx * sx
    if denom == 0:
        return 0, values[0] if values else 0, 1.0
    a = (n * sxy - sx * sy) / denom
    b = (sy - a * sx) / n
    # R-squared
    mean_y = sy / n
    ss_tot = sum((v - mean_y) ** 2 for v in values)
    ss_res = sum((v - (a * i + b)) ** 2 for i, v in enumerate(values))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return a, b, r2


def fit_quadratic(values):
    """Fit y = a*x^2 + b*x + c. Returns (a, b, c, r_squared).

    Uses normal equations for degree-2 polynomial.
    """
    n = len(values)
    if n < 4:
        return 0, 0, 0, 0.0
    # Build sums for normal equations
    s = [0.0] * 5  # s[k] = sum(i^k)
    for i in range(n):
        pk = 1.0
        for k in range(5):
            s[k] += pk
            pk *= i
    ty = [0.0] * 3  # ty[k] = sum(i^k * y)
    for i, v in enumerate(values):
        pk = 1.0
        for k in range(3):
            ty[k] += pk * v
            pk *= i
    # Solve 3x3 system: [[s0,s1,s2],[s1,s2,s3],[s2,s3,s4]] * [c,b,a] = [ty0,ty1,ty2]
    # Using Cramer's rule for simplicity
    m = [[s[0], s[1], s[2]], [s[1], s[2], s[3]], [s[2], s[3], s[4]]]
    det = (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
         - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
         + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
    if abs(det) < 1e-10:
        return 0, 0, 0, 0.0

    def replace_col(mat, col, vec):
        r = [row[:] for row in mat]
        for i in range(3):
            r[i][col] = vec[i]
        return r

    def det3(mat):
        return (mat[0][0] * (mat[1][1] * mat[2][2] - mat[1][2] * mat[2][1])
              - mat[0][1] * (mat[1][0] * mat[2][2] - mat[1][2] * mat[2][0])
              + mat[0][2] * (mat[1][0] * mat[2][1] - mat[1][1] * mat[2][0]))

    c = det3(replace_col(m, 0, ty)) / det
    b = det3(replace_col(m, 1, ty)) / det
    a = det3(replace_col(m, 2, ty)) / det
    # R-squared
    mean_y = sum(values) / n
    ss_tot = sum((v - mean_y) ** 2 for v in values)
    ss_res = sum((v - (a * i * i + b * i + c)) ** 2 for i, v in enumerate(values))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return a, b, c, r2


def detect_periodicity(values, max_period=None):
    """Detect if values are periodic. Returns (period, correlation) or None.

    Finds the first local maximum in the autocorrelation function that exceeds
    a threshold. This distinguishes true periodicity from smooth-data artifacts
    (where all small lags have high correlation simply because the data is smooth).
    """
    n = len(values)
    if max_period is None:
        max_period = min(n // 3, 1024)
    min_period = max(4, n // 64)  # skip trivially small lags
    if n < min_period * 3:
        return None

    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values)
    if var == 0:
        return None  # constant

    # Compute autocorrelation for all candidate lags
    corrs = []
    for p in range(min_period, max_period + 1):
        c = sum((values[i] - mean) * (values[i - p] - mean)
                for i in range(p, n))
        corrs.append(c / var)

    # Find first local maximum above threshold — this is the fundamental period
    threshold = 0.7
    for i in range(1, len(corrs) - 1):
        if (corrs[i] > threshold
                and corrs[i] >= corrs[i - 1]
                and corrs[i] >= corrs[i + 1]):
            return min_period + i, corrs[i]

    return None


def cmd_analyze(args):
    """Analyze data files for pre-compression optimization opportunities."""
    if not args.files:
        print("Error: no input files specified.", file=sys.stderr)
        sys.exit(1)

    all_results = []

    for filepath in args.files:
        path = Path(filepath)
        if not path.exists():
            print(f"Warning: {path} not found, skipping", file=sys.stderr)
            continue

        data = path.read_bytes()
        if not data:
            print(f"Warning: {path} is empty, skipping", file=sys.stderr)
            continue

        result = analyze_data(data, path.name, args)
        all_results.append(result)

    if args.json:
        json.dump(all_results, sys.stdout, indent=2)
        print()
        return

    for r in all_results:
        print_analysis(r)


def analyze_data(data, name, args):
    """Run all analyses on a data block. Returns a result dict."""
    n = len(data)
    values = list(data)

    # --- Basic stats ---
    h_raw = entropy(data)
    zeros = count_zeros(data)
    runs, longest_run, avg_run = count_runs(data)

    # --- Transform entropy comparison ---
    d1 = delta_encode(data)
    d2 = delta2_encode(data)
    xd = xor_encode(data)
    h_delta = entropy(d1)
    h_delta2 = entropy(d2)
    h_xor = entropy(xd)

    transforms = [
        ("raw", h_raw, n),
        ("delta (1st deriv)", h_delta, len(d1)),
        ("delta2 (2nd deriv)", h_delta2, len(d2)),
        ("xor delta", h_xor, len(xd)),
    ]

    # --- Stride / transposition analysis ---
    stride_results = []
    strides_to_test = []
    if args.stride:
        strides_to_test = [args.stride]
    else:
        # Auto-detect useful strides: common table widths
        candidates = [2, 3, 4, 6, 8, 12, 16, 32, 64, 128, 256]
        strides_to_test = [s for s in candidates if s < n and n % s == 0]
        # Also try user-hinted column count
        if args.columns and args.columns > 1:
            s = n // args.columns
            if s > 0 and s not in strides_to_test:
                strides_to_test.append(s)

    for stride in strides_to_test:
        t_data = transpose(data, stride)
        h_t = entropy(t_data)
        h_td = entropy(delta_encode(t_data))
        # Also transpose then delta — column-major + delta
        improvement = h_raw - h_t
        stride_results.append({
            "stride": stride,
            "h_transposed": h_t,
            "h_transposed_delta": h_td,
            "improvement": improvement,
            "improvement_delta": h_delta - h_td,
        })

    # --- Curve fitting (treat bytes as Y values) ---
    curve_fits = {}
    a_lin, b_lin, r2_lin = fit_linear(values)
    curve_fits["linear"] = {"a": a_lin, "b": b_lin, "r2": r2_lin}

    a_q, b_q, c_q, r2_q = fit_quadratic(values)
    curve_fits["quadratic"] = {"a": a_q, "b": b_q, "c": c_q, "r2": r2_q}

    # --- Periodicity ---
    period_result = detect_periodicity(values)

    # --- Suggestions ---
    suggestions = generate_suggestions(
        h_raw, h_delta, h_delta2, h_xor, stride_results,
        curve_fits, period_result, zeros, n, runs, avg_run
    )

    return {
        "name": name,
        "size": n,
        "entropy_raw": h_raw,
        "entropy_delta": h_delta,
        "entropy_delta2": h_delta2,
        "entropy_xor": h_xor,
        "zeros": zeros,
        "zero_pct": zeros / n,
        "runs": runs,
        "longest_run": longest_run,
        "avg_run": avg_run,
        "transforms": transforms,
        "stride_results": stride_results,
        "curve_fits": curve_fits,
        "periodicity": {
            "period": period_result[0],
            "correlation": period_result[1],
        } if period_result else None,
        "suggestions": suggestions,
    }


def generate_suggestions(h_raw, h_delta, h_delta2, h_xor, stride_results,
                          curve_fits, period_result, zeros, n, runs, avg_run):
    """Generate human-readable pre-compression suggestions."""
    suggestions = []

    # Entropy-based transform suggestions
    best_h = h_raw
    best_name = "raw"
    for name, h in [("delta", h_delta), ("delta2", h_delta2), ("xor", h_xor)]:
        if h < best_h:
            best_h = h
            best_name = name

    if best_name != "raw":
        saving = h_raw - best_h
        pct = saving / h_raw * 100 if h_raw > 0 else 0
        suggestions.append({
            "priority": "high" if pct > 10 else "medium",
            "transform": best_name,
            "detail": f"{best_name} encoding reduces entropy by {saving:.2f} "
                      f"bits/byte ({pct:.0f}%): {h_raw:.2f} -> {best_h:.2f}",
        })

    if h_delta2 < h_delta - 0.2:
        suggestions.append({
            "priority": "medium",
            "transform": "delta2",
            "detail": f"2nd derivative ({h_delta2:.2f}) beats 1st ({h_delta:.2f}) — "
                      f"data has smooth acceleration (quadratic/sinusoidal curves)",
        })

    # Transposition suggestions
    for sr in stride_results:
        if sr["improvement"] > 0.3:
            suggestions.append({
                "priority": "high" if sr["improvement"] > 0.5 else "medium",
                "transform": f"transpose(stride={sr['stride']})",
                "detail": f"Column-major with stride {sr['stride']} reduces "
                          f"entropy by {sr['improvement']:.2f} bits/byte "
                          f"({sr['h_transposed']:.2f} vs {h_raw:.2f} raw)",
            })
        # Transpose + delta combo
        if sr["h_transposed_delta"] < h_delta - 0.3:
            suggestions.append({
                "priority": "high",
                "transform": f"transpose(stride={sr['stride']})+delta",
                "detail": f"Transpose stride {sr['stride']} then delta: "
                          f"{sr['h_transposed_delta']:.2f} bits/byte "
                          f"(vs {h_delta:.2f} delta-only, {h_raw:.2f} raw)",
            })

    # Curve fit suggestions — for vector animation data
    r2_lin = curve_fits["linear"]["r2"]
    r2_q = curve_fits["quadratic"]["r2"]

    if r2_q > 0.95:
        suggestions.append({
            "priority": "high",
            "transform": "quadratic_approx",
            "detail": f"Data fits quadratic curve (R²={r2_q:.3f}) — "
                      f"store 3 coefficients + residual instead of {n} bytes. "
                      f"Derivative is linear: perfect for delta encoding.",
        })
    elif r2_lin > 0.95:
        suggestions.append({
            "priority": "high",
            "transform": "linear_approx",
            "detail": f"Data fits linear ramp (R²={r2_lin:.3f}) — "
                      f"store start + slope + residual, or generate at runtime.",
        })
    elif r2_q > 0.85:
        suggestions.append({
            "priority": "medium",
            "transform": "quadratic_approx",
            "detail": f"Rough quadratic fit (R²={r2_q:.3f}) — "
                      f"consider: if visually indistinguishable from sine decay, "
                      f"use quadratic (linear derivative compresses to nothing).",
        })

    # Periodicity suggestions
    if period_result:
        period, corr = period_result
        suggestions.append({
            "priority": "high" if corr > 0.9 else "medium",
            "transform": f"periodic(period={period})",
            "detail": f"Data repeats with period {period} (correlation {corr:.2f}) — "
                      f"store one period ({period} bytes) + delta residual, "
                      f"or use modular generation at runtime.",
        })

    # Run-length suggestions
    if avg_run > 4:
        suggestions.append({
            "priority": "medium",
            "transform": "rle",
            "detail": f"High run density (avg {avg_run:.1f} bytes/run, "
                      f"longest {runs}) — RLE as pre-pass before LZ may help.",
        })

    # Zero density
    zero_pct = zeros / n if n > 0 else 0
    if zero_pct > 0.3:
        suggestions.append({
            "priority": "medium",
            "transform": "sparse",
            "detail": f"{zeros} zero bytes ({zero_pct:.0%}) — "
                      f"consider sparse encoding (store only non-zero positions).",
        })

    # Low entropy = easy to compress regardless
    if h_raw < 3.0:
        suggestions.append({
            "priority": "info",
            "transform": "none",
            "detail": f"Already low entropy ({h_raw:.2f} bits/byte) — "
                      f"any LZ packer will compress well without transforms.",
        })

    return suggestions


def print_analysis(result):
    """Print analysis results for one file."""
    r = result
    print(f"\nPre-compression Analysis: {r['name']}")
    print(f"{'=' * 65}")
    print(f"  Size: {r['size']:,d} bytes")
    print(f"  Zeros: {r['zeros']:,d} ({r['zero_pct']:.0%})")
    print(f"  Runs: {r['runs']:,d} (avg {r['avg_run']:.1f}B, "
          f"longest {r['longest_run']}B)")

    print(f"\n  Entropy (bits/byte, lower = more compressible):")
    print(f"  {'Transform':<25s} {'Entropy':>8s} {'vs raw':>8s}")
    print(f"  {'─' * 45}")
    for name, h, _ in r["transforms"]:
        diff = h - r["entropy_raw"]
        marker = " ◀ best" if h == min(t[1] for t in r["transforms"]) else ""
        sign = "+" if diff > 0 else ""
        diff_str = f"{sign}{diff:.2f}" if name != "raw" else "—"
        print(f"  {name:<25s} {h:>7.2f}  {diff_str:>7s}{marker}")

    if r["stride_results"]:
        # Filter to interesting strides
        interesting = [s for s in r["stride_results"]
                      if s["improvement"] > 0.1 or s["improvement_delta"] > 0.1]
        if interesting:
            print(f"\n  Transposition analysis (column-major reordering):")
            print(f"  {'Stride':<8s} {'H(trans)':>9s} {'H(t+d)':>8s} "
                  f"{'vs raw':>8s} {'vs delta':>9s}")
            print(f"  {'─' * 50}")
            for sr in sorted(interesting, key=lambda x: x["h_transposed"]):
                print(f"  {sr['stride']:<8d} {sr['h_transposed']:>8.2f} "
                      f"{sr['h_transposed_delta']:>8.2f} "
                      f"{-sr['improvement']:>+7.2f} "
                      f"{-sr['improvement_delta']:>+8.2f}")

    # Curve fits
    fits = r["curve_fits"]
    print(f"\n  Curve fitting (R² > 0.85 = useful approximation):")
    print(f"  {'─' * 50}")
    lin = fits["linear"]
    quad = fits["quadratic"]
    lin_star = " ***" if lin["r2"] > 0.95 else (" **" if lin["r2"] > 0.85 else "")
    quad_star = " ***" if quad["r2"] > 0.95 else (" **" if quad["r2"] > 0.85 else "")
    print(f"  Linear:    R²={lin['r2']:.4f}  "
          f"y = {lin['a']:.3f}x + {lin['b']:.1f}{lin_star}")
    print(f"  Quadratic: R²={quad['r2']:.4f}  "
          f"y = {quad['a']:.6f}x² + {quad['b']:.3f}x + {quad['c']:.1f}{quad_star}")

    if r["periodicity"]:
        p = r["periodicity"]
        print(f"\n  Periodicity detected: period={p['period']} "
              f"(correlation {p['correlation']:.2f})")
        savings = r["size"] - p["period"]
        print(f"  Potential: store {p['period']}B + residual "
              f"instead of {r['size']:,d}B ({savings:,d}B saving before LZ)")

    if r["suggestions"]:
        print(f"\n  Suggestions:")
        print(f"  {'─' * 60}")
        for s in r["suggestions"]:
            priority_mark = {"high": ">>", "medium": " >", "info": "  "}
            mark = priority_mark.get(s["priority"], "  ")
            print(f"  {mark} [{s['transform']}] {s['detail']}")

    print()


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="packbench",
        description="Packer benchmark & streaming decompression estimator "
                    "for Z80 demoscene projects",
    )
    sub = parser.add_subparsers(dest="command")

    # bench
    p_bench = sub.add_parser("bench", help="Run packers on files")
    p_bench.add_argument("files", nargs="*", help="Input files to compress")
    p_bench.add_argument("--packers", help="Comma-separated packer names")
    p_bench.add_argument("--list-packers", action="store_true",
                         help="Show all known packers and detection status")
    p_bench.add_argument("--platform", choices=list(PLATFORMS),
                         help=f"Target platform (default: {DEFAULT_PLATFORM})")
    p_bench.add_argument("--json", action="store_true",
                         help="Output JSON for Clockwork integration")

    # budget
    p_budget = sub.add_parser("budget", help="Memory budget estimation")
    p_budget.add_argument("--config", required=True,
                          help="TOML config file path")
    p_budget.add_argument("--json", action="store_true",
                          help="Output JSON for Clockwork integration")

    # timeline
    p_timeline = sub.add_parser("timeline",
                                help="Streaming decompression schedule")
    p_timeline.add_argument("--config", required=True,
                            help="TOML config file path")
    p_timeline.add_argument("--what-if", action="store_true",
                            help="Compare all packers for each effect")
    p_timeline.add_argument("--json", action="store_true",
                            help="Output JSON for Clockwork integration")

    # analyze
    p_analyze = sub.add_parser("analyze",
                               help="Pre-compression data analysis")
    p_analyze.add_argument("files", nargs="*", help="Input data files")
    p_analyze.add_argument("--stride", type=int, default=0,
                           help="Test specific stride for transposition "
                                "(e.g. 256 for 256-byte rows)")
    p_analyze.add_argument("--columns", type=int, default=0,
                           help="Number of columns in tabular data "
                                "(auto-compute stride = size/columns)")
    p_analyze.add_argument("--json", action="store_true",
                           help="Output JSON for Clockwork integration")

    args = parser.parse_args()

    if args.command == "bench":
        cmd_bench(args)
    elif args.command == "budget":
        cmd_budget(args)
    elif args.command == "timeline":
        cmd_timeline(args)
    elif args.command == "analyze":
        cmd_analyze(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
