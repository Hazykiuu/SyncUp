"""Constantes, CSS/JS e utilidades compartilhadas pelas telas do SyncUp."""

from __future__ import annotations

import base64
import shutil
from collections.abc import Callable
from pathlib import Path
from tempfile import mkdtemp
from typing import Any

import gradio as gr

from configuracao import ConfiguracaoCarga
from formatacao import fmt_num
from perfis import LIMIAR_FAVORITOS, LIMIAR_MADRUGADA, LIMIAR_REPEAT

PASTA = Path(__file__).resolve().parents[1]  # raiz do projeto (estilos, fontes)
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
# Pessoas em abas diferentes não esperam umas pelas outras; as leituras de histórico já são
# seguras em paralelo (travas em dados.py e perfil_gosto.py).


CONCORRENCIA = 4


HEAD = '<meta name="theme-color" content="#121212">'


def formatar(numero: int | float) -> str:
    """Formata contagens com separador de milhares brasileiro."""
    return fmt_num(numero)


def falha(mensagem: str) -> gr.Error:
    """Erro para ``raise``, com título em português (o do Gradio vem como "Error")."""
    return gr.Error(mensagem, title='Não deu certo')


def aviso(mensagem: str) -> None:
    gr.Warning(mensagem, title='Atenção')


def info(mensagem: str) -> None:
    gr.Info(mensagem, title='Pronto')


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


def _em_pasta_temporaria(prefixo: str, gerar: Callable[[Path], Any], o_que: str) -> tuple[Any, str]:
    """Gera exportações numa pasta própria do clique; apaga a pasta se a gravação falhar."""
    pasta = mkdtemp(prefix=f'syncup-{prefixo}-')
    try:
        return gerar(Path(pasta)), pasta
    except OSError as erro:
        shutil.rmtree(pasta, ignore_errors=True)
        raise falha(f'Não foi possível gravar {o_que} no diretório temporário.') from erro


def _limpar_exportacoes(pastas: list[str]) -> None:
    """Apaga apenas diretórios temporários criados para exportações desta sessão."""
    for pasta in pastas or []:
        shutil.rmtree(pasta, ignore_errors=True)
