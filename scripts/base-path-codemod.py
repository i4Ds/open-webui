#!/usr/bin/env python3
"""Codemod for sub path support (WEBUI_BASE_PATH), see src/lib/utils/basePath.ts.

Idempotent; re-run it after merging upstream to catch new root paths:

    python3 scripts/base-path-codemod.py && git diff --stat

1. goto imported from $app/navigation -> $lib/utils/navigation (adds the base)
2. $page.url.pathname -> stripBase($page.url.pathname) (route comparisons)
3. href="/..." in Svelte templates -> href="{WEBUI_BASE_URL}/..."
"""

import re
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / 'src'
SKIP = {SRC / 'lib/utils/navigation.ts', SRC / 'lib/utils/basePath.ts'}

NAV_IMPORT = re.compile(r"import \{([^}]*)\} from '\$app/navigation';?")


def add_import(text: str, is_svelte: bool, name: str, module: str) -> str:
    # Already imported from that module?
    m = re.search(rf"import \{{([^}}]*)\}} from '{re.escape(module)}';?", text)
    if m:
        names = [n.strip() for n in m.group(1).split(',') if n.strip()]
        if name in names:
            return text
        new = m.group(0).replace(m.group(1), ' ' + ', '.join(names + [name]) + ' ')
        return text.replace(m.group(0), new, 1)
    line = f"import {{ {name} }} from '{module}';"
    if is_svelte:
        # instance script, not <script context="module"> / <script module>
        for s in re.finditer(r'<script\b([^>]*)>', text):
            if 'module' not in s.group(1):
                return text[: s.end()] + '\n\t' + line + text[s.end() :]
        return f'<script>\n\t{line}\n</script>\n\n' + text
    first_import = re.search(r'^import ', text, re.M)
    pos = first_import.start() if first_import else 0
    return text[:pos] + line + '\n' + text[pos:]


def transform(path: Path) -> bool:
    text = original = path.read_text()
    is_svelte = path.suffix == '.svelte'

    # 1. goto
    def nav(m: re.Match) -> str:
        names = [n.strip() for n in m.group(1).split(',') if n.strip()]
        if 'goto' not in names:
            return m.group(0)
        rest = [n for n in names if n != 'goto']
        out = "import { goto } from '$lib/utils/navigation';"
        if rest:
            out = f"import {{ {', '.join(rest)} }} from '$app/navigation';\n\t" + out
        return out

    text = NAV_IMPORT.sub(nav, text)

    # 2. pathname comparisons ("$page\n\t\t.url.pathname" occurs too)
    text, n_path = re.subn(
        r'(?<!stripBase\()\$page(\s*)\.url\.pathname', r'stripBase($page\1.url.pathname)', text
    )
    if n_path:
        text = add_import(text, is_svelte, 'stripBase', '$lib/utils/basePath')

    # 3. template links
    if is_svelte:
        text, n_href = re.subn(r'href="/(?!/)', 'href="{WEBUI_BASE_URL}/', text)
        if n_href:
            text = add_import(text, is_svelte, 'WEBUI_BASE_URL', '$lib/constants')

    if text != original:
        path.write_text(text)
        return True
    return False


changed = [
    p
    for p in sorted(SRC.rglob('*'))
    if p.suffix in ('.svelte', '.ts', '.js') and p not in SKIP and p.is_file() and transform(p)
]
print(f'{len(changed)} files changed')
for p in changed:
    print(' ', p.relative_to(SRC.parent))
