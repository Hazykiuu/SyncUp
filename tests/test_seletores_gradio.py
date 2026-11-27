"""styles.css e syncup.js dependem de classes internas do Gradio (R1-05): um upgrade não pode quebrar calado."""

from __future__ import annotations

from pathlib import Path

import gradio
import pytest

RAIZ = Path(__file__).resolve().parents[1]
CSS = (RAIZ / 'styles.css').read_text(encoding='utf-8')
JS = (RAIZ / 'syncup.js').read_text(encoding='utf-8')
INTERNOS = ('gradio-container', 'tab-wrapper', 'tab-container', 'overflow-menu', 'label-wrap',
            'upload-container', 'file-preview-holder', 'More tabs')  # fmt: skip


@pytest.fixture(scope='module')
def bundle() -> str:
    pasta = Path(gradio.__file__).parent / 'templates'
    return ''.join(
        p.read_text(encoding='utf-8', errors='ignore')
        for p in pasta.rglob('*')
        if p.suffix in ('.js', '.css')
    )


@pytest.mark.parametrize('nome', INTERNOS)
def test_seletor_interno_existe_no_gradio_instalado(bundle: str, nome: str) -> None:
    assert nome in CSS or nome in JS, f'{nome} não é mais usado: tire da lista'
    assert nome in bundle, f'{nome} sumiu do Gradio {gradio.__version__}'


def test_sem_classes_geradas_nem_seletores_mortos() -> None:
    assert 'svelte-' not in CSS
    web = (RAIZ / 'site/app/stories.css').read_text(encoding='utf-8')
    for morto in (
        '.su-chip-label',
        '.su-srcs',
        '.su-match-h',
        '.su-best-list',
        '.su-steps ',
        '.su-steps code',
    ):
        assert morto not in CSS, morto
    assert 'st-capa-vazia' not in web and '.st-capa.pequena' not in web
