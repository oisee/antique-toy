#!/usr/bin/env python3
"""Translation manifest manager.

Tracks which English source version each translation was made from.
Prevents re-translating unchanged chapters and detects stale translations.

Usage:
    python3 translations/manifest.py stamp es          # record current EN hashes for ES translations
    python3 translations/manifest.py stamp ru uk       # stamp multiple languages
    python3 translations/manifest.py check es          # show what needs (re)translation
    python3 translations/manifest.py check all         # check all languages
    python3 translations/manifest.py diff es           # show EN chapters changed since last translation
"""

import hashlib
import json
import sys
from glob import glob
from pathlib import Path

ROOT = Path(__file__).parent.parent
TRANSLATIONS_DIR = ROOT / "translations"
MANIFEST_FILE = TRANSLATIONS_DIR / "manifest.json"

LANGUAGES = ["es", "ru", "uk"]

# All translatable sources, mapped to their output names
def get_sources():
    sources = {}
    # Chapters
    for p in sorted(glob(str(ROOT / "chapters/ch*/draft.md"))):
        p = Path(p)
        name = p.parent.name  # e.g. "ch11-sound"
        sources[f"chapters/{name}"] = p
    # Appendices
    for p in sorted(glob(str(ROOT / "appendices/appendix-*.md"))):
        p = Path(p)
        sources[f"appendices/{p.stem}"] = p
    # Glossary
    g = ROOT / "glossary.md"
    if g.exists():
        sources["glossary"] = g
    return sources


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest():
    if MANIFEST_FILE.exists():
        return json.loads(MANIFEST_FILE.read_text())
    return {}


def save_manifest(data):
    MANIFEST_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def translation_path(lang, key):
    """Get expected translation file path for a source key."""
    if key.startswith("chapters/"):
        name = key.split("/")[1]
        return TRANSLATIONS_DIR / lang / "chapters" / f"{name}.md"
    elif key.startswith("appendices/"):
        name = key.split("/")[1]
        return TRANSLATIONS_DIR / lang / "appendices" / f"{name}.md"
    elif key == "glossary":
        return TRANSLATIONS_DIR / lang / "glossary.md"
    return None


def cmd_stamp(langs):
    """Record SHA256 of English sources for existing translations."""
    sources = get_sources()
    manifest = load_manifest()

    for lang in langs:
        if lang not in manifest:
            manifest[lang] = {}
        count = 0
        for key, src_path in sources.items():
            tr_path = translation_path(lang, key)
            if tr_path and tr_path.exists():
                manifest[lang][key] = {
                    "source_sha256": sha256(src_path),
                    "translation_sha256": sha256(tr_path),
                }
                count += 1
        print(f"  {lang}: stamped {count} translations")

    save_manifest(manifest)
    print(f"Saved to {MANIFEST_FILE}")


def cmd_check(langs):
    """Show translation status for each language."""
    sources = get_sources()
    manifest = load_manifest()

    for lang in langs:
        lang_manifest = manifest.get(lang, {})
        missing = []
        stale = []
        ok = []

        for key, src_path in sources.items():
            tr_path = translation_path(lang, key)
            if not tr_path or not tr_path.exists():
                missing.append(key)
                continue

            entry = lang_manifest.get(key)
            if not entry:
                # Translated but not stamped — treat as ok but unstamped
                ok.append(f"{key} (unstamped)")
                continue

            current_sha = sha256(src_path)
            if current_sha != entry["source_sha256"]:
                stale.append(key)
            else:
                ok.append(key)

        print(f"\n=== {lang.upper()} ===")
        print(f"  OK: {len(ok)}  |  Stale: {len(stale)}  |  Missing: {len(missing)}")
        if stale:
            print(f"  STALE (EN source changed):")
            for k in stale:
                print(f"    - {k}")
        if missing:
            print(f"  MISSING:")
            for k in missing:
                print(f"    - {k}")


def cmd_diff(langs):
    """Show which EN files changed since last stamp."""
    sources = get_sources()
    manifest = load_manifest()

    for lang in langs:
        lang_manifest = manifest.get(lang, {})
        print(f"\n=== {lang.upper()} — changed since last translation ===")
        changed = False
        for key, src_path in sources.items():
            entry = lang_manifest.get(key)
            if entry and sha256(src_path) != entry["source_sha256"]:
                print(f"  CHANGED: {key}")
                changed = True
        if not changed:
            print("  All up to date!")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    lang_args = sys.argv[2:]

    if "all" in lang_args:
        langs = LANGUAGES
    else:
        langs = [l for l in lang_args if l in LANGUAGES]
        if not langs:
            print(f"Unknown language(s): {lang_args}. Use: {LANGUAGES} or 'all'")
            sys.exit(1)

    if cmd == "stamp":
        cmd_stamp(langs)
    elif cmd == "check":
        cmd_check(langs)
    elif cmd == "diff":
        cmd_diff(langs)
    else:
        print(f"Unknown command: {cmd}. Use: stamp, check, diff")
        sys.exit(1)


if __name__ == "__main__":
    main()
