"""Marca a versão no endereço dos arquivos do app, só na publicação: ``python tools/versionar_site.py site/app <versão>``.

O GitHub Pages deixa o navegador guardar cada arquivo por 10 minutos. Depois de um deploy, um
arquivo novo podia pedir um antigo ainda no cache (o Match quebrou assim na 1.28). Com ``?v=``
dentro de cada arquivo, o que é novo só pede endereços novos. No repositório nada muda.
"""

# shortcut: uma página antiga ainda no cache pode receber um arquivo novo pelo endereço antigo (a
# publicação não guarda as versões anteriores) e dura até 10 min; guardar uma pasta por versão resolve.

from __future__ import annotations

import re
import sys
from pathlib import Path

# Qualquer texto entre aspas que termine em .js ou .css; só ganha a marca se o arquivo existir.
REFERENCIA = re.compile(r"""(?P<aspas>['"])(?P<ref>[\w./-]+\.(?:js|css))(?P=aspas)""")


def versionar(app: Path, versao: str) -> int:
    total = 0
    arquivos = [*app.rglob('*.html'), *app.rglob('*.js')]
    for arquivo in (a for a in arquivos if 'vendor' not in a.relative_to(app).parts):

        def marcar(m: re.Match, pasta: Path = arquivo.parent) -> str:
            nonlocal total
            ref = m['ref']
            # "./x" parte do arquivo; sem ponto é endereço da página (os Workers), que fica em app/.
            alvo = (pasta if ref.startswith('.') else app) / ref
            if ref.startswith(('../', '/')) and not alvo.resolve().is_relative_to(app.resolve()):
                return m[0]  # fora do app (o estilo.css da página inicial)
            if not alvo.is_file():
                return m[0]
            total += 1
            return f'{m["aspas"]}{ref}?v={versao}{m["aspas"]}'

        texto = arquivo.read_bytes().decode('utf-8')
        novo = REFERENCIA.sub(marcar, texto)
        if novo != texto:
            arquivo.write_bytes(novo.encode('utf-8'))
    return total


if __name__ == '__main__':
    pasta, versao = Path(sys.argv[1]), sys.argv[2]
    n = versionar(pasta, versao)
    if not n:
        sys.exit(f'Nenhuma referência encontrada em {pasta}.')
    print(f'{n} referências marcadas com ?v={versao}')
