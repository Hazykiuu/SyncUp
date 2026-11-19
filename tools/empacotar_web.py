"""Prepara os arquivos gerados do app no navegador (``site/app``). Uso: ``python tools/empacotar_web.py``.

Desde a 1.11 a Dupla e o Wrapped rodam em JavaScript, sem Python no navegador, e desde a 1.12 o
visual e a corrida têm arquivos próprios (``nucleo.css`` e ``js/corrida.js``). Sobram as demos:
``demo-wrapped.zip`` e ``demo-bruno.zip``, os dois históricos do "Ver um exemplo" (Rafa e Lu no
app web), e ``demo-carla.zip`` e ``demo-davi.zip`` (Teo e Nina), que completam os quatro da Batalha
e do Match. Os nomes dos arquivos ficam os antigos: ninguém os vê e o CI e os testes dependem deles.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
APP = RAIZ / 'site' / 'app'
# Rafa (demo-wrapped) também é a demo do Wrapped; Lu (demo-bruno) completa a dupla.
# Teo e Nina entram na Batalha com gostos diferentes (mais artistas; mais preso aos favoritos),
# senão as rodadas empatam quase todas. Artistas e músicas com nomes inventados que parecem reais.
DEMOS = {
    'demo-wrapped.zip': {'seed': 41},
    'demo-bruno.zip': {'seed': 97},
    'demo-carla.zip': {'seed': 23, 'artistas': 600, 'expoente_cauda': 0.9},
    'demo-davi.zip': {'seed': 61, 'artistas': 120, 'expoente_cauda': 1.5},
}


def empacotar(destino: Path = APP) -> Path:
    from tools.gerar_dados_falsos import Configuracao, gerar_zip

    destino.mkdir(parents=True, exist_ok=True)
    for nome, ajustes in DEMOS.items():
        config = {
            'linhas': 40_000,
            'artistas': 250,
            'nomes_plausiveis': True,
            'proporcao_various_artists': 0,
            **ajustes,
        }
        gerar_zip(destino / nome, Configuracao(**config))
    return destino


if __name__ == '__main__':
    sys.path.insert(0, str(RAIZ))  # como script, o Python só enxerga tools/
    pasta = empacotar(Path(sys.argv[1]) if len(sys.argv) > 1 else APP)
    for nome in DEMOS:
        print(f'{nome}: {(pasta / nome).stat().st_size // 1024} KB')
