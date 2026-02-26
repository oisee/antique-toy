# Ped7g — upkr compression feedback

**Source:** Ped7g (Slovak ZX Spectrum demoscene developer)
**Topic:** upkr vs ZX0 compression — practical tradeoffs
**Relevant to:** Ch.13 (Size-Coding), possibly Ch.12 (Demo Engine), appendices on compression

## Original (Slovak)

JFYI https://github.com/exoticorn/upkr/ ... je to velmi specificka (az neprakticka) vec, lebo to komprimuje o trochu lepsie nez napr. ZX0, ale rozbaluje to ovela ovela pomalsie, takze pozitivny prinos to ma prave asi len pre demo scenu a intra kde na kazdom byte zalezi, niekde okolo 512-2048 komprimovanych bytov sa to zacina lamat a upkr by malo obvykle vyjst najlepsie (a nad 2048 uz zase ta pomalost zacne byt dost otravna, ak je to na klasickom 3.5MHz ZX, takze napr. na 32kB demo sa to nehodi, ale tam vacsinou clovek najde tych par stovak bytov naviac aby pouzil ZX0 abo nieco take)

## Russian translation

К сведению: https://github.com/exoticorn/upkr/ — это очень специфичная (даже непрактичная) штука, потому что сжимает чуть лучше, чем например ZX0, но распаковывается намного-намного медленнее. Так что положительный эффект от неё есть, пожалуй, только для демосцены и интро, где каждый байт на счету. Где-то в районе 512–2048 сжатых байт наступает перелом, и upkr обычно выигрывает (а выше 2048 медленность уже начинает сильно раздражать, если это классический ZX на 3.5 МГц — так что для 32kB демо не подходит, но там обычно человек находит лишние пару сотен байт, чтобы использовать ZX0 или что-то подобное).

## Key takeaways

- **upkr** compresses slightly better than ZX0 but decompresses **much** slower
- Useful only for demoscene/intros where every byte counts
- Sweet spot: **512–2048 compressed bytes** — upkr usually wins
- Above 2048 bytes: decompression slowness becomes painful at 3.5 MHz
- Not suitable for 32KB demos — use ZX0 or similar instead
- At 32KB scale, you can usually find a few hundred extra bytes to avoid the slowness penalty
