# Розділ 18: Ігровий цикл та система сутностей

> "Гра — це демо, яке слухає."

---

Кожен ефект демо, який ми будували досі, працює в замкненому циклі: обчислити, відрендерити, повторити. Глядач дивиться. Коду байдуже, чи хтось є в кімнаті. Гра порушує цей контракт. Гра *відповідає*. Гравець натискає клавішу, і щось має змінитися — негайно, надійно, в межах того самого бюджету кадру, який ми рахуємо з Розділу 1.

Цей розділ про побудову архітектури, що робить гру можливою на ZX Spectrum та Agon Light 2. Не про рендеринг (Розділ 16 охопив спрайти, Розділ 17 — скролінг) і не про фізику (Розділ 19 займеться зіткненнями та ШІ). Цей розділ — скелет: головний цикл, що рухає все, скінченний автомат, що організовує потік від титульного екрана до геймплею та ігрового кінця, система введення, що зчитує наміри гравця, та система сутностей, що керує кожним об'єктом в ігровому світі.

Наприкінці у тебе буде робочий ігровий скелет із 16 активними сутностями — гравцем, вісьмома ворогами та сімома снарядами — що працює в межах бюджету кадру на обох платформах.

---

## 18.1 Головний цикл

Кожна гра на ZX Spectrum дотримується одного фундаментального ритму:

```
1. HALT          -- чекати на переривання кадру
2. Read input    -- чого хоче гравець?
3. Update state  -- рухати сутності, запускати ШІ, перевіряти зіткнення
4. Render        -- малювати кадр
5. Go to 1
```

Це ігровий цикл. Він нескладний. Його сила в тому, що він виконується п'ятдесят разів на секунду, кожну секунду, і все, що переживає гравець, виникає з цього циклу.

Ось мінімальна реалізація:

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

Інструкція `HALT` — це серцебиття. Коли процесор виконує `HALT`, він зупиняється і чекає на наступне масковане переривання. На Spectrum ULA генерує це переривання на початку кожного кадру — раз на 1/50 секунди. Процесор прокидається, обробник IM1 за адресою $0038 виконується (на стандартній ROM він просто інкрементує лічильник кадрів), а потім виконання продовжується з інструкції після `HALT`. Твій код головного циклу працює, робить свою справу і знову потрапляє на `HALT`, щоб чекати наступного кадру.

Це дає тобі рівно один кадр тактів для всієї роботи. Якщо твоя робота завершується раніше, процесор простоює всередині `HALT` до наступного переривання — жодних витрачених ресурсів, жодного дрейфу, ідеальна синхронізація. Якщо твоя робота займає занадто багато часу і переривання спрацьовує до того, як ти дійдеш до `HALT`, ти пропускаєш кадр. Цикл все одно працює (наступний `HALT` зловить наступне переривання), але гра падає до 25 fps для цього кадру. Пропускаєш стабільно — маєш 25 fps постійно. Пропускаєш сильно — 16.7 fps (кожен третій кадр). Гравець це помічає.

### Бюджет кадру: нагадування

Ми встановили числа в Розділі 1, але варто повторити їх у контексті гри:

| Машина | Тактів на кадр | Практичний бюджет |
|---------|-------------------|------------------|
| ZX Spectrum 48K | 69 888 | ~62 000 (після накладних витрат переривання) |
| ZX Spectrum 128K | 70 908 | ~63 000 |
| Pentagon 128 | 71 680 | ~64 000 |
| Agon Light 2 | ~368 640 | ~360 000 |

«Практичний бюджет» враховує обробник переривань, саму інструкцію `HALT` та накладні витрати на тайминг бордюру. На Spectrum у тебе приблизно 64 000 тактів корисного часу на кадр. На Agon — більше ніж у п'ять разів.

Як типова гра витрачає ці 64 000 тактів? Ось реалістичний розклад для платформера на Spectrum:

| Підсистема | Тактів | % бюджету |
|-----------|----------|-------------|
| Зчитування введення | ~500 | 0.8% |
| Оновлення сутностей (16 сутностей) | ~8 000 | 12.5% |
| Виявлення зіткнень | ~4 000 | 6.3% |
| Програвач музики (PT3) | ~5 000 | 7.8% |
| Рендеринг спрайтів (8 видимих) | ~24 000 | 37.5% |
| Оновлення фону/скролу | ~12 000 | 18.8% |
| Різне (HUD, стан) | ~3 000 | 4.7% |
| **Залишковий запас** | **~7 500** | **11.7%** |

Ці 11.7% запасу — твій страховий резерв. З'їш його — почнеш пропускати кадри на складних сценах. Техніка профілювання кольором бордюру з Розділу 1 — червоний для спрайтів, синій для музики, зелений для логіки — це те, як ти відстежуєш цей бюджет під час розробки. Використовуй постійно.

На Agon та сама ігрова логіка працює за мізерну частку бюджету. Оновлення сутностей, виявлення зіткнень та зчитування введення можуть споживати 15 000 тактів загалом — приблизно 4% кадру Agon. VDP обробляє рендеринг спрайтів на співпроцесорі ESP32, тому витрати на спрайти з боку CPU падають до накладних витрат VDU-команд. У тебе величезний простір для складнішого ШІ, більшої кількості сутностей або просто менше стресу.

![Game loop architecture](illustrations/output/ch18_game_loop.png)

---

## 18.2 Ігровий скінченний автомат

Гра — це не один цикл, а декілька. Титульний екран має свій цикл (анімувати логотип, чекати натискання клавіші). Меню має свій цикл (підсвічувати опції, зчитувати введення). Ігровий цикл — це те, що ми описали вище. Екран паузи заморожує ігровий цикл і запускає простіший. Екран кінця гри — ще один.

Найчистіший спосіб організувати це — **скінченний автомат**: змінна, що відстежує, в якому стані перебуває гра, та таблиця адрес обробників — по одному на стан.

### Визначення станів

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

### Таблиця переходів

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

Головний цикл стає диспетчером, який читає поточний стан і переходить до відповідного обробника:

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

Інструкція `JP (HL)` — ключова. Вона не переходить за адресою, що *зберігається* за HL — вона переходить за адресою, що *міститься* в HL. Це непрямий перехід Z80, і він коштує лише 4 такти. Весь диспетчер — завантаження змінної стану, обчислення зміщення в таблиці, зчитування адреси обробника та перехід — займає 73 такти. Це мізер: приблизно 0.1% бюджету кадру.

Кожен обробник виконує свою логіку і потім переходить назад до `main_loop`:

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

### Чому не ланцюжок порівнянь?

У тебе може виникнути спокуса написати диспетчер так:

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

Це працює, але має дві проблеми. По-перше, вартість зростає лінійно: кожен додатковий стан додає `CP` (7T) і `JP Z` (10T), тому найгірший випадок — 17T на стан. При 5 станах ігровий стан (найпоширеніший випадок) може зайняти 51T, якщо це третє порівняння. Таблиця переходів займає 73T незалежно від того, який стан активний — це O(1), а не O(n).

По-друге, і що важливіше, таблиця переходів масштабується чисто. Додавання шостого стану (наприклад, STATE_SHOP) означає додати один запис `DW` до таблиці та одне визначення константи. Код диспетчера не змінюється взагалі. З ланцюжками порівнянь ти додаєш більше інструкцій до самого диспетчера, і порядок починає впливати на продуктивність. Табличний підхід і швидший у загальному випадку, і чистіший для підтримки.

### Переходи між станами

Переходи між станами відбуваються записом нового значення в `game_state`. Зазвичай ти також викликаєш підпрограму ініціалізації для нового стану:

```z80
; Transition: Game -> Game Over
game_over_transition:
    ld   a, STATE_GAMEOVER
    ld   (game_state), a
    call init_gameover       ; set up game over screen, save score
    ret
```

Тримай переходи явними і централізованими. Поширений баг у іграх на Z80 — перехід стану, який забуває ініціалізувати дані нового стану: екран кінця гри показує сміття, бо ніхто не очистив екран і не скинув лічильник анімації. Кожен стан повинен мати підпрограму `init_`, яку викликає перехід.

---

## 18.3 Введення: зчитування гравця

### Клавіатура ZX Spectrum

Клавіатура Spectrum зчитується через порт `$FE`. Клавіатура підключена як матриця з 8 напіврядів, кожен обирається встановленням біта в нуль у старшому байті адреси порту. Зчитування порту `$FE` з конкретним старшим байтом повертає стан цього напівряду: 5 біт, по одному на клавішу, де 0 означає натиснуту, а 1 — ненатиснуту.

Карта напіврядів:

| Старший байт | Клавіші (біт 0 до біт 4) |
|-----------|----------------------|
| $FE (біт 0 низький) | SHIFT, Z, X, C, V |
| $FD (біт 1 низький) | A, S, D, F, G |
| $FB (біт 2 низький) | Q, W, E, R, T |
| $F7 (біт 3 низький) | 1, 2, 3, 4, 5 |
| $EF (біт 4 низький) | 0, 9, 8, 7, 6 |
| $DF (біт 5 низький) | P, O, I, U, Y |
| $BF (біт 6 низький) | ENTER, L, K, J, H |
| $7F (біт 7 низький) | SPACE, SYMSHIFT, M, N, B |

Стандартне ігрове керування — Q/A/O/P для верх/низ/ліво/право та SPACE для стрільби — охоплює три напівряди. Ось підпрограма, що зчитує їх і пакує результат в один байт:

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

При приблизно 220 тактах у найгіршому випадку зчитування введення — тривіальна частина бюджету кадру. Навіть на Spectrum ти міг би зчитувати клавіатуру десять разів на кадр і ледь помітити це.

### Kempston Joystick

Інтерфейс Kempston ще простіший. Одне зчитування порту повертає всі п'ять напрямків плюс стрільбу:

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

Зверни увагу на зручний збіг: бітова розкладка Kempston точно збігається з нашими визначеннями прапорців `INPUT_*`. Це не випадковість — інтерфейс Kempston був розроблений з урахуванням цього стандарту, і більшість ігор для Spectrum використовують таку саму бітову нумерацію. Якщо ти підтримуєш і клавіатуру, і джойстик, ти можеш об'єднати результати через OR:

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

Тепер решта твого коду лише перевіряє `input_flags` і не цікавиться, звідки прийшло введення — від клавіатури чи джойстика.

### Визначення фронтів: натискання проти утримання

Для деяких дій — постріл кулею, відкриття меню — ти хочеш реагувати на подію *натискання*, а не на утримуваний стан. Якщо ти перевіряєш `bit INPUT_FIRE, a` кожен кадр, гравець стріляє кулею кожну 1/50 секунди, поки тримає кнопку. Це може бути навмисним для швидкого вогню, але для одноразової зброї чи вибору в меню тобі потрібне визначення фронту.

Техніка: зберігай введення попереднього кадру поряд з поточним і виконуй XOR, щоб знайти біти, що змінилися:

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

Тепер `input_pressed` має одиничний біт лише для кнопок, які *не були* натиснуті минулого кадру, але *натиснуті* цього. Використовуй `input_flags` для безперервних дій (рух) і `input_pressed` для одноразових дій (стрільба, стрибок, вибір у меню).

### Agon Light 2: PS/2-клавіатура через MOS

Agon зчитує свою PS/2-клавіатуру через API MOS (Machine Operating System). eZ80 не сканує клавіатурну матрицю безпосередньо — натомість співпроцесор ESP32 VDP обробляє апаратну частину клавіатури і передає події натискань на eZ80 через спільний буфер.

Системна змінна MOS `sysvar_keyascii` (за адресою $0800 + зміщення) містить ASCII-код останньої натиснутої клавіші, або 0, якщо жодна клавіша не натиснута. Для ігрового керування ти зазвичай опитуєш цю змінну або використовуєш виклики API MOS `waitvblank` / keyboard:

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

Agon також підтримує зчитування стану окремих клавіш через VDU-команди (VDU 23,0,$01,keycode), які повертають, чи утримується конкретна клавіша. Це ближче до підходу з напіврядами Spectrum і краще підходить для ігор, що потребують одночасного визначення декількох клавіш. API MOS обробляє протокол PS/2, трансляцію скан-кодів та автоповтор — тобі не потрібно хвилюватися про жодне з цього.

---

## 18.4 Структура сутності

Ігрова сутність — це все, що рухається, анімується, взаємодіє або потребує покадрового оновлення: персонаж гравця, вороги, кулі, вибухи, спливаючі числа очок, бонуси. На Z80 ми представляємо кожну сутність як блок байтів фіксованого розміру в пам'яті.

### Розкладка структури

Ось структура сутності, яку ми будемо використовувати в усіх розділах про розробку ігор:

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

Бітові прапорці в байті `flags`:

```
Bit 0: ACTIVE      -- entity is alive and should be updated/rendered
Bit 1: VISIBLE     -- entity should be rendered (active but invisible = logic only)
Bit 2: COLLIDABLE  -- entity participates in collision detection
Bit 3: FACING_LEFT -- horizontal facing direction
Bit 4: INVINCIBLE  -- temporary invulnerability (player after being hit)
Bit 5: ON_GROUND   -- entity is standing on solid ground (set by physics)
Bit 6-7: reserved
```

### Чому 10 байтів?

Десять байтів — це обдуманий вибір. Достатньо малий, щоб 16 сутностей займали лише 160 байтів — тривіально в термінах пам'яті. Що важливіше, множення індексу сутності на 10 для знаходження зміщення є простим на Z80:

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

Множення на 10 використовує стандартну декомпозицію: 10 = 8 + 2. Ми обчислюємо index * 2, зберігаємо його, обчислюємо index * 8 і додаємо їх. Жодної інструкції множення не потрібно — лише зсуви (ADD HL,HL) і додавання.

Якби ти обрав степінь двійки, як 8 або 16 байтів на сутність, обчислення індексу було б ще простішим (три зсуви для 8, чотири для 16). Але 8 байтів — це занадто тісно: ти б втратив або швидкість, або здоров'я, а обидва потрібні. А 16 байтів витрачають 6 байтів на сутність на доповнення, що накопичується: 16 сутностей x 6 зайвих байтів = 96 байтів мертвого простору. На Spectrum кожен байт важливий. Десять байтів — це правильний розмір для даних, які нам насправді потрібні.

### Чому 16-бітний X, але 8-бітний Y?

Позиція X — 16-бітна з фіксованою точкою (формат 8.8): старший байт — це піксельний стовпець (0-255), а молодший — субпіксельна дробова частина для плавного руху. Це необхідно для ігор з горизонтальним скролінгом, де гравець рухається з дробовою піксельною швидкістю. Персонаж, що рухається зі швидкістю 1.5 піксель на кадр лише з цілочисельними координатами, чергував би кроки в 1 та 2 пікселі, створюючи видимий ривок. З фіксованою точкою 8.8 рух плавний: додавай 0x0180 до X кожен кадр, і піксельна позиція просувається 1, 2, 1, 2, 1, 2... у патерні, який око сприймає як рівномірні 1.5 піксель на кадр.

Позиція Y лише 8 біт, тому що екран Spectrum має висоту 192 піксель — одного байта достатньо для всього діапазону. Для гри з вертикальним скролінгом ти б розширив Y до 16-бітної фіксованої точки ціною одного додаткового байта на сутність.

### Система фіксованої точки 8.8

Арифметика з фіксованою точкою була представлена в Розділі 4. Ось коротке нагадування, як вона застосовується до руху сутностей:

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

Краса фіксованої точки: додавання і віднімання — це просто звичайні 16-бітні операції `ADD HL,DE`. Жодної спеціальної обробки, жодних таблиць підстановки, жодного множення. Дробова точність з'являється автоматично, бо ми переносимо субпіксельні біти разом.

---

## 18.5 Масив сутностей

Сутності живуть у статично виділеному масиві. Жодного динамічного виділення пам'яті, жодних зв'язаних списків, жодної купи. Статичні масиви — стандартний підхід на Z80 з вагомої причини: вони швидкі, передбачувані і не можуть фрагментуватися.

```z80
; Entity array: 16 entities, 10 bytes each = 160 bytes
MAX_ENTITIES    EQU  16
ENTITY_SIZE     EQU  10

entity_array:
    DS   MAX_ENTITIES * ENTITY_SIZE    ; 160 bytes, zeroed at init
```

### Розподіл слотів сутностей

Слот 0 завжди для гравця. Слоти 1-8 — для ворогів. Слоти 9-15 — для снарядів та ефектів (кулі, вибухи, спливаючі очки). Це фіксоване розбиття спрощує код: коли тобі потрібно ітерувати ворогів для ШІ, ти ітеруєш слоти 1-8. Коли потрібно створити кулю, ти шукаєш у слотах 9-15. Гравець завжди за відомою адресою.

```z80
; Fixed slot assignments
SLOT_PLAYER      EQU  0
SLOT_ENEMY_FIRST EQU  1
SLOT_ENEMY_LAST  EQU  8
SLOT_PROJ_FIRST  EQU  9
SLOT_PROJ_LAST   EQU  15
```

### Ітерація сутностей

Основний цикл оновлення проходить через кожен слот сутності, перевіряє прапорець ACTIVE і викликає відповідний обробник оновлення:

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

Тут використовується IX як вказівник на сутність, що зручно, бо IX-індексована адресація дозволяє звертатися до будь-якого поля за зміщенням: `(IX+0)` — це X молодший, `(IX+2)` — Y, `(IX+3)` — тип і так далі. Недолік IX — вартість: кожне `LD A,(IX+n)` займає 19 тактів проти 7 для `LD A,(HL)`. Для циклу оновлення сутностей, що працює 16 разів на кадр, ці накладні витрати прийнятні. Для внутрішнього циклу рендерингу, де ти звертаєшся до даних сутності тисячі разів на кадр, ти б спочатку скопіював потрібні поля в регістри.

### Диспетчеризація оновлення за типом

Кожен тип сутності має свій обробник оновлення. Ми використовуємо ту саму техніку таблиці переходів, що й для скінченного автомату гри:

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

Кожен обробник отримує IX, що вказує на сутність, і може звертатися до всіх полів через індексовану адресацію. Коли обробник виконує `RET`, він повертається до циклу оновлення сутностей, який просувається до наступного слоту.

### Обробник оновлення гравця

Ось типове оновлення гравця — зчитай прапорці введення, застосуй рух, оновити анімацію:

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

Це навмисно просто. Розділ 19 додасть гравітацію, стрибки та реакцію на зіткнення. Поки що суть — у *структурі*: вказівник на сутність в IX, поля доступні за зміщенням, прапорці введення керують зміною стану, лічильник анімації тікає.

---

## 18.6 Пул об'єктів

Кулі, вибухи та ефекти частинок — тимчасові. Куля існує частку секунди, перш ніж щось влучить або вийде за межі екрана. Вибух анімується 8-16 кадрів і зникає. Ти міг би створювати їх динамічно, але на Z80 «динамічно» означає шукати вільну пам'ять, керувати виділенням та ризикувати фрагментацією. Натомість ми використовуємо **пул об'єктів**: фіксований набір слотів, в які сутності активуються та з яких деактивуються.

У нас вже є пул — це масив сутностей. Слоти 9-15 — це пул снарядів/ефектів. Створення кулі означає знайти неактивний слот у цьому діапазоні та заповнити його. Знищення кулі означає очистити її прапорець ACTIVE.

### Створення кулі

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

### Деактивація сутності

Коли куля виходить за межі екрана або вибух завершує свою анімацію, деактивація — це одна інструкція:

```z80
; Deactivate entity at IX
deactivate_entity:
    ld   (ix + 9), 0        ; 19T  clear all flags (ACTIVE=0)
    ret
```

Ось і все. Наступний кадр цикл оновлення бачить ACTIVE=0 і пропускає слот. Слот тепер доступний для наступного виклику `spawn_bullet` для повторного використання.

### Обробник оновлення кулі

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

### Розміри пулу

Сім слотів для снарядів (індекси 9-15) може здатися обмеженим. На практиці це більш ніж достатньо для більшості ігор на Spectrum. Зверни увагу: куля, що перетинає всю ширину екрана (256 пікселів) зі швидкістю 4 пікселі на кадр, потребує 64 кадри — більше секунди. Якщо гравець стріляє раз на 8 кадрів (швидкий темп стрільби), одночасно може існувати щонайбільше 8 куль. Сім слотів з поодинокими невдачами створення (куля просто не виходить у цьому кадрі) виглядає природно, а не як баг. Гравець навряд чи помітить пропущену кулю на межі свого темпу стрільби.

Якщо тобі потрібно більше, розшир масив сутностей. Але будь уважний до вартості: кожна додаткова сутність додає ~160 тактів до найгіршого циклу оновлення (коли активна) і ~50 тактів навіть коли неактивна (перевірка прапорця ACTIVE і просування IX все одно виконуються). Тридцять дві сутності з усіма активними споживали б приблизно 16 000 тактів лише в циклі оновлення — чверть бюджету кадру до того, як ти відрендерив хоча б один піксель.

На Agon ти можеш собі дозволити більші пули. При 360 000 тактах на кадр і апаратному рендерингу спрайтів 64 або навіть 128 сутностей цілком можливі.

---

## 18.7 Сутності вибухів та ефектів

Вибухи, спливаючі очки та ефекти частинок використовують ті самі слоти сутностей, що й кулі. Різниця — в їхніх обробниках оновлення: вони проходять через послідовність кадрів анімації, а потім самознищуються.

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

Для створення вибуху при загибелі ворога:

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

Патерн завжди однаковий: знайти вільний слот, заповнити структуру, встановити прапорці. Обробник оновлення виконує специфічну для типу роботу. Деактивація очищує прапорці. Слот повторно використовується наступного разу, коли щось потрібно створити. Це весь життєвий цикл динамічного об'єкта на Z80 — жодного алокатора, жодного збирача сміття, жодного списку вільних блоків. Просто масив і прапорець.

---

## 18.8 Збираємо все разом: ігровий скелет

Ось повний ігровий скелет, що зв'язує все воєдино. Це компільований фреймворк з усіма частинами з'єднаними: скінченний автомат, введення, система сутностей та головний цикл.

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

Цей скелет компілюється, запускається і робить щось видиме: кольорові блоки рухаються по сітці атрибутів. Блок гравця реагує на керування QAOP. Натискання SPACE створює кулі, що летять через екран. Вороги відбиваються від країв екрана. Коли куля виходить за екран, її слот звільняється для наступного пострілу.

Це некрасиво — блоки атрибутів замість спрайтів, без скролінгу, без звуку. Але архітектура завершена. Кожна частина з цього розділу присутня і з'єднана: головний цикл на основі HALT, диспетчер скінченного автомату, зчитувач введення з визначенням фронтів, масив сутностей з обробниками оновлення за типами та пул об'єктів для снарядів. Розділи 16 і 17 забезпечують рендеринг. Розділ 19 забезпечує фізику та зіткнення. Розділ 11 забезпечує музику. Цей скелет — місце, куди все підключається.

---

## 18.9 Agon Light 2: та сама архітектура, більше простору

Agon Light 2 використовує ту саму фундаментальну структуру ігрового циклу. eZ80 виконує Z80-код нативно (у Z80-сумісному режимі або режимі ADL), тому головний цикл на основі HALT, скінченний автомат, система сутностей та логіка введення — все це переноситься безпосередньо.

Основні відмінності:

**Синхронізація кадрів.** Agon використовує виклик `waitvblank` MOS (RST $08, функція $1E) замість `HALT` для синхронізації кадрів. VDP генерує сигнал вертикального гасіння, і API MOS надає до нього доступ.

**Введення.** Зчитування клавіатури проходить через системні змінні MOS, а не через пряме введення-виведення портів. Матриця напіврядів не існує — PS/2-клавіатуру обробляє ESP32 VDP. Абстрактний рівень введення, який ми побудували (все зводиться до `input_flags`), означає, що решті ігрового коду байдуже до різниці.

**Бюджет сутностей.** При ~360 000 тактах на кадр та апаратному рендерингу спрайтів цикл оновлення сутностей більше не є вузьким місцем. Ти міг би оновлювати 64 сутності зі складним ШІ і все одно використовувати менше 10% бюджету кадру. Обмежуючий фактор на Agon — кількість VDP-спрайтів на рядок розгортки (типово 16-32 апаратних спрайти видимих на одному рядку), а не час CPU.

**Рендеринг.** VDP Agon обробляє рендеринг спрайтів. Замість ручного переносу пікселів в екранну пам'ять (шість методів з Розділу 16) ти надсилаєш VDU-команди для позиціонування апаратних спрайтів. Витрати CPU на спрайт падають з ~1 200 тактів (OR+AND blit на Spectrum) до ~50-100 тактів (відправка VDU-команди позиціонування). Це вивільняє величезний час CPU для ігрової логіки.

**Пам'ять.** Agon має 512 КБ плоскої пам'яті — без банків, без спірних областей. Твій масив сутностей, таблиці підстановки, дані спрайтів, карти рівнів та музика можуть співіснувати без гімнастики перемикання банків, описаної в Розділі 15 для Spectrum 128K.

Практичний висновок: на Agon архітектура цього розділу масштабується без зусиль. Більше сутностей, складніші скінченні автомати, більше ШІ-логіки — ніщо з цього не загрожує бюджету кадру. Дисципліна підрахунку кожного такту все ще має значення (це добра інженерія), але обмеження, що змушують болісно вибирати компроміси на Spectrum, просто не діють.

---

## 18.10 Проєктні рішення та компроміси

### Фіксована проти змінної частоти кадрів

Головний цикл цього розділу припускає фіксовану частоту 50 fps: зроби все за один кадр або пропусти. Альтернатива — змінний крок часу: виміряй, скільки зайняв кадр, і масштабуй весь рух на дельту часу. Змінні кроки часу стандартні в сучасних ігрових рушіях, але додають складності на Z80 — тобі потрібен таймер кадрів, множення на дельту в кожному обчисленні руху та обережна обробка стабільності фізики при змінних частотах.

Для ігор на Spectrum фіксовані 50 fps — майже завжди правильний вибір. Апаратура детермінована, бюджет кадру передбачуваний, і простота фізики з фіксованим кроком (все рухається на сталі величини кожен кадр) усуває цілий клас багів. Якщо твоя гра падає нижче 50 fps, відповідь — оптимізувати, поки не перестане, а не додавати змінний крок часу.

На Agon, з більшим бюджетом, тобі ще менше потрібне змінне хронометрування. Зафіксуй частоту кадрів на 50 або 60 fps і тримай життя простим.

### Розмір сутності: компактний проти щедрий

Наша 10-байтна структура сутності — компактна. Деякі комерційні ігри для Spectrum використовували 16 або навіть 32 байти на сутність, зберігаючи додаткові поля: попередня позиція (для стирання брудних прямокутників), адреса спрайту, розміри зони зіткнення, таймер ШІ тощо.

Компроміс — швидкість ітерації проти доступу до полів. Наш масив з 16 сутностей займає 160 байтів, і повний цикл оновлення працює за ~8 000 тактів. 32-байтна структура з 16 сутностями займає 512 байтів (все ще мало), але накладні витрати ітерації зростають, бо IX просувається на 32 з кожним кроком, а індексовані звернення до полів з великими зміщеннями на кшталт `(IX+28)` коштують ті самі 19 тактів, але їх складніше відстежувати.

Якщо тобі потрібно більше даних на сутність, розглянь розщеплення структури: компактний «гарячий» масив (позиція, тип, прапорці — поля, що зчитуються кожен кадр) і паралельний «холодний» масив (адреса спрайту, стан ШІ, значення очок — поля, що зчитуються лише за потреби). Це той самий компроміс «структура масивів проти масиву структур», з яким стикаються сучасні ігрові рушії, застосований у масштабі Z80.

### Коли використовувати HL замість IX

IX-індексована адресація зручна, але дорога: 19 тактів на звернення проти 7 для `(HL)`. У циклі оновлення (що викликається 16 разів на кадр) надлишок IX прийнятний — 16 x 12 зайвих тактів на звернення = 192 такти, мізер.

Але в циклі рендерингу, де ти можеш звертатися до 4-6 полів сутності для кожного з 8 видимих спрайтів, вартість накопичується. Техніка: на початку проходу рендерингу кожної сутності скопіюй потрібні поля в регістри:

```z80
    ; Copy entity fields to registers for fast rendering
    ld   l, (ix + 0)        ; 19T  X lo
    ld   h, (ix + 1)        ; 19T  X hi
    ld   c, (ix + 2)        ; 19T  Y
    ld   a, (ix + 5)        ; 19T  anim_frame
    ; Now render using H (X pixel), C (Y), A (frame)
    ; All subsequent accesses are register-to-register: 4T each
```

Чотири звернення IX по 19T = 76T наперед, а далі вся підпрограма рендерингу використовує 4T регістрові звернення замість 19T IX-звернень. Якщо підпрограма рендерингу звертається до цих полів 10 разів, ти економиш (19-4) x 10 - 76 = 74 такти на сутність. Небагато, але при 8 сутностях на кадр це 592 такти — достатньо, щоб намалювати ще половину спрайту.

---

## Підсумок

- **Ігровий цикл** — це `HALT -> Введення -> Оновлення -> Рендер -> повтор`. Інструкція `HALT` синхронізується з перериванням кадру, даючи тобі рівно один кадр тактів (приблизно 64 000 на Pentagon, 360 000 на Agon).

- **Скінченний автомат** з таблицею переходів вказівників на обробники (`DW state_title`, `DW state_game` тощо) організовує потік від титульного екрана через геймплей до кінця гри. Диспетчеризація коштує 73 такти незалежно від кількості станів — сталий час, чисте масштабування.

- **Зчитування введення** на Spectrum використовує `IN A,(C)` для опитування напіврядів клавіатури через порт `$FE`. П'ять клавіш (QAOP + SPACE) коштують приблизно 220 тактів. Kempston-джойстик — одне зчитування порту за 11T. Визначення фронтів (натискання проти утримання) використовує XOR між поточним та попереднім кадрами.

- **Структура сутності** — 10 байтів: X (16-бітна фіксована точка), Y, тип, стан, anim_frame, dx, dy, здоров'я, прапорці. Шістнадцять сутностей займають 160 байтів. Множення на 10 для перетворення індексу в адресу використовує декомпозицію 10 = 8 + 2.

- **Масив сутностей** статично виділений з фіксованим розподілом слотів: слот 0 для гравця, слоти 1-8 для ворогів, слоти 9-15 для снарядів та ефектів. Ітерація перевіряє прапорець ACTIVE і диспетчеризує до обробників за типом через другу таблицю переходів.

- **Пул об'єктів** — це сам масив сутностей. Створення встановлює поля та прапорець ACTIVE. Деактивація очищує прапорці. Пошук вільного слоту — лінійний скан відповідного діапазону слотів. Семи слотів для снарядів достатньо для типових частот стрільби, без помітних для гравця пропусків створення.

- **IX-індексована адресація** зручна для доступу до полів сутності (19T на звернення), але дорога у внутрішніх циклах. Копіюй поля в регістри на початку рендерингу для 4T-доступу протягом усього процесу.

- Agon Light 2 використовує ту саму архітектуру з більшим запасом. MOS `waitvblank` замінює `HALT`, PS/2-клавіатура замінює сканування напіврядів, апаратні спрайти замінюють CPU-бліт. Цикл оновлення сутностей більше не є вузьким місцем.

- Практичний скелет цього розділу запускає скінченний автомат, 16 сутностей (1 гравець + 8 ворогів + 7 слотів для куль/ефектів), введення з визначенням фронтів, обробники оновлення за типами та мінімальний рендерер атрибутних блоків. Це шасі, до якого підключаються Розділи 16 (спрайти), 17 (скролінг), 19 (зіткнення) і 11 (звук).

---

## Спробуй сам

1. **Зібрати скелет.** Скомпілюй ігровий скелет з розділу 18.8 і запусти в емуляторі. Використовуй QAOP для руху блоку гравця та SPACE для стрільби. Спостерігай за рухом кольорових блоків. Додай профілювання кольором бордюру (Розділ 1), щоб побачити, скільки бюджету кадру використовується.

2. **Додати шостий стан.** Реалізуй STATE_SHOP між Меню та Грою. Екран магазину повинен відображати три предмети і дозволяти гравцю вибрати один за допомогою ВГОРУ/ВНИЗ та FIRE. Це вправа на скінченний автомат — додай константу, запис у таблицю, обробник та логіку переходу.

3. **Розширити кількість сутностей.** Збільш MAX_ENTITIES до 32, додай 16 додаткових ворогів і виміряй вплив на бюджет кадру за допомогою профілювання бордюром. При якій кількості сутностей цикл оновлення починає загрожувати 50 fps?

4. **Реалізувати підтримку Kempston.** Додай зчитувач Kempston-джойстика і об'єднай його з клавіатурним введенням через OR. Протестуй в емуляторі, що підтримує емуляцію Kempston (Fuse: Options -> Joysticks -> Kempston).

5. **Розділити гарячі та холодні дані.** Створи другий «холодний» масив з 4 байтами на сутність (адреса спрайту, таймер ШІ, стан ШІ, значення очок). Зміни цикл оновлення так, щоб звертатися до холодних даних лише коли тип сутності цього потребує (вороги для ШІ, не кулі). Виміряй економію в тактах.

---

*Далі: Розділ 19 — Зіткнення, фізика та ШІ ворогів. Ми додамо AABB-виявлення зіткнень, гравітацію, стрибки та чотири патерни поведінки ворогів до скелету з цього розділу.*

---

> **Джерела:** матриця клавіатури ZX Spectrum та розкладка портів з технічної документації Sinclair Research; специфікація інтерфейсу Kempston joystick; техніки арифметики з фіксованою точкою з Розділу 4 (Dark/X-Trade, Spectrum Expert #01, 1997); профілювання кольором бордюру з Розділу 1; методи рендерингу спрайтів з Розділу 16; інтеграція музики AY з Розділу 11; документація API MOS Agon Light 2 (Bernardo Kastrup, agon-light.com)
