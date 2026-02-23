# Capítulo 2: La Pantalla como un Rompecabezas

> "¿Por qué las filas van en ese orden?"
> -- Todo programador de ZX Spectrum, en algún momento

Abre cualquier emulador, escribe `PEEK 16384` y estarás leyendo el primer byte de la pantalla del Spectrum. Pero ¿qué byte es? No es el de la esquina superior izquierda de la pantalla en ningún sentido simple. El píxel en la coordenada (0,0) está ahí, sí -- pero el píxel en (0,1), la siguiente fila hacia abajo, vive a 256 bytes de distancia. El píxel en (0,8), la fila superior de la segunda celda de caracteres, vive a solo 32 bytes del inicio. Y el píxel en (0,64) -- la primera fila del tercio medio de la pantalla -- vive exactamente a 2.048 bytes del inicio, en `$4800`.

Este es el rompecabezas más famoso del Spectrum. El diseño de la memoria de pantalla no es secuencial, no es intuitivo, y no es un accidente. Es una consecuencia de las decisiones de diseño de hardware tomadas en 1982, y da forma a cada pieza de código que toca la pantalla. Comprender este diseño -- y aprender los trucos que hacen rápida la navegación por él -- es fundamental para todo lo que sigue en este libro.

---

## El Mapa de Memoria: 6.912 Bytes de Pantalla

La pantalla del Spectrum ocupa una región fija de memoria:

```
$4000 - $57FF    Datos de píxeles    6.144 bytes   (256 x 192 píxeles, 1 bit por píxel)
$5800 - $5AFF    Atributos             768 bytes   (32 x 24 celdas de color)
```

El área de píxeles contiene el mapa de bits: 256 píxeles de ancho, empaquetados 8 por byte, dando 32 bytes por fila. Con 192 filas, eso son 32 x 192 = 6.144 bytes. Cada byte representa 8 píxeles horizontales, con el bit 7 como el píxel más a la izquierda y el bit 0 como el más a la derecha.

El área de atributos contiene la información de color: un byte por cada celda de caracteres de 8x8. Hay 32 columnas y 24 filas, dando 32 x 24 = 768 bytes.

En total: 6.144 + 768 = 6.912 bytes. Esa es la pantalla completa.

![Diseño de memoria de pantalla del ZX Spectrum con tercios, celdas de caracteres y área de atributos](illustrations/output/ch02_screen_layout.png)

Los datos de píxeles y los datos de atributos sirven para propósitos diferentes pero están estrechamente acoplados. Cada byte de píxeles controla 8 puntos en pantalla; el byte de atributo para la celda 8x8 correspondiente controla en qué color aparecen esos puntos. Cambia el píxel y cambiarás la forma. Cambia el atributo y cambiarás el color. Pero solo puedes cambiar el color para un bloque entero de 8x8 -- no por píxel. Este es el "conflicto de atributos" que define el carácter visual del Spectrum, y volveremos a él en breve.

Primero, el rompecabezas: ¿por qué están desordenadas las filas de píxeles?

---

## El Entrelazado: Dónde Viven las Filas

Si el Spectrum almacenara sus filas de píxeles secuencialmente, la fila 0 estaría en `$4000`, la fila 1 en `$4020`, la fila 2 en `$4040`, y así sucesivamente. Cada fila es de 32 bytes, así que la fila N estaría simplemente en `$4000 + N * 32`. Simple, rápido, sensato.

Eso no es lo que pasa.

La pantalla se divide en tres **tercios**, cada uno de 64 filas de píxeles de alto. Dentro de cada tercio, las filas están entrelazadas por fila de celda de caracteres. Aquí es donde realmente viven las primeras 16 filas:

```
Fila  0:  $4000     Tercio 0, fila de car. 0, línea de escaneo 0
Fila  1:  $4100     Tercio 0, fila de car. 0, línea de escaneo 1
Fila  2:  $4200     Tercio 0, fila de car. 0, línea de escaneo 2
Fila  3:  $4300     Tercio 0, fila de car. 0, línea de escaneo 3
Fila  4:  $4400     Tercio 0, fila de car. 0, línea de escaneo 4
Fila  5:  $4500     Tercio 0, fila de car. 0, línea de escaneo 5
Fila  6:  $4600     Tercio 0, fila de car. 0, línea de escaneo 6
Fila  7:  $4700     Tercio 0, fila de car. 0, línea de escaneo 7
Fila  8:  $4020     Tercio 0, fila de car. 1, línea de escaneo 0
Fila  9:  $4120     Tercio 0, fila de car. 1, línea de escaneo 1
Fila 10:  $4220     Tercio 0, fila de car. 1, línea de escaneo 2
Fila 11:  $4320     Tercio 0, fila de car. 1, línea de escaneo 3
Fila 12:  $4420     Tercio 0, fila de car. 1, línea de escaneo 4
Fila 13:  $4520     Tercio 0, fila de car. 1, línea de escaneo 5
Fila 14:  $4620     Tercio 0, fila de car. 1, línea de escaneo 6
Fila 15:  $4720     Tercio 0, fila de car. 1, línea de escaneo 7
```

Observa el patrón. Las primeras 8 filas son las 8 líneas de escaneo de la fila de caracteres 0 -- pero están a 256 bytes de distancia, no a 32. Dentro de esas 8 filas, el byte alto de la dirección se incrementa en 1 cada vez: `$40`, `$41`, `$42`, ... `$47`. Luego la fila 8 salta a `$4020` -- vuelve a un byte alto de `$40`, pero con el byte bajo avanzado en 32.

Aquí está el panorama completo para el tercio superior de la pantalla:

```
Fila car. 0:   líneas de escaneo en $4000, $4100, $4200, $4300, $4400, $4500, $4600, $4700
Fila car. 1:   líneas de escaneo en $4020, $4120, $4220, $4320, $4420, $4520, $4620, $4720
Fila car. 2:   líneas de escaneo en $4040, $4140, $4240, $4340, $4440, $4540, $4640, $4740
Fila car. 3:   líneas de escaneo en $4060, $4160, $4260, $4360, $4460, $4560, $4660, $4760
Fila car. 4:   líneas de escaneo en $4080, $4180, $4280, $4380, $4480, $4580, $4680, $4780
Fila car. 5:   líneas de escaneo en $40A0, $41A0, $42A0, $43A0, $44A0, $45A0, $46A0, $47A0
Fila car. 6:   líneas de escaneo en $40C0, $41C0, $42C0, $43C0, $44C0, $45C0, $46C0, $47C0
Fila car. 7:   líneas de escaneo en $40E0, $41E0, $42E0, $43E0, $44E0, $45E0, $46E0, $47E0
```

El tercio medio comienza en `$4800` y sigue el mismo patrón. El tercio inferior comienza en `$5000`.

### ¿Por qué?

La razón es la ULA -- el Array de Lógica No Comprometida que genera la señal de vídeo. La ULA lee un byte de datos de píxeles y un byte de datos de atributos por cada celda de caracteres de 8 píxeles que dibuja. Necesita ambos bytes en momentos específicos mientras rastrea la pantalla.

El diseño entrelazado significó que la lógica del contador de direcciones de la ULA podía construirse con menos puertas. Mientras la ULA escanea de izquierda a derecha a través de una fila de caracteres, incrementa los 5 bits bajos de la dirección (la columna). Cuando llega al borde derecho, incrementa el byte alto para moverse a la siguiente línea de escaneo dentro de la misma fila de caracteres. Cuando termina las 8 líneas de escaneo, envuelve el byte alto y avanza los bits de fila del byte bajo.

Esto es elegante desde la perspectiva del hardware. La generación de direcciones de la ULA es una simple combinación de contadores -- sin multiplicación, sin aritmética de direcciones compleja. El enrutamiento del PCB era más simple, el conteo de puertas era menor, y el chip era más barato de fabricar.

El programador paga el precio.

---

## El Diseño de Bits: Decodificando (x, y) en una Dirección

Para entender el entrelazado con precisión, observa cómo la coordenada Y se mapea en la dirección de pantalla de 16 bits. Considera un píxel en la columna `x` (0--255) y fila `y` (0--191). El byte que contiene ese píxel está en:

```
Byte alto:  0 1 0 T T S S S
Byte bajo:  L L L C C C C C
```

Donde:
- `TT` = en qué tercio de la pantalla (0, 1 o 2). Bits 7--6 de y.
- `SSS` = línea de escaneo dentro de la celda de caracteres (0--7). Bits 2--0 de y.
- `LLL` = fila de caracteres dentro del tercio (0--7). Bits 5--3 de y.
- `CCCCC` = columna en bytes (0--31). Esto es x / 8, o equivalentemente bits 7--3 de x.

Lo crucial: los bits de y no están en orden. Los bits 7-6 van a un lugar, los bits 5-3 van a otro, y los bits 2-0 van a otro más. La coordenada y se corta en trozos y se distribuye por toda la dirección.

Visualicemos esto con un ejemplo concreto. Píxel (80, 100):

```
x = 80:     byte de columna = 80 / 8 = 10      CCCCC = 01010
y = 100:    binario = 01100100
            TT  = 01       (tercio 1, el tercio medio)
            LLL = 100      (fila de car. 4 dentro del tercio)
            SSS = 100      (línea de escaneo 4 dentro de la celda)

Byte alto:  0  1  0  0  1  1  0  0  = $4C
Byte bajo:  1  0  0  0  1  0  1  0  = $8A

Dirección: $4C8A
```

El bit dentro de ese byte se determina por los 3 bits bajos de x. El bit 7 es el píxel más a la izquierda, así que la posición del píxel (x AND 7) se mapea al bit 7 - (x AND 7).

### El cálculo de dirección en Z80

Convertir (x, y) a una dirección de pantalla es algo que necesitas hacer rápido y a menudo. Aquí tienes una rutina estándar:

```z80
; Input:  B = y (0-191), C = x (0-255)
; Output: HL = screen address, A = bit mask
;
pixel_addr:
    ld   a, b          ; 4T   A = y
    and  $07           ; 7T   A = SSS (scan line within char)
    or   $40           ; 7T   A = 010 00 SSS (add screen base)
    ld   h, a          ; 4T   H = high byte (partial)

    ld   a, b          ; 4T   A = y again
    rra                ; 4T   \
    rra                ; 4T    | shift bits 5-3 of y
    rra                ; 4T   /  down to bits 2-0
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
                       ; --- Total: ~91 T-states
```

91 T-states no es barato. En un bucle interno apretado procesando miles de píxeles, no llamarías a esta rutina por cada píxel. En cambio, calculas la dirección de inicio una vez y luego navegas la pantalla usando manipulación rápida de punteros -- lo que nos lleva a la rutina más importante en la programación de gráficos del Spectrum.

---

## DOWN_HL: Mover una Fila de Píxeles Hacia Abajo

Tienes un puntero en HL apuntando a algún byte en la pantalla. Quieres moverlo una fila de píxeles hacia abajo -- al byte en la misma columna, una línea de escaneo más abajo. ¿Qué tan difícil puede ser?

En un framebuffer lineal, sumas 32 (el número de bytes por fila). Un `ADD HL, DE` con DE = 32: 11 T-states, listo.

En el Spectrum, es un rompecabezas dentro del rompecabezas. Moverse una fila de píxeles hacia abajo significa:

1. **Dentro de una celda de caracteres** (líneas de escaneo 0--6 a 1--7): incrementar H. Los bits de línea de escaneo están en los 3 bits bajos de H, así que `INC H` te mueve una línea de escaneo hacia abajo.

2. **Cruzando un límite de celda de caracteres** (línea de escaneo 7 a línea de escaneo 0 de la siguiente fila): restablecer los bits de línea de escaneo de H a 0, y sumar 32 a L para moverse a la siguiente fila de caracteres.

3. **Cruzando un límite de tercio** (parte inferior de la fila de car. 7 en un tercio a la parte superior de la fila de car. 0 en el siguiente): restablecer L, y sumar 8 a H para moverse al siguiente tercio. Equivalentemente, sumar `$0800` a la dirección.

La rutina clásica maneja los tres casos:

```z80
; DOWN_HL: move HL one pixel row down on the Spectrum screen
; Input:  HL = current screen address
; Output: HL = screen address one row below
;
down_hl:
    inc  h             ; 4T   try moving one scan line down
    ld   a, h          ; 4T
    and  7             ; 7T   did we cross a character boundary?
    ret  nz            ; 11T  (5T if taken) no: done

    ; Crossed a character cell boundary.
    ; Reset scan line to 0, advance character row.
    ld   a, l          ; 4T
    add  a, 32         ; 7T   next character row (L += 32)
    ld   l, a          ; 4T
    ret  c             ; 11T  (5T if taken) if carry, we crossed into next third

    ; No carry from L, but we need to undo the H increment
    ; that moved us into the wrong third.
    ld   a, h          ; 4T
    sub  8             ; 7T   back up one third in H
    ld   h, a          ; 4T
    ret                ; 10T
```

Esta rutina toma diferentes cantidades de tiempo dependiendo del caso:

| Caso | Frecuencia | T-states |
|------|-----------|----------|
| Dentro de una celda de caracteres | 7 de cada 8 filas | 4 + 4 + 7 + 5 = **20** |
| Límite de caracteres, mismo tercio | 6 de cada 64 filas | 4 + 4 + 7 + 11 + 4 + 7 + 4 + 11 + 4 + 7 + 4 + 10 = **77** |
| Límite de tercio | 2 de cada 192 filas | 4 + 4 + 7 + 11 + 4 + 7 + 4 + 5 = **46** |

El caso común -- permanecer dentro de una celda de caracteres -- es rápido: 20 T-states. Pero el caso infrecuente (cruzar un límite de fila de caracteres dentro del mismo tercio) es lento: 77 T-states. Promediado sobre las 192 filas, el coste resulta en aproximadamente **24,6 T-states por llamada**.

Ese promedio oculta un problema. Si estás iterando hacia abajo por toda la pantalla y llamando a DOWN_HL en cada fila, esas llamadas ocasionales de 77 T-states crean picos impredecibles en tu temporización por línea. Para un efecto de demo que necesita temporización consistente por línea de escaneo, este jitter es inaceptable.

### La Optimización de Introspec

En diciembre de 2020, Introspec (spke) publicó un análisis detallado en Hype titulado "Una vez más sobre DOWN_HL" (Eshchyo raz pro DOWN_HL). El artículo examinó el problema de iterar eficientemente hacia abajo por toda la pantalla -- no solo el coste de una llamada, sino el coste total de mover HL a través de las 192 filas.

El enfoque ingenuo -- llamar a la rutina clásica DOWN_HL 191 veces -- cuesta **5.922 T-states** para un recorrido completo de la pantalla. El objetivo de Introspec era encontrar la forma más rápida de iterar a través de las 192 filas, visitando cada dirección de pantalla en orden de arriba a abajo.

Su perspicacia clave fue usar **contadores divididos**. En lugar de probar los bits de la dirección después de cada incremento para detectar cruces de límites, estructuró el bucle para que coincidiera directamente con la jerarquía de tres niveles de la pantalla:

```
Para cada tercio (3 iteraciones):
    Para cada fila de caracteres dentro del tercio (8 iteraciones):
        Para cada línea de escaneo dentro de la celda (8 iteraciones):
            procesar esta fila
            INC H                  ; siguiente línea de escaneo
        deshacer 8 INC H's, ADD 32 a L   ; siguiente fila de caracteres
    deshacer 8 ADD 32's, avanzar al siguiente tercio
```

La operación más interna es solo `INC H` -- 4 T-states. Sin pruebas, sin ramificaciones. Las transiciones de fila de caracteres y de tercio ocurren en puntos fijos y predecibles del bucle, así que no hay lógica condicional en el bucle interno en absoluto.

El resultado: **2.343 T-states** para un recorrido completo de la pantalla. Eso es una mejora del 60% respecto al enfoque clásico, y el coste por línea es absolutamente predecible -- sin jitter.

También había una variación elegante atribuida a RST7, usando un enfoque de doble contador donde el bucle externo mantiene un par de contadores que naturalmente rastrean los límites de fila de caracteres y de tercio. El cuerpo del bucle interno se reduce a un solo `INC H`, y el manejo de límites se integra en la manipulación de contadores a nivel del bucle externo.

La lección práctica: cuando necesites iterar a través de la pantalla del Spectrum en orden, no llames a una rutina DOWN_HL de propósito general 191 veces. Reestructura tu bucle para que coincida con la jerarquía natural de la pantalla, y las ramificaciones desaparecen.

Aquí tienes una versión simplificada del enfoque de contadores divididos:

```z80
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

La directiva `REPT 7` (soportada por sjasmplus) repite el bloque 7 veces en tiempo de ensamblado -- un desenrollado parcial. Dentro de ese bloque, moverse una línea de escaneo hacia abajo es un solo `INC H`. Sin pruebas, sin ramificaciones. El avance de fila de caracteres y el avance de tercio ocurren en los límites fijos del bucle externo.

---

## Memoria de Atributos: 768 Bytes Que lo Cambiaron Todo

Debajo de los datos de píxeles, en `$5800`--`$5AFF`, se encuentra la memoria de atributos. Son 768 bytes -- uno por cada celda de caracteres de 8x8 en la pantalla, dispuestos secuencialmente de izquierda a derecha, de arriba a abajo. A diferencia del área de píxeles, el diseño de atributos es completamente lineal: la celda (col, fila) está en `$5800 + fila * 32 + col`.

Cada byte de atributo tiene este diseño:

```
  Bit:   7     6     5  4  3     2  1  0
       +-----+-----+--------+--------+
       |  F  |  B  | PAPER  |  INK   |
       +-----+-----+--------+--------+

  F       = Flash (0 = apagado, 1 = parpadeo a ~1,6 Hz)
  B       = Bright (0 = normal, 1 = brillante)
  PAPER   = Color de fondo (0-7)
  INK     = Color de primer plano (0-7)
```

Los códigos de color de 3 bits se mapean a:

```
  0 = Negro       4 = Verde
  1 = Azul        5 = Cian
  2 = Rojo        6 = Amarillo
  3 = Magenta     7 = Blanco
```

Con el bit BRIGHT, cada color tiene una variante normal y brillante. El negro permanece negro sea brillante o no, así que la paleta total es de 15 colores distintos:

```
Normal:    Negro  Azul  Rojo  Magenta  Verde  Cian  Amarillo  Blanco
Brillante: Negro  Azul  Rojo  Magenta  Verde  Cian  Amarillo  Blanco
                  (versiones más brillantes de cada uno)
```

![Diseño de bits del byte de atributo mostrando campos de flash, bright, paper e ink](illustrations/output/ch02_attr_byte.png)

Un byte de atributo de `$47` significa: flash apagado, bright apagado, paper = 0 (negro), ink = 7 (blanco). Texto blanco sobre fondo negro -- el valor por defecto del Spectrum. La versión brillante sería `$C7`: `$47` OR `$40` establece el bit bright.

Espera -- eso es incorrecto. Releamos el diseño de bits. El bit 6 es bright, así que blanco brillante sobre negro es `$47` con el bit 6 establecido: `$47 | $40 = $47`. No, `$47` ya es `01000111`. El bit 7 es flash, el bit 6 es bright. Entonces `$47` = flash apagado, bright **encendido**, paper 000, ink 111 = blanco brillante sobre negro. La versión no brillante sería `$07`.

Este tipo de detalle a nivel de bits importa cuando estás construyendo valores de atributos a velocidad. Un patrón común:

```z80
; Build an attribute byte: bright white ink on blue paper
; Bright = 1, Paper = 001 (blue), Ink = 111 (white)
; = 01 001 111 = $4F
    ld   a, $4F
```

### El Conflicto de Atributos

Aquí está la restricción que define al ZX Spectrum: dentro de cada celda de píxeles de 8x8, solo puedes tener **dos colores** -- ink y paper. Cada píxel activado (1) se muestra en el color ink. Cada píxel desactivado (0) se muestra en el color paper. No puedes tener tres colores, ni gradientes, ni coloración por píxel, dentro de una sola celda.

Esto significa que si un sprite rojo se superpone con un fondo verde, la celda de 8x8 que contiene la superposición debe elegir: todos los píxeles activados en esta celda son o rojos o verdes. No puedes tener algunos píxeles activados rojos y algunos verdes en la misma celda. El resultado visual es un bloque discordante de color que "choca" con su entorno -- el infame conflicto de atributos.

```
Sin conflicto (hipotético color por píxel):

  +---------+---------+
  |  Sprite | Rojo    |
  |  rojo   | sobre   |
  |  píxeles| fondo   |
  |         | verde   |
  +---------+---------+

Con conflicto de atributos (realidad del Spectrum):

  +---------+---------+
  |  Sprite | TODO    |
  |  rojo   | rojo    |
  |  píxeles| o TODO  |
  |         | verde   |
  +---------+---------+

  La celda superpuesta no puede tener ambos colores.
```

Muchos juegos tempranos del Spectrum simplemente evitaron el problema: gráficos monocromáticos, o personajes cuidadosamente diseñados para alinearse con la cuadrícula de 8x8. Juegos como Knight Lore y Head Over Heels usaban un solo par ink/paper para toda el área de juego, eliminando el conflicto por completo a costa del color.

Pero la demoscene lo vio de manera diferente. El conflicto de atributos no es solo una limitación -- es una **restricción creativa**. La cuadrícula de 8x8 impone una estética particular: bloques audaces de color, patrones geométricos nítidos, uso deliberado del contraste. Los efectos de demo que trabajan enteramente en el espacio de atributos -- túneles, plasmas, scrollers -- pueden actualizar 768 bytes por fotograma en vez de 6.144, liberando enormes cantidades de presupuesto de ciclos para computación. Cuando toda tu pantalla está basada en atributos, el conflicto se vuelve irrelevante porque no estás mezclando sprites con fondos -- los atributos *son* los gráficos.

La demo Eager de Introspec (2015) construyó su lenguaje visual enteramente alrededor de esta perspicacia. El efecto de túnel, el chaos zoomer y la animación de ciclo de colores todos operan sobre atributos, no píxeles. El resultado es un efecto que corre a velocidad completa de fotograma con espacio de sobra para tambores digitales y un motor de scripting sofisticado. El conflicto no es un problema porque la restricción fue abrazada desde el inicio.

---

## El Borde: Más que Decoración

El área de pantalla de 256x192 píxeles se encuentra en el centro de la pantalla, rodeada por un borde ancho. El color del borde se establece escribiendo en el puerto `$FE`:

```z80
    ld   a, 1          ; 7T   blue = colour 1
    out  ($FE), a       ; 11T  set border colour
```

Solo los bits 0--2 del byte escrito en `$FE` afectan el color del borde. Hay 8 colores (0--7), sin variantes brillantes -- la paleta del borde es el conjunto no brillante. Los bits 3 y 4 del puerto `$FE` controlan las salidas MIC y EAR (interfaz de cinta y sonido del beeper), así que debes enmascarar o establecer esos bits apropiadamente si no pretendes hacer ruido.

El cambio de color del borde tiene efecto inmediatamente -- en la siguiente línea de escaneo que se está dibujando. Esto es lo que hace al borde tan útil como herramienta de depuración. Como vimos en el Capítulo 1, cambiar el color del borde antes y después de una sección de código crea una franja visible cuya altura revela el coste en T-states del código. El borde es tu osciloscopio.

### Efectos de Borde

Debido a que los cambios de color del borde son visibles en la siguiente línea de escaneo, instrucciones `OUT` precisamente temporizadas pueden crear franjas multicolor, barras raster e incluso gráficos primitivos en el área del borde.

El principio básico: la ULA dibuja una línea de escaneo cada 224 T-states (en Pentagon). Si ejecutas una instrucción `OUT ($FE), A` en el momento correcto, cambias el color del borde en una posición horizontal específica de la línea de escaneo actual. Ejecutando una secuencia rápida de instrucciones `OUT` con diferentes valores de color, puedes pintar franjas horizontales de color en el borde.

```z80
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

Los efectos de borde más avanzados pueden crear barras de gradiente, texto desplazable, o incluso imágenes de baja resolución. El desafío es extremo: tienes 224 T-states por línea de escaneo, y cada cambio de color cuesta como mínimo 18 T-states (7 para `LD A,n` + 11 para `OUT`). Eso te da aproximadamente 12 cambios de color por línea de escaneo, lo que significa como máximo 12 bandas de color horizontales por línea.

Los programadores de demos han llevado esto a extremos notables. Pre-cargando múltiples registros con valores de color y usando secuencias más rápidas como `OUT (C), A` seguido de intercambios de registros, exprimen más cambios de color por línea. El borde se convierte en una pantalla en sí misma -- un lienzo fuera del lienzo.

Para nuestros propósitos, el papel más importante del borde es el del Capítulo 1: un visualizador de temporización gratuito y siempre disponible. Cuando estés optimizando la rutina de llenado de pantalla más adelante en este capítulo, el borde es cómo verás tu progreso.

---

## Práctica: El Llenado de Tablero de Ajedrez

El ejemplo en `chapters/ch02-screen-as-puzzle/examples/fill_screen.a80` llena el área de píxeles con un patrón de tablero de ajedrez y los atributos con blanco brillante sobre azul. Recorrámoslo sección por sección.

```z80
    ORG $8000

SCREEN  EQU $4000       ; pixel area start
ATTRS   EQU $5800       ; attribute area start
SCRLEN  EQU 6144        ; pixel bytes (256*192/8)
ATTLEN  EQU 768         ; attribute bytes (32*24)
```

El código se coloca en `$8000` -- de forma segura en memoria no contendida en todos los modelos de Spectrum. Las constantes nombran las direcciones y tamaños clave.

```z80
start:
    ; --- Fill pixels with checkerboard pattern ---
    ld   hl, SCREEN
    ld   de, SCREEN + 1
    ld   bc, SCRLEN - 1
    ld   (hl), $55       ; checkerboard: 01010101
    ldir
```

Esto usa el truco clásico de auto-copia LDIR. Escribe `$55` (binario `01010101`) en el primer byte en `$4000`, luego copia de cada byte al siguiente durante 6.143 bytes. El resultado: cada byte del área de píxeles es `$55`, lo que produce píxeles alternados activados/desactivados -- un tablero de ajedrez. Como el patrón es el mismo en cada byte, el orden entrelazado de las filas no importa -- cada fila obtiene el mismo patrón independientemente.

Coste: `LDIR` a 21 T-states por byte x 6.143 + 16 para el último byte = 129.019 T-states. Casi dos fotogramas completos en un Pentagon. Esto está bien para una configuración única, pero nunca harías esto en un bucle de renderizado por fotograma.

```z80
    ; --- Fill attributes: white ink on blue paper ---
    ; Attribute byte: flash=0, bright=1, paper=001 (blue), ink=111 (white)
    ; = 01 001 111 = $4F
    ld   hl, ATTRS
    ld   de, ATTRS + 1
    ld   bc, ATTLEN - 1
    ld   (hl), $4F
    ldir
```

La misma técnica para los atributos. El valor `$4F` se decodifica como: flash apagado (0), bright encendido (1), paper azul (001), ink blanco (111). Cada celda de 8x8 obtiene ink blanco brillante sobre paper azul. Los píxeles del tablero de ajedrez están activados/desactivados, así que ves puntos alternados blancos y azules -- un patrón visual clásico del ZX Spectrum.

Coste: 768 bytes x 21 + último byte a 16 = 16.143 T-states.

```z80
    ; --- Border: blue ---
    ld   a, 1
    out  ($FE), a

    ; Infinite loop
.wait:
    halt
    jr   .wait
```

Establece el borde en azul (color 1) para que coincida con el color paper, creando un marco visualmente limpio. Luego entra en bucle infinito, deteniendo entre fotogramas. El `HALT` espera la siguiente interrupción enmascarable, que se dispara una vez por fotograma -- este es el latido inactivo de todo programa de Spectrum.

### Qué probar

Carga `fill_screen.a80` en tu ensamblador y emulador. Luego experimenta:

- Cambia `$55` a `$AA` para el tablero de ajedrez inverso, o a `$FF` para relleno sólido, o `$81` para barras verticales.
- Cambia `$4F` a `$07` para ver el mismo patrón sin BRIGHT, o a `$38` para paper blanco con ink negro (el inverso del predeterminado).
- Prueba `$C7` -- eso establece el bit de flash. Observa los caracteres alternando entre colores ink y paper a aproximadamente 1,6 Hz.
- Reemplaza el llenado de píxeles LDIR con un bucle DOWN_HL que escriba diferentes patrones en diferentes filas. Ahora verás el entrelazado en acción: si escribes `$FF` en las filas 0-7 (las líneas de escaneo de la primera celda de caracteres), el área llenada aparecerá como 8 franjas horizontales separadas por espacios -- porque esas filas están a 256 bytes de distancia, no a 32.

---

## Navegando la Pantalla: Un Resumen Práctico

Aquí están las operaciones esenciales de punteros para la pantalla del Spectrum, recopiladas en un solo lugar. Estos son los bloques de construcción de toda rutina gráfica.

### Moverse a la derecha un byte (8 píxeles)

```z80
    inc  l             ; 4T
```

Esto funciona dentro de una fila de caracteres porque la columna está en los 5 bits bajos de L. Si necesitas cruzar límites de bytes en el borde derecho (columna 31 a columna 0 de la siguiente fila), necesitas el DOWN_HL completo más reinicio de L -- pero típicamente no lo necesitas, porque tus bucles son de 32 bytes de ancho.

### Moverse una fila de píxeles hacia abajo

```z80
    inc  h             ; 4T    (within a character cell)
```

Esto funciona para 7 de cada 8 filas. En la octava fila, necesitas la lógica completa de cruce de límites de la rutina DOWN_HL anterior.

### Moverse una fila de caracteres hacia abajo (8 píxeles)

```z80
    ld   a, l          ; 4T
    add  a, 32         ; 7T
    ld   l, a          ; 4T    total: 15T (if no third crossing)
```

Esto avanza una fila de caracteres dentro de un tercio. Si L desborda (carry activado), has cruzado al siguiente tercio y necesitas sumar 8 a H.

### Moverse una fila de píxeles hacia arriba

```z80
    dec  h             ; 4T    (within a character cell)
```

El inverso de `INC H`. Los mismos problemas de límites en los límites de celda de caracteres y de tercio. Aquí está la rutina completa UP_HL, el espejo de DOWN_HL:

```z80
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
    ret  nz            ; 11T  (5T if taken) no: done

    ; Crossed a character cell boundary upward.
    ld   a, l          ; 4T
    sub  32            ; 7T   previous character row (L -= 32)
    ld   l, a          ; 4T
    ret  c             ; 11T  (5T if taken) if carry, crossed into prev third

    ld   a, h          ; 4T
    add  a, 8          ; 7T   compensate H
    ld   h, a          ; 4T
    ret                ; 10T
```

Hay una optimización sutil aquí, contribuida por Artem Topchiy: reemplazar `and 7 / cp 7` con `cpl / and 7`. Después de `DEC H`, si los 3 bits bajos de H pasaron de `000` a `111`, cruzamos un límite de caracteres. La prueba clásica verifica `AND 7` luego compara con 7. La versión optimizada complementa primero: si los bits son `111`, CPL los convierte en `000`, y `AND 7` da cero. Esto ahorra 1 byte y 3 T-states en la ruta de cruce de límites:

```z80
; UP_HL optimised (Artem Topchiy)
; Saves 1 byte, 3 T-states on boundary crossing
;
up_hl_opt:
    dec  h             ; 4T
    ld   a, h          ; 4T
    cpl                ; 4T   complement: 111 -> 000
    and  7             ; 7T   zero if we crossed boundary
    ret  nz            ; 11T  (5T if taken)

    ld   a, l          ; 4T
    sub  32            ; 7T
    ld   l, a          ; 4T
    ret  c             ; 11T  (5T if taken)

    ld   a, h          ; 4T
    add  a, 8          ; 7T
    ld   h, a          ; 4T
    ret                ; 10T
```

El mismo truco `CPL / AND 7` funciona en DOWN_HL también, aunque la condición de límite allí prueba `000` (que CPL convierte en `111`, también distinto de cero después de AND), así que no ayuda yendo hacia abajo. Es específicamente la dirección *hacia arriba* donde el código clásico necesita el `CP 7` extra que la optimización elimina.

### Calcular la dirección de atributo desde una dirección de píxel

Si HL apunta a un byte en el área de píxeles, la dirección de atributo correspondiente se puede calcular:

```z80
; Input:  HL = pixel address ($4000-$57FF)
; Output: HL = attribute address ($5800-$5AFF)
;
pixel_to_attr:
    ld   a, h          ; 4T
    rrca               ; 4T   \
    rrca               ; 4T    | shift bits 5-3 of H (TT, top LLL bit)
    rrca               ; 4T   /  down to bits 2-0
    and  3             ; 7T   keep only the third bits
    or   $58           ; 7T   add attribute base
    ld   h, a          ; 4T
                       ; L is already correct (column + char row)
    ; Total: ~34 T-states
```

Espera -- eso no es del todo correcto. La dirección de píxel tiene la estructura `010 TT SSS` en H y `LLL CCCCC` en L. La dirección de atributo necesita `01011 TT L` en H y `LL CCCCC` en L. En realidad, la dirección de atributo es simplemente `$5800 + (tercio * 256) + (fila_car * 32) + columna`. Permíteme rehacer esto correctamente.

El atributo para la celda de caracteres en columna C, fila R (donde R = 0--23) está en `$5800 + R * 32 + C`. Dada una dirección de píxel en HL, necesitamos extraer la fila de caracteres (0--23) y la columna (0--31). La fila de caracteres es `tercio * 8 + fila_car_dentro_del_tercio`:

```z80
; Input:  HL = pixel address ($4000-$57FF)
; Output: DE = attribute address ($5800-$5AFF)
;         Preserves HL
;
pixel_to_attr:
    ld   a, h          ; 4T   H = 010 TT SSS
    and  $18           ; 7T   mask TT bits -> 000 TT 000
    rrca               ; 4T   \
    rrca               ; 4T    | shift to get 00000 TT 0
    rrca               ; 4T   /
    or   $58           ; 7T   add $58 -> 01011 TT 0  (almost)
    ; Hmm, we also need LLL from L.
```

En la práctica, la formulación exacta depende de lo que necesites. El enfoque más simple usa el hecho de que el área de atributos es lineal:

```z80
; Pixel address HL -> attribute address HL
; H = 010 TT SSS, L = LLL CCCCC
;
; Attribute H should be: 0101 1 TT L(bit 7)
; Attribute L should be: LL CCCCC
;
; Discard SSS entirely (scan line is irrelevant for attributes).

    ld   a, h          ; 4T
    rra                ; 4T
    rra                ; 4T
    rra                ; 4T   A = scan(2:0) 010 TT => SSS 010 TT
    and  $03           ; 7T   A = 000000 TT
    or   $58           ; 7T   A = 01011 0 TT
    ld   h, a          ; 4T

    ld   a, l          ; 4T
    rra                ; 4T
    rra                ; 4T
    rra                ; 4T   rotate LLL CCCCC => CCC CCLLL
    ; That's not right either.
```

Permíteme dar la versión estándar bien conocida en lugar de derivarla incorrectamente:

```z80
; Convert pixel address in HL to attribute address in HL
; Standard method
;
    ld   a, h          ; 4T   H = 010TTSSS
    rrca               ; 4T   \
    rrca               ; 4T    | rotate right 3 times
    rrca               ; 4T   /  A = SSS010TT
    and  $03           ; 7T   A = 000000TT
    or   $58           ; 7T   A = 010110TT
    ld   h, a          ; 4T   H now has the third

    ; L = LLLCCCCC -- already contains char row (LLL) and column (CCCCC)
    ; But we need to combine with TT from H.
    ; Actually, the attribute address is $5800 + TT*$100 + L
    ; Wait -- there are only 256 bytes per third in attributes,
    ; and L already encodes LLL*32 + CCCCC, which ranges 0-255.
    ; So the attribute address is simply ($58 + TT) : L.
    ; But TT goes 0,1,2 and attributes go $5800, $5900, $5A00.
    ; So H = $58 | TT is wrong -- it should be $58 + TT.
    ; $58 + 0 = $58, $58 + 1 = $59, $58 + 2 = $5A. That works.
    ; And OR with $58 when TT is in bits 0-1 gives:
    ;   $58 | 0 = $58, $58 | 1 = $59, $58 | 2 = $5A. Correct!

    ; L stays unchanged. Done.
    ; Total: 34 T-states
```

Así que la versión final limpia es:

```z80
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

Esto funciona porque L ya contiene `LLL CCCCC` -- la fila de caracteres dentro del tercio (0--7) combinada con la columna (0--31) -- y eso es exactamente el byte bajo de la dirección de atributo. El byte alto solo necesita el número de tercio sumado a `$58`. Elegante.

**Caso especial: cuando H tiene bits de línea de escaneo = 111.** Si estás iterando a través de una celda de caracteres de arriba a abajo y acabas de procesar la última línea de escaneo (línea de escaneo 7), los 3 bits bajos de H son `111`. En este caso hay una conversión más rápida de 4 instrucciones, contribuida por Artem Topchiy:

```z80
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

Esto es 2 T-states más rápido que el método general y evita la secuencia `AND / OR`. La compensación es que solo funciona cuando los bits de línea de escaneo son `111` -- pero esa es exactamente la situación después de un bucle de renderizado de celda de caracteres de arriba a abajo, que es uno de los casos de uso más comunes.

---

> **Recuadro Agon Light 2**
>
> La pantalla del Agon Light 2 es gestionada por un VDP (Video Display Processor) -- un microcontrolador ESP32 ejecutando la librería FabGL. La CPU eZ80 se comunica con el VDP a través de un enlace serial, enviando comandos para establecer modos gráficos, dibujar píxeles, definir sprites y gestionar paletas.
>
> No hay diseño de memoria entrelazado. No hay conflicto de atributos. El VDP soporta múltiples modos de mapa de bits a varias resoluciones (desde 640x480 hasta 320x240 y menores), con 64 colores o paletas RGBA completas dependiendo del modo. Los sprites por hardware (hasta 256) y mapas de tiles son soportados nativamente.
>
> Lo que cambia para el programador:
>
> - **Sin rompecabezas de direcciones.** Las coordenadas de píxeles se mapean linealmente a posiciones del búfer. No necesitas DOWN_HL ni recorrido de pantalla con contadores divididos.
> - **Sin conflicto de atributos.** Cada píxel puede ser de cualquier color. La restricción de cuadrícula 8x8 no existe.
> - **Sin acceso directo a memoria del framebuffer.** La CPU no puede escribir directamente a la memoria de vídeo como la CPU del Spectrum escribe en `$4000`. En cambio, envías comandos VDP a través del enlace serial. Dibujar un píxel significa enviar una secuencia de comandos, no almacenar un byte. Esto introduce latencia -- el enlace serial funciona a 1.152.000 baudios -- pero también significa que la CPU está libre durante el renderizado.
> - **Sin trucos de borde a nivel de ciclo.** El VDP maneja la temporización de pantalla de forma independiente. No puedes crear efectos raster temporizando instrucciones `OUT`, porque el pipeline de pantalla está desacoplado del reloj de la CPU.
>
> Para un programador de Spectrum, el Agon se siente liberador y frustrante a partes iguales. Las restricciones que forzaron soluciones creativas en el Spectrum simplemente no existen -- pero tampoco los trucos directos de hardware que esas restricciones habilitaban. Cambias el rompecabezas por una API.

---

## Poniéndolo Todo Junto: Lo Que el Diseño de Pantalla Significa para el Código

Cada técnica en el resto de este libro está moldeada por el diseño de pantalla descrito en este capítulo. Aquí está por qué cada pieza importa:

**El dibujo de sprites** requiere calcular una dirección de pantalla para la posición del sprite, luego iterar hacia abajo a través de las filas del sprite. Cada fila significa `INC H` (7 de cada 8 veces) o el cruce completo de límite de caracteres. Un sprite de 16 píxeles de alto abarca exactamente 2 celdas de caracteres -- cruzarás un límite. Un sprite de 24 píxeles abarca 3 celdas, cruzando 2 límites. El coste del cruce de límites es un impuesto fijo sobre cada sprite.

**El borrado de pantalla** (Capítulo 3) usa el truco PUSH -- estableciendo SP en `$5800` y empujando datos hacia abajo a través del área de píxeles. El entrelazado no importa para el borrado porque cada byte obtiene el mismo valor. Pero para borrados *con patrón* (fondos rayados, rellenos de gradiente), el entrelazado significa que debes pensar cuidadosamente sobre qué filas obtienen qué datos.

**El desplazamiento** (Capítulo 17) es donde el diseño más duele. Desplazar la pantalla hacia arriba un píxel significa mover los 32 bytes de cada fila a la dirección de la fila de arriba. En un framebuffer lineal, esto es una gran copia de bloque. En el Spectrum, las direcciones de origen y destino para cada fila están relacionadas por la lógica DOWN_HL -- no por un desplazamiento fijo. Una rutina de desplazamiento debe navegar el entrelazado para cada fila que copia.

**Los efectos de atributos** (Capítulos 8--9) son donde el diseño ayuda. Como el área de atributos es lineal y pequeña (768 bytes), actualizar colores es rápido. Una actualización de atributos de pantalla completa con LDIR cuesta aproximadamente 16.000 T-states -- menos de un cuarto de fotograma. Por eso los efectos basados en atributos (túneles, plasmas, ciclo de colores) son un pilar del trabajo de demoscene del Spectrum.

---

## Resumen

- La pantalla de 6.912 bytes del Spectrum consiste en **6.144 bytes de datos de píxeles** en `$4000`--`$57FF` y **768 bytes de atributos** en `$5800`--`$5AFF`.
- Las filas de píxeles están **entrelazadas** por celda de caracteres: la dirección codifica y como `010 TT SSS` (byte alto) y `LLL CCCCC` (byte bajo), donde los bits de y se mezclan a través de la dirección.
- Moverse **una fila de píxeles hacia abajo** dentro de una celda de caracteres es solo `INC H` (4 T-states). Cruzar límites de caracteres y de tercios requiere lógica adicional.
- La rutina clásica **DOWN_HL** maneja todos los casos pero cuesta hasta 77 T-states en los límites. Para iteración de pantalla completa, los **bucles con contadores divididos** (enfoque de Introspec) reducen el coste total en un 60% y eliminan el jitter de temporización.
- Cada byte de atributo codifica **Flash, Bright, Paper e Ink** en el formato `FBPPPIII`. Solo **dos colores por celda de 8x8** -- esto es el conflicto de atributos.
- El conflicto de atributos no es solo una limitación sino una **restricción creativa** que definió la estética visual del Spectrum y llevó a efectos de demo eficientes basados solo en atributos.
- El color del **borde** se establece con `OUT ($FE), A` (bits 0--2) y los cambios son visibles en la siguiente línea de escaneo, convirtiéndolo en una **herramienta de depuración de temporización** y un lienzo para efectos raster de la demoscene.
- El **Agon Light 2** no tiene diseño entrelazado, ni conflicto de atributos, ni acceso directo al framebuffer -- reemplaza el rompecabezas con una API de comandos VDP.

---

## Inténtalo Tú Mismo

1. **Mapea las direcciones.** Elige 10 coordenadas (x, y) aleatorias y calcula la dirección de pantalla a mano usando el diseño de bits `010TTSSS LLLCCCCC`. Luego escribe una pequeña rutina Z80 que dibuje un solo píxel en cada coordenada y verifica que tus cálculos coincidan.

2. **Visualiza el entrelazado.** Modifica `fill_screen.a80` para escribir diferentes valores en las primeras 8 filas. Escribe `$FF` (sólido) en la fila 0 y `$00` (vacío) en las filas 1--7. Como las filas 0--7 están en `$4000`, `$4100`, ..., `$4700`, necesitarás cambiar H para alcanzar cada fila. El resultado debería ser una sola línea brillante en la parte superior, con un espacio de 7 líneas vacías antes de la siguiente línea sólida en la fila 8.

3. **Mide DOWN_HL.** Usa la arnés de temporización de color de borde del Capítulo 1. Llama a la rutina clásica DOWN_HL 191 veces (para un recorrido completo de pantalla) y mide la franja. Luego implementa la versión con contadores divididos y compara. La versión con contadores divididos debería producir una franja visiblemente más corta.

4. **Pintor de atributos.** Escribe una rutina que llene el área de atributos con un gradiente: la columna 0 obtiene el color 0, la columna 1 obtiene el color 1, y así sucesivamente (ciclando del 0 al 7). Cada fila debería tener el mismo patrón. Luego modifícalo para que cada fila desplace el patrón una posición -- un arcoíris diagonal. Esta es la semilla de un efecto de demo basado en atributos.

5. **Franjas de borde.** Después de un `HALT`, ejecuta un bucle cerrado que cambie el color del borde en cada línea de escaneo durante 64 líneas. Usa los 8 colores de borde en secuencia (0, 1, 2, 3, 4, 5, 6, 7, repetir). Deberías ver franjas de arcoíris horizontales en el borde superior. Ajusta el retardo de temporización entre instrucciones `OUT` hasta que las franjas estén limpias y estables.

---

> **Fuentes:** Introspec "Eshchyo raz pro DOWN_HL" (Hype, 2020); Introspec "GO WEST Part 1" (Hype, 2015) para efectos de memoria contendida en direcciones de pantalla; Introspec "Making of Eager" (Hype, 2015) para diseño de efectos basados en atributos; la documentación de la ULA del Spectrum para la justificación del diseño de memoria; Artem Topchiy (comunicación personal, 2026) para el UP_HL optimizado y la conversión rápida de píxel a atributo.

*Siguiente: Capítulo 3 -- La Caja de Herramientas del Demoscener. Bucles desenrollados, código auto-modificable, la pila como tubería de datos, y las técnicas que te permiten hacer lo imposible dentro del presupuesto.*
