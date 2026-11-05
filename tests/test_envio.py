"""Todo campo de envio de históricos tem o botão "Adicionar mais arquivos" ligado a ele."""

from __future__ import annotations

import gradio as gr

import ui


def test_cada_envio_tem_botao_que_abre_o_proprio_seletor() -> None:
    demo = ui.criar_interface()
    envios = [
        b
        for b in demo.blocks.values()
        if isinstance(b, gr.File) and b.interactive is not False and b.file_count == 'multiple'
    ]
    assert len(envios) == 5  # Dupla A e B, Match, Wrapped e Grupo
    scripts = [f.js for f in demo.fns.values() if f.js and 'input[type=file]' in f.js]
    for envio in envios:
        assert envio.elem_id and envio.elem_id.startswith('su-envio-')
        assert any(f'#{envio.elem_id} input[type=file]' in js for js in scripts), envio.elem_id
