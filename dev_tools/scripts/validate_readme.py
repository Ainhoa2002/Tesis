#!/usr/bin/env python3
"""Validate README.md references for LCI_MEXICO_CONVERTER.
Checks that referenced .py, .csv, .md files exist under the converter folder.
"""
import re
from pathlib import Path

CONVERTER_DIR = Path('TESIS/annex/LCI/LCI_MEXICO_CONVERTER')
README = CONVERTER_DIR / 'README.md'

pattern = re.compile(r"\(([^)]+\.(?:py|csv|md))\)")
# also catch bare filenames like Pipeline.py mentioned
bare_pattern = re.compile(r"\b([A-Za-z0-9_\-/]+\.(?:py|csv|md))\b")

if not README.exists():
    print('README not found:', README)
    raise SystemExit(1)

text = README.read_text(encoding='utf-8')
refs = set(pattern.findall(text))
# also add bare mentions
refs.update(bare_pattern.findall(text))

missing = []
for ref in sorted(refs):
    # normalize potential ../ references
    p = (CONVERTER_DIR / ref).resolve()
    # allow references that target parent folder (../)
    if not p.exists():
        # try resolving relative to repo root
        alt = Path(ref)
        if not alt.exists():
            missing.append(ref)

if missing:
    print('Missing files referenced in README:')
    for m in missing:
        print(' -', m)
    raise SystemExit(2)

print('All referenced files in README exist (or are external).')
