"""Coincidências temporais e descobertas locais; nenhuma chamada de rede."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from urllib.parse import quote

import pandas as pd

JANELA_SINCRONIA_HORAS = 1.0
MAXIMO_EXEMPLOS_SINCRONIA = 200
MAXIMO_DESCOBERTAS_POR_DIRECAO = 10
COLUNAS_MOMENTOS = [
    'Artista',
    'Música A',
    'Música B',
    'Instante A (UTC)',
    'Instante B (UTC)',
    'Horário A',
    'Horário B',
    'Distância (min)',
]
COLUNAS_PONTE = [
    'De',
    'Para',
    'Artista',
    'Reproduções na origem',
    'Participação na origem (%)',
    'Spotify',
]
COLUNAS_PLAYLIST = ['Artista', 'Música', 'Reproduções A', 'Reproduções B', 'Spotify']


@dataclass(frozen=True)
class MomentosSincronizados:
    """Pares de eventos sem reutilização; exemplos são limitados, total é exato."""

    tipo: Literal['artista', 'musica']
    janela_horas: float
    total_pares: int
    exemplos: pd.DataFrame


def link_spotify(artista: str, musica: str = '') -> str:
    """Constrói link de busca, sem afirmar conhecer o ID oficial da faixa."""
    consulta = f'{artista} {musica}'.strip()
    return 'https://open.spotify.com/search/' + quote(consulta, safe='')


def _codigos(a: pd.Series, b: pd.Series) -> tuple[pd.Series, pd.Series, int]:
    """Converte nomes em códigos inteiros comuns, preservando a ordem alfabética."""
    categorias_a = a.cat.categories if isinstance(a.dtype, pd.CategoricalDtype) else a.unique()
    categorias_b = b.cat.categories if isinstance(b.dtype, pd.CategoricalDtype) else b.unique()
    categorias = pd.Index(categorias_a).union(pd.Index(categorias_b)).sort_values()

    def recodificar(serie: pd.Series) -> pd.Series:
        if isinstance(serie.dtype, pd.CategoricalDtype):
            serie = serie.cat.set_categories(categorias)
        else:
            serie = serie.astype(pd.CategoricalDtype(categorias))
        return serie.cat.codes.astype('int64')

    return recodificar(a), recodificar(b), len(categorias)


def _chaves_comuns(
    a: pd.DataFrame, b: pd.DataFrame, tipo: Literal['artista', 'musica']
) -> tuple[pd.Series, pd.Series]:
    """Chave inteira por artista ou (artista, música), comparável entre os dois perfis."""
    artista_a, artista_b, _ = _codigos(a.artista, b.artista)
    if tipo == 'artista':
        return artista_a, artista_b
    musica_a, musica_b, quantidade = _codigos(a.musica, b.musica)
    return artista_a * quantidade + musica_a, artista_b * quantidade + musica_b


def _ordenar_eventos(
    dados: pd.DataFrame, chave: pd.Series, comuns: pd.Index
) -> tuple[list[int], list[int], list[int]]:
    """Filtra chaves comuns e ordena por (chave, instante UTC) de forma estável."""
    eventos = pd.DataFrame(
        {
            'chave': chave.to_numpy(),
            'instante': dados.data_utc.astype('int64').to_numpy(),
            'posicao': range(len(dados)),
        }
    )
    eventos = eventos[eventos.chave.isin(comuns)].sort_values(['chave', 'instante'], kind='stable')
    return eventos.chave.tolist(), eventos.instante.tolist(), eventos.posicao.tolist()


def momentos_sincronizados(
    a: pd.DataFrame,
    b: pd.DataFrame,
    tipo: Literal['artista', 'musica'] = 'musica',
    janela_horas: float = JANELA_SINCRONIA_HORAS,
) -> MomentosSincronizados:
    """Emparelha eventos cronológicos em UTC com distância ≤ janela.

    Dois ponteiros por artista ou (artista, música) encontram o máximo de
    pares um a um possível na janela, sem reutilizar eventos dentro deste
    tipo de análise. Não faz produto cartesiano nem arredonda horas.
    Complexidade: ordenação O(n log n), emparelhamento O(n). Os dois tipos
    são análises alternativas; seus totais não devem ser somados.
    Exemplos: primeiros 200 na ordem de artista/música e instante.
    Datas do Spotify são instantes registrados, não intervalos de reprodução.
    """
    from math import isfinite

    if tipo not in ('artista', 'musica') or not isfinite(janela_horas) or janela_horas < 0:
        raise ValueError('Informe artista/musica e uma janela finita não negativa.')
    limite = int(janela_horas * 3_600_000_000_000)
    chave_a, chave_b = _chaves_comuns(a, b, tipo)
    # Só eventos cuja chave aparece nos dois perfis podem formar pares.
    comuns = pd.Index(chave_a).intersection(pd.Index(chave_b))
    ordenado_a = _ordenar_eventos(a, chave_a, comuns)
    ordenado_b = _ordenar_eventos(b, chave_b, comuns)
    ka, ta, pa = ordenado_a
    kb, tb, pb = ordenado_b
    pares: list[tuple[int, int]] = []
    total = 0
    i, j, na, nb = 0, 0, len(ka), len(kb)
    # Fusão única de duas sequências ordenadas por (chave, instante): O(n) no total.
    while i < na and j < nb:
        chave_i, chave_j = ka[i], kb[j]
        if chave_i < chave_j:
            i += 1
        elif chave_i > chave_j:
            j += 1
        else:
            distancia = ta[i] - tb[j]
            if distancia < -limite:
                i += 1
            elif distancia > limite:
                j += 1
            else:
                total += 1
                if len(pares) < MAXIMO_EXEMPLOS_SINCRONIA:
                    pares.append((i, j))
                i += 1
                j += 1
    linhas_a = a.iloc[[pa[i] for i, _ in pares]]
    linhas_b = b.iloc[[pb[j] for _, j in pares]]
    exemplos = [
        [
            str(art_a),
            str(mus_a),
            str(mus_b),
            utc_a.isoformat(),
            utc_b.isoformat(),
            str(local_a),
            str(local_b),
            abs(ta[i] - tb[j]) / 60_000_000_000,
        ]
        for (i, j), art_a, mus_a, mus_b, utc_a, utc_b, local_a, local_b in zip(
            pares,
            linhas_a.artista,
            linhas_a.musica,
            linhas_b.musica,
            linhas_a.data_utc,
            linhas_b.data_utc,
            linhas_a.data,
            linhas_b.data,
        )
    ]
    return MomentosSincronizados(
        tipo, janela_horas, total, pd.DataFrame(exemplos, columns=COLUNAS_MOMENTOS)
    )


def ponte_musical(a: pd.Series, b: pd.Series, nome_a: str, nome_b: str) -> pd.DataFrame:
    """Sugere líderes exclusivos de cada origem para o outro perfil.

    Ausência é no recorte enviado, não desinteresse ou descoberta comprovada.
    Não infere influência entre pessoas nem usa dados externos de gêneros.
    """
    linhas = []
    for origem, destino, nome, outro in ((a, b, nome_a, nome_b), (b, a, nome_b, nome_a)):
        exclusivos = (
            origem[~origem.index.isin(destino.index)]
            .sort_values(ascending=False, kind='stable')
            .head(MAXIMO_DESCOBERTAS_POR_DIRECAO)
        )
        total = int(origem.sum())
        for artista, plays in exclusivos.items():
            linhas.append(
                [
                    nome,
                    outro,
                    str(artista),
                    int(plays),
                    float(plays) / total * 100,
                    link_spotify(str(artista)),
                ]
            )
    return pd.DataFrame(linhas, columns=COLUNAS_PONTE)


def playlist_comum(a: pd.Series, b: pd.Series) -> pd.DataFrame:
    """Cruza faixas por (música, artista), sem confundir títulos homônimos."""
    aa = a.rename('Reproduções A').reset_index()
    bb = b.rename('Reproduções B').reset_index()
    comum = aa.merge(bb, on=['musica', 'artista'], how='inner', validate='one_to_one')
    comum['total'] = comum['Reproduções A'] + comum['Reproduções B']
    comum = comum.sort_values(
        ['total', 'artista', 'musica'], ascending=[False, True, True], kind='stable'
    )
    linhas = [
        [
            str(linha[0]),
            str(linha[1]),
            int(linha[2]),
            int(linha[3]),
            link_spotify(str(linha[0]), str(linha[1])),
        ]
        for linha in comum[['artista', 'musica', 'Reproduções A', 'Reproduções B']].itertuples(
            index=False, name=None
        )
    ]
    return pd.DataFrame(linhas, columns=COLUNAS_PLAYLIST)
