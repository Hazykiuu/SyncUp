"""Meus dados: listar e apagar só o que o SyncUp criou, e o bloco de privacidade."""

from __future__ import annotations

from pathlib import Path

import pytest

import ui
from generos import ARQUIVO_CACHE as ARQUIVO_GENEROS
from privacidade import dados_locais, limpar_cache_local


@pytest.fixture
def cache(tmp_path: Path) -> Path:
    cache = tmp_path / 'cache'
    cache.mkdir()
    (cache / ARQUIVO_GENEROS).write_text('{"x": ["rock"]}', encoding='utf-8')
    (cache / 'abc-123.parquet').write_bytes(b'0' * 2048)
    (cache / 'abc-123.json').write_text('{}', encoding='utf-8')
    (cache / 'meu_arquivo.txt').write_text('não é do SyncUp', encoding='utf-8')
    (cache / 'subpasta').mkdir()
    return cache


def test_lista_o_que_esta_guardado(cache: Path) -> None:
    generos, historicos = dados_locais(cache)
    assert generos.arquivos == 1 and historicos.arquivos == 2
    assert historicos.tamanho == 2048 + 2 and historicos.atualizado is not None


def test_limpar_cache_apaga_so_os_arquivos_do_syncup(cache: Path) -> None:
    assert limpar_cache_local(cache) == 3
    assert sorted(p.name for p in cache.iterdir()) == ['meu_arquivo.txt', 'subpasta']
    assert limpar_cache_local(cache / 'nao_existe') == 0


def test_painel_limpa_so_depois_de_confirmar(cache: Path, monkeypatch) -> None:
    monkeypatch.setattr(ui.meus_dados, 'PASTA_CACHE', cache)
    avisos: list[str] = []
    monkeypatch.setattr(ui.gr, 'Info', lambda m, **_: avisos.append(m))
    ui.meus_dados.limpar_cache(False)  # cancelou o confirm()
    assert (cache / 'abc-123.parquet').exists() and not avisos
    html = ui.meus_dados.limpar_cache(True)
    assert not (cache / 'abc-123.parquet').exists() and 'vazio' in html


def test_inicio_explica_a_privacidade() -> None:
    texto = ui.meus_dados.PRIVACIDADE
    for trecho in ('Fica no seu computador', 'MusicBrainz', 'ListenBrainz', 'Meus dados'):
        assert trecho in texto
    assert 'Spotify' not in texto  # o login do Spotify saiu na 1.9
