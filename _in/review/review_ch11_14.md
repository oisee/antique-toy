# Technical Review: Chapters 11-14

Reviewer: Claude Opus 4.6
Date: 2026-02-24
Scope: Technical accuracy errors and AI-smell passages in ch11-ch14 drafts.

---

## Chapter 11: Sound Architecture -- AY, TurboSound, and Triple AY

### TECHNICAL ERRORS

**[T11-1] Mixer value $28 is wrong -- noise B, not noise C (HIGH)**
File: `/Users/alice/dev/antique-toy/chapters/ch11-sound/draft.md`, lines 136-142

```
; Mixer: tone A on, tone B on, tone C on, noise C on
; Binary: 10 0 000 = noise C on + all tones on
; = $28
ld   a, R_MIXER
ld   e, $28
call ay_write
```

$28 = 0b00101000. Bits 5-0 = 101_000. Decoding: Noise C=1(OFF), Noise B=0(ON), Noise A=1(OFF), Tone C=0(ON), Tone B=0(ON), Tone A=0(ON). So $28 enables all three tones plus **noise B**, not noise C. The comment and the binary annotation are both wrong. For "all tones on + noise C on," the correct value is $18 (binary 011_000: Noise C=0(ON), Noise B=1(OFF), Noise A=1(OFF), all tones on).

**[T11-2] Natural tuning table: F2 mod 16 is 8, not 0 (MEDIUM)**
File: `/Users/alice/dev/antique-toy/chapters/ch11-sound/draft.md`, line 374

```
| F2   | 1080   | 0      | 67.5 -> 68            | ~   |
```

1080 mod 16 = 8, not 0. Calculation: 67 * 16 = 1072; 1080 - 1072 = 8. The table entry is self-contradictory: if mod 16 were 0, then 1080/16 would be an integer, but the same row shows 67.5 (non-integer). The "Clean?" column should be "No," not "~". F2 does not divide cleanly.

**[T11-3] Natural tuning table: A#2 mod 16 is 10, not 2 (MEDIUM)**
File: `/Users/alice/dev/antique-toy/chapters/ch11-sound/draft.md`, line 379

```
| A#2  |  810   | 2      | 50.6 -> 51            | No  |
```

810 mod 16 = 10. Calculation: 50 * 16 = 800; 810 - 800 = 10. The stated value of 2 is wrong. The "No" in the Clean column and the non-integer envelope value are correct, only the mod 16 column is wrong.

**[T11-4] TurboSound register blast cost significantly understated (MEDIUM)**
File: `/Users/alice/dev/antique-toy/chapters/ch11-sound/draft.md`, line 555

```
Total cost: about 28 OUT instructions, roughly 400 T-states.
```

28 OUT (C),r instructions at 12T each = 336T for the OUTs alone. But a register blast also requires loading register numbers (14 * LD A,n = 98T), loading data from buffer (14 * LD r,(HL) = 98T), port high-byte changes (14 * LD B,$FF + 14 * LD B,$BF = 196T), and pointer increments (14 * INC HL = 84T). Realistic minimum total for 14 register writes to one AY chip: ~812T. For two chips: ~1624T. The stated "roughly 400 T-states" is approximately half the actual cost for one chip and a quarter of the cost for two chips.

**[T11-5] Note period values inconsistent between chapter text and example file (LOW)**
File: `/Users/alice/dev/antique-toy/chapters/ch11-sound/draft.md`, lines 74-88 vs `/Users/alice/dev/antique-toy/chapters/ch11-sound/examples/ay_test.a80`, lines 29-36

The chapter's note table (line 76) gives C4 period = 424, but `ay_test.a80` line 29 defines `NOTE_C4 EQU 426`. Similar 1-2 unit discrepancies for every note: D4 (378 vs 379), E4 (337 vs 338), F4 (318 vs 319), G4 (283 vs 284), A4 (252 vs 253), C5 (212 vs 213). Both sets are reasonable roundings for a ~1.7734 MHz AY clock, but the chapter text and its own companion example disagree. One set should be authoritative.

### AI SMELL

**[A11-1] Unnecessary restatement in summary (LOW)**
File: `/Users/alice/dev/antique-toy/chapters/ch11-sound/draft.md`, line 934

```
The AY-3-8910 is deceptively simple: 14 registers, 3 channels, basic waveforms.
But the gap between "simple" and "limited" is filled by technique. Arpeggios fake
chords. Envelope abuse creates bass. Noise shaping synthesizes drums. Ornaments
breathe life into static tones.
```

"Deceptively simple" is borderline LLM-voice. The rest of the summary paragraph is fine -- punchy, specific -- but "deceptively simple" is a stock phrase. Consider just cutting those two words.

**[A11-2] "Genuinely rich arrangements" (LOW)**
File: `/Users/alice/dev/antique-toy/chapters/ch11-sound/draft.md`, line 585

```
This is enough for genuinely rich arrangements.
```

"Genuinely rich" is vague superlative padding. The specific claims that follow (dedicated SFX channel, independent noise generators, chords without arpeggios) carry the point without the qualifier.

**[A11-3] Beeper sidebar: "among the most remarkable engineering achievements in 8-bit computing" (LOW)**
File: `/Users/alice/dev/antique-toy/chapters/ch11-sound/draft.md`, line 893

```
These are among the most remarkable engineering achievements in 8-bit computing.
```

Hyperbolic. The preceding examples (ZX-16 with 16-channel polyphony, Rain running 9-channel beeper + visuals) do speak for themselves. The sentence adds nothing that the examples don't already demonstrate.

---

## Chapter 12: Digital Drums and Music Sync

### TECHNICAL ERRORS

**[T12-1] INC HL is 6T, not standard -- verify context (LOW)**
File: `/Users/alice/dev/antique-toy/chapters/ch12-music-sync/draft.md`, line 68

```
    inc  hl                   ; 6 T  - advance pointer
```

INC rr (16-bit increment) is 6T on the Z80. This is correct. No error here -- included for completeness of the audit. The other T-state annotations in this block are also correct: LD A,(HL)=7T, LD B,n=7T, OUT (C),A=12T.

**[T12-2] DJNZ in sample loop: misleading cycle annotation (LOW)**
File: `/Users/alice/dev/antique-toy/chapters/ch12-music-sync/draft.md`, line 72

```
    djnz .sample_loop         ; 13 T (approx 45 T per sample)
```

DJNZ is 13T when taken, 8T when not taken. The comment says "13 T" which is correct for the taken case (all iterations except the last). The "approx 45 T per sample" is 7+6+7+12+13 = 45, consistent. However, DJNZ also decrements B, so the loop counter is B. The setup at line 57 says `ld b, 0` meaning B=0, which on a DJNZ loop means 256 iterations (B wraps 0->255->...->1->0). But then at line 63 B is overwritten with a register select value `ld a, 8 : ld bc, $FFFD : out (c), a` (which destroys B), followed by `ld c, $FD`. Then at line 69, `ld b, $BF` is inside the loop, so B is set to $BF every iteration. The DJNZ at line 72 then decrements this, so B goes $BF->$BE->...->$01->$00 and exits. That means the loop runs $BF = 191 iterations, not 256. The initial `ld b, 0` at line 57 is dead code. This isn't a T-state error per se, but the loop iteration count is confusing: the code as written plays 191 samples per pass, not 256. The comment at line 57 says "256 samples per loop pass" which is wrong given the inner `ld b, $BF`.

**[T12-3] play_kick_drum clobbers BC used for port (LOW)**
File: `/Users/alice/dev/antique-toy/chapters/ch12-music-sync/draft.md`, lines 57-72

The code at line 57 does `ld b, 0` and `ld c, $FD`, then at lines 62-63 does `ld a, 8 : ld bc, $FFFD : out (c), a`, which overwrites both B and C. Then at line 64, `ld c, $FD` restores C. Inside the loop, `ld b, $BF` sets B for the data write port. But the DJNZ at line 72 then decrements B from $BF. This means B is $BF at the OUT, then DJNZ makes it $BE, and the next iteration's `ld b, $BF` resets it. So the OUT port is always $BFFD (B=$BF, C=$FD). This is correct functionally, but the comment "256 samples per loop pass" is misleading as noted above.

### AI SMELL

**[A12-1] Overwrought opening paragraph (MEDIUM)**
File: `/Users/alice/dev/antique-toy/chapters/ch12-music-sync/draft.md`, lines 8-10

```
A demo is not a slideshow of effects. A demo is a performance -- one where every
visual event lands on the beat, every transition breathes with the music, and the
audience never suspects that behind the curtain, a 3.5MHz processor is juggling
half a dozen competing demands with no operating system, no threads, and no safety net.
```

This reads like a keynote speech. "Behind the curtain," "no safety net" -- theatrical padding. The reader already knows what a demo is by Chapter 12. Compare to the terse, direct opening of Chapter 14 ("The ZX Spectrum 128K has 128 kilobytes of RAM. That sounds generous until you start subtracting...") which drops the reader immediately into the problem.

**[A12-2] "Startlingly convincing" (LOW)**
File: `/Users/alice/dev/antique-toy/chapters/ch12-music-sync/draft.md`, line 104

```
The result is startlingly convincing.
```

Editorializing. The reader can judge from the technical description. "Startlingly" is an enthusiasm marker that adds nothing.

**[A12-3] "The insight is deceptively simple" (LOW)**
File: `/Users/alice/dev/antique-toy/chapters/ch12-music-sync/draft.md`, line 295

```
The insight is deceptively simple: use the right tool for the job.
```

"Deceptively simple" is stock phrasing. Just say "The insight: use the right tool for the job." Or cut the sentence entirely -- the rest of the paragraph explains the idea.

**[A12-4] Redundant summary-then-repeat structure in closing paragraphs (LOW)**
File: `/Users/alice/dev/antique-toy/chapters/ch12-music-sync/draft.md`, lines 629-643

The summary at lines 629-641 restates every section heading with a one-line gloss, then lines 641-643 adds a "where we've been, where we're going" transition. Both are standard LLM chapter-end patterns. The bulleted summary at 634-639 is useful; the framing paragraph at 629-633 ("This chapter was not about any single effect or technique. It was about architecture...") is padding. The reader just read the chapter; they know what it was about.

---

## Chapter 13: The Craft of Size-Coding

### TECHNICAL ERRORS

**[T13-1] "RST $10 costs 1 byte. CALL $0010 does the same thing in 3 bytes" -- RST cycles differ (LOW)**
File: `/Users/alice/dev/antique-toy/chapters/ch13-sizecoding/draft.md`, line 38

The size claim is correct (RST = 1 byte, CALL = 3 bytes). However, the chapter does not mention that RST n takes 11T while CALL nn takes 17T. In a chapter focused on size this omission is deliberate and acceptable, but readers doing hybrid size/speed optimization would benefit from knowing RST is also 6T faster.

**[T13-2] sfx_pickup table in ch11 has editing artifact (MEDIUM)**
File: `/Users/alice/dev/antique-toy/chapters/ch11-sound/draft.md`, lines 847-857

```z80
sfx_pickup:
    DB $D4,0, 0, 14, 0    ; frame 0: C5
    DB $A8,0, 0, 14, 0    ; frame 1: C4 (wrong dir? no:)
    ; Actually, let's go up:
    DB $FC,0, 0, 14, 0    ; frame 0: A4
    DB $D4,0, 0, 13, 0    ; frame 1: C5
    ...
```

This reads like an unfinished draft edit. The first two DB lines are followed by a comment admitting the direction is wrong, then a new set of values starts. The "Actually, let's go up:" comment and the false-start data should be removed. As-is, the sfx_pickup table has 8 data entries (2 wrong + 6 correct) before the end marker. The SFX engine would play all 8, including the discarded "wrong direction" frames, producing a garbled sound.

(Note: This is in ch11 but was missed in the ch11 section above; including it here where it was caught during cross-review.)

### AI SMELL

**[A13-1] "borders on magic" (LOW)**
File: `/Users/alice/dev/antique-toy/chapters/ch13-sizecoding/draft.md`, line 8

```
A 256-byte intro that fills the screen with animated patterns and plays a
recognisable melody is a form of compression so extreme it borders on magic.
```

"Borders on magic" is LLM enthusiasm. The preceding description of the 256-byte constraint already conveys the impression of difficulty. Cut "it borders on magic" or replace with something concrete.

**[A13-2] "unlike any other feeling in programming" (LOW)**
File: `/Users/alice/dev/antique-toy/chapters/ch13-sizecoding/draft.md`, line 441

```
The satisfaction of fitting a coherent audiovisual experience into 256 bytes --
of solving the puzzle -- is real and specific and unlike any other feeling in
programming.
```

This is subjective editorializing. The UriS quote at the chapter opening ("It was like playing puzzle-like games") makes the same point more credibly because it comes from a practitioner. The author's endorsement is redundant.

**[A13-3] Section 13.10 "Size-Coding as Art" -- mostly padding (MEDIUM)**
File: `/Users/alice/dev/antique-toy/chapters/ch13-sizecoding/draft.md`, lines 542-551

The entire section 13.10 is a philosophical reflection that restates what the chapter already demonstrated. Every sentence in this section is an opinion or restatement rather than new information. "The craft is the point. The constraint is the canvas." is motivational-poster territory. The chapter is strong on technical content; this section dilutes the ending. Consider cutting it entirely or folding the one concrete observation (the BBB/LPRINT connection) into section 13.4.

---

## Chapter 14: Compression -- More Data in Less Space

### TECHNICAL ERRORS

**[T14-1] ZX0 decompressor claimed as "roughly 70 bytes" but earlier said "69 bytes" for ZX7 (LOW)**
File: `/Users/alice/dev/antique-toy/chapters/ch14-compression/draft.md`, lines 57 and 129

Line 57: "ZX7 ... **69 bytes** ... Tiny decompressor"
Line 129: "ZX0 ... with a decompressor that stays in the 70-byte range"
Line 163: "At roughly 70 bytes, the entire decompressor..."

The text variously says ZX0 is "~70 bytes" and ZX7 is "69 bytes." These are different tools. The exact sizes depend on the specific Z80 implementation variant (standard, turbo, back-to-front, etc.). The text is not wrong per se, but the imprecision around "69," "~70," and "69-70 bytes" across multiple references could confuse a reader into thinking ZX0 and ZX7 have the same decompressor. Clarify which size belongs to which tool, ideally with exact byte counts for the specific variants referenced.

**[T14-2] "4,096 bytes total" budget arithmetic doesn't add up cleanly (LOW)**
File: `/Users/alice/dev/antique-toy/chapters/ch14-compression/draft.md`, line 296

```
4K intro: 4,096 bytes total. ZX0 decompressor: ~70 bytes. Engine + music + effects:
~2,400 bytes. That leaves ~1,626 bytes for compressed data, which decompress to
~3,127 bytes of raw assets.
```

The "4,096 bytes total" is the file size limit. The file consists of an uncompressed decompressor stub (70 bytes) plus compressed payload (~4026 bytes max). But then the text says "Engine + music + effects: ~2,400 bytes" -- this 2,400 bytes is presumably the *uncompressed* size of the code, which gets packed into the compressed payload. The budget math mixes compressed and uncompressed numbers: 70 + 2400 + 1626 = 4096, but 2400 is uncompressed code and 1626 is compressed data. The intended meaning is probably: "4096 bytes total file. 70 bytes decompressor stub. ~4026 bytes of compressed payload, which decompresses to code (~2400 bytes) + data (~3127 bytes) = ~5527 bytes." The current wording reads as if all three numbers add to 4096 in the same domain. Needs clarification.

### AI SMELL

**[A14-1] "There is no universally 'best' compressor" truism (LOW)**
File: `/Users/alice/dev/antique-toy/chapters/ch14-compression/draft.md`, line 107

```
There is no universally "best" compressor. There is only the best compressor for
your specific constraints.
```

Generic wisdom. The preceding analysis (the Pareto frontier discussion, the specific tradeoff numbers) already makes this point concretely. The explicit statement adds nothing.

**[A14-2] Closing flourish "Then move on to the hard part" (LOW)**
File: `/Users/alice/dev/antique-toy/chapters/ch14-compression/draft.md`, line 319

```
Choose the compressor that fits your constraints. Then move on to the hard part ---
making something worth compressing.
```

Pithy sign-off attempting profundity. Reads as an LLM trying to end on an inspirational note. The cheat-sheet table is a strong ending by itself; the closing quip weakens it.

---

## Cross-Chapter Issues

**[X-1] Ch12 references "Chapter 9" for plasma but the chapter directory is ch09-... (LOW)**

The references to "Chapter 9" in ch12 lines 389, 579, 615 and "Chapter 2" in ch13 line 194 appear to be correct based on the directory structure (`ch09-*`, `ch02-*`). No cross-reference errors found.

**[X-2] Ch11 beeper sidebar says "approximately 30 distinct beeper engines" (LOW)**
File: `/Users/alice/dev/antique-toy/chapters/ch11-sound/draft.md`, line 885

```
Between 2010 and 2015, Shiru (Shiru Otaku) cataloged approximately 30 distinct
beeper engines
```

Shiru's actual beeper engine catalog covers engines from across the Spectrum's history, not just 2010-2015. The catalog was *published* around that period, but the engines themselves span decades. The phrasing "between 2010 and 2015, Shiru... cataloged" is ambiguous -- it could mean Shiru did the cataloging work during 2010-2015 (plausible) or that the engines were created during that period (incorrect). Consider rephrasing for clarity.

---

## Summary of Findings

### By Severity

| Severity | Count | IDs |
|----------|-------|-----|
| HIGH | 1 | T11-1 |
| MEDIUM | 5 | T11-2, T11-3, T11-4, T13-2, A13-3 |
| LOW | 14 | T11-5, T12-1, T12-2, T12-3, T13-1, T14-1, T14-2, A11-1, A11-2, A11-3, A12-1, A12-2, A12-3, A12-4, A13-1, A13-2, A14-1, A14-2, X-2 |

### By Type

| Type | Count |
|------|-------|
| Technical accuracy | 10 |
| AI smell | 9 |
| Cross-chapter | 1 |

### Priority Fixes

1. **T11-1**: Fix mixer value $28 or its comment. If the intent is noise C + all tones, use $18. If $28 is intended, change comment to "noise B on."
2. **T13-2**: Remove the false-start entries from sfx_pickup table in ch11.
3. **T11-2, T11-3**: Fix the F2 and A#2 mod 16 values in the natural tuning table.
4. **T11-4**: Correct the TurboSound register blast cost estimate (400T -> ~800-1600T depending on implementation).
5. **A13-3, A12-1**: Consider trimming or cutting the padding sections identified as AI smell.
