"""Perfil de gosto unificado: o mesmo formato para histórico ZIP e para a API do Spotify.

A API do Spotify não entrega o histórico completo, só rankings (top 50 artistas e
músicas em três períodos), as últimas 50 músicas e os artistas seguidos. Para que
uma pessoa que enviou o ZIP possa ser comparada com outra que fez login, o ZIP é
convertido para os MESMOS rankings, calculados sobre as mesmas janelas de tempo.
A compatibilidade usa apenas o que as duas fontes têm em comum (rankings).
"""

from __future__ import annotations

import json
from collections import OrderedDict
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

import pandas as pd

from configuracao import ConfiguracaoCarga, normalizar_nome
from dados import Caminho, carregar_historicos, sha_em_cache
from recursos import Escutas, escutas

PERIODOS = ('short_term', 'medium_term', 'long_term')
NOMES_PERIODOS = {
    'short_term': 'últimas ~4 semanas',
    'medium_term': 'últimos ~6 meses',
    'long_term': 'último ~1 ano',
}
# Janelas equivalentes às da API, contadas a partir do fim do histórico.
JANELAS_DIAS = {'short_term': 28, 'medium_term': 182, 'long_term': 365}
PESO_PERIODO = {'short_term': 0.6, 'medium_term': 0.8, 'long_term': 1.0}
PESO_MUSICAS = 0.5  # Artistas das músicas favoritas reforçam o perfil.
TAMANHO_RANKING = 50
TEMPO_MINIMO_PLAY_MS = 30_000
VERSAO_PERFIL = 1


@dataclass
class PerfilGosto:
    """Rankings de uma pessoa, em qualquer fonte. Listas em ordem de preferência."""

    nome: str
    fonte: str  # 'historico_zip', 'spotify_api', 'listenbrainz' ou 'convite'
    coletado_em: str
    top_artistas: dict[str, list[str]] = field(default_factory=dict)
    top_musicas: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    recentes: list[dict[str, str]] = field(default_factory=list)
    seguidos: list[str] = field(default_factory=list)
    generos: dict[str, list[str]] = field(default_factory=dict)
    versao: int = VERSAO_PERFIL

    @property
    def rotulo_fonte(self) -> str:
        rotulos = {
            'spotify_api': 'Spotify (login)',
            'listenbrainz': 'ListenBrainz',
            'convite': 'Convite',
        }
        return rotulos.get(self.fonte, 'Histórico ZIP')

    def para_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    @classmethod
    def de_dict(cls, dados: dict) -> PerfilGosto:
        if not isinstance(dados, dict) or not dados.get('nome'):
            raise ValueError('Perfil inválido: falta o nome.')
        campos = {k: dados[k] for k in cls.__dataclass_fields__ if k in dados}
        campos.setdefault('fonte', 'desconhecida')
        campos.setdefault('coletado_em', '')
        perfil = cls(**campos)
        if not any(perfil.top_artistas.get(p) for p in PERIODOS):
            raise ValueError(f'O perfil de {perfil.nome} não tem nenhum ranking de artistas.')
        return perfil


def salvar_perfil(perfil: PerfilGosto, pasta: str | Path) -> Path:
    """Grava o perfil em ``pasta/<nome>.json`` (sem tokens, só rankings).

    O nome é a identidade do perfil, sem diferenciar maiúsculas: um novo login de
    "Ana" ou "ana" substitui o arquivo da Ana. Se nomes diferentes derem o mesmo
    nome de arquivo ("Ana Clara" e "Ana_Clara"), o segundo ganha um sufixo ``-2``,
    ``-3``… em vez de apagar o primeiro.
    """
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    seguro = ''.join(c if c.isalnum() or c in '-_' else '_' for c in perfil.nome.strip())[:60]
    base = seguro or 'perfil'
    # Busca sem diferenciar maiúsculas em todo sistema: no Linux, "ana" acharia "Ana.json".
    existentes = {p.name.casefold(): p for p in pasta.glob('*.json')}
    dono = perfil.nome.strip().casefold()
    caminho = existentes.get(f'{base}.json'.casefold(), pasta / f'{base}.json')
    sufixo = 1
    while caminho.exists() and _dono(caminho) != dono:
        sufixo += 1
        nome = f'{base}-{sufixo}.json'
        caminho = existentes.get(nome.casefold(), pasta / nome)
    caminho.write_text(perfil.para_json(), encoding='utf-8')
    return caminho


def _dono(caminho: Path) -> str | None:
    """Nome (casefold) gravado num perfil existente; None se ilegível."""
    try:
        dados = json.loads(caminho.read_text(encoding='utf-8'))
        return str(dados.get('nome', '')).strip().casefold()
    except (OSError, ValueError, AttributeError):
        return None


def carregar_perfil(caminho: str | Path) -> PerfilGosto:
    """Lê um perfil JSON salvo pelo SyncUp."""
    try:
        dados = json.loads(Path(caminho).read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as erro:
        raise ValueError(f'Não foi possível ler o perfil {Path(caminho).name}.') from erro
    return PerfilGosto.de_dict(dados)


def listar_perfis(pasta: str | Path) -> list[Path]:
    """Perfis JSON disponíveis numa pasta, em ordem alfabética."""
    pasta = Path(pasta)
    return sorted(pasta.glob('*.json')) if pasta.is_dir() else []


def _ranking(contagem: pd.Series, limite: int = TAMANHO_RANKING) -> list:
    """Ordena por contagem decrescente e nome crescente (desempate estável)."""
    if contagem.empty:
        return []
    tabela = contagem.rename('n').reset_index()
    chaves = [c for c in tabela.columns if c != 'n']
    for c in chaves:
        tabela[c] = tabela[c].astype(str)
    tabela = tabela.sort_values(['n', *chaves], ascending=[False] + [True] * len(chaves))
    return tabela.head(limite)[chaves].values.tolist()


def perfil_de_historico(dados: pd.DataFrame, nome: str) -> PerfilGosto:
    """Converte ``Historico.dados`` nos mesmos rankings que a API devolveria.

    As janelas (4 semanas, 6 meses, 1 ano) terminam no último registro do
    histórico, não na data de hoje: assim um ZIP antigo continua comparável.
    """
    if dados.empty:
        raise ValueError(f'O histórico de {nome} não tem músicas válidas.')
    plays = dados[dados['ms_played'] >= TEMPO_MINIMO_PLAY_MS]
    if plays.empty:
        raise ValueError(f'O histórico de {nome} não tem plays de pelo menos 30 segundos.')
    fim = plays['data_utc'].max()
    top_artistas: dict[str, list[str]] = {}
    top_musicas: dict[str, list[dict[str, str]]] = {}
    for periodo, dias in JANELAS_DIAS.items():
        janela = plays[plays['data_utc'] > fim - pd.Timedelta(dias, unit='D')]
        artistas = janela.groupby('artista', observed=True).size()
        top_artistas[periodo] = [linha[0] for linha in _ranking(artistas)]
        musicas = janela.groupby(['musica', 'artista'], observed=True).size()
        top_musicas[periodo] = [{'musica': m, 'artista': a} for m, a in _ranking(musicas)]
    ultimas = plays.sort_values('data_utc').tail(50).iloc[::-1]
    recentes = [
        {'musica': str(m), 'artista': str(a), 'tocada_em': t.isoformat()}
        for m, a, t in zip(ultimas['musica'], ultimas['artista'], ultimas['data_utc'])
    ]
    return PerfilGosto(
        nome=(nome or '').strip() or 'Sem nome',
        fonte='historico_zip',
        coletado_em=fim.isoformat(),
        top_artistas=top_artistas,
        top_musicas=top_musicas,
        recentes=recentes,
    )


_perfis_zip: OrderedDict[tuple, PerfilGosto] = OrderedDict()
_trava_perfis = Lock()
MAXIMO_PERFIS_CACHE = 64  # Perfis têm poucos KB; repetir um Match não relê os ZIPs.
_escutas_zip: OrderedDict[tuple, Escutas] = OrderedDict()
# shortcut: as escutas de um histórico real ocupam alguns MB; 16 cobre um Match cheio.
# Guardar em disco (Parquet) se o app passar a atender vários grupos ao mesmo tempo.
MAXIMO_ESCUTAS_CACHE = 16


def _guardar(cache: OrderedDict, chave: tuple, valor, maximo: int) -> None:
    with _trava_perfis:
        cache[chave] = valor
        while len(cache) > maximo:
            cache.popitem(last=False)


def _chave_perfil(partes: list[Caminho], config: ConfiguracaoCarga) -> tuple:
    return tuple(sorted(sha_em_cache(p) for p in partes)), config, VERSAO_PERFIL


def tem_perfil_em_cache(
    arquivos: Caminho | list[Caminho] | tuple[Caminho, ...], configuracao: ConfiguracaoCarga
) -> bool:
    """Se ``perfil_de_arquivos`` devolveria o perfil sem ler os arquivos."""
    partes = list(arquivos) if isinstance(arquivos, (list, tuple)) else [arquivos]
    with _trava_perfis:
        return _chave_perfil(partes, configuracao) in _perfis_zip


def perfil_de_arquivos(
    arquivos: Caminho | list[Caminho] | tuple[Caminho, ...],
    nome: str,
    configuracao: ConfiguracaoCarga | None = None,
) -> PerfilGosto:
    """``perfil_de_historico`` dos arquivos, com cache em memória pelo conteúdo (SHA-256)."""
    config = configuracao or ConfiguracaoCarga()
    partes = list(arquivos) if isinstance(arquivos, (list, tuple)) else [arquivos]
    chave = _chave_perfil(partes, config)
    with _trava_perfis:
        perfil = _perfis_zip.get(chave)
        if perfil is not None:
            _perfis_zip.move_to_end(chave)
    if perfil is None:
        dados = carregar_historicos(partes, configuracao=config).dados
        perfil = perfil_de_historico(dados, nome)
        _guardar(_perfis_zip, chave, perfil, MAXIMO_PERFIS_CACHE)
        # Já com o histórico em mãos: a sintonia do Match não precisa reler o ZIP.
        _guardar(_escutas_zip, chave, escutas(dados), MAXIMO_ESCUTAS_CACHE)
    # O nome não faz parte da chave: o mesmo ZIP pode ser enviado com outro nome.
    return replace(perfil, nome=(nome or '').strip() or 'Sem nome')


def escutas_de_arquivos(
    arquivos: Caminho | list[Caminho] | tuple[Caminho, ...],
    configuracao: ConfiguracaoCarga | None = None,
) -> Escutas:
    """Intervalos de escuta dos arquivos (``recursos.escutas``), com o cache do perfil."""
    config = configuracao or ConfiguracaoCarga()
    partes = list(arquivos) if isinstance(arquivos, (list, tuple)) else [arquivos]
    chave = _chave_perfil(partes, config)
    with _trava_perfis:
        valor = _escutas_zip.get(chave)
        if valor is not None:
            _escutas_zip.move_to_end(chave)
            return valor
    valor = escutas(carregar_historicos(partes, configuracao=config).dados)
    _guardar(_escutas_zip, chave, valor, MAXIMO_ESCUTAS_CACHE)
    return valor


def limpar_cache_perfis() -> None:
    with _trava_perfis:
        _perfis_zip.clear()
        _escutas_zip.clear()


def peso_posicao(posicao: int, tamanho: int = TAMANHO_RANKING) -> float:
    """1º lugar vale 1; o último do top 50 vale 1/50. Posições contam a partir de 1."""
    return max(0.0, (tamanho - posicao + 1) / tamanho)


def vetor_artistas(perfil: PerfilGosto) -> dict[str, float]:
    """Peso de cada artista combinando os rankings dos três períodos.

    peso = Σ peso_período × peso_posição (top artistas)
         + 0,5 × Σ peso_período × peso_posição da melhor música do artista.
    Chaves normalizadas (caixa e pontuação) para casar nomes das duas fontes.
    """
    pesos: dict[str, float] = {}
    for periodo in PERIODOS:
        fator = PESO_PERIODO[periodo]
        for i, artista in enumerate(perfil.top_artistas.get(periodo, [])[:TAMANHO_RANKING], 1):
            chave = normalizar_nome(artista)
            if chave:
                pesos[chave] = pesos.get(chave, 0.0) + fator * peso_posicao(i)
        vistos: set[str] = set()
        for i, faixa in enumerate(perfil.top_musicas.get(periodo, [])[:TAMANHO_RANKING], 1):
            chave = normalizar_nome(str(faixa.get('artista', '')))
            if chave and chave not in vistos:
                vistos.add(chave)
                pesos[chave] = pesos.get(chave, 0.0) + PESO_MUSICAS * fator * peso_posicao(i)
    return pesos


def nomes_exibicao(perfil: PerfilGosto) -> dict[str, str]:
    """Chave normalizada → nome como aparece nos rankings."""
    nomes: dict[str, str] = {}
    for periodo in PERIODOS:
        for artista in perfil.top_artistas.get(periodo, []):
            nomes.setdefault(normalizar_nome(artista), artista)
        for faixa in perfil.top_musicas.get(periodo, []):
            artista = str(faixa.get('artista', ''))
            nomes.setdefault(normalizar_nome(artista), artista)
    return nomes


def musicas_favoritas(perfil: PerfilGosto) -> set[tuple[str, str]]:
    """Todas as músicas que aparecem em algum top (normalizadas)."""
    return {
        (normalizar_nome(str(f.get('musica', ''))), normalizar_nome(str(f.get('artista', ''))))
        for periodo in PERIODOS
        for f in perfil.top_musicas.get(periodo, [])
    }


def agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')
