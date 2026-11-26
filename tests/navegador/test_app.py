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


def _chegar_da_pagina_inicial(pagina, url):
    pagina.add_init_script("try { sessionStorage.setItem('syncup-entrada', '1') } catch {}")
    pagina.goto(f'{url}/app/#wrapped')


def test_chegada_logo_pousa_e_some(page, site_url):
    _chegar_da_pagina_inicial(page, site_url)
    expect(page.locator('.pouso')).to_be_attached()
    expect(page.locator('.pouso')).to_have_count(0, timeout=5_000)  # entrou em sintonia e pousou
    expect(page.locator('body')).to_have_class(re.compile('sintonizado'))
    # a logo de verdade volta quando a cópia pousa em cima dela
    expect(page.locator('#app .marca .logo:visible').first).to_have_css('opacity', '1')


def test_chegada_com_menos_movimento_sem_logo_grande(nova_pagina, site_url):
    pagina = nova_pagina(reduced_motion='reduce')
    _chegar_da_pagina_inicial(pagina, site_url)
    expect(pagina.locator('.pouso')).to_have_count(0)
    expect(pagina.locator('#principal .app-cabeca:visible')).to_be_visible()


def test_abrir_o_app_direto_sem_entrada(page, site_url):
    page.goto(f'{site_url}/app/#wrapped')
    expect(page.locator('.pouso')).to_have_count(0)


def test_wrapped_com_historico_curto_avisa_em_vez_dos_stories(page, site_url, tmp_path):
    curto = tmp_path / 'curto.json'
    curto.write_text(
        '[{"ts": "2023-12-29T03:00:00Z", "ms_played": 200000,'
        ' "master_metadata_track_name": "Faixa", "master_metadata_album_artist_name": "Banda"}]',
        encoding='utf-8',
    )
    page.goto(f'{site_url}/app/#wrapped')
    tela = page.get_by_role('region', name='Seu histórico')
    tela.locator('input[type=file]').first.set_input_files(curto)
    expect(tela.get_by_text('Lido neste aparelho')).to_be_visible(timeout=TEMPO)
    page.get_by_role('button', name='Montar meu Wrapped').click()
    expect(page.locator('[role=alert]:visible')).to_contain_text(
        'Histórico curto demais', timeout=TEMPO
    )
    expect(page.locator('.resultado .st-player:visible')).to_have_count(0)
