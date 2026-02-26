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
