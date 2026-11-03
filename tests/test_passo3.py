"""Validação de métricas, sincronização, grupo, exportação e gráficos novos."""

from __future__ import annotations

import ast
import csv
import json
import math
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PIL import Image, ImageFont

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from analise import EntradaPerfil, comparar, comparar_grupo
from cartao import carregar_fonte, gerar_cartao
from configuracao import ConfiguracaoCarga
from dados import carregar, carregar_historicos, limpar_cache
from exportacoes import exportar_playlist
from graficos import butterfly, mapa_horarios, matriz_grupo, radar_tracos, slope_chart
from metricas import (
    contribuicoes_cosseno,
    cosseno,
    entropia_normalizada,
    gini,
    jaccard_ponderado,
    ponderar_contagens,
)
from recursos import link_spotify, momentos_sincronizados


def evento(
    data: str = '2026-01-01T04:00:00Z', artista: str = 'Dream, Ivory', musica: str = 'Faixa'
) -> dict[str, object]:
    """Constrói um evento musical mínimo válido."""
    return {
        'ts': data,
        'ms_played': 60_000,
        'master_metadata_track_name': musica,
        'master_metadata_album_artist_name': artista,
    }


class Passo3Test(unittest.TestCase):
    """Confere resultados conhecidos e bordas que mudam a interpretação."""

    def setUp(self) -> None:
        """Cria perfis fictícios isolados e limpa o cache."""
        self.temp = TemporaryDirectory()
        self.pasta = Path(self.temp.name)
        limpar_cache()
        self.a = self.salvar(
            'a.json',
            [evento()] * 4
            + [evento(artista='Playboi Carti')] * 9
            + [evento(artista='+Prince', musica='=Faixa')]
            + [evento(artista='X', musica='Homônima')],
        )
        self.b = self.salvar(
            'b.json',
            [evento()] * 2
            + [evento(artista='Katy Perry')] * 8
            + [evento(artista='+Prince', musica='=Faixa')]
            + [evento(artista='Y', musica='Homônima')],
        )

    def tearDown(self) -> None:
        """Remove apenas entradas e saídas temporárias deste caso."""
        limpar_cache()
        self.temp.cleanup()

    def salvar(self, nome: str, eventos: list[dict[str, object]]) -> Path:
        """Grava JSON com nomes em UTF-8."""
        caminho = self.pasta / nome
        caminho.write_text(json.dumps(eventos, ensure_ascii=False), encoding='utf-8')
        return caminho

    def test_ponderacao_e_contribuicoes(self) -> None:
        """Contribuições somam o cosseno em cada transformação e exclusivos dão zero."""
        a, b = {'A': 9, 'B': 4, 'C': 1}, {'A': 2, 'B': 4, 'D': 7}
        self.assertEqual(ponderar_contagens(a, 'raiz'), {'A': 3, 'B': 2, 'C': 1})
        self.assertEqual(ponderar_contagens({'A': 0}, 'log1p'), {'A': 0})
        self.assertAlmostEqual(ponderar_contagens({'A': 9}, 'log1p')['A'], math.log(10))
        for modo in ('bruta', 'raiz', 'log1p'):
            aa, bb = ponderar_contagens(a, modo), ponderar_contagens(b, modo)
            contribuicoes = contribuicoes_cosseno(aa, bb)
            self.assertAlmostEqual(sum(contribuicoes.values()), cosseno(aa, bb), places=14)
            self.assertEqual(contribuicoes['C'], 0)
            self.assertEqual(contribuicoes['D'], 0)
        self.assertEqual(contribuicoes_cosseno({}, {'A': 1}), {'A': 0})
        with self.assertRaises(ValueError):
            ponderar_contagens(a, 'inexistente')

    def test_entropia_gini_e_ruzicka(self) -> None:
        """Uniformidade, categoria única, desigualdade e ausência têm resultados explícitos."""
        self.assertAlmostEqual(entropia_normalizada({'A': 1, 'B': 1, 'C': 1}), 1)
        self.assertEqual(gini({'A': 1, 'B': 1, 'C': 1}), 0)
        self.assertEqual(entropia_normalizada({'A': 9}), 0)
        self.assertEqual(gini({'A': 9}), 0)
        self.assertAlmostEqual(gini({'A': 1, 'B': 3}), 0.25)
        self.assertLess(entropia_normalizada({'A': 1, 'B': 3}), 1)
        self.assertIsNone(entropia_normalizada({'A': 0}))
        self.assertIsNone(gini({}))
        self.assertAlmostEqual(jaccard_ponderado({'A': 2, 'B': 1}, {'A': 1, 'C': 1}), 0.25)
        for funcao in (entropia_normalizada, gini):
            with self.assertRaises(ValueError):
                funcao({'A': float('nan')})

    def test_comparacao_aplica_pesos_sem_mudar_plays_ou_diversidade(self) -> None:
        """Transformação altera somente os pesos das métricas correspondentes."""
        bruta = comparar(self.a, self.b, 'A', 'B', False)
        for modo in ('raiz', 'log1p'):
            r = comparar(self.a, self.b, 'A', 'B', False, ponderacao=modo)
            aa = ponderar_contagens(r.perfil_a.contagens_artistas, modo)
            bb = ponderar_contagens(r.perfil_b.contagens_artistas, modo)
            self.assertAlmostEqual(r.metricas.cosseno, cosseno(aa, bb))
            self.assertAlmostEqual(r.metricas.jaccard_ponderado, jaccard_ponderado(aa, bb))
            self.assertAlmostEqual(
                r.contribuicoes['Contribuição ao cosseno'].sum(), r.metricas.cosseno
            )
            self.assertEqual(r.perfil_a.plays, bruta.perfil_a.plays)
            self.assertEqual(r.perfil_a.entropia, bruta.perfil_a.entropia)
            self.assertEqual(r.metricas.jaccard, bruta.metricas.jaccard)
        self.assertNotAlmostEqual(bruta.metricas.cosseno, r.metricas.cosseno)

    def test_sincronia_cruza_horas_e_limite_inclusivo(self) -> None:
        """Uma hora exata entra, uma hora e um segundo não; não usa buckets arredondados."""
        a = carregar(
            self.salvar('sa.json', [evento('2026-01-01T00:50:00Z'), evento('2026-01-02T00:00:00Z')])
        )
        b = carregar(
            self.salvar('sb.json', [evento('2026-01-01T01:50:00Z'), evento('2026-01-02T01:00:01Z')])
        )
        r = momentos_sincronizados(a, b)
        self.assertEqual(r.total_pares, 1)
        self.assertEqual(r.exemplos['Distância (min)'].iloc[0], 60)
        self.assertEqual(momentos_sincronizados(a, b, janela_horas=0).total_pares, 0)

    def test_sincronia_nao_reutiliza_evento_e_distingue_musica(self) -> None:
        """Duas execuções não multiplicam um evento do outro perfil; título importa no modo música."""
        a = carregar(self.salvar('sa.json', [evento(), evento()]))
        b = carregar(self.salvar('sb.json', [evento(musica='Outra')]))
        self.assertEqual(momentos_sincronizados(a, b, 'artista').total_pares, 1)
        self.assertEqual(momentos_sincronizados(a, b, 'musica').total_pares, 0)
        for janela in (-1, float('inf'), float('nan')):
            with self.assertRaises(ValueError):
                momentos_sincronizados(a, b, janela_horas=janela)

    def test_sincronia_usa_utc_em_hora_local_repetida(self) -> None:
        """Duas horas locais iguais durante DST não são instantes idênticos."""
        config = ConfiguracaoCarga(fuso_horario='America/New_York')
        a = carregar(self.salvar('sa.json', [evento('2025-11-02T05:30:00Z')]), configuracao=config)
        b = carregar(self.salvar('sb.json', [evento('2025-11-02T06:30:00Z')]), configuracao=config)
        self.assertEqual(a.iloc[0].data, b.iloc[0].data)
        self.assertEqual(momentos_sincronizados(a, b, janela_horas=0.5).total_pares, 0)
        self.assertEqual(momentos_sincronizados(a, b).total_pares, 1)

    def test_sincronia_total_com_exemplos_limitados(self) -> None:
        """O limite de 200 linhas não limita o total exato de pares."""
        a = carregar(self.salvar('sa.json', [evento()] * 250))
        r = momentos_sincronizados(a, a)
        self.assertEqual(r.total_pares, 250)
        self.assertEqual(len(r.exemplos), 200)

    def test_playlist_ponte_e_links(self) -> None:
        """Cruza título e artista e sugere exclusivos nos dois sentidos com buscas codificadas."""
        r = comparar(self.a, self.b, 'A', 'B', False)
        self.assertEqual(set(r.playlist['Música']), {'Faixa', '=Faixa'})
        self.assertEqual(set(r.ponte.query("De == 'A'").Artista), {'Playboi Carti', 'X'})
        self.assertEqual(set(r.ponte.query("De == 'B'").Artista), {'Katy Perry', 'Y'})
        self.assertEqual(
            link_spotify('AC/DC', 'A & B'), 'https://open.spotify.com/search/AC%2FDC%20A%20%26%20B'
        )
        self.assertTrue(r.playlist.Spotify.str.startswith('https://open.spotify.com/search/').all())

    def test_csv_preserva_utf8_e_neutraliza_formulas(self) -> None:
        """CSV exporta todos os registros, com BOM, delimitador brasileiro e proteção de fórmulas."""
        r = comparar(self.a, self.b, 'A', 'B', False)
        caminho = exportar_playlist(r, self.pasta / 'playlist.csv')
        self.assertTrue(caminho.read_bytes().startswith(b'\xef\xbb\xbf'))
        with caminho.open(encoding='utf-8-sig', newline='') as arquivo:
            linhas = list(csv.DictReader(arquivo, delimiter=';'))
        self.assertEqual(len(linhas), len(r.playlist))
        prince = next(linha for linha in linhas if 'Prince' in linha['Artista'])
        self.assertEqual(prince['Artista'], "'+Prince")
        self.assertEqual(prince['Música'], "'=Faixa")
        self.assertEqual(linhas[0]['Artista'], 'Dream, Ivory')

    def test_multiplas_partes_e_duplicacao(self) -> None:
        """União preserva categorias, contabiliza duplicações e recusa conteúdo repetido inteiro."""
        a = self.salvar('parte1.json', [evento(), evento(artista='X')])
        b = self.salvar('parte2.json', [evento(), evento(artista='Y')])
        h = carregar_historicos([a, b], configuracao=ConfiguracaoCarga(deduplicar=True))
        self.assertEqual((len(h.dados), h.contadores.recebidos, h.contadores.duplicados), (3, 4, 1))
        self.assertEqual(str(h.dados.artista.dtype), 'category')
        with self.assertRaisesRegex(ValueError, 'mesmo conteúdo'):
            carregar_historicos([a, a])
        r = comparar([a, b], self.b, 'A', 'B', False)
        self.assertEqual(r.perfil_a.plays, 4)
        self.assertEqual(r.diagnostico['Registros recebidos'].iloc[0], 4)

    def test_grupo_matriz_e_limites(self) -> None:
        """Matriz é simétrica, diagonal um e tamanho 3–6; cada par usa pesos escolhidos."""
        for n in (3, 6):
            entradas = [EntradaPerfil(f'Pessoa {i}', self.a if i % 2 else self.b) for i in range(n)]
            r = comparar_grupo(entradas, False, ponderacao='log1p')
            self.assertEqual(r.matriz.shape, (n, n))
            self.assertTrue(r.matriz.equals(r.matriz.T))
            self.assertTrue(all(r.matriz.iloc[i, i] == 1 for i in range(n)))
            self.assertAlmostEqual(
                r.matriz.iloc[0, 1],
                comparar(self.b, self.a, 'B', 'A', False, ponderacao='log1p').metricas.cosseno,
            )
        for n in (2, 7):
            with self.assertRaisesRegex(ValueError, '3 a 6'):
                comparar_grupo([EntradaPerfil(str(i), self.a) for i in range(n)])
        with self.assertRaisesRegex(ValueError, 'nomes diferentes'):
            comparar_grupo([EntradaPerfil('A', self.a)] * 3)

    def test_grupo_recorte_global(self) -> None:
        """Todos os vetores são calculados na mesma interseção, e não por janela de par."""
        datas = [f'2026-01-0{i}T00:00:00Z' for i in range(1, 6)]
        arquivos = [
            self.salvar(f'g{k}.json', [evento(d) for d in ds])
            for k, ds in enumerate((datas, datas[1:4], datas[2:]))
        ]
        r = comparar_grupo([EntradaPerfil(str(i), a) for i, a in enumerate(arquivos)])
        self.assertEqual(str(r.periodo.inicio_utc), '2026-01-03 00:00:00+00:00')
        self.assertEqual(str(r.periodo.fim_utc), '2026-01-04 00:00:00+00:00')
        self.assertEqual([p.plays for p in r.perfis], [2, 2, 2])
        fora = self.salvar('fora.json', [evento('2027-01-01T00:00:00Z')])
        with self.assertRaisesRegex(ValueError, 'período comum'):
            comparar_grupo(
                [EntradaPerfil('A', self.a), EntradaPerfil('B', self.b), EntradaPerfil('C', fora)]
            )

    def test_cartao_dimensoes_e_fallback_sem_rede(self) -> None:
        """Imagem RGB tem dimensão contratada, suporta nomes longos e fontes locais ausentes."""
        r = comparar(self.a, self.b, 'Nome com acentos áéí e ' * 30, 'Outro perfil', False)
        original = ImageFont.truetype

        def sem_fontes_do_sistema(fonte: object, *args: object, **kwargs: object):
            if isinstance(fonte, (str, Path)):
                raise OSError('Fonte local ausente')
            return original(fonte, *args, **kwargs)

        with (
            patch('cartao.ImageFont.truetype', side_effect=sem_fontes_do_sistema),
            patch('socket.socket', side_effect=AssertionError('Rede proibida')),
        ):
            self.assertIsNotNone(carregar_fonte(30, fonte='/inexistente'))
            p = gerar_cartao(r, self.pasta / 'cartao.png', fonte='/inexistente')
        with Image.open(p) as imagem:
            self.assertEqual(imagem.size, (1080, 1350))
            self.assertEqual(imagem.mode, 'RGB')
            self.assertEqual(imagem.format, 'PNG')

    def test_graficos_dados_e_escapes(self) -> None:
        """Confere sinais visuais, escalas comuns, dados e proteção de markup nos nomes."""
        r = comparar(self.a, self.b, '<b>A</b>', 'B', False)
        fig = butterfly(r)
        self.assertTrue(all(x <= 0 for x in fig.data[0].x))
        self.assertTrue(all(x >= 0 for x in fig.data[1].x))
        self.assertIn('&lt;b&gt;', fig.data[0].name)
        mapa = mapa_horarios(r)
        self.assertEqual(len(mapa.data), 2)
        for trace in mapa.data:
            self.assertEqual((len(trace.z), len(trace.z[0])), (7, 24))
            self.assertAlmostEqual(sum(sum(linha) for linha in trace.z), 100)
            self.assertEqual(trace.coloraxis, 'coloraxis')
        self.assertEqual(len(radar_tracos(r).data), 3)
        self.assertTrue(slope_chart(r).data)
        grupo = comparar_grupo([EntradaPerfil(str(i), self.a) for i in range(3)], False)
        # Cosseno envolve raízes e admite arredondamento de ponto flutuante.
        for linha in matriz_grupo(grupo).data[0].z:
            for valor in linha:
                self.assertAlmostEqual(valor, 1.0, places=14)

    def test_contraste_e_imports(self) -> None:
        """Pares de texto definidos têm contraste AA; módulos novos mantêm Python 3.10 sem NumPy."""

        def luminancia(cor: str) -> float:
            valores = [int(cor[i : i + 2], 16) / 255 for i in (1, 3, 5)]
            canais = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in valores]
            return sum(x * p for x, p in zip(canais, (0.2126, 0.7152, 0.0722)))

        for texto, fundo in (
            ('#ffffff', '#181818'),  # texto principal sobre cartões
            ('#b3b3b3', '#181818'),  # texto secundário sobre cartões
            ('#b3b3b3', '#121212'),  # texto secundário sobre o fundo
            ('#000000', '#1ed760'),  # botão primário
            ('#ffffff', '#14833b'),  # valores sobre a cor máxima da matriz do grupo
            ('#000000', '#c4b7ff'),  # iniciais no avatar do perfil B
        ):
            ls = sorted((luminancia(texto), luminancia(fundo)))
            self.assertGreaterEqual((ls[1] + 0.05) / (ls[0] + 0.05), 4.5)
        for caminho in RAIZ.glob('*.py'):
            tree = ast.parse(caminho.read_text(encoding='utf-8'), feature_version=(3, 10))
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    nomes = (
                        [alias.name for alias in node.names]
                        if isinstance(node, ast.Import)
                        else [node.module or '']
                    )
                    self.assertFalse(any(n.split('.')[0] == 'numpy' for n in nomes), str(caminho))
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == 'groupby'
                ):
                    self.assertTrue(
                        any(
                            k.arg == 'observed'
                            and isinstance(k.value, ast.Constant)
                            and k.value.value is True
                            for k in node.keywords
                        ),
                        str(caminho),
                    )


if __name__ == '__main__':
    unittest.main()
