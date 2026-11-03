"""Correções e recursos da v0.6: ingestão robusta, componentes animados e otimizações."""

from __future__ import annotations

import html
import json
import re
import zipfile
from pathlib import Path

import pandas as pd
import pytest

import componentes
from analise import EntradaPerfil, comparar, comparar_grupo
from dados import carregar_historico, limpar_dados
from recursos import momentos_sincronizados
from ui import executar_dupla, tabela_display


def _evento(artista: str, musica: str = 'Faixa', ts: str = '2026-01-01T04:00:00Z') -> dict:
    return {
        'ts': ts,
        'ms_played': 60_000,
        'master_metadata_track_name': musica,
        'master_metadata_album_artist_name': artista,
    }


def _zip(destino: Path, extras: dict[str, bytes] | None = None) -> Path:
    eventos = [_evento('<b>Ana</b>'), _evento('Bia', ts='2026-02-01T04:00:00Z')]
    with zipfile.ZipFile(destino, 'w') as pacote:
        pacote.writestr(
            'Spotify Extended Streaming History/Streaming_History_Audio_1.json', json.dumps(eventos)
        )
        for nome, conteudo in (extras or {}).items():
            pacote.writestr(nome, conteudo)
    return destino


def test_zip_com_metadados_do_macos_e_pastas(tmp_path: Path) -> None:
    """Arquivos ``__MACOSX`` e ``._*`` (binários) não derrubam mais a leitura do ZIP."""
    caminho = _zip(
        tmp_path / 'macos.zip',
        {
            '__MACOSX/Spotify Extended Streaming History/._Streaming_History_Audio_1.json': b'\x00\x05\x16\x07\xff',
            'Spotify Extended Streaming History/._outro.json': b'\xff\xfe',
            'Spotify Extended Streaming History/': b'',
        },
    )
    historico = carregar_historico(caminho)
    assert historico.contadores.validos == 2


def test_json_com_bom_e_nan_continua_aceito(tmp_path: Path) -> None:
    """O leitor rápido recai no json padrão para NaN; BOM UTF-8 continua aceito."""
    texto = (
        json.dumps([_evento('Ana')])[:-1] + ', {"ts": "2026-01-01T05:00:00Z", "ms_played": NaN, '
    )
    texto += '"master_metadata_track_name": "F", "master_metadata_album_artist_name": "B"}]'
    caminho = tmp_path / 'bom.json'
    caminho.write_bytes(b'\xef\xbb\xbf' + texto.encode('utf-8'))
    historico = carregar_historico(caminho)
    assert historico.contadores.recebidos == 2
    assert historico.contadores.ms_invalidos == 1


def test_nomes_com_espacos_nas_bordas_sao_unificados() -> None:
    """Dois nomes que só diferem por espaços viram uma categoria única e ordenada."""
    dados = limpar_dados(
        [
            ('2026-01-01T04:00:00Z', 60_000, 'Faixa', ' Zeca'),
            ('2026-01-01T05:00:00Z', 60_000, 'Faixa', 'Zeca '),
            ('2026-01-01T06:00:00Z', 60_000, 'Faixa', 'Ana'),
        ],
    )
    assert dados.artista.cat.categories.tolist() == ['Ana', 'Zeca']
    assert dados.artista.value_counts()['Zeca'] == 2


def test_nomes_none_nao_quebram(tmp_path: Path) -> None:
    """Nomes ausentes (API/Gradio) caem no padrão em vez de gerar AttributeError."""
    a, b = _zip(tmp_path / 'a.zip'), _zip(tmp_path / 'b.zip')
    r = comparar(a, b, None, None, False)  # type: ignore[arg-type]
    assert (r.perfil_a.nome, r.perfil_b.nome) == ('Pessoa A', 'Pessoa B')
    g = comparar_grupo(
        [EntradaPerfil(None, a), EntradaPerfil('X', b), EntradaPerfil('Y', a)], False
    )  # type: ignore[arg-type]
    assert g.matriz.index[0] == 'Pessoa 1'
    assert len(g.diagnostico) == 3


def test_momentos_casam_com_algoritmo_por_grupo() -> None:
    """A fusão única produz os mesmos pares que o emparelhamento ingênuo por chave."""
    base = pd.Timestamp('2026-01-01', tz='UTC')

    def quadro(eventos):
        dados = pd.DataFrame(eventos, columns=['artista', 'musica', 'min'])
        dados['data_utc'] = base + pd.to_timedelta(dados['min'], unit='min')
        dados['data'] = dados['data_utc'].dt.tz_localize(None)
        for c in ('artista', 'musica'):
            dados[c] = dados[c].astype('category')
        return dados

    a = quadro([('X', 'm1', 0), ('X', 'm2', 30), ('Y', 'm1', 10), ('X', 'm1', 200), ('Z', 'm', 5)])
    b = quadro([('X', 'm1', 50), ('Y', 'm9', 70), ('X', 'm1', 61), ('W', 'm', 5), ('X', 'm2', 31)])
    artistas = momentos_sincronizados(a, b, 'artista')
    musicas = momentos_sincronizados(a, b, 'musica')
    assert artistas.total_pares == 3
    assert musicas.total_pares == 2
    assert artistas.exemplos['Artista'].tolist() == ['X', 'X', 'Y']


def test_componentes_escapam_nomes_e_corrida_tem_json_valido(tmp_path: Path) -> None:
    """HTML animado não interpreta markup dos nomes; a corrida carrega JSON válido."""
    a, b = _zip(tmp_path / 'a.zip'), _zip(tmp_path / 'b.zip')
    r = comparar(a, b, '<script>x</script>', 'B', False)
    blend = componentes.blend_html(r, 'período')
    assert '<script>' not in blend and '&lt;script&gt;' in blend
    assert 'Ruzicka' in blend and 'data-countup' in blend
    corrida = componentes.corrida_html(r)
    atributo = re.search(r'data-race="([^"]*)"', corrida).group(1)
    dados = json.loads(html.unescape(atributo))
    assert dados['meses'] == ['2026-01', '2026-02']
    assert dados['perfis'][0]['nome'] == '<script>x</script>'
    assert all(len(serie) == 2 for serie in dados['perfis'][0]['valores'])
    lista = componentes.lista_top(r.perfil_a.artistas, '#1ed760', 'Top')
    assert '&lt;b&gt;Ana&lt;/b&gt;' in lista and 'open.spotify.com/search/' in lista
    grupo = componentes.grupo_html(
        comparar_grupo([EntradaPerfil(str(i), a) for i in range(3)], False)
    )
    assert 'Dupla mais sintonizada' in grupo


def test_tabela_display_preserva_semantica() -> None:
    """Contagens sem casas, floats com duas, NaN como travessão e textos intactos."""
    tabela = pd.DataFrame(
        {'Medida': ['count', 'mean'], 'A': [3.0, 2.5], 'B': [float('nan'), 1234.5], 'C': ['x', 'y']}
    )
    exibicao = tabela_display(tabela)
    assert exibicao.values.tolist() == [['count', '3', '—', 'x'], ['mean', '2,50', '1.234,50', 'y']]
    assert tabela['A'].dtype == float


def test_executar_dupla_sem_arquivos_mostra_erro_amigavel() -> None:
    """Clique sem uploads (None) gera gr.Error em português, não TypeError."""
    import gradio as gr

    with pytest.raises(gr.Error):
        executar_dupla(
            None,
            None,
            'A',
            'B',
            True,
            'bruta',
            'America/Sao_Paulo',
            '',
            '',
            'manter',
            False,
            False,
            progress=lambda *a, **k: None,
        )


def test_leitura_paralela_equivale_a_sequencial(tmp_path: Path, monkeypatch) -> None:
    """Processos auxiliares produzem exatamente os mesmos históricos da leitura sequencial."""
    import dados

    a, b = _zip(tmp_path / 'a.zip'), tmp_path / 'b.json'
    b.write_text(json.dumps([_evento('Bia'), _evento('Caio', ts='2026-03-01T04:00:00Z')]))
    sequencial = comparar(a, b, 'A', 'B', False)
    dados.limpar_cache()
    monkeypatch.setenv('SYNCUP_PARALELO_MIN_BYTES', '0')
    monkeypatch.setenv('SYNCUP_PROCESSOS', '2')
    dados.habilitar_leitura_paralela(True)
    try:
        assert dados.precarregar([a, b]) == 2
        assert dados.precarregar([a, b]) == 0  # já em memória
        paralelo = comparar(a, b, 'A', 'B', False)
    finally:
        dados.habilitar_leitura_paralela(False)
    assert paralelo.metricas == sequencial.metricas
    pd.testing.assert_frame_equal(paralelo.perfil_a.artistas, sequencial.perfil_a.artistas)
