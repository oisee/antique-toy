
# Coding the Impossible: Z80 Demoscene Techniques for Modern Makers

*From inner loops to AI-assisted development — a practical guide to pushing 8-bit hardware to the limit*

-----

## Concept

A book that bridges two worlds: the hard-won wisdom of ZX Spectrum demoscene coders and the modern toolchain (VS Code, AI assistants, eZ80 hardware like Agon Light 2). Not a nostalgia trip — a *living* technical book where every technique is explained, every example compiles, and readers can run everything on real or emulated hardware.

**Target audience:** Retro-computing enthusiasts who remember Z80 but never wrote demos. Modern embedded developers curious about extreme optimisation. Demosceners who want their knowledge documented before it’s lost.

**Key differentiator:** Every chapter follows the pattern: *idea → constraint → trick → working code → “try it yourself”*. Source code for all examples on GitHub. Interactive playground for testing.

-----

## Part I: The Machine and the Mindset

### Chapter 1: Thinking in Cycles

The Z80 programmer’s worldview: everything is a budget
T-states, machine cycles, and why they matter
Pentagon vs. wait machines (Scorpion): why cycle counts differ
The frame budget: 69,888 T-states (48K) vs 71,680 (Pentagon) — your canvas
**Practical:** Set up VS Code + Z80MacroAsm boilerplate (reference: aGGreSSor’s 2026 Hype article)
**Practical:** Write a “how fast is this?” timing harness
**Historical note:** Dark/X-Trade’s advice from Spectrum Expert #01: “read a maths textbook — derivatives, integrals. Knowing them, you can create a table of practically any function in assembly”
### Chapter 2: The Screen as a Puzzle

ZX Spectrum video memory layout: the weird interleave and why it exists
Attribute memory: 768 bytes that changed everything
The border: not just decoration — a timing-visible debug tool
**Practical:** Fill the screen, fill the attributes, make a border stripe
The eZ80 difference: Agon Light 2’s VDP and what changes
### Chapter 3: The Demoscener’s Toolbox

Unrolled loops and self-modifying code
The stack as a data pipe: PUSH/POP tricks for fast output
LDI chains and why ldi is everyone’s best friend
Code generation: when your program writes the program that draws the screen
**Interview fragment:** Introspec on “coder effects are always about evolving a computation scheme”
### Chapter 3½: The Maths You Actually Need

*Based on Dark/X-Trade’s legendary Spectrum Expert articles — the same Dark who coded Illusion*

**Multiplication on Z80** (from SE#01)

Method 1: shift-and-add from LSB — the classic RR C : JR NC,$+3 : ADD A,B : RRA loop
8×8→16 in 196–204 T-states, 16×16→32 in 730–826 T-states
Method 2: square table lookup — A*B = ((A+B)²-(A-B)²)/4
61 T-states (!) but with accuracy trade-off — “choose: speed or accuracy”
**Practical:** Build both multipliers, compare outputs, see the vertex jitter
**Division on Z80** (from SE#01)

Shift-and-subtract: the restoring division algorithm
8/8 in 236–244 T-states, 16/16 in 938–1034 T-states
Logarithmic division: Log(A/B) = Log(A) - Log(B) with 256-byte tables
Generating log/antilog tables: derivative-based calculation in assembly
Dark’s “method of guessing” the 0.4606 correction coefficient — honest maths
**Sine and Cosine** (from SE#01)

The parabolic approximation: Y ≈ X² mimics a half-period of sine
Generating a 256-byte signed cosine table in a tight loop
**Sidebar:** Raider’s “9 commandments” of sine tables (from the Hype comments)
**Bresenham’s Line** (from SE#01)

Classic algorithm → Xopha modification → why both are too slow
Dark’s matrix method: 8×8 pixel grids with SET x,(HL), trap-based termination
From ~80 cycles/pixel down to ~48 cycles/pixel minimum
“87.5% of checks are wasted” — the insight that drives the optimisation
**Practical:** Draw lines fast enough for wireframe 3D
### Chapter 3¾: 3D on 3.5 MHz

*Based on Dark & STS’s Spectrum Expert #02*

**The Midpoint Method** (from SE#02)

The problem: 12 multiplications per vertex × N vertices = pain
The trick: compute only a cube (or other simple solid), derive all other vertices by averaging
Virtual processor with 4 commands: Load, Store, Average, End
Writing “programs” for vertex interpolation: DB 4,128!5,64!8
**Practical:** A spinning 3D object using midpoint vertex generation
**Solid Polygons** (from SE#02)

Backface culling via normal Z-component: Vx*Wy - Vy*Wx
Convex polygon filling
Z-sorting for complex objects
**Practical:** A solid rotating cube
**Historical context:** These articles are from 1997–1998. The same team (X-Trade) released Illusion around this time. The algorithms in the magazine are the building blocks of the demo.

-----

## Part II: Classic Effects Deconstructed

*Each chapter takes a real demo, explains the effect, shows the inner loop, counts the cycles, and provides a buildable version.*

### Chapter 4: The Sphere — Texture Mapping on 3.5 MHz

**Source demo:** Illusion by X-Trade (1997)
The idea: byte-per-pixel source → bit-packed sphere
The inner loop: add a : add (hl) with variable inc l skips
Code generation for sphere geometry — lookup tables of pixel skips
Counting cycles: 101+32x T-states per byte, why it fits in one frame
Map projections on a budget: equirectangular, Mercator, and “whatever looks round”
**Practical:** Build a 56×56 spinning sphere
**Sidebar:** The Hype thread — how kotsoft and Introspec argued about what matters more, the inner loop or the maths
### Chapter 5: Rotozoomer and Moving Shit

**Source demo:** Illusion by X-Trade
Walking through a texture at an angle: the core rotation idea
2×2 chunky pixels: storing #03 or #00 in a byte
The inner loop: inc l / dec h changing per-frame for rotation
Per-frame code generation: recalculating the walk direction
Buffer → screen via pop hl : ld (nn),hl
Cycle budget: 95 T-states per 4 chunks → 4–6 frames per screen
**Practical:** Build a simple rotozoomer with sine-table movement
**Deep dive:** Sine tables in 256 bytes — Raider’s 9 commandments
### Chapter 6: The Dotfield Scroller

**Source demo:** Illusion by X-Trade
Texture in memory → per-pixel screen output
The inner loop: ld a,(bc) : pop hl : rla : jr nc,$ : set ?,(hl) — 36 T-states per pixel
Stack-based address tables for bouncing motion
Timing analysis: why it comfortably fits with room to spare
**Practical:** A bouncing dot-matrix text scroller
### Chapter 7: Attribute Tunnels and Chaos Zoomers

**Source demo:** Eager by Introspec (2015)
Pseudo-chunky attributes: variable-size “pixels” hiding low centre resolution
Inspiration: Bomb by Atebit’s twister trick
Plasma-based tunnel with sub-pixel smoothness and 4-fold symmetry
Copy with reflections: ld a,(hl) : ld (nn),a : ld (mm),a : ld (bc),a : ldi
Chaos zoomer via unrolled ld hl,nn : ldi with optimisations
Code generation in Processing → Z80 assembly
**Practical:** An attribute tunnel with reflection symmetry
**Sidebar:** “Zapilator” — the spectrum community’s love-hate relationship with precalculation
### Chapter 8: 4-Phase Colour Animation

**Source demo:** Eager by Introspec
2 normal + 2 inverted frames → palette shift = smooth illusion
Anti-clashing pixel selection and why “off” pixels show through
Overlaying text on animation
**Practical:** A simple 4-phase colour cycling animation
-----

## Part III: Sound Meets Screen

### Chapter 9: Digital Drums on the AY

**Source demo:** Eager by Introspec
The challenge: AY has 3 channels, digital audio has… zero
Interrupting drums from the beeper world → AY adaptation
Blending digital samples with AY: the loudness problem
n1k-o’s insight: digital attack + AY decay = convincing hybrid
Frame budgeting with drums: 2 frames per hit, async video generation
Double-buffered attribute frames: prepare 2 pages, play drum, flip
**Practical:** Add a single digital kick drum to an AY track
**Sidebar:** Why nobody heard the digital drums at DiHalt — the emulator problem
### Chapter 10: Music-Synced Demo Engines

Introspec’s two-level scripting: outer script (effects) + inner script (variations)
The kWORK command: generate N frames, show independently
Async generation: falling behind during drums, catching up between hits
Race conditions and resource wars — “real multithreading” on Z80
**Practical:** A minimal scripted demo engine with 3 effects and music sync
-----

## Part IV: The Craft of Size-Coding

### Chapter 11: 512 Bytes of Wonder

Anatomy of a 512-byte intro
Every byte counts: overlapping code and data
Self-modifying tricks for extreme compression
**Teardown:** [Selected 512b intro — candidate: psndcj or Screamer work]
**Practical:** Write a 512-byte intro step by step
### Chapter 12: 4K — A Complete Demo in a Page of Memory

What fits in 4096 bytes: effects + music + flow
Compression and decompression strategies
Runtime generation vs. stored data: the eternal trade-off
**Teardown:** [Selected 4K intro — TBD based on interviews]
**Practical:** A 4K intro with tunnel + music + credits
-----

## Part V: Modern Workflows

### Chapter 13: AI-Assisted Z80 Development

Claude Code and the feedback loop: write → assemble → emulate → debug → iterate
DeZog integration: automated debugging with breakpoints and memory inspection
Unit testing Z80 code: yes, really
When AI helps (iteration, boilerplate, test generation) vs. when it doesn’t (novel optimisation)
**Case study:** Building MinZ — a Z80 programming language with AI assistance
**Honest take:** Introspec says “Z80 they still don’t know” — where are the real limits?
**Historical parallel:** HiSoft C on ZX Spectrum (SE#02) — “10–15x faster than BASIC” but no floats. Higher-level languages on constrained hardware have always been a compromise. How does AI-assisted assembly compare?
### Chapter 14: From Spectrum to Agon Light 2

eZ80 @ 18 MHz: what stays the same, what changes
The Agon Light 2 VDP: modern video output with retro spirit
Porting Spectrum effects to eZ80: a practical guide
CP/M on eZ80: running classic software on modern hardware
**Case study:** The Hobbit on Agon Light 2 — emulation with procedure interception
### Chapter 15: The Living Demoscene

Multimatograf, DiHalt, Chaos Constructions — parties that still run
How to enter your first compo
The community: Hype, ZXArt, Pouet
“No Heart Beats Forever” — why people still make demos in 2026
-----

## Appendices

### A: Z80 Instruction Reference with Cycle Counts

Sorted by use case (output, calculation, flow control)
Pentagon vs. 48K timing differences
The border timing table: out at 11 vs 12 T-states (with the full Hype thread story)
### B: Sine Table Generation

256-byte sine table
Fixed-point arithmetic on Z80
Raider’s method: H = table base, L = argument, rotate L freely
Dark’s parabolic approximation from SE#01: fast, visually close, not mathematically exact
### B½: Logarithm and Power-of-2 Tables

Why Log(A/B) = Log(A) - Log(B) enables fast division
Generating 2^(X/256) tables using derivative-based iteration
Dark’s “method of guessing” the 0.4606 correction for log tables — and his honest admission: “something is not right here, so it is recommended to write a similar one yourself”
The beauty of approximate maths: when “close enough” is the whole point
### C: Setting Up Your Development Environment

VS Code + Z80MacroAsm + SjASMPlus
Emulators: which one for what (Fuse, Unreal, Spectaculator, ZXMAK2 — and why they all sound different)
DeZog for debugging
Getting code onto real hardware
### D: eZ80 Quick Reference

New instructions and addressing modes
24-bit address space
Agon Light 2 MOS API basics
-----

## Source Materials & Status

|Material                                       |Status       |Source                                       |
|-----------------------------------------------|-------------|---------------------------------------------|
|Illusion inner loops + cycle analysis          |✅ Have       |Introspec’s Hype article                     |
|Eager making-of + design process               |✅ Have       |Introspec’s Hype article                     |
|Dark/X-Trade: Algorithms (mult, div, sin, line)|✅ Have       |Spectrum Expert #01 via ZXArt                |
|Dark/X-Trade: 3D graphics + midpoint method    |✅ Have       |Spectrum Expert #02 via ZXArt                |
|Dark/X-Trade: HiSoft C on Spectrum             |✅ Have       |Spectrum Expert #02 via ZXArt                |
|Eager source code                              |🟡 Promised   |Introspec (private, need permission for book)|
|Introspec interview on thought process         |🟡 Partial    |Telegram conversation 2026-02-20             |
|psndcj interview                               |❌ Need       |Contact via demoscene                        |
|Screamer interview                             |❌ Need       |Contact via demoscene                        |
|512b/4K intro teardowns                        |❌ Need       |Select specific works, get permission        |
|MinZ case study                                |🟡 In progress|Alice’s own project                          |
|Agon Light 2 porting guide                     |🟡 In progress|Alice’s own project                          |
|aGGreSSor’s VS Code setup guide                |✅ Have       |Hype article Jan 2026                        |
|Book Alice bought (bad content, good TOC)      |✅ Have       |Amazon link in chat                          |
|Other Spectrum e-zine articles                 |🟡 To survey  |ZXArt press archive                          |

-----

## Notes on Approach

**Every code example must compile and run.** No pseudocode, no “exercise for the reader” hand-waving. GitHub repo with CI that builds everything.
**Respect the sources.** Introspec explicitly said his sources are closed but he’d share with Alice. Each use needs explicit permission. Don’t paraphrase people’s techniques without credit.
**The AI angle is honest, not hype.** Document where Claude Code actually helped (MinZ, emulator work, iteration loops) and where it didn’t (novel Z80 optimisation, creative effect design). Introspec’s scepticism is valid and worth including.
**Bilingual consideration.** The demoscene community around ZX Spectrum is heavily Russian-speaking. Consider whether the book should be in English, Russian, or both. The Hype articles are in Russian; interviews would likely be in Russian.
**The “купила книгу с хорошим оглавлением но контент…” problem.** The book Alice bought had a good TOC but bad content. Our differentiator: real demos, real code, real people explaining their real thought processes. Not academic, not superficial.
**The X-Trade thread.** Dark from X-Trade wrote both the Spectrum Expert algorithm articles (1997–98) AND coded Illusion. Introspec then reverse-engineered Illusion’s inner loops on Hype in 2017. We have *both sides* — the original author teaching fundamentals, and a peer analysing the finished product 20 years later. This is an extraordinary narrative thread that should be woven through Part I → Part II.
**ZXArt as archive.** The Spectrum Expert articles are preserved on zxart.ee with full text. There’s likely more material in other e-zines on ZXArt’s press archive that could feed into the book. Worth a systematic survey.
——

https://zxart.ee/eng/software/

Собери там хорошие статьи от желательно хороших кодеров и сценеров по дизайну и созданию разных дем исторических от разных групп, журналы как zx format, spectrum expert, scenergy, born dead, #z80, и другие может быть ещё современные газеты

Show more
20 Feb

Surveying ZXArt archives for seminal demoscene articles
Surveying ZXArt archives for seminal demoscene articles


Let me explore what's available on ZXArt's press archive systematically.


Organized technical sources by relevance and compiled comprehensive resource inventory
Organized technical sources by relevance and compiled comprehensive resource inventory



































Now I have enough to compile a comprehensive survey. Let me build the document.


Acknowledged comprehensive Z80 demoscene book proposal structure
Acknowledged comprehensive Z80 demoscene book proposal structure



Вот обзор. Несколько ключевых находок:

Главные источники помимо уже имеющихся:

ZX Format #02 — содержит статью по ассемблеру (основы) и описание ZX General Sound от X-Trade (тех же людей, что делали Illusion). Связка X-Trade → Spectrum Expert → Illusion → ZX General Sound — это дополнительная нить повествования.
Black Crow #05 — статья о multicolor-эффектах с алгоритмом и примером кода. Может быть релевантна для Part II.
Hype/Development — статья DenisGrachev'а про создание NHBF (2025) — свежий making-of, идеально подходит к Chapter 15. Также его же «Ещё раз про тайлы и RET» — техника кодинга.
Subliminal Extacy — единственный англоязычный сценовый журнал, 5 номеров с 1995 по 2023. Если книга будет на английском, это хороший мостик.
Чего не нашлось напрямую:

Scenergy точно существует (многократно упоминается как эталон), но отдельные номера на ZXArt нужно искать вручную через их интерфейс — поисковики его плохо индексируют.
Журнал #z80 как отдельное издание не всплыл — возможно, это тег/рубрика, а не самостоятельный журнал.
Следующий логичный шаг — открыть ZXArt напрямую и пройтись по категориям Press → Electronic Magazine руками, фильтруя по наличию статей с тегами «программирование» / «демо».

Zxart press survey
Document · MD 
Собери ещё статьи на hype и на pouet diz:

про rain я немножко писал в дизнике (introspec)

про свои эффекты в break space чуть-чуть в дизнике тоже

(Introspec)

20 Feb

Разыскивал демо-описания Introspec про rain и break space
Разыскивал демо-описания Introspec про rain и break space










Now let me find the Pouet descriptions. First the "rain" demo:


Локализовал источники статей и планировал сбор материалов
Локализовал источники статей и планировал сбор материалов





Давай соберу конкретные дизники Introspec'а на Pouet. Начну с Rain и поищу Break Space.


Разыскал описания эффектов в NFO файлах проектов
Разыскал описания эффектов в NFO файлах проектов






Теперь достану NFO-файлы — именно там дизники с описаниями эффектов.


Переориентировался на прямую загрузку архива и поиск NFO-файлов
Переориентировался на прямую загрузку архива и поиск NFO-файлов






Let me try to get the NFO files by downloading the actual releases.


Переключался между источниками для поиска информации
Переключался между источниками для поиска информации









Let me try to get Introspec's full prod list from Pouet and the Eager making-of from Hype:


Собрал технические статьи из множественных источников и архивов
Собрал технические статьи из множественных источников и архивов










Собрал достаточно. Теперь скомпилирую всё в документ. NFO/diz-файлы Rain и Break Space находятся внутри zip-архивов на scene.org — у меня нет доступа к скачиванию оттуда, но я зафиксирую точные URL.


Подготовился к краткому ответу на русском
Подготовился к краткому ответу на русском




Собрал полный каталог. Вот что нашлось:

Hype — все 27 топиков Introspec'а, из них 6 чисто технических (DOWN_HL, два обзора компрессоров, разбор Illusion, GO WEST ч.1 и ч.2), плюс Making of Eager и пачка обзоров демо-компо.

Pouet diz/nfo — три ключевых файла, которые нужно достать вручную из zip-архивов:

Rain (file_id.diz) — описание rain-эффекта. Архив: rain.zip на scene.org / bbb.retroscene.org
Break Space (breakspace.nfo) — описание эффектов Introspec'а. Архив: breakspace_by_thesuper.zip на scene.org
Eager (nfo) — технический writeup, который Kylearan на Pouet особо отметил: "Big thanks for the nfo file alone, I love reading technical write-ups!"
Бонус: обнаружилось, что в Break Space X-Trade написал 3D-движок — тот же X-Trade, чей Dark писал алгоритмы в Spectrum Expert и кодил Illusion. То есть X-Trade → Introspec нить ещё плотнее, чем казалось: они буквально со-авторы одной демы.

Файлы с scene.org скачать из моего окружения не получилось (домен заблокирован), но все URL точные — можешь сама вытащить дизники.

Introspec hype pouet sources
Document · MD 
Получилось?

00:11

Диагностировал неудачу загрузки и рассмотрел альтернативные источники
Диагностировал неудачу загрузки и рассмотрел альтернативные источники



Нет — scene.org не в списке разрешённых доменов для скачивания. Попробую через bbb.retroscene.org:


Inventoried accessible domains, pivoted to alternative retrieval method
Inventoried accessible domains, pivoted to alternative retrieval method




Тоже нет — bbb.retroscene.org не в разрешённых доменах. Попробую вытянуть NFO через web_fetch:


Обнаружил неполную загрузку, ищет альтернативные источники
Обнаружил неполную загрузку, ищет альтернативные источники


Страница загрузилась, но содержимое демо (файлы) доступно только по прямой ссылке на скачивание, которая заблокирована.

Короче — нет, не получилось. Ни scene.org, ни bbb.retroscene.org нет в списке разрешённых доменов для скачивания из моего окружения. NFO/diz-файлы лежат внутри zip-архивов, и достать их программно я не могу.

Всё остальное собрано: полный каталог 27 статей Introspec'а на Hype, три Pouet-страницы с комментариями и точные URL на архивы. Дизники нужно вытащить вручную — скачать три zip'а:

rain.zip → file_id.diz (описание rain-эффекта)
breakspace_by_thesuper.zip → breakspace.nfo (эффекты Introspec'а)
eager(party).zip → nfo (технический writeup)
Запусти глубокое исследование по лучшим статьям выше и проч

00:12

Подготовил комплексное исследование технических статей для проекта
Подготовил комплексное исследование технических статей для проекта

Запускаю глубокое исследование по всем ключевым источникам. Поехали!


# ZX Spectrum demoscene technical research
favicon
favicon
favicon
Research complete
•
397 sources
•
19m 5s
Your ZX Spectrum demoscene source audit for Coding the Impossible is ready. It covers 14 of 18 targeted Introspec sources with full technical extractions, including Z80 assembly listings with T-state analysis, compression packer benchmarks across 10 tools, contended memory maps for Pentagon-to-Sinclair porting, and scene-by-scene breakdowns of demos like Break Space and Hara Mamba. The report maps every source to your book's five parts and flags five articles on hype.retroscene.org that require direct browser retrieval.

Introspec's ZX Spectrum Demoscene Wisdom: A Source Audit for Coding the Impossible
Document 
Отлично, подготовь пожалуйста список заданий мне для извлечения соответствующих текстов из архивов до которых тебе не получается добраться, и какие статьи и журналы надо бы тебе найти и скачать

08:50

Acknowledged request for task compilation and resource identification
Acknowledged request for task compilation and resource identification







Готово. Всего 6 категорий, ~20 заданий, отсортированных по приоритету:

Фаза 1 (быстрая, ~30 мин): 5 Hype-статей Introspec'а просто открыть в браузере и сохранить (B1–B5), плюс 3 zip-архива скачать с scene.org и вытащить diz/nfo (A1–A3). Самый ценный — B1 (разбор Illusion), он критический для Part II.

Фаза 2 (эмулятор, 1–2 часа): Spectrum Expert #01–03 от Dark'а — это TRD-образы, нужно открыть в Unreal Speccy и найти технические статьи. Замыкает нарративную нить Dark→Introspec→Break Space.

Фаза 3 (по желанию): дополнить три частично извлечённые статьи (Chunky, Hara Mamba, Tiles&RET), проверить Pouet-комментарии, поискать дополнительных авторов.

Всё что загрузишь сюда — обработаю и вплету в план книги.

Manual extraction tasks
Document · MD 




Claude is AI and can make mistakes. Please double-check responses.
Claude