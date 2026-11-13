"""Paridade do Wrapped: o motor JS do app web devolve o mesmo JSON que a ponte do Python.

O mesmo arquivo passa por ``web.ponte.wrapped`` e por ``tests/js/rodar_wrapped.mjs`` (Node);
``dados`` e ``trilha`` são comparados campo a campo (números com tolerância de 1e-9).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

from tools.gerar_dados_falsos import Configuracao, gerar_zip

RAIZ = Path(__file__).resolve().parents[1]
NODE = shutil.which('node')
pytestmark = pytest.mark.skipif(NODE is None, reason='Node não instalado')
URI_A, URI_B = 'spotify:track:' + 'A' * 22, 'spotify:track:' + 'B' * 22


def _ev(ts: str, artista: str, musica: str = 'Faixa', ms: object = 60_000, **extras) -> dict:
    return {
        'ts': ts,
        'ms_played': ms,
        'master_metadata_track_name': musica,
        'master_metadata_album_artist_name': artista,
        **extras,
    }


def _habitos(i: int) -> dict:
    return {
        'skipped': i % 3 == 0,
        'shuffle': i % 2 == 0,
        'offline': i % 5 == 0,
        'platform': ('Android OS 13', 'Windows 10', 'iOS 17', 'web_player', 'Linux')[i % 5],
        'reason_end': ('trackdone', 'fwdbtn', 'endplay')[i % 3],
    }


def _eventos_borda() -> list:
    """Empates de todo tipo, emoji, horário de verão e registros que o núcleo descarta."""
    eventos: list = []
    # Horário de verão de São Paulo (04/11/2018) e duas URIs empatadas para a mesma música.
    eventos += [
        _ev('2018-11-04T02:30:00Z', 'Zé', 'Virada', spotify_track_uri=URI_B, **_habitos(0)),
        _ev('2018-11-04T03:30:00Z', 'Zé', 'Virada', spotify_track_uri=URI_A, **_habitos(1)),
    ]
    # Artistas empatados em plays: ordem por ponto de código (Ａ largo antes do emoji).
    for k, artista in enumerate(['🎸 Banda', 'Ａ Banda', 'Ébano', 'abc', 'ABC']):
        for j in range(3):
            eventos.append(
                _ev(
                    f'2019-03-{10 + k:02d}T{12 + j:02d}:00:00Z',
                    artista,
                    f'Música {k}',
                    **_habitos(j),
                )
            )
    # Dia da semana: domingo aparece primeiro, quarta empata com ele.
    eventos += [_ev(f'2019-04-07T15:0{j}:00Z', 'Lia', 'Domingo') for j in range(4)]
    eventos += [_ev(f'2019-04-10T15:0{j}:00Z', 'Lia', 'Quarta') for j in range(4)]
    # Duas sequências de dias do mesmo tamanho; dias recorde empatados em minutos.
    eventos += [_ev(f'2020-01-0{d}T15:00:00Z', 'Rui', 'Seq', 120_000) for d in (1, 2, 3)]
    eventos += [_ev(f'2020-02-0{d}T15:00:00Z', 'Rui', 'Seq', 120_000) for d in (1, 2, 3)]
    # Descartes e casos estranhos.
    eventos += [
        _ev('2020-03-01T10:00:00Z', 'Pod', 'Ep', episode_name='Episódio'),
        _ev('2020-03-01T11:00:00Z', 'Ana', 'Hit', -5),
        _ev('2020-03-01T12:00:00Z', 'Ana', 'Hit', True),
        _ev('2020-02-30T12:00:00Z', 'Ana', 'Hit'),
        _ev('2020-03-01T13:00:00Z', '  ', 'Hit'),
        _ev('2020-03-01T14:00:00Z', ' Ana ', ' Hit ', '45000'),
        _ev('2020-03-01T14:00:00Z', 'Ana', 'Hit', 45_000),  # repetido no mesmo instante
        _ev('2020-03-01T15:00:00Z', 'Various Artists', 'Coletânea'),
        _ev('2020-03-01T16:00:00Z', 'VARIOUS ARTISTS', 'Coletânea 2'),
        _ev('2020-03-01T17:00:00Z', 'Ana', '(Falsa) Esperança'),
        _ev('2020-03-01T18:00:00Z', 'Ana', 'Curta', 10_000),
        _ev('2021-07-04T23:59:59Z', '<b>Bia</b>', 'Ação & "aspas"', spotify_track_uri=URI_A),
        # Auditoria 1.9: data sem hora e sem segundos entram; antes de 1970 e mais de 24 h saem.
        _ev('2021-08-01', 'Ana', 'Só data'),
        _ev('2021-08-02T10:30', 'Ana', 'Sem segundos'),
        _ev('1969-12-31T12:00:00Z', 'Ana', 'Relógio zerado'),
        _ev('2021-08-03T10:00:00Z', 'Ana', 'Infinita', 1e25),
        'não é um evento',
    ]
    return eventos


def _eventos_empate() -> list:
    """16 plays em que cada desempate decide o resultado (o teste de mutação confere).

    Domingo vem primeiro no arquivo, mas a quarta é mais antiga e vem antes na semana: a
    ordem de chegada não pode decidir o dia da semana favorito nem o dia recorde.
    Ａ (U+FF21) e o emoji empatam no topo: só a ordem por ponto de código põe Ａ antes.
    Windows chega antes, mas empata com Android: plataformas em ordem alfabética.
    Um play de madrugada em 16 = 6,25%, que o Python arredonda para 6,2%.
    """
    emoji, largo = '🎸 Banda', 'Ａ Banda'
    eventos = []
    for dia in ('2019-04-07', '2019-04-03'):  # domingo, depois quarta
        eventos += [_ev(f'{dia}T15:0{j}:00Z', emoji, 'S1', platform='windows') for j in range(2)]
        eventos += [_ev(f'{dia}T16:0{j}:00Z', largo, 'S2', platform='android') for j in range(2)]
    eventos += [_ev(f'2019-04-01T15:0{j}:00Z', 'Rui', 'R') for j in range(3)]
    eventos += [_ev(f'2019-04-02T15:0{j}:00Z', 'Lia', 'L') for j in range(3)]
    eventos += [_ev('2019-04-05T05:00:00Z', 'Bo', 'B'), _ev('2019-04-05T15:00:00Z', 'Bo', 'B')]
    return eventos


@pytest.fixture(scope='module')
def arquivos(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    pasta = tmp_path_factory.mktemp('paridade')
    a, b = pasta / 'a.zip', pasta / 'b.zip'
    gerar_zip(a, Configuracao(linhas=20_000, artistas=150, seed=41))
    gerar_zip(b, Configuracao(linhas=4_000, artistas=120, seed=97))
    borda = pasta / 'borda.zip'
    with zipfile.ZipFile(borda, 'w', zipfile.ZIP_DEFLATED) as pacote:
        pacote.writestr(
            'Spotify Extended Streaming History/Streaming_History_Audio_2018-2021.json',
            json.dumps(_eventos_borda(), ensure_ascii=False),
        )
        pacote.writestr('__MACOSX/._lixo.json', 'lixo')
        pacote.writestr('Spotify Extended Streaming History/ReadMeFirst.pdf', 'pdf')
    antigo = pasta / 'antigo.json'  # exportação antiga: sem hábitos
    antigo.write_bytes(
        b'\xef\xbb\xbf'
        + json.dumps(
            [
                _ev(f'2015-0{m}-1{d}T2{d}:00:00Z', f'Art {d}', f'M {m}')
                for m in (1, 2)
                for d in range(4)
            ]
        ).encode()
    )
    empates = pasta / 'empates.json'
    empates.write_text(json.dumps(_eventos_empate(), ensure_ascii=False), encoding='utf-8')
    curtos = pasta / 'curtos.json'
    curtos.write_text(json.dumps([_ev('2020-01-01T10:00:00Z', 'Ana', 'Hit', 1_000)]))
    return {'a': a, 'b': b, 'borda': borda, 'antigo': antigo, 'empates': empates, 'curtos': curtos}


def _js(caminhos: list[Path], nome: str, opcoes: dict) -> dict:
    saida = subprocess.run(
        [NODE, 'tests/js/rodar_wrapped.mjs', json.dumps(opcoes), nome, *map(str, caminhos)],
        cwd=RAIZ,
        capture_output=True,
        check=True,
    )
    return json.loads(saida.stdout.decode('utf-8'))


def _igual(py: object, js: object, onde: str) -> None:
    if isinstance(py, float) or isinstance(js, float):
        assert js == pytest.approx(py, rel=1e-9, abs=1e-12), onde
    elif isinstance(py, dict):
        assert isinstance(js, dict) and set(py) == set(js), f'{onde}: {set(py) ^ set(js)}'
        for chave in py:
            _igual(py[chave], js[chave], f'{onde}.{chave}')
    elif isinstance(py, list):
        assert isinstance(js, list) and len(py) == len(js), f'{onde}: {py!r} != {js!r}'
        for i, (a, b) in enumerate(zip(py, js)):
            _igual(a, b, f'{onde}[{i}]')
    else:
        assert py == js, f'{onde}: {py!r} != {js!r}'


CASOS = {
    'padrao': (['a'], 'Ana', {}),
    'partes': (['b', 'borda'], ' <b>Bia</b> ', {}),
    'borda': (['borda'], '', {}),
    'borda_opcoes': (
        ['borda'],
        'Lia',
        {
            'varios': 'ignorar',
            'deduplicar': True,
            'musicas': ' falsa esperança \n',
            'artistas': 'zé',
        },
    ),
    'lisboa': (['a'], 'Ana', {'fuso': 'Europe/Lisbon', 'deduplicar': True}),
    'antigo': (['antigo'], 'Ana', {}),
    'empates': (['empates'], 'Ana', {}),
}


@pytest.mark.parametrize('caso', CASOS)
def test_wrapped_js_igual_ao_python(arquivos: dict[str, Path], caso: str) -> None:
    from web import ponte

    chaves, nome, opcoes = CASOS[caso]
    caminhos = [arquivos[c] for c in chaves]
    py = ponte.wrapped([str(c) for c in caminhos], nome, opcoes)
    js = _js(caminhos, nome, opcoes)
    assert 'erro' not in js, js
    _igual(py['dados'], js['dados'], 'dados')
    _igual(py['trilha'], js['trilha'], 'trilha')
    assert js['nome'] == py['nome']


def test_erros_iguais(arquivos: dict[str, Path]) -> None:
    from web import ponte

    for caminhos in ([arquivos['curtos']], [arquivos['a'], arquivos['a']]):
        with pytest.raises(ValueError) as erro:
            ponte.wrapped([str(c) for c in caminhos], 'Ana', {})
        assert _js(caminhos, 'Ana', {}) == {'erro': str(erro.value)}
