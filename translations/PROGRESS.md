# Translation Progress

## Status: ch01-ch10 done, ch11-ch23 + appendices + glossary remaining

### Completed (all three languages)

| Chapter | ES | RU | UK |
|---------|----|----|-----|
| ch01-thinking-in-cycles | done | done | done |
| ch02-screen-as-puzzle | done | done | done |
| ch03-demoscene-toolbox | done | done | done |
| ch04-maths | done | done | done |
| ch05-3d | done | done | done |
| ch06-sphere | done | done | done |
| ch07-rotozoomer | done | done | done |
| ch08-multicolor | done | done | done |
| ch09-tunnels | done | done | done |
| ch10-scroller | done | done | done |

### Remaining (all three languages)

| File | Source path | ES | RU | UK |
|------|-----------|----|----|-----|
| ch11-sound | chapters/ch11-sound/draft.md | todo | todo | todo |
| ch12-music-sync | chapters/ch12-music-sync/draft.md | todo | todo | todo |
| ch13-sizecoding | chapters/ch13-sizecoding/draft.md | todo | todo | todo |
| ch14-compression | chapters/ch14-compression/draft.md | todo | todo | todo |
| ch15-anatomy | chapters/ch15-anatomy/draft.md | todo | todo | todo |
| ch16-sprites | chapters/ch16-sprites/draft.md | todo | todo | todo |
| ch17-scrolling | chapters/ch17-scrolling/draft.md | todo | todo | todo |
| ch18-gameloop | chapters/ch18-gameloop/draft.md | todo | todo | todo |
| ch19-collisions | chapters/ch19-collisions/draft.md | todo | todo | todo |
| ch20-demo-workflow | chapters/ch20-demo-workflow/draft.md | todo | todo | todo |
| ch21-full-game | chapters/ch21-full-game/draft.md | todo | todo | todo |
| ch22-porting-agon | chapters/ch22-porting-agon/draft.md | todo | todo | todo |
| ch23-ai-assisted | chapters/ch23-ai-assisted/draft.md | todo | todo | todo |
| appendix-a | appendices/appendix-a-z80-reference.md | todo | todo | todo |
| appendix-b | appendices/appendix-b-sine-tables.md | todo | todo | todo |
| appendix-c | appendices/appendix-c-compression.md | todo | todo | todo |
| appendix-g | appendices/appendix-g-ay-registers.md | todo | todo | todo |
| glossary | glossary.md | todo | todo | todo |

### How to resume

Each language can be translated independently. For each remaining file:

1. Read `translations/vocabulary.md` for consistent terminology
2. Read the English source file
3. Translate prose, keep all code blocks/image refs/formatting intact
4. Write to `translations/{es,ru,uk}/chapters/chNN-name.md` or `translations/{es,ru,uk}/appendices/...`

Output naming:
- `translations/es/chapters/ch11-sound.md`
- `translations/ru/appendices/appendix-a-z80-reference.md`
- `translations/uk/glossary.md`

### Rules reminder
- Never translate: proper names, product names, chip names, hex, register names
- Keep in English: all code blocks and code comments
- Translate: prose, headings, figure alt text
- Keep: markdown formatting, image paths, \newpage commands
