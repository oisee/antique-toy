# Appendix J: Modern Tools for Retro Demo Production

> *"The best tool is the one that gets the data out of your head and into the Z80's memory in the fewest steps."*

---

## J.1 Two Worlds, One Philosophy

The PC demoscene and the Z80 demoscene look like different planets. On one planet, coders write fragment shaders in GLSL, generate meshes procedurally through node graphs, and compress everything into 64K executables that render real-time 3D at 60fps on consumer GPUs. On the other planet, coders hand-craft Z80 assembly routines that fit fourteen effects into 128K of banked RAM, counting T-states to ensure each frame renders in exactly 71,680 cycles.

The gap in hardware capability is enormous. The gap in philosophy is almost zero.

Both worlds worship constraint. A 64K PC intro is constrained by file size just as ruthlessly as a ZX Spectrum demo is constrained by CPU speed. A Shader Showdown competitor writing a raymarcher in 25 minutes faces the same creative pressure as a 256-byte coder optimising register reuse. Procedural generation --- building content from algorithms rather than storing it as data --- is the central technique on both platforms, because both platforms punish data and reward computation (the PC punishes stored data through file size limits; the Spectrum punishes it through memory limits).

This appendix surveys the modern demoscene toolchain: sync editors, data generators, music synthesisers, executable packers, and shader tools. Most of these tools target x86/GPU platforms and cannot run on a Z80 directly. But they serve three roles in ZX Spectrum production:

1. **Data generators** --- compute trajectories, particle positions, procedural textures on a PC, then export the results as compressed binary tables that the Z80 plays back.
2. **Sync planners** --- design the timing relationship between music and visuals in an interactive editor, then export frame numbers and parameter curves to Z80 `dw` tables.
3. **Prototyping environments** --- test visual algorithms at full speed on a modern GPU, then translate the working algorithm to Z80 assembly knowing exactly what the target output should look like.

The philosophy is consistent: **use any tool for preparation, but the Z80 runtime is handwritten assembly.** The demo's quality is judged by what runs on the Spectrum, not by what runs on the development PC. The tools are scaffolding; the building is Z80.

---

## J.2 Sync Tools

### The Sync Problem

Synchronisation --- making the right visual event happen at the right musical moment --- is the hardest part of demo production (Chapter 20). At the Z80 level, sync is always a data table: frame numbers paired with actions. The question is how to determine those frame numbers efficiently and iterate on them quickly.

Five tools address this problem, each with a different workflow.

### GNU Rocket

**What it is.** GNU Rocket is a sync-tracker --- a tracker-like editor where columns represent named parameters (`camera:x`, `fade:alpha`, `effect:id`) and rows represent time steps (typically frames or musical beats). You set keyframes at specific rows and choose an interpolation mode between them: **step** (instant change), **linear** (constant rate), **smooth** (cubic ease in/out), or **ramp** (exponential). The demo connects to the Rocket editor via TCP during development. You scrub the timeline, edit values, and see the demo update in real-time.

**Who uses it.** Rocket is the de facto standard sync tool across the PC and Amiga demoscenes. Logicoma, Noice, Loonies, Adapt, and dozens of other groups use it. It has been ported to C, C++, C#, Python, Rust, and JavaScript.

**Z80 workflow.** A Z80 Spectrum cannot run a TCP client, but the concept transfers directly:

1. Design sync tracks in Rocket on the PC, scrubbing with the music
2. Export keyframe data as binary (Rocket's native export)
3. Run a Python converter: quantise floats to 8-bit or 16-bit fixed-point, emit `db`/`dw` tables
4. `INCBIN` the tables into the demo

The Z80 code just reads a table --- no TCP, no floats, no complexity. You get Rocket's interactive editing experience during development, and the Spectrum's minimal runtime overhead in the final binary.

**Interpolation.** Rocket's four interpolation modes map cleanly to Z80 playback:
- **Step** → just use the value directly (0 cycles of interpolation overhead)
- **Linear** → precompute the per-frame delta, add it each frame (~20 T-states)
- **Smooth/Ramp** → bake the interpolated curve into the exported table (the Z80 reads precalculated values, no interpolation at runtime)

For most ZX Spectrum demos, baking all curves to per-frame values is the simplest approach. A 3,000-frame demo (one minute at 50fps) with 4 sync parameters consumes 12KB of uncompressed data --- significant, but compressible to 2--4KB with ZX0.

**Source:** `github.com/rocket/rocket` (MIT-like license)

<!-- figure: appj_gnu_rocket -->
```text
┌─────────────────────────────────────────────────────────────────────┐
│                    FIGURE: GNU Rocket sync editor                   │
│                                                                     │
│  Tracker-like grid with named columns:                              │
│  [camera:x]  [camera:y]  [fade:alpha]  [effect:id]                 │
│                                                                     │
│  Rows = frames/time steps. Keyframes shown as bright cells.         │
│  Between keyframes: interpolation curves (step/linear/smooth/ramp)  │
│  visualised as lines connecting values.                             │
│                                                                     │
│  Bottom: transport controls (play, pause, scrub).                   │
│  Connected to running demo via TCP — edit live.                     │
│                                                                     │
│  Screenshot needed: build GNU Rocket from source, create example    │
│  project with 4 tracks, capture at a point showing all 4            │
│  interpolation modes.                                               │
└─────────────────────────────────────────────────────────────────────┘
```

### Vortex Tracker II

**What it is.** Vortex Tracker II is the standard ProTracker 3 editor for the ZX Spectrum scene. The critical feature for sync work is the **frame counter** in the bottom-right corner of the window --- it shows the absolute interrupt count (frame number) at the current playback position.

**Sync workflow.** Play the .pt3 file. Watch the frame counter. When you hear a beat, accent, or phrase transition you want to sync to, note the frame number. Write it into your sync table. Rebuild the demo, test, adjust.

Kolnogorov (Vein) describes this as his primary method: "Vortex + video editor. In Vortex the frame is shown in the bottom-right corner --- I looked at which frames to hook onto, created a table with `dw frame, action` entries, and synced from that."

**The VTI fork.** The community maintains VTI, a fork of Vortex Tracker II with additional features including improved playback accuracy and expanded format support. For sync work, the original VT2 and VTI are equivalent --- the frame counter works the same way.

**Limitation.** Iterating is slow. Every timing change requires rebuilding the demo and watching it from the beginning. For simple demos with a dozen sync points, this is fine. For complex demos with hundreds of events, a more interactive tool (Rocket, Blender) is worth the setup cost.

<!-- figure: appj_vortex_tracker -->
```text
┌─────────────────────────────────────────────────────────────────────┐
│              FIGURE: Vortex Tracker II — frame counter              │
│                                                                     │
│  VT2 main window with pattern editor visible.                       │
│  Bottom-right: position display showing pattern:row and             │
│  absolute frame number.                                             │
│  Highlight/circle the frame counter.                                │
│                                                                     │
│  Caption: "The frame number in VT2's status bar maps directly to    │
│  the PT3 player's interrupt counter on the Spectrum. What you see   │
│  here is what your sync table references."                          │
│                                                                     │
│  Screenshot needed: open any .pt3 in VTI fork, play to a           │
│  mid-song position, capture with frame number visible.              │
└─────────────────────────────────────────────────────────────────────┘
```

### Blender VSE (Video Sequence Editor)

**What it is.** Blender's built-in non-linear video editor. For demo sync, it provides a timeline where you can lay colour-coded strips (one per effect), import the music track as an audio strip with a visible waveform, and place markers at sync points.

**Sync workflow:**
1. Capture each effect running in the emulator as a short video clip (or use solid-colour placeholder strips)
2. Import the clips and the music (.wav) into the VSE
3. Arrange clips on the timeline, scrub to find the perfect cut points
4. Place markers (green diamonds) at each sync event
5. Read off the frame numbers from the marker positions

The visual workflow is powerful: you *see* the audio waveform, you *see* where the beat hits, and you drag the marker to the right spot. No calculations, no BPM-to-frame conversions.

**Export.** Markers can be exported via Blender's Python console:

```python
for m in bpy.context.scene.timeline_markers:
    print(f"dw {m.frame}, 0  ; {m.name}")
```

This outputs a Z80-ready sync table directly. Rename markers to match your effect IDs (`plasma`, `flash`, `scroll`) and the export becomes a complete scene table.

**DaVinci Resolve** provides similar capabilities (timeline + markers + EDL/CSV export) and its free version is sufficient. Choose whichever you already know.

<!-- figure: appj_blender_vse -->
```text
┌─────────────────────────────────────────────────────────────────────┐
│                 FIGURE: Blender VSE — demo storyboard               │
│                                                                     │
│  Timeline with 4-5 colour-coded strips (one per effect):            │
│  [TORUS: blue] [PLASMA: green] [DOTSCROLL: yellow] [ROTOZOOM: red]  │
│                                                                     │
│  Below: audio waveform strip (music.wav)                            │
│  Vertical markers (green diamonds) at sync points.                  │
│  Playhead at a transition point between effects.                    │
│                                                                     │
│  Screenshot needed: create Blender project with dummy strips +      │
│  real AY music exported as WAV. Place ~8 markers at beat hits.      │
└─────────────────────────────────────────────────────────────────────┘
```

### Blender Graph Editor

**What it is.** Blender's curve editor for keyframed properties. For demo work, you create custom properties on an object (e.g., `scroll_speed`, `fade_alpha`, `camera_z`) and keyframe them to match the music's energy and phrasing.

**Why it matters.** The Graph Editor gives you visual, interactive control over how parameters change over time --- the same thing GNU Rocket provides, but integrated into Blender's ecosystem. You can see multiple curves simultaneously, adjust keyframe timing by dragging, and switch interpolation modes (constant, linear, Bezier) per keyframe.

**Export via Python API:**

```python
for fcurve in bpy.data.actions['SyncAction'].fcurves:
    name = fcurve.data_path.split('"')[1]
    print(f"; {name}")
    for kf in fcurve.keyframe_points:
        print(f"    dw {int(kf.co.x)}, {int(kf.co.y)}")
```

This outputs Z80-ready sync data directly. The Blender project becomes your storyboard, your sync reference, and your data pipeline in one file.

<!-- figure: appj_blender_graph -->
```text
┌─────────────────────────────────────────────────────────────────────┐
│              FIGURE: Blender Graph Editor — keyframe export         │
│                                                                     │
│  Graph with X = frame number, Y = parameter value.                  │
│  3 curves: scroll_speed (smooth ease-in), fade_alpha (step at       │
│  transitions), camera_z (linear ramp).                              │
│                                                                     │
│  Annotation showing the Python export:                              │
│  for kf in fcurve.keyframe_points:                                  │
│      print(f"dw {int(kf.co.x)}, {int(kf.co.y)}")                   │
│                                                                     │
│  Arrow pointing to resulting Z80 data:                              │
│  dw 0, 0  /  dw 50, 128  /  dw 150, 255  /  ...                    │
│                                                                     │
│  Screenshot needed: same Blender project, switch to Graph Editor    │
│  view with 3 animated custom properties.                            │
└─────────────────────────────────────────────────────────────────────┘
```

### Motion Canvas

A brief mention: **Motion Canvas** is an emerging MIT-licensed, TypeScript-based tool for creating parametric animations programmatically. It is designed for explanatory videos but its timeline-as-code approach could serve as a sync planning tool for coders who prefer writing code to dragging keyframes. Still early in development; watch the project at `motioncanvas.io`.

### Comparison Table

| Tool | License | Sync method | Z80 export path | Interactive? |
|------|---------|-------------|-----------------|--------------|
| GNU Rocket | MIT-like | Keyframed tracks + interpolation | Binary → Python → `dw` tables | Yes (TCP live editing) |
| Vortex Tracker II | Freeware | Frame counter readout | Manual (note frame numbers) | Partial (listen + note) |
| Blender VSE | GPL | Timeline markers + waveform | Python → `dw` tables | Yes (visual scrubbing) |
| Blender Graph Editor | GPL | Keyframed curves | Python API → `dw` tables | Yes (visual curve editing) |
| DaVinci Resolve | Free/Commercial | Timeline markers | EDL/CSV → Python → `dw` tables | Yes (visual scrubbing) |
| Motion Canvas | MIT | Code-defined timeline | TypeScript export (custom) | Programmatic |

---

## J.3 Pre-visualisation and Storyboarding

Before writing a single line of Z80 assembly, you need to know what the demo looks like. Not in detail --- not every palette choice or scroll speed --- but the overall structure: which effects, in what order, for how long, transitioning how. This is pre-visualisation, and it saves more time than any code optimisation.

### Blender as Storyboard Tool

Blender's **Grease Pencil** (now fully integrated as a 2D drawing system) lets you sketch rough representations of each effect --- coloured rectangles, simple shapes, hand-drawn approximations. These do not need to look like the final effects. They need to communicate: "here, for this many seconds, something blue and swirly happens."

A practical approach:
1. Create one Grease Pencil object per effect (coloured rectangle with the effect's name)
2. Arrange them on the VSE timeline with the music track
3. Play back and watch the structure

You are not making an animatic. You are making a *schedule* --- a visual representation of which effect runs when, and how long it runs for. The colours help you spot structural problems: three slow blue effects in a row means the pacing is off. A 45-second stretch with no transition means the audience gets bored.

### Video Editors for Rough-cut Assembly

Once you have effects running in an emulator, capture them as video clips (OBS Studio, screen recorder, or emulator recording features). Import the clips into a video editor --- DaVinci Resolve, Blender VSE, or even iMovie --- and arrange them on a timeline with the music.

This rough cut reveals problems that are invisible in code:
- An effect that looks impressive in isolation but runs too long in context
- A transition that should happen on the beat but lands between beats
- Two consecutive effects with similar colour palettes that blur together
- A section where the visual energy drops while the music builds

The rough cut costs an hour of work. It saves days of assembly-level timing adjustments.

### The GABBA Workflow

diver4d's approach for GABBA (2019) took this further: he used **Luma Fusion**, an iOS video editor, as his primary sync planning tool. The workflow was:

1. Code each effect individually, test in emulator
2. Screen-record each effect running
3. Import recordings + music into Luma Fusion on an iPad
4. Arrange on the timeline, scrub frame-by-frame to find sync points
5. Note the frame numbers, write sync table

The key insight: frame-level synchronisation is a *video editing* problem, not a *programming* problem. By solving it in a tool designed for video editing, diver4d could iterate on timing in seconds instead of minutes. The Z80 code was the implementation layer; the creative decisions happened in the video editor.

### Kolnogorov on Sync Planning

Kolnogorov (Vein) articulates the combined approach: "I exported effect clips to video, assembled them in a video editor, attached the music track, and looked at what order the effects work best in, noting the frames where events should happen."

The important word is *looked*. This is a visual, intuitive process. You *see* where the beat hits the waveform. You *see* where the effect transition feels right. And you read the frame number. No calculations, no BPM-to-frame conversions.

---

## J.4 Data Generation Engines

A ZX Spectrum demo plays back precomputed data at 50fps. The question is: where do you compute that data? For simple sine tables and Bresenham coordinates, a Python script suffices. For complex 3D trajectories, organic particle motion, or VR-captured gestures, you need a more powerful environment.

### Unity as a Data Generator

Unity is not overkill for ZX Spectrum demos --- it is overkill as a *demo engine*, but perfect as a *data generator*. The distinction matters.

**VR motion capture.** Unity's XR Toolkit captures VR controller position at 90Hz. Draw a trajectory in the air with a VR controller --- the organic movement you get from a hand gesture is impossible to replicate with mathematical formulas. Downsample to 50fps, quantise to 8-bit signed values, delta-encode, compress. A 5-second hand-drawn trajectory becomes 250 bytes of packed data that *feels alive* on the Spectrum.

**GPU particle systems.** Unity's VFX Graph runs millions of particles on the GPU. Prototype a particle fountain, a vortex, or a flocking simulation, then export the particle positions per frame as CSV. On the Spectrum, you plot those positions as dots or attribute cells. The physics simulation that would take months to implement in Z80 runs in milliseconds on a GPU.

**Shader prototyping.** Write a plasma, tunnel, or rotozoomer as a fragment shader in Unity's ShaderGraph. Iterate in real-time at full resolution until it looks right. Then translate the algorithm to Z80, knowing exactly what the target visual should be.

### Unreal Engine as a Data Generator

Unreal offers equivalent capabilities through different tools:
- **OpenXR** for VR motion capture
- **Niagara** for GPU particle systems
- **Material Editor** for shader prototyping

The choice between Unity and Unreal for data generation is a matter of familiarity. Both export to the same formats (CSV, binary arrays). Both provide more computational power than you will ever need for generating Z80 demo data.

### Blender as a Data Generator

For most data generation tasks, Blender is sufficient and fully open-source:

- **Geometry Nodes** for procedural trajectories --- define a path as a spline, scatter points along it, animate with noise, export vertex positions per frame
- **Grease Pencil** for hand-drawn animation --- draw frames, export point coordinates
- **Python API** for direct export --- access any animated property from `bpy.data`
- **Physics simulation** for particles, cloth, fluid --- simulate, bake, export per-frame data

Blender cannot do VR motion capture (without third-party addons) and its particle system is CPU-bound (slower than GPU-based systems for millions of particles). For everything else, it matches or exceeds Unity/Unreal for data generation purposes.

### The Export Pipeline

Regardless of which tool generates the data, the pipeline to Z80 follows the same stages:

```text
Source tool (Unity/Unreal/Blender)
  → Export: float arrays (CSV, JSON, or binary)
    → Python: float → 8-bit fixed-point (or 16-bit where needed)
      → Delta-encode: store differences between frames (smaller values)
        → Transpose: column-major layout (all X values, then all Y values)
          → packbench analyze: verify entropy, check suggested transforms
            → zx0/pletter: compress
              → sjasmplus: INCBIN into demo
```

Each stage reduces the data size:

| Stage | Example size (250 frames × 4 params) |
|-------|--------------------------------------|
| Float CSV | ~10 KB |
| 8-bit fixed-point | 1,000 bytes |
| Delta-encoded | 1,000 bytes (values shrink, better compression ratio) |
| Transposed + compressed | 300–500 bytes |

The delta-encoding and transposition stages do not reduce raw size --- they reshape the data to compress better. Column-major layout groups similar values together (all X deltas, then all Y deltas), which compresses dramatically better than row-major layout where X and Y deltas alternate.

### When to Use Which

| Need | Tool | Why |
|------|------|-----|
| Sine tables, lookup tables | Python script | Simplest, no dependencies |
| Procedural 3D trajectories | Blender (Geometry Nodes) | Free, visual, Python export |
| Hand-drawn animation paths | Blender (Grease Pencil) | Draw directly, frame-by-frame |
| VR gesture capture | Unity (XR Toolkit) or Unreal (OpenXR) | Need VR hardware + runtime |
| GPU particle positions | Unity (VFX Graph) or Unreal (Niagara) | Millions of particles, fast |
| Shader algorithm prototype | Any (ShaderToy, Unity, Unreal, Blender) | Whichever you know |

Kolnogorov's precalculated vector animations are a case in point: the 3D geometry was computed offline (minutes of calculation are acceptable for a 4K intro), the resulting vertex trajectories were stored as compressed tables, and the Spectrum played them back at 50fps. The tool that generated the trajectories is irrelevant to the audience. What matters is that the data exists and the Z80 plays it.

---

## J.5 The PC Demoscene Toolchain: A Brief History

The PC demoscene has spent twenty-five years building tools for procedural content generation and extreme compression. These tools cannot run on a Z80, but their design philosophy --- procedural everything, small is beautiful, constraint as creativity --- mirrors exactly what ZX Spectrum coders do by hand. Understanding the PC toolchain helps you recognise which problems have been solved (in different contexts) and which ideas you can adapt.

### Farbrausch (1999--2012)

**Farbrausch** was a German demogroup that redefined what was possible in 64K and 4K executables. Their approach: build tools that generate everything procedurally, then pack the generators into tiny executables.

**Werkkzeug** (versions 1 through 4) was their flagship tool --- a node-based procedural system where textures, meshes, animations, and compositions were defined as operator graphs. No bitmaps were stored; every pixel was computed at runtime from a recipe of mathematical operations. The tool was used internally by Farbrausch; the audience saw only the resulting executables.

Notable productions built with Werkkzeug:
- **fr-08: .the .product** (2000) --- a real-time 3D music video in 64KB that redefined the 64K intro category. Won the demo compo at The Party 2000.
- **.kkrieger** (2004) --- a first-person shooter in 97,280 bytes. Textures, meshes, animations, AI, and sound, all procedurally generated. The executable is smaller than this appendix's source file.
- **fr-041: debris.** (2007) --- a cinematic 177KB demo that pushed real-time rendering quality beyond what many full-size demos achieved. Won at Breakpoint 2007.

**kkrunchy** was their executable packer for 64K intros --- a context-mixing compressor that achieved compression ratios far beyond standard packers like UPX. kkrunchy is still actively used by 64K intro coders today, more than a decade after Farbrausch disbanded.

**V2 Synthesizer** was a software synthesizer designed for intros --- a VSTi plugin for composing, with a tiny runtime player that fit inside the packed executable. Music was stored as note data and synthesis parameters, not as audio.

In 2012, Farbrausch open-sourced their entire toolchain under a BSD-style license: `github.com/farbrausch/fr_public`. The repository includes Werkkzeug (all versions), kkrunchy, V2, and several other tools. The code is a time capsule of early-2000s demoscene engineering: dense C++, Win32 APIs, Direct3D 9, and creative solutions to problems that modern GPUs solve with brute force.

**Relevance to Z80.** The ZX Spectrum equivalent of Werkkzeug's procedural textures is your Python build script that generates lookup tables from mathematical functions. The equivalent of kkrunchy is ZX0 or Pletter. The equivalent of V2 is AY-beat or Shiru's AY player. Different scale, same principle: generate content from compact descriptions, compress the result, decompress at runtime.

### TiXL (2024--present)

**TiXL** (formerly Tooll3) is the spiritual successor to Werkkzeug, developed by **Still** (pixtur/Thomas Mann) --- a demoscener who has worked with Farbrausch members and carried the node-based procedural approach forward.

TiXL is a real-time motion graphics environment built on modern GPU APIs. Like Werkkzeug, it uses a node graph to define procedural content, but with 20 years of GPU evolution behind it: compute shaders, physically-based rendering, GPU particles, and real-time raymarching.

Licensed under MIT (`github.com/tixl3d/tixl`), TiXL shows where the Werkkzeug philosophy has evolved. The node graph concept --- defining content as a recipe of operations rather than storing it as data --- is directly applicable to Z80 demo development, even though the specific operations are entirely different.

<!-- figure: appj_tixl_nodes -->
```text
┌─────────────────────────────────────────────────────────────────────┐
│                    FIGURE: TiXL node graph                          │
│                                                                     │
│  Visual programming canvas with connected nodes:                    │
│  [Time] → [Sine] → [Multiply] → [SetFloat]                        │
│                                                                     │
│  A procedural texture pipeline:                                     │
│  [Noise3D] → [Remap] → [ColorGrade] → [RenderTarget]              │
│                                                                     │
│  3D scene graph:                                                    │
│  [Mesh:Torus] → [Transform] → [Material] → [DrawMesh]             │
│  [Camera] → [Render] → [PostFX:Bloom] → [Output]                  │
│                                                                     │
│  Right panel: live preview of the rendered output.                  │
│  Bottom: timeline with playback controls.                           │
│                                                                     │
│  Caption: "TiXL (MIT, 2024) carries forward the Werkkzeug           │
│  philosophy of node-based procedural content generation. The         │
│  Z80 equivalent is a Python build script that generates lookup       │
│  tables and compressed data from mathematical functions."            │
│                                                                     │
│  Screenshot needed: install TiXL, open an example project,          │
│  capture the node graph + preview in a split view.                  │
└─────────────────────────────────────────────────────────────────────┘
```

### Bonzomatic

**Bonzomatic** (by Gargaj / Conspiracy) is the standard tool for **Shader Showdown** competitions --- live shader coding battles at demoscene parties. Two coders share a stage, each writing a fragment shader from scratch in 25 minutes, with the code and output projected side-by-side for the audience.

Bonzomatic provides a minimal editor with a live preview window. Every keystroke recompiles the shader; the output updates in real-time. There is no save, no undo history beyond the editor buffer, and no libraries. It is pure constraint-driven creativity --- the same spirit as 256-byte coding on the Spectrum.

**Source:** `github.com/Gargaj/Bonzomatic`

### Crinkler

**Crinkler** (by Rune Stubbe and Aske Simon Christensen / Loonies) is a **compressing linker** for Windows executables. Where a normal linker produces an .exe and you compress it separately, Crinkler combines linking and compression into one step, achieving compression ratios that no separate packer can match.

Crinkler is the standard for 1K, 4K, and 8K PC intros. Its compression is so effective that coders routinely measure their work in "Crinkler bytes" --- the final packed size, which may be 60--70% of the uncompressed code + data.

The Z80 parallel: ZX0 and Pletter serve the same role for Spectrum demos, though compression ratios are more modest (Z80 code has less redundancy than x86).

**Source:** `github.com/runestubbe/Crinkler` (zlib license)

### Squishy

**Squishy** (by Logicoma) is a 64K executable packer --- the equivalent of kkrunchy for modern 64K intros. Unlike Crinkler (which handles tiny intros), Squishy targets the 64KB size class where the executable contains substantial shader code, texture generation routines, and music.

Binary-only distribution; no source available. Mentioned here because Logicoma's 64K intros (Happy Coding, Elysian, H - Immersion) represent the current state of the art in the 64K category, and Squishy is part of that pipeline.

### Shader Minifier

**Shader Minifier** (by Ctrl-Alt-Test) is a GLSL/HLSL minifier that renames variables, removes whitespace, and optimises shader code for minimum size. Used in size-coded intros where every byte of shader source counts (shaders are often stored as strings in the executable and compiled at runtime).

**Source:** `github.com/laurentlb/shader-minifier`

### z80-optimizer

**z80-optimizer** (by oisee, 2025) is a brute-force Z80 superoptimiser written in Go. It enumerates every pair of Z80 instructions (406 × 406 opcodes), tests each pair against all possible register and flag states, and reports when a shorter or faster replacement produces identical output. No heuristics, no machine learning — pure exhaustive search with full state equivalence verification.

A single run on an Apple M2 (3h 16m, 34.7 billion comparisons) produces **602,008 provably correct optimisation rules** across **83 unique transformation patterns**. Examples: `SLA A : RR A` → `OR A` (saves 3 bytes, 12T); `LD A, 0 : NEG` → `SUB A` (saves 2 bytes); `SCF : RR A` → `SCF : RRA` (saves 1 byte, 4T). Crucially, it correctly *rejects* `LD A, 0` → `XOR A` because the flag behaviour differs — the kind of subtle distinction that hand-maintained peephole tables sometimes get wrong.

Useful as a post-processing pass for compiler-generated Z80 code, or as a reference for hand-optimisation. The output is a machine-readable rule database that can be integrated into assembler toolchains. See Chapter 23 for discussion of brute-force vs neural-network approaches to Z80 optimisation.

**Source:** `github.com/oisee/z80-optimizer` (MIT license, v0.1.0)

### The Common Philosophy

All these tools share a principle that translates directly to Z80 work: **procedural generation beats stored data.** On the PC, this means generating textures from noise functions instead of storing bitmaps. On the Spectrum, it means computing a sine table from a parabolic approximation instead of storing 256 bytes of precomputed values. The hardware differs by a factor of a million; the approach is the same.

---

## J.6 Music and Sound Tools

The PC demoscene needs tiny synthesisers --- software instruments that fit inside a 4K or 64K executable while producing music that sounds professional. The Z80 scene needs AY-3-8910 trackers. There is some overlap.

### Sointu

**Sointu** is a 4K intro synthesiser --- a fork of 4klang rewritten in Go for cross-platform support. It provides a VST-like interface for designing patches (oscillators, filters, envelopes, effects) and a compiler that generates a minimal native player.

The player code is designed for extreme size: the entire synth runtime, including all instrument definitions and note data, fits in under 4KB of x86 code + data. This makes it the PC equivalent of what AY-beat (Chapter 13) achieves on the Spectrum: maximum sound from minimum bytes.

**Source:** `github.com/vsariola/sointu` (MIT license)

### 4klang

**4klang** (by Alcatraz) is the original 4K intro synth that Sointu forked from. It provides a VSTi plugin for composing and an assembler output mode that generates NASM source code for the player --- the synthesiser is literally written in x86 assembly, optimised for size.

4klang defined the standard for 4K intro music and remains in active use alongside its successor Sointu.

**Source:** `github.com/gopher-atz/4klang`

### WaveSabre

**WaveSabre** (by Logicoma) targets 64K intros --- a larger size class where the synth can be more sophisticated. It provides VST-compatible instruments with reverb, delay, chorus, distortion, and other effects that 4K synths must omit. The runtime player is compact enough for 64K but too large for 4K.

WaveSabre powers the music in Logicoma's award-winning 64K intros (Happy Coding, Elysian).

**Source:** `github.com/logicomacorp/WaveSabre` (MIT license)

### Oidos

**Oidos** (by Blueberry / Loonies) takes a fundamentally different approach: additive synthesis. Where most synths build sounds from oscillators and filters, Oidos builds them from sums of sine waves with individually controlled frequencies and amplitudes. The result is a distinctive, rich sound that occupies a unique sonic space in 4K intros.

**Source:** `github.com/askeksa/Oidos`

### Furnace

**Furnace** is a multi-system chiptune tracker that supports over 80 sound chips --- including the **AY-3-8910**. This makes it directly relevant to ZX Spectrum demo production: you can compose AY music in Furnace using a modern interface with features that Vortex Tracker II lacks (undo, multiple tabs, visual envelope editor, per-channel oscilloscope).

Additional chips supported include the SN76489 (Sega Master System, BBC Micro), YM2612 (Mega Drive), SID (C64), Pokey (Atari), and many others. If you are working on multi-platform retro projects, Furnace is the one tracker that covers all targets.

**Export formats.** Furnace can export to VGM (Video Game Music) format, which captures raw register writes per frame. For the AY-3-8910, this means you get a stream of 14-byte register dumps at 50/60Hz --- directly usable on the Spectrum with a minimal player that writes registers each interrupt. Custom export scripts can convert VGM to PT3 or to raw register tables for INCBIN.

**Limitation.** Furnace's AY emulation is good but not identical to Vortex Tracker's PT3 playback. If your demo uses a PT3 player, compose in Vortex Tracker for guaranteed 1:1 playback. Use Furnace when you want a modern editing experience and are willing to handle format conversion, or when targeting the AY directly with raw register writes.

**Source:** `github.com/tildearrow/furnace` (GPL-2.0)

### Comparison Table

| Tool | Size class | License | Z80 relevance |
|------|-----------|---------|---------------|
| Sointu | 4K intros | MIT | Conceptual (same constraint as AY-beat) |
| 4klang | 4K intros | OSS | Conceptual |
| WaveSabre | 64K intros | MIT | Conceptual |
| Oidos | 4K intros | OSS | Conceptual |
| Furnace | Any | GPL-2.0 | **Direct** --- AY-3-8910 support, VGM export |
| Vortex Tracker II | Any | Freeware | **Direct** --- PT3 native, ZX standard |

---

## J.7 Practical Recipes

Five step-by-step workflows that bridge modern tools to Z80 assembly. Each recipe starts from a blank project and ends with data you can `INCBIN` into a demo.

### Recipe 1: GNU Rocket → Z80 Sync Table

**Goal:** Design interpolated sync curves in Rocket, export as Z80 `dw` tables.

**Steps:**

1. **Install Rocket.** Clone `github.com/rocket/rocket`, build from source (CMake). Run the editor.

2. **Create tracks.** Add four tracks: `effect:id`, `fade:alpha`, `scroll:speed`, `flash:border`. Set the BPM to match your music (e.g., 125 BPM at 50fps = 24 frames per beat).

3. **Set keyframes.** At row 0: `effect:id` = 0 (logo), `fade:alpha` = 255. At row 150: `effect:id` = 1 (plasma), `fade:alpha` ramp from 255 to 0 (smooth interpolation). Continue for the full demo length.

4. **Export.** Use Rocket's sync exporter (or the `sync_export` tool) to write binary files per track.

5. **Convert with Python:**

```python
import struct

def rocket_to_z80(track_file, output_file):
    with open(track_file, 'rb') as f:
        data = f.read()
    # Rocket binary: array of (row: u32, value: float32) pairs
    pairs = []
    for i in range(0, len(data), 8):
        row, val = struct.unpack('<If', data[i:i+8])
        pairs.append((row, max(0, min(255, int(val)))))

    with open(output_file, 'w') as f:
        for row, val in pairs:
            f.write(f"    dw {row}, {val}\n")
        f.write("    dw 0  ; end marker\n")

rocket_to_z80('effect_id.track', 'sync_effect.inc')
```

6. **Include in demo:**

```z80
sync_effect:
    INCLUDE "sync_effect.inc"
```

**Baking option.** For smooth interpolation without runtime cost, expand the keyframes to per-frame values:

```python
# Interpolate between keyframes, output one value per frame
for frame in range(total_frames):
    value = interpolate(keyframes, frame)  # linear, smooth, or ramp
    print(f"    db {max(0, min(255, int(value)))}")
```

A 3,000-frame track baked to per-frame `db` values = 3,000 bytes uncompressed, ~800 bytes after ZX0.

### Recipe 2: Blender VSE → Frame Number Table

**Goal:** Plan demo structure visually with music, export sync points.

**Steps:**

1. **Create Blender project.** Set frame rate to 50fps (Properties → Output → Frame Rate → 50). Set the timeline length to match your music.

2. **Import music.** Add → Sound in the VSE. Import your .pt3 exported as .wav (use Vortex Tracker's "File → Export to WAV"). The waveform appears on the timeline.

3. **Add effect strips.** Add → Color strips for each effect. Name them (plasma, scroll, torus). Colour-code them. Arrange on the timeline so they cover the full demo duration.

4. **Place markers.** Scrub the timeline. When you hear a beat or transition point, press M to add a marker. Rename each marker: `plasma_start`, `flash_1`, `scroll_begin`, etc.

5. **Export via Python console:**

```python
import bpy

# Print sync table
print("; Auto-generated sync table from Blender VSE")
print("sync_table:")
for m in sorted(bpy.context.scene.timeline_markers,
                key=lambda x: x.frame):
    print(f"    dw {m.frame}  ; {m.name}")
print("    dw 0  ; end marker")
```

6. **Copy output to your project's .inc file.** Rebuild the demo with `make`.

7. **Iterate.** Watch the demo, note where timing feels wrong, return to Blender, adjust markers, re-export. Each iteration takes seconds.

### Recipe 3: Unity VR → Trajectory Data

**Goal:** Capture a hand-drawn 3D trajectory using a VR controller, export as compressed Z80 data.

**Steps:**

1. **Set up Unity project.** Create new 3D project, install XR Toolkit via Package Manager. Configure for your headset (Quest, Index, etc.).

2. **Record controller path.** Create a script that captures `transform.position` of the right controller every frame:

```csharp
void Update() {
    positions.Add(new Vector3(
        controller.transform.position.x,
        controller.transform.position.y,
        controller.transform.position.z
    ));
}
```

3. **Export CSV.** On recording end, write positions to CSV:

```csharp
File.WriteAllLines("trajectory.csv",
    positions.Select(p => $"{p.x},{p.y},{p.z}"));
```

4. **Convert with Python:**

```python
import csv

with open('trajectory.csv') as f:
    rows = list(csv.reader(f))

# Downsample from 90Hz to 50Hz
factor = 90 / 50
resampled = [rows[int(i * factor)] for i in range(int(len(rows) / factor))]

# Quantise to signed 8-bit (-128..127)
def q8(val, scale=64.0):
    return max(-128, min(127, int(float(val) * scale)))

# Delta-encode
prev = [0, 0, 0]
deltas = []
for row in resampled:
    cur = [q8(row[0]), q8(row[1]), q8(row[2])]
    deltas.append([c - p for c, p in zip(cur, prev)])
    prev = cur

# Transpose (column-major) and output
print("; X deltas")
print("traj_dx:")
print("    db " + ", ".join(str(d[0] & 0xFF) for d in deltas))
print("; Y deltas")
print("traj_dy:")
print("    db " + ", ".join(str(d[1] & 0xFF) for d in deltas))
print("; Z deltas")
print("traj_dz:")
print("    db " + ", ".join(str(d[2] & 0xFF) for d in deltas))
```

5. **Compress.** Run each column through ZX0 separately (column-major layout compresses much better than interleaved). `INCBIN` the compressed blobs.

6. **Playback on Z80.** Decompress each column to a buffer. Each frame, read the next delta and add to the current position. Plot the resulting (X, Y) on screen (project Z for depth if needed).

### Recipe 4: Furnace → AY Music

**Goal:** Compose AY-3-8910 music in Furnace and export for ZX Spectrum playback.

**Steps:**

1. **Configure Furnace.** Create new project. Add an AY-3-8910 system (Settings → select "AY-3-8910" from the chip list). Set clock to 1.7734 MHz (ZX Spectrum standard). Set refresh rate to 50Hz (PAL).

2. **Compose.** Use Furnace's pattern editor --- similar to Vortex Tracker but with undo, per-channel oscilloscope, and visual envelope editing. Furnace supports AY hardware envelopes, noise mixing, and all standard AY features.

3. **Export as VGM.** File → Export → VGM. This produces a .vgm file containing raw AY register writes per frame --- a stream of `(register, value)` pairs at 50Hz.

4. **Convert VGM to register dump:**

```python
import struct

def vgm_to_ay_regs(vgm_file):
    with open(vgm_file, 'rb') as f:
        data = f.read()

    # Skip VGM header (find data offset at 0x34)
    data_offset = struct.unpack_from('<I', data, 0x34)[0] + 0x34

    frames = []
    current_regs = [0] * 14
    pos = data_offset

    while pos < len(data):
        cmd = data[pos]
        if cmd == 0xA0:  # AY-3-8910 register write
            reg = data[pos + 1]
            val = data[pos + 2]
            if reg < 14:
                current_regs[reg] = val
            pos += 3
        elif cmd == 0x62:  # Wait 1/50s
            frames.append(list(current_regs))
            pos += 1
        elif cmd == 0x66:  # End of data
            break
        else:
            pos += 1

    return frames

frames = vgm_to_ay_regs('music.vgm')

# Output as Z80 include
print(f"music_frames: equ {len(frames)}")
print("music_data:")
for regs in frames:
    print("    db " + ", ".join(f"${r:02X}" for r in regs))
```

5. **Z80 player.** The simplest possible player --- 14 OUT instructions per interrupt:

```z80
play_frame:
    ld hl, (music_ptr)
    ld b, 14
    xor a
.loop:
    out ($FD), a        ; select register
    ld c, (hl)
    inc hl
    push af
    ld a, c
    out ($BF), a        ; write value
    pop af
    inc a
    djnz .loop
    ld (music_ptr), hl
    ret
```

6. **Alternative: PT3 conversion.** If you prefer using a standard PT3 player (smaller, better compression), use the `vgm2pt3` tool or compose directly in Vortex Tracker. Furnace's advantage is the modern interface; Vortex Tracker's advantage is guaranteed PT3 compatibility.

### Recipe 5: packbench → Pre-compression Analysis

**Goal:** Analyse raw demo data before compression to identify optimal transforms.

**Steps:**

1. **Assemble without compression.** Build your demo with raw (uncompressed) INCBIN data.

2. **Run packbench analyse** on each data file:

```bash
packbench analyze sprites.bin
```

3. **Read the report.** packbench reports:
   - **Entropy** (bits per byte) --- theoretical minimum compressed size
   - **Byte distribution** --- shows if values cluster (good) or spread uniformly (bad for compression)
   - **Run lengths** --- shows repetition patterns
   - **Suggested transforms** --- delta encoding, bit-plane separation, transpose, etc.

4. **Apply suggested transforms.** If packbench suggests delta encoding:

```python
data = open('sprites.bin', 'rb').read()
deltas = bytes([((data[i] - data[i-1]) & 0xFF) for i in range(1, len(data))])
open('sprites_delta.bin', 'wb').write(bytes([data[0]]) + deltas)
```

5. **Re-analyse.** Run packbench on the transformed data. Entropy should be lower.

6. **Compress.** Run ZX0 or Pletter on the transformed data. Compare compressed size against the original --- the transform should yield a smaller result.

7. **Update demo.** The Z80 decompressor runs first (ZX0 decode), then the inverse transform (un-delta) reconstructs the original data. The inverse transform is cheap: ~10 T-states per byte for delta decoding.

---

## Further Reading

- **GNU Rocket:** `github.com/rocket/rocket` --- sync editor + client libraries
- **TiXL:** `github.com/tixl3d/tixl` --- node-based motion graphics (MIT)
- **Farbrausch archive:** `github.com/farbrausch/fr_public` --- Werkkzeug, kkrunchy, V2 (BSD)
- **Furnace:** `github.com/tildearrow/furnace` --- multi-system chiptune tracker (GPL-2.0)
- **Sointu:** `github.com/vsariola/sointu` --- 4K intro synth (MIT)
- **WaveSabre:** `github.com/logicomacorp/WaveSabre` --- 64K intro synth (MIT)
- **Crinkler:** `github.com/runestubbe/Crinkler` --- compressing linker (zlib)
- **Bonzomatic:** `github.com/Gargaj/Bonzomatic` --- live shader coding
- **Shader Minifier:** `github.com/laurentlb/shader-minifier` --- GLSL/HLSL optimizer
- **z80-optimizer:** `github.com/oisee/z80-optimizer` --- brute-force Z80 superoptimiser (MIT)
- **Motion Canvas:** `motioncanvas.io` --- parametric animation (MIT)
- **Blender:** `blender.org` --- 3D, VSE, Graph Editor, Geometry Nodes, Grease Pencil (GPL)
