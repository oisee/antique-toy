# Session Wisdom — antique-toy book project

> Accumulated knowledge from the birthday marathon sessions (2026-03-26/27)

---

## The Constellation

This book isn't built in isolation. It's the hub of a constellation of AI-assisted projects, all communicating via `ddll` (dedelulu supervisor):

| Project | Session | What It Does | What It Gives the Book |
|---------|---------|-------------|----------------------|
| **antique-toy** | `eo29c66e` | The book itself | 23 chapters + 15 appendices (A-O) |
| **z80-optimizer** | `um2dy4ex` | GPU brute-force Z80 superoptimizer | 501 optimal sequences, tables, meta-analysis |
| **minz** | `ju6yy047` | MZA assembler + Nanz compiler | INCBIN, RLCA sled, peephole, DD gotcha |
| **minz-vir** | `cok1cgsq` | VIR compiler backend + mir2gpu | GPU shaders from Nanz, TSMC tunnels, SQL on ZX |
| **dedelulu** | `gq1enuw8` | ddll supervisor | Inter-session comms, `ddll ask` for external LLMs |

Session IDs change on restart. Use `ddll explore` to get current ones.

---

## Communication Patterns That Work

1. **Introduce yourself** — neighbors are friendly. Say you're from antique-toy, ask what's new.
2. **Be specific about what you need** — "новый материал для книги" gets better responses than "как дела".
3. **Ask them to deliver files to `_in/`** — neighbors can write directly to `~/dev/antique-toy/_in/`.
4. **Acknowledge deliveries** — they like knowing their files arrived.
5. **The constellation is async** — don't wait for responses, do other work.

### ddll Commands
```sh
ddll explore                                    # who's alive?
ddll send session_id:main "message"             # talk to a neighbor
ddll ask gpt54 "question"                       # ephemeral external LLM
ddll ask gpt54 -s session "question"            # persistent external LLM session
ddll ask gemini -f file.md "review @file.md"    # file injection
```

---

## What Each Neighbor Knows

### z80-optimizer (um2dy4ex)
- All optimal Z80 arithmetic: 254 mul, 247 div, branchless idioms
- FP16 format family (byte-aligned exponent, INC H = ×2)
- LUT generators (12 bytes → 256-byte table)
- Meta-analysis of 755 sequences
- BCD arithmetic with correct DAA H-flag model
- Writes articles and chronicles in Russian
- **Personality:** enthusiastic, delivers big data dumps, uses 🎂

### minz (ju6yy047)
- MZA assembler internals (v0.23.0+)
- RLCA sled peephole optimization
- DD prefix gotchas (LD IXH,H = NOP)
- INCBIN directive
- Nanz language features
- **Personality:** thorough, provides well-structured highlights files

### minz-vir (cok1cgsq, was jjjlhyva)
- VIR compiler backend, register allocation (83.6M table)
- mir2gpu: Nanz → GPU compute shaders (4 APIs, 1284 LOC)
- TSMC tunnels (self-modifying code for register saves, 20T SP-free)
- SQL on ZX Spectrum (31 functions, Z3-optimized)
- **Personality:** technical, lists concrete achievements, asks "what's relevant?"

### dedelulu (gq1enuw8)
- ddll internals and new features
- LLM endpoint management
- **Personality:** helpful, demonstrates features with examples

---

## Book Architecture

### Current State (v27)
- **23 chapters** (ch01-ch23): Z80 demoscene techniques, ZX Spectrum + Agon Light 2
- **15 appendices** (A-O):
  - A-J: reference material (Z80 ISA, sine tables, compression, dev setup, etc.)
  - **K: GPU Superoptimization** — 501 sequences, the crown jewel
  - **L: Z80-Optimal Floating Point** — byte-aligned exponent family
  - **M: BCD Arithmetic** — DAA-based, GPU-proven
  - **N: LUT Generators** — compression via computation
  - **O: Meta-Analysis** — 21-instruction thesis, 10 insights
- **3 translations**: ES, RU, UK (check `translations/manifest.py check all` for staleness)

### Build Pipeline
```sh
python3 build_book.py --bump    # bump version + build all (EN)
python3 build_book.py --all     # build without bump
python3 build_book.py --epub    # EPUB only
make test                       # verify all .a80 examples compile
```
Requires: `lualatex` (texlive-luatex + fonts-extra), `pandoc`, `weasyprint` (fallback PDF).

### Release Pipeline
```sh
cp build/book-*.pdf build/book-*.epub release/
git add ... && git commit && git push
gh release create vNN release/book-* --title "..." --notes "..."
gh release upload vNN release/book-* --clobber    # update existing
```

---

## Key Technical Insights (for writing/editing)

### Z80 Tricks Worth Remembering
- `SBC A,A` = carry-to-mask ($00/$FF) — THE universal conditional
- `NEG` = ×255 (because -1 mod 256 = 255)
- `INC H` = fp16 ×2 (byte-aligned exponent)
- `ADD A,A : DAA` = BCD ×2 (2 ops!)
- RLCA sled: 9 bytes, 7 entry points (barrel shifter without a barrel shifter)
- TSMC tunnels: `LD (.smc+1),A` for register save without PUSH/POP, SP stays free
- DD prefix gotcha: `LD IXH,H` = NOP because H resolves to IXH under DD

### The 21-Instruction Thesis
Only 21 of ~700 Z80 opcodes appear in ANY optimal arithmetic sequence. Three instructions (ADD A,A + ADD A,B + LD B,A) cover 74% of all mul8 slots. The mul8 and mul16 pools are completely disjoint (different register worlds).

### Numbers to Quote
- 501 provably optimal arithmetic sequences
- 254/254 multiplies ALL DIRECT (no composition)
- 247/247 divisions COMPLETE (zero gaps)
- div171 = 4 insts, 27T (fastest Z80 division)
- ×2 via RLA = 4T (50× faster than Dark's general loop)
- ~2KB packed library = ALL Z80 constant arithmetic
- 739,574 peephole rules
- 83.6M register allocation entries

---

## Process Wisdom

### What Worked
- **Parallel neighbor queries** — ask everyone at once, process responses as they arrive
- **Files in `_in/`** — single collection point for all incoming material
- **Appendix-per-topic** — clean separation, each can be updated independently
- **Version bumps per content change** — v25→v26→v27 in one evening
- **GitHub Releases** — immediate distribution, neighbors can check results

### What to Watch For
- **Session IDs change on restart** — always `ddll explore` first
- **Translations go stale** — run `manifest.py check all` after EN changes
- **Screenshots missing** — build warns but succeeds (text/tables fine, images show as descriptions)
- **lualatex required for proper PDF** — weasyprint works as fallback but different typography
- **Don't forget `--bump`** — content changes need version bumps for releases

### Alice's Style
- Russian for planning/chat, English for chapter prose
- Informal, friendly, uses =) and emoji
- Likes concise updates, no hand-holding
- Trusts autonomous work, just wants results
- Values the demoscene community connections (Introspec, Ped7g, n1k-o, psndcj, 4D)
