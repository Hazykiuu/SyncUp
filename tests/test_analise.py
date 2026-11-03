"""Fluxos do orquestrador e regressão numérica contra golden masters salvos."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from conftest import FabricaEvento, HistoricosFicticios

import hashlib
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from apoio_golden import assert_tabela_golden, contagens_ranking

from analise import EntradaPerfil, ResultadoComparacao, comparar, comparar_grupo


@pytest.mark.parametrize('comum', [False, True])
def test_historicos_identicos(
    historicos: HistoricosFicticios, evento: FabricaEvento, comum: bool
) -> None:
    """Arquivos iguais dão cosseno um, sem transformar o score em identidade pessoal."""
    caminho = historicos.json([evento(artista='A'), evento(artista='B')])
    r = comparar(caminho, caminho, 'Pessoa A', 'Pessoa B', comum)
    assert isinstance(r, ResultadoComparacao) and is_dataclass(r)
    assert r.status_arquivos == 'bytes_identicos'
    assert r.metricas.cosseno == pytest.approx(1)
    assert r.metricas.jaccard == r.metricas.jaccard_ponderado == 1
    assert r.momentos_musicas.total_pares == 2
    assert len(r.playlist) == 2
    assert r.diagnostico['SHA-256 do arquivo'].nunique() == 1


def test_containers_diferentes_mesmos_eventos(
    historicos: HistoricosFicticios, evento: FabricaEvento
) -> None:
    """Campos auxiliares diferentes não alteram o histórico musical nem confundem os hashes."""
    a = historicos.json([evento(ip_addr='0.0.0.0')], 'a.json')
    b = historicos.json([evento(platform='dispositivo ficticio')], 'b.json')
    r = comparar(a, b, 'A', 'B')
    assert r.status_arquivos == 'historicos_identicos'
    assert r.diagnostico['SHA-256 do arquivo'].nunique() == 2
    assert r.metricas.cosseno == 1


def test_sem_periodo_comum_informa_como_comparar(
    historicos: HistoricosFicticios, evento: FabricaEvento
) -> None:
    """Recusa a interseção vazia; histórias completas continuam comparáveis quando solicitadas."""
    a = historicos.json([evento(data='2026-01-01T00:00:00Z')], 'a.json')
    b = historicos.json([evento(data='2026-02-01T00:00:00Z')], 'b.json')
    with pytest.raises(ValueError, match='não possuem período.*comum'):
        comparar(a, b, 'A', 'B', True)
    r = comparar(a, b, 'A', 'B', False)
    assert not r.periodo.comum
    assert r.periodo.inicio_utc is r.periodo.fim_utc is None
    assert r.metricas.cosseno == 1
    assert r.status_arquivos == 'diferentes'
    assert r.momentos_artistas.total_pares == 0


def test_recorte_identico_com_historicos_completos_diferentes(
    historicos: HistoricosFicticios, evento: FabricaEvento
) -> None:
    """Status diferencia identidade somente no período comum de identidade do arquivo completo."""
    a = historicos.json(
        [
            evento(data='2026-01-01T00:00:00Z', artista='Fora'),
            evento(data='2026-02-01T00:00:00Z', artista='Dentro'),
            evento(data='2026-03-01T00:00:00Z', artista='Fora'),
        ],
        'a.json',
    )
    b = historicos.json([evento(data='2026-02-01T00:00:00Z', artista='Dentro')], 'b.json')
    r = comparar(a, b, 'A', 'B')
    assert r.status_arquivos == 'recorte_identico'
    assert r.perfil_a.plays == r.perfil_b.plays == 1
    assert r.perfil_a.artistas.Artista.tolist() == ['Dentro']


def test_sem_musicas_validas_ou_sem_plays(
    historicos: HistoricosFicticios, evento: FabricaEvento
) -> None:
    """As duas faltas de dados têm mensagens específicas antes das divisões pelas normas."""
    musica = historicos.json([evento()], 'musica.json')
    podcast = historicos.json([evento(episode_name='episódio')], 'podcast.json')
    curto = historicos.json([evento(ms=29_999)], 'curto.json')
    with pytest.raises(ValueError, match='não contém registros de músicas válidos'):
        comparar(musica, podcast, 'A', 'B', False)
    with pytest.raises(ValueError, match='30 segundos'):
        comparar(musica, curto, 'A', 'B', False)


@pytest.mark.golden
@pytest.mark.parametrize('comum,chave', [(True, 'comum'), (False, 'completo')])
def test_regressao_contra_golden_master_salvo(
    entradas_golden: tuple[Path, Path], golden_salvo: dict[str, Any], comum: bool, chave: str
) -> None:
    """Preserva métricas e tabelas v0.4, com desempate explícito nos rankings atuais."""
    a, b = entradas_golden
    r = comparar(a, b, 'Perfil A', 'Perfil B', comum)
    anterior = golden_salvo['passo1'][chave]
    assert asdict(r.metricas) == pytest.approx(anterior['metricas'], rel=1e-12, abs=1e-12)
    for perfil, esperado in zip((r.perfil_a, r.perfil_b), anterior['perfis'], strict=True):
        assert perfil.plays == esperado['plays']
        assert perfil.quantidade_artistas == esperado['quantidade_artistas']
        assert perfil.horas == pytest.approx(esperado['horas'], abs=1e-10)
        for dimensao, valor in asdict(perfil.arquetipos).items():
            assert valor['nome'] == esperado['arquetipos'][dimensao]['nome']
            assert valor['proporcao'] == pytest.approx(
                esperado['arquetipos'][dimensao]['proporcao']
            )
    # Somente a referência v0.4 é posicional; o resultado atual tem campos nomeados.
    tabelas = {
        2: r.perfil_a.artistas,
        3: r.perfil_b.artistas,
        4: r.perfil_a.musicas,
        5: r.perfil_b.musicas,
        9: r.estatisticas,
    }
    saidas_antigas = golden_salvo['v04']['resultados'][chave]
    for indice, tabela in tabelas.items():
        contagens = None
        if indice in (2, 3, 4, 5):
            chaves = ['Artista'] if indice in (2, 3) else ['musica', 'artista']
            contagens = contagens_ranking(a if indice in (2, 4) else b, r.periodo, chaves)
        assert_tabela_golden(tabela, saidas_antigas[indice], contagens)
    assert r.contribuicoes['Contribuição ao cosseno'].sum() == pytest.approx(r.metricas.cosseno)


@pytest.mark.golden
def test_fontes_congeladas_permanecem_intactas(golden_salvo: dict[str, Any]) -> None:
    """Hashes históricos identificam a versão de referência que gerou as saídas."""
    raiz = Path(__file__).parent / 'fixtures' / 'v04'
    for nome, resumo in golden_salvo['v04']['fontes_sha256'].items():
        assert hashlib.sha256((raiz / nome).read_bytes()).hexdigest() == resumo


@pytest.mark.parametrize('quantidade', [3, 6])
def test_grupo_matriz_simetrica_e_diagonal(
    quantidade: int, historicos: HistoricosFicticios, evento: FabricaEvento
) -> None:
    """Tamanho máximo/mínimo, simetria e diagonal permanecem válidos com ponderação log1p."""
    a = historicos.json([evento(artista='A'), evento(artista='B')], 'a.json')
    b = historicos.json([evento(artista='B'), evento(artista='C')], 'b.json')
    r = comparar_grupo(
        [EntradaPerfil(f'Pessoa {i}', a if i % 2 else b) for i in range(quantidade)],
        False,
        ponderacao='log1p',
    )
    assert r.matriz.shape == (quantidade, quantidade)
    pd.testing.assert_frame_equal(r.matriz, r.matriz.T)
    assert all(r.matriz.iloc[i, i] == 1 for i in range(quantidade))
    assert r.matriz.iloc[0, 1] == pytest.approx(0.5)
