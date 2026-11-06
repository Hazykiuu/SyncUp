"""Sintonia no Match: entre fontes diferentes, todos com todos e listens do ListenBrainz."""

from __future__ import annotations

import json
import random
from pathlib import Path

import httpx
import pandas as pd
import pytest
from PIL import Image

import listenbrainz
import ui
from cartao import gerar_cartao_match
from listenbrainz import coletar_escutas_listenbrainz
from recursos import escutas, mais_sincronizada, sintonia, sintonia_do_par, sintonia_entre

FUSO = 'America/Sao_Paulo'


def _plays(linhas: list[tuple[str, str, str, int]]) -> pd.DataFrame:
    """(artista, música, fim em UTC, segundos tocados) no formato do histórico."""
    tabela = pd.DataFrame(linhas, columns=['artista', 'musica', 'fim', 'segundos'])
    data_utc = pd.to_datetime(tabela.fim, utc=True)
    return pd.DataFrame(
        {
            'artista': tabela.artista,
            'musica': tabela.musica,
            'data_utc': data_utc,
            'data': data_utc.dt.tz_convert(FUSO).dt.tz_localize(None),
            'ms_played': tabela.segundos * 1000,
        }
    )


def test_fontes_diferentes_se_encontram_pelo_nome_normalizado() -> None:
    zip_ = _plays([('Legião Urbana', 'Tempo Perdido', '2026-03-06T13:05:00Z', 300)])
    lb = _plays([('legião urbana', 'Tempo perdido!', '2026-03-06T13:07:00Z', 300)])
    s = sintonia_entre(escutas(zip_), escutas(lb))
    assert s.minutos == pytest.approx(3.0)
    assert s.primeira.artista == 'Legião Urbana'  # nomes de quem é o "A"


def test_sintonia_igual_com_datas_em_microssegundos() -> None:
    """O pandas 3 lê datas em µs: a sintonia e o horário local não podem mudar com a unidade."""
    zip_ = _plays([('Legião Urbana', 'Tempo Perdido', '2026-03-06T13:05:00Z', 300)])
    lb = _plays([('Legião Urbana', 'Tempo Perdido', '2026-03-06T13:07:00Z', 300)])

    def em_us(d: pd.DataFrame) -> pd.DataFrame:
        return d.assign(data_utc=d.data_utc.dt.as_unit('us'), data=d.data.dt.as_unit('us'))

    ns, us = (
        sintonia_entre(escutas(zip_), escutas(lb)),
        sintonia_entre(escutas(em_us(zip_)), escutas(em_us(lb))),
    )
    assert us.minutos == pytest.approx(ns.minutos) == pytest.approx(3.0)
    assert us.primeira.inicio_local == ns.primeira.inicio_local
    assert us.hora_favorita == ns.hora_favorita


def _referencia(a: pd.DataFrame, b: pd.DataFrame) -> tuple[int, float]:
    """Força bruta: une os intervalos de cada pessoa por faixa e cruza todos com todos."""

    def unidos(d: pd.DataFrame) -> dict[str, list[list[int]]]:
        por_faixa: dict[str, list[list[int]]] = {}
        for art, mus, fim, ms in zip(d.artista, d.musica, d.data_utc, d.ms_played):
            f = fim.value
            por_faixa.setdefault(f'{art}|{mus}', []).append([f - ms * 1_000_000, f])
        for lista in por_faixa.values():
            lista.sort()
            juntos = [lista[0]]
            for ini, fim in lista[1:]:
                if ini <= juntos[-1][1]:
                    juntos[-1][1] = max(juntos[-1][1], fim)
                else:
                    juntos.append([ini, fim])
            lista[:] = juntos
        return por_faixa

    ua, ub = unidos(a), unidos(b)
    n, total = 0, 0.0
    for faixa, lista in ua.items():
        for ia, fa in lista:
            for ib, fb in ub.get(faixa, []):
                d = min(fa, fb) - max(ia, ib)
                if d >= 30_000_000_000:
                    n, total = n + 1, total + d / 60_000_000_000
    return n, total


@pytest.mark.parametrize('semente', range(5))
def test_cruzamento_igual_a_forca_bruta(semente: int) -> None:
    sorteio = random.Random(semente)
    inicio = pd.Timestamp('2026-01-01T12:00:00Z')

    def pessoa() -> pd.DataFrame:
        linhas = []
        for _ in range(300):  # poucas faixas e um dia só: muitos cruzamentos e sobreposições
            fim = pd.Timestamp(inicio.value + sorteio.randrange(0, 86_400) * 10**9, tz='UTC')
            linhas.append(
                ('Banda', f'F{sorteio.randrange(6)}', fim.isoformat(), sorteio.randrange(1, 400))
            )
        return _plays(linhas)

    a, b = pessoa(), pessoa()
    s = sintonia(a, b)
    n, total = _referencia(a, b)
    assert len(s.momentos) == n and s.minutos == pytest.approx(total)
    assert sintonia(b, a).minutos == pytest.approx(total)  # simétrico


def _listens(pedidos: list[dict]) -> httpx.MockTransport:
    def responder(pedido: httpx.Request) -> httpx.Response:
        params = dict(pedido.url.params)
        pedidos.append(params)
        topo = int(params.get('max_ts', 2_000_000_000))
        quantos = 1000 if 'max_ts' not in params else 500  # 2ª página incompleta: fim
        listens = [
            {
                'listened_at': topo - 400 * (i + 1),
                'track_metadata': {
                    'track_name': 'Some Resolve',
                    'artist_name': 'Röyksopp feat. Susanne Sundfør',
                    'additional_info': {'duration_ms': 300_000} if i % 10 else {},
                    'mbid_mapping': {'artists': [{'artist_credit_name': 'Röyksopp'}]},
                },
            }
            for i in range(quantos)
        ]
        cota = {'X-RateLimit-Remaining': '0', 'X-RateLimit-Reset-In': '3'}
        return httpx.Response(200, json={'payload': {'listens': listens}}, headers=cota)

    return httpx.MockTransport(responder)


def test_listens_paginados_com_artista_principal_e_cota(monkeypatch) -> None:
    esperas: list[float] = []
    monkeypatch.setattr(listenbrainz.time, 'sleep', esperas.append)
    pedidos: list[dict] = []
    d = coletar_escutas_listenbrainz('nick', FUSO, httpx.Client(transport=_listens(pedidos)))
    assert len(pedidos) == 2 and pedidos[1]['max_ts'] == str(2_000_000_000 - 400 * 1000)
    assert len(d) == 900 + 450  # sem duração (1 em cada 10) fica de fora
    assert set(d.artista) == {'Röyksopp'} and esperas == [3, 3]
    primeiro = d.iloc[0]
    assert primeiro.ms_played == 300_000
    assert primeiro.data_utc == pd.Timestamp(
        2_000_000_000 - 800 + 300, unit='s', tz='UTC'
    )  # 1º com duração


def test_limite_de_listens() -> None:
    pedidos: list[dict] = []
    cliente = httpx.Client(transport=_listens(pedidos))
    d = coletar_escutas_listenbrainz('nick', FUSO, cliente, limite=1000)
    assert len(pedidos) == 1 and len(d) == 900


def _historico(tmp_path: Path, nome: str, fins: list[str], musica: str = 'X') -> str:
    eventos = [
        {
            'ts': fim,
            'ms_played': 300_000,
            'master_metadata_track_name': musica,
            'master_metadata_album_artist_name': 'Banda',
        }
        for fim in fins
    ]
    caminho = tmp_path / f'{nome}.json'
    caminho.write_text(json.dumps(eventos), encoding='utf-8')
    return str(caminho)


def test_match_mostra_a_dupla_mais_sincronizada(tmp_path: Path) -> None:
    arquivos = [
        _historico(tmp_path, 'ana', ['2026-03-06T13:05:00Z', '2026-03-07T20:00:00Z']),
        _historico(tmp_path, 'bia', ['2026-03-06T13:07:00Z', '2026-03-07T20:01:00Z']),
        _historico(tmp_path, 'caio', ['2026-05-01T10:00:00Z'], 'Y'),
    ]
    html, _, ranking, _, story, estado, _ = ui.executar_match(
        arquivos,
        'Ana\nBia\n<b>Caio</b>',
        [],
        FUSO,
        '',
        '',
        'manter',
        False,
        False,
        progress=lambda *a, **k: None,
    )
    sintonias = estado['sintonias']
    assert len(sintonias) == 3  # todos com todos
    x, y, s = mais_sincronizada(sintonias)
    assert {x, y} == {'Ana', 'Bia'} and s.minutos == pytest.approx(7.0)
    assert sintonia_do_par(sintonias, 'Bia', 'Ana') is s
    assert 'Dupla mais sincronizada' in html and 'DUPLA MAIS SINCRONIZADA' in story
    assert '<b>Caio</b>' not in html and '&lt;b&gt;Caio' in html
    linha = ranking.set_index('Pessoa').loc['Ana', 'Mais em sintonia']
    assert linha == 'Bia (7 min)'
    with Image.open(
        gerar_cartao_match(estado['resultado'].par('Ana', 'Bia'), tmp_path / 'm.png', sintonia=s)
    ) as imagem:
        assert imagem.size == (1080, 1920)
