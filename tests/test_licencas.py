"""O SyncUp é open source (MIT) e só depende de código aberto."""

from __future__ import annotations

import importlib.metadata as metadata
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
# Identificadores SPDX de licenças abertas aceitas para dependências.
ABERTAS = re.compile(r'\b(MIT|BSD|Apache|MPL|PSF|Python Software Foundation|ISC|LGPL|GPL|HPND)')


def _dependencias() -> list[str]:
    nomes = set()
    for arquivo in RAIZ.glob('requirements*.txt'):
        for linha in arquivo.read_text(encoding='utf-8').splitlines():
            linha = linha.split('#')[0].strip()
            if linha and not linha.startswith('-'):
                nomes.add(re.split(r'[\[=<>;!~ ]', linha)[0])
    return sorted(nomes)


def test_projeto_tem_licenca_mit() -> None:
    assert (RAIZ / 'LICENSE').read_text(encoding='utf-8').startswith('MIT License')
    assert (RAIZ / 'fontes' / 'OFL.txt').is_file()  # licença da fonte Figtree


@pytest.mark.parametrize('pacote', _dependencias())
def test_dependencia_tem_licenca_aberta(pacote: str) -> None:
    try:
        dados = metadata.metadata(pacote)
    except metadata.PackageNotFoundError:
        pytest.skip(f'{pacote} não está instalado (dependência opcional)')
    textos = [
        dados.get('License-Expression') or '',
        (dados.get('License') or '')[:200],
        *(c for c in dados.get_all('Classifier') or [] if c.startswith('License ::')),
    ]
    assert any('OSI Approved' in t or ABERTAS.search(t) for t in textos), (
        f'{pacote} não declara uma licença aberta: {textos}'
    )
