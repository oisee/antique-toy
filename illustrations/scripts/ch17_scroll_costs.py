#!/usr/bin/env python3
"""
ch17_scroll_costs.py -- Scrolling method cost comparison.

Bar chart comparing scrolling methods with frame budget line.
Highlights the combined 8-frame method as the winner.

Methods from illustration plan (ch17.1):
  Full pixel horizontal: 135,000T
  Full pixel vertical: 107,000T
  Shadow + tile redraw: 59,000T
  Character scroll: 52,000-66,000T (use 59,000T midpoint)
  Attribute only: 17,000T
  Combined 8-frame (peak): 70,000T
  Combined 8-frame (average): 10,000T

Also from user's request:
  RL chain: 2,080T, LDIR: 4,000T, unrolled RL: 1,200T, combined: avg 600T

Using the chapter-level summary values for the main chart.

Output: illustrations/output/ch17_scroll_costs.png
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
import numpy as np

# --- Data: methods sorted by cost (slowest to fastest at top, chart reads naturally) ---
methods = [
    ('Full pixel horizontal',     135000, False),
    ('Full pixel vertical',       107000, False),
    ('Combined 8-frame (peak)',    70000, False),
    ('Character scroll',           59000, False),
    ('Shadow + tile redraw',       59000, False),
    ('Attribute-only LDIR',        17000, False),
    ('Combined 8-frame (avg)',     10000, True),   # winner
]

# Reverse so fastest at top
methods = list(reversed(methods))

labels   = [m[0] for m in methods]
costs    = [m[1] for m in methods]
winners  = [m[2] for m in methods]

# Colour gradient
min_cost = min(costs)
max_cost = max(costs)
cmap = mcolors.LinearSegmentedColormap.from_list('speed',
    ['#22AA44', '#AACC22', '#DDAA00', '#DD6622', '#CC3333'])
norm = mcolors.Normalize(vmin=min_cost, vmax=max_cost)
bar_colors = [cmap(norm(c)) for c in costs]

# Override winner colour to bright green with border
for i, w in enumerate(winners):
    if w:
        bar_colors[i] = '#22CC44'

# --- Figure ---
fig, ax = plt.subplots(figsize=(7, 4.5))
fig.patch.set_facecolor('white')
ax.set_facecolor('white')

y_pos = np.arange(len(labels))
bar_height = 0.6

bars = ax.barh(y_pos, costs, height=bar_height, color=bar_colors,
               edgecolor='white', linewidth=0.8)

# Highlight winner with thicker border
for i, w in enumerate(winners):
    if w:
        bars[i].set_edgecolor('#006600')
        bars[i].set_linewidth(2.0)

# T-state labels at end of each bar
for i, (val, bar) in enumerate(zip(costs, bars)):
    # For very long bars, put label inside; otherwise outside
    if val > 80000:
        ax.text(val - 2000, i, f'{val:,}T',
                va='center', ha='right', fontsize=8.5, fontfamily='monospace',
                fontweight='bold', color='white')
    else:
        ax.text(val + 1500, i, f'{val:,}T',
                va='center', ha='left', fontsize=8.5, fontfamily='monospace',
                fontweight='bold', color='#333333')

# Frame budget line at 71,680T
frame_budget = 71680
ax.axvline(x=frame_budget, color='#CC3333', linestyle='--', linewidth=1.5, alpha=0.8)
ax.text(frame_budget + 1500, len(labels) - 0.3,
        f'Frame budget\n{frame_budget:,}T',
        va='top', ha='left', fontsize=7.5, fontfamily='sans-serif',
        color='#CC3333', fontweight='bold')

# Winner annotation
for i, w in enumerate(winners):
    if w:
        ax.annotate('WINNER', xy=(costs[i] + 1500, i),
                    fontsize=8, fontweight='bold', color='#006600',
                    fontfamily='sans-serif',
                    xytext=(costs[i] + 18000, i + 0.3),
                    arrowprops=dict(arrowstyle='->', color='#006600', lw=1.5))

ax.set_yticks(y_pos)
ax.set_yticklabels(labels, fontsize=9, fontfamily='sans-serif')
ax.invert_yaxis()  # fastest at top
ax.set_xlabel('T-states per frame', fontsize=10, fontfamily='sans-serif')
ax.set_title('Scrolling Methods -- Cost Comparison',
             fontsize=13, fontweight='bold', fontfamily='sans-serif', pad=12)
ax.set_xlim(0, max(costs) + 20000)

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_linewidth(0.5)
ax.spines['bottom'].set_linewidth(0.5)
ax.tick_params(axis='x', labelsize=8)

plt.tight_layout()
plt.savefig('/Users/alice/dev/antique-toy/illustrations/output/ch17_scroll_costs.png',
            dpi=300, bbox_inches='tight', facecolor='white')
plt.close()
print('Saved ch17_scroll_costs.png')
