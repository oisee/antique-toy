# Capítulo 15: Anatomía de dos máquinas

> "El diseño caracteriza la integridad realizacional, estilística e ideológica."
> -- Introspec (spke), "For Design" (Hype 2015)

Bienvenido a la Parte V. Estamos construyendo un juego.

Las Partes I a IV te dieron el kit de herramientas del demoscener: conteo de ciclos, trucos de pantalla, optimización de bucles internos, arquitectura de sonido, compresión. Un juego plantea demandas diferentes. Necesitas el mapa de memoria completo, no solo la región de pantalla. Necesitas entender la conmutación de bancos, porque tus niveles, música y datos de sprites no cabrán en un bloque contiguo. Necesitas saber cómo los dos procesadores del Agon Light 2 se comunican entre sí, porque tu bucle de juego se extiende a través de esa frontera.

Este capítulo es la referencia de hardware para todo lo que sigue. Donde el Capítulo 1 te dio el presupuesto de fotograma y el Capítulo 2 te dio el diseño de pantalla, este capítulo te da todo lo demás. Tenlo marcado.

---

## 15.1 ZX Spectrum 128K: Mapa de memoria

El Spectrum 48K original tenía un modelo de memoria simple: 16 KB de ROM en `$0000`-`$3FFF`, 48 KB de RAM en `$4000`-`$FFFF`. El modelo 128K mantiene este diseño visible para la CPU pero esconde un sistema de conmutación de bancos debajo.

El 128K tiene ocho páginas de 16 KB de RAM (páginas 0-7, totalizando 128 KB) y dos ROMs de 16 KB (ROM 0: editor 128K, ROM 1: BASIC 48K). En cualquier momento, el Z80 ve un espacio de direcciones de 64 KB dividido en cuatro ranuras de 16 KB:

| Rango de direcciones | Contenido | Notas |
|---------------|----------|-------|
| `$0000`-`$3FFF` | ROM (0 o 1) | Seleccionada por el bit 4 de `$7FFD` |
| `$4000`-`$7FFF` | Página de RAM 5 | **Siempre** página 5. La memoria de pantalla vive aquí. |
| `$8000`-`$BFFF` | Página de RAM 2 | **Siempre** página 2. |
| `$C000`-`$FFFF` | Página de RAM N | Conmutable: cualquier página 0-7 vía `$7FFD` |

Las páginas 5 y 2 están cableadas en sus ranuras. No puedes intercambiarlas. Esto significa que la pantalla (`$4000`-`$57FF`) siempre es accesible, y tu código principal (típicamente con ORG en `$8000`) se sitúa en la página 2 donde no desaparecerá cuando cambies bancos.

La ranura superior de 16 KB en `$C000`-`$FFFF` es la flexible. Escribe en el puerto `$7FFD` y la página mapeada allí cambia.

### El puerto $7FFD: Conmutación de bancos

El puerto `$7FFD` controla la configuración de memoria en el 128K. Es de solo escritura -- no puedes leerlo de vuelta. Esto significa que debes guardar su valor como sombra en una variable de RAM si necesitas conocer el estado actual.

```
Port $7FFD bit layout:
  Bit 0-2:  RAM page mapped at $C000 (0-7)
  Bit 3:    Screen select (0 = normal screen at page 5,
                           1 = shadow screen at page 7)
  Bit 4:    ROM select (0 = 128K ROM, 1 = 48K BASIC ROM)
  Bit 5:    Disable paging (set this and banking is locked
            until next reset -- used by 48K BASIC)
  Bits 6-7: Unused
```

Una rutina típica de cambio de banco:

```z80
; Switch RAM page at $C000 to page number in A (0-7)
; Preserves other $7FFD bits from shadow variable
bank_switch:
    ld   b, a                 ; 4T   save desired page
    ld   a, (bank_shadow)     ; 13T  load current $7FFD state
    and  %11111000            ; 7T   clear page bits (0-2)
    or   b                    ; 4T   insert new page number
    ld   (bank_shadow), a     ; 13T  update shadow
    ld   bc, $7FFD            ; 10T
    out  (c), a               ; 12T  do the switch
    ret                       ; 10T
                              ; --- 73T total
```

Esos 73 T-states no son gratuitos, pero son insignificantes comparados con un presupuesto de fotograma de 70.000+. El coste real de la conmutación de bancos es arquitectónico, no temporal: debes diseñar la disposición de tus datos para que nunca necesites acceder a dos páginas de bancos diferentes simultáneamente. Datos de música en la página 4, datos de nivel en la página 3, gráficos de sprites en la página 6 -- pero tu reproductor de música y tu renderizador no pueden estar ambos ejecutándose desde `$C000` al mismo tiempo.

**La pantalla sombra.** El bit 3 de `$7FFD` selecciona qué página de RAM lee la ULA para la visualización: página 5 (normal) o página 7 (sombra). Esto te da doble búfer por hardware -- dibuja en la pantalla sombra mientras la ULA muestra la normal, luego voltea alternando el bit 3. Usaremos esto intensamente en el Capítulo 17 (Desplazamiento) y el Capítulo 21 (Juego completo).

### Un mapa de memoria práctico para un juego de 128K

Así es como un juego real podría distribuir sus 128 KB a través de las ocho páginas:

| Página | Ranura | Uso |
|------|------|-------|
| 0 | `$C000` (con banco) | Datos de nivel (mapas, definiciones de baldosas) |
| 1 | `$C000` (con banco) | Conjunto de gráficos de sprites 1 |
| 2 | `$8000`-`$BFFF` (fija) | Código principal del juego, sistema de entidades, manejador de interrupciones |
| 3 | `$C000` (con banco) | Conjunto de gráficos de sprites 2, tablas de consulta |
| 4 | `$C000` (con banco) | Datos de música (patrones .pt3, instrumentos) |
| 5 | `$4000`-`$7FFF` (fija) | Pantalla primaria, memoria de atributos, vars del sistema |
| 6 | `$C000` (con banco) | Efectos de sonido, datos adicionales de nivel |
| 7 | `$C000` (con banco) | Pantalla sombra (objetivo de doble búfer) |

Observa: la página 7 cumple doble función. La ULA puede mostrarla como la pantalla sombra, pero también puedes ponerla en el banco de `$C000` y usarla como una página de datos de 16 KB cuando no estás usando doble búfer. Muchas demos explotan esto.

La restricción crítica: **tu manejador de interrupciones y bucle principal deben vivir en las páginas 2 o 5**, porque son las únicas páginas garantizadas de estar mapeadas en todo momento. Si una interrupción se dispara mientras la página 4 está en el banco de `$C000`, y tu manejador de interrupciones vive en `$C000`, la CPU salta a tus datos de música en lugar de tu código. El resultado es un cuelgue, generalmente espectacular.

**Regla:** nunca pongas código crítico en tiempo en una página con banco a menos que estés absolutamente seguro de qué página está activa cuando ese código se ejecuta.

![ZX Spectrum 128K memory map](illustrations/output/ch15_memory_map.png)

---

## 15.2 Memoria contendida: La verdad práctica

En el Capítulo 1, establecimos que los clones Pentagon no tienen memoria contendida y que los conteos de ciclos son fiables en todas partes. Eso es cierto, y el Pentagon sigue siendo el estándar para el trabajo de demos con conteo de ciclos. Pero si estás escribiendo un juego para publicación, tus jugadores incluirán personas ejecutando hardware Sinclair original, modelos Amstrad +2A/+3, y clones FPGA modernos que emulan la temporización original. Necesitas saber qué hace la memoria contendida y cómo evitar sus peores efectos.

Introspec cubrió esto exhaustivamente en sus artículos "GO WEST" en Hype (2015). Aquí está el resumen práctico.

### Qué se contiene

En las máquinas Sinclair originales, la ULA y la CPU comparten un bus de memoria. Cuando la ULA está leyendo datos de pantalla para pintar la visualización (durante las 192 líneas de escaneo activas), cualquier acceso de CPU a ciertas páginas de RAM se retrasa. La CPU se detiene literalmente por T-states extra mientras la ULA termina su lectura.

Las páginas contendidas difieren entre modelos:

| Modelo | Páginas contendidas | Siempre rápidas |
|-------|----------------|-------------|
| 48K | Toda la RAM (`$4000`-`$FFFF`) | Ninguna (pero `$8000`+ es menos contendida en la práctica) |
| 128K / +2 | Páginas 1, 3, 5, 7 | Páginas 0, 2, 4, 6 |
| +2A / +2B / +3 | Páginas 4, 5, 6, 7 | Páginas 0, 1, 2, 3 |

El 48K es el peor caso -- toda la RAM está contendida. En el 128K, el patrón es cada página impar. En el +2A/+3, se invierte: las páginas altas están contendidas.

Esto tiene consecuencias prácticas inmediatas. En un 128K, tu código principal en `$8000` (página 2) está en memoria no contendida -- rápido. La pantalla en `$4000` (página 5) está contendida -- las escrituras a la memoria de pantalla son más lentas durante la visualización activa. Y la página 7 (la pantalla sombra) también está contendida, lo que significa que los rellenos de doble búfer a la pantalla sombra son más lentos de lo que podrías esperar en hardware original.

### ¿Cuánto más lento?

Introspec midió las penalizaciones reales:

- **Acceso aleatorio a byte en memoria contendida:** aproximadamente **0,92 T-states extra por byte** en promedio durante la visualización activa
- **Operaciones de pila (PUSH/POP) a memoria contendida:** aproximadamente **1,3 T-states extra por byte** en promedio
- **Durante el tiempo de borde:** **cero penalización** -- la contención solo ocurre mientras la ULA está pintando activamente líneas de escaneo

Esa cifra de 0,92 significa que un `LD A,(HL)` que debería costar 7 T-states costará, en promedio, unos 7,92 T-states cuando HL apunta a memoria contendida durante la visualización activa. Un PUSH que escribe dos bytes a memoria contendida a 11 T-states costará unos 13,6 T-states en su lugar.

Estos promedios ocultan una realidad desordenada: la penalización real depende de dónde en el ciclo de lectura de 8 T-states de la ULA cae tu acceso de CPU. El patrón se repite cada 8 T-states: penalizaciones de 6, 5, 4, 3, 2, 1, 0, 0 estados extra. Puedes caer en cualquier punto de este ciclo, y la penalización se acumula con cada acceso a memoria dentro de una instrucción. Esto hace que el conteo preciso de ciclos en máquinas contendidas sea genuinamente difícil.

### La respuesta práctica

Para desarrollo de juegos, no efectos de demo, el enfoque es directo:

1. **Pon tu código en memoria no contendida.** En el 128K, ORG en `$8000` (página 2) -- siempre rápido.
2. **Escribe en la pantalla durante el tiempo de borde cuando sea posible.** Los bordes superior e inferior te dan acceso libre de contención a la memoria de pantalla. También lo hace el borde izquierdo/derecho de cada línea de escaneo.
3. **No te preocupes por el modelado preciso de contención.** Presupuesta una ralentización del 15-20% para código que toque la memoria de pantalla durante la visualización activa, y diseña tu presupuesto de fotograma con ese margen. Esto no es trabajo de demo con conteo de ciclos; es desarrollo de juegos.
4. **Prueba en hardware real o emuladores precisos.** Fuse emula la contención correctamente. Unreal Speccy (modo Pentagon) no, por diseño. ZEsarUX puede emular múltiples modelos.

El consejo de Introspec de GO WEST se reduce a esto: **la memoria contendida es un problema de portabilidad, no un drama.** Si tu código funciona en Pentagon, casi seguro funcionará en hardware original también -- solo un poco más lento durante las escrituras de pantalla. Los lugares donde la contención realmente rompe cosas son los efectos de rasterizado con precisión de ciclo (multicolor, sincronización de bus flotante), y esas son técnicas de demo, no técnicas de juego.

---

## 15.3 Temporización de la ULA

La ULA genera la señal de vídeo y la interrupción de CPU. Entender su temporización es esencial para efectos de borde, música dirigida por interrupciones y sincronización de pantalla.

### Estructura del fotograma

Un fotograma completo consiste en líneas de escaneo. El ancho de línea de escaneo y el conteo total de líneas difieren entre modelos:

| Máquina | T-states/línea | Líneas de escaneo | T-states/fotograma |
|---------|--------------|-----------|----------------|
| ZX Spectrum 48K | 224 | 312 | 69.888 |
| ZX Spectrum 128K | 228 | 311 | 70.908 |
| Pentagon 128 | 224 | 320 | 71.680 |

Nota la línea de escaneo más ancha del 128K (228 vs 224 T-states). Los 4 T-states extra por línea están en la porción de borde/sincronización, no en la visualización activa.

### Mapas de tactos: Regiones del fotograma

El fotograma se divide en tres regiones. La interrupción se dispara al inicio del borrado vertical, antes del borde superior. Aquí está el mapa de temporización para cada modelo:

**Pentagon 128 (71.680 T-states)**

```
Interrupt ──┐
            │
Top border  │  80 lines × 224T = 17,920T   No screen reads. No contention.
            │
Active      │ 192 lines × 224T = 43,008T   ULA reads screen memory.
display     │                                No contention on Pentagon.
            │
Bottom      │  48 lines × 224T = 10,752T   No screen reads. No contention.
border      │
────────────┘  Total: 71,680T
```

**ZX Spectrum 128K (70.908 T-states)**

```
Interrupt ──┐
            │
Top border  │  63 lines × 228T = 14,364T   No screen reads. No contention.
            │
Active      │ 192 lines × 228T = 43,776T   ULA reads screen memory.
display     │                                Contention on pages 1,3,5,7.
            │
Bottom      │  56 lines × 228T = 12,768T   No screen reads. No contention.
border      │
────────────┘  Total: 70,908T
```

**ZX Spectrum 48K (69.888 T-states)**

```
Interrupt ──┐
            │
Top border  │  64 lines × 224T = 14,336T   No screen reads. No contention.
            │
Active      │ 192 lines × 224T = 43,008T   ULA reads screen memory.
display     │                                Contention on all RAM.
            │
Bottom      │  56 lines × 224T = 12,544T   No screen reads. No contention.
border      │
────────────┘  Total: 69,888T
```

Después de un `HALT`, tienes todo el período del borde superior -- 17.920 T-states en Pentagon, 14.364 en 128K -- para hacer trabajo antes de que el haz entre en el área de visualización activa y comience la contención. Por eso el código bien estructurado del Spectrum hace las escrituras de pantalla al inicio del fotograma: obtienes acceso libre de contención a la memoria de pantalla durante el período de borde.

### Temporización de línea de escaneo

Cada línea de escaneo se descompone en una porción activa (donde la ULA lee datos de pantalla) y porciones de borde/sincronización:

**48K y Pentagon (224 T-states por línea):**

```
128T  active pixel area (ULA reads screen data)
 24T  right border
 48T  horizontal sync + retrace
 24T  left border
```

**128K (228 T-states por línea):**

```
128T  active pixel area (ULA reads screen data)
 24T  right border
 52T  horizontal sync + retrace
 24T  left border
```

Durante los 128 T-states activos, el acceso a memoria en páginas contendidas se retrasa (en máquinas no-Pentagon). Durante los 96 T-states restantes (o 100 en 128K), sin contención. Incluso durante la visualización activa, aproximadamente la mitad de cada línea de escaneo está libre de contención.

### Presupuesto total vs práctico

Los totales de fotograma anteriores son el tiempo entre interrupciones. El presupuesto *práctico* -- T-states disponibles para tu código -- es menos:

| Sobrecarga | Coste |
|----------|------|
| HALT + reconocimiento de interrupción (IM1) | ~30 T-states |
| ISR mínima (EI + RET) | ~14 T-states |
| Reproductor típico de música PT3 (en ISR) | ~3.000--5.000 T-states |
| Mantenimiento del bucle principal (contador de fotograma, salto HALT) | ~20--50 T-states |

Presupuestos prácticos con un reproductor de música ejecutándose:

| Máquina | Total | Después del reproductor PT3 | Después de reproductor + margen de contención |
|---------|-------|-------------------|----------------------------------|
| Pentagon | 71.680 | ~66.000--68.000 | ~66.000--68.000 (sin contención) |
| 128K | 70.908 | ~65.000--67.000 | ~55.000--60.000 (escrituras de pantalla durante visualización activa) |
| 48K | 69.888 | ~64.000--66.000 | ~50.000--55.000 (toda la RAM contendida) |

Cuando este libro dice "presupuesto de fotograma de ~70.000 T-states," se refiere al total. Cuando planifiques tus bucles internos, presupuesta para la cifra práctica -- típicamente 65.000--68.000 en Pentagon con música.

---

## 15.4 Bus flotante, nieve de ULA y el bug de $7FFD

Estos son tres peculiaridades del hardware que aparecen en máquinas Sinclair originales pero no en la mayoría de los clones. Puede que nunca las encuentres en desarrollo de juegos, pero pueden causar bugs misteriosos si no sabes que existen.

### Bus flotante

En hardware Spectrum original, leer de un puerto no conectado devuelve cualquier dato que la ULA está poniendo en el bus de datos en ese momento. Durante la visualización activa, la ULA está leyendo memoria de pantalla, así que una lectura del puerto `$FF` devuelve el byte que la ULA está leyendo actualmente.

Los programadores de demos explotan esto para sincronización de haz: lee el bus flotante en un bucle cerrado hasta que veas un valor conocido de la memoria de pantalla, y sabes exactamente dónde está el haz. Este es el método de sincronización más barato -- no se requiere temporización de interrupción.

Los juegos raramente necesitan esto, pero ten cuidado: si tu código lee de un puerto que no existe en el hardware, el valor de retorno es impredecible y varía entre modelos. El bus flotante *no* se emula en Pentagon, Scorpion o ZX Next.

### El bug de lectura de $7FFD

El puerto `$7FFD` es de solo escritura. Pero en algunos modelos de Spectrum, leer del puerto `$7FFD` (incluso involuntariamente, a través de una instrucción que pone `$7FFD` en el bus de direcciones) causa que el valor del bus flotante se escriba en el puerto. Esto dispara un cambio de página espurio.

El peligro práctico: la instrucción Z80 `LD A,(nn)` pone la dirección `nn` en el bus durante la ejecución. Si `nn` resulta ser `$7FFD` y estás leyendo datos almacenados en la dirección `$7FFD`, la lectura de memoria puede disparar una escritura de puerto en hardware original. Este es un bug oscuro pero real. Evita almacenar datos en la dirección `$7FFD`.

### Nieve de ULA

Si el registro I del Z80 (usado como base de la tabla de vectores de interrupción IM2) se establece a un valor en el rango `$40`-`$7F`, el ciclo de refresco de DRAM durante cada lectura de opcode M1 pone una dirección en el rango `$4000`-`$7FFF` en el bus de direcciones. Esto conflictúa con las lecturas de pantalla de la ULA y produce "nieve" visual -- ruido aleatorio en la pantalla.

La solución es simple: **nunca establezcas I a un valor entre `$40` y `$7F`.** La configuración típica de IM2 usa `I = $FE` con una tabla de 257 bytes de vectores idénticos en `$FE00`-`$FF00`. Esto mantiene I bien por encima de la zona de peligro.

---

## 15.5 Diferencias entre clones

El ecosistema del ZX Spectrum incluye docenas de clones, pero tres importan más para el desarrollo moderno: el Pentagon 128, el Scorpion ZS-256 y el ZX Spectrum Next.

### Pentagon 128

El Pentagon es la plataforma estándar del demoscene ruso y el objetivo principal de los capítulos de demoscene de este libro.

| Parámetro | Pentagon 128 | 128K original |
|-----------|-------------|---------------|
| Reloj de CPU | 3,5 MHz | 3,5 MHz |
| T-states por fotograma | **71.680** | 70.908 |
| Líneas de escaneo por fotograma | **320** | 311 |
| Memoria contendida | **Ninguna** | Páginas 1, 3, 5, 7 |
| Líneas de borde (superior) | **80** | 63 |
| Líneas de borde (inferior) | **48** | 56 |

Los 772 T-states extra por fotograma (71.680 vs 70.908) provienen de las líneas de escaneo adicionales. El borde se distribuye diferentemente: un borde superior más alto y un borde inferior más corto. Esto afecta los efectos de borde -- código de demo que produce un patrón de borde simétrico en el 128K será ligeramente asimétrico en el Pentagon.

La ausencia de memoria contendida es la característica definitoria del Pentagon para los programadores. Cada instrucción cuesta exactamente lo que dice la hoja de datos. Por eso usamos la temporización del Pentagon a lo largo de este libro.

**Modo Turbo 7 MHz.** Muchas máquinas compatibles con Pentagon (Pentagon 512, Pentagon 1024, ATM Turbo 2+) ofrecen un modo turbo de 7 MHz. La CPU funciona a doble velocidad, pero la temporización de la ULA permanece igual. Esto significa que el presupuesto de fotograma se duplica a aproximadamente 143.360 T-states en modo turbo. La trampa: el modo turbo no es estándar en todas las máquinas, y el código que depende de él no funcionará en un Pentagon 128 estándar o en cualquier hardware Sinclair.

Para juegos, el modo turbo es un lujo que te permite ejecutar lógica más compleja o más sprites por fotograma. Para demos dirigidas a reglas de compo, generalmente está prohibido -- las competiciones especifican "Pentagon 128K, 3,5 MHz."

### Scorpion ZS-256

El Scorpion es un clon ucraniano con 256 KB de RAM (16 páginas de 16 KB) y varias extensiones de hardware.

| Característica | Scorpion ZS-256 |
|---------|----------------|
| RAM | 256 KB (16 páginas) |
| Conmutación de bancos | Puerto extendido `$1FFD` para páginas 8-15 |
| Gráficos | Modo GMX: 320x200, 16 colores de 256 |
| Memoria contendida | Ninguna |
| Temporización de fotograma | Compatible con Pentagon (71.680 T-states) |

La RAM duplicada es útil para juegos: obtienes 16 páginas de datos en lugar de 8. Las páginas extra se acceden vía el puerto `$1FFD`, que usa un esquema similar a `$7FFD` pero controla la RAM adicional.

GMX (Graphics Mode Extended) es el truco del Scorpion: una visualización de 320x200 con 16 colores elegidos de una paleta de 256 colores. Esto rompe completamente con la visualización basada en atributos del Spectrum, ofreciendo un framebuffer lineal más cercano a lo que verías en un Amiga o un PC VGA. El framebuffer GMX es grande (32.000 bytes para color de 4 bits) y vive en las páginas de RAM extendida.

Pocos juegos apuntan a GMX porque limita tu audiencia a propietarios de Scorpion. Pero demuestra lo que el hardware Z80 puede hacer cuando se libera de la cuadrícula de atributos de la ULA.

### ZX Spectrum Next

El ZX Spectrum Next es el buque insignia moderno de la plataforma: una máquina basada en FPGA que es retrocompatible con el Spectrum original pero añade hardware nuevo sustancial.

| Característica | ZX Spectrum Next |
|---------|-----------------|
| CPU | Z80N (Z80 + nuevas instrucciones) a 3,5 / 7 / 14 / 28 MHz |
| RAM | 1 MB (ampliable a 2 MB), páginas MMU de 8 KB |
| MMU | 8 ranuras x 8 KB = mapeo de memoria de grano fino |
| Layer 2 | 256x192 o 320x256, color de 8 bits (256 colores) |
| Tilemap | Capa de tilemap por hardware, baldosas de 40x32 u 80x32 |
| Sprites | 128 sprites por hardware, 16x16, hasta 12 por línea de escaneo |
| Copper | Coprocesador para cambios de registro por línea de escaneo |
| DMA | zxnDMA para transferencias de bloques rápidas |
| Sonido AY | 3 x AY-3-8910 (9 canales) con panorámica estéreo por canal |

La **MMU** del Next es fundamentalmente diferente de la conmutación de bancos del 128K. En lugar de una ranura conmutable de 16 KB, el Next divide todo el espacio de direcciones de 64 KB en ocho ranuras de 8 KB. Cada ranura puede ser mapeada independientemente a cualquier página de 8 KB del pool de 1-2 MB de RAM. Esto significa que puedes tener control de grano fino:

```z80
; Map 8KB page $0A into slot 3 ($6000-$7FFF)
    ld   a, $0A
    ld   bc, $243B          ; Next register select port
    ld   a, $53             ; Register $53 = MMU slot 3
    out  (c), a
    ld   bc, $253B          ; Next register data port
    ld   a, $0A             ; Page $0A
    out  (c), a
```

Esto es mucho más flexible que la única ranura conmutable del 128K. Puedes mapear datos de sprites en una ventana de 8 KB, datos de nivel en otra, y datos de música en una tercera -- todo simultáneamente visible.

**Layer 2** te da una visualización de bitmap de 256 colores sin conflicto de atributos. Esta es la mejora de calidad de vida más significativa para los desarrolladores de juegos: no más planificación cuidadosa de atributos, no más soluciones para el clash de color. Solo un framebuffer donde cada byte es un píxel. El coste es memoria: una pantalla Layer 2 de 256x192 son 49.152 bytes.

**Los sprites por hardware** en el Next proporcionan 128 ranuras de sprite, cada una de 16x16 píxeles con color de 8 bits, hasta 12 por línea de escaneo. Los atributos de sprites (posición, patrón, rotación) se establecen a través de registros del Next y el puerto `$57`. No se necesita renderizado por software.

**El Copper** es un coprocesador que ejecuta un programa simple sincronizado con la posición del haz. Puede escribir en cualquier registro del Next en cualquier línea de escaneo, habilitando cambios de paleta por línea, offsets de desplazamiento y efectos de rasterizado sin consumir T-states del Z80 -- un homenaje deliberado al Copper del Amiga.

**zxnDMA** proporciona transferencias de bloques aceleradas por hardware a aproximadamente 2 T-states por byte -- unas 10 veces más rápido que `LDIR`. Para llenar el framebuffer Layer 2 o transferir datos de sprites, DMA es transformador.

El Next es esencialmente una máquina diferente que resulta ser retrocompatible. Las restricciones interesantes cambian de "¿puedo hacer que esto quepa en el presupuesto de fotograma?" a "¿cómo aprovecho mejor las múltiples capas de hardware?"

---

## 15.6 Agon Light 2: Una bestia diferente

El Agon Light 2 es la segunda plataforma para nuestros capítulos de desarrollo de juegos. Ejecuta un Zilog eZ80 -- un descendiente directo del Z80 -- a 18,432 MHz, con 512 KB de RAM plana y un coprocesador ESP32 separado que maneja vídeo y audio. La arquitectura es fundamentalmente diferente del Spectrum: en lugar de una CPU que comparte un bus con un chip de salida de vídeo fijo, el Agon usa dos procesadores independientes comunicándose a través de un enlace serial.

### Arquitectura de doble procesador

La característica definitoria del Agon es la división entre el **eZ80** (tu CPU) y el **ESP32** (el VDP, Video Display Processor):

```
                        +-----------+
                        |   eZ80    |  18.432 MHz
                        |  512 KB   |  Your code runs here
                        |  MOS API  |  24-bit addressing
                        +-----+-----+
                              |
                          UART serial
                          (384 Kbaud)
                              |
                        +-----+-----+
                        |   ESP32   |  240 MHz dual-core
                        |  FabGL    |  Video: up to 640x480
                        |  VDP      |  Audio: waveforms, samples
                        +-----------+
```

Esta división tiene consecuencias profundas:

1. **Sin memoria de vídeo compartida.** No puedes escribir directamente a un framebuffer. Cada píxel, cada sprite, cada operación de baldosa es un *comando* enviado a través del enlace serial del eZ80 al ESP32.
2. **Latencia.** El enlace serial funciona a 384.000 baudios. Un solo byte de comando toma aproximadamente 26 microsegundos para transmitirse. Operaciones de dibujo complejas (rellenar rectángulo, dibujar bitmap) requieren múltiples bytes y el VDP necesita tiempo para ejecutarlas.
3. **Renderizado asíncrono.** El VDP procesa comandos desde un búfer. Tu código eZ80 envía comandos y continúa ejecutándose. El VDP se pone al día independientemente. Esto significa que no tienes el acoplamiento estrecho del Spectrum entre el trabajo de CPU y la salida de pantalla -- pero tampoco puedes controlar precisamente cuándo aparecen los píxeles.
4. **Tasa de fotogramas independiente.** El VDP renderiza a su propia tasa (típicamente 60 Hz). Tu bucle de juego eZ80 puede ejecutarse a cualquier tasa que quiera; el VDP mostrará lo que haya dibujado más recientemente.

Para los programadores de Spectrum, esto es un cambio de paradigma. Pasas de "escribo bytes a la memoria de vídeo y aparecen en la siguiente línea de escaneo" a "envío comandos de dibujo y confío en que el VDP los renderice eventualmente." La ventaja es una sobrecarga de CPU enormemente reducida para gráficos. La desventaja es menos control.

### Modelo de memoria del eZ80: Plano de 24 bits

El eZ80 tiene un bus de direcciones de 24 bits, dándole un espacio de direcciones teórico de 16 MB. El Agon Light 2 mapea 512 KB de RAM en la parte inferior de este espacio:

| Rango de direcciones | Tamaño | Contenido |
|---------------|------|----------|
| `$000000`-`$07FFFF` | 512 KB | RAM |
| `$080000`-`$0FFFFF` | 512 KB | RAM (espejo, en algunas placas) |
| `$A00000`-`$FFFFFF` | varía | E/S, periféricos on-chip |

Sin conmutación de bancos. Sin cambio de páginas. Sin memoria contendida. Tu código, tus datos, tus búferes, tus tablas de consulta -- todo vive en un espacio único, plano, linealmente direccionable. Después del acto de malabarismo de 8 páginas del Spectrum, esto es liberador.

El eZ80 soporta dos modos de operación que determinan cómo usa este espacio de direcciones.

### Modo ADL vs modo Z80

Esta es la distinción arquitectónica más importante en el Agon, y confunde a los recién llegados constantemente.

**Modo Z80** (también llamado modo compatible con Z80) hace que el eZ80 se comporte como un Z80 clásico: registros de 16 bits, direcciones de 16 bits, espacio de direcciones de 64 KB. Todo el código Z80 estándar funciona sin modificación. Los 8 bits superiores de la dirección vienen del registro MBASE, creando una "ventana" de 64 KB en el espacio de direcciones de 24 bits. Esto es lo que usas al portar código Z80 existente.

**Modo ADL** (Address Data Long) es el modo nativo del eZ80: registros de 24 bits, direcciones de 24 bits, espacio de direcciones completo de 16 MB. HL, BC, DE, SP, e IX/IY son todos de 24 bits de ancho. `LD HL,$123456` carga un valor de 3 bytes. `PUSH HL` empuja 3 bytes a la pila (no 2). Cada puntero es de 3 bytes.

```z80
; ADL mode: 24-bit addressing, full 512KB accessible
    ld   hl, $040000       ; point to a buffer 256KB into RAM
    ld   (hl), $FF         ; write directly -- no banking needed
    ld   bc, 1024
    ld   de, $040001
    ldir                   ; fill 1KB in one shot
```

MOS (el sistema operativo del Agon) arranca el eZ80 en modo ADL, y la mayoría del software del Agon permanece en modo ADL. Las diferencias clave del modo Z80:

| Característica | Modo Z80 | Modo ADL |
|---------|----------|----------|
| Ancho de registro | 16 bits | 24 bits |
| Espacio de direcciones | 64 KB (vía MBASE) | 16 MB (24 bits) |
| Tamaño de PUSH/POP | 2 bytes | 3 bytes |
| Direcciones JP/CALL | 16 bits | 24 bits |
| Tamaño de entrada de pila | 2 bytes por entrada | 3 bytes por entrada |
| Codificación de instrucciones | Compatible Z80 | Extendida (direcciones de 3 bytes) |

**La trampa:** si escribes código asumiendo valores de 16 bits y lo ejecutas en modo ADL, las cosas se rompen de formas sutiles. Un `PUSH HL` empuja 3 bytes, no 2, así que tus estructuras de datos basadas en pila tienen un tamaño diferente. Un `JP (HL)` salta a una dirección de 24 bits, así que las tablas de consulta de direcciones de 16 bits no funcionarán. El eZ80 proporciona instrucciones con sufijos `LD.S` y `LD.L` para controlar explícitamente el ancho de datos, y puedes cambiar entre modos con prefijos `JP.LIL` / `JP.SIS`, pero esto se complica rápido.

**La regla práctica para juegos:** quédate en modo ADL. Usa direcciones de 24 bits en todas partes. No intentes compartir código entre una compilación para Spectrum y una para Agon a nivel de código fuente -- el direccionamiento es demasiado diferente. En su lugar, comparte *algoritmos* y *formatos de datos*, con implementaciones específicas de plataforma para acceso a memoria, E/S y gráficos.

### API de MOS: El sistema operativo

MOS (Machine Operating System) proporciona servicios del sistema en el Agon: E/S de archivos, entrada de teclado, acceso a temporizador y comunicación con el VDP. Las llamadas a MOS se hacen a través de `RST $08` con un número de función en el registro A:

```z80
; MOS API: open a file
    ld   hl, filename       ; pointer to null-terminated filename
    ld   c, $01             ; mode: read
    rst  $08                ; MOS call
    db   $0A                ; function $0A: ffs_fopen
    ; Returns file handle in A
filename:
    db   "level1.dat", 0
```

Funciones clave de MOS para desarrollo de juegos:

| Función | Código | Descripción |
|----------|------|-------------|
| `mos_getkey` | `$00` | Leer teclado (no bloqueante) |
| `mos_load` | `$01` | Cargar archivo de tarjeta SD |
| `mos_save` | `$02` | Guardar archivo en tarjeta SD |
| `mos_sysvars` | `$08` | Obtener puntero a variables del sistema (contador vsync, etc.) |
| `ffs_fopen` | `$0A` | Abrir archivo |
| `ffs_fclose` | `$0B` | Cerrar archivo |
| `ffs_fread` | `$0C` | Leer de archivo |
| `mos_getrtc` | `$12` | Obtener reloj en tiempo real |

La E/S de archivos en el Agon es trivialmente fácil comparada con el Spectrum. Sin carga de cinta, sin wrappers de esxDOS, sin TR-DOS: simplemente abre un archivo de la tarjeta SD y léelo en memoria. Datos de nivel, hojas de sprites, música -- cárgalos bajo demanda, sin gimnasia de conmutación de bancos.

### Comandos VDP: Hablando con la pantalla

Todos los gráficos pasan por comandos VDU enviados al ESP32 VDP. El eZ80 envía bytes a un flujo de salida VDU; el VDP los interpreta como instrucciones de dibujo:

```z80
; VDP: draw a filled rectangle at (10, 10)
    rst  $10 : db 25        ; PLOT command
    rst  $10 : db 85        ; mode: filled rectangle
    rst  $10 : db 10        ; x low
    rst  $10 : db 0         ; x high
    rst  $10 : db 10        ; y low
    rst  $10 : db 0         ; y high
```

Verboso comparado con `LD (HL),A`, pero el VDP hace el renderizado en el ESP32. El VDP soporta modos de bitmap (hasta 640x480), hasta 256 sprites por hardware (cada uno hasta 64x64), tilemaps por hardware con desplazamiento, y audio (formas de onda, ADSR, muestras).

El cuello de botella es el enlace serial, no la CPU. Una escena compleja con muchas actualizaciones de sprites puede saturar el UART, causando retraso visual. Minimiza los comandos VDP por fotograma: agrupa actualizaciones, usa desplazamiento por hardware en lugar de redibujar baldosas, y deja que el motor de sprites haga el trabajo pesado.

---

## 15.7 Comparando las plataformas

Pongamos las dos máquinas lado a lado, enfocándonos en lo que importa para el motor de juego que construiremos en los Capítulos 16-19.

| Característica | ZX Spectrum 128K | Agon Light 2 |
|---------|-----------------|---------------|
| CPU | Z80A @ 3,5 MHz | eZ80 @ 18,432 MHz |
| T-states por fotograma (50 Hz) | ~70.908 (128K) / 71.680 (Pentagon) | ~368.640 |
| RAM | 128 KB (8 x 16 KB páginas) | 512 KB (plana) |
| Espacio de direcciones | 64 KB (con bancos) | 16 MB (24 bits) |
| Memoria de pantalla | Bus compartido, escritura directa | VDP separado, basado en comandos |
| Colores | 15 (8 base x brillo, menos superposición) | Hasta 64 en modos estándar |
| Resolución | 256x192 (color de atributo por 8x8) | Configurable, hasta 640x480 |
| Sprites | Solo por software | Hasta 256 sprites por hardware |
| Desplazamiento | Solo por software (desplazamiento/copia manual) | Offsets de desplazamiento por hardware |
| Sonido | AY-3-8910 (3 canales) | Audio ESP32 (multi-canal, formas de onda) |
| Almacenamiento | Cinta / DivMMC (esxDOS) | Tarjeta SD (FAT32) |
| Doble búfer | Pantalla sombra (página 7) | Gestionado por VDP |

La relación del presupuesto de fotograma es aproximadamente 5:1 a favor del Agon. Pero los gráficos del Agon pasan por un cuello de botella serial, así que la velocidad bruta de CPU no se traduce directamente en velocidad de renderizado. En el Spectrum, `PUSH HL` escribe dos bytes en la pantalla en 11 T-states. En el Agon, actualizar la posición de un sprite requiere 6+ bytes sobre un enlace de 384 Kbaud, tomando cientos de microsegundos independientemente de la velocidad de CPU.

El Spectrum recompensa la optimización a nivel de byte. El Agon recompensa las decisiones arquitectónicas. Ambos recompensan el pensamiento cuidadoso sobre presupuestos de fotograma.

---

## 15.8 Práctica: Utilidad de inspección de memoria

Construyamos un inspector de memoria simple para ambas plataformas. Esta utilidad muestra una región de RAM como bytes hexadecimales en pantalla, y te permite navegar por la memoria con el teclado. Es el tipo de herramienta que usarás constantemente durante el desarrollo.

### Versión para Spectrum

La versión para Spectrum escribe directamente en la memoria de pantalla. Mostramos 16 filas de 16 bytes (256 bytes por página) con la dirección de inicio mostrada a la izquierda.

```z80
; Memory Inspector - ZX Spectrum 128K
; Displays 256 bytes of memory as hex, navigable with keys
; ORG $8000 (page 2, uncontended)

    ORG  $8000

SCREEN_ATTR EQU $5800
START_ADDR  EQU inspect_addr      ; address to inspect (self-mod)

start:
    call clear_screen

main_loop:
    halt                          ; sync to frame

    ; Read keyboard
    call read_keys                ; returns: A = action
    cp   1
    jr   z, .page_up             ; Q = previous page
    cp   2
    jr   z, .page_down           ; A = next page
    cp   3
    jr   z, .bank_up             ; P = next bank
    cp   4
    jr   z, .bank_down           ; O = previous bank
    jr   .draw

.page_up:
    ld   hl, (inspect_addr)
    ld   de, -256
    add  hl, de
    ld   (inspect_addr), hl
    jr   .draw
.page_down:
    ld   hl, (inspect_addr)
    ld   de, 256
    add  hl, de
    ld   (inspect_addr), hl
    jr   .draw
.bank_up:
    ld   a, (current_bank)
    inc  a
    and  7                        ; wrap 0-7
    ld   (current_bank), a
    call bank_switch
    jr   .draw
.bank_down:
    ld   a, (current_bank)
    dec  a
    and  7
    ld   (current_bank), a
    call bank_switch

.draw:
    ; Display current bank and address
    call draw_header

    ; Display 16 rows x 16 bytes
    ld   hl, (inspect_addr)
    ld   b, 16                    ; 16 rows
    ld   de, $4060                ; screen position (row 3, col 0)
.row_loop:
    push bc
    push hl

    ; Print address
    ld   a, h
    call print_hex                ; print high byte of address
    ld   a, l
    call print_hex                ; print low byte
    ld   a, ':'
    call print_char

    ; Print 16 hex bytes
    pop  hl
    push hl
    ld   b, 16
.byte_loop:
    ld   a, (hl)
    call print_hex                ; 7T load + print routine
    inc  hl
    ld   a, ' '
    call print_char
    djnz .byte_loop

    pop  hl
    ld   de, 16
    add  hl, de                   ; advance to next row
    pop  bc

    ; Move screen pointer down one character row
    call next_char_row

    djnz .row_loop

    jr   main_loop

; --- Data ---
inspect_addr:  dw $C000          ; start address to inspect
current_bank:  db 0              ; current bank at $C000
bank_shadow:   db 0              ; shadow of port $7FFD

; read_keys, print_hex, print_char, clear_screen,
; draw_header, next_char_row, bank_switch: implementations
; omitted for brevity -- see examples/mem_inspect.a80
; for the complete compilable source.
```

El punto arquitectónico clave: inspeccionamos `$C000` porque esa es la ranura con banco. Cambiando `current_bank`, podemos paginar a través de las 8 páginas de RAM usando la rutina `bank_switch` de la sección 15.1. El inspector mismo vive en `$8000` (página 2), a salvo de los cambios de banco.

### Versión para Agon

La versión para Agon usa llamadas al sistema MOS para entrada de teclado y salida de texto VDP. Sin cálculo de dirección de pantalla, sin manejo de atributos -- solo envía texto al VDP.

```z80
; Memory Inspector - Agon Light 2 (ADL mode)
    .ASSUME ADL=1
    ORG  $040000

main_loop:
    ; Wait for vsync via MOS sysvar
    rst  $08
    db   $08                      ; mos_sysvars
    ld   a, (ix+$00)              ; sysvar_time (low byte)
.wait_vsync:
    cp   (ix+$00)
    jr   z, .wait_vsync           ; spin until counter changes

    ; Check keyboard (Q = up, A = down)
    rst  $08
    db   $00                      ; mos_getkey
    ; ... navigation same as Spectrum version ...

.draw:
    rst  $10
    db   30                       ; VDU 30 = cursor home

    ld   hl, (inspect_addr)       ; 24-bit load!
    ld   b, 16
.row_loop:
    push bc
    push hl
    call print_hex24              ; print full 24-bit address
    ld   a, ':'
    rst  $10
    pop  hl
    push hl
    ld   b, 16
.byte_loop:
    ld   a, (hl)                  ; direct 24-bit access, no banking
    call print_hex8
    inc  hl
    djnz .byte_loop
    pop  hl
    ld   de, 16
    add  hl, de
    pop  bc
    djnz .row_loop
    jr   main_loop

inspect_addr: dl $000000          ; 24-bit address (dl, not dw)
; Full source: examples/mem_inspect_agon.a80
```

Observa el contraste:

- **Sin conmutación de bancos.** El inspector del Agon puede mirar cualquier dirección en 512 KB directamente. `LD HL,$070000` y estás inspeccionando 448 KB adentro de la RAM. Sin puertos, sin variables sombra, sin riesgo de poner en banco la página equivocada.
- **Sin cálculo de dirección de pantalla.** La salida de texto pasa por `RST $10`, y el VDP maneja el posicionamiento del cursor, renderizado de caracteres y desplazamiento.
- **Directivas de datos de 24 bits.** Usamos `dl` (define long) para punteros de 3 bytes en lugar de `dw` (define word).
- **VSync a través de variables del sistema.** MOS proporciona un contador `sysvar_time` que se incrementa cada fotograma. Hacemos spin-wait sobre él para sincronización de fotograma -- más burdo que el `HALT` del Spectrum, pero funcional.

Ambos inspectores hacen el mismo trabajo. La versión del Spectrum es más código (debes manejar todo tú mismo) pero te da control total. La versión del Agon es menos código (el SO y el VDP manejan la visualización) pero te da menos control sobre exactamente cómo se ve la salida.

Esto refleja la experiencia de desarrollo más amplia en ambas plataformas. El Spectrum demanda más esfuerzo para menos riqueza visual. El Agon demanda menos esfuerzo para más riqueza visual. Ambos recompensan entender el hardware.

---

## Resumen

- El **ZX Spectrum 128K** tiene 128 KB de RAM en 8 páginas de 16 KB. Las páginas 2 y 5 están fijas en el espacio de direcciones; la ranura superior de 16 KB en `$C000` es conmutable vía el puerto `$7FFD`. Mantén tu código principal en la página 2 y tu manejador de interrupciones fuera de la memoria con banco.

- **La memoria contendida** ralentiza el acceso de CPU a ciertas páginas de RAM durante la visualización activa en hardware Sinclair original. Penalización promedio: ~0,92 T-states extra por byte. Los clones Pentagon no tienen contención. Para desarrollo de juegos, presupuesta un 15-20% de sobrecarga en escrituras de pantalla y mantén el código crítico en tiempo en páginas no contendidas.

- **Temporización de la ULA:** la interrupción se dispara al inicio del fotograma. Tienes ~14.000 T-states de tiempo libre de contención antes de que el haz entre en el área de visualización activa. Usa esta ventana para escrituras de pantalla.

- El **puerto $7FFD** es de solo escritura. Guarda su valor como sombra en RAM. El bit 3 selecciona la pantalla sombra (página 7) para doble búfer. El bit 5 desactiva la paginación permanentemente hasta el reinicio.

- **El bus flotante**, **la nieve de ULA** y el **bug de lectura de $7FFD** son peculiaridades del hardware Sinclair original. Evita valores del registro I de `$40`-`$7F`. No almacenes datos en la dirección `$7FFD`. El bus flotante no está presente en los clones.

- **Pentagon 128**: sin memoria contendida, 71.680 T-states por fotograma, 320 líneas de escaneo. El estándar del demoscene. El modo turbo de 7 MHz duplica el presupuesto de fotograma en algunas variantes.

- **Scorpion ZS-256**: 256 KB de RAM (16 páginas), modo GMX 320x200x16 colores.

- **ZX Spectrum Next**: 1-2 MB de RAM con páginas MMU de 8 KB, Layer 2 (bitmap de 256 colores), 128 sprites por hardware, coprocesador Copper, zxnDMA, sonido triple AY.

- El **Agon Light 2** usa una arquitectura de doble procesador: eZ80 @ 18,432 MHz para lógica, ESP32 para vídeo/audio. 512 KB de RAM plana, direccionamiento de 24 bits (modo ADL), API MOS para servicios del sistema, comandos VDP para todos los gráficos.

- **Modo ADL vs modo Z80**: el modo ADL usa registros y direcciones de 24 bits. El modo Z80 emula el Z80 clásico con direcciones de 16 bits vía MBASE. Quédate en modo ADL para código nuevo del Agon.

- El **enlace serial** entre eZ80 y ESP32 es el cuello de botella del Agon. Minimiza el tráfico de comandos VDP por fotograma. Usa sprites y tilemaps por hardware para reducir el número de comandos de dibujo.

- Ambas plataformas recompensan la gestión cuidadosa del presupuesto de fotograma. El Spectrum te da ~70.000 T-states y demanda optimización a nivel de byte. El Agon te da ~368.000 T-states pero limita los gráficos a través de un enlace serial. Diferentes restricciones, misma disciplina.

---

> **Fuentes:** Introspec "GO WEST Parts 1--2" (Hype 2015); ZX Spectrum 128K Service Manual; Zilog eZ80 CPU User Manual; Agon Light 2 Documentation (Bernardo Kastrup); ZX Spectrum Next User Manual (2nd Edition)
