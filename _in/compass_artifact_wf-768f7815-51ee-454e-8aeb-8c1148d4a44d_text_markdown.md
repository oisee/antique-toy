# Pushing pixels on the ZX Spectrum in 2026

The ZX Spectrum — a machine with **256×192 pixels, 15 colors, and no hardware sprites** — continues to produce stunning visuals that appear to defy its specifications. A thriving ecosystem of modern tools, demoscene techniques, and sizecoding wizardry sustains one of retrocomputing's most active creative communities. From pixel-perfect game art crafted in Multipaint and SevenuP to 256-byte intros that generate mesmerizing procedural visuals, the Spectrum's constraints have become a catalyst for ingenuity. This report maps the complete landscape: tools, techniques, mathematical foundations, key figures, and the award-winning productions that define the platform's creative frontier.

---

## The modern game graphics pipeline: from sketch to `.TAP`

Creating graphics for the ZX Spectrum in 2026 follows a pipeline that bridges modern desktop tooling with 1982-era hardware constraints. The core challenge remains the attribute system: each **8×8 pixel cell supports only two colors** (ink and paper), with a brightness bit shared per cell. This "color clash" defines the Spectrum's visual identity and every design decision.

**SevenuP** (by MetalBrain) remains the de facto standard sprite and tile editor. Written in C++ with wxWidgets, it runs cross-platform and handles the full sprite workflow: drawing with attribute constraints enforced, mask generation for transparent overlays, multi-frame animation (up to 32 frames), and export to binary or assembler source compatible with SjASMPlus, Pasmo, and z88dk. Jonathan Cauldwell, creator of the Arcade Game Designer framework, endorses it directly: "For graphics there's a tool called SevenUp which I use, and can thoroughly recommend."

**Multipaint** (by Dr. TerrorZ / Tero Heikkinen) is the artist-oriented alternative, a Java/Processing application supporting multiple retro platforms including ZX Spectrum with standard and ULAplus palettes. Its strength is real-time attribute clash emulation — artists see exactly how their work will render while painting. It supports dither patterns, definable brushes, mirror drawing, and 30-step undo. Actively maintained through 2025, it's popular among demoscene artists like Andy Green, Rail Slave, and Facet.

**Aseprite**, the professional pixel art tool, ships with a built-in ZX Spectrum palette (`zx-spectrum.gpl`) and supports Lua scripting. The community has created plugins like **ZX-flash-animation** (by AlRado on GitHub) for importing and exporting Spectrum `.scr` files. Many developers sketch in Aseprite, then refine in Spectrum-native editors. **ZX PearPixel** (by Rob Pearmain) is a newer entrant — a modern sprite editor and animator designed specifically for the Spectrum with a contemporary UI. **ZX-Paintbrush** (by Claus Jahn) handles multicolor modes and flash animation frames.

The conversion pipeline is equally rich. **Image Spectrumizer** (img2spec, by Jari Komppa) stands out as an artist-oriented converter with a modifier stack, supporting multiple dithering algorithms, false-color processing, and cell modes from 8×8 down to 8×1. It auto-reloads when source files change, enabling live preview while editing in an external program. **BMP2SCR Pro** by LCD handles batch conversion, while **ZX Image library** (by moroz1999) — the engine behind the zxart.ee website — supports over 20 Spectrum screen formats including gigascreen, multicolor, tricolor, and Timex modes.

Russian developer Sergey Yakimovich (ZXBITLES), who created games for the Yandex Retro Games Battle 2020, described a representative modern workflow: sprites drawn in **Paint.NET**, refined in **ZX Paintbrush**, compiled with **Boriel's ZX BASIC** compiler, built via batch scripts that concatenate loader, screen, and game data into a TAP file, then tested in the **Fuse** emulator before verification on real Soviet-era clone hardware via an RGB-to-VGA converter. Richard Shred (Coredump developer) uses a Linux pipeline with Multipaint for graphics, custom Java tools for data conversion, zasm for assembly, and ant for builds.

Complete game frameworks integrate the graphics pipeline directly. **MPAGD** (Multi-Platform Arcade Game Designer, by Jonathan Cauldwell) bundles block, sprite, and screen editors with a BASIC-inspired scripting language, requiring no assembly knowledge. **La Churrera / MTE MK1** (by The Mojon Twins) provides a full C-based framework using z88dk and splib2, with PNG-to-binary converters and compressed map tools — dozens of games including Ninjajar! and Sir Ababol were built with it.

---

## How attribute clash became a creative discipline

The techniques for managing color clash have evolved from crude workarounds into a sophisticated design vocabulary. The simplest approach — **monochrome gameplay** — powered classics like Knight Lore and Head Over Heels: all game elements rendered in one color with colorful status bars at screen edges. **Don Priestley's technique** used large, cartoon-like sprites deliberately designed to fill entire 8×8 character blocks, making the grid constraint invisible. Games like Manic Miner and Dizzy confined background elements to dedicated cells with sprites moving through clear areas.

Modern engines have dramatically expanded what's possible. **NIRVANA Engine** (by Einar Saukas) achieves **8×2 attribute resolution** — halving the vertical clash problem by rewriting attribute memory in sync with the raster beam. It covers 32 columns × 23 rows (nearly the full screen), supports 16×16 pixel tiles and up to 8 sprites, and works on all standard Spectrum models. Games like Yazzie (RetroSouls), El Stompo, and COMPLICA DX use NIRVANA as their display engine, delivering full-color gameplay that would have seemed impossible in 1985. **BIFROST*2 Engine** (also by Saukas) pushes further with true **8×1 multicolor** across 20 columns × 22 rows, though at higher CPU cost.

For smooth sprite movement within these engines, developers create four pre-shifted sprite frames per animation step. All four frames draw at the same position, then the sprite advances one character cell, creating pixel-smooth motion despite the tile-based underlying system.

---

## Racing the beam: demoscene techniques that transcend the hardware

The ZX Spectrum demoscene's most transformative technique is **multicolor** (sometimes called "rainbow graphics"). It exploits a crucial hardware detail: the ULA re-reads attribute data for every pixel row, not just once per 8-row character cell. By rewriting attribute memory in perfect synchronization with the raster beam, code can display different color pairs for blocks as small as 8×1 pixels — effectively **increasing color resolution by 8×**.

The technical challenge is extreme. The Z80 runs at 3.5 MHz with **224 T-states per scanline**. An 18-column multicolor 8×1 effect requires approximately 214 T-states per line, leaving almost no margin. The implementation uses pre-loaded registers (HL, DE, BC, plus the alternate set via EXX) rapidly PUSHed to the stack pointer aimed at attribute memory. Six of nine PUSH operations must fall within the uncontended 96 T-state border/retrace region, since the first three PUSHes land in contended memory where the ULA steals CPU cycles. As Simon Owen documented: "18-column rainbow effect is right at the very edge of what's possible on a 48K Spectrum, with no time to spare."

On Pentagon clones (the standard Russian demo platform), more aggressive stack-based code achieves multicolor up to **24 columns**. The theoretical maximum for full-screen 32-column multicolor requires constraint trade-offs — the **Con18 converter** limits attribute pair changes to 8 per line to make it achievable.

**GigaScreen** exploits the 128K model's shadow screen: alternating two different images at 50 Hz via a single OUT command blends them through persistence of vision on CRT displays, approximately doubling the palette to **~36 distinguishable colors**. Combining gigascreen with multicolor yields **MultiGigaScreen** — the most powerful standard Spectrum display mode, offering 64×48 blocks with 64 colors. **Stellar mode** adds bright/dark alternation for 4×4 pixel blocks. **Tricolor/RGB mode** flickers three monochrome layers to produce 8 per-pixel colors.

**Border effects** exploit the wide border surrounding the 256×192 display. By precisely timing OUT instructions to port 254, code changes the border color multiple times per scanline, creating raster bars, low-resolution graphics, or overscan illusions. Andrew Owen's **BorderTrix** (2012) achieved 6 colors per border scanline.

The **floating bus trick** provides raster-position detection without cycle counting. Reading an unattached I/O port returns whatever data the ULA is currently fetching from video memory, allowing code to determine beam position by comparing read values against known attribute patterns. Ast A. Moore's "Definitive Programmer's Guide to Using the Floating Bus Trick" (2018–2019) documented this technique comprehensively, including the first game to use it on +2A/+3 models.

**Memory contention** — normally a nuisance where the ULA steals CPU cycles during active display — becomes a synchronization tool. The ZXodus Engine uses contention's predictable delays as a timing mechanism, enabling it to function across different Spectrum models. **ULA snow** (random byte display caused by interrupt vector table conflicts with video memory) has even been deliberately exploited as a visual effect.

---

## Sizecoding: entire worlds in 256 bytes

ZX Spectrum sizecoding — creating complete visual productions in 256, 512, 1024, or 4096 bytes — is among the demoscene's most demanding disciplines. The key insight enabling 256-byte intros is architectural: **animate the 768-byte attribute RAM instead of the 6144-byte pixel bitmap**. The attribute area is linearly organized (unlike the notoriously interleaved pixel memory), only 768 bytes must be written per frame, and color changes are visually striking at the 32×24 character grid resolution.

The core strategy for a 256-byte intro follows a tight template:

- **Static pixel pattern** (~15–20 bytes): fill pixel memory with a repeating tile, such as `LD A,$55` for a checkerboard
- **Color ramp data** (~8–32 bytes): a custom color lookup table aligned to a 256-byte boundary for single-register indexing
- **Mathematical effect** (~80–150 bytes): a formula computed over the 32×24 grid, mapped to color indices in attribute RAM
- **Animation** (~10–20 bytes): a frame counter in a register applied to the formula
- **Optional sound** (~10–20 bytes): AY register writes or beeper toggles

A critical size-saving technique is the **45-degree coordinate tilt**: combining X+Y and X−Y makes simple AND/XOR patterns produce visually complex interference effects. The ROM's built-in floating-point calculator (accessed via `RST $28`) can generate sine tables — expensive in cycles but saving precious code bytes. Galois LFSR pseudo-random generators fit in 6–8 bytes. Self-modifying code eliminates branch overhead. Startup register values (BC = start address, IY = $5C3A) are exploited rather than initialized.

**Superogue's development blog for "Fluxus"** (1st place, Flash Party 2020) provides a rare detailed walkthrough: starting from x86 sizecoding experience, converting techniques to Z80 over 10 days, building custom color ramp tools, and implementing attribute-based plasma with ROM calculator sine tables. **Gasman's Spectrum Sizecoding Seminar** (Lovebyte 2021, source on GitHub) documents techniques from ROM exploitation to number encoding for the floating-point calculator.

For 4K intros, the strategy shifts to **compression**. **ZX0** (by Einar Saukas) provides optimal LZ77/LZSS compression with a tiny ~70-byte Z80 decompressor, enabling 4096 compressed bytes to decompress to 15–30KB of code and data. **SerzhSoft's Megademica 4K** (1st place, Revision 2019 Oldskool Intro) exploited this to fit what reviewers called "a new-school demo that is actually a 4K intro" — an extraordinary number of tunnel and LUT-based effects with full AY music and rapid transitions. It was nominated for two Meteoriks awards (Best Low-End Production and Outstanding Technical Achievement). The newer **ZX2** compressor (also by Saukas) was used in **RED REDUX** (2025), one of the first 256-byte intros to include Protracker music.

---

## Procedural graphics: the math behind 3.5 MHz visuals

Every procedural effect on the Z80 rests on **fixed-point arithmetic** (typically 8.8 format: upper byte integer, lower byte fractional) and **pre-computed lookup tables**. The Z80 lacks hardware multiply, floating point, and division — all must be synthesized in software.

**Plasma effects** sum multiple sine waves indexed by screen position and time: `color = sin(x×freq1+t) + sin(y×freq2+t) + sin((x+y)×freq3+t)`. J.B. Langston's well-documented Z80 implementation uses a two-phase approach: pre-calculate a base image from 8 summed sine waves, then per-frame add only a per-row distortion (two sine lookups) — far cheaper than full recalculation. A 256-byte sine table aligned to a page boundary allows indexing with just the L register. At 10 MHz the effect runs at 60 fps; at the Spectrum's 3.5 MHz, artistic compromises (lower resolution, fewer waves) maintain interactivity.

**Fire effects** use a cellular automaton: each pixel averages its neighbors below and decays slightly, creating upward heat dissipation. Division by 4 is two right shifts (trivial on Z80). The bottom row is seeded with random values. On the Spectrum, implementations often work at attribute-cell resolution since the 8×8 color grid naturally produces chunky, flame-like patterns.

**Tunnel effects** pre-compute two lookup tables (angle and distance from center for each screen pixel) once at startup. Per-frame, time-varying offsets are added to these tables to create the scrolling illusion — reducing per-pixel cost to two table lookups plus addition. **Roto-zoomers** exploit incremental calculation: rather than computing trigonometric rotations per pixel, the inner loop simply adds constant deltas (du_per_pixel = cos(angle), dv_per_pixel = sin(angle)) to texture coordinates, replacing per-pixel multiplies with additions.

**Mandelbrot/Julia set** rendering on Z80 is a multiplication benchmark. Each iteration requires two 16×16-bit multiplications (z²_real, z²_imag) plus a cross-product. The RC2014 community optimized Z80 Mandelbrot rendering from 4'58" to 3'48" by replacing shift-and-add multiplication with **square-table multiplication** (using the identity a×b = ((a+b)²−(a−b)²)/4 with a 512-byte lookup table). A Z180's hardware multiplier further reduced this to 1'01".

**3D wireframe** and **raycasting** push the Z80 hardest. Wireframes use pre-calculated rotation with sine table lookups and Bresenham line drawing. Raycasting (Wolfenstein 3D-style) requires DDA stepping through a grid with reciprocal lookup tables for perspective division — Alone Coder achieved the first full-screen DOOM-like effect on a 48K Spectrum, winning Forever 2010.

The universal optimization principles across all effects: **256-byte aligned tables** for single-register indexing, **shadow register sets** (EXX) to double working registers without memory access, **self-modifying code** to inline per-frame constants into instructions, **loop unrolling** with code generation at startup, and aggressive **symmetry exploitation** (Mandelbrot mirroring, quarter-sine tables reconstructed at runtime).

---

## The Russian ZX scene and its prolific documentarians

The Russian ZX Spectrum community — built around Pentagon and Scorpion clones that outlived the original platform by decades — produced the scene's most prolific technical writers and some of its most innovative productions.

**Alone Coder** (Dmitry Bystrov, Ryazan) stands as the most prolific documenter, publishing **76 issues of ACNews** (1997–2023), **13 issues of Info Guide** (technical reference with programming articles), and the **"Этюды по программированию" (Programming Études)** series covering Z80 assembly tricks from conditional addition to TurboSound FM detection. He created NedoOS (a ZX Spectrum operating system), ported Wolfenstein 3D to the Spectrum, built a ZX Spectrum emulator running on a ZX Spectrum, and is extensively quoted in the academic monograph "ZX Spectrum Demoscene" (Cambridge University Press, 2022). His personal archive at alonecoder.nedopc.com hosts decades of demos, source code, and documentation.

**Vyacheslav Mednonogov** (scene handle: Copper Feet, born 1970, Saint Petersburg) is a legendary figure primarily as a game developer rather than demoscener. His НЛО: Враг Неизвестен (1995) was an X-COM clone for the Spectrum; Чёрный Ворон (1997) was a real-time strategy game inspired by Warcraft. Source code for both was later published on Open Source ZX. His documented output includes an audio interview from Chaos Constructions 2000 (transcribed in Adventurer #12 on zxpress.ru) and a long-form interview on RussianGames.me discussing his progression from calculator games to Spectrum development.

**4th Dimension** (Perm, Russia) anchored around artist **Diver** (Aleksey Golubtsov, with 133+ credited productions on Demozoo) and coder **PSNDCJ**, produced landmark demos including **Melange** (1st place CC2000 Invitation) and, as part of the **Stardust** supergroup, **Elysium State** (1st place CAFe 2022). Their collaboration with **Triebkraft** yielded **Aeon** (2008) and the legendary **WeeD** (2003), considered among the greatest ZX Spectrum demos ever made.

**Introspec** (also known as spke), originally Russian but now UK-based, is a respected coder and designer with 22+ productions including **BB** (a generative portrait in 256 bytes, 1st at Multimatograf 2014) and collaborative works with 4th Dimension and Triebkraft. His compression tool **Apultra** (2020, with Emmanuel Marty) serves the broader demoscene.

The richest repositories for Russian ZX technical writing are **zxpress.ru** (massive archive of electronic magazines, programming books, and ZXNet archives), **speccy.info** (SpeccyWiki, with detailed technical articles on multicolor and hardware), **zxart.ee** (comprehensive production database with online emulation), and the **hype.retroscene.org** Graphics FAQ covering everything from attribute clash strategies to sRGB color space considerations for accurate palette reproduction on modern displays.

---

## Award-winning productions that define the platform

The ZX Spectrum demoscene remains remarkably active through 2024–2026, with regular competitions at Chaos Constructions (Saint Petersburg), Forever (Slovakia), DiHalt (Russia), CAFe (Kazan), Revision (Germany), Multimatograf (online), and Lovebyte (online sizecoding).

Among full demos, **Across The Edge** by deMarche (1st place CC2016, Meteoriks 2017 nominee) is widely considered one of the greatest ZX Spectrum demos ever — a Pentagon production with stunning gigascreen, border effects, raster manipulation, and multicolor techniques. **WeeD** by Triebkraft & 4th Dimension (CC2003) defined creative storytelling with wireframe graphics and hidden-line removal. **GembaBoys** (Czech/Slovak "anti-elite alliance") dominated the Forever party from 2013 to 2019, winning three consecutive years (2013–2016) with collaborative megademos. **HOOY-PROGRAM** (Poland), led by Yerzmyey and Gasman, won repeatedly at Forever from 2009 to 2014 and achieved crossover success at Assembly 2003 — one of the only ZX Spectrum demos shown at a major Western party. In 2024, **crossplatform incident** by sibkrew topped CC2024's Oldskool Demo competition, while **Kebugaruha** by CI5 The Amaters & MB Maniax won Forever 2024.

In sizecoding, **Megademica 4K** by SerzhSoft & Gasman (1st at Revision 2019) set the benchmark — packing a full new-school demo's worth of tunnel effects, transitions, and AY music into 4096 bytes. At the 256-byte level, **BB** by Introspec (Multimatograf 2014) generated a recognizable portrait using only a 24-bit Galois LFSR and 64 iterations of random point plotting. **Fluxus** by superogue (Flash Party 2020) demonstrated attribute-based plasma with pattern overlays and ROM-calculated sine tables. **RED REDUX** by Virtual Vision Group (Multimatograf 2025) achieved the remarkable feat of including Protracker music in 256 bytes using ZX2 compression. At CC2024, **daybyday** and **Tooticki häst** by UriS swept the 256-byte category. At DiHalt 2023, **RMDA** (Russian Massive Digital Aggression) took first with **eye**.

Recent 1K entries include **RTZX** by RCL/Virtual Vision Group (1st at CC2024 1KB Procedural Graphics), **forever 2024 1k match** by Dizzy128 (1st at Forever 2024), and **8volution** variants by SinDiKat/GembaBoys across multiple parties. The 2024–2025 season also saw enhanced-platform demos like **Deeper** by Kapitány (Forever 2024) for ZX Enhanced and **PF2026** by Lanex for the eLeMeNt ZX computer.

---

## Essential resources and communities

The ZX Spectrum graphics and demoscene ecosystem is supported by a constellation of specialized sites and tools. For production archives: **Demozoo** (demozoo.org) catalogs all productions with credits and party results; **Pouët** (pouet.net) provides community ratings and discussion; **ZX-Art** (zxart.ee) offers a comprehensive database with online emulation; **zxaaa.net** archives 8000+ ZX demos; and **Demotopia** (zxdemo.org, maintained by Gasman) covers ZX-specific news.

For technical learning: **sizecoding.org/wiki/ZX_Spectrum** documents development setup, startup registers, graphics system, ROM routines, and links to annotated source code. **Gasman's Spectrum Sizecoding Seminar** (github.com/gasman/spectrum-sizecoding) provides hands-on materials from Lovebyte 2021. **ChibiAkumas** (chibiakumas.com/z80/) offers cross-platform Z80 tutorials. **Cemetech's Z80 Advanced Math** pages cover fixed-point arithmetic, multiplication, and trigonometry. **Grauw's MSX resource** (map.grauw.nl) provides exhaustive Z80 multiply/divide optimization techniques.

For Russian-language resources: **zxpress.ru** hosts the largest collection of ZX electronic magazines and programming books. **speccy.info** (SpeccyWiki) provides detailed technical wiki content. **zx-pk.ru** runs active forums on demos, hardware, and software. **hype.retroscene.org** publishes the comprehensive Graphics FAQ. Alone Coder's personal site (alonecoder.nedopc.com/zx/) archives decades of source code and publications.

For tools with source code: **ZX0/ZX2 compressors** (github.com/einar-saukas/ZX0) are essential for 4K intros. **Image Spectrumizer** (github.com/jarikomppa/img2spec) provides artist-oriented image conversion. **ZX Image library** (github.com/moroz1999/zx-image) supports 20+ screen formats. **Bazematic** (bazematic.demozoo.org) offers online development for Spectrum intros. Multiple complete demo source codes are available on GitHub, including BrainWaves 256b (github.com/tslanina/Retro-ZXSpectrum-BrainWaves) and Malady 4K (github.com/Megus/malady4k).

## Conclusion

The ZX Spectrum's creative community in 2026 operates at a paradoxical intersection: using modern desktop tools, cross-compilers, and mathematical optimization techniques to target hardware designed in 1982. The attribute system that once seemed like a crippling limitation has become a generative constraint — multicolor engines rewrite attribute memory 192 times per frame to achieve 8× the intended color resolution, sizecoding artists transform 768 bytes of color data into mesmerizing procedural animations, and game developers use NIRVANA/BIFROST engines to deliver full-color gameplay that would have stunned the machine's designers.

The scene's geographic center of gravity remains Eastern Europe and Russia, where Pentagon clones created a parallel computing culture that sustained the platform decades past its commercial lifespan. The prolific documentation by figures like Alone Coder, the tooling contributions of Einar Saukas (BIFROST, NIRVANA, ZX0/ZX2), and the continuing competition circuit from Chaos Constructions to Forever ensure that the ZX Spectrum remains not a museum piece but an active creative platform — one where the distance between mathematical ingenuity and visual art has never been smaller.