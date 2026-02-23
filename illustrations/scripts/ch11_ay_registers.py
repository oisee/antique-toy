#!/usr/bin/env python3
"""
ch11_ay_registers.py -- AY-3-8910 register map diagram.

16 rows (R0-R15), each showing register number, name, and bit layout.
Colour-coded by function group:
  Tone = blue, Noise = orange, Mixer = red, Volume = green, Envelope = purple

Special attention to R7 mixer with expanded bit layout and "0 = ON" warning.
Register rows R8-R15 are drawn below the R7 expanded section to avoid overlap.

Output: illustrations/output/ch11_ay_registers.png
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# --- ZX Spectrum palette accent colours ---
ZX_BLUE    = '#0000D7'
ZX_RED     = '#D70000'
ZX_GREEN   = '#00D700'
ZX_YELLOW  = '#D7D700'
ZX_CYAN    = '#00D7D7'
ZX_MAGENTA = '#D700D7'

# Function group colours (softer tints for fills, full colours for borders)
COL_TONE     = '#4477CC'   # blue
COL_NOISE    = '#DD8833'   # orange
COL_MIXER    = '#CC3333'   # red
COL_VOLUME   = '#33AA55'   # green
COL_ENVELOPE = '#9944CC'   # purple

FILL_TONE     = '#C8D8F0'
FILL_NOISE    = '#F5DFC0'
FILL_MIXER    = '#F0C0C0'
FILL_VOLUME   = '#C0E8D0'
FILL_ENVELOPE = '#DFC8F0'

# --- Register definitions ---
# (register number, name, bits description, group colour, fill colour)
registers_top = [
    (0,  'Channel A Tone Period Fine',   '7-0: Fine tune',           COL_TONE, FILL_TONE),
    (1,  'Channel A Tone Period Coarse', '3-0: Coarse tune',         COL_TONE, FILL_TONE),
    (2,  'Channel B Tone Period Fine',   '7-0: Fine tune',           COL_TONE, FILL_TONE),
    (3,  'Channel B Tone Period Coarse', '3-0: Coarse tune',         COL_TONE, FILL_TONE),
    (4,  'Channel C Tone Period Fine',   '7-0: Fine tune',           COL_TONE, FILL_TONE),
    (5,  'Channel C Tone Period Coarse', '3-0: Coarse tune',         COL_TONE, FILL_TONE),
    (6,  'Noise Period',                 '4-0: Period (0-31)',        COL_NOISE, FILL_NOISE),
    (7,  'Mixer Control',               'Expanded below',            COL_MIXER, FILL_MIXER),
]

registers_bottom = [
    (8,  'Channel A Volume',            '4: M (env), 3-0: Volume',  COL_VOLUME, FILL_VOLUME),
    (9,  'Channel B Volume',            '4: M (env), 3-0: Volume',  COL_VOLUME, FILL_VOLUME),
    (10, 'Channel C Volume',            '4: M (env), 3-0: Volume',  COL_VOLUME, FILL_VOLUME),
    (11, 'Envelope Period Fine',         '7-0: Fine',                COL_ENVELOPE, FILL_ENVELOPE),
    (12, 'Envelope Period Coarse',       '7-0: Coarse',              COL_ENVELOPE, FILL_ENVELOPE),
    (13, 'Envelope Shape',              '3-0: Shape (0-15)',         COL_ENVELOPE, FILL_ENVELOPE),
    (14, 'I/O Port A',                  '7-0: Data',                 '#888888', '#E0E0E0'),
    (15, 'I/O Port B',                  '7-0: Data',                 '#888888', '#E0E0E0'),
]

# --- Figure ---
fig, ax = plt.subplots(figsize=(7, 11.5))
fig.patch.set_facecolor('white')
ax.set_facecolor('white')

# Layout constants
row_h = 0.48
gap = 0.06
x_reg = 0.0     # register number column
x_name = 0.65   # name column
x_bits = 5.2    # bits description column
total_w = 6.8
y_start = 10.8  # top of first row


def draw_register_row(ax, i_offset, rnum, name, bits, col, fill, y):
    """Draw one register row at vertical position y."""
    rect = mpatches.FancyBboxPatch(
        (x_reg, y - row_h / 2), total_w, row_h,
        boxstyle='round,pad=0.04',
        facecolor=fill, edgecolor=col, linewidth=1.5, alpha=0.85
    )
    ax.add_patch(rect)

    ax.text(x_reg + 0.3, y, f'R{rnum}',
            va='center', ha='center', fontsize=9, fontfamily='monospace',
            fontweight='bold', color='#1a1a1a')

    ax.text(x_name, y, name,
            va='center', ha='left', fontsize=8, fontfamily='sans-serif',
            color='#1a1a1a')

    ax.text(x_bits, y, bits,
            va='center', ha='left', fontsize=7.5, fontfamily='monospace',
            color='#444444')


# Title
ax.text(total_w / 2, y_start + 0.7, 'AY-3-8910 Register Map',
        ha='center', va='center', fontsize=14, fontweight='bold',
        fontfamily='sans-serif', color='#1a1a1a')

# --- Draw R0-R7 ---
for i, (rnum, name, bits, col, fill) in enumerate(registers_top):
    y = y_start - i * (row_h + gap)
    draw_register_row(ax, i, rnum, name, bits, col, fill, y)

# --- R7 Mixer expanded bit layout (below R7 row) ---
r7_row_y = y_start - 7 * (row_h + gap)
mixer_section_top = r7_row_y - row_h / 2 - 0.25

box_w = 0.72
box_h = 0.55
r7_x_start = 0.55

# Label for R7 section
ax.text(0.0, mixer_section_top + 0.05, 'R7 Mixer Bit Layout:',
        fontsize=9.5, fontweight='bold', fontfamily='sans-serif',
        color=COL_MIXER)

mixer_boxes_y = mixer_section_top - 0.55

r7_bits = [
    ('7', 'IOB',    '#AAAAAA'),
    ('6', 'IOA',    '#AAAAAA'),
    ('5', 'NoiseC', COL_NOISE),
    ('4', 'NoiseB', COL_NOISE),
    ('3', 'NoiseA', COL_NOISE),
    ('2', 'ToneC',  COL_TONE),
    ('1', 'ToneB',  COL_TONE),
    ('0', 'ToneA',  COL_TONE),
]

for j, (bnum, bname, bcol) in enumerate(r7_bits):
    x = r7_x_start + j * (box_w + 0.05)
    fill_alpha = 0.20 if bcol == '#AAAAAA' else 0.25
    rect = mpatches.FancyBboxPatch(
        (x, mixer_boxes_y), box_w, box_h,
        boxstyle='round,pad=0.03',
        facecolor=bcol, alpha=fill_alpha,
        edgecolor=bcol, linewidth=1.5
    )
    ax.add_patch(rect)

    ax.text(x + box_w / 2, mixer_boxes_y + box_h + 0.08, f'bit {bnum}',
            va='bottom', ha='center', fontsize=6, fontfamily='monospace',
            color='#666666')

    ax.text(x + box_w / 2, mixer_boxes_y + box_h / 2,
            bname, va='center', ha='center', fontsize=7,
            fontfamily='monospace', fontweight='bold', color='#1a1a1a')

# "0 = ON" warning box
warn_x = r7_x_start + 1.0
warn_y = mixer_boxes_y - 0.55
warn_rect = mpatches.FancyBboxPatch(
    (warn_x, warn_y), 4.5, 0.40,
    boxstyle='round,pad=0.06',
    facecolor='#FFF3CD', edgecolor='#CC8800', linewidth=1.5
)
ax.add_patch(warn_rect)
ax.text(warn_x + 2.25, warn_y + 0.20,
        '0 = ON  (active low!)   1 = OFF / disabled',
        va='center', ha='center', fontsize=8.5, fontfamily='monospace',
        fontweight='bold', color='#8B6914')

# --- Draw R8-R15 below the mixer section ---
bottom_start_y = warn_y - 0.45

for i, (rnum, name, bits, col, fill) in enumerate(registers_bottom):
    y = bottom_start_y - i * (row_h + gap)
    draw_register_row(ax, i, rnum, name, bits, col, fill, y)

# --- Legend ---
legend_y = bottom_start_y - len(registers_bottom) * (row_h + gap) - 0.2

legend_patches = [
    mpatches.Patch(facecolor=FILL_TONE, edgecolor=COL_TONE, linewidth=1.5, label='Tone (R0-R5)'),
    mpatches.Patch(facecolor=FILL_NOISE, edgecolor=COL_NOISE, linewidth=1.5, label='Noise (R6)'),
    mpatches.Patch(facecolor=FILL_MIXER, edgecolor=COL_MIXER, linewidth=1.5, label='Mixer (R7)'),
    mpatches.Patch(facecolor=FILL_VOLUME, edgecolor=COL_VOLUME, linewidth=1.5, label='Volume (R8-R10)'),
    mpatches.Patch(facecolor=FILL_ENVELOPE, edgecolor=COL_ENVELOPE, linewidth=1.5, label='Envelope (R11-R13)'),
    mpatches.Patch(facecolor='#E0E0E0', edgecolor='#888888', linewidth=1.5, label='I/O Ports (R14-R15)'),
]
ax.legend(handles=legend_patches, loc='lower center', fontsize=7,
          framealpha=0.9, edgecolor='#cccccc', ncol=3,
          bbox_to_anchor=(0.5, -0.01))

ax.set_xlim(-0.5, 7.2)
ax.set_ylim(legend_y - 0.6, y_start + 1.2)
ax.axis('off')

plt.tight_layout()
plt.savefig('/Users/alice/dev/antique-toy/illustrations/output/ch11_ay_registers.png',
            dpi=300, bbox_inches='tight', facecolor='white')
plt.close()
print('Saved ch11_ay_registers.png')
