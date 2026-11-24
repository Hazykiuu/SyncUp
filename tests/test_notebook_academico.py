"""Notebook acadêmico: 6 fases do CRISP-DM, ferramentas da disciplina e nenhum dado real."""

from __future__ import annotations

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
NOTEBOOK = RAIZ / 'notebook' / 'SyncUp_CRISP-DM.ipynb'


def _celulas() -> list[dict]:
    return json.loads(NOTEBOOK.read_text(encoding='utf-8'))['cells']


def _texto(tipo: str) -> str:
    return '\n'.join(''.join(c['source']) for c in _celulas() if c['cell_type'] == tipo)


def test_seis_fases_do_crisp_dm_em_ordem() -> None:
    markdown = _texto('markdown')
    fases = [
        'Entendimento do Negócio',
        'Entendimento dos Dados',
        'Preparação dos Dados',
        'Modelagem',
        'Avaliação',
        'Implantação',
    ]
    posicoes = [markdown.index(f'️⃣ {fase}') for fase in fases]
    assert posicoes == sorted(posicoes)


def test_usa_pandas_seaborn_e_describe() -> None:
    codigo = _texto('code')
    assert 'import pandas as pd' in codigo and 'import seaborn as sns' in codigo
    assert codigo.count('.describe()') >= 3
    for grafico in ('sns.histplot', 'sns.boxplot', 'sns.heatmap', 'sns.barplot', 'sns.lineplot'):
        assert grafico in codigo
    for metrica in ('def jaccard', 'def cosseno', 'def duplas_otimas', 'def recomendar'):
        assert metrica in codigo


def test_sem_saidas_nem_dados_reais() -> None:
    for celula in _celulas():
        if celula['cell_type'] == 'code':
            assert celula['outputs'] == [] and celula['execution_count'] is None


def test_notebook_igual_ao_gerador() -> None:
    import importlib.util

    import pytest

    pytest.importorskip('nbformat')
    spec = importlib.util.spec_from_file_location('gerador', RAIZ / 'tools' / 'gerar_notebook.py')
    gerador = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gerador)
    fontes = [''.join(c['source']) for c in _celulas()]
    assert fontes == [c.source for c in gerador.CELULAS]
