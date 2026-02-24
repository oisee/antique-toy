# Appendix D: Development Environment Setup

> *"You need five things: an editor, an assembler, an emulator, a debugger, and a Makefile. Everything else is optional."*
> -- Chapter 1

This appendix walks you through setting up a complete Z80 development environment from scratch. By the end, you will be able to compile every assembly example in this book, run them in an emulator, and debug them with breakpoints and register inspection. The instructions cover macOS, Linux, and Windows.

If you have already followed the setup in Chapter 1, you have most of this in place. This appendix adds detail, covers alternative configurations, and serves as a single reference you can return to when setting up a new machine.

---

## 1. The Assembler: sjasmplus

Every code example in this book is written for **sjasmplus**, an open-source Z80/Z80N macro assembler by z00m128. It supports the full Z80 instruction set including all IX/IY indexed modes, macros, Lua scripting, multiple output formats, and expressions that make demoscene code practical to write.

### Installing from Source

The most reliable way to get sjasmplus is to build it from source. This guarantees you have a known version and avoids platform-specific packaging issues.

```bash
git clone https://github.com/z00m128/sjasmplus.git
cd sjasmplus
make
```

On macOS, you need Xcode command-line tools (`xcode-select --install`). On Linux, you need `g++` and `make` (install via your package manager). On Windows, use MinGW or WSL.

After building, copy the `sjasmplus` binary to somewhere in your PATH:

```bash
# macOS / Linux
sudo cp sjasmplus /usr/local/bin/

# Verify
sjasmplus --version
```

You should see version 1.20.x or later. This book was developed and tested with v1.21.1.

### Version Pinning

The book's repository pins sjasmplus as a git submodule in `tools/sjasmplus/`. If you clone the repository with `--recursive`, you get the exact version used to compile every example:

```bash
git clone --recursive https://github.com/[repo]/antique-toy.git
cd antique-toy/tools/sjasmplus
make
```

This is the safest approach. Assembler behaviour can change between versions -- an expression that works in 1.21 might parse differently in 1.22.

### Key Flags

| Flag | Purpose | Example |
|------|---------|---------|
| `--nologo` | Suppress the startup banner | `sjasmplus --nologo main.a80` |
| `--raw=FILE` | Output a raw binary (no header) | `sjasmplus --raw=output.bin main.a80` |
| `--sym=FILE` | Write a symbol file (for debuggers) | `sjasmplus --sym=output.sym main.a80` |
| `--fullpath` | Show full file paths in error messages | Useful with VS Code problem matcher |
| `--msg=war` | Suppress info messages, show only warnings and errors | Cleaner build output |

A typical build command for a chapter example:

```bash
sjasmplus --nologo --raw=build/example.bin chapters/ch01-thinking-in-cycles/examples/timing.a80
```

### File Extension

All Z80 assembly source files in this book use the `.a80` extension. This is a convention, not a requirement -- sjasmplus does not care about extensions. We use `.a80` because it is recognised by the Z80 Macro Assembler VS Code extension and distinguishes our source from other assembly dialects.

### Hex Notation

The book uses `$FF` for hexadecimal values. sjasmplus also accepts `#FF` and `0FFh`, but `$FF` is the convention throughout. The standalone `$` symbol represents the current program counter address, used in constructs like `jr $` (infinite loop) or `dw $ + 4`.

---

## 2. The Editor: VS Code

Any text editor works. We recommend **Visual Studio Code** because of its Z80-specific extensions and integrated terminal. The entire workflow -- edit, build, debug -- happens in one window.

### Essential Extensions

Install these from the VS Code Extensions marketplace (Ctrl+Shift+X):

| Extension | Author | What It Does |
|-----------|--------|-------------|
| **Z80 Macro Assembler** | mborik (`mborik.z80-macroasm`) | Syntax highlighting, code completion, symbol resolution for Z80 assembly. Understands sjasmplus syntax including macros and local labels. |
| **Z80 Assembly Meter** | Nestor Sancho | Displays byte count and T-state cost of selected instructions in the status bar. Select a block, see its total cost instantly. Indispensable for cycle counting. |
| **DeZog** | Maziac | Z80 debugger. Connects to emulators or its internal simulator. Breakpoints, register watches, memory inspection. See Section 4. |

### Build Task

Set up a build task so Ctrl+Shift+B compiles your current file. Create `.vscode/tasks.json` in your project root:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Assemble Z80",
      "type": "shell",
      "command": "sjasmplus",
      "args": [
        "--fullpath",
        "--nologo",
        "--msg=war",
        "${file}"
      ],
      "group": {
        "kind": "build",
        "isDefault": true
      },
      "problemMatcher": {
        "owner": "z80",
        "fileLocation": "absolute",
        "pattern": {
          "regexp": "^(.*)\\((\\d+)\\):\\s+(error|warning):\\s+(.*)$",
          "file": 1,
          "line": 2,
          "severity": 3,
          "message": 4
        }
      }
    }
  ]
}
```

The `problemMatcher` parses sjasmplus error output so that clicking an error in the terminal jumps to the offending line. The `--fullpath` flag ensures file paths are absolute, which VS Code needs to resolve them correctly.

### Recommended Settings

Add these to your workspace `.vscode/settings.json` for a clean Z80 editing experience:

```json
{
  "editor.tabSize": 8,
  "editor.insertSpaces": false,
  "editor.rulers": [80],
  "files.associations": {
    "*.a80": "z80-macroasm"
  }
}
```

Tab size 8 with real tabs matches the traditional assembly convention where mnemonics and operands align at fixed columns.

---

## 3. Emulators

You need an emulator to run your assembled code. Different emulators serve different purposes.

### ZEsarUX -- Feature-Rich Debugging

**ZEsarUX** by cerebellio is the most feature-rich open-source ZX Spectrum emulator. It supports the full range of Spectrum models (48K, 128K, +2, +3, Pentagon, Scorpion, ZX-Uno, ZX Spectrum Next), has a built-in debugger, and integrates with DeZog for VS Code debugging.

**Install:**

- macOS: `brew install zesarux`
- Linux: Build from source or use the AppImage from https://github.com/chernandezba/zesarux
- Windows: Download the installer from the ZEsarUX website

**Why ZEsarUX for this book:** Most chapter examples target the ZX Spectrum 128K. ZEsarUX emulates 128K memory banking, AY sound, TurboSound (two AY chips), and the contention patterns of different models. Its built-in debugger shows registers, memory, and disassembly without needing VS Code. And its DeZog integration provides the full VS Code debugging experience when you need it.

**Quick launch:**

```bash
# Run a .sna snapshot
zesarux --machine 128k --nosplash output.sna

# Run a .tap file
zesarux --machine 128k --nosplash output.tap
```

### Fuse -- Lightweight and Accurate

**Fuse** (the Free Unix Spectrum Emulator) by Philip Kendall is lightweight, cycle-accurate, and available on every platform. It is the best choice for quick testing when you do not need the full debugger.

**Install:**

- macOS: `brew install fuse-emulator`
- Linux: `apt install fuse-emulator-sdl` (Debian/Ubuntu) or `dnf install fuse-emulator` (Fedora)
- Windows: Download from the Fuse website

**Quick launch:**

```bash
# Run with Pentagon timing (matches the book's T-state counts)
fuse --machine pentagon output.sna

# Run as 128K Spectrum
fuse --machine 128 output.tap
```

Fuse is particularly good for testing timing-sensitive code because its cycle accuracy is well-verified. If your border stripe timing harness (Chapter 1) shows different results in Fuse versus another emulator, trust Fuse.

### Unreal Speccy -- Windows, Pentagon-Focused

If you develop primarily on Windows and target Pentagon timing, **Unreal Speccy** is a strong choice. It has a built-in debugger with memory map, breakpoints, and AY register monitoring. It emulates Pentagon and Scorpion hardware accurately.

Download from http://dlcorp.nedopc.com/viewforum.php?f=27 or search for "Unreal Speccy Portable."

### For Agon Light 2

The Agon Light 2 uses an eZ80 CPU and a different hardware architecture. Chapter 22 covers Agon development in detail. For emulation, **Fab Agon Emulator** provides a software simulation of the Agon hardware (eZ80 + ESP32 VDP). It is available at https://github.com/tomm/fab-agon-emulator and runs on macOS, Linux, and Windows.

### Which Emulator Should I Use?

| Situation | Recommended Emulator |
|-----------|---------------------|
| Day-to-day development, running examples | Fuse (fast startup, accurate) |
| Debugging with breakpoints and register watches | ZEsarUX + DeZog |
| AY/TurboSound music development | ZEsarUX (best AY emulation) |
| Pentagon timing verification | Fuse or Unreal Speccy |
| Agon Light 2 development | Fab Agon Emulator |
| Quick sanity check on Windows | Unreal Speccy |

---

## 4. The Debugger: DeZog

**DeZog** by Maziac is a VS Code extension that turns your editor into a Z80 debugger. It connects to ZEsarUX, CSpect, or its own internal Z80 simulator and provides the debugging experience modern developers expect: breakpoints, stepping, register watches, memory inspection, disassembly view, and call stack.

Chapter 23 discusses DeZog in the context of AI-assisted development. This section covers the practical setup.

### Installation

1. Open VS Code.
2. Go to Extensions (Ctrl+Shift+X).
3. Search for "DeZog" by Maziac.
4. Click Install.

### Connecting to ZEsarUX

DeZog communicates with ZEsarUX over a socket connection. First, launch ZEsarUX with its ZRCP (ZEsarUX Remote Control Protocol) server enabled:

```bash
zesarux --machine 128k --enable-remoteprotocol --remoteprotocol-port 10000
```

Then create a `.vscode/launch.json` in your project:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "type": "dezog",
      "request": "launch",
      "name": "DeZog + ZEsarUX",
      "remoteType": "zesarux",
      "zesarux": {
        "port": 10000
      },
      "sjasmplus": [
        {
          "path": "build/output.sld"
        }
      ],
      "topOfStack": "$FF00",
      "commandsAfterLaunch": [
        "-sprites disable",
        "-patterns disable"
      ]
    }
  ]
}
```

The `sjasmplus` section points to the `.sld` (Source Level Debug) file that sjasmplus generates with the `--sld=FILE` flag. This gives DeZog source-level debugging -- breakpoints on source lines, not just addresses.

To generate the `.sld` file, add the flag to your build command:

```bash
sjasmplus --nologo --raw=build/output.bin --sld=build/output.sld --sym=build/output.sym main.a80
```

### Using the Internal Simulator

For quick debugging without launching an external emulator, DeZog includes a built-in Z80 simulator. Change your `launch.json` to:

```json
{
  "type": "dezog",
  "request": "launch",
  "name": "DeZog Internal Simulator",
  "remoteType": "zsim",
  "zsim": {
    "machine": "spectrum",
    "memoryModel": "ZX128K"
  },
  "sjasmplus": [
    {
      "path": "build/output.sld"
    }
  ],
  "topOfStack": "$FF00"
}
```

The internal simulator is faster to start and does not require ZEsarUX to be installed. It lacks accurate contention emulation, so do not use it for timing-critical debugging -- but for logic debugging (does my multiply routine produce the right result?), it is perfect.

### Key DeZog Features

**Breakpoints.** Click the gutter next to a source line to set a breakpoint. Execution pauses when the Z80 program counter reaches that address. You can also set conditional breakpoints (e.g., break when `A == $FF`).

**Register watches.** The Variables panel shows all Z80 registers: AF, BC, DE, HL, IX, IY, SP, PC, and the alternate set (AF', BC', DE', HL'). Individual flags (C, Z, S, P/V, H, N) are broken out for easy reading.

**Memory inspection.** The Memory panel shows a hex dump of any address range. You can type an address and see what is there. Essential for verifying lookup tables, screen memory contents, and stack state.

**Disassembly view.** Even without source-level debugging, DeZog disassembles the code around the current PC. Useful for understanding what self-modifying code actually looks like at runtime.

**Call stack.** DeZog tracks CALL/RET pairs and shows a call stack. This works for conventional code. Self-modifying code and RET-chaining (Chapter 3) will confuse the stack tracker -- this is expected.

---

## 5. Building the Book's Examples

### Clone the Repository

```bash
git clone --recursive https://github.com/[repo]/antique-toy.git
cd antique-toy
```

The `--recursive` flag pulls the sjasmplus submodule in `tools/sjasmplus/`. If you already cloned without it:

```bash
git submodule update --init --recursive
```

### Prerequisites

You need `make` and a C++ compiler (for building sjasmplus from the submodule). On most systems these are already present:

- macOS: `xcode-select --install`
- Debian/Ubuntu: `sudo apt install build-essential`
- Fedora: `sudo dnf install make gcc-c++`
- Windows: Use WSL, or install MinGW and GNU Make

### Build Commands

The project Makefile handles everything. All compiled output goes to `build/`, which is gitignored.

| Command | What It Does |
|---------|-------------|
| `make` | Compile all chapter examples with sjasmplus |
| `make test` | Assemble all examples, report pass/fail for each |
| `make ch01` | Compile only Chapter 1 examples |
| `make ch04` | Compile only Chapter 4 examples |
| `make demo` | Build the "Antique Toy" companion demo |
| `make clean` | Remove all build artifacts |

A successful `make test` run looks like this:

```
  OK  chapters/ch01-thinking-in-cycles/examples/timing.a80
  OK  chapters/ch04-maths/examples/multiply.a80
  OK  chapters/ch05-wireframe-3d/examples/cube.a80
  ...
---
12 passed, 0 failed
```

If any example fails, the output shows `FAIL` with the filename. Run the failing file manually with sjasmplus to see the detailed error:

```bash
sjasmplus --nologo chapters/ch04-maths/examples/multiply.a80
```

### Running an Example

After compiling, load the output binary into your emulator. The exact method depends on the output format:

```bash
# If the example produces a .sna snapshot
fuse --machine pentagon build/ch01-thinking-in-cycles/examples/timing.sna

# If you built a raw binary, you need to create a .tap or .sna first,
# or load it at the correct address in the emulator's debugger
```

Most chapter examples use ORG `$8000` and produce raw binaries. To run them, either:

1. Use a `.tap` wrapper (the Makefile generates these when the source includes the appropriate directives), or
2. Load the binary at address `$8000` in your emulator's debugger and set PC to `$8000`.

---

## 6. Project Structure for Your Own Code

When you start writing your own Z80 code beyond the book's examples, here is a recommended directory layout:

```
my-demo/
  src/
    main.a80          -- entry point, includes other files
    effects/
      plasma.a80      -- individual effect routines
      scroller.a80
    data/
      font.a80        -- DB/DW data tables
      sintable.a80
    lib/
      multiply.a80    -- reusable utility routines
      draw_line.a80
  assets/
    title.scr         -- raw screen files
    music.pt3         -- tracker music
  build/              -- compiled output (gitignored)
  Makefile
  .vscode/
    tasks.json        -- build task
    launch.json       -- DeZog configuration
```

### Minimal Makefile

```makefile
SJASMPLUS ?= sjasmplus
BUILD_DIR := build
SJASM_FLAGS := --nologo

.PHONY: all clean run

all: $(BUILD_DIR)/demo.bin

$(BUILD_DIR)/demo.bin: src/main.a80 src/effects/*.a80 src/data/*.a80 src/lib/*.a80
	@mkdir -p $(BUILD_DIR)
	$(SJASMPLUS) $(SJASM_FLAGS) --raw=$@ --sym=$(BUILD_DIR)/demo.sym --sld=$(BUILD_DIR)/demo.sld $<

run: $(BUILD_DIR)/demo.bin
	fuse --machine 128 $(BUILD_DIR)/demo.sna

clean:
	rm -rf $(BUILD_DIR)
```

Key points:

- The main source file uses `INCLUDE` directives to pull in other files. sjasmplus resolves includes relative to the source file's directory.
- The `--sym` flag generates a symbol file for reference. The `--sld` flag generates source-level debug data for DeZog.
- List all included source files as dependencies so `make` rebuilds when any file changes.

### Include Convention

In your `main.a80`:

```z80
    ORG $8000

    ; --- Entry point ---
start:
    di
    ; set up stack, interrupts, etc.
    ld   sp, $FF00
    ; ...

    include "lib/multiply.a80"
    include "effects/plasma.a80"
    include "data/sintable.a80"
```

sjasmplus processes `INCLUDE` files inline, as if the text were pasted at that point. Keep your includes organised: library routines first, then effects, then data (since data is typically placed at the end of the binary).

---

## 7. Alternative Tools

This book uses sjasmplus because it is the most capable Z80 assembler for demoscene and game development work. But you may encounter other tools in the community.

### Other Assemblers

| Assembler | Notes |
|-----------|-------|
| **z80asm** | Part of the z88dk C cross-compiler suite. Good if you mix C and assembly. Different syntax conventions. |
| **RASM** | By Roudoudou. Fast, supports CPC and Spectrum. Popular in the Amstrad CPC scene. |
| **pasmo** | Simple, portable, limited features. Suitable for small standalone programs but lacks macros and advanced features needed for larger projects. |

The book's examples use sjasmplus-specific features (local labels with `.`, negative DB values, `$` hex prefix) that may not work unmodified in other assemblers. If you want to port an example to a different assembler, the changes are usually minor: label syntax, hex notation, and directive names.

### Other VS Code Extensions

| Extension | Notes |
|-----------|-------|
| **SjASMPlus Syntax** | Alternative syntax highlighting tuned specifically for sjasmplus. Try it if `z80-macroasm` does not highlight a sjasmplus-specific feature correctly. |
| **Z80 Debugger** (Spectron) | An older VS Code Z80 debugger. DeZog has largely superseded it. |

### CSpect -- Next-Focused Emulator

If you have a ZX Spectrum Next or are targeting Next-specific features (copper, layer 2, DMA, 28MHz turbo mode), **CSpect** by Mike Dailly is the reference emulator. DeZog connects to CSpect the same way it connects to ZEsarUX. CSpect is Windows-only but runs under Wine on macOS and Linux.

### SpectrumAnalyzer

A browser-based tool that visualises ZX Spectrum screen memory layout, attribute conflicts, and timing. Useful for understanding Chapter 2's discussion of the screen interleave. Available at https://shiru.untergrund.net/spectrumanalyzer.html (or search for "ZX Spectrum screen analyzer").

---

## 8. Troubleshooting

### "sjasmplus: command not found"

The binary is not in your PATH. Either copy it to `/usr/local/bin/` (macOS/Linux), add its directory to your PATH, or set the `SJASMPLUS` variable when running make:

```bash
make SJASMPLUS=/path/to/sjasmplus
```

### Compilation errors in the book's examples

First, make sure you are using the sjasmplus version from the submodule (`tools/sjasmplus/`). Newer or older versions may have different behaviour. Second, check that you are assembling the file from the correct directory -- sjasmplus resolves `INCLUDE` paths relative to the source file, not the working directory.

### DeZog cannot connect to ZEsarUX

1. Make sure ZEsarUX is running with `--enable-remoteprotocol`.
2. Check that the port number in `launch.json` matches the `--remoteprotocol-port` argument.
3. On macOS, you may need to allow ZEsarUX through the firewall (System Settings > Privacy & Security).
4. Try restarting ZEsarUX before launching the DeZog session.

### Emulator shows garbled screen

If you load a raw binary and see garbage, the most likely cause is a wrong load address. The book's examples use ORG `$8000`. Make sure your emulator loads the binary at that address, not at `$0000` or some other default. Using `.sna` or `.tap` output (which includes address information) avoids this problem.

### Build output is empty or zero bytes

Check that your source file has an `ORG` directive and at least one instruction. sjasmplus with `--raw=` produces a binary from the first byte emitted to the last. If nothing is emitted (e.g., the file contains only `ORG $8000` with no code), the output is empty.

---

## Tool Reference

| Tool | Purpose | Official URL | Book Reference |
|------|---------|-------------|----------------|
| **sjasmplus** | Z80/Z80N macro assembler | https://github.com/z00m128/sjasmplus | Chapter 1, all examples |
| **VS Code** | Editor and IDE | https://code.visualstudio.com | Chapter 1 |
| **Z80 Macro Assembler** | VS Code syntax extension | Marketplace: `mborik.z80-macroasm` | Chapter 1 |
| **Z80 Assembly Meter** | Cycle count display | Marketplace: Nestor Sancho | Chapter 1 |
| **DeZog** | VS Code Z80 debugger | Marketplace: Maziac / https://github.com/maziac/DeZog | Chapter 23 |
| **ZEsarUX** | Feature-rich Spectrum emulator | https://github.com/chernandezba/zesarux | Chapter 1, Chapter 23 |
| **Fuse** | Lightweight Spectrum emulator | https://fuse-emulator.sourceforge.net | Chapter 1 |
| **Unreal Speccy** | Pentagon-focused emulator | http://dlcorp.nedopc.com | Chapter 1 |
| **CSpect** | ZX Spectrum Next emulator | https://dailly.blogspot.com | Chapter 22 (Next features) |
| **Fab Agon Emulator** | Agon Light 2 emulator | https://github.com/tomm/fab-agon-emulator | Chapter 22 |
| **ZX0** | Optimal LZ compressor | https://github.com/einar-saukas/ZX0 | Chapter 14, Appendix C |
| **Exomizer** | Best-ratio compressor | https://github.com/bitmanipulators/exomizer | Chapter 14, Appendix C |
| **Vortex Tracker II** | AY music tracker | https://github.com/ivanpirog/vortextracker | Chapter 11 |

---

## See Also

- **Chapter 1:** First practical -- setting up VS Code, sjasmplus, and the timing harness.
- **Chapter 22:** Agon Light 2 platform setup, eZ80 toolchain, Fab Agon Emulator.
- **Chapter 23:** DeZog integration with AI-assisted workflows.
- **Appendix A:** Z80 instruction reference -- the instructions you will be debugging.
- **Appendix G:** AY register reference -- useful when debugging sound code in ZEsarUX.
