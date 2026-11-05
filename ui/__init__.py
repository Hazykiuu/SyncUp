"""Apresentação do SyncUp no tema Spotify; consome os resultados estruturados de analise.py.

Um módulo por tela: ``comum`` (estilos e utilidades), ``dupla`` (Dupla e Grupo),
``meu_wrapped``, ``match`` e ``layout`` (montagem da interface). Os nomes abaixo
continuam importáveis de ``ui``, como antes da divisão.
"""

import gradio as gr

from ui import comum, dupla, layout, match, meu_wrapped, meus_dados
from ui.comum import CONCORRENCIA, _limpar_exportacoes
from ui.dupla import (
    apresentar,
    executar_dupla,
    executar_grupo,
    grafico_artistas,
    grafico_meses,
    perfil_card,
    resumo_markdown,
    tabela_display,
    texto_conexoes,
)
from ui.layout import RECURSOS, TOPO, criar_interface
from ui.match import (
    atualizar_perfis,
    baixar_cartao_match,
    baixar_festa,
    executar_match,
    perfis_salvos,
)

__all__ = [
    'CONCORRENCIA',
    'RECURSOS',
    'TOPO',
    '_limpar_exportacoes',
    'apresentar',
    'atualizar_perfis',
    'baixar_cartao_match',
    'baixar_festa',
    'comum',
    'criar_interface',
    'dupla',
    'executar_dupla',
    'executar_grupo',
    'executar_match',
    'gr',
    'grafico_artistas',
    'grafico_meses',
    'layout',
    'match',
    'meu_wrapped',
    'meus_dados',
    'perfil_card',
    'perfis_salvos',
    'resumo_markdown',
    'tabela_display',
    'texto_conexoes',
]
