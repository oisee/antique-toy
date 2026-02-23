# Capítulo 21: Juego Completo -- ZX Spectrum 128K

> *"La única forma de saber si tu motor funciona es lanzar un juego."*

---

Tienes sprites (Capítulo 16). Tienes desplazamiento (Capítulo 17). Tienes un bucle de juego y un sistema de entidades (Capítulo 18). Tienes colisiones, física e IA enemiga (Capítulo 19). Tienes música AY y efectos de sonido (Capítulo 11). Tienes compresión (Capítulo 14). Tienes 128K de RAM con bancos y sabes cómo acceder a cada byte (Capítulo 15).

Ahora debes poner todo en un solo binario que se cargue desde cinta, muestre una pantalla de carga, presente un menú, reproduzca cinco niveles de un plataformas con desplazamiento lateral con cuatro tipos de enemigos y un jefe, registre las puntuaciones más altas y quepa en un archivo `.tap`.

Este es el capítulo de integración. No aparecen técnicas nuevas aquí. En su lugar, enfrentamos los problemas que solo surgen cuando todos los subsistemas deben coexistir: contención de memoria entre bancos de gráficos y código, presupuestos de fotograma que se desbordan cuando el desplazamiento, los sprites, la música y la IA demandan su parte, sistemas de compilación que deben coordinar una docena de pasos de conversión de datos, y las mil pequeñas decisiones sobre qué va dónde en 128K de memoria con bancos.

El juego que estamos construyendo se llama *Ironclaw* -- un plataformas de desplazamiento lateral de cinco niveles protagonizado por un gato mecánico que navega por una serie de plantas de fábrica cada vez más hostiles. El género es deliberado: los plataformas de desplazamiento lateral exigen todos los subsistemas simultáneamente y no dejan dónde esconderse. Si el desplazamiento tartamudea, lo ves. Si el renderizado de sprites desborda el fotograma, lo sientes. Si la detección de colisiones falla, el jugador cae a través del suelo. Un plataformas es la prueba de integración más difícil que un motor de juego Z80 puede enfrentar.

---

## 21.1 Arquitectura del Proyecto

Antes de escribir una sola línea de Z80, necesitas una estructura de directorios que escale. Un juego de 128K con cinco niveles, un conjunto de baldosas, hojas de sprites, una partitura musical y efectos de sonido genera docenas de archivos de datos. Si no los organizas desde el principio, te ahogarás.

### Estructura de Directorios

```
ironclaw/
  src/
    main.a80           -- punto de entrada, conmutación de bancos, máquina de estados
    render.a80          -- renderizador de baldosas, motor de desplazamiento
    sprites.a80         -- rutinas de dibujo de sprites (OR+AND enmascarado)
    entities.a80        -- actualización de entidades, aparición, desaparición
    physics.a80         -- gravedad, fricción, salto, respuesta de colisión
    collisions.a80      -- comprobaciones de colisión AABB y de baldosas
    ai.a80              -- FSM enemiga: patrulla, persecución, ataque, retirada, muerte
    player.a80          -- entrada del jugador, estado, animación
    hud.a80             -- puntuación, vidas, barra de estado
    menu.a80            -- pantalla de título, opciones, puntuaciones altas
    loader.a80          -- pantalla de carga, cargador de cinta/esxDOS
    music_driver.a80    -- reproductor PT3, manejador de interrupciones
    sfx.a80             -- motor de efectos de sonido, robo de canales
    esxdos.a80          -- envolturas de E/S de archivos DivMMC
    banks.a80           -- macros y utilidades de conmutación de bancos
    defs.a80            -- constantes, mapa de memoria, estructura de entidades
  data/
    levels/             -- mapas de baldosas de niveles (comprimidos)
    tiles/              -- gráficos de conjuntos de baldosas
    sprites/            -- hojas de sprites (pre-desplazadas)
    music/              -- archivos de música PT3
    sfx/                -- tablas de definición de SFX
    screens/            -- pantalla de carga, pantalla de título
  tools/
    png2tiles.py        -- convertidor de conjuntos de baldosas desde PNG
    png2sprites.py      -- convertidor de hojas de sprites desde PNG (genera desplazamientos)
    map2bin.py          -- JSON/TMX de Tiled a mapa de baldosas binario
    compress.py         -- envolturas para compresión ZX0/Pletter
  build/                -- salida compilada (en gitignore)
  Makefile              -- el sistema de compilación
```

Cada archivo fuente se enfoca en un subsistema. Cada archivo de datos pasa por una cadena de conversión antes de llegar al ensamblador. El directorio `tools/` contiene scripts de Python que convierten formatos amigables para el artista (imágenes PNG, mapas del editor Tiled) en datos binarios listos para el ensamblador.

### El Sistema de Compilación

El Makefile es la columna vertebral del proyecto. Debe:

1. Convertir todos los gráficos de PNG a datos binarios de baldosas/sprites
2. Convertir mapas de niveles del formato Tiled a mapas de baldosas binarios
3. Comprimir datos de niveles, bancos de gráficos y música con el compresor apropiado
4. Ensamblar todos los archivos fuente en un solo binario
5. Generar el archivo `.tap` final con el cargador correcto

```makefile
# Ironclaw Makefile
ASM       = sjasmplus
COMPRESS  = zx0
PYTHON    = python3

# Data conversion
data/tiles/tileset.bin: data/tiles/tileset.png
	$(PYTHON) tools/png2tiles.py $< $@

data/sprites/player.bin: data/sprites/player.png
	$(PYTHON) tools/png2sprites.py --shifts 4 $< $@

data/levels/level%.bin: data/levels/level%.tmx
	$(PYTHON) tools/map2bin.py $< $@

# Compression (ZX0 for level data -- good ratio, small decompressor)
data/levels/level%.bin.zx0: data/levels/level%.bin
	$(COMPRESS) $< $@

# Compression (Pletter for graphics -- faster decompression)
data/tiles/tileset.bin.plt: data/tiles/tileset.bin
	pletter5 $< $@

# Assembly
build/ironclaw.tap: src/*.a80 data/levels/*.zx0 data/tiles/*.plt \
                    data/sprites/*.bin data/music/*.pt3
	$(ASM) --fullpath src/main.a80 --raw=build/ironclaw.tap

.PHONY: clean
clean:
	rm -rf build/ data/**/*.bin data/**/*.zx0 data/**/*.plt
```

La clave es la cadena de datos. El artista exporta un conjunto de baldosas PNG desde Aseprite. El script `png2tiles.py` lo corta en baldosas de 8x8 o 16x16, convierte cada una al formato de píxeles entrelazado del Spectrum y escribe un blob binario. El diseñador de niveles exporta un mapa `.tmx` de Tiled. El script `map2bin.py` extrae los índices de baldosas y escribe un mapa de baldosas binario compacto. El compresor reduce cada blob. Solo entonces el ensamblador hace `INCBIN` del resultado en el banco de memoria apropiado.

Esta cadena significa que el contenido del juego siempre está en formato editable (PNG, TMX), y el sistema de compilación maneja cada conversión automáticamente. Cambia una baldosa en el PNG, escribe `make`, y la nueva baldosa aparece en el juego.

---

## 21.2 Mapa de Memoria: Asignaciones de Bancos 128K

El ZX Spectrum 128K tiene ocho bancos de RAM de 16KB, numerados del 0 al 7. En cualquier momento, la CPU ve un espacio de direcciones de 64KB:

```
$0000-$3FFF   ROM (16KB) -- ROM de BASIC o del editor 128K
$4000-$7FFF   Banco 5 (siempre) -- memoria de pantalla (pantalla normal)
$8000-$BFFF   Banco 2 (siempre) -- típicamente código
$C000-$FFFF   Conmutable -- bancos 0-7, seleccionados mediante puerto $7FFD
```

Los bancos 5 y 2 están cableados fijamente a `$4000` y `$8000` respectivamente. Solo la ventana superior de 16KB (`$C000-$FFFF`) es conmutable. El registro de selección de banco en el puerto `$7FFD` también controla qué pantalla se muestra (banco 5 o banco 7) y qué página ROM está activa.

```z80
; Port $7FFD layout:
;   Bit 0-2:  Bank number for $C000-$FFFF (0-7)
;   Bit 3:    Screen select (0 = bank 5 normal, 1 = bank 7 shadow)
;   Bit 4:    ROM select (0 = 128K editor, 1 = 48K BASIC)
;   Bit 5:    Disable paging (PERMANENT -- cannot be undone without reset)
;   Bits 6-7: Unused

; Switch to bank N at $C000
; Input: A = bank number (0-7)
; Preserves: all registers except A
switch_bank:
    or   %00010000          ; ROM 1 (48K BASIC) -- keep this set
    ld   (last_bank_state), a
    ld   bc, $7FFD
    out  (c), a
    ret

last_bank_state:
    db   %00010000          ; default: bank 0, normal screen, ROM 1
```

La regla crítica: **almacena siempre tu última escritura a `$7FFD`** en una variable sombra. El puerto `$7FFD` es de solo escritura -- no puedes leer el estado actual. Si necesitas cambiar un bit (digamos, cambiar la pantalla) sin alterar la selección de banco, debes leer tu variable sombra, modificar el bit, escribir el resultado tanto en el puerto como en la sombra.

### Asignación de Bancos de Ironclaw

Así es como Ironclaw distribuye sus 128KB entre los ocho bancos:

```
Banco 0 ($C000)  -- Datos de nivel: mapas de baldosas para niveles 1-2 (comprimidos)
                    Gráficos de conjunto de baldosas (comprimidos)
                    Búfer de descompresión

Banco 1 ($C000)  -- Datos de nivel: mapas de baldosas para niveles 3-5 (comprimidos)
                    Datos y patrones del nivel del jefe
                    Tablas de aparición de enemigos

Banco 2 ($8000)  -- FIJO: Código principal del juego
                    Lógica del jugador, física, colisiones
                    Rutinas de sprites, sistema de entidades
                    Máquina de estados, HUD
                    ~ 14KB código, 2KB tablas/búfers

Banco 3 ($C000)  -- Gráficos de sprites (pre-desplazados x4)
                    Jugador: 6 fotogramas x 4 desplazamientos = 24 variantes
                    Enemigos: 4 tipos x 4 fotogramas x 4 desplazamientos = 64 variantes
                    Proyectiles, partículas, recogibles
                    ~ 12KB total

Banco 4 ($C000)  -- Música: datos de canciones PT3 (título, niveles 1-3)
                    Código del reproductor PT3 (copia residente)

Banco 5 ($4000)  -- FIJO: Pantalla normal
                    Datos de píxeles $4000-$57FF (6.144 bytes)
                    Atributos $5800-$5AFF (768 bytes)
                    ~9KB restantes: manejador de interrupciones, búfers de pantalla

Banco 6 ($C000)  -- Música: datos de canciones PT3 (niveles 4-5, jefe, game over)
                    Tablas de definición de SFX
                    Código del motor de SFX

Banco 7 ($4000)  -- Pantalla sombra (usada para doble búfer)
                    También utilizable como 16KB de almacenamiento de datos cuando
                    no se está usando activamente el doble búfer
```

Hay varias cosas que notar sobre esta distribución:

**El código vive en el banco 2 (fijo).** Dado que el banco 2 siempre está mapeado en `$8000-$BFFF`, tu código principal del juego siempre es accesible. Nunca necesitas paginar código -- solo datos. Esto elimina la clase más peligrosa de error de conmutación de bancos: llamar a una rutina que ha sido paginada fuera.

**Los gráficos de sprites en el banco 3, separados de los datos de nivel en los bancos 0-1.** Al renderizar un fotograma, el renderizador necesita tanto gráficos de baldosas (para el fondo con desplazamiento) como gráficos de sprites (para las entidades). Si ambos estuvieran en el mismo banco conmutable, necesitarías paginar de ida y vuelta a mitad del renderizado. Al colocarlos en bancos separados, puedes paginar los datos de baldosas, renderizar el fondo, luego paginar los datos de sprites y renderizar todas las entidades, con solo dos conmutaciones de banco por fotograma.

**La música está dividida entre los bancos 4 y 6.** El reproductor PT3 se ejecuta dentro del manejador de interrupciones IM2, que se dispara una vez por fotograma. El manejador de interrupciones debe paginar el banco de música, actualizar los registros AY y volver a paginar al banco que estuviera usando el bucle principal. Dividir la música entre dos bancos significa que el manejador de interrupciones debe saber qué banco contiene la canción actual. Manejamos esto con una variable:

```z80
current_music_bank:
    db   4              ; bank 4 by default

im2_handler:
    push af
    push bc
    push de
    push hl
    push ix

    ; Save current bank state
    ld   a, (last_bank_state)
    push af

    ; Page in music bank
    ld   a, (current_music_bank)
    call switch_bank

    ; Update PT3 player -- writes AY registers
    call pt3_play

    ; Check for pending SFX
    call sfx_update

    ; Restore previous bank
    pop  af
    ld   (last_bank_state), a
    ld   bc, $7FFD
    out  (c), a

    pop  ix
    pop  hl
    pop  de
    pop  bc
    pop  af
    ei
    reti
```

**La pantalla sombra en el banco 7** está disponible para doble búfer durante las actualizaciones de desplazamiento (como se describe en el Capítulo 17). Cuando no estás usando activamente el doble búfer -- durante el menú, entre niveles, durante las cinemáticas -- el banco 7 es 16KB de almacenamiento libre. Ironclaw lo usa para mantener el mapa de baldosas descomprimido del nivel actual durante el juego, liberando los bancos conmutables para gráficos y música.

### La Pila

La pila vive en la parte superior del espacio de direcciones del banco 2, creciendo hacia abajo desde `$BFFF`. Con ~14KB de código comenzando en `$8000`, la pila tiene aproximadamente 2KB de espacio -- más que suficiente para una profundidad de llamadas normal, pero debes ser vigilante. La recursión profunda no es una opción. Si estás usando salida de sprites basada en la pila (el método PUSH del Capítulo 16), recuerda que estás prestando el puntero de pila y debes guardarlo y restaurarlo con las interrupciones deshabilitadas.

---

## 21.3 La Máquina de Estados

Un juego no es un programa. Es una secuencia de modos -- pantalla de título, menú, juego, pausa, game over, puntuaciones altas -- cada uno con diferente manejo de entrada, diferente renderizado y diferente lógica de actualización. El Capítulo 18 introdujo el patrón de máquina de estados. Aquí está cómo Ironclaw lo implementa en el nivel superior.

```z80
; Game states
STATE_LOADER    equ  0
STATE_TITLE     equ  1
STATE_MENU      equ  2
STATE_GAMEPLAY  equ  3
STATE_PAUSE     equ  4
STATE_GAMEOVER  equ  5
STATE_HISCORE   equ  6
STATE_LEVELWIN  equ  7

; State handler table -- each entry is a 2-byte address
state_table:
    dw   state_loader       ; 0: loading screen + init
    dw   state_title        ; 1: title screen with animation
    dw   state_menu         ; 2: main menu (start, options, hiscores)
    dw   state_gameplay     ; 3: in-game
    dw   state_pause        ; 4: paused
    dw   state_gameover     ; 5: game over sequence
    dw   state_hiscore      ; 6: high score entry
    dw   state_levelwin     ; 7: level complete, advance

current_state:
    db   STATE_LOADER

; Main loop -- called once per frame after HALT
main_loop:
    halt                    ; wait for frame interrupt

    ; Dispatch to current state handler
    ld   a, (current_state)
    add  a, a              ; x2 for word index
    ld   l, a
    ld   h, 0
    ld   de, state_table
    add  hl, de
    ld   a, (hl)
    inc  hl
    ld   h, (hl)
    ld   l, a              ; HL = handler address
    jp   (hl)              ; jump to handler

; Each handler ends with:  jp main_loop
```

Cada manejador de estado es dueño del fotograma por completo. El manejador de juego ejecuta entrada, física, IA, renderizado y actualizaciones de HUD. El manejador de menú lee la entrada y dibuja el menú. El manejador de pausa simplemente espera la tecla de reanudación, mostrando una superposición de "PAUSED".

Las transiciones de estado ocurren escribiendo un nuevo valor en `current_state`. La transición de `STATE_GAMEPLAY` a `STATE_PAUSE` no requiere limpieza -- el estado del juego permanece intacto, y volver a `STATE_GAMEPLAY` reanuda exactamente donde lo dejaste. Pero la transición de `STATE_GAMEOVER` a `STATE_HISCORE` requiere comprobar si la puntuación del jugador califica, y la transición de `STATE_LEVELWIN` a `STATE_GAMEPLAY` requiere cargar y descomprimir los datos del siguiente nivel.

---

## 21.4 El Fotograma de Juego

Aquí es donde ocurre la integración. Durante `STATE_GAMEPLAY`, cada fotograma debe ejecutar lo siguiente, en orden:

```
1. Leer entrada                ~200 T-states
2. Actualizar física del jugador     ~800 T-states
3. Actualizar estado del jugador     ~400 T-states
4. Actualizar enemigos (IA+física)  ~4.000 T-states (8 enemigos)
5. Comprobar colisiones          ~2.000 T-states
6. Actualizar proyectiles        ~500 T-states
7. Desplazar la vista            ~8.000-15.000 T-states (depende del método)
8. Renderizar baldosas de fondo   ~12.000 T-states (columna/fila expuesta)
9. Borrar sprites antiguos        ~3.000 T-states (restaurar fondo)
10. Dibujar sprites             ~8.000 T-states (8 entidades x ~1.000 cada una)
11. Actualizar HUD               ~1.500 T-states
12. [La música suena en IM2]     ~3.000 T-states (manejador de interrupciones)
                                 ─────────────
                    Total:   ~43.400-50.400 T-states
```

En un Pentagon con 71.680 T-states por fotograma, eso deja 21.000-28.000 T-states de margen. Suena cómodo, pero es engañoso. Esas estimaciones son promedios. Cuando cuatro enemigos están en pantalla y el jugador está saltando sobre un hueco con proyectiles volando, el peor caso puede dispararse un 20-30% por encima del promedio. Tu margen es tu colchón de seguridad.

El orden importa. La entrada debe ir primero -- necesitas la intención del jugador antes de simular la física. La física debe preceder a la detección de colisiones -- necesitas saber a dónde quieren moverse las entidades antes de comprobar si pueden. La respuesta de colisión debe preceder al renderizado -- necesitas las posiciones finales antes de dibujar nada. Y los sprites deben dibujarse después del fondo, porque los sprites se superponen a las baldosas.

### Lectura de Entrada

```z80
; Read keyboard and Kempston joystick
; Returns result in A: bit 0=right, 1=left, 2=down, 3=up, 4=fire
read_input:
    ld   d, 0              ; accumulate result

    ; Kempston joystick (active high)
    in   a, ($1F)          ; Kempston port
    and  %00011111         ; mask 5 bits: fire, up, down, left, right
    ld   d, a

    ; Keyboard: QAOP + space (merge with joystick)
    ; Q = up
    ld   bc, $FBFE         ; half-row Q-T
    in   a, (c)
    bit  0, a              ; Q key
    jr   nz, .not_q
    set  3, d              ; up
.not_q:
    ; O = left
    ld   b, $DF            ; half-row Y-P
    in   a, (c)
    bit  1, a              ; O key
    jr   nz, .not_o
    set  1, d              ; left
.not_o:
    ; P = right
    bit  0, a              ; P key (same half-row)
    jr   nz, .not_p
    set  0, d              ; right
.not_p:
    ; A = down
    ld   b, $FD            ; half-row A-G
    in   a, (c)
    bit  0, a              ; A key
    jr   nz, .not_a
    set  2, d              ; down
.not_a:
    ; Space = fire
    ld   b, $7F            ; half-row space-B
    in   a, (c)
    bit  0, a              ; space
    jr   nz, .not_fire
    set  4, d              ; fire
.not_fire:

    ld   a, d
    ld   (input_state), a
    ret
```

Observa que las lecturas de teclado usan `IN A,(C)` con la dirección de semifila en B. Cada tecla se mapea a un bit en el byte de resultado. Fusionar teclado y joystick en un solo byte significa que el resto de la lógica del juego no necesita saber qué dispositivo de entrada usa el jugador.

### El Motor de Desplazamiento

El desplazamiento es la operación más costosa del fotograma. El Capítulo 17 cubrió las técnicas en detalle; aquí está cómo se integran en el juego.

Ironclaw usa el método de **desplazamiento combinado**: desplazamiento con granularidad de carácter (saltos de 8 píxeles) para la vista principal, con un desplazamiento de píxel (0-7) dentro de la ventana actual de 8 píxeles para un movimiento visual suave. Cuando el desplazamiento de píxel llega a 8, la vista se desplaza una columna de baldosas y el desplazamiento se reinicia a 0.

La vista tiene 30 caracteres de ancho (240 píxeles) y 20 caracteres de alto (160 píxeles), dejando espacio para un HUD de 2 caracteres arriba y abajo. El mapa de baldosas del nivel tiene típicamente 256-512 baldosas de ancho y 20 baldosas de alto.

Cuando la vista se desplaza una columna de baldosas, el renderizador debe:

1. Copiar 29 columnas de la pantalla actual un carácter a la izquierda (o derecha)
2. Dibujar la columna recién expuesta de baldosas del mapa de baldosas

La copia de columna es una cadena LDIR: 20 filas x 8 líneas de píxeles x 29 bytes = 4.640 bytes a 21 T-states cada uno = 97.440 T-states. Eso es más que un fotograma entero. Por eso la técnica de pantalla sombra del Capítulo 17 es esencial.

```z80
; Shadow screen double-buffer scroll
; Frame N: display screen is bank 5, draw screen is bank 7
; 1. Draw the shifted background into bank 7
; 2. Flip: set bit 3 of $7FFD to display bank 7
; Frame N+1: display screen is bank 7, draw screen is bank 5
; 3. Draw the shifted background into bank 5
; 4. Flip: clear bit 3 of $7FFD to display bank 5

flip_screen:
    ld   a, (last_bank_state)
    xor  %00001000          ; toggle screen bit (bit 3)
    ld   (last_bank_state), a
    ld   bc, $7FFD
    out  (c), a
    ret
```

Pero incluso con doble búfer, la copia completa de columna es costosa. Ironclaw optimiza esto distribuyendo el trabajo: durante el desplazamiento suave sub-baldosa (desplazamiento de píxel 1-7), no hay copia de columna -- solo cambia el desplazamiento. La costosa copia de columna ocurre solo en los límites de baldosa, aproximadamente cada 4-8 fotogramas dependiendo de la velocidad del jugador. Entre esos picos, el renderizado de desplazamiento es prácticamente gratuito.

Cuando se cruza un límite de baldosa, la copia de columna puede distribuirse en dos fotogramas usando el doble búfer: el fotograma N dibuja la mitad superior de la pantalla desplazada en el búfer trasero, el fotograma N+1 dibuja la mitad inferior y hace el cambio. El jugador ve un desplazamiento continuo porque el cambio solo ocurre cuando el búfer trasero está completo.

---

## 21.5 Integración de Sprites

Ironclaw usa sprites enmascarados OR+AND (Capítulo 16, método 2) para todas las entidades del juego. Esta es la técnica estándar: para cada píxel de sprite, AND con un byte de máscara para borrar el fondo, luego OR con los datos del sprite para establecer los píxeles.

Cada sprite de 16x16 tiene cuatro copias pre-desplazadas (Capítulo 16, método 3), una para cada alineación horizontal de 2 píxeles. Esto reduce el desplazamiento por píxel de una operación en tiempo de ejecución a una consulta de tabla. El costo: cada fotograma de sprite requiere 4 variantes x 16 líneas x 3 bytes/línea (2 bytes de datos + 1 byte de máscara, ampliados a 3 bytes para manejar el desbordamiento del desplazamiento) = 192 bytes. Pero la velocidad de renderizado baja de ~1.500 T-states a ~1.000 T-states por sprite, y con 8-10 sprites en pantalla, ese ahorro se acumula.

Los datos de sprites pre-desplazados viven en el banco 3. Durante la fase de renderizado de sprites, el renderizador pagina el banco 3, itera a través de todas las entidades activas y dibuja cada una:

```z80
; Draw all active entities
; Assumes bank 3 (sprite graphics) is paged in at $C000
render_entities:
    ld   ix, entity_array
    ld   b, MAX_ENTITIES

.loop:
    push bc

    ; Check if entity is active
    ld   a, (ix + ENT_FLAGS)
    bit  FLAG_ACTIVE, a
    jr   z, .skip

    ; Calculate screen position from world position and viewport
    ld   l, (ix + ENT_X)
    ld   h, (ix + ENT_X + 1)
    ld   de, (viewport_x)
    or   a                 ; clear carry
    sbc  hl, de            ; screen_x = world_x - viewport_x
    ; Check if on screen (0-239)
    bit  7, h
    jr   nz, .skip         ; off-screen left (negative)
    ld   a, h
    or   a
    jr   nz, .skip         ; off-screen right (> 255)
    ld   a, l
    cp   240
    jr   nc, .skip         ; off-screen right (240-255)

    ; Store screen X for sprite routine
    ld   (sprite_screen_x), a

    ; Y position (already in screen coordinates for simplicity)
    ld   a, (ix + ENT_Y)
    ld   (sprite_screen_y), a

    ; Look up sprite graphic address from type + frame + shift
    call get_sprite_address ; returns HL = address in bank 3

    ; Draw masked sprite at (sprite_screen_x, sprite_screen_y)
    call draw_sprite_masked

.skip:
    pop  bc
    ld   de, ENT_SIZE
    add  ix, de            ; next entity
    djnz .loop
    ret
```

### Restauración de Fondo (Rectángulos Sucios)

Antes de dibujar sprites en sus nuevas posiciones, debes borrarlos de sus posiciones antiguas. Ironclaw usa el método de rectángulos sucios del Capítulo 16: antes de dibujar un sprite, guarda el fondo debajo de él en un búfer. Antes de la pasada de renderizado de sprites del siguiente fotograma, restaura esos fondos guardados.

```z80
; Dirty rectangle entry: 4 bytes
;   byte 0: screen address low
;   byte 1: screen address high
;   byte 2: width in bytes
;   byte 3: height in pixel lines

; Save background before drawing sprite
save_background:
    ; HL = screen address, B = height, C = width
    ld   de, bg_save_buffer
    ld   (bg_save_ptr), de
    ; ... copy rectangle from screen to buffer ...
    ret

; Restore all saved backgrounds (called before new sprite render pass)
restore_backgrounds:
    ld   hl, dirty_rect_list
    ld   b, (hl)           ; count of dirty rectangles
    inc  hl
    or   a
    ret  z                 ; no sprites last frame

.loop:
    push bc
    ; Read rectangle descriptor
    ld   e, (hl)
    inc  hl
    ld   d, (hl)           ; DE = screen address
    inc  hl
    ld   b, (hl)           ; B = height
    inc  hl
    ld   c, (hl)           ; C = width
    inc  hl
    push hl

    ; Copy saved background back to screen
    ; ... copy from bg_save_buffer to screen ...

    pop  hl
    pop  bc
    djnz .loop
    ret
```

El costo de los rectángulos sucios es proporcional al número y tamaño de los sprites. Para 8 entidades de 16x16 píxeles (3 bytes de ancho después del desplazamiento), guardar y restaurar cuesta aproximadamente 8 x 16 x 3 x 2 (guardar + restaurar) x ~10 T-states/byte = ~7.680 T-states. No es barato, pero es predecible.

---

## 21.6 Colisiones, Física e IA en Contexto

Los Capítulos 18 y 19 cubrieron estos sistemas de forma aislada. En el juego integrado, el desafío clave es el orden: qué sistema se ejecuta primero, y qué datos necesita cada uno de los demás.

### Bucle de Física-Colisión

La actualización de física debe intercalarse con la detección de colisiones. El patrón es:

```
1. Aplicar gravedad:  velocity_y += GRAVITY
2. Aplicar entrada:    si (input_right) velocity_x += ACCEL
3. Movimiento horizontal:
     a. new_x = x + velocity_x
     b. Comprobar colisiones de baldosas en (new_x, y)
     c. Si bloqueado: empujar al límite de baldosa, velocity_x = 0
     d. Si no: x = new_x
4. Movimiento vertical:
     a. new_y = y + velocity_y
     b. Comprobar colisiones de baldosas en (x, new_y)
     c. Si bloqueado: empujar, velocity_y = 0, establecer bandera on_ground
     d. Si no: y = new_y, limpiar bandera on_ground
5. Si (on_ground Y input_jump): velocity_y = -JUMP_FORCE
```

Los movimientos horizontal y vertical están separados porque la respuesta de colisión debe manejar cada eje independientemente. Si te mueves en diagonal y golpeas una esquina, quieres deslizarte a lo largo de la pared en un eje mientras te detienes en el otro. Comprobar ambos ejes simultáneamente lleva a errores de "pegado" donde el jugador queda atrapado en esquinas.

Todas las posiciones usan formato de punto fijo 8.8 (Capítulo 4): el byte alto es la coordenada de píxel, el byte bajo es la parte fraccionaria. Los valores de velocidad también son 8.8. Esto da precisión de movimiento sub-píxel sin requerir ninguna multiplicación en el bucle principal de física -- la adición y el desplazamiento son suficientes.

```z80
; Apply gravity to entity at IX
; velocity_y is 16-bit signed, 8.8 fixed-point
apply_gravity:
    ld   l, (ix + ENT_VY)
    ld   h, (ix + ENT_VY + 1)
    ld   de, GRAVITY       ; e.g., $0040 = 0.25 pixels/frame/frame
    add  hl, de
    ; Clamp to terminal velocity
    ld   a, h
    cp   MAX_FALL_SPEED    ; e.g., 4 pixels/frame
    jr   c, .no_clamp
    ld   hl, MAX_FALL_SPEED * 256
.no_clamp:
    ld   (ix + ENT_VY), l
    ld   (ix + ENT_VY + 1), h
    ret
```

### Colisión de Baldosas

La comprobación de colisión de baldosas convierte una coordenada de píxel a un índice de baldosa, luego busca el tipo de baldosa en el mapa de colisiones del nivel:

```z80
; Check tile at pixel position (B=x, C=y)
; Returns: A = tile type (0=empty, 1=solid, 2=hazard, 3=platform)
check_tile:
    ; Convert pixel X to tile column: x / 8
    ld   a, b
    srl  a
    srl  a
    srl  a                 ; A = column (0-31)
    ld   l, a

    ; Convert pixel Y to tile row: y / 8
    ld   a, c
    srl  a
    srl  a
    srl  a                 ; A = row (0-23)

    ; Tile index = row * level_width + column
    ld   h, 0
    ld   d, h
    ld   e, a
    ; Multiply row by level_width (e.g., 256 = trivial: just use E as high byte)
    ; For level_width = 256: address = level_map + row * 256 + column
    ld   d, e              ; D = row = high byte of offset
    ld   e, l              ; E = column = low byte of offset
    ld   hl, level_collision_map
    add  hl, de
    ld   a, (hl)           ; A = tile type
    ret
```

Para Ironclaw, los anchos de nivel están establecidos en 256 baldosas. Esto no es una coincidencia -- hace que la multiplicación de fila sea trivial (el número de fila se convierte en el byte alto del desplazamiento). Un nivel de 256 baldosas de ancho a 8 píxeles por baldosa son 2.048 píxeles, aproximadamente 8,5 pantallas de ancho. Para niveles más largos, puedes usar un ancho de 512 baldosas (multiplicar la fila por 2 mediante `SLA E : RL D`), aunque esto cuesta unos pocos T-states extra por consulta.

### IA Enemiga

Cada tipo de enemigo tiene una máquina de estados finita (Capítulo 19). El estado se almacena en la estructura de entidad:

```z80
; Entity structure (16 bytes per entity)
ENT_X       equ  0    ; 16-bit, 8.8 fixed-point
ENT_Y       equ  2    ; 16-bit, 8.8 fixed-point
ENT_VX      equ  4    ; 16-bit, 8.8 fixed-point
ENT_VY      equ  6    ; 16-bit, 8.8 fixed-point
ENT_TYPE    equ  8    ; entity type (player, walker, flyer, shooter, boss)
ENT_STATE   equ  9    ; FSM state (idle, patrol, chase, attack, retreat, dying)
ENT_ANIM    equ  10   ; animation frame counter
ENT_HEALTH  equ  11   ; hit points
ENT_FLAGS   equ  12   ; bit flags: active, on_ground, facing_left, invuln, ...
ENT_TIMER   equ  13   ; general-purpose timer (attack cooldown, etc.)
ENT_AUX1    equ  14   ; type-specific data (patrol point, projectile type, etc.)
ENT_AUX2    equ  15   ; type-specific data
ENT_SIZE    equ  16

MAX_ENTITIES equ 16   ; player + 8 enemies + 7 projectiles
```

Los cuatro tipos de enemigos de Ironclaw:

1. **Walker** -- Patrulla entre dos puntos. Cuando el jugador está a menos de 64 píxeles horizontalmente, cambia al estado Chase (camina hacia el jugador). Cambia a Attack (daño por contacto) al colisionar. Vuelve a Patrol cuando el jugador se aleja o el enemigo llega a un borde.

2. **Flyer** -- Movimiento vertical en onda sinusoidal (usando la tabla de seno del Capítulo 4). Ignora las colisiones de baldosas. Persigue al jugador horizontalmente cuando está en rango. Lanza proyectiles a intervalos.

3. **Shooter** -- Estacionario. Dispara un proyectil horizontal cada N fotogramas cuando el jugador está en línea de visión (misma fila de baldosas, sin baldosas sólidas entre ellos). El proyectil es una entidad separada asignada del grupo de entidades.

4. **Boss** -- FSM multifase. Fase 1: patrullar la plataforma, disparar ráfagas dispersas. Fase 2 (por debajo del 50% de salud): movimiento más rápido, disparos dirigidos, invocar walkers. Fase 3 (por debajo del 25% de salud): enfurecimiento, disparo continuo, temblor de pantalla.

La optimización clave del Capítulo 19: la IA no se ejecuta en cada fotograma. Las actualizaciones de IA enemiga se distribuyen entre fotogramas usando un simple round-robin:

```z80
; Update AI for subset of enemies each frame
; ai_frame_counter cycles 0, 1, 2, 0, 1, 2, ...
update_enemy_ai:
    ld   a, (ai_frame_counter)
    inc  a
    cp   3
    jr   c, .no_wrap
    xor  a
.no_wrap:
    ld   (ai_frame_counter), a

    ; Only update enemies where (entity_index % 3) == ai_frame_counter
    ld   ix, entity_array + ENT_SIZE  ; skip player (index 0)
    ld   b, MAX_ENTITIES - 1
    ld   c, 0              ; entity index counter

.loop:
    push bc
    ld   a, (ix + ENT_FLAGS)
    bit  FLAG_ACTIVE, a
    jr   z, .next

    ; Check if this entity's turn
    ld   a, c
    ld   e, 3
    call mod_a_e           ; A = entity_index % 3
    ld   b, a
    ld   a, (ai_frame_counter)
    cp   b
    jr   nz, .next

    ; Run AI for this entity
    call run_entity_ai     ; dispatch based on ENT_TYPE and ENT_STATE

.next:
    pop  bc
    inc  c
    ld   de, ENT_SIZE
    add  ix, de
    djnz .loop
    ret
```

Esto significa que la IA de cada enemigo se ejecuta una vez cada 3 fotogramas. A 50 fps, eso son aún ~17 actualizaciones de IA por segundo por enemigo -- más que suficiente para un comportamiento reactivo. El ahorro es significativo: si la IA cuesta ~500 T-states por enemigo, ejecutar los 8 enemigos en cada fotograma cuesta 4.000 T-states. Ejecutar 2-3 enemigos por fotograma cuesta 1.000-1.500 T-states. La física y la detección de colisiones siguen ejecutándose en cada fotograma para un movimiento suave.

---

## 21.7 Integración de Sonido

### Música

El reproductor PT3 se ejecuta dentro del manejador de interrupciones IM2, como se mostró en la sección 21.2. El reproductor ocupa aproximadamente 1,5-2KB de código y se ejecuta una vez por fotograma, tomando ~2.500-3.500 T-states dependiendo de la complejidad de la fila de patrón actual.

Cada nivel tiene su propia pista musical. Al transicionar entre niveles, el juego:

1. Hace un fundido de salida de la pista actual (baja los volúmenes AY a 0 durante 25 fotogramas)
2. Pagina el banco de música apropiado (banco 4 o 6)
3. Inicializa el reproductor PT3 con la dirección de inicio de la nueva canción
4. Hace un fundido de entrada

El formato de datos PT3 es compacto -- un bucle musical típico de juego de 2-3 minutos se comprime a 2-4KB con Pletter, por eso dos bancos de música (4 y 6) pueden contener las seis pistas (título, cinco niveles, jefe, game over).

### Efectos de Sonido

Los efectos de sonido usan el sistema de robo de canales basado en prioridad del Capítulo 11. Cuando se dispara un efecto de sonido (el jugador salta, un enemigo muere, un proyectil se dispara), el motor de SFX secuestra temporalmente un canal AY, anulando lo que la música estaba haciendo en ese canal. Cuando el efecto termina, el canal vuelve al control de la música.

```z80
; SFX priority levels
SFX_JUMP       equ  1     ; low priority
SFX_PICKUP     equ  2
SFX_SHOOT      equ  3
SFX_HIT        equ  4
SFX_EXPLODE    equ  5     ; high priority
SFX_BOSS_DIE   equ  6     ; highest priority

; Trigger a sound effect
; A = SFX id
play_sfx:
    ; Check priority -- only play if higher than current SFX
    ld   hl, current_sfx_priority
    cp   (hl)
    ret  c                 ; current SFX has higher priority, ignore

    ; Set up SFX playback
    ld   (hl), a           ; update priority
    ; Look up SFX descriptor table
    add  a, a              ; x2 for word index
    ld   l, a
    ld   h, 0
    ld   de, sfx_table
    add  hl, de
    ld   a, (hl)
    inc  hl
    ld   h, (hl)
    ld   l, a              ; HL = SFX descriptor address

    ; SFX descriptor: duration (byte), channel (byte),
    ;                 then per-frame: freq_lo, freq_hi, volume, noise
    ld   a, (hl)
    ld   (sfx_frames_left), a
    inc  hl
    ld   a, (hl)
    ld   (sfx_channel), a
    inc  hl
    ld   (sfx_data_ptr), hl
    ret
```

La actualización de SFX se ejecuta dentro del manejador de interrupciones, después del reproductor PT3. Si un SFX está activo, sobrescribe los valores de los registros AY que el reproductor PT3 acaba de establecer para el canal secuestrado. Esto significa que la música continúa reproduciéndose correctamente en los otros dos canales, y el canal secuestrado produce el efecto de sonido.

Las definiciones de SFX son tablas procedurales en lugar de audio muestreado. Cada entrada es una secuencia de valores de registro por fotograma:

```z80
; SFX: player jump -- ascending frequency sweep on channel C
sfx_jump_data:
    db   8                 ; duration: 8 frames
    db   2                 ; channel C (0=A, 1=B, 2=C)
    ; Per-frame: freq_lo, freq_hi, volume
    db   $80, $01, 15      ; frame 1: low pitch, full volume
    db   $60, $01, 14      ; frame 2: slightly higher
    db   $40, $01, 13
    db   $20, $01, 12
    db   $00, $01, 10
    db   $E0, $00, 8
    db   $C0, $00, 5
    db   $A0, $00, 2       ; frame 8: high pitch, fading out
```

Este enfoque usa memoria despreciable (8-20 bytes por efecto) y tiempo de CPU despreciable (unas pocas docenas de T-states por fotograma para escribir 3-4 valores de registros AY).

---

## 21.8 Carga: Cinta y DivMMC

Un juego de ZX Spectrum debe cargarse de alguna manera. En los años 80, eso significaba cinta. Hoy, la mayoría de los usuarios tienen una interfaz de tarjeta SD DivMMC (o similar) ejecutando esxDOS. Ironclaw soporta ambos.

### El Archivo .tap y el Cargador BASIC

El formato de archivo `.tap` es una secuencia de bloques de datos, cada uno precedido por una longitud de 2 bytes y un byte de bandera. Un programa cargador BASIC (que es en sí mismo un bloque en el .tap) usa comandos `LOAD "" CODE` para cargar cada bloque en la dirección correcta.

La estructura .tap de Ironclaw:

```
Bloque 0:  Programa cargador BASIC (autoejecución línea 10)
Bloque 1:  Pantalla de carga (6912 bytes -> $4000)
Bloque 2:  Bloque de código principal (contenido del banco 2 -> $8000)
Bloque 3:  Datos del banco 0 (datos de nivel + baldosas, comprimidos)
Bloque 4:  Datos del banco 1 (más datos de nivel)
Bloque 5:  Datos del banco 3 (gráficos de sprites)
Bloque 6:  Datos del banco 4 (pistas musicales 1-3)
Bloque 7:  Datos del banco 6 (pistas musicales 4-6, SFX)
```

El cargador BASIC:

```basic
10 CLEAR 32767
20 LOAD "" SCREEN$
30 LOAD "" CODE
40 BORDER 0: PAPER 0: INK 0: CLS
50 RANDOMIZE USR 32768
```

La línea 10 establece RAMTOP por debajo de `$8000`, protegiendo nuestro código de la pila de BASIC. La línea 20 carga la pantalla de carga directamente en la memoria de pantalla (el `LOAD "" SCREEN$` del Spectrum hace esto automáticamente). La línea 30 carga el bloque de código principal. La línea 40 limpia la pantalla. La línea 50 salta a nuestro código en `$8000`.

Pero esto solo carga el bloque de código principal. Los datos con bancos (bloques 3-7) deben ser cargados por nuestro propio código Z80, que pagina cada banco y usa la rutina de carga de cinta de la ROM:

```z80
; Load bank data from tape
; Called after main code is running
load_bank_data:
    ; Bank 0
    ld   a, 0
    call switch_bank
    ld   ix, $C000         ; load address
    ld   de, BANK0_SIZE    ; data length
    call load_tape_block

    ; Bank 1
    ld   a, 1
    call switch_bank
    ld   ix, $C000
    ld   de, BANK1_SIZE
    call load_tape_block

    ; ... repeat for banks 3, 4, 6 ...
    ret

; Load one tape block using ROM routine
; IX = address, DE = length
load_tape_block:
    ld   a, $FF            ; data block flag (not header)
    scf                    ; carry set = LOAD (not VERIFY)
    call $0556             ; ROM tape loading routine
    ret  nc                ; carry clear = load error
    ret
```

### Carga esxDOS (DivMMC)

Para usuarios con DivMMC o hardware similar, la carga desde una tarjeta SD es dramáticamente más rápida y fiable. La API de esxDOS proporciona operaciones de archivo a través de `RST $08` seguido de un número de función:

```z80
; esxDOS function codes
F_OPEN      equ  $9A
F_CLOSE     equ  $9B
F_READ      equ  $9D
F_WRITE     equ  $9E
F_SEEK      equ  $9F
F_OPENDIR   equ  $A3
F_READDIR   equ  $A4

; esxDOS open modes
FA_READ     equ  $01
FA_WRITE    equ  $06
FA_CREATE   equ  $0E

; Open a file
; IX = pointer to null-terminated filename
; Returns: A = file handle (or carry set on error)
esx_open:
    ld   a, '*'            ; use default drive
    ld   b, FA_READ        ; open for reading
    rst  $08
    db   F_OPEN
    ret

; Read bytes from file
; A = file handle, IX = destination address, BC = byte count
; Returns: BC = bytes actually read (or carry set on error)
esx_read:
    rst  $08
    db   F_READ
    ret

; Close a file
; A = file handle
esx_close:
    rst  $08
    db   F_CLOSE
    ret
```

Ironclaw detecta si esxDOS está presente al inicio comprobando la firma de DivMMC. Si está presente, carga todos los datos desde archivos en la tarjeta SD en lugar de la cinta:

```z80
; Load game data from esxDOS
; All bank data stored in separate files on SD card
load_from_esxdos:
    ; Load bank 0: levels + tiles
    ld   a, 0
    call switch_bank
    ld   ix, filename_bank0
    call esx_open
    ret  c                 ; error -- fall back to tape
    push af                ; save file handle
    ld   ix, $C000
    ld   bc, BANK0_SIZE
    pop  af                ; A = file handle (esxDOS preserves this)
    push af
    call esx_read
    pop  af
    call esx_close

    ; Repeat for other banks...
    ; Bank 1
    ld   a, 1
    call switch_bank
    ld   ix, filename_bank1
    call esx_open
    ret  c
    ; ... (same pattern) ...

    ret

filename_bank0:  db "IRONCLAW.B0", 0
filename_bank1:  db "IRONCLAW.B1", 0
filename_bank3:  db "IRONCLAW.B3", 0
filename_bank4:  db "IRONCLAW.B4", 0
filename_bank6:  db "IRONCLAW.B6", 0
```

El código de detección:

```z80
; Detect esxDOS presence
; Sets carry if esxDOS is NOT available
detect_esxdos:
    ; Try to open a nonexistent file -- if RST $08 returns
    ; without crashing, esxDOS is present
    ld   a, '*'
    ld   b, FA_READ
    ld   ix, test_filename
    rst  $08
    db   F_OPEN
    jr   c, .not_present   ; carry set = open failed, but esxDOS handled it
    ; File actually opened -- close it and return success
    call esx_close
    or   a                 ; clear carry
    ret
.not_present:
    ; esxDOS returned an error -- it IS present, just file not found
    ; Distinguish from "RST $08 went to ROM and crashed"
    ; by checking if we're still running. If we're here, esxDOS is present.
    or   a                 ; clear carry = esxDOS present
    ret

test_filename:  db "IRONCLAW.B0", 0
```

En la práctica, el método de detección más seguro comprueba el byte de identificación de DivMMC en una dirección trampa conocida, o usa una llamada RST $08 conocida como segura. El método anterior funciona porque si esxDOS no está presente, `RST $08` salta al manejador de errores de la ROM, que para la ROM 128K en la dirección `$0008` es un retorno benigno que deja el carry limpio. El código de producción debería usar una comprobación más robusta; el patrón anterior ilustra el concepto.

---

## 21.9 Pantalla de Carga, Menú y Puntuaciones Altas

### Pantalla de Carga

La pantalla de carga es la primera impresión del jugador. Se carga como `LOAD "" SCREEN$` en el cargador BASIC, lo que significa que aparece mientras los bloques de datos restantes se cargan desde la cinta. Con esxDOS, la carga es lo suficientemente rápida como para que quieras mostrar la pantalla durante un tiempo mínimo:

```z80
show_loading_screen:
    ; Loading screen is already in screen memory ($4000) from BASIC loader
    ; If loading from esxDOS, load it explicitly:
    ld   ix, filename_screen
    call esx_open
    ret  c
    push af
    ld   ix, $4000
    ld   bc, 6912
    pop  af
    push af
    call esx_read
    pop  af
    call esx_close

    ; Minimum display time: 100 frames (2 seconds)
    ld   b, 100
.wait:
    halt
    djnz .wait
    ret

filename_screen: db "IRONCLAW.SCR", 0
```

La pantalla de carga en sí es un archivo de pantalla estándar del Spectrum: 6.144 bytes de datos de píxeles seguidos de 768 bytes de atributos, totalizando 6.912 bytes. Créala en cualquier herramienta de arte compatible con el Spectrum (ZX Paintbrush, SEViewer, o Multipaint) o convierte una imagen moderna con una herramienta de dithering.

### Pantalla de Título y Menú

El estado de pantalla de título muestra el logotipo del juego y un fondo animado, luego transiciona al menú con cualquier pulsación de tecla:

```z80
state_title:
    ; Animate background (e.g., scrolling starfield, colour cycling)
    call title_animate

    ; Check for keypress
    xor  a
    in   a, ($FE)          ; read all keyboard half-rows at once
    cpl                    ; invert (keys are active low)
    and  $1F               ; mask 5 key bits
    jr   z, .no_key
    ld   a, STATE_MENU
    ld   (current_state), a
.no_key:
    jp   main_loop
```

El menú ofrece tres opciones: Iniciar Juego, Opciones, Puntuaciones Altas. La navegación usa las teclas arriba/abajo, la selección usa disparo/enter. El menú es una máquina de estados simple dentro del manejador `STATE_MENU`:

```z80
menu_selection:
    db   0                 ; 0=Start, 1=Options, 2=HiScores

state_menu:
    ; Draw menu (only redraw on selection change)
    call draw_menu

    ; Read input
    call read_input
    ld   a, (input_state)

    ; Up
    bit  3, a
    jr   z, .not_up
    ld   a, (menu_selection)
    or   a
    jr   z, .not_up
    dec  a
    ld   (menu_selection), a
    call play_menu_beep
.not_up:

    ; Down
    ld   a, (input_state)
    bit  2, a
    jr   z, .not_down
    ld   a, (menu_selection)
    cp   2
    jr   z, .not_down
    inc  a
    ld   (menu_selection), a
    call play_menu_beep
.not_down:

    ; Fire / Enter
    ld   a, (input_state)
    bit  4, a
    jr   z, .no_fire
    ld   a, (menu_selection)
    or   a
    jr   nz, .not_start
    ; Start game
    call init_game
    ld   a, STATE_GAMEPLAY
    ld   (current_state), a
    jp   main_loop
.not_start:
    cp   1
    jr   nz, .not_options
    ; Options (toggle sound, controls, etc.)
    call show_options
    jp   main_loop
.not_options:
    ; High scores
    ld   a, STATE_HISCORE
    ld   (current_state), a
    jp   main_loop

.no_fire:
    jp   main_loop
```

### Puntuaciones Altas

Las puntuaciones altas se almacenan en una tabla de 10 entradas en el área de datos del banco 2:

```z80
; High score entry: 3 bytes name + 3 bytes BCD score = 6 bytes
; 10 entries = 60 bytes
HISCORE_COUNT equ 10
HISCORE_SIZE  equ 6

hiscore_table:
    ; Pre-filled defaults
    db   "ACE"
    db   $00, $50, $00     ; 005000 BCD
    db   "BOB"
    db   $00, $40, $00     ; 004000
    db   "CAT"
    db   $00, $30, $00     ; 003000
    ; ... 7 more entries ...
    ds   7 * HISCORE_SIZE, 0
```

Las puntuaciones usan BCD (Binary Coded Decimal) -- dos dígitos decimales por byte, tres bytes por puntuación, dando un máximo de 999.999 puntos. BCD es preferible al binario para visualización porque convertir un número binario de 24 bits a decimal en un Z80 requiere división costosa. Con BCD, la instrucción `DAA` maneja el acarreo entre dígitos automáticamente, e imprimir solo requiere enmascarar nibbles:

```z80
; Add points to score
; DE = points to add (BCD, 2 bytes, max 9999)
add_score:
    ld   hl, player_score
    ld   a, (hl)
    add  a, e
    daa                    ; adjust for BCD
    ld   (hl), a
    inc  hl
    ld   a, (hl)
    adc  a, d
    daa
    ld   (hl), a
    inc  hl
    ld   a, (hl)
    adc  a, 0
    daa
    ld   (hl), a
    ret

player_score:
    db   0, 0, 0           ; 3 bytes BCD, little-endian
```

Cuando el juego termina, el código recorre la tabla de puntuaciones altas para ver si la puntuación del jugador califica. Si es así, el juego entra en `STATE_HISCORE` para ingresar el nombre (tres caracteres, seleccionados con arriba/abajo/disparo).

En sistemas esxDOS, la tabla de puntuaciones altas puede guardarse en la tarjeta SD. En sistemas de cinta, las puntuaciones altas persisten solo durante la sesión actual.

---

## 21.10 Carga de Niveles y Descompresión

Cuando el jugador inicia un nivel o completa uno, el juego debe:

1. Paginar el banco que contiene los datos del nivel (banco 0 para niveles 1-2, banco 1 para niveles 3-5)
2. Descomprimir el mapa de baldosas en el banco 7 (el banco de pantalla sombra, reutilizado como búfer de datos durante las transiciones de nivel)
3. Descomprimir los gráficos de baldosas en un búfer en el banco 2 o banco 0
4. Inicializar el array de entidades desde la tabla de aparición del nivel
5. Reiniciar la vista a la posición de inicio del nivel
6. Reiniciar el estado del motor de desplazamiento

```z80
; Load and initialise level
; A = level number (0-4)
load_level:
    push af

    ; Determine which bank holds this level
    cp   2
    jr   nc, .bank1
    ; Levels 0-1: bank 0
    ld   a, 0
    call switch_bank
    pop  af
    push af
    ; Look up compressed data address
    add  a, a
    ld   l, a
    ld   h, 0
    ld   de, level_ptrs_bank0
    add  hl, de
    jr   .decompress
.bank1:
    ; Levels 2-4: bank 1
    ld   a, 1
    call switch_bank
    pop  af
    push af
    sub  2                 ; offset within bank 1
    add  a, a
    ld   l, a
    ld   h, 0
    ld   de, level_ptrs_bank1
    add  hl, de

.decompress:
    ; HL points to 2-byte address of compressed level data in current bank
    ld   a, (hl)
    inc  hl
    ld   h, (hl)
    ld   l, a              ; HL = compressed data source (in $C000-$FFFF)

    ; Decompress tilemap into bank 7
    ; First, save current bank and switch to bank 7
    ; BUT: bank 7 is at $4000 (shadow screen), not $C000
    ; We decompress to $C000 in a temporary bank, then copy
    ; OR: decompress directly into shadow screen at $4000

    ; Simpler approach: decompress into a buffer at $8000+ area
    ; (we have ~2KB free above our code in bank 2)
    ; For large levels, use bank 7 at $4000:
    ; Enable shadow screen banking, then write to $4000-$7FFF

    ld   de, level_buffer  ; destination in bank 2 work area
    call zx0_decompress    ; ZX0 decompressor: HL=src, DE=dest

    ; Initialise entities from spawn table
    pop  af                ; A = level number
    call init_level_entities

    ; Set viewport to level start
    ld   hl, 0
    ld   (viewport_x), hl
    ld   hl, 0
    ld   (viewport_y), hl

    ; Reset scroll state
    xor  a
    ld   (scroll_pixel_offset), a
    ld   (scroll_dirty), a

    ret
```

La elección del compresor importa aquí. Los datos de nivel se cargan una vez por nivel (durante una pantalla de transición), así que la velocidad de descompresión no es crítica -- podemos permitirnos los ~250 T-states por byte de Exomizer para la mejor tasa de compresión. Pero los gráficos de baldosas pueden necesitar descomprimirse durante el juego (si las baldosas están en bancos), así que los ~69 T-states por byte de Pletter son preferibles.

Como se discutió en el Capítulo 14, el código del descompresor en sí ocupa memoria. ZX0 con ~70 bytes es ideal para proyectos donde el espacio de código es ajustado. Ironclaw incluye tanto un descompresor ZX0 (para datos de nivel al cargar) como un descompresor Pletter (para datos de baldosas en streaming durante el juego).

---

## 21.11 Perfilado con DeZog

Has escrito todo el código. Compila. Se ejecuta. El jugador camina, los enemigos patrullan, las baldosas se desplazan, la música suena. Pero el presupuesto de fotograma se desborda en el nivel 3, donde seis enemigos y tres proyectiles están en pantalla simultáneamente. La franja del borde muestra una banda roja que se extiende más allá del área visible de la pantalla. Estás perdiendo fotogramas.

Aquí es donde DeZog se gana su lugar en tu cadena de herramientas.

### Qué es DeZog

DeZog es una extensión de VS Code que proporciona un entorno de depuración completo para programas Z80. Se conecta a emuladores (ZEsarUX, CSpect, o su propio simulador interno) y te da:

- Puntos de interrupción (por dirección, condicionales, logpoints)
- Ejecución paso a paso (step into, step over, step out)
- Observadores de registros (todos los registros Z80, actualizados en tiempo real)
- Visor de memoria (volcado hexadecimal con actualizaciones en vivo)
- Vista de desensamblado
- Pila de llamadas
- **Contador de T-states** -- la herramienta de perfilado que necesitamos

### El Flujo de Trabajo de Perfilado

La franja del borde te dice *que* estás por encima del presupuesto. DeZog te dice *dónde*.

**Paso 1: Aislar el fotograma lento.** Establece un punto de interrupción condicional al inicio del bucle principal que se dispare solo cuando una bandera de "desbordamiento de fotograma" esté activada. Añade código para activar esta bandera cuando el fotograma tome demasiado tiempo:

```z80
; At the end of the gameplay frame, before HALT:
    ; Check if we're still in the current frame
    ; (a simple approach: read the raster line via floating bus
    ;  or use a frame counter incremented by IM2)
    ld   a, (frame_overflow_flag)
    or   a
    jr   z, .ok
    ; Frame overflowed -- set debug breakpoint trigger
    nop                    ; <-- set DeZog breakpoint here
.ok:
```

**Paso 2: Medir costos de subsistemas.** El contador de T-states de DeZog te permite medir el costo exacto de cualquier sección de código. Coloca el cursor al inicio de `update_enemy_ai`, anota el contador de T-states, salta sobre la llamada y anota el nuevo valor del contador. La diferencia es el costo exacto.

Una pasada de perfilado sistemática mide cada subsistema:

```
Subsistema           T-states medidos    % del presupuesto
─────────────────────────────────────────────────
read_input                    187          0,3%
update_player_physics         743          1,0%
update_player_state           412          0,6%
update_enemy_ai             4.231          5,9%   <-- peor caso
check_all_collisions        2.847          4,0%
update_projectiles            523          0,7%
scroll_viewport            12.456         17,4%   <-- costoso
render_exposed_tiles       11.892         16,6%   <-- costoso
restore_backgrounds         3.214          4,5%
draw_sprites               10.156         14,2%   <-- costoso
update_hud                  1.389          1,9%
[IM2 music interrupt]       3.102          4,3%
─────────────────────────────────────────────────
TOTAL                      51.152         71,4%
Margen                     20.528         28,6%
```

Ese es el caso promedio. Ahora perfila el peor caso -- nivel 3, seis enemigos en pantalla, jugador cerca del borde derecho disparando un desplazamiento:

```
Subsistema           T-states medidos    % del presupuesto
─────────────────────────────────────────────────
read_input                    187          0,3%
update_player_physics         743          1,0%
update_player_state           412          0,6%
update_enemy_ai             5.891          8,2%   <-- 6 enemigos activos
check_all_collisions        4.156          5,8%   <-- más pares
update_projectiles          1.247          1,7%   <-- 3 proyectiles
scroll_viewport            14.892         20,8%   <-- desplazamiento + columna nueva
render_exposed_tiles       14.456         20,2%   <-- renderizado de columna completa
restore_backgrounds         4.821          6,7%
draw_sprites               13.892         19,4%   <-- 10 entidades
update_hud                  1.389          1,9%
[IM2 music interrupt]       3.102          4,3%
─────────────────────────────────────────────────
TOTAL                      65.188         90,9%
Margen                      6.492          9,1%
```

Solo 9% de margen en el peor caso. Eso es peligrosamente estrecho. Un enemigo más o un patrón musical complejo podrían llevarte por encima.

**Paso 3: Encontrar el cuello de botella.** La tabla de perfilado lo hace obvio: desplazamiento + renderizado de baldosas consumen el 41% del fotograma en el peor caso. El renderizado de sprites toma el 19%. La IA enemiga toma el 8%.

**Paso 4: Optimizar el cuello de botella.** Opciones, aproximadamente en orden de impacto:

1. **Distribuir el costo de desplazamiento.** En lugar de renderizar la columna nueva completa en un fotograma, renderiza la mitad en el fotograma N y la otra mitad en el fotograma N+1 usando el doble búfer (discutido en la sección 21.4). Esto reduce el pico de desplazamiento de ~29.000 a ~15.000 T-states por fotograma.

2. **Usar sprites compilados para el jugador.** El sprite del jugador siempre está en pantalla y siempre se renderiza. Cambiar de OR+AND enmascarado (Capítulo 16, método 2) a sprites compilados (método 5) ahorra ~30% por dibujo de sprite, pero aumenta el uso de memoria. Para una entidad dibujada frecuentemente, el compromiso vale la pena.

3. **Reducir el sobredibujo de sprites.** Si dos enemigos se superponen, estás dibujando píxeles que serán sobrescritos. Ordena las entidades por coordenada Y (de atrás hacia delante) y salta el dibujo de sprites completamente ocluidos. Esto ayuda en el peor caso cuando las entidades se agrupan.

4. **Ajustar la IA.** Perfila `run_entity_ai` para cada tipo de enemigo. La comprobación de línea de visión del Shooter (escanear columnas de baldosas para oclusión) es a menudo la operación de IA más costosa. Cachea el resultado: solo recomprueba la línea de visión cada 8 fotogramas en lugar de cada 3.

Después de la optimización, el peor caso baja a ~58.000 T-states, dejando 19% de margen. Eso es cómodo.

### Configuración de DeZog para Ironclaw

DeZog se conecta a un emulador que soporta su protocolo de depuración. Para desarrollo de ZX Spectrum 128K, ZEsarUX es la elección recomendada:

```json
// .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "type": "dezog",
            "request": "launch",
            "name": "Ironclaw (ZEsarUX)",
            "remoteType": "zesarux",
            "zesarux": {
                "hostname": "localhost",
                "port": 10000
            },
            "sjasmplus": [
                {
                    "path": "src/main.a80"
                }
            ],
            "topOfStack": "0xBFFF",
            "load": "build/ironclaw.sna",
            "startAutomatically": true,
            "history": {
                "reverseDebugInstructionCount": 100000
            }
        }
    ]
}
```

La configuración `history` habilita la depuración inversa -- puedes retroceder paso a paso para ver cómo llegaste a un error. Esto es invaluable para rastrear fallos de colisión donde una entidad se teletransportó a través de una pared tres fotogramas atrás.

---

## 21.12 La Cadena de Datos en Detalle

Pasar los datos desde las herramientas del artista al juego es a menudo la parte más subestimada de un proyecto. La cadena de Ironclaw convierte cuatro tipos de recursos:

### Conjuntos de Baldosas (PNG a formato de píxeles del Spectrum)

El artista dibuja las baldosas en Aseprite, Photoshop, o cualquier herramienta de pixel art como un PNG con colores indexados. Las baldosas se organizan en una cuadrícula en una sola hoja. El script de conversión:

1. Lee el PNG, verifica que es de 1 bit (blanco y negro) o indexado con colores compatibles con el Spectrum
2. Corta en baldosas de 8x8 o 16x16
3. Convierte cada baldosa al formato de píxeles entrelazado del Spectrum (donde la fila 0 está en el desplazamiento 0, la fila 1 en el desplazamiento 256, no el desplazamiento 1 -- coincidiendo con el diseño de pantalla)
4. Opcionalmente deduplica baldosas idénticas
5. Escribe un blob binario y una tabla de símbolos mapeando IDs de baldosa a desplazamientos

Para los atributos, cada baldosa también lleva un byte de color (INK + PAPER + BRIGHT). El script lo extrae de la paleta del PNG y escribe una tabla de atributos paralela.

### Hojas de Sprites (PNG a datos de sprites pre-desplazados)

Los sprites siguen una cadena similar, pero con un paso adicional: pre-desplazamiento. El script de conversión:

1. Lee la hoja de sprites PNG
2. Corta en fotogramas individuales
3. Genera una máscara para cada fotograma (cualquier píxel no de fondo produce un 0 en la máscara, el fondo produce 1)
4. Para cada fotograma, genera 4 variantes desplazadas horizontalmente (0, 2, 4, 6 píxeles de desplazamiento)
5. Cada variante desplazada se amplía en un byte (un sprite de 2 bytes de ancho se convierte en 3 bytes de ancho para contener el desbordamiento del desplazamiento)
6. Escribe bytes de datos+máscara intercalados para un renderizado eficiente

### Mapas de Niveles (JSON de Tiled a mapa de baldosas binario)

Los niveles se diseñan en Tiled, un editor de mapas de baldosas gratuito y multiplataforma. El diseñador coloca baldosas visualmente, añade capas de objetos para puntos de aparición de entidades y disparadores, y exporta como JSON o TMX.

El script de conversión:

1. Lee la exportación de Tiled
2. Extrae la capa de baldosas como un array plano de índices de baldosa
3. Extrae la capa de objetos para puntos de aparición (posiciones de enemigos, inicio del jugador, ubicaciones de ítems)
4. Genera un mapa de colisiones: para cada baldosa, busca si es sólida, plataforma, peligro o vacía (basado en un archivo de propiedades de baldosa)
5. Escribe el mapa de baldosas, mapa de colisiones y tabla de aparición como archivos binarios separados

### Música (Vortex Tracker II a PT3)

La música se compone en Vortex Tracker II, que exporta directamente a formato `.pt3`. El archivo PT3 se incrusta en los datos del banco con `INCBIN`. El código del reproductor PT3 (ampliamente disponible como ensamblador Z80 de código abierto, típicamente 1,5-2KB) se incluye en el banco de música junto con los datos de las canciones.

### Poniéndolo Todo Junto

La cadena de conversión completa para un nivel:

```
tileset.png ──→ png2tiles.py ──→ tileset.bin ──→ pletter ──→ tileset.bin.plt
                                                              │
level1.tmx ──→ map2bin.py ──→ level1_map.bin ──→ zx0 ──→ level1_map.bin.zx0
              └─→ level1_collision.bin ──→ zx0 ──→ level1_col.bin.zx0
              └─→ level1_spawns.bin (uncompressed, small)
                                                              │
player.png ──→ png2sprites.py ──→ player.bin (pre-shifted) ──┘
enemies.png ──→ png2sprites.py ──→ enemies.bin              ──┘
                                                              │
level1.pt3 ──→ (direct INCBIN) ──────────────────────────────┘
                                                              │
sjasmplus main.a80 ──→ INCBIN all of the above ──→ ironclaw.tap
```

Cada paso está automatizado por el Makefile. El artista cambia una baldosa, escribe `make` y ve el resultado en el emulador.

---

## 21.13 Formato de Lanzamiento: Construyendo el .tap

El entregable final es un archivo `.tap`. sjasmplus puede generar salida `.tap` directamente usando su directiva `SAVETAP`:

```z80
; main.a80 -- top-level assembly file

    ; Define the BASIC loader
    DEVICE ZXSPECTRUM128

    ; Page in bank 2 at $8000
    ORG $8000

    ; Include all game code
    INCLUDE "defs.a80"
    INCLUDE "banks.a80"
    INCLUDE "render.a80"
    INCLUDE "sprites.a80"
    INCLUDE "entities.a80"
    INCLUDE "physics.a80"
    INCLUDE "collisions.a80"
    INCLUDE "ai.a80"
    INCLUDE "player.a80"
    INCLUDE "hud.a80"
    INCLUDE "menu.a80"
    INCLUDE "loader.a80"
    INCLUDE "music_driver.a80"
    INCLUDE "sfx.a80"
    INCLUDE "esxdos.a80"

    ; Entry point
entry:
    di
    ld   sp, $BFFF
    call init_system
    call detect_esxdos
    jr   c, .tape_load
    call load_from_esxdos
    jr   .loaded
.tape_load:
    call load_bank_data
.loaded:
    call init_interrupts
    ei
    jp   main_loop

    ; Bank data sections
    ; Each SLOT/PAGE directive places data into the correct bank
    SLOT 3               ; use $C000 slot
    PAGE 0               ; bank 0
    ORG $C000
    INCLUDE "data/bank0_levels.a80"   ; INCBIN compressed level data

    PAGE 1               ; bank 1
    ORG $C000
    INCLUDE "data/bank1_levels.a80"

    PAGE 3               ; bank 3
    ORG $C000
    INCLUDE "data/bank3_sprites.a80"

    PAGE 4               ; bank 4
    ORG $C000
    INCLUDE "data/bank4_music.a80"

    PAGE 6               ; bank 6
    ORG $C000
    INCLUDE "data/bank6_sfx.a80"

    ; Save as .tap with BASIC loader
    SAVETAP "build/ironclaw.tap", BASIC, "Ironclaw", 10, 2
    SAVETAP "build/ironclaw.tap", CODE, "Screen", $4000, 6912, $4000
    SAVETAP "build/ironclaw.tap", CODE, "Code", $8000, $-$8000, $8000

    ; Save bank snapshots (for .sna or manual loading)
    SAVESNA "build/ironclaw.sna", entry
```

La sintaxis exacta de SAVETAP varía según la versión de sjasmplus. Para juegos 128K con datos en bancos, el enfoque más limpio es generar un snapshot `.sna` (que captura todos los estados de banco) para pruebas en emulador, y un `.tap` con un cargador BASIC más bloques de código máquina para distribución.

### Probando el Lanzamiento

Antes de publicar, prueba en al menos tres emuladores:

1. **Fuse** -- el emulador de referencia del Spectrum, temporización precisa para hardware original
2. **Unreal Speccy** -- temporización Pentagon, el estándar de la demoscene, buen depurador
3. **ZEsarUX** -- soporta bancos 128K, emulación de esxDOS, integración con DeZog

Y si es posible, prueba en hardware real con DivMMC. Los emuladores ocasionalmente difieren en casos límite de temporización, y un juego que funciona perfectamente en Fuse puede perder fotogramas en un Spectrum real debido a efectos de memoria contendida que el emulador modela ligeramente diferente.

---

## 21.14 Pulido Final

La diferencia entre un juego funcional y un juego terminado es el pulido. Aquí tienes una lista de pequeños toques que importan:

**Transiciones de pantalla.** No saltes entre pantallas instantáneamente. Un simple fundido a negro (escribir brillo decreciente en todos los atributos durante 8 fotogramas) o una cortina (limpiar columnas de izquierda a derecha durante 16 fotogramas) le da al juego un aspecto profesional. Costo: despreciable -- las transiciones ocurren entre fotogramas de juego.

**Animación de muerte.** Cuando el jugador muere, congela el juego durante 15 fotogramas, haz parpadear el sprite del jugador alternando su INK entre fotogramas, reproduce el SFX de muerte, luego reaparece. No teletransportes simplemente al jugador de vuelta al punto de control.

**Temblor de pantalla.** Cuando el jefe golpea el suelo o una explosión estalla, desplaza la vista 1-2 píxeles durante 4-6 fotogramas. En el Spectrum, puedes simular esto ajustando el desplazamiento de scroll sin mover realmente ninguna baldosa. Es casi gratis y añade un impacto enorme.

**Modo de atracción.** Después de 30 segundos en la pantalla de título sin entrada, inicia una reproducción de demostración -- graba la entrada del jugador durante una partida de prueba y reprodúcela. Así es como los juegos arcade enganchan a los transeúntes, y también funciona para juegos de Spectrum.

**Ciclo de colores.** Anima colores del texto del menú o del logotipo ciclando atributos a través de una tabla de paleta. Un ciclo de atributos de 4 bytes no cuesta esencialmente nada de CPU y hace que las pantallas estáticas se sientan vivas.

**Antirrebote de entrada.** Ignora las pulsaciones de tecla que duren menos de 2 fotogramas. Sin antirrebote, el cursor del menú saltará opciones porque la tecla se mantuvo presionada durante múltiples fotogramas. Un simple contador de fotogramas por tecla soluciona esto:

```z80
; Debounced fire button
fire_held_frames:
    db   0

check_fire:
    ld   a, (input_state)
    bit  4, a
    jr   z, .released
    ; Fire is held
    ld   a, (fire_held_frames)
    inc  a
    ld   (fire_held_frames), a
    cp   1                 ; only trigger on first frame of press
    ret                    ; Z flag set if this is the first frame
.released:
    xor  a
    ld   (fire_held_frames), a
    ret                    ; Z flag clear (no fire)
```

---

## Resumen

- **La estructura del proyecto importa.** Separa archivos fuente por subsistema, archivos de datos por tipo. Usa un Makefile para automatizar toda la cadena desde PNG/TMX hasta `.tap`.

- **Mapea la memoria cuidadosamente.** Código en el banco 2 (fijo en `$8000`), datos de nivel en los bancos 0-1, gráficos de sprites en el banco 3, música en los bancos 4 y 6, pantalla sombra en el banco 7. Mantén una copia sombra del puerto `$7FFD` -- es de solo escritura.

- **El manejador de interrupciones es dueño de la música.** El manejador IM2 pagina el banco de música, ejecuta el reproductor PT3, actualiza SFX y restaura el banco anterior. Mantenlo ligero -- ~3.000 T-states máximo.

- **El presupuesto de fotograma de juego en Pentagon es 71.680 T-states.** Un fotograma típico con desplazamiento, 8 sprites e IA cuesta ~50.000 T-states de media, ~65.000 en el peor caso. Perfila y optimiza el peor caso, no el promedio.

- **El desplazamiento es la operación individual más costosa.** Usa el método de desplazamiento combinado (LDIR a nivel de carácter + desplazamiento de píxel) con doble búfer de pantalla sombra. Distribuye la copia de columna en dos fotogramas cuando sea posible.

- **Ejecuta la IA enemiga cada 2 o 3 fotogramas.** La física y la detección de colisiones se ejecutan cada fotograma; las decisiones de IA pueden amortizarse. Esto ahorra 2.000-3.000 T-states por fotograma en el peor caso.

- **Usa esxDOS para hardware moderno.** La API `RST $08` / `F_OPEN` / `F_READ` / `F_CLOSE` es simple y rápida. Detecta DivMMC al inicio y recurre a la carga por cinta si no está presente.

- **Perfila con DeZog.** La franja del borde te dice que estás por encima del presupuesto. DeZog te dice dónde. Mide cada subsistema, encuentra el cuello de botella, optimízalo, mide de nuevo.

- **Elige el compresor adecuado para cada tarea.** Exomizer o ZX0 para carga de niveles única (mejor tasa). Pletter para streaming de baldosas durante el juego (descompresión rápida). Consulta el Capítulo 14 para el análisis completo de compromisos.

- **El pulido no es opcional.** Transiciones de pantalla, animaciones de muerte, temblor de pantalla, antirrebote de entrada y modo de atracción son la diferencia entre una demostración técnica y un juego.

- **Prueba en múltiples emuladores y hardware real.** Fuse, Unreal Speccy y ZEsarUX modelan cada uno la temporización de manera diferente. El comportamiento de DivMMC en hardware real puede diferir de la emulación de esxDOS.

---

> **Fuentes:** World of Spectrum (mapa de memoria del ZX Spectrum 128K y documentación del puerto $7FFD); Introspec "Data Compression for Modern Z80 Coding" (Hype 2017); documentación de la API de esxDOS (wiki de DivIDE/DivMMC); documentación de la extensión DeZog para VS Code (GitHub: maziac/DeZog); documentación de sjasmplus (directivas SAVETAP, DEVICE, SLOT, PAGE); especificación del formato PT3 de Vortex Tracker II; Capítulos 11, 14, 15, 16, 17, 18, 19 de este libro.
