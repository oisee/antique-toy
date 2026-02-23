# Canonical Translation Glossary — LOAD BEFORE EVERY CHAPTER

Compact term lookup for translation agents. One term per line.
Format: `EN term` → `ES` | `RU` | `UK`

## NEVER TRANSLATE (keep exactly as-is)

Proper names: Dark, Introspec, spke, n1k-o, Robus, sq, psndcj, diver4d, DenisGrachev, RST7, Ivan Roshin, Einar Saukas
Products: ZX Spectrum, Pentagon, Scorpion, Agon Light 2, sjasmplus, DeZog, Arkos Tracker, Vortex Tracker, ZEsarUX, Fuse
Chips: Z80, Z80N, eZ80, AY-3-8910, ULA, ESP32, VDP
Demos: Illusion, Eager, GABBA, WAYHACK, Old Tower, Lo-Fi Motion
Publications: Spectrum Expert, Hype, Born Dead, Black Crow
Hardware: TurboSound, DivMMC, Beta Disk 128, TR-DOS, esxDOS, MOS
Formats: .a80, .scr, .tap, .sna, .trd, .z80, .pt3, .tzx
Code: ORG, EQU, DB, DW, DS, ALIGN, INCLUDE, INCBIN, DEVICE, SLOT, PAGE, DISPLAY
Registers: A, B, C, D, E, H, L, F, I, R, AF, BC, DE, HL, SP, PC, IX, IY, AF'
Instructions: LD, PUSH, POP, ADD, ADC, SUB, SBC, AND, OR, XOR, CP, INC, DEC, JR, JP, DJNZ, CALL, RET, RST, HALT, NOP, DI, EI, IM, IN, OUT, EX, EXX, LDI, LDIR, LDD, LDDR, CPI, CPIR, BIT, SET, RES, RLC, RRC, RL, RR, SLA, SRA, SRL, RLD, RRD, DAA, CPL, NEG, CCF, SCF
Compression: ZX0, ZX1, ZX2, LZ4, LZSA, LZSA2, Exomizer, MegaLZ, hrust1, aPLib
Techniques as names: DOWN_HL, LDPUSH, kWORK

## TERMS — Timing & Performance

T-state → T-state | такт (T-state) | такт (T-state)
clock cycle → ciclo de reloj | тактовый цикл | тактовий цикл
frame → fotograma | кадр | кадр
frame budget → presupuesto de fotograma | бюджет кадра | бюджет кадру
scanline → línea de escaneo | строка развёртки | рядок розгортки
contended memory → memoria contendida | спорная память | спірна пам'ять
machine cycle → ciclo de máquina | машинный цикл | машинний цикл
M-cycle → M-cycle | M-цикл | M-цикл
border time → tiempo de borde | время бордюра | час бордюру
timing harness → arnés de temporización | тестовая обвязка | тестова обв'язка
interrupt → interrupción | прерывание | переривання
latency → latencia | задержка | затримка
cycle-accurate → con precisión de ciclo | потактово точный | потактово точний
per-frame → por fotograma | покадровый | покадровий

## TERMS — Hardware

screen memory → memoria de pantalla | экранная память | екранна пам'ять
attribute area → área de atributos | область атрибутов | область атрибутів
attribute clash → conflicto de atributos | конфликт атрибутов | конфлікт атрибутів
attribute cell → celda de atributos | ячейка атрибутов | комірка атрибутів
interleaved screen layout → diseño de pantalla entrelazado | чересстрочная раскладка экрана | черезрядкова розкладка екрану
shadow screen → pantalla sombra | теневой экран | тіньовий екран
memory bank → banco de memoria | банк памяти | банк пам'яті
bank switching → conmutación de bancos | переключение банков | перемикання банків
port → puerto | порт | порт
display page → página de visualización | страница экрана | сторінка екрану
pixel row → fila de píxeles | строка пикселей | рядок пікселів
character row → fila de caracteres | знакоряд | знакоряд
third (screen) → tercio | треть | третина
ink → tinta | чернила (ink) | чорнило (ink)
paper → papel | фон (paper) | фон (paper)
bright → brillo | яркость (bright) | яскравість (bright)
flash → parpadeo | мерцание (flash) | мерехтіння (flash)

## TERMS — Sound & Music

tone channel → canal de tono | тональный канал | тональний канал
noise generator → generador de ruido | генератор шума | генератор шуму
envelope → envolvente | огибающая | обвідна
envelope generator → generador de envolvente | генератор огибающей | генератор обвідної
tone period → período de tono | период тона | період тону
envelope period → período de envolvente | период огибающей | період обвідної
mixer → mezclador | микшер | мікшер
volume → volumen | громкость | гучність
frequency → frecuencia | частота | частота
octave → octava | октава | октава
semitone → semitono | полутон | півтон
buzz-bass → buzz-bass | buzz-bass | buzz-bass
just intonation → entonación justa | натуральный строй | натуральний стрій
equal temperament → temperamento igual | равномерная темперация | рівномірна темперація
note table → tabla de notas | таблица нот | таблиця нот
tuning → afinación | настройка | налаштування
tracker → tracker | трекер | трекер
music player → reproductor de música | проигрыватель музыки | програвач музики
digital drums → tambores digitales | цифровые барабаны | цифрові барабани
sample → muestra | сэмпл | семпл

## TERMS — Techniques

self-modifying code (SMC) → código auto-modificable (SMC) | самомодифицирующийся код (SMC) | самомодифікований код (SMC)
unrolled loop → bucle desenrollado | развёрнутый цикл | розгорнутий цикл
loop unrolling → desenrollado de bucles | развёртка цикла | розгортка циклу
PUSH trick → truco PUSH | PUSH-трюк | PUSH-трюк
LDI chain → cadena LDI | LDI-цепочка | LDI-ланцюжок
lookup table → tabla de consulta | таблица подстановки | таблиця підстановки
page-aligned table → tabla alineada a página | страничная таблица | сторінкова таблиця
code generation → generación de código | генерация кода | генерація коду
runtime code generation → generación de código en tiempo de ejecución | генерация кода во время выполнения | генерація коду під час виконання
compiled sprites → sprites compilados | скомпилированные спрайты | скомпільовані спрайти
double buffering → doble búfer | двойная буферизация | подвійна буферизація
dirty rectangles → rectángulos sucios | грязные прямоугольники | брудні прямокутники
multicolor → multicolor | мультиколор | мультиколор
split counters → contadores divididos | раздельные счётчики | роздільні лічильники
beam racing → carrera del haz | гонка с лучом | перегони з променем
backface culling → eliminación de caras traseras | отсечение задних граней | відсікання задніх граней
RET-chaining → encadenamiento RET | RET-цепочка | RET-ланцюжок
4-phase colour → color de 4 fases | 4-фазный цвет | 4-фазний колір
asynchronous frame generation → generación asíncrona de fotogramas | асинхронная генерация кадров | асинхронна генерація кадрів
sprite → sprite | спрайт | спрайт
sprite masking → enmascaramiento de sprites | маскирование спрайтов | маскування спрайтів
clipping → recorte | отсечение | відсікання
scrolling → desplazamiento | скроллинг | скролінг
pixel scrolling → desplazamiento de píxeles | пиксельный скроллинг | піксельний скролінг
tile scrolling → desplazamiento de baldosas | тайловый скроллинг | тайловий скролінг
collision detection → detección de colisiones | обнаружение столкновений | виявлення зіткнень
bounding box → caja delimitadora | ограничивающий прямоугольник | обмежуючий прямокутник
game loop → bucle de juego | игровой цикл | ігровий цикл
state machine → máquina de estados | конечный автомат | скінченний автомат

## TERMS — Algorithms & Math

fixed-point arithmetic → aritmética de punto fijo | арифметика с фиксированной точкой | арифметика з фіксованою точкою
fixed-point → punto fijo | фиксированная точка | фіксована точка
rotation matrix → matriz de rotación | матрица вращения | матриця обертання
Bresenham line → línea de Bresenham | линия Брезенхэма | лінія Брезенхема
sine table → tabla de seno | таблица синусов | таблиця синусів
cosine → coseno | косинус | косинус
AABB collision → colisión AABB | AABB-столкновение | AABB-зіткнення
sliding window → ventana deslizante | скользящее окно | ковзне вікно
decompressor → descompresor | распаковщик | розпаковувач
compressor → compresor | упаковщик | пакувальник
compression ratio → tasa de compresión | степень сжатия | ступінь стиснення
shift-and-add multiply → multiplicación por desplazamiento y suma | умножение сдвигом и сложением | множення зсувом і додаванням
square-table multiply → multiplicación por tabla de cuadrados | умножение через таблицу квадратов | множення через таблицю квадратів
midpoint method → método del punto medio | метод средней точки | метод середньої точки

## TERMS — Demoscene & Culture

demoscene → demoscene | демосцена | демосцена
demo → demo | демо | демо
compo → compo | компо | компо
demoparty → demoparty | демопати | демопаті
making-of → making-of | making-of | making-of
intro → intro | интро | інтро
effect → efecto | эффект | ефект
part (of demo) → parte | часть | частина
scripting engine → motor de scripts | скриптовый движок | скриптовий рушій
demo engine → motor de demo | движок демо | рушій демо
zapilator → zapilator | запилятор | запилятор
sizecoding → sizecoding | sizecoding | sizecoding
scene → escena | сцена | сцена
coder → programador | кодер | кодер
musician → músico | музыкант | музикант
graphician → grafista | графист | графіст
release → lanzamiento | релиз | реліз
party version → versión de fiesta | пати-версия | паті-версія

## TERMS — Assembly & Architecture

opcode → código de operación (opcode) | опкод | опкод
operand → operando | операнд | операнд
mnemonic → mnemónico | мнемоника | мнемоніка
register pair → par de registros | регистровая пара | регістрова пара
accumulator → acumulador | аккумулятор | акумулятор
flag → bandera | флаг | прапорець
carry flag → bandera de acarreo | флаг переноса | прапорець перенесення
zero flag → bandera de cero | флаг нуля | прапорець нуля
stack pointer → puntero de pila | указатель стека | вказівник стеку
program counter → contador de programa | счётчик команд | лічильник команд
instruction → instrucción | инструкция | інструкція
assembler → ensamblador | ассемблер | асемблер
disassembler → desensamblador | дизассемблер | дизасемблер
label → etiqueta | метка | мітка
local label → etiqueta local | локальная метка | локальна мітка
directive → directiva | директива | директива
macro → macro | макрос | макрос
byte → byte | байт | байт
word (16-bit) → palabra | слово | слово
address → dirección | адрес | адреса
memory map → mapa de memoria | карта памяти | карта пам'яті
stack → pila | стек | стек
subroutine → subrutina | подпрограмма | підпрограма
interrupt handler → manejador de interrupciones | обработчик прерываний | обробник переривань
interrupt mode → modo de interrupción | режим прерываний | режим переривань

## TERMS — Book Structure

Chapter → Capítulo | Глава | Розділ
Appendix → Apéndice | Приложение | Додаток
Glossary → Glosario | Глоссарий | Глосарій
Figure → Figura | Рисунок | Рисунок
Table → Tabla | Таблица | Таблиця
Example → Ejemplo | Пример | Приклад
Summary → Resumen | Итого | Підсумок
See also → Ver también | См. также | Див. також
Note → Nota | Примечание | Примітка
Warning → Advertencia | Внимание | Увага
Tip → Consejo | Совет | Порада

## FORBIDDEN ALTERNATIVES (use canonical form only!)

RU: НЕ "фрейм" → ТОЛЬКО "кадр"
RU: НЕ "двойной буфер" → ТОЛЬКО "двойная буферизация"
RU: НЕ "сканлайн" → ТОЛЬКО "строка развёртки"
RU: НЕ "конфликтная память" → ТОЛЬКО "спорная память"
RU: НЕ "фреймовый бюджет" → ТОЛЬКО "бюджет кадра"
RU: НЕ "указатель программ" → ТОЛЬКО "счётчик команд"
ES: НЕ "cuadro" → ТОЛЬКО "fotograma"
ES: НЕ "marco" → ТОЛЬКО "fotograma"
UK: НЕ "флаг" → ТОЛЬКО "прапорець"
UK: НЕ "вказівник програм" → ТОЛЬКО "лічильник команд"
UK: НЕ "фрейм" → ТОЛЬКО "кадр"
UK: НЕ "рушій демо" when meaning "demo engine" as proper noun → use "движок демо" only for generic engine

## STYLE

RU: обращение к читателю на "ты"
UK: обращення до читача на "ти"
ES: tuteo (tú) al dirigirse al lector
All: code blocks, image paths, \newpage — NEVER modify
All: assembly comments — keep in English
All: hex ($4000), binary (%10101010) — keep as-is
