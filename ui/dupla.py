"""Dupla e Grupo: execução, apresentação, gráficos e downloads."""

from __future__ import annotations

from functools import lru_cache
from numbers import Real
from pathlib import Path
from tempfile import gettempdir
from typing import Any

import gradio as gr
import pandas as pd
import plotly.express as px
from plotly.graph_objects import Figure

import componentes
import stories
from analise import (
    EntradaPerfil,
    PerfilComparado,
    ResultadoComparacao,
    comparar,
    comparar_grupo,
)
from cartao import gerar_cartao, gerar_cartao_sintonia
from configuracao import ConfiguracaoCarga
from exportacoes import exportar_playlist
from formatacao import escape_html, escape_markdown, fmt_horas, fmt_num, fmt_pct, listar_markdown
from graficos import (
    butterfly,
    evolucao_mensal,
    mapa_horarios,
    matriz_grupo,
    radar_tracos,
    slope_chart,
)
from perfis import AVISO_TRACOS
from ui.comum import (
    TEXTO_LIMIARES,
    _configuracao,
    _em_pasta_temporaria,
    _linhas,
    falha,
)
from wrapped import Wrapped, wrapped_de_arquivos


def texto_periodo(resultado: ResultadoComparacao) -> str:
    """Apresenta o recorte sem extrair informações de texto ou HTML."""
    periodo = resultado.periodo
    if periodo.comum:
        return f'{periodo.inicio:%d/%m/%Y} a {periodo.fim:%d/%m/%Y} (fuso {periodo.fuso_horario})'
    return f'Históricos completos, com coberturas potencialmente diferentes. Fuso: {periodo.fuso_horario}.'


def perfil_card(perfil: PerfilComparado, cor: str, wrapped: Wrapped | None = None) -> str:
    """Cartão de identidade musical (estilo Wrapped) com traços animados.

    Com ``wrapped``, destaca o arquétipo da vida toda no topo do cartão.
    """
    destaque = stories.arquetipo_html(wrapped) if wrapped is not None else ''
    return componentes.perfil_card(perfil, cor, TEXTO_LIMIARES, destaque)


def _wrapped_seguro(
    arquivos: list[str] | str | None, nome: str, config: ConfiguracaoCarga
) -> Wrapped | None:
    """Wrapped da vida toda sem interromper a comparação se algo faltar."""
    if not arquivos:
        return None
    try:
        return wrapped_de_arquivos(arquivos, nome, config)
    except ValueError:
        return None


def wrapped_dupla_html(wa: Wrapped | None, wb: Wrapped | None) -> str:
    """Dois players de stories lado a lado (histórico completo de cada pessoa)."""
    blocos = [stories.stories_html(w) for w in (wa, wb) if w is not None]
    if not blocos:
        return '<p class="su-note">Não foi possível montar o Wrapped destes históricos.</p>'
    return (
        '<p class="su-note">Wrapped da vida toda: usa o histórico completo de cada pessoa, '
        'não só o período comparado. Clique à direita para avançar, à esquerda para voltar.</p>'
        f'<div class="su-wrapped-row">{"".join(blocos)}</div>'
    )


def resumo_html(resultado: ResultadoComparacao) -> str:
    """Resumo estilo Blend: anel de similaridade, avatares e métricas com contagem animada."""
    return componentes.blend_html(resultado, texto_periodo(resultado))


def resumo_markdown(resultado: ResultadoComparacao) -> str:
    """Mantém a apresentação textual da v0.4 para o benchmark e a regressão."""
    m, a, b = resultado.metricas, resultado.perfil_a, resultado.perfil_b
    texto = f"""## Similaridade musical: {fmt_pct(m.cosseno)}
**Cosseno:** compara o padrão de frequência por artista. **Jaccard geral:** {fmt_pct(m.jaccard)}. **Jaccard do Top 20:** {fmt_pct(m.jaccard_top20)}.

Período: {escape_markdown(texto_periodo(resultado))}

| Perfil | Plays ≥30s | Horas ouvidas (todas as execuções) | Artistas com plays ≥30s |
|---|---:|---:|---:|
| {escape_markdown(a.nome)} | {fmt_num(a.plays)} | {fmt_num(a.horas, 1)} | {fmt_num(a.quantidade_artistas)} |
| {escape_markdown(b.nome)} | {fmt_num(b.plays)} | {fmt_num(b.horas, 1)} | {fmt_num(b.quantidade_artistas)} |

O percentual mede semelhança dos dados musicais. Valores ausentes de escuta são tratados como zero; ausência no arquivo não prova que a pessoa não gosta do artista.
"""
    return texto + f'\n\n**{escape_markdown(resultado.aviso)}**'


def texto_conexoes(resultado: ResultadoComparacao) -> str:
    """Apresenta as listas de artistas calculadas pela análise."""
    texto = '**Artistas em comum:** ' + listar_markdown(resultado.artistas_comuns, 20)
    texto += '\n\n**Favoritos de A ausentes no recorte de B:** ' + listar_markdown(
        resultado.exclusivos_a, 20
    )
    texto += '\n\n**Favoritos de B ausentes no recorte de A:** ' + listar_markdown(
        resultado.exclusivos_b, 20
    )
    return texto


def _celula(valor: Any, inteiro: bool) -> Any:
    """Formata um único valor numérico; textos e datas passam inalterados."""
    if not isinstance(valor, Real):
        return valor
    if pd.isna(valor):
        return '—'
    return fmt_num(valor, 0 if inteiro or isinstance(valor, int) else 2)


def tabela_display(tabela: pd.DataFrame) -> pd.DataFrame:
    """Formata somente a pequena tabela de apresentação; os dados do núcleo permanecem numéricos.

    Processa coluna a coluna com listas, sem acessar célula por célula via ``.at``.
    """
    exibicao = tabela.astype(object)
    if 'Medida' in tabela:
        contagem = tabela['Medida'].eq('count').tolist()
    else:
        contagem = [False] * len(tabela)
    for coluna in exibicao.columns:
        exibicao[coluna] = [
            _celula(valor, inteiro) for valor, inteiro in zip(exibicao[coluna].tolist(), contagem)
        ]
    return exibicao


def apresentar(resultado: ResultadoComparacao) -> list[Any]:
    """Adapta campos nomeados à lista de componentes da v0.4 (benchmark e regressão).

    Este é o único limite posicional; o orquestrador não conhece os componentes.
    """
    a, b = resultado.perfil_a, resultado.perfil_b
    return [
        resumo_html(resultado),
        grafico_artistas(resultado.participacao_artistas, resultado.ordem_artistas),
        tabela_display(a.artistas),
        tabela_display(b.artistas),
        tabela_display(a.musicas),
        tabela_display(b.musicas),
        perfil_card(a, 'green'),
        perfil_card(b, 'violet'),
        texto_conexoes(resultado),
        tabela_display(resultado.estatisticas),
        tabela_display(resultado.diagnostico),
        grafico_meses(resultado),
    ]


def _layout_legado(fig: Figure) -> Figure:
    """Tema Spotify nas figuras legadas, sem alterar os dados protegidos pelo golden master."""
    fig.update_layout(
        separators=',.',
        template='plotly_dark',
        paper_bgcolor='#181818',
        plot_bgcolor='#181818',
        font=dict(family='Figtree, Helvetica Neue, Arial, sans-serif', size=16, color='#ffffff'),
        transition_duration=500,
    )
    fig.update_xaxes(gridcolor='#2a2a2a')
    fig.update_yaxes(gridcolor='#2a2a2a')
    return fig


def grafico_artistas(longo: pd.DataFrame, ordem: list[str]) -> Figure:
    """Desenha os dados de participação preparados pelo orquestrador (figura legada v0.4)."""
    longo = longo.copy()
    for coluna in ('Artista', 'Perfil'):
        longo[coluna] = longo[coluna].map(escape_html)
    ordem = [escape_html(nome) for nome in ordem]
    fig = px.bar(
        longo,
        x='Participação (%)',
        y='Artista',
        color='Perfil',
        orientation='h',
        barmode='group',
        color_discrete_sequence=['#1db954', '#b1a5ff'],
        category_orders={'Artista': list(ordem)},
        height=690,
    )
    _layout_legado(fig).update_layout(
        margin=dict(l=20, r=30, t=65, b=40),
        legend=dict(orientation='h', y=1.08, x=0),
        bargap=0.24,
    )
    fig.update_xaxes(ticksuffix='%')
    fig.update_yaxes(title=None)
    fig.update_traces(
        hovertemplate='%{y}<br>%{x:.2f}% das reproduções<extra>%{fullData.name}</extra>'
    )
    return fig


def grafico_meses(resultado: ResultadoComparacao) -> Figure:
    """Desenha os meses observados, sem inserir zeros em lacunas (figura legada v0.4)."""
    partes = []
    for perfil, prefixo in ((resultado.perfil_a, 'A'), (resultado.perfil_b, 'B')):
        mensal = perfil.mensal.copy()
        mensal['Perfil'] = escape_html(f'{prefixo} · {perfil.nome}')
        partes.append(mensal)
    fig = px.line(
        pd.concat(partes),
        x='Mês',
        y='Horas',
        color='Perfil',
        markers=True,
        color_discrete_sequence=['#1db954', '#b1a5ff'],
        height=400,
    )
    _layout_legado(fig).update_layout(
        margin=dict(l=30, r=30, t=30, b=50),
        legend=dict(orientation='h', y=1.12),
        hovermode='x unified',
    )
    fig.update_xaxes(nticks=10)
    return fig


def _texto_ponte(resultado: ResultadoComparacao) -> str:
    """Apresenta links de busca e mantém nomes especiais como texto literal."""
    partes = [
        'Sugestões de artistas ausentes no recorte do destino. Não são descobertas comprovadas.'
    ]
    for de, para, artista, plays, participacao, link in resultado.ponte.itertuples(
        index=False, name=None
    ):
        partes.append(
            f'- {escape_markdown(de)} → {escape_markdown(para)}: '
            f'[{escape_markdown(artista)}]({link}) · {fmt_num(plays)} plays '
            f'({fmt_num(participacao, 1)}% na origem).'
        )
    if resultado.ponte.empty:
        partes.append('Não há artistas exclusivos para sugerir neste recorte.')
    return '\n\n'.join(partes)


def _diversidade(resultado: ResultadoComparacao) -> pd.DataFrame:
    """Mostra métricas das contagens brutas, independentes da ponderação do cosseno."""
    return pd.DataFrame(
        [
            {
                'Perfil': p.nome,
                'Artistas observados': fmt_num(p.quantidade_artistas),
                'Entropia normalizada': fmt_num(p.entropia, 4) if p.entropia is not None else '—',
                'Gini observado': fmt_num(p.gini, 4) if p.gini is not None else '—',
            }
            for p in (resultado.perfil_a, resultado.perfil_b)
        ]
    )


def executar_dupla(
    arquivos_a: list[str] | None,
    arquivos_b: list[str] | None,
    nome_a: str,
    nome_b: str,
    comum: bool,
    ponderacao: str,
    fuso: str,
    musicas: str,
    artistas: str,
    varios: str,
    disco: bool,
    deduplicar: bool,
    progress: gr.Progress = gr.Progress(),
) -> list[Any]:
    """Executa o núcleo e prepara componentes; progressos representam etapas reais."""
    try:
        progress(0.05, desc='Validando filtros e arquivos')
        config = _configuracao(fuso, musicas, artistas, varios, disco, deduplicar)
        progress(0.15, desc='Lendo históricos e calculando métricas e coincidências')
        r = comparar(
            arquivos_a or [],
            arquivos_b or [],
            nome_a,
            nome_b,
            bool(comum),
            configuracao=config,
            ponderacao=ponderacao or 'bruta',
        )
        progress(0.75, desc='Preparando gráficos e tabelas')
        contribuicoes = r.contribuicoes.head(100).copy()
        contribuicoes['Contribuição ao cosseno'] = [
            fmt_num(float(x) * 100, 4) + ' p.p.' for x in contribuicoes['Contribuição ao cosseno']
        ]
        momentos = componentes.sintonia_html(r) + (
            '<p class="su-note">Quase juntos (até 1 h de distância): '
            f'<b>{fmt_num(r.momentos_artistas.total_pares)}</b> pares com o mesmo artista e '
            f'<b>{fmt_num(r.momentos_musicas.total_pares)}</b> com a mesma música. '
            'Os exemplos estão em "Quase juntos", abaixo.</p>'
        )
        a, b = r.perfil_a, r.perfil_b
        progress(0.85, desc='Montando o Wrapped da vida toda')
        wa = _wrapped_seguro(arquivos_a, a.nome, config)
        wb = _wrapped_seguro(arquivos_b, b.nome, config)
        saidas = [
            r,
            resumo_html(r),
            butterfly(r),
            mapa_horarios(r),
            radar_tracos(r),
            slope_chart(r),
            perfil_card(a, 'green', wa),
            perfil_card(b, 'violet', wb),
            tabela_display(a.artistas),
            tabela_display(b.artistas),
            tabela_display(a.musicas),
            tabela_display(b.musicas),
            contribuicoes,
            tabela_display(r.playlist.head(500)),
            _texto_ponte(r),
            momentos,
            tabela_display(r.momentos_artistas.exemplos),
            tabela_display(r.momentos_musicas.exemplos),
            _diversidade(r),
            tabela_display(r.estatisticas),
            tabela_display(r.diagnostico),
            evolucao_mensal(r),
            texto_conexoes(r),
            None,
            None,
            None,
            # Novos blocos animados (anexados ao fim para manter as posições anteriores).
            componentes.corrida_html(r),
            componentes.lista_top(a.artistas, componentes.VERDE, f'Top artistas · {a.nome}'),
            componentes.lista_top(b.artistas, componentes.ROXO, f'Top artistas · {b.nome}'),
            componentes.lista_top(
                a.musicas, componentes.VERDE, f'Top músicas · {a.nome}', musicas=True
            ),
            componentes.lista_top(
                b.musicas, componentes.ROXO, f'Top músicas · {b.nome}', musicas=True
            ),
            gr.Column(visible=True),
            gr.Column(visible=False),
            wrapped_dupla_html(wa, wb),
        ]
        progress(1, desc='Comparação concluída')
        return saidas
    except ValueError as erro:
        raise falha(str(erro)) from erro


def executar_grupo(
    arquivos: list[str] | None,
    nomes: str,
    comum: bool,
    ponderacao: str,
    fuso: str,
    musicas: str,
    artistas: str,
    varios: str,
    disco: bool,
    deduplicar: bool,
    progress: gr.Progress = gr.Progress(),
) -> list[Any]:
    """No formulário de grupo, cada arquivo é uma pessoa; nomes seguem a ordem exibida."""
    try:
        nomes_lista = list(_linhas(nomes))
        arquivos = arquivos or []
        if not arquivos or len(nomes_lista) != len(arquivos):
            raise ValueError(
                'Informe um nome por arquivo, na mesma ordem, usando de 3 a 6 arquivos.'
            )
        progress(0.1, desc='Lendo os perfis do grupo')
        config = _configuracao(fuso, musicas, artistas, varios, disco, deduplicar)
        r = comparar_grupo(
            [EntradaPerfil(nome, arquivo) for nome, arquivo in zip(nomes_lista, arquivos)],
            bool(comum),
            configuracao=config,
            ponderacao=ponderacao or 'bruta',
        )
        progress(0.85, desc='Construindo matriz e perfis')

        def numero(valor: float | None) -> str:
            return fmt_num(valor, 4) if valor is not None else '—'

        tabela = pd.DataFrame(
            [
                {
                    'Perfil': p.nome,
                    'Plays ≥30s': fmt_num(p.plays),
                    'Horas': fmt_horas(p.horas),
                    'Artistas': fmt_num(p.quantidade_artistas),
                    'Favoritos': f'{p.arquetipos.favoritos.nome} ({fmt_pct(p.arquetipos.favoritos.proporcao)})',
                    'Repeat': f'{p.arquetipos.repeticao.nome} ({fmt_pct(p.arquetipos.repeticao.proporcao)})',
                    'Madrugada': f'{p.arquetipos.madrugada.nome} ({fmt_pct(p.arquetipos.madrugada.proporcao)})',
                    'Entropia': numero(p.entropia),
                    'Gini': numero(p.gini),
                }
                for p in r.perfis
            ]
        )
        matriz = r.matriz.map(fmt_pct).reset_index(names='Perfil')
        periodo = r.periodo
        descricao = (
            f'Recorte comum global: {periodo.inicio:%d/%m/%Y} a {periodo.fim:%d/%m/%Y}.'
            if periodo.comum
            else 'Históricos completos: coberturas podem ser diferentes.'
        )
        hashes = r.diagnostico['SHA-256 do arquivo']
        if hashes.duplicated().any():
            descricao += ' Atenção: há perfis com arquivos de conteúdo idêntico (SHA-256).'
        descricao += f' Fuso: {periodo.fuso_horario}. Cosseno: {r.ponderacao}. ' + AVISO_TRACOS
        progress(1, desc='Grupo concluído')
        return [
            matriz_grupo(r),
            matriz,
            tabela,
            tabela_display(r.diagnostico),
            descricao,
            componentes.grupo_html(r, _arquetipos_grupo(arquivos, nomes_lista, config)),
            gr.Column(visible=True),
        ]
    except ValueError as erro:
        raise falha(str(erro)) from erro


def _arquetipos_grupo(
    arquivos: list[str], nomes: list[str], config: ConfiguracaoCarga
) -> list[tuple[str, str]]:
    """Arquétipo da vida toda de cada pessoa do grupo (ícone, nome)."""
    resultado = []
    for arquivo, nome in zip(arquivos, nomes):
        w = _wrapped_seguro(arquivo, nome, config)
        principal = w.arquetipos.principal if w else None
        resultado.append((principal.icone, principal.nome) if principal else ('', '—'))
    return resultado


def baixar_cartao_sintonia(
    resultado: ResultadoComparacao | None, pastas: list[str] | None
) -> tuple[str, str, list[str]]:
    """Story PNG da escuta simultânea da dupla comparada."""
    if resultado is None:
        raise falha('Faça uma comparação antes de gerar o story da sintonia.')
    arquivo, pasta = _em_pasta_temporaria(
        'sintonia',
        lambda p: str(gerar_cartao_sintonia(resultado, p / 'SyncUp_sintonia.png')),
        'o story',
    )
    return arquivo, arquivo, [*(pastas or []), pasta]


def baixar_playlist(
    resultado: ResultadoComparacao | None, pastas: list[str] | None
) -> tuple[str, list[str]]:
    """Cria um CSV isolado por clique, sem sobrescrever exportações de outras sessões."""
    if resultado is None:
        raise falha('Faça uma comparação antes de exportar a playlist.')
    arquivo, pasta = _em_pasta_temporaria(
        'playlist',
        lambda p: str(exportar_playlist(resultado, p / 'SyncUp_playlist_comum.csv')),
        'a playlist',
    )
    return arquivo, [*(pastas or []), pasta]


def baixar_cartao(
    resultado: ResultadoComparacao | None, pastas: list[str] | None
) -> tuple[str, str, list[str]]:
    """Cria cartão e download isolados, usando somente Pillow e fontes locais."""
    if resultado is None:
        raise falha('Faça uma comparação antes de gerar o cartão.')
    arquivo, pasta = _em_pasta_temporaria(
        'cartao', lambda p: str(gerar_cartao(resultado, p / 'SyncUp_cartao.png')), 'o cartão'
    )
    return arquivo, arquivo, [*(pastas or []), pasta]


@lru_cache(maxsize=1)
def _arquivos_demo() -> tuple[str, str]:
    """Gera (uma vez por processo) dois históricos fictícios pequenos para demonstração."""
    from tools.gerar_dados_falsos import Configuracao, gerar_zip

    pasta = Path(gettempdir()) / 'syncup-demo-v1'
    pasta.mkdir(parents=True, exist_ok=True)
    caminhos = []
    for nome, semente in (('demo_ana.zip', 41), ('demo_bruno.zip', 97)):
        destino = pasta / nome
        if not destino.is_file():
            gerar_zip(destino, Configuracao(linhas=40_000, artistas=250, seed=semente))
        caminhos.append(str(destino))
    return caminhos[0], caminhos[1]


def carregar_demo() -> tuple[list[str], list[str], str, str]:
    """Preenche os dois painéis com dados fictícios (nenhum dado real é usado)."""
    try:
        a, b = _arquivos_demo()
    except (OSError, ImportError, ValueError) as erro:
        raise falha('Não foi possível gerar os dados fictícios de demonstração.') from erro
    return [a], [b], 'Ana (fictícia)', 'Bruno (fictício)'
