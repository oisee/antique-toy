# Appendix O: What 755 Optimal Sequences Teach Us About Computation

> *Structure emerges from exhaustion. None of these patterns were predicted in advance.*

---

## O.1 Introduction

Between late 2025 and early 2026, a brute-force superoptimizer exhaustively searched every possible Z80 instruction sequence up to length 11, verifying full-state equivalence across all input combinations. The result is not a heuristic --- it is a certificate of optimality for 755 arithmetic sequences.

The raw tables are useful on their own (Appendix K). But they also contain *structure* --- patterns that nobody designed, visible only when you look at hundreds of optimal programs simultaneously and ask: what do they have in common? What do they avoid?

This appendix extracts ten such patterns.

---

## O.2 The 21-Instruction Thesis

The Z80 has approximately 700 documented instructions. Only **21** appear in any optimal arithmetic sequence across all multiply, divide, and conversion tables --- just **2.7% of the ISA**.

The 21 survivors cluster into functional roles:

- **Shift/rotate** (7): RLCA, RRCA, RLA, RRA, SLA A, SRA A, SRL A
- **Arithmetic** (6): ADD A,A, ADD A,B/C/D/E/H/L
- **Negate/complement** (2): NEG, CPL
- **Load/save** (3): LD B/C/D,A
- **Conditional mask** (1): SBC A,A
- **Clear** (1): XOR A
- **Subtract** (1): SUB reg

Seven candidate operations *never* appear in any optimal solution. They are strictly dominated --- there always exists a shorter sequence using other instructions that achieves the same effect. The gap between "could be useful" and "is ever useful" is wide.

---

## O.3 Disjoint Worlds

The 8-bit multiply table (mul8: A register) and the 16-bit multiply table (mul16: HL pair) share **zero instructions**. Not one.

mul8 lives entirely in the A-register world: RLCA, ADD A,A, NEG, SBC A,A. mul16 lives in the HL-register world: ADD HL,HL, ADD HL,BC, LD C,A. Both compute constant multiplication, but the Z80's heterogeneous register file forces them through incompatible algorithm families.

Division bridges the two: reciprocal multiplication in HL, followed by extraction to A via `LD A,H`.

---

## O.4 Rotation Dominance in Nonlinear Approximation

In approximate function search (sqrt, log2, cbrt), `RRCA` appears at **276% frequency** --- the average sequence uses it 2.76 times.

Rotations are how linear arithmetic "sees" individual bits. After `RRCA`, the MSB contains what was previously the LSB. A subsequent addition produces a value that mixes low and high bit-fields --- exactly what nonlinear functions require. The rotation-addition pair is the minimal nonlinear basis for bit-level computation.

---

## O.5 Compression via Computation

A 256-byte lookup table for sqrt occupies 256 bytes of ROM. The GPU found a 12-byte instruction sequence that generates the same table to within acceptable error --- **20:1 compression**, not via entropy coding but via computation. The "decompressor" is the CPU itself. (See Appendix N for details.)

Each additional compound operation reduces maximum error by ~30%. The error-depth curve suggests a fundamental property: the set of functions computable by sequences of length N grows combinatorially, and the distance to any target function shrinks predictably as N increases.

---

## O.6 Division IS Multiplication

**100% of division chains** contain a multiplication step as a substring. Between 64% and 92% of the instructions in each div8 sequence are literally mul8 code operating on the reciprocal constant, followed by a small correction suffix.

The superoptimizer rediscovered from first principles what *Hacker's Delight* proved algebraically: division by K equals multiplication by the modular inverse of K. The mul8 library is literally a *substrate* on which division is built.

---

## O.7 Carry-to-Mask: The Universal Conditional

`SBC A,A` --- subtract A from A with carry --- produces \$FF if carry is set, \$00 if clear. It converts a 1-bit condition into a full-byte mask.

This single instruction appears in **100% of branchless conditional idioms** and in the majority of nonlinear approximation sequences. The pattern:

```z80
    CP   threshold    ; sets carry if A < threshold
    SBC  A, A         ; A = $FF if true, $00 if false
    AND  correction   ; mask the correction value
    ADD  A, base      ; apply conditional correction
```

This replaces a branch (10--17 cycles) with a fixed-time branchless sequence. No ISA designer planned `SBC A,A` as a conditional --- the superoptimizer found it.

---

## O.8 The Prefix Sharing Structure

Consecutive constants share remarkably long common prefixes in their optimal sequences. The programs for ×K and ×(K+1) typically share **9--10 instruction prefixes** before diverging.

This enables the packed multi-entry library format (Appendix K): 254 constant multiplications in ~2KB via fall-through chains. It also hints at a deeper **metric space structure** --- numbers close in value have close optimal programs. The shift-add decomposition of integers imposes a smoothness on program space that mirrors the smoothness of the integers themselves.

---

## O.9 Fixed-Point Scaling Affects Search Difficulty

When searching for sqrt approximations, f4.4 format (4 integer bits, 4 fractional) converges faster than f3.5 (more precision) despite having less precision. The reason: f4.4 spreads outputs across a wider byte range, giving the search more "signal" to lock onto.

**Practical guideline:** when configuring a superoptimizer search, prefer output representations that spread values across the full register width. The search cost difference between good and bad representations can be 10× or more.

---

## O.10 Multi-Target Search

The nonlinear search tests each candidate against **15 target functions simultaneously**. Generation cost (enumerating sequences) is shared; verification cost (comparing outputs) is trivial by comparison. Adding more targets is essentially free.

This enables exploration: discovering that a particular 11-instruction sequence happens to compute a good log2 approximation, even though the search was targeting sqrt. The "unexpected match" rate is low (~1 in 10^6), but at depth-11 scale, every hit is valuable.

---

## O.11 Abstract Chains vs. Real Instructions

Optimal Z80 sequences are compared against ISA-independent abstract representations ({dbl, add, sub, save} chains). The overhead ratio averages **0.99×** --- the Z80 code is actually *shorter* than the abstract model.

This is counterintuitive: a concrete ISA should be more verbose than an abstract model. But the Z80 has tricks the abstract model cannot express: `NEG` replaces two abstract ops (×255 = single NEG, 8T). `SBC A,A` has no abstract equivalent. The ISA's historical quirks are not overhead --- they are *computational assets* that thorough search exploits.

---

## O.12 Conclusion

Ten patterns, one recurring theme: **structure emerges from exhaustion.**

None of these observations were predicted in advance. The 21-instruction thesis is a theorem about the Z80 ISA that no human designer knew in 1976. The prefix sharing structure is a topological property of shift-add program space with no prior formalization. The carry-to-mask trick was a design accident that turned out to be the most important instruction in branchless arithmetic.

755 optimal sequences. 21 surviving instructions. One 50-year-old processor that turns out to be a remarkably clean laboratory for studying the nature of computation itself.

---

*Data: z80-optimizer exhaustive tables (mul8, mul16, div8, sqrt/log2 approximations), 2025--2026. All results verified by full-state equivalence checking. Repository: [github.com/oisee/z80-optimizer](https://github.com/oisee/z80-optimizer)*
