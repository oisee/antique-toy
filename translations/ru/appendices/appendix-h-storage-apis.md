# Приложение H: API хранилищ --- TR-DOS и esxDOS

> *«Технически впечатляющее демо, которое поставляется как .tzx, когда правила требуют .trd, будет дисквалифицировано.»*
> -- Глава 20

Два API хранилищ доминируют в мире ZX Spectrum: **TR-DOS** (дисковая операционная система советского интерфейса Beta Disk 128, стандартная на клонах Pentagon и Scorpion) и **esxDOS** (современная операционная система SD-карт, работающая на аппаратных интерфейсах DivMMC и DivIDE). Большинство релизов российской и украинской демосцены распространяются как образы дисков `.trd`. Большинство современных западных релизов используют образы лент `.tap` или файловые структуры, совместимые с esxDOS. Если ты выпускаешь демо или игру сегодня, практичный выбор --- предоставить образ `.trd` для совместимости с огромной российско-украинской базой пользователей, и файл `.tap` для всех остальных. Если твой загрузчик поддерживает определение esxDOS (как описано в Главе 21), пользователи с DivMMC получают быструю загрузку с SD-карты бесплатно.

Это приложение --- справочник по API, который ты держишь открытым, пока пишешь загрузчик. Глава 21 описывает интеграцию в полноценном игровом проекте. Глава 15 описывает аппаратные детали переключения банков памяти и маппинга портов, на которых основаны оба API.

---

## 1. TR-DOS (Beta Disk 128)

### Аппаратная часть

Интерфейс Beta Disk 128 --- стандартный контроллер гибких дисков для Pentagon, Scorpion и большинства советских клонов ZX Spectrum. Он построен на микросхеме контроллера гибких дисков Western Digital WD1793, которая взаимодействует с Z80 через пять портов ввода-вывода.

ПЗУ TR-DOS (8 КБ) занимает диапазон `$0000`--`$3FFF`, когда интерфейс Beta Disk активен. Оно подключается автоматически, когда Z80 выполняет код по адресу `$3D13` (магическая точка входа), и отключается, когда выполнение возвращается в область основного ПЗУ.

### Формат диска

| Свойство | Значение |
|----------|----------|
| Дорожки | 80 |
| Стороны | 2 |
| Секторов на дорожку | 16 |
| Байт на сектор | 256 |
| Общая ёмкость | 640 КБ (655 360 байт) |
| Формат образа | `.trd` (сырой образ диска, 640 КБ) |
| Системная дорожка | Дорожка 0, сторона 0 |

Дорожка 0 содержит каталог диска (секторы 1--8) и информационный сектор диска (сектор 9). Каталог вмещает до 128 записей о файлах. Каждая запись занимает 16 байт:

```
Bytes 0-7:   Filename (8 characters, space-padded)
Byte  8:     File type: 'C' = code, 'B' = BASIC, 'D' = data, '#' = sequential
Bytes 9-10:  Start address (or BASIC line number)
Bytes 11-12: Length in bytes
Byte  13:    Length in sectors
Byte  14:    Starting sector
Byte  15:    Starting track
```

### Карта портов WD1793

| Порт | Чтение | Запись |
|------|--------|--------|
| `$1F` | Регистр состояния | Регистр команд |
| `$3F` | Регистр дорожки | Регистр дорожки |
| `$5F` | Регистр сектора | Регистр сектора |
| `$7F` | Регистр данных | Регистр данных |
| `$FF` | Системный регистр TR-DOS | Системный регистр TR-DOS |

Порт `$FF` --- системный порт Beta Disk. Он управляет выбором дисковода, выбором стороны, загрузкой головки и плотностью записи. Старшие биты также отражают сигналы DRQ (Data Request) и INTRQ (Interrupt Request) от WD1793.

### Команды WD1793

| Команда | Код | Описание |
|---------|-----|----------|
| Restore | `$08` | Переместить головку на дорожку 0. Проверить дорожку. |
| Seek | `$18` | Переместить головку на дорожку из регистра данных. |
| Step In | `$48` | Шаг головки на одну дорожку к центру. |
| Step Out | `$68` | Шаг головки на одну дорожку к краю. |
| Read Sector | `$88` | Прочитать один 256-байтный сектор. |
| Write Sector | `$A8` | Записать один 256-байтный сектор. |
| Read Address | `$C0` | Прочитать следующее поле ID сектора. |
| Force Interrupt | `$D0` | Прервать текущую команду. |

Младший ниббл каждого байта команды содержит флаги-модификаторы (скорость шага, проверка, выбор стороны, задержка). Значения выше используют общие значения по умолчанию. За полной битовой раскладкой обращайся к даташиту WD1793.

### API ПЗУ: загрузка файла

Стандартный подход к файловому вводу-выводу под TR-DOS --- вызов подпрограмм ПЗУ по адресу `$3D13`. ПЗУ TR-DOS предоставляет высокоуровневые файловые операции через систему команд: ты помещаешь параметры в регистры и в системную область по адресам `$5D00`--`$5FFF`, затем вызываешь ПЗУ.

```z80
; TR-DOS: Load a file by name
; Loads a code file ('C' type) to its stored start address
;
; The filename must be placed at $5D02 (8 bytes, space-padded).
; The file type goes to $5D0A.
;
; Call $3D13 with C = $08 (load file command)

load_trdos_file:
    ; Set up filename at TR-DOS system area
    ld   hl, my_filename
    ld   de, $5D02
    ld   bc, 8
    ldir                    ; copy 8-char filename

    ld   a, 'C'             ; file type: code
    ld   ($5D0A), a

    ld   c, $08             ; TR-DOS command: load file
    call $3D13              ; enter TR-DOS ROM
    ret

my_filename:
    db   "SCREEN  "         ; 8 characters, space-padded
```

Чтобы загрузить по конкретному адресу (переопределив сохранённый начальный адрес):

```z80
; TR-DOS: Load file to explicit address
; HL = destination address
; DE = length to load
; Filename already at $5D02, type at $5D0A

load_trdos_to_addr:
    ld   hl, $4000          ; load to screen memory
    ld   de, 6912           ; 6912 bytes (one screen)
    ld   ($5D03), hl        ; override start address
    ld   ($5D05), de        ; override length
    ld   c, $08             ; load file
    call $3D13
    ret
```

### Прямой доступ к секторам

Для демо, которые потоково читают данные с диска --- полноэкранные анимации, музыкальные данные, не помещающиеся в доступную оперативную память, или многочастные демо, подгружающие эффекты на лету --- прямой доступ к секторам полностью обходит файловую систему. Ты управляешь положением головки, читаешь секторы по одному и обрабатываешь данные по мере их поступления.

```z80
; Read a single sector directly via WD1793 ports
; B = track number (0-159, with side encoded in bit 0 of $FF)
; C = sector number (1-16)
; HL = destination buffer (256 bytes)

read_sector:
    ld   a, b
    out  ($3F), a           ; set track register
    ld   a, c
    out  ($5F), a           ; set sector register

    ld   a, $88             ; Read Sector command
    out  ($1F), a           ; issue command

    ; Wait for DRQ and read 256 bytes
    ld   b, 0               ; 256 bytes to read
.wait_drq:
    in   a, ($FF)           ; read system register
    bit  6, a               ; test DRQ bit
    jr   z, .wait_drq       ; wait until data ready
    in   a, ($7F)           ; read data byte
    ld   (hl), a
    inc  hl
    djnz .wait_drq

    ; Wait for command completion
.wait_done:
    in   a, ($1F)           ; read status register
    bit  0, a               ; test BUSY bit
    jr   nz, .wait_done
    ret
```

**Внимание:** Прямой доступ к секторам чувствителен к таймингам. Прерывания должны быть запрещены во время цикла передачи данных, иначе байты будут потеряны. WD1793 выставляет DRQ на ограниченное временное окно; если Z80 не прочитает регистр данных до прихода следующего байта, данные будут перезаписаны. На скорости 250 кбит/с (двойная плотность) у тебя примерно 32 микросекунды на байт --- около 112 тактов (T-state) на Pentagon. Плотный цикл выше выполняется примерно за 50--60 тактов (T-state) на байт, оставляя достаточный запас.

### Обнаружение диска

Чтобы определить, присутствует ли интерфейс Beta Disk:

```z80
; Detect Beta Disk 128
; Returns: carry clear if present, carry set if absent
detect_beta_disk:
    ; The TR-DOS ROM signature is at $0069 when paged in.
    ; We can check port $FF for a sane response:
    ; If no Beta Disk is present, port $FF reads as floating bus.
    in   a, ($1F)           ; read WD1793 status
    cp   $FF                ; floating bus returns $FF
    scf
    ret  z                  ; probably no controller
    or   a                  ; clear carry = present
    ret
```

Более надёжный метод --- попытаться вызвать `$3D13` и проверить, присутствуют ли сигнатурные байты ПЗУ TR-DOS. В продакшн-коде обычно проверяют известную последовательность байт в точках входа ПЗУ TR-DOS.

---

## 2. esxDOS (DivMMC / DivIDE)

### Аппаратная часть

DivMMC (и его более старый собрат DivIDE) --- интерфейс массового хранилища, подключающий SD-карту к ZX Spectrum. Прошивка esxDOS предоставляет POSIX-подобный файловый API, доступный из кода Z80 через `RST $08`. esxDOS поддерживает файловые системы FAT16 и FAT32, длинные имена файлов, подкаталоги и множество одновременно открытых файловых дескрипторов.

DivMMC использует автоматическое маппирование: когда Z80 считывает инструкцию с определённых «ловушечных» адресов (в частности `$0000`, `$0008`, `$0038`, `$0066`, `$04C6`, `$0562`), аппаратура DivMMC автоматически подключает собственное ПЗУ по адресам `$0000`--`$1FFF`. Ловушка `RST $08` --- основная точка входа API.

### Паттерн API

Каждый вызов esxDOS следует одному и тому же паттерну:

```z80
    rst  $08              ; trigger DivMMC auto-map
    db   function_id      ; function number (byte after RST)
    ; Returns:
    ;   Carry clear = success
    ;   Carry set   = error, A = error code
```

Номер функции --- это байт, непосредственно следующий за инструкцией `RST $08` в памяти. Z80 выполняет `RST $08`, что вызывает переход на адрес `$0008`. DivMMC автоматически подключает своё ПЗУ по этому адресу, читает следующий байт (номер функции), диспатчит вызов, затем отключает ПЗУ и возвращается к инструкции после `DB`.

### Справочник функций

| Функция | ID | Описание | Вход | Выход |
|---------|-----|----------|------|-------|
| `M_GETSETDRV` | `$89` | Получить/установить диск по умолчанию | A = `'*'` для диска по умолчанию | A = буква диска |
| `F_OPEN` | `$9A` | Открыть файл | IX = имя файла (нуль-терминированное), B = режим, A = диск | A = дескриптор файла |
| `F_CLOSE` | `$9B` | Закрыть файл | A = дескриптор файла | -- |
| `F_READ` | `$9D` | Прочитать байты | A = дескриптор, IX = буфер, BC = количество | BC = прочитано байт |
| `F_WRITE` | `$9E` | Записать байты | A = дескриптор, IX = буфер, BC = количество | BC = записано байт |
| `F_SEEK` | `$9F` | Позиционирование в файле | A = дескриптор, L = whence, BCDE = смещение | BCDE = новая позиция |
| `F_FSTAT` | `$A1` | Статус файла (по дескриптору) | A = дескриптор, IX = буфер | 11-байтный блок stat |
| `F_OPENDIR` | `$A3` | Открыть каталог | IX = путь (нуль-терминированный) | A = дескриптор каталога |
| `F_READDIR` | `$A4` | Прочитать запись каталога | A = дескриптор каталога, IX = буфер | запись по (IX) |
| `F_CLOSEDIR` | `$A5` | Закрыть каталог | A = дескриптор каталога | -- |
| `F_GETCWD` | `$A8` | Получить текущий каталог | IX = буфер | путь по (IX) |
| `F_CHDIR` | `$A9` | Сменить каталог | IX = путь | -- |
| `F_STAT` | `$AC` | Статус файла (по имени) | IX = имя файла | 11-байтный блок stat |

### Режимы открытия файла

| Режим | Значение | Описание |
|-------|----------|----------|
| Только чтение | `$01` | Открыть существующий файл для чтения |
| Создать/обрезать | `$06` | Создать новый или обрезать существующий для записи |
| Только создать | `$04` | Создать новый файл; ошибка, если существует |
| Дополнение | `$0E` | Открыть для записи в конец файла |

### Значения Seek Whence

| Whence | Значение | Описание |
|--------|----------|----------|
| `SEEK_SET` | `$00` | Смещение от начала файла |
| `SEEK_CUR` | `$01` | Смещение от текущей позиции |
| `SEEK_END` | `$02` | Смещение от конца файла |

### Пример кода: загрузка файла

```z80
; esxDOS: Load a binary file into memory
;
; Uses register conventions from esxDOS API documentation.
; Note: F_READ uses IX for the destination buffer, not HL.

    ld   a, '*'             ; use default drive
    ld   ix, filename       ; pointer to zero-terminated filename
    ld   b, $01             ; FA_READ: open for reading
    rst  $08
    db   $9A                ; F_OPEN
    jr   c, .error          ; carry set = error

    ld   (.file_handle), a  ; save file handle

    ld   ix, $4000          ; destination buffer (screen memory)
    ld   bc, 6912           ; bytes to read (one full screen)
    ld   a, (.file_handle)
    rst  $08
    db   $9D                ; F_READ
    jr   c, .error

    ld   a, (.file_handle)
    rst  $08
    db   $9B                ; F_CLOSE
    ret

.error:
    ; A contains the esxDOS error code
    ; Common errors:
    ;   5 = file not found
    ;   7 = file already exists (on create)
    ;   9 = invalid file handle
    ret

filename:
    db   "screen.scr", 0

.file_handle:
    db   0
```

### Пример кода: потоковое чтение данных из файла

Для демо, которые загружают данные инкрементально --- распаковка фрагментов уровней между кадрами, потоковое воспроизведение предварительно отрендеренной анимации или подгрузка музыкальных паттернов по запросу --- паттерн таков: открыть файл один раз, читать порцию за кадр, закрыть по завершении.

```z80
; Streaming: read N bytes per frame from an open file
; Call stream_init once, then stream_chunk from your main loop.

CHUNK_SIZE  equ  256        ; bytes per frame (tune to budget)

stream_handle:  db 0
stream_done:    db 0

; Initialise: open the file
stream_init:
    ld   a, '*'
    ld   ix, stream_file
    ld   b, $01             ; FA_READ
    rst  $08
    db   $9A                ; F_OPEN
    ret  c                  ; error
    ld   (stream_handle), a
    xor  a
    ld   (stream_done), a   ; not done yet
    ret

; Per-frame: read one chunk into buffer
; Returns: BC = bytes actually read (may be < CHUNK_SIZE at EOF)
stream_chunk:
    ld   a, (stream_done)
    or   a
    ret  nz                 ; already finished

    ld   a, (stream_handle)
    ld   ix, stream_buffer
    ld   bc, CHUNK_SIZE
    rst  $08
    db   $9D                ; F_READ
    jr   c, .eof

    ; BC = bytes actually read
    ld   a, b
    or   c
    jr   z, .eof            ; zero bytes read = end of file
    ret

.eof:
    ld   a, (stream_handle)
    rst  $08
    db   $9B                ; F_CLOSE
    ld   a, 1
    ld   (stream_done), a
    ret

stream_file:
    db   "anim.bin", 0

stream_buffer:
    ds   CHUNK_SIZE
```

### Обнаружение esxDOS

```z80
; Detect esxDOS presence
; Returns: carry clear = esxDOS available, carry set = not available
;
; Strategy: attempt M_GETSETDRV. If esxDOS is present, it returns
; the current drive letter. If not present, RST $08 goes to the
; Spectrum ROM's error handler at $0008 (a benign instruction on
; the 128K ROM) and does not crash.

detect_esxdos:
    ld   a, '*'             ; request default drive
    rst  $08
    db   $89                ; M_GETSETDRV
    ret                     ; carry flag set by esxDOS on error
```

Более консервативный подход --- проверить сигнатуру ловушки DivMMC перед вызовом любых функций API. На практике метод выше работает на всех моделях 128K, потому что обработчик `$0008` в ПЗУ 128K не падает --- он выполняет безопасную последовательность и возвращается. На 48K-машине без esxDOS инструкция `RST $08` попадает в рестарт ошибок, для чего может потребоваться специальная обработка. Глава 21 обсуждает это в контексте продакшн-загрузчика игры.

---

## 3. +3DOS (Amstrad +3)

Amstrad Spectrum +3, со встроенным 3-дюймовым дисководом, имеет собственную ДОС: +3DOS. API использует другой механизм --- вызовы точек входа в ПЗУ +3DOS на странице `$01`, доступные через `RST $08` с другим набором кодов функций.

+3DOS редко используется в демосцене по двум причинам. Во-первых, +3 продавался преимущественно в Западной Европе и никогда не был доминирующей моделью Spectrum ни в одном демосцена-сообществе. Во-вторых, нестандартная раскладка памяти и схема переключения ПЗУ +3 делают его несовместимым с большинством демосценового кода, написанного для архитектуры 128K/Pentagon. Если тебе нужна совместимость с +3, API +3DOS документирован в техническом руководстве Spectrum +3 (Amstrad, 1987). Для большинства демо- и игровых проектов достаточно предоставить файл `.tap` --- +3 загружает файлы `.tap` нативно через режим совместимости с лентой.

---

## 4. Практические паттерны

### Загрузка экрана с диска (TR-DOS)

Загрузочный экран --- первое впечатление пользователя. В TR-DOS файл экрана (`SCREEN  C`, 6912 байт) загружается прямо по адресу `$4000` и появляется мгновенно:

```z80
; TR-DOS: Load a .scr file directly to screen memory
; The screen appears as it loads, line by line.
load_screen_trdos:
    ld   hl, scr_filename
    ld   de, $5D02
    ld   bc, 8
    ldir
    ld   a, 'C'
    ld   ($5D0A), a
    ld   hl, $4000          ; destination: screen memory
    ld   ($5D03), hl
    ld   de, 6912           ; length: full screen
    ld   ($5D05), de
    ld   c, $08             ; load file
    call $3D13
    ret

scr_filename:
    db   "SCREEN  "         ; 8 chars, padded
```

### Загрузка экрана с SD (esxDOS)

Тот же визуальный результат, другой API:

```z80
; esxDOS: Load a .scr file to screen memory
load_screen_esxdos:
    ld   a, '*'
    ld   ix, scr_filename_esx
    ld   b, $01             ; FA_READ
    rst  $08
    db   $9A                ; F_OPEN
    ret  c

    push af                 ; save handle
    ld   ix, $4000          ; destination: screen memory
    ld   bc, 6912
    pop  af
    push af
    rst  $08
    db   $9D                ; F_READ
    pop  af
    rst  $08
    db   $9B                ; F_CLOSE
    ret

scr_filename_esx:
    db   "screen.scr", 0
```

### Двухрежимный загрузчик

Продакшн-загрузчик должен определить доступное хранилище и использовать его:

```z80
; Unified loader: try esxDOS first, fall back to TR-DOS, then tape
load_data:
    call detect_esxdos
    jr   nc, .use_esxdos    ; carry clear = esxDOS present

    call detect_beta_disk
    jr   nc, .use_trdos     ; carry clear = Beta Disk present

    ; Fall back to tape loading
    jp   load_from_tape

.use_esxdos:
    jp   load_from_esxdos

.use_trdos:
    jp   load_from_trdos
```

### Потоковое чтение сжатых данных

Самый мощный паттерн комбинирует API хранилища со сжатием (Приложение C). Открой файл со сжатыми данными, читай порции в буфер каждый кадр, распаковывай в целевую область и продвигайся:

```
Frame 1:  F_READ 256 bytes -> buffer   |  decompress buffer -> screen
Frame 2:  F_READ 256 bytes -> buffer   |  decompress buffer -> screen
Frame 3:  F_READ 256 bytes -> buffer   |  decompress buffer -> screen
...
Frame N:  F_READ < 256 bytes (EOF)     |  decompress, close file
```

При 256 байтах за кадр и 50 кадрах/сек ты получаешь потоковую скорость 12,5 КБ/сек с SD-карты --- достаточно для сжатой полноэкранной анимации. На TR-DOS прямое чтение секторов со скоростью один сектор за кадр даёт 12,8 КБ/сек (256 байт * 50 кадров/сек). Узкое место --- скорость распаковки, а не ввод-вывод.

---

## 5. Справочник форматов файлов

| Формат | Расширение | Применение | Примечания |
|--------|------------|------------|------------|
| Образ диска TR-DOS | `.trd` | Стандарт для релизов на Pentagon/Scorpion | Сырой образ 640 КБ. Поддерживается всеми эмуляторами. |
| Файловый контейнер TR-DOS | `.scl` | Проще, чем .trd | Содержит файлы без полной структуры диска. Хорош для распространения. |
| Образ ленты | `.tap` | Универсальный ленточный формат | Работает на любой модели Spectrum и в любом эмуляторе. Без файловой системы. |
| Расширенный образ ленты | `.tzx` | Лента с защитой от копирования / турбо-загрузчиками | Сохраняет точные тайминги ленты. Редко нужен для новых релизов. |
| Снапшот (48K/128K) | `.sna` | Быстрая загрузка, без файловой системы | Захватывает полное состояние машины. Не нужен код загрузчика. |
| Снапшот (сжатый) | `.z80` | Как .sna, но сжатый | Несколько версий; .z80 v3 поддерживает 128K. |
| Дистрибутив Next | `.nex` | Исполняемый файл ZX Spectrum Next | Самодостаточный бинарник с заголовком, описывающим раскладку банков памяти. |

**Выбор формата релиза:** Для демосценового релиза предоставь как минимум два формата:

1. **`.trd`** для пользователей TR-DOS (российско-украинское сообщество, владельцы Pentagon/Scorpion и пользователи эмуляторов, предпочитающие образы дисков). Это формат по умолчанию для пати вроде Chaos Constructions и DiHalt.
2. **`.tap`** для всех остальных (реальное железо 128K с ленточным входом, пользователи DivMMC через загрузчик `.tap`, и все эмуляторы). sjasmplus умеет генерировать `.tap` напрямую с помощью директивы `SAVETAP`.

Если твоё демо достаточно маленькое (менее 48 КБ), снапшот `.sna` тоже отлично подходит --- он загружается мгновенно без кода загрузчика.

---

## 6. См. также

- **Глава 15** --- Анатомия железа: переключение банков памяти, порт `$7FFD`, полная карта портов, рядом с которой существуют TR-DOS и esxDOS.
- **Глава 20** --- Рабочий процесс демо: форматы релизов, правила подачи на пати, требования к `.trd` и `.tap`.
- **Глава 21** --- Полноценная игра: продакшн-качество кода загрузки с ленты и esxDOS, двухрежимное определение, побанковая загрузка.
- **Приложение C** --- Сжатие: какие компрессоры сочетать с потоковым вводом-выводом.
- **Приложение E** --- eZ80 / Agon Light 2: файловый API MOS на Agon, предоставляющий аналогичные файловые операции (`mos_fopen`, `mos_fread`, `mos_fclose`) через другой механизм (RST $08 с кодами функций MOS в режиме ADL).

---

> **Источники:** WD1793 datasheet (Western Digital, 1983); дизассемблирование TR-DOS v5.03 (различные авторы, public domain); документация API esxDOS (Wikipedia, zxe.io); спецификация аппаратуры DivMMC (Mario Prato / ByteDelight); Spectrum +3 Technical Manual (Amstrad, 1987); Introspec, «Loading and saving on the Spectrum» (Hype, 2016)
