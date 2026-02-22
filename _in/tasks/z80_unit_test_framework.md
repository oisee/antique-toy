# Task: Z80 Unit Test Framework via DZRP Protocol

**Status:** Ready for pickup
**Prereqs:** mza assembler working (`make test` passes), mze or ZXSpeculator available
**Estimated scope:** Phase 1-2: ~4-6 hours; Phase 3-4: ~3-4 hours
**Context:** See `CLAUDE.md` at repo root for project overview

## Background

We need automated testing for Z80 assembly code examples in the book. Manual testing (load in emulator, visually inspect) doesn't scale to 11+ examples across 23 chapters.

### Available Infrastructure

**mza** (our assembler at `../minz-ts/`):
- Produces SNA/TAP/BIN output
- `--symbols file.sym` → label map (name = $addr)
- `--listing file.lst` → source→machine code mapping
- Built-in emulator **mze** with DZRP protocol support
- Remote loader **mzrun** for loading SNAs into emulator

**ZXSpeculator** (oisee fork):
- Cycle-accurate ZX48K emulator
- DZRP protocol support on TCP port 11000
- Breakpoints: address, memory write, IO port, conditional
- Rollback/snapshot support
- Register and memory inspection

**DZRP** (DeZog Remote Protocol):
- TCP socket protocol (default port 11000)
- Shared by both mze and ZXSpeculator
- Commands for: load, run, step, breakpoints, register/memory read
- Originally designed for DeZog VS Code extension

**Existing code:**
- `verify/zx_screen.js` — ZX Spectrum screen memory renderer (use for screen capture)

## Architecture

```
┌─────────────────────────────────────────────┐
│  Test Runner (Node.js)                      │
│  - Reads test specs (.z80test.json)         │
│  - Compiles .a80 → .sna via mza            │
│  - Loads symbols from --symbols output      │
│  - Connects to DZRP emulator               │
│  - Sets breakpoints, runs, asserts          │
│  - Reports pass/fail (TAP format)           │
└──────────────┬──────────────────────────────┘
               │ DZRP (TCP :11000)
               ▼
┌─────────────────────────────────────────────┐
│  Emulator (mze or ZXSpeculator)             │
│  - Loads SNA snapshot                       │
│  - Cycle-accurate Z80 execution             │
│  - Breakpoints: addr, memory, IO, T-state   │
│  - Register/memory/AY inspection            │
│  - Frame-accurate rendering                 │
└─────────────────────────────────────────────┘
```

## Test Spec Format

Tests are defined in `.z80test.json` files alongside the `.a80` source:

```json
{
  "name": "plasma quarter-screen calculation",
  "source": "chapters/ch09-tunnels/examples/plasma.a80",
  "target": "zxspectrum",
  "tests": [
    {
      "name": "calc_plasma fills 192 bytes",
      "setup": {
        "registers": { "A": 0 },
        "memory": { "phase1": 0, "phase2": 0, "phase3": 0 }
      },
      "run": {
        "call": "calc_plasma",
        "max_tstates": 50000
      },
      "assert": {
        "memory_range": {
          "start": "attr_quarter",
          "length": 192,
          "not_all_zero": true
        },
        "tstates_less_than": 45000
      }
    },
    {
      "name": "main_loop runs one frame",
      "run": {
        "start": "entry",
        "stop_at": "main_loop",
        "stop_after_n_hits": 2
      },
      "assert": {
        "memory_range": {
          "start": "$5800",
          "length": 768,
          "not_all_equal": true
        }
      }
    }
  ]
}
```

### Fields

**Top level:**
- `name` — human-readable test suite name
- `source` — path to .a80 file (relative to repo root)
- `target` — assembler target (`zxspectrum`)

**Per test:**
- `name` — test case name
- `setup.registers` — register values to set before running (optional)
- `setup.memory` — memory locations to initialize, keys are label names or `$hex` addresses
- `run.call` — label to call (sets PC to label address, breakpoint at RET)
- `run.start` / `run.stop_at` — run from start label, stop at stop_at label
- `run.stop_after_n_hits` — stop after Nth hit of the breakpoint (default 1)
- `run.max_tstates` — abort if execution exceeds this T-state count
- `assert` — assertions to check after execution stops (see below)

## Assert Types

| Assert | Format | Description |
|--------|--------|-------------|
| `register_equals` | `{ "A": 42, "HL": "$5800", "F.Z": 1 }` | Check register values. `F.Z`, `F.C` etc for individual flags |
| `memory_equals` | `{ "addr": "$5800", "bytes": [71, 71, 71] }` | Exact byte match at address |
| `memory_range` | `{ "start": "label", "length": 192, "not_all_zero": true }` | Check memory range properties |
| `tstates_less_than` | `50000` | Execution took fewer than N T-states |
| `tstates_between` | `[40000, 50000]` | Execution T-states in range |
| `screen_matches` | `"expected_screen.scr"` | Screen memory matches reference .scr file |
| `screen_checksum` | `"$A3B4C5D6"` | CRC32 of screen memory $4000-$5AFF |
| `port_written` | `{ "port": "$BFFD", "value": 42 }` | Verify IO port was written (ZXSpeculator only) |

## Trap/Breakpoint Types

| Trap Type | mze | ZXSpeculator | Description |
|-----------|-----|-------------|-------------|
| Address breakpoint | Yes | Yes | Stop at PC = address |
| Memory write watch | Yes | Yes | Stop when memory at addr is written |
| IO port watch | No | Yes | Stop on OUT to specific port |
| T-state limit | Custom | Custom | Runner counts via step mode or emulator API |
| N-th interrupt | Custom | Custom | Count HALT instructions or IM2 triggers |
| Register value | Custom | Custom | After stop, check register values |
| Memory contents | Yes | Yes | Read memory range via DZRP |

## Implementation Phases

### Phase 1: DZRP Client Library

**File:** `verify/z80test/dzrp_client.js`

Node.js module that implements the DZRP protocol over TCP:

```javascript
class DZRPClient {
  constructor(host = 'localhost', port = 11000)

  // Connection
  async connect()
  async disconnect()

  // Control
  async init()                              // DZRP CMD_INIT
  async loadSna(path)                       // Load SNA snapshot
  async run()                               // Continue execution
  async pause()                             // Pause execution
  async step()                              // Single step (T-state accurate)
  async stepOver()                          // Step over CALL
  async reset()                             // Reset CPU

  // Breakpoints
  async setBreakpoint(address)              // Address breakpoint
  async setMemoryBreakpoint(address, size)  // Memory write watch
  async removeBreakpoint(id)                // Remove breakpoint
  async removeAllBreakpoints()              // Clear all

  // Inspection
  async getRegisters()                      // All registers + flags
  async readMemory(address, length)         // Read memory range
  async writeMemory(address, bytes)         // Write memory
  async setRegister(name, value)            // Set single register

  // Symbols
  loadSymbols(symFilePath)                  // Parse mza --symbols output
  resolveLabel(name)                        // Label → address
}
```

**DZRP protocol reference:** The protocol is binary over TCP. Each message has:
- Length (4 bytes, little-endian)
- Sequence number (1 byte)
- Command ID (1 byte)
- Payload (variable)

Key command IDs to implement:
- `CMD_INIT` (1) — initialize connection
- `CMD_CLOSE` (2) — close connection
- `CMD_GET_REGISTERS` (3) — read all registers
- `CMD_SET_REGISTER` (4) — set single register
- `CMD_WRITE_MEMORY` (5) — write to memory
- `CMD_READ_MEMORY` (6) — read from memory
- `CMD_CONTINUE` (7) — resume execution
- `CMD_PAUSE` (8) — pause execution
- `CMD_ADD_BREAKPOINT` (9) — set breakpoint
- `CMD_REMOVE_BREAKPOINT` (10) — remove breakpoint
- `CMD_STEP_INTO` (11) — single step

**Symbol parsing:** mza `--symbols` output format:
```
label_name = $XXXX
```
Parse into a `Map<string, number>`.

**Testing Phase 1:**
1. Start mze with a test SNA: `mze --dzrp test.sna`
2. Connect with DZRPClient
3. Read registers, verify sensible values
4. Set breakpoint, run, verify it hits
5. Read memory range, verify screen area

### Phase 2: Test Runner

**File:** `verify/z80test/runner.js`

```javascript
// Usage: node verify/z80test/runner.js [spec.z80test.json ...]
// If no args, finds all .z80test.json in chapters/
```

Workflow per test suite:
1. Read `.z80test.json` spec
2. Compile source with mza: `mza --target zxspectrum --symbols build/X.sym -o build/X.sna source.a80`
3. Load symbols from `.sym` file
4. Start emulator (or connect to running one)
5. Load SNA into emulator via DZRP
6. For each test case:
   a. Reset CPU state
   b. Apply `setup` (set registers, write memory)
   c. Set breakpoints per `run` config
   d. Run until breakpoint hit or T-state limit
   e. Read registers/memory
   f. Evaluate all `assert` conditions
   g. Report pass/fail
7. Output TAP-compatible results

**TAP output example:**
```
TAP version 13
1..3
ok 1 - calc_plasma fills 192 bytes
ok 2 - main_loop runs one frame
not ok 3 - timing under budget
  ---
  message: "tstates_less_than: expected < 45000, got 47231"
  ...
```

**Error handling:**
- Compilation failure → skip suite, report error
- Emulator connection failure → abort with clear message
- T-state limit exceeded → fail test with timeout message
- Symbol not found → fail test with "unknown label: X"

### Phase 3: Screen Capture & Visual Regression

**File:** `verify/z80test/screen_capture.js`

Uses existing `verify/zx_screen.js` to render screen memory to PNG:

1. Read screen memory ($4000-$5AFF, 6912 bytes) via DZRP
2. Pass to ZXScreen renderer → PNG buffer
3. Compare against reference screenshot:
   - Exact match: byte-compare the .scr data
   - Fuzzy match: render both to PNG, pixel-diff with tolerance
   - Checksum: CRC32 of .scr data

**Reference screenshots** stored alongside test specs:
```
chapters/ch02-screen-as-puzzle/examples/pixel_demo.expected.scr
chapters/ch02-screen-as-puzzle/examples/pixel_demo.expected.png
```

**Update mode:** `--update-references` flag regenerates reference files from current output.

### Phase 4: T-state Profiler

**File:** `verify/z80test/profiler.js`

Measures T-states between two breakpoints for performance validation:

```javascript
// Usage: node verify/z80test/profiler.js source.a80 start_label end_label
```

1. Set breakpoint at start label
2. Run until hit
3. Record T-state counter
4. Set breakpoint at end label
5. Continue until hit
6. Calculate delta

**Output:**
```
Profile: calc_plasma
  Start: calc_plasma ($8100)
  End:   calc_plasma_done ($8200)
  T-states: 43,217
  Frames: 0.62 (at 69,888 T/frame)
  Budget: 45,000 — OK (96% used)
```

**Use cases:**
- Validate documented cycle counts in chapter prose match actual
- Profile hot routines: rotation, projection, line drawing, plasma
- Regression detection: code change → T-state increase

## File Structure

```
verify/z80test/
  dzrp_client.js          # DZRP protocol client (Phase 1)
  runner.js               # Test runner (Phase 2)
  screen_capture.js       # Screen capture + visual regression (Phase 3)
  profiler.js             # T-state profiler (Phase 4)
  README.md               # Usage docs
```

## Example Test Specs to Create First

### 1. ch01 timing_harness (simplest — register assertion)

```json
{
  "name": "timing harness basic test",
  "source": "chapters/ch01-thinking-in-cycles/examples/timing_harness.a80",
  "target": "zxspectrum",
  "tests": [
    {
      "name": "border changes color",
      "run": {
        "start": "entry",
        "max_tstates": 100000
      },
      "assert": {
        "port_written": { "port": "$FE", "value_not": 0 }
      }
    }
  ]
}
```

### 2. ch09 plasma (memory range assertion)

```json
{
  "name": "plasma effect",
  "source": "chapters/ch09-tunnels/examples/plasma.a80",
  "target": "zxspectrum",
  "tests": [
    {
      "name": "attributes written after one frame",
      "run": {
        "start": "entry",
        "stop_at": "main_loop",
        "stop_after_n_hits": 2
      },
      "assert": {
        "memory_range": {
          "start": "$5800",
          "length": 768,
          "not_all_equal": true
        }
      }
    }
  ]
}
```

### 3. ch02 pixel_demo (visual regression)

```json
{
  "name": "pixel demo visual",
  "source": "chapters/ch02-screen-as-puzzle/examples/pixel_demo.a80",
  "target": "zxspectrum",
  "tests": [
    {
      "name": "screen matches reference after drawing",
      "run": {
        "start": "entry",
        "stop_at": "done",
        "max_tstates": 500000
      },
      "assert": {
        "screen_checksum": "$A3B4C5D6",
        "memory_range": {
          "start": "$4000",
          "length": 6144,
          "not_all_zero": true
        }
      }
    }
  ]
}
```

## Two Execution Modes

### Offline (batch) — for CI/make test

```bash
# Start emulator in background (headless)
mze --dzrp --headless &

# Run all tests
node verify/z80test/runner.js chapters/**/examples/*.z80test.json

# Kill emulator
kill %1
```

### Interactive (visual) — for development

```bash
# Start emulator with display
mze --dzrp test.sna

# In another terminal, run specific test
node verify/z80test/runner.js chapters/ch09-tunnels/examples/plasma.z80test.json --interactive

# Interactive mode pauses between tests so you can see the screen
```

## Makefile Integration

```makefile
# Run Z80 unit tests (requires emulator running with DZRP)
test-z80:
	@node verify/z80test/runner.js $$(find chapters -name '*.z80test.json')

# Profile specific routine
profile:
	@node verify/z80test/profiler.js $(SRC) $(START) $(END)
```

## Verification Checklist

- [ ] Phase 1: DZRPClient connects to mze, reads registers, reads memory
- [ ] Phase 1: Symbol parser loads mza `--symbols` output correctly
- [ ] Phase 2: Runner compiles .a80, loads SNA, runs test, reports pass/fail
- [ ] Phase 2: TAP output format correct
- [ ] Phase 2: ch01 timing_harness test passes
- [ ] Phase 3: Screen capture reads $4000-$5AFF, renders PNG via zx_screen.js
- [ ] Phase 3: ch02 pixel_demo visual regression works
- [ ] Phase 4: Profiler measures T-states between two breakpoints
- [ ] Phase 4: ch09 plasma T-state measurement matches expected budget

## Dependencies

- Node.js (already used for verify/ scripts)
- mza assembler (at `../minz-ts/`)
- mze emulator (built into mza: `mza --emulate` or `mze`)
- Optional: ZXSpeculator for IO port breakpoints and cycle-accurate mode

## DZRP Protocol Notes

The DZRP protocol documentation is sparse. Best references:
- DeZog source code (VS Code extension): defines the protocol
- mze source in `../minz-ts/` — our implementation
- ZXSpeculator source — oisee's implementation

If protocol details are unclear, inspect the mze DZRP implementation in `../minz-ts/` source code for exact message formats and command IDs.
