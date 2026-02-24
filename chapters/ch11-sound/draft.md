# Chapter 11: Sound Architecture -- AY, TurboSound, and Triple AY

> *"The AY chip has three voices. That's not a limitation -- it's a design constraint that shaped an entire musical genre."*

---

The AY-3-8910 is the voice of the ZX Spectrum 128K. General Instrument designed it in 1978 as a Programmable Sound Generator (PSG) -- a single chip that could produce music and sound effects without a dedicated sound CPU. By the time Amstrad put it into the Spectrum 128K in 1986, it was already a proven workhorse: Intellivision, MSX, Atari ST, and dozens of arcade machines all used it or its pin-compatible variants (YM2149 in the Atari ST, AY-3-8912 with fewer I/O ports).

Fourteen registers. Three square-wave tone channels. One noise generator. One envelope generator. That is all you get. Everything you have ever heard in a Spectrum 128K chiptune -- the pumping basslines, the rapid-fire arpeggiated chords, the snappy drums -- comes from programming these fourteen registers fifty times per second.

This chapter takes you from bare register writes to a working music engine. By the end, you will understand exactly how a tracker player puts sound into the AY, and you will have the knowledge to write your own.

---

## 11.1 The AY-3-8910 Register Map

The AY has 14 registers, addressed R0 through R13. On the ZX Spectrum 128K, you access them through two I/O ports:

- **$FFFD** -- Register select (write the register number here first)
- **$BFFD** -- Data write (then write the value here)

Always select the register first, then write the data. This two-step process is fundamental:

```z80
; Write value E to AY register A
ay_write:
    ld   bc, $FFFD
    out  (c), a       ; select register
    ld   b, $BF       ; $BFFD high byte (C stays $FD)
    out  (c), e       ; write data
    ret
```

Note the trick: we only change the high byte of BC between the two OUT instructions. The low byte $FD stays in C throughout. This saves loading a full 16-bit value twice.

### Complete Register Table

| Reg | Name | Bits | Description |
|-----|------|------|-------------|
| R0  | Tone A period, low | 8 | Lower 8 bits of channel A tone period |
| R1  | Tone A period, high | 4 | Upper 4 bits of channel A tone period |
| R2  | Tone B period, low | 8 | Lower 8 bits of channel B tone period |
| R3  | Tone B period, high | 4 | Upper 4 bits of channel B tone period |
| R4  | Tone C period, low | 8 | Lower 8 bits of channel C tone period |
| R5  | Tone C period, high | 4 | Upper 4 bits of channel C tone period |
| R6  | Noise period | 5 | Noise generator period (0-31) |
| R7  | Mixer / I/O enable | 8 | Tone and noise enable per channel + I/O |
| R8  | Volume A | 5 | Channel A volume (0-15) or envelope mode |
| R9  | Volume B | 5 | Channel B volume (0-15) or envelope mode |
| R10 | Volume C | 5 | Channel C volume (0-15) or envelope mode |
| R11 | Envelope period, low | 8 | Lower 8 bits of envelope period |
| R12 | Envelope period, high | 8 | Upper 8 bits of envelope period |
| R13 | Envelope shape | 4 | Envelope waveform shape (0-15) |

<!-- figure: ch11_ay_registers -->
![AY-3-8910 register map](illustrations/output/ch11_ay_registers.png)

### Tone Channels (R0-R5): How Pitch Works

Each of the three tone channels produces a square wave. The frequency is controlled by a 12-bit period value split across two registers:

```
Frequency = AY_clock / (16 x period)
```

On the Spectrum 128K, the AY clock is 1.7734 MHz (half the CPU clock of 3.5469 MHz). So for middle C (approximately 262 Hz):

```
period = 1,773,400 / (16 x 262) = 423
```

The 12-bit period gives a range from 1 (110,837 Hz -- inaudible ultrasonic) to 4095 (27 Hz -- a deep bass rumble). Here is a practical note table for octave 4:

| Note | Frequency (Hz) | Period (decimal) | R_LO | R_HI |
|------|----------------|-------------------|------|------|
| C4   | 261.6 | 424 | $A8 | $01 |
| C#4  | 277.2 | 400 | $90 | $01 |
| D4   | 293.7 | 378 | $7A | $01 |
| D#4  | 311.1 | 357 | $65 | $01 |
| E4   | 329.6 | 337 | $51 | $01 |
| F4   | 349.2 | 318 | $3E | $01 |
| F#4  | 370.0 | 300 | $2C | $01 |
| G4   | 392.0 | 283 | $1B | $01 |
| G#4  | 415.3 | 267 | $0B | $01 |
| A4   | 440.0 | 252 | $FC | $00 |
| A#4  | 466.2 | 238 | $EE | $00 |
| B4   | 493.9 | 225 | $E1 | $00 |
| C5   | 523.3 | 212 | $D4 | $00 |

To go up one octave, halve the period. To go down, double it. The full note table for all useful octaves lives in Appendix G.

### The Noise Generator (R6)

Register R6 controls a single noise generator shared by all three channels. The 5-bit value (0-31) sets the noise "pitch" -- lower values produce higher, hissier noise; higher values produce lower, rougher noise. The noise generator produces pseudo-random output using a 17-bit linear feedback shift register.

Useful ranges:
- **0-5**: High hiss (hi-hat, cymbal)
- **6-12**: Mid noise (snare body)
- **13-20**: Low rumble (explosion)
- **21-31**: Very low (wind, thunder)

### R7: The Mixer -- The Most Important Register

Register R7 is the heart of the AY. Six bits control which channels receive tone, noise, or both. Two more bits control the I/O port direction (irrelevant for sound, leave them as inputs = 1).

```
Bit 7: I/O port B direction (1 = input)
Bit 6: I/O port A direction (1 = input)
Bit 5: Noise C enable (0 = ON, 1 = off)
Bit 4: Noise B enable (0 = ON, 1 = off)
Bit 3: Noise A enable (0 = ON, 1 = off)
Bit 2: Tone C enable  (0 = ON, 1 = off)
Bit 1: Tone B enable  (0 = ON, 1 = off)
Bit 0: Tone A enable  (0 = ON, 1 = off)
```

**The confusing part: 0 means ON.** This trips up everyone the first time. The AY uses active-low logic for the mixer enables. A cleared bit enables the corresponding source.

Here is a table of useful mixer combinations:

| Value | Binary (NcNbNa TcTbTa) | Effect |
|-------|------------------------|--------|
| $38   | `111 000` | All three tones on, no noise |
| $3E   | `111 110` | Tone A only |
| $3D   | `111 101` | Tone B only |
| $3B   | `111 011` | Tone C only |
| $36   | `110 110` | Tone A + Noise A |
| $07   | `000 111` | All three noise, no tones |
| $30   | `110 000` | Tones A+B+C, Noise A |
| $00   | `000 000` | Everything on (cacophony) |
| $3F   | `111 111` | Everything off (silence) |

A common pattern for music: tones A+B for melody and harmony, tone C + noise C for drums:

```
; Mixer: tone A on, tone B on, tone C on, noise C on
; Binary: 10 0 000 = noise C on + all tones on
; = $28
ld   a, R_MIXER
ld   e, $28
call ay_write
```

### Volume Registers (R8-R10)

Each channel has a 4-bit volume control (0-15, where 15 is loudest). But bit 4 is special: setting it switches that channel to **envelope mode**, where the volume is controlled automatically by the envelope generator instead of the fixed value.

```
Bit 4: 1 = use envelope generator, 0 = use bits 3-0
Bits 3-0: Fixed volume level (0-15)
```

The volume curve is logarithmic on a real AY-3-8910 (each step is approximately 1.5 dB) but varies between chip revisions and clones. The YM2149 has a different volume curve, which is why the same tune sounds subtly different on an Atari ST versus a Spectrum.

### Envelope Generator (R11-R13)

The AY has one envelope generator -- shared across all channels that use it. It automatically modulates the volume according to a repeating waveform.

**R11-R12: Envelope Period** -- A 16-bit value controlling the envelope speed:

```
Envelope_frequency = AY_clock / (256 x period)
```

At period = 1, the envelope cycles at about 6,927 Hz. At period = 65535, it cycles at roughly 0.11 Hz -- about once every 9 seconds.

**R13: Envelope Shape** -- Four bits select the waveform. Although 4 bits allow 16 values, only 10 shapes are unique:

| Value | Shape | Description |
|-------|-------|-------------|
| $00-$03 | `\___` | Single decay, then silent. (All four are identical.) |
| $04-$07 | `/___` | Single attack, then silent. (All four are identical.) |
| $08 | `\\\\` | Repeating sawtooth down. |
| $09 | `\___` | Single decay, then silent. (Same as $00.) |
| $0A | `\/\/` | Repeating triangle (decay-attack). |
| $0B | `\'''` | Single decay, then hold at max. |
| $0C | `////` | Repeating sawtooth up. |
| $0D | `/'''` | Single attack, then hold at max. |
| $0E | `/\/\` | Repeating triangle (attack-decay). |
| $0F | `/___` | Single attack, then silent. (Same as $04.) |

Waveform diagrams (volume over time):

```
$00-$03, $09:  |\        $04-$07, $0F:    /|
               | \                        / |
               |  \___                   /  |___

$08: |\  |\  |\            $0C:   /|  /|  /|
     | \ | \ | \                 / | / | / |
     |  \| \| \|                /  |/  |/  |

$0A: |\  /\  /\            $0E:   /\  /\  /\
     | \/  \/  \                 /  \/  \/  \/
     |          |               |

$0B: |\                    $0D:    /|
     | \                         / |
     |  ''''''''                /  |''''''''
```

<!-- figure: ch11_envelope_shapes -->
![AY envelope shape waveforms](illustrations/output/ch11_envelope_shapes.png)

**Key insight:** Writing to R13 *restarts* the envelope from the beginning. This is crucial for bass techniques -- you can trigger a new envelope cycle at any time by writing to R13, even with the same value.

---

## 11.2 Chiptune Techniques on 3 Channels

Three channels is not a lot. A real band has bass, drums, melody, and harmony as a minimum. Chiptune composers developed ingenious tricks to create the illusion of more:

### Arpeggios: Fake Chords

An arpeggio rapidly cycles through the notes of a chord -- one note per frame. At 50 Hz (PAL), cycling through C4, E4, and G4 every frame produces an effect that the ear perceives as a C major chord, even though only one note sounds at any instant.

```z80
; Arpeggio: cycle C-E-G on channel A every frame
; Called once per frame from the interrupt handler
arpeggio:
    ld   a, (arp_pos)
    inc  a
    cp   3
    jr   nz, .no_wrap
    xor  a
.no_wrap:
    ld   (arp_pos), a

    ; Index into note table
    ld   hl, arp_notes
    add  a, a            ; x2 (each entry is a 16-bit period)
    ld   e, a
    ld   d, 0
    add  hl, de
    ld   e, (hl)
    inc  hl
    ld   d, (hl)

    ; Write period to channel A
    ld   a, R_TONE_A_LO
    call ay_write_de_lo
    ld   a, R_TONE_A_HI
    call ay_write_de_hi
    ret

arp_pos:   DB 0
arp_notes: DW 424, 337, 283    ; C4, E4, G4
```

In a tracker, arpeggios are notated as effects applied to notes. Vortex Tracker II uses ornament tables that specify per-tick semitone offsets.

### Buzz-Bass: The Envelope Trick

Here is the most distinctive chiptune bass sound: the "buzz." It works by abusing the envelope generator. Set the envelope to a short repeating sawtooth ($08 or $0C), set the envelope period to match the desired bass note frequency, and restart the envelope every frame. The result is a buzzing, thick bass tone that sounds nothing like a simple square wave.

```z80
; Buzz-bass: play bass note using envelope generator
; DE = envelope period for desired note
buzz_bass:
    ; Set envelope period
    ld   a, R_ENV_LO
    call ay_write_de_lo
    ld   a, R_ENV_HI
    call ay_write_de_hi

    ; Set envelope shape to repeating sawtooth down
    ; Writing R13 restarts the envelope
    ld   a, R_ENV_SHAPE
    ld   e, $08          ; \\\\  repeating sawtooth down
    call ay_write

    ; Set channel volume to envelope mode (bit 4 = 1)
    ld   a, R_VOL_C
    ld   e, $10          ; bit 4 set = use envelope
    call ay_write
    ret
```

The envelope period for a given bass note is:

```
envelope_period = AY_clock / (256 x desired_frequency)
```

For a bass C2 (65.4 Hz): period = 1,773,400 / (256 x 65.4) = 106.

The buzz-bass gives you a bass instrument that sounds fundamentally different from the tone channels, effectively adding a fourth voice to your arrangement.

### The Period Alignment Problem

There is a catch with buzz-bass that equal-tempered note tables hide from you. Look at the formula again:

```
tone_period    = AY_clock / (16 x frequency)
envelope_period = tone_period / 16
```

For the buzz to sound clean, the envelope period must be *exactly* `tone_period / 16`. But integer division truncates. If the tone period is not divisible by 16, the envelope period has a rounding error -- and the envelope waveform drifts against the tone, producing audible beating.

Check our standard table. Octave 4:

| Note | Period | Period mod 16 | Envelope = Period / 16 | Error? |
|------|--------|---------------|------------------------|--------|
| C4   | 424    | 8             | 26 (should be 26.5)    | Yes    |
| D4   | 378    | 10            | 23 (should be 23.625)  | Yes    |
| E4   | 337    | 1             | 21 (should be 21.0625) | Yes    |
| F4   | 318    | 14            | 19 (should be 19.875)  | Yes    |
| G4   | 283    | 11            | 17 (should be 17.6875) | Yes    |
| A4   | 252    | 12            | 15 (should be 15.75)   | Yes    |
| B4   | 225    | 1             | 14 (should be 14.0625) | Yes    |

Not a single clean division! Every note in the equal-tempered scale produces a slightly detuned envelope. For short percussive buzz sounds the beating is masked, but for sustained bass notes it creates an unpleasant warble.

<!-- figure: ch11_te_alignment -->
![Tone + Envelope Phase Alignment: clean T+E with period divisible by 16 (top) vs beating T+E with rounding error (bottom)](illustrations/output/ch11_te_alignment.png)

### Natural Tuning: Table #5

In June 2001, Ivan Roshin published "Частотная таблица с нулевой погрешностью" (A Frequency Table with Zero Error), arriving at the same conclusion that centuries of music theory had already established: replace equal temperament with *just intonation* -- integer-ratio intervals that the AY hardware can divide cleanly.

The natural scale for C major / A minor uses these intervals:

```
C [9/8] D [10/9] E [16/15] F [9/8] G [10/9] A [9/8] B [16/15] C
```

This gives pure fifths (3:2 ratio) for C--G, E--B, A--E. Chromatic notes (sharps/flats) are calculated with the 16/15 ratio.

<!-- figure: ch11_just_intonation -->
![Just Intonation: interval structure of the natural scale with period divisibility table for buzz-bass](illustrations/output/ch11_just_intonation.png)

The resulting periods, computed for a *non-standard* AY clock of 1,520,640 Hz:

```z80
; Table #5: Natural tuning for AY clock = 1,520,640 Hz
; 96 notes (8 octaves), C major / A minor
; Ivan Roshin (concept, 2001), oisee/siril (VTi implementation, 2009)
natural_note_table:
    ; Octave 1: every period divisible by 16!
    DW 2880, 2700, 2560, 2400, 2304, 2160
    DW 2025, 1920, 1800, 1728, 1620, 1536
    ; Octave 2
    DW 1440, 1350, 1280, 1200, 1152, 1080
    DW 1013,  960,  900,  864,  810,  768
    ; Octave 3
    DW  720,  675,  640,  600,  576,  540
    DW  506,  480,  450,  432,  405,  384
    ; Octave 4
    DW  360,  338,  320,  300,  288,  270
    DW  253,  240,  225,  216,  203,  192
    ; Octave 5
    DW  180,  169,  160,  150,  144,  135
    DW  127,  120,  113,  108,  101,   96
    ; Octave 6
    DW   90,   84,   80,   75,   72,   68
    DW   63,   60,   56,   54,   51,   48
    ; Octave 7
    DW   45,   42,   40,   38,   36,   34
    DW   32,   30,   28,   27,   25,   24
    ; Octave 8
    DW   23,   21,   20,   19,   18,   17
    DW   16,   15,   14,   14,   13,   12
```

The key insight is that most main-scale periods are now divisible by 16. Here is octave 2 -- the bass range that matters most for buzz:

| Note | Period | mod 16 | Envelope = Period/16 | Clean? |
|------|--------|--------|----------------------|--------|
| C2   | 1440   | 0      | 90                   | Yes |
| C#2  | 1350   | 6      | 84.375 → 84          | No  |
| D2   | 1280   | 0      | 80                   | Yes |
| D#2  | 1200   | 0      | 75                   | Yes |
| E2   | 1152   | 0      | 72                   | Yes |
| F2   | 1080   | 0      | 67.5 → 68            | ~   |
| F#2  | 1013   | 5      | 63.3 → 63            | No  |
| G2   |  960   | 0      | 60                   | Yes |
| G#2  |  900   | 4      | 56.25 → 56           | No  |
| A2   |  864   | 0      | 54                   | Yes |
| A#2  |  810   | 2      | 50.6 → 51            | No  |
| B2   |  768   | 0      | 48                   | Yes |

Seven of twelve notes divide cleanly -- all the natural notes of C major. Compare to the equal-tempered table where *none* do. On those seven notes the envelope and tone generators lock in phase, and the buzz-bass sounds pure.

**The tradeoff:** this table is only correct for C major / A minor. To play in other keys, you change the AY clock frequency:

| Key | Chip Frequency (Hz) |
|-----|---------------------|
| C/Am    | 1,520,640 |
| C#/A#m  | 1,611,062 |
| D/Bm    | 1,706,861 |
| D#/Cm   | 1,808,356 |
| E/C#m   | 1,915,886 |
| F/Dm    | 2,029,811 |
| F#/D#m  | 2,150,510 |
| G/Em    | 2,278,386 |
| G#/Fm   | 2,413,866 |
| A/F#m   | 2,557,401 |
| A#/Gm   | 2,709,472 |
| B/G#m   | 2,870,586 |

On real hardware the AY clock is fixed, so you cannot actually change keys at runtime. But in an emulator or tracker like Vortex Tracker II, the "chip frequency" is a setting. This is exactly what the Vortex Tracker Improved (VTi) modification by oisee did in 2009: it added Table #5 (the fifth table, index 4 counting from zero) with these natural periods, plus a per-module chip frequency setting that selects the key.

The autosiril MIDI-to-PT3 converter defaults to Table #5 precisely because of these clean envelope ratios -- most converted tracks use buzz-bass extensively, and the natural tuning eliminates beating.

**In practice:** if you are writing a tracker module that relies heavily on buzz-bass, consider composing in C/Am with Table #5. The envelopes will lock perfectly to the tone. If you need a different key, either transpose the chip frequency (tracker-side) or accept the small rounding errors of equal temperament. For short percussive buzz sounds, the difference is inaudible; for sustained bass drones, it is very noticeable.

### Drum Synthesis

With only one noise generator, drums need to share. The standard approach:

**Snare drum:** Noise channel + rapid envelope decay.

```z80
; Snare: noise burst with fast decay
drum_snare:
    ; Noise period: mid-range
    ld   a, R_NOISE
    ld   e, 8
    call ay_write

    ; Mixer: enable noise on channel C
    ld   a, R_MIXER
    ld   e, $28          ; tones A+B on, tone C on, noise C on
    call ay_write

    ; Short envelope: fast decay
    ld   a, R_ENV_LO
    ld   e, 200
    call ay_write
    ld   a, R_ENV_HI
    ld   e, 0
    call ay_write

    ; Envelope shape: single decay
    ld   a, R_ENV_SHAPE
    ld   e, $00          ; \___  single decay to silence
    call ay_write

    ; Channel C to envelope mode
    ld   a, R_VOL_C
    ld   e, $10
    call ay_write
    ret
```

**Kick drum:** Rapid tone sweep downward. Set channel C to a low tone period, then increase the period over several frames:

```z80
; Kick: tone sweep down over 4 frames
; Call once per frame while kick_counter > 0
kick_update:
    ld   a, (kick_counter)
    or   a
    ret  z

    dec  a
    ld   (kick_counter), a

    ; Sweep tone down (increase period)
    ld   hl, (kick_period)
    ld   de, 40          ; sweep speed
    add  hl, de
    ld   (kick_period), hl

    ; Write to channel C
    ld   a, R_TONE_C_LO
    ld   e, l
    call ay_write
    ld   a, R_TONE_C_HI
    ld   e, h
    call ay_write
    ret

kick_counter: DB 0
kick_period:  DW 0
```

**Hi-hat:** Very short noise burst, high noise frequency (low R6 value), immediate volume cut after 1-2 frames.

### Ornaments: Per-Frame Modulation

An ornament is a table of per-frame offsets applied to the pitch or volume of a note. Ornaments give life to otherwise static square waves: vibrato, pitch slides, tremolo, attack/decay envelopes -- all accomplished by table lookup.

```z80
; Example ornament: pitch vibrato
; Table of signed semitone offsets, applied once per frame
ornament_vibrato:
    DB 0, 0, 1, 1, 0, 0, -1, -1    ; 8-frame cycle
    DB $80                           ; end marker
```

The player engine applies the ornament offset to the base note's period value each frame, producing smooth modulation.

---

## 11.3 TurboSound: 2 x AY

Pentagon and Scorpion clones introduced TurboSound -- two AY chips in one machine. The second chip is addressed by selecting it through a bit pattern written to port $FFFD before register operations.

### Chip Selection

On the NedoPC TurboSound card (the most common modern design), chip selection works through port $FFFD:

```z80
; Select chip 0 (primary)
ld   bc, $FFFD
ld   a, $FF          ; bit pattern: select chip 0
out  (c), a

; Select chip 1 (secondary)
ld   bc, $FFFD
ld   a, $FE          ; bit pattern: select chip 1
out  (c), a
```

Once a chip is selected, all subsequent register reads and writes via $FFFD/$BFFD go to that chip. In practice, your music engine selects chip 0, updates all its registers, then selects chip 1 and updates its registers.

### 6 Channels, True Stereo

TurboSound doubles everything: 6 tone channels, 2 independent noise generators, 2 independent envelope generators. A typical stereo arrangement:

| Chip | Channels | Stereo | Role |
|------|----------|--------|------|
| Chip 0 | A0, B0, C0 | Left or center | Lead melody, harmony, bass |
| Chip 1 | A1, B1, C1 | Right or center | Counter-melody, pads, drums |

Or mix them for a wide stereo field:
- Bass on both chips (center)
- Lead on chip 0 (left)
- Counter-melody on chip 1 (right)
- Drums split: kick on chip 0, snare/hi-hat on chip 1

What TurboSound changes musically is significant: on a single AY, the composer is constantly making sacrifices. You cannot have a sustained bass note, a lead melody, and a drum hit at the same time without channel-stealing. With TurboSound, you have room. Dedicated bass channel, dedicated drums, and four remaining voices for melody and harmony. The compromise era ends.

### Engine Modification

Adapting a single-AY engine to TurboSound is straightforward. Your interrupt handler becomes:

```z80
music_frame:
    ; Update chip 0
    ld   a, $FF
    ld   bc, $FFFD
    out  (c), a          ; select chip 0
    call update_chip0    ; write 14 registers

    ; Update chip 1
    ld   a, $FE
    ld   bc, $FFFD
    out  (c), a          ; select chip 1
    call update_chip1    ; write 14 registers
    ret
```

The register write loop writes all 14 registers from a buffer in RAM. For two chips, you maintain two 14-byte buffers and blast them out sequentially. Total cost: about 28 OUT instructions, roughly 400 T-states.

---

## 11.4 Triple AY on ZX Spectrum Next

The ZX Spectrum Next takes it further: three AY-compatible sound chips, giving you 9 channels. But the Next's implementation goes beyond simple triplication.

### Enhanced Features

The Next's AY chips include **per-channel stereo panning**. Each channel can be individually panned left, right, or center -- something the original AY never supported. This is controlled through additional Next-specific registers.

The three chips are addressed via Next register $06 (peripheral 2 setting) or through the standard $FFFD port with chip select values.

### 9 Channels: Orchestral Thinking

Nine channels fundamentally change how you approach composition on 8-bit hardware. Instead of clever tricks to simulate complexity, you can think orchestrally:

| Channel | Assignment | Panning |
|---------|-----------|---------|
| Chip 0, A | Bass line | Center |
| Chip 0, B | Rhythm guitar / pad | Left |
| Chip 0, C | Lead melody | Center |
| Chip 1, A | Harmony / counter-melody | Right |
| Chip 1, B | Arpeggio chord | Left |
| Chip 1, C | Percussion: kick + snare | Center |
| Chip 2, A | Hi-hat / cymbal | Right |
| Chip 2, B | Sound effects (reserved) | Center |
| Chip 2, C | Ambient / pad layers | Left |

This is enough for genuinely rich arrangements. You have a dedicated SFX channel that never interrupts the music. You have independent noise generators for layered percussion. You can sustain chords without arpeggios. The AY's character remains -- square waves are still square waves -- but the compositional freedom approaches that of an Amiga MOD tracker with its four sample channels.

---

## 11.5 Music Engine Architecture

A music engine is the code that reads pattern data and writes AY registers at the correct tempo. On the Spectrum, it lives inside the interrupt handler.

### The Interrupt-Driven Player

The ZX Spectrum's IM2 (Interrupt Mode 2) fires once per frame -- every 1/50th of a second on PAL systems. The music engine hooks into this:

```z80
; Setup: install IM2 handler
setup_im2:
    di
    ld   a, $C0          ; interrupt vector table at $C000
    ld   i, a
    im   2

    ; Fill vector table at $C000 with $C1C1
    ; Handler at $C1C1
    ld   hl, $C000
    ld   de, $C001
    ld   bc, 256
    ld   (hl), $C1
    ldir

    ; Place JP at $C1C1
    ld   a, $C3          ; JP opcode
    ld   ($C1C1), a
    ld   hl, isr_handler
    ld   ($C1C2), hl

    ei
    ret

isr_handler:
    push af
    push bc
    push de
    push hl
    ; ... push all registers you use ...

    call music_play      ; <-- the player routine

    ; ... pop all registers ...
    pop  hl
    pop  de
    pop  bc
    pop  af
    ei
    reti
```

### The Player Loop

The player routine, called 50 times per second, does the following:

1. Decrement the current note's duration counter
2. If zero, advance to the next note in the pattern
3. Apply ornaments and effects (arpeggio, vibrato, slide) to each channel
4. Calculate final period and volume for each channel
5. Write all 14 AY registers

A simplified skeleton:

```z80
music_play:
    ; Decrement speed counter
    ld   a, (speed_counter)
    dec  a
    ld   (speed_counter), a
    ret  nz              ; not time for a new row yet

    ; Reset speed counter
    ld   a, (song_speed)
    ld   (speed_counter), a

    ; Process each channel
    ld   ix, channel_a_data
    call process_channel
    ld   ix, channel_b_data
    call process_channel
    ld   ix, channel_c_data
    call process_channel

    ; Write all registers to AY
    call ay_flush_registers
    ret
```

### Frame Budget

Here is the critical question: how many T-states can the music engine consume before it starves the main program?

The frame is 71,680 T-states on Pentagon (69,888 on 48K). The interrupt fires at the start of the frame. If the music player takes 5,000 T-states, the main program has 66,680 left for visuals.

Typical costs:
- **Simple player** (no effects, no ornaments): ~1,500-2,500 T-states
- **Pro Tracker 3 player**: ~3,000-5,000 T-states
- **Full Vortex Tracker II player** with ornaments and effects: ~4,000-7,000 T-states
- **TurboSound player** (2 chips): ~6,000-10,000 T-states

For a demo running a cycle-hungry effect, 7,000 T-states for music is significant -- about 10% of the frame. Plan accordingly.

### Formats and Trackers

The modern standard for AY music on the Spectrum is **Vortex Tracker II** (.pt3 format). It is a cross-platform tracker that runs on Windows and outputs files directly playable by proven Z80 player routines.

| Format | Tracker | Features | Player Size |
|--------|---------|----------|-------------|
| .pt3 | Vortex Tracker II / Pro Tracker 3 | Ornaments, samples, effects | ~1.2-1.8 KB |
| .asc | ASC Sound Master | Simpler, smaller player | ~0.8-1.0 KB |
| .sqt | SQ-Tracker | Compact, good compression | ~0.6-0.8 KB |
| .stc | Sound Tracker | Basic, oldest | ~0.5-0.7 KB |

**The Pipeline:**

1. Compose in Vortex Tracker II on your PC
2. Export as .pt3 file
3. Include the .pt3 player source (Z80 assembly) in your project
4. Include the .pt3 data file as a binary blob
5. Call `music_init` at startup (passing the address of the song data)
6. Call `music_play` from your interrupt handler every frame

```z80
; In your main code:
    ld   hl, song_data
    call music_init

; In your interrupt handler:
    call music_play

; At the end of the binary:
song_data:
    INCBIN "mysong.pt3"
```

This is the standard approach used by virtually every Spectrum 128K demo and game since the early 2000s.

---

## 11.6 Sound Effects System

Games need sound effects, and sound effects need channels. The standard approach is **priority-based channel stealing**: when a sound effect triggers, it temporarily takes over a channel from the music engine, then releases it when the effect finishes.

### Channel Stealing

```z80
; Trigger a sound effect on the SFX channel
; HL = pointer to SFX data table
sfx_trigger:
    ld   (sfx_pointer), hl
    ld   a, 1
    ld   (sfx_active), a
    ld   a, 0
    ld   (sfx_frame), a
    ret

; Called every frame from the interrupt handler, AFTER music_play
sfx_update:
    ld   a, (sfx_active)
    or   a
    ret  z               ; no active SFX

    ; Read current SFX frame data
    ld   hl, (sfx_pointer)
    ld   a, (sfx_frame)
    ld   e, a
    ld   d, 0

    ; Each SFX frame: [tone_lo, tone_hi, noise, volume, mixer_mask]
    ; 5 bytes per frame
    push hl
    ld   b, 5
    call multiply_de_b   ; DE = frame * 5 (or use repeated add)
    pop  hl
    add  hl, de

    ld   a, (hl)
    cp   $FF             ; end marker?
    jr   z, .sfx_done

    ; Override channel C with SFX data
    ld   e, (hl) : inc hl
    ld   a, R_TONE_C_LO
    call ay_write

    ld   e, (hl) : inc hl
    ld   a, R_TONE_C_HI
    call ay_write

    ld   e, (hl) : inc hl
    ld   a, R_NOISE
    call ay_write

    ld   e, (hl) : inc hl
    ld   a, R_VOL_C
    call ay_write

    ; Advance frame counter
    ld   a, (sfx_frame)
    inc  a
    ld   (sfx_frame), a
    ret

.sfx_done:
    xor  a
    ld   (sfx_active), a ; deactivate SFX
    ret
```

### Procedural SFX Tables

Sound effects are defined as tables of per-frame register values. Here are four classic game sounds:

**Explosion:** Noise with decaying volume.

```z80
sfx_explosion:
    ; tone_lo, tone_hi, noise_period, volume, (unused)
    DB 0, 0, 15, 15, 0    ; frame 0: loud low noise
    DB 0, 0, 18, 13, 0    ; frame 1
    DB 0, 0, 20, 11, 0    ; frame 2
    DB 0, 0, 22, 9,  0    ; frame 3
    DB 0, 0, 25, 7,  0    ; frame 4
    DB 0, 0, 28, 5,  0    ; frame 5
    DB 0, 0, 30, 3,  0    ; frame 6
    DB 0, 0, 31, 1,  0    ; frame 7
    DB $FF                 ; end
```

**Laser:** Fast tone sweep downward.

```z80
sfx_laser:
    DB 10, 0, 0, 14, 0    ; frame 0: high tone
    DB 30, 0, 0, 13, 0    ; frame 1: sweeping down
    DB 60, 0, 0, 12, 0    ; frame 2
    DB 100,0, 0, 10, 0    ; frame 3
    DB 160,0, 0, 8,  0    ; frame 4
    DB 240,0, 0, 5,  0    ; frame 5
    DB 200,1, 0, 3,  0    ; frame 6: into low range
    DB $FF                 ; end
```

**Jump:** Short tone sweep upward.

```z80
sfx_jump:
    DB 200,0, 0, 12, 0    ; frame 0: mid tone
    DB 150,0, 0, 11, 0    ; frame 1: rising
    DB 100,0, 0, 10, 0    ; frame 2
    DB 60, 0, 0, 8,  0    ; frame 3: high
    DB 40, 0, 0, 5,  0    ; frame 4
    DB $FF                 ; end
```

**Pickup:** Rapid arpeggio upward.

```z80
sfx_pickup:
    DB $D4,0, 0, 14, 0    ; frame 0: C5
    DB $A8,0, 0, 14, 0    ; frame 1: C4 (wrong dir? no:)
    ; Actually, let's go up:
    DB $FC,0, 0, 14, 0    ; frame 0: A4
    DB $D4,0, 0, 13, 0    ; frame 1: C5
    DB $A0,0, 0, 12, 0    ; frame 2: E5 (approx)
    DB $6A,0, 0, 11, 0    ; frame 3: C6 (approx)
    DB $6A,0, 0, 8,  0    ; frame 4: sustain
    DB $6A,0, 0, 4,  0    ; frame 5: fade
    DB $FF                 ; end
```

---

## 11.7 Putting It Together: The Working Example

The file `chapters/ch11-sound/examples/ay_test.a80` contains a complete, assembling example that demonstrates the fundamentals: initializing the AY, setting the mixer, writing tone periods, and playing a melody. Study it alongside this chapter -- every concept discussed here is exercised in that code.

The key patterns to notice in the example:

1. **Two-step port access**: Select register via $FFFD, then write data via $BFFD.
2. **Mixer configuration**: $3E enables only tone A (binary `111 110` -- remember, 0 = ON).
3. **Note table**: Pre-calculated period values for each pitch.
4. **HALT-based timing**: Each `HALT` waits for one interrupt, giving 50 Hz timing resolution.

To extend this example into a real music player, you would replace the linear melody table with pattern-based data, add ornament processing, and move the playback into an IM2 interrupt handler so the main loop is free for visuals.

---

> ## Sidebar: Beeper -- A Brief History of Impossibility
>
> Before the 128K and its AY chip, the original 48K Spectrum had exactly one bit of audio output. Pin 4 of port $FE. High or low. That is it.
>
> One bit means one square wave at whatever frequency you toggle it. No volume control, no mixing, no hardware help. To play a note, you sit in a tight loop toggling the bit at the right frequency. To play *two* notes, you interleave two toggle loops. To play three, you interleave three. Each additional voice eats CPU time that could be doing something else -- like, say, drawing graphics.
>
> And yet.
>
> Between 2010 and 2015, Shiru (Shiru Otaku) cataloged approximately 30 distinct beeper engines, each using a different technique to extract polyphony from a single bit. The approaches ranged from simple pin-compatible pulse interleaving (2-3 channels) to extraordinary feats of engineering:
>
> - **ZX-16** by Jan Deak: 16-channel polyphony on a single bit. Sixteen. The CPU does nothing but toggle the speaker bit using a carefully timed schedule that approximates the sum of 16 independent waveforms through pulse-density modulation.
>
> - **Octode XL**: 8-channel beeper engine that actually leaves enough CPU for visuals.
>
> - **Rain** by Life on Mars (2016): A full demo running a 9-channel beeper engine *simultaneously with visual effects* on a 48K Spectrum. The entire production -- music and graphics -- runs without an AY chip, without bank switching, without anything beyond the base machine.
>
> These are among the most remarkable engineering achievements in 8-bit computing. They prove that limits are more permeable than they appear. But they are also impractical for general use: most beeper engines consume 50-90% of CPU time, leaving almost nothing for gameplay or effects. The AY chip exists precisely to offload sound generation to dedicated hardware.
>
> We cover beeper engines here as historical context and inspiration. For practical music in your demos and games, the AY is where you should focus your effort.

---

> ## Sidebar: Agon Light 2 -- VDP Sound System
>
> The Agon Light 2 takes a completely different approach to sound. Its audio is generated by the ESP32 co-processor (the VDP), not by a dedicated sound chip. You send VDU commands over the serial link, and the ESP32 synthesizes audio in software.
>
> **Waveforms:** The Agon's sound system offers multiple waveform types per channel -- square, sine, triangle, sawtooth, and noise. This is already more flexible than the AY's square-only tone generators.
>
> **ADSR Envelopes:** Each channel has a fully programmable Attack-Decay-Sustain-Release envelope. No sharing -- every channel gets its own independent envelope, unlike the AY's single shared envelope generator.
>
> **Channel Count:** The VDP audio system supports multiple simultaneous channels (the exact number depends on the firmware version, but typically 8 or more).
>
> **The Trade-off:** The Agon's sound is controlled through VDU byte sequences sent over serial. This means:
> - Higher latency than direct register writes (serial transfer time)
> - Less precise timing (you cannot bit-bang exact T-state-level sync)
> - But much less CPU overhead (the eZ80 just sends commands; the ESP32 does all synthesis)
>
> The paradigm is closer to MIDI than to register-level programming. You tell the VDP "play this note on channel 3 with a sine wave and this ADSR envelope," and it handles the rest. The musical goals are the same -- melody, bass, drums, effects -- but the programming model is fundamentally different. No mixer register, no period calculations, no envelope shape tables. Just commands and parameters.
>
> For cross-platform projects, consider abstracting your sound system behind a common API: `sound_play_note(channel, note, instrument)`. On the Spectrum, the instrument lookup writes AY registers. On the Agon, it sends VDU commands. Same music data, different backends.

---

## 11.8 Practical Exercises

**Exercise 1: Register Explorer.** Write a program that lets you modify any AY register in real time using keyboard input. Display all 14 register values on screen. This is your single most useful debugging tool for sound work.

**Exercise 2: Three-Channel Arrangement.** Compose a simple 16-bar tune using all three channels: melody on A, bass (buzz-bass using envelope) on C, and arpeggiated chords on B. Use the HALT-based timing from the example as a starting point, then refactor it into an IM2-driven player.

**Exercise 3: Drum Kit.** Implement four drum sounds (kick, snare, hi-hat, crash) as procedural SFX tables. Write a simple drum pattern that plays them in sequence. Integrate with the tune from Exercise 2.

**Exercise 4: Vortex Tracker Integration.** Download Vortex Tracker II, compose a short tune, export as .pt3, and integrate the standard .pt3 player into a Spectrum program. Verify it plays correctly in an emulator.

---

## Summary

The AY-3-8910 is deceptively simple: 14 registers, 3 channels, basic waveforms. But the gap between "simple" and "limited" is filled by technique. Arpeggios fake chords. Envelope abuse creates bass. Noise shaping synthesizes drums. Ornaments breathe life into static tones. And when three channels are genuinely not enough, TurboSound doubles them and the Next triples them.

The architecture pattern is consistent across all configurations: an interrupt fires 50 times per second, a player routine reads pattern data and calculates register values, and those values are blasted to the AY in a tight loop. Whether you are writing your own player or integrating Vortex Tracker, the flow is the same. Understanding the registers means understanding the sound.

In the next chapter, we will put this to work: digital drum samples blended with AY playback, frame-accurate synchronization between music and visuals, and the scripting engines that tie a demo together.

---

> **Sources:** Dark "GS Sound System" (Spectrum Expert #01, 1997); Dark "Music" (Spectrum Expert #02, 1998); Shiru "Beeper 20XX" (Hype 2016); Rain file_id.diz; Info Guide #14 ASC Sound Master docs (ZXArt 2024); Vortex Tracker II documentation
