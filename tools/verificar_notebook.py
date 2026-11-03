"""Valida células do notebook em IPython, sem servidor Jupyter ou portas de rede.

Uso: python tools/verificar_notebook.py
A demonstração padrão deve manter USAR_DADOS_FICTICIOS=True e ABRIR_INTERFACE=False.
Os dados/exports são gerados somente em uma cópia temporária dos módulos.
"""

from __future__ import annotations

import ast
import json
import os
import shutil
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import nbformat
import plotly.io as pio
from IPython.core.interactiveshell import InteractiveShell
from IPython.utils.io import capture_output
from PIL import Image


def verificar_notebook(raiz: Path) -> dict[str, Any]:
    """Executa as células em ordem e falha no primeiro erro, usando dados locais fictícios.

    Não testa a interface gráfica do Jupyter ou seu protocolo de kernel.
    Exercita o código real de ingestão, EDA, métricas, grupo, plots e exportações.
    """
    notebook = nbformat.read(raiz / 'SyncUp.ipynb', as_version=4)
    nbformat.validate(notebook)
    parametros = {}
    for celula in notebook.cells:
        if celula.cell_type != 'code':
            continue
        for node in ast.walk(ast.parse(celula.source)):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
                for alvo in node.targets:
                    if isinstance(alvo, ast.Name):
                        parametros[alvo.id] = node.value.value
    if (
        parametros.get('USAR_DADOS_FICTICIOS') is not True
        or parametros.get('ABRIR_INTERFACE') is not False
    ):
        raise ValueError(
            'A validação exige dados fictícios ativados e interface automática desativada.'
        )
    inicio = time.perf_counter()
    cwd_anterior, sys_path_anterior = Path.cwd(), sys.path.copy()
    renderer_anterior = pio.renderers.default
    try:
        with TemporaryDirectory(prefix='syncup-notebook-') as temporaria:
            copia = Path(temporaria)
            for fonte in raiz.glob('*.py'):
                shutil.copy2(fonte, copia / fonte.name)
            shutil.copy2(raiz / 'styles.css', copia / 'styles.css')
            (copia / 'tools').mkdir()
            shutil.copy2(
                raiz / 'tools' / 'gerar_dados_falsos.py', copia / 'tools' / 'gerar_dados_falsos.py'
            )
            os.chdir(copia)
            sys.path.insert(0, str(copia))
            # Captura representação interativa, sem abrir um navegador para cada figura.
            pio.renderers.default = 'plotly_mimetype'
            shell = InteractiveShell()
            executadas = 0
            with capture_output():
                for indice, celula in enumerate(notebook.cells, 1):
                    if celula.cell_type != 'code':
                        continue
                    resultado = shell.run_cell(celula.source, store_history=False)
                    erro = resultado.error_before_exec or resultado.error_in_exec
                    if erro is not None:
                        raise RuntimeError(f'Erro na célula {indice}: {erro}') from erro
                    executadas += 1
            csv = copia / 'exportacoes_notebook' / 'playlist_comum.csv'
            if not csv.is_file():
                raise RuntimeError('A célula de implantação não produziu o CSV.')
            with Image.open(copia / 'exportacoes_notebook' / 'cartao.png') as imagem:
                if imagem.size != (1080, 1350):
                    raise RuntimeError('O cartão produzido não possui 1080×1350 pixels.')
            return {
                'celulas_total': len(notebook.cells),
                'celulas_codigo_executadas': executadas,
                'erros': 0,
                'segundos': round(time.perf_counter() - inicio, 3),
                'modo': 'IPython no mesmo processo, sem protocolo de kernel Jupyter',
                'dados': 'ficticios',
                'interface_iniciada': False,
            }
    finally:
        os.chdir(cwd_anterior)
        sys.path[:] = sys_path_anterior
        pio.renderers.default = renderer_anterior


if __name__ == '__main__':
    print(
        json.dumps(
            verificar_notebook(Path(__file__).resolve().parents[1]), ensure_ascii=False, indent=2
        )
    )
