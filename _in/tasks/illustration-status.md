# Illustration Status — 2026-02-23

## Summary

| Metric | Count |
|--------|-------|
| Total planned | 248 |
| Done | 15 (6%) |
| P1 remaining | ~91 |
| P2 remaining | ~103 |
| P3 remaining | ~42 |

---

## Done (15)

| File | Chapter | Type | Priority |
|------|---------|------|----------|
| `ch01_tstate_costs.png` | Ch01 | TD | P1 |
| `ch01_frame_budget.png` | Ch01 | TD | P1 |
| `ch02_screen_layout.png` | Ch02 | TD | P2 |
| `ch02_attr_byte.png` | Ch02 | CS | P1 |
| `ch04_multiply_walkthrough.png` | Ch04 | TD | P1 |
| `ch05_3d_pipeline.png` | Ch05 | FD | P2 |
| `ch11_ay_registers.png` | Ch11 | CS | P1 |
| `ch11_envelope_shapes.png` | Ch11 | TD | P1 |
| `ch11_te_alignment.png` | Ch11 | TD | P2 |
| `ch11_just_intonation.png` | Ch11 | CS | P1 |
| `ch15_memory_map.png` | Ch15 | CS | P1 |
| `ch16_sprite_methods.png` | Ch16 | TD | P1 |
| `ch17_scroll_costs.png` | Ch17 | TD | P1 |
| `ch18_game_loop.png` | Ch18 | FD | P1 |
| `ch02_screen_layout.svg` | Ch02 | — | — (SVG variant) |

All 15 PNGs embedded in chapter markdown. ✓

---

## Next Batch — P1 High-Impact (recommended)

These are P1 illustrations that would add the most value, grouped by feasibility:

### Batch A: Matplotlib bar/chart (easy, 1-2 hours each)

| ID | Chapter | Description | Type |
|----|---------|-------------|------|
| 3.1 | Ch03 | PUSH vs LDIR fill speed comparison | TD |
| 4.2 | Ch04 | Square table lookup diagram | TD |
| 4.3 | Ch04 | Fixed-point number layout (8.8, 4.12) | CS |
| 6.1 | Ch06 | Skip table concept (sphere columns) | TD |
| 9.1 | Ch09 | Plasma colour mixing (sin sum → attr) | TD |
| 12.1 | Ch12 | Timeline sync architecture | TD |
| 12.2 | Ch12 | Digital drum waveform (1-bit PCM) | TD |
| 14.1 | Ch14 | LZ77 sliding window diagram | CS |
| 14.2 | Ch14 | Compression ratio comparison chart | TD |

### Batch B: Flow/architecture diagrams (medium, matplotlib)

| ID | Chapter | Description | Type |
|----|---------|-------------|------|
| 2.5 | Ch02 | DOWN_HL decision tree | FD |
| 3.6 | Ch03 | SMC dispatch / RET-chaining flow | FD |
| 5.1 | Ch05 | Rotation matrix → fixed-point pipeline | FD |
| 6.3 | Ch06 | Runtime code generation pipeline | FD |
| 8.1 | Ch08 | Beam-racing timing (scanline vs code) | FD |
| 19.1 | Ch19 | AABB collision detection visual | TD |
| 20.1 | Ch20 | Demo scene-table architecture | FD |

### Batch C: Code structure / bit layouts (medium)

| ID | Chapter | Description | Type |
|----|---------|-------------|------|
| 2.2 | Ch02 | Screen address bit decomposition | CS |
| 7.1 | Ch07 | Rotozoomer UV mapping concept | CS |
| 8.2 | Ch08 | Dual-screen buffer layout | CS |
| 10.1 | Ch10 | Dotfield POP-trick memory layout | CS |
| 15.2 | Ch15 | Contention pattern timing | CS |

### Batch D: Pixel art / screenshots (needs emulator/PIL)

| ID | Chapter | Description | Type |
|----|---------|-------------|------|
| 1.4 | Ch01 | Border stripe timing result | PX |
| 2.3 | Ch02 | Interleaved row order vis | PX |
| 2.8 | Ch02 | Attribute clash example | PX |
| 7.2 | Ch07 | Rotozoomer output screenshot | PX |
| 8.3 | Ch08 | Multicolor effect screenshot | PX |

---

## Chapters With Zero Illustrations (need attention)

| Chapter | P1 planned | P2 planned | Topic |
|---------|------------|------------|-------|
| Ch03 | 3 | 3 | Toolbox (PUSH fill, SMC, LDI) |
| Ch06 | 3 | 3 | Sphere rendering |
| Ch07 | 2 | 3 | Rotozoomer |
| Ch08 | 4 | 3 | Multicolor |
| Ch09 | 3 | 3 | Plasma tunnels |
| Ch10 | 2 | 3 | Dotfield scroller |
| Ch12 | 5 | 4 | Music sync, drums |
| Ch13 | 3 | 4 | Sizecoding |
| Ch14 | 4 | 3 | Compression |
| Ch19 | 5 | 6 | Collisions, AI |
| Ch20 | 3 | 3 | Demo workflow |
| Ch21 | 5 | 7 | Full game |
| Ch22 | 4 | 5 | Porting (Agon) |
| Ch23 | 2 | 4 | AI-assisted dev |
| App A | 3 | 3 | Z80 reference |
| App B | 3 | 3 | Sine tables |
| App C | 2 | 3 | Compression ref |
| App G | 3 | 6 | AY registers |

---

## Production Notes

- Style guide: `_in/tasks/illustration-styleguide.md`
- All scripts: `illustrations/scripts/ch{NN}_{name}.py`
- All output: `illustrations/output/ch{NN}_{name}.png`
- Pandoc: `--resource-path=.` already set in `build_book.py`
- Batch A (9 charts) can be parallelised — each is independent
- Batch D (screenshots) blocked until emulator workflow is set up
