# Chapter 17: Scrolling

> "The screen is 256 pixels wide. The level is 8,000. Somehow, the player must move through it."

---

Every side-scrolling game needs to move the world. The player runs right, the background shifts left. It looks simple. On hardware with a scroll register -- the NES, the Mega Drive, the Agon Light 2 -- it *is* simple: write an offset, and the hardware does the rest. On the ZX Spectrum, there is no scroll register. There is no hardware assistance of any kind. To scroll the screen, you move the bytes yourself. All 6,144 of them.

This chapter works through every practical scrolling method on the Spectrum, from the cheapest to the most expensive: attribute scrolling (768 bytes, trivial), vertical pixel scrolling (tricky because of the interleaved memory layout from Chapter 2), horizontal pixel scrolling (expensive -- every byte in every row must be shifted), and the combined method that real games use to get smooth horizontal scrolling within a manageable budget. We will count every T-state, build comparison tables, and show how the shadow screen trick on the 128K makes the whole thing tearfree.

Then we will look at how the Agon Light 2 handles the same problem with hardware scroll offsets and tilemap support -- a useful contrast that shows what "the same ISA with different hardware" really means in practice.

---

## The Budget

Before we write a single instruction, let us establish what we are working with.

On a Pentagon (the timing model most Spectrum demos and games target), one frame is **71,680 T-states**. On a standard 48K/128K Spectrum, it is 69,888. We will use the Pentagon figure throughout, but the analysis applies to both -- the difference is about 2.5%.

A full-screen scroll means moving data across all 6,144 bytes of pixel memory (and possibly the 768 bytes of attribute memory). The question is always the same: can we do it in one frame, and if so, how many T-states are left for everything else -- game logic, sprite drawing, music, input?

Here is the raw cost of just *touching* every byte in the pixel area, using different methods:

| Method | Per byte | 6,144 bytes | % of frame |
|--------|----------|-------------|------------|
| `ldir` | 21 T | 129,003 T | 180% |
| `ldi` chain | 16 T | 98,304 T | 137% |
| `ld a,(hl)` + `ld (de),a` + `inc hl` + `inc de` | 24 T | 147,456 T | 206% |
| `push` (2 bytes) | 5.5 T/byte | 33,792 T | 47% |

The first three methods cannot move the full pixel area in a single frame. Even `ldi` chains, the fastest copying method after PUSH, blow the budget by 37%. And scrolling is not just copying -- horizontal scrolling requires a *shift* operation on every byte, which adds to the per-byte cost.

This is why scrolling on the Spectrum is a design problem, not just a coding problem. You cannot brute-force a full-screen pixel scroll at 50fps. You must choose your method based on what your game can afford.

---

## Vertical Pixel Scrolling

Vertical scrolling moves the screen contents up or down by one or more pixel rows. Conceptually it is simple: copy each row to the position of the row above (for scrolling up) or below (for scrolling down). On a linear framebuffer, this would be a single block copy. On the Spectrum, the interleaved memory layout (Chapter 2) makes it considerably more interesting.

### The Interleave Problem

Recall the screen address structure from Chapter 2:

```
High byte:  0 1 0 T T S S S
Low byte:   L L L C C C C C
```

Where TT = third (0--2), SSS = scanline within character cell (0--7), LLL = character row within third (0--7), CCCCC = column byte (0--31).

To scroll up by one pixel, you need to copy the contents of row N to row N-1, for every row from 1 to 191. The source and destination addresses for adjacent pixel rows are *not* separated by a constant offset. Within a character cell, consecutive rows differ by $0100 in the high byte (just `INC H` / `DEC H`). But at character cell boundaries -- every 8th row -- the relationship changes: you must adjust L by 32 and reset the scanline bits in H. At third boundaries (every 64th row), the adjustment is different again.

### The Algorithm: Scroll Up by One Pixel

The approach that works with the interleave, rather than against it, uses the split-counter structure from Chapter 2. Maintain two pointers (source and destination) and advance both using the screen's natural hierarchy: 3 thirds, 8 character rows per third, 8 scanlines per character row. Within each character cell, moving between scanlines is just `INC H` / `INC D` on the source and destination. At character row boundaries, reset the scanline bits and add 32 to L. At third boundaries, add 8 to H and reset L. The inner loop copies 32 bytes per row with LDIR or an LDI chain, and the pointer advancement is folded into the outer loop structure.

### Cost Analysis

For each of the 191 row copies, we must copy 32 bytes from source to destination. Using LDIR:

- Per row: 32 bytes x 21 T-states - 5 = 667 T-states for the LDIR, plus pointer management overhead.
- Pointer management (save/restore source and dest, advance scanline): approximately 60 T-states per row within a character cell, more at boundaries.

**Total with LDIR: approximately 143,000 T-states.** That is roughly **two full frames**. A vertical pixel scroll by one row using LDIR does not fit in a single frame.

We can do better. Replace the LDIR with an LDI chain -- 32 LDI instructions per row:

- Per row: 32 x 16 = 512 T-states for the LDIs, plus ~50 T-states of pointer management.
- Total: 191 x 562 = **107,342 T-states.** Still over budget by about 50%.

The PUSH trick is awkward here because we need to copy *between* two non-contiguous areas with a non-constant relationship. PUSH writes to contiguous descending addresses, which does not match the interleaved source/destination pattern.

### Partial Scrolling: The Practical Approach

The reality is that most games do not scroll the entire 192-line display. A typical game reserves:

- Top 2 character rows (16 pixels) for a status bar -- not scrolled.
- Bottom 1 character row (8 pixels) for a score line -- not scrolled.
- Middle: 21 character rows = 168 pixel rows = the scrolling play area.

168 rows of vertical pixel scrolling with LDI chains: 168 x 562 = **94,416 T-states**, or 132% of a frame. Still too much for a single frame if you want time for anything else.

This is why pure vertical pixel scrolling at 1px/frame is rare in Spectrum games. The common approaches are:

1. **Scroll by 8 pixels (one character row):** Move the attributes and the character-aligned pixel data. This is much cheaper because you only copy 21 character rows x 8 scanlines = 168 rows, but you can use a block copy trick: within each third, the character rows are contiguous in blocks. Cost: around 40,000--50,000 T-states with LDIR. Feasible.

2. **Scroll by 1 pixel using a counter:** Scroll 1px per frame visually by combining a character-level scroll (cheap, every 8 frames) with a pixel offset counter (draw new content at an offset within the 8px character cell). We will cover this combined approach in the horizontal scrolling section below, because it is far more commonly needed there.

3. **Use the shadow screen (128K only):** Draw the scrolled content into a back buffer, then flip. This eliminates tearing and lets you spread the work across frames. We cover this later in the chapter.

### Scrolling by 8 Pixels (One Character Row)

Scrolling by a full character row is dramatically cheaper because the source and destination are related by a simple offset within each third. The character rows within a third are spaced 32 bytes apart in L. So scrolling one character row up means copying from L+32 to L, for each scanline and each third.

For scrolling the play area by one character row, the key insight is that within a single scanline, character rows are stored contiguously (32 bytes apart). Scanline 0 of char rows 0--7 in a third lives at `$xx00`, `$xx20`, `$xx40`, ..., `$xxE0`. Scrolling N character rows up by one position within a single scanline is therefore a single block copy of (N-1) x 32 bytes.

For a 20-character-row play area, one scanline's worth of data is 20 x 32 = 640 bytes. Scrolling that scanline means copying 19 x 32 = 608 bytes forward by 32. We do this for each of the 8 scanlines, handling third boundaries separately.

**Estimated cost:** 8 scanlines x ~12,700 T-states per scanline (608 bytes via LDIR) + third-boundary handling = approximately **105,000 T-states**. That is 146% of a frame.

Even character-row scrolling the full play area in one frame is tight. Games handle this by either:

- **Scrolling during the blank (border) period.** The top and bottom border on a Pentagon give approximately 14,000 T-states of free time where no contention occurs.
- **Splitting across two frames.** Scroll the top half one frame, the bottom half the next. The visual effect is a 25fps scroll at 8-pixel jumps.
- **Using the shadow screen** (see below).

---

## Horizontal Pixel Scrolling

Horizontal scrolling is the bread and butter of side-scrolling games: the world moves left or right as the player walks. And it is the most expensive type of scrolling on the Spectrum, because it requires not just copying bytes but *shifting* them.

### Why Horizontal Scrolling Is Expensive

When you scroll the screen left by one pixel, every byte in every row must shift its bits left by one position, and the bit that falls off the left edge of one byte must become the rightmost bit of its left neighbour. This is a rotate-and-carry chain across all 32 bytes of each row.

The Z80's `RL` (rotate left through carry) instruction is the tool for this. For a leftward scroll, each pixel moves one position left. Bit 7 is the leftmost pixel in a byte, bit 0 the rightmost. Shifting left means each byte's bit 7 exits and must enter bit 0 of the byte to its left. The carry flag bridges adjacent bytes, so we process the row from **right to left**:

```z80
; Scroll one pixel row left by 1 pixel
; HL points to byte 31 (rightmost) of the row
;
; Process right to left. Each byte rotates left; carry propagates.
;
    or   a                    ; 4 T   clear carry (no pixel entering from right)

    ; Byte 31 (rightmost)
    rl   (hl)                 ; 15 T  shift left, bit 7 -> carry, carry -> bit 0
    dec  hl                   ; 6 T
    ; Byte 30
    rl   (hl)                 ; 15 T
    dec  hl                   ; 6 T
    ; ...repeat for bytes 29 down to 0...
    ; Byte 0 (leftmost)
    rl   (hl)                 ; 15 T  bit 7 of byte 0 is lost (scrolled off screen)
```

Each byte costs: 15 (RL (HL)) + 6 (DEC HL) = **21 T-states** per byte. For 32 bytes per row: 32 x 21 - 6 = **666 T-states** per row (we do not need the final DEC HL).

Actually, the first byte needs `OR A` (4 T) to clear carry. So one row costs: 4 + 32 x 15 + 31 x 6 = 4 + 480 + 186 = **670 T-states**.

For 192 rows: 192 x 670 = **128,640 T-states**. That is **179% of a frame**.

A full-screen horizontal pixel scroll by one pixel does not fit in a single frame using RL chains. And this is *just the shifting* -- we have not drawn any new content on the right edge.

### The Full Budget Calculation

Let us lay out the complete per-row cost with all the overhead of navigating the interleaved screen:

| Operation | T-states per row |
|-----------|-----------------|
| Set HL to row start (or advance from previous) | ~15 |
| Set HL to rightmost byte: `ld a, l : or $1F : ld l, a` | 15 |
| Clear carry: `or a` | 4 |
| 32 x `rl (hl)` | 480 |
| 31 x `dec hl` (between bytes) | 186 |
| Advance to next row (`inc h` or boundary cross) | 4--77 |
| **Total per row (typical)** | **~704** |

For 192 rows: 192 x 704 = **135,168 T-states** = **189% of one frame**.

For a 168-row play area: 168 x 704 = **118,272 T-states** = **165% of one frame**.

There is no way to do a full-screen single-pixel horizontal scroll in one frame with standard methods on a 3.5 MHz Z80. This is the fundamental constraint that drives every scrolling technique in this chapter.

### Can We Do Better?

You might think unrolling or alternate addressing modes would help. They do not. `RL (IX+d)` costs 23 T-states -- *more* than `RL (HL)` at 15 T. A load-rotate-store sequence (`LD A,(HL) : RLA : LD (HL),A` at 18 T per byte, plus 6 T for `DEC HL` = 24 T) is also slower. The `RL (HL) : DEC HL` chain at 21 T/byte is essentially optimal for horizontal pixel scrolling on the Z80.

**Bottom line:** The only way to make horizontal scrolling affordable is to reduce the number of rows or bytes you scroll.

---

## Attribute (Character) Scrolling

If pixel scrolling is expensive, attribute scrolling is almost free by comparison. Attribute scrolling moves the display in 8-pixel (one character cell) jumps. You only move the 768 bytes of attribute memory and the corresponding character-aligned pixel blocks -- or, more commonly, you move just the attributes and redraw the play area from a tilemap.

### Scrolling Attributes with LDIR

The attribute area is linear: 32 bytes per row, 24 rows, sequential from `$5800` to `$5AFF`. Scrolling left by one character column means copying bytes 1--31 to positions 0--30 in each row, then writing the new column at position 31.

For the entire 24-row attribute area:

```z80
; Scroll all attributes left by 1 character column
; New column data in a 24-byte table at new_col_data
;
scroll_attrs_left:
    ld   hl, $5801          ; 10 T  source: column 1
    ld   de, $5800          ; 10 T  dest: column 0
    ld   bc, 767            ; 10 T  768 - 1 bytes
    ldir                    ; 767*21 + 16 = 16,123 T

    ; Now fill the rightmost column with new data
    ld   hl, new_col_data   ; 10 T
    ld   de, $581F          ; 10 T  column 31 of row 0
    ld   b, 24              ; 7 T
.fill_col:
    ld   a, (hl)            ; 7 T
    ld   (de), a            ; 7 T
    inc  hl                 ; 6 T
    ; advance DE by 32 (next attribute row)
    ld   a, e               ; 4 T
    add  a, 32              ; 7 T
    ld   e, a               ; 4 T
    jr   nc, .no_carry      ; 12/7 T
    inc  d                  ; 4 T
.no_carry:
    djnz .fill_col          ; 13 T
    ret

    ; Total LDIR: ~16,123 T
    ; Total column fill: ~24 * 50 = ~1,200 T
    ; Grand total: ~17,323 T = 24.2% of frame
```

**17,323 T-states for a full-screen attribute scroll.** That is about 24% of a frame. Compare this to the 135,000+ T-states for a pixel scroll. Attribute scrolling is nearly 8x cheaper.

The catch: the scroll jumps by 8 pixels at a time. The visual result is coarse and jerky. For text scrollers in demos, this is often acceptable -- the viewer reads the text, not the smoothness. For a game, 8-pixel jumps feel terrible. That is where the combined method comes in.

---

## The Combined Method: Character Scroll + Pixel Offset

This is the technique that most Spectrum side-scrolling games actually use. The idea is simple and powerful:

1. Maintain a **pixel offset** counter from 0 to 7. Each frame, increment the offset.
2. When the offset reaches 8, reset it to 0 and perform an **attribute/character scroll** -- the cheap operation.
3. On every frame, render the play area with the current pixel offset applied. This offset shifts the entire display by 0--7 pixels within the current character column positions.

The pixel offset can be applied in two ways:

**Method A: Shift the new column.** Only shift the one column of pixel data (the column being scrolled into view) by the current offset. The rest of the screen is drawn from tiles at character alignment. This works when you have a tile-based renderer that redraws from a map.

**Method B: Hardware-style virtual offset.** Maintain a rendering offset that controls where within each character cell the tile data begins. This is conceptually similar to a hardware scroll register but implemented in software.

Method A is more common in practice. Let us walk through it.

### How It Works

Imagine the play area is 20 characters (160 pixels) wide and 20 characters tall. The level data is a tilemap where each tile is 8x8 pixels (one character cell).

The scroll state consists of:
- `scroll_tile_x`: which tile column is at the left edge of the screen (integer, advances by 1 every 8 frames).
- `scroll_pixel_x`: pixel offset within the current tile (0--7, advances by 1 each frame).

Each frame:

1. **If `scroll_pixel_x` is 0:** Redraw the entire play area from the tilemap at character alignment. This is a tile renderer, which we can make fast using LDIR or LDI chains (each tile row is 1 byte or a few bytes of data copied to the right screen address). Cost: 20 columns x 20 rows x ~100 T per tile = ~40,000 T. Affordable.

2. **If `scroll_pixel_x` is 1--7:** Redraw the play area shifted by `scroll_pixel_x` pixels. For most of the play area, the tiles are character-aligned and can be drawn normally -- the pixel offset only affects the **leftmost and rightmost visible columns**, where a tile is partially visible.

Wait -- that is the efficient interpretation, but it requires a tile renderer that clips at sub-character boundaries. The simpler (and more common) approach is:

### The Simple Combined Method

1. Every 8 frames, perform a character-level scroll (LDIR the attribute and pixel data left by one column). Cost: ~17,000 T for attributes + ~40,000 T for pixel data = ~57,000 T. Done once every 8 frames.

2. Every frame, shift a **narrow window** by 1 pixel. This window is only 1 column (32 bytes) or 2 columns (64 bytes) wide -- the seam between the old data and the newly arriving column.

3. **Between character scrolls**, the display shows the last character-scrolled position with a 0--7 pixel offset applied to the edge column. The player perceives smooth 1-pixel-per-frame scrolling.

Here is the per-frame cost breakdown:

| Operation | T-states | Frequency |
|-----------|----------|-----------|
| Character scroll (full play area) | ~57,000 | Every 8th frame |
| Pixel-shift 1--2 edge columns (20 rows x 2 cols x 21 T/byte x 8 scanlines) | ~6,720 | Every frame |
| Draw new tile column at right edge | ~5,000 | Every 8th frame |
| Attribute column update | ~1,200 | Every 8th frame |

**On 7 out of 8 frames:** ~6,720 T-states for the edge pixel shift. That is under 10% of the frame budget. Plenty of room for game logic, sprites, and music.

**On every 8th frame:** ~6,720 + 57,000 + 5,000 + 1,200 = ~69,920 T-states. That is 97.5% of the frame budget. Tight, but doable -- especially if you split the character scroll across two frames or use the shadow screen.

### Implementation: The Edge-Column Pixel Shift

The key inner routine shifts 1 or 2 columns of pixel data by 1 pixel. For a 2-column (16-pixel) window, each row has 2 bytes to shift:

```z80
; Shift 2 bytes left by 1 pixel with carry propagation
; HL points to the right byte of the pair
;
    or   a                ; 4 T    clear carry
    rl   (hl)             ; 15 T   right byte: shift left, bit 7 -> carry
    dec  hl               ; 6 T
    rl   (hl)             ; 15 T   left byte: carry -> bit 0, bit 7 lost
                          ; total: 40 T per row (for 2-byte window)
```

For 160 rows (20 char rows x 8 scanlines): 160 x 40 = **6,400 T-states**. With pointer advancement overhead (~20 T per row), the total is about **9,600 T-states** per frame. Very affordable.

### The Rendering Pipeline

Here is the complete per-frame sequence for a combined horizontal scroller:

```z80
frame_loop:
    halt                         ; wait for interrupt

    ; --- Always: advance pixel offset ---
    ld   a, (scroll_pixel_x)
    inc  a
    cp   8
    jr   nz, .no_char_scroll

    ; --- Every 8th frame: character scroll ---
    xor  a                       ; reset pixel offset to 0
    ld   (scroll_pixel_x), a

    ; Advance tile position
    ld   hl, (scroll_tile_x)
    inc  hl
    ld   (scroll_tile_x), hl

    ; Scroll pixel data left by 1 column (8 pixels)
    call scroll_pixels_left_char

    ; Scroll attributes left by 1 column
    call scroll_attrs_left

    ; Draw new tile column on right edge
    call draw_right_column

    jr   .scroll_done

.no_char_scroll:
    ld   (scroll_pixel_x), a

    ; Shift the edge columns by 1 pixel
    call shift_edge_columns

.scroll_done:
    ; --- Game logic, sprites, music ---
    call update_entities
    call draw_sprites
    call play_music

    jr   frame_loop
```

This is the skeleton of a real Spectrum side-scroller. The key insight is that smooth 1-pixel scrolling is achieved *without* shifting the entire screen every frame. The expensive character-level scroll happens only once every 8 frames, and the per-frame work is minimal.

---

## Scrolling the Pixel Data by One Character Column

The character-level pixel scroll (step 2 in the pipeline above) shifts 8 pixels' worth of data leftward for every row. Because 8 pixels = 1 byte, this is a *byte-level* copy, not a bit-level rotate. Each row's 32 bytes shift left by 1 byte: byte[1] goes to byte[0], byte[2] goes to byte[1], ..., byte[31] goes to byte[30], and byte[31] is cleared or filled with new data.

For a single row, this is a 31-byte LDIR:

```z80
; Shift one pixel row left by 8 pixels (1 byte)
; HL = address of byte 1 (source), DE = address of byte 0 (dest)
; BC = 31
;
    ldir                     ; 31*21 - 5 = 646 T per row... wait.
                             ; Actually: 30*21 + 16 = 646 T. Yes.
```

For the full play area (168 rows): 168 x 646 = 108,528 T-states + row navigation overhead.

A better approach leverages the fact that within each scanline of a character row, the bytes are contiguous. For 20 character columns, one scanline's data is 20 contiguous bytes. Scrolling that scanline left by 1 byte means LDIR of 19 bytes:

```z80
; Scroll one scan line of the play area left by 1 character column
; Play area is 20 columns wide (columns 2-21, for example)
; Source: column 3, Dest: column 2, count: 19
;
    ld   hl, row_addr + 3    ; source = byte 3 of this scan line
    ld   de, row_addr + 2    ; dest   = byte 2
    ld   bc, 19              ; 19 bytes to copy
    ldir                     ; 18*21 + 16 = 394 T
```

For 160 rows: 160 x 394 = 63,040 T-states. Add ~20 T per row for pointer navigation: 160 x 414 = **66,240 T-states**. That is 92% of a frame. Doable but tight on the "every 8th frame" budget.

With LDI chains (19 LDIs per row): 19 x 16 = 304 T per row. For 160 rows: 160 x 324 = **51,840 T-states** = 72% of a frame. Now we have 28% left for drawing the new column and updating attributes.

---

## The Shadow Screen Trick

The ZX Spectrum 128K has a feature that transforms the scrolling problem: **two screen buffers**. The standard screen lives at `$4000` in page 5 (always mapped at `$4000`--`$7FFF`). The shadow screen lives at `$C000` in page 7 (mapped at `$C000`--`$FFFF` when page 7 is banked in).

Port `$7FFD` controls which screen is displayed:

```z80
; Bit 3 of port $7FFD selects the display screen:
;   Bit 3 = 0: display page 5 (standard screen at $4000)
;   Bit 3 = 1: display page 7 (shadow screen at $C000)

    ld   a, (current_bank)
    or   %00001000           ; set bit 3: display shadow screen
    ld   bc, $7FFD
    out  (c), a
```

The trick for scrolling:

1. **Frame N:** The player sees the standard screen (page 5). Meanwhile, you draw the *next* frame's scrolled content into the shadow screen (page 7, at `$C000`).
2. **Frame N+1:** Flip the display to the shadow screen. The player now sees the freshly drawn frame with no tearing. Meanwhile, you start drawing frame N+2 into the now-hidden standard screen.

This double-buffering approach eliminates tearing completely and gives you a full frame (or more) to prepare each scrolled frame. The cost is that you need to maintain two complete screen states, and each "scroll" is actually a full redraw of the play area into the back buffer.

```z80
; Flip displayed screen and return back buffer address in HL
;
; screen_flag:  0 = showing page 5, drawing to page 7
;               1 = showing page 7, drawing to page 5
;
flip_screens:
    ld   a, (screen_flag)
    xor  1                   ; 4 T   toggle
    ld   (screen_flag), a

    ld   hl, $C000           ; assume drawing to page 7
    or   a
    jr   z, .show_page5

    ; Now showing page 7, draw to page 5
    ld   hl, $4000
    ld   a, (current_bank)
    or   %00001000           ; bit 3 set: display page 7
    jr   .do_flip

.show_page5:
    ld   a, (current_bank)
    and  %11110111           ; bit 3 clear: display page 5

.do_flip:
    ld   bc, $7FFD
    out  (c), a
    ld   (current_bank), a
    ret                      ; HL = back buffer address
```

### Shadow Screen Scrolling Strategy

With double-buffering, the scrolling approach changes:

**Instead of scrolling the live screen in place** (which causes tearing and must complete within one frame), you **redraw the play area from the tilemap** into the back buffer at the new scroll position. This is fundamentally different. You are not *moving* existing screen data -- you are *rendering fresh* from the map.

This is more work per frame (you redraw the whole play area, not just shift it), but it has significant advantages:

1. **No tearing.** The player never sees a half-scrolled screen.
2. **No edge-column shifting.** You render each tile at its correct sub-character offset directly.
3. **Flexible scroll speed.** You can scroll 1, 2, or 3 pixels per frame without changing the rendering logic.
4. **Simpler code.** A tile renderer is simpler than a combined shift-and-copy scroller.

The cost of a full play-area redraw from tiles depends on your tile renderer. With 20 x 20 tiles, each tile being 8 bytes (8 scanlines x 1 byte), and using LDI chains:

- 400 tiles x 8 bytes x 16 T per LDI = 51,200 T-states for data output.
- Plus tile address lookups and screen address calculations: ~20 T per tile x 400 = 8,000 T.
- **Total: ~59,200 T-states** = 82% of a frame.

This leaves 18% (~12,900 T-states) for sprites, game logic, and music. Tight but workable.

### Comparison: Scrolling Methods on ZX Spectrum

| Method | T-states/frame | % of frame | Visual quality | Notes |
|--------|---------------|------------|----------------|-------|
| Full pixel scroll (horizontal, 1px) | ~135,000 | 189% | Smooth | Impossible at 50fps |
| Full pixel scroll (vertical, 1px) | ~107,000 | 149% | Smooth | Impossible at 50fps |
| Attribute scroll only | ~17,000 | 24% | Jerky (8px jumps) | Very cheap |
| Combined (char + pixel edge) | ~10,000 avg, ~70,000 peak | 14%/98% | Smooth | Best single-buffer method |
| Shadow screen + tile redraw | ~59,000 | 82% | Smooth, tear-free | Requires 128K |
| Character scroll (8px jumps) | ~52,000--66,000 | 73--92% | Jerky | For scrolling text/status |

<!-- figure: ch17_scroll_costs -->
![Scrolling technique cost comparison](illustrations/output/ch17_scroll_costs.png)

---

## Scrolling Right (and the Direction Problem)

Everything above describes a leftward scroll (the player moves right, the world shifts left). What about scrolling right?

For attribute scrolling, reverse the LDIR direction. Copy bytes 0--30 to positions 1--31, right to left. LDIR copies forward (low to high addresses), so for a rightward scroll you need LDDR (copy backward):

```z80
; Scroll attributes right by 1 character column
;
scroll_attrs_right:
    ld   hl, $5ADE          ; source: last row, column 30
    ld   de, $5ADF          ; dest: last row, column 31
    ld   bc, 767            ; 768 - 1 bytes
    lddr                    ; 767*21 + 16 = 16,123 T
    ret
```

For pixel bit-shifting, a rightward scroll uses `RR (HL)` instead of `RL (HL)`, processing left to right:

```z80
; Scroll one pixel row RIGHT by 1 pixel
; HL points to byte 0 (leftmost)
;
    or   a                ; 4 T    clear carry
    rr   (hl)             ; 15 T   shift right, bit 0 -> carry
    inc  hl               ; 6 T
    rr   (hl)             ; 15 T   carry -> bit 7
    inc  hl               ; 6 T
    ; ... 32 bytes total ...
```

The per-byte cost is identical: 21 T-states. A rightward scroll costs the same as a leftward scroll. The combined method works in both directions with the same budget.

For bidirectional scrolling (the player can go left or right), you need two versions of the character-scroll and edge-shift routines, switched based on direction. Self-modifying code is useful here: before the scroll, patch the RL/RR opcode and the INC/DEC direction in the shift routine. This avoids a branch inside the inner loop (see Chapter 3 for the SMC pattern).

---

## Agon Light 2: Hardware Scrolling

The Agon Light 2's VDP (Video Display Processor) handles scrolling entirely differently from the Spectrum. Where the Spectrum programmer must move bytes manually, the Agon provides hardware-level support for scroll offsets and tilemaps.

### Hardware Scroll Offsets

The VDP supports a viewport offset for bitmap modes. By setting the scroll offset registers, you shift the entire displayed image without moving any pixel data. The eZ80 sends a VDP command via the serial link:

```z80
; Agon: set horizontal scroll offset
; VDU 23, 0, &C3, x_low, x_high
;
    ld   a, 23
    call vdu_write      ; VDU command prefix
    ld   a, 0
    call vdu_write
    ld   a, $C3         ; set scroll offset command
    call vdu_write
    ld   a, (scroll_x)
    call vdu_write      ; x offset low byte
    ld   a, (scroll_x+1)
    call vdu_write      ; x offset high byte
```

The hardware applies this offset when reading the framebuffer for display. No pixel data is moved, no CPU T-states are spent on shifting bytes, and the scroll is perfectly smooth at any speed. The CPU cost is just the serial communication overhead (a few hundred T-states for the VDU command sequence).

### Tilemap Scrolling

The VDP's tilemap mode provides native tile-based rendering. You define a set of tiles (8x8 or 16x16 pixel patterns), build a map array that references tile indices, and the hardware renders the map at display time. Scrolling is achieved by changing the tilemap's viewport offset:

```z80
; Agon: set tilemap scroll offset
; VDU 23, 27, <tilemap_scroll_command>, offset_x, offset_y
;
    ld   a, 23
    call vdu_write
    ld   a, 27
    call vdu_write
    ld   a, 14          ; set tilemap scroll offset
    call vdu_write
    ; ... send x and y offsets ...
```

The tilemap wraps around automatically. As the viewport scrolls past the edge of the map, the hardware wraps to the beginning (or you can update the edge column with new tile indices -- the ring-buffer column loading technique).

### Ring-Buffer Column Loading

For an infinitely scrolling level, the tilemap acts as a ring buffer. The map is wider than the screen by at least one column. As the player scrolls right:

1. The hardware scroll offset advances by 1 pixel per frame (or whatever speed you want).
2. When a new tile column is about to scroll into view, the eZ80 writes new tile indices into the column that just scrolled off the left edge.
3. The tilemap wraps, and the newly written column appears on the right.

```z80
; Ring-buffer column loading (Agon, conceptual)
;
; tilemap is 40 columns wide, screen shows 32
; scroll_col tracks which column is at the left edge
;
ring_buffer_load:
    ld   a, (scroll_col)
    add  a, 32              ; column about to appear on right
    and  39                  ; wrap to tilemap width (mod 40)
    ld   c, a               ; C = column index to update

    ; Load new tile data for this column from the level map
    ; (level_map is a wider array of tile indices)
    ld   hl, (level_ptr)     ; pointer into the level data
    ld   b, 20               ; 20 rows
.load_col:
    ld   a, (hl)             ; read tile index from level
    inc  hl
    ; Write tile index to tilemap at (C, row)
    call set_tilemap_cell    ; VDP command to set one cell
    djnz .load_col

    ld   (level_ptr), hl
    ret
```

The CPU work per frame is minimal: writing 20 tile indices via VDP commands, perhaps 2,000--3,000 T-states total. The rest of the frame is available for game logic. Compare this to the Spectrum's 59,000+ T-states for a tile-based scroll redraw. The Agon's hardware tilemap buys you roughly a 20x reduction in CPU cost for scrolling.

### Comparison: Spectrum vs. Agon Scrolling

| Aspect | ZX Spectrum | Agon Light 2 |
|--------|-------------|---------------|
| Scroll granularity | Software-limited; 1px possible but expensive | 1px native, zero CPU cost |
| CPU cost per frame | 10,000--135,000 T | 500--3,000 T |
| Tearing | Visible without double-buffering | None (VDP handles sync) |
| Direction change | Requires alternate routines or SMC | Change offset sign |
| Map size limit | Limited by RAM, no hardware support | Tilemap size limited by VDP memory |
| Colour per tile | 2 colours per 8x8 cell (attribute) | Full colour per pixel |

The contrast is stark. What the Spectrum programmer spends most of their frame budget on -- moving pixel data across a scrambled memory layout -- the Agon handles with a register write. This is not a criticism of either platform. It is a demonstration of how hardware design choices propagate through every level of the software. The Spectrum's constraints forced the development of the combined scroll method, tile engines, and shadow-screen tricks. The Agon's constraints are elsewhere (serial VDP latency, command overhead for complex scenes).

---

## Practical: Horizontal Side-Scrolling Level

### Spectrum Version: Combined Character + Pixel Scroll

Build a horizontal side-scroller with a 20x20-character play area that scrolls smoothly at 1 pixel per frame. The level data is a tilemap stored in a memory bank.

Here is the complete structure:

```z80
; Side-scroller engine — ZX Spectrum 128K
; Uses combined character + pixel method with shadow screen.
;
    ORG $8000

PLAY_X      EQU 2           ; play area starts at column 2
PLAY_Y      EQU 2           ; play area starts at char row 2
PLAY_W      EQU 20          ; play area width in characters
PLAY_H      EQU 20          ; play area height in characters

scroll_pixel_x:   DB 0      ; pixel offset 0-7
scroll_tile_x:    DW 0      ; tile column at left edge
screen_flag:      DB 0      ; which screen is visible
current_bank:     DB 0      ; current $7FFD value

; --- Main loop ---
main:
    halt                     ; 4 T   sync to frame

    ; Advance scroll
    ld   a, (scroll_pixel_x) ; 13 T
    inc  a                   ; 4 T
    cp   8                   ; 7 T
    jr   c, .pixel_only      ; 12/7 T

    ; Character scroll frame
    xor  a
    ld   (scroll_pixel_x), a

    ; Advance tile position
    ld   hl, (scroll_tile_x)
    inc  hl
    ld   (scroll_tile_x), hl

    ; Get back buffer address
    call get_back_buffer     ; HL = $4000 or $C000

    ; Redraw full play area from tilemap into back buffer
    call render_play_area    ; ~50,000 T

    ; Flip screens
    call flip_screens        ; ~30 T

    jr   .frame_done

.pixel_only:
    ld   (scroll_pixel_x), a

    ; Shift edge columns in current (non-displayed) buffer
    call get_back_buffer
    call shift_edge_columns  ; ~9,600 T

    call flip_screens

.frame_done:
    call update_player       ; ~2,000 T
    call draw_sprites        ; ~5,000 T
    call play_music          ; ~3,000 T (IM2 handler)

    jr   main

; --- Render full play area from tilemap ---
; Input: HL = base address of target screen ($4000 or $C000)
;
render_play_area:
    ; For each tile in the play area:
    ;   Look up tile index from tilemap
    ;   Copy 8 bytes of tile data to screen, navigating interleave
    ;
    ; 20 columns x 20 rows = 400 tiles
    ; Each tile: 8 scan lines x 1 byte = 8 LDI operations
    ; Per tile: lookup (20 T) + 8 x (LDI 16 T + INC H 4 T) = 180 T
    ; Total: 400 x 180 = 72,000 T
    ;
    ; (Actual implementation uses PUSH tricks and
    ;  pre-computed screen address tables for ~55,000 T)
    ret

; --- Shift edge columns by 1 pixel ---
; Shifts the 2 rightmost columns of the play area left by 1 pixel
;
shift_edge_columns:
    ; For each of 160 pixel rows in the play area:
    ;   Navigate to the correct screen address
    ;   RL (HL) on the 2 edge bytes, right to left
    ;
    ; Per row: 40 T (2 bytes shifted) + 20 T (navigation)
    ; Total: 160 x 60 = 9,600 T
    ret
```

### Agon Version: Hardware Tilemap Scrolling

The Agon version is dramatically simpler. The main loop calls `vsync`, increments a 16-bit scroll offset, sends it to the VDP via the `set_scroll_offset` routine (a handful of `vdu_write` calls), and every 8 pixels calls `ring_buffer_load` to update one column of tile indices. The entire scroll costs under 3,000 T-states per frame, leaving 365,000+ T-states for game logic, AI, physics, and rendering. The Spectrum version is a careful exercise in cycle-counting where every technique from Chapters 2 and 3 comes together to achieve what the Agon does with a hardware register.

---

## Vertical + Horizontal: Combined Scrolling

Some games scroll in both directions simultaneously. On the Spectrum, apply the combined method to both axes: character scroll + pixel offset (0--7) for each. The character scroll in each direction happens once every 8 frames. Both coinciding on the same frame is a 1/64 probability (about every 1.3 seconds) -- either accept one dropped frame or split the work. The per-frame edge-shifting cost for both axes: horizontal edge columns (~9,600 T) + vertical edge rows (~6,400 T) = ~16,000 T = 22% of the frame. Manageable.

---

## Optimisation Tips

### 1. Use a Screen Address Lookup Table

Pre-compute a table of 192 screen addresses (one per pixel row) in RAM. Cost: 384 bytes. Benefit: a 16-bit table lookup (about 30 T-states) replaces the bit-shuffling address calculation (91 T-states).

### 2. Scroll Only What Is Visible

If sprites cover part of the play area, you can skip scrolling the rows behind opaque sprites. Track which rows need scrolling with a dirty-row bitmap. This optimisation pays off when sprites cover a significant fraction of the play area.

### 3. Use PUSH for the Character Scroll

For the character-level pixel data scroll (copying 19 bytes left per scanline), the PUSH trick works well. Set SP to the end of each scanline's play area, POP 10 bytes, shift the register contents, and PUSH them back one byte offset. This is complex to set up but reduces the per-scanline cost by 30--40%.

### 4. Split the Character Scroll Across Frames

If the character scroll (every 8th frame) is too expensive for one frame, split it: scroll the top half of the play area on frame N and the bottom half on frame N+1. The visual artefact (the top half shifts 1 frame before the bottom) is barely noticeable at 50fps.

### 5. Palette and Attribute Tricks

For attribute-only scrolling (no pixel data involved), consider using FLASH or BRIGHT changes to create the illusion of motion within a static pixel grid. A rotating set of attribute colours on character-aligned tiles can simulate flow, water, or conveyor belts without moving any pixel data at all.

---

## Summary

- **Full-screen pixel scrolling on the ZX Spectrum is impossible at 50fps.** Horizontal pixel scrolling costs ~135,000 T-states for 192 rows (189% of the frame budget). Vertical costs ~107,000 T-states (149%). The interleaved memory layout adds complexity to vertical scrolling, and the lack of a barrel shifter makes horizontal scrolling inherently expensive.

- **Attribute scrolling is cheap** at ~17,000 T-states (24% of frame), but moves in coarse 8-pixel jumps.

- **The combined method** is what real games use: character-level scrolls (every 8 frames) plus per-frame pixel-shifting of the 1--2 edge columns. Average per-frame cost is under 10,000 T-states. The spike on character-scroll frames (~70,000 T) can be managed with the shadow screen or by splitting across frames.

- **The shadow screen** (128K, page 7) provides tear-free double buffering. Draw the next frame into the back buffer, then flip the display. This changes the scrolling strategy from "shift existing data" to "redraw from tilemap," which is conceptually simpler and eliminates tearing.

- **Horizontal scrolling direction** does not change the cost. Rightward scrolling uses `RR (HL)` instead of `RL (HL)`, left-to-right instead of right-to-left, at the same 21 T-states per byte.

- **Vertical pixel scrolling** is complicated by the Spectrum's interleaved screen layout. Moving one pixel row down means navigating the `010TTSSS LLLCCCCC` address structure, with different pointer adjustments at character-cell and third boundaries. The split-counter approach from Chapter 2 is essential.

- **The Agon Light 2** provides hardware scroll offsets and tilemap rendering that reduce the CPU cost of scrolling to a few VDP commands per frame (~500--3,000 T-states). Ring-buffer column loading keeps the tilemap updated as new terrain scrolls into view. What the Spectrum programmer builds in 70,000 T-states, the Agon handles with a register write.

- **Key techniques from earlier chapters** are essential here: the interleaved screen layout and split-counter navigation (Chapter 2), LDI chains and PUSH tricks for fast data movement (Chapter 3), and self-modifying code for direction-switchable scroll routines (Chapter 3).

---

> **Sources:** Introspec "Eshchyo raz pro DOWN_HL" (Hype, 2020) for interleaved screen navigation; Introspec "GO WEST Part 1" (Hype, 2015) for contended memory costs; DenisGrachev "Ringo Render 64x48" (Hype, 2022) for half-character displacement scrolling; ZX Spectrum 128K Technical Manual for port `$7FFD` and shadow screen; Agon Light 2 VDP documentation for tilemap and scroll offset commands.
