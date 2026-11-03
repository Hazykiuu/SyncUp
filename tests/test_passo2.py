"""Casos de bugs corrigidos, fusos, diagnósticos, categorias e cache Parquet."""

from __future__ import annotations

import ast
import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
import pandas as pd

import dados
from app import carregar, comparar, limpar_cache
from configuracao import ConfiguracaoCarga
from dados import carregar_historico
from formatacao import escape_html, escape_markdown, fmt_horas, fmt_num, fmt_pct, listar_markdown
from ui import grafico_artistas, perfil_card, resumo_markdown, tabela_display, texto_conexoes


def evento(
    data: str = '2026-01-01T04:00:00Z',
    ms: object = 60_000,
    musica: object = 'Faixa',
    artista: object = 'Artista',
    podcast: bool = False,
) -> dict:
    """Cria um evento mínimo ou podcast fictício."""
    return {
        'ts': data,
        'ms_played': ms,
        'master_metadata_track_name': musica,
        'master_metadata_album_artist_name': artista,
        'episode_name': 'Episódio' if podcast else None,
    }


class Passo2Test(unittest.TestCase):
    """Garante os novos contratos sem redefinir os resultados esperados anteriores."""

    def setUp(self) -> None:
        """Isola arquivos, hashes e memória entre testes."""
        self.temporaria = TemporaryDirectory()
        self.pasta = Path(self.temporaria.name)
        limpar_cache()

    def tearDown(self) -> None:
        """Libera somente os arquivos temporários deste teste."""
        limpar_cache()
        self.temporaria.cleanup()

    def salvar(self, eventos: list[dict], nome: str = 'a.json') -> Path:
        """Escreve uma entrada de histórico fictício."""
        p = self.pasta / nome
        p.write_text(json.dumps(eventos, ensure_ascii=False), encoding='utf-8')
        return p

    def test_formatacao_independente_de_locale(self) -> None:
        """Confere separadores brasileiros, percentuais, horas e valores inválidos."""
        self.assertEqual(fmt_num(1234567), '1.234.567')
        self.assertEqual(fmt_num(-1234.567, 2), '-1.234,57')
        self.assertEqual(fmt_pct(0.1234), '12,3%')
        self.assertEqual(fmt_horas(1234.5), '1.234,5 h')
        for valor in (float('inf'), float('nan')):
            with self.assertRaises(ValueError):
                fmt_num(valor)

    def test_escape_e_truncamento_sem_cortar_nomes(self) -> None:
        """Confere Markdown/HTML e consumo limitado de um iterador potencialmente grande."""
        self.assertEqual(escape_markdown('*NSYNC|_nome_'), r'\*NSYNC\|\_nome\_')
        self.assertEqual(escape_html('<b>"&'), '&lt;b&gt;&quot;&amp;')
        vistos = []

        def nomes():
            for n in range(100):
                vistos.append(n)
                yield f'Nome_{n}'

        texto = listar_markdown(nomes(), 2)
        self.assertEqual(vistos, [0, 1])
        self.assertEqual(texto, r'Nome\_0, Nome\_1')
        self.assertEqual(listar_markdown(['nome_muito_longo' * 200], 1).count('nome'), 200)

    def test_iso8601_misto_e_contadores_exclusivos(self) -> None:
        """Aceita variantes ISO, offsets, frações e registra descartes sem dupla contagem."""
        eventos = [
            evento('2026-01-01T04:00:00Z'),
            evento('2026-01-01T04:00:01.123Z'),
            evento('2026-01-01T02:00:02-02:00'),
            evento('inválido'),
            evento(ms=-1),
            evento(ms=True),
            evento(ms='inf'),
            evento(data='inválido', ms=-1, podcast=True),
            evento(musica=None),
            evento(musica='IGNORADA'),
            evento(artista='Various Artists'),
        ]
        config = ConfiguracaoCarga(musicas_ignoradas=('ignorada',), various_artists='ignorar')
        h = carregar_historico(self.salvar(eventos), configuracao=config)
        c = h.contadores
        self.assertEqual(
            (c.recebidos, c.podcasts, c.ms_invalidos, c.datas_invalidas), (11, 1, 3, 1)
        )
        self.assertEqual(
            (c.metadados_invalidos, c.ignorados, c.various_artists_descartados, c.validos),
            (1, 1, 1, 3),
        )
        self.assertEqual(
            c.recebidos,
            c.podcasts
            + c.ms_invalidos
            + c.datas_invalidas
            + c.metadados_invalidos
            + c.various_artists_descartados
            + c.ignorados
            + c.duplicados
            + c.validos,
        )
        self.assertEqual(h.dados.iloc[1].data.microsecond, 123000)

    def test_filtros_editaveis_e_various_artists(self) -> None:
        """Permite desligar a preferência antiga e normaliza caixa/espaços/pontuação."""
        arquivo = self.salvar(
            [
                evento(musica='(Falsa) Esperança'),
                evento(musica='Outra'),
                evento(artista='VARIOUS ARTISTS'),
                evento(artista='Dream, Ivory'),
            ]
        )
        self.assertEqual(len(carregar(arquivo)), 3)
        sem_filtros = ConfiguracaoCarga(musicas_ignoradas=())
        self.assertEqual(len(carregar(arquivo, configuracao=sem_filtros)), 4)
        config = replace(
            sem_filtros, artistas_ignorados=(' dream ivory ',), various_artists='ignorar'
        )
        h = carregar_historico(arquivo, configuracao=config)
        self.assertEqual(len(h.dados), 2)
        self.assertEqual(h.contadores.various_artists_encontrados, 1)
        self.assertEqual(h.contadores.ignorados, 1)

    def test_fuso_e_colunas_inteiras(self) -> None:
        """O mesmo UTC produz datas/horas/meses locais diferentes em cada fuso."""
        arquivo = self.salvar([evento('2026-01-01T02:30:00Z')])
        br = carregar(arquivo)
        tokyo = carregar(arquivo, configuracao=ConfiguracaoCarga(fuso_horario='Asia/Tokyo'))
        self.assertIsNone(br.data.dt.tz)
        self.assertEqual(str(br.data_utc.dt.tz), 'UTC')
        self.assertEqual(
            (br.iloc[0].hora, br.iloc[0].ano_mes, br.iloc[0].data_dia), (23, 202512, 20251231)
        )
        self.assertEqual(
            (tokyo.iloc[0].hora, tokyo.iloc[0].ano_mes, tokyo.iloc[0].data_dia),
            (11, 202601, 20260101),
        )
        for nome in ('hora', 'ano_mes', 'dia_semana', 'data_dia'):
            self.assertTrue(pd.api.types.is_integer_dtype(br[nome]))
        for nome in ('artista', 'musica'):
            self.assertEqual(str(br[nome].dtype), 'category')
        with self.assertRaisesRegex(ValueError, 'Fuso inválido'):
            ConfiguracaoCarga(fuso_horario='Marte/Centro')

    def test_deduplicacao_em_transicao_de_horario_de_verao(self) -> None:
        """Dois instantes com a mesma hora local na volta do relógio continuam distintos."""
        a = self.salvar([evento('2025-11-02T05:30:00Z'), evento('2025-11-02T06:30:00Z')])
        config = ConfiguracaoCarga(fuso_horario='America/New_York', deduplicar=True)
        h = carregar_historico(a, configuracao=config)
        self.assertEqual(len(h.dados), 2)
        self.assertEqual(h.dados.data.nunique(), 1)
        self.assertEqual(h.dados.data_utc.nunique(), 2)
        self.assertEqual(comparar(a, a, 'A', 'B', configuracao=config).perfil_a.plays, 2)

    def test_cobertura_diagnostico_segue_utc_na_volta_do_relogio(self) -> None:
        """O começo é o primeiro instante, mesmo quando seu horário local é maior."""
        a = self.salvar([evento('2025-11-02T05:50:00Z'), evento('2025-11-02T06:10:00Z')])
        config = ConfiguracaoCarga(fuso_horario='America/New_York')
        r = comparar(a, a, 'A', 'B', configuracao=config)
        self.assertEqual(r.diagnostico['Início do histórico'].iloc[0], '2025-11-02 01:50:00')
        self.assertEqual(r.diagnostico['Fim do histórico'].iloc[0], '2025-11-02 01:10:00')
        self.assertEqual(r.perfil_a.plays, 2)

    def test_periodo_comum_usa_instantes_e_nao_hora_local(self) -> None:
        """Evita recorte incorreto durante a hora repetida do horário de verão."""
        a = self.salvar([evento('2025-11-02T05:50:00Z'), evento('2025-11-02T06:10:00Z')])
        b = self.salvar([evento('2025-11-02T05:55:00Z'), evento('2025-11-02T06:05:00Z')], 'b.json')
        # A não tem eventos no intervalo comum apesar de horas locais parecidas.
        config = ConfiguracaoCarga(fuso_horario='America/New_York')
        with self.assertRaisesRegex(ValueError, '30 segundos'):
            comparar(a, b, 'A', 'B', configuracao=config)

    def test_sem_categorias_fantasmas_no_recorte(self) -> None:
        """observed=True elimina artistas/faixas sem registros no recorte."""
        a = self.salvar(
            [
                evento('2026-01-01T00:00:00Z', artista='Fora'),
                evento('2026-02-01T00:00:00Z', artista='Dentro'),
                evento('2026-03-01T00:00:00Z', artista='Fora'),
            ]
        )
        b = self.salvar([evento('2026-02-01T00:00:00Z', artista='Dentro')], 'b.json')
        r = comparar(a, b, 'A', 'B')
        self.assertEqual(r.perfil_a.quantidade_artistas, 1)
        self.assertEqual(r.perfil_a.artistas.Artista.tolist(), ['Dentro'])
        self.assertEqual(len(r.perfil_a.musicas), 1)
        self.assertEqual(r.metricas.jaccard, 1.0)
        self.assertEqual(r.status_arquivos, 'recorte_identico')

    def test_nomes_permanecem_raw_no_nucleo_e_escapados_na_apresentacao(self) -> None:
        """Guarda nomes reais como dados e neutraliza tags/pipes na apresentação."""
        arquivo = self.salvar([evento(artista='*NSYNC|_grupo_<b>')])
        nome = '<img src=x onerror=alert(1)>|_A_'
        r = comparar(arquivo, arquivo, nome, 'B')
        self.assertEqual(r.perfil_a.nome, nome)
        self.assertNotIn('<img', perfil_card(r.perfil_a, 'green'))
        self.assertIn(r'\|\_A\_', resumo_markdown(r))
        self.assertIn(r'\*NSYNC\|\_grupo\_', texto_conexoes(r))
        fig = grafico_artistas(r.participacao_artistas, r.ordem_artistas)
        self.assertNotIn('<b>', str(fig.data[0].y))
        self.assertEqual(fig.layout.separators, ',.')
        tabela = tabela_display(
            pd.DataFrame({'Medida': ['count', 'mean'], 'Valor': [1234.0, 2.34]})
        )
        self.assertEqual(tabela.Valor.tolist(), ['1.234', '2,34'])

    @unittest.skipUnless(
        dados.find_spec('pyarrow') is not None, 'Cache Parquet requer requirements-parquet.txt'
    )
    def test_parquet_reutiliza_e_invalida_por_opcoes(self) -> None:
        """Cache em disco reabre sem JSON e diferencia fuso, filtro e conteúdo."""
        arquivo = self.salvar([evento(), evento(musica='Outra')])
        config = ConfiguracaoCarga(
            usar_cache_disco=True, diretorio_cache=str(self.pasta / '.syncup_cache')
        )
        primeiro = carregar_historico(arquivo, configuracao=config)
        self.assertIn('gravado em Parquet', primeiro.origem_cache)
        limpar_cache()
        with patch(
            'dados._extrair_registros', side_effect=AssertionError('Não deveria reler JSON')
        ):
            segundo = carregar_historico(arquivo, configuracao=config)
        self.assertEqual(segundo.origem_cache, 'Parquet em disco')
        pd.testing.assert_frame_equal(primeiro.dados, segundo.dados)
        self.assertEqual(primeiro.contadores, segundo.contadores)
        diferente = carregar_historico(
            arquivo, configuracao=replace(config, musicas_ignoradas=('Outra',))
        )
        self.assertEqual(len(diferente.dados), 1)
        outro_fuso = carregar_historico(arquivo, configuracao=replace(config, fuso_horario='UTC'))
        self.assertEqual(outro_fuso.dados.iloc[0].hora, 4)
        self.assertEqual(len(list((self.pasta / '.syncup_cache').glob('*.parquet'))), 3)
        self.salvar([evento(ms=70_000), evento(musica='Outra')])
        mudado = carregar_historico(arquivo, configuracao=config)
        self.assertNotEqual(mudado.sha256, primeiro.sha256)
        self.assertEqual(mudado.dados.iloc[0].ms_played, 70_000)

    @unittest.skipUnless(
        dados.find_spec('pyarrow') is not None, 'Cache Parquet requer requirements-parquet.txt'
    )
    def test_parquet_corrompido_e_dependencia_ausente(self) -> None:
        """Reconstrói cache corrompido e explica como instalar dependência opcional."""
        arquivo = self.salvar([evento()])
        config = ConfiguracaoCarga(usar_cache_disco=True, diretorio_cache=str(self.pasta / 'cache'))
        carregar_historico(arquivo, configuracao=config)
        parquet = next((self.pasta / 'cache').glob('*.parquet'))
        parquet.write_bytes(b'corrompido')
        limpar_cache()
        recuperado = carregar_historico(arquivo, configuracao=config)
        self.assertIn('cache inválido reconstruído', recuperado.origem_cache)
        self.assertEqual(len(recuperado.dados), 1)
        with patch('dados.find_spec', return_value=None):
            with self.assertRaisesRegex(ValueError, 'requirements-parquet'):
                carregar_historico(arquivo, configuracao=config)

    def test_arquivos_invalidos_com_mensagens_pt_br(self) -> None:
        """JSON truncado e ZIP inválido não expõem mensagens técnicas em inglês."""
        arquivo = self.pasta / 'incompleto.json'
        arquivo.write_text('[{', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'JSON inválido'):
            carregar(arquivo)
        arquivo = self.pasta / 'incompleto.zip'
        arquivo.write_bytes(b'incompleto')
        with self.assertRaisesRegex(ValueError, 'ZIP está inválido'):
            carregar(arquivo)

    def test_diagnostico_e_cache_por_conteudo_renomeado(self) -> None:
        """Arquivo renomeado mantém dados/cache, mas mostra o nome correto no relatório."""
        arquivo = self.salvar([evento(), evento(podcast=True)])
        outro = self.pasta / 'renomeado.json'
        outro.write_bytes(arquivo.read_bytes())
        r = comparar(arquivo, outro, 'A', 'B')
        self.assertEqual(r.diagnostico.Arquivo.tolist(), ['a.json', 'renomeado.json'])
        self.assertEqual(r.diagnostico['Podcasts descartados'].tolist(), [1, 1])
        self.assertEqual(r.diagnostico['Registros recebidos'].tolist(), [2, 2])
        self.assertEqual(r.diagnostico['Origem dos dados'].iloc[1], 'Memória da sessão')

    def test_groupby_observed_e_sem_numpy(self) -> None:
        """Inspeciona todo groupby no núcleo e os imports novos."""
        for nome in ('dados.py', 'analise.py', 'perfis.py', 'formatacao.py', 'configuracao.py'):
            arvore = ast.parse((RAIZ / nome).read_text(encoding='utf-8'))
            for node in ast.walk(arvore):
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
                        )
                    )
                if isinstance(node, ast.Import):
                    self.assertFalse(any(n.name.split('.')[0] == 'numpy' for n in node.names))
                if isinstance(node, ast.ImportFrom):
                    self.assertNotEqual((node.module or '').split('.')[0], 'numpy')


if __name__ == '__main__':
    unittest.main()
