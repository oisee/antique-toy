#!/usr/bin/env python3
"""
ch02_attr_byte.py — Bit layout of the ZX Spectrum attribute byte.

8 boxes showing bits 7-0:
  F(flash) | B(bright) | P2 P1 P0 (paper) | I2 I1 I0 (ink)
Colour-coded sections with example: $47 = BRIGHT blue ink on black paper.

Output: illustrations/output/ch02_attr_byte.png
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# --- ZX Spectrum palette ---
ZX_BLUE    = '#0000D7'
ZX_RED     = '#D70000'
ZX_GREEN   = '#00D700'
ZX_YELLOW  = '#D7D700'
ZX_CYAN    = '#00D7D7'
ZX_MAGENTA = '#D700D7'

# Colour scheme for the sections
COL_FLASH  = '#D78700'   # orange
COL_BRIGHT = ZX_YELLOW
COL_PAPER  = ZX_GREEN
COL_INK    = ZX_CYAN

# ZX Spectrum colour names (normal and bright variants)
ZX_COLOUR_NAMES = ['Black', 'Blue', 'Red', 'Magenta', 'Green', 'Cyan', 'Yellow', 'White']
ZX_COLOUR_RGB = [
    '#000000', '#0000D7', '#D70000', '#D700D7',
    '#00D700', '#00D7D7', '#D7D700', '#D7D7D7',
]
ZX_BRIGHT_RGB = [
    '#000000', '#0000FF', '#FF0000', '#FF00FF',
    '#00FF00', '#00FFFF', '#FFFF00', '#FFFFFF',
]

# --- Figure ---
fig, ax = plt.subplots(figsize=(7, 4.5))
fig.patch.set_facecolor('white')
ax.set_facecolor('white')

# Bit layout boxes
box_w = 0.8
box_h = 0.8
y_top = 3.5
x_start = 0.4

bit_labels = ['F', 'B', 'P2', 'P1', 'P0', 'I2', 'I1', 'I0']
bit_numbers = [7, 6, 5, 4, 3, 2, 1, 0]
section_colors = [COL_FLASH, COL_BRIGHT,
                  COL_PAPER, COL_PAPER, COL_PAPER,
                  COL_INK, COL_INK, COL_INK]
section_alphas = [0.30, 0.30, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25]

for i in range(8):
    x = x_start + i * box_w
    # Draw box
    rect = mpatches.FancyBboxPatch(
        (x, y_top), box_w, box_h,
        boxstyle='round,pad=0.03',
        facecolor=section_colors[i], alpha=section_alphas[i],
        edgecolor='#333333', linewidth=1.5
    )
    ax.add_patch(rect)

    # Bit label (F, B, P2, etc.)
    ax.text(x + box_w / 2, y_top + box_h / 2 + 0.05, bit_labels[i],
            va='center', ha='center', fontsize=13, fontfamily='monospace',
            fontweight='bold', color='#1a1a1a')

    # Bit number above
    ax.text(x + box_w / 2, y_top + box_h + 0.15, f'bit {bit_numbers[i]}',
            va='bottom', ha='center', fontsize=7, fontfamily='monospace',
            color='#666666')

# Section brackets below the boxes
bracket_y = y_top - 0.25

def draw_bracket(ax, x1, x2, y, label, color):
    """Draw a bracket with a label below a range of boxes."""
    mid = (x1 + x2) / 2
    ax.annotate('', xy=(x1, y), xytext=(x2, y),
                arrowprops=dict(arrowstyle='-', color=color, lw=2.0))
    # Vertical ticks at ends
    tick_h = 0.08
    ax.plot([x1, x1], [y - tick_h, y + tick_h], color=color, lw=2.0)
    ax.plot([x2, x2], [y - tick_h, y + tick_h], color=color, lw=2.0)
    ax.text(mid, y - 0.18, label, va='top', ha='center', fontsize=9,
            fontweight='bold', color=color)

# Flash bracket (bit 7)
draw_bracket(ax, x_start + 0.1, x_start + box_w - 0.1, bracket_y, 'Flash', COL_FLASH)
# Bright bracket (bit 6)
draw_bracket(ax, x_start + box_w + 0.1, x_start + 2 * box_w - 0.1, bracket_y, 'Bright', '#B8860B')
# Paper bracket (bits 5-3)
draw_bracket(ax, x_start + 2 * box_w + 0.1, x_start + 5 * box_w - 0.1, bracket_y, 'Paper (0-7)', '#008800')
# Ink bracket (bits 2-0)
draw_bracket(ax, x_start + 5 * box_w + 0.1, x_start + 8 * box_w - 0.1, bracket_y, 'Ink (0-7)', '#008888')

# --- Example: $47 = 01000111 = BRIGHT white ink on black paper ---
# $47 = 0x47 = 0100_0111: F=0, B=1, Paper=000(black), Ink=111(white)
# User asked for "$47 = BRIGHT blue ink on black paper" but $47 decodes to
# BRIGHT white on black.  We use $41 (=BRIGHT blue on black) for a more
# colourful example that matches the stated intent.

example_val = 0x41
example_bits = f'{example_val:08b}'
example_hex = f'${example_val:02X}'

# Decode
ex_flash  = (example_val >> 7) & 1
ex_bright = (example_val >> 6) & 1
ex_paper  = (example_val >> 3) & 7
ex_ink    = example_val & 7

paper_name = ZX_COLOUR_NAMES[ex_paper]
ink_name   = ZX_COLOUR_NAMES[ex_ink]
bright_str = 'BRIGHT ' if ex_bright else ''
ink_rgb    = ZX_BRIGHT_RGB[ex_ink] if ex_bright else ZX_COLOUR_RGB[ex_ink]
paper_rgb  = ZX_BRIGHT_RGB[ex_paper] if ex_bright else ZX_COLOUR_RGB[ex_paper]

# Draw example section
ex_y = 1.6

ax.text(x_start, ex_y + 0.55, 'Example:', fontsize=11, fontweight='bold',
        fontfamily='sans-serif', color='#1a1a1a')

# Show the binary and hex
ax.text(x_start, ex_y, f'{example_hex}  =  {example_bits}',
        fontsize=12, fontfamily='monospace', color='#333333')

ax.text(x_start, ex_y - 0.45,
        f'= {bright_str}{ink_name} ink on {paper_name} paper',
        fontsize=10, fontfamily='sans-serif', color='#333333')

# Colour swatch
swatch_x = x_start + 5.5
swatch_w = 0.9
swatch_h = 0.5

# Paper swatch
rect_paper = mpatches.FancyBboxPatch(
    (swatch_x, ex_y - 0.15), swatch_w, swatch_h,
    boxstyle='round,pad=0.02',
    facecolor=paper_rgb, edgecolor='#999999', linewidth=1.0
)
ax.add_patch(rect_paper)
ax.text(swatch_x + swatch_w / 2, ex_y + swatch_h + 0.0, 'Paper',
        va='top', ha='center', fontsize=7, color='#666666')

# Ink swatch
rect_ink = mpatches.FancyBboxPatch(
    (swatch_x + swatch_w + 0.15, ex_y - 0.15), swatch_w, swatch_h,
    boxstyle='round,pad=0.02',
    facecolor=ink_rgb, edgecolor='#999999', linewidth=1.0
)
ax.add_patch(rect_ink)
ax.text(swatch_x + swatch_w + 0.15 + swatch_w / 2, ex_y + swatch_h + 0.0, 'Ink',
        va='top', ha='center', fontsize=7, color='#666666')

# --- Title ---
ax.set_title('ZX Spectrum Attribute Byte Layout', fontsize=13, fontweight='bold',
             fontfamily='sans-serif', pad=12)

ax.set_xlim(-0.1, 8.2)
ax.set_ylim(0.5, 5.2)
ax.set_aspect('equal')
ax.axis('off')

plt.tight_layout()
plt.savefig('/Users/alice/dev/antique-toy/illustrations/output/ch02_attr_byte.png',
            dpi=300, bbox_inches='tight', facecolor='white')
plt.close()
print('Saved ch02_attr_byte.png')
