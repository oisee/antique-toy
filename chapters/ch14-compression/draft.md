# Chapter 14: Compression --- More Data in Less Space

The ZX Spectrum 128K has 128 kilobytes of RAM. That sounds generous until you start subtracting: the screen takes 6,912 bytes (6,144 pixels + 768 attributes), the system variables claim their share, the AY music player and its pattern data want a bank or two, your code occupies another few thousand bytes, and the stack needs room to breathe. By the time you sit down to store the actual content of your demo --- the graphics, the animation frames, the precalculated lookup tables --- you are fighting for every byte.

A single full-screen image on the Spectrum is 6,912 bytes. A 4K intro can fit roughly 0.6 of one. A 48K demo could theoretically hold seven screens with nothing else. But demos are not slideshows. They have music. They have code. They have effects that demand tables of precalculated data. The question is not whether to compress --- it is which compressor to use, and when.

This chapter is built around a benchmark. In 2017, Introspec (spke, Life on Mars) published "Data Compression for Modern Z80 Coding" on Hype --- a meticulous comparison of ten compression tools tested against a carefully designed corpus. That article, with its 22,000 views and hundreds of comments, became the reference that ZX coders consult when choosing a compressor. We will walk through his results, understand the tradeoffs, and learn to pick the right tool for each job.

---

## The Memory Problem

Let us be concrete about the constraints. Consider Break Space by Thesuper (Chaos Constructions 2016, 2nd place) --- a demo with 19 scenes running on a ZX Spectrum 128K. One of those scenes, the Magen Fractal by psndcj, displays 122 frames of animation. Each frame is a full 6,912-byte screen. Uncompressed, that is 843,264 bytes --- over six times the machine's total RAM.

psndcj compressed all 122 frames into 10,512 bytes. That is 1.25% of the original size. The entire animation, every frame of it, fits in less space than two uncompressed screens.

Another scene in Break Space, the Mondrian animation, packs 256 hand-drawn frames --- every square cut separately, individually compressed --- into 3 kilobytes.

These are not theoretical exercises. They are production techniques from a demo that competed at one of the scene's most prestigious parties. Compression is not an optimisation you apply at the end. It is a fundamental architectural decision that determines what your demo can contain.

### Compression as bandwidth amplifier

Introspec articulated the insight that elevates compression from a storage trick to a performance technique: **compression acts as a method to increase effective memory bandwidth**.

Consider a demo effect that needs 2 kilobytes of data per frame --- lookup tables, precalculated coordinates, animation data. At 3.5 MHz, the Z80 can read roughly 69,888 bytes per frame if it did nothing but `ld a, (hl) : inc hl` in a tight loop (each iteration: 11 T-states, 69,888 / 11 = 6,353 bytes, so the real throughput is lower). But you are not doing nothing else --- you are running an effect, playing music, handling the demo engine. Your actual data bandwidth is a fraction of the theoretical maximum.

Now suppose you store that 2 KB of data compressed to 800 bytes with a fast decompressor. You read 800 bytes from memory and decompress them into 2,048 bytes in a buffer. If the decompressor runs at 34 cycles per output byte (as LZ4 does), decompressing 2,048 bytes costs 69,632 T-states --- almost exactly one frame. But you can overlap decompression with other work. You can decompress during the border period while the ULA is not contending for the bus. You can decompress a frame ahead and double-buffer.

The result: you are effectively piping more data through the system than the bus could deliver if you were reading it raw. The decompressor is a data amplifier. On a machine where every memory access costs precious T-states, that amplification can be the difference between an effect that fits in one frame and one that takes three.

---

## The Benchmark

Introspec did not simply run each compressor on a few files and eyeball the results. He designed a corpus and measured systematically.

### The corpus

The test data totalled 1,233,995 bytes across five categories:

- **Calgary corpus** --- the standard academic compression benchmark (text, binary, mixed)
- **Canterbury corpus** --- a more modern academic standard
- **30 ZX Spectrum graphics** --- loading screens, multicolour images, game screens
- **24 music files** --- PT3 patterns, AY register dumps, sample data
- **Miscellaneous ZX data** --- tilemaps, lookup tables, mixed demo data

This mix matters. A compressor that excels on English text may struggle with ZX graphics, where long runs of zeros in the pixel area alternate with near-random attribute data. Testing on real Spectrum data --- the data you will actually compress --- is essential.

### The results

Ten tools. Measured on total compressed size (lower is better), decompression speed in T-states per output byte (lower is faster), and decompressor code size in bytes (smaller is better for size-coded productions).

| Tool | Compressed (bytes) | Ratio | Speed (T/byte) | Decompressor Size | Notes |
|------|-------------------|-------|-----------------|-------------------|-------|
| **Exomizer** | 596,161 | 48.3% | ~250 | ~170 bytes | Best compression ratio |
| **ApLib** | 606,833 | 49.2% | ~105 | 199 bytes | Good balance |
| PuCrunch | 616,855 | 50.0% | --- | --- | Complex LZ alternative |
| Hrust 1 | 613,602 | 49.7% | --- | --- | Relocatable stack depacker |
| **Pletter 5** | 635,797 | 51.5% | ~69 | ~120 bytes | Fast + decent compression |
| MegaLZ | 636,910 | 51.6% | ~130 | ~110 bytes | Revived by Introspec in 2019 |
| **ZX7** | 653,879 | 53.0% | ~107 | **69 bytes** | Tiny decompressor |
| **ZX0** | --- | ~52% | ~100 | **~70 bytes** | Successor to ZX7 |
| **LZ4** | 722,522 | 58.6% | **~34** | ~100 bytes | Fastest decompression |
| Hrum | --- | ~52% | --- | --- | Declared obsolete |

Only Exomizer broke the 600,000-byte barrier across the full corpus. But Exomizer's decompression speed --- roughly 250 T-states per output byte --- makes it impractical for anything that needs to decompress during playback.

### The tradeoff triangle

Every compressor makes a tradeoff between three qualities:

1. **Compression ratio** --- how small the compressed data gets
2. **Decompression speed** --- how many T-states per output byte
3. **Decompressor code size** --- how many bytes the decompression routine occupies

You cannot have all three. Exomizer wins on ratio but is slow to decompress and has a large decompressor. LZ4 is the fastest to decompress but wastes 10 percentage points of compression ratio. ZX7 has a 69-byte decompressor but compresses less aggressively than Exomizer.

Introspec's genius was to map these tradeoffs on a Pareto frontier --- a curve where no tool can improve on one dimension without losing on another. If a compressor is dominated on all three axes by another tool, it is obsolete. If it sits on the frontier, it is the right choice for some use case.

His practical recommendations are crisp:

- **Maximum compression, speed irrelevant:** Exomizer. Use for one-time decompression at load time --- loading screens, level data, anything you unpack once into a buffer and use repeatedly.
- **Good compression, moderate speed (~105 T/byte):** ApLib. A solid general-purpose choice when you need decent ratio and can afford ~105 cycles per byte.
- **Fast decompression (~69 T/byte):** Pletter 5. When you need to decompress during gameplay or between scenes and cannot afford Exomizer's sluggish unpacking.
- **Fastest decompression (~34 T/byte):** LZ4. The only choice for real-time streaming --- decompressing data as you play it back. At 34 cycles per output byte, LZ4 can decompress over 2,000 bytes per frame. That is a 2 KB/frame data pipe.
- **Smallest decompressor (69--70 bytes):** ZX7 or ZX0. When the decompressor itself must be tiny --- in 256-byte, 512-byte, or 1K intros where every byte of code counts.

Let these numbers guide your decisions. There is no universally "best" compressor. There is only the best compressor for your specific constraints.

---

## How LZ Compression Works

All of the compressors in the table above belong to the Lempel-Ziv family. Understanding the core idea helps you predict which data compresses well and which does not.

LZ compression replaces repeated byte sequences with back-references. A match says: "copy N bytes from position P bytes back in the already-decoded stream." The compressed stream alternates between **literals** (raw bytes with no useful match) and **matches** (offset + length pairs that reference earlier output).

The differences between compressors come down to encoding: how many bits for the offset, how many for the length, how to signal literal vs match. Exomizer uses sophisticated variable-length bit-level codes that compress tightly but require careful bit-extraction to decode --- hence the ~250 T-states per byte. LZ4 uses byte-aligned tokens that the Z80 processes with simple shifts and masks --- hence ~34 T-states per byte at the cost of 10 percentage points of ratio. ZX0 uses single-bit flags (0 = literal, 1 = match) with Elias interlaced codes for lengths, hitting a sweet spot between size and speed.

ZX Spectrum data compresses well because it has structure: large areas of identical bytes (black backgrounds, blank attributes), repeated patterns (tiles, fonts, UI), and correlated pixel data at regular offsets. Music compresses well too --- PT3 patterns are full of repeated note sequences and empty rows. What compresses poorly: random data, already-compressed data, and very short files where encoding overhead exceeds savings.

---

## ZX0 --- The Size Coder's Choice

ZX0, created by Einar Saukas, is the spiritual successor to ZX7 and has become the default compressor for modern ZX Spectrum development. It deserves special attention.

### Why ZX0 exists

ZX7 was already remarkable: a 69-byte decompressor that achieved respectable compression ratios. But Saukas saw room for improvement. ZX0 uses an optimal parsing algorithm --- it does not just find good matches, it finds the *best possible sequence* of matches and literals for the entire file. The result is compression ratios close to much larger compressors, with a decompressor that stays in the 70-byte range.

### The decompressor

The Z80 decompressor for ZX0 is hand-optimised assembly, designed specifically for the Z80's instruction set. It exploits the Z80's flag register, its block transfer instructions, and the exact timing of conditional jumps to squeeze maximum functionality into minimum bytes. Here is the kind of code we are talking about:

```z80
; ZX0 decompressor — standard version
; HL = source (compressed data)
; DE = destination (output buffer)
; Uses: AF, BC, DE, HL
dzx0_standard:
        ld      bc, $ffff       ; initial offset = -1
        push    bc
        inc     bc              ; BC = 0 (literal length counter)
        ld      a, $80          ; bit buffer: only flag bit set
dzx0s_literals:
        call    dzx0s_elias     ; read literal length
        ldir                    ; copy literals
        add     a, a            ; read flag bit
        jr      c, dzx0s_new_offset
        call    dzx0s_elias     ; read match length
        ex      (sp), hl        ; retrieve offset from stack
        push    hl              ; put it back
        add     hl, de          ; calculate match address
        ldir                    ; copy match
        add     a, a            ; read flag bit
        jr      nc, dzx0s_literals
dzx0s_new_offset:
        ; ... offset decoding continues ...
```

Every instruction pulls double duty. The accumulator serves as both a bit buffer and a working register. The stack holds the last-used offset for repeated matches. The LDIR instruction handles both literal copying and match copying, keeping the code small.

At roughly 70 bytes, the entire decompressor fits in less space than a single ZX Spectrum character row. For a 256-byte intro, that leaves 186 bytes for everything else --- the effect, the animation, the music. For a 4K intro, 70 bytes is negligible overhead. This is why ZX0 has become ubiquitous.

### When to use ZX0

- **256-byte to 1K intros:** The tiny decompressor is essential. Every byte saved on the decompressor is a byte available for content.
- **4K intros:** ZX0 can decompress 4,096 bytes into 15--30 KB of code and data. SerzhSoft's Megademica (1st place, Revision 2019) used this exact strategy to fit what reviewers called "a full new-school demo" into a 4K intro.
- **General demo and game development:** When you need a solid all-around compressor with a small footprint. ZX0 is not the fastest decompressor, but it is fast enough for one-time decompression at load time, and its ratio is competitive with tools that have much larger decompressors.
- **RED REDUX** (2025) used the newer ZX2 variant (also by Saukas) to achieve the remarkable feat of including Protracker music in a 256-byte intro.

ZX0 is not the right choice for real-time streaming (use LZ4) or for maximum compression at any cost (use Exomizer). But for the vast majority of ZX Spectrum projects, it is the correct default.

---

## RLE and Delta Coding

Not everything needs a full LZ compressor. Two simpler techniques handle specific data types more effectively.

### RLE: Run-Length Encoding

The simplest compression scheme: replace a run of identical bytes with a count and a value. "Seventeen zeros" becomes two bytes instead of seventeen.

```
Uncompressed: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
RLE encoded:  11 00   (17 repetitions of $00)
```

The decompressor is trivial --- a few dozen bytes of Z80 code:

```z80
; Minimal RLE decompressor
; HL = source, DE = destination
rle_decompress:
        ld      a, (hl)         ; read count
        inc     hl
        or      a
        ret     z               ; count = 0 means end of stream
        ld      b, a            ; B = count
        ld      a, (hl)         ; read value
        inc     hl
.fill:  ld      (de), a         ; write value
        inc     de
        djnz    .fill           ; repeat count times
        jr      rle_decompress  ; next run
```

RLE compresses beautifully when data contains long runs --- blank screens, solid-colour backgrounds, attribute fills with repeated values. It compresses terribly when data has few runs --- photographic images, random data, complex pixel art.

**When to use RLE:** Loading screens with large uniform areas. Attribute-only animations where most of the screen stays one colour. Initial screen clears. Simple tilemap backgrounds. Any data where you *know* runs will dominate.

The advantage over LZ is simplicity: the decompressor is smaller (under 30 bytes is achievable), faster per byte for run data, and trivial to debug. For size-coded intros where even ZX0's 70 bytes feel expensive, a custom RLE scheme can free precious space.

### Delta coding: store what changed

Delta coding stores the difference between consecutive values rather than absolute values. For animation frames that change incrementally, this can be devastating effective.

Consider two consecutive frames of an animation where 90% of the screen is identical. Frame 2 differs from Frame 1 in only 691 bytes scattered across the screen. Rather than storing the full 6,912-byte Frame 2, store a delta: a list of (position, new_value) pairs for the 691 changed bytes. If each pair costs 3 bytes (2 for position, 1 for value), the delta is 2,073 bytes --- 70% smaller than the full frame.

Delta coding combines naturally with other compressors:

1. **Delta + RLE:** If the changes cluster spatially (as they often do in animations), the position differences between consecutive changes form runs, which RLE compresses further.
2. **Delta + LZ:** Apply delta coding to produce the difference stream, then compress the result with ZX0 or another LZ compressor. The difference stream has more structure (more zeros, more repeated small values) than the raw frame, so LZ compresses it better.

The Break Space Magen Fractal is an example of this principle in action. Those 122 frames at 6,912 bytes each, compressed to 10,512 bytes total, relied on exploiting the inter-frame redundancy. Each frame differs from the previous by a small amount. The compressor (or the data preparation pipeline) exploits this.

**When to use delta coding:** Multi-frame animations. Sprite animations where the figure changes pose but the background stays fixed. Tilemaps that scroll smoothly (each new frame differs from the previous by one column or row). Music pattern data where consecutive rows share most values.

---

## The Practical Pipeline

Understanding compression algorithms is useful. Integrating them into your build pipeline is essential.

### From asset to binary

The pipeline: source asset (PNG) --> converter (png2scr) --> compressor (zx0) --> assembler (SjASMPlus) --> .tap file. The compressor runs on your development machine, not the Spectrum. For ZX0: `zx0 screen.scr screen.zx0`. Include the result with SjASMPlus's INCBIN directive:

```z80
compressed_screen:
    incbin "assets/screen.zx0"
```

At runtime, decompress with a simple call:

```z80
    ld   hl, compressed_screen    ; source: compressed data
    ld   de, $4000                ; destination: screen memory
    call dzx0_standard            ; decompress
```

### Makefile integration

The compression step belongs in your Makefile, not in your head. Every time you rebuild, every asset should be automatically recompressed:

```makefile
# Compress assets as part of the build
ASSETS_RAW = assets/screen.scr assets/level1.bin assets/music.pt3
ASSETS_ZX0 = $(ASSETS_RAW:.scr=.zx0) $(ASSETS_RAW:.bin=.zx0) $(ASSETS_RAW:.pt3=.zx0)

%.zx0: %.scr
	zx0 $< $@

%.zx0: %.bin
	zx0 $< $@

%.zx0: %.pt3
	zx0 $< $@

demo.tap: main.asm $(ASSETS_ZX0)
	sjasmplus main.asm --raw=demo.bin
	bin2tap demo.bin demo.tap
```

Now `make` will recompress any asset whose source has changed, rebuild the assembly, and produce a fresh .tap file. No manual steps. No forgotten recompression. This is how professional demo and game development works on the Spectrum in 2026.

### Example: loading screen with ZX0

Here is a complete, minimal example. A demo loads a compressed loading screen, decompresses it to video memory, and waits for a keypress.

```z80
; loading_screen.asm
; Assemble with: sjasmplus loading_screen.asm

        org  $8000

start:
        ; Decompress the loading screen into video memory
        ld   hl, compressed_screen
        ld   de, $4000          ; screen memory base
        call dzx0_standard

        ; Wait for a keypress
.wait:  xor  a
        in   a, ($fe)
        cpl
        and  $1f
        jr   z, .wait

        ret

; --- ZX0 decompressor (include the standard version) ---
        include "dzx0_standard.asm"

; --- Compressed loading screen ---
compressed_screen:
        incbin "screen.zx0"

        ; Size report
        display "Code + decompressor: ", /d, dzx0_standard - start, " bytes"
        display "Compressed screen: ", /d, $ - compressed_screen, " bytes"
        display "Total: ", /d, $ - start, " bytes"
```

The DISPLAY directives are an SjASMPlus feature that prints size information during assembly. Use them. Always know exactly how large your compressed data is. If a loading screen compresses to 4,200 bytes with ZX0 but 3,800 bytes with Exomizer, and you are only decompressing it once at startup, Exomizer may be worth the larger decompressor. If you are decompressing it every time you return to the title screen, ZX0's faster decompression might matter more.

### Choosing the right compressor: a decision tree

Ask these questions in order:

1. **Is this a size-coded intro (256b, 512b, 1K)?** Use ZX0 or ZX7. The 69--70 byte decompressor is non-negotiable. You cannot afford Exomizer's 170 bytes.

2. **Do you need to decompress during playback (streaming)?** Use LZ4. At ~34 T-states per output byte, it can decompress over 2,000 bytes per frame. No other tool comes close. You sacrifice 10 percentage points of compression ratio for 7x the decompression speed of Exomizer.

3. **Is this a one-time decompression at load time?** Use Exomizer for maximum compression ratio. The 250 T-states per byte do not matter if you are decompressing once during a loading screen. The user will not notice an extra half-second of loading. They will notice if the demo runs out of memory because you chose a worse compressor.

4. **Do you need a balance?** ApLib (~105 T/byte, 49.2% ratio) or Pletter 5 (~69 T/byte, 51.5% ratio). Both sit on the Pareto frontier --- no tool beats them on both dimensions simultaneously.

5. **Is your data mostly runs of identical bytes?** Consider RLE first, then compress the RLE stream with LZ if needed. Two-stage compression can outperform either stage alone on the right data.

6. **Is your data a sequence of similar frames?** Apply delta coding first, then compress the deltas with ZX0 or your chosen LZ compressor. The delta stream will compress dramatically better than the raw frames.

---

## The MegaLZ Revival

A postscript that illustrates why the demoscene's compression landscape keeps evolving.

In 2017, Introspec declared MegaLZ "morally obsolete" --- its compression ratio was similar to Pletter 5, but its decompressor was slower. The format was dead.

Two years later, Introspec himself resurrected it.

The key insight: the compression *format* and the *decompressor implementation* are separable problems. MegaLZ's format was actually good --- it had been the first Spectrum compressor to use an optimal parser (LVD, 2005), and its Elias gamma codes and 500-byte-larger window gave it a slight compression edge over Pletter 5. What was bad was the Z80 decompressor code.

Introspec wrote two new decompressors for MegaLZ:

- **Compact version:** 92 bytes, ~98 T-states per byte (down from 110 bytes and much slower)
- **Fast version:** 234 bytes, ~63 T-states per byte --- faster than three consecutive LDIRs

With the new decompressors, MegaLZ "handily beats Pletter 5 and ZX7" on the combined compression-ratio-plus-speed metric. Introspec kept MegaLZ in his own demo engine because it compressed his specific data "noticeably better" than the alternatives.

The lesson for the practitioner: do not assume a compressor is forever dead. The format is the hard part --- getting optimal parsing right, choosing the right code lengths, balancing the encoding. The decompressor is "just" Z80 code, and Z80 code can always be rewritten. If you find a format that compresses your data well but has a slow decompressor, the format may be worth saving.

---

## What the Numbers Mean in Practice

**4K intro:** 4,096 bytes total. ZX0 decompressor: ~70 bytes. Engine + music + effects: ~2,400 bytes. That leaves ~1,626 bytes for compressed data, which decompress to ~3,127 bytes of raw assets. SerzhSoft's Megademica (1st place, Revision 2019) compressed tunnel effects, transitions, AY music, and rapid scene changes into exactly 4,096 bytes. It was nominated for Outstanding Technical Achievement at the Meteoriks.

**Real-time streaming:** You need 2 KB of data per frame at 50 fps. LZ4 at 34 T/byte decompresses 2,048 bytes in 69,632 T-states --- almost exactly one frame (69,888 T-states on 48K). Tight but feasible with overlapped border-time decompression. ApLib would need 215,040 T-states for the same data --- over three frames. Exomizer over seven. For streaming, LZ4 is the only option.

**128K multi-scene demo:** Eight scenes, each with a 6,912-byte loading screen. Exomizer compresses each to ~3,338 bytes; ZX0 to ~3,594 bytes. The difference: 256 bytes per screen, 2,048 bytes across 8 scenes. When decompression happens during scene transitions, Exomizer's slow decompression is invisible. The 2 KB savings is not.

**256-byte intro:** ZX0's 70-byte decompressor leaves 186 bytes for everything. More commonly at this size, you skip LZ and generate data procedurally with LFSR generators and ROM calculator calls. But when you need specific non-algorithmic data --- a colour ramp, a bitmap fragment --- ZX0 remains the tool.

---

## Summary: The Compressor Cheat Sheet

| Your situation | Use this | Why |
|---|---|---|
| One-time load, maximum ratio | Exomizer | 48.3% ratio, speed irrelevant |
| General purpose, good balance | ApLib | 49.2% ratio, ~105 T/byte |
| Need speed + decent ratio | Pletter 5 | 51.5% ratio, ~69 T/byte |
| Real-time streaming | LZ4 | ~34 T/byte, 2+ KB per frame |
| Size-coded intro (256b--1K) | ZX0 / ZX7 | 69--70 byte decompressor |
| 4K intro | ZX0 | Tiny decompressor + good ratio |
| Runs of identical bytes | RLE (custom) | Decompressor under 30 bytes |
| Sequential animation frames | Delta + LZ | Exploit inter-frame redundancy |

The numbers are the answer. Not opinions, not folklore, not "I heard Exomizer is the best." Introspec tested ten compressors across 1.2 megabytes of real Spectrum data and published the results. Use his numbers. Choose the compressor that fits your constraints. Then move on to the hard part --- making something worth compressing.

---

## Try It Yourself

1. **Compress a loading screen.** Take any ZX Spectrum .scr file (grab one from zxart.ee or create your own in Multipaint). Compress it with ZX0 and Exomizer. Compare the sizes. Then write the minimal loader shown in this chapter to decompress and display it. Time the decompression using border-colour timing from Chapter 1.

2. **Measure the streaming limit.** Write a tight loop that decompresses data with the ZX0 standard decompressor and measures how many bytes it can decompress per frame. Compare with the LZ4 decompressor. Verify the numbers from the benchmark table against your own measurements.

3. **Build a delta compressor.** Take two ZX Spectrum screens that differ slightly (save a game screen, move a sprite, save again). Write a simple tool (in Python or your language of choice) that produces a delta stream: a list of (offset, new_value) pairs for bytes that differ. Compare the size of the delta stream to the size of the full second screen. Then compress the delta stream with ZX0 and compare again.

4. **Integrate compression into a Makefile.** Set up a project with a Makefile that automatically compresses assets as a build step. Change a source PNG, run `make`, and verify that the compressed binary is regenerated and the final .tap file is updated. This is the workflow you will use for every project from now on.

> **Sources:** Introspec "Data Compression for Modern Z80 Coding" (Hype, 2017); Introspec "Compression on the Spectrum: MegaLZ" (Hype, 2019); Break Space NFO (Thesuper, 2016); Einar Saukas, ZX0 (github.com/einar-saukas/ZX0)
