"""Ingestão tolerante aos campos opcionais e rigorosa com conteúdo inválido."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from conftest import FabricaEvento, HistoricosFicticios

import zipfile
from dataclasses import asdict
from pathlib import Path

import pytest

from configuracao import ConfiguracaoCarga
from dados import carregar, carregar_historico, carregar_historicos


@pytest.mark.parametrize('conteudo', ['[', '[{"ts":', '{invalido}', ''])
def test_json_malformado(tmp_path: Path, conteudo: str) -> None:
    """A mensagem de JSON truncado é legível e em pt-BR."""
    caminho = tmp_path / 'quebrado.json'
    caminho.write_text(conteudo, encoding='utf-8')
    with pytest.raises(ValueError, match='JSON inválido'):
        carregar(caminho)


@pytest.mark.parametrize('conteudo', [b'', b'isso nao e um zip', b'PK\x03\x04incompleto'])
def test_zip_corrompido(tmp_path: Path, conteudo: bytes) -> None:
    """ZIP vazio em bytes e ZIP truncado não chegam à análise."""
    caminho = tmp_path / 'quebrado.zip'
    caminho.write_bytes(conteudo)
    with pytest.raises(ValueError, match='ZIP está inválido ou incompleto'):
        carregar(caminho)


def test_json_malformado_dentro_do_zip(tmp_path: Path) -> None:
    """Uma parte corrompida do arquivo compactado não é ignorada silenciosamente."""
    caminho = tmp_path / 'malformado.zip'
    with zipfile.ZipFile(caminho, 'w') as pacote:
        pacote.writestr('Streaming_History_Audio.json', '[{"ts":')
    with pytest.raises(ValueError, match='JSON inválido'):
        carregar(caminho)


@pytest.mark.parametrize(
    'campo', ['ts', 'ms_played', 'master_metadata_track_name', 'master_metadata_album_artist_name']
)
def test_ausencia_de_campo_obrigatorio(
    historicos: HistoricosFicticios, evento: FabricaEvento, campo: str
) -> None:
    """Colunas obrigatórias ausentes em todo o histórico geram erro explícito."""
    registro = evento()
    del registro[campo]
    caminho = historicos.json([registro])
    with pytest.raises(ValueError, match='histórico estendido'):
        carregar(caminho)


@pytest.mark.parametrize('tipo', ['json', 'zip'])
def test_campos_opcionais_nao_sao_exigidos(
    historicos: HistoricosFicticios, evento: FabricaEvento, tipo: str
) -> None:
    """IP, plataforma, shuffle, skipped e campos de podcasts não são necessários para música."""
    registro = evento(artista='Dream, Ivory')
    caminho = (
        historicos.json([registro])
        if tipo == 'json'
        else historicos.zip({'Streaming_History_Audio.json': [registro]})
    )
    h = carregar_historico(caminho)
    assert h.contadores.recebidos == h.contadores.validos == 1
    assert h.dados.iloc[0].artista == 'Dream, Ivory'
    assert h.dados.iloc[0].minutos == 1
    assert str(h.dados.artista.dtype) == str(h.dados.musica.dtype) == 'category'


@pytest.mark.parametrize('campo', ['episode_name', 'episode_show_name', 'spotify_episode_uri'])
def test_podcasts_descartados_com_contador(
    historicos: HistoricosFicticios, evento: FabricaEvento, campo: str
) -> None:
    """Qualquer identificador explícito de episódio indica podcast, mesmo com data/duração inválidas."""
    caminho = historicos.json([evento(), evento(data='invalida', ms=-1, **{campo: 'episodio'})])
    h = carregar_historico(caminho)
    assert len(h.dados) == 1
    assert h.contadores.podcasts == 1
    assert h.contadores.datas_invalidas == h.contadores.ms_invalidos == 0
    assert h.contadores.recebidos == 2


@pytest.mark.parametrize('deduplicar,validos,duplicados', [(False, 4, 0), (True, 3, 1)])
def test_deduplicacao_entre_multiplos_arquivos(
    historicos: HistoricosFicticios,
    evento: FabricaEvento,
    deduplicar: bool,
    validos: int,
    duplicados: int,
) -> None:
    """Remove somente o evento inteiro repetido entre partes, quando solicitado."""
    repetido = evento()
    a = historicos.json([repetido, evento(data='2026-01-01T04:10:00Z')], 'a.json')
    b = historicos.json([repetido, evento(artista='Outro')], 'b.json')
    h = carregar_historicos([a, b], configuracao=ConfiguracaoCarga(deduplicar=deduplicar))
    assert len(h.dados) == h.contadores.validos == validos
    assert h.contadores.duplicados == duplicados
    assert h.contadores.recebidos == 4
    assert h.contadores.recebidos == h.contadores.validos + h.contadores.duplicados
    assert h.duplicados_removidos == duplicados
    assert str(h.dados.artista.dtype) == 'category'


def test_deduplicacao_dentro_de_partes_zip(
    historicos: HistoricosFicticios, evento: FabricaEvento
) -> None:
    """Partes dentro do mesmo ZIP usam a mesma chave de deduplicação UTC."""
    caminho = historicos.zip(
        {'parte1.json': [evento()], 'parte2.json': [evento(), evento(data='2026-01-01T04:01:00Z')]}
    )
    h = carregar_historico(caminho, deduplicar=True)
    assert (len(h.dados), h.contadores.duplicados) == (2, 1)


def test_mesmo_conteudo_repetido_no_mesmo_perfil(
    historicos: HistoricosFicticios, evento: FabricaEvento, tmp_path: Path
) -> None:
    """Um arquivo renomeado com os mesmos bytes é reconhecido pelo hash."""
    a = historicos.json([evento()])
    b = tmp_path / 'outro_nome.json'
    b.write_bytes(a.read_bytes())
    with pytest.raises(ValueError, match='mesmo conteúdo'):
        carregar_historicos([a, b])


def test_descartes_somam_total_recebido(
    historicos: HistoricosFicticios, evento: FabricaEvento
) -> None:
    """Duração, data, identificação e podcast não produzem dupla contagem."""
    caminho = historicos.json(
        [
            evento(),
            evento(ms=True),
            evento(data='inválida'),
            evento(musica=''),
            evento(ms=-1, episode_name='Podcast'),
        ]
    )
    c = asdict(carregar_historico(caminho).contadores)
    motivos = [
        'podcasts',
        'ms_invalidos',
        'datas_invalidas',
        'metadados_invalidos',
        'various_artists_descartados',
        'ignorados',
        'duplicados',
    ]
    assert c['recebidos'] == c['validos'] + sum(c[x] for x in motivos) == 5


def test_datas_fuso_e_instantes_distintos(
    historicos: HistoricosFicticios, evento: FabricaEvento
) -> None:
    """A hora local repetida por DST não transforma dois eventos UTC em um duplicado."""
    caminho = historicos.json(
        [evento(data='2025-11-02T05:30:00Z'), evento(data='2025-11-02T06:30:00Z')]
    )
    h = carregar_historico(
        caminho, configuracao=ConfiguracaoCarga(fuso_horario='America/New_York', deduplicar=True)
    )
    assert h.dados.data.nunique() == 1
    assert h.dados.data_utc.nunique() == 2
    assert h.contadores.duplicados == 0
    assert h.dados.hora.tolist() == [1, 1]
    assert h.dados.data.dt.tz is None
    assert h.dados.ano_mes.tolist() == [202511, 202511]


def test_cache_nao_expoe_dataframe_mutavel(
    historicos: HistoricosFicticios, evento: FabricaEvento
) -> None:
    """Alterar dados devolvidos por carregar não muda a versão no cache."""
    caminho = historicos.json([evento()])
    dados = carregar(caminho)
    dados.loc[0, 'ms_played'] = 999
    assert carregar(caminho).loc[0, 'ms_played'] == 60_000


def test_leituras_simultaneas_nao_dependem_da_trava(
    historicos: HistoricosFicticios, evento: FabricaEvento, monkeypatch
) -> None:
    """Dois arquivos são lidos ao mesmo tempo; o cache continua limitado e coerente."""
    import threading

    import dados

    caminhos = [
        historicos.json([evento(artista=f'Artista {i}')] * (i + 1), f'h{i}.json') for i in range(2)
    ]
    esperados = [carregar_historico(c).dados for c in caminhos]
    dados.limpar_cache()
    barreira = threading.Barrier(2, timeout=10)
    extrair = dados._extrair_registros

    def extrair_junto(caminho):
        barreira.wait()  # só passa se as duas leituras estiverem em andamento juntas
        return extrair(caminho)

    monkeypatch.setattr(dados, '_extrair_registros', extrair_junto)
    resultados: dict[int, object] = {}
    threads = [
        threading.Thread(target=lambda i=i, c=c: resultados.__setitem__(i, carregar_historico(c)))
        for i, c in enumerate(caminhos)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(15)
    assert sorted(resultados) == [0, 1]
    for i, esperado in enumerate(esperados):
        assert resultados[i].dados.equals(esperado)
    assert len(dados._memoria) <= dados.MAXIMO_HISTORICOS_CACHE
