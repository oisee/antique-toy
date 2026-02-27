# Glossary

Technical vocabulary used throughout *Coding the Impossible*. Terms are grouped by category; "First" indicates the chapter where the term is introduced or defined, "Also" lists chapters with significant usage.

---

## A. Timing & Performance

| Term | Definition | Canonical form | First | Also |
|------|-----------|----------------|-------|------|
| T-state | One clock cycle of the Z80 CPU at 3.5 MHz (~286 ns). The fundamental unit of execution time on the Spectrum. | "T-states" in prose; "T" in code comments (e.g., `; 11T`) | Ch01 | Ch02--Ch23 |
| Frame | One complete display refresh at ~50 Hz (PAL). Duration varies by machine model. | "frame" | Ch01 | all |
| Frame budget | Total T-states between interrupts: Pentagon 71,680, ZX 128K 70,908, ZX 48K 69,888. Practical budget after HALT + ISR + music player: ~66,000--68,000 (Pentagon), ~55,000--60,000 (128K with screen writes during active display). See Ch15 tact-maps for per-region breakdown (top border, active display, bottom border). | "frame budget" | Ch01 | Ch04, Ch05, Ch08, Ch10, Ch12, Ch14, Ch16, Ch17, Ch18, Ch21 |
| Scanline | One horizontal line of the display. Width varies: 224 T-states on 48K/Pentagon, 228 T-states on 128K. The frame consists of 320 (Pentagon), 311 (128K), or 312 (48K) scanlines including borders. | "scanline" (one word) | Ch01 | Ch02, Ch08, Ch15, Ch17 |
| Contended memory | RAM pages ($4000--$7FFF) where ULA and CPU share the memory bus on Sinclair hardware. CPU accesses are delayed by 0--6 extra T-states per access in a repeating 8-T-state pattern. Pentagon clones have no contention. | "contended memory" | Ch01 | Ch04, Ch05, Ch15, Ch17, Ch18, Ch21, Ch22, Ch23 |
| Machine cycle (M-cycle) | A group of 3--6 T-states within an instruction. The first M-cycle (M1) is always the opcode fetch at 4 T-states. | "machine cycle" or "M-cycle" | Ch01 | -- |
| Border time | Scanlines outside the 192-line active display (top/bottom borders). No contention; ~14,000 T-states available on 128K. | "border time" | Ch01 | Ch08, Ch15, Ch17 |
| Timing harness | Debugging technique: set border colour to red before code, black after; stripe height on screen shows T-state cost. | "border-colour timing harness" | Ch01 | Ch02, Ch03, Ch08, Ch18 |

## B. Hardware --- Sinclair & Clones

| Term | Definition | Canonical form | First | Also |
|------|-----------|----------------|-------|------|
| Z80 | Zilog Z80A CPU at 3.5 MHz. 8-bit data bus, 16-bit address bus. The processor in all ZX Spectrum models. | "Z80" | Ch01 | all |
| ULA | Uncommitted Logic Array. Custom chip generating the video signal and handling I/O (keyboard, tape, speaker). Shares the memory bus with the CPU on Sinclair hardware. | "ULA" | Ch01 | Ch02, Ch08, Ch15 |
| ZX Spectrum 48K | Original Sinclair model. 69,888 T-states/frame, 312 scanlines, contended lower 32K. | "48K" or "ZX Spectrum 48K" | Ch01 | Ch11, Ch15 |
| ZX Spectrum 128K | Extended model with 128K banked RAM, AY sound chip, two display pages. 70,908 T-states/frame, 311 scanlines. | "128K" or "ZX Spectrum 128K" | Ch01 | Ch11, Ch15, Ch20, Ch21 |
| Screen memory | $4000--$5AFF. Pixel data ($4000--$57FF, 6,144 bytes) + attribute area ($5800--$5AFF, 768 bytes). Interleaved layout for pixel rows. | "screen memory" | Ch01 | Ch02, Ch08, Ch16, Ch17 |
| Attribute area | 768 bytes at $5800--$5AFF. One byte per 8x8 character cell: FBPPPIII (Flash, Bright, Paper×3, Ink×3). Controls colour. | "attribute area" | Ch02 | Ch08, Ch09, Ch10 |
| Attribute clash | Hardware limitation: only 2 colours (ink + paper) per 8x8 cell. Overlapping sprites force colour compromises. | "attribute clash" | Ch02 | Ch08, Ch16 |
| Interleaved screen layout | Pixel rows in video memory are not sequential. Address encodes Y as 010TTSSS.LLLCCCCC across two bytes. Three 2,048-byte thirds. | "interleaved screen layout" | Ch02 | Ch07, Ch16, Ch17, Ch22 |
| Shadow screen | Second display page at $C000 (bank 7) on 128K. Switched via port $7FFD bit 3. | "shadow screen" | Ch08 | Ch10, Ch15, Ch21 |
| AY-3-8910 | General Instrument Programmable Sound Generator. Three square-wave tone channels, one noise generator, one envelope generator. 14 registers. Standard on 128K models. | "AY-3-8910" (first use), then "AY" | Ch11 | Ch12, Ch15, Ch21 |
| Port $FFFD / $BFFD | AY register select / data write ports on 128K. | "$FFFD" / "$BFFD" | Ch11 | Ch12 |
| Port $7FFD | 128K memory paging and screen select port. | "$7FFD" | Ch08 | Ch12, Ch15, Ch21 |
| Port $FE | I/O port: bits 0--2 = border colour, bit 3 = MIC, bit 4 = EAR/speaker. Also keyboard input (active-low half-rows). | "$FE" | Ch01 | Ch02, Ch11, Ch18 |
| IM1 / IM2 | Interrupt modes. IM1: handler at $0038. IM2: vectored via I register + data bus byte; used for custom interrupt handlers (music players, threading). | "IM1" / "IM2" | Ch01 | Ch03, Ch05, Ch11, Ch12 |
| DivMMC | SD card interface for modern Spectrum use. Supports esxDOS. | "DivMMC" | Ch15 | Ch20 |
| ZX Spectrum Next | FPGA-based enhanced Spectrum. Z80N CPU (extra instructions), Triple AY (3×AY), hardware sprites, copper co-processor, tilemap, 28 MHz turbo. | "ZX Spectrum Next" or "Next" | Ch11 | Ch15 |

## C. Hardware --- Soviet/Post-Soviet Ecosystem

| Term | Definition | Canonical form | First | Also |
|------|-----------|----------------|-------|------|
| Pentagon 128 | Most popular Soviet ZX Spectrum clone. No contended memory, 71,680 T-states/frame, 320 scanlines. The reference platform for the ZX Spectrum demoscene. | "Pentagon 128" (first use), then "Pentagon" | Ch01 | Ch04, Ch05, Ch08, Ch11, Ch15, Ch16, Ch17, Ch18, Ch19, Ch20, Ch21, Ch22 |
| Scorpion ZS-256 | Soviet clone with TurboSound and extended memory. Pentagon-compatible timing. | "Scorpion ZS-256" (first use), then "Scorpion" | Ch04 | Ch11, Ch15, Ch20 |
| TurboSound | Two AY chips (2×AY) in one machine, providing 6 sound channels. Standard on Scorpion; available as add-on for Pentagon. | "TurboSound" | Ch11 | Ch15, Ch20 |
| TR-DOS | Disk operating system on Soviet clones via Beta Disk 128 interface. File format: `.trd`. The standard distribution format for demoscene compos and disk magazines. | "TR-DOS" | Ch15 | Ch20 |
| Beta Disk 128 | Floppy controller interface standard on Pentagon and Scorpion clones. | "Beta Disk 128" | Ch15 | Ch20 |

## D. Hardware --- Agon Light 2

| Term | Definition | Canonical form | First | Also |
|------|-----------|----------------|-------|------|
| Agon Light 2 | Single-board computer with Zilog eZ80 CPU at 18.432 MHz and ESP32-based VDP. 512KB flat RAM, no banking. | "Agon Light 2" or "Agon" | Ch01 | Ch11, Ch15, Ch18, Ch22 |
| eZ80 | Zilog eZ80 CPU. Z80-compatible instruction set; most instructions execute in fewer cycles. 24-bit flat addressing (ADL mode). ~368,640 T-states/frame at 50 Hz. | "eZ80" | Ch01 | Ch15, Ch22 |
| VDP | Video Display Processor. ESP32 microcontroller running FabGL library. Handles display, sprites, tilemaps, sound synthesis. Communicates with eZ80 over serial at 1,152,000 baud. | "VDP" | Ch02 | Ch11, Ch15, Ch18, Ch22 |
| ADL mode | 24-bit addressing mode on the eZ80. Flat 512KB address space, no banking. | "ADL mode" | Ch15 | Ch22 |
| MOS | Operating system on the Agon. Provides API calls for VDP commands, keyboard, filesystem. `waitvblank` replaces Spectrum's HALT for frame sync. | "MOS" | Ch18 | Ch22 |

## E. Techniques

| Term | Definition | Canonical form | First | Also |
|------|-----------|----------------|-------|------|
| Self-modifying code (SMC) | Writing to instruction bytes at runtime. Safe on Z80 (no instruction cache). Common patterns: patching immediate operands, changing jump targets, swapping opcodes. | "self-modifying code (SMC)" on first use; "SMC" subsequently | Ch03 | Ch06, Ch07, Ch09, Ch10, Ch13, Ch16, Ch17, Ch22, Ch23 |
| Unrolled loop | Trade code size for speed by repeating the loop body N times, eliminating loop counter overhead. Partial unrolling keeps DJNZ for the outer count. | "unrolled loop" | Ch02 | Ch03, Ch07, Ch10, Ch16, Ch17 |
| PUSH trick | Hijack SP to use PUSH for fast memory writes (5.5 T-states/byte vs 21 for LDIR). Must DI first to protect against interrupts using the stack. | "PUSH trick" or "stack-based output" | Ch03 | Ch07, Ch08, Ch10, Ch16 |
| LDI chain | Sequence of individual LDI instructions; 24% faster than LDIR for known-size copies. Combined with entry-point arithmetic for variable-length copies. | "LDI chain" | Ch03 | Ch07, Ch09 |
| LDPUSH | Fusing display data into `LD DE,nn : PUSH DE` executable code (21T per 2 bytes). Used in multicolor engines. | "LDPUSH" | Ch08 | -- |
| DOWN_HL | Classic routine to advance HL one pixel row down in the Spectrum's interleaved screen memory. 20T common case, 77T worst case (third boundary). | "DOWN_HL" | Ch02 | Ch16, Ch17, Ch23 |
| RET-chaining | Set SP to a table of addresses; each routine ends with RET, dispatching to the next. 10T per dispatch vs 17T for CALL. | "RET-chaining" | Ch03 | -- |
| Code generation | Writing machine code into a buffer at runtime, then executing it. Eliminates branches and loop counters from inner loops. | "code generation" | Ch03 | Ch06, Ch07, Ch09 |
| Compiled sprites | Sprites compiled into a sequence of PUSH/LD instructions with pre-loaded register pairs. Fixed image, maximum speed. | "compiled sprites" | Ch03 | Ch16 |
| Double buffering | Maintaining two display pages to avoid tearing. On 128K: Screen 0 ($4000) and Screen 1 ($C000), switched via port $7FFD. | "double buffering" | Ch05 | Ch08, Ch10, Ch12 |
| Dirty rectangles | Save/restore background under sprites before/after drawing. Avoid full-screen clears. | "dirty rectangles" | Ch08 | Ch16, Ch21 |
| Multicolor | Changing attribute values between ULA scanline reads to display more than 2 colours per 8x8 cell. Consumes 80--90% of CPU. | "multicolor" | Ch08 | -- |
| Page-aligned table | 256-byte lookup table placed at an $xx00 address so H holds the base and L is the index. Single-register indexing with zero overhead. | "page-aligned table" | Ch04 | Ch06, Ch07, Ch09, Ch10 |
| Lookup table | Pre-computed table of values for fast runtime access. Avoids expensive calculations in inner loops. | "lookup table" | Ch03 | Ch04, Ch07, Ch09, Ch17, Ch19, Ch20, Ch22 |
| Split counters | Restructure screen iteration to match the three-level hierarchy (third/char row/scanline), eliminating branching. 60% faster than naive DOWN_HL traversal. | "split counters" | Ch02 | -- |
| 4-phase colour | 4-frame cycle (2 normal + 2 inverted attributes) at 50 Hz. Persistence of vision averages the colours, creating additional perceived colours per cell. | "4-phase colour" | Ch10 | -- |
| Digital drums | Digital PCM sample played through AY volume register as 4-bit DAC (attack phase), transitioning to AY envelope (decay phase). Consumes ~2 frames of CPU per hit. | "digital drums" or "hybrid drums" | Ch12 | -- |
| Asynchronous frame generation | Decoupling visual frame production from display via a ring buffer. Generator writes frames ahead; display reads at steady 50 Hz. Absorbs CPU bursts from drum playback. | "asynchronous frame generation" | Ch12 | -- |

## F. Assembly Notation & Directives

| Term | Definition | Canonical form | First | Also |
|------|-----------|----------------|-------|------|
| ORG | Assembler directive setting the code origin address. `ORG $8000` for Spectrum examples. | `ORG` | Ch01 | all code examples |
| EQU | Define a named constant. `SCREEN EQU $4000`. | `EQU` | Ch02 | all code examples |
| DB / DW / DS | Define Byte / Define Word / Define Space. `DB -3` (negative values allowed in sjasmplus). | `DB`, `DW`, `DS` | Ch04 | all code examples |
| ALIGN | Align to a power-of-two boundary. sjasmplus directive. | `ALIGN` | Ch07 | -- |
| INCLUDE / INCBIN | Include source file / include binary data. sjasmplus directives. | `INCLUDE` / `INCBIN` | Ch14 | Ch20, Ch21 |
| DEVICE / SLOT / PAGE | sjasmplus directives for 128K memory banking emulation at assembly time. | `DEVICE`, `SLOT`, `PAGE` | Ch15 | Ch20, Ch21 |
| DISPLAY | sjasmplus directive printing a value at assembly time. Build-time diagnostics. | `DISPLAY` | Ch20 | Ch21 |
| `$FF` | Hex notation. `$` prefix is preferred. `#FF` also accepted by sjasmplus. | `$FF` | Ch01 | all |
| `%10101010` | Binary notation. | `%10101010` | Ch01 | all |
| `.label` | Local label, scoped to nearest enclosing global label. | `.label` | Ch01 | all |
| sjasmplus | Primary assembler (v1.21.1). Full Z80/Z80N instruction set, macros, Lua scripting, DEVICE/SLOT/PAGE for banking, INCBIN, multiple output formats. | "sjasmplus" | Ch01 | Ch14, Ch20, Ch21, Ch23 |

## G. Demoscene & Culture

| Term | Definition | Canonical form | First | Also |
|------|-----------|----------------|-------|------|
| Compo | Competition at a demoparty. Categories include demo, intro (size-limited), music, graphics. | "compo" | Ch13 | Ch20 |
| Demoparty | Event where demoscene productions are shown and judged. Major ZX parties: Chaos Constructions, DiHalt, CAFe, Multimatograf (Russia); Revision, Forever (Western Europe). | "demoparty" or "party" | Ch20 | -- |
| NFO / file_id.diz | Text files bundled with demo releases containing credits, requirements, and sometimes technical notes. | "NFO" / "file_id.diz" | Ch20 | -- |
| Making-of | Post-release article documenting the development process and technical decisions of a demo. Published on Hype or in disk magazines. | "making-of" | Ch12 | Ch20 |
| Part / effect | A visual section of a demo (tunnel, scroller, sphere, etc.). Multiple parts are sequenced by a demo engine. | "part" or "effect" | Ch09 | Ch12, Ch20 |
| Scripting engine | System that sequences demo parts and synchronises them to music. Two-level: outer script (effect sequence) + inner script (parameter variation within an effect). | "scripting engine" | Ch09 | Ch12, Ch20 |
| kWORK | Introspec's command: "generate N frames, then show them independently of generation." The bridge between scripting and asynchronous frame generation. | "kWORK" | Ch09 | Ch12 |
| Zapilator | Russian scene slang for a "precalculator" demo -- one that pre-computes all frames before playback. Carries mild disapproval (implies no real-time rendering). | "zapilator" | Ch09 | -- |

### Key People

| Name | Role | Chapters |
|------|------|----------|
| Dark | Coder, X-Trade. Author of Spectrum Expert programming articles. Coder of Illusion. | Ch01, Ch04, Ch05, Ch06, Ch07, Ch10 |
| Introspec (spke) | Coder, Life on Mars. Reverse-engineered Illusion. Authored Hype articles (technical analyses, GO WEST series, DOWN_HL). Coded Eager demo. | Ch01--Ch12, Ch15, Ch23 |
| n1k-o | Musician, Skrju. Composed Eager soundtrack. Developed hybrid drum technique with Introspec. | Ch09, Ch12 |
| diver4d | Coder, 4D+TBK (Triebkraft). GABBA demo (CAFe 2019). Pioneered video-editor sync workflow (Luma Fusion). | Ch09, Ch12 |
| DenisGrachev | Coder. Old Tower, GLUF engine, Ringo engine, Dice Legends. RET-chaining technique. | Ch03, Ch08 |
| Robus | Coder. Z80 threading system, WAYHACK demo. | Ch12 |
| psndcj (cyberjack) | Coder, 4D+TBK (Triebkraft). AY/TurboSound expertise. Break Space demo (Magen Fractal effect). | Ch01, Ch07, Ch14 |
| Screamer (sq) | Coder, Skrju. Chunky pixel optimisation research (Born Dead #05, Hype). Development environment guide. | Ch01, Ch07 |
| Ped7g | Peter Helcmanovsky. sjasmplus maintainer, ZX Spectrum Next contributor. Signed arithmetic and RLE feedback. | Ch04, Ch14, App F |
| RST7 | Coder. Dual-counter DOWN_HL optimisation. | Ch02 |

### Key Demos & Productions

| Name | Author/Group | Year | Chapters |
|------|-------------|------|----------|
| Illusion | X-Trade (Dark) | 1996 | Ch01, Ch04, Ch05, Ch06, Ch07, Ch10 |
| Eager (to live) | Introspec / Life on Mars | 2015 | Ch02, Ch03, Ch09, Ch10, Ch12 |
| GABBA | diver4d / 4D+TBK | 2019 | Ch12 |
| WAYHACK | Robus | -- | Ch12 |
| Old Tower | DenisGrachev | -- | Ch08 |
| Lo-Fi Motion | -- | -- | Ch20 |

### Key Publications

| Name | Description | Chapters |
|------|------------|----------|
| Spectrum Expert (#01--#02) | Russian ZX disk magazine (1997--98). Dark's programming tutorials. | Ch01, Ch04, Ch05, Ch06, Ch10, Ch11 |
| Hype | Russian online demoscene platform (hype.retroscene.org). Technical articles, making-ofs, debates. | Ch01--Ch12, Ch23 |
| Born Dead | Russian demoscene newspaper. sq's chunky pixel research (#05, ~2001). | Ch07 |
| Black Crow | Russian ZX scene magazine. Early multicolor documentation (#05, ~2001). | Ch08 |

## H. Algorithms & Compression

| Term | Definition | Canonical form | First | Also |
|------|-----------|----------------|-------|------|
| Shift-and-add multiply | Classic 8×8 unsigned multiply. Scan multiplier bits, shift-and-add. 196--204 T-states. | "shift-and-add multiply" | Ch04 | Ch05 |
| Square-table multiply | A×B = ((A+B)²−(A−B)²)/4 via lookup. ~61 T-states. Trades 512 bytes of tables for speed. | "square-table multiply" | Ch04 | Ch05, Ch07 |
| Logarithmic division | log(A/B) = log(A)−log(B). Two table lookups + subtraction. ~50--70 T-states. Low precision. | "logarithmic division" | Ch04 | Ch05 |
| Parabolic sine approximation | Approximate sine with parabola y = 1−2(x/π)². Max error ~5.6%. 256-byte table, signed. | "parabolic sine approximation" | Ch04 | Ch05, Ch06, Ch09 |
| Bresenham line drawing | Step along major axis with error accumulator for minor-axis steps. ~80 T-states/pixel naive; ~48 with Dark's 8×8 matrix method. | "Bresenham" | Ch04 | -- |
| Midpoint method | Rotate only basis vertices fully; derive remaining vertices by averaging. ~36 T-states per derived vertex vs ~2,400 for full rotation. | "midpoint method" | Ch05 | -- |
| Fixed-point arithmetic | Represent fractional values in integer registers. Common format: 8.8 (8-bit integer + 8-bit fraction). | "fixed-point" | Ch04 | Ch05, Ch18, Ch19 |
| AABB collision | Axis-Aligned Bounding Box overlap test. Four comparisons: left-right and top-bottom for two rectangles. ~70--156 T-states. | "AABB" | Ch19 | Ch21 |
| Backface culling | Skip back-facing polygons using cross-product normal Z-component test. ~500 T-states per face. | "backface culling" | Ch05 | -- |
| ZX0 | Compression format by Einar Saukas. Excellent ratio, moderate decompression speed. | "ZX0" | Ch14 | Ch20 |
| LZ4 | Fast decompression (~34 T-states/byte). The choice for real-time streaming. | "LZ4" | Ch14 | -- |
| Exomizer | High-ratio compressor for 8-bit platforms. Slow decompression. | "Exomizer" | Ch14 | -- |
| MegaLZ | Compression format. Good ratio/speed balance. | "MegaLZ" | Ch14 | -- |
| hrust1 | Compression format common in Russian demoscene. | "hrust1" | Ch14 | Ch20 |

---

*This glossary is extracted from all 23 chapters of "Coding the Impossible." For detailed treatment of any term, see the chapter listed under "First."*
