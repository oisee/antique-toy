#!/usr/bin/env python3
"""
ch01_frame_budget.py — Stacked horizontal bar chart: frame budget breakdown.

Pentagon 128K: 71,680 T-states per frame
ZX Spectrum 48K: 69,888 T-states per frame
Agon Light 2: ~368,000 T-states per frame (18.432 MHz / 50 Hz)

Segments: Music player, Main effect, Screen clear, Idle
Output: illustrations/output/ch01_frame_budget.png
"""

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

# --- ZX Spectrum palette accent colours ---
ZX_BLUE    = '#0000D7'
ZX_RED     = '#D70000'
ZX_GREEN   = '#00D700'
ZX_YELLOW  = '#D7D700'
ZX_CYAN    = '#00D7D7'
ZX_MAGENTA = '#D700D7'

# --- Data ---
machines = ['Agon Light 2\n(18.432 MHz)', 'Pentagon 128K\n(3.5 MHz)', 'ZX 48K\n(3.5 MHz)']
totals   = [368640, 71680, 69888]

# Segment breakdown (T-states)
music       = [20000,  4000,  4000]
main_effect = [200000, 40000, 38000]
screen_clr  = [100000, 20000, 20000]
idle        = [t - m - e - s for t, m, e, s in zip(totals, music, main_effect, screen_clr)]

segments = [music, main_effect, screen_clr, idle]
seg_labels = ['Music player', 'Main effect', 'Screen clear', 'Idle']
seg_colors = [ZX_MAGENTA, ZX_BLUE, ZX_CYAN, '#888888']

# --- Figure ---
fig, ax = plt.subplots(figsize=(7, 3.0))
fig.patch.set_facecolor('white')
ax.set_facecolor('white')

y_pos = np.arange(len(machines))
bar_height = 0.55

# Draw stacked bars
lefts = np.zeros(len(machines))
for seg_vals, label, color in zip(segments, seg_labels, seg_colors):
    bars = ax.barh(y_pos, seg_vals, left=lefts, height=bar_height,
                   label=label, color=color, edgecolor='white', linewidth=0.8)
    lefts += np.array(seg_vals)

# Add total labels at the right end
for i, total in enumerate(totals):
    ax.text(total + 3000, i, f'{total:,}T',
            va='center', ha='left', fontsize=9, fontfamily='monospace',
            fontweight='bold', color='#333333')

# Labels inside bars for the Pentagon row (index 1) — the primary reference
pent_segs = [music[1], main_effect[1], screen_clr[1], idle[1]]
pent_lefts = [0]
for s in pent_segs[:-1]:
    pent_lefts.append(pent_lefts[-1] + s)
for left, val, label in zip(pent_lefts, pent_segs, seg_labels):
    cx = left + val / 2
    if val > 5000:  # only label if segment is wide enough
        ax.text(cx, 1, f'{val // 1000}K',
                va='center', ha='center', fontsize=7.5, fontfamily='monospace',
                color='white', fontweight='bold')

ax.set_yticks(y_pos)
ax.set_yticklabels(machines, fontsize=9, fontfamily='monospace')
ax.set_xlabel('T-states per frame', fontsize=10, fontfamily='sans-serif')
ax.set_title('Frame Budget Breakdown', fontsize=13, fontweight='bold',
             fontfamily='sans-serif', pad=12)

ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{int(x):,}'))
ax.set_xlim(0, max(totals) * 1.15)
ax.tick_params(axis='x', labelsize=8)

# Legend
ax.legend(loc='lower right', fontsize=8, framealpha=0.9, edgecolor='#cccccc')

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_linewidth(0.5)
ax.spines['bottom'].set_linewidth(0.5)

plt.tight_layout()
plt.savefig('/Users/alice/dev/antique-toy/illustrations/output/ch01_frame_budget.png',
            dpi=300, bbox_inches='tight', facecolor='white')
plt.close()
print('Saved ch01_frame_budget.png')
