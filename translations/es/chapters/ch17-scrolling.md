# Capítulo 17: Desplazamiento

> "La pantalla tiene 256 píxeles de ancho. El nivel tiene 8,000. De alguna manera, el jugador debe recorrerlo."

---

Cada juego de desplazamiento lateral necesita mover el mundo. El jugador corre hacia la derecha, el fondo se desplaza hacia la izquierda. Parece simple. En hardware con un registro de desplazamiento -- la NES, la Mega Drive, el Agon Light 2 -- *es* simple: escribes un desplazamiento, y el hardware hace el resto. En el ZX Spectrum, no hay registro de desplazamiento. No hay asistencia de hardware de ningún tipo. Para desplazar la pantalla, mueves los bytes tú mismo. Los 6,144.

Este capítulo recorre todos los métodos prácticos de desplazamiento en el Spectrum, del más barato al más caro: desplazamiento de atributos (768 bytes, trivial), desplazamiento vertical de píxeles (complicado debido al diseño de pantalla entrelazado del Capítulo 2), desplazamiento horizontal de píxeles (caro -- cada byte en cada fila debe ser rotado), y el método combinado que los juegos reales usan para obtener un desplazamiento horizontal suave dentro de un presupuesto manejable. Contaremos cada T-state, construiremos tablas comparativas, y mostraremos cómo el truco de la pantalla sombra en el 128K hace que todo sea libre de tearing.

Luego veremos cómo el Agon Light 2 maneja el mismo problema con desplazamientos de hardware y soporte de tilemaps -- un contraste útil que muestra lo que "la misma ISA con hardware diferente" realmente significa en la práctica.

---

## El presupuesto

Antes de escribir una sola instrucción, establezcamos con qué estamos trabajando.

En un Pentagon (el modelo de temporización al que apuntan la mayoría de las demos y juegos de Spectrum), un fotograma son **71,680 T-states**. En un 48K/128K Spectrum estándar, son 69,888. Usaremos la cifra del Pentagon a lo largo del capítulo, pero el análisis se aplica a ambos -- la diferencia es de aproximadamente el 2.5%.

Un desplazamiento de pantalla completa significa mover datos a través de los 6,144 bytes de memoria de pantalla (y posiblemente los 768 bytes de memoria de atributos). La pregunta es siempre la misma: ¿podemos hacerlo en un fotograma, y si es así, cuántos T-states quedan para todo lo demás -- lógica de juego, dibujo de sprites, música, entrada?

Aquí está el coste bruto de simplemente *tocar* cada byte en el área de píxeles, usando diferentes métodos:

| Método | Por byte | 6,144 bytes | % del fotograma |
|--------|----------|-------------|------------|
| `ldir` | 21 T | 129,003 T | 180% |
| cadena `ldi` | 16 T | 98,304 T | 137% |
| `ld a,(hl)` + `ld (de),a` + `inc hl` + `inc de` | 24 T | 147,456 T | 206% |
| `push` (2 bytes) | 5.5 T/byte | 33,792 T | 47% |

Los tres primeros métodos no pueden mover el área de píxeles completa en un solo fotograma. Incluso las cadenas `ldi`, el método de copia más rápido después de PUSH, exceden el presupuesto en un 37%. Y el desplazamiento no es solo copiar -- el desplazamiento horizontal requiere una operación de *rotación* en cada byte, lo que añade al coste por byte.

Por eso el desplazamiento en el Spectrum es un problema de diseño, no solo un problema de programación. No puedes forzar un desplazamiento de píxeles de pantalla completa a 50fps por fuerza bruta. Debes elegir tu método basándote en lo que tu juego puede permitirse.

---

## Desplazamiento vertical de píxeles

El desplazamiento vertical mueve el contenido de la pantalla hacia arriba o hacia abajo una o más filas de píxeles. Conceptualmente es simple: copiar cada fila a la posición de la fila superior (para desplazar hacia arriba) o inferior (para desplazar hacia abajo). En un framebuffer lineal, esto sería una sola copia de bloque. En el Spectrum, el diseño de pantalla entrelazado (Capítulo 2) lo hace considerablemente más interesante.

### El problema del entrelazado

Recuerda la estructura de dirección de pantalla del Capítulo 2:

```
High byte:  0 1 0 T T S S S
Low byte:   L L L C C C C C
```

Donde TT = tercio (0--2), SSS = línea de escaneo dentro de la celda de caracteres (0--7), LLL = fila de caracteres dentro del tercio (0--7), CCCCC = byte de columna (0--31).

Para desplazar hacia arriba un píxel, necesitas copiar el contenido de la fila N a la fila N-1, para cada fila de 1 a 191. Las direcciones de origen y destino para filas de píxeles adyacentes *no* están separadas por un desplazamiento constante. Dentro de una celda de caracteres, las filas consecutivas difieren en $0100 en el byte alto (simplemente `INC H` / `DEC H`). Pero en los límites de las celdas de caracteres -- cada 8ª fila -- la relación cambia: debes ajustar L en 32 y resetear los bits de línea de escaneo en H. En los límites de tercios (cada 64ª fila), el ajuste es diferente de nuevo.

### El algoritmo: desplazar hacia arriba un píxel

El enfoque que trabaja con el entrelazado, en lugar de contra él, usa la estructura de contadores divididos del Capítulo 2. Mantén dos punteros (origen y destino) y avanza ambos usando la jerarquía natural de la pantalla: 3 tercios, 8 filas de caracteres por tercio, 8 líneas de escaneo por fila de caracteres. Dentro de cada celda de caracteres, moverse entre líneas de escaneo es simplemente `INC H` / `INC D` en el origen y destino. En los límites de filas de caracteres, resetea los bits de línea de escaneo y añade 32 a L. En los límites de tercios, añade 8 a H y resetea L. El bucle interno copia 32 bytes por fila con LDIR o una cadena LDI, y el avance de punteros se integra en la estructura del bucle externo.

### Análisis de coste

Para cada una de las 191 copias de fila, debemos copiar 32 bytes del origen al destino. Usando LDIR:

- Por fila: 32 bytes x 21 T-states - 5 = 667 T-states para el LDIR, más la sobrecarga de gestión de punteros.
- Gestión de punteros (guardar/restaurar origen y destino, avanzar línea de escaneo): aproximadamente 60 T-states por fila dentro de una celda de caracteres, más en los límites.

**Total con LDIR: aproximadamente 143,000 T-states.** Eso es aproximadamente **dos fotogramas completos**. Un desplazamiento vertical de píxeles de una fila usando LDIR no cabe en un solo fotograma.

Podemos hacerlo mejor. Reemplaza el LDIR con una cadena LDI -- 32 instrucciones LDI por fila:

- Por fila: 32 x 16 = 512 T-states para los LDIs, más ~50 T-states de gestión de punteros.
- Total: 191 x 562 = **107,342 T-states.** Aún excede el presupuesto en aproximadamente un 50%.

El truco PUSH es difícil de aplicar aquí porque necesitamos copiar *entre* dos áreas no contiguas con una relación no constante. PUSH escribe en direcciones contiguas descendentes, lo que no coincide con el patrón entrelazado de origen/destino.

### Desplazamiento parcial: el enfoque práctico

La realidad es que la mayoría de los juegos no desplazan la pantalla completa de 192 líneas. Un juego típico reserva:

- Las 2 filas de caracteres superiores (16 píxeles) para una barra de estado -- no se desplazan.
- La fila de caracteres inferior (8 píxeles) para la línea de puntuación -- no se desplaza.
- Zona central: 21 filas de caracteres = 168 filas de píxeles = el área de juego con desplazamiento.

168 filas de desplazamiento vertical de píxeles con cadenas LDI: 168 x 562 = **94,416 T-states**, o el 132% de un fotograma. Todavía demasiado para un solo fotograma si quieres tiempo para cualquier otra cosa.

Por eso el desplazamiento vertical de píxeles puro a 1px/fotograma es raro en los juegos de Spectrum. Los enfoques comunes son:

1. **Desplazar 8 píxeles (una fila de caracteres):** Mover los atributos y los datos de píxeles alineados a caracteres. Esto es mucho más barato porque solo copias 21 filas de caracteres x 8 líneas de escaneo = 168 filas, pero puedes usar un truco de copia de bloques: dentro de cada tercio, las filas de caracteres son contiguas en bloques. Coste: alrededor de 40,000--50,000 T-states con LDIR. Factible.

2. **Desplazar 1 píxel usando un contador:** Desplazar 1px por fotograma visualmente combinando un desplazamiento a nivel de carácter (barato, cada 8 fotogramas) con un contador de desplazamiento de píxeles (dibujar nuevo contenido con un desplazamiento dentro de la celda de 8px de caracteres). Cubriremos este enfoque combinado en la sección de desplazamiento horizontal a continuación, porque es mucho más comúnmente necesario allí.

3. **Usar la pantalla sombra (solo 128K):** Dibujar el contenido desplazado en un búfer trasero, luego intercambiar. Esto elimina el tearing y te permite distribuir el trabajo entre fotogramas. Lo cubrimos más adelante en el capítulo.

### Desplazar 8 píxeles (una fila de caracteres)

Desplazar una fila de caracteres completa es dramáticamente más barato porque el origen y el destino están relacionados por un desplazamiento simple dentro de cada tercio. Las filas de caracteres dentro de un tercio están espaciadas 32 bytes en L. Así que desplazar una fila de caracteres hacia arriba significa copiar de L+32 a L, para cada línea de escaneo y cada tercio.

Para desplazar el área de juego una fila de caracteres, la idea clave es que dentro de una sola línea de escaneo, las filas de caracteres se almacenan de forma contigua (32 bytes de separación). La línea de escaneo 0 de las filas de caracteres 0--7 en un tercio vive en `$xx00`, `$xx20`, `$xx40`, ..., `$xxE0`. Desplazar N filas de caracteres hacia arriba una posición dentro de una sola línea de escaneo es, por tanto, una sola copia de bloque de (N-1) x 32 bytes.

Para un área de juego de 20 filas de caracteres, los datos de una línea de escaneo son 20 x 32 = 640 bytes. Desplazar esa línea de escaneo significa copiar 19 x 32 = 608 bytes hacia adelante 32 posiciones. Hacemos esto para cada una de las 8 líneas de escaneo, manejando los límites de tercios por separado.

**Coste estimado:** 8 líneas de escaneo x ~12,700 T-states por línea de escaneo (608 bytes vía LDIR) + manejo de límites de tercios = aproximadamente **105,000 T-states**. Eso es el 146% de un fotograma.

Incluso el desplazamiento de filas de caracteres del área de juego completa en un fotograma es ajustado. Los juegos manejan esto de las siguientes formas:

- **Desplazar durante el período de blanking (borde).** Los bordes superior e inferior en un Pentagon dan aproximadamente 14,000 T-states de tiempo libre donde no ocurre contención.
- **Dividir entre dos fotogramas.** Desplazar la mitad superior en un fotograma, la mitad inferior en el siguiente. El efecto visual es un desplazamiento de 25fps con saltos de 8 píxeles.
- **Usar la pantalla sombra** (ver más adelante).

---

## Desplazamiento horizontal de píxeles

El desplazamiento horizontal es el pan de cada día de los juegos de desplazamiento lateral: el mundo se mueve hacia la izquierda o la derecha mientras el jugador camina. Y es el tipo de desplazamiento más caro en el Spectrum, porque requiere no solo copiar bytes sino *rotarlos*.

### Por qué el desplazamiento horizontal es caro

Cuando desplazas la pantalla hacia la izquierda un píxel, cada byte en cada fila debe rotar sus bits hacia la izquierda una posición, y el bit que sale por el borde izquierdo de un byte debe convertirse en el bit más a la derecha de su vecino izquierdo. Esto es una cadena de rotación-y-acarreo a través de los 32 bytes de cada fila.

La instrucción `RL` (rotar a la izquierda a través del acarreo) del Z80 es la herramienta para esto. Para un desplazamiento hacia la izquierda, cada píxel se mueve una posición a la izquierda. El bit 7 es el píxel más a la izquierda en un byte, el bit 0 el más a la derecha. Desplazar a la izquierda significa que el bit 7 de cada byte sale y debe entrar en el bit 0 del byte a su izquierda. La bandera de acarreo conecta bytes adyacentes, así que procesamos la fila de **derecha a izquierda**:

```z80
; Scroll one pixel row left by 1 pixel
; HL points to byte 31 (rightmost) of the row
;
; Process right to left. Each byte rotates left; carry propagates.
;
    or   a                    ; 4 T   clear carry (no pixel entering from right)

    ; Byte 31 (rightmost)
    rl   (hl)                 ; 15 T  shift left, bit 7 -> carry, carry -> bit 0
    dec  hl                   ; 6 T
    ; Byte 30
    rl   (hl)                 ; 15 T
    dec  hl                   ; 6 T
    ; ...repeat for bytes 29 down to 0...
    ; Byte 0 (leftmost)
    rl   (hl)                 ; 15 T  bit 7 of byte 0 is lost (scrolled off screen)
```

Cada byte cuesta: 15 (RL (HL)) + 6 (DEC HL) = **21 T-states** por byte. Para 32 bytes por fila: 32 x 21 - 6 = **666 T-states** por fila (no necesitamos el DEC HL final).

En realidad, el primer byte necesita `OR A` (4 T) para limpiar el acarreo. Así que una fila cuesta: 4 + 32 x 15 + 31 x 6 = 4 + 480 + 186 = **670 T-states**.

Para 192 filas: 192 x 670 = **128,640 T-states**. Eso es el **179% de un fotograma**.

Un desplazamiento horizontal de píxeles de pantalla completa de un píxel no cabe en un solo fotograma usando cadenas RL. Y esto es *solo la rotación* -- no hemos dibujado ningún contenido nuevo en el borde derecho.

### El cálculo completo del presupuesto

Expongamos el coste completo por fila con toda la sobrecarga de navegar la pantalla entrelazada:

| Operación | T-states por fila |
|-----------|-----------------|
| Establecer HL al inicio de fila (o avanzar desde la anterior) | ~15 |
| Establecer HL al byte más a la derecha: `ld a, l : or $1F : ld l, a` | 15 |
| Limpiar acarreo: `or a` | 4 |
| 32 x `rl (hl)` | 480 |
| 31 x `dec hl` (entre bytes) | 186 |
| Avanzar a la siguiente fila (`inc h` o cruce de límite) | 4--77 |
| **Total por fila (típico)** | **~704** |

Para 192 filas: 192 x 704 = **135,168 T-states** = **189% de un fotograma**.

Para un área de juego de 168 filas: 168 x 704 = **118,272 T-states** = **165% de un fotograma**.

No hay forma de hacer un desplazamiento horizontal de un solo píxel de pantalla completa en un fotograma con métodos estándar en un Z80 a 3.5 MHz. Esta es la restricción fundamental que impulsa cada técnica de desplazamiento en este capítulo.

### ¿Podemos hacerlo mejor?

Podrías pensar que el desenrollado o modos de direccionamiento alternativos ayudarían. No lo hacen. `RL (IX+d)` cuesta 23 T-states -- *más* que `RL (HL)` con 15 T. Una secuencia de cargar-rotar-almacenar (`LD A,(HL) : RLA : LD (HL),A` a 18 T por byte, más 6 T por `DEC HL` = 24 T) también es más lenta. La cadena `RL (HL) : DEC HL` a 21 T/byte es esencialmente óptima para el desplazamiento horizontal de píxeles en el Z80.

**Conclusión:** La única forma de hacer el desplazamiento horizontal asequible es reducir el número de filas o bytes que desplazas.

---

## Desplazamiento de atributos (caracteres)

Si el desplazamiento de píxeles es caro, el desplazamiento de atributos es casi gratuito en comparación. El desplazamiento de atributos mueve la pantalla en saltos de 8 píxeles (una celda de caracteres). Solo mueves los 768 bytes de memoria de atributos y los bloques de píxeles correspondientes alineados a caracteres -- o, más comúnmente, mueves solo los atributos y redibujas el área de juego desde un tilemap.

### Desplazar atributos con LDIR

El área de atributos es lineal: 32 bytes por fila, 24 filas, secuenciales de `$5800` a `$5AFF`. Desplazar a la izquierda una columna de carácter significa copiar los bytes 1--31 a las posiciones 0--30 en cada fila, luego escribir la nueva columna en la posición 31.

Para el área de atributos completa de 24 filas:

```z80
; Scroll all attributes left by 1 character column
; New column data in a 24-byte table at new_col_data
;
scroll_attrs_left:
    ld   hl, $5801          ; 10 T  source: column 1
    ld   de, $5800          ; 10 T  dest: column 0
    ld   bc, 767            ; 10 T  768 - 1 bytes
    ldir                    ; 767*21 + 16 = 16,123 T

    ; Now fill the rightmost column with new data
    ld   hl, new_col_data   ; 10 T
    ld   de, $581F          ; 10 T  column 31 of row 0
    ld   b, 24              ; 7 T
.fill_col:
    ld   a, (hl)            ; 7 T
    ld   (de), a            ; 7 T
    inc  hl                 ; 6 T
    ; advance DE by 32 (next attribute row)
    ld   a, e               ; 4 T
    add  a, 32              ; 7 T
    ld   e, a               ; 4 T
    jr   nc, .no_carry      ; 12/7 T
    inc  d                  ; 4 T
.no_carry:
    djnz .fill_col          ; 13 T
    ret

    ; Total LDIR: ~16,123 T
    ; Total column fill: ~24 * 50 = ~1,200 T
    ; Grand total: ~17,323 T = 24.2% of frame
```

**17,323 T-states para un desplazamiento de atributos de pantalla completa.** Eso es aproximadamente el 24% de un fotograma. Compara esto con los 135,000+ T-states de un desplazamiento de píxeles. El desplazamiento de atributos es casi 8 veces más barato.

La trampa: el desplazamiento salta 8 píxeles a la vez. El resultado visual es tosco y brusco. Para scrollers de texto en demos, esto suele ser aceptable -- el espectador lee el texto, no la suavidad. Para un juego, los saltos de 8 píxeles se sienten terribles. Ahí es donde entra el método combinado.

---

## El método combinado: desplazamiento de carácter + desplazamiento de píxeles

Esta es la técnica que la mayoría de los juegos de desplazamiento lateral del Spectrum realmente usan. La idea es simple y poderosa:

1. Mantener un contador de **desplazamiento de píxeles** de 0 a 7. Cada fotograma, incrementar el desplazamiento.
2. Cuando el desplazamiento llega a 8, resetearlo a 0 y realizar un **desplazamiento de atributos/caracteres** -- la operación barata.
3. En cada fotograma, renderizar el área de juego con el desplazamiento de píxeles actual aplicado. Este desplazamiento mueve toda la pantalla de 0 a 7 píxeles dentro de las posiciones de columna de carácter actuales.

El desplazamiento de píxeles se puede aplicar de dos formas:

**Método A: Rotar la nueva columna.** Solo rotar la columna de datos de píxeles (la columna que está entrando en la vista) según el desplazamiento actual. El resto de la pantalla se dibuja desde baldosas con alineación de carácter. Esto funciona cuando tienes un renderizador de baldosas que redibuja desde un mapa.

**Método B: Desplazamiento virtual tipo hardware.** Mantener un desplazamiento de renderizado que controla dónde dentro de cada celda de caracteres comienzan los datos de baldosa. Esto es conceptualmente similar a un registro de desplazamiento de hardware pero implementado en software.

El Método A es más común en la práctica. Recorrámoslo.

### Cómo funciona

Imagina que el área de juego tiene 20 caracteres (160 píxeles) de ancho y 20 caracteres de alto. Los datos del nivel son un tilemap donde cada baldosa es de 8x8 píxeles (una celda de caracteres).

El estado del desplazamiento consiste en:
- `scroll_tile_x`: qué columna de baldosa está en el borde izquierdo de la pantalla (entero, avanza en 1 cada 8 fotogramas).
- `scroll_pixel_x`: desplazamiento de píxeles dentro de la baldosa actual (0--7, avanza en 1 cada fotograma).

Cada fotograma:

1. **Si `scroll_pixel_x` es 0:** Redibujar el área de juego completa desde el tilemap con alineación de carácter. Esto es un renderizador de baldosas, que podemos hacer rápido usando LDIR o cadenas LDI (cada fila de baldosa es 1 byte o unos pocos bytes de datos copiados a la dirección de pantalla correcta). Coste: 20 columnas x 20 filas x ~100 T por baldosa = ~40,000 T. Asequible.

2. **Si `scroll_pixel_x` es 1--7:** Redibujar el área de juego desplazada `scroll_pixel_x` píxeles. Para la mayor parte del área de juego, las baldosas están alineadas a caracteres y se pueden dibujar normalmente -- el desplazamiento de píxeles solo afecta a las **columnas visible más a la izquierda y más a la derecha**, donde una baldosa es parcialmente visible.

Espera -- esa es la interpretación eficiente, pero requiere un renderizador de baldosas que recorte en límites sub-carácter. El enfoque más simple (y más común) es:

### El método combinado simple

1. Cada 8 fotogramas, realizar un desplazamiento a nivel de carácter (LDIR de los datos de atributos y píxeles hacia la izquierda una columna). Coste: ~17,000 T para atributos + ~40,000 T para datos de píxeles = ~57,000 T. Se hace una vez cada 8 fotogramas.

2. Cada fotograma, rotar una **ventana estrecha** 1 píxel. Esta ventana tiene solo 1 columna (32 bytes) o 2 columnas (64 bytes) de ancho -- la costura entre los datos antiguos y la columna que está llegando.

3. **Entre desplazamientos de carácter**, la pantalla muestra la última posición desplazada a nivel de carácter con un desplazamiento de 0--7 píxeles aplicado a la columna del borde. El jugador percibe un desplazamiento suave de 1 píxel por fotograma.

Aquí está el desglose de coste por fotograma:

| Operación | T-states | Frecuencia |
|-----------|----------|-----------|
| Desplazamiento de carácter (área de juego completa) | ~57,000 | Cada 8° fotograma |
| Rotación de píxeles de 1--2 columnas de borde (20 filas x 2 cols x 21 T/byte x 8 líneas de escaneo) | ~6,720 | Cada fotograma |
| Dibujar nueva columna de baldosa en borde derecho | ~5,000 | Cada 8° fotograma |
| Actualización de columna de atributos | ~1,200 | Cada 8° fotograma |

**En 7 de cada 8 fotogramas:** ~6,720 T-states para la rotación de píxeles del borde. Eso es menos del 10% del presupuesto de fotograma. Mucho espacio para lógica de juego, sprites y música.

**En cada 8° fotograma:** ~6,720 + 57,000 + 5,000 + 1,200 = ~69,920 T-states. Eso es el 97.5% del presupuesto de fotograma. Ajustado, pero factible -- especialmente si divides el desplazamiento de carácter entre dos fotogramas o usas la pantalla sombra.

### Implementación: la rotación de píxeles de la columna de borde

La rutina interna clave rota 1 o 2 columnas de datos de píxeles 1 píxel. Para una ventana de 2 columnas (16 píxeles), cada fila tiene 2 bytes que rotar:

```z80
; Shift 2 bytes left by 1 pixel with carry propagation
; HL points to the right byte of the pair
;
    or   a                ; 4 T    clear carry
    rl   (hl)             ; 15 T   right byte: shift left, bit 7 -> carry
    dec  hl               ; 6 T
    rl   (hl)             ; 15 T   left byte: carry -> bit 0, bit 7 lost
                          ; total: 40 T per row (for 2-byte window)
```

Para 160 filas (20 filas de caracteres x 8 líneas de escaneo): 160 x 40 = **6,400 T-states**. Con sobrecarga de avance de punteros (~20 T por fila), el total es aproximadamente **9,600 T-states** por fotograma. Muy asequible.

### El pipeline de renderizado

Aquí está la secuencia completa por fotograma para un scroller horizontal combinado:

```z80
frame_loop:
    halt                         ; wait for interrupt

    ; --- Always: advance pixel offset ---
    ld   a, (scroll_pixel_x)
    inc  a
    cp   8
    jr   nz, .no_char_scroll

    ; --- Every 8th frame: character scroll ---
    xor  a                       ; reset pixel offset to 0
    ld   (scroll_pixel_x), a

    ; Advance tile position
    ld   hl, (scroll_tile_x)
    inc  hl
    ld   (scroll_tile_x), hl

    ; Scroll pixel data left by 1 column (8 pixels)
    call scroll_pixels_left_char

    ; Scroll attributes left by 1 column
    call scroll_attrs_left

    ; Draw new tile column on right edge
    call draw_right_column

    jr   .scroll_done

.no_char_scroll:
    ld   (scroll_pixel_x), a

    ; Shift the edge columns by 1 pixel
    call shift_edge_columns

.scroll_done:
    ; --- Game logic, sprites, music ---
    call update_entities
    call draw_sprites
    call play_music

    jr   frame_loop
```

Este es el esqueleto de un juego de desplazamiento lateral real del Spectrum. La idea clave es que el desplazamiento suave de 1 píxel se logra *sin* rotar toda la pantalla en cada fotograma. El costoso desplazamiento a nivel de carácter ocurre solo una vez cada 8 fotogramas, y el trabajo por fotograma es mínimo.

---

## Desplazar los datos de píxeles una columna de carácter

El desplazamiento de píxeles a nivel de carácter (paso 2 en el pipeline anterior) desplaza 8 píxeles de datos hacia la izquierda en cada fila. Como 8 píxeles = 1 byte, esto es una copia a *nivel de byte*, no una rotación a nivel de bit. Los 32 bytes de cada fila se desplazan a la izquierda 1 byte: byte[1] va a byte[0], byte[2] va a byte[1], ..., byte[31] va a byte[30], y byte[31] se limpia o se llena con datos nuevos.

Para una sola fila, esto es un LDIR de 31 bytes:

```z80
; Shift one pixel row left by 8 pixels (1 byte)
; HL = address of byte 1 (source), DE = address of byte 0 (dest)
; BC = 31
;
    ldir                     ; 31*21 - 5 = 646 T per row... wait.
                             ; Actually: 30*21 + 16 = 646 T. Yes.
```

Para el área de juego completa (168 filas): 168 x 646 = 108,528 T-states + sobrecarga de navegación de filas.

Un mejor enfoque aprovecha el hecho de que dentro de cada línea de escaneo de una fila de caracteres, los bytes son contiguos. Para 20 columnas de caracteres, los datos de una línea de escaneo son 20 bytes contiguos. Desplazar esa línea de escaneo a la izquierda 1 byte significa un LDIR de 19 bytes:

```z80
; Scroll one scan line of the play area left by 1 character column
; Play area is 20 columns wide (columns 2-21, for example)
; Source: column 3, Dest: column 2, count: 19
;
    ld   hl, row_addr + 3    ; source = byte 3 of this scan line
    ld   de, row_addr + 2    ; dest   = byte 2
    ld   bc, 19              ; 19 bytes to copy
    ldir                     ; 18*21 + 16 = 394 T
```

Para 160 filas: 160 x 394 = 63,040 T-states. Suma ~20 T por fila para la navegación de punteros: 160 x 414 = **66,240 T-states**. Eso es el 92% de un fotograma. Factible pero ajustado en el presupuesto "cada 8° fotograma".

Con cadenas LDI (19 LDIs por fila): 19 x 16 = 304 T por fila. Para 160 filas: 160 x 324 = **51,840 T-states** = 72% de un fotograma. Ahora nos queda un 28% para dibujar la nueva columna y actualizar los atributos.

---

## El truco de la pantalla sombra

El ZX Spectrum 128K tiene una característica que transforma el problema del desplazamiento: **dos búferes de pantalla**. La pantalla estándar vive en `$4000` en la página 5 (siempre mapeada en `$4000`--`$7FFF`). La pantalla sombra vive en `$C000` en la página 7 (mapeada en `$C000`--`$FFFF` cuando la página 7 está conmutada).

El puerto `$7FFD` controla qué pantalla se muestra:

```z80
; Bit 3 of port $7FFD selects the display screen:
;   Bit 3 = 0: display page 5 (standard screen at $4000)
;   Bit 3 = 1: display page 7 (shadow screen at $C000)

    ld   a, (current_bank)
    or   %00001000           ; set bit 3: display shadow screen
    ld   bc, $7FFD
    out  (c), a
```

El truco para el desplazamiento:

1. **Fotograma N:** El jugador ve la pantalla estándar (página 5). Mientras tanto, tú dibujas el contenido desplazado del *siguiente* fotograma en la pantalla sombra (página 7, en `$C000`).
2. **Fotograma N+1:** Intercambias la pantalla a la pantalla sombra. El jugador ahora ve el fotograma recién dibujado sin tearing. Mientras tanto, empiezas a dibujar el fotograma N+2 en la ahora oculta pantalla estándar.

Este enfoque de doble búfer elimina el tearing completamente y te da un fotograma completo (o más) para preparar cada fotograma desplazado. El coste es que necesitas mantener dos estados de pantalla completos, y cada "desplazamiento" es en realidad un redibujado completo del área de juego en el búfer trasero.

```z80
; Flip displayed screen and return back buffer address in HL
;
; screen_flag:  0 = showing page 5, drawing to page 7
;               1 = showing page 7, drawing to page 5
;
flip_screens:
    ld   a, (screen_flag)
    xor  1                   ; 4 T   toggle
    ld   (screen_flag), a

    ld   hl, $C000           ; assume drawing to page 7
    or   a
    jr   z, .show_page5

    ; Now showing page 7, draw to page 5
    ld   hl, $4000
    ld   a, (current_bank)
    or   %00001000           ; bit 3 set: display page 7
    jr   .do_flip

.show_page5:
    ld   a, (current_bank)
    and  %11110111           ; bit 3 clear: display page 5

.do_flip:
    ld   bc, $7FFD
    out  (c), a
    ld   (current_bank), a
    ret                      ; HL = back buffer address
```

### Estrategia de desplazamiento con pantalla sombra

Con doble búfer, el enfoque de desplazamiento cambia:

**En lugar de desplazar la pantalla activa in situ** (lo que causa tearing y debe completarse dentro de un fotograma), **redibujas el área de juego desde el tilemap** en el búfer trasero en la nueva posición de desplazamiento. Esto es fundamentalmente diferente. No estás *moviendo* datos de pantalla existentes -- estás *renderizando de nuevo* desde el mapa.

Esto es más trabajo por fotograma (redibujas toda el área de juego, no solo la desplazas), pero tiene ventajas significativas:

1. **Sin tearing.** El jugador nunca ve una pantalla a medio desplazar.
2. **Sin rotación de columna de borde.** Renderizas cada baldosa en su desplazamiento sub-carácter correcto directamente.
3. **Velocidad de desplazamiento flexible.** Puedes desplazar 1, 2 o 3 píxeles por fotograma sin cambiar la lógica de renderizado.
4. **Código más simple.** Un renderizador de baldosas es más simple que un scroller combinado de rotación-y-copia.

El coste de un redibujado completo del área de juego desde baldosas depende de tu renderizador de baldosas. Con 20 x 20 baldosas, cada baldosa siendo 8 bytes (8 líneas de escaneo x 1 byte), y usando cadenas LDI:

- 400 baldosas x 8 bytes x 16 T por LDI = 51,200 T-states para la salida de datos.
- Más búsquedas de direcciones de baldosas y cálculos de direcciones de pantalla: ~20 T por baldosa x 400 = 8,000 T.
- **Total: ~59,200 T-states** = 82% de un fotograma.

Esto deja un 18% (~12,900 T-states) para sprites, lógica de juego y música. Ajustado pero viable.

### Comparación: métodos de desplazamiento en ZX Spectrum

| Método | T-states/fotograma | % del fotograma | Calidad visual | Notas |
|--------|---------------|------------|----------------|-------|
| Desplazamiento de píxeles completo (horizontal, 1px) | ~135,000 | 189% | Suave | Imposible a 50fps |
| Desplazamiento de píxeles completo (vertical, 1px) | ~107,000 | 149% | Suave | Imposible a 50fps |
| Solo desplazamiento de atributos | ~17,000 | 24% | Brusco (saltos de 8px) | Muy barato |
| Combinado (carácter + píxel de borde) | ~10,000 prom., ~70,000 pico | 14%/98% | Suave | Mejor método con búfer único |
| Pantalla sombra + redibujado de baldosas | ~59,000 | 82% | Suave, sin tearing | Requiere 128K |
| Desplazamiento de carácter (saltos de 8px) | ~52,000--66,000 | 73--92% | Brusco | Para texto/estado con desplazamiento |

![Scrolling technique cost comparison](illustrations/output/ch17_scroll_costs.png)

---

## Desplazar a la derecha (y el problema de la dirección)

Todo lo anterior describe un desplazamiento hacia la izquierda (el jugador se mueve a la derecha, el mundo se desplaza a la izquierda). ¿Qué pasa con desplazar a la derecha?

Para el desplazamiento de atributos, invierte la dirección del LDIR. Copia los bytes 0--30 a las posiciones 1--31, de derecha a izquierda. LDIR copia hacia adelante (de direcciones bajas a altas), así que para un desplazamiento a la derecha necesitas LDDR (copiar hacia atrás):

```z80
; Scroll attributes right by 1 character column
;
scroll_attrs_right:
    ld   hl, $5ADE          ; source: last row, column 30
    ld   de, $5ADF          ; dest: last row, column 31
    ld   bc, 767            ; 768 - 1 bytes
    lddr                    ; 767*21 + 16 = 16,123 T
    ret
```

Para la rotación de bits de píxeles, un desplazamiento a la derecha usa `RR (HL)` en lugar de `RL (HL)`, procesando de izquierda a derecha:

```z80
; Scroll one pixel row RIGHT by 1 pixel
; HL points to byte 0 (leftmost)
;
    or   a                ; 4 T    clear carry
    rr   (hl)             ; 15 T   shift right, bit 0 -> carry
    inc  hl               ; 6 T
    rr   (hl)             ; 15 T   carry -> bit 7
    inc  hl               ; 6 T
    ; ... 32 bytes total ...
```

El coste por byte es idéntico: 21 T-states. Un desplazamiento a la derecha cuesta lo mismo que un desplazamiento a la izquierda. El método combinado funciona en ambas direcciones con el mismo presupuesto.

Para desplazamiento bidireccional (el jugador puede ir a la izquierda o a la derecha), necesitas dos versiones de las rutinas de desplazamiento de carácter y rotación de borde, alternadas según la dirección. El código auto-modificable (SMC) es útil aquí: antes del desplazamiento, parchea el opcode RL/RR y la dirección INC/DEC en la rutina de rotación. Esto evita una bifurcación dentro del bucle interno (ver Capítulo 3 para el patrón de código auto-modificable).

---

## Agon Light 2: desplazamiento por hardware

El VDP (Video Display Processor) del Agon Light 2 maneja el desplazamiento de una forma completamente diferente al Spectrum. Donde el programador de Spectrum debe mover bytes manualmente, el Agon proporciona soporte a nivel de hardware para desplazamientos y tilemaps.

### Desplazamientos de hardware

El VDP soporta un desplazamiento de viewport para los modos bitmap. Al establecer los registros de desplazamiento, mueves toda la imagen mostrada sin mover ningún dato de píxeles. El eZ80 envía un comando VDP a través del enlace serie:

```z80
; Agon: set horizontal scroll offset
; VDU 23, 0, &C3, x_low, x_high
;
    ld   a, 23
    call vdu_write      ; VDU command prefix
    ld   a, 0
    call vdu_write
    ld   a, $C3         ; set scroll offset command
    call vdu_write
    ld   a, (scroll_x)
    call vdu_write      ; x offset low byte
    ld   a, (scroll_x+1)
    call vdu_write      ; x offset high byte
```

El hardware aplica este desplazamiento al leer el framebuffer para la visualización. No se mueven datos de píxeles, no se gastan T-states de CPU en rotar bytes, y el desplazamiento es perfectamente suave a cualquier velocidad. El coste de CPU es solo la sobrecarga de comunicación serie (unos pocos cientos de T-states para la secuencia de comandos VDU).

### Desplazamiento de tilemap

El modo tilemap del VDP proporciona renderizado de baldosas nativo. Defines un conjunto de baldosas (patrones de píxeles de 8x8 o 16x16), construyes un array de mapa que referencia índices de baldosas, y el hardware renderiza el mapa en tiempo de visualización. El desplazamiento se logra cambiando el desplazamiento del viewport del tilemap:

```z80
; Agon: set tilemap scroll offset
; VDU 23, 27, <tilemap_scroll_command>, offset_x, offset_y
;
    ld   a, 23
    call vdu_write
    ld   a, 27
    call vdu_write
    ld   a, 14          ; set tilemap scroll offset
    call vdu_write
    ; ... send x and y offsets ...
```

El tilemap se envuelve automáticamente. A medida que el viewport se desplaza más allá del borde del mapa, el hardware se envuelve al principio (o puedes actualizar la columna del borde con nuevos índices de baldosa -- la técnica de carga de columnas con búfer circular).

### Carga de columnas con búfer circular

Para un nivel con desplazamiento infinito, el tilemap actúa como un búfer circular. El mapa es más ancho que la pantalla por al menos una columna. A medida que el jugador se desplaza a la derecha:

1. El desplazamiento de hardware avanza 1 píxel por fotograma (o la velocidad que quieras).
2. Cuando una nueva columna de baldosas está a punto de entrar en la vista, el eZ80 escribe nuevos índices de baldosas en la columna que acaba de salir por el borde izquierdo.
3. El tilemap se envuelve, y la columna recién escrita aparece a la derecha.

```z80
; Ring-buffer column loading (Agon, conceptual)
;
; tilemap is 40 columns wide, screen shows 32
; scroll_col tracks which column is at the left edge
;
ring_buffer_load:
    ld   a, (scroll_col)
    add  a, 32              ; column about to appear on right
    and  39                  ; wrap to tilemap width (mod 40)
    ld   c, a               ; C = column index to update

    ; Load new tile data for this column from the level map
    ; (level_map is a wider array of tile indices)
    ld   hl, (level_ptr)     ; pointer into the level data
    ld   b, 20               ; 20 rows
.load_col:
    ld   a, (hl)             ; read tile index from level
    inc  hl
    ; Write tile index to tilemap at (C, row)
    call set_tilemap_cell    ; VDP command to set one cell
    djnz .load_col

    ld   (level_ptr), hl
    ret
```

El trabajo de CPU por fotograma es mínimo: escribir 20 índices de baldosas mediante comandos VDP, quizás 2,000--3,000 T-states en total. El resto del fotograma está disponible para la lógica de juego. Compara esto con los 59,000+ T-states del Spectrum para un redibujado de desplazamiento basado en baldosas. El tilemap por hardware del Agon te da aproximadamente una reducción de 20x en el coste de CPU para el desplazamiento.

### Comparación: Spectrum vs. Agon -- desplazamiento

| Aspecto | ZX Spectrum | Agon Light 2 |
|--------|-------------|---------------|
| Granularidad de desplazamiento | Limitada por software; 1px posible pero caro | 1px nativo, cero coste de CPU |
| Coste de CPU por fotograma | 10,000--135,000 T | 500--3,000 T |
| Tearing | Visible sin doble búfer | Ninguno (el VDP maneja la sincronización) |
| Cambio de dirección | Requiere rutinas alternativas o código auto-modificable | Cambiar signo del desplazamiento |
| Límite de tamaño de mapa | Limitado por RAM, sin soporte de hardware | Tamaño de tilemap limitado por la memoria del VDP |
| Color por baldosa | 2 colores por celda de 8x8 (atributo) | Color completo por píxel |

El contraste es marcado. Lo que el programador de Spectrum gasta en la mayor parte de su presupuesto de fotograma -- mover datos de píxeles a través de un diseño de memoria revuelto -- el Agon lo maneja con una escritura de registro. Esto no es una crítica a ninguna de las dos plataformas. Es una demostración de cómo las decisiones de diseño de hardware se propagan a través de cada nivel del software. Las restricciones del Spectrum forzaron el desarrollo del método combinado de desplazamiento, los motores de baldosas y los trucos de la pantalla sombra. Las restricciones del Agon están en otra parte (latencia serie del VDP, sobrecarga de comandos para escenas complejas).

---

## Práctico: nivel de desplazamiento lateral horizontal

### Versión Spectrum: desplazamiento combinado de carácter + píxel

Construye un juego de desplazamiento lateral horizontal con un área de juego de 20x20 caracteres que se desplaza suavemente a 1 píxel por fotograma. Los datos del nivel son un tilemap almacenado en un banco de memoria.

Aquí está la estructura completa:

```z80
; Side-scroller engine — ZX Spectrum 128K
; Uses combined character + pixel method with shadow screen.
;
    ORG $8000

PLAY_X      EQU 2           ; play area starts at column 2
PLAY_Y      EQU 2           ; play area starts at char row 2
PLAY_W      EQU 20          ; play area width in characters
PLAY_H      EQU 20          ; play area height in characters

scroll_pixel_x:   DB 0      ; pixel offset 0-7
scroll_tile_x:    DW 0      ; tile column at left edge
screen_flag:      DB 0      ; which screen is visible
current_bank:     DB 0      ; current $7FFD value

; --- Main loop ---
main:
    halt                     ; 4 T   sync to frame

    ; Advance scroll
    ld   a, (scroll_pixel_x) ; 13 T
    inc  a                   ; 4 T
    cp   8                   ; 7 T
    jr   c, .pixel_only      ; 12/7 T

    ; Character scroll frame
    xor  a
    ld   (scroll_pixel_x), a

    ; Advance tile position
    ld   hl, (scroll_tile_x)
    inc  hl
    ld   (scroll_tile_x), hl

    ; Get back buffer address
    call get_back_buffer     ; HL = $4000 or $C000

    ; Redraw full play area from tilemap into back buffer
    call render_play_area    ; ~50,000 T

    ; Flip screens
    call flip_screens        ; ~30 T

    jr   .frame_done

.pixel_only:
    ld   (scroll_pixel_x), a

    ; Shift edge columns in current (non-displayed) buffer
    call get_back_buffer
    call shift_edge_columns  ; ~9,600 T

    call flip_screens

.frame_done:
    call update_player       ; ~2,000 T
    call draw_sprites        ; ~5,000 T
    call play_music          ; ~3,000 T (IM2 handler)

    jr   main

; --- Render full play area from tilemap ---
; Input: HL = base address of target screen ($4000 or $C000)
;
render_play_area:
    ; For each tile in the play area:
    ;   Look up tile index from tilemap
    ;   Copy 8 bytes of tile data to screen, navigating interleave
    ;
    ; 20 columns x 20 rows = 400 tiles
    ; Each tile: 8 scan lines x 1 byte = 8 LDI operations
    ; Per tile: lookup (20 T) + 8 x (LDI 16 T + INC H 4 T) = 180 T
    ; Total: 400 x 180 = 72,000 T
    ;
    ; (Actual implementation uses PUSH tricks and
    ;  pre-computed screen address tables for ~55,000 T)
    ret

; --- Shift edge columns by 1 pixel ---
; Shifts the 2 rightmost columns of the play area left by 1 pixel
;
shift_edge_columns:
    ; For each of 160 pixel rows in the play area:
    ;   Navigate to the correct screen address
    ;   RL (HL) on the 2 edge bytes, right to left
    ;
    ; Per row: 40 T (2 bytes shifted) + 20 T (navigation)
    ; Total: 160 x 60 = 9,600 T
    ret
```

### Versión Agon: desplazamiento de tilemap por hardware

La versión para Agon es dramáticamente más simple. El bucle principal llama a `vsync`, incrementa un desplazamiento de 16 bits, lo envía al VDP mediante la rutina `set_scroll_offset` (un puñado de llamadas `vdu_write`), y cada 8 píxeles llama a `ring_buffer_load` para actualizar una columna de índices de baldosas. El desplazamiento completo cuesta menos de 3,000 T-states por fotograma, dejando 365,000+ T-states para lógica de juego, IA, física y renderizado. La versión para Spectrum es un ejercicio cuidadoso de conteo de ciclos donde cada técnica de los Capítulos 2 y 3 se une para lograr lo que el Agon hace con un registro de hardware.

---

## Vertical + horizontal: desplazamiento combinado

Algunos juegos se desplazan en ambas direcciones simultáneamente. En el Spectrum, aplica el método combinado a ambos ejes: desplazamiento de carácter + desplazamiento de píxeles (0--7) para cada uno. El desplazamiento de carácter en cada dirección ocurre una vez cada 8 fotogramas. Que ambos coincidan en el mismo fotograma es una probabilidad de 1/64 (aproximadamente cada 1.3 segundos) -- o bien aceptas un fotograma perdido o divides el trabajo. El coste de rotación de borde por fotograma para ambos ejes: columnas de borde horizontales (~9,600 T) + filas de borde verticales (~6,400 T) = ~16,000 T = 22% del fotograma. Manejable.

---

## Consejos de optimización

### 1. Usa una tabla de consulta de direcciones de pantalla

Precalcula una tabla de 192 direcciones de pantalla (una por fila de píxeles) en RAM. Coste: 384 bytes. Beneficio: una búsqueda en tabla de 16 bits (unos 30 T-states) reemplaza el cálculo de dirección por manipulación de bits (91 T-states).

### 2. Desplaza solo lo que es visible

Si los sprites cubren parte del área de juego, puedes saltarte el desplazamiento de las filas detrás de sprites opacos. Rastrea qué filas necesitan desplazamiento con un bitmap de filas sucias. Esta optimización compensa cuando los sprites cubren una fracción significativa del área de juego.

### 3. Usa PUSH para el desplazamiento de carácter

Para el desplazamiento de datos de píxeles a nivel de carácter (copiar 19 bytes a la izquierda por línea de escaneo), el truco PUSH funciona bien. Establece SP al final de los datos del área de juego de cada línea de escaneo, haz POP de 10 bytes, rota el contenido de los registros, y haz PUSH de vuelta con un desplazamiento de un byte. Esto es complejo de configurar pero reduce el coste por línea de escaneo en un 30--40%.

### 4. Divide el desplazamiento de carácter entre fotogramas

Si el desplazamiento de carácter (cada 8° fotograma) es demasiado caro para un solo fotograma, divídelo: desplaza la mitad superior del área de juego en el fotograma N y la mitad inferior en el fotograma N+1. El artefacto visual (la mitad superior se desplaza 1 fotograma antes que la inferior) es apenas perceptible a 50fps.

### 5. Trucos de paleta y atributos

Para el desplazamiento de solo atributos (sin datos de píxeles involucrados), considera usar cambios de FLASH o BRIGHT para crear la ilusión de movimiento dentro de una cuadrícula de píxeles estática. Un conjunto rotativo de colores de atributos en baldosas alineadas a caracteres puede simular flujo, agua o cintas transportadoras sin mover ningún dato de píxeles en absoluto.

---

## Resumen

- **El desplazamiento de píxeles de pantalla completa en el ZX Spectrum es imposible a 50fps.** El desplazamiento horizontal de píxeles cuesta ~135,000 T-states para 192 filas (189% del presupuesto de fotograma). El vertical cuesta ~107,000 T-states (149%). El diseño de pantalla entrelazado añade complejidad al desplazamiento vertical, y la falta de un barrel shifter hace que el desplazamiento horizontal sea inherentemente caro.

- **El desplazamiento de atributos es barato** con ~17,000 T-states (24% del fotograma), pero se mueve en saltos toscos de 8 píxeles.

- **El método combinado** es lo que usan los juegos reales: desplazamientos a nivel de carácter (cada 8 fotogramas) más rotación de píxeles por fotograma de las 1--2 columnas de borde. El coste promedio por fotograma es inferior a 10,000 T-states. El pico en los fotogramas de desplazamiento de carácter (~70,000 T) se puede gestionar con la pantalla sombra o dividiendo entre fotogramas.

- **La pantalla sombra** (128K, página 7) proporciona doble búfer sin tearing. Dibuja el siguiente fotograma en el búfer trasero, luego intercambia la pantalla. Esto cambia la estrategia de desplazamiento de "mover datos existentes" a "redibujar desde tilemap", lo cual es conceptualmente más simple y elimina el tearing.

- **La dirección del desplazamiento horizontal** no cambia el coste. El desplazamiento a la derecha usa `RR (HL)` en lugar de `RL (HL)`, de izquierda a derecha en lugar de derecha a izquierda, con los mismos 21 T-states por byte.

- **El desplazamiento vertical de píxeles** se complica por el diseño de pantalla entrelazado del Spectrum. Mover una fila de píxeles hacia abajo significa navegar la estructura de dirección `010TTSSS LLLCCCCC`, con ajustes de punteros diferentes en los límites de celdas de caracteres y de tercios. El enfoque de contadores divididos del Capítulo 2 es esencial.

- **El Agon Light 2** proporciona desplazamientos de hardware y renderizado de tilemap que reducen el coste de CPU del desplazamiento a unos pocos comandos VDP por fotograma (~500--3,000 T-states). La carga de columnas con búfer circular mantiene el tilemap actualizado a medida que nuevo terreno entra en la vista. Lo que el programador de Spectrum construye en 70,000 T-states, el Agon lo maneja con una escritura de registro.

- **Técnicas clave de capítulos anteriores** son esenciales aquí: el diseño de pantalla entrelazado y la navegación con contadores divididos (Capítulo 2), cadenas LDI y trucos PUSH para movimiento rápido de datos (Capítulo 3), y código auto-modificable para rutinas de desplazamiento que cambian de dirección (Capítulo 3).

---

> **Fuentes:** Introspec "Eshchyo raz pro DOWN_HL" (Hype, 2020) para navegación de pantalla entrelazada; Introspec "GO WEST Part 1" (Hype, 2015) para costes de memoria contendida; DenisGrachev "Ringo Render 64x48" (Hype, 2022) para desplazamiento de medio carácter; ZX Spectrum 128K Technical Manual para el puerto `$7FFD` y la pantalla sombra; documentación VDP del Agon Light 2 para comandos de tilemap y desplazamiento.
