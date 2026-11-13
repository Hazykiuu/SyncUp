"""Ponte entre o app no navegador (Pyodide) e o núcleo do SyncUp.

Cada ação recebe caminhos no sistema de arquivos virtual e opções simples e devolve
só dados que viram JSON (texto, números, listas, HTML pronto e gráficos do Plotly).
Também roda no Python comum: os testes chamam as mesmas funções.
"""

from __future__ import annotations

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
    tabela_display,
    texto_periodo,
)
from exportacoes import exportar_playlist
from formatacao import fmt_num
from wrapped import wrapped_de_arquivos

SAIDA = Path('/tmp/syncup-saida')
LINHAS_TABELA = 20  # o app mostra uma amostra; a playlist inteira vai no CSV
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
    contribuicoes = r.contribuicoes.head(LINHAS_TABELA).copy()
    contribuicoes['Contribuição ao cosseno'] = [
        fmt_num(float(x) * 100, 4) + ' p.p.' for x in contribuicoes['Contribuição ao cosseno']
    ]
    m = r.metricas
    return {
        'nomes': [a.nome, b.nome],
        'periodo': texto_periodo(r),
        'aviso': r.aviso,
        'dupla': _dupla_json(r),
        'metricas': {
            'cosseno': m.cosseno,
            'jaccard': m.jaccard,
            'jaccard_top20': m.jaccard_top20,
            'ruzicka': m.jaccard_ponderado,
        },
        'html': {
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
            'playlist': _tabela(r.playlist.head(LINHAS_TABELA)),
            'contribuicoes': _tabela(contribuicoes),
            'diversidade': _tabela(_diversidade(r)),
            'estatisticas': _tabela(r.estatisticas),
            'diagnostico': _tabela(r.diagnostico),
            'quase_artistas': _tabela(r.momentos_artistas.exemplos),
            'quase_musicas': _tabela(r.momentos_musicas.exemplos),
        },
    }


def _dupla_json(r: ResultadoComparacao) -> dict:
    """Contrato dos stories da Dupla no app web: só dados, textos crus (o Preact escapa).

    Tudo sai do ``ResultadoComparacao``: quem são, o que têm em comum, o favorito de cada
    um, sugestões da ponte, os relógios e a sintonia. Datas em ISO 8601 (hora local de A).
    """
    perfis = (r.perfil_a, r.perfil_b)
    # Posição de cada artista no ranking da pessoa: plays e, no empate, ordem alfabética.
    posicoes = [
        {
            artista: i
            for i, (artista, _) in enumerate(
                sorted(p.contagens_artistas.items(), key=lambda kv: (-kv[1], kv[0])), 1
            )
        }
        for p in perfis
    ]

    def pessoa(p: Any) -> dict:
        por_hora = p.horarios.groupby('hora')['Reproduções'].sum().reindex(range(24), fill_value=0)
        return {
            'nome': p.nome,
            'plays': p.plays,
            'horas': p.horas,
            'artistas': p.quantidade_artistas,
            'plays_por_hora': por_hora.tolist(),
            'pico_hora': por_hora.idxmax(),  # empate: a hora mais cedo
        }

    def favorito(i: int) -> dict | None:
        """Artista nº 1 de uma pessoa e a posição dele no ranking da outra (None se ausente)."""
        if perfis[i].artistas.empty:
            return None
        nome, plays = perfis[i].artistas.iloc[0][['Artista', 'Reproduções']]
        return {'nome': nome, 'plays': plays, 'posicao_no_outro': posicoes[1 - i].get(nome)}

    apresentar: list[dict] = []
    for de in (r.perfil_a.nome, r.perfil_b.nome):
        linhas = r.ponte[r.ponte['De'] == de].head(2) if len(r.ponte) else r.ponte
        apresentar += [
            {'de': d, 'para': para, 'artista': artista, 'plays': plays, 'link': link}
            for d, para, artista, plays, _participacao, link in linhas.itertuples(
                index=False, name=None
            )
        ]
    return _simples(
        {
            'a': pessoa(r.perfil_a),
            'b': pessoa(r.perfil_b),
            'inicio': r.periodo.inicio,
            'fim': r.periodo.fim,
            'periodo_comum': r.periodo.comum,
            'match': r.metricas.cosseno,
            'total_comuns': len(r.artistas_comuns),
            'em_comum': [
                {
                    'nome': artista,
                    'plays_a': r.perfil_a.contagens_artistas.get(artista, 0),
                    'plays_b': r.perfil_b.contagens_artistas.get(artista, 0),
                }
                for artista in r.artistas_comuns[:3]
            ],
            'favoritos': [favorito(0), favorito(1)],
            'apresentar': apresentar,
            'sintonia': _sintonia_json(r),
            'trilha': _trilha_dupla(r, apresentar),
        }
    )


def _trilha_dupla(r: ResultadoComparacao, apresentar: list[dict]) -> dict:
    """Trilha dos stories da Dupla, no mesmo formato de ``_trilha`` (Wrapped): músicas em comum.

    A fonte é a playlist comum (as faixas que os dois ouviram, da mais ouvida pelos dois para a
    menos). Cada story pede a música ligada ao dado dele; a fila cobre o resto. São no máximo
    ~12 buscas no iTunes, e só os nomes de músicas e artistas em comum saem do aparelho.
    """
    comuns = [
        {'faixa': musica, 'artista': artista}
        for artista, musica in r.playlist[['Artista', 'Música']]
        .head(10)
        .itertuples(index=False, name=None)
    ]
    em_comum = r.artistas_comuns[:3]
    do_artista = [m for m in comuns if m['artista'] in em_comum]
    favoritos = [
        {'artista': p.artistas.iloc[0]['Artista']}
        for p in (r.perfil_a, r.perfil_b)
        if not p.artistas.empty
    ]
    s = r.sintonia
    juntos = (
        [{'faixa': s.top_musicas[0][0], 'artista': s.top_musicas[0][1]}]
        if s is not None and s.top_musicas
        else []
    )
    slides = {
        'abertura': comuns[:1],
        'em_comum': do_artista[:1] + [{'artista': a} for a in em_comum],
        'frente': favoritos,
        'apresentar': [{'artista': p['artista']} for p in apresentar],
        'relogios': comuns[1:2],
        'sintonia': juntos,
        'sintonia_musica': juntos,
        'poster': comuns[:1],
    }
    return {
        'slides': {tipo: c for tipo, c in slides.items() if c},
        # Acabaram as do story? Seguem as mais ouvidas em comum e, depois, os artistas em comum.
        'fila': comuns + [{'artista': a} for a in em_comum],
    }


def _sintonia_json(r: ResultadoComparacao) -> dict | None:
    """A mesma faixa tocando ao mesmo tempo para os dois; None se a sintonia não foi calculada."""
    s = r.sintonia
    if s is None:
        return None

    def momento(m: Any) -> dict | None:
        if m is None:
            return None
        return {
            'musica': m.musica,
            'artista': m.artista,
            'data': m.inicio_local.floor('s'),
            'minutos': m.minutos,
        }

    por_mes: list[list] = []
    if not s.por_mes.empty:
        # Meses sem sintonia também entram (zero): o intervalo entre os encontros aparece.
        meses = pd.period_range(s.por_mes.index[0], s.por_mes.index[-1], freq='M').strftime('%Y-%m')
        por_mes = [[mes, valor] for mes, valor in s.por_mes.reindex(meses, fill_value=0.0).items()]
    musica = None
    if s.top_musicas:
        nome, artista, vezes, minutos = s.top_musicas[0]
        musica = {'nome': nome, 'artista': artista, 'vezes': vezes, 'minutos': minutos}
    return {
        'minutos': s.minutos,
        'momentos': len(s.momentos),
        'quase': r.momentos_musicas.total_pares if r.momentos_musicas else 0,
        'primeira': momento(s.primeira),
        'mais_longo': momento(s.mais_longo),
        'musica': musica,
        'hora_favorita': s.hora_favorita,
        'dia_favorito': s.dia_favorito,
        'por_mes': por_mes,
    }


def _resultado() -> ResultadoComparacao:
    if 'dupla' not in _ultimo:
        raise ValueError('Compare os históricos antes de baixar.')
    return _ultimo['dupla']


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
    w = wrapped_de_arquivos(arquivos, (nome or '').strip() or 'Você', config)
    return {
        'nome': w.nome,
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
