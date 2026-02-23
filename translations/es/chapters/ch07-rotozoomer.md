# Capítulo 7: Rotozoomer y Píxeles Chunky

> *"El truco es que no rotas la pantalla. Rotas tu recorrido a través de la textura."*
> -- parafraseando la idea central detrás de todo rotozoomer jamás escrito

---

Hay un momento en Illusion donde la pantalla se llena con un patrón -- una textura, monocromática, que se repite -- y entonces comienza a girar. La rotación es suave y continua, el zoom respira hacia adentro y hacia afuera, y todo funciona a un ritmo que te hace olvidar que estás viendo un Z80 empujando píxeles a 3,5 MHz. No es el efecto técnicamente más exigente de la demo. La esfera (Capítulo 6) es más difícil matemáticamente. El dotfield scroller (Capítulo 10) es más ajustado en su presupuesto de ciclos. Pero el rotozoomer es el que parece sin esfuerzo, y en el Spectrum, hacer que algo parezca sin esfuerzo es el truco más difícil de todos.

Este capítulo traza dos hilos. El primero es el análisis de Introspec de 2017 del rotozoomer de Illusion por X-Trade. El segundo es el artículo de sq de 2022 en Hype sobre la optimización de píxeles chunky, que lleva el enfoque a 4x4 píxeles y cataloga una familia de estrategias de renderizado con conteos de ciclos precisos. Juntos, mapean el espacio de diseño: cómo funcionan los píxeles chunky, cómo los usan los rotozoomers, y las compensaciones de rendimiento que determinan si tu efecto corre a 4 fotogramas por pantalla o 12.

---

## Qué Hace Realmente un Rotozoomer

Un rotozoomer muestra una textura 2D rotada por cierto ángulo y escalada por cierto factor. El enfoque ingenuo: para cada píxel de pantalla, calcular su coordenada de textura correspondiente mediante una rotación trigonométrica:

```
    tx = sx * cos(theta) * scale  +  sy * sin(theta) * scale  +  offset_x
    ty = -sx * sin(theta) * scale  +  sy * cos(theta) * scale  +  offset_y
```

A 256x192, eso son 49.152 píxeles, cada uno necesitando dos multiplicaciones. Incluso con una multiplicación de tabla de cuadrados de 54 T-states (Capítulo 4), excedes cinco millones de T-states -- aproximadamente 70 fotogramas de tiempo de CPU. El efecto es matemáticamente trivial y computacionalmente imposible.

La idea clave es que la transformación es *lineal*. Moverse un píxel a la derecha en la pantalla siempre suma el mismo (dx, dy) a las coordenadas de textura. Moverse un píxel hacia abajo siempre suma el mismo (dx', dy'). El costo por píxel colapsa de dos multiplicaciones a dos sumas:

```
Step right:   dx = cos(theta) * scale,   dy = -sin(theta) * scale
Step down:    dx' = sin(theta) * scale,  dy' = cos(theta) * scale
```

Comienza cada fila en la coordenada de textura correcta y avanza por (dx, dy) para cada píxel. El bucle interno se convierte en: leer el téxel, avanzar por (dx, dy), repetir. Dos sumas por píxel, ninguna multiplicación. La configuración por fotograma son cuatro multiplicaciones para calcular los vectores de paso a partir del ángulo y escala actuales. Todo lo demás se deduce de la linealidad.

Esta es la optimización fundamental detrás de todo rotozoomer en toda plataforma. En el Amiga, en el PC, en el Spectrum.

---

## Píxeles Chunky: Intercambiando Resolución por Velocidad

Incluso a dos sumas por píxel, escribir 6.144 bytes en la memoria de video entrelazada del Spectrum por fotograma es impráctico -- no si también quieres actualizar el ángulo y dejar tiempo para la música. Los píxeles chunky resuelven esto reduciendo la resolución efectiva. En lugar de un téxel por píxel de pantalla, mapeas un téxel a un bloque de 2x2, 4x4 u 8x8.

Illusion usa píxeles chunky de 2x2: resolución efectiva 128x96, una reducción de 4x en el trabajo. El efecto se ve pixelado de cerca, pero a la velocidad con que la textura barre la pantalla, el movimiento oculta la tosquedad. El ojo perdona la baja resolución cuando todo está en movimiento.

La codificación está diseñada para el bucle interno. Cada píxel chunky se almacena como `$03` (encendido) o `$00` (apagado). ¿Por qué `$03`? Porque `ADD A,A` dos veces lo desplaza a la izquierda 2 posiciones, y luego `ADD A,(HL)` fusiona los bits del siguiente píxel en las posiciones inferiores. Cuatro píxeles chunky se combinan en un byte de salida usando nada más que desplazamientos y sumas -- sin enmascaramiento, sin ramificación, sin manipulación de bits.

---

## El Bucle Interno de Illusion

El desensamblado de Introspec revela la secuencia central de renderizado. HL recorre la textura; H rastrea un eje y L el otro:

```z80
; Inner loop: combine 4 chunky pixels into one output byte
    ld   a,(hl)        ;  7T  -- read first chunky pixel ($03 or $00)
    inc  l             ;  4T  -- step right in texture
    dec  h             ;  4T  -- step up in texture
    add  a,a           ;  4T  -- shift left
    add  a,a           ;  4T  -- shift left (now shifted by 2)
    add  a,(hl)        ;  7T  -- add second chunky pixel
```

La secuencia se repite para el tercer y cuarto píxel. Los `inc l` y `dec h` juntos trazan un camino diagonal a través de la textura -- y diagonal significa rotado. La combinación específica de instrucciones de incremento y decremento determina el ángulo de rotación.

| Paso | Instrucciones | T-states |
|------|-------------|----------|
| Leer píxel 1 | `ld a,(hl)` | 7 |
| Caminar | `inc l : dec h` | 8 |
| Desplazar + Leer píxel 2 | `add a,a : add a,a : add a,(hl)` | 15 |
| Caminar | `inc l : dec h` | 8 |
| Desplazar + Leer píxel 3 | `add a,a : add a,a : add a,(hl)` | 15 |
| Caminar | `inc l : dec h` | 8 |
| Desplazar + Leer píxel 4 | `add a,a : add a,a : add a,(hl)` | 15 |
| Caminar | `inc l : dec h` | 8 |
| Salida + avance | `ld (de),a : inc e` | ~11 |
| **Total por byte** | | **~95** |

Introspec midió aproximadamente 95 T-states por 4 chunks.

La observación crítica: la dirección de caminata está codificada directamente en el flujo de instrucciones. Un ángulo de rotación diferente requiere instrucciones diferentes. Ocho direcciones primarias son posibles usando combinaciones de `inc l`, `dec l`, `inc h`, `dec h` y `nop`. Esto significa que el código de renderizado cambia cada fotograma.

---

## Generación de Código por Fotograma

El código de renderizado se genera fresco en cada fotograma, con instrucciones de dirección parcheadas para el ángulo actual:

| Rango de ángulo | Paso H | Paso L | Dirección |
|-------------|--------|--------|-----------|
| ~0 grados | `nop` | `inc l` | Pura derecha |
| ~45 grados | `dec h` | `inc l` | Derecha y arriba |
| ~90 grados | `dec h` | `nop` | Pura arriba |
| ~135 grados | `dec h` | `dec l` | Izquierda y arriba |
| ~180 grados | `nop` | `dec l` | Pura izquierda |
| ~225 grados | `inc h` | `dec l` | Izquierda y abajo |
| ~270 grados | `inc h` | `nop` | Pura abajo |
| ~315 grados | `inc h` | `inc l` | Derecha y abajo |

Para ángulos intermedios, el generador distribuye los pasos de manera desigual usando una acumulación de error tipo Bresenham. Una rotación de 30 grados alterna entre `inc l : nop` e `inc l : dec h` a una proporción aproximada de 2:1, aproximando la tangente de 1,73:1 de 30 grados. El código resultante es un bucle desenrollado donde cada iteración tiene su propio par de caminata específico, ajustado al ángulo actual.

El costo de renderizado para 128x96 a chunky 2x2:

```
16 output bytes/row x 95 T-states = 1,520 T-states/row
1,520 x 96 rows = 145,920 T-states total
```

Aproximadamente 2 fotogramas en un Pentagon. La estimación de Introspec de 4-6 fotogramas por pantalla es más conservadora, contabilizando la generación de código, transferencia de búfer y la sobrecarga que se acumula más allá del bucle interno desnudo.

---

## Transferencia de Búfer a Pantalla

El rotozoomer renderiza en un búfer fuera de pantalla, luego lo transfiere a la memoria de video. La disposición de pantalla entrelazada hace que el renderizado directo sea doloroso, y el búfer evita el tearing.

La transferencia usa la pila:

```z80
    pop  hl                   ; 10T -- read 2 bytes from buffer
    ld   (screen_addr),hl     ; 16T -- write 2 bytes to screen
```

Las direcciones de pantalla están incrustadas como operandos literales, precalculadas para el entrelazado del Spectrum -- otra instancia de generación de código. A 26 T-states por dos bytes, una transferencia completa de 1.536 bytes cuesta menos de 20.000 T-states. El paso de renderizado es el cuello de botella, no la transferencia.

---

## Inmersión Profunda: Píxeles Chunky 4x4 (sq, Hype 2022)

El artículo de sq lleva los píxeles chunky a 4x4 -- resolución efectiva 64x48. El resultado visual es más tosco, pero la ganancia de rendimiento abre efectos como bumpmapping y renderizado entrelazado. El artículo es un estudio en metodología de optimización: empieza directo, mejora iterativamente, mide en cada paso.

**Enfoque 1: LD/INC básico (101 T-states por par).** Carga valor chunky, escribe al búfer, avanza punteros. El cuello de botella es la gestión de punteros: `INC HL` a 6 T-states se acumula a lo largo de miles de iteraciones.

**Enfoque 2: Variante LDI (104 T-states -- ¡más lento!).** `LDI` copia un byte e incrementa automáticamente ambos punteros en una instrucción. Pero también decrementa BC, consumiendo un par de registros. La sobrecarga de guardar/restaurar lo hace *más lento* que el enfoque ingenuo. Una historia con moraleja: en el Z80, la instrucción "inteligente" no siempre es la rápida.

**Enfoque 3: LDD doble byte (80 T-states por par).** Organizando origen y destino en orden inverso, el auto-decremento de `LDD` trabaja a tu favor. Una secuencia combinada de dos bytes explota esto para una mejora del 21% sobre la línea base.

**Enfoque 4: Código auto-modificable (76-78 T-states por par).** Pre-generar 256 procedimientos de renderizado, uno por cada posible valor de byte, cada uno con el valor del píxel incorporado como operando inmediato:

```z80
; One of 256 pre-generated procedures
proc_A5:
    ld   (hl),$A5        ; 10T  -- value baked into instruction
    inc  l               ;  4T
    ld   (hl),$A5        ; 10T  -- 4x4 block spans 2 bytes horizontally
    ; ... handle vertical repetition ...
    ret                  ; 10T
```

Los 256 procedimientos ocupan aproximadamente 3KB. El renderizado por píxel cae a 76-78 T-states -- 23% más rápido que la línea base, 27% más rápido que LDI.

### Comparación de Rendimiento

| Enfoque | Ciclos/par | Relativo | Memoria |
|----------|------------|----------|--------|
| LD/INC básico | 101 | 1,00x | Mínima |
| Variante LDI | 104 | 0,97x | Mínima |
| LDD doble byte | 80 | 1,26x | Mínima |
| Auto-modificable (256 procs) | 76-78 | 1,30x | ~3KB |

El enfoque auto-modificable gana, pero el margen sobre LDD es estrecho. En una demo de 128K, 3KB están fácilmente disponibles. En una producción de 48K, el enfoque LDD podría ser la mejor decisión de ingeniería.

### Raíces Históricas: Born Dead #05

sq señala que estas técnicas se construyen sobre trabajo publicado en Born Dead #05, un periódico de demoscene ruso de aproximadamente 2001. El artículo fundacional describía el renderizado chunky básico; la contribución de sq fue la optimización sistemática y la variante de procedimientos pre-generados. Así es como evoluciona el conocimiento de la escena: una técnica aparece en una revista de disco oscura, circula dentro de la comunidad, y veintiún años después alguien la revisita con mediciones frescas y trucos nuevos.

---

## Práctico: Construyendo un Rotozoomer Simple

Aquí está la estructura para un rotozoomer funcional con píxeles chunky 2x2 y una textura de tablero de ajedrez.

**Textura.** Una tabla de 256 bytes alineada a página donde cada byte es `$03` o `$00`, generando franjas de 8 píxeles de ancho. El registro H proporciona la segunda dimensión; hacer XOR de H en la consulta crea un tablero de ajedrez completo:

```z80
    ALIGN 256
texture:
    LUA ALLPASS
    for i = 0, 255 do
        if math.floor(i / 8) % 2 == 0 then
            sj.add_byte(0x03)
        else
            sj.add_byte(0x00)
        end
    end
    ENDLUA
```

**Tabla de senos y configuración por fotograma.** Una tabla de senos de 256 entradas alineada a página controla la rotación. Cada fotograma lee `sin(frame_counter)` y `cos(frame_counter)` (coseno mediante un desplazamiento de índice de 64) para calcular los vectores de paso, luego parchea las instrucciones de caminata del bucle interno con los opcodes correctos.

**El bucle de renderizado.** El bucle externo establece la coordenada de textura inicial para cada fila (avanzando perpendicular a la dirección de caminata). El bucle interno recorre la textura:

```z80
.byte_loop:
    ld   a,(hl)              ; read texel 1
    inc  l                   ; walk (patched per-frame)
    add  a,a : add  a,a     ; shift
    add  a,(hl)              ; read texel 2
    inc  l                   ; walk
    add  a,a : add  a,a     ; shift
    add  a,(hl)              ; read texel 3
    inc  l                   ; walk
    add  a,a : add  a,a     ; shift
    add  a,(hl)              ; read texel 4
    inc  l                   ; walk
    ld   (de),a              ; write output byte
    inc  de
    djnz .byte_loop
```

Las instrucciones `inc l` son los objetivos del generador de código. Antes de cada fotograma, se parchan a la combinación apropiada de `inc l`/`dec l`/`inc h`/`dec h`/`nop` basada en el ángulo actual. Para ángulos no cardinales, un acumulador de error de Bresenham distribuye los pasos del eje menor a lo largo de la fila, así que cada instrucción de caminata en el bucle desenrollado puede ser diferente de sus vecinas.

**Bucle principal.** `HALT` para vsync, calcular vectores de paso, generar código de caminata, renderizar al búfer, copiar búfer a pantalla via pila, incrementar contador de fotograma, repetir.

---

## El Espacio de Diseño

El tamaño de píxel chunky es la decisión de diseño más trascendental en un rotozoomer:

| Parámetro | 2x2 (Illusion) | 4x4 (sq) | 8x8 (atributos) |
|-----------|----------------|----------|-------------------|
| Resolución | 128x96 | 64x48 | 32x24 |
| Téxeles/fotograma | 12.288 | 3.072 | 768 |
| Costo del bucle interno | ~146.000 T | ~29.000 T | ~7.300 T |
| Fotogramas/pantalla | ~2,3 | ~0,5 | ~0,1 |
| Calidad visual | Buen movimiento | Chunky pero rápido | Muy pixelado |
| Caso de uso | Efectos destacados | Bumpmapping, overlays | FX solo atributos |

La versión 4x4 cabe dentro de un solo fotograma con espacio para un motor de música y otros efectos. La versión 2x2 toma 2-3 fotogramas pero se ve sustancialmente mejor. El caso 8x8 es el túnel de atributos del Capítulo 9.

Una vez que tienes un renderizador chunky rápido, el rotozoomer es solo una aplicación. El mismo motor impulsa **bumpmapping** (leer diferencias de altura en lugar de téxeles crudos, derivar sombreado), **efectos entrelazados** (renderizar filas pares/impares en fotogramas alternos, duplicando la tasa de fotogramas efectiva a costa de parpadeo), y **distorsión de texturas** (variar la dirección de caminata por fila para efectos ondulados o de ondulación). Un rotozoomer 4x4 puede compartir un fotograma con un scrolltext, un motor de música y una transferencia de pantalla. El trabajo de sq fue motivado exactamente por esta versatilidad.

---

## El Rotozoomer en Contexto

El rotozoomer no es un algoritmo de rotación. Es un *patrón de recorrido de memoria*. Caminas a través de un búfer en línea recta, y la dirección de caminata determina lo que ves. La rotación es una elección de dirección. El zoom es una elección de tamaño de paso. El Z80 no sabe trigonometría. Sabe `INC L` y `DEC H`. Todo lo demás es la interpretación del programador.

En Illusion, el rotozoomer se encuentra junto a la esfera y el dotfield scroller. Los tres comparten la misma arquitectura: parámetros precalculados, bucles internos generados, acceso secuencial a memoria. La esfera usa tablas de salto y conteos variables de `INC L`. El rotozoomer usa instrucciones de caminata parcheadas por dirección. El dotfield usa tablas de direcciones basadas en pila. Tres efectos, una filosofía de motor.

Dark construyó todos ellos. Introspec trazó todos ellos. El patrón que los conecta es la lección de la Parte II: calcula lo que necesitas antes de que comience el bucle interno, genera código que no haga nada más que leer-desplazar-escribir, y mantén el acceso a memoria secuencial.

---

## Resumen

- Un rotozoomer muestra una textura rotada y con zoom recorriéndola en ángulo. La linealidad reduce el costo por píxel de dos multiplicaciones a dos sumas.
- Los píxeles chunky (2x2, 4x4) reducen la resolución efectiva y el costo de renderizado proporcionalmente. Illusion usa 2x2 a 128x96; el sistema de sq usa 4x4 a 64x48.
- El bucle interno de Illusion: `ld a,(hl) : add a,a : add a,a : add a,(hl)` con instrucciones de caminata entre lecturas. Costo: ~95 T-states por byte para 4 píxeles chunky.
- La dirección de caminata cambia por fotograma, requiriendo generación de código -- el bucle de renderizado se parchea antes de cada fotograma.
- El recorrido de optimización 4x4 de sq: LD/INC básico (101 T-states) a LDI (104 T-states, más lento) a LDD (80 T-states) a código auto-modificable con 256 procedimientos pre-generados (76-78 T-states, ~3KB). Basado en trabajo anterior en Born Dead #05 (~2001).
- Transferencia de búfer a pantalla via `pop hl : ld (nn),hl` a ~26 T-states por dos bytes.
- El rotozoomer comparte su arquitectura con la esfera (Capítulo 6) y el dotfield (Capítulo 10): parámetros precalculados, bucles internos generados, acceso secuencial a memoria.

---

> **Fuentes:** Introspec, "Technical Analysis of Illusion by X-Trade" (Hype, 2017); sq, "Chunky Effects on ZX Spectrum" (Hype, 2022); Born Dead #05 (~2001, técnicas originales de píxeles chunky).
