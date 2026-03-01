# Capítulo 4: Las matemáticas que realmente necesitas

> *"Lee un libro de texto de matemáticas -- derivadas, integrales. Las vas a necesitar."*
> -- Dark, Spectrum Expert #01 (1997)

En 1997, un adolescente en San Petersburgo se sentó a escribir un artículo de revista sobre multiplicación. No del tipo que aprendes en la escuela -- del tipo que hace girar un cubo de alambre en un ZX Spectrum a 50 fotogramas por segundo. Su nombre era Dark, programaba para el grupo X-Trade, y su demo *Illusion* ya había ganado el primer lugar en ENLiGHT'96. Ahora estaba escribiendo *Spectrum Expert*, una revista electrónica distribuida en disquete, e iba a explicar exactamente cómo funcionaban sus algoritmos.

Lo que sigue está extraído directamente del artículo "Programming Algorithms" de Dark en Spectrum Expert #01. Estas son las rutinas que impulsaron *Illusion* -- la misma multiplicación que rotaba vértices, la misma tabla de seno que impulsaba el rotozoomer, el mismo trazador de líneas que renderizaba wireframes a velocidad de fotograma completa. Cuando Introspec hizo ingeniería inversa de *Illusion* veinte años después en el blog Hype, encontró estos mismos algoritmos funcionando dentro del binario.

---

## Multiplicación en Z80

El Z80 no tiene instrucción de multiplicación. Cada vez que necesitas A por B -- para matrices de rotación, proyección en perspectiva, mapeo de texturas -- debes sintetizarlo a partir de desplazamientos y sumas. Dark presenta dos métodos, y es característicamente honesto sobre la compensación entre ellos.

### Método 1: desplazamiento y suma desde LSB

El enfoque clásico. Recorre los bits del multiplicador de LSB a MSB. Para cada bit activo, suma el multiplicando en un acumulador. Después de cada bit, desplaza el acumulador a la derecha. Después de ocho iteraciones, el acumulador contiene el producto completo.

Aquí está la multiplicación 8x8 sin signo de Dark. Entrada: B por C. Resultado en A (byte alto) y C (byte bajo):

```z80 id:ch04_method_1_shift_and_add_from
; MULU112 -- 8x8 unsigned multiply
; Input:  B = multiplicand, C = multiplier
; Output: A:C = B * C (16-bit result, A=high, C=low)
; Cost:   196-204 T-states (Pentagon)
;
; From Dark / X-Trade, Spectrum Expert #01 (1997)

mulu112:
    ld   a, 0           ; clear accumulator (high byte of result)
    ld   d, 8           ; 8 bits to process

.loop:
    rr   c              ; shift LSB of multiplier into carry
    jr   nc, .noadd     ; if bit was 0, skip addition
    add  a, b           ; add multiplicand to accumulator
.noadd:
    rra                 ; shift accumulator right (carry into bit 7,
                        ;   bit 0 into carry -- this carry feeds
                        ;   back into C via the next RR C)
    dec  d
    jr   nz, .loop
    ret
```

Estudia esto con cuidado. La instrucción `RRA` desplaza A a la derecha, pero también empuja el bit más bajo de A a la bandera de acarreo. En la siguiente iteración, `RR C` rota ese acarreo hacia la parte superior de C. Así que los bits bajos del producto se ensamblan gradualmente en C, mientras que los bits altos se acumulan en A. Después de ocho iteraciones, el resultado completo de 16 bits está en A:C.

El costo es de 196 a 204 T-states dependiendo de cuántos bits del multiplicador estén activos -- cada bit activo cuesta un `ADD A,B` extra (4 T-states). El ejemplo en `chapters/ch04-maths/examples/multiply8.a80` muestra una variante que devuelve el resultado en HL.

<!-- Screenshot removed: result is border colour only, not capturable as static image -->

Para 16x16 produciendo un resultado de 32 bits, el MULU224 de Dark se ejecuta en 730 a 826 T-states. En la práctica, los motores 3D de la demoscene evitan las multiplicaciones completas de 16x16 manteniendo las coordenadas en punto fijo 8.8 y usando multiplicaciones 8x8 donde sea posible.

<!-- figure: ch04_multiply_walkthrough -->
![Recorrido de multiplicación 8x8 por desplazamiento y suma](illustrations/output/ch04_multiply_walkthrough.png)

### Método 2: búsqueda en tabla de cuadrados

El segundo método de Dark intercambia memoria por velocidad, explotando una identidad algebraica que todo demoscener eventualmente descubre:

```text
A * B = ((A+B)^2 - (A-B)^2) / 4
```

Pre-calcula una tabla de valores de n^2/4, y la multiplicación se convierte en dos búsquedas y una resta -- aproximadamente 61 T-states, más de tres veces más rápido que desplazamiento y suma.

Necesitas una tabla de 512 bytes de (n^2/4) para n = 0 a 511, alineada a página para indexación con un solo registro. La tabla debe ser de 512 bytes porque (A+B) puede alcanzar 510.

```z80 id:ch04_method_2_square_table_lookup_2
; MULU_FAST -- Square table multiply
; Input:  B, C = unsigned 8-bit factors
; Output: HL = B * C (16-bit result)
; Cost:   ~61 T-states (Pentagon)
; Requires: sq_table = 512-byte table of n^2/4, page-aligned
;
; A*B = ((A+B)^2 - (A-B)^2) / 4

mulu_fast:
    ld   h, sq_table >> 8  ; high byte of table address
    ld   a, b
    add  a, c              ; A = B + C (may overflow into carry)
    ld   l, a
    ld   e, (hl)           ; look up (B+C)^2/4 low byte
    inc  h
    ld   d, (hl)           ; look up (B+C)^2/4 high byte

    ld   a, b
    sub  c                 ; A = B - C (may go negative)
    jr   nc, .pos
    neg                    ; take absolute value
.pos:
    ld   l, a
    dec  h
    ld   a, e
    sub  (hl)              ; subtract (B-C)^2/4 low byte
    ld   e, a
    inc  h
    ld   a, d
    sbc  a, (hl)           ; subtract (B-C)^2/4 high byte
    ld   d, a

    ex   de, hl            ; HL = result
    ret
```

¿La contrapartida? Dark es característicamente honesto: **"Elige: velocidad o precisión."** La tabla almacena valores enteros de n^2/4, así que hay un error de redondeo de hasta 0,25 por búsqueda. Para valores grandes esto es insignificante. Para los pequeños deltas de coordenadas en rotación 3D, el error produce un jitter visible en los vértices. Con desplazamiento y suma, la rotación es perfectamente suave.

Para mapeo de texturas, plasma, scrollers -- usa la multiplicación rápida. Para wireframe 3D donde el ojo rastrea vértices individuales -- quédate con desplazamiento y suma. Dark lo sabía porque había probado ambos en *Illusion*.

**Generar la tabla de cuadrados** es un costo único al inicio. Dark sugiere usar el método de derivadas: dado que d(x^2)/dx = 2x, puedes construir la tabla incrementalmente sumando un delta linealmente creciente en cada paso. En la práctica, la mayoría de los programadores calculan la tabla en un cargador BASIC o rutina de inicialización y siguen adelante.

---

## Multiplicación con signo

Un capítulo que enseña multiplicación sin signo y luego la usa para rotar coordenadas 3D tiene un vacío: las matrices de rotación operan con valores con signo. X puede ser -40 o +40, los valores de seno van de -128 a +127. Cada `call mul_signed` en el Capítulo 5 depende de la rutina que estás a punto de ver. Como dijo Ped7g durante su revisión: "un capítulo que enseña rotación 3D sin mostrar la multiplicación con signo es como un libro de cocina que lista los ingredientes pero se olvida del horno."

### Complemento a dos en la práctica

El Z80 representa los enteros con signo en complemento a dos. Las reglas son simples:

- El bit 7 es el bit de signo: 0 = positivo, 1 = negativo
- Los valores positivos son iguales que sin signo: $00 = 0, $01 = 1, ..., $7F = 127
- Los valores negativos cuentan hacia abajo desde $FF: $FF = -1, $FE = -2, ..., $80 = -128
- `NEG` calcula el valor absoluto de un número negativo (niega A: A = 0 - A). Costo: 8T

La idea crítica para la aritmética: **ADD y SUB no se preocupan por el signo.** Sumar $FF (-1) a $03 (+3) da $02 (+2) --- correcto tanto en interpretación con signo como sin signo. La suma del hardware es idéntica. Solo la multiplicación requiere manejo explícito del signo, porque el bucle de desplazamiento y suma trata los bits del multiplicador como valores posicionales sin signo.

### Extensión de signo: la expresión idiomática `rla / sbc a,a`

Cuando multiplicas un valor de 8 bits con signo por otro valor de 8 bits con signo, necesitas conocer los signos. La forma más barata de extraer el bit de signo en el Z80:

```z80
; Sign extension: A → D (0 if positive, $FF if negative)
; Cost: 8T, 2 bytes. Branchless.
    rla                 ; 4T  rotate sign bit into carry
    sbc  a, a           ; 4T  A = 0 if carry clear, $FF if set
```

Después de `sbc a,a`, A es $00 para entradas positivas o $FF para entradas negativas. Este es el byte estándar de extensión de signo usado en toda la demoscene del Z80.

### `mul_signed` --- multiplicación con signo 8x8

El algoritmo: XOR las dos entradas para determinar el signo del resultado, toma los valores absolutos, multiplica sin signo, niega el resultado si el signo era negativo. Esta es la rutina que el Capítulo 5 llama seis veces por rotación de vértice y dos veces por eliminación de caras traseras.

```z80 id:ch04_mul_signed
; mul_signed — 8x8 signed multiply
; Input:  B = signed multiplicand, C = signed multiplier
; Output: HL = signed 16-bit result
; Cost:   ~240-260 T-states (Pentagon)
;
; Algorithm: determine sign, abs both, unsigned multiply, negate if needed.

mul_signed:
    ld   a, b
    xor  c               ; 4T  bit 7 = result sign (1 = negative)
    push af              ; 11T save sign flag

    ; Absolute value of B
    ld   a, b
    or   a
    jp   p, .b_pos       ; 10T skip if positive
    neg                  ; 8T  A = |B|
.b_pos:
    ld   b, a

    ; Absolute value of C
    ld   a, c
    or   a
    jp   p, .c_pos
    neg
.c_pos:
    ld   c, a

    ; Unsigned 8x8 multiply: B * C -> A:C (high:low)
    ld   a, 0
    ld   d, 8
.mul_loop:
    rr   c
    jr   nc, .noadd
    add  a, b
.noadd:
    rra
    dec  d
    jr   nz, .mul_loop

    ; A:C = unsigned product. Move to HL.
    ld   h, a
    ld   l, c

    ; Negate result if sign was negative
    pop  af              ; 10T recover sign
    or   a
    jp   p, .done        ; 10T skip if positive
    ; Negate HL: HL = 0 - HL
    xor  a
    sub  l
    ld   l, a
    sbc  a, a
    sub  h
    ld   h, a
.done:
    ret
```

El núcleo es el mismo bucle de desplazamiento y suma de `mulu112`, envuelto con detección de signo y negación condicional. La sobrecarga es de ~40-60 T-states más allá de la multiplicación sin signo, dependiendo de cuántos operandos necesitan negación.

### `mul_signed_c` --- envoltura fina para eliminación de caras traseras

La eliminación de caras traseras del Capítulo 5 pasa el primer operando en A en lugar de B. Una envoltura fina evita reestructurar el llamador:

```z80 id:ch04_mul_signed_c
; mul_signed_c — signed multiply with A,C inputs
; Input:  A = signed multiplicand, C = signed multiplier
; Output: HL = signed 16-bit result
; Cost:   ~250-270 T-states (Pentagon)

mul_signed_c:
    ld   b, a            ; 4T
    jr   mul_signed      ; 12T  fall through to mul_signed
```

### Comparación de costos

| Rutina | Entrada | Resultado | T-states | Notas |
|---------|-------|--------|----------|-------|
| `mulu112` (sin signo) | B, C | A:C (16 bits) | 196--204 | Desplazamiento y suma del Capítulo 4 |
| `mulu_fast` (tabla de cuadrados) | B, C | HL (16 bits) | ~61 | Necesita tabla de 512 bytes; error de redondeo |
| `mul_signed` | B, C (con signo) | HL (16 bits con signo) | ~240--260 | Manejo de signo añade ~40--60T |
| `mul_signed_c` | A, C (con signo) | HL (16 bits con signo) | ~250--270 | Envoltura para eliminación de caras traseras |

La multiplicación con signo es aproximadamente un 25% más cara que sin signo. Para un cubo de alambre con 8 vértices y 6 multiplicaciones por rotación de eje (12 en total por rotación 3D completa), el costo por vértice es ~3.120 T-states --- aún cómodamente dentro del presupuesto de fotograma.

Las matrices de rotación del Capítulo 5 llaman a `mul_signed` seis veces por vértice para rotación en Z y perspectiva, y `mul_signed_c` dos veces por cara para eliminación de caras traseras. Ahora sabes exactamente qué hacen esas llamadas.

> **Crédito:** El vacío de aritmética con signo fue identificado por Ped7g (Peter Helcmanovsky) durante su revisión del libro.

### Para profundizar: la técnica de corrección de resultado sin signo

El enfoque de 2×abs anterior es claro y correcto, pero existe un método más elegante. La identidad matemática clave: para un número en complemento a dos de N bits, `a_con_signo = a_sin_signo − 2^N × bit_de_signo`. Así, para multiplicación 8×8:

```
a_s × b_s = a_u × b_u − 256 × signo(a) × b_u − 256 × signo(b) × a_u
```

(El término `+65536 × signo(a) × signo(b)` desborda el resultado de 16 bits y desaparece.)

En la práctica: **haz la multiplicación sin signo, luego corrige el byte alto.** Si A era negativo, resta B del byte alto. Si B era negativo, resta A del byte alto. Sin valores absolutos, sin negación condicional del resultado.

En Z80 puro, el ahorro respecto a 2×abs es modesto --- el bucle de desplazamiento y suma domina el costo de cualquier forma. Pero en Z80N, donde `MUL DE` hace una multiplicación sin signo de 8×8 en una sola instrucción, el enfoque de corrección reduce la multiplicación con signo a ~70 T-states y 16 bytes:

```z80
; Multiplicación con signo 16x8 en Z80N (Ped7g)
; Entrada: DE = x (16 bits con signo), L = y (8 bits con signo)
; Salida:  AL = resultado con signo de 16 bits
; Costo:   ~70T, 16 bytes. Requiere instrucción MUL del Z80N.

    xor  a
    bit  7, l           ; ¿es y negativo?
    jr   z, .y_pos
    sub  e              ; compensar: byte alto −= low(x)
.y_pos:
    ld   h, d           ; H = x_alto, L = y
    ld   d, l           ; D = y,      E = x_bajo
    mul  de             ; DE = x_bajo * y (sin signo)
    add  a, d           ; acumular byte alto
    ex   de, hl         ; L = byte bajo del resultado
    mul  de             ; DE = x_alto * y (sin signo)
    add  a, e           ; byte alto final → A:L
    ret
```

El mismo principio funciona para Z80 puro --- guarda los operandos originales antes del bucle de desplazamiento y suma, luego aplica las dos restas condicionales al byte alto. El código es ligeramente más corto que 2×abs+neg, y evita PUSH/POP para la bandera de signo.

> **Crédito:** Técnica de corrección e implementación Z80N por Ped7g. Variantes para Z80 puro por base y busy (SinDiKat).

---

## División en Z80

La división en el Z80 es aún más dolorosa que la multiplicación. Sin instrucción de división, y el algoritmo es inherentemente serial -- cada bit del cociente depende de la resta anterior. Dark nuevamente presenta dos métodos: preciso y rápido.

### Método 1: desplazamiento y resta (división con restauración)

División larga binaria. Comienza con un acumulador en cero. El dividendo se desplaza desde la derecha, un bit por iteración. Intenta restar el divisor; si tiene éxito, establece un bit del cociente. Si falla, restaura el acumulador -- de ahí "división con restauración."

```z80 id:ch04_method_1_shift_and_subtract
; DIVU111 -- 8-bit unsigned divide
; Input:  B = dividend, C = divisor
; Output: B = quotient, A = remainder
; Cost:   236-244 T-states (Pentagon)
;
; From Dark / X-Trade, Spectrum Expert #01 (1997)

divu111:
    xor  a               ; clear accumulator (remainder workspace)
    ld   d, 8            ; 8 bits to process

.loop:
    sla  b               ; shift dividend left -- MSB into carry
    rla                  ; shift carry into accumulator
    cp   c               ; try to subtract divisor
    jr   c, .too_small   ; if accumulator < divisor, skip
    sub  c               ; subtract divisor from accumulator
    inc  b               ; set bit 0 of quotient (B was just shifted,
                         ;   so bit 0 is free)
.too_small:
    dec  d
    jr   nz, .loop
    ret                  ; B = quotient, A = remainder
```

El `INC B` para establecer el bit del cociente es un truco ingenioso: B acaba de ser desplazado a la izquierda por `SLA B`, así que el bit 0 está garantizado en cero. `INC B` lo establece sin afectar otros bits -- más barato que `OR` o `SET`.

La versión de 16 bits (DIVU222) cuesta de 938 a 1.034 T-states. Mil T-states para una sola división. Con un presupuesto de fotograma de ~70.000 T-states, puedes permitirte quizás 70 divisiones por fotograma -- sin hacer nada más. Por eso los motores 3D de la demoscene hacen esfuerzos extremos para evitar la división.

### Método 2: división logarítmica

La alternativa más rápida de Dark usa tablas de logaritmos:

```text
Log(A / B) = Log(A) - Log(B)
A / B = AntiLog(Log(A) - Log(B))
```

Con dos tablas de consulta de 256 bytes -- Log y AntiLog -- la división se convierte en dos búsquedas, una resta y una tercera búsqueda. El costo baja a aproximadamente 50-70 T-states. Para la división en perspectiva (dividir por Z para proyectar puntos 3D en la pantalla), esto cambia las reglas del juego.

**Generar la tabla de logaritmos** es donde las cosas se ponen interesantes. Dark propone construirla usando derivadas -- la misma técnica incremental que la tabla de cuadrados. La derivada de log2(x) es 1/(x * ln(2)), así que acumulas incrementos fraccionarios paso a paso, comenzando desde log2(1) = 0 y avanzando hacia arriba. La constante 1/ln(2) = 1,4427 necesita escalarse para caber en el rango de 8 bits de la tabla.

Y aquí es donde brilla la honestidad de Dark. Después de derivar la fórmula de generación, intenta calcular un coeficiente de corrección para el escalado de la tabla y llega a 0,4606. Luego escribe -- en un artículo de revista publicado -- *"Algo no está bien aquí, así que se recomienda escribir uno similar tú mismo."*

Un chico de diecisiete años en 1997, publicando en una revista en disco leída por sus pares a lo largo de la escena rusa del Spectrum, diciendo abiertamente: logré que esto funcionara, pero mi derivación tiene un hueco, descubre la versión limpia tú mismo. Esa honestidad es rara en la escritura técnica a cualquier nivel, y es una de las cosas que hacen de Spectrum Expert un documento tan notable.

En la práctica, las tablas de logaritmos funcionan. Los errores de redondeo al comprimir una función continua en 256 bytes son aceptables para la proyección en perspectiva. El motor 3D de Dark en *Illusion* usa exactamente esta técnica.

---

## Seno y coseno

Rotación, desplazamiento, plasma -- cada efecto que curva necesita trigonometría. En el Z80, pre-calculas una tabla de consulta. El enfoque de Dark es bellamente pragmático: una parábola es lo suficientemente parecida a una onda sinusoidal para el trabajo de demos.

### La aproximación parabólica

Medio período de coseno, de 0 a pi, curva de +1 hasta -1. Una parábola y = 1 - 2*(x/pi)^2 sigue casi la misma trayectoria. El error máximo es aproximadamente del 5,6% -- terrible para ingeniería, invisible en una demo a resolución de 256x192.

Dark genera una tabla de coseno con signo de 256 bytes (-128 a +127), indexada por ángulo: 0 = 0 grados, 64 = 90 grados, 128 = 180 grados, 256 vuelve a 0. El período de potencia de dos significa que el índice del ángulo se envuelve naturalmente con el desbordamiento de 8 bits, y el coseno se convierte en seno sumando 64.

```z80 id:ch04_the_parabolic_approximation
; Generate 256-byte signed cosine table (-128..+127)
; using parabolic approximation
;
; The table covers one full period: cos(n * 2*pi/256)
; scaled to signed 8-bit range.
;
; Approach: for the first half (0..127), compute
;   y = 127 - (x^2 * 255 / 128^2)
; approximated via incrementing differences.
; Mirror for second half.

gen_cos_table:
    ld   hl, cos_table
    ld   b, 0              ; x = 0
    ld   de, 0             ; running delta (fixed-point)

    ; First quarter: cos descends from +127 to 0
    ; Second quarter: continues to -128
    ; ...build via incremental squared differences

    ; In practice, the generation loop runs ~30 bytes
    ; and produces the table in a few hundred cycles.
```

La idea clave: no necesitas calcular x^2 para cada entrada. Dado que (x+1)^2 - x^2 = 2x + 1, construyes la parábola incrementalmente -- comienzas en el pico, restas un delta linealmente creciente. Sin multiplicación, sin división, sin punto flotante.

La tabla resultante es una aproximación parabólica por tramos. Grafícala contra el seno verdadero y te costará ver la diferencia. Para wireframe 3D o un scroller con rebote, es más que suficiente.

> **Recuadro: los 9 mandamientos de Raider para las tablas de seno**
>
> En los comentarios de Hype sobre el análisis de Introspec de *Illusion*, el programador veterano Raider publicó una lista de reglas para el diseño de tablas de seno que se conoció informalmente como los "9 mandamientos." Los principios clave:
>
> - Usa un tamaño de tabla potencia de dos (256 entradas es canónico).
> - Alinea la tabla a un límite de página para que `H` contenga la base y `L` sea el ángulo directo -- la indexación es gratuita.
> - Almacena valores con signo para uso directo en aritmética de coordenadas.
> - Deja que el ángulo se envuelva naturalmente vía el desbordamiento de 8 bits -- sin comprobación de límites.
> - El coseno es simplemente el seno desplazado un cuarto de período: carga el ángulo, suma 64, busca.
> - Si necesitas mayor precisión, usa una tabla de 16 bits (512 bytes) pero raramente lo necesitas.
> - Genera la tabla al inicio en lugar de almacenarla en el binario -- ahorra espacio, no cuesta nada.
> - Para rotación 3D, pre-multiplica por tu factor de escala y almacena los valores escalados.
> - Nunca computes trigonometría en tiempo de ejecución. Si crees que lo necesitas, estás equivocado.
>
> Estos mandamientos reflejan décadas de experiencia colectiva. Síguelos y tus tablas de seno serán rápidas, pequeñas y correctas.

---

## Trazado de líneas de Bresenham

Cada arista de un objeto de alambre es una línea de (x1,y1) a (x2,y2), y necesitas trazarla rápido. El tratamiento de Dark en Spectrum Expert #01 es la sección más larga de su artículo, recorriendo tres enfoques progresivamente más rápidos.

### El algoritmo clásico y la modificación de Xopha

El algoritmo de Bresenham avanza a lo largo del eje mayor un píxel a la vez, manteniendo un acumulador de error para los pasos del eje menor. En el Spectrum, "poner un píxel" es caro -- la memoria de pantalla entrelazada significa que calcular una dirección de byte y posición de bit cuesta T-states reales. La rutina de ROM toma más de 1.000 T-states por píxel. Incluso un bucle Bresenham optimizado a mano cuesta ~80 T-states por píxel.

Dark menciona la mejora de Xopha: mantener un puntero de pantalla (HL) y avanzarlo incrementalmente en lugar de recalcular desde cero. Moverse a la derecha significa rotar una máscara de bits; moverse hacia abajo significa el ajuste multi-instrucción DOWN_HL. Mejor, pero el problema central permanece.

### El método de matriz de Dark: cuadrículas de píxeles 8x8

Entonces Dark hace su observación clave: **"El 87,5% de las comprobaciones son desperdicio."**

En un bucle Bresenham, en cada píxel preguntas: ¿debería dar un paso lateral? Para una línea casi horizontal, la respuesta es casi siempre no. En promedio, siete de cada ocho comprobaciones no producen ningún paso lateral. Estás quemando T-states en una bifurcación condicional que casi nunca se activa.

La solución de Dark: pre-calcula el patrón de píxeles para cada pendiente de línea dentro de una cuadrícula de píxeles de 8x8, y desenrolla el bucle de dibujo para producir celdas de cuadrícula completas a la vez. Un segmento de línea dentro de un área de 8x8 está completamente determinado por su pendiente. Para cada uno de los ocho octantes, enumera todos los patrones posibles de 8 píxeles como secuencias directas de instrucciones `SET bit,(HL)` con incrementos de dirección entre ellas.

```z80 id:ch04_dark_s_matrix_method_8x8
; Example: one unrolled 8-pixel segment of a nearly-horizontal line
; (octant 0: moving right, gently sloping down)
;
; The line enters at the left edge of an 8x8 character cell
; and exits at the right edge, dropping one pixel row partway through.

    set  7, (hl)        ; pixel 0 (leftmost bit in byte)
    set  6, (hl)        ; pixel 1
    set  5, (hl)        ; pixel 2
    set  4, (hl)        ; pixel 3
    set  3, (hl)        ; pixel 4
    ; --- step down one pixel row ---
    inc  h              ; next screen row (within character cell)
    set  2, (hl)        ; pixel 5
    set  1, (hl)        ; pixel 6
    set  0, (hl)        ; pixel 7 (rightmost bit in byte)
```

Sin bifurcaciones condicionales. Sin acumulador de error. `SET bit,(HL)` cuesta 15 T-states; ocho de ellas más un par de operaciones `INC H` da ~130 T-states por segmento de 8 píxeles, o aproximadamente 16 T-states por píxel. Con la sobrecarga de búsqueda y avance de celda, Dark logra aproximadamente **48 T-states por píxel** -- casi la mitad del costo clásico de Bresenham.

El precio es memoria: una rutina desenrollada separada para cada pendiente por octante, aproximadamente **3KB en total**. En un Spectrum 128K, una inversión modesta para una ganancia de velocidad masiva.

### Terminación basada en trampa

En lugar de comprobar un contador de bucle en cada píxel, Dark coloca un centinela donde termina la línea. Cuando el código de dibujo alcanza el centinela, sale -- eliminando por completo la sobrecarga de `DEC counter / JR NZ`.

El sistema completo -- selección de octante, búsqueda de segmento, dibujo desenrollado, terminación por trampa -- es una de las piezas de código más impresionantes en Spectrum Expert #01. Cuando Introspec desensamblaba *Illusion* en 2017, encontró este método de matriz en funcionamiento, dibujando los wireframes a velocidad de fotograma completa.

---

## Aritmética de punto fijo

Cada algoritmo en este capítulo asume algo que aún no hemos hecho explícito: los números de punto fijo.

El Z80 no tiene unidad de punto flotante. Cada registro contiene un entero. Pero los efectos de demo necesitan valores fraccionarios -- ángulos de rotación, velocidades sub-píxel, factores de escala. La solución es el punto fijo: elige una convención para dónde vive el "punto decimal" dentro de un entero, luego haz toda la aritmética con enteros mientras rastreas la escala mentalmente.

### Formato 8.8

El formato más común en el Z80 es **8.8**: byte alto = parte entera, byte bajo = parte fraccionaria. Un par de registros de 16 bits contiene un número de punto fijo:

```text
H = integer part    (-128..+127 signed, or 0..255 unsigned)
L = fractional part (0..255, representing 0/256 to 255/256)
```

`HL = $0180` representa 1,5 (H=1, L=128, y 128/256 = 0,5). `HL = $FF80` con signo es -0,5 (H=$FF = -1 en complemento a dos, L=$80 suma 0,5).

La belleza: **la suma y la resta son gratuitas** -- simplemente operaciones normales de 16 bits:

```z80 id:ch04_format_8_8_2
; Fixed-point 8.8 addition: result = a + b
; HL = first operand, DE = second operand
    add  hl, de          ; that's it. 11 T-states.

; Fixed-point 8.8 subtraction: result = a - b
    or   a               ; clear carry
    sbc  hl, de          ; 15 T-states.
```

Al procesador no le importa que estés tratando estos como punto fijo. La suma binaria es la misma ya sea que los bits representen enteros o valores 8.8.

### Multiplicación de punto fijo

Multiplicar dos números 8.8 produce un resultado 16.16 -- 32 bits. Quieres 8.8 de vuelta, así que tomas los bits 8..23 del producto (efectivamente desplazando a la derecha por 8). En la práctica, con partes enteras pequeñas (coordenadas, factores de rotación entre -1 y +1), puedes descomponer la multiplicación en productos parciales:

```z80 id:ch04_fixed_point_multiplication
; Fixed-point 8.8 multiply (simplified)
; Input:  BC = first operand (B.C in 8.8)
;         DE = second operand (D.E in 8.8)
; Output: HL = result (H.L in 8.8)
;
; Full product = BC * DE (32 bits), we want bits 8..23
;
; Decomposition:
;   BC * DE = (B*256+C) * (D*256+E)
;           = B*D*65536 + (B*E + C*D)*256 + C*E
;
; In 8.8 result (bits 8..23):
;   H.L = B*D*256 + B*E + C*D + (C*E)/256
;
; For small B,D (say -1..+1), B*D*256 is the dominant term.
; C*E/256 is a rounding correction.
; Total cost: ~200 T-states using the shift-and-add multiplier.

fixmul88:
    ; Multiply B*E -> add to result high
    ld   a, b
    call mul8             ; A = B*E (assuming 8x8->8 truncated)
    ld   h, a

    ; Multiply C*D -> add to result
    ld   a, c
    ld   b, d
    call mul8             ; A = C*D
    add  a, h
    ld   h, a

    ; For higher precision, also compute B*D and C*E
    ; and combine. In practice, the two middle terms
    ; are often sufficient for demo work.

    ld   l, 0             ; fractional part (approximate)
    ret
```

Para rotación impulsada por tabla de seno donde los valores de seno son de 8 bits con signo (-128 a +127, representando -1,0 a +0,996), multiplicar una coordenada de 8 bits por un valor de seno vía `mulu112` da un resultado de 16 bits ya en formato 8.8 -- el byte alto es la coordenada entera rotada, el byte bajo es la fracción.

### Por qué importa el punto fijo

El formato 8.8 es el punto óptimo para el Z80: cabe en un par de registros, suma/resta son gratuitas, la multiplicación cuesta ~200 T-states, y la precisión es suficiente para efectos a resolución de pantalla. Existen otros formatos -- 4.12 para más precisión fraccionaria, 12.4 para más rango entero -- pero 8.8 cubre la gran mayoría de los casos de uso. Los capítulos de desarrollo de juegos más adelante en este libro usan 8.8 exclusivamente.

---

## Teoría y práctica

Estos algoritmos no son técnicas aisladas. Forman un sistema. La multiplicación alimenta la matriz de rotación. La rotación produce coordenadas que necesitan división en perspectiva. La división usa tablas de logaritmos. Los vértices proyectados se conectan con líneas trazadas por el método de matriz. Todo funciona con aritmética de punto fijo, con valores de seno de la tabla parabólica.

Dark diseñó estos como componentes de un solo motor -- el motor que impulsó *Illusion*. Un cubo de alambre girando a velocidad de fotograma completa ejercita cada rutina de este capítulo:

1. **Leer el ángulo de rotación** de la tabla de seno (aproximación parabólica, ~20 T-states por búsqueda)
2. **Multiplicar** las coordenadas de los vértices por factores de rotación (desplazamiento y suma para precisión, o tabla de cuadrados para velocidad -- ~200 o ~61 T-states por multiplicación, 12 multiplicaciones por vértice)
3. **Dividir** por Z para proyección en perspectiva (tablas de logaritmos, ~60 T-states por división)
4. **Trazar líneas** entre vértices proyectados (Bresenham de matriz, ~48 T-states por píxel)

Para un cubo simple (8 vértices, 12 aristas), el costo total por fotograma es aproximadamente:

- Rotación: 8 vértices x 12 multiplicaciones x 200 T-states = 19.200 T-states
- Proyección: 8 vértices x 1 división x 60 T-states = 480 T-states
- Trazado de líneas: 12 aristas x ~40 píxeles x 48 T-states = 23.040 T-states
- **Total: ~42.720 T-states** -- cómodamente dentro del presupuesto de ~70.000 T-states por fotograma

Cambia a la multiplicación rápida de tabla de cuadrados y la rotación baja a 5.760 T-states. Los vértices tiemblan ligeramente, pero ahora tienes margen para objetos más complejos. Velocidad o precisión -- en una demo, tomas esa decisión para cada efecto, cada fotograma.

---

## Lo que Dark hizo bien

Mirando hacia atrás a Spectrum Expert #01 desde casi treinta años de distancia, lo que te impresiona no es solo la calidad de los algoritmos sino la calidad del pensamiento. Dark presenta cada uno, explica las contrapartidas honestamente, admite cuando su derivación tiene lagunas, y confía en el lector para llenar esas lagunas.

Estaba escribiendo para programadores de Spectrum en Rusia a finales de los 1990 -- una comunidad que construía algunas de las demos de 8 bits más impresionantes del mundo, en hardware que el resto del mundo había abandonado. Estos son los bloques de construcción que usaban. Cuando escribas tu primer motor 3D para el Spectrum, estas rutinas lo harán posible.

En el siguiente capítulo, Dark y STS extienden esta base matemática hacia un sistema 3D completo: el método del punto medio para interpolación de vértices, eliminación de caras traseras y renderizado de polígonos sólidos. Las matemáticas aquí son la base. El Capítulo 5 es la arquitectura construida encima.

---

## Números aleatorios: cuando las tablas no alcanzan

Todo lo visto hasta ahora en este capítulo es determinista. Dadas las mismas entradas, la misma multiplicación, la misma búsqueda de seno, el mismo trazado de línea -- obtienes la misma salida. Eso es exactamente lo que quieres para un cubo de alambre girando o un plasma suave.

Pero a veces necesitas caos. Estrellas titilando en un campo estelar. Partículas dispersándose de una explosión. Texturas de ruido para generación de terreno. Un orden aleatorio para pantallas de carga. En competiciones de sizecoding (256 bytes o menos), un buen generador de números aleatorios puede producir efectos visuales sorprendentemente complejos desde casi nada de código.

El Z80 no tiene generador de números aleatorios por hardware. Debes sintetizar la aleatoriedad desde aritmética, y la calidad de esa aritmética importa más de lo que podrías pensar.

### El truco del registro R

El Z80 tiene una fuente incorporada de entropía a la que muchos programadores recurren primero: el registro R. Se incrementa automáticamente con cada búsqueda de instrucción (cada ciclo M1), ciclando a través de 0-127. Puedes leerlo en 9 T-states:

```z80 id:ch04_the_r_register_trick
    ld   a, r              ; 9 T -- read refresh counter
```

Esto *no* es un PRNG. El registro R es completamente determinista -- avanza uno por instrucción, y su valor en cualquier punto depende enteramente de la ruta de código tomada desde el reinicio. En una demo con un bucle principal fijo, R produce la misma secuencia cada vez. Pero es útil como fuente de semilla: lee R una vez al inicio (cuando la temporización depende de cuánto esperó el usuario antes de presionar una tecla) y alimenta ese valor impredecible a un PRNG propiamente dicho.

Algunos programadores mezclan R en su generador en cada llamada, añadiendo entropía genuina de temporización de instrucciones. El generador Ion que veremos abajo usa exactamente este truco.

### Cuatro generadores de la comunidad

En 2024, Gogin (de la escena ZX rusa) reunió una colección de rutinas PRNG para Z80 y las compartió para evaluación. Gogin las probó sistemáticamente, llenando grandes bitmaps para revelar patrones estadísticos. Los resultados son instructivos -- no todas las rutinas "aleatorias" son igualmente aleatorias.

Aquí hay cuatro generadores de esa colección, ordenados de mejor a peor calidad.

#### Generador CMWC de Patrik Rak (Raxoft) (mejor calidad)

Este es un generador de **Complemento Multiplicación-Con-Acarreo** de Patrik Rak (Raxoft), usando el multiplicador 253 y un búfer circular de 8 bytes. Las matemáticas detrás de CMWC están bien estudiadas: George Marsaglia demostró que ciertas combinaciones de multiplicador/búfer producen secuencias con períodos enormes. Con multiplicador 253 y tamaño de búfer 8, el período teórico es (253^8 - 1) / 254 -- aproximadamente 2^66 valores antes de repetirse.

```z80 id:ch04_four_generators_from_the
; Patrik Rak's CMWC PRNG
; Quality: Excellent -- passes visual bitmap tests
; Size:    ~30 bytes code + 8 bytes table
; Output:  A = pseudo-random byte
; Period:  ~2^66

patrik_rak_cmwc_rnd:
    ld   hl, .table
.smc_idx:
    ld   bc, 0              ; 10 T -- i (self-modifying)
    add  hl, bc             ; 11 T
    ld   a, c               ; 4 T
    inc  a                  ; 4 T
    and  7                  ; 7 T -- wrap index to 0-7
    ld   (.smc_idx+1), a    ; 13 T -- store new index
    ld   c, (hl)            ; 7 T -- y = q[i]
    ex   de, hl             ; 4 T
    ld   h, c               ; 4 T -- t = 256 * y
    ld   l, b               ; 4 T
    sbc  hl, bc             ; 15 T -- t = 255 * y
    sbc  hl, bc             ; 15 T -- t = 254 * y
    sbc  hl, bc             ; 15 T -- t = 253 * y
.smc_car:
    ld   c, 0               ; 7 T -- carry (self-modifying)
    add  hl, bc             ; 11 T -- t = 253 * y + c
    ld   a, h               ; 4 T
    ld   (.smc_car+1), a    ; 13 T -- c = t / 256
    ld   a, l               ; 4 T -- x = t % 256
    cpl                     ; 4 T -- x = ~x (complement)
    ld   (de), a            ; 7 T -- q[i] = x
    ret                     ; 10 T

.table:
    DB   82, 97, 120, 111, 102, 116, 20, 12
```

El algoritmo multiplica la entrada actual del búfer por 253, suma un valor de acarreo, almacena el nuevo acarreo y complementa el resultado. El búfer circular de 8 bytes significa que el espacio de estados del generador es vasto -- 8 bytes de búfer más 1 byte de acarreo más el índice, dando mucho más estado interno del que cualquier generador de un solo registro puede lograr.

Veredicto de Gogin: **mejor calidad** de la colección. Al llenar un bitmap de 256x192, no emergen patrones visibles incluso a gran escala.

#### Ion Random (segundo mejor)

Originalmente de Ion Shell para la calculadora TI-83, adaptado para Z80. Este generador mezcla el registro R con un bucle de retroalimentación, logrando una aleatoriedad sorprendentemente buena desde solo ~15 bytes:

```z80 id:ch04_four_generators_from_the_2
; Ion Random
; Quality: Good -- minor patterns visible only at extreme scale
; Size:    ~15 bytes
; Output:  A = pseudo-random byte
; Origin:  Ion Shell (TI-83), adapted for Z80

ion_rnd:
.smc_seed:
    ld   hl, 0              ; 10 T -- seed (self-modifying)
    ld   a, r               ; 9 T -- read refresh counter
    ld   d, a               ; 4 T
    ld   e, (hl)            ; 7 T
    add  hl, de             ; 11 T
    add  a, l               ; 4 T
    xor  h                  ; 4 T
    ld   (.smc_seed+1), hl  ; 16 T -- update seed
    ret                     ; 10 T
```

La inyección del registro R significa que este generador produce secuencias diferentes dependiendo del contexto de llamada -- cuántas instrucciones se ejecutan entre llamadas afecta a R, que se retroalimenta al estado. Para un bucle principal de demo con temporización fija, R avanza de forma predecible, pero la mezcla no lineal (ADD + XOR) aún produce buena salida. En un juego donde la entrada del jugador varía el patrón de llamadas, la contribución de R añade imprevisibilidad genuina.

Veredicto de Gogin: **segundo mejor**. Muy compacto, buena calidad para su tamaño.

#### XORshift 16-bit (mediocre)

Un generador XORshift de 16 bits -- la adaptación para Z80 de la bien conocida familia de Marsaglia:

```z80 id:ch04_four_generators_from_the_3
; 16-bit XORshift PRNG
; Quality: Mediocre -- visible diagonal patterns in bitmap tests
; Size:    ~25 bytes
; Output:  A = pseudo-random byte (H or L)
; Period:  65535

xorshift_rnd:
.smc_state:
    ld   hl, 1              ; 10 T -- state (self-modifying, must not be 0)
    ld   a, h               ; 4 T
    rra                     ; 4 T
    ld   a, l               ; 4 T
    rra                     ; 4 T
    xor  h                  ; 4 T
    ld   h, a               ; 4 T
    ld   a, l               ; 4 T
    rra                     ; 4 T
    ld   a, h               ; 4 T
    rra                     ; 4 T
    xor  l                  ; 4 T
    ld   l, a               ; 4 T
    xor  h                  ; 4 T
    ld   h, a               ; 4 T
    ld   (.smc_state+1), hl ; 16 T -- update state
    ret                     ; 10 T
```

Los generadores XORshift son rápidos y simples, pero con solo 16 bits de estado el período es como máximo 65.535. De forma más problemática, el patrón de rotación de bits crea rayas diagonales visibles cuando la salida se mapea a píxeles. Para un campo estelar rápido o efecto de partículas esto puede ser aceptable. Para cualquier cosa que llene grandes áreas de pantalla con "ruido", los patrones se vuelven obvios.

#### Variante CMWC de Patrik Rak (Raxoft) (mediocre)

Una segunda variante CMWC de Patrik Rak (Raxoft), similar en principio a su versión anterior pero con un arreglo de búfer diferente. Gogin encontró que producía **patrones visibles a escala** -- probablemente debido a cómo la propagación de acarreo interactúa con la indexación del búfer. La incluimos en el ejemplo compilable (`examples/prng.a80`) por completitud, pero para uso en producción, su versión de búfer de 8 bytes anterior es estrictamente superior.

### El enfoque Tribonacci de Elite

Vale una breve mención: el legendario *Elite* (1984) usó una secuencia tipo Tribonacci para su galaxia generada proceduralmente. Tres registros se retroalimentan entre sí en un ciclo, produciendo secuencias deterministas pero bien distribuidas. La idea clave era la reproducibilidad -- dada la misma semilla, la misma galaxia se genera cada vez, lo que significaba que el universo entero podía "caber" en unos pocos bytes de estado del generador. David Braben e Ian Bell usaron esto para generar 8 galaxias de 256 sistemas estelares cada una desde un puñado de bytes de semilla. La técnica está más cerca de una función hash que de un PRNG, pero el principio -- estado pequeño, gran complejidad aparente -- es el mismo que impulsa el sizecoding en la demoscene.

### Generador de galaxias de Elite: una mirada más profunda

El enfoque Tribonacci merece más detalle porque ilustra un principio clave: **un PRNG no es solo una fuente de números aleatorios -- es un algoritmo de compresión.**

David Braben e Ian Bell necesitaban 8 galaxias de 256 sistemas estelares, cada uno con un nombre, posición, economía, tipo de gobierno y nivel tecnológico. Almacenar todo eso explícitamente consumiría kilobytes. En su lugar, almacenaron solo una semilla de 6 bytes por galaxia y un generador determinista que expandía cada semilla en los datos completos del sistema estelar. El generador era un bucle de retroalimentación de tres registros -- cada paso rota y hace XOR de tres valores de 16 bits:

```z80 id:ch04_elite_s_galaxy_generator_a
; Elite's galaxy generator (conceptual, 6502 origin):
;   seed = [s0, s1, s2]  (three 16-bit words)
;   twist: s0' = s1, s1' = s2, s2' = s0 + s1 + s2  (mod 65536)
;   repeat twist for each byte of star system data
```

En el Z80, el mismo principio funciona con tres pares de registros. La operación "twist" produce valores deterministas pero bien distribuidos. La propiedad crucial: dada la misma semilla, la misma galaxia se genera cada vez. La navegación entre estrellas es simplemente re-sembrar y re-generar.

Esta idea -- **estado pequeño, gran complejidad aparente** -- impulsa el sizecoding de la demoscene también. Una intro de 256 bytes que llena la pantalla con patrones intrincados está haciendo exactamente lo que Elite hizo: expandir una semilla diminuta en una salida grande y compleja a través de un proceso determinista.

### Aleatoriedad moldeada

A veces quieres números que son aleatorios pero siguen una distribución específica. Un PRNG uniforme plano da a cada valor la misma probabilidad, pero los fenómenos del mundo real raramente son uniformes: tasas de aparición de enemigos, velocidades de partículas, alturas de terreno -- todos tienden a agruparse alrededor de valores preferidos.

Trucos comunes en el Z80:

- **Distribución triangular** -- suma dos bytes aleatorios uniformes y desplaza a la derecha. La suma se agrupa alrededor del centro (128), produciendo variación de "aspecto natural". Costo: dos llamadas PRNG + ADD + SRL = ~20 T-states extra.

```z80 id:ch04_shaped_randomness
; Triangular random: result clusters around 128
    call patrik_rak_cmwc_rnd  ; A = uniform random
    ld   b, a
    call patrik_rak_cmwc_rnd  ; A = another uniform random
    add  a, b                 ; sum (wraps at 256)
    rra                       ; divide by 2 → triangular distribution
```

- **Muestreo por rechazo** -- genera un número aleatorio, rechaza valores fuera de tu rango deseado. Para rangos potencia de dos esto es gratuito (simplemente AND con una máscara). Para rangos arbitrarios, repite el bucle hasta que el valor encaje.

- **Tablas ponderadas** -- almacena una tabla de consulta de 256 bytes donde cada valor de salida aparece en proporción a su probabilidad deseada. Indexa con un byte aleatorio uniforme. La tabla cuesta 256 bytes pero la búsqueda es instantánea (7 T-states). Perfecta cuando la distribución es compleja y fija.

- **PRNG como función hash** -- alimenta datos estructurados (coordenadas, números de fotograma) a través del PRNG para obtener ruido determinista. Así es como funcionan las texturas de plasma y ruido en sizecoding: `random(x XOR y XOR frame)` da un valor de aspecto diferente por píxel por fotograma, pero es completamente reproducible.

### Semillas y reproducibilidad

En una demo, la reproducibilidad es generalmente deseable: el efecto debería verse igual cada vez que se ejecuta, porque el programador coreografió los visuales para coincidir con la música. Siembra el PRNG una vez con un valor fijo y la secuencia es determinista.

En un juego, la imprevisibilidad importa. Estrategias comunes de siembra:

- **Variable del sistema FRAMES ($5C78)** -- la ROM del Spectrum mantiene un contador de fotogramas de 3 bytes en la dirección $5C78 que se incrementa cada 1/50 de segundo desde el encendido. Leerlo da una semilla dependiente del tiempo que varía según cuánto tiempo ha estado encendida la máquina. Art-top (Artem Topchiy) recomienda usarlo para inicializar la tabla CMWC de Patrik Rak:

```z80 id:ch04_seeds_and_reproducibility
; Seed Patrik Rak CMWC from FRAMES system variable
    ld   hl, $5C78            ; FRAMES (3 bytes, increments at 50 Hz)
    ld   a, (hl)              ; low byte -- most variable
    ld   de, patrik_rak_cmwc_rnd.table
    ld   b, 8
.seed_loop:
    xor  (hl)                 ; mix with FRAMES
    ld   (de), a              ; write to table
    inc  de
    rlca                      ; rotate for variety
    add  a, b                 ; add loop counter
    djnz .seed_loop
```

- **Leer R en un momento de entrada del usuario** -- el conteo exacto de instrucciones entre el reinicio y que el jugador presione una tecla varía en cada ejecución. `LD A,R` en ese momento captura entropía de temporización.
- **Acumulación de contador de fotogramas** -- haz XOR del registro R en un acumulador cada fotograma durante la pantalla de título; usa el valor acumulado como semilla cuando comience el juego.
- **Combinar múltiples fuentes** -- haz XOR de R, el byte bajo de FRAMES, y un byte del bus flotante (en Spectrums 48K, leer ciertos puertos devuelve lo que la ULA está leyendo actualmente de la RAM -- una fuente de entropía posicional).

Para demos, simplemente inicializa el estado del generador a un valor conocido y déjalo. El ejemplo compilable (`examples/prng.a80`) muestra los cuatro generadores con semillas fijas.

### Tabla comparativa

| Algoritmo | Tamaño (bytes) | Velocidad (T-states) | Calidad | Período | Notas |
|-----------|-------------|-------------------|---------|--------|-------|
| Patrik Rak CMWC | ~30 + 8 tabla | ~170 | Excelente | ~2^66 | El mejor en general; búfer de 8 bytes |
| Ion Random | ~15 | ~75 | Buena | Depende de R | Compacto; mezcla registro R |
| XORshift 16 | ~25 | ~90 | Mediocre | 65.535 | Patrones diagonales visibles |
| Patrik Rak CMWC (alt) | ~35 + 10 tabla | ~180 | Mediocre | ~2^66 | Patrones visibles a escala |
| Solo LD A,R | 2 | 9 | Pobre | 128 | NO es un PRNG; usar solo como semilla |

Para la mayoría del trabajo de la demoscene, el **CMWC de Patrik Rak** es el claro ganador: calidad excelente, tamaño razonable, y un período tan largo que nunca se repetirá durante una demo. Si el tamaño de código es crítico (sizecoding, intros de 256 bytes), **Ion Random** empaqueta una calidad notable en 15 bytes. XORshift es un respaldo cuando necesitas algo rápido y no te importa la calidad visual.

> **Créditos:** Colección de PRNGs, evaluación de calidad y pruebas de bitmap por **Gogin**. El generador CMWC de Patrik Rak está basado en la teoría de Complemento Multiplicación-Con-Acarreo de George Marsaglia. Ion Random se origina en **Ion Shell** para la calculadora TI-83.

![Salida de PRNG --- colores aleatorios de atributos llenan la pantalla, revelando la calidad estadística del generador](../../build/screenshots/ch04_prng.png)

---

*Todos los conteos de ciclos en este capítulo son para temporización Pentagon (sin estados de espera). En un Spectrum 48K estándar o Scorpion con memoria contendida, espera conteos más altos para código ejecutándose en los 32K inferiores de RAM. Ver Apéndice A para la referencia completa de temporización.*

> **Fuentes:** Dark / X-Trade, "Programming Algorithms" (Spectrum Expert #01, 1997); Gogin, colección y evaluación de calidad de PRNGs; Patrik Rak (Raxoft), generador CMWC; Ped7g (Peter Helcmanovsky), identificación del vacío de aritmética con signo y revisión
