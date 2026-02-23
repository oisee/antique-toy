# Capítulo 11: Arquitectura de Sonido -- AY, TurboSound y Triple AY

> *"El chip AY tiene tres voces. Eso no es una limitación -- es una restricción de diseño que dio forma a todo un género musical."*

---

El AY-3-8910 es la voz del ZX Spectrum 128K. General Instrument lo diseñó en 1978 como un Generador de Sonido Programable (PSG) -- un solo chip que podía producir música y efectos de sonido sin una CPU de audio dedicada. Para cuando Amstrad lo incorporó en el Spectrum 128K en 1986, ya era un caballo de batalla probado: Intellivision, MSX, Atari ST y docenas de máquinas arcade lo usaban o sus variantes compatibles en pines (YM2149 en el Atari ST, AY-3-8912 con menos puertos de E/S).

Catorce registros. Tres canales de tono de onda cuadrada. Un generador de ruido. Un generador de envolvente. Eso es todo lo que tienes. Todo lo que hayas escuchado en un chiptune de Spectrum 128K -- las líneas de bajo pulsantes, los acordes arpegiados a toda velocidad, los tambores ágiles -- proviene de programar estos catorce registros cincuenta veces por segundo.

Este capítulo te lleva desde las escrituras básicas de registros hasta un motor de música funcional. Al final, entenderás exactamente cómo un reproductor de tracker envía sonido al AY, y tendrás el conocimiento para escribir el tuyo propio.

---

## 11.1 El mapa de registros del AY-3-8910

El AY tiene 14 registros, direccionados del R0 al R13. En el ZX Spectrum 128K, se accede a ellos a través de dos puertos de E/S:

- **$FFFD** -- Selección de registro (escribe aquí primero el número de registro)
- **$BFFD** -- Escritura de datos (luego escribe aquí el valor)

Siempre selecciona el registro primero, luego escribe el dato. Este proceso de dos pasos es fundamental:

```z80
; Write value E to AY register A
ay_write:
    ld   bc, $FFFD
    out  (c), a       ; select register
    ld   b, $BF       ; $BFFD high byte (C stays $FD)
    out  (c), e       ; write data
    ret
```

Observa el truco: solo cambiamos el byte alto de BC entre las dos instrucciones OUT. El byte bajo $FD permanece en C durante todo el proceso. Esto ahorra cargar un valor completo de 16 bits dos veces.

### Tabla completa de registros

| Reg | Nombre | Bits | Descripción |
|-----|--------|------|-------------|
| R0  | Período de tono A, bajo | 8 | 8 bits inferiores del período de tono del canal A |
| R1  | Período de tono A, alto | 4 | 4 bits superiores del período de tono del canal A |
| R2  | Período de tono B, bajo | 8 | 8 bits inferiores del período de tono del canal B |
| R3  | Período de tono B, alto | 4 | 4 bits superiores del período de tono del canal B |
| R4  | Período de tono C, bajo | 8 | 8 bits inferiores del período de tono del canal C |
| R5  | Período de tono C, alto | 4 | 4 bits superiores del período de tono del canal C |
| R6  | Período de ruido | 5 | Período del generador de ruido (0-31) |
| R7  | Mezclador / habilitación de E/S | 8 | Habilitación de tono y ruido por canal + E/S |
| R8  | Volumen A | 5 | Volumen del canal A (0-15) o modo envolvente |
| R9  | Volumen B | 5 | Volumen del canal B (0-15) o modo envolvente |
| R10 | Volumen C | 5 | Volumen del canal C (0-15) o modo envolvente |
| R11 | Período de envolvente, bajo | 8 | 8 bits inferiores del período de envolvente |
| R12 | Período de envolvente, alto | 8 | 8 bits superiores del período de envolvente |
| R13 | Forma de envolvente | 4 | Forma de onda de envolvente (0-15) |

![AY-3-8910 register map](illustrations/output/ch11_ay_registers.png)

### Canales de tono (R0-R5): Cómo funciona el tono

Cada uno de los tres canales de tono produce una onda cuadrada. La frecuencia se controla mediante un valor de período de 12 bits dividido entre dos registros:

```
Frequency = AY_clock / (16 x period)
```

En el Spectrum 128K, el reloj del AY es 1,7734 MHz (la mitad del reloj de CPU de 3,5469 MHz). Así que para el Do central (aproximadamente 262 Hz):

```
period = 1,773,400 / (16 x 262) = 423
```

El período de 12 bits da un rango desde 1 (110.837 Hz -- ultrasónico inaudible) hasta 4095 (27 Hz -- un retumbo grave profundo). Aquí hay una tabla de notas práctica para la octava 4:

| Nota | Frecuencia (Hz) | Período (decimal) | R_LO | R_HI |
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

Para subir una octava, divide el período a la mitad. Para bajar, duplícalo. La tabla de notas completa para todas las octavas útiles está en el Apéndice G.

### El generador de ruido (R6)

El registro R6 controla un único generador de ruido compartido por los tres canales. El valor de 5 bits (0-31) establece el "tono" del ruido -- los valores más bajos producen un ruido más agudo y sibilante; los valores más altos producen un ruido más grave y áspero. El generador de ruido produce una salida pseudo-aleatoria usando un registro de desplazamiento con retroalimentación lineal de 17 bits.

Rangos útiles:
- **0-5**: Siseo agudo (hi-hat, platillo)
- **6-12**: Ruido medio (cuerpo de caja)
- **13-20**: Retumbo grave (explosión)
- **21-31**: Muy grave (viento, trueno)

### R7: El mezclador -- El registro más importante

El registro R7 es el corazón del AY. Seis bits controlan qué canales reciben tono, ruido, o ambos. Dos bits más controlan la dirección del puerto de E/S (irrelevante para el sonido, déjalos como entradas = 1).

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

**La parte confusa: 0 significa ENCENDIDO.** Esto confunde a todos la primera vez. El AY usa lógica activa baja para las habilitaciones del mezclador. Un bit en cero habilita la fuente correspondiente.

Aquí tienes una tabla de combinaciones útiles del mezclador:

| Valor | Binario (NcNbNa TcTbTa) | Efecto |
|-------|------------------------|--------|
| $38   | `111 000` | Los tres tonos encendidos, sin ruido |
| $3E   | `111 110` | Solo tono A |
| $3D   | `111 101` | Solo tono B |
| $3B   | `111 011` | Solo tono C |
| $36   | `110 110` | Tono A + Ruido A |
| $07   | `000 111` | Los tres ruidos, sin tonos |
| $30   | `110 000` | Tonos A+B+C, Ruido A |
| $00   | `000 000` | Todo encendido (cacofonía) |
| $3F   | `111 111` | Todo apagado (silencio) |

Un patrón común para música: tonos A+B para melodía y armonía, tono C + ruido C para percusión:

```
; Mixer: tone A on, tone B on, tone C on, noise C on
; Binary: 10 0 000 = noise C on + all tones on
; = $28
ld   a, R_MIXER
ld   e, $28
call ay_write
```

### Registros de volumen (R8-R10)

Cada canal tiene un control de volumen de 4 bits (0-15, donde 15 es el más fuerte). Pero el bit 4 es especial: activarlo cambia ese canal al **modo de envolvente**, donde el volumen es controlado automáticamente por el generador de envolvente en lugar del valor fijo.

```
Bit 4: 1 = use envelope generator, 0 = use bits 3-0
Bits 3-0: Fixed volume level (0-15)
```

La curva de volumen es logarítmica en un AY-3-8910 real (cada paso es aproximadamente 1,5 dB) pero varía entre revisiones del chip y clones. El YM2149 tiene una curva de volumen diferente, por lo que la misma melodía suena sutilmente diferente en un Atari ST comparado con un Spectrum.

### Generador de envolvente (R11-R13)

El AY tiene un generador de envolvente -- compartido entre todos los canales que lo usan. Modula automáticamente el volumen según una forma de onda repetitiva.

**R11-R12: Período de envolvente** -- Un valor de 16 bits que controla la velocidad de la envolvente:

```
Envelope_frequency = AY_clock / (256 x period)
```

Con período = 1, la envolvente cicla a aproximadamente 6.927 Hz. Con período = 65535, cicla a aproximadamente 0,11 Hz -- una vez cada 9 segundos aproximadamente.

**R13: Forma de envolvente** -- Cuatro bits seleccionan la forma de onda. Aunque 4 bits permiten 16 valores, solo 10 formas son únicas:

| Valor | Forma | Descripción |
|-------|-------|-------------|
| $00-$03 | `\___` | Decaimiento simple, luego silencio. (Las cuatro son idénticas.) |
| $04-$07 | `/___` | Ataque simple, luego silencio. (Las cuatro son idénticas.) |
| $08 | `\\\\` | Diente de sierra descendente repetitivo. |
| $09 | `\___` | Decaimiento simple, luego silencio. (Igual que $00.) |
| $0A | `\/\/` | Triángulo repetitivo (decaimiento-ataque). |
| $0B | `\'''` | Decaimiento simple, luego mantener al máximo. |
| $0C | `////` | Diente de sierra ascendente repetitivo. |
| $0D | `/'''` | Ataque simple, luego mantener al máximo. |
| $0E | `/\/\` | Triángulo repetitivo (ataque-decaimiento). |
| $0F | `/___` | Ataque simple, luego silencio. (Igual que $04.) |

Diagramas de formas de onda (volumen en el tiempo):

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

![AY envelope shape waveforms](illustrations/output/ch11_envelope_shapes.png)

**Dato clave:** Escribir en R13 *reinicia* la envolvente desde el principio. Esto es crucial para las técnicas de bajo -- puedes disparar un nuevo ciclo de envolvente en cualquier momento escribiendo en R13, incluso con el mismo valor.

---

## 11.2 Técnicas de chiptune en 3 canales

Tres canales no es mucho. Una banda real tiene bajo, batería, melodía y armonía como mínimo. Los compositores de chiptune desarrollaron trucos ingeniosos para crear la ilusión de más:

### Arpegios: Acordes falsos

Un arpegio recorre rápidamente las notas de un acorde -- una nota por fotograma. A 50 Hz (PAL), recorrer C4, E4 y G4 cada fotograma produce un efecto que el oído percibe como un acorde de Do mayor, aunque solo suena una nota en cualquier instante.

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

En un tracker, los arpegios se notan como efectos aplicados a notas. Vortex Tracker II usa tablas de ornamentos que especifican desplazamientos de semitonos por tick.

### Buzz-Bass: El truco de la envolvente

Este es el sonido de bajo más distintivo del chiptune: el "buzz". Funciona abusando del generador de envolvente. Configura la envolvente como un diente de sierra corto repetitivo ($08 o $0C), establece el período de envolvente para que coincida con la frecuencia de la nota de bajo deseada, y reinicia la envolvente cada fotograma. El resultado es un tono de bajo zumbante y grueso que no suena en absoluto como una simple onda cuadrada.

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

El período de envolvente para una nota de bajo dada es:

```
envelope_period = AY_clock / (256 x desired_frequency)
```

Para un bajo C2 (65,4 Hz): período = 1.773.400 / (256 x 65,4) = 106.

El buzz-bass te da un instrumento de bajo que suena fundamentalmente diferente a los canales de tono, añadiendo efectivamente una cuarta voz a tu arreglo.

### El problema de alineación de período

Hay una trampa con el buzz-bass que las tablas de notas de temperamento igual te ocultan. Mira la fórmula de nuevo:

```
tone_period    = AY_clock / (16 x frequency)
envelope_period = tone_period / 16
```

Para que el buzz suene limpio, el período de envolvente debe ser *exactamente* `tone_period / 16`. Pero la división entera trunca. Si el período de tono no es divisible entre 16, el período de envolvente tiene un error de redondeo -- y la forma de onda de la envolvente se desplaza respecto al tono, produciendo un batimiento audible.

Revisa nuestra tabla estándar. Octava 4:

| Nota | Período | Período mod 16 | Envolvente = Período / 16 | ¿Error? |
|------|--------|---------------|------------------------|--------|
| C4   | 424    | 8             | 26 (debería ser 26,5)    | Sí    |
| D4   | 378    | 10            | 23 (debería ser 23,625)  | Sí    |
| E4   | 337    | 1             | 21 (debería ser 21,0625) | Sí    |
| F4   | 318    | 14            | 19 (debería ser 19,875)  | Sí    |
| G4   | 283    | 11            | 17 (debería ser 17,6875) | Sí    |
| A4   | 252    | 12            | 15 (debería ser 15,75)   | Sí    |
| B4   | 225    | 1             | 14 (debería ser 14,0625) | Sí    |

¡Ni una sola división limpia! Cada nota de la escala de temperamento igual produce una envolvente ligeramente desafinada. Para sonidos de buzz percusivos cortos el batimiento queda enmascarado, pero para notas de bajo sostenidas crea un vibrato desagradable.

![Tone + Envelope Phase Alignment: clean T+E with period divisible by 16 (top) vs beating T+E with rounding error (bottom)](illustrations/output/ch11_te_alignment.png)

### Afinación natural: Tabla #5

En junio de 2001, Ivan Roshin publicó "Частотная таблица с нулевой погрешностью" (Una tabla de frecuencias con error cero), llegando a la misma conclusión que siglos de teoría musical ya habían establecido: reemplazar el temperamento igual con *entonación justa* -- intervalos de razón entera que el hardware del AY puede dividir limpiamente.

La escala natural para Do mayor / La menor usa estos intervalos:

```
C [9/8] D [10/9] E [16/15] F [9/8] G [10/9] A [9/8] B [16/15] C
```

Esto da quintas puras (razón 3:2) para C--G, E--B, A--E. Las notas cromáticas (sostenidos/bemoles) se calculan con la razón 16/15.

![Just Intonation: interval structure of the natural scale with period divisibility table for buzz-bass](illustrations/output/ch11_just_intonation.png)

Los períodos resultantes, calculados para un reloj AY *no estándar* de 1.520.640 Hz:

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

La idea clave es que la mayoría de los períodos de la escala principal ahora son divisibles entre 16. Aquí está la octava 2 -- el rango de bajo que más importa para el buzz:

| Nota | Período | mod 16 | Envolvente = Período/16 | ¿Limpio? |
|------|--------|--------|----------------------|--------|
| C2   | 1440   | 0      | 90                   | Sí |
| C#2  | 1350   | 6      | 84,375 -> 84          | No  |
| D2   | 1280   | 0      | 80                   | Sí |
| D#2  | 1200   | 0      | 75                   | Sí |
| E2   | 1152   | 0      | 72                   | Sí |
| F2   | 1080   | 0      | 67,5 -> 68            | ~   |
| F#2  | 1013   | 5      | 63,3 -> 63            | No  |
| G2   |  960   | 0      | 60                   | Sí |
| G#2  |  900   | 4      | 56,25 -> 56           | No  |
| A2   |  864   | 0      | 54                   | Sí |
| A#2  |  810   | 2      | 50,6 -> 51            | No  |
| B2   |  768   | 0      | 48                   | Sí |

Siete de doce notas se dividen limpiamente -- todas las notas naturales de Do mayor. Compara con la tabla de temperamento igual donde *ninguna* lo hace. En esas siete notas los generadores de envolvente y tono se sincronizan en fase, y el buzz-bass suena puro.

**La desventaja:** esta tabla solo es correcta para Do mayor / La menor. Para tocar en otras tonalidades, cambias la frecuencia del reloj del AY:

| Tonalidad | Frecuencia del chip (Hz) |
|-----|---------------------|
| C/Am    | 1.520.640 |
| C#/A#m  | 1.611.062 |
| D/Bm    | 1.706.861 |
| D#/Cm   | 1.808.356 |
| E/C#m   | 1.915.886 |
| F/Dm    | 2.029.811 |
| F#/D#m  | 2.150.510 |
| G/Em    | 2.278.386 |
| G#/Fm   | 2.413.866 |
| A/F#m   | 2.557.401 |
| A#/Gm   | 2.709.472 |
| B/G#m   | 2.870.586 |

En hardware real el reloj del AY es fijo, así que no puedes realmente cambiar de tonalidad en tiempo de ejecución. Pero en un emulador o tracker como Vortex Tracker II, la "frecuencia del chip" es un ajuste. Esto es exactamente lo que hizo la modificación Vortex Tracker Improved (VTi) de oisee en 2009: añadió la Tabla #5 (la quinta tabla, índice 4 contando desde cero) con estos períodos naturales, más un ajuste de frecuencia de chip por módulo que selecciona la tonalidad.

El conversor MIDI a PT3 autosiril usa la Tabla #5 por defecto precisamente por estas razones de limpias de envolvente -- la mayoría de las pistas convertidas usan buzz-bass extensivamente, y la afinación natural elimina el batimiento.

**En la práctica:** si estás escribiendo un módulo de tracker que depende mucho del buzz-bass, considera componer en Do/Lam con la Tabla #5. Las envolventes se sincronizarán perfectamente con el tono. Si necesitas una tonalidad diferente, transpone la frecuencia del chip (del lado del tracker) o acepta los pequeños errores de redondeo del temperamento igual. Para sonidos buzz percusivos cortos, la diferencia es inaudible; para drones de bajo sostenidos, es muy notable.

### Síntesis de percusión

Con solo un generador de ruido, la percusión necesita compartir. El enfoque estándar:

**Caja:** Canal de ruido + decaimiento rápido de envolvente.

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

**Bombo:** Barrido rápido de tono descendente. Configura el canal C con un período de tono bajo, luego incrementa el período durante varios fotogramas:

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

**Hi-hat:** Ráfaga de ruido muy corta, frecuencia de ruido alta (valor bajo en R6), corte de volumen inmediato después de 1-2 fotogramas.

### Ornamentos: Modulación por fotograma

Un ornamento es una tabla de desplazamientos por fotograma aplicados al tono o volumen de una nota. Los ornamentos dan vida a ondas cuadradas que de otro modo serían estáticas: vibrato, deslizamientos de tono, trémolo, envolventes de ataque/decaimiento -- todo logrado mediante consulta de tabla.

```z80
; Example ornament: pitch vibrato
; Table of signed semitone offsets, applied once per frame
ornament_vibrato:
    DB 0, 0, 1, 1, 0, 0, -1, -1    ; 8-frame cycle
    DB $80                           ; end marker
```

El motor del reproductor aplica el desplazamiento del ornamento al valor del período de la nota base en cada fotograma, produciendo una modulación suave.

---

## 11.3 TurboSound: 2 x AY

Los clones Pentagon y Scorpion introdujeron TurboSound -- dos chips AY en una sola máquina. El segundo chip se direcciona seleccionándolo a través de un patrón de bits escrito en el puerto $FFFD antes de las operaciones de registro.

### Selección de chip

En la tarjeta NedoPC TurboSound (el diseño moderno más común), la selección de chip funciona a través del puerto $FFFD:

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

Una vez que un chip está seleccionado, todas las lecturas y escrituras de registros subsiguientes vía $FFFD/$BFFD van a ese chip. En la práctica, tu motor de música selecciona el chip 0, actualiza todos sus registros, luego selecciona el chip 1 y actualiza sus registros.

### 6 canales, estéreo verdadero

TurboSound duplica todo: 6 canales de tono, 2 generadores de ruido independientes, 2 generadores de envolvente independientes. Un arreglo estéreo típico:

| Chip | Canales | Estéreo | Función |
|------|----------|--------|------|
| Chip 0 | A0, B0, C0 | Izquierda o centro | Melodía principal, armonía, bajo |
| Chip 1 | A1, B1, C1 | Derecha o centro | Contra-melodía, pads, percusión |

O mézclalos para un campo estéreo amplio:
- Bajo en ambos chips (centro)
- Melodía principal en chip 0 (izquierda)
- Contra-melodía en chip 1 (derecha)
- Percusión dividida: bombo en chip 0, caja/hi-hat en chip 1

Lo que TurboSound cambia musicalmente es significativo: en un solo AY, el compositor está constantemente haciendo sacrificios. No puedes tener una nota de bajo sostenida, una melodía principal y un golpe de percusión al mismo tiempo sin robar canales. Con TurboSound, tienes espacio. Canal de bajo dedicado, percusión dedicada, y cuatro voces restantes para melodía y armonía. La era de los compromisos termina.

### Modificación del motor

Adaptar un motor de un solo AY a TurboSound es sencillo. Tu manejador de interrupciones se convierte en:

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

El bucle de escritura de registros escribe los 14 registros desde un búfer en RAM. Para dos chips, mantienes dos búferes de 14 bytes y los envías secuencialmente. Coste total: unas 28 instrucciones OUT, aproximadamente 400 T-states.

---

## 11.4 Triple AY en ZX Spectrum Next

El ZX Spectrum Next va más allá: tres chips de sonido compatibles con AY, dándote 9 canales. Pero la implementación del Next va más allá de la simple triplicación.

### Características mejoradas

Los chips AY del Next incluyen **panorámica estéreo por canal**. Cada canal puede ser panoramizado individualmente a izquierda, derecha o centro -- algo que el AY original nunca soportó. Esto se controla a través de registros adicionales específicos del Next.

Los tres chips se direccionan vía el registro $06 del Next (configuración del periférico 2) o a través del puerto estándar $FFFD con valores de selección de chip.

### 9 canales: Pensamiento orquestal

Nueve canales cambian fundamentalmente cómo abordas la composición en hardware de 8 bits. En lugar de trucos ingeniosos para simular complejidad, puedes pensar orquestalmente:

| Canal | Asignación | Panorámica |
|---------|-----------|---------|
| Chip 0, A | Línea de bajo | Centro |
| Chip 0, B | Guitarra rítmica / pad | Izquierda |
| Chip 0, C | Melodía principal | Centro |
| Chip 1, A | Armonía / contra-melodía | Derecha |
| Chip 1, B | Acorde arpegiado | Izquierda |
| Chip 1, C | Percusión: bombo + caja | Centro |
| Chip 2, A | Hi-hat / platillo | Derecha |
| Chip 2, B | Efectos de sonido (reservado) | Centro |
| Chip 2, C | Ambiente / capas de pad | Izquierda |

Esto es suficiente para arreglos genuinamente ricos. Tienes un canal de SFX dedicado que nunca interrumpe la música. Tienes generadores de ruido independientes para percusión en capas. Puedes sostener acordes sin arpegios. El carácter del AY permanece -- las ondas cuadradas siguen siendo ondas cuadradas -- pero la libertad compositiva se acerca a la de un tracker MOD de Amiga con sus cuatro canales de muestras.

---

## 11.5 Arquitectura del motor de música

Un motor de música es el código que lee datos de patrones y escribe registros del AY al tempo correcto. En el Spectrum, vive dentro del manejador de interrupciones.

### El reproductor dirigido por interrupciones

El IM2 (modo de interrupción 2) del ZX Spectrum se dispara una vez por fotograma -- cada 1/50 de segundo en sistemas PAL. El motor de música se engancha a esto:

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

### El bucle del reproductor

La rutina del reproductor, llamada 50 veces por segundo, hace lo siguiente:

1. Decrementar el contador de duración de la nota actual
2. Si llega a cero, avanzar a la siguiente nota en el patrón
3. Aplicar ornamentos y efectos (arpegio, vibrato, deslizamiento) a cada canal
4. Calcular el período y volumen finales para cada canal
5. Escribir los 14 registros del AY

Un esqueleto simplificado:

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

### Presupuesto de fotograma

Aquí está la pregunta crítica: ¿cuántos T-states puede consumir el motor de música antes de dejar sin recursos al programa principal?

El fotograma es de 71.680 T-states en Pentagon (69.888 en 48K). La interrupción se dispara al inicio del fotograma. Si el reproductor de música toma 5.000 T-states, el programa principal tiene 66.680 restantes para los gráficos.

Costes típicos:
- **Reproductor simple** (sin efectos, sin ornamentos): ~1.500-2.500 T-states
- **Reproductor Pro Tracker 3**: ~3.000-5.000 T-states
- **Reproductor completo de Vortex Tracker II** con ornamentos y efectos: ~4.000-7.000 T-states
- **Reproductor TurboSound** (2 chips): ~6.000-10.000 T-states

Para una demo ejecutando un efecto exigente en ciclos, 7.000 T-states para la música es significativo -- alrededor del 10% del fotograma. Planifica en consecuencia.

### Formatos y trackers

El estándar moderno para música AY en el Spectrum es **Vortex Tracker II** (formato .pt3). Es un tracker multiplataforma que funciona en Windows y genera archivos directamente reproducibles por rutinas de reproductor Z80 probadas.

| Formato | Tracker | Características | Tamaño del reproductor |
|--------|---------|----------|-------------|
| .pt3 | Vortex Tracker II / Pro Tracker 3 | Ornamentos, muestras, efectos | ~1,2-1,8 KB |
| .asc | ASC Sound Master | Más simple, reproductor más pequeño | ~0,8-1,0 KB |
| .sqt | SQ-Tracker | Compacto, buena compresión | ~0,6-0,8 KB |
| .stc | Sound Tracker | Básico, el más antiguo | ~0,5-0,7 KB |

**La cadena de producción:**

1. Componer en Vortex Tracker II en tu PC
2. Exportar como archivo .pt3
3. Incluir el código fuente del reproductor .pt3 (ensamblador Z80) en tu proyecto
4. Incluir el archivo de datos .pt3 como un blob binario
5. Llamar a `music_init` al inicio (pasando la dirección de los datos de la canción)
6. Llamar a `music_play` desde tu manejador de interrupciones cada fotograma

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

Este es el enfoque estándar usado por virtualmente cada demo y juego de Spectrum 128K desde principios de los 2000.

---

## 11.6 Sistema de efectos de sonido

Los juegos necesitan efectos de sonido, y los efectos de sonido necesitan canales. El enfoque estándar es **robo de canal basado en prioridad**: cuando se dispara un efecto de sonido, temporalmente toma el control de un canal del motor de música, luego lo libera cuando el efecto termina.

### Robo de canal

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

### Tablas de SFX procedurales

Los efectos de sonido se definen como tablas de valores de registro por fotograma. Aquí tienes cuatro sonidos clásicos de juego:

**Explosión:** Ruido con volumen decreciente.

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

**Láser:** Barrido de tono rápido descendente.

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

**Salto:** Barrido de tono corto ascendente.

```z80
sfx_jump:
    DB 200,0, 0, 12, 0    ; frame 0: mid tone
    DB 150,0, 0, 11, 0    ; frame 1: rising
    DB 100,0, 0, 10, 0    ; frame 2
    DB 60, 0, 0, 8,  0    ; frame 3: high
    DB 40, 0, 0, 5,  0    ; frame 4
    DB $FF                 ; end
```

**Recogida:** Arpegio rápido ascendente.

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

## 11.7 Poniéndolo todo junto: El ejemplo funcional

El archivo `chapters/ch11-sound/examples/ay_test.a80` contiene un ejemplo completo y ensamblable que demuestra los fundamentos: inicialización del AY, configuración del mezclador, escritura de períodos de tono y reproducción de una melodía. Estúdialo junto con este capítulo -- cada concepto discutido aquí se ejerce en ese código.

Los patrones clave a notar en el ejemplo:

1. **Acceso al puerto en dos pasos**: Seleccionar registro vía $FFFD, luego escribir datos vía $BFFD.
2. **Configuración del mezclador**: $3E habilita solo el tono A (binario `111 110` -- recuerda, 0 = ENCENDIDO).
3. **Tabla de notas**: Valores de período pre-calculados para cada tono.
4. **Temporización basada en HALT**: Cada `HALT` espera a una interrupción, dando una resolución de temporización de 50 Hz.

Para extender este ejemplo a un reproductor de música real, reemplazarías la tabla de melodía lineal con datos basados en patrones, añadirías procesamiento de ornamentos, y moverías la reproducción a un manejador de interrupciones IM2 para que el bucle principal quede libre para los gráficos.

---

> ## Recuadro: Beeper -- Una breve historia de lo imposible
>
> Antes del 128K y su chip AY, el Spectrum 48K original tenía exactamente un bit de salida de audio. El pin 4 del puerto $FE. Alto o bajo. Eso es todo.
>
> Un bit significa una onda cuadrada a cualquier frecuencia a la que la conmutes. Sin control de volumen, sin mezcla, sin ayuda del hardware. Para tocar una nota, te sientas en un bucle cerrado conmutando el bit a la frecuencia correcta. Para tocar *dos* notas, intercalas dos bucles de conmutación. Para tocar tres, intercalas tres. Cada voz adicional consume tiempo de CPU que podría estar haciendo otra cosa -- como, digamos, dibujar gráficos.
>
> Y sin embargo.
>
> Entre 2010 y 2015, Shiru (Shiru Otaku) catalogó aproximadamente 30 motores de beeper distintos, cada uno usando una técnica diferente para extraer polifonía de un solo bit. Los enfoques iban desde simple intercalado de pulsos compatible con pin (2-3 canales) hasta hazañas extraordinarias de ingeniería:
>
> - **ZX-16** de Jan Deak: polifonía de 16 canales en un solo bit. Dieciséis. La CPU no hace nada más que conmutar el bit del altavoz usando un programa cuidadosamente temporizado que aproxima la suma de 16 formas de onda independientes a través de modulación por densidad de pulsos.
>
> - **Octode XL**: motor de beeper de 8 canales que realmente deja suficiente CPU para gráficos.
>
> - **Rain** de Life on Mars (2016): Una demo completa ejecutando un motor de beeper de 9 canales *simultáneamente con efectos visuales* en un Spectrum 48K. Toda la producción -- música y gráficos -- funciona sin chip AY, sin conmutación de bancos, sin nada más allá de la máquina base.
>
> Estos son algunos de los logros de ingeniería más notables en la computación de 8 bits. Demuestran que los límites son más permeables de lo que aparentan. Pero también son poco prácticos para uso general: la mayoría de los motores de beeper consumen el 50-90% del tiempo de CPU, dejando casi nada para jugabilidad o efectos. El chip AY existe precisamente para descargar la generación de sonido al hardware dedicado.
>
> Cubrimos los motores de beeper aquí como contexto histórico e inspiración. Para música práctica en tus demos y juegos, el AY es donde deberías enfocar tu esfuerzo.

---

> ## Recuadro: Agon Light 2 -- Sistema de sonido VDP
>
> El Agon Light 2 adopta un enfoque completamente diferente para el sonido. Su audio es generado por el coprocesador ESP32 (el VDP), no por un chip de sonido dedicado. Envías comandos VDU a través del enlace serial, y el ESP32 sintetiza audio por software.
>
> **Formas de onda:** El sistema de sonido del Agon ofrece múltiples tipos de forma de onda por canal -- cuadrada, seno, triángulo, diente de sierra y ruido. Esto ya es más flexible que los generadores de tono de solo onda cuadrada del AY.
>
> **Envolventes ADSR:** Cada canal tiene una envolvente Ataque-Decaimiento-Sostenimiento-Liberación completamente programable. Sin compartir -- cada canal tiene su propia envolvente independiente, a diferencia del único generador de envolvente compartido del AY.
>
> **Número de canales:** El sistema de audio del VDP soporta múltiples canales simultáneos (el número exacto depende de la versión del firmware, pero típicamente 8 o más).
>
> **La desventaja:** El sonido del Agon se controla a través de secuencias de bytes VDU enviadas por serial. Esto significa:
> - Mayor latencia que las escrituras directas a registros (tiempo de transferencia serial)
> - Temporización menos precisa (no puedes sincronizar a nivel exacto de T-state)
> - Pero mucho menos sobrecarga de CPU (el eZ80 solo envía comandos; el ESP32 hace toda la síntesis)
>
> El paradigma está más cerca de MIDI que de la programación a nivel de registros. Le dices al VDP "toca esta nota en el canal 3 con una onda seno y esta envolvente ADSR", y él se encarga del resto. Los objetivos musicales son los mismos -- melodía, bajo, percusión, efectos -- pero el modelo de programación es fundamentalmente diferente. Sin registro de mezclador, sin cálculos de período, sin tablas de forma de envolvente. Solo comandos y parámetros.
>
> Para proyectos multiplataforma, considera abstraer tu sistema de sonido detrás de una API común: `sound_play_note(channel, note, instrument)`. En el Spectrum, la búsqueda de instrumento escribe registros del AY. En el Agon, envía comandos VDU. Mismos datos musicales, diferentes backends.

---

## 11.8 Ejercicios prácticos

**Ejercicio 1: Explorador de registros.** Escribe un programa que te permita modificar cualquier registro del AY en tiempo real usando entrada de teclado. Muestra los 14 valores de registro en pantalla. Esta es tu herramienta de depuración más útil para trabajo con sonido.

**Ejercicio 2: Arreglo de tres canales.** Compón una melodía simple de 16 compases usando los tres canales: melodía en A, bajo (buzz-bass usando envolvente) en C, y acordes arpegiados en B. Usa la temporización basada en HALT del ejemplo como punto de partida, luego refactorízalo a un reproductor dirigido por IM2.

**Ejercicio 3: Kit de percusión.** Implementa cuatro sonidos de percusión (bombo, caja, hi-hat, crash) como tablas de SFX procedurales. Escribe un patrón de percusión simple que los reproduzca en secuencia. Intégralo con la melodía del Ejercicio 2.

**Ejercicio 4: Integración con Vortex Tracker.** Descarga Vortex Tracker II, compón una melodía corta, expórtala como .pt3, e integra el reproductor estándar de .pt3 en un programa de Spectrum. Verifica que se reproduce correctamente en un emulador.

---

## Resumen

El AY-3-8910 es engañosamente simple: 14 registros, 3 canales, formas de onda básicas. Pero la brecha entre "simple" y "limitado" se llena con técnica. Los arpegios fingen acordes. El abuso de envolventes crea bajo. El modelado de ruido sintetiza percusión. Los ornamentos dan vida a tonos estáticos. Y cuando tres canales genuinamente no son suficientes, TurboSound los duplica y el Next los triplica.

El patrón de arquitectura es consistente en todas las configuraciones: una interrupción se dispara 50 veces por segundo, una rutina de reproductor lee datos de patrones y calcula valores de registro, y esos valores se envían al AY en un bucle cerrado. Ya sea que estés escribiendo tu propio reproductor o integrando Vortex Tracker, el flujo es el mismo. Entender los registros significa entender el sonido.

En el próximo capítulo, pondremos esto a trabajar: muestras de tambores digitales mezcladas con reproducción AY, sincronización con precisión de fotograma entre música y gráficos, y los motores de scripts que unen una demo.

---

> **Fuentes:** Dark "GS Sound System" (Spectrum Expert #01, 1997); Dark "Music" (Spectrum Expert #02, 1998); Shiru "Beeper 20XX" (Hype 2016); Rain file_id.diz; Info Guide #14 ASC Sound Master docs (ZXArt 2024); Vortex Tracker II documentation
