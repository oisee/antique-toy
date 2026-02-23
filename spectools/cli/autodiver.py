#!/usr/bin/env python3
"""Attribute Grid Optimizer for ZX Spectrum image conversion.

Finds the best (shift_x, shift_y, scale) combination that minimizes
attribute clash when an image is mapped onto the ZX Spectrum's 8x8
colour cell grid. Each 8x8 cell can hold at most 2 colours; pixels
that fall outside the top-2 most frequent colours are counted as
penalty.

This is a Python reimplementation of oisee/autodiver_go.

Usage:
  python autodiver.py photo.png                      # offset-only scan
  python autodiver.py photo.png -s 64                # scan scales 0..64
  python autodiver.py photo.png -s 64 -ss 4          # scale step 4
  python autodiver.py photo.png --palette zx -n 16   # ZX quantize, top 16
  python autodiver.py photo.png -m -p 3              # use significance mask
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Sequence

try:
    from PIL import Image
except ImportError:
    print(
        "Error: Pillow is required but not installed.\n"
        "Install it with:  pip install Pillow",
        file=sys.stderr,
    )
    sys.exit(1)

# ── Constants ─────────────────────────────────────────────────────────

# Target resolution: ZX Spectrum screen
ZX_WIDTH = 256
ZX_HEIGHT = 192
CELL_SIZE = 8
CELLS_X = ZX_WIDTH // CELL_SIZE   # 32
CELLS_Y = ZX_HEIGHT // CELL_SIZE  # 24
TOTAL_CELLS = CELLS_X * CELLS_Y   # 768

# ZX Spectrum palette — 15 unique colours (black shared between normal/bright)
ZX_PALETTE: list[tuple[int, int, int]] = [
    # Normal intensity
    (0, 0, 0),        # Black
    (0, 0, 215),      # Blue
    (215, 0, 0),      # Red
    (215, 0, 215),    # Magenta
    (0, 215, 0),      # Green
    (0, 215, 215),    # Cyan
    (215, 215, 0),    # Yellow
    (215, 215, 215),  # White
    # Bright intensity (black is the same, omitted)
    (0, 0, 255),      # Bright Blue
    (255, 0, 0),      # Bright Red
    (255, 0, 255),    # Bright Magenta
    (0, 255, 0),      # Bright Green
    (0, 255, 255),    # Bright Cyan
    (255, 255, 0),    # Bright Yellow
    (255, 255, 255),  # Bright White
]


# ── ZX Palette Quantization ──────────────────────────────────────────

def _build_palette_lut() -> dict[tuple[int, int, int], tuple[int, int, int]]:
    """Pre-build a lookup table is not practical for 16M colours.
    Instead we cache on the fly during quantization."""
    return {}


def _nearest_zx(rgb: tuple[int, int, int],
                 cache: dict[tuple[int, int, int], tuple[int, int, int]]) -> tuple[int, int, int]:
    """Return the nearest ZX palette colour for an RGB tuple (Euclidean distance)."""
    cached = cache.get(rgb)
    if cached is not None:
        return cached
    r, g, b = rgb
    best_colour = ZX_PALETTE[0]
    best_dist = float("inf")
    for pr, pg, pb in ZX_PALETTE:
        d = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if d < best_dist:
            best_dist = d
            best_colour = (pr, pg, pb)
            if d == 0:
                break
    cache[rgb] = best_colour
    return best_colour


def quantize_image(img: Image.Image) -> Image.Image:
    """Quantize an RGB image to the ZX Spectrum palette in-place (returns new image)."""
    img = img.copy()
    pixels = img.load()
    w, h = img.size
    cache: dict[tuple[int, int, int], tuple[int, int, int]] = {}
    for y in range(h):
        for x in range(w):
            pixels[x, y] = _nearest_zx(pixels[x, y], cache)
    return img


# ── Cell Penalty ──────────────────────────────────────────────────────

def cell_penalty(img_pixels, cx: int, cy: int) -> int:
    """Calculate penalty for one 8x8 cell at cell coordinates (cx, cy).

    Returns the number of pixels that are NOT one of the top-2 most
    frequent colours in the cell.
    """
    x0 = cx * CELL_SIZE
    y0 = cy * CELL_SIZE
    counts: Counter[tuple[int, int, int]] = Counter()
    for dy in range(CELL_SIZE):
        for dx in range(CELL_SIZE):
            counts[img_pixels[x0 + dx, y0 + dy]] += 1

    if len(counts) <= 2:
        return 0

    # Top-2 most frequent colours
    top2 = counts.most_common(2)
    top2_total = top2[0][1] + top2[1][1]
    return CELL_SIZE * CELL_SIZE - top2_total


# ── Significance Mask ─────────────────────────────────────────────────

def load_mask(input_path: Path) -> Image.Image | None:
    """Look for mask_<filename> in the same directory as input. Return or None."""
    mask_name = f"mask_{input_path.name}"
    mask_path = input_path.parent / mask_name
    if not mask_path.exists():
        return None
    try:
        mask = Image.open(mask_path).convert("L")
        return mask
    except Exception as e:
        print(f"Warning: could not load mask {mask_path}: {e}", file=sys.stderr)
        return None


def build_cell_mask(mask_img: Image.Image, shift_x: int, shift_y: int,
                    scaled_w: int, scaled_h: int) -> list[list[bool]]:
    """Resize and crop the mask the same way as the image, then determine
    which cells are 'significant' (contain any white pixel)."""
    # Resize mask to same dimensions as the scaled image
    resized = mask_img.resize((scaled_w, scaled_h), Image.NEAREST)

    # Crop to 256x192 at the given shift
    cropped = resized.crop((shift_x, shift_y, shift_x + ZX_WIDTH, shift_y + ZX_HEIGHT))
    mpx = cropped.load()

    significant: list[list[bool]] = []
    for cy in range(CELLS_Y):
        row: list[bool] = []
        for cx in range(CELLS_X):
            x0 = cx * CELL_SIZE
            y0 = cy * CELL_SIZE
            is_sig = False
            for dy in range(CELL_SIZE):
                for dx in range(CELL_SIZE):
                    if mpx[x0 + dx, y0 + dy] > 127:
                        is_sig = True
                        break
                if is_sig:
                    break
            row.append(is_sig)
        significant.append(row)
    return significant


# ── Progress Bar ──────────────────────────────────────────────────────

def progress_bar(current: int, total: int, bar_width: int = 40,
                 start_time: float | None = None) -> None:
    """Print a simple progress bar to stderr."""
    if total == 0:
        return
    frac = current / total
    filled = int(bar_width * frac)
    bar = "=" * filled
    if filled < bar_width:
        bar += ">"
        bar += " " * (bar_width - filled - 1)
    pct = int(frac * 100)

    eta_str = ""
    if start_time is not None and current > 0:
        elapsed = time.monotonic() - start_time
        remaining = elapsed / current * (total - current)
        if remaining >= 60:
            eta_str = f" ETA {int(remaining // 60)}m{int(remaining % 60):02d}s"
        else:
            eta_str = f" ETA {int(remaining)}s"

    print(f"\r  [{bar}] {pct:3d}% ({current}/{total}){eta_str}  ",
          end="", file=sys.stderr)


# ── Main Algorithm ────────────────────────────────────────────────────

def evaluate_variant(img: Image.Image, use_palette: bool,
                     cell_mask: list[list[bool]] | None,
                     extra_penalty: int) -> int:
    """Evaluate total penalty for a 256x192 image variant."""
    if use_palette:
        img = quantize_image(img)

    pixels = img.load()
    total = 0
    for cy in range(CELLS_Y):
        for cx in range(CELLS_X):
            p = cell_penalty(pixels, cx, cy)
            if cell_mask is not None and cell_mask[cy][cx]:
                p *= extra_penalty
            total += p
    return total


def run_scan(
    input_path: Path,
    max_scale: int,
    scale_step: int,
    use_mask: bool,
    extra_penalty: int,
    output_dir: Path,
    top_n: int,
    palette: str | None,
    show_progress: bool,
) -> None:
    """Run the full attribute grid scan."""
    # Load input image
    try:
        src_img = Image.open(input_path).convert("RGB")
    except Exception as e:
        print(f"Error: cannot open image '{input_path}': {e}", file=sys.stderr)
        sys.exit(1)

    src_w, src_h = src_img.size
    use_palette = palette in ("zx", "zx15")

    # Load significance mask if requested
    mask_img: Image.Image | None = None
    if use_mask:
        mask_img = load_mask(input_path)
        if mask_img is None:
            print(f"Warning: -m specified but mask file 'mask_{input_path.name}' "
                  f"not found in {input_path.parent}. Proceeding without mask.",
                  file=sys.stderr)
            use_mask = False

    # Build list of scale values to test
    scales = list(range(0, max_scale + 1, max(1, scale_step)))

    # Build list of all variants
    variants: list[tuple[int, int, int]] = []  # (shift_x, shift_y, scale)
    for scale in scales:
        target_w = ZX_WIDTH + scale
        # Compute corresponding height maintaining aspect ratio
        target_h = int(target_w * src_h / src_w)
        # Need at least 192 pixels of height to crop
        if target_h < ZX_HEIGHT:
            # Scale height to minimum 192, recompute width
            target_h = ZX_HEIGHT
            target_w = int(target_h * src_w / src_h)
            if target_w < ZX_WIDTH:
                continue  # image too small even after scaling

        max_sx = min(7, target_w - ZX_WIDTH)
        max_sy = min(7, target_h - ZX_HEIGHT)

        for sy in range(max_sy + 1):
            for sx in range(max_sx + 1):
                variants.append((sx, sy, scale))

    total_variants = len(variants)
    if total_variants == 0:
        print("Error: no valid variants to test. Image may be too small.", file=sys.stderr)
        sys.exit(1)

    if show_progress:
        print(f"Testing {total_variants} variants...", file=sys.stderr)

    # Evaluate all variants
    results: list[tuple[int, int, int, int]] = []  # (penalty, sx, sy, scale)
    start_time = time.monotonic()

    # Cache resized images per scale to avoid redundant resizing
    resized_cache: dict[int, Image.Image] = {}

    for idx, (sx, sy, scale) in enumerate(variants):
        if show_progress and (idx % 10 == 0 or idx == total_variants - 1):
            progress_bar(idx + 1, total_variants, start_time=start_time)

        # Get or create resized image for this scale
        if scale not in resized_cache:
            target_w = ZX_WIDTH + scale
            target_h = int(target_w * src_h / src_w)
            if target_h < ZX_HEIGHT:
                target_h = ZX_HEIGHT
                target_w = int(target_h * src_w / src_h)
            resized = src_img.resize((target_w, target_h), Image.LANCZOS)
            resized_cache[scale] = resized

        resized = resized_cache[scale]

        # Crop 256x192 region
        cropped = resized.crop((sx, sy, sx + ZX_WIDTH, sy + ZX_HEIGHT))

        # Build cell mask for this variant if using significance mask
        cell_mask: list[list[bool]] | None = None
        if use_mask and mask_img is not None:
            rw, rh = resized.size
            cell_mask = build_cell_mask(mask_img, sx, sy, rw, rh)

        penalty = evaluate_variant(cropped, use_palette, cell_mask, extra_penalty)
        results.append((penalty, sx, sy, scale))

    if show_progress:
        progress_bar(total_variants, total_variants, start_time=start_time)
        elapsed = time.monotonic() - start_time
        print(f"\nDone in {elapsed:.1f}s.", file=sys.stderr)

    # Sort by penalty ascending
    results.sort(key=lambda r: r[0])

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save top N variant images
    saved = min(top_n, len(results))
    if show_progress:
        print(f"Saving top {saved} variants to {output_dir}/", file=sys.stderr)

    for rank, (penalty, sx, sy, scale) in enumerate(results[:saved], start=1):
        # Reconstruct the cropped image
        if scale not in resized_cache:
            target_w = ZX_WIDTH + scale
            target_h = int(target_w * src_h / src_w)
            if target_h < ZX_HEIGHT:
                target_h = ZX_HEIGHT
                target_w = int(target_h * src_w / src_h)
            resized_cache[scale] = src_img.resize((target_w, target_h), Image.LANCZOS)

        resized = resized_cache[scale]
        cropped = resized.crop((sx, sy, sx + ZX_WIDTH, sy + ZX_HEIGHT))

        if use_palette:
            cropped = quantize_image(cropped)

        filename = f"{rank:03d}_penalty_{penalty:04d}_sx_{sx}_sy_{sy}_sc_{scale}.png"
        cropped.save(output_dir / filename)

    # Write rating CSV
    csv_path = output_dir / "rating.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["penalty", "shift_x", "shift_y", "scale"])
        for penalty, sx, sy, scale in results:
            writer.writerow([penalty, sx, sy, scale])

    if show_progress:
        best = results[0]
        print(f"Best: penalty={best[0]}, shift_x={best[1]}, "
              f"shift_y={best[2]}, scale={best[3]}", file=sys.stderr)
        print(f"Rating saved to {csv_path}", file=sys.stderr)


# ── CLI ───────────────────────────────────────────────────────────────

def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="autodiver",
        description=(
            "Attribute Grid Optimizer for ZX Spectrum image conversion.\n"
            "Finds the best (shift, scale) combination that minimizes\n"
            "attribute clash on the ZX Spectrum's 8x8 colour cell grid."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s photo.png                       # offset-only scan\n"
            "  %(prog)s photo.png -s 64 -ss 4           # scale up to +64px, step 4\n"
            "  %(prog)s photo.png --palette zx -n 16    # quantize to ZX, save top 16\n"
            "  %(prog)s photo.png -m -p 3               # significance mask, 3x penalty\n"
        ),
    )

    parser.add_argument(
        "input",
        type=Path,
        help="Input image file (PNG, BMP, JPG)",
    )
    parser.add_argument(
        "-s",
        type=int,
        default=0,
        metavar="N",
        help="Max scale addition in pixels (default: 0 = offset only)",
    )
    parser.add_argument(
        "-ss",
        type=int,
        default=1,
        metavar="N",
        help="Scale step (default: 1)",
    )
    parser.add_argument(
        "-m",
        action="store_true",
        help="Use significance mask (looks for mask_<filename> in same dir)",
    )
    parser.add_argument(
        "-p",
        type=int,
        default=1,
        metavar="N",
        help="Extra penalty multiplier for masked cells (default: 1)",
    )
    parser.add_argument(
        "-b",
        type=Path,
        default=Path("best"),
        metavar="DIR",
        help="Output directory (default: ./best)",
    )
    parser.add_argument(
        "-n",
        type=int,
        default=8,
        metavar="N",
        help="Save top N results (default: 8)",
    )
    parser.add_argument(
        "--palette",
        choices=["zx", "zx15"],
        default=None,
        help="Quantize to ZX palette before evaluation",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Suppress progress bar output",
    )

    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)

    if not args.input.exists():
        print(f"Error: input file '{args.input}' not found.", file=sys.stderr)
        sys.exit(1)

    run_scan(
        input_path=args.input,
        max_scale=args.s,
        scale_step=args.ss,
        use_mask=args.m,
        extra_penalty=args.p,
        output_dir=args.b,
        top_n=args.n,
        palette=args.palette,
        show_progress=not args.no_progress,
    )


if __name__ == "__main__":
    main()
