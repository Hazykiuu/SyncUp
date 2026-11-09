"""Wrapped da vida toda, arquétipos v0.7 e campos de hábitos na ingestão."""

from __future__ import annotations

import html
import json
from pathlib import Path

import pytest
from PIL import Image

from arquetipos import REGRAS, classificar
from cartao import gerar_cartao_wrapped
from dados import carregar_historico, familia_plataforma, limpar_dados
from stories import arquetipos_detalhe_html, stories_html
from wrapped import calcular_wrapped, wrapped_de_arquivos


def _evento(ts: str, artista: str, musica: str = 'Faixa', ms: int = 60_000, **extras) -> dict:
    return {
        'ts': ts,
        'ms_played': ms,
        'master_metadata_track_name': musica,
        'master_metadata_album_artist_name': artista,
        **extras,
    }


@pytest.fixture
def historico(tmp_path: Path) -> Path:
    """Três dias seguidos + um isolado, dois anos, hábitos preenchidos."""
    eventos = [
        _evento(
            '2023-12-30T03:00:00Z',
            'Zé',
            'Primeira',
            skipped=False,
            shuffle=True,
            platform='Android OS 13 API 33 (Motorola, moto g)',
            reason_end='trackdone',
            offline=False,
        ),
        _evento(
            '2023-12-31T22:00:00Z',
            'Ana',
            'Hit',
            skipped=True,
            shuffle=True,
            platform='windows 10 (10.0.19045; x64)',
            reason_end='fwdbtn',
            offline=False,
        ),
        _evento(
            '2024-01-01T22:00:00Z',
            'Ana',
            'Hit',
            skipped=False,
            shuffle=True,
            platform='Windows 10',
            reason_end='trackdone',
            offline=True,
        ),
        _evento(
            '2024-01-01T23:00:00Z',
            'Ana',
            'Hit',
            skipped=False,
            shuffle=False,
            platform='iOS 17.1 (iPhone15,2)',
            reason_end='trackdone',
            offline=False,
        ),
        _evento(
            '2024-03-10T15:00:00Z',
            '<b>Bia</b>',
            'Outra',
            skipped=False,
            shuffle=False,
            platform='web_player windows 10',
            reason_end='trackdone',
            offline=False,
        ),
        _evento(
            '2024-03-10T15:05:00Z',
            'Ana',
            'Curta',
            ms=10_000,
            skipped=True,
            shuffle=False,
            platform='not_applicable',
            reason_end='fwdbtn',
            offline=False,
        ),
    ]
    caminho = tmp_path / 'vida.json'
    caminho.write_text(json.dumps(eventos), encoding='utf-8')
    return caminho


def test_habitos_preservados_sem_dados_do_aparelho(historico: Path) -> None:
    """Pulos/aleatório/offline viram booleanos; plataforma guarda só a família."""
    dados = carregar_historico(historico).dados
    assert str(dados['pulada'].dtype) == 'boolean'
    assert set(dados['plataforma'].dropna().astype(str)) == {
        'Android',
        'Windows',
        'iOS',
        'Navegador',
    }
    texto = ' '.join(dados['plataforma'].dropna().astype(str))
    assert 'Motorola' not in texto and 'iPhone' not in texto and '19045' not in texto
    assert dados['plataforma'].isna().sum() == 1  # not_applicable
    assert familia_plataforma('PlayStation 5') == 'TV, console ou caixa de som'
    assert familia_plataforma(None) is None


def test_exportacao_antiga_sem_habitos_continua_funcionando() -> None:
    """Tuplas de 4 campos (API antiga) produzem hábitos nulos, sem erro."""
    dados = limpar_dados([('2026-01-01T04:00:00Z', 60_000, 'F', 'A')])
    assert dados['pulada'].isna().all() and dados['plataforma'].isna().all()
    w = calcular_wrapped(dados, 'X')
    assert w.habitos['pulos'] is None and w.habitos['aleatorio'] is None
    assert any('pulos/aleatório' in aviso for aviso in w.avisos)


def test_estatisticas_da_vida_toda(historico: Path) -> None:
    """Rankings, sequência, recorde, primeira música, anos e hábitos conferidos à mão."""
    w = wrapped_de_arquivos(historico, 'Carlos')
    assert w.nome == 'Carlos'
    assert w.plays == 5  # o play de 10 s não entra em rankings
    assert w.artista_vida.nome == 'Ana' and w.artista_vida.plays == 3
    assert w.top_musicas[0].nome == 'Hit' and w.top_musicas[0].artista == 'Ana'
    assert w.primeira_musica.nome == 'Primeira'  # 30/12/2023 00h em São Paulo
    assert [a.ano for a in w.anos] == [2023, 2024]
    assert w.anos[0].novos_artistas == 2 and w.anos[1].novos_artistas == 1
    assert w.sequencia == 3  # 30/12, 31/12 e 01/01 no fuso local
    assert w.repeticao_dia.nome == 'Hit' and w.repeticao_dia.plays == 2
    assert w.habitos['pulos'] == pytest.approx(2 / 6)
    assert w.habitos['offline'] == pytest.approx(1 / 6)
    assert w.habitos['fim_natural'] == pytest.approx(4 / 6)
    assert sum(w.plays_por_hora) == 5
    assert w.fiel.nome == 'Ana' and w.anos_fiel == 2
    assert len(w.fiel_anos) == w.anos_fiel and w.fiel_anos == sorted(w.fiel_anos)


def test_arquetipos_principal_secundarios_e_equilibrado() -> None:
    """Intensidade escolhe o principal; sem regra atingida, cai em equilibrado."""
    medidas = {r.medida: 0.0 for r in REGRAS}
    medidas.update(top1=0.18, madrugada=0.16, sequencia=200.0, aleatorio=0.3)
    perfil = classificar(medidas)
    assert perfil.principal.chave == 'devoto'  # 0,8 de intensidade contra 0,05 e 0,02
    assert [s.chave for s in perfil.secundarios] == ['coruja', 'maratonista']
    assert 'Um único artista ocupa 18,0%' in perfil.principal.explicacao
    vazio = classificar({r.medida: 0.0 for r in REGRAS})
    assert vazio.principal.chave == 'equilibrado' and vazio.secundarios == []
    sem_campos = classificar({'top1': 0.01})
    assert len(sem_campos.avaliados) == 1  # medidas ausentes não são avaliadas
    album = classificar({'fim_natural': 0.9, 'aleatorio': 0.7})
    assert album.principal.chave != 'album'  # até o fim no aleatório não é ouvir álbum


def test_stories_escapam_nomes_e_png(historico: Path, tmp_path: Path) -> None:
    """Slides não interpretam markup; PNG do resumo tem formato de story."""
    w = wrapped_de_arquivos(historico, '<script>x</script>')
    pagina = stories_html(w)
    assert '<script>' not in pagina and '&lt;script&gt;' in pagina
    assert '&lt;b&gt;Bia&lt;/b&gt;' in pagina
    assert pagina.count('class="su-story ') >= 10
    assert 'data-stories' in pagina
    detalhe = arquetipos_detalhe_html(w)
    assert html.unescape(detalhe).count('<small>limiar ') == len(w.arquetipos.avaliados)
    png = gerar_cartao_wrapped(w, tmp_path / 'story.png')
    with Image.open(png) as imagem:
        assert imagem.size == (1080, 1920) and imagem.mode == 'RGB'
