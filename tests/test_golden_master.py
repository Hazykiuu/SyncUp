"""Registra a v0.4 congelada e verifica a v0.5 com entradas fictícias idênticas.

Registro explícito: python tests/test_golden_master.py --registrar
Regressão: python -m unittest discover -s tests -v
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[1]
GOLDEN = RAIZ / 'tests' / 'golden'
BASELINE = RAIZ / 'tests' / 'fixtures' / 'v04'
ARQUIVO_GOLDEN = GOLDEN / 'comparacao_v04.json'
sys.path.insert(0, str(RAIZ))
from apoio_golden import assert_tabela_golden, contagens_ranking

from tools.gerar_dados_falsos import Configuracao, gerar_zip

CONFIG_A = Configuracao(linhas=1_200, artistas=60, seed=41, tamanho_bloco=250)
CONFIG_B = Configuracao(linhas=1_200, artistas=60, seed=97, tamanho_bloco=250)


def preparar_entradas(pasta: Path) -> tuple[Path, Path]:
    """Gera os dois perfis pequenos e determinísticos usados na regressão."""
    return gerar_zip(pasta / 'perfil_a.zip', CONFIG_A), gerar_zip(pasta / 'perfil_b.zip', CONFIG_B)


def serializar_saidas(saidas: list[Any] | tuple[Any, ...]) -> list[Any]:
    """Serializa todas as doze saídas: textos, figuras Plotly e tabelas com tipos."""
    import pandas as pd
    from plotly.graph_objects import Figure

    serializado: list[Any] = []
    for valor in saidas:
        if isinstance(valor, pd.DataFrame):
            serializado.append(
                {
                    'tipo': 'dataframe',
                    'dtypes': valor.dtypes.astype(str).tolist(),
                    'valor': json.loads(
                        valor.to_json(orient='split', date_format='iso', double_precision=15)
                    ),
                }
            )
        elif isinstance(valor, Figure):
            serializado.append({'tipo': 'plotly', 'valor': json.loads(valor.to_json())})
        elif isinstance(valor, str):
            serializado.append({'tipo': 'texto', 'valor': valor})
        else:
            raise TypeError(f'Tipo inesperado: {type(valor).__name__}')
    return serializado


def executar_v04(a: Path, b: Path, destino: Path) -> None:
    """Executa exclusivamente a v0.4 em um processo com sua própria interface."""
    sys.path.insert(0, str(BASELINE))
    import pandas as pd
    import plotly

    import app as baseline

    referencias: dict[str, Any] = {}
    for comum in (True, False):
        baseline.limpar_cache()
        saidas = baseline.comparar(str(a), str(b), 'Perfil A', 'Perfil B', comum)
        referencias['comum' if comum else 'completo'] = serializar_saidas(saidas)
    fontes = {
        nome: hashlib.sha256((BASELINE / nome).read_bytes()).hexdigest()
        for nome in ('app.py', 'ui.py', 'requirements.txt')
    }
    with zipfile.ZipFile(a) as pacote:
        configuracao_a = json.loads(pacote.read('DADOS_FICTICIOS.json'))['configuracao']
    with zipfile.ZipFile(b) as pacote:
        configuracao_b = json.loads(pacote.read('DADOS_FICTICIOS.json'))['configuracao']
    referencia = {
        'versao': '0.4',
        'ambiente': {
            'python': sys.version.split()[0],
            'pandas': pd.__version__,
            'plotly': plotly.__version__,
        },
        'fontes_sha256': fontes,
        'config_a': configuracao_a,
        'config_b': configuracao_b,
        'resultados': referencias,
    }
    texto = json.dumps(referencia, ensure_ascii=False, indent=2) + '\n'
    destino.write_text(texto, encoding='utf-8')


def registrar() -> None:
    """Cria a referência apenas sob solicitação explícita; testes não a sobrescrevem."""
    GOLDEN.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporaria:
        a, b = preparar_entradas(Path(temporaria))
        subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                '--worker-v04',
                str(a),
                str(b),
                str(ARQUIVO_GOLDEN),
            ],
            check=True,
        )
    print(f'Referência v0.4 registrada em {ARQUIVO_GOLDEN}')


class GoldenMasterTest(unittest.TestCase):
    """Protege os resultados existentes sem usar dados pessoais."""

    @classmethod
    def setUpClass(cls) -> None:
        """Carrega a referência registrada e gera suas entradas correspondentes."""
        cls.temporaria = tempfile.TemporaryDirectory()
        cls.a, cls.b = preparar_entradas(Path(cls.temporaria.name))
        cls.referencia = json.loads(ARQUIVO_GOLDEN.read_text(encoding='utf-8'))

    @classmethod
    def tearDownClass(cls) -> None:
        """Remove as entradas temporárias de teste."""
        cls.temporaria.cleanup()

    def verificar(self, comum: bool) -> None:
        """Confere todas as saídas da apresentação, mantendo o núcleo estruturado."""
        from analise import ResultadoComparacao
        from app import comparar
        from ui import grafico_artistas, grafico_meses

        resultado = comparar(self.a, self.b, 'Perfil A', 'Perfil B', comum)
        self.assertIsInstance(resultado, ResultadoComparacao)
        chave = 'comum' if comum else 'completo'
        esperado = self.referencia['resultados'][chave]
        # Os dados antigos permanecem como referência; apresentação e Diagnóstico mudaram na Fase 2.
        tabelas = {
            2: resultado.perfil_a.artistas,
            3: resultado.perfil_b.artistas,
            4: resultado.perfil_a.musicas,
            5: resultado.perfil_b.musicas,
            9: resultado.estatisticas,
        }
        for indice, tabela in tabelas.items():
            with self.subTest(saida=indice, periodo=chave):
                contagens = None
                if indice in (2, 3, 4, 5):
                    chaves = ['Artista'] if indice in (2, 3) else ['musica', 'artista']
                    arquivo = self.a if indice in (2, 4) else self.b
                    contagens = contagens_ranking(arquivo, resultado.periodo, chaves)
                assert_tabela_golden(tabela, esperado[indice], contagens)
        figuras = {
            1: grafico_artistas(resultado.participacao_artistas, resultado.ordem_artistas),
            11: grafico_meses(resultado),
        }
        for indice, figura in figuras.items():
            self.assertEqual(
                json.loads(figura.to_json())['data'], esperado[indice]['valor']['data']
            )
        arquivo = GOLDEN / (
            'comparacao_passo1_300k.json'
            if CONFIG_A.linhas == 300_000
            else 'comparacao_passo1.json'
        )
        numeros = json.loads(arquivo.read_text(encoding='utf-8'))[chave]
        for campo, valor in asdict(resultado.metricas).items():
            self.assertAlmostEqual(valor, numeros['metricas'][campo], places=12)
        for perfil, anterior in zip((resultado.perfil_a, resultado.perfil_b), numeros['perfis']):
            self.assertEqual(perfil.plays, anterior['plays'])
            self.assertEqual(perfil.quantidade_artistas, anterior['quantidade_artistas'])
            self.assertAlmostEqual(perfil.horas, anterior['horas'], places=10)
            for campo, dimensao in asdict(perfil.arquetipos).items():
                self.assertEqual(dimensao['nome'], anterior['arquetipos'][campo]['nome'])
                self.assertAlmostEqual(
                    dimensao['proporcao'], anterior['arquetipos'][campo]['proporcao'], places=12
                )

    def test_periodo_comum(self) -> None:
        """Confere a cobertura comum."""
        self.verificar(True)

    def test_historicos_completos(self) -> None:
        """Confere os históricos completos."""
        self.verificar(False)

    def test_baseline_congelada(self) -> None:
        """Detecta alterações no código que produziu a referência."""
        for nome, esperado in self.referencia['fontes_sha256'].items():
            self.assertEqual(hashlib.sha256((BASELINE / nome).read_bytes()).hexdigest(), esperado)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registrar', action='store_true')
    parser.add_argument(
        '--escala-grande',
        action='store_true',
        help='Usa 300 mil eventos e 3 mil artistas em cada perfil.',
    )
    parser.add_argument('--worker-v04', nargs=3, metavar=('A', 'B', 'SAIDA'))
    args, desconhecidos = parser.parse_known_args()
    if args.escala_grande:
        CONFIG_A = replace(CONFIG_A, linhas=300_000, artistas=3_000, tamanho_bloco=25_000)
        CONFIG_B = replace(CONFIG_B, linhas=300_000, artistas=3_000, tamanho_bloco=25_000)
        ARQUIVO_GOLDEN = GOLDEN / 'comparacao_v04_300k.json'
    if args.worker_v04:
        executar_v04(*(Path(valor) for valor in args.worker_v04))
    elif args.registrar:
        registrar()
    else:
        unittest.main(argv=[sys.argv[0], *desconhecidos])
