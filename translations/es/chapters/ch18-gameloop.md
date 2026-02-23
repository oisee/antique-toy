# Capítulo 18: Bucle de Juego y Sistema de Entidades

> "Un juego es una demo que escucha."

---

Todo efecto de demo que hemos construido hasta ahora se ejecuta en un bucle cerrado: calcular, renderizar, repetir. El espectador observa. Al código no le importa si hay alguien en la habitación. Un juego rompe este contrato. Un juego *responde*. El jugador presiona una tecla y algo debe cambiar -- inmediatamente, de forma fiable, dentro del mismo presupuesto de fotograma que hemos estado contando desde el Capítulo 1.

Este capítulo trata sobre construir la arquitectura que hace posible un juego en el ZX Spectrum y el Agon Light 2. No el renderizado (el Capítulo 16 cubrió sprites, el Capítulo 17 cubrió el desplazamiento) y no la física (el Capítulo 19 manejará colisiones e IA). Este capítulo es el esqueleto: el bucle principal que impulsa todo, la máquina de estados que organiza el flujo desde la pantalla de título hasta el juego y el fin de partida, el sistema de entrada que lee las intenciones del jugador, y el sistema de entidades que gestiona cada objeto en el mundo del juego.

Al final, tendrás un esqueleto de juego funcional con 16 entidades activas -- un jugador, ocho enemigos y siete balas -- ejecutándose dentro del presupuesto de fotograma en ambas plataformas.

---

## 18.1 El Bucle Principal

Todo juego en el ZX Spectrum sigue el mismo ritmo fundamental:

```
1. HALT          -- esperar la interrupción de fotograma
2. Read input    -- ¿qué quiere el jugador?
3. Update state  -- mover entidades, ejecutar IA, verificar colisiones
4. Render        -- dibujar el fotograma
5. Go to 1
```

Este es el bucle de juego. No es complicado. Su poder viene del hecho de que se ejecuta cincuenta veces por segundo, cada segundo, y todo lo que el jugador experimenta emerge de este ciclo.

Aquí está la implementación mínima:

```z80
    ORG  $8000

    ; Install IM1 interrupt handler (standard for games)
    im   1
    ei

main_loop:
    halt                    ; 4T + wait -- sync to frame interrupt

    call read_input         ; poll keyboard/joystick
    call update_entities    ; move everything, run logic
    call render_frame       ; draw to screen

    jr   main_loop          ; 12T -- loop forever
```

La instrucción `HALT` es el latido del corazón. Cuando la CPU ejecuta `HALT`, se detiene y espera la siguiente interrupción enmascarable. En el Spectrum, la ULA dispara esta interrupción al inicio de cada fotograma -- una vez cada 1/50 de segundo. La CPU despierta, el manejador IM1 en la dirección $0038 se ejecuta (en una ROM estándar esto simplemente incrementa el contador de fotogramas), y luego la ejecución se reanuda en la instrucción después de `HALT`. Tu código del bucle principal se ejecuta, hace su trabajo, y llega a `HALT` otra vez para esperar el siguiente fotograma.

Esto te da exactamente el valor de T-states de un fotograma para hacer todo. Si tu trabajo termina antes, la CPU permanece inactiva dentro de `HALT` hasta la siguiente interrupción -- sin energía desperdiciada, sin desviación, sincronización perfecta. Si tu trabajo tarda demasiado y la interrupción se dispara antes de que llegues a `HALT`, pierdes un fotograma. El bucle sigue funcionando (el siguiente `HALT` capturará la interrupción siguiente), pero el juego baja a 25 fps para ese fotograma. Si lo pierdes consistentemente estás a 25 fps permanentemente. Si lo pierdes gravemente estás a 16.7 fps (cada tercer fotograma). El jugador lo nota.

### El Presupuesto de Fotograma, Revisitado

Establecimos los números en el Capítulo 1, pero vale la pena repetirlos en el contexto de un juego:

| Máquina | T-states por fotograma | Presupuesto práctico |
|---------|-------------------|------------------|
| ZX Spectrum 48K | 69,888 | ~62,000 (tras overhead de interrupción) |
| ZX Spectrum 128K | 70,908 | ~63,000 |
| Pentagon 128 | 71,680 | ~64,000 |
| Agon Light 2 | ~368,640 | ~360,000 |

El "presupuesto práctico" contempla el manejador de interrupciones, la propia instrucción `HALT`, y el overhead de temporización del borde. En el Spectrum, tienes aproximadamente 64,000 T-states de tiempo utilizable por fotograma. En el Agon, tienes más de cinco veces eso.

¿Cómo gasta un juego típico esos 64,000 T-states? Aquí hay un desglose realista para un plataformas de Spectrum:

| Subsistema | T-states | % del presupuesto |
|-----------|----------|-------------|
| Lectura de entrada | ~500 | 0.8% |
| Actualización de entidades (16 entidades) | ~8,000 | 12.5% |
| Detección de colisiones | ~4,000 | 6.3% |
| Reproductor de música (PT3) | ~5,000 | 7.8% |
| Renderizado de sprites (8 visibles) | ~24,000 | 37.5% |
| Actualización de fondo/desplazamiento | ~12,000 | 18.8% |
| Misceláneo (HUD, estado) | ~3,000 | 4.7% |
| **Margen restante** | **~7,500** | **11.7%** |

Ese 11.7% de margen es tu margen de seguridad. Si lo consumes, empiezas a perder fotogramas en escenas complejas. La técnica de perfilado con color de borde del Capítulo 1 -- rojo para sprites, azul para música, verde para lógica -- es cómo monitorizas este presupuesto durante el desarrollo. Úsala constantemente.

En el Agon, la misma lógica de juego se ejecuta en una fracción del presupuesto. La actualización de entidades, la detección de colisiones y la lectura de entrada podrían consumir 15,000 T-states en total -- aproximadamente el 4% del fotograma del Agon. El VDP maneja el renderizado de sprites en el coprocesador ESP32, así que el coste de sprites del lado de la CPU se reduce al overhead de comandos VDU. Tienes un enorme margen para IA más compleja, más entidades, o simplemente menos estrés.

![Game loop architecture](illustrations/output/ch18_game_loop.png)

---

## 18.2 La Máquina de Estados del Juego

Un juego no es un solo bucle -- son varios. La pantalla de título tiene su propio bucle (animar logo, esperar pulsación de tecla). El menú tiene su propio bucle (resaltar opciones, leer entrada). El bucle de juego es lo que describimos arriba. La pantalla de pausa congela el bucle de juego y ejecuta uno más simple. La pantalla de fin de partida tiene otro más.

La forma más limpia de organizar estos es una **máquina de estados**: una variable que rastrea en qué estado está el juego, y una tabla de direcciones de manejadores -- una por estado.

### Definiciones de Estado

```z80
; Game states (byte values, used as table offsets)
STATE_TITLE     EQU  0
STATE_MENU      EQU  2      ; x2 because each table entry is 2 bytes
STATE_GAME      EQU  4
STATE_PAUSE     EQU  6
STATE_GAMEOVER  EQU  8

; Current state variable
game_state:     DB   STATE_TITLE
```

### La Tabla de Saltos

```z80
; Table of handler addresses, indexed by state
state_table:
    DW   state_title        ; STATE_TITLE   = 0
    DW   state_menu         ; STATE_MENU    = 2
    DW   state_game         ; STATE_GAME    = 4
    DW   state_pause        ; STATE_PAUSE   = 6
    DW   state_gameover     ; STATE_GAMEOVER = 8
```

### El Despachador

El bucle principal se convierte en un despachador que lee el estado actual y salta al manejador apropiado:

```z80
main_loop:
    halt                    ; sync to frame

    ; Dispatch to current state handler
    ld   a, (game_state)    ; 13T  load state index
    ld   l, a               ; 4T
    ld   h, 0               ; 7T
    ld   de, state_table    ; 10T
    add  hl, de             ; 11T  HL = state_table + offset
    ld   e, (hl)            ; 7T   low byte of handler address
    inc  hl                 ; 6T
    ld   d, (hl)            ; 7T   high byte of handler address
    ex   de, hl             ; 4T   HL = handler address
    jp   (hl)               ; 4T   jump to handler
                            ; --- 73T total dispatch overhead
```

La instrucción `JP (HL)` es la clave. No salta a la dirección almacenada *en* HL -- salta a la dirección *dentro de* HL. Este es el salto indirecto del Z80, y cuesta solo 4 T-states. Todo el despacho -- cargar la variable de estado, calcular el desplazamiento de tabla, leer la dirección del manejador, y saltar -- toma 73 T-states. Eso es despreciable: aproximadamente el 0.1% del presupuesto de fotograma.

Cada manejador ejecuta su propia lógica y luego salta de vuelta a `main_loop`:

```z80
state_title:
    call draw_title_screen
    call read_input
    ; Check for start key (SPACE or ENTER)
    ld   a, (input_flags)
    bit  BUTTON_FIRE, a
    jr   z, .no_start
    ; Transition to menu
    ld   a, STATE_MENU
    ld   (game_state), a
    call init_menu          ; set up menu screen
.no_start:
    jp   main_loop

state_game:
    call read_input
    ; Check for pause
    ld   a, (input_keys)
    bit  KEY_P, a
    jr   z, .not_paused
    ld   a, STATE_PAUSE
    ld   (game_state), a
    jp   main_loop
.not_paused:
    call update_entities
    call check_collisions
    call render_frame
    call update_music       ; AY player -- see Chapter 11
    jp   main_loop

state_pause:
    ; Game is frozen -- only check for unpause
    call read_input
    ld   a, (input_keys)
    bit  KEY_P, a
    jr   z, .still_paused
    ld   a, STATE_GAME
    ld   (game_state), a
.still_paused:
    ; Optionally blink "PAUSED" text
    call blink_pause_text
    jp   main_loop

state_gameover:
    call draw_gameover_screen
    call read_input
    ld   a, (input_flags)
    bit  BUTTON_FIRE, a
    jr   z, .wait
    ld   a, STATE_TITLE
    ld   (game_state), a
    call init_title
.wait:
    jp   main_loop
```

### ¿Por Qué No una Cadena de Comparaciones?

Podrías estar tentado a escribir el despachador como:

```z80
    ld   a, (game_state)
    cp   STATE_TITLE
    jp   z, state_title
    cp   STATE_MENU
    jp   z, state_menu
    cp   STATE_GAME
    jp   z, state_game
    ; ...
```

Esto funciona, pero tiene dos problemas. Primero, el coste crece linealmente: cada estado adicional añade un `CP` (7T) y un `JP Z` (10T), así que el peor caso es 17T por estado. Con 5 estados, el estado de juego (el caso más común) podría tardar 51T en alcanzarse si es la tercera comparación. La tabla de saltos toma 73T independientemente de qué estado esté activo -- es O(1), no O(n).

Segundo, y más importante, la tabla de saltos escala limpiamente. Añadir un sexto estado (digamos, STATE_SHOP) significa añadir una entrada `DW` a la tabla y una definición de constante. El código del despachador no cambia en absoluto. Con cadenas de comparación, añades más instrucciones al propio despachador, y el orden empieza a importar para el rendimiento. El enfoque de tabla es tanto más rápido en el caso común como más limpio de mantener.

### Transiciones de Estado

Las transiciones de estado ocurren escribiendo un nuevo valor en `game_state`. Típicamente también llamas a una rutina de inicialización para el nuevo estado:

```z80
; Transition: Game -> Game Over
game_over_transition:
    ld   a, STATE_GAMEOVER
    ld   (game_state), a
    call init_gameover       ; set up game over screen, save score
    ret
```

Mantén las transiciones explícitas y centralizadas. Un error común en juegos Z80 es una transición de estado que olvida inicializar los datos del nuevo estado -- la pantalla de fin de partida muestra basura porque nadie limpió la pantalla ni reinició el contador de animación. Cada estado debería tener una rutina `init_` que la transición invoca.

---

## 18.3 Entrada: Leyendo al Jugador

### Teclado del ZX Spectrum

El teclado del Spectrum se lee a través del puerto `$FE`. El teclado está cableado como una matriz de 8 semi-filas, cada una seleccionada poniendo un bit bajo en el byte alto de la dirección del puerto. Leer el puerto `$FE` con un byte alto específico devuelve el estado de esa semi-fila: 5 bits, uno por tecla, donde 0 significa presionada y 1 significa no presionada.

El mapa de semi-filas:

| Byte alto | Teclas (bit 0 a bit 4) |
|-----------|----------------------|
| $FE (bit 0 bajo) | SHIFT, Z, X, C, V |
| $FD (bit 1 bajo) | A, S, D, F, G |
| $FB (bit 2 bajo) | Q, W, E, R, T |
| $F7 (bit 3 bajo) | 1, 2, 3, 4, 5 |
| $EF (bit 4 bajo) | 0, 9, 8, 7, 6 |
| $DF (bit 5 bajo) | P, O, I, U, Y |
| $BF (bit 6 bajo) | ENTER, L, K, J, H |
| $7F (bit 7 bajo) | SPACE, SYMSHIFT, M, N, B |

Los controles estándar de juego -- Q/A/O/P para arriba/abajo/izquierda/derecha y SPACE para disparar -- abarcan tres semi-filas. Aquí hay una rutina que los lee y empaqueta el resultado en un solo byte:

```z80
; Input flag bits
INPUT_RIGHT  EQU  0
INPUT_LEFT   EQU  1
INPUT_DOWN   EQU  2
INPUT_UP     EQU  3
INPUT_FIRE   EQU  4

; Read QAOP+SPACE into input_flags
; Returns: A = input_flags byte, also stored at (input_flags)
read_keyboard:
    ld   d, 0               ; 7T   accumulate result in D

    ; Read O and P: half-row $DF (P=bit0, O=bit1)
    ld   bc, $DFFE          ; 10T
    in   a, (c)             ; 12T
    bit  0, a               ; 8T   P key
    jr   nz, .no_right      ; 12/7T
    set  INPUT_RIGHT, d     ; 8T
.no_right:
    bit  1, a               ; 8T   O key
    jr   nz, .no_left       ; 12/7T
    set  INPUT_LEFT, d      ; 8T
.no_left:

    ; Read Q and A: half-rows $FB (Q=bit0) and $FD (A=bit0... wait)
    ; Q is in half-row $FB at bit 0
    ld   b, $FB             ; 7T
    in   a, (c)             ; 12T
    bit  0, a               ; 8T   Q key
    jr   nz, .no_up         ; 12/7T
    set  INPUT_UP, d        ; 8T
.no_up:

    ; A is in half-row $FD at bit 0
    ld   b, $FD             ; 7T
    in   a, (c)             ; 12T
    bit  0, a               ; 8T   A key
    jr   nz, .no_down       ; 12/7T
    set  INPUT_DOWN, d      ; 8T
.no_down:

    ; SPACE: half-row $7F at bit 0
    ld   b, $7F             ; 7T
    in   a, (c)             ; 12T
    bit  0, a               ; 8T
    jr   nz, .no_fire       ; 12/7T
    set  INPUT_FIRE, d      ; 8T
.no_fire:

    ld   a, d               ; 4T
    ld   (input_flags), a   ; 13T
    ret                     ; 10T
    ; Total: ~220T worst case (all keys pressed)
```

Con aproximadamente 220 T-states en el peor caso, la lectura de entrada es trivial en el presupuesto de fotograma. Incluso en el Spectrum podrías permitirte leer el teclado diez veces por fotograma y apenas notarlo.

### Joystick Kempston

La interfaz Kempston es aún más simple. Una lectura de puerto devuelve las cinco direcciones más disparo:

```z80
; Kempston joystick port
KEMPSTON_PORT  EQU  $1F

; Read Kempston joystick
; Returns: A = joystick state
;   bit 0 = right, bit 1 = left, bit 2 = down, bit 3 = up, bit 4 = fire
read_kempston:
    in   a, (KEMPSTON_PORT)  ; 11T
    and  %00011111           ; 7T   mask to 5 bits
    ld   (input_flags), a    ; 13T
    ret                      ; 10T
    ; Total: 41T
```

Observa algo conveniente: la disposición de bits Kempston coincide exactamente con nuestras definiciones de banderas `INPUT_*`. Esto no es coincidencia -- la interfaz Kempston fue diseñada con este estándar en mente, y la mayoría de los juegos de Spectrum adoptan el mismo orden de bits. Si soportas tanto teclado como joystick, puedes combinar los resultados con OR:

```z80
read_input:
    call read_keyboard       ; D = keyboard flags
    push de
    call read_kempston       ; A = joystick flags
    pop  de
    or   d                   ; combine both sources
    ld   (input_flags), a
    ret
```

Ahora el resto de tu código solo verifica `input_flags` y no le importa si la entrada vino del teclado o de un joystick.

### Detección de Flancos: Pulsación vs Mantenimiento

Para algunas acciones -- disparar una bala, abrir un menú -- quieres responder al evento de *pulsación*, no al estado mantenido. Si verificas `bit INPUT_FIRE, a` cada fotograma, el jugador dispara una bala cada 1/50 de segundo mientras mantiene el botón. Eso podría ser intencional para disparo rápido, pero para un arma de disparo único o una selección de menú, necesitas detección de flancos.

La técnica: almacenar la entrada del fotograma anterior junto con la del fotograma actual, y hacer XOR entre ellas para encontrar los bits que cambiaron:

```z80
input_flags:      DB  0    ; current frame
input_prev:       DB  0    ; previous frame
input_pressed:    DB  0    ; newly pressed this frame (edges)

read_input_with_edges:
    ; Save previous state
    ld   a, (input_flags)
    ld   (input_prev), a

    ; Read current state
    call read_input          ; updates input_flags

    ; Compute edges: pressed = current AND NOT previous
    ld   a, (input_prev)
    cpl                      ; 4T   invert previous
    ld   b, a                ; 4T
    ld   a, (input_flags)    ; 13T
    and  b                   ; 4T   current AND NOT previous
    ld   (input_pressed), a  ; 13T  = newly pressed this frame
    ret
```

Ahora `input_pressed` tiene un bit 1 solo para botones que *no* estaban presionados el fotograma anterior pero *sí* están presionados este fotograma. Usa `input_flags` para acciones continuas (movimiento) e `input_pressed` para acciones de un solo disparo (disparar, saltar, seleccionar en menú).

### Agon Light 2: Teclado PS/2 via MOS

El Agon lee su teclado PS/2 a través de la API MOS (Machine Operating System). El eZ80 no escanea directamente una matriz de teclado -- en su lugar, el coprocesador VDP ESP32 maneja el hardware del teclado y pasa eventos de pulsación al eZ80 a través de un búfer compartido.

La variable de sistema MOS `sysvar_keyascii` (en la dirección $0800 + desplazamiento) contiene el código ASCII de la tecla más recientemente presionada, o 0 si ninguna tecla está pulsada. Para controles de juego, típicamente consultas esta variable o usas las llamadas de API MOS `waitvblank` / teclado:

```z80
; Agon: Read keyboard via MOS sysvar
; MOS sysvar_keyascii at IX+$05
read_input_agon:
    ld   a, (ix + $05)      ; read last key from MOS sysvars
    ; Map ASCII to input_flags
    cp   'o'
    jr   nz, .not_left
    set  INPUT_LEFT, d
.not_left:
    cp   'p'
    jr   nz, .not_right
    set  INPUT_RIGHT, d
.not_right:
    ; ... etc for Q, A, SPACE
    ld   a, d
    ld   (input_flags), a
    ret
```

El Agon también soporta la lectura de estados individuales de tecla via comandos VDU (VDU 23,0,$01,keycode), que devuelven si una tecla específica está actualmente mantenida. Esto es más cercano al enfoque de semi-filas del Spectrum y mejor adaptado para juegos que necesitan detección simultánea de teclas. La API MOS maneja el protocolo PS/2, la traducción de códigos de escaneo y la auto-repetición -- nada de lo cual necesitas preocuparte.

---

## 18.4 La Estructura de Entidad

Una entidad de juego es cualquier cosa que se mueve, anima, interactúa o necesita actualización por fotograma: el personaje del jugador, enemigos, balas, explosiones, números de puntuación flotantes, potenciadores. En el Z80, representamos cada entidad como un bloque de bytes de tamaño fijo en memoria.

### Disposición de la Estructura

Aquí está la estructura de entidad que usaremos a lo largo de los capítulos de desarrollo de juegos:

```
Offset  Size  Name        Description
------  ----  ----------  -------------------------------------------
 +0     2     x           X position, 8.8 fixed-point (high=pixel, low=subpixel)
 +2     1     y           Y position, pixel (0-191)
 +3     1     type        Entity type (0=inactive, 1=player, 2=enemy, 3=bullet, ...)
 +4     1     state       Entity state (0=idle, 1=active, 2=dying, 3=dead, ...)
 +5     1     anim_frame  Current animation frame index
 +6     1     dx          Horizontal velocity (signed, fixed-point fractional)
 +7     1     dy          Vertical velocity (signed, fixed-point fractional)
 +8     1     health      Hit points remaining
 +9     1     flags       Bit flags (see below)
------  ----
 10 bytes total per entity
```

Bits de bandera en el byte `flags`:

```
Bit 0: ACTIVE      -- entity is alive and should be updated/rendered
Bit 1: VISIBLE     -- entity should be rendered (active but invisible = logic only)
Bit 2: COLLIDABLE  -- entity participates in collision detection
Bit 3: FACING_LEFT -- horizontal facing direction
Bit 4: INVINCIBLE  -- temporary invulnerability (player after being hit)
Bit 5: ON_GROUND   -- entity is standing on solid ground (set by physics)
Bit 6-7: reserved
```

### ¿Por Qué 10 Bytes?

Diez bytes es una elección deliberada. Es lo suficientemente pequeño para que 16 entidades ocupen solo 160 bytes -- trivial en términos de memoria. Más importante aún, multiplicar un índice de entidad por 10 para encontrar su desplazamiento es sencillo en el Z80:

```z80
; Calculate entity address from index in A
; Input: A = entity index (0-15)
; Output: HL = address of entity structure
; Destroys: DE
get_entity_addr:
    ld   l, a               ; 4T
    ld   h, 0               ; 7T
    add  hl, hl             ; 11T  x2
    ld   d, h               ; 4T
    ld   e, l               ; 4T   DE = index x 2
    add  hl, hl             ; 11T  x4
    add  hl, hl             ; 11T  x8
    add  hl, de             ; 11T  x8 + x2 = x10
    ld   de, entity_array   ; 10T
    add  hl, de             ; 11T  HL = entity_array + index * 10
    ret                     ; 10T
    ; Total: 94T
```

La multiplicación por 10 usa la descomposición estándar: 10 = 8 + 2. Calculamos índice * 2, lo guardamos, calculamos índice * 8, y los sumamos. No se necesita instrucción de multiplicación real -- solo desplazamientos (ADD HL,HL) y una suma.

Si eligieras un tamaño potencia de dos como 8 o 16 bytes por entidad, el cálculo de índice sería aún más simple (tres desplazamientos para 8, cuatro para 16). Pero 8 bytes es demasiado estrecho -- perderías velocidad o salud, y ambas importan. Y 16 bytes desperdicia 6 bytes por entidad en relleno, que se acumula: 16 entidades x 6 bytes desperdiciados = 96 bytes de espacio muerto. En el Spectrum, cada byte importa. Diez bytes es el ajuste correcto para los datos que realmente necesitamos.

### ¿Por Qué X de 16 Bits pero Y de 8 Bits?

La posición X es punto fijo de 16 bits (formato 8.8): el byte alto es la columna de píxeles (0-255) y el byte bajo es una fracción sub-píxel para movimiento suave. Esto es esencial para juegos con desplazamiento horizontal donde el jugador se mueve a velocidades fraccionarias de píxel. Un personaje moviéndose a 1.5 píxeles por fotograma con solo coordenadas enteras alternaría entre pasos de 1 píxel y 2 píxeles, produciendo un temblor visible. Con punto fijo 8.8, el movimiento es suave: añade 0x0180 a X cada fotograma y la posición en píxeles avanza 1, 2, 1, 2, 1, 2... en un patrón que el ojo percibe como un constante 1.5 píxeles por fotograma.

La posición Y es solo de 8 bits porque la pantalla del Spectrum tiene 192 píxeles de alto -- un solo byte cubre el rango completo. Para un juego con desplazamiento vertical, promoverías Y a punto fijo de 16 bits también, al coste de un byte extra por entidad.

### El Sistema de Punto Fijo 8.8

La aritmética de punto fijo se introdujo en el Capítulo 4. Aquí hay un repaso rápido de cómo se aplica al movimiento de entidades:

```z80
; Move entity right at velocity dx
; HL points to entity X (2 bytes: low=fractional, high=pixel)
; A = dx (signed velocity, treated as fractional byte)
move_entity_x:
    ld   c, (hl)            ; 7T   load X fractional part
    inc  hl                  ; 6T
    ld   b, (hl)            ; 7T   load X pixel part
    ; BC = 16-bit fixed-point X

    ld   e, a               ; 4T   dx into E
    ; Sign-extend dx into DE
    rla                      ; 4T   carry = sign bit
    sbc  a, a               ; 4T   A = $FF if negative, $00 if positive
    ld   d, a               ; 4T   DE = signed 16-bit dx

    ex   de, hl             ; 4T
    add  hl, de             ; 11T  new_X = old_X + dx (16-bit add)
    ; HL = new X position (fractional in L, pixel in H)

    ; Store back
    ld   a, l               ; 4T
    ld   (entity_x_lo), a   ; 13T  (self-modifying, or use IX)
    ld   a, h               ; 4T
    ld   (entity_x_hi), a   ; 13T
    ret
```

La belleza del punto fijo: la suma y la resta son simplemente operaciones regulares `ADD HL,DE` de 16 bits. Sin manejo especial, sin tablas de consulta, sin multiplicación. La precisión fraccional ocurre automáticamente porque llevamos los bits sub-píxel consigo.

---

## 18.5 El Array de Entidades

Las entidades viven en un array asignado estáticamente. Sin asignación dinámica de memoria, sin listas enlazadas, sin heap. Los arrays estáticos son el enfoque estándar en el Z80 por una buena razón: son rápidos, predecibles, y no pueden fragmentarse.

```z80
; Entity array: 16 entities, 10 bytes each = 160 bytes
MAX_ENTITIES    EQU  16
ENTITY_SIZE     EQU  10

entity_array:
    DS   MAX_ENTITIES * ENTITY_SIZE    ; 160 bytes, zeroed at init
```

### Asignación de Ranuras de Entidad

La ranura 0 es siempre el jugador. Las ranuras 1-8 son enemigos. Las ranuras 9-15 son proyectiles y efectos (balas, explosiones, popups de puntuación). Esta partición fija simplifica el código: cuando necesitas iterar sobre enemigos para la IA, iteras las ranuras 1-8. Cuando una bala necesita generarse, buscas en las ranuras 9-15. El jugador está siempre en una dirección conocida.

```z80
; Fixed slot assignments
SLOT_PLAYER      EQU  0
SLOT_ENEMY_FIRST EQU  1
SLOT_ENEMY_LAST  EQU  8
SLOT_PROJ_FIRST  EQU  9
SLOT_PROJ_LAST   EQU  15
```

### Iterando Entidades

El bucle de actualización central recorre cada ranura de entidad, verifica la bandera ACTIVE, y llama al manejador de actualización apropiado:

```z80
; Update all active entities
; Total cost: ~2,500T for 16 entities (most inactive), up to ~8,000T (all active)
update_entities:
    ld   ix, entity_array   ; 14T  IX points to first entity
    ld   b, MAX_ENTITIES    ; 7T   loop counter

.loop:
    ; Check if entity is active
    ld   a, (ix + 9)        ; 19T  load flags byte (offset +9)
    bit  0, a               ; 8T   test ACTIVE flag
    jr   z, .skip           ; 12/7T skip if inactive

    ; Entity is active -- dispatch by type
    ld   a, (ix + 3)        ; 19T  load type byte (offset +3)
    ; Jump table dispatch based on type
    call update_by_type     ; ~200-500T depending on type

.skip:
    ; Advance IX to next entity
    ld   de, ENTITY_SIZE    ; 10T
    add  ix, de             ; 15T  IX += 10
    djnz .loop              ; 13/8T
    ret
```

Esto usa IX como puntero de entidad, lo cual es conveniente porque el direccionamiento indexado por IX te permite acceder a cualquier campo por su desplazamiento: `(IX+0)` es X bajo, `(IX+2)` es Y, `(IX+3)` es tipo, y así sucesivamente. La desventaja de IX es el coste: cada `LD A,(IX+n)` toma 19 T-states versus 7 para `LD A,(HL)`. Para el bucle de actualización de entidades, que se ejecuta 16 veces por fotograma, este overhead es aceptable. Para el bucle interno de renderizado donde tocas datos de entidad miles de veces por fotograma, copiarías primero los campos relevantes a registros.

### Despacho de Actualización por Tipo

Cada tipo de entidad tiene su propio manejador de actualización. Usamos la misma técnica de tabla de saltos que la máquina de estados del juego:

```z80
; Entity type constants
TYPE_INACTIVE  EQU  0
TYPE_PLAYER    EQU  1
TYPE_ENEMY     EQU  2
TYPE_BULLET    EQU  3
TYPE_EXPLOSION EQU  4

; Handler table (2 bytes per entry)
type_handlers:
    DW   update_inactive     ; type 0: no-op, should not be called
    DW   update_player       ; type 1
    DW   update_enemy        ; type 2
    DW   update_bullet       ; type 3
    DW   update_explosion    ; type 4

; Dispatch to type handler
; Input: A = entity type, IX = entity pointer
update_by_type:
    add  a, a               ; 4T   type * 2 (table entries are 2 bytes)
    ld   l, a               ; 4T
    ld   h, 0               ; 7T
    ld   de, type_handlers   ; 10T
    add  hl, de             ; 11T
    ld   e, (hl)            ; 7T
    inc  hl                 ; 6T
    ld   d, (hl)            ; 7T
    ex   de, hl             ; 4T
    jp   (hl)               ; 4T   jump to handler (RET will return to caller)
                            ; --- 64T dispatch overhead
```

Cada manejador recibe IX apuntando a la entidad y puede acceder a todos los campos via direccionamiento indexado. Cuando el manejador ejecuta `RET`, retorna al bucle de actualización de entidades, que avanza a la siguiente ranura.

### El Manejador de Actualización del Jugador

Aquí hay una actualización típica del jugador -- leer banderas de entrada, aplicar movimiento, actualizar animación:

```z80
; Update player entity
; IX = entity pointer (slot 0)
update_player:
    ; Read horizontal input
    ld   a, (input_flags)    ; 13T
    bit  INPUT_RIGHT, a      ; 8T
    jr   z, .not_right       ; 12/7T
    ; Move right: add dx to X
    ld   a, 2               ; 7T   dx = 2 subpixels per frame (~1 pixel/frame)
    add  a, (ix + 0)        ; 19T  add to X fractional
    ld   (ix + 0), a        ; 19T
    jr   nc, .no_carry_r    ; 12/7T
    inc  (ix + 1)           ; 23T  carry into X pixel
.no_carry_r:
    res  3, (ix + 9)        ; 23T  clear FACING_LEFT flag
    jr   .horiz_done        ; 12T
.not_right:
    bit  INPUT_LEFT, a       ; 8T
    jr   z, .horiz_done      ; 12/7T
    ; Move left: subtract dx from X
    ld   a, (ix + 0)        ; 19T  load X fractional
    sub  2                   ; 7T   subtract dx
    ld   (ix + 0), a        ; 19T
    jr   nc, .no_borrow_l   ; 12/7T
    dec  (ix + 1)           ; 23T  borrow from X pixel
.no_borrow_l:
    set  3, (ix + 9)        ; 23T  set FACING_LEFT flag
.horiz_done:

    ; Update animation frame (cycle every 8 frames)
    ld   a, (ix + 5)        ; 19T  anim_frame
    inc  a                   ; 4T
    and  7                   ; 7T   wrap 0-7
    ld   (ix + 5), a        ; 19T
    ret
    ; Total: ~250-350T depending on input
```

Esto es deliberadamente simple. El Capítulo 19 añadirá gravedad, saltos y respuesta a colisiones. Por ahora, el punto es la *estructura*: puntero de entidad en IX, campos accedidos por desplazamiento, banderas de entrada impulsando cambios de estado, contador de animación avanzando.

---

## 18.6 El Pool de Objetos

Las balas, explosiones y efectos de partículas son transitorios. Una bala existe por una fracción de segundo antes de que golpee algo o salga de la pantalla. Una explosión se anima durante 8-16 fotogramas y desaparece. Podrías generarlos dinámicamente, pero en el Z80, "dinámico" significa buscar memoria libre, gestionar asignación, y arriesgar fragmentación. En su lugar, usamos un **pool de objetos**: un conjunto fijo de ranuras en las que las entidades se activan y desactivan.

Ya tenemos el pool -- es el array de entidades. Las ranuras 9-15 son el pool de proyectiles/efectos. Generar una bala significa encontrar una ranura inactiva en ese rango y rellenarla. Destruir una bala significa limpiar su bandera ACTIVE.

### Generando una Bala

```z80
; Spawn a bullet at position (B=x_pixel, C=y)
; moving in direction determined by player facing
; Returns: carry set if no free slot available
spawn_bullet:
    ld   ix, entity_array + (SLOT_PROJ_FIRST * ENTITY_SIZE)
    ld   d, SLOT_PROJ_LAST - SLOT_PROJ_FIRST + 1  ; 7 slots to check

.find_slot:
    ld   a, (ix + 9)        ; 19T  flags
    bit  0, a               ; 8T   ACTIVE?
    jr   z, .found          ; 12/7T found an inactive slot

    ld   e, ENTITY_SIZE     ; 7T
    add  ix, de             ; 15T  next slot (note: DE high byte may be nonzero,
                            ;      but we only care about the low 8 bits of offset)
    dec  d                  ; 4T
    jr   nz, .find_slot     ; 12T

    ; No free slot -- set carry and return
    scf                      ; 4T
    ret

.found:
    ; Fill in the bullet entity
    ld   (ix + 0), 0        ; fractional X = 0
    ld   (ix + 1), b        ; pixel X = B
    ld   (ix + 2), c        ; Y = C
    ld   (ix + 3), TYPE_BULLET ; type
    ld   (ix + 4), 1        ; state = active
    ld   (ix + 5), 0        ; anim_frame = 0
    ld   (ix + 8), 1        ; health = 1 (dies on first collision)

    ; Set velocity based on player facing
    ld   a, (entity_array + 9)  ; player flags
    bit  3, a               ; FACING_LEFT?
    jr   z, .fire_right
    ld   (ix + 6), -4       ; dx = -4 (fast, leftward)
    jr   .set_flags
.fire_right:
    ld   (ix + 6), 4        ; dx = +4 (fast, rightward)
.set_flags:
    ld   (ix + 7), 0        ; dy = 0 (horizontal bullet)
    ld   (ix + 9), %00000111  ; flags: ACTIVE + VISIBLE + COLLIDABLE
    or   a                   ; clear carry (success)
    ret
```

### Desactivando una Entidad

Cuando una bala sale de la pantalla o una explosión termina su animación, la desactivación es una sola instrucción:

```z80
; Deactivate entity at IX
deactivate_entity:
    ld   (ix + 9), 0        ; 19T  clear all flags (ACTIVE=0)
    ret
```

Eso es todo. El siguiente fotograma, el bucle de actualización ve ACTIVE=0 y salta la ranura. La ranura ahora está disponible para la siguiente llamada a `spawn_bullet` para reutilizar.

### Manejador de Actualización de Bala

```z80
; Update a bullet entity
; IX = entity pointer
update_bullet:
    ; Move horizontally
    ld   a, (ix + 6)        ; 19T  dx
    ld   e, a               ; 4T
    ; Sign-extend
    rla                      ; 4T
    sbc  a, a               ; 4T
    ld   d, a               ; 4T   DE = signed 16-bit dx

    ld   l, (ix + 0)        ; 19T  X lo
    ld   h, (ix + 1)        ; 19T  X hi
    add  hl, de             ; 11T  new X
    ld   (ix + 0), l        ; 19T
    ld   (ix + 1), h        ; 19T

    ; Check screen bounds (0-255 pixel range)
    ld   a, h               ; 4T   pixel X
    or   a                   ; 4T
    jr   z, .off_screen     ; boundary check: if X=0, leftward bullet exited
    cp   248                ; 7T   near right edge?
    jr   nc, .off_screen    ; past right boundary

    ; Still alive -- return
    ret

.off_screen:
    ; Deactivate
    ld   (ix + 9), 0        ; clear flags
    ret
    ; Total: ~170T active, ~190T when deactivating
```

### Dimensionamiento del Pool

Siete ranuras de proyectiles (índices 9-15) podrían sonar limitadas. En la práctica, es más que suficiente para la mayoría de juegos de Spectrum. Considera: una bala que cruza el ancho completo de la pantalla (256 píxeles) a 4 píxeles por fotograma tarda 64 fotogramas -- más de un segundo. Si el jugador dispara una vez cada 8 fotogramas (una tasa de fuego rápida), como máximo 8 balas pueden existir simultáneamente. Siete ranuras con fallos de generación ocasionales (la bala simplemente no se dispara ese fotograma) se siente natural, no defectuoso. Es poco probable que el jugador note una bala perdida al límite de su tasa de fuego.

Si necesitas más, expande el array de entidades. Pero sé consciente del coste: cada entidad adicional añade ~160 T-states al bucle de actualización en el peor caso (cuando está activa) y ~50 T-states incluso cuando está inactiva (la verificación de la bandera ACTIVE y el avance de IX aún se ejecutan). Treinta y dos entidades todas activas consumirían aproximadamente 16,000 T-states solo en el bucle de actualización -- un cuarto del presupuesto de fotograma antes de haber renderizado un solo píxel.

En el Agon, puedes permitirte pools más grandes. Con 360,000 T-states por fotograma y renderizado de sprites por hardware, 64 o incluso 128 entidades son factibles.

---

## 18.7 Entidades de Explosión y Efecto

Las explosiones, popups de puntuación y efectos de partículas usan las mismas ranuras de entidad que las balas. La diferencia está en sus manejadores de actualización: animan a través de una secuencia de fotogramas y luego se autodestruyen.

```z80
; Update an explosion entity
; IX = entity pointer
update_explosion:
    ; Advance animation frame
    ld   a, (ix + 5)        ; 19T  anim_frame
    inc  a                   ; 4T
    cp   8                   ; 7T   8 frames of animation
    jr   nc, .done          ; 12/7T animation complete

    ld   (ix + 5), a        ; 19T  store new frame
    ret

.done:
    ; Animation complete -- deactivate
    ld   (ix + 9), 0        ; 19T  clear flags
    ret
```

Para generar una explosión cuando un enemigo muere:

```z80
; Spawn explosion at the enemy's position
; IX currently points to the dying enemy
spawn_explosion_at_entity:
    ld   b, (ix + 1)        ; enemy's X pixel
    ld   c, (ix + 2)        ; enemy's Y

    ; Find a free projectile/effect slot
    push ix
    ld   ix, entity_array + (SLOT_PROJ_FIRST * ENTITY_SIZE)
    ld   d, SLOT_PROJ_LAST - SLOT_PROJ_FIRST + 1

.find:
    ld   a, (ix + 9)
    bit  0, a
    jr   z, .got_slot
    ld   e, ENTITY_SIZE
    add  ix, de
    dec  d
    jr   nz, .find
    pop  ix
    ret                      ; no free slot -- skip explosion

.got_slot:
    ld   (ix + 0), 0        ; X fractional
    ld   (ix + 1), b        ; X pixel
    ld   (ix + 2), c        ; Y
    ld   (ix + 3), TYPE_EXPLOSION
    ld   (ix + 4), 1        ; state = active
    ld   (ix + 5), 0        ; anim_frame = 0
    ld   (ix + 6), 0        ; dx = 0 (stationary)
    ld   (ix + 7), 0        ; dy = 0
    ld   (ix + 8), 0        ; health = 0 (not collidable in a meaningful way)
    ld   (ix + 9), %00000011 ; ACTIVE + VISIBLE, not COLLIDABLE
    pop  ix
    ret
```

El patrón es siempre el mismo: encontrar una ranura libre, rellenar la estructura, establecer las banderas. El manejador de actualización hace trabajo específico del tipo. La desactivación limpia las banderas. La ranura se reutiliza la próxima vez que algo necesite generarse. Este es todo el ciclo de vida de objetos dinámicos en el Z80 -- sin asignador, sin recolector de basura, sin lista libre. Solo un array y una bandera.

---

## 18.8 Uniendo Todo: El Esqueleto del Juego

Aquí está el esqueleto de juego completo que une todo. Este es un framework compilable con todas las piezas conectadas: máquina de estados, entrada, sistema de entidades, y el bucle principal.

```z80
    ORG  $8000

; ============================================================
; Constants
; ============================================================
MAX_ENTITIES    EQU  16
ENTITY_SIZE     EQU  10

STATE_TITLE     EQU  0
STATE_MENU      EQU  2
STATE_GAME      EQU  4
STATE_PAUSE     EQU  6
STATE_GAMEOVER  EQU  8

TYPE_INACTIVE   EQU  0
TYPE_PLAYER     EQU  1
TYPE_ENEMY      EQU  2
TYPE_BULLET     EQU  3
TYPE_EXPLOSION  EQU  4

INPUT_RIGHT     EQU  0
INPUT_LEFT      EQU  1
INPUT_DOWN      EQU  2
INPUT_UP        EQU  3
INPUT_FIRE      EQU  4

FLAG_ACTIVE     EQU  0
FLAG_VISIBLE    EQU  1
FLAG_COLLIDABLE EQU  2
FLAG_FACING_L   EQU  3

; ============================================================
; Entry point
; ============================================================
entry:
    di
    ld   sp, $FFFF          ; set stack
    im   1
    ei

    ; Clear entity array
    ld   hl, entity_array
    ld   de, entity_array + 1
    ld   bc, MAX_ENTITIES * ENTITY_SIZE - 1
    ld   (hl), 0
    ldir

    ; Start in title state
    ld   a, STATE_TITLE
    ld   (game_state), a

; ============================================================
; Main loop with state dispatch
; ============================================================
main_loop:
    halt                     ; sync to frame interrupt

    ; --- Border profiling: red = active processing ---
    ld   a, 2
    out  ($FE), a

    ; Dispatch to current state
    ld   a, (game_state)
    ld   l, a
    ld   h, 0
    ld   de, state_table
    add  hl, de
    ld   e, (hl)
    inc  hl
    ld   d, (hl)
    ex   de, hl
    jp   (hl)

; Called by each state handler when done
return_to_loop:
    ; --- Border black: idle ---
    xor  a
    out  ($FE), a
    jr   main_loop

; ============================================================
; State table
; ============================================================
state_table:
    DW   state_title
    DW   state_menu
    DW   state_game
    DW   state_pause
    DW   state_gameover

; ============================================================
; State: Title screen
; ============================================================
state_title:
    call read_input_with_edges
    ld   a, (input_pressed)
    bit  INPUT_FIRE, a
    jr   z, .wait
    ; Transition to game
    ld   a, STATE_GAME
    ld   (game_state), a
    call init_game
.wait:
    jp   return_to_loop

; ============================================================
; State: Game
; ============================================================
state_game:
    call read_input_with_edges

    ; Check pause
    ; (using 'P' key -- half-row $DF, bit 0 is P, but for simplicity
    ;  we check input_pressed bit 4 / FIRE as a toggle here)

    ; Update all entities
    call update_entities

    ; Render all visible entities
    call render_entities

    ; Update music
    ; call music_play         ; PT3 player -- see Chapter 11

    jp   return_to_loop

; ============================================================
; State: Pause (minimal)
; ============================================================
state_pause:
    call read_input_with_edges
    ld   a, (input_pressed)
    bit  INPUT_FIRE, a
    jr   z, .still_paused
    ld   a, STATE_GAME
    ld   (game_state), a
.still_paused:
    jp   return_to_loop

; ============================================================
; State: Game Over (minimal)
; ============================================================
state_gameover:
    call read_input_with_edges
    ld   a, (input_pressed)
    bit  INPUT_FIRE, a
    jr   z, .wait
    ld   a, STATE_TITLE
    ld   (game_state), a
.wait:
    jp   return_to_loop

; ============================================================
; State: Menu (minimal — expand for your game)
; ============================================================
state_menu:
    ; A full menu would display options and handle UP/DOWN/FIRE.
    ; For this skeleton, the menu simply transitions to the title.
    ; See Exercise 2 below for adding a real menu with item selection.
    jp   state_title

; ============================================================
; Init game: set up player and enemies
; ============================================================
init_game:
    ; Clear entity array
    ld   hl, entity_array
    ld   de, entity_array + 1
    ld   bc, MAX_ENTITIES * ENTITY_SIZE - 1
    ld   (hl), 0
    ldir

    ; Set up player (slot 0)
    ld   ix, entity_array
    ld   (ix + 0), 0        ; X fractional = 0
    ld   (ix + 1), 128      ; X pixel = 128 (centre)
    ld   (ix + 2), 160      ; Y = 160 (near bottom)
    ld   (ix + 3), TYPE_PLAYER
    ld   (ix + 4), 1        ; state = active
    ld   (ix + 5), 0        ; anim_frame
    ld   (ix + 6), 0        ; dx
    ld   (ix + 7), 0        ; dy
    ld   (ix + 8), 3        ; health = 3
    ld   (ix + 9), %00000111 ; ACTIVE + VISIBLE + COLLIDABLE

    ; Set up 8 enemies (slots 1-8) in a formation
    ld   ix, entity_array + ENTITY_SIZE   ; slot 1
    ld   b, 8               ; 8 enemies
    ld   c, 24              ; starting X pixel

.enemy_loop:
    ld   (ix + 0), 0        ; X fractional
    ld   (ix + 1), c        ; X pixel
    ld   (ix + 2), 32       ; Y = 32 (near top)
    ld   (ix + 3), TYPE_ENEMY
    ld   (ix + 4), 1        ; state = active
    ld   (ix + 5), 0        ; anim_frame
    ld   (ix + 6), 1        ; dx = 1 (moving right slowly)
    ld   (ix + 7), 0        ; dy = 0
    ld   (ix + 8), 1        ; health = 1
    ld   (ix + 9), %00000111 ; ACTIVE + VISIBLE + COLLIDABLE

    ; Advance to next slot and X position
    ld   de, ENTITY_SIZE
    add  ix, de
    ld   a, c
    add  a, 28              ; 28 pixels apart
    ld   c, a
    djnz .enemy_loop

    ret

; ============================================================
; Input system
; ============================================================
input_flags:      DB  0
input_prev:       DB  0
input_pressed:    DB  0

read_input_with_edges:
    ; Save previous
    ld   a, (input_flags)
    ld   (input_prev), a

    ; Read keyboard (QAOP + SPACE)
    ld   d, 0

    ; P key: half-row $DF, bit 0
    ld   bc, $DFFE
    in   a, (c)
    bit  0, a
    jr   nz, .no_right
    set  INPUT_RIGHT, d
.no_right:
    ; O key: half-row $DF, bit 1
    bit  1, a
    jr   nz, .no_left
    set  INPUT_LEFT, d
.no_left:

    ; Q key: half-row $FB, bit 0
    ld   b, $FB
    in   a, (c)
    bit  0, a
    jr   nz, .no_up
    set  INPUT_UP, d
.no_up:

    ; A key: half-row $FD, bit 0
    ld   b, $FD
    in   a, (c)
    bit  0, a
    jr   nz, .no_down
    set  INPUT_DOWN, d
.no_down:

    ; SPACE: half-row $7F, bit 0
    ld   b, $7F
    in   a, (c)
    bit  0, a
    jr   nz, .no_fire
    set  INPUT_FIRE, d
.no_fire:

    ld   a, d
    ld   (input_flags), a

    ; Compute edges
    ld   a, (input_prev)
    cpl
    ld   b, a
    ld   a, (input_flags)
    and  b
    ld   (input_pressed), a
    ret

; ============================================================
; Entity update loop
; ============================================================
update_entities:
    ld   ix, entity_array
    ld   b, MAX_ENTITIES

.loop:
    push bc
    ld   a, (ix + 9)        ; flags
    bit  FLAG_ACTIVE, a
    jr   z, .skip

    ld   a, (ix + 3)        ; type
    call update_by_type

.skip:
    ld   de, ENTITY_SIZE
    add  ix, de
    pop  bc
    djnz .loop
    ret

; ============================================================
; Type dispatch
; ============================================================
type_handlers:
    DW   .nop_handler       ; TYPE_INACTIVE
    DW   update_player
    DW   update_enemy
    DW   update_bullet
    DW   update_explosion

update_by_type:
    add  a, a
    ld   l, a
    ld   h, 0
    ld   de, type_handlers
    add  hl, de
    ld   e, (hl)
    inc  hl
    ld   d, (hl)
    ex   de, hl
    jp   (hl)

.nop_handler:
    ret

; ============================================================
; Player update
; ============================================================
update_player:
    ld   a, (input_flags)
    bit  INPUT_RIGHT, a
    jr   z, .not_right
    ld   a, (ix + 0)
    add  a, 2               ; move right (subpixel)
    ld   (ix + 0), a
    jr   nc, .x_done_r
    inc  (ix + 1)
.x_done_r:
    res  FLAG_FACING_L, (ix + 9)
    jr   .horiz_done
.not_right:
    bit  INPUT_LEFT, a
    jr   z, .horiz_done
    ld   a, (ix + 0)
    sub  2                   ; move left (subpixel)
    ld   (ix + 0), a
    jr   nc, .x_done_l
    dec  (ix + 1)
.x_done_l:
    set  FLAG_FACING_L, (ix + 9)
.horiz_done:

    ; Fire bullet on press (edge-detected)
    ld   a, (input_pressed)
    bit  INPUT_FIRE, a
    jr   z, .no_fire
    ld   b, (ix + 1)        ; player X pixel
    ld   c, (ix + 2)        ; player Y
    call spawn_bullet
.no_fire:

    ; Animate
    ld   a, (ix + 5)
    inc  a
    and  7
    ld   (ix + 5), a
    ret

; ============================================================
; Enemy update (simple patrol)
; ============================================================
update_enemy:
    ; Move by dx
    ld   a, (ix + 6)        ; dx
    add  a, (ix + 1)        ; add to X pixel
    ld   (ix + 1), a

    ; Bounce at screen edges
    cp   240
    jr   c, .no_bounce_r
    ld   (ix + 6), -1       ; reverse direction
    jr   .bounce_done
.no_bounce_r:
    cp   8
    jr   nc, .bounce_done
    ld   (ix + 6), 1        ; reverse direction
.bounce_done:

    ; Animate
    ld   a, (ix + 5)
    inc  a
    and  3                   ; 4-frame animation cycle
    ld   (ix + 5), a
    ret

; ============================================================
; Bullet update
; ============================================================
update_bullet:
    ld   a, (ix + 6)        ; dx
    add  a, (ix + 1)        ; add to X pixel (simplified: integer movement)
    ld   (ix + 1), a

    ; Off screen?
    cp   248
    jr   nc, .deactivate
    or   a
    jr   z, .deactivate
    ret

.deactivate:
    ld   (ix + 9), 0        ; clear all flags
    ret

; ============================================================
; Explosion update
; ============================================================
update_explosion:
    ld   a, (ix + 5)        ; anim_frame
    inc  a
    cp   8                   ; 8 frames
    jr   nc, .done
    ld   (ix + 5), a
    ret
.done:
    ld   (ix + 9), 0
    ret

; ============================================================
; Spawn bullet
; ============================================================
spawn_bullet:
    ; B = x pixel, C = y
    push ix
    ld   ix, entity_array + (9 * ENTITY_SIZE)   ; first projectile slot
    ld   d, 7               ; 7 slots to search

.find:
    ld   a, (ix + 9)
    bit  FLAG_ACTIVE, a
    jr   z, .found
    ld   e, ENTITY_SIZE
    push de
    pop  de                  ; (DE preserved; only low byte matters for add ix,de)
    ld   e, ENTITY_SIZE
    add  ix, de
    dec  d
    jr   nz, .find
    ; No free slot
    pop  ix
    scf
    ret

.found:
    ld   (ix + 0), 0
    ld   (ix + 1), b
    ld   (ix + 2), c
    ld   (ix + 3), TYPE_BULLET
    ld   (ix + 4), 1
    ld   (ix + 5), 0
    ld   (ix + 7), 0        ; dy = 0

    ; Direction from player facing
    ld   a, (entity_array + 9)   ; player flags
    bit  FLAG_FACING_L, a
    jr   z, .right
    ld   (ix + 6), -4       ; dx = -4
    jr   .dir_done
.right:
    ld   (ix + 6), 4        ; dx = +4
.dir_done:
    ld   (ix + 8), 1        ; health = 1
    ld   (ix + 9), %00000111 ; ACTIVE + VISIBLE + COLLIDABLE

    pop  ix
    or   a                   ; clear carry
    ret

; ============================================================
; Render entities (stub -- see Chapter 16 for sprite rendering)
; ============================================================
render_entities:
    ; In a real game, this iterates visible entities and draws sprites.
    ; See Chapter 16 for OR+AND masked sprites, pre-shifted sprites,
    ; and the dirty-rectangle system.
    ; For this skeleton, we use a minimal attribute-block renderer.
    ld   ix, entity_array
    ld   b, MAX_ENTITIES

.loop:
    push bc
    ld   a, (ix + 9)
    bit  FLAG_VISIBLE, a
    jr   z, .skip

    ; Draw a 1-character coloured block at entity position.
    ; For real sprite rendering, see Chapter 16 (OR+AND masks,
    ; pre-shifted sprites, compiled sprites, dirty rectangles).
    ld   a, (ix + 1)        ; X pixel
    rrca                     ; /2
    rrca                     ; /4
    rrca                     ; /8 = character column
    and  $1F                 ; mask to 0-31
    ld   e, a
    ld   a, (ix + 2)        ; Y pixel
    rrca
    rrca
    rrca
    and  $1F                 ; character row (0-23)
    ; Compute attribute address: $5800 + row*32 + col
    ld   l, a
    ld   h, 0
    add  hl, hl             ; row * 2
    add  hl, hl             ; row * 4
    add  hl, hl             ; row * 8
    add  hl, hl             ; row * 16
    add  hl, hl             ; row * 32
    ld   d, 0
    add  hl, de             ; + column
    ld   de, $5800
    add  hl, de             ; HL = attribute address

    ; Colour by type
    ld   a, (ix + 3)        ; type
    add  a, a               ; type * 2 (crude colour mapping)
    or   %01000000           ; BRIGHT bit
    ld   (hl), a            ; write attribute

.skip:
    ld   de, ENTITY_SIZE
    add  ix, de
    pop  bc
    djnz .loop
    ret

; ============================================================
; Data
; ============================================================
game_state:     DB   STATE_TITLE

entity_array:
    DS   MAX_ENTITIES * ENTITY_SIZE, 0
```

Este esqueleto compila, se ejecuta, y hace algo visible: bloques coloreados se mueven a través de la cuadrícula de atributos. El bloque del jugador responde a los controles QAOP. Presionar SPACE genera balas que vuelan a través de la pantalla. Los enemigos rebotan entre los bordes de la pantalla. Cuando una bala sale de la pantalla, su ranura se libera para el siguiente disparo.

Es feo -- bloques de atributos en lugar de sprites, sin desplazamiento, sin sonido. Pero la arquitectura está completa. Cada pieza de este capítulo está presente y conectada: el bucle principal impulsado por HALT, el despacho de máquina de estados, el lector de entrada con detección de flancos, el array de entidades con manejadores de actualización por tipo, y el pool de objetos para proyectiles. Los Capítulos 16 y 17 proporcionan el renderizado. El Capítulo 19 proporciona la física y colisiones. El Capítulo 11 proporciona la música. Este esqueleto es donde todos se conectan.

---

## 18.9 Agon Light 2: La Misma Arquitectura, Más Espacio

El Agon Light 2 usa la misma estructura fundamental de bucle de juego. El eZ80 ejecuta código Z80 nativamente (en modo compatible Z80 o modo ADL), así que el bucle principal basado en HALT, la máquina de estados, el sistema de entidades, y la lógica de entrada se traducen directamente.

Las diferencias clave:

**Sincronización de fotograma.** El Agon usa la llamada `waitvblank` de MOS (RST $08, función $1E) en lugar de `HALT` para la sincronización de fotograma. El VDP genera la señal de blanqueo vertical y la API MOS la expone.

**Entrada.** La lectura de teclado pasa por variables de sistema MOS en lugar de E/S directa de puerto. La matriz de semi-filas no existe -- el teclado PS/2 es manejado por el VDP ESP32. La capa de abstracción de entrada que construimos (todo confluye en `input_flags`) significa que el resto del código del juego no se preocupa por la diferencia.

**Presupuesto de entidades.** Con ~360,000 T-states por fotograma y renderizado de sprites por hardware, el bucle de actualización de entidades ya no es un cuello de botella. Podrías actualizar 64 entidades con IA compleja y aún usar menos del 10% del presupuesto de fotograma. El factor limitante en el Agon es el conteo de sprites VDP por línea de escaneo (típicamente 16-32 sprites de hardware visibles en la misma línea) en lugar del tiempo de CPU.

**Renderizado.** El VDP del Agon maneja el renderizado de sprites. En lugar de transferir píxeles manualmente a la memoria de pantalla (los seis métodos del Capítulo 16), emites comandos VDU para posicionar sprites de hardware. El coste de CPU por sprite baja de ~1,200 T-states (blit OR+AND en Spectrum) a ~50-100 T-states (enviar un comando de posición VDU). Esto libera un enorme tiempo de CPU para lógica de juego.

**Memoria.** El Agon tiene 512KB de memoria plana -- sin bancos, sin regiones contendidas. Tu array de entidades, tablas de consulta, datos de sprites, mapas de nivel, y música pueden coexistir todos sin la gimnasia de conmutación de bancos que el Capítulo 15 describe para el Spectrum 128K.

La conclusión práctica: en el Agon, la arquitectura de este capítulo escala sin esfuerzo. Más entidades, máquinas de estados más complejas, más lógica de IA -- nada de esto amenaza el presupuesto de fotograma. La disciplina de contar cada T-state sigue importando (es buena ingeniería), pero las restricciones que fuerzan compromisos angustiantes en el Spectrum simplemente no aplican.

---

## 18.10 Decisiones de Diseño y Compromisos

### Tasa de Fotogramas Fija vs Variable

El bucle principal de este capítulo asume una tasa fija de 50 fps: haz todo en un fotograma, o pierde. La alternativa es un paso de tiempo variable: medir cuánto tardó el fotograma y escalar todo el movimiento por delta-tiempo. Los pasos de tiempo variables son estándar en motores de juegos modernos pero añaden complejidad en el Z80 -- necesitas un temporizador de fotograma, multiplicación por delta en cada cálculo de movimiento, y manejo cuidadoso de la estabilidad de la física a tasas variables.

Para juegos de Spectrum, 50 fps fijos es casi universalmente la elección correcta. El hardware es determinístico, el presupuesto de fotograma es predecible, y la simplicidad de la física de paso fijo (todo se mueve cantidades constantes cada fotograma) elimina una categoría completa de errores. Si tu juego cae por debajo de 50 fps, la respuesta es optimizar hasta que no lo haga -- no añadir un paso de tiempo variable.

En el Agon, con su presupuesto más grande, es aún menos probable que necesites temporización variable. Fija la tasa de fotogramas a 50 o 60 fps y mantén la vida simple.

### Tamaño de Entidad: Ligero vs Generoso

Nuestra estructura de entidad de 10 bytes es ligera. Algunos juegos comerciales de Spectrum usaban 16 o incluso 32 bytes por entidad, almacenando campos adicionales como posición anterior (para borrado de rectángulos sucios), dirección de sprite, dimensiones de caja de colisión, temporizador de IA, y más.

El compromiso es velocidad de iteración versus acceso a campos. Nuestro array de 16 entidades toma 160 bytes y el bucle de actualización completo se ejecuta en ~8,000 T-states. Una estructura de 32 bytes con 16 entidades toma 512 bytes (aún pequeño) pero el overhead de iteración crece porque IX avanza 32 cada paso, y los accesos indexados a campos con desplazamientos altos como `(IX+28)` toman los mismos 19 T-states pero son más difíciles de rastrear.

Si necesitas más datos por entidad, considera dividir la estructura: un array "caliente" compacto (posición, tipo, banderas -- los campos tocados cada fotograma) y un array "frío" paralelo (dirección de sprite, estado de IA, valor de puntuación -- campos accedidos solo cuando se necesitan). Este es el mismo compromiso estructura-de-arrays versus array-de-estructuras que enfrentan los motores de juegos modernos, aplicado a la escala del Z80.

### Cuándo Usar HL en Lugar de IX

El direccionamiento indexado por IX es conveniente pero costoso: 19 T-states por acceso versus 7 para `(HL)`. En el bucle de actualización (llamado 16 veces por fotograma), el overhead de IX es aceptable -- 16 x 12 T-states extra por acceso = 192 T-states, despreciable.

Pero en el bucle de renderizado, donde podrías tocar 4-6 campos de entidad para cada uno de 8 sprites visibles, el coste se acumula. La técnica: al inicio del pase de renderizado para cada entidad, copia los campos que necesitas a registros:

```z80
    ; Copy entity fields to registers for fast rendering
    ld   l, (ix + 0)        ; 19T  X lo
    ld   h, (ix + 1)        ; 19T  X hi
    ld   c, (ix + 2)        ; 19T  Y
    ld   a, (ix + 5)        ; 19T  anim_frame
    ; Now render using H (X pixel), C (Y), A (frame)
    ; All subsequent accesses are register-to-register: 4T each
```

Cuatro accesos IX a 19T = 76T por adelantado, luego toda la rutina de renderizado usa accesos a registros de 4T en lugar de accesos IX de 19T. Si la rutina de renderizado toca esos campos 10 veces, ahorras (19-4) x 10 - 76 = 74 T-states por entidad. Pequeño, pero sobre 8 entidades por fotograma, son 592 T-states -- suficiente para dibujar otro medio sprite.

---

## Resumen

- El **bucle de juego** es `HALT -> Entrada -> Actualización -> Renderizado -> repetir`. La instrucción `HALT` se sincroniza con la interrupción de fotograma, dándote exactamente el valor de T-states de un fotograma (aproximadamente 64,000 en un Pentagon, 360,000 en el Agon).

- Una **máquina de estados** con una tabla de saltos de punteros a manejadores (`DW state_title`, `DW state_game`, etc.) organiza el flujo desde la pantalla de título a través del juego hasta el fin de partida. El despacho cuesta 73 T-states independientemente del número de estados -- tiempo constante, escalado limpio.

- La **lectura de entrada** en el Spectrum usa `IN A,(C)` para consultar semi-filas de teclado a través del puerto `$FE`. Cinco teclas (QAOP + SPACE) cuestan aproximadamente 220 T-states para leer. El joystick Kempston es una sola lectura de puerto de 11T. La detección de flancos (pulsación vs mantenimiento) usa XOR entre fotogramas actual y anterior.

- La **estructura de entidad** es de 10 bytes: X (punto fijo de 16 bits), Y, tipo, estado, anim_frame, dx, dy, salud, banderas. Dieciséis entidades ocupan 160 bytes. La multiplicación por 10 para conversión de índice a dirección usa la descomposición 10 = 8 + 2.

- El **array de entidades** se asigna estáticamente con asignaciones de ranura fijas: ranura 0 para el jugador, ranuras 1-8 para enemigos, ranuras 9-15 para proyectiles y efectos. La iteración verifica la bandera ACTIVE y despacha a manejadores por tipo a través de una segunda tabla de saltos.

- El **pool de objetos** es el propio array de entidades. La generación establece campos y la bandera ACTIVE. La desactivación limpia las banderas. La búsqueda de ranura libre es un escaneo lineal del rango de ranuras relevante. Siete ranuras de proyectiles manejan tasas de fuego típicas sin que el jugador note generaciones fallidas.

- El **direccionamiento indexado por IX** es conveniente para acceso a campos de entidad (19T por acceso) pero costoso en bucles internos. Copia campos a registros al inicio del renderizado para acceso de 4T en adelante.

- El Agon Light 2 usa la misma arquitectura con más margen. `waitvblank` de MOS reemplaza a `HALT`, el teclado PS/2 reemplaza el escaneo de semi-filas, los sprites de hardware reemplazan el blitting por CPU. El bucle de actualización de entidades ya no es el cuello de botella.

- El esqueleto práctico en este capítulo ejecuta una máquina de estados, 16 entidades (1 jugador + 8 enemigos + 7 ranuras de bala/efecto), entrada con detección de flancos, manejadores de actualización por tipo, y un renderizador mínimo de bloques de atributos. Es el chasis donde los Capítulos 16 (sprites), 17 (desplazamiento), 19 (colisiones), y 11 (sonido) se conectan.

---

## Inténtalo Tú Mismo

1. **Construye el esqueleto.** Compila el esqueleto de juego de la sección 18.8 y ejecútalo en un emulador. Usa QAOP para mover el bloque del jugador y SPACE para disparar. Observa los bloques coloreados moverse. Añade perfilado por color de borde (Capítulo 1) para ver cuánto presupuesto de fotograma se usa.

2. **Añade un sexto estado.** Implementa STATE_SHOP entre Menú y Juego. La pantalla de tienda debería mostrar tres objetos y dejar al jugador elegir uno con ARRIBA/ABAJO y FIRE. Esto ejercita la máquina de estados -- añade la constante, la entrada de tabla, el manejador, y la lógica de transición.

3. **Expande el conteo de entidades.** Incrementa MAX_ENTITIES a 32, añade 16 enemigos más, y mide el impacto en el presupuesto de fotograma con perfilado de borde. ¿Con cuántas entidades empieza el bucle de actualización a amenazar los 50 fps?

4. **Implementa soporte Kempston.** Añade el lector de joystick Kempston y combínalo con la entrada de teclado usando OR. Prueba en un emulador que soporte emulación Kempston (Fuse: Options -> Joysticks -> Kempston).

5. **Divide datos calientes y fríos.** Crea un segundo array "frío" con 4 bytes por entidad (dirección de sprite, temporizador de IA, estado de IA, valor de puntuación). Modifica el bucle de actualización para acceder a datos fríos solo cuando el tipo de entidad lo requiera (enemigos para IA, no balas). Mide el ahorro en T-states.

---

*Siguiente: Capítulo 19 -- Colisiones, Física e IA Enemiga. Añadiremos detección de colisiones AABB, gravedad, saltos, y cuatro patrones de comportamiento enemigo al esqueleto de este capítulo.*

---

> **Fuentes:** Documentación técnica de Sinclair Research sobre la matriz de teclado y disposición de puertos del ZX Spectrum; especificación de la interfaz de joystick Kempston; técnicas de aritmética de punto fijo del Capítulo 4 (Dark/X-Trade, Spectrum Expert #01, 1997); perfilado por color de borde del Capítulo 1; métodos de renderizado de sprites referenciados del Capítulo 16; integración de música AY referenciada del Capítulo 11; documentación de la API MOS del Agon Light 2 (Bernardo Kastrup, agon-light.com)
