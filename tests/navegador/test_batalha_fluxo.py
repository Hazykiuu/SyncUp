"""Batalha v2 de ponta a ponta: stories até o fim, "Ver de novo", pôster e o sorteio seguinte. Só dados fictícios.

O pôster é conferido pelo que o Canvas escreve (fillText): nomes inteiros, a porcentagem da dupla afinada,
tudo dentro da margem e sem um texto por cima de outro.
"""

import re

import pytest
from playwright.sync_api import expect

from tools.gerar_dados_falsos import Configuracao, gerar_zip

pytestmark = pytest.mark.navegador

TEMPO = 45_000
NOMES = [
    'Maria Eduarda Albuquerque',
    'João Pedro Vasconcelos',
    'Ana Beatriz Cavalcanti',
    'Luiz Fernando Montenegro',
    'Gabriela Fontes Rezende',
    'Francisco Xavier Bittencourt',
]

# Desenha o pôster com `b` e devolve cada fillText com a sua caixa (alinhamento e métricas da fonte).
POSTER = r"""
async (b) => {
  const { desenharPosterBatalha } = await import('/app/js/poster.js');
  const textos = [], orig = CanvasRenderingContext2D.prototype.fillText;
  CanvasRenderingContext2D.prototype.fillText = function (t, x, y) {
    const m = this.measureText(t), w = m.width;
    const x0 = this.textAlign === 'center' ? x - w / 2 : this.textAlign === 'right' ? x - w : x;
    // as métricas já contam o textBaseline: a caixa é y - ascent até y + descent
    textos.push({ t: String(t), x0, x1: x0 + w, y0: y - m.actualBoundingBoxAscent, y1: y + m.actualBoundingBoxDescent });
    return orig.call(this, t, x, y);
  };
  try { await desenharPosterBatalha(b); } finally { CanvasRenderingContext2D.prototype.fillText = orig; }
  return textos;
}
"""


def _batalha_de_mentira(medalhas, campeoes, titulo=None):
    cores = ['#1ed760', '#c4b7ff', '#f573a0', '#ffa42b', '#5cb8ff', '#f5d547']
    return {
        'lutadores': [
            {
                'nome': NOMES[i],
                'cor': cores[i],
                'medalhas': dict(zip(('ouro', 'prata', 'bronze'), m)),
            }
            for i, m in enumerate(medalhas)
        ],
        'campeoes': campeoes,
        'titulo': titulo,
        'afinada': {'par': [5, 4], 'valor': 87.4},
    }


@pytest.mark.parametrize(
    ('medalhas', 'campeoes', 'titulo'),
    [
        (
            [(2, 1, 2), (1, 3, 1), (1, 1, 2), (0, 2, 3), (1, 2, 1), (5, 1, 1)],
            [5],
            'Enciclopédia Musical',
        ),
        ([(3, 2, 1), (1, 3, 1), (1, 1, 2), (0, 2, 3), (2, 1, 1), (3, 2, 1)], [0, 5], None),
        ([(3, 1, 1), (3, 1, 1), (1, 2, 2), (0, 3, 3), (0, 2, 1), (3, 1, 1)], [0, 1, 5], None),
        ([(2, 1, 1)] * 6, [0, 1, 2, 3, 4, 5], None),
    ],
    ids=['1-campeao', '2-campeoes', '3-campeoes', '6-campeoes'],
)
def test_poster_com_nomes_longos_nada_cortado_nem_sobreposto(
    page, site_url, medalhas, campeoes, titulo
):
    page.goto(f'{site_url}/app/#batalha')
    expect(page.locator('button.mais-lutador:visible')).to_be_visible(timeout=TEMPO)
    textos = page.evaluate(POSTER, _batalha_de_mentira(medalhas, campeoes, titulo))
    escritos = ' '.join(t['t'] for t in textos)
    for k in campeoes:
        assert NOMES[k] in escritos, f'{NOMES[k]} cortado: {escritos}'
    if titulo:
        assert titulo.upper() in escritos
    assert any(t['t'].endswith('87,4%') for t in textos), escritos
    fora = [t['t'] for t in textos if t['x0'] < 89 or t['x1'] > 991]
    assert not fora, fora
    juntos = [
        (a['t'], b['t'])
        for i, a in enumerate(textos)
        for b in textos[i + 1 :]
        if a['x0'] < b['x1'] and b['x0'] < a['x1'] and a['y0'] < b['y1'] and b['y0'] < a['y1']
    ]
    assert not juntos, juntos


def _tipos(pagina):
    """Os stories do resultado, na ordem: abertura, rodada-<chave>…, afinada, medalhas, pódio."""
    return pagina.evaluate(
        "[...document.querySelectorAll('#resultado-batalha .st-slot .su-story')]"
        ".map(s => [...s.classList].find(c => c.startsWith('s-')).slice(2))"
    )


def _ate_o_fim(pagina):
    """Pausa e anda story por story até o último; devolve os tipos vistos."""
    player = pagina.locator('#resultado-batalha .st-player')
    expect(player).to_be_visible(timeout=TEMPO)
    player.focus()
    if 'pausado' not in (player.get_attribute('class') or ''):
        player.press(' ')
    expect(player).to_have_class(re.compile(r'\bpausado\b'))
    player.press('Home')
    contador = player.locator('.st-contador')
    total = int(contador.inner_text().split('/')[1])
    vistos = []
    for k in range(total):
        if k:
            player.press('ArrowRight')
        expect(contador).to_have_text(f'{k + 1}/{total}')
        vistos.append(
            pagina.evaluate(
                "[...document.querySelector('#resultado-batalha .st-slot.ativo .su-story').classList]"
                ".find(c => c.startsWith('s-')).slice(2)"
            )
        )
    return vistos


def _confere_rodadas(pagina, vistos):
    rodadas = [t.removeprefix('rodada-') for t in vistos if t.startswith('rodada-')]
    assert vistos[0] == 'abertura' and vistos[-3:] == ['afinada', 'medalhas', 'podio'], vistos
    titulos = pagina.evaluate(
        "ks => import('/app/js/batalha-temas.js').then(m => ks.map(k => m.TEMA[k].titulo))", rodadas
    )
    na_tela = pagina.locator(
        '#resultado-batalha .rodadas > li h3'
    ).all_text_contents()  # sem a caixa alta do CSS
    assert len(na_tela) == len(titulos)
    assert all(h.startswith(t) for h, t in zip(na_tela, titulos)), (na_tela, titulos)
    return rodadas


def _enviar(pagina, arquivos):
    expect(pagina.locator('button.mais-lutador:visible')).to_be_visible(timeout=TEMPO)
    for _ in range(len(arquivos) - 3):
        pagina.locator('button.mais-lutador:visible').click()
    lutadores = pagina.locator('.lutador:visible')
    for i, arquivo in enumerate(arquivos):
        lutadores.nth(i).locator('input.entrada').fill(NOMES[i])
        lutadores.nth(i).locator('input[type=file]').set_input_files(arquivo)
    botao = pagina.get_by_role('button', name='Começar a batalha')
    expect(botao).to_be_enabled(timeout=TEMPO)
    botao.click()


@pytest.mark.parametrize('pessoas', [0, 3, 6], ids=['exemplo', '3-arquivos', '6-arquivos'])
def test_batalha_chega_ao_fim_dos_stories(page, site_url, tmp_path, pessoas):
    page.goto(f'{site_url}/app/?semente=11#batalha')
    if pessoas:
        arquivos = [
            gerar_zip(
                tmp_path / f'p{i}.zip',
                Configuracao(linhas=3000 + 900 * i, artistas=120 + 40 * i, seed=i + 1),
            )
            for i in range(pessoas)
        ]
        _enviar(page, arquivos)
    else:
        page.get_by_role('button', name='Ver um exemplo').click()
    vistos = _ate_o_fim(page)
    rodadas = _confere_rodadas(page, vistos)
    assert 1 <= len(rodadas) <= 10


def test_ver_de_novo_e_poster_usam_os_mesmos_temas(page, site_url):
    page.goto(f'{site_url}/app/?semente=7#batalha')
    page.get_by_role('button', name='Ver um exemplo').click()
    antes = _ate_o_fim(page)
    _confere_rodadas(page, antes)

    def poster():
        with page.expect_download(timeout=TEMPO) as baixado:
            page.get_by_role('button', name='Baixar pôster').first.click()
        return open(baixado.value.path(), 'rb').read()

    png = poster()
    page.get_by_role('button', name='Ver de novo').click()
    depois = _ate_o_fim(page)
    assert depois == antes
    assert poster() == png  # o mesmo resultado (temas, medalhas e título) desenha o mesmo pôster


def test_calcular_de_novo_evita_os_temas_da_batalha_anterior(page, site_url):
    page.goto(f'{site_url}/app/?semente=7#batalha')
    temas = []
    for _ in range(2):
        page.get_by_role('button', name='Ver um exemplo').click()
        # o resultado anterior sai da tela enquanto calcula; o player sem a marca é o novo
        expect(page.locator('#resultado-batalha .st-player:not([data-velho])')).to_be_visible(
            timeout=TEMPO
        )
        temas.append({t for t in _tipos(page) if t.startswith('rodada-')})
        page.evaluate("document.querySelector('#resultado-batalha .st-player').dataset.velho = '1'")
    assert len(temas[0]) == len(temas[1]) == 10
    assert not temas[0] & temas[1], (
        temas[0] & temas[1]
    )  # mesma semente: só a batalha anterior muda o sorteio
