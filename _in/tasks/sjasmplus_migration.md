# Task: sjasmplus Migration — Upgrade + Dual-Assembler Workflow

**Status:** Ready for pickup
**Prereqs:** None (standalone task)
**Estimated scope:** ~2-3 hours
**Context:** See `CLAUDE.md` at repo root for project overview

## Background

We currently have **sjasmplus v1.07 RC8** (2008) installed at `~/dev/bin/sjasmplus`. It's ancient and has compatibility issues. The current release is **v1.20+** on GitHub with full Z80 instruction support, `DEVICE`/`SAVESNA`, local labels, macros, etc.

Our primary assembler is **mza** (developed at `../minz-ts/`). All 11 `.a80` examples compile with mza. However, mza has known instruction limitations (see below), so having sjasmplus as a secondary assembler lets us:
- Validate our code compiles on a standard assembler
- Use full IX/IY indexed addressing (mza workarounds not needed)
- Generate reference binaries for comparison
- Eventually use `ifdef` blocks showing natural vs workaround code

### mza Instruction Limitations (for reference)

These Z80 instructions do NOT work in mza — sjasmplus handles them all:
- `ld (ix+d), imm` — must use `ld a, imm` then `ld (ix+d), a`
- `ld r, (ix+d)` where r != a — must use `ld a, (ix+d)` then `ld r, a`
- `inc/dec (ix+d)` — must load to A, inc/dec, store back
- `add a, (ix+d)` — must load to register, add separately
- `>> 8` in expressions — not supported
- Negative DB values — must use unsigned two's complement (e.g., 252 not -4)

## Step 1: Install Fresh sjasmplus

```bash
# Clone current release
cd ~/dev
git clone https://github.com/z00m128/sjasmplus.git sjasmplus-build
cd sjasmplus-build

# Build from source
cmake . && make

# Replace old binary
cp sjasmplus ~/dev/bin/sjasmplus

# Verify
~/dev/bin/sjasmplus --version
# Should show v1.20+ (not 1.07)
```

**Acceptance:** `~/dev/bin/sjasmplus --version` shows v1.20 or newer.

## Step 2: Create sjasmplus Compatibility Wrapper

Each `.a80` file needs `DEVICE ZXSPECTRUM128` and `SAVESNA` directives for sjasmplus to produce SNA output. Our files don't have these (they use mza's `--target` flag instead).

### Recommended approach: wrapper `.sjasm` files

For each `.a80`, the Makefile generates a temporary wrapper:

```z80
; auto-generated wrapper for sjasmplus
    DEVICE ZXSPECTRUM128
    INCLUDE "original_file.a80"
    SAVESNA "output.sna", entry
```

This keeps `.a80` files clean — no `ifdef` clutter.

### Alternative: Makefile target with sed/echo

The `make test-sjasmplus` target could dynamically prepend `DEVICE ZXSPECTRUM128` and append `SAVESNA` without creating files, using sjasmplus `--stdin` or temp files.

### Decision needed

Pick whichever approach is simplest. The wrapper file approach is cleanest but creates temp files. Either way, the `.a80` source files should NOT be modified.

## Step 3: Update Makefile

Current Makefile already has `ASM` variable and sjasmplus rules. Extend it:

```makefile
SJASMPLUS := $(HOME)/dev/bin/sjasmplus

# Test with sjasmplus — generates wrapper, compiles, reports
test-sjasmplus:
	@ok=0; fail=0; \
	for f in chapters/ch*/examples/*.a80; do \
		[ -f "$$f" ] || continue; \
		base=$$(basename $$f .a80); \
		wrapper=$$(mktemp /tmp/sjasm_XXXX.asm); \
		echo "  DEVICE ZXSPECTRUM128" > $$wrapper; \
		echo "  INCLUDE \"$$f\"" >> $$wrapper; \
		echo "  SAVESNA \"/tmp/$$base.sna\", entry" >> $$wrapper; \
		if $(SJASMPLUS) --nologo $$wrapper 2>/dev/null; then \
			echo "  OK  $$f"; ok=$$((ok+1)); \
		else \
			echo "FAIL  $$f"; fail=$$((fail+1)); \
		fi; \
		rm -f $$wrapper; \
	done; \
	echo "---"; echo "$$ok passed, $$fail failed"

# Test with both assemblers, compare
test-both:
	@echo "=== mza ===" && $(MAKE) test
	@echo ""
	@echo "=== sjasmplus ===" && $(MAKE) test-sjasmplus
```

**Note:** The `entry` label in SAVESNA assumes all examples define an `entry:` label. Check this — some may use `main:` or `start:` or just ORG address. The wrapper may need per-file entry point detection from the symbols.

## Step 4: Validate All 11 .a80 Examples

Compile each with sjasmplus and report pass/fail:

| File | Chapter | Notes |
|------|---------|-------|
| `timing_harness.a80` | ch01 | Simplest, should work |
| `fill_screen.a80` | ch02 | Basic screen fill |
| `pixel_demo.a80` | ch02 | Pixel plotting |
| `push_fill.a80` | ch03 | Stack-based screen fill |
| `multiply8.a80` | ch04 | 8-bit multiply |
| `wireframe_cube.a80` | ch05 | 3D wireframe |
| `plasma.a80` | ch09 | Plasma effect |
| `ay_test.a80` | ch11 | AY sound chip |
| `sprite_demo.a80` | ch16 | Sprite rendering |
| `game_skeleton.a80` | ch18 | Entity system (had 40+ IX workarounds) |
| `aabb_test.a80` | ch19 | Collision detection |

For each:
1. Compile with sjasmplus → note any syntax errors
2. Fix incompatibilities (if any — likely minor: label syntax, expression syntax)
3. Compare machine code output between mza and sjasmplus (strip SNA/BIN headers, diff raw bytes)

**Expected issues:**
- mza uses `$FF` for hex — sjasmplus also supports this, should be fine
- mza uses `.label` for local labels — sjasmplus uses `.label` too (v1.20+)
- Entry point labels may vary per file
- Some mza-specific directives may not exist in sjasmplus

## Step 5: Enable IX/IY in Examples (Optional, Lower Priority)

Now that sjasmplus handles full IX/IY, we can optionally add `ifdef` blocks showing natural code alongside mza workarounds:

```z80
; Natural IX/IY (sjasmplus only)
    IFDEF SJASMPLUS
        ld (ix+ENTITY_X), 100
        inc (ix+ENTITY_STATE)
    ELSE
; mza workaround
        ld a, 100
        ld (ix+ENTITY_X), a
        ld a, (ix+ENTITY_STATE)
        inc a
        ld (ix+ENTITY_STATE), a
    ENDIF
```

**Priority target:** `ch18-gameloop/examples/game_skeleton.a80` — it had 40+ IX workarounds during development.

This is optional and lower priority than steps 1-4.

## Step 6: Document Dual-Assembler Workflow

Update `CLAUDE.md` to add:

```markdown
## Dual-Assembler Workflow

- `make test` — compile all with mza (primary)
- `make test-sjasmplus` — compile all with sjasmplus (secondary)
- `make test-both` — compare both assemblers

sjasmplus (v1.20+) at `~/dev/bin/sjasmplus` handles full Z80 instruction set
including IX/IY indexed addressing that mza doesn't support.
```

## Verification Checklist

- [ ] `~/dev/bin/sjasmplus --version` shows v1.20+
- [ ] `make test` still works (mza, no regressions)
- [ ] `make test-sjasmplus` compiles all 11 examples (or documents which fail and why)
- [ ] `make test-both` runs and produces comparison output
- [ ] CLAUDE.md updated with sjasmplus commands
- [ ] No `.a80` source files were broken by changes
