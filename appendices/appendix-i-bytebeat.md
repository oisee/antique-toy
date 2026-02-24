# Appendix I: Bytebeat and AY-Beat -- Generative Sound on Z80

> *"At 256 bytes, bytebeat is your only realistic option -- there is no room for a pattern player."*
> -- Chapter 13

---

This appendix covers formula-driven sound generation on the ZX Spectrum -- from the original PCM bytebeat concept to the AY-adapted technique that produces structured, evolving music from a handful of Z80 instructions. Chapter 13 introduces AY-beat as a size-coding tool. This appendix is the full reference: the theory, the formulas, the register mappings, and a complete working engine you can drop into a 256-byte intro.

You will need the AY register reference in Appendix G open alongside this appendix. Every register number mentioned here (R0, R7, R8, R11, R13, etc.) is documented there with full bit layouts and port addresses.

---

## 1. Classic Bytebeat: The PCM Tradition

In 2011, Ville-Matias Heikkila (Viznut) published a discovery that had been circulating in underground programming circles: a single C expression, evaluated once per sample with an incrementing counter `t`, can produce complex rhythmic music when the output is interpreted as 8-bit unsigned PCM at 8 kHz.

The core idea:

```c
for (t = 0; ; t++)
    putchar( f(t) );    // pipe to /dev/dsp at 8000 Hz
```

The function `f(t)` is typically a one-line expression built from bitwise operations, multiplication, and bit shifts. No oscillators, no envelopes, no note tables -- just integer arithmetic on a counter.

### Famous Formulas

**`t*((t>>12|t>>8)&63&t>>4)`** -- Viznut's original. Cascading rhythmic tones that cycle through pitch relationships, producing an effect somewhere between a music box and a broken telephone. The `t>>12` and `t>>8` create two frequency-divided versions of the counter; `&63` limits the range; `&t>>4` gates the output rhythmically. The multiplication by `t` creates the fundamental pitch sweep.

**`t*(t>>5|t>>8)>>(t>>16)`** -- Evolving rhythmic patterns. The right-shift by `t>>16` means the entire character of the sound changes every ~8 seconds (65536 samples at 8 kHz). Each 8-second section has a different dynamic range and feel.

**`(t*5&t>>7)|(t*3&t>>10)`** -- Two interleaved melodic lines. The `t*5` and `t*3` create two pitch streams at different intervals; the AND with shifted counters gates them independently; the OR merges them. The result sounds like two interlocking melodies playing simultaneously.

### Why It Works

Bitwise operations on an incrementing counter create periodic structures at multiple time scales simultaneously. Consider the bit pattern of `t` as it counts:

- Bit 0 toggles every sample (4000 Hz -- inaudible as pitch, but shapes the waveform)
- Bit 7 toggles every 128 samples (~62.5 Hz -- bass territory)
- Bit 12 toggles every 4096 samples (~1.95 Hz -- rhythmic pulse)
- Bit 15 toggles every 32768 samples (~0.24 Hz -- structural change)

A right-shift `t>>n` selects which time scale dominates. AND operations create coincidence patterns -- moments when two time scales align. OR operations merge independent patterns. Multiplication by small constants creates harmonic relationships (frequency ratios). The 8-bit truncation of the output acts as a natural waveform shaper, folding values back into range and creating additional harmonics.

The result is self-similar: the sound has rhythmic structure at every scale, from individual oscillation cycles up to multi-second phrase structures. This self-similarity is what makes bytebeat sound like music rather than noise -- even though no musical knowledge went into the formula.

### On the Spectrum: The Beeper Dead End

The ZX Spectrum's beeper output is a 1-bit speaker controlled by bit 4 of port $FE. You can, in principle, run a bytebeat formula and output the result:

```z80
; Beeper bytebeat -- uses all CPU, no visuals possible
; DE = t (16-bit counter)
    ld   de, 0
.loop:
    ; Compute f(t) -- simplified: A = t AND (t >> 8)
    ld   a, e          ; 4T   A = low byte of t
    and  d             ; 4T   A = t_lo AND t_hi
    ; Output bit 4 to speaker
    and  $10           ; 7T   isolate bit 4
    out  ($FE), a      ; 11T  toggle speaker
    inc  de            ; 6T   t++
    jr   .loop         ; 12T
                       ; --- 44T per sample = ~79.5 kHz
```

This runs, and it produces sound. But it consumes 100% of the CPU -- the Z80 is doing nothing but computing samples and toggling the speaker. No screen updates, no visual effects, no input handling. The sample rate is also wrong (too fast), and controlling it precisely requires careful cycle counting with padding NOPs.

For a demo, this is a dead end. The beeper is a 1-bit output that demands constant CPU attention. The real adaptation of bytebeat to the Spectrum requires a different approach entirely.

---

## 2. AY-Beat: Bytebeat Reimagined for a Tone Generator

The AY-3-8910 is not a DAC. It does not accept amplitude samples. It is a programmable tone generator: you give it a frequency (as a period value), a volume (0-15), and optional noise and envelope parameters, and its internal oscillators produce the sound autonomously. The CPU is free to do other work.

The key insight of AY-beat: **replace the sample counter with a frame counter, and replace PCM output with AY register values.**

Classic bytebeat computes one amplitude sample at ~8000 Hz. AY-beat computes tone periods, volumes, and noise parameters at 50 Hz -- once per video frame, triggered by the HALT instruction. The AY's oscillators handle the actual sound generation between frames.

The frame counter `t` replaces the sample counter. Formulas operate on `t` but produce register values, not waveform samples. Where PCM bytebeat has one degree of freedom (amplitude), AY-beat has many: three independent tone periods (12-bit each), three volumes (4-bit each), one noise period (5-bit), and a 16-bit envelope period with shape selection.

### Basic AY-Beat Architecture

```z80
; AY-beat frame update -- called once per HALT
; Assumes frame_counter is a byte in memory
ay_beat_update:
    ld   a, (frame_counter)
    ld   e, a             ; E = t (keep a copy)

    ; === Channel A: tone period from formula ===
    ; tone_lo = (t * 3) AND $3F -- pentatonic-ish cycling
    add  a, a             ; 4T   A = t * 2
    add  a, e             ; 4T   A = t * 3
    and  $3F              ; 7T   mask to 6 bits (periods 0-63)
    ld   d, a             ; 4T   save tone period
    ; Write R0 (tone A low) = D
    xor  a                ; 4T   A = 0 (register number)
    call ay_write_d       ; writes D to AY register A

    ; Write R1 (tone A high) = 0
    ld   a, 1             ; 7T
    ld   d, 0             ; 7T
    call ay_write_d

    ; === Channel A: volume from formula ===
    ; volume = bits 6-3 of t, giving 0-15 cycling
    ld   a, e             ; 4T   reload t
    rrca                  ; 4T
    rrca                  ; 4T
    rrca                  ; 4T
    and  $0F              ; 7T   volume 0-15
    ld   d, a             ; 4T
    ld   a, 8             ; 7T   R8 = Volume A
    call ay_write_d

    ; Advance frame counter
    ld   hl, frame_counter
    inc  (hl)             ; 11T
    ret
```

This is the simplest possible AY-beat: one channel, one tone formula, one volume formula, ~30 bytes. It produces a cycling sweep that rises in pitch and fades in and out -- not music, but recognisably structured sound.

### What Changes from PCM Bytebeat

| Aspect | Classic (PCM) | AY-Beat |
|--------|---------------|---------|
| Update rate | ~8000 Hz | 50 Hz (frame rate) |
| Output | 8-bit amplitude | Tone period (12-bit), volume (4-bit), noise (5-bit) |
| Channels | 1 (mono speaker) | 3 tone + 1 noise + envelope |
| CPU cost | 100% (all cycles) | ~200-500 T per frame (~0.3%) |
| Formula scaling | Fine-grained, fast evolution | Coarse-grained, need wider bit shifts |
| Sound generation | CPU computes every sample | AY hardware oscillators run autonomously |

The 50 Hz frame rate means formulas evolve 160x slower than at 8 kHz. To get equivalent rhythmic density, use larger multipliers and fewer right-shifts. A formula that produces a pleasant rhythm at 8 kHz with `t>>12` (period ~0.5 sec at 8 kHz) needs approximately `t>>4` at 50 Hz for similar timing (~0.3 sec between repetitions). The general rule: divide the PC bytebeat shift amounts by ~7 (log2 of the 160x ratio) and adjust by ear.

---

## 3. Drone: Envelope + Tone (E+T Mode)

This is where AY-beat gets genuinely interesting. The AY envelope generator automatically cycles the volume of a channel without any CPU intervention. Set a channel's volume register to envelope mode (bit 4 = 1, i.e. write $10 to R8/R9/R10), and the hardware handles volume modulation at the envelope frequency defined by R11-R12.

The result is a drone: a continuously evolving timbre produced by the interaction of the tone oscillator and the envelope oscillator. The CPU cost for maintaining this drone is almost zero -- you only need to update the tone period and envelope period once per frame, and the hardware does the rest.

### The Drone Recipe

1. Set a tone period from a formula -- this defines the base pitch.
2. Set an envelope period from a different formula -- this defines the modulation rate.
3. Set the envelope shape to a repeating waveform (shapes $08, $0A, $0C, or $0E).
4. Set the channel volume to envelope mode ($10).
5. The hardware produces a continuously evolving drone with zero per-sample CPU cost.

```z80
; Drone setup -- E+T mode
; Tone period evolves per frame, envelope period evolves slower
drone_update:
    ld   a, (frame_counter)
    ld   e, a             ; E = t

    ; --- Tone period: slowly sweeping ---
    and  $7F              ; 128-frame cycle (2.56 seconds)
    ld   d, a
    xor  a                ; R0 = Tone A low
    call ay_write_d
    ld   a, 1             ; R1 = Tone A high
    ld   d, 0
    call ay_write_d

    ; --- Envelope period: evolves on different time scale ---
    ld   a, e             ; reload t
    rrca
    rrca                  ; divide by 4 -- envelope evolves 4x slower
    and  $3F
    add  a, $10           ; offset to avoid very fast envelopes
    ld   d, a
    ld   a, 11            ; R11 = Envelope period low
    call ay_write_d
    ld   a, 12            ; R12 = Envelope period high
    ld   d, 0
    call ay_write_d

    ; --- Envelope shape: repeating triangle ---
    ; CAUTION: writing R13 restarts the envelope cycle.
    ; Only write on the first frame, or when you want a restart.
    ld   a, e
    or   a
    jr   nz, .skip_shape
    ld   a, 13            ; R13 = Envelope shape
    ld   d, $0A           ; shape $0A = repeating triangle \/\/
    call ay_write_d
.skip_shape:

    ; --- Volume A: envelope mode ---
    ld   a, 8             ; R8 = Volume A
    ld   d, $10           ; bit 4 set = use envelope
    call ay_write_d

    ret
```

The beauty of E+T mode is the interference between the two frequencies. When the envelope period is close to the tone period, you get amplitude modulation effects -- the volume beats at the difference frequency, producing a wavering, organ-like timbre. When the envelope frequency is much lower than the tone frequency, it acts as a slow tremolo. When it is much higher, you get buzz-bass territory (see Appendix G and Chapter 11).

Sweeping the envelope period while the tone period also moves produces continuously evolving textures. The two formulas create a two-dimensional parameter space that the sound explores over time. With the right formula pair, the drone never quite repeats -- it wanders through timbral variations, creating an ambient soundscape from fewer than 30 bytes of code.

### Byte Cost

Setting up E+T mode with a formula takes approximately 15-25 bytes. For a 256-byte intro, this gives you rich, evolving drone sound essentially for free -- no per-frame volume computation needed, no pattern data, just two register values derived from simple formulas. The AY hardware is doing all the oscillation work.

---

## 4. Noise Percussion

The AY noise generator (R6) produces pseudo-random noise at a programmable frequency (0-31). The mixer register (R7) controls which channels receive noise. Toggling noise on and off rhythmically, driven by the frame counter, creates percussion patterns.

### Basic Kick Pattern

```z80
; Noise percussion on channel C
; Frame counter in A (already loaded)
    ld   e, a             ; E = t
    and  $07              ; every 8th frame = 6.25 Hz pulse
    jr   nz, .decay

    ; --- Hit: enable noise on C, max volume ---
    ld   a, 7             ; R7 = Mixer
    ld   d, %00100100     ; tone C off, noise C on, others unchanged
    call ay_write_d
    ld   a, 6             ; R6 = Noise period
    ld   d, 2             ; low period = harsh, punchy
    call ay_write_d
    ld   a, 10            ; R10 = Volume C
    ld   d, $0F           ; maximum volume
    call ay_write_d
    jr   .done

.decay:
    ; --- Decay: reduce volume each frame ---
    ; Simple approach: volume = 15 - (t AND 7)
    ld   a, e
    and  $07              ; frames since last hit
    ld   d, a
    ld   a, $0F
    sub  d                ; volume = 15 - elapsed
    jr   nc, .vol_ok
    xor  a                ; clamp to 0
.vol_ok:
    ld   d, a
    ld   a, 10            ; R10 = Volume C
    call ay_write_d

.done:
```

### Percussion Character by Noise Period

| R6 Value | Character | Use |
|----------|-----------|-----|
| 0-3 | Harsh click, punchy | Kick drum, rimshot |
| 4-8 | Crisp hiss | Snare body |
| 10-15 | Broad noise | Open hi-hat |
| 20-31 | Low rumble | Distant thunder, ambient |

### Rhythmic Variety from Bit Masks

Different AND masks on the frame counter produce different rhythmic densities:

| Mask | Period | Frequency | Character |
|------|--------|-----------|-----------|
| `AND $03` | Every 4 frames | 12.5 Hz | Rapid fire, hi-hat |
| `AND $07` | Every 8 frames | 6.25 Hz | Standard kick |
| `AND $0F` | Every 16 frames | 3.125 Hz | Half-time, sparse |
| `AND $1F` | Every 32 frames | 1.5625 Hz | Slow pulse, intro |

Combine two masks for polyrhythm: test `t AND $07` for the kick, `t AND $03` for the hi-hat. This costs about 10 extra bytes but adds significant rhythmic complexity.

### Using the Envelope for Drum Decay

Instead of manually decaying the volume each frame, use the AY envelope generator in single-shot mode. Set R13 to shape $00 (decay to zero, hold), and the hardware handles the volume fade automatically:

```z80
; Envelope-based drum hit -- zero CPU cost for decay
    ld   a, e
    and  $07              ; every 8th frame
    jr   nz, .no_hit
    ; Set envelope period (controls decay speed)
    ld   a, 11
    ld   d, $80           ; period = $0080 -- medium decay
    call ay_write_d
    ld   a, 12
    ld   d, 0
    call ay_write_d
    ; Trigger: write shape $00 (single decay)
    ld   a, 13
    ld   d, $00
    call ay_write_d
    ; Volume C = envelope mode
    ld   a, 10
    ld   d, $10
    call ay_write_d
.no_hit:
```

This saves several bytes by eliminating the manual decay code. The trade-off: the envelope generator is shared across all channels in envelope mode. If channel A is using E+T drone, channel C cannot independently use the envelope for drum decay. Plan your channel allocation accordingly.

---

## 5. Multi-Channel Harmony

The AY has three independent tone channels. AY-beat can derive all three from a single formula using bit rotation, creating the impression of counterpoint from almost no code.

### Three Voices from One Formula

```z80
; Three related voices from one frame counter
    ld   a, (frame_counter)
    ld   e, a

    ; === Channel A: base formula ===
    and  $3F              ; period 0-63
    ld   d, a
    xor  a                ; R0
    call ay_write_d

    ; === Channel B: same formula, rotated 2 bits ===
    ld   a, e
    rrca
    rrca                  ; rotate right by 2
    and  $3F
    ld   d, a
    ld   a, 2             ; R2
    call ay_write_d

    ; === Channel C: same formula, rotated 4 bits ===
    ld   a, e
    rrca
    rrca
    rrca
    rrca                  ; rotate right by 4
    and  $3F
    ld   d, a
    ld   a, 4             ; R4
    call ay_write_d
```

The bit rotations create phase-shifted versions of the same pattern. The channels play related but offset melodies -- they follow the same contour but arrive at each pitch at different times. This creates an impression of counterpoint: multiple independent voices that share an underlying logic.

### Why Rotation Creates Harmony

RRCA is a *rotation*, not a shift -- bits that fall off the bottom wrap to the top. This means the three channels cycle through the same set of period values in the same order, but offset in time. The offset depends on the rotation amount:

- **RRCA x 2:** The channel is "ahead" by approximately a quarter of the pattern cycle. This often creates intervals that sound like fourths or fifths -- not precisely tuned, but harmonically related enough to be pleasant.
- **RRCA x 4:** Half a byte's worth of offset. This tends to produce octave-like relationships, since bit 4 being rotated to bit 0 effectively halves the period in certain phase alignments.

These are not real musical intervals. They are pseudo-harmonic relationships created by the structure of binary numbers. But the ear is forgiving -- if two tones share most of their bit pattern, they sound "related," and that is enough for a 256-byte intro.

### Volume Formulas for Multi-Channel

Give each channel a different volume formula to avoid all three voices being at the same level simultaneously:

```z80
    ; Volume A: bits 6-3 of t
    ld   a, e
    rrca
    rrca
    rrca
    and  $0F
    ld   d, a
    ld   a, 8
    call ay_write_d

    ; Volume B: bits 4-1 of t (different phase)
    ld   a, e
    rrca
    and  $0F
    ld   d, a
    ld   a, 9
    call ay_write_d

    ; Volume C: inverted bits 5-2 of t
    ld   a, e
    rrca
    rrca
    and  $0F
    xor  $0F              ; invert -- when A is loud, C is quiet
    ld   d, a
    ld   a, 10
    call ay_write_d
```

The inverted volume on channel C creates a call-and-response dynamic: as one voice fades in, another fades out. This costs 2 extra bytes (the `XOR $0F`) but significantly improves the musical texture.

---

## 6. Formula Cookbook

The following formulas have been tested on the AY at 50 Hz frame rate. "Bytes" refers to the Z80 implementation cost for computing the formula from a value already in register A (the frame counter). The period mask determines the pitch range.

### Tone Period Formulas

| # | Formula | Z80 Implementation | Bytes | Sound | Best For |
|---|---------|---------------------|-------|-------|----------|
| 1 | `t AND $3F` | `and $3F` | 2 | Rising sawtooth, 1.28-sec cycle | Simple sweep |
| 2 | `t*3 AND $3F` | `ld e,a : add a,a : add a,e : and $3F` | 5 | Faster sweep, wider intervals | Energetic bass |
| 3 | `t XOR (t>>3)` | `ld e,a : rrca : rrca : rrca : xor e` | 5 | Chaotic with periodic structure | Noise texture |
| 4 | `(t AND $0F) XOR $0F` | `and $0F : xor $0F` | 4 | Triangle wave, ping-pong sweep | Melodic lead |
| 5 | `t*5 AND t>>2` | `ld e,a : add a,a : add a,a : add a,e : ld d,a : ld a,e : rrca : rrca : and d` | 10 | Rhythmic gating | Percussion-like |
| 6 | `(t+t>>4) AND $1F` | `ld e,a : rrca : rrca : rrca : rrca : add a,e : and $1F` | 6 | Slowly modulated sweep | Evolving drone |
| 7 | `t AND (t>>3) AND $1F` | `ld e,a : rrca : rrca : rrca : and e : and $1F` | 6 | Self-similar, fractal rhythm | Complex patterns |
| 8 | `(t>>1) XOR (t>>3)` | `ld e,a : rrca : ld d,a : rrca : rrca : xor d` | 6 | Dual-speed interference | Metallic texture |
| 9 | `t*7 AND $7F` | `ld e,a : add a,a : add a,a : add a,a : sub e : and $7F` | 6 | Wide sweep, 7x speed | Fast arpeggio feel |
| 10 | `(t XOR t>>1) AND $3F` | `ld e,a : rrca : xor e : and $3F` | 5 | Gray code sequence | Staircase melody |
| 11 | `t AND $07 OR t>>4` | `ld e,a : and $07 : ld d,a : ld a,e : rrca : rrca : rrca : rrca : or d` | 8 | Nested loops, two rhythmic layers | Layered rhythm |
| 12 | `(t+t+t>>2) AND $3F` | `ld e,a : add a,a : ld d,a : ld a,e : rrca : rrca : add a,d : and $3F` | 8 | Accelerating sweep with sub-pattern | Textured lead |

### Volume Formulas

| # | Formula | Z80 | Bytes | Effect |
|---|---------|-----|-------|--------|
| V1 | `t>>3 AND $0F` | `rrca : rrca : rrca : and $0F` | 5 | Slow fade cycle, 5.12 sec |
| V2 | `(t AND $0F) XOR $0F` | `and $0F : xor $0F` | 4 | Triangle volume, ping-pong |
| V3 | `t*3>>4 AND $0F` | `ld e,a : add a,a : add a,e : rrca : rrca : rrca : rrca : and $0F` | 8 | Irregular fade pattern |
| V4 | `$0F` (constant) | `ld d,$0F` | 2 | Maximum volume, use with envelope mode |

### How to Read the Table

Pick a tone formula and a volume formula. Combine them. The total byte cost is the sum of both implementations plus the AY register write overhead (~8 bytes per channel for two ay_write calls: register select + data for tone low and volume). A single channel with formula #1 and volume V1 costs approximately 2 + 5 + 16 = 23 bytes including register writes.

Formula #10 (Gray code) deserves special mention. The Gray code sequence only changes one bit per step, so the tone period changes by exactly one unit per frame -- a smooth, staircase-like melody. Combined with the AND mask, it cycles through a limited pitch range with pleasant regularity. This is one of the most musical-sounding single formulas.

---

## 7. Putting It Together: A Complete AY-Beat Engine

Here is a complete, minimal AY-beat engine that produces 3-channel generative sound with envelope drone. This is the engine you drop into a 256-byte intro alongside your visual effect.

```z80
; ============================================================
; Complete AY-beat engine -- 47 bytes
; Produces 3-channel generative music with envelope drone
; Call once per frame (after HALT)
; Clobbers: AF, BC, DE, HL
; ============================================================

ay_beat:
    ld   hl, .frame
    ld   a, (hl)          ; A = frame counter
    inc  (hl)             ; advance for next frame
    ld   e, a             ; E = t (preserved copy)

    ; --- Mixer: all three tones on, no noise ---
    ; Only needed on first frame, but costs 5 bytes either way
    push af
    ld   a, 7             ; R7
    ld   d, $38           ; tones A+B+C on, noise off
    call .wr
    pop  af

    ; --- Channel A: tone = t AND $3F ---
    and  $3F
    ld   d, a
    xor  a                ; R0
    call .wr

    ; --- Channel B: tone = t*3 AND $3F ---
    ld   a, e
    add  a, a
    add  a, e             ; A = t * 3
    and  $3F
    ld   d, a
    ld   a, 2             ; R2
    call .wr

    ; --- Channel C: tone = (t XOR t>>1) AND $3F ---
    ld   a, e
    rrca
    xor  e
    and  $3F
    ld   d, a
    ld   a, 4             ; R4
    call .wr

    ; --- Volumes: A and B fixed at 12, C = envelope mode ---
    ld   a, 8             ; R8 = Volume A
    ld   d, 12
    call .wr
    ld   a, 9             ; R9 = Volume B
    ld   d, 10
    call .wr
    ld   a, 10            ; R10 = Volume C
    ld   d, $10           ; envelope mode
    call .wr

    ; --- Envelope: period sweeps with t, triangle shape ---
    ld   a, e
    rrca
    rrca
    and  $3F
    add  a, $20           ; keep envelope period above $20
    ld   d, a
    ld   a, 11            ; R11
    call .wr
    ; R12 = 0 (envelope period high)
    inc  a                ; A = 12
    ld   d, 0
    call .wr

    ; Shape: only write on frame 0 to avoid constant restarts
    ld   a, e
    or   a
    ret  nz               ; skip shape write on all frames except 0
    ld   a, 13            ; R13
    ld   d, $0E           ; shape $0E = repeating triangle /\/\
    ; fall through to .wr, then ret

.wr:
    ; Write D to AY register A
    ld   bc, $FFFD
    out  (c), a           ; select register
    ld   b, $BF
    out  (c), d           ; write value
    ret

.frame:
    DB   0                ; frame counter (self-modifying data)

; ============================================================
; Total: 47 bytes (code) + AY write routine shared
; The .wr routine is 9 bytes. If your intro already has an
; AY write routine, the engine body alone is 38 bytes.
; ============================================================
```

### What This Produces

- **Channel A:** A simple ascending sweep, cycling through periods 0-63 every 64 frames (1.28 seconds). The fundamental pattern.
- **Channel B:** The same sweep at 3x speed, creating faster-moving intervals. When it aligns with channel A, you hear consonance; when it diverges, you hear dissonance. The alternation creates rhythmic interest.
- **Channel C:** A Gray code sweep in envelope mode. The triangle envelope creates automatic volume modulation, producing a drone that phases against the tone period. This is the harmonic bed underlying the other two voices.
- **Overall:** An evolving, self-similar texture that cycles through tonal relationships. It sounds alien and mechanical -- exactly right for a 256-byte intro.

### Customisation Points

**Change the tone formulas.** Swap any of the AND/RRCA sequences for a different formula from the cookbook (section 6). Each substitution changes the character entirely.

**Add noise percussion.** Insert a `ld a,e : and $07 : jr nz,.no_hit` block (section 4) to add rhythmic kicks. Cost: ~12 bytes. Steal a channel (typically B) or overlay noise on channel C.

**Use pentatonic masking.** Instead of `AND $3F` as the final mask, index into a 5-byte pentatonic lookup table. This constrains the tone periods to harmonically related values, making the output sound more deliberately musical. Cost: ~8 bytes (5 for the table, 3 for the lookup). Chapter 13 discusses this technique.

**Vary fixed volumes.** Replace the constant volume writes with volume formulas from section 6. Even `ld a,e : rrca : rrca : rrca : and $0F` (5 bytes per channel) adds significant dynamic interest.

---

## 8. Advanced: Combining Techniques

The preceding sections cover individual building blocks. A well-crafted AY-beat engine combines several:

### Architecture for a 256-Byte Intro

```
Frame 0:   Set mixer, envelope shape (one-time setup)
Frame N:   Update tone A (melody formula)
           Update tone B (harmony formula, rotated)
           Update volume A (fade formula)
           Update volume B (inverted fade)
           Channel C in E+T drone mode (auto-evolving)
           Every 8th frame: noise hit on C (toggle mixer)
```

The total CPU cost per frame is approximately 300-500 T-states -- well under 1% of the ~70,000 T-states available per frame. The remaining 99% is available for your visual effect.

### Register Budget

The AY has 14 writable registers. In a minimal AY-beat engine, you typically write 8-10 per frame:

| Register | Written | Source |
|----------|---------|--------|
| R0 (Tone A low) | Every frame | Formula |
| R2 (Tone B low) | Every frame | Formula |
| R4 (Tone C low) | Every frame or once | Formula or fixed |
| R1, R3, R5 (Tone high) | Once (set to 0) | Constant |
| R7 (Mixer) | Every frame or once | Constant or toggled for noise |
| R8, R9 (Volume A, B) | Every frame | Formula or constant |
| R10 (Volume C) | Once | $10 (envelope mode) |
| R11 (Envelope low) | Every frame | Formula |
| R13 (Envelope shape) | Once (frame 0) | Constant |

Registers you can skip entirely: R6 (noise period -- only needed if using noise), R12 (envelope high -- set once to 0 for short periods), R14-R15 (I/O ports -- irrelevant for sound).

### Size Breakdown

For a 256-byte intro, every byte matters. Here is how a typical AY-beat budget looks:

| Component | Bytes |
|-----------|-------|
| AY write routine | 9 |
| Frame counter management | 5 |
| 3 tone formulas (simple) | 12-18 |
| 3 volume settings | 6-15 |
| Mixer setup | 5 |
| Envelope setup | 8-12 |
| Total | **45-64** |

This leaves 192-211 bytes for the visual effect, the main loop, and any other infrastructure. At 45 bytes, the engine in section 7 is close to optimal for the amount of sound it produces.

---

## 9. AY-as-DAC: Classic Bytebeat Through the Volume Register

There is a middle path between the beeper dead end and the AY-beat reimagining. The AY-3-8910's volume registers (registers 8, 9, 10) accept 4-bit values (0-15). If you update a volume register at a high rate -- say, during a tight loop -- the AY output becomes a 4-bit DAC. This is how digitised speech and sample playback work in Spectrum demos.

Applied to bytebeat: compute `f(t)`, shift right to 4 bits, write to volume register:

```z80
; AY-as-DAC bytebeat -- 4-bit PCM through volume register
; Still costly (~80% CPU), but sounds better than beeper
    ld   a, 7               ; mixer: all channels off (tone+noise)
    ld   d, %00111111
    call ay_write
    ld   de, 0               ; t = 0
.loop:
    ; Compute f(t): t AND (t >> 5) -- classic bytebeat formula
    ld   a, e
    ld   b, d
    srl  b
    rr   a
    srl  b
    rr   a
    srl  b
    rr   a
    srl  b
    rr   a
    srl  b
    rr   a                   ; A = t >> 5 (using DE as 16-bit t)
    and  e                   ; A = t AND (t >> 5)
    rrca
    rrca
    rrca
    rrca
    and  $0F                 ; scale to 4-bit (0-15)
    ld   bc, AY_REG
    ld   b, $FF              ; select register
    push af
    ld   a, 8                ; register 8: volume A
    out  (c), a
    ld   b, $BF
    pop  af
    out  (c), a              ; write volume
    inc  de                  ; t++
    jr   .loop
```

This produces recognisable bytebeat -- the actual waveform formulas from section 1, audible through the AY. The sound quality is better than the beeper (4-bit resolution vs 1-bit), and the AY's output stage provides proper audio levels.

The cost is still brutal: ~80% CPU. You get a thin sliver of time for visuals -- enough for a slowly-updating attribute effect, not enough for anything ambitious. This technique is useful when you want the *specific sound* of classic bytebeat formulas and are willing to pay the CPU price.

### Three Output Paths Compared

| Path | Resolution | CPU cost | Sound character | Practical for demos? |
|------|-----------|----------|-----------------|---------------------|
| Beeper (port $FE) | 1-bit | ~100% | Harsh, buzzy | No |
| AY volume DAC | 4-bit | ~80% | Classic bytebeat | Barely (attribute effects only) |
| AY-beat (registers) | Tone/noise | ~0.5% | Chip music, generative | Yes -- the right choice |

For size-coded intros and demos, AY-beat is almost always the correct choice. Reserve AY-as-DAC for art projects where the specific bytebeat sound aesthetic is the point.

---

## 10. Music Theory for Algorithms

AY-beat formulas that ignore music theory produce interesting noise. Formulas that *encode* music theory produce actual music. The following techniques add musicality for minimal bytes.

### Scale Tables: Constraining Output to Pleasant Notes

A raw formula like `tone = t AND $3F` produces all 64 possible period values -- most of which are not musically useful. A **scale table** maps formula output to actual note periods, ensuring every value sounds good.

| Scale | Notes | Table size | Character |
|-------|-------|-----------|-----------|
| Pentatonic | 5 (C D E G A) | 10 bytes (5 × 2-byte periods) | Always consonant, folk/world feel |
| Diatonic major | 7 (C D E F G A B) | 14 bytes | Bright, Western, familiar |
| Diatonic minor | 7 (C D Eb F G Ab Bb) | 14 bytes | Dark, melancholic |
| Blues | 6 (C Eb F F# G Bb) | 12 bytes | Gritty, expressive |
| Chromatic | 12 | 24 bytes | Atonal, dissonant -- usually wrong for sizecoding |

The pentatonic scale is the size-coder's best friend: 5 notes, 10 bytes, and *any* combination of notes sounds acceptable. You cannot play a wrong note on a pentatonic scale. This is why so many 256-byte intros sound vaguely "Asian" or "folk" -- the pentatonic constraint makes random sequences musical.

```z80
; Scale-constrained note lookup
; Input: A = formula output (any value)
; Output: DE = AY tone period
    ; Map to scale index: A mod scale_length
    and  $07               ; keep low 3 bits
    cp   5                 ; pentatonic has 5 notes
    jr   c, .in_range
    sub  5                 ; wrap: 5→0, 6→1, 7→2
.in_range:
    add  a, a              ; ×2 for word entries
    ld   hl, pentatonic
    add  a, l
    ld   l, a
    ld   e, (hl)
    inc  hl
    ld   d, (hl)           ; DE = tone period
```

### Octave Derivation: Free Pitch Range

Store one octave of periods. Derive all others by bit-shifting:

- `SRL D : RR E` = one octave up (period halved, pitch doubled)
- `SLA E : RL D` = one octave down (period doubled, pitch halved)

Five pentatonic notes × one stored octave × bit-shifting = 5 notes × 5+ octaves = 25+ distinct pitches from 10 bytes of data. The formula selects the note, a separate bit mask selects the octave:

```z80
    ; note_index = formula AND $0F
    ; octave = note_index / 5 (0-2)
    ; note = note_index % 5
    ; Look up base period, then SRL 'octave' times
```

### Arpeggio: Chord Tones in Sequence

An arpeggio cycles through the tones of a chord. In scale-degree terms:

| Chord | Scale offsets | Sound |
|-------|-------------|-------|
| Major triad | 0, 2, 4 (root, third, fifth) | Bright, resolved |
| Minor triad | 0, 2, 3 (root, m.third, fifth) | Dark, tense |
| Power chord | 0, 4 (root, fifth) | Open, strong |
| Suspended | 0, 3, 4 (root, fourth, fifth) | Ambiguous, floating |

Implementation: `arp_step = (t / speed) % chord_size`, then add the offset to the current root note:

```z80
; Arpeggio: cycle through major triad
    ld   a, (frame)
    rrca
    rrca                   ; A = frame / 4 (arp speed)
    ; mod 3 for three chord tones
    ld   b, a
.mod3:
    sub  3
    jr   nc, .mod3
    add  a, 3              ; A = 0, 1, or 2
    ld   hl, arp_major
    add  a, l
    ld   l, a
    ld   a, (hl)           ; A = scale offset
    ; add to chord root, look up in scale table
    ; ...

arp_major:  DB  0, 2, 4    ; root, third, fifth (3 bytes)
arp_minor:  DB  0, 2, 3    ; root, min.third, fifth (3 bytes)
```

Three bytes per chord shape. The arpeggio speed is derived from the frame counter — no separate timer needed.

### Step Ornaments: Trills, Mordents, and Slides

An ornament is a tiny cyclic pattern of relative pitch offsets applied to a note. In tracker music, ornaments make flat tones come alive:

| Ornament | Pattern | Effect | Bytes |
|----------|---------|--------|-------|
| Trill | 0, +1, 0, -1 | Rapid alternation with neighbor | 4 |
| Mordent | 0, +1, 0, 0 | Brief upper neighbor, then settle | 4 |
| Slide up | 0, 0, +1, +1 | Gradual rise | 4 |
| Vibrato | 0, +1, +1, 0, -1, -1 | Smooth wobble | 6 |

Apply by adding the ornament value to the note index before the scale table lookup:

```z80
    ; ornament_pos = (frame) AND (ornament_length - 1)
    ld   a, (frame)
    and  $03               ; mod 4 for 4-step ornament
    ld   hl, trill
    add  a, l
    ld   l, a
    ld   a, (hl)           ; A = pitch offset (-1, 0, or +1)
    add  a, c              ; C = current note index
    ; ... look up modified note in scale table

trill:    DB  0, 1, 0, -1   ; 4 bytes
mordent:  DB  0, 1, 0, 0    ; 4 bytes
```

Four bytes transform a static tone into a living voice. Stack multiple ornaments on different channels for rich texture.

### Chord Progressions: Harmonic Movement

The chord root can change over time, following a progression. Classical harmony in 4 bytes:

```z80
; I - IV - V - I progression (the backbone of Western music)
progression:  DB  0, 3, 4, 0     ; scale degrees

; Select chord: (frame / 64) AND 3
    ld   a, (frame)
    rrca
    rrca
    rrca
    rrca
    rrca
    rrca                   ; A = frame / 64
    and  $03               ; mod 4
    ld   hl, progression
    add  a, l
    ld   l, a
    ld   a, (hl)           ; A = chord root (scale degree)
```

Four bytes of progression data, cycled by the frame counter, give your AY-beat piece harmonic movement -- the sense that it is "going somewhere" rather than looping on one chord. Other progressions:

| Progression | Degrees | Bytes | Feel |
|-------------|---------|-------|------|
| I-IV-V-I | 0, 3, 4, 0 | 4 | Classic resolution |
| I-V-vi-IV | 0, 4, 5, 3 | 4 | Pop/rock standard |
| i-VI-III-VII | 0, 5, 2, 6 | 4 | Epic minor |
| I-I-I-I | 0, 0, 0, 0 | 1 (or skip) | Drone/meditative |

### Total Data Budget for Rich Music

Combining all techniques:

| Component | Bytes |
|-----------|-------|
| Pentatonic table (5 notes) | 10 |
| Arpeggio pattern (1 chord) | 3 |
| Ornament (trill) | 4 |
| Progression (4 chords) | 4 |
| **Total** | **21** |

21 bytes of musical data — plus ~45 bytes of engine code — produces three-channel music with melody, harmony, chord changes, and ornamentation. The `aybeat.a80` example in this book's companion code demonstrates this approach in 320 bytes, with room left over for visuals.

---

## 11. L-System Grammars: Fractal Melodies

Lindenmayer systems (L-systems) are rewriting grammars originally invented to model plant growth. Applied to music, they generate self-similar sequences with long-range structure from tiny rule sets.

### The Concept

An L-system has an **axiom** (starting string) and **production rules** (expansion rules). Each iteration replaces every symbol according to its rule:

```
Axiom: A
Rules: A → A B,  B → A
```

```
Step 0: A
Step 1: A B
Step 2: A B A
Step 3: A B A A B
Step 4: A B A A B A B A
```

This is the **Fibonacci L-system**. The sequence grows by the Fibonacci ratio (~1.618x per step). Map the symbols to musical events:

| Symbol | Musical meaning |
|--------|----------------|
| A | Play root note (scale degree 0) |
| B | Play fifth (scale degree 4) |

The resulting melody: root, fifth, root, root, fifth, root, fifth, root... — a sequence that is neither periodic nor random, but *quasi-periodic*. It has structure at every scale, like a fractal. It sounds intentional without being repetitive.

### Why L-Systems Work for Music

1. **Self-similarity.** The melody at large scales echoes the melody at small scales. This is what makes composed music feel coherent -- themes recur at different levels.
2. **Non-repetition.** Unlike a looped pattern, an L-system sequence never exactly repeats (for irrational growth ratios). It stays interesting.
3. **Tiny encoding.** The rules are a few bytes. The sequence they generate is arbitrarily long.

### Useful L-System Rules

| Name | Axiom | Rules | Growth | Character |
|------|-------|-------|--------|-----------|
| Fibonacci | A | A→AB, B→A | ~1.618x | Quasi-periodic, organic |
| Thue-Morse | A | A→AB, B→BA | 2x | Balanced, fair — no long runs |
| Period-doubling | A | A→AB, B→AA | 2x | Increasingly syncopated |
| Cantor | A | A→ABA, B→BBB | 3x | Sparse, with silences (B=rest) |

### Z80 Implementation

The trick for Z80 is to **not expand the string in memory** (that would require unbounded buffer space). Instead, compute the symbol at position `n` recursively: trace back through the rule applications to determine which original symbol position `n` came from.

For the Fibonacci L-system, there is an elegant shortcut. The symbol at position `n` depends on the Zeckendorf representation (Fibonacci coding) of `n`. But for practical sizecoding, a simpler approach works:

```z80
; L-system melody generator (Fibonacci: A→AB, B→A)
; Returns next note in sequence
; Uses position counter in memory
;
; The sequence of symbols can be generated iteratively:
; keep two "previous" bytes and generate the next

lsys_next:
    ld   hl, lsys_state
    ld   a, (hl)           ; prev1
    inc  hl
    ld   b, (hl)           ; prev2
    inc  hl
    ld   c, (hl)           ; position in current generation

    ; Fibonacci rule: output prev1, then swap
    ; When position reaches length, expand to next generation
    ld   d, a              ; D = current symbol to output

    ; Advance: shift the pair
    inc  c
    ld   (hl), c
    dec  hl
    ld   (hl), a           ; prev2 = prev1
    dec  hl
    ; New prev1 from rule: A→A (first output), then A→B (second)
    ; Simplified: alternate symbols based on parity
    ld   a, c
    and  $01
    jr   z, .sym_a
    ld   a, 1              ; B
    jr   .store
.sym_a:
    xor  a                 ; A (=0)
.store:
    ld   (hl), a

    ; Map symbol to scale degree
    ld   a, d
    or   a
    jr   z, .root
    ; B = fifth
    ld   a, 4              ; scale degree 4 = fifth in pentatonic
    ret
.root:
    xor  a                 ; scale degree 0 = root
    ret

lsys_state:
    DB   0                 ; prev1 (A=0, B=1)
    DB   0                 ; prev2
    DB   0                 ; position
```

A more practical approach for sizecoding: precompute several iterations of the L-system into a short buffer at init time (one iteration of Fibonacci from a 5-symbol axiom yields 8 symbols, two iterations yield 13, three yield 21 — all fitting in a small buffer), then loop through the buffer as a melody sequence:

```z80
; Precompute L-system into buffer (Fibonacci, 3 iterations)
; Axiom: "AABAB" (5 symbols) → 8 → 13 → 21 symbols
; 21 notes of fractal melody from 5 bytes of axiom + expansion code

lsys_expand:
    ld   hl, lsys_axiom
    ld   de, lsys_buf
    ld   b, 5              ; axiom length
.expand_iter:
    ; One iteration: for each symbol, apply rule
    push bc
    push hl
    ld   hl, lsys_buf
    ld   de, lsys_work     ; expand into work buffer
    ; ...expand according to rules...
    pop  hl
    pop  bc
    ; Copy work back to buf for next iteration
    ; Repeat for desired number of iterations
    ret

lsys_axiom:
    DB   0, 0, 1, 0, 1     ; A A B A B

; During playback:
; melody_index = frame / note_duration
; note = lsys_buf[melody_index % buf_length]
; look up in scale table → AY period
```

### Melody as Motion, Not Absolute Notes

The most musical use of L-systems is not mapping symbols to fixed notes, but mapping them to **scale step directions**. A melody is fundamentally about *motion* — up, down, repeat, skip — on a scale. The starting note is arbitrary; the contour is what matters.

Define symbols as movements:

| Symbol | Meaning | Scale step |
|--------|---------|-----------|
| U | Step up | +1 |
| D | Step down | -1 |
| R | Repeat | 0 |
| S | Skip up (leap) | +2 |

Now an L-system generates melodic *contour*, not fixed pitch sequences:

```
Axiom: U
Rules: U → U R D,  D → U,  R → U D
```

```
Step 0: U                          (+1)
Step 1: U R D                      (+1, 0, -1)
Step 2: U R D  U D  U              (+1, 0, -1, +1, -1, +1)
Step 3: U R D  U D  U  U R D  U  U R D  U D   ...
```

The melody walks up and down the current scale, always staying within the scale table. It naturally tends toward the starting pitch (the returns balance the departures), creating the tension-and-resolution arc that makes music feel intentional.

```z80
; Motion-based L-system playback
; current_note = scale index, modified by each symbol
    ld   a, (current_note)
    ld   hl, lsys_buf
    ld   b, (melody_pos)
    add  a, l
    ; ... get motion symbol at current position ...
    ; D = motion offset from symbol table
    add  a, d              ; current_note += motion
    and  $0F               ; wrap to scale range
    ld   (current_note), a
    ; look up in pentatonic table → AY period
```

This is more musical than mapping A=root, B=fifth. The same L-system rules produce different melodies depending on the starting note and the underlying scale — change the scale from pentatonic to blues and the same contour produces a completely different mood.

### Tribonacci: Three Symbols for Richer Patterns

The Fibonacci L-system uses two symbols. **Tribonacci** uses three: A→ABC, B→A, C→B. The growth ratio is ~1.839x (the tribonacci constant). Three symbols mean more varied melodic content:

| Symbol | As motion | As note |
|--------|-----------|---------|
| A | Step up (+1) | Root |
| B | Repeat (0) | Third |
| C | Step down (-1) | Fifth |

```
Axiom: A
Step 1: A B C
Step 2: A B C  A  B
Step 3: A B C  A  B  A B C  A B C
```

The tribonacci sequence has longer non-repeating runs than Fibonacci and a more complex internal structure. Musically, the three-symbol vocabulary gives melodies more variety — they don't just ping-pong between two states.

### PRNG Melodies with Curated Seeds

A linear feedback shift register (LFSR) or similar PRNG generates a deterministic pseudo-random sequence from a seed value. The sequence *sounds* random but repeats exactly if you reset the seed. This gives you reproducible melody fragments.

The technique: **pre-test many seeds, keep the ones that sound good.** Store 2-4 seed values (2 bytes each) for different sections of your piece. At runtime, load the seed and let the PRNG generate the melody. The PRNG itself is ~6-8 bytes; each seed is 2 bytes.

```z80
; LFSR-based melody generator
; HL = seed (determines the melody)
prng_note:
    ld   a, h
    xor  l              ; mix bits
    rrca
    rrca
    xor  h
    ld   h, a
    ld   a, l
    add  a, h
    ld   l, a           ; advance LFSR state (~6 bytes)
    and  $07            ; constrain to scale range
    ret                 ; A = note index for scale table

; Different seeds → different melodies
seed_verse:   DW  $A73B    ; tested: produces ascending contour
seed_chorus:  DW  $1F4D    ; tested: produces energetic pattern
seed_bridge:  DW  $8E21    ; tested: produces descending, calm
```

The workflow: write a test harness that plays the PRNG melody for each seed value 0-65535, listen (or analyse), mark the good ones. In practice, a few hours of testing yields dozens of usable seeds. Store 3-4 of them and switch between sections of your piece.

**Combining with scale tables:** the PRNG output feeds through the pentatonic table, so even "bad" seeds produce consonant notes. You're curating for *melodic contour*, not avoiding wrong notes — the scale table already handles that.

**Combining with L-systems:** use the PRNG to *select which L-system rule to apply* at each step, creating stochastic L-systems. The seed controls the "personality" of the piece; the grammar rules control the structure. This hybrid produces the richest output from the fewest bytes.

### Combining L-Systems with Other Techniques

L-systems generate note *sequences*. Combine with the other techniques from this appendix:

- **Scale table** maps L-system symbols to actual AY periods
- **Ornaments** add expression to each note
- **Arpeggio** turns each L-system note into a chord
- **Envelope drone** provides a sustained harmonic bed under the fractal melody
- **Chord progression** changes the root — the L-system melody is transposed to each chord

The result: a tiny program (~60-80 bytes of music code + 20 bytes of data) generating minutes of structurally coherent, non-repeating, harmonically grounded music. This is algorithmic composition, not random noise — and it fits in a size-coded intro.

### Other Grammars for Music

Beyond L-systems, other formal grammars produce interesting musical sequences:

**Cellular automata.** Rule 30 or Rule 110, applied to a row of bits, produce complex patterns. Map bit positions to note on/off events. Cost: ~15 bytes for the CA rule, ~20 bytes for the stepper.

**Euclidean rhythms.** Distribute `k` beats evenly across `n` steps. This algorithm (related to the Euclidean GCD) generates rhythmic patterns found in music worldwide: 3-in-8 is tresillo, 5-in-8 is cinquillo, 7-in-12 is a common West African bell pattern. Implementation is ~20 bytes and produces perfect rhythmic foundations for any AY-beat engine.

---

## See Also

- **Chapter 11** -- AY-3-8910 architecture, tone/noise/envelope theory, buzz-bass technique
- **Chapter 12** -- Music engine integration, sync to effects, hybrid digital drums
- **Chapter 13** -- Sizecoding techniques, where AY-beat fits in the 256b/512b/1K/4K size tiers
- **Appendix G** -- Complete AY register reference with bit layouts, port addresses, and note tables

---

> **Sources:** Viznut (Ville-Matias Heikkila), "Algorithmic symphonies from one line of code -- how and why?" (2011); countercomplex.blogspot.com; Chapter 13 of this book; various 256-byte ZX Spectrum intros from Pouet.net
