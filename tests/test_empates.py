"""Empates, corte do top 20 e proteção das verificações do golden master."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

import pandas as pd
import pytest
from apoio_golden import assert_tabela_golden

from analise import comparar

if TYPE_CHECKING:
    from conftest import FabricaEvento, HistoricosFicticios


@pytest.mark.parametrize('ordem', ['direta', 'inversa'])
def test_empates_no_corte_sao_alfabeticos(
    historicos: HistoricosFicticios, evento: FabricaEvento, ordem: str
) -> None:
    """Mais de vinte artistas/faixas empatados têm o mesmo desempate e corte."""
    nomes = [f'Artista {i:02d}' for i in range(1, 26)]
    eventos = [evento(artista=nome, musica='Mesmo título') for nome in nomes]
    if ordem == 'inversa':
        eventos.reverse()
    caminho = historicos.json(eventos)
    resultado = comparar(caminho, caminho, 'A', 'B', False)
    for perfil in (resultado.perfil_a, resultado.perfil_b):
        assert perfil.artistas.Artista.tolist() == nomes[:20]
        assert perfil.musicas.artista.tolist() == nomes[:20]
        assert perfil.musicas.musica.tolist() == ['Mesmo título'] * 20
        assert perfil.artistas['Reproduções'].tolist() == [1] * 20
        assert perfil.musicas['Reproduções'].tolist() == [1] * 20


def _referencia() -> dict:
    """Simula referência histórica com escolha diferente somente no empate do corte."""
    return {
        'dtypes': ['object', 'int64'],
        'valor': {
            'columns': ['Artista', 'Reproduções'],
            'index': [0, 1],
            'data': [['Líder', 5], ['B', 2]],
        },
    }


def test_golden_admite_somente_desempate_valido() -> None:
    """Contagens e líder permanecem iguais; o corte empatado segue o novo desempate."""
    atual = pd.DataFrame([['Líder', 5], ['A', 2]], columns=['Artista', 'Reproduções'])
    universo = Counter({('Líder',): 5, ('B',): 2, ('A',): 2})
    assert_tabela_golden(atual, _referencia(), universo)


@pytest.mark.parametrize('erro', ['contagem', 'nome', 'duplicacao', 'ordem', 'corte'])
def test_golden_rejeita_regressoes_reais(erro: str) -> None:
    """A flexibilização do empate não oculta contagens, identidades ou ordenação erradas."""
    atual = pd.DataFrame([['Líder', 5], ['A', 2]], columns=['Artista', 'Reproduções'])
    universo = Counter({('Líder',): 5, ('B',): 2, ('A',): 2})
    if erro == 'contagem':
        atual.loc[0, 'Reproduções'] = 6
    elif erro == 'nome':
        atual.loc[0, 'Artista'] = 'Inventado'
    elif erro == 'duplicacao':
        atual.loc[1, 'Artista'] = 'Líder'
    elif erro == 'ordem':
        atual = atual.iloc[::-1].reset_index(drop=True)
    else:
        atual.loc[1, 'Artista'] = 'B'
    with pytest.raises(AssertionError):
        assert_tabela_golden(atual, _referencia(), universo)
