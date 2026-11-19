"""Last.fm no app: a API é respondida por páginas falsas (page.route), sem rede e sem chave."""

import json
import random
import re
from urllib.parse import parse_qs, urlparse

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.navegador

AGORA = 1_763_500_000  # nov/2025
CDN = 'https://lastfm.freetls.fastly.net/i/u/300x300'  # capas do álbum que vêm com cada escuta


def _escutas(n=900, seed=7):
    aleatorio = random.Random(seed)
    artistas = [f'Banda {i}' for i in range(30)]
    escutas = []
    for i in range(n):
        artista = artistas[min(int(aleatorio.expovariate(0.15)), 29)]
        escutas.append(
            {
                'name': f'Faixa {aleatorio.randrange(6)} de {artista}',
                'artist': {'#text': artista},
                'date': {'uts': str(AGORA - i * 3 * 3600)},
                'image': [{'size': 'extralarge', '#text': f'{CDN}/{artista[-1]}.jpg'}],
            }
        )
    escutas.insert(
        0, {'name': 'Ao vivo', 'artist': {'#text': 'Banda 0'}, '@attr': {'nowplaying': 'true'}}
    )
    return escutas


def _top(escutas):
    vistos = {}
    for t in escutas:
        vistos.setdefault((t['artist']['#text'], t['name']), None)
    # Metade com duração; a outra metade com "0" (o Last.fm não sabe) cai na mediana.
    return [
        {'name': m, 'artist': {'name': a}, 'duration': str(180 + k % 90) if k % 2 else '0'}
        for k, (a, m) in enumerate(vistos)
    ]


def _servir_lastfm(page, escutas):
    top = _top([e for e in escutas if 'date' in e])

    def responder(rota):
        q = {k: v[0] for k, v in parse_qs(urlparse(rota.request.url).query).items()}
        pagina = int(q.get('page', 1))
        if q['method'] == 'user.getrecenttracks':
            lista = escutas[(pagina - 1) * 200 : pagina * 200]
            corpo = {
                'recenttracks': {
                    'track': lista,
                    '@attr': {
                        'totalPages': str(-(-len(escutas) // 200)),
                        'total': str(len(escutas)),
                    },
                }
            }
        else:
            corpo = {'toptracks': {'track': top, '@attr': {'totalPages': '1'}}}
        rota.fulfill(status=200, content_type='application/json', body=json.dumps(corpo))

    page.route('https://ws.audioscrobbler.com/**', responder)


def _buscar(page, site_url, usuario='carlos'):
    page.goto(f'{site_url}/app/#wrapped')
    page.get_by_role('button', name=re.compile('Usar o Last.fm')).click()
    campo = page.get_by_label('Usuário do Last.fm')
    expect(campo).to_be_focused()
    campo.fill(usuario)
    page.get_by_role('button', name='Buscar escutas').click()


def test_lastfm_vira_wrapped_com_minutos_aproximados(page, site_url):
    _servir_lastfm(page, _escutas())
    _buscar(page, site_url)
    cartao = page.get_by_role('region', name='Seu histórico')
    painel = cartao.locator('dl.telemetria')
    expect(painel).to_be_visible(timeout=30_000)
    expect(cartao.get_by_text('Do Last.fm')).to_be_visible()
    expect(painel).to_contain_text('Duração real')
    expect(painel.locator('.tl-periodo dd')).to_have_text(re.compile(r'.+ → .+'))

    page.get_by_role('button', name=re.compile('Montar meu Wrapped')).click()
    player = page.locator('.resultado .st-player:visible').first
    expect(player).to_be_visible(timeout=45_000)
    intro = player.locator('.st-slot.ativo')
    expect(intro.locator('.st-mega')).to_contain_text('≈')
    expect(intro).to_contain_text('Minutos estimados pelas durações das músicas no Last.fm')
    # Sem código do Spotify, a capa da música vem do Last.fm (a rede externa é cortada; basta o endereço).
    capa = page.locator(f'.resultado img[src^="{CDN}/"]').first
    expect(capa).to_be_attached(timeout=15_000)


def test_lastfm_perfil_privado_explica_o_que_fazer(page, site_url):
    page.route(
        'https://ws.audioscrobbler.com/**',
        lambda rota: rota.fulfill(
            status=200, content_type='application/json', body='{"error":17,"message":"Login"}'
        ),
    )
    _buscar(page, site_url, 'fechado')
    alerta = page.get_by_role('region', name='Seu histórico').get_by_role('alert')
    expect(alerta).to_contain_text('Ocultar escutas recentes')
