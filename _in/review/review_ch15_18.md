# Review: Chapters 15-18 -- Technical Accuracy and AI Smell

Reviewer: Claude Opus 4.6
Date: 2026-02-24

---

## Chapter 15: Anatomy of Two Machines

### Technical Accuracy Errors

**T-15-1. 48K contended memory claim is wrong**
File: `/Users/alice/dev/antique-toy/chapters/ch15-anatomy/draft.md`
Lines: 106-107
Quote:
```
| 48K | All RAM (`$4000`-`$FFFF`) | None (but `$8000`+ is less contended in practice) |
```
What's wrong: On the 48K Spectrum, only the lower 16KB of RAM ($4000-$7FFF) is contended -- this is the RAM shared with the ULA. The upper 32KB ($8000-$FFFF) is on separate RAM chips and is NOT contended at all. The table claims all RAM is contended with a vague hedge that "$8000+ is less contended in practice." It is not "less contended" -- it is uncontended. This contradicts the book's own advice to ORG at $8000 for fast, uncontended code.
Severity: **HIGH**

**T-15-2. 128K top border + bottom border line count**
File: `/Users/alice/dev/antique-toy/chapters/ch15-anatomy/draft.md`
Lines: 180, 185
Quote:
```
Top border  |  63 lines x 228T = 14,364T
Bottom border  |  56 lines x 228T = 12,768T
```
What's wrong: The exact distribution of top and bottom border lines on the 128K varies by source. The total (63+192+56 = 311 lines x 228T = 70,908T) is correct. However, several well-known references (e.g., the WoS "Timing Tests" documentation) give 64 top border lines and 55 bottom border lines for the 128K Toastrack. The source used here should be cited more precisely, since different 128K board revisions (Toastrack, +2 grey) have slightly different distributions. The math works out either way (the total is correct), but the specific line distribution may surprise readers who cross-reference.
Severity: **LOW**

**T-15-3. Stack default address omitted / potentially misleading**
File: `/Users/alice/dev/antique-toy/chapters/ch15-anatomy/draft.md`
Line: 27
Quote: `your main code (typically ORG'd at $8000) sits in page 2 where it will not disappear when you switch banks`
What's wrong: Not an error per se, but when the chapter discusses memory layout and the standard ORG address, it never warns that the BASIC system variables and stack area ($5B00-$5CBF, roughly) live within page 5 and can interfere with your code if you return to BASIC or if the ROM interrupt handler writes to them. For a chapter that aims to be "the hardware reference for everything that follows," this omission matters.
Severity: **LOW**

**T-15-4. Agon frame T-states calculation**
File: `/Users/alice/dev/antique-toy/chapters/ch15-anatomy/draft.md`
Lines: 503
Quote:
```
| T-states per frame (50 Hz) | ~70,908 (128K) / 71,680 (Pentagon) | ~368,640 |
```
What's wrong: The Agon runs at 60 Hz (VDP default), not 50 Hz. At 18.432 MHz and 60 Hz, the per-frame T-state count is 18,432,000 / 60 = 307,200. At 50 Hz it would be 368,640. The column header says "50 Hz" but the Agon natively runs at 60 Hz. This is internally inconsistent -- either the header should say "native frame rate" or the Agon number should reflect 60 Hz = ~307,200T. The text at line 396 ("typically 60 Hz") contradicts the 50 Hz assumption in the comparison table.
Severity: **MEDIUM**

### AI Smell

**A-15-1. "Liberating" flat memory space**
File: `/Users/alice/dev/antique-toy/chapters/ch15-anatomy/draft.md`
Line: 410
Quote: `After the Spectrum's 8-page juggling act, this is liberating.`
What's wrong: Mild emotional editorializing. "Liberating" is subjective filler. A factual comparison (e.g., "this eliminates all banking complexity") would be stronger.
Severity: **LOW**

**A-15-2. "A paradigm shift"**
File: `/Users/alice/dev/antique-toy/chapters/ch15-anatomy/draft.md`
Line: 398
Quote: `For Spectrum programmers, this is a paradigm shift.`
What's wrong: Buzzword. The sentence that follows ("You go from 'I write bytes to video memory...' to 'I send drawing commands...'") is the actual content; the introductory claim adds nothing.
Severity: **LOW**

**A-15-3. "Different constraints, same discipline"**
File: `/Users/alice/dev/antique-toy/chapters/ch15-anatomy/draft.md`
Line: 517
Quote: `Different constraints, same discipline.`
What's wrong: Platitude. Sounds like a motivational poster. Cut it.
Severity: **LOW**

---

## Chapter 16: Fast Sprites

### Technical Accuracy Errors

**T-16-1. XOR sprite inner loop cycle count is wrong**
File: `/Users/alice/dev/antique-toy/chapters/ch16-sprites/draft.md`
Lines: 31-65
Quote: `The inner loop costs 98 T-states per row in the common case (no boundary crossing)`
What's wrong: The actual cycle count for the common case (no boundary crossing, `jr nz` taken):
- `ld a,(ix+0)` = 19T
- `xor (hl)` = 7T
- `ld (hl),a` = 7T
- `inc l` = 4T
- `ld a,(ix+1)` = 19T
- `xor (hl)` = 7T
- `ld (hl),a` = 7T
- `dec l` = 4T
- `inc ix` = 10T
- `inc ix` = 10T
- `inc h` = 4T
- `ld a,h` = 4T
- `and 7` = 7T
- `jr nz,.no_boundary` = **12T** (taken)
- `djnz .row` = 13T

Total = 19+7+7+4+19+7+7+4+10+10+4+4+7+12+13 = **134T**, not 98T.

The error appears to stem from undercouting `jr nz` as 7T instead of 12T (the taken branch costs 12T, not 7T -- this is the common case), and possibly other miscounts. The claimed total of ~1,700T for 16 rows (16 x ~98 = 1,568, rounded to 1,700) should be ~2,144T (16 x 134) or ~2,200T with boundary crossings. The XOR sprite is actually closer in cost to the masked sprite than the text suggests.
Severity: **HIGH**

**T-16-2. JR NZ timing annotation wrong in XOR sprite code**
File: `/Users/alice/dev/antique-toy/chapters/ch16-sprites/draft.md`
Line: 48
Quote: `jr   nz, .no_boundary   ;  7 T   /  boundary crossing`
What's wrong: `JR NZ` when the condition is met (branch taken) costs 12T, not 7T. The 7T cost applies only when the branch is NOT taken (i.e., when there IS a boundary crossing and the code falls through). Since the common case is no boundary crossing (branch taken), the annotation should read 12T.
Severity: **HIGH** (because it cascades into the total cycle count claim)

**T-16-3. JR NZ timing annotation wrong in masked sprite code**
File: `/Users/alice/dev/antique-toy/chapters/ch16-sprites/draft.md`
Line: 145
Quote: `jr   nz, .no_boundary   ;  7 T`
What's wrong: Same error as T-16-2. In the common case (no boundary crossing), `JR NZ` is taken = 12T, not 7T.
Severity: **HIGH**

**T-16-4. Masked sprite row advance cost wrong in cycle table**
File: `/Users/alice/dev/antique-toy/chapters/ch16-sprites/draft.md`
Lines: 168-170
Quote:
```
| Row advance | `inc h` + `ld a,h` + `and 7` + `jr nz` | 22 |
```
What's wrong: `inc h` (4T) + `ld a,h` (4T) + `and 7` (7T) + `jr nz` (12T when taken, common case) = 27T, not 22T. The total per row should be 52+52+27+13 = **144T**, not 139T. The 16-row total should be ~2,304T (not 2,224T), and with boundary crossings ~2,400T (not ~2,300T). The relative conclusions still hold (masked is more expensive than XOR), but the specific numbers are off by ~5%.
Severity: **MEDIUM**

**T-16-5. Compiled sprite per-byte cost claim "28 T-states" is correct but row cost math is wrong**
File: `/Users/alice/dev/antique-toy/chapters/ch16-sprites/draft.md`
Lines: 476-485
Quote:
```
    ld   a, (hl)            ;  7 T   read screen
    and  $C3                ;  7 T   mask: clear sprite pixels
    or   $3C                ;  7 T   graphic: stamp sprite
    ld   (hl), a            ;  7 T   write back
                            ;        per-byte cost: 28 T
```
Then: `For 16 rows x 2 bytes: 16 x (28 + 28 + 4 + 4 + 4) = 16 x 68 = 1,088 T-states`
What's wrong: The row cost breakdown is 28 (left byte) + 28 (right byte) + 4 (`inc l`) + 4 (`dec l`) + 4 (`inc h`) = 68T. But this omits the character boundary check (the same `ld a,h / and 7 / jr nz` sequence = 15T in the common case, or 27T with the `jr nz` at 12T). Without any boundary check or row advance logic, the compiled sprite just hardcodes `inc h`, but that only works within a character cell. For rows crossing character boundaries, extra code is needed (the text shows this at line 441-448 as 30T). The 68T per row figure is only correct for the 6 rows within a character cell that don't cross a boundary; the 2 boundary-crossing rows cost ~92T. A more accurate total: 12 rows x 68T + 2 rows x ~92T + last-row (no inc h) = 816 + 184 + ~60 = ~1,060T. The claimed 1,088T is in the right ballpark but the derivation is imprecise.
Severity: **LOW**

**T-16-6. LDI timing in save background optimization**
File: `/Users/alice/dev/antique-toy/chapters/ch16-sprites/draft.md`
Lines: 614
Quote: `an LDI chain (Chapter 3) copies a byte from (HL) to (DE), increments both, and decrements BC --- all in 16 T-states`
What's wrong: LDI also decrements BC and resets the P/V flag. The timing (16T) is correct. However, the text later claims the manual approach is 24T per byte: `ld a,(hl)` (7T) + `ld (de),a` (7T) + `inc de` (6T) + `inc l` (4T) = 24T. That is correct. But after two LDIs (32T), the text says we need `dec l / dec l` (4+4 = 8T) to undo L advancement. So actual per-row LDI cost is 16+16+4+4 = 40T for data + row navigation, not 32T for data alone. The text handles this correctly in the code at lines 621-643, where the common-case row is tallied as 75T. No error here, just noting the analysis is sound.
Severity: **(no issue)**

**T-16-7. Agon baud rate inconsistency**
File: `/Users/alice/dev/antique-toy/chapters/ch16-sprites/draft.md`
Line: 754
Quote: `At 1,152,000 baud, each byte takes roughly 9 microseconds`
What's wrong: Chapter 15, line 394 states the serial link runs at "384,000 baud" (384 Kbaud). Chapter 16 says "1,152,000 baud." These are different. The Agon Light 2 VDP serial link actually runs at 1,152,000 baud in firmware 2.x+. If ch15 is citing an older firmware version, it should note this. Regardless, the two chapters contradict each other.
Severity: **MEDIUM**

### AI Smell

**A-16-1. "the entire problem collapses to a handful of API calls"**
File: `/Users/alice/dev/antique-toy/chapters/ch16-sprites/draft.md`
Line: 11
Quote: `where the VDP provides hardware sprites and the entire problem collapses to a handful of API calls`
What's wrong: Overly dramatic phrasing. "The problem collapses" is theatrical. "The VDP handles sprites via API calls" says the same thing without the drama.
Severity: **LOW**

**A-16-2. "Both approaches have their satisfactions"**
File: `/Users/alice/dev/antique-toy/chapters/ch16-sprites/draft.md`
Line: 856
Quote: `Both approaches have their satisfactions.`
What's wrong: Empty diplomatic filler. Adds nothing technical. Cut or replace with something specific.
Severity: **LOW**

---

## Chapter 17: Scrolling

### Technical Accuracy Errors

**T-17-1. LDIR cost for 6,144 bytes is wrong**
File: `/Users/alice/dev/antique-toy/chapters/ch17-scrolling/draft.md`
Lines: 27-28
Quote:
```
| `ldir` | 21 T | 129,003 T | 180% |
```
What's wrong: LDIR for 6,144 bytes costs (6,144 - 1) x 21 + 16 = 6,143 x 21 + 16 = 129,003 + 16 = **129,019T**. The table shows 129,003, which omits the 16T cost of the final LDI iteration. The "per byte" column says 21T, but the last byte only costs 16T -- the "21T per byte" is an approximation. The exact total is 129,019T. The percentage should be 129,019 / 71,680 = 180.0%, so the percentage is coincidentally still correct.
Severity: **LOW**

**T-17-2. LDIR cost for 767 bytes in attribute scroll**
File: `/Users/alice/dev/antique-toy/chapters/ch17-scrolling/draft.md`
Lines: 193-194
Quote:
```
    ld   bc, 767            ; 10 T  768 - 1 bytes
    ldir                    ; 767*21 + 16 = 16,123 T
```
What's wrong: The LDIR is copying 767 bytes (BC=767). The cost is: (767-1)*21 + 16 = 766*21 + 16 = 16,086 + 16 = 16,102T. But the comment says "767*21 + 16 = 16,123". Let me check: 767*21 = 16,107. 16,107 + 16 = 16,123. But that formula is wrong -- it should be (767-1)*21 + 16 = (766)*21 + 16, because the LAST iteration of LDIR costs 16T (not 21T), and there are 767 iterations total (766 at 21T + 1 at 16T). So the correct cost is 766*21 + 16 = 16,102T, not 16,123T. The difference is 21T (one extra 21T iteration counted instead of 16T). The error is small but the formula in the comment is wrong.

Actually wait -- let me reconsider the LDIR mechanics. LDIR: it repeats LDI. Each LDI is 16T. After each LDI, if BC != 0, the PC backs up by 2 (costing 5 extra T, total 21T for that iteration). If BC = 0, the instruction ends at 16T. So for BC=767 initially: 766 iterations at 21T + 1 final iteration at 16T = 766*21 + 16 = 16,086 + 16 = 16,102T. The comment's formula (767*21 + 16) double-counts: it does N*21 + 16, but it should be (N-1)*21 + 16. The same formula error appears in the LDIR cost table at line 28.
Severity: **LOW**

**T-17-3. Scroll direction explanation error for RL**
File: `/Users/alice/dev/antique-toy/chapters/ch17-scrolling/draft.md`
Lines: 118-138
Quote: `For a leftward scroll, each pixel moves one position left. Bit 7 is the leftmost pixel in a byte, bit 0 the rightmost. Shifting left means each byte's bit 7 exits and must enter bit 0 of the byte to its left. The carry flag bridges adjacent bytes, so we process the row from right to left`
Then:
```
    rl   (hl)                 ; 15 T  shift left, bit 7 -> carry, carry -> bit 0
```
What's wrong: The `RL (HL)` instruction rotates LEFT through carry: bit 7 goes to carry, carry goes to bit 0, all other bits shift left by one position. When scrolling the screen LEFT by 1 pixel, each pixel must move to the next higher bit position (toward bit 7). Processing right to left: start with the rightmost byte, RL it (bit 7 goes to carry), move to the next byte left, RL it (carry from previous byte enters bit 0, bit 7 goes to carry for the next byte).

Wait -- this is actually correct. When scrolling left, pixels shift toward bit 7 (leftward in the byte). RL shifts all bits left (bit n -> bit n+1). Bit 7 exits to carry. Carry enters bit 0. Processing from right to left, the carry propagates the exiting bit 7 of byte N into bit 0 of byte N-1. This means pixel data moves left across byte boundaries. Correct.

But the clear carry at the start (`or a` = clear carry) means bit 0 of the rightmost byte gets 0 -- the right edge gets a blank pixel. Also correct for a leftward scroll.

No error here. Retracted.
Severity: **(no issue)**

**T-17-4. Per-row cost for RL chain arithmetic inconsistency**
File: `/Users/alice/dev/antique-toy/chapters/ch17-scrolling/draft.md`
Lines: 140-142
Quote:
```
Each byte costs: 15 (RL (HL)) + 6 (DEC HL) = 21 T-states per byte. For 32 bytes per row: 32 x 21 - 6 = 666 T-states per row (we do not need the final DEC HL).

Actually, the first byte needs OR A (4 T) to clear carry. So one row costs: 4 + 32 x 15 + 31 x 6 = 4 + 480 + 186 = 670 T-states.
```
What's wrong: The two calculations give different answers (666 vs 670) and the text presents both as if the second supersedes the first. Let's verify: 32 RL operations at 15T = 480T. 31 DEC HL at 6T = 186T. OR A at 4T = 4T. Total = 480 + 186 + 4 = 670T. The first formula (32 x 21 - 6 = 666) is wrong because it subtracts 6 for the missing final DEC but doesn't account for the OR A. The 670T figure is correct. The 666T figure should have been noted as incomplete (missing the OR A cost), not presented as a standalone calculation. This is confusing but the final 670T answer is correct.
Severity: **LOW**

**T-17-5. Character scroll cost estimate claims "LDIR of 19 bytes" but formula is inconsistent**
File: `/Users/alice/dev/antique-toy/chapters/ch17-scrolling/draft.md`
Lines: 375-376
Quote:
```
    ld   bc, 19              ; 19 bytes to copy
    ldir                     ; 18*21 + 16 = 394 T
```
What's wrong: LDIR for BC=19: (19-1)*21 + 16 = 18*21 + 16 = 378 + 16 = 394T. This is actually correct. (The formula here is right -- (N-1)*21 + 16.) Consistent with itself though inconsistent with the formula used at line 194 (where 767*21 + 16 was used instead of (767-1)*21 + 16).
Severity: **(no issue -- formula here is correct; the earlier one was wrong)**

**T-17-6. Cross-reference to Chapter 21**
File: `/Users/alice/dev/antique-toy/chapters/ch17-scrolling/draft.md`
Line: (not present, but ch15 line 65 references it)
Context: Ch15 says "We will use this heavily in Chapter 17 (Scrolling) and Chapter 21 (Full Game)."
What's wrong: The book outline (`book-outline.md`) should be checked to verify Chapter 21 exists and is indeed a "Full Game" chapter. This is a cross-reference from ch15, not ch17. Noting for completeness.
Severity: **LOW**

### AI Smell

**A-17-1. "It looks simple" / "considerably more interesting"**
File: `/Users/alice/dev/antique-toy/chapters/ch17-scrolling/draft.md`
Lines: 7, 40
Quote: `It looks simple.` and `makes it considerably more interesting`
What's wrong: "Considerably more interesting" is a euphemism for "much harder." It is a mild AI-ism -- hedging a difficulty claim behind a positive-sounding word. Not severe.
Severity: **LOW**

**A-17-2. "This is not a criticism of either platform"**
File: `/Users/alice/dev/antique-toy/chapters/ch17-scrolling/draft.md`
Line: 607
Quote: `This is not a criticism of either platform. It is a demonstration of how hardware design choices propagate through every level of the software.`
What's wrong: Defensive balancing statement. No reader would have read the preceding factual comparison as a "criticism." This is the classic AI pattern of preemptively neutralizing any impression of bias. Cut the first sentence; keep the second if desired.
Severity: **MEDIUM**

---

## Chapter 18: Game Loop and Entity System

### Technical Accuracy Errors

**T-18-1. `HALT` instruction T-state annotation**
File: `/Users/alice/dev/antique-toy/chapters/ch18-gameloop/draft.md`
Line: 39
Quote: `halt                    ; 4T + wait -- sync to frame interrupt`
What's wrong: The `HALT` instruction itself takes 4T to execute (entering halt state), but then the CPU executes NOPs (4T each) until an interrupt arrives. The annotation "4T + wait" is imprecise but not wrong. More precisely: HALT = 4T to enter halt mode, then the CPU consumes NOP cycles until the interrupt. The total time spent is variable (up to one full frame). The annotation is acceptable shorthand.
Severity: **(no issue)**

**T-18-2. JR timing annotation**
File: `/Users/alice/dev/antique-toy/chapters/ch18-gameloop/draft.md`
Line: 45
Quote: `jr   main_loop          ; 12T -- loop forever`
What's wrong: `JR e` (unconditional) = 12T. Correct.
Severity: **(no issue)**

**T-18-3. `JP (HL)` description is correct but potentially misleading**
File: `/Users/alice/dev/antique-toy/chapters/ch18-gameloop/draft.md`
Lines: 137, 141
Quote:
```
    jp   (hl)               ; 4T   jump to handler
```
Then: `The JP (HL) instruction is the key. It does not jump to the address stored at HL -- it jumps to the address in HL.`
What's wrong: The clarification is correct and important. `JP (HL)` is infamously misnamed in Zilog's mnemonics -- it should be `JP HL`. The text correctly clarifies this. No error.
Severity: **(no issue)**

**T-18-4. CP chain analysis overestimates per-state cost**
File: `/Users/alice/dev/antique-toy/chapters/ch18-gameloop/draft.md`
Lines: 217
Quote: `each additional state adds a CP (7T) and a JP Z (10T), so the worst case is 17T per state`
What's wrong: `CP n` = 7T, `JP Z, nn` = 10T. Total = 17T. Correct. `JP cc, nn` is always 10T regardless of whether the condition is met (unlike JR cc which is 12T/7T). This is correct.
Severity: **(no issue)**

**T-18-5. `BIT b, r` timing wrong in keyboard reader**
File: `/Users/alice/dev/antique-toy/chapters/ch18-gameloop/draft.md`
Lines: 275-276
Quote:
```
    bit  0, a               ; 8T   P key
    jr   nz, .no_right      ; 12/7T
```
What's wrong: `BIT b, r` = 8T. Correct. `JR NZ, e` = 12T taken / 7T not taken. Correct. These annotations are fine.
Severity: **(no issue)**

**T-18-6. `SET b, r` timing in keyboard reader**
File: `/Users/alice/dev/antique-toy/chapters/ch18-gameloop/draft.md`
Line: 277
Quote: `set  INPUT_RIGHT, d     ; 8T`
What's wrong: `SET b, r` = 8T. Correct.
Severity: **(no issue)**

**T-18-7. `IN A, (n)` vs `IN A, (C)` timing**
File: `/Users/alice/dev/antique-toy/chapters/ch18-gameloop/draft.md`
Line: 329
Quote: `in   a, (KEMPSTON_PORT)  ; 11T`
What's wrong: `IN A, (n)` = 11T. Correct. Note this is the single-byte port form where the port address low byte is the immediate operand and A is placed on the high address byte. For Kempston port $1F, this is correct -- the high byte doesn't matter for Kempston.
Severity: **(no issue)**

**T-18-8. Entity movement -- sign extension using RLA+SBC A,A**
File: `/Users/alice/dev/antique-toy/chapters/ch18-gameloop/draft.md`
Lines: 498-500
Quote:
```
    rla                      ; 4T   carry = sign bit
    sbc  a, a               ; 4T   A = $FF if negative, $00 if positive
    ld   d, a               ; 4T   DE = signed 16-bit dx
```
What's wrong: `RLA` rotates A left through carry: bit 7 -> carry, carry -> bit 0. After `ld e, a` (which loaded the velocity byte into E), A still holds the velocity byte. `RLA` puts bit 7 (sign bit) into carry. Then `SBC A, A` computes A - A - carry = 0 - carry. If carry=1 (negative velocity), A = $FF. If carry=0 (positive), A = $00. This is a correct sign extension technique.

But wait: before the `rla`, A was modified by `ld e, a` (which loaded E from A). No -- `ld e, a` copies A into E but doesn't change A. So A still holds the velocity value. Then `rla` rotates A left (destroying A's value in the process), putting bit 7 into carry. Then `sbc a, a` produces the sign extension. Correct.
Severity: **(no issue)**

**T-18-9. Stack pointer set to $FFFF**
File: `/Users/alice/dev/antique-toy/chapters/ch18-gameloop/draft.md`
Line: 885
Quote: `ld   sp, $FFFF          ; set stack`
What's wrong: Setting SP to $FFFF means the first `PUSH` will decrement SP by 2 to $FFFD and write the high byte at $FFFE and low byte at $FFFD. This is fine, but note that $FFFF is in the banked page slot ($C000-$FFFF). If the page is switched while stack operations are in progress, this will corrupt data. The code should either set SP to a known safe location in page 2 ($BFFF or lower) or ensure page switching never occurs during stack operations. For a game skeleton that includes bank switching (referenced in ch15), putting the stack in the banked region is a latent bug.

This contradicts ch15's own rule at line 84: "your interrupt handler and main loop must live in pages 2 or 5." The stack should also be in uncontended, non-banked memory.
Severity: **MEDIUM**

**T-18-10. `add a, (ix+1)` in enemy and bullet update**
File: `/Users/alice/dev/antique-toy/chapters/ch18-gameloop/draft.md`
Lines: 1222, 1248
Quote:
```
    ld   a, (ix + 6)        ; dx
    add  a, (ix + 1)        ; add to X pixel
```
What's wrong: `ADD A, (IX+d)` = 19T. The timing is not annotated here but the instruction is valid. However, the enemy update uses integer addition to X pixel (not fixed-point), while the player update uses sub-pixel fixed-point addition with carry propagation. The dx field for enemies is described as "signed, fixed-point fractional" at line 429. But the enemy update treats it as an integer pixel delta (adding dx directly to the pixel byte). This is a design inconsistency -- the entity structure defines dx as fractional, but the enemy handler uses it as integer. Not a Z80 error, but a logic bug in the game skeleton.
Severity: **LOW** (it works in practice since enemies use dx=1, but the code contradicts the data structure definition)

**T-18-11. `ADD IX, DE` with potentially dirty D register in spawn_bullet**
File: `/Users/alice/dev/antique-toy/chapters/ch18-gameloop/draft.md`
Lines: 683, 1289-1293
Quote (from the first spawn_bullet version, line 683):
```
    ld   e, ENTITY_SIZE     ; 7T
    add  ix, de             ; 15T  next slot (note: DE high byte may be nonzero,
                            ;      but we only care about the low 8 bits of offset)
```
What's wrong: The comment acknowledges that D might be nonzero. `ADD IX, DE` adds the full 16-bit DE to IX. If D is nonzero, IX gets corrupted. The code at line 675 sets `d` to the loop counter, so D = 7 initially and decrements. So on the first iteration, `ADD IX, DE` adds 7*256 + 10 = 1802 to IX instead of 10. This is a real bug. The second version of spawn_bullet (lines 1289-1293) has the same issue but attempts to work around it with an odd `push de / pop de` sequence that doesn't actually fix anything.

Actually, looking at the second version more carefully (lines 1289-1293):
```
    ld   e, ENTITY_SIZE
    push de
    pop  de                  ; (DE preserved; only low byte matters for add ix,de)
    ld   e, ENTITY_SIZE
    add  ix, de
```
This `push de / pop de` is a no-op that accomplishes nothing, and then it loads E again. D still has whatever value it had from `dec d` above. The comment claims "only low byte matters" but that's false -- `ADD IX, DE` uses all 16 bits of DE. This is a genuine code bug.
Severity: **HIGH** (broken code in a compilable example)

### AI Smell

**A-18-1. "A game is a demo that listens."**
File: `/Users/alice/dev/antique-toy/chapters/ch18-gameloop/draft.md`
Line: 4
What's wrong: This is the chapter epigraph. As a one-liner quote attributed to no one, it reads as generated aphorism. If it's original, it's fine but should be attributed. If it's meant to sound profound, it reads as AI-generated filler.
Severity: **LOW**

**A-18-2. "no allocator, no garbage collector, no free list. Just an array and a flag."**
File: `/Users/alice/dev/antique-toy/chapters/ch18-gameloop/draft.md`
Line: 840
Quote: `no allocator, no garbage collector, no free list. Just an array and a flag.`
What's wrong: This is a rhetorical flourish, but it actually communicates a real technical point effectively. Borderline, but acceptable.
Severity: **(no issue)**

**A-18-3. "The discipline of counting every T-state still matters (it is good engineering), but the constraints that force agonising trade-offs on the Spectrum simply do not apply."**
File: `/Users/alice/dev/antique-toy/chapters/ch18-gameloop/draft.md`
Line: 1414
Quote: (see above)
What's wrong: The parenthetical "(it is good engineering)" is unnecessary editorializing. The reader of a Z80 assembly book already knows cycle counting matters. Cut the parenthetical.
Severity: **LOW**

---

## Summary of Findings

### High Severity
| ID | Chapter | Issue |
|----|---------|-------|
| T-15-1 | Ch15 | 48K contended memory claim wrong -- only $4000-$7FFF is contended, not all RAM |
| T-16-1 | Ch16 | XOR sprite cycle count wrong: actual is ~134T/row, not 98T/row |
| T-16-2 | Ch16 | `JR NZ` annotated as 7T in XOR sprite (should be 12T when taken) |
| T-16-3 | Ch16 | `JR NZ` annotated as 7T in masked sprite (should be 12T when taken) |
| T-18-11 | Ch18 | `ADD IX, DE` with dirty D register in spawn_bullet -- actual code bug |

### Medium Severity
| ID | Chapter | Issue |
|----|---------|-------|
| T-15-4 | Ch15 | Agon listed at 50Hz/368,640T but actually runs at 60Hz (~307,200T) |
| T-16-4 | Ch16 | Masked sprite row advance cost: 27T not 22T, total per row 144T not 139T |
| T-16-7 | Ch16 | Agon baud rate: ch15 says 384Kbaud, ch16 says 1.152Mbaud -- contradiction |
| T-18-9 | Ch18 | Stack at $FFFF is in banked memory region -- latent bug with bank switching |
| A-17-2 | Ch17 | "This is not a criticism of either platform" -- defensive AI balancing pattern |

### Low Severity
| ID | Chapter | Issue |
|----|---------|-------|
| T-15-2 | Ch15 | 128K top/bottom border line distribution may differ from some references |
| T-15-3 | Ch15 | No warning about system variables / default stack in page 5 |
| T-16-5 | Ch16 | Compiled sprite row cost derivation imprecise (boundary rows omitted) |
| T-17-1 | Ch17 | LDIR for 6,144 bytes: 129,019T not 129,003T (missing final 16T) |
| T-17-2 | Ch17 | LDIR formula in attribute scroll comment uses N*21+16 instead of (N-1)*21+16 |
| T-17-4 | Ch17 | Two RL-chain cost calculations (666 vs 670) presented confusingly |
| T-18-10 | Ch18 | Enemy dx treated as integer but entity structure defines it as fractional |
| A-15-1 | Ch15 | "this is liberating" -- emotional editorializing |
| A-15-2 | Ch15 | "a paradigm shift" -- buzzword |
| A-15-3 | Ch15 | "Different constraints, same discipline" -- platitude |
| A-16-1 | Ch16 | "the entire problem collapses" -- theatrical phrasing |
| A-16-2 | Ch16 | "Both approaches have their satisfactions" -- empty diplomatic filler |
| A-17-1 | Ch17 | "considerably more interesting" -- AI euphemism for "harder" |
| A-18-1 | Ch18 | "A game is a demo that listens" -- unattributed aphorism |
| A-18-3 | Ch18 | "(it is good engineering)" -- unnecessary parenthetical editorializing |
