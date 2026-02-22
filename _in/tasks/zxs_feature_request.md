# Feature Request: zxs (ZXSpeculator CLI) for antique-toy Book Project

**From:** antique-toy ("Coding the Impossible" book repo)
**To:** ZXSpeculator developer
**Date:** 2026-02-22

---

## Context

We're building a Z80 assembly book with 12 compilable examples (.a80 files) + a torus demo. We need `zxs` as the emulator backbone for three workflows:

1. **Automated testing** — compile with sjasmplus/mza, load into zxs, assert register/memory state
2. **VS Code development** — edit .a80, build, run in zxs, debug via DeZog
3. **CI binary validation** — headless execution, screen capture, T-state profiling

All communication via **DZRP (DeZog Remote Protocol)** over TCP.

---

## 1. Command-Line Loading

```bash
# Load and run a snapshot
zxs game.sna

# Load a tape file
zxs demo.tap

# Load raw binary at specific address
zxs --load-bin program.bin --addr 0x8000 --exec 0x8000

# Load .scr (screen data) for visual inspection
zxs --load-scr loading_screen.scr
```

**Why:** Our `make` targets produce .sna (via mza) and raw .bin (via sjasmplus). We need to load both. The `--addr` / `--exec` flags let us load a raw binary at ORG address and set PC, without needing to wrap it in a snapshot.

---

## 2. DZRP Server

```bash
# Start with DZRP enabled (default port 11000)
zxs --dzrp

# Custom port
zxs --dzrp --dzrp-port 11001

# DZRP + load a file
zxs --dzrp game.sna

# Start paused (wait for DZRP client to connect and send commands)
zxs --dzrp --paused
```

### Required DZRP Commands

| Command | ID | Priority | Use Case |
|---------|-----|----------|----------|
| CMD_INIT | 1 | Must | Handshake |
| CMD_CLOSE | 2 | Must | Disconnect |
| CMD_GET_REGISTERS | 3 | Must | Read all Z80 registers (AF, BC, DE, HL, IX, IY, SP, PC, AF', BC', DE', HL', I, R, IM) |
| CMD_SET_REGISTER | 4 | Must | Set single register value |
| CMD_WRITE_MEMORY | 5 | Must | Write bytes to memory |
| CMD_READ_MEMORY | 6 | Must | Read memory range |
| CMD_CONTINUE | 7 | Must | Resume execution |
| CMD_PAUSE | 8 | Must | Pause execution |
| CMD_ADD_BREAKPOINT | 9 | Must | Set breakpoint (address, memory-write, IO-port types) |
| CMD_REMOVE_BREAKPOINT | 10 | Must | Remove breakpoint |
| CMD_STEP_INTO | 11 | Must | Single-step one instruction |
| CMD_STEP_OVER | 12 | Nice | Step over CALL |
| CMD_GET_TBBLUE_REG | 13 | No | Not needed (we target 48K/128K, not Next) |
| CMD_LOAD_SNA | custom? | Nice | Load .sna via DZRP without filesystem access |

**Why:** DeZog VS Code extension speaks DZRP. Our test runner (Node.js) will also speak DZRP directly. Both need the core command set.

---

## 3. Headless Mode (for CI and Automated Tests)

```bash
# Run headless (no window), exit after N frames
zxs --headless --frames 100 game.sna

# Headless with DZRP (test runner connects, drives execution, disconnects)
zxs --headless --dzrp game.sna

# Headless, run until HALT, then exit
zxs --headless --stop-at-halt game.sna
```

**Why:** GitHub Actions CI needs to run `make test-z80` which starts zxs headless, loads each example, runs assertions via DZRP, then kills the emulator. No display available.

---

## 4. Screen Capture / Dump

```bash
# Dump screen memory ($4000-$5AFF) to .scr file
zxs --headless --frames 50 --dump-scr output.scr game.sna

# Dump screen as PNG (rendered with attributes)
zxs --headless --frames 50 --dump-png output.png game.sna
```

**Via DZRP:** Reading $4000-$5AFF (6912 bytes) via CMD_READ_MEMORY works, but a built-in `--dump-scr` is more convenient for quick validation and avoids needing a DZRP client just for screenshots.

**Why:** Visual regression tests — we compare screen output against reference .scr files. Also useful for generating book screenshots.

---

## 5. T-State Counter

We need to measure how many T-states elapsed between two points. Two approaches:

### Option A: DZRP Extension — Read T-State Counter

```
CMD_GET_TSTATES (custom) → returns uint64 cumulative T-state count
```

Test runner sets breakpoint at `start_label`, runs, reads counter. Sets breakpoint at `end_label`, continues, reads counter. Delta = cost.

### Option B: Command-Line Profiler

```bash
# Run from addr A to addr B, report T-states
zxs --headless --profile 0x8100:0x8200 game.sna
# Output: "Profile: 43217 T-states (0.60 frames at 71680 T/frame)"
```

**Why:** Every chapter in the book quotes T-state costs. We need to validate those numbers automatically. This is the single most important feature for the book project after basic DZRP.

---

## 6. Breakpoint Types

| Type | Description | Priority |
|------|-------------|----------|
| Address (PC) | Stop when PC reaches address | Must |
| Memory write | Stop when byte at address is written | Must |
| IO port write | Stop when OUT to specific port | Nice (for AY register tests) |
| IO port read | Stop when IN from specific port | Low |
| T-state limit | Stop after N T-states of execution | Nice (timeout for runaway tests) |
| Conditional | Stop at address only if register condition met | Low |

---

## 7. Machine Model

For the book we primarily need:

- **ZX Spectrum 48K** — default, 69,888 T/frame, contended memory
- **Pentagon 128** — 71,680 T/frame, no contention (nice to have, this is the demoscene standard)

Being able to switch between them would be ideal:

```bash
zxs --model 48k game.sna
zxs --model pentagon game.sna
```

If only one model is supported, 48K is fine — our code runs on both and we can account for the timing difference.

---

## 8. Exit Codes

For CI integration, `zxs` should return meaningful exit codes:

| Code | Meaning |
|------|---------|
| 0 | Clean exit (normal termination or `--frames` limit reached) |
| 1 | Error (file not found, invalid format, etc.) |
| 2 | Timeout (T-state limit exceeded without hitting breakpoint) |

---

## Priority Summary

**Must have (blocking for test framework):**
- Load .sna from command line
- DZRP server (commands 1-11)
- Headless mode
- Read/write memory and registers via DZRP

**Should have (blocking for full workflow):**
- Load raw .bin at address
- T-state counter (DZRP or CLI)
- Screen dump to .scr
- `--paused` start mode
- Breakpoints: address + memory-write

**Nice to have:**
- IO port breakpoints
- PNG screen dump
- Pentagon model
- Step-over
- Conditional breakpoints
- Exit codes

---

## Integration Plan

Once the above is available, our Makefile gets:

```makefile
# Start emulator in background for test suite
test-z80:
	@zxs --headless --dzrp --paused &
	@sleep 1
	@node verify/z80test/runner.js chapters/**/examples/*.z80test.json
	@kill %1

# Quick visual check of a single example
run:
	@mza --target zxspectrum -o build/$(SRC:.a80=.sna) $(SRC)
	@zxs build/$(SRC:.a80=.sna)
```

And VS Code gets a launch.json entry that starts zxs with DZRP, then DeZog connects to it for step-through debugging.

---

## Current Toolchain

```
Editor:      VS Code + Z80 Macro Assembler + Z80 Assembly Meter
Assemblers:  sjasmplus (primary), mza (secondary)
Emulator:    zxs (ZXSpeculator CLI)  ← this request
Debugger:    DeZog (VS Code) → DZRP → zxs
Test runner: Node.js → DZRP → zxs
CI:          GitHub Actions → make test-z80
```
