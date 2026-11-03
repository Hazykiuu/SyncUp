"""Apresentação do SyncUp no tema Spotify; consome os resultados estruturados de analise.py."""

from __future__ import annotations

import base64
import os
import shutil
from functools import lru_cache
from numbers import Real
from pathlib import Path
from tempfile import gettempdir, mkdtemp
from typing import Any
from zoneinfo import available_timezones

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
from cartao import gerar_cartao, gerar_cartao_wrapped
from conciliacao import conciliar
from configuracao import MUSICAS_IGNORADAS_PADRAO, ConfiguracaoCarga
from dados import (
    MAXIMO_HISTORICOS_CACHE,
    carregar_historicos,
    habilitar_leitura_paralela,
    precarregar,
)
from exportacoes import exportar_playlist
from formatacao import escape_html, escape_markdown, fmt_horas, fmt_num, fmt_pct, listar_markdown
from graficos import (
    butterfly,
    evolucao_mensal,
    mapa_horarios,
    matriz_conciliacao,
    matriz_grupo,
    radar_tracos,
    slope_chart,
)
from perfil_gosto import carregar_perfil, listar_perfis, perfil_de_historico
from perfis import AVISO_TRACOS, LIMIAR_FAVORITOS, LIMIAR_MADRUGADA, LIMIAR_REPEAT
from spotify_api import PASTA_PERFIS, REDIRECT_PADRAO
from wrapped import Wrapped, wrapped_de_arquivos

PASTA = Path(__file__).resolve().parent
# Figtree (OFL) embutida no CSS: nenhuma requisição ao Google Fonts, funciona offline.
FONTE_CSS = (
    "@font-face{font-family:'Figtree';font-weight:300 900;font-display:swap;"
    "src:url(data:font/ttf;base64,"
    + base64.b64encode((PASTA / 'fontes' / 'Figtree.ttf').read_bytes()).decode('ascii')
    + ") format('truetype');}\n"
)
CSS = FONTE_CSS + (PASTA / 'styles.css').read_text(encoding='utf-8')
JS = (PASTA / 'syncup.js').read_text(encoding='utf-8')
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
HEAD = '<meta name="theme-color" content="#121212">'


def formatar(numero: int | float) -> str:
    """Formata contagens com separador de milhares brasileiro."""
    return fmt_num(numero)


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
    """Mantém a apresentação textual da v0.4 para o notebook e a regressão."""
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
    """Adapta campos nomeados à lista de componentes da v0.4 (notebook e benchmark).

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
        momentos = (
            f'**Mesmo artista:** {fmt_num(r.momentos_artistas.total_pares)} pares. '
            f'**Mesma música e artista:** {fmt_num(r.momentos_musicas.total_pares)} pares. '
            'Janela inclusiva de 1h em UTC. Eventos não se repetem dentro de cada análise; '
            'os totais são alternativas e não devem ser somados. '
            'Tabelas mostram até 200 exemplos, por artista/música e instante. '
            'Coincidências não comprovam influência ou escuta simultânea durante a faixa.'
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
        raise gr.Error(str(erro)) from erro


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
        raise gr.Error(str(erro)) from erro


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


def executar_wrapped(
    arquivos: list[str] | None,
    nome: str,
    fuso: str,
    musicas: str,
    artistas: str,
    varios: str,
    disco: bool,
    deduplicar: bool,
    progress: gr.Progress = gr.Progress(),
) -> list[Any]:
    """Wrapped individual da vida toda: stories, detalhe dos arquétipos e estado para o PNG."""
    try:
        if not arquivos:
            raise ValueError('Selecione o histórico (ZIP ou JSONs) para montar o Wrapped.')
        progress(0.1, desc='Lendo o histórico completo')
        config = _configuracao(fuso, musicas, artistas, varios, disco, deduplicar)
        w = wrapped_de_arquivos(arquivos, nome, config)
        progress(0.8, desc='Montando os stories')
        saidas = [
            w,
            stories.stories_html(w),
            stories.arquetipos_detalhe_html(w),
            gr.Column(visible=True),
            None,
            None,
        ]
        progress(1, desc='Wrapped pronto')
        return saidas
    except ValueError as erro:
        raise gr.Error(str(erro)) from erro


def baixar_wrapped(w: Wrapped | None, pastas: list[str] | None) -> tuple[str, str, list[str]]:
    """Story PNG 1080×1920 com o resumo do Wrapped, em pasta temporária da sessão."""
    if w is None:
        raise gr.Error('Gere o Wrapped antes de baixar a imagem.')
    pasta = mkdtemp(prefix='syncup-wrapped-')
    try:
        arquivo = gerar_cartao_wrapped(w, Path(pasta) / 'SyncUp_Wrapped.png')
    except OSError as erro:
        shutil.rmtree(pasta, ignore_errors=True)
        raise gr.Error('Não foi possível gravar a imagem no diretório temporário.') from erro
    return str(arquivo), str(arquivo), [*(pastas or []), pasta]


def carregar_demo_wrapped() -> tuple[list[str], str]:
    """Um histórico fictício para experimentar o Wrapped."""
    a, _ = carregar_demo()[:2]
    return a, 'Ana (fictícia)'


def perfis_salvos() -> list[str]:
    """Nomes dos perfis coletados via login do Spotify (pasta perfis_spotify)."""
    return [p.stem for p in listar_perfis(PASTA_PERFIS)]


def atualizar_perfis(selecionados: list[str] | None) -> Any:
    """Recarrega a lista de perfis salvos, mantendo a seleção atual."""
    opcoes = perfis_salvos()
    marcados = [s for s in (selecionados or []) if s in opcoes] or opcoes
    return gr.CheckboxGroup(choices=opcoes, value=marcados)


def executar_match(
    arquivos: list[str] | None,
    nomes: str,
    selecionados: list[str] | None,
    fuso: str,
    musicas: str,
    artistas: str,
    varios: str,
    disco: bool,
    deduplicar: bool,
    progress: gr.Progress = gr.Progress(),
) -> list[Any]:
    """Junta perfis de ZIP e do Spotify, concilia todos e mostra os melhores pares."""
    try:
        arquivos = arquivos or []
        nomes_zip = list(_linhas(nomes))
        if arquivos and len(nomes_zip) != len(arquivos):
            raise ValueError('Informe um nome por arquivo ZIP, na mesma ordem dos arquivos.')
        config = _configuracao(fuso, musicas, artistas, varios, disco, deduplicar)
        perfis, fontes = [], {}
        for i, (arquivo, nome) in enumerate(zip(arquivos, nomes_zip)):
            if i % MAXIMO_HISTORICOS_CACHE == 0:
                # Lê o bloco em paralelo; blocos do tamanho do cache não descartam trabalho.
                precarregar(arquivos[i : i + MAXIMO_HISTORICOS_CACHE], config)
            progress(0.05 + 0.6 * i / max(len(arquivos), 1), desc=f'Lendo o histórico de {nome}')
            historico = carregar_historicos(arquivo, configuracao=config)
            perfis.append(perfil_de_historico(historico.dados, nome))
            fontes[nome] = 'Histórico ZIP'
        for nome in selecionados or []:
            perfil = carregar_perfil(PASTA_PERFIS / f'{nome}.json')
            perfis.append(perfil)
            fontes[perfil.nome] = f'Spotify · {perfil.coletado_em[:10]}'
        progress(0.75, desc='Comparando todos com todos')
        r = conciliar(perfis)
        ranking = pd.DataFrame(
            [
                {
                    'Pessoa': nome,
                    'Fonte': fontes.get(nome, ''),
                    '1º match': f'{r.melhores[nome][0][0]} ({fmt_num(r.melhores[nome][0][1], 1)}%)',
                    '2º match': (
                        f'{r.melhores[nome][1][0]} ({fmt_num(r.melhores[nome][1][1], 1)}%)'
                        if len(r.melhores[nome]) > 1
                        else '—'
                    ),
                }
                for nome in r.nomes
            ]
        )
        progress(1, desc='Matches prontos')
        return [
            componentes.match_html(r, fontes),
            matriz_conciliacao(r),
            ranking,
            gr.Column(visible=True),
        ]
    except ValueError as erro:
        raise gr.Error(str(erro)) from erro


def _limpar_exportacoes(pastas: list[str]) -> None:
    """Apaga apenas diretórios temporários criados para exportações desta sessão."""
    for pasta in pastas or []:
        shutil.rmtree(pasta, ignore_errors=True)


def baixar_playlist(
    resultado: ResultadoComparacao | None, pastas: list[str] | None
) -> tuple[str, list[str]]:
    """Cria um CSV isolado por clique, sem sobrescrever exportações de outras sessões."""
    if resultado is None:
        raise gr.Error('Faça uma comparação antes de exportar a playlist.')
    pasta = mkdtemp(prefix='syncup-playlist-')
    try:
        arquivo = exportar_playlist(resultado, Path(pasta) / 'SyncUp_playlist_comum.csv')
    except OSError as erro:
        shutil.rmtree(pasta, ignore_errors=True)
        raise gr.Error('Não foi possível gravar a playlist no diretório temporário.') from erro
    return str(arquivo), [*(pastas or []), pasta]


def baixar_cartao(
    resultado: ResultadoComparacao | None, pastas: list[str] | None
) -> tuple[str, str, list[str]]:
    """Cria cartão e download isolados, usando somente Pillow e fontes locais."""
    if resultado is None:
        raise gr.Error('Faça uma comparação antes de gerar o cartão.')
    pasta = mkdtemp(prefix='syncup-cartao-')
    try:
        arquivo = gerar_cartao(resultado, Path(pasta) / 'SyncUp_cartao.png')
    except OSError as erro:
        shutil.rmtree(pasta, ignore_errors=True)
        raise gr.Error('Não foi possível gravar o cartão no diretório temporário.') from erro
    return str(arquivo), str(arquivo), [*(pastas or []), pasta]


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
        raise gr.Error('Não foi possível gerar os dados fictícios de demonstração.') from erro
    return [a], [b], 'Ana (fictícia)', 'Bruno (fictício)'


def _tema() -> gr.themes.Base:
    """Tema nativo do Gradio com a paleta escura do Spotify."""
    fonte = [gr.themes.Font('Figtree'), 'Helvetica Neue', 'Helvetica', 'Arial', 'sans-serif']
    cores = dict(
        body_background_fill='#121212',
        body_text_color='#ffffff',
        body_text_color_subdued='#b3b3b3',
        background_fill_primary='#181818',
        background_fill_secondary='#1f1f1f',
        block_background_fill='#181818',
        block_border_color='#2a2a2a',
        block_border_width='1px',
        block_label_text_color='#b3b3b3',
        block_label_background_fill='#181818',
        block_title_text_color='#ffffff',
        block_info_text_color='#b3b3b3',
        border_color_primary='#2a2a2a',
        border_color_accent='#1ed760',
        color_accent='#1ed760',
        color_accent_soft='#1f3d2a',
        input_background_fill='#2a2a2a',
        input_border_color='#2a2a2a',
        input_border_color_focus='#1ed760',
        input_placeholder_color='#b3b3b3',
        checkbox_background_color='#2a2a2a',
        checkbox_background_color_selected='#1ed760',
        checkbox_border_color='#727272',
        checkbox_border_color_selected='#1ed760',
        checkbox_label_background_fill='#181818',
        checkbox_label_background_fill_selected='#181818',
        checkbox_label_text_color='#ffffff',
        checkbox_label_text_color_selected='#ffffff',
        table_text_color='#ffffff',
        table_even_background_fill='#181818',
        table_odd_background_fill='#1f1f1f',
        table_border_color='#2a2a2a',
        table_row_focus='#2a2a2a',
        button_primary_background_fill='#1ed760',
        button_primary_background_fill_hover='#3be477',
        button_primary_text_color='#000000',
        button_primary_text_color_hover='#000000',
        button_secondary_background_fill='#2a2a2a',
        button_secondary_background_fill_hover='#3e3e3e',
        button_secondary_text_color='#ffffff',
        button_secondary_text_color_hover='#ffffff',
        link_text_color='#1ed760',
        link_text_color_hover='#3be477',
        loader_color='#1ed760',
        slider_color='#1ed760',
        stat_background_fill='#1ed760',
        panel_background_fill='#181818',
        accordion_text_color='#ffffff',
        shadow_drop='0 8px 24px rgba(0,0,0,.5)',
    )
    # Mesmas cores no modo escuro do navegador.
    sem_variante = {'color_accent', 'shadow_drop'}
    cores |= {f'{chave}_dark': valor for chave, valor in cores.items() if chave not in sem_variante}
    return gr.themes.Base(
        primary_hue='green',
        secondary_hue='violet',
        neutral_hue='neutral',
        font=fonte,
        font_mono=fonte,
        radius_size=gr.themes.sizes.radius_lg,
    ).set(
        **cores,
        block_info_text_size='15px',
        block_label_text_size='15px',
        block_title_text_size='17px',
        input_text_size='16px',
        button_large_text_size='16px',
        button_small_text_size='16px',
        button_medium_text_size='16px',
        button_large_radius='999px',
        button_medium_radius='999px',
        button_small_radius='999px',
    )


def _secao(titulo: str, texto: str = '') -> gr.HTML:
    """Cabeçalho de seção no estilo das prateleiras do Spotify."""
    corpo = f'<p>{escape_html(texto)}</p>' if texto else ''
    return gr.HTML(f'<div class="su-section"><h3>{escape_html(titulo)}</h3>{corpo}</div>')


HERO = """<header class="su-hero">
  <div class="su-logo" aria-hidden="true"><i></i><i></i><i></i><i></i></div>
  <div class="su-hero-text">
    <small>COMPARADOR DE HISTÓRICOS · v0.8</small>
    <h1>SyncUp</h1>
    <p>Seus históricos do Spotify, lado a lado — tudo processado localmente.</p>
    <div class="su-chips"><span>Match entre amigos</span><span>Login com Spotify</span><span>Wrapped da vida toda</span><span>Arquétipos</span><span>Blend de similaridade</span><span>Corrida de artistas</span><span>Momentos sincronizados</span><span>Modo grupo</span></div>
  </div>
</header>"""

VAZIO = """<div class="su-blend"><div class="su-blend-hero" style="grid-template-columns:auto 1fr">
<div class="su-logo" aria-hidden="true"><i></i><i></i><i></i><i></i></div>
<div class="su-blend-text"><div class="su-eyebrow">PRONTO PARA TOCAR</div>
<h2>Envie os dois históricos e aperte o play</h2>
<p>Use o Histórico Estendido (ZIP ou JSONs) de cada pessoa, ou experimente com dados fictícios.</p></div></div></div>"""


def criar_interface() -> gr.Blocks:
    """Constrói Gradio 5 com tema Spotify, CSS/JS externos e comparação de dupla/grupo."""
    habilitar_leitura_paralela()
    with gr.Blocks(
        theme=_tema(),
        css=CSS,
        js=JS,
        head=HEAD,
        title='SyncUp',
        analytics_enabled=False,
        delete_cache=(3600, 3600),
    ) as demo:
        gr.HTML(HERO)
        gr.Markdown(AVISO_TRACOS, elem_classes='su-note')
        with gr.Accordion('Opções de dados · valem para todas as abas', open=False):
            fuso = gr.Dropdown(
                sorted(available_timezones()), value='America/Sao_Paulo', label='Fuso horário IANA'
            )
            with gr.Row():
                ignorar_musicas = gr.Textbox(
                    value='',
                    placeholder='\n'.join(MUSICAS_IGNORADAS_PADRAO),
                    lines=3,
                    label='Músicas ignoradas · um nome por linha',
                )
                ignorar_artistas = gr.Textbox(
                    value='', lines=3, label='Artistas ignorados · um nome por linha'
                )
            varios = gr.Dropdown(
                choices=[
                    ('Manter como artista agregado', 'manter'),
                    ('Ignorar coletâneas', 'ignorar'),
                ],
                value='manter',
                label='Various Artists',
            )
            disco = gr.Checkbox(value=False, label='Cache Parquet em disco · dependência opcional')
            deduplicar = gr.Checkbox(
                value=False, label='Remover eventos idênticos · UTC, duração, artista e música'
            )
            gr.Markdown(
                'Various Artists não identifica o intérprete real. Arquivos inteiros repetidos são rejeitados dentro do mesmo perfil.'
            )
        opcoes = [fuso, ignorar_musicas, ignorar_artistas, varios, disco, deduplicar]
        with gr.Tabs():
            with gr.Tab('Dupla'):
                estado = gr.State(value=None, time_to_live=3600)
                pastas = gr.State(value=[], time_to_live=3600, delete_callback=_limpar_exportacoes)
                with gr.Row(equal_height=True):
                    with gr.Column(elem_classes=['su-panel', 'a']):
                        gr.HTML(
                            '<div class="su-panel-title"><span class="su-avatar a">A</span>Primeiro perfil</div>'
                        )
                        na = gr.Textbox(value='Pessoa A', label='Nome do primeiro perfil')
                        fa = gr.File(
                            file_count='multiple',
                            file_types=['.zip', '.json'],
                            type='filepath',
                            label='Todas as partes do histórico de A',
                        )
                    with gr.Column(elem_classes=['su-panel', 'b']):
                        gr.HTML(
                            '<div class="su-panel-title"><span class="su-avatar b">B</span>Segundo perfil</div>'
                        )
                        nb = gr.Textbox(value='Pessoa B', label='Nome do segundo perfil')
                        fb = gr.File(
                            file_count='multiple',
                            file_types=['.zip', '.json'],
                            type='filepath',
                            label='Todas as partes do histórico de B',
                        )
                gr.Markdown(
                    'Cada painel representa uma pessoa; vários ZIPs/JSONs do painel serão unidos.',
                    elem_classes='su-note',
                )
                with gr.Row(equal_height=True):
                    comum = gr.Checkbox(value=True, label='Período coberto pelos dois históricos')
                    peso = gr.Dropdown(
                        choices=OPCOES_PONDERACAO,
                        value='bruta',
                        label='Ponderação do cosseno e Ruzicka',
                    )
                    with gr.Column(min_width=260):
                        botao = gr.Button(
                            'Comparar históricos', variant='primary', elem_classes='su-play'
                        )
                        demo_btn = gr.Button(
                            'Testar com dados fictícios', elem_classes='su-secondary'
                        )
                with gr.Column(visible=True) as vazio:
                    gr.HTML(VAZIO)
                with gr.Column(visible=False, elem_classes='su-results') as resultados:
                    resumo = gr.HTML()
                    _secao(
                        'Quem ouve quem',
                        'Participação dos artistas líderes nos plays de cada perfil.',
                    )
                    plot = gr.Plot(show_label=False, elem_classes='su-chart')
                    _secao('Identidades musicais')
                    with gr.Row(equal_height=True):
                        aa = gr.HTML()
                        ab = gr.HTML()
                    _secao(
                        'Corrida dos artistas',
                        'Plays acumulados mês a mês. Use o player para pausar ou arrastar a linha do tempo.',
                    )
                    corrida = gr.HTML()
                    _secao('Explorar')
                    with gr.Tabs():
                        with gr.Tab('Wrapped da vida toda'):
                            wrapped_dupla = gr.HTML()
                        with gr.Tab('Rankings'):
                            with gr.Row(equal_height=True):
                                lista_aa = gr.HTML()
                                lista_ab = gr.HTML()
                            with gr.Row(equal_height=True):
                                lista_ma = gr.HTML()
                                lista_mb = gr.HTML()
                            conexoes = gr.Markdown()
                            with gr.Accordion('Tabelas completas · top 20', open=False):
                                with gr.Row():
                                    ta = gr.Dataframe(
                                        interactive=False, wrap=True, label='Artistas A · top 20'
                                    )
                                    tb = gr.Dataframe(
                                        interactive=False, wrap=True, label='Artistas B · top 20'
                                    )
                                with gr.Row():
                                    ma = gr.Dataframe(
                                        interactive=False, wrap=True, label='Músicas A · top 20'
                                    )
                                    mb = gr.Dataframe(
                                        interactive=False, wrap=True, label='Músicas B · top 20'
                                    )
                        with gr.Tab('Horários e traços'):
                            gr.Markdown(AVISO_TRACOS, elem_classes='su-note')
                            gr.Markdown(
                                f'Favoritos: top 2 ≥{fmt_pct(LIMIAR_FAVORITOS)}. Repeat: top 10 faixas ≥{fmt_pct(LIMIAR_REPEAT)}. '
                                f'Madrugada: 00h–05h59 ≥{fmt_pct(LIMIAR_MADRUGADA)}. Em amostras pequenas, top 10 tende a ser alto.',
                                elem_classes='su-note',
                            )
                            heatmap = gr.Plot(show_label=False, elem_classes='su-chart')
                            radar = gr.Plot(show_label=False, elem_classes='su-chart')
                        with gr.Tab('Diferenças e contribuição'):
                            slope = gr.Plot(show_label=False, elem_classes='su-chart')
                            gr.Markdown(
                                'Contribuição por artista = aᵢ·bᵢ/(|a|·|b|). A soma de todos os artistas é o cosseno. '
                                'Valores em pontos percentuais, com a ponderação selecionada. Tabela: 100 líderes; artistas exclusivos contribuem zero.',
                                elem_classes='su-note',
                            )
                            contrib = gr.Dataframe(
                                interactive=False, wrap=True, label='Contribuições ao cosseno'
                            )
                            gr.Markdown(
                                'Entropia = −Σp·ln(p)/ln(k); uma categoria vale 0. '
                                'Gini = Σ(2i−k−1)xᵢ/(kΣx). Ambos usam contagens brutas positivas dos artistas observados. '
                                'Uniformidade: entropia 1 para k>1, Gini 0; Gini máximo (k−1)/k. Não medem diversidade de gêneros.',
                                elem_classes='su-note',
                            )
                            diversidade = gr.Dataframe(
                                interactive=False, label='Diversidade e desigualdade observadas'
                            )
                        with gr.Tab('Momentos sincronizados'):
                            momentos = gr.Markdown()
                            momentos_a = gr.Dataframe(
                                interactive=False,
                                wrap=True,
                                label='Pares de mesmo artista · exemplos',
                            )
                            momentos_m = gr.Dataframe(
                                interactive=False,
                                wrap=True,
                                label='Pares de mesma música e artista · exemplos',
                            )
                        with gr.Tab('Ponte Musical e playlist'):
                            ponte = gr.Markdown()
                            gr.Markdown(
                                'Playlist = faixas presentes em ambos os recortes, identificadas por artista e título. '
                                'Prévia: até 500 faixas. O CSV contém todas; os links abrem buscas no Spotify. Não cria playlist na sua conta.',
                                elem_classes='su-note',
                            )
                            playlist = gr.Dataframe(
                                interactive=False, wrap=True, label='Playlist comum · prévia'
                            )
                            exportar = gr.Button(
                                'Exportar playlist comum · CSV', elem_classes='su-secondary'
                            )
                            csv_download = gr.File(label='Baixar playlist CSV', interactive=False)
                        with gr.Tab('Cartão para compartilhar'):
                            gr.Markdown(
                                'PNG 1080×1350 gerado localmente. Inclui os nomes informados e métricas do recorte.',
                                elem_classes='su-note',
                            )
                            criar_cartao = gr.Button('Gerar cartão PNG', elem_classes='su-play')
                            imagem = gr.Image(
                                type='filepath', interactive=False, label='Prévia do cartão'
                            )
                            png_download = gr.File(label='Baixar cartão PNG', interactive=False)
                        with gr.Tab('Evolução e EDA'):
                            mensal = gr.Plot(show_label=False, elem_classes='su-chart')
                            stats = gr.Dataframe(
                                interactive=False, label='describe() · minutos por execução'
                            )
                        with gr.Tab('Diagnóstico'):
                            gr.Markdown(
                                'Descartes exclusivos: podcast → duração → data → identificação → Various Artists → filtros → duplicados. '
                                'SHA-256 identifica conteúdo, não o dono. Similaridade 100% não prova arquivos idênticos.',
                                elem_classes='su-note',
                            )
                            diag = gr.Dataframe(interactive=False, wrap=True)
                saidas = [
                    estado,
                    resumo,
                    plot,
                    heatmap,
                    radar,
                    slope,
                    aa,
                    ab,
                    ta,
                    tb,
                    ma,
                    mb,
                    contrib,
                    playlist,
                    ponte,
                    momentos,
                    momentos_a,
                    momentos_m,
                    diversidade,
                    stats,
                    diag,
                    mensal,
                    conexoes,
                    csv_download,
                    imagem,
                    png_download,
                    corrida,
                    lista_aa,
                    lista_ab,
                    lista_ma,
                    lista_mb,
                    resultados,
                    vazio,
                    wrapped_dupla,
                ]
                botao.click(
                    executar_dupla,
                    [fa, fb, na, nb, comum, peso, *opcoes],
                    saidas,
                    api_name='comparar_dupla',
                    scroll_to_output=True,
                )
                demo_btn.click(carregar_demo, None, [fa, fb, na, nb], api_name=False)
                exportar.click(
                    baixar_playlist,
                    [estado, pastas],
                    [csv_download, pastas],
                    api_name='exportar_playlist',
                )
                criar_cartao.click(
                    baixar_cartao,
                    [estado, pastas],
                    [imagem, png_download, pastas],
                    api_name='gerar_cartao',
                )
            with gr.Tab('Match'):
                gr.HTML(
                    '<div class="su-section"><h3>Quem combina com quem?</h3>'
                    '<p>Junte amigos por histórico ZIP ou login no Spotify. O SyncUp compara todos com '
                    'todos, forma as duplas mais compatíveis e diz o que cada um pode apresentar ao outro.</p></div>'
                )
                with gr.Row(equal_height=True):
                    with gr.Column(elem_classes=['su-panel', 'a']):
                        gr.HTML(
                            '<div class="su-panel-title"><span class="su-avatar a">Z</span>Históricos ZIP</div>'
                        )
                        fm = gr.File(
                            file_count='multiple',
                            file_types=['.zip', '.json'],
                            type='filepath',
                            label='Um ZIP do Histórico Estendido por pessoa',
                        )
                        nm = gr.Textbox(lines=4, label='Nomes, um por linha, na ordem dos arquivos')
                    with gr.Column(elem_classes=['su-panel', 'b']):
                        gr.HTML(
                            '<div class="su-panel-title"><span class="su-avatar b">S</span>Login com Spotify · até 5 amigos</div>'
                        )
                        cid = gr.Textbox(
                            value=os.environ.get('SPOTIFY_CLIENT_ID', ''),
                            label='Client ID do seu app no Spotify',
                            placeholder='Cole aqui o Client ID do Developer Dashboard',
                        )
                        nome_sp = gr.Textbox(
                            label='Nome de quem vai entrar', placeholder='Ex.: Bia'
                        )
                        conectar = gr.Button('Conectar com Spotify', elem_classes='su-secondary')
                        salvos = gr.CheckboxGroup(
                            choices=perfis_salvos(),
                            value=perfis_salvos(),
                            label='Perfis coletados pelo Spotify',
                        )
                        recarregar = gr.Button('Atualizar lista', elem_classes='su-secondary')
                with gr.Accordion(
                    'Como configurar o login do Spotify (uma vez, ~5 min)', open=False
                ):
                    gr.HTML(
                        '<ol class="su-steps">'
                        '<li>Entre em <b>developer.spotify.com/dashboard</b> com uma conta <b>Premium</b> e crie um app (Web API).</li>'
                        f'<li>Em <b>Redirect URIs</b>, cadastre exatamente <code>{escape_html(REDIRECT_PADRAO)}</code>.</li>'
                        '<li>Em <b>User Management</b>, adicione o nome e o e-mail do Spotify de cada amigo (máximo 5).</li>'
                        '<li>Copie o <b>Client ID</b> para o campo acima (ou defina a variável <code>SPOTIFY_CLIENT_ID</code>).</li>'
                        '<li>Abra o SyncUp com <code>python app.py</code>. Cada amigo digita o nome, clica em <b>Conectar</b> e autoriza.</li>'
                        '</ol><p class="su-note">O login só funciona com o app aberto por <code>python app.py</code> neste '
                        'computador. Guardamos apenas os rankings num JSON local; o token não é salvo. '
                        'A API mostra favoritos (top 50 de ~4 semanas, ~6 meses e ~1 ano), não o histórico completo; '
                        'por isso os ZIPs são convertidos para os mesmos rankings antes de comparar.</p>'
                    )
                buscar = gr.Button(
                    'Encontrar os matches', variant='primary', elem_classes='su-play'
                )
                with gr.Column(visible=False, elem_classes='su-results') as match_resultados:
                    match_cartoes = gr.HTML()
                    match_plot = gr.Plot(show_label=False, elem_classes='su-chart')
                    match_ranking = gr.Dataframe(
                        interactive=False, wrap=True, label='Ranking de compatibilidade'
                    )
                conectar.click(
                    None,
                    [cid, nome_sp],
                    None,
                    js="(cid, nome) => { window.open('/spotify/login?client_id=' + "
                    "encodeURIComponent(cid || '') + '&nome=' + encodeURIComponent(nome || ''), "
                    "'_blank'); }",
                    api_name=False,
                )
                recarregar.click(atualizar_perfis, salvos, salvos, api_name=False)
                buscar.click(
                    executar_match,
                    [fm, nm, salvos, *opcoes],
                    [match_cartoes, match_plot, match_ranking, match_resultados],
                    api_name='encontrar_matches',
                    scroll_to_output=True,
                )
            with gr.Tab('Wrapped'):
                gr.HTML(
                    '<div class="su-section"><h3>Seu Wrapped da vida toda</h3>'
                    '<p>Envie o Histórico Estendido de uma pessoa (todas as partes) e veja a vida '
                    'inteira no Spotify em stories: artista e música da vida, anos, recordes, '
                    'relógio musical, hábitos e o seu arquétipo de escuta.</p></div>'
                )
                estado_w = gr.State(value=None, time_to_live=3600)
                pastas_w = gr.State(
                    value=[], time_to_live=3600, delete_callback=_limpar_exportacoes
                )
                with gr.Row(equal_height=True):
                    with gr.Column(elem_classes=['su-panel', 'a']):
                        nw = gr.Textbox(value='', label='Seu nome', placeholder='Ex.: Carlos')
                        fw = gr.File(
                            file_count='multiple',
                            file_types=['.zip', '.json'],
                            type='filepath',
                            label='Histórico completo (ZIP ou todos os JSONs)',
                        )
                    with gr.Column(min_width=260):
                        gerar_w = gr.Button(
                            'Gerar meu Wrapped', variant='primary', elem_classes='su-play'
                        )
                        demo_w = gr.Button(
                            'Testar com dados fictícios', elem_classes='su-secondary'
                        )
                        gr.Markdown(
                            'Usa as **Opções de dados** do topo (fuso e filtros). '
                            '"Vida toda" = todo o período do histórico enviado.',
                            elem_classes='su-note',
                        )
                with gr.Column(visible=False, elem_classes='su-results') as wrapped_resultados:
                    with gr.Row(elem_classes='su-wrapped-row'):
                        stories_w = gr.HTML()
                        detalhe_w = gr.HTML()
                    with gr.Row():
                        baixar_w = gr.Button(
                            'Baixar story do resumo · PNG 1080×1920', elem_classes='su-secondary'
                        )
                    with gr.Row():
                        imagem_w = gr.Image(
                            type='filepath', interactive=False, label='Prévia do story'
                        )
                        arquivo_w = gr.File(label='Baixar story PNG', interactive=False)
                gerar_w.click(
                    executar_wrapped,
                    [fw, nw, *opcoes],
                    [estado_w, stories_w, detalhe_w, wrapped_resultados, imagem_w, arquivo_w],
                    api_name='gerar_wrapped',
                    scroll_to_output=True,
                )
                demo_w.click(carregar_demo_wrapped, None, [fw, nw], api_name=False)
                baixar_w.click(
                    baixar_wrapped,
                    [estado_w, pastas_w],
                    [imagem_w, arquivo_w, pastas_w],
                    api_name='baixar_wrapped',
                )
            with gr.Tab('Grupo'):
                gr.Markdown(
                    f'Regras: top 2 artistas ≥{fmt_pct(LIMIAR_FAVORITOS)}; top 10 faixas ≥{fmt_pct(LIMIAR_REPEAT)}; '
                    f'madrugada 00h–05h59 ≥{fmt_pct(LIMIAR_MADRUGADA)}. As proporções aparecem na tabela. '
                    + AVISO_TRACOS,
                    elem_classes='su-note',
                )
                gr.Markdown(
                    'Cada arquivo desta aba representa **uma pessoa**. Se houver várias partes por pessoa, '
                    'use `comparar_grupo()` com `EntradaPerfil` pelo Python. Na matriz comum, todas as células usam a mesma janela global.',
                    elem_classes='su-note',
                )
                with gr.Row(equal_height=True):
                    with gr.Column(elem_classes=['su-panel', 'a']):
                        fg = gr.File(
                            file_count='multiple',
                            file_types=['.zip', '.json'],
                            type='filepath',
                            label='3 a 6 históricos · um arquivo por pessoa',
                        )
                    with gr.Column(elem_classes=['su-panel', 'b']):
                        ng = gr.Textbox(
                            lines=6, label='Um nome por linha, na mesma ordem dos arquivos'
                        )
                with gr.Row(equal_height=True):
                    cg = gr.Checkbox(value=True, label='Período comum a todos os perfis')
                    pg = gr.Dropdown(
                        choices=OPCOES_PONDERACAO,
                        value='bruta',
                        label='Ponderação do cosseno do grupo',
                    )
                    grupo = gr.Button('Comparar grupo', variant='primary', elem_classes='su-play')
                with gr.Column(visible=False, elem_classes='su-results') as grupo_resultados:
                    grupo_cartoes = gr.HTML()
                    grupo_texto = gr.Markdown(elem_classes='su-note')
                    grupo_plot = gr.Plot(show_label=False, elem_classes='su-chart')
                    grupo_matriz = gr.Dataframe(
                        interactive=False, label='Matriz · valores em percentual'
                    )
                    grupo_perfis = gr.Dataframe(
                        interactive=False, wrap=True, label='Perfis e arquétipos'
                    )
                    grupo_diag = gr.Dataframe(
                        interactive=False, wrap=True, label='Diagnóstico de cada perfil'
                    )
                grupo.click(
                    executar_grupo,
                    [fg, ng, cg, pg, *opcoes],
                    [
                        grupo_plot,
                        grupo_matriz,
                        grupo_perfis,
                        grupo_diag,
                        grupo_texto,
                        grupo_cartoes,
                        grupo_resultados,
                    ],
                    api_name='comparar_grupo',
                    scroll_to_output=True,
                )
        gr.Markdown(
            'Plays: ≥30 segundos. Horas e describe(): todas as execuções válidas. '
            'O Ruzicka usa pesos absolutos e é sensível ao volume de escuta. ' + AVISO_TRACOS,
            elem_classes='su-note',
        )
    return demo.queue(default_concurrency_limit=1)
