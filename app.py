"""Entrada do SyncUp e reexportações compatíveis com imports da v0.4."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from analise import EntradaPerfil, ResultadoComparacao, ResultadoGrupo, comparar, comparar_grupo
from configuracao import ConfiguracaoCarga
from dados import LIMITE_BYTES, carregar, limpar_cache
from metricas import metricas

if TYPE_CHECKING:
    import gradio as gr

PORTA_PADRAO = int(os.environ.get('SYNCUP_PORTA', '7860'))
# Pasta própria para os envios: o Gradio só apaga o que este processo criou, então o que sobrar de um
# encerramento à força fica para a limpeza ao abrir.
PASTA_ENVIOS = Path(tempfile.gettempdir()) / 'syncup-envios'
os.environ.setdefault('GRADIO_TEMP_DIR', str(PASTA_ENVIOS))

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


def apagar_envios_antigos() -> None:
    """Apaga o que ficou da última vez. Uma pasta escolhida por quem usa o PC não é tocada."""
    if Path(os.environ.get('GRADIO_TEMP_DIR', '')) != PASTA_ENVIOS or not PASTA_ENVIOS.is_dir():
        return
    for item in PASTA_ENVIOS.iterdir():
        if item.is_dir() and not item.is_symlink():
            shutil.rmtree(item, ignore_errors=True)
        else:
            item.unlink(missing_ok=True)


def porta_livre(porta: int) -> bool:
    """Com outro SyncUp aberto, os envios são dele."""
    import socket

    with socket.socket() as s:
        return s.connect_ex(('127.0.0.1', porta)) != 0


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

    if porta_livre(PORTA_PADRAO):
        apagar_envios_antigos()
    url = f'http://127.0.0.1:{PORTA_PADRAO}/'
    if abrir_navegador:
        threading.Timer(2.0, webbrowser.open, args=(url,)).start()
    print(f'SyncUp rodando em {url}  (Ctrl+C para encerrar)')
    uvicorn.run(criar_servidor(), host='127.0.0.1', port=PORTA_PADRAO, log_level='warning')


if __name__ == '__main__':
    executar()
