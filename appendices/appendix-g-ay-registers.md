# Appendix G: AY-3-8910 / TurboSound / Triple AY Register Reference

> *"Fourteen registers. Three square-wave tone channels. One noise generator. One envelope generator. That is all you get."*
> -- Chapter 11

---

This appendix is a complete register-level reference for the AY-3-8910 Programmable Sound Generator as used in the ZX Spectrum 128K, TurboSound-equipped clones (Pentagon, Scorpion), and the ZX Spectrum Next's triple-AY configuration. Chapter 11 covers the musical techniques; this appendix is the datasheet you keep open while coding.

All hex values use the `$FF` notation. Binary values use `%10101010`. Clock frequency assumes the PAL Spectrum 128K standard of 1.7734 MHz unless otherwise noted.

---

## I/O Ports on ZX Spectrum 128K

| Port | Direction | Function |
|------|-----------|----------|
| **$FFFD** | Write | Select active register (0-15) |
| **$FFFD** | Read | Read value of currently selected register |
| **$BFFD** | Write | Write data to selected register |

### The Write Sequence

Every AY register write is a two-step operation: select the register, then write the value.

```z80
; Write value E to AY register A
; Clobbers: BC
ay_write:
    ld   bc, $FFFD
    out  (c), a       ; 12T  select register
    ld   b, $BF       ; 7T   BC = $BFFD (C stays $FD)
    out  (c), e       ; 12T  write data
    ret               ;      total: 31T + call overhead
```

The trick: only the high byte of BC changes between the two `OUT` instructions. The low byte `$FD` stays in C throughout. This saves 3 bytes and 10 T-states compared to loading a full 16-bit value twice.

### Reading a Register

```z80
; Read AY register A into A
; Clobbers: BC
ay_read:
    ld   bc, $FFFD
    out  (c), a       ; select register
    in   a, (c)       ; read value
    ret
```

Reading is useful for preserving the mixer state (R7) when modifying individual channel enables.

### Bulk Register Write

For music engines that update all 14 registers per frame, an unrolled loop is fastest:

```z80
; Write all 14 AY registers from a buffer
; HL = pointer to 14-byte register buffer (R0-R13)
ay_flush:
    ld   de, $BFFD         ; D = $BF, E = $FD
    ld   c, e              ; C = $FD (shared low byte)
    ld   b, $FF             ; BC = $FFFD (register select port)
    xor  a                  ; start at R0
.loop:
    out  (c), a             ; select register A
    ld   b, d               ; BC = $BFFD
    outi                    ; write (HL) to port, inc HL, dec B
    ; B is now $BE after OUTI dec, but we reload it anyway
    ld   b, $FF             ; BC = $FFFD
    inc  a
    cp   14
    jr   nz, .loop
    ret
```

---

## Complete Register Map

### Overview

| Reg | Name | Bits Used | R/W | Reset | Description |
|-----|------|-----------|-----|-------|-------------|
| R0  | Tone A period, low | 7-0 | R/W | $00 | Channel A tone period, bits 7-0 |
| R1  | Tone A period, high | 3-0 | R/W | $00 | Channel A tone period, bits 11-8 |
| R2  | Tone B period, low | 7-0 | R/W | $00 | Channel B tone period, bits 7-0 |
| R3  | Tone B period, high | 3-0 | R/W | $00 | Channel B tone period, bits 11-8 |
| R4  | Tone C period, low | 7-0 | R/W | $00 | Channel C tone period, bits 7-0 |
| R5  | Tone C period, high | 3-0 | R/W | $00 | Channel C tone period, bits 11-8 |
| R6  | Noise period | 4-0 | R/W | $00 | Noise generator period (0-31) |
| R7  | Mixer / I/O | 7-0 | R/W | $FF | Tone/noise enable + I/O port direction |
| R8  | Volume A | 4-0 | R/W | $00 | Channel A volume or envelope mode |
| R9  | Volume B | 4-0 | R/W | $00 | Channel B volume or envelope mode |
| R10 | Volume C | 4-0 | R/W | $00 | Channel C volume or envelope mode |
| R11 | Envelope period, low | 7-0 | R/W | $00 | Envelope period, bits 7-0 |
| R12 | Envelope period, high | 7-0 | R/W | $00 | Envelope period, bits 15-8 |
| R13 | Envelope shape | 3-0 | W | -- | Envelope waveform (writing restarts envelope) |
| R14 | I/O Port A | 7-0 | R/W | -- | General-purpose I/O (directly mapped on AY-3-8910) |
| R15 | I/O Port B | 7-0 | R/W | -- | General-purpose I/O (directly mapped on AY-3-8910) |

**Note on R14-R15:** The AY-3-8910 has two 8-bit I/O ports. On the ZX Spectrum 128K, I/O port A (R14) is active -- it reads the keyboard matrix and other hardware signals. R15 (I/O port B) is typically not connected. The AY-3-8912 (used in some clones) has only port A; the AY-3-8913 has no I/O ports at all. For sound programming, R14 and R15 are irrelevant.

---

### R0-R1: Channel A Tone Period (12-bit)

```
R0:  [D7] [D6] [D5] [D4] [D3] [D2] [D1] [D0]   bits 7-0 of period
R1:  [ 0] [ 0] [ 0] [ 0] [D11][D10][ D9][ D8]   bits 11-8 of period
```

- **Range:** 1 to 4095 (12-bit unsigned). Period of 0 behaves as 1 on most implementations.
- **Effect:** Sets the frequency of the square wave on channel A.
- **Formula:** `frequency = 1773400 / (16 * period)` (PAL Spectrum 128K)
- **Practical range:** Period 1 = 110,837 Hz (ultrasonic), period 4095 = 27 Hz (deep bass).

```z80
; Set channel A to middle C (C4, ~262 Hz, period 424)
    ld   a, 0              ; R0 = Tone A low
    ld   e, $A8            ; 424 & $FF = $A8
    call ay_write
    ld   a, 1              ; R1 = Tone A high
    ld   e, $01            ; 424 >> 8 = $01
    call ay_write
```

### R2-R3: Channel B Tone Period (12-bit)

Identical layout to R0-R1, for channel B.

### R4-R5: Channel C Tone Period (12-bit)

Identical layout to R0-R1, for channel C.

---

### R6: Noise Period (5-bit)

```
R6:  [ 0] [ 0] [ 0] [D4] [D3] [D2] [D1] [D0]
```

- **Range:** 0 to 31. A single noise generator shared by all three channels.
- **Effect:** Lower values = higher-pitched noise (hiss). Higher values = lower-pitched, rougher noise.
- **Formula:** `noise_frequency = 1773400 / (16 * period)` (same as tone formula)

| R6 Value | Character | Typical Use |
|----------|-----------|-------------|
| 0-5 | High hiss | Hi-hat, cymbal, metallic ring |
| 6-12 | Mid noise | Snare drum body, white noise |
| 13-20 | Low rumble | Explosion, engine, wind |
| 21-31 | Very low | Thunder, distant rumble |

The noise generator uses a 17-bit linear feedback shift register (LFSR) to produce pseudo-random output. The output is the same for both the AY-3-8910 and YM2149, but the LFSR tap positions differ, producing subtly different noise textures on each chip.

---

### R7: Mixer Control (The Most Important Register)

```
R7:  [IOB] [IOA] [NC] [NB] [NA] [TC] [TB] [TA]
      bit7  bit6  bit5 bit4 bit3 bit2 bit1 bit0
```

| Bit | Name | 0 = | 1 = |
|-----|------|-----|-----|
| 7 | I/O port B direction | Output | **Input** |
| 6 | I/O port A direction | Output | **Input** |
| 5 | Noise C enable | **ON** | Off |
| 4 | Noise B enable | **ON** | Off |
| 3 | Noise A enable | **ON** | Off |
| 2 | Tone C enable | **ON** | Off |
| 1 | Tone B enable | **ON** | Off |
| 0 | Tone A enable | **ON** | Off |

**Critical: 0 means ON.** The mixer uses active-low logic. A cleared bit enables the corresponding source. This is the single most confusing aspect of AY programming.

**Bits 7-6:** Always set to 1 (input mode) on the Spectrum. Do not change these unless you know what you are doing with the I/O ports.

#### Common Mixer Values

| Value | Binary (`NC NB NA TC TB TA`) | Effect |
|-------|------------------------------|--------|
| `$38` | `%00 111 000` | All three tones, no noise |
| `$3E` | `%00 111 110` | Tone A only |
| `$3D` | `%00 111 101` | Tone B only |
| `$3B` | `%00 111 011` | Tone C only |
| `$36` | `%00 110 110` | Tone A + Noise A |
| `$2D` | `%00 101 101` | Tone B + Noise B |
| `$1B` | `%00 011 011` | Tone C + Noise C |
| `$28` | `%00 101 000` | All tones + Noise C (music + drums on C) |
| `$07` | `%00 000 111` | All noise, no tones |
| `$00` | `%00 000 000` | Everything on |
| `$3F` | `%00 111 111` | Everything off (silence) |

**Note:** The binary values above show bits 5-0 only. Bits 7-6 should be `%11` for normal operation (I/O ports as inputs), making e.g. `$38` actually `%11 111 000` = `$F8`. However, on the Spectrum 128K the unused upper bits are ignored by convention, and most code uses the short form. Some engines write the full `$F8` form; both work identically.

```z80
; Enable tone A, tone B, tone C, and noise on C only
; Binary: I/O=11, NC=0(on), NB=1, NA=1, TC=0(on), TB=0(on), TA=0(on)
; = %11 011 000 = $D8 (full form) or $28 (short form, bits 7-6 treated as 0)
    ld   a, 7              ; R7 = Mixer
    ld   e, $28
    call ay_write
```

---

### R8-R10: Volume Registers (5-bit)

```
R8:  [ 0] [ 0] [ 0] [ M] [D3] [D2] [D1] [D0]   Channel A
R9:  [ 0] [ 0] [ 0] [ M] [D3] [D2] [D1] [D0]   Channel B
R10: [ 0] [ 0] [ 0] [ M] [D3] [D2] [D1] [D0]   Channel C
```

| Bit | Function |
|-----|----------|
| 4 (M) | Mode: 0 = use fixed volume (bits 3-0), 1 = use envelope generator |
| 3-0 | Fixed volume level: 0 (silent) to 15 (maximum) |

- **Fixed volume mode** (bit 4 = 0): Bits 3-0 set the channel volume directly. 15 = loudest, 0 = silent. The volume curve is logarithmic on a genuine AY-3-8910 (approximately 1.5 dB per step) but linear on the YM2149.
- **Envelope mode** (bit 4 = 1): The channel's volume is controlled by the envelope generator (R11-R13). Bits 3-0 are ignored. Only one envelope generator exists, shared by all channels in envelope mode.

| Value | Effect |
|-------|--------|
| `$00` | Silent |
| `$08` | Half volume (approximately) |
| `$0F` | Maximum fixed volume |
| `$10` | Envelope mode (any value $10-$1F activates envelope) |

**4-bit DAC trick:** By rapidly writing successive sample values to a volume register (without envelope mode), you can play digitised audio through the AY. At 8 kHz sample rate, this consumes approximately 437 T-states per sample write, leaving almost no CPU for other work. See Chapter 12 for the hybrid drum technique.

```z80
; Set channel A to maximum fixed volume
    ld   a, 8              ; R8 = Volume A
    ld   e, $0F            ; volume 15
    call ay_write

; Switch channel C to envelope mode
    ld   a, 10             ; R10 = Volume C
    ld   e, $10            ; bit 4 set = envelope mode
    call ay_write
```

---

### R11-R12: Envelope Period (16-bit)

```
R11: [D7] [D6] [D5] [D4] [D3] [D2] [D1] [D0]   bits 7-0
R12: [D7] [D6] [D5] [D4] [D3] [D2] [D1] [D0]   bits 15-8
```

- **Range:** 1 to 65535 (16-bit unsigned). Period of 0 behaves as 1.
- **Formula:** `envelope_frequency = 1773400 / (256 * period)`
- **At period = 1:** ~6,927 Hz (one complete envelope cycle in ~144 microseconds)
- **At period = 65535:** ~0.106 Hz (one cycle in ~9.4 seconds)

The envelope period controls how fast the volume ramps up or down according to the shape selected in R13. For buzz-bass, the envelope period replaces the tone period as the pitch control:

```
bass_envelope_period = 1773400 / (256 * desired_frequency)
```

For bass C2 (65.4 Hz): period = 1773400 / (256 * 65.4) = 106.

```z80
; Set envelope period to 106 (bass C2 for buzz-bass)
    ld   a, 11             ; R11 = Envelope period low
    ld   e, 106            ; $6A
    call ay_write
    ld   a, 12             ; R12 = Envelope period high
    ld   e, 0
    call ay_write
```

---

### R13: Envelope Shape (4-bit, Write-Only)

```
R13: [ 0] [ 0] [ 0] [ 0] [CONT] [ATT] [ALT] [HOLD]
                            bit3   bit2  bit1   bit0
```

| Bit | Name | Function |
|-----|------|----------|
| 3 | CONT | Continue: 0 = single-shot (reset to 0 or hold), 1 = repeating |
| 2 | ATT | Attack: 0 = start at max, ramp down, 1 = start at 0, ramp up |
| 1 | ALT | Alternate: 0 = same direction each cycle, 1 = reverse direction |
| 0 | HOLD | Hold: 0 = cycle normally, 1 = hold at final level after first cycle |

**Critical behaviour:** Writing ANY value to R13 immediately restarts the envelope from the beginning of the cycle. This is true even if you write the same value already stored. This restart behaviour is essential for triggering buzz-bass notes and drum sounds.

#### All 16 Shape Values

Although 4 bits allow 16 values, many produce identical output. There are only 10 unique shapes:

| Value | Bits (CONT ATT ALT HOLD) | Shape | Behaviour |
|-------|---------------------------|-------|-----------|
| `$00` | `0 0 0 0` | `\___` | Decay to 0, hold at 0 |
| `$01` | `0 0 0 1` | `\___` | Same as $00 |
| `$02` | `0 0 1 0` | `\___` | Same as $00 |
| `$03` | `0 0 1 1` | `\___` | Same as $00 |
| `$04` | `0 1 0 0` | `/___` | Attack to 15, drop to 0, hold at 0 |
| `$05` | `0 1 0 1` | `/___` | Same as $04 |
| `$06` | `0 1 1 0` | `/___` | Same as $04 |
| `$07` | `0 1 1 1` | `/___` | Same as $04 |
| `$08` | `1 0 0 0` | `\\\\` | Repeating sawtooth down |
| `$09` | `1 0 0 1` | `\___` | Single decay, hold at 0 (same as $00) |
| `$0A` | `1 0 1 0` | `\/\/` | Repeating triangle (down-up) |
| `$0B` | `1 0 1 1` | `\^^^` | Single decay, then hold at max (15) |
| `$0C` | `1 1 0 0` | `////` | Repeating sawtooth up |
| `$0D` | `1 1 0 1` | `/^^^` | Single attack, then hold at max (15) |
| `$0E` | `1 1 1 0` | `/\/\` | Repeating triangle (up-down) |
| `$0F` | `1 1 1 1` | `/___` | Single attack, drop to 0, hold at 0 (same as $04) |

#### Envelope Shape Waveforms

```
$00-$03, $09:              $04-$07, $0F:
 15 |\                      15    /|
    | \                          / |
    |  \                        /  |
    |   \                      /   |
  0 |    \___________        0 /    \___________


$08 (repeating \\\\):      $0C (repeating ////):
 15 |\  |\  |\  |\           15   /|  /|  /|  /|
    | \ | \ | \ | \              / | / | / | / |
    |  \|  \|  \|  \            /  |/  |/  |/  |
  0 |               |        0 |               |


$0A (repeating \/\/):      $0E (repeating /\/\):
 15 |\    /\    /\           15   /\    /\    /\
    | \  /  \  /  \              /  \  /  \  /  \
    |  \/    \/    \            /    \/    \/    \
  0 |               |        0 |               |


$0B (decay, hold max):     $0D (attack, hold max):
 15 |\                       15    /|
    | \  ___________              / |___________
    |  \/                        /  |
  0 |               |        0 |               |
```

#### Practical Envelope Uses

| Shape | Value | Use Case |
|-------|-------|----------|
| `$00` | `\___` | Drum decay: sharp hit that fades to silence |
| `$08` | `\\\\` | Buzz-bass: thick repeating bass tone |
| `$0C` | `////` | Buzz-bass (inverted phase): same pitch, different timbre |
| `$0A` | `\/\/` | Metallic/bell tone (triangle modulation) |
| `$0E` | `/\/\` | Metallic/bell tone (inverted triangle) |
| `$0D` | `/^^^` | Fade-in: volume rises to max and holds |

---

## Tone Period to Frequency Conversion

### Formula

```
frequency = AY_clock / (16 * period)
period    = AY_clock / (16 * frequency)
```

### AY Clock by Platform

| Platform | AY Clock | CPU Clock | Relationship |
|----------|----------|-----------|-------------|
| ZX Spectrum 128K (PAL) | 1,773,400 Hz | 3,546,900 Hz | AY = CPU / 2 |
| ZX Spectrum 128K (NTSC) | 1,789,772 Hz | 3,579,545 Hz | AY = CPU / 2 |
| Pentagon 128 | 1,750,000 Hz | 3,500,000 Hz | AY = CPU / 2 |
| Amstrad CPC | 1,000,000 Hz | 4,000,000 Hz | AY = CPU / 4 |
| MSX | 1,789,772 Hz | 3,579,545 Hz | AY = CPU / 2 |
| Atari ST (YM2149) | 2,000,000 Hz | 8,000,000 Hz | YM = CPU / 4 |
| ZX Spectrum Next | 1,773,400 Hz | varies | Same as 128K |

**Practical consequence:** The same period value produces slightly different pitches on different platforms. A tune composed on Pentagon (1.75 MHz) will sound fractionally sharp on a Spectrum 128K (1.7734 MHz). For most musical purposes, the difference is inaudible.

### Complete Note Frequency Table

All period values calculated for AY clock = 1,773,400 Hz (PAL Spectrum 128K).

Octaves 1-2 cover the bass range (buzz-bass territory). Octaves 3-6 are the main melodic range. Octaves 7-8 are high-pitched and increasingly inaccurate due to integer rounding.

#### Octave 1 (Deep Bass)

| Note | Freq (Hz) | Period | R_LO | R_HI |
|------|-----------|--------|------|------|
| C-1  | 32.70 | 3390 | $3E | $0D |
| C#1  | 34.65 | 3199 | $7F | $0C |
| D-1  | 36.71 | 3019 | $CB | $0B |
| D#1  | 38.89 | 2850 | $22 | $0B |
| E-1  | 41.20 | 2690 | $82 | $0A |
| F-1  | 43.65 | 2539 | $EB | $09 |
| F#1  | 46.25 | 2396 | $5C | $09 |
| G-1  | 49.00 | 2262 | $D6 | $08 |
| G#1  | 51.91 | 2135 | $57 | $08 |
| A-1  | 55.00 | 2015 | $DF | $07 |
| A#1  | 58.27 | 1902 | $6E | $07 |
| B-1  | 61.74 | 1795 | $03 | $07 |

#### Octave 2 (Bass)

| Note | Freq (Hz) | Period | R_LO | R_HI |
|------|-----------|--------|------|------|
| C-2  | 65.41 | 1695 | $9F | $06 |
| C#2  | 69.30 | 1599 | $3F | $06 |
| D-2  | 73.42 | 1510 | $E6 | $05 |
| D#2  | 77.78 | 1425 | $91 | $05 |
| E-2  | 82.41 | 1345 | $41 | $05 |
| F-2  | 87.31 | 1270 | $F6 | $04 |
| F#2  | 92.50 | 1198 | $AE | $04 |
| G-2  | 98.00 | 1131 | $6B | $04 |
| G#2  | 103.83 | 1067 | $2B | $04 |
| A-2  | 110.00 | 1008 | $F0 | $03 |
| A#2  | 116.54 | 951  | $B7 | $03 |
| B-2  | 123.47 | 897  | $81 | $03 |

#### Octave 3

| Note | Freq (Hz) | Period | R_LO | R_HI |
|------|-----------|--------|------|------|
| C-3  | 130.81 | 847 | $4F | $03 |
| C#3  | 138.59 | 800 | $20 | $03 |
| D-3  | 146.83 | 755 | $F3 | $02 |
| D#3  | 155.56 | 713 | $C9 | $02 |
| E-3  | 164.81 | 673 | $A1 | $02 |
| F-3  | 174.61 | 635 | $7B | $02 |
| F#3  | 185.00 | 599 | $57 | $02 |
| G-3  | 196.00 | 566 | $36 | $02 |
| G#3  | 207.65 | 534 | $16 | $02 |
| A-3  | 220.00 | 504 | $F8 | $01 |
| A#3  | 233.08 | 475 | $DB | $01 |
| B-3  | 246.94 | 449 | $C1 | $01 |

#### Octave 4 (Middle Octave)

| Note | Freq (Hz) | Period | R_LO | R_HI |
|------|-----------|--------|------|------|
| C-4  | 261.63 | 424 | $A8 | $01 |
| C#4  | 277.18 | 400 | $90 | $01 |
| D-4  | 293.66 | 378 | $7A | $01 |
| D#4  | 311.13 | 357 | $65 | $01 |
| E-4  | 329.63 | 337 | $51 | $01 |
| F-4  | 349.23 | 318 | $3E | $01 |
| F#4  | 369.99 | 300 | $2C | $01 |
| G-4  | 392.00 | 283 | $1B | $01 |
| G#4  | 415.30 | 267 | $0B | $01 |
| A-4  | 440.00 | 252 | $FC | $00 |
| A#4  | 466.16 | 238 | $EE | $00 |
| B-4  | 493.88 | 225 | $E1 | $00 |

#### Octave 5

| Note | Freq (Hz) | Period | R_LO | R_HI |
|------|-----------|--------|------|------|
| C-5  | 523.25 | 212 | $D4 | $00 |
| C#5  | 554.37 | 200 | $C8 | $00 |
| D-5  | 587.33 | 189 | $BD | $00 |
| D#5  | 622.25 | 178 | $B2 | $00 |
| E-5  | 659.26 | 168 | $A8 | $00 |
| F-5  | 698.46 | 159 | $9F | $00 |
| F#5  | 739.99 | 150 | $96 | $00 |
| G-5  | 783.99 | 142 | $8E | $00 |
| G#5  | 830.61 | 134 | $86 | $00 |
| A-5  | 880.00 | 126 | $7E | $00 |
| A#5  | 932.33 | 119 | $77 | $00 |
| B-5  | 987.77 | 112 | $70 | $00 |

#### Octave 6

| Note | Freq (Hz) | Period | R_LO | R_HI |
|------|-----------|--------|------|------|
| C-6  | 1046.50 | 106 | $6A | $00 |
| C#6  | 1108.73 | 100 | $64 | $00 |
| D-6  | 1174.66 | 94  | $5E | $00 |
| D#6  | 1244.51 | 89  | $59 | $00 |
| E-6  | 1318.51 | 84  | $54 | $00 |
| F-6  | 1396.91 | 79  | $4F | $00 |
| F#6  | 1479.98 | 75  | $4B | $00 |
| G-6  | 1567.98 | 71  | $47 | $00 |
| G#6  | 1661.22 | 67  | $43 | $00 |
| A-6  | 1760.00 | 63  | $3F | $00 |
| A#6  | 1864.66 | 59  | $3B | $00 |
| B-6  | 1975.53 | 56  | $38 | $00 |

#### Octave 7 (High)

| Note | Freq (Hz) | Period | R_LO | R_HI |
|------|-----------|--------|------|------|
| C-7  | 2093.00 | 53 | $35 | $00 |
| C#7  | 2217.46 | 50 | $32 | $00 |
| D-7  | 2349.32 | 47 | $2F | $00 |
| D#7  | 2489.02 | 45 | $2D | $00 |
| E-7  | 2637.02 | 42 | $2A | $00 |
| F-7  | 2793.83 | 40 | $28 | $00 |
| F#7  | 2959.96 | 37 | $25 | $00 |
| G-7  | 3135.96 | 35 | $23 | $00 |
| G#7  | 3322.44 | 33 | $21 | $00 |
| A-7  | 3520.00 | 31 | $1F | $00 |
| A#7  | 3729.31 | 30 | $1E | $00 |
| B-7  | 3951.07 | 28 | $1C | $00 |

#### Octave 8 (Very High -- Limited Accuracy)

| Note | Freq (Hz) | Period | R_LO | R_HI | Actual Freq | Error (cents) |
|------|-----------|--------|------|------|-------------|---------------|
| C-8  | 4186.01 | 26 | $1A | $00 | 4264.23 | +32 |
| C#8  | 4434.92 | 25 | $19 | $00 | 4433.50 | -1 |
| D-8  | 4698.63 | 24 | $18 | $00 | 4618.23 | -30 |
| D#8  | 4978.03 | 22 | $16 | $00 | 5038.07 | +21 |
| E-8  | 5274.04 | 21 | $15 | $00 | 5278.27 | +1 |
| F-8  | 5587.65 | 20 | $14 | $00 | 5541.88 | -14 |
| F#8  | 5919.91 | 19 | $13 | $00 | 5833.55 | -26 |
| G-8  | 6271.93 | 18 | $12 | $00 | 6158.75 | -32 |

**Note:** Above octave 6, integer rounding of the period value produces increasingly audible pitch errors. The "Actual Freq" and "Error" columns for octave 8 show the real output frequency and deviation in cents. For high notes, fine-tuning is not possible -- the resolution is simply too coarse.

### Compact Note Table for Z80 Code

Most tracker engines store the period table as 16-bit words. Here is a practical 96-note table (octaves 1-8) for inclusion in assembly source:

```z80
; AY note period table: 96 notes, C-1 to B-8
; Each entry is a 16-bit period value (low byte first)
; Index = (octave * 12) + semitone, where C=0, C#=1, ..., B=11
note_table:
    ; Octave 1
    DW 3390, 3199, 3019, 2850, 2690, 2539
    DW 2396, 2262, 2135, 2015, 1902, 1795
    ; Octave 2
    DW 1695, 1599, 1510, 1425, 1345, 1270
    DW 1198, 1131, 1067, 1008,  951,  897
    ; Octave 3
    DW  847,  800,  755,  713,  673,  635
    DW  599,  566,  534,  504,  475,  449
    ; Octave 4
    DW  424,  400,  378,  357,  337,  318
    DW  300,  283,  267,  252,  238,  225
    ; Octave 5
    DW  212,  200,  189,  178,  168,  159
    DW  150,  142,  134,  126,  119,  112
    ; Octave 6
    DW  106,  100,   94,   89,   84,   79
    DW   75,   71,   67,   63,   59,   56
    ; Octave 7
    DW   53,   50,   47,   45,   42,   40
    DW   37,   35,   33,   31,   30,   28
    ; Octave 8
    DW   26,   25,   24,   22,   21,   20
    DW   19,   18,   17,   16,   15,   14
```

```z80
; Look up note period: A = note number (0-95)
; Returns DE = period value
; Clobbers: HL
get_note_period:
    ld   h, 0
    ld   l, a
    add  hl, hl           ; HL = note * 2 (word index)
    ld   de, note_table
    add  hl, de
    ld   e, (hl)
    inc  hl
    ld   d, (hl)          ; DE = period
    ret
```

### Table #5: Natural Tuning (Just Intonation)

The standard note table above uses equal temperament (12-TET) -- every semitone is the 12th root of 2 apart. This works well for tone channels, but creates a problem for **buzz-bass (T+E)**: since `envelope_period = tone_period / 16`, any tone period not divisible by 16 introduces a rounding error. The envelope drifts against the tone, producing audible beating on sustained bass notes.

Ivan Roshin's "Frequency Table with Zero Error" (2001) and oisee's VTi implementation (2009) solve this by using **just intonation** -- integer-ratio intervals for C major / A minor:

```
C [9/8] D [10/9] E [16/15] F [9/8] G [10/9] A [9/8] B [16/15] C
```

This produces pure fifths (C--G, E--B, A--E at exact 3:2) and, critically, periods where most main-scale notes divide evenly by 16.

**AY clock: 1,520,640 Hz** (non-standard; select per-key frequency below):

```z80
; Table #5: Natural tuning note table
; 96 notes, C-1 to B-8, for AY clock = 1,520,640 Hz
; C major / A minor only; other keys via chip frequency change
natural_note_table:
    ; Octave 1
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

**Period divisibility check (Octave 2, bass range):**

| Note | Period | mod 16 | Env Period | Clean T+E? |
|------|--------|--------|------------|------------|
| C2   | 1440   | 0      | 90         | Yes |
| C#2  | 1350   | 6      | 84         | No  |
| D2   | 1280   | 0      | 80         | Yes |
| D#2  | 1200   | 0      | 75         | Yes |
| E2   | 1152   | 0      | 72         | Yes |
| F2   | 1080   | 0      | 67         | ~   |
| F#2  | 1013   | 5      | 63         | No  |
| G2   | 960    | 0      | 60         | Yes |
| G#2  | 900    | 4      | 56         | No  |
| A2   | 864    | 0      | 54         | Yes |
| A#2  | 810    | 2      | 50         | No  |
| B2   | 768    | 0      | 48         | Yes |

Seven of twelve notes (all natural notes of C major) divide cleanly -- compared to *zero* in the equal-tempered table.

**Transposition via chip frequency:** since the table is fixed to C/Am, other keys require a different AY clock. Each step multiplies by 2^(1/12):

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

On hardware the AY clock is fixed; in trackers (Vortex Tracker II/Improved) and emulators, this is a per-module setting. Table #5 is the default for the autosiril MIDI-to-PT3 converter because most converted tracks use buzz-bass heavily. See Chapter 11 for a detailed explanation of the T+E alignment problem.

---

## TurboSound: 2 x AY

TurboSound is a hardware modification adding a second AY chip, giving 6 tone channels, 2 noise generators, and 2 envelope generators. The most common modern implementation is the NedoPC TurboSound card.

### Chip Selection

Both AY chips share the same I/O ports ($FFFD/$BFFD). A chip select value written to $FFFD switches all subsequent register operations to the selected chip.

| Chip Select Value | Target |
|-------------------|--------|
| `$FF` | Chip 0 (primary / original AY) |
| `$FE` | Chip 1 (secondary AY) |

```z80
; Select chip 0 (primary)
    ld   bc, $FFFD
    ld   a, $FF
    out  (c), a          ; all subsequent R/W goes to chip 0

; Select chip 1 (secondary)
    ld   bc, $FFFD
    ld   a, $FE
    out  (c), a          ; all subsequent R/W goes to chip 1
```

**Important:** The chip select persists until changed. After selecting chip 1, all register operations -- including reads -- target chip 1. Always explicitly select the chip before any register access in your engine.

### TurboSound Engine Architecture

A typical TurboSound music engine maintains two 14-byte register buffers and writes them sequentially:

```z80
; Update both AY chips -- called once per frame from ISR
ts_update:
    ; --- Chip 0 ---
    ld   a, $FF
    ld   bc, $FFFD
    out  (c), a               ; select chip 0
    ld   hl, ay0_regs         ; 14-byte buffer for chip 0
    call ay_flush              ; write all 14 registers

    ; --- Chip 1 ---
    ld   a, $FE
    ld   bc, $FFFD
    out  (c), a               ; select chip 1
    ld   hl, ay1_regs         ; 14-byte buffer for chip 1
    call ay_flush              ; write all 14 registers
    ret

ay0_regs: DS 14               ; chip 0 register shadow
ay1_regs: DS 14               ; chip 1 register shadow
```

Total cost: approximately 28 OUT instructions, roughly 700-800 T-states including overhead. This is about 1% of a frame budget -- negligible.

### Stereo Configuration

TurboSound enables true stereo. The two chips can be hard-panned or mixed:

| Configuration | Chip 0 (Left) | Chip 1 (Right) | Character |
|---------------|---------------|-----------------|-----------|
| **Wide stereo** | Lead, bass (A0+B0), drums (C0) | Counter-melody (A1+B1), pads (C1) | Spacious, concert-like |
| **Centered bass** | Bass on C0 + C1 (same data) | Lead on A0, harmony on A1 | Solid low end |
| **Split drums** | Kick (C0) | Snare + hi-hat (C1) | Punchy, wide percussion |

Each chip has its own independent noise generator and envelope generator. This means you can run buzz-bass on chip 0 and a completely independent envelope percussion on chip 1 without interference -- impossible on a single AY.

---

## ZX Spectrum Next: Triple AY (3 x AY)

The ZX Spectrum Next includes three AY-compatible sound chips, providing 9 tone channels, 3 noise generators, and 3 envelope generators.

### Chip Selection on Next

The Next extends the TurboSound protocol. The third chip is selected via the same mechanism:

| Chip Select Value | Target |
|-------------------|--------|
| `$FF` | Chip 0 |
| `$FE` | Chip 1 |
| `$FD` | Chip 2 |

The Next also provides access through Next register $06 (Peripheral 2), which configures the sound chip mode:

| Next Reg $06, bits 1-0 | Mode |
|-------------------------|------|
| `%00` | Single AY (Spectrum 128K compatible) |
| `%01` | TurboSound (2 x AY) |
| `%10` | Triple AY (3 x AY) |

### Per-Channel Stereo Panning

The Next adds a feature the original AY never had: per-channel stereo panning. Each of the 9 channels can be individually panned left, right, or centre.

Panning is controlled through AY register 14 (R14), repurposed on the Next as a stereo control register when accessed in the AY chip context:

| Bit | Channel | 0 = | 1 = |
|-----|---------|-----|-----|
| 0 | A, right | off | on |
| 1 | A, left | off | on |
| 2 | B, right | off | on |
| 3 | B, left | off | on |
| 4 | C, right | off | on |
| 5 | C, left | off | on |

Set both bits (left + right) for centre panning. Set only one bit for hard left or hard right.

---

## Common Patterns in Z80 Code

### Silence the AY

```z80
; Silence all channels immediately
ay_silence:
    xor  a                 ; volume = 0
    ld   e, a
    ld   a, 8              ; R8 = Volume A
    call ay_write
    ld   a, 9              ; R9 = Volume B
    call ay_write
    ld   a, 10             ; R10 = Volume C
    call ay_write
    ; Disable all tone and noise
    ld   a, 7              ; R7 = Mixer
    ld   e, $3F            ; all off
    call ay_write
    ret
```

### Play a Single Note on Channel A

```z80
; Play note with period DE on channel A at volume 12
; Assumes mixer is already configured for tone A
play_note_a:
    ld   a, 0              ; R0 = Tone A low
    ld   e, d              ; wait -- let's do this properly
    ; Actually: DE has period, E = low byte, D = high byte
    push de
    ld   a, 0              ; R0
    call ay_write           ; E already has low byte
    pop  de
    ld   e, d
    ld   a, 1              ; R1
    call ay_write           ; E = high byte
    ld   a, 8              ; R8 = Volume A
    ld   e, 12             ; volume 12
    call ay_write
    ret
```

### Trigger a Buzz-Bass Note

```z80
; Buzz-bass: envelope-based bass note
; DE = envelope period for desired pitch
buzz_bass:
    ld   a, 11             ; R11 = Envelope period low
    call ay_write           ; E = low byte of period
    ld   e, d
    ld   a, 12             ; R12 = Envelope period high
    call ay_write
    ld   a, 13             ; R13 = Envelope shape
    ld   e, $08            ; repeating sawtooth down
    call ay_write           ; this also restarts the envelope
    ld   a, 10             ; R10 = Volume C
    ld   e, $10            ; envelope mode
    call ay_write
    ret
```

### Trigger Envelope (Restart)

```z80
; Restart the envelope without changing its shape
; Useful for re-triggering buzz-bass on a new note
; The shape value must be written even if unchanged
env_restart:
    ld   a, 13             ; R13 = Envelope shape
    ld   e, (hl)           ; shape from current instrument data
    call ay_write           ; writing R13 = instant restart
    ret
```

### Digital Drum Hit (4-bit DAC)

```z80
; Play a short digital sample through AY volume register
; HL = pointer to 4-bit sample data (values 0-15)
; B  = number of samples to play
; Uses channel A (R8) as DAC
;
; WARNING: This consumes all CPU time during playback.
; Disable interrupts before calling.
play_sample:
    di
    ld   a, 8              ; select R8 (Volume A)
    ld   bc, $FFFD
    out  (c), a
    ld   c, $FD            ; prepare for $BFFD writes
.loop:
    ld   a, (hl)           ; 7T   load sample
    inc  hl                ; 6T   advance pointer
    ld   b, $BF            ; 7T   BC = $BFFD
    out  (c), a            ; 12T  write volume = sample
    ; Timing padding: adjust NOPs to hit target sample rate
    nop                    ; 4T
    nop                    ; 4T
    ld   b, a              ; 4T   (dummy, preserves timing)
    ld   b, 0              ; 7T   reset B for next iteration
    ; Total per sample: ~51T = ~14.6 us = ~68.6 kHz
    ; For 8 kHz, add ~386T of padding (96 NOPs or a delay loop)
    dec  b
    jr   nz, .loop
    ei
    ret
```

See Chapter 12 for the hybrid drum technique (digital attack + AY envelope decay) that makes this practical in a demo engine.

---

## Tracker Format Notes

### ProTracker 3 (.pt3)

**ProTracker 3** (PT3) is the most widely used tracker format on the ZX Spectrum 128K. The cross-platform editor **Vortex Tracker II** natively produces .pt3 files.

| Property | Value |
|----------|-------|
| Channels | 3 (single AY) or 6 (TurboSound) |
| Pattern length | 1-64 rows |
| Song speed | 1-255 (frames per row) |
| Instruments | Ornament tables + amplitude envelopes |
| Effects | Arpeggio, portamento, vibrato, envelope control |
| Player size | ~1.2-1.8 KB (Z80 assembly) |
| Data format | Packed patterns + instrument/ornament tables |

#### How PT3 Data Maps to AY Registers

On each frame (1/50th second), the PT3 player:

1. Decrements the speed counter. If it reaches zero, advance to the next row.
2. For each channel (A, B, C):
   - Read the note, instrument, and effect from the current row.
   - Apply the instrument's ornament (per-frame pitch offset table).
   - Apply the instrument's amplitude envelope (per-frame volume table).
   - Calculate the final tone period and volume.
3. Update the mixer register (R7) based on which channels use tone, noise, or both.
4. Write all calculated values to R0-R13.

```
PT3 row data:
  Note C-4, Instrument 3, Effect: Arpeggio +4+7
       |          |              |
       v          v              v
  Period=424  Ornament table  +4 semitones, +7 semitones
       |      applied per-frame  cycling every 3 frames
       v          |              |
  R0=$A8, R1=$01  |              |
       <----------+              |
  Final period adjusted by ornament offset
       <-----------------------------+
  Period cycles: 424 -> 337 -> 283 -> 424 -> ...
  (C4  -> E4  -> G4  -> C4  -> ...)
```

#### Integration in Your Project

```z80
; Standard PT3 integration
; 1. Include the player source
    INCLUDE "pt3player.asm"

; 2. Include the song data
song_data:
    INCBIN "mysong.pt3"

; 3. Initialise at startup
    ld   hl, song_data
    call music_init         ; PT3 player init routine

; 4. Call from IM2 handler every frame
isr_handler:
    ; ... push registers ...
    call music_play         ; PT3 player frame routine
    ; ... pop registers ...
    ei
    reti
```

### Other Tracker Formats

| Format | Tracker | Channels | Player Size | Key Feature |
|--------|---------|----------|-------------|-------------|
| .pt3 | Pro Tracker 3 / Vortex Tracker II | 3-6 | ~1.2-1.8 KB | Industry standard. Ornaments + samples. |
| .pt2 | Pro Tracker 2 | 3 | ~0.8-1.0 KB | Older, simpler. Still used for size reasons. |
| .stc | Sound Tracker / Sound Tracker Pro | 3 | ~0.5-0.7 KB | Oldest Spectrum format. No ornaments. |
| .asc | ASC Sound Master | 3 | ~0.8-1.0 KB | Compact player. Russian scene favourite. |
| .sqt | SQ-Tracker | 3 | ~0.6-0.8 KB | Excellent data compression. |
| .ay  | AY emulation container | varies | N/A | Captures raw register dumps. For emulators, not playback engines. |

### Vortex Tracker II

**Vortex Tracker II** is the modern standard for composing AY music. It runs on Windows (and via Wine on Linux/macOS), and directly exports .pt3 files compatible with all standard Z80 players.

Key features for demoscene use:
- **TurboSound mode:** Edit 6 channels (2 x AY) in a single module.
- **Ornament editor:** Visual per-frame pitch offset tables.
- **Sample editor:** Per-frame amplitude + tone/noise control.
- **Loop points:** Set loop start for each pattern and for the entire song.
- **Export:** .pt3 (native), .txt (plain text dump for analysis), .wav (audio render).

The typical demoscene workflow:
1. Compose in Vortex Tracker II.
2. Export as .pt3.
3. Include the standard `pt3player.asm` (widely available, multiple versions optimised for size or speed).
4. `INCBIN` the .pt3 data.
5. Call `music_init` and `music_play` as shown above.

---

## AY-3-8910 vs YM2149: Differences That Matter

The Yamaha YM2149 (used in the Atari ST and some Spectrum clones) is pin-compatible with the AY-3-8910 but not bit-identical:

| Feature | AY-3-8910 | YM2149 |
|---------|-----------|--------|
| Volume curve | Logarithmic (1.5 dB/step) | Linear |
| Noise LFSR | 17-bit, specific taps | 17-bit, different taps |
| Envelope precision | 16 volume steps (4-bit) | 32 volume steps (5-bit internally) |
| Pin 26 (SEL) | Clock divider | Same, but often hard-wired |
| Output DAC | 4-bit resistor ladder | 5-bit resistor ladder |

**Practical impact:** The same tune sounds warmer/bassier on a real AY-3-8910 and brighter/thinner on a YM2149 due to the different volume curves. Emulators typically let you select which chip to emulate. When testing your music, try both -- your audience may have either chip in their machine.

---

## Quick Reference Card

### Register Summary (Tear-Out)

```
R0  = Tone A low        (8 bits)    R/W
R1  = Tone A high       (4 bits)    R/W
R2  = Tone B low        (8 bits)    R/W
R3  = Tone B high       (4 bits)    R/W
R4  = Tone C low        (8 bits)    R/W
R5  = Tone C high       (4 bits)    R/W
R6  = Noise period      (5 bits)    R/W    0=highest, 31=lowest
R7  = Mixer             (8 bits)    R/W    0=ON (active low!)
R8  = Volume A          (5 bits)    R/W    bit4=envelope mode
R9  = Volume B          (5 bits)    R/W    bit4=envelope mode
R10 = Volume C          (5 bits)    R/W    bit4=envelope mode
R11 = Envelope low      (8 bits)    R/W
R12 = Envelope high     (8 bits)    R/W
R13 = Envelope shape    (4 bits)    W      write = restart!

Ports:  $FFFD = select register    $BFFD = write data
Write:  OUT ($FFFD),reg  then  OUT ($BFFD),value
Read:   OUT ($FFFD),reg  then  IN A,($FFFD)

Tone:   freq = 1773400 / (16 * period)      period = 12-bit (1-4095)
Env:    freq = 1773400 / (256 * period)      period = 16-bit (1-65535)
Noise:  freq = 1773400 / (16 * period)       period = 5-bit (0-31)

Mixer R7 bits:  [IOB IOA | NC NB NA | TC TB TA]   0=enable, 1=disable
Envelope R13:   [CONT ATT ALT HOLD]
  $00 = \___    $08 = \\\\    $0A = \/\/    $0B = \^^^
  $04 = /___    $0C = ////    $0E = /\/\    $0D = /^^^

TurboSound:  $FF->$FFFD = chip 0    $FE->$FFFD = chip 1
Next 3xAY:   $FF = chip 0   $FE = chip 1   $FD = chip 2
```

---

> **Sources:** General Instrument AY-3-8910 / AY-3-8912 datasheet (1979); Yamaha YM2149 Application Manual; Dark "GS Sound System" (Spectrum Expert #01, 1997); Introspec "Eager" making-of (Hype 2015); Vortex Tracker II documentation (S.V. Bulba); NedoPC TurboSound FM documentation; ZX Spectrum Next User Manual, Issue 2
