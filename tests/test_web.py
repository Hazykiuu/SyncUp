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
    with zipfile.ZipFile(tmp_path / 'demo-wrapped.zip') as demo:  # demo do Wrapped (JS)
        assert any(n.endswith('.json') for n in demo.namelist())


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


def test_nomes_maliciosos_nao_viram_html_ativo(zips: tuple[str, str]) -> None:
    """O HTML vai para dangerouslySetInnerHTML: nada de tag ou atributo executável."""
    from html.parser import HTMLParser

    from web import ponte

    ativos: list[str] = []

    class Caçador(HTMLParser):
        def handle_starttag(self, tag: str, attrs: list) -> None:
            ativos.extend(tag for _ in [0] if tag in {'script', 'img', 'iframe'})
            ativos.extend(k for k, v in attrs if k.startswith('on') or 'javascript:' in (v or ''))

    nome_a, nome_b = '<img src=x onerror=alert(1)>', "\"><script>alert('2')</script>"
    r = ponte.comparar_dupla([zips[0]], [zips[1]], nome_a, nome_b)
    for parte in r['html'].values():
        for trecho in parte if isinstance(parte, list) else [parte]:
            Caçador().feed(trecho)
    assert not ativos
    assert 'su-stories' in r['html']['wrapped']  # o Wrapped (calculado antes) continua saindo
    # Gráficos: < > escapados, aspas legíveis (o Plotly não decodifica &quot;).
    legendas = json.dumps(r['graficos']['artistas'])
    assert '&lt;img' in legendas and '&quot;' not in legendas and '&#x27;' not in legendas


def test_wrapped_e_cartao_no_navegador(zips: tuple[str, str], tmp_path: Path, monkeypatch) -> None:
    from web import ponte

    monkeypatch.setattr(ponte, 'SAIDA', tmp_path)
    r = ponte.wrapped([zips[0]], ' <b>Ana</b> ')
    json.dumps(r)  # atravessa o Worker
    assert 'stories' not in r  # o app web desenha os stories a partir de `dados`
    assert r['dados']['nome'] == '<b>Ana</b>'  # cru: o Preact escapa
    trilha = r['trilha']
    assert {'primeira', 'artista', 'top_musicas', 'recorde', 'fiel'} <= set(trilha['slides'])
    assert trilha['slides']['artista'] == [{'artista': trilha['slides']['artista'][0]['artista']}]
    assert trilha['fila'] and all(m['artista'] for m in trilha['fila'])
    png = Path(ponte.cartao_wrapped())
    assert png.suffix == '.png' and png.stat().st_size > 10_000
    ponte.comparar_dupla([zips[0]], [zips[1]], 'Ana', 'Bia')
    assert Path(ponte.cartao_wrapped()).is_file()  # a Dupla não apaga o Wrapped


def test_wrapped_roda_sem_plotly_nem_pillow(zips: tuple[str, str]) -> None:
    """O worker só baixa o plotly (9,9 MB) na Dupla e o Pillow no PNG: o Wrapped não pode precisar deles."""
    codigo = (
        'import sys\n'
        'class Bloqueio:\n'
        '    def find_spec(self, nome, *args):\n'
        "        if nome.split('.')[0] in {'plotly', 'PIL'}:\n"
        "            raise ImportError('bloqueado: ' + nome)\n"
        'sys.meta_path.insert(0, Bloqueio())\n'
        'from web import ponte\n'
        f'r = ponte.wrapped([{zips[0]!r}], "Ana")\n'
        "assert r['dados']['top_musicas']\n"
        "assert not {'plotly', 'PIL'} & {m.split('.')[0] for m in sys.modules}\n"
    )
    subprocess.run([sys.executable, '-c', codigo], cwd=RAIZ, check=True)


def test_contrato_json_do_wrapped(zips: tuple[str, str]) -> None:
    """``dados`` leva todos os campos do Wrapped em JSON puro; textos crus (o Preact escapa)."""
    from dataclasses import fields
    from datetime import datetime

    from web import ponte
    from wrapped import Wrapped

    r = ponte.wrapped([zips[0]], '<b>Ana</b>')
    dados = json.loads(json.dumps(r['dados'], allow_nan=False))  # sem NaN, sem tipos estranhos
    assert set(dados) == {f.name for f in fields(Wrapped)}
    assert dados['nome'] == '<b>Ana</b>'  # cru: escapar aqui viraria &lt;b&gt; na tela
    for campo in ('inicio', 'fim', 'primeira_data', 'dia_recorde', 'descoberta_artista_vida'):
        datetime.fromisoformat(dados[campo])
    item = dados['top_musicas'][0]
    assert set(item) == {'nome', 'plays', 'horas', 'artista', 'uri'} and isinstance(
        item['plays'], int
    )
    assert item['uri'].startswith('spotify:track:')  # o JS só aceita ID real (22 caracteres)
    assert dados['top_artistas'][0]['uri'] is None  # artista não tem ID no ZIP
    assert dados['anos'][0]['ano'] and isinstance(dados['anos'][0]['top_artistas'], list)
    assert len(dados['plays_por_hora']) == 24
    assert {'nome', 'icone', 'forca'} <= set(dados['arquetipos']['principal'])
    assert all(len(p) == 2 for p in dados['plataformas'])


def test_simples_troca_nan_e_numpy() -> None:
    import numpy as np
    import pandas as pd

    from web.ponte import _simples

    assert _simples({'a': float('nan'), 'b': np.int64(3), 'c': (pd.NaT, np.float64(1.5))}) == {
        'a': None,
        'b': 3,
        'c': [None, 1.5],
    }
