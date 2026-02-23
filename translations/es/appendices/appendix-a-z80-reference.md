# Apéndice A: Referencia rápida de instrucciones Z80

> *"Una instrucción que debería tardar 7 T-states podría tardar 13 si cae en la peor fase del ciclo de contención."*
> -- Capítulo 1

Esto no es un manual completo del Z80. Es una tarjeta de referencia para programadores de la demoscene y de videojuegos en ZX Spectrum y Agon Light 2 -- las instrucciones que realmente usas, las temporizaciones que necesitas saber de memoria, y los patrones que ahorran T-states en los bucles internos.

Todos los conteos de T-states asumen **temporización de Pentagon** (sin contención). Los conteos de bytes son la longitud de codificación de la instrucción. Las columnas de banderas muestran: **S** (signo), **Z** (cero), **H** (medio acarreo), **P/V** (paridad/desbordamiento), **N** (resta), **C** (acarreo). Un guion significa sin cambio; un punto significa indefinido.

---

## Instrucciones de carga de 8 bits

| Instrucción | Bytes | T-states | Banderas | Notas |
|-------------|-------|----------|----------|-------|
| `LD r,r'` | 1 | 4 | ------ | Instrucción más rápida. r,r' = A,B,C,D,E,H,L |
| `LD r,n` | 2 | 7 | ------ | Carga inmediata |
| `LD r,(HL)` | 1 | 7 | ------ | Lectura de memoria vía HL |
| `LD (HL),r` | 1 | 7 | ------ | Escritura de memoria vía HL |
| `LD (HL),n` | 2 | 10 | ------ | Inmediato a memoria |
| `LD A,(BC)` | 1 | 7 | ------ | |
| `LD A,(DE)` | 1 | 7 | ------ | |
| `LD (BC),A` | 1 | 7 | ------ | |
| `LD (DE),A` | 1 | 7 | ------ | |
| `LD A,(nn)` | 3 | 13 | ------ | Dirección absoluta |
| `LD (nn),A` | 3 | 13 | ------ | Dirección absoluta |
| `LD r,(IX+d)` | 3 | 19 | ------ | Indexada. Costosa -- evitar en bucles internos |
| `LD (IX+d),r` | 3 | 19 | ------ | Indexada |
| `LD (IX+d),n` | 4 | 23 | ------ | Indexada inmediata |
| `LD A,I` | 2 | 9 | SZ0P0- | P/V = IFF2 |
| `LD A,R` | 2 | 9 | SZ0P0- | P/V = IFF2; R = contador de refresco |

---

## Instrucciones de carga de 16 bits

| Instrucción | Bytes | T-states | Banderas | Notas |
|-------------|-------|----------|----------|-------|
| `LD rr,nn` | 3 | 10 | ------ | rr = BC, DE, HL, SP |
| `LD HL,(nn)` | 3 | 16 | ------ | |
| `LD (nn),HL` | 3 | 16 | ------ | |
| `LD rr,(nn)` | 4 | 20 | ------ | rr = BC, DE, SP (prefijo ED) |
| `LD (nn),rr` | 4 | 20 | ------ | rr = BC, DE, SP (prefijo ED) |
| `LD SP,HL` | 1 | 6 | ------ | Configurar puntero de pila |
| `LD SP,IX` | 2 | 10 | ------ | |
| `PUSH rr` | 1 | 11 | ------ | rr = AF, BC, DE, HL. **5.5T por byte** |
| `POP rr` | 1 | 10 | ------ | **5T por byte** -- lectura de 2 bytes más rápida |
| `PUSH IX` | 2 | 15 | ------ | |
| `POP IX` | 2 | 14 | ------ | |

---

## Aritmética y lógica de 8 bits

| Instrucción | Bytes | T-states | Banderas | Notas |
|-------------|-------|----------|----------|-------|
| `ADD A,r` | 1 | 4 | SZ.V0C | |
| `ADD A,n` | 2 | 7 | SZ.V0C | |
| `ADD A,(HL)` | 1 | 7 | SZ.V0C | |
| `ADC A,r` | 1 | 4 | SZ.V0C | Suma con acarreo |
| `ADC A,n` | 2 | 7 | SZ.V0C | |
| `SUB r` | 1 | 4 | SZ.V1C | |
| `SUB n` | 2 | 7 | SZ.V1C | |
| `SUB (HL)` | 1 | 7 | SZ.V1C | |
| `SBC A,r` | 1 | 4 | SZ.V1C | Resta con acarreo |
| `CP r` | 1 | 4 | SZ.V1C | Comparar (SUB sin almacenar resultado) |
| `CP n` | 2 | 7 | SZ.V1C | |
| `CP (HL)` | 1 | 7 | SZ.V1C | |
| `AND r` | 1 | 4 | SZ1P00 | H siempre activado, C siempre desactivado |
| `AND n` | 2 | 7 | SZ1P00 | |
| `OR r` | 1 | 4 | SZ0P00 | Desactiva H y C |
| `OR n` | 2 | 7 | SZ0P00 | |
| `XOR r` | 1 | 4 | SZ0P00 | `XOR A` = poner A a cero en 4T/1B (vs `LD A,0` = 7T/2B) |
| `XOR n` | 2 | 7 | SZ0P00 | |
| `INC r` | 1 | 4 | SZ.V0- | **No** afecta al acarreo |
| `DEC r` | 1 | 4 | SZ.V1- | **No** afecta al acarreo |
| `INC (HL)` | 1 | 11 | SZ.V0- | Lectura-modificación-escritura |
| `DEC (HL)` | 1 | 11 | SZ.V1- | Lectura-modificación-escritura |
| `NEG` | 2 | 8 | SZ.V1C | A = 0 - A (negación en complemento a dos) |
| `DAA` | 1 | 4 | SZ.P-C | Ajuste BCD -- rara vez usado en demos |
| `CPL` | 1 | 4 | --1-1- | A = NOT A (complemento a uno) |
| `SCF` | 1 | 4 | --0-00 | Activar bandera de acarreo. N,H desactivados. Nuevo comportamiento en CMOS |
| `CCF` | 1 | 4 | --.-0. | Complementar acarreo. H = C anterior |

---

## Aritmética de 16 bits

| Instrucción | Bytes | T-states | Banderas | Notas |
|-------------|-------|----------|----------|-------|
| `ADD HL,rr` | 1 | 11 | --.?0C | rr = BC, DE, HL, SP. Solo afecta H, N, C |
| `ADC HL,rr` | 2 | 15 | SZ.V0C | Conjunto completo de banderas |
| `SBC HL,rr` | 2 | 15 | SZ.V1C | Conjunto completo de banderas |
| `INC rr` | 1 | 6 | ------ | No afecta a ninguna bandera |
| `DEC rr` | 1 | 6 | ------ | No afecta a ninguna bandera |
| `ADD IX,rr` | 2 | 15 | --.?0C | rr = BC, DE, IX, SP |

**Punto clave:** `INC rr` y `DEC rr` **no** activan la bandera de cero. No puedes usar `DEC BC / JR NZ` como contador de bucle de 16 bits. Usa `DEC B / JR NZ` para bucles de 8 bits con `DJNZ`, o comprueba BC explícitamente.

---

## Rotación y desplazamiento

| Instrucción | Bytes | T-states | Banderas | Notas |
|-------------|-------|----------|----------|-------|
| `RLCA` | 1 | 4 | --0-0C | Rotar A a la izquierda, bit 7 al acarreo y bit 0 |
| `RRCA` | 1 | 4 | --0-0C | Rotar A a la derecha, bit 0 al acarreo y bit 7 |
| `RLA` | 1 | 4 | --0-0C | Rotar A a la izquierda a través del acarreo |
| `RRA` | 1 | 4 | --0-0C | Rotar A a la derecha a través del acarreo. **Clave para bucles de multiplicación** |
| `RLC r` | 2 | 8 | SZ0P0C | Prefijo CB. Conjunto completo de banderas |
| `RRC r` | 2 | 8 | SZ0P0C | |
| `RL r` | 2 | 8 | SZ0P0C | Rotar a la izquierda a través del acarreo |
| `RR r` | 2 | 8 | SZ0P0C | Rotar a la derecha a través del acarreo |
| `SLA r` | 2 | 8 | SZ0P0C | Desplazamiento aritmético a la izquierda. Bit 0 = 0 |
| `SRA r` | 2 | 8 | SZ0P0C | Desplazamiento aritmético a la derecha. Bit 7 preservado (extensión de signo) |
| `SRL r` | 2 | 8 | SZ0P0C | Desplazamiento lógico a la derecha. Bit 7 = 0 |
| `RLC (HL)` | 2 | 15 | SZ0P0C | Lectura-modificación-escritura |
| `RL (HL)` | 2 | 15 | SZ0P0C | Desplazar datos de píxel a la izquierda |
| `RR (HL)` | 2 | 15 | SZ0P0C | Desplazar datos de píxel a la derecha |
| `SLA (HL)` | 2 | 15 | SZ0P0C | |
| `SRL (HL)` | 2 | 15 | SZ0P0C | |
| `RLD` | 2 | 18 | SZ0P0- | Rotar nibbles de (HL) a la izquierda a través de A. Útil para gráficos de nibble |
| `RRD` | 2 | 18 | SZ0P0- | Rotar nibbles de (HL) a la derecha a través de A |

**Nota para la demoscene:** `RLA`/`RRA` (4T, 1 byte) solo afectan al acarreo y a los bits 3,5 de F. Las versiones con prefijo CB `RL r`/`RR r` (8T, 2 bytes) activan todas las banderas. En bucles de multiplicación, las versiones del acumulador ahorran la mitad del coste.

---

## Manipulación de bits

| Instrucción | Bytes | T-states | Banderas | Notas |
|-------------|-------|----------|----------|-------|
| `BIT b,r` | 2 | 8 | .Z1.0- | Comprobar bit b del registro |
| `BIT b,(HL)` | 2 | 12 | .Z1.0- | Comprobar bit b de la memoria |
| `SET b,r` | 2 | 8 | ------ | Activar bit b del registro |
| `SET b,(HL)` | 2 | 15 | ------ | Activar bit b de la memoria. **Usado en dibujo de líneas** |
| `RES b,r` | 2 | 8 | ------ | Desactivar bit b del registro |
| `RES b,(HL)` | 2 | 15 | ------ | Desactivar bit b de la memoria |

---

## Salto, llamada, retorno

| Instrucción | Bytes | T-states | Banderas | Notas |
|-------------|-------|----------|----------|-------|
| `JP nn` | 3 | 10 | ------ | Salto absoluto |
| `JP cc,nn` | 3 | 10 | ------ | Condicional: NZ, Z, NC, C, PO, PE, P, M. **Misma velocidad tomado o no** |
| `JR e` | 2 | 12 | ------ | Salto relativo (-128 a +127) |
| `JR cc,e` | 2 | 12/7 | ------ | cc = NZ, Z, NC, C solamente. **7T si no se toma** |
| `JP (HL)` | 1 | 4 | ------ | Saltar a la dirección en HL. Salto indirecto más rápido |
| `JP (IX)` | 2 | 8 | ------ | Saltar a la dirección en IX |
| `DJNZ e` | 2 | 13/8 | ------ | Dec B, saltar si NZ. **13T tomado, 8T no tomado** |
| `CALL nn` | 3 | 17 | ------ | Apilar PC, saltar a nn |
| `CALL cc,nn` | 3 | 17/10 | ------ | 10T si no se toma |
| `RET` | 1 | 10 | ------ | Desapilar PC. **Usado para despacho con encadenamiento RET** |
| `RET cc` | 1 | 11/5 | ------ | 5T si no se toma |
| `RST p` | 1 | 11 | ------ | Llamada a $00,$08,$10,$18,$20,$28,$30,$38 |

**Comparaciones clave para despacho:**

| Método | T-states | Bytes |
|--------|----------|-------|
| `CALL nn` | 17 | 3 |
| `RET` (como despacho en encadenamiento RET) | 10 | 1 |
| `JP (HL)` | 4 | 1 |
| `JP nn` | 10 | 3 |

---

## Instrucciones de E/S

| Instrucción | Bytes | T-states | Banderas | Notas |
|-------------|-------|----------|----------|-------|
| `OUT (n),A` | 2 | 11 | ------ | Dirección del puerto = `(A << 8) | n`. Borde: `OUT ($FE),A` |
| `IN A,(n)` | 2 | 11 | ------ | Dirección del puerto = `(A << 8) | n`. Teclado: `IN A,($FE)` |
| `OUT (C),r` | 2 | 12 | ------ | Dirección del puerto = BC. **Escritura de registros AY** |
| `IN r,(C)` | 2 | 12 | SZ0P0- | Dirección del puerto = BC. Activa banderas |
| `OUTI` | 2 | 16 | .Z..1. | Sacar (HL) al puerto (C), inc HL, dec B |
| `OTIR` | 2 | 21/16 | 01..1. | Repetir OUTI hasta B=0. 16T en el último |
| `OUTD` | 2 | 16 | .Z..1. | Sacar (HL) al puerto (C), inc HL, dec B |

**Direcciones de puerto del AY-3-8910 en ZX Spectrum 128K:**

| Puerto | Dirección | Propósito |
|--------|-----------|-----------|
| Selección de registro | `$FFFD` | `LD BC,$FFFD : OUT (C),A` |
| Escritura de datos | `$BFFD` | `LD B,$BF : OUT (C),r` |
| Lectura de datos | `$FFFD` | `IN A,(C)` |

Secuencia típica de escritura de registro AY (24T + sobrecarga):

```z80
    ld   bc, $FFFD      ; 10T  AY register select port
    out  (c), a          ; 12T  select register number (in A)
    ld   b, $BF          ;  7T  switch to data port $BFFD
    out  (c), e          ; 12T  write value (in E)
                         ; --- 41T total
```

---

## Instrucciones de bloque

| Instrucción | Bytes | T-states | Banderas | Notas |
|-------------|-------|----------|----------|-------|
| `LDI` | 2 | 16 | --0.0- | (DE) = (HL), inc HL, inc DE, dec BC. P/V = (BC != 0) |
| `LDIR` | 2 | 21/16 | --000- | Repetir LDI. 21T por byte, 16T último byte |
| `LDD` | 2 | 16 | --0.0- | (DE) = (HL), dec HL, dec DE, dec BC |
| `LDDR` | 2 | 21/16 | --000- | Repetir LDD. 21T por byte, 16T último byte |
| `CPI` | 2 | 16 | SZ.?1- | Comparar A con (HL), inc HL, dec BC |
| `CPIR` | 2 | 21/16 | SZ.?1- | Repetir CPI. Se detiene al encontrar coincidencia o BC=0 |
| `CPD` | 2 | 16 | SZ.?1- | Comparar A con (HL), dec HL, dec BC |
| `CPDR` | 2 | 21/16 | SZ.?1- | Repetir CPD |

**Coste por byte de LDI vs LDIR:**

| Método | Por byte | 256 bytes | 32 bytes | Ahorro |
|--------|----------|-----------|----------|--------|
| LDIR | 21T (16T último) | 5,371T | 672T | -- |
| Cadena LDI | 16T | 4,096T | 512T | 24% más rápido |

Una cadena LDI desenrollada cuesta 2 bytes por LDI (`$ED $A0`), pero ahorra 5T por byte -- 24% más rápido que LDIR. Consulta el Capítulo 3 para la aritmética de punto de entrada con cadenas LDI.

---

## Intercambio y miscelánea

| Instrucción | Bytes | T-states | Banderas | Notas |
|-------------|-------|----------|----------|-------|
| `EX DE,HL` | 1 | 4 | ------ | Intercambiar DE y HL. **Intercambio de punteros gratuito** |
| `EX AF,AF'` | 1 | 4 | ------ | Intercambiar AF con AF' sombra |
| `EXX` | 1 | 4 | ------ | Intercambiar BC,DE,HL con BC',DE',HL'. **6 registros en 4T** |
| `EX (SP),HL` | 1 | 19 | ------ | Intercambiar HL con la cima de la pila. Útil para paso de parámetros |
| `EX (SP),IX` | 2 | 23 | ------ | Intercambiar IX con la cima de la pila |
| `DI` | 1 | 4 | ------ | Desactivar interrupciones. **Requerido antes de trucos con la pila** |
| `EI` | 1 | 4 | ------ | Activar interrupciones. Retardado una instrucción |
| `HALT` | 1 | 4+ | ------ | Esperar interrupción. La instrucción de sincronización de fotograma |
| `NOP` | 1 | 4 | ------ | Relleno, temporización |
| `IM 1` | 2 | 8 | ------ | Modo de interrupción 1 (RST $38). Modo estándar del Spectrum |
| `IM 2` | 2 | 8 | ------ | Modo de interrupción 2. Usa el registro I como byte alto de la tabla de vectores |

---

## Las instrucciones "rápidas" de la demoscene

Estas son las instrucciones más baratas por categoría -- los bloques de construcción de cada bucle interno optimizado.

### Movimiento registro a registro más rápido

`LD r,r'` -- **4T, 1 byte**. El coste mínimo de cualquier instrucción Z80. Incluye `LD A,A` (efectivamente un NOP que no afecta a las banderas).

### Forma más rápida de poner un registro a cero

`XOR A` -- **4T, 1 byte**. Pone A a cero, activa la bandera Z, desactiva el acarreo. Compara con `LD A,0` a 7T/2 bytes. Usa siempre `XOR A` a menos que necesites preservar las banderas.

### Lectura de memoria más rápida

`LD A,(HL)` -- **7T, 1 byte**. El coste mínimo para cualquier lectura de memoria. Otras fuentes de registro (`LD A,(BC)`, `LD A,(DE)`) también son 7T/1 byte, pero HL es el único puntero que soporta `LD r,(HL)` para todos los registros.

### Escritura de memoria más rápida

`LD (HL),r` -- **7T, 1 byte**. Empatada con la lectura. Escribir a un puntero BC o DE (`LD (BC),A`, `LD (DE),A`) también es 7T/1B pero solo funciona con A.

### Escritura de 2 bytes más rápida

`PUSH rr` -- **11T, 1 byte** para 2 bytes = **5.5T por byte**. La forma más rápida de escribir datos en memoria, pero solo donde apunta SP (hacia abajo). Requiere DI y secuestrar el puntero de pila. Ver Capítulo 3.

### Lectura de 2 bytes más rápida

`POP rr` -- **10T, 1 byte** para 2 bytes = **5T por byte**. Incluso más rápido que PUSH para lectura. Usa con SP apuntando a una tabla de datos para búsquedas ultrarrápidas.

### Copia de bloque más rápida

| Método | Por byte | Notas |
|--------|----------|-------|
| Par `PUSH/POP` | 5.25T | Escritura: 5.5T, Lectura: 5T. Pero necesita secuestro de SP |
| `LDI` (cadena desenrollada) | 16T | Sin configuración por byte. 24% más rápido que LDIR |
| `LDIR` | 21T | Una sola instrucción, pero lenta por byte |
| `LD (HL),r` + `INC HL` | 13T | Cuerpo del bucle manual (sin contador de bucle) |
| `LD (HL),r` + `INC L` | 11T | Solo funciona dentro de una página de 256 bytes |

### E/S más rápida

`OUT (n),A` -- **11T, 2 bytes**. Para direcciones de puerto fijas (borde, etc.). Para puertos variables (AY), `OUT (C),r` a 12T/2 bytes es la única opción.

### Intercambio de punteros más rápido

`EX DE,HL` -- **4T, 1 byte**. Intercambiar el contenido de DE y HL instantáneamente. Ningún otro intercambio de registros es tan barato. `EXX` también 4T/1 byte pero intercambia los tres pares a la vez.

### Bucle condicional más rápido

`DJNZ e` -- **13T tomado, 8T no tomado, 2 bytes**. Decrementa B y salta. Compara con `DEC B / JR NZ,e` a 4+12 = 16T/3 bytes. DJNZ ahorra 3T y 1 byte por iteración.

### Salto indirecto más rápido

`JP (HL)` -- **4T, 1 byte**. Salta a la dirección en HL. A pesar del mnemónico engañoso, esto NO lee de la memoria en (HL) -- carga PC con el valor de HL. Indispensable para tablas de salto y gotos calculados.

---

## Instrucciones no documentadas

Estas instrucciones no están en la documentación oficial de Zilog pero funcionan de forma fiable en todo el silicio Z80 (NMOS y CMOS), todos los clones ZX Spectrum, y el eZ80. Son ampliamente usadas en código de la demoscene y soportadas por sjasmplus.

### IXH, IXL, IYH, IYL (registros de medio índice)

Los registros IX e IY pueden dividirse en mitades de 8 bits, accedidos anteponiendo las instrucciones normales de H/L con DD/FD:

| Instrucción | Bytes | T-states | Notas |
|-------------|-------|----------|-------|
| `LD A,IXH` | 2 | 8 | Leer byte alto de IX |
| `LD A,IXL` | 2 | 8 | Leer byte bajo de IX |
| `LD IXH,A` | 2 | 8 | Escribir byte alto de IX |
| `LD IXL,n` | 3 | 11 | Inmediato en IX bajo |
| `ADD A,IXL` | 2 | 8 | Aritmética con mitades de IX |
| `INC IXH` | 2 | 8 | Incrementar byte alto de IX |
| `DEC IXL` | 2 | 8 | Decrementar byte bajo de IX |

**Uso en la demoscene:** Dos registros extra de 8 bits para contadores, acumuladores o valores pequeños sin tocar el archivo de registros principal. Particularmente útiles cuando BC/DE/HL están todos ocupados como punteros. Coste: 4T más que la operación equivalente con registro principal.

Sintaxis sjasmplus: `IXH`, `IXL`, `IYH`, `IYL` (también acepta `HX`, `LX`, `HY`, `LY`).

### SLL r (Shift Left Logical)

| Instrucción | Bytes | T-states | Notas |
|-------------|-------|----------|-------|
| `SLL r` | 2 | 8 | Desplazar a la izquierda, bit 0 puesto a 1 (no 0) |
| `SLL (HL)` | 2 | 15 | Lo mismo para memoria |

`SLL` desplaza a la izquierda y pone el bit 0 a 1 (a diferencia de `SLA` que pone el bit 0 a 0). Código de operación (opcode): CB 30+r. Ocasionalmente útil para construir patrones de bits.

Sintaxis sjasmplus: `SLL` o `SLI` o `SL1`.

### OUT (C),0

| Instrucción | Bytes | T-states | Notas |
|-------------|-------|----------|-------|
| `OUT (C),0` | 2 | 12 | Sacar cero al puerto BC |

Código de operación (opcode) `ED 71`. Saca cero al puerto direccionado por BC. En Z80 CMOS (incluyendo eZ80), saca $FF en su lugar. **No portable a Agon Light 2.** En Z80 NMOS (todos los Spectrum reales), saca $00 de forma fiable.

Sintaxis sjasmplus: `OUT (C),0`.

### Operaciones de bits no documentadas con prefijo CB en (IX+d)

Instrucciones como `SET b,(IX+d),r` realizan simultáneamente una operación de bits en memoria en (IX+d) y copian el resultado en el registro r. Son instrucciones de 4 bytes (DD CB dd op) que tardan 23T. Ocasionalmente útiles pero raramente críticas.

---

## Hoja de referencia de efectos en banderas

Saber qué instrucciones activan qué banderas te permite evitar instrucciones `CP` o `AND A` redundantes -- una fuente común de T-states desperdiciados.

### Instrucciones que activan todas las banderas aritméticas (S, Z, H, P/V, N, C)

- `ADD A,r/n/(HL)` -- P/V = desbordamiento
- `ADC A,r/n/(HL)` -- P/V = desbordamiento
- `SUB r/n/(HL)` -- P/V = desbordamiento
- `SBC A,r/n/(HL)` -- P/V = desbordamiento
- `CP r/n/(HL)` -- Mismas banderas que SUB pero A sin cambio
- `NEG` -- P/V = desbordamiento
- `ADC HL,rr` -- P/V = desbordamiento
- `SBC HL,rr` -- P/V = desbordamiento

### Instrucciones que activan Z y S (pero NO el acarreo)

- `INC r` / `DEC r` -- C sin cambio. **No se puede comprobar el acarreo después de INC/DEC.**
- `INC (HL)` / `DEC (HL)` -- Igual
- `AND r/n/(HL)` -- C siempre 0, H siempre 1
- `OR r/n/(HL)` -- C siempre 0, H siempre 0
- `XOR r/n/(HL)` -- C siempre 0, H siempre 0
- `IN r,(C)` -- C sin cambio
- `BIT b,r/(HL)` -- Z = complemento del bit comprobado, C sin cambio
- Todas las rotaciones/desplazamientos con prefijo CB -- Conjunto completo de banderas incluyendo C

### Instrucciones que activan SOLO banderas relacionadas con el acarreo

- `ADD HL,rr` -- Solo H y C (S, Z, P/V sin cambio)
- `RLCA` / `RRCA` / `RLA` / `RRA` -- Solo C, H=0, N=0 (S, Z, P/V sin cambio)
- `SCF` -- C=1, H=0, N=0
- `CCF` -- C invertido, H = C anterior, N=0

### Instrucciones que NO activan banderas

- `LD` (todas las variantes)
- `INC rr` / `DEC rr` (inc/dec de 16 bits)
- `PUSH` / `POP` (excepto POP AF que restaura las banderas)
- `EX` / `EXX`
- `DI` / `EI` / `HALT` / `NOP`
- `JP` / `JR` / `DJNZ` / `CALL` / `RET` / `RST`
- `OUT (n),A` / `IN A,(n)` (las versiones sin CB)

### Trucos prácticos

**Comprobar A igual a cero sin CP 0:**
```z80
    or   a              ; 4T  sets Z if A=0, clears C
    and  a              ; 4T  same effect, but also sets H
```

**Comprobar el acarreo después de INC/DEC de 16 bits:** No puedes. `INC rr`/`DEC rr` no activan banderas. Para comprobar si un registro de 16 bits llegó a cero:
```z80
    ld   a, b           ; 4T
    or   c              ; 4T  Z set if BC = 0
```

**Omitir CP después de SUB:** Si ya realizaste `SUB r`, las banderas están activadas -- no lo sigas con `CP` u `OR A`.

**INC/DEC preservan el acarreo:** Usa `INC r`/`DEC r` entre aritmética de múltiple precisión sin destruir la cadena de acarreo.

---

## Arquitectura de registros

### Conjunto de registros principal

```
  A   F          Accumulator + Flags
  B   C          Counter (B for DJNZ) + general
  D   E          General purpose pair
  H   L          Primary memory pointer (HL is the "accumulator pair")
```

### Registros especiales

```
  SP             Stack pointer (16-bit)
  PC             Program counter (16-bit)
  IX             Index register (16-bit, DD prefix, +4T penalty)
  IY             Index register (16-bit, FD prefix, +4T penalty)
                 NOTE: IY is used by the Spectrum ROM interrupt handler.
                 Do not use IY unless you have DI or IM2 set up.
  I              Interrupt vector page (used in IM2)
  R              Refresh counter (7-bit, increments every M1 cycle)
```

### Registros sombra

```
  A'  F'         Swapped with EX AF,AF'
  B'  C'         \
  D'  E'          | Swapped all three with EXX
  H'  L'         /
```

`EXX` intercambia BC/DE/HL con BC'/DE'/HL' en **4T**. Esto te da seis registros extra de 8 bits (o tres pares extra de 16 bits) a un coste prácticamente nulo. Uso común: mantener punteros en el conjunto sombra e intercambiarlos según sea necesario.

**Advertencia:** El manejador de interrupciones de la ROM del Spectrum (IM1) usa los registros sombra. Si las interrupciones están activadas, los datos de `EXX`/`EX AF,AF'` se corromperán en cada interrupción. Siempre usa `DI` antes de usar registros sombra, o cambia a IM2 con tu propio manejador.

### Emparejamiento de registros para instrucciones

| Par | Usado por | Notas |
|-----|-----------|-------|
| BC | `DJNZ` (solo B), `OUT (C),r`, `IN r,(C)`, instrucciones de bloque (contador) | B = contador de bucle, C = byte bajo del puerto |
| DE | `EX DE,HL`, `LDI`/`LDIR` (destino), `LD (DE),A` | Puntero de destino para operaciones de bloque |
| HL | Casi todo: `LD r,(HL)`, `ADD HL,rr`, `JP (HL)`, `PUSH/POP`, `LDI` (origen) | El puntero universal |
| AF | `PUSH AF`/`POP AF`, `EX AF,AF'` | A = acumulador, F = banderas |
| SP | `PUSH`/`POP`, `LD SP,HL`, `EX (SP),HL` | Secuestrar para trucos con datos |

---

## Secuencias de instrucciones comunes

### Cálculo de dirección de píxel (dirección de pantalla a partir de Y,X)

Convierte coordenadas de pantalla a dirección de memoria de vídeo del ZX Spectrum. Entrada: B = Y (0-191), C = X (0-255). Salida: HL = dirección del byte de pantalla, A = máscara de bit.

```z80
; pixel_addr: calculate screen address from coordinates
; Input:  B = Y (0-191), C = X (0-255)
; Output: HL = byte address, A = pixel bit position
; Cost:   ~55 T-states
;
pixel_addr:
    ld   a, b           ; 4T   A = Y
    and  $07             ; 7T   scanline within char cell (SSS)
    or   $40             ; 7T   add screen base ($4000 high byte)
    ld   h, a           ; 4T   H = 010 00 SSS (partial)
    ld   a, b           ; 4T   A = Y again
    rra                 ; 4T   \
    rra                 ; 4T    | shift character row (TTRR RRR)
    rra                 ; 4T   /  to bits 4-3
    and  $18             ; 7T   mask TT (third bits)
    or   h              ; 4T   H = 010 TT SSS
    ld   h, a           ; 4T
    ld   a, c           ; 4T   A = X
    rra                 ; 4T   \
    rra                 ; 4T    | X / 8
    rra                 ; 4T   /
    and  $1F             ; 7T   mask to 5-bit column
    ld   l, a           ; 4T   L = 000 CCCCC
```

### DOWN_HL: bajar una fila de píxeles

La primitiva gráfica más utilizada en el Spectrum. El caso común (dentro de la celda de caracteres) cuesta solo 20T.

```z80
; down_hl: advance HL one pixel row down
; Input:  HL = screen address
; Output: HL = address one row below
; Cost:   20T (common), 46T (third boundary), 77T (char boundary)
;
down_hl:
    inc  h              ; 4T   try next scanline
    ld   a, h           ; 4T
    and  7              ; 7T   crossed character boundary?
    ret  nz             ; 5T   no: done (20T total)

    ld   a, l           ; 4T   yes: advance character row
    add  a, 32          ; 7T   L += 32
    ld   l, a           ; 4T
    ret  c              ; 5T   carry = crossed third (46T total)

    ld   a, h           ; 4T   same third: undo extra H increment
    sub  8              ; 7T
    ld   h, a           ; 4T
    ret                 ; 10T  (77T total)
```

### Multiplicación sin signo 8x8 (desplazamiento y suma)

De Dark / X-Trade, Spectrum Expert #01 (1997). Usada en matrices de rotación y transformaciones de coordenadas.

```z80
; mulu112: 8x8 unsigned multiply
; Input:  B = multiplicand, C = multiplier
; Output: A:C = 16-bit result (A = high, C = low)
; Cost:   196-204 T-states
;
mulu112:
    ld   a, 0           ; 7T   clear accumulator
    ld   d, 8           ; 7T   8 bits

.loop:
    rr   c              ; 8T   shift multiplier bit into carry
    jr   nc, .noadd     ; 7/12T
    add  a, b           ; 4T   add multiplicand
.noadd:
    rra                 ; 4T   shift result right
    dec  d              ; 4T
    jr   nz, .loop      ; 12T
    ret                 ; 10T
```

### Escritura de registro AY

Secuencia estándar para escribir en el chip de sonido AY-3-8910 en ZX Spectrum 128K.

```z80
; ay_write: write value to AY register
; Input:  A = register number (0-15), E = value
; Cost:   41 T-states (plus CALL/RET overhead)
;
ay_write:
    ld   bc, $FFFD      ; 10T  register select port
    out  (c), a          ; 12T  select register
    ld   b, $BF          ;  7T  data port ($BFFD)
    out  (c), e          ; 12T  write value
    ret                  ; 10T
```

### Comparación de 16 bits (HL vs DE)

El Z80 no tiene comparación directa de 16 bits. Usa `SBC` y restaura.

```z80
; Compare HL with DE (sets flags as if HL - DE)
; Destroys: A (if using the OR method for equality)
;
; For equality only:
    or   a              ; 4T   clear carry
    sbc  hl, de         ; 15T  HL = HL - DE, flags set
    add  hl, de         ; 11T  restore HL
                        ; --- 30T total, Z flag valid
```

### Relleno de pantalla basado en pila

La forma más rápida de rellenar la pantalla con un patrón. Ver Capítulo 3.

```z80
; fill_screen: fill 6144 bytes using PUSH
; Input:  HL = 16-bit fill pattern
; Cost:   ~36,000 T-states (vs ~129,000 with LDIR)
;
fill_screen:
    di                          ; 4T
    ld   (restore_sp + 1), sp   ; 20T  save SP (self-modifying)
    ld   sp, $5800              ; 10T  end of pixel area

    ld   b, 192                 ; 7T   192 iterations x 16 pushes x 2 bytes = 6144
.loop:
    REPT 16
        push hl                 ; 11T  x 16 = 176T
    ENDR
    djnz .loop                  ; 13T/8T

restore_sp:
    ld   sp, $0000              ; 10T  self-modified
    ei                          ; 4T
    ret                         ; 10T
```

### Iteración rápida de filas de píxeles (contadores divididos)

Del análisis de DOWN_HL de Introspec (Hype, 2020). Elimina todas las bifurcaciones condicionales del bucle interno. Coste total para 192 filas: 2,343T vs 5,922T para llamadas ingenuas a DOWN_HL.

```z80
; iterate all 192 rows with minimal overhead
; HL starts at $4000
;
iterate_screen:
    ld   hl, $4000          ; 10T
    ld   c, 3               ; 7T   three thirds

.third:
    ld   b, 8               ; 7T   eight character rows per third

.char_row:
    push hl                 ; 11T  save char row start

    REPT 7
        ; ... process row using HL ...
        inc  h              ; 4T   next scanline (NO branching)
    ENDR
    ; ... process 8th row ...

    pop  hl                 ; 10T  restore char row start
    ld   a, l              ; 4T
    add  a, 32             ; 7T   next character row
    ld   l, a              ; 4T
    djnz .char_row         ; 13T/8T

    ld   a, h              ; 4T
    add  a, 8              ; 7T   next third
    ld   h, a              ; 4T
    dec  c                 ; 4T
    jr   nz, .third        ; 12T/7T
```

---

## Comparaciones rápidas de coste

Para decisiones de bucle interno, estas comparaciones son las más importantes:

| Operación | Forma lenta | Forma rápida | Ahorro |
|-----------|-------------|--------------|--------|
| Poner A a cero | `LD A,0` (7T, 2B) | `XOR A` (4T, 1B) | 3T, 1B |
| Comprobar A=0 | `CP 0` (7T, 2B) | `OR A` (4T, 1B) | 3T, 1B |
| Copiar 1 byte a mem | `LD (HL),A`+`INC HL` (13T) | `LDI` (16T) | LDI es más lento pero auto-incrementa DE también |
| Copiar N bytes | `LDIR` (21T/byte) | N x `LDI` (16T/byte) | 24% más rápido, cuesta 2N bytes de código |
| Rellenar 2 bytes | `LD (HL),A`+`INC HL` x2 (26T) | `PUSH rr` (11T) | 58% más rápido, necesita secuestro de SP |
| Bucle de 8 bits | `DEC B`+`JR NZ` (16T, 3B) | `DJNZ` (13T, 2B) | 3T, 1B por iteración |
| Llamada indirecta | `CALL nn` (17T, 3B) | `RET` vía lista de renderizado (10T, 1B) | 7T, 2B por despacho |
| Intercambio de registros | `LD A,H`+`LD H,D`+`LD D,A` (12T, 3B) | `EX DE,HL` (4T, 1B) | 8T, 2B |
| Guardar 6 registros | 3 x `PUSH` (33T, 3B) | `EXX` (4T, 1B) | 29T, 2B |

---

## Referencia de tamaño de codificación de instrucciones

Para sizecoding y estimar la densidad de código:

| Prefijo | Instrucciones | Bytes extra | T-states extra |
|---------|---------------|-------------|----------------|
| Ninguno | La mayoría de ops de 8 bits, LD, ADD, INC, PUSH, POP, JP, JR | 0 | 0 |
| CB | Ops de bits, desplazamientos, rotaciones en registros | +1 | +4 típicamente |
| ED | Ops de bloque, ADC/SBC de 16 bits, IN/OUT (C), LD rr,(nn) | +1 | varía |
| DD | Operaciones indexadas con IX | +1 | +4 a +8 |
| FD | Operaciones indexadas con IY | +1 | +4 a +8 |
| DD CB | Bit/desplazamiento/rotación en (IX+d) | +2 | +8 a +12 |

**Consejo para sizecoding:** Evita instrucciones indexadas con IX/IY cuando sea posible. `LD A,(IX+5)` son 3 bytes/19T. `LD L,5 / LD A,(HL)` son 3 bytes/11T si H ya contiene la página. Los registros índice son convenientes pero costosos.

---

> **Fuentes:** Zilog Z80 CPU User Manual (UM0080); Sean Young, "The Undocumented Z80 Documented" (2005); Dark / X-Trade, "Programming Algorithms" (Spectrum Expert #01, 1997); Introspec, "Once more about DOWN_HL" (Hype, 2020); Capítulo 1 (arnés de temporización); Capítulo 3 (patrones del toolbox); Capítulo 4 (multiplicación, división)
