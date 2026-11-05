"""Blocos HTML animados no tema Spotify; recebem resultados prontos e só apresentam.

Todo texto vindo dos arquivos passa por ``escape_html``. Os dados da corrida de
artistas vão em um atributo JSON escapado e são lidos pelo ``syncup.js``. Os
valores finais já estão no HTML: sem JavaScript, ou com movimento reduzido, a
página continua correta, apenas sem animação.
"""

from __future__ import annotations

import json
from math import pi
from typing import TYPE_CHECKING
from zlib import crc32

import pandas as pd

from formatacao import escape_html, fmt_horas, fmt_num, fmt_pct
from recursos import Sintonia, link_spotify, mais_sincronizada, sintonia_do_par

if TYPE_CHECKING:
    from analise import PerfilComparado, ResultadoComparacao, ResultadoGrupo
    from conciliacao import ResultadoConciliacao

VERDE = '#1ed760'
ROXO = '#c4b7ff'
CORES_GRUPO = [VERDE, ROXO, '#ffa42b', '#4cc9f0', '#f573a0', '#e8db5a']
RAIO_ANEL = 54
CIRCUNFERENCIA = 2 * pi * RAIO_ANEL
ARTISTAS_CORRIDA = 8


def _inicial(nome: str) -> str:
    """Até duas iniciais visíveis (primeira e última palavra), para os avatares circulares."""
    palavras = [p for p in (nome or '').split() if p[:1].isalnum()]
    if not palavras:
        return '?'
    letras = palavras[0][:1] + (palavras[-1][:1] if len(palavras) > 1 else '')
    return escape_html(letras.upper())


def _contador(valor: float, casas: int, sufixo: str = '') -> str:
    """Número final formatado, com atributos para a contagem animada no navegador."""
    return (
        f'<b data-countup="{valor:.6f}" data-decimals="{casas}" '
        f'data-suffix="{escape_html(sufixo)}">{fmt_num(valor, casas)}{escape_html(sufixo)}</b>'
    )


def _anel(proporcao: float) -> str:
    """Anel SVG animado com a proporção (0–1) como arco verde."""
    deslocamento = CIRCUNFERENCIA * (1 - max(0.0, min(1.0, proporcao)))
    return (
        '<svg class="su-ring" viewBox="0 0 128 128" aria-hidden="true">'
        '<defs><linearGradient id="suRingGrad" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0%" stop-color="{VERDE}"/><stop offset="100%" stop-color="{ROXO}"/>'
        '</linearGradient></defs>'
        f'<circle class="su-ring-bg" cx="64" cy="64" r="{RAIO_ANEL}"/>'
        f'<circle class="su-ring-fg" cx="64" cy="64" r="{RAIO_ANEL}" '
        f'style="--c:{CIRCUNFERENCIA:.2f};--off:{deslocamento:.2f}" '
        f'stroke-dasharray="{CIRCUNFERENCIA:.2f}" stroke-dashoffset="{deslocamento:.2f}"/>'
        '</svg>'
    )


def blend_html(resultado: ResultadoComparacao, texto_periodo: str) -> str:
    """Cabeçalho estilo "Blend": avatares, anel de similaridade e quatro métricas."""
    m, a, b = resultado.metricas, resultado.perfil_a, resultado.perfil_b
    cards = [
        ('Similaridade musical', m.cosseno, f'Cosseno · ponderação {resultado.ponderacao}'),
        ('Artistas em comum', m.jaccard, 'Jaccard · todos os artistas'),
        ('Favoritos compartilhados', m.jaccard_top20, 'Jaccard · Top 20'),
        ('Contagens compartilhadas', m.jaccard_ponderado, 'Ruzicka · ponderação selecionada'),
    ]
    metricas = ''.join(
        f'<div class="su-metric{" primary" if i == 0 else ""}" style="--i:{i}">'
        f'<small>{escape_html(titulo)}</small>{_contador(valor * 100, 1, "%")}'
        f'<div class="su-meter"><i style="--value:{valor * 100:.2f}%"></i></div>'
        f'<p>{escape_html(sub)}</p></div>'
        for i, (titulo, valor, sub) in enumerate(cards)
    )
    return f"""<section class="su-blend">
  <div class="su-blend-hero">
    <div class="su-avatars">
      <span class="su-avatar a" title="{escape_html(a.nome)}">{_inicial(a.nome)}</span>
      <span class="su-avatar b" title="{escape_html(b.nome)}">{_inicial(b.nome)}</span>
    </div>
    <div class="su-blend-text">
      <div class="su-eyebrow">BLEND DE HISTÓRICOS</div>
      <h2><span class="a">{escape_html(a.nome)}</span> <em>+</em> <span class="b">{escape_html(b.nome)}</span></h2>
      <p>{fmt_num(a.plays)} + {fmt_num(b.plays)} plays ≥30s · {len(resultado.artistas_comuns)} artistas em comum</p>
    </div>
    <div class="su-ring-wrap">{_anel(m.cosseno)}<div class="su-ring-label">{_contador(m.cosseno * 100, 0, '%')}<span>match</span></div></div>
  </div>
  <div class="su-metric-grid">{metricas}</div>
  <div class="su-note">{escape_html(texto_periodo)} · Similaridade calculada sobre o histórico de escuta.</div>
  <div class="su-note su-status">{escape_html(resultado.aviso)}</div>
</section>"""


def _barra(proporcao: float) -> str:
    """Trilho animado para um traço proporcional."""
    return f'<div class="su-track"><i style="--value:{max(0.0, min(1.0, proporcao)) * 100:.2f}%"></i></div>'


def lista_top(
    tabela: pd.DataFrame, cor: str, titulo: str, limite: int = 10, musicas: bool = False
) -> str:
    """Lista numerada estilo playlist: passa o mouse e o número vira ▶ (busca no Spotify)."""
    if tabela.empty:
        return f'<div class="su-tracklist-card"><h3>{escape_html(titulo)}</h3><p class="su-note">Sem dados neste recorte.</p></div>'
    linhas = tabela.head(limite)
    maximo = max(int(linhas['Reproduções'].max()), 1)
    if musicas:
        entradas = [
            (str(m), str(a), link_spotify(str(a), str(m)), int(p))
            for m, a, p in zip(linhas['musica'], linhas['artista'], linhas['Reproduções'])
        ]
    else:
        entradas = [
            (str(a), '', link_spotify(str(a)), int(p))
            for a, p in zip(linhas.iloc[:, 0], linhas['Reproduções'])
        ]
    itens = []
    for i, (principal, secundario, link, plays) in enumerate(entradas):
        tom = crc32(principal.encode('utf-8')) % 360
        itens.append(
            f'<li style="--i:{i}"><a href="{escape_html(link)}" target="_blank" rel="noopener noreferrer">'
            f'<span class="su-num">{i + 1}</span><span class="su-playicon" aria-hidden="true"></span>'
            f'<span class="su-cover" style="--hue:{tom}">{_inicial(principal)}</span>'
            f'<span class="su-meta"><b>{escape_html(principal)}</b>'
            + (f'<small>{escape_html(secundario)}</small>' if secundario else '')
            + '</span>'
            f'<span class="su-mini"><i style="--value:{plays / maximo * 100:.1f}%"></i></span>'
            f'<span class="su-count">{fmt_num(plays)}</span></a></li>'
        )
    return (
        f'<div class="su-tracklist-card" style="--accent:{cor}"><h3>{escape_html(titulo)}</h3>'
        f'<ol class="su-tracklist">{"".join(itens)}</ol></div>'
    )


def _serie_corrida(perfil: PerfilComparado, meses: list[int]) -> dict[str, object]:
    """Contagens acumuladas por mês dos artistas que chegam ao top em algum mês."""
    dados = perfil.artistas_por_mes
    if dados.empty:
        return {'nome': perfil.nome, 'artistas': [], 'valores': []}
    tabela = (
        dados.assign(artista=dados['artista'].astype(object))
        .pivot_table(
            index='ano_mes',
            columns='artista',
            values='Reproduções',
            aggfunc='sum',
            fill_value=0,
            observed=True,
        )
        .reindex(meses, fill_value=0)
        .cumsum()
    )
    selecionados: set[str] = set()
    for _, linha in tabela.iterrows():
        positivos = linha[linha > 0]
        selecionados.update(positivos.nlargest(ARTISTAS_CORRIDA).index)
    colunas = sorted(selecionados, key=lambda nome: (-int(tabela[nome].iloc[-1]), str(nome)))
    return {
        'nome': perfil.nome,
        'artistas': [str(x) for x in colunas],
        'valores': [[int(v) for v in tabela[nome].tolist()] for nome in colunas],
    }


def corrida_html(resultado: ResultadoComparacao) -> str:
    """Corrida animada dos artistas mais ouvidos, mês a mês, com controles de player."""
    a, b = resultado.perfil_a, resultado.perfil_b
    meses = sorted(
        set(a.artistas_por_mes.get('ano_mes', pd.Series(dtype='int64')).tolist())
        | set(b.artistas_por_mes.get('ano_mes', pd.Series(dtype='int64')).tolist())
    )
    if not meses:
        return '<p class="su-note">Sem meses suficientes para a corrida de artistas.</p>'
    dados = {
        'meses': [f'{m // 100:04d}-{m % 100:02d}' for m in meses],
        'topo': ARTISTAS_CORRIDA,
        'perfis': [
            {**_serie_corrida(a, meses), 'cor': VERDE, 'rotulo': 'A'},
            {**_serie_corrida(b, meses), 'cor': ROXO, 'rotulo': 'B'},
        ],
    }
    atributo = escape_html(json.dumps(dados, ensure_ascii=False, separators=(',', ':')))
    return (
        f'<div class="su-race" data-race="{atributo}">'
        '<p class="su-note">Corrida dos artistas: plays ≥30s acumulados mês a mês no recorte. '
        'Ative o JavaScript para ver a animação.</p></div>'
    )


def perfil_card(perfil: PerfilComparado, classe: str, limiares: str, destaque: str = '') -> str:
    """Cartão "Wrapped" de identidade musical com traços animados.

    ``destaque`` recebe o bloco do arquétipo da vida toda (``stories.arquetipo_html``).
    """
    arq = perfil.arquetipos
    tracos = ''.join(
        f'<div class="su-trait" style="--i:{i}"><div class="su-trait-title">'
        f'<strong>{escape_html(d.nome)}</strong><span>{fmt_pct(d.proporcao)}</span></div>'
        f'{_barra(d.proporcao)}<p>{escape_html(d.descricao)}</p></div>'
        for i, d in enumerate((arq.favoritos, arq.repeticao, arq.madrugada))
    )
    return f"""<article class="su-identity {classe}">
  <div class="su-identity-head"><span class="su-avatar {'a' if classe == 'green' else 'b'}">{_inicial(perfil.nome)}</span>
  <div><div class="su-eyebrow">IDENTIDADE MUSICAL</div><h2>{escape_html(perfil.nome or 'Perfil')}</h2></div></div>
  <div class="su-mini-stats">
    <div class="su-mini-stat">{_contador(perfil.plays, 0)}<span>plays ≥30s</span></div>
    <div class="su-mini-stat"><b>{fmt_horas(perfil.horas)}</b><span>horas · todas as execuções</span></div>
    <div class="su-mini-stat">{_contador(perfil.quantidade_artistas, 0)}<span>artistas</span></div>
  </div>
  {destaque}
  <div class="su-eyebrow su-traits-title">TRAÇOS NO PERÍODO COMPARADO</div>
  {tracos}
  <p class="su-rule-note">{escape_html(limiares)}</p>
</article>"""


def grupo_html(resultado: ResultadoGrupo, arquetipos: list[tuple[str, str]] | None = None) -> str:
    """Cartões por pessoa no Modo Grupo, com o par mais parecido em destaque.

    ``arquetipos``: (ícone, nome) do arquétipo da vida toda de cada perfil, na mesma ordem.
    """
    nomes = list(resultado.matriz.index)
    melhor, par = -1.0, ('', '')
    for i, x in enumerate(nomes):
        for y in nomes[i + 1 :]:
            valor = float(resultado.matriz.loc[x, y])
            if valor > melhor:
                melhor, par = valor, (x, y)
    cartoes = ''.join(
        f'<div class="su-group-card" style="--accent:{CORES_GRUPO[i % len(CORES_GRUPO)]};--i:{i}">'
        f'<span class="su-avatar" style="background:var(--accent)">{_inicial(p.nome)}</span>'
        f'<b>{escape_html(p.nome)}</b><small>{fmt_num(p.plays)} plays · {fmt_num(p.quantidade_artistas)} artistas</small>'
        + (
            f'<em class="su-arch-mini">{escape_html(arquetipos[i][0])} {escape_html(arquetipos[i][1])}</em>'
            if arquetipos and i < len(arquetipos)
            else f'<em>{escape_html(p.arquetipos.favoritos.nome)}</em>'
        )
        + '</div>'
        for i, p in enumerate(resultado.perfis)
    )
    destaque = (
        f'<div class="su-group-best"><span>Dupla mais sintonizada</span>'
        f'<b>{escape_html(par[0])} + {escape_html(par[1])}</b>{_contador(melhor * 100, 1, "%")}</div>'
        if melhor >= 0
        else ''
    )
    return (
        f'<section class="su-group">{destaque}<div class="su-group-grid">{cartoes}</div></section>'
    )


def _chips(nomes: list[str], limite: int, classe: str = '') -> str:
    return ''.join(
        f'<span class="su-chip {classe}" style="--i:{i}">{escape_html(n)}</span>'
        for i, n in enumerate(nomes[:limite])
    )


def _sintonia_linha(sintonias: dict[tuple[str, str], Sintonia], grupo: list[str]) -> str:
    """Minutos ouvindo junto dentro do grupo; vazio se alguém não tem histórico de escuta."""
    pares = [sintonia_do_par(sintonias, x, y) for i, x in enumerate(grupo) for y in grupo[i + 1 :]]
    if not pares or any(s is None for s in pares):
        return ''
    minutos = sum(s.minutos for s in pares)
    if minutos > 0:
        detalhe = (
            'somando os pares do trio' if len(grupo) == 3 else 'a mesma música, no mesmo instante'
        )
        valor = f'<b>{fmt_num(minutos, 0)} min</b><small>{detalhe}</small>'
    else:
        quase = sum(s.quase_juntos for s in pares)
        valor = (
            f'<b>{fmt_num(quase, 0)}×</b><small>quase juntos (até 1 h de distância)</small>'
            if quase
            else '<small>Ainda não ouviram nada ao mesmo tempo.</small>'
        )
    return f'<div class="su-poster-line su-poster-sync"><span>Em sintonia</span>{valor}</div>'


def match_html(
    resultado: ResultadoConciliacao,
    fontes: dict[str, str] | None = None,
    sintonias: dict[tuple[str, str], Sintonia] | None = None,
) -> str:
    """Pares escolhidos pela conciliação como pôsteres 4:5, prontos para print e post.

    ``sintonias``: escuta simultânea de cada par com histórico (``recursos.sintonia_entre``).
    """
    fontes, sintonias = fontes or {}, sintonias or {}
    cartoes = []
    for k, grupo in enumerate(resultado.pares):
        pares_internos = [resultado.par(x, y) for i, x in enumerate(grupo) for y in grupo[i + 1 :]]
        principal = max(pares_internos, key=lambda c: c.pontuacao)
        pontuacao = sum(c.pontuacao for c in pares_internos) / len(pares_internos)
        cores = [CORES_GRUPO[(k * 3 + i) % len(CORES_GRUPO)] for i in range(len(grupo))]
        avatares = ''.join(
            f'<span class="su-avatar" style="background:{cor}" title="{escape_html(n)}">'
            f'{_inicial(n)}</span>'
            for n, cor in zip(grupo, cores)
        )
        nomes = '<i>+</i>'.join(f'<span>{escape_html(n)}</span>' for n in grupo)
        selos = ' · '.join(
            f'{escape_html(n)}: {escape_html(fontes[n])}' for n in grupo if fontes.get(n)
        )
        trocas = ''
        if len(grupo) == 2:
            a, b = principal.a, principal.b
            trocas = (
                '<details class="su-swaps"><summary>O que um pode mostrar ao outro</summary>'
                f'<p><b>{escape_html(a)} → {escape_html(b)}</b></p>'
                f'<div class="su-chips">{_chips(principal.recomendacoes_para_b, 4, "rec")}</div>'
                f'<p><b>{escape_html(b)} → {escape_html(a)}</b></p>'
                f'<div class="su-chips">{_chips(principal.recomendacoes_para_a, 4, "rec")}</div>'
                '</details>'
            )
        comuns = principal.artistas_comuns
        estilo = ''
        if principal.pontuacao_generos is not None:
            estilo = (
                f'<div class="su-poster-line"><span>No estilo</span>'
                f'<b>{fmt_num(principal.pontuacao_generos, 1)}%</b>'
                f'<div class="su-chips">{_chips(principal.generos_comuns, 3)}</div></div>'
            )
        dividem = (
            f'<div class="su-poster-line"><span>Vocês dividem</span>'
            f'<div class="su-chips">{_chips(comuns, 4)}</div></div>'
            if comuns
            else '<p class="su-poster-sub">Nenhum artista em comum: ótimo para sair da bolha.</p>'
        )
        rotulo = 'O TRIO' if len(grupo) == 3 else f'DUPLA {k + 1}'
        cartoes.append(
            f'<article class="su-match-card" style="--i:{k};--c1:{cores[0]};--c2:{cores[1]}">'
            f'<div class="su-poster-kicker"><span>SYNCUP MATCH</span><span>{rotulo}</span></div>'
            f'<div class="su-avatars">{avatares}</div>'
            f'<h3 class="su-poster-names">{nomes}</h3>'
            f'<div class="su-poster-score">{_contador(pontuacao, 1, "%")}'
            f'<span>{escape_html(principal.nivel)}</span></div>'
            f'<p class="su-poster-sub">{escape_html(principal.descricao)}</p>'
            + dividem
            + estilo
            + _sintonia_linha(sintonias, list(grupo))
            + trocas
            + (f'<small class="su-src">{selos}</small>' if selos else '')
            + '</article>'
        )
    media = resultado.pontuacao_media_pares
    campea = mais_sincronizada(sintonias)
    premio = (
        '<div class="su-group-best su-sync-award"><span>Dupla mais sincronizada</span>'
        f'<b>{escape_html(campea[0])} + {escape_html(campea[1])}</b>'
        f'{_contador(campea[2].minutos, 0, " min")}'
        '<small class="su-note">ouvindo a mesma música ao mesmo tempo</small></div>'
        if campea
        else ''
    )
    divisao = 'duplas' if all(len(g) == 2 for g in resultado.pares) else 'duplas e um trio'
    return (
        '<section class="su-match">'
        f'<div class="su-group-best"><span>Melhor divisão do grupo em {divisao}</span>'
        f'<b>{len(resultado.nomes)} pessoas · {len(resultado.pares)} grupo'
        f'{"s" if len(resultado.pares) != 1 else ""}</b>'
        f'{_contador(media, 1, "%")}<small class="su-note">compatibilidade média dos grupos</small>'
        '</div>' + premio + f'<div class="su-match-grid">{"".join(cartoes)}</div>'
        '</section>'
    )


def sintonia_html(resultado: ResultadoComparacao) -> str:
    """Stories da sintonia e a linha do tempo mês a mês dos minutos ouvidos juntos."""
    import stories

    s = resultado.sintonia
    quase = resultado.momentos_musicas.total_pares if resultado.momentos_musicas else 0
    a, b = resultado.perfil_a.nome, resultado.perfil_b.nome
    linha = ''
    if s is not None and not s.por_mes.empty:
        # Meses sem sintonia também aparecem (barra vazia): o intervalo entre encontros é visível.
        meses = pd.period_range(s.por_mes.index[0], s.por_mes.index[-1], freq='M').strftime('%Y-%m')
        por_mes = s.por_mes.reindex(meses, fill_value=0.0)
        maximo = float(por_mes.max()) or 1.0
        barras = ''.join(
            f'<li style="--h:{valor / maximo:.3f};--i:{i}" title="{escape_html(mes)}: '
            f'{fmt_num(valor, 0)} min">'
            + (
                f'<span>{escape_html(mes[5:])}/{escape_html(mes[2:4])}</span>'
                if i == 0 or mes.endswith('-01')
                else ''
            )
            + '</li>'
            for i, (mes, valor) in enumerate(por_mes.items())
        )
        linha = (
            '<div class="su-sync-timeline"><h4>Quando a sintonia aconteceu</h4>'
            f'<ol aria-label="Minutos juntos por mês">{barras}</ol></div>'
        )
    corpo = stories.stories_sintonia_html(a, b, s, quase) if s is not None else ''
    return f'<section class="su-sync"><div class="su-sync-story">{corpo}</div>{linha}</section>'
