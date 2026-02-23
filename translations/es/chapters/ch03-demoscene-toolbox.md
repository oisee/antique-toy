# Capitulo 3: La Caja de Herramientas del Demoscener

Todo oficio tiene su bolsa de trucos --- patrones a los que los practicantes recurren con tanta naturalidad que dejan de considerarlos trucos. Un demoscener del Z80 recurre a las tecnicas de este capitulo.

Estos patrones --- bucles desenrollados, codigo auto-modificable, la pila como canal de datos, cadenas LDI, generacion de codigo y RET-encadenamiento --- aparecen en casi cada efecto que construiremos en la Parte II. Son lo que separa una demo que cabe en un fotograma de una que necesita tres. Aprendelos aqui, y los reconoceras en todas partes.

---

## Bucles Desenrollados y Codigo Auto-Modificable

### El coste de iterar

Considera el bucle interno mas simple posible: borrar 256 bytes de memoria.

```z80
; Looped version: clear 256 bytes at (HL)
    ld   b, 0            ; 7 T   (B=0 means 256 iterations)
    xor  a               ; 4 T
.loop:
    ld   (hl), a         ; 7 T
    inc  hl              ; 6 T
    djnz .loop           ; 13 T  (8 on last iteration)
```

Cada iteracion cuesta 7 + 6 + 13 = 26 T-states para almacenar un solo byte. Solo 7 de esos T-states hacen trabajo util --- el resto es sobrecarga. Eso es un 73% de desperdicio. Para 256 bytes: 256 x 26 - 5 = 6.651 T-states. En una maquina donde tienes 69.888 T-states por fotograma, esos T-states desperdiciados duelen.

### Desenrollar: intercambiar ROM por velocidad

La solucion es brutal y efectiva: escribe el cuerpo del bucle N veces y elimina el bucle.

```z80
; Unrolled version: clear 256 bytes at (HL)
    xor  a               ; 4 T
    ld   (hl), a         ; 7 T
    inc  hl              ; 6 T
    ld   (hl), a         ; 7 T
    inc  hl              ; 6 T
    ld   (hl), a         ; 7 T
    inc  hl              ; 6 T
    ; ... repeated 256 times total
```

Cada byte ahora cuesta 7 + 6 = 13 T-states. Sin DJNZ. Sin contador de bucle. Total: 256 x 13 = 3.328 T-states --- la mitad de la version con bucle.

El coste es el tamano del codigo: 256 repeticiones ocupan 512 bytes frente a 7 del bucle. Estas intercambiando ROM por velocidad.

**Cuando desenrollar:** Bucles internos que se ejecutan miles de veces por fotograma --- borrado de pantalla, dibujado de sprites, copia de datos.

**Cuando NO desenrollar:** Bucles externos que se ejecutan una o dos veces por fotograma. Ahorrar 5 T-states en 24 iteraciones te da 120 T-states --- menos de tres NOPs. No vale la pena el aumento de tamano.

El punto medio practico es el *desenrollado parcial*: desenrolla 8 o 16 iteraciones dentro del bucle, conserva DJNZ para el conteo exterior. El ejemplo `push_fill.a80` en el directorio `examples/` de este capitulo hace exactamente esto: 16 PUSHes por iteracion, 192 iteraciones.

### Codigo auto-modificable: el arma secreta del Z80

El Z80 no tiene cache de instrucciones, ni buffer de prebusqueda, ni pipeline. Cuando la CPU busca un byte de instruccion de la RAM, lee lo que este alli *en ese momento*. Si cambiaste ese byte un ciclo antes, la CPU ve el nuevo valor. Esta es una propiedad garantizada de la arquitectura.

El codigo auto-modificable (SMC) significa escribir en los bytes de instruccion en tiempo de ejecucion. El patron clasico es parchear un operando inmediato:

```z80
; Self-modifying code: fill with a runtime-determined value
    ld   a, (fill_value)       ; load the fill byte from somewhere
    ld   (patch + 1), a        ; overwrite the operand of the LD below
patch:
    ld   (hl), $00             ; this $00 gets replaced at runtime
    inc  hl
    ; ...
```

El `ld (patch + 1), a` escribe en el operando inmediato del siguiente `ld (hl), $00`, cambiandolo a `ld (hl), $AA` o lo que hayas cargado. La CPU ejecuta los bytes que encuentra. Algunos patrones comunes de SMC:

**Parchear opcodes.** Incluso puedes reemplazar la instruccion misma. Necesitas un bucle que a veces incrementa HL y a veces lo decrementa? Antes del bucle, escribe el opcode de INC HL ($23) o DEC HL ($2B) en el byte de instruccion. Dentro del bucle interno, no hay salto alguno --- la instruccion correcta ya esta colocada. Compara esto con un enfoque de salto-por-iteracion que costaria 12 T-states (JR NZ) en cada pixel individual.

**Guardar y restaurar el puntero de pila.** Este patron aparece constantemente al usar trucos de PUSH (mas abajo):

```z80
    ld   (restore_sp + 1), sp     ; save SP into the operand below
    ; ... do stack tricks ...
restore_sp:
    ld   sp, $0000                ; self-modified: the $0000 was overwritten
```

El `ld (nn), sp` guarda el SP actual directamente en el operando del posterior `ld sp, nn`. Sin variable temporal. Este es codigo idiomatico de demoscene Z80.

**Una nota de precaucion.** El SMC es seguro en el Z80, el eZ80 y cada clon de Spectrum. *No* es seguro en CPUs modernas con cache (x86, ARM) sin instrucciones explicitas de vaciado de cache. Si portas a una arquitectura diferente, esto es lo primero que se rompe.

---

## La Pila como Canal de Datos

### Por que PUSH es la escritura mas rapida en el Z80

La instruccion PUSH escribe 2 bytes en memoria y decrementa SP, todo en 11 T-states. Comparemos las alternativas para escribir datos en una direccion de pantalla:

| Metodo | Bytes escritos | T-states | T-states por byte |
|--------|---------------|----------|-------------------|
| `ld (hl), a` + `inc hl` | 1 | 13 | 13,0 |
| `ld (hl), a` + `inc l` | 1 | 11 | 11,0 |
| `ldi` | 1 | 16 | 16,0 |
| `ldir` (por byte) | 1 | 21 | 21,0 |
| `push hl` | 2 | 11 | **5,5** |

PUSH escribe dos bytes en 11 T-states --- 5,5 T-states por byte. Casi 4 veces mas rapido que LDIR. La trampa: PUSH escribe donde apunta SP, y SP es normalmente tu pila. Para usar PUSH como canal de datos, debes secuestrar el puntero de pila.

### La tecnica

El patron es siempre el mismo:

1. Deshabilitar interrupciones (DI). Si una interrupcion se dispara mientras SP apunta a la pantalla, la CPU empujara la direccion de retorno en tus datos de pixel. Le sigue el caos.
2. Guardar SP. Usa codigo auto-modificable para guardarlo.
3. Establecer SP al *final* de tu area objetivo. La pila crece hacia abajo --- PUSH decrementa SP antes de escribir. Asi que si quieres llenar desde $4000 hasta $57FF, estableces SP en $5800.
4. Cargar tus datos en pares de registros y hacer PUSH repetidamente.
5. Restaurar SP y rehabilitar interrupciones (EI).

Aqui esta el nucleo del ejemplo `push_fill.a80` del directorio `examples/` de este capitulo:

```z80
stack_fill:
    di                          ; critical: no interrupts while SP is moved
    ld   (restore_sp + 1), sp   ; self-modifying: save SP

    ld   sp, SCREEN_END         ; SP points to end of screen ($5800)
    ld   hl, $AAAA              ; pattern to fill

    ld   b, 192                 ; 192 iterations x 16 PUSHes x 2 bytes = 6144
.loop:
    push hl                     ; 11 T  \
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |  16 PUSHes = 32 bytes
    push hl                     ; 11 T   |  = 176 T-states
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |
    push hl                     ; 11 T  /
    djnz .loop                  ; 13 T (8 on last)

restore_sp:
    ld   sp, $0000              ; self-modified: restores original SP
    ei
    ret
```

El cuerpo interno de 16 PUSHes escribe 32 bytes en 176 T-states. Total para los 6.144 bytes del area de pixeles completa: aproximadamente 36.000 T-states. Compara con LDIR: 6.144 x 21 - 5 = 129.019 T-states. El metodo PUSH es aproximadamente 3,6 veces mas rapido --- la diferencia entre caber en un fotograma y desbordar al siguiente.

### Donde se usan los trucos de PUSH

- **Borrado de pantalla.** El uso mas comun. Toda demo necesita borrar la pantalla entre efectos.
- **Sprites compilados.** El sprite se compila en una secuencia de instrucciones PUSH con pares de registros precargados. La salida de sprites mas rapida posible en el Z80.
- **Salida rapida de datos.** Cada vez que necesitas transferir un bloque de datos a un rango de direcciones contiguo: llenado de atributos, copias de buffer, construccion de listas de visualizacion.

El precio que pagas: las interrupciones estan desactivadas. Si tu reproductor de musica funciona desde una interrupcion IM2, perdera un compas durante una secuencia larga de PUSH. Los coders de demos planifican alrededor de esto --- programan los llenados PUSH durante el tiempo de borde, o los dividen en multiples fotogramas.

---

## Cadenas LDI

### LDI vs LDIR

LDI copia un byte de (HL) a (DE), incrementa ambos y decrementa BC. LDIR hace lo mismo pero repite hasta que BC = 0. La diferencia esta en el temporizado:

| Instruccion | T-states | Notas |
|-------------|----------|-------|
| LDI | 16 | Copia 1 byte, siempre 16 T |
| LDIR (por byte) | 21 | Copia 1 byte, vuelve a iterar. Ultimo byte: 16 T |

LDIR cuesta 5 T-states adicionales por byte para su verificacion interna de retorno al bucle. Esos 5 T-states se acumulan rapidamente.

Para 256 bytes:
- LDIR: 255 x 21 + 16 = 5.371 T-states
- 256 x LDI: 256 x 16 = 4.096 T-states
- Ahorro: 1.275 T-states (24%)

Una cadena de instrucciones LDI individuales son solo 256 repeticiones del opcode de dos bytes `$ED $A0`. Eso son 512 bytes de codigo para ahorrar un 24% --- el mismo intercambio de ROM por velocidad que el desenrollado de bucles.

### Cuando las cadenas LDI brillan

El punto ideal es copiar bloques de tamano conocido. Una cadena de 32 LDIs ahorra 160 T-states respecto a LDIR para una fila de sprite. A lo largo de 24 filas, son 3.840 T-states por fotograma.

Pero el verdadero poder emerge cuando combinas cadenas LDI con *aritmetica de punto de entrada*. Si tienes una cadena de 256 LDIs y quieres copiar solo 100 bytes, salta a la cadena en la posicion 156. Sin contador de bucle, sin configuracion. Esta tecnica se usa en el chaos zoomer de Introspec en Eager (2015):

```z80
; Chaos zoomer inner loop (simplified from Eager)
; Each line copies a different number of bytes from a source buffer.
; Entry point into the LDI chain is calculated per line.
    ld   hl, source_data
    ld   de, dest_screen
    ; ... calculate entry point based on zoom factor ...
    jp   (ix)             ; jump into the LDI chain at the right point

ldi_chain:
    ldi                   ; byte 255
    ldi                   ; byte 254
    ldi                   ; byte 253
    ; ... 256 LDIs total ...
    ldi                   ; byte 0
    ; falls through to next line setup
```

Esta copia de longitud variable con cero sobrecarga de bucle por byte es una tecnica que simplemente no puedes lograr con LDIR. Es una razon por la que LDI es el mejor amigo de todos en el codigo de demoscene.

---

## Generacion de Codigo

### La tecnica mas poderosa

Todo lo anterior es una optimizacion fija --- el codigo se ejecuta de la misma manera cada fotograma. La generacion de codigo va mas alla: tu programa escribe el programa que dibuja la pantalla. Hay dos variantes: offline (antes del ensamblado) y en tiempo de ejecucion (durante la ejecucion).

### Offline: generar ensamblador desde un lenguaje de nivel superior

Introspec uso Processing (un entorno de programacion creativa basado en Java) para generar ensamblador Z80 para el chaos zoomer en Eager (2015). Un chaos zoomer cambia la magnificacion en cada fotograma --- diferentes pixeles fuente se mapean a diferentes ubicaciones de pantalla. En lugar de calcular estos mapeos en tiempo de ejecucion, el script de Processing precalculo cada mapeo y genero archivos fuente .a80 que contienen cadenas LDI y instrucciones LD optimizadas.

El flujo de trabajo: un script de Processing calcula, para cada fotograma, que byte fuente se mapea a que byte de pantalla. Genera fuente Z80 --- secuencias de instrucciones `ld hl, source_addr` y `ldi` --- que el ensamblador (sjasmplus) compila junto al codigo del motor escrito a mano. En tiempo de ejecucion, el motor simplemente llama al codigo pregenerado para el fotograma actual.

Esto no es "hacer trampa". Es la vision fundamental de que la division del trabajo entre tiempo de compilacion y tiempo de ejecucion puede eliminar saltos, consultas y aritmetica del bucle interno por completo. El script de Processing hace las matematicas dificiles una vez, lentamente, en una maquina moderna. El Z80 hace la parte facil --- copiar bytes --- tan rapido como es fisicamente posible.

### Tiempo de ejecucion: el programa escribe codigo maquina durante la ejecucion

A veces los parametros cambian cada fotograma, asi que la generacion offline no es suficiente. La rutina de mapeado de esfera en Illusion de X-Trade (ENLiGHT'96) genera codigo maquina en un buffer de RAM en tiempo de ejecucion. La geometria de la esfera cambia al rotar --- diferentes pixeles necesitan diferentes distancias de salto. Antes de cada fotograma, el motor emite bytes de opcode en un buffer, luego los ejecuta:

```z80
; Runtime code generation (conceptual, simplified from Illusion)
; Generate an unrolled rendering loop for this frame's sphere slice

    ld   hl, code_buffer
    ld   de, sphere_table       ; per-frame skip distances

    ld   b, SPHERE_WIDTH
.gen_loop:
    ld   a, (de)                ; load skip distance for this pixel
    inc  de

    ; Emit: ld a, (hl) -- opcode $7E
    ld   (hl), $7E
    inc  hl

    ; Emit: add a, N   -- opcodes $C6, N
    ld   (hl), $C6
    inc  hl
    ld   (hl), a                ; the skip distance, as immediate operand
    inc  hl

    djnz .gen_loop

    ; Emit: ret -- opcode $C9
    ld   (hl), $C9

    ; Now execute the generated code
    call code_buffer
```

El codigo generado es una secuencia en linea recta sin saltos, sin consultas, sin sobrecarga de bucle --- pero es *codigo diferente cada fotograma*. En lugar de "if pixel_skip == 3 then..." a 12 T-states por salto, emites las instrucciones exactas necesarias y las ejecutas sin saltos.

**Cuando generar codigo:** Si las mismas operaciones ocurren cada fotograma con solo cambios de datos, el codigo auto-modificable (parchear operandos) es suficiente. Si la *estructura* cambia --- diferentes numeros de iteraciones, diferentes secuencias de instrucciones --- genera el codigo. Si puedes precomputar las variaciones en una maquina moderna, prefiere la generacion offline: es depurable, verificable e impone cero coste en tiempo de ejecucion. La generacion en tiempo de ejecucion vale la pena cuando el codigo generado se ejecuta mucho mas frecuentemente de lo que cuesta generarlo.

---

## RET-Encadenamiento

### Convertir la pila en una tabla de despacho

En 2025, DenisGrachev publico una tecnica en Hype desarrollada para su juego Dice Legends. El problema: renderizar un campo de juego basado en tiles requiere dibujar docenas de tiles por fotograma. El enfoque ingenuo usa CALL:

```z80
; Naive approach: call each tile renderer
    call draw_tile_0
    call draw_tile_1
    call draw_tile_2
    ; ...
```

Cada CALL cuesta 17 T-states. Para un campo de juego de 30 x 18 (540 tiles), son 9.180 T-states solo en despacho.

La idea de DenisGrachev: establecer SP a una *lista de renderizado* --- una tabla de direcciones --- y terminar cada procedimiento de dibujo de tile con RET. RET saca 2 bytes de (SP) y los pone en PC. Si SP apunta a tu lista de renderizado, RET no retorna al llamador --- salta a la siguiente rutina en la lista.

```z80
; RET-chaining: zero call overhead
    di
    ld   (restore_sp + 1), sp   ; save SP
    ld   sp, render_list        ; SP points to our dispatch table

    ; "Call" the first tile routine by falling into it or using RET:
    ret                         ; pops first address from render_list

; Each tile routine ends with:
draw_tile_N:
    ; ... draw the tile ...
    ret                         ; pops NEXT address from render_list

; The render list is a sequence of addresses:
render_list:
    dw   draw_tile_42           ; first tile to draw
    dw   draw_tile_7            ; second tile
    dw   draw_tile_42           ; third tile (same tile type, different position)
    ; ... one entry per tile on screen ...
    dw   render_done            ; sentinel: address of cleanup code

render_done:
restore_sp:
    ld   sp, $0000              ; self-modified: restore SP
    ei
```

Cada despacho ahora cuesta 10 T-states (RET) en lugar de 17 (CALL). Para 540 tiles: 3.780 T-states ahorrados. Pero la ganancia real es el despacho gratuito --- cada entrada puede apuntar a un procedimiento diferente (tile ancho, tile vacio, tile animado). Sin tabla de saltos, sin llamada indirecta. La lista de renderizado *es* el programa.

### Tres estrategias para la lista de renderizado

DenisGrachev exploro tres enfoques para construir la lista de renderizado:

1. **Mapa como lista de renderizado.** El propio mapa de tiles es la lista de renderizado: cada celda contiene la direccion de la rutina de dibujo para ese tipo de tile. Simple pero inflexible --- cambiar un tile implica reescribir 2 bytes en el mapa.

2. **Segmentos basados en direcciones.** La pantalla se divide en segmentos. La lista de renderizado de cada segmento es un bloque de direcciones copiado de una tabla maestra. Cambiar tiles significa copiar un nuevo bloque de direcciones.

3. **Basado en bytes con tablas de consulta de 256 bytes.** Cada tipo de tile es un solo byte (el indice del tile). Una tabla de consulta de 256 bytes mapea indices de tiles a direcciones de rutinas. La lista de renderizado se construye iterando sobre los bytes del mapa de tiles y consultando cada direccion. Este es el enfoque que DenisGrachev eligio para Dice Legends.

Usando el enfoque basado en bytes, amplio el campo de juego de 26 x 15 tiles (el limite de su motor anterior) a 30 x 18 tiles manteniendo la tasa de fotogramas objetivo. Los ahorros por eliminar la sobrecarga de CALL, combinados con el despacho de coste cero, liberaron suficientes T-states para renderizar un 40% mas de tiles.

### Las contrapartidas

Como todos los trucos de pila, las interrupciones deben estar deshabilitadas mientras SP esta secuestrado. Cada rutina de tile debe ser autocontenida --- terminando con RET y sin usar CALL, ya que la pila real no esta disponible. En la practica, las rutinas de tiles son lo suficientemente cortas como para que esto no sea una limitacion.

---

## Sidebar: "El Codigo esta Muerto" (Introspec, 2015)

En enero de 2015, Introspec publico un breve y provocador ensayo en Hype titulado "El Codigo esta Muerto" (Kod myortv). El argumento traza un paralelo con "La Muerte del Autor" de Roland Barthes: asi como Barthes arguia que el significado de un texto pertenece al lector, no al escritor, Introspec argumenta que el codigo de una demo solo vive verdaderamente cuando alguien lo lee --- en un depurador, en un listado de desensamblado, en codigo fuente compartido en un foro.

La verdad incomoda: las demos modernas se consumen como medios visuales. La gente las ve en YouTube. Votan en Pouet basandose en capturas de video. Nadie ve los bucles internos. Una optimizacion brillante que ahorra 3 T-states por pixel es invisible para el 99% de la audiencia. "Escribir codigo puramente por si mismo", escribio Introspec, "ha perdido relevancia".

Y sin embargo.

Estas leyendo este libro. Estamos abriendo el depurador. Estamos contando T-states. Estamos mirando dentro. Las tecnicas de este capitulo no son piezas de museo. Son herramientas vivas, y el hecho de que la mayoria de la gente nunca las vera no disminuye su artesania.

El ensayo de Introspec es un desafio, no una rendicion. Posteriormente publico algunos de los analisis tecnicos mas detallados que la escena ZX haya producido --- incluyendo el desglose de Illusion y los benchmarks de compresion referenciados a lo largo de este libro. El codigo puede estar muerto para el espectador de YouTube. Pero para el lector con un desensamblador y una mente curiosa, esta muy vivo.

---

## Juntandolo Todo

Las tecnicas de este capitulo no son independientes. En la practica, se componen:

- **El borrado de pantalla** combina *bucles desenrollados* con *trucos de PUSH*: un bucle parcialmente desenrollado de 16 PUSHes por iteracion, con SP secuestrado via *codigo auto-modificable*.
- **Los sprites compilados** combinan *generacion de codigo* (cada sprite se compila a codigo ejecutable), *salida PUSH* (la forma mas rapida de escribir datos de pixel) y *auto-modificacion* (parcheando direcciones de pantalla por fotograma).
- **Los motores de tiles** combinan *RET-encadenamiento* para despacho con *cadenas LDI* dentro de cada rutina de tile para copia rapida de datos.
- **Los chaos zoomers** combinan *generacion de codigo offline* (scripts de Processing emitiendo ensamblador) con *cadenas LDI* (el codigo generado es mayormente secuencias LDI) y *auto-modificacion* (parcheando direcciones fuente por fotograma).

El hilo comun: cada tecnica elimina algo del bucle interno. Desenrollar elimina el contador de bucle. La auto-modificacion elimina saltos. PUSH elimina la sobrecarga por byte. Las cadenas LDI eliminan la penalizacion de repeticion de LDIR. La generacion de codigo elimina toda la distincion entre codigo y datos. El RET-encadenamiento elimina la sobrecarga de CALL.

El Z80 funciona a 3,5 MHz. Tienes 69.888 T-states por fotograma. Cada T-state que ahorras en el bucle interno es un T-state que puedes gastar en mas pixeles, mas colores, mas movimiento. La caja de herramientas de este capitulo es como llegas alli.

En los capitulos que siguen, veras cada una de estas tecnicas en accion en demos reales --- la esfera texturizada de Illusion, el tunel de atributos de Eager, el motor multicolor de Old Tower. El objetivo de este capitulo fue darte el vocabulario. Ahora veamos que construyeron los maestros con el.

---

## Pruebalo Tu Mismo

1. **Mide la diferencia.** Toma el arnes de temporizado del Capitulo 1 y mide tres versiones de un llenado de 256 bytes: (a) el bucle `ld (hl), a : inc hl : djnz`, (b) un `ld (hl), a : inc hl` x 256 completamente desenrollado, y (c) el llenado basado en PUSH de `examples/push_fill.a80`. Compara las anchuras de la franja de borde. La franja de la version PUSH deberia ser visiblemente mas corta.

2. **Construye un borrado auto-modificable.** Escribe una rutina de borrado de pantalla que tome el patron de llenado como parametro y lo parchee en un bucle de llenado basado en PUSH usando codigo auto-modificable. Llamala dos veces con patrones diferentes y observa la pantalla alternarse.

3. **Cronometra una cadena LDI.** Escribe una copia de 32 bytes usando LDIR y otra usando 32 x LDI. Mide ambas con la tecnica del color de borde. La cadena LDI deberia ahorrar 160 T-states --- visible si ejecutas la copia en un bucle ajustado.

4. **Experimenta con puntos de entrada.** Construye una cadena LDI de 128 entradas y una pequena rutina que calcule un punto de entrada basado en un valor en el registro A (0--128). Salta a la cadena en diferentes puntos. Esta es una version simplificada de la copia de longitud variable usada en los chaos zoomers reales.

> **Fuentes:** DenisGrachev "Tiles and RET" (Hype, 2025); Introspec "Making of Eager" (Hype, 2015); Introspec "Technical Analysis of Illusion" (Hype, 2017); Introspec "Code is Dead" (Hype, 2015)
