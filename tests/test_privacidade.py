"""Meus dados: listar e apagar só o que o SyncUp criou, e o bloco de privacidade."""

from __future__ import annotations

from pathlib import Path

import pytest

import ui
from generos import ARQUIVO_CACHE as ARQUIVO_GENEROS
from perfil_gosto import PerfilGosto, salvar_perfil
from privacidade import apagar_perfil, dados_locais, limpar_cache_local


@pytest.fixture
def pastas(tmp_path: Path) -> tuple[Path, Path]:
    perfis, cache = tmp_path / 'perfis', tmp_path / 'cache'
    for nome in ('Carlos', 'Nicollas'):
        salvar_perfil(PerfilGosto(nome, 'spotify_api', '', {'long_term': ['X']}), perfis)
    cache.mkdir()
    (cache / ARQUIVO_GENEROS).write_text('{"x": ["rock"]}', encoding='utf-8')
    (cache / 'abc-123.parquet').write_bytes(b'0' * 2048)
    (cache / 'abc-123.json').write_text('{}', encoding='utf-8')
    (cache / 'meu_arquivo.txt').write_text('não é do SyncUp', encoding='utf-8')
    (cache / 'subpasta').mkdir()
    return perfis, cache


def test_lista_o_que_esta_guardado(pastas: tuple[Path, Path]) -> None:
    perfis, generos, historicos = dados_locais(*pastas)
    assert perfis.arquivos == 2 and perfis.detalhe == 'Carlos, Nicollas'
    assert generos.arquivos == 1 and historicos.arquivos == 2
    assert historicos.tamanho == 2048 + 2 and historicos.atualizado is not None


def test_apagar_perfil_so_pelo_nome_da_lista(pastas: tuple[Path, Path], tmp_path: Path) -> None:
    perfis, _ = pastas
    (tmp_path / 'app.json').write_text('{}', encoding='utf-8')
    assert not apagar_perfil(perfis, '../app')  # nome fora da lista não vira caminho
    assert (tmp_path / 'app.json').exists()
    assert apagar_perfil(perfis, 'Carlos') and not (perfis / 'Carlos.json').exists()
    assert not apagar_perfil(perfis, 'Carlos')
    assert (perfis / 'Nicollas.json').exists()


def test_limpar_cache_apaga_so_os_arquivos_do_syncup(pastas: tuple[Path, Path]) -> None:
    _, cache = pastas
    assert limpar_cache_local(cache) == 3
    assert sorted(p.name for p in cache.iterdir()) == ['meu_arquivo.txt', 'subpasta']
    assert limpar_cache_local(cache / 'nao_existe') == 0


def test_painel_apaga_so_depois_de_confirmar(pastas: tuple[Path, Path], monkeypatch) -> None:
    perfis, cache = pastas
    monkeypatch.setattr(ui.meus_dados, 'PASTA_PERFIS', perfis)
    monkeypatch.setattr(ui.meus_dados, 'PASTA_CACHE', cache)
    avisos: list[str] = []
    monkeypatch.setattr(ui.gr, 'Info', avisos.append)
    html, lista = ui.meus_dados.apagar_perfil_salvo('')  # cancelou o confirm()
    assert (perfis / 'Carlos.json').exists() and not avisos
    assert 'Carlos, Nicollas' in html and lista.choices == [
        ('Carlos', 'Carlos'),
        ('Nicollas', 'Nicollas'),
    ]
    html, lista = ui.meus_dados.apagar_perfil_salvo('Carlos')
    assert not (perfis / 'Carlos.json').exists() and avisos == ['Perfil de Carlos apagado.']
    ui.meus_dados.limpar_cache(False)
    assert (cache / 'abc-123.parquet').exists()
    ui.meus_dados.limpar_cache(True)
    assert not (cache / 'abc-123.parquet').exists()


def test_nome_com_html_aparece_como_texto(tmp_path: Path, monkeypatch) -> None:
    salvar_perfil(PerfilGosto('<b>Bia</b>', 'spotify_api', '', {'long_term': ['X']}), tmp_path)
    monkeypatch.setattr(ui.meus_dados, 'PASTA_PERFIS', tmp_path)
    assert '<b>Bia' not in ui.meus_dados.resumo_html()


def test_inicio_explica_a_privacidade() -> None:
    texto = ui.meus_dados.PRIVACIDADE
    for trecho in ('Fica no seu computador', 'MusicBrainz', 'token do Spotify', 'Meus dados'):
        assert trecho in texto
