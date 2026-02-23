# Sub-project: spectools — ZX Spectrum Development Toolkit

Companion tools for "Coding the Impossible" book.
Separate repo or `tools/` monorepo. To be developed by Claude agents.

---

## Vision

A collection of modern, zero-dependency CLI tools + a modular ZX Spectrum emulator core.
Everything a demoscene developer needs that doesn't already exist in good quality.

**Three pillars:**
1. **CLI utilities** — Python, standalone, useful day-one
2. **Analytical emulator** — Rust/TypeScript, cycle-accurate, embeddable
3. **Web tools** — JS/HTML interactive prototypers and visualizers

---

## Pillar 1: CLI Utilities (Python 3.10+, zero deps except Pillow for image tools)

### 1.1 autodiver.py — Attribute Grid Optimizer

Reimplementation of oisee/autodiver_go in Python.

**Input:** PNG/BMP image (any size)
**Output:** Top-N best variants saved to `./best/`, rating CSV

**Algorithm:**
- For each combination of (shift_x 0..7, shift_y 0..7, scale 0..max):
  - Resize image to 256+(scale) width, crop to 256x192 at (shift_x, shift_y)
  - For each 8x8 cell: count unique colours, penalty = pixels beyond top-2 colours
  - Total penalty = sum of all 768 cells
- Sort by penalty ascending, output best N variants

**Flags:**
- `-s N` — max scale addition (default 0 = offset only)
- `-ss N` — scale step (default 1)
- `-m` — use significance mask (mask_*.png)
- `-p N` — extra penalty for masked pixels (default 1)
- `-b DIR` — output directory (default ./best)
- `-n N` — save top N results (default 8)
- `--palette zx|zx15` — quantize to ZX palette before evaluation

**Future:** per-cell shifting (moroz1999's idea from 2015 demoscene.ru thread)

### 1.2 tstate.py — T-State Annotator

**Input:** .a80 assembly file
**Output:** Annotated file with T-state costs per instruction and per block

**Features:**
- Parse Z80 mnemonics, look up T-state cost from table
- For conditional instructions: show both taken/not-taken costs
- Sum T-states per block (label to label)
- Warn if block exceeds frame budget (69888 T for 48K)
- Output: annotated .a80 to stdout or side-by-side HTML

**T-state database:** all documented + undocumented Z80 instructions, including:
- IX/IY prefix costs (+4T for DD/FD prefix)
- Contended memory penalties (optional, per-model)

### 1.3 notetable.py — AY Note Table Generator

**Input:** tuning system, base frequency, AY clock
**Output:** Assembly DW table (96 notes, 8 octaves)

**Tuning systems:**
- `--12tet` — equal temperament (standard)
- `--just` — just intonation / natural tuning (Table #5, Ivan Roshin)
- `--pythagorean` — Pythagorean tuning
- `--custom FILE` — custom ratio file

**Flags:**
- `--clock N` — AY clock in Hz (default 1773400 for ZX128)
- `--base-freq N` — A4 frequency (default 440)
- `--format asm|c|json` — output format
- `--check-envelope` — report which periods are divisible by 16

### 1.4 sinetable.py — Sine Table Generator

**Input:** approach number (1-7), table size, amplitude
**Output:** Assembly DB table + accuracy report

**Approaches (from Appendix B):**
1. Full 256-byte LUT (precomputed)
2. Quarter-wave symmetry (64 bytes)
3. Second-order delta encoding
4. Parabolic approximation
5. Bhaskara I approximation
6. Recursive difference equation
7. CORDIC-style iterative

**Flags:**
- `--approach N` — which approach (default 1)
- `--size N` — table size (default 256)
- `--amplitude N` — max value (default 127)
- `--format asm|c|json`
- `--compare` — compare all approaches, output error table

### 1.5 scrview.py — ZX Spectrum Screen Viewer

**Input:** .scr file (6912 bytes) or .tap/.sna snapshot
**Output:** ANSI terminal rendering or HTML file

**Features:**
- Decode pixel data (3 thirds, interleaved rows)
- Apply attributes (ink, paper, bright, flash)
- ANSI mode: use 256-colour terminal with half-block characters
- HTML mode: generate pixel-perfect HTML with CSS grid
- `--grid` — overlay 8x8 attribute grid
- `--clash` — highlight cells with 3+ colours (red border)
- `--attr-only` — show only attribute colours (no pixels)

### 1.6 z80dasm.py — Interactive Z80 Disassembler

A clean, embeddable Z80 disassembler in Python.

**Features:**
- Disassemble raw binary or .sna/.z80/.tap snapshots
- Recursive descent (follow jumps/calls) + linear sweep
- Detect code vs data regions
- Label generation (auto-label targets of jumps/calls)
- Undocumented opcodes (IX/IY half-registers, SLL, etc.)
- Output: annotated assembly or structured JSON
- ROM symbol database (Spectrum 48K ROM labels)

**Flags:**
- `--org N` — origin address (default $8000)
- `--entry N` — entry point(s) for recursive descent
- `--format asm|json|html`
- `--rom-labels` — use Spectrum ROM symbol names
- `--smc-detect` — flag self-modifying code patterns (writes to code addresses)

**Architecture:** clean separation: decoder → instruction IR → formatter.
The decoder module should be reusable in the emulator (Pillar 2).

---

## Pillar 2: Analytical Emulator — "spectre"

A modular, cycle-accurate ZX Spectrum emulator designed for embedding in analytical tools.

### Architecture

```
┌─────────────────────────────────────┐
│         Host Application            │
│  (CLI / Web / IDE plugin / tests)   │
├─────────────────────────────────────┤
│         spectre API                 │
│  create_machine(profile) → Machine  │
│  machine.step() / .run_frame()      │
│  machine.inspect() / .trace()       │
├───────────┬─────────────────────────┤
│  Z80 Core │  Bus / Memory / IO      │
│  (decode + │  (configurable per     │
│   execute)│   machine profile)      │
├───────────┼─────────────────────────┤
│           │  Timing Engine          │
│           │  (T-state maps per      │
│           │   instruction, per      │
│           │   machine model)        │
├───────────┼─────────────────────────┤
│           │  Contention Model       │
│           │  (per-model memory      │
│           │   contention tables)    │
└───────────┴─────────────────────────┘
```

### Machine Profiles (JSON/TOML config)

Each profile defines:
- CPU clock speed
- Memory map (pages, banks, ROM layout)
- Contention pattern (which T-states of each instruction hit contended memory)
- I/O port map
- AY clock frequency
- Frame timing (T-states per line, lines per frame, INT position)
- Border timing

**Profiles:**
- ZX Spectrum 48K (standard ULA timing)
- ZX Spectrum 128K / +2 / +3
- Pentagon 128/512/1024 (no contention!)
- Scorpion 256
- ZX Spectrum Next (Z80N extended instructions)
- Agon Light 2 (eZ80 — separate core? or just Z80 subset)

### Analytical Features (the killer differentiator)

**Execution trace:**
- Log every PC value → code coverage map
- Log every memory read/write → classify addresses as code/data/variable/constant/SMC
- Log every port I/O → peripheral interaction map
- Log conditional branch outcomes → branch profiling

**T-state profiling:**
- Per-address cumulative T-state count (hot-spot map)
- Per-frame T-state budget tracking
- Contention cost breakdown (how many T lost to contention per frame)

**SMC detection:**
- Track writes to addresses later executed as code
- Flag SMC patterns: `ld (addr), a` where `addr` is in code region

**Memory classification (from your 2015 demoscene.ru idea!):**
- Address never accessed → unknown
- Address only executed → code
- Address only read → constant / ROM
- Address written then executed → self-modifying code
- Address written and read → variable
- Block moved by LDIR/LDDR → relocated code/data

**Call graph:**
- Track CALL/RET pairs → build call graph
- Detect stack manipulation (RST, PUSH/RET tricks, JP (HL))
- Export as DOT/Mermaid/JSON

### Language Choice

**Option A: TypeScript/JavaScript**
+ Runs in browser (web tools!) and Node.js (CLI)
+ Easy integration with verify/ prototypers
+ NPM distribution
- Slower than native (but V8 JIT is fast enough for ZX speed)

**Option B: Rust**
+ Maximum performance
+ WASM compilation for browser
+ Memory safety
- Higher development effort
- Harder for community to contribute

**Option C: Python**
+ Consistent with other tools
+ Easiest to prototype
- Too slow for real-time emulation (but OK for analytical runs)

**Recommendation:** TypeScript for the core (runs everywhere, fast enough, embeddable in web tools). Python wrapper via subprocess/IPC for integration with CLI tools.

### MVP Scope

Phase 1: Z80 CPU core + memory bus + basic 48K profile
Phase 2: Execution trace + code coverage map
Phase 3: 128K support + contention model
Phase 4: T-state profiling + SMC detection
Phase 5: AY emulation + full analytical suite
Phase 6: Pentagon/Scorpion/Next profiles

---

## Pillar 3: Web Tools (HTML/JS, static, no server needed)

Extend the existing `verify/` directory into a full interactive toolkit.

### 3.1 Attribute Clash Visualizer
- Drop a PNG → see attribute grid overlay, clash count per cell
- Drag to shift image, see penalty change in real-time
- Basically autodiver with a GUI

### 3.2 Screen Memory Explorer
- Interactive visualization of ZX Spectrum screen memory layout
- Click pixel → see address calculation, attribute lookup
- Animate the interleaved row order

### 3.3 Effect Prototyper Collection
- All book effects as interactive JS demos with parameter sliders:
  - Plasma, tunnel, rotozoomer, sphere, dotfield, multicolor
  - Adjustable: palette, speed, sine parameters, resolution

### 3.4 T-State Calculator
- Paste Z80 assembly → get T-state annotation
- Highlight contended instructions for selected machine model
- Block-level summary with frame budget bar

### 3.5 Z80 Instruction Explorer
- Interactive reference: click instruction → see encoding, T-states, flags
- Filter by category, search by mnemonic
- Side-by-side: Z80 vs eZ80 differences

---

## Repo Structure

```
spectools/
├── README.md
├── LICENSE                    # MIT
├── pyproject.toml             # Python package config
├── cli/                       # Python CLI tools
│   ├── autodiver.py
│   ├── tstate.py
│   ├── notetable.py
│   ├── sinetable.py
│   ├── scrview.py
│   └── z80dasm.py
├── spectre/                   # Emulator core (TypeScript)
│   ├── package.json
│   ├── src/
│   │   ├── z80/              # CPU core
│   │   │   ├── decoder.ts
│   │   │   ├── executor.ts
│   │   │   └── registers.ts
│   │   ├── bus/              # Memory + I/O bus
│   │   │   ├── memory.ts
│   │   │   └── io.ts
│   │   ├── timing/           # T-state engine
│   │   │   ├── tstate-map.ts
│   │   │   └── contention.ts
│   │   ├── machines/         # Machine profiles
│   │   │   ├── spectrum48k.json
│   │   │   ├── spectrum128k.json
│   │   │   ├── pentagon128.json
│   │   │   └── scorpion256.json
│   │   ├── analysis/         # Analytical features
│   │   │   ├── tracer.ts
│   │   │   ├── profiler.ts
│   │   │   ├── smc-detect.ts
│   │   │   └── call-graph.ts
│   │   └── index.ts
│   └── tests/
├── web/                       # Interactive web tools
│   ├── attr-clash/
│   ├── screen-explorer/
│   ├── effect-prototyper/
│   ├── tstate-calc/
│   └── z80-explorer/
├── data/                      # Shared data files
│   ├── z80-opcodes.json      # Full instruction set with T-states
│   ├── spectrum48k-rom.bin   # (gitignored, downloaded)
│   └── contention-tables/
└── docs/
    └── architecture.md
```

---

## Development Plan

### Sprint 1 — CLI Tools (can start immediately)
- [ ] autodiver.py
- [ ] tstate.py
- [ ] notetable.py
- [ ] sinetable.py
- [ ] scrview.py

### Sprint 2 — Disassembler + Data
- [ ] z80dasm.py
- [ ] z80-opcodes.json (complete instruction database)
- [ ] Spectrum ROM symbol database

### Sprint 3 — Emulator Core MVP
- [ ] Z80 decoder (all opcodes including undocumented)
- [ ] Z80 executor (cycle-accurate)
- [ ] Memory bus (48K layout)
- [ ] Basic execution trace
- [ ] Pass ZEXALL tests

### Sprint 4 — Analytical Features
- [ ] Code coverage map
- [ ] T-state profiler
- [ ] SMC detection
- [ ] Memory classification
- [ ] Call graph builder

### Sprint 5 — Machine Profiles
- [ ] 128K bank switching
- [ ] Contention model (48K, 128K)
- [ ] Pentagon profile (no contention)
- [ ] AY-3-8910 register-level emulation

### Sprint 6 — Web Tools
- [ ] Attribute clash visualizer
- [ ] Screen memory explorer
- [ ] T-state calculator web UI
- [ ] Effect prototyper collection

---

## References

- oisee/autodiver_go — attribute optimizer (Go). github.com/oisee/autodiver_go
- oisee/autosiril — MIDI-to-PT3 converter. github.com/oisee/autosiril
- oisee/vti — Vortex Tracker Improved. github.com/oisee/vti
- demoscene.ru articles by oisee (2015): AutoDiver v1.0, v2.0, Z80 code analysis
- Ivan Roshin — "Частотная таблица с нулевой погрешностью" (2001)
- Einar Saukas — ZX0/ZX1/ZX2 compressors
- maziac/DeZog — VS Code Z80 debugger
- SkoolKit — ZX Spectrum disassembly toolkit
- Spectrum Analyser — interactive RE tool (colourclash.co.uk)
