# Appendix P: Register Allocation as a Solved Game

> *83.6 million shapes. 37.6 million enriched. O(1) lookup replaces NP-complete search.*

---

## P.1 The Problem: 7 Registers, Infinite Demand

The Z80 has 7 general-purpose 8-bit registers: A, B, C, D, E, H, L. Every program needs more variables than that. The compiler must decide: which variable lives in which register, and when.

This decision is **register allocation** --- the single most impactful optimization a compiler makes. A good allocation eliminates 30--50% of move instructions. A bad one turns fast code into a shuffle of `LD` instructions.

### Why Z80 is Hard

Most modern CPUs have 16--32 general registers. x86-64 has 16. ARM has 31. Z80 has 7 --- and they're **not interchangeable**:

- **A** is the only accumulator. All ALU operations (ADD, SUB, AND, OR, XOR, CP) use A as one operand and destination. Cost: 4T.
- **H:L** is the only pair for indirect memory access `(HL)` and 16-bit ADD.
- **B** is the only register for `DJNZ` (loop countdown).
- **D:E** often holds pointers for `LDIR`/`LDDR` block operations.

If your variable needs an ADD but lives in register C, you pay 12T instead of 4T:

```z80
; Variable in A (natural):     ; Variable in C (expensive):
ADD A, B        ; 4T           LD A, C         ; 4T (move to A)
                               ADD A, B        ; 4T (the actual ADD)
                               LD C, A         ; 4T (move result back)
                               ; Total: 12T — 3× slower!
```

---

## P.2 Graph Coloring: The Classical Approach

Register allocation reduces to **graph coloring** --- a problem studied since 1852 (the four-color theorem for maps).

Two variables **interfere** if they're alive at the same time. If x and y are both needed for the same instruction, they can't share a register. Each node = variable, each edge = interference, coloring = assigning registers such that no edge connects two same-colored nodes.

**The catch:** graph coloring with k colors is NP-complete for general graphs (Karp, 1972). For k=7 (Z80), worst case is exponential. But real programs aren't worst case --- most interference graphs from real programs have low **treewidth** (Chaitin, 1981).

---

## P.3 What We Built: Exhaustive Tables

Instead of solving graph coloring at compile time, we **pre-computed every answer**.

For each variable count (2--6), we enumerate all possible interference graph shapes, try all 7^N register assignments, check feasibility, and score cost. The result: a lookup table.

| Variables | Shapes | Feasible | Time |
|-----------|--------|----------|------|
| ≤4 | 156,506 | 123,453 (78.9%) | 40 seconds |
| ≤5 | 17,366,874 | 11,762,983 (67.7%) | 20 minutes |
| 6 (dense) | 66,118,738 | 25,772,093 (38.9%) | ~6 hours |
| **Total** | **83,642,118** | **37,658,529** | |

### The Feasibility Cliff

As variables increase, feasibility drops dramatically --- a **phase transition** like water freezing:

```
Variables:  2     3     4     5     6     7     8
Feasible: 95.9%  89.2%  78.9%  67.7%  38.9%  ~5%   ~0.1%
```

Below 6 variables, almost everything fits. Above 7, almost nothing does. The cliff happens exactly where it matters: Z80 has 7 registers, and real functions have 3--8 live variables.

---

## P.4 The GPU Breakthrough

Checking 83.6M shapes sequentially takes days. On GPU, it takes hours.

Each GPU thread independently evaluates one shape: decode into interference graph, try all 7^N assignments, check constraints, keep minimum-cost feasible assignment.

**Performance:** 17.4M shapes × 7^5 = 2.9 trillion constraint checks. Two RTX 4060 Ti complete this in 20 minutes.

For shapes with 7+ variables (7^7 = 823K assignments per shape), a CPU backtracking solver prunes the search tree. Pruning factor: **1000--4000×** compared to brute force. A shape with 10 variables: 7^10 = 282 billion checks brute force vs ~70 million with pruning (4000× fewer).

---

## P.5 Enrichment: From "Feasible" to "Optimal for Your Code"

The original tables answer: "Can these variables fit in registers?" The enriched tables answer: "What's the **cheapest** way to fit them, given my operations?"

### The Register Cost Graph

Z80 registers are not equal. A is the hub (all ALU goes through it). H:L is the 16-bit accumulator for `ADD HL,rr`. IX halves are accessible but expensive (DD prefix = +4T). Moving between non-adjacent registers costs:

| Move | Cost | Notes |
|------|------|-------|
| A ↔ any r | 4T | Direct `LD` |
| B ↔ C, D ↔ E, H ↔ L | 4T | Within pair |
| H ↔ IXH | 16T | Via `EX DE,HL; LD IXH,D; EX DE,HL` |
| A ↔ IXH | 8T | Direct `LD IXH,A` (DD prefix) |

### Hidden Infeasibility

The original tables said 37.6M assignments are "feasible." But:

| Constraint | Shapes affected | Meaning |
|-----------|-----------------|---------|
| **No A** | 43% | u8 ALU impossible without extra moves (+8T per op) |
| **No HL** | 21% | u16 ADD impossible naturally (+13T per op) |
| **mul8 conflict** | 93% | multiply clobbers live variables |
| **B occupied** | 13% | DJNZ loop counter needs save/restore |

**Only 9% of assignments are "ideal"** --- have A, HL, are mul8-safe, and B-free.

The compiler that picks a random feasible assignment pays up to **60% overhead** compared to the optimal one.

---

## P.6 The O(1) Lookup Architecture

Every function has a computable **signature**: `(interference_graph_shape, operation_bag)`.

The operation bag is order-independent --- ADD A,B costs 4T whether it's the first or last instruction. The order of liveness is already captured in the interference graph.

### Five-Level Pipeline

1. **Cut vertex decomposition**: split functions with 7+ variables at graph cut points into ≤6-variable subproblems --- always lossless
2. **Enriched table lookup** (91%): O(1) result from pre-computed table --- assignment + cost + flags
3. **EXX shadow bank**: functions that exceed 7 registers get a second register file via `EXX` (4T context switch)
4. **GPU partition optimizer**: for 7--14 variable functions, find the optimal split into ≤6-variable subgraphs on GPU
5. **Z3 SAT solver** (fallback): provably optimal, <10 seconds

**91% of functions** resolve in O(1) --- a hash table lookup. The remaining 9% fall through to increasingly powerful solvers. No function is unsolvable --- decomposition always finds a way.

### VIR Corpus Validation

Analysis of 820 real functions from the VIR compiler corpus confirms the table's coverage:

- **Move instructions = 34%** of all operations --- the single largest category, and the primary target for register allocation optimization
- **Multiply = 0%** --- no function in the corpus uses hardware multiply (confirming that mul8 conflict, while theoretically affecting 93% of shapes, rarely matters in practice)
- **Average live variables: 3.8** --- well within the ≤6 sweet spot of the enriched tables

---

## P.7 How Other Compilers Do It

|  | SDCC | GCC/LLVM | Z3 (MinZ) | **Ours** |
|--|------|----------|-----------|----------|
| Quality | Heuristic | Good | Optimal | **Optimal** |
| Speed | Fast | Fast | 36s/645fn | **O(1)** |
| Offline cost | None | None | None | **10 min GPU** |
| Table size | None | None | None | **78MB** |

**SDCC** uses a greedy allocator with heuristic spilling. Result: correct but often suboptimal. Our comparison (SDCC 4.5.0 vs optimal):

| Function | SDCC | Optimal | Overhead |
|----------|------|---------|----------|
| abs\_diff | 7 instr | 4 instr | +75% |
| mul3 | 4 instr | 3 instr | +33% |
| div10 | CALL library | 3 instr inline | --- |
| gray\_encode | 4 instr | 3 instr | +33% |

**GCC/LLVM** use graph coloring with coalescing (Chaitin-Briggs). Good for 16+ registers but struggles with Z80's 7 --- spill costs dominate.

**MinZ** uses Z3 SMT solver for exact optimal allocation. Optimal but slow: 645 functions in 36 seconds (sequential).

We trade 78MB of pre-computed data for O(1) optimal allocation at compile time.

---

## P.8 Width-Aware Feasibility

Variable width dramatically changes register pressure:

- **u8:** 7 registers + IXH/IXL/IYH/IYL = 11 possible slots
- **u16:** only BC, DE, HL, IX/IY = 3--5 pairs
- **u32:** requires shadow banks via EXX --- HL:H'L', DE:D'E', BC:B'C'

**u8 ADD:** 11 possible source registers → hundreds of valid assignments.
**u16 ADD:** only HL as accumulator → 2--3 valid assignments.
**4+ u16 variables → INFEASIBLE** without IX/IY (only 3 register pairs).

The enriched tables include width-aware scoring: `u16_pair_count`, `u16_add_natural` (11T via HL+rr) vs `u16_add_via_u8` (24T decomposed), and `u16_slots_free`.

---

## P.9 The CALL Save Problem

Function calls destroy registers. The caller must save live variables before CALL and restore after. This is often the most expensive part of register allocation.

### Save Strategies (cheapest first)

| Channel | Method | Cost |
|---------|--------|------|
| 1. Free register | `LD r',r` | 8T |
| 2. EX AF,AF' | (A+F only) | 8T |
| 3. IX/IY halves | `LD IXH,r` | 16T |
| 4. PUSH/POP | Stack | 21T per pair |
| 5. Self-modify | `LD (imm),A` | 20T |

**Smart save strategy = 17T average** (50% less than naive PUSH/POP at 34T). On 500 functions × 2 CALLs = **17,000 T-states saved**.

---

## P.10 Wave Function Collapse: The Next Frontier

WFC (Wave Function Collapse) is a constraint propagation technique from procedural generation. Each instruction position starts with all possible instructions (~394 ops), then constraints eliminate impossibilities.

Constraint: input in B → position 0 collapses to `{LD A,B}`. Constraint: preserve DE → eliminates all DE-clobbering instructions. After propagation, the search space is reduced 90--99% before brute force begins.

**GPU-friendly:** reindexing (regenerate thread-to-candidate mapping) instead of runtime pruning (which causes warp divergence).

---

## P.11 Real-World Data: What Z80 Code Actually Looks Like

Instruction frequencies across real Z80 programs:

| Category | The Hobbit (1982) | ZX Demos | antique-toy book | Average |
|----------|------------------|----------|-----------------|---------|
| **LD/MOV** | 27% | 37% | 41% | **35%** |
| **ALU** | 19% | 25% | 20% | **22%** |
| **Branch** | 27% | 19% | 24% | **22%** |
| **Stack** | 8% | 10% | 4% | **7%** |
| **IX/IY** | 11% | 3% | 9% | **6%** |
| **Exchange** | 1% | 2% | 0.3% | **1%** |

**LD/MOV = 35% of all instructions** --- the overhead that register allocation directly eliminates. A perfect allocator removes most of these moves, saving ~30% of total execution time.

**IX/IY usage: 6--11%** in real code --- higher than expected. Used for structure field access, cross-bank bridging (not swapped by EXX), and cheap save slots (`LD IXH,r` = 8T, no stack).

---

## P.12 What This Enables

For the **MinZ compiler**: O(1) register allocation for 90% of functions, early infeasibility detection, width-aware constraints, idiom compatibility (which mul8/div8 sequences work without save/restore), and pre-computed CALL save costs.

For **research**: 37.6M data points on register allocation feasibility, empirical measurement of the phase transition at 6--7 variables, and a new approach combining graph coloring with instruction selection.

For **retro computing**: the same tables that optimize a compiler also explain *why* hand-written Z80 code looks the way it does. The Hobbit's 11% IX/IY usage isn't arbitrary --- it's the natural response to register pressure in functions with 5+ live variables.

---

*83.6M shapes enumerated, 37.6M enriched with 15 operation-aware metrics. Tables available at [github.com/oisee/z80-optimizer](https://github.com/oisee/z80-optimizer).*
