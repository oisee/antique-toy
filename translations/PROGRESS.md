# Translation Progress

## Status: ES complete, RU/UK ch01-ch10 done, ch11-ch23 + appendices + glossary remaining

### Spanish (ES) — COMPLETE

All 23 chapters + 4 appendices + glossary translated (~165K words). Manifest stamped 2026-02-23.

### Russian (RU) & Ukrainian (UK) — ch01-ch10 done

| File | Source path | RU | UK |
|------|-----------|----|----|
| ch01-thinking-in-cycles | chapters/ch01-thinking-in-cycles/draft.md | done | done |
| ch02-screen-as-puzzle | chapters/ch02-screen-as-puzzle/draft.md | done | done |
| ch03-demoscene-toolbox | chapters/ch03-demoscene-toolbox/draft.md | done | done |
| ch04-maths | chapters/ch04-maths/draft.md | done | done |
| ch05-3d | chapters/ch05-3d/draft.md | done | done |
| ch06-sphere | chapters/ch06-sphere/draft.md | done | done |
| ch07-rotozoomer | chapters/ch07-rotozoomer/draft.md | done | done |
| ch08-multicolor | chapters/ch08-multicolor/draft.md | done | done |
| ch09-tunnels | chapters/ch09-tunnels/draft.md | done | done |
| ch10-scroller | chapters/ch10-scroller/draft.md | done | done |
| ch11-sound | chapters/ch11-sound/draft.md | todo | todo |
| ch12-music-sync | chapters/ch12-music-sync/draft.md | todo | todo |
| ch13-sizecoding | chapters/ch13-sizecoding/draft.md | todo | todo |
| ch14-compression | chapters/ch14-compression/draft.md | todo | todo |
| ch15-anatomy | chapters/ch15-anatomy/draft.md | todo | todo |
| ch16-sprites | chapters/ch16-sprites/draft.md | todo | todo |
| ch17-scrolling | chapters/ch17-scrolling/draft.md | todo | todo |
| ch18-gameloop | chapters/ch18-gameloop/draft.md | todo | todo |
| ch19-collisions | chapters/ch19-collisions/draft.md | todo | todo |
| ch20-demo-workflow | chapters/ch20-demo-workflow/draft.md | todo | todo |
| ch21-full-game | chapters/ch21-full-game/draft.md | todo | todo |
| ch22-porting-agon | chapters/ch22-porting-agon/draft.md | todo | todo |
| ch23-ai-assisted | chapters/ch23-ai-assisted/draft.md | todo | todo |
| appendix-a | appendices/appendix-a-z80-reference.md | todo | todo |
| appendix-b | appendices/appendix-b-sine-tables.md | todo | todo |
| appendix-c | appendices/appendix-c-compression.md | todo | todo |
| appendix-g | appendices/appendix-g-ay-registers.md | todo | todo |
| glossary | glossary.md | todo | todo |

### How to resume

Each language can be translated independently. For each remaining file:

1. Read `translations/glossary-lookup.md` for canonical terminology (161 terms)
2. Read the English source file
3. Translate prose, keep all code blocks/image refs/formatting intact
4. Write to `translations/{ru,uk}/chapters/chNN-name.md` or `translations/{ru,uk}/appendices/...`
5. After translating, run `python3 translations/manifest.py stamp {lang}` to record hashes

Use `python3 translations/manifest.py check {lang}` to see what needs translation.

### Rules reminder
- Never translate: proper names, product names, chip names, hex, register names
- Keep in English: all code blocks and code comments
- Translate: prose, headings, figure alt text
- Keep: markdown formatting, image paths, \newpage commands
- See FORBIDDEN ALTERNATIVES in glossary-lookup.md
