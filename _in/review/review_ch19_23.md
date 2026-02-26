# Review: Chapters 19-23 — Technical Accuracy and AI Smell

Reviewer: Claude Opus 4.6 automated review
Date: 2026-02-24
Scope: ch19 (Collisions), ch20 (Demo Workflow), ch21 (Full Game), ch22 (Porting Agon), ch23 (AI-Assisted)

---

## TECHNICAL ACCURACY ERRORS

### T-01. Ch19 — Wrong T-state total for AABB early exit path
**File:** `/Users/alice/dev/antique-toy/chapters/ch19-collisions/draft.md`
**Lines:** 45, 87, 122
**Quote (line 87):** `; --- early exit: 82T (taken) ---`
**Quote (line 45):** `"The first X-overlap test rejects them in ~82 T-states."`
**Quote (line 122):** `"Best case (first test fails): approximately 82 T-states."`
**What's wrong:** The actual T-state count for the early exit path (first test fails) is:
- `ld a, (iy+1)` = 19T
- `add a, (iy+13)` = 19T
- `ld b, a` = 4T
- `ld a, (ix+1)` = 19T
- `cp b` = 4T
- `jr nc, .no_collision` = 12T (taken)
- Subtotal to branch: 77T
- Then `.no_collision`: `or a` = 4T, `ret` = 10T
- Full early exit path: 91T

The claimed 82T does not match any plausible sum of the instructions shown. The code path through to the taken JR is 77T; the full exit path including `or a` + `ret` is 91T. Neither is 82.
**Severity:** MEDIUM — The relative point (early exit is cheap) is valid, but the specific number is wrong and cited three times.

### T-02. Ch19 — Wrong worst-case T-state total for AABB collision
**File:** `/Users/alice/dev/antique-toy/chapters/ch19-collisions/draft.md`
**Lines:** 74, 122, 1167
**Quote (line 74):** `; Cost: 70-156 T-states (Pentagon), depending on early exit`
**Quote (line 122):** `"Worst case (all four tests pass): approximately 156 T-states."`
**What's wrong:** Counting all instructions through the collision-detected path (all four tests pass, all JRs not taken):
- Test 1: 19+19+4+19+4+7 = 72T (JR not taken = 7T)
- Test 2: 19+19+4+7+7 = 56T (both JRs not taken = 7T each)
- Test 3: 19+19+4+19+4+7 = 72T
- Test 4: 19+19+4+7+7 = 56T
- Final: `scf` = 4T, `ret` = 10T
- Total: 72+56+72+56+14 = 270T

Even being generous and assuming some instructions were miscounted, the sum is well over 156T. The IX/IY indexed instructions at 19T each dominate, and there are 12 of them (12 x 19 = 228T alone). The "approximately 156 T-states" claim for the worst case is significantly too low.
**Severity:** HIGH — The worst case is nearly double what is claimed. This would mislead a reader calculating frame budgets.

### T-03. Ch19 — `tile_at` T-state estimate is too low
**File:** `/Users/alice/dev/antique-toy/chapters/ch19-collisions/draft.md`
**Line:** 159
**Quote:** `; Cost: ~40 T-states (Pentagon)`
**What's wrong:** Counting the actual instructions:
- `ld a, c` = 4T
- 3x `srl a` = 3x8 = 24T
- `ld l, a` = 4T
- `ld h, 0` = 7T
- 5x `add hl, hl` = 5x11 = 55T
- `ld a, b` = 4T
- 3x `srl a` = 24T
- `ld e, a` = 4T
- `ld d, 0` = 7T
- `add hl, de` = 11T
- `ld de, tilemap` = 10T
- `add hl, de` = 11T
- `ld a, (hl)` = 7T
- `ret` = 10T
- Total: ~182T

The claimed "~40 T-states" is off by more than 4x. The actual cost is closer to 182T.
**Severity:** HIGH — A core routine used in frame budget calculations is radically undercosted. Readers using this estimate for budget planning will massively underestimate tile collision cost.

### T-04. Ch19 — `SRL A` timing shown as 8T
**File:** `/Users/alice/dev/antique-toy/chapters/ch19-collisions/draft.md`
**Lines:** 163-165, 177-179
**Quote:** `srl  a  ; 8T   /2`
**What's wrong:** `SRL A` is a CB-prefixed instruction. Its timing is 8T on Z80. This is actually correct. (Retained for completeness but no error here.)
**Severity:** N/A — Verified correct.

### T-05. Ch23 — DOWN_HL code is claimed to fail at third boundary, but it is actually correct
**File:** `/Users/alice/dev/antique-toy/chapters/ch23-ai-assisted/draft.md`
**Lines:** 316-332
**Quote (line 331):** `"This is correct for the first two thirds of the screen but fails at the third-third boundary."`
**Quote (line 331-332):** `"the transition from the second to the third third requires adding $08 to H, not subtracting"`
**What's wrong:** The DOWN_HL code shown is actually correct for all three screen thirds, including the third-to-third boundary. Here is the trace:

At the boundary between second and third thirds: last pixel row of last char row in second third. H = 01001 111 (binary), L = 111 CCCCC. (H = $4F for column 0.)
- `inc h`: H = $50 (01010 000). Pixel row wrapped 7->0, third bits advanced from 01 to 10.
- `and 7`: result is 0, so no early return.
- `add a, 32` to L: char row bits (111) + 1 = 000, carry IS set.
- `ret c`: returns with H=$50, L=000CCCCC. Address $50xx is the start of the third third. Correct.

The inc h overflow naturally propagates into the "third" bits of H. When L's char-row bits also wrap (setting carry), the code correctly returns with both H and L pointing to the start of the next third. The `sub 8` path is never reached for third-boundary crossings because `ret c` exits first.

The chapter uses this as a key argument that "AI gets Z80 wrong," but the example code is actually correct. This undermines the narrative point.
**Severity:** HIGH — A central technical example in the chapter is wrong about being wrong. The code shown works correctly. The book claims a bug that does not exist.

### T-06. Ch23 — Rotozoomer inner loop total is wrong
**File:** `/Users/alice/dev/antique-toy/chapters/ch23-ai-assisted/draft.md`
**Lines:** 294-300
**Quote (line 300):** `; --- 30T per pixel pair`
**What's wrong:** Counting the instructions:
- `ld a, (hl)` = 7T
- `inc l` = 4T
- `dec h` = 4T
- `add a` (= `add a, a`) = 4T
- `add a` = 4T
- `add (hl)` (= `add a, (hl)`) = 7T
- Total = 30T

Actually, this is correct. The count adds up to 30T. No error.
**Severity:** N/A — Verified correct.

### T-07. Ch22 — eZ80 ADL mode state table code has a bug
**File:** `/Users/alice/dev/antique-toy/chapters/ch22-porting-agon/draft.md`
**Lines:** 271-288
**Quote (lines 273-276):**
```z80
    ld   a,(game_state)
    ld   e,a
    ld   d,0               ; DE = state index (24-bit, upper byte zero)
    ld   hl,a              ; HL = state * 3
```
**What's wrong:** `ld hl, a` is not a valid Z80 or eZ80 instruction. There is no `LD HL, A` encoding. To get the state value into HL, you would need something like `ld l, a : ld h, 0` or use DE that was just set. The code also does not correctly compute state * 3. After `ld e, a` and the invalid `ld hl, a`, it does `add hl, hl` (state * 2) then `add hl, de` (state * 2 + state = state * 3). The logic for * 3 is correct but the `ld hl, a` instruction does not exist.
**Severity:** MEDIUM — Example code in the porting chapter contains an invalid instruction. Readers trying to assemble this will get an error.

### T-08. Ch22 — Incorrect clock speed / frame budget for Agon Light 2
**File:** `/Users/alice/dev/antique-toy/chapters/ch22-porting-agon/draft.md`
**Line:** 48
**Quote:** `| Frame budget | ~71,680 T-states (Pentagon) | ~368,640 T-states (at 50 Hz) |`
**What's wrong:** At 18.432 MHz and 50 Hz, the frame budget would be 18,432,000 / 50 = 368,640 T-states. This math checks out. However, the eZ80 executes most instructions in fewer cycles than the Z80 (many single-byte instructions are 1 cycle on eZ80 vs 4T on Z80). The "T-states" for the eZ80 are clock cycles, not Z80-equivalent T-states. Comparing "368,640" eZ80 clock cycles to "71,680" Z80 T-states as the same unit is misleading because the eZ80 completes most instructions in 1-3 clocks vs 4+ on Z80. The effective throughput difference is larger than 5:1.

The text at line 577 acknowledges this partially: "many eZ80 instructions also execute in fewer clock cycles." But the comparison table on line 48 presents the raw numbers as equivalent units without qualification.
**Severity:** LOW — The text partially addresses this later, but the table is misleading at first read.

### T-09. Ch21 — BASIC loader uses wrong CLEAR value for 128K game
**File:** `/Users/alice/dev/antique-toy/chapters/ch21-full-game/draft.md`
**Lines:** 840-847
**Quote:** `10 CLEAR 32767`
**What's wrong:** `CLEAR 32767` sets RAMTOP to 32767 ($7FFF), which protects memory from $8000 upward. The text on line 847 says "Line 10 sets RAMTOP below $8000, protecting our code from BASIC's stack." This is correct in intent. However, the standard practice for 128K games is `CLEAR 24575` ($5FFF) to also protect the contended memory region used by screen memory and any data placed in the $6000-$7FFF area. Using 32767 is not wrong per se, but leaves $6000-$7FFF unprotected, which may be overwritten by BASIC's stack during the LOAD commands that follow.

Additionally, line 50 (`RANDOMIZE USR 32768`) jumps to $8000, which is correct.
**Severity:** LOW — Works in most cases but is not best practice for 128K.

### T-10. Ch22 — `BIT 7,A` claim is wrong about Z80 limitations
**File:** `/Users/alice/dev/antique-toy/chapters/ch22-porting-agon/draft.md`
**Lines:** 778-779
**Quote:** `"On the Z80, you would need BIT 7,A (which does not work with arbitrary masks)"`
**What's wrong:** The parenthetical "(which does not work with arbitrary masks)" is confusingly written but technically accurate -- `BIT b, r` only tests a single numbered bit (0-7), not an arbitrary bitmask. However, for the specific example of testing bit 7 (TST A, $80), BIT 7,A does exactly the same thing on Z80 and is only 2 bytes/8T. The claim that you'd need `PUSH AF / AND mask / POP AF` to test bit 7 is wrong -- `BIT 7,A` works perfectly for that case. The TST instruction is only advantageous for non-power-of-2 masks.
**Severity:** LOW — The example chosen for TST does not demonstrate its actual advantage over BIT.

### T-11. Ch19 — `add a, (iy+13)` produces wrong result if sum overflows
**File:** `/Users/alice/dev/antique-toy/chapters/ch19-collisions/draft.md`
**Lines:** 81-82
**What's wrong:** The AABB code computes B.right as `B.x_int + B.width` using unsigned 8-bit ADD. If an entity is at X=240 with width=32, the sum wraps to 16. The subsequent `cp` comparison would then incorrectly conclude that A.left (say, 200) >= B.right (16), reporting no collision when there should be one. The code does not handle the unsigned overflow case. This is a real gameplay bug for entities near the right screen edge.

The text does not mention this limitation or suggest clamping/guarding against overflow.
**Severity:** MEDIUM — Undocumented edge-case bug in a key code example. Readers who use this code verbatim will get phantom collision failures near screen edges.

### T-12. Ch21 — IM2 handler does not save IY register
**File:** `/Users/alice/dev/antique-toy/chapters/ch21-full-game/draft.md`
**Lines:** 237-267
**What's wrong:** The IM2 interrupt handler pushes AF, BC, DE, HL, IX but does not push/pop IY. If the PT3 player or SFX update routine uses IY (which many PT3 players do), and the main game loop also uses IY (the collision code in ch19 uses IY extensively), the handler will corrupt IY. This is a classic 128K game bug.
**Severity:** MEDIUM — Missing register preservation in interrupt handler. Likely to cause intermittent crashes in real code.

---

## AI SMELL

### S-01. Ch19 — Vague opening quote with no attribution
**File:** `/Users/alice/dev/antique-toy/chapters/ch19-collisions/draft.md`
**Line:** 3
**Quote:** `"Every game is a lie. Physics is faked. Intelligence is a table lookup. The player never notices because the lies are told at 50 frames per second."`
**What's wrong:** This reads like a faux-profound epigraph generated by an LLM. It has no attribution. Compare to ch20's opening quote which is attributed to Introspec from a specific article. Unattributed philosophical quotes at chapter openings are a strong AI-smell signal.
**Severity:** LOW

### S-02. Ch21 — Unattributed opening quote
**File:** `/Users/alice/dev/antique-toy/chapters/ch21-full-game/draft.md`
**Line:** 4
**Quote:** `"The only way to know if your engine works is to ship a game."`
**What's wrong:** Same pattern as S-01. Generic wisdom with no attribution. Sounds AI-generated.
**Severity:** LOW

### S-03. Ch22 — Unattributed opening quote
**File:** `/Users/alice/dev/antique-toy/chapters/ch22-porting-agon/draft.md`
**Line:** 4
**Quote:** `"The same instruction set, a completely different machine."`
**What's wrong:** Same pattern. Three consecutive chapters with unattributed epigraphs that read like taglines.
**Severity:** LOW

### S-04. Ch22 — "This should be easy. It is not easy." rhetorical pattern
**File:** `/Users/alice/dev/antique-toy/chapters/ch22-porting-agon/draft.md`
**Lines:** 9-11
**Quote:** `"This should be easy. It is not easy. It is *different* in ways that will surprise you, and the surprises teach you things about both machines that you would not learn any other way."`
**What's wrong:** This is a classic LLM dramatic setup/subversion pattern. The short-sentence reversal followed by the vague promise of surprises is AI filler. The "surprises teach you things" clause adds nothing concrete.
**Severity:** LOW

### S-05. Ch22 — "What Each Platform Forces You To Do Better" section
**File:** `/Users/alice/dev/antique-toy/chapters/ch22-porting-agon/draft.md`
**Lines:** 726-753
**What's wrong:** This section reads like philosophical padding. Lines like "This discipline transfers to every platform you will ever work on" (line 733) and "Even on the Agon, where you have T-states to spare, writing tight inner loops is a habit worth keeping" (line 734) are generic truisms that add nothing a Z80 programmer does not already know. The section tells the reader that both platforms teach useful skills -- a conclusion so obvious it does not need 28 lines to state.

The most AI-smelling passage: "The Agon makes you a better *tool builder* --- writing converters, optimizers, asset pipeline scripts. The Spectrum makes you a better *optimizer* of the code itself. Both skills matter." (lines 751-752). This is the classic "balanced both-sides" wrap-up that LLMs produce when summarizing tradeoffs.
**Severity:** MEDIUM — The section is ~30 lines of padding in an otherwise practical chapter. Could be cut to 5 lines.

### S-06. Ch20 — "This is a general principle" transitional filler
**File:** `/Users/alice/dev/antique-toy/chapters/ch20-demo-workflow/draft.md`
**Line:** 152
**Quote:** `"This is a general principle. Demo workflow is not about doing everything in assembly. It is about using the right tool for each task."`
**What's wrong:** "This is a general principle" is a transitional phrase that LLMs insert when they want to extract a moral from a specific example. The sentence that follows is a truism. The paragraph works better without the first sentence.
**Severity:** LOW

### S-07. Ch20 — Section 20.8 ("MORE") is overwrought
**File:** `/Users/alice/dev/antique-toy/chapters/ch20-demo-workflow/draft.md`
**Lines:** 307-323
**What's wrong:** The treatment of Introspec's "MORE" essay is padded with interpretation that tells the reader how to feel:
- "The technology serves the art, not the other way around." (line 315) -- restating Introspec's point in blander language
- "The coder who treats these as afterthoughts produces a tech demo. The coder who treats them as design decisions produces a demo." (lines 319-320) -- the "the X who does Y vs the X who does Z" structure is an LLM pattern

The section would be stronger if it quoted more from Introspec and interpreted less.
**Severity:** LOW

### S-08. Ch20 — "You will not win" concluding paragraph
**File:** `/Users/alice/dev/antique-toy/chapters/ch20-demo-workflow/draft.md`
**Lines:** 388
**Quote:** `"You will not win. Your effects will be simpler than the experienced groups' entries. Your sync will be imperfect. Your transitions will be rough. None of this matters. What matters is that you finished a demo, submitted it to a compo, and joined a community that has been doing this for thirty years. The next demo will be better. And the one after that."`
**What's wrong:** This is a motivational speech to the reader. The "none of this matters / what matters is" reversal and the "the next X will be better. And the one after that" cadence are textbook LLM encouragement patterns. It is not wrong, but it feels like a pep talk from a chatbot rather than advice from a demoscener. Compare to Introspec's blunt "Two pixels suffice to tell a story" -- that is authentic voice. This is AI comfort.
**Severity:** MEDIUM — Undercuts the authentic voice that the rest of the chapter establishes.

### S-09. Ch23 — "Neither magic nor useless. A tool. Like HiSoft C, but different."
**File:** `/Users/alice/dev/antique-toy/chapters/ch23-ai-assisted/draft.md`
**Line:** 411
**Quote:** `"Neither magic nor useless. A tool. Like HiSoft C, but different."`
**What's wrong:** The staccato sentence fragments followed by the "balanced conclusion" is classic AI closing rhetoric. The comparison to HiSoft C is genuinely interesting (one of the chapter's best ideas), but this line reduces it to a bumper sticker.
**Severity:** LOW

### S-10. Ch23 — "The demoscene has always been about the last 20%"
**File:** `/Users/alice/dev/antique-toy/chapters/ch23-ai-assisted/draft.md`
**Lines:** 351-352
**Quote:** `"The demoscene has always been about the last 20%. The AI does not change that. It changes how fast you get through the first 80%."`
**What's wrong:** The 80/20 framing is an AI-generated aphorism. The demoscene is not "about the last 20%" in any measurable sense -- it is about the complete production. The line sounds good and says little.
**Severity:** LOW

### S-11. Ch23 — "If that makes you uncomfortable, good."
**File:** `/Users/alice/dev/antique-toy/chapters/ch23-ai-assisted/draft.md`
**Line:** 6
**Quote:** `"If that makes you uncomfortable, good. That discomfort is worth examining."`
**What's wrong:** This is a performatively confrontational opener that LLMs use to signal self-awareness. The "good. That discomfort is worth examining" is especially characteristic -- it positions the text as brave and thoughtful without actually being either.
**Severity:** LOW

### S-12. Ch23 — Section 23.10 is generic "broader picture" padding
**File:** `/Users/alice/dev/antique-toy/chapters/ch23-ai-assisted/draft.md`
**Lines:** 399-411
**What's wrong:** This section is 13 lines of generic observations about AI lowering barriers to entry. Every sentence could appear in any article about any tool for any creative domain:
- "What it changes is the speed of the input" (line 403)
- "lowers the entry barrier without lowering the ceiling" (line 405)
- "The experts will still write better inner loops than any AI" (line 405)
- "The demoscene thrives on participation" (line 407)

None of this is wrong. All of it is filler. The specific content of the chapter (MinZ case study, DOWN_HL analysis, Antique Toy experience) is far more valuable than this concluding generalization.
**Severity:** MEDIUM — Cut this section or reduce it to 2 sentences. The chapter's strength is its specificity; this section abandons that.

---

## SUMMARY

### Technical Errors: 10 found

| ID | Chapter | Severity | Issue |
|----|---------|----------|-------|
| T-01 | 19 | MEDIUM | AABB early exit T-state count wrong (claims 82T, actual 91T) |
| T-02 | 19 | HIGH | AABB worst-case T-state count wrong (claims 156T, actual ~270T) |
| T-03 | 19 | HIGH | tile_at cost wrong (claims ~40T, actual ~182T) |
| T-05 | 23 | HIGH | DOWN_HL example claimed buggy but is actually correct |
| T-07 | 22 | MEDIUM | ADL mode state table uses invalid `ld hl, a` instruction |
| T-08 | 22 | LOW | Frame budget comparison conflates eZ80 cycles with Z80 T-states |
| T-09 | 21 | LOW | CLEAR 32767 in BASIC loader is not best practice |
| T-10 | 22 | LOW | TST example poorly chosen (BIT 7,A works for that case) |
| T-11 | 19 | MEDIUM | AABB code silently wraps on X+width overflow near screen edge |
| T-12 | 21 | MEDIUM | IM2 handler does not save/restore IY |

### AI Smell: 12 found

| ID | Chapter | Severity | Issue |
|----|---------|----------|-------|
| S-01 | 19 | LOW | Unattributed faux-profound opening quote |
| S-02 | 21 | LOW | Unattributed opening quote |
| S-03 | 22 | LOW | Unattributed opening quote |
| S-04 | 22 | LOW | "This should be easy. It is not easy." reversal pattern |
| S-05 | 22 | MEDIUM | "What Each Platform Forces You To Do Better" is 30 lines of padding |
| S-06 | 20 | LOW | "This is a general principle" transitional filler |
| S-07 | 20 | LOW | Section 20.8 overwrought interpretation of Introspec's "MORE" |
| S-08 | 20 | MEDIUM | Motivational "you will not win" paragraph is chatbot pep talk |
| S-09 | 23 | LOW | "Neither magic nor useless. A tool." staccato closing |
| S-10 | 23 | LOW | "The demoscene has always been about the last 20%" aphorism |
| S-11 | 23 | LOW | "If that makes you uncomfortable, good" performative opener |
| S-12 | 23 | MEDIUM | Section 23.10 is generic "broader picture" filler |

### Highest-priority fixes:
1. **T-02 + T-03**: The T-state claims for AABB and tile_at are wrong by large factors. These feed into frame budget estimates that readers will rely on. Recount all instruction timings in ch19 code examples.
2. **T-05**: The DOWN_HL "failure" example in ch23 is the centerpiece of the "AI gets Z80 wrong" argument, but the code is correct. Either find an actually-buggy AI example, or fix the analysis.
3. **S-05 + S-08 + S-12**: Three MEDIUM-severity AI-smell sections that could be cut or condensed significantly.
