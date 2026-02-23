#!/usr/bin/env python3
"""
Generate a book-quality diagram of the ZX Spectrum screen memory layout,
showing the interleaved row addressing scheme.

Output: SVG and PNG (300 DPI) in illustrations/output/
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.path as mpath
import numpy as np
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Accent palette — three muted colours for the three thirds
THIRD_COLORS = [
    "#3D6E9E",  # Steel blue  — top third
    "#C06030",  # Burnt orange — middle third
    "#3D8B57",  # Sage green   — bottom third
]
THIRD_COLORS_LIGHT = [
    "#B8D0EA",  # Light blue
    "#F0C9A8",  # Light orange
    "#B5D8BF",  # Light green
]

TEXT_COLOR = "#222222"
MONO_FONT = "monospace"
LABEL_FONT = "sans-serif"


def build_memory_order():
    """Return a list of 192 entries: (screen_y, third, char_row, pixel_line).

    Memory order iterates: for each third -> for each SSS -> for each LLL.
    The screen_y for a given (TT, SSS, LLL) is:
        screen_y = TT*64 + LLL*8 + SSS
    """
    entries = []
    for tt in range(3):
        for sss in range(8):
            for lll in range(8):
                screen_y = tt * 64 + lll * 8 + sss
                entries.append((screen_y, tt, lll, sss))
    return entries


def draw_rows(ax, x_left, width, order, y_offset, row_h):
    """Draw 192 thin rectangles.  *order* maps position index -> entry."""
    for idx, (screen_y, tt, lll, sss) in enumerate(order):
        y = y_offset + idx * row_h
        base = np.array(plt.matplotlib.colors.to_rgb(THIRD_COLORS_LIGHT[tt]))
        dark = np.array(plt.matplotlib.colors.to_rgb(THIRD_COLORS[tt]))
        mix = base * (1 - lll * 0.09) + dark * (lll * 0.09)
        if sss % 2 == 1:
            mix = mix * 0.95
        color = np.clip(mix, 0, 1)

        rect = mpatches.Rectangle(
            (x_left, y), width, row_h * 0.90,
            linewidth=0, facecolor=color,
        )
        ax.add_patch(rect)


def connect_line(ax, mem_idx, screen_y, tt, row_h, y_offset,
                 screen_right, mem_left):
    """Draw a thin bezier from screen row to memory row."""
    y_mem = y_offset + mem_idx * row_h + row_h * 0.45
    y_scr = y_offset + screen_y * row_h + row_h * 0.45
    x_scr = screen_right
    x_mem = mem_left

    mid_x = (x_scr + x_mem) / 2
    verts = [
        (x_scr, y_scr),
        (mid_x, y_scr),
        (mid_x, y_mem),
        (x_mem, y_mem),
    ]
    codes = [
        mpath.Path.MOVETO,
        mpath.Path.CURVE4,
        mpath.Path.CURVE4,
        mpath.Path.CURVE4,
    ]
    path = mpath.Path(verts, codes)
    patch = FancyArrowPatch(
        path=path,
        arrowstyle="-",
        color=THIRD_COLORS[tt],
        linewidth=0.5,
        alpha=0.45,
    )
    ax.add_patch(patch)


# ---------------------------------------------------------------------------
# Figure layout
# ---------------------------------------------------------------------------
fig = plt.figure(figsize=(7.5, 10.5), facecolor="white")

gs = fig.add_gridspec(
    nrows=2, ncols=1,
    height_ratios=[6.5, 3.0],
    hspace=0.30,
    left=0.04, right=0.96, top=0.95, bottom=0.03,
)

entries = build_memory_order()

# ===== TOP PANEL: Interleave visualisation ================================
ax_top = fig.add_subplot(gs[0])
ax_top.set_xlim(-2.5, 35)
ax_top.set_ylim(-2.5, 196)
ax_top.invert_yaxis()
ax_top.set_aspect("auto")
ax_top.axis("off")

# Title
ax_top.text(
    16, -2.0,
    "ZX Spectrum Screen Memory Layout",
    ha="center", va="bottom",
    fontsize=15, fontweight="bold", fontfamily=LABEL_FONT,
    color=TEXT_COLOR,
)

SCREEN_LEFT = 0
SCREEN_WIDTH = 11
MEM_LEFT = 20
MEM_WIDTH = 11
ROW_TOP = 4
ROW_H = 1.0

# Column headers
ax_top.text(
    SCREEN_LEFT + SCREEN_WIDTH / 2, ROW_TOP - 0.5,
    "Screen (pixel order)",
    ha="center", va="bottom",
    fontsize=9.5, fontweight="bold", fontfamily=LABEL_FONT, color=TEXT_COLOR,
)
ax_top.text(
    MEM_LEFT + MEM_WIDTH / 2, ROW_TOP - 0.5,
    "Memory (address order)",
    ha="center", va="bottom",
    fontsize=9.5, fontweight="bold", fontfamily=LABEL_FONT, color=TEXT_COLOR,
)

# Draw screen-order rows
screen_order = sorted(entries, key=lambda e: e[0])
draw_rows(ax_top, SCREEN_LEFT, SCREEN_WIDTH, screen_order, ROW_TOP, ROW_H)

# Draw memory-order rows
draw_rows(ax_top, MEM_LEFT, MEM_WIDTH, entries, ROW_TOP, ROW_H)

# --- Third boundary labels and address ranges (right side of memory) ---
for tt in range(3):
    mem_y_top = ROW_TOP + tt * 64 * ROW_H
    mem_y_bot = ROW_TOP + (tt + 1) * 64 * ROW_H

    bx = MEM_LEFT + MEM_WIDTH + 0.3
    ax_top.plot(
        [bx, bx + 0.4, bx + 0.4, bx],
        [mem_y_top + 1, mem_y_top + 1, mem_y_bot - 1, mem_y_bot - 1],
        color=THIRD_COLORS[tt], linewidth=1.8, solid_capstyle="round",
    )

    addr_start = 0x4000 + tt * 0x0800
    addr_end = addr_start + 0x07FF
    third_names = ["Top third", "Middle third", "Bottom third"]
    ax_top.text(
        bx + 0.7, (mem_y_top + mem_y_bot) / 2,
        f"{third_names[tt]}\n${addr_start:04X}-${addr_end:04X}",
        ha="left", va="center",
        fontsize=7.5, fontfamily=MONO_FONT,
        color=THIRD_COLORS[tt], fontweight="bold",
    )

    # Brackets on the screen side
    sx = SCREEN_LEFT - 0.3
    scr_y_top = ROW_TOP + tt * 64 * ROW_H
    scr_y_bot = ROW_TOP + (tt + 1) * 64 * ROW_H
    ax_top.plot(
        [sx, sx - 0.4, sx - 0.4, sx],
        [scr_y_top + 1, scr_y_top + 1, scr_y_bot - 1, scr_y_bot - 1],
        color=THIRD_COLORS[tt], linewidth=1.8, solid_capstyle="round",
    )

# --- Connecting lines: first 8 memory rows (line 0 of all 8 char rows) ---
for mem_idx in range(8):
    screen_y, tt, lll, sss = entries[mem_idx]
    connect_line(
        ax_top, mem_idx, screen_y, tt, ROW_H, ROW_TOP,
        SCREEN_LEFT + SCREEN_WIDTH, MEM_LEFT,
    )

# --- Row labels in the gap: show memory interleave pattern ---
gap_cx = (SCREEN_LEFT + SCREEN_WIDTH + MEM_LEFT) / 2
annot_data = [
    (0, "Row 0, line 0"),
    (1, "Row 1, line 0"),
    (2, "Row 2, line 0"),
    (3, "Row 3, line 0"),
    (4, "Row 4, line 0"),
    (5, "Row 5, line 0"),
    (6, "Row 6, line 0"),
    (7, "Row 7, line 0"),
]
for mem_idx, label in annot_data:
    y = ROW_TOP + mem_idx * ROW_H + ROW_H * 0.45
    ax_top.text(
        gap_cx, y,
        label,
        ha="center", va="center",
        fontsize=6.5, fontfamily=MONO_FONT, color="#333333",
        bbox=dict(boxstyle="round,pad=0.15", facecolor="white",
                  edgecolor="none", alpha=0.85),
    )

# Separator line + "then" label
sep_y = ROW_TOP + 8 * ROW_H
ax_top.plot(
    [gap_cx - 3, gap_cx + 3],
    [sep_y, sep_y],
    color="#AAAAAA", linewidth=0.6, linestyle="--",
)
ax_top.text(
    gap_cx, sep_y + ROW_H * 0.5,
    "Row 0, line 1",
    ha="center", va="center",
    fontsize=6.5, fontfamily=MONO_FONT, color="#333333",
    bbox=dict(boxstyle="round,pad=0.15", facecolor="white",
              edgecolor="none", alpha=0.85),
)
ax_top.text(
    gap_cx, sep_y + ROW_H * 1.5,
    "Row 1, line 1",
    ha="center", va="center",
    fontsize=6.5, fontfamily=MONO_FONT, color="#333333",
    bbox=dict(boxstyle="round,pad=0.15", facecolor="white",
              edgecolor="none", alpha=0.85),
)
ax_top.text(
    gap_cx, sep_y + ROW_H * 2.5,
    "...",
    ha="center", va="center",
    fontsize=7, fontfamily=MONO_FONT, color="#888888",
)


# ===== BOTTOM PANEL: Address bit layout ==================================
ax_bot = fig.add_subplot(gs[1])
ax_bot.set_xlim(-1, 18.5)
ax_bot.set_ylim(-0.5, 9.0)
ax_bot.invert_yaxis()
ax_bot.set_aspect("equal")
ax_bot.axis("off")

ax_bot.text(
    8.75, -0.1,
    "Address Bit Layout:  010TTSSS LLLCCCCC",
    ha="center", va="bottom",
    fontsize=11.5, fontweight="bold", fontfamily=MONO_FONT,
    color=TEXT_COLOR,
)

# Draw the 16-bit address as a row of boxes
bit_labels_hi = ["0", "1", "0", "T", "T", "S", "S", "S"]
bit_labels_lo = ["L", "L", "L", "C", "C", "C", "C", "C"]
bit_numbers_hi = ["15", "14", "13", "12", "11", "10", "9", "8"]
bit_numbers_lo = ["7", "6", "5", "4", "3", "2", "1", "0"]

all_labels = bit_labels_hi + bit_labels_lo
all_numbers = bit_numbers_hi + bit_numbers_lo


def bit_color(label):
    if label in ("0", "1"):
        return "#E0E0E0", TEXT_COLOR
    if label == "T":
        return "#FFD0D0", "#A03030"
    if label == "S":
        return "#D0E8FF", "#3050A0"
    if label == "L":
        return "#D0FFD0", "#208040"
    if label == "C":
        return "#FFF0C0", "#907020"
    return "white", "black"


BOX_W = 1.0
BOX_H = 1.0
START_X = 0.5
ROW_Y = 1.5

for i, (label, bitnum) in enumerate(zip(all_labels, all_numbers)):
    x = START_X + i * BOX_W
    if i >= 8:
        x += 0.5

    bg, fg = bit_color(label)
    rect = FancyBboxPatch(
        (x, ROW_Y), BOX_W, BOX_H,
        boxstyle="round,pad=0.05",
        facecolor=bg, edgecolor="#999999", linewidth=0.8,
    )
    ax_bot.add_patch(rect)

    ax_bot.text(
        x + BOX_W / 2, ROW_Y + BOX_H / 2,
        label,
        ha="center", va="center",
        fontsize=11, fontweight="bold", fontfamily=MONO_FONT,
        color=fg,
    )

    ax_bot.text(
        x + BOX_W / 2, ROW_Y - 0.15,
        bitnum,
        ha="center", va="bottom",
        fontsize=6, fontfamily=MONO_FONT, color="#888888",
    )

# Byte labels
ax_bot.text(
    START_X + 4 * BOX_W, ROW_Y + BOX_H + 0.3,
    "High byte",
    ha="center", va="top",
    fontsize=8, fontfamily=LABEL_FONT, color="#666666",
)
ax_bot.text(
    START_X + 8 * BOX_W + 0.5 + 4 * BOX_W, ROW_Y + BOX_H + 0.3,
    "Low byte",
    ha="center", va="top",
    fontsize=8, fontfamily=LABEL_FONT, color="#666666",
)

# --- Legend for bit fields (2 rows x 3 columns, better spacing) ---
legend_y = ROW_Y + BOX_H + 1.4
legend_items = [
    ("010",   "Fixed prefix ($40)",           "#E0E0E0", TEXT_COLOR),
    ("TT",    "Third (0-2)",                  "#FFD0D0", "#A03030"),
    ("SSS",   "Scanline in char cell (0-7)",  "#D0E8FF", "#3050A0"),
    ("LLL",   "Char row in third (0-7)",      "#D0FFD0", "#208040"),
    ("CCCCC", "Column byte (0-31)",           "#FFF0C0", "#907020"),
]

COL_SPACING = 6.0
for i, (code, desc, bg, fg) in enumerate(legend_items):
    col = i % 3
    row = i // 3
    lx = 0.5 + col * COL_SPACING
    ly = legend_y + row * 1.2

    rect = FancyBboxPatch(
        (lx, ly), 0.7, 0.7,
        boxstyle="round,pad=0.05",
        facecolor=bg, edgecolor="#999999", linewidth=0.6,
    )
    ax_bot.add_patch(rect)
    ax_bot.text(
        lx + 0.35, ly + 0.35,
        code[0],
        ha="center", va="center",
        fontsize=8, fontweight="bold", fontfamily=MONO_FONT, color=fg,
    )
    ax_bot.text(
        lx + 0.95, ly + 0.35,
        f"{code} = {desc}",
        ha="left", va="center",
        fontsize=7, fontfamily=LABEL_FONT, color=TEXT_COLOR,
    )

# --- Example address calculation ---
ex_y = legend_y + 2.8
ax_bot.text(
    0.5, ex_y,
    "Example:  Third 1, scanline 3, char row 5, column 10",
    ha="left", va="top",
    fontsize=8, fontweight="bold", fontfamily=LABEL_FONT, color=TEXT_COLOR,
)
ax_bot.text(
    0.5, ex_y + 0.85,
    "  High: 010 | 01 | 011 = $4B    (TT=01, SSS=011)",
    ha="left", va="top",
    fontsize=7.5, fontfamily=MONO_FONT, color="#555555",
)
ax_bot.text(
    0.5, ex_y + 1.55,
    "  Low:  101 | 01010    = $AA    (LLL=101, CCCCC=01010)",
    ha="left", va="top",
    fontsize=7.5, fontfamily=MONO_FONT, color="#555555",
)
ax_bot.text(
    0.5, ex_y + 2.25,
    "  Address: $4BAA \u2192 pixel row 109 (third 1, row 5, line 3), column 10",
    ha="left", va="top",
    fontsize=7.5, fontfamily=MONO_FONT, color="#555555",
)


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------
svg_path = OUTPUT_DIR / "ch02_screen_layout.svg"
png_path = OUTPUT_DIR / "ch02_screen_layout.png"

fig.savefig(str(svg_path), format="svg", bbox_inches="tight")
fig.savefig(str(png_path), format="png", dpi=300, bbox_inches="tight")
plt.close(fig)

print(f"Saved: {svg_path}")
print(f"Saved: {png_path}")
