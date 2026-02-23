# Apéndice B: Generación de tablas de seno y tablas trigonométricas

> *"El coseno es simplemente seno desplazado un cuarto de período."*
> -- Los mandamientos de Raider

---

Todo efecto de demo que curve -- rotación, plasma, desplazamiento, túneles -- necesita una tabla de seno. En el Z80, pre-calculas los valores en una tabla de consulta e indexas por ángulo. La cuestión es cómo almacenar y acceder a esa tabla de la forma más eficiente posible.

Este apéndice compara ocho enfoques para el almacenamiento de tablas de seno, desde lo obvio (tabla de 256 bytes) hasta lo exótico (codificación delta de segundo orden de 2 bits). Los datos provienen de `verify/sine_compare.py`, que puedes ejecutar para reproducir cada número aquí.

## El formato estándar

Una tabla de seno de la demoscene tiene **256 entradas**, indexadas por ángulo:

| Índice | Ángulo |
|--------|--------|
| 0 | 0° |
| 64 | 90° |
| 128 | 180° |
| 192 | 270° |
| 256 (vuelve a 0) | 360° |

Cada entrada es un **byte con signo** (-128 a +127), que representa de -1.0 a aproximadamente +1.0. El período potencia de dos significa que el índice de ángulo se envuelve naturalmente con el desbordamiento de 8 bits, y el coseno se convierte en seno sumando 64:

```z80
; sin(angle) -- direct table lookup
    ld   h, high(sin_table)  ; 7T   table must be 256-byte aligned
    ld   l, a                ; 4T   A = angle (0-255)
    ld   a, (hl)             ; 7T   A = sin(angle)
                             ; --- 18 T-states total

; cos(angle) -- offset by quarter period
    add  a, 64               ; 7T   cos = sin + 90°
    ld   l, a                ; 4T
    ld   a, (hl)             ; 7T
```

Esta es la regla clave de Raider: almacenar H una vez con el byte alto de la tabla, luego L es el ángulo y se envuelve libremente.

---

## Comparación de enfoques

| # | Enfoque | Datos | Código | Total | RAM | Error máx. | RMS |
|---|---------|-------|--------|-------|-----|------------|-----|
| 1 | Tabla completa (256 bytes) | 256 | 0 | **256** | 0 | 0 | 0.00 |
| 2 | Tabla de cuarto de onda | 65 | 21 | **86** | 0 | 0 | 0.00 |
| 3 | Aproximación parabólica | 0 | 38 | **38** | 0 | 8 | 4.51 |
| 4 | Cuarto de onda + deltas de 2.° orden | 18 | 45 | **63** | 64 | 0 | 0.00 |
| 5 | Aproximación de Bhaskara I | 0 | ~60 | **~60** | 0 | 1 | 0.49 |
| 5b | Bhaskara I + bitmap de corrección | 1 | ~80 | **~81** | 0 | 0 | 0.00 |
| 6 | Cuarto de onda + deltas empaquetados de 4 bits | 33 | 43 | **76** | 64 | 0 | 0.00 |
| 7 | Deltas de 2.° orden completos, empaquetados a 2 bits | 66 | 30 | **96** | 256 | 0 | 0.00 |

Los enfoques caen en tres categorías:

- **Basados en consulta** (sin necesidad de RAM): tabla completa, tabla de cuarto de onda
- **Basados en generación** (necesitan búfer de RAM al inicio): enfoques delta y delta de segundo orden
- **Aproximados** (sin tabla en absoluto): parabólico, Bhaskara I
- **Aproximado + corrección exacta**: Bhaskara I con bitmap de corrección

---

## Enfoque 1: Tabla completa de 256 bytes

El más simple y rápido. Pre-calcula los 256 valores e inclúyelos como datos.

```z80
; Lookup: 18 T-states, zero error
    ld   h, high(sin_table)
    ld   l, a
    ld   a, (hl)
```

**Coste:** 256 bytes de ROM.
**Velocidad:** 18 T-states por consulta.
**Cuándo usarlo:** Siempre, a menos que estés haciendo sizecoding. En un Spectrum de 48K con ~40K libres, 256 bytes no son nada. Esta es la opción por defecto.

---

## Enfoque 2: Tabla de cuarto de onda

Una onda sinusoidal tiene simetría cuádruple. El primer cuadrante (0° a 90°, índices 0 a 64) contiene toda la información:

- **Segundo cuadrante** (65-128): espejo del primer cuadrante. `sin(128 - i) = sin(i)`.
- **Tercer cuadrante** (129-192): negativo del primer cuadrante. `sin(128 + i) = -sin(i)`.
- **Cuarto cuadrante** (193-255): espejo negativo. `sin(256 - i) = -sin(i)`.

Almacena solo 65 bytes (índices 0 a 64 inclusive), luego reconstruye:

```z80
; Quarter-wave sine lookup
; Input:  A = angle (0-255)
; Output: A = sin(angle), signed byte
; Uses:   HL, BC
; Table:  sin_quarter (65 bytes, 256-byte aligned)
;
qsin:
    ld   c, a               ; 4T   save original angle
    and  $7F                 ; 7T   fold to 0-127 (first half)
    cp   65                  ; 7T   past the peak?
    jr   c, .no_mirror       ; 12/7T
    ; Mirror: index = 128 - index
    neg                      ; 8T
    add  a, 128              ; 7T
.no_mirror:
    ld   h, high(sin_quarter) ; 7T
    ld   l, a                ; 4T
    ld   a, (hl)             ; 7T   A = |sin(angle)|
    bit  7, c                ; 8T   was original angle >= 128?
    ret  z                   ; 11/5T  no: positive half, done
    neg                      ; 8T   yes: negate for third/fourth quadrant
    ret                      ; 10T
```

**Coste:** 65 bytes de datos + ~21 bytes de código = **86 bytes en total**.
**Velocidad:** ~50-70 T-states por consulta (varía según el cuadrante).
**Error:** Cero.
**Cuándo usarlo:** Demos con limitación de tamaño (intros de 256, 512 bytes) donde necesitas valores exactos pero no puedes permitirte 256 bytes.

---

## Enfoque 3: Aproximación parabólica (método de Dark)

De Dark / X-Trade, *Spectrum Expert* #01 (1997). La idea: medio período del coseno se parece a una parábola. La aproximación `y ~ 1 - 2(x/pi)^2` se ajusta bastante. En términos enteros, cada medio período se genera como una función cuadrática por tramos.

**Código puro, cero datos.** El bucle de generación necesita una multiplicación de 8x8 y algo de lógica de acumulador -- aproximadamente 38 bytes.

El error está acotado: **error absoluto máximo = 8** (de un rango de 256 pasos), o aproximadamente **6.3%** de escala completa. El error RMS es 4.51.

Aquí es donde la parábola diverge del seno verdadero (primer cuadrante):

```
Index  True  Para  Diff
    0     0     0    +0
    4    12    15    -3
    8    25    30    -5
   12    37    43    -6
   16    49    56    -7
   20    60    67    -7
   24    71    77    -6
   28    81    87    -6
   32    88    93    -5
```

La parábola está consistentemente "adelantada" -- sube más rápido cerca de cero y es más plana cerca del pico. Divergencia máxima: **8 unidades en el índice 17** (aproximadamente 24°).

**Cuándo usarlo:** Sizecoding extremo (intros de 64 bytes, cargadores compactos). Plasmas, scrollers simples y efectos de ondulación donde el ojo no distingue la curvatura exacta de la aproximada. No adecuado para rotación suave o 3D wireframe preciso.

---

## Enfoque 4: Codificación delta de segundo orden (el truco profundo)

Este es el enfoque más interesante matemáticamente, y con diferencia la representación exacta más compacta.

### La idea clave

La segunda derivada de sin(x) es -sin(x). Con precisión de entero de 8 bits, cuantizando a bytes con signo, la segunda diferencia finita de la tabla de seno tiene una propiedad notable: **cada valor es exactamente -1, 0 o +1**.

```
True sine:      [0,  3,  6,  9, 12, 16, 19, 22, 25, ...]
First diff:     [3,  3,  3,  3,  4,  3,  3,  3,  3, ...]
Second diff:    [0,  0,  0,  1, -1,  0,  0,  0,  0, ...]
```

Tres valores. Dos bits por entrada. Esto no es una aproximación -- es exacto. La razón matemática: `d^2(sin)/dx^2` es una función suave con magnitud pequeña, y con 256 entradas por período con amplitud de 8 bits, la segunda derivada discreta nunca excede +/-1.

### Tabla completa vía deltas de segundo orden de 2 bits

Almacenar: valor inicial (1 byte), delta inicial (1 byte), luego 254 deltas de segundo orden empaquetados a 2 bits cada uno (64 bytes). **Total: 66 bytes de datos + ~30 bytes de código de decodificación = 96 bytes.** Necesita 256 bytes de RAM para decodificar.

### Cuarto de onda vía deltas de segundo orden de 2 bits

Combinar con simetría de cuarto de onda: almacenar solo los primeros 64 deltas de segundo orden. **Total: 18 bytes de datos + ~45 bytes de código de decodificación = 63 bytes.** Necesita 64 bytes de RAM.

Esta es la **representación exacta más pequeña**: 63 bytes en total para una tabla de seno de 256 entradas perfecta.

```z80
; Decode quarter-wave from 2-bit second-order deltas
; sin_d2_data: 16 bytes of packed 2-bit deltas (64 entries)
; sin_buffer:  64 bytes RAM for decoded quarter-wave
;
decode_quarter_d2:
    ld   hl, sin_buffer      ; destination
    ld   de, sin_d2_data     ; source (packed d2 values)
    xor  a
    ld   (hl), a             ; sin[0] = 0
    inc  hl
    ld   b, a                ; b = current delta (starts at 0)
    ld   c, 63               ; 63 more entries to decode

.loop:
    ; Unpack 2-bit d2 value
    ; 00 = 0, 01 = +1, 11 = -1 (10 unused)
    rr   (de)                ; shift out 2 bits
    rr   (de)
    ; ... (bit extraction logic)

    ; Apply: delta += d2, value += delta
    add  a, b               ; new delta
    ld   b, a
    ld   a, (hl-1)          ; previous value (pseudocode)
    add  a, b
    ld   (hl), a
    inc  hl
    dec  c
    jr   nz, .loop

    ; Now use qsin() lookup on sin_buffer
```

La decodificación se ejecuta una vez al inicio. Después de eso, usa la rutina de consulta de cuarto de onda del Enfoque 2 sobre el búfer decodificado.

**Cuándo usarlo:** Demos con código limitado por tamaño (intros de 128, 256 bytes) donde necesitas valores exactos, puedes permitirte 64 bytes de RAM, y tienes una breve fase de inicio. El bucle de decodificación se ejecuta en menos de 2,000 T-states -- invisible.

> **Nota al margen: Por qué no 1 bit por delta?**
>
> Una objeción intuitiva: el seno de cuarto de onda (0° a 90°) es monótonamente creciente. Las primeras diferencias d1 son siempre no negativas. En matemáticas continuas, la segunda derivada del seno en el primer cuadrante es siempre negativa (la curva es cóncava). Así que d2 debería ser <= 0, lo que significa que solo necesitamos {-1, 0} -- un solo bit por entrada.
>
> La intuición es correcta para el seno continuo, pero incorrecta para el seno entero cuantizado. Con precisión de 8 bits, el redondeo crea saltos ascendentes ocasionales en d1:
>
> ```
> d1:  3, 3, 3, 3, 4, 3, 3, ...  (that 4 is a rounding correction)
> d2:  0, 0, 0, +1, -1, 0, ...   (the +1 is load-bearing)
> ```
>
> Hay 12 de esas entradas +1 de 63. Si las suprimes (limitando d1 a ser monótonamente no creciente), los errores se *acumulan*: para el índice 64 el pico alcanza solo 108 en lugar de 127 -- un error máximo de 19, peor que la aproximación parabólica. Esas correcciones +1 llevan precisamente la información necesaria para alcanzar los valores enteros correctos. No puedes eliminarlas.
>
> Un código de prefijo de longitud variable (0 -> 1 bit, +/-1 -> 2 bits) ahorra 4 bytes de datos sobre la codificación fija de 2 bits pero cuesta ~15 bytes extra de lógica de decodificación Z80. Pérdida neta. La codificación fija de 2 bits es el óptimo práctico.

> **Nota al margen: Por qué parábola + corrección no ayuda**
>
> Otra idea intuitiva: generar una aproximación parabólica (38 bytes de código, error máximo 8), luego almacenar una pequeña tabla de corrección para ajustarla a valores exactos. Las correcciones van de -8 a +8, así que deberían comprimirse bien.
>
> Las correcciones *sí* se comprimen bien -- sus primeras diferencias son exactamente {-1, 0, +1}, empaquetándose en 2 bits por entrada. Pero esto no es coincidencia. Una parábola es una cuadrática con segunda derivada constante. Así que:
>
> - `d2(sin)` pertenece a {-1, 0, +1} -- la segunda derivada del seno a precisión entera
> - `d2(para)` pertenece a {-1, 0, +1} -- la segunda derivada de la parábola (casi constante)
> - `d1(correction)` = `d1(sin) - d1(para)` pertenece a {-1, 0, +1} -- **la misma entropía**
>
> Los deltas de corrección tienen *exactamente la misma estructura* que el d2 directo del seno. Pero la ruta parabólica añade 38 bytes de código de generación, más ~20 bytes para aplicar correcciones. Total: ~96 bytes vs 63 bytes para codificación d2 directa.
>
> La parábola elimina el componente suave (baja frecuencia) del seno -- pero la codificación d2 de 2 bits ya maneja los datos suaves perfectamente. No queda nada que la parábola pueda contribuir que d2 no capture ya. El código de generación es puro overhead.

---

## Enfoque 5: Aproximación de Bhaskara I (siglo VII)

La entrada más sorprendente en nuestra comparación viene del matemático indio del siglo VII Bhaskara I. Su aproximación racional al seno, publicada alrededor del 629 d.C., logra **un error máximo de solo 1 unidad** a precisión de 8 bits -- dramáticamente mejor que la aproximación parabólica (error máximo 8) y casi exacta.

### La fórmula

Para ángulo x en radianes (0 a pi):

```
sin(x) ~ 16x(pi - x) / (5pi^2 - 4x(pi - x))
```

En nuestro dominio entero (ángulo 0-64 para el primer cuadrante, amplitud 0-127):

```
sin(i) ~ 127 x 16i(64 - i) / (5 x 64^2 - 4 x i(64 - i))
       = 127 x 16i(64 - i) / (20480 - 4i(64 - i))
```

La fórmula es un cociente de dos cuadráticas. En el Z80 esto necesita una multiplicación de 8x8 y una división de 16 bits -- rutinas que muchas demos ya incluyen para proyección 3D o mapeado de texturas.

### Precisión

A lo largo de las 65 entradas del primer cuadrante, Bhaskara I coincide con el seno entero exacto en todas partes excepto **8 posiciones** (de 65), donde difiere exactamente en +/-1:

```
Index  True  Bhaskara  Diff
    4    12        13    -1
   17    51        52    -1
   28    81        80    +1
   31    88        87    +1
   40   106       105    +1
   43   111       110    +1
   50   120       119    +1
   52   122       121    +1
```

Solo 8 posiciones difieren, todas exactamente en +/-1. Los errores están divididos: 2 entradas donde Bhaskara sobrepasa (cerca del inicio), 6 donde se queda corto (cerca del pico). Ocho correcciones en total, que se codifican como un bitmap de un solo byte.

### Implementación en Z80

La implementación requiere:
- Una rutina de multiplicación 8x8->16 (~20 bytes, probablemente ya disponible)
- Una rutina de división 16/16->16 (~30 bytes, probablemente ya disponible)
- El wrapper de Bhaskara en sí (~25 bytes)
- Lógica de plegado de cuarto de onda (~15 bytes, compartida con el Enfoque 2)

Si tu demo ya tiene rutinas de multiplicación y división, el coste marginal es aproximadamente **25 bytes** para una función seno con error máximo 1.

Si necesitas las rutinas desde cero, el total es aproximadamente **60 bytes** de código con cero bytes de datos. Esto es competitivo con el enfoque de deltas d2 (63 bytes) pero no requiere búfer de RAM ni fase de decodificación al inicio. La compensación: 1 unidad de error vs precisión perfecta.

### Bhaskara I + bitmap de corrección (exacto)

Para eliminar esa última unidad de error, almacena las 8 posiciones de corrección como un bitmap. Como las correcciones son simétricas (las 4 primeras necesitan +1, las 4 últimas necesitan -1), un byte basta:

```z80
; After computing Bhaskara approximation in A, index in C:
    push af
    ld   a, c
    ; Look up correction from bitmap (8 specific indices)
    ; ... (~20 bytes of correction logic)
    pop  af
    add  a, correction      ; ±1 or 0
```

Total: ~80 bytes de código + 1 byte de datos = **~81 bytes**, cero RAM, cero tiempo de inicio, valores exactos. Más caro que deltas d2 (63B) pero evita el búfer de RAM y la decodificación al inicio.

### Cuándo usar Bhaskara I

- **Ya tienes rutinas de multiplicación/división:** ~25 bytes extra, error máximo 1. Difícil de superar.
- **Sin RAM disponible para búfer de decodificación:** A diferencia de los deltas d2, Bhaskara calcula al vuelo.
- **Generación en tiempo real necesaria:** Cada valor se calcula independientemente -- sin dependencia secuencial, así que puedes calcular sin(cualquier ángulo) sin decodificar una tabla primero.
- **Error de +/-1 aceptable:** Para scrollers, plasmas y la mayoría de efectos visuales, la diferencia entre error máximo 1 y error máximo 0 es literalmente invisible.

> **Nota histórica:** La fórmula de Bhaskara I precede a las tablas trigonométricas europeas por casi un milenio. Que una aproximación racional del siglo VII logre un error máximo de 1 en un procesador de 8 bits de los años 80 es una hermosa colisión de elegancia matemática y restricciones de ingeniería. La fórmula fue publicada en *Mahabhaskariya* (629 d.C.), un comentario sobre los métodos astronómicos de Aryabhata.

---

## Recomendaciones prácticas

Cada enfoque basado en generación produce una tabla de consulta al inicio. Después de eso, el coste en tiempo de ejecución es idéntico: `LD H, high(table) / LD L, A / LD A, (HL)` = **18 T-states** para una tabla de 256 bytes, o la rutina de plegado de cuarto de onda a **50-70 T-states** para un búfer de 64 bytes. La columna "coste ROM" a continuación es lo que importa para el sizecoding -- son los bytes totales que tu enfoque ocupa en el binario.

| Caso de uso | Enfoque | Coste ROM | RAM | Inicio | Consulta | Error |
|-------------|---------|-----------|-----|--------|----------|-------|
| **Demo / juego normal** | Tabla completa de 256 bytes | 256B | 0 | ninguno | 18 T | exacto |
| **Intro de 512 bytes** | Tabla de cuarto de onda | 86B | 0 | ninguno | 50-70 T | exacto |
| **Intro de 256 bytes** | Cuarto de onda + deltas d2 | 63B | 64B | ~2K T | 50-70 T | exacto |
| **Tiene multiplicación/división** | Bhaskara I (generar a LUT) | ~25B extra | 256B | ~80K T | 18 T | +/-1 máx. |
| **Intro de 128 bytes** | Parabólica (generar a LUT) | 38B | 256B | ~10K T | 18 T | +/-8 máx. |

### El árbol de decisión

1. **Tienes 256 bytes de sobra?** Usa la tabla completa. No le des demasiadas vueltas. `LD L,A / LD A,(HL)` a 18 T-states no se puede superar.

2. **Limitación de tamaño pero necesitas precisión?** Tabla de cuarto de onda a 86 bytes. Sin necesidad de RAM, sin fase de inicio. La consulta es de 50-70 T-states (la lógica de plegado).

3. **Límite de tamaño extremo, se necesitan valores exactos?** Cuarto de onda + decodificación delta de segundo orden a 63 bytes. Decodifica una vez al inicio en un búfer de cuarto de 64 bytes, luego usa la misma consulta con plegado.

4. **Ya tienes multiplicación/división?** Bhaskara I a ~25 bytes extra. Genera una LUT completa de 256 bytes al inicio, luego disfruta de consultas de 18 T-states con error máximo 1.

5. **Límite de tamaño extremo, aproximación aceptable?** Parabólica a 38 bytes, cero datos. Genera a una LUT de 256 bytes al inicio. Error máximo 8, bueno para plasmas y ondulaciones.

### Lo que no funciona

- **Parabólica + tabla de corrección** (123 bytes exactos): peor que simplemente usar una tabla de cuarto de onda (86 bytes). El overhead de calcular la parábola *y* buscar una corrección anula el propósito.

- **Delta + RLE** (100-219 bytes): los deltas del seno varían suavemente en lugar de repetirse en series. RLE está diseñado para datos con largas series constantes -- el seno tiene la forma incorrecta para ello.

- **Tabla codificada con deltas completa** (152-271 bytes): usa *más* bytes totales que la tabla cruda de 256 bytes. La codificación delta solo ayuda cuando los deltas son significativamente más pequeños que los valores originales; los deltas del seno ya están acotados a +/-4, pero aún necesitas 256 de ellos.

---

## Los mandamientos de Raider

En los comentarios de Hype sobre el análisis de Introspec de *Illusion*, el veterano programador Raider destiló décadas de sabiduría colectiva en "mandamientos" informales para el diseño de tablas de seno:

1. **256 entradas por período completo.** El índice de ángulo se envuelve con el desbordamiento de 8 bits. No se necesita aritmética modular.
2. **Bytes con signo: -128 a +127.** Coincide con la aritmética con signo del Z80.
3. **Alinear la tabla a página.** Colocarla en un límite de 256 bytes para que H sea constante. `LD H,high(table)` una vez, luego `LD L,angle / LD A,(HL)` para siempre.
4. **Coseno es seno + 64.** Una instrucción `ADD A,64`.
5. **Seno de (ángulo + 128) = -seno(ángulo).** `NEG` invierte el signo. Usa esto para desplazamientos de fase.
6. **No calcules seno en tiempo de ejecución** a menos que estés haciendo sizecoding. Una consulta de tabla siempre es más rápida.
7. **Mantén la amplitud como potencia de dos** (64, 127, 128) para que la multiplicación sea un desplazamiento.
8. **La simetría de cuarto de onda** ahorra un 75% de almacenamiento cuando cada byte importa.
9. **Prueba en los límites.** El índice 0 debe ser exactamente 0. El índice 64 debe ser el valor positivo máximo (+127). El índice 128 debe ser exactamente 0. El índice 192 debe ser el valor negativo máximo (-128 o -127, dependiendo de tu convención).

Estas reglas reflejan décadas de experiencia. Síguelas y tus tablas de seno serán rápidas, pequeñas y correctas.

---

## Referencia: La tabla completa de 256 bytes

Para mayor comodidad, aquí está la tabla de seno estándar (256 entradas, con signo, período = 256, amplitud +/-127):

```z80
; 256-byte sine table, page-aligned
; sin(0) = 0, sin(64) = +127, sin(128) = 0, sin(192) = -128
;
    ALIGN 256
sin_table:
    DB    0,   3,   6,   9,  12,  16,  19,  22
    DB   25,  28,  31,  34,  37,  40,  43,  46
    DB   49,  51,  54,  57,  60,  63,  65,  68
    DB   71,  73,  76,  78,  81,  83,  85,  88
    DB   90,  92,  94,  96,  98, 100, 102, 104
    DB  106, 108, 109, 111, 112, 114, 115, 117
    DB  118, 119, 120, 121, 122, 123, 124, 124
    DB  125, 126, 126, 127, 127, 127, 127, 127
    DB  127, 127, 127, 127, 127, 127, 126, 126
    DB  125, 124, 124, 123, 122, 121, 120, 119
    DB  118, 117, 115, 114, 112, 111, 109, 108
    DB  106, 104, 102, 100,  98,  96,  94,  92
    DB   90,  88,  85,  83,  81,  78,  76,  73
    DB   71,  68,  65,  63,  60,  57,  54,  51
    DB   49,  46,  43,  40,  37,  34,  31,  28
    DB   25,  22,  19,  16,  12,   9,   6,   3
    DB    0,  -3,  -6,  -9, -12, -16, -19, -22
    DB  -25, -28, -31, -34, -37, -40, -43, -46
    DB  -49, -51, -54, -57, -60, -63, -65, -68
    DB  -71, -73, -76, -78, -81, -83, -85, -88
    DB  -90, -92, -94, -96, -98,-100,-102,-104
    DB -106,-108,-109,-111,-112,-114,-115,-117
    DB -118,-119,-120,-121,-122,-123,-124,-124
    DB -125,-126,-126,-127,-127,-127,-127,-127
    DB -128,-127,-127,-127,-127,-127,-126,-126
    DB -125,-124,-124,-123,-122,-121,-120,-119
    DB -118,-117,-115,-114,-112,-111,-109,-108
    DB -106,-104,-102,-100, -98, -96, -94, -92
    DB  -90, -88, -85, -83, -81, -78, -76, -73
    DB  -71, -68, -65, -63, -60, -57, -54, -51
    DB  -49, -46, -43, -40, -37, -34, -31, -28
    DB  -25, -22, -19, -16, -12,  -9,  -6,  -3
```

Copia, pega, ensambla, usa.

---

> **Fuentes:** Dark / X-Trade "Programming Algorithms" (Spectrum Expert #01, 1997) para la aproximación parabólica; Bhaskara I, *Mahabhaskariya* (629 d.C.) para la aproximación racional; Raider (comentarios en Hype, 2017) para principios de diseño de tablas de seno; `verify/sine_compare.py` para análisis comparativo
