"""Apresentação da Dupla sem Gradio: HTML, tabelas e gráficos a partir do resultado.

Usado pela interface Gradio (``ui/``) e pelo app no navegador (``web/ponte.py``, Pyodide).
"""

from __future__ import annotations

from numbers import Real
from typing import TYPE_CHECKING, Any

import pandas as pd

import componentes
import stories
from analise import PerfilComparado, ResultadoComparacao
from configuracao import ConfiguracaoCarga
from formatacao import escape_html, escape_markdown, fmt_num, fmt_pct, listar_markdown
from perfis import LIMIAR_FAVORITOS, LIMIAR_MADRUGADA, LIMIAR_REPEAT
from wrapped import Wrapped, wrapped_de_arquivos

if TYPE_CHECKING:
    from plotly.graph_objects import Figure

OPCOES_PONDERACAO = [
    ('Bruta (x)', 'bruta'),
    ('Raiz quadrada (√x)', 'raiz'),
    ('Logaritmo (ln(1+x))', 'log1p'),
]


TEXTO_LIMIARES = (
    f'Regras experimentais: favoritos ≥{LIMIAR_FAVORITOS:.0%}; repeat ≥{LIMIAR_REPEAT:.0%}; '
    f'madrugada ≥{LIMIAR_MADRUGADA:.0%}. Descrevem este recorte de escuta; '
    'não medem personalidade ou afinidade amorosa.'
)


def formatar(numero: int | float) -> str:
    """Formata contagens com separador de milhares brasileiro."""
    return fmt_num(numero)


def _linhas(texto: str | None) -> tuple[str, ...]:
    """Um nome por linha, ignorando linhas vazias."""
    return tuple(x.strip() for x in (texto or '').splitlines() if x.strip())


def _configuracao(
    fuso: str, musicas: str, artistas: str, varios: str, disco: bool, deduplicar: bool
) -> ConfiguracaoCarga:
    """Converte controles visíveis em uma configuração única para os dois modos."""
    return ConfiguracaoCarga(
        fuso_horario=fuso or 'America/Sao_Paulo',
        musicas_ignoradas=_linhas(musicas),
        artistas_ignorados=_linhas(artistas),
        various_artists=varios or 'manter',
        usar_cache_disco=bool(disco),
        deduplicar=bool(deduplicar),
    )


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
    import plotly.express as px  # sob demanda: o app no navegador só baixa o plotly na Dupla

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
    import plotly.express as px  # sob demanda: o app no navegador só baixa o plotly na Dupla

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
