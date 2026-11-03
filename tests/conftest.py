"""Fixtures pytest com históricos fictícios, isolamento de cache e sementes fixas."""

from __future__ import annotations

import json
import os
import zipfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

# Desativa telemetria nos testes antes de importar a interface.
os.environ['GRADIO_ANALYTICS_ENABLED'] = 'False'
from dados import limpar_cache
from tools.gerar_dados_falsos import Configuracao, gerar_zip

Evento = dict[str, Any]
FabricaEvento = Callable[..., Evento]


@pytest.fixture(autouse=True)
def cache_isolado() -> Iterator[None]:
    """Garante que cada teste começa e termina sem históricos no cache global."""
    limpar_cache()
    yield
    limpar_cache()


@pytest.fixture
def evento() -> FabricaEvento:
    """Produz os quatro campos obrigatórios; extras do Spotify são opcionais."""

    def criar(
        data: str = '2026-01-01T04:00:00Z',
        ms: Any = 60_000,
        musica: Any = 'Faixa',
        artista: Any = 'Artista',
        **extras: Any,
    ) -> Evento:
        """Personaliza um evento sem depender de arquivos ou contas reais."""
        return {
            'ts': data,
            'ms_played': ms,
            'master_metadata_track_name': musica,
            'master_metadata_album_artist_name': artista,
            **extras,
        }

    return criar


@dataclass(frozen=True)
class HistoricosFicticios:
    """Escreve somente dentro do diretório temporário criado pelo pytest."""

    pasta: Path

    def json(self, eventos: list[Evento], nome: str = 'historico.json') -> Path:
        """Grava histórico UTF-8, preservando nomes musicais com acentos."""
        caminho = self.pasta / nome
        caminho.write_text(json.dumps(eventos, ensure_ascii=False), encoding='utf-8')
        return caminho

    def zip(self, partes: dict[str, list[Evento]], nome: str = 'historico.zip') -> Path:
        """Cria ZIP com várias partes do histórico, sem campos auxiliares obrigatórios."""
        caminho = self.pasta / nome
        with zipfile.ZipFile(caminho, 'w', compression=zipfile.ZIP_DEFLATED) as pacote:
            for arquivo, eventos in partes.items():
                pacote.writestr(arquivo, json.dumps(eventos, ensure_ascii=False))
        return caminho


@pytest.fixture
def historicos(tmp_path: Path) -> HistoricosFicticios:
    """Disponibiliza uma fábrica de arquivos descartáveis por teste."""
    return HistoricosFicticios(tmp_path)


@pytest.fixture(scope='session')
def golden_salvo() -> dict[str, Any]:
    """Lê referências existentes; nunca gera ou regrava resultados esperados."""
    pasta = Path(__file__).parent / 'golden'
    return {
        'v04': json.loads((pasta / 'comparacao_v04.json').read_text(encoding='utf-8')),
        'passo1': json.loads((pasta / 'comparacao_passo1.json').read_text(encoding='utf-8')),
    }


@pytest.fixture(scope='session')
def entradas_golden(
    tmp_path_factory: pytest.TempPathFactory, golden_salvo: dict[str, Any]
) -> tuple[Path, Path]:
    """Reproduz somente entradas usando as configurações guardadas pela v0.4."""
    pasta = tmp_path_factory.mktemp('golden-ficticio')
    referencia = golden_salvo['v04']
    return (
        gerar_zip(pasta / 'a.zip', Configuracao(**referencia['config_a'])),
        gerar_zip(pasta / 'b.zip', Configuracao(**referencia['config_b'])),
    )
