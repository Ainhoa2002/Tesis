#!/usr/bin/env python3
import os, re
root = os.path.join('TESIS','annex','LCI')
pattern = re.compile(r'^(\s*)def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(')

for dirpath, dirs, files in os.walk(root):
    for fn in files:
        if not fn.endswith('.py'):
            continue
        path = os.path.join(dirpath, fn)
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        changed = False
        out = []
        i = 0
        while i < len(lines):
            line = lines[i]
            m = pattern.match(line)
            if m and len(m.group(1))==0:
                # top-level def
                # find previous non-empty line index
                j = len(out)-1
                while j >=0 and out[j].strip()=='' : j-=1
                prev = out[j].lstrip() if j>=0 else ''
                if not prev.startswith('#'):
                    name = m.group(2)
                    human = name.lstrip('_').replace('_',' ').capitalize()
                    comment = f"# Purpose: {human}.\n"
                    out.append(comment)
                    changed = True
            out.append(line)
            i+=1
        if changed:
            with open(path, 'w', encoding='utf-8') as f:
                f.writelines(out)
            print(f'Updated: {path}')
