"""Eixo de estilo: gêneros do Spotify e do MusicBrainz (API simulada, sem rede)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from conciliacao import comparar_perfis
from generos import ConsultaMusicBrainz, preencher_generos, vetor_generos
from perfil_gosto import PerfilGosto


def _perfil(nome: str, artistas: list[str], generos: dict[str, list[str]] | None = None):
    tops = {p: list(artistas) for p in ('short_term', 'medium_term', 'long_term')}
    return PerfilGosto(nome, 'teste', '', tops, {}, generos=generos or {})


def _musicbrainz(pedidos: list[str]) -> httpx.MockTransport:
    respostas = {
        'Legião Urbana': {
            'score': 100,
            'tags': [{'name': 'Rock', 'count': 3}, {'name': 'MPB', 'count': 5}],
        },
        'Quase': {'score': 60, 'tags': [{'name': 'pop', 'count': 9}]},
    }

    def responder(pedido: httpx.Request) -> httpx.Response:
        assert pedido.headers['User-Agent'].startswith('SyncUp/')
        nome = pedido.url.params['query'].removeprefix('artist:"').removesuffix('"')
        pedidos.append(nome)
        artista = respostas.get(nome)
        return httpx.Response(200, json={'artists': [artista] if artista else []})

    return httpx.MockTransport(responder)


def test_consulta_respeita_intervalo_score_e_cache(tmp_path: Path) -> None:
    pedidos: list[str] = []
    agora = [100.0]
    esperas: list[float] = []

    def dormir(s: float) -> None:
        esperas.append(s)
        agora[0] += s

    cache = tmp_path / 'generos.json'
    consulta = ConsultaMusicBrainz(
        httpx.Client(transport=_musicbrainz(pedidos)), cache, lambda: agora[0], dormir
    )
    assert consulta.generos('Legião Urbana') == ['mpb', 'rock']  # mais votada primeiro
    assert consulta.generos('Quase') == []  # score baixo: sem correspondência confiável
    assert consulta.generos('legiao urbana!') == []  # outra grafia não é o mesmo nome normalizado
    assert consulta.generos('LEGIÃO URBANA') == ['mpb', 'rock']  # caixa diferente: cache
    assert esperas == [pytest.approx(1.0), pytest.approx(1.0)]
    consulta.fechar()
    assert json.loads(cache.read_text(encoding='utf-8'))['legiãourbana'] == ['mpb', 'rock']
    # Nova sessão lê o cache e não chama a rede.
    de_novo = ConsultaMusicBrainz(httpx.Client(transport=_musicbrainz(pedidos)), cache)
    pedidos.clear()
    assert de_novo.generos('Legião Urbana') == ['mpb', 'rock'] and pedidos == []


def test_falha_de_rede_nao_entra_no_cache(tmp_path: Path) -> None:
    def falhar(pedido: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError('sem internet', request=pedido)

    consulta = ConsultaMusicBrainz(
        httpx.Client(transport=httpx.MockTransport(falhar)),
        tmp_path / 'g.json',
        dormir=lambda s: None,
    )
    assert consulta.generos('Legião Urbana') == []
    assert 'legiãourbana' not in consulta._cache


def test_preencher_mantem_generos_do_spotify(tmp_path: Path) -> None:
    pedidos: list[str] = []
    consulta = ConsultaMusicBrainz(
        httpx.Client(transport=_musicbrainz(pedidos)), tmp_path / 'g.json', dormir=lambda s: None
    )
    perfil = _perfil('Ana', ['Pitty', 'Legião Urbana'], {'Pitty': ['brazilian rock']})
    completo = preencher_generos(perfil, consulta)
    assert pedidos == ['Legião Urbana']
    assert completo.generos == {'Pitty': ['brazilian rock'], 'Legião Urbana': ['mpb', 'rock']}
    assert perfil.generos == {'Pitty': ['brazilian rock']}  # original intacto


def test_estilo_aproxima_quem_nao_divide_artistas() -> None:
    a = _perfil('Ana', ['Pitty'], {'Pitty': ['brazilian rock']})
    b = _perfil('Bia', ['Legião Urbana'], {'Legião Urbana': ['rock', 'mpb']})
    vetor = vetor_generos(a)
    assert vetor['brazilian rock'] > vetor['rock'] > 0  # palavra derivada vale metade
    c = comparar_perfis(a, b)
    assert c.pontuacao == 0 and c.pontuacao_generos is not None and c.pontuacao_generos > 0
    assert c.generos_comuns == ['rock']
    sem = comparar_perfis(a, _perfil('Caio', ['Pitty']))
    assert sem.pontuacao_generos is None and sem.generos_comuns == []


def test_sem_internet_para_depois_de_poucas_falhas_e_cache_ruim_e_ignorado(tmp_path: Path) -> None:
    pedidos: list[str] = []

    def falhar(pedido: httpx.Request) -> httpx.Response:
        pedidos.append(pedido.url.params['query'])
        raise httpx.ConnectError('sem internet', request=pedido)

    cache = tmp_path / 'g.json'
    cache.write_text('[]', encoding='utf-8')  # JSON válido, mas não é um objeto
    consulta = ConsultaMusicBrainz(
        httpx.Client(transport=httpx.MockTransport(falhar)), cache, dormir=lambda s: None
    )
    for i in range(10):
        assert consulta.generos(f'Artista {i}') == []
    assert len(pedidos) == 3 and consulta.falhas == 3  # não espera o timeout dos outros 7


def test_salvar_mescla_com_o_que_outra_sessao_gravou(tmp_path: Path) -> None:
    cache = tmp_path / 'g.json'
    primeira = ConsultaMusicBrainz(httpx.Client(transport=_musicbrainz([])), cache)
    segunda = ConsultaMusicBrainz(httpx.Client(transport=_musicbrainz([])), cache)
    primeira.generos('Legião Urbana')
    primeira.salvar()
    segunda.generos('Quase')
    segunda.salvar()  # não apaga o que a primeira gravou
    assert set(json.loads(cache.read_text(encoding='utf-8'))) == {'legiãourbana', 'quase'}
    assert not list(tmp_path.glob('*.tmp'))


def test_match_na_tela_busca_generos_e_avisa_falha(tmp_path: Path, monkeypatch) -> None:
    import ui

    avisos: list[str] = []
    fechadas: list[bool] = []

    class ConsultaFalsa:
        def __init__(self, cache):
            assert Path(cache).name == 'generos_musicbrainz.json'
            self.falhas = 1

        def generos(self, artista: str) -> list[str]:
            return {'X': ['rock'], 'Y': ['rock', 'indie']}.get(artista, [])

        def fechar(self) -> None:
            fechadas.append(True)

    monkeypatch.setattr(ui, 'ConsultaMusicBrainz', ConsultaFalsa)
    monkeypatch.setattr(ui.gr, 'Warning', avisos.append)
    zips = []
    for nome, artista in (('Ana', 'X'), ('Bia', 'Y')):
        p = tmp_path / f'{nome}.json'
        p.write_text(
            json.dumps(
                [
                    {
                        'ts': '2026-10-01T10:00:00Z',
                        'ms_played': 60_000,
                        'master_metadata_track_name': 'F',
                        'master_metadata_album_artist_name': artista,
                    }
                ]
            ),
            encoding='utf-8',
        )
        zips.append(str(p))
    html, *_, estado, _ = ui.executar_match(
        zips,
        'Ana\nBia',
        [],
        'America/Sao_Paulo',
        '',
        '',
        'manter',
        False,
        False,
        True,
        progress=lambda *a, **k: None,
    )
    assert fechadas == [True] and avisos and 'MusicBrainz' in avisos[0]
    assert 'No estilo' in html
    assert estado['resultado'].par('Ana', 'Bia').generos_comuns == ['rock']


def test_falha_passageira_ganha_uma_nova_tentativa(tmp_path: Path) -> None:
    respostas = iter(
        [
            httpx.Response(503),
            httpx.Response(
                200, json={'artists': [{'score': 100, 'tags': [{'name': 'rock', 'count': 1}]}]}
            ),
        ]
    )
    consulta = ConsultaMusicBrainz(
        httpx.Client(transport=httpx.MockTransport(lambda pedido: next(respostas))),
        tmp_path / 'g.json',
        dormir=lambda s: None,
    )
    assert consulta.generos('Legião Urbana') == ['rock'] and consulta.falhas == 1
