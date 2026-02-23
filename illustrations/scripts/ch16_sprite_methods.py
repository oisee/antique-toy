#!/usr/bin/env python3
"""
ch16_sprite_methods.py -- Sprite rendering method comparison chart.

Horizontal bar chart comparing 6 sprite rendering methods by T-state cost.
Sorted fastest to slowest with colour gradient green -> red.
Frame budget line for 8 sprites shown.

Uses the canonical values from the illustration plan (ch16.1):
  XOR: 1,700T, OR+AND masked: 2,300T, pre-shifted masked: 2,300T,
  stack/PUSH: 810T, compiled no-mask: 570T, compiled masked: 1,088T

Output: illustrations/output/ch16_sprite_methods.png
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
import numpy as np

# --- Data: (method name, T-states per 16x16 sprite draw) ---
# Using the values from the illustration plan
methods = [
    ('Compiled (no mask)',     570),
    ('Stack / PUSH trick',    810),
    ('Compiled (masked)',    1088),
    ('XOR',                  1700),
    ('OR + AND mask',        2300),
    ('Pre-shifted mask',     2300),
]

# Sort fastest to slowest (already sorted)
labels = [m[0] for m in methods]
costs  = [m[1] for m in methods]

# Colour gradient: green (fast) -> yellow (mid) -> red (slow)
min_cost = min(costs)
max_cost = max(costs)
cmap = mcolors.LinearSegmentedColormap.from_list('speed',
    ['#22AA44', '#AACC22', '#DDAA00', '#DD6622', '#CC3333'])
norm = mcolors.Normalize(vmin=min_cost, vmax=max_cost)
bar_colors = [cmap(norm(c)) for c in costs]

# --- Figure ---
fig, ax = plt.subplots(figsize=(7, 4.0))
fig.patch.set_facecolor('white')
ax.set_facecolor('white')

y_pos = np.arange(len(labels))
bar_height = 0.6

bars = ax.barh(y_pos, costs, height=bar_height, color=bar_colors,
               edgecolor='white', linewidth=0.8)

# T-state labels at end of each bar
for i, (val, bar) in enumerate(zip(costs, bars)):
    ax.text(val + 40, i, f'{val:,}T',
            va='center', ha='left', fontsize=9, fontfamily='monospace',
            fontweight='bold', color='#333333')

# Frame budget line: what you can afford for 8 sprites
# Total frame = 71,680T. With music (5000T) + scroll (12000T) + other (10000T)
# leaves ~44,000T for sprites. 44000 / 8 = 5,500T per sprite.
# But from user's spec: frame budget line at ~3,500T
budget_per_sprite = 3500
ax.axvline(x=budget_per_sprite, color='#CC3333', linestyle='--', linewidth=1.5, alpha=0.8)
ax.text(budget_per_sprite + 40, len(labels) - 0.5,
        f'Budget: {budget_per_sprite:,}T\n(8 sprites in frame)',
        va='top', ha='left', fontsize=7.5, fontfamily='sans-serif',
        color='#CC3333', fontweight='bold')

# Mark methods that fit within budget
for i, cost in enumerate(costs):
    if cost <= budget_per_sprite:
        ax.text(40, i, '', va='center', ha='left', fontsize=10)

ax.set_yticks(y_pos)
ax.set_yticklabels(labels, fontsize=9.5, fontfamily='sans-serif')
ax.set_xlabel('T-states per 16x16 sprite', fontsize=10, fontfamily='sans-serif')
ax.set_title('Sprite Rendering Methods -- Cost Comparison',
             fontsize=13, fontweight='bold', fontfamily='sans-serif', pad=12)
ax.set_xlim(0, max(costs) + 500)

# Info box
info_text = 'Green = fast,  Red = slow\nDashed line = per-sprite budget for 8 sprites'
ax.text(0.98, 0.02, info_text, transform=ax.transAxes,
        ha='right', va='bottom', fontsize=7, fontfamily='sans-serif',
        color='#666666', fontstyle='italic',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='#F8F8F8',
                  edgecolor='#CCCCCC', linewidth=0.5))

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_linewidth(0.5)
ax.spines['bottom'].set_linewidth(0.5)
ax.tick_params(axis='x', labelsize=8)

plt.tight_layout()
plt.savefig('/Users/alice/dev/antique-toy/illustrations/output/ch16_sprite_methods.png',
            dpi=300, bbox_inches='tight', facecolor='white')
plt.close()
print('Saved ch16_sprite_methods.png')
