#!/usr/bin/env python3
"""Automated screenshot generator for book examples.

Compiles each .a80 example with sjasmplus, runs it in mzx (headless),
and captures a PNG screenshot at the specified frame.

Also generates build/screenshots/manifest.json linking each screenshot
to its source file, chapter, and capture parameters.

Usage:
    python3 tools/screenshots.py                  # all examples
    python3 tools/screenshots.py --chapter 9      # just ch09
    python3 tools/screenshots.py --name plasma    # just plasma
    python3 tools/screenshots.py --list           # show config
    python3 tools/screenshots.py --border         # include border
    python3 tools/screenshots.py --manifest-only  # regenerate manifest without screenshots
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = ROOT / "build"
SCREENSHOT_DIR = BUILD_DIR / "screenshots"
SJASMPLUS = "sjasmplus"
MZX = "mzx"

# Pre-built attribute block ($38 = white ink on black paper)
ATTRS_FILE = BUILD_DIR / "attrs_38.bin"

# Minimal IM1 ISR stub: EI ($FB) + RETI ($ED $4D) — loaded at $0038
# Required for bare-metal --run mode where no ROM provides an ISR
ISR_STUB = BUILD_DIR / "isr_stub.bin"


# ---------------------------------------------------------------------------
# Per-example configuration
# ---------------------------------------------------------------------------
# Each entry: (source_path_relative, {options})
#   frames: int — frame to capture at
#   model: str — 48k, 128k, pentagon (default: 48k)
#   attrs: bool — preload $5800 with $38 (white on black)
#   set: str — extra --set flags (appended after defaults)
#   border: bool — include border in capture (default: False)
#   skip: bool — skip this example (e.g. audio-only)
#   note: str — human-readable note

EXAMPLES = [
    # Ch01
    ("chapters/ch01-thinking-in-cycles/examples/timing_harness.a80", {
        "frames": 5, "border": True,
        "note": "Border-colour timing harness (free-running, no HALT needed)",
    }),
    # Ch02
    ("chapters/ch02-screen-as-puzzle/examples/fill_screen.a80", {
        "frames": 5, "set": "EI", "border": True,
        "note": "Checkerboard screen fill (needs EI for HALT)",
    }),
    ("chapters/ch02-screen-as-puzzle/examples/pixel_demo.a80", {
        "frames": 10, "attrs": True,
        "note": "Pixel plotting demo",
    }),
    # Ch03
    ("chapters/ch03-demoscene-toolbox/examples/push_fill.a80", {
        "frames": 5, "border": True,
        "note": "PUSH-based screen fill (free-running, border for timing stripe)",
    }),
    ("chapters/ch03-demoscene-toolbox/examples/ldi_chain.a80", {
        "frames": 5, "border": True,
        "note": "LDI chain vs LDIR comparison (free-running, border stripes)",
    }),
    # Ch04
    ("chapters/ch04-maths/examples/multiply8.a80", {
        "frames": 5, "border": True,
        "note": "8-bit multiply routine (border = result AND 7 = cyan)",
    }),
    ("chapters/ch04-maths/examples/prng.a80", {
        "frames": 30, "attrs": True,
        "note": "PRNG filling attributes with random colours",
    }),
    # Ch05
    ("chapters/ch05-3d/examples/wireframe_cube.a80", {
        "frames": 100,
        "note": "Rotating wireframe cube",
    }),
    # Ch06
    ("chapters/ch06-sphere/examples/sphere.a80", {
        "frames": 100,
        "note": "Sphere outline",
    }),
    # Ch07
    ("chapters/ch07-rotozoomer/examples/rotozoomer.a80", {
        "frames": 100,
        "note": "Rotating/zooming texture",
    }),
    # Ch08
    ("chapters/ch08-multicolor/examples/multicolor.a80", {
        "frames": 50, "set": "EI,IM=1",
        "note": "Multicolour effect (beam-racing, timing-dependent)",
    }),
    ("chapters/ch08-multicolor/examples/multicolor_dualscreen.a80", {
        "frames": 50, "model": "128k", "set": "EI,IM=1",
        "note": "Dual-screen multicolour (128K, beam-racing)",
    }),
    # Ch09
    ("chapters/ch09-tunnels/examples/plasma.a80", {
        "frames": 100,
        "note": "Attribute-based plasma effect",
    }),
    # Ch10
    ("chapters/ch10-scroller/examples/dotscroll.a80", {
        "frames": 33, "set": "EI",
        "note": "Bouncing dotfield text scroller (frame-sensitive: render takes >1 frame)",
    }),
    # Ch11
    ("chapters/ch11-sound/examples/ay_test.a80", {
        "frames": 50, "skip": True,
        "note": "AY sound test (audio only, no visual)",
    }),
    # Ch12
    ("chapters/ch12-music-sync/examples/music_sync.a80", {
        "frames": 200, "set": "EI,IM=1", "skip": True,
        "note": "Music sync framework (IM2 pipeline — mzx IM2 not yet working in bare-metal mode)",
    }),
    # Ch13
    ("chapters/ch13-sizecoding/examples/intro256.a80", {
        "frames": 500, "set": "EI,IM=1",
        "note": "256-byte intro (no EI in code, needs it from config)",
    }),
    ("chapters/ch13-sizecoding/examples/aybeat.a80", {
        "frames": 100, "skip": True,
        "note": "AY-beat engine (audio only)",
    }),
    # Ch14
    ("chapters/ch14-compression/examples/decompress.a80", {
        "frames": 30, "attrs": True,
        "note": "Decompression demo",
    }),
    ("chapters/ch14-compression/examples/rle_intro.a80", {
        "frames": 10, "border": True, "sna": "rle_intro.sna",
        "note": "Ped7g's 120-byte self-modifying RLE intro (SAVESNA, 48K)",
    }),
    # Ch15
    ("chapters/ch15-anatomy/examples/bank_inspect.a80", {
        "frames": 30, "model": "128k", "set": "EI", "skip": True,
        "note": "128K RAM bank inspector (needs ROM font at $3D00 — not available in bare-metal mode)",
    }),
    # Ch16
    ("chapters/ch16-sprites/examples/sprite_demo.a80", {
        "frames": 100,
        "note": "OR+AND masked sprite with movement",
    }),
    # Ch17
    ("chapters/ch17-scrolling/examples/hscroll.a80", {
        "frames": 200,
        "note": "Horizontal pixel scroller",
    }),
    # Ch18
    ("chapters/ch18-gameloop/examples/game_skeleton.a80", {
        "frames": 200, "skip": True,
        "note": "Game loop skeleton (needs FIRE key input to render)",
    }),
    # Ch19
    ("chapters/ch19-collisions/examples/aabb_test.a80", {
        "frames": 100, "set": "EI",
        "note": "AABB collision detection test",
    }),
    # Ch20
    ("chapters/ch20-demo-workflow/examples/demo_framework.a80", {
        "frames": 100,
        "note": "Demo framework with effect slots",
    }),
    # Ch21
    ("chapters/ch21-full-game/examples/game_skeleton.a80", {
        "frames": 200, "model": "128k", "skip": True,
        "note": "Full game skeleton (128K, needs SPACE key input to render)",
    }),
    # Ch22
    ("chapters/ch22-porting-agon/examples/agon_entity.a80", {
        "frames": 100, "skip": True,
        "note": "Agon VDP port stub (no screen memory writes)",
    }),
    # Ch23
    ("chapters/ch23-ai-assisted/examples/diagonal_fill.a80", {
        "frames": 30, "attrs": True, "set": "EI",
        "note": "AI-generated diagonal fill (needs pixel fill fix for visibility)",
    }),
]


# ---------------------------------------------------------------------------
# Browser prototype screenshots (Chrome headless)
# ---------------------------------------------------------------------------
# Each entry: (html_path_relative, {options})
#   chapter: int — chapter number (for id prefix)
#   note: str — description
#   needs_raf: bool — uses requestAnimationFrame (won't render in headless)

PROTOTYPES = [
    ("verify/ch02_screen_layout.html", {
        "chapter": 2,
        "note": "ZX Spectrum screen memory layout visualiser",
    }),
    ("verify/ch05_3d.html", {
        "chapter": 5,
        "note": "3D wireframe rotation prototype",
        "needs_raf": True,
    }),
    ("verify/ch06_sphere.html", {
        "chapter": 6,
        "note": "Sphere outline rendering prototype",
    }),
    ("verify/ch07_rotozoomer.html", {
        "chapter": 7,
        "note": "Rotozoomer texture mapping prototype",
        "needs_raf": True,
    }),
    ("verify/ch08_multicolor.html", {
        "chapter": 8,
        "note": "Multicolour beam-racing prototype",
    }),
    ("verify/ch09_plasma.html", {
        "chapter": 9,
        "note": "Attribute plasma effect prototype",
    }),
    ("verify/ch10_dotfield.html", {
        "chapter": 10,
        "note": "Bouncing dotfield scroller prototype",
    }),
    ("verify/ch16_sprites.html", {
        "chapter": 16,
        "note": "XOR/OR/AND sprite rendering prototype",
    }),
    ("verify/ch17_scrolling.html", {
        "chapter": 17,
        "note": "Horizontal pixel scrolling prototype",
    }),
    ("verify/torus.html", {
        "chapter": 20,
        "note": "Wireframe torus rotation prototype (Antique Toy demo)",
    }),
]


def ensure_preloads():
    """Create pre-built binary files for screenshot pipeline."""
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    if not ATTRS_FILE.exists():
        ATTRS_FILE.write_bytes(b'\x38' * 768)
    if not ISR_STUB.exists():
        # EI ($FB) + RETI ($ED $4D) — minimal IM1 handler at $0038
        ISR_STUB.write_bytes(b'\xfb\xed\x4d')


def compile_example(src_path, sna=None):
    """Compile .a80 to .bin (or .sna) with sjasmplus. Returns output path or None."""
    if sna:
        # SNA mode: source uses DEVICE + SAVESNA, compile without --raw
        sna_path = BUILD_DIR / sna
        result = subprocess.run(
            [SJASMPLUS, "--nologo", str(src_path)],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return None, result.stderr.strip()
        if not sna_path.exists():
            return None, f"SNA not produced: {sna_path}"
        return sna_path, None
    else:
        bin_path = BUILD_DIR / (src_path.stem + ".bin")
        result = subprocess.run(
            [SJASMPLUS, "--nologo", f"--raw={bin_path}", str(src_path)],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return None, result.stderr.strip()
        return bin_path, None


def take_screenshot(bin_path, png_path, opts):
    """Run mzx and capture a screenshot."""
    frames = opts.get("frames", 50)
    model = opts.get("model", "48k")
    attrs = opts.get("attrs", False)
    extra_set = opts.get("set", "")
    border = opts.get("border", False)
    sna = opts.get("sna", None)

    cmd = [MZX, "--model", model]

    if sna:
        # SNA mode: load snapshot directly (DEVICE+SAVESNA examples)
        cmd += ["--snapshot", str(bin_path)]
    elif attrs or (extra_set and any(f.strip().upper() == "EI" for f in extra_set.split(","))):
        # Use --load mode: allows preloading ISR stub + attrs + code
        needs_isr = any(f.strip().upper() == "EI" for f in extra_set.split(",")) if extra_set else False
        loads = f"{bin_path}@8000"
        if attrs:
            loads = f"{ATTRS_FILE}@5800," + loads
        if needs_isr:
            loads += f",{ISR_STUB}@0038"
        cmd += ["--load", loads]
        set_flags = "PC=8000,SP=FF00,DI,IM=1"
        if extra_set:
            set_flags += "," + extra_set
        cmd += ["--set", set_flags]
    else:
        # Use --run for simple cases (no ISR needed)
        cmd += ["--run", f"{bin_path}@8000"]
        if extra_set:
            cmd += ["--set", extra_set]

    cmd += ["--frames", str(frames)]
    cmd += ["--screenshot", str(png_path)]

    if not border:
        cmd += ["--no-border"]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.returncode == 0, result.stderr.strip()


def get_chapter_num(src_path):
    """Extract chapter number from path."""
    import re
    m = re.search(r'ch(\d+)', str(src_path))
    return int(m.group(1)) if m else 0


def build_manifest():
    """Generate manifest.json linking screenshots to their sources."""
    manifest = {}

    # mzx screenshots
    for rel_path, opts in EXAMPLES:
        src = ROOT / rel_path
        ch = get_chapter_num(src)
        sid = f"ch{ch:02d}_{src.stem}"
        png = SCREENSHOT_DIR / f"{sid}.png"

        entry = {
            "type": "mzx",
            "id": sid,
            "source": rel_path,
            "chapter": ch,
            "png": f"build/screenshots/{sid}.png",
            "exists": png.exists(),
            "frames": opts.get("frames", 50),
            "model": opts.get("model", "48k"),
            "border": opts.get("border", False),
        }
        if opts.get("skip"):
            entry["skip"] = True
            entry["skip_reason"] = opts.get("note", "")
        if opts.get("note"):
            entry["note"] = opts["note"]
        if opts.get("set"):
            entry["mzx_set"] = opts["set"]
        if opts.get("attrs"):
            entry["attrs"] = True

        manifest[sid] = entry

    # Browser prototypes
    for rel_path, opts in PROTOTYPES:
        src = ROOT / rel_path
        ch = opts["chapter"]
        stem = src.stem
        sid = f"proto_{stem}"
        png = SCREENSHOT_DIR / f"{sid}.png"

        entry = {
            "type": "browser",
            "id": sid,
            "source": rel_path,
            "chapter": ch,
            "png": f"build/screenshots/{sid}.png",
            "exists": png.exists(),
            "tool": "chrome-headless",
        }
        if opts.get("needs_raf"):
            entry["needs_raf"] = True
            entry["note"] = opts.get("note", "") + " (needs manual capture — rAF doesn't fire in headless)"
        elif opts.get("note"):
            entry["note"] = opts["note"]

        manifest[sid] = entry

    manifest_path = SCREENSHOT_DIR / "manifest.json"
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\nManifest: {manifest_path} ({len(manifest)} entries)")
    return manifest_path


def main():
    parser = argparse.ArgumentParser(
        description="Automated screenshot generator for book examples",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--chapter", type=int, help="Only process this chapter number")
    parser.add_argument("--name", help="Only process examples matching this name")
    parser.add_argument("--list", action="store_true", help="List all examples and exit")
    parser.add_argument("--border", action="store_true", help="Include border in captures")
    parser.add_argument("--force", action="store_true", help="Regenerate even if PNG exists")
    parser.add_argument("--include-skipped", action="store_true",
                        help="Include audio-only examples")
    parser.add_argument("--manifest-only", action="store_true",
                        help="Regenerate manifest.json without taking screenshots")
    args = parser.parse_args()

    # Manifest-only mode: just regenerate JSON and exit
    if args.manifest_only:
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        build_manifest()
        return

    # Check tools
    for tool in [SJASMPLUS, MZX]:
        result = subprocess.run(["which", tool], capture_output=True)
        if result.returncode != 0:
            print(f"ERROR: {tool} not found in PATH", file=sys.stderr)
            sys.exit(1)

    ensure_preloads()
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    # Filter examples
    examples = []
    for rel_path, opts in EXAMPLES:
        src = ROOT / rel_path
        ch = get_chapter_num(src)

        if args.chapter and ch != args.chapter:
            continue
        if args.name and args.name.lower() not in src.stem.lower():
            continue

        examples.append((src, opts))

    if args.list:
        print(f"{'Example':<40s} {'Frames':>6s} {'Model':>6s} {'Attrs':>5s} {'Skip':>5s}  Note")
        print("-" * 100)
        for src, opts in examples:
            name = src.stem
            print(f"{name:<40s} {opts.get('frames', 50):6d} "
                  f"{opts.get('model', '48k'):>6s} "
                  f"{'yes' if opts.get('attrs') else '':>5s} "
                  f"{'SKIP' if opts.get('skip') else '':>5s}  "
                  f"{opts.get('note', '')}")
        print(f"\n{len(examples)} examples configured")
        return

    # Process
    ok = 0
    fail = 0
    skip = 0

    for src, opts in examples:
        name = src.stem
        ch = get_chapter_num(src)
        png_name = f"ch{ch:02d}_{name}"
        png = SCREENSHOT_DIR / f"{png_name}.png"

        if opts.get("skip") and not args.include_skipped:
            print(f"  SKIP  {name:30s}  {opts.get('note', '')}")
            skip += 1
            continue

        if png.exists() and not args.force:
            print(f"  EXIST {name:30s}  {png.name}")
            ok += 1
            continue

        # Override border from CLI
        if args.border:
            opts = dict(opts, border=True)

        # Compile
        bin_path, err = compile_example(src, sna=opts.get("sna"))
        if not bin_path:
            print(f"  FAIL  {name:30s}  compile error: {err}")
            fail += 1
            continue

        # Screenshot
        success, err = take_screenshot(bin_path, png, opts)
        if success:
            print(f"  OK    {name:30s}  → {png.name}")
            ok += 1
        else:
            print(f"  FAIL  {name:30s}  mzx error: {err}")
            fail += 1

    print(f"\n---")
    print(f"{ok} OK, {fail} failed, {skip} skipped")

    # Always regenerate manifest after screenshots
    build_manifest()

    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
