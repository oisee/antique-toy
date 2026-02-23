# Capítulo 6: La Esfera --- Mapeo de Texturas a 3,5 MHz

> *"Los efectos de coder siempre tratan de evolucionar un esquema de cómputo."*
> --- Introspec, 2017

---

Es 1996, y una demo llamada *Illusion* obtiene el primer lugar en ENLiGHT'96 en San Petersburgo. La audiencia observa cómo una imagen monocromática se envuelve alrededor de una esfera giratoria, rotando suavemente en tiempo real, en un ZX Spectrum funcionando a 3,5 MHz sin ninguna aceleración por hardware. Sin blitter. Sin GPU. Sin coprocesador. Solo un Z80, 48 kilobytes de RAM contigua, y lo que un programador de veinte años llamado Dark pudiera exprimir de ellos.

Veinte años después, en marzo de 2017, Introspec se sienta con una copia del binario y un desensamblador. Descompone el bucle de renderizado instrucción por instrucción, cuenta T-states, mapea direcciones de memoria a estructuras de datos, y publica sus hallazgos en Hype. Lo que sigue es uno de los análisis públicos más detallados de un efecto de demoscene jamás escritos para el ZX Spectrum --- y, en el hilo de comentarios que erupciona debajo, un debate sobre qué es lo que realmente importa en el renderizado en tiempo real en hardware con recursos limitados.

Este capítulo sigue el análisis de Introspec. Miraremos por encima de su hombro mientras traza el código, entenderemos *por qué* la esfera funciona como lo hace, y luego construiremos una versión simplificada nosotros mismos.

---

## El Problema: Un Objeto Redondo en una Pantalla Cuadrada

Una esfera en pantalla no es una esfera. Es un círculo relleno con una imagen distorsionada. La distorsión sigue las reglas de la proyección esférica: los píxeles cerca del ecuador están espaciados uniformemente, los píxeles cerca de los polos están comprimidos horizontalmente, y todo el mapeo se curva para crear la ilusión de una superficie tridimensional.

La imagen fuente en Illusion está almacenada como un mapa de bits monocromático --- un byte por píxel, donde cada byte es 0 o 1. Esto es extravagante para los estándares del Spectrum, donde la memoria de pantalla empaqueta ocho píxeles por byte, pero compra algo esencial: el código de renderizado puede tratar los píxeles como valores aritméticos en lugar de posiciones de bits.

La tarea, entonces, es esta: leer píxeles de la imagen fuente, muestrearlos de acuerdo con una proyección esférica, empaquetar ocho de ellos en un solo byte de pantalla, y escribir ese byte en la memoria de video. Hacer esto para cada byte visible de la esfera. Hacerlo lo suficientemente rápido para animar. Hacerlo en un Z80 a 3,5 MHz.

## La Clave: Código Que Escribe Código

La primera pregunta que cualquier programador de Z80 hace es: ¿cómo es el bucle interno? En una máquina donde un solo `NOP` toma 4 T-states y tienes aproximadamente 70.000 T-states por fotograma, el bucle interno *es* el programa. Todo lo demás --- configuración, generación de tablas, gestión de fotogramas --- es sobrecarga que ocurre una vez o con poca frecuencia. El bucle interno se ejecuta miles de veces por fotograma.

La solución de Dark es no tener un bucle interno fijo en absoluto.

En su lugar, el código de renderizado se *genera en tiempo de ejecución*. Para cada línea horizontal de la esfera, el programa construye una secuencia de instrucciones Z80 adaptadas a la geometría de esa línea. El código generado lee píxeles fuente en orden, los acumula en bytes de pantalla mediante desplazamientos y sumas, y avanza a través de los datos fuente por distancias que varían con la curvatura de la esfera. Diferentes líneas de la esfera producen diferente código.

Esta es una técnica que aparece a lo largo de la demoscene: código auto-generado, a veces llamado "sprites compilados" cuando se aplica al renderizado de sprites, o "generación de bucles desenrollados" en el caso general. Lo que hace distintiva la versión de la esfera es la variabilidad. Un sprite compilado es fijo --- una vez generado, dibuja la misma forma cada vez. El código de la esfera cambia con el ángulo de rotación, porque diferentes píxeles fuente se vuelven visibles a medida que la esfera gira.

## Dentro del Desensamblado

Introspec trazó el motor de renderizado hasta un bloque de código generado y un conjunto de tablas de consulta comenzando en la dirección `$6944`. Las tablas codifican la geometría de la esfera como una serie de *distancias de salto*: para cada posición a lo largo de una línea de escaneo de la esfera, cuántos píxeles fuente deben saltarse antes de que el siguiente sea muestreado.

En el ecuador, las distancias de salto son aproximadamente uniformes --- la imagen fuente se mapea sobre la esfera con mínima distorsión. Cerca de los polos, la compresión horizontal de la proyección significa saltos más grandes entre píxeles muestreados. En la parte superior e inferior, solo unos pocos píxeles son visibles por línea, y los saltos pueden ser sustanciales.

El bucle interno generado tiene una estructura repetitiva. Para cada byte de pantalla (ocho píxeles empaquetados), ejecuta una secuencia como esta:

```z80
; --- Accumulating 8 source pixels into one screen byte ---
; HL points into the source image (one byte per pixel)
; A is the accumulator, building the screen byte bit by bit

    add  a,a          ; shift accumulator left (make room for next pixel)
    add  a,(hl)       ; add source pixel (0 or 1) into lowest bit
    inc  l            ; advance to next source pixel
    ; ... possibly more INC L instructions here,
    ; depending on how many pixels to skip

    add  a,a          ; shift again
    add  a,(hl)       ; sample next pixel
    inc  l
    inc  l            ; skip one extra pixel (sphere curvature)

    add  a,a
    add  a,(hl)
    inc  l

    ; ... six more times, for 8 pixels total ...
```

El detalle clave: entre cada `add a,(hl)`, el número de instrucciones `inc l` varía. Una posición de píxel podría necesitar un solo `inc l` (muestrear píxeles adyacentes). Otra podría necesitar tres o cuatro (saltar sobre regiones comprimidas de la proyección). Las tablas de consulta en `$6944` codifican exactamente cuántas instrucciones `inc l` insertar en cada posición.

Veamos más cuidadosamente qué sucede con un solo píxel:

```z80
    add  a,a          ;  4 T-states  (shift A left by 1)
    add  a,(hl)       ;  7 T-states  (add source pixel into bit 0)
    inc  l            ;  4 T-states  (advance source pointer)
```

Ese es el costo mínimo: 15 T-states para desplazar el acumulador y muestrear un píxel, más 4 T-states por cada byte fuente saltado. Después de ocho de tales secuencias, el acumulador contiene un byte de pantalla completo.

Observa que el puntero fuente se avanza usando `inc l` en lugar de `inc hl`. Esto es deliberado. `INC HL` toma 6 T-states; `INC L` toma 4. Al restringir los datos fuente a residir dentro de una sola página de 256 bytes (de modo que solo el byte bajo de la dirección cambia), Dark ahorra 2 T-states por avance. Cuando estás haciendo esto miles de veces por fotograma, esos 2 T-states se acumulan.

Hay una sutileza aquí que es fácil pasar por alto. La imagen fuente está almacenada como un byte por píxel, e `INC L` da la vuelta dentro de una página de 256 bytes. Esto significa que cada línea de escaneo de datos fuente debe caber dentro de 256 bytes, y el búfer fuente debe estar alineado a página. La restricción da forma a todo el diseño de memoria de la demo.

## Contando T-States

Introspec calculó el costo por byte de salida como:

**101 + 32x T-states**

donde *x* es el número promedio de instrucciones `INC L` extra por píxel más allá de la obligatoria. Verifiquemos esto.

El costo fijo por píxel es:

| Instrucción | T-states |
|-------------|----------|
| `add a,a`   | 4        |
| `add a,(hl)`| 7        |
| `inc l`     | 4        |
| **Subtotal** | **15**  |

Para 8 píxeles, el costo fijo es 8 x 15 = 120 T-states. Pero hay sobrecarga adicional por byte: el código debe escribir el byte completado en la memoria de pantalla y prepararse para el siguiente. Supongamos que la secuencia de salida se ve algo así:

```z80
    ld   (de),a       ;  7 T-states  (write screen byte)
    inc  e            ;  4 T-states  (advance screen pointer)
```

También puede haber configuración para el acumulador (un `xor a` o similar) al inicio de cada byte. Tomando la cifra medida por Introspec de 101 T-states como el costo base fijo por byte, la sobrecarga más allá del muestreo de píxeles en bruto representa aproximadamente 101 - 120 = ... lo que significa que la cifra base ya incluye las instrucciones de salida y parte del trabajo de píxeles está entrelazado de forma diferente a lo que sugiere el conteo ingenuo.

La forma más limpia de leer la fórmula: 101 T-states de sobrecarga fija (salida, gestión de punteros, cualquier configuración por byte), más 32 T-states por salto extra. El "32" viene de 8 píxeles por 4 T-states por `INC L` extra, lo que nos da x como el número promedio de saltos extra por posición de píxel en ese byte. Cuando la esfera está cerca del ecuador, x es pequeño --- la proyección es cercana a uniforme. Cerca de los polos, x es grande, y el renderizado se ralentiza. Pero los polos también tienen menos bytes para dibujar (la esfera es más estrecha allí), así que la carga de trabajo total se equilibra aproximadamente.

¿Es esto lo suficientemente rápido? El fotograma del Spectrum es aproximadamente 70.000 T-states (más en Pentagon: 71.680). Una esfera de 56 píxeles de diámetro ocupa aproximadamente 7 bytes de ancho en su parte más amplia. Sobre la altura completa, quizás 200--250 bytes necesitan ser renderizados. A 101 T-states por byte (ecuatorial, x cerca de cero), eso es aproximadamente 25.000 T-states --- cómodamente dentro del presupuesto de un solo fotograma, con espacio sobrante para la limpieza de pantalla, consultas a tablas, y toda la otra gestión. Incluso cerca de los polos donde x podría promediar 2--3, el costo por byte sube a 165--197 T-states, pero se necesitan dibujar menos bytes. La aritmética funciona. Cabe.

## El Paso de Generación de Código

Antes de que el bucle interno se ejecute, un *paso de generación de código* lo construye. Este paso lee las tablas de consulta en `$6944`, que codifican la geometría de la esfera para el ángulo de rotación actual, y emite instrucciones Z80 en un búfer:

1. Para cada línea de escaneo de la esfera, leer las distancias de salto de la tabla.
2. Emitir `add a,a` seguido de `add a,(hl)` para cada píxel.
3. Emitir el número apropiado de instrucciones `inc l` basado en la distancia de salto.
4. Después de cada 8 píxeles, emitir la instrucción de salida para escribir el byte acumulado en la memoria de pantalla.
5. Al final de cada línea de escaneo, emitir un retorno o salto al manejador de la siguiente línea.

El bloque de código generado se llama entonces directamente. La CPU ejecuta las instrucciones como si fueran una subrutina normal, pero fueron escritas momentos antes por el generador de código. Esto es código auto-modificable en el sentido más literal --- el programa genera el programa que dibuja la pantalla.

El paso de generación de código en sí no es gratuito, pero se ejecuta una vez por fotograma (o una vez por paso de rotación), mientras que el bucle interno generado se ejecuta cientos de veces. El costo amortizado es negligible.

## Lo Que Dark Sabía: Spectrum Expert y los Bloques de Construcción

Hay un detalle en esta historia que la transforma de una curiosidad técnica en un arco narrativo. Dark --- el programador detrás del efecto de esfera de Illusion --- es el mismo Dark que escribió los artículos de *Algoritmos de Programación* en Spectrum Expert #01, publicado en 1997.

Esos artículos cubren multiplicación (shift-and-add vs. consulta de tabla de cuadrados), división (restauración y logarítmica), generación de tablas de seno mediante aproximación parabólica, y dibujo de líneas Bresenham con bloques de matriz 8x8 optimizados. Son material tutorial, escrito para la comunidad de programación del ZX Spectrum, explicando técnicas fundamentales que cualquier programador de demos necesitaría.

Y son, con bastante precisión, los bloques de construcción usados en Illusion.

La esfera requiere: tablas de consulta trigonométricas para calcular la proyección (seno/coseno, la aproximación parabólica del artículo de Dark). Multiplicación de punto fijo para escalado. Diseño de memoria cuidadoso para velocidad (la misma disciplina de conteo de ciclos que Dark enseña a lo largo de los artículos). El enfoque de tablas de salto para codificar la geometría de la esfera es una aplicación directa del tipo de pensamiento orientado a precomputación que Dark defiende.

Dark publicó el libro de texto. Luego escribió la demo que demuestra cada técnica en él. Veinte años después, Introspec realizó ingeniería inversa de la demo y encontró exactamente los patrones que Dark había enseñado. Tenemos ambos lados de la historia: el profesor explicando sus métodos, y el analista confirmando que esos métodos son precisamente lo que contiene el producto terminado.

## El Debate en Hype: Bucles Internos vs. Matemáticas

El artículo de Introspec de 2017 en Hype generó un largo hilo de comentarios. Entre los intercambios más sustantivos hubo un debate entre kotsoft e Introspec sobre dónde reside el verdadero trabajo de un efecto como este.

kotsoft argumentó que el enfoque matemático de la proyección --- cómo se calcula qué píxel fuente se mapea a qué posición de pantalla --- es la decisión de diseño crítica. Calcula mal la proyección, o usa un algoritmo ingenuo, y ninguna cantidad de optimización del bucle interno te salvará. El modelo matemático determina si el efecto es siquiera *factible* en el hardware.

Introspec contrarrestó que el bucle interno es donde los T-states realmente se gastan. Puedes tener un hermoso modelo matemático, pero si el código de renderizado cuesta 200 T-states por byte en lugar de 100, has reducido a la mitad tu tasa de fotogramas. El enfoque matemático define *qué* calcular; el bucle interno determina *si puedes calcularlo a tiempo*.

Ambos tienen razón, y la tensión entre ellos ilumina algo fundamental sobre la programación de demoscene. Un efecto de demo no es matemática pura ni ingeniería pura. Es la intersección: un esquema de cómputo elegante (la proyección esférica codificada como tablas de salto) casado con una estrategia de ejecución eficiente (bucles desenrollados generados con avances `INC L`). Ninguno por sí solo es suficiente.

El resumen de Introspec lo captura: "los efectos de coder siempre tratan de evolucionar un esquema de cómputo." La palabra *evolucionar* es clave. No comienzas con un algoritmo de libro de texto y lo optimizas hasta que encaje. Evolucionas el algoritmo y la implementación juntos, cada uno restringiendo y habilitando al otro, hasta que encuentras una forma que funciona dentro del presupuesto del hardware.

## Práctico: Una Esfera Giratoria Simplificada de 56x56

Esbocemos cómo construirías una versión simplificada de este efecto. Apuntaremos a una esfera de 56x56 píxeles --- 7 bytes de ancho en el ecuador, 56 líneas de escaneo de alto. El objetivo no es reproducir el motor de renderizado completo de Illusion, sino entender la técnica central lo suficientemente bien como para implementarla.

### Paso 1: Precomputar la Geometría de la Esfera

Para cada línea de escaneo *y* (de -28 a +27, centrada en la esfera), calcula el arco visible:

```
radius_at_y = sqrt(R^2 - y^2)    ; where R = 28 (sphere radius in pixels)
```

Esto da el semi-ancho de la esfera en esa línea de escaneo. Para cada posición de píxel *x* dentro de ese arco, calcula la longitud y latitud correspondientes en la superficie de la esfera:

```
latitude  = arcsin(y / R)
longitude = arcsin(x / radius_at_y) + rotation_angle
```

Estos dan las coordenadas (u, v) en la textura fuente para cada píxel de pantalla.

### Paso 2: Construir Tablas de Salto

En lugar de almacenar pares completos (u, v) para cada píxel (prohibitivamente costoso en memoria), calcula la *diferencia en posición fuente* entre píxeles de pantalla adyacentes. Para cada línea de escaneo, necesitas una lista de valores de salto: cuántos píxeles fuente avanzar entre muestras consecutivas de pantalla.

Cerca del ecuador, píxeles de pantalla consecutivos se mapean a píxeles fuente casi adyacentes --- saltos de 1. Cerca de los polos, la proyección comprime, y saltas más píxeles fuente --- saltos de 2, 3, o más.

Almacena estos como una tabla. Para nuestra esfera de 56x56, necesitas como máximo 56 entradas por línea (la línea más ancha), por 56 líneas, por un byte por entrada. Eso es como máximo 3.136 bytes para un solo ángulo de rotación --- pero en la práctica, puedes explotar la simetría vertical (la mitad superior refleja la mitad inferior) y almacenar solo la mitad de la tabla.

Para la animación, necesitas tablas de salto para múltiples ángulos de rotación. Con 32 pasos de rotación, podrías ajustar las tablas en 32 x 1.568 = aproximadamente 49KB. Eso desborda la memoria disponible, así que en la práctica usarías menos pasos de rotación, resolución angular más gruesa, o regenerar tablas sobre la marcha desde una representación compacta.

### Paso 3: Generar el Código de Renderizado

Para cada fotograma, lee la tabla de saltos para el ángulo de rotación actual y genera código Z80:

```z80
; Code generator pseudocode (in Z80 assembly, this would be
; a loop that writes opcodes into a buffer)

generate_sphere_code:
    ld   iy,skip_table        ; pointer to skip distances
    ld   ix,code_buffer       ; pointer to output code buffer

.line_loop:
    ; For each scan line...
    ld   b,bytes_this_line    ; number of output bytes (e.g. 7 at equator)

.byte_loop:
    ; For each output byte, emit code for 8 pixels:
    ld   c,8                  ; 8 pixels per byte

.pixel_loop:
    ; Emit: ADD A,A
    ld   (ix+0),$87           ; opcode for ADD A,A
    inc  ix

    ; Emit: ADD A,(HL)
    ld   (ix+0),$86           ; opcode for ADD A,(HL)
    inc  ix

    ; Emit INC L instructions based on skip distance
    ld   a,(iy+0)             ; read skip distance
    inc  iy

.emit_inc_l:
    or   a
    jr   z,.pixel_done
    ld   (ix+0),$2C           ; opcode for INC L
    inc  ix
    dec  a
    jr   nz,.emit_inc_l

.pixel_done:
    dec  c
    jr   nz,.pixel_loop

    ; Emit: LD (DE),A  (write byte to screen)
    ld   (ix+0),$12           ; opcode for LD (DE),A
    inc  ix
    ; Emit: INC E
    ld   (ix+0),$1C           ; opcode for INC E
    inc  ix

    dec  b
    jr   nz,.byte_loop

    ; Emit line transition code here (advance DE to next screen line)
    ; ...

    jr   .line_loop
```

Esto está simplificado --- el código real de Illusion está más estrechamente integrado, y Dark probablemente usó un generador de código más compacto y eficiente. Pero el principio es el mismo: leer distancias de salto, emitir opcodes.

### Paso 4: Ejecutar y Mostrar

Una vez que el búfer de código está lleno, llámalo como una subrutina:

```z80
    ld   hl,source_image      ; source texture (page-aligned, 1 byte/pixel)
    ld   de,screen_address    ; start of sphere area in video memory
    call code_buffer          ; execute the generated rendering code
```

El código generado recorre toda la esfera, leyendo píxeles fuente, empaquetándolos en bytes de pantalla, y escribiéndolos en la memoria de video. Cuando retorna, la esfera está dibujada.

Para la animación, incrementa el ángulo de rotación, carga la tabla de saltos correspondiente (o regenerala), regenera el código, y renderiza de nuevo.

### Paso 5: Diseño de la Imagen Fuente

La textura fuente debe estar organizada para un acceso secuencial rápido. Dado que el código de renderizado usa `INC L` para avanzar a través de ella, la textura debe estar alineada a página (comenzar en una dirección donde el byte bajo es `$00`), y cada fila debe caber dentro de 256 bytes. Una textura de 256 píxeles de ancho almacenada como un byte por píxel cumple perfectamente esta restricción: cada fila ocupa una página.

Para el caso monocromático, cada píxel es `$00` o `$01`. Esto significa que `ADD A,(HL)` suma 0 (píxel apagado) o 1 (píxel encendido) al bit más bajo del acumulador, justo después de que `ADD A,A` ha desplazado todo hacia arriba. El resultado es un byte de pantalla empaquetado por bits donde cada bit corresponde a un píxel fuente muestreado.

---

## El Patrón General

La esfera en Illusion es una instancia específica de un patrón general de la demoscene que aparece a lo largo de este libro. El patrón tiene tres partes:

**Precomputación.** El trabajo matemático costoso --- proyección, trigonometría, transformaciones de coordenadas --- se hace una vez (o una vez por fotograma) y se almacena como tablas compactas. Las tablas codifican *qué* renderizar sin codificar *cómo*.

**Generación de código.** El código de renderizado en sí se genera a partir de las tablas. Esto elimina ramificaciones, contadores de bucle, y lógica condicional del bucle interno. Cada instrucción en el código generado hace trabajo útil. No hay sobrecarga por "averiguar qué hacer a continuación" --- esa decisión se tomó durante la generación.

**Acceso secuencial a memoria.** El bucle interno lee datos secuencialmente, avanzando un puntero con incrementos de un solo byte. Este es el patrón de acceso más rápido posible en el Z80, donde las cargas indirectas por registro (`LD A,(HL)`) son baratas y el direccionamiento indexado (`LD A,(IX+d)`) es costoso.

El rotozoomer en el próximo capítulo usa el mismo patrón. También lo hace el scroller de campo de puntos en el Capítulo 10. Y los túneles de atributos en el Capítulo 9. Los detalles específicos difieren --- diferentes tablas, diferente código generado, diferentes formatos de datos --- pero la arquitectura es la misma. Introspec reconoció esto cuando escribió que los efectos de coder tratan de "evolucionar un esquema de cómputo." La esfera, el rotozoomer, el túnel: todos están evolucionados del mismo enfoque fundamental. La evolución está en los detalles --- qué cómputo, qué diseño de tabla, qué bucle interno --- pero el esqueleto es compartido.

Dark entendió esto en 1996. Lo codificó en sus artículos de Spectrum Expert en 1997. Introspec lo confirmó por desensamblado en 2017. El patrón es tan válido ahora como lo era entonces, en cualquier plataforma donde los T-states son escasos y cada instrucción debe ganarse su lugar.

---

## Resumen

- El efecto de esfera en Illusion mapea una imagen fuente monocromática sobre una esfera giratoria usando código Z80 generado dinámicamente.
- Las tablas de consulta codifican la geometría de la esfera como distancias de salto de píxeles. El código de renderizado se genera a partir de estas tablas en tiempo de ejecución.
- El bucle interno usa `ADD A,A` y `ADD A,(HL)` para acumular píxeles en bytes de pantalla, con números variables de instrucciones `INC L` para avanzar a través de los datos fuente.
- Rendimiento: 101 + 32x T-states por byte de salida, donde x depende de la posición.
- El enfoque ejemplifica un patrón general de la demoscene: precomputar la geometría, generar código, acceder a la memoria secuencialmente.
- Dark escribió los algoritmos de bloques de construcción en Spectrum Expert (1997) y los aplicó en Illusion (1996). Introspec realizó ingeniería inversa del resultado veinte años después, confirmando las técnicas.

---

> **Fuentes:** Introspec, "Technical Analysis of Illusion by X-Trade" (Hype, 2017); Dark, "Programming Algorithms" (Spectrum Expert #01, 1997). El hilo de comentarios en Hype incluye contribuciones de kotsoft, Raider, y otros.
