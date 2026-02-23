# ZX Spectrum Development Tools Survey (Feb 2026)

## Recommended Modern Toolchain

| Role | Tool | Notes |
|------|------|-------|
| Editor | VS Code + Z80 Macro-Assembler + ASM Code Lens + Z80 Assembly meter | Free, cross-platform |
| Assembler | sjasmplus (primary), RASM (built-in compression) | Both actively maintained |
| Debugger | DeZog (VS Code, built-in simulator or socket to emulator) | By maziac, very active |
| Emulator | ZEsarUX (general), #CSpect (Next), Fuse (accuracy) | All with debug support |
| Music | Arkos Tracker 3 (cross-platform) or Vortex Tracker II/2.6 | AT3 = most active |
| Graphics | Multipaint (cross-platform) or ZX-Paintbrush (Windows) | Attr-aware |
| Compression | ZX0 (best ratio/speed), LZSA2 (fastest decompress) | Einar Saukas / E. Marty |
| Disassembly | SkoolKit (Python, gold standard) + Spectrum Analyser (alpha) | Active |
| Image conv | img2spec (interactive) or autodiver (attribute optimization) | |

## Assemblers

- **sjasmplus** — full Z80/Z80N, macros, Lua, TAP/TRD/SNA output. github.com/z00m128/sjasmplus
- **RASM** v2.3.9 — extremely fast, built-in ZX0/ZX7/Exomizer/LZSA compression. github.com/EdouardBERGE/rasm
- **z88dk** — full C + asm SDK for 100+ Z80 machines. github.com/z88dk/z88dk
- **Pasmo** v0.5.5 — simple, not actively maintained. PasmoNext fork for Z80N.
- **Zasm** v4.5.0 — multi-syntax support, Z80N. github.com/Megatokio/zasm
- **Specasm** — assembler running NATIVELY on ZX Spectrum! github.com/markdryan/specasm
- **Boriel ZX BASIC** — BASIC-to-Z80 compiler. github.com/boriel-basic/zxbasic

## Graphics Editors

- **Multipaint** 2025.3 — multi-platform, attr-aware, ZX/C64/MSX/CPC. multipaint.kameli.net
- **ZX-Paintbrush** — Windows, full attr awareness + multicolor. zx-modules.jimdofree.com
- **Colorator** — ZX Spectrum hi-color editor. github.com/yomboprime/colorator

## Image Converters

- **img2spec** — interactive GUI with real-time preview. github.com/jarikomppa/img2spec
- **BMP2SCR** — classic, high quality, Windows only. Legacy but still used.
- **autodiver** (oisee) — attribute grid optimization via shift/scale/rotate. github.com/oisee/autodiver_go
- **Gfx2Next** — for Spectrum Next formats. rustypixels.uk/gfx2next
- **SCRplus** — Python converter. github.com/avian2/scrplus

## Music Trackers

- **Arkos Tracker 3.5** (Dec 2025) — cross-platform, unlimited AY, MIDI import. julien-nevo.com/arkostracker
- **Vortex Tracker II** / 2.5 / 2.6 — classic PT3 editor, triple AY in v2.6. bulba.untergrund.net
- **VTi** (oisee) — VT II mod with envelope-as-notes, Table #5. github.com/oisee/vti
- **autosiril** (oisee) — MIDI-to-PT3 converter. github.com/oisee/autosiril

## Compressors

- **ZX0** — optimal, 69-byte decompressor. github.com/einar-saukas/ZX0
- **ZX1** — simpler ZX0, -1.5% ratio +15% speed. github.com/einar-saukas/ZX1
- **ZX2** — minimalist. github.com/einar-saukas/ZX2
- **Exomizer 3** — best absolute ratio, larger decompressor. bitbucket.org/magli143/exomizer
- **APUltra** — aPLib format, 5-7% better than original. github.com/emmanuel-marty/apultra
- **LZSA/LZSA2** — fastest decompression, 67-byte Z80 decompressor. github.com/emmanuel-marty/lzsa
- **RCS** — screen reorder for better compression. github.com/einar-saukas/RCS

## Emulators

- **ZEsarUX** v12.1 — DeZog socket, ZENG networking, comprehensive. github.com/chernandezba/zesarux
- **#CSpect** v3.0 — Spectrum Next focused, DeZog compatible. mdf200.itch.io/cspect
- **Fuse** — most accurate classic Spectrum emulation. fuse-emulator.sourceforge.net
- **Retro Virtual Machine** v2.1.20 — CRT effects, pixel editor. retrovirtualmachine.org

## VS Code Extensions

- **DeZog** (maziac) — full Z80 debugger, built-in simulator. marketplace: maziac.dezog
- **ASM Code Lens** (maziac) — go-to-def, references, rename. marketplace: maziac.asm-code-lens
- **Z80 Macro-Assembler** (mborik) — syntax highlighting. marketplace: mborik.z80-macroasm
- **Z80 Assembly meter** (theNestruo) — T-state counter in status bar! marketplace: theNestruo.z80-asm-meter
- **EZ80 Assembly** (Alex Parker) — eZ80 highlighting for Agon Light 2.

## Disassembly / Analysis

- **SkoolKit** v9.6 — Python, annotated HTML disassembly, code tracing. skoolkit.ca
- **Spectrum Analyser** — interactive RE: emulator+debugger+disasm+gfx viewer. colourclash.co.uk
- **Ghidra** — free, has Z80 module + RetroGhidra for ZX loaders. github.com/hippietrail/RetroGhidra
- **IDA Pro** — commercial gold standard. hex-rays.com

## Game/Demo Libraries

- **lib-spectrum** — Z80 game dev modules. github.com/breakintoprogram/lib-spectrum
- **lib-spectrum-next** — Next-specific Z80 library. github.com/breakintoprogram/lib-spectrum-next
- **libzx** — homebrew game library. sebastianmihai.com/libzx.html
- **NextBuild Studio** v1.1.1 — Boriel BASIC IDE for Next. zxbasic.uk/nextbuildstudio
