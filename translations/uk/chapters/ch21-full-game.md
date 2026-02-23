# Розділ 21: Повна гра -- ZX Spectrum 128K

> *"Єдиний спосіб дізнатися, чи працює твій рушій, — випустити гру."*

---

У тебе є спрайти (Розділ 16). У тебе є скролінг (Розділ 17). У тебе є ігровий цикл та система сутностей (Розділ 18). У тебе є зіткнення, фізика та ШІ ворогів (Розділ 19). У тебе є музика AY та звукові ефекти (Розділ 11). У тебе є стиснення (Розділ 14). У тебе є 128 КБ банкової пам'яті, і ти знаєш, як адресувати кожен її байт (Розділ 15).

Тепер тобі треба скласти все це в єдиний двійковий файл, що завантажується з касети, показує екран завантаження, представляє меню, проводить п'ять рівнів горизонтального платформера з чотирма типами ворогів і босом, відстежує рекорди і вміщується у файл `.tap`.

Це розділ про інтеграцію. Нових технік тут не з'являється. Натомість ми стикаємося з проблемами, які виникають лише тоді, коли всі підсистеми мають співіснувати: конфлікти пам'яті між графічними банками та кодом, бюджети кадру, що переповнюються, коли скролінг, спрайти, музика та ШІ одночасно вимагають свою частку, системи збірки, що мають координувати десяток кроків конвертації даних, і тисяча дрібних рішень про те, що куди класти в 128 КБ банкової пам'яті.

Гра, яку ми будуємо, називається *Ironclaw* -- горизонтальний платформер на п'ять рівнів, де механічний кіт проходить серію дедалі ворожіших заводських поверхів. Жанр обраний навмисно: горизонтальні платформери вимагають усіх підсистем одночасно і не залишають місця, де сховатися. Якщо скролінг заїкається — ти це бачиш. Якщо рендеринг спрайтів не вміщується в кадр — ти це відчуваєш. Якщо виявлення зіткнень дає збій — гравець провалюється крізь підлогу. Платформер — це найскладніший інтеграційний тест, з яким може зіткнутися рушій гри на Z80.

---

## 21.1 Архітектура проекту

Перш ніж написати хоча б один рядок Z80, тобі потрібна структура каталогів, що масштабується. Гра на 128К з п'ятьма рівнями, тайлсетом, листами спрайтів, музичною партитурою та звуковими ефектами генерує десятки файлів даних. Якщо ти не організуєш їх з самого початку — потонеш.

### Структура каталогів

```
ironclaw/
  src/
    main.a80           -- точка входу, перемикання банків, скінченний автомат
    render.a80          -- тайловий рендерер, рушій скролінгу
    sprites.a80         -- процедури малювання спрайтів (OR+AND з маскою)
    entities.a80        -- оновлення сутностей, створення, знищення
    physics.a80         -- гравітація, тертя, стрибок, реакція на зіткнення
    collisions.a80      -- AABB та тайлові перевірки зіткнень
    ai.a80              -- FSM ворогів: патруль, переслідування, атака, відступ, смерть
    player.a80          -- введення гравця, стан, анімація
    hud.a80             -- рахунок, життя, панель статусу
    menu.a80            -- титульний екран, опції, рекорди
    loader.a80          -- екран завантаження, завантажувач касети/esxDOS
    music_driver.a80    -- PT3-програвач, обробник переривань
    sfx.a80             -- рушій звукових ефектів, захоплення каналу
    esxdos.a80          -- обгортки файлового вводу-виводу DivMMC
    banks.a80           -- макроси та утиліти перемикання банків
    defs.a80            -- константи, карта пам'яті, структура сутності
  data/
    levels/             -- тайлові карти рівнів (стиснуті)
    tiles/              -- графіка тайлсетів
    sprites/            -- листи спрайтів (попередньо зсунуті)
    music/              -- файли музики PT3
    sfx/                -- таблиці визначень SFX
    screens/            -- екран завантаження, титульний екран
  tools/
    png2tiles.py        -- конвертер тайлсетів із PNG
    png2sprites.py      -- конвертер листів спрайтів із PNG (генерує зсуви)
    map2bin.py          -- Tiled JSON/TMX у двійкову тайлову карту
    compress.py         -- обгортка навколо стиснення ZX0/Pletter
  build/                -- скомпільований вивід (gitignored)
  Makefile              -- система збірки
```

Кожен файл вихідного коду зосереджений на одній підсистемі. Кожен файл даних проходить через конвеєр конвертації, перш ніж потрапити до асемблера. Каталог `tools/` містить Python-скрипти, що конвертують формати, зручні для художника (PNG-зображення, карти редактора Tiled), у двійкові дані, готові для асемблера.

### Система збірки

Makefile — це хребет проекту. Він повинен:

1. Конвертувати всю графіку з PNG у двійкові дані тайлів/спрайтів
2. Конвертувати карти рівнів із формату Tiled у двійкові тайлові карти
3. Стиснути дані рівнів, графічні банки та музику відповідним пакувальником
4. Зібрати всі файли вихідного коду в єдиний двійковий файл
5. Згенерувати фінальний файл `.tap` з правильним завантажувачем

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

Ключова ідея — конвеєр даних. Художник експортує PNG-тайлсет з Aseprite. Скрипт `png2tiles.py` нарізає його на тайли 8x8 або 16x16, конвертує кожен у черезрядковий піксельний формат Spectrum і записує двійковий блоб. Дизайнер рівнів експортує карту `.tmx` з Tiled. Скрипт `map2bin.py` витягує індекси тайлів і записує компактну двійкову тайлову карту. Пакувальник стискає кожен блоб. І лише тоді асемблер через `INCBIN` включає результат у відповідний банк пам'яті.

Цей конвеєр означає, що вміст гри завжди в редагованій формі (PNG, TMX), а система збірки обробляє кожну конвертацію автоматично. Зміни тайл у PNG, набери `make` — і новий тайл з'явиться у грі.

---

## 21.2 Карта пам'яті: розподіл банків 128К

ZX Spectrum 128K має вісім банків оперативної пам'яті по 16 КБ, пронумерованих від 0 до 7. У будь-який момент процесор бачить 64-КБ адресний простір:

```
$0000-$3FFF   ROM (16KB) -- BASIC або ROM редактора 128К
$4000-$7FFF   Банк 5 (завжди) -- екранна пам'ять (звичайний екран)
$8000-$BFFF   Банк 2 (завжди) -- зазвичай код
$C000-$FFFF   Перемикається -- банки 0-7, обрані через порт $7FFD
```

Банки 5 і 2 жорстко прив'язані до `$4000` та `$8000` відповідно. Лише верхнє 16-КБ вікно (`$C000-$FFFF`) є перемикаємим. Регістр вибору банку на порту `$7FFD` також керує тим, який екран відображається (банк 5 чи банк 7), та яка сторінка ROM активна.

```z80
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

Критичне правило: **завжди зберігай останній запис у `$7FFD`** у тіньову змінну. Порт `$7FFD` працює лише на запис — ти не можеш прочитати поточний стан назад. Якщо тобі треба змінити один біт (скажімо, перемкнути екран), не порушуючи вибір банку, ти повинен прочитати свою тіньову змінну, модифікувати біт, записати результат і в порт, і в тіньову змінну.

### Розподіл банків Ironclaw

Ось як Ironclaw розподіляє свої 128 КБ між вісьмома банками:

```
Банк 0 ($C000)  -- Дані рівнів: тайлові карти для рівнів 1-2 (стиснуті)
                   Графіка тайлсету (стиснута)
                   Буфер розпакування

Банк 1 ($C000)  -- Дані рівнів: тайлові карти для рівнів 3-5 (стиснуті)
                   Дані та патерни рівня з босом
                   Таблиці появи ворогів

Банк 2 ($8000)  -- ФІКСОВАНИЙ: основний код гри
                   Логіка гравця, фізика, зіткнення
                   Процедури спрайтів, система сутностей
                   Скінченний автомат, HUD
                   ~ 14 КБ коду, 2 КБ таблиць/буферів

Банк 3 ($C000)  -- Графіка спрайтів (попередньо зсунута x4)
                   Гравець: 6 кадрів x 4 зсуви = 24 варіанти
                   Вороги: 4 типи x 4 кадри x 4 зсуви = 64 варіанти
                   Снаряди, частинки, бонуси
                   ~ 12 КБ загалом

Банк 4 ($C000)  -- Музика: дані пісень PT3 (титульна, рівні 1-3)
                   Код PT3-програвача (резидентна копія)

Банк 5 ($4000)  -- ФІКСОВАНИЙ: звичайний екран
                   Піксельні дані $4000-$57FF (6 144 байти)
                   Атрибути $5800-$5AFF (768 байтів)
                   Залишок ~9 КБ: обробник переривань, екранні буфери

Банк 6 ($C000)  -- Музика: дані пісень PT3 (рівні 4-5, бос, game over)
                   Таблиці визначень SFX
                   Код рушія SFX

Банк 7 ($4000)  -- Тіньовий екран (для подвійної буферизації)
                   Також може використовуватися як 16 КБ сховище даних,
                   коли подвійна буферизація не активна
```

Кілька речей, на які варто звернути увагу в цьому розподілі:

**Код живе в банку 2 (фіксованому).** Оскільки банк 2 завжди відображений за адресами `$8000-$BFFF`, твій основний код гри завжди доступний. Тобі ніколи не треба підключати код — лише дані. Це виключає найнебезпечніший клас помилок банкування: виклик процедури, яка була відключена з адресного простору.

**Графіка спрайтів у банку 3, окремо від даних рівнів у банках 0-1.** Під час рендерингу кадру рендереру потрібні і графіка тайлів (для фону, що скролиться), і графіка спрайтів (для сутностей). Якби обидва були в одному перемикаємому банку, довелося б перемикати банки вперед-назад посеред рендерингу. Розмістивши їх в окремих банках, ти можеш підключити дані тайлів, відрендерити фон, потім підключити дані спрайтів і відрендерити всі сутності, з лише двома перемиканнями банків на кадр.

**Музика розділена між банками 4 та 6.** PT3-програвач працює всередині обробника переривань IM2, який спрацьовує раз на кадр. Обробник переривань повинен підключити музичний банк, оновити регістри AY і повернути банк, який використовував головний цикл. Розділення музики між двома банками означає, що обробник переривань повинен знати, який банк містить поточну пісню. Ми обробляємо це через змінну:

```z80
current_music_bank:
    db   4              ; bank 4 by default

im2_handler:
    push af
    push bc
    push de
    push hl
    push ix

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

    pop  ix
    pop  hl
    pop  de
    pop  bc
    pop  af
    ei
    reti
```

**Тіньовий екран у банку 7** доступний для подвійної буферизації під час оновлень скролінгу (як описано в Розділі 17). Коли ти не ведеш активну подвійну буферизацію — у меню, між рівнями, під час кат-сцен — банк 7 є 16 КБ вільного сховища. Ironclaw використовує його для зберігання розпакованої тайлової карти поточного рівня під час геймплею, вивільняючи перемикаємі банки для графіки та музики.

### Стек

Стек знаходиться у верхній частині адресного простору банку 2, зростаючи вниз від `$BFFF`. При ~14 КБ коду, що починається з `$8000`, стек має приблизно 2 КБ простору — цього більш ніж достатньо для звичайної глибини викликів, але потрібна пильність. Глибока рекурсія — не варіант. Якщо ти використовуєш стековий вивід спрайтів (метод PUSH з Розділу 16), пам'ятай, що ти позичаєш вказівник стеку і повинен зберегти та відновити його з вимкненими перериваннями.

---

## 21.3 Скінченний автомат

Гра — це не одна програма. Це послідовність режимів — титульний екран, меню, геймплей, пауза, кінець гри, рекорди — кожен зі своєю обробкою введення, своїм рендерингом та своєю логікою оновлення. Розділ 18 представив патерн скінченного автомата. Ось як Ironclaw реалізує його на верхньому рівні.

```z80
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

Кожен обробник стану повністю володіє кадром. Обробник геймплею запускає введення, фізику, ШІ, рендеринг та оновлення HUD. Обробник меню зчитує введення та малює меню. Обробник паузи просто чекає клавішу зняття паузи, показуючи накладку "PAUSED".

Переходи між станами відбуваються записом нового значення в `current_state`. Перехід з `STATE_GAMEPLAY` у `STATE_PAUSE` не потребує очищення — ігровий стан залишається недоторканим, і повернення до `STATE_GAMEPLAY` продовжує рівно з того місця, де ти зупинився. Але перехід з `STATE_GAMEOVER` у `STATE_HISCORE` вимагає перевірки, чи потрапляє рахунок гравця в таблицю, а перехід з `STATE_LEVELWIN` у `STATE_GAMEPLAY` вимагає завантаження та розпакування даних наступного рівня.

---

## 21.4 Кадр геймплею

Тут відбувається інтеграція. Під час `STATE_GAMEPLAY` кожен кадр повинен виконати наступне, по порядку:

```
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

На Pentagon з 71 680 тактами (T-states) на кадр це залишає 21 000-28 000 тактів запасу. Звучить комфортно, але це оманливо. Ці оцінки — середні. Коли чотири вороги на екрані, а гравець стрибає через прогалину з летючими снарядами, найгірший випадок може злетіти на 20-30% вище середнього. Твій запас — це твій запас міцності.

Порядок має значення. Введення повинно бути першим — тобі потрібен намір гравця перед симуляцією фізики. Фізика повинна передувати виявленню зіткнень — тобі потрібно знати, куди сутності хочуть рухатися, перш ніж перевіряти, чи можуть вони. Реакція на зіткнення повинна передувати рендерингу — тобі потрібні фінальні позиції перед малюванням чогось. І спрайти повинні малюватися після фону, бо спрайти накладаються на тайли.

### Зчитування введення

```z80
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

Зверни увагу, що зчитування клавіатури використовує `IN A,(C)` з адресою напіврядка в B. Кожна клавіша відображається на біт у результуючому байті. Об'єднання клавіатури та джойстика в один байт означає, що решті ігрової логіки байдуже, який пристрій введення використовує гравець.

### Рушій скролінгу

Скролінг — найдорожча операція в кадрі. Розділ 17 детально розглянув техніки; ось як вони інтегруються в гру.

Ironclaw використовує метод **комбінованого скролінгу**: скролінг з кроком у символ (стрибки по 8 пікселів) для основного вікна перегляду, з піксельним зміщенням (0-7) всередині поточного 8-піксельного вікна для плавного візуального руху. Коли піксельне зміщення досягає 8, вікно перегляду зсувається на один стовпець тайлів, а зміщення скидається до 0.

Вікно перегляду має ширину 30 символів (240 пікселів) і висоту 20 символів (160 пікселів), залишаючи місце для HUD висотою 2 символи зверху та знизу. Тайлова карта рівня зазвичай має ширину 256-512 тайлів і висоту 20 тайлів.

Коли вікно перегляду зсувається на один стовпець тайлів, рендерер повинен:

1. Скопіювати 29 стовпців поточного екрана на один символ ліворуч (або праворуч)
2. Намалювати щойно відкритий стовпець тайлів із тайлової карти

Копіювання стовпця — це ланцюжок LDIR: 20 рядків x 8 піксельних ліній x 29 байтів = 4 640 байтів по 21 такту (T-state) кожен = 97 440 тактів. Це більше, ніж весь кадр. Ось чому техніка тіньового екрану з Розділу 17 є необхідною.

```z80
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

Але навіть з подвійною буферизацією повне копіювання стовпця є дорогим. Ironclaw оптимізує це, розподіляючи роботу: під час плавного субтайлового скролінгу (піксельне зміщення 1-7) копіювання стовпця не відбувається — змінюється лише зміщення. Дороге копіювання стовпця відбувається лише на границях тайлів, приблизно кожні 4-8 кадрів залежно від швидкості гравця. Між цими піками рендеринг скролінгу практично безкоштовний.

Коли перетинається границя тайлу, копіювання стовпця можна розподілити між двома кадрами за допомогою подвійного буфера: кадр N малює верхню половину зсунутого екрана в задній буфер, кадр N+1 малює нижню половину та перемикає. Гравець бачить плавний скролінг, бо перемикання відбувається лише тоді, коли задній буфер готовий.

---

## 21.5 Інтеграція спрайтів

Ironclaw використовує спрайти з маскою OR+AND (Розділ 16, метод 2) для всіх ігрових сутностей. Це стандартна техніка: для кожного пікселя спрайта AND з байтом маски очищає фон, потім OR з даними спрайта встановлює пікселі.

Кожен спрайт 16x16 має чотири попередньо зсунуті копії (Розділ 16, метод 3), по одній для кожного 2-піксельного горизонтального вирівнювання. Це замінює зсув на піксель під час виконання на пошук у таблиці. Ціна: кожен кадр спрайта вимагає 4 варіанти x 16 ліній x 3 байти/лінія (2 байти даних + 1 байт маски, розширені до 3 байтів для обробки переповнення зсуву) = 192 байти. Але швидкість рендерингу знижується з ~1 500 тактів (T-states) до ~1 000 тактів на спрайт, і з 8-10 спрайтами на екрані ця економія накопичується.

Попередньо зсунуті дані спрайтів знаходяться в банку 3. Під час фази рендерингу спрайтів рендерер підключає банк 3, проходить по всіх активних сутностях і малює кожну:

```z80
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

### Відновлення фону (брудні прямокутники)

Перш ніж малювати спрайти на нових позиціях, ти повинен стерти їх зі старих позицій. Ironclaw використовує метод брудних прямокутників з Розділу 16: перед малюванням спрайта зберігає фон під ним у буфер. Перед наступним проходом рендерингу спрайтів відновлює збережені фони.

```z80
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

Вартість брудних прямокутників пропорційна кількості та розміру спрайтів. Для 8 сутностей розміром 16x16 пікселів (3 байти завширшки після зсуву) збереження та відновлення коштує приблизно 8 x 16 x 3 x 2 (збереження + відновлення) x ~10 тактів/байт = ~7 680 тактів (T-states). Недешево, але передбачувано.

---

## 21.6 Зіткнення, фізика та ШІ в контексті

Розділи 18 та 19 розглянули ці системи ізольовано. В інтегрованій грі головна складність — порядок: яка система запускається першою і які дані потрібні кожній від інших?

### Цикл фізика-зіткнення

Оновлення фізики повинне чергуватися з виявленням зіткнень. Патерн такий:

```
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

Горизонтальний та вертикальний рухи розділені, бо реакція на зіткнення повинна обробляти кожну вісь незалежно. Якщо ти рухаєшся по діагоналі й потрапляєш у кут, ти хочеш ковзати вздовж стіни по одній осі, зупиняючись по іншій. Перевірка обох осей одночасно призводить до помилок "залипання", коли гравець застряє на кутах.

Усі позиції використовують формат фіксованої точки 8.8 (Розділ 4): старший байт — це піксельна координата, молодший — дробова частина. Значення швидкості також 8.8. Це дає субпіксельну точність руху без жодного множення в основному циклі фізики — достатньо додавання та зсувів.

```z80
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

### Тайлове зіткнення

Перевірка тайлового зіткнення конвертує піксельну координату в індекс тайлу, потім шукає тип тайлу в карті зіткнень рівня:

```z80
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

Для Ironclaw ширина рівнів встановлена в 256 тайлів. Це не збіг — це робить множення рядка тривіальним (номер рядка стає старшим байтом зміщення). Рівень шириною 256 тайлів по 8 пікселів на тайл — це 2 048 пікселів, приблизно 8.5 екранів завширшки. Для довших рівнів можна використати ширину 512 тайлів (множити рядок на 2 через `SLA E : RL D`), хоча це коштує кілька додаткових тактів на пошук.

### ШІ ворогів

Кожен тип ворога має скінченний автомат (Розділ 19). Стан зберігається в структурі сутності:

```z80
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

Чотири типи ворогів Ironclaw:

1. **Ходок (Walker)** -- Патрулює між двома точками. Коли гравець в межах 64 пікселів по горизонталі, переходить у стан Chase (йде до гравця). Переходить в Attack (контактна шкода) при зіткненні. Повертається до Patrol, коли гравець віддаляється або ворог досягає краю платформи.

2. **Літун (Flyer)** -- Вертикальний рух синусоїдою (використовуючи таблицю синусів з Розділу 4). Ігнорує тайлові зіткнення. Переслідує гравця горизонтально, коли той в межах досяжності. Скидає снаряди з інтервалами.

3. **Стрілець (Shooter)** -- Стаціонарний. Стріляє горизонтальним снарядом кожні N кадрів, коли гравець у зоні прямої видимості (той самий рядок тайлів, жодного суцільного тайлу між ними). Снаряд — окрема сутність, виділена з пулу сутностей.

4. **Бос (Boss)** -- Багатофазний скінченний автомат. Фаза 1: патрулювання платформи, стрільба розсіяними залпами. Фаза 2 (нижче 50% здоров'я): швидший рух, прицільні постріли, викликає ходоків. Фаза 3 (нижче 25% здоров'я): лють, безперервний вогонь, тряска екрана.

Ключова оптимізація з Розділу 19: ШІ запускається не кожен кадр. Оновлення ШІ ворогів розподіляються між кадрами за допомогою простого кругового перебору:

```z80
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

Це означає, що ШІ кожного ворога запускається раз на 3 кадри. При 50 fps це все ще ~17 оновлень ШІ на секунду на ворога — більш ніж достатньо для чуйної поведінки. Економія значна: якщо ШІ коштує ~500 тактів (T-states) на ворога, запуск всіх 8 ворогів кожен кадр коштує 4 000 тактів. Запуск 2-3 ворогів на кадр коштує 1 000-1 500 тактів. Фізика та виявлення зіткнень все ще працюють кожен кадр для плавного руху.

---

## 21.7 Інтеграція звуку

### Музика

PT3-програвач працює всередині обробника переривань IM2, як показано в секції 21.2. Програвач займає приблизно 1.5-2 КБ коду і виконується раз на кадр, витрачаючи ~2 500-3 500 тактів (T-states) залежно від складності поточного рядка патерну.

Кожен рівень має власний музичний трек. При переході між рівнями гра:

1. Згасає поточний трек (знижує гучність AY до 0 за 25 кадрів)
2. Підключає відповідний музичний банк (банк 4 або 6)
3. Ініціалізує PT3-програвач адресою початку нової пісні
4. Плавно збільшує гучність

Формат даних PT3 компактний — типовий музичний цикл гри на 2-3 хвилини стискається до 2-4 КБ з Pletter, саме тому два музичні банки (4 та 6) можуть вмістити всі шість треків (титульний, п'ять рівнів, бос, game over).

### Звукові ефекти

Звукові ефекти використовують систему захоплення каналу на основі пріоритетів з Розділу 11. Коли спрацьовує звуковий ефект (стрибок гравця, смерть ворога, постріл снаряда), рушій SFX тимчасово захоплює один канал AY, перекриваючи те, що музика робила на цьому каналі. Коли ефект завершується, канал повертається під контроль музики.

```z80
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

Оновлення SFX виконується всередині обробника переривань, після PT3-програвача. Якщо SFX активний, він перезаписує значення регістрів AY, які PT3-програвач щойно встановив для захопленого каналу. Це означає, що музика продовжує грати коректно на інших двох каналах, а захоплений канал відтворює звуковий ефект.

Визначення SFX — це процедурні таблиці, а не записаний звук. Кожен запис — послідовність покадрових значень регістрів:

```z80
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

Цей підхід використовує мізерну кількість пам'яті (8-20 байтів на ефект) і мізерну кількість процесорного часу (кілька десятків тактів на кадр для запису 3-4 значень регістрів AY).

---

## 21.8 Завантаження: касета та DivMMC

Гра для ZX Spectrum повинна якось завантажуватися. У 1980-х це означало касету. Сьогодні більшість користувачів мають DivMMC (або аналогічний) інтерфейс SD-карти з esxDOS. Ironclaw підтримує обидва варіанти.

### Файл .tap та завантажувач BASIC

Формат файлу `.tap` — це послідовність блоків даних, кожному з яких передує 2-байтна довжина та байт-прапорець. Завантажувач на BASIC (сам є блоком у .tap) використовує команди `LOAD "" CODE` для завантаження кожного блоку за правильною адресою.

Структура .tap для Ironclaw:

```
Block 0:  BASIC loader program (autorun line 10)
Block 1:  Loading screen (6912 bytes -> $4000)
Block 2:  Main code block (bank 2 content -> $8000)
Block 3:  Bank 0 data (level data + tiles, compressed)
Block 4:  Bank 1 data (more level data)
Block 5:  Bank 3 data (sprite graphics)
Block 6:  Bank 4 data (music tracks 1-3)
Block 7:  Bank 6 data (music tracks 4-6, SFX)
```

Завантажувач BASIC:

```basic
10 CLEAR 32767
20 LOAD "" SCREEN$
30 LOAD "" CODE
40 BORDER 0: PAPER 0: INK 0: CLS
50 RANDOMIZE USR 32768
```

Рядок 10 встановлює RAMTOP нижче `$8000`, захищаючи наш код від стеку BASIC. Рядок 20 завантажує екран завантаження прямо в екранну пам'ять (команда Spectrum `LOAD "" SCREEN$` робить це автоматично). Рядок 30 завантажує основний блок коду. Рядок 40 очищає екран. Рядок 50 переходить до нашого коду за адресою `$8000`.

Але це завантажує лише основний блок коду. Дані банків (блоки 3-7) повинен завантажити наш власний Z80-код, який підключає кожен банк і використовує процедуру завантаження з ROM:

```z80
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

### Завантаження esxDOS (DivMMC)

Для користувачів з DivMMC або подібним обладнанням завантаження з SD-карти є надзвичайно швидшим та надійнішим. API esxDOS надає файлові операції через `RST $08` з наступним номером функції:

```z80
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

Ironclaw визначає наявність esxDOS при запуску, перевіряючи сигнатуру DivMMC. Якщо вона присутня, всі дані завантажуються з файлів на SD-карті замість касети:

```z80
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

Код виявлення:

```z80
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

На практиці найбезпечніший метод виявлення перевіряє ідентифікаційний байт DivMMC за відомою адресою-пасткою або використовує відому безпечну комбінацію RST $08. Наведений вище метод працює, тому що якщо esxDOS відсутній, `RST $08` переходить до обробника помилок ROM, який для ROM 128K за адресою `$0008` є безпечним поверненням, що залишає carry скинутим. Виробничий код повинен використовувати більш надійну перевірку; наведений патерн ілюструє концепцію.

---

## 21.9 Екран завантаження, меню та рекорди

### Екран завантаження

Екран завантаження — це перше враження гравця. Він завантажується як `LOAD "" SCREEN$` у завантажувачі BASIC, тобто з'являється, поки завантажуються решта блоків даних з касети. На esxDOS завантаження досить швидке, і ти можеш захотіти відобразити екран протягом мінімального часу:

```z80
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

Сам екран завантаження — це стандартний файл екрана Spectrum: 6 144 байти піксельних даних з наступними 768 байтами атрибутів, загалом 6 912 байтів. Створи його в будь-якому Spectrum-сумісному графічному інструменті (ZX Paintbrush, SEViewer або Multipaint) або конвертуй сучасне зображення за допомогою інструменту дизерингу.

### Титульний екран і меню

Стан титульного екрана відображає логотип гри та анімований фон, потім переходить до меню при будь-якому натисканні клавіші:

```z80
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

Меню пропонує три варіанти: Start Game, Options, High Scores. Навігація — клавіші вгору/вниз, вибір — fire/enter. Меню — це простий скінченний автомат всередині обробника `STATE_MENU`:

```z80
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

### Рекорди

Рекорди зберігаються в таблиці з 10 записів в області даних банку 2:

```z80
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

Рахунок використовує BCD (двійково-десятковий код) — дві десяткові цифри на байт, три байти на рахунок, що дає максимум 999 999 очок. BCD краще за двійковий для відображення, бо конвертація 24-бітного двійкового числа в десяткове на Z80 вимагає дорогого ділення. З BCD інструкція `DAA` автоматично обробляє перенесення між цифрами, а друк вимагає лише маскування нібблів:

```z80
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

Коли гра завершується, код сканує таблицю рекордів, щоб перевірити, чи потрапляє рахунок гравця. Якщо так, гра переходить у `STATE_HISCORE` для введення імені (три символи, вибір клавішами вгору/вниз/fire).

На системах з esxDOS таблиця рекордів може бути збережена на SD-карту. На касетних системах рекорди зберігаються лише протягом поточної сесії.

---

## 21.10 Завантаження рівня та розпакування

Коли гравець починає рівень або завершує один, гра повинна:

1. Підключити банк з даними рівня (банк 0 для рівнів 1-2, банк 1 для рівнів 3-5)
2. Розпакувати тайлову карту в банк 7 (банк тіньового екрану, перепрофільований як буфер даних під час переходів між рівнями)
3. Розпакувати графіку тайлів у буфер у банку 2 або банку 0
4. Ініціалізувати масив сутностей з таблиці появи рівня
5. Скинути вікно перегляду на стартову позицію рівня
6. Скинути стан рушія скролінгу

```z80
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

Вибір пакувальника тут має значення. Дані рівня завантажуються раз на рівень (під час екрану переходу), тому швидкість розпакування не критична — ми можемо дозволити собі ~250 тактів (T-states) на байт у Exomizer заради найкращого ступеня стиснення. Але графіка тайлів може потребувати розпакування під час геймплею (якщо тайли банковані), тому ~69 тактів на байт у Pletter є переважними.

Як обговорювалося в Розділі 14, код розпаковувача сам по собі займає пам'ять. ZX0 з ~70 байтами ідеальний для проектів, де кодовий простір обмежений. Ironclaw включає і розпаковувач ZX0 (для даних рівнів при завантаженні), і розпаковувач Pletter (для потокових даних тайлів під час геймплею).

---

## 21.11 Профілювання з DeZog

Ти написав весь код. Він компілюється. Він працює. Гравець ходить, вороги патрулюють, тайли скроляться, музика грає. Але бюджет кадру переповнюється на рівні 3, де шість ворогів і три снаряди одночасно на екрані. Стрічка бордюру показує червону смугу, що виходить за межі видимої області екрана. Ти губиш кадри.

Саме тут DeZog доводить свою цінність у твоєму інструментарії.

### Що таке DeZog?

DeZog — це розширення VS Code, що надає повноцінне середовище зневадження для Z80-програм. Він підключається до емуляторів (ZEsarUX, CSpect або власний вбудований симулятор) і дає тобі:

- Точки зупину (за адресою, умовні, логування)
- Покрокове виконання (увійти, перешагнути, вийти)
- Спостереження за регістрами (всі регістри Z80, оновлення в реальному часі)
- Перегляд пам'яті (hex-дамп з живим оновленням)
- Вид дизасемблювання
- Стек викликів
- **Лічильник тактів (T-states)** — інструмент профілювання, який нам потрібен

### Робочий процес профілювання

Стрічка бордюру говорить тобі, *що* ти вийшов за бюджет. DeZog говорить тобі *де*.

**Крок 1: ізолюй повільний кадр.** Встанови умовну точку зупину на початку головного циклу, яка спрацьовує лише тоді, коли встановлено прапорець "переповнення кадру". Додай код для встановлення цього прапорця, коли кадр занадто довгий:

```z80
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

**Крок 2: виміряй вартість підсистем.** Лічильник тактів DeZog дозволяє виміряти точну вартість будь-якої ділянки коду. Постав курсор на початку `update_enemy_ai`, заміть значення лічильника тактів, перешагни через виклик і заміть нове значення. Різниця — точна вартість.

Систематичний прохід профілювання вимірює кожну підсистему:

```
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

Це середній випадок. Тепер профілюй найгірший — рівень 3, шість ворогів на екрані, гравець біля правого краю, що запускає скролінг:

```
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

Лише 9% запасу в найгіршому випадку. Це небезпечно мало. Ще один ворог або складний музичний патерн — і ти вийдеш за межі.

**Крок 3: знайди вузьке місце.** Таблиця профілювання робить його очевидним: скролінг + рендеринг тайлів споживають 41% кадру в найгіршому випадку. Рендеринг спрайтів — 19%. ШІ ворогів — 8%.

**Крок 4: оптимізуй вузьке місце.** Варіанти, приблизно в порядку впливу:

1. **Розподіли вартість скролінгу.** Замість рендерингу повного нового стовпця за один кадр, рендери половину в кадрі N і половину в кадрі N+1, використовуючи подвійний буфер (обговорено в секції 21.4). Це зменшує пік скролінгу з ~29 000 до ~15 000 тактів (T-states) на кадр.

2. **Використай скомпільовані спрайти для гравця.** Спрайт гравця завжди на екрані і завжди рендериться. Перехід від OR+AND з маскою (Розділ 16, метод 2) до скомпільованих спрайтів (метод 5) економить ~30% на малювання спрайта, але збільшує використання пам'яті. Для однієї часто малюваної сутності компроміс вартий.

3. **Зменш перемальовування спрайтів.** Якщо два вороги перекриваються, ти малюєш пікселі, які будуть перезаписані. Відсортуй сутності за координатою Y (від далекого до близького) та пропускай малювання повністю закритих спрайтів. Це допомагає в найгіршому випадку, коли сутності скупчуються.

4. **Підтягни ШІ.** Профілюй `run_entity_ai` для кожного типу ворога. Перевірка прямої видимості Стрільця (сканування стовпців тайлів на перешкоди) часто є найдорожчою операцією ШІ. Кешуй результат: перевіряй пряму видимість кожні 8 кадрів замість кожних 3.

Після оптимізації найгірший випадок знижується до ~58 000 тактів, залишаючи 19% запасу. Це комфортно.

### Конфігурація DeZog для Ironclaw

DeZog підключається до емулятора, що підтримує його протокол зневадження. Для розробки на ZX Spectrum 128K рекомендований ZEsarUX:

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

Налаштування `history` вмикає зворотне зневадження — ти можеш крокувати назад, щоб побачити, як ти дійшов до помилки. Це безцінно для відстеження глюків зіткнень, коли сутність телепортувалася крізь стіну три кадри тому.

---

## 21.12 Конвеєр даних у деталях

Перетворення даних з інструментів художника в гру часто є найбільш недооціненою частиною проекту. Конвеєр Ironclaw конвертує чотири види ресурсів:

### Тайлсети (PNG у піксельний формат Spectrum)

Художник малює тайли в Aseprite, Photoshop або будь-якому піксель-арт інструменті як PNG з індексованими кольорами. Тайли розташовані сіткою на одному листі. Скрипт конвертації:

1. Зчитує PNG, перевіряє, що це 1-бітне (чорно-біле) або індексоване з Spectrum-сумісними кольорами
2. Нарізає на тайли 8x8 або 16x16
3. Конвертує кожен тайл у черезрядковий піксельний формат Spectrum (де рядок 0 знаходиться зі зміщенням 0, рядок 1 зі зміщенням 256, а не 1 — відповідно до розкладки екрану)
4. За бажанням дедуплікує ідентичні тайли
5. Записує двійковий блоб та таблицю символів, що відображає ідентифікатори тайлів на зміщення

Для атрибутів кожен тайл також несе байт кольору (INK + PAPER + BRIGHT). Скрипт витягує це з палітри PNG і записує паралельну таблицю атрибутів.

### Листи спрайтів (PNG у попередньо зсунуті дані спрайтів)

Спрайти проходять аналогічний конвеєр, але з додатковим кроком: попередній зсув. Скрипт конвертації:

1. Зчитує PNG-лист спрайтів
2. Нарізає на окремі кадри
3. Генерує маску для кожного кадру (будь-який не-фоновий піксель дає 0 у масці, фон дає 1)
4. Для кожного кадру генерує 4 горизонтально зсунуті варіанти (0, 2, 4, 6 пікселів зміщення)
5. Кожен зсунутий варіант розширюється на один байт (2-байтний спрайт стає 3 байти завширшки для утримання переповнення зсуву)
6. Записує чергування байтів даних+маски для ефективного рендерингу

### Карти рівнів (Tiled JSON у двійкову тайлову карту)

Рівні проєктуються в Tiled — безкоштовному крос-платформному редакторі тайлових карт. Дизайнер розміщує тайли візуально, додає шари об'єктів для точок появи сутностей та тригерів, і експортує як JSON або TMX.

Скрипт конвертації:

1. Зчитує експорт Tiled
2. Витягує тайловий шар як плоский масив індексів тайлів
3. Витягує шар об'єктів для точок появи (позиції ворогів, старт гравця, розташування предметів)
4. Генерує карту зіткнень: для кожного тайлу шукає, чи є він суцільним, платформою, небезпекою або порожнім (на основі файлу властивостей тайлів)
5. Записує тайлову карту, карту зіткнень та таблицю появи як окремі двійкові файли

### Музика (Vortex Tracker II у PT3)

Музика створюється в Vortex Tracker II, який експортує безпосередньо у формат `.pt3`. Файл PT3 вбудовується в дані банку через `INCBIN`. Код PT3-програвача (широко доступний як Z80-асемблер з відкритим кодом, зазвичай 1.5-2 КБ) включається в музичний банк поруч з даними пісень.

### Зібрати все разом

Повний конвеєр конвертації для рівня:

```
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

Кожен крок автоматизований Makefile. Художник змінює тайл, набирає `make` — і бачить результат в емуляторі.

---

## 21.13 Формат релізу: збірка .tap

Фінальний результат — файл `.tap`. sjasmplus може генерувати `.tap` безпосередньо за допомогою директиви `SAVETAP`:

```z80
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

Точний синтаксис SAVETAP залежить від версії sjasmplus. Для ігор на 128К з банковими даними найчистіший підхід — генерувати знімок `.sna` (який зберігає стан усіх банків) для тестування в емуляторі, та `.tap` із завантажувачем BASIC та блоками машинного коду для розповсюдження.

### Тестування релізу

Перед публікацією протестуй щонайменше на трьох емуляторах:

1. **Fuse** — еталонний емулятор Spectrum, точний таймінг для оригінального обладнання
2. **Unreal Speccy** — таймінг Pentagon, стандарт демосцени, гарний зневаджувач
3. **ZEsarUX** — підтримує банкування 128К, емуляцію esxDOS, інтеграцію DeZog

І якщо можливо, протестуй на реальному обладнанні з DivMMC. Емулятори інколи відрізняються в граничних випадках таймінгу, і гра, що ідеально працює у Fuse, може губити кадри на реальному Spectrum через ефекти спірної пам'яті, які емулятор моделює трохи інакше.

---

## 21.14 Фінальне полірування

Різниця між працюючою грою та завершеною грою — це полірування. Ось контрольний список дрібних штрихів, які мають значення:

**Переходи екранів.** Не переходь між екранами миттєво. Просте затемнення (запис зменшуваної яскравості у всі атрибути протягом 8 кадрів) або витирання (очищення стовпців зліва направо протягом 16 кадрів) надає грі професійне відчуття. Вартість: мізерна — переходи відбуваються між кадрами геймплею.

**Анімація смерті.** Коли гравець гине, заморозь геймплей на 15 кадрів, мигни спрайтом гравця, перемикаючи його INK між кадрами, відтвори SFX смерті, потім відроди. Не телепортуй гравця назад на чекпоїнт без церемоній.

**Тряска екрана.** Коли бос б'є по землі або відбувається вибух, зсунь вікно перегляду на 1-2 пікселі на 4-6 кадрів. На Spectrum це можна імітувати, коригуючи зміщення скролінгу без фактичного переміщення тайлів. Це практично безкоштовно і додає величезний ефект присутності.

**Режим залучення (Attract mode).** Після 30 секунд на титульному екрані без введення запусти демонстраційне відтворення — запиши введення гравця під час тестового проходження і відтвори його. Так аркадні автомати приваблювали перехожих, і це працює для ігор Spectrum теж.

**Циклічна зміна кольорів.** Анімуй кольори тексту меню або логотипу, циклічно змінюючи атрибути через таблицю палітри. 4-байтний цикл атрибутів не коштує практично нічого процесорного часу і робить статичні екрани живими.

**Фільтрація дребезгу введення.** Ігноруй натискання клавіш тривалістю менше 2 кадрів. Без фільтрації дребезгу курсор меню буде проскакувати повз пункти, бо клавіша утримувалася протягом кількох кадрів. Простий лічильник кадрів на клавішу виправляє це:

```z80
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

## Підсумок

- **Структура проекту має значення.** Розділяй файли вихідного коду за підсистемами, файли даних за типами. Використовуй Makefile для автоматизації повного конвеєра від PNG/TMX до `.tap`.

- **Ретельно плануй карту пам'яті.** Код у банку 2 (фіксований, `$8000`), дані рівнів у банках 0-1, графіка спрайтів у банку 3, музика в банках 4 та 6, тіньовий екран у банку 7. Тримай тіньову копію порту `$7FFD` — він працює лише на запис.

- **Обробник переривань володіє музикою.** Обробник IM2 підключає музичний банк, запускає PT3-програвач, оновлює SFX та відновлює попередній банк. Тримай його легким — максимум ~3 000 тактів (T-states).

- **Бюджет кадру геймплею на Pentagon — 71 680 тактів.** Типовий кадр зі скролінгом, 8 спрайтами та ШІ коштує ~50 000 тактів у середньому, ~65 000 у найгіршому випадку. Профілюй та оптимізуй найгірший випадок, а не середній.

- **Скролінг — найдорожча окрема операція.** Використовуй метод комбінованого скролінгу (LDIR на рівні символів + піксельне зміщення) з подвійною буферизацією через тіньовий екран. Розподіляй копіювання стовпця між двома кадрами, коли можливо.

- **Запускай ШІ ворогів кожен 2-й або 3-й кадр.** Фізика та виявлення зіткнень працюють кожен кадр; рішення ШІ можна амортизувати. Це економить 2 000-3 000 тактів на кадр у найгіршому випадку.

- **Використовуй esxDOS для сучасного обладнання.** API `RST $08` / `F_OPEN` / `F_READ` / `F_CLOSE` простий і швидкий. Виявляй DivMMC при запуску і відступай до завантаження з касети, якщо відсутній.

- **Профілюй з DeZog.** Стрічка бордюру говорить тобі, що ти за межами бюджету. DeZog говорить тобі, де. Вимірюй кожну підсистему, знаходь вузьке місце, оптимізуй його, вимірюй знову.

- **Обирай правильний пакувальник для кожної задачі.** Exomizer або ZX0 для одноразового завантаження рівня (найкращий ступінь стиснення). Pletter для потокової передачі тайлів під час геймплею (швидке розпакування). Детальний аналіз компромісів у Розділі 14.

- **Полірування не є опціональним.** Переходи екранів, анімації смерті, тряска екрана, фільтрація дребезгу введення та режим залучення — це різниця між технічним демо і грою.

- **Тестуй на кількох емуляторах та реальному обладнанні.** Fuse, Unreal Speccy та ZEsarUX моделюють таймінг по-різному. Поведінка DivMMC на реальному обладнанні може відрізнятися від емульованого esxDOS.

---

> **Джерела:** World of Spectrum (карта пам'яті ZX Spectrum 128K та документація порту $7FFD); Introspec "Data Compression for Modern Z80 Coding" (Hype 2017); документація API esxDOS (DivIDE/DivMMC wiki); документація розширення DeZog для VS Code (GitHub: maziac/DeZog); документація sjasmplus (директиви SAVETAP, DEVICE, SLOT, PAGE); специфікація формату Vortex Tracker II PT3; Розділи 11, 14, 15, 16, 17, 18, 19 цієї книги.
