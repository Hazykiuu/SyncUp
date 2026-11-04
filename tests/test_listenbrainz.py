"""ListenBrainz com a API simulada (sem rede) e a lista de perfis do Spotify na tela."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

import ui
from listenbrainz import PERIODOS_API, coletar_perfil_listenbrainz
from perfil_gosto import PerfilGosto, salvar_perfil


def _api(pedidos: list[str], sem_mes: bool = True) -> httpx.MockTransport:
    def responder(pedido: httpx.Request) -> httpx.Response:
        caminho, faixa = pedido.url.path, pedido.url.params.get('range')
        pedidos.append(f'{caminho}?{faixa}')
        if '/user/ninguem/' in caminho:
            return httpx.Response(404, json={'error': 'Cannot find user: ninguem'})
        if sem_mes and faixa == 'month':
            return httpx.Response(204)  # período ainda sem estatística
        if caminho.endswith('/artists'):
            return httpx.Response(
                200, json={'payload': {'artists': [{'artist_name': f'A-{faixa}'}]}}
            )
        if caminho.endswith('/recordings'):
            dados = [{'track_name': 'Faixa', 'artist_name': f'A-{faixa}'}]
            return httpx.Response(200, json={'payload': {'recordings': dados}})
        listens = [
            {'listened_at': 1771414109, 'track_metadata': {'track_name': 'F', 'artist_name': 'A'}}
        ]
        return httpx.Response(200, json={'payload': {'listens': listens}})

    return httpx.MockTransport(responder)


def test_perfil_listenbrainz_nos_mesmos_periodos_do_spotify() -> None:
    pedidos: list[str] = []
    perfil = coletar_perfil_listenbrainz('nick', 'Nicollas', httpx.Client(transport=_api(pedidos)))
    assert perfil.fonte == 'listenbrainz' and perfil.rotulo_fonte == 'ListenBrainz'
    assert perfil.nome == 'Nicollas'
    assert perfil.top_artistas == {
        'short_term': [],  # 204: sem estatística do mês ainda
        'medium_term': ['A-half_yearly'],
        'long_term': ['A-year'],
    }
    assert perfil.recentes[0]['tocada_em'].startswith('2026-02-18')
    assert {p.split('?')[1] for p in pedidos if '/stats/' in p} == set(PERIODOS_API.values())


@pytest.mark.parametrize(
    ('usuario', 'mensagem'),
    [('ninguem', 'não encontrado'), ('../admin', 'inválido'), ('', 'inválido')],
)
def test_usuario_inexistente_ou_invalido(usuario: str, mensagem: str) -> None:
    pedidos: list[str] = []
    with pytest.raises(ValueError, match=mensagem):
        coletar_perfil_listenbrainz(usuario, cliente=httpx.Client(transport=_api(pedidos)))
    if mensagem == 'inválido':
        assert pedidos == []  # nada vai para a rede com um nome suspeito


def test_sem_estatistica_nenhuma_explica_o_motivo() -> None:
    vazio = httpx.MockTransport(lambda p: httpx.Response(204))
    with pytest.raises(ValueError, match='uma vez por dia'):
        coletar_perfil_listenbrainz('nova', cliente=httpx.Client(transport=vazio))


def test_match_aceita_usuarios_do_listenbrainz(monkeypatch) -> None:
    def falso(usuario: str) -> PerfilGosto:
        tops = {p: ['X', usuario] for p in ('short_term', 'medium_term', 'long_term')}
        return PerfilGosto(usuario, 'listenbrainz', '', tops)

    monkeypatch.setattr(ui, 'coletar_perfil_listenbrainz', falso)
    html, *_ = ui.executar_match(
        [],
        '',
        [],
        'America/Sao_Paulo',
        '',
        '',
        'manter',
        False,
        False,
        False,
        'nick\nbia',
        progress=lambda *a, **k: None,
    )
    assert 'nick' in html and 'bia' in html and 'ListenBrainz' in html


def test_perfil_que_acabou_de_logar_entra_marcado(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(ui, 'PASTA_PERFIS', tmp_path)
    for nome in ('Carlos', 'Bia'):
        salvar_perfil(PerfilGosto(nome, 'spotify_api', '', {'long_term': ['X']}), tmp_path)
    # Carlos já estava na lista e foi desmarcado; Bia acabou de logar.
    lista, conhecidos = ui.atualizar_perfis([], ['Carlos'])
    assert lista.value == ['Bia'] and conhecidos == ['Bia', 'Carlos']
    lista, _ = ui.atualizar_perfis(['Carlos'], ['Bia', 'Carlos'])
    assert lista.value == ['Carlos']  # desmarcar continua valendo
