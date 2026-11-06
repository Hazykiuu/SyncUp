"""Dupla e Grupo: execução, apresentação, gráficos e downloads."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from tempfile import gettempdir
from typing import Any

import gradio as gr
import pandas as pd

import componentes
from analise import (
    EntradaPerfil,
    ResultadoComparacao,
    comparar,
    comparar_grupo,
)
from apresentacao import (  # noqa: F401 (reexportados para ui e para os testes)
    _celula,
    _diversidade,
    _layout_legado,
    _texto_ponte,
    _wrapped_seguro,
    apresentar,
    grafico_artistas,
    grafico_meses,
    perfil_card,
    resumo_html,
    resumo_markdown,
    tabela_display,
    texto_conexoes,
    texto_periodo,
    wrapped_dupla_html,
)
from cartao import gerar_cartao, gerar_cartao_sintonia
from configuracao import ConfiguracaoCarga
from exportacoes import exportar_playlist
from formatacao import fmt_horas, fmt_num, fmt_pct
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
    _configuracao,
    _em_pasta_temporaria,
    _linhas,
    falha,
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
