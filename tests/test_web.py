"""App no navegador: o pacote do Pyodide e a ponte (rodando aqui no Python comum)."""

from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from analise import comparar
from configuracao import ConfiguracaoCarga
from tools.empacotar_web import empacotar
from tools.gerar_dados_falsos import Configuracao, gerar_zip

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def zips(tmp_path_factory: pytest.TempPathFactory) -> tuple[str, str]:
    pasta = tmp_path_factory.mktemp('web')
    a, b = pasta / 'a.zip', pasta / 'b.zip'
    gerar_zip(a, Configuracao(linhas=4_000, artistas=120, seed=41))
    gerar_zip(b, Configuracao(linhas=4_000, artistas=120, seed=97))
    return str(a), str(b)


def test_pacote_leva_so_o_que_roda_no_navegador(tmp_path: Path) -> None:
    with zipfile.ZipFile(empacotar(tmp_path / 'nucleo.zip')) as pacote:
        nomes = set(pacote.namelist())
    assert {'web/ponte.py', 'analise.py', 'dados.py', 'fontes/Figtree.ttf'} <= nomes
    # Rede, servidor e interface Gradio ficam de fora.
    assert not nomes & {'generos.py', 'spotify_api.py', 'listenbrainz.py', 'app.py'}
    assert not any(n.startswith('ui/') for n in nomes)


def test_ponte_nao_importa_gradio_nem_rede() -> None:
    codigo = (
        'import sys, web.ponte; '
        "proibidos = {'gradio', 'fastapi', 'httpx', 'uvicorn'} & set(sys.modules); "
        'assert not proibidos, proibidos'
    )
    subprocess.run([sys.executable, '-c', codigo], cwd=RAIZ, check=True)


def test_comparar_dupla_igual_ao_nucleo_e_vira_json(zips: tuple[str, str]) -> None:
    from web import ponte

    a, b = zips
    r = ponte.comparar_dupla([a], [b], 'Ana', 'Bia', {'comum': True, 'ponderacao': 'raiz'})
    texto = json.dumps(r)  # tudo precisa atravessar o Worker como JSON
    assert 'Ana' in texto and 'Bia' in texto
    referencia = comparar(a, b, 'Ana', 'Bia', configuracao=ConfiguracaoCarga(), ponderacao='raiz')
    assert r['metricas']['cosseno'] == pytest.approx(referencia.metricas.cosseno)
    assert set(r['graficos']) == {'artistas', 'horarios', 'tracos', 'rankings', 'meses'}
    assert r['html']['resumo'] and len(r['html']['perfis']) == 2
    assert r['tabelas']['playlist']['colunas']


def test_downloads_da_dupla(zips: tuple[str, str], tmp_path: Path, monkeypatch) -> None:
    from web import ponte

    monkeypatch.setattr(ponte, 'SAIDA', tmp_path)
    ponte.comparar_dupla([zips[0]], [zips[1]], 'Ana', 'Bia')
    for gerar, sufixo in (
        (ponte.cartao_dupla, '.png'),
        (ponte.cartao_sintonia, '.png'),
        (ponte.playlist_dupla, '.csv'),
    ):
        caminho = Path(gerar())
        assert caminho.suffix == sufixo and caminho.stat().st_size > 0
