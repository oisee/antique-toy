#!/usr/bin/env python3
"""
ch05_3d_pipeline.py — 3D rendering pipeline flow diagram for Z80 wireframe engine.

Pipeline stages:
  Model coords -> Rotate -> Project -> Clip -> Draw

With coordinate type annotations at each stage.

Output: illustrations/output/ch05_3d_pipeline.png
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import numpy as np

# --- ZX Spectrum palette ---
ZX_BLUE    = '#0000D7'
ZX_RED     = '#D70000'
ZX_GREEN   = '#00D700'
ZX_YELLOW  = '#D7D700'
ZX_CYAN    = '#00D7D7'
ZX_MAGENTA = '#D700D7'

# Stage colours (gradient from blue to green)
STAGE_COLORS = ['#0055AA', ZX_BLUE, '#4400AA', ZX_MAGENTA, ZX_RED]
STAGE_COLORS = ['#2255AA', '#3366CC', '#5544BB', '#7733AA', '#AA2266']

# --- Data ---
stages = [
    {
        'label': 'Model\nCoords',
        'detail': '(x, y, z)',
        'desc': '3D local\nvertices',
    },
    {
        'label': 'Rotate',
        'detail': 'Z, Y, X axes',
        'desc': '3D world\ncoordinates',
    },
    {
        'label': 'Project',
        'detail': 'perspective\ndivision',
        'desc': '2D screen\ncoordinates',
    },
    {
        'label': 'Clip',
        'detail': 'bounds\ncheck',
        'desc': 'visible\nvertices',
    },
    {
        'label': 'Draw',
        'detail': 'Bresenham\nlines',
        'desc': 'pixels on\nscreen',
    },
]

# --- Figure ---
fig, ax = plt.subplots(figsize=(7, 3.5))
fig.patch.set_facecolor('white')
ax.set_facecolor('white')
ax.axis('off')

n = len(stages)
box_w = 1.1
box_h = 0.9
gap = 0.55
total_w = n * box_w + (n - 1) * gap
x_start = (7 - total_w) / 2
y_center = 1.75

# Subtle gradient background boxes
for i, stage in enumerate(stages):
    x = x_start + i * (box_w + gap)
    y = y_center - box_h / 2

    # Main box with rounded corners
    color = STAGE_COLORS[i]
    rect = mpatches.FancyBboxPatch(
        (x, y), box_w, box_h,
        boxstyle='round,pad=0.08',
        facecolor=color, edgecolor='white', linewidth=2.0, alpha=0.90
    )
    ax.add_patch(rect)

    # Stage label (bold, white)
    ax.text(x + box_w / 2, y_center + 0.08, stage['label'],
            ha='center', va='center', fontsize=11, fontweight='bold',
            fontfamily='sans-serif', color='white',
            path_effects=[pe.withStroke(linewidth=0.5, foreground='#00000033')])

    # Technique detail (smaller, white)
    ax.text(x + box_w / 2, y_center - 0.28, stage['detail'],
            ha='center', va='center', fontsize=7, fontfamily='monospace',
            color='#FFFFFFCC', linespacing=1.2)

    # Coordinate type annotation below box
    ax.text(x + box_w / 2, y - 0.20, stage['desc'],
            ha='center', va='top', fontsize=7.5, fontfamily='sans-serif',
            color='#555555', linespacing=1.3, style='italic')

    # Draw arrow to next stage
    if i < n - 1:
        arrow_x_start = x + box_w + 0.04
        arrow_x_end = x + box_w + gap - 0.04
        ax.annotate('', xy=(arrow_x_end, y_center),
                    xytext=(arrow_x_start, y_center),
                    arrowprops=dict(
                        arrowstyle='->', color='#666666',
                        lw=2.0, mutation_scale=15,
                        connectionstyle='arc3,rad=0'
                    ))

# Title
ax.text(3.5, y_center + box_h / 2 + 0.55,
        '3D Rendering Pipeline (Z80 Wireframe Engine)',
        ha='center', va='center', fontsize=13, fontweight='bold',
        fontfamily='sans-serif', color='#1a1a1a')

# Subtitle with cost annotation
ax.text(3.5, y_center + box_h / 2 + 0.25,
        'Total: ~42,720 T-states per frame for 8-vertex cube on Pentagon 128K',
        ha='center', va='center', fontsize=8, fontfamily='monospace',
        color='#888888')

# Data flow label beneath everything
ax.annotate('', xy=(x_start + total_w - 0.1, y_center - box_h / 2 - 0.68),
            xytext=(x_start + 0.1, y_center - box_h / 2 - 0.68),
            arrowprops=dict(arrowstyle='->', color='#CCCCCC',
                            lw=1.5, mutation_scale=12))
ax.text(3.5, y_center - box_h / 2 - 0.80, 'Data flow',
        ha='center', va='top', fontsize=7.5, color='#AAAAAA',
        fontfamily='sans-serif', style='italic')

ax.set_xlim(-0.2, 7.2)
ax.set_ylim(0.0, 3.2)

plt.tight_layout()
plt.savefig('/Users/alice/dev/antique-toy/illustrations/output/ch05_3d_pipeline.png',
            dpi=300, bbox_inches='tight', facecolor='white')
plt.close()
print('Saved ch05_3d_pipeline.png')
