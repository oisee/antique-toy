# Hype Article Summaries — Fetched Content

> Full content summaries from key articles fetched 2026-02-22.
> These are AI-extracted summaries. For exact quotes, re-fetch the original pages.

---

## 1. Технический разбор Illusion от X-Trade (introspec, 2017-03-18)

**URL:** /blog/dev/670.html

Technical analysis of the ZX Spectrum demo "Illusion" examining internal effects:

**Sphere Texture Mapping:** Monochrome image stored as one byte per pixel mapped onto a sphere using dynamically generated unrolled loops. Code reads pixels sequentially, shifting accumulator A and adding current pixel values, with variable INC L instructions depending on sphere position. Lookup tables at address #6944 contain pixel skip distances. Performance: 101+32x T-states per byte.

**Bouncing Ball Scroller:** Texture-based approach with pixel data in memory, output using stack-based addressing. ~36 cycles per pixel. Inner loop: `ld a,(bc) : pop hl : rla : jr nc,$ : set ?,(hl)`

**Rotozoomer/Moving Shit:** Pre-calculated texture data with 2×2 pixel chunks stored as bytes. Generated code walks horizontally across screen while traversing texture at angles. Inner loop: `ld a,(hl) : inc l : dec h : add a : add a : add (hl)`. Performance: 95 T-states per 4 chunks → 4-6 frames per screen.

**Key insight from Introspec:** "coder effects are always about evolving a computation scheme"

Comments include debates about sine tables, precalculation, sphere projections, border timings (the 11 vs 12 T-state OUT argument).

---

## 2. Making of Eager (introspec, 2015-08-09)

**URL:** /blog/demo/261.html

Development of the ZX Spectrum demo "Eager (to live)" from June–August 2015.

**Digital Drums:** When drums needed to play, engine stops note playback and plays drum sounds. Digital samples blended with AY: loudness problem solved by n1k-o's insight (digital attack + AY decay = convincing hybrid).

**Asynchronous Frame Generation:** Frames generated asynchronously with display. Engine prepares multiple video pages while drum audio plays. 2 frames per drum hit. Double-buffered attribute frames.

**Attribute copying with reflections (4-fold symmetry):**
```z80
ld a,(hl)      ; source byte
ld (nn),a      ; upper quarter right
ld (mm),a      ; lower quarter left
ld (bc),a      ; lower quarter right
ldi            ; under 15 cycles per byte
```

**Chaos zoomer:** Unrolled `ld hl,nn : ldi` with optimizations.

**Code generation in Processing → Z80 assembly.**

**Scripting engine:** Two-level: outer script (effects) + inner script (variations). kWORK command: generate N frames, show independently. Async generation: falling behind during drums, catching up between hits.

---

## 3. Сжатие данных для современного кодинга под Z80 (introspec, 2017-09-08)

**URL:** /blog/dev/740.html

Comprehensive comparison of 10 data compression tools for Z80:

| Tool | Compression Ratio | Speed (cycles/byte) | Decompressor Size |
|------|-------------------|---------------------|-------------------|
| Exomizer | 48.31% | ~250 | larger |
| ApLib | 49.18% | ~105 | 199 bytes |
| Pletter 5 | 51.52% | ~75 | medium |
| LZ4 | 58.55% | ~34 | medium |
| ZX7 | decent | moderate | 69 bytes |

Key insight: "Compression acts as a method to increase effective memory bandwidth" — LZ4 can decompress >2KB per frame on Z80.

Test corpus: Calgary/Canterbury datasets + 30 ZX graphics + 24 music files + mixed ZX data.

---

## 4. Ещё раз про DOWN_HL (introspec, 2020-12-30)

**URL:** /blog/dev/1047.html

Optimizing the DOWN_HL routine for moving screen address pointer down by one pixel row:

- Standard: ~5,922 cycles for full 192-line screen
- JP instead of JR: 5,616 cycles (5.2% improvement)
- Split counters: 2,343 cycles (60% improvement!)

RST7 contributed elegant solution with dual row counters. Main loop reduces to just `inc h`.

Recommendation: inline macros and unrolled loops, not subroutine calls.

---

## 5. Ещё раз про тайлы и RET (DenisGrachev, 2025-09-19)

**URL:** /blog/dev/1116.html

Optimized tile rendering for "Dice Legends" using RET-chaining:

Core technique: Set stack pointer to render list, each tile procedure ends with RET which pops next tile address. Replaces traditional jump chains.

Three render list strategies:
1. Map as render list
2. Address-based (copy segments)
3. Byte-based with 256-byte lookup tables (chosen)

Expanded playfield from 26×15 to 30×18 tiles.

---

## 6. Мультиколор будет побеждён (DenisGrachev, 2019-01-11)

**URL:** /blog/dev/768.html

Advanced multicolor rendering in ZX Spectrum games Old Tower and GLUF:

**LDPUSH technique:** `ld de, 2-byte-data : push de` generates executable code that outputs pixel data directly while serving as display buffer. Data written backwards due to stack pointer mechanics, 51 bytes per scanline.

**GLUF:** 8×2 multicolor, 24×16 char game area, double-buffered, 16×16 sprites/tiles, sound at 25Hz. Rendering exhausts ~70,000 cycles per frame.

Two-frame architecture: Frame 1 handles attributes + tile rendering. Frame 2 handles remaining tiles + sprite overlay.

---

## 7. Threads on Z80 (Robus, 2015-09-03)

**URL:** /blog/dev/271.html

Interrupt-driven threading system for Z80 (IM2 mode):

- SwitchThread procedure for context switching (saves/restores SP, memory page)
- Each thread gets dedicated 128-byte stack + memory page
- Used in WAYHACK demo: one thread calculates effects, another renders text
- "Honest multithreading rarely requires more than two threads"
- Supports both ZX Spectrum and TS-Config platforms

---

## 8. GO WEST, часть 1 & 2 (introspec, 2015-02/06)

**URLs:** /blog/dev/130.html, /blog/dev/230.html

Comprehensive ZX Spectrum hardware guide for Western models:

**Part 1 — Contended (slow) memory:**
- 48K: #4000-#7FFF slow during screen refresh
- 128K/+2: pages 1,3,5,7 slow
- +2A/+2B/+3: pages 4-7 slow; pages 0,2 always fast
- Penalty: ~0.92 extra cycles/byte random access, ~1.3 cycles/byte for stack operations
- Zero penalty during border periods

**Part 2 — Floating bus and port quirks:**
- Port #FF reads whatever's on the data bus (used for beam sync)
- #7FFD reading bug: reads write floating bus value into port
- ULA snow when I register points to #40-#7F
- Kempston joystick detection requires border timing

---

## 9. Ringo Render 64x48 (DenisGrachev, 2022-12-02)

**URL:** /blog/dev/1092.html

ZX Spectrum game achieving 64×48 resolution via two-screen multicolor:

- "11110000b" pattern: left pixels = ink, right = paper
- Screen switching every 4 scan lines
- Sprites: 12×10 pixels, 120 bytes, fixed-cycle macros
- Tile rendering with pre-generated code in memory pages using `pop af : or (hl)` patterns
- Horizontal scrolling with half-character displacement

---

## 10. Немного про чанки на ZX Spectrum (sq/Monster^Sage, 2022-07-16)

**URL:** /blog/demo/1084.html

4×4 chunky pixel rendering optimization:

- Basic LD/INC: 101 cycles/pair
- LDI variant: 104 cycles/pair
- LDD dual-byte: 80 cycles/pair
- **Self-modifying code:** Pre-generate rendering procedures with `LD (HL), *` immediates → 76-78 cycles/pair
- 256 procedure variants (~3KB) eliminate data-copying overhead

Based on work in BornDead #05.

---

## 11. Making of Lo-Fi Motion (restorer, 2020-09-27)

**URL:** /blog/demo/1023.html

ZX Spectrum demo for DiHalt 2020 using "lo-fi" attribute graphics ("Belarusian pixel"):

- Scene table system: bank, entry address, frame duration, parameters
- Most effects render to virtual 1-byte-per-pixel buffers (32 or 48 half-char rows)
- ~14 effects: raskolbas, slime/fire, interp, plasma, rain, dina, rtzoomer, rbars, bigpic
- Tools: sjasmplus, BGE 3.05, TRDetz, Photoshop, Ruby scripts, hrust1opt compression
- Source code on GitHub
- Built in 2 weeks of evening work

---

## 12. Making of GABBA (diver4d, 2019-11-08)

**URL:** /blog/demo/948.html

Synchronized gabber demo for CAFe'2019:

- Priority: tight audio-visual synchronization over traditional effects
- Innovation: Used Luma Fusion (iOS video editor) for 50fps timeline editing
- Eliminated constant recompilation for sync work
- Composer n1k-o created track with frame-level structural mapping

---

## 13. Бипер 20XX (Shiru, 2016-01-16)

**URL:** /blog/sound/350.html

~30 beeper engines cataloged (2010-2015):

- **ZX-16** (Jan Deak, 2014): 16-channel polyphony (!)
- **xtone** (utz, 2015): 6-channel wavetable
- **Octode variants**: 8-channel (original, XL, 2k15, PWM)
- **nanobeep/Huby**: Sub-100-byte engines for games
- Synthesis methods: PWM, PFM, phase interference, wavetable
- Tools: Beepola, 1tracker, XM/MIDI converters

---

## 14. Код мёртв (introspec, 2015-01-23)

"Code is dead" — parallel to Barthes' "Death of the Author." Code only lives when people read it in debuggers. Modern demos consumed as visual media. "Writing code purely for its own sake has lost relevance."

## 15. За дизайн (introspec, 2015-01-30)

Design = "complete aggregate of all demo components, both visible and concealed. Design characterizes realizational, stylistic, ideological integrity." A deliberately ugly demo can have excellent design.

## 16. MORE (introspec, 2015-02-06)

Challenges ZX scene to transcend platform limitations. "Two pixels suffice to tell a story." References James Houston's printer-music video. Demands "MORE" from creators.

---

## 17. VS Code + Z80MacroAsm Setup (sq, 2019-11-05)

**URL:** /blog/dev/946.html

- VS Code + Z80 Assembly extension (mborik) + zxboilerplate template
- Ctrl+Shift+B to compile → demo.sna + user.l
- Integration with Unreal Speccy (F3 to load)
- Recommended extensions: Z80 Debugger (ZEsarUX), Z80 Assembly Meter, ASM Code Lens

---

## 18. Секреты LPRINT (diver4d, 2015-11-16)

**URL:** /blog/demo/304.html

LPRINT trick: redirect BASIC printer output to screen memory via system variable 23681. Data reorders in "transposed" manner across 8 states. First appeared in pirated cassette loader, later used in "BBB by JtN/4D" (2011).

---

## 19. NHBF Making-of (UriS, 2025-10-01)

**URL:** /blog/dev/1120.html

256-byte intro "No Heart Beats Forever" for CC 2025. Inspired by "RED REDUX" (Multimatograf 2025). Looped square wave power chords + random pentatonic notes. Optimization = "playing puzzle-like games." Art-Top found register values from screen clear matched text length.
