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
    from conciliacao import conciliar

    perfis = [perfil_de_arquivos(str(c), n, config) for n, c in pessoas]
    r = conciliar(perfis)
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
        'conciliacao': {
            'pares': [list(g) for g in r.pares],
            'melhores': {n: [list(x) for x in v] for n, v in r.melhores.items()},
            'media': r.pontuacao_media_pares,
        },
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


def test_emparelhamento_igual_ao_python():
    """Matrizes aleatórias com muitos empates (valores inteiros pequenos), de 1 a 9 pessoas."""
    import random

    import pandas as pd

    from conciliacao import emparelhamento_otimo

    sorteio = random.Random(7)
    casos = []
    for n in [1, 2, 3, 4, 5, 6, 7, 8, 9] * 6:
        nomes = [f'P{k}' for k in range(n)]
        valores = [[100.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                valores[i][j] = valores[j][i] = float(sorteio.choice([0, 1, 2, 5, 12.5]))
        casos.append({'nomes': nomes, 'valores': valores})
    saida = subprocess.run(
        [NODE, 'tests/js/rodar_match.mjs', json.dumps({'_matrizes': casos})],
        cwd=RAIZ,
        capture_output=True,
        check=True,
    )
    js = json.loads(saida.stdout)
    for caso, grupos in zip(casos, js, strict=True):
        m = pd.DataFrame(caso['valores'], index=caso['nomes'], columns=caso['nomes'])
        assert [list(g) for g in emparelhamento_otimo(m)] == grupos, caso


def _node(script: str, entrada: str) -> str:
    saida = subprocess.run(
        [NODE, '--input-type=module', '-e', script],
        cwd=RAIZ,
        input=entrada.encode('utf-8'),
        capture_output=True,
        check=True,
    )
    return saida.stdout.decode('utf-8')


LER = """import { lerConvite } from './site/app/js/convite.js';
let s = ''; for await (const c of process.stdin) s += c;
process.stdout.write(JSON.stringify(await lerConvite(s)));"""
GERAR = """import { gerarConvite } from './site/app/js/convite.js';
let s = ''; for await (const c of process.stdin) s += c;
process.stdout.write(await gerarConvite(JSON.parse(s)));"""


def test_convite_do_pc_abre_no_navegador_e_vice_versa(arquivos):  # noqa: F811
    from convite import gerar_convite, ler_convite
    from perfil_gosto import perfil_de_arquivos

    perfil = perfil_de_arquivos(str(arquivos['a']), 'Ana 🎸')
    rankings = {'top_artistas': perfil.top_artistas, 'top_musicas': perfil.top_musicas}
    no_js = json.loads(_node(LER, gerar_convite(perfil)))
    assert {k: no_js[k] for k in rankings} == rankings and no_js['nome'] == 'Ana 🎸'
    codigo = _node(GERAR, json.dumps({'nome': perfil.nome, **rankings}))
    no_py = ler_convite(codigo)
    assert no_py.nome == 'Ana 🎸'
    assert {'top_artistas': no_py.top_artistas, 'top_musicas': no_py.top_musicas} == rankings
