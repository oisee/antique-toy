# Глава 18: Игровой цикл и система сущностей

> "Игра --- это демо, которое слушает."

---

Каждый эффект для демо, который мы строили до сих пор, работает в замкнутом цикле: вычислить, отрисовать, повторить. Зритель наблюдает. Коду всё равно, есть ли кто-то в комнате. Игра нарушает этот контракт. Игра *реагирует*. Игрок нажимает клавишу --- и что-то должно измениться немедленно, надёжно, в пределах того же бюджета кадра, который мы считаем с Главы 1.

Эта глава о построении архитектуры, которая делает игру возможной на ZX Spectrum и Agon Light 2. Не рендеринг (спрайты были в Главе 16, скроллинг в Главе 17) и не физика (столкновения и ИИ будут в Главе 19). Эта глава --- скелет: главный цикл, который всем управляет, конечный автомат, организующий переход от титульного экрана к геймплею и к экрану проигрыша, система ввода, считывающая намерения игрока, и система сущностей, управляющая каждым объектом в игровом мире.

К концу главы у тебя будет работающий каркас игры с 16 активными сущностями --- игрок, восемь врагов и семь пуль --- укладывающийся в бюджет кадра на обеих платформах.

---

## 18.1 Главный цикл

Каждая игра на ZX Spectrum следует одному фундаментальному ритму:

```
1. HALT          -- ждать прерывания кадра
2. Read input    -- чего хочет игрок?
3. Update state  -- перемещение сущностей, ИИ, проверка столкновений
4. Render        -- отрисовка кадра
5. Go to 1
```

Это игровой цикл. Он не сложен. Его сила в том, что он выполняется пятьдесят раз в секунду, каждую секунду, и всё, что испытывает игрок, возникает из этого цикла.

Вот минимальная реализация:

```z80
    ORG  $8000

    ; Install IM1 interrupt handler (standard for games)
    im   1
    ei

main_loop:
    halt                    ; 4T + wait -- sync to frame interrupt

    call read_input         ; poll keyboard/joystick
    call update_entities    ; move everything, run logic
    call render_frame       ; draw to screen

    jr   main_loop          ; 12T -- loop forever
```

Инструкция `HALT` --- это сердцебиение. Когда процессор выполняет `HALT`, он останавливается и ждёт следующего маскируемого прерывания. На Spectrum ULA генерирует это прерывание в начале каждого кадра --- раз в 1/50 секунды. Процессор просыпается, обработчик IM1 по адресу $0038 выполняется (на стандартной ROM это просто инкремент счётчика кадров), а затем выполнение продолжается с инструкции после `HALT`. Код твоего главного цикла отрабатывает, выполняет свою работу и снова попадает на `HALT`, чтобы дождаться следующего кадра.

Это даёт тебе ровно один кадр тактов на всё. Если работа завершается раньше, процессор простаивает внутри `HALT` до следующего прерывания --- никаких потерь, никакого дрейфа, идеальная синхронизация. Если работа занимает слишком много времени и прерывание срабатывает до того, как ты дойдёшь до `HALT`, ты пропускаешь кадр. Цикл всё равно работает (следующий `HALT` поймает очередное прерывание), но игра падает до 25 fps на этом кадре. Пропускаешь регулярно --- получаешь стабильные 25 fps. Пропускаешь сильно --- 16.7 fps (каждый третий кадр). Игрок это замечает.

### Бюджет кадра: повторение

Мы установили эти числа в Главе 1, но их стоит повторить в контексте игры:

| Машина | Тактов на кадр | Практический бюджет |
|---------|-------------------|------------------|
| ZX Spectrum 48K | 69 888 | ~62 000 (после накладных расходов на прерывание) |
| ZX Spectrum 128K | 70 908 | ~63 000 |
| Pentagon 128 | 71 680 | ~64 000 |
| Agon Light 2 | ~368 640 | ~360 000 |

"Практический бюджет" учитывает обработчик прерывания, саму инструкцию `HALT` и накладные расходы на тайминг бордюра. На Spectrum у тебя примерно 64 000 тактов полезного времени на кадр. На Agon --- более чем в пять раз больше.

Как типичная игра тратит эти 64 000 тактов? Вот реалистичная разбивка для платформера на Spectrum:

| Подсистема | Тактов | % бюджета |
|-----------|----------|-------------|
| Чтение ввода | ~500 | 0.8% |
| Обновление сущностей (16 сущностей) | ~8 000 | 12.5% |
| Обнаружение столкновений | ~4 000 | 6.3% |
| Проигрыватель музыки (PT3) | ~5 000 | 7.8% |
| Рендеринг спрайтов (8 видимых) | ~24 000 | 37.5% |
| Обновление фона/скроллинга | ~12 000 | 18.8% |
| Разное (HUD, состояние) | ~3 000 | 4.7% |
| **Оставшийся запас** | **~7 500** | **11.7%** |

Эти 11.7% запаса --- твоя зона безопасности. Заходишь в неё --- начинаешь терять кадры на сложных сценах. Техника профилирования цветом бордюра из Главы 1 --- красный для спрайтов, синий для музыки, зелёный для логики --- это способ мониторить этот бюджет в процессе разработки. Используй его постоянно.

На Agon та же игровая логика занимает малую долю бюджета. Обновление сущностей, обнаружение столкновений и чтение ввода могут потребовать 15 000 тактов суммарно --- около 4% бюджета кадра Agon. VDP обрабатывает рендеринг спрайтов на сопроцессоре ESP32, так что затраты на спрайты со стороны процессора сводятся к накладным расходам на VDU-команды. У тебя огромный запас для более сложного ИИ, большего числа сущностей или просто меньшего стресса.

![Game loop architecture](illustrations/output/ch18_game_loop.png)

---

## 18.2 Конечный автомат игры

Игра --- это не один цикл, а несколько. У титульного экрана свой цикл (анимация логотипа, ожидание нажатия клавиши). У меню свой цикл (подсветка пунктов, чтение ввода). Игровой цикл --- то, что мы описали выше. Экран паузы замораживает игровой цикл и запускает более простой. У экрана "Game Over" ещё один.

Самый чистый способ организовать всё это --- **конечный автомат**: переменная, хранящая текущее состояние игры, и таблица адресов обработчиков --- по одному на состояние.

### Определения состояний

```z80
; Game states (byte values, used as table offsets)
STATE_TITLE     EQU  0
STATE_MENU      EQU  2      ; x2 because each table entry is 2 bytes
STATE_GAME      EQU  4
STATE_PAUSE     EQU  6
STATE_GAMEOVER  EQU  8

; Current state variable
game_state:     DB   STATE_TITLE
```

### Таблица переходов

```z80
; Table of handler addresses, indexed by state
state_table:
    DW   state_title        ; STATE_TITLE   = 0
    DW   state_menu         ; STATE_MENU    = 2
    DW   state_game         ; STATE_GAME    = 4
    DW   state_pause        ; STATE_PAUSE   = 6
    DW   state_gameover     ; STATE_GAMEOVER = 8
```

### Диспетчер

Главный цикл становится диспетчером, который читает текущее состояние и переходит к соответствующему обработчику:

```z80
main_loop:
    halt                    ; sync to frame

    ; Dispatch to current state handler
    ld   a, (game_state)    ; 13T  load state index
    ld   l, a               ; 4T
    ld   h, 0               ; 7T
    ld   de, state_table    ; 10T
    add  hl, de             ; 11T  HL = state_table + offset
    ld   e, (hl)            ; 7T   low byte of handler address
    inc  hl                 ; 6T
    ld   d, (hl)            ; 7T   high byte of handler address
    ex   de, hl             ; 4T   HL = handler address
    jp   (hl)               ; 4T   jump to handler
                            ; --- 73T total dispatch overhead
```

Инструкция `JP (HL)` --- ключевая. Она переходит не по адресу, *хранящемуся* в HL, а по адресу, *находящемуся* в HL. Это косвенный переход Z80, и он стоит всего 4 такта. Весь диспатч --- загрузка переменной состояния, вычисление смещения в таблице, чтение адреса обработчика и переход --- занимает 73 такта. Это ничтожно мало: около 0.1% бюджета кадра.

Каждый обработчик выполняет свою логику и затем возвращается к `main_loop`:

```z80
state_title:
    call draw_title_screen
    call read_input
    ; Check for start key (SPACE or ENTER)
    ld   a, (input_flags)
    bit  BUTTON_FIRE, a
    jr   z, .no_start
    ; Transition to menu
    ld   a, STATE_MENU
    ld   (game_state), a
    call init_menu          ; set up menu screen
.no_start:
    jp   main_loop

state_game:
    call read_input
    ; Check for pause
    ld   a, (input_keys)
    bit  KEY_P, a
    jr   z, .not_paused
    ld   a, STATE_PAUSE
    ld   (game_state), a
    jp   main_loop
.not_paused:
    call update_entities
    call check_collisions
    call render_frame
    call update_music       ; AY player -- see Chapter 11
    jp   main_loop

state_pause:
    ; Game is frozen -- only check for unpause
    call read_input
    ld   a, (input_keys)
    bit  KEY_P, a
    jr   z, .still_paused
    ld   a, STATE_GAME
    ld   (game_state), a
.still_paused:
    ; Optionally blink "PAUSED" text
    call blink_pause_text
    jp   main_loop

state_gameover:
    call draw_gameover_screen
    call read_input
    ld   a, (input_flags)
    bit  BUTTON_FIRE, a
    jr   z, .wait
    ld   a, STATE_TITLE
    ld   (game_state), a
    call init_title
.wait:
    jp   main_loop
```

### Почему не цепочка сравнений?

Может возникнуть соблазн написать диспетчер так:

```z80
    ld   a, (game_state)
    cp   STATE_TITLE
    jp   z, state_title
    cp   STATE_MENU
    jp   z, state_menu
    cp   STATE_GAME
    jp   z, state_game
    ; ...
```

Это работает, но имеет две проблемы. Во-первых, стоимость растёт линейно: каждое дополнительное состояние добавляет `CP` (7T) и `JP Z` (10T), так что в худшем случае --- 17T на состояние. При 5 состояниях игровое состояние (самый частый случай) может потребовать 51T на достижение, если оно третье в цепочке сравнений. Таблица переходов стоит 73T независимо от активного состояния --- это O(1), а не O(n).

Во-вторых, что важнее, таблица переходов масштабируется чисто. Добавление шестого состояния (скажем, STATE_SHOP) означает добавление одной записи `DW` в таблицу и одного определения константы. Код диспетчера не меняется вообще. При цепочке сравнений ты добавляешь больше инструкций в сам диспетчер, и порядок начинает влиять на производительность. Табличный подход и быстрее в типичном случае, и чище в поддержке.

### Переходы между состояниями

Переходы между состояниями выполняются записью нового значения в `game_state`. Обычно при этом вызывается процедура инициализации нового состояния:

```z80
; Transition: Game -> Game Over
game_over_transition:
    ld   a, STATE_GAMEOVER
    ld   (game_state), a
    call init_gameover       ; set up game over screen, save score
    ret
```

Делай переходы явными и централизованными. Частый баг в играх для Z80 --- переход между состояниями, который забывает инициализировать данные нового состояния: экран проигрыша показывает мусор, потому что никто не очистил экран и не сбросил счётчик анимации. Каждое состояние должно иметь процедуру `init_`, которую переход вызывает.

---

## 18.3 Ввод: чтение игрока

### Клавиатура ZX Spectrum

Клавиатура Spectrum читается через порт `$FE`. Клавиатура подключена как матрица из 8 полурядов, каждый выбирается установкой бита в ноль в старшем байте адреса порта. Чтение порта `$FE` с определённым старшим байтом возвращает состояние этого полуряда: 5 бит, по одному на клавишу, где 0 означает "нажата", а 1 --- "не нажата".

Карта полурядов:

| Старший байт | Клавиши (бит 0 -- бит 4) |
|-----------|----------------------|
| $FE (бит 0 = 0) | SHIFT, Z, X, C, V |
| $FD (бит 1 = 0) | A, S, D, F, G |
| $FB (бит 2 = 0) | Q, W, E, R, T |
| $F7 (бит 3 = 0) | 1, 2, 3, 4, 5 |
| $EF (бит 4 = 0) | 0, 9, 8, 7, 6 |
| $DF (бит 5 = 0) | P, O, I, U, Y |
| $BF (бит 6 = 0) | ENTER, L, K, J, H |
| $7F (бит 7 = 0) | SPACE, SYMSHIFT, M, N, B |

Стандартные игровые управления --- Q/A/O/P для вверх/вниз/влево/вправо и SPACE для огня --- охватывают три полуряда. Вот процедура, которая их считывает и упаковывает результат в один байт:

```z80
; Input flag bits
INPUT_RIGHT  EQU  0
INPUT_LEFT   EQU  1
INPUT_DOWN   EQU  2
INPUT_UP     EQU  3
INPUT_FIRE   EQU  4

; Read QAOP+SPACE into input_flags
; Returns: A = input_flags byte, also stored at (input_flags)
read_keyboard:
    ld   d, 0               ; 7T   accumulate result in D

    ; Read O and P: half-row $DF (P=bit0, O=bit1)
    ld   bc, $DFFE          ; 10T
    in   a, (c)             ; 12T
    bit  0, a               ; 8T   P key
    jr   nz, .no_right      ; 12/7T
    set  INPUT_RIGHT, d     ; 8T
.no_right:
    bit  1, a               ; 8T   O key
    jr   nz, .no_left       ; 12/7T
    set  INPUT_LEFT, d      ; 8T
.no_left:

    ; Read Q and A: half-rows $FB (Q=bit0) and $FD (A=bit0... wait)
    ; Q is in half-row $FB at bit 0
    ld   b, $FB             ; 7T
    in   a, (c)             ; 12T
    bit  0, a               ; 8T   Q key
    jr   nz, .no_up         ; 12/7T
    set  INPUT_UP, d        ; 8T
.no_up:

    ; A is in half-row $FD at bit 0
    ld   b, $FD             ; 7T
    in   a, (c)             ; 12T
    bit  0, a               ; 8T   A key
    jr   nz, .no_down       ; 12/7T
    set  INPUT_DOWN, d      ; 8T
.no_down:

    ; SPACE: half-row $7F at bit 0
    ld   b, $7F             ; 7T
    in   a, (c)             ; 12T
    bit  0, a               ; 8T
    jr   nz, .no_fire       ; 12/7T
    set  INPUT_FIRE, d      ; 8T
.no_fire:

    ld   a, d               ; 4T
    ld   (input_flags), a   ; 13T
    ret                     ; 10T
    ; Total: ~220T worst case (all keys pressed)
```

При примерно 220 тактах в худшем случае чтение ввода тривиально в бюджете кадра. Даже на Spectrum ты можешь позволить себе читать клавиатуру десять раз за кадр и едва это заметить.

### Джойстик Kempston

Интерфейс Kempston ещё проще. Одно чтение порта возвращает все пять направлений плюс огонь:

```z80
; Kempston joystick port
KEMPSTON_PORT  EQU  $1F

; Read Kempston joystick
; Returns: A = joystick state
;   bit 0 = right, bit 1 = left, bit 2 = down, bit 3 = up, bit 4 = fire
read_kempston:
    in   a, (KEMPSTON_PORT)  ; 11T
    and  %00011111           ; 7T   mask to 5 bits
    ld   (input_flags), a    ; 13T
    ret                      ; 10T
    ; Total: 41T
```

Обрати внимание на удобное совпадение: расположение бит Kempston совпадает с нашими определениями `INPUT_*`. Это не случайность --- интерфейс Kempston был разработан с учётом этого стандарта, и большинство игр для Spectrum используют тот же порядок бит. Если ты поддерживаешь и клавиатуру, и джойстик, можно объединить результаты через OR:

```z80
read_input:
    call read_keyboard       ; D = keyboard flags
    push de
    call read_kempston       ; A = joystick flags
    pop  de
    or   d                   ; combine both sources
    ld   (input_flags), a
    ret
```

Теперь остальной код проверяет только `input_flags` и не заботится о том, пришёл ли ввод с клавиатуры или джойстика.

### Детектирование фронтов: нажатие vs удержание

Для некоторых действий --- выстрел, открытие меню --- нужно реагировать на событие *нажатия*, а не на состояние удержания. Если проверять `bit INPUT_FIRE, a` каждый кадр, игрок выпускает пулю каждую 1/50 секунды, пока удерживает кнопку. Это может быть намеренным для скорострельного оружия, но для одиночного выстрела или выбора в меню нужно детектирование фронтов.

Техника: сохраняем ввод предыдущего кадра рядом с текущим и XOR-им их, чтобы найти изменившиеся биты:

```z80
input_flags:      DB  0    ; current frame
input_prev:       DB  0    ; previous frame
input_pressed:    DB  0    ; newly pressed this frame (edges)

read_input_with_edges:
    ; Save previous state
    ld   a, (input_flags)
    ld   (input_prev), a

    ; Read current state
    call read_input          ; updates input_flags

    ; Compute edges: pressed = current AND NOT previous
    ld   a, (input_prev)
    cpl                      ; 4T   invert previous
    ld   b, a                ; 4T
    ld   a, (input_flags)    ; 13T
    and  b                   ; 4T   current AND NOT previous
    ld   (input_pressed), a  ; 13T  = newly pressed this frame
    ret
```

Теперь `input_pressed` имеет единичный бит только для кнопок, которые *не были* нажаты в прошлом кадре, но *нажаты* в этом. Используй `input_flags` для непрерывных действий (движение) и `input_pressed` для одноразовых действий (выстрел, прыжок, выбор в меню).

### Agon Light 2: PS/2-клавиатура через MOS

Agon читает свою PS/2-клавиатуру через MOS (Machine Operating System) API. eZ80 не сканирует клавиатурную матрицу напрямую --- вместо этого сопроцессор ESP32 VDP обрабатывает аппаратное обеспечение клавиатуры и передаёт события нажатий на eZ80 через общий буфер.

Системная переменная MOS `sysvar_keyascii` (по адресу $0800 + смещение) хранит ASCII-код последней нажатой клавиши или 0, если ни одна клавиша не нажата. Для игрового управления обычно опрашивают эту переменную или используют вызовы MOS API `waitvblank` / keyboard:

```z80
; Agon: Read keyboard via MOS sysvar
; MOS sysvar_keyascii at IX+$05
read_input_agon:
    ld   a, (ix + $05)      ; read last key from MOS sysvars
    ; Map ASCII to input_flags
    cp   'o'
    jr   nz, .not_left
    set  INPUT_LEFT, d
.not_left:
    cp   'p'
    jr   nz, .not_right
    set  INPUT_RIGHT, d
.not_right:
    ; ... etc for Q, A, SPACE
    ld   a, d
    ld   (input_flags), a
    ret
```

Agon также поддерживает чтение состояний отдельных клавиш через VDU-команды (VDU 23,0,$01,keycode), которые возвращают, удерживается ли конкретная клавиша в данный момент. Это ближе к подходу полурядов Spectrum и лучше подходит для игр, которым нужно одновременное обнаружение нажатий. MOS API обрабатывает протокол PS/2, трансляцию сканкодов и автоповтор --- обо всём этом тебе не нужно беспокоиться.

---

## 18.4 Структура сущности

Игровая сущность --- это всё, что двигается, анимируется, взаимодействует или требует покадрового обновления: персонаж игрока, враги, пули, взрывы, всплывающие числа очков, усиления. На Z80 мы представляем каждую сущность как блок байтов фиксированного размера в памяти.

### Раскладка структуры

Вот структура сущности, которую мы будем использовать во всех главах о разработке игр:

```
Offset  Size  Name        Description
------  ----  ----------  -------------------------------------------
 +0     2     x           X position, 8.8 fixed-point (high=pixel, low=subpixel)
 +2     1     y           Y position, pixel (0-191)
 +3     1     type        Entity type (0=inactive, 1=player, 2=enemy, 3=bullet, ...)
 +4     1     state       Entity state (0=idle, 1=active, 2=dying, 3=dead, ...)
 +5     1     anim_frame  Current animation frame index
 +6     1     dx          Horizontal velocity (signed, fixed-point fractional)
 +7     1     dy          Vertical velocity (signed, fixed-point fractional)
 +8     1     health      Hit points remaining
 +9     1     flags       Bit flags (see below)
------  ----
 10 bytes total per entity
```

Битовые флаги в байте `flags`:

```
Bit 0: ACTIVE      -- entity is alive and should be updated/rendered
Bit 1: VISIBLE     -- entity should be rendered (active but invisible = logic only)
Bit 2: COLLIDABLE  -- entity participates in collision detection
Bit 3: FACING_LEFT -- horizontal facing direction
Bit 4: INVINCIBLE  -- temporary invulnerability (player after being hit)
Bit 5: ON_GROUND   -- entity is standing on solid ground (set by physics)
Bit 6-7: reserved
```

### Почему 10 байт?

Десять байт --- осознанный выбор. Это достаточно мало, чтобы 16 сущностей занимали всего 160 байт --- ничтожно в терминах памяти. Важнее то, что умножение индекса сущности на 10 для нахождения смещения --- простая задача на Z80:

```z80
; Calculate entity address from index in A
; Input: A = entity index (0-15)
; Output: HL = address of entity structure
; Destroys: DE
get_entity_addr:
    ld   l, a               ; 4T
    ld   h, 0               ; 7T
    add  hl, hl             ; 11T  x2
    ld   d, h               ; 4T
    ld   e, l               ; 4T   DE = index x 2
    add  hl, hl             ; 11T  x4
    add  hl, hl             ; 11T  x8
    add  hl, de             ; 11T  x8 + x2 = x10
    ld   de, entity_array   ; 10T
    add  hl, de             ; 11T  HL = entity_array + index * 10
    ret                     ; 10T
    ; Total: 94T
```

Умножение на 10 использует стандартную декомпозицию: 10 = 8 + 2. Мы вычисляем индекс * 2, сохраняем его, вычисляем индекс * 8 и складываем. Никакой реальной инструкции умножения --- только сдвиги (ADD HL,HL) и сложение.

Если выбрать размер, равный степени двойки --- 8 или 16 байт на сущность --- вычисление индекса было бы ещё проще (три сдвига для 8, четыре для 16). Но 8 байт слишком тесно --- ты потеряешь либо скорость, либо здоровье, и то и другое важно. А 16 байт тратят 6 байт на сущность на паддинг, что накапливается: 16 сущностей x 6 потерянных байт = 96 байт мёртвого пространства. На Spectrum каждый байт на счету. Десять байт --- правильный размер для данных, которые нам реально нужны.

### Почему 16-битный X, но 8-битный Y?

Позиция X --- 16-битная с фиксированной точкой (формат 8.8): старший байт --- столбец пикселя (0--255), младший байт --- субпиксельная дробная часть для плавного движения. Это необходимо для горизонтально скроллящихся игр, где персонаж движется с дробной скоростью. Персонаж, движущийся со скоростью 1.5 пикселя за кадр только с целочисленными координатами, чередовал бы шаги в 1 и 2 пикселя, создавая видимые рывки. С фиксированной точкой 8.8 движение плавное: добавляем 0x0180 к X каждый кадр, и позиция пикселя продвигается 1, 2, 1, 2, 1, 2... по шаблону, который глаз воспринимает как стабильные 1.5 пикселя за кадр.

Позиция Y --- всего 8 бит, потому что экран Spectrum имеет высоту 192 пикселя --- одного байта достаточно для всего диапазона. Для игры с вертикальным скроллингом ты бы расширил Y до 16-битной фиксированной точки, ценой одного дополнительного байта на сущность.

### Система фиксированной точки 8.8

Арифметика с фиксированной точкой была введена в Главе 4. Вот краткий обзор того, как она применяется к движению сущностей:

```z80
; Move entity right at velocity dx
; HL points to entity X (2 bytes: low=fractional, high=pixel)
; A = dx (signed velocity, treated as fractional byte)
move_entity_x:
    ld   c, (hl)            ; 7T   load X fractional part
    inc  hl                  ; 6T
    ld   b, (hl)            ; 7T   load X pixel part
    ; BC = 16-bit fixed-point X

    ld   e, a               ; 4T   dx into E
    ; Sign-extend dx into DE
    rla                      ; 4T   carry = sign bit
    sbc  a, a               ; 4T   A = $FF if negative, $00 if positive
    ld   d, a               ; 4T   DE = signed 16-bit dx

    ex   de, hl             ; 4T
    add  hl, de             ; 11T  new_X = old_X + dx (16-bit add)
    ; HL = new X position (fractional in L, pixel in H)

    ; Store back
    ld   a, l               ; 4T
    ld   (entity_x_lo), a   ; 13T  (self-modifying, or use IX)
    ld   a, h               ; 4T
    ld   (entity_x_hi), a   ; 13T
    ret
```

Красота фиксированной точки: сложение и вычитание --- это обычные 16-битные операции `ADD HL,DE`. Никакой специальной обработки, никаких таблиц подстановки, никакого умножения. Дробная точность достигается автоматически, потому что мы несём субпиксельные биты с собой.

---

## 18.5 Массив сущностей

Сущности живут в статически выделенном массиве. Никакого динамического выделения памяти, никаких связных списков, никакой кучи. Статические массивы --- стандартный подход на Z80 по уважительной причине: они быстрые, предсказуемые и не могут фрагментироваться.

```z80
; Entity array: 16 entities, 10 bytes each = 160 bytes
MAX_ENTITIES    EQU  16
ENTITY_SIZE     EQU  10

entity_array:
    DS   MAX_ENTITIES * ENTITY_SIZE    ; 160 bytes, zeroed at init
```

### Распределение слотов сущностей

Слот 0 --- всегда игрок. Слоты 1--8 --- враги. Слоты 9--15 --- снаряды и эффекты (пули, взрывы, всплывающие очки). Это фиксированное разделение упрощает код: когда нужно перебрать врагов для ИИ, ты перебираешь слоты 1--8. Когда нужно создать пулю, ты ищешь в слотах 9--15. Игрок всегда по известному адресу.

```z80
; Fixed slot assignments
SLOT_PLAYER      EQU  0
SLOT_ENEMY_FIRST EQU  1
SLOT_ENEMY_LAST  EQU  8
SLOT_PROJ_FIRST  EQU  9
SLOT_PROJ_LAST   EQU  15
```

### Перебор сущностей

Основной цикл обновления проходит по каждому слоту сущности, проверяет флаг ACTIVE и вызывает соответствующий обработчик обновления:

```z80
; Update all active entities
; Total cost: ~2,500T for 16 entities (most inactive), up to ~8,000T (all active)
update_entities:
    ld   ix, entity_array   ; 14T  IX points to first entity
    ld   b, MAX_ENTITIES    ; 7T   loop counter

.loop:
    ; Check if entity is active
    ld   a, (ix + 9)        ; 19T  load flags byte (offset +9)
    bit  0, a               ; 8T   test ACTIVE flag
    jr   z, .skip           ; 12/7T skip if inactive

    ; Entity is active -- dispatch by type
    ld   a, (ix + 3)        ; 19T  load type byte (offset +3)
    ; Jump table dispatch based on type
    call update_by_type     ; ~200-500T depending on type

.skip:
    ; Advance IX to next entity
    ld   de, ENTITY_SIZE    ; 10T
    add  ix, de             ; 15T  IX += 10
    djnz .loop              ; 13/8T
    ret
```

Здесь IX используется как указатель на сущность, что удобно, потому что IX-индексированная адресация позволяет обращаться к любому полю по смещению: `(IX+0)` --- X low, `(IX+2)` --- Y, `(IX+3)` --- type, и так далее. Минус IX --- стоимость: каждая `LD A,(IX+n)` стоит 19 тактов против 7 для `LD A,(HL)`. Для цикла обновления сущностей, который выполняется 16 раз за кадр, эти накладные расходы приемлемы. Для внутреннего цикла рендеринга, где данные сущности трогаются тысячи раз за кадр, ты бы сначала скопировал нужные поля в регистры.

### Диспатч обновления по типу

У каждого типа сущности свой обработчик обновления. Мы используем ту же технику таблицы переходов, что и для конечного автомата игры:

```z80
; Entity type constants
TYPE_INACTIVE  EQU  0
TYPE_PLAYER    EQU  1
TYPE_ENEMY     EQU  2
TYPE_BULLET    EQU  3
TYPE_EXPLOSION EQU  4

; Handler table (2 bytes per entry)
type_handlers:
    DW   update_inactive     ; type 0: no-op, should not be called
    DW   update_player       ; type 1
    DW   update_enemy        ; type 2
    DW   update_bullet       ; type 3
    DW   update_explosion    ; type 4

; Dispatch to type handler
; Input: A = entity type, IX = entity pointer
update_by_type:
    add  a, a               ; 4T   type * 2 (table entries are 2 bytes)
    ld   l, a               ; 4T
    ld   h, 0               ; 7T
    ld   de, type_handlers   ; 10T
    add  hl, de             ; 11T
    ld   e, (hl)            ; 7T
    inc  hl                 ; 6T
    ld   d, (hl)            ; 7T
    ex   de, hl             ; 4T
    jp   (hl)               ; 4T   jump to handler (RET will return to caller)
                            ; --- 64T dispatch overhead
```

Каждый обработчик получает IX, указывающий на сущность, и может обращаться ко всем полям через индексированную адресацию. Когда обработчик выполняет `RET`, он возвращается в цикл обновления сущностей, который переходит к следующему слоту.

### Обработчик обновления игрока

Вот типичное обновление игрока --- чтение флагов ввода, применение движения, обновление анимации:

```z80
; Update player entity
; IX = entity pointer (slot 0)
update_player:
    ; Read horizontal input
    ld   a, (input_flags)    ; 13T
    bit  INPUT_RIGHT, a      ; 8T
    jr   z, .not_right       ; 12/7T
    ; Move right: add dx to X
    ld   a, 2               ; 7T   dx = 2 subpixels per frame (~1 pixel/frame)
    add  a, (ix + 0)        ; 19T  add to X fractional
    ld   (ix + 0), a        ; 19T
    jr   nc, .no_carry_r    ; 12/7T
    inc  (ix + 1)           ; 23T  carry into X pixel
.no_carry_r:
    res  3, (ix + 9)        ; 23T  clear FACING_LEFT flag
    jr   .horiz_done        ; 12T
.not_right:
    bit  INPUT_LEFT, a       ; 8T
    jr   z, .horiz_done      ; 12/7T
    ; Move left: subtract dx from X
    ld   a, (ix + 0)        ; 19T  load X fractional
    sub  2                   ; 7T   subtract dx
    ld   (ix + 0), a        ; 19T
    jr   nc, .no_borrow_l   ; 12/7T
    dec  (ix + 1)           ; 23T  borrow from X pixel
.no_borrow_l:
    set  3, (ix + 9)        ; 23T  set FACING_LEFT flag
.horiz_done:

    ; Update animation frame (cycle every 8 frames)
    ld   a, (ix + 5)        ; 19T  anim_frame
    inc  a                   ; 4T
    and  7                   ; 7T   wrap 0-7
    ld   (ix + 5), a        ; 19T
    ret
    ; Total: ~250-350T depending on input
```

Это намеренно просто. Глава 19 добавит гравитацию, прыжки и реакцию на столкновения. Пока что суть --- в *структуре*: указатель сущности в IX, поля по смещению, флаги ввода управляют изменениями состояния, счётчик анимации тикает.

---

## 18.6 Пул объектов

Пули, взрывы и эффекты частиц --- временные. Пуля существует долю секунды, прежде чем попасть во что-то или покинуть экран. Взрыв анимируется 8--16 кадров и исчезает. Можно создавать их динамически, но на Z80 "динамически" означает поиск свободной памяти, управление выделением и риск фрагментации. Вместо этого мы используем **пул объектов**: фиксированный набор слотов, в которые сущности активируются и из которых деактивируются.

У нас уже есть пул --- это массив сущностей. Слоты 9--15 --- пул снарядов/эффектов. Создание пули означает поиск неактивного слота в этом диапазоне и его заполнение. Уничтожение пули означает очистку её флага ACTIVE.

### Создание пули

```z80
; Spawn a bullet at position (B=x_pixel, C=y)
; moving in direction determined by player facing
; Returns: carry set if no free slot available
spawn_bullet:
    ld   ix, entity_array + (SLOT_PROJ_FIRST * ENTITY_SIZE)
    ld   d, SLOT_PROJ_LAST - SLOT_PROJ_FIRST + 1  ; 7 slots to check

.find_slot:
    ld   a, (ix + 9)        ; 19T  flags
    bit  0, a               ; 8T   ACTIVE?
    jr   z, .found          ; 12/7T found an inactive slot

    ld   e, ENTITY_SIZE     ; 7T
    add  ix, de             ; 15T  next slot (note: DE high byte may be nonzero,
                            ;      but we only care about the low 8 bits of offset)
    dec  d                  ; 4T
    jr   nz, .find_slot     ; 12T

    ; No free slot -- set carry and return
    scf                      ; 4T
    ret

.found:
    ; Fill in the bullet entity
    ld   (ix + 0), 0        ; fractional X = 0
    ld   (ix + 1), b        ; pixel X = B
    ld   (ix + 2), c        ; Y = C
    ld   (ix + 3), TYPE_BULLET ; type
    ld   (ix + 4), 1        ; state = active
    ld   (ix + 5), 0        ; anim_frame = 0
    ld   (ix + 8), 1        ; health = 1 (dies on first collision)

    ; Set velocity based on player facing
    ld   a, (entity_array + 9)  ; player flags
    bit  3, a               ; FACING_LEFT?
    jr   z, .fire_right
    ld   (ix + 6), -4       ; dx = -4 (fast, leftward)
    jr   .set_flags
.fire_right:
    ld   (ix + 6), 4        ; dx = +4 (fast, rightward)
.set_flags:
    ld   (ix + 7), 0        ; dy = 0 (horizontal bullet)
    ld   (ix + 9), %00000111  ; flags: ACTIVE + VISIBLE + COLLIDABLE
    or   a                   ; clear carry (success)
    ret
```

### Деактивация сущности

Когда пуля покидает экран или взрыв завершает анимацию, деактивация --- одна инструкция:

```z80
; Deactivate entity at IX
deactivate_entity:
    ld   (ix + 9), 0        ; 19T  clear all flags (ACTIVE=0)
    ret
```

Вот и всё. В следующем кадре цикл обновления увидит ACTIVE=0 и пропустит слот. Слот теперь доступен для следующего вызова `spawn_bullet`.

### Обработчик обновления пули

```z80
; Update a bullet entity
; IX = entity pointer
update_bullet:
    ; Move horizontally
    ld   a, (ix + 6)        ; 19T  dx
    ld   e, a               ; 4T
    ; Sign-extend
    rla                      ; 4T
    sbc  a, a               ; 4T
    ld   d, a               ; 4T   DE = signed 16-bit dx

    ld   l, (ix + 0)        ; 19T  X lo
    ld   h, (ix + 1)        ; 19T  X hi
    add  hl, de             ; 11T  new X
    ld   (ix + 0), l        ; 19T
    ld   (ix + 1), h        ; 19T

    ; Check screen bounds (0-255 pixel range)
    ld   a, h               ; 4T   pixel X
    or   a                   ; 4T
    jr   z, .off_screen     ; boundary check: if X=0, leftward bullet exited
    cp   248                ; 7T   near right edge?
    jr   nc, .off_screen    ; past right boundary

    ; Still alive -- return
    ret

.off_screen:
    ; Deactivate
    ld   (ix + 9), 0        ; clear flags
    ret
    ; Total: ~170T active, ~190T when deactivating
```

### Размер пула

Семь слотов для снарядов (индексы 9--15) могут показаться ограничением. На практике этого более чем достаточно для большинства игр на Spectrum. Подумай: пуля, пересекающая весь экран (256 пикселей) со скоростью 4 пикселя за кадр, летит 64 кадра --- больше секунды. Если игрок стреляет раз в 8 кадров (высокая скорострельность), одновременно может существовать максимум 8 пуль. Семь слотов с редкими неудачами спавна (пуля просто не вылетает в этом кадре) ощущаются естественно, а не как баг. Игрок вряд ли заметит пропущенную пулю на пределе скорострельности.

Если нужно больше --- расширяй массив сущностей. Но помни о стоимости: каждая дополнительная сущность добавляет ~160 тактов к худшему случаю цикла обновления (когда активна) и ~50 тактов даже когда неактивна (проверка флага ACTIVE и продвижение IX всё равно выполняются). Тридцать две сущности при всех активных потребляют примерно 16 000 тактов только в цикле обновления --- четверть бюджета кадра до того, как ты отрисовал хоть один пиксель.

На Agon можно позволить себе большие пулы. При 360 000 тактах на кадр и аппаратном рендеринге спрайтов 64 или даже 128 сущностей вполне реальны.

---

## 18.7 Сущности взрывов и эффектов

Взрывы, всплывающие очки и эффекты частиц используют те же слоты сущностей, что и пули. Разница --- в их обработчиках обновления: они проходят через последовательность кадров анимации и затем самоуничтожаются.

```z80
; Update an explosion entity
; IX = entity pointer
update_explosion:
    ; Advance animation frame
    ld   a, (ix + 5)        ; 19T  anim_frame
    inc  a                   ; 4T
    cp   8                   ; 7T   8 frames of animation
    jr   nc, .done          ; 12/7T animation complete

    ld   (ix + 5), a        ; 19T  store new frame
    ret

.done:
    ; Animation complete -- deactivate
    ld   (ix + 9), 0        ; 19T  clear flags
    ret
```

Чтобы создать взрыв при гибели врага:

```z80
; Spawn explosion at the enemy's position
; IX currently points to the dying enemy
spawn_explosion_at_entity:
    ld   b, (ix + 1)        ; enemy's X pixel
    ld   c, (ix + 2)        ; enemy's Y

    ; Find a free projectile/effect slot
    push ix
    ld   ix, entity_array + (SLOT_PROJ_FIRST * ENTITY_SIZE)
    ld   d, SLOT_PROJ_LAST - SLOT_PROJ_FIRST + 1

.find:
    ld   a, (ix + 9)
    bit  0, a
    jr   z, .got_slot
    ld   e, ENTITY_SIZE
    add  ix, de
    dec  d
    jr   nz, .find
    pop  ix
    ret                      ; no free slot -- skip explosion

.got_slot:
    ld   (ix + 0), 0        ; X fractional
    ld   (ix + 1), b        ; X pixel
    ld   (ix + 2), c        ; Y
    ld   (ix + 3), TYPE_EXPLOSION
    ld   (ix + 4), 1        ; state = active
    ld   (ix + 5), 0        ; anim_frame = 0
    ld   (ix + 6), 0        ; dx = 0 (stationary)
    ld   (ix + 7), 0        ; dy = 0
    ld   (ix + 8), 0        ; health = 0 (not collidable in a meaningful way)
    ld   (ix + 9), %00000011 ; ACTIVE + VISIBLE, not COLLIDABLE
    pop  ix
    ret
```

Паттерн всегда один и тот же: найти свободный слот, заполнить структуру, установить флаги. Обработчик обновления выполняет специфичную для типа работу. Деактивация очищает флаги. Слот переиспользуется в следующий раз, когда что-то нужно создать. Это весь жизненный цикл динамических объектов на Z80 --- никакого аллокатора, никакого сборщика мусора, никакого списка свободных блоков. Просто массив и флаг.

---

## 18.8 Собираем всё вместе: каркас игры

Вот полный каркас игры, связывающий всё воедино. Это компилируемый фреймворк со всеми частями: конечный автомат, ввод, система сущностей и главный цикл.

```z80
    ORG  $8000

; ============================================================
; Constants
; ============================================================
MAX_ENTITIES    EQU  16
ENTITY_SIZE     EQU  10

STATE_TITLE     EQU  0
STATE_MENU      EQU  2
STATE_GAME      EQU  4
STATE_PAUSE     EQU  6
STATE_GAMEOVER  EQU  8

TYPE_INACTIVE   EQU  0
TYPE_PLAYER     EQU  1
TYPE_ENEMY      EQU  2
TYPE_BULLET     EQU  3
TYPE_EXPLOSION  EQU  4

INPUT_RIGHT     EQU  0
INPUT_LEFT      EQU  1
INPUT_DOWN      EQU  2
INPUT_UP        EQU  3
INPUT_FIRE      EQU  4

FLAG_ACTIVE     EQU  0
FLAG_VISIBLE    EQU  1
FLAG_COLLIDABLE EQU  2
FLAG_FACING_L   EQU  3

; ============================================================
; Entry point
; ============================================================
entry:
    di
    ld   sp, $FFFF          ; set stack
    im   1
    ei

    ; Clear entity array
    ld   hl, entity_array
    ld   de, entity_array + 1
    ld   bc, MAX_ENTITIES * ENTITY_SIZE - 1
    ld   (hl), 0
    ldir

    ; Start in title state
    ld   a, STATE_TITLE
    ld   (game_state), a

; ============================================================
; Main loop with state dispatch
; ============================================================
main_loop:
    halt                     ; sync to frame interrupt

    ; --- Border profiling: red = active processing ---
    ld   a, 2
    out  ($FE), a

    ; Dispatch to current state
    ld   a, (game_state)
    ld   l, a
    ld   h, 0
    ld   de, state_table
    add  hl, de
    ld   e, (hl)
    inc  hl
    ld   d, (hl)
    ex   de, hl
    jp   (hl)

; Called by each state handler when done
return_to_loop:
    ; --- Border black: idle ---
    xor  a
    out  ($FE), a
    jr   main_loop

; ============================================================
; State table
; ============================================================
state_table:
    DW   state_title
    DW   state_menu
    DW   state_game
    DW   state_pause
    DW   state_gameover

; ============================================================
; State: Title screen
; ============================================================
state_title:
    call read_input_with_edges
    ld   a, (input_pressed)
    bit  INPUT_FIRE, a
    jr   z, .wait
    ; Transition to game
    ld   a, STATE_GAME
    ld   (game_state), a
    call init_game
.wait:
    jp   return_to_loop

; ============================================================
; State: Game
; ============================================================
state_game:
    call read_input_with_edges

    ; Check pause
    ; (using 'P' key -- half-row $DF, bit 0 is P, but for simplicity
    ;  we check input_pressed bit 4 / FIRE as a toggle here)

    ; Update all entities
    call update_entities

    ; Render all visible entities
    call render_entities

    ; Update music
    ; call music_play         ; PT3 player -- see Chapter 11

    jp   return_to_loop

; ============================================================
; State: Pause (minimal)
; ============================================================
state_pause:
    call read_input_with_edges
    ld   a, (input_pressed)
    bit  INPUT_FIRE, a
    jr   z, .still_paused
    ld   a, STATE_GAME
    ld   (game_state), a
.still_paused:
    jp   return_to_loop

; ============================================================
; State: Game Over (minimal)
; ============================================================
state_gameover:
    call read_input_with_edges
    ld   a, (input_pressed)
    bit  INPUT_FIRE, a
    jr   z, .wait
    ld   a, STATE_TITLE
    ld   (game_state), a
.wait:
    jp   return_to_loop

; ============================================================
; State: Menu (minimal — expand for your game)
; ============================================================
state_menu:
    ; A full menu would display options and handle UP/DOWN/FIRE.
    ; For this skeleton, the menu simply transitions to the title.
    ; See Exercise 2 below for adding a real menu with item selection.
    jp   state_title

; ============================================================
; Init game: set up player and enemies
; ============================================================
init_game:
    ; Clear entity array
    ld   hl, entity_array
    ld   de, entity_array + 1
    ld   bc, MAX_ENTITIES * ENTITY_SIZE - 1
    ld   (hl), 0
    ldir

    ; Set up player (slot 0)
    ld   ix, entity_array
    ld   (ix + 0), 0        ; X fractional = 0
    ld   (ix + 1), 128      ; X pixel = 128 (centre)
    ld   (ix + 2), 160      ; Y = 160 (near bottom)
    ld   (ix + 3), TYPE_PLAYER
    ld   (ix + 4), 1        ; state = active
    ld   (ix + 5), 0        ; anim_frame
    ld   (ix + 6), 0        ; dx
    ld   (ix + 7), 0        ; dy
    ld   (ix + 8), 3        ; health = 3
    ld   (ix + 9), %00000111 ; ACTIVE + VISIBLE + COLLIDABLE

    ; Set up 8 enemies (slots 1-8) in a formation
    ld   ix, entity_array + ENTITY_SIZE   ; slot 1
    ld   b, 8               ; 8 enemies
    ld   c, 24              ; starting X pixel

.enemy_loop:
    ld   (ix + 0), 0        ; X fractional
    ld   (ix + 1), c        ; X pixel
    ld   (ix + 2), 32       ; Y = 32 (near top)
    ld   (ix + 3), TYPE_ENEMY
    ld   (ix + 4), 1        ; state = active
    ld   (ix + 5), 0        ; anim_frame
    ld   (ix + 6), 1        ; dx = 1 (moving right slowly)
    ld   (ix + 7), 0        ; dy = 0
    ld   (ix + 8), 1        ; health = 1
    ld   (ix + 9), %00000111 ; ACTIVE + VISIBLE + COLLIDABLE

    ; Advance to next slot and X position
    ld   de, ENTITY_SIZE
    add  ix, de
    ld   a, c
    add  a, 28              ; 28 pixels apart
    ld   c, a
    djnz .enemy_loop

    ret

; ============================================================
; Input system
; ============================================================
input_flags:      DB  0
input_prev:       DB  0
input_pressed:    DB  0

read_input_with_edges:
    ; Save previous
    ld   a, (input_flags)
    ld   (input_prev), a

    ; Read keyboard (QAOP + SPACE)
    ld   d, 0

    ; P key: half-row $DF, bit 0
    ld   bc, $DFFE
    in   a, (c)
    bit  0, a
    jr   nz, .no_right
    set  INPUT_RIGHT, d
.no_right:
    ; O key: half-row $DF, bit 1
    bit  1, a
    jr   nz, .no_left
    set  INPUT_LEFT, d
.no_left:

    ; Q key: half-row $FB, bit 0
    ld   b, $FB
    in   a, (c)
    bit  0, a
    jr   nz, .no_up
    set  INPUT_UP, d
.no_up:

    ; A key: half-row $FD, bit 0
    ld   b, $FD
    in   a, (c)
    bit  0, a
    jr   nz, .no_down
    set  INPUT_DOWN, d
.no_down:

    ; SPACE: half-row $7F, bit 0
    ld   b, $7F
    in   a, (c)
    bit  0, a
    jr   nz, .no_fire
    set  INPUT_FIRE, d
.no_fire:

    ld   a, d
    ld   (input_flags), a

    ; Compute edges
    ld   a, (input_prev)
    cpl
    ld   b, a
    ld   a, (input_flags)
    and  b
    ld   (input_pressed), a
    ret

; ============================================================
; Entity update loop
; ============================================================
update_entities:
    ld   ix, entity_array
    ld   b, MAX_ENTITIES

.loop:
    push bc
    ld   a, (ix + 9)        ; flags
    bit  FLAG_ACTIVE, a
    jr   z, .skip

    ld   a, (ix + 3)        ; type
    call update_by_type

.skip:
    ld   de, ENTITY_SIZE
    add  ix, de
    pop  bc
    djnz .loop
    ret

; ============================================================
; Type dispatch
; ============================================================
type_handlers:
    DW   .nop_handler       ; TYPE_INACTIVE
    DW   update_player
    DW   update_enemy
    DW   update_bullet
    DW   update_explosion

update_by_type:
    add  a, a
    ld   l, a
    ld   h, 0
    ld   de, type_handlers
    add  hl, de
    ld   e, (hl)
    inc  hl
    ld   d, (hl)
    ex   de, hl
    jp   (hl)

.nop_handler:
    ret

; ============================================================
; Player update
; ============================================================
update_player:
    ld   a, (input_flags)
    bit  INPUT_RIGHT, a
    jr   z, .not_right
    ld   a, (ix + 0)
    add  a, 2               ; move right (subpixel)
    ld   (ix + 0), a
    jr   nc, .x_done_r
    inc  (ix + 1)
.x_done_r:
    res  FLAG_FACING_L, (ix + 9)
    jr   .horiz_done
.not_right:
    bit  INPUT_LEFT, a
    jr   z, .horiz_done
    ld   a, (ix + 0)
    sub  2                   ; move left (subpixel)
    ld   (ix + 0), a
    jr   nc, .x_done_l
    dec  (ix + 1)
.x_done_l:
    set  FLAG_FACING_L, (ix + 9)
.horiz_done:

    ; Fire bullet on press (edge-detected)
    ld   a, (input_pressed)
    bit  INPUT_FIRE, a
    jr   z, .no_fire
    ld   b, (ix + 1)        ; player X pixel
    ld   c, (ix + 2)        ; player Y
    call spawn_bullet
.no_fire:

    ; Animate
    ld   a, (ix + 5)
    inc  a
    and  7
    ld   (ix + 5), a
    ret

; ============================================================
; Enemy update (simple patrol)
; ============================================================
update_enemy:
    ; Move by dx
    ld   a, (ix + 6)        ; dx
    add  a, (ix + 1)        ; add to X pixel
    ld   (ix + 1), a

    ; Bounce at screen edges
    cp   240
    jr   c, .no_bounce_r
    ld   (ix + 6), -1       ; reverse direction
    jr   .bounce_done
.no_bounce_r:
    cp   8
    jr   nc, .bounce_done
    ld   (ix + 6), 1        ; reverse direction
.bounce_done:

    ; Animate
    ld   a, (ix + 5)
    inc  a
    and  3                   ; 4-frame animation cycle
    ld   (ix + 5), a
    ret

; ============================================================
; Bullet update
; ============================================================
update_bullet:
    ld   a, (ix + 6)        ; dx
    add  a, (ix + 1)        ; add to X pixel (simplified: integer movement)
    ld   (ix + 1), a

    ; Off screen?
    cp   248
    jr   nc, .deactivate
    or   a
    jr   z, .deactivate
    ret

.deactivate:
    ld   (ix + 9), 0        ; clear all flags
    ret

; ============================================================
; Explosion update
; ============================================================
update_explosion:
    ld   a, (ix + 5)        ; anim_frame
    inc  a
    cp   8                   ; 8 frames
    jr   nc, .done
    ld   (ix + 5), a
    ret
.done:
    ld   (ix + 9), 0
    ret

; ============================================================
; Spawn bullet
; ============================================================
spawn_bullet:
    ; B = x pixel, C = y
    push ix
    ld   ix, entity_array + (9 * ENTITY_SIZE)   ; first projectile slot
    ld   d, 7               ; 7 slots to search

.find:
    ld   a, (ix + 9)
    bit  FLAG_ACTIVE, a
    jr   z, .found
    ld   e, ENTITY_SIZE
    push de
    pop  de                  ; (DE preserved; only low byte matters for add ix,de)
    ld   e, ENTITY_SIZE
    add  ix, de
    dec  d
    jr   nz, .find
    ; No free slot
    pop  ix
    scf
    ret

.found:
    ld   (ix + 0), 0
    ld   (ix + 1), b
    ld   (ix + 2), c
    ld   (ix + 3), TYPE_BULLET
    ld   (ix + 4), 1
    ld   (ix + 5), 0
    ld   (ix + 7), 0        ; dy = 0

    ; Direction from player facing
    ld   a, (entity_array + 9)   ; player flags
    bit  FLAG_FACING_L, a
    jr   z, .right
    ld   (ix + 6), -4       ; dx = -4
    jr   .dir_done
.right:
    ld   (ix + 6), 4        ; dx = +4
.dir_done:
    ld   (ix + 8), 1        ; health = 1
    ld   (ix + 9), %00000111 ; ACTIVE + VISIBLE + COLLIDABLE

    pop  ix
    or   a                   ; clear carry
    ret

; ============================================================
; Render entities (stub -- see Chapter 16 for sprite rendering)
; ============================================================
render_entities:
    ; In a real game, this iterates visible entities and draws sprites.
    ; See Chapter 16 for OR+AND masked sprites, pre-shifted sprites,
    ; and the dirty-rectangle system.
    ; For this skeleton, we use a minimal attribute-block renderer.
    ld   ix, entity_array
    ld   b, MAX_ENTITIES

.loop:
    push bc
    ld   a, (ix + 9)
    bit  FLAG_VISIBLE, a
    jr   z, .skip

    ; Draw a 1-character coloured block at entity position.
    ; For real sprite rendering, see Chapter 16 (OR+AND masks,
    ; pre-shifted sprites, compiled sprites, dirty rectangles).
    ld   a, (ix + 1)        ; X pixel
    rrca                     ; /2
    rrca                     ; /4
    rrca                     ; /8 = character column
    and  $1F                 ; mask to 0-31
    ld   e, a
    ld   a, (ix + 2)        ; Y pixel
    rrca
    rrca
    rrca
    and  $1F                 ; character row (0-23)
    ; Compute attribute address: $5800 + row*32 + col
    ld   l, a
    ld   h, 0
    add  hl, hl             ; row * 2
    add  hl, hl             ; row * 4
    add  hl, hl             ; row * 8
    add  hl, hl             ; row * 16
    add  hl, hl             ; row * 32
    ld   d, 0
    add  hl, de             ; + column
    ld   de, $5800
    add  hl, de             ; HL = attribute address

    ; Colour by type
    ld   a, (ix + 3)        ; type
    add  a, a               ; type * 2 (crude colour mapping)
    or   %01000000           ; BRIGHT bit
    ld   (hl), a            ; write attribute

.skip:
    ld   de, ENTITY_SIZE
    add  ix, de
    pop  bc
    djnz .loop
    ret

; ============================================================
; Data
; ============================================================
game_state:     DB   STATE_TITLE

entity_array:
    DS   MAX_ENTITIES * ENTITY_SIZE, 0
```

Этот каркас компилируется, запускается и делает что-то видимое: цветные блоки перемещаются по сетке атрибутов. Блок игрока реагирует на управление QAOP. Нажатие SPACE создаёт пули, которые летят через экран. Враги отскакивают между краями экрана. Когда пуля покидает экран, её слот освобождается для следующего выстрела.

Выглядит некрасиво --- атрибутные блоки вместо спрайтов, нет скроллинга, нет звука. Но архитектура полна. Каждая часть из этой главы присутствует и подключена: главный цикл на HALT, диспетчер конечного автомата, считыватель ввода с детектированием фронтов, массив сущностей с обработчиками обновления по типам, и пул объектов для снарядов. Главы 16 и 17 предоставляют рендеринг. Глава 19 --- физику и столкновения. Глава 11 --- музыку. Этот каркас --- место, куда они все подключаются.

---

## 18.9 Agon Light 2: та же архитектура, больше пространства

Agon Light 2 использует ту же фундаментальную структуру игрового цикла. eZ80 выполняет Z80-код нативно (в Z80-совместимом режиме или режиме ADL), так что главный цикл на HALT, конечный автомат, система сущностей и логика ввода --- всё переносится напрямую.

Ключевые отличия:

**Синхронизация кадров.** Agon использует вызов MOS `waitvblank` (RST $08, функция $1E) вместо `HALT` для синхронизации кадров. VDP генерирует сигнал вертикального гашения, и MOS API его предоставляет.

**Ввод.** Чтение клавиатуры проходит через системные переменные MOS, а не через прямой ввод-вывод портов. Матрицы полурядов не существует --- PS/2-клавиатура обрабатывается ESP32 VDP. Уровень абстракции ввода, который мы построили (всё сводится к `input_flags`), означает, что остальной код игры не заботится о разнице.

**Бюджет сущностей.** При ~360 000 тактах на кадр и аппаратном рендеринге спрайтов цикл обновления сущностей больше не является узким местом. Можно обновлять 64 сущности со сложным ИИ и всё равно использовать менее 10% бюджета кадра. Ограничивающий фактор на Agon --- количество спрайтов VDP на строку развёртки (обычно 16--32 аппаратных спрайта на одной линии), а не процессорное время.

**Рендеринг.** VDP Agon обрабатывает рендеринг спрайтов. Вместо ручного блиттинга пикселей в экранную память (шесть методов из Главы 16) ты отправляешь VDU-команды для позиционирования аппаратных спрайтов. Стоимость CPU на спрайт падает с ~1200 тактов (блит OR+AND на Spectrum) до ~50--100 тактов (отправка VDU-команды позиции). Это освобождает огромное количество процессорного времени для игровой логики.

**Память.** У Agon 512 КБ плоской памяти --- никакого банкинга, никаких спорных регионов. Массив сущностей, таблицы подстановки, данные спрайтов, карты уровней и музыка могут сосуществовать без гимнастики переключения банков, описанной в Главе 15 для Spectrum 128K.

Практический вывод: на Agon архитектура этой главы масштабируется без усилий. Больше сущностей, более сложные конечные автоматы, больше логики ИИ --- ничто из этого не угрожает бюджету кадра. Дисциплина подсчёта каждого такта по-прежнему важна (это хорошая инженерия), но ограничения, вынуждающие мучительные компромиссы на Spectrum, просто не применяются.

---

## 18.10 Проектные решения и компромиссы

### Фиксированная vs переменная частота кадров

Главный цикл этой главы предполагает фиксированные 50 fps: сделай всё за один кадр или пропусти. Альтернатива --- переменный временной шаг: измерить длительность кадра и масштабировать всё движение по дельте времени. Переменные временные шаги стандартны в современных игровых движках, но добавляют сложность на Z80 --- нужен таймер кадра, умножение на дельту в каждом вычислении движения и аккуратная обработка стабильности физики при переменных скоростях.

Для игр на Spectrum фиксированные 50 fps --- почти всегда правильный выбор. Аппаратура детерминирована, бюджет кадра предсказуем, и простота физики с фиксированным шагом (всё движется на постоянные величины каждый кадр) устраняет целую категорию багов. Если твоя игра падает ниже 50 fps, ответ --- оптимизировать, пока не перестанет, а не добавлять переменный временной шаг.

На Agon, с его большим бюджетом, переменный тайминг ещё менее вероятно потребуется. Фиксируй частоту кадров на 50 или 60 fps и упрощай жизнь.

### Размер сущности: компактный vs щедрый

Наша 10-байтная структура сущности --- компактная. Некоторые коммерческие игры для Spectrum использовали 16 или даже 32 байта на сущность, храня дополнительные поля: предыдущая позиция (для стирания грязных прямоугольников), адрес спрайта, размеры коллизионного бокса, таймер ИИ и многое другое.

Компромисс --- скорость перебора versus доступ к полям. Наш массив из 16 сущностей занимает 160 байт, и полный цикл обновления выполняется за ~8 000 тактов. Структура в 32 байта с 16 сущностями занимает 512 байт (всё ещё мало), но накладные расходы на перебор растут, потому что IX продвигается на 32 каждый шаг, и индексированные обращения к полям с большими смещениями вроде `(IX+28)` стоят те же 19 тактов, но их труднее отслеживать.

Если нужно больше данных на сущность, рассмотри разделение структуры: компактный "горячий" массив (позиция, тип, флаги --- поля, используемые каждый кадр) и параллельный "холодный" массив (адрес спрайта, состояние ИИ, значение очков --- поля, к которым обращаются только по необходимости). Это тот же компромисс "структура массивов" vs "массив структур", с которым сталкиваются современные игровые движки, применённый в масштабе Z80.

### Когда использовать HL вместо IX

IX-индексированная адресация удобна, но дорога: 19 тактов на обращение против 7 для `(HL)`. В цикле обновления (вызывается 16 раз за кадр) накладные расходы IX приемлемы --- 16 x 12 дополнительных тактов на обращение = 192 такта, ничтожно.

Но в цикле рендеринга, где ты можешь трогать 4--6 полей сущности для каждого из 8 видимых спрайтов, стоимость накапливается. Техника: в начале прохода рендеринга для каждой сущности копируй нужные поля в регистры:

```z80
    ; Copy entity fields to registers for fast rendering
    ld   l, (ix + 0)        ; 19T  X lo
    ld   h, (ix + 1)        ; 19T  X hi
    ld   c, (ix + 2)        ; 19T  Y
    ld   a, (ix + 5)        ; 19T  anim_frame
    ; Now render using H (X pixel), C (Y), A (frame)
    ; All subsequent accesses are register-to-register: 4T each
```

Четыре обращения через IX по 19T = 76T авансом, затем вся процедура рендеринга использует обращения к регистрам по 4T вместо 19T через IX. Если процедура рендеринга трогает эти поля 10 раз, ты экономишь (19-4) x 10 - 76 = 74 такта на сущность. Немного, но для 8 сущностей за кадр это 592 такта --- достаточно, чтобы нарисовать ещё полспрайта.

---

## Итого

- **Игровой цикл** --- это `HALT -> Ввод -> Обновление -> Рендеринг -> повтор`. Инструкция `HALT` синхронизируется с прерыванием кадра, давая тебе ровно один кадр тактов (примерно 64 000 на Pentagon, 360 000 на Agon).

- **Конечный автомат** с таблицей переходов из указателей на обработчики (`DW state_title`, `DW state_game`, и т.д.) организует поток от титульного экрана через геймплей к экрану проигрыша. Диспатч стоит 73 такта независимо от количества состояний --- постоянное время, чистое масштабирование.

- **Чтение ввода** на Spectrum использует `IN A,(C)` для опроса полурядов клавиатуры через порт `$FE`. Пять клавиш (QAOP + SPACE) стоят примерно 220 тактов. Джойстик Kempston --- одно чтение порта за 11T. Детектирование фронтов (нажатие vs удержание) использует XOR между текущим и предыдущим кадрами.

- **Структура сущности** --- 10 байт: X (16-бит с фиксированной точкой), Y, тип, состояние, anim_frame, dx, dy, здоровье, флаги. Шестнадцать сущностей занимают 160 байт. Умножение на 10 для преобразования индекса в адрес использует декомпозицию 10 = 8 + 2.

- **Массив сущностей** статически выделен с фиксированным распределением слотов: слот 0 для игрока, слоты 1--8 для врагов, слоты 9--15 для снарядов и эффектов. Перебор проверяет флаг ACTIVE и диспатчит к обработчикам по типам через вторую таблицу переходов.

- **Пул объектов** --- это сам массив сущностей. Создание устанавливает поля и флаг ACTIVE. Деактивация очищает флаги. Поиск свободного слота --- линейный сканирование соответствующего диапазона слотов. Семь слотов для снарядов справляются с типичной скорострельностью без того, чтобы игрок замечал пропущенные спавны.

- **IX-индексированная адресация** удобна для доступа к полям сущности (19T на обращение), но дорога во внутренних циклах. Копируй поля в регистры в начале рендеринга для обращений по 4T.

- Agon Light 2 использует ту же архитектуру с большим запасом. MOS `waitvblank` заменяет `HALT`, PS/2-клавиатура заменяет сканирование полурядов, аппаратные спрайты заменяют CPU-блиттинг. Цикл обновления сущностей больше не является узким местом.

- Практический каркас в этой главе содержит конечный автомат, 16 сущностей (1 игрок + 8 врагов + 7 слотов для пуль/эффектов), ввод с детектированием фронтов, обработчики обновления по типам и минимальный рендерер атрибутных блоков. Это шасси, к которому подключаются Главы 16 (спрайты), 17 (скроллинг), 19 (столкновения) и 11 (звук).

---

## Попробуй сам

1. **Собери каркас.** Скомпилируй каркас игры из раздела 18.8 и запусти его в эмуляторе. Используй QAOP для перемещения блока игрока и SPACE для стрельбы. Наблюдай, как цветные блоки двигаются. Добавь профилирование цветом бордюра (Глава 1), чтобы увидеть, сколько бюджета кадра используется.

2. **Добавь шестое состояние.** Реализуй STATE_SHOP между Menu и Game. Экран магазина должен отображать три предмета и позволять игроку выбрать один клавишами UP/DOWN и FIRE. Это упражнение на конечный автомат --- добавь константу, запись в таблице, обработчик и логику перехода.

3. **Увеличь количество сущностей.** Увеличь MAX_ENTITIES до 32, добавь 16 врагов и измерь влияние на бюджет кадра с помощью профилирования бордюром. При каком количестве сущностей цикл обновления начинает угрожать 50 fps?

4. **Реализуй поддержку Kempston.** Добавь считыватель джойстика Kempston и объедини его с клавиатурным вводом через OR. Протестируй в эмуляторе, поддерживающем эмуляцию Kempston (Fuse: Options -> Joysticks -> Kempston).

5. **Раздели горячие и холодные данные.** Создай второй "холодный" массив с 4 байтами на сущность (адрес спрайта, таймер ИИ, состояние ИИ, значение очков). Измени цикл обновления так, чтобы холодные данные использовались только когда тип сущности этого требует (враги для ИИ, не пули). Измерь экономию тактов.

---

*Далее: Глава 19 --- Столкновения, физика и ИИ врагов. Мы добавим AABB-обнаружение столкновений, гравитацию, прыжки и четыре модели поведения врагов к каркасу из этой главы.*

---

> **Источники:** клавиатурная матрица и раскладка портов ZX Spectrum из технической документации Sinclair Research; спецификация интерфейса джойстика Kempston; техники арифметики с фиксированной точкой из Главы 4 (Dark/X-Trade, Spectrum Expert #01, 1997); профилирование цветом бордюра из Главы 1; методы рендеринга спрайтов из Главы 16; интеграция музыки AY из Главы 11; документация MOS API Agon Light 2 (Bernardo Kastrup, agon-light.com)
