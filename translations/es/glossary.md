# Glosario

Vocabulario técnico utilizado a lo largo de *Coding the Impossible*. Los términos están agrupados por categoría; "First" indica el capítulo donde el término se introduce o define, "Also" lista los capítulos con uso significativo.

---

## A. Temporización y rendimiento

| Term (Término) | Definición | Canonical form | First | Also |
|------|-----------|----------------|-------|------|
| T-state (T-state) | Un ciclo de reloj de la CPU Z80 a 3.5 MHz (~286 ns). La unidad fundamental de tiempo de ejecución en el Spectrum. | "T-states" in prose; "T" in code comments (e.g., `; 11T`) | Ch01 | Ch02--Ch23 |
| Frame (fotograma) | Un refresco completo de pantalla a ~50 Hz (PAL). La duración varía según el modelo de máquina. | "frame" | Ch01 | all |
| Frame budget (presupuesto de fotograma) | Total de T-states entre interrupciones: Pentagon 71,680, ZX 128K 70,908, ZX 48K 69,888. Presupuesto práctico después de HALT + ISR + reproductor de música: ~66,000--68,000 (Pentagon), ~55,000--60,000 (128K con escrituras a pantalla durante la visualización activa). Ver el Cap. 15 para mapas de tact con desglose por región (borde superior, pantalla activa, borde inferior). | "frame budget" | Ch01 | Ch04, Ch05, Ch08, Ch10, Ch12, Ch14, Ch16, Ch17, Ch18, Ch21 |
| Scanline (línea de escaneo) | Una línea horizontal de la pantalla. El ancho varía: 224 T-states en 48K/Pentagon, 228 T-states en 128K. El fotograma consiste en 320 (Pentagon), 311 (128K), o 312 (48K) líneas de escaneo incluyendo bordes. | "scanline" (one word) | Ch01 | Ch02, Ch08, Ch15, Ch17 |
| Contended memory (memoria contendida) | Páginas de RAM ($4000--$7FFF) donde ULA y CPU comparten el bus de memoria en hardware Sinclair. Los accesos de la CPU se retrasan por 0--6 T-states extra por acceso en un patrón repetitivo de 8 T-states. Los clones Pentagon no tienen contención. | "contended memory" | Ch01 | Ch04, Ch05, Ch15, Ch17, Ch18, Ch21, Ch22, Ch23 |
| Machine cycle (ciclo de máquina) | Un grupo de 3--6 T-states dentro de una instrucción. El primer ciclo de máquina (M1) siempre es la búsqueda del código de operación (opcode) a 4 T-states. | "machine cycle" or "M-cycle" | Ch01 | -- |
| Border time (tiempo de borde) | Líneas de escaneo fuera de la pantalla activa de 192 líneas (bordes superior/inferior). Sin contención; ~14,000 T-states disponibles en 128K. | "border time" | Ch01 | Ch08, Ch15, Ch17 |
| Timing harness (arnés de temporización) | Técnica de depuración: establecer el color del borde a rojo antes del código, negro después; la altura de la franja en pantalla muestra el coste en T-states. | "border-colour timing harness" | Ch01 | Ch02, Ch03, Ch08, Ch18 |

## B. Hardware --- Sinclair y clones

| Term (Término) | Definición | Canonical form | First | Also |
|------|-----------|----------------|-------|------|
| Z80 | CPU Zilog Z80A a 3.5 MHz. Bus de datos de 8 bits, bus de direcciones de 16 bits. El procesador en todos los modelos ZX Spectrum. | "Z80" | Ch01 | all |
| ULA | Uncommitted Logic Array. Chip personalizado que genera la señal de vídeo y maneja E/S (teclado, cinta, altavoz). Comparte el bus de memoria con la CPU en hardware Sinclair. | "ULA" | Ch01 | Ch02, Ch08, Ch15 |
| ZX Spectrum 48K | Modelo Sinclair original. 69,888 T-states/fotograma, 312 líneas de escaneo, 32K inferiores con contención. | "48K" or "ZX Spectrum 48K" | Ch01 | Ch11, Ch15 |
| ZX Spectrum 128K | Modelo extendido con 128K de RAM bancada, chip de sonido AY, dos páginas de visualización. 70,908 T-states/fotograma, 311 líneas de escaneo. | "128K" or "ZX Spectrum 128K" | Ch01 | Ch11, Ch15, Ch20, Ch21 |
| Screen memory (memoria de pantalla) | $4000--$5AFF. Datos de píxeles ($4000--$57FF, 6,144 bytes) + área de atributos ($5800--$5AFF, 768 bytes). Disposición entrelazada para filas de píxeles. | "screen memory" | Ch01 | Ch02, Ch08, Ch16, Ch17 |
| Attribute area (área de atributos) | 768 bytes en $5800--$5AFF. Un byte por celda de caracteres 8x8: FBPPPIII (Flash, Bright, Paper x3, Ink x3). Controla el color. | "attribute area" | Ch02 | Ch08, Ch09, Ch10 |
| Attribute clash (conflicto de atributos) | Limitación del hardware: solo 2 colores (tinta + papel) por celda de 8x8. Los sprites superpuestos fuerzan compromisos de color. | "attribute clash" | Ch02 | Ch08, Ch16 |
| Interleaved screen layout (diseño de pantalla entrelazado) | Las filas de píxeles en la memoria de vídeo no son secuenciales. La dirección codifica Y como 010TTSSS.LLLCCCCC a través de dos bytes. Tres tercios de 2,048 bytes. | "interleaved screen layout" | Ch02 | Ch07, Ch16, Ch17, Ch22 |
| Shadow screen (pantalla sombra) | Segunda página de visualización en $C000 (banco 7) en 128K. Conmutada vía puerto $7FFD bit 3. | "shadow screen" | Ch08 | Ch10, Ch15, Ch21 |
| AY-3-8910 | Generador de Sonido Programable de General Instrument. Tres canales de tono de onda cuadrada, un generador de ruido, un generador de envolvente. 14 registros. Estándar en modelos 128K. | "AY-3-8910" (first use), then "AY" | Ch11 | Ch12, Ch15, Ch21 |
| Port $FFFD / $BFFD (puerto $FFFD / $BFFD) | Puertos de selección de registro / escritura de datos del AY en 128K. | "$FFFD" / "$BFFD" | Ch11 | Ch12 |
| Port $7FFD (puerto $7FFD) | Puerto de paginación de memoria y selección de pantalla del 128K. | "$7FFD" | Ch08 | Ch12, Ch15, Ch21 |
| Port $FE (puerto $FE) | Puerto de E/S: bits 0--2 = color del borde, bit 3 = MIC, bit 4 = EAR/altavoz. También entrada de teclado (medias filas activas-bajas). | "$FE" | Ch01 | Ch02, Ch11, Ch18 |
| IM1 / IM2 | Modos de interrupción. IM1: manejador en $0038. IM2: vectorizado vía registro I + byte del bus de datos; usado para manejadores de interrupción personalizados (reproductores de música, threading). | "IM1" / "IM2" | Ch01 | Ch03, Ch05, Ch11, Ch12 |
| DivMMC | Interfaz de tarjeta SD para uso moderno del Spectrum. Soporta esxDOS. | "DivMMC" | Ch15 | Ch20 |
| ZX Spectrum Next | Spectrum mejorado basado en FPGA. CPU Z80N (instrucciones extra), Triple AY (3xAY), sprites por hardware, coprocesador copper, tilemap, turbo a 28 MHz. | "ZX Spectrum Next" or "Next" | Ch11 | Ch15 |

## C. Hardware --- Ecosistema soviético/postsoviético

| Term (Término) | Definición | Canonical form | First | Also |
|------|-----------|----------------|-------|------|
| Pentagon 128 | El clon soviético de ZX Spectrum más popular. Sin memoria contendida, 71,680 T-states/fotograma, 320 líneas de escaneo. La plataforma de referencia para la demoscene del ZX Spectrum. | "Pentagon 128" (first use), then "Pentagon" | Ch01 | Ch04, Ch05, Ch08, Ch11, Ch15, Ch16, Ch17, Ch18, Ch19, Ch20, Ch21, Ch22 |
| Scorpion ZS-256 | Clon soviético con TurboSound y memoria extendida. Temporización compatible con Pentagon. | "Scorpion ZS-256" (first use), then "Scorpion" | Ch04 | Ch11, Ch15, Ch20 |
| TurboSound | Dos chips AY (2xAY) en una máquina, proporcionando 6 canales de sonido. Estándar en Scorpion; disponible como añadido para Pentagon. | "TurboSound" | Ch11 | Ch15, Ch20 |
| TR-DOS | Sistema operativo de disco en clones soviéticos vía interfaz Beta Disk 128. Formato de archivo: `.trd`. El formato de distribución estándar para compos de la demoscene y revistas de disco. | "TR-DOS" | Ch15 | Ch20 |
| Beta Disk 128 | Interfaz estándar de controladora de disquete en clones Pentagon y Scorpion. | "Beta Disk 128" | Ch15 | Ch20 |

## D. Hardware --- Agon Light 2

| Term (Término) | Definición | Canonical form | First | Also |
|------|-----------|----------------|-------|------|
| Agon Light 2 | Computadora de placa única con CPU Zilog eZ80 a 18.432 MHz y VDP basado en ESP32. 512KB de RAM plana, sin bancos. | "Agon Light 2" or "Agon" | Ch01 | Ch11, Ch15, Ch18, Ch22 |
| eZ80 | CPU Zilog eZ80. Conjunto de instrucciones compatible con Z80; la mayoría de instrucciones se ejecutan en menos ciclos. Direccionamiento plano de 24 bits (modo ADL). ~368,640 T-states/fotograma a 50 Hz. | "eZ80" | Ch01 | Ch15, Ch22 |
| VDP | Procesador de visualización de vídeo. Microcontrolador ESP32 ejecutando la librería FabGL. Maneja la pantalla, sprites, tilemaps, síntesis de sonido. Se comunica con el eZ80 por serial a 1,152,000 baudios. | "VDP" | Ch02 | Ch11, Ch15, Ch18, Ch22 |
| ADL mode (modo ADL) | Modo de direccionamiento de 24 bits en el eZ80. Espacio de direcciones plano de 512KB, sin bancos. | "ADL mode" | Ch15 | Ch22 |
| MOS | Sistema operativo en el Agon. Proporciona llamadas API para comandos VDP, teclado, sistema de archivos. `waitvblank` reemplaza al HALT del Spectrum para sincronización de fotograma. | "MOS" | Ch18 | Ch22 |

## E. Técnicas

| Term (Término) | Definición | Canonical form | First | Also |
|------|-----------|----------------|-------|------|
| Self-modifying code (código auto-modificable, SMC) | Escribir en bytes de instrucciones en tiempo de ejecución. Seguro en Z80 (sin caché de instrucciones). Patrones comunes: parchear operandos inmediatos, cambiar destinos de salto, intercambiar opcodes. | "self-modifying code (SMC)" on first use; "SMC" subsequently | Ch03 | Ch06, Ch07, Ch09, Ch10, Ch13, Ch16, Ch17, Ch22, Ch23 |
| Unrolled loop (bucle desenrollado) | Intercambiar tamaño de código por velocidad repitiendo el cuerpo del bucle N veces, eliminando el overhead del contador de bucle. El desenrollado parcial mantiene DJNZ para el conteo externo. | "unrolled loop" | Ch02 | Ch03, Ch07, Ch10, Ch16, Ch17 |
| PUSH trick (truco PUSH) | Secuestrar SP para usar PUSH para escrituras rápidas en memoria (5.5 T-states/byte vs 21 para LDIR). Debe usarse DI primero para proteger contra interrupciones que usan la pila. | "PUSH trick" or "stack-based output" | Ch03 | Ch07, Ch08, Ch10, Ch16 |
| LDI chain (cadena LDI) | Secuencia de instrucciones LDI individuales; 24% más rápida que LDIR para copias de tamaño conocido. Combinada con aritmética de punto de entrada para copias de longitud variable. | "LDI chain" | Ch03 | Ch07, Ch09 |
| LDPUSH | Fusionar datos de visualización en código ejecutable `LD DE,nn : PUSH DE` (21T por 2 bytes). Usado en motores multicolor. | "LDPUSH" | Ch08 | -- |
| DOWN_HL | Rutina clásica para avanzar HL una fila de píxeles hacia abajo en la memoria de pantalla entrelazada del Spectrum. 20T caso común, 77T peor caso (límite de tercio). | "DOWN_HL" | Ch02 | Ch16, Ch17, Ch23 |
| RET-chaining (encadenamiento RET) | Establecer SP a una tabla de direcciones; cada rutina termina con RET, despachando a la siguiente. 10T por despacho vs 17T para CALL. | "RET-chaining" | Ch03 | -- |
| Code generation (generación de código) | Escribir código máquina en un búfer en tiempo de ejecución, luego ejecutarlo. Elimina bifurcaciones y contadores de bucle de los bucles internos. | "code generation" | Ch03 | Ch06, Ch07, Ch09 |
| Compiled sprites (sprites compilados) | Sprites compilados en una secuencia de instrucciones PUSH/LD con pares de registros pre-cargados. Imagen fija, velocidad máxima. | "compiled sprites" | Ch03 | Ch16 |
| Double buffering (doble búfer) | Mantener dos páginas de visualización para evitar el tearing. En 128K: Pantalla 0 ($4000) y Pantalla 1 ($C000), conmutadas vía puerto $7FFD. | "double buffering" | Ch05 | Ch08, Ch10, Ch12 |
| Dirty rectangles (rectángulos sucios) | Guardar/restaurar el fondo bajo los sprites antes/después de dibujar. Evitar borrados de pantalla completa. | "dirty rectangles" | Ch08 | Ch16, Ch21 |
| Multicolor (multicolor) | Cambiar valores de atributos entre lecturas de línea de escaneo de la ULA para mostrar más de 2 colores por celda de 8x8. Consume 80--90% de la CPU. | "multicolor" | Ch08 | -- |
| Page-aligned table (tabla alineada a página) | Tabla de consulta de 256 bytes colocada en una dirección $xx00 para que H contenga la base y L sea el índice. Indexación de un solo registro sin overhead. | "page-aligned table" | Ch04 | Ch06, Ch07, Ch09, Ch10 |
| Lookup table (tabla de consulta) | Tabla de valores pre-calculados para acceso rápido en tiempo de ejecución. Evita cálculos costosos en bucles internos. | "lookup table" | Ch03 | Ch04, Ch07, Ch09, Ch17, Ch19, Ch20, Ch22 |
| Split counters (contadores divididos) | Reestructurar la iteración de pantalla para coincidir con la jerarquía de tres niveles (tercio/fila de caracteres/línea de escaneo), eliminando bifurcaciones. 60% más rápido que el recorrido ingenuo con DOWN_HL. | "split counters" | Ch02 | -- |
| 4-phase colour (color de 4 fases) | Ciclo de 4 fotogramas (2 normales + 2 con atributos invertidos) a 50 Hz. La persistencia retiniana promedia los colores, creando colores adicionales percibidos por celda. | "4-phase colour" | Ch10 | -- |
| Digital drums (tambores digitales) | Muestra PCM digital reproducida a través del registro de volumen AY como DAC de 4 bits (fase de ataque), transicionando a envolvente AY (fase de decaimiento). Consume ~2 fotogramas de CPU por golpe. | "digital drums" or "hybrid drums" | Ch12 | -- |
| Asynchronous frame generation (generación asíncrona de fotogramas) | Desacoplar la producción de fotogramas visuales de la visualización vía un búfer circular. El generador escribe fotogramas por adelantado; la pantalla lee a 50 Hz estables. Absorbe picos de CPU de la reproducción de percusión. | "asynchronous frame generation" | Ch12 | -- |

## F. Notación y directivas de ensamblador

| Term (Término) | Definición | Canonical form | First | Also |
|------|-----------|----------------|-------|------|
| ORG | Directiva del ensamblador que establece la dirección de origen del código. `ORG $8000` para ejemplos del Spectrum. | `ORG` | Ch01 | all code examples |
| EQU | Definir una constante con nombre. `SCREEN EQU $4000`. | `EQU` | Ch02 | all code examples |
| DB / DW / DS | Define Byte / Define Word / Define Space. `DB -3` (valores negativos permitidos en sjasmplus). | `DB`, `DW`, `DS` | Ch04 | all code examples |
| ALIGN | Alinear a un límite de potencia de dos. Directiva de sjasmplus. | `ALIGN` | Ch07 | -- |
| INCLUDE / INCBIN | Incluir archivo fuente / incluir datos binarios. Directivas de sjasmplus. | `INCLUDE` / `INCBIN` | Ch14 | Ch20, Ch21 |
| DEVICE / SLOT / PAGE | Directivas de sjasmplus para emulación de bancos de memoria 128K en tiempo de ensamblaje. | `DEVICE`, `SLOT`, `PAGE` | Ch15 | Ch20, Ch21 |
| DISPLAY | Directiva de sjasmplus que imprime un valor en tiempo de ensamblaje. Diagnósticos en tiempo de compilación. | `DISPLAY` | Ch20 | Ch21 |
| `$FF` | Notación hexadecimal. El prefijo `$` es preferido. `#FF` también aceptado por sjasmplus. | `$FF` | Ch01 | all |
| `%10101010` | Notación binaria. | `%10101010` | Ch01 | all |
| `.label` (etiqueta local) | Etiqueta local, con alcance hasta la etiqueta global más cercana. | `.label` | Ch01 | all |
| sjasmplus | Ensamblador primario (v1.21.1). Conjunto completo de instrucciones Z80/Z80N, macros, scripting Lua, DEVICE/SLOT/PAGE para bancos, INCBIN, múltiples formatos de salida. | "sjasmplus" | Ch01 | Ch14, Ch20, Ch21, Ch23 |

## G. Demoscene y cultura

| Term (Término) | Definición | Canonical form | First | Also |
|------|-----------|----------------|-------|------|
| Compo (compo) | Competición en una demoparty. Las categorías incluyen demo, intro (limitada por tamaño), música, gráficos. | "compo" | Ch13 | Ch20 |
| Demoparty (demoparty) | Evento donde se muestran y juzgan producciones de la demoscene. Fiestas ZX importantes: Chaos Constructions, DiHalt, CAFe, Multimatograf (Rusia); Revision, Forever (Europa occidental). | "demoparty" or "party" | Ch20 | -- |
| NFO / file_id.diz | Archivos de texto incluidos con los lanzamientos de demos que contienen créditos, requisitos, y a veces notas técnicas. | "NFO" / "file_id.diz" | Ch20 | -- |
| Making-of (making-of) | Artículo post-lanzamiento que documenta el proceso de desarrollo y las decisiones técnicas de una demo. Publicado en Hype o en revistas de disco. | "making-of" | Ch12 | Ch20 |
| Part / effect (parte / efecto) | Una sección visual de una demo (túnel, scroller, esfera, etc.). Múltiples partes son secuenciadas por un motor de demo. | "part" or "effect" | Ch09 | Ch12, Ch20 |
| Scripting engine (motor de scripts) | Sistema que secuencia las partes de una demo y las sincroniza con la música. Dos niveles: script externo (secuencia de efectos) + script interno (variación de parámetros dentro de un efecto). | "scripting engine" | Ch09 | Ch12, Ch20 |
| kWORK | Comando de Introspec: "generar N fotogramas, luego mostrarlos independientemente de la generación." El puente entre scripting y generación asíncrona de fotogramas. | "kWORK" | Ch09 | Ch12 |
| Zapilator (zapilator) | Jerga de la escena rusa para una demo "pre-calculadora" -- una que pre-calcula todos los fotogramas antes de la reproducción. Conlleva una leve desaprobación (implica que no hay renderizado en tiempo real). | "zapilator" | Ch09 | -- |

### Personas clave

| Nombre | Rol | Capítulos |
|--------|-----|-----------|
| Dark | Programador, X-Trade. Autor de artículos de programación en Spectrum Expert. Programador de Illusion. | Ch01, Ch04, Ch05, Ch06, Ch07, Ch10 |
| Introspec (spke) | Programador, Life on Mars. Hizo ingeniería inversa de Illusion. Autor de artículos en Hype (análisis técnicos, serie GO WEST, DOWN_HL). Programó la demo Eager. | Ch01--Ch12, Ch15, Ch23 |
| n1k-o | Músico, Skrju. Compuso la banda sonora de Eager. Desarrolló la técnica de tambores digitales híbridos con Introspec. | Ch09, Ch12 |
| diver4d | Programador, 4th Dimension. Demo GABBA (CAFe 2019). Pionero del flujo de trabajo de sincronización con editor de vídeo (Luma Fusion). | Ch09, Ch12 |
| DenisGrachev | Programador. Old Tower, motor GLUF, motor Ringo, Dice Legends. Técnica de encadenamiento RET. | Ch03, Ch08 |
| Robus | Programador. Sistema de threading Z80, demo WAYHACK. | Ch12 |
| sq (psndcj) | Programador. Investigación de optimización de píxeles gruesos (Born Dead #05, Hype). Guía de entorno de desarrollo. | Ch01, Ch07 |
| RST7 | Programador. Optimización de DOWN_HL con doble contador. | Ch02 |

### Demos y producciones clave

| Nombre | Autor/grupo | Año | Capítulos |
|--------|-------------|-----|-----------|
| Illusion | X-Trade (Dark) | 1996 | Ch01, Ch04, Ch05, Ch06, Ch07, Ch10 |
| Eager (to live) | Introspec / Life on Mars | 2015 | Ch02, Ch03, Ch09, Ch10, Ch12 |
| GABBA | diver4d / 4th Dimension | 2019 | Ch12 |
| WAYHACK | Robus | -- | Ch12 |
| Old Tower | DenisGrachev | -- | Ch08 |
| Lo-Fi Motion | -- | -- | Ch20 |

### Publicaciones clave

| Nombre | Descripción | Capítulos |
|--------|-------------|-----------|
| Spectrum Expert (#01--#02) | Revista rusa de disco ZX (1997--98). Tutoriales de programación de Dark. | Ch01, Ch04, Ch05, Ch06, Ch10, Ch11 |
| Hype | Plataforma rusa de la demoscene online (hype.retroscene.org). Artículos técnicos, making-ofs, debates. | Ch01--Ch12, Ch23 |
| Born Dead | Periódico ruso de la demoscene. Investigación de píxeles gruesos de sq (#05, ~2001). | Ch07 |
| Black Crow | Revista rusa de la escena ZX. Documentación temprana de multicolor (#05, ~2001). | Ch08 |

## H. Algoritmos y compresión

| Term (Término) | Definición | Canonical form | First | Also |
|------|-----------|----------------|-------|------|
| Shift-and-add multiply (multiplicación por desplazamiento y suma) | Multiplicación clásica sin signo 8x8. Escanear bits del multiplicador, desplazar y sumar. 196--204 T-states. | "shift-and-add multiply" | Ch04 | Ch05 |
| Square-table multiply (multiplicación por tabla de cuadrados) | AxB = ((A+B)^2-(A-B)^2)/4 vía consulta. ~61 T-states. Intercambia 512 bytes de tablas por velocidad. | "square-table multiply" | Ch04 | Ch05, Ch07 |
| Logarithmic division (división logarítmica) | log(A/B) = log(A)-log(B). Dos consultas de tabla + resta. ~50--70 T-states. Baja precisión. | "logarithmic division" | Ch04 | Ch05 |
| Parabolic sine approximation (aproximación parabólica del seno) | Aproximar seno con parábola y = 1-2(x/pi)^2. Error máx. ~5.6%. Tabla de 256 bytes, con signo. | "parabolic sine approximation" | Ch04 | Ch05, Ch06, Ch09 |
| Bresenham line drawing (dibujo de líneas de Bresenham) | Avanzar a lo largo del eje mayor con acumulador de error para pasos del eje menor. ~80 T-states/píxel ingenuo; ~48 con el método de matriz 8x8 de Dark. | "Bresenham" | Ch04 | -- |
| Midpoint method (método del punto medio) | Rotar completamente solo los vértices base; derivar los vértices restantes promediando. ~36 T-states por vértice derivado vs ~2,400 para rotación completa. | "midpoint method" | Ch05 | -- |
| Fixed-point arithmetic (aritmética de punto fijo) | Representar valores fraccionarios en registros enteros. Formato común: 8.8 (8 bits enteros + 8 bits fraccionarios). | "fixed-point" | Ch04 | Ch05, Ch18, Ch19 |
| AABB collision (colisión AABB) | Test de solapamiento de caja delimitadora alineada a ejes. Cuatro comparaciones: izquierda-derecha y arriba-abajo para dos rectángulos. ~70--156 T-states. | "AABB" | Ch19 | Ch21 |
| Backface culling (eliminación de caras traseras) | Omitir polígonos orientados hacia atrás usando test de componente Z del producto cruzado de la normal. ~500 T-states por cara. | "backface culling" | Ch05 | -- |
| ZX0 | Formato de compresión de Einar Saukas. Excelente tasa de compresión, velocidad de descompresión moderada. | "ZX0" | Ch14 | Ch20 |
| LZ4 | Descompresión rápida (~34 T-states/byte). La opción para streaming en tiempo real. | "LZ4" | Ch14 | -- |
| Exomizer | Compresor de alta tasa para plataformas de 8 bits. Descompresión lenta. | "Exomizer" | Ch14 | -- |
| MegaLZ | Formato de compresión. Buen equilibrio entre tasa y velocidad. | "MegaLZ" | Ch14 | -- |
| hrust1 | Formato de compresión común en la demoscene rusa. | "hrust1" | Ch14 | Ch20 |

---

*Este glosario está extraído de los 23 capítulos de "Coding the Impossible." Para un tratamiento detallado de cualquier término, consulta el capítulo listado bajo "First."*
