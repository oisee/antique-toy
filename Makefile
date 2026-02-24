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
MZA_RAW_FLAGS := --target generic -f bin -u

# Source files
CHAPTERS  := $(wildcard chapters/ch*/examples/*.a80)
DEMO_MAIN := demo/src/main.a80
DEMO_TORUS := demo/src/torus.a80

# Book build
PYTHON ?= python3
BUILD_BOOK := $(PYTHON) build_book.py

.PHONY: all clean test test-mza test-compare demo book book-a4 book-a5 book-epub release version-bump verify-listings inject-listings audit-tstates autotag-stats screenshots

all: $(patsubst chapters/%.a80,$(BUILD_DIR)/%.bin,$(CHAPTERS))

$(BUILD_DIR)/%.bin: chapters/%.a80
	@mkdir -p $(dir $@)
	$(SJASMPLUS) $(SJASM_FLAGS) --raw=$@ $<

demo:
	@mkdir -p $(BUILD_DIR)
	cd demo/src && $(SJASMPLUS) $(SJASM_FLAGS) main.a80

demo-torus:
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
	if [ -f "$(DEMO_TORUS)" ]; then \
		if (cd demo/src && $(SJASMPLUS) $(SJASM_FLAGS) torus.a80) >/dev/null 2>&1; then \
			echo "  OK  $(DEMO_TORUS)"; ok=$$((ok+1)); \
		else \
			echo "FAIL  $(DEMO_TORUS)"; fail=$$((fail+1)); \
		fi; \
	fi; \
	if [ -f "$(DEMO_MAIN)" ]; then \
		if (cd demo/src && $(SJASMPLUS) $(SJASM_FLAGS) main.a80) >/dev/null 2>&1; then \
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
	if [ -f "$(DEMO_MAIN)" ]; then \
		if (cd demo/src && $(MZA_PATH) $(MZA_FLAGS) -o /dev/null torus.a80) 2>/dev/null; then \
			echo "  OK  $(DEMO_MAIN)"; ok=$$((ok+1)); \
		else \
			echo "FAIL  $(DEMO_MAIN)"; fail=$$((fail+1)); \
		fi; \
	fi; \
	echo "---"; echo "$$ok passed, $$fail failed"

test-compare:
	@ok=0; fail=0; skip=0; \
	mkdir -p $(BUILD_DIR)/cmp-sj $(BUILD_DIR)/cmp-mza; \
	for f in chapters/ch*/examples/*.a80; do \
		[ -f "$$f" ] || continue; \
		base=$$(basename $$f .a80); \
		sj=$(BUILD_DIR)/cmp-sj/$$base.bin; \
		mz=$(BUILD_DIR)/cmp-mza/$$base.bin; \
		if ! $(SJASMPLUS) $(SJASM_FLAGS) --raw=$$sj $$f >/dev/null 2>&1; then \
			echo "SKIP  $$f (sjasmplus failed)"; skip=$$((skip+1)); continue; \
		fi; \
		if ! $(MZA_PATH) $(MZA_RAW_FLAGS) -o $$mz $$f 2>/dev/null; then \
			echo "SKIP  $$f (mza failed)"; skip=$$((skip+1)); continue; \
		fi; \
		if cmp -s $$sj $$mz; then \
			echo "  OK  $$f"; ok=$$((ok+1)); \
		else \
			sjsz=$$(wc -c < $$sj | tr -d ' '); \
			mzsz=$$(wc -c < $$mz | tr -d ' '); \
			echo "DIFF  $$f (sjasmplus=$${sjsz}B, mza=$${mzsz}B)"; \
			fail=$$((fail+1)); \
		fi; \
	done; \
	if [ -f "$(DEMO_MAIN)" ]; then \
		sj=$(BUILD_DIR)/cmp-sj/torus.bin; \
		mz=$(BUILD_DIR)/cmp-mza/torus.bin; \
		if (cd demo/src && $(SJASMPLUS) $(SJASM_FLAGS) --raw=../../$$sj torus.a80) >/dev/null 2>&1 && \
		   (cd demo/src && $(MZA_PATH) $(MZA_RAW_FLAGS) -o ../../$$mz torus.a80) 2>/dev/null; then \
			if cmp -s $$sj $$mz; then \
				echo "  OK  $(DEMO_MAIN)"; ok=$$((ok+1)); \
			else \
				sjsz=$$(wc -c < $$sj | tr -d ' '); \
				mzsz=$$(wc -c < $$mz | tr -d ' '); \
				echo "DIFF  $(DEMO_MAIN) (sjasmplus=$${sjsz}B, mza=$${mzsz}B)"; \
				fail=$$((fail+1)); \
			fi; \
		else \
			echo "SKIP  $(DEMO_MAIN) (assembler failed)"; skip=$$((skip+1)); \
		fi; \
	fi; \
	echo "---"; echo "$$ok match, $$fail differ, $$skip skipped"

# --- Book targets (via build_book.py, auto-increments version) ---
book:
	$(BUILD_BOOK) --all

book-a4:
	$(BUILD_BOOK) --pdf

book-a5:
	$(BUILD_BOOK) --pdf-a5

book-epub:
	$(BUILD_BOOK) --epub

release: clean book
	@mkdir -p release
	cp $(BUILD_DIR)/book-a4-*.pdf $(BUILD_DIR)/book-a5-*.pdf $(BUILD_DIR)/book-*.epub release/
	@echo "Release files copied to release/"

version-bump:
	$(BUILD_BOOK) --bump

verify-listings:
	$(PYTHON) tools/manage_listings.py verify

inject-listings:
	$(PYTHON) tools/manage_listings.py inject --lang all

audit-tstates:
	$(PYTHON) tools/audit_tstates.py --scan-chapters

autotag-stats:
	$(PYTHON) tools/autotag.py --stats

screenshots:
	$(PYTHON) tools/screenshots.py --force

clean:
	rm -rf $(BUILD_DIR)
