"""Página inicial aberta no navegador: seções novas, caminho para o app e celular."""

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.navegador


def test_pagina_inicial_leva_ao_app(page, site_url):
    page.goto(f'{site_url}/')
    expect(page.locator('#jornada')).to_be_visible()
    expect(page.locator('section.respiro')).to_be_visible()
    page.locator('section.respiro').get_by_role('link', name='Abrir o app').click()
    expect(page).to_have_url(f'{site_url}/app/')
    expect(page.locator('nav.nav-app')).to_be_visible()


def test_pagina_inicial_sem_rolagem_lateral_no_celular(nova_pagina, site_url):
    pagina = nova_pagina(viewport={'width': 375, 'height': 812})
    pagina.goto(f'{site_url}/')
    pagina.mouse.wheel(0, 4000)  # passa pela jornada presa na tela
    largura = pagina.evaluate('document.documentElement.scrollWidth - innerWidth')
    assert largura <= 0, f'rola {largura}px para o lado'


@pytest.mark.parametrize('largura', [1319, 1024, 800])
def test_notas_da_pauta_nao_cobrem_o_texto_do_rodape(nova_pagina, site_url, largura):
    pagina = nova_pagina(viewport={'width': largura, 'height': 900}, reduced_motion='reduce')
    pagina.goto(f'{site_url}/')
    texto = pagina.locator('.rodape-cta .lado').bounding_box()
    for nota in pagina.locator('.pauta i').all():
        n = nota.bounding_box()
        if not n:
            continue
        cruza = n['x'] < texto['x'] + texto['width'] and n['x'] + n['width'] > texto['x']
        assert not (
            cruza and n['y'] < texto['y'] + texto['height'] and n['y'] + n['height'] > texto['y']
        )
