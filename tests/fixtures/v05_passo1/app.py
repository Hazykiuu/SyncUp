"""Entrada do SyncUp v0.5 e reexportações compatíveis com imports da v0.4."""
from __future__ import annotations
from typing import TYPE_CHECKING

from analise import ResultadoComparacao, comparar
from dados import carregar, limpar_cache
from metricas import metricas
from perfis import arquetipo

if TYPE_CHECKING:
    import gradio as gr

__all__ = ['carregar', 'comparar', 'metricas', 'criar_interface', 'limpar_cache',
           'ResultadoComparacao', 'arquetipo']


def criar_interface() -> gr.Blocks:
    """Carrega a interface sob demanda, mantendo o núcleo independente dela."""
    from ui import criar_interface as construir
    return construir()


if __name__ == '__main__':
    criar_interface().launch(inbrowser=True)
