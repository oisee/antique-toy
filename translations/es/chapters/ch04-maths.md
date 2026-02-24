# Capitulo 4: Las Matematicas Que Realmente Necesitas

> *"Lee un libro de texto de matematicas -- derivadas, integrales. Las vas a necesitar."*
> -- Dark, Spectrum Expert #01 (1997)

En 1997, un adolescente en San Petersburgo se sento a escribir un articulo de revista sobre multiplicacion. No la clase que aprendes en la escuela -- la clase que hace que un cubo de alambre gire en un ZX Spectrum a 50 fotogramas por segundo. Su nombre era Dark, programaba para el grupo X-Trade, y su demo *Illusion* ya habia ganado el primer puesto en ENLiGHT'96. Ahora estaba escribiendo *Spectrum Expert*, una revista electronica distribuida en disquete, y iba a explicar exactamente como funcionaban sus algoritmos.

Lo que sigue esta extraido directamente del articulo "Programming Algorithms" de Dark en Spectrum Expert #01. Estas son las rutinas que alimentaron *Illusion* -- la misma multiplicacion que rotaba vertices, la misma tabla de seno que impulsaba el rotozoomer, el mismo dibujador de lineas que renderizaba estructuras de alambre a tasa de fotogramas completa. Cuando Introspec hizo ingenieria inversa de *Illusion* veinte anos despues en el blog Hype, encontro estos algoritmos exactos funcionando dentro del binario.

---

## Multiplicacion en Z80

El Z80 no tiene instruccion de multiplicacion. Cada vez que necesitas A por B -- para matrices de rotacion, proyeccion en perspectiva, mapeado de texturas -- debes sintetizarlo a partir de desplazamientos y sumas. Dark presenta dos metodos, y es caracteristicamente honesto sobre el compromiso entre ellos.

### Metodo 1: Desplazamiento y Suma desde el LSB

El enfoque clasico. Recorre los bits del multiplicador del LSB al MSB. Por cada bit activo, suma el multiplicando a un acumulador. Despues de cada bit, desplaza el acumulador a la derecha. Despues de ocho iteraciones, el acumulador contiene el producto completo.

Aqui esta la multiplicacion sin signo 8x8 de Dark. Entrada: B por C. Resultado en A (byte alto) y C (byte bajo):

```z80
; MULU112 -- 8x8 unsigned multiply
; Input:  B = multiplicand, C = multiplier
; Output: A:C = B * C (16-bit result, A=high, C=low)
; Cost:   196-204 T-states (Pentagon)
;
; From Dark / X-Trade, Spectrum Expert #01 (1997)

mulu112:
    ld   a, 0           ; clear accumulator (high byte of result)
    ld   d, 8           ; 8 bits to process

.loop:
    rr   c              ; shift LSB of multiplier into carry
    jr   nc, .noadd     ; if bit was 0, skip addition
    add  a, b           ; add multiplicand to accumulator
.noadd:
    rra                 ; shift accumulator right (carry into bit 7,
                        ;   bit 0 into carry -- this carry feeds
                        ;   back into C via the next RR C)
    dec  d
    jr   nz, .loop
    ret
```

Estudia esto con cuidado. La instruccion `RRA` desplaza A a la derecha, pero tambien empuja el bit mas bajo de A al indicador de acarreo. En la siguiente iteracion, `RR C` rota ese acarreo hacia la parte superior de C. Asi los bits bajos del producto se ensamblan gradualmente en C, mientras los bits altos se acumulan en A. Despues de ocho iteraciones, el resultado completo de 16 bits esta en A:C.

El coste es de 196 a 204 T-states dependiendo de cuantos bits del multiplicador estan activos -- cada bit activo cuesta un `ADD A,B` adicional (4 T-states). El ejemplo en `chapters/ch04-maths/examples/multiply8.a80` muestra una variante que devuelve el resultado en HL.

Para 16x16 produciendo un resultado de 32 bits, el MULU224 de Dark funciona en 730 a 826 T-states. En la practica, los motores 3D de demoscene evitan multiplicaciones completas 16x16 manteniendo las coordenadas en punto fijo 8.8 y usando multiplicaciones 8x8 donde sea posible.

![Recorrido de multiplicacion 8x8 por desplazamiento y suma](illustrations/output/ch04_multiply_walkthrough.png)

### Metodo 2: Consulta en Tabla de Cuadrados

El segundo metodo de Dark intercambia memoria por velocidad, explotando una identidad algebraica que todo demoscener eventualmente descubre:

```
A * B = ((A+B)^2 - (A-B)^2) / 4
```

Pre-computa una tabla de valores n^2/4, y la multiplicacion se convierte en dos consultas y una resta -- aproximadamente 61 T-states, mas de tres veces mas rapido que el desplazamiento y suma.

Necesitas una tabla de 512 bytes de (n^2/4) para n = 0 a 511, alineada a pagina para indexacion con un solo registro. La tabla debe ser de 512 bytes porque (A+B) puede alcanzar 510.

```z80
; MULU_FAST -- Square table multiply
; Input:  B, C = unsigned 8-bit factors
; Output: HL = B * C (16-bit result)
; Cost:   ~61 T-states (Pentagon)
; Requires: sq_table = 512-byte table of n^2/4, page-aligned
;
; A*B = ((A+B)^2 - (A-B)^2) / 4

mulu_fast:
    ld   h, sq_table >> 8  ; high byte of table address
    ld   a, b
    add  a, c              ; A = B + C (may overflow into carry)
    ld   l, a
    ld   e, (hl)           ; look up (B+C)^2/4 low byte
    inc  h
    ld   d, (hl)           ; look up (B+C)^2/4 high byte

    ld   a, b
    sub  c                 ; A = B - C (may go negative)
    jr   nc, .pos
    neg                    ; take absolute value
.pos:
    ld   l, a
    dec  h
    ld   a, e
    sub  (hl)              ; subtract (B-C)^2/4 low byte
    ld   e, a
    inc  h
    ld   a, d
    sbc  a, (hl)           ; subtract (B-C)^2/4 high byte
    ld   d, a

    ex   de, hl            ; HL = result
    ret
```

El compromiso? Dark es caracteristicamente honesto: **"Elige: velocidad o precision."** La tabla almacena valores enteros de n^2/4, asi que hay un error de redondeo de hasta 0,25 por consulta. Para valores grandes esto es insignificante. Para los pequenos deltas de coordenadas en la rotacion 3D, el error produce un temblor visible en los vertices. Con desplazamiento y suma, la rotacion es perfectamente suave.

Para mapeado de texturas, plasma, scrollers -- usa la multiplicacion rapida. Para 3D de alambre donde el ojo sigue vertices individuales -- quédate con desplazamiento y suma. Dark lo sabia porque habia probado ambos en *Illusion*.

**Generar la tabla de cuadrados** es un coste de inicio de una sola vez. Dark sugiere usar el metodo de la derivada: como d(x^2)/dx = 2x, puedes construir la tabla incrementalmente sumando un delta linealmente creciente en cada paso. En la practica, la mayoria de los coders calculan la tabla en un cargador BASIC o rutina de inicializacion y siguen adelante.

---

## Division en Z80

La division en el Z80 es aun mas dolorosa que la multiplicacion. Sin instruccion de division, y el algoritmo es inherentemente serial -- cada bit del cociente depende de la resta anterior. Dark nuevamente presenta dos metodos: preciso y rapido.

### Metodo 1: Desplazamiento y Resta (Division con Restauracion)

Division larga binaria. Comienza con un acumulador en cero. El dividendo se desplaza desde la derecha, un bit por iteracion. Intenta restar el divisor; si tiene exito, establece un bit del cociente. Si falla, restaura el acumulador -- de ahi "division con restauracion".

```z80
; DIVU111 -- 8-bit unsigned divide
; Input:  B = dividend, C = divisor
; Output: B = quotient, A = remainder
; Cost:   236-244 T-states (Pentagon)
;
; From Dark / X-Trade, Spectrum Expert #01 (1997)

divu111:
    xor  a               ; clear accumulator (remainder workspace)
    ld   d, 8            ; 8 bits to process

.loop:
    sla  b               ; shift dividend left -- MSB into carry
    rla                  ; shift carry into accumulator
    cp   c               ; try to subtract divisor
    jr   c, .too_small   ; if accumulator < divisor, skip
    sub  c               ; subtract divisor from accumulator
    inc  b               ; set bit 0 of quotient (B was just shifted,
                         ;   so bit 0 is free)
.too_small:
    dec  d
    jr   nz, .loop
    ret                  ; B = quotient, A = remainder
```

El `INC B` para establecer el bit del cociente es un truco elegante: B acaba de ser desplazado a la izquierda por `SLA B`, asi que el bit 0 esta garantizado en cero. `INC B` lo establece sin afectar otros bits -- mas barato que `OR` o `SET`.

La version de 16 bits (DIVU222) cuesta de 938 a 1.034 T-states. Mil T-states por una sola division. Con un presupuesto de fotograma de ~70.000 T-states, puedes permitirte quizas 70 divisiones por fotograma -- sin hacer nada mas. Por eso los motores 3D de demoscene hacen esfuerzos extremos para evitar la division.

### Metodo 2: Division Logaritmica

La alternativa mas rapida de Dark usa tablas de logaritmos:

```
Log(A / B) = Log(A) - Log(B)
A / B = AntiLog(Log(A) - Log(B))
```

Con dos tablas de consulta de 256 bytes -- Log y AntiLog -- la division se convierte en dos consultas, una resta y una tercera consulta. El coste baja a aproximadamente 50-70 T-states. Para la division de perspectiva (dividir entre Z para proyectar puntos 3D en pantalla), esto es revolucionario.

**Generar la tabla de logaritmos** es donde las cosas se ponen interesantes. Dark propone construirla usando derivadas -- la misma tecnica incremental que la tabla de cuadrados. La derivada de log2(x) es 1/(x * ln(2)), asi que acumulas incrementos fraccionarios paso a paso, comenzando desde log2(1) = 0 y avanzando. La constante 1/ln(2) = 1,4427 necesita ser escalada para caber en el rango de 8 bits de la tabla.

Y aqui es donde la honestidad de Dark brilla. Despues de derivar la formula de generacion, intenta calcular un coeficiente de correccion para el escalado de la tabla y llega a 0,4606. Luego escribe -- en un articulo de revista publicado -- *"Algo no esta bien aqui, asi que se recomienda escribir uno similar por tu cuenta."*

Un adolescente de diecisiete anos en 1997, publicando en una revista de disco leida por sus pares en toda la escena Spectrum rusa, diciendo abiertamente: consegui que esto funcionara, pero mi derivacion tiene un hueco, averigua la version limpia por ti mismo. Esa honestidad es rara en la escritura tecnica a cualquier nivel, y es una de las cosas que hacen de Spectrum Expert un documento tan notable.

En la practica, las tablas de logaritmos funcionan. Los errores de redondeo al comprimir una funcion continua en 256 bytes son aceptables para la proyeccion en perspectiva. El motor 3D de Dark en *Illusion* usa exactamente esta tecnica.

---

## Seno y Coseno

Rotacion, scrolling, plasma -- cada efecto que se curva necesita trigonometria. En el Z80, precalculas una tabla de consulta. El enfoque de Dark es bellamente pragmatico: una parabola es lo suficientemente cercana a una onda sinusoidal para el trabajo de demo.

### La Aproximacion Parabolica

Medio periodo de coseno, de 0 a pi, se curva de +1 a -1. Una parabola y = 1 - 2*(x/pi)^2 sigue casi el mismo camino. El error maximo es de aproximadamente 5,6% -- terrible para ingenieria, invisible en una demo a resolucion de 256x192.

Dark genera una tabla de coseno de 256 bytes con signo (-128 a +127), indexada por angulo: 0 = 0 grados, 64 = 90 grados, 128 = 180 grados, 256 vuelve a 0. El periodo en potencia de dos significa que el indice de angulo se envuelve naturalmente con el desbordamiento de 8 bits, y el coseno se convierte en seno sumando 64.

```z80
; Generate 256-byte signed cosine table (-128..+127)
; using parabolic approximation
;
; The table covers one full period: cos(n * 2*pi/256)
; scaled to signed 8-bit range.
;
; Approach: for the first half (0..127), compute
;   y = 127 - (x^2 * 255 / 128^2)
; approximated via incrementing differences.
; Mirror for second half.

gen_cos_table:
    ld   hl, cos_table
    ld   b, 0              ; x = 0
    ld   de, 0             ; running delta (fixed-point)

    ; First quarter: cos descends from +127 to 0
    ; Second quarter: continues to -128
    ; ...build via incremental squared differences

    ; In practice, the generation loop runs ~30 bytes
    ; and produces the table in a few hundred cycles.
```

La idea clave: no necesitas calcular x^2 para cada entrada. Como (x+1)^2 - x^2 = 2x + 1, construyes la parabola incrementalmente -- empieza en el pico, resta un delta linealmente creciente. Sin multiplicacion, sin division, sin punto flotante.

La tabla resultante es una aproximacion parabolica por tramos. Graficala contra el seno verdadero y te costara ver la diferencia. Para 3D de alambre o un scroller rebotante, es mas que suficiente.

> **Sidebar: Los 9 Mandamientos de las Tablas de Seno de Raider**
>
> En los comentarios de Hype sobre el analisis de *Illusion* de Introspec, el coder veterano Raider dejo una lista de reglas para el diseno de tablas de seno que se conocio informalmente como los "9 mandamientos". Los principios clave:
>
> - Usa un tamano de tabla en potencia de dos (256 entradas es canonico).
> - Alinea la tabla a un limite de pagina para que `H` contenga la base y `L` sea el angulo directo -- la indexacion es gratuita.
> - Almacena valores con signo para uso directo en aritmetica de coordenadas.
> - Deja que el angulo se envuelva naturalmente via desbordamiento de 8 bits -- sin verificacion de limites.
> - El coseno es simplemente seno desplazado un cuarto de periodo: carga el angulo, suma 64, consulta.
> - Si necesitas mayor precision, usa una tabla de 16 bits (512 bytes) pero raramente lo necesitas.
> - Genera la tabla al inicio en lugar de almacenarla en el binario -- ahorra espacio, no cuesta nada.
> - Para rotacion 3D, pre-multiplica por tu factor de escala y almacena los valores escalados.
> - Nunca calcules trigonometria en tiempo de ejecucion. Si crees que lo necesitas, estas equivocado.
>
> Estos mandamientos reflejan decadas de experiencia colectiva. Siguelos y tus tablas de seno seran rapidas, pequenas y correctas.

---

## Dibujo de Lineas de Bresenham

Cada arista de un objeto de alambre es una linea de (x1,y1) a (x2,y2), y necesitas dibujarla rapido. El tratamiento de Dark en Spectrum Expert #01 es la seccion mas larga de su articulo, trabajando a traves de tres enfoques progresivamente mas rapidos.

### El Algoritmo Clasico y la Modificacion de Xopha

El algoritmo de Bresenham avanza a lo largo del eje mayor un pixel a la vez, manteniendo un acumulador de error para los pasos del eje menor. En el Spectrum, "establecer un pixel" es costoso -- la memoria de pantalla entrelazada significa que calcular una direccion de byte y posicion de bit cuesta T-states reales. La rutina de la ROM toma mas de 1000 T-states por pixel. Incluso un bucle de Bresenham optimizado a mano cuesta ~80 T-states por pixel.

Dark menciona la mejora de Xopha: mantener un puntero de pantalla (HL) y avanzarlo incrementalmente en lugar de recalcular desde cero. Moverse a la derecha significa rotar una mascara de bits; moverse hacia abajo significa el ajuste DOWN_HL de multiples instrucciones. Mejor, pero el problema central permanece.

### El Metodo de Matrices de Dark: Cuadriculas de Pixeles 8x8

Entonces Dark hace su observacion clave: **"El 87,5% de las verificaciones se desperdician."**

En un bucle de Bresenham, en cada pixel preguntas: debo dar un paso lateral? Para una linea casi horizontal, la respuesta es casi siempre no. En promedio, siete de cada ocho verificaciones no producen paso lateral. Estas quemando T-states en un salto condicional que casi nunca se activa.

La solucion de Dark: pre-computar el patron de pixeles para cada pendiente de linea dentro de una cuadricula de pixeles 8x8, y desenrollar el bucle de dibujo para emitir celdas de cuadricula completas de una vez. Un segmento de linea dentro de un area 8x8 esta completamente determinado por su pendiente. Para cada uno de los ocho octantes, enumera todos los patrones posibles de 8 pixeles como secuencias directas de instrucciones `SET bit,(HL)` con incrementos de direccion entre ellas.

```z80
; Example: one unrolled 8-pixel segment of a nearly-horizontal line
; (octant 0: moving right, gently sloping down)
;
; The line enters at the left edge of an 8x8 character cell
; and exits at the right edge, dropping one pixel row partway through.

    set  7, (hl)        ; pixel 0 (leftmost bit in byte)
    set  6, (hl)        ; pixel 1
    set  5, (hl)        ; pixel 2
    set  4, (hl)        ; pixel 3
    set  3, (hl)        ; pixel 4
    ; --- step down one pixel row ---
    inc  h              ; next screen row (within character cell)
    set  2, (hl)        ; pixel 5
    set  1, (hl)        ; pixel 6
    set  0, (hl)        ; pixel 7 (rightmost bit in byte)
```

Sin saltos condicionales. Sin acumulador de error. `SET bit,(HL)` toma 15 T-states; ocho de ellas mas un par de operaciones `INC H` dan ~130 T-states por segmento de 8 pixeles, o aproximadamente 16 T-states por pixel. Con la sobrecarga de consulta y avance de celda, Dark logra aproximadamente **48 T-states por pixel** -- casi la mitad del coste clasico de Bresenham.

El precio es memoria: una rutina desenrollada separada para cada pendiente por octante, aproximadamente **3KB en total**. En un Spectrum 128K, una inversion modesta para una ganancia de velocidad masiva.

### Terminacion Basada en Trampa

En lugar de verificar un contador de bucle en cada pixel, Dark coloca un centinela donde termina la linea. Cuando el codigo de dibujo llega al centinela, sale -- eliminando la sobrecarga de `DEC counter / JR NZ` por completo.

El sistema completo -- seleccion de octante, consulta de segmento, dibujo desenrollado, terminacion por trampa -- es una de las piezas de codigo mas impresionantes de Spectrum Expert #01. Cuando Introspec desensamblo *Illusion* en 2017, encontro este metodo de matrices en funcionamiento, dibujando las estructuras de alambre a tasa de fotogramas completa.

---

## Aritmetica de Punto Fijo

Cada algoritmo en este capitulo asume algo que aun no hemos hecho explicito: numeros de punto fijo.

El Z80 no tiene unidad de punto flotante. Cada registro contiene un entero. Pero los efectos de demo necesitan valores fraccionarios -- angulos de rotacion, velocidades sub-pixel, factores de escala. La solucion es el punto fijo: elige una convencion para donde vive el "punto decimal" dentro de un entero, luego haz toda la aritmetica con enteros mientras rastreas el escalado mentalmente.

### Formato 8.8

El formato mas comun en el Z80 es **8.8**: byte alto = parte entera, byte bajo = parte fraccionaria. Un par de registros de 16 bits contiene un numero de punto fijo:

```
H = parte entera    (-128..+127 con signo, o 0..255 sin signo)
L = parte fraccionaria (0..255, representando 0/256 a 255/256)
```

`HL = $0180` representa 1,5 (H=1, L=128, y 128/256 = 0,5). `HL = $FF80` con signo es -0,5 (H=$FF = -1 en complemento a dos, L=$80 suma 0,5).

La belleza: **la suma y la resta son gratuitas** -- solo operaciones normales de 16 bits:

```z80
; Fixed-point 8.8 addition: result = a + b
; HL = first operand, DE = second operand
    add  hl, de          ; that's it. 11 T-states.

; Fixed-point 8.8 subtraction: result = a - b
    or   a               ; clear carry
    sbc  hl, de          ; 15 T-states.
```

Al procesador no le importa que estes tratando estos como punto fijo. La suma binaria es la misma ya sea que los bits representen enteros o valores 8.8.

### Multiplicacion en Punto Fijo

Multiplicar dos numeros 8.8 produce un resultado 16.16 -- 32 bits. Quieres 8.8 de vuelta, asi que tomas los bits 8..23 del producto (efectivamente desplazando 8 a la derecha). En la practica, con partes enteras pequenas (coordenadas, factores de rotacion entre -1 y +1), puedes descomponer la multiplicacion en productos parciales:

```z80
; Fixed-point 8.8 multiply (simplified)
; Input:  BC = first operand (B.C in 8.8)
;         DE = second operand (D.E in 8.8)
; Output: HL = result (H.L in 8.8)
;
; Full product = BC * DE (32 bits), we want bits 8..23
;
; Decomposition:
;   BC * DE = (B*256+C) * (D*256+E)
;           = B*D*65536 + (B*E + C*D)*256 + C*E
;
; In 8.8 result (bits 8..23):
;   H.L = B*D*256 + B*E + C*D + (C*E)/256
;
; For small B,D (say -1..+1), B*D*256 is the dominant term.
; C*E/256 is a rounding correction.
; Total cost: ~200 T-states using the shift-and-add multiplier.

fixmul88:
    ; Multiply B*E -> add to result high
    ld   a, b
    call mul8             ; A = B*E (assuming 8x8->8 truncated)
    ld   h, a

    ; Multiply C*D -> add to result
    ld   a, c
    ld   b, d
    call mul8             ; A = C*D
    add  a, h
    ld   h, a

    ; For higher precision, also compute B*D and C*E
    ; and combine. In practice, the two middle terms
    ; are often sufficient for demo work.

    ld   l, 0             ; fractional part (approximate)
    ret
```

Para rotacion impulsada por tabla de seno donde los valores de seno son de 8 bits con signo (-128 a +127, representando -1,0 a +0,996), multiplicar una coordenada de 8 bits por un valor de seno via `mulu112` da un resultado de 16 bits ya en formato 8.8 -- el byte alto es la coordenada entera rotada, el byte bajo es la fraccion.

### Por Que Importa el Punto Fijo

El formato 8.8 es el punto ideal para el Z80: cabe en un par de registros, la suma/resta son gratuitas, la multiplicacion cuesta ~200 T-states, y la precision es suficiente para efectos a resolucion de pantalla. Existen otros formatos -- 4.12 para mas precision fraccionaria, 12.4 para mas rango entero -- pero 8.8 cubre la gran mayoria de los casos de uso. Los capitulos de desarrollo de juegos mas adelante en este libro usan 8.8 exclusivamente.

---

## Teoria y Practica

Estos algoritmos no son tecnicas aisladas. Forman un sistema. La multiplicacion alimenta la matriz de rotacion. La rotacion genera coordenadas que necesitan division de perspectiva. La division usa tablas de logaritmos. Los vertices proyectados se conectan con lineas dibujadas por el metodo de matrices. Todo funciona con aritmetica de punto fijo, con valores de seno de la tabla parabolica.

Dark los diseno como componentes de un solo motor -- el motor que alimentaba *Illusion*. Un cubo de alambre girando a tasa de fotogramas completa ejercita cada rutina de este capitulo:

1. **Lee el angulo de rotacion** de la tabla de seno (aproximacion parabolica, ~20 T-states por consulta)
2. **Multiplica** las coordenadas de vertices por factores de rotacion (desplazamiento y suma para precision, o tabla de cuadrados para velocidad -- ~200 o ~60 T-states por multiplicacion, 12 multiplicaciones por vertice)
3. **Divide** entre Z para proyeccion en perspectiva (tablas de logaritmos, ~60 T-states por division)
4. **Dibuja lineas** entre vertices proyectados (Bresenham de matrices, ~48 T-states por pixel)

Para un cubo simple (8 vertices, 12 aristas), el coste total por fotograma es aproximadamente:

- Rotacion: 8 vertices x 12 multiplicaciones x 200 T-states = 19.200 T-states
- Proyeccion: 8 vertices x 1 division x 60 T-states = 480 T-states
- Dibujo de lineas: 12 aristas x ~40 pixeles x 48 T-states = 23.040 T-states
- **Total: ~42.720 T-states** -- comodamente dentro del presupuesto de fotograma de ~70.000 T-states

Cambia a la multiplicacion rapida con tabla de cuadrados y la rotacion baja a 5.760 T-states. Los vertices tiemblan ligeramente, pero ahora tienes margen para objetos mas complejos. Velocidad o precision -- en una demo, tomas esa decision para cada efecto, cada fotograma.

---

## Lo Que Dark Hizo Bien

Mirando atras al Spectrum Expert #01 desde casi treinta anos de distancia, lo que te impacta no es solo la calidad de los algoritmos sino la calidad del pensamiento. Dark presenta cada uno, explica los compromisos honestamente, admite cuando su derivacion tiene huecos, y confia en que el lector llenara esos huecos.

Estaba escribiendo para coders de Spectrum en Rusia a finales de los 90 -- una comunidad que construia algunas de las demos de 8 bits mas impresionantes del mundo, en hardware que el resto del mundo habia abandonado. Estos son los bloques de construccion que usaban. Cuando escribas tu primer motor 3D para el Spectrum, estas rutinas lo haran posible.

En el siguiente capitulo, Dark y STS extienden esta base matematica a un sistema 3D completo: el metodo del punto medio para interpolacion de vertices, eliminacion de caras traseras y renderizado de poligonos solidos. Las matematicas de aqui son los cimientos. El Capitulo 5 es la arquitectura construida encima.

---

## Numeros Aleatorios: Cuando las Tablas No Sirven

Todo lo presentado hasta ahora en este capitulo es determinista. Dados los mismos datos de entrada, la misma multiplicacion, la misma consulta de seno, el mismo dibujo de linea -- obtienes la misma salida. Eso es exactamente lo que quieres para un cubo de alambre giratorio o un plasma suave.

Pero a veces necesitas caos. Estrellas titilando en un campo estelar. Particulas dispersandose de una explosion. Texturas de ruido para generacion de terreno. Un orden aleatorio para pantallas de carga. En competiciones de sizecoding (256 bytes o menos), un buen generador de numeros aleatorios puede producir efectos visuales sorprendentemente complejos con casi nada de codigo.

El Z80 no tiene generador de numeros aleatorios por hardware. Debes sintetizar aleatoriedad a partir de aritmetica, y la calidad de esa aritmetica importa mas de lo que podrias pensar.

### El Truco del Registro R

El Z80 tiene una fuente incorporada de entropia a la que muchos coders recurren primero: el registro R. Se incrementa automaticamente con cada busqueda de instruccion (cada ciclo M1), ciclando de 0 a 127. Puedes leerlo en 9 T-states:

```z80
    ld   a, r              ; 9 T -- read refresh counter
```

Esto *no* es un PRNG. El registro R es completamente determinista -- avanza de uno en uno por instruccion, y su valor en cualquier punto depende enteramente del camino de codigo tomado desde el reinicio. En una demo con un bucle principal fijo, R produce la misma secuencia cada vez. Pero es util como fuente de semilla: lee R una vez al inicio (cuando el temporizado depende de cuanto espero el usuario antes de presionar una tecla) y alimenta ese valor impredecible a un PRNG apropiado.

Algunos coders mezclan R en su generador en cada llamada, anadiendo entropia genuina de temporizado de instrucciones. El generador Ion de abajo usa exactamente este truco.

### Cuatro Generadores de la Comunidad

En 2024, Gogin (de la escena ZX rusa) recopilo una coleccion de rutinas PRNG para Z80 y las compartio para evaluacion. Gogin las probo sistematicamente, llenando bitmaps grandes para revelar patrones estadisticos. Los resultados son instructivos -- no todas las rutinas "aleatorias" son igualmente aleatorias.

Aqui hay cuatro generadores de esa coleccion, ordenados de mejor a peor calidad.

#### Generador CMWC de Patrik Rak (Mejor Calidad)

Este es un generador **Multiply-With-Carry Complementario** de Patrik Rak, usando el multiplicador 253 y un buffer circular de 8 bytes. Las matematicas detras de CMWC estan bien estudiadas: George Marsaglia demostro que ciertas combinaciones de multiplicador/buffer producen secuencias con periodos enormes. Con multiplicador 253 y tamano de buffer 8, el periodo teorico es (253^8 - 1) / 254 -- aproximadamente 2^66 valores antes de repetirse.

```z80
; Patrik Rak's CMWC PRNG
; Quality: Excellent -- passes visual bitmap tests
; Size:    ~30 bytes code + 8 bytes table
; Output:  A = pseudo-random byte
; Period:  ~2^66

patrik_rak_cmwc_rnd:
    ld   hl, .table
.smc_idx:
    ld   bc, 0              ; 10 T -- i (self-modifying)
    add  hl, bc             ; 11 T
    ld   a, c               ; 4 T
    inc  a                  ; 4 T
    and  7                  ; 7 T -- wrap index to 0-7
    ld   (.smc_idx+1), a    ; 13 T -- store new index
    ld   c, (hl)            ; 7 T -- y = q[i]
    ex   de, hl             ; 4 T
    ld   h, c               ; 4 T -- t = 256 * y
    ld   l, b               ; 4 T
    sbc  hl, bc             ; 15 T -- t = 255 * y
    sbc  hl, bc             ; 15 T -- t = 254 * y
    sbc  hl, bc             ; 15 T -- t = 253 * y
.smc_car:
    ld   c, 0               ; 7 T -- carry (self-modifying)
    add  hl, bc             ; 11 T -- t = 253 * y + c
    ld   a, h               ; 4 T
    ld   (.smc_car+1), a    ; 13 T -- c = t / 256
    ld   a, l               ; 4 T -- x = t % 256
    cpl                     ; 4 T -- x = ~x (complement)
    ld   (de), a            ; 7 T -- q[i] = x
    ret                     ; 10 T

.table:
    DB   82, 97, 120, 111, 102, 116, 20, 12
```

El algoritmo multiplica la entrada actual del buffer por 253, suma un valor de acarreo, almacena el nuevo acarreo y complementa el resultado. El buffer circular de 8 bytes significa que el espacio de estados del generador es vasto -- 8 bytes de buffer mas 1 byte de acarreo mas el indice, dando mucho mas estado interno del que cualquier generador de un solo registro puede lograr.

El veredicto de Gogin: **mejor calidad** de la coleccion. Al llenar un bitmap de 256x192, no emergen patrones visibles ni siquiera a escalas grandes.

#### Ion Random (Segundo Mejor)

Originalmente de Ion Shell para la calculadora TI-83, adaptado para Z80. Este generador mezcla el registro R con un bucle de retroalimentacion, logrando una aleatoriedad sorprendentemente buena con solo ~15 bytes:

```z80
; Ion Random
; Quality: Good -- minor patterns visible only at extreme scale
; Size:    ~15 bytes
; Output:  A = pseudo-random byte
; Origin:  Ion Shell (TI-83), adapted for Z80

ion_rnd:
.smc_seed:
    ld   hl, 0              ; 10 T -- seed (self-modifying)
    ld   a, r               ; 9 T -- read refresh counter
    ld   d, a               ; 4 T
    ld   e, (hl)            ; 7 T
    add  hl, de             ; 11 T
    add  a, l               ; 4 T
    xor  h                  ; 4 T
    ld   (.smc_seed+1), hl  ; 16 T -- update seed
    ret                     ; 10 T
```

La inyeccion del registro R significa que este generador produce secuencias diferentes dependiendo del contexto de llamada -- cuantas instrucciones se ejecutan entre llamadas afecta a R, que retroalimenta al estado. Para un bucle principal de demo con temporizado fijo, R avanza predeciblemente, pero la mezcla no lineal (ADD + XOR) aun produce buena salida. En un juego donde la entrada del jugador varia el patron de llamada, la contribucion de R anade verdadera impredecibilidad.

El veredicto de Gogin: **segundo mejor**. Muy compacto, buena calidad para su tamano.

#### XORshift de 16 bits (Mediocre)

Un generador XORshift de 16 bits -- la adaptacion Z80 de la conocida familia de Marsaglia:

```z80
; 16-bit XORshift PRNG
; Quality: Mediocre -- visible diagonal patterns in bitmap tests
; Size:    ~25 bytes
; Output:  A = pseudo-random byte (H or L)
; Period:  65535

xorshift_rnd:
.smc_state:
    ld   hl, 1              ; 10 T -- state (self-modifying, must not be 0)
    ld   a, h               ; 4 T
    rra                     ; 4 T
    ld   a, l               ; 4 T
    rra                     ; 4 T
    xor  h                  ; 4 T
    ld   h, a               ; 4 T
    ld   a, l               ; 4 T
    rra                     ; 4 T
    ld   a, h               ; 4 T
    rra                     ; 4 T
    xor  l                  ; 4 T
    ld   l, a               ; 4 T
    xor  h                  ; 4 T
    ld   h, a               ; 4 T
    ld   (.smc_state+1), hl ; 16 T -- update state
    ret                     ; 10 T
```

Los generadores XORshift son rapidos y simples, pero con solo 16 bits de estado el periodo es como maximo 65.535. Mas problematico, el patron de rotacion de bits crea rayas diagonales visibles cuando la salida se mapea a pixeles. Para un campo de estrellas rapido o efecto de particulas esto puede ser aceptable. Para cualquier cosa que llene areas grandes de pantalla con "ruido", los patrones se vuelven obvios.

#### Variante CMWC de Raxoft (Mediocre)

Una variante CMWC de Raxoft, similar en principio a la version de Patrik Rak pero con un arreglo de buffer diferente. Gogin encontro que producia **patrones visibles a escala** -- probablemente debido a como la propagacion del acarreo interactua con la indexacion del buffer. Lo incluimos en el ejemplo compilable (`examples/prng.a80`) por completitud, pero para uso en produccion, la version de Patrik Rak es estrictamente superior.

### El Enfoque Tribonacci de Elite

Vale la pena una breve mencion: el legendario *Elite* (1984) uso una secuencia tipo Tribonacci para su galaxia generada proceduralmente. Tres registros retroalimentan entre si en un ciclo, produciendo secuencias deterministas pero bien distribuidas. La idea clave era la reproducibilidad -- dada la misma semilla, la misma galaxia se genera cada vez, lo que significaba que todo el universo podia "caber" en unos pocos bytes de estado del generador. David Braben e Ian Bell usaron esto para generar 8 galaxias de 256 sistemas estelares cada una a partir de un punado de bytes de semilla. La tecnica esta mas cerca de una funcion hash que de un PRNG, pero el principio -- estado pequeno, complejidad aparente grande -- es el mismo que impulsa el sizecoding de demoscene.

### El Generador de Galaxias de Elite: Una Mirada Mas Profunda

El enfoque Tribonacci merece mas detalle porque ilustra un principio profundo: **un PRNG no es solo una fuente de numeros aleatorios -- es un algoritmo de compresion.**

David Braben e Ian Bell necesitaban 8 galaxias de 256 sistemas estelares, cada uno con un nombre, posicion, economia, tipo de gobierno y nivel tecnologico. Almacenar todo eso explicitamente consumiria kilobytes. En su lugar, almacenaron solo una semilla de 6 bytes por galaxia y un generador determinista que expandia cada semilla en los datos completos del sistema estelar. El generador era un bucle de retroalimentacion de tres registros -- cada paso rota y aplica XOR a tres valores de 16 bits:

```
; Elite's galaxy generator (conceptual, 6502 origin):
;   seed = [s0, s1, s2]  (three 16-bit words)
;   twist: s0' = s1, s1' = s2, s2' = s0 + s1 + s2  (mod 65536)
;   repeat twist for each byte of star system data
```

En el Z80, el mismo principio funciona con tres pares de registros. La operacion "twist" produce valores deterministas pero bien distribuidos. La propiedad crucial: dada la misma semilla, la misma galaxia se genera cada vez. La navegacion entre estrellas es simplemente volver a sembrar y regenerar.

Esta idea -- **estado pequeno, complejidad aparente grande** -- tambien impulsa el sizecoding de demoscene. Un intro de 256 bytes que llena la pantalla con patrones intrincados esta haciendo exactamente lo que Elite hizo: expandir una semilla diminuta en una salida grande y compleja a traves de un proceso determinista.

### Aleatoriedad Modelada

A veces quieres numeros que sean aleatorios pero sigan una distribucion especifica. Un PRNG plano uniforme da a cada valor la misma probabilidad, pero los fenomenos del mundo real raramente son uniformes: tasas de aparicion de enemigos, velocidades de particulas, alturas de terreno -- todos tienden a agruparse alrededor de valores preferidos.

Trucos comunes en el Z80:

- **Distribucion triangular** -- suma dos bytes aleatorios uniformes y desplaza a la derecha. La suma se agrupa alrededor del centro (128), produciendo variacion de "aspecto natural". Coste: dos llamadas al PRNG + ADD + SRL = ~20 T-states adicionales.

```z80
; Triangular random: result clusters around 128
    call patrik_rak_cmwc_rnd  ; A = uniform random
    ld   b, a
    call patrik_rak_cmwc_rnd  ; A = another uniform random
    add  a, b                 ; sum (wraps at 256)
    rra                       ; divide by 2 -> triangular distribution
```

- **Muestreo por rechazo** -- genera un numero aleatorio, rechaza valores fuera de tu rango deseado. Para rangos en potencia de dos esto es gratuito (solo AND con una mascara). Para rangos arbitrarios, itera hasta que el valor encaje.

- **Tablas ponderadas** -- almacena una tabla de consulta de 256 bytes donde cada valor de salida aparece en proporcion a su probabilidad deseada. Indexa con un byte aleatorio uniforme. La tabla cuesta 256 bytes pero la consulta es instantanea (7 T-states). Perfecto cuando la distribucion es compleja y fija.

- **PRNG como funcion hash** -- alimenta datos estructurados (coordenadas, numeros de fotograma) a traves del PRNG para obtener ruido determinista. Asi es como funcionan las texturas de plasma y ruido en sizecoding: `random(x XOR y XOR frame)` da un valor de aspecto diferente por pixel por fotograma, pero es enteramente reproducible.

### Semillas y Reproducibilidad

En una demo, la reproducibilidad es usualmente deseable: el efecto deberia verse igual cada vez que se ejecuta, porque el coder coreografio los visuales para coincidir con la musica. Siembra el PRNG una vez con un valor fijo y la secuencia es determinista.

En un juego, la impredecibilidad importa. Estrategias comunes de sembramiento:

- **Variable de sistema FRAMES ($5C78)** -- la ROM del Spectrum mantiene un contador de fotogramas de 3 bytes en la direccion $5C78 que se incrementa cada 1/50 de segundo desde el encendido. Leerlo da una semilla dependiente del tiempo que varia con cuanto tiempo ha estado funcionando la maquina. Art-top recomienda usarlo para inicializar la tabla CMWC de Patrik Rak:

```z80
; Seed Patrik Rak CMWC from FRAMES system variable
    ld   hl, $5C78            ; FRAMES (3 bytes, increments at 50 Hz)
    ld   a, (hl)              ; low byte -- most variable
    ld   de, patrik_rak_cmwc_rnd.table
    ld   b, 8
.seed_loop:
    xor  (hl)                 ; mix with FRAMES
    ld   (de), a              ; write to table
    inc  de
    rlca                      ; rotate for variety
    add  a, b                 ; add loop counter
    djnz .seed_loop
```

- **Lee R en un momento de entrada del usuario** -- el conteo exacto de instrucciones entre el reinicio y cuando el jugador presiona una tecla varia cada ejecucion. `LD A,R` en ese momento captura entropia de temporizado.
- **Acumulacion de contador de fotogramas** -- aplica XOR del registro R a un acumulador cada fotograma durante la pantalla de titulo; usa el valor acumulado como semilla cuando el juego comienza.
- **Combinar multiples fuentes** -- aplica XOR al R, al byte bajo de FRAMES, y un byte del bus flotante (en Spectrums 48K, leer ciertos puertos devuelve lo que la ULA esta buscando actualmente de la RAM -- una fuente de entropia posicional).

Para demos, simplemente inicializa el estado del generador a un valor conocido y dejalo. El ejemplo compilable (`examples/prng.a80`) muestra los cuatro generadores con semillas fijas.

### Tabla Comparativa

| Algoritmo | Tamano (bytes) | Velocidad (T-states) | Calidad | Periodo | Notas |
|-----------|---------------|---------------------|---------|--------|-------|
| Patrik Rak CMWC | ~30 + 8 tabla | ~170 | Excelente | ~2^66 | Mejor en general; buffer de 8 bytes |
| Ion Random | ~15 | ~75 | Buena | Depende de R | Compacto; mezcla registro R |
| XORshift 16 | ~25 | ~90 | Mediocre | 65.535 | Patrones diagonales visibles |
| Raxoft CMWC | ~35 + 10 tabla | ~180 | Mediocre | ~2^66 | Patrones visibles a escala |
| LD A,R solo | 2 | 9 | Pobre | 128 | NO es un PRNG; usar solo como semilla |

Para la mayoria del trabajo de demoscene, el **CMWC de Patrik Rak** es el claro ganador: excelente calidad, tamano razonable y un periodo tan largo que nunca se repetira durante una demo. Si el tamano del codigo es critico (sizecoding, intros de 256 bytes), **Ion Random** empaqueta una calidad notable en 15 bytes. XORshift es un recurso de emergencia cuando necesitas algo rapido y no te importa la calidad visual.

> **Creditos:** Coleccion de PRNG, evaluacion de calidad y pruebas de bitmap por **Gogin**. El generador CMWC de Patrik Rak se basa en la teoria de Multiply-With-Carry Complementario de George Marsaglia. Ion Random se origina en **Ion Shell** para la calculadora TI-83.

---

*Todos los conteos de ciclos en este capitulo son para temporizado Pentagon (sin estados de espera). En un Spectrum 48K estandar o Scorpion con memoria contendida, espera conteos mas altos para codigo ejecutandose en los 32K inferiores de RAM. Ver Apendice A para la referencia completa de temporizado.*
