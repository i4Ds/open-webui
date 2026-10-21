"""Sub path support (WEBUI_BASE_PATH): pytest backend/open_webui/test/test_base_path.py"""

import asyncio

import pytest

from open_webui.utils.base_path import BasePathMiddleware, rewrite_html, with_base_path

BASE = '/planet-express'


@pytest.mark.parametrize(
    'url, expected',
    [
        ('/static/x.png', '/planet-express/static/x.png'),
        ('/?q=1', '/planet-express/?q=1'),
        ('/planet-express/x', '/planet-express/x'),
        ('/planet-express', '/planet-express'),
        ('//cdn.example/x', '//cdn.example/x'),
        ('https://idp.example/x', 'https://idp.example/x'),
        ('relative/x', 'relative/x'),
    ],
)
def test_with_base_path(url, expected):
    assert with_base_path(BASE, url) == expected
    assert with_base_path('', url) == url


def test_rewrite_html():
    html = (
        '<link href="/_app/immutable/a.js" rel="modulepreload">'
        '<link rel="manifest" href="/manifest.json">'
        '<script>__sveltekit_1v0 = {\n\t\tbase: ""\n\t};'
        'import("/_app/immutable/entry/start.js"); x = \'/static/splash.png\';'
        'y = "/api/v1/x"; z = "/_apple";</script>'
    )
    out = rewrite_html(html, BASE, ['_app', 'static', 'manifest.json'])
    assert 'base: "/planet-express"' in out
    assert 'href="/planet-express/_app/immutable/a.js"' in out
    assert 'import("/planet-express/_app/immutable/entry/start.js")' in out
    assert "'/planet-express/static/splash.png'" in out
    assert 'href="/planet-express/manifest.json"' in out
    # not a build dir entry / only a prefix of one
    assert '"/api/v1/x"' in out and '"/_apple"' in out
    assert rewrite_html(html, '', ['_app']) == html


def _run(path: str, location: bytes):
    seen = {}

    async def app(scope, receive, send):
        seen['path'] = scope['path']
        await send({'type': 'http.response.start', 'status': 302, 'headers': [(b'location', location)]})

    sent = []

    async def send(message):
        sent.append(message)

    scope = {'type': 'http', 'path': path, 'raw_path': path.encode()}
    asyncio.run(BasePathMiddleware(app, BASE)(scope, None, send))
    return seen['path'], dict(sent[0]['headers'])[b'location']


@pytest.mark.parametrize(
    'path, expected',
    [
        ('/planet-express/c/1', '/c/1'),  # proxy passes the prefix through
        ('/planet-express', '/'),
        ('/c/1', '/c/1'),  # proxy strips the prefix
        ('/planet-expressX', '/planet-expressX'),
    ],
)
def test_middleware_paths_and_redirects(path, expected):
    assert _run(path, b'/static/favicon.png') == (expected, b'/planet-express/static/favicon.png')


def test_middleware_keeps_external_redirects():
    assert _run('/x', b'https://idp.example/x')[1] == b'https://idp.example/x'
