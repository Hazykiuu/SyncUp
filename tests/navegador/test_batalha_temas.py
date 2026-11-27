"""Stories da Batalha v2: os 56 temas (6 modelos de desenho) cabem na moldura com 6 lutadores e nomes longos.

O teste serve tests/navegador/batalha_forcada.js no lugar do Worker da Batalha (nada novo na interface de
produção): números de pior caso, todos os temas como story. Para cada story, medir_slide.js confere que nada
sai da moldura nem fica sob o contador, que o conteúdo não transborda e que nenhum número é cortado.
"""

import json
import re
from pathlib import Path

import pytest
from playwright.sync_api import expect

AQUI = Path(__file__).resolve().parent
SITE = AQUI.parents[1] / 'site'
FORCADA = (AQUI / 'batalha_forcada.js').read_text(encoding='utf-8')
MEDIR = (AQUI / 'medir_slide.js').read_text(encoding='utf-8')
NOMES = [
    'Maria Eduarda Albuquerque',
    'João Pedro Vasconcelos',
    'Ana Beatriz Cavalcanti',
    'Luiz Fernando Montenegro',
    'Gabriela Fontes Rezende',
    'Francisco Xavier Bittencourt',
]
DEMOS = ['demo-wrapped', 'demo-bruno', 'demo-carla', 'demo-davi', 'demo-wrapped', 'demo-bruno']
TEMPO = 45_000

pytestmark = pytest.mark.navegador


def _batalha_forcada(pagina, url):
    """Monta a batalha de 6 pelo formulário, com todos os temas como story; devolve o player pausado no 1º."""
    chaves = pagina.evaluate(
        "import('/app/js/batalha-temas.js').then(m => m.TEMAS.map(t => t.chave))"
    )
    corpo = f'const FORCAR = {json.dumps({"modo": "sintetico", "chaves": chaves})};\n{FORCADA}'
    pagina.route(
        '**/batalha-worker.js',
        lambda rota: rota.fulfill(body=corpo, content_type='text/javascript; charset=utf-8'),
    )
    # a 1ª carga do app pode passar de 5 s com a máquina ocupada
    expect(pagina.locator('button.mais-lutador:visible')).to_be_visible(timeout=TEMPO)
    for _ in range(3):
        pagina.locator('button.mais-lutador:visible').click()
    lutadores = pagina.locator('.lutador:visible')
    for i, nome in enumerate(NOMES):
        lutadores.nth(i).locator('input.entrada').fill(nome)
        lutadores.nth(i).locator('input[type=file]').set_input_files(
            SITE / 'app' / f'{DEMOS[i]}.zip'
        )
    pagina.get_by_role('button', name='Começar a batalha').click()
    player = pagina.locator('#resultado-batalha .st-player')
    expect(player).to_be_visible(timeout=TEMPO)
    player.focus()
    if 'pausado' not in (player.get_attribute('class') or ''):
        player.press(' ')
    expect(player).to_have_class(re.compile(r'\bpausado\b'))
    player.press('Home')
    return player, len(chaves)


@pytest.mark.parametrize(
    ('largura', 'altura', 'modo'),
    [
        (360, 740, 'normal'),
        (412, 915, 'normal'),
        (1440, 900, 'normal'),
        (360, 740, 'reduce'),
        (360, 740, 'forced'),
    ],
)
def test_56_temas_cabem_na_moldura(nova_pagina, site_url, largura, altura, modo):
    pagina = nova_pagina(
        viewport={'width': largura, 'height': altura},
        reduced_motion='reduce' if modo == 'reduce' else 'no-preference',
        forced_colors='active' if modo == 'forced' else 'none',
    )
    pagina.goto(f'{site_url}/app/#batalha')
    player, temas = _batalha_forcada(pagina, site_url)
    contador = player.locator('.st-contador')
    total = int(contador.inner_text().split('/')[1])
    assert total == temas + 4  # abertura, os 56, dupla afinada, medalhas e pódio
    problemas, tipos = {}, []
    for k in range(total):
        if k:
            player.press('ArrowRight')
            expect(contador).to_have_text(f'{k + 1}/{total}')
        m = pagina.evaluate(MEDIR)
        tipos.append(m['tipo'])
        if m['problemas']:
            problemas[m['tipo']] = m['problemas']
    assert len([t for t in tipos if t.startswith('rodada-')]) == temas
    assert not problemas, json.dumps(problemas, ensure_ascii=False, indent=1)
    assert pagina.evaluate('document.documentElement.scrollWidth - innerWidth') <= 0
    # A medida enxerga o defeito: um número empurrado para fora tem de aparecer.
    player.press('Home')
    player.press('ArrowRight')
    expect(contador).to_have_text(f'2/{total}')
    pagina.add_style_tag(content='.st-slot.ativo .sb-valor { margin-left: 120vw; }')
    assert pagina.evaluate(MEDIR)['problemas']
