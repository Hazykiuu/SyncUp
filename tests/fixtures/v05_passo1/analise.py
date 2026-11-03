"""Orquestra a comparação sem importar interface, HTML ou bibliotecas gráficas."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import pandas as pd

from dados import Caminho, Historico, carregar_historico
from metricas import metricas, jaccard, jaccard_ponderado
from perfis import (ArquetiposMusicais, classificar_arquetipos,
                    HORA_INICIO_MADRUGADA, HORA_FIM_MADRUGADA)

TEMPO_MINIMO_PLAY_MS = 30_000
QUANTIDADE_TOP_ARTISTAS = 20
QUANTIDADE_TOP_MUSICAS = 20
QUANTIDADE_ARTISTAS_GRAFICO = 12
StatusArquivos = Literal['bytes_identicos', 'historicos_identicos', 'recorte_identico', 'diferentes']


@dataclass(frozen=True)
class MetricasComparacao:
    """Similaridades entre zero e um; ponderado usa contagens absolutas."""
    cosseno: float
    jaccard: float
    jaccard_top20: float
    jaccard_ponderado: float


@dataclass(frozen=True)
class PeriodoComparacao:
    """Recorte aplicado; históricos completos não possuem limites conjuntos."""
    comum: bool
    inicio: pd.Timestamp | None
    fim: pd.Timestamp | None


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


def _tabela(series: pd.Series, coluna: str) -> pd.DataFrame:
    """Constrói o ranking de artistas com o ordenamento mantido da v0.4."""
    tabela = series.sort_values(ascending=False).head(QUANTIDADE_TOP_ARTISTAS).rename('Reproduções').reset_index()
    tabela.columns = [coluna, 'Reproduções']
    return tabela


def _perfil(dados: pd.DataFrame, plays: pd.DataFrame, artistas: pd.Series,
            faixas: pd.Series, nome: str) -> PerfilComparado:
    """Calcula um perfil usando contagens compartilhadas pelos rankings e regras."""
    horas = plays.data.dt.hour
    madrugada = int(horas.between(HORA_INICIO_MADRUGADA, HORA_FIM_MADRUGADA - 1).sum())
    arquetipos = classificar_arquetipos(artistas.to_dict(), faixas.to_dict(), len(plays), madrugada)
    mes = dados.data.dt.year * 100 + dados.data.dt.month
    mensal = dados.groupby(mes).minutos.sum().div(60).rename('Horas').rename_axis('Mês').reset_index()
    mensal['Mês'] = mensal['Mês'].map(lambda valor: f'{valor//100:04d}-{valor%100:02d}')
    return PerfilComparado(
        nome=nome, plays=len(plays), horas=float(dados.minutos.sum() / 60),
        quantidade_artistas=len(artistas), artistas=_tabela(artistas, 'Artista'),
        musicas=faixas.sort_values(ascending=False).head(QUANTIDADE_TOP_MUSICAS).rename('Reproduções').reset_index(),
        arquetipos=arquetipos, mensal=mensal,
    )


def _diagnostico(a: Historico, b: Historico, nomes: tuple[str, str]) -> pd.DataFrame:
    """Expõe somente identificação e cobertura dos dois históricos recebidos."""
    return pd.DataFrame({
        'Perfil': list(nomes), 'Arquivo': [a.arquivo, b.arquivo],
        'SHA-256 do arquivo': [a.sha256, b.sha256],
        'Registros de músicas antes do recorte': [len(a.dados), len(b.dados)],
        'Início do histórico': [str(a.dados.data.min()), str(b.dados.data.min())],
        'Fim do histórico': [str(a.dados.data.max()), str(b.dados.data.max())],
    })


def comparar(arquivo_a: Caminho, arquivo_b: Caminho, nome_a: str, nome_b: str,
             periodo_comum: bool = True, *, deduplicar: bool = False) -> ResultadoComparacao:
    """Compara dois arquivos, preservando os cinco argumentos da API anterior.

    Rankings usam plays de pelo menos 30 segundos. Horas e describe() usam
    todas as execuções válidas. Deduplicação é opcional e desativada por padrão.
    A mudança intencional de contrato na v0.5 é o retorno estruturado.
    """
    if not arquivo_a or not arquivo_b:
        raise ValueError('Selecione um arquivo de histórico para cada pessoa.')
    ha = carregar_historico(arquivo_a, deduplicar=deduplicar)
    hb = carregar_historico(arquivo_b, deduplicar=deduplicar)
    a, b = ha.dados, hb.dados
    if a.empty or b.empty:
        raise ValueError('Um dos históricos não contém registros de músicas válidos.')
    historicos_iguais = a.reset_index(drop=True).equals(b.reset_index(drop=True))
    diagnostico = _diagnostico(ha, hb, (nome_a, nome_b))
    inicio, fim = None, None
    if periodo_comum:
        inicio, fim = max(a.data.min(), b.data.min()), min(a.data.max(), b.data.max())
        if inicio > fim:
            raise ValueError('Os históricos não possuem período de cobertura em comum. Desmarque a opção para comparar períodos diferentes.')
        a, b = a[a.data.between(inicio, fim)], b[b.data.between(inicio, fim)]
    va, vb = a[a.ms_played >= TEMPO_MINIMO_PLAY_MS], b[b.ms_played >= TEMPO_MINIMO_PLAY_MS]
    if va.empty or vb.empty:
        raise ValueError('Não há reproduções de pelo menos 30 segundos para os dois perfis nesse período.')
    ra, rb = va.groupby('artista').size(), vb.groupby('artista').size()
    fa = va.groupby(['musica', 'artista']).size()
    fb = vb.groupby(['musica', 'artista']).size()
    cosine, jac = metricas(ra, rb)
    top = jaccard(ra.nlargest(QUANTIDADE_TOP_ARTISTAS).index, rb.nlargest(QUANTIDADE_TOP_ARTISTAS).index)
    ponderado = jaccard_ponderado(ra, rb)
    # Há plays nos dois perfis: todas as quatro métricas possuem denominadores positivos.
    if cosine is None or jac is None or top is None or ponderado is None:
        raise ValueError('Não há dados suficientes para calcular as similaridades.')
    nome_a, nome_b = nome_a.strip() or 'Pessoa A', nome_b.strip() or 'Pessoa B'
    todos = ra.index.union(rb.index)
    pesos = ra.reindex(todos, fill_value=0) / ra.sum() + rb.reindex(todos, fill_value=0) / rb.sum()
    selecionados = pesos.nlargest(QUANTIDADE_ARTISTAS_GRAFICO).index
    grafico = pd.DataFrame({
        'Artista': selecionados,
        f'A · {nome_a}': ra.reindex(selecionados, fill_value=0) / ra.sum() * 100,
        f'B · {nome_b}': rb.reindex(selecionados, fill_value=0) / rb.sum() * 100,
    }).melt(id_vars='Artista', var_name='Perfil', value_name='Participação (%)')
    if ha.sha256 == hb.sha256:
        status: StatusArquivos = 'bytes_identicos'
        aviso = 'Os arquivos recebidos possuem bytes idênticos (SHA-256 igual). Confira os arquivos selecionados na aba Diagnóstico.'
    elif historicos_iguais:
        status = 'historicos_identicos'
        aviso = 'Os ZIPs são diferentes, mas os registros de músicas após a limpeza são idênticos. Isso não identifica o dono dos arquivos.'
    elif a.reset_index(drop=True).equals(b.reset_index(drop=True)):
        status = 'recorte_identico'
        aviso = 'Os históricos completos são diferentes; apenas os registros no período selecionado coincidem.'
    else:
        status = 'diferentes'
        aviso = 'Os históricos recebidos possuem registros diferentes.'
    comuns = sorted(set(ra.index) & set(rb.index), key=lambda x: (-(ra[x] / len(va) + rb[x] / len(vb)), x))
    estatisticas = pd.concat({f'A · {nome_a}': a[['minutos']].describe(), f'B · {nome_b}': b[['minutos']].describe()}, axis=1)
    estatisticas.columns = ['Minutos por execução · A', 'Minutos por execução · B']
    return ResultadoComparacao(
        metricas=MetricasComparacao(cosine, jac, top, ponderado),
        periodo=PeriodoComparacao(periodo_comum, inicio, fim),
        perfil_a=_perfil(a, va, ra, fa, nome_a), perfil_b=_perfil(b, vb, rb, fb, nome_b),
        participacao_artistas=grafico, ordem_artistas=list(selecionados), artistas_comuns=comuns,
        exclusivos_a=[x for x in ra.sort_values(ascending=False).index if x not in rb.index],
        exclusivos_b=[x for x in rb.sort_values(ascending=False).index if x not in ra.index],
        estatisticas=estatisticas.reset_index(names='Medida'), diagnostico=diagnostico,
        status_arquivos=status, aviso=aviso, deduplicacao_ativa=deduplicar,
        duplicados_removidos_a=ha.duplicados_removidos, duplicados_removidos_b=hb.duplicados_removidos,
    )
