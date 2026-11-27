"""A publicação marca a versão no endereço dos arquivos do app (tools/versionar_site.py).

Sem isso, até 10 min depois de um deploy o navegador juntava um arquivo novo com um antigo do cache.
"""

import re
import shutil
from pathlib import Path

from tools.versionar_site import versionar

APP = Path(__file__).resolve().parents[1] / 'site' / 'app'


def test_todo_endereco_de_modulo_worker_e_estilo_leva_a_versao(tmp_path):
    app = tmp_path / 'app'
    shutil.copytree(APP, app, ignore=shutil.ignore_patterns('*.zip'))
    versionar(app, 'abc1234')

    arquivos = [p for p in app.rglob('*.js') if 'vendor' not in p.parts]
    textos = {p: p.read_text(encoding='utf-8') for p in arquivos}
    imports = [(p, m) for p, s in textos.items() for m in re.findall(r"from '(\.[^']+)'", s)]
    workers = [
        (p, m) for p, s in textos.items() for m in re.findall(r"['\"]([\w-]+-worker\.js[^'\"]*)", s)
    ]
    pagina = (app / 'index.html').read_text(encoding='utf-8')
    da_pagina = re.findall(r'(?:src|href)="((?!\.\./|https?:|#)[^"]+\.(?:js|css)[^"]*)"', pagina)
    mapa = re.findall(r'"preact-htm": "([^"]+)"', pagina)

    assert len(imports) > 50 and len(workers) >= 5 and len(da_pagina) >= 5 and mapa
    for _, ref in imports + workers:
        assert ref.endswith('.js?v=abc1234'), ref
    for ref in da_pagina + mapa:
        assert ref.endswith('?v=abc1234'), ref
    # o que foi marcado existe: sem a marca, o caminho continua o mesmo
    for origem, ref in imports:
        assert (origem.parent / ref.split('?')[0]).is_file(), ref
    for _, ref in workers:
        assert (app / ref.split('?')[0]).is_file(), ref


def test_o_que_nao_e_arquivo_do_app_fica_como_esta(tmp_path):
    (tmp_path / 'a.js').write_text(
        "import x from './b.js';\nconst n = 'dados.json', u = 'https://x.test/c.js', z = './nao-existe.js';\n",
        encoding='utf-8',
    )
    (tmp_path / 'b.js').write_text('export default 1;\n', encoding='utf-8')
    versionar(tmp_path, 'v9')
    texto = (tmp_path / 'a.js').read_text(encoding='utf-8')
    assert "'./b.js?v=v9'" in texto
    assert (
        "'dados.json'" in texto
        and "'https://x.test/c.js'" in texto
        and "'./nao-existe.js'" in texto
    )
