#!/usr/bin/env python3
"""Build script for "Coding the Impossible" book.

Concatenates chapter markdown, manages version, calls pandoc for PDF/EPUB.
Based on the abap-deep-dive build system.

Usage:
    python3 build_book.py --pdf           # A4 PDF (English)
    python3 build_book.py --pdf-a5        # A5 PDF
    python3 build_book.py --epub          # EPUB
    python3 build_book.py --all           # all three formats
    python3 build_book.py --lang es       # Spanish edition (ES suffix)
    python3 build_book.py --lang ru       # Russian edition
    python3 build_book.py --lang uk       # Ukrainian edition
    python3 build_book.py --bump          # increment version (v9 → v10)
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from glob import glob
from pathlib import Path

ROOT = Path(__file__).parent
BUILD_DIR = ROOT / "build"
VERSION_FILE = ROOT / "version.json"

TITLE = "Coding the Impossible"
SUBTITLE = "Z80 Demoscene Techniques for Modern Makers"
AUTHOR = "Alice Vinogradova"
LANG = "en"

# Chapters in order (glob sorts correctly thanks to chNN- prefix)
CHAPTER_GLOB = "chapters/ch*/draft.md"
EXTRA_FILES = ["glossary.md"]
APPENDIX_GLOB = "appendices/appendix-*.md"

# Translated editions
TRANSLATIONS = {
    "es": {
        "title": "Programando lo Imposible",
        "subtitle": "Técnicas de Demoscene Z80 para Creadores Modernos",
        "lang": "es",
        "chapter_glob": "translations/es/chapters/ch*.md",
        "appendix_glob": "translations/es/appendices/appendix-*.md",
        "extra_files": ["translations/es/glossary.md"],
    },
    "ru": {
        "title": "Программируя невозможное",
        "subtitle": "Демосценовые техники Z80 для современных разработчиков",
        "lang": "ru",
        "chapter_glob": "translations/ru/chapters/ch*.md",
        "appendix_glob": "translations/ru/appendices/appendix-*.md",
        "extra_files": ["translations/ru/glossary.md"],
    },
    "uk": {
        "title": "Програмуючи неможливе",
        "subtitle": "Демосценові техніки Z80 для сучасних розробників",
        "lang": "uk",
        "chapter_glob": "translations/uk/chapters/ch*.md",
        "appendix_glob": "translations/uk/appendices/appendix-*.md",
        "extra_files": ["translations/uk/glossary.md"],
    },
}


def load_version():
    if VERSION_FILE.exists():
        with open(VERSION_FILE) as f:
            data = json.load(f)
        # Migrate from old major/minor/build_number format
        if "version" not in data:
            data = {"version": 9, "last_build": data.get("last_build", "")}
            save_version(data)
        return data
    return {"version": 1, "last_build": ""}


def save_version(v):
    with open(VERSION_FILE, "w") as f:
        json.dump(v, f, indent=2)
        f.write("\n")


def bump_version(v):
    v["version"] += 1
    v["last_build"] = datetime.now().isoformat(timespec="seconds")
    save_version(v)
    return v


def version_tag(v):
    """Return version tag string, e.g. 'v9'."""
    return f"v{v['version']}"


def version_string(v):
    """Return full version string for filenames: 'v9_20260224'."""
    date = datetime.now().strftime("%Y%m%d")
    return f"v{v['version']}_{date}"


DISCLAIMER_FILE = ROOT / "disclaimer.md"

# Regex matching tagged code fences: ```lang src:path [lines:N..M]
_TAGGED_SRC_RE = re.compile(
    r'^```(\w+)((?:\s+\w+:\S+)+)\s*$'
)


def preprocess_listings(text, base_dir=ROOT):
    """Replace content of src:-tagged code blocks with fresh source file content.

    Called during book build to ensure PDF always has the latest code,
    even if .md files are stale. Only processes src: tags (not id: tags,
    which are self-contained in the .md).
    """
    lines = text.split('\n')
    out = []
    i = 0

    while i < len(lines):
        m = _TAGGED_SRC_RE.match(lines[i])
        if m:
            tag_str = m.group(2)
            tags = {}
            for tm in re.finditer(r'(\w+):(\S+)', tag_str):
                tags[tm.group(1)] = tm.group(2)

            if 'src' in tags:
                # Keep the fence opening
                out.append(lines[i])

                # Skip old content until closing ```
                j = i + 1
                while j < len(lines) and lines[j].rstrip() != '```':
                    j += 1

                # Resolve source file
                src_path = tags['src']
                full_path = base_dir / src_path
                if not full_path.exists():
                    full_path = ROOT / src_path

                if full_path.exists():
                    src_text = full_path.read_text(encoding='utf-8')
                    src_lines = src_text.split('\n')

                    # Apply line range if specified
                    if 'lines' in tags:
                        parts = tags['lines'].split('..')
                        if len(parts) == 2:
                            start, end = int(parts[0]), int(parts[1])
                            src_lines = src_lines[start - 1:end]

                    out.extend(src_lines)
                else:
                    # Source missing — keep original inline content
                    k = i + 1
                    while k < j:
                        out.append(lines[k])
                        k += 1

                # Add closing fence
                if j < len(lines):
                    out.append(lines[j])
                i = j + 1
                continue

        out.append(lines[i])
        i += 1

    return '\n'.join(out)


def strip_fence_tags(text):
    """Strip everything after the language identifier on code fence lines.

    Our source .md files use ```z80 id:ch01_xxx (and other tags) which pandoc
    doesn't recognise — it expects ```z80 or ```{.z80 #id}. Without this fix,
    pandoc treats the fence as inline code and collapses the block into one line.

    Converts: ```z80 id:ch01_xxx src:path lines:1..5
    To:        ```z80
    """
    return re.sub(
        r'^(```\w+)\s+.+$',
        r'\1',
        text,
        flags=re.MULTILINE,
    )


def combine_chapters(chapter_glob=CHAPTER_GLOB, extra_files=EXTRA_FILES,
                     appendix_glob=APPENDIX_GLOB):
    """Concatenate all chapters + extras into a single markdown string."""
    chapters = sorted(glob(str(ROOT / chapter_glob)))
    if not chapters:
        print(f"ERROR: no chapter files found matching {chapter_glob}", file=sys.stderr)
        sys.exit(1)

    parts = []

    # Prepend disclaimer page if it exists
    if DISCLAIMER_FILE.exists():
        parts.append(DISCLAIMER_FILE.read_text(encoding='utf-8'))

    for i, path in enumerate(chapters):
        with open(path, encoding="utf-8") as f:
            content = f.read()
        if i > 0:
            parts.append("\n\\newpage\n")
        parts.append(content)

    # Append extra files (glossary, index)
    for name in extra_files:
        path = ROOT / name
        if path.exists():
            parts.append("\n\\newpage\n")
            with open(path, encoding="utf-8") as f:
                parts.append(f.read())

    # Append appendices (sorted alphabetically: appendix-a, appendix-b, ...)
    appendices = sorted(glob(str(ROOT / appendix_glob)))
    for path in appendices:
        parts.append("\n\\newpage\n")
        with open(path, encoding="utf-8") as f:
            parts.append(f.read())

    return "\n".join(parts)


def write_metadata(vs, vtag="", paper="a4", title=TITLE, subtitle=SUBTITLE, lang=LANG):
    """Generate metadata.yaml for pandoc with version on title page."""
    meta = BUILD_DIR / "metadata.yaml"
    date = datetime.now().strftime("%Y-%m-%d")
    date_line = f"{AUTHOR} --- {vtag} ({date})"

    content = f"""---
title: "{title}"
subtitle: "{subtitle}"
author: "{AUTHOR}"
date: "{date_line}"
lang: {lang}
documentclass: book
classoption:
  - openany
mainfont: "DejaVu Serif"
sansfont: "DejaVu Sans"
monofont: "DejaVu Sans Mono"
monofontoptions:
  - Scale=0.85
toc: true
toc-depth: 2
highlight-style: tango
header-includes: |
  \\usepackage{{fvextra}}
  \\DefineVerbatimEnvironment{{Highlighting}}{{Verbatim}}{{breaklines,commandchars=\\\\\\{{\\}}}}
---
"""
    meta.write_text(content)
    return meta


def write_combined(text, vs):
    """Write combined markdown to build dir."""
    out = BUILD_DIR / f"combined_{vs}.md"
    out.write_text(text, encoding="utf-8")
    # Also write as "latest" for convenience
    latest = BUILD_DIR / "combined.md"
    latest.write_text(text, encoding="utf-8")
    return latest


def run_pandoc(args, label):
    print(f"  Building {label}...")
    cmd = ["pandoc", f"--resource-path={ROOT}"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR building {label}:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    if result.stderr:
        # Print warnings but don't fail
        for line in result.stderr.strip().split("\n"):
            if line.strip():
                print(f"  [warn] {line}")


def _copy_stable(out, base, ext):
    """Copy build output to stable name: book-a4-v9-ES.pdf."""
    import shutil
    stable = BUILD_DIR / f"{base}{ext}"
    shutil.copy2(out, stable)
    print(f"    → {stable.name}")


def build_pdf_a4(meta, combined, vs, vtag, lang_suffix=""):
    out = BUILD_DIR / f"Coding_the_Impossible_{vs}{lang_suffix}.pdf"
    run_pandoc([
        str(meta), str(combined),
        "-o", str(out),
        "--pdf-engine=lualatex",
        "-V", "fontsize=11pt",
        "-V", "geometry=a4paper, margin=1in",
    ], f"A4 PDF → {out.name}")
    _copy_stable(out, f"book-a4-{vtag}{lang_suffix}", ".pdf")
    return out


def build_pdf_a5(meta, combined, vs, vtag, lang_suffix=""):
    out = BUILD_DIR / f"Coding_the_Impossible_{vs}{lang_suffix}_A5.pdf"
    run_pandoc([
        str(meta), str(combined),
        "-o", str(out),
        "--pdf-engine=lualatex",
        "-V", "fontsize=10pt",
        "-V", "geometry=a5paper, top=15mm, bottom=15mm, left=18mm, right=15mm",
    ], f"A5 PDF → {out.name}")
    _copy_stable(out, f"book-a5-{vtag}{lang_suffix}", ".pdf")
    return out


def build_epub(meta, combined, vs, vtag, lang_suffix=""):
    out = BUILD_DIR / f"Coding_the_Impossible_{vs}{lang_suffix}.epub"
    run_pandoc([
        str(meta), str(combined),
        "-o", str(out),
        "--epub-chapter-level=1",
    ], f"EPUB → {out.name}")
    _copy_stable(out, f"book-{vtag}{lang_suffix}", ".epub")
    return out


CHANGELOG_FILE = ROOT / "CHANGELOG.md"


def main():
    parser = argparse.ArgumentParser(description="Build Coding the Impossible book")
    parser.add_argument("--pdf", action="store_true", help="Build A4 PDF")
    parser.add_argument("--pdf-a5", action="store_true", help="Build A5 PDF")
    parser.add_argument("--epub", action="store_true", help="Build EPUB")
    parser.add_argument("--all", action="store_true", help="Build all formats")
    parser.add_argument("--lang", default="en", choices=["en", "es", "ru", "uk"],
                        help="Language edition to build (default: en)")
    parser.add_argument("--bump", action="store_true", help="Bump version (v9 → v10)")
    parser.add_argument("--no-increment", action="store_true", help="Don't update last_build timestamp")
    parser.add_argument("--no-changelog", action="store_true", help="Skip changelog appendix")
    args = parser.parse_args()

    # Default to --all if nothing specified
    if not (args.pdf or args.pdf_a5 or args.epub or args.all or args.bump):
        args.all = True

    v = load_version()

    # Handle version bump
    if args.bump:
        v = bump_version(v)
        print(f"Version bumped to {version_tag(v)}")
        args.all = True

    if args.all:
        args.pdf = args.pdf_a5 = args.epub = True

    # Update last_build timestamp
    if not args.no_increment:
        v["last_build"] = datetime.now().isoformat(timespec="seconds")
        save_version(v)

    # Resolve language settings
    if args.lang != "en":
        tr = TRANSLATIONS[args.lang]
        build_title = tr["title"]
        build_subtitle = tr["subtitle"]
        build_lang = tr["lang"]
        build_chapter_glob = tr["chapter_glob"]
        build_appendix_glob = tr["appendix_glob"]
        build_extra_files = tr["extra_files"]
        lang_suffix = f"_{args.lang.upper()}"
    else:
        build_title = TITLE
        build_subtitle = SUBTITLE
        build_lang = LANG
        build_chapter_glob = CHAPTER_GLOB
        build_appendix_glob = APPENDIX_GLOB
        build_extra_files = EXTRA_FILES
        lang_suffix = ""

    vtag = version_tag(v)
    vs = version_string(v)
    print(f"Building: {build_title} [{vtag}] ({args.lang.upper()})")

    # Prepare
    BUILD_DIR.mkdir(exist_ok=True)
    text = combine_chapters(build_chapter_glob, build_extra_files, build_appendix_glob)

    # Resolve src:-tagged code blocks with fresh source content
    text = preprocess_listings(text)

    # Strip custom fence tags (id:, src:, lines:) so pandoc sees clean fences
    text = strip_fence_tags(text)

    # Fix image paths: chapters use ../../build/ which breaks in combined.md
    text = text.replace('../../build/', 'build/')

    # Append changelog appendix (EN only, manually maintained CHANGELOG.md)
    if args.lang == "en" and not args.no_changelog and CHANGELOG_FILE.exists():
        print("  Including CHANGELOG.md")
        text += "\n\\newpage\n"
        text += "\n" + CHANGELOG_FILE.read_text(encoding="utf-8")

    combined = write_combined(text, vs)
    meta = write_metadata(vs, vtag=vtag, title=build_title, subtitle=build_subtitle, lang=build_lang)

    outputs = []
    if args.pdf:
        outputs.append(build_pdf_a4(meta, combined, vs, vtag, lang_suffix))
    if args.pdf_a5:
        outputs.append(build_pdf_a5(meta, combined, vs, vtag, lang_suffix))
    if args.epub:
        outputs.append(build_epub(meta, combined, vs, vtag, lang_suffix))

    print(f"\nDone. {len(outputs)} file(s) built:")
    for o in outputs:
        size = o.stat().st_size
        if size > 1024 * 1024:
            print(f"  {o.name}  ({size / 1024 / 1024:.1f} MB)")
        else:
            print(f"  {o.name}  ({size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
