# Ped7g Discord Review Feedback (2026-02-25)

Source: Czech/Slovak ZX Spectrum Discord
Language: Slovak

## upkr compression

See `upkr_compression.md` in this folder. Key point: sweet spot 512-2048 compressed bytes,
above that too slow for 3.5MHz. Not suitable for 32KB demos.

**Status**: Added to packbench.py packer profiles and mentioned in Ch.14/Appendix C.

## General readiness question

> судя по скорости релизов, мне кажется, что это пишет AI, а ты только «рулишь». Так что
> если ты собираешься некоторые главы ещё несколько раз основательно переделывать и проверять,
> то мне кажется бессмысленным сейчас стараться делать исправления и рисковать, что они снова
> пропадут при следующем редактировании.

> в целом выглядит интересно... но пока я бы обозначил это как WIP/draft, потому что словами
> Introspec'а — «Z80 they still don't know» — и это видно по результату.

**Response**: Very early stages, book is < 1 week old. Opus accelerates prototyping but
human review needed. After topic stabilization, human editors will be assigned per chapter.
Feedback won't be lost — goes into feedback/corrections folder as guardrails.

## Appendix A specific issues

### 1. Shadow registers warning — INCORRECT claim

> Warning: The Spectrum ROM interrupt handler (IM1) uses the shadow registers.
> If interrupts are enabled, EXX/EX AF,AF' data will be corrupted on every interrupt.

Ped7g says: only IY is important (must point to sysvars or safe memory),
shadow registers are preserved by ROM ISR.

**Status**: ✅ Fixed (2026-02-26). Warning now correctly says IY is the concern,
shadow registers are safe. Appendix A line ~447.

### 2. pixel_addr routine (p.464) — incomplete

> Missing setting of upper 3 bits in L to Y:5:3

**Status**: ✅ Fixed (2026-02-26). Added Y[5:3] → L[7:5] computation using
AND $38 + RLCA + RLCA, then OR with X/8 column bits. T-state cost updated to ~107T.

### 3. Quick Cost Comparisons — confusing

> "Copy 1 byte to mem" — the "slow way" writes to HL and is actually faster.
> The two approaches are too different to compare without explanation.
> Looks more like set/fill than copy.

**Status**: ✅ Fixed (2026-02-26). Row relabeled to "Copy 1 byte (HL)→(DE)" with
correct slow way: `LD A,(HL)`+`LD (DE),A`+`INC HL`+`INC DE` (26T, 4B) vs LDI (16T, 2B).

### 4. sjasmplus --syntax=abf

> Would be happier if --syntax=abf was more promoted. More reasonable default
> for people starting with sjasmplus.

**Status**: ✅ Added (2026-02-26). Listed in Appendix D Key Flags table with
description of what it enables.

### 5. VSCode problemMatcher regex

> Current regex doesn't catch id-warnings like `warning[out0]`.
> Suggested fix: `^(.*)\\((\\d+)\\):\\s+(error|warning)[^:]*:\\s+(.*)$`

**Status**: ✅ Fixed (2026-02-26). Applied Ped7g's suggested regex.

### 6. RLE routine in compression chapter

> RLE routine offered for 256B intros is unnecessarily long and has
> wrong T-states count.

**Status**: ✅ Fixed (2026-02-26). Code size corrected from "23 bytes" / "under 30 bytes"
to correct "12 bytes". T-state annotation clarified with per-pair overhead note.
Added transposition tip for improving RLE compression with 2D data.

### 7. Z80N instructions (Appendix F)

> T-state counts "fly up and down" — possible first draft quality.

**Action needed**: Full audit of Appendix F T-states against official Next documentation.

---

## RLE depacker for 256B intros — detailed follow-up (2026-02-27)

Ped7g clarifies his earlier RLE comment wasn't just "a feeling" that RLE is big for 256 bytes,
but that the code is genuinely long and complex. Provides a complete working example.

### Minimal self-modifying RLE depacker (9 bytes core)

```z80
target:
  ds <size needed + stack>
intro_data:
  dw target
  db value, rep
  ..
  db 0x18,0 ; must reach `ld (hl),c` and overwrite it to create opcode `18 23` -> `jr rle_loop_inner+0x25`
rle_start:
  ld sp,intro_data
  pop hl
rle_loop_outer:
  pop bc
rle_loop_inner:
  ld (hl),c
  inc hl
  djnz rle_loop_inner
  jr rle_loop_outer
; 0x1F bytes to fill with other helper code
  ds 0x1F
intro_start:
  assert $ == rle_loop_inner + 2 + 0x23 ; make sure we are at exiting `jr` target
  ...
```

### Byte count analysis

- Book's "minimal RLE decompressor": 13 bytes (but HL+DE pre-set, needs outer call)
- Ped7g's skeleton: `db 0x18,0` (jr in data) + `rle_loop_outer` code → 2+1+1+1+2+2 = **9 bytes** core
- SP+HL setup adds +6 → **15 bytes total** for self-contained RLE decoder
- Awkward 31-byte window that must be jumped over and filled with code; worst case +4 bytes (2x jr)

### Complete working example (120 bytes .bin)

```z80
    DEVICE ZXSPECTRUM48, $8000

target  EQU $4000
  ; start RLE with filling screen
    ORG $5B00       ; loading address of intro -> print buffer
intro_data:
    dw target
; bitmap stripes every other line
    .(4*3) db $AA, 0, $00, 0
    db $43, 32*2, $44, 32*4, $45, 32*3, $46, 32*2, $47, 32*2
    db $46, 32*2, $45, 32*3, $44, 32*4, $43, 32*2
    db 0x18,0 ; must reach `ld (hl),c` and overwrite it to create opcode `18 23` -> `jr rle_loop_inner+0x25`
rle_start:
  ei  ; simulate BASIC environment after LOAD including enabled interrupts during depack
  ld sp,intro_data
  pop hl
rle_loop_outer:
  pop bc
rle_loop_inner:
  ld (hl),c
  inc hl
  djnz rle_loop_inner
  jr rle_loop_outer
; 0x1F bytes to fill with other helper code
  ds 0x1F
intro_start:
  assert $ == rle_loop_inner + 2 + 0x23 ; make sure we are at exiting `jr` target
    inc a
    and 7
    out (254),a
    jr intro_start

    SAVESNA "temp.sna", rle_start
    SAVEBIN "temp.bin", intro_data, $-intro_data    ; real intro binary
```

Result: 120 bytes .bin (including 31 bytes padding that could contain code).
Screenshot: colored stripes filling screen via attribute values.

### Complexity notes for the book

Ped7g notes this is harder to describe in a book because:
1. Part of the data IS the mechanism (the `db 0x18,0` overwrites the depack loop to create a `jr` exit)
2. User must understand the buffer must end "in the code" to overwrite the depack loop
3. Advanced users will immediately ask "wait, he changes SP, what about interrupts?" —
   the interrupt does occasionally overwrite something, but only data already consumed,
   so the stack remains functional for the intro code itself

### Permission

Asked to use in book with credit — awaiting response.

**Status**: Reviewing for inclusion in compression chapter. Great example of self-modifying
code technique for size-optimized intros.
