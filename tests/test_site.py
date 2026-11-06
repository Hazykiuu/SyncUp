"""Landing page (site/): idioma, links, arquivos e só scripts externos permitidos."""

from __future__ import annotations

import re
from pathlib import Path

from configuracao import GITHUB_URL, X_URL

SITE = Path(__file__).resolve().parents[1] / 'site'
HTML = (SITE / 'index.html').read_text(encoding='utf-8')


def test_idioma_e_links_principais() -> None:
    assert '<html lang="pt-BR">' in HTML
    assert f'{GITHUB_URL}/releases/latest' in HTML and X_URL in HTML


def test_arquivos_locais_existem() -> None:
    locais = set(re.findall(r'(?:src|href)="(assets/[^"]+)"', HTML)) | set(
        re.findall(r"'(assets/[^']+)'", HTML)
    )
    assert locais, 'nenhum arquivo local encontrado'
    for caminho in locais:
        assert (SITE / caminho).is_file(), caminho


def test_scripts_externos_so_da_lista_permitida() -> None:
    externos = re.findall(r'https?://[^"\'\s)]+\.m?js', HTML)
    assert externos == ['https://unpkg.com/lenis@1.3.23/dist/lenis.mjs']
    assert 'gsap' not in HTML.lower()
    assert not re.search(r'googletagmanager|google-analytics|gtag\(|facebook\.net', HTML)
