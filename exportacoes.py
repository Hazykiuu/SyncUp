"""Exportação local de playlist; não cria playlists na conta do Spotify."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from analise import ResultadoComparacao


def _celula_segura(valor: object) -> str:
    """Impede que nomes enviados sejam interpretados como fórmulas de planilha."""
    texto = str(valor)
    if texto.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')):
        return "'" + texto
    return texto


def exportar_playlist(resultado: ResultadoComparacao, destino: str | Path) -> Path:
    """Grava todas as faixas comuns em CSV UTF-8 BOM, separado por ponto e vírgula.

    Os links são buscas no Spotify. Nomes potencialmente interpretados como
    fórmulas recebem um apóstrofo de proteção ao abrir em Excel/LibreOffice.
    """
    caminho = Path(destino)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open('w', encoding='utf-8-sig', newline='') as saida:
        escritor = csv.writer(saida, delimiter=';')
        escritor.writerow(resultado.playlist.columns)
        for linha in resultado.playlist.itertuples(index=False, name=None):
            escritor.writerow([_celula_segura(valor) for valor in linha])
    return caminho
