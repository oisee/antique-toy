# Capítulo 16: Sprites rápidos

> *"¿Dos colores por celda? Bien. Pero esos dos colores se van a mover."*

---

Todo juego necesita cosas que se muevan. Balas, enemigos, el personaje del jugador, explosiones. En cualquier hardware con un blitter o una GPU, la mecánica de colocar una imagen pequeña en una posición arbitraria de la pantalla se resuelve por ti. En el ZX Spectrum, es tu problema.

El Spectrum no tiene sprites por hardware, ni blitter, ni coprocesador. Cada píxel de cada sprite es colocado por tu código Z80, una instrucción a la vez, en la misma memoria de vídeo que la ULA está leyendo 50 veces por segundo. Y como el diseño de la memoria de pantalla es entrelazado (Capítulo 2), "una fila abajo" significa `INC H` --- a menos que estés cruzando un límite de carácter, en cuyo caso significa algo considerablemente más feo.

Este capítulo presenta seis métodos para dibujar sprites en el Spectrum, desde la rutina XOR más simple hasta los sprites compilados que se ejecutan a la velocidad máxima teórica del hardware. Cada método tiene compensaciones. También veremos el Agon Light 2, donde el VDP proporciona sprites por hardware y todo el problema se colapsa en un puñado de llamadas API.

---

## Método 1: Sprites XOR

### El enfoque más simple

El dibujo XOR es el sprite mínimo viable. No requiere datos de máscara, ni búfer de guardado de fondo, ni paso de borrado. Dibujas el sprite aplicando XOR entre sus datos de píxeles y la pantalla, y lo borras aplicando XOR con los mismos datos de nuevo --- la propiedad del XOR de que `A XOR B XOR B = A` garantiza que el fondo se restaura.

Aquí hay una rutina completa de sprite XOR de 16x16:

```z80
; Draw a 16x16 XOR sprite
; Input:  HL = screen address (top-left byte of sprite position)
;         IX = pointer to sprite data (32 bytes: 2 bytes x 16 rows)
;
xor_sprite_16x16:
    ld   b, 16              ;  7 T   16 rows

.row:
    ld   a, (ix+0)          ; 19 T   left byte of sprite row
    xor  (hl)               ;  7 T   combine with screen
    ld   (hl), a            ;  7 T   write back
    inc  l                  ;  4 T   move right one byte

    ld   a, (ix+1)          ; 19 T   right byte of sprite row
    xor  (hl)               ;  7 T
    ld   (hl), a            ;  7 T   write back
    dec  l                  ;  4 T   restore column

    inc  ix                 ; 10 T   \  advance sprite
    inc  ix                 ; 10 T   /  data pointer

    inc  h                  ;  4 T   move down one pixel row
    ld   a, h               ;  4 T   \
    and  7                  ;  7 T    | check character
    jr   nz, .no_boundary   ;  7 T   /  boundary crossing

    ; Character boundary: adjust HL
    ld   a, l               ;  4 T
    add  a, 32              ;  7 T
    ld   l, a               ;  4 T
    jr   c, .no_fix         ;  7 T
    ld   a, h               ;  4 T
    sub  8                  ;  7 T
    ld   h, a               ;  4 T
.no_fix:

.no_boundary:
    djnz .row               ; 13 T  (8 on last)
    ret                     ; 10 T
```

El bucle interno cuesta 98 T-states por fila en el caso común (sin cruce de límite de carácter) y hasta 131 T-states en los límites de carácter. Para 16 filas: aproximadamente 1.700 T-states por dibujo. Para borrar el sprite, llama a la misma rutina de nuevo con la misma dirección de pantalla --- el XOR se deshace a sí mismo.

Coste total para animar un sprite XOR: ~3.400 T-states por fotograma (dibujo + borrado).

### Cuándo funciona el XOR

Los sprites XOR son perfectos para:

- **Cursores.** Un cursor de texto parpadeante, una mira, un resaltado de selección. Cualquier cosa que se sienta encima de un fondo estático y no necesite verse bonito.
- **Balas.** Un proyectil de 2x2 o 4x4 que se mueve lo suficientemente rápido como para que los artefactos visuales sean invisibles.
- **Marcadores de depuración.** Trazar cajas de colisión, posiciones de entidades, nodos de ruta.

### Cuándo falla el XOR

El XOR tiene dos problemas serios. Primero, la calidad visual es pobre. Donde el sprite se superpone con datos de pantalla existentes, los píxeles se invierten en lugar de reemplazarse. Un sprite blanco pasando sobre texto blanco se vuelve invisible. Un personaje cuidadosamente dibujado se convierte en un lío de píxeles invertidos contra un fondo detallado.

Segundo, el XOR no te da control sobre los atributos. El color del sprite es cualquier combinación de tinta/papel que esté en las celdas que superpone. Para una bala o cursor esto está bien. Para un sprite de personaje, no.

A pesar de sus limitaciones, el XOR es lo suficientemente útil como para que todo programador de juegos debería tenerlo en su kit de herramientas. Veinte líneas de código, cero memoria extra, y simplemente funciona.

---

## Método 2: Sprites con máscara OR+AND

### El estándar de la industria

Casi todos los juegos comerciales de Spectrum lanzados después de 1984 usaron esta técnica o una variante cercana. Un sprite con máscara lleva dos piezas de datos por cada fila: una *máscara* y el *gráfico*. La máscara define la forma del sprite --- qué píxeles pertenecen al sprite y cuáles son transparentes. El gráfico define la apariencia del sprite --- cuáles de los píxeles con forma están activos.

El algoritmo de dibujo para cada byte es:

1. Lee el byte de la pantalla.
2. Aplica AND con la máscara. Esto limpia los píxeles donde aparecerá el sprite, dejando el resto del fondo intacto.
3. Aplica OR con el gráfico. Esto estampa los píxeles del sprite en el área limpiada.

El resultado: el sprite aparece en pantalla con las áreas transparentes mostrando el fondo a través. Sin artefactos XOR. Sin píxeles invertidos. Sprites limpios y de aspecto profesional.

### Formato de datos

Para un sprite de 16x16, cada fila contiene 4 bytes: máscara-izquierda, gráfico-izquierda, máscara-derecha, gráfico-derecha. El byte de máscara tiene `1` para píxeles transparentes y `0` para píxeles opacos (porque AND con 1 preserva el fondo, AND con 0 lo limpia). Total de datos por sprite: 16 filas x 4 bytes = 64 bytes.

### El bucle interno

```z80
; Draw a 16x16 masked sprite (byte-aligned)
; Input:  HL = screen address
;         DE = pointer to sprite data
;              Format per row: mask_L, gfx_L, mask_R, gfx_R
;
masked_sprite_16x16:
    ld   b, 16              ;  7 T

.row:
    ; --- Left byte ---
    ld   a, (de)            ;  7 T   load mask
    and  (hl)               ;  7 T   clear sprite-shaped hole in background
    inc  de                 ;  6 T
    ld   c, a               ;  4 T   save masked background

    ld   a, (de)            ;  7 T   load graphic
    or   c                  ;  4 T   stamp sprite into hole
    ld   (hl), a            ;  7 T   write to screen
    inc  de                 ;  6 T
    inc  l                  ;  4 T   move right

    ; --- Right byte ---
    ld   a, (de)            ;  7 T   load mask
    and  (hl)               ;  7 T
    inc  de                 ;  6 T
    ld   c, a               ;  4 T

    ld   a, (de)            ;  7 T   load graphic
    or   c                  ;  4 T
    ld   (hl), a            ;  7 T
    inc  de                 ;  6 T
    dec  l                  ;  4 T   restore column

    ; --- Next row (DOWN_HL) ---
    inc  h                  ;  4 T
    ld   a, h               ;  4 T
    and  7                  ;  7 T
    jr   nz, .no_boundary   ;  7 T

    ld   a, l               ;  4 T
    add  a, 32              ;  7 T
    ld   l, a               ;  4 T
    jr   c, .no_fix         ;  7 T
    ld   a, h               ;  4 T
    sub  8                  ;  7 T
    ld   h, a               ;  4 T
.no_fix:
.no_boundary:
    djnz .row               ; 13 T
    ret                     ; 10 T
```

### Conteo de ciclos

Contemos el caso común (sin cruce de límite de carácter):

| Sección | Instrucciones | T-states |
|---------|-------------|----------|
| Byte izquierdo: máscara+dibujo | `ld a,(de)` + `and (hl)` + `inc de` + `ld c,a` + `ld a,(de)` + `or c` + `ld (hl),a` + `inc de` + `inc l` | 52 |
| Byte derecho: máscara+dibujo | Misma secuencia + `dec l` | 52 |
| Avance de fila | `inc h` + `ld a,h` + `and 7` + `jr nz` | 22 |
| Bucle | `djnz` | 13 |
| **Total por fila** | | **139** |

Para 16 filas: 16 x 139 = **2.224 T-states** (caso común). Añade sobrecarga de cruce de límite para ~2 límites en un sprite de 16 píxeles: aproximadamente **2.300 T-states** en total.

Pero esto solo dibuja el sprite. También necesitas borrar el sprite del fotograma anterior, lo que significa restaurar el fondo --- abordaremos esto en el Método 6 (Rectángulos sucios). Por ahora, nota que solo el dibujo es aproximadamente 35% más caro que XOR, pero la calidad visual es incomparablemente mejor.

### Alineación a byte y el problema del desplazamiento

La rutina anterior asume que el sprite comienza en un límite de byte --- es decir, la coordenada x es un múltiplo de 8. En la práctica, los personajes de juego se mueven píxel a píxel, no en saltos de 8 píxeles. Si la posición x de tu sprite es 53, comienza en la columna de bytes 6, píxel 5 dentro de ese byte. Los datos del sprite necesitan ser desplazados a la derecha por 5 bits.

Puedes desplazar al momento de dibujar:

```z80
; Shift mask and graphic right by A bits
; This adds significant cost per byte
    ld   a, (de)            ;  7 T   load mask byte
    ld   c, a               ;  4 T
    ld   a, b               ;  4 T   shift count
.shift:
    srl  c                  ;  8 T   \
    dec  a                  ;  4 T    | per-bit shift loop
    jr   nz, .shift         ; 12 T   /
```

Cada bit de desplazamiento cuesta 24 T-states por byte en este bucle ingenuo. Para un desplazamiento de 5 bits en un sprite de 16 de ancho (3 bytes por fila después del desplazamiento, ya que el sprite se desborda a un tercer byte), estás viendo unos 5 x 24 x 3 = 360 T-states extra por fila --- duplicando el coste de dibujo. Para 8 sprites a 25 fps, esta sobrecarga de desplazamiento sola consumiría aproximadamente 46.000 T-states por fotograma --- más del 60% de tu presupuesto.

Por eso existen los sprites pre-desplazados.

---

## Método 3: Sprites pre-desplazados

### La compensación memoria-por-velocidad

La idea es simple: en lugar de desplazar los datos del sprite al momento de dibujar, pre-calcula versiones desplazadas del sprite al momento de carga (o al momento del ensamblaje) y almacénalas junto al original. Cuando necesitas dibujar el sprite con un offset de 3 píxeles dentro de un byte, usas la versión que fue pre-desplazada por 3 píxeles.

Hay dos configuraciones comunes:

**4 copias desplazadas** (desplazamiento de 0, 2, 4, 6 píxeles). Esto da una resolución horizontal de 2 píxeles. El sprite se ajusta a posiciones de píxeles pares, lo que a menudo es aceptable para personajes de juego. Coste de memoria: 4x los datos sin desplazar.

**8 copias desplazadas** (desplazamiento de 0, 1, 2, 3, 4, 5, 6, 7 píxeles). Posicionamiento horizontal completo a nivel de píxel. Coste de memoria: 8x los datos sin desplazar. Pero cada versión desplazada también es más ancha: un sprite de 16 píxeles de ancho desplazado 1--7 bits se desborda a una tercera columna de bytes, así que cada copia desplazada tiene 3 bytes de ancho en lugar de 2.

### Cálculo de memoria

Para un sprite de 16x16 con máscara:

| Configuración | Bytes por fila | Filas | Copias | Total |
|---------------|--------------|------|--------|-------|
| Solo sin desplazar | 4 (máscara+gfx x 2 bytes) | 16 | 1 | 64 |
| 4 desplazamientos | 4 | 16 | 4 | 256 |
| 8 desplazamientos (3 bytes de ancho) | 6 (máscara+gfx x 3 bytes) | 16 | 8 | 768 |

Para un sprite con 4 fotogramas de animación, multiplica por 4:

| Configuración | Por fotograma | 4 fotogramas | 8 sprites |
|---------------|-----------|----------|-----------|
| Sin desplazar + desplazamiento en tiempo de ejecución | 64 | 256 | 2.048 |
| 4 pre-desplazamientos | 256 | 1.024 | 8.192 |
| 8 pre-desplazamientos | 768 | 3.072 | 24.576 |

24 KB para 8 sprites con pre-desplazamiento completo. En un Spectrum 128K, eso es un banco y medio de memoria solo para datos de sprites. En una máquina de 48K, es casi la mitad de la RAM disponible. La compensación es cruda.

### Compromiso práctico

La mayoría de los juegos usan 4 copias pre-desplazadas. La resolución horizontal de 2 píxeles apenas se nota en el juego. Algunos juegos usan 8 copias para el personaje del jugador (donde el movimiento suave importa más) y 4 copias o incluso desplazamiento en tiempo de ejecución para sprites menos importantes.

La rutina de dibujo para sprites pre-desplazados es idéntica a la rutina de sprite con máscara alineada a byte --- simplemente seleccionas el conjunto de datos pre-desplazado correcto antes de llamarla:

```z80
; Select pre-shifted sprite data
; Input:  A = x coordinate (0-255)
;         IY = base of pre-shift table (4 entries, each pointing to 16-row data)
; Output: DE = pointer to correct shifted sprite data
;
select_preshift:
    and  $06                ;  7 T   mask to shifts 0,2,4,6 (4 copies)
    ld   c, a               ;  4 T
    ld   b, 0               ;  7 T
    add  iy, bc             ; 15 T
    ld   e, (iy+0)          ; 19 T
    ld   d, (iy+1)          ; 19 T   DE = pointer to shifted data
    ret
```

El tiempo de dibujo es el mismo que el Método 2: ~2.300 T-states. Pero has eliminado completamente el coste de desplazamiento por píxel. El precio se paga en memoria, no en T-states.

---

## Método 4: Sprites de pila (El método PUSH)

### La salida más rápida en el Z80

Vimos en el Capítulo 3 que PUSH escribe 2 bytes en 11 T-states --- 5,5 T-states por byte, la operación de escritura más rápida en el Z80. Los sprites de pila explotan esto para la salida de sprites: establece SP al final del área del sprite en la pantalla, carga pares de registros con datos del sprite, y haz PUSH de ellos en la pantalla.

La técnica requiere una configuración crítica:

1. **DI** --- deshabilita interrupciones. Si una interrupción se dispara mientras SP apunta a la pantalla, la CPU empuja su dirección de retorno en tus datos de píxeles, corrompiendo la visualización y probablemente colgando.
2. **Guarda SP** --- almacena el puntero de pila real usando código auto-modificable (SMC).
3. **Establece SP** a la esquina inferior derecha del área del sprite en pantalla (PUSH funciona hacia abajo).
4. **Carga y PUSH** --- carga datos del sprite en pares de registros y haz PUSH de ellos en secuencia.
5. **Restaura SP y EI** --- devuelve la pila y re-habilita interrupciones.

### El bucle interno

Para un sprite de 16x16 (2 bytes de ancho), cada fila es un solo PUSH:

```z80
; Stack sprite: 16x16, writes 2 bytes per row via PUSH
; Input:  screen_addr = pre-calculated bottom-right screen address
;         sprite_data = 32 bytes of pixel data (2 bytes x 16 rows,
;                       stored bottom-to-top because PUSH goes downward)
;
stack_sprite_16x16:
    di                           ;  4 T

    ld   (restore_sp + 1), sp    ; 20 T   save SP (self-mod)

    ld   sp, (screen_addr)       ; 20 T   SP = bottom of sprite on screen
    ld   ix, sprite_data         ; 14 T

    ; Row 15 (bottom) - each PUSH writes 2 bytes and decrements SP
    ld   h, (ix+31)              ; 19 T   \
    ld   l, (ix+30)              ; 19 T    | load bottom row
    push hl                      ; 11 T   /  write to screen

    ; But wait --- SP just decremented by 2, and the next row UP
    ; on the Spectrum screen is NOT at SP-2. The interleaved layout
    ; means "one row up" is at a completely different address.
    ;
    ; This is the fundamental problem with stack sprites on the
    ; Spectrum: the screen is not contiguous in memory.
```

Y aquí está la dificultad fundamental. El método PUSH es la escritura más rápida posible, pero el diseño de pantalla entrelazado del Spectrum significa que las filas de pantalla consecutivas no están en direcciones consecutivas. SP decrementa linealmente, pero las filas de pantalla siguen el patrón `010TTSSS LLLCCCCC` del Capítulo 2.

### Haciéndolo funcionar: cadena de SP pre-calculada

La solución es no depender del auto-decremento de SP para la navegación de filas. En su lugar, estableces SP explícitamente para cada fila:

```z80
; Stack sprite: 16x16 with explicit SP per row
; This is the practical version --- each row gets SP set independently
;
stack_sprite_16x16:
    di                           ;  4 T
    ld   (restore_sp + 1), sp    ; 20 T

    ld   hl, (sprite_data + 0)   ; 16 T   row 0 data
    ld   sp, (row_addrs + 0)     ; 20 T   SP = screen addr for row 0 + 2
    push hl                      ; 11 T   write row 0
                                 ;        total per row: 47 T

    ld   hl, (sprite_data + 2)   ; 16 T   row 1 data
    ld   sp, (row_addrs + 2)     ; 20 T
    push hl                      ; 11 T
    ; ... repeated for all 16 rows ...

restore_sp:
    ld   sp, $0000               ; 10 T   self-modified
    ei                           ;  4 T
    ret                          ; 10 T
```

Cada fila cuesta 47 T-states. Para 16 filas: 16 x 47 = 752 T-states, más configuración y desmontaje (~60 T-states). Total: aproximadamente **810 T-states**.

Compara esto con los ~2.300 T-states del Método 2. El sprite de pila es casi 3 veces más rápido --- pero viene con restricciones.

### Los costes

**Sin enmascaramiento.** El PUSH escribe 2 bytes incondicionalmente. Sobreescribe lo que había en pantalla. No hay paso de AND-con-máscara. El sprite siempre es un rectángulo sólido --- cualquier píxel "transparente" mostrará el color de fondo del sprite, no el fondo del juego. Para sprites sobre un fondo de color sólido (muchos juegos clásicos de Spectrum usaban negro), esto está bien. Para sprites sobre fondos detallados, no.

**Direcciones de fila pre-calculadas.** Necesitas una tabla de direcciones de pantalla para las 16 filas del sprite, actualizada cada vez que el sprite se mueve. Esto es un coste de configuración por fotograma --- no enorme, pero no gratuito.

**Las interrupciones están desactivadas.** Para 8 sprites, aproximadamente 6.500 T-states con interrupciones deshabilitadas. Si tu música funciona desde IM2, programa el dibujo de sprites inmediatamente después de HALT.

**Los datos deben almacenarse en orden PUSH.** Ya que PUSH escribe el byte alto en (SP-1) y el byte bajo en (SP-2), y SP decrementa *antes* de escribir, la disposición de datos requiere atención cuidadosa. Los datos del sprite se almacenan invertidos: el byte más a la derecha de una fila se convierte en el byte bajo cargado en el registro, el más a la izquierda se convierte en el byte alto.

### Cuándo usar sprites de pila

Los sprites de pila son el arma preferida cuando necesitas velocidad bruta y tu fondo es lo suficientemente simple como para que las sobreescrituras de rectángulo completo sean aceptables. Juegos estilo arcade con fondos negros, superposiciones de puntuación y objetos en movimiento rápido son el encaje natural. El método PUSH también se usa para limpiar pantalla y salida masiva de datos (Capítulo 3), donde la limitación de "sin enmascaramiento" es irrelevante.

---

## Método 5: Sprites compilados

### El sprite es el código

Un sprite compilado lleva la filosofía de generación de código del Capítulo 3 a su conclusión lógica. En lugar de una tabla de datos interpretada por una rutina de dibujo, el sprite *es* una rutina ejecutable. Cada byte de píxel visible en el sprite se convierte en una instrucción `LD (HL), n`. Las series transparentes se convierten en instrucciones `INC L` o `INC H` para saltarlas. El sprite completo se renderiza llamándolo con `CALL`.

### Cómo funciona

Considera un sprite simple de 8x8 con algunos píxeles transparentes. En un sprite con máscara, almacenarías pares de máscara+gráfico y ejecutarías el bucle AND/OR. En un sprite compilado, generas instrucciones Z80 al momento del ensamblaje (o al momento de carga):

```z80
; Compiled sprite for a small arrow shape
; Input:  HL = screen address of top-left byte
; The sprite draws itself.
;
compiled_arrow:
    ; Row 0: one pixel byte
    ld   (hl), $18          ; 10 T   ..##....
    inc  h                  ;  4 T   next row

    ; Row 1: one pixel byte
    ld   (hl), $3C          ; 10 T   ..####..
    inc  h                  ;  4 T

    ; Row 2: one pixel byte
    ld   (hl), $7E          ; 10 T   .######.
    inc  h                  ;  4 T

    ; Row 3: one pixel byte
    ld   (hl), $FF          ; 10 T   ########
    inc  h                  ;  4 T

    ; Row 4: one pixel byte
    ld   (hl), $3C          ; 10 T   ..####..
    inc  h                  ;  4 T

    ; Row 5: one pixel byte
    ld   (hl), $3C          ; 10 T   ..####..
    inc  h                  ;  4 T

    ; Row 6: one pixel byte
    ld   (hl), $3C          ; 10 T   ..####..
    inc  h                  ;  4 T

    ; Row 7: one pixel byte
    ld   (hl), $3C          ; 10 T   ..####..

    ret                     ; 10 T

    ; Total: 8 x (10 + 4) + 10 = 122 T-states
    ; Compare: masked routine for 8x8 = ~600 T-states
```

Eso son 122 T-states para un sprite de 8x8. El enfoque con máscara toma aproximadamente 5 veces más.

### Sprite compilado de 16x16

Para un sprite más ancho, cada fila puede tener múltiples instrucciones `LD (HL), n` separadas por `INC L`:

```z80
; Compiled sprite: 16x16 (2 bytes wide)
; Input:  HL = screen address of top-left
;
compiled_sprite_16x16:
    ; Row 0
    ld   (hl), $3C          ; 10 T   left byte
    inc  l                  ;  4 T
    ld   (hl), $0F          ; 10 T   right byte
    dec  l                  ;  4 T   restore column
    inc  h                  ;  4 T   next row
                            ;        row cost: 32 T

    ; Row 1
    ld   (hl), $7E          ; 10 T
    inc  l                  ;  4 T
    ld   (hl), $1F          ; 10 T
    dec  l                  ;  4 T
    inc  h                  ;  4 T
                            ;        row cost: 32 T

    ; ... rows 2-6 similar ...

    ; Row 7 (character boundary)
    ld   (hl), $FF          ; 10 T
    inc  l                  ;  4 T
    ld   (hl), $FF          ; 10 T
    dec  l                  ;  4 T
    ; Character boundary crossing:
    ld   a, l               ;  4 T
    add  a, 32              ;  7 T
    ld   l, a               ;  4 T
    ld   a, h               ;  4 T
    sub  8                  ;  7 T
    ld   h, a               ;  4 T   boundary cost: 30 T
    inc  h                  ;  4 T
                            ;        row cost: 62 T

    ; Rows 8-15 similar to 0-6, with another boundary at row 15
    ; ...
    ret                     ; 10 T
```

Por fila (caso común): 32 T-states. Para 16 filas con 1--2 cruces de límite: aproximadamente **570 T-states**.

### Las compensaciones

**Fortalezas:**
- El método de sprite con máscara más rápido. Puedes incorporar enmascaramiento AND en sprites compilados --- cada byte se convierte en `ld a,(hl)` / `and mask` / `or graphic` / `ld (hl),a` en lugar de un simple `ld (hl),n`. Incluso con enmascaramiento, el enfoque compilado evita sobrecarga de bucle, gestión de puntero de datos y conteo de filas.
- Sin sobrecarga de bucle en absoluto. El código es completamente en línea recta.
- Las regiones transparentes no cuestan nada si abarcan bytes completos --- simplemente las saltas con `INC L` o `INC H`.

**Debilidades:**
- **Tamaño de código.** Cada byte visible toma 2 bytes de código (`LD (HL), n`). Con enmascaramiento (4 instrucciones por byte), el tamaño de código se triplica aproximadamente. Un conjunto completo de 8 sprites compilados pre-desplazados con 4 fotogramas de animación puede alcanzar varios kilobytes por sprite.
- **Sin cambios de datos en tiempo de ejecución.** Los valores de píxeles están integrados en los operandos de instrucciones. La animación requiere una rutina compilada separada por fotograma.
- **El manejo de límites está integrado.** Los cruces de límite de carácter se sitúan en posiciones fijas, así que el sprite debe mantener alineación vertical consistente o necesitas múltiples versiones compiladas.

### Sprites compilados con enmascaramiento

Para sprites que necesitan aparecer sobre un fondo detallado, compilas la máscara en el código:

```z80
; Compiled sprite with masking: one byte
; Instead of ld (hl),n, we do:
    ld   a, (hl)            ;  7 T   read screen
    and  $C3                ;  7 T   mask: clear sprite pixels
    or   $3C                ;  7 T   graphic: stamp sprite
    ld   (hl), a            ;  7 T   write back
                            ;        per-byte cost: 28 T
```

28 T-states por byte, versus 52 T-states por byte en la rutina con máscara de propósito general (Método 2). El ahorro viene de eliminar la gestión de punteros, conteo de bucle y carga de datos --- los valores de máscara y gráfico son operandos inmediatos.

Para 16 filas x 2 bytes: 16 x (28 + 28 + 4 + 4 + 4) = 16 x 68 = **1.088 T-states**. Esto es aproximadamente la mitad del coste de la rutina con máscara genérica, con soporte completo de transparencia.

| Método | Coste de dibujo 16x16 | Enmascaramiento | Notas |
|--------|-----------------|---------|-------|
| Sprite XOR | ~1.700 T | No | Dibujo + borrado = ~3.400 T |
| OR+AND con máscara | ~2.300 T | Sí | Enfoque estándar |
| Pre-desplazado con máscara | ~2.300 T | Sí | Sin coste de desplazamiento; 4--8x memoria |
| Sprite de pila (PUSH) | ~810 T | No | DI requerido; rectángulo sólido |
| Compilado (sin máscara) | ~570 T | No | Código = sprite; huella grande |
| Compilado (con máscara) | ~1.088 T | Sí | Lo mejor de ambos; huella más grande |

![Sprite rendering methods comparison](illustrations/output/ch16_sprite_methods.png)

---

## Método 6: Rectángulos sucios

### El problema del fondo

Los Métodos 1--5 todos abordan la cuestión de *poner* píxeles en pantalla. Pero los sprites se mueven. Cada fotograma, el sprite está en una nueva posición. Antes de dibujar el sprite en su nueva posición, debes borrarlo de la vieja posición --- o la pantalla se llena de imágenes fantasma residuales.

El método XOR maneja esto implícitamente: XOR la vieja posición para borrar, XOR la nueva posición para dibujar. Pero para todos los demás métodos, necesitas una forma de restaurar el fondo.

Hay tres enfoques comunes:

**Limpieza completa de pantalla.** Borra el área de píxeles cada fotograma (~36.000 T-states con PUSH del Capítulo 3), luego redibuja todo. Factible pero caro.

**Guardado/restauración de fondo.** Antes de dibujar cada sprite, guarda la pantalla detrás de él. Para borrar, copia el búfer guardado de vuelta. El coste es O(tamaño_sprite) por sprite, no O(tamaño_pantalla).

**Seguimiento de rectángulos sucios.** Un refinamiento: rastrea qué rectángulos fueron modificados, restaura solo esos, luego dibuja los nuevos sprites (guardando el nuevo fondo mientras avanzas).

### El ciclo de guardado/restauración

El enfoque práctico para la mayoría de los juegos de Spectrum es guardado/restauración de fondo por sprite. Aquí está el ciclo para un sprite por fotograma:

1. **Restaurar** el fondo guardado del último fotograma (copiar búfer guardado a la vieja posición en pantalla).
2. **Guardar** el fondo en la nueva posición en pantalla (copiar pantalla al búfer de guardado).
3. **Dibujar** el sprite en la nueva posición.

El orden importa. Restauras antes de guardar para evitar sobreescribir el nuevo guardado de fondo con datos obsoletos si los sprites se superponen.

### Rutina de guardado/restauración

Para un sprite de 16x16 (2 bytes de ancho, 16 filas), el búfer de fondo es de 32 bytes:

```z80
; Save background behind a 16x16 sprite
; Input:  HL = screen address (top-left)
;         DE = pointer to save buffer (32 bytes)
;
save_background_16x16:
    ld   b, 16              ;  7 T

.row:
    ld   a, (hl)            ;  7 T   read left byte
    ld   (de), a            ;  7 T   save it
    inc  de                 ;  6 T
    inc  l                  ;  4 T

    ld   a, (hl)            ;  7 T   read right byte
    ld   (de), a            ;  7 T   save it
    inc  de                 ;  6 T
    dec  l                  ;  4 T

    ; DOWN_HL (same as sprite routines)
    inc  h                  ;  4 T
    ld   a, h               ;  4 T
    and  7                  ;  7 T
    jr   nz, .no_boundary   ;  7 T
    ld   a, l               ;  4 T
    add  a, 32              ;  7 T
    ld   l, a               ;  4 T
    jr   c, .no_fix         ;  7 T
    ld   a, h               ;  4 T
    sub  8                  ;  7 T
    ld   h, a               ;  4 T
.no_fix:
.no_boundary:
    djnz .row               ; 13 T
    ret                     ; 10 T
```

La rutina de restauración es idéntica con origen y destino intercambiados: lee del búfer, escribe a la pantalla. Cada rutina toma aproximadamente **1.400 T-states** para 16 filas.

### Presupuesto completo del fotograma

Calculemos el coste por fotograma para 8 sprites animados de 16x16 usando enmascaramiento OR+AND con guardado/restauración de fondo:

| Operación | Por sprite | 8 sprites |
|-----------|-----------|-----------|
| Restaurar fondo | ~1.400 T | 11.200 T |
| Guardar nuevo fondo | ~1.400 T | 11.200 T |
| Dibujar sprite (con máscara) | ~2.300 T | 18.400 T |
| **Total** | **~5.100 T** | **~40.800 T** |

En un Pentagon (71.680 T-states por fotograma): 40.800 T dejan **30.880 T** para lógica del juego, procesamiento de entrada, música y todo lo demás. A 25 fps tienes el doble de presupuesto (dos fotogramas por actualización), dando ~103.000 T-states para trabajo no relacionado con sprites. Esto es cómodo para un juego.

Si usas sprites compilados con máscara en su lugar:

| Operación | Por sprite | 8 sprites |
|-----------|-----------|-----------|
| Restaurar fondo | ~1.400 T | 11.200 T |
| Guardar nuevo fondo | ~1.400 T | 11.200 T |
| Dibujar sprite (compilado, con máscara) | ~1.088 T | 8.704 T |
| **Total** | **~3.888 T** | **~31.104 T** |

Eso ahorra casi 10.000 T-states por fotograma --- una mejora significativa que te compra más espacio para lógica de juego o más sprites.

### Orden de dibujo y superposición

Cuando múltiples sprites se superponen, el orden de dibujo importa. El enfoque correcto más simple:

1. Restaurar todos los fondos (en orden inverso de dibujo, para manejar correctamente las superposiciones).
2. Guardar todos los nuevos fondos.
3. Dibujar todos los sprites.

La restauración en orden inverso asegura que cuando dos sprites se superpusieron en el último fotograma, el búfer de guardado del sprite anterior (que capturó el fondo limpio) se restaura último, limpiando correctamente el área de superposición.

El razonamiento: si el sprite A fue dibujado encima del sprite B, el búfer de guardado de A contiene los píxeles de B. Restaurar A primero expone B, luego restaurar B revela el fondo limpio. La restauración en orden directo deja artefactos. Muchos juegos evitan esto previniendo la superposición o aceptando fallos menores.

---

## Optimizando los bucles internos

### Eliminando la gestión de punteros

Las rutinas anteriores gastan tiempo significativo en gestión de punteros: `inc de`, `inc l`, `dec l`, y la lógica de límite de DOWN_HL. Varias optimizaciones pueden reducir esta sobrecarga.

**Usar LDI en lugar de copia manual.** Para operaciones de guardado/restauración, una cadena LDI (Capítulo 3) copia un byte de (HL) a (DE), incrementa ambos, y decrementa BC --- todo en 16 T-states. Comparado con nuestro `ld a,(hl)` + `ld (de),a` + `inc de` + `inc l` manual a 24 T-states, LDI ahorra 8 T-states por byte. Para un sprite de 16x16 (32 bytes), eso son 256 T-states ahorrados por operación de guardado o restauración.

```z80
; Save background using LDI (partial unroll, 2 bytes per row)
; HL = screen address, DE = save buffer
;
save_bg_ldi:
    ld   b, 16              ;  7 T
.row:
    ldi                     ; 16 T   copy left byte
    ldi                     ; 16 T   copy right byte
    dec  l                  ;  4 T   \
    dec  l                  ;  4 T   /  LDI advanced L by 2, undo it

    ; DOWN_HL
    inc  h                  ;  4 T
    ld   a, h               ;  4 T
    and  7                  ;  7 T
    jr   nz, .no_boundary   ;  7 T
    ld   a, l               ;  4 T
    add  a, 32              ;  7 T
    ld   l, a               ;  4 T
    jr   c, .no_fix         ;  7 T
    ld   a, h               ;  4 T
    sub  8                  ;  7 T
    ld   h, a               ;  4 T
.no_fix:
.no_boundary:
    djnz .row               ; 13 T
    ret                     ; 10 T
```

Coste de fila en caso común: 16 + 16 + 4 + 4 + 4 + 4 + 7 + 7 + 13 = **75 T-states**. Para 16 filas: aproximadamente **1.200 T-states** --- una mejora valiosa sobre los 1.400 T-states del enfoque manual.

**Combinar guardado y dibujo.** En lugar de guardar-luego-dibujar como dos pasadas separadas sobre el área de pantalla, combínalas en una sola pasada: para cada byte, lee la pantalla (guárdalo), luego escribe los datos del sprite. Esto reduce a la mitad el número de operaciones de avance de fila y elimina un recorrido completo de DOWN_HL:

```z80
; Combined save-and-draw for masked sprite
; HL = screen address, DE = sprite data (mask, gfx pairs)
; IX = save buffer
;
save_and_draw_16x16:
    ld   b, 16              ;  7 T
.row:
    ; Left byte
    ld   a, (hl)            ;  7 T   read screen (for saving)
    ld   (ix+0), a          ; 19 T   save to buffer
    ld   c, a               ;  4 T

    ld   a, (de)            ;  7 T   load mask
    and  c                  ;  4 T   mask background
    inc  de                 ;  6 T
    ld   c, a               ;  4 T

    ld   a, (de)            ;  7 T   load graphic
    or   c                  ;  4 T   stamp sprite
    ld   (hl), a            ;  7 T   write to screen
    inc  de                 ;  6 T
    inc  l                  ;  4 T

    ; Right byte (similar)
    ld   a, (hl)            ;  7 T
    ld   (ix+1), a          ; 19 T
    ld   c, a               ;  4 T

    ld   a, (de)            ;  7 T
    and  c                  ;  4 T
    inc  de                 ;  6 T
    ld   c, a               ;  4 T

    ld   a, (de)            ;  7 T
    or   c                  ;  4 T
    ld   (hl), a            ;  7 T
    inc  de                 ;  6 T
    dec  l                  ;  4 T

    ; Advance IX and HL
    inc  ix                 ; 10 T
    inc  ix                 ; 10 T

    inc  h                  ;  4 T
    ld   a, h               ;  4 T
    and  7                  ;  7 T
    jr   nz, .no_boundary   ;  7 T
    ld   a, l               ;  4 T
    add  a, 32              ;  7 T
    ld   l, a               ;  4 T
    jr   c, .no_fix         ;  7 T
    ld   a, h               ;  4 T
    sub  8                  ;  7 T
    ld   h, a               ;  4 T
.no_fix:
.no_boundary:
    djnz .row               ; 13 T
    ret                     ; 10 T
```

Esto combina guardado y dibujo en una sola pasada. El coste por fila (caso común): aproximadamente **200 T-states**. Para 16 filas: aproximadamente **3.300 T-states** --- comparado con guardar separado (~1.200 T) + dibujar (~2.300 T) = 3.500 T-states. El ahorro es modesto (~200 T por sprite), pero se acumula con 8 sprites.

Para máximo rendimiento, desenrolla toda la rutina: sin bucle DJNZ, código explícito por fila con cruces de límite integrados en las filas 7 y 15. Esto elimina la sobrecarga de bucle y prueba de límite, llevando el total a aproximadamente **2.780 T-states** al coste de ~300 bytes de código por rutina de sprite.

---

## Agon Light 2: Sprites VDP por hardware

El Agon Light 2 adopta un enfoque fundamentalmente diferente. El eZ80 se comunica con un VDP (Video Display Processor) en un ESP32, que maneja todo el renderizado de sprites por hardware. La CPU sube bitmaps, luego emite comandos para posicionar, mostrar, ocultar y animar sprites. El VDP compone los sprites durante su propia pasada de renderizado, sin coste de CPU por píxel. Se soportan hasta 256 ranuras de sprite.

La secuencia de comandos VDU para definir y activar un sprite:

```
VDU 23, 27, 0, n                     ; Select sprite n
VDU 23, 27, 1, w, h, format          ; Create sprite: w x h pixels
; ... upload bitmap data ...
VDU 23, 27, 4, x_lo, x_hi, y_lo, y_hi  ; Set position
VDU 23, 27, 11                        ; Show sprite
```

En ensamblador eZ80, estos comandos se envían como secuencias de bytes al VDP vía `RST $10` (salida de carácter MOS). Cada comando es una secuencia de pares `ld a, byte : rst $10`.

### Mover un sprite

Una vez definido, mover un sprite es solo el comando de posición:

```z80
; Agon: Move sprite 0 to (x, y)
; Input: BC = x, DE = y
;
move_sprite:
    ld   a, 23 : rst $10
    ld   a, 27 : rst $10
    ld   a, 4  : rst $10    ; move command
    ld   a, 0  : rst $10    ; sprite number

    ld   a, c  : rst $10    ; x low
    ld   a, b  : rst $10    ; x high
    ld   a, e  : rst $10    ; y low
    ld   a, d  : rst $10    ; y high
    ret
```

El coste de CPU para mover un sprite es solo el coste de enviar ~10 bytes a través de la interfaz serial. A 1.152.000 baudios, cada byte toma aproximadamente 9 microsegundos, así que mover un sprite toma aproximadamente 90 microsegundos --- unos 1.660 T-states a 18,432 MHz. Mover 8 sprites: ~13.000 T-states. El VDP maneja toda la composición de píxeles, transparencia y gestión de fondo por hardware.

### Límites por línea de escaneo

El VDP tiene un límite práctico en píxeles de sprites por línea de escaneo horizontal. Cuando demasiados sprites se superponen en la misma línea, algunos pueden parpadear --- el mismo fenómeno visto en la NES y la Master System. Una guía razonable es de 8 a 12 sprites de 16x16 por línea de escaneo. Para 8 sprites distribuidos por la pantalla, es poco probable que alcances este límite.

### La compensación

El Agon elimina todo el problema de dibujo de sprites. Sin guardado/restauración, sin enmascaramiento, sin navegación de pantalla entrelazada. El coste es abstracción: sin trucos por píxel, sin manipulación creativa de datos, y dependencia de las capacidades del firmware del VDP. El Spectrum te obliga a construir todo desde cero. El Agon te libera para gastar ese esfuerzo en diseño de juego.

---

## Práctica: 8 sprites animados a 25 fps

### Implementación para Spectrum

Nuestro objetivo: 8 sprites animados de 16x16 con guardado/restauración de fondo, ejecutándose a 25 fps (actualizando cada 2 fotogramas) en un ZX Spectrum 128K.

**Arquitectura:**

Cada sprite tiene una estructura de datos:

```z80
; Sprite structure (12 bytes per sprite)
;
SPRITE_X        EQU 0       ; x coordinate (0-255)
SPRITE_Y        EQU 1       ; y coordinate (0-191)
SPRITE_OLD_X    EQU 2       ; previous x (for erase)
SPRITE_OLD_Y    EQU 3       ; previous y
SPRITE_FRAME    EQU 4       ; current animation frame (0-3)
SPRITE_DIR      EQU 5       ; direction / flags
SPRITE_DX       EQU 6       ; x velocity (signed)
SPRITE_DY       EQU 7       ; y velocity (signed)
SPRITE_GFX      EQU 8       ; pointer to sprite graphic data (2 bytes)
SPRITE_SAVE     EQU 10      ; pointer to background save buffer (2 bytes)

SPRITE_SIZE     EQU 12
NUM_SPRITES     EQU 8
```

**Ciclo por fotograma (cada 2 VBLANKs):**

```z80
main_loop:
    halt                    ; wait for VBLANK
    halt                    ; wait again (25 fps = every 2nd frame)

    ; Phase 1: Restore all backgrounds (reverse order)
    ld   ix, sprites + (NUM_SPRITES - 1) * SPRITE_SIZE
    ld   b, NUM_SPRITES
.restore_loop:
    call restore_sprite_bg
    ld   de, -SPRITE_SIZE
    add  ix, de
    djnz .restore_loop

    ; Phase 2: Update positions
    ld   ix, sprites
    ld   b, NUM_SPRITES
.update_loop:
    call update_sprite_position
    ld   de, SPRITE_SIZE
    add  ix, de
    djnz .update_loop

    ; Phase 3: Save backgrounds and draw (forward order)
    ld   ix, sprites
    ld   b, NUM_SPRITES
.draw_loop:
    call save_and_draw_sprite
    ld   de, SPRITE_SIZE
    add  ix, de
    djnz .draw_loop

    ; Phase 4: Game logic, input, sound
    call process_input
    call update_game_logic
    call update_sound

    jr   main_loop
```

**Presupuesto de ciclos:**

| Fase | Coste |
|-------|------|
| 2 x HALT | 0 T (esperando) |
| Restaurar 8 fondos | 8 x 1.200 = 9.600 T |
| Actualizar 8 posiciones | 8 x 200 = 1.600 T |
| Guardar + Dibujar 8 sprites | 8 x 3.300 = 26.400 T |
| Sobrecarga de bucle | ~2.000 T |
| **Total trabajo de sprites** | **~39.600 T** |
| **Disponible para lógica de juego** | **~103.000 T** |

Con un presupuesto de 2 fotogramas de 143.360 T-states (2 x 71.680 en Pentagon), tenemos aproximadamente 103.000 T-states para lógica de juego, entrada y sonido. Esto es generoso --- suficiente para IA de entidades (Capítulo 19), detección de colisiones con baldosas, reproducción de música y procesamiento de entrada.

Antes de dibujar cada sprite, calcula la dirección de pantalla desde (x, y) usando la rutina del Capítulo 2, y selecciona los datos pre-desplazados correctos basándote en `x AND $06` (para 4 niveles de desplazamiento). La lógica de selección de pre-desplazamiento del Método 3 se aplica directamente.

### Implementación para Agon

En el Agon, el bucle principal se vuelve trivialmente simple: espera VSync, actualiza posiciones, envía comandos de movimiento `VDU 23,27,4` para cada sprite, y procede a la lógica del juego. Sin guardado/restauración, sin enmascaramiento, sin cálculo de dirección de pantalla, sin navegación de filas entrelazadas. El VDP maneja todo.

El contraste es instructivo. En el Spectrum, el renderizado de sprites es el coste dominante --- 40.000 T-states por fotograma, donde cada ciclo ahorrado en el bucle interno se traduce directamente en más sprites o más lógica de juego. En el Agon, el renderizado de sprites es efectivamente gratuito desde la perspectiva de la CPU, y tu esfuerzo de ingeniería va al diseño de juego en lugar de empujar píxeles. Ambos enfoques tienen sus satisfacciones.

---

## Resumen

- **Los sprites XOR** son el método más simple: XOR para dibujar, XOR de nuevo para borrar. ~1.700 T-states para dibujar un sprite de 16x16. Sin máscara, sin guardado de fondo necesario. La calidad visual es pobre (píxeles invertidos sobre detalle de fondo). Buenos para cursores, balas y marcadores de depuración.

- **Los sprites con máscara OR+AND** son el estándar de la industria. Cada byte pasa por una secuencia AND-con-máscara, OR-con-gráfico que produce transparencia limpia. ~2.300 T-states para un sprite de 16x16. Esto es lo que usan la mayoría de los juegos comerciales de Spectrum.

- **Los sprites pre-desplazados** eliminan el coste de desplazamiento por píxel almacenando 4 u 8 copias pre-computadas y desplazadas de los datos del sprite. El tiempo de dibujo es el mismo que la rutina con máscara. El coste de memoria escala de 4x (4 desplazamientos, resolución de 2 píxeles) a 8x (8 desplazamientos, resolución de píxel completo). La compensación estándar de memoria-vs-velocidad.

- **Los sprites de pila (método PUSH)** son la salida bruta más rápida: ~810 T-states para un sprite de 16x16. Requiere DI/EI, gestión explícita de SP por fila, y produce rectángulos sólidos (sin enmascaramiento). Mejor para juegos con fondos simples.

- **Los sprites compilados** convierten el sprite en código ejecutable. Cada byte de píxel se convierte en una instrucción `LD (HL),n`. ~570 T-states sin enmascaramiento, ~1.088 T-states con enmascaramiento compilado. El método con máscara más rápido, al coste de gran tamaño de código. La animación requiere rutinas compiladas separadas por fotograma.

- **Los rectángulos sucios** con guardado/restauración de fondo son la técnica estándar para animación de sprites. Guarda el fondo antes de dibujar, restáuralo antes de dibujar el siguiente fotograma. Restaura en orden inverso de dibujo para manejar correctamente los sprites superpuestos. El enfoque combinado de guardar-y-dibujar reduce el coste por sprite a ~3.300 T-states.

- **8 sprites a 25 fps** en un Spectrum 128K cuestan aproximadamente 40.000 T-states por ciclo de actualización (cada 2 fotogramas), dejando ~103.000 T-states para lógica de juego --- un presupuesto cómodo para un juego real.

- **Los sprites por hardware del Agon Light 2** eliminan todo el problema de renderizado. Define los sprites una vez, muévelos con comandos VDU. El coste de CPU es insignificante. La compensación es abstracción: ganas rendimiento pero pierdes la capacidad de hacer trucos por píxel con los datos del sprite.

- La elección del método de sprite depende de los requisitos de tu juego: complejidad del fondo, número de sprites, necesidades de animación, memoria disponible y tasa de fotogramas objetivo. La mayoría de los juegos de Spectrum usan enmascaramiento OR+AND con pre-desplazamiento y rectángulos sucios. Las producciones del demoscene y los juegos críticos en rendimiento recurren a sprites compilados o al método PUSH.

---

## Inténtalo tú mismo

1. **Implementa los seis métodos.** Toma un diseño de sprite simple de 8x8 e implementa versiones XOR, con máscara y compiladas. Usa el arnés de temporización por color de borde del Capítulo 1 para comparar sus costes de dibujo. La diferencia debería ser claramente visible.

2. **Generador de pre-desplazamiento.** Escribe una utilidad (en Python, Processing, o ensamblador Z80) que tome un sprite con máscara y genere 4 versiones pre-desplazadas. Almacénalas en memoria y escribe una rutina de dibujo que seleccione la versión correcta basándose en la coordenada x.

3. **Demo de guardado/restauración de fondo.** Pon un sprite con máscara sobre un fondo con patrón (el tablero de ajedrez de la práctica del Capítulo 2). Mueve el sprite con entrada de teclado. Verifica que el fondo se restaura correctamente mientras el sprite se mueve. Luego añade un segundo sprite y verifica que las áreas superpuestas se manejan correctamente.

4. **El desafío de 8 sprites.** Implementa el sistema completo de 8 sprites con guardado/restauración de fondo y animación. Comienza con el enfoque OR+AND con máscara. Mide el presupuesto de ciclos con colores de borde. Si tienes espacio, cambia a sprites compilados con máscara y mide la mejora.

5. **Comparación con Agon.** Si tienes un Agon Light 2, implementa la misma animación de 8 sprites usando sprites por hardware del VDP. Compara la complejidad del código y el presupuesto de CPU disponible para lógica de juego.

---

> **Fuentes:** Spectrum graphics programming folklore, widely documented across the ZX community; Chapter 3 of this book for PUSH tricks and self-modifying code; Chapter 2 for screen layout and DOWN_HL; Agon Light 2 VDP documentation (Quark firmware, FabGL sprite API); the game-dev chapters of *book-plan.md* for the six-method framework and practical targets.
