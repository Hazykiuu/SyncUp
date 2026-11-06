"""Constantes, CSS/JS e utilidades compartilhadas pelas telas do SyncUp."""

from __future__ import annotations

import base64
import shutil
from collections.abc import Callable
from pathlib import Path
from tempfile import mkdtemp
from typing import Any

import gradio as gr

from apresentacao import (  # noqa: F401 (reexportados para as telas)
    OPCOES_PONDERACAO,
    TEXTO_LIMIARES,
    _configuracao,
    _linhas,
    formatar,
)

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


# Pessoas em abas diferentes não esperam umas pelas outras; as leituras de histórico já são
# seguras em paralelo (travas em dados.py e perfil_gosto.py).


CONCORRENCIA = 4


HEAD = '<meta name="theme-color" content="#121212">'


def falha(mensagem: str) -> gr.Error:
    """Erro para ``raise``, com título em português (o do Gradio vem como "Error")."""
    return gr.Error(mensagem, title='Não deu certo')


def aviso(mensagem: str) -> None:
    gr.Warning(mensagem, title='Atenção')


def info(mensagem: str) -> None:
    gr.Info(mensagem, title='Pronto')


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
