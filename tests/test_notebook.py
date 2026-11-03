"""Validação estrutural do notebook didático e dos imports da arquitetura final."""

from __future__ import annotations

import ast
from pathlib import Path

import nbformat


def test_notebook_crisp_dm_valido_sem_servidor_automatico() -> None:
    """As seis fases, imports modulares e padrão fictício permitem execução independente."""
    caminho = Path(__file__).resolve().parents[1] / 'SyncUp.ipynb'
    notebook = nbformat.read(caminho, as_version=4)
    nbformat.validate(notebook)
    titulos = [
        linha
        for celula in notebook.cells
        if celula.cell_type == 'markdown'
        for linha in celula.source.splitlines()
        if linha.startswith('## ')
    ]
    assert titulos == [
        '## 1. Entendimento do negócio',
        '## 2. Entendimento dos dados',
        '## 3. Preparação dos dados',
        '## 4. Modelagem',
        '## 5. Avaliação',
        '## 6. Implantação',
    ]
    importados = set()
    atribuicoes = {}
    for celula in notebook.cells:
        if celula.cell_type != 'code':
            continue
        assert not celula.outputs  # Histórico pessoal nunca vai nas saídas distribuídas.
        tree = ast.parse(celula.source, feature_version=(3, 10))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                importados.add(node.module)
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
                for alvo in node.targets:
                    if isinstance(alvo, ast.Name):
                        atribuicoes[alvo.id] = node.value.value
    assert {'dados', 'analise', 'metricas', 'perfis', 'graficos', 'configuracao'} <= importados
    assert atribuicoes['USAR_DADOS_FICTICIOS'] is True
    assert atribuicoes['ABRIR_INTERFACE'] is False
