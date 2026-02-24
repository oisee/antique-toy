Eremus, [2026-02-23 23:00]
A wonderful job Alice!

Eremus, [2026-02-23 23:00]
VERY interesting and, in a fast view, it seems an invaluable resource for everyone who wants to optimize his Z80 ASM coding skills

Eremus, [2026-02-23 23:02]
One question: Do you plan to add some info and coding examples for dealing with contended machines (Spectrum 48K and 128K). As you surely know they are the "standard" on West Europe and Pentagon was unknown here in eighties and nineties.

Alice V., [2026-02-23 23:10]
yes, sure, based on Introspec's article: "Go West" (how to adapt Pentagon/TR-Dos demos/games to Classic ZX 48k/128 etc)

( https://hype.retroscene.org/blog/dev/130.html - part 1
  https://hype.retroscene.org/blog/dev/230.html - part 2)

and code examples should be contended-friendly (maybe they not yet right now - but the goal is to be Classic-friendly)

Eremus, [2026-02-24 00:01]
"GO WEST"

Eremus, [2026-02-24 00:01]
https://youtu.be/LNBjMRvOB5M?si=UCRfiqo7ezkSN7LG

---

## Key points

1. **Positive reception:** "invaluable resource for everyone who wants to optimize Z80 ASM coding skills"

2. **Request: contended memory coverage.** Spectrum 48K and 128K have ULA contention (6,5,4,3,2,1,0,0 pattern). Pentagon does not. Western European scene used real Spectrums, not Pentagons. Contended timing affects every inner loop that touches $4000-$7FFF.

3. **"Go West" reference:** Introspec's two-part article on adapting Pentagon code to classic Spectrums:
   - Part 1: https://hype.retroscene.org/blog/dev/130.html
   - Part 2: https://hype.retroscene.org/blog/dev/230.html

## Actions needed

- Expand contended memory coverage (currently mentioned in ch01 and ch15, but examples assume Pentagon timing)
- Consider adding contended-friendly variants of key inner loops
- Reference "Go West" articles as primary source
- Goal: all code examples should work correctly on both Pentagon and classic 48K/128K
