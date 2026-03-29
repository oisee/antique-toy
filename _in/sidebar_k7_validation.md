# Sidebar K.7: Three-Level Validation — How GPU Discovers What Humans Miss

> *The carry_compare trick for division was not found in any Z80 reference, textbook, or forum post. A GPU found it by trying everything.*

## The Problem

Given: build a table of optimal Z80 sequences for `A ÷ K` (unsigned 8-bit division by constant) for all K = 2..255.

The obvious approach — GPU brute-force over individual Z80 instructions — fails. Division by 3 requires 16 instructions (A×171>>9), but GPU search at depth ≤8 finds nothing. The search space at depth 16 (21^16 ≈ 10^21) is beyond any GPU.

## Level 1: Analytical (Hacker's Delight)

The textbook solution: for each K, find magic multiplier M and shift S such that `floor(A × M / 2^S) = floor(A / K)` for all A = 0..255.

This works. For every K, there exists an M ≤ 510 and S ≤ 19. Compose with our existing mul16 table (254 proven-optimal multiply sequences) and a chain of SRL instructions:

```
div K = LD H,0; LD L,A; mul16[M]; LD A,H; SRL A × (S−8)
```

**Result: 254/254 divisors solved.** Average: **154 T-states.**

But is this optimal? We have no proof. The analytical approach finds *a* solution, not *the best* solution.

## Level 2: Composite Search (Human Intuition + Automation)

Key insight: the analytical formula only tries `A × M >> S`. But what about:

- **Pre-shift**: `(A >> P) × M >> S` — shift right first, then multiply a smaller number
- **Double multiply**: `A × M1 × M2 >> S` — factor M into two smaller multiplies
- **Round-down correction**: Hacker's Delight "add-and-shift" variant

We enumerate all these *structural* decompositions and pick the cheapest per K:

```python
for pre_shift in range(1, 8):        # try (A >> P) first
    for M in range(2, 256):           # then multiply
        for S in range(8, 20):        # then shift
            if verify_all_256(K, pre_shift, M, S):
                cost = SRL×P + preamble + mul16[M] + postamble
                track_best(K, cost)
```

**Result: 140/254 improved.** New average: **135 T-states** (−12%).

Star discovery: **PRESHIFT** — `div86 = (A>>1) × 6 >> 8` costs just **60T** (was 170T). Exploits that 86 = 2 × 43, and ×6 has a short mul16 sequence.

## Level 3: GPU Exhaustive (No Assumptions)

Meanwhile, we had a background GPU search running on the original brute-force kernel — searching depth ≤6 sequences from a pool of 21 Z80 instructions, with a parametric B register (pre-loaded with a constant).

For K < 128, it found nothing new (sequences too short). But for K ≥ 128, it found **128 solutions** with this pattern:

```z80
OR   A          ; 4T   clear carry
LD   B, (256−K) ; 7T   preload threshold
ADC  A, B       ; 4T   A + (256−K) + 0 — overflows iff A ≥ K
SBC  A, A       ; 4T   A = 0xFF if carry, 0x00 if not
AND  1          ; 7T   A = 1 if A ≥ K, 0 otherwise
```

**5 instructions. 26 T-states. For ALL K ≥ 128.**

This works because when K ≥ 128, the quotient `floor(A/K)` can only be 0 or 1. The ADC overflow is a *comparison*, and SBC A,A materializes the carry into a mask.

**No human found this.** Not in Hacker's Delight. Not on any Z80 forum. Not in SDCC source. The GPU tried 21^6 × 256 = 23 billion sequences per K value and found the one that works.

## The Combined Result

| Level | Method | avg T | Δ from prev | Discoveries |
|-------|--------|-------|-------------|-------------|
| 1 | Analytical | 154T | baseline | multiply-and-shift formula |
| 2 | Composite | 135T | −12% | PRESHIFT, DOUBLE_MUL |
| 3 | GPU exhaustive | **79T** | **−49%** | **carry_compare** |

Each level found optimizations the others *could not*:

- **Analytical** provides the mathematical foundation — without it, we'd have no div3 or div10 at all (they need 16+ instructions, far beyond GPU depth)
- **Composite search** exploits structural patterns (factorization of K) — the search space is small enough for Python, but requires human insight about *what structures to try*
- **GPU exhaustive** makes no assumptions about structure — it found a trick that no textbook describes, because no human thought to search for it

## Verification: Four Independent Systems

The carry_compare trick was cross-verified on four independent implementations:

| System | Method | Scope | Result |
|--------|--------|-------|--------|
| z80-optimizer | Python exhaustive | 128 × 256 = 32,768 | ALL PASS |
| MinZ compiler | Python simulation | 32,768 | ALL PASS |
| MinZ-VIR backend | VIR IntrinsicTable + Z80 emulator | 32,768 | ALL PASS |
| MinZ-ABAP frontend | MIR2 VM + Z80 emu + LLVM lli | 22 assertions | ALL PASS |

The final table: **254/254 divisors, 6 methods, average 79 T-states** — faster than SDCC's generic `__div8` runtime (80–200T) even on the *average* divisor.

## The Methodology

This three-level approach generalizes beyond division:

1. **Analytical**: derive formulas from first principles. Covers the cases where the answer has known mathematical structure. Fast, complete for its domain, but limited by what humans know to look for.

2. **Composite search**: enumerate *structural decompositions* that combine proven building blocks (our mul8/mul16/u32 tables). Covers the gap between "formula exists" and "GPU can reach it." Requires human insight about what structures are promising.

3. **GPU exhaustive**: try everything, assume nothing. Covers the cases where the optimal solution has no known mathematical structure. Limited by search depth, but finds tricks nobody thought to look for.

The levels are complementary, not redundant. Running only Level 1 leaves 49% performance on the table. Running only Level 3 can't find sequences longer than depth 8. Together, they produce results that neither could achieve alone.

---

*Data: `data/div8_optimal.json` (v3, 254 entries). Scripts: `scripts/gen_div8_table.py` (L1), `scripts/composite_div_search.py` (L2), GPU kernel `cuda/z80_divmod_fast.cu` (L3). Cross-verification logs in `contexts/day6_wisdom.md`.*
