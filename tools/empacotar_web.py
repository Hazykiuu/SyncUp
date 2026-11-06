"""Empacota o núcleo do SyncUp para o app no navegador (Pyodide).

Parte de ``web/ponte.py`` e segue só os imports que rodam de verdade (ignora os de
``if TYPE_CHECKING``). Recusa qualquer módulo que importe Gradio, FastAPI, httpx ou
uvicorn: no navegador eles não existem. Uso: ``python tools/empacotar_web.py``.
"""

from __future__ import annotations

import ast
import shutil
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / 'site' / 'app' / 'syncup-core.zip'
ENTRADAS = ('web/ponte.py', 'tools/gerar_dados_falsos.py')
PROIBIDOS = {'gradio', 'fastapi', 'httpx', 'uvicorn', 'starlette'}
EXTRAS = ('fontes/Figtree.ttf', 'fontes/OFL.txt', 'web/__init__.py')


def _imports(arquivo: Path) -> set[str]:
    """Módulos importados em tempo de execução (fora de ``if TYPE_CHECKING``)."""
    arvore = ast.parse(arquivo.read_text(encoding='utf-8'))
    ignorados = {
        id(no)
        for bloco in ast.walk(arvore)
        if isinstance(bloco, ast.If) and getattr(bloco.test, 'id', '') == 'TYPE_CHECKING'
        for no in ast.walk(bloco)
    }
    nomes: set[str] = set()
    for no in ast.walk(arvore):
        if id(no) in ignorados:
            continue
        if isinstance(no, ast.Import):
            nomes.update(a.name for a in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module and not no.level:
            nomes.add(no.module)
    return nomes


def _caminho(modulo: str) -> Path | None:
    """Arquivo local de um módulo do projeto (``dados`` → ``dados.py``), se existir."""
    candidato = RAIZ / (modulo.replace('.', '/') + '.py')
    return candidato if candidato.is_file() else None


def modulos() -> list[Path]:
    """Fecho de dependências locais a partir das entradas; falha se tocar num proibido."""
    pendentes = [RAIZ / e for e in ENTRADAS]
    vistos: dict[Path, None] = {}
    while pendentes:
        arquivo = pendentes.pop()
        if arquivo in vistos:
            continue
        vistos[arquivo] = None
        for modulo in _imports(arquivo):
            if modulo.split('.')[0] in PROIBIDOS:
                raise SystemExit(
                    f'{arquivo.relative_to(RAIZ)} importa {modulo}: não roda no navegador.'
                )
            local = _caminho(modulo)
            if local is not None:
                pendentes.append(local)
    return sorted(vistos, key=lambda p: p.relative_to(RAIZ).as_posix())


def empacotar(destino: Path = DESTINO) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destino, 'w', zipfile.ZIP_DEFLATED) as pacote:
        for arquivo in [*modulos(), *(RAIZ / e for e in EXTRAS)]:
            pacote.write(arquivo, arquivo.relative_to(RAIZ).as_posix())
    # O HTML do núcleo (Blend, stories, corrida) usa as mesmas classes e animações do app local.
    shutil.copyfile(RAIZ / 'styles.css', destino.parent / 'componentes.css')
    # syncup.js é uma função solta (o Gradio a executa); no app ela é chamada direto.
    js = (RAIZ / 'syncup.js').read_text(encoding='utf-8').strip()
    (destino.parent / 'componentes.js').write_text(f'({js})();\n', encoding='utf-8')
    return destino


if __name__ == '__main__':
    saida = empacotar(Path(sys.argv[1]) if len(sys.argv) > 1 else DESTINO)
    with zipfile.ZipFile(saida) as pacote:
        nomes = pacote.namelist()
    print(
        f'{saida.relative_to(RAIZ) if saida.is_relative_to(RAIZ) else saida}: '
        f'{len(nomes)} arquivos, {saida.stat().st_size // 1024} KB'
    )
