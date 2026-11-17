"""Paridade do Match: perfil e compatibilidade em JS dão o mesmo que ``perfil_gosto`` e ``conciliacao``.

Os mesmos arquivos passam pelo Python e por ``tests/js/rodar_match.mjs`` (Node). Números com
tolerância de 1e-9; listas e textos iguais. Reaproveita os arquivos e casos de borda do Wrapped.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict
from pathlib import Path

import pytest

from tests.test_paridade_wrapped import NODE, RAIZ, _igual, arquivos  # noqa: F401 (fixture)

pytestmark = pytest.mark.skipif(NODE is None, reason='Node não instalado')


def _js(pessoas: list[tuple[str, Path]], opcoes: dict) -> dict:
    saida = subprocess.run(
        [NODE, 'tests/js/rodar_match.mjs', json.dumps(opcoes), *(f'{n}={c}' for n, c in pessoas)],
        cwd=RAIZ,
        capture_output=True,
        check=True,
    )
    return json.loads(saida.stdout.decode('utf-8'))


def _py(pessoas: list[tuple[str, Path]], opcoes: dict) -> dict:
    from conciliacao import comparar_perfis
    from perfil_gosto import perfil_de_arquivos
    from web.ponte import _configuracao

    config = _configuracao(
        opcoes.get('fuso', ''),
        opcoes.get('musicas', ''),
        opcoes.get('artistas', ''),
        opcoes.get('varios', 'manter'),
        False,
        bool(opcoes.get('deduplicar', False)),
    )
    perfis = [perfil_de_arquivos(str(c), n, config) for n, c in pessoas]
    pares = []
    for i, a in enumerate(perfis):
        for b in perfis[i + 1 :]:
            d = asdict(comparar_perfis(a, b))
            del d['pontuacao_generos'], d['generos_comuns']  # sem gêneros no navegador
            pares.append(d)
    return {
        'perfis': [
            {
                'nome': p.nome,
                'fonte': p.fonte,
                'top_artistas': p.top_artistas,
                'top_musicas': p.top_musicas,
            }
            for p in perfis
        ],
        'pares': pares,
    }


@pytest.mark.parametrize(
    'chaves, opcoes',
    [
        (('a', 'b', 'borda'), {}),
        (('a', 'empates', 'antigo'), {'varios': 'ignorar', 'deduplicar': True}),
        (('borda', 'b'), {'artistas': 'Ana', 'fuso': 'UTC'}),
    ],
)
def test_match_igual_ao_python(arquivos, chaves, opcoes):  # noqa: F811
    pessoas = [(f'P{k} {c}', arquivos[c]) for k, c in enumerate(chaves)]
    js = _js(pessoas, opcoes)
    if chaves[:2] == ('a', 'b'):  # a e b têm artistas em comum: o teste não compara só vazios
        assert js['pares'][0]['pontuacao'] > 0 and js['pares'][0]['artistas_comuns']
    _igual(_py(pessoas, opcoes), js, 'match')


def test_sem_plays_validos_falha_igual(arquivos):  # noqa: F811
    assert 'pelo menos 30 segundos' in _js([('Ana', arquivos['curtos'])], {})['erro']
