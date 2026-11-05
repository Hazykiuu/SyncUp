"""O que o SyncUp guarda no computador e como apagar (painel "Meus dados").

Só arquivos que o próprio app cria são listados e apagados: perfis ``*.json`` na
pasta de perfis e, na pasta de cache, os arquivos de topo com sufixos conhecidos.
Nada fora dessas pastas é tocado, e subpastas ficam como estão.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from dados import limpar_cache
from generos import ARQUIVO_CACHE as ARQUIVO_GENEROS
from perfil_gosto import limpar_cache_perfis, listar_perfis

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


def dados_locais(pasta_perfis: str | Path, pasta_cache: str | Path) -> list[ItemLocal]:
    """Perfis do Spotify, cache de gêneros e cache de históricos, com tamanho e data."""
    perfis = listar_perfis(pasta_perfis)
    cache = _arquivos_cache(Path(pasta_cache))
    generos = [p for p in cache if p.name == ARQUIVO_GENEROS]
    historicos = [p for p in cache if p.name != ARQUIVO_GENEROS]
    return [
        _item(
            'Perfis do Spotify',
            ', '.join(p.stem for p in perfis) or 'nenhum',
            perfis,
        ),
        _item('Gêneros do MusicBrainz', 'nomes de artistas e seus gêneros', generos),
        _item('Cache de históricos', 'cópia em Parquet dos ZIPs lidos', historicos),
    ]


def apagar_perfil(pasta_perfis: str | Path, nome: str) -> bool:
    """Apaga o perfil salvo com esse nome; ``False`` se ele não existe.

    O nome é comparado com a lista de perfis, nunca usado para montar um caminho:
    um nome como ``../app`` não alcança nada fora da pasta.
    """
    caminho = next((p for p in listar_perfis(pasta_perfis) if p.stem == nome), None)
    if caminho is None:
        return False
    caminho.unlink(missing_ok=True)
    return True


def limpar_cache_local(pasta_cache: str | Path) -> int:
    """Apaga o cache em disco e o da memória; devolve quantos arquivos saíram."""
    arquivos = _arquivos_cache(Path(pasta_cache))
    for arquivo in arquivos:
        arquivo.unlink(missing_ok=True)
    limpar_cache()
    limpar_cache_perfis()
    return len(arquivos)
