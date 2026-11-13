"""O que o SyncUp guarda no computador e como apagar (painel "Meus dados").

Só arquivos que o próprio app cria são listados e apagados: na pasta de cache, os
arquivos de topo com sufixos conhecidos.
Nada fora dessas pastas é tocado, e subpastas ficam como estão.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from dados import limpar_cache
from generos import ARQUIVO_CACHE as ARQUIVO_GENEROS
from perfil_gosto import limpar_cache_perfis

# Parquet, manifestos, gêneros e gravações que pararam pela metade.
SUFIXOS_CACHE = ('.parquet', '.json', '.tmp')


@dataclass(frozen=True)
class ItemLocal:
    """Um tipo de dado guardado no computador."""

    rotulo: str
    detalhe: str
    arquivos: int
    tamanho: int  # bytes
    atualizado: datetime | None


def _arquivos_cache(pasta: Path) -> list[Path]:
    if not pasta.is_dir():
        return []
    return sorted(p for p in pasta.iterdir() if p.is_file() and p.suffix in SUFIXOS_CACHE)


def _item(rotulo: str, detalhe: str, arquivos: list[Path]) -> ItemLocal:
    estados = [p.stat() for p in arquivos]
    recente = max((e.st_mtime for e in estados), default=None)
    return ItemLocal(
        rotulo,
        detalhe,
        len(arquivos),
        sum(e.st_size for e in estados),
        datetime.fromtimestamp(recente) if recente is not None else None,
    )


def dados_locais(pasta_cache: str | Path) -> list[ItemLocal]:
    """Cache de gêneros e cache de históricos, com tamanho e data."""
    cache = _arquivos_cache(Path(pasta_cache))
    generos = [p for p in cache if p.name == ARQUIVO_GENEROS]
    historicos = [p for p in cache if p.name != ARQUIVO_GENEROS]
    return [
        _item('Gêneros do MusicBrainz', 'nomes de artistas e seus gêneros', generos),
        _item('Cache de históricos', 'cópia em Parquet dos ZIPs lidos', historicos),
    ]


def limpar_cache_local(pasta_cache: str | Path) -> int:
    """Apaga o cache em disco e o da memória; devolve quantos arquivos saíram."""
    arquivos = _arquivos_cache(Path(pasta_cache))
    for arquivo in arquivos:
        arquivo.unlink(missing_ok=True)
    limpar_cache()
    limpar_cache_perfis()
    return len(arquivos)
