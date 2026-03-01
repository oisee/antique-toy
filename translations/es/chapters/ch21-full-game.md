# Capítulo 21: Juego Completo -- ZX Spectrum 128K

> *"La única forma de saber si tu motor funciona es lanzar un juego."*

---

Tienes sprites (Capítulo 16). Tienes desplazamiento (Capítulo 17). Tienes un bucle de juego y sistema de entidades (Capítulo 18). Tienes colisiones, física e IA enemiga (Capítulo 19). Tienes música AY y efectos de sonido (Capítulo 11). Tienes compresión (Capítulo 14). Tienes 128K de RAM con bancos y sabes cómo direccionar cada byte (Capítulo 15).

Ahora debes poner todo en un solo binario que cargue desde cinta, muestre una pantalla de carga, presente un menú, reproduzca cinco niveles de un plataformas de desplazamiento lateral con cuatro tipos de enemigos y un jefe, registre puntuaciones máximas y quepa en un archivo `.tap`.

Este es el capítulo de integración. No aparecen técnicas nuevas aquí. En su lugar, enfrentamos los problemas que solo emergen cuando todos los subsistemas deben coexistir: contención de memoria entre bancos de gráficos y código, presupuestos de fotograma que se desbordan cuando el desplazamiento, los sprites, la música y la IA demandan su parte, sistemas de compilación que deben coordinar una docena de pasos de conversión de datos, y las mil pequeñas decisiones sobre qué va dónde en 128K de memoria con bancos.

El juego que estamos construyendo se llama *Ironclaw* -- un plataformas de desplazamiento lateral de cinco niveles protagonizado por un gato mecánico que navega una serie de suelos de fábrica cada vez más hostiles. El género es deliberado: los plataformas de desplazamiento lateral demandan cada subsistema simultáneamente y no dejan dónde esconderse. Si el desplazamiento tartamudea, lo ves. Si el renderizado de sprites desborda el fotograma, lo sientes. Si la detección de colisiones falla, el jugador cae a través del suelo. Un plataformas es la prueba de integración más difícil que un motor de juegos Z80 puede enfrentar.

---

## 21.1 Arquitectura del Proyecto

Antes de escribir una sola línea de Z80, necesitas una estructura de directorios que escale. Un juego de 128K con cinco niveles, un conjunto de baldosas, hojas de sprites, una partitura musical y efectos de sonido genera docenas de archivos de datos. Si no los organizas desde el principio, te ahogarás.

### Disposición del Directorio

```text
ironclaw/
  src/
    main.a80           -- entry point, bank switching, state machine
    render.a80          -- tile renderer, scroll engine
    sprites.a80         -- sprite drawing routines (OR+AND masked)
    entities.a80        -- entity update, spawning, despawning
    physics.a80         -- gravity, friction, jump, collision response
    collisions.a80      -- AABB and tile collision checks
    ai.a80              -- enemy FSM: patrol, chase, attack, retreat, death
    player.a80          -- player input, state, animation
    hud.a80             -- score, lives, status bar
    menu.a80            -- title screen, options, high scores
    loader.a80          -- loading screen, tape/esxDOS loader
    music_driver.a80    -- PT3 player, interrupt handler
    sfx.a80             -- sound effects engine, channel stealing
    esxdos.a80          -- DivMMC file I/O wrappers
    banks.a80           -- bank switching macros and utilities
    defs.a80            -- constants, memory map, entity structure
  data/
    levels/             -- level tilemaps (compressed)
    tiles/              -- tileset graphics
    sprites/            -- sprite sheets (pre-shifted)
    music/              -- PT3 music files
    sfx/                -- SFX definition tables
    screens/            -- loading screen, title screen
  tools/
    png2tiles.py        -- PNG tileset converter
    png2sprites.py      -- PNG sprite sheet converter (generates shifts)
    map2bin.py          -- Tiled JSON/TMX to binary tilemap
    compress.py         -- wrapper around ZX0/Pletter compression
  build/                -- compiled output (gitignored)
  Makefile              -- the build system
```

Cada archivo fuente se centra en un subsistema. Cada archivo de datos pasa por un pipeline de conversión antes de llegar al ensamblador. El directorio `tools/` contiene scripts Python que convierten formatos amigables para el artista (imágenes PNG, mapas del editor Tiled) en datos binarios listos para el ensamblador.

### El Sistema de Compilación

El Makefile es la columna vertebral del proyecto. Debe:

1. Convertir todos los gráficos de PNG a datos binarios de baldosas/sprites
2. Convertir mapas de nivel del formato Tiled a tilemaps binarios
3. Comprimir datos de nivel, bancos de gráficos y música con el compresor apropiado
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

La idea clave es el pipeline de datos. El artista exporta un conjunto de baldosas PNG desde Aseprite. El script `png2tiles.py` lo corta en baldosas de 8x8 o 16x16, convierte cada una al formato de píxeles entrelazado del Spectrum, y escribe un blob binario. El diseñador de niveles exporta un mapa `.tmx` de Tiled. El script `map2bin.py` extrae los índices de baldosas y escribe un tilemap binario compacto. El compresor comprime cada blob. Solo entonces el ensamblador hace `INCBIN` del resultado en el banco de memoria apropiado.

Este pipeline significa que el contenido del juego siempre está en formato editable (PNG, TMX), y el sistema de compilación maneja cada conversión automáticamente. Cambia una baldosa en el PNG, escribe `make`, y la nueva baldosa aparece en el juego.

---

## 21.2 Mapa de Memoria: Asignaciones de Bancos 128K

El ZX Spectrum 128K tiene ocho bancos de RAM de 16KB, numerados del 0 al 7. En cualquier momento, la CPU ve un espacio de direcciones de 64KB:

```text
$0000-$3FFF   ROM (16KB) -- BASIC or 128K editor ROM
$4000-$7FFF   Bank 5 (always) -- screen memory (normal screen)
$8000-$BFFF   Bank 2 (always) -- typically code
$C000-$FFFF   Switchable -- banks 0-7, selected via port $7FFD
```

Los bancos 5 y 2 están cableados a `$4000` y `$8000` respectivamente. Solo la ventana superior de 16KB (`$C000-$FFFF`) es conmutable. El registro de selección de banco en el puerto `$7FFD` también controla qué pantalla se muestra (banco 5 o banco 7) y qué página de ROM está activa.

```z80 id:ch21_memory_map_128k_bank_2
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

La regla crítica: **siempre almacena tu última escritura a `$7FFD`** en una variable sombra. El puerto `$7FFD` es solo de escritura -- no puedes leer el estado actual. Si necesitas cambiar un bit (digamos, cambiar la pantalla) sin perturbar la selección de banco, debes leer tu variable sombra, modificar el bit, escribir el resultado tanto al puerto como a la variable sombra.

### Asignación de Bancos de Ironclaw

Así es como Ironclaw distribuye sus 128KB entre los ocho bancos:

```text
Bank 0 ($C000)  -- Level data: tilemaps for levels 1-2 (compressed)
                   Tileset graphics (compressed)
                   Decompression buffer

Bank 1 ($C000)  -- Level data: tilemaps for levels 3-5 (compressed)
                   Boss level data and patterns
                   Enemy spawn tables

Bank 2 ($8000)  -- FIXED: Main game code
                   Player logic, physics, collisions
                   Sprite routines, entity system
                   State machine, HUD
                   ~ 14KB code, 2KB tables/buffers

Bank 3 ($C000)  -- Sprite graphics (pre-shifted x4)
                   Player: 6 frames x 4 shifts = 24 variants
                   Enemies: 4 types x 4 frames x 4 shifts = 64 variants
                   Projectiles, particles, pickups
                   ~ 12KB total

Bank 4 ($C000)  -- Music: PT3 song data (title, levels 1-3)
                   PT3 player code (resident copy)

Bank 5 ($4000)  -- FIXED: Normal screen
                   Pixel data $4000-$57FF (6,144 bytes)
                   Attributes $5800-$5AFF (768 bytes)
                   Remaining ~9KB: interrupt handler, screen buffers

Bank 6 ($C000)  -- Music: PT3 song data (levels 4-5, boss, game over)
                   SFX definition tables
                   SFX engine code

Bank 7 ($4000)  -- Shadow screen (used for double buffering)
                   Also usable as 16KB data storage when
                   not actively double-buffering
```

<!-- figure: ch21_128k_bank_allocation -->
```text
         ZX Spectrum 128K — Ironclaw Bank Allocation
         ═══════════════════════════════════════════

$0000 ┌─────────────────────────────┐
      │         ROM (16 KB)         │  BASIC / 128K editor
$4000 ├─────────────────────────────┤
      │    Bank 5 — FIXED           │  Screen pixels ($4000–$57FF)
      │    Normal screen            │  Attributes ($5800–$5AFF)
      │    + IM2 handler, buffers   │  ~9 KB free for interrupt code
$8000 ├─────────────────────────────┤
      │    Bank 2 — FIXED           │  Main game code (~14 KB)
      │    Player, physics, AI      │  Tables, buffers (~2 KB)
      │    Sprites, entities, HUD   │  Stack grows down from $BFFF
$C000 ├─────────────────────────────┤
      │    Switchable bank (0–7)    │  Selected via port $7FFD
      │    ┌───────────────────┐    │
      │    │ Bank 0: Levels 1–2│    │  Compressed tilemaps + tileset
      │    │ Bank 1: Levels 3–5│    │  Boss data, enemy spawns
      │    │ Bank 3: Sprites   │    │  Pre-shifted ×4 (24+64 variants)
      │    │ Bank 4: Music A   │    │  PT3: title, levels 1–3
      │    │ Bank 6: Music B   │    │  PT3: levels 4–5, boss; SFX
      │    │ Bank 7: Shadow scr│    │  Double buffer / data storage
      │    └───────────────────┘    │
$FFFF └─────────────────────────────┘

  Key: Banks 2 and 5 are always visible (hardwired).
       Only $C000–$FFFF is switchable.
       Port $7FFD is write-only — always shadow its state!
```

Varias cosas que observar sobre esta disposición:

**El código vive en el banco 2 (fijo).** Dado que el banco 2 siempre está mapeado en `$8000-$BFFF`, tu código principal del juego siempre es accesible. Nunca necesitas paginar código -- solo datos. Esto elimina la clase más peligrosa de error de bancos: llamar a una rutina que ha sido paginada fuera.

**Gráficos de sprites en el banco 3, separados de los datos de nivel en los bancos 0-1.** Al renderizar un fotograma, el renderizador necesita tanto gráficos de baldosas (para el fondo con desplazamiento) como gráficos de sprites (para las entidades). Si ambos estuvieran en el mismo banco conmutable, necesitarías paginar de ida y vuelta a mitad del renderizado. Al colocarlos en bancos separados, puedes paginar los datos de baldosas, renderizar el fondo, luego paginar los datos de sprites y renderizar todas las entidades, con solo dos cambios de banco por fotograma.

**La música está dividida entre los bancos 4 y 6.** El reproductor PT3 se ejecuta durante el manejador de interrupciones, que se dispara una vez por fotograma. El manejador de interrupciones debe paginar el banco de música, actualizar los registros AY, y volver a paginar al banco que el bucle principal estaba usando. Dividir la música entre dos bancos significa que el manejador de interrupciones debe saber qué banco contiene la canción actual. Lo manejamos con una variable:

```z80 id:ch21_ironclaw_bank_allocation_3
current_music_bank:
    db   4              ; bank 4 by default

im2_handler:
    push af
    push bc
    push de
    push hl
    push ix
    push iy              ; IY must be preserved -- BASIC uses it
                         ; for system variables, and PT3 players
                         ; typically use IY internally

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

    pop  iy
    pop  ix
    pop  hl
    pop  de
    pop  bc
    pop  af
    ei
    reti
```

**La pantalla sombra en el banco 7** está disponible para doble búfer durante las actualizaciones de desplazamiento (como se describe en el Capítulo 17). Cuando no estás haciendo doble búfer activamente -- durante el menú, entre niveles, durante las cinemáticas -- el banco 7 es 16KB de almacenamiento libre. Ironclaw lo usa para mantener el tilemap descomprimido del nivel actual durante el juego, liberando los bancos conmutables para gráficos y música.

### La Pila

La pila vive en la parte superior del espacio de direcciones del banco 2, creciendo hacia abajo desde `$BFFF`. Con ~14KB de código empezando en `$8000`, la pila tiene aproximadamente 2KB de espacio -- más que suficiente para la profundidad normal de llamadas, pero debes estar vigilante. La recursión profunda no es una opción. Si estás usando salida de sprites basada en la pila (el método PUSH del Capítulo 16), recuerda que estás tomando prestado el puntero de pila y debes guardarlo y restaurarlo con las interrupciones deshabilitadas.

---

## 21.3 La Máquina de Estados

Un juego no es un solo programa. Es una secuencia de modos -- pantalla de título, menú, juego, pausa, fin de partida, puntuaciones máximas -- cada uno con diferente manejo de entrada, diferente renderizado y diferente lógica de actualización. El Capítulo 18 introdujo el patrón de máquina de estados. Así es como Ironclaw lo implementa a nivel superior.

```z80 id:ch21_the_state_machine
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

Cada manejador de estado posee el fotograma completamente. El manejador de juego ejecuta entrada, física, IA, renderizado y actualizaciones del HUD. El manejador de menú lee la entrada y dibuja el menú. El manejador de pausa simplemente espera la tecla de despausa, mostrando una superposición de "PAUSED".

Las transiciones de estado ocurren escribiendo un nuevo valor en `current_state`. La transición de `STATE_GAMEPLAY` a `STATE_PAUSE` no requiere limpieza -- el estado del juego queda intacto, y volver a `STATE_GAMEPLAY` reanuda exactamente donde lo dejaste. Pero la transición de `STATE_GAMEOVER` a `STATE_HISCORE` requiere verificar si la puntuación del jugador califica, y la transición de `STATE_LEVELWIN` a `STATE_GAMEPLAY` requiere cargar y descomprimir los datos del siguiente nivel.

---

## 21.4 El Fotograma de Juego

Aquí es donde ocurre la integración. Durante `STATE_GAMEPLAY`, cada fotograma debe ejecutar lo siguiente, en orden:

```text
1. Read input                ~200 T-states
2. Update player physics     ~800 T-states
3. Update player state       ~400 T-states
4. Update enemies (AI+phys)  ~4,000 T-states (8 enemies)
5. Check collisions          ~2,000 T-states
6. Update projectiles        ~500 T-states
7. Scroll the viewport       ~8,000-15,000 T-states (depends on method)
8. Render background tiles   ~12,000 T-states (exposed column/row)
9. Erase old sprites         ~3,000 T-states (background restore)
10. Draw sprites             ~8,000 T-states (8 entities x ~1,000 each)
11. Update HUD               ~1,500 T-states
12. [Music plays in IM2]     ~3,000 T-states (interrupt handler)
                             ─────────────
                    Total:   ~43,400-50,400 T-states
```

En un Pentagon con 71.680 T-states por fotograma, eso deja 21.000-28.000 T-states de margen. Eso suena cómodo, pero es engañoso. Esas estimaciones son promedios. Cuando cuatro enemigos están en pantalla y el jugador está saltando sobre un hueco con proyectiles volando, el peor caso puede dispararse un 20-30% por encima del promedio. Tu margen es tu reserva de seguridad.

El orden importa. La entrada debe ir primero -- necesitas la intención del jugador antes de simular la física. La física debe preceder a la detección de colisiones -- necesitas saber dónde quieren moverse las entidades antes de verificar si pueden. La respuesta a colisiones debe preceder al renderizado -- necesitas posiciones finales antes de dibujar cualquier cosa. Y los sprites deben dibujarse después del fondo, porque los sprites se superponen a las baldosas.

### Lectura de Entrada

```z80 id:ch21_reading_input
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

Observa que las lecturas del teclado usan `IN A,(C)` con la dirección de semifila en B. Cada tecla se mapea a un bit en el byte de resultado. Fusionar teclado y joystick en un solo byte significa que el resto de la lógica del juego no se preocupa por qué dispositivo de entrada usa el jugador.

### El Motor de Desplazamiento

El desplazamiento es la operación más costosa del fotograma. El Capítulo 17 cubrió las técnicas en detalle; aquí vemos cómo se integran en el juego.

Ironclaw usa el método de **desplazamiento combinado**: desplazamiento de granularidad de carácter (saltos de 8 píxeles) para la ventana gráfica principal, con un desplazamiento de píxel (0-7) dentro de la ventana actual de 8 píxeles para movimiento visual suave. Cuando el desplazamiento de píxel alcanza 8, la ventana gráfica se desplaza una columna de baldosas y el desplazamiento se reinicia a 0.

La ventana gráfica tiene 30 caracteres de ancho (240 píxeles) y 20 caracteres de alto (160 píxeles), dejando espacio para un HUD de 2 caracteres arriba y abajo. El tilemap del nivel tiene típicamente 256-512 baldosas de ancho y 20 baldosas de alto.

Cuando la ventana gráfica se desplaza una columna de baldosas, el renderizador debe:

1. Copiar 29 columnas de la pantalla actual un carácter a la izquierda (o derecha)
2. Dibujar la columna de baldosas recién expuesta del tilemap

La copia de columna es una cadena LDIR: 20 filas x 8 líneas de píxeles x 29 bytes = 4.640 bytes a 21 T-states cada uno = 97.440 T-states. Eso es más que un fotograma completo. Por eso la técnica de pantalla sombra del Capítulo 17 es esencial.

```z80 id:ch21_the_scroll_engine
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

Pero incluso con doble búfer, la copia completa de columna es costosa. Ironclaw optimiza esto distribuyendo el trabajo: durante el desplazamiento suave sub-baldosa (desplazamiento de píxel 1-7), no hay copia de columna -- solo cambia el desplazamiento. La costosa copia de columna ocurre solo en los límites de baldosa, aproximadamente cada 4-8 fotogramas dependiendo de la velocidad del jugador. Entre esos picos, el renderizado del desplazamiento es prácticamente gratuito.

Cuando se cruza un límite de baldosa, la copia de columna puede distribuirse en dos fotogramas usando el doble búfer: el fotograma N dibuja la mitad superior de la pantalla desplazada en el búfer trasero, el fotograma N+1 dibuja la mitad inferior y hace el cambio. El jugador ve un desplazamiento continuo porque el cambio solo ocurre cuando el búfer trasero está completo.

---

## 21.5 Integración de Sprites

Ironclaw usa sprites enmascarados OR+AND (Capítulo 16, método 2) para todas las entidades del juego. Esta es la técnica estándar: para cada píxel del sprite, haz AND con un byte de máscara para limpiar el fondo, luego OR con los datos del sprite para establecer los píxeles.

Cada sprite de 16x16 tiene cuatro copias pre-desplazadas (Capítulo 16, método 3), una para cada alineación horizontal de 2 píxeles. Esto reduce el desplazamiento por píxel de una operación en tiempo de ejecución a una consulta de tabla. El coste: cada fotograma de sprite requiere 4 variantes x 16 líneas x 3 bytes/línea (2 bytes de datos + 1 byte de máscara, ampliado a 3 bytes para manejar el desbordamiento del desplazamiento) = 192 bytes. Pero la velocidad de renderizado baja de ~1.500 T-states a ~1.000 T-states por sprite, y con 8-10 sprites en pantalla, ese ahorro se acumula.

Los datos de sprites pre-desplazados viven en el banco 3. Durante la fase de renderizado de sprites, el renderizador pagina el banco 3, itera a través de todas las entidades activas, y dibuja cada una:

```z80 id:ch21_sprite_integration
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

Antes de dibujar sprites en sus nuevas posiciones, debes borrarlos de sus posiciones antiguas. Ironclaw usa el método de rectángulos sucios del Capítulo 16: antes de dibujar un sprite, guarda el fondo debajo de él en un búfer. Antes del paso de renderizado de sprites del siguiente fotograma, restaura esos fondos guardados.

```z80 id:ch21_background_restore_dirty
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

El coste de los rectángulos sucios es proporcional al número y tamaño de los sprites. Para 8 entidades de 16x16 píxeles (3 bytes de ancho tras el desplazamiento), guardar y restaurar cuesta aproximadamente 8 x 16 x 3 x 2 (guardar + restaurar) x ~10 T-states/byte = ~7.680 T-states. No es barato, pero es predecible.

---

## 21.6 Colisiones, Física e IA en Contexto

Los Capítulos 18 y 19 cubrieron estos sistemas de forma aislada. En el juego integrado, el desafío clave es el orden: qué sistema se ejecuta primero, y qué datos necesita cada uno de los demás.

### Bucle de Física-Colisión

La actualización de física debe intercalarse con la detección de colisiones. El patrón es:

```text
1. Apply gravity:  velocity_y += GRAVITY
2. Apply input:    if (input_right) velocity_x += ACCEL
3. Horizontal move:
     a. new_x = x + velocity_x
     b. Check tile collisions at (new_x, y)
     c. If blocked: push back to tile boundary, velocity_x = 0
     d. Else: x = new_x
4. Vertical move:
     a. new_y = y + velocity_y
     b. Check tile collisions at (x, new_y)
     c. If blocked: push back, velocity_y = 0, set on_ground flag
     d. Else: y = new_y, clear on_ground flag
5. If (on_ground AND input_jump): velocity_y = -JUMP_FORCE
```

Los movimientos horizontal y vertical están separados porque la respuesta a colisiones debe manejar cada eje de forma independiente. Si te mueves en diagonal y golpeas una esquina, quieres deslizarte a lo largo de la pared en un eje mientras te detienes en el otro. Verificar ambos ejes simultáneamente lleva a errores de "pegado" donde el jugador queda atrapado en las esquinas.

Todas las posiciones usan formato de punto fijo 8.8 (Capítulo 4): el byte alto es la coordenada del píxel, el byte bajo es la parte fraccional. Los valores de velocidad también son 8.8. Esto da precisión de movimiento sub-píxel sin requerir ninguna multiplicación en el bucle central de física -- la suma y el desplazamiento son suficientes.

```z80 id:ch21_physics_collision_loop_2
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

### Colisión con Baldosas

La verificación de colisión con baldosas convierte una coordenada de píxel a un índice de baldosa, luego busca el tipo de baldosa en el mapa de colisión del nivel:

```z80 id:ch21_tile_collision
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

Para Ironclaw, los anchos de nivel se fijan en 256 baldosas. Esto no es una coincidencia -- hace que la multiplicación de fila sea trivial (el número de fila se convierte en el byte alto del desplazamiento). Un nivel de 256 baldosas de ancho a 8 píxeles por baldosa son 2.048 píxeles, aproximadamente 8,5 pantallas de ancho. Para niveles más largos, puedes usar un ancho de 512 baldosas (multiplica la fila por 2 mediante `SLA E : RL D`), aunque esto cuesta algunos T-states extra por consulta.

### IA Enemiga

Cada tipo de enemigo tiene una máquina de estados finitos (Capítulo 19). El estado se almacena en la estructura de entidad:

```z80 id:ch21_enemy_ai
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

1. **Caminante** -- Patrulla entre dos puntos. Cuando el jugador está a menos de 64 píxeles horizontalmente, cambia al estado Persecución (camina hacia el jugador). Cambia a Ataque (daño por contacto) en colisión. Vuelve a Patrulla cuando el jugador se aleja o el enemigo llega a un borde.

2. **Volador** -- Movimiento vertical en onda senoidal (usando la tabla de seno del Capítulo 4). Ignora colisiones con baldosas. Persigue al jugador horizontalmente cuando está dentro del alcance. Lanza proyectiles a intervalos.

3. **Tirador** -- Estacionario. Dispara un proyectil horizontal cada N fotogramas cuando el jugador está dentro de la línea de visión (misma fila de baldosas, sin baldosas sólidas entre ambos). El proyectil es una entidad separada asignada de la piscina de entidades.

4. **Jefe** -- Máquina de estados multifase. Fase 1: patrullar plataforma, disparar ráfagas dispersas. Fase 2 (por debajo del 50% de salud): movimiento más rápido, disparos dirigidos, convoca caminantes. Fase 3 (por debajo del 25% de salud): enfurecimiento, disparo continuo, sacudida de pantalla.

La optimización clave del Capítulo 19: la IA no se ejecuta cada fotograma. Las actualizaciones de IA enemiga se distribuyen entre fotogramas usando un round-robin simple:

```z80 id:ch21_enemy_ai_2
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

Esto significa que la IA de cada enemigo se ejecuta una vez cada 3 fotogramas. A 50 fps, eso sigue siendo ~17 actualizaciones de IA por segundo por enemigo -- más que suficiente para un comportamiento reactivo. El ahorro es significativo: si la IA cuesta ~500 T-states por enemigo, ejecutar los 8 enemigos cada fotograma cuesta 4.000 T-states. Ejecutar 2-3 enemigos por fotograma cuesta 1.000-1.500 T-states. La física y la detección de colisiones siguen ejecutándose cada fotograma para un movimiento suave.

---

## 21.7 Integración de Sonido

### Música

El reproductor PT3 se ejecuta dentro del manejador de interrupciones IM2, como se mostró en la sección 21.2. El reproductor ocupa aproximadamente 1,5-2KB de código y se ejecuta una vez por fotograma, tomando ~2.500-3.500 T-states dependiendo de la complejidad de la fila del patrón actual.

Cada nivel tiene su propia pista musical. Al transicionar entre niveles, el juego:

1. Hace fade out de la pista actual (rampa de volúmenes AY a 0 durante 25 fotogramas)
2. Pagina el banco de música apropiado (banco 4 o 6)
3. Inicializa el reproductor PT3 con la dirección de inicio de la nueva canción
4. Hace fade in

El formato de datos PT3 es compacto -- un bucle musical típico de 2-3 minutos se comprime a 2-4KB con Pletter, por lo que dos bancos de música (4 y 6) pueden albergar las seis pistas (título, cinco niveles, jefe, fin de partida).

### Efectos de Sonido

Los efectos de sonido usan el sistema de robo de canal basado en prioridades del Capítulo 11. Cuando se dispara un efecto de sonido (el jugador salta, un enemigo muere, un proyectil se dispara), el motor SFX secuestra temporalmente un canal AY, anulando lo que la música estaba haciendo en ese canal. Cuando el efecto termina, el canal vuelve al control de la música.

```z80 id:ch21_sound_effects
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

La actualización SFX se ejecuta dentro del manejador de interrupciones, después del reproductor PT3. Si un SFX está activo, sobrescribe los valores de registro AY que el reproductor PT3 acaba de establecer para el canal robado. Esto significa que la música continúa reproduciéndose correctamente en los otros dos canales, y el canal robado produce el efecto de sonido.

Las definiciones SFX son tablas procedurales en lugar de audio muestreado. Cada entrada es una secuencia de valores de registro por fotograma:

```z80 id:ch21_sound_effects_2
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

Este enfoque usa memoria despreciable (8-20 bytes por efecto) y tiempo de CPU despreciable (unas pocas docenas de T-states por fotograma para escribir 3-4 valores de registro AY).

---

## 21.8 Carga: Cinta y DivMMC

Un juego de ZX Spectrum debe cargarse de alguna manera. En los años 80, eso significaba cinta. Hoy, la mayoría de usuarios tienen un DivMMC (o similar) con interfaz de tarjeta SD ejecutando esxDOS. Ironclaw soporta ambos.

### El Archivo .tap y el Cargador BASIC

El formato de archivo `.tap` es una secuencia de bloques de datos, cada uno precedido por una longitud de 2 bytes y un byte de bandera. Un programa cargador BASIC (en sí mismo un bloque en el .tap) usa comandos `LOAD "" CODE` para cargar cada bloque en la dirección correcta.

Estructura del .tap de Ironclaw:

```text
Block 0:  BASIC loader program (autorun line 10)
Block 1:  Loading screen (6912 bytes -> $4000)
Block 2:  Main code block (bank 2 content -> $8000)
Block 3:  Bank 0 data (level data + tiles, compressed)
Block 4:  Bank 1 data (more level data)
Block 5:  Bank 3 data (sprite graphics)
Block 6:  Bank 4 data (music tracks 1-3)
Block 7:  Bank 6 data (music tracks 4-6, SFX)
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

```z80 id:ch21_the_tap_file_and_basic_loader_3
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

Para usuarios con un DivMMC o hardware similar, la carga desde tarjeta SD es dramáticamente más rápida y fiable. La API esxDOS proporciona operaciones de archivo a través de `RST $08` seguido de un número de función:

```z80 id:ch21_esxdos_loading_divmmc
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

Ironclaw detecta si esxDOS está presente al inicio comprobando la firma del DivMMC. Si está presente, carga todos los datos desde archivos en la tarjeta SD en lugar de la cinta:

```z80 id:ch21_esxdos_loading_divmmc_2
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

```z80 id:ch21_esxdos_loading_divmmc_3
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

En la práctica, el método de detección más seguro comprueba el byte de identificación del DivMMC en una dirección trampa conocida, o usa una llamada RST $08 conocida como segura. El método anterior funciona porque si esxDOS no está presente, `RST $08` salta al manejador de errores de la ROM, que para la ROM 128K en la dirección `$0008` es un retorno benigno que deja el carry limpio. El código de producción debería usar una comprobación más robusta; el patrón anterior ilustra el concepto.

---

## 21.9 Pantalla de Carga, Menú y Puntuaciones Máximas

### Pantalla de Carga

La pantalla de carga es la primera impresión del jugador. Se carga como `LOAD "" SCREEN$` en el cargador BASIC, lo que significa que aparece mientras los bloques de datos restantes se cargan desde la cinta. En esxDOS, la carga es lo suficientemente rápida como para que quieras mostrar la pantalla durante una duración mínima:

```z80 id:ch21_loading_screen
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

El estado de pantalla de título muestra el logo del juego y un fondo animado, luego transiciona al menú con cualquier pulsación:

```z80 id:ch21_title_screen_and_menu
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

El menú ofrece tres opciones: Empezar Juego, Opciones, Puntuaciones Máximas. La navegación usa las teclas arriba/abajo, la selección usa disparo/enter. El menú es una máquina de estados simple dentro del manejador `STATE_MENU`:

```z80 id:ch21_title_screen_and_menu_2
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

### Puntuaciones Máximas

Las puntuaciones máximas se almacenan en una tabla de 10 entradas en el área de datos del banco 2:

```z80 id:ch21_high_scores
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

Las puntuaciones usan BCD (Decimal Codificado en Binario) -- dos dígitos decimales por byte, tres bytes por puntuación, dando un máximo de 999.999 puntos. BCD es preferible al binario para la visualización porque convertir un número binario de 24 bits a decimal en un Z80 requiere divisiones costosas. Con BCD, la instrucción `DAA` maneja el acarreo entre dígitos automáticamente, e imprimir solo requiere enmascarar nibbles:

```z80 id:ch21_high_scores_2
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

Cuando el juego termina, el código recorre la tabla de puntuaciones máximas para ver si la puntuación del jugador califica. Si lo hace, el juego entra en `STATE_HISCORE` para la entrada de nombre (tres caracteres, seleccionados con arriba/abajo/disparo).

En sistemas esxDOS, la tabla de puntuaciones máximas puede guardarse en la tarjeta SD. En sistemas de cinta, las puntuaciones máximas persisten solo durante la sesión actual.

---

## 21.10 Carga de Nivel y Descompresión

Cuando el jugador comienza un nivel o completa uno, el juego debe:

1. Paginar el banco que contiene los datos del nivel (banco 0 para niveles 1-2, banco 1 para niveles 3-5)
2. Descomprimir el tilemap en el banco 7 (el banco de pantalla sombra, reutilizado como búfer de datos durante las transiciones de nivel)
3. Descomprimir los gráficos de baldosas en un búfer en el banco 2 o banco 0
4. Inicializar el array de entidades desde la tabla de generación del nivel
5. Reiniciar la ventana gráfica a la posición de inicio del nivel
6. Reiniciar el estado del motor de desplazamiento

```z80 id:ch21_level_loading_and
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

Como se discutió en el Capítulo 14, el código del descompresor en sí ocupa memoria. ZX0 con ~70 bytes es ideal para proyectos donde el espacio de código es ajustado. Ironclaw incluye tanto un descompresor ZX0 (para datos de nivel en tiempo de carga) como un descompresor Pletter (para datos de baldosas en flujo durante el juego).

---

## 21.11 Perfilado con DeZog

Has escrito todo el código. Compila. Se ejecuta. El jugador camina, los enemigos patrullan, las baldosas se desplazan, la música suena. Pero el presupuesto de fotograma se desborda en el nivel 3, donde seis enemigos y tres proyectiles están en pantalla simultáneamente. La franja del borde muestra una banda roja que se extiende más allá del área visible de la pantalla. Estás perdiendo fotogramas.

Aquí es donde DeZog se gana su lugar en tu cadena de herramientas.

### ¿Qué es DeZog?

DeZog es una extensión de VS Code que proporciona un entorno completo de depuración para programas Z80. Se conecta a emuladores (ZEsarUX, CSpect, o su propio simulador interno) y te da:

- Puntos de interrupción (por dirección, condicionales, logpoints)
- Ejecución paso a paso (entrar, pasar por encima, salir)
- Inspección de registros (todos los registros Z80, actualizados en tiempo real)
- Visor de memoria (volcado hexadecimal con actualizaciones en vivo)
- Vista de desensamblado
- Pila de llamadas
- **Contador de T-states** -- la herramienta de perfilado que necesitamos

### El Flujo de Trabajo de Perfilado

La franja del borde te dice *que* estás por encima del presupuesto. DeZog te dice *dónde*.

**Paso 1: Aislar el fotograma lento.** Establece un punto de interrupción condicional al inicio del bucle principal que se active solo cuando una bandera de "desbordamiento de fotograma" esté establecida. Añade código para establecer esta bandera cuando el fotograma tarda demasiado:

```z80 id:ch21_the_profiling_workflow
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

**Paso 2: Medir costes de subsistemas.** El contador de T-states de DeZog te permite medir el coste exacto de cualquier sección de código. Coloca el cursor al inicio de `update_enemy_ai`, anota el contador de T-states, pasa por encima de la llamada, y anota el nuevo valor del contador. La diferencia es el coste exacto.

Un pase de perfilado sistemático mide cada subsistema:

```text
Subsystem            Measured T-states   Budget %
─────────────────────────────────────────────────
read_input                    187          0.3%
update_player_physics         743          1.0%
update_player_state           412          0.6%
update_enemy_ai             4,231          5.9%   <-- worst case
check_all_collisions        2,847          4.0%
update_projectiles            523          0.7%
scroll_viewport            12,456         17.4%   <-- expensive
render_exposed_tiles       11,892         16.6%   <-- expensive
restore_backgrounds         3,214          4.5%
draw_sprites               10,156         14.2%   <-- expensive
update_hud                  1,389          1.9%
[IM2 music interrupt]       3,102          4.3%
─────────────────────────────────────────────────
TOTAL                      51,152         71.4%
Slack                      20,528         28.6%
```

Ese es el caso promedio. Ahora perfila el peor caso -- nivel 3, seis enemigos en pantalla, jugador cerca del borde derecho activando un desplazamiento:

```text
Subsystem            Measured T-states   Budget %
─────────────────────────────────────────────────
read_input                    187          0.3%
update_player_physics         743          1.0%
update_player_state           412          0.6%
update_enemy_ai             5,891          8.2%   <-- 6 enemies active
check_all_collisions        4,156          5.8%   <-- more pairs
update_projectiles          1,247          1.7%   <-- 3 projectiles
scroll_viewport            14,892         20.8%   <-- scroll + new column
render_exposed_tiles       14,456         20.2%   <-- full column render
restore_backgrounds         4,821          6.7%
draw_sprites               13,892         19.4%   <-- 10 entities
update_hud                  1,389          1.9%
[IM2 music interrupt]       3,102          4.3%
─────────────────────────────────────────────────
TOTAL                      65,188         90.9%
Slack                       6,492          9.1%
```

Solo 9% de margen en el peor caso. Eso es peligrosamente ajustado. Un enemigo más o un patrón musical complejo podría empujarte por encima.

**Paso 3: Encontrar el cuello de botella.** La tabla de perfilado lo hace obvio: desplazamiento + renderizado de baldosas consumen el 41% del fotograma en el peor caso. Renderizado de sprites toma el 19%. IA enemiga toma el 8%.

**Paso 4: Optimizar el cuello de botella.** Opciones, aproximadamente en orden de impacto:

1. **Distribuir el coste del desplazamiento.** En lugar de renderizar la nueva columna completa en un fotograma, renderiza la mitad en el fotograma N y la mitad en el fotograma N+1 usando el doble búfer (discutido en la sección 21.4). Esto corta el pico del desplazamiento de ~29.000 a ~15.000 T-states por fotograma.

2. **Usar sprites compilados para el jugador.** El sprite del jugador siempre está en pantalla y siempre se renderiza. Cambiar de enmascarado OR+AND (Capítulo 16, método 2) a sprites compilados (método 5) ahorra ~30% por dibujo de sprite, pero incrementa el uso de memoria. Para una entidad dibujada frecuentemente, la compensación vale la pena.

3. **Reducir el sobredibujo de sprites.** Si dos enemigos se superponen, estás dibujando píxeles que serán sobrescritos. Ordena las entidades por coordenada Y (de atrás hacia adelante) y salta el dibujo de sprites totalmente ocluidos. Esto ayuda en el peor caso cuando las entidades se agrupan.

4. **Ajustar la IA.** Perfila `run_entity_ai` para cada tipo de enemigo. La verificación de línea de visión del Tirador (escanear columnas de baldosas para oclusión) es a menudo la operación de IA más costosa. Almacena el resultado en caché: solo re-verifica la línea de visión cada 8 fotogramas en lugar de cada 3.

Tras la optimización, el peor caso baja a ~58.000 T-states, dejando un 19% de margen. Eso es cómodo.

### Configuración de DeZog para Ironclaw

DeZog se conecta a un emulador que soporte su protocolo de depuración. Para desarrollo de ZX Spectrum 128K, ZEsarUX es la opción recomendada:

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

La configuración `history` habilita la depuración inversa -- puedes retroceder paso a paso para ver cómo llegaste a un error. Esto es invaluable para rastrear errores de colisión donde una entidad se teletransportó a través de una pared tres fotogramas atrás.

---

## 21.12 El Pipeline de Datos en Detalle

Llevar datos desde las herramientas del artista al juego es a menudo la parte más subestimada de un proyecto. El pipeline de Ironclaw convierte cuatro tipos de assets:

### Conjuntos de Baldosas (PNG a formato de píxeles del Spectrum)

El artista dibuja baldosas en Aseprite, Photoshop, o cualquier herramienta de pixel art como un PNG de color indexado. Las baldosas se arreglan en una cuadrícula en una sola hoja. El script de conversión:

1. Lee el PNG, verifica que sea de 1 bit (blanco y negro) o indexado con colores compatibles con el Spectrum
2. Corta en baldosas de 8x8 o 16x16
3. Convierte cada baldosa al formato de píxeles entrelazado del Spectrum (donde la fila 0 está en el desplazamiento 0, la fila 1 en el desplazamiento 256, no en el desplazamiento 1 -- coincidiendo con la disposición de la pantalla)
4. Opcionalmente deduplica baldosas idénticas
5. Escribe un blob binario y una tabla de símbolos mapeando IDs de baldosas a desplazamientos

Para atributos, cada baldosa también lleva un byte de color (tinta + papel + brillo). El script extrae esto de la paleta del PNG y escribe una tabla de atributos paralela.

### Hojas de Sprites (PNG a datos de sprites pre-desplazados)

Los sprites siguen un pipeline similar, pero con un paso adicional: pre-desplazamiento. El script de conversión:

1. Lee la hoja de sprites PNG
2. Corta en fotogramas individuales
3. Genera una máscara para cada fotograma (cualquier píxel no-fondo produce un 0 en la máscara, el fondo produce 1)
4. Para cada fotograma, genera 4 variantes desplazadas horizontalmente (0, 2, 4, 6 píxeles de desplazamiento)
5. Cada variante desplazada se amplía un byte (un sprite de 2 bytes de ancho se convierte en 3 bytes de ancho para contener el desbordamiento del desplazamiento)
6. Escribe bytes de datos+máscara entrelazados para renderizado eficiente

### Mapas de Nivel (JSON de Tiled a tilemap binario)

Los niveles se diseñan en Tiled, un editor de tilemaps gratuito y multiplataforma. El diseñador coloca baldosas visualmente, añade capas de objetos para puntos de generación de entidades y disparadores, y exporta como JSON o TMX.

El script de conversión:

1. Lee la exportación de Tiled
2. Extrae la capa de baldosas como un array plano de índices de baldosas
3. Extrae la capa de objetos para puntos de generación (posiciones de enemigos, inicio del jugador, ubicaciones de objetos)
4. Genera un mapa de colisión: para cada baldosa, busca si es sólida, una plataforma, un peligro o vacía (basándose en un archivo de propiedades de baldosas)
5. Escribe el tilemap, el mapa de colisión y la tabla de generación como archivos binarios separados

### Música (Vortex Tracker II a PT3)

La música se compone en Vortex Tracker II, que exporta directamente al formato `.pt3`. El archivo PT3 se incrusta en los datos del banco con `INCBIN`. El código del reproductor PT3 (ampliamente disponible como ensamblador Z80 de código abierto, típicamente 1,5-2KB) se incluye en el banco de música junto con los datos de la canción.

### Juntando Todo

El pipeline de conversión completo para un nivel:

```text
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

Cada paso está automatizado por el Makefile. El artista cambia una baldosa, escribe `make`, y ve el resultado en el emulador.

---

## 21.13 Formato de Lanzamiento: Construyendo el .tap

El entregable final es un archivo `.tap`. sjasmplus puede generar salida `.tap` directamente usando su directiva `SAVETAP`:

```z80 id:ch21_release_format_building_the
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

La sintaxis exacta de SAVETAP varía según la versión de sjasmplus. Para juegos 128K con datos de bancos, el enfoque más limpio es generar un snapshot `.sna` (que captura todos los estados de los bancos) para pruebas en emulador, y un `.tap` con un cargador BASIC más bloques de código máquina para distribución.

### Probando el Lanzamiento

Antes de publicar, prueba en al menos tres emuladores:

1. **Fuse** -- el emulador de Spectrum de referencia, temporizado preciso para hardware original
2. **Unreal Speccy** -- temporizado Pentagon, el estándar de la demoscene, buen depurador
3. **ZEsarUX** -- soporta bancos 128K, emulación esxDOS, integración con DeZog

Y si es posible, prueba en hardware real con un DivMMC. Los emuladores ocasionalmente difieren en casos extremos de temporizado, y un juego que funciona perfectamente en Fuse puede perder fotogramas en un Spectrum real debido a efectos de memoria contendida que el emulador modela ligeramente diferente.

---

## 21.14 Pulido Final

La diferencia entre un juego funcional y un juego terminado es el pulido. Aquí hay una lista de verificación de pequeños detalles que importan:

**Transiciones de pantalla.** No saltes entre pantallas instantáneamente. Un simple fundido a negro (escribe brillo decreciente en todos los atributos durante 8 fotogramas) o una cortina (limpia columnas de izquierda a derecha durante 16 fotogramas) le da al juego una sensación profesional. Coste: despreciable -- las transiciones ocurren entre fotogramas de juego.

**Animación de muerte.** Cuando el jugador muere, congela el juego durante 15 fotogramas, haz parpadear el sprite del jugador alternando su tinta entre fotogramas, reproduce el SFX de muerte, luego reaparece. No simplemente teletransportes al jugador de vuelta al punto de control.

**Sacudida de pantalla.** Cuando el jefe golpea el suelo o una explosión ocurre, desplaza la ventana gráfica 1-2 píxeles durante 4-6 fotogramas. En el Spectrum, puedes falsificar esto ajustando el desplazamiento del scroll sin realmente mover ninguna baldosa. Es casi gratuito y añade un enorme impacto.

**Modo atracción.** Después de 30 segundos en la pantalla de título sin entrada, inicia una reproducción de demo -- graba la entrada del jugador durante una partida de prueba y reprodúcela. Así es como las máquinas recreativas enganchan a los transeúntes, y también funciona para juegos de Spectrum.

**Ciclo de colores.** Anima los colores del texto del menú o del logo ciclando atributos a través de una tabla de paleta. Un ciclo de atributos de 4 bytes cuesta esencialmente cero CPU y hace que las pantallas estáticas se sientan vivas.

**Antirrebote de entrada.** Ignora pulsaciones que duren menos de 2 fotogramas. Sin antirrebote, el cursor del menú saltará opciones porque la tecla se mantuvo durante múltiples fotogramas. Un simple contador de fotogramas por tecla arregla esto:

```z80 id:ch21_final_polish
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

- **La estructura del proyecto importa.** Separa archivos fuente por subsistema, archivos de datos por tipo. Usa un Makefile para automatizar el pipeline completo desde PNG/TMX hasta `.tap`.

- **Mapea la memoria cuidadosamente.** Código en el banco 2 (fijo en `$8000`), datos de nivel en los bancos 0-1, gráficos de sprites en el banco 3, música en los bancos 4 y 6, pantalla sombra en el banco 7. Mantén una copia sombra del puerto `$7FFD` -- es solo de escritura.

- **El manejador de interrupciones es dueño de la música.** El manejador IM2 pagina el banco de música, ejecuta el reproductor PT3, actualiza SFX, y restaura el banco anterior. Mantenlo ligero -- máximo ~3.000 T-states.

- **El presupuesto de fotograma de juego en Pentagon es 71.680 T-states.** Un fotograma típico con desplazamiento, 8 sprites y IA cuesta ~50.000 T-states de promedio, ~65.000 en el peor caso. Perfila y optimiza el peor caso, no el promedio.

- **El desplazamiento es la operación individual más costosa.** Usa el método de desplazamiento combinado (LDIR a nivel de carácter + desplazamiento de píxel) con doble búfer de pantalla sombra. Distribuye la copia de columna en dos fotogramas cuando sea posible.

- **Ejecuta la IA enemiga cada 2 o 3 fotogramas.** La física y la detección de colisiones se ejecutan cada fotograma; las decisiones de IA pueden amortizarse. Esto ahorra 2.000-3.000 T-states por fotograma en el peor caso.

- **Usa esxDOS para hardware moderno.** La API `RST $08` / `F_OPEN` / `F_READ` / `F_CLOSE` es simple y rápida. Detecta DivMMC al inicio y recurre a la carga por cinta si está ausente.

- **Perfila con DeZog.** La franja del borde te dice que estás por encima del presupuesto. DeZog te dice dónde. Mide cada subsistema, encuentra el cuello de botella, optimízalo, mide de nuevo.

- **Elige el compresor correcto para cada trabajo.** Exomizer o ZX0 para carga de nivel única (mejor tasa). Pletter para transmisión de baldosas durante el juego (descompresión rápida). Ver Capítulo 14 para el análisis completo de compensaciones.

- **El pulido no es opcional.** Las transiciones de pantalla, animaciones de muerte, sacudida de pantalla, antirrebote de entrada y modo atracción son la diferencia entre una demo técnica y un juego.

- **Prueba en múltiples emuladores y hardware real.** Fuse, Unreal Speccy y ZEsarUX cada uno modela el temporizado de forma diferente. El comportamiento de DivMMC en hardware real puede diferir del esxDOS emulado.

---

> **Fuentes:** World of Spectrum (mapa de memoria del ZX Spectrum 128K y documentación del puerto $7FFD); Introspec "Data Compression for Modern Z80 Coding" (Hype 2017); documentación de la API esxDOS (wiki DivIDE/DivMMC); documentación de la extensión DeZog para VS Code (GitHub: maziac/DeZog); documentación de sjasmplus (directivas SAVETAP, DEVICE, SLOT, PAGE); especificación del formato PT3 de Vortex Tracker II; Capítulos 11, 14, 15, 16, 17, 18, 19 de este libro.
