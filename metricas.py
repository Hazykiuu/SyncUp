"""Métricas em Python puro, com validação e estabilidade numérica explicáveis."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from math import isfinite

Frequencias = Mapping[str, int | float]


def _validar(frequencias: Frequencias) -> dict[str, float]:
    """Converte frequências e rejeita pesos negativos ou não finitos."""
    try:
        valores = {chave: float(valor) for chave, valor in frequencias.items()}
    except (TypeError, ValueError, OverflowError) as erro:
        raise ValueError('As frequências devem ser números finitos e não negativos.') from erro
    if any(not isfinite(valor) or valor < 0 for valor in valores.values()):
        raise ValueError('As frequências devem ser finitas e não negativas.')
    return valores


def _escalar(valores: dict[str, float], maior: float | None = None) -> dict[str, float]:
    """Divide por um peso positivo para impedir estouros nas somas e quadrados.

    Para Ruzicka, usa o mesmo divisor nos dois perfis, preservando volumes.
    Para cosseno, cada vetor pode ter seu divisor: a fórmula é invariante a escala.
    """
    escala = max(valores.values(), default=0.0) if maior is None else maior
    return {nome: valor / escala if escala else 0.0 for nome, valor in valores.items()}


def _preparar_cosseno(
    a: dict[str, float], b: dict[str, float]
) -> tuple[dict[str, float], dict[str, float], float]:
    """Reescala vetores validados e devolve o produto das normas estáveis."""
    va, vb = _escalar(a), _escalar(b)
    norma_a = sum(valor**2 for valor in va.values()) ** 0.5
    norma_b = sum(valor**2 for valor in vb.values()) ** 0.5
    return va, vb, norma_a * norma_b


def _cosseno(a: dict[str, float], b: dict[str, float]) -> float | None:
    """Calcula produto escalar/normas sem elevar pesos extremos ao quadrado."""
    va, vb, denominador = _preparar_cosseno(a, b)
    produto = sum(va[chave] * vb[chave] for chave in va.keys() & vb.keys())
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
    """Calcula Ruzicka: soma dos pesos mínimos / soma dos máximos em cada chave.

    Usa os pesos fornecidos, sem normalização automática. Pesos de chaves
    ausentes são zero; uma união com todos os pesos zero devolve None.
    """
    va, vb = _validar(a), _validar(b)
    escala = max(max(va.values(), default=0.0), max(vb.values(), default=0.0))
    va, vb = _escalar(va, escala), _escalar(vb, escala)
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


PONDERACOES = ('bruta', 'raiz', 'log1p')


def ponderar_contagens(frequencias: Frequencias, modo: str = 'bruta') -> dict[str, float]:
    """Aplica x, √x ou ln(1+x); não normaliza volumes entre perfis.

    As transformações reduzem a influência dos artistas muito repetidos.
    O logaritmo vem da biblioteca padrão; nenhuma métrica importa NumPy.
    """
    from math import log1p

    if modo not in PONDERACOES:
        raise ValueError('Ponderação inválida. Use bruta, raiz ou log1p.')
    valores = _validar(frequencias)
    if modo == 'raiz':
        return {nome: valor**0.5 for nome, valor in valores.items()}
    if modo == 'log1p':
        return {nome: log1p(valor) for nome, valor in valores.items()}
    return valores


def contribuicoes_cosseno(a: Frequencias, b: Frequencias) -> dict[str, float]:
    """Retorna aᵢ·bᵢ/(|a|·|b|) por artista; a soma é o cosseno.

    Artistas exclusivos contribuem zero. Vetores nulos devolvem zeros;
    o cosseno desses vetores continua indefinido (None).
    """
    va, vb, denominador = _preparar_cosseno(_validar(a), _validar(b))
    return {
        nome: va.get(nome, 0.0) * vb.get(nome, 0.0) / denominador if denominador else 0.0
        for nome in sorted(va.keys() | vb.keys())
    }


def entropia_normalizada(frequencias: Frequencias) -> float | None:
    """Calcula −Σp·ln(p)/ln(k), apenas para k artistas observados positivos.

    Uma categoria tem diversidade zero; ausência de categorias retorna None.
    Uniformidade entre categorias observadas vale um, sem medir gêneros.
    """
    from math import log

    valores = [x for x in _validar(frequencias).values() if x > 0]
    if not valores:
        return None
    if len(valores) == 1:
        return 0.0
    escala = max(valores)
    valores = [x / escala for x in valores]
    total = sum(valores)
    # Probabilidades que arredondam para zero têm contribuição limite de zero.
    entropia = -sum((x / total) * log(x / total) for x in valores if x > 0) / log(len(valores))
    return min(1.0, max(0.0, entropia))


def gini(frequencias: Frequencias) -> float | None:
    """Mede desigualdade das contagens positivas dos artistas observados.

    Usa Σ(2i−k−1)xᵢ/(kΣx), com valores crescentes e i começando em um.
    Uniformidade e uma única categoria dão zero; o teto é (k−1)/k.
    Não inclui artistas ausentes nem equivale a diversidade de gêneros.
    """
    valores = sorted(x for x in _validar(frequencias).values() if x > 0)
    if not valores:
        return None
    escala = max(valores)
    valores = [x / escala for x in valores]
    k = len(valores)
    return max(
        0.0,
        min(1.0, sum((2 * i - k - 1) * x for i, x in enumerate(valores, 1)) / (k * sum(valores))),
    )
