# Coding the Impossible — Book Examples Build System
# Primary assembler: sjasmplus (full Z80 instruction set, $FF and #FF hex)
# Secondary: mza (MinZ Assembler, used for mze emulation + DZRP)
#
# Usage:
#   make                    # build all chapter examples
#   make test               # assemble all with sjasmplus, report errors
#   make test-mza           # assemble all with mza
#   make ch01               # build chapter 1 examples
#   make demo               # build the torus demo
#   make clean              # remove build artifacts

SJASMPLUS ?= sjasmplus
MZA_PATH  := $(HOME)/dev/minz-ts/minzc/mza
BUILD_DIR := build

# sjasmplus flags
SJASM_FLAGS := --nologo

# mza flags
MZA_FLAGS := --target zxspectrum -u

# Source files
CHAPTERS  := $(wildcard chapters/ch*/examples/*.a80)
DEMO_MAIN := demo/src/torus.a80

.PHONY: all clean test test-mza demo

all: $(patsubst chapters/%.a80,$(BUILD_DIR)/%.bin,$(CHAPTERS))

$(BUILD_DIR)/%.bin: chapters/%.a80
	@mkdir -p $(dir $@)
	$(SJASMPLUS) $(SJASM_FLAGS) --raw=$@ $<

demo:
	@mkdir -p $(BUILD_DIR)
	cd demo/src && $(SJASMPLUS) $(SJASM_FLAGS) --raw=../../$(BUILD_DIR)/torus.bin torus.a80

# Per-chapter shortcuts
ch%:
	@for f in chapters/$@-*/examples/*.a80; do \
		[ -f "$$f" ] || continue; \
		echo "=== $$f ==="; \
		mkdir -p $(BUILD_DIR); \
		$(SJASMPLUS) $(SJASM_FLAGS) --raw=$(BUILD_DIR)/$$(basename $$f .a80).bin $$f; \
	done

test:
	@ok=0; fail=0; \
	for f in chapters/ch*/examples/*.a80; do \
		[ -f "$$f" ] || continue; \
		if $(SJASMPLUS) $(SJASM_FLAGS) $$f >/dev/null 2>&1; then \
			echo "  OK  $$f"; ok=$$((ok+1)); \
		else \
			echo "FAIL  $$f"; fail=$$((fail+1)); \
		fi; \
	done; \
	if [ -f "$(DEMO_MAIN)" ]; then \
		if (cd demo/src && $(SJASMPLUS) $(SJASM_FLAGS) torus.a80) >/dev/null 2>&1; then \
			echo "  OK  $(DEMO_MAIN)"; ok=$$((ok+1)); \
		else \
			echo "FAIL  $(DEMO_MAIN)"; fail=$$((fail+1)); \
		fi; \
	fi; \
	echo "---"; echo "$$ok passed, $$fail failed"

test-mza:
	@ok=0; fail=0; \
	for f in chapters/ch*/examples/*.a80; do \
		[ -f "$$f" ] || continue; \
		if $(MZA_PATH) $(MZA_FLAGS) -o /dev/null $$f 2>/dev/null; then \
			echo "  OK  $$f"; ok=$$((ok+1)); \
		else \
			echo "FAIL  $$f"; fail=$$((fail+1)); \
		fi; \
	done; \
	echo "---"; echo "$$ok passed, $$fail failed"

clean:
	rm -rf $(BUILD_DIR)
