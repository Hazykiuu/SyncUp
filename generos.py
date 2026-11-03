"""Gêneros musicais: vetor de estilo por pessoa e consulta opcional ao MusicBrainz.

O login do Spotify já traz gêneros por artista. O histórico ZIP não traz; para
ele, se a pessoa ativar, os gêneros vêm do MusicBrainz (base aberta, dados CC0),
respeitando 1 consulta por segundo e guardando as respostas num cache local.
Só nomes de artistas são enviados.

As tags do MusicBrainz são colaborativas e não usam o mesmo vocabulário do
Spotify ("brazilian rock" × "rock"). Por isso cada gênero também conta, com
meio peso, para as palavras que o formam. O eixo de gênero é uma aproximação.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from tempfile import NamedTemporaryFile

import httpx

from configuracao import ConfiguracaoCarga, normalizar_nome
from perfil_gosto import PERIODOS, PerfilGosto, vetor_artistas

URL_MUSICBRAINZ = 'https://musicbrainz.org/ws/2/artist'
USER_AGENT = 'SyncUp/0.9 ( https://github.com/Hazykiuu/SyncUp )'
INTERVALO_S = 1.0  # Regra de uso do MusicBrainz para clientes anônimos.
SCORE_MINIMO = 90
MAXIMO_TAGS = 5
ARTISTAS_POR_PERFIL = 25
PESO_PALAVRA = 0.5
MAXIMO_FALHAS = 3
TENTATIVAS = 2
ARQUIVO_CACHE = 'generos_musicbrainz.json'
# Mesma pasta do cache Parquet (ConfiguracaoCarga.diretorio_cache); a UI passa a configurada.
CACHE_PADRAO = Path(ConfiguracaoCarga().diretorio_cache) / ARQUIVO_CACHE


def _limpar(genero: str) -> str:
    return re.sub(r'\s+', ' ', str(genero).casefold().replace('-', ' ')).strip()


class ConsultaMusicBrainz:
    """Busca as tags mais votadas de um artista, com intervalo mínimo e cache em JSON."""

    def __init__(
        self,
        cliente: httpx.Client | None = None,
        cache: str | Path = CACHE_PADRAO,
        relogio: Callable[[], float] = time.monotonic,
        dormir: Callable[[float], None] = time.sleep,
    ) -> None:
        self._proprio = cliente is None
        self.cliente = cliente or httpx.Client(timeout=15, headers={'User-Agent': USER_AGENT})
        self.caminho = Path(cache)
        self._relogio, self._dormir = relogio, dormir
        self._ultima: float | None = None
        self.falhas = 0
        self._cache = self._ler_disco()

    def _ler_disco(self) -> dict[str, list[str]]:
        try:
            dados = json.loads(self.caminho.read_text('utf-8'))
        except (OSError, ValueError):
            return {}
        return dados if isinstance(dados, dict) else {}

    def generos(self, artista: str) -> list[str]:
        """Tags do artista; lista vazia se não houver correspondência confiável."""
        chave = normalizar_nome(artista)
        if not chave:
            return []
        if chave in self._cache:
            return self._cache[chave]
        nome = str(artista).replace('\\', '\\\\').replace('"', '\\"')
        artistas = None
        for _ in range(TENTATIVAS):  # uma falha passageira (conexão fria, 503) ganha outra chance
            if self.falhas >= MAXIMO_FALHAS:
                return []  # Sem internet ou serviço fora: não espera o timeout de cada artista.
            if self._ultima is not None:
                espera = INTERVALO_S - (self._relogio() - self._ultima)
                if espera > 0:
                    self._dormir(espera)
            self._ultima = self._relogio()
            try:
                resposta = self.cliente.get(
                    URL_MUSICBRAINZ,
                    params={'query': f'artist:"{nome}"', 'fmt': 'json', 'limit': 1},
                    headers={'User-Agent': USER_AGENT},
                )
                resposta.raise_for_status()
                artistas = resposta.json().get('artists') or []
                break
            except (httpx.HTTPError, ValueError):
                self.falhas += 1
        if artistas is None:
            return []  # Falha de rede não entra no cache: tenta de novo na próxima vez.
        tags: list[str] = []
        if artistas and int(artistas[0].get('score', 0)) >= SCORE_MINIMO:
            votadas = sorted(
                (t for t in artistas[0].get('tags') or [] if int(t.get('count', 0)) > 0),
                key=lambda t: (-int(t['count']), str(t.get('name', ''))),
            )
            tags = [_limpar(t['name']) for t in votadas[:MAXIMO_TAGS] if t.get('name')]
        self._cache[chave] = tags
        return tags

    def salvar(self) -> None:
        """Grava o cache; falhas de disco não interrompem a análise.

        Mescla com o que outra sessão gravou enquanto esta consultava, e usa um
        temporário com nome único, para que duas abas não apaguem uma à outra.
        """
        temporario: Path | None = None
        try:
            self.caminho.parent.mkdir(parents=True, exist_ok=True)
            mesclado = {**self._ler_disco(), **self._cache}
            with NamedTemporaryFile(
                'w', dir=self.caminho.parent, suffix='.tmp', encoding='utf-8', delete=False
            ) as arquivo:
                temporario = Path(arquivo.name)
                json.dump(mesclado, arquivo, ensure_ascii=False)
            temporario.replace(self.caminho)
        except OSError:
            if temporario is not None:
                temporario.unlink(missing_ok=True)

    def fechar(self) -> None:
        self.salvar()
        if self._proprio:
            self.cliente.close()


def artistas_principais(perfil: PerfilGosto, limite: int = ARTISTAS_POR_PERFIL) -> list[str]:
    """Artistas do ranking mais longo para o mais curto, sem repetição."""
    vistos: dict[str, str] = {}
    for periodo in reversed(PERIODOS):
        for artista in perfil.top_artistas.get(periodo, []):
            vistos.setdefault(normalizar_nome(artista), artista)
    return list(vistos.values())[:limite]


def preencher_generos(
    perfil: PerfilGosto, consulta: ConsultaMusicBrainz, limite: int = ARTISTAS_POR_PERFIL
) -> PerfilGosto:
    """Completa ``perfil.generos`` para os artistas principais que ainda não têm gênero."""
    generos = dict(perfil.generos)
    conhecidos = {normalizar_nome(a) for a, g in generos.items() if g}
    for artista in artistas_principais(perfil, limite):
        if normalizar_nome(artista) not in conhecidos:
            encontrados = consulta.generos(artista)
            if encontrados:
                generos[artista] = encontrados
    return replace(perfil, generos=generos)


def generos_declarados(perfil: PerfilGosto) -> set[str]:
    """Gêneros como vieram da fonte (sem as palavras derivadas)."""
    return {_limpar(g) for gs in perfil.generos.values() for g in gs if _limpar(g)}


def vetor_generos(perfil: PerfilGosto) -> dict[str, float]:
    """Peso de cada gênero: o peso do artista dividido entre os gêneros dele.

    Gêneros compostos também somam ``PESO_PALAVRA`` às palavras que os formam.
    """
    por_artista = {
        normalizar_nome(a): [_limpar(g) for g in gs if _limpar(g)]
        for a, gs in perfil.generos.items()
    }
    pesos: dict[str, float] = {}
    for chave, peso in vetor_artistas(perfil).items():
        generos = por_artista.get(chave) or []
        for genero in generos:
            parte = peso / len(generos)
            pesos[genero] = pesos.get(genero, 0.0) + parte
            palavras = genero.split()
            if len(palavras) > 1:
                for palavra in palavras:
                    pesos[palavra] = pesos.get(palavra, 0.0) + PESO_PALAVRA * parte
    return pesos
