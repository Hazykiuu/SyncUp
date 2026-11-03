"""Entrada do SyncUp (v0.8) e reexportações compatíveis com imports da v0.4."""

from __future__ import annotations

from typing import TYPE_CHECKING

from analise import EntradaPerfil, ResultadoComparacao, ResultadoGrupo, comparar, comparar_grupo
from configuracao import ConfiguracaoCarga
from dados import carregar, limpar_cache
from metricas import metricas
from perfis import arquetipo

if TYPE_CHECKING:
    import gradio as gr

__all__ = [
    'carregar',
    'comparar',
    'metricas',
    'criar_interface',
    'limpar_cache',
    'ResultadoComparacao',
    'ConfiguracaoCarga',
    'arquetipo',
    'ResultadoGrupo',
    'EntradaPerfil',
    'comparar_grupo',
]


def criar_interface() -> gr.Blocks:
    """Carrega a interface sob demanda, mantendo o núcleo independente dela."""
    from ui import criar_interface as construir

    return construir()


def criar_servidor():
    """FastAPI com a interface Gradio em / e o login do Spotify em /spotify/*."""
    import gradio as gr
    from fastapi import FastAPI

    from spotify_api import registrar_rotas

    servidor = FastAPI(title='SyncUp')
    registrar_rotas(servidor)
    return gr.mount_gradio_app(servidor, criar_interface(), path='/')


def executar(abrir_navegador: bool = True) -> None:
    """Sobe o servidor local em 127.0.0.1 (a porta da Redirect URI do Spotify)."""
    import threading
    import webbrowser

    import uvicorn

    from spotify_api import PORTA_PADRAO

    url = f'http://127.0.0.1:{PORTA_PADRAO}/'
    if abrir_navegador:
        threading.Timer(2.0, webbrowser.open, args=(url,)).start()
    print(f'SyncUp rodando em {url}  (Ctrl+C para encerrar)')
    uvicorn.run(criar_servidor(), host='127.0.0.1', port=PORTA_PADRAO, log_level='warning')


if __name__ == '__main__':
    executar()
