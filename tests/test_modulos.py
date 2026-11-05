"""Verifica os contratos novos: métricas, deduplicação, validação e cache."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import sys
import tempfile
import unittest
import zipfile
from dataclasses import is_dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from analise import ResultadoComparacao
from app import carregar, comparar, criar_interface, limpar_cache, metricas
from dados import carregar_historico, deduplicar_registros, sha256_arquivo
from metricas import cosseno, jaccard, jaccard_ponderado
from perfis import classificar_arquetipos
from tools.gerar_dados_falsos import Configuracao, gerar_zip


def evento(
    data: str, duracao: int | str, musica: str | None = 'Faixa', artista: str = 'Artista'
) -> dict:
    """Cria um registro mínimo de música ou podcast fictício."""
    return {
        'ts': data,
        'ms_played': duracao,
        'master_metadata_track_name': musica,
        'master_metadata_album_artist_name': artista,
    }


class ModulosTest(unittest.TestCase):
    """Casos pequenos com resultados esperados conhecidos."""

    def setUp(self) -> None:
        """Isola arquivos e cache entre casos."""
        self.temporaria = tempfile.TemporaryDirectory()
        self.pasta = Path(self.temporaria.name)
        limpar_cache()

    def tearDown(self) -> None:
        """Libera os históricos e os arquivos temporários."""
        limpar_cache()
        self.temporaria.cleanup()

    def salvar(self, nome: str, eventos: list[dict]) -> Path:
        """Escreve um JSON de entrada em UTF-8."""
        arquivo = self.pasta / nome
        arquivo.write_text(json.dumps(eventos, ensure_ascii=False), encoding='utf-8-sig')
        return arquivo

    def test_metricas_conhecidas(self) -> None:
        """Confere proporcionalidade, conjuntos disjuntos e ponderação."""
        self.assertAlmostEqual(cosseno({'A': 10, 'B': 20}, {'A': 1, 'B': 2}), 1.0)
        self.assertEqual(metricas({'A': 1}, {'B': 1}), (0.0, 0.0))
        self.assertEqual(jaccard({'A', 'B'}, {'B', 'C'}), 1 / 3)
        self.assertEqual(jaccard_ponderado({'A': 2, 'B': 1}, {'A': 1, 'C': 1}), 1 / 4)
        self.assertEqual(metricas({}, {}), (None, None))
        self.assertEqual(metricas({'A': 0}, {'A': 2}), (None, 0.0))
        self.assertIsNone(jaccard_ponderado({}, {}))
        for invalido in (-1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                cosseno({'A': invalido}, {'A': 1})
            with self.assertRaises(ValueError):
                jaccard_ponderado({'A': invalido}, {'A': 1})

    def test_limites_arquetipos(self) -> None:
        """Inclui os valores exatamente iguais aos limiares nomeados."""
        artistas = {'A': 3, 'B': 3, 'C': 2, 'D': 2}
        faixas = {(str(i), 'A'): 1 for i in range(10)}
        resultado = classificar_arquetipos(artistas, faixas, 10, 4)
        self.assertEqual(resultado.favoritos.nome, 'Fiel aos favoritos')
        self.assertEqual(resultado.favoritos.proporcao, 0.6)
        self.assertEqual(resultado.madrugada.nome, 'Coruja musical')
        self.assertEqual(resultado.madrugada.proporcao, 0.4)
        with self.assertRaises(ValueError):
            classificar_arquetipos({}, {}, 0, 0)

    def test_limpeza_fuso_duracoes_e_podcasts(self) -> None:
        """Remove registros inválidos, guarda plays curtos e converte UTC para Brasília."""
        arquivo = self.salvar(
            'a.json',
            [
                evento('2026-01-01T02:30:00Z', 60_000, '  Faixa  ', '  Artista  '),
                evento('2026-01-01T04:00:00Z', '29999'),
                evento('ruim', 60_000),
                evento('2026-01-01T04:00:00Z', -1),
                evento('2026-01-01T04:00:00Z', 60_000, None),
                evento('2026-01-01T04:00:00Z', 60_000, '(Falsa) Esperança'),
                evento('2026-01-01T04:00:00Z', 60_000, '   '),
            ],
        )
        dados = carregar(arquivo)
        self.assertEqual(len(dados), 2)
        self.assertEqual(dados.iloc[0].data.month, 12)
        self.assertEqual(dados.iloc[0].musica, 'Faixa')
        self.assertEqual(dados.iloc[0].artista, 'Artista')
        resultado = comparar(arquivo, arquivo, 'A', 'B', False)
        self.assertEqual(resultado.perfil_a.plays, 1)
        self.assertAlmostEqual(resultado.perfil_a.horas, (60_000 + 29_999) / 3_600_000)
        self.assertEqual(resultado.status_arquivos, 'bytes_identicos')

    def test_deduplicacao_optativa(self) -> None:
        """Preserva plays por padrão e remove apenas chaves coincidentes quando solicitado."""
        repetido = evento('2026-01-01T04:00:00Z', 60_000)
        arquivo = self.salvar(
            'a.json', [repetido, repetido.copy(), evento('2026-01-01T04:10:00Z', 60_000)]
        )
        self.assertEqual(len(carregar(arquivo)), 3)
        self.assertEqual(len(deduplicar_registros(carregar(arquivo))), 2)
        h = carregar_historico(arquivo, deduplicar=True)
        self.assertEqual(h.registros_antes_deduplicacao, 3)
        self.assertEqual(h.duplicados_removidos, 1)
        resultado = comparar(arquivo, arquivo, 'A', 'B', deduplicar=True)
        self.assertTrue(resultado.deduplicacao_ativa)
        self.assertEqual(resultado.perfil_a.plays, 2)
        self.assertEqual(resultado.duplicados_removidos_a, 1)

    def test_cache_e_hash(self) -> None:
        """Edições no DataFrame não contaminam o cache; mudança no arquivo é relida."""
        arquivo = self.salvar('a.json', [evento('2026-01-01T04:00:00Z', 60_000)])
        original = carregar(arquivo)
        original['artista'] = original.artista.cat.add_categories(['Alteração'])
        original.loc[original.index[0], 'artista'] = 'Alteração'
        self.assertEqual(carregar(arquivo).iloc[0].artista, 'Artista')
        hash_anterior = sha256_arquivo(arquivo)
        self.salvar('a.json', [evento('2026-01-01T04:00:00Z', 70_000)])
        # Mesmo tamanho regravado no mesmo instante teria a mesma data: avança 1 s, como na vida real.
        estado = arquivo.stat()
        os.utime(arquivo, ns=(estado.st_atime_ns, estado.st_mtime_ns + 1_000_000_000))
        h = carregar_historico(arquivo)
        self.assertEqual(h.dados.iloc[0].ms_played, 70_000)
        self.assertNotEqual(h.sha256, hash_anterior)
        self.assertEqual(h.sha256, hashlib.sha256(arquivo.read_bytes()).hexdigest())

    def test_cobertura_sem_sobreposicao(self) -> None:
        """Recusa cobertura comum inexistente e aceita históricos completos."""
        a = self.salvar('a.json', [evento('2026-01-01T04:00:00Z', 60_000)])
        b = self.salvar('b.json', [evento('2026-05-01T04:00:00Z', 60_000)])
        with self.assertRaisesRegex(ValueError, 'período de cobertura'):
            comparar(a, b, 'A', 'B')
        resultado = comparar(a, b, 'A', 'B', False)
        self.assertIsInstance(resultado, ResultadoComparacao)
        self.assertTrue(is_dataclass(resultado))
        self.assertFalse(resultado.periodo.comum)
        self.assertIsNone(resultado.periodo.inicio)
        self.assertAlmostEqual(resultado.metricas.cosseno, 1.0)

    def test_zip_reproduzivel_e_campos(self) -> None:
        """Confere tamanho, campos especiais, cauda longa e ZIP determinístico."""
        config = Configuracao(linhas=1_000, artistas=40, seed=12, tamanho_bloco=200)
        a = gerar_zip(self.pasta / 'a.zip', config)
        b = gerar_zip(self.pasta / 'b.zip', config)
        self.assertEqual(a.read_bytes(), b.read_bytes())
        with zipfile.ZipFile(a) as pacote:
            eventos = []
            for nome in pacote.namelist():
                conteudo = json.loads(pacote.read(nome))
                if isinstance(conteudo, list):
                    eventos.extend(conteudo)
        self.assertEqual(len(eventos), 1_000)
        self.assertTrue(any(e['episode_name'] for e in eventos))
        self.assertTrue(
            any(e['master_metadata_album_artist_name'] == 'Various Artists' for e in eventos)
        )
        self.assertTrue(
            {'ip_addr', 'platform', 'reason_end', 'skipped', 'shuffle'} <= eventos[0].keys()
        )
        h = carregar_historico(a)
        self.assertNotIn('ip_addr', h.dados.columns)
        self.assertEqual(h.dados.artista.nunique(), 41)
        self.assertEqual(comparar(a, b, 'A', 'B').status_arquivos, 'bytes_identicos')

    def test_nucleo_sem_ui_ou_numpy(self) -> None:
        """Inspeciona imports: núcleo sem interface e projeto sem NumPy direto."""
        for nome in ('metricas.py', 'perfis.py', 'dados.py', 'analise.py', 'app.py'):
            arvore = ast.parse((RAIZ / nome).read_text(encoding='utf-8'))
            for node in ast.walk(arvore):
                imports = (
                    [alias.name for alias in node.names]
                    if isinstance(node, ast.Import)
                    else [node.module or '']
                    if isinstance(node, ast.ImportFrom)
                    else []
                )
                self.assertFalse(any(n.split('.')[0] == 'numpy' for n in imports))
                if nome != 'app.py':
                    self.assertFalse(
                        any(n.split('.')[0] in {'ui', 'app', 'gradio', 'plotly'} for n in imports)
                    )
        self.assertTrue(callable(criar_interface))


if __name__ == '__main__':
    unittest.main()
