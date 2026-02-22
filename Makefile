# Coding the Impossible — Book Examples Build System
# Supports: mza (MinZ Assembler) primary, sjasmplus secondary
# Note: sjasmplus v1.07 (2008) at ~/dev/bin has compatibility issues.
#       For sjasmplus, use v1.20+ (https://github.com/z00m128/sjasmplus)
#
# Usage:
#   make                    # build all examples with mza
#   make ASM=sjasmplus      # build all with sjasmplus
#   make ch01               # build chapter 1 examples
#   make test               # assemble all, report errors
#   make clean              # remove build artifacts

# Full path needed because mza may be a shell alias
MZA_PATH := $(HOME)/dev/minz-ts/minzc/mza
ASM ?= $(MZA_PATH)
BUILD_DIR := build
CHAPTERS := $(wildcard chapters/ch*/examples/*.a80)

# mza flags
MZA_FLAGS := --target zxspectrum -u
# sjasmplus flags
SJASM_FLAGS := --nologo

.PHONY: all clean test ch01 ch02 ch03 ch04 ch05 ch06

all: $(patsubst chapters/%.a80,$(BUILD_DIR)/%.bin,$(CHAPTERS))

# Generic rule: mza
ifeq ($(ASM),mza)
$(BUILD_DIR)/%.bin: chapters/%.a80
	@mkdir -p $(dir $@)
	$(ASM) $(MZA_FLAGS) -o $@ $<
endif

# Generic rule: sjasmplus
ifeq ($(ASM),sjasmplus)
$(BUILD_DIR)/%.sna: chapters/%.a80
	@mkdir -p $(dir $@)
	$(ASM) $(SJASM_FLAGS) --raw=$@ $<
endif

# Per-chapter shortcuts
ch%:
	@for f in chapters/$@-*/examples/*.a80; do \
		[ -f "$$f" ] || continue; \
		echo "=== $$f ==="; \
		$(ASM) $(MZA_FLAGS) -o $(BUILD_DIR)/$$(basename $$f .a80).bin $$f; \
	done

test:
	@ok=0; fail=0; \
	for f in chapters/ch*/examples/*.a80; do \
		[ -f "$$f" ] || continue; \
		if $(ASM) $(MZA_FLAGS) -o /dev/null $$f 2>/dev/null; then \
			echo "  OK  $$f"; ok=$$((ok+1)); \
		else \
			echo "FAIL  $$f"; fail=$$((fail+1)); \
		fi; \
	done; \
	echo "---"; echo "$$ok passed, $$fail failed"

clean:
	rm -rf $(BUILD_DIR)
