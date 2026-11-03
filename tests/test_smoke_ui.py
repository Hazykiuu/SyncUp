"""Teste de fumaça da árvore Gradio 5, sem iniciar servidor ou abrir navegador."""

from __future__ import annotations

from pathlib import Path

import gradio as gr
import pytest

from app import criar_interface


@pytest.mark.ui
def test_criar_interface_monta_arvore_sem_erros() -> None:
    """Valida montagem, abas, múltiplos arquivos, plots, tema, CSS e rotas dos callbacks."""
    demo = criar_interface()
    try:
        assert isinstance(demo, gr.Blocks)
        assert demo.config['title'] == 'SyncUp'
        componentes = list(demo.blocks.values())
        arquivos = [c for c in componentes if isinstance(c, gr.File) and c.interactive is not False]
        assert len(arquivos) == 5  # dupla A, dupla B, match, Wrapped e grupo
        assert all(c.file_count == 'multiple' for c in arquivos)
        assert any(isinstance(c, gr.Tab) and 'Grupo' in c.label for c in componentes)
        assert len([c for c in componentes if isinstance(c, gr.Plot)]) >= 6
        assert {f.api_name for f in demo.fns.values() if f.api_name} == {
            'comparar_dupla',
            'comparar_grupo',
            'exportar_playlist',
            'gerar_cartao',
            'gerar_wrapped',
            'baixar_wrapped',
            'encontrar_matches',
            'playlist_festa',
            'baixar_cartao_match',
        }
        assert 'fonts.googleapis.com' not in str(demo.theme._stylesheets)  # fonte local (OFL)
        assert demo.theme is not None
        css = Path(__file__).resolve().parents[1] / 'styles.css'
        assert css.is_file()
        assert 'prefers-reduced-motion' in css.read_text(encoding='utf-8')
    finally:
        demo.close()
