"""O site como é publicado (endereços com ?v=): o Match roda e nenhum módulo é pedido sem a versão."""

import functools
import shutil
import threading
from http.server import ThreadingHTTPServer

import pytest
from conftest import SITE, _Silencioso
from playwright.sync_api import expect

from tools.versionar_site import versionar

pytestmark = pytest.mark.navegador


def test_site_versionado_roda_o_match_sem_pedir_arquivo_sem_versao(page, site_url, tmp_path):
    copia = tmp_path / 'site'
    shutil.copytree(SITE, copia)
    versionar(copia / 'app', 'teste1')
    servidor = ThreadingHTTPServer(
        ('127.0.0.1', 0), functools.partial(_Silencioso, directory=str(copia))
    )
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    pedidos = []
    page.context.on('request', lambda r: pedidos.append(r.url))
    try:
        page.goto(f'http://127.0.0.1:{servidor.server_address[1]}/app/#match')
        page.locator('.match-area').get_by_role('button', name='Ver um exemplo').click()
        expect(page.locator('#resultado-match > *').first).to_be_attached(timeout=60_000)
    finally:
        servidor.shutdown()
    do_app = [u for u in pedidos if '/app/' in u and u.split('?')[0].endswith(('.js', '.css'))]
    assert any('match-worker.js?v=teste1' in u for u in do_app), do_app
    assert all(u.endswith('?v=teste1') for u in do_app), [u for u in do_app if 'teste1' not in u]
