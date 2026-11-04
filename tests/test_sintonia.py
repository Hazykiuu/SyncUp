"""Em sintonia: a mesma faixa tocando para os dois no mesmo instante (conferido à mão)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from cartao import gerar_cartao_sintonia
from componentes import sintonia_html
from dados import carregar_historico
from recursos import sintonia


def _historico(tmp_path: Path, nome: str, plays: list[tuple[str, int, str]]):
    """plays: (fim em UTC, segundos tocados, música). Artista fixo."""
    eventos = [
        {
            'ts': fim,
            'ms_played': segundos * 1000,
            'master_metadata_track_name': musica,
            'master_metadata_album_artist_name': 'Banda',
        }
        for fim, segundos, musica in plays
    ]
    caminho = tmp_path / f'{nome}.json'
    caminho.write_text(json.dumps(eventos), encoding='utf-8')
    return carregar_historico(caminho).dados


def test_sobreposicao_real_conta_e_mede_os_minutos(tmp_path: Path) -> None:
    a = _historico(
        tmp_path,
        'a',
        [
            ('2026-03-06T13:05:00Z', 300, 'X'),  # 13:00–13:05
            ('2026-03-06T15:00:00Z', 120, 'X'),  # sozinho
            ('2026-03-07T13:00:20Z', 60, 'Y'),  # 12:59:20–13:00:20
        ],
    )
    b = _historico(
        tmp_path,
        'b',
        [
            ('2026-03-06T13:07:00Z', 300, 'X'),  # 13:02–13:07 → 3 min juntos
            ('2026-03-06T13:04:00Z', 240, 'Z'),  # outra faixa no mesmo horário: não conta
            ('2026-03-07T13:01:00Z', 60, 'Y'),  # 13:00:00–13:01:00 → 20 s: abaixo de 30 s
        ],
    )
    s = sintonia(a, b)
    assert len(s.momentos) == 1
    assert s.minutos == pytest.approx(3.0)
    m = s.primeira
    assert m.musica == 'X' and str(m.inicio_utc) == '2026-03-06 13:02:00+00:00'
    assert m.inicio_local.hour == 10  # fuso padrão America/Sao_Paulo (UTC−3)
    assert s.hora_favorita == 10 and s.dia_favorito == 'sexta'
    assert s.top_musicas == [('X', 'Banda', 1, pytest.approx(3.0))]
    assert s.por_mes.to_dict() == {'2026-03': pytest.approx(3.0)}


def test_sem_sintonia_e_html_e_cartao_seguros(tmp_path: Path) -> None:
    from analise import comparar

    pa = tmp_path / 'a.json'
    pb = tmp_path / 'b.json'
    for caminho, fim, musica in (
        (pa, '2026-03-06T13:05:00Z', '<b>X</b>'),
        (pb, '2026-05-06T13:05:00Z', 'Y'),
    ):
        caminho.write_text(
            json.dumps(
                [
                    {
                        'ts': fim,
                        'ms_played': 200_000,
                        'master_metadata_track_name': musica,
                        'master_metadata_album_artist_name': 'Banda',
                    }
                ]
            ),
            encoding='utf-8',
        )
    r = comparar(pa, pb, '<i>Ana</i>', 'Bia', False)
    assert r.sintonia is not None and r.sintonia.momentos == []
    html = sintonia_html(r)
    assert 'Ainda não ouviram' in html and '<i>Ana</i>' not in html and '&lt;i&gt;' in html
    with Image.open(gerar_cartao_sintonia(r, tmp_path / 's.png')) as imagem:
        assert imagem.size == (1080, 1920)


def test_stories_e_cartao_com_momentos(tmp_path: Path) -> None:
    from analise import comparar

    plays = [('2026-03-06T13:05:00Z', 300, 'X'), ('2026-04-01T22:10:00Z', 200, 'X')]
    outro = [('2026-03-06T13:07:00Z', 300, 'X'), ('2026-04-01T22:11:00Z', 200, 'X')]
    for nome, lista in (('a', plays), ('b', outro)):
        _historico(tmp_path, nome, lista)
    r = comparar(tmp_path / 'a.json', tmp_path / 'b.json', 'Ana', 'Bia', False)
    assert len(r.sintonia.momentos) == 2
    html = sintonia_html(r)
    assert 'A MÚSICA DE VOCÊS' in html and 'su-sync-timeline' in html
    with Image.open(gerar_cartao_sintonia(r, tmp_path / 's.png')) as imagem:
        assert imagem.size == (1080, 1920)
