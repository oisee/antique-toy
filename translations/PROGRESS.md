# Translation Progress

## Status: ALL COMPLETE (2026-02-23)

All 4 language editions built and released as v0.6.

**Note:** The English edition is always the primary and ahead of translations. Translations are updated periodically (possibly every few releases) rather than after every EN edit. The manifest system tracks staleness automatically.

| Language | Chapters | Appendices | Glossary | Words | PDF/EPUB | Release |
|----------|----------|------------|----------|-------|----------|---------|
| EN | 23/23 | 4/4 | done | ~128K | built | v0.6 |
| ES | 23/23 | 4/4 | done | ~165K | built | v0.6 |
| RU | 23/23 | 4/4 | done | ~140K | built | v0.6 |
| UK | 23/23 | 4/4 | done | ~142K | built | v0.6 |

**Total: ~575K words, 112 translated files, 12 release artifacts.**

### Maintaining translations

When EN source chapters are edited:

```sh
python3 translations/manifest.py check all    # show stale translations
python3 translations/manifest.py diff es      # show what changed in EN since last ES stamp
```

After retranslating stale files:

```sh
python3 translations/manifest.py stamp es     # update hashes
```

### Building translated editions

```sh
python3 build_book.py --lang es               # Spanish PDF/EPUB
python3 build_book.py --lang ru --pdf         # Russian A4 PDF only
python3 build_book.py --lang uk --all         # Ukrainian all formats
```

### Rules reminder
- Never translate: proper names, product names, chip names, hex, register names
- Keep in English: all code blocks and code comments
- Translate: prose, headings, figure alt text
- Keep: markdown formatting, image paths, \newpage commands
- Always load `translations/glossary-lookup.md` before translating
- See FORBIDDEN ALTERNATIVES in glossary-lookup.md
