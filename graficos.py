"""Figuras Plotly no tema Spotify, a partir de resultados nomeados; sem dependência da UI.

As animações de entrada são aplicadas no navegador (``static/syncup.js``); aqui as
figuras declaram ``transition`` para que atualizações via ``Plotly.react`` também
sejam animadas entre um resultado e outro.
"""

from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from formatacao import fmt_num, fmt_pct
from perfis import LIMIAR_FAVORITOS, LIMIAR_MADRUGADA, LIMIAR_REPEAT

if TYPE_CHECKING:
    from analise import PerfilComparado, ResultadoComparacao, ResultadoGrupo
    from conciliacao import ResultadoConciliacao

# Paleta inspirada no Spotify. Pares de texto/fundo verificados em AA nos testes.
VERDE = '#1ed760'
ROXO = '#c4b7ff'
FUNDO = '#181818'
GRADE = '#2a2a2a'
TEXTO = '#ffffff'
SECUNDARIO = '#b3b3b3'
VERDE_ESCURO = '#14833b'
FONTE = 'Figtree, "Circular Std", "Helvetica Neue", Helvetica, Arial, sans-serif'
CORES_GRUPO = [VERDE, ROXO, '#ffa42b', '#4cc9f0', '#f573a0', '#e8db5a']
DIAS_SEMANA = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
TRANSICAO = dict(duration=650, easing='cubic-in-out')


def _texto(texto: object) -> str:
    """Escapa só & < >: o Plotly lê tags, mas mostra &quot; e &#x27; ao pé da letra."""
    return escape(str(texto), quote=False)


def _base(figura: go.Figure, titulo: str, altura: int = 520) -> go.Figure:
    """Aplica contraste, fontes, locale numérico, transições e margens comuns."""
    figura.update_layout(
        title=dict(
            text=f'<b>{titulo}</b>',
            font=dict(size=20, color=TEXTO),
            x=0.01,
            xanchor='left',
            y=0.98,
            yanchor='top',
        ),
        height=altura,
        template='plotly_dark',
        paper_bgcolor=FUNDO,
        plot_bgcolor=FUNDO,
        font=dict(family=FONTE, size=15, color=TEXTO),
        separators=',.',
        margin=dict(l=45, r=35, t=110, b=60),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.01,
            x=0,
            font=dict(color=SECUNDARIO),
            bgcolor='rgba(0,0,0,0)',
        ),
        hoverlabel=dict(
            font=dict(size=15, family=FONTE, color=TEXTO), bgcolor='#282828', bordercolor=VERDE
        ),
        transition=TRANSICAO,
    )
    figura.update_xaxes(gridcolor=GRADE, zerolinecolor=SECUNDARIO, linecolor=GRADE)
    figura.update_yaxes(gridcolor=GRADE, linecolor=GRADE)
    return figura


def butterfly(resultado: ResultadoComparacao) -> go.Figure:
    """Compara participações brutas; o sinal negativo de A é apenas visual."""
    artistas = resultado.ordem_artistas
    a, b = resultado.perfil_a, resultado.perfil_b
    valores_a = [a.contagens_artistas.get(x, 0) / a.plays * 100 for x in artistas]
    valores_b = [b.contagens_artistas.get(x, 0) / b.plays * 100 for x in artistas]
    nomes = [_texto(x) for x in artistas]
    fig = go.Figure()
    for perfil, valores, sinal, cor, prefixo in (
        (a, valores_a, -1, VERDE, 'A'),
        (b, valores_b, 1, ROXO, 'B'),
    ):
        fig.add_bar(
            y=nomes,
            x=[sinal * x for x in valores],
            orientation='h',
            name=_texto(f'{prefixo} · {perfil.nome}'),
            marker=dict(color=cor, line=dict(width=0), cornerradius=6),
            customdata=valores,
            hovertemplate='%{y}<br>%{customdata:.2f}% dos plays<extra>%{fullData.name}</extra>',
        )
    limite = max(valores_a + valores_b + [1.0]) * 1.1
    ticks = [-limite, -limite / 2, 0, limite / 2, limite]
    _base(fig, 'Artistas: participação na escuta', max(500, len(artistas) * 40 + 180))
    fig.update_layout(barmode='relative', bargap=0.3)
    fig.update_xaxes(
        title=dict(text='Participação nos plays de cada perfil (%)', font=dict(color=SECUNDARIO)),
        range=[-limite, limite],
        tickvals=ticks,
        ticktext=[fmt_num(abs(x), 1) + '%' for x in ticks],
    )
    fig.update_yaxes(autorange='reversed', title=None, showgrid=False)
    return fig


def _matriz_horarios(perfil: PerfilComparado) -> list[list[float]]:
    """Preenche sete dias e 24 horas, como percentual do total de plays."""
    matriz = [[0.0] * 24 for _ in range(7)]
    for dia, hora, quantidade in perfil.horarios.itertuples(index=False, name=None):
        matriz[int(dia)][int(hora)] = float(quantidade) / perfil.plays * 100
    return matriz


def mapa_horarios(resultado: ResultadoComparacao) -> go.Figure:
    """Exibe mapas lado a lado com a mesma escala, no fuso já aplicado pelo loader."""
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=[
            _texto(f'A · {resultado.perfil_a.nome}'),
            _texto(f'B · {resultado.perfil_b.nome}'),
        ],
        horizontal_spacing=0.12,
    )
    matrizes = [_matriz_horarios(p) for p in (resultado.perfil_a, resultado.perfil_b)]
    for coluna, matriz in enumerate(matrizes, 1):
        fig.add_trace(
            go.Heatmap(
                z=matriz,
                x=list(range(24)),
                y=DIAS_SEMANA,
                coloraxis='coloraxis',
                xgap=2,
                ygap=2,
                hovertemplate='%{y}, %{x}h<br>%{z:.2f}% dos plays<extra></extra>',
            ),
            row=1,
            col=coluna,
        )
    _base(fig, f'Horários de escuta · {_texto(resultado.periodo.fuso_horario)}', 540)
    fig.update_layout(
        coloraxis=dict(
            colorscale=[[0, '#202020'], [0.35, '#1a5c33'], [0.7, VERDE_ESCURO], [1, VERDE]],
            # Escala comum aos dois mapas, do menor ao maior valor observado: realça o padrão.
            cmin=min(min(map(min, m)) for m in matrizes),
            cmax=max(max(map(max, m)) for m in matrizes) or 1,
            colorbar=dict(title='% dos plays', outlinewidth=0, thickness=14),
        )
    )
    fig.update_annotations(font=dict(color=SECUNDARIO, size=15))
    fig.update_xaxes(title='Hora local', tickvals=[0, 4, 8, 12, 16, 20, 23], showgrid=False)
    fig.update_yaxes(autorange='reversed', showgrid=False)
    return fig


def radar_tracos(resultado: ResultadoComparacao) -> go.Figure:
    """Compara três proporções observáveis e os limiares oficiais do módulo perfis."""
    categorias = ['Top 2 artistas', 'Top 10 faixas', 'Madrugada (00–05h59)']
    theta = categorias + [categorias[0]]
    fig = go.Figure()
    for prefixo, perfil, cor, preenchimento in (
        ('A', resultado.perfil_a, VERDE, 'rgba(30,215,96,0.25)'),
        ('B', resultado.perfil_b, ROXO, 'rgba(196,183,255,0.25)'),
    ):
        arq = perfil.arquetipos
        valores = [arq.favoritos.proporcao, arq.repeticao.proporcao, arq.madrugada.proporcao]
        fig.add_trace(
            go.Scatterpolar(
                r=[x * 100 for x in valores + [valores[0]]],
                theta=theta,
                mode='lines+markers',
                fill='toself',
                fillcolor=preenchimento,
                line=dict(color=cor, width=3),
                marker=dict(size=9),
                name=_texto(f'{prefixo} · {perfil.nome}'),
                hovertemplate='%{theta}: %{r:.1f}%<extra>%{fullData.name}</extra>',
            )
        )
    limiares = [LIMIAR_FAVORITOS * 100, LIMIAR_REPEAT * 100, LIMIAR_MADRUGADA * 100]
    fig.add_trace(
        go.Scatterpolar(
            r=limiares + [limiares[0]],
            theta=theta,
            mode='lines+markers',
            line=dict(color=TEXTO, dash='dash', width=2),
            name='Limiares de classificação',
        )
    )
    _base(fig, 'Traços de escuta · regras experimentais', 580)
    fig.update_layout(
        polar=dict(
            bgcolor=FUNDO,
            radialaxis=dict(
                range=[0, 100],
                ticksuffix='%',
                gridcolor='#3a3a3a',
                linecolor='#3a3a3a',
                tickfont=dict(size=13, color=SECUNDARIO),
            ),
            angularaxis=dict(gridcolor='#3a3a3a', linecolor='#3a3a3a', tickfont=dict(size=15)),
        ),
        legend=dict(orientation='h', yanchor='top', y=-0.06, x=0.5, xanchor='center'),
        margin=dict(l=90, r=90, t=90, b=90),
    )
    return fig


def slope_chart(resultado: ResultadoComparacao, limite: int = 8) -> go.Figure:
    """Liga participações por artista entre A e B; não representa evolução temporal."""
    fig = go.Figure()
    a, b = resultado.perfil_a, resultado.perfil_b
    artistas = resultado.ordem_artistas[: max(0, limite)]
    for i, artista in enumerate(artistas):
        valores = [
            a.contagens_artistas.get(artista, 0) / a.plays * 100,
            b.contagens_artistas.get(artista, 0) / b.plays * 100,
        ]
        fig.add_trace(
            go.Scatter(
                x=[0, 1],
                y=valores,
                mode='lines+markers',
                name=_texto(artista),
                line=dict(color=CORES_GRUPO[i % len(CORES_GRUPO)], width=3),
                marker=dict(size=12, symbol='circle' if i < 6 else 'diamond'),
                hovertemplate='%{y:.2f}% dos plays<extra>%{fullData.name}</extra>',
            )
        )
    quantidade = len(artistas)
    _base(
        fig,
        f'Diferenças de participação · {quantidade} artista{"s" if quantidade != 1 else ""} '
        f'líder{"es" if quantidade != 1 else ""}',
        600,
    )
    fig.update_xaxes(
        tickvals=[0, 1],
        ticktext=[_texto(f'A · {a.nome}'), _texto(f'B · {b.nome}')],
        range=[-0.15, 1.15],
        showgrid=False,
        zeroline=False,
    )
    fig.update_yaxes(title='Participação nos plays (%)', ticksuffix='%')
    fig.update_layout(
        legend=dict(orientation='v', x=1.02, y=0.9, yanchor='top'),
        margin=dict(l=70, r=190, t=90, b=85),
    )
    return fig


def matriz_grupo(resultado: ResultadoGrupo) -> go.Figure:
    """Exibe a matriz simétrica, com valores explícitos além das cores."""
    nomes = [_texto(x) for x in resultado.matriz.index]
    valores = resultado.matriz.values.tolist()
    fig = go.Figure(
        go.Heatmap(
            x=nomes,
            y=nomes,
            z=valores,
            zmin=0,
            zmax=1,
            xgap=4,
            ygap=4,
            colorscale=[[0, '#202020'], [1, VERDE_ESCURO]],
            text=[[fmt_pct(x) for x in linha] for linha in valores],
            texttemplate='%{text}',
            textfont=dict(color=TEXTO, size=18, family=FONTE),
            showscale=False,
            hovertemplate='%{y} × %{x}<br>Cosseno: %{z:.4f}<extra></extra>',
        )
    )
    _base(fig, f'Grupo · cosseno com ponderação {_texto(resultado.ponderacao)}', 640)
    fig.update_xaxes(showgrid=False, side='bottom')
    fig.update_yaxes(autorange='reversed', showgrid=False)
    return fig


def evolucao_mensal(resultado: ResultadoComparacao) -> go.Figure:
    """Horas por mês com área suave; meses sem dados não recebem zeros artificiais."""
    fig = go.Figure()
    for prefixo, perfil, cor, area in (
        ('A', resultado.perfil_a, VERDE, 'rgba(30,215,96,0.12)'),
        ('B', resultado.perfil_b, ROXO, 'rgba(196,183,255,0.12)'),
    ):
        fig.add_trace(
            go.Scatter(
                x=perfil.mensal['Mês'],
                y=perfil.mensal['Horas'],
                mode='lines+markers',
                name=_texto(f'{prefixo} · {perfil.nome}'),
                line=dict(color=cor, width=3, shape='spline', smoothing=0.6),
                marker=dict(size=6),
                fill='tozeroy',
                fillcolor=area,
                hovertemplate='%{x}: %{y:.1f} h<extra>%{fullData.name}</extra>',
            )
        )
    _base(fig, 'Horas ouvidas por mês', 430)
    fig.update_layout(hovermode='x unified')
    fig.update_xaxes(nticks=12, showgrid=False)
    fig.update_yaxes(title='Horas', rangemode='tozero')
    return fig


def matriz_conciliacao(resultado: ResultadoConciliacao) -> go.Figure:
    """Compatibilidade de todos com todos (0–100); a diagonal fica em branco."""
    nomes = [_texto(x) for x in resultado.nomes]
    valores = [
        [None if i == j else v for j, v in enumerate(linha)]
        for i, linha in enumerate(resultado.matriz.values.tolist())
    ]
    maximo = max((v for linha in valores for v in linha if v is not None), default=1) or 1
    fig = go.Figure(
        go.Heatmap(
            x=nomes,
            y=nomes,
            z=valores,
            zmin=0,
            zmax=maximo,
            xgap=4,
            ygap=4,
            colorscale=[[0, '#202020'], [1, VERDE_ESCURO]],
            text=[['—' if v is None else fmt_num(v, 1) + '%' for v in linha] for linha in valores],
            texttemplate='%{text}',
            textfont=dict(color=TEXTO, size=17, family=FONTE),
            showscale=False,
            hoverongaps=False,
            hovertemplate='%{y} × %{x}<br>Compatibilidade: %{z:.1f}%<extra></extra>',
        )
    )
    _base(fig, 'Compatibilidade de todos com todos', max(420, 90 * len(nomes) + 160))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(autorange='reversed', showgrid=False)
    return fig
