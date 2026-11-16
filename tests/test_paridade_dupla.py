"""Paridade da Dupla: a comparação em JS do app web dá o mesmo resultado que ``analise.comparar``.

Os mesmos arquivos passam pelo Python e por ``tests/js/rodar_dupla.mjs`` (Node). Números com
tolerância de 1e-9; listas e textos iguais. Reaproveita os arquivos e casos de borda do Wrapped.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tests.test_paridade_wrapped import NODE, RAIZ, _igual, arquivos  # noqa: F401 (fixture)

pytestmark = pytest.mark.skipif(NODE is None, reason='Node não instalado')


def _js(a: list[Path], b: list[Path], nomes: tuple[str, str], opcoes: dict) -> dict:
    lados = [f'a:{c}' for c in a] + [f'b:{c}' for c in b]
    saida = subprocess.run(
        [NODE, 'tests/js/rodar_dupla.mjs', json.dumps(opcoes), *nomes, *lados],
        cwd=RAIZ,
        capture_output=True,
        check=True,
    )
    return json.loads(saida.stdout.decode('utf-8'))


def _py(a: list[Path], b: list[Path], nomes: tuple[str, str], opcoes: dict) -> dict:
    """O mesmo recorte do resultado do Python, no formato que o JS devolve."""
    from analise import comparar
    from web.ponte import _configuracao

    config = _configuracao(
        opcoes.get('fuso', ''),
        opcoes.get('musicas', ''),
        opcoes.get('artistas', ''),
        opcoes.get('varios', 'manter'),
        False,
        bool(opcoes.get('deduplicar', False)),
    )
    r = comparar(
        [str(c) for c in a],
        [str(c) for c in b],
        *nomes,
        bool(opcoes.get('comum', True)),
        configuracao=config,
        ponderacao=opcoes.get('ponderacao') or 'bruta',
    )
    from web import ponte

    m, p = r.metricas, r.periodo

    def quase(x):
        return {
            'total_pares': x.total_pares,
            'exemplos': [
                [*linha[:7], float(linha[7])] for linha in x.exemplos.itertuples(index=False)
            ],
        }

    def data(valor):
        return None if valor is None else valor.floor('s').isoformat()

    def perfil(x):
        return {
            'nome': x.nome,
            'plays': x.plays,
            'horas': x.horas,
            'artistas': x.quantidade_artistas,
            'top_artistas': [[a, int(n)] for a, n in x.artistas.itertuples(index=False)],
            'top_musicas': [[mu, ar, int(n)] for mu, ar, n in x.musicas.itertuples(index=False)],
        }

    return {
        'metricas': {
            'cosseno': m.cosseno,
            'jaccard': m.jaccard,
            'jaccard_top20': m.jaccard_top20,
            'ruzicka': m.jaccard_ponderado,
        },
        'periodo': {'comum': p.comum, 'inicio': data(p.inicio), 'fim': data(p.fim)},
        'perfis': [perfil(r.perfil_a), perfil(r.perfil_b)],
        'comuns': r.artistas_comuns,
        'so_a': r.exclusivos_a,
        'so_b': r.exclusivos_b,
        'contribuicoes': [[a, float(v)] for a, v in r.contribuicoes.itertuples(index=False)],
        'playlist': [
            [ar, mu, int(x), int(y), link]
            for ar, mu, x, y, link in r.playlist.itertuples(index=False)
        ],
        'ponderacao': r.ponderacao,
        'quase_artistas': quase(r.momentos_artistas),
        'quase_musicas': quase(r.momentos_musicas),
        'sintonia': ponte._simples(ponte._sintonia_json(r)),
        'ponte': [
            [de, para, art, int(n), float(pct), link]
            for de, para, art, n, pct, link in r.ponte.itertuples(index=False)
        ],
        'diversidade': [{'entropia': x.entropia, 'gini': x.gini} for x in (r.perfil_a, r.perfil_b)],
        'estatisticas': [
            [float(v) for v in r.estatisticas[coluna]] for coluna in r.estatisticas.columns[1:]
        ],
    }


def _sintonia_borda(pasta: Path) -> tuple[Path, Path]:
    """Mesma faixa com nomes em caixas diferentes, plays que se sobrepõem, encontros com meses vazios
    no meio, um "quase" (a 40 min) e um encontro curto demais (20 s juntos)."""
    from tests.test_paridade_wrapped import _ev

    a = [
        _ev('2021-01-10T10:03:00Z', 'Zé Ramalho', 'Avôhai', 180_000),
        _ev('2021-01-10T10:04:00Z', 'Zé Ramalho', 'Avôhai', 120_000),  # sobrepõe o anterior
        _ev('2021-04-02T22:00:00Z', 'Lia', 'Noite', 200_000),
        _ev('2021-04-03T08:00:00Z', 'Rui', 'Manhã', 60_000),
        _ev('2021-04-05T12:00:00Z', 'Bo', 'Curta', 60_000),
    ]
    b = [
        _ev('2021-01-10T10:02:30Z', 'ZÉ RAMALHO', 'avôhai!', 150_000),
        _ev('2021-04-02T22:01:00Z', 'lia', 'noite', 200_000),
        _ev('2021-04-03T08:40:00Z', 'Rui', 'Manhã', 60_000),  # 40 min depois: quase juntos
        _ev('2021-04-05T12:00:40Z', 'Bo', 'Curta', 60_000),  # 20 s juntos: não conta
    ]
    caminhos = (pasta / 'sa.json', pasta / 'sb.json')
    for caminho, eventos in zip(caminhos, (a, b)):
        caminho.write_text(json.dumps(eventos, ensure_ascii=False), encoding='utf-8')
    return caminhos


def test_sintonia_de_borda_igual_ao_python(tmp_path: Path) -> None:
    sa, sb = _sintonia_borda(tmp_path)
    js = _js([sa], [sb], ('Ana', 'Bia'), {'comum': False})
    assert 'erro' not in js, js
    py = _py([sa], [sb], ('Ana', 'Bia'), {'comum': False})
    assert py['sintonia']['momentos'] == 2 and len(py['sintonia']['por_mes']) == 4
    for campo in ('sintonia', 'quase_musicas', 'quase_artistas', 'ponte', 'estatisticas'):
        _igual(py[campo], js[campo], campo)


CASOS = {
    'padrao': (['a'], ['b'], ('Ana', 'Bia'), {}),
    'raiz': (['a'], ['b'], ('Ana', 'Bia'), {'ponderacao': 'raiz'}),
    'log': (['a'], ['b'], ('Ana', 'Bia'), {'ponderacao': 'log1p'}),
    'sem_periodo_comum': (['a'], ['b'], ('', ' '), {'comum': False}),
    'borda': (['borda'], ['empates'], ('Lia', '<b>Rui</b>'), {}),
    'borda_opcoes': (
        ['b', 'borda'],
        ['a'],
        ('Lia', 'Ana'),
        {'varios': 'ignorar', 'deduplicar': True, 'artistas': 'zé', 'fuso': 'Europe/Lisbon'},
    ),
    'mesmo_arquivo': (['a'], ['a'], ('Ana', 'Ana 2'), {'ponderacao': 'log1p'}),
}


@pytest.mark.parametrize('caso', CASOS)
def test_dupla_js_igual_ao_python(arquivos: dict[str, Path], caso: str) -> None:  # noqa: F811
    ca, cb, nomes, opcoes = CASOS[caso]
    a, b = [arquivos[c] for c in ca], [arquivos[c] for c in cb]
    js = _js(a, b, nomes, opcoes)
    assert 'erro' not in js, js
    py = _py(a, b, nomes, opcoes)
    js['periodo'] = {k: js['periodo'][k] for k in ('comum', 'inicio', 'fim')}
    _igual(py, js, 'dupla')


def test_erros_iguais_aos_do_python(arquivos: dict[str, Path]) -> None:  # noqa: F811
    casos = [
        ([arquivos['curtos']], [arquivos['a']], {}),  # sem plays de 30 s num dos lados
        ([arquivos['antigo']], [arquivos['a']], {}),  # 2015 x 2018+: sem período em comum
        ([arquivos['a']], [arquivos['b']], {'ponderacao': 'quadrado'}),
    ]
    for a, b, opcoes in casos:
        with pytest.raises(ValueError) as erro:
            _py(a, b, ('Ana', 'Bia'), opcoes)
        assert _js(a, b, ('Ana', 'Bia'), opcoes) == {'erro': str(erro.value)}
