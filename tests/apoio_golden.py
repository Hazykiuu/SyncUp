"""Regressão rigorosa sem depender do desempate instável da referência v0.4."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from analise import TEMPO_MINIMO_PLAY_MS, PeriodoComparacao
from dados import carregar_historicos


def contagens_ranking(
    arquivo: Path, periodo: PeriodoComparacao, chaves: list[str]
) -> Counter[tuple[str, ...]]:
    """Conta diretamente os eventos válidos, independentemente do ranking produzido."""
    dados = carregar_historicos(arquivo).dados
    if periodo.comum:
        dados = dados[dados.data_utc.between(periodo.inicio_utc, periodo.fim_utc)]
    plays = dados[dados.ms_played >= TEMPO_MINIMO_PLAY_MS]
    colunas = ['artista'] if chaves == ['Artista'] else chaves
    return Counter(plays[colunas].itertuples(index=False, name=None))


def assert_tabela_golden(
    atual: pd.DataFrame,
    referencia: dict[str, Any],
    contagens: Counter[tuple[str, ...]] | None = None,
) -> None:
    """Preserva valores e permite só o novo desempate, inclusive no corte do top.

    A v0.4 usava quicksort, que não define a ordem entre contagens iguais.
    Rankings atuais devem coincidir exatamente com uma contagem independente,
    ordenada por contagem decrescente/nome crescente. A referência histórica
    ainda verifica colunas, tipos, número de linhas, contagens de cada posição
    e identidade/contagem de todos os itens acima do empate na última posição.
    Tabelas sem ranking continuam sendo comparadas integralmente.
    """
    split = referencia['valor']
    esperado = pd.DataFrame(split['data'], columns=split['columns'], index=split['index'])
    esperado = esperado.astype(dict(zip(split['columns'], referencia['dtypes'], strict=True)))
    if contagens is None:
        pd.testing.assert_frame_equal(atual, esperado, check_exact=False, rtol=1e-12, atol=1e-12)
        return
    assert atual.columns.tolist() == esperado.columns.tolist()
    assert atual.dtypes.tolist() == esperado.dtypes.tolist()
    pd.testing.assert_index_equal(atual.index, esperado.index)
    assert atual['Reproduções'].tolist() == esperado['Reproduções'].tolist()
    chaves = [c for c in atual.columns if c != 'Reproduções']
    ordenados = sorted(contagens.items(), key=lambda item: (-item[1], item[0]))[: len(atual)]
    correto = pd.DataFrame(
        [(*chave, quantidade) for chave, quantidade in ordenados], columns=atual.columns
    ).astype(dict(zip(esperado.columns, referencia['dtypes'], strict=True)))
    pd.testing.assert_frame_equal(atual, correto, check_exact=True)
    if esperado.empty:
        return
    limite = int(esperado['Reproduções'].iloc[-1])
    # Acima do corte, toda identidade deve continuar igual à referência histórica.
    sem_empate_no_corte = esperado[esperado['Reproduções'] > limite]
    novo_sem_empate = atual[atual['Reproduções'] > limite]
    pd.testing.assert_frame_equal(
        novo_sem_empate.sort_values(chaves).reset_index(drop=True),
        sem_empate_no_corte.sort_values(chaves).reset_index(drop=True),
        check_exact=True,
    )
