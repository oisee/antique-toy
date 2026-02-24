RCL, [2026-02-24 05:20]
Книжка здоровская!  Боюсь только, что слишком много пытается сразу объять. Я бы ограничил "классикой" (считая тут Пентагон как подвид), а супер-Спектрумы, а тем более вообще не-Спектрумы типа Agon Light, вынес бы в другую книгу.

Я бы ещё посоветовал больше прямых ссылок на исходные материалы, а также упомянуть предыдущие такие попытки, как например https://zxdn.narod.ru/coding.htm  (где тоже много вкусностей)

Я к примеру недавно прочитал очень даже замечательную книжку Bare metal Amiga programming, которая старается не просто описывать железо, но и показывать возможное использование той или иной фишки, но даже при всём этом через некоторые главы было очень тяжело продраться - удовольствие близкое к чтению руководства по эксплуатации автомобиля из бардачка

RCL, [2026-02-24 05:45]
Понял, спасибо за контекст!

Насчёт оптимизации всё же скажу, что она очень сильно завязана не только на процессор, но и на всю машину.  DOWNHL тут ярким примером, но и не только DOWNHL - невозможность замаппить RAM под адрес 0000 исключает к примеру широкое использование команд RST, а также делает разные выборки из таблиц и текстур сложнее чем можно сделать скажем на тех же супер-Спектрумах, зато отсутствие иных прерываний кроме кадрового - наоборот, позволяет широко использовать стек.

Но так или иначе здорово, больше таких материалов

---

## Key points

1. **Scope concern:** book tries to cover too much, should focus on "classics" (Spectrum + Pentagon), move super-Spectrums and non-Spectrums (Agon) to a separate book.

2. **Sources:** wants more direct links to source materials. Recommends https://zxdn.narod.ru/coding.htm as prior art.

3. **Optimization is machine-specific, not just CPU-specific:**
   - DOWN_HL is purely ZX Spectrum (ULA screen layout)
   - No RAM at $0000 on Spectrum = can't use RST freely (super-Spectrums can)
   - No RAM at $0000 = page-aligned table lookups harder
   - Only vertical interrupt = safe to use stack as data tool (CPC has 3 CRTC interrupts, can't do this as freely)

4. **Bare Metal Amiga comparison:** even a good book with practical examples can feel like a car manual. Wants more context on *why* to use a feature.

## Actions taken

- README rewritten with honest platform positioning: "This book lives on the ZX Spectrum"
- Per-chapter platform tags added (Z80 / ZX / eZ80)
- zxdn.narod.ru noted for potential references
- RCL's point about machine-specific optimization strengthened the book's positioning
