"""Casos de borda e resultados analíticos das métricas em Python puro."""

from __future__ import annotations

import math
from collections.abc import Callable

import pytest

from metricas import (
    contribuicoes_cosseno,
    cosseno,
    entropia_normalizada,
    gini,
    jaccard,
    jaccard_ponderado,
    metricas,
    ponderar_contagens,
)


@pytest.mark.parametrize(
    'a,b', [({}, {}), ({}, {'A': 1}), ({'A': 0}, {'A': 1}), ({'A': 0, 'B': 0}, {'A': 0})]
)
def test_cosseno_vazio_ou_norma_nula(a: dict[str, float], b: dict[str, float]) -> None:
    """Norma zero é indefinida, em vez de falsa similaridade de zero ou cem por cento."""
    assert cosseno(a, b) is None
    assert cosseno(b, a) is None


@pytest.mark.parametrize(
    'a,b,esperado',
    [
        ({'A': 1}, {'B': 1}, 0),
        ({'A': 3, 'B': 4}, {'A': 6, 'B': 8}, 1),
        ({'A': 3, 'B': 4}, {'A': 3}, 0.6),
    ],
)
def test_cosseno_ortogonal_proporcional_e_conhecido(
    a: dict[str, float], b: dict[str, float], esperado: float
) -> None:
    """Confere ortogonalidade, escala e uma projeção com norma 3–4–5."""
    assert cosseno(a, b) == pytest.approx(esperado, abs=1e-14)
    assert cosseno(b, a) == pytest.approx(esperado, abs=1e-14)


@pytest.mark.parametrize(
    'a,b,esperado',
    [
        ([], [], None),
        ([], ['A'], 0),
        (['A', 'A'], ['A'], 1),
        (['A'], ['B'], 0),
        (['A', 'B'], ['B', 'C'], 1 / 3),
    ],
)
def test_jaccard_bordas(a: list[str], b: list[str], esperado: float | None) -> None:
    """Listas viram conjuntos; duplicações e ordem não alteram o Jaccard."""
    resultado = jaccard(iter(a), iter(b))
    assert resultado == esperado
    assert jaccard(b, a) == esperado


def test_api_compatibilidade_ignora_pesos_zero_no_jaccard() -> None:
    """A API metricas mantém a tupla de dois valores e artistas de peso positivo."""
    assert metricas({}, {}) == (None, None)
    assert metricas({'A': 0}, {'A': 2}) == (None, 0)
    assert metricas({'A': 1, 'B': 0}, {'A': 1}) == (1, 1)


def test_soma_exata_das_contribuicoes_em_vetor_conhecido() -> None:
    """Caso 3–4–5: contribuições 9/25 e 16/25 somam exatamente 1 em float."""
    contribuicoes = contribuicoes_cosseno({'A': 3, 'B': 4}, {'A': 3, 'B': 4})
    assert contribuicoes == {'A': 9 / 25, 'B': 16 / 25}
    assert sum(contribuicoes.values()) == cosseno({'A': 3, 'B': 4}, {'A': 3, 'B': 4}) == 1


@pytest.mark.parametrize('modo', ['bruta', 'raiz', 'log1p'])
def test_contribuicoes_somam_cosseno_ponderado(modo: str) -> None:
    """Nos demais vetores usa tolerância, pois somas de ponto flutuante não são exatas."""
    a = ponderar_contagens({'A': 9, 'B': 4, 'Exclusivo A': 1}, modo)
    b = ponderar_contagens({'A': 2, 'B': 4, 'Exclusivo B': 7}, modo)
    contribuicoes = contribuicoes_cosseno(a, b)
    assert contribuicoes['Exclusivo A'] == contribuicoes['Exclusivo B'] == 0
    assert math.fsum(contribuicoes.values()) == pytest.approx(cosseno(a, b), abs=1e-14)
    assert contribuicoes == contribuicoes_cosseno(b, a)
    assert contribuicoes_cosseno({'A': 0}, {'A': 3}) == {'A': 0}


@pytest.mark.parametrize(
    'a,b,esperado',
    [
        ({}, {}, None),
        ({'A': 0}, {'B': 0}, None),
        ({'A': 1}, {'B': 1}, 0),
        ({'A': 2}, {'A': 2}, 1),
        ({'A': 2, 'B': 1}, {'A': 1, 'C': 1}, 0.25),
        ({'A': 10}, {'A': 1}, 0.1),
    ],
)
def test_ruzicka_usa_pesos_absolutos(
    a: dict[str, float], b: dict[str, float], esperado: float | None
) -> None:
    """Ruzicka responde ao volume mesmo quando o cosseno é um."""
    assert jaccard_ponderado(a, b) == esperado
    assert jaccard_ponderado(b, a) == esperado


@pytest.mark.parametrize('invalido', [-1, float('nan'), float('inf'), -float('inf')])
@pytest.mark.parametrize('funcao', [cosseno, jaccard_ponderado, contribuicoes_cosseno])
def test_metricas_rejeitam_pesos_invalidos(funcao: Callable[..., object], invalido: float) -> None:
    """Um peso inválido é recusado mesmo se pertencer a um artista exclusivo."""
    with pytest.raises(ValueError, match='finitas e não negativas'):
        funcao({'Exclusivo': invalido}, {'A': 1})


@pytest.mark.parametrize('funcao', [ponderar_contagens, entropia_normalizada, gini])
def test_metricas_unarias_rejeitam_peso_negativo(funcao: Callable[..., object]) -> None:
    """Validação também se aplica à transformação e aos indicadores de diversidade."""
    with pytest.raises(ValueError):
        funcao({'A': -1})


def test_transformacoes_e_diversidade() -> None:
    """Calcula raiz/logaritmo e bordas da entropia/Gini independentemente do fluxo de arquivos."""
    assert ponderar_contagens({'A': 9}, 'raiz') == {'A': 3}
    assert ponderar_contagens({'A': 9}, 'log1p')['A'] == pytest.approx(math.log(10))
    with pytest.raises(ValueError, match='Ponderação inválida'):
        ponderar_contagens({}, 'incorreta')
    assert entropia_normalizada({}) is None
    assert gini({'A': 0}) is None
    assert entropia_normalizada({'A': 1}) == gini({'A': 1}) == 0
    assert entropia_normalizada({'A': 1, 'B': 1}) == pytest.approx(1)
    assert gini({'A': 1, 'B': 1}) == 0
    assert gini({'A': 1, 'B': 3}) == pytest.approx(0.25)


@pytest.mark.parametrize('peso', [1e308, 1e-200])
def test_pesos_finitos_extremos_nao_estouram_nem_viram_norma_zero(peso: float) -> None:
    """Reescalonamento algébrico evita overflow/underflow sem modificar as fórmulas."""
    vetor = {'A': peso, 'B': peso}
    assert cosseno(vetor, vetor) == pytest.approx(1, abs=1e-14)
    assert jaccard_ponderado(vetor, vetor) == 1
    contribuicoes = contribuicoes_cosseno(vetor, vetor)
    assert contribuicoes == pytest.approx({'A': 0.5, 'B': 0.5})
    assert sum(contribuicoes.values()) == pytest.approx(1)
    assert entropia_normalizada(vetor) == pytest.approx(1)
    assert gini(vetor) == 0
