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

**Action needed**: Verify and fix in Appendix A.

### 2. pixel_addr routine (p.464) — incomplete

> Missing setting of upper 3 bits in L to Y:5:3

**Action needed**: Check and fix pixel_addr in Appendix A.

### 3. Quick Cost Comparisons — confusing

> "Copy 1 byte to mem" — the "slow way" writes to HL and is actually faster.
> The two approaches are too different to compare without explanation.
> Looks more like set/fill than copy.

**Action needed**: Clarify or relabel in Appendix A.

### 4. sjasmplus --syntax=abf

> Would be happier if --syntax=abf was more promoted. More reasonable default
> for people starting with sjasmplus.

**Action needed**: Consider mentioning in Appendix D (dev setup).

### 5. VSCode problemMatcher regex

> Current regex doesn't catch id-warnings like `warning[out0]`.
> Suggested fix: `^(.*)\\((\\d+)\\):\\s+(error|warning)[^:]*:\\s+(.*)$`

**Action needed**: Check and fix in Appendix D.

### 6. RLE routine in compression chapter

> RLE routine offered for 256B intros is unnecessarily long and has
> wrong T-states count.

**Action needed**: Verify RLE routine in Ch.14 and Appendix C.

### 7. Z80N instructions (Appendix F)

> T-state counts "fly up and down" — possible first draft quality.

**Action needed**: Full audit of Appendix F T-states.
