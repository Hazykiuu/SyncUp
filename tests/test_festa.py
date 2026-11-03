"""Playlist da festa, stories e cartão do Match."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from PIL import Image

from cartao import gerar_cartao_match
from conciliacao import comparar_perfis, conciliar
from festa import _valores, exportar_csv, exportar_xspf, playlist_festa
from perfil_gosto import PerfilGosto
from stories import stories_match_html


def _perfil(nome: str, faixas: list[tuple[str, str]], generos=None) -> PerfilGosto:
    artistas = list(dict.fromkeys(a for _, a in faixas))
    tops = {p: artistas for p in ('short_term', 'medium_term', 'long_term')}
    musicas = [{'musica': m, 'artista': a} for m, a in faixas]
    return PerfilGosto(nome, 'teste', '', tops, {p: musicas for p in tops}, generos=generos or {})


GRUPO = [
    _perfil('Ana', [('Hit', 'Pop'), ('Só da Ana', 'Indie'), ('Outra', 'Indie')]),
    _perfil('Bia', [('Hit', 'Pop'), ('Pesado', 'Metal')]),
    _perfil('Caio', [('Samba 1', 'Samba'), ('Samba 2', 'Samba')]),
]


def test_playlist_cobre_todo_mundo_e_e_deterministica() -> None:
    faixas = playlist_festa(GRUPO, n=3)
    assert faixas[0].musica == 'Hit' and set(faixas[0].para) == {'Ana', 'Bia'}
    cobertos = {p for f in faixas for p in f.para}
    assert cobertos == {'Ana', 'Bia', 'Caio'}  # Caio não divide nada e mesmo assim entra
    assert playlist_festa(GRUPO, n=3) == faixas
    assert len(playlist_festa(GRUPO, n=100)) == 6  # nunca repete faixa
    with pytest.raises(ValueError):
        playlist_festa(GRUPO[:1])


def test_artista_em_comum_vale_meio_ponto() -> None:
    a = _perfil('Ana', [('Faixa A', 'Banda')])
    b = _perfil('Bia', [('Faixa B', 'Banda')])
    primeira = playlist_festa([a, b], n=1)[0]
    assert set(primeira.para) == {'Ana', 'Bia'}  # a outra pessoa conhece o artista
    # 1º lugar nos três períodos: a faixa vale 2,4 para quem a tem e 1,2 (metade) para a outra.
    valores = _valores([a, b])[('faixaa', 'banda')][2]
    assert valores == {'Ana': pytest.approx(2.4), 'Bia': pytest.approx(1.2)}


def test_exportacoes_abertas_sao_validas_e_escapadas(tmp_path: Path) -> None:
    perigoso = [_perfil('<b>Ana</b>', [('=SOMA(1)', 'A & B <x>')]), _perfil('Bia', [('Z', 'Y')])]
    faixas = playlist_festa(perigoso)
    csv = exportar_csv(faixas, tmp_path / 'festa.csv').read_text(encoding='utf-8-sig')
    assert "'=SOMA(1)" in csv
    xspf = exportar_xspf(faixas, tmp_path / 'festa.xspf', 'Festa <teste>')
    raiz = ET.parse(xspf).getroot()
    ns = {'x': 'http://xspf.org/ns/0/'}
    assert raiz.find('x:title', ns).text == 'Festa <teste>'
    criadores = [t.text for t in raiz.findall('x:trackList/x:track/x:creator', ns)]
    assert 'A & B <x>' in criadores
    assert '<x>' not in xspf.read_text(encoding='utf-8')  # escapado no arquivo


def test_stories_do_match_escapam_nomes() -> None:
    perfis = [_perfil('<script>x</script>', [('Hit', 'Pop')]), *GRUPO[1:]]
    html = stories_match_html(conciliar(perfis))
    assert '<script>' not in html and '&lt;script&gt;' in html
    assert html.count('su-story ') == 1 + 1 + 1  # abertura, um trio, resumo


def test_cartao_do_match_com_e_sem_generos(tmp_path: Path) -> None:
    com = comparar_perfis(
        _perfil('Ana', [('Hit', 'Pop')], {'Pop': ['pop']}),
        _perfil('Bia', [('Hit', 'Pop')], {'Pop': ['pop']}),
    )
    sem = comparar_perfis(*GRUPO[:2])
    for i, c in enumerate((com, sem)):
        with Image.open(gerar_cartao_match(c, tmp_path / f'{i}.png')) as imagem:
            assert imagem.size == (1080, 1350)


def test_fonte_invalida_cai_na_figtree() -> None:
    from cartao import carregar_fonte

    assert carregar_fonte(30, True, '/inexistente').getname() == ('Figtree', 'Bold')
