"""Aba Meu Wrapped: execução, download e dados fictícios."""

from __future__ import annotations

from typing import Any

import gradio as gr

import stories
from cartao import gerar_cartao_wrapped
from ui.comum import (
    _configuracao,
    _em_pasta_temporaria,
)
from ui.dupla import (
    carregar_demo,
)
from wrapped import Wrapped, wrapped_de_arquivos


def executar_wrapped(
    arquivos: list[str] | None,
    nome: str,
    fuso: str,
    musicas: str,
    artistas: str,
    varios: str,
    disco: bool,
    deduplicar: bool,
    progress: gr.Progress = gr.Progress(),
) -> list[Any]:
    """Wrapped individual da vida toda: stories, detalhe dos arquétipos e estado para o PNG."""
    try:
        if not arquivos:
            raise ValueError('Selecione o histórico (ZIP ou JSONs) para montar o Wrapped.')
        progress(0.1, desc='Lendo o histórico completo')
        config = _configuracao(fuso, musicas, artistas, varios, disco, deduplicar)
        w = wrapped_de_arquivos(arquivos, nome, config)
        progress(0.8, desc='Montando os stories')
        saidas = [
            w,
            stories.stories_html(w),
            stories.arquetipos_detalhe_html(w),
            gr.Column(visible=True),
            None,
            None,
        ]
        progress(1, desc='Wrapped pronto')
        return saidas
    except ValueError as erro:
        raise gr.Error(str(erro)) from erro


def baixar_wrapped(w: Wrapped | None, pastas: list[str] | None) -> tuple[str, str, list[str]]:
    """Story PNG 1080×1920 com o resumo do Wrapped, em pasta temporária da sessão."""
    if w is None:
        raise gr.Error('Gere o Wrapped antes de baixar a imagem.')
    arquivo, pasta = _em_pasta_temporaria(
        'wrapped', lambda p: str(gerar_cartao_wrapped(w, p / 'SyncUp_Wrapped.png')), 'a imagem'
    )
    return arquivo, arquivo, [*(pastas or []), pasta]


def carregar_demo_wrapped() -> tuple[list[str], str]:
    """Um histórico fictício para experimentar o Wrapped."""
    a, _ = carregar_demo()[:2]
    return a, 'Ana (fictícia)'
