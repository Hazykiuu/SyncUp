"""Regras experimentais de arquétipos, com parâmetros centralizados."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from heapq import nlargest

import pandas as pd

from formatacao import fmt_pct

AVISO_TRACOS = (
    'Arquétipos e traços são regras experimentais sobre este recorte de escuta. '
    'Não medem personalidade ou afinidade amorosa. Não são testes psicológicos.'
)

LIMIAR_FAVORITOS = 0.60
LIMIAR_REPEAT = 0.40
LIMIAR_MADRUGADA = 0.40
QUANTIDADE_FAVORITOS = 2
QUANTIDADE_FAIXAS_REPEAT = 10
HORA_INICIO_MADRUGADA = 0
HORA_FIM_MADRUGADA = 6  # Limite exclusivo.


@dataclass(frozen=True)
class DimensaoArquetipo:
    """Nome e proporção observada de uma dimensão de escuta."""

    nome: str
    proporcao: float
    descricao: str
    limiar: float


@dataclass(frozen=True)
class ArquetiposMusicais:
    """Três regras explicáveis; não representam um teste de personalidade."""

    favoritos: DimensaoArquetipo
    repeticao: DimensaoArquetipo
    madrugada: DimensaoArquetipo


def classificar_arquetipos(
    artistas: Mapping[str, int],
    faixas: Mapping[tuple[str, str], int],
    total_plays: int,
    plays_madrugada: int,
) -> ArquetiposMusicais:
    """Classifica um recorte a partir de contagens já calculadas."""
    if total_plays <= 0:
        raise ValueError('Arquétipos exigem pelo menos uma reprodução válida.')
    if not 0 <= plays_madrugada <= total_plays:
        raise ValueError('A contagem de madrugada deve estar entre zero e total_plays.')
    for contagens in (artistas, faixas):
        if any(valor < 0 for valor in contagens.values()) or sum(contagens.values()) != total_plays:
            raise ValueError('Cada conjunto de contagens deve somar total_plays.')
    concentracao = sum(nlargest(QUANTIDADE_FAVORITOS, artistas.values())) / total_plays
    repeticao = sum(nlargest(QUANTIDADE_FAIXAS_REPEAT, faixas.values())) / total_plays
    madrugada = plays_madrugada / total_plays
    return classificar_proporcoes(concentracao, repeticao, madrugada)


def classificar_proporcoes(
    concentracao: float, repeticao: float, madrugada: float
) -> ArquetiposMusicais:
    """Aplica as mesmas regras a proporções já agregadas por pandas."""
    if any(not 0 <= valor <= 1 for valor in (concentracao, repeticao, madrugada)):
        raise ValueError('As proporções dos arquétipos devem estar entre zero e um.')
    return ArquetiposMusicais(
        favoritos=DimensaoArquetipo(
            'Fiel aos favoritos' if concentracao >= LIMIAR_FAVORITOS else 'Gosto distribuído',
            concentracao,
            'Participação dos dois artistas líderes nas reproduções.',
            LIMIAR_FAVORITOS,
        ),
        repeticao=DimensaoArquetipo(
            'Mestre do repeat' if repeticao >= LIMIAR_REPEAT else 'Repertório variado',
            repeticao,
            'Participação das dez faixas líderes nas reproduções. Em amostras pequenas, este valor tende a ser alto.',
            LIMIAR_REPEAT,
        ),
        madrugada=DimensaoArquetipo(
            'Coruja musical' if madrugada >= LIMIAR_MADRUGADA else 'Fora da madrugada',
            madrugada,
            'Reproduções entre 00h e 05h59, no fuso horário selecionado.',
            LIMIAR_MADRUGADA,
        ),
    )


def arquetipo(contagens: pd.Series) -> str:
    """Preserva o texto do arquétipo inicial, disponível na v0.4."""
    total = int(contagens.sum())
    if total <= 0:
        raise ValueError('Arquétipos exigem contagens positivas.')
    concentracao = float(contagens.nlargest(QUANTIDADE_FAVORITOS).sum()) / total
    nome = 'Fiel aos favoritos' if concentracao >= LIMIAR_FAVORITOS else 'Gosto distribuído'
    return (
        f'**{nome}** — seus dois artistas líderes representam **{fmt_pct(concentracao)}** '
        f'das reproduções no recorte. Regra experimental: concentração ≥{LIMIAR_FAVORITOS:.0%} '
        'recebe Fiel aos favoritos. ' + AVISO_TRACOS
    )
