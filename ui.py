"""Apresentação do SyncUp no tema Spotify; consome os resultados estruturados de analise.py."""

from __future__ import annotations

import base64
import os
import shutil
from collections.abc import Callable
from functools import lru_cache
from itertools import combinations
from numbers import Real
from pathlib import Path
from tempfile import gettempdir, mkdtemp
from typing import Any
from zoneinfo import available_timezones

import gradio as gr
import httpx
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
from cartao import gerar_cartao, gerar_cartao_match, gerar_cartao_sintonia, gerar_cartao_wrapped
from conciliacao import conciliar
from configuracao import MUSICAS_IGNORADAS_PADRAO, ConfiguracaoCarga
from dados import (
    MAXIMO_HISTORICOS_CACHE,
    habilitar_leitura_paralela,
    precarregar,
)
from exportacoes import exportar_playlist
from festa import exportar_csv, exportar_xspf, playlist_festa
from formatacao import escape_html, escape_markdown, fmt_horas, fmt_num, fmt_pct, listar_markdown
from generos import ARQUIVO_CACHE as ARQUIVO_CACHE_GENEROS
from generos import ConsultaMusicBrainz, preencher_generos
from graficos import (
    butterfly,
    evolucao_mensal,
    mapa_horarios,
    matriz_conciliacao,
    matriz_grupo,
    radar_tracos,
    slope_chart,
)
from listenbrainz import coletar_perfil_listenbrainz
from perfil_gosto import carregar_perfil, listar_perfis, perfil_de_arquivos, tem_perfil_em_cache
from perfis import AVISO_TRACOS, LIMIAR_FAVORITOS, LIMIAR_MADRUGADA, LIMIAR_REPEAT
from spotify_api import PASTA_PERFIS, REDIRECT_PADRAO
from wrapped import Wrapped, wrapped_de_arquivos

PASTA = Path(__file__).resolve().parent
# Figtree (OFL) embutida no CSS: nenhuma requisição ao Google Fonts, funciona offline.
FONTE_CSS = (
    "@font-face{font-family:'Figtree';font-weight:300 900;font-display:swap;"
    'src:url(data:font/ttf;base64,'
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
    arquivo, pasta = _em_pasta_temporaria(
        'wrapped', lambda p: str(gerar_cartao_wrapped(w, p / 'SyncUp_Wrapped.png')), 'a imagem'
    )
    return arquivo, arquivo, [*(pastas or []), pasta]


def carregar_demo_wrapped() -> tuple[list[str], str]:
    """Um histórico fictício para experimentar o Wrapped."""
    a, _ = carregar_demo()[:2]
    return a, 'Ana (fictícia)'


def perfis_salvos() -> list[str]:
    """Nomes dos perfis coletados via login do Spotify (pasta perfis_spotify)."""
    return [p.stem for p in listar_perfis(PASTA_PERFIS)]


def atualizar_perfis(
    selecionados: list[str] | None, conhecidos: list[str] | None = None
) -> tuple[Any, list[str]]:
    """Recarrega a lista mantendo a seleção; quem acabou de logar já entra marcado."""
    opcoes = perfis_salvos()
    novos = [s for s in opcoes if s not in (conhecidos or [])]
    marcados = [s for s in opcoes if s in (selecionados or []) or s in novos] or opcoes
    return gr.CheckboxGroup(choices=opcoes, value=marcados), opcoes


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
    buscar_generos: bool = False,
    usuarios_listenbrainz: str = '',
    progress: gr.Progress = gr.Progress(),
) -> list[Any]:
    """Junta perfis de ZIP, ListenBrainz e Spotify, concilia todos e mostra os melhores pares."""
    try:
        arquivos = arquivos or []
        nomes_zip = list(_linhas(nomes))
        if arquivos and len(nomes_zip) != len(arquivos):
            raise ValueError('Informe um nome por arquivo ZIP, na mesma ordem dos arquivos.')
        config = _configuracao(fuso, musicas, artistas, varios, disco, deduplicar)
        perfis, fontes = [], {}
        entradas = list(zip(arquivos, nomes_zip))
        # Só lê o que ainda não virou perfil em cache, em blocos paralelos do tamanho do
        # cache de históricos (assim um bloco não descarta o anterior antes de ser usado).
        pendentes = [(a, n) for a, n in entradas if not tem_perfil_em_cache(a, config)]
        for j in range(0, len(pendentes), MAXIMO_HISTORICOS_CACHE):
            bloco = pendentes[j : j + MAXIMO_HISTORICOS_CACHE]
            precarregar([a for a, _ in bloco], config)
            for k, (arquivo, nome) in enumerate(bloco, j):
                progress(0.05 + 0.6 * k / len(pendentes), desc=f'Lendo o histórico de {nome}')
                perfil_de_arquivos(arquivo, nome, config)
        for arquivo, nome in entradas:
            perfis.append(perfil_de_arquivos(arquivo, nome, config))
            fontes[nome] = 'Histórico ZIP'
        for nome in selecionados or []:
            perfil = carregar_perfil(PASTA_PERFIS / f'{nome}.json')
            perfis.append(perfil)
            fontes[perfil.nome] = f'Spotify · {perfil.coletado_em[:10]}'
        for usuario in _linhas(usuarios_listenbrainz):
            progress(0.65, desc=f'Lendo o ListenBrainz de {usuario}')
            try:
                perfil = coletar_perfil_listenbrainz(usuario)
            except httpx.HTTPError as erro:
                raise ValueError(
                    f'Não foi possível falar com o ListenBrainz para {usuario}. Confira a internet.'
                ) from erro
            perfis.append(perfil)
            fontes[perfil.nome] = 'ListenBrainz'
        if buscar_generos:
            consulta = ConsultaMusicBrainz(
                cache=Path(config.diretorio_cache) / ARQUIVO_CACHE_GENEROS
            )
            try:
                for i, perfil in enumerate(perfis):
                    progress(0.65 + 0.1 * i / len(perfis), desc=f'Gêneros de {perfil.nome}')
                    perfis[i] = preencher_generos(perfil, consulta)
            finally:
                consulta.fechar()
            if consulta.falhas:
                gr.Warning(
                    'O MusicBrainz não respondeu (sem internet ou serviço ocupado). '
                    'O estilo foi calculado só com os gêneros já conhecidos.'
                )
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
        duplas = [par for g in r.pares for par in combinations(g, 2)]
        # Valor = índice: nomes são texto livre e não precisam ser separados de volta.
        opcoes_duplas = [(f'{x} × {y}', i) for i, (x, y) in enumerate(duplas)]
        return [
            componentes.match_html(r, fontes),
            matriz_conciliacao(r),
            ranking,
            gr.Column(visible=True),
            stories.stories_match_html(r),
            {'resultado': r, 'perfis': perfis, 'duplas': duplas},
            gr.Dropdown(choices=opcoes_duplas, value=0 if duplas else None),
        ]
    except ValueError as erro:
        raise gr.Error(str(erro)) from erro


def baixar_festa(match: dict | None, pastas: list[str] | None) -> tuple[str, list[str], list[str]]:
    """Playlist que cobre o gosto do grupo do último Match, em CSV e XSPF."""
    if not match:
        raise gr.Error('Encontre os matches antes de montar a playlist da festa.')
    faixas = playlist_festa(match['perfis'])
    if not faixas:
        raise gr.Error('Os perfis não têm músicas favoritas suficientes para a playlist.')
    arquivos, pasta = _em_pasta_temporaria(
        'festa',
        lambda p: [
            str(exportar_csv(faixas, p / 'SyncUp_festa.csv')),
            str(exportar_xspf(faixas, p / 'SyncUp_festa.xspf', 'SyncUp · Playlist da festa')),
        ],
        'a playlist',
    )
    linhas = ''.join(
        f'<li><a href="{escape_html(f.link)}" target="_blank" rel="noopener">'
        f'<b>{escape_html(f.musica)}</b> · {escape_html(f.artista)}</a>'
        f'<small>para {escape_html(", ".join(f.para))}</small></li>'
        for f in faixas
    )
    html = f'<ol class="su-festa">{linhas}</ol>'
    return html, arquivos, [*(pastas or []), pasta]


def baixar_cartao_match(
    match: dict | None, dupla: int | None, pastas: list[str] | None
) -> tuple[str, str, list[str]]:
    """Cartão PNG de uma dupla do último Match (``dupla`` é o índice em ``match['duplas']``)."""
    if not match or dupla is None:
        raise gr.Error('Encontre os matches e escolha uma dupla antes de gerar o cartão.')
    try:
        a, b = match['duplas'][int(dupla)]
    except (IndexError, ValueError, TypeError) as erro:
        raise gr.Error('Essa dupla não faz parte do último Match.') from erro
    compatibilidade = match['resultado'].par(a, b)
    arquivo, pasta = _em_pasta_temporaria(
        'match',
        lambda p: str(gerar_cartao_match(compatibilidade, p / 'SyncUp_match.png')),
        'o cartão',
    )
    return arquivo, arquivo, [*(pastas or []), pasta]


def baixar_cartao_sintonia(
    resultado: ResultadoComparacao | None, pastas: list[str] | None
) -> tuple[str, str, list[str]]:
    """Story PNG da escuta simultânea da dupla comparada."""
    if resultado is None:
        raise gr.Error('Faça uma comparação antes de gerar o story da sintonia.')
    arquivo, pasta = _em_pasta_temporaria(
        'sintonia',
        lambda p: str(gerar_cartao_sintonia(resultado, p / 'SyncUp_sintonia.png')),
        'o story',
    )
    return arquivo, arquivo, [*(pastas or []), pasta]


def _em_pasta_temporaria(prefixo: str, gerar: Callable[[Path], Any], o_que: str) -> tuple[Any, str]:
    """Gera exportações numa pasta própria do clique; apaga a pasta se a gravação falhar."""
    pasta = mkdtemp(prefix=f'syncup-{prefixo}-')
    try:
        return gerar(Path(pasta)), pasta
    except OSError as erro:
        shutil.rmtree(pasta, ignore_errors=True)
        raise gr.Error(f'Não foi possível gravar {o_que} no diretório temporário.') from erro


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
        raise gr.Error('Faça uma comparação antes de gerar o cartão.')
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


TOPO = """<header class="su-topbar">
  <div class="su-logo sm" aria-hidden="true"><i></i><i></i><i></i><i></i></div>
  <b>SyncUp</b><span class="su-topbar-tag">v0.95 · código aberto</span>
</header>"""

INICIO_TOPO = """<section class="su-hero">
  <div class="su-logo" aria-hidden="true"><i></i><i></i><i></i><i></i></div>
  <div class="su-hero-text">
    <small>SEUS HISTÓRICOS DO SPOTIFY, LADO A LADO</small>
    <h1>Descubra com quem<br>você está em sintonia.</h1>
    <p>Compare, encontre o seu match e poste o resultado. Tudo roda neste computador.</p>
  </div>
</section>
<h3 class="su-home-h">O que dá para fazer</h3>"""

INICIO_RODAPE = """<section class="su-steps-home">
  <h3 class="su-home-h">Como funciona</h3>
  <ol>
    <li><b>1</b><span><strong>Pegue seus dados</strong>O Histórico Estendido do Spotify (ZIP), um login ou o usuário do ListenBrainz.</span></li>
    <li><b>2</b><span><strong>Envie e aperte o play</strong>O SyncUp compara rankings, horários e hábitos.</span></li>
    <li><b>3</b><span><strong>Compartilhe</strong>Baixe o story 1080×1920 e poste.</span></li>
  </ol>
</section>
<section class="su-open">
  <span>🔒 100% local</span><span>MIT · código aberto</span><span>ListenBrainz e MusicBrainz</span>
  <a href="https://github.com/Hazykiuu/SyncUp" target="_blank" rel="noopener">Ver no GitHub →</a>
</section>"""

# Aba de destino, ícone, título, texto e cor de cada cartão do Início.
RECURSOS = [
    ('dupla', '🎧', 'Dupla', 'Blend, identidades e rankings de duas pessoas.', '#1ed760'),
    (
        'dupla',
        '💞',
        'Em sintonia',
        'Quando vocês ouviram a mesma música ao mesmo tempo.',
        '#f573a0',
    ),
    ('match', '✨', 'Match', 'Junte a galera e descubra as melhores duplas.', '#c4b7ff'),
    ('match', '🎉', 'Playlist da festa', 'Músicas que agradam o grupo inteiro.', '#ffa42b'),
    ('wrapped', '📼', 'Wrapped', 'A sua vida inteira no Spotify, em stories.', '#4cc9f0'),
    ('grupo', '👥', 'Grupo', 'Até 6 perfis comparados numa matriz.', '#e8db5a'),
]


def _cartao_recurso(icone: str, titulo: str, texto: str, cor: str) -> gr.Button:
    """Cartão de recurso do Início; devolve o botão que leva à aba."""
    with gr.Column(elem_classes='su-feature', min_width=240):
        gr.HTML(
            f'<div class="su-feature-in" style="--c:{cor}"><span class="su-feature-ico">{icone}</span>'
            f'<h4>{escape_html(titulo)}</h4><p>{escape_html(texto)}</p></div>'
        )
        return gr.Button('Abrir', elem_classes='su-secondary', size='sm')


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
        gr.HTML(TOPO)
        # Opções avançadas numa gaveta lateral fechada: a página mostra só o que encanta.
        with gr.Sidebar(label='Opções de dados', open=False, elem_classes='su-sidebar'):
            gr.HTML(
                '<div class="su-side-head"><b>Opções de dados</b>'
                '<span>Valem para todas as abas.</span></div>'
            )
            fuso = gr.Dropdown(
                sorted(available_timezones()), value='America/Sao_Paulo', label='Fuso horário IANA'
            )
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
                'Various Artists não identifica o intérprete real. Arquivos inteiros repetidos '
                'são rejeitados dentro do mesmo perfil.',
                elem_classes='su-note',
            )
            gr.Markdown(AVISO_TRACOS, elem_classes='su-note')
        opcoes = [fuso, ignorar_musicas, ignorar_artistas, varios, disco, deduplicar]
        with gr.Tabs(elem_classes='su-nav') as abas:
            with gr.Tab('Início', id='inicio'):
                gr.HTML(INICIO_TOPO)
                atalhos = []
                with gr.Row(elem_classes='su-features'):
                    for aba, icone, titulo, texto, cor in RECURSOS[:3]:
                        atalhos.append((aba, _cartao_recurso(icone, titulo, texto, cor)))
                with gr.Row(elem_classes='su-features'):
                    for aba, icone, titulo, texto, cor in RECURSOS[3:]:
                        atalhos.append((aba, _cartao_recurso(icone, titulo, texto, cor)))
                gr.HTML(INICIO_RODAPE)
            with gr.Tab('Dupla', id='dupla'):
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
                    with gr.Row(equal_height=True):
                        aa = gr.HTML()
                        ab = gr.HTML()
                    with gr.Tabs(elem_classes='su-subnav'):
                        with gr.Tab('Wrapped'):
                            wrapped_dupla = gr.HTML()
                        with gr.Tab('Em sintonia'):
                            momentos = gr.HTML()
                            with gr.Row():
                                sintonia_btn = gr.Button(
                                    'Gerar story da sintonia', elem_classes='su-secondary'
                                )
                            sintonia_img = gr.Image(show_label=False, interactive=False)
                            sintonia_arquivo = gr.File(label='Baixar story PNG', interactive=False)
                            with gr.Accordion('Quase juntos: até 1 h de distância', open=False):
                                gr.Markdown(
                                    'Pares de plays com até 1 h entre os horários de fim (UTC), '
                                    'sem repetir eventos. Os totais de artista e de música são '
                                    'alternativos, não somáveis. Até 200 exemplos por tabela.',
                                    elem_classes='su-note',
                                )
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
                        with gr.Tab('Rankings'):
                            corrida = gr.HTML()
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
                        with gr.Tab('Gráficos'):
                            _secao(
                                'Quem ouve quem',
                                'Participação dos artistas líderes nos plays de cada perfil.',
                            )
                            plot = gr.Plot(show_label=False, elem_classes='su-chart')
                            _secao('Horários e traços')
                            heatmap = gr.Plot(show_label=False, elem_classes='su-chart')
                            radar = gr.Plot(show_label=False, elem_classes='su-chart')
                            gr.Markdown(
                                f'Favoritos: top 2 ≥{fmt_pct(LIMIAR_FAVORITOS)}. Repeat: top 10 faixas ≥{fmt_pct(LIMIAR_REPEAT)}. '
                                f'Madrugada: 00h–05h59 ≥{fmt_pct(LIMIAR_MADRUGADA)}. Em amostras pequenas, top 10 tende a ser alto.',
                                elem_classes='su-note',
                            )
                            _secao('Onde vocês se diferenciam')
                            slope = gr.Plot(show_label=False, elem_classes='su-chart')
                            _secao('Mês a mês')
                            mensal = gr.Plot(show_label=False, elem_classes='su-chart')
                        with gr.Tab('Compartilhar'):
                            _secao('Cartão da dupla', 'PNG 1080×1350 gerado neste computador.')
                            criar_cartao = gr.Button('Gerar cartão PNG', elem_classes='su-play')
                            imagem = gr.Image(
                                type='filepath', interactive=False, label='Prévia do cartão'
                            )
                            png_download = gr.File(label='Baixar cartão PNG', interactive=False)
                            _secao('Ponte musical')
                            ponte = gr.Markdown()
                            _secao(
                                'Playlist em comum',
                                'Faixas que os dois ouviram. Os links abrem buscas no Spotify.',
                            )
                            playlist = gr.Dataframe(
                                interactive=False, wrap=True, label='Playlist comum · prévia'
                            )
                            exportar = gr.Button(
                                'Exportar playlist comum · CSV', elem_classes='su-secondary'
                            )
                            csv_download = gr.File(label='Baixar playlist CSV', interactive=False)
                    with gr.Accordion('Detalhes técnicos', open=False, elem_classes='su-tech'):
                        gr.Markdown(
                            'Contribuição por artista = aᵢ·bᵢ/(|a|·|b|); a soma é o cosseno, em '
                            'pontos percentuais e com a ponderação escolhida (100 líderes).',
                            elem_classes='su-note',
                        )
                        contrib = gr.Dataframe(
                            interactive=False, wrap=True, label='Contribuições ao cosseno'
                        )
                        gr.Markdown(
                            'Entropia = −Σp·ln(p)/ln(k); Gini = Σ(2i−k−1)xᵢ/(kΣx), com contagens '
                            'brutas dos artistas observados. Não medem diversidade de gêneros.',
                            elem_classes='su-note',
                        )
                        diversidade = gr.Dataframe(
                            interactive=False, label='Diversidade e desigualdade observadas'
                        )
                        stats = gr.Dataframe(
                            interactive=False, label='describe() · minutos por execução'
                        )
                        gr.Markdown(
                            'Descartes exclusivos: podcast → duração → data → identificação → '
                            'Various Artists → filtros → duplicados. SHA-256 identifica conteúdo, '
                            'não o dono.',
                            elem_classes='su-note',
                        )
                        diag = gr.Dataframe(interactive=False, wrap=True, label='Diagnóstico')
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
                sintonia_btn.click(
                    baixar_cartao_sintonia,
                    [estado, pastas],
                    [sintonia_img, sintonia_arquivo, pastas],
                    api_name='baixar_sintonia',
                )
            with gr.Tab('Match', id='match'):
                gr.HTML(
                    '<div class="su-section"><h3>Quem combina com quem?</h3>'
                    '<p>Junte a galera por qualquer fonte. O SyncUp compara todos com todos, '
                    'forma as duplas que mais combinam e gera pôsteres prontos para postar.</p></div>'
                )
                with gr.Row(equal_height=True, elem_classes='su-sources'):
                    with gr.Column(elem_classes=['su-panel', 'a']):
                        gr.HTML(
                            '<div class="su-panel-title"><span class="su-avatar a">Z</span>'
                            'Histórico ZIP<small>sem limite</small></div>'
                        )
                        fm = gr.File(
                            file_count='multiple',
                            file_types=['.zip', '.json'],
                            type='filepath',
                            label='Um ZIP do Histórico Estendido por pessoa',
                        )
                        nm = gr.Textbox(lines=3, label='Nomes, um por linha, na ordem dos arquivos')
                    with gr.Column(elem_classes=['su-panel', 'c']):
                        gr.HTML(
                            '<div class="su-panel-title"><span class="su-avatar c">L</span>'
                            'ListenBrainz<small>sem limite · só o usuário</small></div>'
                            '<p class="su-note">Código aberto. Crie uma conta grátis em '
                            '<a href="https://listenbrainz.org" target="_blank" rel="noopener">'
                            'listenbrainz.org</a> e conecte o Spotify uma vez em '
                            '<i>Settings → Music services</i>. Ninguém precisa de Client ID.</p>'
                        )
                        lb = gr.Textbox(
                            lines=3,
                            label='Usuários do ListenBrainz, um por linha',
                            placeholder='nicollas\nbia_musica',
                        )
                    with gr.Column(elem_classes=['su-panel', 'b']):
                        gr.HTML(
                            '<div class="su-panel-title"><span class="su-avatar b">S</span>'
                            'Login com Spotify<small>até 5 · cadastrados</small></div>'
                        )
                        nome_sp = gr.Textbox(
                            label='Nome de quem vai entrar', placeholder='Ex.: Bia'
                        )
                        conectar = gr.Button('Conectar com Spotify', elem_classes='su-secondary')
                        conhecidos = gr.State(value=perfis_salvos())
                        salvos = gr.CheckboxGroup(
                            choices=perfis_salvos(),
                            value=perfis_salvos(),
                            label='Perfis coletados pelo Spotify',
                        )
                        recarregar = gr.Button('Atualizar lista', elem_classes='su-secondary')
                        with gr.Accordion('Configurar (só quem criou o app)', open=False):
                            cid = gr.Textbox(
                                value=os.environ.get('SPOTIFY_CLIENT_ID', ''),
                                label='Client ID do app no Spotify',
                                placeholder='Cole o Client ID do Developer Dashboard',
                            )
                            gr.HTML(
                                '<ol class="su-steps">'
                                '<li>Em <b>developer.spotify.com/dashboard</b>, com conta '
                                '<b>Premium</b>, crie um app e marque só <b>Web API</b>.</li>'
                                f'<li>Redirect URI: <code>{escape_html(REDIRECT_PADRAO)}</code></li>'
                                '<li>Em <b>User Management</b>, cadastre o e-mail da conta '
                                'Spotify de cada amigo (máx. 5).</li>'
                                '<li>Cole o Client ID acima ou defina <code>SPOTIFY_CLIENT_ID</code>.'
                                '</li></ol><p class="su-note">Regra do Spotify para apps pessoais. '
                                'Sem cadastro, use o ListenBrainz ou o ZIP. O token nunca é salvo.</p>'
                            )
                generos_mb = gr.Checkbox(
                    value=False,
                    label='Comparar também o estilo (gêneros do MusicBrainz)',
                    info='Envia só nomes de artistas, 1 por segundo. Na 1ª vez, ~25 s por pessoa.',
                )
                buscar = gr.Button(
                    'Encontrar os matches', variant='primary', elem_classes='su-play'
                )
                estado_m = gr.State(value=None, time_to_live=3600)
                pastas_m = gr.State(
                    value=[], time_to_live=3600, delete_callback=_limpar_exportacoes
                )
                with gr.Column(visible=False, elem_classes='su-results') as match_resultados:
                    with gr.Tabs():
                        with gr.Tab('Revelação'):
                            match_stories = gr.HTML()
                        with gr.Tab('Duplas'):
                            match_cartoes = gr.HTML()
                        with gr.Tab('Todos com todos'):
                            match_plot = gr.Plot(show_label=False, elem_classes='su-chart')
                            match_ranking = gr.Dataframe(
                                interactive=False, wrap=True, label='Com quem cada um mais combina'
                            )
                        with gr.Tab('Playlist da festa'):
                            gr.Markdown(
                                'Até 30 músicas que cobrem o gosto de todo o grupo, equilibrando '
                                'quem ainda tem pouco. Baixe em CSV ou XSPF (formato aberto, abre '
                                'no VLC). Os links são buscas no Spotify.',
                                elem_classes='su-note',
                            )
                            festa_btn = gr.Button(
                                'Montar playlist da festa', elem_classes='su-secondary'
                            )
                            festa_lista = gr.HTML()
                            festa_arquivos = gr.File(
                                label='Baixar CSV e XSPF', file_count='multiple', interactive=False
                            )
                        with gr.Tab('Para postar'):
                            gr.Markdown(
                                'Story 1080×1920 para o Instagram, gerado neste computador.',
                                elem_classes='su-note',
                            )
                            dupla_m = gr.Dropdown(label='Escolha a dupla', choices=[])
                            cartao_m_btn = gr.Button(
                                'Gerar story da dupla', elem_classes='su-secondary'
                            )
                            cartao_m_img = gr.Image(show_label=False, interactive=False)
                            cartao_m_arquivo = gr.File(label='Baixar cartão PNG', interactive=False)
                conectar.click(
                    None,
                    [cid, nome_sp],
                    None,
                    js="(cid, nome) => { window.open('/spotify/login?client_id=' + "
                    "encodeURIComponent(cid || '') + '&nome=' + encodeURIComponent(nome || ''), "
                    "'_blank'); }",
                    api_name=False,
                )
                recarregar.click(
                    atualizar_perfis, [salvos, conhecidos], [salvos, conhecidos], api_name=False
                )
                # Cada aba nova do navegador vê os perfis salvos depois que o servidor subiu.
                demo.load(
                    atualizar_perfis, [salvos, conhecidos], [salvos, conhecidos], api_name=False
                )
                buscar.click(
                    executar_match,
                    [fm, nm, salvos, *opcoes, generos_mb, lb],
                    [
                        match_cartoes,
                        match_plot,
                        match_ranking,
                        match_resultados,
                        match_stories,
                        estado_m,
                        dupla_m,
                    ],
                    api_name='encontrar_matches',
                    scroll_to_output=True,
                )
                festa_btn.click(
                    baixar_festa,
                    [estado_m, pastas_m],
                    [festa_lista, festa_arquivos, pastas_m],
                    api_name='playlist_festa',
                )
                cartao_m_btn.click(
                    baixar_cartao_match,
                    [estado_m, dupla_m, pastas_m],
                    [cartao_m_img, cartao_m_arquivo, pastas_m],
                    api_name='baixar_cartao_match',
                )
            with gr.Tab('Wrapped', id='wrapped'):
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
            with gr.Tab('Grupo', id='grupo'):
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
        for aba, atalho in atalhos:
            atalho.click(lambda a=aba: gr.Tabs(selected=a), None, abas, api_name=False)
        gr.Markdown(
            'Plays: ≥30 segundos. Horas e describe(): todas as execuções válidas. '
            'O Ruzicka usa pesos absolutos e é sensível ao volume de escuta. ' + AVISO_TRACOS,
            elem_classes=['su-note', 'su-footer'],
        )
    return demo.queue(default_concurrency_limit=1)
