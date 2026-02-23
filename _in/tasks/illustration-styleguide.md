# Illustration Style Guide — "Coding the Impossible"

Visual brand book for all book illustrations. Generated from analysis of 14 existing matplotlib scripts.

---

## Colour Palette

### Primary — ZX Spectrum Bright Colours

| Name      | Hex       | Use |
|-----------|-----------|-----|
| ZX Blue   | `#0000D7` | Load ops, data, flow lines |
| ZX Red    | `#D70000` | I/O, critical, warnings |
| ZX Green  | `#00D700` | Stack ops, success, positive |
| ZX Yellow | `#D7D700` | Emphasis, comparison baseline |
| ZX Cyan   | `#00D7D7` | Tone/signal, input, headers |
| ZX Magenta| `#D700D7` | Flow control, envelope, special |

### Secondary — Derived / Context Colours

| Name          | Hex       | Use |
|---------------|-----------|-----|
| Orange        | `#D78700` | Noise, block transfer, flash |
| Dark green    | `#00AA00` | Stack (darker for readability) |
| Grey neutral  | `#888888` | Idle, disabled, skip |
| Burnt orange  | `#C06030` | Middle-third screen area |
| Steel blue    | `#3D6E9E` | Top-third screen area |
| Sage green    | `#3D8B57` | Bottom-third screen area |

### Memory Map Palette

| Region         | Hex       |
|----------------|-----------|
| ROM            | `#B0B0B0` |
| Screen memory  | `#80D8D8` |
| Code           | `#7090D0` |
| Data           | `#80C890` |
| Switchable bank| `#E8D870` |
| Contended      | `#E8A0A0` |

### Backgrounds

| Context       | Background  | Text       | Grid       |
|---------------|-------------|------------|------------|
| Standard      | `white`     | `#1a1a1a`  | `#CCCCCC`  |
| Dark (audio)  | `#1a1a2e`   | `#e0e0e0`  | `#2a2a4a`  |
| Panel dark    | `#16213e`   | `#e0e0e0`  | `#2a2a4a`  |
| Subtitle      | —           | `#555555`  | —          |
| Dim text      | —           | `#888888`  | —          |

**Rule:** Dark background (`#1a1a2e`) is reserved for audio/signal diagrams (ch11, ch12).
Everything else uses white background.

---

## Typography

| Element             | Font         | Size     | Weight |
|---------------------|--------------|----------|--------|
| Figure title        | sans-serif   | 13-16 pt | bold   |
| Axis label          | sans-serif   | 8-10 pt  | normal |
| Hex/binary/register | **monospace** | 8-10 pt  | bold   |
| Instruction mnemonic| **monospace** | 9-10 pt  | bold   |
| Data value in bar   | **monospace** | 8-9 pt   | bold   |
| Section header      | sans-serif   | 8-11 pt  | bold   |
| Legend              | sans-serif   | 7-8 pt   | normal |
| Footnote/source     | sans-serif   | 6-7 pt   | normal |

**Rule:** monospace ONLY for: hex (`$4000`), binary (`%10101010`), register names (`R13`), T-state counts, period/frequency values, addresses, code mnemonics.
Everything else: sans-serif.

---

## Dimensions

| Diagram type          | figsize           | DPI |
|-----------------------|-------------------|-----|
| Horizontal bar chart  | `(7, 3.5–4.5)`   | 300 |
| Stacked bar           | `(7, 3.0)`        | 300 |
| Flow/pipeline         | `(7, 3.5)`        | 300 |
| Complex layout        | `(7.5, 10.5)`     | 300 |
| Register map          | `(7, 4.5–11.5)`   | 300 |
| Envelope grid (2×4)   | `(7, 3.5)`        | 300 |
| Circular diagram      | `(7, 7)`          | 300 |
| Memory map            | `(7, 8.5)`        | 300 |
| Two-panel comparison  | `(10, 6)`         | 300 |

**Rule:** Always `dpi=300`, `bbox_inches='tight'`. No exceptions.

---

## Layout Rules

### Spines & Grid
- **Always** hide top and right spines
- Left/bottom spine: `linewidth=0.5`, `color='#999999'`
- Grid: `color='#CCCCCC'`, `linewidth=0.5`, `alpha=0.5`

### Bars
- Height: `0.55–0.6` for horizontal bars
- Edge: `white`, `linewidth=0.8`
- Label: outside bar end, monospace bold

### Boxes & Patches
- `FancyBboxPatch` with `boxstyle='round,pad=0.05'`
- Fill: `alpha=0.7–0.9` for primary, `0.15–0.35` for subtle
- Edge: `linewidth=1.2–2.0`

### Legends
- Position: `upper right` (default) or context-appropriate
- `fontsize=8`, `framealpha=0.9`, `edgecolor='#cccccc'`

### Annotations
- Background: `white` with `edgecolor='#CCCCCC'`, `alpha=0.85`
- Arrows: `'->'`, `color='#666666'`, `linewidth=1.5`

### Tight Layout
- Always call `plt.tight_layout()` or use `gridspec` with explicit margins

---

## Diagram Types

### TD — Technical Diagram (matplotlib)
Bar charts, cost comparisons, timing analyses, waveform plots.
~94 planned. Primary tool: matplotlib.

### FD — Flow Diagram (matplotlib or mermaid→png)
Pipelines, state machines, decision trees, game loops.
~44 planned. Prefer matplotlib for consistency; mermaid as fallback.

### CS — Code Structure (matplotlib)
Register maps, bit layouts, memory maps, byte structure.
~88 planned. Use rounded boxes with monospace labels.

### PX — Pixel Art / Screenshot (PIL or emulator)
Actual ZX Spectrum output, attribute clash, visual results.
~22 planned. Annotated emulator screenshots or PIL-generated pixel grids.

---

## File Naming

```
illustrations/scripts/ch{NN}_{short_name}.py
illustrations/output/ch{NN}_{short_name}.png
```

Examples:
- `ch01_frame_budget.py` → `ch01_frame_budget.png`
- `ch11_te_alignment.py` → `ch11_te_alignment.png`
- `appG_envelope_table.py` → `appG_envelope_table.png`

For appendices: `app{letter}_{name}` (e.g. `appA_`, `appB_`, `appC_`, `appG_`).

---

## Markdown Embedding

```markdown
![Alt text description](illustrations/output/chNN_name.png)
```

- `--resource-path` in pandoc points to repo root
- Alt text: 3-10 words, descriptive (for accessibility + EPUB)
- Place image reference AFTER the paragraph introducing the concept, BEFORE the next section

---

## Accessibility

- High contrast text/background (WCAG AA)
- Never rely on colour alone — always add labels, shapes, or borders
- Monospace distinguishes data from prose visually
- Symbols: ✓ (clean), ✗ (error), ≈ (approximate)
