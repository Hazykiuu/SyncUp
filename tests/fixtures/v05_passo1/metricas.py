"""Métricas puras com Python; biblioteca padrão apenas para validar valores."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from math import isfinite

Frequencias = Mapping[str, int | float]


def _validar(frequencias: Frequencias) -> dict[str, float]:
    """Converte frequências e rejeita pesos negativos ou não finitos."""
    valores = {chave: float(valor) for chave, valor in frequencias.items()}
    if any(not isfinite(valor) or valor < 0 for valor in valores.values()):
        raise ValueError('As frequências devem ser finitas e não negativas.')
    return valores


def _cosseno(a: dict[str, float], b: dict[str, float]) -> float | None:
    """Calcula o produto escalar esparso dividido pelas duas normas."""
    produto = sum(a[chave] * b[chave] for chave in a.keys() & b.keys())
    norma_a = sum(valor ** 2 for valor in a.values()) ** 0.5
    norma_b = sum(valor ** 2 for valor in b.values()) ** 0.5
    denominador = norma_a * norma_b
    return max(0.0, min(1.0, produto / denominador)) if denominador else None


def cosseno(a: Frequencias, b: Frequencias) -> float | None:
    """Compara frequências; devolve None se algum vetor tem norma zero."""
    return _cosseno(_validar(a), _validar(b))


def jaccard(a: Iterable[str], b: Iterable[str]) -> float | None:
    """Divide a interseção pela união de conjuntos; união vazia devolve None."""
    conjunto_a, conjunto_b = set(a), set(b)
    uniao = conjunto_a | conjunto_b
    return len(conjunto_a & conjunto_b) / len(uniao) if uniao else None


def jaccard_ponderado(a: Frequencias, b: Frequencias) -> float | None:
    """Divide a soma dos pesos mínimos pela soma dos máximos em cada chave.

    Usa os pesos fornecidos, sem normalização automática. Pesos de chaves
    ausentes são zero; uma união com todos os pesos zero devolve None.
    """
    va, vb = _validar(a), _validar(b)
    chaves = va.keys() | vb.keys()
    minimo = sum(min(va.get(chave, 0.0), vb.get(chave, 0.0)) for chave in chaves)
    maximo = sum(max(va.get(chave, 0.0), vb.get(chave, 0.0)) for chave in chaves)
    return minimo / maximo if maximo else None


def metricas(a: Frequencias, b: Frequencias) -> tuple[float | None, float | None]:
    """Mantém a API v0.4: retorna cosseno e Jaccard dos pesos positivos.

    Também aceita Series de pandas, pois possuem o método items().
    """
    va, vb = _validar(a), _validar(b)
    artistas_a = {chave for chave, valor in va.items() if valor > 0}
    artistas_b = {chave for chave, valor in vb.items() if valor > 0}
    return _cosseno(va, vb), jaccard(artistas_a, artistas_b)
