"""Fluxo real HTTP do Gradio 5: uploads, dupla, grupo e downloads locais."""

from __future__ import annotations

import json
import os
import sys
import unittest
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

os.environ['GRADIO_ANALYTICS_ENABLED'] = 'False'
RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
import gradio as gr

from dados import limpar_cache
from ui import _limpar_exportacoes, criar_interface


def evento(artista: str, musica: str = 'Faixa') -> dict[str, object]:
    """Constrói dados mínimos independentes de contas reais."""
    return {
        'ts': '2026-01-01T04:00:00Z',
        'ms_played': 60_000,
        'master_metadata_track_name': musica,
        'master_metadata_album_artist_name': artista,
    }


class InterfaceTest(unittest.TestCase):
    """Exercita preprocessamento Gradio de vários arquivos e estado entre cliques."""

    def test_upload_dupla_grupo_e_exportacoes(self) -> None:
        """Uploads passam pelo FileData real; CSV/PNG são baixados via rotas do Gradio."""
        limpar_cache()
        demo = criar_interface()
        self.assertTrue(
            all(
                c.file_count == 'multiple'
                for c in demo.blocks.values()
                if isinstance(c, gr.File) and c.interactive is not False
            )
        )
        self.assertEqual(
            {f.api_name for f in demo.fns.values() if f.api_visibility == 'public'},
            {
                'comparar_dupla',
                'comparar_grupo',
                'exportar_playlist',
                'gerar_cartao',
                'gerar_wrapped',
                'baixar_wrapped',
                'encontrar_matches',
                'playlist_festa',
                'baixar_cartao_match',
                'baixar_sintonia',
                'gerar_convite',
            },
        )
        app = gr.mount_gradio_app(FastAPI(), demo, path='/')
        opcoes = ['America/Sao_Paulo', '', '', 'manter', False, False]
        session = 'syncup-teste-local'
        with (
            TemporaryDirectory() as temp,
            TestClient(app, raise_server_exceptions=False) as cliente,
        ):
            self.assertEqual(cliente.get('/').status_code, 200)
            perfis = [
                [evento('Dream, Ivory'), evento('Carti')],
                [evento('*NSYNC', '=teste')],
                [evento('Dream, Ivory'), evento('Katy Perry')],
                [evento('Dream, Ivory'), evento('Gaga')],
            ]
            uploads = []
            for i, dados in enumerate(perfis):
                p = Path(temp) / f'perfil_{i}.json'
                p.write_text(json.dumps(dados), encoding='utf-8')
                with p.open('rb') as arquivo:
                    resp = cliente.post(
                        '/gradio_api/upload', files={'files': (p.name, arquivo, 'application/json')}
                    )
                self.assertEqual(resp.status_code, 200, resp.text)
                uploads.append(
                    {
                        'path': resp.json()[0],
                        'orig_name': p.name,
                        'meta': {'_type': 'gradio.FileData'},
                    }
                )

            def executar(nome: str, dados: list[object]):
                """Preserva sessão para que State seja reusado nas exportações."""
                resp = cliente.post(
                    f'/gradio_api/run/{nome}', json={'data': dados, 'session_hash': session}
                )
                self.assertEqual(resp.status_code, 200, resp.text)
                return resp.json()['data']

            resultado = executar(
                'comparar_dupla',
                [[uploads[0], uploads[1]], [uploads[2]], '<b>A</b>', 'B', False, 'log1p', *opcoes],
            )
            # 26 saídas históricas + 7 blocos da v0.6 + Wrapped da dupla (v0.7).
            self.assertEqual(len(resultado), 34)
            self.assertIn('Ruzicka', resultado[1])
            self.assertIn('&lt;b&gt;A&lt;/b&gt;', resultado[6])
            self.assertEqual(resultado[20]['data'][0][3], '3')
            csv_saida = executar('exportar_playlist', [None, None])[0]
            baixado = cliente.get(csv_saida['url'])
            self.assertEqual(baixado.status_code, 200)
            self.assertTrue(baixado.content.startswith(b'\xef\xbb\xbf'))
            self.assertIn('Dream, Ivory', baixado.text)
            png_saida = executar('gerar_cartao', [None, None])[1]
            baixado = cliente.get(png_saida['url'])
            self.assertEqual(baixado.status_code, 200)
            with Image.open(BytesIO(baixado.content)) as imagem:
                self.assertEqual(imagem.size, (1080, 1350))
            grupo = executar(
                'comparar_grupo',
                [[uploads[0], uploads[2], uploads[3]], 'A\nB\nC', False, 'raiz', *opcoes],
            )
            self.assertEqual(len(grupo), 7)
            self.assertEqual(len(grupo[1]['data']), 3)
            self.assertIn('Não medem personalidade ou afinidade amorosa', grupo[4])
            # Remove as pastas privadas criadas pelo callback deste teste.
            for state in demo.state_holder.session_data.values():
                for valor in state.state_data.values():
                    if isinstance(valor, list) and all(
                        isinstance(p, str) and Path(p).name.startswith('syncup-') for p in valor
                    ):
                        _limpar_exportacoes(valor)
        limpar_cache()


if __name__ == '__main__':
    unittest.main()
