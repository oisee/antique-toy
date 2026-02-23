#!/usr/bin/env python3
"""
ch15_memory_map.py -- ZX Spectrum 128K memory map.

Shows:
- 4 x 16KB address slots (0000-3FFF ROM, 4000-7FFF bank 5, 8000-BFFF bank 2,
  C000-FFFF switchable)
- All 8 RAM banks (0-7) with typical usage labels
- Port $7FFD bit layout for bank switching
- Colour-coded: ROM=grey, screen=cyan, code=blue, data=green, switchable=yellow

Output: illustrations/output/ch15_memory_map.png
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# --- Colours ---
COL_ROM        = '#B0B0B0'
COL_SCREEN     = '#80D8D8'   # cyan-ish
COL_CODE       = '#7090D0'   # blue
COL_DATA       = '#80C890'   # green
COL_SWITCHABLE = '#E8D870'   # yellow
COL_CONTENDED  = '#E8A0A0'   # light red for contended pages

# --- Figure ---
fig, ax = plt.subplots(figsize=(7, 8.5))
fig.patch.set_facecolor('white')
ax.set_facecolor('white')

# ========== LEFT SIDE: 64KB Address Space (4 slots) ==========

slot_x = 0.3
slot_w = 2.2
slot_h = 1.3
slot_gap = 0.08
y_top = 7.8

# Title
ax.text(slot_x + slot_w / 2, y_top + 0.5,
        'ZX Spectrum 128K Memory Map',
        ha='center', va='center', fontsize=14, fontweight='bold',
        fontfamily='sans-serif', color='#1a1a1a')

# Subtitle
ax.text(slot_x + slot_w / 2, y_top + 0.15,
        '64KB Address Space (4 x 16KB slots)',
        ha='center', va='center', fontsize=9, fontfamily='sans-serif',
        color='#666666')

slots = [
    ('$0000-$3FFF', 'ROM 0 / ROM 1',     COL_ROM,        'ROM (16KB)\nBASIC 128 or 48'),
    ('$4000-$7FFF', 'Bank 5 (fixed)',     COL_SCREEN,     'Screen memory\n+ system vars'),
    ('$8000-$BFFF', 'Bank 2 (fixed)',     COL_CODE,       'Main code\n(always visible)'),
    ('$C000-$FFFF', 'Bank 0-7 (switch)',  COL_SWITCHABLE, 'Switchable page\nvia port $7FFD'),
]

for i, (addr, name, col, desc) in enumerate(slots):
    y = y_top - i * (slot_h + slot_gap)

    rect = mpatches.FancyBboxPatch(
        (slot_x, y - slot_h), slot_w, slot_h,
        boxstyle='round,pad=0.06',
        facecolor=col, edgecolor='#333333', linewidth=1.5, alpha=0.7
    )
    ax.add_patch(rect)

    # Address label on the left edge
    ax.text(slot_x - 0.1, y - slot_h / 2, addr,
            va='center', ha='right', fontsize=7.5, fontfamily='monospace',
            fontweight='bold', color='#333333')

    # Name + description inside
    ax.text(slot_x + slot_w / 2, y - slot_h * 0.3, name,
            va='center', ha='center', fontsize=9, fontfamily='sans-serif',
            fontweight='bold', color='#1a1a1a')
    ax.text(slot_x + slot_w / 2, y - slot_h * 0.7, desc,
            va='center', ha='center', fontsize=7, fontfamily='sans-serif',
            color='#444444')

# Arrow from switchable slot to the bank array on the right
arrow_y = y_top - 3 * (slot_h + slot_gap) - slot_h / 2
ax.annotate('', xy=(3.8, arrow_y + 0.1), xytext=(slot_x + slot_w + 0.1, arrow_y + 0.1),
            arrowprops=dict(arrowstyle='->', color='#CC8800', lw=2.0,
                            connectionstyle='arc3,rad=0.0'))
ax.text(3.15, arrow_y + 0.3, 'maps to', ha='center', fontsize=7,
        color='#CC8800', fontstyle='italic')


# ========== RIGHT SIDE: 8 RAM Banks ==========

bank_x = 3.9
bank_w = 2.6
bank_h = 0.65
bank_gap = 0.05
bank_y_top = y_top - 0.05

# Title for bank section
ax.text(bank_x + bank_w / 2, bank_y_top + 0.3,
        '8 RAM Banks (16KB each)',
        ha='center', va='center', fontsize=10, fontweight='bold',
        fontfamily='sans-serif', color='#333333')

banks = [
    (0, 'Level data / buffers',    COL_DATA,       False),
    (1, 'Sprite set 1',            COL_DATA,       True),
    (2, 'Main code (fixed $8000)', COL_CODE,       False),
    (3, 'Music / sound data',      COL_DATA,       True),
    (4, 'Extra data',              COL_DATA,       False),
    (5, 'Screen (fixed $4000)',    COL_SCREEN,     True),
    (6, 'Sprite set 2',            COL_DATA,       False),
    (7, 'Shadow screen / buffer',  COL_SWITCHABLE, True),
]

for i, (bnum, usage, col, contended) in enumerate(banks):
    y = bank_y_top - i * (bank_h + bank_gap)

    rect = mpatches.FancyBboxPatch(
        (bank_x, y - bank_h), bank_w, bank_h,
        boxstyle='round,pad=0.04',
        facecolor=col, edgecolor='#333333', linewidth=1.2, alpha=0.65
    )
    ax.add_patch(rect)

    # Bank number
    ax.text(bank_x + 0.25, y - bank_h / 2, f'{bnum}',
            va='center', ha='center', fontsize=10, fontfamily='monospace',
            fontweight='bold', color='#1a1a1a')

    # Usage label
    ax.text(bank_x + 0.55, y - bank_h / 2, usage,
            va='center', ha='left', fontsize=7.5, fontfamily='sans-serif',
            color='#333333')

    # Contended marker
    if contended:
        ax.text(bank_x + bank_w - 0.1, y - bank_h / 2, 'C',
                va='center', ha='right', fontsize=7, fontfamily='monospace',
                fontweight='bold', color='#CC3333')

# Contended note
ax.text(bank_x + bank_w - 0.1, bank_y_top - 8 * (bank_h + bank_gap) - 0.15,
        'C = contended (slower on 128K/+2)',
        ha='right', va='top', fontsize=6.5, fontfamily='sans-serif',
        color='#CC3333', fontstyle='italic')


# ========== BOTTOM: Port $7FFD Bit Layout ==========

port_y = 1.2
port_x_start = 0.5
box_w = 0.72
box_h = 0.55

ax.text(3.5, port_y + box_h + 0.55,
        'Port $7FFD — Bank Select Register',
        ha='center', va='center', fontsize=11, fontweight='bold',
        fontfamily='sans-serif', color='#1a1a1a')

# Bit definitions for port $7FFD
port_bits = [
    ('7', '-',          '#DDDDDD', '#999999'),
    ('6', '-',          '#DDDDDD', '#999999'),
    ('5', 'DIS',        '#E8A0A0', '#CC3333'),
    ('4', 'ROM',        COL_ROM,   '#555555'),
    ('3', 'SCR',        COL_SCREEN,'#007777'),
    ('2', 'RAM2',       COL_SWITCHABLE, '#888800'),
    ('1', 'RAM1',       COL_SWITCHABLE, '#888800'),
    ('0', 'RAM0',       COL_SWITCHABLE, '#888800'),
]

for j, (bnum, bname, bcol, tcol) in enumerate(port_bits):
    x = port_x_start + j * (box_w + 0.05)

    rect = mpatches.FancyBboxPatch(
        (x, port_y), box_w, box_h,
        boxstyle='round,pad=0.03',
        facecolor=bcol, alpha=0.35,
        edgecolor=tcol, linewidth=1.5
    )
    ax.add_patch(rect)

    # Bit number above
    ax.text(x + box_w / 2, port_y + box_h + 0.08, f'bit {bnum}',
            va='bottom', ha='center', fontsize=6, fontfamily='monospace',
            color='#666666')

    # Name inside
    ax.text(x + box_w / 2, port_y + box_h / 2, bname,
            va='center', ha='center', fontsize=8, fontfamily='monospace',
            fontweight='bold', color='#1a1a1a')

# Annotations below port bits
ann_y = port_y - 0.22
annotations = [
    (port_x_start + 0.38, 'Unused'),
    (port_x_start + 2 * (box_w + 0.05) + box_w / 2, 'Disable\npaging'),
    (port_x_start + 3 * (box_w + 0.05) + box_w / 2, 'ROM\nselect'),
    (port_x_start + 4 * (box_w + 0.05) + box_w / 2, 'Screen\n0=norm\n1=shadow'),
    (port_x_start + 6 * (box_w + 0.05), 'RAM page (0-7)\nat $C000'),
]

for x, label in annotations:
    ax.text(x, ann_y, label, ha='center', va='top',
            fontsize=6, fontfamily='sans-serif', color='#555555')

ax.set_xlim(-0.8, 7.0)
ax.set_ylim(-0.3, y_top + 0.9)
ax.axis('off')

plt.tight_layout()
plt.savefig('/Users/alice/dev/antique-toy/illustrations/output/ch15_memory_map.png',
            dpi=300, bbox_inches='tight', facecolor='white')
plt.close()
print('Saved ch15_memory_map.png')
