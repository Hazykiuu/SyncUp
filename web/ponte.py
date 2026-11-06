"""Ponte entre o app no navegador (Pyodide) e o núcleo do SyncUp.

Cada ação recebe caminhos no sistema de arquivos virtual e opções simples e devolve
só dados que viram JSON (texto, números, listas, HTML pronto e gráficos do Plotly).
Também roda no Python comum: os testes chamam as mesmas funções.
"""

from __future__ import annotations

import gc
import json
import math
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

import componentes
import stories
from analise import ResultadoComparacao, comparar
from apresentacao import (
    _configuracao,
    _diversidade,
    _wrapped_seguro,
    perfil_card,
    resumo_html,
    tabela_display,
    texto_periodo,
    wrapped_dupla_html,
)
from exportacoes import exportar_playlist
from formatacao import fmt_num
from wrapped import wrapped_de_arquivos

SAIDA = Path('/tmp/syncup-saida')
# shortcut: guarda só o último resultado (o app no navegador atende uma pessoa por aba);
# trocar por um dicionário por id se um dia houver mais de uma comparação aberta.
_ultimo: dict[str, Any] = {}


def _tabela(tabela: pd.DataFrame) -> dict[str, list]:
    """Tabela já formatada em pt-BR, como colunas + linhas (cada célula vira texto)."""
    exibicao = tabela_display(tabela)
    return {
        'colunas': [str(c) for c in exibicao.columns],
        'linhas': [
            ['' if v is None else str(v) for v in linha]
            for linha in exibicao.itertuples(index=False)
        ],
    }


def _grafico(figura: Any) -> dict:
    """Figura do Plotly como dicionário (o navegador desenha com plotly.js)."""
    return json.loads(figura.to_json())


def comparar_dupla(
    arquivos_a: list[str],
    arquivos_b: list[str],
    nome_a: str,
    nome_b: str,
    opcoes: dict | None = None,
) -> dict:
    """Ação ``comparar_dupla``: o mesmo cálculo da aba Dupla do Gradio, em dados simples."""
    # Sob demanda: o worker só baixa o plotly (9,9 MB) quando a Dupla é usada.
    from graficos import butterfly, evolucao_mensal, mapa_horarios, radar_tracos, slope_chart

    o = opcoes or {}
    config = _configuracao(
        o.get('fuso', ''),
        o.get('musicas', ''),
        o.get('artistas', ''),
        o.get('varios', 'manter'),
        False,  # sem cache em disco no navegador
        bool(o.get('deduplicar', False)),
    )
    _ultimo.pop('dupla', None)  # o resultado anterior não fica vivo durante o novo pico
    # Wrapped primeiro: o pico dele (histórico inteiro) não se soma ao da comparação (iOS ~350 MB).
    wa = _wrapped_seguro(arquivos_a, (nome_a or '').strip() or 'Pessoa A', config)
    wb = _wrapped_seguro(arquivos_b, (nome_b or '').strip() or 'Pessoa B', config)
    gc.collect()
    r = comparar(
        arquivos_a,
        arquivos_b,
        nome_a,
        nome_b,
        bool(o.get('comum', True)),
        configuracao=config,
        ponderacao=o.get('ponderacao') or 'bruta',
    )
    _ultimo['dupla'] = r
    a, b = r.perfil_a, r.perfil_b
    contribuicoes = r.contribuicoes.head(100).copy()
    contribuicoes['Contribuição ao cosseno'] = [
        fmt_num(float(x) * 100, 4) + ' p.p.' for x in contribuicoes['Contribuição ao cosseno']
    ]
    m = r.metricas
    return {
        'nomes': [a.nome, b.nome],
        'periodo': texto_periodo(r),
        'aviso': r.aviso,
        'metricas': {
            'cosseno': m.cosseno,
            'jaccard': m.jaccard,
            'jaccard_top20': m.jaccard_top20,
            'ruzicka': m.jaccard_ponderado,
        },
        'html': {
            'resumo': resumo_html(r),
            'perfis': [perfil_card(a, 'green', wa), perfil_card(b, 'violet', wb)],
            'sintonia': componentes.sintonia_html(r),
            'corrida': componentes.corrida_html(r),
            'listas': [
                componentes.lista_top(a.artistas, componentes.VERDE, f'Top artistas · {a.nome}'),
                componentes.lista_top(b.artistas, componentes.ROXO, f'Top artistas · {b.nome}'),
                componentes.lista_top(
                    a.musicas, componentes.VERDE, f'Top músicas · {a.nome}', musicas=True
                ),
                componentes.lista_top(
                    b.musicas, componentes.ROXO, f'Top músicas · {b.nome}', musicas=True
                ),
            ],
            'wrapped': wrapped_dupla_html(wa, wb),
        },
        'quase': {
            'artistas': r.momentos_artistas.total_pares,
            'musicas': r.momentos_musicas.total_pares,
        },
        'graficos': {
            'artistas': _grafico(butterfly(r)),
            'horarios': _grafico(mapa_horarios(r)),
            'tracos': _grafico(radar_tracos(r)),
            'rankings': _grafico(slope_chart(r)),
            'meses': _grafico(evolucao_mensal(r)),
        },
        'conexoes': {
            'comuns': r.artistas_comuns[:20],
            'so_a': r.exclusivos_a[:20],
            'so_b': r.exclusivos_b[:20],
        },
        'ponte': [
            {'de': de, 'para': para, 'artista': artista, 'plays': int(plays), 'link': link}
            for de, para, artista, plays, _participacao, link in r.ponte.itertuples(
                index=False, name=None
            )
        ],
        'tabelas': {
            'playlist': _tabela(r.playlist.head(500)),
            'contribuicoes': _tabela(contribuicoes),
            'diversidade': _tabela(_diversidade(r)),
            'estatisticas': _tabela(r.estatisticas),
            'diagnostico': _tabela(r.diagnostico),
            'quase_artistas': _tabela(r.momentos_artistas.exemplos),
            'quase_musicas': _tabela(r.momentos_musicas.exemplos),
        },
    }


def _resultado() -> ResultadoComparacao:
    if 'dupla' not in _ultimo:
        raise ValueError('Compare os históricos antes de baixar.')
    return _ultimo['dupla']


def cartao_dupla() -> str:
    """Ação ``gerar_cartao``: PNG do resultado da Dupla; devolve o caminho no sistema virtual."""
    from cartao import gerar_cartao  # Pillow sob demanda

    SAIDA.mkdir(parents=True, exist_ok=True)
    return str(gerar_cartao(_resultado(), SAIDA / 'SyncUp_cartao.png'))


def cartao_sintonia() -> str:
    """Ação ``baixar_sintonia``: story PNG da sintonia da Dupla."""
    from cartao import gerar_cartao_sintonia  # Pillow sob demanda

    SAIDA.mkdir(parents=True, exist_ok=True)
    return str(gerar_cartao_sintonia(_resultado(), SAIDA / 'SyncUp_sintonia.png'))


def playlist_dupla() -> str:
    """Ação ``exportar_playlist``: CSV protegido da playlist comum."""
    SAIDA.mkdir(parents=True, exist_ok=True)
    return str(exportar_playlist(_resultado(), SAIDA / 'SyncUp_playlist.csv'))


def wrapped(arquivos: list[str], nome: str, opcoes: dict | None = None) -> dict:
    """Ação ``executar_wrapped``: Wrapped da vida toda de uma pessoa (stories e arquétipos)."""
    o = opcoes or {}
    config = _configuracao(
        o.get('fuso', ''),
        o.get('musicas', ''),
        o.get('artistas', ''),
        o.get('varios', 'manter'),
        False,  # sem cache em disco no navegador
        bool(o.get('deduplicar', False)),
    )
    _ultimo.pop('wrapped', None)  # o anterior não fica vivo durante o novo pico
    w = wrapped_de_arquivos(arquivos, (nome or '').strip() or 'Você', config)
    _ultimo['wrapped'] = w
    return {
        'nome': w.nome,
        'stories': stories.stories_html(w),
        'arquetipos': stories.arquetipos_detalhe_html(w),
        'trilha': _trilha(w),
        'dados': _wrapped_json(w),
    }


def _simples(valor: Any) -> Any:
    """Converte para tipos que o JSON aceita: datas em ISO, NaN em None, numpy em Python."""
    if isinstance(valor, dict):
        return {str(k): _simples(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_simples(v) for v in valor]
    if valor is pd.NaT:
        return None
    if isinstance(valor, pd.Timestamp):
        return valor.isoformat()
    if hasattr(valor, 'item') and not isinstance(valor, (str, bytes)):
        valor = valor.item()  # numpy.int64, numpy.float64…
    if isinstance(valor, float) and not math.isfinite(valor):
        return None
    return valor


def _wrapped_json(w: Any) -> dict:
    """Contrato do Wrapped para o Preact: todos os campos do ``Wrapped`` em JSON puro.

    Os textos vão crus (sem escape HTML): o Preact escapa ao desenhar. Datas em ISO 8601.
    """
    return _simples(asdict(w))


def _trilha(w: Any) -> dict:
    """Candidatas de música de cada slide, ligadas ao dado dele, em ordem de preferência.

    ``{'faixa', 'artista'}`` é uma música certa; ``{'artista'}`` pede as mais famosas do artista
    (ordem do iTunes). O JS toca a primeira candidata ainda não tocada; ``fila`` cobre o resto.
    O JS só busca algo se a pessoa pedir som.
    """

    def musica(item: Any) -> dict | None:
        return {'faixa': item.nome, 'artista': item.artista} if item and item.artista else None

    def artista(nome: str) -> dict | None:
        return {'artista': nome} if nome else None

    def lista(*candidatas: dict | None) -> list[dict]:
        return [c for c in candidatas if c]

    tops = [musica(m) for m in w.top_musicas]
    ultimo = w.anos[-1] if w.anos else None
    slides = {
        'intro': lista(musica(ultimo.top_musica) if ultimo else None, *tops),
        'primeira': lista(musica(w.primeira_musica)),
        'artista': lista(artista(w.artista_vida.nome)),
        'top_artistas': lista(*(artista(a.nome) for a in w.top_artistas[1:3])),
        'top_musicas': lista(*tops),
        'anos': lista(musica(w.anos[0].top_musica) if w.anos else None),
        'descobertas': lista(
            artista(ultimo.top_artistas[0].nome) if ultimo and ultimo.top_artistas else None
        ),
        'recorde': lista(musica(w.repeticao_dia), artista(w.artista_dia_recorde)),
        'fiel': lista(artista(w.fiel.nome)),
    }
    return {
        'slides': {tipo: c for tipo, c in slides.items() if c},
        # Acabaram as mais ouvidas? Seguem as mais famosas dos top artistas, sem repetir.
        'fila': [m for m in tops[:10] if m] + lista(*(artista(a.nome) for a in w.top_artistas[:5])),
    }


def cartao_wrapped() -> str:
    """Ação ``baixar_wrapped``: story PNG 1080×1920 do Wrapped."""
    from cartao import gerar_cartao_wrapped  # Pillow sob demanda

    if 'wrapped' not in _ultimo:
        raise ValueError('Monte o Wrapped antes de baixar.')
    SAIDA.mkdir(parents=True, exist_ok=True)
    return str(gerar_cartao_wrapped(_ultimo['wrapped'], SAIDA / 'SyncUp_wrapped.png'))


def arquivos_demo(pasta: str = '/tmp/syncup-demo') -> dict:
    """Dois históricos fictícios pequenos, gerados no próprio aparelho (nenhum dado real)."""
    from tools.gerar_dados_falsos import Configuracao, gerar_zip

    destino = Path(pasta)
    destino.mkdir(parents=True, exist_ok=True)
    caminhos = []
    for nome, semente in (('demo_ana.zip', 41), ('demo_bruno.zip', 97)):
        arquivo = destino / nome
        if not arquivo.is_file():
            gerar_zip(arquivo, Configuracao(linhas=40_000, artistas=250, seed=semente))
        caminhos.append(str(arquivo))
    return {
        'a': caminhos[0],
        'b': caminhos[1],
        'nome_a': 'Ana (fictícia)',
        'nome_b': 'Bruno (fictício)',
    }
