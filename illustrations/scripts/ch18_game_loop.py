#!/usr/bin/env python3
"""
ch18_game_loop.py -- Circular game loop diagram.

Four boxes in a circle: HALT(sync) -> Input -> Update -> Render
Connected clockwise with arrows. T-state budget annotations on each segment.
Centre text: "50 Hz / 71,680T"

Output: illustrations/output/ch18_game_loop.png
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# --- ZX Spectrum accent colours ---
ZX_BLUE    = '#0000D7'
ZX_RED     = '#D70000'
ZX_GREEN   = '#00D700'
ZX_CYAN    = '#00D7D7'
ZX_MAGENTA = '#D700D7'
ZX_YELLOW  = '#D7D700'

# --- Phase definitions ---
# (label, sub-label, colour, T-states, percentage)
phases = [
    ('HALT',   'sync to VBlank',     '#666666',    '~30T',    '0.04%'),
    ('Input',  'read keyboard',      ZX_CYAN,      '~500T',   '0.7%'),
    ('Update', 'game logic',         ZX_GREEN,     '~12,000T','16.7%'),
    ('Render', 'sprites + scroll',   ZX_BLUE,      '~36,000T','50.2%'),
]

# --- Figure ---
fig, ax = plt.subplots(figsize=(7, 7))
fig.patch.set_facecolor('white')
ax.set_facecolor('white')

# Circle layout parameters
cx, cy = 3.5, 3.5     # centre
radius = 2.0           # circle radius
box_w = 1.7
box_h = 0.9

# Place 4 boxes at cardinal positions (clockwise from top)
# Top = HALT, Right = Input, Bottom = Update, Left = Render
angles_deg = [90, 0, 270, 180]  # mathematical angles (CCW from right)

positions = []
for angle_deg in angles_deg:
    angle_rad = np.radians(angle_deg)
    x = cx + radius * np.cos(angle_rad)
    y = cy + radius * np.sin(angle_rad)
    positions.append((x, y))

# Draw boxes
for i, ((x, y), (label, sub, col, tstate, pct)) in enumerate(zip(positions, phases)):
    # Box
    rect = mpatches.FancyBboxPatch(
        (x - box_w / 2, y - box_h / 2), box_w, box_h,
        boxstyle='round,pad=0.12',
        facecolor=col, alpha=0.18,
        edgecolor=col, linewidth=2.5
    )
    ax.add_patch(rect)

    # Main label
    ax.text(x, y + 0.12, label,
            va='center', ha='center', fontsize=14, fontfamily='sans-serif',
            fontweight='bold', color=col if col != '#666666' else '#333333')

    # Sub-label
    ax.text(x, y - 0.2, sub,
            va='center', ha='center', fontsize=7.5, fontfamily='sans-serif',
            color='#555555')

# Draw clockwise arrows between boxes
# Arrow path: HALT(top) -> Input(right) -> Update(bottom) -> Render(left) -> HALT(top)
arrow_pairs = [
    (0, 1),  # HALT -> Input
    (1, 2),  # Input -> Update
    (2, 3),  # Update -> Render
    (3, 0),  # Render -> HALT
]

# T-state annotations for each arrow (placed along the arc)
arrow_labels = [
    phases[1][3],  # Input cost: ~500T
    phases[2][3],  # Update cost: ~12,000T
    phases[3][3],  # Render cost: ~36,000T
    'music\n~5,000T',  # Music plays during HALT -> next cycle
]

for idx, (i_from, i_to) in enumerate(arrow_pairs):
    x1, y1 = positions[i_from]
    x2, y2 = positions[i_to]

    # Calculate arrow start/end points on box edges
    angle = np.arctan2(y2 - y1, x2 - x1)

    # Offset start/end to box edges
    # Use a simpler approach: shrink the arrow by box dimensions
    shrink = 0.65
    dx = x2 - x1
    dy = y2 - y1
    length = np.sqrt(dx**2 + dy**2)
    nx, ny = dx / length, dy / length

    ax1 = x1 + nx * shrink
    ay1 = y1 + ny * shrink
    ax2 = x2 - nx * shrink
    ay2 = y2 - ny * shrink

    # Curved arrow
    ax.annotate('',
        xy=(ax2, ay2), xytext=(ax1, ay1),
        arrowprops=dict(
            arrowstyle='->', color='#444444', lw=2.0,
            connectionstyle='arc3,rad=0.25',
            shrinkA=5, shrinkB=5
        ))

    # T-state label along the arc (offset outward from centre)
    mid_x = (x1 + x2) / 2
    mid_y = (y1 + y2) / 2
    # Push label outward from centre
    out_x = mid_x - cx
    out_y = mid_y - cy
    out_len = np.sqrt(out_x**2 + out_y**2)
    if out_len > 0.01:
        out_x /= out_len
        out_y /= out_len
    else:
        out_x, out_y = 0, 1

    label_x = mid_x + out_x * 0.75
    label_y = mid_y + out_y * 0.75

    ax.text(label_x, label_y, arrow_labels[idx],
            ha='center', va='center', fontsize=7.5, fontfamily='monospace',
            fontweight='bold', color='#666666',
            bbox=dict(boxstyle='round,pad=0.15', facecolor='white',
                      edgecolor='#CCCCCC', linewidth=0.5, alpha=0.9))

# Centre text
ax.text(cx, cy + 0.15, '50 Hz', ha='center', va='center',
        fontsize=18, fontweight='bold', fontfamily='sans-serif',
        color='#1a1a1a')
ax.text(cx, cy - 0.25, '71,680T / frame', ha='center', va='center',
        fontsize=10, fontfamily='monospace', color='#555555')

# Title
ax.text(cx, cy + radius + 1.3, 'Game Loop Architecture',
        ha='center', va='center', fontsize=14, fontweight='bold',
        fontfamily='sans-serif', color='#1a1a1a')

# Remaining budget annotation
ax.text(cx, cy - 0.65, 'headroom: ~18,000T (25%)',
        ha='center', va='center', fontsize=8, fontfamily='sans-serif',
        color='#888888', fontstyle='italic')

ax.set_xlim(0, 7)
ax.set_ylim(0, 7)
ax.set_aspect('equal')
ax.axis('off')

plt.tight_layout()
plt.savefig('/Users/alice/dev/antique-toy/illustrations/output/ch18_game_loop.png',
            dpi=300, bbox_inches='tight', facecolor='white')
plt.close()
print('Saved ch18_game_loop.png')
