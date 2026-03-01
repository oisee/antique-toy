# Capítulo 2: La pantalla como un rompecabezas

> "¿Por qué las filas van en ese orden?"
> -- Todo programador de ZX Spectrum, en algún momento

Abre cualquier emulador, escribe `PEEK 16384` y estarás leyendo el primer byte de la pantalla del Spectrum. Pero ¿qué byte es? No el superior izquierdo de la pantalla en ningún sentido simple. El píxel en la coordenada (0,0) está ahí, sí -- pero el píxel en (0,1), la siguiente fila hacia abajo, vive a 256 bytes de distancia. El píxel en (0,8), la fila superior de la segunda celda de caracteres, vive a solo 32 bytes del inicio. Y el píxel en (0,64) -- la primera fila del tercio medio de la pantalla -- vive exactamente a 2.048 bytes del inicio, en `$4800`.

Este es el rompecabezas más famoso del Spectrum. El diseño de pantalla entrelazado no es secuencial, no es intuitivo y no es un accidente. Es una consecuencia de las decisiones de diseño de hardware tomadas en 1982, y moldea cada pieza de código que toca la pantalla. Entender este diseño -- y aprender los trucos que lo hacen rápido de navegar -- es fundamental para todo lo que sigue en este libro.

---

## El mapa de memoria: 6.912 bytes de pantalla

La pantalla del Spectrum ocupa una región fija de memoria:

```text
$4000 - $57FF    Pixel data      6,144 bytes   (256 x 192 pixels, 1 bit per pixel)
$5800 - $5AFF    Attributes        768 bytes   (32 x 24 colour cells)
```

El área de píxeles contiene el mapa de bits: 256 píxeles de ancho, empaquetados 8 por byte, dando 32 bytes por fila. Con 192 filas, eso son 32 x 192 = 6.144 bytes. Cada byte representa 8 píxeles horizontales, con el bit 7 como el píxel más a la izquierda y el bit 0 como el más a la derecha.

El área de atributos contiene la información de color: un byte por cada celda de caracteres de 8x8. Hay 32 columnas y 24 filas, dando 32 x 24 = 768 bytes.

En total: 6.144 + 768 = 6.912 bytes. Esa es toda la pantalla.

<!-- figure: ch02_screen_layout -->
![Diseño de la memoria de pantalla del ZX Spectrum con tercios, celdas de caracteres y área de atributos](illustrations/output/ch02_screen_layout.png)

Los datos de píxeles y los datos de atributos sirven para propósitos diferentes pero están estrechamente acoplados. Cada byte de píxeles controla 8 puntos en pantalla; el byte de atributos de la celda de 8x8 correspondiente controla en qué color aparecen esos puntos. Cambia el píxel y cambias la forma. Cambia el atributo y cambias el color. Pero solo puedes cambiar el color para un bloque completo de 8x8 -- no por píxel. Este es el "conflicto de atributos" que define el carácter visual del Spectrum, y volveremos a él en breve.

Primero, el rompecabezas: ¿por qué las filas de píxeles están desordenadas?

---

## El entrelazado: dónde viven las filas

Si el Spectrum almacenara sus filas de píxeles secuencialmente, la fila 0 estaría en `$4000`, la fila 1 en `$4020`, la fila 2 en `$4040`, y así sucesivamente. Cada fila tiene 32 bytes, así que la fila N estaría simplemente en `$4000 + N * 32`. Simple, rápido, sensato.

Eso no es lo que ocurre.

La pantalla está dividida en tres **tercios**, cada uno de 64 filas de píxeles de alto. Dentro de cada tercio, las filas están entrelazadas por fila de caracteres. Aquí es donde realmente viven las primeras 16 filas:

```text
Row  0:  $4000     Third 0, char row 0, scan line 0
Row  1:  $4100     Third 0, char row 0, scan line 1
Row  2:  $4200     Third 0, char row 0, scan line 2
Row  3:  $4300     Third 0, char row 0, scan line 3
Row  4:  $4400     Third 0, char row 0, scan line 4
Row  5:  $4500     Third 0, char row 0, scan line 5
Row  6:  $4600     Third 0, char row 0, scan line 6
Row  7:  $4700     Third 0, char row 0, scan line 7
Row  8:  $4020     Third 0, char row 1, scan line 0
Row  9:  $4120     Third 0, char row 1, scan line 1
Row 10:  $4220     Third 0, char row 1, scan line 2
Row 11:  $4320     Third 0, char row 1, scan line 3
Row 12:  $4420     Third 0, char row 1, scan line 4
Row 13:  $4520     Third 0, char row 1, scan line 5
Row 14:  $4620     Third 0, char row 1, scan line 6
Row 15:  $4720     Third 0, char row 1, scan line 7
```

Observa el patrón. Las primeras 8 filas son las 8 líneas de escaneo de la fila de caracteres 0 -- pero están a 256 bytes de distancia, no 32. Dentro de esas 8 filas, el byte alto de la dirección se incrementa en 1 cada vez: `$40`, `$41`, `$42`, ... `$47`. Luego la fila 8 salta a `$4020` -- de vuelta a un byte alto de `$40`, pero con el byte bajo avanzado en 32.

Aquí está la imagen completa para el tercio superior de la pantalla:

```text
Char row 0:   scan lines at $4000, $4100, $4200, $4300, $4400, $4500, $4600, $4700
Char row 1:   scan lines at $4020, $4120, $4220, $4320, $4420, $4520, $4620, $4720
Char row 2:   scan lines at $4040, $4140, $4240, $4340, $4440, $4540, $4640, $4740
Char row 3:   scan lines at $4060, $4160, $4260, $4360, $4460, $4560, $4660, $4760
Char row 4:   scan lines at $4080, $4180, $4280, $4380, $4480, $4580, $4680, $4780
Char row 5:   scan lines at $40A0, $41A0, $42A0, $43A0, $44A0, $45A0, $46A0, $47A0
Char row 6:   scan lines at $40C0, $41C0, $42C0, $43C0, $44C0, $45C0, $46C0, $47C0
Char row 7:   scan lines at $40E0, $41E0, $42E0, $43E0, $44E0, $45E0, $46E0, $47E0
```

El tercio medio comienza en `$4800` y sigue el mismo patrón. El tercio inferior comienza en `$5000`.

### ¿Por qué?

La razón es la ULA -- el Uncommitted Logic Array que genera la señal de vídeo. La ULA lee un byte de datos de píxeles y un byte de datos de atributos por cada celda de caracteres de 8 píxeles que dibuja. Necesita ambos bytes en momentos específicos mientras recorre la pantalla.

El diseño entrelazado significaba que la lógica del contador de direcciones de la ULA podía construirse con menos puertas. Mientras la ULA escanea de izquierda a derecha a lo largo de una fila de caracteres, incrementa los 5 bits bajos de la dirección (la columna). Cuando llega al borde derecho, incrementa el byte alto para pasar a la siguiente línea de escaneo dentro de la misma fila de caracteres. Cuando termina las 8 líneas de escaneo, reinicia el byte alto y avanza los bits de fila del byte bajo.

Esto es elegante desde la perspectiva del hardware. La generación de direcciones de la ULA es una combinación simple de contadores -- sin multiplicación, sin aritmética de direcciones compleja. El ruteo del PCB era más simple, el conteo de puertas era menor y el chip era más barato de fabricar.

El programador paga el precio.

---

## El diseño de bits: decodificando (x, y) en una dirección

![Diseño de la memoria de pantalla del ZX Spectrum — tercios entrelazados con mapeo de bits de dirección codificado por colores](../../build/screenshots/proto_ch02_screen_layout.png)

Para entender el entrelazado con precisión, observa cómo la coordenada Y se mapea a la dirección de pantalla de 16 bits. Considera un píxel en la columna `x` (0--255) y la fila `y` (0--191). El byte que contiene ese píxel está en:

```text
High byte:  0 1 0 T T S S S
Low byte:   L L L C C C C C
```

Donde:
- `TT` = qué tercio de la pantalla (0, 1 o 2). Bits 7--6 de y.
- `SSS` = línea de escaneo dentro de la celda de caracteres (0--7). Bits 2--0 de y.
- `LLL` = fila de caracteres dentro del tercio (0--7). Bits 5--3 de y.
- `CCCCC` = columna en bytes (0--31). Esto es x / 8, o equivalentemente los bits 7--3 de x.

Lo crucial: los bits de y no están en orden. Los bits 7-6 van a un lugar, los bits 5-3 van a otro, y los bits 2-0 van a otro más. La coordenada y se trocea y se distribuye por toda la dirección.

Visualicemos esto con un ejemplo concreto. Píxel (80, 100):

```text
x = 80:     column byte = 80 / 8 = 10      CCCCC = 01010
y = 100:    binary = 01100100
            TT  = 01       (third 1, the middle third)
            LLL = 100      (char row 4 within the third)
            SSS = 100      (scan line 4 within the char cell)

High byte:  0  1  0  0  1  1  0  0  = $4C
Low byte:   1  0  0  0  1  0  1  0  = $8A

Address: $4C8A
```

El bit dentro de ese byte está determinado por los 3 bits bajos de x. El bit 7 es el píxel más a la izquierda, así que la posición del píxel (x AND 7) se mapea al bit 7 - (x AND 7).

### El cálculo de la dirección en Z80

Convertir (x, y) a una dirección de pantalla es algo que necesitas hacer rápido y a menudo. Aquí tienes una rutina estándar:

```z80 id:ch02_the_address_calculation_in
; Input:  B = y (0-191), C = x (0-255)
; Output: HL = screen address, A = bit mask
;
pixel_addr:
    ld   a, b          ; 4T   A = y
    and  $07           ; 7T   A = SSS (scan line within char)
    or   $40           ; 7T   A = 010 00 SSS (add screen base)
    ld   h, a          ; 4T   H = high byte (partial)

    ld   a, b          ; 4T   A = y again
    rla                ; 4T   \  shift bits 5-3 of y
    rla                ; 4T   /  left to bits 7-5
    and  $E0           ; 7T   mask to get LLL 00000
    ld   l, a          ; 4T   L = LLL 00000 (partial)

    ld   a, b          ; 4T   A = y again
    and  $C0           ; 7T   A = TT 000000
    rra                ; 4T   \
    rra                ; 4T    | shift bits 7-6 of y
    rra                ; 4T   /  to bits 4-3
    or   h             ; 4T   combine with SSS
    ld   h, a          ; 4T   H = 010 TT SSS (complete)

    ld   a, c          ; 4T   A = x
    rra                ; 4T   \
    rra                ; 4T    | x / 8
    rra                ; 4T   /
    and  $1F           ; 7T   mask to CCCCC
    or   l             ; 4T   combine with LLL 00000
    ld   l, a          ; 4T   L = LLL CCCCC (complete)
                       ; --- Total: ~87 T-states
```

87 T-states no es barato. En un bucle interno cerrado procesando miles de píxeles, no llamarías a esta rutina por píxel. En su lugar, calculas la dirección inicial una vez y luego navegas la pantalla usando manipulación rápida de punteros -- lo que nos lleva a la rutina más importante en la programación de gráficos del Spectrum.

![Demo de trazado de píxeles — píxeles individuales colocados en pantalla usando la rutina de cálculo de direcciones](../../build/screenshots/ch02_pixel_demo.png)

---

## DOWN_HL: Moverse una fila de píxeles hacia abajo

Tienes un puntero en HL a algún byte en la pantalla. Quieres moverlo una fila de píxeles hacia abajo -- al byte en la misma columna, una línea de escaneo más abajo. ¿Qué tan difícil puede ser?

En un framebuffer lineal, sumas 32 (el número de bytes por fila). Un `ADD HL, DE` con DE = 32: 11 T-states, listo.

En el Spectrum, es un rompecabezas dentro del rompecabezas. Moverse una fila de píxeles hacia abajo significa:

1. **Dentro de una celda de caracteres** (líneas de escaneo 0--6 a 1--7): incrementa H. Los bits de línea de escaneo están en los 3 bits bajos de H, así que `INC H` te mueve una línea de escaneo hacia abajo.

2. **Cruzando un límite de celda de caracteres** (línea de escaneo 7 a línea de escaneo 0 de la siguiente fila): reinicia los bits de línea de escaneo de H a 0, y suma 32 a L para pasar a la siguiente fila de caracteres.

3. **Cruzando un límite de tercio** (parte inferior de la fila de caracteres 7 en un tercio a la parte superior de la fila de caracteres 0 en el siguiente): reinicia L, y suma 8 a H para pasar al siguiente tercio. Equivalentemente, suma `$0800` a la dirección.

La rutina clásica maneja los tres casos:

```z80 id:ch02_downhl_moving_one_pixel_row
; DOWN_HL: move HL one pixel row down on the Spectrum screen
; Input:  HL = current screen address
; Output: HL = screen address one row below
;
down_hl:
    inc  h             ; 4T   try moving one scan line down
    ld   a, h          ; 4T
    and  7             ; 7T   did we cross a character boundary?
    ret  nz            ; 11/5T  no: done

    ; Crossed a character cell boundary.
    ; Reset scan line to 0, advance character row.
    ld   a, l          ; 4T
    add  a, 32         ; 7T   next character row (L += 32)
    ld   l, a          ; 4T
    ret  c             ; 11/5T  if carry, we crossed into next third

    ; No carry from L, but we need to undo the H increment
    ; that moved us into the wrong third.
    ld   a, h          ; 4T
    sub  8             ; 7T   back up one third in H
    ld   h, a          ; 4T
    ret                ; 10T
```

Esta rutina tarda diferentes cantidades de tiempo dependiendo del caso:

| Caso | Frecuencia | T-states |
|------|-----------|----------|
| Dentro de una celda de caracteres | 7 de cada 8 filas | 4 + 4 + 7 + 11 = **26** |
| Límite de caracteres, mismo tercio | 7 de cada 64 filas | 4 + 4 + 7 + 5 + 4 + 7 + 4 + 5 + 4 + 7 + 4 + 10 = **65** |
| Límite de tercio | 2 de cada 192 filas | 4 + 4 + 7 + 5 + 4 + 7 + 4 + 11 = **46** |

El caso común -- permanecer dentro de una celda de caracteres -- es rápido: 26 T-states (un RET condicional que se activa cuesta 11T, no 5T). El caso poco común (cruzar un límite de fila de caracteres dentro del mismo tercio) es de 65 T-states. Promediado sobre las 192 filas, el coste resulta en aproximadamente **30,5 T-states por llamada**.

Ese promedio oculta un problema. Si estás iterando hacia abajo por toda la pantalla y llamando a DOWN_HL en cada fila, esas llamadas ocasionales de 65 T-states causan picos en la temporización por línea de forma impredecible. Para un efecto de demo que necesita temporización consistente por línea de escaneo, esta fluctuación es inaceptable.

### La optimización de Introspec

En diciembre de 2020, Introspec (spke) publicó un análisis detallado en Hype titulado "Once more about DOWN_HL" (Eshchyo raz pro DOWN_HL). El artículo examinaba el problema de iterar hacia abajo por toda la pantalla de forma eficiente -- no solo el coste de una llamada, sino el coste total de mover HL a través de las 192 filas.

El enfoque ingenuo -- llamar a la rutina clásica DOWN_HL 191 veces -- cuesta **5.825 T-states** para un recorrido de pantalla completa. El objetivo de Introspec era encontrar la forma más rápida de iterar a través de las 192 filas, visitando cada dirección de pantalla en orden de arriba a abajo.

Su idea clave fue usar **contadores divididos**. En lugar de probar los bits de dirección después de cada incremento para detectar cruces de límites, estructuró el bucle para coincidir directamente con la jerarquía de tres niveles de la pantalla:

```text id:ch02_introspec_s_optimisation
For each third (3 iterations):
    For each character row within the third (8 iterations):
        For each scan line within the character cell (8 iterations):
            process this row
            INC H                  ; next scan line
        undo 8 INC H's, ADD 32 to L   ; next character row
    undo 8 ADD 32's, advance to next third
```

La operación más interna es solo `INC H` -- 4 T-states. Sin pruebas, sin saltos. Las transiciones de fila de caracteres y de tercio ocurren en puntos fijos y predecibles del bucle, así que no hay lógica condicional en el bucle interno en absoluto.

El resultado: **2.343 T-states** para un recorrido de pantalla completa. Eso es una mejora del 60% sobre el enfoque clásico, y el coste por línea es absolutamente predecible -- sin fluctuaciones.

También hubo una variación elegante atribuida a RST7, usando un enfoque de contador doble donde el bucle externo mantiene un par de contadores que naturalmente rastrean los límites de fila de caracteres y de tercio. El cuerpo del bucle interno se reduce a un solo `INC H`, y el manejo de límites se integra en la manipulación de contadores en el nivel del bucle externo.

La lección práctica: cuando necesites iterar a través de la pantalla del Spectrum en orden, no llames a una rutina DOWN_HL de propósito general 191 veces. Reestructura tu bucle para coincidir con la jerarquía natural de la pantalla, y los saltos desaparecen.

Aquí tienes una versión simplificada del enfoque de contadores divididos:

```z80 id:ch02_introspec_s_optimisation_2
; Iterate all 192 screen rows using split counters
; HL = $4000 at entry (top-left of screen)
;
iterate_screen:
    ld   hl, $4000          ; 10T  start of screen
    ld   c, 3               ; 7T   3 thirds

.third_loop:
    ld   b, 8               ; 7T   8 character rows per third

.row_loop:
    push hl                 ; 11T  save start of this char row

    ; --- Process 8 scan lines within this character cell ---
    REPT 7
        ; ... your per-row code here, using HL ...
        inc  h              ; 4T   next scan line
    ENDR
    ; ... process the 8th (last) scan line ...

    pop  hl                 ; 10T  restore char row start
    ld   a, l               ; 4T
    add  a, 32              ; 7T   next character row
    ld   l, a               ; 4T

    djnz .row_loop          ; 13T/8T

    ; Advance to next third
    ld   a, h               ; 4T
    add  a, 8               ; 7T   next third ($0800 higher)
    ld   h, a               ; 4T

    dec  c                  ; 4T
    jr   nz, .third_loop    ; 12T/7T
```

La directiva `REPT 7` (soportada por sjasmplus) repite el bloque 7 veces en tiempo de ensamblaje -- un desenrollado parcial. Dentro de ese bloque, moverse una línea de escaneo hacia abajo es un solo `INC H`. Sin pruebas, sin saltos. El avance de fila de caracteres y de tercio ocurre en los límites fijos del bucle externo.

---

## Memoria de atributos: 768 bytes que lo cambiaron todo

Debajo de los datos de píxeles, en `$5800`--`$5AFF`, se encuentra la memoria de atributos. Son 768 bytes -- uno por cada celda de caracteres de 8x8 en la pantalla, organizados secuencialmente de izquierda a derecha, de arriba a abajo. A diferencia del área de píxeles, el diseño de atributos es completamente lineal: la celda (col, fila) está en `$5800 + fila * 32 + col`.

Cada byte de atributos tiene este diseño:

```text
  Bit:   7     6     5  4  3     2  1  0
       +-----+-----+--------+--------+
       |  F  |  B  | PAPER  |  INK   |
       +-----+-----+--------+--------+

  F       = Flash (0 = apagado, 1 = parpadeando a ~1,6 Hz)
  B       = Bright (0 = normal, 1 = brillante)
  PAPER   = Color de fondo (0-7)
  INK     = Color de primer plano (0-7)
```

Los códigos de color de 3 bits se mapean a:

```text
  0 = Negro       4 = Verde
  1 = Azul        5 = Cian
  2 = Rojo        6 = Amarillo
  3 = Magenta     7 = Blanco
```

Con el bit BRIGHT, cada color tiene una variante normal y brillante. El negro sigue siendo negro ya sea brillante o no, así que la paleta total es de 15 colores distintos:

```text
Normal:  Negro  Azul  Rojo  Magenta  Verde  Cian  Amarillo  Blanco
Bright:  Negro  Azul  Rojo  Magenta  Verde  Cian  Amarillo  Blanco
                (versiones más brillantes de cada uno)
```

<!-- figure: ch02_attr_byte -->
![Diseño de bits del byte de atributos mostrando los campos flash, bright, paper e ink](illustrations/output/ch02_attr_byte.png)

Un byte de atributos de `$47` = `01000111`: flash apagado (bit 7 = 0), bright **activado** (bit 6 = 1), paper = 000 (negro), ink = 111 (blanco). Texto blanco brillante sobre fondo negro. La versión sin brillo es `$07` = `00000111` -- el valor predeterminado del Spectrum tras `BORDER 0: PAPER 0: INK 7`.

Este tipo de detalle a nivel de bits importa cuando estás construyendo valores de atributos a velocidad. Un patrón común:

```z80 id:ch02_attribute_memory_768_bytes_4
; Build an attribute byte: bright white ink on blue paper
; Bright = 1, Paper = 001 (blue), Ink = 111 (white)
; = 01 001 111 = $4F
    ld   a, $4F
```

### El conflicto de atributos

Esta es la restricción definitoria del ZX Spectrum: dentro de cada celda de 8x8 píxeles, solo puedes tener **dos colores** -- tinta y papel. Cada píxel activado (1) se muestra en el color de tinta. Cada píxel desactivado (0) se muestra en el color de papel. No puedes tener tres colores, ni degradados, ni color por píxel, dentro de una sola celda.

Esto significa que si un sprite rojo se superpone con un fondo verde, la celda de 8x8 que contiene la superposición debe elegir: todos los píxeles activados en esta celda son rojos o verdes. No puedes tener algunos píxeles rojos y algunos verdes activados en la misma celda. El resultado visual es un bloque discordante de color que "choca" con su entorno -- el infame conflicto de atributos.

```text
Without clash (hypothetical per-pixel colour):

  +---------+---------+
  |  Red    | Red on  |
  |  sprite | green   |
  |  pixels | back-   |
  |         | ground  |
  +---------+---------+

With attribute clash (Spectrum reality):

  +---------+---------+
  |  Red    | Either  |
  |  sprite | ALL red |
  |  pixels | or ALL  |
  |         | green   |
  +---------+---------+

  The overlapping cell cannot have both colours.
```

Muchos juegos tempranos del Spectrum simplemente evitaban el problema: gráficos monocromáticos, o personajes cuidadosamente diseñados para alinearse con la cuadrícula de 8x8. Juegos como Knight Lore y Head Over Heels usaban una sola pareja tinta/papel para toda el área de juego, eliminando el conflicto por completo a costa del color.

Pero la demoscene lo vio de forma diferente. El conflicto de atributos no es solo una limitación -- es una **restricción creativa**. La cuadrícula de 8x8 fuerza una estética particular: bloques audaces de color, patrones geométricos nítidos, uso deliberado del contraste. Los efectos de demo que trabajan enteramente en el espacio de atributos -- túneles, plasmas, scrollers -- pueden actualizar 768 bytes por fotograma en lugar de 6.144, liberando enormes cantidades de presupuesto de fotograma para computación. Cuando toda tu pantalla está dirigida por atributos, el conflicto se vuelve irrelevante porque no estás mezclando sprites con fondos -- los atributos *son* los gráficos.

La demo Eager (2015) de Introspec construyó su lenguaje visual enteramente alrededor de esta idea. El efecto de túnel, el zoomer caótico y la animación de ciclo de color operan todos sobre atributos, no píxeles. El resultado es un efecto que funciona a velocidad completa de fotograma con margen de sobra para tambores digitales y un sofisticado motor de scripts. El conflicto no es un problema porque la restricción fue aceptada desde el principio.

---

## El borde: más que decoración

El área de visualización de 256x192 píxeles se sitúa en el centro de la pantalla, rodeada por un amplio borde. El color del borde se establece escribiendo al puerto `$FE`:

```z80 id:ch02_the_border_more_than
    ld   a, 1          ; 7T   blue = colour 1
    out  ($FE), a       ; 11T  set border colour
```

Solo los bits 0--2 del byte escrito a `$FE` afectan el color del borde. Hay 8 colores (0--7), sin variantes brillantes -- la paleta del borde es el conjunto sin brillo. Los bits 3 y 4 del puerto `$FE` controlan las salidas MIC y EAR (interfaz de cinta y sonido del altavoz), así que debes enmascarar o establecer esos bits apropiadamente si no pretendes hacer ruido.

El cambio de color del borde tiene efecto inmediatamente -- en la misma siguiente línea de escaneo que se está dibujando. Esto es lo que hace al borde tan útil como herramienta de depuración. Como vimos en el Capítulo 1, cambiar el color del borde antes y después de una sección de código crea una franja visible cuya altura revela el coste en T-states del código. El borde es tu osciloscopio.

### Efectos de borde

Dado que los cambios de color del borde son visibles en la siguiente línea de escaneo, las instrucciones `OUT` con temporización precisa pueden crear franjas multicolor, barras ráster e incluso gráficos básicos en el área del borde.

El principio básico: la ULA dibuja una línea de escaneo cada 224 T-states (en Pentagon). Si ejecutas una instrucción `OUT ($FE), A` en el momento correcto, cambias el color del borde en una posición horizontal específica de la línea de escaneo actual. Ejecutando una secuencia rápida de instrucciones `OUT` con diferentes valores de color, puedes pintar franjas horizontales de color en el borde.

```z80 id:ch02_border_effects
; Simple border stripes
; Assumes we are synced to the start of a border scanline

    ld   a, 2          ; 7T   red
    out  ($FE), a       ; 11T
    ; ... delay to fill this scanline ...
    ld   a, 5          ; 7T   cyan
    out  ($FE), a       ; 11T
    ; ... delay to fill next scanline ...
    ld   a, 6          ; 7T   yellow
    out  ($FE), a       ; 11T
```

Los efectos de borde más avanzados pueden crear barras de degradado, texto con desplazamiento, o incluso imágenes de baja resolución. El desafío es extremo: tienes 224 T-states por línea de escaneo, y cada cambio de color cuesta como mínimo 18 T-states (7 para `LD A,n` + 11 para `OUT`). Eso te da aproximadamente 12 cambios de color por línea de escaneo, lo que significa como máximo 12 bandas horizontales de color por línea.

Los programadores de demos han llevado esto a extremos notables. Pre-cargando múltiples registros con valores de color y usando secuencias más rápidas como `OUT (C), A` seguido de intercambios de registros, exprimen más cambios de color por línea. El borde se convierte en una pantalla en sí misma -- un lienzo fuera del lienzo.

Para nuestros propósitos, el papel más importante del borde es el del Capítulo 1: un visualizador de temporización gratuito y siempre disponible. Cuando estés optimizando la rutina de relleno de pantalla más adelante en este capítulo, el borde es cómo verás tu progreso.

---

## Práctica: el relleno de tablero de ajedrez

El ejemplo en `chapters/ch02-screen-as-puzzle/examples/fill_screen.a80` rellena el área de píxeles con un patrón de tablero de ajedrez y los atributos con blanco brillante sobre azul. Recorrámoslo sección por sección.

```z80 id:ch02_practical_the_checkerboard
    ORG $8000

SCREEN  EQU $4000       ; pixel area start
ATTRS   EQU $5800       ; attribute area start
SCRLEN  EQU 6144        ; pixel bytes (256*192/8)
ATTLEN  EQU 768         ; attribute bytes (32*24)
```

El código se coloca en `$8000` -- de forma segura en memoria no contendida en todos los modelos de Spectrum. Las constantes nombran las direcciones y tamaños clave.

```z80 id:ch02_practical_the_checkerboard_2
start:
    ; --- Fill pixels with checkerboard pattern ---
    ld   hl, SCREEN
    ld   de, SCREEN + 1
    ld   bc, SCRLEN - 1
    ld   (hl), $55       ; checkerboard: 01010101
    ldir
```

Esto usa el truco clásico de autocopia con LDIR. Escribe `$55` (binario `01010101`) en el primer byte en `$4000`, luego copia de cada byte al siguiente durante 6.143 bytes. El resultado: cada byte del área de píxeles es `$55`, lo que produce píxeles alternados activados/desactivados -- un tablero de ajedrez. Dado que el patrón es el mismo en cada byte, el orden entrelazado de las filas no importa -- cada fila obtiene el mismo patrón sin importar el orden.

Coste: `LDIR` copia 6.143 bytes. La última iteración cuesta 16T, todas las demás 21T: (6.143 - 1) x 21 + 16 = 128.998 T-states. Casi dos fotogramas completos en un Pentagon. Esto es aceptable para una configuración única, pero nunca harías esto en un bucle de renderizado por fotograma.

```z80 id:ch02_practical_the_checkerboard_3
    ; --- Fill attributes: white ink on blue paper ---
    ; Attribute byte: flash=0, bright=1, paper=001 (blue), ink=111 (white)
    ; = 01 001 111 = $4F
    ld   hl, ATTRS
    ld   de, ATTRS + 1
    ld   bc, ATTLEN - 1
    ld   (hl), $4F
    ldir
```

La misma técnica para los atributos. El valor `$4F` se decodifica como: flash apagado (0), bright activado (1), paper azul (001), ink blanco (111). Cada celda de 8x8 obtiene tinta blanca brillante sobre papel azul. Los píxeles del tablero de ajedrez están activados/desactivados, así que ves puntos alternados blancos y azules -- un patrón visual clásico del ZX Spectrum.

Coste: `LDIR` copia 767 bytes -- (767 - 1) x 21 + 16 = 16.102 T-states.

```z80 id:ch02_practical_the_checkerboard_4
    ; --- Border: blue ---
    ld   a, 1
    out  ($FE), a

    ; Infinite loop
.wait:
    halt
    jr   .wait
```

Establece el borde en azul (color 1) para coincidir con el color del papel, creando un marco visualmente limpio. Luego entra en un bucle infinito, deteniéndose entre fotogramas. El `HALT` espera la siguiente interrupción enmascarable, que se dispara una vez por fotograma -- este es el latido inactivo de todo programa del Spectrum.

![Relleno de pantalla con bytes alternados — patrón de tablero de ajedrez en blanco brillante sobre azul](../../build/screenshots/ch02_fill_screen.png)

### Qué probar

Carga `fill_screen.a80` en tu ensamblador y emulador. Luego experimenta:

- Cambia `$55` a `$AA` para el tablero de ajedrez inverso, o a `$FF` para relleno sólido, o `$81` para barras verticales.
- Cambia `$4F` a `$07` para ver el mismo patrón sin BRIGHT, o a `$38` para papel blanco con tinta negra (el inverso del predeterminado).
- Prueba `$C7` -- eso activa el bit de flash. Observa cómo los caracteres alternan entre colores de tinta y papel a unos 1,6 Hz.
- Reemplaza el relleno de píxeles LDIR con un bucle DOWN_HL que escriba diferentes patrones en diferentes filas. Ahora verás el entrelazado en acción: si escribes `$FF` (sólido) a las filas 0-7 (las líneas de escaneo de la primera celda de caracteres), el área rellenada aparecerá como 8 franjas horizontales brillantes separadas por espacios vacíos -- porque esas filas están a 256 bytes de distancia, no 32.

---

## Navegando la pantalla: un resumen práctico

Aquí están las operaciones esenciales de puntero para la pantalla del Spectrum, recopiladas en un solo lugar. Estos son los bloques de construcción de toda rutina gráfica.

### Moverse un byte a la derecha (8 píxeles)

```z80 id:ch02_moving_right_one_byte_8
    inc  l             ; 4T
```

Esto funciona dentro de una fila de caracteres porque la columna está en los 5 bits bajos de L. Si necesitas cruzar los límites de byte en el borde derecho (columna 31 a columna 0 de la siguiente fila), necesitas el DOWN_HL completo más reinicio de L -- pero típicamente no lo necesitas, porque tus bucles tienen 32 bytes de ancho.

### Moverse una fila de píxeles hacia abajo

```z80 id:ch02_moving_down_one_pixel_row
    inc  h             ; 4T    (within a character cell)
```

Esto funciona para 7 de cada 8 filas. En la 8.a fila, necesitas la lógica completa de cruce de límites de la rutina DOWN_HL anterior.

### Moverse una fila de caracteres hacia abajo (8 píxeles)

```z80 id:ch02_moving_down_one_character_row
    ld   a, l          ; 4T
    add  a, 32         ; 7T
    ld   l, a          ; 4T    total: 15T (if no third crossing)
```

Esto avanza una fila de caracteres dentro de un tercio. Si L desborda (carry activado), has cruzado al siguiente tercio y necesitas sumar 8 a H.

### Moverse una fila de píxeles hacia arriba

```z80 id:ch02_moving_up_one_pixel_row
    dec  h             ; 4T    (within a character cell)
```

El inverso de `INC H`. Los mismos problemas de límites en los bordes de celda de caracteres y de tercio. Aquí está la rutina completa UP_HL, el espejo de DOWN_HL:

```z80 id:ch02_moving_up_one_pixel_row_2
; UP_HL: move HL one pixel row up on the Spectrum screen
; Input:  HL = current screen address
; Output: HL = screen address one row above
;
; Classic version:
up_hl:
    dec  h             ; 4T   try moving one scan line up
    ld   a, h          ; 4T
    and  7             ; 7T   did we cross a character boundary?
    cp   7             ; 7T
    ret  nz            ; 11/5T  no: done

    ; Crossed a character cell boundary upward.
    ld   a, l          ; 4T
    sub  32            ; 7T   previous character row (L -= 32)
    ld   l, a          ; 4T
    ret  c             ; 11/5T  if carry, crossed into prev third

    ld   a, h          ; 4T
    add  a, 8          ; 7T   compensate H
    ld   h, a          ; 4T
    ret                ; 10T
```

Hay una optimización sutil aquí, contribuida por Art-top (Artem Topchiy): reemplazar `and 7 / cp 7` con `cpl / and 7`. Después de `DEC H`, si los 3 bits bajos de H pasaron de `000` a `111`, cruzamos un límite de caracteres. La prueba clásica comprueba `AND 7` y luego compara con 7. La versión optimizada complementa primero: si los bits son `111`, CPL los convierte en `000`, y `AND 7` da cero. Esto ahorra 1 byte y 3 T-states en la ruta de cruce de límites:

```z80 id:ch02_moving_up_one_pixel_row_3
; UP_HL optimised (Art-top)
; Saves 1 byte, 3 T-states on boundary crossing
;
up_hl_opt:
    dec  h             ; 4T
    ld   a, h          ; 4T
    cpl                ; 4T   complement: 111 -> 000
    and  7             ; 7T   zero if we crossed boundary
    ret  nz            ; 11/5T

    ld   a, l          ; 4T
    sub  32            ; 7T
    ld   l, a          ; 4T
    ret  c             ; 11/5T

    ld   a, h          ; 4T
    add  a, 8          ; 7T
    ld   h, a          ; 4T
    ret                ; 10T
```

El mismo truco de `CPL / AND 7` funciona también en DOWN_HL, aunque la condición de límite allí prueba `000` (que CPL convierte en `111`, también distinto de cero después de AND), así que no ayuda yendo hacia abajo. Es específicamente la dirección *hacia arriba* donde el código clásico necesita el `CP 7` extra que la optimización elimina.

### Calcular la dirección de atributo desde una dirección de píxel

Si HL apunta a un byte en el área de píxeles, la dirección de atributo correspondiente puede calcularse. Recuerda la estructura de dirección de píxeles: H = `010TTSSS`, L = `LLLCCCCC`. La dirección de atributo para la misma celda de caracteres es `$5800 + TT * 256 + LLL * 32 + CCCCC`. Dado que L ya codifica `LLL * 32 + CCCCC` (que va de 0 a 255), la dirección de atributo es simplemente `($58 + TT) : L`. Todo lo que necesitamos hacer es extraer los dos bits TT de H, combinarlos con `$58`, y dejar L sin cambiar:

```z80 id:ch02_computing_the_attribute
; Convert pixel address in HL to attribute address in HL
; Input:  HL = pixel address ($4000-$57FF)
; Output: HL = corresponding attribute address ($5800-$5AFF)
;
    ld   a, h          ; 4T
    rrca               ; 4T
    rrca               ; 4T
    rrca               ; 4T
    and  3             ; 7T
    or   $58           ; 7T
    ld   h, a          ; 4T
    ; L unchanged       --- Total: 34T
```

Esto funciona porque L ya contiene `LLL CCCCC` -- la fila de caracteres dentro del tercio (0--7) combinada con la columna (0--31) -- y eso es exactamente el byte bajo de la dirección de atributo. El byte alto solo necesita que el número de tercio se sume a `$58`. Elegante.

**Caso especial: cuando H tiene bits de línea de escaneo = 111.** Si estás iterando a través de una celda de caracteres de arriba a abajo y acabas de procesar la última línea de escaneo (línea de escaneo 7), los 3 bits bajos de H son `111`. En este caso hay una conversión más rápida de 4 instrucciones, contribuida por Art-top:

```z80 id:ch02_computing_the_attribute_2
; Pixel-to-attribute when H low bits are %111
; (e.g., after processing the last scanline of a character cell)
; Input:  HL where H = 010TT111
; Output: HL = attribute address
;
    srl  h             ; 8T   010TT111 -> 0010TT11
    rrc  h             ; 8T   0010TT11 -> 10010TT1
    srl  h             ; 8T   10010TT1 -> 010010TT
    set  4, h          ; 8T   010010TT -> 010110TT = $58+TT
    ; L unchanged.     --- Total: 32T, 4 instructions
```

Esto es 2 T-states más rápido que el método general y evita la secuencia `AND / OR`. La contrapartida es que solo funciona cuando los bits de línea de escaneo son `111` -- pero esa es exactamente la situación después de un bucle de renderizado de celda de caracteres de arriba a abajo, que es uno de los casos de uso más comunes.

---

> **Barra lateral de Agon Light 2**
>
> La pantalla del Agon Light 2 es gestionada por un VDP (Video Display Processor) -- un microcontrolador ESP32 que ejecuta la librería FabGL. La CPU eZ80 se comunica con el VDP a través de un enlace serial, enviando comandos para configurar modos gráficos, dibujar píxeles, definir sprites y gestionar paletas.
>
> No hay diseño de pantalla entrelazado. No hay conflicto de atributos. El VDP soporta múltiples modos bitmap en varias resoluciones (desde 640x480 hasta 320x240 y menores), con 64 colores o paletas RGBA completas dependiendo del modo. Los sprites por hardware (hasta 256) y los mapas de tiles son soportados nativamente.
>
> Lo que cambia para el programador:
>
> - **Sin rompecabezas de direcciones.** Las coordenadas de píxeles se mapean linealmente a posiciones del búfer. No necesitas DOWN_HL ni recorrido de pantalla con contadores divididos.
> - **Sin conflicto de atributos.** Cada píxel puede ser de cualquier color. La restricción de la cuadrícula de 8x8 no existe.
> - **Sin acceso directo de memoria al framebuffer.** La CPU no puede escribir directamente en la memoria de vídeo como la CPU del Spectrum escribe en `$4000`. En su lugar, envías comandos VDP por el enlace serial. Dibujar un píxel significa enviar una secuencia de comandos, no almacenar un byte. Esto introduce latencia -- el enlace serial funciona a 1.152.000 baudios -- pero también significa que la CPU está libre durante el renderizado.
> - **Sin trucos de borde a nivel de ciclo.** El VDP maneja la temporización de pantalla de forma independiente. No puedes crear efectos ráster temporizando instrucciones `OUT`, porque la canalización de pantalla está desacoplada del reloj de la CPU.
>
> Para un programador de Spectrum, el Agon se siente liberador y frustrante a partes iguales. Las restricciones que forzaron soluciones creativas en el Spectrum simplemente no existen -- pero tampoco existen los trucos directos de hardware que esas restricciones habilitaban. Cambias el rompecabezas por una API.

---

## Poniendo todo junto: qué significa el diseño de pantalla para el código

Cada técnica en el resto de este libro está moldeada por el diseño de pantalla descrito en este capítulo. He aquí por qué cada pieza importa:

**El dibujado de sprites** requiere calcular una dirección de pantalla para la posición del sprite, luego iterar hacia abajo a través de las filas del sprite. Cada fila significa `INC H` (7 de cada 8 veces) o el cruce completo de límite de caracteres. Un sprite de 16 píxeles de alto abarca exactamente 2 celdas de caracteres -- cruzarás un límite. Un sprite de 24 píxeles abarca 3 celdas, cruzando 2 límites. El coste de cruce de límites es un impuesto fijo en cada sprite.

**El borrado de pantalla** (Capítulo 3) usa el truco PUSH -- estableciendo SP en `$5800` y empujando datos hacia abajo a través del área de píxeles. El entrelazado no importa para borrar porque cada byte obtiene el mismo valor. Pero para borrados *con patrón* (fondos rayados, rellenos degradados), el entrelazado significa que debes pensar cuidadosamente qué filas obtienen qué datos.

**El desplazamiento** (Capítulo 17) es donde el diseño más perjudica. Desplazar la pantalla hacia arriba un píxel significa mover los 32 bytes de cada fila a la dirección de la fila de arriba. En un framebuffer lineal, esto es una gran copia de bloque. En el Spectrum, las direcciones de origen y destino de cada fila están relacionadas por la lógica de DOWN_HL -- no por un desplazamiento fijo. Una rutina de desplazamiento debe navegar el entrelazado para cada fila que copia.

**Los efectos de atributos** (Capítulos 8--9) son donde el diseño ayuda. Dado que el área de atributos es lineal y pequeña (768 bytes), actualizar colores es rápido. Una actualización de atributos a pantalla completa con LDIR cuesta unos 16.000 T-states -- menos de un cuarto de fotograma. Por eso los efectos basados en atributos (túneles, plasmas, ciclo de color) son un elemento básico del trabajo demoscene del Spectrum.

---

## Resumen

- La pantalla de 6.912 bytes del Spectrum consiste en **6.144 bytes de datos de píxeles** en `$4000`--`$57FF` y **768 bytes de atributos** en `$5800`--`$5AFF`.
- Las filas de píxeles están **entrelazadas** por celda de caracteres: la dirección codifica y como `010 TT SSS` (byte alto) y `LLL CCCCC` (byte bajo), donde los bits de y están repartidos por toda la dirección.
- Moverse **una fila de píxeles hacia abajo** dentro de una celda de caracteres es solo `INC H` (4 T-states). Cruzar límites de caracteres y tercios requiere lógica adicional.
- La rutina clásica **DOWN_HL** maneja todos los casos pero cuesta hasta 65 T-states en los límites. Para iteración de pantalla completa, los **bucles de contadores divididos** (el enfoque de Introspec) reducen el coste total en un 60% y eliminan las fluctuaciones de temporización.
- Cada byte de atributos codifica **Flash, Bright, Paper e Ink** en el formato `FBPPPIII`. Solo **dos colores por celda de 8x8** -- este es el conflicto de atributos.
- El conflicto de atributos no es solo una limitación sino una **restricción creativa** que definió la estética visual del Spectrum y llevó a efectos de demo eficientes basados solo en atributos.
- El color del **borde** se establece con `OUT ($FE), A` (bits 0--2) y los cambios son visibles en la siguiente línea de escaneo, convirtiéndolo en una **herramienta de depuración de temporización** y un lienzo para efectos ráster de la demoscene.
- El **Agon Light 2** no tiene diseño entrelazado, ni conflicto de atributos, ni acceso directo al framebuffer -- reemplaza el rompecabezas con una API de comandos VDP.

---

## Inténtalo tú mismo

1. **Mapea las direcciones.** Elige 10 coordenadas (x, y) aleatorias y calcula la dirección de pantalla a mano usando el diseño de bits `010TTSSS LLLCCCCC`. Luego escribe una pequeña rutina Z80 que trace un solo píxel en cada coordenada y verifica que tus cálculos coincidan.

2. **Visualiza el entrelazado.** Modifica `fill_screen.a80` para escribir diferentes valores en las primeras 8 filas. Escribe `$FF` (sólido) en la fila 0 y `$00` (vacío) en las filas 1--7. Dado que las filas 0--7 están en `$4000`, `$4100`, ..., `$4700`, necesitarás cambiar H para alcanzar cada fila. El resultado debería ser una sola línea brillante en la parte superior, con un espacio de 7 líneas vacías antes de la siguiente línea sólida en la fila 8.

3. **Temporiza DOWN_HL.** Usa el arnés de temporización de color de borde del Capítulo 1. Llama a la rutina clásica DOWN_HL 191 veces (para un recorrido de pantalla completa) y mide la franja. Luego implementa la versión de contadores divididos y compara. La versión de contadores divididos debería producir una franja visiblemente más corta.

4. **Pintor de atributos.** Escribe una rutina que rellene el área de atributos con un degradado: la columna 0 obtiene el color 0, la columna 1 obtiene el color 1, y así sucesivamente (ciclando entre 0--7). Cada fila debería tener el mismo patrón. Luego modifícalo para que cada fila desplace el patrón una posición -- un arcoíris diagonal. Esta es la semilla de un efecto de demo basado en atributos.

5. **Franjas de borde.** Después de un `HALT`, ejecuta un bucle cerrado que cambie el color del borde en cada línea de escaneo durante 64 líneas. Usa los 8 colores de borde en secuencia (0, 1, 2, 3, 4, 5, 6, 7, repetir). Deberías ver franjas horizontales de arcoíris en el borde superior. Ajusta el retardo de temporización entre instrucciones `OUT` hasta que las franjas estén limpias y estables.

---

> **Fuentes:** Introspec "Eshchyo raz pro DOWN_HL" (Hype, 2020); Introspec "GO WEST Part 1" (Hype, 2015) para efectos de memoria contendida en direcciones de pantalla; Introspec "Making of Eager" (Hype, 2015) para diseño de efectos basados en atributos; la documentación de la ULA del Spectrum para la justificación del diseño de memoria; Art-top (comunicación personal, 2026) para el UP_HL optimizado y la conversión rápida de píxel a atributo.

*Siguiente: Capítulo 3 -- La caja de herramientas del demoscener. Bucles desenrollados, código auto-modificable, la pila como conducto de datos, y las técnicas que te permiten hacer lo imposible dentro del presupuesto.*
