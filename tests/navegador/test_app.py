"""App web de ponta a ponta: exemplo dos quatro modos, pré-leitura e "menos movimento"."""

import re
from pathlib import Path

import pytest
from playwright.sync_api import expect

SITE = Path(__file__).resolve().parents[2] / 'site'

pytestmark = pytest.mark.navegador

TEMPO = 45_000  # a Dupla e a Batalha montam no Worker; o CI é mais lento que o PC


def _abrir_exemplo(pagina, url, modo):
    pagina.goto(f'{url}/app/#{modo}')
    # Os quatro modos ficam montados; só o visível aparece para o get_by_role.
    pagina.get_by_role('button', name='Ver um exemplo').click()
    player = pagina.locator('.resultado .st-player:visible').first
    expect(player).to_be_visible(timeout=TEMPO)
    return player


@pytest.mark.parametrize('modo', ['wrapped', 'dupla', 'batalha', 'match'])
def test_exemplo_chega_aos_stories_e_avanca(page, site_url, modo):
    player = _abrir_exemplo(page, site_url, modo)
    contador = player.locator('.st-contador')
    expect(contador).to_have_text(re.compile(r'^\d+/\d+$'))
    player.focus()
    player.press(' ')  # pausa: o relógio não avança sozinho no meio do teste
    expect(player).to_have_class(re.compile(r'\bpausado\b'))
    atual, total = map(int, contador.inner_text().split('/'))
    assert total > 1
    player.press('ArrowRight')
    expect(contador).to_have_text(f'{min(atual + 1, total)}/{total}')


def test_pre_leitura_mostra_periodo_e_reproducoes(page, site_url):
    page.goto(f'{site_url}/app/#wrapped')
    # Os quatro modos ficam montados: o cartão certo é o da tela visível.
    tela = page.get_by_role('region', name='Seu histórico')
    tela.locator('input[type=file]').first.set_input_files(SITE / 'app' / 'demo-wrapped.zip')
    painel = tela.locator('dl.telemetria')
    expect(painel).to_be_visible(timeout=TEMPO)
    expect(painel.locator('.tl-periodo dd')).to_have_text(re.compile(r'.+ → .+'))
    expect(painel).to_contain_text('Reproduções')
    expect(tela.get_by_text('Lido neste aparelho')).to_be_visible()


def test_menos_movimento_troca_direto(nova_pagina, site_url):
    pagina = nova_pagina(reduced_motion='reduce')
    player = _abrir_exemplo(pagina, site_url, 'wrapped')
    expect(player).to_be_focused()  # sem a transição, o foco vai direto para o player


def test_app_sem_rolagem_lateral_no_celular(nova_pagina, site_url):
    pagina = nova_pagina(viewport={'width': 375, 'height': 812})
    _abrir_exemplo(pagina, site_url, 'wrapped')
    largura = pagina.evaluate('document.documentElement.scrollWidth - innerWidth')
    assert largura <= 0, f'rola {largura}px para o lado'
