#!/usr/bin/env python3
"""Z80 T-State Annotator — reads Z80 assembly and annotates T-state costs.

Parses sjasmplus-compatible .a80 source files, looks up instruction timing
from a built-in database, sums per-block costs, and warns when blocks
exceed frame budgets for ZX Spectrum machines.

Usage:
    python tstate.py source.a80
    cat source.a80 | python tstate.py
    python tstate.py --machine 48k --total source.a80
"""

from __future__ import annotations

import argparse
import html as html_mod
import re
import sys
from typing import TextIO

# ---------------------------------------------------------------------------
# Frame budgets (T-states per frame)
# ---------------------------------------------------------------------------
FRAME_BUDGETS: dict[str, int] = {
    "48k": 69888,
    "128k": 70908,
    "pentagon": 71680,
}

# ---------------------------------------------------------------------------
# T-state database
# ---------------------------------------------------------------------------
# Each entry maps a normalised pattern to either:
#   int          — fixed cost
#   (int, int)   — (taken, not-taken) for conditional instructions
#
# Patterns use placeholders:
#   r    = 8-bit register (a b c d e h l)
#   rr   = 16-bit register pair (bc de hl sp)
#   rrx  = ix or iy
#   cc   = condition code (z nz c nc pe po p m)
#   n    = 8-bit immediate
#   nn   = 16-bit immediate / address
#   d    = signed displacement (ix+d / iy+d)
#   b    = bit number 0-7
#
# The lookup algorithm tries increasingly general patterns.
# ---------------------------------------------------------------------------

# Helpers to build the database concisely
_R8 = {"a", "b", "c", "d", "e", "h", "l"}
_R16 = {"bc", "de", "hl", "sp"}
_RXY = {"ix", "iy"}
_RXY_H = {"ixh", "ixl", "iyh", "iyl"}  # undocumented half-index regs
_CC = {"z", "nz", "c", "nc", "pe", "po", "p", "m"}
_SHIFT_ROT = {"rlc", "rrc", "rl", "rr", "sla", "sra", "srl", "sll"}
_ALU_OPS = {"add", "adc", "sub", "sbc", "and", "xor", "or", "cp"}

# The database: pattern -> cost
# We build it programmatically for completeness, then patch special cases.
TSTATE_DB: dict[str, int | tuple[int, int]] = {}


def _add(pattern: str, cost: int | tuple[int, int]) -> None:
    TSTATE_DB[pattern] = cost


def _build_database() -> None:
    """Populate TSTATE_DB with all standard Z80 instruction timings."""

    # -- NOP, HALT, DI, EI, CCF, SCF, DAA, CPL, RLD, RRD, NEG, EXX --------
    _add("nop", 4)
    _add("halt", 4)
    _add("di", 4)
    _add("ei", 4)
    _add("ccf", 4)
    _add("scf", 4)
    _add("daa", 4)
    _add("cpl", 4)
    _add("neg", 8)
    _add("exx", 4)
    _add("rld", 18)
    _add("rrd", 18)

    # -- IM ------------------------------------------------------------------
    for m in (0, 1, 2):
        _add(f"im {m}", 8)

    # -- LD r,r'  (4T, except r=(HL) or r'=(HL)) ---------------------------
    for dst in _R8:
        for src in _R8:
            _add(f"ld {dst},{src}", 4)
    # LD r,n
    for r in _R8:
        _add(f"ld {r},n", 7)
    # LD r,(HL)
    for r in _R8:
        _add(f"ld {r},(hl)", 7)
    # LD (HL),r
    for r in _R8:
        _add(f"ld (hl),{r}", 7)
    # LD (HL),n
    _add("ld (hl),n", 10)

    # -- LD with IX/IY+d ---------------------------------------------------
    for xy in _RXY:
        for r in _R8:
            _add(f"ld {r},({xy}+d)", 19)
            _add(f"ld ({xy}+d),{r}", 19)
        _add(f"ld ({xy}+d),n", 19)

    # -- LD 16-bit ----------------------------------------------------------
    for rr in ("bc", "de", "hl", "sp"):
        _add(f"ld {rr},nn", 10)
    for xy in _RXY:
        _add(f"ld {xy},nn", 14)
    # LD rr,(nn)  /  LD (nn),rr
    _add("ld hl,(nn)", 16)
    _add("ld (nn),hl", 16)
    for rr in ("bc", "de", "sp"):
        _add(f"ld {rr},(nn)", 20)
        _add(f"ld (nn),{rr}", 20)
    for xy in _RXY:
        _add(f"ld {xy},(nn)", 20)
        _add(f"ld (nn),{xy}", 20)

    # LD A,(rr)  /  LD (rr),A
    for rr in ("bc", "de"):
        _add(f"ld a,({rr})", 7)
        _add(f"ld ({rr}),a", 7)
    _add("ld a,(nn)", 13)
    _add("ld (nn),a", 13)

    # LD SP,HL / LD SP,IX / LD SP,IY
    _add("ld sp,hl", 6)
    for xy in _RXY:
        _add(f"ld sp,{xy}", 10)

    # LD I,A  LD R,A  LD A,I  LD A,R
    _add("ld i,a", 9)
    _add("ld r,a", 9)
    _add("ld a,i", 9)
    _add("ld a,r", 9)

    # -- PUSH / POP ---------------------------------------------------------
    for rr in ("af", "bc", "de", "hl"):
        _add(f"push {rr}", 11)
        _add(f"pop {rr}", 10)
    for xy in _RXY:
        _add(f"push {xy}", 15)
        _add(f"pop {xy}", 14)

    # -- EX -----------------------------------------------------------------
    _add("ex de,hl", 4)
    _add("ex af,af'", 4)
    # Also match without apostrophe
    _add("ex af,af", 4)
    _add("ex (sp),hl", 19)
    for xy in _RXY:
        _add(f"ex (sp),{xy}", 23)

    # -- INC / DEC 8-bit ----------------------------------------------------
    for r in _R8:
        _add(f"inc {r}", 4)
        _add(f"dec {r}", 4)
    _add("inc (hl)", 11)
    _add("dec (hl)", 11)
    for xy in _RXY:
        _add(f"inc ({xy}+d)", 23)
        _add(f"dec ({xy}+d)", 23)

    # -- INC / DEC 16-bit ---------------------------------------------------
    for rr in _R16:
        _add(f"inc {rr}", 6)
        _add(f"dec {rr}", 6)
    for xy in _RXY:
        _add(f"inc {xy}", 10)
        _add(f"dec {xy}", 10)

    # -- Undocumented IXH/IXL/IYH/IYL operations ---------------------------
    for rh in _RXY_H:
        _add(f"inc {rh}", 8)
        _add(f"dec {rh}", 8)
        _add(f"ld {rh},n", 11)
        for r in _R8:
            if r not in ("h", "l"):  # can't mix h/l with ixh/ixl etc.
                _add(f"ld {rh},{r}", 8)
                _add(f"ld {r},{rh}", 8)
        # ld ixh,ixl etc.
        for rh2 in _RXY_H:
            if rh[:2] == rh2[:2]:  # same index register
                _add(f"ld {rh},{rh2}", 8)

    # -- ALU operations (ADD A, ADC A, SUB, SBC A, AND, XOR, OR, CP) -------
    for op in _ALU_OPS:
        prefix = f"{op} a," if op in ("add", "adc", "sbc") else f"{op} "
        # Some assemblers also accept "sub a,r" etc.
        alt_prefix = f"{op} a," if op in ("sub", "and", "xor", "or", "cp") else None
        for r in _R8:
            _add(f"{prefix}{r}", 4)
            if alt_prefix:
                _add(f"{alt_prefix}{r}", 4)
        _add(f"{prefix}n", 7)
        if alt_prefix:
            _add(f"{alt_prefix}n", 7)
        _add(f"{prefix}(hl)", 7)
        if alt_prefix:
            _add(f"{alt_prefix}(hl)", 7)
        for xy in _RXY:
            _add(f"{prefix}({xy}+d)", 19)
            if alt_prefix:
                _add(f"{alt_prefix}({xy}+d)", 19)
        # Undocumented: ALU with IXH/IXL/IYH/IYL
        for rh in _RXY_H:
            _add(f"{prefix}{rh}", 8)
            if alt_prefix:
                _add(f"{alt_prefix}{rh}", 8)

    # -- ADD HL,rr / ADC HL,rr / SBC HL,rr ---------------------------------
    for rr in _R16:
        _add(f"add hl,{rr}", 11)
        _add(f"adc hl,{rr}", 15)
        _add(f"sbc hl,{rr}", 15)
    for xy in _RXY:
        for rr in ("bc", "de", "sp"):
            _add(f"add {xy},{rr}", 15)
        _add(f"add {xy},{xy}", 15)

    # -- Rotate / shift accumulator -----------------------------------------
    _add("rlca", 4)
    _add("rrca", 4)
    _add("rla", 4)
    _add("rra", 4)

    # -- CB-prefix rotate/shift/bit ops -------------------------------------
    for op in _SHIFT_ROT:
        for r in _R8:
            _add(f"{op} {r}", 8)
        _add(f"{op} (hl)", 15)
        for xy in _RXY:
            _add(f"{op} ({xy}+d)", 23)

    # BIT b,r / BIT b,(HL) / BIT b,(IX+d)
    for b in range(8):
        for r in _R8:
            _add(f"bit {b},{r}", 8)
        _add(f"bit {b},(hl)", 12)
        for xy in _RXY:
            _add(f"bit {b},({xy}+d)", 20)

    # SET/RES b,r / SET/RES b,(HL) / SET/RES b,(IX+d)
    for op in ("set", "res"):
        for b in range(8):
            for r in _R8:
                _add(f"{op} {b},{r}", 8)
            _add(f"{op} {b},(hl)", 15)
            for xy in _RXY:
                _add(f"{op} {b},({xy}+d)", 23)

    # -- Jumps, calls, returns ----------------------------------------------
    _add("jp nn", 10)
    _add("jp (hl)", 4)
    for xy in _RXY:
        _add(f"jp ({xy})", 8)
        _add(f"jp ({xy}+d)", 8)  # normaliser converts (ix) to (ix+d)
    for cc in _CC:
        _add(f"jp {cc},nn", 10)

    _add("jr nn", 12)
    for cc in ("z", "nz", "c", "nc"):
        _add(f"jr {cc},nn", (12, 7))

    _add("djnz nn", (13, 8))

    _add("call nn", 17)
    for cc in _CC:
        _add(f"call {cc},nn", (17, 10))

    _add("ret", 10)
    _add("reti", 14)
    _add("retn", 14)
    for cc in _CC:
        _add(f"ret {cc}", (11, 5))

    for n in range(8):
        _add(f"rst {n * 8}", 11)
        _add(f"rst ${n * 8:02x}", 11)
        _add(f"rst ${n * 8:02X}", 11)
    # Also allow rst with hex like $08, $10 etc. and the common rst n form
    _add("rst n", 11)

    # -- I/O ----------------------------------------------------------------
    _add("in a,(n)", 11)
    _add("in a,(nn)", 11)   # normaliser can't distinguish 8/16-bit port
    _add("out (n),a", 11)
    _add("out (nn),a", 11)  # normaliser can't distinguish 8/16-bit port
    for r in _R8:
        _add(f"in {r},(c)", 12)
        _add(f"out (c),{r}", 12)
    # Undocumented: in f,(c) or in (c)
    _add("in f,(c)", 12)
    _add("in (c)", 12)

    # -- Block instructions -------------------------------------------------
    _add("ldi", 16)
    _add("ldd", 16)
    _add("ldir", (21, 16))
    _add("lddr", (21, 16))
    _add("cpi", 16)
    _add("cpd", 16)
    _add("cpir", (21, 16))
    _add("cpdr", (21, 16))
    _add("ini", 16)
    _add("ind", 16)
    _add("inir", (21, 16))
    _add("indr", (21, 16))
    _add("outi", 16)
    _add("outd", 16)
    _add("otir", (21, 16))
    _add("otdr", (21, 16))


_build_database()

# ---------------------------------------------------------------------------
# sjasmplus directive keywords (case-insensitive)
# ---------------------------------------------------------------------------
_DIRECTIVES = {
    "org", "equ", "db", "dw", "dd", "ds", "defs", "defb", "defw", "defd",
    "defm", "dz", "align", "include", "incbin", "device", "slot", "page",
    "macro", "endm", "if", "ifdef", "ifndef", "else", "endif", "end",
    "struct", "ends", "dup", "edup", "rept", "endr", "module", "endmodule",
    "output", "outend", "fpos", "phase", "dephase", "unphase", "disp",
    "ent", "assert", "display", "byte", "word", "block", "savebin",
    "savetrd", "savetap", "savesna", "save3dos", "emptytrd", "emptytap",
    "lua", "endlua", "labelslist", "opt",
}

# ---------------------------------------------------------------------------
# Z80 mnemonic set (for distinguishing labels from instructions)
# ---------------------------------------------------------------------------
_Z80_MNEMONICS = {
    "adc", "add", "and", "bit", "call", "ccf", "cp", "cpd", "cpdr",
    "cpi", "cpir", "cpl", "daa", "dec", "di", "djnz", "ei", "ex",
    "exx", "halt", "im", "in", "inc", "ind", "indr", "ini", "inir",
    "jp", "jr", "ld", "ldd", "lddr", "ldi", "ldir", "neg", "nop",
    "or", "otdr", "otir", "out", "outd", "outi", "pop", "push",
    "res", "ret", "reti", "retn", "rl", "rla", "rlc", "rlca", "rld",
    "rr", "rra", "rrc", "rrca", "rrd", "rst", "sbc", "scf", "set",
    "sla", "sll", "sra", "srl", "sub", "xor",
}

# ---------------------------------------------------------------------------
# Instruction parser
# ---------------------------------------------------------------------------

# Regex to strip a trailing comment
_RE_COMMENT = re.compile(r";.*$")

# Regex to detect a label  (global or local)
# Global: starts at col 0 or word followed by ':'
# Local: starts with '.'
_RE_GLOBAL_LABEL = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:")
_RE_LOCAL_LABEL = re.compile(r"^(\.[A-Za-z_][A-Za-z0-9_]*)\s*:?")

# Regex to detect a constant assignment  LABEL EQU value (or = value)
_RE_EQU = re.compile(
    r"^([A-Za-z_][A-Za-z0-9_]*)\s+(?:EQU|equ|=)\s+", re.IGNORECASE
)


def _normalise_operand(op: str) -> str:
    """Normalise a single operand to a pattern token.

    Replaces numeric literals and expressions with placeholder tokens:
      (ix+<expr>) -> (ix+d)
      (nn)        -> (nn)         when it's a memory reference
      42 / $FF    -> n or nn      depending on context

    This is intentionally approximate — the goal is to match the TSTATE_DB.
    """
    op = op.strip()
    if not op:
        return op

    # (IX+d) / (IY+d) — with any displacement expression
    m = re.match(r"^\(\s*(ix|iy)\s*[+\-].*\)$", op, re.IGNORECASE)
    if m:
        return f"({m.group(1).lower()}+d)"

    # (IX) / (IY) with no displacement — treated as (IX+0)
    m = re.match(r"^\(\s*(ix|iy)\s*\)$", op, re.IGNORECASE)
    if m:
        return f"({m.group(1).lower()}+d)"

    # (HL), (BC), (DE), (SP), (C) — keep as-is (lowercase)
    m = re.match(r"^\(\s*([a-zA-Z]{1,2})\s*\)$", op)
    if m:
        inner = m.group(1).lower()
        if inner in ("hl", "bc", "de", "sp", "c"):
            return f"({inner})"

    # (nn) — parenthesised numeric expression = memory address
    if op.startswith("(") and op.endswith(")"):
        return "(nn)"

    # Register names
    low = op.lower()
    if low in _R8 | _R16 | _RXY | _RXY_H | {"af", "af'", "i", "r", "f"}:
        return low

    # Condition codes
    if low in _CC:
        return low

    # Numeric literal or expression -> n (we'll upgrade to nn at lookup)
    return "n"


def _normalise_instruction(mnemonic: str, operands: list[str]) -> str:
    """Build a normalised instruction key for TSTATE_DB lookup."""
    mnem = mnemonic.lower()
    parts = [mnem]

    norm_ops: list[str] = []
    for i, op in enumerate(operands):
        # BIT/SET/RES/IM/RST: first operand is a literal number, keep as-is
        if i == 0 and mnem in ("bit", "set", "res", "im", "rst"):
            norm_ops.append(op.strip())
        else:
            norm_ops.append(_normalise_operand(op))

    if norm_ops:
        parts.append(",".join(norm_ops))
    return " ".join(parts)


def _parse_operands(operand_str: str) -> list[str]:
    """Split operand string on commas, respecting parentheses."""
    operands: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in operand_str:
        if ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            operands.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    tail = "".join(current).strip()
    if tail:
        operands.append(tail)
    return operands


def lookup_tstates(mnemonic: str, operands: list[str]) -> int | tuple[int, int] | None:
    """Look up T-state cost for a Z80 instruction.

    Returns:
        int            — fixed cost
        (int, int)     — (taken, not-taken) for conditional instructions
        None           — unrecognised instruction
    """
    key = _normalise_instruction(mnemonic, operands)

    # Direct lookup
    if key in TSTATE_DB:
        return TSTATE_DB[key]

    # Try replacing last 'n' with 'nn' (for JP nn, CALL nn, etc.)
    key_nn = key
    if key_nn.endswith(",n"):
        key_nn = key_nn[:-1] + "nn"
    elif key_nn.endswith(" n"):
        key_nn = key_nn[:-1] + "nn"
    if key_nn in TSTATE_DB:
        return TSTATE_DB[key_nn]

    # For two-operand instructions, try nn for first operand too
    # e.g. "ld (n),a" -> "ld (nn),a"
    key_nn2 = re.sub(r"\(n\)", "(nn)", key)
    if key_nn2 != key and key_nn2 in TSTATE_DB:
        return TSTATE_DB[key_nn2]

    # Combined: both operand upgrades
    key_nn3 = re.sub(r"\(n\)", "(nn)", key_nn)
    if key_nn3 != key and key_nn3 in TSTATE_DB:
        return TSTATE_DB[key_nn3]

    # Try "rst n" catch-all
    if mnemonic.lower() == "rst":
        return TSTATE_DB.get("rst n")

    # BIT/SET/RES with symbolic bit number: try substituting 0 as bit number
    # since T-state cost is identical regardless of which bit
    mnem = mnemonic.lower()
    if mnem in ("bit", "set", "res") and len(operands) == 2:
        second = _normalise_operand(operands[1])
        test_key = f"{mnem} 0,{second}"
        if test_key in TSTATE_DB:
            return TSTATE_DB[test_key]

    # IM with symbolic argument
    if mnem == "im" and len(operands) == 1:
        return 8  # IM 0/1/2 all cost 8T

    return None


# ---------------------------------------------------------------------------
# Line classifier
# ---------------------------------------------------------------------------

class LineInfo:
    """Parsed information about a single source line."""

    __slots__ = (
        "raw", "stripped", "is_blank", "is_comment_only",
        "global_label", "local_label", "is_directive", "is_equ",
        "mnemonic", "operands", "tstates", "comment",
        "multi_tstates",
    )

    def __init__(self, raw: str) -> None:
        self.raw = raw.rstrip("\n\r")
        self.stripped = ""
        self.is_blank = False
        self.is_comment_only = False
        self.global_label: str | None = None
        self.local_label: str | None = None
        self.is_directive = False
        self.is_equ = False
        self.mnemonic: str | None = None
        self.operands: list[str] = []
        self.tstates: int | tuple[int, int] | None = None
        self.comment: str | None = None
        # For multi-statement lines (nop : nop : nop), list of costs
        self.multi_tstates: list[int | tuple[int, int] | None] | None = None


def parse_line(raw: str) -> LineInfo:
    """Parse a single assembly source line."""
    info = LineInfo(raw)

    # Extract trailing comment
    line = raw.rstrip("\n\r")
    comment_match = _RE_COMMENT.search(line)
    if comment_match:
        info.comment = comment_match.group()
        line = line[:comment_match.start()]
    else:
        info.comment = None

    info.stripped = line.strip()

    if not info.stripped:
        if info.comment:
            info.is_comment_only = True
        else:
            info.is_blank = True
        return info

    work = info.stripped

    # Check for EQU-style constant assignment (before label check)
    if _RE_EQU.match(work):
        info.is_equ = True
        info.is_directive = True
        return info

    # Check for global label
    # Exclude known Z80 mnemonics from being treated as labels
    # (e.g. "nop : nop" where "nop" followed by " :" looks like a label)
    m = _RE_GLOBAL_LABEL.match(work)
    if m and m.group(1).lower() not in _Z80_MNEMONICS:
        info.global_label = m.group(1)
        work = work[m.end():].strip()
        if not work:
            return info

    # Check for local label
    if not info.global_label:
        m = _RE_LOCAL_LABEL.match(work)
        if m:
            info.local_label = m.group(1)
            work = work[m.end():].strip()
            if not work:
                return info

    if not work:
        return info

    # sjasmplus multi-statement separator: "nop : nop : nop"
    # Split on ' : ' (colon with surrounding spaces) to detect multi-statement lines.
    # Must be careful not to split operands like "(ix+3)" or label suffixes.
    statements = re.split(r"\s+:\s+", work)
    if len(statements) > 1:
        # Multi-statement line: parse each statement, collect T-states
        multi_costs: list[int | tuple[int, int] | None] = []
        first_mnemonic = None
        for stmt in statements:
            stmt = stmt.strip()
            if not stmt:
                continue
            s_parts = stmt.split(None, 1)
            s_mnemonic = s_parts[0].lower()
            s_rest = s_parts[1].strip() if len(s_parts) > 1 else ""
            if s_mnemonic in _DIRECTIVES:
                continue
            s_operands = _parse_operands(s_rest) if s_rest else []
            cost = lookup_tstates(s_mnemonic, s_operands)
            multi_costs.append(cost)
            if first_mnemonic is None:
                first_mnemonic = s_mnemonic
                info.operands = s_operands

        info.mnemonic = first_mnemonic
        info.multi_tstates = multi_costs
        # Compute total T-states for the line
        info.tstates = _sum_multi_costs(multi_costs)
        return info

    # Single statement
    # Split into mnemonic and operands
    parts = work.split(None, 1)
    mnemonic = parts[0].lower()
    rest = parts[1].strip() if len(parts) > 1 else ""

    # Check for directives
    if mnemonic in _DIRECTIVES:
        info.is_directive = True
        return info

    info.mnemonic = mnemonic
    if rest:
        info.operands = _parse_operands(rest)
    else:
        info.operands = []

    # Look up T-states
    info.tstates = lookup_tstates(mnemonic, info.operands)

    return info


def _sum_multi_costs(
    costs: list[int | tuple[int, int] | None],
) -> int | tuple[int, int] | None:
    """Sum T-state costs from multiple statements on one line."""
    if not costs:
        return None
    if any(c is None for c in costs):
        return None  # can't sum if any are unknown
    total_min = 0
    total_max = 0
    for c in costs:
        if isinstance(c, tuple):
            total_max += c[0]
            total_min += c[1]
        else:
            assert isinstance(c, int)
            total_min += c
            total_max += c
    if total_min == total_max:
        return total_min
    return (total_max, total_min)


# ---------------------------------------------------------------------------
# Block tracker
# ---------------------------------------------------------------------------

class Block:
    """A block of code between global labels."""

    def __init__(self, label: str | None) -> None:
        self.label = label
        self.min_tstates = 0  # sum of min (not-taken for conditionals)
        self.max_tstates = 0  # sum of max (taken for conditionals)
        self.has_unknown = False
        self.first_line_idx = 0
        self.exit_instruction: str | None = None  # jp, jr, ret, etc.

    def add(self, cost: int | tuple[int, int] | None) -> None:
        if cost is None:
            self.has_unknown = True
            return
        if isinstance(cost, tuple):
            taken, not_taken = cost
            self.min_tstates += not_taken
            self.max_tstates += taken
        else:
            self.min_tstates += cost
            self.max_tstates += cost


# ---------------------------------------------------------------------------
# Annotation formatter
# ---------------------------------------------------------------------------

def _format_tstates(cost: int | tuple[int, int] | None) -> str:
    """Format T-state cost as a string."""
    if cost is None:
        return "?T"
    if isinstance(cost, tuple):
        taken, not_taken = cost
        return f"{taken}T/{not_taken}T (taken/not-taken)"
    return f"{cost}T"


def _block_summary(block: Block) -> str:
    """Format block summary string."""
    label = block.label or "(top)"
    if block.min_tstates == block.max_tstates:
        return f"{label} ({block.min_tstates}T)"
    return f"{label} ({block.min_tstates}T..{block.max_tstates}T)"


def _is_exit_mnemonic(mnemonic: str | None) -> str | None:
    """If mnemonic is a block-exiting instruction, return its name."""
    if mnemonic is None:
        return None
    m = mnemonic.lower()
    if m in ("jp", "jr", "ret", "reti", "retn"):
        return m.upper()
    return None


# ---------------------------------------------------------------------------
# Annotation column width
# ---------------------------------------------------------------------------
_ANNOTATION_COL = 40  # column where annotations start


def _pad_to_col(text: str, col: int) -> str:
    """Pad text with spaces to reach the given column."""
    if len(text) >= col:
        return text + " "
    return text + " " * (col - len(text))


# ---------------------------------------------------------------------------
# Main annotator
# ---------------------------------------------------------------------------

def annotate(
    source: TextIO,
    machine: str = "pentagon",
    blocks_only: bool = False,
    show_total: bool = False,
    quiet: bool = False,
    output_html: bool = False,
) -> str:
    """Annotate assembly source with T-state costs.

    Returns the annotated text as a string.
    """
    budget = FRAME_BUDGETS[machine]
    lines = source.readlines()

    # Parse all lines
    parsed: list[LineInfo] = [parse_line(line) for line in lines]

    # Post-parse: mark lines inside LUA/ENDLUA blocks as directives
    in_lua = False
    for info in parsed:
        stripped_lower = info.stripped.lower()
        if stripped_lower.startswith("lua"):
            in_lua = True
            info.is_directive = True
            info.mnemonic = None
            info.tstates = None
            continue
        if stripped_lower.startswith("endlua"):
            in_lua = False
            info.is_directive = True
            info.mnemonic = None
            info.tstates = None
            continue
        if in_lua:
            info.is_directive = True
            info.mnemonic = None
            info.tstates = None

    # Identify blocks (between global labels)
    blocks: list[Block] = []
    current_block = Block(None)
    current_block.first_line_idx = 0

    for idx, info in enumerate(parsed):
        if info.global_label:
            # Finish previous block
            blocks.append(current_block)
            current_block = Block(info.global_label)
            current_block.first_line_idx = idx
        if info.mnemonic:
            current_block.add(info.tstates)
            exit_type = _is_exit_mnemonic(info.mnemonic)
            if exit_type:
                current_block.exit_instruction = exit_type

    blocks.append(current_block)

    # Build block summary lookup: line_idx -> block that starts here
    block_start_map: dict[int, Block] = {}
    for blk in blocks:
        block_start_map[blk.first_line_idx] = blk

    # Build output
    output_lines: list[str] = []
    total_min = 0
    total_max = 0
    total_unknown = False
    warnings: list[str] = []

    for idx, info in enumerate(parsed):
        # Check if a new block starts at this line
        blk = block_start_map.get(idx)
        if blk is not None and blk.label is not None:
            # Insert block header before this line
            summary = _block_summary(blk)
            header = f"; --- Block: {summary} ---"

            # Check budget warnings
            warn_parts: list[str] = []
            if blk.has_unknown:
                warn_parts.append("contains ?T instructions")
            if blk.max_tstates > budget:
                warn_parts.append(f"exceeds {machine} budget: {budget}T")
                warnings.append(
                    f"Block '{blk.label}': {blk.max_tstates}T exceeds "
                    f"{machine} frame budget ({budget}T)"
                )

            if warn_parts:
                header += "  [WARNING: " + "; ".join(warn_parts) + "]"

            exit_note = ""
            if blk.exit_instruction:
                exit_note = f"  [exits via {blk.exit_instruction}]"
            if exit_note:
                header += exit_note

            # Emit blank separator + header
            padded = _pad_to_col("", _ANNOTATION_COL)
            output_lines.append(f"{padded}{header}")

        # Format this line
        if blocks_only:
            # In blocks-only mode, skip individual line output
            # except block headers (already emitted above)
            continue

        raw = info.raw

        if info.is_blank or info.is_comment_only:
            output_lines.append(raw)
            continue

        if info.is_directive or info.is_equ:
            output_lines.append(raw)
            continue

        if info.global_label and info.mnemonic is None:
            # Label-only line
            padded = _pad_to_col(raw, _ANNOTATION_COL)
            output_lines.append(f"{padded};")
            continue

        if info.local_label and info.mnemonic is None:
            # Local label-only line
            padded = _pad_to_col(raw, _ANNOTATION_COL)
            output_lines.append(f"{padded};")
            continue

        if info.mnemonic:
            cost_str = _format_tstates(info.tstates)
            padded = _pad_to_col(raw, _ANNOTATION_COL)
            output_lines.append(f"{padded}; {cost_str}")

            # Accumulate totals
            if info.tstates is None:
                total_unknown = True
            elif isinstance(info.tstates, tuple):
                total_min += info.tstates[1]
                total_max += info.tstates[0]
            else:
                total_min += info.tstates
                total_max += info.tstates
        else:
            # Unrecognised — just pass through
            output_lines.append(raw)

    # Totals — when blocks_only, compute from block summaries
    if show_total:
        if blocks_only:
            total_min = sum(blk.min_tstates for blk in blocks)
            total_max = sum(blk.max_tstates for blk in blocks)
            total_unknown = any(blk.has_unknown for blk in blocks)
        output_lines.append("")
        if total_min == total_max:
            total_str = f"; === Total: {total_min}T ==="
        else:
            total_str = f"; === Total: {total_min}T..{total_max}T ==="
        if total_unknown:
            total_str += "  (some instructions unrecognised)"
        output_lines.append(total_str)

    # Quiet mode: only output warnings
    if quiet:
        return "\n".join(warnings) + ("\n" if warnings else "")

    result = "\n".join(output_lines) + "\n"

    # HTML output
    if output_html:
        result = _to_html(output_lines)

    # Append warnings to stderr
    for w in warnings:
        print(f"WARNING: {w}", file=sys.stderr)

    return result


# ---------------------------------------------------------------------------
# HTML output
# ---------------------------------------------------------------------------

_HTML_HEADER = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Z80 T-State Analysis</title>
<style>
body { background: #1e1e1e; color: #d4d4d4; font-family: 'Consolas', 'Monaco', monospace; font-size: 14px; padding: 20px; }
pre { line-height: 1.4; }
.t-fast { color: #4ec9b0; }     /* green — <=7T */
.t-medium { color: #dcdcaa; }   /* yellow — 8-15T */
.t-slow { color: #ce9178; }     /* orange — 16-19T */
.t-very-slow { color: #f44747; } /* red — >=20T */
.t-unknown { color: #f44747; font-weight: bold; }
.block-header { color: #569cd6; font-weight: bold; }
.warning { color: #f44747; font-weight: bold; }
.label { color: #4fc1ff; }
.comment { color: #6a9955; }
.total { color: #c586c0; font-weight: bold; }
</style>
</head>
<body>
<pre>
"""

_HTML_FOOTER = """\
</pre>
</body>
</html>
"""


def _classify_cost(cost_str: str) -> str:
    """Return a CSS class based on T-state cost."""
    if "?T" in cost_str:
        return "t-unknown"
    # Extract the first number
    m = re.search(r"(\d+)T", cost_str)
    if not m:
        return ""
    t = int(m.group(1))
    if t <= 7:
        return "t-fast"
    if t <= 15:
        return "t-medium"
    if t <= 19:
        return "t-slow"
    return "t-very-slow"


def _to_html(lines: list[str]) -> str:
    """Convert annotated output lines to HTML."""
    parts = [_HTML_HEADER]
    for line in lines:
        escaped = html_mod.escape(line)

        # Colour block headers
        if "; --- Block:" in line:
            if "WARNING" in line:
                escaped = f'<span class="block-header warning">{escaped}</span>'
            else:
                escaped = f'<span class="block-header">{escaped}</span>'
        elif line.startswith("; === Total:"):
            escaped = f'<span class="total">{escaped}</span>'
        else:
            # Colour the T-state annotation part
            # Find the annotation after the source code
            m = re.match(r"^(.*?)(;\s*\d+T.*|;\s*\?T.*)$", line)
            if m:
                src_part = html_mod.escape(m.group(1))
                ann_part = m.group(2)
                cost_class = _classify_cost(ann_part)
                ann_escaped = html_mod.escape(ann_part)
                if cost_class:
                    escaped = f'{src_part}<span class="{cost_class}">{ann_escaped}</span>'

        parts.append(escaped)
        parts.append("\n")

    parts.append(_HTML_FOOTER)
    return "".join(parts)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tstate",
        description="Z80 T-State Annotator — annotate assembly with cycle costs",
        epilog=(
            "Examples:\n"
            "  python tstate.py source.a80\n"
            "  python tstate.py --machine 48k --total source.a80\n"
            "  cat source.a80 | python tstate.py --html > annotated.html\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "file",
        nargs="?",
        help="Input .a80 assembly file (reads stdin if omitted)",
    )
    parser.add_argument(
        "--machine",
        choices=["48k", "128k", "pentagon"],
        default="pentagon",
        help="Frame budget for warnings (default: pentagon = 71680T)",
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="Output as HTML with colour coding",
    )
    parser.add_argument(
        "--blocks-only",
        action="store_true",
        help="Only show block summaries, not per-instruction",
    )
    parser.add_argument(
        "--total",
        action="store_true",
        help="Show total T-states at end",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Quiet mode: only output warnings",
    )
    args = parser.parse_args()

    if args.file:
        try:
            source = open(args.file, "r", encoding="utf-8")
        except FileNotFoundError:
            print(f"Error: file not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        except OSError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        source = sys.stdin

    try:
        result = annotate(
            source,
            machine=args.machine,
            blocks_only=args.blocks_only,
            show_total=args.total,
            quiet=args.quiet,
            output_html=args.html,
        )
    finally:
        if source is not sys.stdin:
            source.close()

    sys.stdout.write(result)


if __name__ == "__main__":
    main()
