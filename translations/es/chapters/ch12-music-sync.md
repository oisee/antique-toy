# Capítulo 12: Tambores digitales y sincronización musical

> *"Mi cerebro no está sobrellevando bien la programación asíncrona."*
> -- Introspec, file_id.diz de la versión de fiesta de Eager (to live), 3BM Open Air 2015

---

Una demo no es una presentación de diapositivas con efectos. Una demo es una actuación -- una donde cada evento visual cae en el tiempo del ritmo, cada transición respira con la música, y la audiencia nunca sospecha que detrás del telón, un procesador de 3,5MHz está haciendo malabares con media docena de demandas en competencia sin sistema operativo, sin hilos y sin red de seguridad.

Este capítulo trata sobre la arquitectura que hace posible ese acto de malabarismo. Hemos pasado los capítulos anteriores construyendo efectos individuales -- túneles, zoomers, scrollers, animaciones de color -- y en el Capítulo 11 aprendimos cómo el chip AY produce música. Ahora debemos conectar todo. Las preguntas ya no son "¿cómo dibujo un túnel?" o "¿cómo toco una nota?" sino más bien: ¿Cómo reproduzco una muestra de tambor que consume casi toda la CPU manteniendo los gráficos fluidos? ¿Cómo sincronizo los cambios de efecto con el ritmo de la música? ¿Cómo estructuro una demo de dos minutos para que funcione de manera fiable de principio a fin?

Las respuestas vienen de tres fuentes. Eager de Introspec (2015) nos da síntesis de tambores digitales y generación asíncrona de fotogramas. GABBA de diver4d (2019) muestra un enfoque radicalmente diferente para la sincronización musical usando un editor de vídeo como herramienta de línea de tiempo. Y el sistema de hilos de Robus (2015) demuestra que el multihilo honesto en el Z80 es posible, aunque raramente necesario.

Juntas, estas tres técnicas representan el pensamiento arquitectónico que separa una colección de efectos de una demo terminada.

---

## 12.1 Tambores digitales en el AY

### El problema: El AY no puede reproducir muestras

El AY-3-8910, como cubrimos en el Capítulo 11, es un sintetizador. Genera ondas cuadradas, ruido y formas de envolvente. No tiene capacidad de reproducción de muestras, ni DAC, ni RAM de forma de onda. Cada sonido que produce se construye a partir de esas fuentes primitivas en tiempo real. Si quieres un bombo realista -- del tipo con un ataque transiente punzante seguido de un decaimiento resonante -- el generador de ruido y la envolvente del AY pueden aproximarlo, pero el resultado suena inconfundiblemente sintético. Le falta el peso de un golpe percusivo real.

Pero hay una puerta trasera.

Los registros R8, R9 y R10 controlan el volumen de los canales A, B y C. Cada uno es un valor de 4 bits (0-15). Si escribes en un registro de volumen una vez por fotograma, obtienes un nivel de volumen estático. Pero ¿qué pasa si escribes miles de veces por fotograma? ¿Qué pasa si tratas el registro de volumen como un DAC crudo de 4 bits y le alimentas valores sucesivos de muestra de una grabación digitalizada?

Obtienes reproducción PCM. Cruda, ruidosa, de 4 bits, pero reconocible. El AY se convierte en un reproductor de muestras -- no por diseño, sino por fuerza bruta.

### El coste: Aniquilación de CPU

Aquí está el problema. Para reproducir una muestra de tambor digitalizada con cualquier calidad razonable, necesitas actualizar el registro de volumen a tasas de audio. Una tasa de muestreo de 8 kHz significa una actualización cada 125 microsegundos. A 3,5 MHz, 125 microsegundos son aproximadamente 437 T-states. Eso es ajustado pero factible -- puedes hacer trabajo útil en los huecos entre escrituras de muestra.

Pero 8 kHz suena terrible. Para un bombo contundente, quieres al menos la percepción de mayor fidelidad. Y aquí la economía colapsa. A tasas de muestreo efectivas más altas, necesitas una interrupción o un bucle de sondeo cerrado que se dispare cada 125-250 T-states. A esa frecuencia, casi no queda tiempo de CPU para nada más. Mientras la muestra de tambor se reproduce, el procesador es un motor de reproducción de audio dedicado. La generación de vídeo, el scripting, el manejo de entrada -- todo se detiene.

Una muestra típica de bombo dura 20-40 milisegundos para la porción crítica del ataque. A 50 Hz, eso es 1-2 fotogramas. Durante esos fotogramas, la CPU desaparece.

### La idea de n1k-o: El tambor híbrido

n1k-o, el músico detrás de la banda sonora de Eager, encontró la solución. La observación clave: un sonido de tambor tiene dos fases distintas. El **ataque** -- el transiente inicial, el "clic" o "golpe" agudo que le da al bombo su contundencia -- es corto, complejo e imposible de sintetizar de forma convincente en el AY. Pero el **decaimiento** -- la cola resonante que sigue -- es una caída suave de volumen, exactamente el tipo de cosa que el generador de envolvente del AY maneja naturalmente.

El enfoque híbrido: reproducir el ataque como una muestra digital (consumiendo tiempo de CPU durante 1-2 fotogramas), luego pasar al generador de envolvente del AY para el decaimiento (consumiendo cero tiempo de CPU, ya que el hardware hace el trabajo automáticamente). Ataque digital más decaimiento AY equivale a un sonido de tambor que tiene el golpe realista de una muestra y la cola suave de la síntesis por hardware.

En la práctica, la implementación funciona así:

```z80
; Play hybrid kick drum
; 1. Start digital sample playback for attack phase
; 2. When sample ends, configure AY envelope for decay

play_kick_drum:
    di                        ; disable interrupts -- timing critical

    ; --- Digital attack phase ---
    ; Play ~800 samples at ~8kHz = ~100ms = ~2 frames
    ld   hl, kick_sample      ; pointer to 4-bit sample data
    ld   b, 0                 ; 256 samples per loop pass
    ld   c, $FD               ; low byte of AY data port ($BFFD)

    ; Select volume register R8 (channel A)
    ld   a, 8
    ld   bc, $FFFD
    out  (c), a               ; select R8
    ld   c, $FD               ; prepare for $BFFD writes

.sample_loop:
    ld   a, (hl)              ; 7 T  - load sample byte
    inc  hl                   ; 6 T  - advance pointer
    ld   b, $BF               ; 7 T  - high byte of $BFFD
    out  (c), a               ; 12 T - write volume = sample value
    ; ... timing padding to hit target sample rate ...
    djnz .sample_loop         ; 13 T (approx 45 T per sample)

    ; --- AY decay phase ---
    ; Configure envelope for smooth volume decay
    ; The AY takes over -- zero CPU cost from here

    ld   a, R_ENV_LO
    ld   e, 200               ; envelope period: moderate decay speed
    call ay_write
    ld   a, R_ENV_HI
    ld   e, 0
    call ay_write
    ld   a, R_ENV_SHAPE
    ld   e, $00               ; \___  single decay to silence
    call ay_write
    ld   a, R_VOL_A
    ld   e, $10               ; switch channel A to envelope mode
    call ay_write

    ei
    ret

kick_sample:
    ; 4-bit PCM data: attack portion of a kick drum
    ; Each byte = one sample, value 0-15
    DB 0, 2, 8, 15, 14, 12, 15, 13
    DB 10, 14, 11, 8, 12, 9, 6, 10
    ; ... (typically 400-800 bytes for the full attack)
```

Los datos de la muestra en sí -- esos 400-800 bytes de PCM de 4 bits -- provienen de una grabación real de tambor, submuestreada y cuantizada a 4 bits. El transiente de ataque preserva el carácter del instrumento original: la maza golpeando el parche, la compresión inicial del aire, el inicio agudo que nuestros oídos usan para identificar el sonido. La envolvente del AY luego proporciona un decaimiento limpio y suave que nuestros oídos aceptan como la resonancia natural del cuerpo del tambor.

El resultado es sorprendentemente convincente. En un chip que no tiene ninguna capacidad de reproducción de muestras, escuchas algo que suena como un bombo real. No calidad de estudio, ni siquiera calidad Amiga, pero mundos mejor que la síntesis pura del AY.

### El presupuesto de fotograma: Dos fotogramas por golpe

El coste por fotograma es concreto: dos fotogramas por golpe de tambor. Durante estos fotogramas, aproximadamente 140.000 T-states (dos períodos completos de fotograma en Pentagon) son consumidos por el bucle de reproducción de muestras. La CPU no hace nada más. La pantalla continúa mostrando lo que estaba en la memoria de pantalla, pero no se generan nuevos fotogramas. No se procesan datos musicales (el tambor ES la música durante esos dos fotogramas). No se ejecuta ningún motor de scripts.

Dos fotogramas a 50 Hz son 40 milisegundos. Para una pista musical con bombos en el tiempo a 130 BPM, eso es aproximadamente un golpe de tambor cada 23 fotogramas. Dos fotogramas de cada 23 consumidos por la reproducción de tambor -- alrededor del 9% del tiempo total de CPU, entregado en ráfagas agudas que monopolizan completamente el procesador.

Este es el desafío arquitectónico que impulsa el resto del capítulo. ¿Cómo mantienes los gráficos funcionando suavemente cuando el audio roba la CPU durante dos fotogramas seguidos, de forma impredecible, docenas de veces por minuto?

---

## 12.2 Generación asíncrona de fotogramas

### El enfoque ingenuo falla

La arquitectura de demo más simple es síncrona: genera un fotograma del efecto visual, espera HALT (vsync), muéstralo. Genera el siguiente fotograma, HALT, muéstralo. Esto es lo que construimos en cada ejercicio práctico hasta ahora. Funciona perfectamente cuando la generación de fotograma toma menos de un período de fotograma.

Ahora añade tambores digitales. El motor de música señala: "reproduce bombo en el próximo tiempo." La rutina de reproducción de muestras se apodera de la CPU durante dos fotogramas. Durante esos dos fotogramas, no se generan nuevos fotogramas de vídeo. Cuando el tambor termina, la pantalla ha estado mostrando el mismo fotograma durante tres refrescos (el último fotograma generado se mostró una vez normalmente, luego dos veces durante el golpe de tambor). El efecto visual tartamudea.

Con un golpe de tambor cada 23 fotogramas, la audiencia ve un breve congelamiento cada medio segundo. Es notable. Es feo. Es inaceptable para una demo de competición.

### La solución de Introspec: Acumular fotogramas

La arquitectura de Introspec en Eager desacopla la generación de fotogramas de la visualización de fotogramas. El motor visual no genera un fotograma e inmediatamente lo muestra. En su lugar, genera fotogramas en un búfer -- tantos como puede -- y el sistema de visualización los muestra a una tasa constante de 50 Hz independientemente de lo que el generador esté haciendo.

El mecanismo es fotogramas de atributos con doble búfer. Dos páginas de datos de atributos existen en memoria. Mientras una página se muestra (la ULA lee de ella durante el refresco de pantalla), el generador escribe el siguiente fotograma en la otra página. Cuando un nuevo fotograma está listo, el motor intercambia las páginas: el fotograma recién generado se convierte en la página de visualización, y la vieja página de visualización se convierte en el nuevo objetivo de generación.

```
Time ──────────────────────────────────────────────────►

Display:   [Frame 1] [Frame 2] [Frame 3] [Frame 4] [Frame 5]
Generator: ──gen F2──|──gen F3──|──gen F4──|── DRUM ──|──gen F5──
                                           ↑          ↑
                                      drum starts  drum ends

During the drum hit, the display shows Frame 4 (already generated).
Frame 5 generation resumes immediately after the drum finishes.
```

Pero el doble búfer simple solo te da un fotograma de holgura. Si el tambor consume dos fotogramas, necesitas haber generado dos fotogramas por adelantado. Aquí es donde la generación asíncrona de Introspec verdaderamente diverge del doble búfer simple: el motor puede **acumular** múltiples fotogramas por adelantado.

En el Spectrum 128K, la conmutación de bancos de memoria proporciona el espacio. Los fotogramas de atributos son pequeños -- 768 bytes cada uno. Una sola página de 16KB puede contener aproximadamente 20 fotogramas de atributos. El generador funciona tan rápido como puede, escribiendo fotograma tras fotograma en el búfer. El sistema de visualización lee del búfer a un ritmo constante de 50 Hz. Cuando el generador es más rápido que el tiempo real (lo cual suele ser el caso, ya que el plasma de atributos es barato), el búfer se llena. Cuando un golpe de tambor pausa la generación, el sistema de visualización consume del búfer. Mientras el búfer no se vacíe, la audiencia ve una animación suave a 50 Hz.

### La dinámica del búfer

Piensa en esto como un problema de productor-consumidor, pero en una máquina sin concurrencia.

El **productor** es el generador de efectos de plasma/túnel/zoomer. Produce fotogramas de atributos a una tasa variable -- a veces más rápido que 50 Hz (cuando el cálculo es simple y no se están reproduciendo tambores), a veces cero (durante la reproducción de tambores).

El **consumidor** es el sistema de visualización, leyendo un fotograma por refresco de pantalla a exactamente 50 Hz.

El **búfer** se sitúa entre ellos, absorbiendo la diferencia.

La dinámica es directa:

- **Entre golpes de tambor:** El generador funciona más rápido que la visualización. El búfer se llena. Si alcanza la capacidad, el generador descansa (o el motor avanza el estado del script).
- **Durante un golpe de tambor:** El generador se detiene. La visualización drena el búfer a 50 Hz. Un golpe de tambor de dos fotogramas consume dos fotogramas del búfer.
- **Después de un golpe de tambor:** El generador reanuda, funcionando tan rápido como es posible para rellenar el búfer antes del próximo golpe.

La restricción crítica: **el búfer nunca debe vaciarse durante un golpe de tambor.** Si dos golpes de tambor ocurren en rápida sucesión -- digamos, un patrón bombo-caja con dos fotogramas de separación -- el búfer necesita al menos cuatro fotogramas de reserva. El motor de scripts de Introspec gestiona esto conociendo la línea de tiempo musical de antemano. Cuando se acerca un pasaje denso de percusión, el motor genera fotogramas extra para acolchar el búfer. Cuando sigue un pasaje tranquilo, el búfer se llena naturalmente.

La trampa: si el patrón de percusión es demasiado denso -- demasiados golpes demasiado cerca -- el generador no puede mantener el ritmo. El búfer se vacía, y la visualización repite un fotograma. Esta es una restricción dura de la arquitectura, y esto influyó en la composición de n1k-o. La música fue escrita con conocimiento de la capacidad del motor: los golpes de tambor están espaciados lo suficientemente lejos como para que el generador siempre pueda recuperarse. El músico y el programador diseñaron juntos, cada uno entendiendo las restricciones del otro.

---

## 12.3 El motor de scripts

### Por qué necesitas un script

A estas alturas, la lista de cosas que necesitan coordinación es larga:

- El generador de efecto visual (qué efecto está activo, qué parámetros usa)
- El reproductor de música (qué patrón se está reproduciendo, cuándo se disparan los tambores)
- El búfer de fotogramas (qué tan lleno está, cuándo generar más)
- Las transiciones entre efectos (desvanecer uno, aparecer el siguiente)
- La línea de tiempo general (la demo dura dos minutos -- qué sucede cuándo)

Podrías codificar todo esto en un bucle principal monolítico. Algunas demos lo hacen. Pero Introspec eligió un camino diferente: un sistema de scripts de dos niveles que separa *qué sucede* de *cuándo sucede*.

### Script externo: La secuencia de efectos

El script externo es una secuencia lineal de comandos que controlan la estructura general de la demo. Piensa en ello como un setlist para un concierto:

```
; Outer script (conceptual, not exact syntax)
EFFECT  tunnel, params_set_1     ; start the tunnel effect
WAIT    200                       ; run for 200 frames (4 seconds)
EFFECT  zoomer, params_set_1     ; switch to chaos zoomer
WAIT    150                       ; 3 seconds
EFFECT  tunnel, params_set_2     ; tunnel again, different colours
WAIT    250                       ; 5 seconds
; ... and so on for the full demo
```

Cada comando `EFFECT` carga la función generadora y su bloque de parámetros. Cada `WAIT` le dice al motor cuántos fotogramas ejecutar el efecto actual antes de avanzar al siguiente comando. Las transiciones entre efectos -- fundidos cruzados, cortes duros, barridos de color -- son ellas mismas programadas como efectos.

### Script interno: Variaciones dentro de un efecto

Dentro de un solo efecto, los parámetros cambian con el tiempo. Las frecuencias de plasma del túnel cambian, la paleta de colores rota, la velocidad del zoom acelera. Estas variaciones son controladas por el script interno -- una secuencia por efecto de cambios de parámetros indexados a números de fotograma:

```
; Inner script for tunnel effect (conceptual)
FRAME  0:   plasma_freq = 3, palette = warm
FRAME  50:  plasma_freq = 5                   ; frequency shift
FRAME  100: palette = cool                     ; colour change
FRAME  120: plasma_freq = 2, palette = hot     ; both change
```

El script interno se ejecuta independientemente del script externo. Cuando el script externo dice "ejecutar túnel durante 200 fotogramas", el script interno maneja la evolución visual dentro de esos 200 fotogramas.

### kWORK: El comando clave

El comando más importante en el sistema de scripts es lo que Introspec llama **kWORK**: "genera N fotogramas, luego muéstralos independientemente de la generación." Este único comando es el puente entre el sistema de scripts y la arquitectura asíncrona.

Cuando el motor encuentra `kWORK 8`, este:

1. Genera 8 fotogramas del efecto actual en el búfer de fotogramas.
2. Entrega esos fotogramas al sistema de visualización.
3. Mientras el sistema de visualización los muestra (durante 8/50 = 160ms), el motor es libre de hacer otro trabajo: procesar el siguiente comando del script, preparar el siguiente lote, o ceder tiempo de CPU para la reproducción de tambores.

Este desacoplamiento -- generar ahora, mostrar después -- es el habilitador fundamental de la operación asíncrona. Sin kWORK, el motor estaría bloqueado en un ciclo síncrono generar-mostrar-generar-mostrar sin holgura para interrupciones de tambor.

En la práctica, el motor llama a kWORK repetidamente, generando pequeños lotes de fotogramas (4-8 a la vez). Entre lotes, verifica si hay un disparo de tambor pendiente. Si lo hay, deja que el tambor suene, sabiendo que el sistema de visualización tiene suficientes fotogramas en el búfer para continuar suavemente. Después de que el tambor termina, genera el siguiente lote para reponer el búfer.

```z80
; Simplified engine loop (conceptual)
engine_loop:
    ; Check if drum is pending
    ld   a, (drum_pending)
    or   a
    jr   z, .no_drum
    call play_drum            ; consumes 2 frames of CPU time
    xor  a
    ld   (drum_pending), a

.no_drum:
    ; Generate a batch of frames
    call generate_batch       ; kWORK: produce N frames into buffer
    ; (generate_batch returns when batch is done)

    ; Check outer script for effect changes
    call advance_script

    jr   engine_loop
```

La belleza de esta arquitectura es su simplicidad a nivel macro. El motor es un bucle: verificar tambores, generar fotogramas, avanzar el script. Toda la complejidad está dentro de `generate_batch` (que gestiona el búfer, maneja el cálculo de plasma y escribe datos de atributos) y `play_drum` (que ejecuta la rutina de muestra digital de la sección 12.1). El sistema de scripts proporciona la secuenciación; el búfer proporciona el desacoplamiento temporal; la rutina de tambor proporciona el impacto audio. Cada componente tiene una responsabilidad clara.

---

## 12.4 La innovación de GABBA: El editor de vídeo como herramienta de línea de tiempo

En 2019, diver4d (de 4D+TBK) obtuvo el primer lugar en CAFe con GABBA, una demo temática de gabber con una sincronización audiovisual brutalmente precisa. La sincronización era tan exacta que cada golpe visual aterrizaba exactamente en el pulso musical, cada transición coincidía con un límite de frase, y toda la producción se sentía como un videoclip en lugar de una demo.

La sorpresa técnica estaba en el flujo de trabajo, no en el código.

### El problema con la sincronización basada en código

El enfoque tradicional para la sincronización musical en demos de ZX es incrustar datos de temporización en el código. Sabes que el bombo golpea en el fotograma 47, así que escribes un comando de script que dispara el evento visual en el fotograma 47. Luego ves la demo, decides que la temporización está ligeramente desajustada, cambias el número a 49, recompilas, vuelves a probar y repites. Para una demo de dos minutos a 50 fps, eso son 6.000 fotogramas de puntos de sincronización potenciales. Acertarlos todos por ensayo y error toma semanas.

Eager de Introspec fue construida de esta manera, y el desarrollo fue agotador. Cada ajuste de sincronización requería recompilación -- ensamblar el código Z80, cargar el binario en un emulador, ver la sección relevante, notar qué estaba desajustado, editar el fuente y repetir. El ciclo de retroalimentación se medía en minutos por iteración.

### La respuesta de diver4d: Luma Fusion

diver4d evitó el ciclo de código-edición-compilación-prueba por completo. Usó **Luma Fusion**, un editor de vídeo para iOS, como su herramienta de sincronización.

El flujo de trabajo:

1. **n1k-o compuso la pista de gabber** con marcadores estructurales a nivel de fotograma. El músico y el programador trabajaron desde el mismo documento: una línea de tiempo donde cada pulso, cada relleno, cada desglose estaba marcado con un número de fotograma. No era una guía aproximada de tempo -- era un mapa con precisión de fotograma de toda la pista.

2. **diver4d grabó cada efecto visual** ejecutándose a 50 fps en un emulador y exportó las grabaciones como clips de vídeo.

3. **En Luma Fusion**, organizó los clips de vídeo en una línea de tiempo de 50 fps junto con la pista de audio. Podía navegar por la demo fotograma a fotograma, viendo exactamente cómo cada visual se alineaba con cada evento musical. Mover una transición era tan simple como arrastrar un clip en la línea de tiempo.

4. **Una vez que la temporización estaba correcta en el editor**, extrajo los números de fotograma para cada transición y cambio de efecto, y escribió esos números en los datos del script Z80.

La idea es engañosamente simple: usa la herramienta correcta para el trabajo. Un editor de vídeo está diseñado específicamente para sincronización multimedia a nivel de fotograma. El ensamblador Z80 no lo está. Al hacer el trabajo creativo de sincronización en el editor y el trabajo de implementación en ensamblador, diver4d separó las decisiones artísticas de las restricciones de ingeniería.

### Lo que esto cambia

El beneficio inmediato es velocidad. Ajustar la temporización de sincronización en un editor de vídeo toma segundos. Ajustarla en ensamblador toma minutos. Sobre cientos de puntos de sincronización, el ahorro de tiempo acumulado es enorme. Pero el beneficio más profundo es la libertad creativa. Cuando la iteración es barata, experimentas más. Pruebas la transición dos fotogramas antes, ves cómo se siente, la pruebas dos fotogramas después. Notas que el visual funciona mejor golpeando ligeramente *antes* del ritmo (una técnica tomada de la edición de cine, donde los cortes en el tiempo se sienten tardíos por el tiempo de reacción humano). Nunca podrías descubrir esta idea a través de iteración basada en código -- el ciclo de retroalimentación es demasiado lento.

La limitación es que este flujo de trabajo funciona mejor para demos donde la temporización es fija -- donde la demo siempre se reproduce de la misma manera. Si quieres elementos interactivos o generativos que respondan a condiciones de ejecución, necesitas el enfoque basado en código. Pero para la abrumadora mayoría de demos de ZX, que son producciones lineales de línea de tiempo fija, el flujo de trabajo del editor de vídeo es superior.

GABBA demostró que las herramientas de producción del demoscene no tienen que ser retro. El código Z80 es de 1985. El flujo de trabajo de sincronización puede ser de 2019. No hay contradicción.

---

## 12.5 Hilos en Z80: Un camino diferente

Robus, escribiendo en Hype en 2015, presentó una técnica que ataca el problema de concurrencia desde un ángulo completamente diferente: multihilo real en el Z80.

### El problema, replanteado

La tensión fundamental en un motor de demo es que múltiples tareas necesitan tiempo de CPU en el mismo fotograma: generación de efectos, reproducción de música, muestras de tambor, scripting, transiciones. La solución de Introspec es cooperativa: el motor intercala manualmente estas tareas usando un sistema de scripts y búfer de fotogramas. Esto funciona, pero requiere una programación manual cuidadosa y toda la arquitectura asíncrona que hemos estado discutiendo.

¿Qué pasaría si el Z80 pudiera ejecutar dos tareas simultáneamente?

### Cambio de contexto basado en IM2

Puede, en cierta medida. La interrupción IM2 del Z80 proporciona un punto natural de cambio de contexto. Cada fotograma, la interrupción se dispara. Si el manejador de interrupciones guarda el estado de la tarea actual y carga el estado de otra tarea, tienes multihilo preventivo.

El procedimiento `SwitchThread` de Robus hace exactamente esto:

```z80
; SwitchThread: save current thread, resume next thread
; Called from within the IM2 interrupt handler
SwitchThread:
    ; Save current thread's stack pointer
    ld   (thread_sp_save), sp

    ; Save current memory page configuration
    ld   a, (current_7ffd)
    ld   (thread_page_save), a

    ; Load next thread's state
    ld   a, (next_thread_page)
    ld   (current_7ffd), a
    ld   bc, $7FFD
    out  (c), a               ; switch memory page

    ld   sp, (next_thread_sp)  ; switch stack pointer

    ; Execution continues in the next thread's context
    ; (it was previously suspended at this same point)
    ret
```

Cada hilo obtiene su propia **pila de 128 bytes** y una **página de memoria dedicada** (uno de los ocho bancos de 16KB del Spectrum 128K). La pila es pequeña pero suficiente -- el código Z80 raramente anida profundamente. La página de memoria dedicada le da a cada hilo su propio espacio de trabajo sin interferir con el otro.

### Cómo funciona en la práctica

En la demo WAYHACK de Robus, dos hilos se ejecutan concurrentemente:

- **Hilo 1:** Calcula el efecto visual (un renderizador de perspectiva de mazmorra).
- **Hilo 2:** Renderiza texto desplazable a lo largo de la parte inferior de la pantalla.

Ningún hilo sabe del otro. Cada uno se ejecuta en su propia página de memoria con su propia pila. Cada fotograma, la interrupción IM2 se dispara y `SwitchThread` alterna entre ellos. El Hilo 1 obtiene un fotograma de tiempo de CPU, luego el Hilo 2 obtiene un fotograma, y así sucesivamente.

El resultado: el scroller de texto se ejecuta a un constante 25 Hz (cada segundo fotograma), y el efecto visual se ejecuta a 25 Hz. Ninguna tarea necesita ser consciente de la existencia de la otra. Sin programación cooperativa, sin puntos de cesión, sin intercalado manual. La interrupción maneja todo.

### El modelo de hilos

El modelo es simple:

```
Frame 1: Interrupt → save Thread 2 → restore Thread 1 → Thread 1 runs
Frame 2: Interrupt → save Thread 1 → restore Thread 2 → Thread 2 runs
Frame 3: Interrupt → save Thread 2 → restore Thread 1 → Thread 1 runs
...
```

Cada hilo ve un mundo consistente: sus registros, su pila, su página de memoria. El cambio ocurre en un punto fijo (la interrupción), así que no hay condiciones de carrera en datos compartidos. Si los hilos necesitan comunicarse (por ejemplo, el Hilo 1 señala al Hilo 2 que cambie el texto), lo hacen a través de una ubicación de memoria compartida a la que ambos hilos pueden acceder -- una simple bandera o buzón.

### Consideraciones prácticas

La propia evaluación de Robus es característicamente honesta: **"El multihilo honesto raramente requiere más de dos hilos"** en el Z80. La sobrecarga del cambio de contexto (guardar y restaurar SP más un cambio de página de memoria) es modesta -- quizás 100 T-states -- pero cada hilo adicional reduce a la mitad el tiempo de CPU disponible por hilo. Con dos hilos, cada uno obtiene 25 Hz. Con tres, cada uno obtiene aproximadamente 16,7 Hz. En una máquina donde la suavidad visual exige cerca de 50 Hz, dos hilos es el límite práctico.

El enfoque de hilos es ortogonal al enfoque de búfer asíncrono de Introspec. Podrías combinarlos: un hilo genera fotogramas de efectos en un búfer mientras el otro maneja la música y reproducción de tambores. En la práctica, esta combinación es rara -- las dos técnicas resuelven el mismo problema (intercalar tareas que consumen mucha CPU) a través de mecanismos diferentes, y la mayoría de los programadores de demos eligen una u otra según las demandas específicas de su producción.

Los hilos funcionan mejor cuando dos tareas son verdaderamente independientes y ninguna necesita más de 25 Hz. El enfoque de búfer asíncrono funciona mejor cuando una tarea (gráficos) necesita 50 Hz y la otra (tambores) necesita ráfagas impredecibles. Para la arquitectura de Eager, donde la suavidad visual era primordial y la temporización de tambores estaba dictada por la música, el enfoque de búfer ganó. Para la arquitectura de WAYHACK, donde dos tareas de estado estable corrían en paralelo, los hilos ganaron.

---

## 12.6 Práctica: Un motor de demo con scripts mínimo

Construyamos un motor de demo mínimo que une los conceptos de este capítulo. El objetivo no es la sofisticación de Eager -- es un esqueleto que demuestra la arquitectura.

### Qué construimos

- **Tres efectos simples:** plasma (basado en atributos, del Capítulo 9), barras de color (franjas horizontales de atributos) y un scroller de texto.
- **Música AY** reproduciéndose vía interrupción IM2 (usando un reproductor .pt3, como se describió en el Capítulo 11).
- **Una muestra digital de bombo** que se reproduce en el tiempo, robando 2 fotogramas de CPU.
- **Un script de línea de tiempo simple** que cambia entre efectos en puntos definidos.
- **Atributos con doble búfer** para absorber las pausas de los golpes de tambor.

### El mapa de memoria

```
$6000-$7FFF   Engine code + effect routines
$8000-$9FFF   Music player + song data
$A000-$AFFF   Sine tables, colour maps, sample data
$B000-$BFFF   Frame ring buffer (attribute frames)
$C000-$DFFF   Shadow screen (second display page)
$E000-$FFFF   Stack + IM2 vector table + workspace

Bank 0-3:     Not used (available for larger effects)
Bank 5:       Normal screen ($4000-$5AFF display)
Bank 7:       Shadow screen ($C000-$DAFF display)
```

### El script de línea de tiempo

```z80
; Timeline script: sequence of (effect_id, duration_frames, param_ptr)
timeline:
    DB  EFFECT_PLASMA,   0, 150   ; plasma for 150 frames (3 sec)
    DW  plasma_params_1
    DB  EFFECT_BARS,     0, 100   ; colour bars for 100 frames (2 sec)
    DW  bars_params_1
    DB  EFFECT_SCROLLER, 0, 200   ; text scroller for 200 frames (4 sec)
    DW  scroller_params_1
    DB  EFFECT_PLASMA,   0, 150   ; plasma again, different params
    DW  plasma_params_2
    DB  $FF                        ; end marker: loop from start

EFFECT_PLASMA   EQU 0
EFFECT_BARS     EQU 1
EFFECT_SCROLLER EQU 2
```

### El bucle principal del motor

```z80
; Main engine loop
; Assumes IM2 is set up and music player runs in the ISR

engine_init:
    ; Set up display: fill pixel memory with checkerboard
    call fill_checkerboard

    ; Initialise ring buffer
    xor  a
    ld   (buf_write_idx), a
    ld   (buf_read_idx), a
    ld   (buf_count), a

    ; Load first effect from timeline
    ld   hl, timeline
    ld   (script_ptr), hl
    call load_next_effect

engine_main:
    ; === Step 1: Check for drum trigger ===
    ld   a, (drum_pending)
    or   a
    jr   z, .no_drum

    ; Play the drum -- this consumes ~2 frames
    call play_kick_drum
    xor  a
    ld   (drum_pending), a
    jr   .after_drum

.no_drum:
    ; === Step 2: Generate a frame into the buffer ===
    ld   a, (buf_count)
    cp   BUF_CAPACITY         ; buffer full?
    jr   nc, .buffer_full

    ; Generate one frame of the current effect
    call generate_frame       ; writes 768 bytes to ring buffer

    ; Advance buffer write pointer
    ld   a, (buf_write_idx)
    inc  a
    cp   BUF_CAPACITY
    jr   nz, .no_wrap_w
    xor  a
.no_wrap_w:
    ld   (buf_write_idx), a
    ld   a, (buf_count)
    inc  a
    ld   (buf_count), a

.buffer_full:
.after_drum:
    ; === Step 3: Advance timeline ===
    ld   hl, (frame_counter)
    inc  hl
    ld   (frame_counter), hl

    ; Check if current effect duration has elapsed
    ld   de, (effect_duration)
    or   a
    sbc  hl, de
    jr   c, .effect_continues

    ; Load next effect from timeline
    call load_next_effect
    ld   hl, 0
    ld   (frame_counter), hl

.effect_continues:
    ; === Step 4: Wait if we are ahead of display ===
    halt                      ; sync to frame boundary

    jr   engine_main
```

### La ISR de visualización

```z80
; IM2 interrupt handler: runs every frame (50 Hz)
frame_isr:
    push af
    push bc
    push de
    push hl

    ; Play music (updates AY registers)
    call music_play

    ; Check if music engine signals a drum hit
    ld   a, (music_drum_flag)
    or   a
    jr   z, .no_drum_signal
    xor  a
    ld   (music_drum_flag), a
    ld   a, 1
    ld   (drum_pending), a    ; signal main loop
.no_drum_signal:

    ; Display next frame from ring buffer
    ld   a, (buf_count)
    or   a
    jr   z, .no_frame         ; buffer empty, keep current frame

    ; Copy buffered attributes to display page
    call copy_buf_to_screen

    ; Advance read pointer
    ld   a, (buf_read_idx)
    inc  a
    cp   BUF_CAPACITY
    jr   nz, .no_wrap_r
    xor  a
.no_wrap_r:
    ld   (buf_read_idx), a
    ld   a, (buf_count)
    dec  a
    ld   (buf_count), a

.no_frame:
    pop  hl
    pop  de
    pop  bc
    pop  af
    ei
    reti

BUF_CAPACITY EQU 8           ; 8 frames of buffer (8 x 768 = 6,144 bytes)
```

### El despacho del generador de efectos

```z80
; Generate one frame of the current effect
; Writes attribute data to the ring buffer
generate_frame:
    ld   a, (current_effect)
    or   a
    jr   z, .do_plasma
    cp   1
    jr   z, .do_bars
    cp   2
    jr   z, .do_scroller
    ret

.do_plasma:
    call calc_plasma          ; from Chapter 9 -- writes 768 bytes
    ret
.do_bars:
    call calc_colour_bars     ; horizontal attribute stripes
    ret
.do_scroller:
    call calc_text_scroll     ; text rendering into attributes
    ret
```

### Observaciones

Este esqueleto es deliberadamente simple. Un motor de producción añadiría:

- **Scripts internos** para variación de parámetros dentro de cada efecto.
- **Efectos de transición** (fundidos cruzados entre dos búferes de atributos).
- **Múltiples sonidos de tambor** (bombo, caja, hi-hat), cada uno con sus propios datos de muestra.
- **Monitorización del nivel del búfer** para que el generador pueda priorizar la recuperación después de pasajes densos de percusión.
- **Conmutación de bancos de memoria** para almacenar más fotogramas y soportar datos de efectos más grandes.

Pero incluso en esta forma mínima, la arquitectura demuestra los principios clave:

1. **Generación y visualización desacopladas.** El generador y la ISR de visualización se comunican solo a través del búfer circular. Ninguno sabe ni le importa la temporización del otro.

2. **Los golpes de tambor son absorbidos por el búfer.** Cuando `play_kick_drum` consume dos fotogramas, la ISR de visualización continúa mostrando fotogramas del búfer. La audiencia no ve ningún tartamudeo.

3. **El script dirige la línea de tiempo.** Añadir un nuevo efecto o cambiar la secuencia significa editar la tabla de datos `timeline`, no reestructurar el código del motor.

4. **El reproductor de música se ejecuta en la ISR.** Actualiza los registros del AY cada fotograma independientemente de lo que el bucle principal esté haciendo. La única interacción es la bandera `drum_pending` -- un buzón de un byte entre la ISR y el bucle principal.

Esta es la arquitectura de una demo. No los efectos, no la música, no el arte -- la *fontanería* que hace que todo funcione junto. Es la parte menos visible de una demo y la más difícil de hacer bien. Introspec pasó diez semanas en Eager, y la arquitectura consumió más de ese tiempo que cualquier efecto individual.

---

## 12.7 Ejercicios prácticos

**Ejercicio 1: Motor básico.** Implementa el esqueleto anterior con un solo efecto (plasma del Capítulo 9) y sin muestras de tambor. Verifica que el búfer circular funciona correctamente: la visualización muestra animación suave mientras el generador funciona a su velocidad natural.

**Ejercicio 2: Añade el tambor.** Graba (o sintetiza) una muestra de bombo de 4 bits (400-800 bytes). Añade la rutina `play_kick_drum` y dispárala cada 25 fotogramas. Verifica que la visualización permanece suave durante la reproducción del tambor. ¿Cuál es la tasa máxima de tambor antes de que el búfer se vacíe?

**Ejercicio 3: Línea de tiempo multi-efecto.** Añade un segundo efecto (barras de color o scroller de texto). Escribe un script de línea de tiempo que cambie entre efectos cada 3-4 segundos. Verifica que las transiciones ocurren en el fotograma correcto.

**Ejercicio 4: Sincronización con música.** Carga una melodía corta en .pt3 y modifica el reproductor para que establezca `music_drum_flag` cuando ocurra un evento particular en el patrón (por ejemplo, una nota en el canal C por debajo de cierto tono). Ahora los tambores son dirigidos por la música, no por un contador de fotogramas fijo. Esto es sincronización musical real.

**Ejercicio 5: Flujo de trabajo con editor de vídeo.** Graba tu demo ejecutándose en un emulador a 50 fps. Importa la grabación en un editor de vídeo (cualquier editor que soporte edición a nivel de fotograma). Ajusta los números de fotograma del script de línea de tiempo basándote en lo que ves en el editor. Experimenta la diferencia en velocidad de iteración comparada con la sincronización solo por código.

---

## Resumen

Este capítulo no fue sobre un solo efecto o técnica. Fue sobre arquitectura -- la estructura invisible que permite que una demo exista como una actuación coherente, sincronizada, de dos minutos en lugar de una colección de pantallas inconexas.

Los problemas centrales son universales. Todo motor de demo debe responder: ¿Cómo comparto la CPU entre audio y vídeo? ¿Cómo mantengo la visualización suave cuando el audio roba tiempo de procesamiento? ¿Cómo secuencio efectos y los sincronizo con la música? ¿Cómo gestiono la línea de tiempo de una producción de varios minutos?

Las soluciones que examinamos son complementarias:

- **Tambores digitales** (n1k-o/Introspec) explotan los registros de volumen del AY como un DAC crudo, mezclando muestras digitales con síntesis por hardware para producir percusión que trasciende las capacidades diseñadas del chip.
- **Generación asíncrona de fotogramas** (Introspec) desacopla la producción de vídeo de la visualización a través de un búfer circular, absorbiendo las ráfagas de CPU consumidas por la reproducción de tambores.
- **Líneas de tiempo con scripts** (Introspec) separan el *qué* y *cuándo* de una demo del *cómo*, haciendo posible diseñar y ajustar una producción de dos minutos sin reestructurar el motor.
- **Sincronización con editor de vídeo** (diver4d) traslada el trabajo creativo de temporización a una herramienta diseñada específicamente para ello, acelerando dramáticamente el ciclo de iteración de sincronización.
- **Hilos en Z80** (Robus) proporciona concurrencia genuina para tareas que son independientes y de estado estable, al coste de reducir a la mitad la tasa de fotogramas para cada tarea.

Con este capítulo, cerramos el círculo de la sección de demoscene del libro. Hemos construido efectos (Partes I-II), hecho sonido (Capítulo 11), y ahora conectado todo en un motor funcional. El lector que ha seguido desde el Capítulo 1 tiene una imagen completa: desde el conteo de T-states hasta una demo sincronizada y con scripts con tambores digitales.

En el próximo capítulo, cambiamos de marcha completamente. La Parte IV nos lleva al sizecoding -- el arte de encajar una producción entera en 256 bytes. La arquitectura pasa de "¿cómo gestiono un búfer circular?" a "¿cómo hago que cada byte haga doble servicio?" Las restricciones se estrechan en tres órdenes de magnitud, y el pensamiento cambia para igualarlo.

---

> **Fuentes:** Introspec, "Making of Eager," Hype, 2015 (hype.retroscene.org/blog/demo/261.html); Introspec, file_id.diz from Eager (to live), 3BM Open Air 2015; diver4d, "Making of GABBA," Hype, 2019 (hype.retroscene.org/blog/demo/948.html); Robus, "Threads on Z80," Hype, 2015 (hype.retroscene.org/blog/dev/271.html); Eager source code excerpts courtesy of Introspec (Life on Mars)
