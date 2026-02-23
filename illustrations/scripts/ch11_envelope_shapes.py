#!/usr/bin/env python3
"""
ch11_envelope_shapes.py -- AY-3-8910 envelope waveform shapes.

Shows the 8 unique envelope patterns in a 2x4 grid.
Each subplot shows volume (0-15) over time for one envelope shape.
Labelled with R13 value and descriptive name.

Output: illustrations/output/ch11_envelope_shapes.png
"""

import matplotlib.pyplot as plt
import numpy as np

# --- ZX Spectrum palette ---
ZX_BLUE    = '#0000D7'
ZX_RED     = '#D70000'
ZX_GREEN   = '#00D700'
ZX_YELLOW  = '#D7D700'
ZX_CYAN    = '#00D7D7'
ZX_MAGENTA = '#D700D7'

# Colours for each envelope shape plot line
PLOT_COLOURS = [ZX_RED, '#DD8833', ZX_BLUE, ZX_CYAN,
                ZX_GREEN, ZX_MAGENTA, ZX_YELLOW, '#00AA00']

def make_envelope(shape_type, periods=3):
    """Generate volume-over-time data for an AY envelope shape.

    Returns (time, volume) arrays covering `periods` envelope cycles.
    One cycle = 16 steps (volume 0-15).
    """
    steps_per_period = 16
    total_steps = steps_per_period * periods

    t = np.arange(total_steps)
    v = np.zeros(total_steps)

    if shape_type == 'decay':
        # \___  (single decay, then hold at 0)
        for i in range(total_steps):
            if i < steps_per_period:
                v[i] = 15 - i
            else:
                v[i] = 0

    elif shape_type == 'attack':
        # /---  (single attack, then hold at 0)
        for i in range(total_steps):
            if i < steps_per_period:
                v[i] = i
            else:
                v[i] = 0

    elif shape_type == 'sawtooth_down':
        # \\\\  (repeating decay)
        for i in range(total_steps):
            v[i] = 15 - (i % steps_per_period)

    elif shape_type == 'decay_hold_low':
        # \___ hold at 0
        for i in range(total_steps):
            if i < steps_per_period:
                v[i] = 15 - i
            else:
                v[i] = 0

    elif shape_type == 'sawtooth_up':
        # ////  (repeating attack)
        for i in range(total_steps):
            v[i] = i % steps_per_period

    elif shape_type == 'attack_hold_high':
        # /--- hold at 15
        for i in range(total_steps):
            if i < steps_per_period:
                v[i] = i
            else:
                v[i] = 15

    elif shape_type == 'triangle_down':
        # \/\/  (decay then attack, repeating)
        for i in range(total_steps):
            pos = i % (steps_per_period * 2)
            if pos < steps_per_period:
                v[i] = 15 - pos
            else:
                v[i] = pos - steps_per_period

    elif shape_type == 'triangle_up':
        # /\/\  (attack then decay, repeating)
        for i in range(total_steps):
            pos = i % (steps_per_period * 2)
            if pos < steps_per_period:
                v[i] = pos
            else:
                v[i] = 2 * steps_per_period - 1 - pos

    return t, v


# The 8 unique AY envelope shapes
# R13 values map to shapes: 0-3 = decay, 4-7 = attack, 8 = sawtooth down,
# 9 = decay hold low, 10 = triangle down, 11 = attack hold high,
# 12 = sawtooth up, 13 = attack hold high, 14 = triangle up, 15 = decay hold low
envelopes = [
    ('$00-$03', 'Decay',             'decay'),
    ('$04-$07', 'Attack',            'attack'),
    ('$08',     'Sawtooth Down',     'sawtooth_down'),
    ('$09',     'Decay, Hold Low',   'decay_hold_low'),
    ('$0A',     'Triangle Down-Up',  'triangle_down'),
    ('$0B',     'Decay, Hold High',  'attack_hold_high'),
    ('$0C',     'Sawtooth Up',       'sawtooth_up'),
    ('$0E',     'Triangle Up-Down',  'triangle_up'),
]

# --- Figure: 2 rows x 4 columns ---
fig, axes = plt.subplots(2, 4, figsize=(7, 3.5))
fig.patch.set_facecolor('white')
fig.suptitle('AY-3-8910 Envelope Shapes (R13)', fontsize=13,
             fontweight='bold', fontfamily='sans-serif', color='#1a1a1a',
             y=1.02)

for idx, (r13_val, name, shape_type) in enumerate(envelopes):
    row = idx // 4
    col = idx % 4
    ax = axes[row, col]

    ax.set_facecolor('#FAFAFA')

    t, v = make_envelope(shape_type, periods=3)

    # Plot as a step function for that crisp digital look
    ax.step(t, v, where='post', color=PLOT_COLOURS[idx], linewidth=1.8)
    ax.fill_between(t, v, step='post', alpha=0.12, color=PLOT_COLOURS[idx])

    # Labels
    ax.set_title(f'R13 = {r13_val}', fontsize=7.5, fontfamily='monospace',
                 fontweight='bold', color='#333333', pad=4)
    ax.text(0.5, 0.92, name, transform=ax.transAxes, ha='center', va='top',
            fontsize=7, fontfamily='sans-serif', color='#555555')

    # Y axis
    ax.set_ylim(-1, 17)
    ax.set_yticks([0, 15])
    ax.set_yticklabels(['0', '15'], fontsize=6, fontfamily='monospace')

    # X axis - just show time arrow
    ax.set_xlim(-1, len(t))
    ax.set_xticks([])
    ax.set_xlabel('time', fontsize=6, color='#888888', labelpad=1)

    # Clean spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_linewidth(0.5)
    ax.spines['bottom'].set_linewidth(0.5)
    ax.spines['left'].set_color('#999999')
    ax.spines['bottom'].set_color('#999999')
    ax.tick_params(axis='y', length=2, width=0.5, colors='#999999')

plt.tight_layout()
plt.savefig('/Users/alice/dev/antique-toy/illustrations/output/ch11_envelope_shapes.png',
            dpi=300, bbox_inches='tight', facecolor='white')
plt.close()
print('Saved ch11_envelope_shapes.png')
