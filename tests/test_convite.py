"""Convite por código: ida e volta, só rankings, e código de fora sempre conferido."""

from __future__ import annotations

import base64
import json
import zlib

import pytest

from convite import PREFIXO, gerar_convite, ler_convite, separar_convites
from perfil_gosto import PERIODOS, PerfilGosto


def _perfil(nome: str = 'Bia') -> PerfilGosto:
    return PerfilGosto(
        nome,
        'historico_zip',
        '2026-11-01',
        {p: [f'Artista {i}' for i in range(50)] for p in PERIODOS},
        {
            p: [{'musica': f'Música {i}', 'artista': f'Artista {i}'} for i in range(50)]
            for p in PERIODOS
        },
        recentes=[{'musica': 'X', 'artista': 'Y', 'tocada_em': '2026-11-01T03:00:00+00:00'}],
        seguidos=['Segredo'],
        generos={'Artista 0': ['rock']},
    )


def _codigo(dados: object) -> str:
    bruto = zlib.compress(json.dumps(dados).encode('utf-8'))
    return PREFIXO + base64.urlsafe_b64encode(bruto).decode('ascii').rstrip('=')


def test_ida_e_volta_so_com_rankings() -> None:
    codigo = gerar_convite(_perfil())
    assert codigo.startswith(PREFIXO) and len(codigo) < 5000
    perfil = ler_convite(codigo)
    assert perfil.nome == 'Bia' and perfil.fonte == 'convite' and perfil.rotulo_fonte == 'Convite'
    assert perfil.top_artistas == _perfil().top_artistas
    assert perfil.top_musicas == _perfil().top_musicas
    assert perfil.recentes == [] and perfil.seguidos == [] and perfil.generos == {}
    assert 'Segredo' not in zlib.decompress(base64.urlsafe_b64decode(codigo[8:] + '==')).decode()


def test_codigo_quebrado_pelo_aplicativo_de_mensagem() -> None:
    a, b = gerar_convite(_perfil('Ana')), gerar_convite(_perfil('Bia'))
    colado = f'{a[:40]}\n{a[40:90]} {a[90:]}\n\n{b}'
    codigos = separar_convites(colado)
    assert codigos == [a, b]
    assert [ler_convite(c).nome for c in codigos] == ['Ana', 'Bia']


@pytest.mark.parametrize(
    ('codigo', 'mensagem'),
    [
        ('oi, tudo bem?', 'não parece um convite'),
        (PREFIXO + 'A' * 30_000, 'grande demais'),
        (PREFIXO + '!!!não é base64', 'incompleto'),
        (gerar_convite(_perfil())[:-30], 'incompleto'),
        (_codigo(['lista']), 'incompleto'),
        (_codigo({'n': 'X' * 61, 'a': {}, 'm': {}}), 'incompleto'),
        (_codigo({'n': 'Bia', 'a': {'long_term': [1, 2]}, 'm': {}}), 'incompleto'),
        (_codigo({'n': 'Bia', 'a': {'long_term': ['A'] * 51}, 'm': {}}), 'incompleto'),
        (_codigo({'n': 'Bia', 'a': {}, 'm': {}}), 'nenhum ranking'),
    ],
)
def test_codigo_invalido_vira_mensagem_clara(codigo: str, mensagem: str) -> None:
    with pytest.raises(ValueError, match=mensagem):
        ler_convite(codigo)


def test_zip_bomb_no_codigo_e_recusado() -> None:
    bomba = zlib.compress(b'{"n":"' + b'a' * 5_000_000 + b'"}', 9)
    codigo = PREFIXO + base64.urlsafe_b64encode(bomba).decode('ascii').rstrip('=')
    assert len(codigo) < 20_000  # cabe no limite de texto, mas descompacta para 5 MB
    with pytest.raises(ValueError, match='incompleto'):
        ler_convite(codigo)


def _historico(tmp_path, nome: str, artistas: list[str]) -> str:
    eventos = [
        {
            'ts': f'2026-10-0{i + 1}T10:00:00Z',
            'ms_played': 200_000,
            'master_metadata_track_name': f'Faixa {a}',
            'master_metadata_album_artist_name': a,
        }
        for i, a in enumerate(artistas)
    ]
    caminho = tmp_path / f'{nome}.json'
    caminho.write_text(json.dumps(eventos), encoding='utf-8')
    return str(caminho)


OPCOES = ['America/Sao_Paulo', '', '', 'manter', False, False]


def test_convite_do_zip_entra_no_match_e_o_invalido_sai_com_aviso(tmp_path, monkeypatch) -> None:
    import ui

    codigo = ui.match.gerar_meu_convite(
        [_historico(tmp_path, 'bia', ['X', 'Y'])], 'Bia', None, *OPCOES
    )
    assert codigo.startswith(PREFIXO)
    avisos: list[str] = []
    monkeypatch.setattr(ui.gr, 'Warning', lambda m, **_: avisos.append(m))
    html, *_, estado, _ = ui.executar_match(
        [_historico(tmp_path, 'ana', ['X', 'Z'])],
        'Ana',
        [],
        *OPCOES,
        False,
        '',
        f'{codigo}\nSYNCUP1.cortado',
        progress=lambda *a, **k: None,
    )
    assert [p.nome for p in estado['perfis']] == ['Ana', 'Bia']
    assert 'Bia: Convite' in html
    assert len(avisos) == 1 and 'Convite 2' in avisos[0]
    assert ('Ana', 'Bia') not in estado['sintonias']  # convite não traz escuta


def test_gerar_convite_de_perfil_salvo_so_pela_lista(tmp_path, monkeypatch) -> None:
    from gradio.exceptions import Error

    import ui
    from perfil_gosto import salvar_perfil

    salvar_perfil(_perfil('Carlos'), tmp_path)
    monkeypatch.setattr(ui.match, 'PASTA_PERFIS', tmp_path)
    assert ler_convite(ui.match.gerar_meu_convite(None, '', 'Carlos', *OPCOES)).nome == 'Carlos'
    for errado, mensagem in (('../app', 'não está mais salvo'), (None, 'Envie o seu ZIP')):
        with pytest.raises(Error, match=mensagem):
            ui.match.gerar_meu_convite(None, '', errado, *OPCOES)
    with pytest.raises(Error, match='seu nome'):
        ui.match.gerar_meu_convite([_historico(tmp_path, 'x', ['X'])], ' ', None, *OPCOES)
