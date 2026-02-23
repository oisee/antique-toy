# Apéndice G: Referencia de registros AY-3-8910 / TurboSound / Triple AY

> *"Catorce registros. Tres canales de tono de onda cuadrada. Un generador de ruido. Un generador de envolvente. Eso es todo lo que tienes."*
> -- Capítulo 11

---

Este apéndice es una referencia completa a nivel de registro del Generador de Sonido Programable AY-3-8910 tal como se usa en el ZX Spectrum 128K, clones equipados con TurboSound (Pentagon, Scorpion), y la configuración de triple AY del ZX Spectrum Next. El Capítulo 11 cubre las técnicas musicales; este apéndice es la hoja de datos que mantienes abierta mientras programas.

Todos los valores hexadecimales usan la notación `$FF`. Los valores binarios usan `%10101010`. La frecuencia de reloj asume el estándar PAL del Spectrum 128K de 1.7734 MHz a menos que se indique lo contrario.

---

## Puertos de E/S en ZX Spectrum 128K

| Puerto | Dirección | Función |
|--------|-----------|---------|
| **$FFFD** | Escritura | Seleccionar registro activo (0-15) |
| **$FFFD** | Lectura | Leer valor del registro actualmente seleccionado |
| **$BFFD** | Escritura | Escribir datos al registro seleccionado |

### La secuencia de escritura

Cada escritura de registro AY es una operación de dos pasos: seleccionar el registro, luego escribir el valor.

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

El truco: solo el byte alto de BC cambia entre las dos instrucciones `OUT`. El byte bajo `$FD` permanece en C todo el tiempo. Esto ahorra 3 bytes y 10 T-states comparado con cargar un valor completo de 16 bits dos veces.

### Lectura de un registro

```z80
; Read AY register A into A
; Clobbers: BC
ay_read:
    ld   bc, $FFFD
    out  (c), a       ; select register
    in   a, (c)       ; read value
    ret
```

La lectura es útil para preservar el estado del mezclador (R7) al modificar las habilitaciones de canales individuales.

### Escritura masiva de registros

Para motores musicales que actualizan los 14 registros por fotograma, un bucle desenrollado es lo más rápido:

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

## Mapa completo de registros

### Vista general

| Reg | Nombre | Bits usados | L/E | Reset | Descripción |
|-----|--------|-------------|-----|-------|-------------|
| R0  | Período tono A, bajo | 7-0 | L/E | $00 | Período de tono canal A, bits 7-0 |
| R1  | Período tono A, alto | 3-0 | L/E | $00 | Período de tono canal A, bits 11-8 |
| R2  | Período tono B, bajo | 7-0 | L/E | $00 | Período de tono canal B, bits 7-0 |
| R3  | Período tono B, alto | 3-0 | L/E | $00 | Período de tono canal B, bits 11-8 |
| R4  | Período tono C, bajo | 7-0 | L/E | $00 | Período de tono canal C, bits 7-0 |
| R5  | Período tono C, alto | 3-0 | L/E | $00 | Período de tono canal C, bits 11-8 |
| R6  | Período de ruido | 4-0 | L/E | $00 | Período del generador de ruido (0-31) |
| R7  | Mezclador / E/S | 7-0 | L/E | $FF | Habilitación tono/ruido + dirección puerto E/S |
| R8  | Volumen A | 4-0 | L/E | $00 | Volumen canal A o modo envolvente |
| R9  | Volumen B | 4-0 | L/E | $00 | Volumen canal B o modo envolvente |
| R10 | Volumen C | 4-0 | L/E | $00 | Volumen canal C o modo envolvente |
| R11 | Período envolvente, bajo | 7-0 | L/E | $00 | Período de envolvente, bits 7-0 |
| R12 | Período envolvente, alto | 7-0 | L/E | $00 | Período de envolvente, bits 15-8 |
| R13 | Forma de envolvente | 3-0 | E | -- | Forma de onda de envolvente (escribir reinicia la envolvente) |
| R14 | Puerto E/S A | 7-0 | L/E | -- | E/S de propósito general (mapeado directamente en AY-3-8910) |
| R15 | Puerto E/S B | 7-0 | L/E | -- | E/S de propósito general (mapeado directamente en AY-3-8910) |

**Nota sobre R14-R15:** El AY-3-8910 tiene dos puertos de E/S de 8 bits. En el ZX Spectrum 128K, el puerto de E/S A (R14) está activo -- lee la matriz de teclado y otras señales de hardware. R15 (puerto de E/S B) normalmente no está conectado. El AY-3-8912 (usado en algunos clones) tiene solo el puerto A; el AY-3-8913 no tiene puertos de E/S en absoluto. Para programación de sonido, R14 y R15 son irrelevantes.

---

### R0-R1: Período de tono del canal A (12 bits)

```
R0:  [D7] [D6] [D5] [D4] [D3] [D2] [D1] [D0]   bits 7-0 of period
R1:  [ 0] [ 0] [ 0] [ 0] [D11][D10][ D9][ D8]   bits 11-8 of period
```

- **Rango:** 1 a 4095 (12 bits sin signo). Un período de 0 se comporta como 1 en la mayoría de implementaciones.
- **Efecto:** Establece la frecuencia de la onda cuadrada en el canal A.
- **Fórmula:** `frecuencia = 1773400 / (16 * período)` (PAL Spectrum 128K)
- **Rango práctico:** Período 1 = 110,837 Hz (ultrasónico), período 4095 = 27 Hz (bajo profundo).

```z80
; Set channel A to middle C (C4, ~262 Hz, period 424)
    ld   a, 0              ; R0 = Tone A low
    ld   e, $A8            ; 424 & $FF = $A8
    call ay_write
    ld   a, 1              ; R1 = Tone A high
    ld   e, $01            ; 424 >> 8 = $01
    call ay_write
```

### R2-R3: Período de tono del canal B (12 bits)

Disposición idéntica a R0-R1, para el canal B.

### R4-R5: Período de tono del canal C (12 bits)

Disposición idéntica a R0-R1, para el canal C.

---

### R6: Período de ruido (5 bits)

```
R6:  [ 0] [ 0] [ 0] [D4] [D3] [D2] [D1] [D0]
```

- **Rango:** 0 a 31. Un solo generador de ruido compartido por los tres canales.
- **Efecto:** Valores más bajos = ruido más agudo (siseo). Valores más altos = ruido más grave y áspero.
- **Fórmula:** `frecuencia_ruido = 1773400 / (16 * período)` (misma fórmula que tono)

| Valor R6 | Carácter | Uso típico |
|----------|----------|------------|
| 0-5 | Siseo agudo | Hi-hat, platillo, timbre metálico |
| 6-12 | Ruido medio | Cuerpo de caja, ruido blanco |
| 13-20 | Retumbo bajo | Explosión, motor, viento |
| 21-31 | Muy bajo | Trueno, retumbo distante |

El generador de ruido usa un registro de desplazamiento con retroalimentación lineal (LFSR) de 17 bits para producir una salida pseudo-aleatoria. La salida es la misma tanto para el AY-3-8910 como para el YM2149, pero las posiciones de tap del LFSR difieren, produciendo texturas de ruido sutilmente diferentes en cada chip.

---

### R7: Control del mezclador (el registro más importante)

```
R7:  [IOB] [IOA] [NC] [NB] [NA] [TC] [TB] [TA]
      bit7  bit6  bit5 bit4 bit3 bit2 bit1 bit0
```

| Bit | Nombre | 0 = | 1 = |
|-----|--------|-----|-----|
| 7 | Dirección puerto E/S B | Salida | **Entrada** |
| 6 | Dirección puerto E/S A | Salida | **Entrada** |
| 5 | Habilitación ruido C | **ON** | Off |
| 4 | Habilitación ruido B | **ON** | Off |
| 3 | Habilitación ruido A | **ON** | Off |
| 2 | Habilitación tono C | **ON** | Off |
| 1 | Habilitación tono B | **ON** | Off |
| 0 | Habilitación tono A | **ON** | Off |

**Crítico: 0 significa ON.** El mezclador usa lógica activa-baja. Un bit desactivado habilita la fuente correspondiente. Este es el aspecto más confuso de la programación del AY.

**Bits 7-6:** Siempre establecer a 1 (modo entrada) en el Spectrum. No cambies estos a menos que sepas lo que estás haciendo con los puertos de E/S.

#### Valores comunes del mezclador

| Valor | Binario (`NC NB NA TC TB TA`) | Efecto |
|-------|-------------------------------|--------|
| `$38` | `%00 111 000` | Los tres tonos, sin ruido |
| `$3E` | `%00 111 110` | Solo tono A |
| `$3D` | `%00 111 101` | Solo tono B |
| `$3B` | `%00 111 011` | Solo tono C |
| `$36` | `%00 110 110` | Tono A + Ruido A |
| `$2D` | `%00 101 101` | Tono B + Ruido B |
| `$1B` | `%00 011 011` | Tono C + Ruido C |
| `$28` | `%00 101 000` | Todos los tonos + Ruido C (música + percusión en C) |
| `$07` | `%00 000 111` | Todo ruido, sin tonos |
| `$00` | `%00 000 000` | Todo activado |
| `$3F` | `%00 111 111` | Todo desactivado (silencio) |

**Nota:** Los valores binarios arriba muestran solo los bits 5-0. Los bits 7-6 deberían ser `%11` para operación normal (puertos de E/S como entradas), haciendo que p. ej. `$38` sea en realidad `%11 111 000` = `$F8`. Sin embargo, en el Spectrum 128K los bits superiores no usados son ignorados por convención, y la mayoría del código usa la forma corta. Algunos motores escriben la forma completa `$F8`; ambas funcionan de forma idéntica.

```z80
; Enable tone A, tone B, tone C, and noise on C only
; Binary: I/O=11, NC=0(on), NB=1, NA=1, TC=0(on), TB=0(on), TA=0(on)
; = %11 011 000 = $D8 (full form) or $28 (short form, bits 7-6 treated as 0)
    ld   a, 7              ; R7 = Mixer
    ld   e, $28
    call ay_write
```

---

### R8-R10: Registros de volumen (5 bits)

```
R8:  [ 0] [ 0] [ 0] [ M] [D3] [D2] [D1] [D0]   Channel A
R9:  [ 0] [ 0] [ 0] [ M] [D3] [D2] [D1] [D0]   Channel B
R10: [ 0] [ 0] [ 0] [ M] [D3] [D2] [D1] [D0]   Channel C
```

| Bit | Función |
|-----|---------|
| 4 (M) | Modo: 0 = usar volumen fijo (bits 3-0), 1 = usar generador de envolvente |
| 3-0 | Nivel de volumen fijo: 0 (silencio) a 15 (máximo) |

- **Modo de volumen fijo** (bit 4 = 0): Los bits 3-0 establecen el volumen del canal directamente. 15 = más fuerte, 0 = silencio. La curva de volumen es logarítmica en un genuino AY-3-8910 (aproximadamente 1.5 dB por paso) pero lineal en el YM2149.
- **Modo envolvente** (bit 4 = 1): El volumen del canal es controlado por el generador de envolvente (R11-R13). Los bits 3-0 son ignorados. Solo existe un generador de envolvente, compartido por todos los canales en modo envolvente.

| Valor | Efecto |
|-------|--------|
| `$00` | Silencio |
| `$08` | Medio volumen (aproximadamente) |
| `$0F` | Volumen fijo máximo |
| `$10` | Modo envolvente (cualquier valor $10-$1F activa la envolvente) |

**Truco de DAC de 4 bits:** Escribiendo rápidamente valores de muestra sucesivos en un registro de volumen (sin modo envolvente), puedes reproducir audio digitalizado a través del AY. A una tasa de muestreo de 8 kHz, esto consume aproximadamente 437 T-states por escritura de muestra, dejando casi ninguna CPU para otro trabajo. Ver Capítulo 12 para la técnica de tambores digitales híbridos.

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

### R11-R12: Período de envolvente (16 bits)

```
R11: [D7] [D6] [D5] [D4] [D3] [D2] [D1] [D0]   bits 7-0
R12: [D7] [D6] [D5] [D4] [D3] [D2] [D1] [D0]   bits 15-8
```

- **Rango:** 1 a 65535 (16 bits sin signo). Un período de 0 se comporta como 1.
- **Fórmula:** `frecuencia_envolvente = 1773400 / (256 * período)`
- **Con período = 1:** ~6,927 Hz (un ciclo completo de envolvente en ~144 microsegundos)
- **Con período = 65535:** ~0.106 Hz (un ciclo en ~9.4 segundos)

El período de envolvente controla qué tan rápido sube o baja el volumen según la forma seleccionada en R13. Para buzz-bass, el período de envolvente reemplaza al período de tono como control de tono:

```
período_envolvente_bajo = 1773400 / (256 * frecuencia_deseada)
```

Para bajo C2 (65.4 Hz): período = 1773400 / (256 * 65.4) = 106.

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

### R13: Forma de envolvente (4 bits, solo escritura)

```
R13: [ 0] [ 0] [ 0] [ 0] [CONT] [ATT] [ALT] [HOLD]
                            bit3   bit2  bit1   bit0
```

| Bit | Nombre | Función |
|-----|--------|---------|
| 3 | CONT | Continuar: 0 = disparo único (restablecer a 0 o mantener), 1 = repetir |
| 2 | ATT | Ataque: 0 = comenzar en máx., bajar, 1 = comenzar en 0, subir |
| 1 | ALT | Alternar: 0 = misma dirección cada ciclo, 1 = invertir dirección |
| 0 | HOLD | Mantener: 0 = ciclar normalmente, 1 = mantener en nivel final tras el primer ciclo |

**Comportamiento crítico:** Escribir CUALQUIER valor en R13 reinicia inmediatamente la envolvente desde el comienzo del ciclo. Esto es cierto incluso si escribes el mismo valor ya almacenado. Este comportamiento de reinicio es esencial para disparar notas de buzz-bass y sonidos de percusión.

#### Los 16 valores de forma

Aunque 4 bits permiten 16 valores, muchos producen salidas idénticas. Solo hay 10 formas únicas:

| Valor | Bits (CONT ATT ALT HOLD) | Forma | Comportamiento |
|-------|---------------------------|-------|----------------|
| `$00` | `0 0 0 0` | `\___` | Decaimiento a 0, mantener en 0 |
| `$01` | `0 0 0 1` | `\___` | Igual que $00 |
| `$02` | `0 0 1 0` | `\___` | Igual que $00 |
| `$03` | `0 0 1 1` | `\___` | Igual que $00 |
| `$04` | `0 1 0 0` | `/___` | Ataque a 15, caer a 0, mantener en 0 |
| `$05` | `0 1 0 1` | `/___` | Igual que $04 |
| `$06` | `0 1 1 0` | `/___` | Igual que $04 |
| `$07` | `0 1 1 1` | `/___` | Igual que $04 |
| `$08` | `1 0 0 0` | `\\\\` | Diente de sierra descendente repetitivo |
| `$09` | `1 0 0 1` | `\___` | Decaimiento simple, mantener en 0 (igual que $00) |
| `$0A` | `1 0 1 0` | `\/\/` | Triángulo repetitivo (abajo-arriba) |
| `$0B` | `1 0 1 1` | `\^^^` | Decaimiento simple, luego mantener en máx. (15) |
| `$0C` | `1 1 0 0` | `////` | Diente de sierra ascendente repetitivo |
| `$0D` | `1 1 0 1` | `/^^^` | Ataque simple, luego mantener en máx. (15) |
| `$0E` | `1 1 1 0` | `/\/\` | Triángulo repetitivo (arriba-abajo) |
| `$0F` | `1 1 1 1` | `/___` | Ataque simple, caer a 0, mantener en 0 (igual que $04) |

#### Formas de onda de envolvente

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

#### Usos prácticos de la envolvente

| Forma | Valor | Caso de uso |
|-------|-------|-------------|
| `$00` | `\___` | Decaimiento de percusión: golpe seco que se desvanece al silencio |
| `$08` | `\\\\` | Buzz-bass: tono bajo grueso repetitivo |
| `$0C` | `////` | Buzz-bass (fase invertida): mismo tono, timbre diferente |
| `$0A` | `\/\/` | Tono metálico/campana (modulación triangular) |
| `$0E` | `/\/\` | Tono metálico/campana (triángulo invertido) |
| `$0D` | `/^^^` | Fade-in: el volumen sube al máximo y se mantiene |

---

## Conversión de período de tono a frecuencia

### Fórmula

```
frecuencia = reloj_AY / (16 * período)
período    = reloj_AY / (16 * frecuencia)
```

### Reloj AY por plataforma

| Plataforma | Reloj AY | Reloj CPU | Relación |
|------------|----------|-----------|----------|
| ZX Spectrum 128K (PAL) | 1,773,400 Hz | 3,546,900 Hz | AY = CPU / 2 |
| ZX Spectrum 128K (NTSC) | 1,789,772 Hz | 3,579,545 Hz | AY = CPU / 2 |
| Pentagon 128 | 1,750,000 Hz | 3,500,000 Hz | AY = CPU / 2 |
| Amstrad CPC | 1,000,000 Hz | 4,000,000 Hz | AY = CPU / 4 |
| MSX | 1,789,772 Hz | 3,579,545 Hz | AY = CPU / 2 |
| Atari ST (YM2149) | 2,000,000 Hz | 8,000,000 Hz | YM = CPU / 4 |
| ZX Spectrum Next | 1,773,400 Hz | varía | Igual que 128K |

**Consecuencia práctica:** El mismo valor de período produce tonos ligeramente diferentes en diferentes plataformas. Una melodía compuesta en Pentagon (1.75 MHz) sonará fraccionalmente aguda en un Spectrum 128K (1.7734 MHz). Para la mayoría de propósitos musicales, la diferencia es inaudible.

### Tabla completa de frecuencias de notas

Todos los valores de período calculados para reloj AY = 1,773,400 Hz (PAL Spectrum 128K).

Las octavas 1-2 cubren el rango de bajos (territorio de buzz-bass). Las octavas 3-6 son el rango melódico principal. Las octavas 7-8 son agudas y cada vez más imprecisas debido al redondeo entero.

#### Octava 1 (bajo profundo)

| Nota | Frec (Hz) | Período | R_LO | R_HI |
|------|-----------|---------|------|------|
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

#### Octava 2 (bajo)

| Nota | Frec (Hz) | Período | R_LO | R_HI |
|------|-----------|---------|------|------|
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

#### Octava 3

| Nota | Frec (Hz) | Período | R_LO | R_HI |
|------|-----------|---------|------|------|
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

#### Octava 4 (octava media)

| Nota | Frec (Hz) | Período | R_LO | R_HI |
|------|-----------|---------|------|------|
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

#### Octava 5

| Nota | Frec (Hz) | Período | R_LO | R_HI |
|------|-----------|---------|------|------|
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

#### Octava 6

| Nota | Frec (Hz) | Período | R_LO | R_HI |
|------|-----------|---------|------|------|
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

#### Octava 7 (agudo)

| Nota | Frec (Hz) | Período | R_LO | R_HI |
|------|-----------|---------|------|------|
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

#### Octava 8 (muy aguda -- precisión limitada)

| Nota | Frec (Hz) | Período | R_LO | R_HI | Frec real | Error (cents) |
|------|-----------|---------|------|------|-----------|---------------|
| C-8  | 4186.01 | 26 | $1A | $00 | 4264.23 | +32 |
| C#8  | 4434.92 | 25 | $19 | $00 | 4433.50 | -1 |
| D-8  | 4698.63 | 24 | $18 | $00 | 4618.23 | -30 |
| D#8  | 4978.03 | 22 | $16 | $00 | 5038.07 | +21 |
| E-8  | 5274.04 | 21 | $15 | $00 | 5278.27 | +1 |
| F-8  | 5587.65 | 20 | $14 | $00 | 5541.88 | -14 |
| F#8  | 5919.91 | 19 | $13 | $00 | 5833.55 | -26 |
| G-8  | 6271.93 | 18 | $12 | $00 | 6158.75 | -32 |

**Nota:** Por encima de la octava 6, el redondeo entero del valor de período produce errores de tono cada vez más audibles. Las columnas "Frec real" y "Error" para la octava 8 muestran la frecuencia real de salida y la desviación en cents. Para notas agudas, el ajuste fino no es posible -- la resolución es simplemente demasiado gruesa.

### Tabla compacta de notas para código Z80

La mayoría de motores de tracker almacenan la tabla de períodos como palabras de 16 bits. Aquí hay una tabla práctica de 96 notas (octavas 1-8) para incluir en código fuente ensamblador:

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

### Tabla #5: Afinación natural (entonación justa)

La tabla de notas estándar de arriba usa temperamento igual (12-TET) -- cada semitono está separado por la raíz duodécima de 2. Esto funciona bien para canales de tono, pero crea un problema para **buzz-bass (T+E)**: como `período_envolvente = período_tono / 16`, cualquier período de tono no divisible por 16 introduce un error de redondeo. La envolvente se desfasa respecto al tono, produciendo batidos audibles en notas de bajo sostenidas.

La "Tabla de frecuencias con error cero" de Ivan Roshin (2001) y la implementación VTi de oisee (2009) resuelven esto usando **entonación justa** -- intervalos de razón entera para Do mayor / La menor:

```
C [9/8] D [10/9] E [16/15] F [9/8] G [10/9] A [9/8] B [16/15] C
```

Esto produce quintas puras (C--G, E--B, A--E a exactamente 3:2) y, críticamente, períodos donde la mayoría de notas de la escala principal se dividen uniformemente por 16.

**Reloj AY: 1,520,640 Hz** (no estándar; selecciona la frecuencia por tonalidad a continuación):

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

**Comprobación de divisibilidad del período (Octava 2, rango de bajos):**

| Nota | Período | mod 16 | Período env. | T+E limpio? |
|------|---------|--------|--------------|-------------|
| C2   | 1440   | 0      | 90         | Sí |
| C#2  | 1350   | 6      | 84         | No  |
| D2   | 1280   | 0      | 80         | Sí |
| D#2  | 1200   | 0      | 75         | Sí |
| E2   | 1152   | 0      | 72         | Sí |
| F2   | 1080   | 0      | 67         | ~   |
| F#2  | 1013   | 5      | 63         | No  |
| G2   | 960    | 0      | 60         | Sí |
| G#2  | 900    | 4      | 56         | No  |
| A2   | 864    | 0      | 54         | Sí |
| A#2  | 810    | 2      | 50         | No  |
| B2   | 768    | 0      | 48         | Sí |

Siete de doce notas (todas las notas naturales de Do mayor) se dividen limpiamente -- comparado con *cero* en la tabla de temperamento igual.

**Transposición vía frecuencia del chip:** como la tabla está fijada a Do/Lam, otras tonalidades requieren un reloj AY diferente. Cada paso multiplica por 2^(1/12):

| Tonalidad | Frecuencia del chip (Hz) |
|-----------|--------------------------|
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

En hardware el reloj AY es fijo; en trackers (Vortex Tracker II/Improved) y emuladores, esto es una configuración por módulo. La Tabla #5 es la predeterminada para el convertidor MIDI-a-PT3 autosiril porque la mayoría de pistas convertidas usan buzz-bass intensivamente. Ver Capítulo 11 para una explicación detallada del problema de alineación T+E.

---

## TurboSound: 2 x AY

TurboSound es una modificación de hardware que añade un segundo chip AY, proporcionando 6 canales de tono, 2 generadores de ruido y 2 generadores de envolvente. La implementación moderna más común es la tarjeta NedoPC TurboSound.

### Selección de chip

Ambos chips AY comparten los mismos puertos de E/S ($FFFD/$BFFD). Un valor de selección de chip escrito en $FFFD cambia todas las operaciones de registro subsiguientes al chip seleccionado.

| Valor de selección de chip | Destino |
|----------------------------|---------|
| `$FF` | Chip 0 (primario / AY original) |
| `$FE` | Chip 1 (AY secundario) |

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

**Importante:** La selección de chip persiste hasta que se cambie. Después de seleccionar el chip 1, todas las operaciones de registro -- incluyendo lecturas -- apuntan al chip 1. Siempre selecciona explícitamente el chip antes de cualquier acceso a registros en tu motor.

### Arquitectura del motor TurboSound

Un motor musical TurboSound típico mantiene dos búferes de registros de 14 bytes y los escribe secuencialmente:

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

Coste total: aproximadamente 28 instrucciones OUT, aproximadamente 700-800 T-states incluyendo overhead. Esto es cerca del 1% del presupuesto de fotograma -- despreciable.

### Configuración estéreo

TurboSound habilita estéreo verdadero. Los dos chips pueden tener paneo duro o mezcla:

| Configuración | Chip 0 (izquierda) | Chip 1 (derecha) | Carácter |
|---------------|---------------------|-------------------|----------|
| **Estéreo amplio** | Lead, bajo (A0+B0), percusión (C0) | Contra-melodía (A1+B1), pads (C1) | Espacioso, como en concierto |
| **Bajo centrado** | Bajo en C0 + C1 (mismos datos) | Lead en A0, armonía en A1 | Registro bajo sólido |
| **Percusión dividida** | Bombo (C0) | Caja + hi-hat (C1) | Percusión contundente y amplia |

Cada chip tiene su propio generador de ruido y generador de envolvente independientes. Esto significa que puedes ejecutar buzz-bass en el chip 0 y una percusión con envolvente completamente independiente en el chip 1 sin interferencia -- imposible con un solo AY.

---

## ZX Spectrum Next: Triple AY (3 x AY)

El ZX Spectrum Next incluye tres chips de sonido compatibles con AY, proporcionando 9 canales de tono, 3 generadores de ruido y 3 generadores de envolvente.

### Selección de chip en el Next

El Next extiende el protocolo TurboSound. El tercer chip se selecciona vía el mismo mecanismo:

| Valor de selección de chip | Destino |
|----------------------------|---------|
| `$FF` | Chip 0 |
| `$FE` | Chip 1 |
| `$FD` | Chip 2 |

El Next también proporciona acceso a través del registro Next $06 (Peripheral 2), que configura el modo del chip de sonido:

| Reg Next $06, bits 1-0 | Modo |
|--------------------------|------|
| `%00` | AY simple (compatible con Spectrum 128K) |
| `%01` | TurboSound (2 x AY) |
| `%10` | Triple AY (3 x AY) |

### Paneo estéreo por canal

El Next añade una característica que el AY original nunca tuvo: paneo estéreo por canal. Cada uno de los 9 canales puede ser paneado individualmente a izquierda, derecha o centro.

El paneo se controla a través del registro AY 14 (R14), reutilizado en el Next como un registro de control estéreo cuando se accede en el contexto del chip AY:

| Bit | Canal | 0 = | 1 = |
|-----|-------|-----|-----|
| 0 | A, derecha | off | on |
| 1 | A, izquierda | off | on |
| 2 | B, derecha | off | on |
| 3 | B, izquierda | off | on |
| 4 | C, derecha | off | on |
| 5 | C, izquierda | off | on |

Activa ambos bits (izquierda + derecha) para paneo central. Activa solo un bit para paneo duro a izquierda o derecha.

---

## Patrones comunes en código Z80

### Silenciar el AY

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

### Tocar una sola nota en el canal A

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

### Disparar una nota buzz-bass

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

### Disparar envolvente (reinicio)

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

### Golpe de percusión digital (DAC de 4 bits)

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

Ver Capítulo 12 para la técnica de tambores digitales híbridos (ataque digital + decaimiento con envolvente AY) que hace esto práctico en un motor de demo.

---

## Notas sobre formatos de tracker

### ProTracker 3 (.pt3)

**ProTracker 3** (PT3) es el formato de tracker más ampliamente usado en el ZX Spectrum 128K. El editor multiplataforma **Vortex Tracker II** produce nativamente archivos .pt3.

| Propiedad | Valor |
|-----------|-------|
| Canales | 3 (AY simple) o 6 (TurboSound) |
| Longitud de patrón | 1-64 filas |
| Velocidad de canción | 1-255 (fotogramas por fila) |
| Instrumentos | Tablas de ornamento + envolventes de amplitud |
| Efectos | Arpegio, portamento, vibrato, control de envolvente |
| Tamaño del reproductor | ~1.2-1.8 KB (ensamblador Z80) |
| Formato de datos | Patrones empaquetados + tablas de instrumentos/ornamentos |

#### Cómo los datos PT3 se mapean a los registros AY

En cada fotograma (1/50 de segundo), el reproductor PT3:

1. Decrementa el contador de velocidad. Si llega a cero, avanza a la siguiente fila.
2. Para cada canal (A, B, C):
   - Lee la nota, instrumento y efecto de la fila actual.
   - Aplica el ornamento del instrumento (tabla de desplazamiento de tono por fotograma).
   - Aplica la envolvente de amplitud del instrumento (tabla de volumen por fotograma).
   - Calcula el período de tono y volumen finales.
3. Actualiza el registro del mezclador (R7) según qué canales usan tono, ruido o ambos.
4. Escribe todos los valores calculados en R0-R13.

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

#### Integración en tu proyecto

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

### Otros formatos de tracker

| Formato | Tracker | Canales | Tamaño reproductor | Característica clave |
|---------|---------|---------|--------------------|-----------------------|
| .pt3 | Pro Tracker 3 / Vortex Tracker II | 3-6 | ~1.2-1.8 KB | Estándar de la industria. Ornamentos + muestras. |
| .pt2 | Pro Tracker 2 | 3 | ~0.8-1.0 KB | Más antiguo, más simple. Todavía usado por razones de tamaño. |
| .stc | Sound Tracker / Sound Tracker Pro | 3 | ~0.5-0.7 KB | Formato más antiguo del Spectrum. Sin ornamentos. |
| .asc | ASC Sound Master | 3 | ~0.8-1.0 KB | Reproductor compacto. Favorito de la escena rusa. |
| .sqt | SQ-Tracker | 3 | ~0.6-0.8 KB | Excelente compresión de datos. |
| .ay  | Contenedor de emulación AY | varía | N/A | Captura volcados crudos de registros. Para emuladores, no motores de reproducción. |

### Vortex Tracker II

**Vortex Tracker II** es el estándar moderno para componer música AY. Se ejecuta en Windows (y vía Wine en Linux/macOS), y exporta directamente archivos .pt3 compatibles con todos los reproductores Z80 estándar.

Características clave para uso en la demoscene:
- **Modo TurboSound:** Editar 6 canales (2 x AY) en un solo módulo.
- **Editor de ornamentos:** Tablas visuales de desplazamiento de tono por fotograma.
- **Editor de muestras:** Control de amplitud + tono/ruido por fotograma.
- **Puntos de bucle:** Establecer inicio de bucle para cada patrón y para la canción completa.
- **Exportación:** .pt3 (nativo), .txt (volcado de texto plano para análisis), .wav (renderizado de audio).

El flujo de trabajo típico de la demoscene:
1. Componer en Vortex Tracker II.
2. Exportar como .pt3.
3. Incluir el `pt3player.asm` estándar (ampliamente disponible, múltiples versiones optimizadas para tamaño o velocidad).
4. `INCBIN` los datos .pt3.
5. Llamar a `music_init` y `music_play` como se muestra arriba.

---

## AY-3-8910 vs YM2149: diferencias que importan

El Yamaha YM2149 (usado en el Atari ST y algunos clones Spectrum) es compatible pin a pin con el AY-3-8910 pero no idéntico a nivel de bits:

| Característica | AY-3-8910 | YM2149 |
|----------------|-----------|--------|
| Curva de volumen | Logarítmica (1.5 dB/paso) | Lineal |
| LFSR de ruido | 17 bits, taps específicos | 17 bits, taps diferentes |
| Precisión de envolvente | 16 pasos de volumen (4 bits) | 32 pasos de volumen (5 bits internamente) |
| Pin 26 (SEL) | Divisor de reloj | Igual, pero a menudo cableado fijo |
| DAC de salida | Escalera de resistencias de 4 bits | Escalera de resistencias de 5 bits |

**Impacto práctico:** La misma melodía suena más cálida/con más cuerpo en un AY-3-8910 real y más brillante/más delgada en un YM2149 debido a las diferentes curvas de volumen. Los emuladores típicamente te permiten seleccionar qué chip emular. Cuando pruebes tu música, prueba ambos -- tu audiencia puede tener cualquiera de los dos chips en su máquina.

---

## Tarjeta de referencia rápida

### Resumen de registros (desprendible)

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

> **Fuentes:** General Instrument AY-3-8910 / AY-3-8912 datasheet (1979); Yamaha YM2149 Application Manual; Dark "GS Sound System" (Spectrum Expert #01, 1997); Introspec "Eager" making-of (Hype 2015); Vortex Tracker II documentation (S.V. Bulba); NedoPC TurboSound FM documentation; ZX Spectrum Next User Manual, Issue 2
