"""Playlist da festa: poucas músicas que cobrem o gosto de todo o grupo.

Cada música tem um valor para cada pessoa: o peso dela no top da pessoa
(posição × período, como em ``perfil_gosto.vetor_artistas``) ou, se só o artista
estiver nos rankings da pessoa, metade disso. A escolha é gulosa e maximiza
Σ √cobertura: a raiz faz cada nova música valer mais para quem ainda tem pouco,
então ninguém fica de fora enquanto houver música para essa pessoa.

Sai em CSV e em XSPF (formato aberto de playlist da Xiph, aceito por VLC e
outros players livres). Nada é criado na conta do Spotify.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from math import sqrt
from pathlib import Path
from xml.etree import ElementTree as ET

from configuracao import normalizar_nome
from exportacoes import _celula_segura
from perfil_gosto import (
    PERIODOS,
    PESO_PERIODO,
    TAMANHO_RANKING,
    PerfilGosto,
    peso_posicao,
    vetor_artistas,
)
from recursos import link_spotify

TAMANHO_PADRAO = 30
FRACAO_SO_ARTISTA = 0.5


@dataclass(frozen=True)
class FaixaFesta:
    musica: str
    artista: str
    para: tuple[str, ...]  # quem tem a música (ou o artista) nos rankings, do maior valor ao menor

    @property
    def link(self) -> str:
        return link_spotify(self.artista, self.musica)


def _valores(perfis: list[PerfilGosto]) -> dict[tuple[str, str], tuple[str, str, dict[str, float]]]:
    """Chave normalizada da faixa → (música, artista, valor por pessoa)."""
    faixas: dict[tuple[str, str], tuple[str, str, dict[str, float]]] = {}
    for perfil in perfis:
        for periodo in PERIODOS:
            for i, f in enumerate(perfil.top_musicas.get(periodo, [])[:TAMANHO_RANKING], 1):
                musica, artista = str(f.get('musica', '')), str(f.get('artista', ''))
                chave = (normalizar_nome(musica), normalizar_nome(artista))
                if not chave[0]:
                    continue
                _, _, valores = faixas.setdefault(chave, (musica, artista, {}))
                peso = PESO_PERIODO[periodo] * peso_posicao(i)
                valores[perfil.nome] = valores.get(perfil.nome, 0.0) + peso
    # Quem não tem a faixa, mas tem o artista, também curte um pouco.
    for perfil in perfis:
        artistas = vetor_artistas(perfil)
        maximo = max(artistas.values(), default=0.0) or 1.0
        for (_, artista_chave), (_, _, valores) in faixas.items():
            if perfil.nome not in valores and artista_chave in artistas:
                valores[perfil.nome] = FRACAO_SO_ARTISTA * artistas[artista_chave] / maximo
    return faixas


def playlist_festa(perfis: list[PerfilGosto], n: int = TAMANHO_PADRAO) -> list[FaixaFesta]:
    """Escolhe até ``n`` faixas maximizando a cobertura equilibrada do grupo."""
    if len(perfis) < 2:
        raise ValueError('A playlist da festa precisa de pelo menos duas pessoas.')
    faixas = _valores(perfis)
    cobertura = {p.nome: 0.0 for p in perfis}
    restantes = dict(faixas)
    escolhidas: list[FaixaFesta] = []
    while restantes and len(escolhidas) < n:

        def ganho(item: tuple[tuple[str, str], tuple[str, str, dict[str, float]]]) -> tuple:
            chave, (_, _, valores) = item
            total = sum(sqrt(cobertura[p] + v) - sqrt(cobertura[p]) for p, v in valores.items())
            return (-total, chave)  # desempate determinístico pelo nome normalizado

        chave, (musica, artista, valores) = min(restantes.items(), key=ganho)
        del restantes[chave]
        for pessoa, valor in valores.items():
            cobertura[pessoa] += valor
        para = tuple(p for p, _ in sorted(valores.items(), key=lambda x: (-x[1], x[0])))
        escolhidas.append(FaixaFesta(musica, artista, para))
    return escolhidas


def exportar_csv(faixas: list[FaixaFesta], destino: str | Path) -> Path:
    """CSV UTF-8 BOM separado por ponto e vírgula, protegido contra fórmulas."""
    caminho = Path(destino)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open('w', encoding='utf-8-sig', newline='') as saida:
        escritor = csv.writer(saida, delimiter=';')
        escritor.writerow(['Música', 'Artista', 'Para', 'Spotify'])
        for f in faixas:
            linha = [f.musica, f.artista, ', '.join(f.para), f.link]
            escritor.writerow([_celula_segura(v) for v in linha])
    return caminho


def exportar_xspf(faixas: list[FaixaFesta], destino: str | Path, titulo: str) -> Path:
    """Playlist XSPF 1 (https://xspf.org); o ElementTree escapa todo o texto."""
    ns = 'http://xspf.org/ns/0/'
    ET.register_namespace('', ns)
    raiz = ET.Element(f'{{{ns}}}playlist', version='1')
    ET.SubElement(raiz, f'{{{ns}}}title').text = titulo
    ET.SubElement(raiz, f'{{{ns}}}creator').text = 'SyncUp'
    lista = ET.SubElement(raiz, f'{{{ns}}}trackList')
    for f in faixas:
        faixa = ET.SubElement(lista, f'{{{ns}}}track')
        ET.SubElement(faixa, f'{{{ns}}}title').text = f.musica
        ET.SubElement(faixa, f'{{{ns}}}creator').text = f.artista
        ET.SubElement(faixa, f'{{{ns}}}annotation').text = 'Para ' + ', '.join(f.para)
        ET.SubElement(faixa, f'{{{ns}}}info').text = f.link
    caminho = Path(destino)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(raiz).write(caminho, encoding='utf-8', xml_declaration=True)
    return caminho
