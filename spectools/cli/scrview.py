#!/usr/bin/env python3
"""ZX Spectrum Screen (.scr) Viewer.

Renders ZX Spectrum screen dumps (6912-byte .scr files) in the terminal
using ANSI escape codes, or exports as HTML (with embedded SVG or PNG).

Supports the full ZX Spectrum screen layout:
  Pixel data  $4000-$57FF  (6144 bytes) -- 3 thirds, interleaved scan rows
  Attr data   $5800-$5AFF  (768 bytes)  -- 32x24 colour grid

Usage:
  python scrview.py screen.scr                     # ANSI terminal output
  python scrview.py screen.scr --html out.html     # HTML file
  python scrview.py screen.scr --info              # Screen statistics
  python scrview.py screen.scr --grid              # Show 8x8 attr grid
  python scrview.py screen.scr --clash             # Highlight colour clash
  python scrview.py screen.scr --attr-only         # Attrs without pixels
"""

from __future__ import annotations

import argparse
import html as html_mod
import io
import sys
from pathlib import Path

# ── ZX Spectrum colour palette ────────────────────────────────────────

# Indexed as ZX_PALETTE[bright][colour_index] -> (r, g, b)
ZX_PALETTE: list[list[tuple[int, int, int]]] = [
    # Normal (bright=0)
    [
        (0, 0, 0),        # 0: Black
        (0, 0, 215),      # 1: Blue
        (215, 0, 0),      # 2: Red
        (215, 0, 215),    # 3: Magenta
        (0, 215, 0),      # 4: Green
        (0, 215, 215),    # 5: Cyan
        (215, 215, 0),    # 6: Yellow
        (215, 215, 215),  # 7: White
    ],
    # Bright (bright=1)
    [
        (0, 0, 0),        # 0: Black (same)
        (0, 0, 255),      # 1: Blue
        (255, 0, 0),      # 2: Red
        (255, 0, 255),    # 3: Magenta
        (0, 255, 0),      # 4: Green
        (0, 255, 255),    # 5: Cyan
        (255, 255, 0),    # 6: Yellow
        (255, 255, 255),  # 7: White
    ],
]

COLOUR_NAMES = ["Black", "Blue", "Red", "Magenta", "Green", "Cyan", "Yellow", "White"]

# Screen dimensions
SCR_WIDTH_PX = 256
SCR_HEIGHT_PX = 192
SCR_COLS = 32       # character columns (256 / 8)
SCR_ROWS = 24       # character rows (192 / 8)
PIXEL_SIZE = 6144   # bytes of pixel data
ATTR_SIZE = 768     # bytes of attribute data
SCR_SIZE = PIXEL_SIZE + ATTR_SIZE  # 6912 bytes


# ── Screen data decode ────────────────────────────────────────────────

def scr_pixel_offset(x_byte: int, y_pixel: int) -> int:
    """Return byte offset within pixel data for column x_byte (0..31),
    scan line y_pixel (0..191).

    ZX Spectrum screen address encoding:
      High byte: 010 TT SSS  (T = third 0-2, S = scanline-in-char 0-7)
      Low byte:  LLL CCCCC   (L = char-row-in-third 0-7, C = column 0-31)

    Offset from base = ((y & 0xC0) << 5) | ((y & 0x07) << 8)
                      | ((y & 0x38) << 2) | x_byte
    """
    return (
        ((y_pixel & 0xC0) << 5)
        | ((y_pixel & 0x07) << 8)
        | ((y_pixel & 0x38) << 2)
        | x_byte
    )


def decode_pixels(pixel_data: bytes) -> list[list[int]]:
    """Decode pixel data into a 192x256 bitmap.
    Returns rows[y][x] where value is 0 or 1."""
    rows: list[list[int]] = []
    for y in range(SCR_HEIGHT_PX):
        row: list[int] = []
        for x_byte in range(SCR_COLS):
            offset = scr_pixel_offset(x_byte, y)
            byte_val = pixel_data[offset]
            for bit in range(7, -1, -1):
                row.append((byte_val >> bit) & 1)
        rows.append(row)
    return rows


def decode_attr(attr_byte: int) -> tuple[int, int, int, int]:
    """Decode an attribute byte.
    Returns (ink, paper, bright, flash)."""
    flash = (attr_byte >> 7) & 1
    bright = (attr_byte >> 6) & 1
    paper = (attr_byte >> 3) & 7
    ink = attr_byte & 7
    return ink, paper, bright, flash


def get_attr(attr_data: bytes, char_row: int, char_col: int) -> tuple[int, int, int, int]:
    """Get attribute for character cell (char_row 0..23, char_col 0..31).
    Returns (ink, paper, bright, flash)."""
    offset = char_row * SCR_COLS + char_col
    return decode_attr(attr_data[offset])


def pixel_colour(
    pixels: list[list[int]],
    attr_data: bytes,
    x: int,
    y: int,
) -> tuple[int, int, int]:
    """Return the RGB colour of pixel at (x, y)."""
    char_row = y // 8
    char_col = x // 8
    ink, paper, bright, _flash = get_attr(attr_data, char_row, char_col)
    if pixels[y][x]:
        return ZX_PALETTE[bright][ink]
    else:
        return ZX_PALETTE[bright][paper]


def pixel_colour_attr_only(
    attr_data: bytes,
    x: int,
    y: int,
) -> tuple[int, int, int]:
    """Return colour for attr-only mode: left half = ink, right half = paper."""
    char_row = y // 8
    char_col = x // 8
    ink, paper, bright, _flash = get_attr(attr_data, char_row, char_col)
    x_in_cell = x % 8
    if x_in_cell < 4:
        return ZX_PALETTE[bright][ink]
    else:
        return ZX_PALETTE[bright][paper]


# ── ANSI terminal output ─────────────────────────────────────────────

def ansi_fg_bg(fg: tuple[int, int, int], bg: tuple[int, int, int]) -> str:
    """Return ANSI 24-bit colour escape for foreground + background."""
    return (
        f"\033[38;2;{fg[0]};{fg[1]};{fg[2]}m"
        f"\033[48;2;{bg[0]};{bg[1]};{bg[2]}m"
    )


def ansi_bg(colour: tuple[int, int, int]) -> str:
    """Return ANSI 24-bit background colour escape."""
    return f"\033[48;2;{colour[0]};{colour[1]};{colour[2]}m"


ANSI_RESET = "\033[0m"
UPPER_HALF = "\u2580"  # upper half block


def render_ansi(
    pixels: list[list[int]],
    attr_data: bytes,
    *,
    attr_only: bool = False,
    grid: bool = False,
    clash_cells: set[tuple[int, int]] | None = None,
    border: int = 0,
) -> str:
    """Render screen to ANSI string using half-block characters.

    Each terminal character cell represents 2 vertical pixels:
      - Upper pixel colour as foreground (via UPPER_HALF char)
      - Lower pixel colour as background

    Output: 256 chars wide, 96 rows tall (plus optional border).
    """
    lines: list[str] = []
    border_rgb = ZX_PALETTE[0][border & 7]

    # Optional top border (2 rows = 1 terminal line)
    if border:
        border_line = ansi_bg(border_rgb) + " " * (SCR_WIDTH_PX + 4) + ANSI_RESET
        lines.append(border_line)

    for term_row in range(SCR_HEIGHT_PX // 2):
        y_top = term_row * 2
        y_bot = y_top + 1
        parts: list[str] = []

        if border:
            parts.append(ansi_bg(border_rgb) + "  ")

        prev_fg: tuple[int, int, int] | None = None
        prev_bg: tuple[int, int, int] | None = None

        for x in range(SCR_WIDTH_PX):
            if attr_only:
                fg = pixel_colour_attr_only(attr_data, x, y_top)
                bg = pixel_colour_attr_only(attr_data, x, y_bot)
            else:
                fg = pixel_colour(pixels, attr_data, x, y_top)
                bg = pixel_colour(pixels, attr_data, x, y_bot)

            # Grid overlay: draw white lines on cell boundaries
            if grid:
                if x % 8 == 0 or y_top % 8 == 0:
                    fg = (128, 128, 128)
                if x % 8 == 0 or y_bot % 8 == 0:
                    bg = (128, 128, 128)

            # Clash overlay: red border on clashing cells
            if clash_cells:
                char_row = y_top // 8
                char_col = x // 8
                if (char_row, char_col) in clash_cells:
                    on_edge = (
                        x % 8 == 0 or x % 8 == 7
                        or y_top % 8 == 0 or y_bot % 8 == 7
                    )
                    if on_edge:
                        fg = (255, 0, 0)
                        bg = (255, 0, 0)

            # Only emit escape if colour changed
            if fg != prev_fg or bg != prev_bg:
                parts.append(ansi_fg_bg(fg, bg))
                prev_fg = fg
                prev_bg = bg

            parts.append(UPPER_HALF)

        parts.append(ANSI_RESET)

        if border:
            parts.append(ansi_bg(border_rgb) + "  " + ANSI_RESET)

        lines.append("".join(parts))

    # Optional bottom border
    if border:
        border_line = ansi_bg(border_rgb) + " " * (SCR_WIDTH_PX + 4) + ANSI_RESET
        lines.append(border_line)

    return "\n".join(lines)


# ── HTML / SVG output ─────────────────────────────────────────────────

def _try_png_html(
    pixels: list[list[int]],
    attr_data: bytes,
    *,
    attr_only: bool,
    grid: bool,
    clash_cells: set[tuple[int, int]] | None,
    border: int,
    scale: int,
) -> str | None:
    """Try to generate HTML with embedded PNG using PIL. Returns None if unavailable."""
    try:
        from PIL import Image  # type: ignore[import-untyped]
    except ImportError:
        return None

    import base64

    border_px = 16 if border else 0
    img_w = SCR_WIDTH_PX + 2 * border_px
    img_h = SCR_HEIGHT_PX + 2 * border_px
    img = Image.new("RGB", (img_w, img_h))
    put = img.putpixel

    border_rgb = ZX_PALETTE[0][border & 7]

    # Fill border
    if border_px:
        for y in range(img_h):
            for x in range(img_w):
                put((x, y), border_rgb)

    # Draw pixels
    for y in range(SCR_HEIGHT_PX):
        for x in range(SCR_WIDTH_PX):
            if attr_only:
                c = pixel_colour_attr_only(attr_data, x, y)
            else:
                c = pixel_colour(pixels, attr_data, x, y)

            if grid and (x % 8 == 0 or y % 8 == 0):
                c = (128, 128, 128)

            if clash_cells:
                char_row = y // 8
                char_col = x // 8
                if (char_row, char_col) in clash_cells:
                    if x % 8 == 0 or x % 8 == 7 or y % 8 == 0 or y % 8 == 7:
                        c = (255, 0, 0)

            put((border_px + x, border_px + y), c)

    # Scale up
    if scale > 1:
        img = img.resize((img_w * scale, img_h * scale), Image.NEAREST)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    return _html_wrapper(
        f'<img src="data:image/png;base64,{b64}" '
        f'width="{img_w * scale}" height="{img_h * scale}" '
        f'style="image-rendering: pixelated;" />'
    )


def _svg_html(
    pixels: list[list[int]],
    attr_data: bytes,
    *,
    attr_only: bool,
    grid: bool,
    clash_cells: set[tuple[int, int]] | None,
    border: int,
    scale: int,
) -> str:
    """Generate HTML with embedded SVG (no dependencies)."""
    border_px = 16 if border else 0
    svg_w = SCR_WIDTH_PX + 2 * border_px
    svg_h = SCR_HEIGHT_PX + 2 * border_px

    border_rgb = ZX_PALETTE[0][border & 7]

    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{svg_w * scale}" height="{svg_h * scale}" '
        f'viewBox="0 0 {svg_w} {svg_h}" '
        f'shape-rendering="crispEdges">'
    )

    # Border background
    if border_px:
        br, bg, bb = border_rgb
        parts.append(
            f'<rect x="0" y="0" width="{svg_w}" height="{svg_h}" '
            f'fill="rgb({br},{bg},{bb})" />'
        )

    # Build colour map: group adjacent same-colour pixels into runs
    # This reduces SVG size dramatically compared to one rect per pixel
    for y in range(SCR_HEIGHT_PX):
        x = 0
        while x < SCR_WIDTH_PX:
            if attr_only:
                c = pixel_colour_attr_only(attr_data, x, y)
            else:
                c = pixel_colour(pixels, attr_data, x, y)

            if grid and (x % 8 == 0 or y % 8 == 0):
                c = (128, 128, 128)

            if clash_cells:
                char_row = y // 8
                char_col = x // 8
                if (char_row, char_col) in clash_cells:
                    if x % 8 == 0 or x % 8 == 7 or y % 8 == 0 or y % 8 == 7:
                        c = (255, 0, 0)

            # Run-length: find consecutive pixels with the same colour
            run_start = x
            x += 1
            while x < SCR_WIDTH_PX:
                if attr_only:
                    nc = pixel_colour_attr_only(attr_data, x, y)
                else:
                    nc = pixel_colour(pixels, attr_data, x, y)

                if grid and (x % 8 == 0 or y % 8 == 0):
                    nc = (128, 128, 128)

                if clash_cells:
                    cr2 = y // 8
                    cc2 = x // 8
                    if (cr2, cc2) in clash_cells:
                        if x % 8 == 0 or x % 8 == 7 or y % 8 == 0 or y % 8 == 7:
                            nc = (255, 0, 0)

                if nc != c:
                    break
                x += 1

            run_len = x - run_start
            r, g, b = c
            parts.append(
                f'<rect x="{border_px + run_start}" y="{border_px + y}" '
                f'width="{run_len}" height="1" fill="rgb({r},{g},{b})" />'
            )

    parts.append("</svg>")

    return _html_wrapper("\n".join(parts))


def _html_wrapper(body_content: str) -> str:
    """Wrap content in a minimal HTML page."""
    return (
        "<!DOCTYPE html>\n"
        "<html>\n"
        "<head>\n"
        '  <meta charset="utf-8">\n'
        "  <title>ZX Spectrum Screen</title>\n"
        "  <style>\n"
        "    body { background: #222; display: flex; justify-content: center;\n"
        "           align-items: center; min-height: 100vh; margin: 0; }\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        f"  {body_content}\n"
        "</body>\n"
        "</html>\n"
    )


def render_html(
    pixels: list[list[int]],
    attr_data: bytes,
    *,
    attr_only: bool = False,
    grid: bool = False,
    clash_cells: set[tuple[int, int]] | None = None,
    border: int = 0,
    scale: int = 3,
) -> str:
    """Render screen as HTML. Uses PIL/PNG if available, SVG otherwise."""
    result = _try_png_html(
        pixels, attr_data,
        attr_only=attr_only, grid=grid, clash_cells=clash_cells,
        border=border, scale=scale,
    )
    if result is not None:
        return result

    return _svg_html(
        pixels, attr_data,
        attr_only=attr_only, grid=grid, clash_cells=clash_cells,
        border=border, scale=scale,
    )


# ── Analysis ──────────────────────────────────────────────────────────

def find_clash_cells(
    pixels: list[list[int]],
    attr_data: bytes,
) -> set[tuple[int, int]]:
    """Find character cells that have 3+ distinct foreground pixel patterns.

    In a normal ZX Spectrum cell, there are exactly 2 colours (ink + paper).
    A 'clash' cell has pixels set with ink colour but the attr allows only one
    ink. The practical definition: count unique non-zero pixel byte values
    per cell; if a cell has ink pixels that would need different colours, it
    is 'clashing'. However, .scr doesn't store intended colours per pixel --
    all ink pixels share one colour. So true clash detection is about checking
    if the original artist used more than the available 2 colours.

    Simplified approach: count unique pixel byte patterns per 8x8 cell.
    If a cell has more than 2 distinct row-byte values (excluding all-0 and
    all-1 which are just paper/ink fills), mark it as complex/potentially
    clashing. This is a heuristic.

    More practical: mark cells where ink == paper (invisible pixels) as a
    different kind of issue, or cells that look like they might have needed
    more colours.

    Actually, the most useful 'clash' in practice: mark cells where the
    attribute's ink == paper (content invisible), or where flash is set.

    Let's use a definition that's most useful for artists: cells with high
    pixel complexity (many distinct byte patterns) that would be hard to
    draw within the 2-colour-per-cell limit.
    """
    clash: set[tuple[int, int]] = set()
    for char_row in range(SCR_ROWS):
        for char_col in range(SCR_COLS):
            # Collect the 8 pixel bytes for this cell
            patterns: set[int] = set()
            for scan in range(8):
                y = char_row * 8 + scan
                offset = scr_pixel_offset(char_col, y)
                patterns.add(pixels[y][char_col * 8] << 7
                             | pixels[y][char_col * 8 + 1] << 6
                             | pixels[y][char_col * 8 + 2] << 5
                             | pixels[y][char_col * 8 + 3] << 4
                             | pixels[y][char_col * 8 + 4] << 3
                             | pixels[y][char_col * 8 + 5] << 2
                             | pixels[y][char_col * 8 + 6] << 1
                             | pixels[y][char_col * 8 + 7])
            # Remove trivial patterns (all ink or all paper)
            patterns.discard(0x00)
            patterns.discard(0xFF)
            # If 3+ distinct non-trivial patterns, mark as complex
            if len(patterns) >= 6:
                clash.add((char_row, char_col))
    return clash


def screen_info(
    pixels: list[list[int]],
    attr_data: bytes,
) -> str:
    """Generate statistics about the screen."""
    lines: list[str] = []
    lines.append("Screen Statistics")
    lines.append("=" * 40)

    # Count attribute properties
    flash_count = 0
    bright_count = 0
    ink_usage: dict[int, int] = {}
    paper_usage: dict[int, int] = {}
    unique_attrs: set[int] = set()

    for i in range(ATTR_SIZE):
        attr_byte = attr_data[i]
        unique_attrs.add(attr_byte)
        ink, paper, bright, flash = decode_attr(attr_byte)

        ink_usage[ink] = ink_usage.get(ink, 0) + 1
        paper_usage[paper] = paper_usage.get(paper, 0) + 1
        if flash:
            flash_count += 1
        if bright:
            bright_count += 1

    lines.append(f"Total cells:         {SCR_ROWS * SCR_COLS} ({SCR_ROWS}x{SCR_COLS})")
    lines.append(f"Unique attr values:  {len(unique_attrs)}")
    lines.append(f"Flash cells:         {flash_count}")
    lines.append(f"Bright cells:        {bright_count}")
    lines.append("")

    lines.append("Ink colour usage:")
    for c in range(8):
        count = ink_usage.get(c, 0)
        if count:
            bar = "#" * min(count // 10, 40)
            lines.append(f"  {c} {COLOUR_NAMES[c]:>8s}: {count:4d} {bar}")

    lines.append("")
    lines.append("Paper colour usage:")
    for c in range(8):
        count = paper_usage.get(c, 0)
        if count:
            bar = "#" * min(count // 10, 40)
            lines.append(f"  {c} {COLOUR_NAMES[c]:>8s}: {count:4d} {bar}")

    # Pixel density
    total_set = sum(sum(row) for row in pixels)
    total_pixels = SCR_WIDTH_PX * SCR_HEIGHT_PX
    lines.append("")
    lines.append(f"Pixel density:       {total_set}/{total_pixels} "
                 f"({100.0 * total_set / total_pixels:.1f}%)")

    # Per-third density
    for third in range(3):
        y_start = third * 64
        y_end = y_start + 64
        third_set = sum(sum(row) for row in pixels[y_start:y_end])
        third_total = 64 * SCR_WIDTH_PX
        lines.append(f"  Third {third}:           {third_set}/{third_total} "
                     f"({100.0 * third_set / third_total:.1f}%)")

    # Clash analysis
    clash = find_clash_cells(pixels, attr_data)
    lines.append("")
    lines.append(f"Complex cells:       {len(clash)} "
                 f"(cells with 6+ distinct pixel patterns)")

    return "\n".join(lines)


# ── File loading ──────────────────────────────────────────────────────

def load_scr(path: str) -> tuple[bytes, bytes]:
    """Load a .scr file. Returns (pixel_data, attr_data).

    Accepts:
      6912 bytes -- standard .scr (pixels + attributes)
      6144 bytes -- pixels only (attributes default to white ink on black paper)
    """
    filepath = Path(path)
    if not filepath.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    data = filepath.read_bytes()
    size = len(data)

    if size == SCR_SIZE:
        return data[:PIXEL_SIZE], data[PIXEL_SIZE:]
    elif size == PIXEL_SIZE:
        # Pixels only: default attributes = bright white on black (0x47)
        # ink=7 (white), paper=0 (black), bright=0, flash=0
        default_attr = bytes([0x07] * ATTR_SIZE)
        return data, default_attr
    else:
        print(
            f"Error: invalid file size {size} bytes. "
            f"Expected {SCR_SIZE} (full .scr) or {PIXEL_SIZE} (pixels only).",
            file=sys.stderr,
        )
        sys.exit(1)


# ── CLI ───────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scrview",
        description=(
            "ZX Spectrum Screen (.scr) Viewer.\n"
            "Renders 6912-byte ZX Spectrum screen dumps in the terminal\n"
            "using ANSI escape codes, or exports as HTML (SVG/PNG)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  %(prog)s screen.scr                       ANSI terminal output\n"
            "  %(prog)s screen.scr --html out.html        export as HTML file\n"
            "  %(prog)s screen.scr --info                 print screen statistics\n"
            "  %(prog)s screen.scr --grid --ansi          show with grid overlay\n"
            "  %(prog)s screen.scr --clash                highlight complex cells\n"
            "  %(prog)s screen.scr --attr-only            show attributes only\n"
            "  %(prog)s screen.scr --border 1             blue border\n"
        ),
    )

    parser.add_argument(
        "file",
        help="ZX Spectrum .scr file (6912 or 6144 bytes)",
    )

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--ansi", action="store_true", default=False,
        help="ANSI terminal output (default if --html not specified)",
    )
    mode_group.add_argument(
        "--html", metavar="FILE", default=None,
        help="generate HTML file (uses PNG if PIL available, SVG otherwise)",
    )

    parser.add_argument(
        "--grid", action="store_true", default=False,
        help="overlay 8x8 attribute cell grid",
    )
    parser.add_argument(
        "--clash", action="store_true", default=False,
        help="highlight cells with high pixel complexity (red border)",
    )
    parser.add_argument(
        "--attr-only", action="store_true", default=False,
        help="show only attribute colours (no pixel detail)",
    )
    parser.add_argument(
        "--info", action="store_true", default=False,
        help="print screen statistics (colours, flash, bright, density)",
    )
    parser.add_argument(
        "--border", type=int, default=0, choices=range(8),
        metavar="N",
        help="border colour 0-7 (default 0=black)",
    )
    parser.add_argument(
        "--scale", type=int, default=3,
        metavar="N",
        help="pixel scale for HTML output (default 3)",
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Load screen data
    pixel_data, attr_data = load_scr(args.file)

    # Decode pixel bitmap
    pixels = decode_pixels(pixel_data)

    # --info: print statistics and exit (unless combined with rendering)
    if args.info:
        print(screen_info(pixels, attr_data))
        if not args.html and not args.ansi:
            return

    # Clash detection
    clash_cells: set[tuple[int, int]] | None = None
    if args.clash:
        clash_cells = find_clash_cells(pixels, attr_data)

    # Render
    if args.html:
        html_content = render_html(
            pixels, attr_data,
            attr_only=args.attr_only,
            grid=args.grid,
            clash_cells=clash_cells,
            border=args.border,
            scale=args.scale,
        )
        out_path = Path(args.html)
        out_path.write_text(html_content, encoding="utf-8")
        print(f"Written: {out_path} ({len(html_content)} bytes)")
    else:
        # Default: ANSI terminal output
        ansi_output = render_ansi(
            pixels, attr_data,
            attr_only=args.attr_only,
            grid=args.grid,
            clash_cells=clash_cells,
            border=args.border,
        )
        print(ansi_output)


if __name__ == "__main__":
    main()
