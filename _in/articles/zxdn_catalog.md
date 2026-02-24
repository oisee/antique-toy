# ZXDN Coding Articles Catalog

**Source:** ZX Developer's Network (ZXDN) — the largest curated collection of ZX Spectrum programming articles from Russian-language scene press (1997-2005).
**Original URL:** zxdn.narod.ru (now mirrored at [alexanderk.ru/zxdn](http://alexanderk.ru/zxdn/coding.html) and [GitHub](https://github.com/alexanderk23/zxdn))
**Language:** Russian (all articles)
**Total articles in coding section:** ~267 files (including .htm wrappers for multi-file articles)
**Local path:** `_in/raw/zxdn/coding/` (NOTE: local files are 0-byte stubs; content available via GitHub repo)

---

## Collection Assessment

### Value for "Coding the Impossible"

**Overall rating: HIGH** — This is the single richest Russian-language source on ZX Spectrum assembly programming. The collection spans 30+ scene magazines and covers nearly every topic in our book. Key strengths:

1. **Demoscene-specific content** from Demo Or Die, Scenergy, Born Dead — exactly our target audience
2. **Alone Coder (AlCo) articles** from ZX-Guide — he's one of the most respected ZX coders and his optimization/multicolor articles are authoritative
3. **Practical Z80 assembly** with cycle counts, working code, and real demo/game implementations
4. **Historical primary sources** — articles from SE#01 (Spectrum Expert), Scenergy, Demo Or Die are by active demosceners writing about their own techniques

### Limitations

- Most articles are intermediate-depth (2,000-4,000 words); few are truly deep dives
- Quality varies significantly between magazines (ZX-Guide and Info Guide are high quality; some smaller zines are basic)
- Code is in various assembler syntaxes (ALASM, Storm, STS) — not sjasmplus, so examples need adaptation
- Some articles are purely theoretical with no Z80 code
- Several "beginner assembly" articles have no relevance to our advanced book

### Recommended Reading Priority

Articles marked with stars below indicate highest value for the book:
- `***` = Must-read, directly fills a gap or provides unique technique
- `**` = Valuable supplementary material, good reference
- `*` = Worth skimming, minor additions possible

---

## Full Article Catalog

### 1. BASIC and Dialects
*Not relevant to the book (Z80 assembly focus)*

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| zf1basic.txt | Basic для программистов | ZX Format #1-4 | — | — |
| zf57beta.txt | Beta Basic | ZX Format #5-7 | — | — |

### 2. Assembler for Beginners
*Mostly below our book's level, but some contain useful system details*

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| zg14asmt.txt | Уроки ассемблера для ламеров (1-4) | ZX-Guide #1-4 | — | — |
| op2041as.txt | Ассемблер: взгляд издалека | Optron #20-41 | — | — |
| zf1asmdm.txt | Ассемблер в картинках для "чайников" | ZX Format #1-2 | — | — |
| zf3zxhrd.txt | Экскурс в анатомию ZX | ZX Format #3 | Ch.1-2 | * |
| zf7asmbg.txt | О кодинге для начинающих | ZX Format #7 | — | — |
| adv2asmt.txt | Ответы на вопросы начинающих | Adventurer #2 | — | — |
| adv4bgnq.txt | Ответы на вопросы начинающих | Adventurer #4 | — | — |
| adv5romp.txt | Использование подпрограмм ПЗУ | Adventurer #5 | — | — |
| adv5chan.txt | RST 16 (#10) | Adventurer #5 | — | — |
| dv0alspr.txt | Печать в нижних строках экрана | Deja Vu #0A | — | — |
| dv09keyb.txt | Опрос клавиатуры | Deja Vu #09 | Ch.18 | * |
| dv09trdr.txt | Сброс с переходом в TR-DOS | Deja Vu #09 | — | — |
| kn10beam.txt | Ну почему он так режет? | Krasnodar News #10 | Ch.1 | * |
| zf3adapt.txt | Адаптация программ на диск | ZX Format #3 | — | — |
| zf3dexor.txt | Как бороться с закрытыми кодами | ZX Format #3 | — | — |
| iz04lgop.txt | Xor And Or ??? | IzhNews #4 | — | — |

### 3. Code Optimization
*Directly relevant to Ch.1 (T-state budgets) and Ch.3 (demoscene toolbox)*

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| bd0abopt.txt | Как кодить оптимально | Born Dead #0A-#0B | Ch.1, Ch.3, Ch.13 | ** |
| zg4optim.txt | Оптимизация по скорости | ZX-Guide #4 | Ch.1, Ch.3 | *** |
| ig7optim.txt | Основы оптимизации под Z80 | Info Guide #7 | Ch.1, Ch.3 | *** |
| ig10grcd.txt | Код Грея и оптимизация | Info Guide #10 | Ch.3, Ch.4 | ** |

**Sampled assessment:**
- **zg4optim.txt** (Alone Coder, ~3,000 words): Superb. Explicit cycle counts per chunk, rotation+bumpmapping optimization, code generation techniques. Teaches "thinking non-standardly" about performance. Directly relevant to Ch.1/Ch.3.
- **ig7optim.txt** (~3,000 words): Comprehensive. Self-modifying code patterns (var=$+1), loop unrolling (DUP/EDUP), register tricks, CALL→JP replacement, multi-entry procedures. Essential reference for Ch.3.
- **bd0abopt.txt** (~4,000 words over 2 issues): Sine table compression via delta-RLE, attribute sprite optimization, size-coding techniques. Bridges Ch.3 and Ch.13.

### 4. Digital Sound
*Relevant to Ch.11-12 (AY, drums, music sync)*

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| bd0gdpcm.txt | Сжатие звука методом ADPCM | Born Dead #0G | Ch.12 | ** |
| bd09gmcc.txt | Воспроизведение оцифровок на AY (MCC) | Born Dead #09, #0G | Ch.12 | *** |
| ig6dacrs.txt | Больше бит на звуковом устройстве | Info Guide #6 | Ch.11, Ch.12 | ** |
| zg45dsnd.txt | Цифровые плееры | ZX-Guide #4.5 | Ch.12 | ** |
| ig10zvuk.txt | О звуке (бипер) | Info Guide #10 | Ch.11 | * |
| ms12dsnd.txt | Цифровой звук | MSD #12 | Ch.12 | * |

### 5. Music and AY
*Directly relevant to Ch.11 (AY architecture) and Ch.12 (music sync)*

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| zg45mfmt.txt | Автоопределение музыкальных форматов | ZX-Guide #4.5 | Ch.11 | * |
| zg45ayeq.txt | Индикатор AY | ZX-Guide #4.5 | Ch.11 | * |
| flt1ayfq.txt | Таблица делителей для нот | Flash Time #1 | Ch.11 | ** |
| sng1msnc.txt | Синхронизация с музыкой в демах | Scenergy #1 | Ch.12 | *** |
| ig10beep.txt | Бипер | Info Guide #10 | Ch.11 | * |
| dv04fade.txt | Плавное уменьшение громкости | Deja Vu #04 | Ch.11 | * |

**Sampled assessment:**
- **sng1msnc.txt** (~3,500 words): Excellent. Critiques naive sync methods, presents custom pseudo-program system with IM2 resident handler for async effect control. Based on "Forever" demo. Includes full source. Must-read for Ch.12.
- **flt1ayfq.txt**: Frequency divider table for all musical notes on AY — practical reference for Ch.11.

### 6. Graphics — Screen Output and Layout

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| zg1scfrm.txt | Вывод экрана за прерывание | ZX-Guide #1 | Ch.2, Ch.3 | *** |
| zg4fmapp.txt | Mapping | ZX-Guide #4 | Ch.6, Ch.7 | ** |
| 3b1scrll.txt | Опять Scroll... | 3bit #1 | Ch.17 | * |
| zg1etud1.txt | Оптимальный DOWN HL | ZX-Guide #1 | Ch.2 | ** |
| n125dnhl.txt | Процедуры next/prev линии | Nicron #125 | Ch.2 | ** |
| zg1etud2.txt | Точка Старых | ZX-Guide #1 | Ch.2 | * |
| m08drlne.txt | Алгоритм рисования линии | Move #08 | Ch.5 | * |
| ig9vslon.txt | О летающем слоне | Info Guide #9 | Ch.16 | * |

**Sampled assessment:**
- **zg1scfrm.txt** (Alone Coder, ~2,000 words): LD-PUSH method for full-screen output within one interrupt (71,680 cycles on Pentagon). Challenges POP-PUSH orthodoxy. Includes dispatcher mechanism and PUSHROLL.H scroll example. Directly relevant to Ch.2/Ch.3.
- **n125dnhl.txt**, **zg1etud1.txt**: Screen address calculation — next/previous line routines. Standard reference for Ch.2.

### 7. Graphics — 3D, Shading, Projection
*Core material for Ch.5 (wireframe), Ch.6 (sphere/texture)*

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| dod1filt.txt | Локальная фильтрация растровых изображений | Demo Or Die #1 | Ch.6 | * |
| dod1hdfc.txt | Алгоритмы обработки видимости поверхностей | Demo Or Die #1 | Ch.5 | ** |
| dod13d2d.txt | Проецирование 3D>2D | Demo Or Die #1 | Ch.5 | * |
| dod1pgns/ | Заливка треугольника, Гуро shading | Demo Or Die #1 | Ch.5, Ch.6 | ** |
| dod2phng/ | Phong shading | Demo Or Die #2 | Ch.6 | ** |
| dod2flat.txt | Flat shading | Demo Or Die #2 | Ch.5, Ch.6 | ** |
| dod2rdbl.txt | Radial blur | Demo Or Die #2 | Ch.9 | * |
| dod2mvsh.txt | Moving Shit | Demo Or Die #2 | Ch.10 | * |
| dpt1fgfx.txt | Совершенные методы кодинга и графика | Depth #1 | Ch.3 | * |
| adv7fsln/ | Быстрые процедуры линии | Adventurer #7 | Ch.5 | ** |
| sng1bump/ | Phong Bump Mapping | Scenergy #1 | Ch.6 | *** |
| sng2txmp/ | Texture mapping | Scenergy #2 | Ch.6 | *** |
| sng2txph.txt | Texture mapping + Phong shading | Scenergy #2 | Ch.6 | *** |
| dv06ball/ | Генерилка шариков | Deja Vu #06 | Ch.6 | * |
| dv06frac/ | Фрактальный папоротник | Deja Vu #06 | — | — |
| ec01gf3d.txt | Изображение трёхмерных объектов | Echo #01 | Ch.5 | * |
| zpw3gf3d.txt | Быстрая 3D-графика для Speccy | ZX Power #3-4 | Ch.5 | *** |
| zf6clbmc.txt | BMC - Show 'em up in colour | ZX Format #6 | Ch.8 | * |
| zf7trclr.txt | Расширение цветовых возможностей ZX | ZX Format #7 | Ch.8 | * |
| asp4gfxb.txt | Быстрая и не очень быстрая графика | ASpect #4 | Ch.3, Ch.16 | ** |

**Sampled assessments:**
- **zpw3gf3d.txt** (Ruff/Avalon, ~12,000 words over 2 issues): Substantial. Novel rotation approach — rotates entire planes then interpolates, avoiding per-point sin/cos. Lookup tables for 3 axes. Renders 175 vectors in real-time. Has errors but innovative approach. Critical for Ch.5.
- **sng1bump/**, **sng2txmp/**, **sng2txph.txt** (Scenergy articles): Phong bump mapping and texture mapping implementations on ZX Spectrum. These are among the most advanced graphics articles in the collection. Essential for Ch.6.
- **dod1hdfc.txt** (~1,200 words): Backface culling via determinant, painter's algorithm, Z-buffer. Conceptual only (no Z80 code) but useful theory overview for Ch.5.
- **asp4gfxb.txt** (~4,500 words): LDI chains vs PUSH/POP vs POP+LD for screen buffer output. Practical comparison with working code. Good reference for Ch.3/Ch.16.
- **dod13d2d.txt** (~300 words): Very brief — just projection formulas. Minimal value.

### 8. Graphics — Chunky Pixels
*Directly relevant to Ch.7 (rotozoomer, chunky pixels)*

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| bd05fc2p.txt | Fast C2P procedure | Born Dead #05 | Ch.7 | *** |
| dod2chnk.txt | Chunks Output | Demo or Die #2 | Ch.7 | ** |
| ps11ch22.txt | Dithering 2*2=16 | Psychoz #11 | Ch.7 | ** |
| ad14c2pi.txt | Chunks 2x2 | Adventurer #14 | Ch.7 | * |
| zg4ch4g.txt | Генерация чанков 4x4 | ZX-Guide #4 | Ch.7 | ** |

**Sampled assessment:**
- **bd05fc2p.txt** (~300 words + code): Fast C2P using jump-table with 256 pre-calculated routines. 109 cycles per chunk pair, full screen in ~83,712 cycles (>25 fps for bump mapping). Compact but highly valuable technique for Ch.7.
- **dod2chnk.txt** (~2,500 words): Two chunking approaches (packed 4-bit pairs vs single byte), dither table generation for 16 grayscale levels. Good working code. Relevant to Ch.7.

### 9. Graphics — Sprites
*Directly relevant to Ch.16 (fast sprites)*

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| zg45spro.txt | Быстрый вывод спрайтов | ZX-Guide #4.5 | Ch.16 | *** |
| n105sprd.txt | Вспомогательные операции при выводе спрайта | Nicron #105 | Ch.16 | * |
| adv7spgn.txt | Поиск адреса спрайта в архиве | Adventurer #7 | Ch.16 | * |
| dv09dspr.txt | Вывод спрайтов 2x2 знакоместа | Deja Vu #09 | Ch.16 | * |
| dv05sint.txt | Стек при разрешённых прерываниях (спрайты) | Deja Vu #05 | Ch.16, Ch.3 | ** |
| dv0asspr.txt | Стек при разрешённых прерываниях (ч.2) | Deja Vu #0A | Ch.16, Ch.3 | ** |
| dv05dspr.txt | Вывод спрайтов | Deja Vu #05 | Ch.16 | * |
| zpw3mask.txt | Автосоздание маски для спрайтов | ZX Power #3 | Ch.16 | ** |

**Sampled assessment:**
- **zg45spro.txt** (Alone Coder, ~3,500 words): Pre-shifted sprite tables (8 shift variants), AND/XOR masking, stack-based data feeding, alternate register sets (EXX). Designed for RTS games with 20+ characters. Highly relevant to Ch.16.
- **dv05sint.txt** (~2,500 words): Stack pointer manipulation during interrupts for sprite rendering. Uses EX (SP),HL trick. From actual demo (TRASH DEMO, ART'98). Good for Ch.3/Ch.16 stack tricks section.
- **zpw3mask.txt**: Automatic sprite mask generation — useful practical technique for Ch.16.

### 10. Graphics — Text Display
*Minor relevance (Ch.17 scrolling text, Ch.18 game UI)*

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| bc06tout/ | Секреты текстового вывода | Black Crow #06 | Ch.17 | * |
| 3b1prsym.txt | Всё о печати символов | 3bit #1 | — | — |
| zg1etud4.txt | Быстрая печать буквы 6x8 | ZX-Guide #1 | Ch.17 | * |
| lp12pr42.txt | Быстрый драйвер 42 символов | LPrint #12 | — | — |
| fu1print.txt | Быстрая печать 42, 64 символа | Funeral #1 | — | — |
| dv04nump.txt | Печать чисел в разных системах | Deja Vu #04 | — | — |
| dv09pr42.txt | Быстрая печать 42 символов | Deja Vu #09 | — | — |
| dv09pr64.txt | Быстрый вывод строки с 64 символами | Deja Vu #09 | — | — |
| dv07prnt.txt | Процедура печати для Бейсика | Deja Vu #07 | — | — |
| asp8pr64.txt | Чтобы строка вмещала больше | ASpect #8 | — | — |

### 11. Graphics — Interface Elements
*Minor relevance*

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| adv8wndw.txt | Рисование окна с рамкой | Adventurer #8 | Ch.18 | * |
| 3b1drwin.txt | Рисование окна в цвете | 3bit #1 | Ch.18 | * |

### 12. Graphics — Image Conversion
*Not directly relevant (PC→ZX conversion tools, not demoscene techniques)*

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| ad13fsbg.txt | Floyd-Steinberg | Adventurer #13 | — | — |
| dv07dith/ | Dithering, как он есть | Deja Vu #07 | Ch.7 | * |
| dv0adit2/ | Dithering #02 | Deja Vu #0A | Ch.7 | * |
| ig7cvimg/ | Конвертирование PC→ZX | Info Guide #7-8 | — | — |
| dv08ascr/ | Конверсия графики в ASCII | Deja Vu #08 | — | — |
| dv0ascta.txt | К вопросу о конверсии | Deja Vu #0A | — | — |

### 13. Graphics — Individual Effects
*Relevant to Ch.7 (rotozoomer), Ch.9 (tunnels/zoomers), Ch.10 (dotfield)*

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| adv9rotm/ | Вращалка-извращалка | Adventurer #9 | Ch.7 | ** |
| vw1water.txt | Круги на воде | Virtual Worlds #1 | Ch.9 | * |
| dod2plsm/ | Реализация плазмы 2x2 | Demo Or Die #2 | Ch.9 | ** |
| adv8iris.txt | Графический эффект 'Iris' | Adventurer #8 | Ch.20 | * |
| adv8atsc.txt | Плавный псевдо-атрибутный скролл | Adventurer #8 | Ch.17 | ** |
| dv03fatr.txt | Плавающие атрибуты | Deja Vu #03 | Ch.9 | * |
| dv04pbls.txt | Плазменные шарики | Deja Vu #04 | Ch.9 | * |
| iz09fire.txt | Эффект горящего огня | IzhNews #9 | Ch.9 | * |

### 14. Graphics — Border and Multicolor
*Directly relevant to Ch.8 (multicolor, beam racing)*

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| zf5bordr.txt | Об эффектах на бордюре | ZX Format #5 | Ch.8 | ** |
| zf6mlclr.txt | Изготовление мультиколоров | ZX Format #6 | Ch.8 | *** |
| m02mcbrd.txt | Мультиколор и бордюрные эффекты | Move #02 | Ch.8 | ** |
| bc05bord.txt | Мультиколор и чанки на бордюре | Black Crow #05 | Ch.8 | ** |
| zg2mchow.txt | О мультиколоре вообще и MC24 | ZX-Guide #2 | Ch.8 | *** |

**Sampled assessments:**
- **zg2mchow.txt** (AlCo, ~8,000 words, 8 chapters): Definitive multicolor guide. Covers beam racing, per-scanline attribute changes, POP-based methods, dual-screen switching (128K). Extensive Z80 code with interrupt handlers and timing loops. Must-read for Ch.8.
- **zf6mlclr.txt** (~2,000 words): Practical step-by-step: INT→timing→attribute replacement via LDI. IM 2 mode setup. Scorpion-specific timings. Good complement to zg2mchow.
- **zf5bordr.txt** (~2,500 words): Border effects — horizontal stripes, vertical lines via port #FE timing. Cycle counting and ULA sync. Good for Ch.8 border section.

### 15. Graphics — Video / Animation
*Partially relevant to Ch.14 (compression) and Ch.20 (demo workflow)*

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| ad15mcol.txt | Больше цвета! | Adventurer #15 | Ch.8 | * |
| ig7video.txt | Упаковка видео для ZX | Info Guide #7 | Ch.14 | ** |
| ig8cdvid.txt | CD video на ZX | Info Guide #8 | Ch.14 | * |
| dod1atvd/ | Конвертирование атрибутного видео | Demo Or Die #1 | Ch.14 | * |
| sng2jamv/ | Упаковка анимаций в JAM | Scenergy #2 | Ch.14 | ** |
| zxvdonzx.txt | Видео на спектруме. Реально? | (standalone) | Ch.14 | * |

### 16. Game Making
*Relevant to Ch.18-19 (game loop, AI, collisions) and Ch.5 (3D)*

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| ad11game/ | Game making #2 | Adventurer #11 | Ch.18 | * |
| ad13doom/ | Как написать 3D игру типа DOOM | Adventurer #13 | Ch.5 | ** |
| ig7gpr3d.txt | 3D проецирование пола/трассы | Info Guide #7 | Ch.5, Ch.6 | ** |
| ig8p16cg.txt | Написание аркадной игры | Info Guide #8 | Ch.18 | ** |
| dn21gmai/ | Теория AI | Don News #21 | Ch.19 | ** |
| ig5ray3d/ | Raycasting — DOOM на спектруме | Inferno Guide #5 | Ch.5 | ** |
| vw1pfind.txt | Поиск пути | Virtual Worlds #1 | Ch.19 | ** |
| zf5cgmai.txt | ИИ в компьютерных играх | ZX Format #5-6 | Ch.19 | ** |
| zf6wvalg.txt | Построение кратчайшего маршрута | ZX Format #6 | Ch.19 | ** |

**Sampled assessment:**
- **vw1pfind.txt** (~3,000 words): BFS-based pathfinding with bit-packed cells. No Z80 code (pseudocode only), but solid algorithm exposition. Useful for Ch.19.
- **ig5ray3d/**: Raycasting tutorial for ZX Spectrum. Relevant to Ch.5 as an alternative 3D approach.

### 17. Demo Making
*Directly relevant to Ch.13 (size-coding) and Ch.20 (demo workflow)*

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| sng2dngl.txt | Секреты DAINGY | Scenergy #2 | Ch.20, Ch.5 | *** |
| kn10i256.txt | Intro в 256 байт? | Krasnodar News #10 | Ch.13 | ** |

**Sampled assessments:**
- **sng2dngl.txt** (Cryss/RZL, ~3,500 words): Post-mortem of DAINGY demo (CC'999, 3rd place). 3D text rotation with derivative-based sine generation, chunk system (8x4 blocks), running wave effect, dual-buffer architecture. Real production insights. Must-read for Ch.20.
- **kn10i256.txt** (~750 words): Complete 153-byte screensaver with stack exploitation, dynamic table generation, mirrored drawing. Good example for Ch.13 (size-coding).

### 18. Data Compression
*Directly relevant to Ch.14 (compression)*

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| bd08comp.txt | Улучшение сжимаемости картинок | Born Dead #08 | Ch.14 | * |
| zg4pak3.txt | Упаковка триколоров | ZX-Guide #4 | Ch.14 | * |
| ig5arfmt.txt | Форматы упакованных данных на ZX | Inferno Guide #5 | Ch.14 | ** |
| ig7hpack.txt | Практические принципы LZ упаковки | Info Guide #7 | Ch.14 | *** |
| zxvgfxpk.txt | Сжатие графической информации | (standalone) | Ch.14 | * |
| ig10jpeg.txt | Декодирование JPEG | Info Guide #10 | Ch.14 | * |
| dv06huff.txt | Сжатие по Хаффмену | Deja Vu #06 | Ch.14 | ** |
| dv05mpck.txt | Депакер для MS-PACK | Deja Vu #05 | Ch.14 | * |
| ig10pack.txt | Эффективность упаковщиков | Info Guide #10 | Ch.14 | ** |

**Sampled assessments:**
- **ig7hpack.txt** (~8,000 words): Comprehensive LZ compression guide. Hash tables for pattern search, lazy evaluation, Huffman tree construction (max 15 levels), 128K window management, archive creation on TR-DOS. The most substantial compression article in the collection. Essential for Ch.14.
- **dv06huff.txt** (~8,000 words): Thorough Huffman coding tutorial — tree construction, adaptive Huffman, overflow prevention, weight scaling. Theoretical but well-structured. Good for Ch.14 background.

### 19. Calculations and Algorithms
*Directly relevant to Ch.4 (multiply, PRNG, fixed-point)*

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| adv9sint.txt | Як синус забабахать | Adventurer #9 | Ch.4, Ch.5 | ** |
| ad10ieee.txt | Работа с IEEE-числами | Adventurer #10 | — | — |
| ad13nrnd.txt | Научное RND | Adventurer #13 | Ch.4 | * |
| ig10rndg.txt | О некоторых RND-генераторах | Info Guide #10 | Ch.4 | *** |
| ig7mthex.txt | Распознавание арифметических выражений | Info Guide #7 | — | — |
| ig8tgnmt.txt | Синус и компания | Info Guide #8 | Ch.4, Ch.5 | ** |
| m09sqrcl.txt | Один полезный трюк с ^ | Move #09 | Ch.4 | * |
| bg01squp.txt | Возведение в квадрат | Bugs #1 | Ch.4 | * |
| dod2sqtg.txt | Генератор таблицы квадратов | Demo Or Die #2 | Ch.4 | ** |
| bg01sqgt.txt | Квадратный корень | Bugs #1 | Ch.4 | * |
| bd21apsq.txt | Извлечение приблизительного корня | Body #21 | Ch.4 | * |
| bd22divd.txt | Делим 16 бит на 8 бит | Body #22 | Ch.4 | * |
| ig9asort.txt | О сортировке | Info Guide #9 | Ch.5 | * |
| dod2sort.txt | Сортировка | Demo Or Die #2 | Ch.5 | ** |
| adv8long.txt | LONG? Что это такое? | Adventurer #8 | Ch.4 | * |
| dv09calc.txt | Конверсия со стека калькулятора | Deja Vu #09 | — | — |
| dv05math.txt | Умножение, квадратный корень | Deja Vu #05 | Ch.4 | ** |
| zf7fcalc.txt | Быстрые вычисления в ассемблере | ZX Format #7 | Ch.4 | ** |

**Sampled assessments:**
- **ig10rndg.txt** (~2,000 words): LFSR generators with parameter tables for max-length sequences (2^N-1 period) + Mitchell-Moore generator (X[n]=X[n-24]+X[n-55], period ~2^62). Working Z80 code for both. Must-read for Ch.4 PRNG section.
- **dv05math.txt** (~2,500 words): Table-based fast multiply using sum/difference of squares identity (141-207 cycles vs 310-358 for iterative). Square root via Newton's method. Good for Ch.4.
- **zf7fcalc.txt** (~2,500 words): Binary long division, multiplication, fixed-point arithmetic with 1/256 precision. Pedagogically sound. Good for Ch.4.
- **dod2sort.txt** (~3,000 words): Bubble, selection, merge, bit/byte sort. Benchmarked on ZX (BYTESORT+ ~30K cycles, selection ~85K). Useful for Ch.5 z-sorting.

### 20. File Formats
*Partially relevant to Ch.11 (music formats) and Ch.14 (compression formats)*

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| an12pt3x.txt | Формат Pro Tracker v3.x | AlCoNews #12 | Ch.11 | ** |
| pt37xfmt.txt | Формат Pro Tracker v3.7x | (distribution) | Ch.11 | ** |
| ec02pt21.txt | Формат Pro Tracker 2.101 | Echo #02 | Ch.11 | * |
| ec03stpr.txt | Формат Sound Tracker Pro | Echo #03 | Ch.11 | * |
| an13t888.txt | Формат упакованного триколора .888 | AlCoNews #13 | Ch.14 | * |
| an26chip.txt | Формат Chip Tracker 1.x | AlCoNews #26 | Ch.11 | * |
| fu1vechr/ | Формат *.chr (векторные шрифты) | Funeral #1 | — | — |
| ig10anif.txt | Формат ani-файлов | Info Guide #10 | Ch.14 | * |
| ig10mglz.txt | Формат MegaLZ | Info Guide #10 | Ch.14 | ** |
| zf7modfm.txt | Формат MOD-файла | ZX Format #7 | Ch.11 | * |

### 21. Libraries
*Minor relevance*

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| sng2mmlb.txt | Memory Management Library | Scenergy #2 | Ch.15 | * |
| sng2zxal.txt | ZXA library | Scenergy #2 | — | — |
| dv09hrlb.txt | Hrust Library 2.02 | Deja Vu #09 | Ch.14 | ** |

### 22. Device Programming
*Partially relevant — TurboSound and General Sound articles are key*

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| bc07cmos.txt | Программируем CMOS К512ВИ1 | Black Crow #07 | — | — |
| zf6gsprg.txt | Программирование General Sound | ZX Format #6 | Ch.11 | * |
| se01gsfc.txt | GENERAL'изация программ | Spectrum Expert #1 | Ch.11 | ** |
| ad13prgs.txt | Прямое программирование General Sound | Adventurer #13 | Ch.11 | * |
| zg45pent.txt | Порты ZX Spectrum (Pentagon) | ZX-Guide #4.5 | Ch.1, Ch.2 | ** |
| an32m384/ | Видеорежим 384x304 | AlCoNews #32 | — | — |
| ig7m384p/ | 384x304: программирование | Info Guide #7 | — | — |
| ig8tsprg.txt | Программирование Turbo Sound | Info Guide #8 | Ch.11 | *** |
| lp21prog.txt | Определение разных устройств | LPrint #21 | — | — |
| fu15pdrv.txt | Драйвер принтера D-100M | Funeral #1.5 | — | — |
| ec05byte.txt | Двойное разрешение на ZX | Echo #05 | Ch.2 | * |
| dv02mgrs.txt | Перехват Magic/Reset на Scorpion | Deja Vu #02 | — | — |
| ig10atms.txt | Аппаратный скроллинг на ATM2 | Info Guide #10 | Ch.17 | * |
| dv09ctrl.txt | Интерфейс | Deja Vu #09 | Ch.18 | * |
| op14kemp.txt | Kempston Mouse | Optron #14 | Ch.18 | * |
| ec06vt37.txt | Контроллер КР1810ВТ37 | Echo #06 | — | — |
| ec07vi53/ | Программируемый таймер 8253 | Echo #07 | — | — |
| ec01azsd.txt | Azure Sound Drive v8.6 | Echo #01 | — | — |
| dv02xtrm.txt | XTR-modem | Deja Vu #02 | — | — |

**Sampled assessment:**
- **ig8tsprg.txt** (Shiru Otaku, via NedoPC #3): TurboSound dual-AY programming. Port addresses (#FFFD/#BFFD), chip switching (#FF→chip 0, #FE→chip 1), auto-detection code, Power of Sound vs NedoPC variant support. Essential for Ch.11 TurboSound section.
- **se01gsfc.txt** (~8,000 words): General Sound programming — complete guide with port I/O, sound effect initialization, driver frameworks, Target Renegade case study. Useful background for Ch.11.

### 23. Computer-Specific
*Minor relevance*

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| adv1atms/ | Экраны ATM-Turbo 2+ | Adventurer #1 | — | — |
| ec02byte.txt | Компьютер 'Байт-01' | Echo #02 | — | — |
| op07miko.txt | Miko Best 256KB | Optron #7, #21 | — | — |
| bd10p1mb.txt | Pentagon 1024 | Born Dead #10 | Ch.15 | * |
| ec01prfi.txt | ZX Profi: управление ресурсами | Echo #01 | — | — |
| zf4scorp.txt | Теневой монитор Scorpion | ZX Format #4 | — | — |
| sp128pl3.txt | ZX Spectrum +3 | (standalone) | — | — |

### 24. Memory Management
*Relevant to Ch.15 (128K banking)*

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| ec05memd.txt | Драйвер памяти | Echo #05 | Ch.15 | * |
| qcmemdrv.txt | Драйвер памяти Quick Commander | (standalone) | Ch.15 | * |
| on76ramd.txt | Драйвер расширенной памяти | Online #76 | Ch.15 | * |
| on44emem.txt | Расширенная память Profi/Scorpion | Online #44 | Ch.15 | * |
| sng1ramd.txt | RAM Disk для ZX Spectrum 128 | Scenergy #1 | Ch.15 | ** |
| zf5mmhlp.txt | MEMHELP | ZX Format #5 | — | — |
| zf5autoc.txt | AUTOconfig v5.03 | ZX Format #5 | — | — |
| sp22mdrv.txt | Драйвер верхней памяти | Spectrofon #22 | Ch.15 | * |

### 25. Software Protection / Cracking
*Not relevant to the book*

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| bc02hcmk.txt | Защита Mortal Kombat | Black Crow #02 | — | — |
| bc02povw.txt | Общий обзор защит | Black Crow #02 | — | — |
| bc02prem.txt | Снятие защит | Black Crow #02 | — | — |
| bc06pcpt.txt | Защита от копирования | Black Crow #06 | — | — |
| m0235xor.txt | XOR'em all | Move #02-05 | — | — |
| adv3ptct.txt | Методы защиты информации | Adventurer #3 | — | — |
| adv6ptct.txt | Методы защиты программного кода | Adventurer #6 | — | — |
| dv08prot.txt | Некопируемый сектор | Deja Vu #08 | — | — |
| dv09ivir.txt | Вирус-невидимка | Deja Vu #09 | — | — |
| zpw2rest.txt | Восстановление программ | ZX Power #2 | — | — |
| zpw3poke.txt | Cheat и Pokes | ZX Power #3 | — | — |
| zf3cheat.txt | Пособие для мелкого пакостника | ZX Format #3 | — | — |
| zf4cheat.txt | В поисках вечной жизни | ZX Format #4 | — | — |

### 26. TR-DOS / Disk Systems
*Not directly relevant (book doesn't cover disk I/O)*

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| bc05strd.txt | Справочник по TR-DOS | Black Crow #05 | — | — |
| bc02trda.txt | Загрузка уровней | Black Crow #02 | Ch.18 | * |
| dv07dver.txt | Создание дисковых версий | Deja Vu #07 | — | — |
| adv6dver.txt | Дисковая версия | Adventurer #6 | — | — |
| bc07pbar.txt | Индикация работы с диском | Black Crow #07 | — | — |
| an2tclpm.txt | О командных строках | AlCoNews #2 | — | — |
| zg1trdos.txt | TR-DOS Level 1: 15635 | ZX-Guide #1 | — | — |
| zg2trdos.txt | TR-DOS Level 2: ВГ93 | ZX-Guide #2 | — | — |
| zg3trdos.txt | TR-DOS Level 3 | ZX-Guide #3 | — | — |
| ig7d3d13.txt | Смена диска/дисковода | Info Guide #7 | — | — |
| 3b1trder.txt | Обработка дисковых ошибок | 3bit #1 | — | — |
| adv7trer.txt | Обработка дисковых ошибок | Adventurer #7 | — | — |
| dv093d13.txt | Ошибки TR-DOS при #3D13 | Deja Vu #09 | — | — |
| m08stdtr.txt | Строение стандартной дорожки | Move #08 | — | — |
| vw1trdos.txt | Секреты TR-DOS | Virtual Worlds #1 | — | — |
| dv0agdsk.txt | Определение наличия диска | Deja Vu #0A | — | — |
| dv01im2t.txt | IM2 при TR-DOS | Deja Vu #01 | — | — |
| adv46dsl.txt | Дисковые загрузчики | Adventurer #4, #6 | — | — |
| dv05runb.txt | Загрузка бейсик-файлов | Deja Vu #05 | — | — |
| dv06ffmt.txt | Сверхбыстрое форматирование | Deja Vu #06 | — | — |
| dv06rwdr.txt | Драйвер чтения/записи | Deja Vu #06 | — | — |
| zf56trds.txt | TR-DOS для программистов | ZX Format #5-6 | — | — |
| zf3trerr.txt | Ошибка TR-DOS | ZX Format #3 | — | — |
| trdosdrv.txt | Независимый файловый драйвер | (standalone) | — | — |
| ms09trda.txt | Загрузчик в кодах | MSD #9 | — | — |
| trdirsys.txt | Directory System for TR-DOS | (standalone) | — | — |

### 27. iS-DOS
*Not relevant*

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| zf56ispr.txt | Программирование iS-DOS | ZX Format #5-6 | — | — |
| zf1isucl.txt | UniColor | ZX Format #1 | — | — |
| zf1isgme.txt | gmen.com | ZX Format #1 | — | — |
| zf1iswnd.txt | Оконная система | ZX Format #1 | — | — |
| zf2ismon.txt | Монитор командной строки | ZX Format #2 | — | — |
| zf3isobj.txt | Формат *.obj | ZX Format #3 | — | — |
| zf3isasm.txt | Таблица локальных символов | ZX Format #3 | — | — |

### 28. Other Disk Systems
*Not relevant*

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| ad13mdos.txt | MDOS, MB02 | Adventurer #13 | — | — |
| ig7doses.txt | Форматы дисков | Info Guide #7 | — | — |
| ig8discp.txt | DISCiPLE/+D руководство | Info Guide #8 | — | — |
| ig10mofs.txt | Разметка винчестера Scorpion | Info Guide #10 | — | — |

### 29. User Interface
*Minor*

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| dv0aifce.txt | К вопросу о стрелках | Deja Vu #0A | — | — |
| asp7iarw.txt | Стрелочка без стрелочника | ASpect #7 | — | — |

### 30. Emulators
*Not relevant*

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| bd05emud.txt | Emulators must die! | Born Dead #05 | — | — |

### 31. Text Processing
*Not relevant*

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| bc02txts.txt | Быстрый поиск слова | Black Crow #02 | — | — |

### 32. Drivers
*Not relevant*

| File | Title | Source | Book Ch. | Rating |
|------|-------|--------|----------|--------|
| ec06rcrd.txt | RAM-диск в Real Commander | Echo #06 | — | — |
| zf6mmdrv.txt | Драйвер модема для MMD | ZX Format #6 | — | — |

### 33. Uncategorized / Additional Files
*Files present in local directory but not clearly in the index*

| File | Title (inferred) | Book Ch. | Rating |
|------|-------------------|----------|--------|
| m04orgzx.txt | Организация ZX (?) | Ch.2 | ? |
| adv4tmtr.txt | (Unknown) | ? | ? |
| adv8opas.txt | (Unknown) | ? | ? |
| adv8vidc.txt | (Unknown) | ? | ? |
| dv0awkbt.txt | (Unknown) | ? | ? |
| ig5autoc.txt | (Unknown) | ? | ? |
| ig7bigpr.txt | (Unknown) | ? | ? |
| ig7reloc.txt | Relocatable code (?) | Ch.3 | ? |

---

## Top 30 Most Valuable Articles for the Book

Ranked by potential to improve specific chapters with techniques, algorithms, or code not yet fully covered in the drafts.

### Tier 1: Must-Read (directly fills gaps)

| # | File | Title | For Ch. | Why |
|---|------|-------|---------|-----|
| 1 | ig8tsprg.txt | Программирование Turbo Sound | Ch.11 | **Only TurboSound programming guide** with port addresses, chip switching, auto-detection code. Not covered this deeply in current draft. |
| 2 | zg2mchow.txt | О мультиколоре и MC24 | Ch.8 | **Definitive multicolor guide** by Alone Coder. 8 chapters, POP-based methods, 128K dual-screen tricks. Most comprehensive treatment of per-scanline techniques. |
| 3 | sng1msnc.txt | Синхронизация с музыкой в демах | Ch.12 | **Demo music sync system** with pseudo-programs and IM2 resident handler. From actual "Forever" demo. Nothing comparable in current drafts. |
| 4 | ig7hpack.txt | Практические принципы LZ упаковки | Ch.14 | **Most comprehensive LZ tutorial** in Russian ZX press (~8,000 words). Hash tables, lazy evaluation, Huffman trees. Deepens Ch.14 significantly. |
| 5 | zpw3gf3d.txt | Быстрая 3D-графика для Speccy | Ch.5 | **Novel 3D rotation method** — plane rotation + interpolation instead of per-point sin/cos. ~12,000 words. Real-time 175 vectors. |
| 6 | zg4optim.txt | Оптимизация по скорости | Ch.1, Ch.3 | Alone Coder on speed optimization. Cycle counts per chunk, code generation, rotation + bumpmapping. Teaches unconventional thinking. |
| 7 | ig7optim.txt | Основы оптимизации под Z80 | Ch.1, Ch.3 | **Self-modifying code patterns**, loop unrolling, multi-entry procedures. Canonical reference for demoscene toolbox. |
| 8 | zg45spro.txt | Быстрый вывод спрайтов | Ch.16 | Alone Coder's sprite system — pre-shifted tables, AND/XOR masking, EXX register switching. Designed for 20+ sprites in RTS. |
| 9 | bd05fc2p.txt | Fast C2P procedure | Ch.7 | Jump-table C2P with 256 pre-calculated routines. 109 cycles/pair, >25 fps fullscreen. Key technique for Ch.7. |
| 10 | ig10rndg.txt | О некоторых RND-генераторах | Ch.4 | LFSR + Mitchell-Moore generators with working Z80 code and parameter tables. Fills PRNG gap in Ch.4. |

### Tier 2: Valuable Supplementary Material

| # | File | Title | For Ch. | Why |
|---|------|-------|---------|-----|
| 11 | sng1bump/ | Phong Bump Mapping | Ch.6 | Bump mapping implementation on ZX. Advanced shading technique. |
| 12 | sng2txmp/ | Texture mapping | Ch.6 | Texture mapping on ZX Spectrum from Scenergy zine. |
| 13 | sng2txph.txt | Texture mapping + Phong shading | Ch.6 | Combined texturing + Phong on ZX. |
| 14 | sng2dngl.txt | Секреты DAINGY | Ch.20 | Demo post-mortem: derivative sine, chunk system, wave effect. Real production insights. |
| 15 | dod2plsm/ | Реализация плазмы 2x2 | Ch.9 | Plasma effect implementation. Relevant to attribute tunnels chapter. |
| 16 | dv05math.txt | Умножение, квадратный корень | Ch.4 | Table-based fast multiply (sum/difference of squares). 141-207 vs 310-358 cycles. |
| 17 | dod1pgns/ | Заливка треугольника, Гуро shading | Ch.5, Ch.6 | Triangle fill + Gouraud shading on ZX. |
| 18 | dod2phng/ | Phong shading | Ch.6 | Phong shading implementation from Demo Or Die. |
| 19 | bd09gmcc.txt | AY MCC (оцифровки) | Ch.12 | Digital sample playback on AY via MCC method. Key for digital drums chapter. |
| 20 | dv06huff.txt | Сжатие по Хаффмену | Ch.14 | Thorough Huffman tutorial (~8,000 words). Adaptive Huffman, tree rebalancing. |
| 21 | dod1hdfc.txt | Алгоритмы видимости поверхностей | Ch.5 | Backface culling, painter's algorithm, Z-buffer — theory overview. |
| 22 | zg1scfrm.txt | Вывод экрана за прерывание | Ch.2, Ch.3 | LD-PUSH method for full-screen in one interrupt. Challenges POP-PUSH. |
| 23 | asp4gfxb.txt | Быстрая и не очень графика | Ch.3, Ch.16 | LDI vs PUSH/POP vs POP+LD comparison for screen buffer output. |
| 24 | dod2chnk.txt | Chunks Output | Ch.7 | Two chunking approaches, dither table generation, 16 grayscale. |
| 25 | zf6mlclr.txt | Изготовление мультиколоров | Ch.8 | Practical multicolor step-by-step with IM 2 setup and LDI timing. |
| 26 | dod2sort.txt | Сортировка | Ch.5 | Sorting algorithms benchmarked on ZX: bubble, selection, merge, bytesort. For z-sorting in 3D. |
| 27 | kn10i256.txt | Intro в 256 байт? | Ch.13 | Complete 153-byte screensaver. Stack exploitation, dynamic tables. Size-coding example. |
| 28 | an12pt3x.txt | Формат Pro Tracker v3.x | Ch.11 | PT3 module format reference — needed for music playback code. |
| 29 | ig10mglz.txt | Формат MegaLZ | Ch.14 | MegaLZ packed format specification. |
| 30 | vw1pfind.txt | Поиск пути (BFS) | Ch.19 | Pathfinding with bit-packed cells. Good algorithm reference. |

---

## Source Magazines Represented

The ZXDN coding collection draws from 30+ scene publications:

| Abbreviation | Full Name | City | Articles | Quality |
|-------------|-----------|------|----------|---------|
| ZX-Guide (zg) | ZX-Guide | Ryazan | ~15 | **High** (Alone Coder) |
| Info Guide (ig) | Info Guide / Inferno Guide | Ryazan | ~20 | **High** |
| Deja Vu (dv) | Deja Vu | Kemerovo | ~25 | Medium-High |
| Adventurer (adv) | Adventurer | Kazan | ~15 | Medium |
| Demo Or Die (dod) | Demo Or Die | — | ~12 | **High** (demoscene focus) |
| Scenergy (sng) | Scenergy | Novgorod | ~8 | **High** (demoscene focus) |
| Born Dead (bd) | Born Dead | Samara | ~10 | High |
| ZX Format (zf) | ZX Format | St. Petersburg | ~20 | Medium |
| Black Crow (bc) | Black Crow | — | ~8 | Medium |
| Echo (ec) | Echo | — | ~8 | Medium |
| ZX Power (zpw) | ZX Power | — | ~6 | Medium-High |
| AlCoNews (an) | AlCoNews | Ryazan | ~6 | Medium |
| ASpect (asp) | ASpect | St. Petersburg | ~3 | Medium |
| Move (m) | Move | — | ~5 | Medium |
| Funeral (fu) | Funeral | — | ~3 | Medium |
| Depth (dpt) | Depth | — | ~2 | Medium |
| Nicron (n) | Nicron | — | ~2 | Low-Medium |
| Spectrofon (sp) | Spectrofon | — | ~2 | Medium |
| Spectrum Expert (se) | Spectrum Expert | St. Petersburg | ~1 | **High** |
| Flash Time (flt) | Flash Time | — | ~1 | Medium |
| Virtual Worlds (vw) | Virtual Worlds | Dzerzhinsky | ~3 | Medium |
| Krasnodar News (kn) | Krasnodar News | Krasnodar | ~2 | Medium |
| Don News (dn) | Don News | — | ~1 | Medium |
| IzhNews (iz) | IzhNews | Izhevsk | ~2 | Low |
| Psychoz (ps) | Psychoz | — | ~1 | Medium |
| Bugs (bg) | Bugs | — | ~2 | Low |
| Body (bd) | Body | — | ~2 | Low |
| MSD (ms) | MSD | — | ~2 | Low |
| LPrint (lp) | LPrint | — | ~3 | Low-Medium |
| Online (on) | Online | — | ~2 | Low |
| Optron (op) | Optron | — | ~3 | Low |

---

## Coverage Map: ZXDN Articles per Book Chapter

| Chapter | Topic | # Relevant | Top Sources |
|---------|-------|-----------|-------------|
| Ch.1 | T-state budgets | 5 | zg4optim, ig7optim, kn10beam |
| Ch.2 | Screen memory/ULA | 5 | zg1scfrm, zg1etud1, n125dnhl |
| Ch.3 | Demoscene toolbox | 8 | ig7optim, zg4optim, asp4gfxb, dv05sint |
| Ch.4 | Multiply/PRNG/math | 12 | ig10rndg, dv05math, zf7fcalc, dod2sqtg |
| Ch.5 | 3D wireframe | 10 | zpw3gf3d, dod1hdfc, dod13d2d, dod2sort |
| Ch.6 | Sphere/texture | 8 | sng1bump, sng2txmp, sng2txph, dod2phng |
| Ch.7 | Rotozoomer/chunky | 7 | bd05fc2p, dod2chnk, adv9rotm, zg4ch4g |
| Ch.8 | Multicolor | 5 | zg2mchow, zf6mlclr, zf5bordr, m02mcbrd |
| Ch.9 | Tunnels/zoomers | 5 | dod2plsm, vw1water, dv04pbls, iz09fire |
| Ch.10 | Dotfield | 2 | dod2mvsh |
| Ch.11 | AY/TurboSound | 10 | ig8tsprg, flt1ayfq, se01gsfc, an12pt3x |
| Ch.12 | Drums/sync | 4 | sng1msnc, bd09gmcc, bd0gdpcm |
| Ch.13 | Size-coding | 3 | kn10i256, bd0abopt |
| Ch.14 | Compression | 10 | ig7hpack, dv06huff, ig10mglz, sng2jamv |
| Ch.15 | 128K banking | 4 | sng1ramd, on76ramd, bd10p1mb |
| Ch.16 | Fast sprites | 8 | zg45spro, zpw3mask, dv05dspr, dv05sint |
| Ch.17 | Scrolling | 4 | 3b1scrll, adv8atsc, ig10atms |
| Ch.18 | Game loop | 4 | ig8p16cg, ad11game, dv09keyb |
| Ch.19 | Collisions/AI | 4 | vw1pfind, zf5cgmai, dn21gmai, zf6wvalg |
| Ch.20 | Demo workflow | 3 | sng2dngl, adv8iris |
| Ch.21-23 | (porting/AI) | 0 | — |

---

## Notes on Access

Local copy at `_in/raw/zxdn/` — cloned from GitHub mirror (https://github.com/alexanderk23/zxdn). Full content, 292 coding articles.

Articles are plain text in **CP1251** encoding (Windows Cyrillic). Read with:
```python
with open(filename, 'rb') as f:
    text = f.read().decode('cp1251')
```
