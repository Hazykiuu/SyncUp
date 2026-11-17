"""Orquestra a comparação sem importar interface, HTML ou bibliotecas gráficas."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Literal

import pandas as pd

from configuracao import ConfiguracaoCarga
from dados import Caminho, Historico, carregar_historicos, precarregar
from metricas import (
    contribuicoes_cosseno,
    cosseno,
    entropia_normalizada,
    gini,
    jaccard_ponderado,
    metricas,
    ponderar_contagens,
    rbo,
)
from perfis import (
    HORA_FIM_MADRUGADA,
    HORA_INICIO_MADRUGADA,
    QUANTIDADE_FAIXAS_REPEAT,
    QUANTIDADE_FAVORITOS,
    ArquetiposMusicais,
    classificar_proporcoes,
)
from recursos import (
    MomentosSincronizados,
    Sintonia,
    momentos_sincronizados,
    playlist_comum,
    ponte_musical,
    sintonia,
)

TEMPO_MINIMO_PLAY_MS = 30_000
QUANTIDADE_TOP_ARTISTAS = 20
QUANTIDADE_TOP_MUSICAS = 20
# "Favoritos em comum": RBO nos 50 artistas mais ouvidos (estudo com 12 históricos).
PROFUNDIDADE_RBO = 50
# Opção "mais peso ao que vocês ouvem agora": uma escuta de 1 ano atrás vale metade.
MEIA_VIDA_DIAS = 365
QUANTIDADE_ARTISTAS_GRAFICO = 12
StatusArquivos = Literal[
    'bytes_identicos', 'historicos_identicos', 'recorte_identico', 'diferentes'
]


def contagens_recentes(plays: pd.DataFrame, referencia: pd.Timestamp) -> pd.Series:
    """Plays por artista, cada um valendo 0,5^(idade/meia-vida), com a idade contada da referência."""
    idade = (referencia - plays.data_utc).dt.total_seconds() / 86_400  # em dias
    pesos = 0.5 ** (idade / MEIA_VIDA_DIAS)
    serie = pesos.groupby(plays.artista, observed=True, sort=True).sum()
    serie.index = pd.Index(serie.index.astype(object), name='artista')
    return serie


def ranking_artistas(contagens: pd.Series, n: int = PROFUNDIDADE_RBO) -> list[str]:
    """Os `n` artistas mais ouvidos; empate pelo nome (ordem de ponto de código), igual ao dupla.js."""
    return [k for k, _ in sorted(contagens.items(), key=lambda kv: (-kv[1], kv[0]))][:n]


@dataclass(frozen=True)
class MetricasComparacao:
    """Similaridades entre zero e um; Ruzicka usa pesos absolutos selecionados."""

    cosseno: float
    jaccard: float
    rbo_top50: float
    jaccard_ponderado: float


@dataclass(frozen=True)
class PeriodoComparacao:
    """Recorte aplicado; históricos completos não possuem limites conjuntos."""

    comum: bool
    inicio: pd.Timestamp | None
    fim: pd.Timestamp | None
    fuso_horario: str = 'America/Sao_Paulo'
    inicio_utc: pd.Timestamp | None = None
    fim_utc: pd.Timestamp | None = None


@dataclass(frozen=True)
class PerfilComparado:
    """Resumo, rankings e arquétipos de uma pessoa no recorte selecionado."""

    nome: str
    plays: int
    horas: float
    quantidade_artistas: int
    artistas: pd.DataFrame
    musicas: pd.DataFrame
    arquetipos: ArquetiposMusicais
    mensal: pd.DataFrame
    entropia: float | None = None
    gini: float | None = None
    horarios: pd.DataFrame = field(default_factory=pd.DataFrame)
    contagens_artistas: dict[str, int] = field(default_factory=dict)
    artistas_por_mes: pd.DataFrame = field(default_factory=pd.DataFrame)


@dataclass(frozen=True)
class ResultadoComparacao:
    """Resultado nomeado; não contém HTML, figuras ou tuplas posicionais de saídas."""

    metricas: MetricasComparacao
    periodo: PeriodoComparacao
    perfil_a: PerfilComparado
    perfil_b: PerfilComparado
    participacao_artistas: pd.DataFrame
    ordem_artistas: list[str]
    artistas_comuns: list[str]
    exclusivos_a: list[str]
    exclusivos_b: list[str]
    estatisticas: pd.DataFrame
    diagnostico: pd.DataFrame
    status_arquivos: StatusArquivos
    aviso: str
    deduplicacao_ativa: bool
    duplicados_removidos_a: int
    duplicados_removidos_b: int
    ponderacao: str = 'bruta'
    recente: bool = False  # cosseno, Ruzicka e RBO com mais peso no que se ouve agora
    contribuicoes: pd.DataFrame = field(default_factory=pd.DataFrame)
    momentos_artistas: MomentosSincronizados | None = None
    momentos_musicas: MomentosSincronizados | None = None
    sintonia: Sintonia | None = None  # mesma faixa tocando ao mesmo tempo (v0.9)
    ponte: pd.DataFrame = field(default_factory=pd.DataFrame)
    playlist: pd.DataFrame = field(default_factory=pd.DataFrame)


def _lista(arquivos: Caminho | list[Caminho]) -> list[Caminho]:
    """Normaliza um caminho único ou uma lista de partes."""
    return [arquivos] if isinstance(arquivos, (str, Path)) else list(arquivos)


def _historicos_iguais(a: pd.DataFrame, b: pd.DataFrame) -> bool:
    """Compara eventos por instante, duração e nomes, ignorando níveis não observados."""
    if len(a) != len(b):
        return False
    colunas = ['data_utc', 'ms_played', 'musica', 'artista']
    aa, bb = a[colunas].reset_index(drop=True), b[colunas].reset_index(drop=True)
    for coluna in ('musica', 'artista'):
        aa[coluna] = aa[coluna].astype(object)
        bb[coluna] = bb[coluna].astype(object)
    return aa.equals(bb)


def _tabela(series: pd.Series, coluna: str) -> pd.DataFrame:
    """Ordena artistas por contagem decrescente e nome crescente nos empates."""
    tabela = series.rename('Reproduções').reset_index()
    tabela.columns = [coluna, 'Reproduções']
    tabela[coluna] = tabela[coluna].astype(object)
    return (
        tabela.sort_values(['Reproduções', coluna], ascending=[False, True], kind='stable')
        .head(QUANTIDADE_TOP_ARTISTAS)
        .reset_index(drop=True)
    )


def _perfil(
    dados: pd.DataFrame, plays: pd.DataFrame, artistas: pd.Series, faixas: pd.Series, nome: str
) -> PerfilComparado:
    """Calcula um perfil usando contagens compartilhadas pelos rankings e regras."""
    horas = plays.hora
    madrugada = int(horas.between(HORA_INICIO_MADRUGADA, HORA_FIM_MADRUGADA - 1).sum())
    # O top de contagens não precisa de nomes; RangeIndex evita buscas no MultiIndex.
    arquetipos = classificar_proporcoes(
        float(artistas.nlargest(QUANTIDADE_FAVORITOS).sum()) / len(plays),
        float(faixas.reset_index(drop=True).nlargest(QUANTIDADE_FAIXAS_REPEAT).sum()) / len(plays),
        madrugada / len(plays),
    )
    mensal = (
        dados.groupby('ano_mes', observed=True)
        .minutos.sum()
        .div(60)
        .rename('Horas')
        .rename_axis('Mês')
        .reset_index()
    )
    mensal['Mês'] = mensal['Mês'].map(lambda valor: f'{valor // 100:04d}-{valor % 100:02d}')
    musicas = faixas.rename('Reproduções').reset_index()
    musicas[['musica', 'artista']] = musicas[['musica', 'artista']].astype(object)
    musicas = (
        musicas.sort_values(
            ['Reproduções', 'musica', 'artista'], ascending=[False, True, True], kind='stable'
        )
        .head(QUANTIDADE_TOP_MUSICAS)
        .reset_index(drop=True)
    )
    return PerfilComparado(
        nome=nome,
        plays=len(plays),
        horas=float(dados.minutos.sum() / 60),
        quantidade_artistas=len(artistas),
        artistas=_tabela(artistas, 'Artista'),
        musicas=musicas,
        arquetipos=arquetipos,
        mensal=mensal,
        entropia=entropia_normalizada(artistas),
        gini=gini(artistas),
        horarios=plays.groupby(['dia_semana', 'hora'], observed=True)
        .size()
        .rename('Reproduções')
        .reset_index(),
        contagens_artistas={str(k): int(v) for k, v in artistas.items()},
        artistas_por_mes=plays.groupby(['ano_mes', 'artista'], observed=True)
        .size()
        .rename('Reproduções')
        .reset_index(),
    )


def _diagnostico(historicos: list[Historico], nomes: list[str]) -> pd.DataFrame:
    """Expõe somente identificação e cobertura dos históricos recebidos."""
    registros = []
    for h, nome in zip(historicos, nomes):
        c = h.contadores
        registros.append(
            {
                'Perfil': nome,
                'Arquivo': h.arquivo,
                'SHA-256 do arquivo': h.sha256,
                'Registros recebidos': c.recebidos,
                'Podcasts descartados': c.podcasts,
                'Duração inválida': c.ms_invalidos,
                'Data inválida': c.datas_invalidas,
                'Identificação inválida': c.metadados_invalidos,
                'Various Artists encontrados': c.various_artists_encontrados,
                'Various Artists descartados': c.various_artists_descartados,
                'Ignorados pelos filtros': c.ignorados,
                'Duplicados removidos': c.duplicados,
                'Registros de músicas antes do recorte': c.validos,
                # Posições (argmin/argmax) funcionam mesmo com índices repetidos.
                'Início do histórico': str(h.dados['data'].iloc[h.dados.data_utc.argmin()]),
                'Fim do histórico': str(h.dados['data'].iloc[h.dados.data_utc.argmax()]),
                'Fuso horário': h.fuso_horario,
                'Origem dos dados': h.origem_cache,
            }
        )
    return pd.DataFrame(registros)


def comparar(
    arquivo_a: Caminho | list[Caminho],
    arquivo_b: Caminho | list[Caminho],
    nome_a: str,
    nome_b: str,
    periodo_comum: bool = True,
    *,
    deduplicar: bool | None = None,
    configuracao: ConfiguracaoCarga | None = None,
    ponderacao: str = 'bruta',
    recente: bool = False,
) -> ResultadoComparacao:
    """Compara dois arquivos, preservando os cinco argumentos da API anterior.

    Rankings usam plays de pelo menos 30 segundos. Horas e describe() usam
    todas as execuções válidas. Deduplicação é opcional e desativada por padrão.
    A mudança intencional de contrato na v0.5 é o retorno estruturado.
    """
    if not arquivo_a or not arquivo_b:
        raise ValueError('Selecione um arquivo de histórico para cada pessoa.')
    config = configuracao or ConfiguracaoCarga()
    if deduplicar is not None:
        config = replace(config, deduplicar=deduplicar)
    ponderar_contagens({}, ponderacao)  # Valida antes de ler arquivos grandes.
    nome_a = (nome_a or '').strip() or 'Pessoa A'
    nome_b = (nome_b or '').strip() or 'Pessoa B'
    precarregar([*_lista(arquivo_a), *_lista(arquivo_b)], config)
    ha = carregar_historicos(arquivo_a, configuracao=config)
    hb = carregar_historicos(arquivo_b, configuracao=config)
    a, b = ha.dados, hb.dados
    if a.empty or b.empty:
        raise ValueError('Um dos históricos não contém registros de músicas válidos.')
    historicos_iguais = _historicos_iguais(a, b)
    diagnostico = _diagnostico([ha, hb], [nome_a, nome_b])
    inicio, fim, inicio_utc, fim_utc = None, None, None, None
    if periodo_comum:
        inicio_utc = max(a.data_utc.min(), b.data_utc.min())
        fim_utc = min(a.data_utc.max(), b.data_utc.max())
        if inicio_utc > fim_utc:
            raise ValueError(
                'Os históricos não possuem período de cobertura em comum. Desmarque a opção para comparar períodos diferentes.'
            )
        # Obtém limites locais já calculados, sem reconverter a coluna de datas.
        inicio = (
            a.loc[a.data_utc.eq(inicio_utc), 'data'].iloc[0]
            if a.data_utc.eq(inicio_utc).any()
            else b.loc[b.data_utc.eq(inicio_utc), 'data'].iloc[0]
        )
        fim = (
            a.loc[a.data_utc.eq(fim_utc), 'data'].iloc[0]
            if a.data_utc.eq(fim_utc).any()
            else b.loc[b.data_utc.eq(fim_utc), 'data'].iloc[0]
        )
        a, b = (
            a[a.data_utc.between(inicio_utc, fim_utc)],
            b[b.data_utc.between(inicio_utc, fim_utc)],
        )
    va, vb = a[a.ms_played >= TEMPO_MINIMO_PLAY_MS], b[b.ms_played >= TEMPO_MINIMO_PLAY_MS]
    if va.empty or vb.empty:
        raise ValueError(
            'Não há reproduções de pelo menos 30 segundos para os dois perfis nesse período.'
        )
    ra, rb = (
        va.groupby('artista', observed=True, sort=True).size(),
        vb.groupby('artista', observed=True, sort=True).size(),
    )
    ra.index = pd.Index(ra.index.astype(object), name='artista')
    rb.index = pd.Index(rb.index.astype(object), name='artista')
    fa = va.groupby(['musica', 'artista'], observed=True, sort=True).size()
    fb = vb.groupby(['musica', 'artista'], observed=True, sort=True).size()
    # Com "recente", o cosseno, o Ruzicka e o RBO usam plays com peso pelo tempo; o resto segue por contagem.
    # A idade conta do fim do recorte comum (igual para os dois) ou, sem ele, do último play de cada um.
    if recente:
        qa = contagens_recentes(va, fim_utc if periodo_comum else va.data_utc.max())
        qb = contagens_recentes(vb, fim_utc if periodo_comum else vb.data_utc.max())
    else:
        qa, qb = ra, rb
    pesos_a, pesos_b = ponderar_contagens(qa, ponderacao), ponderar_contagens(qb, ponderacao)
    cosine, jac = metricas(pesos_a, pesos_b)
    top = rbo(ranking_artistas(qa), ranking_artistas(qb), k=PROFUNDIDADE_RBO)
    ponderado = jaccard_ponderado(pesos_a, pesos_b)
    # Há plays nos dois perfis: todas as quatro métricas possuem denominadores positivos.
    if cosine is None or jac is None or top is None or ponderado is None:
        raise ValueError('Não há dados suficientes para calcular as similaridades.')
    total_a, total_b = len(va), len(vb)
    todos = ra.index.union(rb.index)
    pesos = ra.reindex(todos, fill_value=0) / total_a + rb.reindex(todos, fill_value=0) / total_b
    # Maior participação somada; empate pelo nome (o nlargest do pandas não garante a ordem dos empates,
    # e o app do navegador precisa da mesma ordem: dupla.js).
    selecionados = pd.Index(
        [k for k, _ in sorted(pesos.items(), key=lambda kv: (-kv[1], kv[0]))][
            :QUANTIDADE_ARTISTAS_GRAFICO
        ],
        dtype=object,
    )
    grafico = pd.DataFrame(
        {
            'Artista': selecionados,
            f'A · {nome_a}': ra.reindex(selecionados, fill_value=0) / total_a * 100,
            f'B · {nome_b}': rb.reindex(selecionados, fill_value=0) / total_b * 100,
        }
    ).melt(id_vars='Artista', var_name='Perfil', value_name='Participação (%)')
    if ha.sha256 == hb.sha256:
        status: StatusArquivos = 'bytes_identicos'
        aviso = 'Os arquivos recebidos possuem bytes idênticos (SHA-256 igual). Confira os arquivos selecionados na aba Diagnóstico.'
    elif historicos_iguais:
        status = 'historicos_identicos'
        aviso = 'Os ZIPs são diferentes, mas os registros de músicas após a limpeza são idênticos. Isso não identifica o dono dos arquivos.'
    elif _historicos_iguais(a, b):
        status = 'recorte_identico'
        aviso = 'Os históricos completos são diferentes; apenas os registros no período selecionado coincidem.'
    else:
        status = 'diferentes'
        aviso = 'Os históricos recebidos possuem registros diferentes.'
    comuns = (
        pesos.loc[ra.index.intersection(rb.index).sort_values()]
        .sort_values(ascending=False, kind='stable')
        .index.tolist()
    )
    ordem_a = ra.sort_index().sort_values(ascending=False, kind='stable').index
    ordem_b = rb.sort_index().sort_values(ascending=False, kind='stable').index
    estatisticas = pd.concat(
        {f'A · {nome_a}': a[['minutos']].describe(), f'B · {nome_b}': b[['minutos']].describe()},
        axis=1,
    )
    estatisticas.columns = ['Minutos por execução · A', 'Minutos por execução · B']
    perfil_a, perfil_b = _perfil(a, va, ra, fa, nome_a), _perfil(b, vb, rb, fb, nome_b)
    # Solta as cópias do período comum antes das etapas mais pesadas (sincronia e sintonia):
    # só va/vb seguem; derruba o pico de memória, que importa no navegador.
    del a, b
    return ResultadoComparacao(
        metricas=MetricasComparacao(cosine, jac, top, ponderado),
        periodo=PeriodoComparacao(
            periodo_comum, inicio, fim, config.fuso_horario, inicio_utc, fim_utc
        ),
        perfil_a=perfil_a,
        perfil_b=perfil_b,
        participacao_artistas=grafico,
        ordem_artistas=list(selecionados),
        artistas_comuns=comuns,
        exclusivos_a=ordem_a[~ordem_a.isin(rb.index)].tolist(),
        exclusivos_b=ordem_b[~ordem_b.isin(ra.index)].tolist(),
        estatisticas=estatisticas.reset_index(names='Medida'),
        diagnostico=diagnostico,
        status_arquivos=status,
        aviso=aviso,
        deduplicacao_ativa=config.deduplicar,
        duplicados_removidos_a=ha.duplicados_removidos,
        duplicados_removidos_b=hb.duplicados_removidos,
        ponderacao=ponderacao,
        recente=recente,
        contribuicoes=_ordenar_contribuicoes(contribuicoes_cosseno(pesos_a, pesos_b)),
        momentos_artistas=momentos_sincronizados(va, vb, 'artista'),
        momentos_musicas=momentos_sincronizados(va, vb, 'musica'),
        sintonia=sintonia(va, vb),
        ponte=ponte_musical(ra, rb, nome_a, nome_b),
        playlist=playlist_comum(fa, fb),
    )


def _ordenar_contribuicoes(contribuicoes: dict[str, float]) -> pd.DataFrame:
    """Maior contribuição primeiro; empate pelo nome do artista.

    Ordena pelo valor arredondado a 15 casas: contribuições iguais na matemática podem diferir no
    último bit (a raiz da norma), e o empate precisa dar a mesma ordem aqui e no app web (dupla.js).
    """
    tabela = pd.DataFrame(contribuicoes.items(), columns=['Artista', 'Contribuição ao cosseno'])
    tabela['_ordem'] = tabela['Contribuição ao cosseno'].round(15)
    return (
        tabela.sort_values(['_ordem', 'Artista'], ascending=[False, True], kind='stable')
        .drop(columns='_ordem')
        .reset_index(drop=True)
    )


MINIMO_PERFIS_GRUPO = 3
MAXIMO_PERFIS_GRUPO = 6


@dataclass(frozen=True)
class EntradaPerfil:
    """Nome e uma ou várias partes de um único histórico pessoal."""

    nome: str
    arquivos: Caminho | list[Caminho]


@dataclass(frozen=True)
class ResultadoGrupo:
    """Perfis e matriz de cosseno no mesmo recorte global, quando solicitado."""

    perfis: list[PerfilComparado]
    matriz: pd.DataFrame
    periodo: PeriodoComparacao
    ponderacao: str
    diagnostico: pd.DataFrame


def comparar_grupo(
    entradas: list[EntradaPerfil],
    periodo_comum: bool = True,
    *,
    configuracao: ConfiguracaoCarga | None = None,
    ponderacao: str = 'bruta',
) -> ResultadoGrupo:
    """Calcula perfis uma vez e compara vetores entre três e seis pessoas.

    No modo comum, toda a matriz usa a interseção UTC global dos históricos,
    evitando comparar cada célula em uma janela diferente. Os nomes devem
    ser distintos para identificar linhas. Não calcula afinidade pessoal.
    """
    if not MINIMO_PERFIS_GRUPO <= len(entradas) <= MAXIMO_PERFIS_GRUPO:
        raise ValueError('O Modo Grupo exige de 3 a 6 perfis.')
    nomes = [(e.nome or '').strip() or f'Pessoa {i + 1}' for i, e in enumerate(entradas)]
    if len(set(nomes)) != len(nomes):
        raise ValueError('Use nomes diferentes para identificar os perfis do grupo.')
    config = configuracao or ConfiguracaoCarga()
    ponderar_contagens({}, ponderacao)
    precarregar([arquivo for e in entradas for arquivo in _lista(e.arquivos)], config)
    historicos = [carregar_historicos(e.arquivos, configuracao=config) for e in entradas]
    if any(h.dados.empty for h in historicos):
        raise ValueError('Um dos perfis não contém músicas válidas após os filtros.')
    inicio_utc = max(h.dados.data_utc.min() for h in historicos) if periodo_comum else None
    fim_utc = min(h.dados.data_utc.max() for h in historicos) if periodo_comum else None
    if periodo_comum and inicio_utc > fim_utc:
        raise ValueError('Não há período comum a todo o grupo. Desmarque o recorte comum.')
    inicio = fim = None
    if periodo_comum:
        # Os limites já existem na coluna local de pelo menos um perfil.
        inicio = next(
            h.dados.loc[h.dados.data_utc.eq(inicio_utc), 'data'].iloc[0]
            for h in historicos
            if h.dados.data_utc.eq(inicio_utc).any()
        )
        fim = next(
            h.dados.loc[h.dados.data_utc.eq(fim_utc), 'data'].iloc[0]
            for h in historicos
            if h.dados.data_utc.eq(fim_utc).any()
        )
    perfis, vetores = [], []
    for nome, h in zip(nomes, historicos):
        dados = h.dados
        if periodo_comum:
            dados = dados[dados.data_utc.between(inicio_utc, fim_utc)]
        plays = dados[dados.ms_played >= TEMPO_MINIMO_PLAY_MS]
        if plays.empty:
            raise ValueError(f'Não há plays ≥30s para {nome} no período escolhido.')
        artistas = plays.groupby('artista', observed=True, sort=True).size()
        artistas.index = pd.Index(artistas.index.astype(object), name='artista')
        faixas = plays.groupby(['musica', 'artista'], observed=True, sort=True).size()
        perfis.append(_perfil(dados, plays, artistas, faixas, nome))
        vetores.append(ponderar_contagens(artistas, ponderacao))
    matriz = [[1.0 if i == j else 0.0 for j in range(len(entradas))] for i in range(len(entradas))]
    for i in range(len(entradas)):
        for j in range(i + 1, len(entradas)):
            valor = cosseno(vetores[i], vetores[j])
            if valor is None:
                raise ValueError('Não há dados suficientes para a matriz de similaridade.')
            matriz[i][j] = matriz[j][i] = valor
    return ResultadoGrupo(
        perfis,
        pd.DataFrame(matriz, index=nomes, columns=nomes),
        PeriodoComparacao(periodo_comum, inicio, fim, config.fuso_horario, inicio_utc, fim_utc),
        ponderacao,
        _diagnostico(historicos, nomes),
    )
