"""Entrada do SyncUp e reexportações compatíveis com imports da v0.4."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from analise import EntradaPerfil, ResultadoComparacao, ResultadoGrupo, comparar, comparar_grupo
from configuracao import ConfiguracaoCarga
from dados import LIMITE_BYTES, carregar, limpar_cache
from metricas import metricas

if TYPE_CHECKING:
    import gradio as gr

PORTA_PADRAO = int(os.environ.get('SYNCUP_PORTA', '7860'))

__all__ = [
    'carregar',
    'comparar',
    'metricas',
    'criar_interface',
    'limpar_cache',
    'ResultadoComparacao',
    'ConfiguracaoCarga',
    'ResultadoGrupo',
    'EntradaPerfil',
    'comparar_grupo',
]


def criar_interface() -> gr.Blocks:
    """Carrega a interface sob demanda, mantendo o núcleo independente dela."""
    from ui import criar_interface as construir

    return construir()


def criar_servidor():
    """FastAPI com a interface Gradio em /."""
    import gradio as gr
    from fastapi import FastAPI

    servidor = FastAPI(title='SyncUp')
    from ui.comum import CSS, HEAD, JS
    from ui.layout import _tema

    return gr.mount_gradio_app(
        servidor,
        criar_interface(),
        path='/',
        max_file_size=LIMITE_BYTES,
        theme=_tema(),
        css=CSS,
        js=JS,
        head=HEAD,
        footer_links=[],  # Sem "Usar via API · Construído com Gradio · Configurações".
    )


def executar(abrir_navegador: bool = True) -> None:
    """Sobe o servidor local em 127.0.0.1."""
    import threading
    import webbrowser

    import uvicorn

    url = f'http://127.0.0.1:{PORTA_PADRAO}/'
    if abrir_navegador:
        threading.Timer(2.0, webbrowser.open, args=(url,)).start()
    print(f'SyncUp rodando em {url}  (Ctrl+C para encerrar)')
    uvicorn.run(criar_servidor(), host='127.0.0.1', port=PORTA_PADRAO, log_level='warning')


if __name__ == '__main__':
    executar()
