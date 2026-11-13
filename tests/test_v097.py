"""v0.97: versão única, concorrência por evento, limite do histórico e login só pelo app."""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

import pytest

import dados
from configuracao import VERSAO
from dados import carregar_historico

RAIZ = Path(__file__).resolve().parents[1]


def test_versao_unica_no_pyproject_readme_e_barra() -> None:
    import ui

    pyproject = (RAIZ / 'pyproject.toml').read_text(encoding='utf-8')
    assert re.search(r'^version = "(.+)"$', pyproject, re.M).group(1).startswith(VERSAO + '.')
    assert (RAIZ / 'README.md').read_text(encoding='utf-8').startswith(f'# SyncUp v{VERSAO}\n')
    assert f'v{VERSAO} · código aberto' in ui.TOPO


def test_creditos_na_barra_e_no_inicio_vem_das_constantes() -> None:
    from configuracao import GITHUB_URL, X_URL, X_USUARIO
    from ui.layout import INICIO_RODAPE, TOPO

    assert f'href="{GITHUB_URL}"' in TOPO and f'href="{X_URL}"' in TOPO and X_USUARIO in TOPO
    assert f'href="{GITHUB_URL}"' in INICIO_RODAPE


def test_match_sozinho_na_fila_e_o_resto_em_paralelo() -> None:
    import ui

    demo = ui.criar_interface()
    limites = {f.api_name: f.concurrency_limit for f in demo.fns.values()}
    assert limites['encontrar_matches'] == 1  # MusicBrainz: 1 consulta/s para o app todo
    assert limites['comparar_dupla'] == 'default'
    assert demo._queue.default_concurrency_limit == ui.CONCORRENCIA > 1


def test_upload_tem_o_mesmo_teto_do_historico() -> None:
    import app

    servidor = app.criar_servidor()
    blocos = next(r.app.blocks for r in servidor.routes if getattr(r, 'path', '') == '')
    assert blocos.max_file_size == dados.LIMITE_BYTES


def test_zip_grande_demais_e_recusado_antes_de_descompactar(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(dados, 'LIMITE_BYTES', 1000)
    caminho = tmp_path / 'grande.zip'
    with zipfile.ZipFile(caminho, 'w', zipfile.ZIP_DEFLATED) as pacote:
        pacote.writestr('Streaming_History_Audio_2026.json', '[' + ' ' * 2000 + ']')
    with pytest.raises(ValueError, match='descompactado'):
        carregar_historico(caminho)
    json_grande = tmp_path / 'grande.json'
    json_grande.write_text('[' + ' ' * 2000 + ']', encoding='utf-8')
    with pytest.raises(ValueError, match='descompactado'):
        carregar_historico(json_grande)
