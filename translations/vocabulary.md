# Translation Vocabulary — "Coding the Impossible"

Consistent terminology across all translated editions. Source language: English.

## Rules

1. **Never translate**: proper names (Dark, Introspec, n1k-o, Robus, sq), product names (ZX Spectrum, Pentagon, Scorpion, Agon Light 2, sjasmplus, DeZog, Arkos Tracker), chip designations (Z80, AY-3-8910, ULA, eZ80), file extensions (.a80, .scr, .tap, .sna, .trd), hex notation ($4000, $FF), demo/game titles (Illusion, Eager, GABBA, Old Tower), publication names (Spectrum Expert, Hype, Born Dead, Black Crow), register names (A, B, C, HL, IX, SP, PC)
2. **Keep in English**: code keywords (ORG, EQU, DB, DW, PUSH, POP, LD, JR, DJNZ, CALL, RET, HALT), code comments in examples, API/function names
3. **Transliterate if needed**: demoscene slang may stay in original (English or Russian) with a brief gloss in target language
4. **Translate**: all prose, section headings, figure captions, glossary definitions, appendix text

---

## A. Timing & Performance

| English | Spanish (es) | Russian (ru) | Ukrainian (uk) | Notes |
|---------|-------------|-------------|----------------|-------|
| T-state | T-state | такт (T-state) | такт (T-state) | Keep "T-state" in parentheses on first use |
| clock cycle | ciclo de reloj | тактовый цикл | тактовий цикл | |
| frame | fotograma | кадр | кадр | |
| frame budget | presupuesto de fotograma | бюджет кадра | бюджет кадру | |
| scanline | línea de escaneo | строка развёртки | рядок розгортки | |
| contended memory | memoria contendida | спорная память | спірна пам'ять | Also: "конфликтная память" (ru) |
| machine cycle (M-cycle) | ciclo de máquina | машинный цикл | машинний цикл | |
| border time | tiempo de borde | время бордюра | час бордюру | |
| timing harness | arnés de temporización | тестовая обвязка | тестова обв'язка | |
| interrupt | interrupción | прерывание | переривання | |
| latency | latencia | задержка | затримка | |

## B. Hardware

| English | Spanish (es) | Russian (ru) | Ukrainian (uk) | Notes |
|---------|-------------|-------------|----------------|-------|
| screen memory | memoria de pantalla | экранная память | екранна пам'ять | |
| attribute area | área de atributos | область атрибутов | область атрибутів | |
| attribute clash | conflicto de atributos | конфликт атрибутов | конфлікт атрибутів | |
| interleaved screen layout | diseño de pantalla entrelazado | чересстрочная раскладка экрана | черезрядкова розкладка екрану | |
| shadow screen | pantalla sombra | теневой экран | тіньовий екран | |
| memory bank | banco de memoria | банк памяти | банк пам'яті | |
| port | puerto | порт | порт | |
| display page | página de visualización | страница экрана | сторінка екрану | |

## C. Sound

| English | Spanish (es) | Russian (ru) | Ukrainian (uk) | Notes |
|---------|-------------|-------------|----------------|-------|
| tone channel | canal de tono | тональный канал | тональний канал | |
| noise generator | generador de ruido | генератор шума | генератор шуму | |
| envelope | envolvente | огибающая | обвідна | |
| tone period | período de tono | период тона | період тону | |
| envelope period | período de envolvente | период огибающей | період обвідної | |
| buzz-bass | buzz-bass | buzz-bass | buzz-bass | Keep English; it's demoscene jargon |
| just intonation | entonación justa | натуральный строй | натуральний стрій | |
| equal temperament | temperamento igual | равномерная темперация | рівномірна темперація | |
| note table | tabla de notas | таблица нот | таблиця нот | |
| TurboSound | TurboSound | TurboSound | TurboSound | Never translate |

## D. Techniques

| English | Spanish (es) | Russian (ru) | Ukrainian (uk) | Notes |
|---------|-------------|-------------|----------------|-------|
| self-modifying code (SMC) | código auto-modificable (SMC) | самомодифицирующийся код (SMC) | самомодифікований код (SMC) | |
| unrolled loop | bucle desenrollado | развёрнутый цикл | розгорнутий цикл | |
| PUSH trick | truco PUSH | PUSH-трюк | PUSH-трюк | |
| LDI chain | cadena LDI | LDI-цепочка | LDI-ланцюжок | |
| lookup table | tabla de consulta | таблица подстановки | таблиця підстановки | |
| page-aligned table | tabla alineada a página | страничная таблица | сторінкова таблиця | |
| code generation | generación de código | генерация кода | генерація коду | |
| compiled sprites | sprites compilados | скомпилированные спрайты | скомпільовані спрайти | |
| double buffering | doble búfer | двойная буферизация | подвійна буферизація | |
| dirty rectangles | rectángulos sucios | грязные прямоугольники | брудні прямокутники | |
| multicolor | multicolor | мультиколор | мультиколор | Demoscene term, keep as-is |
| split counters | contadores divididos | раздельные счётчики | роздільні лічильники | |
| digital drums | tambores digitales | цифровые барабаны | цифрові барабани | |
| beam racing | carrera del haz | гонка с лучом | перегони з променем | |
| backface culling | eliminación de caras traseras | отсечение задних граней | відсікання задніх граней | |
| RET-chaining | encadenamiento RET | RET-цепочка | RET-ланцюжок | |

## E. Demoscene & Culture

| English | Spanish (es) | Russian (ru) | Ukrainian (uk) | Notes |
|---------|-------------|-------------|----------------|-------|
| demoscene | demoscene | демосцена | демосцена | |
| demo | demo | демо | демо | |
| compo | compo | компо | компо | Keep original |
| demoparty | demoparty | демопати | демопаті | |
| making-of | making-of | making-of | making-of | Keep English |
| intro | intro | интро | інтро | |
| effect | efecto | эффект | ефект | |
| part (of demo) | parte | часть | частина | |
| scripting engine | motor de scripts | скриптовый движок | скриптовий рушій | |
| zapilator | zapilator | запилятор | запилятор | Russian scene slang, keep original |
| sizecoding | sizecoding | sizecoding | sizecoding | Keep English |

## F. Algorithms & Compression

| English | Spanish (es) | Russian (ru) | Ukrainian (uk) | Notes |
|---------|-------------|-------------|----------------|-------|
| fixed-point arithmetic | aritmética de punto fijo | арифметика с фиксированной точкой | арифметика з фіксованою точкою | |
| rotation matrix | matriz de rotación | матрица вращения | матриця обертання | |
| Bresenham line | línea de Bresenham | линия Брезенхэма | лінія Брезенхема | |
| sine table | tabla de seno | таблица синусов | таблиця синусів | |
| AABB collision | colisión AABB | AABB-столкновение | AABB-зіткнення | |
| sliding window | ventana deslizante | скользящее окно | ковзне вікно | |
| decompressor | descompresor | распаковщик | розпаковувач | |

## G. Assembly Notation

| English | Spanish (es) | Russian (ru) | Ukrainian (uk) | Notes |
|---------|-------------|-------------|----------------|-------|
| opcode | código de operación (opcode) | опкод | опкод | |
| operand | operando | операнд | операнд | |
| mnemonic | mnemónico | мнемоника | мнемоніка | |
| register pair | par de registros | регистровая пара | регістрова пара | |
| accumulator | acumulador | аккумулятор | акумулятор | |
| flag | bandera | флаг | прапорець | |
| carry flag | bandera de acarreo | флаг переноса | прапорець перенесення | |
| zero flag | bandera de cero | флаг нуля | прапорець нуля | |
| stack pointer | puntero de pila | указатель стека | вказівник стеку | |
| program counter | contador de programa | счётчик команд | лічильник команд | |
| instruction | instrucción | инструкция | інструкція | |
| assembler | ensamblador | ассемблер | асемблер | |
| disassembler | desensamblador | дизассемблер | дизасемблер | |
| label | etiqueta | метка | мітка | |
| directive | directiva | директива | директива | |

## H. Book Structure

| English | Spanish (es) | Russian (ru) | Ukrainian (uk) | Notes |
|---------|-------------|-------------|----------------|-------|
| Chapter | Capítulo | Глава | Розділ | |
| Appendix | Apéndice | Приложение | Додаток | |
| Glossary | Glosario | Глоссарий | Глосарій | |
| Index | Índice | Указатель | Покажчик | |
| Figure | Figura | Рисунок | Рисунок | |
| Table | Tabla | Таблица | Таблиця | |
| Example | Ejemplo | Пример | Приклад | |
| Summary | Resumen | Итого | Підсумок | |

---

## Book Title

| Language | Title | Subtitle |
|----------|-------|----------|
| English | Coding the Impossible | Z80 Demoscene Techniques for Modern Makers |
| Spanish | Programando lo Imposible | Técnicas de Demoscene Z80 para Creadores Modernos |
| Russian | Программируя невозможное | Демосценовые техники Z80 для современных разработчиков |
| Ukrainian | Програмуючи неможливе | Демосценові техніки Z80 для сучасних розробників |
