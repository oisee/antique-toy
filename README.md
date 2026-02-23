# Coding the Impossible

**Z80 Demoscene Techniques for Modern Makers**

A book about Z80/eZ80 assembly on ZX Spectrum and Agon Light 2, with deep focus on demoscene techniques. 23 chapters covering everything from T-state budgets and attribute plasma tunnels to wireframe 3D, digital drums, and full game development.

Companion demo project "Not Eager" included -- an AI-assisted multi-effect ZX Spectrum demo.

## Building the book

Requires [Pandoc](https://pandoc.org/) and LuaLaTeX (TeX Live).

```sh
make book-a4    # PDF, A4 format (402 pages)
make book-a5    # PDF, A5 format (545 pages)
make book-epub  # EPUB
make book       # all three
```

## Building the code examples

Requires [sjasmplus](https://github.com/z00m128/sjasmplus) (pinned as submodule in `tools/sjasmplus/`).

```sh
make            # compile all chapter examples
make test       # assemble all, report pass/fail
make demo       # build the "Not Eager" demo
```

## License

This project is licensed under [CC BY-NC 4.0](LICENSE.md):

- Free use for non-commercial purposes
- Modification and derivative works allowed
- Attribution required
- Commercial use requires separate permission

See [LICENSE.md](LICENSE.md) for details.

### Why this license?

CC BY-NC 4.0 protects original authors from the (unlikely but possible) scenario where third parties commercially exploit the material without the authors' consent. Unlike MIT, which permits any use including commercial, CC BY-NC 4.0 ensures that:

- The book remains freely available for educational and personal use
- Community improvements and corrections stay in the open
- Commercial publishing is only possible with the author's explicit permission

For commercial licensing inquiries, please contact the author.

(c) 2025-2026 Alice Vinogradova. All rights reserved.
