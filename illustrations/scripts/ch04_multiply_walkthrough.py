#!/usr/bin/env python3
"""
ch04_multiply_walkthrough.py — Step-by-step visualization of 8-bit shift-and-add multiply.

Example: 13 x 11 = 143
Multiplier:  13 = 00001101
Multiplicand: 11 = 00001011

Algorithm: test each bit of the multiplier (LSB first), if set add multiplicand
to accumulator, then shift multiplicand left (or shift accumulator right).

We use the classic "shift multiplicand left, test multiplier bits from LSB" approach.

Output: illustrations/output/ch04_multiply_walkthrough.png
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

HIGHLIGHT  = '#FFD700'  # gold for active bit
ADD_COLOR  = ZX_GREEN
SKIP_COLOR = '#999999'
BIT_ON     = '#333333'
BIT_OFF    = '#BBBBBB'

# --- Multiply: 13 x 11 ---
multiplier = 13     # 00001101
multiplicand = 11   # 00001011
expected = multiplier * multiplicand  # 143

# Walk through the algorithm (shift-and-add, LSB first)
# Test multiplier bits from bit 0 to bit 7
# If bit is set: accumulator += multiplicand
# Then: multiplicand <<= 1 (or equivalently, shift the partial product)

steps = []
accumulator = 0
shifted_multiplicand = multiplicand

for bit_pos in range(8):
    bit_val = (multiplier >> bit_pos) & 1
    add_val = shifted_multiplicand if bit_val else 0
    old_acc = accumulator
    accumulator += add_val
    steps.append({
        'bit_pos': bit_pos,
        'bit_val': bit_val,
        'shifted_mcand': shifted_multiplicand,
        'add_val': add_val,
        'old_acc': old_acc,
        'new_acc': accumulator,
    })
    shifted_multiplicand <<= 1

assert accumulator == expected, f"Bug: {accumulator} != {expected}"

# --- Figure ---
fig, ax = plt.subplots(figsize=(7, 7.5))
fig.patch.set_facecolor('white')
ax.set_facecolor('white')
ax.axis('off')

# Title
ax.text(0.5, 0.97, 'Shift-and-Add Multiply: 13 x 11 = 143',
        transform=ax.transAxes, fontsize=14, fontweight='bold',
        ha='center', va='top', fontfamily='sans-serif')

# Subtitle with binary
ax.text(0.5, 0.935,
        f'Multiplier = 13 = 00001101    Multiplicand = 11 = 00001011',
        transform=ax.transAxes, fontsize=9, ha='center', va='top',
        fontfamily='monospace', color='#555555')

# Column headers
header_y = 0.89
col_step = 0.04
col_bit  = 0.14
col_mult_bits = 0.28
col_action = 0.53
col_accum = 0.78
col_accum_bin = 0.92

headers = [
    (col_step, 'Step'),
    (col_bit, 'Bit'),
    (col_mult_bits, 'Multiplier bits'),
    (col_action, 'Action'),
    (col_accum, 'Acc'),
    (col_accum_bin, 'Acc (binary)'),
]

for x, label in headers:
    ax.text(x, header_y, label, transform=ax.transAxes, fontsize=8.5,
            fontweight='bold', ha='center', va='top', fontfamily='sans-serif',
            color='#333333')

# Separator line (drawn in axes coordinates via plot)
ax.plot([0.02, 0.98], [0.87, 0.87], color='#CCCCCC', linewidth=0.5,
        transform=ax.transAxes, clip_on=False)

# Draw each step
row_height = 0.085
start_y = 0.83

for i, step in enumerate(steps):
    y = start_y - i * row_height
    bit_pos = step['bit_pos']
    bit_val = step['bit_val']

    row_color = ADD_COLOR if bit_val else SKIP_COLOR
    row_alpha = 1.0 if bit_val else 0.6

    # Step number
    ax.text(col_step, y, f'{i}', transform=ax.transAxes, fontsize=9,
            ha='center', va='center', fontfamily='monospace', color='#333333')

    # Bit position and value
    ax.text(col_bit, y, f'b{bit_pos} = {bit_val}', transform=ax.transAxes,
            fontsize=9, ha='center', va='center', fontfamily='monospace',
            color=row_color, fontweight='bold' if bit_val else 'normal')

    # Multiplier bits with highlight on current bit
    mult_bits = f'{multiplier:08b}'
    # We need to draw each character individually to highlight the active bit
    bit_str_x_start = col_mult_bits - 0.06
    char_w = 0.015
    for j in range(8):
        cx = bit_str_x_start + j * char_w
        # Bit index in the binary string: bit 7 is index 0, bit 0 is index 7
        actual_bit_pos = 7 - j
        ch = mult_bits[j]

        if actual_bit_pos == bit_pos:
            # Highlight this bit
            rect = mpatches.FancyBboxPatch(
                (cx - 0.005, y - 0.015), 0.013, 0.030,
                boxstyle='round,pad=0.002',
                facecolor=HIGHLIGHT, alpha=0.7,
                edgecolor='none',
                transform=ax.transAxes
            )
            ax.add_patch(rect)
            ax.text(cx + 0.001, y, ch, transform=ax.transAxes, fontsize=9,
                    ha='center', va='center', fontfamily='monospace',
                    fontweight='bold', color='#000000')
        else:
            c = BIT_ON if ch == '1' else BIT_OFF
            ax.text(cx + 0.001, y, ch, transform=ax.transAxes, fontsize=9,
                    ha='center', va='center', fontfamily='monospace', color=c)

    # Action
    if bit_val:
        action_str = f'ADD {step["shifted_mcand"]}'
        action_color = ADD_COLOR
    else:
        action_str = 'skip'
        action_color = SKIP_COLOR

    ax.text(col_action, y, action_str, transform=ax.transAxes, fontsize=9,
            ha='center', va='center', fontfamily='monospace',
            color=action_color, fontweight='bold' if bit_val else 'normal')

    # Accumulator value
    ax.text(col_accum, y, f'{step["new_acc"]}', transform=ax.transAxes,
            fontsize=9, ha='center', va='center', fontfamily='monospace',
            color='#333333', fontweight='bold')

    # Accumulator binary (16-bit for clarity)
    acc_bin = f'{step["new_acc"]:016b}'
    ax.text(col_accum_bin, y, acc_bin[-8:], transform=ax.transAxes,
            fontsize=8, ha='center', va='center', fontfamily='monospace',
            color='#555555')

# Final result box
result_y = start_y - 8 * row_height - 0.02

# Draw a light box
rect = mpatches.FancyBboxPatch(
    (0.15, result_y - 0.025), 0.70, 0.05,
    boxstyle='round,pad=0.01',
    facecolor='#F0F0F0', edgecolor='#999999', linewidth=1.0,
    transform=ax.transAxes
)
ax.add_patch(rect)

ax.text(0.5, result_y, f'Result: 13 x 11 = {expected}  (${expected:02X} = {expected:08b})',
        transform=ax.transAxes, fontsize=11, fontweight='bold',
        ha='center', va='center', fontfamily='monospace', color='#1a1a1a')

# Legend
legend_y = result_y - 0.06
ax.text(0.22, legend_y, 'Bit set: ADD multiplicand',
        transform=ax.transAxes, fontsize=8, color=ADD_COLOR, fontfamily='sans-serif')
ax.text(0.60, legend_y, 'Bit clear: skip (no addition)',
        transform=ax.transAxes, fontsize=8, color=SKIP_COLOR, fontfamily='sans-serif')

ax.set_xlim(0, 1)
ax.set_ylim(0, 1)

plt.tight_layout()
plt.savefig('/Users/alice/dev/antique-toy/illustrations/output/ch04_multiply_walkthrough.png',
            dpi=300, bbox_inches='tight', facecolor='white')
plt.close()
print('Saved ch04_multiply_walkthrough.png')
