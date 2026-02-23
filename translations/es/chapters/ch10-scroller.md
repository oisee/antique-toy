# Capítulo 10: El Dotfield Scroller y Color de 4 Fases

> *"Dos fotogramas normales y dos fotogramas invertidos. El ojo ve el promedio."*
> -- Introspec, Making of Eager (2015)

---

El ZX Spectrum muestra dos colores por celda de 8x8. El texto se desplaza por una pantalla a la velocidad que la CPU pueda manejar. Estas son restricciones fijas -- el hardware hace lo que hace, y ninguna cantidad de ingenio cambiará el silicio.

Pero el ingenio puede cambiar lo que el espectador *percibe*.

Este capítulo reúne dos técnicas de dos demos diferentes, separadas por casi veinte años pero conectadas por un principio compartido. El dotfield scroller de *Illusion* de X-Trade (ENLiGHT'96) renderiza texto como una nube rebotante de puntos individuales, cada uno colocado a un costo de solo 36 T-states. La animación de color de 4 fases de *Eager* de Introspec (3BM Open Air 2015) alterna cuatro fotogramas cuidadosamente construidos a 50Hz para engañar al ojo haciéndole ver colores que el hardware no puede producir. Uno explota la resolución espacial -- colocando puntos donde quieras, sin restricción de celdas de caracteres. El otro explota la resolución temporal -- ciclando fotogramas más rápido de lo que el ojo puede seguir. Juntos demuestran los dos ejes principales de hacer trampa en hardware con restricciones: espacio y tiempo.

---

## Parte 1: El Dotfield Scroller

### Lo Que Ve el Espectador

Imagina un mensaje -- "ILLUSION BY X-TRADE" -- renderizado no en caracteres de bloque sólidos sino como un campo de puntos individuales, cada punto un solo píxel. El texto se desliza horizontalmente por la pantalla en un desplazamiento suave. Pero los puntos no están sentados en líneas de escaneo planas. Rebotan. Todo el campo de puntos ondula en una onda sinusoidal, cada columna desplazada verticalmente de sus vecinas, creando la impresión de texto ondulando sobre la superficie del agua.

### La Fuente como Textura

La fuente se almacena como una textura de bitmap en memoria -- un bit por punto. Si el bit es 1, un punto aparece en pantalla. Si el bit es 0, nada sucede. La palabra crítica es *transparente*. En un renderizador normal, escribes cada posición de píxel. En el dotfield scroller, los píxeles transparentes son casi gratis. Verificas el bit, y si es cero, lo saltas. Solo los píxeles encendidos requieren una escritura a la memoria de video.

Esto significa que el costo de renderizado es proporcional al número de puntos visibles, no al área total. Un carácter típico de 8x8 podría tener 20 píxeles encendidos de 64. Para un mensaje de desplazamiento grande, esta economía importa enormemente. BC apunta a los datos de fuente; RLA desplaza cada bit a la bandera de acarreo para determinar encendido o apagado.

### Tablas de Direcciones Basadas en Pila

En un scroller convencional, la posición de pantalla de cada píxel se calcula a partir de coordenadas (x, y) usando la fórmula de dirección entrelazada del Spectrum. Ese cálculo involucra desplazamientos, máscaras y consultas. Hacerlo para miles de píxeles por fotograma consumiría todo el presupuesto.

La solución de Dark: precalcular cada dirección de pantalla y almacenarlas como una tabla que el puntero de pila recorre. POP lee 2 bytes y auto-incrementa SP, todo en 10 T-states. Apunta SP a la tabla en lugar de la pila real, y POP se convierte en la recuperación de direcciones más rápida posible -- sin registros de índice, sin aritmética de punteros, sin sobrecarga.

El movimiento de rebote está codificado enteramente en la tabla de direcciones. Cada entrada es una dirección de pantalla que ya incluye el desplazamiento vertical sinusoidal. El "rebote" no ocurre en tiempo de renderizado. Ocurrió cuando la tabla fue construida. Las tres dimensiones de la animación -- posición de desplazamiento, onda de rebote, forma del carácter -- colapsan en una sola secuencia lineal de direcciones de 16 bits, consumida a máxima velocidad por POP.

### El Bucle Interno

El análisis de Introspec de 2017 de Illusion revela el bucle interno. Un byte de datos de fuente contiene 8 bits -- 8 píxeles. `LD A,(BC)` lee el byte una vez, luego RLA desplaza un bit a la vez a través de 8 iteraciones desenrolladas:

```z80
; Dotfield scroller inner loop (unrolled for one font byte)
; BC = pointer to font/texture data, SP = pre-built address table

    ld   a,(bc)      ;  7 T  read font byte (once per 8 pixels)
    inc  bc          ;  6 T  advance to next font byte

    ; Pixel 7 (MSB)
    pop  hl          ; 10 T  get screen address from stack
    rla              ;  4 T  shift texture bit into carry
    jr   nc,.skip7   ; 12/7 T  skip if transparent
    set  7,(hl)      ; 15 T  plot the dot
.skip7:
    ; Pixel 6
    pop  hl          ; 10 T
    rla              ;  4 T
    jr   nc,.skip6   ; 12/7 T
    set  6,(hl)      ; 15 T
.skip6:
    ; ... pixels 5 through 0 follow the same pattern,
    ; with SET 5 through SET 0 ...
```

El costo por píxel, excluyendo la obtención amortizada del byte:

| Camino | Instrucciones | T-states |
|------|-------------|----------|
| Píxel opaco | `pop hl` + `rla` + `jr nc` (no tomado) + `set ?,(hl)` | **36** |
| Píxel transparente | `pop hl` + `rla` + `jr nc` (tomado) | **26** |

Los `LD A,(BC)` e `INC BC` cuestan 13 T-states amortizados sobre 8 píxeles -- alrededor de 1,6 T por píxel. Los "36 T-states por píxel" de Introspec son el costo del peor caso dentro del byte desenrollado, excluyendo esa sobrecarga.

La posición del bit SET cambia para cada píxel (7, 6, 5 ... 0), que es por qué el bucle se desenrolla 8 veces en lugar de repetirse. No puedes parametrizar la posición del bit en SET sin indexación IX/IY (demasiado lenta) o código auto-modificable (sobrecarga). Desenrollar es la solución limpia.

### La Aritmética del Presupuesto

El presupuesto de fotograma del Pentagon es 71.680 T-states. Asumiendo que el 60-70% está disponible para el scroller (el resto va a música, limpieza de pantalla, configuración de tabla), eso son aproximadamente 45.000 T-states.

Considera 4.096 puntos (8 caracteres de texto de 8x8). Una fuente típica está aproximadamente un 30% llena: 1.200 puntos opacos a 36 T cada uno, 2.900 transparentes a 26 T cada uno. Total: 43.200 + 75.400 + 6.656 (sobrecarga de obtención de bytes) = aproximadamente 125.000 T-states. Eso es alrededor de 1,75 fotogramas -- el scroller se actualiza a aproximadamente 28 fps, cómodamente suave.

Los números funcionan porque dos optimizaciones se combinan. El direccionamiento basado en pila elimina todo cálculo de coordenadas. La transparencia basada en textura elimina todas las escrituras para píxeles vacíos.

### Cómo Se Codifica el Rebote

La tabla de direcciones es donde vive el arte. Para crear el movimiento de rebote, una tabla de senos desplaza la posición vertical de cada columna:

```
y_offset = sin_table[(column * 8 + scroll_pos * 2) & 255]
```

La multiplicación por 8 controla la frecuencia espacial; el factor de 2 en la posición de desplazamiento controla la velocidad de fase. Dada la (x, y + y_offset) de cada punto, la dirección de pantalla del Spectrum se calcula y se almacena en la tabla. El código de construcción de tabla se ejecuta una vez por fotograma, fuera del bucle interno. El bucle interno solo ve un flujo de direcciones precalculadas.

---

## Parte 2: Animación de Color de 4 Fases

### El Problema del Color

Cada celda de 8x8 tiene un color de tinta (0-7) y un color de papel (0-7). Dentro de un solo fotograma, obtienes exactamente dos colores por celda. Pero el Spectrum funciona a 50 fotogramas por segundo, y el ojo humano no ve fotogramas individuales a esa tasa. Ve el promedio.

### El Truco

La técnica de 4 fases de Introspec cicla a través de cuatro fotogramas:

1. **Normal A:** tinta = C1, papel = C2. Datos de píxeles = patrón A.
2. **Normal B:** tinta = C3, papel = C4. Datos de píxeles = patrón B.
3. **Invertido A:** tinta = C2, papel = C1. Datos de píxeles = patrón A (mismos píxeles, colores intercambiados).
4. **Invertido B:** tinta = C4, papel = C3. Datos de píxeles = patrón B (mismos píxeles, colores intercambiados).

A 50Hz, cada fotograma se muestra durante 20 milisegundos. El ciclo de cuatro fotogramas se completa en 80ms -- 12,5 ciclos por segundo, por encima del umbral de fusión de parpadeo en pantallas CRT.

### Las Matemáticas de la Percepción

Traza un solo píxel que está "encendido" en el patrón A y "apagado" en el patrón B:

| Fotograma | Estado del píxel | Color mostrado |
|-------|-------------|-----------------|
| Normal A | encendido (tinta) | C1 |
| Normal B | apagado (papel) | C4 |
| Invertido A | encendido (tinta) | C2 |
| Invertido B | apagado (papel) | C3 |

El ojo percibe el promedio: (C1 + C2 + C3 + C4) / 4.

Ahora verifica: un píxel "encendido" en ambos patrones ve C1, C3, C2, C4. Un píxel "apagado" en ambos ve C2, C4, C1, C3. Todos los casos producen el mismo promedio. El patrón de píxeles no afecta el tono percibido -- solo la elección de C1 a C4 lo hace.

¿Entonces por qué tener dos patrones? Porque las transiciones *intermedias* importan. Un píxel que alterna entre rojo brillante y verde brillante parpadea notablemente a 12,5Hz. Un píxel alternando entre tonos similares apenas parpadea. Los patrones de dithering -- tableros de ajedrez, rejillas de medio tono, matrices ordenadas -- controlan la *textura* del parpadeo. Introspec eligió patrones de modo que las transiciones entre fotogramas produjeran mínima oscilación visible. Esta es la selección de píxeles anti-conflicto: la disposición cuidadosa de bits "encendidos" y "apagados" para asegurar que ningún píxel alterne entre colores dramáticamente diferentes en fotogramas consecutivos.

### Por Qué la Inversión Es Esencial

Sin el paso de inversión, los píxeles "encendidos" siempre mostrarían tinta y los píxeles "apagados" siempre mostrarían papel. Obtendrías exactamente dos colores visibles por celda, parpadeando entre dos pares diferentes. La inversión asegura que tanto tinta como papel contribuyen a ambos estados de píxel a lo largo del ciclo, mezclando los cuatro colores en la salida percibida.

En el Spectrum, la inversión es barata -- intercambia los bits de tinta y papel en el byte de atributo, o precalcula ambos búferes normal e invertido y cicla entre ellos.

### Costo Práctico

Cuatro búferes de atributos pre-construidos, ciclados una vez por fotograma. El costo por fotograma es una copia de bloque de 768 bytes en la RAM de atributos: aproximadamente 16.000 T-states via LDIR, o alrededor de 4.500 T-states via trucos PUSH. Menos de un cuarto del presupuesto de fotograma de cualquier manera.

Memoria: 4 x 768 = 3.072 bytes para los búferes. Los patrones de píxeles (A y B) se escriben una vez en la inicialización y nunca se tocan de nuevo.

### Superposición de Texto

En Eager, texto desplazable se superpone sobre la animación de color. El enfoque más simple reserva ciertas celdas para texto, excluyéndolas del ciclo de color -- atributos fijos blanco sobre negro con glifos de fuente reales. Un enfoque más sofisticado integra el texto en la animación de fases: las formas de los glifos anulan bits específicos en los patrones A y B, asegurando que el texto sea visible en cada fotograma mientras los píxeles circundantes aún ciclan. Esto produce texto que parece flotar sobre el fondo animado, con sangrado de color hasta los bordes de cada forma de letra.

---

## El Principio Compartido: Engaño Temporal

El dotfield scroller usa 50 fotogramas por segundo para flexibilidad *espacial*. Cada fotograma es una instantánea de posiciones de puntos en un instante; el cerebro del espectador interpola entre instantáneas para percibir movimiento suave. El trabajo de la CPU es *colocar* puntos lo más rápido posible, leyendo direcciones precalculadas de la pila.

La animación de color de 4 fases usa 50 fotogramas por segundo para flexibilidad de *color*. Cada fotograma muestra uno de cuatro estados de color; la retina del espectador los promedia. Ningún fotograma individual contiene el resultado percibido -- solo existe en la persistencia de visión.

Ambos explotan la misma realidad física: el CRT se refresca a 50Hz, y el sistema visual humano no puede resolver fotogramas individuales a esa tasa. La resolución *temporal* del Spectrum es mucho más rica que su resolución espacial o de color. Los programadores de la demoscene descubrieron que la resolución temporal es el eje más barato para explotar.

Ambos reducen sus bucles internos al mínimo absoluto. El scroller a 36 T-states por punto. La animación de color a una sola copia de búfer por fotograma. Ambos mueven la complejidad fuera del bucle interno hacia la precalculación. Y ambos producen resultados que parecen, para el espectador casual, como si el hardware no debería ser capaz de ellos.

Esto es lo que hace de la demoscene una forma de arte temporal. Una captura de pantalla de un dotfield scroller muestra una dispersión de píxeles. Una captura de pantalla de una animación de color de 4 fases muestra dos colores por celda, exactamente como el hardware especifica. Tienes que verlos *moverse* para verlos funcionar. La belleza está en la secuencia, no en el fotograma.

---

## Práctico 1: Un Scroller de Texto Dot-Matrix Rebotante

Construye un dotfield scroller simplificado: un mensaje de texto corto renderizado como un campo de puntos-matriz rebotante usando direccionamiento basado en POP.

**Estructuras de datos.** Una fuente de bitmap 8x8 alineada a página (la fuente ROM en `$3D00` funciona). Una tabla de senos de 256 bytes para el desplazamiento de rebote. Un búfer RAM para la tabla de direcciones (hasta 4.096 x 2 bytes).

**Construcción de tabla.** Antes de cada fotograma, iterar a través de los caracteres visibles. Para cada bit en cada byte de fuente, calcular la dirección de pantalla incorporando el desplazamiento de rebote sinusoidal, y almacenarlo en la tabla de direcciones. Esto se ejecuta una vez por fotograma fuera del bucle interno.

**Renderizado.** Deshabilitar interrupciones. Guardar SP via código auto-modificable. Apuntar SP a la tabla de direcciones. Ejecutar el bucle interno desenrollado: `ld a,(bc) : inc bc`, luego 8 repeticiones de `pop hl : rla : jr nc,skip : set N,(hl)` con N de 7 a 0. Restaurar SP. Habilitar interrupciones.

**Bucle principal.** `halt` (sincronizar a 50Hz), limpiar la pantalla (limpieza basada en PUSH del Capítulo 3), construir la tabla de direcciones, renderizar el dotfield, avanzar posición de desplazamiento y fase de rebote.

**Extensiones.** Limpieza parcial de pantalla (rastrear el rectángulo delimitador). Doble búfer via pantalla sombra en 128K. Múltiples armónicos de rebote. Densidad variable de puntos para un aspecto más disperso y etéreo.

---

## Práctico 2: Una Animación de Ciclado de Color de 4 Fases

Construye una animación de color de 4 fases produciendo gradientes suaves.

**Patrones de píxeles.** Llena la memoria de bitmap con dos patrones de dithering complementarios. Lo más simple: líneas de píxeles pares obtienen `$55` (01010101), líneas impares obtienen `$AA` (10101010). Para calidad de producción, usa una matriz Bayer 4x4 ordenada.

**Búferes de atributos.** Precalcula cuatro búferes de 768 bytes. Los búferes 0 y 1 contienen atributos normales con dos esquemas de color diferentes (variando tinta/papel a través de la pantalla para un gradiente diagonal). Los búferes 2 y 3 son las versiones invertidas -- bits de tinta y papel intercambiados. El intercambio es una rotación de bits: tres RRCAs para mover bits de tinta a posición de papel, tres RLCAs en la otra dirección, enmascarar y combinar.

**Bucle principal.** Cada fotograma: `halt`, indexar en una tabla de 4 entradas de punteros de búfer usando un contador de fase (AND 3), LDIR 768 bytes a `$5800`, incrementar el contador de fase. Ese es todo el motor en tiempo de ejecución -- alrededor de 16.000 T-states por fotograma.

**Animación.** Para un gradiente en movimiento, regenerar un búfer por fotograma (el que está a punto de convertirse en el más antiguo del ciclo de 4 fotogramas) con un desplazamiento de color avanzando. Esto mantiene un pipeline: mostrar fotograma N mientras generas fotograma N+4. Alternativamente, precalcular todos los búferes a través de bancos de 128K para cero costo en tiempo de ejecución.

---

## Resumen

- El **dotfield scroller** renderiza texto como puntos individuales. El bucle interno -- `pop hl : rla : jr nc,skip : set ?,(hl)` -- cuesta 36 T-states por píxel opaco, 26 por píxel transparente.
- El **direccionamiento basado en pila** codifica la trayectoria de rebote como direcciones de pantalla preconstruidas. POP las recupera a 10 T-states cada una -- la lectura de acceso aleatorio más rápida en el Z80.
- El **color de 4 fases** cicla 4 fotogramas de atributos (2 normales + 2 invertidos) a 50Hz. La persistencia de visión promedia los colores, creando la ilusión de más de 2 colores por celda.
- El **paso de inversión** asegura que los cuatro colores contribuyan a cada posición de píxel.
- Ambas técnicas explotan la **resolución temporal** para crear efectos imposibles en cualquier fotograma individual.
- El scroller usa la pila para flexibilidad espacial; la animación de color usa alternancia de fotogramas para flexibilidad de color -- los dos ejes principales del engaño en la demoscene.

---

## Inténtalo Tú Mismo

1. Construye el dotfield scroller. Empieza con un solo carácter estático trazado via el bucle interno basado en POP. Verifica la temporización esperada con la arnés de borde del Capítulo 1. Luego agrega la tabla de rebote y observa cómo ondula.

2. Experimenta con los parámetros de rebote. Cambia la amplitud del seno, la frecuencia espacial y la velocidad de fase. Pequeños cambios producen diferencias visuales dramáticas.

3. Construye la animación de color de 4 fases. Empieza con color uniforme (todas las celdas iguales en cada fase). Verifica que ves un color estable que no es ni la tinta ni el papel de ningún fotograma individual. Luego agrega el gradiente diagonal.

4. Prueba diferentes patrones de dithering. Tablero de ajedrez, bloques 2x2, matriz Bayer, ruido aleatorio. ¿Cuáles minimizan el parpadeo visible? ¿Cuáles producen los gradientes percibidos más suaves?

5. Combina ambas técnicas: fondo de color de 4 fases con un dotfield scroller monocromático encima.

---

> **Fuentes:** Introspec, "Technical Analysis of Illusion by X-Trade" (Hype, 2017); Introspec, "Making of Eager" (Hype, 2015); Dark, "Programming Algorithms" (Spectrum Expert #01, 1997). El desensamblado del bucle interno y conteos de ciclos siguen el análisis de Introspec de 2017. La técnica de color de 4 fases se describe en el artículo making-of de Eager y el file_id.diz de la versión de party.
