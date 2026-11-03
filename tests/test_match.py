"""Perfil unificado, conciliação (pares ótimos) e login do Spotify com API simulada."""

from __future__ import annotations

import base64
import hashlib
import json
from itertools import permutations
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pandas as pd
import pytest

import spotify_api
from conciliacao import comparar_perfis, conciliar, emparelhamento_otimo, nivel
from dados import carregar_historico
from perfil_gosto import (
    PerfilGosto,
    carregar_perfil,
    perfil_de_historico,
    peso_posicao,
    salvar_perfil,
    vetor_artistas,
)


def _perfil(
    nome: str, artistas: list[str], musicas: list[tuple[str, str]] | None = None
) -> PerfilGosto:
    tops = {p: list(artistas) for p in ('short_term', 'medium_term', 'long_term')}
    faixas = [{'musica': m, 'artista': a} for m, a in (musicas or [])]
    return PerfilGosto(nome, 'teste', '', tops, {p: faixas for p in tops})


def _evento(ts: str, artista: str, musica: str = 'F', ms: int = 60_000) -> dict:
    return {
        'ts': ts,
        'ms_played': ms,
        'master_metadata_track_name': musica,
        'master_metadata_album_artist_name': artista,
    }


def test_zip_vira_rankings_nas_mesmas_janelas_da_api(tmp_path: Path) -> None:
    """Janelas contam a partir do fim do histórico; desempate alfabético; ≥30 s."""
    eventos = (
        [_evento('2026-01-01T10:00:00Z', 'Antigo')] * 5  # > 1 ano antes do fim
        + [_evento('2026-12-01T10:00:00Z', 'Meio')] * 3  # dentro de 6 meses
        + [_evento('2027-03-20T10:00:00Z', 'Novo')] * 2  # dentro de 4 semanas
        + [_evento('2027-03-25T10:00:00Z', 'Bia')] * 2
        + [_evento('2027-03-25T11:00:00Z', 'Curto', ms=5_000)] * 9  # não conta
    )
    caminho = tmp_path / 'h.json'
    caminho.write_text(json.dumps(eventos), encoding='utf-8')
    perfil = perfil_de_historico(carregar_historico(caminho).dados, 'Ana')
    assert perfil.fonte == 'historico_zip'
    assert perfil.top_artistas['short_term'] == ['Bia', 'Novo']
    assert perfil.top_artistas['medium_term'] == ['Meio', 'Bia', 'Novo']
    assert 'Antigo' not in perfil.top_artistas['long_term']
    assert perfil.recentes[0]['artista'] == 'Bia'


def test_pesos_por_posicao_e_nomes_normalizados() -> None:
    assert peso_posicao(1) == 1 and peso_posicao(50) == pytest.approx(0.02)
    a = _perfil('A', ['The Smiths', 'Radiohead'])
    b = _perfil('B', ['the smiths!', 'Outro'])
    va = vetor_artistas(a)
    assert va['thesmiths'] == pytest.approx(0.6 + 0.8 + 1.0)  # 1º lugar nos três períodos
    c = comparar_perfis(a, b)
    assert c.artistas_comuns == ['The Smiths'] and 0 < c.pontuacao < 100
    assert c.recomendacoes_para_b == ['Radiohead'] and c.recomendacoes_para_a == ['Outro']
    assert comparar_perfis(a, a).pontuacao == 100.0


def test_emparelhamento_e_otimo_e_trio_quando_impar() -> None:
    nomes = list('ABCDEF')
    valores = [
        [100, 50, 10, 0, 5, 1],
        [50, 100, 40, 2, 0, 3],
        [10, 40, 100, 45, 1, 0],
        [0, 2, 45, 100, 30, 4],
        [5, 0, 1, 30, 100, 9],
        [1, 3, 0, 4, 9, 100],
    ]
    matriz = pd.DataFrame(valores, index=nomes, columns=nomes, dtype=float)
    pares = emparelhamento_otimo(matriz)
    total = sum(matriz.loc[x, y] for x, y in pares)
    melhor = max(
        sum(matriz.loc[p[i], p[i + 1]] for i in range(0, 6, 2)) for p in permutations(nomes)
    )
    assert total == melhor and sorted(len(p) for p in pares) == [2, 2, 2]
    impar = emparelhamento_otimo(matriz.loc[list('ABCDE'), list('ABCDE')])
    assert sorted(len(g) for g in impar) == [2, 3]


def test_conciliar_valida_e_monta_ranking() -> None:
    perfis = [
        _perfil('Ana', ['X', 'Y', 'Z']),
        _perfil('Bia', ['X', 'Y', 'W']),
        _perfil('Caio', ['K', 'L']),
        _perfil('Davi', ['K', 'M']),
    ]
    r = conciliar(perfis)
    assert {frozenset(p) for p in r.pares} == {
        frozenset({'Ana', 'Bia'}),
        frozenset({'Caio', 'Davi'}),
    }
    assert r.melhores['Ana'][0][0] == 'Bia'
    assert r.matriz.loc['Ana', 'Caio'] == 0 and nivel(0)[0] == 'Mundos diferentes'
    with pytest.raises(ValueError):
        conciliar(perfis[:1])
    with pytest.raises(ValueError):
        conciliar([perfis[0], _perfil('Ana', ['Q'])])


def test_perfil_json_ida_e_volta(tmp_path: Path) -> None:
    p = _perfil('Jô/../x', ['A'], [('m', 'A')])
    caminho = salvar_perfil(p, tmp_path)
    assert caminho.parent == tmp_path and '..' not in caminho.name
    assert carregar_perfil(caminho).top_artistas == p.top_artistas
    (tmp_path / 'ruim.json').write_text('{"nome": "Sem"}', encoding='utf-8')
    with pytest.raises(ValueError):
        carregar_perfil(tmp_path / 'ruim.json')


def _api_simulada(chamadas: list[str]) -> httpx.MockTransport:
    def responder(req: httpx.Request) -> httpx.Response:
        chamadas.append(f'{req.method} {req.url.path}')
        if req.url.path == '/api/token':
            corpo = parse_qs(req.content.decode())
            assert corpo['grant_type'] == ['authorization_code'] and 'code_verifier' in corpo
            assert 'client_secret' not in corpo
            return httpx.Response(200, json={'access_token': 'tok', 'token_type': 'Bearer'})
        assert req.headers['Authorization'] == 'Bearer tok'
        periodo = req.url.params.get('time_range', '')
        if req.url.path == '/v1/me/top/artists':
            nomes = {
                'short_term': ['Ado'],
                'medium_term': ['Ado', 'Laufey'],
                'long_term': ['Laufey'],
            }
            return httpx.Response(
                200, json={'items': [{'name': n, 'genres': ['j-pop']} for n in nomes[periodo]]}
            )
        if req.url.path == '/v1/me/top/tracks':
            return httpx.Response(
                200, json={'items': [{'name': 'Usseewa', 'artists': [{'name': 'Ado'}]}]}
            )
        if req.url.path == '/v1/me/player/recently-played':
            return httpx.Response(
                200,
                json={
                    'items': [
                        {
                            'track': {'name': 'From the Start', 'artists': [{'name': 'Laufey'}]},
                            'played_at': '2026-11-01T10:00:00Z',
                        }
                    ]
                },
            )
        if req.url.path == '/v1/me/following':
            depois = req.url.params.get('after')
            itens = [{'name': 'Seguido 2'}] if depois else [{'name': 'Seguido 1'}]
            cursor = None if depois else 'c1'
            return httpx.Response(
                200, json={'artists': {'items': itens, 'cursors': {'after': cursor}}}
            )
        return httpx.Response(404)

    return httpx.MockTransport(responder)


def test_login_pkce_coleta_e_salva_sem_token(tmp_path: Path) -> None:
    url = spotify_api.iniciar_login('Bruno', 'cid123', 'http://127.0.0.1:7860/spotify/callback')
    q = parse_qs(urlparse(url).query)
    assert q['client_id'] == ['cid123'] and q['code_challenge_method'] == ['S256']
    assert 'user-top-read' in q['scope'][0]
    pendente = spotify_api._pendentes[q['state'][0]]
    esperado = base64.urlsafe_b64encode(
        hashlib.sha256(pendente.verificador.encode()).digest()
    ).rstrip(b'=')
    assert q['code_challenge'][0] == esperado.decode()
    chamadas: list[str] = []
    with httpx.Client(transport=_api_simulada(chamadas)) as cliente:
        perfil, caminho = spotify_api.concluir_login(q['state'][0], 'codigo', tmp_path, cliente)
    assert perfil.fonte == 'spotify_api' and perfil.nome == 'Bruno'
    assert perfil.top_artistas['medium_term'] == ['Ado', 'Laufey']
    assert (
        perfil.seguidos == ['Seguido 1', 'Seguido 2'] and perfil.recentes[0]['artista'] == 'Laufey'
    )
    texto = caminho.read_text(encoding='utf-8')
    assert 'tok' not in texto and 'access_token' not in texto
    with pytest.raises(ValueError):  # estado usado só uma vez
        spotify_api.concluir_login(q['state'][0], 'codigo', tmp_path, cliente)


def test_login_exige_nome_e_client_id() -> None:
    with pytest.raises(ValueError):
        spotify_api.iniciar_login('', 'cid')
    with pytest.raises(ValueError):
        spotify_api.iniciar_login('Ana', ' ')


def test_rotas_do_servidor(tmp_path: Path, monkeypatch) -> None:
    """/spotify/login redireciona ao Spotify; /spotify/callback salva o perfil."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    chamadas: list[str] = []
    transporte = _api_simulada(chamadas)
    original = httpx.Client
    monkeypatch.setattr(spotify_api.httpx, 'Client', lambda **kw: original(transport=transporte))
    app = FastAPI()
    spotify_api.registrar_rotas(app, tmp_path, 'http://127.0.0.1:7860/spotify/callback')
    with TestClient(app) as cliente:
        r = cliente.get(
            '/spotify/login', params={'nome': 'Bia', 'client_id': 'abc'}, follow_redirects=False
        )
        assert r.status_code in (302, 307) and r.headers['location'].startswith(
            spotify_api.URL_AUTORIZAR
        )
        estado = parse_qs(urlparse(r.headers['location']).query)['state'][0]
        ok = cliente.get('/spotify/callback', params={'code': 'c', 'state': estado})
        assert ok.status_code == 200 and 'Perfil de Bia salvo' in ok.text
        assert (tmp_path / 'Bia.json').is_file()
        ruim = cliente.get('/spotify/callback', params={'error': 'access_denied'})
        assert ruim.status_code == 400 and '<script' not in ruim.text


def test_match_na_interface_mistura_zip_e_spotify(tmp_path: Path, monkeypatch) -> None:
    import ui

    zips = []
    for nome, artistas in (('Ana', ['X', 'Y']), ('Bia', ['X', 'Z'])):
        p = tmp_path / f'{nome}.json'
        p.write_text(
            json.dumps([_evento('2026-10-01T10:00:00Z', a) for a in artistas]), encoding='utf-8'
        )
        zips.append(str(p))
    pasta = tmp_path / 'perfis'
    salvar_perfil(_perfil('Caio', ['Y', 'Z']), pasta)
    monkeypatch.setattr(ui, 'PASTA_PERFIS', pasta)
    assert ui.perfis_salvos() == ['Caio']
    html, figura, ranking, _ = ui.executar_match(
        zips,
        'Ana\nBia',
        ['Caio'],
        'America/Sao_Paulo',
        '',
        '',
        'manter',
        False,
        False,
        progress=lambda *a, **k: None,
    )
    assert 'trio' in html and 'Ranking individual' in html
    assert len(figura.data[0].z) == 3 and list(ranking['Pessoa']) == ['Ana', 'Bia', 'Caio']
    assert ranking.loc[2, 'Fonte'].startswith('Spotify')
