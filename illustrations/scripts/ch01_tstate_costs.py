#!/usr/bin/env python3
"""
ch01_tstate_costs.py — Horizontal bar chart of common Z80 instruction T-state costs.

Colour-coded by category:
  Load = blue, Stack = green, Block = orange, I/O = red, Flow = purple

Output: illustrations/output/ch01_tstate_costs.png
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# --- ZX Spectrum palette accent colours ---
ZX_BLUE    = '#0000D7'
ZX_RED     = '#D70000'
ZX_GREEN   = '#00D700'
ZX_CYAN    = '#00D7D7'
ZX_MAGENTA = '#D700D7'

# Category colours
CAT_LOAD  = ZX_BLUE
CAT_STACK = '#00AA00'  # slightly darker green for readability
CAT_BLOCK = '#D78700'  # orange
CAT_IO    = ZX_RED
CAT_FLOW  = ZX_MAGENTA

# --- Data (instruction, T-states, category colour) ---
instructions = [
    ('NOP',          4,  CAT_LOAD),
    ('LD r, r\'',    4,  CAT_LOAD),
    ('LD A, (HL)',   7,  CAT_LOAD),
    ('PUSH rr',     11,  CAT_STACK),
    ('OUT (C), r',  12,  CAT_IO),
    ('DJNZ e',      13,  CAT_FLOW),
    ('LDI',         16,  CAT_BLOCK),
    ('CALL nn',     17,  CAT_FLOW),
    ('LDIR',        21,  CAT_BLOCK),
]

labels  = [i[0] for i in instructions]
tstates = [i[1] for i in instructions]
colors  = [i[2] for i in instructions]

# --- Figure ---
fig, ax = plt.subplots(figsize=(7, 4.0))
fig.patch.set_facecolor('white')
ax.set_facecolor('white')

y_pos = np.arange(len(labels))
bar_height = 0.6

bars = ax.barh(y_pos, tstates, height=bar_height, color=colors,
               edgecolor='white', linewidth=0.8)

# Add T-state labels at the end of each bar
for i, (val, bar) in enumerate(zip(tstates, bars)):
    ax.text(val + 0.4, i, f'{val}T',
            va='center', ha='left', fontsize=9.5, fontfamily='monospace',
            fontweight='bold', color='#333333')

ax.set_yticks(y_pos)
ax.set_yticklabels(labels, fontsize=10, fontfamily='monospace')
ax.invert_yaxis()  # cheapest at top
ax.set_xlabel('T-states', fontsize=10, fontfamily='sans-serif')
ax.set_title('Z80 Instruction Costs', fontsize=13, fontweight='bold',
             fontfamily='sans-serif', pad=12)
ax.set_xlim(0, max(tstates) + 5)

# Category legend — place in upper right where bars are short
legend_patches = [
    mpatches.Patch(color=CAT_LOAD,  label='Load'),
    mpatches.Patch(color=CAT_STACK, label='Stack'),
    mpatches.Patch(color=CAT_BLOCK, label='Block transfer'),
    mpatches.Patch(color=CAT_IO,    label='I/O'),
    mpatches.Patch(color=CAT_FLOW,  label='Flow control'),
]
ax.legend(handles=legend_patches, loc='upper right', fontsize=8,
          framealpha=0.9, edgecolor='#cccccc')

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_linewidth(0.5)
ax.spines['bottom'].set_linewidth(0.5)
ax.tick_params(axis='x', labelsize=8)

plt.tight_layout()
plt.savefig('/Users/alice/dev/antique-toy/illustrations/output/ch01_tstate_costs.png',
            dpi=300, bbox_inches='tight', facecolor='white')
plt.close()
print('Saved ch01_tstate_costs.png')
