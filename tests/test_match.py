"""Perfil unificado, conciliação (pares ótimos) e login do Spotify com API simulada."""

from __future__ import annotations

import base64
import hashlib
import json
import random
from itertools import combinations, permutations
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pandas as pd
import pytest
from PIL import Image

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


def _valor_grupos(matriz: pd.DataFrame, grupos: list[tuple[str, ...]]) -> float:
    """Dupla vale o seu par; trio vale a média dos seus três pares."""
    total = 0.0
    for g in grupos:
        links = [matriz.loc[x, y] for x, y in combinations(g, 2)]
        total += sum(links) / len(links)
    return total


def _duplas(pessoas: list[str]):
    """Todas as divisões de um número par de pessoas em duplas."""
    if not pessoas:
        yield []
        return
    primeira, resto = pessoas[0], pessoas[1:]
    for outra in resto:
        for p in _duplas([x for x in resto if x != outra]):
            yield [(primeira, outra), *p]


def _particoes(pessoas: list[str]):
    """Um trio qualquer mais todas as divisões do restante em duplas."""
    for trio in combinations(pessoas, 3):
        for p in _duplas([x for x in pessoas if x not in trio]):
            yield [trio, *p]


@pytest.mark.parametrize('n', [5, 7])
def test_emparelhamento_impar_e_otimo_contra_busca_exaustiva(n: int) -> None:
    """O trio é escolhido junto com as duplas, não encaixado depois."""
    rng = random.Random(n)
    nomes = [chr(65 + i) for i in range(n)]
    for _ in range(40):
        matriz = pd.DataFrame(100.0, index=nomes, columns=nomes)
        for x, y in combinations(nomes, 2):
            matriz.loc[x, y] = matriz.loc[y, x] = round(rng.uniform(0, 30), 1)
        grupos = emparelhamento_otimo(matriz)
        assert sorted(len(g) for g in grupos) == [2] * (n // 2 - 1) + [3]
        melhor = max(_valor_grupos(matriz, p) for p in _particoes(nomes))
        assert _valor_grupos(matriz, grupos) == pytest.approx(melhor)


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


def test_salvar_perfil_nao_apaga_outra_pessoa_com_mesmo_nome_seguro(tmp_path: Path) -> None:
    ana_clara = salvar_perfil(_perfil('Ana Clara', ['A']), tmp_path)
    outra = salvar_perfil(_perfil('Ana_Clara', ['B']), tmp_path)
    assert ana_clara != outra and outra.name == 'Ana_Clara-2.json'
    assert carregar_perfil(ana_clara).top_artistas['long_term'] == ['A']
    # Novo login da mesma pessoa substitui o arquivo dela.
    assert salvar_perfil(_perfil('Ana Clara', ['C']), tmp_path) == ana_clara
    assert carregar_perfil(ana_clara).top_artistas['long_term'] == ['C']
    assert len(list(tmp_path.glob('*.json'))) == 2


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
    html, figura, ranking, _, revelacao, estado, dupla = ui.executar_match(
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
    assert 'O TRIO' in html and 'su-match-card' in html
    assert len(figura.data[0].z) == 3 and list(ranking['Pessoa']) == ['Ana', 'Bia', 'Caio']
    assert ranking.loc[2, 'Fonte'].startswith('Spotify')
    assert 'data-stories' in revelacao and 'O TRIO' in revelacao
    assert len(dupla.choices) == 3  # os três pares internos do trio
    pastas: list[str] = []
    lista, arquivos, pastas = ui.baixar_festa(estado, pastas)
    assert {Path(a).suffix for a in arquivos} == {'.csv', '.xspf'} and 'para' in lista
    _, png, pastas = ui.baixar_cartao_match(estado, dupla.value, pastas)
    with Image.open(png) as imagem:
        assert imagem.size == (1080, 1920)
    ui._limpar_exportacoes(pastas)
    assert not any(Path(p).exists() for p in pastas)


def test_match_repetido_reusa_perfil_do_zip(tmp_path: Path, monkeypatch) -> None:
    import perfil_gosto

    caminho = tmp_path / 'Ana.json'
    caminho.write_text(json.dumps([_evento('2026-10-01T10:00:00Z', 'X')]), encoding='utf-8')
    chamadas = []
    original = perfil_gosto.carregar_historicos
    monkeypatch.setattr(
        perfil_gosto, 'carregar_historicos', lambda *a, **k: chamadas.append(1) or original(*a, **k)
    )
    primeiro = perfil_gosto.perfil_de_arquivos(caminho, 'Ana')
    segundo = perfil_gosto.perfil_de_arquivos(str(caminho), 'Outra')
    assert len(chamadas) == 1
    assert segundo.nome == 'Outra' and segundo.top_artistas == primeiro.top_artistas


def test_perfil_novo_aparece_depois_de_atualizar_lista(tmp_path: Path, monkeypatch) -> None:
    """Um amigo loga com o app aberto: Atualizar lista libera o perfil para o Match."""
    import asyncio

    from gradio.exceptions import Error
    from gradio.state_holder import SessionState

    import ui

    monkeypatch.setattr(ui, 'PASTA_PERFIS', tmp_path)
    demo = ui.criar_interface()  # sem perfis salvos ainda
    funcoes = {f.fn.__name__: f for f in demo.fns.values() if f.fn}
    salvar_perfil(_perfil('Caio', ['Y']), tmp_path)
    salvar_perfil(_perfil('Dani', ['Y', 'Z']), tmp_path)
    entradas = [None, '', ['Caio', 'Dani'], 'America/Sao_Paulo', '', '', 'manter', False, False]
    entradas += [False, '']  # sem MusicBrainz e sem ListenBrainz

    async def fluxo() -> None:
        sessao = SessionState(demo)
        await demo.process_api(block_fn=funcoes['atualizar_perfis'], inputs=[[], []], state=sessao)
        saida = await demo.process_api(
            block_fn=funcoes['executar_match'], inputs=entradas, state=sessao
        )
        assert 'Caio' in saida['data'][0]
        with pytest.raises(Error, match='not in the list of choices'):
            await demo.process_api(
                block_fn=funcoes['executar_match'], inputs=entradas, state=SessionState(demo)
            )

    asyncio.run(fluxo())
    assert any(
        d.fn is ui.atualizar_perfis and d.targets and d.targets[0][1] == 'load'
        for d in demo.fns.values()
    )


def test_match_repetido_nao_precarrega_zips_com_perfil_em_cache(
    tmp_path: Path, monkeypatch
) -> None:
    import ui

    chamadas: list[list] = []
    monkeypatch.setattr(ui, 'precarregar', lambda arquivos, config: chamadas.append(list(arquivos)))
    zips = []
    for i in range(8):  # mais que MAXIMO_HISTORICOS_CACHE (6): dois blocos
        p = tmp_path / f'p{i}.json'
        p.write_text(json.dumps([_evento('2026-10-01T10:00:00Z', f'A{i}')]), encoding='utf-8')
        zips.append(str(p))
    nomes = '\n'.join(f'P{i}' for i in range(8))
    args = (zips, nomes, [], 'America/Sao_Paulo', '', '', 'manter', False, False)
    ui.executar_match(*args, progress=lambda *a, **k: None)
    assert [len(c) for c in chamadas] == [6, 2]
    chamadas.clear()
    ui.executar_match(*args, progress=lambda *a, **k: None)
    assert chamadas == []


def test_403_mostra_chamada_e_motivo_do_spotify() -> None:
    corpo = {'error': {'status': 403, 'message': 'the user may not be registered'}}
    cliente = httpx.Client(transport=httpx.MockTransport(lambda p: httpx.Response(403, json=corpo)))
    with pytest.raises(PermissionError, match='/me/top/artists.*may not be registered'):
        spotify_api.coletar_perfil('t', 'Nicollas', cliente)


def test_403_em_texto_puro_tambem_mostra_o_motivo() -> None:
    cliente = httpx.Client(
        transport=httpx.MockTransport(
            lambda p: httpx.Response(403, text='user may not be registered')
        )
    )
    with pytest.raises(PermissionError, match='user may not be registered'):
        spotify_api.coletar_perfil('t', 'Nicollas', cliente)
