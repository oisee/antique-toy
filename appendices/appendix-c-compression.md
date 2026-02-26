# Appendix C: Compression Quick Reference

> *"The question is not whether to compress --- it is which compressor to use, and when."*
> -- Chapter 14

This appendix is a tear-out reference card for data compression on the ZX Spectrum. Chapter 14 covers the theory, the benchmark data, and the reasoning behind each recommendation. This appendix distils it into lookup tables and decision rules you can pin above your monitor.

All numbers come from Introspec's 2017 benchmark ("Data Compression for Modern Z80 Coding," Hype) unless otherwise noted. The test corpus was 1,233,995 bytes of mixed data: Calgary/Canterbury academic benchmarks, 30 ZX Spectrum graphics, 24 music files, and miscellaneous demo data.

---

## Compressor Comparison Table

| Compressor | Author | Compressed (bytes) | Ratio | Decompressor Size | Speed (T/byte) | Backwards | Notes |
|------------|--------|--------------------|-------|--------------------|-----------------|-----------|-------|
| **Exomizer 2** | Magnus Lind | 596,161 | 48.3% | ~170 bytes | ~250 | Yes | Best ratio. Slow to decompress. |
| **ApLib** | Joergen Ibsen | 606,833 | 49.2% | ~199 bytes | ~105 | No | Good all-rounder. |
| **Hrust 1** | Alone Coder | 613,602 | 49.7% | ~150 bytes | ~120 | Yes | Relocatable stack depacker. Popular in Russian scene. |
| **PuCrunch** | Pasi Ojala | 616,855 | 50.0% | ~200 bytes | ~140 | No | Originally for C64. |
| **Pletter 5** | XL2S | 635,797 | 51.5% | ~120 bytes | ~69 | No | Fast + decent ratio. |
| **MegaLZ** | LVD / Introspec | 636,910 | 51.6% | 92 bytes (compact) | ~98 (compact) | No | Optimal parser. Revived 2019 with new decompressors. |
| **MegaLZ fast** | LVD / Introspec | 636,910 | 51.6% | 234 bytes | ~63 | No | Fastest MegaLZ variant. Faster than 3x LDIR. |
| **ZX0** | Einar Saukas | ~642,000* | ~52% | ~70 bytes | ~100 | Yes | Successor to ZX7. Optimal parser. Modern default. |
| **ZX7** | Einar Saukas | 653,879 | 53.0% | **69 bytes** | ~107 | Yes | Tiny decompressor. The classic size-coder tool. |
| **Bitbuster** | Team Bomba | ~660,000* | ~53.5% | ~90 bytes | ~80 | No | Simple. Good for first projects. |
| **LZ4** | Yann Collet (Z80 port) | 722,522 | 58.6% | ~100 bytes | **~34** | No | Fastest decompression. Byte-aligned tokens. |
| **Hrum** | Hrumer | ~642,000* | ~52% | ~130 bytes | ~110 | No | Popular in Russian scene. Declared obsolete by Introspec. |
| **ZX1** | Einar Saukas | --- | ~51% | ~80 bytes | ~90 | Yes | ZX0 variant. Slightly better ratio, slightly larger decompressor. |
| **ZX2** | Einar Saukas | --- | ~50% | ~100 bytes | ~85 | Yes | Used in RED REDUX 256b intro (2025). Best ZXn ratio. |

\* Approximate. ZX0, Bitbuster, and Hrum were not in the original 2017 benchmark; values are estimated from independent tests on similar corpora.

**Reading the table:**

- **Ratio** = compressed size / original size. Lower is better.
- **Speed** = T-states per output byte during decompression. Lower is faster.
- **Decompressor Size** = bytes of Z80 code needed for the decompression routine. Lower is better for size-coded intros.
- **Backwards** = supports decompressing from end to start, allowing in-place decompression when source and destination overlap.

---

## Decision Tree: Which Compressor?

Follow top-to-bottom. Take the first branch that matches your situation.

```
START
  |
  +-- Is this a 256-byte or 512-byte intro?
  |     YES --> ZX0 (70-byte decompressor) or custom RLE (<30 bytes)
  |
  +-- Is this a 1K or 4K intro?
  |     YES --> ZX0 (best ratio-to-decompressor-size)
  |
  +-- Do you need real-time streaming (decompress during playback)?
  |     YES --> LZ4 (~34 T/byte = 2+ KB per frame at 50fps)
  |
  +-- Do you need fast decompression between scenes?
  |     YES --> MegaLZ fast (~63 T/byte) or Pletter 5 (~69 T/byte)
  |
  +-- Is decompression speed irrelevant (one-time load at startup)?
  |     YES --> Exomizer (48.3% ratio, nothing beats it)
  |
  +-- Need a good balance of ratio and speed?
  |     YES --> ApLib (~105 T/byte, 49.2% ratio)
  |
  +-- Is the data mostly runs of identical bytes?
  |     YES --> Custom RLE (decompressor < 30 bytes, trivial)
  |
  +-- Is the data sequential animation frames?
  |     YES --> Delta-encode first, then compress with ZX0 or LZ4
  |
  +-- First project, want something simple?
        YES --> Bitbuster or ZX0 (both well-documented, easy to integrate)
```

---

## Compressibility of Common ZX Spectrum Data Types

How well different data types compress, and tricks to improve the ratio.

| Data Type | Raw Size | Typical ZX0 Ratio | Typical Exomizer Ratio | Notes |
|-----------|----------|-------------------|------------------------|-------|
| **Screen pixels** ($4000-$57FF) | 6,144 bytes | 40--60% | 35--55% | Depends on image complexity. Black backgrounds compress well. |
| **Attributes** ($5800-$5AFF) | 768 bytes | 30--50% | 25--45% | Often highly repetitive. Solid-colour areas compress to almost nothing. |
| **Full screen** (pixels + attrs) | 6,912 bytes | 40--58% | 35--52% | Compress pixels and attributes separately for 5--10% better ratio. |
| **Sine/cosine tables** | 256 bytes | 60--75% | 55--70% | Smooth curves compress well. Consider generation instead (Appendix B). |
| **Tile data** (8x8 tiles) | varies | 35--55% | 30--50% | Reorder tiles by similarity for better ratio. |
| **Sprite data** | varies | 45--65% | 40--60% | Mask bytes hurt ratio. Store masks separately. |
| **PT3 music data** | varies | 40--55% | 35--50% | Pattern data is repetitive. Empty rows compress well. |
| **AY register dumps** | varies | 30--50% | 25--45% | Highly repetitive between frames. Delta-encode first. |
| **Lookup tables** (arbitrary) | varies | 50--80% | 45--75% | Random-looking data compresses poorly. Pre-sort if possible. |
| **Font data** (96 chars x 8 bytes) | 768 bytes | 55--70% | 50--65% | Lots of zero bytes (descenders, thin strokes). |

### Pre-compression tricks

These techniques improve compression ratio by restructuring data before feeding it to the compressor.

**Separate pixels from attributes.** A full 6,912-byte screen stored as one block forces the compressor to handle a transition from pixel data to attribute data at byte 6,144. Compress the 6,144-byte pixel block and the 768-byte attribute block separately. The attribute block, being highly repetitive, often compresses to under 200 bytes.

**Delta-encode animation frames.** Store the first frame in full. For each subsequent frame, store only the bytes that differ from the previous frame as (offset, value) pairs. Apply LZ compression to the delta stream. psndcj compressed 122 frames (843,264 bytes raw) into 10,512 bytes using this technique in Break Space.

**Reorder data for locality.** Tile maps stored in row-major order may compress better if reordered so that similar tiles are adjacent. Sort sprite frames by visual similarity. Group repeated sub-patterns together.

**Store constants separately.** If a data block contains a repeated header or footer (e.g., tile metadata), factor it out and store it once. Only compress the variable portion.

**Interleave planes.** For multicolour or masked sprites, storing all mask bytes together and all pixel bytes together often compresses better than interleaving mask-pixel-mask-pixel per row.

---

## Minimal RLE Decompressor

The simplest useful compressor. Only 12 bytes of code. Suitable for 256-byte intros or data with long runs of identical bytes. See Chapter 14 for a full discussion.

```z80
; Minimal RLE decompressor
; Format: [count][value] pairs, terminated by count = 0
; HL = source (compressed data)
; DE = destination (output buffer)
; Destroys: AF, BC
rle_decompress:
        ld      a, (hl)         ; read count             7T
        inc     hl              ;                         6T
        or      a               ; count = 0?              4T
        ret     z               ; yes: done               5T/11T
        ld      b, a            ; B = count               4T
        ld      a, (hl)         ; read value              7T
        inc     hl              ;                         6T
.fill:  ld      (de), a         ; write value             7T
        inc     de              ;                         6T
        djnz    .fill           ; loop B times            13T/8T
        jr      rle_decompress  ; next pair               12T
; Total: 12 bytes of code
; Speed: ~26 T-states per output byte (within long runs)
;        + 46T overhead per [count, value] pair
```

**Encoding tool** (Python one-liner for simple RLE):

```python
def rle_encode(data):
    out = bytearray()
    i = 0
    while i < len(data):
        val = data[i]
        count = 1
        while i + count < len(data) and data[i + count] == val and count < 255:
            count += 1
        out.extend([count, val])
        i += count
    out.extend([0])  # terminator
    return out
```

This naive RLE expands data with no runs (worst case: 2 bytes per 1 byte of input). For mixed data, use escape-byte RLE: a special byte signals a run, and all other bytes are literals. Or just use ZX0.

**Transposition trick.** RLE benefits dramatically from column-major data layout. If you have a 32×24 attribute block where each row varies but columns are often constant, transposing the data (storing all column 0 values, then column 1, etc.) creates long runs that RLE compresses well. The trade-off: the Z80 must un-transpose the data after decompression, which costs an extra pass (~13 T-states per byte for a simple nested-loop copy). Count the total cost (decompressor code + un-transpose code + compressed data) against ZX0 (decompressor + compressed data, no transform needed) to see which wins for your specific data.

---

## ZX0 Standard Decompressor (Z80)

The full standard forward decompressor by Einar Saukas. Approximately 70 bytes. This is the version you will use in most projects.

```z80
; ZX0 decompressor - standard forward version
; (c) Einar Saukas, based on Wikipedia description of LZ format
; HL = source (compressed data)
; DE = destination (output buffer)
; Destroys: AF, BC, DE, HL
dzx0_standard:
        ld      bc, $ffff       ; initial offset = -1
        push    bc              ; store offset on stack
        inc     bc              ; BC = 0 (literal length will be read)
        ld      a, $80          ; init bit buffer with end marker
dzx0s_literals:
        call    dzx0s_elias     ; read number of literals
        ldir                    ; copy literals from source to dest
        add     a, a            ; read next bit: 0 = last offset, 1 = new offset
        jr      c, dzx0s_new_offset
        ; reuse last offset
        call    dzx0s_elias     ; read match length
dzx0s_copy:
        ex      (sp), hl        ; swap: HL = offset, stack = source
        push    hl              ; put offset back on stack
        add     hl, de          ; HL = dest + offset = match source address
        ldir                    ; copy match
        add     a, a            ; read next bit: 0 = literal, 1 = match/offset
        jr      nc, dzx0s_literals
        ; new offset
dzx0s_new_offset:
        call    dzx0s_elias     ; read offset MSB (high bits)
        ex      af, af'         ; save bit buffer
        dec     b               ; B = $FF (offset is negative)
        rl      c               ; C = offset MSB * 2 + carry
        inc     c               ; adjust
        jr      z, dzx0s_done   ; offset = 256 means end of stream
        ld      a, (hl)         ; read offset LSB
        inc     hl
        rra                     ; LSB bit 0 -> carry = length bit
        push    bc              ; save offset MSB
        ld      b, 0
        ld      c, a            ; C = offset LSB >> 1
        pop     af              ; A = offset MSB (from push bc)
        ld      b, a            ; BC = full offset (negative)
        ex      (sp), hl        ; store offset, retrieve source
        push    bc              ; store offset again
        ld      bc, 1           ; minimum match length = 1
        jr      nc, dzx0s_copy  ; if carry clear: length = 1
        call    dzx0s_elias     ; otherwise read match length
        inc     bc              ; +1
        jr      dzx0s_copy
dzx0s_done:
        pop     hl              ; clean stack
        ex      af, af'         ; restore flags
        ret
; Elias interlaced code reader
dzx0s_elias:
        inc     c               ; C starts at 1
dzx0s_elias_loop:
        add     a, a            ; read bit
        jr      nz, dzx0s_elias_nz
        ld      a, (hl)         ; refill bit buffer
        inc     hl
        rla                     ; shift in carry
dzx0s_elias_nz:
        ret     nc              ; stop bit (0) = done
        add     a, a            ; read data bit
        jr      nz, dzx0s_elias_nz2
        ld      a, (hl)         ; refill
        inc     hl
        rla
dzx0s_elias_nz2:
        rl      c               ; shift bit into C
        rl      b               ; and into B
        jr      dzx0s_elias_loop
```

**Usage:**

```z80
        ld      hl, compressed_data     ; source address
        ld      de, $4000               ; destination (e.g., screen)
        call    dzx0_standard           ; decompress
```

**Backwards variant.** ZX0 also provides a backwards decompressor (`dzx0_standard_back`) that reads compressed data from end to start and writes output from end to start. This enables in-place decompression: place the compressed data at the end of the destination buffer, and decompress backwards so the output overwrites the compressed data only after it has been read. Essential when RAM is tight.

---

## Integration Patterns

### Pattern 1: Decompress to screen at startup

The most common use case. Load a compressed loading screen and display it.

```z80
        org     $8000
start:
        ld      hl, compressed_screen
        ld      de, $4000               ; screen memory
        call    dzx0_standard
        ; screen is now visible
        ; ... continue with demo/game ...

        include "dzx0_standard.asm"

compressed_screen:
        incbin  "screen.zx0"
```

### Pattern 2: Decompress to buffer between effects

Decompress the next effect's data into a scratch buffer while the current effect is still running, or during a fade-out.

```z80
; During scene transition:
        ld      hl, scene2_data_zx0
        ld      de, scratch_buffer      ; e.g., $C000 in bank 1
        call    dzx0_standard
        ; scratch_buffer now holds the uncompressed data
        ; switch to scene 2, which reads from scratch_buffer
```

### Pattern 3: Stream decompression during playback

For real-time effects that need a continuous data feed. LZ4 is the only practical choice here.

```z80
; Each frame: decompress next chunk
frame_loop:
        ld      hl, (lz4_read_ptr)     ; current position in compressed stream
        ld      de, frame_buffer
        ld      bc, 2048                ; bytes to decompress this frame
        call    lz4_decompress_partial
        ld      (lz4_read_ptr), hl     ; save position for next frame
        ; render from frame_buffer
        ; ...
        jr      frame_loop
```

At ~34 T/byte, LZ4 decompresses 2,048 bytes in 69,632 T-states --- fitting within one frame (69,888 T-states on 48K). This is tight. Use border-time decompression or double-buffering for safety.

### Pattern 4: Bank-switched compressed data (128K)

Store compressed data across multiple 16KB banks. Decompress from the currently paged bank, then switch banks when you run out.

```z80
; Page in bank containing compressed data
        ld      a, (current_bank)
        or      $10                     ; bit 4 = ROM select
        ld      bc, $7ffd
        out     (c), a                  ; page bank into $C000-$FFFF

        ld      hl, $C000              ; compressed data starts at bank base
        ld      de, dest_buffer
        call    dzx0_standard

        ; Page next bank for next asset
        ld      a, (current_bank)
        inc     a
        ld      (current_bank), a
```

For large demos with many compressed assets, maintain a table of (bank, offset, destination) tuples and loop through them during loading.

---

## Build Pipeline: From Asset to Binary

The compression step belongs in your Makefile, not in your head.

```
Source asset       Converter        Compressor        Assembler
  (PNG)       -->   (png2scr)   -->   (zx0)      -->  (sjasmplus)  --> .tap
  (WAV)       -->   (pt3tools)  -->   (zx0)      -->  (incbin)
  (TMX)       -->   (tmx2bin)   -->   (exomizer)
```

**Makefile rules:**

```makefile
# Compress .scr screens with ZX0
%.zx0: %.scr
	zx0 $< $@

# Compress large assets with Exomizer (one-time load)
%.exo: %.bin
	exomizer raw -c $< -o $@

# Build final binary
demo.bin: main.asm assets/title.zx0 assets/font.zx0
	sjasmplus main.asm --raw=$@
```

**Tool installation:**

| Tool | Source | Install |
|------|--------|---------|
| ZX0 | github.com/einar-saukas/ZX0 | `gcc -O2 -o zx0 src/zx0.c src/compress.c src/optimize.c src/memory.c` |
| Exomizer | github.com/bitmanipulators/exomizer | `make` in `src/` directory |
| LZ4 | github.com/lz4/lz4 | `make` or `brew install lz4` |
| MegaLZ | github.com/AntonioCerra/megalzR | Older; check Introspec's Hype article for links |

---

## Quick Formulas

**Bytes per frame at 50fps with decompressor X:**

```
bytes_per_frame = 69,888 / speed_t_per_byte
```

| Compressor | T/byte | Bytes/frame (48K) | Bytes/frame (128K Pentagon) |
|------------|--------|-------------------|-----------------------------|
| LZ4 | 34 | 2,055 | 2,108 |
| MegaLZ fast | 63 | 1,109 | 1,138 |
| Pletter 5 | 69 | 1,012 | 1,038 |
| ZX0 | 100 | 698 | 716 |
| ApLib | 105 | 665 | 682 |
| Hrust 1 | 120 | 582 | 597 |
| Exomizer | 250 | 279 | 286 |

(128K Pentagon frame = 71,680 T-states)

**Memory saved by compression over N screens:**

```
saved = N * 6912 * (1 - ratio)
```

Example: 8 loading screens with Exomizer at 48.3% ratio save 8 * 6912 * 0.517 = 28,575 bytes --- nearly two full 16KB banks.

---

## See Also

- **Chapter 14:** Full discussion of compression theory, Introspec's benchmark, ZX0 internals, and the delta + LZ pipeline.
- **Appendix B:** Sine table generation --- when tables are small enough, consider generating instead of compressing.
- **Appendix A:** Z80 instruction reference --- LDIR, PUSH/POP, and other instructions used in decompressors.

> **Sources:** Introspec "Data Compression for Modern Z80 Coding" (Hype, 2017); Introspec "Compression on the Spectrum: MegaLZ" (Hype, 2019); Einar Saukas, ZX0/ZX7/ZX1/ZX2 (github.com/einar-saukas); Break Space NFO (Thesuper, 2016)
