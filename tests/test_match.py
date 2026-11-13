"""Perfil unificado, conciliação (pares ótimos) e o Match na interface."""

from __future__ import annotations

import json
import random
from itertools import combinations, permutations
from pathlib import Path

import pandas as pd
import pytest
from PIL import Image

from conciliacao import comparar_perfis, conciliar, emparelhamento_otimo, nivel
from dados import carregar_historico
from perfil_gosto import (
    PerfilGosto,
    perfil_de_historico,
    peso_posicao,
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


def test_match_na_interface_com_tres_zips(tmp_path: Path, monkeypatch) -> None:
    import ui

    zips = []
    for nome, artistas in (('Ana', ['X', 'Y']), ('Bia', ['X', 'Z']), ('Caio', ['Y', 'Z'])):
        p = tmp_path / f'{nome}.json'
        p.write_text(
            json.dumps([_evento('2026-10-01T10:00:00Z', a) for a in artistas]), encoding='utf-8'
        )
        zips.append(str(p))
    html, figura, ranking, _, revelacao, estado, dupla = ui.executar_match(
        zips,
        'Ana\nBia\nCaio',
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
    assert set(ranking['Fonte']) == {'Histórico ZIP'}
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


def test_match_repetido_nao_precarrega_zips_com_perfil_em_cache(
    tmp_path: Path, monkeypatch
) -> None:
    import ui

    chamadas: list[list] = []
    monkeypatch.setattr(
        ui.match, 'precarregar', lambda arquivos, config: chamadas.append(list(arquivos))
    )
    zips = []
    for i in range(8):  # mais que MAXIMO_HISTORICOS_CACHE (6): dois blocos
        p = tmp_path / f'p{i}.json'
        p.write_text(json.dumps([_evento('2026-10-01T10:00:00Z', f'A{i}')]), encoding='utf-8')
        zips.append(str(p))
    nomes = '\n'.join(f'P{i}' for i in range(8))
    args = (zips, nomes, 'America/Sao_Paulo', '', '', 'manter', False, False)
    ui.executar_match(*args, progress=lambda *a, **k: None)
    assert [len(c) for c in chamadas] == [6, 2]
    chamadas.clear()
    ui.executar_match(*args, progress=lambda *a, **k: None)
    assert chamadas == []


def test_nome_repetido_acusa_antes_de_ler_os_historicos(tmp_path: Path, monkeypatch) -> None:
    """Dois nomes iguais (ZIP ou ListenBrainz) param na hora, sem ler histórico nem chamar a rede."""
    from gradio.exceptions import Error

    import ui

    lidos: list = []
    monkeypatch.setattr(ui.match, 'perfil_de_arquivos', lambda *a, **k: lidos.append(a))
    monkeypatch.setattr(ui.match, 'coletar_perfil_listenbrainz', lambda u: lidos.append(u))
    opcoes = ('America/Sao_Paulo', '', '', 'manter', False, False, False)
    with pytest.raises(Error, match='nome diferente'):
        ui.executar_match(
            ['a.json', 'b.json'], 'Ana\n ana ', *opcoes, '', progress=lambda *a, **k: None
        )
    with pytest.raises(Error, match='nome diferente'):
        ui.executar_match(['a.json'], 'Bia', *opcoes, 'bia', progress=lambda *a, **k: None)
    assert lidos == []
