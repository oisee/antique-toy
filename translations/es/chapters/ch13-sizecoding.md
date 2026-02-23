# Capítulo 13: El arte del sizecoding

> "Era como jugar juegos de rompecabezas -- un constante reordenamiento de código para encontrar codificaciones más cortas."
> -- UriS, sobre escribir NHBF (2025)

Hay una categoría de competición del demoscene donde la restricción no es el tiempo sino el *espacio*. Tu programa completo -- el código que dibuja la pantalla, produce el sonido, maneja el bucle de fotogramas, contiene los datos que necesite -- debe caber en 256 bytes. O 512. O 1K, o 4K, u 8K. Ni un byte más. El archivo se mide, y si son 257 bytes, queda descalificado.

Estas son competiciones de **sizecoding**, y producen algunos de los trabajos más notables de la escena del ZX Spectrum. Una intro de 256 bytes que llena la pantalla con patrones animados y toca una melodía reconocible es una forma de compresión tan extrema que roza la magia. La brecha entre lo que ve la audiencia y el tamaño del archivo que lo produce -- esa brecha es el arte.

Este capítulo trata sobre la mentalidad, las técnicas y los trucos específicos que hacen posible el sizecoding.

---

## 13.1 ¿Qué es el sizecoding?

Las competiciones de demos típicamente ofrecen varias categorías con límite de tamaño:

| Categoría | Límite de tamaño | Qué cabe |
|----------|-----------|-----------|
| 256 bytes | 256 | Un efecto ajustado, quizás sonido simple |
| 512 bytes | 512 | Un efecto con música básica o dos efectos simples |
| 1K intro | 1.024 | Múltiples efectos, música apropiada, transiciones |
| 4K intro | 4.096 | Una demo corta con varias partes |
| 8K intro | 8.192 | Una mini-demo pulida |

Los límites son absolutos. El archivo se mide en bytes, y no hay negociación.

Lo que hace fascinante al sizecoding es que invierte la jerarquía normal de optimización. En el mundo de efectos del demoscene con conteo de ciclos, optimizas para *velocidad* -- desenrollando bucles, duplicando datos, generando código, todo intercambiando espacio por tiempo. El sizecoding invierte esto. La velocidad no importa. La legibilidad no importa. La única pregunta es: ¿puedo hacerlo un byte más corto?

UriS, quien escribió la intro de 256 bytes NHBF para Chaos Constructions 2025, describió el proceso como "jugar juegos de rompecabezas." La descripción es exacta. El sizecoding es un rompecabezas donde las piezas son instrucciones Z80, el tablero son 256 bytes de RAM, y las mejores soluciones involucran movimientos que resuelven múltiples problemas simultáneamente.

El cambio de mentalidad:

- **Cada byte es precioso.** Una instrucción de 3 bytes donde una de 2 bytes basta es el 0,4% de tu programa entero. A 256 bytes, un byte ahorrado es como ahorrar 250 bytes en un programa de 64K.

- **Código y datos se superponen.** Los mismos bytes que se ejecutan como instrucciones pueden servir como datos. El Z80 no conoce la diferencia -- solo la ruta del contador de programa a través de la memoria distingue el código de los datos.

- **La elección de instrucción está impulsada por el tamaño, no la velocidad.** `RST $10` cuesta 1 byte. `CALL $0010` hace lo mismo en 3 bytes. En una demo normal nunca lo notarías. En 256 bytes, esos 2 bytes son la diferencia entre tener sonido o no.

- **El estado inicial es datos gratis.** Después del arranque, los registros tienen valores conocidos. La memoria en ciertas direcciones contiene datos conocidos. Un programador de sizecoding explota cada bit de este estado gratuito.

- **El código auto-modificable no es un truco -- es una necesidad.** Cuando no puedes permitirte una variable separada, modificas el operando de una instrucción en su lugar.

---

## 13.2 Anatomía de una intro de 256 bytes: NHBF

**NHBF** (No Heart Beats Forever) fue creada por UriS para Chaos Constructions 2025, inspirada por RED REDUX de Multimatograf 2025. Produce texto con efectos de pantalla y música -- acordes de potencia de onda cuadrada en bucle con notas de melodía pentatónica aleatorias -- todo en 256 bytes.

### La música

A 256 bytes, no puedes incluir un reproductor de tracker ni tablas de notas. NHBF controla el chip AY directamente. Los acordes de potencia están codificados como valores inmediatos en las instrucciones de escritura de registros del AY -- los mismos bytes que forman el operando de `LD A, n` *son* la nota musical. El canal de melodía usa un generador pseudo-aleatorio (típicamente `LD A, R` -- leer el registro de refresco -- seguido de AND para enmascarar el rango) para elegir de una escala pentatónica. Una escala pentatónica suena agradable sin importar qué notas caigan una al lado de otra, así que la melodía suena intencional aunque sea aleatoria. Dos bytes para un número "aleatorio"; cinco notas que nunca chocan.

### Lo visual

Imprimir texto a través de la ROM -- `RST $10` muestra un carácter por 1 byte por llamada -- es la manera más barata de poner píxeles en pantalla. Pero incluso una cadena de 20 caracteres cuesta 40 bytes (códigos de carácter + llamadas RST). Los programadores de sizecoding buscan formas de comprimir más: superponer los datos de la cadena con otro código, o computar caracteres desde una fórmula.

### El rompecabezas: Encontrar superposiciones

UriS describe el proceso central como un reordenamiento constante. Escribes una primera versión a 300 bytes, luego la miras fijamente. Notas que el contador de bucle para el efecto visual termina con el valor que necesitas como número de registro del AY. Eliminas el `LD A, 7` que lo establecería -- el bucle ya dejó A con 7. Dos bytes ahorrados. La rutina de limpieza de pantalla usa LDIR, que decrementa BC a cero. Arregla el código para que la siguiente sección necesite BC = 0, y ahorra el `LD BC, 0` -- otros 3 bytes.

Cada instrucción produce efectos secundarios -- valores de registro, estados de banderas, contenidos de memoria -- y el arte es organizar las instrucciones para que los efectos secundarios de una rutina sean las entradas de otra.

### El descubrimiento de Art-Top

Durante el desarrollo, Art-Top notó algo notable: los valores de registro sobrantes de la rutina de limpieza de pantalla coincidían con la longitud exacta necesaria para la cadena de texto. No fue planeado. UriS había escrito la limpieza de pantalla, luego la salida de texto, y las dos resultaron compartir un estado de registro que eliminaba un contador de longitud separado.

Este tipo de superposición fortuita es el corazón de la programación de 256 bytes. No puedes planificarlo. Solo puedes crear condiciones donde pueda ocurrir, reordenando constantemente el código y observando alineaciones accidentales. Cuando encuentras una, se siente como descubrir que dos piezas de rompecabezas de puzzles diferentes encajan perfectamente.

### Técnicas clave a 256 bytes

**1. Usar el estado inicial de registros y memoria.** Después de una carga estándar por cinta, los registros tienen valores conocidos: A a menudo contiene el último byte cargado, BC la longitud del bloque, HL apunta cerca del final de los datos cargados. El área de variables del sistema ($5C00-$5CB5) contiene valores conocidos. La memoria de pantalla está limpia después de CLS. Cada valor conocido que explotas en lugar de cargarlo explícitamente ahorra 1-3 bytes.

**2. Superponer código y datos.** El byte $3E es el código de operación (opcode) de `LD A, n` y también el valor 62 -- un carácter ASCII, una coordenada de pantalla, o un valor de registro del AY. Si tu programa ejecuta este byte como una instrucción *y* lo lee como datos desde una ruta de código diferente, has hecho que un byte haga dos trabajos. Patrón común: el operando inmediato de `LD A, n` sirve como datos que otra rutina lee con `LD A, (addr)` apuntando a instruction_address + 1.

**3. Elegir instrucciones por tamaño.**

| Codificación larga | Codificación corta | Ahorro |
|---------------|----------------|---------|
| `CALL $0010` (3 bytes) | `RST $10` (1 byte) | 2 bytes |
| `JP label` (3 bytes) | `JR label` (2 bytes) | 1 byte |
| `LD A, 0` (2 bytes) | `XOR A` (1 byte) | 1 byte |
| `CP 0` (2 bytes) | `OR A` (1 byte) | 1 byte |

Las instrucciones RST son críticas. `RST n` es un CALL de 1 byte a una de ocho direcciones ($00, $08, $10, $18, $20, $28, $30, $38). En el Spectrum, `RST $10` llama a la salida de caracteres de la ROM, `RST $28` entra en la calculadora. En una demo normal estas rutinas ROM son demasiado lentas. A 256 bytes, ahorrar 2 bytes por CALL lo es todo.

**Cada JP en una intro de 256 bytes debería ser un JR** -- todo el programa cabe dentro del rango -128..+127.

**4. Código auto-modificable para reusar secuencias.** ¿Necesitas una subrutina para operar en dos direcciones diferentes? Codifica la primera y parchea el operando para la segunda llamada. Más barato que pasar parámetros.

**5. Relaciones matemáticas entre constantes.** Si tu música necesita un período de tono de 200 y tu efecto necesita un contador de bucle de 200, usa el mismo registro. Si un valor es el doble de otro, usa `ADD A, A` (1 byte) en lugar de cargar una segunda constante (2 bytes).

---

## 13.3 El truco de LPRINT

En 2015, diver4d publicó "Los secretos de LPRINT" en Hype, documentando una técnica más antigua que el propio demoscene -- una que apareció por primera vez en los cargadores de software pirata en casete en los años 80.

### Cómo funciona

La variable del sistema en la dirección 23681 ($5C81) controla a dónde las rutinas de salida de BASIC dirigen los datos. Normalmente apunta al búfer de impresora. Modifícala para apuntar a la memoria de pantalla, y LPRINT escribe directamente en la pantalla:

```basic
10 POKE 23681,64: LPRINT "HELLO"
```

Ese único POKE redirige el canal de impresora a $4000 -- el inicio de la memoria de pantalla.

### El efecto de transposición

El resultado visual no es solo texto en pantalla -- es texto *transpuesto*. La memoria de pantalla del Spectrum es entrelazada (Capítulo 2), pero el controlador de impresora escribe secuencialmente. Los datos aterrizan en la memoria de pantalla según la lógica lineal del controlador pero se *muestran* según el diseño entrelazado. El resultado cicla a través de 8 estados visuales a medida que progresa por los tercios de la pantalla -- una cascada de datos que se construye en bandas horizontales, desplazándose y recombinándose.

Con diferentes datos de caracteres -- caracteres gráficos, UDGs, o secuencias ASCII cuidadosamente elegidas -- la transposición produce patrones visuales impactantes. La sentencia LPRINT maneja todo el direccionamiento de pantalla, renderizado de caracteres y avance del cursor. Tu programa solo proporciona los datos.

### De cargadores piratas al arte demo

diver4d rastreó el truco hasta los cargadores de casetes piratas. Los piratas que añadían pantallas de carga personalizadas necesitaban efectos visuales en muy pocos bytes de BASIC -- LPRINT era ideal. La técnica cayó en desuso a medida que la escena se movió al código máquina.

Pero en 2011, JtN y 4D lanzaron **BBB**, una demo que deliberadamente volvió a LPRINT como declaración artística. El viejo truco del cargador pirata, enmarcado con intención, se convirtió en arte demo. La restricción -- BASIC, un hack de redirección de impresora, sin código máquina -- se convirtió en el medio.

### Por qué importa para el sizecoding

LPRINT logra una salida de pantalla compleja por casi cero bytes de tu propio código. La ROM hace el trabajo pesado. Tu contribución: un POKE para redirigir la salida, datos para imprimir, y `RST $10` (o LPRINT) para dispararlo. Aprovechas la ROM de 16K del Spectrum como un motor de salida de pantalla "gratuito" -- código que no cuenta contra tu límite de tamaño.

---

## 13.4 Intros de 512 bytes: Espacio para respirar

Duplicar de 256 a 512 bytes no es el doble -- es cualitativamente diferente. A 256, luchas por cada instrucción y el sonido es mínimo. A 512, puedes tener un efecto apropiado *y* sonido apropiado, o dos efectos con una transición.

### Patrones comunes de 512 bytes

**Plasma vía sumas de tabla de seno.** La tabla de seno es la parte costosa. Una tabla completa de 256 bytes consume la mitad de tu presupuesto. Soluciones: una tabla de cuarto de onda de 64 entradas reflejada en tiempo de ejecución (ahorra 192 bytes), o generar la tabla al inicio usando la aproximación parabólica del Capítulo 4 (~20 bytes de código en lugar de 256 bytes de datos).

**Túnel vía consulta de ángulo/distancia.** A 512 bytes, calculas ángulo y distancia al vuelo usando aproximaciones burdas. Menor calidad visual que el túnel de Eager (Capítulo 9), pero reconociblemente un túnel.

**Fuego vía autómata celular.** Cada celda promedia sus vecinos de abajo, menos decaimiento. Pocas instrucciones por píxel, animación convincente, y a 512 bytes puedes añadir atributos para color *y* un sonido de beeper.

### Trucos de auto-modificación

La auto-modificación se vuelve estructural a 512 bytes. Incrusta el contador de fotograma *dentro* de una instrucción:

```z80
frame_ld:
    ld   a, 0               ; this 0 is the frame counter
    inc  a
    ld   (frame_ld + 1), a  ; update the counter in place
```

Sin variable separada. El contador vive en el flujo de instrucciones.

Parchea offsets de salto para cambiar entre efectos:

```z80
effect_jump:
    jr   effect_1               ; this offset gets patched
    ; ...
effect_1:
    ; render effect 1, then:
    ld   a, effect_2 - effect_jump - 2
    ld   (effect_jump + 1), a   ; next frame jumps to effect 2
```

### El truco del ORG

Elige la dirección ORG de tu programa para que los bytes de dirección en sí mismos sean datos útiles. Coloca código en $4000 y cada JR/DJNZ que apunte a etiquetas cerca del inicio genera bytes de offset pequeños -- utilizables como contadores de bucle, valores de color, o números de registro del AY. Si tu efecto necesita $40 (el byte alto de la memoria de pantalla) como constante, coloca código en una dirección donde $40 aparezca naturalmente en un operando de dirección. La *codificación del propio código* proporciona datos que necesitas en otra parte.

Este es el nivel más profundo del rompecabezas del sizecoding.

---

## 13.5 Práctica: Escribir una intro de 256 bytes paso a paso

Comienza con un plasma de atributos funcional (~400 bytes) y optimízalo a 256.

### Paso 1: La versión sin optimizar

Un plasma de atributos simple: llena 768 bytes de memoria de atributos con valores de sumas de seno, desplazados por un contador de fotograma. Sonido: una melodía cíclica en el canal A del AY. Esta versión es limpia, legible, y de aproximadamente 400 bytes -- la tabla de seno (32 bytes), tabla de notas (16 bytes), escrituras AY en línea, y el bucle de plasma con consultas de tabla.

### Paso 2: Reemplazar CALL con RST

Cualquier llamada a una dirección ROM que coincida con un vector RST ahorra 2 bytes por invocación. Para la salida del AY, reemplaza las seis escrituras verbosas de registros en línea (~60 bytes) con una pequeña subrutina:

```z80
ay_write:                      ; register in A, value in E
    ld   bc, $FFFD
    out  (c), a
    ld   b, $BF
    out  (c), e
    ret                        ; 8 bytes total
```

Seis llamadas (5 bytes cada una: cargar A + cargar E + CALL) = 30 + 8 = 38 bytes. Ahorro: ~22 bytes.

### Paso 3: Superponer datos con código

La tabla de seno de 32 bytes al punto de entrada se decodifica como instrucciones Z80 mayormente inofensivas ($00=NOP, $06=LD B,n, $0C=INC C...). Colócala al inicio del programa. En la primera ejecución, la CPU tropieza a través de estas "instrucciones," revolviendo algunos registros. El bucle principal luego salta más allá de la tabla y nunca la ejecuta de nuevo -- pero los datos permanecen para las consultas. Los bytes de la tabla cumplen doble función.

### Paso 4: Explotar el estado de los registros

Después de que el bucle de plasma escribe 768 atributos, HL = $5B00 y BC = 0 (de cualquier LDIR usado en la inicialización). Si la siguiente operación necesita estos valores, omite las cargas explícitas. El descubrimiento de Art-Top en NHBF fue exactamente esto: los valores de los registros de la limpieza de pantalla coincidían con la longitud de la cadena de texto. No fue planeado. Fue notado.

Después de cada pase de optimización, anota lo que cada registro contiene en cada punto. El estado de los registros es un recurso compartido -- la moneda fundamental del sizecoding.

### Paso 5: Codificaciones más pequeñas en todas partes

- `LD A, 0` -> `XOR A` (ahorrar 1 byte)
- `LD HL, nn` + `LD A, (HL)` -> `LD A, (nn)` (ahorrar 1 byte si HL no se necesita)
- `JP` -> `JR` en todas partes (ahorrar 1 byte cada vez)
- `CALL sub : ... : RET` -> caer directamente (ahorrar 4 bytes)
- `PUSH AF` para guardados temporales vs `LD (var), A` (ahorrar 2 bytes)

### El empujón final

Los últimos 10-20 bytes son los más difíciles. Reestructuración: reordena el código para que los fall-throughs eliminen instrucciones JR. Fusiona los bucles de sonido y visual. Incrusta bytes de datos en el flujo de instrucciones -- si necesitas $07 como datos y también necesitas un `RLCA` (código de operación (opcode) $07), arregla que uno sirva como ambos.

Miras fijamente el volcado hexadecimal. Pruebas mover la rutina de sonido antes de la rutina visual. Pruebas reemplazar la tabla de seno con un generador en tiempo de ejecución. Cada intento reordena los bytes. A veces todo se alinea.

La satisfacción de encajar una experiencia audiovisual coherente en 256 bytes -- de resolver el rompecabezas -- es real y específica y diferente a cualquier otra sensación en la programación.

---

## 13.6 El sizecoding como arte

Hay un momento en el sizecoding -- y el making-of de UriS lo captura perfectamente -- cuando el programa tiene 260 bytes y necesitas cortar 4. Podrías eliminar una característica visual. Podrías simplificar el sonido. O podrías encontrar una codificación donde los mismos bytes sirvan para ambos propósitos. Cuando encuentras esa codificación, no es solo una solución técnica. Es *elegante*. El código es más bello por ser más pequeño.

Por esto persisten las competiciones de sizecoding. La utilidad práctica de un programa de 256 bytes es cero. El oficio es lo que importa. La restricción es el lienzo. Los resultados -- binarios diminutos que producen música y movimiento desde un espacio más pequeño que este párrafo -- son arte genuino.

El artículo de LPRINT de diver4d hace un punto similar desde la dirección opuesta. El truco de LPRINT no es eficiente. Produce ruido visual que apenas califica como un "efecto." Pero cuando JtN y 4D lo usaron en BBB, enmarcando la técnica con intención artística, el resultado fue una demo que la gente recordó. La restricción se convirtió en el medio. Las limitaciones se convirtieron en el estilo.

El sizecoding te enseña cosas que mejoran toda tu programación. La disciplina de cuestionar cada byte agudiza la conciencia de codificación de instrucciones. El hábito de buscar superposiciones se transfiere a cualquier trabajo de optimización. La práctica de explotar el estado inicial y los efectos secundarios te hace un mejor programador de sistemas. Y la experiencia de resolución de rompecabezas -- encontrar la disposición donde todo encaja -- se aplica mucho más allá de 256 bytes.

---

## Resumen

- Las competiciones de **sizecoding** requieren programas completos en 256, 512, 1K, 4K u 8K bytes -- límites estrictos que demandan un enfoque fundamentalmente diferente de la programación.
- **NHBF** (UriS, CC 2025) demuestra la mentalidad de 256 bytes: cada byte cumple doble función, los estados de registro de una rutina alimentan la siguiente, la elección de instrucción está impulsada puramente por el tamaño de codificación.
- **El truco de LPRINT** (diver4d, 2015) redirige la salida de impresora de BASIC a la memoria de pantalla vía la dirección 23681, produciendo patrones visuales complejos en un puñado de bytes -- de cargadores de casetes piratas al arte demo.
- **A 512 bytes**, el código auto-modificable (SMC) se vuelve estructural (parcheando destinos de salto, incrustando contadores en operandos), y efectos como plasma, túnel y fuego se vuelven factibles junto con sonido.
- **El proceso de optimización** se mueve desde cambios estructurales (eliminar tablas, fusionar bucles) a elecciones de codificación (RST por CALL, JR por JP, XOR A por LD A,0) a descubrimientos fortuitos (estados de registro alineándose con necesidades de datos).
- **El truco del ORG** -- elegir tu dirección de carga para que los bytes de dirección sirvan como datos útiles -- representa el nivel más profundo del rompecabezas.

---

## Inténtalo tú mismo

1. **Empieza grande, reduce.** Escribe un plasma de atributos con un contador de fotograma. Hazlo funcionar a cualquier tamaño. Luego optimiza a 512 bytes, rastreando cada byte ahorrado y cómo.

2. **Explora LPRINT.** En BASIC, prueba `POKE 23681,64 : FOR i=1 TO 500 : LPRINT CHR$(RND*96+32); : NEXT i`. Observa cómo los datos transpuestos llenan la pantalla. Experimenta con diferentes rangos de caracteres.

3. **Mapea el estado de tus registros.** Escribe un programa pequeño y anota lo que contiene cada registro en cada punto. Busca lugares donde la salida de una rutina coincide con la entrada necesaria de otra.

4. **Estudia los vectores RST.** Desensambla la ROM del Spectrum en $0000, $0008, $0010, $0018, $0020, $0028, $0030, $0038. Estas son tus subrutinas "gratuitas."

5. **El desafío de 256 bytes.** Lleva la práctica de este capítulo a 256 bytes. Tendrás que tomar decisiones difíciles sobre qué conservar y qué eliminar. Esa es la cuestión.

---

*Siguiente: Capítulo 14 -- Compresión: Más datos en menos espacio. Pasamos de programas que caben en 256 bytes al problema de meter kilobytes de datos en kilobytes de almacenamiento, con el benchmark comprehensivo de Introspec de 10 compresores como nuestra guía.*

> **Fuentes:** UriS "NHBF Making-of" (Hype, 2025); diver4d "LPRINT Secrets" (Hype, 2015)
