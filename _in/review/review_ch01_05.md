# Technical Review: Chapters 1-5

Reviewer: Claude Opus 4.6
Date: 2026-02-24
Scope: Technical accuracy and AI-smell audit of ch01 through ch05 drafts.

---

## 1. TECHNICAL ACCURACY ERRORS

### [HIGH] Ch.2: RET cc T-state values are swapped throughout

**File:** `/Users/alice/dev/antique-toy/chapters/ch02-screen-as-puzzle/draft.md`

On the Z80, conditional RET (RET cc) costs **11T when the condition is met (taken)** and **5T when the condition is not met (falls through)**. The chapter has these values swapped in every occurrence.

**Line 194:**
```
    ret  nz            ; 11T  (5T if taken) no: done
```
The comment says "11T (5T if taken)" -- but "if taken" means the condition IS met, in which case the cost IS 11T, not 5T. The parenthetical is self-contradictory. Reading in context, the author intended: "normally 11T, but only 5T if the return is taken." That is backwards. Taken = 11T. Not taken = 5T.

The same error appears at:
- **Line 201:** `ret  c  ; 11T  (5T if taken)`
- **Line 537:** `ret  nz ; 11T  (5T if taken)`
- **Line 543:** `ret  c  ; 11T  (5T if taken)`
- **Line 562:** `ret  nz ; 11T  (5T if taken)`
- **Line 567:** `ret  c  ; 11T  (5T if taken)`

**Consequence -- the timing table at lines 213-217 is wrong for 2 of 3 cases:**

The table at line 215 says the common case (within a character cell) costs `4 + 4 + 7 + 5 = 20T`. This uses 5T for RET NZ taken (returning). The correct value is 11T for taken, giving `4 + 4 + 7 + 11 = **26T**`.

The table at line 216 says the character-boundary-same-third case costs 77T. Using corrected values (RET NZ not-taken = 5T, RET C not-taken = 5T): `4 + 4 + 7 + 5 + 4 + 7 + 4 + 5 + 4 + 7 + 4 + 10 = **65T**` (not 77T).

The table at line 217 says the third-boundary case costs 46T. With corrected values (RET NZ not-taken = 5T, RET C taken = 11T): `4 + 4 + 7 + 5 + 4 + 7 + 4 + 11 = **46T**`. This one happens to be correct because 5+11 = 11+5.

Corrected table:

| Case | Frequency | T-states |
|------|-----------|----------|
| Within character cell | 7 of 8 | 4+4+7+11 = **26T** |
| Character boundary, same third | 6 of 64 | **65T** |
| Third boundary | 2 of 192 | **46T** |

The average cost quoted at line 219 ("about 24.6 T-states per call") is also wrong. With correct values the average is higher.

**Severity: HIGH** -- This is a factual error that propagates through the timing analysis. The common-case cost is 30% higher than stated.

---

### [HIGH] Ch.4: "Patrik Rak" and "Raxoft" treated as different people

**File:** `/Users/alice/dev/antique-toy/chapters/ch04-maths/draft.md`

**Lines 419-528:** The section on PRNGs presents "Patrik Rak's CMWC Generator" (line 419) and "Raxoft's CMWC Variant" (line 526) as work by two different people. Line 528 says the Raxoft variant is "similar in principle to Patrik Rak's version" -- implying independent authorship.

Raxoft is Patrik Rak's handle/brand name. They are the same person. Patrik Rak publishes code and utilities under the name "Raxoft." The text should either:
- Use a single name throughout, or
- Explicitly note they are the same person, e.g., "Patrik Rak (Raxoft)"

The comparison table at line 610 lists them as separate entries, reinforcing the confusion.

**Severity: HIGH** -- Factual error about a real, identifiable person in the ZX Spectrum community.

---

### [MEDIUM] Ch.2: LDIR cost calculation is wrong (off by 21T)

**File:** `/Users/alice/dev/antique-toy/chapters/ch02-screen-as-puzzle/draft.md`

**Line 447:**
```
Cost: `LDIR` at 21 T-states per byte x 6,143 + 16 for the last byte = 129,019 T-states.
```

The code sets BC = SCRLEN - 1 = 6143. LDIR with BC=6143 copies 6143 bytes: 6142 iterations at 21T + 1 last iteration at 16T = 128,998T. The text computes 6143*21 + 16 = 129,019, which double-counts the last byte (gives it 21T for the repeat PLUS 16T extra). The correct formula is either (6143-1)*21 + 16 = 128,998, or equivalently 6143*21 - 5 = 128,998.

Ch.3 line 169 uses the correct formula (`6,144 x 21 - 5`) for a similar calculation, so the author knows the right approach -- it just was not applied consistently.

**Severity: MEDIUM** -- 21 T-states off. Not large enough to change any design decision, but the text presents it as an exact calculation.

---

### [MEDIUM] Ch.2: Attribute LDIR cost has wrong formula AND wrong arithmetic

**File:** `/Users/alice/dev/antique-toy/chapters/ch02-screen-as-puzzle/draft.md`

**Line 462:**
```
Cost: 768 bytes x 21 + last byte at 16 = 16,143 T-states.
```

Two errors here:
1. The code sets BC = ATTLEN - 1 = 767, so LDIR copies 767 bytes, not 768.
2. Even accepting the text's formula literally: 768 * 21 + 16 = 16,128 + 16 = 16,144, not 16,143. The arithmetic is off by 1.

The correct cost: (767-1)*21 + 16 = 766*21 + 16 = 16,086 + 16 = 16,102T. Or equivalently: 767*21 - 5 = 16,102T.

**Severity: MEDIUM** -- Double error (wrong byte count and wrong arithmetic).

---

### [MEDIUM] Ch.2: UP_HL has same RET cc T-state bug as DOWN_HL

**File:** `/Users/alice/dev/antique-toy/chapters/ch02-screen-as-puzzle/draft.md`

**Lines 537, 543:** The classic UP_HL routine repeats the same "11T (5T if taken)" error pattern as DOWN_HL. Same issue: taken = 11T, not 5T.

**Lines 562, 567:** The optimized UP_HL also has the same error.

**Severity: MEDIUM** -- Same bug as the DOWN_HL case, less impactful because no timing table is derived from these values.

---

### [LOW] Ch.3: Frame budget quoted as 69,888 (48K) despite Pentagon being the reference platform

**File:** `/Users/alice/dev/antique-toy/chapters/ch03-demoscene-toolbox/draft.md`

**Line 375:**
```
The Z80 runs at 3.5 MHz. You have 69,888 T-states per frame.
```

Ch.1 establishes Pentagon (71,680 T-states) as the reference platform for the book: "All the T-state tables in this book assume Pentagon timing unless stated otherwise" (ch01 line 92). Ch.3 then quotes the 48K figure without qualification. This is inconsistent with the stated convention.

**Severity: LOW** -- Does not cause incorrect reasoning, but contradicts the book's own established convention. Use 71,680 for consistency with the rest of the book.

---

### [LOW] Ch.1: Minor approximation in LDIR full-screen cost

**File:** `/Users/alice/dev/antique-toy/chapters/ch01-thinking-in-cycles/draft.md`

**Line 68:**
```
a single `LDIR` copying 6,912 bytes (one full screen of pixel data) costs approximately 6,912 x 21 = 145,152 T-states.
```

The precise cost is (6912-1)*21 + 16 = 145,147T. The text says "approximately" so this is acceptable, but noting it for completeness. Also, the parenthetical says "one full screen of pixel data" but 6,912 bytes includes both pixel data (6,144) AND attributes (768). Should say "one full screen" or "pixel data plus attributes."

**Severity: LOW** -- Labeled as approximate, and the 5T difference is negligible. The description of what 6,912 bytes covers is slightly misleading.

---

### [LOW] Ch.5: Averaging overflow not addressed

**File:** `/Users/alice/dev/antique-toy/chapters/ch05-3d/draft.md`

**Lines 64-65:**
```z80
    add  a, b           ;  4 T-states
    sra  a              ;  8 T-states
```

When A and B are both near +127 or both near -128, `ADD A, B` overflows the 8-bit register before `SRA` can halve the result. For example, A=100, B=100: ADD gives 200 (unsigned) which is -56 in signed 8-bit. SRA then gives -28, not the correct average of 100. The text does not mention this limitation. In practice, with coordinates typically in the -60..+60 range, overflow is unlikely, but the code is mathematically incorrect for the general case.

**Severity: LOW** -- Unlikely to trigger with typical demo coordinate ranges, but the code as presented is not correct for arbitrary signed 8-bit inputs.

---

## 2. AI SMELL

### [MEDIUM] Ch.2: "Wait -- that is wrong" chain-of-thought left in prose

**File:** `/Users/alice/dev/antique-toy/chapters/ch02-screen-as-puzzle/draft.md`

**Lines 330-332:**
```
An attribute byte of `$47` means: flash off, bright off, paper = 0 (black), ink = 7 (white). White text on a black background -- the Spectrum's default. The bright version would be `$C7`: `$47` OR `$40` sets the bright bit.

Wait -- that is wrong. Let us re-read the bit layout. Bit 6 is bright, so bright white on black is `$47` with bit 6 set: `$47 | $40 = $47`. No, `$47` is already `01000111`. Bit 7 is flash, bit 6 is bright. So `$47` = flash off, bright **on**, paper 000, ink 111 = bright white on black. The non-bright version would be `$07`.
```

This reads like an LLM debugging its own output in real time -- making a mistake, then "catching" it in a way that looks deliberate but actually reveals chain-of-thought processing. A human author would simply correct the text; they would not leave the wrong version and then "discover" the error mid-paragraph. The "Wait -- that is wrong" pattern is characteristic of LLM self-correction.

Additionally, the first claim (`$C7` as the bright version) is also wrong: $C7 = 11000111 = flash ON, bright ON, which is not what you'd want for just "bright." The self-correction catches the $47 issue but does not address the $C7 claim.

**Recommendation:** Delete lines 330-331 entirely. Start at: "$47 is `01000111` in binary: flash off (bit 7 = 0), bright on (bit 6 = 1), paper black (000), ink white (111). The non-bright version is $07."

---

### [MEDIUM] Ch.2: Pixel-to-attribute derivation left as a messy false start

**File:** `/Users/alice/dev/antique-toy/chapters/ch02-screen-as-puzzle/draft.md`

**Lines 579-670:** The pixel-to-attribute conversion section contains THREE failed attempts at deriving the routine, with self-correcting commentary:

- Lines 586-594: First attempt, ending with "Wait -- that is not quite right."
- Lines 600-640: Second attempt, with inline commentary like "Hmm, we also need LLL from L" and "That's not right either."
- Lines 644-670: Third attempt, which finally works, but includes lengthy inline commentary rethinking the logic.

This is a hallmark of LLM generation: the model produces an incorrect derivation, detects the error, and "tries again" rather than going back and editing. A human technical writer would present only the working derivation.

**Recommendation:** Cut everything between line 579 and line 673. Keep only the final clean version (lines 674-687) with the comment block at lines 688-689 explaining why it works.

---

### [LOW] Ch.5: "remarkably" used twice in one paragraph

**File:** `/Users/alice/dev/antique-toy/chapters/ch05-3d/draft.md`

**Line 125:** "The interpreter loop is remarkably compact:"
**Line 202:** "The architecture is remarkably clean."

Two uses of "remarkably" within 77 lines. This is a common LLM tic -- reaching for the same intensifier multiple times in a passage.

---

### [LOW] Ch.5: "The ratio is staggering"

**File:** `/Users/alice/dev/antique-toy/chapters/ch05-3d/draft.md`

**Line 72:**
```
The ratio is staggering: averaging is **66 times cheaper** than rotation.
```

"Staggering" is an empty intensifier. The 66x ratio speaks for itself. Just say: "Averaging is 66 times cheaper than rotation."

---

### [LOW] Ch.4: "a profound principle"

**File:** `/Users/alice/dev/antique-toy/chapters/ch04-maths/draft.md`

**Line 536:**
```
The Tribonacci approach deserves more detail because it illustrates a profound principle: **a PRNG is not just a random number source -- it is a compression algorithm.**
```

"Profound principle" is an LLM superlative. The bolded claim is interesting enough on its own. Replace with: "The Tribonacci approach illustrates an important idea:" or just drop the preamble and state the principle.

---

### [LOW] Ch.3: "The most powerful technique" as a section heading

**File:** `/Users/alice/dev/antique-toy/chapters/ch03-demoscene-toolbox/draft.md`

**Line 231:**
```
### The most powerful technique
```

Superlative heading with no qualifier. Every technique in a demoscene toolbox chapter could be called "the most powerful" depending on context. A more specific heading like "Generating code at assembly time and runtime" would be informative rather than grandiose.

---

### [LOW] Ch.5: Historical section repeats points already made

**File:** `/Users/alice/dev/antique-toy/chapters/ch05-3d/draft.md`

**Lines 655-665:** The "Historical Context: From Magazine to Demo" section largely restates information already presented earlier in the chapter and in Ch.4:

- Line 657 repeats that Dark and STS published in SE#02 (already stated at line 89, 104, etc.)
- Line 659 repeats that Dark was from X-Trade and *Illusion* won at ENLiGHT'96 (stated in Ch.4 lines 6-8 and throughout)
- Line 663 repeats that Introspec found the same algorithms in *Illusion* (stated in Ch.4 line 8 and Ch.5 passim)

This reads like LLM "closing summary" padding -- restating the narrative arc as if the reader needs reminding of what they just read 2 pages ago.

**Recommendation:** Cut this section to 1-2 paragraphs. The only new content is the observation about the virtual processor resembling modern game engine patterns (line 661), which could be a single paragraph after the VP section itself.

---

## 3. ITEMS CHECKED AND FOUND CORRECT

For completeness, the following claims were verified and are accurate:

- Ch.1: T-state table (NOP=4, LD A,B=4, LD A,(HL)=7, PUSH HL=11, DJNZ=13/8, LDIR=21/16, OUT(n)A=11) -- all correct
- Ch.1: Frame budgets (48K=69,888, 128K=70,908, Pentagon=71,680) -- all correct
- Ch.1: Pentagon scanline = 224T (71,680/320) -- correct
- Ch.1: PUSH HL M-cycle breakdown (M1=5T + 2x write=3T+3T = 11T) -- correct
- Ch.1: Timing harness total (256*(16+13)-5 = 7,419T) -- correct
- Ch.1: DJNZ timing (13T taken, 8T falls through) -- correct
- Ch.2: Screen memory layout addresses and bit decomposition -- correct
- Ch.2: SRL/RRC/SET timing (all 8T for register operands) -- correct
- Ch.3: CALL nn = 17T, RET = 10T -- correct
- Ch.3: PUSH fill total (192 * (176+13) - 5 ~= 36,283T, "roughly 36,000") -- correct
- Ch.3: LDI = 16T, LDIR per byte = 21T -- correct
- Ch.4: SRA A = 8T (CB-prefixed) -- correct
- Ch.5: ADD A,B = 4T, SRA A = 8T, total 12T per coordinate average -- correct

---

## SUMMARY

| Severity | Count | Category |
|----------|-------|----------|
| HIGH | 2 | Technical accuracy (RET cc swap, Rak/Raxoft identity) |
| MEDIUM | 4 | Technical accuracy (2), AI smell (2) |
| LOW | 9 | Technical accuracy (3), AI smell (6) |
| **Total** | **15** | |

The two HIGH-severity issues should be fixed before any editing pass. The RET cc timing swap in Ch.2 affects six comment lines and one timing table, propagating through the DOWN_HL and UP_HL analysis. The Patrik Rak / Raxoft confusion in Ch.4 is a factual error about a living person that could embarrass the book.

The two MEDIUM AI-smell issues (Ch.2 lines 330-332 and 579-670) are the most conspicuous LLM artifacts in these five chapters: visible chain-of-thought reasoning left in the final text. They should be rewritten to present only the correct derivation.
