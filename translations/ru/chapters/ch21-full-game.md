# Глава 21: Полная игра -- ZX Spectrum 128K

> *«Единственный способ узнать, работает ли твой движок, -- выпустить игру.»*

---

У тебя есть спрайты (Глава 16). У тебя есть скроллинг (Глава 17). У тебя есть игровой цикл и система сущностей (Глава 18). У тебя есть столкновения, физика и ИИ врагов (Глава 19). У тебя есть музыка на AY и звуковые эффекты (Глава 11). У тебя есть сжатие (Глава 14). У тебя есть 128K банковой памяти, и ты знаешь, как обращаться к каждому её байту (Глава 15).

Теперь тебе нужно поместить всё это в один бинарный файл, который грузится с ленты, показывает экран загрузки, представляет меню, проводит пять уровней бокового скроллера с четырьмя типами врагов и боссом, ведёт таблицу рекордов и помещается в файл `.tap`.

Это глава интеграции. Здесь не появляется новых техник. Вместо этого мы сталкиваемся с проблемами, которые возникают только тогда, когда все подсистемы должны сосуществовать: конкуренция за память между графическими банками и кодом, бюджеты кадра, которые переполняются, когда скроллинг, спрайты, музыка и ИИ одновременно требуют свою долю, системы сборки, которые должны координировать десятки шагов конвертации данных, и тысяча мелких решений о том, что куда разместить в 128K банковой памяти.

Игра, которую мы создаём, называется *Ironclaw* -- пятиуровневый боковой платформер, в котором механический кот пробирается через серию всё более враждебных фабричных этажей. Жанр выбран намеренно: боковые платформеры требуют одновременной работы всех подсистем и не дают спрятаться. Если скроллинг заикается, ты это видишь. Если рендеринг спрайтов не укладывается в кадр, ты это чувствуешь. Если обнаружение столкновений даёт сбой, игрок проваливается сквозь пол. Платформер -- это самый жёсткий интеграционный тест, с которым может столкнуться игровой движок на Z80.

---

## 21.1 Архитектура проекта

Прежде чем написать хотя бы одну строку Z80-кода, тебе нужна структура каталогов, которая масштабируется. Игра для 128K с пятью уровнями, набором тайлов, листами спрайтов, музыкальной партитурой и звуковыми эффектами генерирует десятки файлов данных. Если ты не организуешь их с самого начала, ты утонешь.

### Структура каталогов

```text
ironclaw/
  src/
    main.a80           -- entry point, bank switching, state machine
    render.a80          -- tile renderer, scroll engine
    sprites.a80         -- sprite drawing routines (OR+AND masked)
    entities.a80        -- entity update, spawning, despawning
    physics.a80         -- gravity, friction, jump, collision response
    collisions.a80      -- AABB and tile collision checks
    ai.a80              -- enemy FSM: patrol, chase, attack, retreat, death
    player.a80          -- player input, state, animation
    hud.a80             -- score, lives, status bar
    menu.a80            -- title screen, options, high scores
    loader.a80          -- loading screen, tape/esxDOS loader
    music_driver.a80    -- PT3 player, interrupt handler
    sfx.a80             -- sound effects engine, channel stealing
    esxdos.a80          -- DivMMC file I/O wrappers
    banks.a80           -- bank switching macros and utilities
    defs.a80            -- constants, memory map, entity structure
  data/
    levels/             -- level tilemaps (compressed)
    tiles/              -- tileset graphics
    sprites/            -- sprite sheets (pre-shifted)
    music/              -- PT3 music files
    sfx/                -- SFX definition tables
    screens/            -- loading screen, title screen
  tools/
    png2tiles.py        -- PNG tileset converter
    png2sprites.py      -- PNG sprite sheet converter (generates shifts)
    map2bin.py          -- Tiled JSON/TMX to binary tilemap
    compress.py         -- wrapper around ZX0/Pletter compression
  build/                -- compiled output (gitignored)
  Makefile              -- the build system
```

Каждый исходный файл сосредоточен на одной подсистеме. Каждый файл данных проходит через конвейер преобразования, прежде чем попадёт к ассемблеру. Каталог `tools/` содержит Python-скрипты, которые конвертируют удобные для художника форматы (PNG-изображения, карты редактора Tiled) в бинарные данные, готовые для ассемблера.

### Система сборки

Makefile -- это хребет проекта. Он должен:

1. Конвертировать всю графику из PNG в бинарные данные тайлов/спрайтов
2. Конвертировать карты уровней из формата Tiled в бинарные тайловые карты
3. Сжать данные уровней, графические банки и музыку подходящим упаковщиком
4. Ассемблировать все исходные файлы в один бинарник
5. Сгенерировать итоговый файл `.tap` с правильным загрузчиком

```makefile
# Ironclaw Makefile
ASM       = sjasmplus
COMPRESS  = zx0
PYTHON    = python3

# Data conversion
data/tiles/tileset.bin: data/tiles/tileset.png
	$(PYTHON) tools/png2tiles.py $< $@

data/sprites/player.bin: data/sprites/player.png
	$(PYTHON) tools/png2sprites.py --shifts 4 $< $@

data/levels/level%.bin: data/levels/level%.tmx
	$(PYTHON) tools/map2bin.py $< $@

# Compression (ZX0 for level data -- good ratio, small decompressor)
data/levels/level%.bin.zx0: data/levels/level%.bin
	$(COMPRESS) $< $@

# Compression (Pletter for graphics -- faster decompression)
data/tiles/tileset.bin.plt: data/tiles/tileset.bin
	pletter5 $< $@

# Assembly
build/ironclaw.tap: src/*.a80 data/levels/*.zx0 data/tiles/*.plt \
                    data/sprites/*.bin data/music/*.pt3
	$(ASM) --fullpath src/main.a80 --raw=build/ironclaw.tap

.PHONY: clean
clean:
	rm -rf build/ data/**/*.bin data/**/*.zx0 data/**/*.plt
```

Ключевая идея -- конвейер данных. Художник экспортирует PNG-тайлсет из Aseprite. Скрипт `png2tiles.py` нарезает его на тайлы 8x8 или 16x16, конвертирует каждый в чересстрочный пиксельный формат Spectrum и записывает бинарный блоб. Дизайнер уровней экспортирует карту `.tmx` из Tiled. Скрипт `map2bin.py` извлекает индексы тайлов и записывает компактную бинарную тайловую карту. Упаковщик сжимает каждый блоб. И только тогда ассемблер подключает результат через INCBIN в нужный банк памяти.

Этот конвейер означает, что контент игры всегда в редактируемой форме (PNG, TMX), а система сборки обрабатывает каждое преобразование автоматически. Измени тайл в PNG, набери `make`, и новый тайл появится в игре.

---

## 21.2 Карта памяти: распределение банков 128K

ZX Spectrum 128K имеет восемь 16-килобайтных банков ОЗУ, пронумерованных от 0 до 7. В любой момент процессор видит 64-килобайтное адресное пространство:

```text
$0000-$3FFF   ROM (16KB) -- BASIC or 128K editor ROM
$4000-$7FFF   Bank 5 (always) -- screen memory (normal screen)
$8000-$BFFF   Bank 2 (always) -- typically code
$C000-$FFFF   Switchable -- banks 0-7, selected via port $7FFD
```

Банки 5 и 2 жёстко привязаны к адресам `$4000` и `$8000` соответственно. Только верхнее 16-килобайтное окно (`$C000-$FFFF`) переключается. Регистр выбора банка по порту `$7FFD` также управляет отображаемым экраном (банк 5 или банк 7) и активной страницей ПЗУ.

```z80 id:ch21_memory_map_128k_bank_2
; Port $7FFD layout:
;   Bit 0-2:  Bank number for $C000-$FFFF (0-7)
;   Bit 3:    Screen select (0 = bank 5 normal, 1 = bank 7 shadow)
;   Bit 4:    ROM select (0 = 128K editor, 1 = 48K BASIC)
;   Bit 5:    Disable paging (PERMANENT -- cannot be undone without reset)
;   Bits 6-7: Unused

; Switch to bank N at $C000
; Input: A = bank number (0-7)
; Preserves: all registers except A
switch_bank:
    or   %00010000          ; ROM 1 (48K BASIC) -- keep this set
    ld   (last_bank_state), a
    ld   bc, $7FFD
    out  (c), a
    ret

last_bank_state:
    db   %00010000          ; default: bank 0, normal screen, ROM 1
```

Критически важное правило: **всегда сохраняй последнюю запись в `$7FFD`** в теневой переменной. Порт `$7FFD` -- только для записи, прочитать текущее состояние нельзя. Если тебе нужно изменить один бит (скажем, переключить экран), не нарушая выбор банка, ты должен прочитать теневую переменную, изменить нужный бит, записать результат и в порт, и в теневую переменную.

### Распределение банков Ironclaw

Вот как Ironclaw распределяет свои 128 килобайт по восьми банкам:

```text
Bank 0 ($C000)  -- Level data: tilemaps for levels 1-2 (compressed)
                   Tileset graphics (compressed)
                   Decompression buffer

Bank 1 ($C000)  -- Level data: tilemaps for levels 3-5 (compressed)
                   Boss level data and patterns
                   Enemy spawn tables

Bank 2 ($8000)  -- FIXED: Main game code
                   Player logic, physics, collisions
                   Sprite routines, entity system
                   State machine, HUD
                   ~ 14KB code, 2KB tables/buffers

Bank 3 ($C000)  -- Sprite graphics (pre-shifted x4)
                   Player: 6 frames x 4 shifts = 24 variants
                   Enemies: 4 types x 4 frames x 4 shifts = 64 variants
                   Projectiles, particles, pickups
                   ~ 12KB total

Bank 4 ($C000)  -- Music: PT3 song data (title, levels 1-3)
                   PT3 player code (resident copy)

Bank 5 ($4000)  -- FIXED: Normal screen
                   Pixel data $4000-$57FF (6,144 bytes)
                   Attributes $5800-$5AFF (768 bytes)
                   Remaining ~9KB: interrupt handler, screen buffers

Bank 6 ($C000)  -- Music: PT3 song data (levels 4-5, boss, game over)
                   SFX definition tables
                   SFX engine code

Bank 7 ($4000)  -- Shadow screen (used for double buffering)
                   Also usable as 16KB data storage when
                   not actively double-buffering
```

<!-- figure: ch21_128k_bank_allocation -->

```text
         ZX Spectrum 128K — Ironclaw Bank Allocation
         ═══════════════════════════════════════════

$0000 ┌─────────────────────────────┐
      │         ROM (16 KB)         │  BASIC / 128K editor
$4000 ├─────────────────────────────┤
      │    Bank 5 — FIXED           │  Screen pixels ($4000–$57FF)
      │    Normal screen            │  Attributes ($5800–$5AFF)
      │    + IM2 handler, buffers   │  ~9 KB free for interrupt code
$8000 ├─────────────────────────────┤
      │    Bank 2 — FIXED           │  Main game code (~14 KB)
      │    Player, physics, AI      │  Tables, buffers (~2 KB)
      │    Sprites, entities, HUD   │  Stack grows down from $BFFF
$C000 ├─────────────────────────────┤
      │    Switchable bank (0–7)    │  Selected via port $7FFD
      │    ┌───────────────────┐    │
      │    │ Bank 0: Levels 1–2│    │  Compressed tilemaps + tileset
      │    │ Bank 1: Levels 3–5│    │  Boss data, enemy spawns
      │    │ Bank 3: Sprites   │    │  Pre-shifted ×4 (24+64 variants)
      │    │ Bank 4: Music A   │    │  PT3: title, levels 1–3
      │    │ Bank 6: Music B   │    │  PT3: levels 4–5, boss; SFX
      │    │ Bank 7: Shadow scr│    │  Double buffer / data storage
      │    └───────────────────┘    │
$FFFF └─────────────────────────────┘

  Key: Banks 2 and 5 are always visible (hardwired).
       Only $C000–$FFFF is switchable.
       Port $7FFD is write-only — always shadow its state!
```

Несколько замечаний об этой раскладке:

**Код размещён в банке 2 (фиксированном).** Поскольку банк 2 всегда отображён по адресам `$8000-$BFFF`, основной код игры всегда доступен. Тебе никогда не нужно подключать код -- только данные. Это исключает самый опасный класс ошибок с банками: вызов подпрограммы, которая была выгружена.

**Графика спрайтов в банке 3, отдельно от данных уровней в банках 0-1.** При рендеринге кадра рендереру нужна и графика тайлов (для скроллящегося фона), и графика спрайтов (для сущностей). Если бы и то, и другое было в одном переключаемом банке, пришлось бы переключаться туда-сюда в процессе рендеринга. Размещая их в разных банках, можно подключить данные тайлов, отрисовать фон, затем подключить данные спрайтов и отрисовать все сущности -- всего два переключения банков за кадр.

**Музыка разделена между банками 4 и 6.** Проигрыватель PT3 работает в обработчике прерываний IM2, который срабатывает раз за кадр. Обработчик прерываний должен подключить банк с музыкой, обновить регистры AY и переключить обратно на тот банк, который использовал основной цикл. Разделение музыки на два банка означает, что обработчик прерываний должен знать, в каком банке находится текущая композиция. Мы решаем это с помощью переменной:

```z80 id:ch21_ironclaw_bank_allocation_3
current_music_bank:
    db   4              ; bank 4 by default

im2_handler:
    push af
    push bc
    push de
    push hl
    push ix
    push iy              ; IY must be preserved -- BASIC uses it
                         ; for system variables, and PT3 players
                         ; typically use IY internally

    ; Save current bank state
    ld   a, (last_bank_state)
    push af

    ; Page in music bank
    ld   a, (current_music_bank)
    call switch_bank

    ; Update PT3 player -- writes AY registers
    call pt3_play

    ; Check for pending SFX
    call sfx_update

    ; Restore previous bank
    pop  af
    ld   (last_bank_state), a
    ld   bc, $7FFD
    out  (c), a

    pop  iy
    pop  ix
    pop  hl
    pop  de
    pop  bc
    pop  af
    ei
    reti
```

**Теневой экран в банке 7** доступен для двойной буферизации при обновлении скроллинга (как описано в Главе 17). Когда ты не ведёшь активную двойную буферизацию -- в меню, между уровнями, во время заставок -- банк 7 является 16 килобайтами свободного хранилища. Ironclaw использует его для хранения распакованной тайловой карты текущего уровня во время геймплея, освобождая переключаемые банки для графики и музыки.

### Стек

Стек располагается в верхней части адресного пространства банка 2, растёт вниз от `$BFFF`. При ~14 килобайтах кода, начинающегося с `$8000`, для стека остаётся примерно 2 килобайта -- более чем достаточно для нормальной глубины вызовов, но нужно быть бдительным. Глубокая рекурсия -- не вариант. Если ты используешь стековый вывод спрайтов (метод PUSH из Главы 16), помни, что ты заимствуешь указатель стека и должен сохранить и восстановить его с отключёнными прерываниями.

---

## 21.3 Конечный автомат

Игра -- это не одна программа. Это последовательность режимов -- титульный экран, меню, геймплей, пауза, конец игры, таблица рекордов -- каждый со своей обработкой ввода, своим рендерингом и своей логикой обновления. В Главе 18 мы представили паттерн конечного автомата. Вот как Ironclaw реализует его на верхнем уровне.

```z80 id:ch21_the_state_machine
; Game states
STATE_LOADER    equ  0
STATE_TITLE     equ  1
STATE_MENU      equ  2
STATE_GAMEPLAY  equ  3
STATE_PAUSE     equ  4
STATE_GAMEOVER  equ  5
STATE_HISCORE   equ  6
STATE_LEVELWIN  equ  7

; State handler table -- each entry is a 2-byte address
state_table:
    dw   state_loader       ; 0: loading screen + init
    dw   state_title        ; 1: title screen with animation
    dw   state_menu         ; 2: main menu (start, options, hiscores)
    dw   state_gameplay     ; 3: in-game
    dw   state_pause        ; 4: paused
    dw   state_gameover     ; 5: game over sequence
    dw   state_hiscore      ; 6: high score entry
    dw   state_levelwin     ; 7: level complete, advance

current_state:
    db   STATE_LOADER

; Main loop -- called once per frame after HALT
main_loop:
    halt                    ; wait for frame interrupt

    ; Dispatch to current state handler
    ld   a, (current_state)
    add  a, a              ; x2 for word index
    ld   l, a
    ld   h, 0
    ld   de, state_table
    add  hl, de
    ld   a, (hl)
    inc  hl
    ld   h, (hl)
    ld   l, a              ; HL = handler address
    jp   (hl)              ; jump to handler

; Each handler ends with:  jp main_loop
```

Каждый обработчик состояния полностью владеет кадром. Обработчик геймплея выполняет ввод, физику, ИИ, рендеринг и обновление интерфейса. Обработчик меню читает ввод и рисует меню. Обработчик паузы просто ждёт клавишу снятия паузы, отображая надпись «PAUSED».

Переходы между состояниями происходят записью нового значения в `current_state`. Переход из `STATE_GAMEPLAY` в `STATE_PAUSE` не требует очистки -- игровое состояние не затрагивается, и возврат в `STATE_GAMEPLAY` продолжает ровно с того места, где остановился. Но переход из `STATE_GAMEOVER` в `STATE_HISCORE` требует проверки, попадает ли счёт игрока в таблицу рекордов, а переход из `STATE_LEVELWIN` в `STATE_GAMEPLAY` требует загрузки и распаковки данных следующего уровня.

---

## 21.4 Кадр геймплея

Именно здесь происходит интеграция. В состоянии `STATE_GAMEPLAY` каждый кадр должен выполнить следующее, в указанном порядке:

```text
1. Read input                ~200 T-states
2. Update player physics     ~800 T-states
3. Update player state       ~400 T-states
4. Update enemies (AI+phys)  ~4,000 T-states (8 enemies)
5. Check collisions          ~2,000 T-states
6. Update projectiles        ~500 T-states
7. Scroll the viewport       ~8,000-15,000 T-states (depends on method)
8. Render background tiles   ~12,000 T-states (exposed column/row)
9. Erase old sprites         ~3,000 T-states (background restore)
10. Draw sprites             ~8,000 T-states (8 entities x ~1,000 each)
11. Update HUD               ~1,500 T-states
12. [Music plays in IM2]     ~3,000 T-states (interrupt handler)
                             ─────────────
                    Total:   ~43,400-50,400 T-states
```

На Pentagon с его 71 680 тактами на кадр остаётся 21 000-28 000 тактов запаса. Звучит комфортно, но это обманчиво. Эти оценки -- средние значения. Когда на экране четыре врага, а игрок прыгает через пропасть с летящими снарядами, худший случай может быть на 20-30% выше среднего. Твой запас -- это запас прочности.

Порядок имеет значение. Ввод должен быть первым -- тебе нужно намерение игрока до моделирования физики. Физика должна предшествовать обнаружению столкновений -- нужно знать, куда сущности хотят двигаться, прежде чем проверять, могут ли они. Реакция на столкновения должна предшествовать рендерингу -- нужны окончательные позиции, прежде чем что-то рисовать. А спрайты должны рисоваться после фона, потому что спрайты накладываются на тайлы.

### Чтение ввода

```z80 id:ch21_reading_input
; Read keyboard and Kempston joystick
; Returns result in A: bit 0=right, 1=left, 2=down, 3=up, 4=fire
read_input:
    ld   d, 0              ; accumulate result

    ; Kempston joystick (active high)
    in   a, ($1F)          ; Kempston port
    and  %00011111         ; mask 5 bits: fire, up, down, left, right
    ld   d, a

    ; Keyboard: QAOP + space (merge with joystick)
    ; Q = up
    ld   bc, $FBFE         ; half-row Q-T
    in   a, (c)
    bit  0, a              ; Q key
    jr   nz, .not_q
    set  3, d              ; up
.not_q:
    ; O = left
    ld   b, $DF            ; half-row Y-P
    in   a, (c)
    bit  1, a              ; O key
    jr   nz, .not_o
    set  1, d              ; left
.not_o:
    ; P = right
    bit  0, a              ; P key (same half-row)
    jr   nz, .not_p
    set  0, d              ; right
.not_p:
    ; A = down
    ld   b, $FD            ; half-row A-G
    in   a, (c)
    bit  0, a              ; A key
    jr   nz, .not_a
    set  2, d              ; down
.not_a:
    ; Space = fire
    ld   b, $7F            ; half-row space-B
    in   a, (c)
    bit  0, a              ; space
    jr   nz, .not_fire
    set  4, d              ; fire
.not_fire:

    ld   a, d
    ld   (input_state), a
    ret
```

Обрати внимание, что чтение клавиатуры использует `IN A,(C)` с адресом полуряда в B. Каждая клавиша соответствует биту в байте результата. Объединение клавиатуры и джойстика в один байт означает, что остальной логике игры безразлично, какое устройство ввода использует игрок.

### Движок скроллинга

Скроллинг -- самая дорогая операция в кадре. Глава 17 подробно рассматривала техники; здесь показано, как они интегрируются в игру.

Ironclaw использует метод **комбинированного скроллинга**: скроллинг с гранулярностью символа (скачки по 8 пикселей) для основного видового окна с пиксельным смещением (0-7) внутри текущего 8-пиксельного окна для плавного визуального перемещения. Когда пиксельное смещение достигает 8, видовое окно сдвигается на один столбец тайлов, а смещение сбрасывается в 0.

Видовое окно имеет ширину 30 символов (240 пикселей) и высоту 20 символов (160 пикселей), оставляя место для 2-символьного интерфейса сверху и снизу. Тайловая карта уровня обычно имеет ширину 256-512 тайлов и высоту 20 тайлов.

Когда видовое окно сдвигается на один столбец тайлов, рендерер должен:

1. Скопировать 29 столбцов текущего экрана на один символ влево (или вправо)
2. Нарисовать новый открывшийся столбец тайлов из тайловой карты

Копирование столбцов -- это цепочка LDIR: 20 рядов x 8 пиксельных строк x 29 байт = 4 640 байт по 21 такту каждый = 97 440 тактов. Это больше, чем целый кадр. Вот почему техника теневого экрана из Главы 17 критически важна.

```z80 id:ch21_the_scroll_engine
; Shadow screen double-buffer scroll
; Frame N: display screen is bank 5, draw screen is bank 7
; 1. Draw the shifted background into bank 7
; 2. Flip: set bit 3 of $7FFD to display bank 7
; Frame N+1: display screen is bank 7, draw screen is bank 5
; 3. Draw the shifted background into bank 5
; 4. Flip: clear bit 3 of $7FFD to display bank 5

flip_screen:
    ld   a, (last_bank_state)
    xor  %00001000          ; toggle screen bit (bit 3)
    ld   (last_bank_state), a
    ld   bc, $7FFD
    out  (c), a
    ret
```

Но даже с двойной буферизацией полное копирование столбцов обходится дорого. Ironclaw оптимизирует это, распределяя работу: во время плавного субтайлового скроллинга (пиксельное смещение 1-7) копирование столбцов не происходит -- меняется только смещение. Дорогое копирование столбцов происходит только на границах тайлов, примерно каждые 4-8 кадров в зависимости от скорости игрока. Между этими пиками рендеринг скроллинга практически бесплатен.

Когда граница тайла пересекается, копирование столбцов можно распределить на два кадра с помощью двойного буфера: кадр N рисует верхнюю половину сдвинутого экрана в задний буфер, кадр N+1 рисует нижнюю половину и переключает. Игрок видит бесшовный скроллинг, потому что переключение происходит только когда задний буфер полностью готов.

---

## 21.5 Интеграция спрайтов

Ironclaw использует спрайты OR+AND с маской (Глава 16, метод 2) для всех игровых сущностей. Это стандартная техника: для каждого пикселя спрайта выполняется AND с байтом маски для очистки фона, затем OR с данными спрайта для установки пикселей.

Каждый спрайт 16x16 имеет четыре предварительно сдвинутых копии (Глава 16, метод 3), по одной для каждого 2-пиксельного горизонтального выравнивания. Это превращает попиксельный сдвиг из операции времени выполнения в обращение к таблице подстановки. Цена: каждый кадр спрайта требует 4 варианта x 16 строк x 3 байта/строку (2 байта данных + 1 байт маски, расширенные до 3 байт для обработки переполнения сдвига) = 192 байта. Зато скорость рендеринга падает с ~1 500 тактов до ~1 000 тактов на спрайт, и при 8-10 спрайтах на экране эта экономия накапливается.

Предварительно сдвинутые данные спрайтов хранятся в банке 3. Во время фазы рендеринга спрайтов рендерер подключает банк 3, проходит по всем активным сущностям и рисует каждую:

```z80 id:ch21_sprite_integration
; Draw all active entities
; Assumes bank 3 (sprite graphics) is paged in at $C000
render_entities:
    ld   ix, entity_array
    ld   b, MAX_ENTITIES

.loop:
    push bc

    ; Check if entity is active
    ld   a, (ix + ENT_FLAGS)
    bit  FLAG_ACTIVE, a
    jr   z, .skip

    ; Calculate screen position from world position and viewport
    ld   l, (ix + ENT_X)
    ld   h, (ix + ENT_X + 1)
    ld   de, (viewport_x)
    or   a                 ; clear carry
    sbc  hl, de            ; screen_x = world_x - viewport_x
    ; Check if on screen (0-239)
    bit  7, h
    jr   nz, .skip         ; off-screen left (negative)
    ld   a, h
    or   a
    jr   nz, .skip         ; off-screen right (> 255)
    ld   a, l
    cp   240
    jr   nc, .skip         ; off-screen right (240-255)

    ; Store screen X for sprite routine
    ld   (sprite_screen_x), a

    ; Y position (already in screen coordinates for simplicity)
    ld   a, (ix + ENT_Y)
    ld   (sprite_screen_y), a

    ; Look up sprite graphic address from type + frame + shift
    call get_sprite_address ; returns HL = address in bank 3

    ; Draw masked sprite at (sprite_screen_x, sprite_screen_y)
    call draw_sprite_masked

.skip:
    pop  bc
    ld   de, ENT_SIZE
    add  ix, de            ; next entity
    djnz .loop
    ret
```

### Восстановление фона (грязные прямоугольники)

Перед рисованием спрайтов в новых позициях нужно стереть их из старых позиций. Ironclaw использует метод грязных прямоугольников из Главы 16: перед рисованием спрайта сохраняем фон под ним в буфер. Перед проходом рендеринга спрайтов следующего кадра восстанавливаем эти сохранённые фоны.

```z80 id:ch21_background_restore_dirty
; Dirty rectangle entry: 4 bytes
;   byte 0: screen address low
;   byte 1: screen address high
;   byte 2: width in bytes
;   byte 3: height in pixel lines

; Save background before drawing sprite
save_background:
    ; HL = screen address, B = height, C = width
    ld   de, bg_save_buffer
    ld   (bg_save_ptr), de
    ; ... copy rectangle from screen to buffer ...
    ret

; Restore all saved backgrounds (called before new sprite render pass)
restore_backgrounds:
    ld   hl, dirty_rect_list
    ld   b, (hl)           ; count of dirty rectangles
    inc  hl
    or   a
    ret  z                 ; no sprites last frame

.loop:
    push bc
    ; Read rectangle descriptor
    ld   e, (hl)
    inc  hl
    ld   d, (hl)           ; DE = screen address
    inc  hl
    ld   b, (hl)           ; B = height
    inc  hl
    ld   c, (hl)           ; C = width
    inc  hl
    push hl

    ; Copy saved background back to screen
    ; ... copy from bg_save_buffer to screen ...

    pop  hl
    pop  bc
    djnz .loop
    ret
```

Стоимость грязных прямоугольников пропорциональна количеству и размеру спрайтов. Для 8 сущностей размером 16x16 пикселей (3 байта в ширину после сдвига) сохранение и восстановление стоит примерно 8 x 16 x 3 x 2 (сохранение + восстановление) x ~10 тактов/байт = ~7 680 тактов. Недёшево, но предсказуемо.

---

## 21.6 Столкновения, физика и ИИ в контексте

Главы 18 и 19 рассматривали эти системы изолированно. В интегрированной игре ключевая задача -- порядок: какая система запускается первой и какие данные каждой из них нужны от остальных?

### Цикл физика-столкновения

Обновление физики должно чередоваться с обнаружением столкновений. Паттерн такой:

```text
1. Apply gravity:  velocity_y += GRAVITY
2. Apply input:    if (input_right) velocity_x += ACCEL
3. Horizontal move:
     a. new_x = x + velocity_x
     b. Check tile collisions at (new_x, y)
     c. If blocked: push back to tile boundary, velocity_x = 0
     d. Else: x = new_x
4. Vertical move:
     a. new_y = y + velocity_y
     b. Check tile collisions at (x, new_y)
     c. If blocked: push back, velocity_y = 0, set on_ground flag
     d. Else: y = new_y, clear on_ground flag
5. If (on_ground AND input_jump): velocity_y = -JUMP_FORCE
```

Горизонтальное и вертикальное перемещения разделены, потому что реакция на столкновение должна обрабатывать каждую ось независимо. Если ты двигаешься по диагонали и попадаешь в угол, нужно скользить вдоль стены по одной оси, останавливаясь по другой. Одновременная проверка обеих осей приводит к багам «залипания», когда игрок застревает на углах.

Все позиции используют формат с фиксированной точкой 8.8 (Глава 4): старший байт -- пиксельная координата, младший -- дробная часть. Значения скоростей тоже 8.8. Это даёт субпиксельную точность движения без какого-либо умножения в ядре физического цикла -- сложения и сдвигов достаточно.

```z80 id:ch21_physics_collision_loop_2
; Apply gravity to entity at IX
; velocity_y is 16-bit signed, 8.8 fixed-point
apply_gravity:
    ld   l, (ix + ENT_VY)
    ld   h, (ix + ENT_VY + 1)
    ld   de, GRAVITY       ; e.g., $0040 = 0.25 pixels/frame/frame
    add  hl, de
    ; Clamp to terminal velocity
    ld   a, h
    cp   MAX_FALL_SPEED    ; e.g., 4 pixels/frame
    jr   c, .no_clamp
    ld   hl, MAX_FALL_SPEED * 256
.no_clamp:
    ld   (ix + ENT_VY), l
    ld   (ix + ENT_VY + 1), h
    ret
```

### Столкновение с тайлами

Проверка столкновения с тайлом преобразует пиксельную координату в индекс тайла, а затем ищет тип тайла в карте столкновений уровня:

```z80 id:ch21_tile_collision
; Check tile at pixel position (B=x, C=y)
; Returns: A = tile type (0=empty, 1=solid, 2=hazard, 3=platform)
check_tile:
    ; Convert pixel X to tile column: x / 8
    ld   a, b
    srl  a
    srl  a
    srl  a                 ; A = column (0-31)
    ld   l, a

    ; Convert pixel Y to tile row: y / 8
    ld   a, c
    srl  a
    srl  a
    srl  a                 ; A = row (0-23)

    ; Tile index = row * level_width + column
    ld   h, 0
    ld   d, h
    ld   e, a
    ; Multiply row by level_width (e.g., 256 = trivial: just use E as high byte)
    ; For level_width = 256: address = level_map + row * 256 + column
    ld   d, e              ; D = row = high byte of offset
    ld   e, l              ; E = column = low byte of offset
    ld   hl, level_collision_map
    add  hl, de
    ld   a, (hl)           ; A = tile type
    ret
```

В Ironclaw ширина уровней установлена в 256 тайлов. Это не совпадение -- это делает умножение на ширину ряда тривиальным (номер ряда становится старшим байтом смещения). Уровень шириной 256 тайлов по 8 пикселей на тайл -- это 2 048 пикселей, примерно 8,5 экранов в ширину. Для более длинных уровней можно использовать ширину 512 тайлов (умножение ряда на 2 через `SLA E : RL D`), хотя это стоит несколько дополнительных тактов на каждое обращение.

### ИИ врагов

Каждый тип врага имеет конечный автомат (Глава 19). Состояние хранится в структуре сущности:

```z80 id:ch21_enemy_ai
; Entity structure (16 bytes per entity)
ENT_X       equ  0    ; 16-bit, 8.8 fixed-point
ENT_Y       equ  2    ; 16-bit, 8.8 fixed-point
ENT_VX      equ  4    ; 16-bit, 8.8 fixed-point
ENT_VY      equ  6    ; 16-bit, 8.8 fixed-point
ENT_TYPE    equ  8    ; entity type (player, walker, flyer, shooter, boss)
ENT_STATE   equ  9    ; FSM state (idle, patrol, chase, attack, retreat, dying)
ENT_ANIM    equ  10   ; animation frame counter
ENT_HEALTH  equ  11   ; hit points
ENT_FLAGS   equ  12   ; bit flags: active, on_ground, facing_left, invuln, ...
ENT_TIMER   equ  13   ; general-purpose timer (attack cooldown, etc.)
ENT_AUX1    equ  14   ; type-specific data (patrol point, projectile type, etc.)
ENT_AUX2    equ  15   ; type-specific data
ENT_SIZE    equ  16

MAX_ENTITIES equ 16   ; player + 8 enemies + 7 projectiles
```

Четыре типа врагов Ironclaw:

1. **Walker** -- Патрулирует между двумя точками. Когда игрок оказывается в пределах 64 пикселей по горизонтали, переключается в состояние преследования (идёт к игроку). Переключается в атаку (контактный урон) при столкновении. Возвращается к патрулированию, когда игрок удаляется или враг достигает края платформы.

2. **Flyer** -- Синусоидальное вертикальное движение (с использованием таблицы синусов из Главы 4). Игнорирует столкновения с тайлами. Преследует игрока по горизонтали, когда тот в зоне досягаемости. Сбрасывает снаряды через интервалы.

3. **Shooter** -- Стационарный. Стреляет горизонтальным снарядом каждые N кадров, когда игрок находится в прямой видимости (тот же ряд тайлов, между ними нет сплошных тайлов). Снаряд -- это отдельная сущность, выделяемая из пула сущностей.

4. **Boss** -- Многофазный конечный автомат. Фаза 1: патрулирование платформы, стрельба веером. Фаза 2 (ниже 50% здоровья): ускоренное движение, прицельная стрельба, вызов Walker. Фаза 3 (ниже 25% здоровья): ярость, непрерывный огонь, тряска экрана.

Ключевая оптимизация из Главы 19: ИИ не запускается каждый кадр. Обновления ИИ врагов распределяются по кадрам с помощью простого циклического перебора:

```z80 id:ch21_enemy_ai_2
; Update AI for subset of enemies each frame
; ai_frame_counter cycles 0, 1, 2, 0, 1, 2, ...
update_enemy_ai:
    ld   a, (ai_frame_counter)
    inc  a
    cp   3
    jr   c, .no_wrap
    xor  a
.no_wrap:
    ld   (ai_frame_counter), a

    ; Only update enemies where (entity_index % 3) == ai_frame_counter
    ld   ix, entity_array + ENT_SIZE  ; skip player (index 0)
    ld   b, MAX_ENTITIES - 1
    ld   c, 0              ; entity index counter

.loop:
    push bc
    ld   a, (ix + ENT_FLAGS)
    bit  FLAG_ACTIVE, a
    jr   z, .next

    ; Check if this entity's turn
    ld   a, c
    ld   e, 3
    call mod_a_e           ; A = entity_index % 3
    ld   b, a
    ld   a, (ai_frame_counter)
    cp   b
    jr   nz, .next

    ; Run AI for this entity
    call run_entity_ai     ; dispatch based on ENT_TYPE and ENT_STATE

.next:
    pop  bc
    inc  c
    ld   de, ENT_SIZE
    add  ix, de
    djnz .loop
    ret
```

Это означает, что ИИ каждого врага запускается раз в 3 кадра. При 50 fps это всё ещё ~17 обновлений ИИ в секунду на врага -- более чем достаточно для отзывчивого поведения. Экономия существенна: если ИИ стоит ~500 тактов на врага, запуск всех 8 врагов каждый кадр обходится в 4 000 тактов. Запуск 2-3 врагов за кадр -- 1 000-1 500 тактов. Физика и обнаружение столкновений по-прежнему работают каждый кадр для плавного движения.

---

## 21.7 Интеграция звука

### Музыка

Проигрыватель PT3 работает внутри обработчика прерываний IM2, как показано в разделе 21.2. Проигрыватель занимает примерно 1,5-2 килобайта кода и выполняется раз за кадр, потребляя ~2 500-3 500 тактов в зависимости от сложности текущего ряда паттерна.

Каждый уровень имеет свой музыкальный трек. При переходе между уровнями игра:

1. Затухает текущий трек (плавное уменьшение громкости AY до 0 за 25 кадров)
2. Подключает нужный банк с музыкой (банк 4 или 6)
3. Инициализирует проигрыватель PT3 начальным адресом новой композиции
4. Плавно вводит звук

Формат данных PT3 компактен -- типичный 2-3-минутный игровой музыкальный цикл сжимается до 2-4 килобайт с Pletter, поэтому два банка для музыки (4 и 6) вмещают все шесть треков (титульный, пять уровней, босс, конец игры).

### Звуковые эффекты

Звуковые эффекты используют систему захвата каналов на основе приоритетов из Главы 11. Когда срабатывает звуковой эффект (прыжок игрока, гибель врага, выстрел снаряда), движок SFX временно захватывает один канал AY, подменяя то, что музыка делала на этом канале. Когда эффект заканчивается, канал возвращается под управление музыки.

```z80 id:ch21_sound_effects
; SFX priority levels
SFX_JUMP       equ  1     ; low priority
SFX_PICKUP     equ  2
SFX_SHOOT      equ  3
SFX_HIT        equ  4
SFX_EXPLODE    equ  5     ; high priority
SFX_BOSS_DIE   equ  6     ; highest priority

; Trigger a sound effect
; A = SFX id
play_sfx:
    ; Check priority -- only play if higher than current SFX
    ld   hl, current_sfx_priority
    cp   (hl)
    ret  c                 ; current SFX has higher priority, ignore

    ; Set up SFX playback
    ld   (hl), a           ; update priority
    ; Look up SFX descriptor table
    add  a, a              ; x2 for word index
    ld   l, a
    ld   h, 0
    ld   de, sfx_table
    add  hl, de
    ld   a, (hl)
    inc  hl
    ld   h, (hl)
    ld   l, a              ; HL = SFX descriptor address

    ; SFX descriptor: duration (byte), channel (byte),
    ;                 then per-frame: freq_lo, freq_hi, volume, noise
    ld   a, (hl)
    ld   (sfx_frames_left), a
    inc  hl
    ld   a, (hl)
    ld   (sfx_channel), a
    inc  hl
    ld   (sfx_data_ptr), hl
    ret
```

Обновление SFX выполняется внутри обработчика прерываний, после проигрывателя PT3. Если SFX активен, он перезаписывает значения регистров AY, которые проигрыватель PT3 только что установил для захваченного канала. Это означает, что музыка продолжает корректно играть на двух других каналах, а захваченный канал воспроизводит звуковой эффект.

Определения SFX -- это процедурные таблицы, а не сэмплы. Каждая запись -- последовательность покадровых значений регистров:

```z80 id:ch21_sound_effects_2
; SFX: player jump -- ascending frequency sweep on channel C
sfx_jump_data:
    db   8                 ; duration: 8 frames
    db   2                 ; channel C (0=A, 1=B, 2=C)
    ; Per-frame: freq_lo, freq_hi, volume
    db   $80, $01, 15      ; frame 1: low pitch, full volume
    db   $60, $01, 14      ; frame 2: slightly higher
    db   $40, $01, 13
    db   $20, $01, 12
    db   $00, $01, 10
    db   $E0, $00, 8
    db   $C0, $00, 5
    db   $A0, $00, 2       ; frame 8: high pitch, fading out
```

Такой подход потребляет пренебрежимо мало памяти (8-20 байт на эффект) и пренебрежимо мало процессорного времени (несколько десятков тактов за кадр на запись 3-4 значений регистров AY).

---

## 21.8 Загрузка: лента и DivMMC

Игра для ZX Spectrum должна как-то загружаться. В 1980-х это означало ленту. Сегодня у большинства пользователей есть DivMMC (или аналог) с SD-картой под управлением esxDOS. Ironclaw поддерживает оба варианта.

### Файл .tap и загрузчик на BASIC

Формат файла `.tap` -- это последовательность блоков данных, каждый из которых предваряется 2-байтной длиной и флаговым байтом. Программа-загрузчик на BASIC (сама являющаяся блоком в .tap) использует команды `LOAD "" CODE` для загрузки каждого блока по нужному адресу.

Структура .tap файла Ironclaw:

```text
Block 0:  BASIC loader program (autorun line 10)
Block 1:  Loading screen (6912 bytes -> $4000)
Block 2:  Main code block (bank 2 content -> $8000)
Block 3:  Bank 0 data (level data + tiles, compressed)
Block 4:  Bank 1 data (more level data)
Block 5:  Bank 3 data (sprite graphics)
Block 6:  Bank 4 data (music tracks 1-3)
Block 7:  Bank 6 data (music tracks 4-6, SFX)
```

Загрузчик на BASIC:

```basic
10 CLEAR 32767
20 LOAD "" SCREEN$
30 LOAD "" CODE
40 BORDER 0: PAPER 0: INK 0: CLS
50 RANDOMIZE USR 32768
```

Строка 10 устанавливает RAMTOP ниже `$8000`, защищая наш код от стека BASIC. Строка 20 загружает экран загрузки непосредственно в экранную память (команда `LOAD "" SCREEN$` Spectrum делает это автоматически). Строка 30 загружает основной блок кода. Строка 40 очищает экран. Строка 50 прыгает на наш код по адресу `$8000`.

Но это загружает только основной блок кода. Банковые данные (блоки 3-7) должны загружаться нашим собственным Z80-кодом, который подключает каждый банк и использует подпрограмму загрузки с ленты из ПЗУ:

```z80 id:ch21_the_tap_file_and_basic_loader_3
; Load bank data from tape
; Called after main code is running
load_bank_data:
    ; Bank 0
    ld   a, 0
    call switch_bank
    ld   ix, $C000         ; load address
    ld   de, BANK0_SIZE    ; data length
    call load_tape_block

    ; Bank 1
    ld   a, 1
    call switch_bank
    ld   ix, $C000
    ld   de, BANK1_SIZE
    call load_tape_block

    ; ... repeat for banks 3, 4, 6 ...
    ret

; Load one tape block using ROM routine
; IX = address, DE = length
load_tape_block:
    ld   a, $FF            ; data block flag (not header)
    scf                    ; carry set = LOAD (not VERIFY)
    call $0556             ; ROM tape loading routine
    ret  nc                ; carry clear = load error
    ret
```

### Загрузка через esxDOS (DivMMC)

Для пользователей с DivMMC или аналогичным оборудованием загрузка с SD-карты драматически быстрее и надёжнее. API esxDOS предоставляет файловые операции через `RST $08` с последующим номером функции:

```z80 id:ch21_esxdos_loading_divmmc
; esxDOS function codes
F_OPEN      equ  $9A
F_CLOSE     equ  $9B
F_READ      equ  $9D
F_WRITE     equ  $9E
F_SEEK      equ  $9F
F_OPENDIR   equ  $A3
F_READDIR   equ  $A4

; esxDOS open modes
FA_READ     equ  $01
FA_WRITE    equ  $06
FA_CREATE   equ  $0E

; Open a file
; IX = pointer to null-terminated filename
; Returns: A = file handle (or carry set on error)
esx_open:
    ld   a, '*'            ; use default drive
    ld   b, FA_READ        ; open for reading
    rst  $08
    db   F_OPEN
    ret

; Read bytes from file
; A = file handle, IX = destination address, BC = byte count
; Returns: BC = bytes actually read (or carry set on error)
esx_read:
    rst  $08
    db   F_READ
    ret

; Close a file
; A = file handle
esx_close:
    rst  $08
    db   F_CLOSE
    ret
```

Ironclaw определяет наличие esxDOS при запуске, проверяя сигнатуру DivMMC. При наличии загружает все данные из файлов на SD-карте вместо ленты:

```z80 id:ch21_esxdos_loading_divmmc_2
; Load game data from esxDOS
; All bank data stored in separate files on SD card
load_from_esxdos:
    ; Load bank 0: levels + tiles
    ld   a, 0
    call switch_bank
    ld   ix, filename_bank0
    call esx_open
    ret  c                 ; error -- fall back to tape
    push af                ; save file handle
    ld   ix, $C000
    ld   bc, BANK0_SIZE
    pop  af                ; A = file handle (esxDOS preserves this)
    push af
    call esx_read
    pop  af
    call esx_close

    ; Repeat for other banks...
    ; Bank 1
    ld   a, 1
    call switch_bank
    ld   ix, filename_bank1
    call esx_open
    ret  c
    ; ... (same pattern) ...

    ret

filename_bank0:  db "IRONCLAW.B0", 0
filename_bank1:  db "IRONCLAW.B1", 0
filename_bank3:  db "IRONCLAW.B3", 0
filename_bank4:  db "IRONCLAW.B4", 0
filename_bank6:  db "IRONCLAW.B6", 0
```

Код обнаружения:

```z80 id:ch21_esxdos_loading_divmmc_3
; Detect esxDOS presence
; Sets carry if esxDOS is NOT available
detect_esxdos:
    ; Try to open a nonexistent file -- if RST $08 returns
    ; without crashing, esxDOS is present
    ld   a, '*'
    ld   b, FA_READ
    ld   ix, test_filename
    rst  $08
    db   F_OPEN
    jr   c, .not_present   ; carry set = open failed, but esxDOS handled it
    ; File actually opened -- close it and return success
    call esx_close
    or   a                 ; clear carry
    ret
.not_present:
    ; esxDOS returned an error -- it IS present, just file not found
    ; Distinguish from "RST $08 went to ROM and crashed"
    ; by checking if we're still running. If we're here, esxDOS is present.
    or   a                 ; clear carry = esxDOS present
    ret

test_filename:  db "IRONCLAW.B0", 0
```

На практике самый надёжный метод обнаружения проверяет идентификационный байт DivMMC по известному адресу ловушки или использует заведомо безопасный вызов RST $08. Метод выше работает, потому что если esxDOS отсутствует, `RST $08` прыгает на обработчик ошибок ПЗУ, который для 128K ПЗУ по адресу `$0008` представляет собой безобидный возврат с очищенным флагом переноса. В продакшн-коде следует использовать более надёжную проверку; приведённый паттерн иллюстрирует концепцию.

---

## 21.9 Экран загрузки, меню и таблица рекордов

### Экран загрузки

Экран загрузки -- первое впечатление игрока. Он загружается командой `LOAD "" SCREEN$` в BASIC-загрузчике, что означает, что он появляется, пока оставшиеся блоки данных грузятся с ленты. При загрузке через esxDOS она настолько быстра, что стоит отображать экран минимальное время:

```z80 id:ch21_loading_screen
show_loading_screen:
    ; Loading screen is already in screen memory ($4000) from BASIC loader
    ; If loading from esxDOS, load it explicitly:
    ld   ix, filename_screen
    call esx_open
    ret  c
    push af
    ld   ix, $4000
    ld   bc, 6912
    pop  af
    push af
    call esx_read
    pop  af
    call esx_close

    ; Minimum display time: 100 frames (2 seconds)
    ld   b, 100
.wait:
    halt
    djnz .wait
    ret

filename_screen: db "IRONCLAW.SCR", 0
```

Экран загрузки -- это стандартный файл экрана Spectrum: 6 144 байта пиксельных данных, за ними 768 байт атрибутов, итого 6 912 байт. Создай его в любом Spectrum-совместимом графическом редакторе (ZX Paintbrush, SEViewer или Multipaint) или конвертируй современное изображение инструментом дизеринга.

### Титульный экран и меню

Состояние титульного экрана отображает логотип игры и анимированный фон, затем переходит в меню при любом нажатии клавиши:

```z80 id:ch21_title_screen_and_menu
state_title:
    ; Animate background (e.g., scrolling starfield, colour cycling)
    call title_animate

    ; Check for keypress
    xor  a
    in   a, ($FE)          ; read all keyboard half-rows at once
    cpl                    ; invert (keys are active low)
    and  $1F               ; mask 5 key bits
    jr   z, .no_key
    ld   a, STATE_MENU
    ld   (current_state), a
.no_key:
    jp   main_loop
```

Меню предлагает три пункта: Начать игру, Настройки, Таблица рекордов. Навигация -- клавишами вверх/вниз, выбор -- огнём/Enter. Меню -- это простой конечный автомат внутри обработчика `STATE_MENU`:

```z80 id:ch21_title_screen_and_menu_2
menu_selection:
    db   0                 ; 0=Start, 1=Options, 2=HiScores

state_menu:
    ; Draw menu (only redraw on selection change)
    call draw_menu

    ; Read input
    call read_input
    ld   a, (input_state)

    ; Up
    bit  3, a
    jr   z, .not_up
    ld   a, (menu_selection)
    or   a
    jr   z, .not_up
    dec  a
    ld   (menu_selection), a
    call play_menu_beep
.not_up:

    ; Down
    ld   a, (input_state)
    bit  2, a
    jr   z, .not_down
    ld   a, (menu_selection)
    cp   2
    jr   z, .not_down
    inc  a
    ld   (menu_selection), a
    call play_menu_beep
.not_down:

    ; Fire / Enter
    ld   a, (input_state)
    bit  4, a
    jr   z, .no_fire
    ld   a, (menu_selection)
    or   a
    jr   nz, .not_start
    ; Start game
    call init_game
    ld   a, STATE_GAMEPLAY
    ld   (current_state), a
    jp   main_loop
.not_start:
    cp   1
    jr   nz, .not_options
    ; Options (toggle sound, controls, etc.)
    call show_options
    jp   main_loop
.not_options:
    ; High scores
    ld   a, STATE_HISCORE
    ld   (current_state), a
    jp   main_loop

.no_fire:
    jp   main_loop
```

### Таблица рекордов

Таблица рекордов хранится в виде 10 записей в области данных банка 2:

```z80 id:ch21_high_scores
; High score entry: 3 bytes name + 3 bytes BCD score = 6 bytes
; 10 entries = 60 bytes
HISCORE_COUNT equ 10
HISCORE_SIZE  equ 6

hiscore_table:
    ; Pre-filled defaults
    db   "ACE"
    db   $00, $50, $00     ; 005000 BCD
    db   "BOB"
    db   $00, $40, $00     ; 004000
    db   "CAT"
    db   $00, $30, $00     ; 003000
    ; ... 7 more entries ...
    ds   7 * HISCORE_SIZE, 0
```

Очки используют BCD (двоично-десятичный код) -- две десятичные цифры на байт, три байта на счёт, что даёт максимум 999 999 очков. BCD предпочтительнее двоичного формата для отображения, потому что преобразование 24-битного двоичного числа в десятичное на Z80 требует дорогого деления. С BCD инструкция `DAA` автоматически обрабатывает перенос между цифрами, а для печати достаточно маскировать полубайты:

```z80 id:ch21_high_scores_2
; Add points to score
; DE = points to add (BCD, 2 bytes, max 9999)
add_score:
    ld   hl, player_score
    ld   a, (hl)
    add  a, e
    daa                    ; adjust for BCD
    ld   (hl), a
    inc  hl
    ld   a, (hl)
    adc  a, d
    daa
    ld   (hl), a
    inc  hl
    ld   a, (hl)
    adc  a, 0
    daa
    ld   (hl), a
    ret

player_score:
    db   0, 0, 0           ; 3 bytes BCD, little-endian
```

Когда игра заканчивается, код просматривает таблицу рекордов, чтобы определить, попадает ли счёт игрока в неё. Если да, игра переходит в `STATE_HISCORE` для ввода имени (три символа, выбираемых клавишами вверх/вниз/огонь).

На системах с esxDOS таблица рекордов может сохраняться на SD-карту. На системах с лентой рекорды сохраняются только на время текущей сессии.

---

## 21.10 Загрузка уровней и распаковка

Когда игрок начинает уровень или завершает его, игра должна:

1. Подключить банк, содержащий данные уровня (банк 0 для уровней 1-2, банк 1 для уровней 3-5)
2. Распаковать тайловую карту в банк 7 (банк теневого экрана, перепрофилированный в буфер данных при переходах между уровнями)
3. Распаковать графику тайлов в буфер в банке 2 или банке 0
4. Инициализировать массив сущностей из таблицы спавна уровня
5. Сбросить видовое окно на начальную позицию уровня
6. Сбросить состояние движка скроллинга

```z80 id:ch21_level_loading_and
; Load and initialise level
; A = level number (0-4)
load_level:
    push af

    ; Determine which bank holds this level
    cp   2
    jr   nc, .bank1
    ; Levels 0-1: bank 0
    ld   a, 0
    call switch_bank
    pop  af
    push af
    ; Look up compressed data address
    add  a, a
    ld   l, a
    ld   h, 0
    ld   de, level_ptrs_bank0
    add  hl, de
    jr   .decompress
.bank1:
    ; Levels 2-4: bank 1
    ld   a, 1
    call switch_bank
    pop  af
    push af
    sub  2                 ; offset within bank 1
    add  a, a
    ld   l, a
    ld   h, 0
    ld   de, level_ptrs_bank1
    add  hl, de

.decompress:
    ; HL points to 2-byte address of compressed level data in current bank
    ld   a, (hl)
    inc  hl
    ld   h, (hl)
    ld   l, a              ; HL = compressed data source (in $C000-$FFFF)

    ; Decompress tilemap into bank 7
    ; First, save current bank and switch to bank 7
    ; BUT: bank 7 is at $4000 (shadow screen), not $C000
    ; We decompress to $C000 in a temporary bank, then copy
    ; OR: decompress directly into shadow screen at $4000

    ; Simpler approach: decompress into a buffer at $8000+ area
    ; (we have ~2KB free above our code in bank 2)
    ; For large levels, use bank 7 at $4000:
    ; Enable shadow screen banking, then write to $4000-$7FFF

    ld   de, level_buffer  ; destination in bank 2 work area
    call zx0_decompress    ; ZX0 decompressor: HL=src, DE=dest

    ; Initialise entities from spawn table
    pop  af                ; A = level number
    call init_level_entities

    ; Set viewport to level start
    ld   hl, 0
    ld   (viewport_x), hl
    ld   hl, 0
    ld   (viewport_y), hl

    ; Reset scroll state
    xor  a
    ld   (scroll_pixel_offset), a
    ld   (scroll_dirty), a

    ret
```

Выбор упаковщика здесь важен. Данные уровня загружаются один раз за уровень (во время экрана перехода), поэтому скорость распаковки не критична -- мы можем позволить себе ~250 тактов на байт у Exomizer ради лучшей степени сжатия. Но графика тайлов может нуждаться в распаковке во время геймплея (если тайлы хранятся в банках), поэтому предпочтительны ~69 тактов на байт у Pletter.

Как обсуждалось в Главе 14, код распаковщика сам занимает память. ZX0 с ~70 байтами идеален для проектов с дефицитом пространства для кода. Ironclaw включает и распаковщик ZX0 (для данных уровней при загрузке), и распаковщик Pletter (для потоковых данных тайлов во время геймплея).

---

## 21.11 Профилирование с DeZog

Ты написал весь код. Он компилируется. Он работает. Игрок ходит, враги патрулируют, тайлы скроллятся, музыка играет. Но бюджет кадра переполняется на уровне 3, где одновременно на экране шесть врагов и три снаряда. Полоска бордюра показывает красную полосу, выходящую за пределы видимой области экрана. Ты теряешь кадры.

Вот тут DeZog зарабатывает своё место в твоём инструментарии.

### Что такое DeZog?

DeZog -- это расширение VS Code, предоставляющее полноценную среду отладки для Z80-программ. Он подключается к эмуляторам (ZEsarUX, CSpect или собственному встроенному симулятору) и даёт тебе:

- Точки останова (по адресу, условные, логпоинты)
- Пошаговое выполнение (вход, перешагивание, выход)
- Наблюдение за регистрами (все регистры Z80, обновляемые в реальном времени)
- Просмотр памяти (hex-дамп с живым обновлением)
- Представление дизассемблера
- Стек вызовов
- **Счётчик тактов** -- инструмент профилирования, который нам нужен

### Рабочий процесс профилирования

Полоска бордюра говорит, *что* ты выходишь за бюджет. DeZog говорит, *где*.

**Шаг 1: Изолируй медленный кадр.** Установи условную точку останова в начале основного цикла, которая срабатывает только при установленном флаге «переполнение кадра». Добавь код, устанавливающий этот флаг, когда кадр занимает слишком много:

```z80 id:ch21_the_profiling_workflow
; At the end of the gameplay frame, before HALT:
    ; Check if we're still in the current frame
    ; (a simple approach: read the raster line via floating bus
    ;  or use a frame counter incremented by IM2)
    ld   a, (frame_overflow_flag)
    or   a
    jr   z, .ok
    ; Frame overflowed -- set debug breakpoint trigger
    nop                    ; <-- set DeZog breakpoint here
.ok:
```

**Шаг 2: Измерь стоимость подсистем.** Счётчик тактов DeZog позволяет измерить точную стоимость любого участка кода. Помести курсор в начало `update_enemy_ai`, запиши значение счётчика тактов, перешагни через вызов и запиши новое значение. Разница -- это точная стоимость.

Систематический проход профилирования измеряет каждую подсистему:

```text
Subsystem            Measured T-states   Budget %
─────────────────────────────────────────────────
read_input                    187          0.3%
update_player_physics         743          1.0%
update_player_state           412          0.6%
update_enemy_ai             4,231          5.9%   <-- worst case
check_all_collisions        2,847          4.0%
update_projectiles            523          0.7%
scroll_viewport            12,456         17.4%   <-- expensive
render_exposed_tiles       11,892         16.6%   <-- expensive
restore_backgrounds         3,214          4.5%
draw_sprites               10,156         14.2%   <-- expensive
update_hud                  1,389          1.9%
[IM2 music interrupt]       3,102          4.3%
─────────────────────────────────────────────────
TOTAL                      51,152         71.4%
Slack                      20,528         28.6%
```

Это средний случай. Теперь профилируй худший случай -- уровень 3, шесть врагов на экране, игрок возле правого края, вызывающий скроллинг:

```text
Subsystem            Measured T-states   Budget %
─────────────────────────────────────────────────
read_input                    187          0.3%
update_player_physics         743          1.0%
update_player_state           412          0.6%
update_enemy_ai             5,891          8.2%   <-- 6 enemies active
check_all_collisions        4,156          5.8%   <-- more pairs
update_projectiles          1,247          1.7%   <-- 3 projectiles
scroll_viewport            14,892         20.8%   <-- scroll + new column
render_exposed_tiles       14,456         20.2%   <-- full column render
restore_backgrounds         4,821          6.7%
draw_sprites               13,892         19.4%   <-- 10 entities
update_hud                  1,389          1.9%
[IM2 music interrupt]       3,102          4.3%
─────────────────────────────────────────────────
TOTAL                      65,188         90.9%
Slack                       6,492          9.1%
```

Всего 9% запаса в худшем случае. Это опасно мало. Ещё один враг или сложный музыкальный паттерн могут вывести за рамки.

**Шаг 3: Найди узкое место.** Таблица профилирования делает очевидным: скроллинг + рендеринг тайлов потребляют 41% кадра в худшем случае. Рендеринг спрайтов забирает 19%. ИИ врагов -- 8%.

**Шаг 4: Оптимизируй узкое место.** Варианты, примерно в порядке влияния:

1. **Распредели стоимость скроллинга.** Вместо рендеринга полного нового столбца за один кадр рисуй половину в кадре N и половину в кадре N+1 с помощью двойного буфера (обсуждалось в разделе 21.4). Это снижает пик скроллинга с ~29 000 до ~15 000 тактов за кадр.

2. **Используй скомпилированные спрайты для игрока.** Спрайт игрока всегда на экране и всегда рисуется. Переход от OR+AND с маской (Глава 16, метод 2) к скомпилированным спрайтам (метод 5) экономит ~30% на каждую отрисовку спрайта, но увеличивает расход памяти. Для одной часто рисуемой сущности этот компромисс оправдан.

3. **Уменьши перерисовку спрайтов.** Если два врага перекрываются, ты рисуешь пиксели, которые будут перезаписаны. Сортируй сущности по Y-координате (от дальних к ближним) и пропускай отрисовку полностью закрытых спрайтов. Это помогает в худшем случае, когда сущности группируются.

4. **Подтяни ИИ.** Профилируй `run_entity_ai` для каждого типа врага. Проверка прямой видимости Shooter (сканирование столбцов тайлов на предмет загораживания) часто оказывается самой дорогой операцией ИИ. Кэшируй результат: перепроверяй прямую видимость каждые 8 кадров вместо каждых 3.

После оптимизации худший случай падает до ~58 000 тактов, оставляя 19% запаса. Это комфортно.

### Конфигурация DeZog для Ironclaw

DeZog подключается к эмулятору, поддерживающему его протокол отладки. Для разработки под ZX Spectrum 128K рекомендуется ZEsarUX:

```json
// .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "type": "dezog",
            "request": "launch",
            "name": "Ironclaw (ZEsarUX)",
            "remoteType": "zesarux",
            "zesarux": {
                "hostname": "localhost",
                "port": 10000
            },
            "sjasmplus": [
                {
                    "path": "src/main.a80"
                }
            ],
            "topOfStack": "0xBFFF",
            "load": "build/ironclaw.sna",
            "startAutomatically": true,
            "history": {
                "reverseDebugInstructionCount": 100000
            }
        }
    ]
}
```

Параметр `history` включает обратную отладку -- ты можешь шагать назад, чтобы увидеть, как ты пришёл к ошибке. Это неоценимо для отслеживания глюков столкновений, когда сущность телепортировалась сквозь стену три кадра назад.

---

## 21.12 Конвейер данных в деталях

Перенос данных из инструментов художника в игру -- зачастую самая недооценённая часть проекта. Конвейер Ironclaw конвертирует четыре вида ассетов:

### Тайлсеты (PNG в пиксельный формат Spectrum)

Художник рисует тайлы в Aseprite, Photoshop или любом другом редакторе пиксельной графики в виде индексированного PNG. Тайлы расположены сеткой на одном листе. Скрипт конвертации:

1. Читает PNG, проверяет, что он 1-битный (чёрно-белый) или индексированный с цветами, совместимыми со Spectrum
2. Нарезает на тайлы 8x8 или 16x16
3. Конвертирует каждый тайл в чересстрочный пиксельный формат Spectrum (где строка 0 находится по смещению 0, строка 1 -- по смещению 256, а не по смещению 1 -- в соответствии с раскладкой экрана)
4. Опционально дедуплицирует идентичные тайлы
5. Записывает бинарный блоб и таблицу символов, отображающую ID тайлов в смещения

Для атрибутов каждый тайл также несёт цветовой байт (чернила (ink) + фон (paper) + яркость (bright)). Скрипт извлекает его из палитры PNG и записывает параллельную таблицу атрибутов.

### Листы спрайтов (PNG в предварительно сдвинутые данные спрайтов)

Спрайты следуют аналогичному конвейеру, но с дополнительным шагом: предварительным сдвигом. Скрипт конвертации:

1. Читает PNG-лист спрайтов
2. Нарезает на отдельные кадры
3. Генерирует маску для каждого кадра (любой не-фоновый пиксель даёт 0 в маске, фоновый -- 1)
4. Для каждого кадра генерирует 4 горизонтально сдвинутых варианта (смещение 0, 2, 4, 6 пикселей)
5. Каждый сдвинутый вариант расширяется на один байт (2-байтовый спрайт становится 3-байтовым для хранения переполнения сдвига)
6. Записывает чередующиеся байты данных и маски для эффективного рендеринга

### Карты уровней (Tiled JSON в бинарную тайловую карту)

Уровни разрабатываются в Tiled -- бесплатном кроссплатформенном редакторе тайловых карт. Дизайнер размещает тайлы визуально, добавляет слои объектов для точек спавна сущностей и триггеров и экспортирует в JSON или TMX.

Скрипт конвертации:

1. Читает экспорт Tiled
2. Извлекает слой тайлов как плоский массив индексов тайлов
3. Извлекает слой объектов для точек спавна (позиции врагов, начальная позиция игрока, расположение предметов)
4. Генерирует карту столкновений: для каждого тайла определяет, является ли он сплошным, платформой, опасностью или пустым (на основе файла свойств тайлов)
5. Записывает тайловую карту, карту столкновений и таблицу спавна как отдельные бинарные файлы

### Музыка (Vortex Tracker II в PT3)

Музыка создаётся в Vortex Tracker II, который экспортирует непосредственно в формат `.pt3`. Файл PT3 встраивается в данные банка через `INCBIN`. Код проигрывателя PT3 (широко доступный как Z80-ассемблер с открытым исходным кодом, обычно 1,5-2 килобайта) размещается в банке с музыкой рядом с данными композиций.

### Сборка воедино

Полный конвейер конвертации для уровня:

```text
tileset.png ──→ png2tiles.py ──→ tileset.bin ──→ pletter ──→ tileset.bin.plt
                                                              │
level1.tmx ──→ map2bin.py ──→ level1_map.bin ──→ zx0 ──→ level1_map.bin.zx0
              └─→ level1_collision.bin ──→ zx0 ──→ level1_col.bin.zx0
              └─→ level1_spawns.bin (uncompressed, small)
                                                              │
player.png ──→ png2sprites.py ──→ player.bin (pre-shifted) ──┘
enemies.png ──→ png2sprites.py ──→ enemies.bin              ──┘
                                                              │
level1.pt3 ──→ (direct INCBIN) ──────────────────────────────┘
                                                              │
sjasmplus main.a80 ──→ INCBIN all of the above ──→ ironclaw.tap
```

Каждый шаг автоматизирован Makefile. Художник меняет тайл, набирает `make` и видит результат в эмуляторе.

---

## 21.13 Формат релиза: сборка .tap

Конечный продукт -- файл `.tap`. sjasmplus может генерировать выходные `.tap` файлы напрямую через директиву `SAVETAP`:

```z80 id:ch21_release_format_building_the
; main.a80 -- top-level assembly file

    ; Define the BASIC loader
    DEVICE ZXSPECTRUM128

    ; Page in bank 2 at $8000
    ORG $8000

    ; Include all game code
    INCLUDE "defs.a80"
    INCLUDE "banks.a80"
    INCLUDE "render.a80"
    INCLUDE "sprites.a80"
    INCLUDE "entities.a80"
    INCLUDE "physics.a80"
    INCLUDE "collisions.a80"
    INCLUDE "ai.a80"
    INCLUDE "player.a80"
    INCLUDE "hud.a80"
    INCLUDE "menu.a80"
    INCLUDE "loader.a80"
    INCLUDE "music_driver.a80"
    INCLUDE "sfx.a80"
    INCLUDE "esxdos.a80"

    ; Entry point
entry:
    di
    ld   sp, $BFFF
    call init_system
    call detect_esxdos
    jr   c, .tape_load
    call load_from_esxdos
    jr   .loaded
.tape_load:
    call load_bank_data
.loaded:
    call init_interrupts
    ei
    jp   main_loop

    ; Bank data sections
    ; Each SLOT/PAGE directive places data into the correct bank
    SLOT 3               ; use $C000 slot
    PAGE 0               ; bank 0
    ORG $C000
    INCLUDE "data/bank0_levels.a80"   ; INCBIN compressed level data

    PAGE 1               ; bank 1
    ORG $C000
    INCLUDE "data/bank1_levels.a80"

    PAGE 3               ; bank 3
    ORG $C000
    INCLUDE "data/bank3_sprites.a80"

    PAGE 4               ; bank 4
    ORG $C000
    INCLUDE "data/bank4_music.a80"

    PAGE 6               ; bank 6
    ORG $C000
    INCLUDE "data/bank6_sfx.a80"

    ; Save as .tap with BASIC loader
    SAVETAP "build/ironclaw.tap", BASIC, "Ironclaw", 10, 2
    SAVETAP "build/ironclaw.tap", CODE, "Screen", $4000, 6912, $4000
    SAVETAP "build/ironclaw.tap", CODE, "Code", $8000, $-$8000, $8000

    ; Save bank snapshots (for .sna or manual loading)
    SAVESNA "build/ironclaw.sna", entry
```

Точный синтаксис SAVETAP зависит от версии sjasmplus. Для 128K-игр с банковыми данными самый чистый подход -- генерировать снапшот `.sna` (который захватывает состояние всех банков) для тестирования в эмуляторе и `.tap` с BASIC-загрузчиком плюс блоки машинного кода для дистрибуции.

### Тестирование релиза

Перед публикацией протестируй как минимум на трёх эмуляторах:

1. **Fuse** -- эталонный эмулятор Spectrum, точный тайминг оригинального оборудования
2. **Unreal Speccy** -- тайминг Pentagon, стандарт демосцены, хороший отладчик
3. **ZEsarUX** -- поддержка 128K-банков, эмуляция esxDOS, интеграция с DeZog

И если возможно, протестируй на реальном оборудовании с DivMMC. Эмуляторы иногда различаются в граничных случаях тайминга, и игра, которая идеально работает в Fuse, может терять кадры на реальном Spectrum из-за эффектов спорной памяти, которые эмулятор моделирует чуть иначе.

---

## 21.14 Финальная полировка

Разница между работающей игрой и готовой игрой -- это полировка. Вот чек-лист мелких штрихов, которые имеют значение:

**Переходы между экранами.** Не переключайся между экранами мгновенно. Простое затухание в чёрный (запись уменьшающейся яркости во все атрибуты за 8 кадров) или протирание (очистка столбцов слева направо за 16 кадров) придаёт игре профессиональный вид. Стоимость: пренебрежимая -- переходы происходят между игровыми кадрами.

**Анимация смерти.** Когда игрок погибает, заморозь геймплей на 15 кадров, мигай спрайтом игрока, переключая его чернила (ink) между кадрами, проиграй SFX смерти, затем перерожди. Не телепортируй игрока обратно на чекпоинт просто так.

**Тряска экрана.** Когда босс приземляется или происходит взрыв, сдвинь видовое окно на 1-2 пикселя на 4-6 кадров. На Spectrum это можно имитировать, корректируя смещение скроллинга без фактического перемещения тайлов. Это почти бесплатно и добавляет огромную динамику.

**Режим привлечения.** После 30 секунд на титульном экране без ввода запусти воспроизведение демо -- запиши ввод игрока во время тестового прохождения и воспроизведи его. Так аркадные автоматы привлекали прохожих, и для игр на Spectrum это тоже работает.

**Циклическая смена цветов.** Анимируй текст меню или цвета логотипа, циклически переключая атрибуты через таблицу палитры. 4-байтовый цикл атрибутов обходится практически в ноль процессорного времени и заставляет статичные экраны оживать.

**Антидребезг ввода.** Игнорируй нажатия клавиш короче 2 кадров. Без антидребезга курсор меню будет проскакивать мимо пунктов, потому что клавиша удерживалась несколько кадров. Простой счётчик кадров для каждой клавиши решает проблему:

```z80 id:ch21_final_polish
; Debounced fire button
fire_held_frames:
    db   0

check_fire:
    ld   a, (input_state)
    bit  4, a
    jr   z, .released
    ; Fire is held
    ld   a, (fire_held_frames)
    inc  a
    ld   (fire_held_frames), a
    cp   1                 ; only trigger on first frame of press
    ret                    ; Z flag set if this is the first frame
.released:
    xor  a
    ld   (fire_held_frames), a
    ret                    ; Z flag clear (no fire)
```

---

## Итого

- **Структура проекта важна.** Разделяй исходные файлы по подсистемам, файлы данных по типам. Используй Makefile для автоматизации полного конвейера от PNG/TMX до `.tap`.

- **Карта памяти -- тщательно.** Код в банке 2 (фиксированный по `$8000`), данные уровней в банках 0-1, графика спрайтов в банке 3, музыка в банках 4 и 6, теневой экран в банке 7. Храни теневую копию порта `$7FFD` -- он только для записи.

- **Обработчик прерываний владеет музыкой.** Обработчик IM2 подключает банк с музыкой, запускает проигрыватель PT3, обновляет SFX и восстанавливает предыдущий банк. Держи его лёгким -- максимум ~3 000 тактов.

- **Бюджет кадра геймплея на Pentagon -- 71 680 тактов.** Типичный кадр со скроллингом, 8 спрайтами и ИИ стоит ~50 000 тактов в среднем, ~65 000 в худшем случае. Профилируй и оптимизируй худший случай, а не средний.

- **Скроллинг -- самая дорогая одиночная операция.** Используй метод комбинированного скроллинга (посимвольный LDIR + пиксельное смещение) с двойной буферизацией через теневой экран. По возможности распределяй копирование столбцов на два кадра.

- **Запускай ИИ врагов каждый 2-й или 3-й кадр.** Физика и обнаружение столкновений работают каждый кадр; решения ИИ можно амортизировать. Это экономит 2 000-3 000 тактов за кадр в худшем случае.

- **Используй esxDOS для современного оборудования.** API `RST $08` / `F_OPEN` / `F_READ` / `F_CLOSE` прост и быстр. Определяй DivMMC при запуске и откатывайся на загрузку с ленты при отсутствии.

- **Профилируй с DeZog.** Полоска бордюра говорит, что ты выходишь за бюджет. DeZog говорит, где. Измеряй каждую подсистему, находи узкое место, оптимизируй его, измеряй снова.

- **Выбирай правильный упаковщик для каждой задачи.** Exomizer или ZX0 для одноразовой загрузки уровней (лучшая степень сжатия). Pletter для потоковой подачи тайлов во время геймплея (быстрая распаковка). Подробный анализ компромиссов -- в Главе 14.

- **Полировка не опциональна.** Переходы между экранами, анимации смерти, тряска экрана, антидребезг ввода и режим привлечения -- вот что отличает технодемо от игры.

- **Тестируй на нескольких эмуляторах и реальном оборудовании.** Fuse, Unreal Speccy и ZEsarUX моделируют тайминг по-разному. Поведение DivMMC на реальном оборудовании может отличаться от эмулированного esxDOS.

---

> **Источники:** World of Spectrum (документация по карте памяти ZX Spectrum 128K и порту $7FFD); Introspec «Data Compression for Modern Z80 Coding» (Hype, 2017); документация API esxDOS (DivIDE/DivMMC wiki); документация расширения DeZog для VS Code (GitHub: maziac/DeZog); документация sjasmplus (директивы SAVETAP, DEVICE, SLOT, PAGE); спецификация формата PT3 Vortex Tracker II; Главы 11, 14, 15, 16, 17, 18, 19 этой книги.
