#!/bin/bash
# test_mza_compat.sh — E2E binary comparison: mza vs sjasmplus (reference)
# Run from project root: ./test_mza_compat.sh
#
# Tests all .a80 files with both assemblers and compares output byte-for-byte.
# Also runs targeted regression tests for known mza bugs.

set -uo pipefail

SJASMPLUS="${SJASMPLUS:-sjasmplus}"
MZA="${MZA:-$HOME/dev/minz-ts/minzc/mza}"
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

OK=0
FAIL=0
SKIP=0
DETAILS=""

pass() { OK=$((OK+1)); printf "  \033[32mOK\033[0m    %s\n" "$1"; }
fail() { FAIL=$((FAIL+1)); printf "  \033[31mFAIL\033[0m  %s  —  %s\n" "$1" "$2"; DETAILS="$DETAILS\n$1: $2"; }
skip() { SKIP=$((SKIP+1)); printf "  \033[33mSKIP\033[0m  %s  —  %s\n" "$1" "$2"; }

# Check tools exist
if ! command -v "$SJASMPLUS" &>/dev/null; then
    echo "ERROR: sjasmplus not found at '$SJASMPLUS'" >&2; exit 1
fi
if [ ! -x "$MZA" ] && ! command -v "$MZA" &>/dev/null; then
    echo "ERROR: mza not found at '$MZA'" >&2; exit 1
fi

echo "sjasmplus: $($SJASMPLUS --version 2>&1 | head -1)"
echo "mza:       $MZA"
echo ""

# ============================================================
# Part 1: Project files — binary comparison
# ============================================================
echo "=== Part 1: Project files (binary match) ==="
echo ""

compare_file() {
    local src="$1"
    local name="$2"
    local workdir="${3:-.}"

    local sj_bin="$TMPDIR/sj_${name}.bin"
    local mza_bin="$TMPDIR/mza_${name}.bin"
    local mza_raw="$TMPDIR/mza_raw_${name}.bin"

    # Assemble with sjasmplus
    if ! (cd "$workdir" && "$SJASMPLUS" --nologo --raw="$sj_bin" "$(basename "$src")") >/dev/null 2>&1; then
        skip "$src" "sjasmplus failed"
        return
    fi

    # Assemble with mza
    if ! (cd "$workdir" && "$MZA" --target zxspectrum -o "$mza_bin" "$(basename "$src")") 2>/dev/null; then
        fail "$src" "mza assembly failed"
        return
    fi

    # Extract raw bytes from mza SNA (27-byte header + offset to ORG $8000)
    local sj_size
    sj_size=$(wc -c < "$sj_bin" | tr -d ' ')
    dd if="$mza_bin" bs=1 skip=16411 count="$sj_size" 2>/dev/null > "$mza_raw"

    if cmp -s "$sj_bin" "$mza_raw"; then
        pass "$src ($sj_size bytes)"
    else
        local ndiff
        ndiff=$(cmp -l "$sj_bin" "$mza_raw" 2>/dev/null | wc -l | tr -d ' ')
        fail "$src" "$ndiff bytes differ out of $sj_size"
    fi
}

for f in chapters/ch*/examples/*.a80; do
    [ -f "$f" ] || continue
    name=$(basename "$f" .a80)
    compare_file "$f" "$name" "$(dirname "$f")"
done

# Demo (needs cd for INCLUDE paths)
if [ -f demo/src/torus.a80 ]; then
    compare_file "demo/src/torus.a80" "torus" "demo/src"
fi

# ============================================================
# Part 2: Regression tests for specific mza bugs
# ============================================================
echo ""
echo "=== Part 2: Regression tests ==="
echo ""

# --- Bug 1: BIT/SET/RES + EQU constant ---
cat > "$TMPDIR/bug1.a80" << 'EOF'
    ORG $8000
FLAG0 EQU 0
FLAG1 EQU 1
FLAG3 EQU 3
FLAG4 EQU 4
    ; Each pair: literal then EQU — must produce identical bytes
    bit  0, a           ; CB 47
    bit  FLAG0, a       ; CB 47
    bit  1, a           ; CB 4F
    bit  FLAG1, a       ; CB 4F
    bit  3, a           ; CB 5F
    bit  FLAG3, a       ; CB 5F
    bit  4, a           ; CB 67
    bit  FLAG4, a       ; CB 67
    set  3, d           ; CB DA
    set  FLAG3, d       ; CB DA
    res  4, b           ; CB A0
    res  FLAG4, b       ; CB A0
    bit  3, (ix+5)      ; DD CB 05 5E
    bit  FLAG3, (ix+5)  ; DD CB 05 5E
    set  1, (ix+9)      ; DD CB 09 CE
    set  FLAG1, (ix+9)  ; DD CB 09 CE
    res  3, (ix+2)      ; DD CB 02 9E
    res  FLAG3, (ix+2)  ; DD CB 02 9E
    ret
EOF
compare_file "$TMPDIR/bug1.a80" "bug1_bit_equ" "$TMPDIR"

# --- Bug 2: BIT/SET/RES + (HL) ---
cat > "$TMPDIR/bug2.a80" << 'EOF'
    ORG $8000
    bit  0, (hl)        ; CB 46
    bit  3, (hl)        ; CB 5E
    bit  7, (hl)        ; CB 7E
    set  0, (hl)        ; CB C6
    set  3, (hl)        ; CB DE
    set  7, (hl)        ; CB FE
    res  0, (hl)        ; CB 86
    res  3, (hl)        ; CB 9E
    res  7, (hl)        ; CB BE
    ret
EOF
compare_file "$TMPDIR/bug2.a80" "bug2_bit_hl" "$TMPDIR"

# --- Bug 3: Local labels in expressions ---
cat > "$TMPDIR/bug3.a80" << 'EOF'
    ORG $8000
global:
    nop
.local:
    nop
    ld   a, (.local)        ; should load from .local's address
    ld   (.local + 1), a    ; should store to .local + 1
    ret
EOF
compare_file "$TMPDIR/bug3.a80" "bug3_local_expr" "$TMPDIR"

# --- Bug 1+3 combined: BIT + EQU + local labels in expressions ---
cat > "$TMPDIR/bug_combined.a80" << 'EOF'
    ORG $8000
FLAG EQU 3
start:
    nop
.target:
    cp   0
    ld   a, (value)
    bit  FLAG, a            ; must be bit 3, a (CB 5F)
    jr   z, .skip
    ld   (.target + 1), a   ; must reference .target address + 1
.skip:
    ret
value: DB 42
EOF
compare_file "$TMPDIR/bug_combined.a80" "bug_combined" "$TMPDIR"

# ============================================================
# Summary
# ============================================================
echo ""
echo "=== Summary ==="
echo "  Passed: $OK"
echo "  Failed: $FAIL"
echo "  Skipped: $SKIP"
if [ $FAIL -gt 0 ]; then
    echo ""
    echo "Failed details:"
    echo -e "$DETAILS"
    exit 1
fi
