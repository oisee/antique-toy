#!/usr/bin/env python3
"""
ch11_just_intonation.py -- Just Intonation vs Equal Temperament for AY-3-8910.

Main element: Interval ratio diagram for C major scale showing the three
interval sizes (9/8, 10/9, 16/15) as colored bars, with pure fifth arcs
and an equal temperament comparison line.

Secondary element: Period divisibility table for octave 2, showing which
periods divide cleanly by 16 for buzz-bass envelope locking.

Output: illustrations/output/ch11_just_intonation.png
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import numpy as np
from fractions import Fraction

# ---------------------------------------------------------------------------
# Style constants
# ---------------------------------------------------------------------------
BG_COLOR     = '#1a1a2e'
BG_LIGHTER   = '#252545'
TEXT_COLOR    = '#e0e0e0'
TEXT_DIM      = '#8888aa'
TEXT_BRIGHT   = '#ffffff'
GRID_COLOR   = '#2a2a4a'

# ZX Spectrum-inspired bright palette
ZX_CYAN      = '#00D7D7'
ZX_GREEN     = '#00D700'
ZX_MAGENTA   = '#D700D7'
ZX_YELLOW    = '#D7D700'
ZX_RED       = '#D70000'
ZX_BLUE      = '#0055D7'
ZX_WHITE     = '#D7D7D7'

# Interval colors
COL_MAJOR_WHOLE = ZX_CYAN      # 9/8 = major whole tone
COL_MINOR_WHOLE = ZX_GREEN     # 10/9 = minor whole tone
COL_SEMITONE    = ZX_MAGENTA   # 16/15 = diatonic semitone
COL_EQUAL       = ZX_YELLOW    # equal temperament reference
COL_FIFTH_ARC   = '#FF8844'    # pure fifth arcs

# Divisibility colors
COL_CLEAN       = '#44DD44'    # divisible by 16
COL_APPROX      = '#DDAA22'    # approximately (F2)
COL_DIRTY       = '#DD4444'    # not divisible

MONO_FONT = 'monospace'

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
# C major scale just intonation intervals (adjacent)
# C [9/8] D [10/9] E [16/15] F [9/8] G [10/9] A [9/8] B [16/15] C'
notes = ['C', 'D', 'E', 'F', 'G', 'A', 'B', "C'"]
intervals = [
    (Fraction(9, 8),  'Major whole tone'),
    (Fraction(10, 9), 'Minor whole tone'),
    (Fraction(16, 15), 'Diatonic semitone'),
    (Fraction(9, 8),  'Major whole tone'),
    (Fraction(10, 9), 'Minor whole tone'),
    (Fraction(9, 8),  'Major whole tone'),
    (Fraction(16, 15), 'Diatonic semitone'),
]

# Interval sizes in cents for bar widths
def ratio_to_cents(r):
    return 1200 * np.log2(float(r))

interval_cents = [ratio_to_cents(iv[0]) for iv in intervals]

# Octave 2 period data from the chapter
oct2_data = [
    ('C',   1440, True,   '90'),
    ('C#',  1350, False,  '84.4'),
    ('D',   1280, True,   '80'),
    ('D#',  1200, True,   '75'),
    ('E',   1152, True,   '72'),
    ('F',   1080, 'approx', '67.5'),
    ('F#',  1013, False,  '63.3'),
    ('G',    960, True,   '60'),
    ('G#',   900, False,  '56.3'),
    ('A',    864, True,   '54'),
    ('A#',   810, False,  '50.6'),
    ('B',    768, True,   '48'),
]

# ---------------------------------------------------------------------------
# Figure setup
# ---------------------------------------------------------------------------
fig = plt.figure(figsize=(12, 7), dpi=100)
fig.patch.set_facecolor(BG_COLOR)

# Two main areas: left = intervals (wider), right = divisibility table
gs = fig.add_gridspec(1, 2, width_ratios=[2.3, 1], wspace=0.06,
                      left=0.04, right=0.98, top=0.88, bottom=0.06)

ax_main = fig.add_subplot(gs[0, 0])
ax_table = fig.add_subplot(gs[0, 1])

for ax in [ax_main, ax_table]:
    ax.set_facecolor(BG_COLOR)
    ax.tick_params(colors=TEXT_DIM)
    for spine in ax.spines.values():
        spine.set_color(GRID_COLOR)

# ---------------------------------------------------------------------------
# Title
# ---------------------------------------------------------------------------
fig.text(0.50, 0.965, 'Just Intonation: Natural Tuning for AY-3-8910',
         ha='center', va='center', fontsize=16, fontweight='bold',
         fontfamily=MONO_FONT, color=TEXT_BRIGHT)
fig.text(0.50, 0.925, 'Table #5  \u2014  Ivan Roshin (2001) / oisee (2009)',
         ha='center', va='center', fontsize=10, fontfamily=MONO_FONT,
         color=TEXT_DIM)

# ===========================================================================
# LEFT PANEL: Interval ratio diagram
# ===========================================================================
ax = ax_main
ax.set_xlim(-0.5, 8.0)
ax.set_ylim(-3.2, 5.6)
ax.axis('off')

# Section label
ax.text(3.75, 5.3, 'C Major Scale Intervals', ha='center', va='center',
        fontsize=13, fontweight='bold', fontfamily=MONO_FONT, color=TEXT_BRIGHT)

# --- Note positions along x-axis ---
# Place notes at cumulative cent positions, scaled to 0-7.5 range
cum_cents = [0]
for c in interval_cents:
    cum_cents.append(cum_cents[-1] + c)
total_cents = cum_cents[-1]  # ~1200
note_x = [c / total_cents * 7.5 for c in cum_cents]

# --- Draw interval bars ---
bar_y = 2.5
bar_h = 0.65

def get_interval_color(ratio):
    if ratio == Fraction(9, 8):
        return COL_MAJOR_WHOLE
    elif ratio == Fraction(10, 9):
        return COL_MINOR_WHOLE
    else:
        return COL_SEMITONE

for i, (ratio, name) in enumerate(intervals):
    x_left = note_x[i]
    x_right = note_x[i + 1]
    width = x_right - x_left
    color = get_interval_color(ratio)

    # Bar fill
    rect = mpatches.FancyBboxPatch(
        (x_left + 0.02, bar_y - bar_h / 2), width - 0.04, bar_h,
        boxstyle='round,pad=0.03',
        facecolor=color, edgecolor=color, alpha=0.30, linewidth=1.5
    )
    ax.add_patch(rect)
    # Bar border (brighter)
    rect_border = mpatches.FancyBboxPatch(
        (x_left + 0.02, bar_y - bar_h / 2), width - 0.04, bar_h,
        boxstyle='round,pad=0.03',
        facecolor='none', edgecolor=color, alpha=0.9, linewidth=1.5
    )
    ax.add_patch(rect_border)

    # Ratio label inside bar
    cx = (x_left + x_right) / 2
    ratio_str = f'{ratio.numerator}/{ratio.denominator}'
    ax.text(cx, bar_y + 0.03, ratio_str,
            ha='center', va='center', fontsize=10, fontweight='bold',
            fontfamily=MONO_FONT, color=color,
            path_effects=[pe.withStroke(linewidth=3, foreground=BG_COLOR)])

    # Cents below the bar
    cents_val = interval_cents[i]
    ax.text(cx, bar_y - bar_h / 2 - 0.12, f'{cents_val:.1f}\u00a2',
            ha='center', va='top', fontsize=7, fontfamily=MONO_FONT,
            color=TEXT_DIM)

# --- Note labels on a baseline ---
note_y = 3.6
for i, (note, x) in enumerate(zip(notes, note_x)):
    # Note circle
    circle = plt.Circle((x, note_y), 0.22, facecolor=BG_LIGHTER,
                         edgecolor=TEXT_COLOR, linewidth=1.5)
    ax.add_patch(circle)
    ax.text(x, note_y, note, ha='center', va='center',
            fontsize=11, fontweight='bold', fontfamily=MONO_FONT,
            color=TEXT_BRIGHT)

    # Vertical tick down to bar
    ax.plot([x, x], [note_y - 0.22, bar_y + bar_h / 2 + 0.05],
            color=TEXT_DIM, linewidth=0.5, alpha=0.4, linestyle=':')

# --- Pure fifth arcs ---
note_to_idx = {n: i for i, n in enumerate(notes)}
arc_data = [
    ('C', 'G', 0.65, 'C\u2192G  3:2 (pure fifth)'),
    ('E', 'B', 0.35, 'E\u2192B  3:2'),
]

for note_from, note_to, arc_height, label_text in arc_data:
    i_from = note_to_idx[note_from]
    i_to = note_to_idx[note_to]
    x_from = note_x[i_from]
    x_to = note_x[i_to]
    cx = (x_from + x_to) / 2
    w = x_to - x_from

    # Draw smooth arc above note circles
    theta = np.linspace(0, np.pi, 80)
    arc_xs = cx + (w / 2) * np.cos(theta)
    arc_ys = note_y + 0.28 + arc_height * np.sin(theta)
    ax.plot(arc_xs, arc_ys, color=COL_FIFTH_ARC, linewidth=2.0, alpha=0.85)

    # Small arrowhead at the end (right side) of the arc
    # Use the last few points of the arc to determine direction
    dx = arc_xs[-1] - arc_xs[-3]
    dy = arc_ys[-1] - arc_ys[-3]
    ax.annotate('', xy=(arc_xs[-1], arc_ys[-1]),
                xytext=(arc_xs[-1] - dx * 3, arc_ys[-1] - dy * 3),
                arrowprops=dict(arrowstyle='->', color=COL_FIFTH_ARC,
                                lw=2.0, mutation_scale=12),
                annotation_clip=False)

    # Label at the peak of the arc
    peak_y = note_y + 0.28 + arc_height + 0.10
    ax.text(cx, peak_y, label_text, ha='center', va='bottom',
            fontsize=7.5, fontfamily=MONO_FONT, color=COL_FIFTH_ARC,
            fontweight='bold',
            path_effects=[pe.withStroke(linewidth=2, foreground=BG_COLOR)])

# --- Pitch difference (JI vs ET) ---
diff_y = 1.55
ax.text(3.75, diff_y + 0.25, 'Pitch difference (JI \u2212 ET, cents)',
        ha='center', va='center', fontsize=8, fontfamily=MONO_FONT,
        color=TEXT_DIM)

# Cumulative cents for ET
et_semitones = [2, 2, 1, 2, 2, 2, 1]
et_cum = [0]
for s in et_semitones:
    et_cum.append(et_cum[-1] + s)
et_cum_cents = [s * 100 for s in et_cum]  # 0, 200, 400, 500, 700, 900, 1100, 1200
et_total = et_cum[-1]  # 12
et_note_x = [c / et_total * 7.5 for c in et_cum]

for i in range(len(notes)):
    diff = cum_cents[i] - et_cum_cents[i]
    x_pos = (note_x[i] + et_note_x[i]) / 2
    if abs(diff) < 0.01:
        label = '0'
        color = TEXT_DIM
    else:
        label = f'{diff:+.1f}'
        color = ZX_RED if abs(diff) > 15 else COL_EQUAL
    ax.text(x_pos, diff_y, label,
            ha='center', va='center', fontsize=7.5, fontweight='bold',
            fontfamily=MONO_FONT, color=color,
            path_effects=[pe.withStroke(linewidth=2, foreground=BG_COLOR)])

# --- Equal temperament comparison bars below ---
et_y = 0.65
et_bar_h = 0.40

ax.text(3.75, et_y + 0.55, 'Equal Temperament (for comparison)',
        ha='center', va='center', fontsize=9, fontfamily=MONO_FONT,
        color=COL_EQUAL, alpha=0.9)

for i in range(7):
    x_left = et_note_x[i]
    x_right = et_note_x[i + 1]
    width = x_right - x_left

    rect = mpatches.FancyBboxPatch(
        (x_left + 0.02, et_y - et_bar_h / 2), width - 0.04, et_bar_h,
        boxstyle='round,pad=0.02',
        facecolor=COL_EQUAL, edgecolor=COL_EQUAL, alpha=0.18, linewidth=1
    )
    ax.add_patch(rect)
    rect_b = mpatches.FancyBboxPatch(
        (x_left + 0.02, et_y - et_bar_h / 2), width - 0.04, et_bar_h,
        boxstyle='round,pad=0.02',
        facecolor='none', edgecolor=COL_EQUAL, alpha=0.55, linewidth=1
    )
    ax.add_patch(rect_b)

    # Semitone count inside
    cx = (x_left + x_right) / 2
    ax.text(cx, et_y, f'{et_semitones[i]}',
            ha='center', va='center', fontsize=9, fontweight='bold',
            fontfamily=MONO_FONT, color=COL_EQUAL, alpha=0.85)

# ET note labels below bars
for i, (note, x) in enumerate(zip(notes, et_note_x)):
    ax.text(x, et_y - et_bar_h / 2 - 0.12, note,
            ha='center', va='top', fontsize=8, fontfamily=MONO_FONT,
            color=COL_EQUAL, alpha=0.6)

# "semitones" label
ax.text(7.8, et_y, 'semitones', ha='left', va='center',
        fontsize=6.5, fontfamily=MONO_FONT, color=COL_EQUAL, alpha=0.5,
        rotation=0)

# --- Explanatory note ---
ax.text(3.75, -0.7, 'Just intonation uses integer ratios \u2014 AY periods divide',
        ha='center', va='center', fontsize=8, fontfamily=MONO_FONT,
        color=TEXT_DIM, style='italic')
ax.text(3.75, -0.95, 'cleanly by 16, giving perfect buzz-bass envelope lock',
        ha='center', va='center', fontsize=8, fontfamily=MONO_FONT,
        color=TEXT_DIM, style='italic')

# --- Legend for interval types ---
legend_y = -1.5
legend_items = [
    (COL_MAJOR_WHOLE, '9/8  Major whole tone (204\u00a2)'),
    (COL_MINOR_WHOLE, '10/9 Minor whole tone (182\u00a2)'),
    (COL_SEMITONE,    '16/15 Diatonic semitone (112\u00a2)'),
    (COL_FIFTH_ARC,   '3:2  Pure fifth (702\u00a2)'),
    (COL_EQUAL,       'Equal temperament reference'),
]

for i, (color, label) in enumerate(legend_items):
    col_idx = i % 3
    row_idx = i // 3
    lx = 0.0 + col_idx * 2.7
    ly = legend_y - row_idx * 0.4
    rect = mpatches.FancyBboxPatch(
        (lx - 0.12, ly - 0.12), 0.24, 0.24,
        boxstyle='round,pad=0.02',
        facecolor=color, edgecolor=color, alpha=0.5, linewidth=1
    )
    ax.add_patch(rect)
    ax.text(lx + 0.22, ly, label,
            ha='left', va='center', fontsize=7, fontfamily=MONO_FONT,
            color=TEXT_COLOR)

# ===========================================================================
# RIGHT PANEL: Period divisibility table
# ===========================================================================
ax = ax_table
ax.set_xlim(-0.5, 10.5)
ax.set_ylim(-2.0, 15.5)
ax.axis('off')

# Title
ax.text(5, 14.0, 'Octave 2: Buzz-Bass', ha='center', va='center',
        fontsize=11, fontweight='bold', fontfamily=MONO_FONT,
        color=TEXT_BRIGHT)
ax.text(5, 13.4, 'Period \u00f7 16 = Envelope Period', ha='center', va='center',
        fontsize=8, fontfamily=MONO_FONT, color=TEXT_DIM)

# Column positions (shifted left to fit status symbol)
cols = [0.8, 3.0, 5.5, 7.6, 9.5]
headers = ['Note', 'Period', 'P/16', 'Env', '']

# Column headers
header_y = 12.6
for x, h in zip(cols, headers):
    ax.text(x, header_y, h, ha='center', va='center',
            fontsize=8, fontweight='bold', fontfamily=MONO_FONT,
            color=TEXT_COLOR)

# Divider line
ax.plot([0.0, 10.2], [header_y - 0.3, header_y - 0.3],
        color=GRID_COLOR, linewidth=1)

# Data rows
for i, (note, period, clean, env_str) in enumerate(oct2_data):
    y = header_y - 0.8 - i * 0.95

    # Determine status color and symbol
    if clean is True:
        status_color = COL_CLEAN
        status_sym = '\u2713'  # checkmark
        row_alpha = 1.0
    elif clean == 'approx':
        status_color = COL_APPROX
        status_sym = '\u2248'  # approximately equal
        row_alpha = 0.85
    else:
        status_color = COL_DIRTY
        status_sym = '\u2717'  # X mark
        row_alpha = 0.6

    # Subtle row background for clean notes
    if clean is True:
        row_rect = mpatches.FancyBboxPatch(
            (0.0, y - 0.35), 10.2, 0.7,
            boxstyle='round,pad=0.02',
            facecolor=COL_CLEAN, alpha=0.06, edgecolor='none'
        )
        ax.add_patch(row_rect)

    # Note name
    note_color = TEXT_BRIGHT if clean is True else TEXT_DIM
    ax.text(cols[0], y, note, ha='center', va='center',
            fontsize=9, fontweight='bold', fontfamily=MONO_FONT,
            color=note_color, alpha=row_alpha)

    # Period value
    ax.text(cols[1], y, str(period), ha='center', va='center',
            fontsize=9, fontfamily=MONO_FONT,
            color=TEXT_COLOR, alpha=row_alpha)

    # Period / 16
    p16 = period / 16
    p16_str = str(int(p16)) if p16 == int(p16) else f'{p16:.1f}'
    ax.text(cols[2], y, p16_str, ha='center', va='center',
            fontsize=8, fontfamily=MONO_FONT,
            color=status_color, alpha=row_alpha)

    # Envelope value (integer used in practice)
    ax.text(cols[3], y, env_str, ha='center', va='center',
            fontsize=8, fontfamily=MONO_FONT,
            color=TEXT_COLOR, alpha=row_alpha)

    # Status symbol
    ax.text(cols[4], y, status_sym, ha='center', va='center',
            fontsize=11, fontfamily='sans-serif',
            color=status_color, fontweight='bold')

# Divider line at bottom
bottom_y = header_y - 0.8 - len(oct2_data) * 0.95
ax.plot([0.0, 10.2], [bottom_y + 0.5, bottom_y + 0.5],
        color=GRID_COLOR, linewidth=1)

# Summary
ax.text(5, bottom_y - 0.05, '7/12 notes divide cleanly',
        ha='center', va='center',
        fontsize=8.5, fontweight='bold', fontfamily=MONO_FONT, color=COL_CLEAN)
ax.text(5, bottom_y - 0.55, 'All natural notes of C major',
        ha='center', va='center',
        fontsize=7.5, fontfamily=MONO_FONT, color=TEXT_DIM)
ax.text(5, bottom_y - 1.0, 'ET: 0/12 divide cleanly',
        ha='center', va='center',
        fontsize=7.5, fontfamily=MONO_FONT, color=COL_DIRTY)

# Legend for status symbols
leg_y = bottom_y - 1.8
for sym, label, color in [
    ('\u2713', 'Period mod 16 = 0', COL_CLEAN),
    ('\u2248', 'mod 16 \u2260 0 (F: 1080/16=67.5)', COL_APPROX),
    ('\u2717', 'Rounding error in P/16', COL_DIRTY),
]:
    ax.text(1.5, leg_y, sym, ha='center', va='center',
            fontsize=10, fontfamily='sans-serif', color=color, fontweight='bold')
    ax.text(2.5, leg_y, label, ha='left', va='center',
            fontsize=6.5, fontfamily=MONO_FONT, color=TEXT_DIM)
    leg_y -= 0.55

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------
plt.savefig('/Users/alice/dev/antique-toy/illustrations/output/ch11_just_intonation.png',
            dpi=300, bbox_inches='tight', facecolor=BG_COLOR)
plt.close()
print('Saved ch11_just_intonation.png')
