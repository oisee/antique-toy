# Technical Review: Chapters 6-10

Reviewer: Claude Opus 4.6
Date: 2026-02-24
Scope: Technical accuracy + AI smell

---

## Chapter 6: The Sphere (ch06-sphere/draft.md)

### Technical Accuracy

**[T6-1] MEDIUM — Summary reverses causation between Illusion and Spectrum Expert articles**
File: `/Users/alice/dev/antique-toy/chapters/ch06-sphere/draft.md`, line 288
> "Dark wrote the building-block algorithms in Spectrum Expert (1997) and applied them in Illusion (1996)."

Illusion was released at ENLiGHT'96 (1996). The Spectrum Expert articles were published in 1997. The demo came first; the articles came after. The phrasing "wrote... and applied them" implies the articles preceded the demo. The body text on lines 127-128 gets the timeline right. The summary should say something like "applied techniques in Illusion (1996) and later documented them in Spectrum Expert (1997)."

**[T6-2] LOW — Ambiguous formula derivation in T-state counting section**
File: `/Users/alice/dev/antique-toy/chapters/ch06-sphere/draft.md`, lines 98-107
The section attempts to verify Introspec's "101 + 32x" formula by computing the fixed cost as 8 x 15 = 120 T-states, then finds 120 > 101, and says "the overhead beyond the raw pixel sampling accounts for roughly 101 - 120 = ... which means the base figure already includes the output instructions and some of the pixel work is interleaved differently than the naive count suggests."

This reads like the author realized the arithmetic didn't work out and hand-waved through the discrepancy instead of resolving it. The formula is Introspec's and presumably correct, but the verification attempt muddles rather than clarifies. Either verify it properly (show the actual instruction breakdown that yields 101) or present Introspec's formula as measured rather than derived.

### AI Smell

**[A6-1] LOW — Rhetorical buildup with no technical payload**
File: `/Users/alice/dev/antique-toy/chapters/ch06-sphere/draft.md`, line 8
> "No blitter. No GPU. No co-processor. Just a Z80, 48 kilobytes of contiguous RAM, and whatever a twenty-year-old coder named Dark could squeeze out of them."

The tricolon "No blitter. No GPU. No co-processor." is dramatic writing aimed at a general audience. Any reader of a Z80 demoscene book already knows the Spectrum has no blitter or GPU. Borderline -- it sets the scene for newcomers, but experienced Z80 programmers will find it patronizing.

**[A6-2] LOW — Paragraph restates what was just said**
File: `/Users/alice/dev/antique-toy/chapters/ch06-sphere/draft.md`, lines 265-277
> "The sphere in Illusion is a specific instance of a general demoscene pattern..."

The entire "The Larger Pattern" section (lines 265-278) recapitulates what the chapter already demonstrated. The three bullet points (Precomputation, Code generation, Sequential memory access) were already covered in the preceding 250 lines. The forward references to chapters 9, 10, and 7 are useful, but the section as a whole reads like a conclusion that summarizes too eagerly.

---

## Chapter 7: Rotozoomer and Chunky Pixels (ch07-rotozoomer/draft.md)

### Technical Accuracy

**[T7-1] HIGH — `SET n,(DE)` and `RES n,(DE)` do not exist on the Z80**
File: `/Users/alice/dev/antique-toy/chapters/ch07-rotozoomer/draft.md`, lines 338-341
```z80
    set  m,(de)           ; 15T  -- set screen bit
    ...
    res  m,(de)           ; 15T  -- clear screen bit
```

The Z80 `SET`/`RES` instructions only accept `(HL)` or `(IX+d)`/`(IY+d)` as memory operands. There is no `SET n,(DE)` or `RES n,(DE)`. The code snippet is invalid Z80 assembly and will not assemble. To write to an address in DE, you would need to use HL or an IX/IY-indexed approach. This also invalidates the T-state count and the "30-40 T-states minimum" per-pixel cost estimate on line 348.

**[T7-2] MEDIUM — 2x2 chunky row count confusion in rendering cost calculation**
File: `/Users/alice/dev/antique-toy/chapters/ch07-rotozoomer/draft.md`, lines 145-147
```
16 output bytes/row x 95 T-states = 1,520 T-states/row
1,520 x 96 rows = 145,920 T-states total
```

At 2x2 chunky with effective resolution 128x96, the texel grid is 64 columns x 48 rows (since each 2x2 chunky pixel covers 2 horizontal and 2 vertical real pixels). The inner loop packs 4 texels into each output byte (64/4 = 16 bytes wide), but there are only 48 unique texel rows, not 96. The calculation uses 96 rows (the effective pixel height), but the inner loop only needs to run once per unique texel row. The row duplication to fill the second physical pixel row of each 2x2 block should happen during the buffer-to-screen copy, not in the inner loop. The rendering cost should be approximately 72,960 T-states (48 rows), not 145,920. The "Texels/frame: 12,288" in the design space table (line 312) is also inconsistent -- at 2x2 chunky, there are 3,072 unique texels (64x48), not 12,288.

**[T7-3] LOW — `JR z,.pixel_off` timing annotation swapped**
File: `/Users/alice/dev/antique-toy/chapters/ch07-rotozoomer/draft.md`, line 337
```z80
    jr   z,.pixel_off     ; 7/12T
```

The comment says "7/12T" but the convention throughout the book is taken/not-taken. JR is 12T when taken (branch taken, condition true) and 7T when not taken (fall through). Since the branch is JR Z and this tests whether the bit is zero (pixel off), taken = pixel off = 12T. The "7/12T" annotation could confuse readers who expect the taken/not-taken order. Should be "12/7T" (taken/not-taken) to match the convention used in ch10 (line 68: `jr nc,.skip7 ; 12/7 T`).

### AI Smell

**[A7-1] MEDIUM — Opening paragraph is purple prose**
File: `/Users/alice/dev/antique-toy/chapters/ch07-rotozoomer/draft.md`, lines 8
> "There is a moment in Illusion where the screen fills with a pattern -- a texture, monochrome, repeating -- and then it begins to turn. The rotation is smooth and continuous, the zoom breathes in and out, and the whole thing runs at a pace that makes you forget you are watching a Z80 push pixels at 3.5 MHz."

"The zoom breathes in and out" and "makes you forget you are watching a Z80 push pixels" are the kind of evocative scene-setting that works in a magazine article but feels overwrought in a technical book. The sentence "on the Spectrum, making something look effortless is the hardest trick of all" is a cliche dressed in platform specificity.

**[A7-2] LOW — "beauty of the pre-computed table approach" (ch10, but pattern also appears in ch07)**
File: `/Users/alice/dev/antique-toy/chapters/ch07-rotozoomer/draft.md`, line 399
> "The rotozoomer is not a rotation algorithm. It is a *memory traversal pattern*."

This is the kind of "reframe the obvious" statement that LLMs love. The point is valid but the formulation -- "X is not Y. It is Z." -- is a recognizable AI rhetorical pattern. It appears multiple times across these chapters ("The attribute grid is not a limitation to work around. It is a framebuffer to work with" in ch09 line 26; "This is what makes the demoscene a temporal art form" in ch10 line 290). One instance is a stylistic choice. Three is a pattern.

---

## Chapter 8: Multicolor (ch08-multicolor/draft.md)

### Technical Accuracy

**[T8-1] MEDIUM — PUSH operation order is wrong**
File: `/Users/alice/dev/antique-toy/chapters/ch08-multicolor/draft.md`, line 52
> "The instruction `PUSH DE` writes the contents of DE to the address pointed to by SP, then decrements SP by 2."

This is backwards. PUSH first decrements SP by 1, writes the high byte to (SP), decrements SP by 1 again, writes the low byte to (SP). After PUSH DE, SP points to the low byte of the data just written, not to the old SP value. The correct description is: PUSH decrements SP by 2, then writes the register pair to the new (SP) location. The current wording implies the data is written to the old SP position, which would overwrite whatever was at the previous stack top rather than pushing below it.

This matters for understanding the LDPUSH technique: SP must be set to the byte AFTER the last screen byte to fill, because PUSH pre-decrements. The text on line 64-66 correctly describes the right-to-left fill behavior, which is consistent with PUSH pre-decrementing. But the explicit description of the instruction's operation on line 52 is wrong.

**[T8-2] LOW — `LD (HL),A : INC L` cost described as "per byte" is slightly misleading**
File: `/Users/alice/dev/antique-toy/chapters/ch08-multicolor/draft.md`, line 200
> "With `LD (HL),A : INC L` at 11 T-states per byte, writing 32 bytes takes 352 T-states"

This is technically correct (7+4=11T per byte), but the approach also requires loading the attribute value into A before each write. The full sequence would be something like `LD A,value : LD (HL),A : INC L` or similar, making the real cost higher than 352T. The 352T figure only accounts for the write+advance, not the data loading. Flagging as LOW because the text's point (352T > 224T, so you can't change every scanline) remains valid even if the real cost is higher.

### AI Smell

**[A8-1] MEDIUM — Section "What DenisGrachev's Work Means" is editorial padding**
File: `/Users/alice/dev/antique-toy/chapters/ch08-multicolor/draft.md`, lines 390-402
> "The demoscene has always been about pushing hardware past its limits..."
> "Demos are performance art. They run once, they impress, they end."
> "Games are engineering."

This entire section (lines 390-402) is a philosophical essay about the demo-vs-game distinction. While the point is valid, the section tells the reader what to think rather than presenting new technical content. The first paragraph especially -- "The demoscene has always been about pushing hardware past its limits. But there is a distinction..." -- is generic framing that could appear in any retro computing article. The specific claims about DenisGrachev's contribution are better made (and already were made) in the GLUF and Ringo sections where the engineering details support them.

**[A8-2] LOW — Overexplaining the obvious for the target audience**
File: `/Users/alice/dev/antique-toy/chapters/ch08-multicolor/draft.md`, lines 254-258
> "The ZX Spectrum has 15 colours: 8 base colours (black, blue, red, magenta, green, cyan, yellow, white) and 7 BRIGHT variants..."

Any reader of a Z80 demoscene techniques book knows the Spectrum palette. This is reference material that belongs in an appendix, not in a chapter body. The BRIGHT constraint note is useful; the full palette enumeration is not.

---

## Chapter 9: Attribute Tunnels and Chaos Zoomers (ch09-tunnels/draft.md)

### Technical Accuracy

**[T9-1] MEDIUM — `LD HL,nn : LDI` pair described as "6 bytes" but is actually 5 bytes**
File: `/Users/alice/dev/antique-toy/chapters/ch09-tunnels/draft.md`, line 108
> "each pair is just 6 bytes and 26 T-states"

`LD HL,nn` = 3 bytes (opcode $21 + 2 operand bytes). `LDI` = 2 bytes (prefix $ED + opcode $A0). Total = 5 bytes, not 6. The T-state count (26T = 10+16) is correct. The byte count error matters for estimating memory consumption of the unrolled code: 192 cells x 5 bytes = 960 bytes, not the 1,152 bytes implied by "6 bytes."

**[T9-2] LOW — LDI side effect on BC not mentioned in chaos zoomer section**
File: `/Users/alice/dev/antique-toy/chapters/ch09-tunnels/draft.md`, lines 95-108
The chaos zoomer uses unrolled `ld hl,nn : ldi` sequences for up to 192 cells (or 768 for the full screen). Each `LDI` decrements BC. After 192 iterations, BC has been decremented 192 times from whatever its starting value was. If BC is needed for anything else (or if BC reaches 0, affecting the P/V flag and potentially breaking conditional logic), this could be a subtle bug. The text should at least note that BC is consumed as a side effect and must be considered in the register allocation.

### AI Smell

**[A9-1] LOW — "disarmingly simple" is AI-flavored hedging**
File: `/Users/alice/dev/antique-toy/chapters/ch09-tunnels/draft.md`, line 18
> "The insight is disarmingly simple."

This is a mild case. "Disarmingly simple" is a stock phrase that signals "I'm about to tell you something obvious but want to make it sound profound." The insight (use attributes as a framebuffer) IS simple, and the text immediately explains it. The qualifier adds nothing.

**[A9-2] LOW — "remarkably tight" is a subjective quality judgment**
File: `/Users/alice/dev/antique-toy/chapters/ch09-tunnels/draft.md`, line 71
> "The copy routine is remarkably tight."

Vague superlative. The code IS tight, but "remarkably" is the author's impression, not a technical description. Just show the code and let the reader judge.

---

## Chapter 10: The Dotfield Scroller and 4-Phase Colour (ch10-scroller/draft.md)

### Technical Accuracy

**[T10-1] HIGH — "LD (addr),SP does not exist on the Z80" is wrong**
File: `/Users/alice/dev/antique-toy/chapters/ch10-scroller/draft.md`, line 48
> "`LD (addr),SP` does not exist on the Z80. The only option is `LD (.smc+1),SP`"

`LD (nn),SP` absolutely exists on the Z80. It is instruction ED 73 nn nn, costing 20 T-states. It is documented in the official Zilog Z80 manual. Ironically, `LD (.smc+1),SP` IS the `LD (nn),SP` instruction -- the author is using the instruction while claiming it doesn't exist. The sentence then says "This costs 20 T-states" which is the correct timing for `LD (nn),SP`.

The self-modifying code technique described (writing SP into the operand of a later `LD SP,nn`) is a legitimate idiom, but the motivation given (that direct SP storage doesn't exist) is false. A more accurate motivation: the SMC approach saves and restores SP in a single operation sequence, whereas using `LD (nn),SP` for save and `LD SP,(nn)` for restore requires remembering a separate memory address. The SMC version is self-contained.

**[T10-2] MEDIUM — PUSH-based attribute copy cost of "roughly 4,500 T-states" for 768 bytes is too low**
File: `/Users/alice/dev/antique-toy/chapters/ch10-scroller/draft.md`, line 227
> "Using the PUSH trick (point SP at the end of attribute RAM, load register pairs, PUSH), you can move 768 bytes in roughly 4,500 T-states -- a 3.5x speedup"

The fastest possible PUSH-based block copy is POP+PUSH per 2 bytes: POP (10T) + PUSH (11T) = 21T per 2 bytes. For 768 bytes: 384 iterations x 21T = 8,064T. Even counting only the PUSH instructions (ignoring the data loading): 384 x 11T = 4,224T. But you cannot PUSH data you haven't loaded, so the minimum cost is at least 8,064T. The "4,500 T-states" figure appears to count only the PUSH half and ignore data loading entirely. The "3.5x speedup" (16,128 / 4,500) is consequently wrong; the real speedup over LDIR is approximately 2x (16,128 / 8,064).

**[T10-3] LOW — 12.5 Hz assertion for 4-phase flicker-fusion may be optimistic**
File: `/Users/alice/dev/antique-toy/chapters/ch10-scroller/draft.md`, line 176
> "The four-frame cycle completes in 80ms -- 12.5 cycles per second, above the flicker-fusion threshold on CRT displays."

The flicker-fusion threshold for most humans is around 50-60 Hz for large-field stimuli, not 12.5 Hz. At 12.5 Hz, flicker IS perceptible. The text later acknowledges this implicitly by discussing how pattern selection minimizes visible oscillation (line 193) and how CRT phosphor persistence helps (line 276). The claim that 12.5 Hz is "above the flicker-fusion threshold" is technically incorrect. The technique works despite visible flicker, not because flicker is imperceptible. It works because the eye averages the colors even when flicker is detectable, and CRT phosphor persistence + careful color pairing minimizes the perceptual impact.

### AI Smell

**[A10-1] MEDIUM — "The Shared Principle: Temporal Cheating" section is a philosophy lecture**
File: `/Users/alice/dev/antique-toy/chapters/ch10-scroller/draft.md`, lines 280-291
> "This is what makes the demoscene a temporal art form. A screenshot of a dotfield scroller shows a scatter of pixels. A screenshot of a 4-phase colour animation shows two colours per cell, exactly as the hardware specifies. You have to see them *move* to see them work. The beauty is in the sequence, not the frame."

This section synthesizes the chapter's two techniques into a philosophical statement. The observation about temporal vs. spatial resolution is valid but stated with more flourish than substance. "The beauty is in the sequence, not the frame" is a quotable aphorism, but it's the kind of closing flourish that an LLM produces as a capstone paragraph. The preceding lines about "temporal art form" and "demoscene cheating" add no technical insight.

**[A10-2] LOW — Rhetorical reframing pattern appears again**
File: `/Users/alice/dev/antique-toy/chapters/ch10-scroller/draft.md`, line 8-9
> "The ZX Spectrum displays two colours per 8x8 cell. Text scrolls across a screen at whatever rate the CPU can manage. These are fixed constraints -- the hardware does what it does, and no amount of cleverness will change the silicon."
> "But cleverness can change what the viewer *perceives*."

The "but cleverness can change perception" pivot is the same framing used in ch09 ("The insight is disarmingly simple"), ch07 ("The rotozoomer is not a rotation algorithm"), and ch08 ("But the ULA does not know this"). It's effective once; by the fifth chapter in a row, it's a recognizable pattern.

---

## Summary of Findings

### Technical Accuracy — by severity

| ID | Severity | Chapter | Issue |
|----|----------|---------|-------|
| T7-1 | HIGH | ch07 | `SET n,(DE)` and `RES n,(DE)` don't exist on Z80 |
| T10-1 | HIGH | ch10 | Claims `LD (addr),SP` doesn't exist (it does: ED 73) |
| T6-1 | MEDIUM | ch06 | Summary reverses Illusion (1996) / SE articles (1997) causation |
| T7-2 | MEDIUM | ch07 | 2x2 chunky uses 96 rows but should be 48 texel rows |
| T8-1 | MEDIUM | ch08 | PUSH operation order described backwards |
| T9-1 | MEDIUM | ch09 | `LD HL,nn : LDI` is 5 bytes, not 6 |
| T10-2 | MEDIUM | ch10 | PUSH-based 768-byte copy claim of 4,500T is ~8,064T in reality |
| T6-2 | LOW | ch06 | T-state formula verification attempt hand-waves the mismatch |
| T7-3 | LOW | ch07 | JR z timing "7/12T" convention inconsistent with rest of book |
| T8-2 | LOW | ch08 | LD (HL),A : INC L cost omits data loading |
| T9-2 | LOW | ch09 | LDI side effect on BC not mentioned for zoomer |
| T10-3 | LOW | ch10 | 12.5 Hz claimed "above flicker-fusion threshold" (it's not) |

### AI Smell — by severity

| ID | Severity | Chapter | Issue |
|----|----------|---------|-------|
| A7-1 | MEDIUM | ch07 | Opening paragraph is purple prose |
| A7-2 | LOW | ch07 | "X is not Y. It is Z." reframing pattern used across multiple chapters |
| A8-1 | MEDIUM | ch08 | "What DenisGrachev's Work Means" section is editorial padding |
| A10-1 | MEDIUM | ch10 | "Temporal Cheating" section is philosophy, not content |
| A6-1 | LOW | ch06 | "No blitter. No GPU. No co-processor." patronizes the audience |
| A6-2 | LOW | ch06 | "The Larger Pattern" section restates what was already shown |
| A8-2 | LOW | ch08 | Full palette enumeration unnecessary for target audience |
| A9-1 | LOW | ch09 | "disarmingly simple" is stock AI-adjacent phrasing |
| A9-2 | LOW | ch09 | "remarkably tight" is subjective filler |
| A10-2 | LOW | ch10 | Same "but cleverness can..." pivot reused across chapters |

### Overall Assessment

The technical content in these five chapters is strong. The cycle counting is accurate across hundreds of instruction timing claims. Opcodes are correct. Hardware addresses are correct. The narrative structure -- tracing techniques through Dark's original work, Introspec's analysis, and sq's optimisation studies -- is well-researched and coherent.

The two HIGH-severity issues (nonexistent SET/RES (DE) instructions, false claim about LD (nn),SP) need fixing. The MEDIUM issues are mostly arithmetic errors or imprecise descriptions that could mislead a reader trying to reproduce the techniques.

The AI smell is present but restrained. The main pattern is philosophical summarization sections that restate technical content in aphoristic form. These sections read well in isolation but become repetitive across chapters. The "X is not Y, it is Z" reframing device appears too often. The opening scene-setting paragraphs occasionally talk down to the audience.
