"""Slides do Wrapped da vida toda, no formato de stories (9:16), em HTML puro.

O ``syncup.js`` transforma o bloco em um player (toque/clique para avançar,
barras de progresso, pausa e teclado). Sem JavaScript, os slides aparecem em
sequência. Todo texto vindo do histórico passa por ``escape_html``.
"""

from __future__ import annotations

from math import cos, pi, sin
from typing import TYPE_CHECKING

from arquetipos import AVISO_ARQUETIPOS, formatar_valor
from formatacao import escape_html, fmt_num, fmt_pct
from wrapped import Wrapped, data_br, mes_ano

if TYPE_CHECKING:
    from conciliacao import ResultadoConciliacao
    from recursos import Sintonia

FUNDOS = {
    'intro': ('#1ed760', '#0b3d20'),
    'primeira': ('#7b4ae2', '#1d0f45'),
    'artista': ('#ff6437', '#4a0f1f'),
    'top_artistas': ('#2d46b9', '#0d1640'),
    'top_musicas': ('#c13584', '#3b0b2c'),
    'anos': ('#0f7b6c', '#06302a'),
    'descobertas': ('#e8a600', '#4a2a00'),
    'recorde': ('#e22134', '#3d0710'),
    'relogio': ('#1e3264', '#05070f'),
    'maratona': ('#ff4632', '#3a0a00'),
    'fiel': ('#509bf5', '#0e2347'),
    'habitos': ('#8d67ab', '#251633'),
    'arquetipo': ('#1ed760', '#5b2ad6'),
    'resumo': ('#121212', '#121212'),
    'match_intro': ('#5b2ad6', '#120a33'),
    'match_par': ('#1ed760', '#0b3d20'),
    'match_trio': ('#ff6437', '#4a0f1f'),
    'sintonia': ('#f573a0', '#3b0b2c'),
    'fim': ('#1ed760', '#0b1f14'),  # resumos do Match e da sintonia, sem a faixa do Wrapped
}


def _e(texto: object) -> str:
    return escape_html(str(texto))


def _n(valor: float, casas: int = 0, sufixo: str = '') -> str:
    """Número com contagem animada (o valor final já está no texto)."""
    return (
        f'<b data-countup="{valor:.6f}" data-decimals="{casas}" data-suffix="{_e(sufixo)}">'
        f'{fmt_num(valor, casas)}{_e(sufixo)}</b>'
    )


def _slide(tipo: str, corpo: str) -> str:
    claro, escuro = FUNDOS[tipo]
    return (
        f'<section class="su-story s-{tipo}" style="--bg1:{claro};--bg2:{escuro}">'
        f'<div class="su-story-in">{corpo}</div></section>'
    )


def _a(conteudo: str, atraso: int = 0, tag: str = 'div', classe: str = '') -> str:
    """Elemento com entrada animada escalonada (``--d`` × 140 ms)."""
    return f'<{tag} class="su-a {classe}" style="--d:{atraso}">{conteudo}</{tag}>'


def _lista(itens: list[tuple[str, str, int]], maximo: int) -> str:
    """Lista numerada com barras proporcionais (nome, detalhe, plays)."""
    linhas = []
    for i, (nome, detalhe, plays) in enumerate(itens):
        largura = plays / maximo * 100 if maximo else 0
        sub = f'<small>{_e(detalhe)}</small>' if detalhe else ''
        linhas.append(
            f'<li class="su-a" style="--d:{i + 2}"><span class="su-rank">{i + 1}</span>'
            f'<span class="su-li-txt"><b>{_e(nome)}</b>{sub}'
            f'<i class="su-li-bar" style="--value:{largura:.1f}%"></i></span>'
            f'<em>{fmt_num(plays)}</em></li>'
        )
    return f'<ol class="su-story-list">{"".join(linhas)}</ol>'


def _relogio(plays_por_hora: list[int], pico: int) -> str:
    """Relógio radial de 24 barras; a hora de pico fica destacada."""
    maximo = max(plays_por_hora) or 1
    linhas = []
    for hora, valor in enumerate(plays_por_hora):
        angulo = (hora / 24) * 2 * pi - pi / 2
        r0, r1 = 34, 34 + 56 * valor / maximo
        x0, y0 = 100 + r0 * cos(angulo), 100 + r0 * sin(angulo)
        x1, y1 = 100 + r1 * cos(angulo), 100 + r1 * sin(angulo)
        classe = 'pico' if hora == pico else ''
        linhas.append(
            f'<line class="{classe}" x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" '
            f'pathLength="1" style="--d:{hora}"/>'
        )
    marcas = ''.join(
        f'<text x="{100 + 24 * cos(h / 24 * 2 * pi - pi / 2):.1f}" '
        f'y="{100 + 24 * sin(h / 24 * 2 * pi - pi / 2) + 3:.1f}">{h}h</text>'
        for h in (0, 6, 12, 18)
    )
    return f'<svg class="su-clock" viewBox="0 0 200 200" aria-hidden="true">{"".join(linhas)}{marcas}</svg>'


def _anel(proporcao: float | None, rotulo: str, atraso: int) -> str:
    """Pequeno anel de porcentagem para os hábitos."""
    if proporcao is None:
        return ''
    return (
        f'<div class="su-habit su-a" style="--d:{atraso}"><svg viewBox="0 0 64 64" aria-hidden="true">'
        '<circle class="bg" cx="32" cy="32" r="27" pathLength="100"/>'
        f'<circle class="fg" cx="32" cy="32" r="27" pathLength="100" style="--p:{proporcao * 100:.1f}"/></svg>'
        f'{_n(proporcao * 100, 0, "%")}<span>{_e(rotulo)}</span></div>'
    )


def stories_html(w: Wrapped) -> str:
    """Gera todos os slides do Wrapped de uma pessoa."""
    slides: list[str] = []
    anos_txt = f'{mes_ano(w.inicio)} → {mes_ano(w.fim)}'
    dias_inteiros = w.horas / 24

    slides.append(
        _slide(
            'intro',
            _a('<span class="su-kicker">SYNCUP WRAPPED · VIDA TODA</span>', 0)
            + _a(f'<h2>{_e(w.nome)},<br>sua vida no Spotify</h2>', 1)
            + _a(f'<p class="su-sub">{_e(anos_txt)}</p>', 2)
            + _a(f'<div class="su-mega">{_n(w.horas, 0)}<span>horas de música</span></div>', 3)
            + _a(
                f'<p>Isso dá <strong>{fmt_num(dias_inteiros, 1)} dias inteiros</strong> sem parar, '
                f'em {fmt_num(w.dias_com_musica)} dias com música.</p>',
                4,
            ),
        )
    )
    slides.append(
        _slide(
            'primeira',
            _a('<span class="su-kicker">LÁ NO COMEÇO</span>', 0)
            + _a('<h3>Tudo começou com</h3>', 1)
            + _a(f'<div class="su-big-name">{_e(w.primeira_musica.nome)}</div>', 2)
            + _a(f'<p class="su-sub">{_e(w.primeira_musica.artista)}</p>', 3)
            + _a(f'<p>em {_e(data_br(w.primeira_data))}, às {w.primeira_data:%H:%M}.</p>', 4),
        )
    )
    slides.append(
        _slide(
            'artista',
            _a('<span class="su-kicker">O ARTISTA DA SUA VIDA</span>', 0)
            + _a(f'<div class="su-avatar-xl">{_e(w.artista_vida.nome[:1].upper())}</div>', 1)
            + _a(f'<div class="su-big-name">{_e(w.artista_vida.nome)}</div>', 2)
            + _a(
                f'<div class="su-pair"><div>{_n(w.artista_vida.plays)}<span>plays</span></div>'
                f'<div>{_n(w.artista_vida.horas, 0)}<span>horas</span></div>'
                f'<div><b>{fmt_pct(w.participacao_artista_vida)}</b><span>de tudo</span></div></div>',
                3,
            )
            + _a(
                f'<p>Vocês se conheceram em <strong>{_e(mes_ano(w.descoberta_artista_vida))}</strong>.</p>',
                4,
            ),
        )
    )
    maximo_art = w.top_artistas[0].plays if w.top_artistas else 1
    slides.append(
        _slide(
            'top_artistas',
            _a('<span class="su-kicker">SEU TOP 5 DE TODOS OS TEMPOS</span>', 0)
            + _a('<h3>Artistas</h3>', 1)
            + _lista(
                [(a.nome, f'{fmt_num(a.horas, 0)} h', a.plays) for a in w.top_artistas], maximo_art
            ),
        )
    )
    maximo_mus = w.top_musicas[0].plays if w.top_musicas else 1
    slides.append(
        _slide(
            'top_musicas',
            _a('<span class="su-kicker">AS QUE MAIS TOCARAM</span>', 0)
            + _a('<h3>Músicas</h3>', 1)
            + _lista([(m.nome, m.artista, m.plays) for m in w.top_musicas[:5]], maximo_mus),
        )
    )
    if len(w.anos) > 1:
        maior = max((a.horas for a in w.anos), default=1) or 1
        ano_top = max(w.anos, key=lambda a: a.horas)
        linhas = ''.join(
            f'<li class="su-a" style="--d:{i + 2}"><span class="su-year">{a.ano}</span>'
            f'<span class="su-year-bar"><i style="--value:{a.horas / maior * 100:.1f}%"></i>'
            f'<small>{_e(a.top_artistas[0].nome) if a.top_artistas else "—"}</small></span>'
            f'<em>{fmt_num(a.horas, 0)} h</em></li>'
            for i, a in enumerate(w.anos)
        )
        slides.append(
            _slide(
                'anos',
                _a('<span class="su-kicker">ANO A ANO</span>', 0)
                + _a(f'<h3>{ano_top.ano} foi o seu ano mais musical</h3>', 1)
                + f'<ol class="su-years">{linhas}</ol>'
                + _a(
                    '<p class="su-foot">Barra: horas no ano · nome: artista nº 1 daquele ano.</p>',
                    len(w.anos) + 2,
                ),
            )
        )
        maior_desc = max((a.novos_artistas for a in w.anos), default=1) or 1
        curioso = max(w.anos, key=lambda a: a.novos_artistas)
        colunas = ''.join(
            f'<div class="su-col" style="--d:{i};--value:{a.novos_artistas / maior_desc * 100:.1f}%">'
            f'<i></i><em>{fmt_num(a.novos_artistas)}</em><span>{str(a.ano)[2:]}</span></div>'
            for i, a in enumerate(w.anos)
        )
        slides.append(
            _slide(
                'descobertas',
                _a('<span class="su-kicker">DESCOBERTAS</span>', 0)
                + _a(
                    f'<div class="su-mega">{_n(w.quantidade_artistas)}<span>artistas diferentes</span></div>',
                    1,
                )
                + _a(
                    f'<p>Seu ano mais curioso foi <strong>{curioso.ano}</strong>, '
                    f'com {fmt_num(curioso.novos_artistas)} artistas novos.</p>',
                    2,
                )
                + f'<div class="su-cols">{colunas}</div>',
            )
        )
    slides.append(
        _slide(
            'recorde',
            _a('<span class="su-kicker">O DIA MAIS MUSICAL</span>', 0)
            + _a(f'<div class="su-big-name">{_e(data_br(w.dia_recorde))}</div>', 1)
            + _a(
                f'<div class="su-mega">{_n(w.horas_dia_recorde, 1)}<span>horas em um único dia</span></div>',
                2,
            )
            + (
                _a(f'<p>Quem mais tocou: <strong>{_e(w.artista_dia_recorde)}</strong>.</p>', 3)
                if w.artista_dia_recorde
                else ''
            )
            + _a(
                f'<div class="su-callout">Em {_e(data_br(w.data_repeticao_dia))} você ouviu '
                f'<strong>{_e(w.repeticao_dia.nome)}</strong> ({_e(w.repeticao_dia.artista)}) '
                f'<strong>{fmt_num(w.repeticao_dia.plays)} vezes</strong>.</div>',
                4,
            ),
        )
    )
    periodos = ''.join(
        f'<div class="su-a" style="--d:{i + 4}"><b>{fmt_pct(v, 0)}</b><span>{_e(k)}</span></div>'
        for i, (k, v) in enumerate(w.periodos.items())
    )
    slides.append(
        _slide(
            'relogio',
            _a('<span class="su-kicker">SEU RELÓGIO MUSICAL</span>', 0)
            + _a(f'<h3>Seu horário de pico: {w.pico_hora}h</h3>', 1)
            + _a(_relogio(w.plays_por_hora, w.pico_hora), 2)
            + f'<div class="su-periods">{periodos}</div>'
            + _a(
                f'<p class="su-foot">Dia favorito: {_e(w.dia_semana_favorito)} · fuso {_e(w.fuso_horario)}</p>',
                8,
            ),
        )
    )
    slides.append(
        _slide(
            'maratona',
            _a('<span class="su-kicker">CONSTÂNCIA</span>', 0)
            + _a(
                f'<div class="su-mega su-fire">{_n(w.sequencia)}<span>dias seguidos ouvindo música</span></div>',
                1,
            )
            + _a(
                f'<p>De {_e(data_br(w.inicio_sequencia))} a {_e(data_br(w.fim_sequencia))}.</p>', 2
            )
            + _a(
                f'<p>No total, teve música em <strong>{fmt_num(w.dias_com_musica)}</strong> '
                f'dos {fmt_num(w.dias_periodo)} dias do seu histórico '
                f'({fmt_pct(w.dias_com_musica / max(w.dias_periodo, 1), 0)}).</p>',
                3,
            ),
        )
    )
    total_anos = len(w.anos)
    slides.append(
        _slide(
            'fiel',
            _a('<span class="su-kicker">FIDELIDADE</span>', 0)
            + _a('<h3>Presença mais constante no seu top 5</h3>', 1)
            + _a(f'<div class="su-big-name">{_e(w.fiel.nome)}</div>', 2)
            + _a(
                f'<p>Esteve no seu top 5 anual em <strong>{w.anos_fiel} de {total_anos} '
                f'ano{"s" if total_anos != 1 else ""}</strong>.</p>',
                3,
            )
            + _a(
                '<div class="su-dots">'
                + ''.join(
                    f'<span class="{"on" if a.ano in w.fiel_anos else ""}">{a.ano}</span>'
                    for a in w.anos
                )
                + '</div>',
                4,
            ),
        )
    )
    h = w.habitos
    aneis = (
        _anel(h.get('aleatorio'), 'no aleatório', 2)
        + _anel(h.get('pulos'), 'faixas puladas', 3)
        + _anel(h.get('fim_natural'), 'ouvidas até o fim', 4)
        + _anel(h.get('offline'), 'offline', 5)
    )
    if aneis:
        plataformas = ''.join(
            f'<li class="su-a" style="--d:{i + 6}"><span>{_e(nome)}</span>'
            f'<i style="--value:{v * 100:.1f}%"></i><em>{fmt_pct(v, 0)}</em></li>'
            for i, (nome, v) in enumerate(p for p in w.plataformas if p[1] >= 0.01)
        )
        slides.append(
            _slide(
                'habitos',
                _a('<span class="su-kicker">SEUS HÁBITOS</span>', 0)
                + _a('<h3>Como você ouve</h3>', 1)
                + f'<div class="su-habits">{aneis}</div>'
                + (f'<ul class="su-platforms">{plataformas}</ul>' if plataformas else ''),
            )
        )
    arq = w.arquetipos
    secundarios = ''.join(
        f'<span class="su-badge su-a" style="--d:{i + 5}">{_e(s.icone)} {_e(s.nome)}</span>'
        for i, s in enumerate(arq.secundarios)
    )
    quase = ''.join(
        f'<span class="su-badge quase su-a" style="--d:{i + 7}">quase {_e(q.nome)} · '
        f'{_e(formatar_valor(q.valor, "pct" if q.limiar < 1 else "num"))}</span>'
        for i, q in enumerate(arq.quase)
        if q.chave not in ('explorador',)
    )
    slides.append(
        _slide(
            'arquetipo',
            _a('<span class="su-kicker">SEU ARQUÉTIPO DE ESCUTA</span>', 0)
            + _a(f'<div class="su-emoji">{_e(arq.principal.icone)}</div>', 1, classe='su-reveal')
            + _a(f'<div class="su-big-name">{_e(arq.principal.nome)}</div>', 3)
            + _a(f'<p>{_e(arq.principal.explicacao)}</p>', 4)
            + (f'<div class="su-badges">{secundarios}{quase}</div>' if secundarios or quase else '')
            + _a(f'<p class="su-foot">{_e(AVISO_ARQUETIPOS)}</p>', 9),
        )
    )
    top_a = ''.join(f'<li>{_e(a.nome)}</li>' for a in w.top_artistas)
    top_m = ''.join(f'<li>{_e(m.nome)}</li>' for m in w.top_musicas[:5])
    slides.append(
        _slide(
            'resumo',
            _a(
                f'<div class="su-final-head"><span class="su-avatar-xl sm">{_e(w.nome[:1].upper())}</span>'
                f'<div><span class="su-kicker">SYNCUP WRAPPED</span><b>{_e(w.nome)}</b>'
                f'<small>{_e(anos_txt)}</small></div></div>',
                0,
            )
            + _a(
                f'<div class="su-final-grid"><div><span>Top artistas</span><ol>{top_a}</ol></div>'
                f'<div><span>Top músicas</span><ol>{top_m}</ol></div></div>',
                1,
            )
            + _a(
                f'<div class="su-final-stats"><div><span>Horas</span><b>{fmt_num(w.horas, 0)}</b></div>'
                f'<div><span>Artistas</span><b>{fmt_num(w.quantidade_artistas)}</b></div>'
                f'<div><span>Arquétipo</span><b>{_e(arq.principal.icone)} {_e(arq.principal.nome)}</b></div></div>',
                2,
            )
            + _a('<button type="button" class="su-replay">↺ Ver de novo</button>', 3),
        )
    )
    avisos = ''.join(f'<p class="su-note">{_e(a)}</p>' for a in w.avisos)
    return (
        f'<div class="su-stories" data-stories tabindex="0" aria-label="Wrapped de {_e(w.nome)}">'
        f'<div class="su-stories-frame">{"".join(slides)}</div></div>{avisos}'
    )


def arquetipo_html(w: Wrapped, classe: str = '') -> str:
    """Bloco de destaque do arquétipo da vida toda (usado nos cartões de identidade)."""
    arq = w.arquetipos
    badges = ''.join(
        f'<span class="su-badge">{_e(s.icone)} {_e(s.nome)}</span>' for s in arq.secundarios
    )
    return (
        f'<div class="su-arch {classe}"><span class="su-arch-emoji">{_e(arq.principal.icone)}</span>'
        f'<div><small>ARQUÉTIPO DA VIDA TODA</small><b>{_e(arq.principal.nome)}</b>'
        f'<p>{_e(arq.principal.explicacao)}</p>'
        + (f'<div class="su-badges">{badges}</div>' if badges else '')
        + '</div></div>'
    )


def arquetipos_detalhe_html(w: Wrapped) -> str:
    """Todas as regras avaliadas, com o valor da pessoa e o limiar (transparência)."""
    from arquetipos import REGRAS

    regras = {r.chave: r for r in REGRAS}
    linhas = []
    for i, a in enumerate(w.arquetipos.avaliados):
        regra = regras[a.chave]
        escala = max(regra.teto, a.valor) or 1
        valor_txt = formatar_valor(a.valor, regra.formato)
        limiar_txt = formatar_valor(regra.limiar, regra.formato)
        classe = 'on' if a.forca >= 1 else ''
        linhas.append(
            f'<li class="{classe}" style="--i:{i}"><span class="su-ad-ic">{_e(a.icone)}</span>'
            f'<span class="su-ad-name"><b>{_e(a.nome)}</b><small>{_e(a.explicacao)}</small></span>'
            f'<span class="su-ad-bar"><i style="--value:{min(a.valor / escala, 1) * 100:.1f}%"></i>'
            f'<u style="left:{regra.limiar / escala * 100:.1f}%" title="limiar"></u></span>'
            f'<em>{_e(valor_txt)}<small>limiar {_e(limiar_txt)}</small></em></li>'
        )
    return (
        '<div class="su-arch-detail"><h3>Todos os arquétipos avaliados</h3>'
        '<p class="su-note">A barra é o seu valor; o traço branco é o limiar da regra. '
        'Em verde, as regras atingidas.</p>'
        f'<ol>{"".join(linhas)}</ol><p class="su-note">{_e(AVISO_ARQUETIPOS)}</p></div>'
    )


def stories_match_html(
    r: ResultadoConciliacao, sintonias: dict[tuple[str, str], Sintonia] | None = None
) -> str:
    """Revelação animada das duplas do Match, no mesmo player do Wrapped.

    Com ``sintonias``, ganha o slide da dupla que mais ouviu a mesma música ao mesmo tempo.
    """
    from recursos import mais_sincronizada

    comparacoes = len(r.nomes) * (len(r.nomes) - 1) // 2
    slides = [
        _slide(
            'match_intro',
            _a('<span class="su-kicker">SYNCUP MATCH</span>', 0)
            + _a(f'<div class="su-mega">{_n(len(r.nomes))}<span>pessoas</span></div>', 1)
            + _a(f'<p>{_n(comparacoes)} comparações depois, chegou a hora.</p>', 2)
            + _a('<h3>Quem combina com quem?</h3>', 3),
        )
    ]
    for grupo in r.pares:
        internos = [r.par(x, y) for i, x in enumerate(grupo) for y in grupo[i + 1 :]]
        principal = max(internos, key=lambda c: c.pontuacao)
        media = sum(c.pontuacao for c in internos) / len(internos)
        comuns = ''.join(
            f'<span class="su-chip">{_e(a)}</span>' for a in principal.artistas_comuns[:4]
        )
        estilo = (
            _a(f'<p class="su-sub">No estilo: {fmt_num(principal.pontuacao_generos, 1)}%</p>', 6)
            if principal.pontuacao_generos is not None
            else ''
        )
        slides.append(
            _slide(
                'match_trio' if len(grupo) == 3 else 'match_par',
                _a(
                    '<span class="su-kicker">'
                    + ('O TRIO' if len(grupo) == 3 else 'A DUPLA')
                    + '</span>',
                    0,
                )
                + ''.join(
                    _a(f'<div class="su-big-name">{_e(nome)}</div>', 1 + i)
                    for i, nome in enumerate(grupo)
                )
                + _a(
                    f'<div class="su-mega">{_n(media, 1, "%")}<span>{_e(principal.nivel)}</span></div>',
                    4,
                )
                + (_a(f'<div class="su-badges">{comuns}</div>', 5) if comuns else '')
                + estilo,
            )
        )
    campea = mais_sincronizada(sintonias or {})
    if campea:
        x, y, s = campea
        musica = s.top_musicas[0] if s.top_musicas else None
        slides.append(
            _slide(
                'sintonia',
                _a('<span class="su-kicker">DUPLA MAIS SINCRONIZADA</span>', 0)
                + _a(f'<div class="su-big-name">{_e(x)}</div>', 1)
                + _a(f'<div class="su-big-name">{_e(y)}</div>', 2)
                + _a(f'<div class="su-mega">{_n(s.minutos)}<span>minutos juntos</span></div>', 3)
                + _a('<p>ouvindo a mesma música, no mesmo instante.</p>', 4)
                + (
                    _a(
                        f'<p class="su-sub">A música de vocês: {_e(musica[0])} · {_e(musica[1])}</p>',
                        5,
                    )
                    if musica
                    else ''
                ),
            )
        )
    linhas = ''.join(f'<li>{" + ".join(_e(n) for n in g)}</li>' for g in r.pares)
    slides.append(
        _slide(
            'fim',
            _a('<span class="su-kicker">RESUMO DO MATCH</span>', 0)
            + _a(
                f'<div class="su-final-grid"><div><span>Grupos</span><ol>{linhas}</ol></div></div>',
                1,
            )
            + _a(
                f'<div class="su-final-stats"><div><span>Média dos grupos</span>'
                f'<b>{fmt_num(r.pontuacao_media_pares, 1)}%</b></div></div>',
                2,
            )
            + _a(
                '<p class="su-foot">Compara os rankings musicais enviados. '
                'Não mede personalidade nem afinidade pessoal.</p>',
                3,
            )
            + _a('<button type="button" class="su-replay">↺ Ver de novo</button>', 4),
        )
    )
    return (
        '<div class="su-stories" data-stories tabindex="0" aria-label="Revelação do Match">'
        f'<div class="su-stories-frame">{"".join(slides)}</div></div>'
    )


def stories_sintonia_html(nome_a: str, nome_b: str, s: Sintonia, quase: int) -> str:
    """Stories da escuta simultânea: a mesma faixa tocando ao mesmo tempo para os dois."""
    a, b = _e(nome_a), _e(nome_b)
    if not s.momentos:
        slides = [
            _slide(
                'sintonia',
                _a('<span class="su-kicker">EM SINTONIA</span>', 0)
                + _a(f'<h2>{a} e {b}</h2>', 1)
                + _a('<p>Ainda não ouviram a mesma música ao mesmo tempo neste recorte.</p>', 2)
                + _a(
                    f'<div class="su-mega">{_n(quase)}<span>vezes quase juntos (até 1 h)</span></div>',
                    3,
                ),
            )
        ]
    else:
        primeira, longo = s.primeira, s.mais_longo
        musica, artista, vezes, minutos = s.top_musicas[0]
        slides = [
            _slide(
                'sintonia',
                _a('<span class="su-kicker">EM SINTONIA</span>', 0)
                + _a(f'<h2>{a} e {b}<br>ouviram juntos</h2>', 1)
                + _a(
                    f'<div class="su-mega">{_n(s.minutos, 0)}<span>minutos ao mesmo tempo</span></div>',
                    2,
                )
                + _a(
                    f'<p>Foram <strong>{fmt_num(len(s.momentos))} momentos</strong> com a mesma '
                    'música tocando para os dois, no mesmo instante.</p>',
                    3,
                ),
            ),
            _slide(
                'primeira',
                _a('<span class="su-kicker">A PRIMEIRA VEZ</span>', 0)
                + _a(f'<div class="su-big-name">{_e(primeira.musica)}</div>', 1)
                + _a(f'<p class="su-sub">{_e(primeira.artista)}</p>', 2)
                + _a(
                    f'<p>em {_e(data_br(primeira.inicio_local))}, às '
                    f'{primeira.inicio_local:%H:%M}.</p>',
                    3,
                ),
            ),
            _slide(
                'top_musicas',
                _a('<span class="su-kicker">A MÚSICA DE VOCÊS</span>', 0)
                + _a(f'<div class="su-big-name">{_e(musica)}</div>', 1)
                + _a(f'<p class="su-sub">{_e(artista)}</p>', 2)
                + _a(
                    f'<div class="su-pair"><div>{_n(vezes)}<span>vezes juntos</span></div>'
                    f'<div>{_n(minutos, 0)}<span>minutos</span></div></div>',
                    3,
                ),
            ),
            _slide(
                'relogio',
                _a('<span class="su-kicker">QUANDO VOCÊS SE ENCONTRAM</span>', 0)
                + _a(
                    f'<div class="su-mega">{s.hora_favorita}h<span>a hora favorita</span></div>', 1
                )
                + _a(
                    f'<p>e o dia que mais junta vocês é <strong>{_e(s.dia_favorito)}</strong>.</p>',
                    2,
                )
                + _a(
                    f'<p class="su-sub">Momento mais longo: {_e(longo.musica)}, '
                    f'{fmt_num(longo.minutos, 1)} min, em {_e(data_br(longo.inicio_local))}.</p>',
                    3,
                ),
            ),
        ]
    slides.append(
        _slide(
            'fim',
            _a('<span class="su-kicker">SYNCUP · EM SINTONIA</span>', 0)
            + _a(
                f'<div class="su-final-stats"><div><span>Minutos juntos</span>'
                f'<b>{fmt_num(s.minutos, 0)}</b></div><div><span>Momentos</span>'
                f'<b>{fmt_num(len(s.momentos))}</b></div><div><span>Quase juntos</span>'
                f'<b>{fmt_num(quase)}</b></div></div>',
                1,
            )
            + _a(
                '<p class="su-foot">Ao mesmo tempo = a mesma faixa tocando para os dois, com pelo '
                'menos 30 s em comum, pelo horário de fim e a duração de cada play.</p>',
                2,
            )
            + _a('<button type="button" class="su-replay">↺ Ver de novo</button>', 3),
        )
    )
    return (
        f'<div class="su-stories" data-stories tabindex="0" aria-label="Sintonia de {a} e {b}">'
        f'<div class="su-stories-frame">{"".join(slides)}</div></div>'
    )
