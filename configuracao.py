"""Opções explícitas da ingestão; filtros são dados editáveis, não condições fixas."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

VERSAO = '1.5'  # Fonte única: pyproject, README e barra do app conferidos em teste.
GITHUB_URL = 'https://github.com/Hazykiuu/SyncUp'
X_URL = 'https://x.com/HazyKiuu'
X_USUARIO = '@HazyKiuu'
MUSICAS_IGNORADAS_PADRAO = ('(Falsa) Esperança',)  # Preferência anterior, editável ou removível.
PoliticaVarious = Literal['manter', 'ignorar']


def normalizar_nome(nome: str) -> str:
    """Normaliza caixa, espaços e pontuação, preservando letras e acentos."""
    return re.sub(r'[\W_]+', '', unicodedata.normalize('NFKC', nome).casefold())


@dataclass(frozen=True)
class ConfiguracaoCarga:
    """Configura filtros, fuso, deduplicação e cache opcional em disco."""

    fuso_horario: str = 'America/Sao_Paulo'
    musicas_ignoradas: tuple[str, ...] = MUSICAS_IGNORADAS_PADRAO
    artistas_ignorados: tuple[str, ...] = ()
    various_artists: PoliticaVarious = 'manter'
    deduplicar: bool = False
    usar_cache_disco: bool = False
    diretorio_cache: str = '.syncup_cache'

    def __post_init__(self) -> None:
        """Valida opções antes de ler arquivos ou consultar caches."""
        try:
            ZoneInfo(self.fuso_horario)
        except (ZoneInfoNotFoundError, ValueError, TypeError) as erro:
            raise ValueError(
                'Fuso inválido. Use um nome IANA, como America/Sao_Paulo ou Europe/Lisbon.'
            ) from erro
        if self.various_artists not in ('manter', 'ignorar'):
            raise ValueError('Escolha manter ou ignorar para Various Artists.')
        for nomes in (self.musicas_ignoradas, self.artistas_ignorados):
            if not isinstance(nomes, tuple) or any(not isinstance(nome, str) for nome in nomes):
                raise ValueError('Os nomes ignorados devem ser informados em tuplas de textos.')
        if not isinstance(self.diretorio_cache, str) or not self.diretorio_cache.strip():
            raise ValueError('Informe uma pasta válida para o cache em disco.')

    def opcoes_dados(self) -> dict[str, object]:
        """Identifica apenas opções que modificam o conteúdo preparado."""
        return {
            'fuso_horario': self.fuso_horario,
            'musicas_ignoradas': sorted(
                {normalizar_nome(n) for n in self.musicas_ignoradas if n.strip()}
            ),
            'artistas_ignorados': sorted(
                {normalizar_nome(n) for n in self.artistas_ignorados if n.strip()}
            ),
            'various_artists': self.various_artists,
            'deduplicar': self.deduplicar,
        }
