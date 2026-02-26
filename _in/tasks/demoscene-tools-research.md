# Demoscene Tools Research (2026-02-26)

For potential Appendix J: "Demoscene Tools & Modern Production Pipeline"

## Farbrausch Tools (open-sourced 2012)

Repository: https://github.com/farbrausch/fr_public
License: BSD / public domain

| Tool | What | Status |
|------|------|--------|
| Werkkzeug 1-4 | Node-based procedural demotool (textures, meshes, timeline) | Archived, VS2010 |
| kkrunchy | Exe packer for 64k intros (context mixing + arithmetic coding) | Archived but still used |
| V2 Synthesizer | Softsynth for 64k intros (VSTi + player) | Archived, community forks exist |
| OpenKTG | Standalone procedural texture generator | Archived |
| RauschGenerator 2 | 64k intro engine | Archived |
| Lekktor | Profiling and dead-code removal | Archived |

Notable: fr-08 (.the .product), .kkrieger (96KB FPS), fr-041 (debris) all built with Werkkzeug.

## Currently Active Demoscene Tools

| Tool | What | License | Status | URL |
|------|------|---------|--------|-----|
| **TiXL** (ex-Tooll3) | Node-based real-time motion gfx (Still/pixtur) | MIT | Very active (v4.0.6, 2025) | github.com/tixl3d/tixl |
| **GNU Rocket** | Sync-tracker (interpolated parameter curves) | MIT-ish | Active | github.com/rocket/rocket |
| **Bonzomatic** | Live shader coding (Shader Showdown tool) | OSS | Active | github.com/Gargaj/Bonzomatic |
| **Sointu** | 4k intro synth (fork of 4klang, Go, cross-platform) | MIT | Very active | github.com/vsariola/sointu |
| **WaveSabre** | 64k intro synth (Logicoma) | MIT | Active | github.com/logicomacorp/WaveSabre |
| **4klang** | 4k intro synth (Alcatraz) | OSS | Stable | github.com/gopher-atz/4klang |
| **Oidos** | Additive synthesis synth (Loonies/Blueberry) | OSS | Stable | github.com/askeksa/Oidos |
| **Crinkler** | Compressing linker for 1k/4k/8k intros | zlib | Active | github.com/runestubbe/Crinkler |
| **Squishy** | Exe packer for 64k (Logicoma) | Binary only | Active | logicoma.io/squishy |
| **Shader Minifier** | GLSL/HLSL minifier (Ctrl-Alt-Test) | OSS | Active | github.com/laurentlb/shader-minifier |
| **Furnace** | Multi-system chiptune tracker (supports AY!) | GPL-2.0 | Very active | github.com/tildearrow/furnace |

## Z80/Retro Relevance

Almost none of the PC demoscene tools are directly usable for Z80 work.
Two worlds: PC = procedural GPU + tiny executables; Z80 = hand-crafted assembly + cycle counting.

**Directly relevant for ZX Spectrum:**
- Furnace (AY-3-8910 support, modern alternative to Vortex Tracker)
- GNU Rocket (concept only — export sync data → convert to Z80 tables)

**Conceptually relevant (worth describing in book):**
- TiXL — shows where Werkkzeug's ideas evolved to
- Farbrausch's approach — procedural everything, same philosophy as size-coding
- Sointu/4klang — PC equivalent of what AY-beat does on Spectrum

## For Screenshots in Book

Recommended (with pseudo-screenshot placeholders for now):
1. GNU Rocket — sync tracks with interpolation (MIT, safe)
2. Blender VSE — timeline + audio waveform + markers (GPL, safe)
3. Blender Graph Editor — keyframe curves (GPL, safe)
4. Vortex Tracker II — frame counter (own fork VTI, safe)
5. TiXL — node graph (MIT, safe) — to show where Werkkzeug evolved

Unity/Unreal — mention as data generators, no screenshots (license concerns).
