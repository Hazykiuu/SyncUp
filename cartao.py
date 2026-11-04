"""Cartão PNG local em Pillow; fontes locais com fallback e nenhuma rede."""

from __future__ import annotations

import os
from functools import lru_cache
from itertools import islice
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from formatacao import fmt_num, fmt_pct
from perfis import LIMIAR_FAVORITOS, QUANTIDADE_FAVORITOS

if TYPE_CHECKING:
    from analise import ResultadoComparacao
    from conciliacao import Compatibilidade
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
    variante = 'DejaVuSans-Bold.ttf' if negrito else 'DejaVuSans.ttf'
    windows = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'
    # Figtree (OFL) do projeto logo após a fonte pedida: o PNG fica igual em qualquer sistema.
    candidatas = ([str(fonte)] if fonte else []) + [
        str(FIGTREE),
        f'/usr/share/fonts/truetype/dejavu/{variante}',
        str(windows / ('segoeuib.ttf' if negrito else 'segoeui.ttf')),
        '/System/Library/Fonts/Supplemental/Arial.ttf',
        variante,
    ]
    for candidata in candidatas:
        try:
            carregada = ImageFont.truetype(candidata, tamanho)
            if candidata == str(FIGTREE):
                carregada.set_variation_by_name('Bold' if negrito else 'Regular')
            return carregada
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


def _logo(d: ImageDraw.ImageDraw) -> None:
    """Disco preto com as quatro barras verdes, no canto superior esquerdo."""
    d.ellipse((64, 60, 144, 140), fill='#000000')
    for i, altura in enumerate((34, 50, 26, 42)):
        x = 82 + i * 12
        d.rounded_rectangle((x, 122 - altura, x + 7, 122), radius=3, fill=VERDE)


def _anel(d: ImageDraw.ImageDraw, caixa: tuple[int, int, int, int], proporcao: float) -> None:
    """Anel cinza preenchido em verde na proporção dada (limitada a 0–1)."""
    proporcao = max(0.0, min(1.0, proporcao))
    d.arc(caixa, 0, 360, fill='#3e3e3e', width=16)
    if proporcao > 0:
        d.arc(caixa, -90, -90 + 360 * proporcao, fill=VERDE, width=16)


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

    _logo(d)
    texto(168, 74, 'SyncUp', 48, TEXTO, True)
    texto(64, 175, 'O encontro dos seus históricos musicais', 30, SECUNDARIO)
    texto(64, 245, resultado.perfil_a.nome, 42, VERDE, True)
    texto(64, 306, '×  ' + resultado.perfil_b.nome, 42, ROXO, True)
    d.rounded_rectangle((64, 392, 1016, 620), radius=30, fill=PAINEL)
    texto(100, 415, 'SIMILARIDADE DE ESCUTA · COSSENO', 26, SECUNDARIO)
    texto(96, 455, fmt_pct(resultado.metricas.cosseno), 104, VERDE, True, 690)
    _anel(d, (812, 420, 984, 592), resultado.metricas.cosseno)  # à direita do painel
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


def gerar_cartao_match(
    compatibilidade: Compatibilidade, destino: str | Path, fonte: str | Path | None = None
) -> Path:
    """Story 1080×1920 de uma dupla do Match: pontuação, nível, artistas e estilo em comum."""
    c = compatibilidade
    story = _Story(VERDE, ROXO, fonte)
    story.cabecalho('SYNCUP MATCH')
    story.avatares([c.a, c.b], 470)
    story.centro(f'{c.a}  +  {c.b}', 700, 60, forte=True)
    story.centro(f'{fmt_num(c.pontuacao, 1)}%', 790, 230, forte=True)
    story.pilula(c.nivel.upper(), 1060)
    y = story.lista('VOCÊS DIVIDEM', c.artistas_comuns[:4] or ['Nenhum artista em comum'], 1180)
    if c.pontuacao_generos is not None:
        estilo = ', '.join(c.generos_comuns[:3]) or 'estilos diferentes'
        story.lista(f'NO ESTILO · {fmt_num(c.pontuacao_generos, 1)}%', [estilo], y)
    story.rodape('Compara os rankings musicais enviados. Não mede afinidade pessoal.')
    return story.salvar(destino)


class _Story:
    """Pôster 9:16 com fundo em degradê de duas cores, no estilo dos cartões da tela."""

    LARGURA, ALTURA = 1080, 1920

    def __init__(self, cor1: str, cor2: str, fonte: str | Path | None = None) -> None:
        self.fonte = fonte
        tamanho = (self.LARGURA, self.ALTURA)
        self.imagem = Image.new('RGB', tamanho, '#0c0c0c')
        # Duas manchas de luz: elipses desfocadas do tamanho da imagem, sem bordas duras.
        for cor, caixa, forca in (
            (cor1, (-420, -380, 900, 900), 215),
            (cor2, (180, 1050, 1500, 2300), 190),
        ):
            mascara = Image.new('L', tamanho, 0)
            ImageDraw.Draw(mascara).ellipse(caixa, fill=forca)
            mascara = mascara.filter(ImageFilter.GaussianBlur(220))
            self.imagem.paste(cor, (0, 0), mascara)
        escurecer = Image.linear_gradient('L').resize(tamanho)
        self.imagem.paste((0, 0, 0), (0, 0), escurecer.point(lambda v: round(v * 0.45)))
        self.d = ImageDraw.Draw(self.imagem)
        self.cores = (cor1, cor2)

    def _fonte(self, tamanho: int, forte: bool):
        return carregar_fonte(tamanho, forte, self.fonte)

    def centro(self, valor: str, y: int, tamanho: int, cor: str = TEXTO, forte=False) -> None:
        f = self._fonte(tamanho, forte)
        linha = _ajustar_texto(valor, self.LARGURA - 128, self.d, f)
        x = (self.LARGURA - self.d.textlength(linha, font=f)) / 2
        self.d.text((x, y), linha, fill=cor, font=f)

    def cabecalho(self, titulo: str) -> None:
        _logo(self.d)
        f = self._fonte(40, True)
        self.d.text((168, 80), titulo, fill=TEXTO, font=f, spacing=0)

    def avatares(self, nomes: list[str], y: int, raio: int = 120) -> None:
        passo = raio * 1.7
        inicio = self.LARGURA / 2 - passo * (len(nomes) - 1) / 2
        centros = [inicio + i * passo for i in range(len(nomes))]
        for i, cx in enumerate(centros):
            caixa = (cx - raio, y - raio, cx + raio, y + raio)
            self.d.ellipse(caixa, fill=self.cores[i % 2], outline='#0c0c0c', width=12)
        f = self._fonte(round(raio * 0.72), True)
        for nome, cx in zip(nomes, centros):  # letras depois dos círculos: nada fica coberto
            letras = ''.join(p[0] for p in nome.split()[:2] if p[:1].isalnum()).upper() or '?'
            w = self.d.textlength(letras, font=f)
            self.d.text((cx - w / 2, y - raio * 0.46), letras, fill='#000000', font=f)

    def pilula(self, valor: str, y: int) -> None:
        f = self._fonte(34, True)
        w = self.d.textlength(valor, font=f)
        x = (self.LARGURA - w) / 2
        self.d.rounded_rectangle((x - 34, y - 16, x + w + 34, y + 58), radius=40, fill='#000000')
        self.d.text((x, y), valor, fill=TEXTO, font=f)

    def lista(self, titulo: str, itens: list[str], y: int) -> int:
        """Painel com título e itens; devolve onde o próximo bloco pode começar."""
        # Painel translúcido: desenhado numa camada RGBA e combinado com o fundo.
        camada = Image.new('RGBA', self.imagem.size, (0, 0, 0, 0))
        caixa = (64, y, 1016, y + 90 + 64 * len(itens))
        ImageDraw.Draw(camada).rounded_rectangle(caixa, radius=36, fill=(0, 0, 0, 120))
        self.imagem = Image.alpha_composite(self.imagem.convert('RGBA'), camada).convert('RGB')
        self.d = ImageDraw.Draw(self.imagem)
        f = self._fonte(28, True)
        self.d.text((104, y + 32), titulo, fill=SECUNDARIO, font=f)
        for i, item in enumerate(itens):
            fi = self._fonte(44, i == 0)
            linha = _ajustar_texto(item, 870, self.d, fi)
            self.d.text((104, y + 82 + i * 64), linha, fill=TEXTO, font=fi)
        return caixa[3] + 28

    def rodape(self, aviso: str) -> None:
        self.centro(aviso, 1790, 26, SECUNDARIO)
        self.centro('SyncUp · código aberto', 1836, 28, TEXTO, forte=True)

    def salvar(self, destino: str | Path) -> Path:
        caminho = Path(destino)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        self.imagem.save(caminho, format='PNG', optimize=True)
        return caminho
