# Session Report: 2026-02-26

## Packbench Tool + Ch.14 Pre-compression + Ch.20 Sync Workflow

### Done

**1. `tools/packbench.py` — new tool (4 modes)**

- `bench` — run real packer binaries on files, measure compressed sizes. Falls back to Introspec's benchmark ratios when binaries not found. Tested with lz4 (installed), 8 others (estimated).
- `budget` — 128K memory map from TOML config. Shows reserved areas, per-effect compressed storage, bank utilization. Reports over-budget conflicts.
- `timeline` — streaming decompression scheduler. Models overlap (decompress next effect during current), pause (dedicated decompression frames), and streaming (start playing before full decompress). `--what-if` compares all 9 packers per effect.
- `analyze` — pre-compression data analysis. Shannon entropy across transforms (raw, delta, delta², XOR), stride-based transposition testing, curve fitting (linear/quadratic R²), periodicity detection, actionable suggestions ranked by priority.

All modes support `--json` for Clockwork integration.

9 packer profiles: lz4, megalz, pletter, zx0, aplib, zx7, hrust1, exomizer, upkr.
4 platform presets: spectrum48, spectrum128, pentagon128, next.

**2. `demo/packbench.toml` — Antique Toy preset**

5 effects (torus, plasma, dotscroll, rotozoomer, credits) with realistic T-state budgets from the actual demo memory map.

**3. Chapter 14: "Pre-Compression Data Preparation" section (~1,200 words)**

- Shannon entropy as theoretical floor + Python code
- Second derivative encoding (sin ≈ quadratic → linear derivative → constant 2nd derivative)
- Transposition for tabular data (XYZ vertices: 7.52 → 2.58 bits/byte with stride=3 + delta)
- Mask/pixel plane separation
- Practical transforms table (8 data types)
- Key insight: transpose + delta + fast packer > raw + slow packer
- 2 new exercises

**4. Chapter 20: "Synchronisation and Compositing" section (~1,100 words)**

4 approaches to demo sync:
1. Vortex Tracker + manual `dw frame, action` tables (Kolnogorov/Vein workflow)
2. Video editor as sync planner (DaVinci Resolve, Blender VSE — diver4d/GABBA workflow)
3. GNU Rocket (PC/Amiga standard → Z80 export pipeline via Python)
4. Blender pre-visualization (Graph Editor → Python export → Z80 tables)

Central philosophy: "суть синхры в том, чтобы местами было неровно и ломано" — algorithmic sync is dead, human sync is alive.

**5. v16 built and released**

- Version bumped 15 → 16
- PDF (A4: 4.8MB, A5: 4.9MB) + EPUB (3.6MB)
- Copied to `release/`
- CHANGELOG updated
- README updated: word count (~184K), Clockwork mention, tools table, ch14 description

### Screenshots needed (future)

For Ch.20 sync section:
1. GNU Rocket — sync tracks with interpolation curves (MIT, need to build from source)
2. Vortex Tracker II — VTI fork, frame counter visible
3. Blender VSE — timeline with effect clips + audio waveform + markers
4. Blender Graph Editor — keyframe curves → `dw frame, value` export

### Decisions

- Unity/Unreal/Adobe = overkill for ZX Spectrum book, skip
- Cavalry = acquired by Canva, future uncertain, skip
- Motion Canvas (MIT, TypeScript) = best OSS candidate for parametric sync, mention but no screenshot yet
- Clockwork = the gap — no Z80-aware visual timeline tool exists yet
