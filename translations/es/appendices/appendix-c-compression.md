# Apéndice C: Referencia rápida de compresión

> *"La cuestión no es si comprimir --- es qué compresor usar, y cuándo."*
> -- Capítulo 14

Este apéndice es una tarjeta de referencia desprendible para la compresión de datos en el ZX Spectrum. El Capítulo 14 cubre la teoría, los datos de referencia y el razonamiento detrás de cada recomendación. Este apéndice lo destila en tablas de consulta y reglas de decisión que puedes colgar encima de tu monitor.

Todos los números provienen del benchmark de Introspec de 2017 ("Data Compression for Modern Z80 Coding," Hype) a menos que se indique lo contrario. El corpus de prueba fue de 1,233,995 bytes de datos mixtos: benchmarks académicos Calgary/Canterbury, 30 gráficos de ZX Spectrum, 24 archivos de música y datos misceláneos de demos.

---

## Tabla comparativa de compresores

| Compresor | Autor | Comprimido (bytes) | Tasa | Tamaño descompresor | Velocidad (T/byte) | Hacia atrás | Notas |
|-----------|-------|--------------------|------|---------------------|---------------------|-------------|-------|
| **Exomizer 2** | Magnus Lind | 596,161 | 48.3% | ~170 bytes | ~250 | Sí | Mejor tasa. Lento al descomprimir. |
| **ApLib** | Joergen Ibsen | 606,833 | 49.2% | ~199 bytes | ~105 | No | Buen todoterreno. |
| **Hrust 1** | Alone Coder | 613,602 | 49.7% | ~150 bytes | ~120 | Sí | Desempaquetador reubicable en pila. Popular en la escena rusa. |
| **PuCrunch** | Pasi Ojala | 616,855 | 50.0% | ~200 bytes | ~140 | No | Originalmente para C64. |
| **Pletter 5** | XL2S | 635,797 | 51.5% | ~120 bytes | ~69 | No | Rápido + tasa decente. |
| **MegaLZ** | LVD / Introspec | 636,910 | 51.6% | 92 bytes (compacto) | ~98 (compacto) | No | Analizador óptimo. Revivido en 2019 con nuevos descompresores. |
| **MegaLZ fast** | LVD / Introspec | 636,910 | 51.6% | 234 bytes | ~63 | No | Variante más rápida de MegaLZ. Más rápido que 3x LDIR. |
| **ZX0** | Einar Saukas | ~642,000* | ~52% | ~70 bytes | ~100 | Sí | Sucesor de ZX7. Analizador óptimo. La opción moderna por defecto. |
| **ZX7** | Einar Saukas | 653,879 | 53.0% | **69 bytes** | ~107 | Sí | Descompresor diminuto. La herramienta clásica para sizecoding. |
| **Bitbuster** | Team Bomba | ~660,000* | ~53.5% | ~90 bytes | ~80 | No | Simple. Bueno para primeros proyectos. |
| **LZ4** | Yann Collet (port Z80) | 722,522 | 58.6% | ~100 bytes | **~34** | No | Descompresión más rápida. Tokens alineados a byte. |
| **Hrum** | Hrumer | ~642,000* | ~52% | ~130 bytes | ~110 | No | Popular en la escena rusa. Declarado obsoleto por Introspec. |
| **ZX1** | Einar Saukas | --- | ~51% | ~80 bytes | ~90 | Sí | Variante de ZX0. Tasa ligeramente mejor, descompresor ligeramente más grande. |
| **ZX2** | Einar Saukas | --- | ~50% | ~100 bytes | ~85 | Sí | Usado en la intro RED REDUX 256b (2025). Mejor tasa ZXn. |

\* Aproximado. ZX0, Bitbuster y Hrum no estaban en el benchmark original de 2017; los valores son estimaciones de pruebas independientes en corpus similares.

**Lectura de la tabla:**

- **Tasa** = tamaño comprimido / tamaño original. Más bajo es mejor.
- **Velocidad** = T-states por byte de salida durante la descompresión. Más bajo es más rápido.
- **Tamaño descompresor** = bytes de código Z80 necesarios para la rutina de descompresión. Más bajo es mejor para intros con código limitado por tamaño.
- **Hacia atrás** = soporta descompresión de fin a inicio, permitiendo descompresión in-situ cuando el origen y destino se solapan.

---

## Árbol de decisión: Qué compresor?

Sigue de arriba abajo. Toma la primera rama que coincida con tu situación.

```
INICIO
  |
  +-- Es una intro de 256 o 512 bytes?
  |     SÍ --> ZX0 (descompresor de 70 bytes) o RLE personalizado (<30 bytes)
  |
  +-- Es una intro de 1K o 4K?
  |     SÍ --> ZX0 (mejor relación tasa/tamaño de descompresor)
  |
  +-- Necesitas streaming en tiempo real (descomprimir durante la reproducción)?
  |     SÍ --> LZ4 (~34 T/byte = 2+ KB por fotograma a 50fps)
  |
  +-- Necesitas descompresión rápida entre escenas?
  |     SÍ --> MegaLZ fast (~63 T/byte) o Pletter 5 (~69 T/byte)
  |
  +-- La velocidad de descompresión es irrelevante (carga única al inicio)?
  |     SÍ --> Exomizer (tasa del 48.3%, nada lo supera)
  |
  +-- Necesitas un buen equilibrio entre tasa y velocidad?
  |     SÍ --> ApLib (~105 T/byte, tasa del 49.2%)
  |
  +-- Los datos son mayormente series de bytes idénticos?
  |     SÍ --> RLE personalizado (descompresor < 30 bytes, trivial)
  |
  +-- Los datos son fotogramas de animación secuenciales?
  |     SÍ --> Codifica en delta primero, luego comprime con ZX0 o LZ4
  |
  +-- Primer proyecto, quieres algo simple?
        SÍ --> Bitbuster o ZX0 (ambos bien documentados, fáciles de integrar)
```

---

## Compresibilidad de tipos de datos comunes del ZX Spectrum

Qué tan bien comprimen los diferentes tipos de datos, y trucos para mejorar la tasa.

| Tipo de datos | Tamaño crudo | Tasa típica ZX0 | Tasa típica Exomizer | Notas |
|---------------|--------------|-----------------|----------------------|-------|
| **Píxeles de pantalla** ($4000-$57FF) | 6,144 bytes | 40--60% | 35--55% | Depende de la complejidad de la imagen. Los fondos negros comprimen bien. |
| **Atributos** ($5800-$5AFF) | 768 bytes | 30--50% | 25--45% | A menudo muy repetitivos. Las áreas de color sólido comprimen a casi nada. |
| **Pantalla completa** (píxeles + attrs) | 6,912 bytes | 40--58% | 35--52% | Comprime píxeles y atributos por separado para una tasa 5--10% mejor. |
| **Tablas de seno/coseno** | 256 bytes | 60--75% | 55--70% | Las curvas suaves comprimen bien. Considera la generación en su lugar (Apéndice B). |
| **Datos de baldosas** (baldosas de 8x8) | varía | 35--55% | 30--50% | Reordena baldosas por similitud para mejor tasa. |
| **Datos de sprites** | varía | 45--65% | 40--60% | Los bytes de máscara perjudican la tasa. Almacena las máscaras por separado. |
| **Datos de música PT3** | varía | 40--55% | 35--50% | Los datos de patrón son repetitivos. Las filas vacías comprimen bien. |
| **Volcados de registros AY** | varía | 30--50% | 25--45% | Muy repetitivos entre fotogramas. Codifica en delta primero. |
| **Tablas de consulta** (arbitrarias) | varía | 50--80% | 45--75% | Los datos de aspecto aleatorio comprimen mal. Pre-ordena si es posible. |
| **Datos de fuente** (96 chars x 8 bytes) | 768 bytes | 55--70% | 50--65% | Muchos bytes cero (descendentes, trazos finos). |

### Trucos de pre-compresión

Estas técnicas mejoran la tasa de compresión reestructurando los datos antes de pasarlos al compresor.

**Separar píxeles de atributos.** Una pantalla completa de 6,912 bytes almacenada como un solo bloque fuerza al compresor a manejar una transición de datos de píxeles a datos de atributos en el byte 6,144. Comprime el bloque de 6,144 bytes de píxeles y el bloque de 768 bytes de atributos por separado. El bloque de atributos, siendo muy repetitivo, a menudo comprime a menos de 200 bytes.

**Codificar fotogramas de animación en delta.** Almacena el primer fotograma completo. Para cada fotograma subsiguiente, almacena solo los bytes que difieren del fotograma anterior como pares (desplazamiento, valor). Aplica compresión LZ al flujo de deltas. psndcj comprimió 122 fotogramas (843,264 bytes crudos) en 10,512 bytes usando esta técnica en Break Space.

**Reordenar datos por localidad.** Los mapas de baldosas almacenados en orden fila-mayor pueden comprimir mejor si se reordenan para que baldosas similares sean adyacentes. Ordena los fotogramas de sprites por similitud visual. Agrupa sub-patrones repetidos juntos.

**Almacenar constantes por separado.** Si un bloque de datos contiene una cabecera o pie de página repetido (p. ej., metadatos de baldosas), factorízalo y almacénalo una vez. Comprime solo la parte variable.

**Intercalar planos.** Para sprites multicolor o con máscara, almacenar todos los bytes de máscara juntos y todos los bytes de píxeles juntos a menudo comprime mejor que intercalar máscara-píxel-máscara-píxel por fila.

---

## Descompresor RLE mínimo

El compresor útil más simple. Menos de 30 bytes. Adecuado para intros de 256 bytes o datos con largas series de bytes idénticos. Consulta el Capítulo 14 para una discusión completa.

```z80
; Minimal RLE decompressor
; Format: [count][value] pairs, terminated by count = 0
; HL = source (compressed data)
; DE = destination (output buffer)
; Destroys: AF, BC
rle_decompress:
        ld      a, (hl)         ; read count             7T
        inc     hl              ;                         6T
        or      a               ; count = 0?              4T
        ret     z               ; yes: done               5T/11T
        ld      b, a            ; B = count               4T
        ld      a, (hl)         ; read value              7T
        inc     hl              ;                         6T
.fill:  ld      (de), a         ; write value             7T
        inc     de              ;                         6T
        djnz    .fill           ; loop B times            13T/8T
        jr      rle_decompress  ; next pair               12T
; Total: 23 bytes of code
; Speed: ~26 T-states per output byte (within runs)
```

**Herramienta de codificación** (una línea en Python para RLE simple):

```python
def rle_encode(data):
    out = bytearray()
    i = 0
    while i < len(data):
        val = data[i]
        count = 1
        while i + count < len(data) and data[i + count] == val and count < 255:
            count += 1
        out.extend([count, val])
        i += count
    out.extend([0])  # terminator
    return out
```

Este RLE ingenuo expande datos sin series (peor caso: 2 bytes por 1 byte de entrada). Para datos mixtos, usa RLE con byte de escape: un byte especial señala una serie, y todos los demás bytes son literales. O simplemente usa ZX0.

---

## Descompresor estándar ZX0 (Z80)

El descompresor estándar directo completo por Einar Saukas. Aproximadamente 70 bytes. Esta es la versión que usarás en la mayoría de proyectos.

```z80
; ZX0 decompressor - standard forward version
; (c) Einar Saukas, based on Wikipedia description of LZ format
; HL = source (compressed data)
; DE = destination (output buffer)
; Destroys: AF, BC, DE, HL
dzx0_standard:
        ld      bc, $ffff       ; initial offset = -1
        push    bc              ; store offset on stack
        inc     bc              ; BC = 0 (literal length will be read)
        ld      a, $80          ; init bit buffer with end marker
dzx0s_literals:
        call    dzx0s_elias     ; read number of literals
        ldir                    ; copy literals from source to dest
        add     a, a            ; read next bit: 0 = last offset, 1 = new offset
        jr      c, dzx0s_new_offset
        ; reuse last offset
        call    dzx0s_elias     ; read match length
dzx0s_copy:
        ex      (sp), hl        ; swap: HL = offset, stack = source
        push    hl              ; put offset back on stack
        add     hl, de          ; HL = dest + offset = match source address
        ldir                    ; copy match
        add     a, a            ; read next bit: 0 = literal, 1 = match/offset
        jr      nc, dzx0s_literals
        ; new offset
dzx0s_new_offset:
        call    dzx0s_elias     ; read offset MSB (high bits)
        ex      af, af'         ; save bit buffer
        dec     b               ; B = $FF (offset is negative)
        rl      c               ; C = offset MSB * 2 + carry
        inc     c               ; adjust
        jr      z, dzx0s_done   ; offset = 256 means end of stream
        ld      a, (hl)         ; read offset LSB
        inc     hl
        rra                     ; LSB bit 0 -> carry = length bit
        push    bc              ; save offset MSB
        ld      b, 0
        ld      c, a            ; C = offset LSB >> 1
        pop     af              ; A = offset MSB (from push bc)
        ld      b, a            ; BC = full offset (negative)
        ex      (sp), hl        ; store offset, retrieve source
        push    bc              ; store offset again
        ld      bc, 1           ; minimum match length = 1
        jr      nc, dzx0s_copy  ; if carry clear: length = 1
        call    dzx0s_elias     ; otherwise read match length
        inc     bc              ; +1
        jr      dzx0s_copy
dzx0s_done:
        pop     hl              ; clean stack
        ex      af, af'         ; restore flags
        ret
; Elias interlaced code reader
dzx0s_elias:
        inc     c               ; C starts at 1
dzx0s_elias_loop:
        add     a, a            ; read bit
        jr      nz, dzx0s_elias_nz
        ld      a, (hl)         ; refill bit buffer
        inc     hl
        rla                     ; shift in carry
dzx0s_elias_nz:
        ret     nc              ; stop bit (0) = done
        add     a, a            ; read data bit
        jr      nz, dzx0s_elias_nz2
        ld      a, (hl)         ; refill
        inc     hl
        rla
dzx0s_elias_nz2:
        rl      c               ; shift bit into C
        rl      b               ; and into B
        jr      dzx0s_elias_loop
```

**Uso:**

```z80
        ld      hl, compressed_data     ; source address
        ld      de, $4000               ; destination (e.g., screen)
        call    dzx0_standard           ; decompress
```

**Variante hacia atrás.** ZX0 también proporciona un descompresor hacia atrás (`dzx0_standard_back`) que lee datos comprimidos de fin a inicio y escribe la salida de fin a inicio. Esto permite la descompresión in-situ: coloca los datos comprimidos al final del búfer de destino, y descomprime hacia atrás para que la salida sobrescriba los datos comprimidos solo después de haberlos leído. Esencial cuando la RAM es escasa.

---

## Patrones de integración

### Patrón 1: Descomprimir a pantalla al inicio

El caso de uso más común. Cargar una pantalla de carga comprimida y mostrarla.

```z80
        org     $8000
start:
        ld      hl, compressed_screen
        ld      de, $4000               ; screen memory
        call    dzx0_standard
        ; screen is now visible
        ; ... continue with demo/game ...

        include "dzx0_standard.asm"

compressed_screen:
        incbin  "screen.zx0"
```

### Patrón 2: Descomprimir a búfer entre efectos

Descomprime los datos del siguiente efecto en un búfer auxiliar mientras el efecto actual sigue en ejecución, o durante un fundido de salida.

```z80
; During scene transition:
        ld      hl, scene2_data_zx0
        ld      de, scratch_buffer      ; e.g., $C000 in bank 1
        call    dzx0_standard
        ; scratch_buffer now holds the uncompressed data
        ; switch to scene 2, which reads from scratch_buffer
```

### Patrón 3: Descompresión en streaming durante la reproducción

Para efectos en tiempo real que necesitan un flujo continuo de datos. LZ4 es la única opción práctica aquí.

```z80
; Each frame: decompress next chunk
frame_loop:
        ld      hl, (lz4_read_ptr)     ; current position in compressed stream
        ld      de, frame_buffer
        ld      bc, 2048                ; bytes to decompress this frame
        call    lz4_decompress_partial
        ld      (lz4_read_ptr), hl     ; save position for next frame
        ; render from frame_buffer
        ; ...
        jr      frame_loop
```

A ~34 T/byte, LZ4 descomprime 2,048 bytes en 69,632 T-states --- cabe dentro de un fotograma (69,888 T-states en 48K). Es ajustado. Usa descompresión durante tiempo de borde o doble búfer por seguridad.

### Patrón 4: Datos comprimidos con conmutación de bancos (128K)

Almacena datos comprimidos a través de múltiples bancos de 16KB. Descomprime desde el banco actualmente paginado, luego cambia de banco cuando se agote.

```z80
; Page in bank containing compressed data
        ld      a, (current_bank)
        or      $10                     ; bit 4 = ROM select
        ld      bc, $7ffd
        out     (c), a                  ; page bank into $C000-$FFFF

        ld      hl, $C000              ; compressed data starts at bank base
        ld      de, dest_buffer
        call    dzx0_standard

        ; Page next bank for next asset
        ld      a, (current_bank)
        inc     a
        ld      (current_bank), a
```

Para demos grandes con muchos recursos comprimidos, mantén una tabla de tuplas (banco, desplazamiento, destino) y recórrelas durante la carga.

---

## Pipeline de construcción: del recurso al binario

El paso de compresión pertenece a tu Makefile, no a tu cabeza.

```
Recurso fuente     Convertidor      Compresor         Ensamblador
  (PNG)       -->   (png2scr)   -->   (zx0)      -->  (sjasmplus)  --> .tap
  (WAV)       -->   (pt3tools)  -->   (zx0)      -->  (incbin)
  (TMX)       -->   (tmx2bin)   -->   (exomizer)
```

**Reglas de Makefile:**

```makefile
# Compress .scr screens with ZX0
%.zx0: %.scr
	zx0 $< $@

# Compress large assets with Exomizer (one-time load)
%.exo: %.bin
	exomizer raw -c $< -o $@

# Build final binary
demo.bin: main.asm assets/title.zx0 assets/font.zx0
	sjasmplus main.asm --raw=$@
```

**Instalación de herramientas:**

| Herramienta | Fuente | Instalación |
|-------------|--------|-------------|
| ZX0 | github.com/einar-saukas/ZX0 | `gcc -O2 -o zx0 src/zx0.c src/compress.c src/optimize.c src/memory.c` |
| Exomizer | github.com/bitmanipulators/exomizer | `make` en el directorio `src/` |
| LZ4 | github.com/lz4/lz4 | `make` o `brew install lz4` |
| MegaLZ | github.com/AntonioCerra/megalzR | Más antiguo; consulta el artículo de Introspec en Hype para enlaces |

---

## Fórmulas rápidas

**Bytes por fotograma a 50fps con el descompresor X:**

```
bytes_por_fotograma = 69,888 / velocidad_t_por_byte
```

| Compresor | T/byte | Bytes/fotograma (48K) | Bytes/fotograma (128K Pentagon) |
|-----------|--------|----------------------|---------------------------------|
| LZ4 | 34 | 2,055 | 2,108 |
| MegaLZ fast | 63 | 1,109 | 1,138 |
| Pletter 5 | 69 | 1,012 | 1,038 |
| ZX0 | 100 | 698 | 716 |
| ApLib | 105 | 665 | 682 |
| Hrust 1 | 120 | 582 | 597 |
| Exomizer | 250 | 279 | 286 |

(Fotograma de 128K Pentagon = 71,680 T-states)

**Memoria ahorrada por compresión en N pantallas:**

```
ahorrado = N * 6912 * (1 - tasa)
```

Ejemplo: 8 pantallas de carga con Exomizer al 48.3% de tasa ahorran 8 * 6912 * 0.517 = 28,575 bytes --- casi dos bancos completos de 16KB.

---

## Ver también

- **Capítulo 14:** Discusión completa de la teoría de compresión, el benchmark de Introspec, las interioridades de ZX0, y el pipeline delta + LZ.
- **Apéndice B:** Generación de tablas de seno --- cuando las tablas son lo suficientemente pequeñas, considera generar en lugar de comprimir.
- **Apéndice A:** Referencia de instrucciones Z80 --- LDIR, PUSH/POP, y otras instrucciones usadas en descompresores.

> **Fuentes:** Introspec "Data Compression for Modern Z80 Coding" (Hype, 2017); Introspec "Compression on the Spectrum: MegaLZ" (Hype, 2019); Einar Saukas, ZX0/ZX7/ZX1/ZX2 (github.com/einar-saukas); Break Space NFO (Thesuper, 2016)
