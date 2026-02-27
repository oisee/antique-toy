# Capítulo 1: Pensar en Ciclos

> "Los efectos de coder siempre consisten en evolucionar un esquema de computación."
> -- Introspec (spke), Life on Mars

Tienes 71.680 ciclos de reloj. Ese es tu lienzo, tu presupuesto, tu mundo entero. Cada instrucción que escribes consume algunos de esos ciclos. Cada fotograma, el contador se reinicia y obtienes otros 71.680 -- ni más, ni menos. Si no cumples el plazo, la pantalla se desgarra, la música tartamudea, la ilusión se rompe.

Este capítulo trata sobre aprender a ver tu código como lo ve un demoscener del Z80: no como texto, no como algoritmos, sino como un *presupuesto*.

---

## T-States: La Moneda del Z80

La CPU Z80 no ejecuta instrucciones en bloques uniformes. Cada instrucción toma un número específico de **T-states** (estados de tiempo) -- los ciclos de reloj fundamentales del procesador. A 3,5 MHz, un T-state dura aproximadamente 286 nanosegundos. Ese número no es importante. Lo que importa es que las instrucciones tienen costes muy diferentes, y necesitas conocer esos costes de memoria.

Aquí tienes un puñado de instrucciones que usarás constantemente:

| Instrucción | Qué hace | T-states |
|-------------|----------|----------|
| `NOP` | Nada | 4 |
| `LD A,B` | Copia B en A | 4 |
| `LD A,(HL)` | Carga byte de la dirección de memoria en HL | 7 |
| `LD (HL),A` | Almacena A en la dirección de memoria en HL | 7 |
| `LD A,n` | Carga un byte inmediato en A | 7 |
| `INC HL` | Incrementa HL | 6 |
| `ADD A,B` | Suma B a A | 4 |
| `PUSH HL` | Empuja HL a la pila | 11 |
| `DJNZ label` | Decrementa B, salta si no es cero | 13 (tomado) / 8 (cae) |
| `LDIR` | Copia en bloque, por byte | 21 (repitiendo) / 16 (último byte) |
| `OUT (n),A` | Escribe A en puerto de E/S | 11 |

Observa el rango. Un `LD A,B` de registro a registro cuesta 4 T-states -- el mínimo para cualquier instrucción. Una lectura de memoria `LD A,(HL)` cuesta 7, porque la CPU necesita ciclos de máquina adicionales para poner la dirección en el bus y esperar a que la RAM responda. `LDIR`, la instrucción de copia en bloque a la que todo programador de Spectrum recurre instintivamente, cuesta 21 T-states por cada byte que copia (excepto el último, que cuesta 16). Eso es más de cinco veces el coste de un NOP.

![Costes en T-states de instrucciones Z80 comunes](illustrations/output/ch01_tstate_costs.png)

¿Por qué importa esto? Porque cuando estás llenando una pantalla, o actualizando datos de sprites, o calculando el siguiente fotograma de un efecto de plasma, cada instrucción consume tu presupuesto. La diferencia entre una instrucción de 4 T-states y una de 7 T-states, multiplicada por diez mil iteraciones en un bucle interno, es la diferencia entre un efecto que funciona a 50 fotogramas por segundo y uno que no.

### Ciclos de Máquina y Acceso a Memoria

Cada T-state es un tick del reloj de la CPU, pero el Z80 no se comunica con la memoria en cada tick. Las instrucciones se dividen en **ciclos de máquina** (M-cycles), cada uno de los cuales toma 3-6 T-states. El primer ciclo de máquina de cada instrucción es la **búsqueda de código de operación (opcode)** (M1), que siempre toma 4 T-states: la CPU pone el contador de programa en el bus de direcciones, lee el byte del opcode y simultáneamente refresca la DRAM. Los ciclos de máquina siguientes leen bytes adicionales (operandos, datos de memoria) o escriben resultados.

Por esto `LD A,B` toma exactamente 4 T-states -- es una instrucción de un solo byte que se completa enteramente dentro de la búsqueda de opcode. Pero `LD A,(HL)` toma 7 T-states: 4 para la búsqueda de opcode, luego 3 más para el ciclo de lectura de memoria donde la CPU pone HL en el bus de direcciones y lee el byte en esa dirección.

No necesitas memorizar el desglose interno de ciclos de máquina de cada instrucción. Pero entender el patrón -- búsqueda de opcode + lecturas de operandos + accesos a memoria = coste total -- te ayuda a desarrollar intuición sobre *por qué* las instrucciones cuestan lo que cuestan. Un `PUSH HL` a 11 T-states tiene sentido cuando te das cuenta de que la CPU debe hacer una búsqueda de opcode (5T para esta, ya que también decrementa SP), luego dos ciclos de escritura a memoria separados (3T cada uno) para almacenar los bytes alto y bajo de HL en la pila.

---

## El Fotograma: Tu Lienzo

El ZX Spectrum genera una señal de vídeo PAL a aproximadamente 50 fotogramas por segundo. Cada fotograma, el chip ULA lee la memoria de vídeo y pinta la pantalla, línea por línea. Al final de cada fotograma, la ULA dispara una interrupción enmascarable. La CPU ejecuta una instrucción `HALT` para esperar esa interrupción, hace su trabajo, y luego ejecuta `HALT` de nuevo para esperar el siguiente fotograma. Este es el latido de todo programa de Spectrum.

El número de T-states entre una interrupción y la siguiente -- el **presupuesto de fotograma** -- depende de la máquina:

| Máquina | T-states por fotograma | Líneas de escaneo | Hz |
|---------|------------------------|--------------------|----|
| ZX Spectrum 48K | 69.888 | 312 | 50,08 |
| ZX Spectrum 128K | 70.908 | 311 | 50,02 |
| Pentagon 128 | 71.680 | 320 | 48,83 |

Esos son T-states *totales* entre interrupciones. El presupuesto práctico es menor -- resta el coste del manejador de interrupciones (un reproductor de música PT3 típicamente consume 3.000--5.000 T-states por fotograma), la sobrecarga del HALT, y en máquinas que no son Pentagon, las penalizaciones por contención. En un Pentagon con un reproductor de música, espera aproximadamente 66.000--68.000 T-states para tu bucle principal. El Capítulo 15 tiene los mapas de tactos detallados.

![Desglose del presupuesto de fotograma en diferentes modelos de ZX Spectrum](illustrations/output/ch01_frame_budget.png)

Si tu bucle principal -- manejo de entrada, lógica del juego, actualización de sonido, renderizado de pantalla -- toma más T-states que un fotograma, pierdes fotogramas. Las cosas se ralentizan. El truco de la franja de borde que construiremos más adelante en este capítulo lo hará dolorosamente visible.

Para poner estos números en perspectiva: un solo `LDIR` copiando 6.912 bytes (una pantalla completa de datos de píxeles) cuesta aproximadamente 6.912 x 21 = 145.152 T-states. Eso es más de dos fotogramas enteros en un Spectrum 48K. Ni siquiera puedes copiar la pantalla una vez por fotograma con el método más simple posible. Este es el tipo de restricción que fuerza la creatividad.

---

## Pentagon vs. Máquinas con Espera

Notarás que los presupuestos de fotograma anteriores difieren entre máquinas. La diferencia no es solo en los números -- refleja una división arquitectónica fundamental que dio forma a la demoscene del ZX Spectrum.

### Las Máquinas Originales de Sinclair

En los Spectrum 48K y 128K originales, la memoria de pantalla vive en las direcciones `$4000`-`$5AFF` (datos de píxeles) y `$5800`-`$5B00` (atributos de color). Esta región de memoria -- todo el rango `$4000`-`$7FFF`, de hecho -- es **memoria contendida**. La ULA (Uncommitted Logic Array), que genera la señal de vídeo, necesita leer esta memoria para pintar la pantalla. La CPU y la ULA comparten el mismo bus de memoria, y cuando ambas quieren leer al mismo tiempo, la ULA gana. La CPU se ve obligada a esperar.

Durante las 192 líneas activas de visualización, cada acceso de la CPU al rango `$4000`-`$7FFF` se retrasa potencialmente. El retraso sigue un patrón repetitivo de 8 T-states: 6, 5, 4, 3, 2, 1, 0, 0 estados de espera adicionales, ciclando a lo largo de cada línea de escaneo. Una instrucción que debería tomar 7 T-states podría tomar 13 si cae en la peor fase del ciclo de contención.

Esto hace que el conteo de ciclos en los Spectrum originales sea una pesadilla. Tu bucle interno cuidadosamente calculado funciona a una velocidad diferente dependiendo de dónde en el fotograma se ejecuta, y si el código o los datos que toca están en el rango contendido. Introspec documentó esto en sus artículos "GO WEST" en Hype (2015): durante el renderizado de pantalla, cada acceso a byte de memoria contendida cuesta un promedio de 2,625 T-states adicionales. Para operaciones de pila que escriben en memoria de pantalla, espera aproximadamente 1,3 T-states adicionales por byte.

### El Pentagon: Temporización Limpia

El Pentagon 128, el clon soviético del ZX Spectrum más popular, adoptó un enfoque diferente. Sus diseñadores le dieron a la ULA su propia ventana de acceso a memoria que no entra en conflicto con la CPU. **No hay memoria contendida en el Pentagon.** Cada instrucción toma exactamente el número de T-states listado en la hoja de datos, independientemente de dónde viva el código o a qué memoria acceda.

Por esto el Pentagon tiene una duración de fotograma diferente -- 71.680 T-states, 320 líneas de escaneo. La temporización de la ULA es ligeramente diferente porque no hay necesidad de intercalar el acceso de CPU y ULA. Pero la recompensa es enorme: puedes contar ciclos con confianza absoluta. Cuando tu bucle interno dice que cuesta 36 T-states por iteración, cuesta 36 T-states por iteración, cada vez, en todas partes del fotograma.

Esta temporización limpia es la razón por la que el Pentagon se convirtió en la plataforma estándar para la demoscene del ZX Spectrum, particularmente en la antigua Unión Soviética donde estos clones eran ubicuos. Cuando ves demos de grupos como X-Trade, 4D+TBK (Triebkraft) o Life on Mars, están dirigidas abrumadoramente a la temporización del Pentagon. Cuando Introspec escribió su legendario análisis técnico de Illusion por X-Trade, los conteos de ciclos que citó asumían Pentagon.

Para aprender, el modelo Pentagon es ideal: puedes concentrarte en entender qué cuestan las instrucciones sin preocuparte por los efectos de contención. Todas las tablas de T-states en este libro asumen temporización Pentagon a menos que se indique lo contrario. Cuando necesitemos discutir las diferencias (y lo haremos, en el Capítulo 15), seremos explícitos.

**La regla práctica:** coloca tu código crítico en tiempo en memoria no contendida (`$8000`-`$FFFF` en un 48K), y tus conteos de ciclos serán correctos tanto en Pentagons como en Spectrums originales.

---

## Pensar en Presupuestos

Ahora que conoces el tamaño del fotograma, puedes empezar a hacer la aritmética que define el pensamiento de la demoscene Z80.

Digamos que quieres llenar la pantalla completa con un color calculado cada fotograma -- un efecto de plasma simple, actualizando solo los 768 bytes de memoria de atributos en `$5800`. A 50 fps, necesitas calcular y escribir 768 valores de color cada 71.680 T-states.

Si tu bucle interno por byte de atributo se ve así:

```z80
    ld   a,c        ; 4T   column index
    add  a,b        ; 4T   add row index (diagonal pattern)
    add  a,d        ; 4T   add frame counter (animation)
    and  7          ; 7T   clamp to 0-7
    ld   (hl),a     ; 7T   write attribute
    inc  hl         ; 6T   next attribute address
                    ; --- 32T per byte
```

Eso son 32 T-states por byte. Para 768 bytes: 32 x 768 = 24.576 T-states. Suma la sobrecarga del bucle (mantener contadores para filas y columnas, el `DJNZ` para el bucle interno), y podrías aterrizar alrededor de 28.000-30.000 T-states. Eso deja más de 40.000 T-states para todo lo demás -- reproducción de música, manejo de entrada, lo que necesites.

Pero ¿y si quisieras actualizar cada byte de *píxel*, los 6.144? A 32 T-states por byte, eso son 196.608 T-states -- casi tres fotogramas. De repente estás mirando una tasa de actualización de 17 fps en lugar de 50 fps. O necesitas un bucle interno más rápido, una región de actualización más pequeña, o un enfoque completamente diferente.

Así es como piensan los programadores del Z80. Cada decisión de diseño comienza con aritmética: cuántos bytes, cuántos T-states por byte, cuántos T-states en el presupuesto de fotograma, ¿cabe? Cuando no cabe, no buscas una máquina más rápida -- buscas un algoritmo más ingenioso.

---

> **Barra lateral Agon Light 2**
>
> El Agon Light 2 ejecuta un Zilog eZ80 a 18,432 MHz. El eZ80 ejecuta el mismo conjunto de instrucciones del Z80 (es un descendiente arquitectónico directo), pero la mayoría de las instrucciones se ejecutan en menos ciclos de reloj -- muchas instrucciones de un solo byte se completan en solo 1 ciclo en lugar de 4. A 18,432 MHz con una tasa de fotogramas de 50 Hz, obtienes aproximadamente **368.640 T-states por fotograma**.
>
> Eso es poco más de 5 veces el presupuesto del Pentagon. El mismo lenguaje ensamblador Z80, los mismos registros, los mismos mnemónicos de instrucciones -- pero con cinco veces más espacio para respirar. Un bucle interno que consume el 70% de un fotograma del Pentagon podría usar solo el 14% de un fotograma del Agon.
>
> Esto no hace al Agon "fácil". Tiene sus propias restricciones: no hay memoria de vídeo estilo ULA (la pantalla es gestionada por un coprocesador ESP32 que ejecuta el VDP), direccionamiento plano de 24 bits en lugar de memoria banqueada, y un modelo de E/S completamente diferente. Pero si alguna vez has deseado tener solo un *poco más de espacio* en tu presupuesto de fotograma para intentar algo ambicioso, el Agon es donde el mismo pensamiento Z80 escala.
>
> A lo largo de este libro, señalaremos dónde el presupuesto más grande del Agon cambia el cálculo. Por ahora, solo recuerda el número: **~368.000 T-states**. Mismo ISA, cinco veces el lienzo.

---

## Práctico: Configurando Tu Entorno de Desarrollo

Antes de escribir nuestro primer arnés de temporización, necesitas una cadena de herramientas funcional. La configuración descrita aquí sigue la guía de sq de Hype (2019), que se ha convertido en el estándar de la comunidad.

### Lo Que Necesitas

1. **VS Code** -- tu editor y entorno integrado.
2. **Extensión Z80 Macro Assembler** de mborik (`mborik.z80-macroasm`) -- resaltado de sintaxis, completado de código, resolución de símbolos para ensamblador Z80. Instálala desde el marketplace de VS Code.
3. **Z80 Assembly Meter** de Nestor Sancho -- muestra el conteo de bytes y el conteo de ciclos de la(s) instrucción(es) seleccionada(s) en la barra de estado. Esto es invaluable. Selecciona un bloque de código y ve su coste total en T-states instantáneamente.
4. **sjasmplus** -- el ensamblador en sí. Multiplataforma, código abierto, soporta macros, scripting Lua, múltiples formatos de salida. Descárgalo de https://github.com/z00m128/sjasmplus y coloca el binario en algún lugar de tu PATH.
5. **Unreal Speccy** (Windows) o **Fuse** (multiplataforma) -- el emulador. Se prefiere Unreal Speccy para desarrollo de demos porque emula la temporización del Pentagon con precisión y tiene un depurador integrado.

### Estructura del Proyecto

Crea un directorio para tus experimentos del Capítulo 1. Un proyecto mínimo se ve así:

```
ch01/
  main.a80          -- your source file
  build.bat         -- (Windows) sjasmplus main.a80
  Makefile           -- (macOS/Linux) make target
```

### Configuración de Compilación

En VS Code, configura una tarea de compilación (`.vscode/tasks.json`) para poder compilar con Ctrl+Shift+B:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Assemble Z80",
      "type": "shell",
      "command": "sjasmplus",
      "args": [
        "--fullpath",
        "--nologo",
        "--msg=war",
        "${file}"
      ],
      "group": {
        "kind": "build",
        "isDefault": true
      },
      "problemMatcher": {
        "owner": "z80",
        "fileLocation": "absolute",
        "pattern": {
          "regexp": "^(.*)\\((\\d+)\\):\\s+(error|warning):\\s+(.*)$",
          "file": 1,
          "line": 2,
          "severity": 3,
          "message": 4
        }
      }
    }
  ]
}
```

Presiona Ctrl+Shift+B. Si sjasmplus está en tu PATH y no hay errores, obtendrás un archivo `.sna` o `.tap` (dependiendo de tus directivas de fuente) que puedes abrir directamente en tu emulador.

Para integración con Unreal Speccy, la extensión de Alex_Rider de 2024 añade un enlace F5-para-lanzar -- el emulador abre tu snapshot compilado automáticamente. Si estás en macOS o Linux y usas Fuse, una regla simple en el Makefile hace lo mismo:

```makefile
run: main.sna
	fuse --machine pentagon main.sna
```

---

## Práctico: El Arnés de Temporización

Esta es la herramienta de depuración más importante que construirás en todo este libro. Es extremadamente simple, no requiere hardware especial, y la usarás constantemente.

La idea: cambia el color del borde a rojo inmediatamente antes del código que quieres medir, y cámbialo de vuelta a negro inmediatamente después. El borde del Spectrum es dibujado por la ULA en tiempo real, sincronizado con el haz de electrones. Una franja roja más ancha significa más T-states gastados en tu código.

Aquí está el arnés completo:

```z80
    ORG $8000

start:
    ; Wait for the frame interrupt
    halt

    ; --- Border RED: code under test begins ---
    ld   a, 2          ; 7T  red = colour 2
    out  ($FE), a      ; 11T write to border port

    ; ===== CODE UNDER TEST =====
    ; Replace this block with whatever you want to measure.
    ; Example: 256 iterations of a NOP loop.

    ld   b, 0          ; 7T  B=0 wraps to 256 iterations
.loop:
    nop                ; 4T
    nop                ; 4T
    nop                ; 4T
    nop                ; 4T  -- 16T per iteration body
    djnz .loop         ; 13T taken, 8T on final iteration
    ; Total: 256 * (16+13) - 5 = 7,419 T-states

    ; ===== END CODE UNDER TEST =====

    ; --- Border BLACK: idle ---
    xor  a             ; 4T  A=0 (black), shorter than LD A,0
    out  ($FE), a      ; 11T

    ; Loop forever
    jr   start
```

Carga esto en tu emulador. Verás una franja roja a través del borde. La altura de esa franja es directamente proporcional al número de T-states que tu código de prueba consumió.

### Leyendo la Franja

Cada línea de escaneo toma 224 T-states (en Pentagon). Así que si tu franja roja tiene N líneas de escaneo de alto, tu código tomó aproximadamente N x 224 T-states. El ejemplo anterior usa aproximadamente 7.419 T-states, que son aproximadamente 33 líneas de escaneo -- deberías ver una banda roja de aproximadamente un sexto del camino hacia abajo del borde.

Ahora intenta reemplazar el bucle NOP con algo más pesado. Reemplaza los cuatro NOPs con:

```z80
.loop:
    ld   a,(hl)        ; 7T
    add  a,(hl)        ; 7T
    ld   (de),a        ; 7T
    inc  hl            ; 6T   -- 27T per iteration body
    djnz .loop         ; 13T taken
    ; Total: 256 * (27+13) - 5 = 10,235 T-states
```

La franja roja crece notablemente. Esa diferencia visual -- puedes verla sin un depurador, sin un perfilador, sin ninguna herramienta -- son 2.816 T-states. Aproximadamente 12 líneas de escaneo.

Así es como los programadores de demos del Spectrum han perfilado sus efectos desde los años 80. El borde es tu osciloscopio.

### Variaciones

Puedes usar diferentes colores para marcar diferentes fases de tu código:

```z80
    ld   a, 2          ; red
    out  ($FE), a
    call render_sprites
    ld   a, 1          ; blue
    out  ($FE), a
    call update_music
    ld   a, 4          ; green
    out  ($FE), a
    call game_logic
    xor  a             ; black
    out  ($FE), a
```

Ahora el borde muestra una banda roja (renderizado de sprites), luego azul (música), luego verde (lógica del juego), luego negro (tiempo libre). Puedes ver de un vistazo qué subsistema está consumiendo tu presupuesto de fotograma.

Una nota sobre `xor a` versus `ld a, 0`: ambos establecen A en cero. `XOR A` toma 4 T-states y 1 byte. `LD A, 0` toma 7 T-states y 2 bytes. En un arnés de temporización la diferencia es despreciable, pero vale la pena notarla -- este tipo de micro-conciencia es de lo que está hecho el código Z80.

---

## ¿Qué Cabe en un Fotograma?

Usemos nuestra aritmética de presupuesto para responder algunas preguntas prácticas.

**¿Cuántos sprites puedes dibujar por fotograma?** Un sprite enmascarado de 16x16 usando el método OR+AND toma aproximadamente 16 líneas de escaneo x (leer máscara + leer sprite + leer pantalla + combinar + escribir pantalla) por byte. Una estimación razonable es de unos 1.200 T-states por sprite. En un Pentagon, eso son 71.680 / 1.200 = ~59 sprites, si el renderizado de sprites fuera lo *único* que hicieras. En la práctica, con música, lógica del juego y todo lo demás, 8-12 sprites completos por fotograma es típico.

**¿Cuántos bytes puede copiar LDIR por fotograma?** A 21 T-states por byte: 71.680 / 21 = 3.413 bytes. Ni siquiera la mitad de la pantalla.

**¿Cuántas operaciones de multiplicación?** Una multiplicación rápida de tabla de cuadrados 8x8 toma unos 54 T-states. 71.680 / 54 = 1.327 multiplicaciones por fotograma. Una rotación 3D de un solo punto necesita 9 multiplicaciones. Así que podrías rotar unos 147 puntos por fotograma *si no hicieras nada más*. Límite práctico con un motor de demo completo: 30-50 puntos.

Cada pregunta de diseño se reduce a esta aritmética. ¿Puedo hacerlo? ¿Cuántos puedo hacer? ¿A qué tengo que renunciar para hacer espacio?

---

## Nota Histórica: El Consejo de Dark

En 1997, un programador llamado Dark del grupo X-Trade publicó una serie de artículos en *Spectrum Expert* #01, una revista electrónica rusa para desarrolladores de ZX Spectrum. Estos artículos cubrían multiplicación, división, generación de seno/coseno, y algoritmos de dibujo de líneas en ensamblador Z80 -- los bloques de construcción fundamentales que alimentan cada efecto de demo.

Dark abrió con este consejo:

> "Lee un libro de texto de matemáticas -- derivadas, integrales. Conociéndolas, puedes crear una tabla de prácticamente cualquier función en ensamblador."

Esto no era teoría vacía. Dark no era solo un escritor -- era un programador. La demo *Illusion* de X-Trade, lanzada en ENLiGHT'96, presentaba una esfera giratoria texturizada, un rotozoomer, un motor 3D y un scroller de puntos rebotantes, todo funcionando en un Z80 a 3,5 MHz. Los algoritmos que Dark describió en sus artículos de revista eran los mismos algoritmos que alimentaban los efectos de su demo.

Veinte años después, Introspec (spke) publicó un análisis técnico detallado de Illusion en Hype, analizando los bucles internos instrucción por instrucción, contando cada T-state. Los artículos de revista de 1997 y la ingeniería inversa de 2017 cuentan la misma historia desde ambos lados: el autor explicando sus bloques de construcción, y un par midiendo la máquina terminada. Seguiremos este hilo a lo largo del libro.

El punto de Dark se mantiene: las matemáticas no son opcionales. No necesitas un título en matemáticas, pero necesitas entender cómo convertir una función matemática en una tabla, cómo aproximar operaciones costosas con otras baratas, y cómo pensar sobre error versus velocidad. El Capítulo 4 recorrerá los algoritmos de Dark en detalle. Por ahora, recuerda su consejo. Es el punto de partida de todo.

---

## El Esquema de Computación

Introspec, escribiendo sobre lo que hace un buen efecto de demo, destiló la filosofía en una sola frase:

> "Los efectos de coder siempre consisten en evolucionar un esquema de computación."

Esta es la idea más profunda de este capítulo. Un efecto de demo no es una imagen; es un *proceso*. Cada fotograma, el esquema de computación produce el siguiente estado a partir del anterior. El arte está en elegir un esquema que produzca una evolución visualmente convincente mientras cabe dentro del presupuesto de fotograma.

Un plasma es un esquema de computación: suma ondas sinusoidales en cada posición de la cuadrícula, desplazadas por el tiempo. Un túnel es un esquema de computación: busca ángulo y distancia en tablas precalculadas, desplazados por el tiempo. Un objeto 3D giratorio es un esquema de computación: multiplica coordenadas de vértices por una matriz de rotación que cambia cada fotograma. El esquema particular determina el resultado visual, el coste en T-states y los requisitos de memoria -- todo a la vez, todo interrelacionado.

Cuando te sientas a escribir un efecto, no estás preguntando "¿cómo dibujo esta imagen?". Estás preguntando "¿qué computación, evolucionada fotograma a fotograma, produce este visual?" Ese cambio de pensamiento -- de imagen a proceso, de salida a esquema -- es la visión del mundo del programador de Z80.

Y la primera restricción de cualquier esquema es el presupuesto. 71.680 T-states. ¿Puedes evolucionar tu computación dentro de ese presupuesto? Si no, ¿puedes encontrar un esquema más barato que produzca un visual similar? ¿Puedes precalcular parte del esquema en tablas? ¿Puedes repartir la computación entre múltiples fotogramas? ¿Puedes explotar la simetría para calcular la mitad de la pantalla y reflejar la otra mitad?

Estas son las preguntas que impulsan cada capítulo de este libro. Comienzan aquí, con contar T-states.

---

## Resumen

- Cada instrucción del Z80 tiene un coste específico en T-states. Aprende los comunes de memoria: `NOP` = 4, `LD A,B` = 4, `LD A,(HL)` = 7, `PUSH HL` = 11, `LDIR` = 21/16, `OUT (n),A` = 11.
- El **presupuesto de fotograma** es tu restricción dura: 69.888 T-states (48K), 70.908 (128K), o 71.680 (Pentagon). A 50 fps, todo debe caber.
- **Pentagon no tiene memoria contendida**, haciendo que los conteos de ciclos sean fiables y predecibles. Por eso se convirtió en el estándar de la demoscene.
- El **Agon Light 2** (eZ80 @ 18,432 MHz) da ~368.000 T-states por fotograma -- mismo conjunto de instrucciones, cinco veces el espacio.
- El **arnés de temporización con color de borde** es tu osciloscopio: rojo antes, negro después, lee el ancho de la franja.
- La programación Z80 es **aritmética de presupuesto**: bytes x T-states por byte vs. presupuesto de fotograma. Cada decisión de diseño comienza aquí.
- Los efectos son **esquemas de computación evolucionados en el tiempo**. El arte es encontrar un esquema que quepa en el presupuesto y se vea bien.

---

## Inténtalo Tú Mismo

1. Construye el arnés de temporización de este capítulo. Reemplaza el bucle NOP con un `LDIR` que copie 256 bytes y compara el ancho de la franja con la versión NOP. Calcula la diferencia esperada en T-states y verifícala visualmente.

2. Escribe un bucle que llene los 768 bytes de memoria de atributos (`$5800`-`$5AFF`) con un valor de color único. Mídelo con el arnés. Ahora intenta llenarlo usando `LDIR` en lugar de un bucle byte por byte. ¿Cuál es más rápido? ¿Por cuántas líneas de escaneo?

3. Abre el Z80 Assembly Meter en VS Code. Selecciona diferentes bloques de código y observa el contador de T-states en la barra de estado. Acostúmbrate a verificar los costes mientras escribes.

4. Configura el perfilador de borde multicolor (rojo / azul / verde / negro) con tres bucles ficticios de diferentes longitudes. Ajusta los conteos del bucle hasta que puedas distinguir visualmente las tres bandas. Este es tu ejercicio de calibración para leer la temporización del borde.

---

*Siguiente: Capítulo 2 -- La Pantalla como un Puzle. Nos sumergiremos en el notoriamente desordenado diseño de memoria de vídeo del Spectrum y aprenderemos por qué `INC H` te mueve un píxel hacia abajo.*
