# Clockwork — ZX Spectrum Demoscene Sync Editor

## Project Specification v0.1

### 1. What Is This?

**Clockwork** — web-based timeline/sync editor for ZX Spectrum demoscene productions. Connects music (AY-3-8910, PT3/PSG) to visual effects with frame-accurate synchronization.

**Core idea**: GNU Rocket, but aware of chiptune music structure (patterns, notes, drums, envelopes) — not just a beat grid.

### 2. Where Does It Live?

**Separate repository** (`clockwork` or `zx-sync`), referenced from the book project.

**Rationale:**

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| Chapter tool (ch12) | Close to content | Too complex for a chapter, couples lifecycles | No |
| Appendix | Self-contained reference | Still tied to book releases | No |
| Subdirectory in antique-toy | Easy access | Pollutes book repo, wrong audience | No |
| **Separate repo** | Own lifecycle, community tool, reusable by any demo | Need to coordinate | **Yes** |

The book's ch12 teaches sync *concepts*. Clockwork is the *practical tool* — it has value beyond the book. Other demosceners (not just readers) should be able to use it. The "Antique Toy" demo uses it as first customer.

**Integration with book repo**: git submodule or just a link in README/ch12. The demo engine (`demo/src/engine.a80`) already has timeline + ring buffer architecture ready for Clockwork's exported sync data.

### 3. Problem Statement

Current ZX Spectrum demo sync workflow:

1. **Hand-code** frame numbers in assembly scene table → tedious, error-prone
2. **Video editor** (GABBA/diver4d approach: Luma Fusion) → visual but disconnected from code
3. **Guess and recompile** → most common, most painful

There is **no dedicated sync tool** for ZX Spectrum / retro platforms. GNU Rocket exists for PC demoscene but:
- Doesn't understand chiptune music structure (patterns, instruments, drums)
- Beat grid doesn't map to PT3/PSG frame-level events
- No AY register visualization
- No ZX-specific export (binary tables for Z80)

### 4. Precision Levels

Three tiers of sync precision, from rough to exact:

```
Level 0: Paper timing
  "Intro = 0-500, main = 500-2000, finale = 2000-3000"
  Tools: pen & paper, spreadsheet, any video editor
  Precision: ~seconds (±50 frames)

Level 1: Video editor workflow
  Record AY audio → import to video editor → mark sync points visually
  Export timecodes → convert to frame numbers
  Tools: Luma Fusion, DaVinci Resolve, Audacity
  Precision: ~0.5 sec (±25 frames)

Level 2: Clockwork (this project)
  Frame-accurate interactive editing tied to music events
  See every note, drum, pattern change on a timeline
  Place keyframes on parameter tracks, preview in real-time
  Tools: web browser
  Precision: 1 frame (20ms at 50Hz)
```

### 5. Architecture

#### 5.1 Pure Frontend (No Backend Required)

The simplest, most portable version is **100% client-side**:

```
┌─────────────────────────────────────────────┐
│                  Browser                     │
│                                              │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  │
│  │ PT3/PSG  │  │  ayumi-js │  │  Audio   │  │
│  │  Parser  │→ │  (AY emu) │→ │ Worklet  │→ 🔊
│  └────┬─────┘  └───────────┘  └──────────┘  │
│       │                                      │
│       ↓ register dump per frame              │
│  ┌──────────────────────────────────────┐    │
│  │         Timeline Editor              │    │
│  │  ┌─ waveform (wavesurfer.js) ──────┐│    │
│  │  ├─ pattern/row markers ───────────┤│    │
│  │  ├─ channel activity (A/B/C/noise) ┤│    │
│  │  ├─ drum/event detectors ──────────┤│    │
│  │  ├─ user sync tracks (keyframes) ──┤│    │
│  │  └─ effect parameter curves ───────┘│    │
│  └──────────────────────────────────────┘    │
│       │                                      │
│       ↓ export                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ JSON     │  │ .a80     │  │ binary   │   │
│  │ (debug)  │  │ (include)│  │ (table)  │   │
│  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────┘
```

**No server, no install, no dependencies.** Open `index.html` → drag-drop PT3/PSG file → edit → export.

#### 5.2 Optional Backend (for advanced features)

For heavier tasks, a Python backend can be added later:

- Convert TAP/TRD → extract music → PSG dump
- Run sjasmplus to assemble demo with exported sync data
- Launch mzx emulator for live preview
- Batch processing / CI integration

**Tech**: FastAPI or Flask, communicates via REST/WebSocket. But this is Phase 2+.

#### 5.3 Optional Rocket Compatibility

If the Clockwork editor speaks Rocket's WebSocket protocol (port 1338), then:
- Existing Rocket-enabled demos can connect
- Clockwork becomes a drop-in Rocket replacement with music awareness
- JS Rocket client library already exists

This is Phase 3 — nice to have, not essential.

### 6. Core Components

#### 6.1 Music Engine

| Component | Library | Purpose |
|-----------|---------|---------|
| AY emulation | ayumi-js (pure JS) | Sample-accurate sound generation |
| PT3 parser | Cowbell's PT3 backend or AYSir | Parse patterns, notes, instruments |
| PSG parser | Custom (~50 lines) | Parse register dumps |
| Audio output | AudioWorklet | Glitch-free playback off main thread |
| Waveform | wavesurfer.js | Visual waveform + regions + markers |

**Data flow**: PT3 file → parser → per-frame register writes → ayumi-js → AudioWorklet → speakers. Simultaneously, register writes are recorded as a PSG stream for the timeline.

#### 6.2 Music Analysis (automatic event detection)

From the per-frame AY register dump, detect:

| Event | Detection Method |
|-------|-----------------|
| **Drum hit** | Noise period change (R6) + volume spike (R8-R10) + mixer noise enable (R7) |
| **Note onset** | Tone period change (R0-R5) with volume > 0 |
| **Pattern boundary** | PT3 parser reports pattern/row number per frame |
| **Envelope trigger** | R13 write (envelope shape register) |
| **Silence** | All volumes = 0 |
| **Bass note** | Channel with lowest tone period |
| **Buzz-bass** | Envelope mode on (R8-R10 bit 4) + specific period alignment |

These detected events appear as **markers on the timeline** — user can snap sync keyframes to them.

#### 6.3 Timeline Editor

Two candidates for the canvas timeline:

1. **animation-timeline-js** — zero-dep TypeScript, canvas-based keyframe editor with snap, zoom, drag. Best fit.
2. **Custom canvas** — full control but more work.

**Timeline rows (top to bottom):**

```
┌─ Audio waveform (wavesurfer.js) ──────────────────────┐
├─ Pattern │ 0  │ 1  │ 2  │ 3  │ 4  │ 5  │ ...        │  ← from PT3
├─ Row     │0..63│0..63│0..63│                           │  ← PT3 row counter
├─ Ch.A ♪  │▃▃▅▇▇▅▃▃│▃▃▅▇▇▅▃▃│                          │  ← volume envelope
├─ Ch.B ♪  │    ▅▇▅  │    ▅▇▅  │                         │
├─ Ch.C ♪  │▇▇▇▇▇▇▇▇│▇▇▇▇▇▇▇▇│                         │  ← bass line
├─ Noise 🥁│  ▏  ▏   │  ▏  ▏   │                         │  ← detected drums
├─ Envelope │ ╱╲    │  ╱╲   │                             │
├─────────────────────────────────────────────────────────┤
├─ effect_id  │ plasma=0 ████│ torus=1 ████████│ plasma ██│  ← user track
├─ fade       │╲▁▁▁▁▁▁▁▁▁▁▁▁│▁▁▁▁▁▁▁▁▁▁▁▁╱╲▁│          │  ← user track
├─ rotate_spd │▁▁▁▁▁╱▔▔▔▔▔╲▁│▁▁╱▔▔▔▔▔▔▔▔▔▔▔▔│          │  ← user track
├─ palette    │ 0           │ 1    ▏  2       │ 0        │  ← user track (step)
└─────────────────────────────────────────────────────────┘
  frame: 0    100   200   300   400   500   600   700
```

**Top half**: read-only music analysis (auto-generated from PSG data).
**Bottom half**: user-editable sync tracks with keyframes.

#### 6.4 Sync Tracks (user-defined parameters)

Each track is a named float channel with keyframes:

```javascript
{
  name: "effect_id",       // track name (hierarchical: "scene:effect_id")
  type: "step",            // interpolation default for this track
  keyframes: [
    { frame: 0,   value: 0, interp: "step" },    // plasma
    { frame: 200, value: 1, interp: "step" },    // torus
    { frame: 450, value: 0, interp: "step" },    // plasma again
  ]
}
```

**Interpolation modes** (same as Rocket):
- **step**: constant until next keyframe
- **linear**: linear interpolation
- **smooth**: smoothstep (Hermite)
- **ramp**: quadratic ease-in

#### 6.5 Event Triggers (music → demo)

User defines trigger rules:

```javascript
{
  name: "flash_on_drum",
  source: "drum_hit",           // detected event type
  channel: "noise",             // which channel to watch
  action: "set",                // set a sync track value
  target_track: "flash",        // which track to modify
  value: 1,                     // value to set
  decay: { frames: 4, to: 0 }, // auto-decay back to 0 over 4 frames
}
```

This lets the demo **react to music** without manually placing keyframes on every drum hit.

#### 6.6 Export Formats

**a) JSON** (for debugging and round-tripping):
```json
{
  "version": 1,
  "music": "demo_tune.pt3",
  "bpm_hint": 125,
  "total_frames": 8000,
  "tracks": [ ... ],
  "triggers": [ ... ]
}
```

**b) Z80 assembly include** (for the demo):
```z80
; Generated by Clockwork — do not edit
; Music: demo_tune.pt3 (8000 frames, 160 sec)

SCENE_COUNT EQU 5

scene_table:
    ; effect_id, duration (frames), param_ptr
    DB 0 : DW 200 : DW params_0    ; plasma
    DB 1 : DW 250 : DW params_1    ; torus
    DB 0 : DW 200 : DW params_2    ; plasma (variant)
    DB 1 : DW 350 : DW params_3    ; torus (fast)
    DB $FF                          ; end marker

; Per-frame parameter table for tracks that need it
; (only keyframe changes stored, not every frame)
params_0:
    DB 0     ; fade=0, rotate_spd=0, palette=0
params_1:
    DB 128   ; fade=0, rotate_spd=128, palette=1
; ...

; Drum trigger table (frames where drum_hit detected)
drum_frames:
    DW 47, 95, 143, 191, 239, ...
    DW $FFFF  ; end marker
```

**c) Binary table** (compact, for memory-constrained demos):
```
Header: 4 bytes ("CWRK")
Track count: 1 byte
Per track:
  Name length: 1 byte
  Name: N bytes
  Keyframe count: 2 bytes (LE)
  Per keyframe:
    Frame: 2 bytes (LE)
    Value: 2 bytes (LE, fixed-point 8.8)
    Interpolation: 1 byte
```

### 7. User Workflow

```
1. Open Clockwork in browser
2. Drag-drop PT3 or PSG file
   → music loads, waveform appears, patterns/notes visualized
3. Press Play — hear music, see playback cursor move
4. Add sync tracks: "effect_id", "fade", "palette", etc.
5. Click on timeline to place keyframes
   → snap to detected drums, pattern boundaries, notes
6. Define trigger rules: "on every drum hit, flash=1 for 4 frames"
7. Preview: see parameter curves animate in real-time with music
8. Export → .a80 include file for demo engine
9. Assemble demo, run in emulator, verify sync
10. Iterate: adjust keyframes, re-export, re-test
```

### 8. Tech Stack

| Layer | Technology | Size | Notes |
|-------|-----------|------|-------|
| **AY emulation** | ayumi-js | ~8 KB | Pure JS port of ayumi |
| **PT3 parsing** | Custom or Cowbell backend | ~15 KB | Extract patterns/notes/instruments |
| **PSG parsing** | Custom | ~2 KB | Trivial format |
| **Audio output** | AudioWorklet | ~3 KB | Modern, off-thread |
| **Waveform** | wavesurfer.js v7 | ~15 KB | Regions + markers |
| **Timeline** | animation-timeline-js | ~30 KB | Canvas keyframe editor |
| **UI framework** | Vanilla JS + CSS | — | No framework needed |
| **Export** | Custom | ~5 KB | JSON + .a80 + binary |
| **Total** | | ~80 KB | No build step needed |

**No npm, no webpack, no React.** ES modules + `<script type="module">`. Open `index.html` and it works.

### 9. Phased Development

#### Phase 0: PSG Viewer (MVP, 1 week)
- Load PSG file → visualize 14 registers per frame on a scrollable timeline
- Playback via ayumi-js + AudioWorklet
- Waveform display
- Show frame numbers, detected pattern boundaries
- **Value**: immediately useful for debugging AY music, even without sync editing

#### Phase 1: Sync Track Editor (2 weeks)
- Add user-defined parameter tracks below the music visualization
- Keyframe placement with snap-to-event
- Step/linear/smooth interpolation
- JSON export/import
- **Value**: replaces hand-coded scene tables

#### Phase 2: Music-Aware Triggers (1 week)
- Drum detection, note onset detection
- Trigger rules (drum → flash, pattern change → effect switch)
- Auto-generated keyframes from triggers
- **Value**: reactive demos without manual keyframe placement

#### Phase 3: Z80 Export (1 week)
- Generate .a80 include files matching Antique Toy's engine format
- Binary table export for custom engines
- Scene table + parameter tables + event tables
- **Value**: closes the loop — edit in browser, export to demo

#### Phase 4: Live Preview (optional)
- WebSocket connection to mzx emulator (if mzx gains a remote API)
- Or: Rocket protocol compatibility (port 1338)
- Or: built-in ZX Spectrum screen renderer (canvas, using register dumps)
- **Value**: see the actual demo while editing sync

### 10. File Format: `.clockwork`

Project file = JSON with embedded or referenced music:

```json
{
  "clockwork_version": 1,
  "project_name": "Antique Toy",
  "music": {
    "file": "demo_tune.pt3",
    "format": "pt3",
    "total_frames": 8000,
    "speed": 3,
    "highlight": 16
  },
  "detected_events": {
    "drums": [47, 95, 143, ...],
    "pattern_boundaries": [0, 192, 384, ...],
    "notes": { "A": [...], "B": [...], "C": [...] }
  },
  "tracks": [
    {
      "name": "effect_id",
      "color": "#ff6600",
      "default_interp": "step",
      "keyframes": [
        { "frame": 0, "value": 0 },
        { "frame": 200, "value": 1 }
      ]
    }
  ],
  "triggers": [
    {
      "name": "flash_on_drum",
      "source": "drum_hit",
      "target": "flash",
      "value": 1,
      "decay": 4
    }
  ],
  "export": {
    "format": "a80",
    "engine": "antique_toy",
    "scene_table_label": "scene_table"
  }
}
```

### 11. Relationship to Book Content

| Book Section | Clockwork Connection |
|---|---|
| **Ch.11 (Sound)** | AY register map = what Clockwork visualizes |
| **Ch.12 (Music Sync)** | Concepts implemented by Clockwork (ring buffer, scripting, GABBA's workflow) |
| **Ch.12.4 (GABBA's method)** | Clockwork replaces the video editor step with a purpose-built tool |
| **Ch.20 (Demo Workflow)** | Scene table format = Clockwork's export target |
| **Appendix** | "Using Clockwork" tutorial (2-3 pages) linking to the tool |
| **Demo (Antique Toy)** | First customer — `demo/src/tables.a80` generated by Clockwork |

### 12. Prior Art Comparison

| Feature | GNU Rocket | Clockwork | Video Editor |
|---------|-----------|-----------|-------------|
| Beat grid | BPM-based | Frame + music-event aware | Manual markers |
| Music understanding | None (just BPM) | Full (patterns, notes, drums) | Waveform only |
| AY register view | No | Yes | No |
| Keyframe editing | Yes (float tracks) | Yes (float tracks) | Sort of (markers) |
| Interpolation | 4 modes | 4 modes (same) | N/A |
| Trigger rules | No | Yes (drum→flash) | No |
| Z80 export | No | Yes (.a80, binary) | No (timecodes) |
| Live demo connection | TCP socket | Phase 4 (WebSocket) | None |
| Platform | Desktop (Qt) | Browser | Desktop |
| Install | Compile C++ | Open HTML | Heavy app |
| ZX Spectrum aware | No | Yes | No |

### 13. Open Questions

1. **Name**: "Clockwork" fits the Antique Toy aesthetic (clockwork mechanism = precise timing). Alternatives: "zx-sync", "spectrack", "AY-sync". What do we prefer?

2. **PT3 parsing depth**: Do we parse PT3 natively in JS (complex: effects, ornaments, samples) or shell out to a conversion tool (pt3-to-psg) and work with PSG only? PSG-only is simpler but loses pattern/row structure.

3. **TurboSound**: Support 2xAY from day one or add later? (AYSir has dual-chip support in development.)

4. **Rocket compatibility**: Worth the protocol overhead? Or just export Rocket-compatible track files for offline use?

5. **Scope boundary**: Where does Clockwork end and the demo engine begin? Clockwork exports data; the demo engine consumes it. Clear interface = scene table + parameter tables.

### 14. Success Criteria

**Phase 0 is successful when**: you can load a PSG file, see register activity per frame on a timeline, hear the music, and identify drum hits visually.

**Phase 1 is successful when**: you can place keyframes on sync tracks, snap them to detected events, and export a JSON that round-trips perfectly.

**Phase 3 is successful when**: the Antique Toy demo's `tables.a80` is generated by Clockwork, the demo assembles and runs with correct effect timing.

**The project is successful when**: a demoscener who has never used it can load their PT3, define sync in 15 minutes, and export a working scene table.
