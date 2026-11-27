"""Landing page (site/): idioma, links, arquivos e só scripts externos permitidos."""

from __future__ import annotations

import base64
import hashlib
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
    # A URL aparece duas vezes no importmap: no import e na chave de integridade (hash do arquivo).
    assert sorted(set(externos)) == ['https://unpkg.com/lenis@1.3.23/dist/lenis.mjs']
    assert '"integrity"' in HTML
    assert 'gsap' not in HTML.lower()
    assert not re.search(r'googletagmanager|google-analytics|gtag\(|facebook\.net', HTML)


def test_landing_leva_ao_app_e_nao_promete_o_que_saiu() -> None:
    assert HTML.count('href="app/"') >= 3 and (SITE / 'app' / 'index.html').is_file()
    for velho in (
        '100% local',
        'seu computador',
        'Login do Spotify',
        'token do Spotify',
        'iniciar.bat',
    ):
        assert velho not in HTML, velho


def test_app_serve_o_preact_do_proprio_site() -> None:
    """R3-02: o app abre sem CDN, e o arquivo copiado é o mesmo que o import map conferia no unpkg."""
    app = Path(__file__).resolve().parents[1] / 'site' / 'app'
    pagina = (app / 'index.html').read_text(encoding='utf-8')
    mapa = re.search(r'<script type="importmap">(.*?)</script>', pagina, re.S).group(1)
    assert 'https://' not in mapa and './vendor/standalone.module.js' in mapa
    resumo = hashlib.sha384((app / 'vendor' / 'standalone.module.js').read_bytes()).digest()
    assert base64.b64encode(resumo).decode() == (
        'StNNHifqKmppGEDNqrv+YtX8PD3mhAhLtNbioQ4QxbPNqaTnktcDjsIPGjcDoiKa'
    )
    assert {'LICENSE-htm', 'LICENSE-preact'} <= {p.name for p in (app / 'vendor').iterdir()}


def test_nenhum_subtitulo_do_app_diz_que_nada_sai() -> None:
    """R3-05: com "Capas e som" ligado, nomes de artistas e músicas vão para terceiros."""
    fonte = (SITE / 'app/js/main.js').read_text(encoding='utf-8')
    assert not re.search(r'Nada (sai|é enviado)', fonte)


def test_privacidade_nao_promete_que_o_lastfm_some_ao_fechar() -> None:
    """R3-11: o que vem do Last.fm fica no navegador até vencer ou ser apagado."""
    assert (
        'sumiu' not in HTML
        and 'por até 7 dias' not in HTML
        and '7 dias' in HTML
        and 'Apagar dados guardados' in HTML
    )
