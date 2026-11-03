"""Formatação pt-BR independente do locale e escape nos limites da apresentação."""

from __future__ import annotations

import re
from collections.abc import Iterable
from html import escape
from itertools import islice
from math import isfinite


def fmt_num(valor: int | float, casas: int = 0) -> str:
    """Formata número finito com milhares em pontos e decimal em vírgula."""
    if not isinstance(casas, int) or casas < 0:
        raise ValueError('A quantidade de casas decimais deve ser um inteiro não negativo.')
    if not isfinite(valor):
        raise ValueError('Não é possível formatar um número não finito.')
    return f'{valor:,.{casas}f}'.translate(str.maketrans({',': '.', '.': ','}))


def fmt_pct(proporcao: float, casas: int = 1) -> str:
    """Formata uma proporção: 0,1234 torna-se 12,3%."""
    return fmt_num(proporcao * 100, casas) + '%'


def fmt_horas(horas: float, casas: int = 1) -> str:
    """Formata uma quantidade em horas: 1234,5 torna-se 1.234,5 h."""
    return fmt_num(horas, casas) + ' h'


def escape_html(texto: str) -> str:
    """Escapa caracteres especiais em conteúdo HTML, incluindo aspas."""
    return escape(str(texto), quote=True)


def escape_markdown(texto: str) -> str:
    """Escapa sintaxe Markdown e HTML; neutraliza quebras de linha em tabelas."""
    seguro = escape_html(texto).replace('\r', ' ').replace('\n', ' ')
    return re.sub(r'([\\`*_{}\[\]()#+.!|>~\-])', r'\\\1', seguro)


def listar_markdown(nomes: Iterable[str], limite: int = 20) -> str:
    """Trunca por quantidade de itens sem cortar nomes ou sequências de escape."""
    if limite < 0:
        raise ValueError('O limite de itens deve ser não negativo.')
    return ', '.join(escape_markdown(nome) for nome in islice(nomes, limite))
