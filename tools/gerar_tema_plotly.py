"""Gera site/app/js/tema-plotly.js: o tema 'plotly_dark' do Plotly em JSON, para os gráficos da Dupla.

O app do navegador monta os gráficos em JS (sem o Plotly do Python); o tema é o mesmo que o
Python embute em cada figura. Rodar depois de atualizar o plotly:
    .venv/Scripts/python.exe tools/gerar_tema_plotly.py
tests/test_paridade_dupla.py confere que o arquivo bate com o plotly instalado.
"""

from __future__ import annotations

import json
from pathlib import Path

DESTINO = Path(__file__).resolve().parents[1] / 'site' / 'app' / 'js' / 'tema-plotly.js'


def conteudo() -> str:
    import plotly.io as pio

    tema = pio.templates['plotly_dark'].to_plotly_json()
    return (
        '// Gerado por tools/gerar_tema_plotly.py: o tema plotly_dark do Plotly. Não editar à mão.\n'
        f'export const TEMA = {json.dumps(tema, ensure_ascii=False, separators=(",", ":"))};\n'
    )


if __name__ == '__main__':
    DESTINO.write_bytes(conteudo().encode('utf-8'))
    print(f'{DESTINO} ({DESTINO.stat().st_size} bytes)')
