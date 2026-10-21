"""Serve Open WebUI under a sub path (WEBUI_BASE_PATH), e.g. behind a reverse
proxy at https://example.org/chat/.

The frontend is built once with base "" and learns the real base at runtime:
SvelteKit reads `base` from the bootstrap object in index.html, which
`rewrite_html` fills in. Everything that leaves the backend as a root-relative
URL (index.html asset links, redirects) gets the prefix here; the frontend
handles its own URLs (see src/lib/utils/basePath.ts).
"""

import os
import re
from pathlib import Path

from starlette.types import ASGIApp, Message, Receive, Scope, Send


def with_base_path(base: str, url: str) -> str:
    """Prefix a root-relative URL ("/x") with base; leave everything else alone."""
    if not base or not url.startswith('/') or url.startswith('//'):
        return url
    if url == base or url.startswith(base + '/') or url.startswith(base + '?'):
        return url
    return base + url


_BOOTSTRAP_BASE = re.compile(r'(__sveltekit_\w+\s*=\s*\{\s*base:\s*)""')


def rewrite_html(html: str, base: str, top_level_names: list[str]) -> str:
    """Point a built index.html at base: SvelteKit's runtime base plus every
    quoted root-relative reference to a top-level entry of the build dir
    ("/_app/...", "/static/...", "/manifest.json", ...)."""
    if not base:
        return html
    html = _BOOTSTRAP_BASE.sub(lambda m: f'{m.group(1)}"{base}"', html)
    if top_level_names:
        names = '|'.join(re.escape(n) for n in sorted(top_level_names, key=len, reverse=True))
        html = re.sub(rf'(?<=["\'(])/(?=(?:{names})(?:[/"\'?#)]|$))', base + '/', html)
    return html


def build_dir_entries(directory: str | os.PathLike) -> list[str]:
    try:
        return [p.name for p in Path(directory).iterdir() if not p.name.startswith('.')]
    except OSError:
        return []


class BasePathMiddleware:
    """Accept requests with or without the base prefix (proxies differ in
    whether they strip it) and prefix root-relative Location headers, so
    redirects stay under the base path."""

    def __init__(self, app: ASGIApp, base: str) -> None:
        self.app = app
        self.base = base
        self.base_bytes = base.encode()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] not in ('http', 'websocket') or not self.base:
            await self.app(scope, receive, send)
            return

        path = scope.get('path', '')
        if path == self.base or path.startswith(self.base + '/'):
            scope = dict(scope)
            scope['path'] = path[len(self.base) :] or '/'
            raw_path = scope.get('raw_path')
            if raw_path and raw_path.startswith(self.base_bytes):
                scope['raw_path'] = raw_path[len(self.base_bytes) :] or b'/'

        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: Message) -> None:
            if message['type'] == 'http.response.start':
                headers = []
                for name, value in message.get('headers', []):
                    if name.lower() == b'location':
                        value = with_base_path(self.base, value.decode('latin-1')).encode('latin-1')
                    headers.append((name, value))
                message = {**message, 'headers': headers}
            await send(message)

        await self.app(scope, receive, send_wrapper)
