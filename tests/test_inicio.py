"""Aba Início: os cartões levam às abas certas; os resumos novos usam o slide 'fim'."""

from __future__ import annotations

import gradio as gr
import pandas as pd

import ui
from conciliacao import conciliar
from perfil_gosto import PerfilGosto
from recursos import Sintonia
from stories import stories_match_html, stories_sintonia_html


def test_cartoes_do_inicio_abrem_as_abas() -> None:
    demo = ui.criar_interface()
    try:
        abas = next(
            b
            for b in demo.blocks.values()
            if isinstance(b, gr.Tabs) and 'su-nav' in (b.elem_classes or [])
        )
        ids = [t.id for t in abas.children if isinstance(t, gr.Tab)]
        assert ids == ['inicio', 'dupla', 'match', 'wrapped', 'grupo']
        atalhos = [
            f for f in demo.fns.values() if abas in f.outputs and f.api_visibility == 'private'
        ]
        destinos = []
        for f in atalhos:
            saida = f.fn()
            abas_e_sub = saida if isinstance(saida, tuple) else (saida,)
            destinos.append(tuple(t.selected for t in abas_e_sub))
        # O cartão "Em sintonia" abre a Dupla já na sub-aba da sintonia.
        assert destinos == [(r[0],) if r[1] is None else (r[0], r[1]) for r in ui.RECURSOS]
        assert ('dupla', 'sintonia') in destinos
        # Opções de dados ficam na gaveta lateral, fechada por padrão.
        lateral = next(b for b in demo.blocks.values() if isinstance(b, gr.Sidebar))
        assert lateral.open is False
    finally:
        demo.close()


def test_resumos_do_match_e_da_sintonia_usam_o_slide_fim() -> None:
    def perfil(nome: str) -> PerfilGosto:
        return PerfilGosto(nome, 't', '', {'long_term': ['X', nome]})

    match = stories_match_html(conciliar([perfil('Ana'), perfil('Bia')]))
    vazia = Sintonia([], 0.0, [], pd.Series(dtype=float), None, None)
    sintonia = stories_sintonia_html('Ana', 'Bia', vazia, 3)
    for html in (match, sintonia):
        assert 's-fim' in html and 's-resumo' not in html
