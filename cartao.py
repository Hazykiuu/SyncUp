"""Cartão PNG local em Pillow; fontes locais com fallback e nenhuma rede."""

from __future__ import annotations

import os
from functools import lru_cache
from itertools import islice
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

from formatacao import fmt_pct
from perfis import LIMIAR_FAVORITOS, QUANTIDADE_FAVORITOS

if TYPE_CHECKING:
    from analise import ResultadoComparacao
    from wrapped import Wrapped

LARGURA_CARTAO = 1080
ALTURA_CARTAO = 1350
FUNDO = '#121212'
PAINEL = '#1f1f1f'
TEXTO = '#ffffff'
SECUNDARIO = '#b3b3b3'
VERDE = '#1ed760'
ROXO = '#c4b7ff'
TOPO_GRADIENTE = (30, 215, 96)
FIGTREE = Path(__file__).resolve().parent / 'fontes' / 'Figtree.ttf'


def carregar_fonte(
    tamanho: int, negrito: bool = False, fonte: str | Path | None = None
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Tenta fonte indicada, DejaVu, fontes do Windows e fallback do Pillow.

    Cada combinação é aberta do disco uma única vez por processo.
    """
    return _carregar_fonte(tamanho, negrito, str(fonte) if fonte else None)


@lru_cache(maxsize=64)
def _carregar_fonte(
    tamanho: int, negrito: bool, fonte: str | None
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Implementação com cache de ``carregar_fonte``."""
    if fonte is None:
        try:
            # Figtree (OFL) do projeto: o PNG fica igual em qualquer sistema.
            figtree = ImageFont.truetype(str(FIGTREE), tamanho)
            figtree.set_variation_by_name('Bold' if negrito else 'Regular')
            return figtree
        except (OSError, ValueError):
            pass
    variante = 'DejaVuSans-Bold.ttf' if negrito else 'DejaVuSans.ttf'
    windows = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'
    candidatas = ([str(fonte)] if fonte else []) + [
        f'/usr/share/fonts/truetype/dejavu/{variante}',
        str(windows / ('segoeuib.ttf' if negrito else 'segoeui.ttf')),
        '/System/Library/Fonts/Supplemental/Arial.ttf',
        variante,
    ]
    for candidata in candidatas:
        try:
            return ImageFont.truetype(candidata, tamanho)
        except (OSError, ValueError):
            continue
    try:
        return ImageFont.load_default(size=tamanho)
    except TypeError:  # Compatibilidade com Pillow 10.0.
        return ImageFont.load_default()


def _ajustar_texto(
    texto: str,
    largura: int,
    desenho: ImageDraw.ImageDraw,
    fonte: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> str:
    """Limita cada linha visualmente, preservando o espaço reservado ao rodapé."""
    texto = ' '.join(str(texto).split())
    sufixo = '…'
    try:
        fonte.getmask(texto + sufixo)
    except UnicodeEncodeError:  # Fonte bitmap do fallback do Pillow 10.0.
        texto = texto.encode('latin-1', errors='replace').decode('latin-1')
        sufixo = '...'
    if desenho.textlength(texto, font=fonte) <= largura:
        return texto
    # Busca binária pelo maior prefixo que cabe: O(log n) medições em vez de O(n).
    baixo, alto = 0, len(texto)
    while baixo < alto:
        meio = (baixo + alto + 1) // 2
        if desenho.textlength(texto[:meio] + sufixo, font=fonte) <= largura:
            baixo = meio
        else:
            alto = meio - 1
    return texto[:baixo].rstrip() + sufixo


def gerar_cartao(
    resultado: ResultadoComparacao, destino: str | Path, fonte: str | Path | None = None
) -> Path:
    """Gera PNG 1080×1350 com dados da dupla e aviso de interpretação.

    Não contém identificadores do arquivo, IP, dispositivo ou timestamps de
    eventos. Compartilhar nomes é uma decisão de quem baixar o cartão.
    """
    imagem = Image.new('RGB', (LARGURA_CARTAO, ALTURA_CARTAO), FUNDO)
    d = ImageDraw.Draw(imagem)
    # Degradê verde no topo, como as capas de playlist do Spotify.
    fundo = (18, 18, 18)
    for y in range(560):
        t = (1 - y / 560) ** 1.6 * 0.55
        cor = tuple(round(f + (g - f) * t) for f, g in zip(fundo, TOPO_GRADIENTE))
        d.line((0, y, LARGURA_CARTAO, y), fill=cor)

    def texto(
        x: int,
        y: int,
        valor: str,
        tamanho: int = 30,
        cor: str = TEXTO,
        forte: bool = False,
        largura: int = 940,
    ) -> None:
        """Desenha uma linha com largura limitada e fonte carregada localmente."""
        f = carregar_fonte(tamanho, forte, fonte)
        d.text((x, y), _ajustar_texto(valor, largura, d, f), fill=cor, font=f)

    d.ellipse((64, 60, 144, 140), fill='#000000')
    for i, altura in enumerate((34, 50, 26, 42)):
        x = 82 + i * 12
        d.rounded_rectangle((x, 122 - altura, x + 7, 122), radius=3, fill=VERDE)
    texto(168, 74, 'SyncUp', 48, TEXTO, True)
    texto(64, 175, 'O encontro dos seus históricos musicais', 30, SECUNDARIO)
    texto(64, 245, resultado.perfil_a.nome, 42, VERDE, True)
    texto(64, 306, '×  ' + resultado.perfil_b.nome, 42, ROXO, True)
    d.rounded_rectangle((64, 392, 1016, 620), radius=30, fill=PAINEL)
    texto(100, 415, 'SIMILARIDADE DE ESCUTA · COSSENO', 26, SECUNDARIO)
    texto(96, 455, fmt_pct(resultado.metricas.cosseno), 104, VERDE, True, 690)
    # Anel de similaridade à direita do painel.
    proporcao = max(0.0, min(1.0, resultado.metricas.cosseno))
    caixa = (812, 420, 984, 592)
    d.arc(caixa, 0, 360, fill='#3e3e3e', width=16)
    if proporcao > 0:
        d.arc(caixa, -90, -90 + 360 * proporcao, fill=VERDE, width=16)
    texto(100, 580, f'Ponderação: {resultado.ponderacao} · plays ≥30 segundos', 24, SECUNDARIO)
    texto(64, 665, f'Artistas em comum · Jaccard: {fmt_pct(resultado.metricas.jaccard)}', 30)
    texto(
        64,
        715,
        f'Contagens em comum · Ruzicka: {fmt_pct(resultado.metricas.jaccard_ponderado)}',
        30,
    )
    texto(64, 790, 'ALGUNS ARTISTAS COMPARTILHADOS', 26, VERDE, True)
    artistas = list(islice(resultado.artistas_comuns, 3))
    for i, artista in enumerate(artistas or ['Nenhum artista comum neste recorte']):
        texto(64, 843 + i * 48, artista, 32)
    for y, perfil, cor in ((1000, resultado.perfil_a, VERDE), (1066, resultado.perfil_b, ROXO)):
        texto(64, y, f'{perfil.nome} · {perfil.arquetipos.favoritos.nome}', 26, cor)
        texto(
            64,
            y + 34,
            f'Top {QUANTIDADE_FAVORITOS}: {fmt_pct(perfil.arquetipos.favoritos.proporcao)} dos plays · limiar ≥{fmt_pct(LIMIAR_FAVORITOS)}',
            22,
            SECUNDARIO,
        )
    periodo = resultado.periodo
    faixa = (
        f'{periodo.inicio:%d/%m/%Y} a {periodo.fim:%d/%m/%Y}'
        if periodo.comum
        else 'Históricos completos'
    )
    texto(64, 1140, f'{faixa} · {periodo.fuso_horario}', 24, SECUNDARIO)
    d.line((64, 1195, 1016, 1195), fill='#53685d', width=2)
    texto(64, 1220, 'Regras experimentais de escuta. Não medem personalidade', 25, SECUNDARIO)
    texto(64, 1260, 'ou afinidade amorosa. Coincidência não comprova influência.', 25, SECUNDARIO)
    caminho = Path(destino)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    imagem.save(caminho, format='PNG', optimize=True)
    return caminho


def gerar_cartao_wrapped(
    wrapped: Wrapped, destino: str | Path, fonte: str | Path | None = None
) -> Path:
    """Story PNG 1080×1920 com o resumo do Wrapped da vida toda (sem rede)."""
    from formatacao import fmt_num
    from wrapped import mes_ano

    largura, altura = 1080, 1920
    imagem = Image.new('RGB', (largura, altura), FUNDO)
    d = ImageDraw.Draw(imagem)
    # Faixa verde (texto preto, contraste alto) que escurece levemente até a borda.
    for y in range(410):
        t = y / 410
        cor = tuple(round(a + (b - a) * t) for a, b in zip(TOPO_GRADIENTE, (22, 156, 72)))
        d.line((0, y, largura, y), fill=cor)

    def texto(x, y, valor, tamanho=34, cor=TEXTO, forte=False, limite=952):
        f = carregar_fonte(tamanho, forte, fonte)
        d.text((x, y), _ajustar_texto(valor, limite, d, f), fill=cor, font=f)

    d.ellipse((64, 72, 150, 158), fill='#000000')
    for i, alt in enumerate((36, 54, 28, 46)):
        x = 84 + i * 13
        d.rounded_rectangle((x, 140 - alt, x + 8, 140), radius=3, fill=VERDE)
    texto(176, 88, 'SyncUp Wrapped', 46, '#000000', True)
    texto(64, 220, wrapped.nome, 92, '#000000', True)
    texto(
        64,
        340,
        f'{mes_ano(wrapped.inicio)} → {mes_ano(wrapped.fim)} · vida toda',
        36,
        '#0b2e18',
        True,
    )
    texto(64, 430, fmt_num(wrapped.horas, 0), 190, VERDE, True)
    texto(70, 640, 'horas de música', 44, TEXTO, True)

    texto(64, 800, 'TOP ARTISTAS', 30, SECUNDARIO, True, 440)
    texto(560, 800, 'TOP MÚSICAS', 30, SECUNDARIO, True, 440)
    for i, artista in enumerate(wrapped.top_artistas[:5]):
        texto(64, 856 + i * 64, f'{i + 1}  {artista.nome}', 38, TEXTO, i == 0, 470)
    for i, musica in enumerate(wrapped.top_musicas[:5]):
        texto(560, 856 + i * 64, f'{i + 1}  {musica.nome}', 38, TEXTO, i == 0, 470)

    d.rounded_rectangle((64, 1220, 1016, 1500), radius=36, fill=PAINEL)
    texto(104, 1252, 'ARQUÉTIPO DE ESCUTA', 30, SECUNDARIO, True)
    texto(104, 1302, wrapped.arquetipos.principal.nome, 70, VERDE, True, 880)
    texto(104, 1400, wrapped.arquetipos.principal.explicacao, 30, TEXTO, False, 880)

    estatisticas = (
        ('Artistas', fmt_num(wrapped.quantidade_artistas)),
        ('Dias seguidos', fmt_num(wrapped.sequencia)),
        ('Pico', f'{wrapped.pico_hora}h'),
    )
    for i, (rotulo, valor) in enumerate(estatisticas):
        x = 64 + i * 330
        texto(x, 1560, rotulo.upper(), 28, SECUNDARIO, True, 300)
        texto(x, 1602, valor, 64, TEXTO, True, 300)
    d.line((64, 1740, 1016, 1740), fill='#3e3e3e', width=2)
    texto(
        64, 1770, 'Hábitos de escuta do histórico enviado. Não mede personalidade.', 28, SECUNDARIO
    )
    caminho = Path(destino)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    imagem.save(caminho, format='PNG', optimize=True)
    return caminho
