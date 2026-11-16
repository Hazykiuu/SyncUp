"""Prepara os arquivos gerados do app no navegador (``site/app``). Uso: ``python tools/empacotar_web.py``.

Desde a 1.11 a Dupla e o Wrapped rodam em JavaScript, sem Python no navegador. Sobram três tarefas:
- ``componentes.css`` e ``componentes.js``: o visual das listas, da corrida e dos stories (o mesmo do
  app para PC, ``styles.css`` e ``syncup.js``);
- ``demo-wrapped.zip`` e ``demo-bruno.zip``: os dois históricos fictícios do "Testar com dados
  fictícios" (Ana e Bruno, os mesmos de ``web.ponte.arquivos_demo``).
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
APP = RAIZ / 'site' / 'app'
# Ana também é a demo do Wrapped; Bruno completa a dupla (sementes de ponte.arquivos_demo).
DEMOS = {'demo-wrapped.zip': 41, 'demo-bruno.zip': 97}


def empacotar(destino: Path = APP) -> Path:
    from tools.gerar_dados_falsos import Configuracao, gerar_zip

    destino.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(RAIZ / 'styles.css', destino / 'componentes.css')
    # syncup.js é uma função solta (o Gradio a executa); no app ela é chamada direto.
    js = (RAIZ / 'syncup.js').read_text(encoding='utf-8').strip()
    (destino / 'componentes.js').write_text(f'({js})();\n', encoding='utf-8')
    for nome, semente in DEMOS.items():
        gerar_zip(destino / nome, Configuracao(linhas=40_000, artistas=250, seed=semente))
    return destino


if __name__ == '__main__':
    sys.path.insert(0, str(RAIZ))  # como script, o Python só enxerga tools/
    pasta = empacotar(Path(sys.argv[1]) if len(sys.argv) > 1 else APP)
    for nome in ('componentes.css', 'componentes.js', *DEMOS):
        print(f'{nome}: {(pasta / nome).stat().st_size // 1024} KB')
