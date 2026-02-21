# Задания на ручное извлечение источников
## Книга «Coding the Impossible: Z80 Demoscene Techniques for Modern Makers»

Все задачи ниже — то, до чего я не могу добраться программно из-за ограничений на домены (scene.org, bbb.retroscene.org, zxart.ee, vtrdos.ru) или потому что старые страницы Hype не индексируются поисковиками.

---

## A. ZIP-АРХИВЫ: скачать → извлечь NFO/DIZ

Это самые ценные первоисточники — технические описания эффектов от самих авторов.

### A1. Rain by Life on Mars — file_id.diz
- **Скачать:** https://files.scene.org/view/parties/2016/multimatograf16/8bit_demo/rain.zip
- **Альтернатива:** https://bbb.retroscene.org (поиск «Rain Life on Mars»)
- **Извлечь:** `file_id.diz` из корня архива
- **Содержит:** описание rain-эффекта, работающего одновременно с 9-канальным beeper-движком на 48K/16K
- **Для книги:** Part III (Sound Meets Screen), Part IV (16K constraints)

### A2. Break Space by Thesuper — breakspace.nfo
- **Скачать:** https://files.scene.org/view/parties/2016/chaosconstructions16/zx_spectrum_640k_demo/breakspace_by_thesuper.zip
- **Альтернатива:** NFO также выложен на bay6.retroscene.org (ссылка из Pouet-комментариев diver'а)
- **Извлечь:** `breakspace.nfo` (или как он назван внутри)
- **Содержит:** посценовый разбор всех 19 частей демо, кредиты, описания эффектов (weaves, Magen Fractal, Venus 3D, Mondrian)
- **Для книги:** Part II (эффекты), Part IV (сжатие в практике — 122 фрейма в 10КБ)
- **⚠️ Частично извлечено** через Pouet prod_nfo — но нужен полный текст

### A3. Eager (to live) by Life on Mars — NFO
- **Скачать:** https://files.scene.org/view/parties/2015/3bmopenair15/zx_demo/eager(party).zip
- **Финальная версия:** introspec.retroscene.org/demo/eager(finalver).zip
- **Извлечь:** NFO-файл (имя неизвестно — может быть .nfo или .txt)
- **Содержит:** подробный технический writeup (Kylearan на Pouet: «Big thanks for the nfo file alone, I love reading technical write-ups!»). Chaos zoomer, 50Hz визуалы, true digi-drums
- **Для книги:** Part II (tunnel, chaos zoomer), Part III (digi-drums)

---

## B. HYPE-СТАТЬИ: открыть в браузере → сохранить полный текст

Эти страницы существуют, но НЕ индексируются поисковиками и НЕ доступны через web_fetch.

### B1. ★★★ «Технический разбор Illusion от X-Trade» — Introspec
- **URL:** https://hype.retroscene.org/blog/dev/670.html
- **Дата:** март 2017
- **Сохранить:** полный текст статьи + комментарии
- **Содержит:** внутренние циклы сферы, ротозумера, тоннеля из Illusion (Enlight'96). Ключевой источник для Part II
- **Приоритет:** КРИТИЧЕСКИЙ — это центральный разбор для главы об эффектах

### B2. ★★★ «Making of Eager» — Introspec
- **URL:** https://hype.retroscene.org/blog/demo/261.html
- **Дата:** август 2015
- **Сохранить:** полный текст (~30КБ по оценке) + комментарии
- **Содержит:** подробный making-of демо Eager. Дизайнерские решения, технические компромиссы, chaos zoomer
- **Приоритет:** ВЫСОКИЙ — making-of + технический документ

### B3. ★★☆ «Код мёртв» — Introspec
- **URL:** https://hype.retroscene.org/blog/demo/32.html
- **Дата:** январь 2015
- **Сохранить:** полный текст + комментарии
- **Содержит:** эссе о роли кода в демосцене. «pop hl : ldd» как культурный артефакт. Философия design-first
- **Приоритет:** СРЕДНИЙ — эпиграф/сайдбар для Part I (Mindset)

### B4. ★★☆ «За дизайн» — Introspec
- **URL:** https://hype.retroscene.org/blog/demo/64.html
- **Дата:** январь 2015
- **Сохранить:** полный текст + комментарии
- **Содержит:** манифест design-first подхода к демомейкингу
- **Приоритет:** СРЕДНИЙ — парный текст к «Код мёртв»

### B5. ★★☆ «MORE» — Introspec
- **URL:** https://hype.retroscene.org/blog/demo/87.html
- **Дата:** февраль 2015
- **Сохранить:** полный текст + комментарии
- **Содержит:** амбиция делать демы, «которые не принадлежат Spectrum'у» — выход за пределы платформы
- **Приоритет:** СРЕДНИЙ — философия, цитата для введения

### B6. ★☆☆ «Компо десятилетия (CC 2015)» — Introspec
- **URL:** https://hype.retroscene.org/blog/demo/278.html
- **Дата:** август 2015
- **Сохранить:** если будет время — контекст CC'15, обзоры демо
- **Приоритет:** НИЗКИЙ — контекстуальный

---

## C. HYPE-СТАТЬИ: частично извлечены, нужен полный текст

Эти статьи я смог частично загрузить, но HTML truncated или комментарии обрезаны.

### C1. «Chunky effects on ZX Spectrum» — sq (2022)
- **URL:** https://hype.retroscene.org/blog/dev/1050.html
- **Что нужно:** полный текст с кодом (4×4 halftone chunky, bumpmapping, интерлейсинг)
- **Для книги:** Part II (classic effects)

### C2. «Making of Hara Mamba, Scene!» — DenisGrachev (2019)
- **URL:** https://hype.retroscene.org/blog/demo/945.html
- **Что нужно:** полные листинги Z80 для пяти эффектов (hidden rotator, Kpacku scroll, Vasyliev scroll, morphing cat, Zatulinsky tunnel)
- **Для книги:** Part II, Part III

### C3. «Ещё раз про тайлы и RET» — DenisGrachev (2025)
- **URL:** https://hype.retroscene.org/blog/dev/1116.html
- **Что нужно:** полные примеры кода RET-chaining для тайловых движков
- **Для книги:** Part I (screen layout), Part II (tile engines)

---

## D. ЭЛЕКТРОННЫЕ ЖУРНАЛЫ (ZXArt / vtrdos): скачать TRD-образы

Эти журналы — «зингадцатки» формата TRD, читаемые в эмуляторе (Unreal Speccy, ZEsarUX). Содержат статьи Dark'а (X-Trade) об алгоритмах и оптимизациях.

### D1. ★★★ Spectrum Expert #01–03 — Dark / X-Trade
- **ZXArt:** https://zxart.ee → Press → поиск «Spectrum Expert»
- **vtrdos.ru:** http://vtrdos.ru/press.htm → Spectrum Expert
- **Все выпуски:** #01 (1997), #02 (1998), #03 (1998)
- **Содержит:** фундаментальные алгоритмы для демокодинга на Спектруме. Тот самый Dark, чей код Introspec анализировал в «Техническом разборе Illusion» (B1 выше)
- **Нужно:** открыть в эмуляторе, найти технические статьи, переписать/скриншотить ключевые алгоритмы
- **Для книги:** Part I (T-states, maths), Part II (effects). Историческая нить: Dark (1997) → Introspec (2017)

### D2. ★★☆ Born Dead #05 — упомянут в «Chunky effects»
- **ZXArt:** https://zxart.ee → Press → «Born Dead»
- **Содержит:** реализацию chunky-пикселей, на которую ссылается sq
- **Для книги:** Part II (chunky effects)

### D3. ★★☆ Scenergy #01–03 (2002–2004)
- **ZXArt:** https://zxart.ee → Press → «Scenergy»
- **Содержит:** англоязычный (!) диск-журнал от Raw/Premier League. Статьи по кодингу, обзоры демо
- **Для книги:** один из немногих англоязычных ZX-журналов — потенциально напрямую цитируемый

### D4. ★☆☆ ZX Format #4.5 (ENLiGHT'96 special)
- **ZXArt:** https://zxart.ee/eng/software/pressa/newspaper/zx-format/
- **Содержит:** специальный номер, посвящённый ENLiGHT'96 (партии, где Illusion от X-Trade занял 1-е место)
- **Для книги:** контекст для Illusion, возможно обзор/рецензия демо

### D5. ★☆☆ Info Guide #14 (2024) — ASC Sound Master manual
- **ZXArt:** https://zxart.ee/eng/software/pressa/disk-magazine/info-guide-14/
- **Содержит:** документация музредактора ASC Sound Master (Position/Pattern/Quant)
- **Для книги:** Part III (Sound), как справочный материал по AY-музыке

---

## E. POUET: дополнительные комментарии

### E1. Rain — технические комментарии
- **URL:** https://www.pouet.net/prod.php?which=67276
- **Что нужно:** проверить, нет ли в комментариях технических деталей о beeper-движке от Introspec'а или MISTER BEEP'а (Yerzmyey), которые я мог пропустить

### E2. Illusion by X-Trade — комментарий lordcoxis о 128K-фиксе
- **URL:** https://www.pouet.net/prod.php?which=1581
- **Что нужно:** комментарий lordcoxis (2021) с техническими деталями фикса для 128K/+3. Частично извлечён, но проверить полноту

---

## F. ДОПОЛНИТЕЛЬНЫЕ ИСТОЧНИКИ ДЛЯ ПОИСКА

Эти не из конкретных архивов, а скорее «поиск по наводке»:

### F1. Introspec's GitHub / личный сайт
- **introspec.retroscene.org** — проверить, есть ли другие технические тексты
- **GitHub:** поиск «introspec» или «spke» — возможно есть репозитории с исходниками демо

### F2. Yerzmyey / MISTER BEEP — документация beeper-движков
- Поиск документации к 9-канальному 1-bit beeper-движку, используемому в Rain
- Возможно на его сайте или Pouet-комментариях

### F3. sq (psndcj) — другие технические статьи на Hype
- https://hype.retroscene.org/profile/sq/created/topics/
- Автор VS Code гайда и chunky effects — проверить, нет ли ещё неизвестных статей

### F4. DenisGrachev — другие статьи на Hype
- https://hype.retroscene.org/profile/DenisGrachev/created/topics/
- Автор NHBF, Hara Mamba, Tiles&RET — проверить полный список

---

## Рекомендуемый порядок работы

**Фаза 1 — Быстрые победы (30 мин):**
1. B1–B5: открыть 5 Hype-статей в браузере, сохранить как PDF/HTML (Cmd+S)
2. A1–A3: скачать 3 zip-архива, извлечь diz/nfo

**Фаза 2 — Журналы в эмуляторе (1–2 часа):**
3. D1: Spectrum Expert #01–03 — найти на vtrdos.ru, открыть в Unreal Speccy
4. D2–D3: Born Dead #05, Scenergy — если найдутся на ZXArt

**Фаза 3 — Дополнительное (по желанию):**
5. C1–C3: дополнить частично извлечённые статьи
6. E1–E2: проверить Pouet-комментарии
7. F1–F4: поиск дополнительных авторов

---

## Формат сохранения

Для максимальной пользы при работе со мной:
- **Hype-статьи:** сохранить как `.html` (полная страница) или скопировать текст в `.txt`
- **NFO/DIZ:** текстовые файлы, просто скопировать как есть
- **Журналы (TRD):** скриншоты ключевых статей + переписанный текст технических разделов
- **Всё загрузить** сюда в чат или в следующий сеанс — я обработаю и добавлю в план книги
