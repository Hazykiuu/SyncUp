"""Testes de navegador (pytest -m navegador): o site/ servido localmente e aberto no Chromium.

Precisa de requirements-e2e.txt e `python -m playwright install chromium`. Sem o Playwright, esta pasta
fica fora da coleta, e o pytest normal segue igual.
"""

import functools
import subprocess
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

try:
    import playwright  # noqa: F401
except ImportError:
    collect_ignore_glob = ['test_*.py']

RAIZ = Path(__file__).resolve().parents[2]
SITE = RAIZ / 'site'
DEMOS = ['demo-wrapped.zip', 'demo-bruno.zip', 'demo-carla.zip', 'demo-davi.zip']
# O app só carrega o htm (Preact) de fora; o resto da rede é cortado para o teste não depender dela.
HOSTS_PERMITIDOS = ('127.0.0.1', 'unpkg.com')


class _Silencioso(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture(scope='session')
def site_url():
    # As demos do "Ver um exemplo" ficam no .gitignore: gera se faltarem (o CI também gera antes).
    if not all((SITE / 'app' / d).exists() for d in DEMOS):
        subprocess.run(
            [sys.executable, str(RAIZ / 'tools' / 'empacotar_web.py')], check=True, cwd=RAIZ
        )
    servidor = ThreadingHTTPServer(
        ('127.0.0.1', 0), functools.partial(_Silencioso, directory=str(SITE))
    )
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    yield f'http://127.0.0.1:{servidor.server_address[1]}'
    servidor.shutdown()


def _vigiar(pagina, erros):
    pagina.route(
        '**/*',
        lambda rota: rota.continue_()
        if any(f'//{h}' in rota.request.url for h in HOSTS_PERMITIDOS)
        else rota.abort(),
    )
    pagina.on('pageerror', lambda e: erros.append(f'pageerror: {e}'))
    # "Failed to load resource" é a rede externa cortada acima (capas, trechos), não um erro do app.
    pagina.on(
        'console',
        lambda m: m.type == 'error'
        and 'Failed to load resource' not in m.text
        and erros.append(f'console: {m.text}'),
    )


@pytest.fixture
def erros():
    return []


@pytest.fixture
def page(page, erros):
    """A página do pytest-playwright, com rede externa cortada e sem erro de JS no console."""
    _vigiar(page, erros)
    yield page
    assert not erros, '\n'.join(erros)


@pytest.fixture
def nova_pagina(browser, erros):
    """Abre um contexto com opções próprias (ex.: reduced_motion) e vigia os erros do mesmo jeito."""
    contextos = []

    def abrir(**opcoes):
        ctx = browser.new_context(**opcoes)
        contextos.append(ctx)
        pagina = ctx.new_page()
        _vigiar(pagina, erros)
        return pagina

    yield abrir
    for ctx in contextos:
        ctx.close()
    assert not erros, '\n'.join(erros)
