# Introspec's ZX Spectrum demoscene wisdom: a source audit for *Coding the Impossible*

**Fourteen of eighteen targeted sources yielded substantial technical content**, ranging from complete Z80 assembly listings with T-state analysis to full NFO scene-by-scene breakdowns. Five older Hype articles (IDs 32–670) are not indexed by search engines and require direct browser access. This report catalogs every extracted technical detail, maps each source to book chapters, and flags the gaps that remain.

---

## Priority 1 articles delivered the deepest technical payload

### 1. "Ещё раз про DOWN_HL" — The Spectrum's most-called routine, dissected

Introspec opens with the assumption that readers already know DOWN_HL (the routine that advances a screen pointer one pixel line down through the Spectrum's infamously non-linear display memory). He then benchmarks three variants against a **baseline of 5,922 T-states** for a full 192-line screen traversal.

**Standard DOWN_HL** costs 27T per within-character-row step (168 steps), 59T for row crossings (21 steps), and 49T for screen-third crossings (3 steps). The "DOWN_HL+" variant collapses row and third crossings into a single 56T path, yielding **5,880T** — a **0.7% gain** Introspec calls "essentially pennies."

The real win comes from **DOWN_HL_c**, which caches the "correct" H value for the current screen third in register C:

```z80
DOWN_HL_c:
    inc h
    ld a,h
    and 7
    jr z,charedge
next: ...
charedge:
    ld a,l
    add 32
    ld l,a
    jr c,newthird
    ld h,c         ; restore from cache
    jr next
newthird:
    ld c,h         ; update cache
    jr next
```

The inner-step cost drops from **27T to 22T** — 5 T-states saved on every single pixel line. The article also discusses a table-based approach using SP to index lookup tables, trading ~1KB of RAM for roughly 3T per step savings. Introspec estimates a compact unrolled procedure could fit in ~4KB without significant short-path speed loss.

**Book relevance:** Part I (T-states, screen layout) and Part II (effect inner loops). The DOWN_HL_c variant with its 22T inner step is a foundational optimization that cascades through every pixel-pushing effect.

### 2. "Сжатие данных для современного кодинга под Z80" (2017) — 10 packers on the Pareto frontier

Introspec's core analytical insight: **don't measure compression ratio or decompression speed alone — map packers on a Pareto optimality frontier** of both dimensions. He tested 10 packers across 5 data categories (Calgary corpus, Canterbury corpus, ZX graphics, music, miscellaneous) totaling **1,233,995 bytes** of uncompressed data.

**Key benchmark results (total compressed bytes / ratio):**

| Packer | Total Bytes | Ratio | Decompression | Best For |
|--------|------------|-------|---------------|----------|
| **Exomizer** | **596,161** | **48.3%** | ~250 T/byte | Maximum compression |
| ApLib | 606,833 | 49.2% | ~110 T/byte | Good compression, moderate speed |
| PuCrunch | 616,855 | 50.0% | — | Complex LZ alternative |
| Hrust 1 | 613,602 | 49.7% | — | Relocatable stack depacker |
| **Pletter 5** | **635,797** | **51.5%** | **~69 T/byte** | Speed + decent compression |
| MegaLZ | 636,910 | 51.6% | ~130 T/byte (old) | Obsolete in 2017, revived 2019 |
| **ZX7** | **653,879** | **53.0%** | ~107 T/byte | **69-byte depacker** for mini-intros |
| LZ4 | 722,522 | 58.6% | Fastest | Raw decompression speed |

Only Exomizer broke the "magic 600,000-byte barrier." Introspec's practical recommendations are crisp: need max compression → Exomizer; need ≤110 T/byte → ApLib; need ≤75 T/byte → Pletter 5; care only about speed → LZ4; making 256b–1K intros → ZX7 (69-byte depacker). He declared MegaLZ and Hrum "morally obsolete" in 2017 — a judgment he would reverse two years later.

**Book relevance:** Part IV (size-coding, compression). The Pareto framework itself is a pedagogical gem.

### 3. "Компрессия на спектруме: MegaLZ" (2019) — Resurrection through better depackers

Introspec rewrote MegaLZ's depackers and **transformed it from obsolete to competitive**:

- **New compact depacker:** 92 bytes, ~98 T/byte (down from 110 bytes, much slower)
- **New fast depacker:** 234 bytes, **~63 T/byte** — faster than 3×LDIR, comparable to "the speed of some rotozoomers"

MegaLZ was historically notable as **the first Spectrum compressor with an optimal parser** (LVD, 2005). Its format resembles Hrum but uses Elias gamma codes instead of Rice codes and has a 500-byte-larger window, yielding ~0.6% better compression. With new depackers, MegaLZ "handily beats Pletter5 and ZX7," though LZSA2 remains ~30% faster in decompression. Introspec kept MegaLZ in his demo engine because it compresses his data "noticeably better."

**Book relevance:** Part IV. The lesson that format design and depacker implementation are separable problems — and that a "dead" format can be revived through better Z80 code — is a powerful teaching moment.

### 4. "Технический разбор Illusion от X-Trade" (2017)

**⚠️ Article not retrievable** (URL /blog/dev/670.html not indexed). However, substantial technical details were recovered from Pouet comments on the Illusion demo (Enlight'96, 1st place):

The **textured sphere** doesn't complete in one frame even with all code/data in fast RAM. Lordcoxis (who made a 128K/+3 fix in 2021) discovered that only half the sphere needs clearing each frame — top or bottom, depending on direction. The **rotozoomer** had its IM2 table located in slow RAM, causing issues on 128K models; the fix placed the IM2 table inside the actual bitmap, choosing a vector that "didn't look out of place." The **zooming scroller** skipped frames depending on music load and required zoom-factor limiting for 128K compatibility.

**Book relevance:** Part II (sphere, rotozoomer, tunnel are already in the book plan). The sphere half-clearing optimization and IM2-in-bitmap trick are directly usable.

### 5–6. "GO WEST" parts 1 & 2 — The definitive Pentagon-to-Sinclair porting guide

These two articles form the most comprehensive English-accessible documentation of **hardware differences between Russian Pentagon clones and original Western Spectrums**. Part 1 covers memory and ports; Part 2 covers floating bus, the "port #FF" myth, and the snow effect.

**Contended memory** is the central topic of Part 1. Introspec quantifies the penalty: during screen rendering (~35% of frame time), each byte access to slow memory costs an average of **2.625 extra T-states**. For double-byte stack operations writing to screen, expect ~1.3 extra T-states per copied byte. His "hygiene rules" are practical: place code in fast memory, prefer border-time rendering, schedule non-screen work during display.

The **fast/slow memory map** differs critically across models:

| Machine | Always Fast | Always Slow |
|---------|------------|-------------|
| 48K | #0000–#3FFF, #8000–#FFFF | #4000–#7FFF |
| 128K/+2 | Pages 0, 2, 4, 6 | Pages 1, 3, 5, 7 |
| +2A/+2B/+3 | Pages 0, 1, 2, 3 | Pages 4, 5, 6, 7 |

**Universal rule: pages 0 and 2 are always fast; pages 5 and 7 are always slow.**

Part 2 reveals that **"port #FF" does not exist** — it is floating bus behavior on non-existent ports, the #1 source of Russian software failing on Western machines. The classic Kempston detection bug occurs because port 31 (odd!) reads floating bus on machines without Kempston hardware; during screen rendering, a screen byte with cleared upper bits triggers a false positive. The fix: test after HALT during border time only.

The **snow effect** occurs when register I points to slow memory (#40–#7F) — the ULA misreads screen data through the refresh cycle. On 128K/+2 this can cause crashes. Fixed on +2A/+2B/+3. Never place IM2 vector tables in slow memory.

**Book relevance:** Part I (machine architecture) and Part V (modern workflows — understanding these differences is essential for testing on real hardware). The port decoding tables and contended memory maps belong in a reference appendix.

---

## Priority 2 philosophy articles are partially recovered

The four design/philosophy articles (IDs 32, 64, 87, 261) **could not be fetched** — the older Hype pages aren't indexed by search engines. However, Introspec's positions were reconstructed from Pouet discussions:

**"Код мёртв" (Code is Dead)** is a deliberate Nietzschean paraphrase. Introspec clarified on Pouet: "I wrote 'Code is dead'… by that I meant that even the best coders on the platform have no clue anymore." This is not anti-code but anti-complacency — a call for design-first thinking where **technical ambition serves artistic vision**, not the reverse.

**"Making of Eager"** reportedly contains ~30KB of technical writeup. Kylearan praised it specifically: "Big thanks for the nfo file alone, I love reading technical write-ups!" The demo features a **chaos zoomer** ("done in a way it was not done on Spectrum before"), all visuals at **50Hz with true digi-drums**. Introspec explicitly rejected accusations of "no code," noting the sweaty effort was hidden by design.

**"За дизайн" and "MORE"** articulate the philosophy that ZX Spectrum demos should be **art that happens to run on a Spectrum**, not merely demonstrations of what the Spectrum can do. These need direct browser retrieval.

**Book relevance:** Part I (mindset chapter) and any design philosophy sections. The "code is dead" essay would make an excellent epigraph or sidebar.

---

## Pouet productions revealed cross-pollinating innovations

### Rain by Life on Mars — 9-channel beeper alongside real-time visuals

This **16K demo** (Multimatograf 2016, 2nd place) runs a rain effect simultaneously with MISTER BEEP's 9-channel 1-bit beeper engine on a **48K rubber-key Spectrum**. Multiple commenters (moroz1999: "the best beeper demo so far"; evilpaul: "you don't even notice the limitations") confirmed the achievement's significance. The beeper engine consumes massive CPU, yet the rain effect persists. The file_id.diz contains Introspec's technical writeup on the rain effect, but **NFO content was not directly retrievable** from Pouet.

**Book relevance:** Part III (beeper, music-synced engines) and Part IV (16K size constraints).

### Break Space by Thesuper — 19 scenes with a full NFO technical breakdown

The NFO (posted by diver at bay6.retroscene.org) contains scene-by-scene credits and techniques for all 19 parts. Key technical highlights:

- **Weaves effect** (Introspec, 2+ weeks): inspired by David Whyte's beesandbombs GIFs, "slightly harder than it looks"
- **Magen Fractal** (psndcj): 122 frames × 6912 bytes packed into **10,512 bytes — 1.25% of original**
- **Venus de Milo scene** uses **X-Trade's 3D engine** for a lowpoly rotating model
- **Shattered logo**: the code routine that generated it was larger than the packed result, so the runtime routine was replaced by a static packed image
- **Mondrian**: 256 hand-drawn frames, every square cut separately, all packed into **3KB**

The demo was strongly influenced by **The Black Lotus and Ephidrena** demos. Introspec confirmed tape support with full ZX Spectrum 128K/+2/+2A/+3 compatibility.

**Book relevance:** Part II (effects), Part IV (compression in practice — the Magen Fractal and Mondrian packing are extreme examples), Part V (classic Spectrum compatibility).

### Ultraviolet by HOOY-PROGRAM — Introspec's optimization unlocked 22-column 8×1 multicolour

Gasman's one-man demo achieved the **first-ever 22-column 8×1 multicolour on an original Sinclair Spectrum 128**, combined with gigascreen interlacing for an effective **82-color palette**. The key technical chain:

1. **Introspec's idea**: with the 128K second screen, you only need to update **6 of the 8 raster lines live** (the other 2 are pre-rendered on the alternate screen)
2. **Screen-switching timing**: "hammer away on a single screen as long as possible, then switch screens just when you're about to run out of cycles"
3. **Data visualization**: Gasman built a spreadsheet showing exactly where contention delays occur, enabling **hand-optimized instruction ordering** to squeeze out the final columns

The gigascreen interlace yields 5 intensity levels per RGB component: 0%/25%/50%/75%/100% from combinations of off/dimmed/bright across two frames. The theoretical 125 colors reduce to **82 usable colors** due to bright/dim attribute constraints.

**Book relevance:** Part II (4-phase color / multicolour chapter). The data-visualization approach to contention optimization is a methodological insight for Part V (modern workflows).

---

## Additional Hype articles expand the book's source base significantly

### DenisGrachev's "Tiles and RET" (2025) — PUSH-based rendering for multicolor games

This article describes how tile rendering for the multicolor game **Dice Legends** was accelerated from a 26×15 to **30×18 playfield** using RET-chained dispatch:

```z80
ld sp,renderList
ret              ; chains through tile procedures
```

Each tile procedure is a self-contained block of `ld (hl),pixel : inc h` instructions that ends with `ret`, which pops the next tile's address from the render list. Register DE holds the two most common byte values (0 and 255) for speed. Three approaches to render-list generation are compared: map-as-renderlist (fastest, used in Gluf), address-copy via unrolled `pop/ld`, and byte-per-tile with lookup tables (chosen for ZakMcDruken). The lookup table approach patches two tiles simultaneously using stack operations.

**Book relevance:** Part I (screen layout tricks) and Part II (tile engines). The RET-chaining pattern is a fundamental Z80 idiom.

### DenisGrachev's NHBF making-of (2025) — 256 bytes of sizecoding craft

The **1st place CC2025 256-byte intro** reveals key sizecoding techniques: music from looped powerchords with random pentatonic on the third AY channel, all frequencies constrained to **1-byte dividers**. The "solo" melody literally plays ROM code from some address as note data. The text consists of ZX BASIC tokens forming meaningful sentences — DeepSeek AI generated the gem "I poke heart into code." Counter initialization is skipped because the first cycle with zeroed attributes is harmless. The Shura-Bura rule serves as desktop motto: "Any program can always be shortened by one instruction."

**Book relevance:** Part IV (256b–4K intros, every technique described). Part III (AY sound synthesis in minimal space).

### DenisGrachev's "Making of Hara Mamba" (2019) — Five effects with full Z80 listings

This CAFe 2019 entry provides **complete annotated Z80 source** for five effects:

- **Hidden rotator**: border animation using ink/paper layer separation, self-modifying raster bar code fitting exactly 224 T-states per line
- **Kpacku scroll**: attribute-based smooth scroll storing current cell color in ink and next cell's color in paper, with interlaced screen flipping using `jp (iy)` / `jp (hl)` tricks
- **Vasyliev scroll**: 8×2 multicolor with per-line bank switching via `out (c),d/e`, distortion through `ld sp,xxxxx` self-modification patching from sine-based templates
- **Realtime morphing cat**: 25fps 8×1 multicolor with delta-based distortion templates
- **Zatulinsky tunnel**: table-based tunnel with 8×4 lookup format, compositing two texels per inner loop

**Book relevance:** Part II (tunnel, multicolor effects) and Part III (music-synced timing). The 224 T-state-per-line constraint and self-modifying SP patching are recurring patterns.

### sq's "Chunky effects on ZX Spectrum" (2022) — Partial retrieval

Covers 4×4 halftone chunky pixels, the BornDead #05 implementation, interlacing strategies (draw even/odd lines on alternating frames), and bumpmapping. Historical context references **Shit 4 Brainz, Power Up, Refresh, Forever, Napalm, Dogma**. Full technical body not retrieved.

**Book relevance:** Part II (classic effects).

### sq's VS Code + Z80 setup guide (2019, 40 comments through 2026)

The definitive guide to modern ZX Spectrum development: VS Code + Z80 Macro-Assembler extension by mborik, with community-recommended additions: **Z80 Debugger** (maziac, communicates with ZEsarUX), **Z80 Assembly Meter** (Néstor Sancho, shows byte/cycle counts in status bar), **ASM Code Lens** (maziac, refactoring support). A companion article by Alex_Rider (2024) adds F5-to-Unreal-Speccy integration. No separate aGGreSSor 2026 article exists — aGGreSSor commented on sq's article in January 2026.

**Book relevance:** Part V (modern workflows). This is the primary source for the toolchain chapter.

---

## Source-to-chapter mapping at a glance

| Book Part | Key Sources Retrieved |
|-----------|----------------------|
| **I: Machine & Mindset** | DOWN_HL (timing), GO WEST 1+2 (contended memory, port decoding, fast/slow map), Код мёртв philosophy |
| **II: Classic Effects** | Illusion (partial — sphere, rotozoomer, tunnel), Hara Mamba (5 effects with code), Tiles & RET, Break Space NFO, chunky effects |
| **III: Sound Meets Screen** | Rain (beeper + visuals), NHBF (AY in 256b), Hara Mamba (music sync) |
| **IV: Size-Coding** | Compression 2017 (Pareto framework, 10 packers), MegaLZ 2019 (depacker resurrection), NHBF (256b craft), Magen Fractal (122 screens → 10KB) |
| **V: Modern Workflows** | VS Code guide (sq 2019), F5-to-Unreal (Alex_Rider 2024), Ultraviolet data-visualization for contention, GO WEST porting guides |

## Five sources require direct browser retrieval

The following articles exist on hype.retroscene.org but are not indexed by search engines or archived on the Wayback Machine. They must be accessed directly in a browser:

1. **"Технический разбор Illusion от X-Trade"** — /blog/dev/670.html — Critical for Part II
2. **"Making of Eager"** — /blog/demo/261.html — Contains ~30KB technical writeup with chaos zoomer details
3. **"Код мёртв"** — /blog/demo/32.html — Philosophy of code in demoscene
4. **"За дизайн"** — /blog/demo/64.html — Design-first manifesto
5. **"MORE"** — /blog/demo/87.html — Platform transcendence philosophy

Additionally, the **Rain file_id.diz** (containing Introspec's rain effect writeup) requires downloading the demo archive from files.scene.org and extracting the file_id.diz directly. The **Eager NFO** can be found in the final version archive at introspec.retroscene.org/demo/eager(finalver).zip.

## Conclusion

Introspec's body of work reveals a consistent methodology: **quantify everything in T-states, map tradeoffs on Pareto frontiers, then choose the design-optimal point rather than the technically maximal one**. His compression survey doesn't crown a single winner but teaches readers to think in tradeoff curves. His DOWN_HL analysis doesn't just present the fastest variant but shows exactly when each optimization matters. His "Code is dead" philosophy doesn't reject technical skill but insists it serve artistic vision.

The most technically dense sources — the compression benchmark, MegaLZ revival, GO WEST porting guides, and Hara Mamba making-of — are fully retrieved with code examples intact. The Ultraviolet discussion provides the rare case of a cross-group optimization (Introspec's second-screen idea enabling Gasman's 22-column achievement) that demonstrates how demoscene knowledge circulates. The newly discovered DenisGrachev articles and sq's VS Code guide expand the book's source base beyond Introspec alone, confirming that the Hype dev blog is the single richest repository of modern ZX Spectrum coding knowledge in any language.