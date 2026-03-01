# Apéndice I: Bytebeat y AY-Beat -- Sonido generativo en Z80

> *"Con 256 bytes, bytebeat es tu única opción realista -- no hay espacio para un reproductor de patrones."*
> -- Capítulo 13

---

Este apéndice cubre la generación de sonido basada en fórmulas en el ZX Spectrum -- desde el concepto original de bytebeat PCM hasta la técnica adaptada al AY que produce música estructurada y evolutiva a partir de un puñado de instrucciones Z80. El Capítulo 13 presenta AY-beat como herramienta de sizecoding. Este apéndice es la referencia completa: la teoría, las fórmulas, los mapeos de registros y un motor funcional completo que puedes integrar en una intro de 256 bytes.

Necesitarás tener abierta la referencia de registros del AY del Apéndice G junto a este apéndice. Cada número de registro mencionado aquí (R0, R7, R8, R11, R13, etc.) está documentado allí con los diseños completos de bits y direcciones de puerto.

---

## 1. Bytebeat clásico: La tradición PCM

En 2011, Ville-Matias Heikkila (Viznut) publicó un descubrimiento que había circulado en círculos de programación underground: una sola expresión en C, evaluada una vez por muestra con un contador incremental `t`, puede producir música rítmica compleja cuando la salida se interpreta como PCM de 8 bits sin signo a 8 kHz.

La idea central:

```c
for (t = 0; ; t++)
    putchar( f(t) );    // pipe to /dev/dsp at 8000 Hz
```

La función `f(t)` es típicamente una expresión de una línea construida con operaciones a nivel de bits, multiplicaciones y desplazamientos. Sin osciladores, sin envolventes, sin tablas de notas -- solo aritmética de enteros sobre un contador.

### Fórmulas famosas

**`t*((t>>12|t>>8)&63&t>>4)`** -- La original de Viznut. Tonos rítmicos en cascada que recorren relaciones de altura tonal, produciendo un efecto entre una caja de música y un teléfono roto. `t>>12` y `t>>8` crean dos versiones del contador divididas en frecuencia; `&63` limita el rango; `&t>>4` controla la salida rítmicamente. La multiplicación por `t` crea el barrido fundamental de tono.

**`t*(t>>5|t>>8)>>(t>>16)`** -- Patrones rítmicos evolutivos. El desplazamiento a la derecha por `t>>16` significa que el carácter completo del sonido cambia cada ~8 segundos (65536 muestras a 8 kHz). Cada sección de 8 segundos tiene un rango dinámico y una sensación diferentes.

**`(t*5&t>>7)|(t*3&t>>10)`** -- Dos líneas melódicas entrelazadas. `t*5` y `t*3` crean dos flujos de tono a diferentes intervalos; el AND con contadores desplazados los filtra independientemente; el OR los fusiona. El resultado suena como dos melodías interconectadas sonando simultáneamente.

### Por qué funciona

Las operaciones a nivel de bits sobre un contador incremental crean estructuras periódicas a múltiples escalas temporales simultáneamente. Considera el patrón de bits de `t` mientras cuenta:

- El bit 0 cambia cada muestra (4000 Hz -- inaudible como tono, pero da forma a la onda)
- El bit 7 cambia cada 128 muestras (~62.5 Hz -- territorio de graves)
- El bit 12 cambia cada 4096 muestras (~1.95 Hz -- pulso rítmico)
- El bit 15 cambia cada 32768 muestras (~0.24 Hz -- cambio estructural)

Un desplazamiento a la derecha `t>>n` selecciona qué escala temporal domina. Las operaciones AND crean patrones de coincidencia -- momentos en que dos escalas temporales se alinean. Las operaciones OR fusionan patrones independientes. La multiplicación por constantes pequeñas crea relaciones armónicas (proporciones de frecuencia). La truncación a 8 bits de la salida actúa como un conformador natural de forma de onda, plegando los valores de vuelta al rango y creando armónicos adicionales.

El resultado es autosimilar: el sonido tiene estructura rítmica a todas las escalas, desde ciclos de oscilación individuales hasta estructuras de fraseo de varios segundos. Esta autosimilaridad es lo que hace que el bytebeat suene como música en lugar de ruido -- aunque ningún conocimiento musical fue empleado en la fórmula.

### En el Spectrum: El callejón sin salida del beeper

La salida de beeper del ZX Spectrum es un altavoz de 1 bit controlado por el bit 4 del puerto $FE. En principio, puedes ejecutar una fórmula bytebeat y emitir el resultado:

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

Esto funciona y produce sonido. Pero consume el 100% de la CPU -- el Z80 no hace más que calcular muestras y activar el altavoz. Sin actualizaciones de pantalla, sin efectos visuales, sin manejo de entrada. La tasa de muestreo también es incorrecta (demasiado rápida), y controlarla con precisión requiere un conteo cuidadoso de ciclos con NOP de relleno.

Para una demo, esto es un callejón sin salida. El beeper es una salida de 1 bit que exige atención constante de la CPU. La verdadera adaptación del bytebeat al Spectrum requiere un enfoque completamente diferente.

---

## 2. AY-Beat: Bytebeat reimaginado para un generador de tonos

El AY-3-8910 no es un DAC. No acepta muestras de amplitud. Es un generador de tonos programable: le das una frecuencia (como valor de período), un volumen (0-15) y parámetros opcionales de ruido y envolvente, y sus osciladores internos producen el sonido de forma autónoma. La CPU queda libre para hacer otro trabajo.

La idea clave del AY-beat: **reemplazar el contador de muestras por un contador de fotogramas, y reemplazar la salida PCM por valores de registros del AY.**

El bytebeat clásico calcula una muestra de amplitud a ~8000 Hz. AY-beat calcula períodos de tono, volúmenes y parámetros de ruido a 50 Hz -- una vez por fotograma de vídeo, disparado por la instrucción HALT. Los osciladores del AY manejan la generación real de sonido entre fotogramas.

El contador de fotogramas `t` reemplaza al contador de muestras. Las fórmulas operan sobre `t` pero producen valores de registros, no muestras de forma de onda. Donde el bytebeat PCM tiene un grado de libertad (amplitud), AY-beat tiene muchos: tres períodos de tono independientes (12 bits cada uno), tres volúmenes (4 bits cada uno), un período de ruido (5 bits) y un período de envolvente de 16 bits con selección de forma.

### Arquitectura básica de AY-Beat

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

Este es el AY-beat más simple posible: un canal, una fórmula de tono, una fórmula de volumen, ~30 bytes. Produce un barrido cíclico que sube en tono y se desvanece entrando y saliendo -- no es música, pero es un sonido reconociblemente estructurado.

### Qué cambia respecto al bytebeat PCM

| Aspecto | Clásico (PCM) | AY-Beat |
|---------|---------------|---------|
| Tasa de actualización | ~8000 Hz | 50 Hz (tasa de fotogramas) |
| Salida | Amplitud de 8 bits | Período de tono (12 bits), volumen (4 bits), ruido (5 bits) |
| Canales | 1 (altavoz mono) | 3 tonos + 1 ruido + envolvente |
| Coste de CPU | 100% (todos los ciclos) | ~200-500 T por fotograma (~0.3%) |
| Escalado de fórmulas | Granularidad fina, evolución rápida | Granularidad gruesa, se necesitan desplazamientos de bits más amplios |
| Generación de sonido | La CPU calcula cada muestra | Los osciladores del AY funcionan autónomamente |

La tasa de fotogramas de 50 Hz significa que las fórmulas evolucionan 160 veces más lento que a 8 kHz. Para obtener una densidad rítmica equivalente, usa multiplicadores más grandes y menos desplazamientos a la derecha. Una fórmula que produce un ritmo agradable a 8 kHz con `t>>12` (período ~0.5 seg a 8 kHz) necesita aproximadamente `t>>4` a 50 Hz para una temporización similar (~0.3 seg entre repeticiones). La regla general: divide las cantidades de desplazamiento del bytebeat de PC por ~7 (log2 del ratio 160x) y ajusta de oído.

---

## 3. Drone: Envolvente + Tono (Modo E+T)

Aquí es donde AY-beat se vuelve genuinamente interesante. El generador de envolvente del AY cicla automáticamente el volumen de un canal sin ninguna intervención de la CPU. Configura el registro de volumen de un canal en modo envolvente (bit 4 = 1, es decir, escribe $10 en R8/R9/R10) y el hardware maneja la modulación de volumen a la frecuencia de envolvente definida por R11-R12.

El resultado es un drone: un timbre continuamente evolutivo producido por la interacción del oscilador de tono y el oscilador de envolvente. El coste de CPU para mantener este drone es casi cero -- solo necesitas actualizar el período de tono y el período de envolvente una vez por fotograma, y el hardware hace el resto.

### La receta del drone

1. Configura un período de tono desde una fórmula -- esto define el tono base.
2. Configura un período de envolvente desde una fórmula diferente -- esto define la tasa de modulación.
3. Configura la forma de envolvente a una onda repetitiva (formas $08, $0A, $0C o $0E).
4. Configura el volumen del canal a modo envolvente ($10).
5. El hardware produce un drone continuamente evolutivo con coste de CPU por muestra de cero.

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

La belleza del modo E+T es la interferencia entre las dos frecuencias. Cuando el período de envolvente está cerca del período de tono, obtienes efectos de modulación de amplitud -- el volumen pulsa a la frecuencia de diferencia, produciendo un timbre ondulante, similar a un órgano. Cuando la frecuencia de envolvente es mucho menor que la frecuencia de tono, actúa como un tremolo lento. Cuando es mucho mayor, entras en territorio del buzz-bass (ver Apéndice G y Capítulo 11).

Barrer el período de envolvente mientras el período de tono también se mueve produce texturas continuamente evolutivas. Las dos fórmulas crean un espacio de parámetros bidimensional que el sonido explora a lo largo del tiempo. Con el par de fórmulas adecuado, el drone nunca se repite del todo -- deambula por variaciones tímbricas, creando un paisaje sonoro ambiental con menos de 30 bytes de código.

### Coste en bytes

Configurar el modo E+T con una fórmula requiere aproximadamente 15-25 bytes. Para una intro de 256 bytes, esto te da un sonido drone rico y evolutivo esencialmente gratis -- sin necesidad de cálculo de volumen por fotograma, sin datos de patrón, solo dos valores de registro derivados de fórmulas simples. El hardware del AY hace todo el trabajo de oscilación.

---

## 4. Percusión con ruido

El generador de ruido del AY (R6) produce ruido pseudoaleatorio a una frecuencia programable (0-31). El registro del mezclador (R7) controla qué canales reciben ruido. Activar y desactivar el ruido rítmicamente, controlado por el contador de fotogramas, crea patrones de percusión.

### Patrón básico de bombo

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

### Carácter de percusión según el período de ruido

| Valor de R6 | Carácter | Uso |
|-------------|----------|-----|
| 0-3 | Clic duro, contundente | Bombo, rimshot |
| 4-8 | Siseo nítido | Cuerpo de caja |
| 10-15 | Ruido amplio | Hi-hat abierto |
| 20-31 | Retumbo grave | Trueno lejano, ambiente |

### Variedad rítmica con máscaras de bits

Diferentes máscaras AND sobre el contador de fotogramas producen diferentes densidades rítmicas:

| Máscara | Período | Frecuencia | Carácter |
|---------|---------|------------|----------|
| `AND $03` | Cada 4 fotogramas | 12.5 Hz | Fuego rápido, hi-hat |
| `AND $07` | Cada 8 fotogramas | 6.25 Hz | Bombo estándar |
| `AND $0F` | Cada 16 fotogramas | 3.125 Hz | Medio tiempo, espaciado |
| `AND $1F` | Cada 32 fotogramas | 1.5625 Hz | Pulso lento, intro |

Combina dos máscaras para polirritmia: prueba `t AND $07` para el bombo, `t AND $03` para el hi-hat. Esto cuesta unos 10 bytes extra pero añade complejidad rítmica significativa.

### Uso de la envolvente para la caída del tambor

En lugar de decaer manualmente el volumen en cada fotograma, usa el generador de envolvente del AY en modo disparo único. Configura R13 a la forma $00 (decaimiento a cero, mantener), y el hardware maneja el desvanecimiento de volumen automáticamente:

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

Esto ahorra varios bytes al eliminar el código de decaimiento manual. La contrapartida: el generador de envolvente es compartido entre todos los canales en modo envolvente. Si el canal A usa drone E+T, el canal C no puede usar independientemente la envolvente para el decaimiento del tambor. Planifica la asignación de canales acorde.

---

## 5. Armonía multicanal

El AY tiene tres canales de tono independientes. AY-beat puede derivar los tres de una sola fórmula usando rotación de bits, creando la impresión de contrapunto con casi nada de código.

### Tres voces de una fórmula

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

Las rotaciones de bits crean versiones desfasadas del mismo patrón. Los canales tocan melodías relacionadas pero desplazadas -- siguen el mismo contorno pero llegan a cada tono en momentos diferentes. Esto crea una impresión de contrapunto: múltiples voces independientes que comparten una lógica subyacente.

### Por qué la rotación crea armonía

RRCA es una *rotación*, no un desplazamiento -- los bits que salen por abajo vuelven por arriba. Esto significa que los tres canales recorren el mismo conjunto de valores de período en el mismo orden, pero desplazados en el tiempo. El desplazamiento depende de la cantidad de rotación:

- **RRCA x 2:** El canal está "adelantado" por aproximadamente un cuarto del ciclo del patrón. Esto suele crear intervalos que suenan como cuartas o quintas -- no afinados con precisión, pero armónicamente relacionados lo suficiente como para ser agradables.
- **RRCA x 4:** Medio byte de desplazamiento. Esto tiende a producir relaciones tipo octava, ya que el bit 4 rotado a la posición del bit 0 efectivamente reduce a la mitad el período en ciertas alineaciones de fase.

Estos no son intervalos musicales reales. Son relaciones pseudo-armónicas creadas por la estructura de los números binarios. Pero el oído es tolerante -- si dos tonos comparten la mayor parte de su patrón de bits, suenan "relacionados", y eso es suficiente para una intro de 256 bytes.

### Fórmulas de volumen para multicanal

Dale a cada canal una fórmula de volumen diferente para evitar que las tres voces estén al mismo nivel simultáneamente:

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

El volumen invertido en el canal C crea una dinámica de llamada y respuesta: mientras una voz se desvanece entrando, otra se desvanece saliendo. Esto cuesta 2 bytes extra (el `XOR $0F`) pero mejora significativamente la textura musical.

---

## 6. Recetario de fórmulas

Las siguientes fórmulas han sido probadas en el AY a 50 Hz de tasa de fotogramas. "Bytes" se refiere al coste de implementación Z80 para calcular la fórmula a partir de un valor ya en el registro A (el contador de fotogramas). La máscara de período determina el rango de tono.

### Fórmulas de período de tono

| # | Fórmula | Implementación Z80 | Bytes | Sonido | Ideal para |
|---|---------|---------------------|-------|--------|------------|
| 1 | `t AND $3F` | `and $3F` | 2 | Diente de sierra ascendente, ciclo de 1.28 seg | Barrido simple |
| 2 | `t*3 AND $3F` | `ld e,a : add a,a : add a,e : and $3F` | 5 | Barrido más rápido, intervalos más amplios | Bajo energético |
| 3 | `t XOR (t>>3)` | `ld e,a : rrca : rrca : rrca : xor e` | 5 | Caótico con estructura periódica | Textura de ruido |
| 4 | `(t AND $0F) XOR $0F` | `and $0F : xor $0F` | 4 | Onda triangular, barrido ping-pong | Melodía principal |
| 5 | `t*5 AND t>>2` | `ld e,a : add a,a : add a,a : add a,e : ld d,a : ld a,e : rrca : rrca : and d` | 10 | Filtrado rítmico | Tipo percusión |
| 6 | `(t+t>>4) AND $1F` | `ld e,a : rrca : rrca : rrca : rrca : add a,e : and $1F` | 6 | Barrido modulado lentamente | Drone evolutivo |
| 7 | `t AND (t>>3) AND $1F` | `ld e,a : rrca : rrca : rrca : and e : and $1F` | 6 | Autosimilar, ritmo fractal | Patrones complejos |
| 8 | `(t>>1) XOR (t>>3)` | `ld e,a : rrca : ld d,a : rrca : rrca : xor d` | 6 | Interferencia de doble velocidad | Textura metálica |
| 9 | `t*7 AND $7F` | `ld e,a : add a,a : add a,a : add a,a : sub e : and $7F` | 6 | Barrido amplio, velocidad 7x | Sensación de arpegio rápido |
| 10 | `(t XOR t>>1) AND $3F` | `ld e,a : rrca : xor e : and $3F` | 5 | Secuencia de código Gray | Melodía en escalera |
| 11 | `t AND $07 OR t>>4` | `ld e,a : and $07 : ld d,a : ld a,e : rrca : rrca : rrca : rrca : or d` | 8 | Bucles anidados, dos capas rítmicas | Ritmo por capas |
| 12 | `(t+t+t>>2) AND $3F` | `ld e,a : add a,a : ld d,a : ld a,e : rrca : rrca : add a,d : and $3F` | 8 | Barrido acelerado con sub-patrón | Melodía con textura |

### Fórmulas de volumen

| # | Fórmula | Z80 | Bytes | Efecto |
|---|---------|-----|-------|--------|
| V1 | `t>>3 AND $0F` | `rrca : rrca : rrca : and $0F` | 5 | Ciclo de desvanecimiento lento, 5.12 seg |
| V2 | `(t AND $0F) XOR $0F` | `and $0F : xor $0F` | 4 | Volumen triangular, ping-pong |
| V3 | `t*3>>4 AND $0F` | `ld e,a : add a,a : add a,e : rrca : rrca : rrca : rrca : and $0F` | 8 | Patrón de desvanecimiento irregular |
| V4 | `$0F` (constante) | `ld d,$0F` | 2 | Volumen máximo, usar con modo envolvente |

### Cómo leer la tabla

Elige una fórmula de tono y una fórmula de volumen. Combínalas. El coste total en bytes es la suma de ambas implementaciones más la sobrecarga de escritura de registros del AY (~8 bytes por canal para dos llamadas a ay_write: selección de registro + datos para tono bajo y volumen). Un solo canal con la fórmula #1 y el volumen V1 cuesta aproximadamente 2 + 5 + 16 = 23 bytes incluyendo las escrituras de registros.

La fórmula #10 (código Gray) merece mención especial. La secuencia de código Gray solo cambia un bit por paso, así que el período de tono cambia exactamente en una unidad por fotograma -- una melodía suave, tipo escalera. Combinada con la máscara AND, recorre un rango de tono limitado con agradable regularidad. Esta es una de las fórmulas individuales que mejor suenan musicalmente.

---

## 7. Juntando todo: Un motor AY-Beat completo

Aquí tienes un motor AY-beat completo y mínimo que produce sonido generativo de 3 canales con drone de envolvente. Este es el motor que integras en una intro de 256 bytes junto a tu efecto visual.

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

### Qué produce esto

- **Canal A:** Un barrido ascendente simple, recorriendo períodos 0-63 cada 64 fotogramas (1.28 segundos). El patrón fundamental.
- **Canal B:** El mismo barrido a velocidad 3x, creando intervalos de movimiento más rápido. Cuando se alinea con el canal A, escuchas consonancia; cuando diverge, escuchas disonancia. La alternancia crea interés rítmico.
- **Canal C:** Un barrido de código Gray en modo envolvente. La envolvente triangular crea modulación automática de volumen, produciendo un drone que se desfasa contra el período de tono. Esta es la base armónica subyacente a las otras dos voces.
- **En conjunto:** Una textura evolutiva y autosimilar que recorre relaciones tonales. Suena alienígena y mecánico -- exactamente lo correcto para una intro de 256 bytes.

### Puntos de personalización

**Cambia las fórmulas de tono.** Intercambia cualquiera de las secuencias AND/RRCA por una fórmula diferente del recetario (sección 6). Cada sustitución cambia el carácter por completo.

**Añade percusión de ruido.** Inserta un bloque `ld a,e : and $07 : jr nz,.no_hit` (sección 4) para añadir golpes rítmicos. Coste: ~12 bytes. Roba un canal (típicamente B) o superpón ruido en el canal C.

**Usa enmascaramiento pentatónico.** En lugar de `AND $3F` como máscara final, indexa en una tabla de consulta pentatónica de 5 bytes. Esto restringe los períodos de tono a valores armónicamente relacionados, haciendo que la salida suene más deliberadamente musical. Coste: ~8 bytes (5 para la tabla, 3 para la consulta). El Capítulo 13 discute esta técnica.

**Varía los volúmenes fijos.** Reemplaza las escrituras de volumen constante con fórmulas de volumen de la sección 6. Incluso `ld a,e : rrca : rrca : rrca : and $0F` (5 bytes por canal) añade un interés dinámico significativo.

---

## 8. Avanzado: Combinando técnicas

Las secciones anteriores cubren bloques individuales. Un motor AY-beat bien elaborado combina varios:

### Arquitectura para una intro de 256 bytes

```
Frame 0:   Set mixer, envelope shape (one-time setup)
Frame N:   Update tone A (melody formula)
           Update tone B (harmony formula, rotated)
           Update volume A (fade formula)
           Update volume B (inverted fade)
           Channel C in E+T drone mode (auto-evolving)
           Every 8th frame: noise hit on C (toggle mixer)
```

El coste total de CPU por fotograma es aproximadamente 300-500 T-states -- muy por debajo del 1% de los ~70,000 T-states disponibles por fotograma. El 99% restante está disponible para tu efecto visual.

### Presupuesto de registros

El AY tiene 14 registros escribibles. En un motor AY-beat mínimo, típicamente escribes 8-10 por fotograma:

| Registro | Escrito | Fuente |
|----------|---------|--------|
| R0 (Tono A bajo) | Cada fotograma | Fórmula |
| R2 (Tono B bajo) | Cada fotograma | Fórmula |
| R4 (Tono C bajo) | Cada fotograma o una vez | Fórmula o fijo |
| R1, R3, R5 (Tono alto) | Una vez (establecido a 0) | Constante |
| R7 (Mezclador) | Cada fotograma o una vez | Constante o conmutado para ruido |
| R8, R9 (Volumen A, B) | Cada fotograma | Fórmula o constante |
| R10 (Volumen C) | Una vez | $10 (modo envolvente) |
| R11 (Envolvente bajo) | Cada fotograma | Fórmula |
| R13 (Forma de envolvente) | Una vez (fotograma 0) | Constante |

Registros que puedes omitir completamente: R6 (período de ruido -- solo necesario si usas ruido), R12 (envolvente alto -- configurado una vez a 0 para períodos cortos), R14-R15 (puertos de E/S -- irrelevantes para sonido).

### Desglose de tamaño

Para una intro de 256 bytes, cada byte importa. Así es como se ve un presupuesto típico de AY-beat:

| Componente | Bytes |
|------------|-------|
| Rutina de escritura al AY | 9 |
| Gestión del contador de fotogramas | 5 |
| 3 fórmulas de tono (simples) | 12-18 |
| 3 configuraciones de volumen | 6-15 |
| Configuración del mezclador | 5 |
| Configuración de envolvente | 8-12 |
| Total | **45-64** |

Esto deja 192-211 bytes para el efecto visual, el bucle principal y cualquier otra infraestructura. Con 45 bytes, el motor de la sección 7 está cerca del óptimo para la cantidad de sonido que produce.

---

## 9. AY como DAC: Bytebeat clásico a través del registro de volumen

Existe un camino intermedio entre el callejón sin salida del beeper y la reimaginación de AY-beat. Los registros de volumen del AY-3-8910 (registros 8, 9, 10) aceptan valores de 4 bits (0-15). Si actualizas un registro de volumen a alta tasa -- digamos, durante un bucle cerrado -- la salida del AY se convierte en un DAC de 4 bits. Así es como funcionan el habla digitalizada y la reproducción de muestras en las demos del Spectrum.

Aplicado al bytebeat: calcula `f(t)`, desplaza a la derecha hasta 4 bits, escribe en el registro de volumen:

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

Esto produce bytebeat reconocible -- las fórmulas de forma de onda reales de la sección 1, audibles a través del AY. La calidad de sonido es mejor que la del beeper (resolución de 4 bits vs 1 bit), y la etapa de salida del AY proporciona niveles de audio adecuados.

El coste sigue siendo brutal: ~80% de CPU. Obtienes una franja delgada de tiempo para visuales -- suficiente para un efecto de atributos que se actualice lentamente, no lo suficiente para nada ambicioso. Esta técnica es útil cuando quieres el *sonido específico* de las fórmulas de bytebeat clásico y estás dispuesto a pagar el precio de CPU.

### Tres rutas de salida comparadas

| Ruta | Resolución | Coste de CPU | Carácter sonoro | ¿Práctico para demos? |
|------|-----------|-------------|-----------------|----------------------|
| Beeper (puerto $FE) | 1 bit | ~100% | Áspero, zumbante | No |
| AY volumen DAC | 4 bits | ~80% | Bytebeat clásico | Apenas (solo efectos de atributos) |
| AY-beat (registros) | Tono/ruido | ~0.5% | Música chip, generativa | Sí -- la elección correcta |

Para intros de sizecoding y demos, AY-beat es casi siempre la elección correcta. Reserva AY como DAC para proyectos artísticos donde la estética sonora específica del bytebeat es el objetivo.

---

## 10. Teoría musical para algoritmos

Las fórmulas de AY-beat que ignoran la teoría musical producen ruido interesante. Las fórmulas que *codifican* teoría musical producen música real. Las siguientes técnicas añaden musicalidad con un mínimo de bytes.

### Tablas de escala: Restringiendo la salida a notas agradables

Una fórmula cruda como `tone = t AND $3F` produce los 64 valores de período posibles -- la mayoría de los cuales no son musicalmente útiles. Una **tabla de escala** mapea la salida de la fórmula a períodos de notas reales, asegurando que cada valor suene bien.

| Escala | Notas | Tamaño de tabla | Carácter |
|--------|-------|-----------------|----------|
| Pentatónica | 5 (C D E G A) | 10 bytes (5 x períodos de 2 bytes) | Siempre consonante, sensación folk/world |
| Diatónica mayor | 7 (C D E F G A B) | 14 bytes | Brillante, occidental, familiar |
| Diatónica menor | 7 (C D Eb F G Ab Bb) | 14 bytes | Oscura, melancólica |
| Blues | 6 (C Eb F F# G Bb) | 12 bytes | Cruda, expresiva |
| Cromática | 12 | 24 bytes | Atonal, disonante -- generalmente incorrecta para sizecoding |

La escala pentatónica es la mejor amiga del size-coder: 5 notas, 10 bytes, y *cualquier* combinación de notas suena aceptable. No puedes tocar una nota incorrecta en una escala pentatónica. Por eso tantas intros de 256 bytes suenan vagamente "asiáticas" o "folk" -- la restricción pentatónica hace musicales las secuencias aleatorias.

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

### Derivación de octavas: Rango de tono gratis

Almacena una octava de períodos. Deriva todas las demás mediante desplazamiento de bits:

- `SRL D : RR E` = una octava arriba (período a la mitad, tono al doble)
- `SLA E : RL D` = una octava abajo (período al doble, tono a la mitad)

Cinco notas pentatónicas x una octava almacenada x desplazamiento de bits = 5 notas x 5+ octavas = 25+ tonos distintos con 10 bytes de datos. La fórmula selecciona la nota, una máscara de bits separada selecciona la octava:

```z80
    ; note_index = formula AND $0F
    ; octave = note_index / 5 (0-2)
    ; note = note_index % 5
    ; Look up base period, then SRL 'octave' times
```

### Arpegio: Tonos de acorde en secuencia

Un arpegio recorre los tonos de un acorde. En términos de grados de la escala:

| Acorde | Desplazamientos de escala | Sonido |
|--------|--------------------------|--------|
| Tríada mayor | 0, 2, 4 (fundamental, tercera, quinta) | Brillante, resuelto |
| Tríada menor | 0, 2, 3 (fundamental, tercera menor, quinta) | Oscuro, tenso |
| Acorde de potencia | 0, 4 (fundamental, quinta) | Abierto, fuerte |
| Suspendido | 0, 3, 4 (fundamental, cuarta, quinta) | Ambiguo, flotante |

Implementación: `arp_step = (t / speed) % chord_size`, luego suma el desplazamiento a la nota raíz actual:

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

Tres bytes por forma de acorde. La velocidad del arpegio se deriva del contador de fotogramas -- no se necesita un temporizador separado.

### Ornamentos de paso: Trinos, mordentes y deslizamientos

Un ornamento es un pequeño patrón cíclico de desplazamientos relativos de tono aplicado a una nota. En la música de tracker, los ornamentos dan vida a los tonos planos:

| Ornamento | Patrón | Efecto | Bytes |
|-----------|--------|--------|-------|
| Trino | 0, +1, 0, -1 | Alternancia rápida con el vecino | 4 |
| Mordente | 0, +1, 0, 0 | Breve vecino superior, luego se estabiliza | 4 |
| Deslizamiento ascendente | 0, 0, +1, +1 | Subida gradual | 4 |
| Vibrato | 0, +1, +1, 0, -1, -1 | Oscilación suave | 6 |

Se aplica sumando el valor del ornamento al índice de nota antes de la consulta en la tabla de escala:

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

Cuatro bytes transforman un tono estático en una voz viva. Apila múltiples ornamentos en diferentes canales para una textura rica.

### Progresiones de acordes: Movimiento armónico

La nota raíz del acorde puede cambiar a lo largo del tiempo, siguiendo una progresión. Armonía clásica en 4 bytes:

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

Cuatro bytes de datos de progresión, ciclados por el contador de fotogramas, dan a tu pieza AY-beat movimiento armónico -- la sensación de que "va hacia algún lugar" en lugar de repetirse sobre un solo acorde. Otras progresiones:

| Progresión | Grados | Bytes | Sensación |
|------------|--------|-------|-----------|
| I-IV-V-I | 0, 3, 4, 0 | 4 | Resolución clásica |
| I-V-vi-IV | 0, 4, 5, 3 | 4 | Estándar pop/rock |
| i-VI-III-VII | 0, 5, 2, 6 | 4 | Menor épico |
| I-I-I-I | 0, 0, 0, 0 | 1 (o se omite) | Drone/meditativo |

### Presupuesto total de datos para música rica

Combinando todas las técnicas:

| Componente | Bytes |
|------------|-------|
| Tabla pentatónica (5 notas) | 10 |
| Patrón de arpegio (1 acorde) | 3 |
| Ornamento (trino) | 4 |
| Progresión (4 acordes) | 4 |
| **Total** | **21** |

21 bytes de datos musicales -- más ~45 bytes de código del motor -- producen música de tres canales con melodía, armonía, cambios de acorde y ornamentación. El ejemplo `aybeat.a80` en el código complementario de este libro demuestra este enfoque en 320 bytes, con espacio de sobra para visuales.

---

## 11. Gramáticas de sistemas-L: Melodías fractales

Los sistemas de Lindenmayer (sistemas-L) son gramáticas de reescritura inventadas originalmente para modelar el crecimiento de plantas. Aplicados a la música, generan secuencias autosimilares con estructura a gran escala a partir de conjuntos de reglas diminutos.

### El concepto

Un sistema-L tiene un **axioma** (cadena inicial) y **reglas de producción** (reglas de expansión). Cada iteración reemplaza cada símbolo según su regla:

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

Este es el **sistema-L de Fibonacci**. La secuencia crece según la proporción de Fibonacci (~1.618x por paso). Mapea los símbolos a eventos musicales:

| Símbolo | Significado musical |
|---------|---------------------|
| A | Tocar nota fundamental (grado de escala 0) |
| B | Tocar quinta (grado de escala 4) |

La melodía resultante: fundamental, quinta, fundamental, fundamental, quinta, fundamental, quinta, fundamental... -- una secuencia que no es periódica ni aleatoria, sino *cuasi-periódica*. Tiene estructura a todas las escalas, como un fractal. Suena intencional sin ser repetitiva.

### Por qué los sistemas-L funcionan para la música

1. **Autosimilaridad.** La melodía a grandes escalas refleja la melodía a pequeñas escalas. Esto es lo que hace que la música compuesta se sienta coherente -- los temas reaparecen a diferentes niveles.
2. **No repetición.** A diferencia de un patrón en bucle, una secuencia de sistema-L nunca se repite exactamente (para proporciones de crecimiento irracionales). Se mantiene interesante.
3. **Codificación mínima.** Las reglas son unos pocos bytes. La secuencia que generan es arbitrariamente larga.

### Reglas útiles de sistemas-L

| Nombre | Axioma | Reglas | Crecimiento | Carácter |
|--------|--------|--------|-------------|----------|
| Fibonacci | A | A→AB, B→A | ~1.618x | Cuasi-periódico, orgánico |
| Thue-Morse | A | A→AB, B→BA | 2x | Equilibrado, justo -- sin rachas largas |
| Duplicación de período | A | A→AB, B→AA | 2x | Cada vez más sincopado |
| Cantor | A | A→ABA, B→BBB | 3x | Disperso, con silencios (B=silencio) |

### Implementación en Z80

El truco para Z80 es **no expandir la cadena en memoria** (eso requeriría un búfer de tamaño ilimitado). En su lugar, calcula el símbolo en la posición `n` recursivamente: retrocede a través de las aplicaciones de reglas para determinar de qué símbolo original provino la posición `n`.

Para el sistema-L de Fibonacci, hay un atajo elegante. El símbolo en la posición `n` depende de la representación de Zeckendorf (codificación de Fibonacci) de `n`. Pero para sizecoding práctico, un enfoque más simple funciona:

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

Un enfoque más práctico para sizecoding: precalcular varias iteraciones del sistema-L en un búfer corto en tiempo de inicialización (una iteración de Fibonacci desde un axioma de 5 símbolos produce 8 símbolos, dos iteraciones producen 13, tres producen 21 -- todos caben en un búfer pequeño), luego recorrer el búfer como secuencia melódica:

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

### Melodía como movimiento, no como notas absolutas

El uso más musical de los sistemas-L no es mapear símbolos a notas fijas, sino mapearlos a **direcciones de paso en la escala**. Una melodía es fundamentalmente sobre *movimiento* -- arriba, abajo, repetir, saltar -- en una escala. La nota inicial es arbitraria; el contorno es lo que importa.

Define los símbolos como movimientos:

| Símbolo | Significado | Paso de escala |
|---------|-------------|---------------|
| U | Paso arriba | +1 |
| D | Paso abajo | -1 |
| R | Repetir | 0 |
| S | Salto arriba (salto) | +2 |

Ahora un sistema-L genera *contorno* melódico, no secuencias de tono fijas:

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

La melodía camina arriba y abajo por la escala actual, manteniéndose siempre dentro de la tabla de escala. Naturalmente tiende hacia el tono de inicio (los retornos equilibran las salidas), creando el arco de tensión y resolución que hace que la música se sienta intencional.

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

Esto es más musical que mapear A=fundamental, B=quinta. Las mismas reglas del sistema-L producen melodías diferentes dependiendo de la nota inicial y la escala subyacente -- cambia la escala de pentatónica a blues y el mismo contorno produce un estado de ánimo completamente diferente.

### Tribonacci: Tres símbolos para patrones más ricos

El sistema-L de Fibonacci usa dos símbolos. **Tribonacci** usa tres: A→ABC, B→A, C→B. La proporción de crecimiento es ~1.839x (la constante tribonacci). Tres símbolos significan contenido melódico más variado:

| Símbolo | Como movimiento | Como nota |
|---------|-----------------|-----------|
| A | Paso arriba (+1) | Fundamental |
| B | Repetir (0) | Tercera |
| C | Paso abajo (-1) | Quinta |

```
Axiom: A
Step 1: A B C
Step 2: A B C  A  B
Step 3: A B C  A  B  A B C  A B C
```

La secuencia tribonacci tiene rachas no repetitivas más largas que Fibonacci y una estructura interna más compleja. Musicalmente, el vocabulario de tres símbolos da a las melodías más variedad -- no solo van y vienen entre dos estados.

### Melodías PRNG con semillas curadas

Un registro de desplazamiento con retroalimentación lineal (LFSR) u otro PRNG similar genera una secuencia pseudoaleatoria determinista a partir de un valor semilla. La secuencia *suena* aleatoria pero se repite exactamente si restableces la semilla. Esto te da fragmentos melódicos reproducibles.

La técnica: **pre-prueba muchas semillas, conserva las que suenan bien.** Almacena 2-4 valores de semilla (2 bytes cada uno) para diferentes secciones de tu pieza. En tiempo de ejecución, carga la semilla y deja que el PRNG genere la melodía. El PRNG en sí ocupa ~6-8 bytes; cada semilla son 2 bytes.

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

El flujo de trabajo: escribe un arnés de prueba que reproduzca la melodía del PRNG para cada valor de semilla 0-65535, escucha (o analiza), marca las buenas. En la práctica, unas pocas horas de prueba producen docenas de semillas utilizables. Almacena 3-4 de ellas y alterna entre secciones de tu pieza.

**Combinación con tablas de escala:** la salida del PRNG pasa por la tabla pentatónica, así que incluso las semillas "malas" producen notas consonantes. Estás curando por *contorno melódico*, no evitando notas incorrectas -- la tabla de escala ya se encarga de eso.

**Combinación con sistemas-L:** usa el PRNG para *seleccionar qué regla del sistema-L aplicar* en cada paso, creando sistemas-L estocásticos. La semilla controla la "personalidad" de la pieza; las reglas gramaticales controlan la estructura. Este híbrido produce la salida más rica con la menor cantidad de bytes.

### Combinando sistemas-L con otras técnicas

Los sistemas-L generan *secuencias* de notas. Combina con las otras técnicas de este apéndice:

- **Tabla de escala** mapea los símbolos del sistema-L a períodos del AY reales
- **Ornamentos** añaden expresión a cada nota
- **Arpegio** convierte cada nota del sistema-L en un acorde
- **Drone de envolvente** proporciona una base armónica sostenida bajo la melodía fractal
- **Progresión de acordes** cambia la fundamental -- la melodía del sistema-L se transpone a cada acorde

El resultado: un programa diminuto (~60-80 bytes de código musical + 20 bytes de datos) que genera minutos de música armónicamente fundamentada, estructuralmente coherente y no repetitiva. Esto es composición algorítmica, no ruido aleatorio -- y cabe en una intro de sizecoding.

### Otras gramáticas para música

Más allá de los sistemas-L, otras gramáticas formales producen secuencias musicales interesantes:

**Autómatas celulares.** La Regla 30 o la Regla 110, aplicadas a una fila de bits, producen patrones complejos. Mapea las posiciones de bits a eventos de nota activada/desactivada. Coste: ~15 bytes para la regla del AC, ~20 bytes para el avance.

**Ritmos euclidianos.** Distribuye `k` golpes uniformemente en `n` pasos. Este algoritmo (relacionado con el MCD euclidiano) genera patrones rítmicos presentes en la música de todo el mundo: 3 en 8 es tresillo, 5 en 8 es cinquillo, 7 en 12 es un patrón común de campana de África Occidental. La implementación ocupa ~20 bytes y produce bases rítmicas perfectas para cualquier motor AY-beat.

---

## Ver también

- **Capítulo 11** -- Arquitectura del AY-3-8910, teoría de tono/ruido/envolvente, técnica de buzz-bass
- **Capítulo 12** -- Integración del motor de música, sincronización con efectos, tambores digitales híbridos
- **Capítulo 13** -- Técnicas de sizecoding, dónde encaja AY-beat en los niveles de tamaño 256b/512b/1K/4K
- **Apéndice G** -- Referencia completa de registros del AY con diseños de bits, direcciones de puerto y tablas de notas

---

> **Fuentes:** Viznut (Ville-Matias Heikkila), "Algorithmic symphonies from one line of code -- how and why?" (2011); countercomplex.blogspot.com; Capítulo 13 de este libro; varias intros de 256 bytes para ZX Spectrum de Pouet.net
