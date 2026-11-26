"""Teste de fumaça da árvore Gradio 6, sem iniciar servidor ou abrir navegador."""

from __future__ import annotations

import re
from pathlib import Path

import gradio as gr
import pytest

from app import criar_interface
from ui.layout import _tema


@pytest.mark.ui
def test_criar_interface_monta_arvore_sem_erros() -> None:
    """Valida montagem, abas, múltiplos arquivos, plots, tema, CSS e rotas dos callbacks."""
    demo = criar_interface()
    try:
        assert isinstance(demo, gr.Blocks)
        assert demo.config['title'] == 'SyncUp'
        componentes = list(demo.blocks.values())
        arquivos = [c for c in componentes if isinstance(c, gr.File) and c.interactive is not False]
        assert len(arquivos) == 6  # dupla A e B, match, convite, Wrapped e grupo
        assert all(c.file_count == 'multiple' for c in arquivos)
        assert any(isinstance(c, gr.Tab) and 'Grupo' in c.label for c in componentes)
        assert len([c for c in componentes if isinstance(c, gr.Plot)]) >= 6
        assert {f.api_name for f in demo.fns.values() if f.api_visibility == 'public'} == {
            'comparar_dupla',
            'comparar_grupo',
            'exportar_playlist',
            'gerar_cartao',
            'gerar_wrapped',
            'baixar_wrapped',
            'encontrar_matches',
            'playlist_festa',
            'baixar_cartao_match',
            'baixar_sintonia',
            'gerar_convite',
        }
        # Gradio 6: o tema vai no mount_gradio_app (app.py), não no Blocks.
        assert 'fonts.googleapis.com' not in str(_tema()._stylesheets)  # fonte local (OFL)
        css = Path(__file__).resolve().parents[1] / 'styles.css'
        assert css.is_file()
        assert 'prefers-reduced-motion' in css.read_text(encoding='utf-8')
    finally:
        demo.close()


def test_prazo_de_apagar_cumpre_o_que_o_texto_promete() -> None:
    """R3-11: no pior caso o arquivo dura frequência + idade; o texto promete 1 hora."""
    from pathlib import Path

    from ui.meus_dados import PRIVACIDADE

    layout = (Path(__file__).resolve().parents[1] / 'ui/layout.py').read_text(encoding='utf-8')
    frequencia, idade = map(int, re.search(r'delete_cache=\((\d+), (\d+)\)', layout).groups())
    assert frequencia + idade <= 3600
    assert 'em até 1 hora com o app aberto' in PRIVACIDADE and 'próxima vez' in PRIVACIDADE


def test_textos_do_pc_sem_jargao_de_codigo() -> None:
    """R2-14: "describe()" é nome de função, não é texto para quem usa."""
    from pathlib import Path

    layout = (Path(__file__).resolve().parents[1] / 'ui/layout.py').read_text(encoding='utf-8')
    assert 'describe()' not in layout
