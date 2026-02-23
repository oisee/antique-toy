#!/usr/bin/env python3
"""
ch11_te_alignment.py -- Tone + Envelope phase alignment for AY-3-8910.

Compares "clean" T+E buzz (tone period exactly divisible by 16) with
"beating" T+E buzz (tone period NOT divisible by 16).

Top panel:  Clean alignment -- envelope and tone stay in phase.
Bottom panel: Beating buzz -- envelope drifts relative to tone, producing
              the characteristic warble / amplitude modulation.

Output: illustrations/output/ch11_te_alignment.png
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import NullLocator

# ---------------------------------------------------------------------------
# Colours -- dark theme with ZX Spectrum bright palette
# ---------------------------------------------------------------------------
BG_DARK    = '#1a1a2e'
BG_PANEL   = '#16213e'
GRID_CLR   = '#2a2a4a'
TEXT_CLR    = '#cccccc'
TITLE_CLR  = '#ffffff'
CYAN       = '#00FFFF'   # tone
YELLOW     = '#FFFF00'   # envelope
GREEN      = '#00FF00'   # combined
GREY_DIM   = '#666688'
ACCENT_RED = '#FF4444'

# ---------------------------------------------------------------------------
# Helper: generate AY-style signals
# ---------------------------------------------------------------------------

def tone_wave(t, half_period):
    """Square wave toggling every `half_period` samples.  Output 0 or 1."""
    return ((t // half_period) % 2).astype(float)


def envelope_sawtooth(t, env_period):
    """Repeating sawtooth 0..15 over `env_period` steps, then reset.
    This models AY envelope shape $0C (sawtooth up, repeating)."""
    phase = t % env_period
    return (phase / env_period) * 15.0


def combined_signal(tone, envelope):
    """When tone gate is HIGH, output = envelope volume.
    When tone gate is LOW, output = 0.
    This is the simplified AY T+E mixing model."""
    return tone * envelope

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------

# CLEAN case: C2, tone period = 1440 (1440 / 16 = 90 exactly)
CLEAN_TONE_PERIOD = 1440       # full period in AY clock steps
CLEAN_ENV_PERIOD  = 90         # = 1440 / 16

# BEATING case: C4 (12-TET), tone period = 424 (424 / 16 = 26.5 -> 26)
BEAT_TONE_PERIOD  = 424
BEAT_ENV_PERIOD   = 26         # truncated from 26.5

# We'll show several complete tone cycles to make the drift visible.
# Use a normalised time axis so both panels have comparable visual width.
# Show enough cycles to see ~2 full beat periods in the bottom panel.

CLEAN_SHOW_CYCLES = 6          # 6 tone cycles
BEAT_SHOW_CYCLES  = 12         # 12 tone cycles to see the drift

clean_samples = CLEAN_TONE_PERIOD * CLEAN_SHOW_CYCLES
beat_samples  = BEAT_TONE_PERIOD * BEAT_SHOW_CYCLES

t_clean = np.arange(clean_samples)
t_beat  = np.arange(beat_samples)

# Generate signals
clean_tone = tone_wave(t_clean, CLEAN_TONE_PERIOD // 2)
clean_env  = envelope_sawtooth(t_clean, CLEAN_ENV_PERIOD)
clean_comb = combined_signal(clean_tone, clean_env)

beat_tone  = tone_wave(t_beat, BEAT_TONE_PERIOD // 2)
beat_env   = envelope_sawtooth(t_beat, BEAT_ENV_PERIOD)
beat_comb  = combined_signal(beat_tone, beat_env)

# Normalise time to [0, 1] for each panel so they have similar visual width
t_clean_norm = t_clean / clean_samples
t_beat_norm  = t_beat / beat_samples

# ---------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------

fig, (ax_top, ax_bot) = plt.subplots(
    2, 1, figsize=(10, 6), dpi=100,
    gridspec_kw={'hspace': 0.38}
)
fig.patch.set_facecolor(BG_DARK)

# Suptitle
fig.suptitle('Tone + Envelope Phase Alignment',
             fontsize=16, fontweight='bold', fontfamily='monospace',
             color=TITLE_CLR, y=0.97)


def style_axis(ax, title_text, label_text):
    """Apply common dark-theme styling to an axis."""
    ax.set_facecolor(BG_PANEL)
    ax.set_title(title_text, fontsize=11, fontweight='bold',
                 fontfamily='monospace', color=TITLE_CLR, pad=10, loc='left')

    # Subtle grid
    ax.grid(True, color=GRID_CLR, linewidth=0.4, alpha=0.6)
    ax.set_xlim(0, 1)
    ax.set_ylim(-2, 19)
    ax.set_yticks([0, 5, 10, 15])
    ax.set_yticklabels(['0', '5', '10', '15'],
                       fontsize=7, fontfamily='monospace', color=GREY_DIM)
    ax.set_ylabel('Volume', fontsize=8, fontfamily='monospace',
                  color=GREY_DIM, labelpad=6)
    ax.xaxis.set_major_locator(NullLocator())
    ax.set_xlabel('time  \u2192', fontsize=8, fontfamily='monospace',
                  color=GREY_DIM, labelpad=4)

    # Spines
    for spine in ax.spines.values():
        spine.set_color(GRID_CLR)
        spine.set_linewidth(0.6)
    ax.tick_params(axis='y', length=3, width=0.5, colors=GREY_DIM)

    # Label box at bottom-right
    ax.text(0.99, 0.04, label_text, transform=ax.transAxes,
            ha='right', va='bottom', fontsize=7.5, fontfamily='monospace',
            color=TEXT_CLR, alpha=0.85,
            bbox=dict(boxstyle='round,pad=0.4', facecolor=BG_DARK,
                      edgecolor=GRID_CLR, alpha=0.9))


# ---- Top panel: Clean alignment ----
style_axis(ax_top,
           'Clean T+E (period divisible by 16)',
           'C2   period=1440   envelope=90   (1440/16 = 90 exact)')

# Tone: scale square wave to sit at top of plot as reference
tone_display = clean_tone * 15
ax_top.step(t_clean_norm, tone_display, where='post',
            color=CYAN, linewidth=0.9, alpha=0.45, label='Tone (square)')

# Envelope
ax_top.plot(t_clean_norm, clean_env,
            color=YELLOW, linewidth=0.8, alpha=0.55, label='Envelope (sawtooth)')

# Combined (the signal you actually hear)
ax_top.fill_between(t_clean_norm, 0, clean_comb, step='post',
                    color=GREEN, alpha=0.15)
ax_top.step(t_clean_norm, clean_comb, where='post',
            color=GREEN, linewidth=1.2, alpha=0.9, label='Combined output')

# Mark envelope resets with tiny vertical lines
env_resets_clean = np.where(np.diff(clean_env) < -1)[0] + 1
for r in env_resets_clean:
    x = t_clean_norm[r]
    ax_top.axvline(x, color=YELLOW, linewidth=0.3, alpha=0.25, linestyle='--')

ax_top.legend(loc='upper right', fontsize=7, fancybox=False,
              framealpha=0.7, edgecolor=GRID_CLR,
              facecolor=BG_DARK, labelcolor=TEXT_CLR)

# ---- Bottom panel: Beating buzz ----
style_axis(ax_bot,
           'Beating T+E (period NOT divisible by 16)',
           'C4 (12-TET)   period=424   envelope=26   '
           '(424/16 = 26.5 \u2192 26, error!)')

tone_display_b = beat_tone * 15
ax_bot.step(t_beat_norm, tone_display_b, where='post',
            color=CYAN, linewidth=0.9, alpha=0.45, label='Tone (square)')

ax_bot.plot(t_beat_norm, beat_env,
            color=YELLOW, linewidth=0.8, alpha=0.55, label='Envelope (sawtooth)')

ax_bot.fill_between(t_beat_norm, 0, beat_comb, step='post',
                    color=GREEN, alpha=0.15)
ax_bot.step(t_beat_norm, beat_comb, where='post',
            color=GREEN, linewidth=1.2, alpha=0.9, label='Combined output')

# Mark envelope resets
env_resets_beat = np.where(np.diff(beat_env) < -1)[0] + 1
for r in env_resets_beat:
    x = t_beat_norm[r]
    ax_bot.axvline(x, color=YELLOW, linewidth=0.3, alpha=0.25, linestyle='--')

# Mark tone-edge/envelope-phase drift with red arrows at a few points
# Find tone rising edges (0->1 transitions)
tone_edges = np.where(np.diff(beat_tone) > 0)[0] + 1
# At each tone rising edge, check envelope phase
for i, edge in enumerate(tone_edges):
    if edge >= len(beat_env):
        continue
    env_phase = (beat_env[edge] / 15.0)  # 0..1 within envelope cycle
    # Only annotate every other edge to avoid clutter, skip first
    if i > 0 and i % 2 == 0:
        x = t_beat_norm[edge]
        # Small red tick at top showing the drift
        ax_bot.plot(x, 16.5, marker='v', markersize=3,
                    color=ACCENT_RED, alpha=0.7)

# Add a "drift" annotation
if len(tone_edges) > 6:
    mid_edge = tone_edges[len(tone_edges) // 2]
    x_mid = t_beat_norm[mid_edge]
    ax_bot.annotate('phase drift',
                    xy=(x_mid, 16.5), xytext=(x_mid + 0.06, 17.8),
                    fontsize=7, fontfamily='monospace', color=ACCENT_RED,
                    arrowprops=dict(arrowstyle='->', color=ACCENT_RED,
                                   lw=0.8),
                    ha='left', va='center')

ax_bot.legend(loc='upper right', fontsize=7, fancybox=False,
              framealpha=0.7, edgecolor=GRID_CLR,
              facecolor=BG_DARK, labelcolor=TEXT_CLR)

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------
out_path = '/Users/alice/dev/antique-toy/illustrations/output/ch11_te_alignment.png'
plt.savefig(out_path, dpi=300, bbox_inches='tight', facecolor=BG_DARK)
plt.close()
print(f'Saved {out_path}')
