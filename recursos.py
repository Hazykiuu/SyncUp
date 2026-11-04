"""Coincidências temporais e descobertas locais; nenhuma chamada de rede."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from urllib.parse import quote

import pandas as pd

from configuracao import normalizar_nome

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


MINIMO_JUNTOS_S = 30  # Sobreposição mínima para contar como "ao mesmo tempo".
DIAS_SEMANA = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo']


@dataclass(frozen=True)
class MomentoJuntos:
    """Um trecho em que os dois ouviam a mesma faixa no mesmo instante."""

    artista: str
    musica: str
    inicio_utc: pd.Timestamp
    inicio_local: pd.Timestamp  # no fuso de quem enviou o histórico A
    minutos: float


@dataclass(frozen=True)
class Sintonia:
    """Escuta simultânea de verdade: intervalos [fim − duração, fim] que se cruzam."""

    # shortcut: guarda todos os momentos (poucos KB cada) no State da sessão por 1 h;
    # limitar a uma amostra se o app passar a atender muitos usuários num servidor.
    momentos: list[MomentoJuntos]  # em ordem cronológica
    minutos: float
    top_musicas: list[tuple[str, str, int, float]]  # música, artista, vezes, minutos
    por_mes: pd.Series  # 'AAAA-MM' → minutos juntos
    hora_favorita: int | None
    dia_favorito: str | None
    quase_juntos: int = 0  # mesma faixa a menos de 1 h, sem chegar a 30 s juntos

    @property
    def primeira(self) -> MomentoJuntos | None:
        return self.momentos[0] if self.momentos else None

    @property
    def mais_recente(self) -> MomentoJuntos | None:
        return self.momentos[-1] if self.momentos else None

    @property
    def mais_longo(self) -> MomentoJuntos | None:
        return max(self.momentos, key=lambda m: (m.minutos, -m.inicio_utc.value), default=None)


def _normalizados(serie: pd.Series) -> tuple[pd.Series, pd.Index]:
    """Código inteiro de cada valor e o vocabulário de nomes normalizados (sem repetidos)."""
    if isinstance(serie.dtype, pd.CategoricalDtype):
        codigos, nomes = serie.cat.codes.to_numpy(), serie.cat.categories.astype(str)
    else:
        codigos, nomes = pd.factorize(serie.astype(str), sort=False)
    # Nomes diferentes podem normalizar igual ("Ana" e "ana"): recodifica pelos normalizados.
    recodigos, normais = pd.factorize(pd.Index([normalizar_nome(n) or n.casefold() for n in nomes]))
    return pd.Series(recodigos).take(codigos).reset_index(drop=True), pd.Index(normais)


@dataclass(frozen=True)
class Escutas:
    """Intervalos de escuta de uma pessoa, prontos para cruzar com os de qualquer outra.

    ``tabela``: ``artista`` e ``musica`` (códigos nos vocabulários normalizados),
    ``inicio`` e ``fim`` (ns UTC), ``nome_artista`` e ``nome_musica`` (como
    vieram) e ``deslocamento`` (ns até o horário local).
    """

    tabela: pd.DataFrame
    artistas: pd.Index
    musicas: pd.Index

    def __len__(self) -> int:
        return len(self.tabela)


def escutas(dados: pd.DataFrame) -> Escutas:
    """Cada play vira ``[fim − duração, fim]``; plays sobrepostos da mesma faixa se unem.

    Eventos repetidos ou a mesma faixa em dois aparelhos não contam o mesmo
    trecho duas vezes. Artista e música são normalizados (``normalizar_nome``)
    para que fontes diferentes (ZIP e ListenBrainz) se encontrem. Os nomes e o
    fuso de cada intervalo vêm do 1º play dele.
    """
    artista, artistas = _normalizados(dados.artista)
    musica, musicas = _normalizados(dados.musica)
    fim = dados.data_utc.astype('int64').to_numpy()
    tabela = pd.DataFrame(
        {
            'faixa': artista.to_numpy() * max(len(musicas), 1) + musica.to_numpy(),
            'inicio': fim - dados.ms_played.astype('int64').to_numpy() * 1_000_000,
            'fim': fim,
            'posicao': range(len(dados)),
        }
    )
    tabela = tabela[tabela.fim > tabela.inicio].sort_values(['faixa', 'inicio'], kind='stable')
    # Um intervalo novo começa quando a faixa muda ou quando começa depois do maior fim
    # visto até ali na mesma faixa; senão é sobreposto ao anterior e os dois se unem.
    maior_fim = tabela.groupby('faixa', sort=False, observed=True).fim.cummax()
    anterior = maior_fim.groupby(tabela.faixa, sort=False, observed=True).shift()
    grupo = (anterior.isna() | (tabela.inicio > anterior)).cumsum()
    unidos = tabela.groupby(grupo, sort=False, observed=True).agg(
        inicio=('inicio', 'first'), fim=('fim', 'max'), posicao=('posicao', 'first')
    )
    posicoes = unidos.posicao.to_numpy()
    primeiras = dados.iloc[posicoes]
    deslocamento = primeiras.data - primeiras.data_utc.dt.tz_localize(None)
    return Escutas(
        pd.DataFrame(
            {
                'artista': artista.to_numpy()[posicoes],
                'musica': musica.to_numpy()[posicoes],
                'inicio': unidos.inicio.to_numpy(),
                'fim': unidos.fim.to_numpy(),
                'nome_artista': primeiras.artista.to_numpy(),
                'nome_musica': primeiras.musica.to_numpy(),
                'deslocamento': deslocamento.astype('int64').to_numpy(),
            }
        ),
        artistas,
        musicas,
    )


def sintonia_entre(ea: Escutas, eb: Escutas) -> Sintonia:
    """Momentos em que A e B tocavam a mesma faixa ao mesmo tempo, a partir de ``escutas``.

    Os códigos de B são traduzidos para os vocabulários de A (custo pelo número
    de nomes, não de plays). Como os intervalos de cada pessoa numa faixa já
    estão unidos (não se sobrepõem), um intervalo de B só pode cruzar, entre os
    de A que começaram antes dele, o último. Duas buscas ``merge_asof`` (B
    depois de A, A depois de B) acham assim todos os cruzamentos, cada um uma
    vez, sem laço em Python: barato o bastante para comparar todos com todos.
    Cada sobreposição de pelo menos ``MINIMO_JUNTOS_S`` segundos é um momento
    juntos. Nomes e horário local vêm de A.
    """
    ta, tb = ea.tabela, eb.tabela
    largura = max(len(ea.musicas), 1)
    artista_b = ea.artistas.get_indexer(eb.artistas)[tb.artista.to_numpy()]  # -1: A não tem
    musica_b = ea.musicas.get_indexer(eb.musicas)[tb.musica.to_numpy()]
    faixa_a = ta.artista.to_numpy() * largura + ta.musica.to_numpy()
    faixa_b = artista_b * largura + musica_b
    tem_b = (artista_b >= 0) & (musica_b >= 0)
    comum_b = tem_b & pd.Series(faixa_b).isin(faixa_a).to_numpy()
    comum_a = pd.Series(faixa_a).isin(faixa_b[tem_b]).to_numpy()
    a = ta[comum_a].reset_index(drop=True)
    xa = pd.DataFrame(
        {'faixa': faixa_a[comum_a], 'ia': a.inicio, 'fa': a.fim, 'linha': range(len(a))}
    ).sort_values('ia', kind='stable')
    xb = pd.DataFrame(
        {
            'faixa': faixa_b[comum_b],
            'ib': tb.inicio.to_numpy()[comum_b],
            'fb': tb.fim.to_numpy()[comum_b],
        }
    ).sort_values('ib', kind='stable')
    pares = pd.concat(
        [
            pd.merge_asof(xb, xa, left_on='ib', right_on='ia', by='faixa'),
            pd.merge_asof(
                xa, xb, left_on='ia', right_on='ib', by='faixa', allow_exact_matches=False
            ),
        ]
    ).dropna(subset=['ia', 'ib'])
    inicio = pares.ia.where(pares.ia > pares.ib, pares.ib).astype('int64')
    duracao = pares.fa.where(pares.fa < pares.fb, pares.fb).astype('int64') - inicio
    juntos = duracao >= MINIMO_JUNTOS_S * 1_000_000_000
    # shortcut: "quase" conta só o vizinho mais próximo de cada intervalo (um piso, não o
    # total exato); usar momentos_sincronizados se o número precisar bater com o da Dupla.
    quase = int((~juntos & (-duracao <= JANELA_SINCRONIA_HORAS * 3600 * 1_000_000_000)).sum())
    achados = sorted(
        zip(
            pares.linha[juntos].astype('int64').tolist(),
            inicio[juntos].tolist(),
            duracao[juntos].tolist(),
        ),
        key=lambda x: x[1],
    )
    artistas, musicas = a.nome_artista.tolist(), a.nome_musica.tolist()
    deslocamentos = a.deslocamento.tolist()
    momentos = [
        MomentoJuntos(
            artistas[p],
            musicas[p],
            pd.Timestamp(inicio, tz='UTC'),
            pd.Timestamp(inicio + deslocamentos[p]),
            duracao / 60_000_000_000,
        )
        for p, inicio, duracao in achados
    ]
    if not momentos:
        return Sintonia([], 0.0, [], pd.Series(dtype=float), None, None, quase)
    tabela = pd.DataFrame(
        {
            'musica': [m.musica for m in momentos],
            'artista': [m.artista for m in momentos],
            'minutos': [m.minutos for m in momentos],
            'mes': [m.inicio_local.strftime('%Y-%m') for m in momentos],
            'hora': [m.inicio_local.hour for m in momentos],
            'dia': [m.inicio_local.dayofweek for m in momentos],
        }
    )
    top = (
        tabela.groupby(['musica', 'artista'], observed=True)
        .agg(vezes=('minutos', 'size'), minutos=('minutos', 'sum'))
        .reset_index()
        .sort_values(['minutos', 'musica'], ascending=[False, True], kind='stable')
        .head(5)
    )
    por_hora = tabela.groupby('hora', observed=True).minutos.sum()
    por_dia = tabela.groupby('dia', observed=True).minutos.sum()
    return Sintonia(
        momentos=momentos,
        minutos=float(tabela.minutos.sum()),
        top_musicas=[(m, art, int(v), float(mi)) for m, art, v, mi in top.itertuples(index=False)],
        por_mes=tabela.groupby('mes', observed=True).minutos.sum().sort_index(),
        hora_favorita=int(por_hora.idxmax()),
        dia_favorito=DIAS_SEMANA[int(por_dia.idxmax())],
        quase_juntos=quase,
    )


def sintonia(a: pd.DataFrame, b: pd.DataFrame) -> Sintonia:
    """Momentos em que A e B tocavam a mesma faixa ao mesmo tempo (históricos completos).

    O Spotify registra o fim de cada reprodução (``ts``) e quanto tocou
    (``ms_played``); o início é ``fim − duração``.
    """
    return sintonia_entre(escutas(a), escutas(b))


def sintonia_do_par(sintonias: dict[tuple[str, str], Sintonia], x: str, y: str) -> Sintonia | None:
    """Sintonia de um par do Match, em qualquer ordem; ``None`` se faltou histórico de escuta."""
    return sintonias.get((x, y)) or sintonias.get((y, x))


def mais_sincronizada(
    sintonias: dict[tuple[str, str], Sintonia],
) -> tuple[str, str, Sintonia] | None:
    """O par com mais minutos ouvindo junto; ``None`` se ninguém chegou a ouvir junto."""
    melhor = max(sintonias.items(), key=lambda par: par[1].minutos, default=None)
    if melhor is None or melhor[1].minutos <= 0:
        return None
    (x, y), s = melhor
    return x, y, s


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
