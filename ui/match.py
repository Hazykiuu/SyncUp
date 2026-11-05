"""Aba Match: perfis salvos, conciliação, sintonia, festa e cartões."""

from __future__ import annotations

from itertools import combinations
from pathlib import Path
from typing import Any

import gradio as gr
import httpx
import pandas as pd

import componentes
import stories
from cartao import gerar_cartao_match
from conciliacao import conciliar
from convite import gerar_convite, ler_convite, separar_convites
from dados import (
    MAXIMO_HISTORICOS_CACHE,
    precarregar,
)
from festa import exportar_csv, exportar_xspf, playlist_festa
from formatacao import escape_html, fmt_num
from generos import ARQUIVO_CACHE as ARQUIVO_CACHE_GENEROS
from generos import ConsultaMusicBrainz, preencher_generos
from graficos import (
    matriz_conciliacao,
)
from listenbrainz import coletar_escutas_listenbrainz, coletar_perfil_listenbrainz
from perfil_gosto import (
    carregar_perfil,
    escutas_de_arquivos,
    listar_perfis,
    perfil_de_arquivos,
    tem_perfil_em_cache,
)
from recursos import Escutas, Sintonia, escutas, sintonia_do_par, sintonia_entre
from spotify_api import PASTA_PERFIS
from ui.comum import (
    _configuracao,
    _em_pasta_temporaria,
    _linhas,
)


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


def _mais_em_sintonia(sintonias: dict[tuple[str, str], Sintonia], nome: str) -> str:
    """Com quem a pessoa mais ouviu junto, para a tabela do Match."""
    juntos = [
        (s.minutos, y if x == nome else x) for (x, y), s in sintonias.items() if nome in (x, y)
    ]
    minutos, outro = max(juntos, default=(0.0, ''))
    return f'{outro} ({fmt_num(minutos, 0)} min)' if minutos > 0 else '—'


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
    codigos_convite: str = '',
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
        escutas_por_nome: dict[str, Escutas] = {}  # só quem tem histórico de escuta
        for arquivo, nome in entradas:
            perfil = perfil_de_arquivos(arquivo, nome, config)
            perfis.append(perfil)
            fontes[perfil.nome] = 'Histórico ZIP'
            escutas_por_nome[perfil.nome] = escutas_de_arquivos(arquivo, config)
        for nome in selecionados or []:
            perfil = carregar_perfil(PASTA_PERFIS / f'{nome}.json')
            perfis.append(perfil)
            fontes[perfil.nome] = f'Spotify · {perfil.coletado_em[:10]}'
        usuarios = _linhas(usuarios_listenbrainz)
        fora: list[str] = []
        sem_sintonia: list[str] = []
        for i, usuario in enumerate(usuarios):
            progress(0.6 + 0.05 * i / len(usuarios), desc=f'Lendo o ListenBrainz de {usuario}')
            try:
                perfil = coletar_perfil_listenbrainz(usuario)
            except ValueError as erro:  # usuário inexistente, sem estatísticas ou serviço ocupado
                fora.append(f'{usuario}: {erro}')
                continue
            except httpx.HTTPError:
                fora.append(f'{usuario}: o ListenBrainz não respondeu. Confira a internet.')
                continue
            perfis.append(perfil)
            fontes[perfil.nome] = 'ListenBrainz'
            try:
                escutas_por_nome[perfil.nome] = escutas(
                    coletar_escutas_listenbrainz(usuario, config.fuso_horario)
                )
            except (ValueError, httpx.HTTPError):  # sem listens: entra no Match, sem sintonia
                sem_sintonia.append(perfil.nome)
        for k, codigo in enumerate(separar_convites(codigos_convite), 1):
            try:
                perfil = ler_convite(codigo)
            except ValueError as erro:  # código cortado ou alterado: os demais continuam
                fora.append(f'Convite {k}: {erro}')
                continue
            perfis.append(perfil)
            fontes[perfil.nome] = 'Convite'
        if fora:
            # Um nome errado não derruba o Match: quem falhou fica de fora, com o motivo.
            gr.Warning('Ficaram de fora do Match · ' + ' · '.join(fora))
        if sem_sintonia:
            gr.Warning(
                'Os listens não vieram do ListenBrainz, então ficaram sem sintonia: '
                + ', '.join(sem_sintonia)
            )
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
        nomes_escuta = [n for n in r.nomes if n in escutas_por_nome]
        pares_escuta = list(combinations(nomes_escuta, 2))
        sintonias = {}
        for k, (x, y) in enumerate(pares_escuta):
            progress(0.8 + 0.19 * k / len(pares_escuta), desc=f'Sintonia de {x} e {y}')
            sintonias[(x, y)] = sintonia_entre(escutas_por_nome[x], escutas_por_nome[y])
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
                    'Mais em sintonia': _mais_em_sintonia(sintonias, nome),
                }
                for nome in r.nomes
            ]
        )
        progress(1, desc='Matches prontos')
        duplas = [par for g in r.pares for par in combinations(g, 2)]
        # Valor = índice: nomes são texto livre e não precisam ser separados de volta.
        opcoes_duplas = [(f'{x} × {y}', i) for i, (x, y) in enumerate(duplas)]
        return [
            componentes.match_html(r, fontes, sintonias),
            matriz_conciliacao(r),
            ranking,
            gr.Column(visible=True),
            stories.stories_match_html(r, sintonias),
            {'resultado': r, 'perfis': perfis, 'duplas': duplas, 'sintonias': sintonias},
            gr.Dropdown(choices=opcoes_duplas, value=0 if duplas else None),
        ]
    except ValueError as erro:
        raise gr.Error(str(erro)) from erro


def gerar_meu_convite(
    arquivos: list[str] | None,
    nome: str,
    perfil_salvo: str | None,
    fuso: str,
    musicas: str,
    artistas: str,
    varios: str,
    disco: bool,
    deduplicar: bool,
) -> str:
    """Código de convite a partir do ZIP da pessoa ou de um perfil salvo do Spotify."""
    try:
        if arquivos:
            if not (nome or '').strip():
                raise ValueError('Escreva o seu nome antes de gerar o código.')
            config = _configuracao(fuso, musicas, artistas, varios, disco, deduplicar)
            perfil = perfil_de_arquivos(list(arquivos), nome, config)
        elif perfil_salvo:
            if perfil_salvo not in perfis_salvos():  # nunca monta caminho com texto de fora
                raise ValueError('Esse perfil não está mais salvo. Clique em Atualizar lista.')
            perfil = carregar_perfil(PASTA_PERFIS / f'{perfil_salvo}.json')
        else:
            raise ValueError('Envie o seu ZIP ou escolha um perfil salvo do Spotify.')
        return gerar_convite(perfil)
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
    s = sintonia_do_par(match.get('sintonias', {}), a, b)
    arquivo, pasta = _em_pasta_temporaria(
        'match',
        lambda p: str(gerar_cartao_match(compatibilidade, p / 'SyncUp_match.png', sintonia=s)),
        'o cartão',
    )
    return arquivo, arquivo, [*(pastas or []), pasta]
