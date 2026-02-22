# Project "Not Eager" — AI-Assisted ZX Spectrum Demo

> An "inspired by Eager" demo, built with Claude Code to prove that AI *can* assist with Z80 demoscene coding.

## Concept

A response to Introspec's (valid) skepticism that AI doesn't really understand Z80.
We reverse-engineer the key techniques from Eager (2015) and build a new demo
that combines them with Dark's midpoint 3D engine from Spectrum Expert #02.

## Target Effects

1. **Attribute tunnel with 4-fold symmetry** (from Eager — Chapter 9)
2. **Chaos zoomer** (from Eager — Chapter 9)
3. **4-phase colour animation** (from Eager — Chapter 10)
4. **Midpoint 3D object** (from Dark/SE#02 — Chapter 5) — the new ingredient
5. **Digital drums on AY** (from Eager — Chapter 12)

## Technical Goals

- ZX Spectrum 128K (Pentagon timing)
- AY music with digital drum hits (n1k-o technique)
- Async frame generation (Introspec's dual-buffer approach)
- All code AI-assisted, documented step by step
- Release at a compo (Multimatograf? DiHalt? CC?)

## Why This Matters for the Book

- Chapter 23 case study: "we didn't just write *about* demos, we *made* one"
- Proves (or disproves) AI assistance for real Z80 work
- Gets Introspec's attention and (hopefully) collaboration

## Status

- [ ] Reverse-engineer Eager attribute tunnel inner loop
- [ ] Implement 4-fold symmetry copy routine
- [ ] Port Dark's midpoint 3D from SE#02 algorithms
- [ ] Build chaos zoomer with code generation
- [ ] AY music engine with digital drums
- [ ] Scripting/timeline engine
- [ ] Compose music (or find collaborator)
- [ ] Polish and release

## Build

```sh
make demo       # builds demo/src/*.a80 → demo/build/not-eager.tap
```
